# Decision register

Every design decision taken while building the project, in order. Each entry gives the decision, the alternatives,
the reason, the evidence and where it lives in the code. **[guide deviation]** marks a departure from
`docs/research_guide.md`. The guide's own 13 corrections to the original plan (its section "Corrections to the
proposed plan") are taken as given and are not repeated here.

New decisions take the next free number. Never renumber: D-numbers are cited in code docstrings and notebooks.

---

## Stage 0 — Setup and reproducibility (2026-11-07)

### D01 — Verify that rule engine v0 reproduces before building on it
- **Decision:** re-run `rules_v0.py` into a scratch folder and compare with the shipped `event_catalogue_v0/` CSVs.
- **Result:** all 4 files are identical in shape (220, 421, 13 and 72 rows), columns and values. The only differences are the order of rows that share a timestamp and CRLF line endings. The check was repeated after the repo restructure, again identical.
- **Why:** every later number depends on v0's preprocessing (`regularise`, `expected`).

### D02 — A separate, private git repository for the project
- **Decision:** `git init` inside the project folder. Remote: `github.com/farah1902/grid-event-or-data-artefact` (private).
- **Alternative rejected:** the existing repository rooted at `C:\Users\Dell` (remote `ESA_LandCover_Streamlit`), which would have mixed this research into an unrelated public project.
- **Why private:** unpublished research.

### D03 — Repository layout
- **Decision:** `data/raw`, `docs`, `src`, `notebooks`, `results/{event_catalogue_v0,catalogue_v1,labels_v1,figures}`, `tools`. The guide was renamed to `docs/research_guide.md`.
- **Why:** separate inputs, code, generated results and documentation; notebooks resolve paths from the repo root.

### D04 — Archive duplicates instead of deleting them
- **Decision:** exact duplicates and scratch outputs moved to `_local_archive/` (git-ignored): the root copy of `rules_v0.py`, `zero_events_v0.csv`, `out_check/`, the zips and `__pycache__`. Nothing was deleted.

### D05 — Figures reuse v0 preprocessing
- **Decision:** NB1 imports `rules_v0` (`load`, `regularise`, `expected`) rather than re-implementing it.
- **Why:** figure numbers then match the catalogue exactly. Example: Fig 3 hold run lengths match `stuck_runs.csv` (216–402 points).

### D06 — Hold state for plotting and rules
- **Definition:** a point is "held" if it belongs to a run of ≥ 6 identical non-zero values (counting the first value of the run). This is guide eq. 6 plus the 6-step minimum.
- **Code:** `rules_v1.hold_mask` (same logic as NB1's `hold_mask`).

### D07 — Linear-interpolation signature (new state, not in the guide) [guide deviation]
- **Decision:** a point is "interpolated" if it belongs to a run of ≥ 6 collinear, non-zero points with non-zero slope:
  |Δ²x_t| < 1e-8 · max(1, |x_t|), |Δx_t| > 1e-12, x_t ≠ 0.
- **Why:** in Fig 3, six Foum El Oued zones were straight lines. Their first differences were constant to a standard deviation of about 1e-14 (F01). Real telemetry noise is many orders of magnitude larger than 1e-8, so the tolerance only catches machine-precision straight lines.
- **Alternatives:** looser tolerances would also catch quantised integer ramps (Marrakech); see D17.
- **Code:** `rules_v1.interp_mask`.

### D08 — Clock-offset estimation (guide eq. 9) and sign convention
- **Procedure:**
  - Profile = mean daily shape over 7 days, computed per zone, divided by the zone mean, then averaged across zones.
  - Dead, held and interpolated steps are excluded.
  - "pre" = [D − 7 d, D); "post" = [D + 1 d, D + 8 d), so the change day itself is skipped.
  - δ runs over ±120 min in data-step increments, with a circular shift (`np.roll(post, −k)`).
  - δ* = argmax of the Pearson correlation.
- **Sign convention:** δ* > 0 means the same behaviour is stamped δ minutes **later** after D. The guide's "+50 to +60 min" for Oct 2022 is the same magnitude with the opposite sign (the notebook reports −60).
- **Code:** NB1 `clock_offset`; `rules_v1.clock_offset` (identical logic, plus availability checks).

### D09 — Midday/evening windows for the structural-change figure
- **Definition:** midday = 11:00–14:59 and evening = 18:00–21:59, timestamps as recorded. Dead, held and interpolated steps are removed.
- **Result:** F's ratio goes from 0.89 to 1.03, consistent with the guide's 0.88 → 1.03.

### D10 — Fig 1 map is schematic
- **Decision:** approximate city coordinates on plain lon/lat axes, no basemap dependency. A proper basemap (cartopy/geopandas) is left for NB7.

### D11 — Timestamps are used as recorded
- **Decision:** no clock correction anywhere so far: figures, rules and label model.
- **Why:** the correction needs δ* per period. That is unreliable around Ramadan (F12), and the guide wants results with and without correction.
- **Consequence:** R10's 06:00–11:59 window is in recorded time. Captions say so.

### D12 — Figure style
- **Decision:**
  - Artefacts in warm hues (A1 `#C8553D`, A2 `#F2A541`, A3 `#E9C46A`, A4 `#8C2F39`); grid events in blues (G1–G4) and teal (G5); normal grey.
  - States are shaded spans: hold amber, linear interpolation teal `#2A9D8F`, exact zero red, noise floor purple, missing black.
  - Every figure is saved as PNG (200 dpi) and PDF.
- **Code:** `src/viz.py`.

---

## Stage 1 — Rule engine v1 (2026-11-07)

### D13 — Voting units are typed items, linked into episodes [guide deviation]
- **Decision:** rules vote on four item kinds instead of one event list:
  - `dead`: dead-state runs grouped across zones;
  - `fill`: hold and interpolation runs grouped across zones;
  - `clock`: (city, date) pairs;
  - `transfer`: candidate days.
- Dead and fill items are linked into **episodes**. Two items link if they overlap or touch (gap ≤ 10 min) and either some zone-run boundary of one is within 10 min of a boundary of the other, or their time IoU is ≥ 0.5.
- **Why:** the large episodes are compound (hold → zero; zero → linear fill). One label per event cannot describe "A2 then A1". The guide already asked for votes on events, not timestamps; v1 makes each phase an event.
- **Alternatives rejected:**
  - Merging everything into connected components. One 108-h outage would chain unrelated events together.
  - v0's single list of dead events, which cannot see holds.
- **Code:** `rules_v1.dead_items`, `fill_items`, `clock_items`, `transfer_items`, `episodes`.

### D14 — Grouping only inside one system
- **Decision:** runs are grouped by start time (within 10 min of the group's first start, v0's semantics) **separately** for the south (L, B, F share one logger timeline) and for Marrakech.
- **Why:** v0 grouped across all four cities. Marrakech is a separate system, so a coincidental start within 10 min is meaningless. This is consistent with the guide's correction #1.

### D15 — Dead runs no longer need an exact zero [v0 deviation; consistent with guide eq. 4]
- **Decision:** `REQUIRE_EXACT_ZERO = False`. A dead run is ≥ 3 steps of x = 0 or x ≤ 0.05 · x̂.
- **Why:** H1 says a de-energised feeder reads a **noise floor**. v0's "≥ 1 exact zero" condition dropped exactly those runs.
- **Effect:** +20 southern runs and +43 Marrakech runs (Marrakech zone 2, whole-kW values). See F15 on the Marrakech caveat.

### D16 — State priority: exact zero > linear interpolation > noise floor > hold
- **Decision:**
  - dead = (x = 0) ∨ (x ≤ 0.05 x̂ ∧ ¬interp);
  - hold = hold ∧ ¬dead;
  - interp = interp ∧ ¬dead ∧ ¬hold.
- **Why:** a straight line ramping up from 0 is fill, not a de-energised noise floor (C01 and 24 Dec 2023 L2/L3 were misread as noise floor before this). Exact zeros stay dead.

### D17 — Longer minimums for Marrakech: 12 points for holds and for interpolation runs
- **Why:** Marrakech values are 100 % whole kW, so identical values repeat naturally. Zone 2 (median 30 kW) has 125 hold runs of ≥ 6 points but only 8 of ≥ 12. Integer ramps can also be collinear by chance. 12 points at 30 min = 6 h.

### D18 — Keep the guide's 6-point hold minimum in the south
- **Context:** Laâyoune shows about 1,070 runs of 3–5 identical points, mostly simultaneous across all 5 zones, until Apr 2023 (F09).
- **Decision:** keep 6 as the default and expose `HOLD_MIN_PTS`. Lowering it for multi-zone holds belongs to the sensitivity sweep (guide ablation 6).
- **Why:** this avoids flooding the item list with about 220 short items before the label model exists. The regime is documented as a finding instead.

### D19 — "Co-extensive" means time IoU ≥ 0.5 (R4, R21) [guide deviation]
- **Guide R4:** fires if at **any** step one zone is dead while another is held.
- **v1:** the held (or interpolated) run in another zone must have time IoU ≥ 0.5 with the dead item. A fill run that ends exactly where a dead run starts in the same zone is handled by R3 (hold) or R21 (linear).
- **Why:** with any-step overlap, a 1-h stuck sensor anywhere during a 108-h feeder outage would vote A1.

### D20 — R7 also abstains when R21 fires [guide deviation]
- **Guide R7:** regional outage if multi-city and not R2/R3/R4 and (R5 or R6 or τ ≥ 30 min).
- **v1:** "not R3/R4/R21". R2 is a fill-item rule in v1, and its dead-item counterpart is R4.
- **Why:** a linear fill next to the dead zones is fill evidence just like a hold. The guide predates the interpolation finding.
- **Effect:** R7 fires on 0 items (F07).

### D21 — R15 candidate dates and fit-quality guard [guide deviation]
- **Candidate dates:**
  - Europe: 2022-10-30, 2023-03-26, 2023-10-29, 2024-03-31.
  - Morocco: 2023-03-19 → GMT, 2023-04-23 → GMT+1, 2024-03-10 → GMT, 2024-04-14 → GMT+1.
  - Every date with duplicate or missing stamps in the audit.
- **Guard:** R15 votes A4 only if |δ*| ≥ 50 min **and** the correlation after the best shift is ≥ 0.9 **and** it improves on no shift by ≥ 0.05.
- **Why:** without the guard R15 fired on 18 of 33 dates, including Ramadan dates and Marrakech dates where the profile fit was 0.09–0.30. With the guard it fires on 6: Oct 2022 (L, B, F), Oct 2023 (L, B), and B on 2024-03-31.

### D22 — Restoration features measured per zone, after any straight-line ramp [guide deviation in detail]
- **Decision:**
  - r_E, π_E, τ_E (eq. 3) are aligned at each zone's own restoration time and summed across zones. v0 used the main city's aggregate at the event end.
  - If a linear-interpolation run starts exactly where the dead run ends, alignment moves to the end of that run.
  - The features `fill_ramp_zones` and `fill_ramp_min` record it.
- **Why:** 25 of 117 southern dead runs (21 %) "restore" through a straight line (F05). Measuring there makes H2's ramp evidence an interpolation artefact. Example: C02's r went from 0.22 (v0) to 1.01.
- **Code:** `rules_v1.restoration`.

### D23 — R5 and R6 vote the family label "G"
- **Decision:** as in the guide ("G (any)"). The label model treats "G" as speaking for every G type (D31).

### D24 — R10 maintenance window = start hour 6–11 inclusive (06:00–11:59) and duration ≤ 6 h
- **Decision:** v0's convention. The guide writes "06:00–11:00". The difference is the 11:xx starts.

### D25 — R12/R20 "neighbours vary" threshold = 0.8
- **Definition:** over the run's steps, at least 80 % of (other zones of the same city × steps) are in no anomalous state, not NaN, and have a non-zero first difference.

### D26 — Rule set and numbering
- **Implemented:** R1–R16 (guide numbering) plus R19–R21, the new linear-interpolation family. R19 = multi-zone linear fill → A2, R20 = single-zone linear fill → A3, R21 = linear fill co-extensive with or ending at a dead run → A1.
- **Not implemented:** R17 and R18 (external evidence). The user asked to skip external validation. The numbers R17/R18 stay reserved.

### D27 — `mv_label` in items.csv is for inspection only
- **Decision:** v1 writes a plurality label for quick reading. `conflict:G3|G4` on 67 single-zone items is **by design**: R9 (any single zone → G3) and R10 (morning, ≤ 6 h → G4) both fire. Probabilistic labels come from the label model (`results/labels_v1/q.csv`).

---

## Stage 2 — Label model (2026-11-08)

All of these live in `src/label_model.py`. Each was forced by a failure observed on the real votes. The failures are recorded as F20–F22.

### D28 — Abstention is an observed output [guide deviation, correction to eq. 10–11]
- **Guide:** q_i(y) ∝ π_y ∏_{r fired} θ_r(y, λ_r(i)), with θ_r(y, l) = P(λ_r = l | y, fired).
- **Problem:** every v1 rule emits one label. Normalised over the non-abstain outputs, θ_r(y, l) = 1 for every class y, so the votes carry no information. With the guide's smoothing denominator α|Y| the vote only rewards classes that already have more mass.
- **Decision:** θ_r(y, o) = P(λ_r = o | y) over o ∈ {abstain} ∪ outputs(r). Not firing is evidence.

### D29 — Feasible classes per item from its kind and hierarchy level [guide deviation]
- **Feasible sets:**

| Item | Feasible classes |
|---|---|
| dead, ≥ 2 cities | {A1, G1} |
| dead, 1 city, ≥ 2 zones | {A1, G2, G3} |
| dead, 1 zone | {A1, G3, G4} |
| fill, ≥ 2 zones | {A2, N} |
| fill, 1 zone | {A3, N} |
| clock | {A4, N} |
| transfer | {G5, N} |

- **Why:** the guide's typology defines each type at one hierarchy level (its "Level" column). Without gating, EM moved items across kinds and levels (for example, multi-city zero fills labelled G3).
- A1 stays feasible at every dead level, so episode evidence (R3, R21) can still call a single-zone zero an artefact.
- Class priors π are per item kind and renormalised over each item's feasible set.

### D30 — Applicability domains
- **Decision:** a rule contributes a likelihood factor only on items its precondition can observe:
  - R2 and R12 on fill items containing a hold;
  - R19 and R20 on fill items containing interpolation;
  - R13 (repeated hour) on clock items that are **not** spring-forward dates;
  - R14 (missing hour) only on spring-forward dates (Europe Mar; Morocco → GMT+1);
  - R15 where δ* is computable;
  - every other rule on all items of its kind.
- **Why:** hold vs interpolation (A2, A3) and repeated vs missing hour (A4) are mutually exclusive sub-signatures. Under conditional independence, a hold item "should" also fire the interpolation rule, so A3 hold items were pushed to other classes and missing-hour dates to N.
- A built-in assertion checks that no rule ever fires outside its domain.

### D31 — What a vote speaks for
- **Decision:** "G" (R5, R6) speaks for G1–G5. R9 (one zone dead) speaks for {G3, G4}. Its refinements R10 (→ G4) and R11 (→ G3) split them. Every other output speaks for its own label.
- **Why:** with R9 speaking only for G3, R10 ⊂ R9 forces G4 items to be "R9 false positives", and EM merged G4 into G3.

### D32 — Constrained one-coin parameterisation [guide deviation]
- **Model:** per rule output (r, l): P(λ_r = l | y) = a_rl if l speaks for y, b_rl otherwise. Abstain takes the rest.
  - a has Beta pseudo-counts (1, 1), the guide's α = 1.
  - b has pseudo-counts (1, 9): rules rarely fire on classes they don't speak for.
  - 20 restarts. Restart 0 is a deterministic init (a = 0.7, b = 0.05); the others add log-normal noise (σ = 0.5). The restart with the highest **penalised** log-likelihood (log-lik + log Beta prior) is kept. Stop when |Δ loglik| < 1e-6.
- **Alternative kept as a baseline:** the guide's unconstrained model (`structure="full"`: one free row per class, Dirichlet α = 1) with the same D28–D31 and D34 machinery.
- **Why:**
  - Before D29–D31, the unconstrained model's restarts agreed on only 19–100 % of items and its best solution lost class meaning (C06 and C12 → G3, every single-zone → G4, all transfers → N).
  - Even with D29–D31 the unconstrained model reaches only 63 % minimum restart agreement, 0.68 recovery accuracy and ECE 0.28. The constrained model reaches 100 %, 0.92 and 0.03 (F21, F22).

### D33 — Defining rules get propensity pseudo-counts (9, 1) [guide deviation]
- **Defining rules:** R2, R8, R10, R12, R13, R14, R16, R19, R20. Inside its applicability domain, each fires exactly when the typology's definition of its class holds:
  - G2: ≥ 90 % of one city dead and the others alive;
  - G4: one zone, 06–11 h, ≤ 6 h;
  - G5: conserved transfer;
  - A2: ≥ 2 zones held or interpolated together;
  - A3: one zone held or interpolated while its neighbours move;
  - A4: repeated or missing hour on a clock date.
- **Why:** a class whose only evidence is one rule cannot be held by EM with a flat prior. G4's propensity fell to 0.59 and G4 absorbed half the "unplanned" outages. The single G5 item went to N.
- **Effect:** E15 shows that removing this prior changes 39 % of dead labels (the G3/G4 split). This is the most influential prior (F24).

### D34 — Dirichlet(1) prior on class priors π
- **Decision:** π_k(y) ∝ Σ_{i of kind k} q_i(y) + 1 for each class of kind k. The guide uses π_y = mean q, with no smoothing.
- **Why:** an EM fixed point where a class prior reaches ~0 and never recovers. Observed twice: the 6 vote-less fill items went to A3 at 100 % because N had emptied, and C11 (the only G5 item) went to N.

### D35 — No sampled "normal" windows in NB2
- **Guide:** items include an equal number of sampled windows where every rule abstains (class N).
- **Decision:** not done in NB2. With D29, dead items cannot be N, and fill, clock and transfer items already carry N. All-abstain windows would add no information about any rule's propensity. They are needed by the **end model** (NB3) as negatives, so they are deferred there.

### D36 — What counts as evaluation of the label model on real data
- **Decision:** without ground truth, NB2 reports:
  - restart stability;
  - parameter recovery on votes simulated from the fitted model (20 seeds; accuracy, macro-F1, ECE, Brier);
  - robustness of the real labels to dropping each rule family and to each prior;
  - agreement with majority vote and with the guide's model.
- Accuracy against known types is **deferred to NB4** (injection).
- **Caveat for the paper:** the recovery test checks identifiability under the model's own assumptions. It does not test the rules.

### D37 — Majority-vote baseline definition
- **Definition:** plurality over the item's feasible classes. A vote that speaks for several feasible classes splits its weight equally. Ties go to the first class in `CLASSES` order. Items with no usable vote get N, or the first feasible class for dead items.
- **Code:** `label_model.majority_vote`.

### D38 — Notebooks are generated by scripts
- **Decision:** `tools/make_nb*.py` write the notebooks, which are then executed with nbconvert, so code cells stay reviewable as plain Python and the notebooks can be rebuilt. The executed notebooks, with their outputs, are committed.

---

## Stage 3 — Detector and end model (NB3, 2026-11-08)

Code: `src/detector.py`, `src/end_model.py`, `notebooks/NB3_detector_end_model.ipynb` (generator `tools/make_nb3_detector_end_model.py`).

### D39 — Predictor: LightGBM nowcasts, the guide's "cheaper fallback", not the TCN-GAT [guide deviation, allowed by the guide]
- **Decision:** each zone's ρ is predicted by LightGBM with a Huber objective (δ = 0.1; the guide's masked Huber loss). Training uses only rule-clean steps (masked loss).
- **Parameters:** 400 trees, learning rate 0.05, 31 leaves, min_child_samples 50, bagging 0.8, colsample 0.9, λ = 1.
- **Why:** the guide allows this fallback and states that eq. 14–16 do not depend on the predictor. The TCN-GAT stays an option and an ablation (NB4); it is not needed to test the hierarchy idea.
- **Environment note:**
  - LightGBM 4.7.0 crashed intermittently on the author's Windows machine (access violation in `LGBM_DatasetSetField`). It worked on toy data and failed on the real features, and contiguous arrays did not fix it.
  - `detector.predict_rho(backend="auto")` therefore falls back to scikit-learn's `HistGradientBoostingRegressor` (same histogram-GBDT family; absolute-error loss) **for the whole call** when LightGBM raises. The notebook prints the backend used.
  - **The Colab run with LightGBM is the reference run**; local runs that fell back are for code validation.
  - The user asked for lightgbm, PyWavelets and statsmodels explicitly (2026-11-08).

### D40 — Which residual carries the region / city / zone hierarchy [guide deviation]
- **Guide eq. 13:** predict zone z from its own past plus the **current** values of its neighbours (leave-one-zone-out graph nowcast), then split that residual into g, u, v (eq. 14).
- **Problem:** in a logger failure every zone drops at once. A predictor that sees the neighbours' current values can partly "explain" the drop, so the region part g, which is exactly where the guide wants logger artefacts to show, may shrink.
- **Decision:** build both residuals and test them:
  - **forecast:** own masked past + calendar, no neighbour information;
  - **nowcast:** the guide's version, forecast features plus every other zone's current ρ;
  - an **STL** residual (statsmodels) as a classical baseline.
- **Test:** for every southern rule item, the level with the highest score (g, the item's cities' u, the item's zones' v) should match the level its structure implies (multi-city → g, ≥ 90 % of one city → u, one zone → v). Also compare clean-data prediction error.
- **Result:** the hypothesis was **not** confirmed on the real data (F29). The nowcast's g scores for logger events are as large as the forecast's (C06: 227.9 vs 222.6). Hierarchy consistency is 0.752 (nowcast) vs 0.738 (forecast) vs 0.699 (STL), a difference of about 3 of 206 items. Neighbours also don't improve clean MAE (0.0287 vs 0.0285).
- **Choice:** `MAIN = "forecast"`.
  - The two are equal within noise; the forecast is simpler.
  - Its region response does not depend on shared shocks having been masked during training. The nowcast's does: unflagged shared anomalies could be explained away by the neighbours.
  - NB4 must test this with unflagged injected multi-zone events. If the nowcast is as good there, either can be used.

### D41 — Two-fold temporal cross-fitting
- **Decision:** models trained on Sep 2022 – Jun 2023 predict Jul 2023 – May 2024, and vice versa (split at 2023-07-01, the guide's train/test boundary).
- **Why:** every residual is out of sample, so in-sample overfitting cannot shrink residuals.

### D42 — Multi-scale = phase-aligned MODWT of the residual [guide deviation in detail]
- **Guide:** decompose ρ with MODWT and fit one predictor per band, then compare each band with its prediction.
- **Decision:** decompose the **residual** e = ρ − ρ̂ with the MODWT pyramid algorithm (LA(8) = PyWavelets `sym4`, J = 4, circular), then **phase-align** each band.
  - Each band is shifted back by its group delay, measured numerically as the energy centroid of the band's impulse response: W1 4, W2 11, W3 25, W4 53 and V4 43 steps. These match the analytical LA(8) shifts of Percival & Walden (2^{j−1}·7 − 3 = 4, 11, 25, 53; 15·3 = 45 for V4).
  - Wrapped ends and boundary coefficients are NaN. NaN residuals are filled with 0 before filtering.
- **Bands at 10 min:** W1 20–40 min, W2 40–80 min, W3 80–160 min, W4 160–320 min, V4 smooth (> 320 min).
- **Why:**
  - Same role as the guide's design, per-scale anomaly evidence, without training five predictors per zone.
  - **The first version used unaligned (causal) coefficients.** They smeared every event up to about 18 h forward in time: detector flags appeared on normal data 8–10 h after real disturbances (E18 v1, candidates X012, X056, X098) and inflated γ to 104.
  - The catalogue is built retrospectively, so non-causal alignment is legitimate. An online detector would need the causal version and a delay correction.
  - `pywt.swt` was used to check energy preservation: x 3980.7, our MODWT 3981.6, `pywt.swt` 3980.1 on a test signal, interior coefficients. The filter is asserted equal to Percival & Walden's LA(8).

### D43 — Level scores, warm-up and threshold γ
- **Level scores (eq. 15):** robust z = (|ε| − median|ε|) / (1.4826 MAD|ε| + 1e-6), with the median and MAD over a **trailing** 28-day window (minimum 7 days) and estimated only on steps that are rule-clean at that level:
  - g: no zone of the system flagged;
  - u_c: no zone of city c flagged;
  - v_z: zone z not flagged.
- **Warm-up:** scores are NaN for the first 21 days of each system (x̂ needs 14 days and the robust window 7 more). In v1 of the notebook, the top detector-only "candidate" (score 9014) was an artefact of the empty baseline in the first week.
- **Zone-step score Z** = max over the 6 bands and over the levels that contain the zone.
- **γ** = 99.5th percentile of Z over **rule-negative** zone-steps. A zone-step counts as rule-negative if:
  - its own zone has no rule state within ± half the widest band's support (53 steps), and
  - no multi-zone rule state exists in the system within ± 53 steps (multi-zone events move g and u for every zone).
- The first version used "not masked" as the negative set. It included the band spillover around events and gave γ = 104.

### D44 — Detector-only candidates
- **Decision:**
  - runs of ≥ 3 flagged steps per zone, allowing gaps of ≤ 1 step;
  - a run is discarded if it overlaps a rule zone-run of the same zone, extended by ± 53 steps (half the support of the widest phase-aligned band);
  - the remaining runs are grouped across zones by start within 10 min (as in the rule engine).
- **Description, not types:**
  - "partial drop": mean ρ < 0.7 and minimum ρ < 0.5;
  - "surge": mean ρ > 1.4;
  - "other": anything else.
- These are anomalies the rules do not cover: the detector's coverage gain (guide: "a multi-scale graph detector adds coverage").

### D45 — Normal windows (the guide's N items, deferred from NB2 by D35)
- **Decision:**
  - 250 southern and 50 Marrakech windows;
  - durations drawn from the rule items' durations (capped at 48 h);
  - zone patterns drawn from the rule items' structure (one zone, one whole city, or all zones);
  - accepted only if none of their zones has a rule state, a detector flag or a NaN within ±1 h;
  - fixed seed (0).
- They are the end model's negatives (target N).

### D46 — End-model scope: event items only
- **Decision:** the end model covers dead and fill items, normal windows and detector-only candidates. Clock and transfer items are day-level, rule-defined objects; they keep the label-model q.

### D47 — End-model training (eq. 12), evaluation and fusion
- **Features:** one unified feature vector per item, computed identically for every source (methods §6):
  - structure;
  - state shares;
  - ρ dynamics before, during and after the item;
  - calendar;
  - fill adjacency;
  - episode context, to address F25;
  - detector scores per level and band, plus the nowcast zone score.
- **Learners:**
  - LightGBM multiclass (300 trees, learning rate 0.05, 15 leaves, min_child_samples 5) on rows expanded per class with weight q_i(y) (eq. 12);
  - a 2-layer MLP (64-64, dropout 0.1, AdamW, soft cross-entropy, 400 full-batch epochs; median imputation + missing indicators);
  - the backend follows D39.
- **Targets:** q over EVENT_CLASSES = {A1, A2, A3, G1, G2, G3, G4, N} for rule items; N for normal windows.
- **Evaluation:** out of fold, GroupKFold(5) with groups = episode, so an item is never scored by a model that saw its own episode. Detector-only candidates are scored by a model trained on all labelled items.
- **Ablations:** no detector features, no episode features, detector features only, and the MLP.
- **Fusion (eq. 16):** p ∝ q^β f^(1−β) on each rule item's feasible set, β = 0.5 provisional. β and temperature scaling need ground truth, so they are tuned on injected data in NB4. Detector-only candidates have no q: they use the uniform distribution, so p follows f.

### D48 — Calendar features for the predictor
- **Features:**
  - time of day (raw, sin, cos), weekday, weekend, month;
  - Ramadan (23 Mar – 21 Apr 2023, 12 Mar – 9 Apr 2024);
  - Eid days (22–23 Apr 2023, 29–30 Jun 2023, 10–11 Apr 2024);
  - fixed national holidays;
  - Morocco's GMT period (19 Mar 03:00 – 23 Apr 02:00 2023, 10 Mar 03:00 – 14 Apr 02:00 2024).
- Religious dates are Morocco's announced dates as best known and may be off by a day. They are only predictor features, never labelling rules.

### D49 — STL baseline settings
- **Decision:** statsmodels STL, period = 1 day, **non-robust** (robust STL on 15 × 88,890 steps did not finish within 10 min locally). Masked and missing steps are filled with 1 (= expected) before decomposition. STL is two-sided (non-causal), so it is a reference, not a deployable detector.

### D50 — The end model abstains in fusion on classes it cannot learn
- **Decision:** classes whose total training mass Σ_i q_i(y) over rule items is below 3 items are "low support". On real data this is A1 (about 3), G1 and G2 (1). For rule items whose label-model arg max is a low-support class, fusion returns p = q: the end model abstains.
- **Why:** out of fold, a class with one example is never in the training folds when that example is scored. Without abstention, fusion turned the only G2 item (26 Sep 2022, all Laâyoune zones, q_G2 = 0.99) into G3 (0.82). That was an artefact of the evaluation design, not evidence.
- **Effect:** β (still 0.5) and abstention only matter where the two experts disagree. NB4 tunes β on injected data, where these classes have many examples.
