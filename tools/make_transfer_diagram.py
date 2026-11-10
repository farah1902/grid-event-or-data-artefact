"""Fig 14: the transfer protocol (NB6, D71). Draws, stage by stage, what is frozen from Morocco, what is re-estimated
from Tetouan's unlabelled series, and what the single-city system changes, with the results of the transfer.
Every element is listed in docs/transfer_protocol.md; the numbers are in results/transfer_tetouan/summary.json.

    python tools/make_transfer_diagram.py      -> results/figures/fig14_transfer_protocol.{png,pdf}
"""
import json, sys, textwrap
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from viz import savefig

S = json.loads((ROOT / "results" / "transfer_tetouan" / "summary.json").read_text())
F1 = [S["detection_F1"][f"{r} | ours (rules + detector)"] for r in ("1%", "3%", "7%")]
RULES = [S["detection_F1"][f"{r} | rules only (rule engine v1)"] for r in ("1%", "3%", "7%")]
ALARMS = S["real_alarms"]["TCN-GAT, hierarchy, multi-scale"]["n"]
N_EV = S["injected_events"]

BLUE, BLUE_T = "#2F6690", "#E3ECF5"        # frozen
ORANGE, ORANGE_T = "#C77C11", "#FCEFD9"    # re-estimated from the target's unlabelled data
GREY, GREY_T = "#5F6B76", "#F1F2F4"        # single-city adaptation
RED, RED_T = "#C8553D", "#FBE9E5"          # results
INK = "#1F2328"


def box(ax, x, y, w, h, text, fc, ec, fs=8.2, ls="-", weight="normal", wrap=None, ha="left", lw=1.3):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.004,rounding_size=0.008", fc=fc, ec=ec, lw=lw, ls=ls))
    if wrap:
        text = "\n".join(textwrap.fill(p, wrap, break_on_hyphens=False) if p else "" for p in text.split("\n"))
    tx = x + 0.008 if ha == "left" else x + w / 2
    ax.text(tx, y + h / 2, text, ha=ha, va="center", fontsize=fs, color=INK, weight=weight, linespacing=1.25)


def arrow(ax, p, q, color=INK, lw=1.4, style="-|>"):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=12, color=color, lw=lw))


def main():
    fig = plt.figure(figsize=(17, 9.6))
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.text(0.5, 0.975, "Fig 14 — Transfer to Tetouan without re-tuning: what is frozen, what is learned from unlabelled data, "
            "what one city changes", ha="center", va="center", fontsize=13, weight="bold", color=INK)

    # ---------------- source
    box(ax, 0.012, 0.62, 0.17, 0.30,
        "SOURCE · Morocco (UCI 1158)\n15 zones · 3 cities · 2022–24 · A\n\n"
        "Chosen here, then frozen:\n• 19 rules and all thresholds\n• label-model π, θ (Dawid–Skene)\n"
        "• detector design + training config\n• event formation (w, q, gap)\n  on development seeds 100–104",
        BLUE_T, BLUE, fs=8.6)
    arrow(ax, (0.185, 0.77), (0.215, 0.77), BLUE, lw=2)
    ax.text(0.2, 0.795, "frozen", ha="center", fontsize=8, color=BLUE, weight="bold")

    # ---------------- target
    box(ax, 0.818, 0.79, 0.17, 0.13,
        "TARGET · Tetouan (UCI)\n3 zones · 1 city · 2017 · kW\nno labels · pre-cleaned series", GREY_T, GREY, fs=8.6)

    # ---------------- pipeline stages
    cols = dict(stage=(0.22, 0.13), frozen=(0.355, 0.17), est=(0.53, 0.14), adapt=(0.675, 0.13))
    heads = dict(frozen=("FROZEN from Morocco", BLUE), est=("RE-ESTIMATED from Tetouan's\nunlabelled series", ORANGE),
                 adapt=("ONE-CITY ADAPTATION\n(structural, not tuned)", GREY))
    ax.text(cols["stage"][0] + cols["stage"][1] / 2, 0.905, "PIPELINE STAGE", ha="center", fontsize=9, weight="bold", color=INK)
    for k, (t, c) in heads.items():
        ax.text(cols[k][0] + cols[k][1] / 2, 0.905, t, ha="center", va="center", fontsize=8.6, weight="bold", color=c)
    stages = [
        ("1  Per-step states → items", "dead ε = 5 % of x̂, hold ≥ 6, linear fill ≥ 6 points (relative: kW vs A needs no change)",
         "x̂ = same-slot median of the previous 14 days", None),
        ("2  19 labelling rules vote", "every threshold (τ, η, r, π, κ, δ*, hours, durations)", None,
         "R1 multi-city zero and R7 regional outage cannot fire"),
        ("3  Label model", "π, θ fitted on Morocco; applied by one E-step (no refit); 0 unseen rule outputs", None, None),
        ("4  Predictor: TCN-GAT", "architecture + training config (Huber, AdamW, 40 epochs, patience 6, seed 0)",
         "weights, on rule-clean steps; 2 folds split at 1 Jul 2017", "graph = 3 same-city edges, no cross-city edge"),
        ("5  Multi-scale residual hierarchy", "MODWT LA(8) J = 4, phase alignment, robust z (28-day window)",
         "score scales", "city part ≡ region part (u = 0)"),
        ("6  Event formation", "smoothing w = 24, percentile q = 99.9, merge gap = 12, run ≥ 3",
         "γ = 99.9th percentile of Tetouan's rule-negative steps", None),
    ]
    y0, h, gap = 0.79, 0.096, 0.018
    for i, (name, fr, es, ad) in enumerate(stages):
        y = y0 - i * (h + gap)
        box(ax, cols["stage"][0], y, cols["stage"][1], h, name, "white", INK, fs=8.8, weight="bold", wrap=20)
        box(ax, cols["frozen"][0], y, cols["frozen"][1], h, fr, BLUE_T, BLUE, fs=7.9, wrap=36)
        if es:
            box(ax, cols["est"][0], y, cols["est"][1], h, es, ORANGE_T, ORANGE, fs=7.9, wrap=30)
        else:
            ax.text(cols["est"][0] + cols["est"][1] / 2, y + h / 2, "—", ha="center", va="center", color="#999", fontsize=10)
        if ad:
            box(ax, cols["adapt"][0], y, cols["adapt"][1], h, ad, GREY_T, GREY, fs=7.9, ls="--", wrap=34)
        else:
            ax.text(cols["adapt"][0] + cols["adapt"][1] / 2, y + h / 2, "—", ha="center", va="center", color="#999", fontsize=10)
        if i < len(stages) - 1:
            arrow(ax, (cols["stage"][0] + cols["stage"][1] / 2, y), (cols["stage"][0] + cols["stage"][1] / 2, y - gap), INK, lw=1.1)

    # ---------------- results
    arrow(ax, (0.903, 0.785), (0.903, 0.73), GREY, lw=1.4)
    ax.text(0.908, 0.757, "run the frozen pipeline", fontsize=7.6, color=GREY, va="center")
    box(ax, 0.818, 0.565, 0.17, 0.16,
        f"REAL CLEAN YEAR\n\n0 false rule items\n(only the 4 clock days, all N)\n\n{ALARMS} detector alarms in 36 zone-months",
        RED_T, RED, fs=8.6, ha="center")
    box(ax, 0.818, 0.33, 0.17, 0.215,
        f"{N_EV:,} INJECTED EVENTS (30 datasets)\n\nevent F1, rules + detector\n"
        f"{F1[0]:.3f} · {F1[1]:.3f} · {F1[2]:.3f}\nat 1 · 3 · 7 %\n\nprecision 0.98–1.00\n"
        f"above rules alone ({RULES[0]:.3f} · {RULES[1]:.3f} · {RULES[2]:.3f})\nin 10/10 seeds at every rate",
        RED_T, RED, fs=8.6, ha="center")
    box(ax, 0.818, 0.15, 0.17, 0.16,
        "ATTRIBUTION (frozen label model)\n\n5 of 6 classes: 0.85–1.00 accuracy\nmacro-F1 without A1: 0.95–0.98\n\n"
        "A1 → G2: zero gap = city outage\nwhen there is only one city", RED_T, RED, fs=8.4, ha="center")

    # ---------------- engineering band and legend
    box(ax, 0.012, 0.035, 0.795, 0.09,
        "ENGINEERING ONLY (no threshold or setting changed):  rule engine accepts a series with no anomaly (3 empty-table fixes) · "
        "label model predict() · single-city injector (G1 not injected; A1 and U_SHOCK city-wide; A2 2–3 zones or city-wide) · "
        "cross-fitting split read at run time; graph top-k clamped · 2017 calendar and clock dates · item schema aligned.   "
        "Morocco reproduced exactly after every change (catalogue, label model, injector, TCN-GAT MAE 0.0294).   "
        "No file changed after the first injected Tetouan result (docs/transfer_protocol.md §5).",
        "white", INK, fs=8.0, wrap=205, lw=1.0)
    for k, (lab, fc, ec, ls) in enumerate([("frozen from Morocco", BLUE_T, BLUE, "-"), ("re-estimated from unlabelled target data", ORANGE_T, ORANGE, "-"),
                                           ("single-city adaptation", GREY_T, GREY, "--"), ("result on Tetouan", RED_T, RED, "-")]):
        x = 0.82 + 0  # legend column under the results
        yy = 0.105 - k * 0.022
        ax.add_patch(FancyBboxPatch((x, yy), 0.018, 0.014, boxstyle="round,pad=0.002", fc=fc, ec=ec, lw=1.1, ls=ls))
        ax.text(x + 0.024, yy + 0.007, lab, va="center", fontsize=7.8, color=INK)
    savefig(fig, ROOT / "results" / "figures", "fig14_transfer_protocol")


if __name__ == "__main__":
    main()
