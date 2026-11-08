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
