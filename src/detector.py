"""
detector.py - multi-scale residual detector with a region / city / zone hierarchy (guide eq. 13-15).

Pipeline per system (south = L, B, F with 15 zones on one 10-min logger timeline; Marrakech = 2 zones, 30 min):
  1. rho = x / x_hat (eq. 2), clipped to [0, 3]. Mask M = dead | hold | interp (rule engine v1 states) | NaN.
  2. Predict rho for every zone with LightGBM (Huber objective, delta 0.1: the guide's masked Huber loss and its
     "cheaper fallback" nowcaster; D39), trained only on unmasked steps, two-fold cross-fitted in time so every
     prediction is out of sample (D41). Two predictors (D40):
       "forecast" F: the zone's own past (masked: flagged steps become NaN) + calendar. No neighbour information,
                     so a shock shared by all zones stays in every zone's residual.
       "nowcast"  N: F's features + the CURRENT rho of every other zone of the system (guide eq. 13,
                     leave-one-zone-out). A shared shock is partly explained by the neighbours.
  3. Residual e = rho - rho_hat. Multi-scale: MODWT with the LA(8) filter (PyWavelets 'sym4'), J = 4 levels (D42),
     pyramid algorithm on the residual, then PHASE-ALIGNED: each band is shifted back by its group delay,
     measured numerically from the band's impulse response (Percival & Walden's practice for LA filters).
     Unaligned causal coefficients smeared events up to ~18 h forward in time (detector flags on normal data after
     events, and an inflated threshold). The catalogue is retrospective, so the non-causal alignment is fine.
     Bands at 10 min: W1 20-40 min, W2 40-80 min, W3 80-160 min, W4 160-320 min, V4 smooth (> 320 min).
  4. Hierarchy (eq. 14) per band: g = median over the system's zones, u_c = median over city c - g,
     v_z = e_z - g - u_c(z).
  5. Level scores (eq. 15): robust z-score of |level| against a trailing 28-day median and MAD computed on
     steps that are clean at that level (no zone of the region / city / zone flagged by the rules), excluding
     structural zeros of the hierarchy (D51).

Dependencies: numpy, pandas, lightgbm, PyWavelets, statsmodels (STL baseline, Ljung-Box).
"""
import os
import warnings

import numpy as np
import pandas as pd
import pywt
import lightgbm as lgb

os.environ.setdefault("LOKY_MAX_CPU_COUNT", str(os.cpu_count() or 4))
warnings.filterwarnings("ignore", message="X does not have valid feature names")

CITY_SHORT = {"Laayoune": "L", "Boujdour": "B", "Foum eloued": "F", "Marrakech": "M"}
STEP_MIN = {"south": 10, "Marrakech": 30}
SPLIT = pd.Timestamp("2023-07-01")          # cross-fitting boundary (also the guide's train / test boundary)
WARMUP_DAYS = 21                             # x_hat needs 14 days; robust scores need >= 7 more (D43)
BANDS = ["raw", "W1", "W2", "W3", "W4", "V4"]
LEVELS = ["g", "u", "v"]

# Daubechies least-asymmetric LA(8) scaling filter (Percival & Walden 2000) = PyWavelets 'sym4' dec_lo
LA8 = np.array(pywt.Wavelet("sym4").dec_lo)
_PW_LA8 = np.array([-0.0757657147893407, -0.0296355276459541, 0.4976186676324578, 0.8037387518052163,
                    0.2978577956055422, -0.0992195435769354, -0.0126039672622612, 0.0322231006040713])
assert np.allclose(LA8, _PW_LA8, atol=1e-10), "PyWavelets sym4 differs from the Percival-Walden LA(8) filter"

# Calendar (Morocco). Religious dates can differ by one day from other countries: treat as approximate.
RAMADAN = [("2023-03-23", "2023-04-21"), ("2024-03-12", "2024-04-09")]
EID = ["2023-04-22", "2023-04-23", "2023-06-29", "2023-06-30", "2024-04-10", "2024-04-11"]
MOROCCO_GMT = [("2023-03-19 03:00", "2023-04-23 02:00"), ("2024-03-10 03:00", "2024-04-14 02:00")]
FIXED_HOLIDAYS = ["01-01", "01-11", "05-01", "07-30", "08-14", "08-20", "08-21", "11-06", "11-18"]


# ------------------------------------------------------------------ panel
def build_panel(data, exp, masks, system):
    """Wide frames (time x zone code) for one system: rho, x, mask, plus zone -> city map."""
    cities = [c for c in data if (c != "Marrakech") == (system == "south")]
    cols, rho, x, msk = [], [], [], []
    states = {k: [] for k in ("zero", "dead", "hold", "interp")}
    for c in cities:
        d, e = data[c], exp[c]
        m = masks[c]["dead"] | masks[c]["hold"] | masks[c]["interp"]
        for z in d.columns:
            code = f"{CITY_SHORT[c]}{z.replace('zone', '')}"
            cols.append((code, c))
            r = (d[z] / e[z]).where(e[z] > 0).clip(0, 3)
            rho.append(r.rename(code)); x.append(d[z].rename(code)); msk.append((m[z] | r.isna()).rename(code))
            states["zero"].append(d[z].eq(0).rename(code))
            for k in ("dead", "hold", "interp"):
                states[k].append(masks[c][k][z].rename(code))
    P = dict(rho=pd.concat(rho, axis=1), x=pd.concat(x, axis=1), mask=pd.concat(msk, axis=1),
             states={k: pd.concat(v, axis=1) for k, v in states.items()},
             city={k: v for k, v in cols}, system=system, step=STEP_MIN[system])
    P["per_day"] = int(24 * 60 / P["step"])
    return P


def calendar(index):
    t = pd.DatetimeIndex(index)
    tod = (t.hour * 60 + t.minute).to_numpy()
    f = pd.DataFrame(index=index)
    f["tod"] = tod
    f["tod_sin"], f["tod_cos"] = np.sin(2 * np.pi * tod / 1440), np.cos(2 * np.pi * tod / 1440)
    f["dow"] = t.dayofweek
    f["weekend"] = (t.dayofweek >= 5).astype(int)
    f["month"] = t.month
    day = t.normalize()
    f["ramadan"] = np.zeros(len(t), dtype=int)
    for a, b in RAMADAN:
        f.loc[(day >= a) & (day <= b), "ramadan"] = 1
    f["eid"] = day.isin(pd.to_datetime(EID)).astype(int)
    f["holiday"] = pd.Index(t.strftime("%m-%d")).isin(FIXED_HOLIDAYS).astype(int)
    f["morocco_gmt"] = np.zeros(len(t), dtype=int)
    for a, b in MOROCCO_GMT:
        f.loc[(t >= a) & (t < b), "morocco_gmt"] = 1
    return f


def own_features(P, z, cal):
    """Lags of the zone's own rho with flagged steps removed (NaN), plus calendar."""
    p = P["per_day"]
    m = P["rho"][z].where(~P["mask"][z])
    f = cal.copy()
    for k in (1, 2, 3, 6):
        f[f"lag{k}"] = m.shift(k)
    f["lag_1d"], f["lag_2d"], f["lag_7d"] = m.shift(p), m.shift(2 * p), m.shift(7 * p)
    f["mean_last6"] = m.shift(1).rolling(6, min_periods=2).mean()
    f["median_prev_day"] = m.shift(1).rolling(p, min_periods=p // 4).median()
    return f


# ------------------------------------------------------------------ predictors
LGB_PARAMS = dict(objective="huber", alpha=0.1, n_estimators=400, learning_rate=0.05, num_leaves=31,
                  min_child_samples=50, subsample=0.8, subsample_freq=1, colsample_bytree=0.9,
                  reg_lambda=1.0, verbose=-1, n_jobs=max(1, (os.cpu_count() or 2) // 2))


def _model(seed, backend):
    if backend == "lightgbm":
        return lgb.LGBMRegressor(random_state=seed, **LGB_PARAMS)
    # Fallback only (D39): same histogram-GBDT family. Used when LightGBM's native library fails (it crashed
    # intermittently on the author's Windows machine; it runs normally on Colab). The notebook prints the backend.
    from sklearn.ensemble import HistGradientBoostingRegressor
    return HistGradientBoostingRegressor(loss="absolute_error", max_iter=400, learning_rate=0.05, max_leaf_nodes=31,
                                         min_samples_leaf=50, l2_regularization=1.0, random_state=seed)


def predict_rho(P, kind="forecast", seed=0, backend="auto"):
    """Out-of-sample rho_hat for every zone: two-fold cross-fitting at SPLIT (D41).
    kind: 'forecast' (own past + calendar) or 'nowcast' (+ current rho of all other zones).
    backend: 'lightgbm', 'sklearn' or 'auto' (LightGBM, falling back to sklearn for the whole call if it fails)."""
    if backend == "auto":
        try:
            out = predict_rho(P, kind, seed, "lightgbm")
            P["backend"] = "lightgbm"
            return out
        except OSError as ex:
            print(f"LightGBM failed ({ex}); falling back to sklearn HistGradientBoosting")
            P["backend"] = "sklearn"
            return predict_rho(P, kind, seed, "sklearn")
    cal = calendar(P["rho"].index)
    out = pd.DataFrame(index=P["rho"].index, columns=P["rho"].columns, dtype=float)
    fold = P["rho"].index >= SPLIT
    for z in P["rho"].columns:
        X = own_features(P, z, cal)
        if kind == "nowcast":
            for z2 in P["rho"].columns:
                if z2 != z:
                    X[f"nb_{z2}"] = P["rho"][z2]
        y = P["rho"][z]
        ok = ~P["mask"][z] & y.notna()
        for tr_fold in (False, True):
            tr = ok & (fold == tr_fold)
            if tr.sum() < 1000:
                continue
            # contiguous float64 arrays kept alive in local names: LightGBM 4.7 on Windows crashed intermittently
            # (access violation in LGBM_DatasetSetField) when handed temporary pandas objects
            Xtr = np.ascontiguousarray(X[tr].to_numpy(dtype=np.float64))
            ytr = np.ascontiguousarray(y[tr].to_numpy(dtype=np.float64))
            model = _model(seed, backend).fit(Xtr, ytr)
            te = (fold != tr_fold)
            Xte = np.ascontiguousarray(X[te].to_numpy(dtype=np.float64))
            out.loc[te, z] = model.predict(Xte)
    return out


# ------------------------------------------------------------------ multi-scale
def modwt(x, J=4, filt=LA8):
    """MODWT pyramid (Percival & Walden 2000), circular, causal: W_{j,t} uses x_t, x_{t-1}, ...
    Returns ([W1..WJ], VJ) as numpy arrays; boundary-affected coefficients are set to NaN."""
    g = filt / np.sqrt(2)
    L = len(g)
    h = np.array([(-1) ** l * g[L - 1 - l] for l in range(L)])
    V, W = np.asarray(x, dtype=float).copy(), []
    for j in range(1, J + 1):
        s = 2 ** (j - 1)
        Wj, Vj = np.zeros_like(V), np.zeros_like(V)
        for l in range(L):
            r = np.roll(V, s * l)
            Wj += h[l] * r
            Vj += g[l] * r
        nb = (2 ** j - 1) * (L - 1)
        Wj[:nb] = np.nan
        W.append(Wj)
        V = Vj
    V = V.copy()
    V[:(2 ** J - 1) * (L - 1)] = np.nan
    return W, V


def band_delays(J=4, n=4096):
    """Group delay (steps) of each MODWT band, from the energy centroid of its impulse response."""
    x = np.zeros(n); t0 = n // 2; x[t0] = 1.0
    W, V = modwt(x, J)
    t = np.arange(n)
    d = {}
    for j, w in enumerate(W + [V]):
        w2 = np.nan_to_num(w) ** 2
        d[f"W{j + 1}" if j < J else f"V{J}"] = int(round((t * w2).sum() / w2.sum() - t0))
    return d


BAND_DELAY = band_delays()
SPILL_STEPS = int(np.ceil(((2 ** 4 - 1) * (len(LA8) - 1) + 1) / 2))   # half the support of the widest band


def bands(E, align=True):
    """Residual frame (time x zone) -> dict band -> frame. NaN residuals are treated as 0 for filtering.
    align=True shifts each band back by its group delay (phase alignment; wrapped ends become NaN)."""
    out = {"raw": E}
    filled = E.fillna(0.0)
    W = {z: modwt(filled[z].to_numpy()) for z in E.columns}

    def al(a, name):
        if not align:
            return a
        d = BAND_DELAY[name]
        r = np.roll(a, -d)
        if d > 0:
            r[-d:] = np.nan
        return r
    for j in range(4):
        out[f"W{j + 1}"] = pd.DataFrame({z: al(W[z][0][j], f"W{j + 1}") for z in E.columns}, index=E.index)
    out["V4"] = pd.DataFrame({z: al(W[z][1], "V4") for z in E.columns}, index=E.index)
    return out


# ------------------------------------------------------------------ hierarchy and scores
def hierarchy(E, city):
    """Eq. 14: g (Series), u (DataFrame city), v (DataFrame zone)."""
    g = E.median(axis=1, skipna=True)
    cities = sorted(set(city.values()))
    med_c = pd.DataFrame({c: E[[z for z in E.columns if city[z] == c]].median(axis=1, skipna=True) for c in cities})
    u = med_c.sub(g, axis=0)
    v = E.sub(g, axis=0) - pd.DataFrame({z: u[city[z]] for z in E.columns})
    return g, u, v


STRUCTURAL_ZERO = 1e-12


def robust_score(s, clean, window, min_periods):
    """Eq. 15 with a trailing window; median and MAD of |s| estimated on clean steps only.

    Structural zeros are excluded from the estimate (D51). A city median over an odd number of zones is attained
    by one of them, so v of that zone is exactly 0 (and u of a city is exactly 0 when its median zone is also the
    region median). These zeros carry no information about the zone. If they fill half the trailing window, the
    median and MAD collapse to 0 and the score becomes |s| / 1e-6 (observed: B1, V4 band, 16-18 Mar 2024,
    z = 15 182 with LightGBM residuals; F35)."""
    a = s.abs()
    est = clean & (a > STRUCTURAL_ZERO)
    med = a.where(est).rolling(window, min_periods=min_periods).median()
    mad = (a - med).abs().where(est).rolling(window, min_periods=min_periods).median()
    return (a - med) / (1.4826 * mad + 1e-6)


def level_scores(P, E, bands_used=BANDS):
    """Scores s[band][level] for one residual frame. g: Series, u: frame (city), v: frame (zone)."""
    p = P["per_day"]
    win, mp = 28 * p, 7 * p
    M = P["mask"]
    warm = P["rho"].index < P["rho"].index[0] + pd.Timedelta(days=WARMUP_DAYS)
    city = P["city"]
    clean_g = ~M.any(axis=1)
    clean_u = pd.DataFrame({c: ~M[[z for z in M.columns if city[z] == c]].any(axis=1) for c in sorted(set(city.values()))})
    clean_v = ~M
    B = bands(E) if len(bands_used) > 1 else {"raw": E}
    S = {}
    for b in bands_used:
        g, u, v = hierarchy(B[b], city)
        g, u, v = g.copy(), u.copy(), v.copy()
        g[warm] = np.nan; u.loc[warm] = np.nan; v.loc[warm] = np.nan
        S[b] = dict(
            g=robust_score(g, clean_g, win, mp),
            u=pd.DataFrame({c: robust_score(u[c], clean_u[c], win, mp) for c in u.columns}) if u.shape[1] > 1 else
              pd.DataFrame({c: pd.Series(0.0, index=u.index) for c in u.columns}),
            v=pd.DataFrame({z: robust_score(v[z], clean_v[z], win, mp) for z in v.columns}),
        )
    return S


def zone_max_score(P, S):
    """Per zone and step: max over bands and over the levels that contain the zone (g, its city's u, its v)."""
    city = P["city"]
    parts = []
    for b, d in S.items():
        parts.append(pd.DataFrame({z: np.fmax(np.fmax(d["g"].to_numpy(), d["u"][city[z]].to_numpy()), d["v"][z].to_numpy())
                                   for z in P["rho"].columns}, index=P["rho"].index))
    out = parts[0]
    for q in parts[1:]:
        out = np.fmax(out, q)
    return out


def runs_of(mask, max_gap=1, min_len=3):
    """Runs of True allowing gaps of <= max_gap False steps; returns list of (start_idx, end_idx_inclusive)."""
    m = np.asarray(mask, dtype=bool)
    idx = np.flatnonzero(m)
    if len(idx) == 0:
        return []
    out, a, prev = [], idx[0], idx[0]
    for i in idx[1:]:
        if i - prev - 1 > max_gap:
            if prev - a + 1 >= min_len:
                out.append((a, prev))
            a = i
        prev = i
    if prev - a + 1 >= min_len:
        out.append((a, prev))
    return out


# ------------------------------------------------------------------ classical baseline and residual diagnostics
def stl_residual(P, period=None, robust=False):
    """Baseline residual (statsmodels STL): rho minus trend and daily seasonal component, per zone.
    Masked and missing steps are filled with 1 (= expected) before decomposition. Non-causal (two-sided)."""
    from statsmodels.tsa.seasonal import STL
    period = period or P["per_day"]
    out = {}
    for z in P["rho"].columns:
        y = P["rho"][z].where(~P["mask"][z]).fillna(1.0)
        fit = STL(y.to_numpy(), period=period, robust=robust).fit()
        out[z] = P["rho"][z] - (fit.trend + fit.seasonal)
    return pd.DataFrame(out, index=P["rho"].index)


def ljung_box(E, mask, lags):
    """Ljung-Box Q statistic of clean residuals (masked steps dropped), per zone (statsmodels)."""
    from statsmodels.stats.diagnostic import acorr_ljungbox
    rows = []
    for z in E.columns:
        r = E[z].where(~mask[z]).dropna()
        lb = acorr_ljungbox(r.to_numpy(), lags=lags, return_df=True)
        acf1 = float(np.corrcoef(r.to_numpy()[1:], r.to_numpy()[:-1])[0, 1])
        rows.append(dict(zone=z, n=len(r), acf_lag1=round(acf1, 3), **{f"lb_stat_{l}": round(float(lb.loc[l, "lb_stat"]), 1) for l in lags}))
    return pd.DataFrame(rows)
