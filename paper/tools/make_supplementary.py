"""Build the supplementary material (D107): paper/supplementary/supplementary.tex and its figures.

Every table is generated from the stored result files (no number is typed by hand); numbers are rounded half-up
from the stored values. The figures are drawn by src/paper_supplement.py (no title inside the image, no internal
codes). Only packages that the article itself uses or that ship with every LaTeX installation are loaded, so the
file builds locally and on Overleaf.

    python paper/tools/make_supplementary.py            # tables + figures (about 2 min: rule engine, injector)
    python paper/tools/make_supplementary.py --no-figures
    cd paper/supplementary && latexmk -pdf supplementary.tex
"""
import json
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "results"
TAB = RES / "paper" / "tables"
OUT = ROOT / "paper" / "supplementary"
FIG = OUT / "figures"
REPO_URL = "https://github.com/farah1902/grid-event-or-data-artefact-code"


# ---------------------------------------------------------------- formatting
def r(x, nd=3):
    """Half-up rounding of a stored value; '--' for a missing one. Refuses a value stored with too few digits to round
    safely (its digits beyond nd are exactly 5): rounding it again could differ from rounding the unrounded value."""
    if x is None or (isinstance(x, (float, np.floating)) and np.isnan(x)) or (isinstance(x, str) and x.strip() in ("", "nan")):
        return "--"
    d = Decimal(repr(float(x)))
    tail = format(d, "f").split(".")[1][nd:] if "." in format(d, "f") else ""
    if tail.rstrip("0") == "5":
        raise ValueError(f"{x} cannot be rounded safely to {nd} decimals (stored rounded); show it as stored")
    return str(d.quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP))


def pct1(x):
    """A stored share (3 decimals) as a percentage with one decimal: exact, no re-rounding."""
    return str((Decimal(repr(float(x))) * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)) + r"\%"


DAG = r"$^{\dagger}$"


def pv(p):
    if p is None or (isinstance(p, float) and np.isnan(p)):
        return "--"
    return r"$<$0.001" if float(p) < 0.0005 else r(p)


def tx(s):
    """Plain text -> LaTeX: escape the special characters and set the symbols in math."""
    s = str(s)
    for a, b in [("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("#", r"\#"), ("_", r"\_"), ("{", r"\{"),
                 ("}", r"\}"), ("$", r"\$"), ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}")]:
        s = s.replace(a, b)
    for a, b in [("x̂", r"$\hat{x}$"), ("±", r"$\pm$"), ("≤", r"$\leq$"), ("≥", r"$\geq$"), ("→", r"$\rightarrow$"),
                 ("−", r"$-$"), ("×", r"$\times$"), ("β", r"$\beta$"), ("κ", r"$\kappa$"), ("π", r"$\pi$"),
                 ("δ", r"$\delta$"), ("η", r"$\eta$"), ("γ", r"$\gamma$"), ("ρ", r"$\rho$"), ("α", r"$\alpha$"),
                 ("·", r"$\cdot$"), ("*", r"$^{*}$")]:
        s = s.replace(a, b)
    return s


def zones_short(s):
    """'B1,B2,B3,F1,...' -> 'B1--B3, F1--F7'."""
    s = str(s)
    if s.startswith("15 zones"):
        return "all 15 southern zones"
    out, cur = [], None
    for z in s.split(","):
        c, n = z[0], int(z[1:])
        if cur and cur[0] == c and n == cur[2] + 1:
            cur[2] = n
        else:
            if cur:
                out.append(cur)
            cur = [c, n, n]
    out.append(cur)
    return ", ".join(f"{c}{a}" if a == b else (f"{c}{a}, {c}{b}" if b == a + 1 else f"{c}{a}--{c}{b}") for c, a, b in out)


def mean_of(s):
    """The mean of a stored 'mean ± s.d.' string, digits as stored."""
    return str(s).split("±")[0].strip()


def pct(x):
    return f"{int(round(float(x) * 100))}\\%"


METHOD = {  # stored method names -> the article's terms
    "ours (rules + detector)": "Full method", "rules only (rule engine v1)": "Rules alone",
    "TCN-GAT, hierarchy, multi-scale": "Main detector",
    "main detector: TCN-GAT, hierarchy, multi-scale": "Main detector",
    "TCN-GAT, hierarchy, multi-scale (NB3 event formation)": "Main detector, untuned event formation",
    "TCN-GAT, NB3 event formation (untuned)": "Main detector, untuned event formation",
    "LightGBM forecast, hierarchy, multi-scale": "LightGBM residual",
    "LightGBM forecast, hierarchy, multi-scale (NB3 event formation)": "LightGBM residual, untuned event formation",
    "LightGBM, NB3 event formation (untuned)": "LightGBM residual, untuned event formation",
    "LightGBM + learned-graph correction, hierarchy, multi-scale": "LightGBM + learned-graph correction",
    "LightGBM + TCN correction (no graph), hierarchy, multi-scale": "LightGBM + TCN correction (no graph)",
    "mean(LightGBM, TCN-GAT), hierarchy, multi-scale": "Mean of LightGBM and TCN-GAT",
    "single scale (raw band)": "Main detector, raw band only",
    "main detector, single scale (raw band)": "Main detector, raw band only",
    "main detector, no hierarchy (flat residual)": "Main detector, no hierarchy (flat zone score)",
    "LGB nowcast (raw, hierarchy)": "LightGBM nowcast, raw band",
    "LGB nowcast, raw (all zones, no learned edges)": "LightGBM nowcast, raw band",
    "TCN, no graph, raw": "TCN without the graph, raw band",
    "TCN-GAT, learned graph, raw": "Main detector, raw band only",
    "TCN, no graph, hierarchy, multi-scale": "Main detector without the graph",
    "TCN, no graph, hierarchy, multi-scale (own tuned event formation)": "Main detector without the graph, own event formation",
    "STL + MAD": "STL", "Isolation Forest": "Isolation Forest", "LOF": "LOF", "GDN": "GDN", "USAD": "USAD",
}


def m(name):
    return METHOD.get(name, name)


# ---------------------------------------------------------------- table writers
def ragged(colspec):
    """Paragraph columns set ragged right (no stretched word spaces in narrow cells)."""
    return colspec.replace("p{", r">{\raggedright\arraybackslash}p{")


def table(label, caption, colspec, head, rows, size=r"\footnotesize", sep="4pt"):
    """A non-floating table (caption above, kept on one page), placed where it is written."""
    colspec = ragged(colspec)
    body = "\n".join(r"\midrule" if row == "MID" else " & ".join(row) + r" \\" for row in rows)
    return (f"\\begin{{stable}}\n\\caption{{{caption}}}\\label{{{label}}}\n{size}\\setlength{{\\tabcolsep}}{{{sep}}}\n"
            f"\\begin{{tabular}}{{{colspec}}}\n\\toprule\n{head}\n\\midrule\n{body}\n\\bottomrule\n\\end{{tabular}}\n\\end{{stable}}\n")


def longtable(label, caption, colspec, head, rows, size=r"\footnotesize", sep="4pt"):
    import re
    bare = re.sub(r"[@p]\{[^}]*\}", lambda g: "p" if g.group(0)[0] == "p" else "", colspec)   # drop @{..}; p{..} -> p
    n = sum(bare.count(k) for k in "lrcp")
    colspec = ragged(colspec)
    body = "\n".join(r"\midrule" if row == "MID" else " & ".join(row) + r" \\" for row in rows)
    return (f"\\begingroup{size}\\setlength{{\\tabcolsep}}{{{sep}}}\n\\begin{{longtable}}{{{colspec}}}\n"
            f"\\caption{{{caption}}}\\label{{{label}}}\\\\\n\\toprule\n{head}\n\\midrule\n\\endfirsthead\n"
            f"\\multicolumn{{{n}}}{{@{{}}l}}{{\\emph{{Table \\thetable, continued}}}}\\\\\n\\toprule\n{head}\n\\midrule\n\\endhead\n"
            f"\\bottomrule\n\\endfoot\n{body}\n\\end{{longtable}}\n\\endgroup\n")


def figure(name, label, caption):
    return (f"\\begin{{sfigure}}\n\\includegraphics[width=\\textwidth]{{figures/{name}}}\n"
            f"\\caption{{{caption}}}\\label{{{label}}}\n\\end{{sfigure}}\n")


def rd(f, **kw):
    return pd.read_csv(f, encoding="utf-8", **kw)


# ---------------------------------------------------------------- S1: real-data events
def t_key_events():
    k = rd(TAB / "Table4_key_events.csv")
    k["t"] = pd.to_datetime(k.start)                        # episodes in time order, items in time order within each
    k["t0"] = k.groupby("episode").t.transform("min")
    k = k.sort_values(["t0", "t"], kind="mergesort")
    rows, prev = [], None
    for x in k.itertuples():
        if prev is not None and x.episode != prev:
            rows.append("MID")
        prev = x.episode
        rows.append([pd.Timestamp(x.start).strftime("%Y-%m-%d %H:%M"), r(x.duration_h, 2), zones_short(x.zones), x.kind, x.label,
                     r(x.confidence, 2), tx(x.episode_sequence)])
    head = r"Start & Duration (h) & Zones & Item & Label & Conf. & Episode: labels in time order \\"
    cap = ("Key events on the real data. Each row is a rule item with its final label and confidence; rows between two "
           "horizontal lines form one episode, whose items' labels are listed in time order with their confidence. Times "
           "as recorded. The January 2023 episode is shown in Fig.~4 of the article, the episode of 31 March -- 2 April "
           "2024 in Fig.~5 and the episode of 16 July 2023 in Fig.~\\ref{fig:s-jul2023}.")
    return table("tab:s-key-events", cap, r"@{}l r l l c c p{4.3cm}@{}", head, rows, size=r"\scriptsize", sep="3.5pt")


def t_clock(items, cat):
    c = items[items.kind == "clock"].merge(cat[["item_id", "label", "confidence"]], on="item_id", how="left")
    c["start"] = pd.to_datetime(c.start)
    order = {"Laayoune": 0, "Boujdour": 1, "Foum eloued": 2, "Marrakech": 3}
    c = c.assign(o=c.cities.map(order)).sort_values(["o", "start"])
    name = {"Laayoune": "Laâyoune", "Boujdour": "Boujdour", "Foum eloued": "Foum El Oued", "Marrakech": "Marrakech"}
    rows, prev = [], None
    for x in c.itertuples():
        if prev is not None and x.cities != prev:
            rows.append("MID")
        prev = x.cities
        cal = "Europe" if x.europe_date else ("Morocco" if x.morocco_date else "--")
        d = "--" if pd.isna(x.delta_star_min) else ("0" if x.delta_star_min == 0 else f"{int(x.delta_star_min):+d}")
        rows.append([x.start.strftime("%Y-%m-%d"), name[x.cities], cal, str(int(x.n_duplicate_stamps)), str(int(x.n_missing_steps)),
                     d, r(x.corr_at_0, 4), r(x.corr_best, 4), f"{x.label} ({r(x.confidence, 2)})"])     # correlations as stored
    head = (r"Date & City & Calendar & Duplicated & Missing & $\delta^{*}$ & Corr. & Corr. & Final label \\" "\n"
            r" & & change & stamps & steps & (min) & at 0 & at $\delta^{*}$ & (confidence) \\")
    cap = ("Clock days: the rule items of kind clock. Calendar change: the European change of summer time (Europe) or "
           "Morocco's suspension of GMT+1 for Ramadan and its return (Morocco); the other Marrakech days have stamp "
           "anomalies only. Duplicated stamps and missing steps come from the audit of the recorded time stamps. "
           "$\\delta^{*}$ is the shift (within $\\pm$120~min) that maximises the correlation between the mean daily profiles "
           "of the 7 days before and the 7 days after the date (Fig.~\\ref{fig:s-clock}); the correlations are those at zero "
           "shift and at $\\delta^{*}$. Final label of the label model.")
    return longtable("tab:s-clock", cap, r"@{}l l l r r r r r l@{}", head, rows, size=r"\scriptsize", sep="4pt")


def t_transfers(items, cat):
    t = items[items.kind == "transfer"].merge(cat[["item_id", "label", "confidence"]], on="item_id", how="left")
    t = t.assign(start=pd.to_datetime(t.start)).sort_values("start")
    short = {"Laayoune": "L", "Boujdour": "B", "Foum eloued": "F"}
    name = {"Boujdour": "Boujdour", "Foum eloued": "Foum El Oued", "Laayoune": "Laâyoune"}
    rows = [[x.start.strftime("%Y-%m-%d"), name[x.cities], f"{short[x.cities]}{x.zone_up[-1]} ({r(x.delta_up, 1)})",
             f"{short[x.cities]}{x.zone_down[-1]} ({r(x.delta_down, 1)})", r(x.kappa, 2), f"{x.label} ({r(x.confidence, 2)})"]
            for x in t.itertuples()]
    head = r"Day & City & Zone up ($\Delta$, A) & Zone down ($\Delta$, A) & $\kappa$ & Final label (confidence) \\"
    cap = ("Candidate load-transfer days: the rule items of kind transfer. On each day, the 14-day median of one zone's "
           "daily mean current rises and another's falls, each by more than 25\\% of the zone's mean level ($\\Delta$: "
           "median of the 14 days after minus median of the 14 days ending on the day). The conservation index "
           "$\\kappa = |\\sum_z \\Delta_z| / \\max(\\Delta_{\\mathrm{up}}, -\\Delta_{\\mathrm{down}})$ is computed over all zones of the "
           "city; rule R16 votes G5 when $\\kappa \\leq 0.3$. Fig.~\\ref{fig:s-transfer} shows the only conserved transfer.")
    return table("tab:s-transfers", cap, r"@{}l l l l r l@{}", head, rows)


# ---------------------------------------------------------------- S2: rules and label model
FAMILY = {"simultaneity": "simultaneity", "hold": "holds", "restoration": "restoration", "city": "city",
          "single_zone": "single zone", "calendar": "calendar", "clock": "clock", "conservation": "conservation",
          "interpolation": "straight-line fills"}
FAMILY_ADJ = {"simultaneity": "simultaneity", "hold": "hold", "restoration": "restoration", "city": "city",       # "the X rules"
              "single_zone": "single-zone", "calendar": "calendar", "clock": "clock", "conservation": "conservation",
              "interpolation": "straight-line-fill"}


def t_rule_params():
    p = rd(TAB / "TableS1_rule_parameters.csv")
    sp = {"G1+G2+G3+G4+G5": "G1--G5", "G3+G4": "G3, G4"}
    rows = [[x.rule + (DAG if x.defining else ""), FAMILY[x.family], x.output, sp.get(x.speaks_for, x.speaks_for),
             str(int(x.n_applicable)), str(int(x.n_fired)), r(x.a_propensity, 4), r(x.b_false_positive, 4), r(x.log_odds_a_over_b, 2),
             r(x.learned_precision, 3)] for x in p.itertuples()]          # as stored (4, 4, 2 and 3 decimals)
    head = (r"Rule & Family & Output & Speaks for & Applicable & Fired & $a$ & $b$ & $\ln(a/b)$ & Learned \\" "\n"
            r" & & & & items & & & & & precision \\")
    cap = ("Learned parameters of the constrained label model on the real data. For each rule: the classes its output speaks "
           "for, the items on which it is applicable (its precondition can be observed) and on which it fires, the propensity "
           "$a$ (probability of the output when the item's class is one the output speaks for), the false-positive rate $b$ "
           "(probability of the output otherwise), the evidence $\\ln(a/b)$ and the learned precision (mean posterior mass on "
           "the classes the output speaks for, over the items the rule fires on). $^{\\dagger}$Defining rule, with the prior "
           "Beta(9, 1) on $a$ instead of Beta(1, 1). R7 never fires on the real data and has no row.")
    return table("tab:s-rule-params", cap, r"@{}l l c l r r r r r r@{}", head, rows, size=r"\scriptsize")


def t_stability():
    s = rd(RES / "labels_v1" / "restart_stability.csv", index_col=0)
    sn = json.loads((RES / "labels_v1" / "snorkel" / "summary.json").read_text(encoding="utf-8"))
    st = rd(RES / "labels_v1" / "snorkel" / "stability_seeds.csv")
    rows = [["Constrained label model (ours)", "20 restarts", r(s.loc["constrained", "min"]), r(s.loc["constrained", "mean"]), "0"],
            ["Unconstrained Dawid--Skene model", "20 restarts", r(s.loc["full (guide)", "min"]), r(s.loc["full (guide)", "mean"]), "0"],
            ["Snorkel label model", f"{len(st)} seeds", r(sn["stability_min"]), r(sn["stability_mean"]), str(int(sn["infeasible_labels"]))]]
    head = r"Label model & Runs & Agreement, min & Agreement, mean & Labels outside $\mathcal{Y}(i)$ \\"
    cap = ("Stability of the labels on the real data (327 rule items). Agreement: share of items whose label equals the "
           "label of the kept restart (Dawid--Skene models; the restart with the highest penalised log-likelihood is kept) or "
           "of seed~0 (Snorkel). The constrained and unconstrained models restrict every item to its feasible set "
           f"$\\mathcal{{Y}}(i)$; Snorkel's label model does not. Snorkel's labels agree with ours on {r(sn['agree_with_ours'])} "
           "of the items.")
    return table("tab:s-stability", cap, r"@{}l l r r r@{}", head, rows)


def t_recovery():
    rec = rd(TAB / "TableS2_label_model_recovery.csv", header=[0, 1], index_col=0)
    name = {"DS constrained": "Constrained label model (ours)", "DS full (guide)": "Unconstrained Dawid--Skene model",
            "majority vote": "Majority vote"}
    rows = []
    for lab, x in rec.iterrows():
        rows.append([name[lab]] + [f"{r(x[(k, 'mean')])} $\\pm$ {r(x[(k, 'std')])}" if pd.notna(x[(k, "mean")]) else "--"
                                   for k in ("accuracy", "macro_f1", "ece", "brier")])
    head = r"Labeller & Accuracy & Macro-F1 & ECE & Brier score \\"
    cap = ("Recovery of known classes. Classes and votes are simulated for the 327 real items from the fitted constrained "
           "model, the label models are refitted on the simulated votes, and the recovered labels are scored against the "
           "simulated classes (mean $\\pm$ s.d. over the simulation runs; ECE with 10 equal-width bins).")
    return table("tab:s-recovery", cap, r"@{}l c c c c@{}", head, rows)


def t_robustness():
    t = rd(TAB / "TableS3_label_robustness.csv")
    prior = {"prior_b=(1,4)": r"prior Beta(1, 4) on $b$ (default Beta(1, 9))",
             "prior_b=(1,19)": r"prior Beta(1, 19) on $b$",
             "no defining prior": r"no defining-rule prior (Beta(1, 1) on every $a$)",
             "prior_pi=0.5": r"class-prior pseudo-count $\gamma$ = 0.5 (default 1)",
             "prior_pi=2": r"class-prior pseudo-count $\gamma$ = 2",
             "init a=0.9,b=0.02": r"initial $a$ = 0.9, $b$ = 0.02 (default 0.7, 0.05)"}
    rows, prev = [], None
    for x in t.itertuples():
        if prev is not None and x.test != prev:
            rows.append("MID")
        prev = x.test
        what = (f"without the {FAMILY_ADJ[x.setting]} rules ({x.rules_removed.replace(',', ', ')})" if x.test == "drop family"
                else prior[x.setting])
        rows.append([what] + [pct1(v) for v in (x.changed, x.changed_dead, x.changed_fill, x.changed_clock, x.changed_transfer)])
    head = (r"Change & All items & Dead & Fill & Clock & Transfer \\")
    cap = ("Sensitivity of the real-data labels to every rule family and prior: the share of items whose label changes when "
           "one rule family is removed or one prior or initial value is changed, over all 327 items and per item kind "
           "(126 dead, 155 fill, 33 clock, 13 transfer). The simultaneity family includes R7, which never fires.")
    return table("tab:s-robustness", cap, r"@{}l r r r r r@{}", head, rows)


# ---------------------------------------------------------------- S3: detector and end model, real data
def t_predictors():
    p = rd(TAB / "TableS6_predictor_comparison.csv")
    name = {"LGB forecast": "LightGBM forecast (the LightGBM residual)", "LGB nowcast (all zones, no learned edges)": "LightGBM nowcast",
            "TCN (no graph)": "TCN without the graph", "TCN-GAT (learned graph)": "TCN-GAT (main detector)",
            "LightGBM + TCN correction (no graph)": "LightGBM + TCN correction (no graph)",
            "LightGBM + learned-graph correction (hybrid)": "LightGBM + learned-graph correction",
            "mean(LightGBM, TCN-GAT)": "Mean of LightGBM and TCN-GAT"}
    rows = []
    for pr, g in p.groupby("predictor", sort=False):
        a, b = g[g.period == "all"].iloc[0], g[g.period != "all"].iloc[0]
        rows.append([name[pr], r(a.MAE, 4), r(a.median_abs, 4), r(a.RMSE, 4), r(b.MAE, 4), r(b.median_abs, 4), r(b.RMSE, 4)])
    head = (r" & \multicolumn{3}{c}{Whole record} & \multicolumn{3}{c}{From 1 July 2023} \\" "\n"
            r"\cmidrule(lr){2-4}\cmidrule(lr){5-7}" "\n"
            r"Predictor & MAE & Median & RMSE & MAE & Median & RMSE \\")
    cap = ("Accuracy of the predictors of $\\rho = x/\\hat{x}$ on the real southern data, on rule-clean zone-steps, out of "
           "sample (two-fold temporal cross-fitting split at 1 July 2023). Median: median absolute error. The nowcast reads, "
           "besides the forecast features, the current value of every other zone (a fully connected input with no learned "
           "edges). Corrections are added to the LightGBM forecast by a TCN without or with the learned graph.")
    return table("tab:s-predictors", cap, r"@{}l r r r r r r@{}", head, rows)


def t_dev_selection():
    d = rd(TAB / "TableS4_dev_selection.csv")
    rows = [[m(x.detector), str(int(x.w)), f"{r(x.q, 1)}\\%", str(int(x.gap)), r(x.f1), r(x.precision), r(x.recall), r(x.f1_zone),
             r(x.f1_nb3_setting), str(int(x.n_real_candidates))] for x in d.itertuples()]
    head = (r"Detector & $w$ & $q$ & $g_{\max}$ & F1 & Precision & Recall & Zone-strict & F1, untuned & Real-data \\" "\n"
            r" & & & & & & & F1 & setting & candidates \\")
    cap = ("Event formation chosen on the development datasets (3\\% with seeds 100--102, 1\\% with seed 103, 7\\% with seed "
           "104): for each detector, the best of the 48 settings of the smoothing window $w$ (steps), the percentile $q$ and the "
           "merge gap $g_{\\max}$ (steps) by mean event F1 of the detector alone. F1, untuned setting: the same detector with "
           "$(w, q, g_{\\max}) = (1, 99.5\\%, 1)$. Real-data candidates: detector-only candidates on the uninjected southern "
           "series at the chosen setting (events that do not overlap a rule item). The main detector was chosen among the four "
           "predictors by the development F1 of the "
           "rules plus its candidates. GDN, USAD and the main detector without the graph are tuned the same way; their settings "
           "are given in Tables~\\ref{tab:s-deep} and \\ref{tab:s-graph}.")
    return table("tab:s-dev", cap, r"@{}l r r r r r r r r r@{}", head, rows, size=r"\scriptsize", sep="3.5pt")


def t_hard_negatives():
    h = rd(RES / "benchmark_v1" / "hard_negatives.csv")
    rows, prev = [], None
    for x in h.itertuples():
        if prev is not None and x.detector != prev:
            rows.append("MID")
        rows.append([m(x.detector) if x.detector != prev else "", x.day_type, f"{int(x.zone_steps):,}", r(x.flag_rate, 4),
                     r(x.ratio_to_ordinary, 2)])
        prev = x.detector
    head = r"Detector & Day type & Zone-steps & Flag rate & Ratio to ordinary weekdays \\"
    cap = ("Alarms of the detectors alone on the real southern data by day type: the share of rule-negative zone-steps (no "
           "rule state of the zone within $\\pm$53 steps) whose score exceeds the detector's threshold, and its ratio to the "
           "rate on ordinary weekdays. Day types are exclusive, in the order Eid, national holiday, Ramadan, weekend.")
    return table("tab:s-hard-negatives", cap, r"@{}l l r r r@{}", head, rows, size=r"\scriptsize")


# ---------------------------------------------------------------- S4: injection benchmark
TYPES = ["A1", "A2", "A3", "G1", "G2", "G3", "G4", "U_SHOCK", "U_PARTIAL"]


def t_recall_by_type():
    d = rd(RES / "benchmark_v1" / "detection_recall_by_type.csv")
    order = ["ours (rules + detector)", "rules only (rule engine v1)", "TCN-GAT, hierarchy, multi-scale",
             "TCN-GAT, hierarchy, multi-scale (NB3 event formation)", "single scale (raw band)",
             "LightGBM forecast, hierarchy, multi-scale", "LightGBM forecast, hierarchy, multi-scale (NB3 event formation)",
             "LightGBM + learned-graph correction, hierarchy, multi-scale", "LightGBM + TCN correction (no graph), hierarchy, multi-scale",
             "mean(LightGBM, TCN-GAT), hierarchy, multi-scale", "LGB nowcast (raw, hierarchy)"]
    assert set(order) == set(d.method), set(d.method) ^ set(order)
    rows = []
    for k, rate in enumerate(sorted(d.rate.unique())):
        if k:
            rows.append("MID")
        g = d[d.rate == rate].set_index("method")
        for i, mt in enumerate(order):
            x = g.loc[mt]
            rows.append([pct(rate) if i == 0 else "", m(mt)] + [r(x[f"recall_{t}"], 3) for t in TYPES])   # as stored
    head = r"Rate & Method & " + " & ".join(tx(t) for t in TYPES) + r" \\"
    cap = ("Recall by injected type (share of the injected events of the type that overlap a predicted event), test "
           "period, mean over the 10 test seeds. U\\_SHOCK and U\\_PARTIAL are untyped events that no rule can see. Untuned event "
           "formation: $(w, q, g_{\\max}) = (1, 99.5\\%, 1)$. The nowcast is defined in Table~\\ref{tab:s-predictors}.")
    return longtable("tab:s-recall", cap, r"@{}l p{3.9cm} " + "r" * len(TYPES) + "@{}", head, rows, size=r"\scriptsize", sep="3.2pt")


def t_detection_tests():
    w = rd(RES / "benchmark_v1" / "table5_wilcoxon.csv")
    rows = []
    for x in w.itertuples():
        if x.best_baseline.startswith("rules only"):
            a, b = "Full method", "Rules alone"
        else:
            a, b = "Main detector", m(x.best_baseline.replace("main detector vs ", ""))
        rows.append([tx(x.rate), a, b, r(x.ours_F1), r(x.baseline_F1), pv(x.wilcoxon_p)])
    rows = rows[:3] + ["MID"] + rows[3:]
    head = r"Rate & Method & Compared with & F1, method & F1, other & $p$ \\"
    cap = ("Paired two-sided Wilcoxon signed-rank tests over the 10 test seeds on event F1 (Section~5.3 of the article; "
           "every predicted event counts, alarms on the uninjected series included). The smallest attainable $p$ is 0.002. "
           "With the method's own alarms on the uninjected series excluded, the full method beats the rules alone in 10 of 10 "
           "seeds at every rate ($p = 0.002$).")
    return longtable("tab:s-detection-tests", cap, r"@{}l l l r r r@{}", head, rows, size=r"\scriptsize")


def t_deep():
    d = rd(RES / "benchmark_v1" / "deep_baselines" / "table_deep_baselines.csv")
    rows = []
    for k, (mt, g) in enumerate(d.groupby("method", sort=False)):
        if k:
            rows.append("MID")
        for x in g.itertuples():
            rows.append([mt, tx(x.rate), tx(x.setting), tx(x.F1), tx(x.precision), tx(x.recall)]
                        + [mean_of(getattr(x, f"recall_{t}")) for t in ["A1", "A2", "A3", "G1", "G2", "G3", "G4"]])
    head = (r"Method & Rate & $(w, q, g_{\max})$ & F1 & Precision & Recall & \multicolumn{7}{c}{Recall by type (mean)} \\" "\n"
            r"\cmidrule(l){7-13}" "\n"
            r" & & & & & & A1 & A2 & A3 & G1 & G2 & G3 & G4 \\")
    cap = ("The deep multivariate baselines GDN and USAD on the injection benchmark (test period, mean $\\pm$ s.d. over the 10 "
           "test seeds), with their own event formation tuned on the development datasets, and their recall by injected type "
           "(means; F1 with their own alarms excluded and their real-data alarms are in Table~6 of the article). GDN finds "
           "the multi-city zero gaps (A1) but almost none of the single-zone fills (A3).")
    return table("tab:s-deep", cap, r"@{}l l l l l l rrrrrrr@{}", head, rows, size=r"\scriptsize", sep="2pt")


def t_gdn_forecast():
    g = rd(RES / "benchmark_v1" / "deep_baselines" / "gdn_forecast_vs_persistence.csv")
    tr = {"< 2023-07-01": "before 1 July 2023", ">= 2023-07-01": "from 1 July 2023"}
    win = {"training fold (in sample)": "training fold (in sample)", "other fold (out of sample)": "other fold (out of sample)"}
    rows = [[tr[x.model_trained_on], win[x.windows], f"{int(x.n):,}", r(x.mse_gdn, 5), r(x.mse_last_value, 5), r(x.mse_mean_last5, 5),
             r(x.ratio_gdn_to_last_value, 1)] for x in g.itertuples()]
    head = (r"GDN trained on & Windows & $n$ & MSE, GDN & MSE, last value & MSE, mean of & Ratio GDN / \\" "\n"
            r" & & & & & last 5 values & last value \\")
    cap = ("GDN's one-step forecasts against two naive forecasts on clean windows of the real southern series, for the two "
           "cross-fitted models (mean squared error of $\\rho$). On clean data GDN's forecasts are 7--14 times worse than the "
           "last value.")
    return table("tab:s-gdn-forecast", cap, r"@{}l l r r r r r@{}", head, rows, size=r"\scriptsize")


def t_deep_tests():
    w = rd(RES / "benchmark_v1" / "deep_baselines" / "wilcoxon_deep_baselines.csv")
    w = w[w.metric == "f1"]
    ref = {"main": "Main detector", "rules": "Rules alone", "ours": "Full method", "STL": "STL", "LOF": "LOF",
           "Isolation Forest": "Isolation Forest", "STL + MAD": "STL"}
    rows, prev = [], None
    for x in w.itertuples():
        if prev is not None and x.rate != prev:
            rows.append("MID")
        prev = x.rate
        rows.append([tx(x.rate), x.baseline, ref.get(x.reference, x.reference), r(x.baseline_mean, 4), r(x.reference_mean, 4),
                     f"{int(x.reference_wins)}/{int(x.n_seeds)}", pv(x.wilcoxon_p)])
    head = r"Rate & Baseline & Compared with & F1, baseline & F1, other & Other better & $p$ \\"
    cap = ("Paired two-sided Wilcoxon tests of the deep baselines on event F1 (10 test seeds). Other better: seeds in which "
           "the compared method has the higher F1.")
    return longtable("tab:s-deep-tests", cap, r"@{}l l l r r r r@{}", head, rows, size=r"\scriptsize")


def t_ablations():
    a = rd(TAB / "Table7e_ablations_main_detector.csv")
    name = {"main detector (TCN-GAT, multi-scale, hierarchy, tuned)": "Main detector",
            "− learned graph (TCN residual), same event formation": "without the learned graph, same event formation",
            "− learned graph, its own tuned event formation": "without the learned graph, own event formation",
            "− learned graph and − multi-scale (TCN, raw band)": "without the graph and the bands (TCN, raw band)",
            "− multi-scale (raw band only)": "without the bands (raw band only)",
            "− hierarchy (flat residual)": "without the hierarchy (flat zone score)",
            "LightGBM predictor instead of TCN-GAT (own tuning)": "LightGBM predictor (own event formation)",
            "− tuned event formation (NB3 setting)": "untuned event formation (1, 99.5\\%, 1)"}
    rows, prev = [], None
    for x in a.itertuples():
        if prev is not None and x.rate != prev:
            rows.append("MID")
        prev = x.rate
        main = x.group == "main"
        sgn = "$+$" if float(x.dF1) > 0 else ("$-$" if float(x.dF1) < 0 else "")
        rows.append([tx(x.rate), name[x.ablation], tx(x.F1), "--" if main else f"{sgn}{r(abs(float(x.dF1)), 4)} $\\pm$ {r(x.dF1_sd, 4)}",
                     "--" if main else pv(x.p), "--" if main else f"{int(x.main_wins)}/10", r(x.F1_bgx, 3), r(x.AUC_PR, 3)])
    head = (r"Rate & Variant & Event F1 & $\Delta$F1 vs main & $p$ & Main & F1, own & AUC-PR \\" "\n"
            r" & & & & & better & background excl. & \\")
    cap = ("Ablations of the main detector (the numbers behind Fig.~8 of the article): event F1 (mean $\\pm$ s.d. over the 10 "
           "test seeds), the mean $\\pm$ s.d. of the per-seed difference from the main detector, the paired Wilcoxon $p$, the "
           "seeds in which the main detector is better, F1 with the detector's own alarms on the uninjected series excluded, "
           "and step-wise AUC-PR. $\\Delta$F1 is rounded from the unrounded per-seed differences.")
    return longtable("tab:s-ablations", cap, r"@{}l p{4.4cm} l l r r r r@{}", head, rows, size=r"\scriptsize", sep="3.5pt")


def t_graph():
    g = rd(TAB / "Table7f_graph_ablation.csv")
    rows, prev = [], None
    for x in g.itertuples():
        if prev is not None and x.rate != prev:
            rows.append("MID")
        prev = x.rate
        short = {"TCN-GAT, hierarchy, multi-scale": "with graph", "TCN, no graph, hierarchy, multi-scale": "no graph",
                 "TCN, no graph, hierarchy, multi-scale (own tuned event formation)": "no graph, own"}
        rows.append([tx(x.rate), short[x.method], tx(x.F1), mean_of(x.precision), mean_of(x.recall), mean_of(x.F1_zone_strict),
                     mean_of(x.AUC_PR), mean_of(x.F1_own_background_excluded), str(int(x.real_data_alarms)), mean_of(x.recall_U_SHOCK),
                     mean_of(x.recall_U_PARTIAL)])
    settings = {short[k]: v for k, v in zip(g.method, g.setting)}
    head = (r"Rate & Variant & F1 & Precision & Recall & Zone- & AUC-PR & F1, own & Real-data & U\_SHOCK & U\_PARTIAL \\" "\n"
            r" & & & & & strict F1 & & bg.\ excl. & alarms & recall & recall \\")
    cap = ("The learned graph as an ablation: the main detector with and without the graph attention, the latter at the main "
           f"detector's event formation ({tx(settings['no graph'])}) and at its own, tuned on the development datasets "
           f"like every detector ({tx(settings['no graph, own'])}). Event F1: mean $\\pm$ s.d. over the 10 test seeds; the "
           "other columns: means.")
    return table("tab:s-graph", cap, r"@{}l l l r r r r r r r r@{}", head, rows, size=r"\scriptsize", sep="2.2pt")


def t_variants_3pct():
    b = rd(TAB / "Table7b_detector_ablations_3pct.csv")
    b = b[b.variant != "TCN-GAT, learned graph, raw"]          # the same run as "main detector, single scale (raw band)"
    rows = [[m(x.variant), tx(x.F1), tx(x.AUC_PR), mean_of(x.recall_A2), mean_of(x.recall_G3), mean_of(x.recall_U_SHOCK),
             mean_of(x.recall_U_PARTIAL)]
            for x in b.itertuples()]
    head = (r"Variant & Event F1 & AUC-PR & A2 & G3 & U\_SHOCK & U\_PARTIAL \\" "\n"
            r" & & & recall & recall & recall & recall \\")
    cap = ("Detector variants at 3\\% contamination (test period, mean $\\pm$ s.d. over the 10 test seeds), at the main "
           "detector's event formation unless stated; recall columns: means.")
    return table("tab:s-variants", cap, r"@{}p{4.8cm} l l r r r r@{}", head, rows, size=r"\scriptsize", sep="3.5pt")


def t_thresholds():
    t = rd(TAB / "Table7d_threshold_sensitivity.csv")
    name = {"baseline": r"as used ($\varepsilon$ 0.05, hold 6, $\tau$ 10 min)", "eps 0.02": r"noise floor $\varepsilon$ = 0.02",
            "eps 0.10": r"noise floor $\varepsilon$ = 0.10", "hold 4": "hold of 4 equal values", "hold 12": "hold of 12 equal values",
            "tau 0 min": r"simultaneity window $\tau$ = 0 min", "tau 20 min": r"simultaneity window $\tau$ = 20 min"}
    rows = [[name[x.config], tx(x.rules_F1), mean_of(x.rules_recall), mean_of(x.recall_A2), mean_of(x.recall_A3), mean_of(x.recall_G3),
             mean_of(x.recall_G4), mean_of(x.recall_U_PARTIAL), tx(x.label_model_macro_F1)] for x in t.itertuples()]
    head = (r"Thresholds & Rules & Rules & A2 & A3 & G3 & G4 & U\_PARTIAL & Label model \\" "\n"
            r" & F1 & recall & recall & recall & recall & recall & recall & macro-F1 \\")
    cap = ("Sensitivity to the rule-engine thresholds on injected data (3\\%, test seeds 0--2, test period; mean $\\pm$ s.d.): "
           "the rules alone and the label model with one threshold changed at a time; recall columns: means.")
    return table("tab:s-thresholds", cap, r"@{}p{3.9cm} l r r r r r r l@{}", head, rows, size=r"\scriptsize", sep="3pt")


def t_rule_families():
    t = rd(TAB / "Table7c_rule_families.csv")
    rows = [["all rule families" if x.label_model == "all rule families" else
             f"without the {FAMILY_ADJ[x.label_model.replace('without ', '')]} rules", tx(x.macro_F1)] for x in t.itertuples()]
    head = r"Label model & Macro-F1 \\"
    cap = ("The label model refitted without one rule family at a time, on the typed injected events detected by the full "
           "method (3\\%, test period, mean $\\pm$ s.d. over the 10 test seeds).")
    return table("tab:s-families", cap, r"@{}l l@{}", head, rows)


def t_attribution_tests():
    w = rd(RES / "benchmark_v1" / "attribution_wilcoxon" / "wilcoxon.csv")
    s = json.loads((RES / "benchmark_v1" / "attribution_wilcoxon" / "summary.json").read_text(encoding="utf-8"))
    name = {"label model q vs majority vote": "Label model", "fusion (β*, D50 abstention) vs majority vote": "Fusion"}
    rows = [[tx(x.rate), name[x.comparison], r(x.mean_other, 4), r(x.mean_mv, 4), f"{int(x.other_better)} / {int(x.ties)} / {int(x.mv_better)}",
             pv(x.wilcoxon_p)] for x in w.itertuples()]
    head = r"Rate & Labeller & Macro-F1 & Macro-F1, majority vote & Better / tied / worse & $p$ \\"
    beta = ", ".join(f"{s['beta_star'][k]}" for k in ("1%", "3%", "7%"))
    cap = ("Attribution against the rules' majority vote (the tests behind Table~7 of the article): macro-F1 on the typed "
           "injected events detected by the full method (test period, mean over the 10 test seeds), the seeds in which the "
           "labeller is better, tied or worse, and the paired Wilcoxon $p$. Fusion weight $\\beta$ tuned on "
           f"the earlier period: {beta} at 1, 3 and 7\\%; the end model abstains on classes with fewer than 3 training items.")
    return table("tab:s-attribution-tests", cap, r"@{}l l r r c r@{}", head, rows)


def t_snorkel():
    a = rd(RES / "benchmark_v1" / "snorkel_baseline" / "table_snorkel_attribution.csv")
    w = rd(RES / "benchmark_v1" / "snorkel_baseline" / "wilcoxon_snorkel.csv")
    rows = [[tx(x["rate"]), f"{int(x['n_events']):,}", tx(x["majority vote"]), tx(x["label model (ours)"]), tx(x["Snorkel"]),
             tx(x["Snorkel + feasible sets"])] for _, x in a.iterrows()]
    rows.append("MID")
    nm = {"label model (ours) vs majority vote": "ours vs majority vote", "label model (ours) vs Snorkel": "ours vs Snorkel",
          "label model (ours) vs Snorkel + feasible sets": "ours vs Snorkel + feasible sets"}
    for x in w.itertuples():
        rows.append([tx(x.rate), "", nm[x.comparison], f"{r(x.ours, 4)} vs {r(x.other, 4)}", f"ours better in {int(x.ours_wins)}, tied in {int(x.ties)}",
                     f"$p$ = {pv(x.wilcoxon_p)}"])
    head = r"Rate & Events & Majority vote & Label model (ours) & Snorkel & Snorkel + feasible sets \\"
    cap = ("Snorkel's label model on the same rule votes (injected data, the typed events matched by a rule item; macro-F1, "
           "mean $\\pm$ s.d. over the 10 test seeds), and paired Wilcoxon tests of our label model against each labeller "
           "(lower block: mean macro-F1, seeds in which ours is better and tied). Feasible sets: Snorkel's probabilities "
           "restricted to the item's feasible classes.")
    return table("tab:s-snorkel", cap, r"@{}l r l l l l@{}", head, rows, size=r"\scriptsize")


# ---------------------------------------------------------------- S5: downstream
def t_forecast30():
    f = rd(RES / "downstream_v1" / "forecast_all" / "forecast_summary.csv")
    sub = {"after anomaly (2 days)": "after", "all": "all"}
    rows, prev = [], None
    for x in f.itertuples():
        key = (x.model, x.horizon)
        if prev is not None and key != prev:
            rows.append("MID")
        prev = key
        rows.append([x.model, x.horizon, sub[x.subset], tx(x.rate), r(x.MASE_S0_mean), r(x.MASE_S1_mean), r(x.MASE_S2_mean), r(x.MASE_S3_mean),
                     f"{int(x.S2_better_than_S1_n)}/{int(x.n)}", pv(x.wilcoxon_p_S1_vs_S2), f"{int(x.S2_better_than_S0_n)}/{int(x.n)}",
                     pv(x.wilcoxon_p_S0_vs_S2)])
    head = (r"Forecaster & Horizon & Steps & Rate & S0 & S1 & S2 & S3 & S2 better & $p$ & S2 better & $p$ \\" "\n"
            r" & & & & \multicolumn{4}{c}{MASE (mean)} & than S1 & & than S0 & \\")
    cap = ("Forecasting on the 30 injected test datasets by rate (the numbers behind Table~8 and Fig.~10 of the article): "
           "mean MASE of each cleaning strategy, test period 1 January -- 24 May 2024, on steps within two days after an "
           "anomalous state (after) or all scored steps (all); the datasets in which S2 has the lower MASE and the paired "
           "Wilcoxon $p$. Naive: persistence at 1~h, seasonal naive at 1~day.")
    return longtable("tab:s-forecast30", cap, r"@{}l l l l r r r r r r r r@{}", head, rows, size=r"\scriptsize", sep="3.2pt")


def t_dm30():
    d = rd(RES / "downstream_v1" / "forecast_all" / "dm_summary.csv")
    d = d[d.comparison != "S2 vs S3"]
    sub = {"after anomaly (2 days)": "after", "all": "all"}
    rows = [[x.model, x.horizon, sub[x.subset], x.comparison, f"{int(x.sig_better)}", f"{int(x.sig_worse)}", r(x.DM_mean, 2)]
            for x in d.itertuples()]
    head = r"Forecaster & Horizon & Steps & Comparison & S2 significantly better & S2 significantly worse & Mean DM \\"
    cap = ("Diebold--Mariano tests per injected dataset (30 datasets): the number of datasets in which S2 is significantly "
           "better or worse ($p < 0.05$) and the mean statistic (positive: S2 better).")
    return table("tab:s-dm30", cap, r"@{}l l l l r r r@{}", head, rows, size=r"\scriptsize")


def t_dm_real():
    d = rd(RES / "downstream_v1" / "table8_dm.csv")
    d = d[d.data == "real"]
    sub = {"after anomaly (2 days)": "after", "all": "all"}
    rows = [[x.model, x.horizon, sub.get(x.subset, x.subset), x.comparison, f"{int(x.n_steps):,}", r(x.mean_loss_diff, 3),
             r(x.share_steps_second_better, 3), r(x.DM, 2), pv(x.p)] for x in d.itertuples()]
    head = (r"Forecaster & Horizon & Steps & Comparison & $n$ & Mean loss & Share of steps & DM & $p$ \\" "\n"
            r" & & & & & difference & second better & & \\")
    cap = ("Diebold--Mariano tests on the real data (test period 1 January -- 24 May 2024): loss summed over zones, "
           "$d_t = L^{(1)}_t - L^{(2)}_t$ (positive: the second strategy better), Newey--West variance with bandwidth equal to "
           "the horizon.")
    return longtable("tab:s-dm-real", cap, r"@{}l l l l r r r r r@{}", head, rows, size=r"\scriptsize")


def t_outage30():
    o = rd(RES / "downstream_v1" / "outage_all" / "outage_summary.csv")
    rows = [[tx(x.rate), str(int(x.n)), f"{r(x.naive_ratio_mean, 2)} $\\pm$ {r(x.naive_ratio_sd, 2)}", f"{r(x.naive_ratio_min, 2)}--{r(x.naive_ratio_max, 2)}",
             f"{r(x.typed_ratio_mean, 2)} $\\pm$ {r(x.typed_ratio_sd, 2)}", f"{r(x.typed_ratio_min, 2)}--{r(x.typed_ratio_max, 2)}",
             f"{int(x.typed_closer_n)}/{int(x.n)}", pv(x.wilcoxon_p) if float(x.wilcoxon_p) >= 0.0005 else f"{float(x.wilcoxon_p):.1e}".replace("e-0", r" $\times 10^{-") + "}$",
             r(x.truth_zone_hours_mean, 1)] for x in o.itertuples()]
    head = (r"Rate & Datasets & Naive ratio & Range & Typed ratio & Range & Typed & $p$ & True outage \\" "\n"
            r" & & (mean $\pm$ s.d.) & & (mean $\pm$ s.d.) & & closer & & zone-hours (mean) \\")
    cap = ("Outage statistics on the 30 injected test datasets: counted outage zone-hours relative to the injected truth, "
           "naive (every flagged dead state) and typed (dead states inside grid-event items), the datasets in which typed "
           "counting is closer to the truth ($|\\log r|$) and the paired Wilcoxon $p$.")
    return table("tab:s-outage30", cap, r"@{}l r l l l l r r r@{}", head, rows, size=r"\scriptsize", sep="3.5pt")


# ---------------------------------------------------------------- S6: transfer
def t_tetouan_recall():
    d = rd(RES / "transfer_tetouan" / "table9_recall_by_type.csv")
    ty = ["A1", "A2", "A3", "G2", "G3", "G4", "U_SHOCK", "U_PARTIAL"]
    rows, prev = [], None
    for x in d.itertuples():
        if prev is not None and x.rate != prev:
            rows.append("MID")
        rows.append([pct(x.rate) if x.rate != prev else "", m(x.method)] + [r(getattr(x, f"recall_{t}"), 3) for t in ty])  # as stored
        prev = x.rate
    head = r"Rate & Method & " + " & ".join(tx(t) for t in ty) + r" \\"
    cap = ("Transfer to Tetouan: recall by injected type (mean over the 10 seeds; G1 is not injected in a single-city system).")
    return table("tab:s-tetouan-recall", cap, r"@{}l l " + "r" * len(ty) + "@{}", head, rows, size=r"\scriptsize", sep="3.2pt")


def t_tetouan_attr():
    d = rd(RES / "transfer_tetouan" / "table9_attribution.csv")
    rows = [[pct(x.rate), tx(x.detected_share), tx(x.macro_F1_label_model), tx(x.macro_F1_majority_vote), tx(x.accuracy_label_model),
             tx(x.accuracy_majority_vote), tx(x.end_to_end)] for x in d.itertuples()]
    head = (r"Rate & Typed events & Macro-F1, & Macro-F1, & Accuracy, & Accuracy, & End to end \\" "\n"
            r" & detected & label model & majority vote & label model & majority vote & \\")
    cap = ("Transfer to Tetouan: attribution by the frozen label model (one E-step with the parameters fitted on the "
           "Moroccan votes) and by the rules' majority vote, mean $\\pm$ s.d. over the 10 seeds. End to end: the share of "
           "typed injected events both detected and correctly typed.")
    return table("tab:s-tetouan-attr", cap, r"@{}l l l l l l l@{}", head, rows, size=r"\scriptsize")


def t_tetouan_tests():
    d = rd(RES / "transfer_tetouan" / "table9_wilcoxon.csv")
    rows, prev = [], None
    for x in d.itertuples():
        if prev is not None and x.rate != prev:
            rows.append("MID")
        prev = x.rate
        other = m(x.comparison.replace("main detector vs ", ""))
        rows.append([tx(x.rate), other, r(x.main, 4), r(x.other, 4), f"{int(x.main_wins)}/10", pv(x.p)])
    head = r"Rate & Main detector compared with & F1, main & F1, other & Main better & $p$ \\"
    cap = "Transfer to Tetouan: paired Wilcoxon tests of the main detector against every other method on event F1 (10 seeds)."
    return longtable("tab:s-tetouan-tests", cap, r"@{}l l r r r r@{}", head, rows, size=r"\scriptsize")


# ---------------------------------------------------------------- S7: reproducibility
def t_software():
    b = json.loads((RES / "benchmark_v1" / "summary.json").read_text(encoding="utf-8"))
    dpb = json.loads((RES / "benchmark_v1" / "deep_baselines" / "summary.json").read_text(encoding="utf-8"))
    sn = json.loads((RES / "labels_v1" / "snorkel" / "summary.json").read_text(encoding="utf-8"))
    rows = [["Local runs (Windows PC, 8 logical CPU cores)", "Python 3.12.1, NumPy 1.26.4, pandas 2.2.0, SciPy 1.12.0, scikit-learn 1.5.1, "
             "statsmodels 0.15.0, PyWavelets 1.8.0, Matplotlib 3.8.3, openpyxl 3.1.5"],
            ["", f"LightGBM 4.6.0; PyTorch {tx(dpb['torch_version'])} on CPU (graph ablation, GDN, USAD)"],
            ["Injection benchmark (NB4)", f"Google Colab with a GPU (device {b['device']}); PyTorch {tx(b['torch_version'])}, LightGBM {b['lightgbm_version']}"],
            ["Snorkel baseline", f"separate environment with Snorkel {sn['snorkel_version']}"]]
    head = r"Environment & Versions \\"
    cap = ("Software and hardware. The versions of the local environment were read on 15 November 2026; each run records the "
           "versions it used in its \\texttt{summary.json}. LightGBM is pinned at 4.6.0 (4.7.0 crashed on the local machine).")
    return table("tab:s-software", cap, r"@{}p{4.6cm} p{10.6cm}@{}", head, rows, size=r"\footnotesize")


def t_runtimes():
    j = lambda p: json.loads((RES / p).read_text(encoding="utf-8"))  # noqa: E731
    nb3, nb6, nb7 = j("end_model_v1/summary.json"), j("transfer_tetouan/summary.json"), j("paper/summary.json")
    dpb, gab = j("benchmark_v1/deep_baselines/summary.json"), j("benchmark_v1/graph_ablation/summary.json")
    fa, oa, nb4 = j("downstream_v1/forecast_all/summary.json"), j("downstream_v1/outage_all/summary.json"), j("benchmark_v1/summary.json")
    rows = [["Rule engine (states, items, votes)", "CPU", "about 30 s", "documented"],
            ["Label model (NB2)", "CPU", "about 1.5 min", "documented"],
            ["Detector and end model (NB3)", "CPU", f"{nb3['runtime_min']} min", "recorded"],
            ["Development selection of event formation (seeds 100--104)", "CPU", "about 35 min (1 h with the extended grid)", "documented"],
            ["Injection benchmark, 30 test datasets (NB4)", "GPU (Colab)", f"2--3 h, resumable (the last session {nb4['runtime_min']} min)", "documented, recorded"],
            ["No-graph ablation on the 30 test datasets", "CPU", f"{r(gab['seconds'] / 60, 1)} min", "recorded"],
            ["GDN and USAD on the 30 test datasets", "CPU", f"{r(dpb['seconds'] / 60, 1)} min", "recorded"],
            ["Downstream test on the real data (NB5)", "CPU", "17.5 min", "recorded"],
            ["Outage statistics, 30 test datasets", "CPU", f"{oa['minutes_full_run']} min", "recorded"],
            ["Forecasting, 30 test datasets", "CPU", f"{fa['minutes_this_call']} min", "recorded"],
            ["Transfer to Tetouan (NB6)", "CPU", f"{nb6['runtime_min']} min", "recorded"],
            ["Final catalogue, figures and tables (NB7)", "CPU", f"{nb7['runtime_min']} min", "recorded"]]
    head = r"Step & Hardware & Wall-clock time & Source \\"
    cap = ("Run times. Recorded: written by the run itself (\\texttt{summary.json}) or logged when it ran; documented: the "
           "approximate time given in the repository's instructions. The injection benchmark ran on Colab, was interrupted "
           "once and resumed.")
    return table("tab:s-runtimes", cap, r"@{}p{5.6cm} l p{4.3cm} l@{}", head, rows, size=r"\footnotesize")


def t_settings():
    b = json.loads((RES / "benchmark_v1" / "deep_baselines" / "summary.json").read_text(encoding="utf-8"))
    g, u = b["gdn_cfg"], b["usad_cfg"]
    rows = [
        ["Expected value", r"$\hat{x}$: median of the same time slot over the previous 14 days"],
        ["States", r"exact zero $x = 0$; noise floor $x \leq 0.05\,\hat{x}$; hold: $\geq 6$ equal values; straight-line fill: $\geq 6$ collinear points"],
        ["Items", r"runs of one system whose starts lie within $\tau = 10$~min form one item; episodes: items sharing boundaries"],
        ["Label model", r"priors Beta(1, 1) on $a$ (Beta(9, 1) for defining rules), Beta(1, 9) on $b$, pseudo-count $\gamma = 1$ per class; "
                        r"initial $a = 0.7$, $b = 0.05$; 20 restarts (log-normal jitter, s.d. 0.5); stop at $|\Delta \log L| < 10^{-6}$ "
                        r"or 3,000 iterations; the restart with the highest penalised log-likelihood is kept"],
        ["LightGBM predictor", r"one regressor per zone; Huber loss ($\delta = 0.1$); 400 trees, learning rate 0.05, 31 leaves, "
                               r"min.\ 50 samples per leaf, row subsample 0.8, column subsample 0.9, L2 penalty 1; own lags 1, 2, 3, 6 steps, "
                               r"1, 2, 7 days, mean of the last 6 steps, median of the previous day, calendar"],
        ["TCN-GAT predictor", r"causal TCN: 6 residual blocks, kernel 3, dilations 1--32, 32 channels, receptive field 253 steps; graph "
                              r"attention, 2 heads, same-city zones plus $k = 4$ learned cross-city zones (16-d embeddings); head MLP with "
                              r"the TCN state, the attention message, the embedding, 11 calendar features and the zone's value and mask "
                              r"1 and 7 days earlier"],
        ["Training (both)", r"rule-clean steps only (masked loss); two-fold temporal cross-fitting at 1 July 2023; TCN-GAT: AdamW, "
                            r"learning rate $2 \cdot 10^{-3}$, weight decay $10^{-4}$, cosine schedule, early stopping on the last 15\% "
                            r"of each fold (patience 6, at most 40 epochs), chunks of 256 steps"],
        ["Multi-scale bands", r"MODWT with the LA(8) filter, levels 1--4; bands raw, W1--W4, V4, phase-aligned (delays 4, 11, 25, 53 and 43 steps)"],
        ["Level scores", r"trailing 28-day robust $z$-score of $|\varepsilon|$ on rule-clean steps (at least 7 days of history; "
                         r"structural zeros excluded); zone-step score: maximum over bands and levels"],
        ["Event formation", r"main detector $(w, q, g_{\max}) = (24, 99.9\%, 12)$; runs of at least 3 steps; every detector tuned "
                            r"over the same 48 settings (Table~\ref{tab:s-dev})"],
        ["End model and fusion", r"LightGBM multiclass on rows weighted by $q$ ($q > 10^{-3}$), out of fold (5 folds grouped by "
                                 r"episode); fusion $p \propto q^{\beta} f^{1-\beta}$ on the feasible classes; abstention on "
                                 r"classes with fewer than 3 training items"],
        ["STL", r"daily period, non-robust; robust $z$-score of the remainder"],
        ["Isolation Forest, LOF", r"features of $\rho$: value, first difference, difference from one day earlier, mean and "
                                  r"s.d.\ over 6 steps; Isolation Forest 100 trees; LOF 35 neighbours (novelty mode)"],
        ["GDN", f"window {g['win']}, embedding {g['dim']}, top-$k$ {g['topk']}, batch {g['batch']}, at most {g['epochs']} epochs "
                f"(early stopping {g['early_stop']}), learning rate {g['lr']}, dropout {g['dropout']}, validation share {g['val_ratio']}"],
        ["USAD", f"window {u['win']}, hidden size {u['hidden']}, {u['epochs']} epochs, training share {u['train_frac']}, "
                 f"$\\alpha = {u['alpha']}$, $\\beta = {u['beta']}$"],
        ["Downstream forecaster", r"global LightGBM direct model per horizon (6 and 144 steps), L2 loss, 500 trees, learning rate "
                                  r"0.05, 63 leaves; trained from day 35 to 31 December 2023; scored 1 January -- 24 May 2024"],
        ["Statistics", r"exact two-sided Wilcoxon signed-rank tests; Diebold--Mariano with Newey--West bandwidth equal to the "
                       r"horizon; ECE with 10 equal-width bins"],
    ]
    head = r"Component & Settings \\"
    cap = ("Settings used for every result of the article (the full list of parameters is in the released code). GDN and "
           "USAD use the settings released by their authors.")
    return table("tab:s-settings", cap, r"@{}p{3.3cm} p{12.2cm}@{}", head, [[a, b_] for a, b_ in rows], size=r"\footnotesize")


def t_seeds():
    rows = [["Injected test datasets", r"rates 1, 3, 7\% $\times$ seeds 0--9 (30 datasets, 8,526 events); generator seeded with (1000 $\times$ rate, seed)"],
            ["Development datasets", r"3\% with seeds 100--102, 1\% with seed 103, 7\% with seed 104"],
            ["Threshold sensitivity", r"3\%, test seeds 0--2"],
            ["Tetouan injected datasets", r"rates 1, 3, 7\% $\times$ seeds 0--9 (30 datasets)"],
            ["Label model", "20 restarts; restart 0 deterministic"],
            ["Snorkel", "seeds 0--19 on the real data"],
            ["Fig.~\\ref{fig:s-injected}", r"3\%, seed 0"]]
    head = r"Use & Seeds \\"
    cap = "Random seeds. Every injected dataset is regenerated from its rate and seed."
    return table("tab:s-seeds", cap, r"@{}p{4.2cm} p{11.3cm}@{}", head, rows, size=r"\footnotesize")


# ---------------------------------------------------------------- figures
def draw_figures():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    sys.path.insert(0, str(ROOT / "src"))
    plt.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42})
    import rules_v1 as R1
    import paper_supplement as SUP
    FIG.mkdir(parents=True, exist_ok=True)
    cat = rd(RES / "catalogue_final" / "catalogue.csv")
    res = R1.build(ROOT / "data" / "raw" / "Data Morocco.xlsx")
    SUP.figure_s1(res, FIG)
    print("S2 delta*:", SUP.figure_s2(res, FIG))
    print("S3 transfer:", SUP.figure_s3(res, FIG))
    SUP.figure_s4(res, FIG)
    print("S5:", SUP.figure_s5(cat, FIG))
    print("S6:", SUP.figure_s6(cat, res, FIG))
    print("S7:", SUP.figure_s7(cat, FIG))
    print("S8:", SUP.figure_s8(res, FIG))
    SUP.figure_s9(FIG)
    plt.close("all")


# ---------------------------------------------------------------- document
PREAMBLE = r"""\documentclass[11pt,a4paper]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{lmodern}
\usepackage{amsmath,amssymb}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{array}
\usepackage{longtable}
\usepackage{xcolor}
\usepackage[hidelinks]{hyperref}

% A4 with 2.5-cm margins (set by hand: only packages that ship with every installation are used)
\setlength{\textwidth}{160mm}\setlength{\oddsidemargin}{25mm}\addtolength{\oddsidemargin}{-1in}
\setlength{\evensidemargin}{\oddsidemargin}
\setlength{\topmargin}{20mm}\addtolength{\topmargin}{-1in}\setlength{\headheight}{0pt}\setlength{\headsep}{0pt}
\setlength{\textheight}{247mm}\setlength{\footskip}{10mm}
\setlength{\parindent}{0pt}\setlength{\parskip}{5pt plus 1pt}
\setlength{\emergencystretch}{1.5em}
\renewcommand{\thesection}{S\arabic{section}}
\renewcommand{\thetable}{S\arabic{table}}
\renewcommand{\thefigure}{S\arabic{figure}}
\setlength{\LTcapwidth}{\textwidth}
\setlength{\abovecaptionskip}{4pt}

% Tables and figures are placed where they are written (no floats), each kept on one page with its caption
\makeatletter
\newenvironment{stable}{\par\addvspace{8pt}\noindent\begin{minipage}{\textwidth}\def\@captype{table}\centering}{\end{minipage}\par\addvspace{8pt}}
\newenvironment{sfigure}{\par\addvspace{8pt}\noindent\begin{minipage}{\textwidth}\def\@captype{figure}\centering}{\end{minipage}\par\addvspace{8pt}}
\makeatother

\begin{document}
"""

INTRO = r"""\begin{center}
{\Large\bfseries Supplementary material}\\[6pt]
{\large Grid event or data artefact? Hierarchical weak supervision for anomaly attribution in multi-city feeder telemetry}\\[8pt]
Saad Farah, Lahcen Hassine, Hatim Lechgar, Anass Rghioui
\end{center}

This supplement gives the evidence behind statements of the article that its main tables and figures do not show: the
real-data events and clock days (Section~\ref{sec:s-real}), the rules and the label model (Section~\ref{sec:s-rules}),
the detector and the end model on the real data (Section~\ref{sec:s-detector}), the full injection benchmark
(Section~\ref{sec:s-benchmark}), the downstream test (Section~\ref{sec:s-downstream}), the transfer test
(Section~\ref{sec:s-transfer}), and the software versions, settings, run times and seeds (Section~\ref{sec:s-repro}).
Every number is read from the result files released with the code at \url{REPO}, where the typed catalogue
(404 entries) is also released as a CSV file.

Conventions. Time stamps are as recorded. Zones: L1--L5 La\^ayoune, B1--B3 Boujdour, F1--F7 Foum El Oued, M1--M2 Marrakech.
Types: A1 zero-fill gap, A2 simultaneous fill, A3 single-zone fill, A4 clock error, G1 regional outage, G2 city outage,
G3 unplanned feeder outage, G4 planned work, G5 load transfer, N normal or untyped. Unless stated otherwise, results on
injected data are for the test period (July 2023 -- May 2024) and are means $\pm$ s.d.\ over the 10 test seeds of each
contamination rate (1, 3 and 7\%); $p$-values are from exact paired two-sided Wilcoxon signed-rank tests, whose smallest
attainable value over 10 seeds is 0.002. Untuned event formation means $(w, q, g_{\max}) = (1, 99.5\%, 1)$.

\tableofcontents
"""


def build():
    items = rd(RES / "catalogue_v1" / "items.csv")
    cat = rd(RES / "catalogue_final" / "catalogue.csv")
    parts = [PREAMBLE, INTRO.replace("REPO", REPO_URL)]
    parts += [r"\clearpage\section{Real-data events and clock days}\label{sec:s-real}",
              t_key_events(),
              figure("FigS1", "fig:s-jul2023",
                     "The only regional-outage candidate, 16--17 July 2023 (time stamps as recorded). Boujdour and Foum El Oued "
                     "read exact zeros from 14:50 for 16.2~h (A1, confidence 0.93) while every Laâyoune zone is filled by "
                     "straight lines from 15:30 for 15.5~h (A2, 1.00): a recording failure, not an outage. Shading: per-step "
                     "states; dashed line: expected value; dotted lines: the two start times."),
              t_clock(items, cat),
              figure("FigS2", "fig:s-clock",
                     "Clock evidence at 30 October 2022, the European return to winter time, when the hour 02:00--02:50 is "
                     "recorded twice. (a) Mean daily profile of each southern city over the 7 days before (solid) and after "
                     "(dashed) the date, normalised by its mean; (b) correlation of the two profiles as a function of the shift "
                     "applied to the second: $\\delta^{*} = -60$~min in all three cities."),
              t_transfers(items, cat),
              figure("FigS3", "fig:s-transfer",
                     "The only conserved load transfer: Boujdour, 16 December 2023. (a) Daily mean current of the three zones "
                     "and their sum over 45 days either side of the day (dotted); (b) change of the 14-day medians: B2 gains what "
                     "B1 loses, so the city total is conserved ($\\kappa = 0.07$, Table~\\ref{tab:s-transfers}), and rule R16 votes "
                     "G5."),
              r"\clearpage\section{Rules and label model}\label{sec:s-rules}",
              t_rule_params(),
              figure("FigS4", "fig:s-rules",
                     "Rule diagnostics on the real data. (a) Items each rule votes on, out of the items of the kind it reads, "
                     "coloured by the rule's output; (b) items on which two rules both fire; (c) items on which two rules give "
                     "incompatible outputs. Colour scales are logarithmic."),
              t_stability(), t_recovery(), t_robustness(),
              r"\clearpage\section{Detector and end model on the real data}\label{sec:s-detector}",
              t_predictors(), t_dev_selection(), t_hard_negatives(),
              figure("FigS5", "fig:s-signatures",
                     "Signatures of the 126 dead items of the real data, coloured by final label. (a) Share of exact zeros "
                     "$\\eta$ in the dead run; (b) restoration ratio $r$ and overshoot $\\pi$ (dashed: the threshold of rule R5); "
                     "(c) duration and ramp time $\\tau$. The restoration features do not separate the classes."),
              figure("FigS6", "fig:s-timeline",
                     "The typed catalogue on one timeline: rule items of kind dead and fill (filled) and detector-only "
                     "candidates (outlined) per zone, coloured by final label; dotted lines: clock days (coloured when labelled A4)."),
              figure("FigS7", "fig:s-endmodel",
                     "End model on the real data. (a) Label-model label against the out-of-fold end-model label of the rule "
                     "items; (b) agreement with the label model on the rule items and share of normal windows predicted N, by "
                     "variant (GBDT: gradient-boosted trees); (c) final labels of the detector-only candidates, from the main "
                     "detector in the southern system and from the LightGBM residual in Marrakech."),
              r"\clearpage\section{Injection benchmark}\label{sec:s-benchmark}",
              figure("FigS8", "fig:s-injected",
                     "One injected event of each type over the original series (grey), from the dataset with 3\\% "
                     "contamination and seed~0; shading: the injected span. U\\_SHOCK and U\\_PARTIAL scale the load down and "
                     "are not typed by any rule."),
              t_recall_by_type(), t_detection_tests(), t_deep(), t_gdn_forecast(), t_deep_tests(),
              t_ablations(), t_graph(), t_variants_3pct(), t_thresholds(), t_rule_families(), t_attribution_tests(), t_snorkel(),
              r"\clearpage\section{Downstream test}\label{sec:s-downstream}",
              t_forecast30(), t_dm30(), t_dm_real(), t_outage30(),
              r"\clearpage\section{Transfer test}\label{sec:s-transfer}",
              figure("FigS9", "fig:s-tetouan",
                     "The UCI Tetouan data used for the transfer test: three zones of one city, 2017, 10-min steps. (a) Daily "
                     "mean per zone; (b) one week."),
              t_tetouan_recall(), t_tetouan_attr(), t_tetouan_tests(),
              r"\clearpage\section{Software, settings, run times and seeds}\label{sec:s-repro}",
              t_software(), t_settings(), t_runtimes(), t_seeds(),
              r"\end{document}"]
    OUT.mkdir(parents=True, exist_ok=True)
    tex = "\n".join(parts) + "\n"
    import re
    number = {lab: k + 1 for k, lab in enumerate(re.findall(r"\\label\{(tab:s-[^}]+)\}", tex))}
    cited = {"tab:s-robustness": 7, "tab:s-deep": 13, "tab:s-gdn-forecast": 14,       # cited by number in the article
             "tab:s-software": 30, "tab:s-settings": 31, "tab:s-runtimes": 32}         # (Sections 4.5, 5.6 and 6)
    assert all(number[k] == v for k, v in cited.items()), {k: number[k] for k in cited}
    (OUT / "supplementary.tex").write_bytes(tex.encode("utf-8"))
    print("wrote", OUT / "supplementary.tex", f"({len(tex.splitlines())} lines)")


if __name__ == "__main__":
    if "--no-figures" not in sys.argv:
        draw_figures()
    build()
