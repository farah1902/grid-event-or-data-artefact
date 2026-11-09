# Paper handoff — state of the science for the writing agent

Read this first if you are writing the paper. It says what the project has established, what changed relative to
the research guide (`docs/research_guide.md`), what the paper can claim now, and what is still missing. Every
claim points to a finding (F…) in `docs/findings.md` or a decision (D…) in `docs/decisions.md`. Every number is in
`docs/results_summary.md`.

**Status: 2026-11-09.**
- Done:
  - rule engine v1 (19 rules);
  - the label model (constrained Dawid–Skene);
  - **the detector and end model (NB3)**, reference run with LightGBM 4.6.0 and the structural-zero fix (D51, D52). An independent Colab run exposed a scale-collapse bug in the zone-level score (F35); it is fixed, and the hierarchy numbers below are the corrected ones.
- **NB4 written and tested, awaiting the author's Colab run:** the learned-graph TCN-GAT (guide eq. 13 as written; D53), the hybrids (D59) and the injection benchmark (D54–D58, D60). Its results go into results_summary §9 and new findings.
- **Main detector changed (2026-11-09, D61): the TCN-GAT multi-scale graph residual detector.**
  - It was chosen on development datasets (seeds 100–104), with every detector and baseline tuned the same way (D60). Development F1 alone: 0.786 vs 0.759 for LightGBM, and it wins in all 10 cells (F39).
  - LightGBM, its hybrids with a learned correction and the plain average are ablations.
  - NB4 §8b produces the south catalogue with the main detector (`results/main_detector/`). NB3's south detector numbers describe the LightGBM detector.
  - The NB4 evaluation protocol was also corrected: the scoring area no longer favours the LightGBM detector (F36).
- Not done: downstream forecasting (NB5), the Tetouan transfer (NB6) and the final figures (NB7).

## 1. The paper in one paragraph (current evidence)

Feeder telemetry from three southern Moroccan cities that share one data logger contains far more data artefacts
than grid events. The artefacts take four mechanical forms:
- zero fills;
- held (frozen) values;
- **straight-line interpolation**, a signature the original plan did not anticipate and which is the most common fill mechanism in this data;
- clock errors, where the logger follows European daylight saving in autumn.

The large "outages" in the record are compound acquisition failures: holds or straight-line fills that turn into
exact zeros, with held and zeroed zones side by side in different cities. No clean regional outage survives
(F03, F07). About one in five dead runs "restores" through a synthetic straight line, so restoration dynamics are
not trustworthy evidence (F05, F16).

Hierarchical rules can still separate the cases, and a constrained Dawid–Skene label model turns their sparse,
single-label votes into stable, calibrated probabilities. The guide's unconstrained formulation is not identifiable
on these votes (F20–F22).

A multi-scale residual detector split into region, city and zone parts (eq. 14) places **zero-fill artefacts and
outages** at the right hierarchy level (multi-city dead items: 3/3 at the region; single-zone dead items: 92 % at
the zone). It does **not** do so reliably for **fill** artefacts, whose residuals are zone-specific by construction
(multi-city fills at the region 1/6, city-wide fills at the city 55 %; F30).
Rules and detector are therefore complementary.

The detector also finds 290 anomalies that no rule covers. Most fall outside the typology:
- partial outages just above the dead threshold;
- sub-30-min system-wide disturbances;
- sustained surges.

This points to typology extensions and to the ε sensitivity question (F32).

In the southern system the provisional labels give about 2,600 artefact zone-hours against about 300 grid-event
zone-hours. Counting every zero as an outage would overstate outage time about four-fold (F26, provisional until
NB4 and NB5).

## 2. Suggested storyline

1. **Problem:** utilities clean feeder telemetry blind (guide). Real-data motivation figures: Fig 3 (C05/C06), Fig 4 (C12) and E1b (C09). Put them early.
2. **Typology** with measurable signatures at hierarchy levels, extended with the linear-fill signature (F01). New typology table and Fig 2.
3. **Candidate generation:** per-step states (zero, noise floor, hold, linear fill), typed items and episodes (methods §2–3).
4. **Rules** (methods §4): 19 rules, including the interpolation family. Fig 7.
5. **Label model:** why the guide's equations fail (F20, F21), the constrained model, stability and recovery (F22), robustness (F24). E12, E14.
6. **Detector and end model** (NB3, methods §6–7):
   - forecast residual;
   - phase-aligned MODWT bands;
   - residual hierarchy (Fig 8): it works for outages, not for fills (F30);
   - detector-only candidates and typology gaps (F32, E18);
   - the end model reproduces the label model (F33) and corrects the threshold of one rule (F34).
   - Then the **(pending)** injection benchmark against baselines (NB4).
7. **Case studies on real data:** the catalogue (Table 4 draft in results_summary §7), C01/C09 re-reads, synthetic restoration ramps, the daily logger freeze.
8. **(Pending)** downstream: forecasting error and outage statistics, naive vs typed cleaning (NB5). F26 is the preview.
9. **(Pending)** Tetouan transfer (NB6).
10. **Threats and limitations** (§6 below).

### Text the author asked to include in the paper

- **On the graph nowcast (Methods, detector; 2026-11-08):** "The nowcast of eq. 13 is a fully connected 'graph' with no learned edges: the current value of every other zone enters the tree model as a plain feature. It adds nothing (clean-data MAE 0.0292 vs 0.0288 for the forecast residual), so it is used only as a comparison and as an end-model feature, not as the main residual." Sources: D40, F29, results_summary §8. The learned-graph model (TCN-GAT, guide eq. 13 as written) is evaluated in NB4; report its result next to this sentence.
- **On the main detector (Methods, detector; 2026-11-09, D61):** "The main detector is a multi-scale graph residual detector.
  - A TCN-GAT, a causal temporal convolutional network with graph attention over the zones' current values and learned cross-city edges, predicts each southern zone.
  - Its residual is split into phase-aligned MODWT bands and into region, city and zone parts.
  - Events are formed by smoothing, a percentile threshold and run merging, tuned on separate development data, as for every compared method."
  - **Pair it with three honest qualifiers:**
    - the graph does not improve the point forecast (MAE 0.0294 vs 0.0288 for LightGBM; a learned correction on LightGBM converges to zero, F37);
    - its advantage is event detection with fewer fragmented false alarms (F38, F39), not step-wise AUC-PR, where STL + MAD and LightGBM rank higher (F39);
    - under strict counting no detector raises the rules' event F1 on the rules' own typology (F40).
  - Final numbers come from NB4 (test seeds 0–9).

## 3. Corrections to the guide (continuing the guide's own table, #1–13)

These are changes to the **guide's plan**, found by running it on the real data. The guide's corrections #1–13 stand.

| # | Guide item | Problem found | Fix | Ref |
|---|---|---|---|---|
| 14 | Typology A1–A4 (zeros, holds, stuck, clock) | Straight-line interpolation is a common fill mechanism (85 pure and 16 mixed fill items of 155) and is invisible to hold detection | New state (eq. 21); A2/A3 cover holds **and** linear fills; new rules R19–R21 | F01, D07, D26 |
| 15 | C05 = L, B, F4 holds | F1–F3, F5–F7 are linearly filled over the same span: all 15 zones | Episode EP056: A2, A2 → A1 | F02 |
| 16 | C09 = G1 candidate ("L normal") | L is linearly interpolated during the B/F zeros | A1 (0.93); no G1 left in the real data (R7 fires 0×) | F03, F07 |
| 17 | C01 = noise-floor feeder outage | Zeros → straight line → zeros | Re-segmented into 4 items | F06 |
| 18 | Restoration ratio, ramp and overshoot (eq. 3, R1, R5, R7, H2) | 21 % of dead runs restore through a synthetic straight line. C02's r = 0.22 was an artefact | Measure after the ramp (D22). R5 turns out uninformative (log(a/b) = 0.12) | F05, F16 |
| 19 | Dead = x ≤ 5 % x̂ (eq. 4); v0 also required an exact zero | v0 dropped exactly the noise-floor runs that H1 is about | No exact-zero requirement | D15 |
| 20 | Rules vote on "events" | Large events are compound (fill → zero), so one label per event cannot describe them | Typed items (dead, fill, clock, transfer) linked into episodes | D13 |
| 21 | R4: any step with one zone dead and another held | A 1-h stuck sensor during a 108-h outage would vote A1 | Co-extensive = time IoU ≥ 0.5 | D19 |
| 22 | R15: \|δ\*\| ≥ 50 min | Fires on 18/33 dates, including Ramadan dates and fits with correlation 0.09–0.30 | Fit-quality guard (corr ≥ 0.9, gain ≥ 0.05) → 6 votes | D21, F12 |
| 23 | Label model eq. 10–11 (fired rules only) | With single-label rules, θ = 1 for every class, so votes carry no information | Abstention is an observed output (eq. 24) | D28, F20 |
| 24 | Unconstrained Dawid–Skene, "identifiable because most items get several votes" | Most items get 1–3 votes and rules rarely co-fire. The model is unstable (63 % restart agreement) and loses class meaning | Feasible classes by level, applicability domains, constrained one-coin parameters, defining-rule and π priors (eq. 24–26) | D29–D34, F21, F22 |
| 25 | Equal number of all-abstain N windows in the label model | They add no information once classes are gated by level | Deferred to the end model (NB3) as negatives | D35 |
| 26 | Clock shift "+50 to +60 min" | The sign convention was not defined | δ\* < 0 means stamped earlier after the date; Oct 2022 = −60 | D08, F04 |
| 27 | Hold minimum 6 steps | Laâyoune has a daily 30–50 min freeze in all zones (218 episodes) below the threshold | Keep 6; sensitivity sweep; report as a finding | D18, F09 |
| 28 | Eq. 8 windows [d, d+13] vs [d−14, d−1] | v0 uses [d+1, d+14] vs [d−13, d] | Documented; one-day shift, no effect on the C11 result | methods §3 |
| 29 | R10 window "06:00–11:00" | v0 uses start hours 6–11 inclusive | Documented (06:00–11:59) | D24 |
| 30 | TCN-GAT nowcaster | Not needed to test the hierarchy idea; heavy on CPU | LightGBM (Huber) nowcasts, the guide's own fallback | D39 |
| 31 | Eq. 13 graph nowcast (neighbours' current values) as the residual | Adds nothing on clean data (MAE 0.0292 vs 0.0288); also does not absorb masked logger artefacts | Forecast residual as main; the nowcast is kept as a comparison and a feature | D40, F29 |
| 32 | MODWT bands of ρ, one predictor per band | Five predictors per zone. Causal coefficients smear events by up to 18 h | MODWT of the residual, phase-aligned by measured group delays | D42, F31 |
| 33 | "An artefact on the logger moves the region part" (eq. 14 rationale) | True for zero fills; false for holds and linear fills (zone-specific drift) | Report hierarchy accuracy by kind; rules handle fills | F30 |
| 36 | Eq. 15 robust z over the hierarchy parts | A median over an odd number of zones makes one zone's v exactly 0; with these zeros in the scale estimate, the MAD collapses (B1, z = 15,182) and every small city's zone scores are inflated | Exclude structural zeros from the median and MAD | D51, F35 |
| 34 | Detector adds coverage within the typology | Detector-only anomalies are mostly outside it (partial outages, short interruptions, surges) | Report them as untyped; propose typology extensions; ε sweep in NB4 | F32 |
| 35 | Fusion eq. 16 for every class | The end model cannot learn a class with one example out of fold (the G2 item flipped to G3) | End-model abstention on classes with < 3 items of training mass | D50, F34 |

## 4. Contributions — status against the guide's list

| # | Guide contribution | Status | Evidence |
|---|---|---|---|
| 1 | Typology (4 artefact + 5 grid-event types) with measurable signatures | **Done and extended** (linear-fill signature) | F01–F06, methods §2 |
| 2 | Hierarchical weak supervision without manual annotation, calibrated probabilistic labels | **Label model done.** Stability and synthetic-recovery calibration shown (ECE 0.033). Calibration against known types is pending (NB4) | F20–F24 |
| 3 | Multi-scale residual detector split into region/city/zone parts | **Done, now with the learned graph as the main detector (D61):** TCN-GAT residual, multi-scale bands, region/city/zone hierarchy and tuned event formation. It is best on development event F1 (0.786 vs LightGBM 0.759, STL 0.717, LOF 0.648, Isolation Forest 0.473; F39), but not on step-wise AUC-PR. Hierarchy accuracy by kind (NB3, LightGBM residual): works for dead and zero-fill events (3/3, 92 %), only partly for fills. Test results: NB4 | F28–F32, F35–F40, Fig 8, Fig 9, E18, E20 |
| 4 | Released typed event catalogue for UCI 1158 | Draft exists (`results/labels_v1/q.csv`, 327 items, plus episodes). Release after NB4 validation | results_summary §6–7 |
| 5 | Type-aware cleaning improves forecasts and outage statistics | Not started (NB5). Preview: naive zero = outage overstates outage time ≈ 4.2× (provisional) | F26 |
| 6 | Transfer test on Tetouan | Not started (NB6) | — |
| new | Methodological: the guide's Dawid–Skene fails on sparse single-label rule sets; a constrained, level-gated variant works | Done | F20–F22, D28–D34 |
| new | Empirical: straight-line interpolation and synthetic restoration ramps in utility telemetry; a daily logger freeze | Done | F01, F05, F09 |

## 5. Research questions and hypotheses — evidence so far

| Item | Status | Evidence |
|---|---|---|
| RQ1: can the hierarchy alone give reliable type labels? | Partly. Labels are stable and agree 98 % with majority vote. **Reliability vs truth: NB4** | F22, F23 |
| RQ2: which signatures separate events from artefacts? | Holds and linear fills (log(a/b) 3.4–4.0) and simultaneity with fill (R1, R3, R4, R21) are strong. Exact-zero share (R6, 2.2) is moderate. **Restoration overshoot (R5, 0.12) is uninformative.** Conservation: one example | F16, results_summary §6 |
| RQ3: does learning beat rules alone and unsupervised detectors? | On real data the end model reproduces the label model (94.7 % out of fold; 95.7 % without detector features). Detector features add no agreement with rule-derived targets, and they cannot by construction. It corrects one rule threshold (3 vote-less linear fills → A3). **Development data (F39, F40):** the graph detector beats every unsupervised detector on event F1. Under strict counting, adding it to the rules does not raise event F1 (0.863 vs 0.888): it adds recall on what the rules miss at a false-alarm cost. **Test: NB4** | F33, F34, F39, F40 |
| RQ4: does type-aware cleaning help? | Pending (NB5). Preview F26 | F26 |
| RQ5: transfer without re-tuning? | Pending (NB6) | — |
| H1: acquisition failures → exact zeros or simultaneous holds; de-energised feeders → noise floor | **Supported and extended.** All 3 multi-city zero fills have η = 1.0 and come with holds or linear fills; 84 of 126 dead items have η < 0.9 and are mostly single-zone. Caveat: some noise floors are linear fills (D16) | F03, F06, F17 |
| H2: real outages restore with a ramp or overshoot; gaps return straight to expected | **Weak / threatened.** Synthetic ramps (21 %); R5 uninformative | F05, F16 |
| H3: transfers conserve current; faults and gaps don't | One clean case (κ = 0.07); the 12 other level-shift candidates have κ ≥ 0.72 | F19 |

## 6. Threats to validity and limitations (current)

1. **No ground truth on real data.** All real-data labels are provisional. Validation = injection (NB4) plus external records, which the user chose not to pursue (R17/R18 not implemented). Say this plainly.
2. **Circularity.** Labels come from rules, so agreement with rules (98 %) is not accuracy. The parameter-recovery test only checks identifiability under the model's assumptions (D36).
3. **G1 has no real example** (F07). G1 performance will rest entirely on injected events.
4. **R10 window overlaps the morning linear-fill window** (F08). Some G4 may be data maintenance, and G4 is driven by a defining rule.
5. **Item-level labels ignore episode context** (F25). For example, the C12 tail zero on L1 is labelled G4 (0.96). An episode-context rule or the end model should fix this.
6. **Marrakech** dead items are mostly whole-kW noise-floor runs in one small zone (F15). Report the south separately.
7. **Thresholds** were set on the same data. The sensitivity sweep (guide ablation 6) is still to be run on injected data.
8. **Clock.** Timestamps are uncorrected (D11). R10 and all time-of-day features are in recorded time. The logger's clock regime is only partly understood (F04).
9. **Label-model priors matter.** The defining-rule prior changes 39 % of dead labels (G3/G4 split) (F24). Report it as a modelling choice with its sensitivity.
10. **Small classes:** A1 has 3 items, G2 1 and G5 1 on real data. No per-class real-data statistics are possible; use case studies.
11. **Run-to-run sensitivity of the detector:** the detector-only list and γ depend on the predictor backend and on the scale fix (311 → 323 → 290 candidates over three runs; γ 37.2 → 33.3 → 25.5). Clean-data MAE and the outage-localisation result are stable. Report detector-only counts as approximate, and the hierarchy result by kind (F30, F35).
12. **The residual hierarchy does not localise fill artefacts reliably** (F30). Don't present eq. 14 as a general artefact localiser.
13. **Detector-only candidates are untyped** (F32). The end model's "N" for them means "no typed class fits", not "normal".
14. **End-model circularity:** trained on q, the end model can at most reproduce the rules on real data (F33). Its benefit has to be shown on injected data.
15. **Median hierarchy over few zones** (Boujdour has 3): one zone is always the city median, so its zone part is exactly 0 a third of the time. Scales must be estimated on informative steps (D51, F35).
16. **Design chosen on injected development data.** The main detector and all event-formation settings were chosen on seeds 100–104 of the same injector as the test seeds. The datasets differ, but the signature generator is the same, so the test measures performance on these signatures, not on unseen kinds of event (D60).
17. **Strict false-alarm counting** treats every unflagged real-data alarm as false, although about half of NB3's candidates looked like real surges or partial drops (F32, F40). NB4 reports a second view (each method's own real-data detections excluded) and the real-data alarm counts.
18. **Tuning trades short shocks for precision** (F38): with the tuned event formation, unflagged-shock recall drops from 0.61 to 0.10 for the graph detector. NB4 reports the untuned rows too.

## 7. Claims the paper must NOT make (yet)

- Any accuracy, F1 or calibration number "on real data". Only synthetic recovery and, later, injection results exist.
- That a regional outage (G1) was detected in the data.
- That restoration dynamics (ramp, overshoot) distinguish outages from artefacts.
- The 4.2× outage-time overstatement as a final result (provisional until NB4 and NB5).
- Any causal link between events and the Boujdour II commissioning (26 Jan 2023) or the 400 kV switch (Jul 2023). These are coincidences in time only; external validation was not pursued.
- Marrakech outage counts as physical outages.
- Results "in local time": no clock correction has been applied.
- That the residual hierarchy localises all artefacts (only zero fills and outages; F30).
- That detector-only candidates labelled N are normal (F32).
- That detector features improve the end model on real data (they don't change agreement; F33).
- That the graph improves prediction accuracy (F37), or that the graph detector is best at step-wise AUC-PR (F39).
- That the detector raises event F1 over the rules under strict counting (F40), unless NB4's test seeds show it.
- Development-seed numbers as results: cite NB4's test seeds.

## 8. What is still missing (in roadmap order)

| Notebook | Content | Will provide |
|---|---|---|
| NB3 | **Done** (LightGBM 4.6.0 reference run with the structural-zero fix): residual hierarchy, Fig 8, detector-only candidates, end model, fusion | contribution 3 |
| NB4 | **Written and tested; awaiting the Colab run.** Main detector: TCN-GAT multi-scale graph residual detector, chosen on development seeds with every detector tuned (D60, D61; `tools/dev_select_detector.py`). TCN-GAT with a learned graph (D53), hybrids (D59); injection of observed signatures at 1/3/7 % × 10 seeds, including linear fills, compound fill → zero, unflagged multi-zone shocks and partial outages (D54); baselines (rules, STL + MAD, Isolation Forest, LOF, majority vote; D57); metrics (eq. 17–18); ablations (pipeline, rule families, hierarchy, scale, graph, nowcast, ε / hold / τ) and hard negatives | Tables 5–7, Figs 9–11, E20–E21; first real validation |
| NB5 | Forecasting with S0–S3 cleaning, DM test, outage-hours check | Table 8, Fig 12; confirms or refutes F26 |
| NB6 | Tetouan transfer with frozen rules | Table 9 |
| NB7 | Final figures (basemap, typology diagram, framework diagram) | Figs 1, 2, 6 |

**Injection additions required by the findings (including NB3):**
- **unflagged** multi-zone shared shocks, to compare the forecast and nowcast residuals (F29);
- partial outages (0.05 < ρ < 0.5) and sub-30-min interruptions, to test ε and the 3-step minimum (F32);
- sustained unconserved level shifts (F32);
- straight-line gap fills (single-zone and multi-zone, slopes as observed in `zone_runs.csv`);
- zero spells ending in a straight-line ramp (F05);
- daily short multi-zone freezes (F09);
- G1 events (none exist in the real data).
- events in Boujdour (3 zones), single-zone and city-wide, to check the zone-level scale after the structural-zero fix (F35, D51).

## 9. Writing conventions

- **Terms:**
  - *dead state* (x = 0 or x ≤ 5 % of expected); *exact zero*; *noise floor*;
  - *hold* (identical non-zero values, last value carried forward); *linear fill* or *straight-line interpolation* (constant first difference); *fill* = hold or linear fill;
  - *item* (the unit rules vote on); *episode* (linked items);
  - *zero-fill gap* (A1), *simultaneous fill* (A2), *single-zone fill* (A3), *clock error* (A4);
  - *regional outage* (G1), *city outage* (G2), *unplanned feeder outage* (G3), *planned work* (G4), *load transfer* (G5).
- **Notation:** follow the guide (x, x̂, ρ, η, r_E, π_E, τ_E, S_E, κ, δ\*, q_i(y), θ_r). New: a_rl, b_rl, 𝒴(i), 𝒜(i), S(r, l) (methods §5).
- **Refer to events** by date and zone codes (e.g. "31 Mar 2024, B/F and L3–L5"), with the guide's C-ids where they exist. Item ids (D###…) are internal and change between runs.
- **Times:** "as recorded". Mention in captions that no clock correction is applied.
- **Units:** A for the south, kW for Marrakech. Use ρ or ratios when comparing.
- **Numbers:** cite only from `docs/results_summary.md`. If a number is missing there, compute it from `results/` and add it there first.

## 10. Where things are

| Need | File |
|---|---|
| Every number | `docs/results_summary.md` |
| Method text and equations | `docs/methods.md` |
| Why something was done | `docs/decisions.md` |
| What was found | `docs/findings.md` |
| Column meanings | `docs/data_dictionary.md` |
| Figures and their roles | `docs/figures_and_tables.md` |
| Chronology | `docs/research_log.md` |
| Original plan, equations 1–20, references | `docs/research_guide.md` |
| Probabilistic catalogue | `results/labels_v1/q.csv`, `episodes_labelled.csv` |
| Code | `src/rules_v1.py`, `src/label_model.py`, `src/detector.py`, `src/end_model.py` |
