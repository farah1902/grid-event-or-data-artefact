"""
rules_v0.py - Rule engine v0 for "Grid event or data artefact?"
Builds the event catalogue for the UCI Morocco smart-meter dataset (id 1158).
Needs only pandas + numpy (Colab works as-is).

Usage:  python rules_v0.py "Data Morocco.xlsx" out_dir
Outputs (in out_dir):
  timestamp_audit.csv  - duplicates / missing steps / backward jumps per city
  zero_events.csv      - zero-runs grouped across zones and cities, with features + provisional type
  stuck_runs.csv       - runs of identical non-zero values
  transfers.csv        - candidate load-transfer / level-shift dates
"""
import sys, os
import numpy as np
import pandas as pd

STEP = {"Laayoune": "10min", "Boujdour": "10min", "Foum eloued": "10min", "Marrakech": "30min"}
SOUTH = ["Laayoune", "Boujdour", "Foum eloued"]          # share the same 10-min logger timeline
MIN_ZERO_STEPS = 3                                       # zero-run >= 30 min (10-min data)
STUCK_STEPS = {"10min": 6, "30min": 6}                   # identical non-zero value for >= 1 h / 3 h
BASELINE_DAYS = 14                                       # expected value = median of same slot over 14 prior days


def load(path):
    raw = pd.read_excel(path, sheet_name=None)
    return {k.strip(): v for k, v in raw.items()}


def audit_timestamps(city, df):
    t = df["DateTime"]
    step = pd.Timedelta(STEP[city])
    d = t.diff()
    back = t[d < pd.Timedelta(0)]
    dups = t[t.duplicated(keep=False)]
    s = t.drop_duplicates().sort_values()
    full = pd.date_range(s.iloc[0], s.iloc[-1], freq=STEP[city])
    missing = full.difference(s)
    rows = []
    for v in sorted(set(dups)):
        rows.append(dict(city=city, kind="duplicate", timestamp=v, n=int((t == v).sum())))
    for v in back:
        rows.append(dict(city=city, kind="backward_jump", timestamp=v, n=1))
    # collapse missing timestamps into runs
    if len(missing):
        m = pd.Series(missing)
        g = (m.diff() != step).cumsum()
        for _, grp in m.groupby(g):
            rows.append(dict(city=city, kind="missing_run", timestamp=grp.iloc[0], n=len(grp)))
    return rows


def regularise(city, df):
    """Average duplicate stamps, sort, put on a regular grid (missing steps -> NaN)."""
    d = df.groupby("DateTime").mean().sort_index()
    full = pd.date_range(d.index[0], d.index[-1], freq=STEP[city])
    return d.reindex(full)


def expected(series, city):
    """x_hat_t = median of x at the same time-of-day over the previous BASELINE_DAYS days (zeros excluded)."""
    per_day = int(pd.Timedelta("1D") / pd.Timedelta(STEP[city]))
    x = series.where(series > 0)
    lags = pd.concat([x.shift(per_day * k) for k in range(1, BASELINE_DAYS + 1)], axis=1)
    return lags.median(axis=1, skipna=True)


def runs(mask):
    """Return list of (start_idx, end_idx_inclusive) for True runs in a boolean Series."""
    m = mask.to_numpy()
    out, i, n = [], 0, len(m)
    while i < n:
        if m[i]:
            j = i
            while j + 1 < n and m[j + 1]:
                j += 1
            out.append((i, j))
            i = j + 1
        else:
            i += 1
    return out


DEAD_REL = 0.05     # "dead" = x <= 5% of expected value (a dead feeder reads a noise floor, not always exact 0)
START_TOL = pd.Timedelta("10min")   # runs starting within 10 min of each other = one event


def zero_runs(data, exp):
    """Dead-state runs per zone. A run must contain at least one exact zero OR last >= MIN_ZERO_STEPS."""
    recs = []
    for city, d in data.items():
        step = pd.Timedelta(STEP[city])
        for z in d.columns:
            x, xh = d[z], exp[city][z]
            dead = (x == 0) | (x <= DEAD_REL * xh)
            for a, b in runs(dead.fillna(False)):
                seg = x.iloc[a:b + 1]
                n0 = int((seg == 0).sum())
                if b - a + 1 >= MIN_ZERO_STEPS and n0 > 0:
                    recs.append(dict(city=city, zone=z, start=d.index[a], end=d.index[b] + step,
                                     steps=b - a + 1, exact_zero_share=round(n0 / (b - a + 1), 2)))
    return pd.DataFrame(recs)


def group_events(zr):
    """Runs whose start times lie within START_TOL of the event's first start = one event
    (simultaneity is the hierarchical signal; mere overlap is not)."""
    zr = zr.sort_values("start").reset_index(drop=True)
    ev_id, first, ids = -1, None, []
    for _, r in zr.iterrows():
        if first is None or r.start - first > START_TOL:
            ev_id += 1
            first = r.start
        ids.append(ev_id)
    zr["event"] = ids
    return zr


def restoration_features(data, exp, city, zones, start, end):
    """Pre-event ratio, restoration ratio r = x/x_hat over the first 30 min after the end, ramp time."""
    d, e = data[city], exp[city]
    step = pd.Timedelta(STEP[city])
    k = max(1, int(pd.Timedelta("30min") / step))
    tot = d[zones].sum(axis=1, min_count=1)
    etot = e[zones].sum(axis=1, min_count=1)
    after = tot[end:end + (k - 1) * step]
    eafter = etot[end:end + (k - 1) * step]
    before = tot[start - k * step:start - step]
    ebefore = etot[start - k * step:start - step]
    r_after = after.mean() / eafter.mean() if eafter.mean() > 0 else np.nan
    r_before = before.mean() / ebefore.mean() if ebefore.mean() > 0 else np.nan
    # ramp: steps until total reaches 90% of expected
    win = (tot[end:end + 36 * step] / etot[end:end + 36 * step]).to_numpy()
    hit = np.where(win >= 0.9)[0]
    ramp_min = int(hit[0] * step.total_seconds() / 60) if len(hit) else None
    peak = (tot[end:end + 6 * step] / etot[end:end + 6 * step]).max()
    return r_before, r_after, peak, ramp_min


def classify(row):
    """Provisional rule vote (v0), codes as in the guide's typology. Returns (type, rule fired)."""
    if row.n_cities >= 2:
        if row.peak_ratio is not None and row.peak_ratio >= 1.15:
            return "G1_regional_outage?", "R7+R5: multi-city, cold-load pickup"
        return "A1_zero_fill_gap?", "R1: multi-city, same start, no pickup"
    if row.n_cities == 1 and row.frac_zones >= 0.9:
        return "G2_city_outage?", "R8: >=90% zones of one city"
    if row.n_zones == 1:
        if 6 <= row.start_hour <= 11 and row.duration_h <= 6:
            return "G4_planned_work?", "R10: one zone, starts 06-11 h, <= 6 h"
        return "G3_feeder_outage", "R9: one zone only"
    return "G3m_partial_city", "R9m: some zones of one city"


def zero_events(data, exp):
    zr = group_events(zero_runs(data, exp))
    zcount = {c: d.shape[1] for c, d in data.items()}
    out = []
    for ev, g in zr.groupby("event"):
        start, end = g.start.min(), g.end.max()
        cities = sorted(g.city.unique())
        starts_by_city = g.groupby("city").start.min()
        feats = {}
        for c in cities:
            zones = sorted(g[g.city == c].zone.unique())
            feats[c] = restoration_features(data, exp, c, zones, g[g.city == c].start.min(), g[g.city == c].end.max())
        main = max(cities, key=lambda c: (g.city == c).sum())
        rb, ra, pk, rm = feats[main]
        out.append(dict(
            event=ev, start=start, end=end, duration_h=round((end - start).total_seconds() / 3600, 2),
            cities="+".join(cities), n_cities=len(cities),
            zones=";".join(f"{c}:{','.join(sorted(g[g.city == c].zone.unique()))}" for c in cities),
            n_zones=g.groupby(["city", "zone"]).ngroups,
            frac_zones=round(max(g[g.city == c].zone.nunique() / zcount[c] for c in cities), 2),
            same_start=bool(len(cities) > 1),
            exact_zero_share=round(float((g.exact_zero_share * g.steps).sum() / g.steps.sum()), 2),
            weekday=start.day_name()[:3], start_hour=start.hour,
            pre_ratio=round(rb, 2) if pd.notna(rb) else None,
            restore_ratio=round(ra, 2) if pd.notna(ra) else None,
            peak_ratio=round(pk, 2) if pd.notna(pk) else None,
            ramp_to_90pct_min=rm,
        ))
    ev = pd.DataFrame(out)
    ev[["provisional_type", "rule"]] = ev.apply(lambda r: pd.Series(classify(r)), axis=1)
    return ev.sort_values("duration_h", ascending=False)


def stuck_runs(data):
    recs = []
    for city, d in data.items():
        k = STUCK_STEPS[STEP[city]]
        step = pd.Timedelta(STEP[city])
        for z in d.columns:
            x = d[z]
            same = (x.diff() == 0) & (x != 0) & x.notna()
            for a, b in runs(same):
                n = b - a + 2  # number of identical points
                if n >= k:
                    recs.append(dict(city=city, zone=z, start=d.index[a - 1], end=d.index[b] + step,
                                     points=n, value=round(float(x.iloc[b]), 3)))
    return pd.DataFrame(recs).sort_values("points", ascending=False)


def transfers(data, min_rel=0.25):
    """Candidate load transfers: zone i up, zone j down (same city), city total ~ stable.
    Uses 14-day medians of daily means before/after each day."""
    recs = []
    for city, d in data.items():
        if d.shape[1] < 2:
            continue
        daily = d.where(d > 0).resample("1D").mean()
        pre = daily.rolling(14, min_periods=10).median()
        post = daily[::-1].rolling(14, min_periods=10).median()[::-1].shift(-1)
        delta = post - pre
        lvl = daily.mean()
        for day in delta.index:
            dz = delta.loc[day]
            if dz.isna().any():
                continue
            up, dn = dz.idxmax(), dz.idxmin()
            if dz[up] > min_rel * lvl[up] and -dz[dn] > min_rel * lvl[dn]:
                cons = abs(dz.sum()) / max(dz[up], -dz[dn])
                recs.append(dict(city=city, day=day.date(), zone_up=up, delta_up=round(dz[up], 1),
                                 zone_down=dn, delta_down=round(dz[dn], 1),
                                 conservation_index=round(cons, 2)))
    t = pd.DataFrame(recs)
    if t.empty:
        return t
    # keep the best day per (city, zone pair, 30-day window)
    t["score"] = (t.delta_up - t.delta_down) / (1 + t.conservation_index)
    t["win"] = pd.to_datetime(t.day).dt.to_period("M")
    return (t.sort_values("score", ascending=False)
             .drop_duplicates(["city", "zone_up", "zone_down", "win"])
             .drop(columns="win").sort_values("score", ascending=False))


def main(path, out):
    os.makedirs(out, exist_ok=True)
    raw = load(path)
    audit = sum((audit_timestamps(c, df) for c, df in raw.items()), [])
    pd.DataFrame(audit).to_csv(f"{out}/timestamp_audit.csv", index=False)
    data = {c: regularise(c, df) for c, df in raw.items()}
    exp = {c: d.apply(lambda s: expected(s, c)) for c, d in data.items()}
    zero_events(data, exp).to_csv(f"{out}/zero_events.csv", index=False)
    stuck_runs(data).to_csv(f"{out}/stuck_runs.csv", index=False)
    transfers(data).to_csv(f"{out}/transfers.csv", index=False)
    print("done ->", out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "catalogue_out")
