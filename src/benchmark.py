"""Injection benchmark (NB4): run the whole method and its baselines on injected data and score them.

For one injected dataset:
  1. rule engine v1 on the injected series (items, votes, zone runs, states);
  2. label model (constrained Dawid-Skene) and majority vote;
  3. residuals from predictors fitted once on the real data (cross-fitted, so each half of the injected series is
     predicted by models that never saw it): LightGBM forecast and nowcast (NB3), TCN without graph, TCN-GAT, their
     average, and the hybrids LightGBM + TCN / learned-graph correction (D59);
  4. level scores, event formation (score smoothing w, threshold gamma at the q-th percentile on rule-negative
     zone-steps, merge gap; NB3: w = 1, q = 99.5, gap = 1) and detections for every detector variant and baseline.
     The main detector and the settings of the tuned detectors come from tools/dev_select_detector.py (D60);
  5. end model (soft-label GBDT, out of fold by episode) and fusion, as in NB3;
  6. metrics against the injected truth: event-wise precision / recall / F1 (eq. 17), step-wise AUC-PR, boundary
     errors, and an event table (one row per typed injected event with every labeler's distribution) from which the
     notebook computes attribution macro-F1, ECE (eq. 18), Brier and tunes beta on the training period.

Evaluation scope (D54, D60): only predictions that touch the clean region (where injection was allowed) or an injected
event count. The clean region is rule-based, the same for every detector. Predictions that lie entirely on real rule
states are ignored because their truth is unknown; the *_bgx metrics also ignore each method's own detections on the
uninjected series (set_background), the same treatment for detectors as the rule states give the rules.
"""
import time
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

import rules_v1 as R1
import detector as D
import end_model as EM
import label_model as LM
import graph_model as G
from inject import TYPED, UNTYPED

SOUTH = ["Laayoune", "Boujdour", "Foum eloued"]
CL = EM.EVENT_CLASSES

# ------------------------------------------------------------------ detector variants (D59, D60)
V_HYB = "LightGBM + learned-graph correction, hierarchy, multi-scale"
V_HYB_NOG = "LightGBM + TCN correction (no graph), hierarchy, multi-scale"
V_LGB = "LightGBM forecast, hierarchy, multi-scale"
V_GAT = "TCN-GAT, hierarchy, multi-scale"
V_MEAN = "mean(LightGBM, TCN-GAT), hierarchy, multi-scale"
V_TCN_MS = "TCN, no graph, hierarchy, multi-scale"   # no-graph ablation of the main detector (added after NB4, D62)
V_NOW = "LGB nowcast (raw, hierarchy)"
V_TCN_RAW = "TCN, no graph (raw, hierarchy)"
V_GAT_RAW = "TCN-GAT (raw, hierarchy)"
V_SINGLE = "single scale (raw band)"            # ablations of whichever detector is the main one
V_FLAT = "no hierarchy (flat residual)"
V_GAT_NB3 = V_GAT + " (NB3 event formation)"      # untuned rows: the effect of event formation on short shocks
V_LGB_NB3 = V_LGB + " (NB3 event formation)"
BASELINES = ("STL + MAD", "Isolation Forest", "LOF")
# variant -> (predictor key, "ms" = all phase-aligned bands | "raw" = raw band); the hierarchy is always used
VARIANTS = {V_HYB: ("LGB + GAT", "ms"), V_HYB_NOG: ("LGB + TCN", "ms"), V_LGB: ("LGB forecast", "ms"),
            V_GAT: ("TCN-GAT", "ms"), V_MEAN: ("mean(LGB, TCN-GAT)", "ms"), V_TCN_MS: ("TCN", "ms"), V_NOW: ("LGB nowcast", "raw"),
            V_TCN_RAW: ("TCN", "raw"), V_GAT_RAW: ("TCN-GAT", "raw")}
MAIN_CANDIDATES = (V_HYB, V_LGB, V_GAT, V_MEAN)
TUNED = MAIN_CANDIDATES + BASELINES                # detectors whose event formation is tuned on development seeds
DEFAULT_SETTING = dict(w=1, q=99.5, gap=1)       # NB3: no smoothing, 99.5th percentile, merge gap of 1 step
MAIN = V_HYB                                     # default; NB4 takes it from the development selection (D60)


# ------------------------------------------------------------------ region and helpers
def clean_region(P, det_items=None, burn_days=35, clock_dates=None):
    """Zone-steps where injection is allowed and where predictions are scored: away from real rule states (+-SPILL),
    real multi-zone states, the 35-day burn-in (14-day expected value + 21-day warm-up) and clock days.
    det_items: real-data detector candidates to exclude as well (+-SPILL). NB4 passes None (D60): excluding one
    detector's own candidates would hide that detector's false alarms and only those."""
    M = P["mask"]
    w = 2 * D.SPILL_STEPS + 1
    near_own = M.astype(float).rolling(w, center=True, min_periods=1).max() > 0
    near_multi = (M.sum(axis=1) >= 2).astype(float).rolling(w, center=True, min_periods=1).max().to_numpy() > 0
    bad = near_own.to_numpy() | near_multi[:, None] | P["rho"].isna().to_numpy()
    idx = P["rho"].index
    cols = list(P["rho"].columns)
    sp = pd.Timedelta(minutes=P["step"] * D.SPILL_STEPS)
    for r in (det_items.itertuples() if det_items is not None else ()):
        a, b = idx.searchsorted(r.start - sp), idx.searchsorted(r.end + sp)
        for z in r.zones.split(","):
            if z in cols:
                bad[a:b, cols.index(z)] = True
    bad[: burn_days * P["per_day"]] = True
    for d in (clock_dates if clock_dates is not None else R1.EUROPE_DST + R1.MOROCCO_DST):
        d = pd.Timestamp(d)
        bad[idx.searchsorted(d - pd.Timedelta(days=1)):idx.searchsorted(d + pd.Timedelta(days=2))] = True
    return pd.DataFrame(~bad, index=idx, columns=cols)


def flat_score(P, E):
    """Ablation 'no hierarchy': robust z of the zone residual itself (same window, warm-up and zero rule as eq. 15)."""
    win, mp = 28 * P["per_day"], 7 * P["per_day"]
    warm = P["rho"].index < P["rho"].index[0] + pd.Timedelta(days=D.WARMUP_DAYS)
    out = {}
    for z in E.columns:
        s = E[z].copy(); s[warm] = np.nan
        out[z] = D.robust_score(s, ~P["mask"][z], win, mp)
    return pd.DataFrame(out, index=E.index)


def smooth_score(Z, w):
    """Centred moving average of a zone score over w steps (w = 1: unchanged). Part of event formation (D60)."""
    return Z if int(w) <= 1 else Z.rolling(int(w), center=True, min_periods=1).mean()


def gamma_of(P, Z, q=99.5):
    """NB3's threshold: q-th percentile (99.5) of Z on zone-steps away from rule states (own zone and multi-zone)."""
    w = 2 * D.SPILL_STEPS + 1
    M = P["mask"].astype(float)
    near_own = M.rolling(w, center=True, min_periods=1).max() > 0
    near_multi = (M.sum(axis=1) >= 2).astype(float).rolling(w, center=True, min_periods=1).max() > 0
    neg = (~near_own) & (~near_multi.to_numpy()[:, None]) & Z.notna()
    return float(np.nanpercentile(Z.where(neg).to_numpy(), q))


def iso_lof_features(P):
    rho = P["rho"]
    feats = {
        "rho": rho, "d1": rho.diff(), "d_day": rho - rho.shift(P["per_day"]),
        "std6": rho.rolling(6, min_periods=2).std(), "mean6": rho.rolling(6, min_periods=2).mean(),
    }
    X = np.stack([f.to_numpy() for f in feats.values()], axis=-1)        # (T, Z, 5)
    return np.nan_to_num(X, nan=0.0)


def iso_lof_scores(P, seed=0, use_lof=True, n_fit=50000, n_fit_lof=10000):
    """Classical unsupervised baselines on per-zone-step features of rho (guide: Isolation Forest, LOF)."""
    from sklearn.ensemble import IsolationForest
    from sklearn.neighbors import LocalOutlierFactor
    X = iso_lof_features(P)
    T, Z, k = X.shape
    flat = X.reshape(-1, k)
    neg = (~P["mask"]).to_numpy().reshape(-1) & P["rho"].notna().to_numpy().reshape(-1)
    rng = np.random.default_rng(seed)
    fit_idx = rng.choice(np.flatnonzero(neg), size=min(n_fit, int(neg.sum())), replace=False)
    out = {}
    iso = IsolationForest(n_estimators=100, random_state=seed, n_jobs=-1).fit(flat[fit_idx])
    out["Isolation Forest"] = pd.DataFrame(-iso.score_samples(flat).reshape(T, Z), index=P["rho"].index, columns=P["rho"].columns)
    if use_lof:
        lof = LocalOutlierFactor(n_neighbors=35, novelty=True, n_jobs=-1).fit(flat[fit_idx[:n_fit_lof]])
        out["LOF"] = pd.DataFrame(-lof.score_samples(flat).reshape(T, Z), index=P["rho"].index, columns=P["rho"].columns)
    return out


def _span_mask(df, index, cols, end_col="end"):
    """Boolean frame (time x zone) covering each row's [start, end_col) on its zones."""
    m = np.zeros((len(index), len(cols)), dtype=bool)
    ci = {z: i for i, z in enumerate(cols)}
    for r in df.itertuples():
        a, b = index.searchsorted(r.start), index.searchsorted(getattr(r, end_col))
        for z in r.zones.split(","):
            if z in ci:
                m[a:max(b, a + 1), ci[z]] = True
    return m


# ------------------------------------------------------------------ matching and metrics
def match_events(pred, truth, need_zone=True):
    """Pairs (pred row, truth row, overlap in 10-min steps x shared zones): time overlap of [start, end) with the
    truth's [start, end_affected) and, if need_zone, at least one shared zone (guide eq. 17 needs time overlap only)."""
    pairs = []
    if not len(pred) or not len(truth):
        return pd.DataFrame(columns=["p", "t", "overlap"])
    pz = [set(z.split(",")) for z in pred.zones]
    tz = [set(z.split(",")) for z in truth.zones]
    ps, pe = pred.start.to_numpy(), pred.end.to_numpy()
    ts, te = truth.start.to_numpy(), np.maximum(truth.end_affected.to_numpy(), truth.end.to_numpy())
    for j in range(len(truth)):
        hit = np.flatnonzero((ps < te[j]) & (pe > ts[j]))
        for i in hit:
            sh = pz[i] & tz[j]
            if sh or not need_zone:
                ov = (min(pe[i], te[j]) - max(ps[i], ts[j])) / np.timedelta64(10, "m")
                pairs.append((i, j, float(ov) * max(len(sh), 0.5)))
    return pd.DataFrame(pairs, columns=["p", "t", "overlap"])


def detection_metrics(pred, truth, scope, index, cols, period_mask):
    """Event-wise P, R, F1 (eq. 17) in one period. scope: bool array (time x zone) of countable zone-steps."""
    pin = period_mask[index.searchsorted(pred.start.clip(upper=index[-1]))] if len(pred) else np.array([], bool)
    pred = pred[pin].reset_index(drop=True) if len(pred) else pred
    tin = period_mask[index.searchsorted(truth.start)] if len(truth) else np.array([], bool)
    truth = truth[tin].reset_index(drop=True) if len(truth) else truth
    if len(pred):
        counted = np.array([scope[index.searchsorted(r.start):max(index.searchsorted(r.end), index.searchsorted(r.start) + 1),
                                  [cols.index(z) for z in r.zones.split(",") if z in cols]].any() for r in pred.itertuples()])
        pred = pred[counted].reset_index(drop=True)
    n_p, n_t = len(pred), len(truth)

    def prf(m):
        tp_p = m.p.nunique() if len(m) else 0
        tp_t = m.t.nunique() if len(m) else 0
        P_ = tp_p / n_p if n_p else np.nan
        R_ = tp_t / n_t if n_t else np.nan
        return P_, R_, (2 * P_ * R_ / (P_ + R_) if n_p and n_t and (P_ + R_) > 0 else 0.0)
    m_time = match_events(pred, truth, need_zone=False)        # guide eq. 17: overlap in time
    m = match_events(pred, truth, need_zone=True)              # zone-strict: also share a zone
    P_, R_, F1 = prf(m_time)
    Pz, Rz, F1z = prf(m)
    found = set(m.t) if len(m) else set()
    rec_type = {f"recall_{t}": float(np.mean([j in found for j in np.flatnonzero(truth.type.to_numpy() == t)]))
                if (truth.type == t).any() else np.nan for t in TYPED + UNTYPED}
    # boundary errors of the best-overlapping zone-matched prediction (minutes)
    se, ee = [], []
    if len(m):
        best = m.sort_values("overlap", ascending=False).drop_duplicates("t")
        for r in best.itertuples():
            se.append(abs((pred.start[r.p] - truth.start[r.t]).total_seconds()) / 60)
            ee.append(abs((pred.end[r.p] - truth.end[r.t]).total_seconds()) / 60)
    return dict(n_pred=n_p, n_true=n_t, precision=P_, recall=R_, f1=F1, precision_zone=Pz, recall_zone=Rz, f1_zone=F1z,
                start_err_min=float(np.median(se)) if se else np.nan, end_err_min=float(np.median(ee)) if ee else np.nan,
                **rec_type)


def step_auc(score, truth_mask, scope, period_mask):
    """Step-wise AUC-PR (average precision) on countable zone-steps of one period."""
    sel = scope & period_mask[:, None]
    y = truth_mask[sel]
    if y.sum() == 0:
        return np.nan
    s = np.nan_to_num(np.asarray(score)[sel], nan=-1e9, posinf=1e12)
    return float(average_precision_score(y, s))


# ------------------------------------------------------------------ the benchmark
class Benchmark:
    def __init__(self, raw, P_real, det_real, lgb_models, graph_models, gb_backend="lightgbm", log=True,
                 main=MAIN, settings=None):
        """lgb_models: {'forecast': models, 'nowcast': models} from detector.fit_rho_models on the real data;
        graph_models: {'TCN', 'TCN-GAT', 'LGB + TCN', 'LGB + GAT'} from graph_model.fit_graph_models (the last two
        are hybrids on the LightGBM forecast, D59); det_real: None for the rule-based clean region (D60);
        main: the main detector variant; settings: {variant: dict(w, q, gap)} event formation (D60)."""
        self.raw, self.lgb, self.graph, self.gbb, self.log = raw, lgb_models, graph_models, gb_backend, log
        self.main, self.settings = main, dict(settings or {})
        self.background = {}
        self.clean = clean_region(P_real, det_real)
        self.index = P_real["rho"].index
        self.cols = list(P_real["rho"].columns)

    def set_background(self, real):
        """Each method's predictions on the real, uninjected data (pipeline() output). In run(), injected-data
        predictions that match one of the same method's real-data predictions (shared zone, time overlap) are also
        scored with those removed (*_bgx metrics, D60): their truth is unknown, as for rule states."""
        bg = {k: d[["start", "end", "zones"]].reset_index(drop=True) if len(d) else pd.DataFrame(columns=["start", "end", "zones"])
              for k, d in real["DET"].items()}
        do = real["det_only"]
        bg["ours (rules + detector)"] = do[["start", "end", "zones"]].reset_index(drop=True) if len(do) else pd.DataFrame(columns=["start", "end", "zones"])
        bg["rules only (rule engine v1)"] = pd.DataFrame(columns=["start", "end", "zones"])   # real rule items are outside the scoring area
        self.background = bg

    def _t(self, msg, t0):
        if self.log:
            print(f"    {msg}: {time.time() - t0:.0f} s", flush=True)
        return time.time()

    def setting(self, name):
        """Event formation of one detector (D60): main candidates and baselines use their own tuned setting (NB3's if
        none); every other variant is an ablation and uses the main detector's setting, so it changes one thing only."""
        if name in self.settings and (name in TUNED or name == self.main):
            return {**DEFAULT_SETTING, **self.settings[name]}
        if name not in TUNED and name != self.main:
            return self.setting(self.main)
        return dict(DEFAULT_SETTING)

    def predictions(self, P):
        """rho_hat of every predictor on panel P (each fold by the model trained on the other fold of the real data)."""
        pf = D.apply_rho_models(P, self.lgb["forecast"], "forecast")
        pred = {"LGB forecast": pf, "LGB nowcast": D.apply_rho_models(P, self.lgb["nowcast"], "nowcast")}
        for k, m in self.graph.items():
            hybrid = any(getattr(x, "use_base", False) for x in m.values())
            pred[k] = G.apply_graph_models(P, m, base=pf if hybrid else None)
        if "TCN-GAT" in pred:
            pred["mean(LGB, TCN-GAT)"] = (pf + pred["TCN-GAT"]) / 2
        return pred

    def raw_scores(self, P, pred, baselines=BASELINES, seed=0):
        """Unsmoothed zone scores of every available variant and baseline, and the level scores by predictor."""
        E = {k: P["rho"] - v for k, v in pred.items()}
        main_key = VARIANTS[self.main][0]
        LS = {}
        for v, (k, b) in VARIANTS.items():
            if k in E and b == "ms" and (k not in LS or len(LS[k]) == 1):
                LS[k] = D.level_scores(P, E[k])
        for v, (k, b) in VARIANTS.items():
            if k in E and k not in LS:
                LS[k] = D.level_scores(P, E[k], bands_used=["raw"])
        Z = {v: D.zone_max_score(P, LS[k] if b == "ms" else {"raw": LS[k]["raw"]})
             for v, (k, b) in VARIANTS.items() if k in LS}
        Z[V_SINGLE] = D.zone_max_score(P, {"raw": LS[main_key]["raw"]})
        Z[V_FLAT] = flat_score(P, E[main_key])
        if "STL + MAD" in baselines:
            Z["STL + MAD"] = flat_score(P, D.stl_residual(P, jumps=True, n_jobs=-1))
        if "Isolation Forest" in baselines or "LOF" in baselines:
            Z.update(iso_lof_scores(P, seed=seed, use_lof="LOF" in baselines))
        return Z, LS

    def pipeline(self, data, seed=0, baselines=BASELINES, family_ablation=False):
        """The whole method on one dataset (injected or real): rules, label model, every detector, the main
        detector's candidates, end model and the distribution table PRED of every predicted south item."""
        t0 = time.time(); tt = t0
        res = R1.build_from_data(self.raw, data)
        tt = self._t("rule engine", tt)
        items = res["items"]
        votes = res["votes"].set_index("item_id")
        ds = LM.DawidSkene().fit(votes, items, R1.RULE_KIND)
        mv = LM.majority_vote(votes, items)
        tt = self._t("label model", tt)
        P = D.build_panel(res["data"], res["exp"], res["masks"], "south")
        zr = res["zone_runs"]
        pred = self.predictions(P)
        tt = self._t("predictions", tt)
        Z0, LS = self.raw_scores(P, pred, baselines, seed)
        tt = self._t("level scores and baselines", tt)
        SCORES, GAM, DET = {}, {}, {}
        empty = pd.DataFrame(columns=zr.columns)
        for k, z in Z0.items():
            st = self.setting(k)
            SCORES[k] = smooth_score(z, st["w"])
            GAM[k] = gamma_of(P, SCORES[k], st["q"])
            DET[k] = EM.detector_items(P, SCORES[k], GAM[k], empty, max_gap=st["gap"])
        for k, name in ((V_GAT, V_GAT_NB3), (V_LGB, V_LGB_NB3)):    # the same scores with NB3's event formation
            if k in Z0:
                SCORES[name] = Z0[k]
                GAM[name] = gamma_of(P, Z0[k], DEFAULT_SETTING["q"])
                DET[name] = EM.detector_items(P, Z0[k], GAM[name], empty, max_gap=DEFAULT_SETTING["gap"])
        MAIN_ = self.main
        S_main = LS[VARIANTS[MAIN_][0]]
        S_now_v = LS["LGB nowcast"]["raw"]["v"]

        # rule items (south dead/fill) and the main detector's detector-only candidates
        ev = items[(items.system == "south") & items.kind.isin(["dead", "fill"])].reset_index(drop=True)
        det_only = EM.detector_items(P, SCORES[MAIN_], GAM[MAIN_], zr, max_gap=self.setting(MAIN_)["gap"])
        if len(det_only):
            det_only.insert(0, "item_id", [f"X{i:03d}" for i in range(len(det_only))])

        # end model and fusion, exactly as NB3 (south only)
        rng = np.random.default_rng(seed)
        busy = P["mask"] | (SCORES[MAIN_] > GAM[MAIN_]) | P["rho"].isna()
        pats = np.where(ev.n_cities >= 2, "all", np.where(ev.n_zones >= 2, "city", "zone"))
        nw = EM.normal_windows(P, busy, 250, rng, ev.duration_h.clip(upper=48).to_numpy(), pats)
        nw.insert(0, "item_id", [f"N{i:03d}" for i in range(len(nw))])
        epi = EM.episode_info(items)
        parts = [p for p in (ev, nw, det_only) if len(p)]
        feat = pd.concat([EM.item_features(P, S_main, S_now_v, p, zr, epi) for p in parts], ignore_index=True)
        feat["source"] = feat.item_id.str[0].map({"D": "rule", "F": "rule", "N": "normal", "X": "detector"})
        DET_COLS = [c for c in feat.columns if c.startswith("det_")]
        EP_COLS = ["ep_n_items", "ep_has_multizone_fill", "ep_has_multicity_dead", "ep_duration_h", "preceded_by_fill", "followed_by_fill"]
        BASE = [c for c in feat.columns if c not in DET_COLS + EP_COLS + ["item_id", "source"]]
        lab = feat[feat.source != "detector"].reset_index(drop=True)
        qi = ds.q_.copy(); qi.index = items.item_id.values
        Q = np.zeros((len(lab), len(CL)))
        for i, r in enumerate(lab.itertuples()):
            if r.source == "rule":
                Q[i] = [qi.at[r.item_id, c] for c in CL]
            else:
                Q[i, CL.index("N")] = 1.0
        Q = Q / Q.sum(axis=1, keepdims=True).clip(min=1e-12)
        ep_of = dict(zip(items.item_id, items.episode))
        groups = np.array([ep_of[i] if isinstance(ep_of.get(i), str) else i for i in lab.item_id])
        X_all, X_nod = lab[BASE + EP_COLS + DET_COLS].to_numpy(float), lab[BASE + EP_COLS].to_numpy(float)
        F_all = EM.oof_predict(X_all, Q, groups, EM.fit_predict_gbdt, backend=self.gbb)
        F_nod = EM.oof_predict(X_nod, Q, groups, EM.fit_predict_gbdt, backend=self.gbb)
        dsub = feat[feat.source == "detector"].reset_index(drop=True)
        if len(dsub):
            Fd = EM.fit_predict_gbdt(X_all, Q, dsub[BASE + EP_COLS + DET_COLS].to_numpy(float), CL, backend=self.gbb)
            Fd_nod = EM.fit_predict_gbdt(X_nod, Q, dsub[BASE + EP_COLS].to_numpy(float), CL, backend=self.gbb)
        tt = self._t("end model", tt)

        # one distribution table for every predicted item of the full method
        rows = []
        lab_i = {r.item_id: i for i, r in enumerate(lab.itertuples())}
        mv_of = dict(zip(items.item_id, mv.values))
        for r in ev.itertuples():
            i = lab_i[r.item_id]
            rows.append(dict(item_id=r.item_id, source="rule", start=r.start, end=r.end, zones=r.zones,
                             feasible=",".join(c for c in LM.feasible_classes(r) if c in CL), mv=mv_of[r.item_id],
                             **{f"q_{c}": Q[i, k] for k, c in enumerate(CL)}, **{f"f_{c}": F_all[i, k] for k, c in enumerate(CL)},
                             **{f"fn_{c}": F_nod[i, k] for k, c in enumerate(CL)}))
        for j, r in enumerate(dsub.itertuples()):
            d = det_only.set_index("item_id").loc[r.item_id]
            rows.append(dict(item_id=r.item_id, source="detector", start=d.start, end=d.end, zones=d.zones,
                             feasible=",".join(CL), mv="N", **{f"q_{c}": 1 / len(CL) for c in CL},
                             **{f"f_{c}": Fd[j, k] for k, c in enumerate(CL)}, **{f"fn_{c}": Fd_nod[j, k] for k, c in enumerate(CL)}))
        PRED = pd.DataFrame(rows)

        # label-model ablation: drop one rule family at a time (guide ablation 2)
        fam_q = {}
        if family_ablation:
            for fam in sorted(set(R1.RULE_FAMILY.values()) - {"clock"}):              # no clock events are injected
                keep = [c for c in votes.columns if R1.RULE_FAMILY.get(c) != fam]
                qf = LM.DawidSkene(n_restarts=5).fit(votes[keep], items, R1.RULE_KIND).q_
                qf.index = items.item_id.values
                fam_q[fam] = qf
            tt = self._t("family ablation", tt)
        return dict(items=items, P=P, zr=zr, ev=ev, det_only=det_only, SCORES=SCORES, GAM=GAM, DET=DET, PRED=PRED,
                    fam_q=fam_q, pred=pred, feat=feat, seconds=time.time() - t0)

    def run(self, data_inj, truth, seed=0, baselines=BASELINES, family_ablation=False):
        """pipeline() on one injected dataset, then every metric against the injected truth."""
        t0 = time.time()
        o = self.pipeline(data_inj, seed, baselines, family_ablation)
        P, ev, det_only, SCORES, GAM, DET, PRED, fam_q = (o[k] for k in ("P", "ev", "det_only", "SCORES", "GAM", "DET", "PRED", "fam_q"))
        MAIN_ = self.main

        # ---------------------------------------------------------------- metrics
        fold = (self.index >= D.SPLIT)
        periods = {"train": ~fold, "test": fold}
        truth = truth.copy()
        tmask = _span_mask(truth, self.index, self.cols, "end")
        scope = self.clean.to_numpy() | _span_mask(truth, self.index, self.cols, "end_affected")
        rule_pred = ev[["item_id", "start", "end", "zones"]]
        full_pred = pd.concat([rule_pred, det_only[["item_id", "start", "end", "zones"]] if len(det_only) else None], ignore_index=True)
        methods = {"rules only (rule engine v1)": rule_pred, "ours (rules + detector)": full_pred}
        for k, d in DET.items():
            methods[k] = d[["start", "end", "zones"]] if len(d) else pd.DataFrame(columns=["start", "end", "zones"])
        det_rows = []
        for pname, pm in periods.items():
            for k, pr in methods.items():
                pr = pr.reset_index(drop=True)
                row = dict(method=k, period=pname, gamma=GAM.get(k, np.nan),
                           **detection_metrics(pr, truth, scope, self.index, self.cols, pm))
                bg = self.background.get(k)
                if bg is not None:          # D60: each method's own detections on the uninjected data are not scored
                    hit = match_events(pr, bg.assign(end_affected=bg.end), need_zone=True) if len(pr) and len(bg) else pd.DataFrame(columns=["p"])
                    m2 = detection_metrics(pr.drop(index=set(hit.p)).reset_index(drop=True), truth, scope, self.index, self.cols, pm)
                    row.update(n_pred_bgx=m2["n_pred"], precision_bgx=m2["precision"], recall_bgx=m2["recall"], f1_bgx=m2["f1"], f1_zone_bgx=m2["f1_zone"])
                det_rows.append(row)
        rule_step = P["mask"].to_numpy().astype(float)
        auc_scores = {**{k: Z.to_numpy() for k, Z in SCORES.items()}, "rules only (rule engine v1)": rule_step,
                      "ours (rules + detector)": np.where(rule_step > 0, 1e12, SCORES[MAIN_].to_numpy())}
        auc_rows = [dict(method=k, period=pname, auc_pr=step_auc(s, tmask, scope, pm))
                    for pname, pm in periods.items() for k, s in auc_scores.items()]

        # event table: typed truth events matched to the full method's predicted items
        m = match_events(PRED, truth)
        best = m.sort_values("overlap", ascending=False).drop_duplicates("t").set_index("t") if len(m) else pd.DataFrame()
        erows = []
        for j, t in truth.iterrows():
            row = dict(event_id=t.event_id, type=t.type, family=t.family, start=t.start, end=t.end, zones=t.zones,
                       n_zones=t.n_zones, mechanism=t.mechanism, period="test" if t.start >= D.SPLIT else "train",
                       detected=j in best.index)
            if j in best.index:
                pr = PRED.iloc[int(best.at[j, "p"])]
                row.update(item_id=pr.item_id, source=pr.source, feasible=pr.feasible, mv=pr.mv,
                           **{k: pr[k] for k in PRED.columns if k[:2] in ("q_", "f_") or k.startswith("fn_")})
                if fam_q and pr.source == "rule":
                    for fam, qf in fam_q.items():
                        row[f"lm_without_{fam}"] = qf.loc[pr.item_id].idxmax()
            erows.append(row)
        events = pd.DataFrame(erows)

        # predictions of the full method, with how they relate to the truth (for false-alarm analysis)
        fp = full_pred.copy()
        fp["source"] = np.where(fp.item_id.str.startswith("X"), "detector", "rule")
        fp["period"] = np.where(fp.start >= D.SPLIT, "test", "train")
        fp["in_scope"] = [bool(scope[self.index.searchsorted(r.start):max(self.index.searchsorted(r.end), self.index.searchsorted(r.start) + 1),
                                     [self.cols.index(z) for z in r.zones.split(",") if z in self.cols]].any()) for r in fp.itertuples()]
        mz = match_events(fp, truth)
        fp["match_zone"] = fp.index.isin(mz.p) if len(mz) else False
        te = np.maximum(truth.end_affected.to_numpy(), truth.end.to_numpy())
        fp["match_time_only"] = [bool(((truth.start.to_numpy() < r.end) & (te > r.start)).any()) for r in fp.itertuples()]
        fp["n_zones"] = fp.zones.str.count(",") + 1
        if len(det_only):
            fp = fp.merge(det_only[["item_id", "max_score"]], on="item_id", how="left")
        info = dict(seconds=time.time() - t0, n_rule_items=len(ev), n_detector_only=len(det_only),
                    gamma_main=GAM[MAIN_], main=MAIN_, n_truth=len(truth))
        return dict(detection=pd.DataFrame(det_rows), auc=pd.DataFrame(auc_rows), events=events, pred=fp, info=info)


# ------------------------------------------------------------------ attribution metrics (notebook side)
def fused(events, beta, abstain_low=("A1", "G1", "G2"), f_prefix="f_"):
    """Fusion eq. 16 on the event table, with the end model abstaining where q's arg max is a low-support class
    (D50; on injected data these classes are no longer rare, so the notebook also reports abstain_low=()).
    f_prefix 'fn_' uses the end model without detector features."""
    q = events[[f"q_{c}" for c in CL]].to_numpy(float)
    f = events[[f"{f_prefix}{c}" for c in CL]].to_numpy(float)
    feas = np.array([[c in str(s).split(",") for c in CL] for s in events.feasible])
    abstain = np.isin(np.array(CL)[q.argmax(1)], list(abstain_low))
    if "source" in events:
        # detector-only items carry a uniform q (the label model has no vote on them), whose arg max is just the first
        # class (A1): abstaining there would return that uniform q. As in NB3, they are fused without abstention.
        abstain &= (events["source"] == "rule").to_numpy()
    p = EM.fuse(q, f, feas, beta=beta, abstain=abstain)
    return p


def attribution_scores(y_true, probs=None, labels=None):
    """Macro-F1 over the typed classes, accuracy, and (with probabilities) ECE and multi-class Brier."""
    from sklearn.metrics import f1_score
    y_true = np.asarray(y_true)
    if probs is not None:
        labels = np.array(CL)[probs.argmax(1)]
    out = dict(n=len(y_true), macro_f1=f1_score(y_true, labels, labels=TYPED, average="macro", zero_division=0),
               accuracy=float((labels == y_true).mean()) if len(y_true) else np.nan)
    for c in TYPED:
        out[f"f1_{c}"] = f1_score(y_true, labels, labels=[c], average="macro", zero_division=0) if (y_true == c).any() else np.nan
    if probs is not None:
        conf = probs.max(1)
        out["ece"] = LM.ece(conf, labels == y_true)
        onehot = np.array([[c == y for c in CL] for y in y_true], dtype=float)
        out["brier"] = float(((probs - onehot) ** 2).sum(1).mean())
    return out


# ------------------------------------------------------------------ threshold sensitivity (guide ablation 6)
def rules_sensitivity(raw, data_inj, truth, clean, index, cols, eps=None, hold=None, tol_min=None):
    """Rule engine + label model only, with one threshold changed: epsilon (dead threshold), hold length (10-min
    systems) or the simultaneity tolerance tau. Returns rule-only detection metrics on both periods and the
    label-model attribution of the typed injected events. Module constants are restored afterwards."""
    old = (R1.EPS, dict(R1.HOLD_MIN_PTS), R1.TOL, R1.group_by_start.__defaults__)
    try:
        if eps is not None:
            R1.EPS = eps
        if hold is not None:
            R1.HOLD_MIN_PTS = {**R1.HOLD_MIN_PTS, "10min": hold}
        if tol_min is not None:
            R1.TOL = pd.Timedelta(minutes=tol_min)
            R1.group_by_start.__defaults__ = (R1.TOL,)
        res = R1.build_from_data(raw, data_inj)
    finally:
        R1.EPS, R1.HOLD_MIN_PTS, R1.TOL, R1.group_by_start.__defaults__ = old
    items = res["items"]
    votes = res["votes"].set_index("item_id")
    q = LM.DawidSkene().fit(votes, items, R1.RULE_KIND).q_
    q.index = items.item_id.values
    ev = items[(items.system == "south") & items.kind.isin(["dead", "fill"])].reset_index(drop=True)
    scope = clean.to_numpy() | _span_mask(truth, index, cols, "end_affected")
    fold = index >= D.SPLIT
    det = [dict(period=pn, **detection_metrics(ev[["start", "end", "zones"]], truth, scope, index, cols, pm))
           for pn, pm in (("train", ~fold), ("test", fold))]
    m = match_events(ev, truth)
    best = m.sort_values("overlap", ascending=False).drop_duplicates("t").set_index("t") if len(m) else pd.DataFrame()
    lab = []
    for j, t in truth.iterrows():
        if t.type in TYPED:
            lab.append(dict(type=t.type, period="test" if t.start >= D.SPLIT else "train",
                            label=q.loc[ev.item_id[int(best.at[j, "p"])]].idxmax() if j in best.index else "missed"))
    return pd.DataFrame(det), pd.DataFrame(lab)
