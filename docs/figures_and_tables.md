# Figures and tables

Every figure in `results/figures/` exists as PNG (200 dpi) and PDF. Style is set in `src/viz.py` (D12):
- artefacts in warm hues, grid events in blues and teal, normal grey;
- states shaded as spans: hold amber, linear interpolation teal, exact zero red, noise floor purple, missing black;
- time axis = timestamps as recorded.

"Role" is a suggestion for the paper:
- **main**: belongs in the main text;
- **supp**: supplementary material;
- **diag**: internal diagnostic, probably not published.

## Figures produced so far

| File | Notebook | Content | Role | Notes / caveats |
|---|---|---|---|---|
| `fig1_map_coverage` | NB1 | (a) schematic map of the 4 cities; (b) state bars for all 17 zones (held, linear interpolation, exact zero, noise floor, missing) with clock dates | main (guide Fig 1) | Map is schematic (D10). Panel (b) uses NB1's masks, computed before the v1 state priority (D16), so a few noise-floor spans would be teal under v1 |
| `fig3_C05_C06_jan2023` | NB1 | 25–29 Jan 2023, 15 zones stacked: L/B/F4 holds, F linear fills, then the 15-zone zero fill | **main** (guide Fig 3) | Shows F02. Boujdour II commissioning date marked |
| `fig4_C12_mar2024` | NB1 | 31 Mar – 2 Apr 2024: L1/L2 held for 43 h next to zero-filled zones | **main** (guide Fig 4) | The strongest single piece of artefact evidence |
| `fig5_clock_2022-10-30` | NB1 | Daily profiles before and after 30 Oct 2022 and corr(δ) | main (guide Fig 5) | δ\* = −60 in all 3 cities. Sign convention D08 |
| `figS_clock_{2023-03-19, 2023-04-23, 2023-10-29, 2024-03-10, 2024-04-14}` | NB1 | The same for the other clock dates | supp | Ramadan dates are confounded (F12) |
| `E1_C09_jul2023` | NB1 | 16–17 Jul 2023: city totals vs expected, plus a zoom on restoration | supp | Shows L interpolated and F above baseline (F03) |
| `E1b_C09_stack` | NB1 | 16–17 Jul 2023: all 15 zones stacked, B/F zeros next to L linear fill | **main candidate** | Overturns the guide's only G1 candidate (F03) |
| `E2_C11_transfer` | NB1 | Boujdour daily means ±45 days around 16 Dec 2023, and Δ per zone with κ | supp | G5 example (F19) |
| `E3_single_zone_timing` | NB1 | v0 single-zone events: start hour, weekday, duration | supp | Uses **v0** events and types |
| `E4_signatures` | NB1 | v0 dead events: η histogram, r vs π, ramp vs duration | supp | Uses **v0** restoration features, which were measured on synthetic ramps (F05). Regenerate from v1 before publishing |
| `E5_single_zone_gallery` | NB1 | C01, C02, C04, C07 traces | supp | The C01 panel is superseded by E10 |
| `E6_catalogue_timeline` | NB1 | All v0 events on one timeline, coloured by v0 type, with long holds and interpolations hatched | supp | v0 types. Regenerate with label-model labels for the paper |
| `E7_FoumElOued_structural` | NB1 | F quarterly level and midday/evening ratio | supp | F13 |
| `E8_Marrakech_timestamps` | NB1 | Marrakech row-to-row steps; backward jumps at 00:00 | supp | F14 |
| `fig7_rule_diagnostics` | NB1b | v1 rule coverage; rule × rule overlap and conflict matrices | main or supp (guide Fig 7) | The 69 R9–R10 conflicts are by design |
| `E9_vote_matrix` | NB1b | Votes on every multi-zone dead/fill item and every clock/transfer item with votes | supp | Shows F08 (morning fills) |
| `E10_C01_relabelled` | NB1b | C01: zeros → straight-line fill → zeros | **main candidate** | F06 |
| `E11_short_simultaneous_freezes` | NB1b | Weekly count of short simultaneous freezes per city, and Laâyoune start hours | supp | F09 |
| `E12_label_model_rules` | NB2 | Learned propensity a vs false-positive rate b per rule; log(a/b), votes, learned precision | **main candidate** | Shows R5 ≈ uninformative (F16) |
| `E13_label_confidence` | NB2 | Confidence per assigned type; entropy per item kind | supp | |
| `E14_key_event_posteriors` | NB2 | Full posterior q(y) for the items of the key events | **main candidate** | Reader-friendly evidence for the catalogue |
| `E15_label_robustness` | NB2 | % of labels changing when a rule family or a prior changes | supp | F24 |

## Figures added by NB3 (detector and end model)

All NB3 figures come from the reference run (LightGBM 4.6.0, structural-zero fix; D51, D52). Cosmetic fixes for NB7: Fig 8 repeats day labels on its x-axis (12-hour ticks with a day-only format); E19(b)'s legend overlaps the MLP bar.

| File | Notebook | Content | Role | Notes / caveats |
|---|---|---|---|---|
| `fig8_residual_hierarchy` | NB3 | Level scores g, u, v during C05/C06 (logger: hold → zero fill) vs C02 (F4 feeder outage); g from the forecast and nowcast residuals | **main** (guide Fig 8) | Logger zero fill → g about 10², while a feeder outage moves only v (F4). Holds move v and u but not g coherently (F30) |
| `E16_predictor_example` | NB3 | One normal week of L1: observed ρ, forecast, nowcast, residual | supp | F28 |
| `E17_detector_only_candidates` | NB3 | Detector-only candidates over time (score, zones) and start hours | supp | F32 |
| `E18_detector_only_gallery` | NB3 | Top-scoring candidates per nature (partial drop, surge, other) | **main candidate** | Shows near-dead runs above ε, a sub-30-min system-wide disturbance and sustained surges (F32) |
| `E19_end_model` | NB3 | (a) label model vs out-of-fold end model on rule items; (b) agreement per ablation variant; (c) end-model labels of detector candidates | supp | F33 |
| `E20_learned_graph` | NB4 | TCN-GAT graph (the graph inside the main detector, D61): edges (same city + 4 learned cross-city neighbours per zone) and mean attention on clean steps | **main** (the main detector's learned graph) | D53, D61 |
| `E21_injected_signatures` | NB4 | One injected event per type over the original series (grey) | supp | D54 |
| `fig9_detection` | NB4; regenerated (`paper_regen.fig9_detection`): learned-graph ablation row (D62), **GDN and USAD rows (D82)** | Event F1 and step AUC-PR per method at 1/3/7 %, test period, mean ± sd over seeds | **main** (guide Fig 9; dot plot instead of PR curves, because curves need stored scores) | Table 5 |
| `fig10_11_attribution` | NB4 | (a) confusion of injected type vs fused label, 3 %, test; (b) reliability of q, f and p | **main** (guide Figs 10 and 11) | Table 6 |
| `fig9b_ablations` | `tools/ablation_summary.py` | Ablations of the main detector at 1/3/7 %: ΔF1 vs main (mean ± sd of per-seed differences), filled = Wilcoxon p < 0.05, learned-graph ablation shaded and first | **main** (the graph presented as an ablation, D67) | Table 7e, F42, F43 |
| `fig14_transfer_protocol` | `tools/make_transfer_diagram.py` | The transfer protocol stage by stage: frozen from Morocco (blue), re-estimated from Tetouan's unlabelled series (orange), single-city adaptations (grey, dashed), results (red), engineering changes (bottom band) | **main** (method / transfer section; the full list is in docs/transfer_protocol.md) | D68–D71, F55–F58 |
| `fig13_tetouan` | NB6 | (a) event F1 of every method on Tetouan at 1/3/7 % (frozen method); (b) attribution confusion of the frozen label model, 3 % | **main** (transfer, RQ5) | Table 9, F56–F58 |
| `E22_tetouan_series` | NB6 | Tetouan 2017: daily mean per zone, and one week at 10-min steps | supp (data description) | F55 |
| `fig12_downstream` | NB5; **regenerated by NB7** (`paper_regen.fig12_downstream`, D76; panel (b) from the 30 datasets, D83) | (a) real-data and (b) injected-data LightGBM MASE by cleaning strategy (S0–S3) at 1 h and 1 day, test steps after an anomaly (panel (b): mean of the 30 injected datasets, `forecast_all/forecast_summary.csv`); (c) outage zone-hours / injected truth, naive (S0) and typed (S2), on all 30 NB4 test datasets: seeds as points, mean ± sd per rate and over all 30 (NB5's version used 4 datasets) | **main** (guide Fig 12) | Table 8, F51–F54 |

Guide plan update: **Fig 8 (residual hierarchy) is done.** Fig 6 (framework) should now show the residual hierarchy feeding the end model and the detector-only candidate stream.

## The guide's figure and table plan — status

| Guide item | Status | Where / what remains |
|---|---|---|
| Fig 1 (map + coverage) | **done (NB7)** | `fig1_map_coverage`: Natural Earth basemap without boundaries, southern inset, Tetouan; coverage from rule engine v1 (D73) |
| Fig 2 (typology diagram) | **done (NB7)** | `fig2_typology`: nine schematic signatures with level, signature and rules; straight-line fills in A2 and A3 |
| Fig 3 (Jan 2023) | done | `fig3_C05_C06_jan2023` |
| Fig 4 (Mar 2024) | done | `fig4_C12_mar2024` |
| Fig 5 (clock evidence) | done | `fig5_clock_2022-10-30` |
| Fig 6 (framework diagram) | **done (NB7)** | `fig6_framework`: weak-supervision lane, residual-detector lane, end model and fusion, catalogue, the three evaluations |
| Fig 7 (rule coverage, overlap, conflict) | done | `fig7_rule_diagnostics` |
| Fig 8 (residual hierarchy g, u, v) | done | `fig8_residual_hierarchy` (NB3) |
| Fig 9 (detection PR curves) | **done** (NB4 Colab run, 2026-11-09) | `fig9_detection` (dot plot of event F1 and step AUC-PR, test period). The no-graph multi-scale row (D62) is not in the figure; add it in NB7 from `graph_ablation/` |
| Fig 10 (attribution confusion matrix) | **done** | `fig10_11_attribution` (a); 3 %, test, pooled seeds. Main error A1 → G1 (F47) |
| Fig 11 (reliability diagram) | **done** | `fig10_11_attribution` (b); pooled-seed ECE (differs from Table 6's per-seed mean, results_summary §9.4); NB2 has the synthetic-recovery ECE |
| Fig 12 (downstream MASE, outage-hours error) | **done** (NB5; panel (c) extended to the 30 test datasets by NB7, D76) | `fig12_downstream`: (a) real and (b) injected LightGBM MASE by strategy after anomalies, (c) outage zone-hours / injected truth on 30 datasets. Numbers: results_summary §10 (§10.1b for panel c) |
| Table 1 (data inventory) | done | `docs/results_summary.md` §1 |
| Table 2 (typology and signatures) | **done (NB7)** | `results/paper/tables/Table2_typology.csv` (with real-data counts) |
| Table 3 (labelling rules) | done | `docs/methods.md` §4 |
| Table 4 (event catalogue) | **done (NB7)** | `results/paper/tables/Table4_key_events.csv`; the full released catalogue is `results/catalogue_final/` (D72) |
| Table 5–7 (detection, attribution, ablations) | **done** (NB4) | `results/benchmark_v1/table5*`, `table6*`, `table7*`; plus the no-graph ablation `graph_ablation/table_graph_ablation.csv` (D62) and the deep baselines `deep_baselines/table_deep_baselines.csv` (D82; **to be added to Table 5 and Fig 7 in the results step**). Numbers: results_summary §9 |
| Table 8 (forecasting) | **done** (NB5) | `results/downstream_v1/table8_forecasting.csv`, `table8_dm.csv`; results_summary §10.2 |
| Table 9 (Tetouan) | **done** (NB6) | `results/transfer_tetouan/table9_detection.csv`, `table9_attribution.csv`, `table9_recall_by_type.csv`, `table9_wilcoxon.csv`; results_summary §11 |

## Candidate new tables

- **Label-model comparison:** stability and parameter recovery for constrained DS, the guide's DS and majority vote (`docs/results_summary.md` §6). Good for justifying D32.
- **Learned rule parameters** a, b, log(a/b) and precision (`results/labels_v1/rule_params.csv`).
- **Corrections to the guide's method** (`docs/paper_handoff.md` §3), as a methods table or an appendix.

## NB7: the final paper set (D72–D75)

- **The authority for paper numbering and captions is `results/paper/MANIFEST.md`.** Main: Fig 1–14; supplementary: Fig S1–S28; tables: 28 CSVs in `results/paper/tables/` (27 at NB7; `Table8_outage_all_datasets` added by D76).
- **Renumbered for the paper:**
  - Fig 10 = `fig9b_ablations`;
  - Fig 11 = `fig10_11_attribution`;
  - Fig 13 = `fig14_transfer_protocol` (the protocol before the results);
  - Fig 14 = `fig13_tetouan`.
- **Drawn in NB7:** `fig1_map_coverage` (replaces the schematic map), `fig2_typology`, `fig6_framework`.
- **Regenerated in NB7 (D74):** `fig8_residual_hierarchy` (axis fixed; F29 reproduced), `fig9_detection` (graph-ablation row), `E4_signatures` (v1 and final labels), `E6_catalogue_timeline` (final labels), `E19_end_model` (legend; final candidates), `E22_tetouan_series` (legend).
- **Caveats now resolved:**
  - Fig 1 (D16 masks);
  - E4 (v0 features);
  - E6 (v0 types);
  - the Fig 8 axis and the E19 legend.
- **Caveats still open:**
  - E3 uses v0 events (S22);
  - E5's C01 panel is superseded by E10 (S23);
  - E17 and E18 show the NB3 LightGBM detector's candidates (S7, S17).

## Paper figures in submission form (D86)

`paper/tools/export_figures.py` draws all 12 main figures into `paper/figures/Figure_N.pdf`: no built-in title, no internal codes, 7.2 in wide, 6.5–7 pt text, TrueType fonts. Figures 1–3: `src/paper_figures.py` (paper mode); 7 and 10: `src/paper_regen.py` (paper mode); 4, 5, 6, 8, 9, 11, 12: `src/paper_submission.py`. The repo figures in `results/figures/` keep their titles (working versions).
