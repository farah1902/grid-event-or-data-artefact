# Results summary — numbers to cite

This is the single source of truth for numbers. Every value below comes from a file in `results/`, named in each
section. Status: as of 2026-11-08 (rule engine v1 + label model). **No result here has been validated against
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
