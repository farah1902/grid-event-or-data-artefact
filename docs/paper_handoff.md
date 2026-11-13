# Paper handoff — state of the science for the writing agent

Read this first if you are writing the paper. It says what the project has established, what changed relative to
the research guide (`docs/research_guide.md`), what the paper can claim now, and what is still missing. Every
claim points to a finding (F…) in `docs/findings.md` or a decision (D…) in `docs/decisions.md`. Every number is in
`docs/results_summary.md`.

**Status: 2026-11-10.**
- Done:
  - rule engine v1 (19 rules);
  - the label model (constrained Dawid–Skene);
  - **the detector and end model (NB3)**, reference run with LightGBM 4.6.0 and the structural-zero fix (D51, D52). An independent Colab run exposed a scale-collapse bug in the zone-level score (F35); it is fixed, and the hierarchy numbers below are the corrected ones.
- **NB4 done (Colab GPU run, 2026-11-09; results_summary §9, findings F41–F50):** the learned-graph TCN-GAT (guide eq. 13 as written; D53), the hybrids (D59) and the injection benchmark (D54–D58, D60) on 30 test datasets (1/3/7 % × seeds 0–9, 8,526 injected events). A no-graph ablation of the main detector was added afterwards on the same datasets (D62, F42). The test seeds are now spent (D63).
- **Main detector changed (2026-11-09, D61): the TCN-GAT multi-scale graph residual detector.**
  - It was chosen on development datasets (seeds 100–104), with every detector and baseline tuned the same way (D60). Development F1 alone: 0.786 vs 0.759 for LightGBM, and it wins in all 10 cells (F39).
  - LightGBM, its hybrids with a learned correction and the plain average are ablations.
  - NB4 §8b produces the south catalogue with the main detector (`results/main_detector/`). NB3's south detector numbers describe the LightGBM detector.
  - The NB4 evaluation protocol was also corrected: the scoring area no longer favours the LightGBM detector (F36).
- **NB5 done (2026-11-10, local; results_summary §10, F51–F54):** downstream test of the cleaning strategies S0–S3 on real and injected data (D64–D66).
- **NB6 done (2026-11-10, local; results_summary §11, F55–F58):** transfer to Tetouan with the method frozen (D68–D70).
- **NB7 done (2026-11-10, local; D72–D75, results_summary §12):**
  - the final catalogue is released (`results/catalogue_final/`);
  - Figs 1, 2 and 6 are drawn;
  - Figs 8 and 9 and E4, E6, E19 and E22 are regenerated with the noted fixes;
  - the paper set (`results/paper/`: 14 main and 28 supplementary figures with draft captions, 28 tables since D76) is ready.
- **External review (2026-11-13; D76, F59):** the naive outage mean corrected to 1.88 (was 1.89, an average of rounded values); outage statistics extended to all 30 NB4 test datasets (typed 1.26× vs naive 1.88×, typed closer in 30/30); Fig 12(c) regenerated from them.
- **The analysis is complete. Next: writing the paper** from this handoff, `results/paper/MANIFEST.md` and results_summary.

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

In the southern system, counting every dead state as an outage gives 1,220.5 zone-hours against 294.0 for the
grid-event labels: a 4.15-fold overstatement (F51).

**Injection benchmark (NB4, 30 datasets, 8,526 injected events; F41–F50).**
- **Detection:** the multi-scale neural residual detector (TCN-GAT) is the best of eight detectors at 3 % and 7 % contamination, and tied at 1 % (F41). Removing its learned graph does not hurt it, so its advantage comes from the neural residual and the tuned event formation, not from the graph (F42).
- **Rules + detector:** adding the detector to the rules raises recall at every rate. Event F1 improves only at 7 %, or when each method's own real-data alarms are not counted (F44).
- **Attribution:** macro-F1 0.91–0.94, calibrated (ECE 0.07–0.10), but no better than majority vote on these signatures (F46). The main error is multi-city zero gaps read as regional outages (F47).

**Downstream (NB5; F51–F54).**
- **Outages:** on the 30 injected test datasets, typed outage counts are 1.26× the truth (± 0.24), against 1.88× (± 0.32) for naive counting; typed is closer to the truth in 30/30 datasets, and its whole excess is multi-city zero gaps read as outages (F59).
- **Forecasts:** typed cleaning gives the best forecasts after anomalies, within about 1 % of an oracle, for a forecaster that reads the event indicator.

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
   - Then the injection benchmark (NB4): Table 5 and Fig 9 (detectors and baselines), then **Table 7e and Fig 9b, the ablations of the main detector, with the learned-graph ablation first** (D67, F42, F43). Table 6 and Figs 10–11 cover attribution.
7. **Case studies on real data:** the catalogue (Table 4 draft in results_summary §7), C01/C09 re-reads, synthetic restoration ramps, the daily logger freeze.
8. **Downstream (NB5):**
   - Counting every dead state as an outage overstates southern outage time 4.15× on the real data (F51). On the 30 injected test datasets, the naive count is 1.88× the truth and the typed count 1.26×, closer in 30/30 (p = 1.9 × 10⁻⁹); 99.98 % of the typed excess lies inside injected A1 spans, i.e. the A1 → G1 confusion (F59; first measured on 4 datasets in F52).
   - Typed cleaning gives the best LightGBM forecasts, mainly after anomalies (day-ahead MASE −14 % vs naive interpolation on the real data), and comes within about 1 % of an oracle (F53).
   - A model-free forecaster prefers erasing outages, so the typed labels should be given to the forecaster, not only used for cleaning (F54).
9. **Tetouan transfer (NB6).**
   - Show **Fig 14** (the protocol: what is frozen, what is re-estimated from unlabelled data, what one city changes) before the results. Every adaptation is listed in `docs/transfer_protocol.md` (D71).
   - Frozen rules raise zero false items on a clean year of another city's data (F55).
   - The full method reaches F1 0.945 / 0.919 / 0.890 at precision 0.98–1.00 and beats the rules everywhere (F56).
   - On one year of 3 zones, the data-efficient LightGBM is the better stand-alone detector at 3–7 % (F57).
   - Attribution transfers for 5 of 6 classes (macro-F1 without A1 0.95–0.98). A1 fails because its evidence is cross-city (F58).
10. **Threats and limitations** (§6 below).

### Text the author asked to include in the paper

- **On the graph nowcast (Methods, detector; 2026-11-08):** "The nowcast of eq. 13 is a fully connected 'graph' with no learned edges: the current value of every other zone enters the tree model as a plain feature. It adds nothing (clean-data MAE 0.0292 vs 0.0288 for the forecast residual), so it is used only as a comparison and as an end-model feature, not as the main residual." Sources: D40, F29, results_summary §8. The learned-graph model (TCN-GAT, guide eq. 13 as written) is evaluated in NB4; report its result next to this sentence.
- **On the main detector (Methods, detector; 2026-11-09, D61):** "The main detector is a multi-scale graph residual detector.
  - A TCN-GAT, a causal temporal convolutional network with graph attention over the zones' current values and learned cross-city edges, predicts each southern zone.
  - Its residual is split into phase-aligned MODWT bands and into region, city and zone parts.
  - Events are formed by smoothing, a percentile threshold and run merging, tuned on separate development data, as for every compared method."
  - **Pair it with four honest qualifiers:**
    - **the learned graph adds no detection skill:** the same detector without the graph is equal or slightly better on the test seeds (F1 0.671 / 0.817 / 0.857 vs 0.644 / 0.813 / 0.854, significant at 1 %; F42). The graph's contribution is the interpretable dependency map (E20);
    - the graph does not improve the point forecast (MAE 0.0294 vs 0.0288 for LightGBM; a learned correction on LightGBM converges to zero, F37);
    - its advantage is event detection with fewer fragmented false alarms (F38, F39), not step-wise AUC-PR, where STL + MAD and LightGBM rank higher (F39);
    - under strict counting no detector raises the rules' event F1 on the rules' own typology (F40).
  - **Test numbers (NB4, seeds 0–9):** F1 0.644 / 0.813 / 0.854 at 1 / 3 / 7 %, best of eight detectors at 3 % and 7 % (p ≤ 0.02), tied at 1 % (F41).
  - **Framing decided by the author (D67, 2026-11-10):**
    - "TCN-GAT" stays the named main detector.
    - **The learned graph is presented as an ablation:** graph attention on vs off, everything else equal (methods §6.2, Table 7e, Fig 9b, F42).
    - Highlight it as an analysed component that enriches the study: the learned cross-city dependencies (E20) are interpretable, while detection accuracy does not depend on the graph.
    - The detection gain is attributed to the neural residual, the multi-scale scoring and the tuned event formation.

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
| 30 | TCN-GAT nowcaster | Not needed to test the hierarchy idea in NB3; heavy on CPU | NB3 used LightGBM (Huber), the guide's own fallback (D39). NB4 implemented the TCN-GAT with a learned graph (D53); it became the main detector (D61), and the learned graph is presented as an ablation because removing it does not hurt detection (D67, F42) | D39, D53, D61, D67 |
| 31 | Eq. 13 graph nowcast (neighbours' current values) as the residual | Adds nothing on clean data (MAE 0.0292 vs 0.0288); also does not absorb masked logger artefacts | Forecast residual as main; the nowcast is kept as a comparison and a feature | D40, F29 |
| 32 | MODWT bands of ρ, one predictor per band | Five predictors per zone. Causal coefficients smear events by up to 18 h | MODWT of the residual, phase-aligned by measured group delays | D42, F31 |
| 33 | "An artefact on the logger moves the region part" (eq. 14 rationale) | True for zero fills; false for holds and linear fills (zone-specific drift) | Report hierarchy accuracy by kind; rules handle fills | F30 |
| 36 | Eq. 15 robust z over the hierarchy parts | A median over an odd number of zones makes one zone's v exactly 0; with these zeros in the scale estimate, the MAD collapses (B1, z = 15,182) and every small city's zone scores are inflated | Exclude structural zeros from the median and MAD | D51, F35 |
| 34 | Detector adds coverage within the typology | Detector-only anomalies are mostly outside it (partial outages, short interruptions, surges) | Report them as untyped; propose typology extensions; ε sweep in NB4 | F32 |
| 35 | Fusion eq. 16 for every class | The end model cannot learn a class with one example out of fold (the G2 item flipped to G3) | End-model abstention on classes with < 3 items of training mass | D50, F34 |
| 37 | One threshold rule (γ, gap) for every detector | Event formation changes detector rankings more than the predictor does; a fixed rule favours some detectors | Smoothing, percentile threshold and merge gap tuned per detector on separate development seeds, with the same budget for every detector | D60, F38 |
| 38 | Deep forecaster (PatchTST or N-BEATS) in the downstream test | Heavy, and not needed to show that the effect does not depend on the model | A model-free naive reference (persistence, seasonal naive) next to LightGBM | D65, F54 |
| 39 | S2 re-aligns A4 clock stamps | Timestamps are kept as recorded throughout the study | Clock items are excluded from scoring instead | D11, D64 |
| 40 | Tetouan: only the expected-value baseline is re-estimated | A forecast-residual detector also needs predictor weights and a threshold on any new system | Predictor weights and γ (frozen percentile) re-estimated from the unlabelled series as well; rules, label-model parameters and event formation frozen; every adaptation listed in docs/transfer_protocol.md | D68–D71, F55–F58 |

## 4. Contributions — status against the guide's list

| # | Guide contribution | Status | Evidence |
|---|---|---|---|
| 1 | Typology (4 artefact + 5 grid-event types) with measurable signatures | **Done and extended** (linear-fill signature) | F01–F06, methods §2 |
| 2 | Hierarchical weak supervision without manual annotation, calibrated probabilistic labels | **Label model done.** Stability and synthetic-recovery calibration shown (ECE 0.033). Calibration against known types is pending (NB4) | F20–F24 |
| 3 | Multi-scale residual detector split into region/city/zone parts | **Done and tested (NB4).** Main detector: TCN-GAT residual, multi-scale bands, region/city/zone hierarchy and tuned event formation (D61). It is the best of eight detectors at 3 % and 7 % (F1 0.813 and 0.854, p ≤ 0.02) and tied at 1 % (F41). Qualifiers: removing the learned graph does not hurt it (F42); the multi-scale bands help at low contamination, while the hierarchy is a localisation device, not a detection gain (F43); it is not best at step-wise AUC-PR (F39, F41); and it does not improve prediction (F37). Hierarchy localisation: dead items 92 % at the zone, multi-city dead items 3/3 (LightGBM) or 2/3 (neural residuals) at the region (F30, F43) | F28–F32, F35–F45, Fig 8, Fig 9, E18, E20 |
| 4 | Released typed event catalogue for UCI 1158 | **Done (NB7).** `results/catalogue_final/`: 404 entries (327 rule items + 77 detector-only candidates) with label, confidence, p(y), label source and episodes; README data card. Labels validated on injected data (NB4), not against external records | D72, results_summary §12 |
| 5 | Type-aware cleaning improves forecasts and outage statistics | **Done (NB5), with qualifiers.** Outage time: naive counting overstates it 4.15× on the real data; on the 30 injected test datasets the typed count is 1.26× the truth, against 1.88× (naive) and 0 (S1), closer in 30/30 (F59). Forecasts: typed cleaning gives the best LightGBM forecasts after anomalies (real day-ahead MASE 1.061 vs 1.233 for S1 and 1.501 for S0), within about 1 % of the oracle on injected data. Qualifiers: over all test steps the effect is ≤ 3 %, and it needs an indicator-aware forecaster | F51–F54, F59, Fig 12, Table 8 |
| 6 | Transfer test on Tetouan | **Done (NB6).** Without re-tuning: zero false rule items on the clean real year; full-method F1 0.945 / 0.919 / 0.890 (precision 0.98–1.00), above the rules alone at every rate (p = 0.002); attribution macro-F1 0.77–0.79, or 0.95–0.98 without A1 (the single-city limit). Qualifier: the neural detector alone is overtaken by LightGBM at 3–7 % on this small dataset | F55–F58, Fig 13, Table 9 |
| new | Methodological: the guide's Dawid–Skene fails on sparse single-label rule sets; a constrained, level-gated variant works | Done | F20–F22, D28–D34 |
| new | Empirical: straight-line interpolation and synthetic restoration ramps in utility telemetry; a daily logger freeze | Done | F01, F05, F09 |

## 5. Research questions and hypotheses — evidence so far

| Item | Status | Evidence |
|---|---|---|
| RQ1: can the hierarchy alone give reliable type labels? | Partly. Labels are stable and agree 98 % with majority vote. **Reliability vs truth: NB4** | F22, F23 |
| RQ2: which signatures separate events from artefacts? | Holds and linear fills (log(a/b) 3.4–4.0) and simultaneity with fill (R1, R3, R4, R21) are strong. Exact-zero share (R6, 2.2) is moderate. **Restoration overshoot (R5, 0.12) is uninformative.** Conservation: one example | F16, results_summary §6 |
| RQ3: does learning beat rules alone and unsupervised detectors? | **Test seeds (NB4).** The learned detector beats every unsupervised detector (STL + MAD, LOF, Isolation Forest) at 3 % and 7 % and ties at 1 % (F41). Adding it to the rules raises recall at every rate (+0.03 to +0.06; untyped shocks, partial outages and city outages the rules miss), but raises event F1 only at 7 % under strict counting, and at every rate when each method's own real-data alarms are not counted. Zone-strict F1 is lower than the rules' at every rate (F44). In attribution, the end model alone is worse than the label model, and fusion matches majority vote (F46). On real data the end model reproduces the label model (F33) | F33, F34, F41, F44, F46 |
| RQ4: does type-aware cleaning help? | **Yes, where it can.** Outage statistics are much closer to the truth (1.26× vs 1.88× on 30 injected datasets, closer in 30/30; 4.15× naive-to-typed on the real data). Forecasts after anomalies are better than with naive interpolation and close to the oracle, for a forecaster that reads the event indicator. Over all test steps the gain is small (≤ 3 %). For a naive forecaster, interpolating everything (S1) gives lower error but erases outages | F51–F54, F59 |
| RQ5: transfer without re-tuning? | **Yes for detection, mostly for attribution.** The frozen method raises no false rule item on Tetouan's clean year and detects 80–91 % of injected events at 98–100 % precision, above the rules alone everywhere. Five of six classes are typed at 0.85–1.00 accuracy. City-wide zero gaps (A1) become city outages, because the A1 evidence is cross-city by design | F55–F58 |
| H1: acquisition failures → exact zeros or simultaneous holds; de-energised feeders → noise floor | **Supported and extended.** All 3 multi-city zero fills have η = 1.0 and come with holds or linear fills; 84 of 126 dead items have η < 0.9 and are mostly single-zone. Caveat: some noise floors are linear fills (D16) | F03, F06, F17 |
| H2: real outages restore with a ramp or overshoot; gaps return straight to expected | **Weak / threatened.** Synthetic ramps (21 %); R5 uninformative | F05, F16 |
| H3: transfers conserve current; faults and gaps don't | One clean case (κ = 0.07); the 12 other level-shift candidates have κ ≥ 0.72 | F19 |

## 6. Threats to validity and limitations (current)

1. **No ground truth on real data.** All real-data labels are provisional. Validation = injection (NB4) plus external records, which the user chose not to pursue (R17/R18 not implemented). Say this plainly.
2. **Circularity.** Labels come from rules, so agreement with rules (98 %) is not accuracy. The parameter-recovery test only checks identifiability under the model's assumptions (D36).
3. **G1 has no real example** (F07). G1 performance rests entirely on injected events: recall 1.000, attribution F1 0.862 at 3 %, with multi-city zero gaps read as G1 (F47).
4. **R10 window overlaps the morning linear-fill window** (F08). Some G4 may be data maintenance, and G4 is driven by a defining rule.
5. **Item-level labels ignore episode context** (F25). For example, the C12 tail zero on L1 is labelled G4 (0.96). An episode-context rule or the end model should fix this.
6. **Marrakech** dead items are mostly whole-kW noise-floor runs in one small zone (F15). Report the south separately.
7. **Thresholds** were set on the same data. On injected data they are not on a cliff edge (F48): rules F1 0.880–0.891 for ε 0.02–0.10, hold 12 and τ 0–20 min. The exceptions are hold 4 (0.765) and ε 0.02 for the label model (0.819).
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
18. **Tuning trades short shocks for precision** (F38, F45): on the test seeds, the graph detector's unflagged-shock recall is 0.21 tuned vs 0.77 at NB3's event formation (3 %). Its median onset error is 140–168 min. NB4 reports the untuned rows too.
19. **Hierarchy spill-over** (F43, F44): the zone score is the maximum over the region, city and zone parts, so a multi-zone event lifts zones it did not touch. Most detector-only candidates next to injected events sit on the wrong zones (25–75 % time-only matches). As a result, zone-strict F1 of rules + detector stays below the rules alone at every rate.
20. **Injector realism** (F47): injected multi-city zero gaps copy the zero part of the real compound events but not the holds and fills around them. Part of the A1 → G1 confusion is therefore a property of the injector.
21. **Post-hoc ablation** (D62, F42): the no-graph multi-scale row was computed after the test results were seen. It changes no design choice (D63), but say that it was added after the main run. It showed that the graph adds no detection skill.
22. **Spent test seeds** (D63): any design change suggested by NB4 (flat residual, family weights, linking detector-only candidates to episodes) needs development seeds and fresh test seeds.
23. **Single-city transfer** (F58, D69): with one city, A1 and G2 share every cue the rules use, and G1 cannot exist. The Tetouan attribution numbers include this structural failure. Report them with and without A1.
24. **Small-system predictors** (F57): the neural predictors are data-hungry (Tetouan MAE 0.045 vs 0.011 for LightGBM). Stand-alone detector rankings on Tetouan differ from Morocco's.
25. **Tetouan is pre-cleaned** (F55): its real series has no anomaly at all, so its false-alarm rate is a best case, and recall comes only from injected Morocco signatures.

## 7. Claims the paper must NOT make (yet)

- Any accuracy, F1 or calibration number "on real data". Only synthetic recovery and, later, injection results exist.
- That a regional outage (G1) was detected in the data.
- That restoration dynamics (ramp, overshoot) distinguish outages from artefacts.
- "Correct outage statistics" for typed cleaning: it still overcounts by 26 % on average over the 30 injected datasets (up to 2.16× in one; F59). Say "much closer to the truth than naive counting, in every dataset, with a known residual: multi-city zero gaps read as outages".
- That typed cleaning improves forecasts in general: the gain concentrates after anomalies, and over all test steps it is ≤ 3 % (F53). It needs an indicator-aware forecaster (F54).
- Any causal link between events and the Boujdour II commissioning (26 Jan 2023) or the 400 kV switch (Jul 2023). These are coincidences in time only; external validation was not pursued.
- Marrakech outage counts as physical outages.
- Results "in local time": no clock correction has been applied.
- That the residual hierarchy localises all artefacts (only zero fills and outages; F30).
- That detector-only candidates labelled N are normal (F32).
- That detector features improve the end model on real data (they don't change agreement; F33).
- That the graph improves prediction accuracy (F37), or that the graph detector is best at step-wise AUC-PR (F39).
- **That the learned graph improves detection.** The no-graph ablation is equal or slightly better at every rate (F42).
- That the detector raises event F1 over the rules in general. On the test seeds it does so at 7 % under strict counting, and at every rate only with each method's own real-data background excluded. Under zone-strict matching it never does (F44).
- That the graph detector is best "at every contamination rate": at 1 % it is tied with the other model-based detectors (F41).
- That the region/city/zone hierarchy improves detection. The flat residual matches or beats it on event F1 at 1 % and 7 % and on AUC-PR at every rate (F43). The hierarchy's value is localisation (F30).
- That the label model is more accurate than majority vote on injected data: it is not (F46). Its value is calibrated probabilities and stability on sparse real-data votes.
- That the method "transfers without loss": A1 attribution fails in a single-city system (F58), and the neural detector alone loses to LightGBM at 3–7 % on Tetouan (F57).
- That Tetouan's 7 real-data alarms are events: they are unvalidated (F55).
- Development-seed numbers as results: cite NB4's test seeds.

## 8. What is still missing (in roadmap order)

| Notebook | Content | Will provide |
|---|---|---|
| NB3 | **Done** (LightGBM 4.6.0 reference run with the structural-zero fix): residual hierarchy, Fig 8, detector-only candidates, end model, fusion | contribution 3 |
| NB4 | **Done** (Colab GPU run, 2026-11-09; results_summary §9; F41–F50). No-graph ablation added afterwards with `tools/graph_ablation.py` (D62, F42). Test seeds spent (D63) | Tables 5–7, Figs 9–11, E20–E21 |
| NB5 | **Done** (local, 2026-11-10; F51–F54, results_summary §10). LightGBM + naive reference; no deep forecaster (D65). Outage statistics extended to the 30 test datasets on 2026-11-13 (`tools/outage_all_datasets.py`, D76, F59, §10.1b) | Table 8, Fig 12 |
| NB6 | **Done** (local, 2026-11-10; F55–F58, results_summary §11) | Table 9, Fig 13, E22 |
| NB7 | **Done** (local, 2026-11-10; D72–D75): catalogue release, Figs 1, 2, 6, regenerated figures, the paper set | `results/paper/MANIFEST.md`, `results/catalogue_final/` |

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
| Probabilistic catalogue (final, released) | `results/catalogue_final/` (README inside) |
| Paper figures and tables, numbering and draft captions | `results/paper/MANIFEST.md` |
| Label-model output (NB2) | `results/labels_v1/q.csv`, `episodes_labelled.csv` |
| Code | `src/rules_v1.py`, `src/label_model.py`, `src/detector.py`, `src/end_model.py` |
