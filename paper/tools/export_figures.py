"""Export the paper's drawn figures in submission form: no title inside the image (the caption carries it),
TrueType fonts embedded (pdf.fonttype 42), one PDF per figure named Figure_N.pdf in paper/figures/.

Figures drawn here: Figure_1 (data map and coverage), Figure_2 (typology), Figure_3 (framework).
The other main figures are still copied by sync_figures.py until the figure step re-exports them the same way.
Run after sync_figures.py:
    python paper/tools/export_figures.py          (~1 min: rebuilds the rule-engine states for Figure 1)
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

import rules_v1 as R1          # noqa: E402
import paper_figures as PF     # noqa: E402

OUT = ROOT / "paper" / "figures"
XLSX = ROOT / "data" / "raw" / "Data Morocco.xlsx"
LAND = ROOT / "data" / "external" / "natural_earth" / "ne_50m_land.geojson"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cat = pd.read_csv(ROOT / "results" / "catalogue_final" / "catalogue.csv")
    n_items, n_det = int((cat.source == "rule").sum()), int((cat.source == "detector").sum())
    PF.fig2_typology(OUT, paper_name="Figure_2"); plt.close("all")
    PF.fig6_framework(OUT, n_items=n_items, n_det=n_det, paper_name="Figure_3"); plt.close("all")
    res = R1.build(XLSX)
    PF.fig1_map_coverage(res, OUT, LAND, paper_name="Figure_1"); plt.close("all")


if __name__ == "__main__":
    main()
