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

## Session 3 — 2026-11-08 — NB3: multi-scale residual detector and end model

**User requests:**
1. "Go for the NB3, the multi-scale residual detector and the end model."
2. Mid-session: "please use lightgbm, pywt, statsmodels; I will install everything for you".
3. Later: "you can give me the notebook and I will run it in Colab".

**Environment:**
- Installed lightgbm 4.7.0, PyWavelets 1.8.0 and statsmodels 0.15.0 locally with pip.
- **LightGBM crashed** with an access violation in `LGBM_DatasetSetField` on the real features.
  - Toy data worked, and every single parameter (and the full set) worked in isolation. The crash was intermittent and survived contiguous float64 arrays and a fixed thread count.
  - Decision (D39): an automatic fallback to scikit-learn's HistGradientBoosting for the whole call, with the backend printed. The Colab LightGBM run is the reference.
  - Robust STL (statsmodels) on 15 × 88,890 steps did not finish within 10 min, so non-robust STL is used (D49).

**Prototype (before the notebook):**
- Forecast vs nowcast MAE on clean steps: 0.0285 vs 0.0287. The neighbours' current values add nothing.
- MODWT energy check: x 3980.7, ours 3981.6, `pywt.swt` 3980.1.

**NB3, first full run (12.9 min, fallback backend):**
- γ = 103.8, recall G3 39 %, G4 29 %.
- The detector-only gallery showed method artefacts:
  - a score of 9,014 in the first week (empty baseline);
  - flags 8–10 h after real disturbances on normal data, because causal wavelet bands smear events forward.
- The hierarchy-test hypothesis (D40: the nowcast absorbs logger artefacts) was **not** confirmed: g is 227.9 (nowcast) vs 222.6 (forecast) for C06.
- Fusion turned the singleton G2 item into G3.

**Fixes:**
1. Phase-aligned MODWT bands, using group delays measured from impulse responses (4, 11, 25, 53, 43 steps; they match the analytical LA(8) shifts) (D42).
2. A 21-day warm-up and a 7-day minimum for the robust windows (D43).
3. γ's negative set excludes zone-steps within ±53 steps of a rule state in the same zone, or of a multi-zone rule state in the system (D43).
4. Symmetric ±53-step exclusion for detector-only candidates (D44).
5. End-model abstention on low-support classes in fusion (D50).

**Second run:** it failed in the hierarchy cell because `np.nanargmax` hit all-NaN scores for warm-up items. Fixed by leaving warm-up items out of the test (11 items, including the G2 candidate).

**Third run (12.9 min), results:**
- γ = 37.2.
- Recall: G3 94 %, G4 95 %, A1 3/3, A2 67 %, A3 52 %.
- Hierarchy by kind: dead g 3/3, dead v 96 %, fill g 1/6, fill u 33 %.
- 311 detector-only candidates: 151 other, 140 surges, 20 partial drops. The end model calls 301 of them N, i.e. untyped.
- End model: 96.8 % out-of-fold agreement with the label model; 100 % of normal windows → N.
- Fusion changes 4 labels.
- Findings F28–F34; decisions D39–D50.

**Documentation updated:**
- decisions D39–D50 (D40 rewritten with the result; D42–D44 rewritten after the fixes);
- findings F28–F34;
- methods §6–7 (eq. 27–29);
- results_summary §8;
- data_dictionary (detector_v1, end_model_v1);
- figures_and_tables (Fig 8, E16–E19);
- paper_handoff (status, corrections #30–35, contribution 3, RQ3, threats, claims, next steps);
- CLAUDE.md, README, requirements.txt.

**For the next agent or session:**
- When the user returns the Colab outputs (`results/detector_v1/`, `results/end_model_v1/`, NB3 figures, the executed notebook), replace the numbers in results_summary §8, F28–F34 and paper_handoff, and note the backend change here.
- Then NB4 (injection).

## Session 4 — 2026-11-08 — NB3 on Colab, a scale bug, LightGBM 4.6.0 locally, the reference run

**User requests:**
1. "How can I synchronise between Colab and my local machine to keep you updated?"
2. Installed Google Drive for desktop; asked to check that the repo is on Drive, then ran NB3 on Colab.
3. "I closed Foxit, check your fig8 and update."

**Sync set-up:**
- Drive for desktop in Streaming mode mounts `G:\My Drive`; the Drive copy of the repo is `G:\My Drive\grid-event-or-data-artefact` (no `.git`). Before the run, all 52 files NB3 reads were hash-identical to the local repo.
- A switch to Mirroring moved the Drive to `C:\Users\Dell\My Drive` and emptied G: while it downloaded; the user switched back to Streaming.
- **Colab left outputs unsent:** the figures reached Drive, the CSVs and `summary.json` did not, and the notebook was unsaved. Fixed by `drive.flush_and_unmount()` and Ctrl+S. NB3 now ends with that flush cell (D52).

**Run 2 — Colab, LightGBM 4.6.0, code of a9ec65a (11.1 min, 0 errors):**
- Committed as 21e6695 to keep a record.
- Close to the sklearn run on the predictors (MAE 0.0288 vs 0.0285) and on the hierarchy (dead g 3/3, dead v 0.958).
- **But nine B1 detector-only candidates on 16–18 Mar 2024 scored 3,973–15,182** (everything else < 293).

**Diagnosis (F35):**
- Boujdour has 3 zones, so its city median is one of them, and that zone's v is exactly 0.
- B1 was the median zone on 52 % of the V4-band window, so the median and MAD of |v| were 0 and z = |v| / 1e-6.
- The sklearn residuals stayed just below the 50 % line.
- Zeros biased every zone-level scale downward (v = 0 on 28–37 % of Boujdour steps).

**Fix (D51):** `robust_score` excludes structural zeros (|s| ≤ 1e-12) from the median and MAD. On the same residuals, B1's V4 score drops from 14,940 to 2.1. Diagnostic: `tools/diag_structural_zeros.py` → `results/detector_v1/structural_zeros.csv`.

**LightGBM locally (D52):**
- Colab ships 4.6.0. Installed 4.6.0 locally (`pip install lightgbm==4.6.0`): the south forecast ran in 121 s with MAE 0.0288, no crash. 4.7.0 is the crashing version.
- Pinned in `requirements.txt`. NB3's `summary.json` now records `lightgbm_version` and `colab`.

**Run 3 — local, LightGBM 4.6.0, with D51 (19.8 min, 0 errors) = reference:**
- Waited 22 min for Foxit to release `fig8_residual_hierarchy.pdf`; a locked PDF makes `savefig` fail.
- Results:
  - γ = 25.5 (south), 16.9 (Marrakech);
  - hierarchy consistency: forecast 0.714, nowcast 0.694, STL 0.621;
  - by kind: dead g 3/3, dead v 0.915, fill g 1/6, fill u 0.550, fill v 0.651;
  - recall: G3 18/18, G4 95 %, A2 79 %, A3 53 %;
  - 290 detector-only candidates: 143 other, 114 surges, 33 partial drops; 42 multi-zone;
  - end model 94.7 % (95.7 % without detector features);
  - fusion changes 3 labels (the three vote-less linear fills → A3).

**How the three runs compare** (south; sklearn a9ec65a / Colab LightGBM before the fix / reference):

| Quantity | sklearn | LightGBM, before fix | Reference |
|---|---|---|---|
| Forecast MAE | 0.0285 | 0.0288 | 0.0288 |
| Nowcast MAE | 0.0287 | 0.0292 | 0.0292 |
| γ south | 37.24 | 33.35 | 25.51 |
| Hierarchy (forecast / nowcast / STL) | 0.738 / 0.752 / 0.699 | 0.772 / 0.791 / 0.699 | 0.714 / 0.694 / 0.621 |
| Dead v / fill u / fill v (forecast) | 0.958 / 0.325 / 0.779 | 0.958 / 0.350 / 0.849 | 0.915 / 0.550 / 0.651 |
| Recall A2 / A3 / G3 / G4 | 0.667 / 0.523 / 0.944 / 0.946 | 0.737 / 0.511 / 0.944 / 0.946 | 0.789 / 0.534 / 1.000 / 0.946 |
| Detector-only candidates | 311 | 323 | 290 |
| End model, all features | 0.968 | 0.957 | 0.947 |
| Fused label changes | 4 | 5 | 3 |

- **What is stable:** clean-data MAE, outage localisation (dead g 3/3, dead v > 0.9), the nowcast adding nothing, the end model reproducing the label model, and the three vote-less linear fills → A3.
- **What moved:** fill localisation, γ and the detector-only list. The forecast/nowcast order on hierarchy consistency flips between runs, which confirms it is noise.

**Figures checked visually:**
- Fig 8 and E16–E19 are correct.
- Cosmetic issues are left for NB7: Fig 8 repeats day labels on its x-axis; E19(b)'s legend overlaps a bar.

**Documentation updated:**
- results_summary §8 (rewritten);
- findings section D (F28–F34 rewritten, new F35);
- decisions D40 result, D43 note, new D51–D52, D39 superseded note;
- methods eq. 15 as implemented;
- paper_handoff (status, §1, correction #36, contribution 3, RQ3, threats 11, 12, 15);
- data_dictionary (`structural_zeros.csv`, summary keys), figures_and_tables, CLAUDE.md (LightGBM and Colab sync sections), README, docs/README.

**Generator note:** `tools/make_nb3_detector_end_model.py` changed (flush cell and summary keys). The notebook was regenerated and executed from it, so they match. The D51 docstring in `src/detector.py` was edited after the run (text only).

**For the next agent or session:** NB4 (injection). Use the injection additions in paper_handoff §8. Add one for F35: a multi-zone event in Boujdour (3 zones) to check the zone-level scale after D51.

## Session 5 — 2026-11-08 — Paper note on the nowcast; NB4 written (TCN-GAT + injection benchmark)

**User requests:**
1. "Are we already implementing the graph? yes or no." Answer: no. NB3's nowcast feeds every other zone's current value to LightGBM as plain features (a fully connected "graph" with no learned edges), and NB3's hierarchy is a fixed median tree.
2. Add to the paper: the nowcast is a fully connected "graph" with no learned edges; it adds nothing (MAE 0.0292 vs 0.0288), so it is only a comparison and a feature, not the main residual. → `paper_handoff.md` ("Text the author asked to include") and `methods.md` §6.
3. "For NB4, add the TCN-GAT (to add value to our work) and the injection benchmark. Don't skip the graph." Put NB4 on Drive; the author runs it on Colab.

**Code:**
- `src/rules_v1.py`: `build()` split into `build_from_data(raw, data)` so the rule engine can run on injected series. Output unchanged (items identical to catalogue_v1).
- `src/detector.py`:
  - `predict_rho` split into `fit_rho_models` / `apply_rho_models`, so models fitted on the real data can predict injected data. Predictions are identical to before (checked against the pickled LightGBM 4.6.0 forecast);
  - `stl_residual(jumps=True, n_jobs)`: R-style smoother jumps, 183 s → 3 s, residual correlation 0.9999 with the default. NB3 still uses the default.
- New `src/graph_model.py` (D53, D55): the TCN-GAT and its no-graph ablation.
  - The first version computed the TCN once per 1-day window and was far too slow on CPU (> 10 min for 2 small epochs). It was rewritten fully convolutional over contiguous chunks; outputs are chunk-independent (max diff 1.2e-7) and an epoch takes about 15 s on CPU.
  - A softmax over all-masked neighbours gave NaN; it was fixed with a large negative logit plus explicit zeroing.
- New `src/inject.py` (D54) and `src/benchmark.py` (pipeline rerun, baselines, metrics, threshold sensitivity).
- New `tools/make_nb4_benchmark.py` → `notebooks/NB4_benchmark.ipynb` (resumable, D58) and `tools/sync_drive.py` (repo ↔ Drive by MD5).

**Local checks:**
- **TCN-GAT and TCN fully trained on CPU** (40 epochs max, patience 6; stopped at 29–36 epochs, about 17 min per model). Clean-data MAE on the real data: TCN-GAT 0.0294, TCN without graph 0.0299, LightGBM forecast 0.0288. The learned graph helps the TCN a little, and LightGBM stays slightly ahead. The models are saved in `results/benchmark_v1/models/` (`tcn_gat.pt`, `tcn.pt` in git; the 73 MB LightGBM pickle is git-ignored and copied to Drive only). NB4 loads them, so Colab does not retrain.
- **One injected dataset end to end** (3 %, seed 0, tiny TCNs; mechanics test, not results):
  - 244 events (26–29 per type), 3.03 % of clean zone-steps;
  - all stages run; 729 s, of which STL took 462 s under CPU contention, hence the jumps;
  - every typed event was detected;
  - attribution macro-F1 ≈ 0.91; the main confusions are G3 → G4 and A1 → G1;
  - dropping the interpolation rule family lowers label-model accuracy 0.91 → 0.64;
  - unflagged shared shocks: forecast raw 0.18 vs nowcast raw 0.06 recall (the F29 concern appears on injected data).
  - **These numbers are from one seed and are not citable.** The Colab run produces the real ones.

## Session 6 — 2026-11-08 — Pre-run check of NB4 on Drive

**User request:** before running NB4 on Colab, check that everything it needs is on Drive. Confirm whether the work has a multi-scale graph-based anomaly detector and a multi-scale graph residual detector.

**Drive check:**
- `tools/sync_drive.py --dry-run`: 140 files, all identical by MD5. This includes the data xlsx, `src/`, the catalogue and detector inputs, NB4 and the three model files.
- Drive for desktop's local metadata database (copied to scratch and read; not modified) gives every key file a cloud id with the right size, and has 0 pending operations. The upload to Google Drive is complete, including the 73 MB LightGBM pickle.
- `tcn.pt` and `tcn_gat.pt` load with `weights_only=True`, so torch ≥ 2.6 on Colab can read them.

**Changes:**
- NB4 generator: the LightGBM pickle is loaded in a `try` block with a forecast smoke test, and refit if either fails (D58).
- The notebook was regenerated, and its first three cells (setup, panel, model loading) were run locally: OK. Before the edit, the generator output matched the notebook exactly.
- `tcn.pt` and `tcn_gat.pt`: the stored training config said `epochs=30, patience=4` because the models were saved without the training config. The histories show the real values, `epochs=40, patience=6`: each fold stops exactly 6 epochs after its best validation epoch, at 28–35 epochs. Only the stored config was corrected; the weights were checked bit-identical.

**Answer on the graph detector:**
- The two names describe one component, run in NB4 as the variant `TCN-GAT, hierarchy, multi-scale`:
  1. residual e = ρ − TCN-GAT prediction (learned graph: same-city edges plus learned top-4 cross-city edges, 2-head attention; D53);
  2. phase-aligned MODWT bands;
  3. region/city/zone median hierarchy per band;
  4. robust scores, then the max over bands and levels;
  5. γ threshold.
- Its ablations are `TCN-GAT (raw, hierarchy)` (single scale) and `TCN, no graph (raw, hierarchy)` (no graph).
- The main pipeline (end model, fusion, attribution in Table 6) still uses the LightGBM-forecast multi-scale detector. The graph detector is compared on detection (Table 5, recall by type, Table 7 ablations, hard negatives), not on attribution.

