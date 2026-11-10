"""Transfer test on the UCI Tetouan dataset (NB6; guide "Generalisation to Tetouan", RQ5, Table 9; D68-D70).

Tetouan: 3 distribution zones of one city, 2017, 10-min steps, power in kW (Salam & El Hibaoui 2018).

Frozen from the Morocco study (no re-tuning, nothing chosen on Tetouan):
  - every rule threshold (rules_v1), the item and episode definitions;
  - the label model's parameters (fitted on the Morocco votes, applied with DawidSkene.predict);
  - the detector architectures and training hyper-parameters (TCN-GAT, its no-graph TCN ablation, LightGBM);
  - each detector's event formation (smoothing w, threshold percentile q, merge gap) from dev_selection.json;
  - the injected signatures, rates and the evaluation code (benchmark.detection_metrics, eq. 17).
Re-estimated from Tetouan's own unlabelled data, as the method prescribes for any new system:
  - the expected value x_hat (eq. 1) and the robust-score scales;
  - the predictor weights (trained on Tetouan's rule-clean steps, cross-fitted in two folds split at 1 Jul 2017);
  - the threshold gamma, as the frozen q-th percentile of Tetouan's own rule-negative zone-steps.
Single-city consequences (D69): the city and region parts of the hierarchy coincide (u = 0); the graph has only
same-city edges; R1 (multi-city zero) and R7 (regional outage) cannot fire; G1 cannot be distinguished from G2 and is
not injected; multi-city injected types become city-wide.
"""
from pathlib import Path

import numpy as np
import pandas as pd

import rules_v0 as R0
import rules_v1 as R1
import detector as D
import end_model as EM
import graph_model as G
import benchmark as B
import inject as INJ
import label_model as LM

CITY = SYSTEM = "Tetouan"
SPLIT_T = pd.Timestamp("2017-07-01")
TYPES_T = ["A1", "A2", "A3", "G2", "G3", "G4", "U_SHOCK", "U_PARTIAL"]      # G1 = G2 in a single city
TYPED_T = ["A1", "A2", "A3", "G2", "G3", "G4"]
V_OWN = B.V_TCN_MS + " (own tuned event formation)"
DETECTORS = [B.V_GAT, B.V_TCN_MS, V_OWN, B.V_LGB, "STL + MAD", "Isolation Forest", "LOF"]
EMPTY3 = pd.DataFrame(columns=["start", "end", "zones"])
ITEM_COLS = list(pd.read_csv(Path(__file__).resolve().parents[1] / "results" / "catalogue_v1" / "items.csv", nrows=0).columns)


def register():
    """Make the rule engine and the detector aware of the Tetouan system (no threshold changes)."""
    R0.STEP[CITY] = "10min"                 # rules_v1 uses the same dict object
    R1.SYSTEM[CITY] = SYSTEM
    R1.CITY_SHORT[CITY] = "T"
    D.SPLIT = SPLIT_T                       # cross-fitting boundary inside 2017 (read at call time by graph_model)


def load(path):
    """raw = {city: frame with DateTime + zone1..3}, data = regularised frame, weather (not used by the method)."""
    df = pd.read_csv(path)
    df["DateTime"] = pd.to_datetime(df["DateTime"], format="%m/%d/%Y %H:%M")
    zc = [c for c in df.columns if c.startswith("Zone")]
    raw_df = df[["DateTime"] + zc].rename(columns={c: f"zone{i + 1}" for i, c in enumerate(zc)})
    weather = df.set_index("DateTime").drop(columns=zc)
    return {CITY: raw_df}, {CITY: R0.regularise(CITY, raw_df)}, weather


def frozen_label_model(xlsx):
    """The Morocco label model (as NB2: all items, constrained Dawid-Skene, 20 restarts)."""
    res = R1.build(xlsx)
    ds = LM.DawidSkene().fit(res["votes"].set_index("item_id"), res["items"], R1.RULE_KIND)
    return ds, res


def settings(sel):
    """Event formation per detector, frozen from the Morocco development selection (D60)."""
    st = {k: {**B.DEFAULT_SETTING, **v} for k, v in sel["settings"].items()}
    st[B.V_TCN_MS] = st[sel["main"]]                                   # ablation: the main detector's setting
    st[V_OWN] = dict(w=48, q=99.9, gap=12)                             # its own development setting (D62)
    return st


class Transfer:
    def __init__(self, raw, data, ds, sel, log=print):
        self.raw, self.ds, self.log = raw, ds, log
        self.st = settings(sel)
        self.real = self.analyse_rules(data)
        self.P = self.real["P"]
        self.clean = B.clean_region(self.P, None)
        self.index, self.cols = self.P["rho"].index, list(self.P["rho"].columns)
        self.models = {}
        self.background = {}

    # ------------------------------------------------------------ predictors (trained once on the real series)
    def fit_predictors(self, cfg, device, models_dir, log=True):
        import pickle, time
        models_dir.mkdir(parents=True, exist_ok=True)
        for name, fname, graph in (("TCN-GAT", "tcn_gat.pt", True), ("TCN", "tcn.pt", False)):
            f = models_dir / fname
            if f.exists():
                self.models[name] = G.load_models(f, self.P, device=device); self.log(f"{name} loaded from {f}")
            else:
                t = time.time()
                self.models[name], h = G.fit_graph_models(self.P, graph=graph, cfg=cfg, device=device, log=log)
                G.save_models(self.models[name], f, cfg); h.to_csv(models_dir / f"{f.stem}_history.csv", index=False)
                self.log(f"{name} trained in {time.time() - t:.0f} s")
        f = models_dir / "lightgbm_forecast.pkl"
        if f.exists():
            self.models["LGB"] = pickle.load(open(f, "rb"))
        else:
            self.models["LGB"] = D.fit_rho_models(self.P, "forecast", backend="lightgbm")
            pickle.dump(self.models["LGB"], open(f, "wb"))

    def predictions(self, P):
        return {"TCN-GAT": G.apply_graph_models(P, self.models["TCN-GAT"]), "TCN": G.apply_graph_models(P, self.models["TCN"]),
                "LGB": D.apply_rho_models(P, self.models["LGB"], "forecast")}

    # ------------------------------------------------------------ one dataset
    def analyse_rules(self, data):
        r = R1.build_from_data(self.raw, data)
        # the frozen item schema: a clean series has only clock items, which lack the dead/fill feature columns
        items = r["items"].reindex(columns=list(dict.fromkeys(ITEM_COLS + list(r["items"].columns))))
        votes = r["votes"].set_index("item_id")
        q = self.ds.predict(votes, items, R1.RULE_KIND); q.index = items.item_id.values
        mv = LM.majority_vote(votes, items); mv.index = items.item_id.values
        items = items.assign(label=q.idxmax(axis=1).reindex(items.item_id).values,
                             confidence=q.max(axis=1).reindex(items.item_id).values,
                             mv=mv.reindex(items.item_id).values)
        P = D.build_panel(r["data"], r["exp"], r["masks"], SYSTEM)
        ev = items[(items.system == SYSTEM) & items.kind.isin(["dead", "fill"])].reset_index(drop=True)
        return dict(r=r, items=items, q=q, P=P, ev=ev, zr=r["zone_runs"], unseen=dict(self.ds.unseen_))

    def scores(self, P, pred, seed=0):
        Z = {}
        for v, k in ((B.V_GAT, "TCN-GAT"), (B.V_TCN_MS, "TCN"), (B.V_LGB, "LGB")):
            Z[v] = D.zone_max_score(P, D.level_scores(P, P["rho"] - pred[k]))
        Z[V_OWN] = Z[B.V_TCN_MS]
        Z["STL + MAD"] = B.flat_score(P, D.stl_residual(P, jumps=True))
        Z.update(B.iso_lof_scores(P, seed=seed))
        return Z

    def detect(self, out):
        """Smoothed scores, gamma and detections (alone) per detector, and the main detector's detector-only items."""
        P, Z0 = out["P"], out["Z0"]
        S, GAM, DET = {}, {}, {}
        empty = pd.DataFrame(columns=["system", "code", "start", "end"])
        for k in DETECTORS:
            st = self.st[k]
            S[k] = B.smooth_score(Z0[k], st["w"])
            GAM[k] = B.gamma_of(P, S[k], st["q"])
            DET[k] = EM.detector_items(P, S[k], GAM[k], empty, max_gap=st["gap"])
        m = self.st[B.V_GAT]
        det_only = EM.detector_items(P, S[B.V_GAT], GAM[B.V_GAT], out["zr"], max_gap=m["gap"])
        return S, GAM, DET, det_only

    def analyse(self, data, seed=0):
        out = self.analyse_rules(data)
        out["Z0"] = self.scores(out["P"], self.predictions(out["P"]), seed)
        out["S"], out["GAM"], out["DET"], out["det_only"] = self.detect(out)
        return out

    def set_background(self, real):
        bg = {k: d[["start", "end", "zones"]].reset_index(drop=True) if len(d) else EMPTY3 for k, d in real["DET"].items()}
        do = real["det_only"]
        bg["ours (rules + detector)"] = do[["start", "end", "zones"]].reset_index(drop=True) if len(do) else EMPTY3
        rl = real["ev"]
        bg["rules only (rule engine v1)"] = rl[["start", "end", "zones"]].reset_index(drop=True) if len(rl) else EMPTY3
        self.background = bg

    # ------------------------------------------------------------ metrics on one injected dataset
    def metrics(self, out, truth):
        idx, cols = self.index, self.cols
        pm = np.ones(len(idx), dtype=bool)                       # whole year: nothing was tuned on Tetouan
        tmask = B._span_mask(truth, idx, cols, "end")
        scope = self.clean.to_numpy() | B._span_mask(truth, idx, cols, "end_affected")
        ev, do = out["ev"], out["det_only"]
        rule_pred = ev[["start", "end", "zones"]].reset_index(drop=True) if len(ev) else EMPTY3
        full = pd.concat([rule_pred, do[["start", "end", "zones"]] if len(do) else None], ignore_index=True)
        methods = {"rules only (rule engine v1)": rule_pred, "ours (rules + detector)": full}
        for k, d in out["DET"].items():
            methods[k] = d[["start", "end", "zones"]].reset_index(drop=True) if len(d) else EMPTY3
        rows = []
        for k, pr in methods.items():
            m = B.detection_metrics(pr, truth, scope, idx, cols, pm)
            bg = self.background.get(k)
            if bg is not None and len(pr) and len(bg):
                hit = B.match_events(pr, bg.assign(end_affected=bg.end), need_zone=True)
                m2 = B.detection_metrics(pr.drop(index=set(hit.p)).reset_index(drop=True), truth, scope, idx, cols, pm)
            else:
                m2 = m
            rows.append(dict(method=k, gamma=out["GAM"].get(k, np.nan), **m, f1_bgx=m2["f1"], precision_bgx=m2["precision"],
                             n_pred_bgx=m2["n_pred"], f1_zone_bgx=m2["f1_zone"]))
        det = pd.DataFrame(rows)
        rule_step = out["P"]["mask"].to_numpy().astype(float)
        auc = {k: B.step_auc(s.to_numpy(), tmask, scope, pm) for k, s in out["S"].items()}
        auc["rules only (rule engine v1)"] = B.step_auc(rule_step, tmask, scope, pm)
        auc["ours (rules + detector)"] = B.step_auc(np.where(rule_step > 0, 1e12, out["S"][B.V_GAT].to_numpy()), tmask, scope, pm)
        det["auc_pr"] = det.method.map(auc)
        # attribution: typed injected events -> best zone-matched rule item -> frozen label model / majority vote
        mt = B.match_events(rule_pred, truth) if len(rule_pred) else pd.DataFrame(columns=["p", "t", "overlap"])
        best = mt.sort_values("overlap", ascending=False).drop_duplicates("t").set_index("t") if len(mt) else pd.DataFrame()
        att = []
        for j, t in truth.iterrows():
            if t.type not in TYPED_T:
                continue
            row = dict(event_id=t.event_id, type=t.type, n_zones=t.n_zones, mechanism=t.mechanism, detected=j in best.index)
            if j in best.index:
                it = ev.iloc[int(best.at[j, "p"])]
                row.update(item_id=it.item_id, kind=it.kind, label=it.label, confidence=it.confidence, mv=it.mv,
                           **{f"q_{c}": out["q"].at[it.item_id, c] for c in out["q"].columns})
            att.append(row)
        return det, pd.DataFrame(att)


def macro_f1(y, yhat, classes=TYPED_T):
    from sklearn.metrics import f1_score
    y, yhat = np.asarray(y), np.asarray(yhat)
    present = [c for c in classes if (y == c).any()]
    return float(f1_score(y, yhat, labels=present, average="macro", zero_division=0)) if len(y) else np.nan
