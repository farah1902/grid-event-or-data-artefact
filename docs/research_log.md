# Research log

Chronological record of every work session: what was asked, what was done, what was found, and what went wrong.
Agents append a new section per session (see `CLAUDE.md`). Decisions are D… (`decisions.md`) and findings F…
(`findings.md`).

---

## Session 1 — 2026-11-07 — Orientation, verification, evidence figures, repository

**User requests (in order):**
1. Read the research guide and create memory to start working on it.
2. "Should I run rules_v0? Where do I start?"
3. Verify that `out_check` and `event_catalogue_v0` are identical, then write a notebook that plots everything needed. The user said external validation (step 3 of the guide's week) was not important to them, that they don't care about the timeline, and that they want to accelerate.
4. Push all code, CSVs, md files, results, figures and notebooks into a well-structured repository.
5. Install the GitHub CLI and push.

**Work done:**
- Read the guide in full and created the agent memory (project, status, decisions, user profile).
- **Reproducibility (D01):** the user had already run `rules_v0.py` into `out_check/`. All 4 CSVs match `event_catalogue_v0/` exactly, except for the order of tied rows and CRLF.
- **NB1 (`notebooks/NB1_evidence_figures.ipynb`):**
  - Built from a generator script (now `tools/make_nb1_evidence_figures.py`), executed with nbconvert, and inspected figure by figure.
  - Figures: Fig 1, 3, 4, 5 (plus 5 supplementary clock dates) and E1–E8.
  - Numbers matched the guide: C05 holds of 216–402 points; C12 L1 = 73.598 A and L2 = 63.652 A over 257–258 steps; C09 η = 1.00 and π = 1.38 (v0); κ = 0.07 for C11; 57/68 single-zone events in 06–11 h; F level −50 % and midday/evening ratio 0.89 → 1.03; δ\* = 60 min (sign −) in all 3 cities in Oct 2022.
- **Discovery of straight-line interpolation (F01):** six F zones in Fig 3 were straight lines with a constant first difference (std ≈ 1e-14). A dataset-wide count gave 275 runs in 102 groups, 48 spanning ≥ 2 zones. The C09 re-read followed: L was interpolated, not normal (F03).
- **Notebook fixes made after looking at the figures:**
  - E1's main panels were stuck on the zoom window (`sharex=True` across columns → `sharex="col"`).
  - Annotations overlapped in Fig 4.
  - Map labels collided in Fig 1 (three iterations).
  - G4 used the hold colour (changed to a blue grid-event hue).
  - A docstring inside a generated cell string broke the generator.
- **Repository (D02–D04):**
  - The project folder sat inside a git repository rooted at `C:\Users\Dell` (remote ESA_LandCover_Streamlit). A new, separate repo was created instead.
  - The folder was restructured (`data/raw`, `docs`, `src`, `notebooks`, `results`); the guide was renamed to `docs/research_guide.md`; duplicates were moved to the git-ignored `_local_archive/`.
  - The old `figures/` folder could not be removed (a PDF was open in a viewer), so it is git-ignored.
  - NB1 paths were updated and the notebook re-executed. `rules_v0` was re-checked from its new location (identical).
- **GitHub:**
  - `gh` was not installed; installed `GitHub.cli` 2.103.3 with winget.
  - Web device login (the user approved code 5E5C-B71C).
  - `gh repo create grid-event-or-data-artefact --private --source . --push`.
  - First commit `b47840c`.

## Session 1 (continued) — 2026-11-07 — Rule engine v1

**User request:** add R3–R6, R11, R12, R15 and the new linear-interpolation rule.

**Threshold checks on the data before coding:**
- Noise-floor-only dead runs (no exact zero), ≥ 3 steps: L 6, B 3, F 11, M 43. M max length 139 steps → D15.
- Marrakech zone 2 hold runs: 125 of ≥ 6 points, 38 of ≥ 8, 8 of ≥ 12 (median 30 kW, 100 % integer values) → D17.
- Laâyoune short holds: 1,097 runs of ≥ 3 points but only 25 of ≥ 6. They are simultaneous across all 5 zones and stop in Apr 2023 → F09, D18. Boujdour zone 2 has 334 natural short repeats → F10.

**Implementation:** `src/rules_v1.py` (items, episodes, 19 rules). First run: 134 dead, 141 fill, 33 clock and 13 transfer items, about 28 s.

**Problems found on inspection, and fixes:**
1. R7 fired 0 times. Kept: it's a finding (F07).
2. R15 fired on 18/33 dates, including Ramadan dates and Marrakech fits with correlation 0.09–0.30 → fit-quality guard (D21) → 6 votes. New: B on 2024-03-31, +60 min.
3. The inspection majority label hid the C09 conflict → it now emits `conflict:A1|G?`.
4. The 24 Dec 2023 L2/L3 "noise floor" was the low end of a straight line from 0 → state priority (D16). This also re-segmented C01 (F06).
5. 25 of 117 southern dead runs restore through a straight line (F05) → restoration is measured after the ramp (D22). C02's r went from 0.22 to 1.01.

**NB1b (`notebooks/NB1b_rules_v1.ipynb`):** Fig 7, key-event mapping, v0 → v1 comparison (70/72 same start), E9 vote matrix, E10 (C01), E11 (short freezes). E11 led to the daily-freeze finding: 120/218 freezes start in the 08:00 hour, one per day on 186 days (F09). E9 showed multi-zone linear fills clustering in 08:00–10:30 (F08).

**Also:** `src/viz.py` (shared style, stacked-zone plot); README updated. Commit `a4ab780`, pushed.

## Session 2 — 2026-11-08 — Label model (NB2) and full documentation

**User request:** "tackle NB2 now, but note every single information, decision, behaviour and everything you do on the GitHub repo to help another Claude agent to write the paper. Do more."

**Label-model development (each step was driven by a failure on the real votes):**
1. Before coding, the guide's eq. 10–11 (fired rules only) was found to be uninformative with single-label rules (F20) → abstention is modelled (D28).
2. **First fit:** unconstrained DS with kind gating only. Restarts agreed on 19–100 %; the best solution put C06 and C12 in G3, every single-zone item in G4 and every transfer in N (F21).
3. **One-coin constrained model** (D32). Restarts were still unstable, and degenerate classes appeared:
   - all clock items → A4, all transfers → G5;
   - G4 collapsed into G3 (R10 ⊂ R9);
   - single-zone holds → A2.
4. Added **level-based feasible classes** (D29), **applicability domains** (D30), **R9 speaks for {G3, G4}** (D31) and **Beta(1, 9) on false-positive rates** (D32). Restarts now agree 100 %, but:
   - G4 still absorbed outages (R10 propensity 0.59);
   - C11 went to N;
   - missing-hour dates went to N.
5. Added **defining-rule propensity priors** (9, 1) (D33) and split the clock rules by clock direction (R13 vs R14 domains, D30). Remaining problems: vote-less fill items → A3 at 100 % (N had emptied), and C11 → N.
6. Added a **Dirichlet(1) prior on π** (D34). Final: stable and sensible. C06/C09/C12 → A1 (0.93–1.00), 26 Sep 2022 → G2 (0.99), C11 → G5 (0.68), vote-less fills ≈ 0.5.
- Known limitation kept and documented: the C12 tail item on L1 → G4 (0.96) (F25).

**NB2 (`notebooks/NB2_label_model.ipynb`, about 80 s):**
- Constrained DS vs the guide's full DS vs majority vote.
- Learned parameters (E12), confidence (E13), key-event posteriors (E14).
- Parameter recovery over 20 seeds: constrained 0.922 accuracy and ECE 0.033; full 0.682 and 0.276; MV 0.911.
- Robustness to rule families and priors (E15).
- Labelled items (`q.csv`) and episodes.
- New findings:
  - R5 is uninformative (log(a/b) = 0.12) (F16).
  - The defining-rule prior and the calendar family each move 39 % of dead labels (F24).
  - Artefact zone-hours outnumber grid-event zone-hours about 9:1 in the south, and naive zero = outage overstates outage time about 4.2× (F26, provisional).

**Documentation written:**
- `CLAUDE.md`;
- `docs/decisions.md` (D01–D38), `docs/findings.md` (F01–F27);
- `docs/methods.md` (implemented method, new eq. 21–26), `docs/results_summary.md`;
- `docs/data_dictionary.md`, `docs/figures_and_tables.md`, `docs/paper_handoff.md` (including corrections #14–29 to the guide);
- this log.
- Notebook generators copied into `tools/`.

**Behaviour notes for future agents:**
- Windows plus Git Bash.
  - Heredocs with complex quoting failed twice; writing Python patch scripts to files was more reliable.
  - The `gh` binary is not on the bash PATH.
- nbconvert prints debugger warnings about frozen modules; they are harmless.
- The pandas FutureWarning on `fillna` downcasting in `label_model.applicability` was removed when the R14 domain switched to spring-forward dates.
