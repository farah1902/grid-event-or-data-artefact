"""Export all main figures of the paper in submission form (D78, D85, D86): no title inside the image (the caption
carries it), no internal codes, TrueType fonts embedded (pdf.fonttype 42), one PDF per figure named Figure_N.pdf in
paper/figures/. Numbering = order of first citation (paper/OUTLINE.md).

    Figure_1  data map and coverage            paper_figures.fig1_map_coverage
    Figure_2  typology                          paper_figures.fig2_typology
    Figure_3  framework                         paper_figures.fig6_framework
    Figure_4  January 2023 episode              paper_submission.figure_4
    Figure_5  31 March - 2 April 2024 episode   paper_submission.figure_5
    Figure_6  residual hierarchy                paper_submission.figure_6 (needs results/benchmark_v1/models/lightgbm_models.pkl)
    Figure_7  detection                         paper_regen.fig9_detection (paper mode)
    Figure_8  ablations of the main detector    paper_submission.figure_8
    Figure_9  attribution                       paper_submission.figure_9 (checks the stored confusion matrix)
    Figure_10 downstream                        paper_regen.fig12_downstream (paper mode)
    Figure_11 transfer protocol                 paper_submission.figure_11
    Figure_12 Tetouan                           paper_submission.figure_12

    python paper/tools/export_figures.py          (~2 min: rebuilds the rule-engine states once)
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
plt.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42})   # TrueType, embedded (journal artwork rules)

import rules_v1 as R1           # noqa: E402
import paper_figures as PF      # noqa: E402
import paper_regen as RG        # noqa: E402
import paper_submission as PS   # noqa: E402

OUT = ROOT / "paper" / "figures"
XLSX = ROOT / "data" / "raw" / "Data Morocco.xlsx"
LAND = ROOT / "data" / "external" / "natural_earth" / "ne_50m_land.geojson"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cat = pd.read_csv(ROOT / "results" / "catalogue_final" / "catalogue.csv")
    n_items, n_det = int((cat.source == "rule").sum()), int((cat.source == "detector").sum())
    PF.fig2_typology(OUT, paper_name="Figure_2"); plt.close("all")
    PF.fig6_framework(OUT, n_items=n_items, n_det=n_det, paper_name="Figure_3"); plt.close("all")
    RG.fig9_detection(OUT, paper_name="Figure_7"); plt.close("all")
    PS.figure_8(OUT)
    print("Figure_9 ECE (pooled, 3 %):", {k: round(v, 3) for k, v in PS.figure_9(OUT).items()})
    RG.fig12_downstream(OUT, paper_name="Figure_10"); plt.close("all")
    PS.figure_11(OUT)
    PS.figure_12(OUT)
    res = R1.build(XLSX)
    PF.fig1_map_coverage(res, OUT, LAND, paper_name="Figure_1"); plt.close("all")
    PS.figure_4(res, OUT)
    PS.figure_5(res, OUT)
    print("Figure_6 region-score maxima:", PS.figure_6(res, OUT))


if __name__ == "__main__":
    main()
