"""Diagnostic for F35 / D51: structural zeros of the median hierarchy and the scale collapse they cause.

The city part u and zone part v come from medians over an odd number of zones, so one zone always equals the
median: its v is exactly 0 at that step. This script measures how often that happens and shows the collapse
of the old scale estimate (zeros included) for B1, V4 band, 16-18 Mar 2024, against the fixed one (D51).

    python tools/diag_structural_zeros.py "data/raw/Data Morocco.xlsx" results/detector_v1 [--cache file.pkl]

Uses the LightGBM forecast residual of the south system (about 2 min). Writes structural_zeros.csv.
"""
import sys, pickle, argparse
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import rules_v1 as R1, detector as D


def old_score(s, clean, window, min_periods):
    """robust_score as it was before D51 (structural zeros included in the median and MAD)."""
    a = s.abs()
    med = a.where(clean).rolling(window, min_periods=min_periods).median()
    mad = (a - med).abs().where(clean).rolling(window, min_periods=min_periods).median()
    return (a - med) / (1.4826 * mad + 1e-6), med, mad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("xlsx"); ap.add_argument("out"); ap.add_argument("--cache", default=None)
    a = ap.parse_args()
    if a.cache and Path(a.cache).exists():
        d = pickle.load(open(a.cache, "rb")); P, pred = d["P"], d["pred"]
    else:
        res = R1.build(a.xlsx)
        P = D.build_panel(res["data"], res["exp"], res["masks"], "south")
        pred = D.predict_rho(P, "forecast", backend="lightgbm")
        if a.cache:
            pickle.dump(dict(P=P, pred=pred), open(a.cache, "wb"))
    E = P["rho"] - pred
    city, M = P["city"], P["mask"]
    win, mp = 28 * P["per_day"], 7 * P["per_day"]
    B = D.bands(E)
    rows = []
    # 1. share of steps where the zone part / city part is exactly zero, per band
    for b in B:
        g, u, v = D.hierarchy(B[b], city)
        warm = v.index < v.index[0] + pd.Timedelta(days=D.WARMUP_DAYS)
        for z in v.columns:
            ok = v[z].notna() & ~warm
            rows.append(dict(check="share_v_exactly_0", band=b, unit=z, value=round(float((v[z][ok].abs() < D.STRUCTURAL_ZERO).mean()), 4)))
        for c in u.columns:
            ok = u[c].notna() & ~warm
            rows.append(dict(check="share_u_exactly_0", band=b, unit=c, value=round(float((u[c][ok].abs() < D.STRUCTURAL_ZERO).mean()), 4)))
    # 2. B1, 16-18 Mar 2024: old vs fixed scale, per band
    sl = slice("2024-03-16", "2024-03-18")
    for b in B:
        g, u, v = D.hierarchy(B[b], city)
        s = v["B1"].copy(); s[s.index < s.index[0] + pd.Timedelta(days=D.WARMUP_DAYS)] = np.nan
        clean = ~M["B1"]
        sc_old, med_old, mad_old = old_score(s, clean, win, mp)
        sc_new = D.robust_score(s, clean, win, mp)
        share0 = (s.abs() < D.STRUCTURAL_ZERO).astype(float).where(clean & s.notna()).rolling(win, min_periods=mp).mean()
        rows += [dict(check="B1_16-18Mar2024_window_share_v0_max", band=b, unit="B1", value=round(float(share0[sl].max()), 3)),
                 dict(check="B1_16-18Mar2024_MAD_old_min", band=b, unit="B1", value=float(mad_old[sl].min())),
                 dict(check="B1_16-18Mar2024_max_score_old", band=b, unit="B1", value=round(float(sc_old[sl].max()), 1)),
                 dict(check="B1_16-18Mar2024_max_score_fixed", band=b, unit="B1", value=round(float(sc_new[sl].max()), 1))]
    # 3. how many zone-steps had a collapsed old scale (MAD < 1e-4), per band
    for b in B:
        g, u, v = D.hierarchy(B[b], city)
        n_low = n_all = 0
        for z in v.columns:
            s = v[z].copy(); s[s.index < s.index[0] + pd.Timedelta(days=D.WARMUP_DAYS)] = np.nan
            _, _, mad = old_score(s, ~M[z], win, mp)
            n_all += int(mad.notna().sum()); n_low += int((mad < 1e-4).sum())
        rows += [dict(check="zone_steps_old_MAD_below_1e-4", band=b, unit="all zones", value=n_low),
                 dict(check="zone_steps_with_scale", band=b, unit="all zones", value=n_all)]
    out = pd.DataFrame(rows)
    Path(a.out).mkdir(parents=True, exist_ok=True)
    out.to_csv(Path(a.out) / "structural_zeros.csv", index=False)
    print(out[out.check.str.startswith("B1") | out.check.str.startswith("zone_steps")].to_string(index=False))
    print(out[(out.band == "raw")].pivot_table(index="unit", columns="check", values="value").round(3).to_string())
    print("lightgbm backend:", P.get("backend"))


if __name__ == "__main__":
    main()
