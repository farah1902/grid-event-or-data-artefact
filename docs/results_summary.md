# Results summary — numbers to cite

This is the single source of truth for numbers. Every value below comes from a file in `results/`, named in each
section. Status: as of 2026-11-08 (rule engine v1, label model, detector and end model). **No result here has been validated against
known types yet; that is NB4.** Item ids (D###, F###, …) change if the rule engine is re-run with other
parameters.

## 1. Data inventory (guide Table 1, verified)

| City | Zones | Step | Unit | Period | Rows | Exact zeros |
|---|---|---|---|---|---|---|
| Laâyoune (L) | 5 | 10 min | A | 14 Sep 2022 17:10 – 24 May 2024 00:00 | 88,890 | 1,465 |
| Boujdour (B) | 3 | 10 min | A | same | 88,890 | 1,413 |
| Foum El Oued (F) | 7 | 10 min | A | same | 88,890 | 4,329 (4,323 after duplicate averaging) |
| Marrakech (M) | 2 | 30 min | kW | 9 Jan 2023 – 8 Jan 2024 | 17,501 (17,520 regular steps) | 101 |

The regular grid has 12 NaN steps per southern city and 25 in Marrakech.

## 2. Timestamp audit (`results/event_catalogue_v0/timestamp_audit.csv`)

| City | Duplicated stamps | Missing runs (steps) | Backward jumps |
|---|---|---|---|
| L, B, F (each) | 12 (on 30 Oct 2022 and 29 Oct 2023, 02:00–02:50) | 2 runs, 12 steps (23 Apr 2023 and 14 Apr 2024, 02:00) | 2 |
| Marrakech | 3 (6 rows) | 4 runs, 25 steps (19 at the start) | 366 (the daily 00:00 row placed after 23:30) |

## 3. Clock offsets δ\* (`results/figures/clock_offsets.csv`; sign: negative = stamped earlier after the date)

| Date | Event | L | B | F | M |
|---|---|---|---|---|---|
| 2022-10-30 | Europe fall-back | −60 (0.987) | −60 (0.978) | −60 (0.924) | n/a |
| 2023-03-19 | Morocco → GMT | +30 (0.845) | 0 (0.903) | +20 (0.888) | +30 (0.961) |
| 2023-04-23 | Morocco → GMT+1 | −120 (0.775) | +20 (0.847) | −60 (0.910) | 0 (0.710) |
| 2023-10-29 | Europe fall-back | −120 (0.997) | −60 (0.981) | −60 (0.851) | −30 (0.826) |
| 2024-03-10 | Morocco → GMT | +120 (0.712) | −120 (0.818) | −60 (0.854) | n/a |
| 2024-04-14 | Morocco → GMT+1 | −20 (0.862) | +20 (0.918) | −120 (0.843) | n/a |
| 2023-03-26 | Europe spring-forward | +20 (0.799) | 0 (0.929) | −90 (0.753) | −30 (0.939) |
| 2024-03-31 | Europe spring-forward | 0 (0.987) | +60 (0.989) | +60 (0.767) | n/a |

The value in brackets is the correlation at δ\*. The 2023-03-26 and 2024-03-31 rows come from `results/catalogue_v1/items.csv` (clock items). Clock-item labels: 14 A4 (Oct 2022 and Oct 2023 L/B at 0.98, F Oct 2023 at 0.83, the four missing-hour dates × 3 cities at 0.70, and 2 Marrakech duplicate dates at 0.83). All Ramadan-switch dates, Europe spring-forward dates and Marrakech gap dates are N (0.95–0.97), except B on 2024-03-31 (N 0.60). R15 fires only where corr ≥ 0.9 and the gain over δ = 0 is ≥ 0.05: Oct 2022 for L, B, F; Oct 2023 for L, B; and B on 2024-03-31.

## 4. Rule engine v0 (`results/event_catalogue_v0/`)

- 72 dead events (≥ 30 min, at least one exact zero). Provisional types: G4 51, G3 17, A1 2, G1 1, G2 1.
- 220 stuck runs (≥ 6 identical non-zero values). 13 transfer candidates.
- Single-zone events: 68, of which 57 start 06:00–11:59 and 33 at weekends.

## 5. Rule engine v1 (`results/catalogue_v1/`)

**Zone runs:**

| | South | Marrakech |
|---|---|---|
| Dead | 117 | 48 |
| Hold | 95 | 7 |
| Linear interpolation | 274 | 0 |

**Items:** 327 in total (126 dead, 155 fill, 33 clock, 13 transfer).
- Dead: 78 south, 48 Marrakech. 55 dead items have no exact zero (η = 0), 43 of them in Marrakech.
- Fill: 148 south, 7 Marrakech. 85 pure interpolation, 54 pure hold, 16 mixed.

**Episodes:** 230, of which 38 have ≥ 2 items.

**Votes per rule** (`rule_summary.csv`):

| R1 | R2 | R3 | R4 | R5 | R6 | R7 | R8 | R9 | R10 | R11 | R12 | R13 | R14 | R15 | R16 | R19 | R20 | R21 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 12 | 3 | 3 | 21 | 84 | 0 | 1 | 122 | 69 | 4 | 44 | 8 | 6 | 6 | 1 | 48 | 48 | 5 |

**v0 → v1:** 70 of 72 v0 dead events keep their start time. 2 were re-segmented: C01, and v0 event 53 (21 Oct 2023 F, now a G3-type zero spell plus an A3 fill). 56 new dead items: 43 Marrakech, 13 south.

**Synthetic restoration ramps:** 25 of 117 southern dead zone-runs are followed directly by a linear fill. C02's r_E is 0.22 in v0 and 1.01 in v1.

## 6. Label model (`results/labels_v1/`)

**Stability** (`restart_stability.csv`): constrained model, all 20 restarts agree on 100 % of items. Guide-style full model: minimum agreement 62.7 %, mean 83.2 %.

**Learned rule parameters** (`rule_params.csv`):

| Rule | a (propensity) | b (false-positive rate) | log(a/b) | Votes | Learned precision |
|---|---|---|---|---|---|
| R1 | 0.403 | 0.0075 | 3.99 | 1 | 1.00 |
| R2* | 0.636 | 0.0193 | 3.50 | 12 | 0.99 |
| R3 | 0.605 | 0.0151 | 3.69 | 3 | 0.67 |
| R4 | 0.404 | 0.0225 | 2.89 | 3 | 0.33 |
| R5 | 0.168 | 0.150 | **0.12** | 21 | 0.95 |
| R6 | 0.680 | 0.0775 | 2.17 | 84 | 1.00 |
| R8* | 0.909 | 0.0075 | 4.80 | 1 | 0.99 |
| R9 | 0.992 | 0.0733 | 2.61 | 122 | 1.00 |
| R10* | 0.893 | 0.0563 | 2.76 | 69 | 0.96 |
| R11 | 0.100 | 0.0122 | 2.10 | 4 | 0.98 |
| R12* | 0.954 | 0.0308 | 3.43 | 44 | 1.00 |
| R13* | 0.923 | 0.0755 | 2.50 | 8 | 0.93 |
| R14* | 0.883 | 0.147 | 1.79 | 6 | 0.70 |
| R15 | 0.431 | 0.0574 | 2.02 | 6 | 0.89 |
| R16* | 0.890 | 0.0596 | 2.70 | 1 | 0.68 |
| R19* | 0.951 | 0.0178 | 3.98 | 48 | 1.00 |
| R20* | 0.959 | 0.0169 | 4.04 | 48 | 1.00 |
| R21 | 0.391 | 0.0381 | 2.33 | 5 | 0.19 |

\* = defining rule (propensity prior (9, 1)). R7 never fires.

**Class priors π** (per kind, `class_priors.csv`):

| Kind | Priors |
|---|---|
| dead | A1 0.030, G1 0.008, G2 0.015, G3 0.369, G4 0.577 |
| fill | A2 0.366, A3 0.607, N 0.027 |
| clock | A4 0.392, N 0.608 |
| transfer | G5 0.125, N 0.875 |

**Labels** (`q.csv`, arg max):

| A1 | A2 | A3 | A4 | G1 | G2 | G3 | G4 | G5 | N |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 57 | 95 | 14 | 0 | 1 | 53 | 69 | 1 | 34 |

- By family: 169 artefact items, 124 grid-event items, 34 normal.
- Mean confidence 0.945; 8 items below 0.7.
- Agreement with majority vote 98.2 %; with the guide-style full model 56.9 %.

**Labels by system** (dead and fill items; zone-hours ≈ duration × zones, an upper bound):

| System | Label | Items | Hours | Zone-hours |
|---|---|---|---|---|
| south | A1 | 3 | 73.7 | 936.5 |
| south | A2 | 57 | 268.3 | 1,470.2 |
| south | A3 | 88 | 197.9 | 197.9 |
| south | N (fill) | 3 | 22.7 | 22.7 |
| south | G2 | 1 | 0.8 | 4.1 |
| south | G3 | 18 | 208.3 | 208.3 |
| south | G4 | 56 | 81.5 | 81.5 |
| Marrakech | A3 | 7 | 46.0 | 46.0 |
| Marrakech | G3 | 35 | 352.0 | 352.0 |
| Marrakech | G4 | 13 | 66.5 | 66.5 |

- South totals: artefacts 2,604.6 zone-h, grid events 294.0 zone-h, out of about 222,222 zone-hours in the record (1.17 % and 0.13 %).
- A naive "zero = outage" count, (936.5 + 294.0) / 294.0, overstates southern outage time about 4.2× (F26, provisional).

**Parameter recovery** (`recovery_summary.csv`, 20 seeds):

| Labeler | Accuracy | Macro-F1 | ECE | Brier |
|---|---|---|---|---|
| Constrained DS | 0.922 ± 0.021 | 0.872 ± 0.080 | 0.033 ± 0.012 | 0.124 ± 0.028 |
| Full DS (guide) | 0.682 ± 0.058 | 0.493 ± 0.077 | 0.276 ± 0.065 | 0.577 ± 0.118 |
| Majority vote | 0.911 ± 0.017 | 0.843 ± 0.064 | n/a | n/a |

**Robustness** (`robustness.csv`; % of items whose label changes, total / dead / fill / clock / transfer):

| Change | Total | Dead | Fill | Clock | Transfer |
|---|---|---|---|---|---|
| Drop calendar (R10, R14) | 17.1 | 38.9 | 0 | 21.2 | 0 |
| Drop city (R8) | 0.3 | 0.8 | 0 | 0 | 0 |
| Drop clock (R13, R15) | 2.4 | 0 | 0 | 24.2 | 0 |
| Drop conservation (R16) | 3.7 | 0 | 0 | 0 | 92.3 |
| Drop hold (R2, R3, R4, R12) | 0.6 | 0 | 1.3 | 0 | 0 |
| Drop interpolation (R19–R21) | 46.8 | 0.8 | 98.1 | 0 | 0 |
| Drop restoration (R5, R6) | 0 | 0 | 0 | 0 | 0 |
| Drop simultaneity (R1, R7) | 0 | 0 | 0 | 0 | 0 |
| Drop single zone (R9, R11) | 0 | 0 | 0 | 0 | 0 |
| prior_b = (1, 4) | 1.8 | 0 | 0 | 18.2 | 0 |
| prior_b = (1, 19) | 0 | 0 | 0 | 0 | 0 |
| No defining prior | 16.2 | 38.9 | 1.9 | 3.0 | 0 |
| prior_pi = 0.5 | 0.9 | 0 | 1.9 | 0 | 0 |
| prior_pi = 2 | 0.9 | 0 | 1.9 | 0 | 0 |
| init a = 0.9, b = 0.02 | 0 | 0 | 0 | 0 | 0 |

## 7. Key events (draft of guide Table 4, updated)

| Guide id | Date (as recorded) | Zones | v1 items → label (q) | Reading |
|---|---|---|---|---|
| C01 | 2022-10-23 08:10 | L5 | D052 G4 (0.96) → F025 A3 → F026 A3 → D053 G3 (0.84) | zeros → straight-line fill → zeros; not a noise floor (F06) |
| C02 | 2022-10-29 20:40, 108 h | F4 | D058 G3 (0.98) → F033 A3 | feeder outage, synthetic restoration ramp (F05) |
| C03 | 2022-10-30 | L, B, F | K000/K008/K016 A4 (0.98) | European fall-back, repeated hour, δ\* = −60 |
| C04 | 2022-11-16 22:40 | F1 | D064 G3 (0.84) → F037 A3 | feeder outage + synthetic ramp |
| C05 | 2023-01-26 01:20–02:20 | all 15 | F051 A2 (1.00), F052 A2 (1.00) | simultaneous hold (L, B, F4) + linear fill (F1–3, F5–7) (F02) |
| C06 | 2023-01-28 21:10, 13.7 h | all 15 | D077 A1 (0.99) | zero fill right after the B hold (R3) |
| C07 | 2023-02-10 08:20, 42 h | F6 | D079 G3 (0.98) → F057 A3 | feeder outage + synthetic ramp |
| C08 | 2023-04-23 | L, B, F | K003/K011/K019 A4 (0.70 each) | missing hour, Morocco → GMT+1 (R14 only) |
| C09 | 2023-07-16 14:50, 16.2 h | B, F zeros; L linear | D096 A1 (0.93) → F086 A2 (1.00) | acquisition failure, not G1 (F03) |
| C10 | 2023-10-29 | L, B, F | K004/K012 A4 (0.98), K020 A4 (0.83) | European fall-back (F's profile fit 0.85, below the R15 guard) |
| C11 | 2023-12-16 | B1 → B2 | T000 G5 (0.68) | conserved transfer, κ = 0.07 |
| C12 | 2024-03-31 09:10, 45.8 h | B, F, L3–5 zero; L1/L2 held | F144 A2 → D117 A1 (1.00) → F145 A2 → D118 G4 (0.96) | hold → zero, with held and zeroed zones side by side; last item is a model limitation (F25) |
| C13 | 2024-04-14 | L, B, F | K007/K015/K023 A4 (0.70 each) | missing hour (R14 only) |
| new | 2022-09-26 08:20, 0.8 h | L1–L5 | D048 G2 (0.99) | the only city-outage candidate (F18) |
| new | 2024-03-31 | B | K014 N (0.60) | +60 profile shift with no missing hour, during Ramadan |

## 8. Detector and end model (NB3; `results/detector_v1/`, `results/end_model_v1/`)

**Reference run:** local, LightGBM 4.6.0, with the structural-zero fix (D51, D52), 2026-11-08, 19.8 min. Earlier runs are superseded: the local sklearn-fallback run (a9ec65a) and the Colab LightGBM run before the fix (21e6695). Their numbers are recorded in the research log (session 4) and must not be cited.

**Predictors** (`predictor_metrics.csv`; MAE of ρ on rule-clean steps, out of sample):

| System | Residual | All | Jul 2023 + |
|---|---|---|---|
| south | forecast | 0.0288 | 0.0278 |
| south | nowcast (guide eq. 13) | 0.0292 | 0.0282 |
| south | STL (non-robust) | 0.0594 | 0.0589 |
| south | ρ̂ = 1 (expected value) | 0.1835 | 0.1796 |
| Marrakech | forecast | 0.1077 | 0.0921 |
| Marrakech | nowcast | 0.1077 | 0.0925 |
| Marrakech | ρ̂ = 1 | 0.2755 | 0.2673 |

Residual lag-1 autocorrelation (median over southern zones; `ljung_box.csv`): forecast 0.179, nowcast 0.196. Ljung–Box Q (median): forecast 2,813 at lag 1 and 11,205 at lag 144; nowcast 3,358 and 14,038.

**MODWT group delays** (steps): W1 4, W2 11, W3 25, W4 53, V4 43. Spill half-width 53 steps.

**Structural zeros of the hierarchy** (`structural_zeros.csv`, raw band, LightGBM forecast residual; F35, D51):
- share of steps where a zone's v is exactly 0: Boujdour 0.281–0.365 (B1 0.365), Laâyoune 0.124–0.240, Foum El Oued 0.091–0.203;
- share where a city's u is exactly 0: Boujdour 0.085, Foum El Oued 0.129, Laâyoune 0.188;
- B1, 16–18 Mar 2024, V4 band: B1 is the city median on up to 52.3 % of the trailing window; the old scale (zeros included) has MAD = 0 and score 14,940; the fixed score is 2.1;
- zone-steps with a collapsed old V4 scale (MAD < 1e-4): 925 of 1,257,663; none in the other bands.

**Hierarchy consistency** (`hierarchy_consistency*.csv`; 206 southern items with a defined expected level, 11 warm-up items excluded):

| Residual | All | g (n = 9) | u (n = 40) | v (n = 157) |
|---|---|---|---|---|
| forecast | 0.714 | 0.444 | 0.550 | 0.771 |
| nowcast | 0.694 | 0.444 | 0.450 | 0.771 |
| STL | 0.621 | 0.444 | 0.325 | 0.707 |

By kind:

| Kind | Expected level | n | Forecast | Nowcast | STL |
|---|---|---|---|---|---|
| dead | g | 3 | 1.000 | 1.000 | 1.000 |
| dead | v | 71 | 0.915 | 0.915 | 0.873 |
| fill | g | 6 | 0.167 | 0.167 | 0.167 |
| fill | u | 40 | 0.550 | 0.450 | 0.325 |
| fill | v | 86 | 0.651 | 0.651 | 0.570 |

**Region score g at the logger events** (raw band, maximum over the item; forecast / nowcast): C06 218.0 / 232.6; C09 230.0 / 240.4; C12 175.6 / 177.1. For C05's multi-city fill item: 86.1 / 90.7.

**Threshold:** γ = 25.51 (south) and 16.85 (Marrakech), from 1,128,259 of 1,256,385 southern and 30,270 of 35,040 Marrakech zone-steps counted as rule-negative. History: the first, unaligned version gave γ = 103.79 (south); the aligned version before the structural-zero fix gave 37.24 (sklearn) and 33.35 (LightGBM).

**Detector recall of rule items** (share with Z > γ somewhere in the item; `detector_recall_of_rule_items.csv`):

| System | Label | Items | Recall | Median score |
|---|---|---|---|---|
| south | A1 | 3 | 1.000 | 566 |
| south | A2 | 57 | 0.789 | 49 |
| south | A3 | 88 | 0.534 | 56 |
| south | G2 | 1 | 0 (in the warm-up) | n/a |
| south | G3 | 18 | 1.000 | 139 |
| south | G4 | 56 | 0.946 | 101 |
| south | N (fill) | 3 | 1.000 | 134 |
| Marrakech | A3 | 7 | 0.000 | 5 |
| Marrakech | G3 | 35 | 0.086 | 10 |
| Marrakech | G4 | 13 | 0.077 | 12 |

**Detector-only candidates** (`detector_items.csv`, `detector_only_nature.csv`):
- 290 in total: 283 south, 7 Marrakech.
- Zones: 248 single-zone, 29 two-zone, 4 three-zone, 1 four-zone, 3 five-zone, 3 six-zone, 1 seven-zone, 1 fifteen-zone.
- Duration quantiles (10 / 50 / 90 %): 0.5 / 1.33 / 5.67 h. Highest score 276.7 (L2, 2 Nov 2023, surge).

| System | Nature | n | Median h | Median ρ | Multi-zone |
|---|---|---|---|---|---|
| south | other | 139 | 1.00 | 0.90 | 35 |
| south | surge | 111 | 2.83 | 1.74 | 0 |
| south | partial drop | 33 | 1.83 | 0.45 | 2 |
| Marrakech | other | 4 | 1.75 | 0.97 | 2 |
| Marrakech | surge | 3 | 2.00 | 1.63 | 3 |

End-model label of the candidates: N 270 ("no typed class fits"), A3 13, G4 5, A2 1, G3 1.

**Normal windows:** 300. South 250: 189 single-zone, 19 Boujdour-wide, 18 Laâyoune-wide, 19 Foum-El-Oued-wide, 5 all-zone. Marrakech: 50 single-zone.

**End model** (`end_model_metrics.csv`; out of fold, GroupKFold 5 by episode; 43 features; LightGBM):

| Variant | Agreement with the label model on 281 rule items | Normal windows predicted N | Soft CE (rule) |
|---|---|---|---|
| GBDT, all features | 0.947 | 1.000 | 0.300 |
| GBDT, no detector features | 0.957 | 1.000 | 0.300 |
| GBDT, no episode features | 0.943 | 1.000 | 0.309 |
| GBDT, detector features only | 0.541 | 0.970 | 1.570 |
| MLP, all features | 0.900 | 0.997 | 0.369 |

Per class (GBDT, all features): A1 3/3, A2 57/57, A3 95/95, G2 0/1 (→ G4), G3 45/53 (8 → G4), G4 66/69 (3 → G3), N (vote-less fills) 0/3 (they go to A3).

**Fusion** (β = 0.5; end-model abstention on low-support classes A1, G1, G2, affecting 4 items):
- 3 of 281 rule labels change, all N → A3: the vote-less single-zone linear fills on L2 and L3 (24 Dec 2023, p = 0.979 and 0.987) and L1 (6 Apr 2024, p = 0.944).
- Final rule-item labels (`p_type.csv`): A3 98, G4 69, A2 57, G3 53, A1 3, G2 1.
- The C12 tail item on L1 (2 Apr 2024 06:10) stays G4 after fusion (p = 0.83); the end model alone says G3. Episode features do not resolve F25.

**Superseded for the south by NB4 (D61):** the paper's main detector is now the TCN-GAT graph detector with tuned event formation. NB4 §8b writes the south catalogue it produces to `results/main_detector/`. The numbers above describe the LightGBM detector at NB3's event formation (w 1, q 99.5, gap 1). Marrakech keeps them.

## 8b. NB4 development selection (`results/benchmark_v1/dev/`, `dev_selection.json`; development seeds 100–104, *not test results*)

Scoring area: rule-based, the same for every detector (D60). "Every alarm counts" F1, eq. 17, both periods pooled.

**Predictors, real-data MAE** (clean steps):
- mean(LightGBM, TCN-GAT) **0.02821**
- mean(LightGBM, TCN) 0.02840
- LightGBM 0.02879
- LightGBM + learned-graph correction 0.02879
- LightGBM + TCN correction 0.02879
- TCN-GAT 0.02945
- TCN 0.02986

**Detector alone, each at its best event formation** (w = smoothing steps, q = threshold percentile, gap = merge gap):

| Detector | w, q, gap | F1 | Precision | Recall | Zone-strict F1 | U_SHOCK recall | U_PARTIAL recall | Real-data alarms | F1 at NB3's setting |
|---|---|---|---|---|---|---|---|---|---|
| **TCN-GAT, hierarchy, multi-scale (main)** | 24, 99.9, 12 | **0.786** | **0.866** | **0.729** | **0.755** | 0.104 | 0.236 | 70 | 0.649 |
| mean(LightGBM, TCN-GAT) | 48, 99.8, 12 | 0.771 | 0.861 | 0.703 | 0.729 | 0.042 | 0.209 | 44 | 0.672 |
| LightGBM + learned-graph correction | 24, 99.8, 6 | 0.760 | 0.826 | 0.714 | 0.732 | 0.124 | 0.255 | 56 | 0.683 |
| LightGBM forecast | 24, 99.8, 6 | 0.759 | 0.828 | 0.710 | 0.731 | 0.119 | 0.262 | 58 | 0.681 |
| STL + MAD | 24, 99.8, 12 | 0.717 | 0.846 | 0.628 | 0.680 | 0.159 | 0.328 | 86 | 0.591 |
| LOF | 24, 99.8, 12 | 0.648 | 0.726 | 0.621 | 0.615 | 0.153 | 0.455 | 148 | 0.464 |
| Isolation Forest | 3, 99.5, 3 | 0.473 | 0.412 | 0.599 | 0.419 | 0.050 | 0.086 | 416 | 0.384 |

**Further development results:**
- **Full method (rules + detector-only candidates) at the selected settings:** TCN-GAT 0.863, mean 0.854, hybrid 0.850, LightGBM 0.849. The rules alone score F1 0.888 (precision 1.000, recall 0.798).
- **Real-data alarms at NB3's setting:** LightGBM 283, TCN-GAT 444, mean 350, STL 475, Isolation Forest 480, LOF 858.
- **U_SHOCK recall at NB3's setting, detector alone:** TCN-GAT 0.609, LightGBM 0.439, STL 0.776, LOF 0.473.
- **Step-wise AUC-PR** (no smoothing): STL + MAD 0.785, LightGBM 0.649, the hybrid 0.646, mean 0.582, TCN-GAT 0.553, LOF 0.446, Isolation Forest 0.269.
- **Per cell:** TCN-GAT beats LightGBM alone in all 10 dataset × period cells, by 0.014 to 0.042.

## 9. NB4 test results: the injection benchmark (`results/benchmark_v1/`; test seeds 0–9)

**Run** (`summary.json`):
- Colab, CUDA GPU, LightGBM 4.6.0, torch 2.14.1+cu130.
- Models loaded from `results/benchmark_v1/models/`: LightGBM, TCN, TCN-GAT and the two hybrids. The main detector and the event formations come from `dev_selection.json`.
- 30 datasets: 1 %, 3 % and 7 % of clean zone-time × seeds 0–9.
- 8,526 injected events: A1 1,127, G1 930, A2 927, U_SHOCK 926, G4 926, G3 923, A3 923, U_PARTIAL 923, G2 921.
- The run resumed once after a disconnect (61 min in the last session). All run files were written on 9 Nov 2026, 21:04–23:22.
- South panel: 88,890 steps × 15 zones. Clean share of zone-steps: 0.819 overall, 0.770 in the train period, 0.863 in the test period.

**Conventions:** test period (Jul 2023 – May 2024); mean ± sd over 10 seeds; event F1 = eq. 17 (time overlap); every alarm counts unless stated otherwise. Order of rates: 1 % / 3 % / 7 %.

### 9.1 Detection (Table 5, Fig 9; `table5_detection.csv`)

| Method | Event formation (w, q, gap) | F1 1 % | F1 3 % | F1 7 % | F1, own background excluded | Zone-strict F1 | AUC-PR | Real-data alarms |
|---|---|---|---|---|---|---|---|---|
| **ours (rules + main detector)** | 24, 99.9, 12 | 0.721 ± 0.047 | 0.876 ± 0.008 | **0.906 ± 0.008** | **0.896 / 0.905 / 0.908** | 0.628 / 0.778 / 0.811 | 0.898 / 0.935 / 0.922 | 70 detector-only |
| rules only (rule engine v1) | — | **0.863 ± 0.032** | **0.879 ± 0.013** | 0.896 ± 0.009 | 0.863 / 0.879 / 0.896 | **0.863 / 0.872 / 0.876** | 0.853 / 0.900 / 0.888 | — |
| **TCN-GAT, hierarchy, multi-scale (main)** | 24, 99.9, 12 | 0.644 ± 0.067 | **0.813 ± 0.020** | **0.854 ± 0.011** | 0.817 / 0.842 / 0.848 | 0.615 / 0.783 / 0.805 | 0.547 / 0.598 / 0.565 | 191 |
| mean(LightGBM, TCN-GAT) | 48, 99.8, 12 | **0.655 ± 0.050** | 0.773 ± 0.024 | 0.843 ± 0.015 | 0.786 / 0.810 / 0.840 | 0.626 / 0.738 / 0.779 | 0.521 / 0.592 / 0.543 | 131 |
| LightGBM + learned-graph correction | 24, 99.8, 6 | 0.627 ± 0.051 | 0.765 ± 0.024 | 0.827 ± 0.017 | 0.791 / 0.819 / 0.829 | 0.616 / 0.740 / 0.775 | 0.595 / 0.676 / 0.633 | 150 |
| LightGBM + TCN correction (no graph) | main's | 0.645 ± 0.038 | 0.752 ± 0.026 | 0.790 ± 0.021 | 0.736 / 0.780 / 0.792 | 0.632 / 0.728 / 0.739 | 0.593 / 0.671 / 0.627 | 93 |
| LightGBM forecast | 24, 99.8, 6 | 0.623 ± 0.055 | 0.765 ± 0.022 | 0.827 ± 0.015 | 0.793 / 0.817 / 0.830 | 0.611 / 0.739 / 0.774 | 0.592 / 0.678 / 0.633 | 152 |
| STL + MAD | 24, 99.8, 12 | 0.625 ± 0.043 | 0.734 ± 0.026 | 0.771 ± 0.024 | 0.741 / 0.763 / 0.763 | 0.610 / 0.706 / 0.714 | 0.577 / 0.721 / 0.723 | 178 |
| LOF | 24, 99.8, 12 | 0.570 ± 0.035 | 0.720 ± 0.029 | 0.698 ± 0.108 | 0.714 / 0.756 / 0.697 | 0.549 / 0.692 / 0.638 | 0.568 / 0.653 / 0.591 | 263 |
| Isolation Forest | 3, 99.5, 3 | 0.211 ± 0.078 | 0.462 ± 0.043 | 0.605 ± 0.099 | 0.386 / 0.625 / 0.649 | 0.167 / 0.416 / 0.531 | 0.103 / 0.268 / 0.392 | 457 |

- **Precision / recall of the main detector:** 0.583 / 0.892 / 0.976 and 0.730 / 0.748 / 0.759. Ours: precision 0.646 / 0.921 / 0.984, recall 0.824 / 0.834 / 0.839. Rules: precision 1.000, recall 0.760 / 0.785 / 0.812.
- **"Real-data alarms":** all alarms of the detector alone on the uninjected south data, including those on real rule states. This differs from the 70 detector-only candidates of §8b and §9.8, which exclude alarms overlapping rule items.
- **Median onset error** (minutes, zone-matched): main 168 / 165 / 140; LightGBM 110 / 118 / 100; STL + MAD 70 / 70 / 60; LOF 20 / 28 / 45; Isolation Forest 10; flat residual 82 / 90 / 80. Rules and ours: 0.

**Wilcoxon signed-rank, 10 seeds** (`table5_wilcoxon.csv`; ours vs rules from `runs/`):
- **Main detector vs each other detector:**
  - 3 %: p = 0.002 for all seven;
  - 7 %: p = 0.020 (average), 0.004 (graph hybrid), 0.002 (the rest);
  - 1 %: p = 0.56 (average), 0.32 (graph hybrid), 1.0 (no-graph hybrid), 0.16 (LightGBM), 0.49 (STL + MAD), 0.010 (LOF), 0.002 (Isolation Forest).
- **Ours vs rules:**
  - strict F1: p = 0.002 (rules better), 0.63, 0.002 (ours better, 10/10 seeds);
  - F1 with own background excluded: ours better at every rate, 10/10 seeds, p = 0.002;
  - recall: ours higher at every rate, 10/10 seeds;
  - zone-strict F1: rules better at every rate, p = 0.002.
- **Predicted events per test period, ours vs rules vs injected:** 1 % 66.8 / 31.0 / 40.8 (ours 40.9 with background excluded); 3 % 132.5 / 90.2 / 116.9; 7 % 328.2 / 250.3 / 321.9.
- **Detector-only candidates in scope, test period:** 35.8 / 42.3 / 77.9 per dataset. Share that shares a zone with an injected event: 0.084 / 0.175 / 0.182. Share that overlaps one in time only, on other zones: 0.254 / 0.584 / 0.751. Share that overlaps none: 0.662 / 0.241 / 0.067 (F44).

### 9.2 Ablations (Table 7b, 3 %; Table 5 for the other rates)

| Variant (at the main detector's event formation unless stated) | F1 1 % | F1 3 % | F1 7 % | AUC-PR 3 % | U_SHOCK recall 3 % | U_PARTIAL recall 3 % |
|---|---|---|---|---|---|---|
| main: TCN-GAT, hierarchy, multi-scale | 0.644 | 0.813 | 0.854 | 0.598 | 0.212 | 0.207 |
| single scale (raw band) | 0.595 | 0.772 | 0.853 | 0.626 | 0.111 | 0.231 |
| no hierarchy (flat residual) | **0.675** | 0.796 | **0.856** | **0.811** | 0.053 | 0.222 |
| TCN, no graph (raw, hierarchy) | 0.612 | 0.775 | **0.864** | 0.668 | 0.196 | 0.245 |
| TCN-GAT (raw, hierarchy) | 0.595 | 0.772 | 0.853 | 0.626 | 0.111 | 0.231 |
| LGB nowcast (raw, hierarchy) | 0.615 | 0.715 | 0.770 | 0.704 | 0.000 | 0.066 |
| TCN-GAT, NB3 event formation (1, 99.5, 1) | 0.365 | 0.670 | 0.835 | 0.595 | **0.774** | **0.395** |
| LightGBM, NB3 event formation | 0.451 | 0.705 | 0.833 | 0.695 | 0.591 | 0.320 |

- "single scale (raw band)" and "TCN-GAT (raw, hierarchy)" are the same detector once the main detector is the TCN-GAT, so their rows are identical.
- The no-graph multi-scale row (`TCN, no graph, hierarchy, multi-scale`) is in §9.2b.

### 9.2b No-graph ablation of the main detector (`results/benchmark_v1/graph_ablation/`, D62)
- **Reproduction:** the main detector recomputed on CPU equals the Colab rows in 30/30 runs (F1 and F1 with own background excluded; max abs difference 0). Real-data alarms 191.
- **Development (seeds 100–104):**
  - no-graph TCN F1 alone 0.786 at the main setting (TCN-GAT 0.786);
  - 0.794 at its own best setting (w 48, q 99.9, gap 12);
  - full method 0.866 (TCN-GAT 0.863).

| Detector | Setting | F1 1 % | F1 3 % | F1 7 % | Own background excluded | Zone-strict F1 | AUC-PR | Real-data alarms | U_SHOCK recall | Onset error (min) |
|---|---|---|---|---|---|---|---|---|---|---|
| TCN-GAT, hierarchy, multi-scale (main) | 24, 99.9, 12 | 0.644 ± 0.067 | 0.813 ± 0.020 | 0.854 ± 0.011 | 0.817 / 0.842 / 0.848 | 0.615 / 0.783 / 0.805 | 0.547 / 0.598 / 0.565 | 191 | 0.302 / 0.212 / 0.058 | 168 / 165 / 140 |
| TCN, no graph, hierarchy, multi-scale | 24, 99.9, 12 | **0.671 ± 0.048** | **0.817 ± 0.020** | 0.857 ± 0.009 | 0.826 / 0.847 / 0.852 | 0.641 / 0.789 / 0.806 | 0.540 / 0.598 / 0.568 | 202 | 0.277 / 0.255 / 0.076 | 158 / 150 / 135 |
| the same, own tuned event formation | 48, 99.9, 12 | **0.707 ± 0.040** | 0.801 ± 0.019 | **0.861 ± 0.012** | 0.823 / 0.829 / 0.856 | 0.675 / 0.765 / 0.800 | 0.505 / 0.574 / 0.532 | 170 | 0.253 / 0.123 / 0.028 | 238 / 240 / 230 |

**Wilcoxon, main vs no graph** (10 seeds; `wilcoxon_graph_ablation.csv`; the number of seeds the main detector wins in brackets):
- **Same setting:**
  - F1: p = 0.037 (2/10), 0.13 (3/10), 0.064 (3/10);
  - own background excluded: p = 0.50, 0.084, 0.021 (2/10);
  - AUC-PR: p = 0.56, 0.85, 0.49.
- **Own tuning:**
  - F1: p = 0.004 (1/10), 0.020 (main better, 9/10), 0.027 (2/10);
  - AUC-PR: main better at every rate (p = 0.010, 0.010, 0.002).

### 9.3 Recall by type (`detection_recall_by_type.csv`, zone-strict, test period)
- **Rules only:** A1, A2, A3, G1, G3, G4 1.000; G2 0.900 / 0.929 / 0.939; U_SHOCK 0, U_PARTIAL 0 / 0.020 / 0.
- **Ours:** every typed class 1.000 (G2 0.998 at 7 %); U_SHOCK 0.302 / 0.212 / 0.052; U_PARTIAL 0.180 / 0.207 / 0.220.
- **Main detector alone:**
  - A1 1.000 / 1.000 / 0.997, A2 0.888 / 0.788 / 0.726, A3 0.252 / 0.289 / 0.255;
  - G1 1.000, G2 1.000 / 0.994 / 0.998, G3 1.000 / 1.000 / 0.997, G4 0.975 / 1.000 / 0.987.
- **LightGBM alone:** A3 0.148 / 0.215 / 0.184; G3 0.975 / 0.947 / 0.908; G4 0.926 / 0.915 / 0.938; U_SHOCK 0.130 / 0.163 / 0.045.

### 9.4 Attribution (Table 6, Table 7a, Figs 10–11; `table6_attribution.csv`)

| Labeller | Macro-F1 1 % | 3 % | 7 % | ECE 1 % | 3 % | 7 % |
|---|---|---|---|---|---|---|
| majority vote (rules) | 0.940 ± 0.054 | **0.921 ± 0.029** | **0.913 ± 0.015** | — | — | — |
| label model q | 0.934 ± 0.055 | 0.914 ± 0.029 | 0.900 ± 0.017 | 0.068 | 0.089 | 0.099 |
| end model f, no detector features | 0.875 ± 0.090 | 0.899 ± 0.040 | 0.898 ± 0.019 | 0.124 | 0.076 | 0.069 |
| end model f, all features | 0.845 ± 0.071 | 0.874 ± 0.025 | 0.902 ± 0.018 | 0.107 | 0.078 | 0.061 |
| fusion, no detector features (β*) | **0.944 ± 0.037** | 0.918 ± 0.022 | 0.905 ± 0.020 | 0.071 | 0.090 | 0.098 |
| **fusion (β*, D50 abstention)** | **0.944 ± 0.037** | 0.919 ± 0.023 | 0.906 ± 0.019 | 0.074 | 0.090 | 0.100 |
| fusion (β*, no abstention) | 0.936 ± 0.051 | 0.920 ± 0.026 | 0.910 ± 0.020 | 0.068 | 0.084 | 0.074 |

- **β\*** (train period, by macro-F1): with abstention 0.7 / 0.6 / 0.6; without 0.9 / 0.7 / 0.3.
- **Per-class F1, fusion at 3 %:** A1 0.789, A2 0.977, A3 0.993, G1 0.862, G2 0.937, G3 0.933, G4 0.945.
- **ECE:** Table 6 averages the per-seed ECE. Fig 11 pools the seeds at 3 %: label model 0.074, end model 0.062, fusion 0.078.
- **Confusion, fusion at 3 %, test, pooled** (`fig10_confusion_fused.csv`; rows = injected type):
  - A1 105 correct of 160 (→ G1 44, → G2 6, → N 5);
  - A2 109/113 (→ N 4); A3 117/119 (→ A2 2);
  - G1 133/133; G2 126/137 (→ N 11); G3 108/123 (→ G4 15); G4 126/126.
- **A1 → G1 mechanism** (3 %, both periods, label-model arg max, 271 detected A1): multi-city zero gaps → G1 in 40/128 (two cities) and 29/100 (three cities); zero fills after a city fill → G2 in 13/25. Label-model A1 accuracy 0.697; without the simultaneity family 0.834. G1 accuracy 1.000 either way.
- **End to end** (typed test events, detected and correctly typed, `end_to_end.csv`): 0.945 ± 0.038 / 0.907 ± 0.026 / 0.896 ± 0.020. Detected share 1.000 / 1.000 / 0.9996.
- **Table 7a (3 %):** majority vote 0.921; label model 0.914 (ECE 0.089); fusion without detector features 0.918 (0.090); fusion with D50 abstention 0.919 (0.090).

### 9.5 Rule-family ablation (Table 7c; 3 %, label model macro-F1, test)
All families 0.914 ± 0.029. Without:
- simultaneity **0.941 ± 0.047**;
- city 0.922;
- conservation 0.915;
- single-zone 0.915;
- restoration 0.902;
- hold 0.893;
- calendar **0.778**;
- interpolation **0.724 ± 0.110**.

### 9.6 Threshold sensitivity (Table 7d; 3 %, seeds 0–2, test)

| Setting | Rules F1 | Rules recall | U_PARTIAL recall | G3 recall | G4 recall | A3 recall | Label model macro-F1 |
|---|---|---|---|---|---|---|---|
| baseline (ε 0.05, hold 6, τ 10 min) | 0.891 | 0.803 | 0.042 | 1.000 | 1.000 | 1.000 | 0.906 |
| ε 0.02 | 0.880 | 0.786 | 0.000 | 0.946 | 0.944 | 1.000 | **0.819** |
| ε 0.10 | 0.881 | 0.812 | **0.162** | 1.000 | 1.000 | 1.000 | 0.915 |
| hold 4 | **0.765** | 0.803 | 0.042 | 1.000 | 1.000 | 1.000 | 0.906 |
| hold 12 | 0.880 | 0.786 | 0.042 | 1.000 | 1.000 | 0.820 | 0.885 |
| τ 0 min | 0.891 | 0.803 | 0.042 | 1.000 | 1.000 | 1.000 | 0.905 |
| τ 20 min | 0.891 | 0.803 | 0.042 | 1.000 | 1.000 | 1.000 | 0.904 |

### 9.7 Hard negatives (`hard_negatives.csv`; real data, detector alone, flag rate relative to ordinary weekdays)
- **Main detector** (base rate 0.0011): weekend 1.70, Eid 2.56, national holiday 0.99, Ramadan 0.73.
- **LightGBM** (0.0018): weekend 1.17, Ramadan 2.15, Eid 0.34, national holiday 0.
- **Average** (0.0020): weekend 1.28, Ramadan 1.35, Eid 1.39, national holiday 0.
- **Zone-steps per day type:** ordinary weekday 746,257; weekend 288,425; Ramadan 116,548; national holiday 29,970; Eid 11,280.

### 9.8 Predictors and the learned graph (real data; `predictor_comparison.csv`, `hierarchy_consistency_by_predictor.csv`, `learned_cross_city_edges*.csv`)
- **MAE, all periods (test period in brackets):**
  - mean(LightGBM, TCN-GAT) 0.0282 (0.0278);
  - LightGBM forecast 0.0288 (0.0278), equal to both hybrids;
  - LightGBM nowcast 0.0292 (0.0282);
  - TCN-GAT 0.0294 (0.0296);
  - TCN 0.0299 (0.0289).
  - The same models as §8b (loaded, not retrained).
- **RMSE:** the neural predictors and the average have lower RMSE (0.0496–0.0498) than LightGBM (0.0541): fewer large errors, more small ones.
- **Rule items at the expected hierarchy level** (206): TCN 0.767, TCN-GAT 0.733, LightGBM 0.714, average 0.714, graph hybrid 0.709, nowcast 0.694, no-graph hybrid 0.689.
  - Multi-city dead items at the region: LightGBM and the hybrids 3/3, neural residuals 2/3.
  - Single-zone dead items at the zone: 0.915 for all.
  - Fills at the zone: TCN 0.767, TCN-GAT 0.733, LightGBM 0.651.
- **Learned graph (E20):**
  - Mean attention per edge: same city 0.115, cross-city 0.085.
  - Strongest cross-city edges: B3 ← L2 0.191, B2 ← L2 0.190, B2 ← L4 0.179, B3 ← F4 0.167, B1 ← F2 0.162.
  - Boujdour (3 zones) reads most from other cities.

### 9.9 Real data with the main detector (NB4 §8b; `results/main_detector/`)
- **Setting:** γ = 24.87 (w 24, q 99.9, gap 12); β = 0.6 (3 %, with abstention).
- **Candidates:** 70 detector-only candidates, against 283 for NB3's south detector; 66 overlap an NB3 candidate.
  - Shape: 61 single-zone, 7 two-zone, 1 three-zone, 1 spanning all 15 zones.
  - Where: Laâyoune 51, Boujdour 13, Foum El Oued 5, all three cities 1.
  - Duration: median 3.4 h (IQR 2.2–5.0).
  - When: 49 in the test period, 21 in the train period.
  - NB3 nature: other 41, surge 17, partial drop 8, not in NB3 4.
- **Fused labels of the candidates:** N 58, A3 7, G4 3, A2 1, A1 1.
- **Rule items (south):** 226. Labels A3 91, G4 57, A2 57, G3 17, A1 3, G2 1. One change from NB3: 6 Aug 2023 07:00–13:30, B2, G3 → G4 (p 0.556 vs 0.443).

## 10. NB5 downstream test (`results/downstream_v1/`; southern system; test period 1 Jan – 24 May 2024)

**Setup:** D64–D66. Labels: the main-detector catalogue on the real data; the label-model arg max on injected data. Injected datasets: NB4's 3 % seeds 0–2 and 7 % seed 0. LightGBM 4.6.0, local CPU, 17.5 min.
- Flagged zone-steps (dead, hold or linear fill in a qualifying run): 1.22 % of the south panel.
- Steps imputed as artefacts: 14,437 zone-steps. Steps kept as grid events: 1,764 zone-steps.
- Scored test zone-steps: 305,257, of which 24,744 had a flagged state in the preceding 2 days.

### 10.1 Outage statistics
- **Real data** (`outage_real.csv`):
  - naive (every dead state) 1,220.5 zone-h in 117 runs; typed (G items) 294.0 zone-h in 79 runs; **ratio 4.15**.
  - Dead zone-hours by label: A1 926.5, G3 201.8, G4 88.0, G2 4.2.
  - By city (naive / typed zone-h): Foum El Oued 728.7 / 220.0, Laâyoune 252.0 / 52.2, Boujdour 239.8 / 21.8.
- **Injected data** (`outage_injected.csv`, `injected/*_outage.csv`; outage zone-hours / truth):
  - naive 1.49, 2.39, 1.77, 1.90 (mean **1.89**);
  - typed 1.14, 1.76, 1.29, 1.25 (mean **1.36**);
  - S1 0.
  - Truth 2,478.8 / 1,595.8 / 2,346.3 / 4,503.8 zone-h.
  - Typed outage zone-steps: precision 0.567–0.872, recall 0.997–0.999.

### 10.2 Forecasting (Table 8, Fig 12; `table8_forecasting.csv`, `table8_dm.csv`; MASE, eq. 19)

| Data | Model | Horizon | Subset | S0 | S1 | S2 | S3 |
|---|---|---|---|---|---|---|---|
| real | LightGBM | 1 h | after anomaly | 0.656 | 0.661 | **0.613** | — |
| real | LightGBM | 1 h | all | 0.654 | 0.657 | 0.654 | — |
| real | LightGBM | 1 day | after anomaly | 1.501 | 1.233 | **1.061** | — |
| real | LightGBM | 1 day | all | 1.140 | 1.115 | **1.102** | — |
| real | naive | 1 h | after anomaly | 1.081 | 1.059 | **1.052** | — |
| real | naive | 1 day | after anomaly | 2.220 | 1.553 | **1.278** | — |
| injected (mean of 4) | LightGBM | 1 h | after anomaly | 0.708 | 0.640 | 0.625 | **0.618** |
| injected | LightGBM | 1 h | all | 0.652 | 0.622 | 0.613 | **0.608** |
| injected | LightGBM | 1 day | after anomaly | 1.293 | 1.107 | 1.056 | **1.046** |
| injected | LightGBM | 1 day | all | 1.170 | 1.069 | 1.043 | **1.039** |
| injected | naive | 1 h | all | 0.913 | **0.881** | 0.891 | 0.882 |
| injected | naive | 1 day | all | 1.401 | **1.155** | 1.236 | 1.199 |

- **MAE (A), real data, LightGBM, day-ahead after an anomaly:** 10.53 / 9.63 / 8.89. On all steps: 7.86 / 7.77 / 7.71.
- **Real-data Diebold–Mariano tests**, LightGBM, p for S1 vs S2 and S0 vs S2:
  - 1 h after anomaly < 0.0001 and 0.0001;
  - 1 h all 0.019 and 0.86;
  - 1 day after anomaly 0.22 and 0.23;
  - 1 day all 0.25 and 0.21.
  - DM statistics are positive (S2 better) in every row.
- **Injected data, LightGBM, datasets with S2 significantly better (p < 0.05), out of 4:**
  - vs S0: 4 in every row;
  - vs S1: 1 h all 4, 1 h after 3, 1 day 2;
  - S1 is never significantly better than S2.
  - S2 closes 62–86 % of the S1-to-S3 gap.
- **Injected data, naive reference:** S1 is significantly better than S2 in 4/4 datasets at 1 h and 2/4 at 1 day (F54).
