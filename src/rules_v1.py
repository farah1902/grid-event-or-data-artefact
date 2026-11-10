"""
rules_v1.py - Rule engine v1 for "Grid event or data artefact?"

Adds to v0 the rules R3, R4, R5, R6, R11, R12, R15 (definitions in docs/research_guide.md)
and a new linear-interpolation family R19-R21. NB1 found straight-line gap fills
(constant first difference), which v0 cannot see because it only detects identical values.
Every rule votes for one type or abstains. Conflicts are left for the label model (NB2).
R17/R18 (external evidence) are not implemented.

Items, the unit that rules vote on:
  dead     - dead-state runs (x == 0 or x <= EPS * x_hat), grouped across zones by start time (eq. 4, 7)
  fill     - hold runs (identical non-zero values, eq. 6) and linear-interpolation runs, grouped by start time
  clock    - (city, date) on clock-change calendar dates or dates with duplicate/missing stamps
  transfer - candidate load-transfer days (v0 detector, eq. 8)
Grouping only happens inside one system: the southern 10-min logger group (L, B, F) or Marrakech.

Labels: A1 A2 A3 A4 G1 G2 G3 G4 G5, plus "G" (any grid event) for R5 and R6.

Usage:  python src/rules_v1.py "data/raw/Data Morocco.xlsx" results/catalogue_v1
Outputs: items.csv, votes.csv, zone_runs.csv, rule_summary.csv
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rules_v0 import STEP, SOUTH, audit_timestamps, expected, load, regularise, runs, transfers  # noqa: E402

# ---------------------------------------------------------------- parameters
# Defaults follow the guide; each one is swept in ablation 6.
EPS = 0.05                          # dead state: x <= 5% of expected (eq. 4)
MIN_DEAD_STEPS = 3                  # >= 30 min at 10-min resolution
REQUIRE_EXACT_ZERO = False          # v0 used True. Noise-floor-only runs are the G3 signature (H1), so keep them.
HOLD_MIN_PTS = {"10min": 6, "30min": 12}     # Marrakech is whole-kW: identical values repeat naturally
INTERP_MIN_PTS = {"10min": 6, "30min": 12}   # same reason for collinear integer runs
TOL = pd.Timedelta("10min")         # simultaneity tolerance tau (eq. 7)
COEXT_IOU = 0.5                     # a fill run and a dead event are co-extensive if their time IoU >= 0.5
R1_ETA, R1_R, R1_TAU = 0.95, 0.2, 10
R5_PI = 1.15
R6_ETA = 0.9
R7_TAU = 30
R8_FRAC, R8_ALIVE = 0.9, 0.5
R10_HOURS, R10_MAXDUR = (6, 11), 6
R11_DUR = 24
R12_VARY = 0.8                      # share of neighbour zone-steps that are normal and moving
R15_DELTA = 50
R15_MIN_CORR, R15_MIN_GAIN = 0.9, 0.05   # v1 guard: the shifted profile must fit well and clearly beat no shift
R16_KAPPA = 0.3

EUROPE_DST = ["2017-03-26", "2017-10-29",                               # 2017: Tetouan transfer test (NB6)
              "2022-10-30", "2023-03-26", "2023-10-29", "2024-03-31"]   # last Sunday of Oct / Mar
MOROCCO_DST = ["2017-03-26", "2017-05-21", "2017-07-02", "2017-10-29",  # 2017: summer time, suspended for Ramadan
               "2023-03-19", "2023-04-23", "2024-03-10", "2024-04-14"]  # Ramadan switches to/from GMT
# Dates outside a dataset's range are ignored, so the 2017 entries do not change any Morocco result.

RULES = ["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9", "R10", "R11", "R12",
         "R13", "R14", "R15", "R16", "R19", "R20", "R21"]
RULE_FAMILY = {  # guide ablation 2, plus the new interpolation family
    "R1": "simultaneity", "R7": "simultaneity",
    "R2": "hold", "R3": "hold", "R4": "hold", "R12": "hold",
    "R5": "restoration", "R6": "restoration",
    "R8": "city", "R9": "single_zone", "R11": "single_zone",
    "R10": "calendar", "R13": "clock", "R14": "calendar", "R15": "clock",
    "R16": "conservation",
    "R19": "interpolation", "R20": "interpolation", "R21": "interpolation",
}
RULE_KIND = {r: "dead" for r in ["R1", "R3", "R4", "R5", "R6", "R7", "R8", "R9", "R10", "R11", "R21"]}
RULE_KIND.update({r: "fill" for r in ["R2", "R12", "R19", "R20"]})
RULE_KIND.update({r: "clock" for r in ["R13", "R14", "R15"]})
RULE_KIND["R16"] = "transfer"

CITY_SHORT = {"Laayoune": "L", "Boujdour": "B", "Foum eloued": "F", "Marrakech": "M"}
SYSTEM = {c: ("south" if c in SOUTH else c) for c in STEP}


# ---------------------------------------------------------------- state masks
def hold_mask(x, min_pts):
    """Points belonging to runs of >= min_pts identical non-zero values (eq. 6)."""
    same = (x.diff() == 0) & (x != 0) & x.notna()
    length = same.groupby((~same).cumsum()).transform("sum")
    mark = same & (length >= min_pts - 1)
    return mark | (mark.shift(-1, fill_value=False) & ~same)        # add the first point of each run


def interp_mask(x, min_pts):
    """Points belonging to runs of >= min_pts collinear non-zero values with non-zero slope."""
    dx = x.diff()
    lin = (dx.diff().abs() < 1e-8 * np.maximum(1, x.abs())) & (dx.abs() > 1e-12) & x.notna() & (x != 0)
    length = lin.groupby((~lin).cumsum()).transform("sum")           # k collinear 2nd differences = k + 2 points
    mark = lin & (length >= min_pts - 2)
    return mark | mark.shift(-1, fill_value=False) | mark.shift(-2, fill_value=False)


def state_masks(data, exp):
    """city -> {dead, hold, interp} boolean DataFrames.
    Priority: exact zero > linear interpolation > noise floor > hold. A non-zero point lying on a
    straight-line fill (e.g. a line ramping up from 0) is fill, not a de-energised noise floor."""
    out = {}
    for c, d in data.items():
        st = STEP[c]
        zero = d.eq(0)
        interp_raw = d.apply(lambda s: interp_mask(s, INTERP_MIN_PTS[st]))
        floor = ((d <= EPS * exp[c]) & d.notna()).fillna(False)
        dead = zero | (floor & ~interp_raw)
        hold = d.apply(lambda s: hold_mask(s, HOLD_MIN_PTS[st])) & ~dead
        interp = interp_raw & ~dead & ~hold
        out[c] = dict(dead=dead, hold=hold, interp=interp)
    return out


def zone_runs(data, masks):
    """One row per qualifying run of a state in one zone. end is exclusive (first step after the run)."""
    recs = []
    for c, d in data.items():
        step = pd.Timedelta(STEP[c])
        kmin = dict(dead=MIN_DEAD_STEPS, hold=HOLD_MIN_PTS[STEP[c]], interp=INTERP_MIN_PTS[STEP[c]])
        for z in d.columns:
            x = d[z]
            for kind in ("dead", "hold", "interp"):
                for a, b in runs(masks[c][kind][z]):
                    n = b - a + 1
                    if n < kmin[kind]:
                        continue
                    seg = x.iloc[a:b + 1]
                    n0 = int((seg == 0).sum())
                    if kind == "dead" and REQUIRE_EXACT_ZERO and n0 == 0:
                        continue
                    recs.append(dict(
                        system=SYSTEM[c], city=c, zone=z, code=f"{CITY_SHORT[c]}{z.replace('zone', '')}",
                        kind=kind, start=d.index[a], end=d.index[b] + step, a=a, b=b, steps=n,
                        n_zero=n0, value=round(float(seg.iloc[-1]), 3) if kind == "hold" else np.nan,
                        slope=round(float(seg.diff().iloc[-1]), 5) if kind == "interp" else np.nan,
                        quantised=bool((seg == seg.round()).all())))
    cols = ["system", "city", "zone", "code", "kind", "start", "end", "a", "b", "steps", "n_zero", "value", "slope", "quantised"]
    return pd.DataFrame(recs, columns=cols)       # explicit columns: a clean series (Tetouan, NB6) has no run at all


def group_by_start(df, tol=TOL):
    """Runs whose start lies within tol of the group's first start form one item (v0 semantics), per system."""
    df = df.sort_values(["system", "start", "city", "zone"]).reset_index(drop=True)
    gid, ids, first, sys_ = -1, [], None, None
    for r in df.itertuples():
        if first is None or r.system != sys_ or r.start - first > tol:
            gid, first, sys_ = gid + 1, r.start, r.system
        ids.append(gid)
    df["group"] = ids
    return df


def iou(s1, e1, s2, e2):
    """Time IoU between [s1, e1) and arrays [s2, e2)."""
    s1, e1 = np.datetime64(s1, "ns"), np.datetime64(e1, "ns")
    s2, e2 = np.asarray(s2, dtype="datetime64[ns]"), np.asarray(e2, dtype="datetime64[ns]")
    inter = (np.minimum(e1, e2) - np.maximum(s1, s2)) / np.timedelta64(1, "m")
    union = (np.maximum(e1, e2) - np.minimum(s1, s2)) / np.timedelta64(1, "m")
    return np.where(inter > 0, inter / np.maximum(union, 1e-9), 0.0)


# ---------------------------------------------------------------- dead items
def restoration(data, exp, rr, fill_after):
    """r_E, pi_E, tau_E (eq. 3) and pre-event ratio, aligned at each zone's own restoration time.
    About 1 in 5 southern dead runs returns through a straight-line ramp (a linear fill). Restoration is
    measured after that synthetic ramp, so r, pi and tau describe recorded data, not interpolation.
    fill_after: (city, zone, dead_end) -> index just past the interp run that starts there."""
    step = pd.Timedelta(STEP[rr.city.iloc[0]])
    n30 = max(1, int(pd.Timedelta("30min") / step))
    n60 = max(1, int(pd.Timedelta("60min") / step))
    nramp = int(pd.Timedelta("6h") / step)
    num, den = np.zeros(nramp), np.zeros(nramp)
    pre_n = pre_d = 0.0
    n_fill, fill_steps = 0, 0
    for r in rr.itertuples():
        x, xh = data[r.city][r.zone].to_numpy(), exp[r.city][r.zone].to_numpy()
        k = r.b + 1
        if (r.city, r.zone, r.end) in fill_after:
            k2 = fill_after[(r.city, r.zone, r.end)]
            n_fill, fill_steps = n_fill + 1, max(fill_steps, k2 - k)
            k = k2
        xa, ha = x[k:k + nramp], xh[k:k + nramp]
        ok = ~np.isnan(xa) & ~np.isnan(ha)
        num[:len(xa)] += np.where(ok, xa, 0)
        den[:len(xa)] += np.where(ok, ha, 0)
        xp, hp = x[max(0, r.a - n30):r.a], xh[max(0, r.a - n30):r.a]
        okp = ~np.isnan(xp) & ~np.isnan(hp)
        pre_n += xp[okp].sum()
        pre_d += hp[okp].sum()
    with np.errstate(invalid="ignore", divide="ignore"):
        ratio = np.where(den > 0, num / den, np.nan)
    r_E = num[:n30].sum() / den[:n30].sum() if den[:n30].sum() > 0 else np.nan
    pi_E = np.nanmax(ratio[:n60]) if np.isfinite(ratio[:n60]).any() else np.nan
    hit = np.where(ratio >= 0.9)[0]
    tau = float(hit[0] * step.total_seconds() / 60) if len(hit) else np.nan
    pre = pre_n / pre_d if pre_d > 0 else np.nan
    return r_E, pi_E, tau, pre, n_fill, fill_steps * step.total_seconds() / 60


def dead_items(data, exp, zr):
    dr = group_by_start(zr[zr.kind == "dead"])
    fills = zr[zr.kind.isin(["hold", "interp"])]
    zcount = {c: d.shape[1] for c, d in data.items()}
    ip = zr[zr.kind == "interp"]
    fill_after = {(r.city, r.zone, r.start): r.b + 1 for r in ip.itertuples()}
    rows = []
    for g, rr in dr.groupby("group"):
        s, e = rr.start.min(), rr.end.max()
        system = rr.system.iloc[0]
        cities = sorted(rr.city.unique())
        n_steps = rr.steps.sum()
        r_E, pi_E, tau, pre, n_fill, fill_min = restoration(data, exp, rr, fill_after)
        # R3 / R21: a fill run in the same zone ends exactly where the dead run starts
        f_sys = fills[fills.system == system]
        adj = f_sys.merge(rr[["city", "zone", "start"]], left_on=["city", "zone", "end"], right_on=["city", "zone", "start"],
                          suffixes=("", "_dead"))
        # R4 / R21: fill runs in other zones that are co-extensive with the dead event
        dead_codes = set(rr.code)
        other = f_sys[~f_sys.code.isin(dead_codes)]
        co = other[iou(s, e, other.start.to_numpy(), other.end.to_numpy()) >= COEXT_IOU]
        # R8: are the other cities of the same system alive during the event?
        alive = []
        for c in data:
            if SYSTEM[c] != system or c in cities:
                continue
            tot = data[c][s:e - pd.Timedelta(STEP[c])].sum(axis=1, min_count=1)
            etot = exp[c][s:e - pd.Timedelta(STEP[c])].sum(axis=1, min_count=1)
            alive.append(float((tot / etot).median()))
        rows.append(dict(
            kind="dead", system=system, start=s, end=e, duration_h=round((e - s).total_seconds() / 3600, 2),
            cities="+".join(cities), n_cities=len(cities), zones=",".join(sorted(rr.code)), n_zones=rr.code.nunique(),
            frac_zones=round(max(rr[rr.city == c].zone.nunique() / zcount[c] for c in cities), 2),
            eta=round(float(rr.n_zero.sum() / n_steps), 3),
            restore_ratio=round(r_E, 3) if pd.notna(r_E) else np.nan,
            peak_ratio=round(pi_E, 3) if pd.notna(pi_E) else np.nan,
            ramp_min=tau, pre_ratio=round(pre, 3) if pd.notna(pre) else np.nan,
            fill_ramp_zones=n_fill, fill_ramp_min=fill_min,
            start_hour=s.hour, weekday=s.day_name()[:3],
            hold_to_dead=int((adj.kind == "hold").sum()), interp_to_dead=int((adj.kind == "interp").sum()),
            coext_hold_zones=int(co[co.kind == "hold"].code.nunique()),
            coext_interp_zones=int(co[co.kind == "interp"].code.nunique()),
            others_alive=round(min(alive), 3) if alive else np.nan,
            _codes=sorted(rr.code), _bounds=sorted(set(rr.start) | set(rr.end)),
        ))
    return pd.DataFrame(rows)


def vote_dead(it):
    v = {}
    multi = it.n_cities >= 2
    if multi and it.eta >= R1_ETA and abs(it.restore_ratio - 1) <= R1_R and it.ramp_min <= R1_TAU:
        v["R1"] = "A1"
    if it.hold_to_dead > 0:
        v["R3"] = "A1"
    if it.coext_hold_zones > 0:
        v["R4"] = "A1"
    if it.peak_ratio >= R5_PI:
        v["R5"] = "G"
    if it.eta < R6_ETA:
        v["R6"] = "G"
    if it.interp_to_dead > 0 or it.coext_interp_zones > 0:
        v["R21"] = "A1"
    # R7: the guide excludes R2/R3/R4. v1 also excludes R21, because a linear fill is fill evidence too.
    fill_evidence = any(k in v for k in ("R3", "R4", "R21"))
    if multi and not fill_evidence and ("R5" in v or "R6" in v or not (it.ramp_min <= R7_TAU)):
        v["R7"] = "G1"
    if it.n_cities == 1 and it.frac_zones >= R8_FRAC and (pd.isna(it.others_alive) or it.others_alive > R8_ALIVE):
        v["R8"] = "G2"
    if it.n_zones == 1:
        v["R9"] = "G3"
        if R10_HOURS[0] <= it.start_hour <= R10_HOURS[1] and it.duration_h <= R10_MAXDUR:
            v["R10"] = "G4"
        if it.duration_h > R11_DUR:
            v["R11"] = "G3"
    return v


# ---------------------------------------------------------------- fill items
def fill_items(data, masks, zr):
    fr = group_by_start(zr[zr.kind.isin(["hold", "interp"])])
    dead = zr[zr.kind == "dead"]
    rows = []
    for g, rr in fr.groupby("group"):
        s, e = rr.start.min(), rr.end.max()
        system = rr.system.iloc[0]
        vary = np.nan
        if rr.code.nunique() == 1:
            r = rr.iloc[0]
            nb = [z for z in data[r.city].columns if z != r.zone]
            if nb:
                sl = slice(r.a, r.b + 1)
                d = data[r.city][nb].iloc[sl]
                bad = (masks[r.city]["dead"][nb] | masks[r.city]["hold"][nb] | masks[r.city]["interp"][nb]).iloc[sl]
                moving = data[r.city][nb].diff().iloc[sl].ne(0) & d.notna()
                vary = round(float((moving & ~bad).to_numpy().mean()), 3)
        d_sys = dead[dead.system == system]
        nxt = rr.merge(d_sys[["city", "zone", "start"]], left_on=["city", "zone", "end"], right_on=["city", "zone", "start"],
                       suffixes=("", "_dead"))
        other = d_sys[~d_sys.code.isin(set(rr.code))]
        coext = other[iou(s, e, other.start.to_numpy(), other.end.to_numpy()) >= COEXT_IOU]
        kinds = set(rr.kind)
        rows.append(dict(
            kind="fill", system=system, start=s, end=e, duration_h=round((e - s).total_seconds() / 3600, 2),
            cities="+".join(sorted(rr.city.unique())), n_cities=rr.city.nunique(),
            zones=",".join(sorted(rr.code)), n_zones=rr.code.nunique(),
            n_hold_zones=int(rr[rr.kind == "hold"].code.nunique()), n_interp_zones=int(rr[rr.kind == "interp"].code.nunique()),
            fill_kind="mixed" if len(kinds) > 1 else kinds.pop(), max_points=int(rr.steps.max()),
            start_hour=s.hour, weekday=s.day_name()[:3],
            neighbours_vary=vary, fill_to_dead=int(len(nxt)), coext_dead_zones=int(coext.code.nunique()),
            _codes=sorted(rr.code), _bounds=sorted(set(rr.start) | set(rr.end)),
        ))
    return pd.DataFrame(rows)


def vote_fill(it):
    v = {}
    if it.n_hold_zones >= 2:
        v["R2"] = "A2"
    if it.n_interp_zones >= 2:
        v["R19"] = "A2"
    if it.n_zones == 1 and it.neighbours_vary >= R12_VARY:
        if it.fill_kind == "hold":
            v["R12"] = "A3"
        elif it.fill_kind == "interp":
            v["R20"] = "A3"
    return v


# ---------------------------------------------------------------- clock items
def city_profile(d, bad, a, b):
    x = d[a:b].where(~bad[a:b])
    p = x.groupby(x.index.hour * 60 + x.index.minute).mean()
    return (p / p.mean()).mean(axis=1)


def clock_offset(d, bad, step, D, days=7, max_min=120):
    """delta*(D) of eq. 9 in minutes, plus corr at 0 and at delta*. NaN when 7 days are missing on a side."""
    D = pd.Timestamp(D)
    stp = pd.Timedelta(step)
    if not (d.index[0] <= D - pd.Timedelta(days=days) and D + pd.Timedelta(days=days + 1) <= d.index[-1]):
        return np.nan, np.nan, np.nan
    pre = city_profile(d, bad, D - pd.Timedelta(days=days), D - stp)
    post = city_profile(d, bad, D + pd.Timedelta(days=1), D + pd.Timedelta(days=days + 1) - stp)
    if len(pre) != len(post) or pre.isna().any() or post.isna().any():
        return np.nan, np.nan, np.nan
    m = int(stp.total_seconds() // 60)
    ks = np.arange(-max_min // m, max_min // m + 1)
    corr = np.array([np.corrcoef(pre.values, np.roll(post.values, -k))[0, 1] for k in ks])
    i = int(np.nanargmax(corr))
    return float(ks[i] * m), float(corr[len(ks) // 2]), float(corr[i])


def clock_items(raw, data, masks):
    audit = pd.DataFrame(sum((audit_timestamps(c, df) for c, df in raw.items()), []))
    if audit.empty:                       # a perfectly regular timeline (Tetouan, NB6) has no stamp anomaly
        audit = pd.DataFrame(columns=["city", "kind", "timestamp", "n"]).astype({"timestamp": "datetime64[ns]", "n": int})
    eu, ma = set(pd.to_datetime(EUROPE_DST)), set(pd.to_datetime(MOROCCO_DST))
    rows = []
    for c, d in data.items():
        a = audit[audit.city == c]
        dup = a[a.kind == "duplicate"].timestamp.dt.normalize().value_counts()
        miss = a[a.kind == "missing_run"].assign(day=lambda t: t.timestamp.dt.normalize()).groupby("day").n.sum()
        bad = masks[c]["dead"] | masks[c]["hold"] | masks[c]["interp"]
        for D in sorted(eu | ma | set(dup.index) | set(miss.index)):
            if not (d.index[0] <= D <= d.index[-1]):
                continue
            delta, c0, cb = clock_offset(d, bad, STEP[c], D)
            rows.append(dict(
                kind="clock", system=SYSTEM[c], start=D, end=D + pd.Timedelta("1D"), duration_h=24.0,
                cities=c, n_cities=1, zones="", n_zones=0,
                europe_date=D in eu, morocco_date=D in ma,
                n_duplicate_stamps=int(dup.get(D, 0)), n_missing_steps=int(miss.get(D, 0)),
                delta_star_min=delta, corr_at_0=round(c0, 4) if pd.notna(c0) else np.nan,
                corr_best=round(cb, 4) if pd.notna(cb) else np.nan,
            ))
    return pd.DataFrame(rows)


def vote_clock(it):
    v = {}
    if it.n_duplicate_stamps > 0:
        v["R13"] = "A4"
    if it.n_missing_steps > 0 and (it.europe_date or it.morocco_date):
        v["R14"] = "A4"
    if (pd.notna(it.delta_star_min) and abs(it.delta_star_min) >= R15_DELTA
            and it.corr_best >= R15_MIN_CORR and it.corr_best - it.corr_at_0 >= R15_MIN_GAIN):
        v["R15"] = "A4"
    return v


# ---------------------------------------------------------------- transfer items
def transfer_items(data):
    t = transfers(data)
    rows = []
    for r in t.itertuples():
        D = pd.Timestamp(r.day)
        rows.append(dict(
            kind="transfer", system=SYSTEM[r.city], start=D, end=D + pd.Timedelta("1D"), duration_h=24.0,
            cities=r.city, n_cities=1,
            zones=f"{CITY_SHORT[r.city]}{r.zone_up[-1]},{CITY_SHORT[r.city]}{r.zone_down[-1]}", n_zones=2,
            zone_up=r.zone_up, delta_up=r.delta_up, zone_down=r.zone_down, delta_down=r.delta_down,
            kappa=r.conservation_index))
    return pd.DataFrame(rows)


def vote_transfer(it):
    return {"R16": "G5"} if it.kappa <= R16_KAPPA else {}


# ---------------------------------------------------------------- episodes, summaries
def episodes(items):
    """Link dead and fill items of one system into compound episodes (e.g. hold -> zero).
    Two items are linked if they overlap or touch (gap <= TOL) and either a run boundary of one lies
    within TOL of a run boundary of the other, or they are co-extensive (IoU >= COEXT_IOU)."""
    ev = items[items.kind.isin(["dead", "fill"])]
    parent = {i: i for i in ev.index}

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    idx = list(ev.index)
    for n, i in enumerate(idx):
        a = ev.loc[i]
        for j in idx[n + 1:]:
            b = ev.loc[j]
            if a.system != b.system or b.start > a.end + TOL or a.start > b.end + TOL:
                continue
            near = any(abs(x - y) <= TOL for x in a["_bounds"] for y in b["_bounds"])
            if near or iou(a.start, a.end, np.array([b.start]), np.array([b.end]))[0] >= COEXT_IOU:
                parent[find(i)] = find(j)
    roots = {i: find(i) for i in idx}
    order = {r: k for k, r in enumerate(sorted(set(roots.values()), key=lambda r: ev.loc[r].start))}
    out = pd.Series(np.nan, index=items.index, dtype=object)
    for i, r in roots.items():
        out[i] = f"EP{order[r]:03d}"
    return out


def compatible(l1, l2):
    return l1 == l2 or (l1[0] == "G" and l2[0] == "G" and "G" in (l1, l2))


def majority(votes):
    """Inspection-only label (the label model replaces it in NB2): majority over specific types.
    Family 'G' votes back the specific G types if any were voted, otherwise they count as one candidate 'G?'."""
    labels = list(votes.values())
    if not labels:
        return "abstain"
    score = pd.Series([l for l in labels if l != "G"], dtype=object).value_counts().astype(float)
    nG = labels.count("G")
    g_spec = [k for k in score.index if k.startswith("G")]
    if nG and g_spec:
        score[g_spec] += nG / len(g_spec)
    elif nG:
        score["G?"] = nG
    top = score[score == score.max()]
    return top.index[0] if len(top) == 1 else "conflict:" + "|".join(sorted(top.index))


def rule_summary(items, votes):
    rows = []
    for r in RULES:
        kind = RULE_KIND[r]
        n_kind = int((items.kind == kind).sum())
        fired = votes[r].notna()
        others = votes.drop(columns=[r])
        overlap = conflict = 0
        for i in votes.index[fired]:
            ov = others.loc[i].dropna()
            overlap += int(len(ov) > 0)
            conflict += int(any(not compatible(votes.at[i, r], l) for l in ov))
        rows.append(dict(rule=r, family=RULE_FAMILY[r], item_kind=kind, n_items_of_kind=n_kind,
                         n_votes=int(fired.sum()), coverage=round(fired.sum() / n_kind, 3) if n_kind else np.nan,
                         labels=",".join(sorted(votes.loc[fired, r].unique())) if fired.any() else "",
                         overlap=overlap, conflict=conflict))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- pipeline
def build(path):
    raw = load(path)
    data = {c: regularise(c, df) for c, df in raw.items()}
    return build_from_data(raw, data)


def build_from_data(raw, data):
    """Everything after loading: used by build() and by the injection benchmark (NB4), which edits `data`.
    raw is only used for the clock items (duplicate and missing stamps)."""
    exp = {c: d.apply(lambda s, c=c: expected(s, c)) for c, d in data.items()}
    masks = state_masks(data, exp)
    zr = zone_runs(data, masks)
    parts = [dead_items(data, exp, zr), fill_items(data, masks, zr), clock_items(raw, data, masks), transfer_items(data)]
    parts = [p for p in parts if len(p)]  # a clean series (Tetouan, NB6) has no dead or fill item
    voters = {"dead": vote_dead, "fill": vote_fill, "clock": vote_clock, "transfer": vote_transfer}
    prefix = {"dead": "D", "fill": "F", "clock": "K", "transfer": "T"}
    for p in parts:
        p["item_id"] = [f"{prefix[k]}{i:03d}" for i, k in enumerate(p.kind)]
    items = pd.concat(parts, ignore_index=True)
    items["episode"] = episodes(items)
    vote_rows = []
    for it in items.itertuples():
        v = voters[it.kind](it)
        vote_rows.append({r: v.get(r, np.nan) for r in RULES})
    votes = pd.DataFrame(vote_rows, index=items.index, columns=RULES)
    items["n_votes"] = votes.notna().sum(axis=1)
    items["votes"] = [";".join(f"{r}:{l}" for r, l in row.dropna().items()) for _, row in votes.iterrows()]
    items["mv_label"] = [majority(row.dropna().to_dict()) for _, row in votes.iterrows()]
    items = items.drop(columns=["_codes", "_bounds"], errors="ignore")
    first = ["item_id", "kind", "episode", "system", "start", "end", "duration_h", "cities", "zones",
             "n_cities", "n_zones", "mv_label", "n_votes", "votes"]
    items = items[first + [c for c in items.columns if c not in first]]
    votes.insert(0, "item_id", items.item_id)
    summary = rule_summary(items, votes.set_index("item_id"))
    return dict(items=items, votes=votes, zone_runs=zr.drop(columns=["a", "b"]), rule_summary=summary,
                data=data, exp=exp, masks=masks, raw=raw)


def main(path, out):
    os.makedirs(out, exist_ok=True)
    res = build(path)
    for k in ("items", "votes", "zone_runs", "rule_summary"):
        res[k].to_csv(os.path.join(out, f"{k}.csv"), index=False)
    it = res["items"]
    print(it.groupby("kind").size().to_string())
    print(res["rule_summary"].to_string(index=False))
    print("done ->", out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "results/catalogue_v1")
