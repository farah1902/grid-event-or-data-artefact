"""Table 7e and Fig 9b: every ablation of the main detector at the three contamination rates, with the learned-graph
ablation first (D67). Reads stored per-run files only (no recomputation):
  results/benchmark_v1/runs/r*_detection.csv, r*_auc.csv       (NB4, Colab)
  results/benchmark_v1/graph_ablation/test_detection.csv        (tools/graph_ablation.py, D62)

    python tools/ablation_summary.py
Outputs: results/benchmark_v1/table7e_ablations_main_detector.csv, results/figures/fig9b_ablations.{png,pdf}
"""
import re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import wilcoxon
import benchmark as B
from viz import savefig

BM = ROOT / "results" / "benchmark_v1"
V_OWN = B.V_TCN_MS + " (own tuned event formation)"
# (label in the table, method name in the run files, group)
ABL = [
    ("− learned graph (TCN residual), same event formation", B.V_TCN_MS, "graph"),
    ("− learned graph, its own tuned event formation", V_OWN, "graph"),
    ("− learned graph and − multi-scale (TCN, raw band)", B.V_TCN_RAW, "other"),
    ("− multi-scale (raw band only)", B.V_SINGLE, "other"),
    ("− hierarchy (flat residual)", B.V_FLAT, "other"),
    ("LightGBM predictor instead of TCN-GAT (own tuning)", B.V_LGB, "other"),
    ("− tuned event formation (NB3 setting)", B.V_GAT_NB3, "other"),
]
COLOR = {"graph": "#C8553D", "other": "#7B5EA7"}       # project palette (viz.py); validated pair (dataviz check)


def load():
    rows = []
    for f in sorted((BM / "runs").glob("r*_detection.csv")):
        m = re.search(r"r(\d\d)_s(\d\d)", f.name)
        d = pd.read_csv(f).assign(rate=int(m.group(1)) / 100, seed=int(m.group(2)))
        a = pd.read_csv(f.with_name(f.name.replace("_detection", "_auc")))
        rows.append(d.merge(a, on=["method", "period"], how="left"))
    nb4 = pd.concat(rows, ignore_index=True)
    ga = pd.read_csv(BM / "graph_ablation" / "test_detection.csv")
    ga = ga[ga.method != B.V_GAT]                            # the recomputed main rows equal NB4's (D62)
    cols = ["method", "period", "rate", "seed", "f1", "f1_bgx", "auc_pr"]
    det = pd.concat([nb4[cols], ga[cols]], ignore_index=True)
    return det[det.period == "test"]


def main():
    det = load()
    rows = []
    for rate in (0.01, 0.03, 0.07):
        g = det[det.rate == rate]
        ref = g[g.method == B.V_GAT].set_index("seed").sort_index()
        rows.append(dict(rate=f"{rate:.0%}", ablation="main detector (TCN-GAT, multi-scale, hierarchy, tuned)", group="main",
                         F1=f"{ref.f1.mean():.3f} ± {ref.f1.std(ddof=1):.3f}", dF1=0.0, dF1_sd=0.0, p=np.nan, main_wins=np.nan,
                         F1_bgx=round(ref.f1_bgx.mean(), 3), AUC_PR=round(ref.auc_pr.mean(), 3)))
        for label, meth, grp in ABL:
            o = g[g.method == meth].set_index("seed").reindex(ref.index)
            d = o.f1 - ref.f1
            p = float(wilcoxon(o.f1, ref.f1).pvalue) if (d != 0).any() else 1.0
            rows.append(dict(rate=f"{rate:.0%}", ablation=label, group=grp, F1=f"{o.f1.mean():.3f} ± {o.f1.std(ddof=1):.3f}",
                             dF1=round(d.mean(), 4), dF1_sd=round(d.std(ddof=1), 4), p=p, main_wins=int((d < 0).sum()),
                             F1_bgx=round(o.f1_bgx.mean(), 3), AUC_PR=round(o.auc_pr.mean(), 3)))
    t = pd.DataFrame(rows)
    t.to_csv(BM / "table7e_ablations_main_detector.csv", index=False)
    pd.set_option("display.width", 220); pd.set_option("display.max_colwidth", 60)
    print(t.to_string(index=False))

    # Fig 9b: change of event F1 relative to the main detector, per rate (small multiples, shared y order)
    labels = [a[0] for a in ABL]
    fig, axs = plt.subplots(1, 3, figsize=(13.5, 3.9), sharey=True)
    for ax, rate in zip(axs, ("1%", "3%", "7%")):
        s = t[(t.rate == rate) & (t.group != "main")].set_index("ablation").loc[labels]
        y = np.arange(len(labels))[::-1]
        ax.axvline(0, color="#1F2328", lw=0.8)
        ax.axhspan(y[1] - 0.5, y[0] + 0.5, color="#C8553D", alpha=0.06, lw=0)        # the graph ablation band
        for yi, (lab, r) in zip(y, s.iterrows()):
            c = COLOR[r.group]
            ax.errorbar(r.dF1, yi, xerr=r.dF1_sd, fmt="none", ecolor=c, elinewidth=1.2, capsize=0)
            ax.plot(r.dF1, yi, "o", ms=7, mfc=c if r.p < 0.05 else "white", mec=c, mew=1.6)
            ax.annotate(f"{r.dF1:+.3f}", (r.dF1 + r.dF1_sd, yi), xytext=(4, 0), textcoords="offset points", ha="left", va="center",
                        fontsize=7, color="#444", zorder=5, bbox=dict(boxstyle="square,pad=0.15", fc="white", ec="none"))
        lo, hi = (s.dF1 - s.dF1_sd).min(), (s.dF1 + s.dF1_sd).max()
        ax.set_xlim(min(lo, 0) - 0.08 * (hi - lo), max(hi, 0) + 0.32 * (hi - lo))
        ax.set_title(f"{rate} contamination", fontsize=10)
        ax.set_xlabel("Δ event F1 vs main detector")
        ax.grid(axis="x", color="#E5E5E5", lw=0.6); ax.set_axisbelow(True)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    axs[0].set_yticks(np.arange(len(labels))[::-1]); axs[0].set_yticklabels(labels, fontsize=8)
    fig.suptitle("Fig 9b — Ablations of the main detector (test period, 10 seeds; mean ± sd of the per-seed difference; "
                 "filled = Wilcoxon p < 0.05; shaded = learned-graph ablation; x-scales differ by rate)", fontsize=9.5, y=1.02)
    fig.tight_layout()
    savefig(fig, ROOT / "results" / "figures", "fig9b_ablations")


if __name__ == "__main__":
    main()
