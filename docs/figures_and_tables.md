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

All NB3 figures come from the local run with the scikit-learn fallback (D39). Regenerate them from the Colab LightGBM run before publishing.

| File | Notebook | Content | Role | Notes / caveats |
|---|---|---|---|---|
| `fig8_residual_hierarchy` | NB3 | Level scores g, u, v during C05/C06 (logger: hold → zero fill) vs C02 (F4 feeder outage); g from the forecast and nowcast residuals | **main** (guide Fig 8) | Logger zero fill → g about 10², while a feeder outage moves only v (F4). Holds move v and u but not g coherently (F30) |
| `E16_predictor_example` | NB3 | One normal week of L1: observed ρ, forecast, nowcast, residual | supp | F28 |
| `E17_detector_only_candidates` | NB3 | Detector-only candidates over time (score, zones) and start hours | supp | F32 |
| `E18_detector_only_gallery` | NB3 | Top-scoring candidates per nature (partial drop, surge, other) | **main candidate** | Shows near-dead runs above ε, a sub-30-min system-wide disturbance and sustained surges (F32) |
| `E19_end_model` | NB3 | (a) label model vs out-of-fold end model on rule items; (b) agreement per ablation variant; (c) end-model labels of detector candidates | supp | F33 |

Guide plan update: **Fig 8 (residual hierarchy) is done.** Fig 6 (framework) should now show the residual hierarchy feeding the end model and the detector-only candidate stream.

## The guide's figure and table plan — status

| Guide item | Status | Where / what remains |
|---|---|---|
| Fig 1 (map + coverage) | done (schematic map) | `fig1_map_coverage`; real basemap in NB7 |
| Fig 2 (typology diagram) | **to draw** | Must now include the linear-fill signature: A2 = simultaneous fill (hold or linear), A3 = single-zone fill (stuck or linear) |
| Fig 3 (Jan 2023) | done | `fig3_C05_C06_jan2023` |
| Fig 4 (Mar 2024) | done | `fig4_C12_mar2024` |
| Fig 5 (clock evidence) | done | `fig5_clock_2022-10-30` |
| Fig 6 (framework diagram) | **to draw** | Update: item kinds (dead, fill, clock, transfer), episodes, constrained label model (D28–D34) |
| Fig 7 (rule coverage, overlap, conflict) | done | `fig7_rule_diagnostics` |
| Fig 8 (residual hierarchy g, u, v) | done | `fig8_residual_hierarchy` (NB3) |
| Fig 9 (detection PR curves) | pending | NB4 |
| Fig 10 (attribution confusion matrix) | pending | NB4 |
| Fig 11 (reliability diagram) | pending | NB4. NB2 has the synthetic-recovery ECE only |
| Fig 12 (downstream MASE, outage-hours error) | pending | NB5 |
| Table 1 (data inventory) | done | `docs/results_summary.md` §1 |
| Table 2 (typology and signatures) | to update | The guide's table plus the linear-fill signatures (F01) |
| Table 3 (labelling rules) | done | `docs/methods.md` §4 |
| Table 4 (event catalogue) | draft done | `docs/results_summary.md` §7; full list in `results/labels_v1/q.csv` and `episodes_labelled.csv` |
| Table 5–7 (detection, attribution, ablations) | pending | NB4 |
| Table 8 (forecasting) | pending | NB5 |
| Table 9 (Tetouan) | pending | NB6 |

## Candidate new tables

- **Label-model comparison:** stability and parameter recovery for constrained DS, the guide's DS and majority vote (`docs/results_summary.md` §6). Good for justifying D32.
- **Learned rule parameters** a, b, log(a/b) and precision (`results/labels_v1/rule_params.csv`).
- **Corrections to the guide's method** (`docs/paper_handoff.md` §3), as a methods table or an appendix.
