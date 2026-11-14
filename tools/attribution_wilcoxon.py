"""Paired Wilcoxon tests behind Table 6 (attribution on the typed injected test events the full method detects).

NB4 reports the mean macro-F1 of each labeller (results/benchmark_v1/table6_attribution.csv) but no paired test. This
script rebuilds the per-dataset macro-F1 of majority vote, the label model q and the fusion (beta* with the D50
abstention, as in NB4) from the stored run files, checks the means against Table 6, and tests the label model and the
fusion against majority vote per contamination rate (10 seeds each). Read-only on the NB4 outputs; seconds.

    python tools/attribution_wilcoxon.py
-> results/benchmark_v1/attribution_wilcoxon/{macro_f1_per_dataset.csv, wilcoxon.csv, summary.json}
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import benchmark as B  # noqa: E402

BM = ROOT / "results" / "benchmark_v1"
OUT = BM / "attribution_wilcoxon"
RATES = [0.01, 0.03, 0.07]
SEEDS = range(10)


def beta_star():
    """beta* per rate as NB4 chose it: best train-period macro-F1 with abstention, ties broken towards 0.5."""
    bt = pd.read_csv(BM / "beta_tuning_train_period.csv")
    out = {}
    for rate in RATES:
        g = bt[np.isclose(bt.rate, rate) & (bt.abstain == True)]  # noqa: E712
        out[rate] = float(g.loc[(g.macro_f1 - 1e-9 * (g.beta - 0.5).abs()).idxmax(), "beta"])
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    beta = beta_star()
    rows = []
    for rate in RATES:
        for seed in SEEDS:
            ev = pd.read_csv(BM / "runs" / f"r{round(rate * 100):02d}_s{seed:02d}_events.csv")
            sub = ev[(ev.period == "test") & ev.detected & ev.type.isin(B.TYPED)]
            y = sub.type.to_numpy()
            labs = {"majority vote (rules)": dict(labels=np.where(sub.mv.isin(B.CL), sub.mv, "N")),
                    "label model q": dict(probs=sub[[f"q_{c}" for c in B.CL]].to_numpy(float)),
                    "fusion (β*, D50 abstention)": dict(probs=B.fused(sub, beta[rate]))}
            for name, kw in labs.items():
                rows.append(dict(rate=f"{rate:.0%}", seed=seed, labeler=name, n=len(sub),
                                 macro_f1=B.attribution_scores(y, **kw)["macro_f1"]))
    per = pd.DataFrame(rows)
    per.to_csv(OUT / "macro_f1_per_dataset.csv", index=False)

    # the means must reproduce Table 6
    t6 = pd.read_csv(BM / "table6_attribution.csv")
    for (rate, name), g in per.groupby(["rate", "labeler"]):
        stored = float(t6[(t6.rate == rate) & (t6.labeler == name)].macro_F1.iloc[0].split("±")[0])
        assert abs(g.macro_f1.mean() - stored) < 5e-4, (rate, name, g.macro_f1.mean(), stored)

    wil = []
    for rate, g in per.groupby("rate", sort=False):
        w = g.pivot(index="seed", columns="labeler", values="macro_f1")
        mv = w["majority vote (rules)"]
        for other in ["label model q", "fusion (β*, D50 abstention)"]:
            d = w[other] - mv
            p = float(wilcoxon(w[other], mv).pvalue) if (d != 0).any() else 1.0
            wil.append(dict(rate=rate, comparison=f"{other} vs majority vote", mean_other=round(w[other].mean(), 4),
                            mean_mv=round(mv.mean(), 4), other_better=int((d > 0).sum()), ties=int((d == 0).sum()),
                            mv_better=int((d < 0).sum()), wilcoxon_p=p))
    wil = pd.DataFrame(wil)
    wil.to_csv(OUT / "wilcoxon.csv", index=False)
    json.dump(dict(beta_star={f"{r:.0%}": b for r, b in beta.items()}, seeds=list(SEEDS), rates=[f"{r:.0%}" for r in RATES],
                   selection="test period, detected, true type in the seven typed classes (as NB4 Table 6)",
                   test="scipy.stats.wilcoxon, two-sided, zero differences dropped (exact when no ties, else normal approximation)",
                   table6_means_reproduced=True), open(OUT / "summary.json", "w"), indent=1)
    print(wil.to_string(index=False))


if __name__ == "__main__":
    main()
