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

### F26 — Anomalous time is dominated by artefacts — *provisional*
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
