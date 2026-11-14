"""Copy the paper's main figures from results/figures/ to paper/figures/ under the submission names Figure_N.pdf.

The numbering is the paper's order of first citation (paper/OUTLINE.md). Run from anywhere:
    python paper/tools/sync_figures.py
"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "results" / "figures"
DST = ROOT / "paper" / "figures"

# paper number -> source stem in results/figures/
# Figures 1-3 (map, typology, framework) are drawn in submission form by export_figures.py and are not copied here.
FIGURES = {
    4: "fig3_C05_C06_jan2023",       # 6.1 January 2023 logger episode
    5: "fig4_C12_mar2024",           # 6.1 31 Mar - 2 Apr 2024 compound episode
    6: "fig8_residual_hierarchy",    # 6.3 residual hierarchy on real data
    7: "fig9_detection",             # 6.4 detection on injected events
    8: "fig9b_ablations",            # 6.4 ablations of the main detector (learned graph first)
    9: "fig10_11_attribution",       # 6.5 attribution: confusion and reliability
    10: "fig12_downstream",          # 6.6 downstream: forecasting and outage statistics
    11: "fig14_transfer_protocol",   # 6.7 transfer protocol
    12: "fig13_tetouan",             # 6.7 transfer results
}


def main():
    DST.mkdir(parents=True, exist_ok=True)
    for n, stem in FIGURES.items():
        src = SRC / f"{stem}.pdf"
        if not src.exists():
            raise SystemExit(f"missing {src}")
        shutil.copyfile(src, DST / f"Figure_{n}.pdf")
        print(f"Figure_{n}.pdf  <-  results/figures/{stem}.pdf")


if __name__ == "__main__":
    main()
