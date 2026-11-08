"""
end_model.py - detector-only candidates, normal windows, item features, end model (guide eq. 12) and fusion (eq. 16).

Items scored by the end model ("event items"):
  rule items      - dead and fill items of rule engine v1, with soft targets q from the label model (NB2)
  normal windows  - random windows with no rule item and no detector flag in their zones; target N (D35)
  detector items  - runs of detector-flagged zone-steps that no rule item covers (coverage beyond the rules);
                    unlabelled, predicted only
Clock and transfer items are day-level and rule-defined; they keep their label-model q (D46).

End model: soft-label classifier over EVENT_CLASSES trained on rows expanded per class with weight q_i(y)
(guide eq. 12), out-of-fold by episode groups (D47). Two learners: LightGBM (main) and a 2-layer MLP (torch).
Fusion (eq. 16): p ~ q^beta * f^(1 - beta) on each rule item's feasible set; beta = 0.5 until NB4 tunes it.
"""
import numpy as np
import pandas as pd

EVENT_CLASSES = ["A1", "A2", "A3", "G1", "G2", "G3", "G4", "N"]
TOL = pd.Timedelta("10min")


# ------------------------------------------------------------------ detector-only candidates
def detector_items(P, Zmax, gamma, zone_runs, min_steps=3, max_gap=1, spill_steps=None):
    """Runs of Zmax > gamma per zone that do not touch a rule zone-run of the same zone, extended on both sides
    by spill_steps (half the support of the widest phase-aligned wavelet band, which still responds around an
    event), grouped across zones by start within 10 min (as in rule engine v1)."""
    from detector import runs_of, SPILL_STEPS
    spill_steps = SPILL_STEPS if spill_steps is None else spill_steps
    idx = P["rho"].index
    step = pd.Timedelta(minutes=P["step"])
    zr = zone_runs[zone_runs.system == P["system"]]
    recs = []
    for z in P["rho"].columns:
        flag = (Zmax[z] > gamma).to_numpy()
        busy = np.zeros(len(idx), dtype=bool)
        for r in zr[zr.code == z].itertuples():
            a = max(0, idx.searchsorted(r.start) - spill_steps)
            b = idx.searchsorted(r.end) + spill_steps
            busy[a:b] = True
        for a, b in runs_of(flag, max_gap=max_gap, min_len=min_steps):
            if busy[a:b + 1].any():
                continue
            recs.append(dict(system=P["system"], code=z, city=P["city"][z], start=idx[a], end=idx[b] + step,
                             steps=b - a + 1, max_score=float(np.nanmax(Zmax[z].to_numpy()[a:b + 1]))))
    if not recs:
        return pd.DataFrame()
    r = pd.DataFrame(recs).sort_values("start").reset_index(drop=True)
    gid, first, ids = -1, None, []
    for s in r.start:
        if first is None or s - first > TOL:
            gid, first = gid + 1, s
        ids.append(gid)
    r["group"] = ids
    out = (r.groupby("group").agg(start=("start", "min"), end=("end", "max"), zones=("code", lambda c: ",".join(sorted(c))),
                                  n_zones=("code", "nunique"), cities=("city", lambda c: "+".join(sorted(set(c)))),
                                  n_cities=("city", "nunique"), max_score=("max_score", "max"))
           .reset_index(drop=True))
    out["system"] = P["system"]
    out["kind"] = "detector"
    out["duration_h"] = (out.end - out.start).dt.total_seconds() / 3600
    return out


def normal_windows(P, busy_any, n, rng, durations_h, zone_patterns):
    """Random windows whose zones have no rule item, no detector flag and no NaN during the window (+-1 h)."""
    idx = P["rho"].index
    step = pd.Timedelta(minutes=P["step"])
    zones = list(P["rho"].columns)
    cities = sorted(set(P["city"].values()))
    out, tries = [], 0
    while len(out) < n and tries < 200 * n:
        tries += 1
        dur = pd.Timedelta(hours=float(rng.choice(durations_h)))
        pat = rng.choice(zone_patterns)
        if pat == "zone":
            zs = [zones[rng.integers(len(zones))]]
        elif pat == "city":
            c = cities[rng.integers(len(cities))]
            zs = [z for z in zones if P["city"][z] == c]
        else:
            zs = zones
        a = int(rng.integers(30 * P["per_day"], len(idx) - int(dur / step) - P["per_day"]))
        b = a + max(1, int(dur / step))
        pad = int(pd.Timedelta(hours=1) / step)
        if busy_any[zs].iloc[max(0, a - pad):b + pad].to_numpy().any():
            continue
        out.append(dict(system=P["system"], kind="normal", start=idx[a], end=idx[b], zones=",".join(sorted(zs)),
                        n_zones=len(zs), cities="+".join(sorted(set(P["city"][z] for z in zs))),
                        n_cities=len(set(P["city"][z] for z in zs)), duration_h=(idx[b] - idx[a]).total_seconds() / 3600))
    return pd.DataFrame(out)


# ------------------------------------------------------------------ features
def item_features(P, S, Snb, items, zone_runs, episode_info):
    """One feature row per item of system P. S: level scores (band -> level -> frame/series) of the main residual;
    Snb: zone scores of the nowcast residual (raw band, v level) or None; episode_info: item_id -> dict."""
    idx = P["rho"].index
    step = pd.Timedelta(minutes=P["step"])
    rho = P["rho"]
    st = P["states"]
    city = P["city"]
    ncity = {c: sum(1 for z in rho.columns if city[z] == c) for c in set(city.values())}
    zr = zone_runs[zone_runs.system == P["system"]]
    fill_starts = set(zip(zr[zr.kind != "dead"].code, zr[zr.kind != "dead"].start))
    fill_ends = set(zip(zr[zr.kind != "dead"].code, zr[zr.kind != "dead"].end))
    rows = []
    for it in items.itertuples():
        zs = it.zones.split(",")
        cs = sorted(set(city[z] for z in zs))
        a, b = idx.searchsorted(it.start), max(idx.searchsorted(it.end), idx.searchsorted(it.start) + 1)
        R = rho[zs].iloc[a:b]
        zm = R.mean(axis=1)
        n3, n6 = max(1, int(pd.Timedelta("30min") / step)), max(1, int(pd.Timedelta("60min") / step))
        pre = rho[zs].iloc[max(0, a - n3):a].mean(axis=1).mean()
        post = rho[zs].iloc[b:b + n3].mean(axis=1).mean()
        peak = rho[zs].iloc[b:b + n6].mean(axis=1).max()
        x = P["x"][zs].iloc[a:b]
        f = dict(item_id=it.item_id, duration_h=it.duration_h, n_zones=len(zs), n_cities=len(cs),
                 frac_zones=max(sum(1 for z in zs if city[z] == c) / ncity[c] for c in cs), multi_city=int(len(cs) >= 2),
                 share_zero=float(st["zero"][zs].iloc[a:b].to_numpy().mean()),
                 share_dead=float(st["dead"][zs].iloc[a:b].to_numpy().mean()),
                 share_hold=float(st["hold"][zs].iloc[a:b].to_numpy().mean()),
                 share_interp=float(st["interp"][zs].iloc[a:b].to_numpy().mean()),
                 share_missing=float(R.isna().to_numpy().mean()),
                 share_flat=float((x.diff().iloc[1:] == 0).to_numpy().mean()) if len(x) > 1 else np.nan,
                 rho_mean=float(zm.mean()), rho_min=float(zm.min()), rho_std=float(zm.std()) if len(zm) > 1 else 0.0,
                 pre_rho=float(pre), post_rho=float(post), post_peak=float(peak),
                 start_hour=it.start.hour + it.start.minute / 60, weekday=it.start.dayofweek, weekend=int(it.start.dayofweek >= 5),
                 preceded_by_fill=int(any((z, it.start) in fill_ends for z in zs)),
                 followed_by_fill=int(any((z, it.end) in fill_starts for z in zs)))
        f["start_sin"], f["start_cos"] = np.sin(2 * np.pi * f["start_hour"] / 24), np.cos(2 * np.pi * f["start_hour"] / 24)
        ep = episode_info.get(it.item_id, {})
        f.update(ep_n_items=ep.get("n_items", 1), ep_has_multizone_fill=ep.get("multizone_fill", 0),
                 ep_has_multicity_dead=ep.get("multicity_dead", 0), ep_duration_h=ep.get("duration_h", it.duration_h))
        # detector features
        raw = S["raw"]
        g = raw["g"].iloc[a:b]
        u = raw["u"][cs].iloc[a:b]
        v = raw["v"][zs].iloc[a:b]
        f.update(det_g_max=float(np.nanmax(g.to_numpy())) if g.notna().any() else np.nan, det_g_mean=float(g.mean()),
                 det_u_max=float(np.nanmax(u.to_numpy())) if u.notna().any().any() else np.nan, det_u_mean=float(u.mean().mean()),
                 det_v_max=float(np.nanmax(v.to_numpy())) if v.notna().any().any() else np.nan, det_v_mean=float(v.mean().mean()))
        top = np.nan_to_num(np.array([f["det_g_max"], f["det_u_max"], f["det_v_max"]]), nan=-np.inf)
        f["det_top_g"], f["det_top_u"], f["det_top_v"] = [int(i == int(np.argmax(top))) for i in range(3)]
        for bnd in [k for k in S if k != "raw"]:
            vals = [S[bnd]["g"].iloc[a:b].to_numpy(), S[bnd]["u"][cs].iloc[a:b].to_numpy().ravel(), S[bnd]["v"][zs].iloc[a:b].to_numpy().ravel()]
            allv = np.concatenate([np.atleast_1d(v_) for v_ in vals])
            f[f"det_{bnd}_max"] = float(np.nanmax(allv)) if np.isfinite(allv).any() else np.nan
        if Snb is not None:
            nb = Snb[zs].iloc[a:b]
            f["det_nb_max"] = float(np.nanmax(nb.to_numpy())) if nb.notna().any().any() else np.nan
        rows.append(f)
    return pd.DataFrame(rows)


def episode_info(items):
    """item_id -> episode context for rule items (from rule engine v1's episodes)."""
    info = {}
    ev = items[items.kind.isin(["dead", "fill"]) & items.episode.notna()]
    for ep, g in ev.groupby("episode"):
        d = dict(n_items=len(g), multizone_fill=int(((g.kind == "fill") & (g.n_zones >= 2)).any()),
                 multicity_dead=int(((g.kind == "dead") & (g.n_cities >= 2)).any()),
                 duration_h=float((g.end.max() - g.start.min()).total_seconds() / 3600))
        for i in g.item_id:
            info[i] = d
    return info


# ------------------------------------------------------------------ learners
def expand_soft(X, Q, classes, wmin=1e-3):
    """Guide eq. 12 via row expansion: one row per (item, class) with weight q_i(y)."""
    rows, ys, ws = [], [], []
    for i in range(len(X)):
        for k, c in enumerate(classes):
            if Q[i, k] > wmin:
                rows.append(i); ys.append(k); ws.append(Q[i, k])
    return X[np.array(rows)], np.array(ys), np.array(ws)


def make_gbdt(backend="lightgbm", seed=0):
    if backend == "lightgbm":
        import lightgbm as lgb
        return lgb.LGBMClassifier(objective="multiclass", n_estimators=300, learning_rate=0.05, num_leaves=15,
                                  min_child_samples=5, subsample=0.8, subsample_freq=1, colsample_bytree=0.8,
                                  reg_lambda=1.0, verbose=-1, random_state=seed, n_jobs=2)
    from sklearn.ensemble import HistGradientBoostingClassifier
    return HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=5,
                                          l2_regularization=1.0, random_state=seed)


def fit_predict_gbdt(Xtr, Qtr, Xte, classes, backend="lightgbm", seed=0):
    Xe, ye, we = expand_soft(np.ascontiguousarray(Xtr, dtype=np.float64), Qtr, classes)
    m = make_gbdt(backend, seed).fit(Xe, ye, sample_weight=we)
    pr = m.predict_proba(np.ascontiguousarray(Xte, dtype=np.float64))
    out = np.zeros((len(Xte), len(classes)))
    out[:, m.classes_.astype(int)] = pr
    return out


def fit_predict_mlp(Xtr, Qtr, Xte, classes, seed=0, hidden=64, epochs=400, lr=3e-3, wd=1e-3):
    """2-layer MLP with soft cross-entropy (torch). Median imputation + missing indicators, standardisation."""
    import torch
    torch.manual_seed(seed)
    med = np.nanmedian(Xtr, axis=0)
    med = np.where(np.isfinite(med), med, 0.0)

    def prep(X):
        miss = np.isnan(X).astype(float)
        Xi = np.where(np.isnan(X), med, X)
        return np.hstack([Xi, miss])
    A, B = prep(Xtr), prep(Xte)
    mu, sd = A.mean(axis=0), A.std(axis=0) + 1e-6
    A, B = (A - mu) / sd, (B - mu) / sd
    net = torch.nn.Sequential(torch.nn.Linear(A.shape[1], hidden), torch.nn.ReLU(), torch.nn.Dropout(0.1),
                              torch.nn.Linear(hidden, hidden), torch.nn.ReLU(), torch.nn.Linear(hidden, len(classes)))
    opt = torch.optim.AdamW(net.parameters(), lr=lr, weight_decay=wd)
    xa, qa = torch.tensor(A, dtype=torch.float32), torch.tensor(Qtr, dtype=torch.float32)
    for _ in range(epochs):
        net.train(); opt.zero_grad()
        loss = -(qa * torch.log_softmax(net(xa), dim=1)).sum(dim=1).mean()
        loss.backward(); opt.step()
    net.eval()
    with torch.no_grad():
        return torch.softmax(net(torch.tensor(B, dtype=torch.float32)), dim=1).numpy()


def oof_predict(X, Q, groups, learner, n_splits=5, seed=0, **kw):
    """Out-of-fold predictions: no item is scored by a model that saw its own (or its episode's) target."""
    from sklearn.model_selection import GroupKFold
    out = np.zeros_like(Q)
    for tr, te in GroupKFold(n_splits=n_splits).split(X, groups=groups):
        out[te] = learner(X[tr], Q[tr], X[te], EVENT_CLASSES, seed=seed, **kw)
    return out


def fuse(q, f, feasible, beta=0.5, eps=1e-6, abstain=None):
    """Guide eq. 16, product of experts on the feasible set: p ~ q^beta * f^(1-beta).
    abstain: boolean per item; where True the end model abstains and p = q on the feasible set (D50)."""
    p = np.exp(beta * np.log(np.clip(q, eps, 1)) + (1 - beta) * np.log(np.clip(f, eps, 1))) * feasible
    p = p / p.sum(axis=1, keepdims=True)
    if abstain is not None and np.any(abstain):
        qq = q * feasible
        p[abstain] = qq[abstain] / qq[abstain].sum(axis=1, keepdims=True)
    return p


def low_support_classes(Q, classes, min_items=3.0):
    """Classes whose total training mass (sum of q) is below min_items: out of fold the end model cannot learn them."""
    mass = Q.sum(axis=0)
    return [c for c, m in zip(classes, mass) if m < min_items]


def soft_ce(q, f, eps=1e-9):
    return float(-(q * np.log(np.clip(f, eps, 1))).sum(axis=1).mean())
