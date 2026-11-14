"""NB7: figures regenerated from stored results with the fixes noted during the project (D74).
  Fig 8  - level scores recomputed with the saved LightGBM models; the x-axis repeated day labels fixed
  Fig 9  - NB4's detection figure plus the learned-graph ablation row (D62) and the deep baselines GDN and USAD (D82),
           shorter labels; paper mode = the paper's Figure 7 (compared methods only, print width, no title; D85)
  E4     - signatures of the v1 dead items (restoration measured after the synthetic ramp, D22), final labels
  E6     - the typed catalogue on one timeline (final labels; v0 types before)
  E19    - end model: the legend moved off the bars; panel (c) uses the final catalogue's candidates
  E22    - Tetouan series: the legend moved off the lines
  Fig 12 - NB5's downstream figure; panel (c) from all 30 NB4 test datasets (tools/outage_all_datasets.py, D76) and
           panel (b) from the 30-dataset forecasting run (D83) instead of NB5's 4; paper mode = the paper's Figure 10 (D85)
Nothing here changes a method result."""
import pickle
import re
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle

import benchmark as B
import detector as D
from viz import COL, LABEL_COL, CITY_SHORT, savefig

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
LABEL_COL_N = {**LABEL_COL, "N": "#9AA0A6"}
ORDER_CL = ["A1", "A2", "A3", "A4", "G1", "G2", "G3", "G4", "G5", "N"]


# ---------------------------------------------------------------- Fig 8
def fig8_hierarchy(res, fig_dir):
    P = D.build_panel(res["data"], res["exp"], res["masks"], "south")
    lgb = pickle.load(open(RES / "benchmark_v1" / "models" / "lightgbm_models.pkl", "rb"))
    S = {}
    for k in ("forecast", "nowcast"):
        S[k] = D.level_scores(P, P["rho"] - D.apply_rho_models(P, lgb[k], k), bands_used=["raw"])["raw"]
    Sf, Sn = S["forecast"], S["nowcast"]
    cases = [("C05/C06 · 25–30 Jan 2023 (logger: hold → zero fill)", "2023-01-25 12:00", "2023-01-30 00:00", ["L1", "B1", "F4"]),
             ("C02 · 29 Oct – 4 Nov 2022 (F4 feeder outage)", "2022-10-29 06:00", "2022-11-04 00:00", ["F4", "F1", "L1"])]
    check = {}
    fig, axs = plt.subplots(3, 2, figsize=(13, 6.6), sharex="col")
    for col, (title, a, b, zs) in enumerate(cases):
        axs[0, col].plot(Sf["g"][a:b], color="#0B2545", lw=.8, label="g, forecast residual")
        axs[0, col].plot(Sn["g"][a:b], color="#C8553D", lw=.8, ls="--", label="g, nowcast residual (guide eq. 13)")
        axs[0, col].set_ylabel("region g"); axs[0, col].set_title(title, fontsize=9)
        check[title] = dict(g_forecast_max=round(float(Sf["g"][a:b].max()), 1), g_nowcast_max=round(float(Sn["g"][a:b].max()), 1))
        for c, colr in zip(["Laayoune", "Boujdour", "Foum eloued"], ["#2F6690", "#3A7D44", "#C8553D"]):
            axs[1, col].plot(Sf["u"][c][a:b], color=colr, lw=.8, label=f"u {CITY_SHORT[c]}")
        axs[1, col].set_ylabel("city u")
        for z, colr in zip(zs, ["#C8553D", "#2F6690", "#3A7D44"]):
            axs[2, col].plot(Sf["v"][z][a:b], color=colr, lw=.8, label=f"v {z}")
        axs[2, col].set_ylabel("zone v")
        axs[2, col].xaxis.set_major_locator(mdates.DayLocator())
        axs[2, col].xaxis.set_minor_locator(mdates.HourLocator(byhour=[12]))
        axs[2, col].xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
        for r_ in range(3):
            axs[r_, col].set_yscale("symlog", linthresh=10)
            axs[r_, col].set_ylim(top=axs[r_, col].get_ylim()[1] * 8)          # headroom: the legend sits above the data
            axs[r_, col].legend(fontsize=6.5, loc="upper right", ncol=3)
            for st in ["dead", "hold", "interp"]:
                m = P["states"][st][zs[0]][a:b]
                axs[r_, col].fill_between(m.index, 0, 1, where=m.to_numpy(), step="post", color=COL["zero" if st == "dead" else st],
                                          alpha=.15, lw=0, transform=axs[r_, col].get_xaxis_transform())
    fig.suptitle("Fig 8 — Level scores (robust z, eq. 15) of the residual hierarchy: a logger episode moves the region part, "
                 "a feeder outage only the zone part", y=1.01)
    fig.tight_layout(); savefig(fig, fig_dir, "fig8_residual_hierarchy")
    return check


# ---------------------------------------------------------------- Fig 9
SHORT = {
    "ours (rules + detector)": "ours: rules + main detector",
    "rules only (rule engine v1)": "rules only",
    B.V_GAT: "main detector: TCN-GAT, hierarchy, multi-scale",
    B.V_TCN_MS: "  – learned graph (TCN, hierarchy, multi-scale)",
    B.V_MEAN: "mean(LightGBM, TCN-GAT)",
    B.V_HYB: "LightGBM + learned-graph correction",
    B.V_HYB_NOG: "LightGBM + TCN correction",
    B.V_LGB: "LightGBM forecast",
    B.V_SINGLE: "  – multi-scale (raw band only)",
    B.V_FLAT: "  – hierarchy (flat residual)",
    B.V_TCN_RAW: "  – graph, – multi-scale (TCN, raw band)",
    B.V_NOW: "LightGBM nowcast (raw band)",
    B.V_GAT_NB3: "main detector, NB3 event formation",
    B.V_LGB_NB3: "LightGBM, NB3 event formation",
    "STL + MAD": "STL + MAD", "Isolation Forest": "Isolation Forest", "LOF": "LOF",
    "GDN": "GDN (deep: learned graph)", "USAD": "USAD (deep: autoencoders)",
}
ORDER9 = ["ours (rules + detector)", "rules only (rule engine v1)", B.V_GAT, B.V_TCN_MS, B.V_SINGLE, B.V_FLAT, B.V_TCN_RAW,
          B.V_GAT_NB3, B.V_MEAN, B.V_HYB, B.V_HYB_NOG, B.V_LGB, B.V_LGB_NB3, B.V_NOW, "STL + MAD", "Isolation Forest", "LOF",
          "GDN", "USAD"]
BASE9 = ["rules only (rule engine v1)", "STL + MAD", "Isolation Forest", "LOF", "GDN", "USAD"]
# paper mode: the compared methods only; the ablations of the main detector are in Figure 8 (fig9b_ablations)
ORDER9_PAPER = ["ours (rules + detector)", "rules only (rule engine v1)", B.V_GAT, B.V_LGB, B.V_MEAN, B.V_HYB,
                "STL + MAD", "LOF", "Isolation Forest", "GDN", "USAD"]


def detection_runs():
    rows = []
    for f in sorted((RES / "benchmark_v1" / "runs").glob("r*_detection.csv")):
        m = re.search(r"r(\d\d)_s(\d\d)", f.name)
        d = pd.read_csv(f).merge(pd.read_csv(f.with_name(f.name.replace("_detection", "_auc"))), on=["method", "period"], how="left")
        rows.append(d.assign(rate=int(m.group(1)) / 100, seed=int(m.group(2))))
    nb4 = pd.concat(rows, ignore_index=True)
    ga = pd.read_csv(RES / "benchmark_v1" / "graph_ablation" / "test_detection.csv")
    ga = ga[ga.method == B.V_TCN_MS]
    deep = pd.read_csv(RES / "benchmark_v1" / "deep_baselines" / "test_detection.csv")      # GDN, USAD (D82)
    cols = ["method", "period", "rate", "seed", "f1", "auc_pr"]
    d = pd.concat([nb4[cols], ga[cols], deep[cols]], ignore_index=True)
    return d[d.period == "test"]


def _fig9_draw(dt, rates, order, seps, size, paper_name, fig_dir, ms=(5, 4)):
    """Figure 7 in submission form: print width, no title, one PDF."""
    fig, axs = plt.subplots(1, 3, figsize=size, sharey=True)
    for ax, rate in zip(axs, rates):
        d = dt[dt.rate == rate]
        for i, m in enumerate(order):
            g = d[d.method == m]
            col = "#C8553D" if m in ("ours (rules + detector)", B.V_GAT) else ("#2F6690" if m in BASE9 else "#7B5EA7")
            ax.errorbar(g.f1.mean(), i, xerr=g.f1.std(ddof=1), fmt="o", color=col, ms=ms[0], capsize=1.5, lw=0.9)
            ax.errorbar(g.auc_pr.mean(), i + 0.3, xerr=g.auc_pr.std(ddof=1), fmt="s", color=col, mfc="white", ms=ms[1],
                        capsize=1.5, lw=0.9)
        for y in seps:
            ax.axhline(y, color="#DDDDDD", lw=0.6)
        ax.set_yticks(range(len(order))); ax.set_yticklabels([SHORT_PAPER.get(m, SHORT[m]) for m in order]); ax.invert_yaxis()
        ax.set_xlim(0, 1); ax.set_xticks([0, 0.25, 0.5, 0.75, 1]); ax.set_xticklabels(["0", ".25", ".5", ".75", "1"])
        ax.set_title(f"{rate:.0%} contamination")
        ax.grid(axis="x", color="#EEEEEE", lw=0.5); ax.set_axisbelow(True)
    axs[1].set_xlabel("event F1 (●) and step-wise AUC-PR (□)")
    fig.tight_layout(w_pad=0.6)
    fig.savefig(f"{fig_dir}/{paper_name}.pdf", bbox_inches="tight"); print("saved", f"{fig_dir}/{paper_name}.pdf")


SHORT_PAPER = {"ours (rules + detector)": "full method (rules + main detector)", B.V_GAT: "main detector (TCN-GAT)",
               B.V_LGB: "LightGBM residual", B.V_MEAN: "mean of LightGBM and TCN-GAT",
               B.V_HYB: "LightGBM + learned-graph correction", "STL + MAD": "STL"}


def fig9_detection(fig_dir, paper_name=None):
    """Repo version: every method, ablations included. Paper mode (paper_name): the compared methods only (the
    ablations are Figure 8), no title (the caption carries it), one PDF; the caller sets pdf.fonttype 42."""
    dt = detection_runs()
    rates = [0.01, 0.03, 0.07]
    order = ORDER9_PAPER if paper_name else ORDER9
    seps = (1.5, 2.5, 5.5) if paper_name else (1.5, 7.5, 13.5)
    if paper_name:
        with plt.rc_context({"font.size": 7, "axes.titlesize": 7.5, "axes.labelsize": 7, "xtick.labelsize": 6.5,
                             "ytick.labelsize": 7}):
            return _fig9_draw(dt, rates, order, seps, (7.2, 3.1), paper_name, fig_dir, ms=(3.5, 3))
    fig, axs = plt.subplots(1, 3, figsize=(16, 6.0), sharey=True)
    for ax, rate in zip(axs, rates):
        d = dt[dt.rate == rate]
        for i, m in enumerate(order):
            g = d[d.method == m]
            col = "#C8553D" if m in ("ours (rules + detector)", B.V_GAT) else ("#2F6690" if m in BASE9 else "#7B5EA7")
            ax.errorbar(g.f1.mean(), i, xerr=g.f1.std(ddof=1), fmt="o", color=col, ms=5, capsize=2)
            ax.errorbar(g.auc_pr.mean(), i + 0.28, xerr=g.auc_pr.std(ddof=1), fmt="s", color=col, mfc="white", ms=4, capsize=2)
        for y in seps:
            ax.axhline(y, color="#DDDDDD", lw=0.7)
        ax.set_yticks(range(len(order))); ax.set_yticklabels([SHORT[m] for m in order], fontsize=7.5)
        ax.invert_yaxis()
        ax.set_xlim(0, 1); ax.set_title(f"{rate:.0%} contamination", fontsize=10); ax.set_xlabel("event F1 (●) and step AUC-PR (□)")
        ax.grid(axis="x", color="#EEEEEE", lw=0.6); ax.set_axisbelow(True)
    fig.suptitle("Fig 9 — Detection on injected events (test period, mean ± sd over 10 seeds). Red: ours and the main detector; "
                 "purple: its ablations (–) and other predictors; blue: baselines (classical and deep)", y=1.0, fontsize=10.5)
    fig.tight_layout(); savefig(fig, fig_dir, "fig9_detection")


# ---------------------------------------------------------------- E4
def e4_signatures(cat, fig_dir):
    items = pd.read_csv(RES / "catalogue_v1" / "items.csv")
    d = items[items.kind == "dead"].merge(cat[["item_id", "label"]], on="item_id", how="left")
    labs = [l for l in ORDER_CL if (d.label == l).any()]
    fig, axs = plt.subplots(1, 3, figsize=(14, 4))
    bins = np.linspace(0, 1, 11)
    bottom = np.zeros(len(bins) - 1)
    for l in labs:
        h, _ = np.histogram(d[d.label == l].eta.clip(0, 1), bins)
        axs[0].bar(bins[:-1], h, width=0.095, align="edge", bottom=bottom, color=LABEL_COL_N[l], label=l); bottom += h
    axs[0].set_xlabel("exact-zero share η"); axs[0].set_ylabel("dead items"); axs[0].legend(fontsize=7, title="final label", title_fontsize=7)
    axs[0].set_title("(a) exact zeros vs noise floor (H1)", fontsize=9)
    for l in labs:
        g = d[d.label == l]
        axs[1].scatter(g.restore_ratio, g.peak_ratio, s=18, color=LABEL_COL_N[l], label=l, alpha=0.85, edgecolor="white", lw=0.4)
    axs[1].axhline(1.15, color="#888", lw=0.7, ls="--"); axs[1].text(2.6, 1.2, "π = 1.15 (R5)", fontsize=7, ha="right", color="#666")
    axs[1].set_xlabel("restoration ratio r (after the ramp, D22)"); axs[1].set_ylabel("overshoot π"); axs[1].set_ylim(0, 3)
    axs[1].set_title("(b) restoration: no class separation (R5 uninformative, F16)", fontsize=9)
    for l in labs:
        g = d[d.label == l]
        axs[2].scatter(g.duration_h, g.ramp_min.fillna(0), s=18, color=LABEL_COL_N[l], label=l, alpha=0.85, edgecolor="white", lw=0.4)
    axs[2].set_xscale("log"); axs[2].set_xlabel("duration (h)"); axs[2].set_ylabel("restoration ramp (min)")
    axs[2].set_title("(c) duration vs ramp time", fontsize=9)
    fig.suptitle(f"E4 — Signatures of the {len(d)} dead items (rule engine v1), coloured by final label", y=1.03)
    fig.tight_layout(); savefig(fig, fig_dir, "E4_signatures")


# ---------------------------------------------------------------- E6
def e6_catalogue_timeline(cat, res, fig_dir):
    zones = [(c, z, f"{CITY_SHORT[c]}{z.replace('zone', '')}") for c in ["Laayoune", "Boujdour", "Foum eloued", "Marrakech"]
             for z in res["data"][c].columns]
    row = {code: k for k, (_, _, code) in enumerate(zones[::-1])}
    fig, ax = plt.subplots(figsize=(15, 6.2))
    for (c, z, code) in zones:
        d = res["data"][c][z]
        ax.add_patch(Rectangle((mdates.date2num(d.index[0]), row[code] - 0.4), mdates.date2num(d.index[-1]) - mdates.date2num(d.index[0]), 0.8,
                               fc="#F6F6F6", ec="none"))
    sub = cat[cat.kind.isin(["dead", "fill", "detector"])]
    for r in sub.itertuples():
        zs = [z for z in str(r.zones).split(",") if z in row]
        if not zs and str(r.zones).startswith("15 zones"):
            zs = [code for (_, _, code) in zones if code[0] in "LBF"]
        a, b = mdates.date2num(pd.Timestamp(r.start)), mdates.date2num(pd.Timestamp(r.end))
        for z in zs:
            if r.source == "detector":
                ax.add_patch(Rectangle((a, row[z] - 0.4), max(b - a, 0.12), 0.8, fc="none", ec=LABEL_COL_N[r.label], lw=0.8))
            else:
                ax.add_patch(Rectangle((a, row[z] - 0.4), max(b - a, 0.12), 0.8, fc=LABEL_COL_N[r.label], ec="none"))
    for r in cat[cat.kind == "clock"].itertuples():
        ax.axvline(mdates.date2num(pd.Timestamp(r.start)), color=LABEL_COL_N["A4"] if r.label == "A4" else "#CCCCCC", lw=0.9, ls=":")
    ax.set_yticks(range(len(zones))); ax.set_yticklabels([code for (_, _, code) in zones[::-1]], fontsize=7.5)
    ax.set_ylim(-0.7, len(zones) - 0.3)
    ax.set_xlim(mdates.date2num(pd.Timestamp("2022-09-10")), mdates.date2num(pd.Timestamp("2024-05-28")))
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10])); ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
    for y in (1.5, 8.5, 11.5):
        ax.axhline(y, color="#BBBBBB", lw=0.6)
    labs = [l for l in ORDER_CL if (sub.label == l).any()]
    from matplotlib.lines import Line2D
    hand = ([Rectangle((0, 0), 1, 1, fc=LABEL_COL_N[l]) for l in labs] + [Rectangle((0, 0), 1, 1, fc="none", ec="#666")]
            + [Line2D([0], [0], color=LABEL_COL_N["A4"], ls=":", lw=1.2), Line2D([0], [0], color="#CCCCCC", ls=":", lw=1.2)])
    ax.legend(hand, labs + ["outline: detector-only candidate", "clock day labelled A4", "clock day labelled N"], ncol=len(hand), fontsize=7.5, loc="upper center",
              bbox_to_anchor=(0.5, -0.09), frameon=False)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    n_rule = int((sub.source == "rule").sum()); n_det = int((sub.source == "detector").sum())
    ax.set_title(f"E6 — The typed catalogue on one timeline: {n_rule} dead and fill items (filled) and {n_det} detector-only candidates "
                 "(outlined), final labels; dotted: clock days (A4 in colour)", fontsize=10)
    fig.tight_layout(); savefig(fig, fig_dir, "E6_catalogue_timeline")


# ---------------------------------------------------------------- E19
def e19_end_model(cat, fig_dir):
    pt = pd.read_csv(RES / "end_model_v1" / "p_type.csv")
    em = pd.read_csv(RES / "end_model_v1" / "end_model_metrics.csv")
    r = pt[pt.source == "rule"]
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.2), gridspec_kw=dict(width_ratios=[1.0, 1.15, 1.0]))
    cm = pd.crosstab(pd.Series(r.label_q.values, name="label model"), pd.Series(r.label_f.values, name="end model (OOF)"))
    axs[0].imshow(np.log1p(cm.values), cmap="Blues")
    axs[0].set_xticks(range(cm.shape[1])); axs[0].set_xticklabels(cm.columns); axs[0].set_yticks(range(cm.shape[0])); axs[0].set_yticklabels(cm.index)
    for (i, j), v in np.ndenumerate(cm.values):
        axs[0].text(j, i, v, ha="center", va="center", fontsize=7)
    axs[0].set_xlabel("end model, out of fold"); axs[0].set_ylabel("label model"); axs[0].set_title("(a) rule items (NB3, real data)", fontsize=9)
    e = em.set_index("variant")[["agree_rule_items", "normal_windows_as_N"]]
    y = np.arange(len(e))
    axs[1].barh(y - 0.2, e.agree_rule_items, height=0.38, color="#2F6690", label="agreement on rule items")
    axs[1].barh(y + 0.2, e.normal_windows_as_N, height=0.38, color="#9AA0A6", label="normal windows predicted N")
    axs[1].set_yticks(y); axs[1].set_yticklabels(e.index, fontsize=7.5); axs[1].invert_yaxis(); axs[1].set_xlim(0, 1)
    axs[1].legend(fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, frameon=False)
    axs[1].set_title("(b) agreement by variant", fontsize=9)
    det = cat[cat.source == "detector"]
    tab = det.groupby(["system", "label"]).size().unstack(fill_value=0)
    labs = [l for l in ORDER_CL if l in tab.columns]
    left = np.zeros(len(tab))
    for l in labs:
        axs[2].barh(range(len(tab)), tab[l], left=left, color=LABEL_COL_N[l], label=l); left += tab[l].to_numpy()
    axs[2].set_yticks(range(len(tab))); axs[2].set_yticklabels([f"{s}\n({'main detector' if s == 'south' else 'NB3 detector'})" for s in tab.index], fontsize=8)
    axs[2].legend(fontsize=7, ncol=len(labs), loc="upper center", bbox_to_anchor=(0.5, -0.12), frameon=False)
    axs[2].set_xlabel("detector-only candidates"); axs[2].set_title("(c) final labels of detector-only candidates", fontsize=9)
    fig.suptitle("E19 — End model: agreement with the label model, ablations, and labels of the detector-only candidates", y=1.03)
    fig.tight_layout(); savefig(fig, fig_dir, "E19_end_model")


# ---------------------------------------------------------------- E22
def e22_tetouan(fig_dir):
    import transfer as T
    split = D.SPLIT
    T.register()                       # Tetouan in the city dictionaries; register() also moves D.SPLIT to 2017 ...
    D.SPLIT = split                    # ... which this figure does not need, so the Morocco split is restored
    raw, data, _ = T.load(ROOT / "data" / "raw" / "tetouan" / "Tetuan City power consumption.csv")
    x = data["Tetouan"].rename(columns={"zone1": "T1", "zone2": "T2", "zone3": "T3"})
    fig, axs = plt.subplots(2, 1, figsize=(12, 5.4))
    cols = ["#2F6690", "#C8553D", "#3A7D44"]
    for c, k in zip(x.columns, cols):
        axs[0].plot(x[c].resample("1D").mean(), lw=1, color=k, label=c)
        axs[1].plot(x[c].loc["2017-03-06":"2017-03-12"], lw=.8, color=k)
    axs[0].set_ylabel("daily mean (kW)"); axs[0].set_title("(a) 2017, daily mean per zone", fontsize=9)
    axs[0].legend(ncol=3, fontsize=8, loc="lower left", bbox_to_anchor=(0.0, 1.02), frameon=False)
    axs[1].set_ylabel("kW"); axs[1].set_title("(b) one week, 10-min steps", fontsize=9)
    axs[1].xaxis.set_major_formatter(mdates.DateFormatter("%a %d %b"))
    fig.suptitle("E22 — UCI Tetouan: three zones of one city (transfer test)", y=1.0)
    fig.tight_layout(); savefig(fig, fig_dir, "E22_tetouan_series")


# ---------------------------------------------------------------- Fig 12
SC12 = {"S0": "#9AA0A6", "S1": "#F2A541", "S2": "#C8553D", "S3": "#2F6690"}


def fig12_downstream(fig_dir, paper_name=None):
    """(a): LightGBM MASE after anomalies by strategy, real data (NB5 Table 8, unchanged).
    (b): the same on injected data, mean over the 30 NB4 test datasets (tools/forecast_all_datasets.py, D83; NB5's
    4-dataset means before). (c): outage zone-hours / injected truth on the 30 NB4 test datasets, per rate: seeds as
    points, mean +- sd. Paper mode (paper_name): print width (7.2 in), text >= 6.5 pt, no title and no bar values (the
    paper's downstream table carries them), one PDF; the caller sets pdf.fonttype 42."""
    P = paper_name is not None
    F_PAPER = dict(title=7.5, legend=6.5, bar=6, text=6.5, tick=6.5, label=7, ms=4.5, s=5)
    F_REPO = dict(title=9, legend=8, bar=6, text=7, tick=9, label=10, ms=7, s=10)
    F = F_PAPER if P else F_REPO
    t8 = pd.read_csv(RES / "downstream_v1" / "table8_forecasting.csv")
    fa = pd.read_csv(RES / "downstream_v1" / "forecast_all" / "forecast_summary.csv")
    per = pd.read_csv(RES / "downstream_v1" / "outage_all" / "outage_per_dataset.csv")
    fig, axs = plt.subplots(1, 3, figsize=(7.2, 2.6) if P else (15, 4.4), gridspec_kw=dict(width_ratios=[1, 1, 1.25]))
    for k, (ax, data) in enumerate(zip(axs[:2], ("real", "injected"))):
        if data == "real":
            g = t8[(t8.data == data) & (t8.subset == "after anomaly (2 days)") & (t8.model == "LightGBM")]
            g = g.pivot_table(index="horizon", columns="strategy", values="MASE").reindex(["1 h", "1 day"])
            title = "(a) real data" if P else "(a) real data, test steps after an anomaly (2 days)"
        else:
            g = fa[(fa.rate == "all") & (fa.subset == "after anomaly (2 days)") & (fa.model == "LightGBM")].set_index("horizon")
            g = g[[f"MASE_{s}_mean" for s in ("S0", "S1", "S2", "S3")]].rename(columns=lambda c: c[5:7]).reindex(["1 h", "1 day"])
            title = "(b) injected data (30 datasets)" if P else "(b) injected data (mean of 30 datasets), steps after an anomaly"
        g.plot.bar(ax=ax, color=[SC12[c] for c in g.columns], rot=0, width=0.8, edgecolor="white", linewidth=0.6 if P else 1)
        ax.set_ylabel("MASE (LightGBM)" if (k == 0 or not P) else "", fontsize=F["label"]); ax.set_xlabel("")
        ax.set_title(title, fontsize=F["title"]); ax.tick_params(labelsize=F["tick"])
        ax.set_ylim(0, g.max().max() * (1.22 if P else 1.12))
        ax.legend(fontsize=F["legend"], ncol=4, loc="upper left", handlelength=1, columnspacing=0.8, frameon=False)
        if not P:
            for cont in ax.containers:
                ax.bar_label(cont, fmt="%.2f", fontsize=F["bar"], padding=1)
    ax = axs[2]
    rates = sorted(per.rate.unique())
    rows = [(f"{r:.0%}", per[per.rate == r]) for r in rates] + [("all 30", per)]
    rng = np.random.default_rng(0)
    for i, (lab, g) in enumerate(rows):
        for dy, col, key, name in ((-0.17, SC12["S0"], "naive_ratio", "naive, every dead state (S0)"),
                                   (0.17, SC12["S2"], "typed_ratio", "typed (S2)" if P else "typed, label model (S2)")):
            y = i + dy
            if lab != "all 30":
                ax.scatter(g[key], y + rng.uniform(-0.06, 0.06, len(g)), s=F["s"], color=col, alpha=0.45, lw=0, zorder=2)
            m, sd = g[key].mean(), g[key].std(ddof=1)
            ax.errorbar(m, y, xerr=sd, fmt="D" if lab == "all 30" else "o", color=col, mec="white", mew=0.8 if P else 1,
                        ms=F["ms"], capsize=2 if P else 3, lw=1.1 if P else 1.6, zorder=3, label=name if i == 0 else None)
            if P and lab == "all 30":      # paper: values only for the pooled row (cited in the text), beside the bar
                ax.text(m + sd + 0.04, y, f"{m:.2f} ± {sd:.2f}", ha="left", va="center", fontsize=F["text"], color="#1F2328")
            elif not P:
                ax.text(m, y - 0.2 if dy < 0 else y + 0.2, f"{m:.2f} ± {sd:.2f}", ha="center", va="bottom" if dy < 0 else "top",
                        fontsize=F["text"], color="#1F2328")
    ax.axvline(1, color="#1F2328", lw=0.8, ls="--", zorder=1)
    ax.text(1.0, -0.5, " truth", fontsize=F["text"], va="center", color="#1F2328")
    ax.axhline(len(rows) - 1.5, color="#DDDDDD", lw=0.8)
    ax.set_yticks(range(len(rows))); ax.set_yticklabels([lab for lab, _ in rows]); ax.invert_yaxis()
    ax.tick_params(labelsize=F["tick"])
    ax.set_ylim(len(rows) - 0.4, -0.6)
    ax.set_xlim(0.65, max(per.naive_ratio.max(), per.typed_ratio.max()) * 1.08)
    ax.set_xlabel("outage zone-hours / injected truth" if P else
                  "outage zone-hours / injected truth   (S1 interpolation: 0, outages erased)", fontsize=F["label"])
    ax.set_ylabel("contamination rate", fontsize=F["label"])
    ax.set_title("(c) outage hours, 30 injected datasets" if P else
                 "(c) outage statistics, the 30 injected test datasets (10 seeds per rate)", fontsize=F["title"])
    ax.grid(axis="x", color="#EEEEEE", lw=0.6); ax.set_axisbelow(True)
    if P:
        ax.legend(fontsize=F["legend"], loc="upper center", bbox_to_anchor=(0.45, -0.24), ncol=2, frameon=False,
                  handletextpad=0.3, columnspacing=1.0)
    else:
        ax.legend(fontsize=F["legend"], loc="lower right", frameon=False)
    if P:
        fig.tight_layout(w_pad=0.8)
        fig.savefig(f"{fig_dir}/{paper_name}.pdf", bbox_inches="tight"); print("saved", f"{fig_dir}/{paper_name}.pdf")
        return
    fig.suptitle("Fig 12 — Downstream: forecast error by cleaning strategy (test period 1 Jan – 24 May 2024) "
                 "and outage-hours error", y=1.02)
    fig.tight_layout(); savefig(fig, fig_dir, "fig12_downstream")
