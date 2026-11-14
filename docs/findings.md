# Findings register

Every empirical finding so far, numbered for citation (F01, F02, …). Each gives the observation, the numbers,
where the evidence is (file or figure), how confident we are, and what it means for the paper. "Guide" means
`docs/research_guide.md`. Numbers come from the files named in each entry; when in doubt, re-run and update.

Confidence levels:
- **solid**: directly measured, mechanical.
- **strong**: measured, with a plausible but untested interpretation.
- **provisional**: depends on unvalidated labels or thresholds.

---

## A. Data and acquisition artefacts

### F01 — A linear-interpolation artefact exists in the data (new; not in the guide) — *solid*
- **Observation:** stretches where a zone's series is a perfect straight line. The first difference is constant to machine precision; for example, in F1–F7 between 26 Jan 02:20 and 27 Jan 15:40 2023, the standard deviation of Δx is ≈ 1e-14.
- **Numbers:**
  - NB1 (≥ 6 collinear points, all cities): 275 runs in 102 groups, 48 groups touching ≥ 2 zones at once.
  - Rule engine v1 (Marrakech minimum 12 points, priority rules D16): 274 southern interpolation zone-runs, 0 in Marrakech.
  - Of the 155 v1 fill items, 85 are pure interpolation, 54 pure hold and 16 mixed. **Linear interpolation is the most common fill mechanism in this dataset, more common than holds.**
- **Evidence:** `results/figures/interp_runs.csv`, `results/catalogue_v1/zone_runs.csv`, Fig 3, E1b, E10.
- **Interpretation (strong):** this is the signature of a historian or export that retrieves values at regular intervals and linearly interpolates between archived points. During a communication loss, the straight line joins the last value before the gap to the first value after it. Holds (last value carried forward) and linear fills are then the same mechanism under two retrieval modes.
- **Paper:** a new artefact signature. It extends the typology: A2 becomes "simultaneous fill (hold or linear)" and A3 "single-zone fill". Contribution 1 should mention it.

### F02 — C05 (Jan 2023) involves all 15 southern zones, not 9 — *solid*
- F1–F3 and F5–F7 are linearly interpolated from 26 Jan 02:20 to 27 Jan 15:40/15:50, the same span as the F4 hold. With the L holds (from 01:20) and the B holds (from 02:10/02:20), every southern zone is filled.
- **Evidence:** Fig 3 (teal spans), episode EP056 (items F051, F052, D077).

### F03 — C09 (16 Jul 2023) is probably an acquisition failure, not a regional outage — *strong*
- **Guide:** "B and F dead, L normal → G1 candidate".
- **Data:**
  - B and F read exact zeros from 14:50 to 07:00.
  - **All 5 L zones are linearly interpolated from 15:30 to 06:50/07:00.** Laâyoune was not normal; its gap was filled with straight lines.
  - Zeros in two cities next to straight-line fill in the third is a mixed artefact state that the grid cannot produce (the R4 logic).
- **Overshoot:** π = 1.33 in v1. B's overshoot decays within about 3 h, but F stays 1.3–1.5× its expected value for hours before and after the event, so π is partly a baseline effect.
- **Label model:** the C09 dead item → A1 (q = 0.93), and the L fill → A2 (1.00).
- **Evidence:** E1, E1b, E14.
- **Paper:** the guide's only G1 candidate disappears. See F07.

### F04 — Clock artefacts: the logger follows European DST in autumn — *solid (dates), strong (interpretation)*
- **Repeated hour:** 02:00–02:50 is duplicated on 30 Oct 2022 and 29 Oct 2023 in L, B and F (6 duplicate stamps per city per date, 12 per city in total). Those are Europe's fall-back dates; Morocco's clock does not move then.
- **Missing hour:** stamps missing at 02:00 on 23 Apr 2023 and 14 Apr 2024 (6 steps each, per city). Those are Morocco's return to GMT+1 after Ramadan.
- **Profile shift δ\*** (sign convention D08: negative = after the date, behaviour is stamped earlier):

| Date | L | B | F |
|---|---|---|---|
| 30 Oct 2022 | −60 (corr 0.98) | −60 (0.98) | −60 (0.92) |
| 29 Oct 2023 | −120 (1.00) | −60 (0.98) | −60 (0.85: below the 0.9 fit guard) |

  The guide's "+50 to +60" is the same magnitude with the opposite sign.
- **New:** Boujdour on 31 Mar 2024 (Europe's spring-forward date) shows δ\* = +60 (corr 0.99), but **no missing hour**, during Ramadan. The label model calls it N (0.60). 31 Mar 2024 is also the day C12 starts.
- **No repeated hour at Morocco's switch to GMT** (19 Mar 2023, 10 Mar 2024): confirmed open question from the guide.
- **Evidence:** `results/figures/clock_offsets.csv`, Fig 5 and figS_clock_*, `results/event_catalogue_v0/timestamp_audit.csv`, items K000–K032.

### F05 — About 1 in 5 dead runs "restore" through a synthetic straight line — *solid*
- **Numbers:**
  - 25 of 117 southern dead zone-runs (21 %) are followed immediately by a linear-interpolation run in the same zone, between the last zero and the first real reading.
  - The guide's G3 events C02 (F4, 108 h), C04 (F1) and C07 (F6, 42 h) all end this way. Episode sequences: G3 → A3.
- **Consequence:**
  - Restoration features measured on that line are artefacts.
  - C02's restoration ratio was r = 0.22 ("comes back slowly") in v0. Measured after the line it is r = 1.01 with no ramp.
  - v1 measures restoration after the line (D22).
- **Paper:** a threat to H2 ("real outages restore with a ramp"). A ramp in this data can be an interpolation artefact. Report it.

### F06 — C01 is not a noise-floor outage — *solid*
- **Guide/v0:** L5, 23 Oct 2022 11:10, 22.3 h, η = 0.51, "noise floor".
- **v1:** zeros 08:10–09:40, then a straight line 09:40–11:10 (slope 3.0 A/step), then a straight line 11:20–18:30 (43 points at ≤ 5 % of expected, slope 0.11 A/step), then zeros (and some noise floor) 18:30 → 09:30 next day.
- **Label model sequence:** G4 (0.96) → A3 → A3 → G3 (0.84).
- **Evidence:** E10, episode EP020.

### F07 — No clean regional outage (G1) remains in the real data — *strong*
- R7 (the regional-outage rule) fires on **0** items. All 3 multi-city dead events come with hold or linear-fill evidence: C06 (R3), C09 (R21), C12 (R1, R3, R4). All three get A1 from the label model (0.93–1.00).
- **Consequence:** G1 cannot be learned or evaluated from real data. It must come from injection (NB4). Say so in the paper.

### F08 — Multi-zone linear fills cluster in the morning, inside R10's "planned work" window — *strong (observation), provisional (meaning)*
- In E9, most multi-zone interpolation items start between 08:00 and 10:30.
- **Caveat:** some G4 "planned work" events (one zone dead, 06:00–11:59, ≤ 6 h) may be data-side maintenance, not grid works. The label model trusts R10 as a defining rule (D33), so this is a known threat to G4 precision.

### F09 — A daily logger freeze in Laâyoune until April 2023 — *solid (pattern), strong (interpretation)*
- **Numbers:**
  - 218 episodes where ≥ 2 Laâyoune zones hold 3–5 identical points at the same time.
  - 120 of them start in the 08:00 hour, plus a secondary cluster around 21:00.
  - 186 days have exactly one. The regime stops in Apr 2023.
  - B and F show only 2 and 1 such episodes.
- **Interpretation:** a scheduled daily logger task (sync or upload) that freezes all channels for 30–50 min.
- These runs are below the 6-point hold threshold, so v1 does not vote on them (D18).
- **Evidence:** E11.

### F10 — Boujdour zone 2 repeats short values naturally — *solid*
- 334 runs of 3–5 identical points spread over the whole period. B2 is a small feeder (about 15 A) with coarse resolution. These are quantisation, not artefacts, which justifies a ≥ 6-point hold minimum.

### F11 — Boujdour reads whole amperes during frozen periods (from the guide, confirmed) — *solid*
- Held values such as 77.000, 12.000, 31.000 (C05) and 38.000, 51.000, 41.000 (C12) are integers, while normal B values are not. This hints at a separate encoding in the telemetry path during holds.

### F12 — δ\* is unreliable around Ramadan and on Marrakech gap dates — *solid*
- Without a fit-quality guard, R15 fired on 18 of 33 clock items. Profile correlations were 0.09–0.30 on Marrakech audit dates and 0.59–0.85 on Ramadan switch dates. Behaviour and clock change together (as the guide warned).
- With the guard (D21), R15 fires on 6.

### F13 — Foum El Oued structural decline (confirms the guide) — *solid*
- City total relative to Q3 2022: 0.76 (Q4 2022), 0.58 (Q1 2023), 0.61, 0.71, 0.69, **0.47 (Q1 2024)**, 0.51 (Q2 2024).
- Midday/evening ratio: 0.89 → 0.93 → 0.95 → 0.95 → 0.96 → 0.97 → 1.02 → 1.03. A rising ratio doesn't fit rooftop PV.
- **Evidence:** E7.

### F14 — Marrakech timestamp defects (confirms the guide) — *solid*
- 366 backward jumps (each day's 00:00 row sits after 23:30; probably a "24:00" reading stamped with the same date), 3 duplicated stamps (6 rows), and 4 missing runs (25 steps, 19 of them at the start).
- **Evidence:** E8, `timestamp_audit.csv`. (The southern cities each have 12 duplicated stamps and 2 missing runs of 6 steps, all on clock dates.)

### F15 — Marrakech "outages" are mostly noise-floor runs in zone 2 — *provisional*
- 48 Marrakech dead items, 43 of them with no exact zero (η = 0), all in M2 (median 30 kW, whole-kW values). Label model: 35 G3, 13 G4. M1 is never dead.
- **Caveat:** with whole-kW quantisation and a small feeder, readings of 0–1 kW against an expected 20+ kW may be genuine outages or low-load quantisation. Treat Marrakech G3/G4 counts as provisional; report the south separately.

---

## B. Rules (v1)

### F16 — Restoration overshoot (R5) carries almost no evidence — *strong*
- The label model learns a = 0.168 and b = 0.150 for R5 (π ≥ 1.15), so log(a/b) = 0.12. Every other rule has log(a/b) between 1.8 and 4.8.
- Dropping the restoration family (R5, R6) changes 0 labels.
- **Meaning:** cold-load-pickup overshoot does not separate grid events from artefacts in this data. Together with F05 and F03, **H2 is weak**. A paper claim based on restoration dynamics must be stated cautiously or tested by injection.
- **Evidence:** `results/labels_v1/rule_params.csv`, E12, E15.

### F17 — Rule coverage and conflicts (v1 on the real data) — *solid*
- **Items:** 327 (126 dead, 155 fill, 33 clock, 13 transfer), linked into 230 episodes; 38 episodes have ≥ 2 items.
- **Votes per rule:** R1 1, R2 12, R3 3, R4 3, R5 21, R6 84, R7 0, R8 1, R9 122, R10 69, R11 4, R12 44, R13 8, R14 6, R15 6, R16 1, R19 48, R20 48, R21 5.
- **Conflicting rule pairs** (incompatible labels on the same item, counted per item and pair): R9–R10 69 (by design: R10 refines R9), R21–R9/R10 6, R4–R5/R6/R9/R10 7, R3–R9/R10 2, R5–R21 1, R6–R21 3.
- **v0 → v1:** 70 of v0's 72 dead events have a v1 dead item with the same start. 2 were re-segmented (C01, and v0 event 53 on 21 Oct 2023). 56 v1 dead items are new: 43 Marrakech and 13 southern noise-floor runs.
- **Evidence:** `results/catalogue_v1/rule_summary.csv`, Fig 7, E9.

### F18 — A city outage candidate (G2) — *strong*
- On 26 Sep 2022 at 08:20, all 5 Laâyoune zones are dead for 50 min (η = 1.0), while Boujdour and Foum El Oued stay alive (median ratio 1.11). R8 fires, and the label model gives G2 = 0.99.
- This is the guide's "1 event, 0.8 h". It is the only G2.

### F19 — One conserved load transfer (G5) — *solid (measurement), strong (label)*
- Boujdour, 16 Dec 2023: zone 1 drops 31.9 A, zone 2 gains 33.0 A, κ = 0.07. It is the only transfer candidate with κ ≤ 0.3; the other 12 have κ between 0.72 and 4.15.
- Label model: G5 = 0.68. A single vote against a prior of 1/8 is honest uncertainty.
- **Evidence:** E2.

---

## C. Label model

### F20 — The guide's label-model equations cannot use single-label rules — *solid (mathematical)*
- With θ_r(y, l) = P(λ_r = l | y, fired) and a single possible output l, θ_r(y, l) = 1 for every y. The likelihood ignores the votes, so the posterior equals the prior.
- Every v1 rule emits one label, so abstention must be modelled (D28).

### F21 — The unconstrained Dawid–Skene model is not identifiable on these votes — *solid*
- **First attempt** (abstention modelled, gating by item kind only):
  - restart agreement as low as 19 %;
  - best solution: C06 and C12 → G3, every single-zone dead item → G4, all 13 transfers → N.
- **With feasibility, applicability, speaks-for and the π prior (D29–D31, D34)**, the guide-style full model still:
  - reaches only 63 % minimum restart agreement;
  - labels all 57 multi-zone fills N and all G4 as G3;
  - agrees with the constrained model on only 56.9 % of items.
- **Cause:** rules rarely co-fire (most items get 1–3 votes) and each emits one label, so EM regroups items by likelihood. The guide's identifiability argument ("most items get several votes") does not hold on the real data.

### F22 — The constrained (one-coin) model is stable and recovers its own parameters — *solid*
- **Restarts:** all 20 agree on 100 % of items.
- **Parameter recovery** (20 seeds, votes simulated from the fitted model on the same 327 items):

| Labeler | Accuracy | Macro-F1 | ECE | Brier |
|---|---|---|---|---|
| Constrained DS (ours) | 0.922 ± 0.021 | 0.872 ± 0.080 | 0.033 ± 0.012 | 0.124 ± 0.028 |
| Guide's full DS | 0.682 ± 0.058 | 0.493 ± 0.077 | 0.276 ± 0.065 | 0.577 ± 0.118 |
| Majority vote | 0.911 ± 0.017 | 0.843 ± 0.064 | n/a | n/a |

- **Caveat:** this tests identifiability and calibration under the model's own assumptions, not the rules.
- **Evidence:** `results/labels_v1/recovery_summary.csv`, `recovery_runs.csv`.

### F23 — Probabilistic labels on the real data — *provisional (no ground truth)*
- **Label counts** (327 items): A3 95, G4 69, A2 57, G3 53, N 34, A4 14, A1 3, G2 1, G5 1.
- **By family:** 169 artefact, 124 grid event, 34 normal. Mean confidence 0.945; 8 items below 0.7:
  - 6 vote-less single-zone fills at about 0.51;
  - Boujdour on 31 Mar 2024 → N at 0.60;
  - the C11 transfer → G5 at 0.68.
- **Agreement with majority vote: 98.2 %.** On the real data the label model mostly confirms the rules. Its value is calibrated confidence where rules conflict, and robustness under injection (to be shown in NB4). The 6 disagreements:
  - D053 and D115: single-zone zero spell right after a linear fill. MV says A1, DS says G3 (0.84).
  - Three vote-less fills: N → A3 (0.51).
  - Boujdour on 31 Mar 2024: A4 → N.
- **Evidence:** `results/labels_v1/q.csv`, E13, E14.

### F24 — Which rules the real labels depend on — *solid*
- Share of items whose label changes:

| Change | Items affected |
|---|---|
| Drop the calendar family (R10, R14) | 39 % of dead items (the G3/G4 split), 21 % of clock items |
| Drop the interpolation family (R19–R21) | 98 % of fill items |
| Drop the conservation family (R16) | 92 % of transfer items (no evidence left; the prior decides) |
| Drop the clock family (R13, R15) | 24 % of clock items |
| Drop hold, restoration, simultaneity or single-zone families | ≤ 1.3 % |
| Turn off the defining-rule prior | 39 % of dead items |
| b prior (1, 4) | 18 % of clock items |
| b prior (1, 19), π prior 0.5 or 2, different init | ≤ 2 % |

- **Evidence:** `results/labels_v1/robustness.csv`, E15.

### F25 — The item-level label model ignores episode context — *solid (observation)*
- D118 (L1, 50 min of zeros at the tail of C12, right after a 43-h hold) → G4 (0.96). R9 and R10 outweigh R3.
- D053 and D115 → G3 although a linear fill precedes them.
- **Fix candidates:** an episode-context rule (a dead item linked to a multi-zone fill in the same episode → A1), or the end model (NB3) with episode features. Not done yet.

### F26 — Anomalous time is dominated by artefacts — *provisional* (**measured exactly in F51: 4.15×; on injected data the typed count is far closer to the truth than the naive one, F52**)
- **Southern system, all labelled items, zone-hours ≈ item duration × zones (upper-bound approximation):**
  - artefacts 2,604.6 zone-h;
  - grid events 294.0 zone-h (G2 4.1, G3 208.3, G4 81.5);
  - normal 22.7 zone-h.
  - Out of about 222,222 southern zone-hours in the record, that is 1.17 % artefact and 0.13 % grid event.
- **A1 zero fills alone are 936.5 zone-h.** A naive "zero = outage" rule would count them as outages and overstate southern outage time about 4.2-fold: (936.5 + 294.0) / 294.0.
- **Paper:** a strong preview of the downstream argument (guide RQ4, the SAIDI-style check). It must be confirmed after NB4 validates the labels and NB5 runs the outage-statistics check.
- **Evidence:** `results/labels_v1/q.csv` (aggregation in docs/results_summary.md).

### F27 — Compound episodes are the norm for large events — *solid*
- **Label sequences:**
  - C05/C06: A2 → A2 → A1 (the holds, then the 15-zone zero fill).
  - C12: A2 → A1 → A2 → G4 (B/F hold → zero fill → L1/L2 hold → L1 tail; the last item is the F25 limitation).
  - C09: A1 → A2.
  - C01: G4 → A3 → A3 → G3.
  - C02, C04, C07: G3 → A3 (outage, then synthetic ramp).
- **Evidence:** `results/labels_v1/episodes_labelled.csv`.

---

## D. Detector and end model (NB3, 2026-11-08)

**Run behind every number in this section:** local, LightGBM 4.6.0, with the structural-zero fix (D51, D52). The two earlier runs (sklearn fallback; Colab LightGBM before the fix) are superseded; how their numbers differed is in the research log (session 4) and in F35.

### F28 — The predictors are accurate on clean data — *solid*
- **Out-of-sample MAE of ρ on rule-clean steps:**

| System | Forecast | Nowcast | STL | ρ̂ = 1 (expected value) |
|---|---|---|---|---|
| South | 0.0288 | 0.0292 | 0.0594 | 0.1835 |
| Marrakech | 0.108 | 0.108 | n/a | 0.276 |

- The south second fold (Jul 2023 +) has MAE 0.0278, so there is no degradation across the temporal split.
- **Residual autocorrelation** (lag-1, median over zones): forecast 0.18, nowcast 0.20 (statsmodels Ljung–Box Q at lag 144: about 11,000 and 14,000). Some structure is left, which a better predictor could remove.
- **Backend robustness:** the sklearn HistGradientBoosting fallback gave the same MAE within 0.0003 (research log, session 4).
- **Evidence:** `results/detector_v1/predictor_metrics.csv`, `ljung_box.csv`, E16.

### F29 — The guide's graph nowcast neither helps nor hurts on real data — *solid (measurement), strong (interpretation)*
- **No gain on normal data:** adding every other zone's current ρ (guide eq. 13) does not lower the MAE (0.0292 vs 0.0288).
- **No absorption of logger artefacts:** the concern behind D40 was that the nowcast would "explain away" logger artefacts. It does not on the real data: the region score g during C06 is 232.6 with the nowcast vs 218.0 with the forecast (C09: 240.4 vs 230.0).
- **Hierarchy consistency:** forecast 0.714, nowcast 0.694, STL 0.621 (206 southern items outside the warm-up). The forecast/nowcast gap is 4 city-level fill items. In the two superseded runs the order was reversed (nowcast ahead by 3–4 items), so the difference is noise.
- **Why:** trees trained only on rule-clean steps never see all zones dropping together, so an all-zone drop is out of distribution and gets a near-normal prediction. **For shared anomalies the rules do not flag**, which is the detector's purpose, the nowcast could still absorb them. This is untested on real data; NB4 must inject unflagged multi-zone events and compare.
- **Choice:** forecast as the main residual (D40). It is at least as good, simpler, and does not depend on shared shocks being masked during training.

### F30 — The residual hierarchy localises outages reliably and fills only partly — *solid*
- **Share of items whose top-scoring level matches their structural level** (raw band):

| Item kind | Expected level | n | Forecast | Nowcast | STL |
|---|---|---|---|---|---|
| dead | g (multi-city) | 3 | 1.00 | 1.00 | 1.00 |
| dead | v (one zone) | 71 | 0.915 | 0.915 | 0.873 |
| fill | g | 6 | 0.167 | 0.167 | 0.167 |
| fill | u | 40 | 0.550 | 0.450 | 0.325 |
| fill | v | 86 | 0.651 | 0.651 | 0.570 |

- **Mechanism:** a dead event is a coherent amplitude shock (every affected zone goes to about −1), so the median across zones carries it to the right level. A hold or linear fill makes each zone drift away from its *own* expected path by a different amount and sign, so the shared part (median) is small and the zone part dominates. City-wide fills reach u about half the time; multi-city fills almost never reach g (1 of 6, C05).
- **The fix of F35 changed these numbers.** Before it, structural zeros inflated zone-level scores, so v "won" too often: dead v 0.958, fill v 0.849, fill u 0.350 (Colab LightGBM run). With honest scales, the conclusion holds and is sharper: outages localise (3/3, 92 %), fills are ambiguous.
- **Paper:** the guide's claim "an artefact on the logger moves the region part" holds for **zero-fill** artefacts (C06, C09, C12: g scores 176–230; Fig 8) but **not for fill artefacts**. Fill artefacts are identified by the rules (holds, collinearity), not by the residual hierarchy. That makes the rules and the detector complementary. Say so.
- **Evidence:** `results/detector_v1/hierarchy_consistency.csv`, `hierarchy_consistency_by_kind.csv`, Fig 8.

### F31 — Multi-scale scoring needs phase alignment, a warm-up and honest scales; then the detector finds most outages — *solid*
- **First version** (causal MODWT bands, negative set = "not masked"):
  - γ = 103.8;
  - the top detector-only candidates were artefacts of the method: flags 8–10 h after real disturbances on normal data (causal band smear), and a score of 9,014 in the first week (empty baseline);
  - recall of G3/G4 items was only 39 % / 29 %.
- **After phase alignment** (measured group delays W1–W4 = 4, 11, 25, 53 steps, V4 = 43, matching the analytical LA(8) shifts), a 21-day warm-up, a negative set away from rule events (D42–D43) and the structural-zero fix (D51):
  - γ = 25.5 in the south and 16.9 in Marrakech (37.2 / 33.3 before the fix, with sklearn / LightGBM);
  - southern recall of rule items: A1 3/3, G3 18/18, G4 95 %, A2 79 %, A3 53 %, the 3 vote-less fills 3/3. The G2 item falls in the warm-up.
- **Marrakech is weak:** recall G3 9 %, G4 8 %, A3 0. Its predictor MAE is 0.11 (whole kW, a small zone), and its 48 dead items are mostly noise-floor runs (F15).
- **Cost of the warm-up:** 11 southern items (14 Sep – 5 Oct 2022) have no detector score, including the only G2 candidate.
- **Evidence:** `results/detector_v1/detector_recall_of_rule_items.csv`, research log.

### F32 — The detector finds anomalies outside the typology — *strong*
- **Numbers:** 290 detector-only candidates (283 south, 7 Marrakech). 248 are single-zone; median duration 1.3 h (10–90 %: 0.5–5.7 h).
- **Descriptive bins:** 143 "other", 114 surges (mean ρ > 1.4), 33 partial drops (mean ρ < 0.7 and minimum ρ < 0.5).
- **Examples (E18):**
  - **Near-dead runs the dead definition misses:** F1, 17 Dec 2022, mean ρ ≈ 0.08 for 7.3 h (just above ε = 0.05); B1, 29 Oct 2022, ρ ≈ 0.08 for 0.5 h; L3, 14 Nov 2023, ρ ≈ 0.07–0.1 for about 4 h (score 213).
  - **Dead runs shorter than the 3-step minimum:** F3 (8 Jun 2023), L2 (11 Mar 2024).
  - **A system-wide disturbance shorter than 30 min:** 5 Feb 2024 09:40, all 15 zones flagged (score 226); F1 hits zero for one step and B1/B2 dip.
  - **Half-load periods:** L4, 1–2 Nov 2023, ρ ≈ 0.4–0.7 (four candidates).
  - **Sustained surges:** L2 at about 1.8× expected through Nov 2023 (18 candidates, 15 surges; the three highest-scoring candidates of the whole run, 224–277, on 1–3 Nov); L4 (24 Dec 2023, 20 Jan 2024); B3 (27 Apr 2023); B2 (13 Jul 2023; 12–15 Dec 2023 at the ρ clip of 3 for days, which may also be a broken expected value).
  - **Short single-step spikes** (other): L5, 3 Aug 2023 (ρ 2.6 then 0.2); L3, 12 Oct 2023 (ρ 3.0).
- **Multi-zone candidates** (42) are mostly short (0.5–6 h) city-wide wobbles. Several fall on calendar transitions: Laâyoune on 12 Mar 2024 (first day of Ramadan 2024, three candidates up to 4.3 h) and L1/L4/L5 on 19 Mar 2023 (the switch to GMT, a clock-ambiguous date; results_summary §3). The predictor has calendar features for both, but not for the transition day itself. This is an observation, not a typed result.
- **End-model label of the 290 candidates:** N 270, A3 13, G4 5, A2 1, G3 1. The end model is trained only on typed classes and normal windows, so "N" here means **no typed class fits**. These are untyped anomalies, not normal behaviour.
- **Paper:**
  1. Coverage beyond the rules is real but mostly *outside* the typology.
  2. **The dead threshold ε and the 3-step minimum matter.** Several partial drops are near-misses of the dead definition (guide ablation 6: ε ∈ {0.02, 0.05, 0.1}).
  3. Candidate typology extensions:
     - **partial outage** (0.05 < ρ < 0.5);
     - **short interruption** (< 30 min, system-wide);
     - **unconserved level shift / surge**. The L2 surge in Nov 2023 has no matching drop, so it is not a G5 transfer under R16.
- **Evidence:** `results/detector_v1/detector_items.csv`, `detector_only_nature.csv`, E17, E18.

### F33 — The end model reproduces the label model; detector and episode features add no agreement on real data — *solid*
- **Out of fold by episode, GBDT (LightGBM) with all 43 features:**
  - 94.7 % agreement with the label model's arg max on the 281 rule items;
  - 100 % of the 300 normal windows predicted N;
  - per class: A1 3/3, A2 57/57, A3 95/95, G3 45/53, G4 66/69, G2 0/1 (a singleton cannot be learned out of fold);
  - the 3 vote-less fills → A3, not N.
- **Ablations:**
  - without detector features: 95.7 % (3 items more than with them);
  - without episode features: 94.3 %;
  - detector features only: 54.1 %;
  - MLP with all features: 90.0 %.
- **Meaning:**
  - The targets q are functions of rule features, so on real data the end model mostly re-learns the rules. Detector features cannot raise agreement with rule-derived targets; here they slightly lower it (the G3/G4 split). Their value must be shown on injected data (NB4), where rules miss or misfire.
  - Episode features did **not** fix F25: the C12 tail item on L1 (2 Apr 2024) is still G4 after fusion (p = 0.83), although the end model alone now says G3.
- **Evidence:** `results/end_model_v1/end_model_metrics.csv`, E19.

### F34 — Fusion changes 3 rule labels — *strong*
- β = 0.5, with end-model abstention on the low-support classes A1, G1 and G2 (D50; 4 items affected). 3 of 281 rule labels change, all N → A3: the three vote-less single-zone linear fills (L2/L3 on 24 Dec 2023, L1 on 6 Apr 2024; q_N ≈ 0.52; p_A3 = 0.94–0.99). A straight line is a fill even when the neighbours are too quiet for R20's 0.8 threshold. This is a sensible correction of a rule threshold by the end model.
- The G3 → G4 change on L3 (24 Dec 2023 05:50) seen in both superseded runs no longer happens: that item sits on the G3/G4 boundary.
- **Without D50:** the only G2 item (26 Sep 2022) became G3 (0.82, sklearn run). That was purely an artefact of out-of-fold prediction for a singleton class.
- **Evidence:** `results/end_model_v1/p_type.csv`.

### F35 — The median hierarchy has structural zeros that can collapse the robust scale — *solid* (bug found and fixed)
- **Mechanism:** the median of an odd number of zones is attained by one of them, so that zone's v is exactly 0 at that step; a city's u is exactly 0 when its median zone is also the region median. In the raw band, v is exactly 0 on 28–37 % of steps for the Boujdour zones (3 zones), 12–24 % in Laâyoune (5) and 9–20 % in Foum El Oued (7); u is exactly 0 on 9–19 % of steps.
- **Failure:** with zeros in the robust-scale estimate (D43 as first written), the median and MAD of |v| collapse to 0 whenever one zone is the city median for half of the 28-day window. The Colab LightGBM run hit this: B1 was Boujdour's median zone on 52 % of the V4-band window before 16–18 Mar 2024, and nine B1 "candidates" scored 3,973–15,182, while every other candidate scored below 293. The sklearn run stayed just below the 50 % line, so it did not show. Only 925 of 1,257,663 V4 zone-steps had a collapsed scale, but zeros biased **every** zone-level scale downward, most for small cities.
- **Fix (D51):** structural zeros (|s| ≤ 1e-12) are excluded from the median and MAD. B1's score on 16–18 Mar 2024 drops from 14,940 to 2.1 (V4 band).
- **Consequences:** γ fell (33.3 → 25.5, LightGBM), the zone level stopped "winning" by inflation (F30), and the detector-only list lost its spurious Boujdour entries (323 → 290 candidates; 42 multi-zone instead of 18).
- **Paper:** this is worth one sentence in the method (eq. 15) and one in the limitations: a median hierarchy over few zones needs its scale estimated on informative steps only. It also shows why an independent rerun with another backend was worth doing.
- **Evidence:** `results/detector_v1/structural_zeros.csv` (`tools/diag_structural_zeros.py`), commit 21e6695 (the Colab run before the fix).

## E. NB4 development: the graph detector and a fair evaluation (2026-11-09)

All numbers in this section are from the **development datasets** (seeds 100–104: three at 3 %, one at 1 %, one at 7 %; both periods pooled). They choose the design and are not test results. The test results are NB4's (seeds 0–9). Evidence: `results/benchmark_v1/dev/` and `dev_selection.json` (`tools/dev_select_detector.py`).

### F36 — NB4's first scoring area favoured the LightGBM detector — *solid* (protocol bug found and fixed)
- **Mechanism:** D54 excluded NB3's real-data detector candidates from the clean region where predictions are scored. Those candidates came from the LightGBM detector, so LightGBM's own false alarms on the real series were never counted, while those of every other detector (TCN-GAT, STL, Isolation Forest, LOF) were.
- **Size** (NB3 event formation, 5 development datasets):
  - LightGBM F1 0.850 (precision 0.941) under the old area, against 0.681 (0.626) under the rule-based area;
  - TCN-GAT 0.772 (0.770) against 0.649 (0.568).
  - The gap between the two shrank from 0.078 to 0.032.
- **Fix (D60):** the scoring area is rule-based, the same for every detector.
- **Paper:** report only the corrected protocol. If needed, one sentence in the methods: the scoring area must not depend on any compared detector.

### F37 — A learned correction on top of LightGBM adds nothing; averaging LightGBM and TCN-GAT helps a little — *solid*
- **Hybrids (D59):** LightGBM + learned-graph correction, and the same without the graph.
  - Both end at exactly LightGBM's real-data MAE: 0.02879 for all three.
  - Their validation loss is flat from the first epoch in both folds (0.000767 and 0.00109): the correction learned on the earlier months does not carry over, so early stopping keeps it near zero.
- **The plain average of LightGBM and TCN-GAT is the most accurate predictor** (MAE 0.02821). The TCN-GAT itself scores 0.02945 and the TCN 0.02986. The average of LightGBM and the no-graph TCN scores 0.02840, so the graph contributes part of the gain.
- **Paper:** the graph cannot improve LightGBM's point forecast, which is consistent with F27/the nowcast note (MAE 0.0292 vs 0.0288). Its value must come from detection, not prediction.

### F38 — Event formation matters more than the predictor, and it reverses the ranking — *solid*
- **Grid:** score smoothing w ∈ {1, 3, 6, 12, 24, 48} steps (centred moving average), threshold percentile q ∈ {99.0, 99.5, 99.8, 99.9, 99.95, 99.98} and merge gap ∈ {1, 3, 6, 12}, 48 settings in total. It was extended twice because the optimum sat on its edge; the final optima are inside the grid, and the top settings lie within 0.001 F1 of each other.
- **Detector alone, F1 at NB3's setting (w 1, q 99.5, gap 1) → at its best setting:**
  - LightGBM 0.681 → 0.759 (24, 99.8, 6);
  - TCN-GAT 0.649 → **0.786** (24, 99.9, 12);
  - average 0.672 → 0.771 (48, 99.8, 12);
  - STL + MAD 0.591 → 0.717 (24, 99.8, 12);
  - LOF 0.464 → 0.648 (24, 99.8, 12);
  - Isolation Forest 0.384 → 0.473 (3, 99.5, 3).
- **Why:** the 99.5th percentile with no smoothing breaks every residual excursion into many short events, which are scored as false alarms. A 4-hour smoothing, a stricter threshold and a wider merge gap cut the real-data alarms of the south system: LightGBM 283 → 58, TCN-GAT 444 → 70, STL 475 → 86, LOF 858 → 148.
  - The graph residual fragments most, so it gains most.
- **Price:** short shocks. Unflagged-shock (U_SHOCK) recall alone falls from 0.609 to 0.104 for TCN-GAT and from 0.439 to 0.119 for LightGBM; STL keeps 0.159. NB4 reports both event formations (the "NB3 event formation" rows).
- **Paper:** event formation is part of the detector and must be tuned for every compared method on separate data. Comparing detectors at one fixed threshold rule would have ranked them differently.

### F39 — The TCN-GAT graph detector is the best detector on the development data — *strong* (test pending)
- **Detector alone, at each detector's best setting:**

  | Detector | F1 | Precision | Recall | Real-data alarms |
  |---|---|---|---|---|
  | **TCN-GAT, hierarchy, multi-scale** | **0.786** | **0.866** | **0.729** | 70 |
  | average of LightGBM and TCN-GAT | 0.771 | 0.861 | 0.703 | 44 |
  | LightGBM forecast | 0.759 | 0.828 | 0.710 | 58 |
  | LightGBM + learned-graph correction | 0.760 | 0.826 | 0.714 | 56 |
  | STL + MAD | 0.717 | 0.846 | 0.628 | 86 |
  | LOF | 0.648 | 0.726 | 0.621 | 148 |
  | Isolation Forest | 0.473 | 0.412 | 0.599 | 416 |

- **Consistency:** TCN-GAT beats LightGBM in all 10 dataset × period cells, by 0.014 to 0.042.
- **With the rules (the method's use):** F1 0.863 vs 0.849 (LightGBM) and 0.854 (average). The zone-strict F1 is 0.769 vs 0.755.
- **Selection (D61):** the TCN-GAT multi-scale graph residual detector is the main detector. LightGBM and the hybrids become ablations.
- **Step-wise AUC-PR does not follow** (threshold-free, w = 1):
  - STL + MAD 0.785, LightGBM 0.649, average 0.582, TCN-GAT 0.553.
  - Forecasters that see the recent past catch up after an event starts, so mainly its edges score high, while the STL residual stays large throughout. The graph detector is best at finding events, not at covering every anomalous step.
- **Paper:** the graph contribution is event detection with fewer fragmented false alarms, not prediction accuracy (F37) and not step coverage. State all three.

### F40 — Under strict counting, no detector improves the rules' event F1 on the rules' own typology — *solid*
- **Rules alone:** F1 0.888, precision 1.000, recall 0.798, zone-strict F1 0.874.
  - Their precision is 1 by construction: real rule states are outside the scoring area, and the rules fire on every injected zero, hold and linear fill.
- **Rules + detector:**
  - best F1 0.872 (TCN-GAT at the setting that maximises the full method);
  - 0.863 at the selected setting.
  - The detector adds 3–4 points of recall (untyped events and missed outages) and costs 8–10 points of precision.
- **Why:** every real-data detector alarm in rule-clean time counts as a false alarm. About half of NB3's real-data candidates were surges or partial drops (F32), so this counting is pessimistic.
- **Remedy:** NB4 also reports F1 with each method's own real-data detections excluded (D60). This is the same treatment the rule states give the rules.
- **Paper:** do not claim that the detector raises event F1 over the rules. Claim that it finds what the rules cannot (untyped events), at a stated false-alarm cost on the real series, and that it feeds the end model.

## F. NB4 test results: the injection benchmark (Colab run, 2026-11-09)

**Evidence:** `results/benchmark_v1/` (`summary.json`, `table5_*.csv`, `table6_attribution.csv`, `table7*.csv`, `runs/`), `results/main_detector/`, `results/benchmark_v1/graph_ablation/` (F42), Figs 9–11, E20, E21.
- **Datasets:** test seeds 0–9 at 1 %, 3 % and 7 % of clean zone-time: 30 datasets, 8,526 injected events.
- **Scope:** all numbers are **test period** (Jul 2023 – May 2024), mean ± standard deviation over the 10 seeds, unless stated otherwise.
- **Run:** Colab GPU, LightGBM 4.6.0, torch 2.14.1. The models were loaded, not retrained. The run resumed once after a disconnect; all 30 run files were written on 9 Nov between 21:04 and 23:22, from the code synced at 01:09.
- **Event F1 (eq. 17):** a time overlap with an injected event, including its restoration tail; every alarm counts unless stated otherwise.

### F41 — The graph detector is the best detector on the test seeds at 3 % and 7 %, and tied with the model-based detectors at 1 % — *solid*
- **Detector alone, each at its development-tuned event formation:**

  | Detector | 1 % | 3 % | 7 % |
  |---|---|---|---|
  | **TCN-GAT, hierarchy, multi-scale (main)** | 0.644 ± 0.067 | **0.813 ± 0.020** | **0.854 ± 0.011** |
  | mean(LightGBM, TCN-GAT) | **0.655 ± 0.050** | 0.773 ± 0.024 | 0.843 ± 0.015 |
  | LightGBM + learned-graph correction | 0.627 ± 0.051 | 0.765 ± 0.024 | 0.827 ± 0.017 |
  | LightGBM + TCN correction (no graph) | 0.645 ± 0.038 | 0.752 ± 0.026 | 0.790 ± 0.021 |
  | LightGBM forecast | 0.623 ± 0.055 | 0.765 ± 0.022 | 0.827 ± 0.015 |
  | STL + MAD | 0.625 ± 0.043 | 0.734 ± 0.026 | 0.771 ± 0.024 |
  | LOF | 0.570 ± 0.035 | 0.720 ± 0.029 | 0.698 ± 0.108 |
  | Isolation Forest | 0.211 ± 0.078 | 0.462 ± 0.043 | 0.605 ± 0.099 |

- **Wilcoxon signed-rank over the 10 seeds** (`table5_wilcoxon.csv`):
  - **3 %:** the main detector beats every other detector, p = 0.002 for each.
  - **7 %:** it beats every other detector: p = 0.020 against the average, 0.004 against the graph hybrid and 0.002 against the rest.
  - **1 %:** it is not distinguishable from the average (p = 0.56), the hybrids (0.32, 1.0), LightGBM (0.16) or STL + MAD (0.49). It beats LOF (0.010) and Isolation Forest (0.002).
- **Precision and recall of the main detector:** precision 0.583 / 0.892 / 0.976, recall 0.730 / 0.748 / 0.759 at 1 / 3 / 7 %. At 1 % its precision is low because its real-data alarms weigh against few injected events. With its own background excluded (D60), its F1 is 0.817 / 0.842 / 0.848.
- **Development → test:** development F1 alone was 0.786 (rates pooled; F39). The ranking generalised: on the development data the main detector beat LightGBM in 10 of 10 cells, and on the test data it beats it at all three rates (significantly at 3 % and 7 %).
- **Step-wise AUC-PR does not follow (F39 confirmed):** main 0.547 / 0.598 / 0.565, LightGBM 0.592 / 0.678 / 0.633, STL + MAD 0.577 / 0.721 / 0.723.
- **Real-data alarms of the detector alone** (south, including alarms on real rule states; `real_data_alarms` in Table 5): main 191, average 131, graph hybrid 150, LightGBM 152, no-graph hybrid 93, STL 178, LOF 263, Isolation Forest 457. With NB3's event formation: TCN-GAT 639, LightGBM 454.
  - **Two definitions, do not mix them:** the development tables count the 70 detector-only candidates, which exclude alarms that overlap real rule items; Table 5 counts all 191.
- **Paper:** "The graph detector is the best of the eight detectors at 3 % and 7 % contamination (p ≤ 0.02 against each, 10 seeds) and statistically tied with the other model-based detectors at 1 %." Do not say "best at every rate".

### F42 — The learned graph adds no detection skill: the same detector without the graph is as good or slightly better — *solid*
- **Ablation** (D62, `results/benchmark_v1/graph_ablation/`): the TCN residual without graph attention, through the same MODWT bands, hierarchy and event formation (`TCN, no graph, hierarchy, multi-scale`), on the NB4 datasets.
- **Reproduction:** the main detector recomputed on CPU (torch 2.2) gives exactly the Colab GPU rows: F1 and F1 with background excluded identical in 30/30 runs; 191 real-data alarms. The add-on is therefore directly comparable with Table 5.
- **Development seeds** (the selection data, never shown to the selection because the row did not exist):
  - no-graph F1 alone 0.786 at the main setting, against 0.786 for the TCN-GAT;
  - 0.794 at its own tuned setting (w 48, q 99.9, gap 12);
  - full method 0.866 vs 0.863;
  - the own-tuned no-graph detector beats the TCN-GAT in 7 of 10 cells.
- **Test seeds, test period** (mean over 10 seeds):

  | Detector | Setting | F1 1 % | F1 3 % | F1 7 % | Own background excluded | AUC-PR | Real-data alarms | Onset error (min) |
  |---|---|---|---|---|---|---|---|---|
  | TCN-GAT (main) | 24, 99.9, 12 | 0.644 | 0.813 | 0.854 | 0.817 / 0.842 / 0.848 | 0.547 / 0.598 / 0.565 | 191 | 168 / 165 / 140 |
  | TCN, no graph | 24, 99.9, 12 | **0.671** | **0.817** | **0.857** | **0.826 / 0.847 / 0.852** | 0.540 / 0.598 / 0.568 | 202 | 158 / 150 / 135 |
  | TCN, no graph, own tuning | 48, 99.9, 12 | **0.707** | 0.801 | **0.861** | 0.823 / 0.829 / 0.856 | 0.505 / 0.574 / 0.532 | 170 | 238 / 240 / 230 |

- **Wilcoxon, 10 seeds** (`wilcoxon_graph_ablation.csv`):
  - **Same setting (the ablation proper):**
    - F1: no graph better at 1 % (p = 0.037; the graph wins 2 of 10 seeds), no significant difference at 3 % (p = 0.13) and 7 % (p = 0.064);
    - background excluded: no graph better at 7 % (p = 0.021), no difference at 1 % and 3 %;
    - AUC-PR equal (p ≥ 0.49).
  - **Own tuning:** no graph better at 1 % (p = 0.004) and 7 % (p = 0.027), worse at 3 % (p = 0.020); AUC-PR lower at every rate.
- **Interpretation:**
  - The main detector's advantage over LightGBM and the baselines (F41) comes from the TCN residual combined with multi-scale scoring and tuned event formation, not from graph attention. The neural residuals fragment less after smoothing than the LightGBM residual (F38).
  - This is consistent with F37: the graph does not improve prediction either. Its MAE is slightly lower than the TCN's (0.0294 vs 0.0299), but that does not carry over to detection.
  - The no-graph TCN residual also localises rule items slightly better (0.767 vs 0.733, F43).
- **What the graph does give:** an interpretable dependency map (E20; Boujdour reads most from Laâyoune and Foum El Oued), and part of the ensemble gain in F37 (MAE of the average with LightGBM 0.0282 with the graph, 0.0284 without).
- **Paper:**
  - Do not claim that the learned graph improves detection.
  - Accurate statement: "a multi-scale neural residual detector; adding learned graph attention over the zones' current values neither helps nor hurts detection (the no-graph ablation is equal or slightly better at every rate), so the graph's contribution is interpretability, not accuracy."
  - The main detector was selected (D61) before this row existed, and the test seeds are spent (D63). Switching the main detector to the no-graph TCN on this evidence would be a choice made on the test data. 
  - **Resolved (D67):** the main detector keeps its name, and the graph is presented as an ablation (Table 7e, Fig 9b, methods §6.2).

### F43 — Multi-scale scoring helps at low contamination; the region/city/zone hierarchy does not help detection — *solid*
- **Setup:** ablations of the main detector, each at the main detector's event formation (w 24, q 99.9, gap 12; D60), so that only one component changes.
- **Single scale (raw band only):** F1 0.595 / 0.772 / 0.853, against the main detector's 0.644 / 0.813 / 0.854. The MODWT bands add 0.04–0.05 F1 at 1 % and 3 % (Wilcoxon p = 0.004 and 0.002) and nothing at 7 % (p = 0.85).
- **No hierarchy (flat robust z of the zone residual, raw band):**
  - F1 0.675 / 0.796 / 0.856. Paired Wilcoxon against the main detector (Table 7e): not different at 1 % (p = 0.16) or 7 % (p = 0.38), significantly lower at 3 % (p = 0.014; the main detector wins 9/10 seeds);
  - AUC-PR 0.736 / 0.811 / 0.791, much higher than the main detector's 0.547 / 0.598 / 0.565;
  - start error 82 / 90 / 80 min against 168 / 165 / 140 min.
- **Why:** the zone score is the maximum over the region, city and zone parts (eq. 14). A multi-zone event shifts the region or city median, so the zones it did not touch also score high at those levels. This adds false zone-steps (lower AUC-PR) and time-only matches (F44). The hierarchy's value is in **placing** an event at the right level (F30: dead items 92 % at the zone and 3/3 at the region), not in detecting it.
- **Localisation by predictor** (real rule items at the expected level, `hierarchy_consistency_by_predictor.csv`, 206 items):

  | Predictor | All items | Multi-city dead at the region | Single-zone dead at the zone | Fills at the zone |
  |---|---|---|---|---|
  | TCN (no graph) | **0.767** | 2/3 | 0.915 | 0.767 |
  | TCN-GAT | 0.733 | 2/3 | 0.915 | 0.733 |
  | LightGBM forecast | 0.714 | **3/3** | 0.915 | 0.651 |
  | average of LightGBM and TCN-GAT | 0.714 | 2/3 | 0.915 | 0.651 |

  The neural residuals localise fills better. LightGBM's residual is the only one that places all three multi-city dead items at the region.
- **Caveat:** the flat variant was not tuned on the development data, and adopting it now would be a choice made on the test seeds (D63).
- **Other paired tests (Table 7e):**
  - TCN, raw band: lower at 1 % and 3 % (p = 0.027, 0.002), higher at 7 % (p = 0.004);
  - LightGBM as the predictor: lower at 3 % and 7 % (p = 0.002), not different at 1 % (p = 0.16);
  - NB3 event formation: lower at every rate (p = 0.002).
- **Paper:**
  - "multi-scale bands help at low contamination; the hierarchy is a localisation device and does not hurt detection (it helps at 3 %)";
  - report the flat row next to the main one;
  - do not claim that the hierarchy improves detection.

### F44 — Adding the graph detector to the rules: worse at 1 %, equal at 3 %, better at 7 % under strict counting; better at every rate with each method's real-data background excluded; worse at every rate under zone-strict matching — *solid*
- **Event F1, ours (rules + detector-only candidates) vs rules alone** (Wilcoxon over 10 seeds):

  | Rate | Ours, strict | Rules | p | Ours, own background excluded | p | Ours, zone-strict | Rules, zone-strict |
  |---|---|---|---|---|---|---|---|
  | 1 % | 0.721 | **0.863** | 0.002 | **0.896** (10/10 seeds) | 0.002 | 0.628 | **0.863** |
  | 3 % | 0.876 | 0.879 | 0.63 | **0.905** (10/10) | 0.002 | 0.778 | **0.872** |
  | 7 % | **0.906** (10/10) | 0.896 | 0.002 | **0.908** (10/10) | 0.002 | 0.811 | **0.876** |

- **Recall** rises at every rate: 0.824 vs 0.760, 0.834 vs 0.785 and 0.839 vs 0.812 (10/10 seeds each). The gain comes from:
  - unflagged events: U_SHOCK recall 0 → 0.30 / 0.21 / 0.05 and U_PARTIAL 0 → 0.18 / 0.21 / 0.22;
  - city outages the rules miss: G2 recall 0.90 / 0.93 / 0.94 → 1.00 / 1.00 / 0.998.
- **Precision falls:** 0.646 / 0.921 / 0.984 against 1.000 for the rules.
  - At 1 %, ours predicts 66.8 events per test period against 40.8 injected. About 26 of them are the real-data background: with it removed, ours predicts 40.9.
- **Zone-strict view: the detector-only candidates mostly flag the wrong zones** (test period, in scope; `runs/*_pred.csv`):
  - only 8 % / 18 % / 18 % share a zone with an injected event;
  - 25 % / 58 % / 75 % overlap an injected event in time on other zones;
  - the rest (66 % / 24 % / 7 %) overlap nothing, mostly the real-data background.
  - **Why:** the rule items already cover the affected zones, so the detector items left over are the unaffected zones lifted by the region or city part of the score (F43). Under eq. 17 these time-only overlaps count as hits; under zone-strict matching they are false alarms. Even with the background excluded, zone-strict F1 stays below the rules: 0.814 / 0.813 / 0.815 vs 0.863 / 0.872 / 0.876.
- **Paper:**
  - The detector adds recall the rules cannot have (untyped events, missed city outages).
  - Whether this raises event F1 depends on how unflagged real-data alarms are counted and on the contamination rate.
  - Report all three views.
  - Do not claim a general F1 gain over the rules.
  - A natural fix links detector-only candidates that co-occur with a rule item in the same city or region to that episode instead of reporting them as new events. It has to be developed on development seeds and tested on fresh seeds (D63).

### F45 — The tuned event formation trades short shocks and onset timing for precision — *solid*
- **Unflagged-shock recall** (U_SHOCK, zone-strict) of the main detector: 0.302 / 0.212 / 0.058 tuned, against 0.925 / 0.774 / 0.285 at NB3's event formation (w 1, q 99.5, gap 1). The NB3 setting's F1 is 0.365 / 0.670 / 0.835 because of fragmented alarms: 639 on the real data, against 191 tuned.
- **Median onset error** of zone-matched detections: main 168 / 165 / 140 min, LightGBM 110 / 118 / 100, STL + MAD 70 / 70 / 60, LOF 20 / 28 / 45, Isolation Forest 10. The 4-hour smoothing window and the 12-step merge gap blur onsets.
- **Typed events, recall of the detector alone** (`detection_recall_by_type.csv`):
  - main detector: A1 0.997–1.000, G1 1.000, G2–G4 0.975–1.000;
  - LightGBM: G2–G4 0.908–1.000.
  - Short single-zone fills (A3) are the hardest typed class for the detectors: 0.25–0.29 for the main detector, 0.15–0.22 for LightGBM. The rules catch them all.
- **Paper:** the detector is for finding sustained events. Event timing comes from the rules where they fire. For detector-only items, report onsets as approximate (± about 3 h).

### F46 — On injected signatures, the label model does not beat majority vote; fusion matches both; the end model alone is worse — *solid*
- **Attribution macro-F1** over the typed events detected by the full method (test period):

  | Labeller | 1 % | 3 % | 7 % |
  |---|---|---|---|
  | majority vote (rules) | 0.940 | **0.921** | **0.913** |
  | label model q | 0.934 | 0.914 | 0.900 |
  | end model f, no detector features | 0.875 | 0.899 | 0.898 |
  | end model f, all features | 0.845 | 0.874 | 0.902 |
  | fusion (β*, D50 abstention) | **0.944** | 0.919 | 0.906 |
  | fusion (β*, no abstention) | 0.936 | 0.920 | 0.910 |

  The differences between majority vote, label model and fusion are within one standard deviation (0.015–0.055).
- **Detector features do not help the end model** at 1 % and 3 % (0.845 vs 0.875, 0.874 vs 0.899) and barely at 7 % (0.902 vs 0.898), consistent with F33 on real data.
- **Calibration:**
  - Mean per-seed ECE: label model 0.068 / 0.089 / 0.099, fusion 0.074 / 0.090 / 0.100, end model 0.107 / 0.078 / 0.061.
  - Pooled over the seeds at 3 % (Fig 11): 0.074, 0.078 and 0.062.
  - Majority vote gives no probabilities.
- **End to end** (typed test events detected and correctly typed): 0.945 / 0.907 / 0.896. The full method detects practically every typed event (detected share 1.000 / 1.000 / 0.9996).
- **β\*** (tuned on the train period): 0.7 / 0.6 / 0.6 with abstention.
- **Paper:**
  - The label model's contribution is calibrated probabilities and stability on sparse real-data votes (F21–F24), not higher accuracy than majority vote on clean injected signatures, where the rules rarely conflict.
  - Report majority vote as a strong baseline.
  - Contribution 2 ("calibrated probabilistic labels") holds; "more accurate than voting" does not.

### F47 — Multi-city zero-fill gaps are read as regional outages, through the simultaneity rules — *solid*
- **Fig 10 (3 %, test, fused):**
  - A1 is the weakest class (F1 0.789): 105 of 160 correct, 44 → G1, 6 → G2, 5 → N.
  - Other errors: G3 → G4 15 of 123, and G2 → N 11 of 137. The G2 cases are the city outages the rules miss: the detector finds them, but as detector-only items they are labelled N (F44).
  - G1 133/133 and G4 126/126 are perfect.
- **Mechanism** (3 %, all periods, 271 detected A1 events; label-model arg max):
  - multi-city zero gaps go to G1 69 times out of 228 (2 cities 40/128, 3 cities 29/100);
  - zero fills after a city-wide fill, in one city, go to G2 13 times out of 25.
  - The injected G1 drops to a floor level; the injected A1 drops exactly to zero across several cities at once, and the simultaneity family votes "regional".
- **Rule-family ablation** (Table 7c, 3 %, test, label model macro-F1): all families 0.914. Without simultaneity **0.941**, without city 0.922, conservation 0.915, single-zone 0.915, restoration 0.902, hold 0.893, calendar 0.778, interpolation 0.724.
  - Without simultaneity, A1 accuracy rises from 0.697 to 0.834, G1 stays at 1.000, and overall accuracy goes from 0.904 to 0.925.
  - Interpolation and calendar are the most valuable families.
- **Caveat:** on the real data, multi-city zero fills come with holds or linear fills (F03), which the rules use. The injected A1 copies the zero part only. So the confusion is partly a property of the injector.
- **Paper:**
  - Report it as the main attribution error: exact simultaneous zeros across cities are ambiguous between a logger gap and a regional outage when nothing else is known.
  - It argues for the exact-zero share (R6) and the fill context outweighing simultaneity.
  - Re-weighting the families on these results would be tuning on the test seeds (D63).

### F48 — The rules and the label model are robust to their thresholds, except the hold length and a tight ε — *solid*
- **Setup:** Table 7d, 3 %, seeds 0–2, test period, one threshold changed at a time.
- **Rules F1:**
  - baseline 0.891; ε 0.02 0.880, ε 0.10 0.881, hold 12 0.880, τ 0 or 20 min 0.891;
  - **hold 4: 0.765**, with unchanged recall. Four-step holds also fire on short real freezes (F09) inside the scoring area, so precision drops.
- **Label model macro-F1:**
  - baseline 0.906; ε 0.10 0.915, hold 4 0.906, hold 12 0.885, τ 0.904–0.905;
  - **ε 0.02: 0.819**.
- **ε and partial outages:** U_PARTIAL recall of the rules rises from 0.042 to 0.162 at ε 0.10, confirming F32: partial outages sit just above the dead threshold.
- **Paper:** the thresholds chosen on the real data (D15, D18) are not on a cliff edge, except that a hold minimum below 6 steps would admit the daily freeze.

### F49 — Hard negatives: the graph detector flags weekends and Eid more often, LightGBM flags Ramadan — *solid (measurement)*
- **Setup:** real data; flag rate of the detector alone per day type, divided by the ordinary-weekday rate (`hard_negatives.csv`).
- **Main detector** (ordinary weekday 0.0011): weekend 1.70×, Eid 2.56×, national holiday 0.99×, Ramadan 0.73×.
- **LightGBM** (ordinary weekday 0.0018): weekend 1.17×, Ramadan 2.15×, Eid 0.34×, holidays 0.
- **Ordinary-weekday flag rate:** the main detector's is about 40 % lower than LightGBM's.
- **Why:** not examined. Both predictors receive calendar inputs, the TCN-GAT through its calendar features and LightGBM through explicit calendar columns.
- **Paper:**
  - One sentence in the hard-negative analysis.
  - Eid and weekends are where the graph detector's alarms concentrate.
  - Few days are involved (Eid: 11,280 zone-steps), so treat the ratios as indicative.

### F50 — The real-data catalogue with the main detector: 70 detector-only candidates, the rule labels unchanged — *solid*
- **Setup:** NB4 §8b (`results/main_detector/`): the south data through the whole method with the main detector. γ = 24.87, β = 0.6.
- **Candidates:** 70 detector-only candidates, against 283 for NB3's south detector; 66 of the 70 overlap an NB3 candidate.
  - **Shape:** 61 single-zone, 7 two-zone, 1 three-zone and 1 spanning all 15 zones.
  - **Where:** Laâyoune 51, Boujdour 13, Foum El Oued 5, all three cities 1.
  - **Duration:** median 3.4 h (IQR 2.2–5.0).
  - **When:** 49 in the test period, 21 in the train period.
  - **By NB3's nature class:** other 41, surge 17, partial drop 8, not in NB3 4.
- **Fused labels of the candidates:** N 58, A3 7, G4 3, A2 1, A1 1. N still means "no typed class fits" (F32).
- **Rule items (226 in the south):** one label changes against NB3. The 6 Aug 2023 07:00–13:30 dead item on B2 moves from G3 to G4 (p 0.556 vs 0.443), a borderline case.
  - South rule-item labels: A3 91, G4 57, A2 57, G3 17, A1 3, G2 1.
- **Paper:**
  - The catalogue's typed part does not depend on the detector.
  - The untyped part shrinks four-fold with the tuned graph detector.
  - Cite the main-detector numbers for the south and NB3's for Marrakech (D61).

## G. NB5: does type-aware cleaning matter? (2026-11-10)

**Evidence:** `results/downstream_v1/` (`table8_forecasting.csv`, `table8_dm.csv`, `outage_real.csv`, `outage_injected.csv`, `injected/`, `summary.json`), Fig 12, `notebooks/NB5_downstream.ipynb`. Design: D64–D66.
- **Scope:** southern system.
- **Test period:** 1 Jan – 24 May 2024.
- **Strategies:** S0 raw, S1 naive interpolation, S2 typed, S3 oracle (injected data only).
- **Injected datasets:** NB4's 3 % seeds 0–2 and 7 % seed 0.

### F51 — Counting every dead state as an outage overstates southern outage time 4.15-fold on the real data — *solid (measurement); interpretation rests on the labels*
- **Dead states inside qualifying rule runs:**
  - naive count ("every dead state is an outage"): **1,220.5 zone-hours in 117 runs**;
  - typed count (dead steps of items labelled G): **294.0 zone-hours in 79 runs**;
  - ratio 4.15.
- This is the exact version of F26's approximation (4.2×). F26 is confirmed.
- **Dead zone-hours by item label:** A1 926.5, G3 201.8, G4 88.0, G2 4.2. A2 and A3 contribute none, because fills are not dead.
- **By city, naive vs typed zone-hours:** Foum El Oued 728.7 vs 220.0, Laâyoune 252.0 vs 52.2, Boujdour 239.8 vs 21.8.
- **Paper:** the utility-facing headline. On the injected data, where the truth is known, the typed count is far closer to it than the naive count (F52). The real-data ratio inherits the label uncertainty: the attribution accuracy on injected data is 0.90–0.94 (F46).

### F52 — On injected data, typed outage statistics remove most of the naive overcount but still overcount, because of the A1 → G1 confusion — *solid* (**extended to all 30 test datasets in F59: typed 1.26× vs naive 1.88×, typed closer in 30/30; cite F59 in the paper**)
- **Outage zone-hours inside NB4's scoring area**, relative to the injected truth (G1–G4 core spans):

  | Dataset | Truth (zone-h) | Naive, every dead state (S0) | Typed, label model (S2) | Interpolated away (S1) |
  |---|---|---|---|---|
  | 3 %, seed 0 | 2,478.8 | 1.49× | 1.14× | 0 |
  | 3 %, seed 1 | 1,595.8 | 2.39× | 1.76× | 0 |
  | 3 %, seed 2 | 2,346.3 | 1.77× | 1.29× | 0 |
  | 7 %, seed 0 | 4,503.8 | 1.90× | 1.25× | 0 |
  | mean | | **1.88×** | **1.36×** | 0 |

- **Outage counts (runs):** at 3 %, truth 405.7, naive 727.7, typed 535.0; at 7 %, 999, 1,819 and 1,296.
- **Typed outage zone-steps:** recall 0.997–0.999, precision 0.567–0.872. The typed count misses almost no true outage time; its excess is artefact time labelled G, mainly multi-city zero gaps read as regional outages (F47).
- **S1 erases every outage:** a forecaster-oriented cleaning that interpolates everything reports no outage time at all.
- **Paper:** typed cleaning cuts the outage-time error from +88 % to +36 % on average. The remaining error is a measured, named confusion. Do not claim "correct outage statistics" (the guide's expected effect); claim "much closer to the truth than naive counting, with a known residual bias".

### F53 — Typed cleaning gives the best LightGBM forecasts on real and injected data; the gain sits after anomalies and comes close to the oracle — *solid* (**injected part extended to all 30 test datasets in F62; cite F62**)
- **Real data, MASE, S0 / S1 / S2** (Diebold–Mariano p for S1 vs S2 and S0 vs S2):

  | Horizon | After an anomaly (24,744 zone-steps) | DM p | All test steps (305,257) | DM p |
  |---|---|---|---|---|
  | 1 h | 0.656 / 0.661 / **0.613** | < 0.0001 / 0.0001 | 0.654 / 0.657 / 0.654 | 0.019 / 0.86 |
  | 1 day | 1.501 / 1.233 / **1.061** | 0.22 / 0.23 | 1.140 / 1.115 / **1.102** | 0.25 / 0.21 |

  - After an anomaly, the day-ahead MAE falls from 10.53 A (S0) and 9.63 A (S1) to 8.89 A (S2): −29 % and −14 % in MASE.
  - The day-ahead gain is large but not significant on the real data: a few multi-zone events carry it, so the HAC variance is large.
- **Injected data, MASE, mean of 4 datasets, S0 / S1 / S2 / S3:**
  - after an anomaly: 1 h 0.708 / 0.640 / 0.625 / 0.618; 1 day 1.293 / 1.107 / 1.056 / 1.046;
  - all test steps: 1 h 0.652 / 0.622 / 0.613 / 0.608; 1 day 1.170 / 1.069 / 1.043 / 1.039.
  - **S2 vs S0:** S2 is significantly better (DM p < 0.05) in 4 of 4 datasets for every horizon and subset.
  - **S2 vs S1:** 4/4 at 1 h on all steps, 3/4 at 1 h after an anomaly, 2/4 at 1 day. S1 is never significantly better.
  - **S2 vs the oracle:** S2 closes 62–86 % of the gap between S1 and S3. The oracle is significantly better than S2 in 0–3 of 4 datasets.
- **Paper:**
  - "Type-aware cleaning improves day-ahead forecasts after anomalies by 14 % (MASE) over naive interpolation on the real data, and comes within about 1 % of an oracle on injected data (MASE 1.056 vs 1.046)."
  - Report the 'all steps' rows too: over the whole test period the effect is small (≤ 3 %), because anomalies are rare.

### F54 — The typed advantage needs a forecaster that reads the event indicator: a model-free forecaster prefers erasing outages — *solid* (**confirmed on 30 datasets in F62**)
- **Naive reference** (persistence at 1 h, seasonal naive at 1 day), injected data, MASE S0 / S1 / S2 / S3:
  - 1 h, all steps: 0.913 / **0.881** / 0.891 / 0.882;
  - 1 day, all steps: 1.401 / **1.155** / 1.236 / 1.199.
  - S1 is significantly better than S2 in 4/4 datasets at 1 h and 2/4 at 1 day. S0 is worst throughout.
- **On the real data, where grid events are few,** the naive reference still prefers S2: 1 day after an anomaly 2.220 / 1.553 / **1.278**.
- **Why:** S2 keeps grid events in the history. Persistence and seasonal naive copy an outage forward into the next hour or day, while LightGBM reads the event indicator and discounts it. S1 removes outages from the history, which helps a naive forecast, but it also removes them from the outage statistics (F52).
- **Paper:** the guide's expected effect ("S2: best error and correct outage statistics") holds for an indicator-aware forecaster. With a forecaster that cannot use the indicator, there is a trade-off between forecast error (S1) and outage statistics (S2). This is an argument for passing the typed labels to the forecaster, not just cleaning with them.

## H. NB6: transfer to Tetouan without re-tuning (2026-11-10)

**Evidence:** `results/transfer_tetouan/` (`summary.json`, `table9_*.csv`, `real_*.csv`, `confusion_label_model_3pct.csv`, `morocco_vs_tetouan.csv`, `runs/`), Fig 13, E22, `notebooks/NB6_tetouan.ipynb`. Design: D68–D70.
- **Frozen:** rules, label-model parameters, detector architectures and hyper-parameters, event formation.
- **Re-estimated from Tetouan's unlabelled series:** x̂, predictor weights, γ.
- **Benchmark:** 30 injected datasets (1/3/7 % × seeds 0–9), 2,778 injected events. Whole year after the burn-in.

### F55 — On a clean year of another city's data, the frozen rules raise zero false items — *solid*
- **The series:** 52,416 steps (1 Jan – 30 Dec 2017). No duplicate or missing stamp, no zero, and no run of equal values longer than 3 steps.
- **Frozen rule engine:** no zone run (dead, hold or linear fill) and so no dead or fill item.
- **Clock days:** the only items are the 4 clock-change days (26 Mar, 21 May, 2 Jul, 29 Oct 2017), all labelled N by the frozen label model (confidence 0.969).
  - Their profile offsets are −10, +10, −30 and 0 min, below the 50-min threshold of R15, with fit correlations 0.96–0.99.
  - No rule output unseen in Morocco occurred.
- **Detector alarms on the real series in 2017** (3 zones):
  - main detector 7 (0.20 per zone-month; 26.8 alarm zone-hours);
  - no-graph TCN 9; LightGBM 15; STL + MAD 13; LOF 11; Isolation Forest 72.
  - The main detector's alarms fall on 20 Apr (T1, T2), 4 and 7 Jul (T1), and 28 Sep, 12 Nov and 20 Nov (T3). None is on a Ramadan, Eid or holiday date.
  - Zone 3's level falls by about half from September, and the November alarms coincide with a short mid-November bump in that zone (E22a). This is an observation, not a validated event.
- **Paper:** "Applied frozen to a clean year of a different city's feeders, the rule engine raised no false item. The main detector raised 7 alarms in 36 zone-months, the fewest of the seven detectors."

### F56 — The full method transfers: event F1 0.945 / 0.919 / 0.890 at precision 0.98–1.00, better than the rules alone at every rate — *solid*

| Method (Tetouan, frozen) | F1 1 % | F1 3 % | F1 7 % | Precision | Recall |
|---|---|---|---|---|---|
| **ours (rules + main detector)** | **0.945 ± 0.036** | **0.919 ± 0.008** | **0.890 ± 0.009** | 0.983 / 1.000 / 1.000 | 0.913 / 0.850 / 0.801 |
| rules only | 0.856 ± 0.012 | 0.861 ± 0.010 | 0.860 ± 0.006 | 1.000 | 0.749 / 0.756 / 0.754 |

- **Ours vs rules:** better in 10/10 seeds at every rate (Wilcoxon p = 0.002 each). Zone-strict F1 0.936 / 0.908 / 0.881 vs 0.856 / 0.857 / 0.855.
- **Recall by type (ours):**
  - every typed class 1.000 at 1 % and 3 %; at 7 %, G2 0.987 and the rest 1.000;
  - U_PARTIAL 0.975 / 0.736 / 0.340 and U_SHOCK 0.308 / 0.020 / 0.000. The rules alone find neither.
- **Why the detector now adds F1 at every rate** (unlike Morocco, F44): the clean series gives the detector almost no background (7 alarms), so its additions keep precision at 1.000 at 3 % and 7 %.
- **Morocco vs Tetouan, ours** (context, not a paired test): 0.721 vs 0.945 at 1 %, 0.876 vs 0.919 at 3 %, 0.906 vs 0.890 at 7 %.
- **Paper:** RQ5 answered for detection. Without re-tuning, the full method detects 80–91 % of injected events at 98–100 % precision and beats the rules alone everywhere.

### F57 — Detector alone after transfer: the main detector is best at 1 %; at 3 % and 7 % the data-efficient LightGBM and STL detectors overtake it — *solid*
- **Event F1, detector alone:**
  - main (TCN-GAT) 0.857 / 0.793 / 0.722;
  - LightGBM 0.761 / 0.868 / 0.764;
  - STL + MAD 0.747 / 0.828 / 0.743;
  - LOF 0.739 / 0.728 / 0.201;
  - Isolation Forest 0.483 / 0.692 / 0.806.
- **Wilcoxon** (`table9_wilcoxon.csv`):
  - **1 %:** the main detector beats every other detector (p ≤ 0.004), except the no-graph TCN (p = 0.086).
  - **3 %:** LightGBM (p = 0.002) and STL + MAD (p = 0.004) beat it.
  - **7 %:** LightGBM (p = 0.006) and Isolation Forest (p = 0.002) beat it; STL + MAD is not significantly different (p = 0.21).
- **Why — the neural predictors need more data:**
  - Tetouan predictor MAE: LightGBM 0.0110, TCN 0.0406, TCN-GAT 0.0447; on Morocco, 0.0288, 0.0299 and 0.0294.
  - Each Tetouan fold trains on about 22,000 steps of 3 zones (half a year), against 15 zones and about 44,000 steps per fold in Morocco.
  - LightGBM's explicit same-time-yesterday and last-week features work with little data.
- **The detector alone misses fills** (main detector at 3 %: A2 0.416, A3 0.009). Fills are the rules' job; in the full method every typed recall is 1.000.
- **Graph ablation on Tetouan** (same-city edges only):
  - without the graph, F1 changes by −0.025 / −0.008 / −0.010 (p = 0.086 / 0.33 / 0.13);
  - with its own tuning, the no-graph TCN is worse at every rate (p ≤ 0.008).
  - Consistent with F42: the graph neither helps nor hurts significantly.
- **Paper:**
  - The frozen event formation transfers: model-based detectors keep precision ≥ 0.98 at 3 % and 7 %.
  - On one year of a 3-zone system, a data-efficient predictor is the better stand-alone detector at higher contamination.
  - Report it honestly. The full method stays best because the rules carry the typed events and the detector only adds what they cannot see.

### F58 — Attribution transfers, except for the class whose evidence is cross-city by design — *solid*
- **Frozen label model, macro-F1 over the injected classes:** 0.793 / 0.774 / 0.771 (majority vote 0.793 / 0.781 / 0.785). The full method detects 99 % of typed events.
- **Without A1:** macro-F1 0.978 / 0.951 / 0.949 and accuracy 0.970 / 0.940 / 0.931. This is as good as on Morocco, where all classes give 0.934 / 0.914 / 0.900.
- **Accuracy per class (1 / 3 / 7 %):**
  - A1 0.158 / 0.164 / 0.145;
  - A2 0.914 / 0.862 / 0.845; A3 1.000 / 1.000 / 0.973;
  - G2 1.000 everywhere; G3 0.944 / 0.847 / 0.877; G4 1.000 / 1.000 / 0.968.
- **A1 → G2 in 348 of 417 detected A1 events, at confidence 0.99.**
  - A city-wide exact-zero gap is read as a city outage, because the A1 evidence that worked in Morocco is cross-city: R1 needs zeros in several cities.
  - The guide anticipated this ("city-level and regional rules can't fire there").
  - The same ambiguity appears in Morocco when the zero gap is the only evidence (F47).
- **A2 → N in 49 of 342:** two-zone fills with one zone held and the other linearly interpolated. Neither R2 (≥ 2 held zones) nor R19 (≥ 2 linear zones) fires.
- **G3 ↔ G4 in 49 of 669:** unplanned outages placed in the 06:00–11:00 window read as planned work (R10), as in Morocco.
- **Paper:** RQ5 answered for attribution. Five of the six injected classes transfer at 0.85–1.00 accuracy. A1 does not, and the paper must say why: in a single-city system, a logger zero gap and a city outage share every cue the rules use. A within-city cue (an exact-zero share η = 1 across all zones together with a missing restoration ramp) is future work, and would need fresh evaluation (D63).

### F59 — On all 30 test datasets, typed outage counting is closer to the truth in every dataset; its whole excess is multi-city zero gaps read as grid outages — *solid*
- **Why:** F52 rested on 4 injected datasets (external review, 2026-11-13; D76). `tools/outage_all_datasets.py` repeats NB5's outage code unchanged on every NB4 test dataset (1, 3, 7 %, seeds 0–9). It reproduces NB5's 4 datasets exactly (`reproduction_nb5.csv`, difference 0.0).
- **Outage zone-hours relative to the injected truth** (G1–G4 core spans; `outage_all/outage_summary.csv`; mean ± sd over 10 seeds, range):

  | Rate | Naive, every dead state (S0) | Typed, label model (S2) | Typed closer to truth | Wilcoxon p |
  |---|---|---|---|---|
  | 1 % | 1.76 ± 0.46 (1.20–2.56) | **1.16 ± 0.36** (1.00–2.16) | 10/10 | 0.002 |
  | 3 % | 2.01 ± 0.26 (1.49–2.39) | **1.28 ± 0.20** (1.06–1.76) | 10/10 | 0.002 |
  | 7 % | 1.89 ± 0.13 (1.64–2.02) | **1.33 ± 0.07** (1.21–1.45) | 10/10 | 0.002 |
  | all 30 | 1.88 ± 0.32 | **1.26 ± 0.24** | **30/30** | 1.9 × 10⁻⁹ |

  - Distance to the truth = |log(estimate / truth)|; paired Wilcoxon signed-rank test, naive vs typed.
  - S1 (naive interpolation) reports 0 outage hours in every dataset.
- **Outage counts (runs ≥ 3 steps) / truth:** naive 1.84, typed 1.22 (mean over 30).
- **Typed outage zone-steps:** recall 0.998 (0.987–1.000), precision 0.82 (0.46–1.00). The typed count misses 178.7 of 70,411.8 true outage zone-hours (0.25 %).
- **Where the excess comes from** (sums over the 30 datasets, `outage_per_dataset.csv`):
  - typed: 21,171.2 extra zone-hours, of which **21,166.3 (99.98 %) lie inside injected A1 spans** (multi-city zero gaps), 0.0 inside other injected artefacts and 4.8 elsewhere;
  - naive: 62,698.5 extra zone-hours, 62,693.7 (99.99 %) inside injected artefact spans.
  - This confirms F52's explanation directly: the typed residual is exactly the A1 → G1 confusion (F47), and nothing else.
- **Spread:** the typed ratio is ≤ 1.05 in 6 of 30 datasets. Its worst case (1 %, seed 6: 2.16, precision 0.46) is one dataset whose A1 gaps are long relative to its small true outage time (564 zone-h). The typed mean rises with contamination (1.16 → 1.28 → 1.33) as A1 events become more numerous; its spread falls (sd 0.36 → 0.07).
- **The 4-dataset mean (1.36) was on the high side:** the 30-dataset mean is 1.26. NB5's 3 %, seed 1 dataset (1.76) is the 3 % maximum.
- **Paper:** "typed counting cuts the outage-time overstatement from +88 % to +26 % on average and is closer to the truth in all 30 injected datasets (Wilcoxon p = 0.002 at every rate). Its remaining excess is entirely multi-city zero gaps labelled as outages." Cite this instead of F52's 4-dataset numbers; keep the real-data 4.15× (F51) next to it.

### F60 — The Marrakech labels do not depend on the fusion weight β in [0.4, 1] — *solid*
- **Why:** Marrakech is outside the injection benchmark, so its β (0.5) is untuned (D80).
- **Check** (`tools/marrakech_beta_sensitivity.py` → `results/end_model_v1/marrakech_beta_sensitivity.csv` and `.json`): NB3's stored q and f (4 decimals) with NB3's feasible sets and D50 abstention reproduce every stored rule-item label at β = 0.5 (281/281).
- **Marrakech (55 rule items: G3 35, G4 13, A3 7):**
  - the label-model and end-model arg max agree on 53 of 55; the 2 disagreements (D003, D011) are G3 (q) vs G4 (f), fused to G3;
  - β ∈ {0.4, …, 1.0}: 0 labels change relative to β = 0.5;
  - β ∈ {0.1, 0.2, 0.3}: 1 label changes (G3 → G4); β = 0: 2 change.
  - **The result holds for every real β ≥ 0.4, not only on the grid:** for each item, the log-ratio of two classes' fused scores, β log(q_a/q_b) + (1 − β) log(f_a/f_b), is linear in β, so a label that wins at β = 0.4 and at β = 1 wins on the whole interval; abstaining items (p = q) do not depend on β. Below 0.4 at most two items change, both G3 → G4.
- The released catalogue (`results/catalogue_final/catalogue.csv`) carries the same 35 / 13 / 7 Marrakech labels.
- **Paper:** §4.7 states the reason and the insensitivity in one sentence.

### F61 — The deep multivariate baselines GDN and USAD lose to the rules, to the main detector and to STL in every seed — *solid*
- **Test period, event F1 (eq. 17), mean ± sd over 10 seeds, 1 % / 3 % / 7 %** (`results/benchmark_v1/deep_baselines/table_deep_baselines.csv`):
  - GDN 0.370 ± 0.044 / 0.563 ± 0.028 / 0.707 ± 0.025; USAD 0.286 ± 0.046 / 0.413 ± 0.025 / 0.517 ± 0.038;
  - for reference (NB4): main detector 0.644 / 0.813 / 0.854; rules alone 0.863 / 0.879 / 0.896; rules + detector 0.721 / 0.876 / 0.906; STL + MAD 0.625 / 0.735 / 0.771; LOF 0.570 / 0.720 / 0.698; Isolation Forest 0.211 / 0.462 / 0.605.
- **Paired Wilcoxon over seeds** (`wilcoxon_deep_baselines.csv`): the main detector, the rules, the full method and STL + MAD beat both GDN and USAD in 10 of 10 seeds at every rate (p = 0.002), on F1 and on zone-strict F1. With each method's own background alarms excluded, the same holds, except GDN vs STL + MAD (STL better in 9/10, 10/10, 8/10; p = 0.010, 0.002, 0.037).
- **Against the other classical baselines:** GDN beats Isolation Forest at every rate (10/10, 10/10, 8/10) and loses to LOF at 1 % and 3 % (10/10), not significantly at 7 % (p = 0.43). USAD beats Isolation Forest at 1 % only and loses to LOF at every rate.
- **Other views:** own-background-excluded F1 GDN 0.681 / 0.702 / 0.740, USAD 0.427 / 0.448 / 0.475; zone-strict GDN 0.287 / 0.456 / 0.568, USAD 0.232 / 0.349 / 0.405; step AUC-PR GDN 0.177 / 0.282 / 0.353, USAD 0.129 / 0.321 / 0.422; real-data alarms GDN 366, USAD 243 (main detector alone 191).
- **What they find:** GDN finds the multi-city zero gaps (recall A1 0.99 / 0.98 / 0.96) and injected regional outages (G1 1.00) but almost no single-zone fill (A3 0.00 / 0.01 / 0.01) and a quarter of the simultaneous fills (A2 0.25–0.29): a hold or a straight line is easy to forecast. U_SHOCK recall GDN 0.26–0.32, USAD 0.06–0.09 (main detector: see §9.3). Onset error: GDN 20 min, USAD 90–95 min.
- **Development:** F1 alone 0.567 (GDN) and 0.446 (USAD) at their tuned settings.
- **Paper:** "Two deep multivariate detectors, GDN and USAD, run with their authors' settings, reach event F1 of 0.37–0.71 and 0.29–0.52, below the rules (0.86–0.90), the main detector (0.64–0.85) and STL (0.63–0.77) in every seed." It supports the paper's point that acquisition artefacts are better found by their signatures than by generic anomaly scores. Caveat: the benchmark favours the rules (D84), and GDN forecasts poorly on this data (F63).

### F62 — On all 30 test datasets, typed cleaning gives the best LightGBM forecasts in 28–30 of 30 datasets; the naive forecaster still prefers interpolation — *solid* (confirms F53 and F54; cite these numbers)
- **MASE, mean over 30 datasets, S0 / S1 / S2 / S3** (`results/downstream_v1/forecast_all/forecast_summary.csv`; Wilcoxon over datasets):

  | Model | Horizon | Subset | S0 / S1 / S2 / S3 | S2 better than S0 | S2 better than S1 |
  |---|---|---|---|---|---|
  | LightGBM | 1 day | after anomaly | 1.295 / 1.140 / **1.058** / 1.052 | 29/30 (p 3.7e-9) | 29/30 (p 4.7e-7) |
  | LightGBM | 1 day | all | 1.174 / 1.076 / **1.052** / 1.051 | 30/30 (p 1.9e-9) | 29/30 (p 3.2e-6) |
  | LightGBM | 1 h | after anomaly | 0.696 / 0.636 / **0.625** / 0.619 | 29/30 (p 3.8e-6) | 29/30 (p 3.8e-6) |
  | LightGBM | 1 h | all | 0.653 / 0.625 / **0.625** / 0.620 | 29/30 (p 3.8e-6) | 28/30 (p 4.4e-6) |
  | naive | 1 day | after anomaly | 2.036 / **1.377** / 1.499 / 1.448 | 30/30 (p 1.9e-9) | 10/30 (S1 better, p 6.1e-4) |
  | naive | 1 h | after anomaly | 0.995 / **0.920** / 0.939 / 0.923 | 30/30 (p 1.9e-9) | 0/30 (S1 better, p 1.9e-9) |

- **Diebold–Mariano per dataset, LightGBM** (`dm_summary.csv`): S2 significantly better than S1 in 26/30 (1 h after anomaly), 25/30 (1 h all), 14/30 (1 day after anomaly) and 19/30 (1 day all); significantly worse in at most 1/30. Against S0: 28, 29, 19, 26 of 30.
- **Weak spot:** at 3 %, 1 h, S2 beats S1 in 9 of 10 datasets but not significantly (p = 0.084), and its mean MASE is higher (0.645 vs 0.631): one dataset carries a large S2 loss.
- **S2 vs the oracle S3:** MASE gap 0.0006–0.0059 for LightGBM (about 0.5 % day-ahead after an anomaly).
- **Naive reference (F54 confirmed):** S1 beats S2 at 1 h in 30/30 datasets and at 1 day in 20/30; S2 beats S0 in 30/30. DM: S2 significantly worse than S1 in 21/30 at 1 h and 11/30 at 1 day.
- **The 4-dataset means (F53) were close:** e.g. LightGBM day-ahead after an anomaly S1 1.107 → 1.140 and S2 1.056 → 1.058 over 30.
- **Paper:** "Over 30 injected datasets, type-aware cleaning gives the lowest LightGBM error in 28–30 of them (Wilcoxon p ≤ 5 × 10⁻⁶) and comes within 0.5 % of an oracle day-ahead; with a forecaster that cannot read the event indicator, interpolation remains better for forecasting, at the cost of the outage statistics (F59)."

### F63 — GDN, run as released, forecasts the feeders 7–14 times worse than the last value — *solid*
- **Rule-clean windows of the real series, min-max scaled units** (`results/benchmark_v1/deep_baselines/gdn_forecast_vs_persistence.csv`, `tools/gdn_forecast_check.py`): MSE GDN 0.0042 / 0.0049 (model trained before Jul 2023; in / out of sample) and 0.0027 / 0.0025 (trained after), vs 0.00035–0.00038 for the last value and 0.0007–0.0008 for the mean of the last 5 values: 6.7–13.8 × persistence.
- **Mean attention weight on the zone itself:** 0.22 and 0.51 (the rest goes to its 4 learned neighbours). In GDN's attention the target's own term is the same for every neighbour it scores, so a node cannot learn to attend to itself specifically; its forecast is a blend of feeders, and the shared output layer flattens it.
- Before the min-max scaling was added (D82) the ratio was about 10 × in unscaled units; the scaling made the inputs faithful but did not remove the gap.
- **Not a training failure:** both folds early-stopped (29 and 26 epochs) at a stable training loss; the code follows the official layers.
- **Paper:** state GDN's forecast error next to persistence (supplement), so that the comparison is seen to use GDN as released. It agrees with F42: on few-zone feeder systems, mixing neighbours does not help; our TCN-GAT reads each zone's own history through its temporal network and uses the graph only for the neighbours' current values. If the static-attention argument is used in the text, cite Brody et al. (ICLR 2022) after checking it.
