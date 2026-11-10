"""Downstream test (NB5; guide "Downstream forecasting evaluation", eq. 19-20): does type-aware cleaning change
forecasts and outage statistics?

Cleaning strategies (guide table), applied to the flagged zone-steps (dead, hold or linear-fill state inside a
qualifying zone run):
  S0 raw     - nothing changed.
  S1 naive   - every flagged run is linearly interpolated, artefacts and grid events alike (outages are erased).
  S2 typed   - flagged steps of items labelled A1-A3 are imputed with the expected profile x_hat (eq. 1) scaled to
               join the series at both edges; steps of items labelled G* are kept, flagged by an event indicator
               that the forecaster sees, and excluded from the training loss. Items labelled N, clock items and
               detector-only candidates are left as recorded. A4 is not re-aligned: timestamps stay as recorded (D11).
  S3 oracle  - S2 with the true types (injected data only).

Forecasters: a global LightGBM direct forecaster per horizon (1 h = 6 steps, 1 day = 144 steps) on the zone-scaled
series, and a model-free reference on the same cleaned series (persistence at 1 h, seasonal naive at 1 day). Rolling origin: every step is an origin. Scoring (guide): target steps in 1 Jan - 24 May 2024 that every
strategy treats as normal (no flagged state, no rule item, no detector-only candidate, not injected), against the
recorded values.
"""
import numpy as np
import pandas as pd

import detector as D

H = {"1 h": 6, "1 day": 144}
TEST_START, TEST_END = pd.Timestamp("2024-01-01"), pd.Timestamp("2024-05-25")
TRAIN_START_DAYS = 35                           # burn-in: x_hat needs 14 days, robust scores 21 more (as NB4)
ART, GRID = ("A1", "A2", "A3"), ("G1", "G2", "G3", "G4", "G5")
LGB_PARAMS = dict(objective="l2", n_estimators=500, learning_rate=0.05, num_leaves=63, min_child_samples=100,
                  subsample=0.7, subsample_freq=1, colsample_bytree=0.9, reg_lambda=1.0, verbose=-1)


# ------------------------------------------------------------------ masks
def rowmask(df, keep):
    """df & a per-row boolean vector, broadcast over the zones."""
    return df & np.broadcast_to(np.asarray(keep, bool)[:, None], df.shape)


def exp_panel(exp, P):
    """Expected values x_hat (eq. 1) as a wide frame with P's zone codes."""
    out = {}
    for c, e in exp.items():
        for z in e.columns:
            code = f"{D.CITY_SHORT[c]}{z.replace('zone', '')}"
            if code in P["x"].columns:
                out[code] = e[z]
    return pd.DataFrame(out).reindex(index=P["x"].index, columns=P["x"].columns)


def run_mask(P, zone_runs):
    """Zone-steps inside a qualifying rule zone run (dead, hold or linear fill) of P's system."""
    m = np.zeros(P["x"].shape, dtype=bool)
    idx, cols = P["x"].index, list(P["x"].columns)
    zr = zone_runs[(zone_runs.system == P["system"]) & zone_runs.kind.isin(["dead", "hold", "interp"])]
    for r in zr.itertuples():
        if r.code in cols:
            m[idx.searchsorted(pd.Timestamp(r.start)):idx.searchsorted(pd.Timestamp(r.end)), cols.index(r.code)] = True
    return pd.DataFrame(m, index=idx, columns=cols)


def span_mask(P, spans, end_col="end"):
    """Boolean frame covering each row's [start, end_col) on its zones (comma-separated codes)."""
    m = np.zeros(P["x"].shape, dtype=bool)
    idx, cols = P["x"].index, list(P["x"].columns)
    ci = {z: i for i, z in enumerate(cols)}
    for r in spans.itertuples():
        a, b = idx.searchsorted(pd.Timestamp(r.start)), idx.searchsorted(pd.Timestamp(getattr(r, end_col)))
        for z in str(r.zones).split(","):
            if z in ci:
                m[a:max(b, a + 1), ci[z]] = True
    return pd.DataFrame(m, index=idx, columns=cols)


def typed_masks(P, flagged, labelled):
    """labelled: rows (start, end, zones, label). Returns (artefact, grid) masks: flagged steps inside items of
    each family; artefact wins where an artefact and a grid item overlap (the fill part of a compound episode)."""
    art = span_mask(P, labelled[labelled.label.isin(ART)]) & flagged
    grid = span_mask(P, labelled[labelled.label.isin(GRID)]) & flagged & ~art
    return art, grid


# ------------------------------------------------------------------ cleaning
def _edge_ratio(x, xh, ok, i, step, n=3):
    """Median of x / x_hat over up to n valid steps next to position i (step = -1 left, +1 right)."""
    vals, j = [], i
    while len(vals) < n and 0 <= j < len(x):
        if ok[j] and xh[j] > 0 and np.isfinite(x[j]):
            vals.append(x[j] / xh[j])
        j += step
        if abs(j - i) > 36:
            break
    return float(np.median(vals)) if vals else np.nan


def clean(P, flagged, art, grid, xh, strategy):
    """Cleaned x (wide frame) and the event indicator (S2/S3). strategy in S0, S1, S2, S3."""
    x = P["x"].copy()
    ind = pd.DataFrame(False, index=x.index, columns=x.columns)
    if strategy == "S0":
        return x, ind
    if strategy == "S1":
        y = x.mask(flagged)
        return y.interpolate(limit_area="inside").ffill().bfill(), ind
    # S2 / S3: impute artefacts with x_hat scaled to join both edges; keep grid events, flag them
    ok_all = ~(flagged | x.isna())
    for z in x.columns:
        a_m = art[z].to_numpy()
        if not a_m.any():
            continue
        xv, hv, ok = x[z].to_numpy(float).copy(), xh[z].to_numpy(float), ok_all[z].to_numpy()
        for a, b in D.runs_of(a_m, max_gap=0, min_len=1):
            rl = _edge_ratio(xv, hv, ok, a - 1, -1)
            rr = _edge_ratio(xv, hv, ok, b + 1, +1)
            rl = rr if np.isnan(rl) else rl
            rr = rl if np.isnan(rr) else rr
            rl, rr = (1.0, 1.0) if np.isnan(rl) else (rl, rr)
            w = np.linspace(0, 1, b - a + 3)[1:-1]
            xv[a:b + 1] = np.nan_to_num(hv[a:b + 1], nan=0.0) * ((1 - w) * rl + w * rr)
        x[z] = xv
    return x, grid.copy()


# ------------------------------------------------------------------ forecasting
def zone_scale(P, normal):
    """Per-zone scale: median of the recorded x on normal steps before the test period."""
    pre = P["x"].index < TEST_START
    return P["x"][rowmask(normal, pre)].median().clip(lower=1e-6)


def design(y, ind, h, cal):
    """Long design matrix for horizon h: features at origin t (cleaned, scaled series), target y(t + h)."""
    p = 144
    rows = []
    for k, z in enumerate(y.columns):
        s = y[z]
        f = pd.DataFrame(index=y.index)
        for lag in (0, 1, 2, 5, 11):
            f[f"l{lag}"] = s.shift(lag)
        f["mean6"] = s.rolling(6, min_periods=1).mean()
        f["mean1d"] = s.rolling(p, min_periods=p // 4).mean()
        for d in (1, 2, 7):                          # same time of day as the target, d days earlier (<= origin)
            f[f"seas{d}"] = s.shift(d * p - h)
        f["event_now"] = ind[z].astype(float).to_numpy()
        f["event_recent"] = ind[z].astype(float).rolling(p, min_periods=1).max().to_numpy()
        ct = cal.shift(-h)                            # calendar of the target time
        for c in ("tod_sin", "tod_cos", "dow", "weekend", "ramadan", "eid", "holiday"):
            f[c] = ct[c].to_numpy()
        f["zone"] = k
        f["target"] = s.shift(-h)
        f["target_time"] = y.index + pd.Timedelta(minutes=10 * h)
        f["code"] = z
        rows.append(f)
    return pd.concat(rows)


FEATS = None


def fit_predict(y, ind, train_ok, h, cal, seed=0, backend="lightgbm"):
    """Global direct forecaster for horizon h. train_ok: wide bool frame of usable training targets (indexed by
    target time). Returns the forecast of y(t) made at t - h, as a wide frame indexed by target time."""
    global FEATS
    X = design(y, ind, h, cal)
    FEATS = [c for c in X.columns if c not in ("target", "target_time", "code")]
    tt = X["target_time"].to_numpy()
    tr = _lookup(train_ok, X["target_time"], X["code"]) & (pd.DatetimeIndex(tt) < TEST_START) & X["target"].notna().to_numpy()
    Xtr = np.ascontiguousarray(X.loc[tr, FEATS].to_numpy(np.float64))
    ytr = np.ascontiguousarray(X.loc[tr, "target"].to_numpy(np.float64))
    if backend == "lightgbm":
        import lightgbm as lgb
        m = lgb.LGBMRegressor(random_state=seed, n_jobs=-1, **LGB_PARAMS).fit(Xtr, ytr, categorical_feature=[FEATS.index("zone")])
    else:
        from sklearn.ensemble import HistGradientBoostingRegressor
        m = HistGradientBoostingRegressor(max_iter=500, learning_rate=0.05, random_state=seed).fit(Xtr, ytr)
    te = pd.DatetimeIndex(tt) >= TEST_START - pd.Timedelta(minutes=10 * h)
    pred = m.predict(np.ascontiguousarray(X.loc[te, FEATS].to_numpy(np.float64)))
    out = pd.DataFrame({"t": X.loc[te, "target_time"].to_numpy(), "code": X.loc[te, "code"].to_numpy(), "p": pred})
    return out.pivot(index="t", columns="code", values="p").reindex(columns=y.columns), int(tr.sum())


def _lookup(ok, times, codes):
    """ok.at[time, code] for aligned arrays (False where the time is outside ok's index)."""
    pos = ok.index.get_indexer(pd.DatetimeIndex(times))
    ci = {c: i for i, c in enumerate(ok.columns)}
    col = np.array([ci[c] for c in codes])
    arr = ok.to_numpy()
    res = np.zeros(len(pos), dtype=bool)
    good = pos >= 0
    res[good] = arr[pos[good], col[good]]
    return res


def naive(y, h):
    """Model-free reference on the cleaned series: persistence x_hat(t) = y(t - h) for the 1-h horizon,
    seasonal naive x_hat(t) = y(t - 1 day) for the day-ahead horizon."""
    return y.shift(h) if h < 144 else y.shift(144)


# ------------------------------------------------------------------ metrics
def mase_scale(P, normal):
    """Per-zone MASE scale (eq. 19): mean |x(t) - x(t - 1 day)| over training steps where both are normal."""
    x = P["x"]
    ok = rowmask(normal & normal.shift(144, fill_value=False), x.index < TEST_START)
    return (x - x.shift(144)).abs()[ok].mean()


def scores(err, scale):
    """err: long frame (code, e = x - forecast, x); scale: per-zone MASE scale. Returns MAE, RMSE (A), MASE, sMAPE (%)."""
    e = err["e"].to_numpy(); xv = err["x"].to_numpy(); s = err["code"].map(scale).to_numpy()
    f = xv - e
    return dict(n=len(e), MAE=float(np.mean(np.abs(e))), RMSE=float(np.sqrt(np.mean(e ** 2))),
                MASE=float(np.mean(np.abs(e) / s)),
                sMAPE=float(100 * np.mean(2 * np.abs(e) / np.clip(np.abs(xv) + np.abs(f), 1e-9, None))))


def dm_test(d, lag):
    """Diebold-Mariano (eq. 20) on a loss-differential series d (time order), Newey-West HAC variance with
    Bartlett weights up to `lag`. Returns (DM statistic, two-sided normal p)."""
    from scipy.stats import norm
    d = np.asarray(d, float); d = d[np.isfinite(d)]
    n = len(d)
    if n < 10:
        return np.nan, np.nan
    u = d - d.mean()
    v = u @ u / n
    for k in range(1, min(lag, n - 1) + 1):
        v += 2 * (1 - k / (lag + 1)) * (u[k:] @ u[:-k]) / n
    stat = d.mean() / np.sqrt(v / n) if v > 0 else np.nan
    return float(stat), float(2 * norm.sf(abs(stat))) if np.isfinite(stat) else np.nan


# ------------------------------------------------------------------ one dataset
def forecast_eval(P, flagged, masks, normal, score_ok, xh, seed=0, models=("LightGBM", "naive"), log=print):
    """Forecast every strategy and score it.
    masks: {strategy: (artefact mask, grid mask)} (ignored for S0 and S1); normal: zone-steps used for the scales;
    score_ok: zone-steps that may be scored (normal under every strategy). Returns (score rows, per-step losses).
    Subsets: all scored test steps, and those whose zone had a flagged step in the 2 days before (where the history
    the forecaster reads contains anomalies, so cleaning can matter)."""
    import time
    idx = P["x"].index
    cal = D.calendar(idx)
    scale, ms = zone_scale(P, normal), mase_scale(P, normal)
    burn = idx >= idx[0] + pd.Timedelta(days=TRAIN_START_DAYS)
    test = (idx >= TEST_START) & (idx < TEST_END)
    sc = rowmask(score_ok, test)
    recent = flagged.astype(float).rolling(288, min_periods=1).max().shift(1).fillna(0).astype(bool)
    subsets = {"all": sc, "after anomaly (2 days)": sc & recent}
    rows, loss = [], {}
    for S, (art, grid) in masks.items():
        y, ind = clean(P, flagged, art, grid, xh, S)
        train_ok = rowmask(y.notna() & ~ind, burn)              # S2/S3: grid events excluded from the loss
        for hname, h in H.items():
            for model in models:
                t0 = time.time()
                if model == "LightGBM":
                    f, ntr = fit_predict(y / scale, ind, train_ok, h, cal, seed)
                    f = (f * scale).reindex(idx)
                else:
                    f, ntr = naive(y, h), 0
                e = P["x"] - f
                ev, xv, cols = e.to_numpy(float), P["x"].to_numpy(float), np.array(P["x"].columns)
                for sub, m in subsets.items():
                    ti, zi = np.nonzero(m.to_numpy() & np.isfinite(ev) & np.isfinite(xv))
                    long = pd.DataFrame(dict(code=cols[zi], e=ev[ti, zi], x=xv[ti, zi]))
                    rows.append(dict(strategy=S, model=model, horizon=hname, subset=sub, n_train=ntr, **scores(long, ms)))
                    loss[(S, model, hname, sub)] = (e.where(m).abs() / ms).sum(axis=1, min_count=1)   # per-time-step summed scaled loss
                log(f"  {S} {model} {hname}: {time.time() - t0:.0f} s")
    return pd.DataFrame(rows), loss


def dm_table(loss, pairs=(("S1", "S2"), ("S0", "S2"), ("S2", "S3"))):
    """DM tests on the per-time-step loss (scaled absolute error summed over the scored zones, so that its mean is
    proportional to the pooled MASE difference); d = L(first) - L(second) (> 0: second is better)."""
    rows = []
    keys = {k[1:] for k in loss}
    for model, hname, sub in sorted(keys):
        for a, b in pairs:
            if (a, model, hname, sub) not in loss or (b, model, hname, sub) not in loss:
                continue
            d = (loss[(a, model, hname, sub)] - loss[(b, model, hname, sub)]).dropna()
            stat, p = dm_test(d.to_numpy(), lag=H[hname])
            rows.append(dict(model=model, horizon=hname, subset=sub, comparison=f"{a} vs {b}", mean_loss_diff=float(d.mean()),
                             share_steps_second_better=float((d > 0).mean()), n_steps=len(d), DM=stat, p=p))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ outage statistics
def outage_stats(P, dead_mask, step_h=1 / 6):
    """Zone-hours and number of runs (>= 3 steps) of a dead/outage mask, per zone and in total."""
    rows = []
    for z in dead_mask.columns:
        m = dead_mask[z].to_numpy()
        rows.append(dict(code=z, zone_hours=float(m.sum() * step_h), outages=len(D.runs_of(m, max_gap=0, min_len=3))))
    df = pd.DataFrame(rows)
    return df, dict(zone_hours=float(df.zone_hours.sum()), outages=int(df.outages.sum()))
