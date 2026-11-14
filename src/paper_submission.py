"""Main figures of the paper in submission form (D86): Figures 4, 5, 6, 8, 9, 11 and 12.

One style for every figure: drawn at 7.2 in (close to Elsevier's 190-mm full-page width), text 6.5-7 pt, no title
inside the image (the caption carries it), no internal codes (C05, NB3, guide equation numbers), one PDF per figure
with TrueType fonts (the caller sets pdf.fonttype 42). Figures 1-3 are drawn by paper_figures.py and Figures 7 and 10
by paper_regen.py in their paper modes. Everything is read from stored results, except Figures 4-6, which rebuild
the per-step states with the rule engine (rules_v1) and Figure 6, which applies the saved LightGBM forecaster.
Nothing here changes a result.
"""
import pickle
import textwrap
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, FancyBboxPatch, FancyArrowPatch

import benchmark as B
import detector as D
import inject as INJ
import label_model as LM
import rules_v1 as R1
from viz import COL

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
W = 7.2                                       # figure width, inches
FS = dict(base=7, small=6.5)
INK = "#1F2328"
STYLE = {"font.size": FS["base"], "axes.titlesize": FS["base"], "axes.labelsize": FS["base"], "xtick.labelsize": FS["small"],
         "ytick.labelsize": FS["small"], "legend.fontsize": FS["small"], "axes.spines.top": False, "axes.spines.right": False,
         "legend.frameon": False}


def _save(fig, out, name):
    fig.savefig(f"{out}/{name}.pdf", bbox_inches="tight")
    plt.close(fig)
    print("saved", f"{out}/{name}.pdf")


# ---------------------------------------------------------------- Figures 4 and 5: episodes, zone by zone
def _stack(res, t0, t1, marks, highlight, out, name):
    t0, t1 = pd.Timestamp(t0), pd.Timestamp(t1)
    zones = [(c, z) for c in R1.SOUTH for z in res["data"][c].columns]
    with plt.rc_context(STYLE):
        fig, axes = plt.subplots(len(zones), 1, figsize=(W, 0.29 * len(zones) + 1.0), sharex=True)
        for i, (ax, (c, z)) in enumerate(zip(axes, zones)):
            x, xh = res["data"][c][z][t0:t1], res["exp"][c][z][t0:t1]
            mk = {k: res["masks"][c][k][z][t0:t1] for k in ("dead", "hold", "interp")}
            spans = [("hold", mk["hold"], .45), ("interp", mk["interp"], .35), ("zero", mk["dead"] & x.eq(0), .35),
                     ("dead", mk["dead"] & ~x.eq(0), .35), ("missing", x.isna(), .25)]
            tr = ax.get_xaxis_transform()
            for k, m, a in spans:
                ax.fill_between(x.index, 0, 1, where=m.to_numpy(), step="post", color=COL[k], alpha=a, lw=0, transform=tr)
            ax.plot(xh.index, xh.values, color=COL["expected"], lw=.6, ls="--")
            ax.plot(x.index, x.values, color=COL["trace"], lw=.7, drawstyle="steps-post")
            code = f"{R1.CITY_SHORT[c]}{z.replace('zone', '')}"
            hl = code in highlight
            ax.set_ylabel(code, rotation=0, ha="right", va="center", fontsize=FS["base"],
                          fontweight="bold" if hl else "normal", color=COL["artefact"] if hl else INK)
            ax.set_yticks([]); ax.spines["left"].set_visible(False)
            ymax = np.nanmax([x.max(), xh.max()]) if len(x) else 1
            ax.set_ylim(0, (ymax if np.isfinite(ymax) and ymax > 0 else 1) * 1.15)
            for tm, _ in marks:
                ax.axvline(pd.Timestamp(tm), color="#444", lw=.7, ls=":")
            if i and zones[i - 1][0] != c:                      # a line between cities
                ax.spines["top"].set_visible(True); ax.spines["top"].set_color("#888")
        for k, (tm, txt) in enumerate(marks):
            axes[0].annotate(txt, (pd.Timestamp(tm), 1.05 + 0.6 * (k % 2)), xycoords=("data", "axes fraction"),
                             fontsize=FS["small"], ha="left", va="bottom")
        axes[-1].set_xlim(t0, t1)
        axes[-1].xaxis.set_major_locator(mdates.DayLocator())
        axes[-1].xaxis.set_minor_locator(mdates.HourLocator(byhour=[6, 12, 18]))
        axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%d %b %Y"))
        leg = [Patch(color=COL["hold"], alpha=.6, label="held value"), Patch(color=COL["interp"], alpha=.5, label="straight-line fill"),
               Patch(color=COL["zero"], alpha=.5, label="exact zero"), Patch(color=COL["dead"], alpha=.5, label="noise floor"),
               Patch(color=COL["missing"], alpha=.4, label="missing stamp"),
               Line2D([], [], color=COL["trace"], lw=1, label="recorded x"),
               Line2D([], [], color=COL["expected"], lw=1, ls="--", label=r"expected $\hat{x}$")]
        fig.legend(handles=leg, loc="lower center", ncol=7, bbox_to_anchor=(.5, -.005), handlelength=1.2, columnspacing=1.0)
        fig.tight_layout(rect=(0, .05, 1, .97)); fig.subplots_adjust(hspace=.08)
        _save(fig, out, name)


def figure_4(res, out):
    _stack(res, "2023-01-25 12:00", "2023-01-29 18:00",
           [("2023-01-28 21:10", "28 Jan 21:10: Boujdour hold ends, all 15 zones at exact zero")], {"F4"}, out, "Figure_4")


def figure_5(res, out):
    _stack(res, "2024-03-31 03:00", "2024-04-02 14:00",
           [("2024-03-31 09:10", "09:10: Boujdour and Foum El Oued held"), ("2024-03-31 11:10", "11:10: zero fill; L1, L2 held")],
           {"L1", "L2"}, out, "Figure_5")


# ---------------------------------------------------------------- Figure 6: residual hierarchy
def figure_6(res, out):
    """Level scores of the LightGBM forecast residual (raw band), as fig8_residual_hierarchy without the nowcast line."""
    P = D.build_panel(res["data"], res["exp"], res["masks"], "south")
    lgb = pickle.load(open(RES / "benchmark_v1" / "models" / "lightgbm_models.pkl", "rb"))
    S = D.level_scores(P, P["rho"] - D.apply_rho_models(P, lgb["forecast"], "forecast"), bands_used=["raw"])["raw"]
    cases = [("(a) 25–30 January 2023: holds, then a 15-zone zero fill", "2023-01-25 12:00", "2023-01-30 00:00", ["L1", "B1", "F4"]),
             ("(b) 29 October – 4 November 2022: feeder outage on F4", "2022-10-29 06:00", "2022-11-04 00:00", ["F4", "F1", "L1"])]
    check = {}
    with plt.rc_context(STYLE):
        fig, axs = plt.subplots(3, 2, figsize=(W, 4.6), sharex="col")
        for col, (title, a, b, zs) in enumerate(cases):
            axs[0, col].plot(S["g"][a:b], color="#0B2545", lw=.8, label="region g")
            axs[0, col].set_title(title)
            check[title] = round(float(S["g"][a:b].max()), 1)
            for c, colr in zip(["Laayoune", "Boujdour", "Foum eloued"], ["#2F6690", "#3A7D44", "#C8553D"]):
                axs[1, col].plot(S["u"][c][a:b], color=colr, lw=.8, label=f"city u, {R1.CITY_SHORT[c]}")
            for z, colr in zip(zs, ["#C8553D", "#2F6690", "#3A7D44"]):
                axs[2, col].plot(S["v"][z][a:b], color=colr, lw=.8, label=f"zone v, {z}")
            axs[2, col].xaxis.set_major_locator(mdates.DayLocator())
            axs[2, col].xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
            for r_, lab in enumerate(["region g", "city u", "zone v"]):
                ax = axs[r_, col]
                ax.set_yscale("symlog", linthresh=10)
                ax.set_ylim(top=ax.get_ylim()[1] * 8)
                ax.legend(loc="upper right", ncol=3, handlelength=1.2, columnspacing=0.8)
                if col == 0:
                    ax.set_ylabel(f"{lab}\n(robust z)")
                for st in ["dead", "hold", "interp"]:
                    m = P["states"][st][zs[0]][a:b]
                    ax.fill_between(m.index, 0, 1, where=m.to_numpy(), step="post", color=COL["zero" if st == "dead" else st],
                                    alpha=.15, lw=0, transform=ax.get_xaxis_transform())
        fig.tight_layout(h_pad=0.4, w_pad=1.0)
        _save(fig, out, "Figure_6")
    return check


# ---------------------------------------------------------------- Figure 8: ablations of the main detector
ABL_PAPER = [
    ("− learned graph (TCN residual), same event formation", "− learned graph"),
    ("− learned graph, its own tuned event formation", "− learned graph, own event formation"),
    ("− learned graph and − multi-scale (TCN, raw band)", "− learned graph, − multi-scale"),
    ("− multi-scale (raw band only)", "− multi-scale (raw band only)"),
    ("− hierarchy (flat residual)", "− hierarchy (flat residual)"),
    ("LightGBM predictor instead of TCN-GAT (own tuning)", "LightGBM predictor, own event formation"),
    ("− tuned event formation (NB3 setting)", "− tuned event formation (untuned)"),
]


def figure_8(out):
    t = pd.read_csv(RES / "benchmark_v1" / "table7e_ablations_main_detector.csv")
    keys = [a for a, _ in ABL_PAPER]
    with plt.rc_context(STYLE):
        fig, axs = plt.subplots(1, 3, figsize=(W, 2.5), sharey=True)
        for ax, rate in zip(axs, ("1%", "3%", "7%")):
            s = t[(t.rate == rate)].set_index("ablation").loc[keys]
            y = np.arange(len(keys))[::-1]
            ax.axvline(0, color=INK, lw=0.7)
            ax.axhspan(y[1] - 0.5, y[0] + 0.5, color="#C8553D", alpha=0.07, lw=0)
            for yi, (_, r) in zip(y, s.iterrows()):
                c = "#C8553D" if r.group == "graph" else "#7B5EA7"
                ax.errorbar(r.dF1, yi, xerr=r.dF1_sd, fmt="none", ecolor=c, elinewidth=1.0, capsize=0)
                ax.plot(r.dF1, yi, "o", ms=4.5, mfc=c if r.p < 0.05 else "white", mec=c, mew=1.2)
            lo, hi = (s.dF1 - s.dF1_sd).min(), (s.dF1 + s.dF1_sd).max()
            ax.set_xlim(min(lo, 0) - 0.08 * (hi - lo), max(hi, 0) + 0.08 * (hi - lo))
            ax.set_title(f"{rate} contamination")
            ax.set_xlabel(r"$\Delta$ event F1")
            ax.grid(axis="x", color="#E5E5E5", lw=0.5); ax.set_axisbelow(True)
        axs[0].set_yticks(np.arange(len(keys))[::-1]); axs[0].set_yticklabels([b for _, b in ABL_PAPER])
        fig.tight_layout(w_pad=0.8)
        _save(fig, out, "Figure_8")


# ---------------------------------------------------------------- Figure 9: attribution (3 %)
def figure_9(out, rate=0.03, beta=0.6):
    """Rebuilt from runs/*_events.csv exactly as NB4 (typed, detected, test period); the confusion is checked against
    the stored fig10_confusion_fused.csv. beta = the 3 % beta* with abstention (results_summary 9.4)."""
    ev = pd.concat([pd.read_csv(f) for f in sorted((RES / "benchmark_v1" / "runs").glob(f"r{int(rate * 100):02d}_s*_events.csv"))],
                   ignore_index=True)
    sub = ev[ev.type.isin(INJ.TYPED) & ev.detected & (ev.period == "test")].reset_index(drop=True)
    CL = B.CL
    pf = B.fused(sub, beta)
    lab_p = np.array(CL)[pf.argmax(1)]
    cm = pd.crosstab(pd.Categorical(sub.type, categories=INJ.TYPED), pd.Categorical(lab_p, categories=CL), dropna=False)
    stored = pd.read_csv(RES / "benchmark_v1" / "fig10_confusion_fused.csv", index_col=0)
    assert (stored.to_numpy() == cm.to_numpy()).all(), "confusion differs from the stored NB4 matrix"
    eces = {}
    with plt.rc_context(STYLE):
        fig, axs = plt.subplots(1, 2, figsize=(W, 2.9), gridspec_kw=dict(width_ratios=[1.15, 1]))
        norm = cm.div(cm.sum(axis=1).replace(0, 1), axis=0)
        axs[0].imshow(norm.values, cmap="Blues", vmin=0, vmax=1, aspect="auto")
        axs[0].set_xticks(range(len(CL))); axs[0].set_xticklabels(CL)
        axs[0].set_yticks(range(len(INJ.TYPED))); axs[0].set_yticklabels(INJ.TYPED)
        for (i, j), v in np.ndenumerate(cm.values):
            if v:
                axs[0].text(j, i, v, ha="center", va="center", fontsize=FS["small"], color="w" if norm.values[i, j] > .6 else "k")
        axs[0].set_xlabel("fused label"); axs[0].set_ylabel("injected type"); axs[0].set_title("(a) confusion")
        for sp in ("top", "right", "left", "bottom"):
            axs[0].spines[sp].set_visible(False)
        bins = np.linspace(0, 1, 11)
        for name, probs, col in [("label model q", sub[[f"q_{c}" for c in CL]].to_numpy(float), "#9AA0A6"),
                                 ("end model f", sub[[f"f_{c}" for c in CL]].to_numpy(float), "#7B5EA7"),
                                 ("fusion p", pf, "#C8553D")]:
            conf = probs.max(1); corr = np.array(CL)[probs.argmax(1)] == sub.type.to_numpy()
            k = np.clip(np.digitize(conf, bins) - 1, 0, 9)
            xs = [conf[k == i].mean() for i in range(10) if (k == i).sum() >= 5]
            ys = [corr[k == i].mean() for i in range(10) if (k == i).sum() >= 5]
            eces[name] = LM.ece(conf, corr)
            axs[1].plot(xs, ys, "o-", color=col, ms=3.5, lw=1.0, label=f"{name} (ECE {eces[name]:.3f})")
        axs[1].plot([0, 1], [0, 1], color="#bbb", lw=.7, ls="--")
        axs[1].set_xlabel("confidence"); axs[1].set_ylabel("accuracy"); axs[1].legend(loc="upper left")
        axs[1].set_title("(b) reliability")
        fig.tight_layout(w_pad=1.5)
        _save(fig, out, "Figure_9")
    return eces


# ---------------------------------------------------------------- Figure 11: transfer protocol
FROZEN, FROZEN_T = "#2F6690", "#E3ECF5"
EST, EST_T = "#C77C11", "#FCEFD9"
ADAPT, ADAPT_T = "#5F6B76", "#F1F2F4"
STAGES = [
    ("Per-step states and items", "relative thresholds: dead ≤ 5 % of x̂; hold and straight line ≥ 6 points",
     "expected value x̂ (median of the previous 14 days)", None),
    ("19 labelling rules", "every rule and threshold", None, "the two multi-city rules cannot fire"),
    ("Label model", "parameters π, θ fitted on Morocco; one E-step, no refit", None, None),
    ("Predictor (TCN-GAT)", "architecture and training settings", "weights, on rule-clean steps (two folds)",
     "graph: the 3 same-city edges only"),
    ("Residual hierarchy and scores", "MODWT LA(8), J = 4; robust z-score, 28-day window", "score scales",
     "city part = region part"),
    ("Event formation", "w = 24, q = 99.9 %, merge gap 12, runs ≥ 3 steps", "threshold $\\gamma_q$ at the frozen percentile", None),
]


def _box(ax, x, y, w, h, text, fc, ec, wrap, ls="-", weight="normal"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.003,rounding_size=0.006", fc=fc, ec=ec, lw=0.9, ls=ls))
    ax.text(x + 0.008, y + h / 2, textwrap.fill(text, wrap, break_on_hyphens=False), ha="left", va="center",
            fontsize=FS["small"], color=INK, weight=weight, linespacing=1.15)


def figure_11(out):
    with plt.rc_context(STYLE):
        fig = plt.figure(figsize=(W, 4.0))
        ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
        # wrap widths in characters for 6.5-pt text in boxes of 0.17, 0.30, 0.26 and 0.23 x 7.2 in
        cols = [(0.005, 0.17, "Stage", INK, None, None, 20),
                (0.185, 0.30, "Frozen\nfrom Morocco", FROZEN, FROZEN_T, "-", 40),
                (0.495, 0.26, "Re-estimated from\nTetouan's unlabelled series", EST, EST_T, "-", 34),
                (0.765, 0.23, "Changed by a\nsingle-city system", ADAPT, ADAPT_T, "--", 30)]
        top, h, gap = 0.865, 0.124, 0.018
        for x, w, head, col, *_ in cols:
            ax.text(x + 0.004, 0.94, head, ha="left", va="center", fontsize=FS["base"], weight="bold", color=col,
                    linespacing=1.1)
        for i, (stage, fr, es, ad) in enumerate(STAGES):
            y = top - i * (h + gap) - h + 0.03
            _box(ax, cols[0][0], y, cols[0][1], h, f"{i + 1}  {stage}", "white", INK, cols[0][6], weight="bold")
            for (x, w, _, col, fc, ls, wrap), txt in zip(cols[1:], (fr, es, ad)):
                if txt:
                    _box(ax, x, y, w, h, txt, fc, col, wrap, ls=ls)
                else:
                    ax.text(x + w / 2, y + h / 2, "—", ha="center", va="center", color="#999", fontsize=FS["base"])
            if i < len(STAGES) - 1:
                xm = cols[0][0] + cols[0][1] / 2
                ax.add_patch(FancyArrowPatch((xm, y), (xm, y - gap), arrowstyle="-|>", mutation_scale=7, color=INK, lw=0.8))
        _save(fig, out, "Figure_11")


# ---------------------------------------------------------------- Figure 12: Tetouan
TET_SHOW = [("ours (rules + detector)", "full method", "#C8553D"), ("rules only (rule engine v1)", "rules alone", "#2F6690"),
            (B.V_GAT, "main detector (TCN-GAT)", "#C8553D"), (B.V_TCN_MS, "main detector, no graph", "#7B5EA7"),
            (B.V_LGB, "LightGBM residual", "#7B5EA7"), ("STL + MAD", "STL", "#2F6690"),
            ("Isolation Forest", "Isolation Forest", "#2F6690"), ("LOF", "LOF", "#2F6690")]


def figure_12(out):
    det = pd.concat([pd.read_csv(f).assign(rate=int(f.name[1:3]) / 100) for f in
                     sorted((RES / "transfer_tetouan" / "runs").glob("r*_detection.csv"))], ignore_index=True)
    cm = pd.read_csv(RES / "transfer_tetouan" / "confusion_label_model_3pct.csv", index_col=0)
    with plt.rc_context(STYLE):
        fig, axs = plt.subplots(1, 2, figsize=(W, 2.9), gridspec_kw=dict(width_ratios=[1.35, 1]))
        ys = np.arange(len(TET_SHOW))[::-1]
        for k, (rate, mk) in enumerate(zip((0.01, 0.03, 0.07), ["o", "s", "D"])):
            for y, (m, _, col) in zip(ys, TET_SHOW):
                g = det[(det.rate == rate) & (det.method == m)].f1
                axs[0].errorbar(g.mean(), y + (1 - k) * 0.24, xerr=g.std(ddof=1), fmt=mk, color=col, ms=3.5, capsize=0, lw=0.8,
                                mfc=col if rate == 0.03 else "white", label=f"{rate:.0%}" if y == ys[0] else None)
        axs[0].set_yticks(ys); axs[0].set_yticklabels([lab for _, lab, _ in TET_SHOW])
        axs[0].set_xlim(0, 1); axs[0].set_xlabel("event F1 (mean ± s.d., 10 seeds)")
        axs[0].legend(title="contamination", title_fontsize=FS["small"], loc="upper left")
        axs[0].grid(axis="x", color="#EEEEEE", lw=0.5); axs[0].set_axisbelow(True)
        axs[0].set_title("(a) detection")
        norm = cm.div(cm.sum(axis=1).replace(0, 1), axis=0)
        axs[1].imshow(norm.values, cmap="Blues", vmin=0, vmax=1, aspect="auto")
        axs[1].set_xticks(range(cm.shape[1])); axs[1].set_xticklabels(cm.columns)
        axs[1].set_yticks(range(cm.shape[0])); axs[1].set_yticklabels(cm.index)
        for (i, j), v in np.ndenumerate(cm.values):
            if v:
                axs[1].text(j, i, v, ha="center", va="center", fontsize=FS["small"], color="w" if norm.values[i, j] > .6 else "k")
        axs[1].set_xlabel("label (frozen label model)"); axs[1].set_ylabel("injected type"); axs[1].set_title("(b) attribution, 3 %")
        for sp in ("top", "right", "left", "bottom"):
            axs[1].spines[sp].set_visible(False)
        fig.tight_layout(w_pad=1.5)
        _save(fig, out, "Figure_12")
