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
  - **Superseded by D52:** LightGBM 4.6.0 works locally, so the reference run is local again. The fallback stays in the code for other machines.

### D40 — Which residual carries the region / city / zone hierarchy [guide deviation]
- **Guide eq. 13:** predict zone z from its own past plus the **current** values of its neighbours (leave-one-zone-out graph nowcast), then split that residual into g, u, v (eq. 14).
- **Problem:** in a logger failure every zone drops at once. A predictor that sees the neighbours' current values can partly "explain" the drop, so the region part g, which is exactly where the guide wants logger artefacts to show, may shrink.
- **Decision:** build both residuals and test them:
  - **forecast:** own masked past + calendar, no neighbour information;
  - **nowcast:** the guide's version, forecast features plus every other zone's current ρ;
  - an **STL** residual (statsmodels) as a classical baseline.
- **Test:** for every southern rule item, the level with the highest score (g, the item's cities' u, the item's zones' v) should match the level its structure implies (multi-city → g, ≥ 90 % of one city → u, one zone → v). Also compare clean-data prediction error.
- **Result:** the hypothesis was **not** confirmed on the real data (F29). The nowcast's g scores for logger events are as large as the forecast's (C06: 232.6 vs 218.0). Hierarchy consistency is 0.714 (forecast) vs 0.694 (nowcast) vs 0.621 (STL) in the reference run; the two superseded runs had the nowcast 3–4 items ahead, so the difference is noise. Neighbours also don't improve clean MAE (0.0292 vs 0.0288).
- **Choice:** `MAIN = "forecast"`.
  - The two are equal within noise (the sign of the difference flips between runs); the forecast is simpler.
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
- **Structural zeros** of the median hierarchy (|s| ≤ 1e-12) are also excluded from the median and MAD (D51, added after F35).
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

### D51 — Structural zeros are excluded from the level-score scale [bug fix, 2026-11-08]
- **Problem (F35):** u and v come from medians (eq. 14). The median of an odd number of zones is one of them, so that zone's v is exactly 0 at that step; a city's u is exactly 0 when its median zone is also the region median. If these zeros fill at least half of the trailing 28-day window, the median and the MAD of |v| are 0 and the robust z (D43) becomes |v| / 1e-6.
- **Where it bit:** the Colab LightGBM run (commit 21e6695). B1 (Boujdour has 3 zones) was the city's median zone on 52 % of the V4-band window before 16–18 Mar 2024. Its old V4 scale was 0, and nine detector-only "candidates" on B1 scored 3,973–15,182 (the sklearn run happened to stay below the 50 % line, top score 317). Only 925 of 1,257,663 V4 zone-steps had a collapsed scale, but the bias exists everywhere: zeros pull the median and MAD of small cities' v down and inflate their scores.
- **Decision:** `detector.robust_score` estimates the median and MAD only on steps that are clean **and** have |s| > 1e-12 (`STRUCTURAL_ZERO`). The score itself is still computed at every step; at a structural zero it is negative (not anomalous). Eq. 14 (e = g + u + v) is unchanged.
- **Alternatives rejected:**
  - leave-one-out medians (v_z = e_z − median of the *other* zones), which break the additive identity of eq. 14;
  - a larger fixed MAD floor, which is unit-dependent and ad hoc;
  - the mean instead of the median, which loses robustness to the very events being scored.
- **Effect** (`results/detector_v1/structural_zeros.csv`, LightGBM forecast residual):
  - B1, 16–18 Mar 2024, V4: old score 14,940, fixed score 2.1;
  - the maximum zone score drops to the level of real events.
- **Code:** `src/detector.py` (`robust_score`, `STRUCTURAL_ZERO`); diagnostic `tools/diag_structural_zeros.py`.

### D52 — LightGBM 4.6.0 pinned; the reference run is local again
- **Finding:** LightGBM 4.6.0 (the version Colab ships) runs on the author's Windows machine; 4.7.0 crashed (D39). The local 4.6.0 south forecast reproduces Colab's MAE (0.0288).
- **Decision:** `requirements.txt` pins `lightgbm==4.6.0`. NB3 runs locally with LightGBM; Colab stays an option (the notebook now ends with `drive.flush_and_unmount()` on Colab, because Colab left the CSVs of the first run unsent while the figures arrived).
- **Run record:**
  - 2026-11-08, local, sklearn fallback, code a9ec65a (D39);
  - 2026-11-08, Colab, LightGBM 4.6.0, code a9ec65a, commit 21e6695: exposed F35;
  - 2026-11-08, local, LightGBM 4.6.0, with D51: **the reference run**, numbers in `results_summary.md` §8.
- `summary.json` now records `lightgbm_version` and `colab`.

### D53 — The learned graph: a TCN-GAT nowcaster (guide eq. 13 as written) [NB4, 2026-11-08]
- **Request:** the author asked for the guide's graph model in NB4, "to add value to the work" (2026-11-08), in addition to NB3's LightGBM (D39).
- **Model** (`src/graph_model.py`):
  - nodes = the 15 southern zones;
  - a causal TCN shared by all zones on each zone's past ρ and rule mask: 6 residual blocks, kernel 3, dilations 1–32, 32 channels, receptive field 253 steps (about 42 h);
  - a 2-head graph-attention layer over the **current** ρ of the zone's neighbours (leave-one-zone-out: the zone's own current value is never an input). Masked neighbours are excluded from the attention;
  - neighbours: every zone of the same city, plus the top-k = 4 zones of *other* cities by cosine similarity of trainable 16-d node embeddings (GDN-style, recomputed at each forward pass), as the guide specifies;
  - head: an MLP on the TCN state, the attention message, the node embedding, calendar features (D48) and the zone's own value 1 day and 7 days earlier.
- **Training:**
  - masked Huber loss (δ = 0.1, as LightGBM's), AdamW (lr 2e-3, weight decay 1e-4), cosine schedule, up to 40 epochs, early stopping (patience 6) on the last 15 % of each training fold;
  - two-fold temporal cross-fitting at 2023-07-01, exactly like D41.
  - The TCN is fully convolutional, so it runs over contiguous chunks (warm-up = receptive field, then 256 targets). Predictions are independent of chunk boundaries (checked: max difference 1.2e-7).
- **Ablation:** the same network without the graph (`graph=False`) = the TCN analogue of the LightGBM forecast.
- **Scope:** south only. Marrakech has 2 zones in one city, so a graph is trivial there; it keeps LightGBM.

### D54 — Injection protocol and evaluation scope [NB4]
- **Corrected by D60 (2026-11-09):** the scoring and injection area no longer excludes NB3's detector candidates, which hid the LightGBM detector's own false alarms (F36). The rest of D54 stands.
- **Where:** a clean region of zone-steps that are:
  - farther than ±53 steps (D43's spill) from any real rule state of the same zone, and from any real multi-zone state;
  - farther than ±53 steps from NB3's detector-only candidates;
  - past the 35-day burn-in (14-day expected value + 21-day warm-up);
  - not within a day of a clock-change date.
- **What** (`src/inject.py`): the guide's types with observed signatures:
  - A1: exact zeros in 2–3 whole cities;
  - A2: holds or straight-line fills, per zone 50/50 (F01), on 2+ zones; whole-city patterns are followed by an A1 with probability 0.5 (the C05 → C06 and C12 compounds);
  - A3: a single-zone hold or linear fill, 1–6 h;
  - G1: 2 cities at a noise floor x̂·U(0, 0.03) with 0–30 % exact zeros, a 20–90 min linear ramp and a decaying overshoot ω ~ U(1.1, 1.5);
  - G2: one city, as G1, 20 min – 6 h;
  - G3: one zone, any hour, 1–48 h;
  - G4: one zone, start 06:00–11:59, 70 % weekends, 1–6 h, 10–30 min ramp, no overshoot.
  - Durations are log-uniform in the ranges above. G3 is capped at 48 h and A1 at 24 h (guide: up to 5 d / 48 h) to keep enough events per type.
  - **Plus two untyped cases the findings require:**
    - U_SHOCK: 2–3 whole cities × U(0.5, 0.8) for 0.5–4 h. No rule fires, so this tests forecast vs nowcast (F29).
    - U_PARTIAL: one zone × U(0.10, 0.45) for 1–8 h, above ε (F32).
  - **Not injected:** A4 clock errors (the rules are calendar-gated) and G5 transfers (weeks long; day-level items outside the end model, D46).
- **How much:** events are placed round-robin over the 9 types until the injected zone-steps reach the target share (1, 3, 7 %) of clean zone-steps. Each event blocks its zones for ±12 h, and multi-city events block all zones for ±3 h. The seed is (rate × 1000, seed).
- **Evaluation scope:**
  - a predicted event counts only if it touches the clean region or an injected span; predictions entirely near real anomalies are ignored, because their truth is unknown;
  - **two matching rules**, both reported:
    - *guide eq. 17* (the headline F1): a match is a time overlap with the injected span, including its restoration tail;
    - *zone-strict*: also at least one shared zone. Per-type recall and the attribution matching always use the zone-strict rule.
  - **Why both:** in the end-to-end test (3 %, seed 0), 31 of the 34 in-scope detector predictions that missed every injected event under the zone rule overlapped an injected event in time, and covered whole *other* cities. When most cities drop together, the region median g follows them, so the unaffected city stands out at the city level u. This is a property of the median hierarchy, not a false alarm in time. Only 3 predictions were false alarms under both rules.
  - the test period is Jul 2023 – May 2024; the training period is used only for β.
- **Predictors are not retrained on injected data.** They were fitted on the real data with cross-fitting, so each half of an injected series is predicted by models trained on the other half of the *real* series and has never seen an injected event. The label model and the end model are refitted on every injected dataset, as in the real pipeline.

### D55 — One TCN-GAT on ρ, not one network per MODWT band [guide deviation]
- **Guide eq. 13:** one TCN-GAT per MODWT band of ρ, with learned band weights α.
- **Decision:** one network predicts ρ. The residual is then decomposed with the same phase-aligned MODWT as LightGBM's (D42), and the band scores are combined by the maximum (D43).
- **Why:** this is the same deviation as D42, for the same reasons: five networks per system for no gain in interpretability, and the comparison with LightGBM stays clean, because only the predictor changes. α would need injected validation data for tuning, which the max over bands does not.

### D56 — β tuning and the D50 abstention on injected data [NB4]
- β ∈ {0, 0.1, …, 1} is chosen per rate by macro-F1 on the injected events of the **training period** (pooled over seeds) and frozen for the test period. Ties go to the value nearest 0.5.
- On injected data, A1, G1 and G2 are no longer rare, so fusion is reported both with D50's abstention (the real-data setting) and without it.
- Temperature scaling is not applied. ECE is reported as is, for q, f and p.
- **Detector-only items are fused without abstention (bug fix, 2026-11-09).** Their q is uniform, so its arg max is the first class (A1), a low-support class. `benchmark.fused` therefore abstained and returned the uniform q: every detector-only item was labelled A1. NB3 fused them without abstention, and `fused` now does the same (abstention applies to rule items only). This was found in the NB4 QUICK test: all 54 real-data candidates were A1 before the fix; after it, N 48, A3 5, G4 1. It affects the injected events matched to detector items (7 of 368 detected typed events in the QUICK runs).

### D57 — Baselines that are not run [NB4]
- **Run:**
  - the rule engine alone;
  - STL + MAD (robust z of the STL residual, same window as eq. 15);
  - Isolation Forest and LOF (scikit-learn; per zone-step features ρ, Δρ, ρ − ρ one day earlier, 1-h mean and std; fit on 50,000 / 10,000 rule-negative zone-steps);
  - majority vote as a labeler;
  - our own ablations: no hierarchy, single scale, no graph, nowcast.
- **Not run:**
  - Matrix Profile: O(n²) per zone on 88,890 steps;
  - USAD, TranAD, Anomaly Transformer and TimesNet: deep reconstruction and forecasting baselines that need the authors' code and a training budget per seed;
  - GDN and MTAD-GAT: the closest graph baselines. The TCN-GAT itself uses GDN's learned top-k graph, so the graph idea is tested, but not the authors' implementations;
  - Snorkel: an extra dependency (guide correction #10).
- Say so in the paper. They can be added on the same injected datasets later, because the runs are reproducible from (rate, seed).

### D58 — NB4 run protocol: cached, resumable, Colab GPU [NB4]
- Each (rate, seed) run writes its truth, detection, AUC and event tables to `results/benchmark_v1/runs/` as soon as it finishes; a rerun skips finished runs.
- The trained predictors are saved in `results/benchmark_v1/models/`. `tcn.pt` and `tcn_gat.pt` are in git; `lightgbm_models.pkl` (73 MB) is git-ignored and lives on Drive.
- Colab has newer numpy, scikit-learn and torch than the machine that saved the models (numpy 1.26.4, scikit-learn 1.5.1, torch 2.2.0).
  - The `.pt` files hold only dicts, tensors and scalars, so they load under torch's strict `weights_only=True` default (torch ≥ 2.6). This was checked.
  - NB4 loads the LightGBM pickle in a `try` block and smoke-tests a forecast. If either fails, it refits LightGBM (4.6.0, as pinned) instead of crashing, and prints why.
- `QUICK = True` runs 1 rate × 2 seeds with 2-epoch networks (written to `results/benchmark_quick/`) to test the notebook.
- The rule-family ablation of the label model runs at 3 % only. The threshold sweep (rules + label model only) runs at 3 % on 3 seeds.

### D59 — Hybrid predictor: LightGBM forecast + learned correction (graph or no graph) [NB4] — kept as ablation
- **What:** `graph_model.TCNGAT(use_base=True)`, `fit_graph_models(..., base=PF)`.
  - The network receives the cross-fitted LightGBM forecast PF and outputs PF + a learned correction. The last layer is zero-initialised, so training starts from PF exactly.
  - The graph attention also reads each neighbour's current residual ρ_j − PF_j.
  - Same training as D53: masked Huber loss, two folds, early stopping, 40 epochs, patience 6.
  - Ablation: the same without the graph (LightGBM + TCN correction).
  - Models: `results/benchmark_v1/models/hybrid_gat.pt`, `hybrid_tcn.pt`.
- **Why:** the author asked for the graph to be the main detector and the strongest model, "keeping LightGBM if it is the best". A correction on top of the best predictor is the natural way to keep LightGBM and add the graph.
- **Outcome (F37):** the correction does not generalise; both hybrids end at LightGBM's MAE (0.02879). They stay in NB4 as ablations: no correction vs learned correction, with and without graph.
- **Code:** `src/graph_model.py`, `src/benchmark.py` (`VARIANTS`).

### D60 — Fair evaluation: rule-based scoring area, per-detector event formation, two views of precision [NB4] **[corrects D54]**
- **Scoring area:** `clean_region(P, None)`: rule states, multi-zone states, burn-in and clock days only. NB3's detector candidates are no longer excluded, because that hid the LightGBM detector's own false alarms and nobody else's (F36). Injection uses the same region.
- **Event formation is part of each detector:**
  - score smoothing w (centred moving average of the zone score);
  - threshold γ at the q-th percentile of rule-negative zone-steps;
  - merge gap (`detector_items(max_gap)`);
  - minimum run of 3 steps, as in NB3.
  - NB3's choice was w = 1, q = 99.5, gap = 1.
  - **Tuned detectors:** the main candidates (TCN-GAT, LightGBM, their average, the graph hybrid) and the baselines (STL + MAD, Isolation Forest, LOF). Each gets the setting with its best mean event F1 alone on the development datasets.
  - **Ablations** (single scale, flat, the no-graph hybrid, raw-band predictor variants) inherit the main detector's setting, so they change one thing only.
  - NB4 also reports TCN-GAT and LightGBM with NB3's setting (`... (NB3 event formation)`), because tuning trades short shocks for precision (F38).
- **Development datasets:** seeds 100–104 (3 % × 3, 1 %, 7 %) from the same injector. The benchmark seeds 0–9 are never used for any choice.
- **Two views of precision:**
  - **primary:** every alarm counts (conservative; the criterion of the development selection, so that noisy settings cannot win);
  - **`*_bgx`:** each method's own detections on the uninjected series are not scored (`Benchmark.set_background`). This is the treatment the rule states already give the rules.
  - Table 5 also gives each method's number of real-data alarms.
- **Code:** `src/benchmark.py` (`clean_region`, `smooth_score`, `gamma_of(q)`, `Benchmark.setting`, `set_background`), `tools/dev_select_detector.py`.

### D61 — Main detector: the TCN-GAT multi-scale graph residual detector [NB4] **[changes NB3's main detector for the south]**
- **Choice:** `TCN-GAT, hierarchy, multi-scale` with w = 24 (4 h), q = 99.9, gap = 12.
  - Pipeline: TCN-GAT residual (D53) → phase-aligned MODWT bands (D42) → region/city/zone median hierarchy (D51) → robust scores, max over bands and levels (D43) → event formation (D60).
- **Selection rule (fixed before looking):** the main detector is the candidate with the best mean F1 of the full method (rules + its detector-only candidates) at its own tuned setting, on the development datasets. TCN-GAT 0.863, average 0.854, graph hybrid 0.850, LightGBM 0.849 (F39). It is also the best alone: 0.786 vs 0.759, in all 10 cells.
- **Consequences:**
  - NB4's end model, fusion, attribution tables and the real-data catalogue (`results/main_detector/`, NB4 §8b) use the graph detector.
  - Marrakech (2 zones, one city: nothing for a graph to learn) keeps NB3's LightGBM detector.
  - NB3's south numbers (γ 25.5, 290 candidates) describe the LightGBM detector at NB3's event formation and are superseded by NB4 §8b for the paper's catalogue.
- **The author's request:** "present the graph as the main detector and make it more powerful than any other model; if LightGBM is the best, keep it and do a best benchmark, but always keep the graph in the top".
  - The graph detector won the development selection, so it is the main one.
  - LightGBM had the same tuning budget; nothing was tuned for the graph alone.
  - In every table the graph detectors come right after the main detector.
- **Caveats for the paper:** F37 (no prediction gain), F39 (lower step-wise AUC-PR than STL and LightGBM) and F40 (no event-F1 gain over the rules under strict counting).

### D62 — The no-graph ablation of the main detector, added after the NB4 run [NB4 add-on]
- **Gap:** NB4 compared the TCN-GAT with a TCN without the graph only on the raw band (`TCN, no graph (raw, hierarchy)`). The row that isolates the graph inside the main detector was missing. It is the TCN residual through the same MODWT bands, hierarchy and event formation (`TCN, no graph, hierarchy, multi-scale`).
- **Fix:**
  - `benchmark.V_TCN_MS` was added to `VARIANTS`, so that a future NB4 run includes it. Adding it does not change the raw-band row, because the multi-scale level scores contain the raw band unchanged.
  - `tools/graph_ablation.py` computes it on exactly the NB4 datasets. The injected data are regenerated from the same seeds, and the script asserts that they equal `runs/*_truth.csv`.
- **Three rows**, scored as `Benchmark.run` (both precision views, zone-strict F1, step AUC-PR, per-type recall):
  1. **the main detector, recomputed here:** a reproduction check of the Colab rows (CPU and torch 2.2 here, GPU and torch 2.14 on Colab);
  2. **the no-graph TCN at the main detector's event formation:** the ablation in the sense of D60, one thing changed;
  3. **the no-graph TCN at its own event formation:** tuned on development seeds 100–104 over the same 48 settings by the same criterion, so it is not handicapped by a setting chosen for the graph.
- **Not rerun:** the end model and attribution, because the main detector does not change.
- **Output:** `results/benchmark_v1/graph_ablation/`.
- **Outcome (F42):** the CPU recomputation matches the Colab rows exactly. Without the graph the detector is equal or slightly better: F1 0.671 / 0.817 / 0.857 vs 0.644 / 0.813 / 0.854, significant at 1 %. The main detector is **not** changed (D63); the paper framing is the author's decision.

### D63 — The test seeds are spent: no design change is made from NB4's test results [NB4]
- **Rule:** seeds 0–9 have been looked at. Several results suggest changes:
  - the flat residual (F43);
  - dropping or down-weighting the simultaneity family (F47);
  - linking detector-only candidates to co-occurring rule items (F44).
- **These are reported, not adopted.** Adopting any of them now would select the design on the test data.
- **If a change is wanted:**
  1. develop it on the development seeds (100–104), with the protocol of D60;
  2. evaluate it once on **fresh** test seeds (20–29; 10–19 are reserved as a spare);
  3. report it as a post-hoc revision next to the original result.
- **The injector is the same for every seed set**, so threat 16 of the handoff applies in full.

### D64 — NB5 cleaning strategies as implemented [NB5]
- **Scope:** the southern system (15 zones). Marrakech is a separate 30-min kW system with a different detector (D61) and almost no grid events (F15), so it is left out.
- **Flagged zone-steps:** dead, hold or linear-fill states inside a qualifying rule zone run (`zone_runs`, D13 thresholds). Only these are cleaned. Isolated short states are left as recorded under every strategy.
- **S1 naive:** every flagged run is linearly interpolated between its edges, artefacts and grid events alike.
- **S2 typed:**
  - flagged steps of items labelled A1–A3 are imputed with x̂ (eq. 1), multiplied by a ratio that moves linearly from the left-edge to the right-edge ratio x / x̂. Each edge ratio is the median of up to 3 valid neighbours within 6 h, so the imputation joins the series at both ends (guide "Imputation for artefacts");
  - flagged steps of items labelled G* are kept, marked by an event indicator (feature), and excluded from the training loss;
  - where an artefact item and a grid item overlap, the artefact wins (the fill part of a compound episode).
- **Left as recorded:** items labelled N, clock and transfer items, and detector-only candidates.
  - **[guide deviation]** A4 stamps are not re-aligned: timestamps stay as recorded (D11), and the clock items are excluded from scoring instead.
- **Labels:**
  - real data: the fused labels of the main-detector catalogue (`results/main_detector/p_type_south.csv`, NB4 §8b);
  - injected data: the label model's arg max, which matches fusion there (F46).
- **S3 oracle (injected data only):** S2's masks outside the injected spans, plus the true types inside them. Injected A1–A3 core spans are imputed. Injected G1–G4, U_SHOCK and U_PARTIAL spans, restoration tails included, are kept with the indicator.
- **Code:** `src/downstream.py` (`clean`, `typed_masks`, `run_mask`).

### D65 — NB5 forecasters: global LightGBM direct forecaster and a naive reference; no deep model [NB5] **[guide deviation]**
- **LightGBM:**
  - one global model per horizon (1 h = 6 steps, 1 day = 144 steps) over the 15 zones, on each zone's series divided by its median on normal pre-test steps;
  - features at the origin t: lags 0, 1, 2, 5, 11; mean of the last hour and the last day; the same time of day as the target 1, 2 and 7 days earlier; the event indicator now and in the last day (zero for S0 and S1); the target-time calendar (time of day, day of week, weekend, Ramadan, Eid, holiday); zone id;
  - L2 loss, 500 trees, learning rate 0.05, 63 leaves, seed 0;
  - every step is an origin (rolling origin, direct forecasting).
- **Naive reference:** persistence at 1 h (the cleaned series 1 h earlier) and seasonal naive at 1 day (one day earlier). It is model-free, so a strategy effect on it cannot be a training artefact.
- **Not run:** PatchTST or N-BEATS (guide). The guide wants a deep model to show that the effect does not depend on the architecture. The naive reference serves that purpose at no cost, in line with the author's light-dependency preference. A neural forecaster can be added later on Colab.
- **Training period:** from day 35 (burn-in) to 31 Dec 2023. **Test period:** 1 Jan – 24 May 2024 (guide).

### D66 — NB5 scoring and the injected datasets [NB5]
- **Scored zone-steps (guide):** those that every strategy treats as normal: no flagged state, no rule item of any kind, no detector-only candidate and a recorded value. On injected data, scoring also requires NB4's clean region and excludes every injected span, restoration tail included. The truth is then the recorded series.
- **Subsets:**
  - all scored test steps;
  - **"after anomaly (2 days)":** scored steps whose zone had a flagged state in the preceding 2 days. Cleaning can only change a forecast through the history it reads, so the effect concentrates there.
- **Metrics:** MAE and RMSE in A; MASE (eq. 19) with a per-zone seasonal-naive scale on normal training steps; sMAPE.
- **Diebold–Mariano test (eq. 20):** on the per-time-step scaled absolute loss **summed** over the scored zones, with a Newey–West variance and Bartlett lag = the horizon (overlapping direct forecasts).
  - **Why the sum:** it makes the mean loss difference proportional to the pooled MASE difference.
  - A first version averaged over the zones. That weights a time step with one scored zone like one with fifteen, and it gave a loss difference of the opposite sign to the table: the S2 advantage sits in multi-zone anomalies. Comparisons: S1 vs S2, S0 vs S2 and S2 vs S3.
- **Injected datasets:** NB4's test datasets 3 % seeds 0–2 and 7 % seed 0, regenerated and checked against the stored truth. NB5 evaluates and selects nothing on them, so D63 is respected.
- **Outage statistics:** inside NB4's scoring area (clean region plus injected spans):
  - **truth:** the core spans of injected G1–G4. U_PARTIAL is not counted as an outage;
  - **naive (S0):** every flagged dead state;
  - **S1:** none, because interpolation erases them;
  - **typed (S2):** flagged dead states inside G-labelled items.
  - Reported as zone-hours, number of runs (≥ 3 steps), and the zone-step precision and recall of the typed outages.
  - On the real data, where there is no truth, the naive vs typed ratio is reported. It is the exact version of F26's 4.2×.

### D67 — Paper framing: the main detector keeps its name; the learned graph is presented as an ablation [author's decision, 2026-11-10]
- **Choice:**
  - The main detector stays the TCN-GAT multi-scale residual detector selected in D61. It is first in every table.
  - The learned graph is presented and analysed **as an ablation**: graph attention on vs off, everything else equal (D62). This is a highlighted part of the evaluation, not the source of the claimed gain.
- **The author's words:** "let's take ur recommendation, but we should highlight that we add the graph (as an ablation) no problem, to make our research more riche, but make sure that the graph is an ablation".
- **Why:**
  - F42 shows that removing the graph leaves detection equal or slightly better.
  - Switching the main detector would be a choice made on the spent test seeds (D63).
  - Presenting the graph as an ablation keeps the evaluation complete and honest. It also adds a result the field cares about: whether a learned graph helps on few-zone feeder systems.
- **Wording for the paper:**
  - "multi-scale neural residual detector (TCN-GAT)";
  - the graph component is "evaluated by ablation";
  - its contribution is "interpretability (learned cross-city dependencies, E20), not detection accuracy".
- **Where:** Table 7e and Fig 9b (`tools/ablation_summary.py`; the graph ablation is shaded and listed first), methods §6.2, paper_handoff §2 and §4.
