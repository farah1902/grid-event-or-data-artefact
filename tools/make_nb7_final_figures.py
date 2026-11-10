# Generator for notebooks/NB7_final_figures.ipynb. Usage: python tools/make_nb7_final_figures.py notebooks/NB7_final_figures.ipynb
import sys
import nbformat as nbf
from nbformat.v4 import new_notebook, new_code_cell as C, new_markdown_cell as M

cells = []
cells.append(M(r"""# NB7 · Final figures, tables and the released catalogue

The last step of the roadmap. NB7 computes no new method result; everything is read from `results/`.

**1. The final catalogue** (D72) → `results/catalogue_final/`, released with a README (contribution 4):
- south dead and fill items: fusion with the main detector (NB4 §8b);
- Marrakech: NB3 fusion;
- clock and transfer items: the label model;
- detector-only candidates: `XS###` in the south, `XM###` in Marrakech.

**2. Figures the original plan asked for that were not drawn yet:**
- **Fig 1:** a real basemap (Natural Earth 1:50m land, no boundaries drawn; D73), and the coverage panel with rule engine v1's qualifying runs (D16);
- **Fig 2:** the typology, with the straight-line-fill signature;
- **Fig 6:** the framework.

**3. Figures regenerated with the fixes noted during the project** (D74):
- Fig 8: x-axis day labels; level scores recomputed and checked against F29;
- Fig 9: the learned-graph ablation row added;
- E4: built from v1, with final labels;
- E6: final labels;
- E19: legend fixed; panel (c) shows the final candidates;
- E22: legend fixed.

**4. The paper set** (D75) → `results/paper/`:
- the main and supplementary figures under their paper numbers, with draft captions in `MANIFEST.md`;
- every table as CSV: Tables 1–9 (new: 1 inventory, 2 typology, 3 rules, 4 key events) and Tables S1–S7.

Runtime about 2 min (local CPU; the LightGBM pickle in `results/benchmark_v1/models/` is needed for Fig 8)."""))

cells.append(C(r"""import sys, json, time
from pathlib import Path
ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(ROOT / "src"))
import pandas as pd
import matplotlib.pyplot as plt
import rules_v1 as R1, detector as D, transfer as T
import paper_figures as PF, paper_regen as RG, paper_tables as PT
pd.set_option("display.width", 220); pd.set_option("display.max_columns", 30); pd.set_option("display.max_colwidth", 60)
FIG = ROOT / "results" / "figures"
LAND = ROOT / "data" / "external" / "natural_earth" / "ne_50m_land.geojson"
T0 = time.time()
res = R1.build(ROOT / "data" / "raw" / "Data Morocco.xlsx")
print("rule engine v1:", len(res["items"]), "items")"""))

cells.append(M("## 1. The final catalogue and its release (D72)"))
cells.append(C(r"""cat = PF.final_catalogue(); eps = PF.final_episodes(cat); ke = PF.key_events_table(cat, eps)
out = PT.release_catalogue(cat, eps, ke)
print(len(cat), "entries:", cat.groupby(["system", "source"]).size().to_dict())
display(cat.groupby(["system", "label"]).size().unstack(fill_value=0))
display(cat.label_source.value_counts())
display(ke)
print("released to", out)"""))

cells.append(M("## 2. Fig 1 — data: basemap and coverage (D73)"))
cells.append(C(r"""PF.fig1_map_coverage(res, FIG, LAND); plt.show()"""))

cells.append(M("## 3. Fig 2 — typology, and Table 2"))
cells.append(C(r"""PF.fig2_typology(FIG); plt.show()
typology = PF.table2_typology(cat); display(typology)"""))

cells.append(M("## 4. Fig 6 — framework"))
cells.append(C(r"""PF.fig6_framework(FIG, n_items=int((cat.source == "rule").sum()), n_det=int((cat.source == "detector").sum())); plt.show()"""))

cells.append(M("## 5. Regenerated figures (D74)"))
cells.append(C(r"""check = RG.fig8_hierarchy(res, FIG); plt.show()
print(check)
c = check["C05/C06 · 25–30 Jan 2023 (logger: hold → zero fill)"]
assert (c["g_forecast_max"], c["g_nowcast_max"]) == (218.0, 232.6), "Fig 8 no longer reproduces F29"
RG.fig9_detection(FIG); plt.show()
RG.e4_signatures(cat, FIG); plt.show()
RG.e6_catalogue_timeline(cat, res, FIG); plt.show()
RG.e19_end_model(cat, FIG); plt.show()
RG.e22_tetouan(FIG); plt.show()
print("cross-fitting split still", D.SPLIT.date())"""))

cells.append(M("## 6. The paper set: tables, numbered figures, manifest (D75)"))
cells.append(C(r"""split = D.SPLIT; T.register(); D.SPLIT = split                       # Tetouan in the city dictionaries for Table 1
_, tet, _ = T.load(ROOT / "data" / "raw" / "tetouan" / "Tetuan City power consumption.csv")
tables = PT.build_tables(res, tet, cat, eps, ke, typology)
figs = PT.build_figures()
counts = f"{len(cat)} entries: {int((cat.source == 'rule').sum())} rule items, {int((cat.source == 'detector').sum())} detector-only candidates"
PT.write_manifest(figs, tables, counts)
print(len(tables), "tables;", len(figs), "figures;", counts)
display(pd.read_csv(PT.PAPER / "tables" / "Table1_data_inventory.csv"))
display(pd.read_csv(PT.PAPER / "tables" / "Table3_rules.csv"))"""))

cells.append(M("## 7. Summary"))
cells.append(C(r"""summary = dict(
    catalogue=dict(entries=len(cat), by_system_source={f"{a} | {b}": int(v) for (a, b), v in cat.groupby(["system", "source"]).size().items()},
                   labels=cat.label.value_counts().to_dict(), labels_rule_items=cat[cat.source == "rule"].label.value_counts().to_dict()),
    fig8_check=check, figures_main=len(PT.MAIN_FIGURES), figures_supp=len(PT.SUPP_FIGURES), tables=list(tables),
    runtime_min=round((time.time() - T0) / 60, 1))
summary = json.loads(json.dumps(summary, default=int))
(PT.PAPER / "summary.json").write_text(json.dumps(summary, indent=2)); print(json.dumps(summary, indent=1)[:1500])"""))

nb = new_notebook(cells=cells)
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nbf.write(nb, sys.argv[1])
print("wrote", sys.argv[1])
