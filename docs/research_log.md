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


## Session 6 (continued) — 2026-11-08/09 — The graph detector becomes the main detector; NB4's evaluation made fair

**User request:** "I want to present it [the multi-scale graph residual detector] as the main detector in the paper, and also make it more powerful than any other model. If LightGBM is the best, keep it and do a best benchmark, but always keep the graph at the top."

**What was done:**
1. **Development study 1** (`scratchpad`, NB3 event formation, seeds 100–104):
   - LightGBM-MS beat every graph design: TCN-GAT-MS, the mean of the two predictions, level splits (g from LightGBM, u/v from the graph) and score ensembles.
   - This exposed **F36**: the scoring area excluded NB3's LightGBM candidates, which hid only LightGBM's false alarms.
   - Rerun with a rule-based area: LightGBM 0.681, mean 0.672, TCN-GAT 0.649.
2. **Hybrids (D59):** `graph_model` got a `base=` input (LightGBM forecast + learned correction; the attention also reads the neighbours' current LightGBM residuals).
   - Trained on CPU: 338 s (graph) and 475 s (no graph).
   - Both end at LightGBM's MAE, 0.02879, with flat validation loss (**F37**). The mean of LightGBM and TCN-GAT has MAE 0.02821.
   - The old TCN-GAT still loads with an identical MAE (0.02945).
3. **Benchmark refactor** (`src/benchmark.py`):
   - variant table (`VARIANTS`), `Benchmark(main=, settings=)`, `predictions()`, `raw_scores()`;
   - `pipeline()` runs the whole method on any dataset, including the real one; `run()` = `pipeline()` + metrics;
   - event formation per detector (`smooth_score`, `gamma_of(q)`, `max_gap`); ablations inherit the main detector's setting;
   - `set_background()` adds the `*_bgx` metrics;
   - rows with NB3's event formation for TCN-GAT and LightGBM.
   - Checked end to end on one injected dataset (298 s on a busy CPU).
4. **`tools/dev_select_detector.py` (D60):** a grid over w, q and gap for the main candidates and the baselines, on seeds 100–104.
   - The first grid (18 settings) had its optimum on the upper edge, so it was extended twice, to 48 settings.
   - Final: TCN-GAT 0.786 alone (24, 99.9, 12) vs LightGBM 0.759 (24, 99.8, 6); TCN-GAT wins all 10 cells.
   - Full method: 0.863 vs 0.849. **Main detector = TCN-GAT, hierarchy, multi-scale (D61)**, chosen by the rule fixed in the tool before the extensions.
   - Rules alone 0.888 (**F40**). STL has the best step-wise AUC-PR (**F39**).
   - On the first grid LightGBM had led; the ranking changed only once larger settings were allowed, for every detector alike (**F38**).
5. **NB4 generator:**
   - main detector and settings read from `dev_selection.json`; rule-based scoring area;
   - the four graph models trained or loaded (hybrids with `base=PF`); predictor comparison with the hybrids and the mean;
   - E20 shows the TCN-GAT graph, and the edges of both graph models are saved;
   - graph detectors right after the main detector in Tables 5 and 7b and in Fig 9; Wilcoxon tests of the main detector against every other detector;
   - Table 5 also gives F1 with own background excluded and the real-data alarms;
   - new §8b: the real data through the whole method with the main detector → `results/main_detector/` (compared with NB3);
   - hard negatives use each detector's own event formation;
   - QUICK mode writes §8b into `results/benchmark_quick/`.
6. **Docs:** D54 marked corrected; D59–D61; F36–F40; results_summary (NB3 marked superseded for the south; new §8b); methods §6.1 (eq. 29′); paper_handoff (status, text for the paper, contribution 3, RQ3, threats 16–18, claims not to make).
   - A LaTeX block in methods §6.1 was first written through a non-raw Python string (`\t`, `\f`, `\r` were turned into control characters); it was repaired.

**Honest reading for the paper:**
- The graph detector wins on event detection after fair tuning, because its excursions fragment less once smoothed.
- It does not improve prediction (F37) or step-wise ranking (F39).
- Under strict counting it does not raise the rules' event F1 (F40).
- The NB4 test seeds decide the final numbers.
- **NB4 QUICK test of the new notebook** (local, 2 datasets at 3 %, 2-epoch networks, so its detector numbers are not meaningful): every cell runs.
  - It found a fusion bug (D56): detector-only items were labelled A1. It is fixed in `benchmark.fused`.
  - The QUICK copy had been generated before §8b's QUICK output folder was fixed, so it wrote into `results/main_detector/`. That folder was deleted; the Colab run will create it.

## Session 7 — 2026-11-10 — NB4 results pulled and analysed; no-graph ablation; NB5 written

**User request:** "ok done, check, analyze and continue ur work please" (after the NB4 Colab run).

**Check of the Colab run:**
- All 30 benchmark runs and the 21 threshold-sensitivity runs are on Drive. So are every table, `summary.json`, `results/main_detector/`, Figs 9–11, E20, E21 and the executed notebook (saved 23:45).
- All run files were written on 9 Nov, 21:04–23:22, after the 01:09 code sync. Every `_info.json` names the TCN-GAT main detector.
- Colab disconnected once and resumed (the run cell only logs r07_s02–s09).
- The models were loaded, not retrained: the predictor MAEs equal the local ones.
- No errors or stderr output in the executed notebook.
- Pulled with `tools/sync_drive.py --pull results/benchmark_v1 results/main_detector results/figures notebooks/NB4_benchmark.ipynb`.

**Analysis (findings F41, F43–F50; numbers in results_summary §9):**
- **The graph detector is the best detector at 3 % and 7 %** (p ≤ 0.02 against each of the seven others) and tied at 1 % (F41). The development ranking generalised.
- **Rules + detector vs rules alone** depends on how alarms are counted and on the rate (F44). Strict: worse at 1 %, equal at 3 %, better at 7 %. Own background excluded: better at every rate, 10/10 seeds. Zone-strict: worse at every rate.
  - New measurement from `runs/*_pred.csv`: 25–75 % of the in-scope detector-only candidates overlap an injected event in time but on other zones. This is spill-over through the region and city parts of the score.
- **Ablations (F43):** multi-scale helps at 1 % and 3 %. The flat residual matches or beats the hierarchy on event F1 at 1 % and 7 % and on AUC-PR everywhere. The hierarchy is a localisation device, not a detection gain.
- **Tuning costs short shocks and onset timing** (F45): U_SHOCK 0.21 vs 0.77 at 3 %; median onset error 140–168 min.
- **Attribution (F46):** the label model does not beat majority vote on injected data, and fusion matches both. The end model alone is worse, and detector features do not help it.
- **Multi-city zero gaps → G1** through the simultaneity family (F47). Without that family, A1 accuracy rises from 0.697 to 0.834.
- **Threshold sensitivity, hard negatives, real-data catalogue:** F48, F49, F50.
- **Interpretation pitfalls found and documented:**
  - Table 5's `real_data_alarms` (191 for the main detector) counts all detector alarms, whereas the development tables counted the 70 detector-only candidates.
  - Fig 11's ECE is pooled over seeds; Table 6 gives the per-seed mean.
  - The 11 G2 → N cases in Fig 10 are the city outages the rules miss: the detector finds them, but labels them N.

**NB5 (downstream test), written and executed locally:**
- **Code:** `src/downstream.py` (masks, cleaning S0–S3, global LightGBM direct forecaster, naive reference, MASE, DM test, outage statistics) and `tools/make_nb5_downstream.py` → `notebooks/NB5_downstream.ipynb`. Decisions D64–D66.
- **Runtime:** 17.5 min on CPU (about 20 s per LightGBM fit). Outputs are cached in `results/downstream_v1/`, so a re-execution only redraws.
- **Bugs met while building it:**
  1. a helper named `rows` was shadowed by a local list (renamed `rowmask`);
  2. the first Diebold–Mariano loss averaged the zones within each time step, which reversed the sign of the day-ahead LightGBM difference relative to the pooled MASE. It now sums over zones (D66);
  3. the naive reference used a one-day lag at both horizons. It now uses persistence at 1 h.
  - Fig 12 was first drawn with truncated y-axes and the "all steps" subset for the real data. It now uses the after-anomaly subset in both panels, with axes from 0 and value labels.
- **Results:** F51–F54, results_summary §10. F26 was confirmed exactly: 4.15×.

**No-graph ablation of the main detector (D62, F42):**
- **The gap:** NB4 compared the TCN-GAT with a no-graph TCN only on the raw band. `benchmark.V_TCN_MS` was added to `VARIANTS` and to the NB4 generator. The executed NB4 notebook was **not** regenerated, so that the Colab outputs stay intact; the generator is now one row ahead of it.
- **The computation:** `tools/graph_ablation.py` computes the row on the NB4 datasets (regenerated from their seeds and asserted equal to `runs/*_truth.csv`).
  - A first run crashed after the development phase: `detector_items` needs zone-run columns on its empty frame. It was fixed and resumed from the cached development grid.
  - Runtime: about 8 min for development and about 45 s per test dataset on CPU, longer while NB5 ran in parallel.
- **Reproduction:** the CPU recomputation equals the Colab GPU rows in 30/30 runs.
- **Result:** without the graph, the detector is equal or slightly better on the development data (0.794 vs 0.786 at its own setting) and on the test seeds (0.671 / 0.817 / 0.857 vs 0.644 / 0.813 / 0.854 at the same setting; significant at 1 %).
  - The main detector's advantage comes from the neural residual and event formation, not from the graph.
  - Per D63 the main detector is unchanged. The framing is left to the author (paper_handoff, "open decision").

**Framing of the graph, and the repository update (same session, after the user's reply):**
- **User request:** "let's take ur recommendation, but we should highlight that we add the graph (as an ablation) no problem, to make our research more riche, but make sure that the graph is an ablation (u can do ur best); also before moving to the NB6, update the github repo (readme and others) for all this final results (based on NB4 and 5)".
- **D67:** the main detector keeps its name (TCN-GAT, D61), and the learned graph is presented as an ablation (graph on vs off).
- **`tools/ablation_summary.py` (new):** builds Table 7e (`results/benchmark_v1/table7e_ablations_main_detector.csv`) and Fig 9b (`fig9b_ablations`) from the stored per-run files. It covers every ablation of the main detector at the three rates, with paired Wilcoxon tests, the graph ablation first and shaded.
  - The figure's palette (project red and purple) was checked with the dataviz validator: all checks pass.
  - Label collisions with the zero line were fixed in two passes.
- **Paired tests that refine F43:** the flat-residual ablation is not different from the main detector at 1 % and 7 % (p = 0.16, 0.38) and significantly worse at 3 % (p = 0.014). F43 was corrected: the hierarchy does not hurt detection, and it helps at 3 %.
- **Docs updated:**
  - methods §6.2 (the graph ablation) and §8 (downstream test);
  - findings F42 (resolved) and F43 (paired tests); results_summary §9.2c;
  - paper_handoff (framing decided, storyline item 6);
  - figures_and_tables, data_dictionary, docs/README (register ranges), CLAUDE.md.
- **Root README rewritten for the final state:**
  - method overview;
  - main results of the real data, NB4 (with the graph as an ablation) and NB5;
  - main figures, repository layout and the reproduce order (including `graph_ablation.py`, `ablation_summary.py` and NB5).
- **Tooling note:** a long bash heredoc failed again ("unexpected EOF"), so the README was written with the file tool. Multi-line doc edits use a small script that tries both line endings, because the docs mix CRLF and LF.

## Session 8 — 2026-11-10 — NB6: transfer to Tetouan

**User request:** "let's attack NB6 and see how our model can easily detect everything (let's talk with more confidance bro !!)".

**Data audit:** the UCI Tetouan series is pristine (no zeros, no duplicate or missing stamps, no hold or linear-fill runs). That makes it a clean false-alarm test. Recall must come from injected Morocco signatures.

**Code made general for a third, single-city system** (D69). The Morocco regression was rerun after each change: catalogue_v1 items, votes and zone runs identical; label-model `predict` equals the fitted q on Morocco (max difference 0.0); injector r03_s00 truth identical; TCN-GAT MAE 0.0294.
- `label_model.DawidSkene.predict`: frozen-parameter E-step.
- `inject.Injector`: single-city patterns and `sample(types=)`.
- `graph_model`: dynamic `detector.SPLIT`; top-k clamped.
- `detector.build_panel`: any named system. 2017 calendar entries in detector and rules_v1.
- **Rule engine on a series with no anomaly at all,** which had never happened: `zone_runs` returns typed empty columns, `clock_items` accepts an empty audit, and `build_from_data` skips empty item kinds. Each surfaced as a crash on Tetouan and was fixed in turn.
- `src/transfer.py` (new): registration, loading, frozen label model, predictors trained on Tetouan, scores, event formation and metrics.

**Run:** `tools/make_nb6_tetouan.py` → `notebooks/NB6_tetouan.ipynb`, executed locally in 13.1 min (predictors trained by a prototype run and reloaded: TCN-GAT 73 s, TCN 33 s).

**Results (F55–F58, results_summary §11, Fig 13, E22):**
- Zero false rule items on the clean year.
- The main detector has the fewest real alarms (7).
- Full method F1 0.945 / 0.919 / 0.890 at precision 0.98–1.00, above the rules alone at every rate (10/10 seeds).
- The detector alone: main best at 1 %; LightGBM and STL better at 3–7 %, because the neural predictors are data-hungry (MAE 0.045 vs 0.011).
- Attribution macro-F1 0.77–0.79, or 0.95–0.98 without A1. A1 → G2 in 348/417 is the single-city limit.

**Transfer audit and protocol diagram** (same day, after the user asked whether every step, fix and adaptation of the transfer is in the repo, and for a diagram):
- **Audit:** the NB6 commit diff was checked line by line against D68–D70. Six details were missing (units, unused weather columns, the single-city A2 split and compound, the per-dataset baseline fits, timestamps as recorded, the prototype training). The hold, linear-fill and injector code was re-read to confirm that the kW-vs-A switch needs no change.
- **New `docs/transfer_protocol.md`:** the complete register, with components, values, status (frozen / re-estimated / adapted / engineering), code locations, regression checks and the chronology from file modification times. No file changed after the first injected Tetouan result.
- **New Fig 14** (`tools/make_transfer_diagram.py`): the protocol stage by stage, with results read from `summary.json`. Layout was fixed in three passes: a stray arrow, hyphen and formula wraps, spacing.
- D71; README embeds Fig 14 and links the register; docs index, figure register, handoff (storyline item 9) and CLAUDE.md updated.

## Session 9 — 2026-11-10 — NB7: final figures, tables and the released catalogue

**User request:** "yes ready for the NB7 (focus on this step without missing anything please)".

**Inventory first.** From the figure register, the handoff, the guide's figure plan and the fixes noted along the way:
- figures never drawn: Fig 1 basemap, Fig 2, Fig 6;
- fixes: Fig 8 axis, E19 legend, Fig 9 graph row, E22 legend;
- stale versions: E4 (v0 features), E6 (v0 types), Fig 1(b) (D16 masks);
- tables: Table 2, Table 4;
- the catalogue release (contribution 4).

**Done:**
- `src/paper_figures.py`:
  - the final catalogue (404 entries; D72);
  - Fig 1 with a Natural Earth basemap (downloaded v5.1.2, public domain), no boundaries (Western Sahara is disputed), a southern inset and Tetouan (D73);
  - Fig 2 (nine schematic signatures; the A1 panel shows the compound hold → zeros);
  - Fig 6 (two lanes, end model and fusion, catalogue, evaluations).
- `src/paper_regen.py` (D74):
  - Fig 8: scores recomputed with the saved LightGBM models; F29 reproduced exactly (218.0 / 232.6), and NB7 asserts it;
  - Fig 9 with the graph-ablation row;
  - E4, E6, E19 and E22.
- `src/paper_tables.py` (D72, D75):
  - Tables 1–4 and S7 built; Tables 5–9 and S1–S6 copied;
  - the numbered figure set and MANIFEST.md with draft captions;
  - the catalogue release with a README data card.
- `tools/make_nb7_final_figures.py` → `notebooks/NB7_final_figures.ipynb`, executed locally (1.1 min, no errors).
- **paper_handoff §3 corrections:** #30 brought up to date; #37–#40 added (per-detector event formation, no deep forecaster, no A4 re-alignment, Tetouan re-estimation scope).

**Visual checks and fixes:**
- Fig 1: label collisions → southern inset; scale bar under the inset; inset spines hidden by the global style.
- Fig 2: notes touching traces; A1 vs G1 made explicit with in-panel notes.
- Fig 6: a crossing arrow removed; boxes resized; the fusion formula rendered with mathtext.
- Fig 8: legend over the plateau → headroom.
- E6: legend for the clock days.

**Pitfalls:**
- bash heredocs turn `\\n` into a newline (scripts written with the file tool instead);
- `transfer.register` moves `detector.SPLIT` (restored in NB7);
- the corrections-table parser needed escaped-pipe handling.

## Session 10 — 2026-11-13 — External review: 1.88, outage statistics on all 30 test datasets

**Context:** the author shared the repository with another Claude instance for a review and asked for an answer without code changes. The answer checked every number in the review against the repo:
- correct: the full-method vs rules numbers (F44), label model vs majority vote (F46), the guide-style Dawid–Skene restart agreement (63 % minimum, F21), the graph ablation (F42);
- **correct and fixed here:** the naive outage mean is 1.88, not 1.89 (the docs averaged rounded ratios); the outage result rested on 4 datasets;
- **incomplete in the review:** it left out the view with each method's real-data background excluded (ours better at every rate, 10/10 seeds; F44), the recall gain (F44), and the Tetouan transfer, where rules + detector beat the rules alone at every rate (F56). Those stay in the paper next to the strict view.
- Open questions for the author (journal, framing, manuscript format, front matter, emailing the dataset authors) were answered with recommendations and left to the author.

**User request:** "ok go and push then we continue".

**Done:**
- **1.89 → 1.88** in README, results_summary §10.1 (with a note on the cause), F52 (and +89 % → +88 %), paper_handoff (four places).
- **`tools/outage_all_datasets.py` (D76):** NB5's outage code, unchanged, on all 30 NB4 test datasets (1 / 3 / 7 %, seeds 0–9), each regenerated and checked against `runs/*_truth.csv`. Reproduces NB5's 4 datasets exactly (asserted). Adds a breakdown of where the extra outage hours come from. Full run 58.2 min on CPU (0.5–4 min per dataset, longest at 7 %).
- **Result (F59, results_summary §10.1b):** typed 1.26 ± 0.24 × truth vs naive 1.88 ± 0.32; typed closer in 30/30 (p = 0.002 at each rate, 1.9 × 10⁻⁹ pooled); 99.98 % of the typed excess lies inside injected A1 spans, so the residual is exactly the A1 → G1 confusion (F47). The 4-dataset typed mean (1.36) was on the high side.
- **Fig 12 regenerated by NB7** (`paper_regen.fig12_downstream`): panels (a), (b) unchanged (Table 8); panel (c) now shows the 30 datasets (seeds as points, mean ± sd per rate and pooled). Caption updated in MANIFEST.md; new table `Table8_outage_all_datasets.csv` (28 tables). NB7 re-executed (1.9 min, no errors; Fig 8 check passes). NB5's executed notebook still shows its 4-dataset panel (c): the paper figure is NB7's.
- **Docs:** D76, F59 (F52 header points to it), results_summary §10.1b, figure register, data dictionary, handoff (status, outage claims, RQ4, "do not claim" list), README, CLAUDE.md, docs index.

**Pitfall:** re-executing NB7 rewrites every PDF with a new timestamp although the content is unchanged (the PNGs are byte-identical); the timestamp-only PDFs were restored from git, so only Fig 12 changed.

## Session 11 — 2026-11-13 — Paper writing starts: journal, framing, outline

**Author's decisions (2026-11-13):**
- journal: **Applied Energy**;
- framing: data findings and weak supervision first, the detector as a complement (with the Tetouan transfer), and **the value of the work made explicit**;
- format: **LaTeX** (Elsevier `elsarticle`) in `paper/`;
- front matter (authors, affiliations, funding, CRediT): later;
- no email to the dataset authors (the author has already asked about the data).
- Working rule set by the author: step by step, every figure, table and equation placed deliberately; **every external reference verified on the web, never from memory**.

**Journal requirements checked** (official guide for authors via search; the ScienceDirect page blocks automated download): abstract ≤ 250 words; highlights 3–5 bullets ≤ 85 characters; graphical abstract encouraged. Length limit, keyword count and declarations still to be verified on the official page (third-party pages disagree).

**Done:** `paper/OUTLINE.md`:
- the value thread V1–V5 with evidence (F/D numbers);
- the adapted structure (8 sections + declarations + supplement), adapted from the author's proposed structure; items that were not run (several deep and graph baselines, Snorkel, clustering labelers, VUS-PR, balanced accuracy, temperature scaling, 30-min robustness, news-record rule) are not presented as run;
- the place of every main figure (13), table (10) and equation (26), with paper numbering in order of first citation;
- the writing order (methods and results first, introduction and abstract last).
- **Length (later the same day):** the author found a third-party table giving ~8,000 words for research articles. A further search found 8,000, 7,000–10,000 and 12,000 on third-party pages and 5,000 in an outdated 2015 author pack; none official. Working budget set to **8,000 words of body text** (the safer figure), with a per-section budget in the outline; main paper trimmed to 11 figures and 9 tables (the two logger episodes become one composite figure; the clock evidence and the key-events table move to the supplement).
- **Official guide, "Writing and formatting" section** (pasted by the author): recorded in `paper/OUTLINE.md` (files, title page, abstract, keywords 1–7, highlights, graphical abstract ≥ 1328 px, math, tables without vertical rules or shading and not duplicating figures, figures as separate files with embedded fonts and ≥ 300 dpi, no combined images unless compared, accessible colour). Consequences: the two logger episodes stay two figures (main paper 12 figures, 9 tables); PDFs to be re-exported with TrueType fonts; booktabs tables that add what their figure does not show. Length limit, declarations and reference style still to be read on the guide.

## Session 12 — 2026-11-14 — Writing steps 2 and 3: LaTeX skeleton, verified dataset references, §3 drafted

**Author's decisions:** length 8,000–8,100 words of body text; no conflict of interest; CRediT later; data and code available; references in numbered style ([1]) via a .bib file importable into Zotero or Mendeley.

**Step 2, skeleton (`paper/`):** `main.tex` (elsarticle 3.5 2026/01/09 from MiKTeX, `preprint,12pt`, line numbers, elsarticle-num), one file per section with its budget, `declarations.tex`, `references.bib`, `tools/sync_figures.py` (Figure_1 … Figure_12 from results/figures/), `tools/wordcount.py` (texcount, body text only), `README.md` (build, rules, status), `.gitignore`.

**References verified** (DOI content negotiation, 2026-11-14): UCI 1158 (10.24432/C5FC8R), Data in Brief (10.1016/j.dib.2025.112067, full text read), OPSEARCH (10.1007/s12597-025-00950-w), UCI 849 Tetouan (10.24432/C5B034), IRSEC 2018 (10.1109/IRSEC.2018.8703007). The research guide had listed some method references "from memory"; none is used until verified.

**Step 3, §3 Data, hierarchy and typology (first draft, 712 words):** datasets (Table 1), Fig 1, hierarchy and the acquisition layer, problem formulation with Eqs (1)–(2), typology (Table 2, Fig 2). Checks run: the 12 missing stamps are identical in the three southern cities (from 23 Apr 2023 02:00); Foum El Oued zones 5–7 carry values to 24 May 2024 in the UCI file (the data paper's table says 26 Dec 2023); the UCI Tetouan record states no unit. Wording decision D77 (no "one data logger" in the paper).

**Compiled** (latexmk, no errors); pages rendered and checked: tables and figures place correctly; the figures still carry baked-in titles and small text (figure step).

**Step 4, §4 Method (first draft, 1,497 words of 1,750):** overview (Fig 3); per-step states, items, episodes and signatures, Eqs (3)–(10); the 19 rules (Table 3: family, item, vote, condition, real-data coverage, learned precision); why the standard Dawid–Skene model fails with single-label rules, Eq (11); the constrained label model, Eqs (12)–(14); the detector (TCN-GAT predictor with the graph as an ablation, MODWT bands, g/u/v hierarchy, robust scores, event formation), Eqs (15)–(19); end model and fusion, Eqs (20)–(21); type-aware cleaning, Eq (22). Source: docs/methods.md as implemented.
- **References verified and added (12):** Dawid & Skene 1979 (pages 20–28 confirmed on RePEc), Zhang et al. 2016 JMLR (full text checked: Section 6 defines the one-coin model), Ratner et al. 2017 (Snorkel), Percival & Walden 2000 (MODWT), Bai et al. 2018 (TCN, arXiv), Veličković et al. 2018 (GAT, arXiv/ICLR), Deng & Hooi 2021 (GDN), Ke et al. 2017 (LightGBM, NeurIPS BibTeX), Huber 1964, Rousseeuw & Croux 1993 (MAD), Hinton 2002 (products of experts). arXiv DOIs (10.48550) resolved.
- **Fixes found while checking:** nine defining rules (not eight); Dawid–Skene θ defined conditional on the rule firing (the F20 argument needs it); "logger-wide" replaced (D77); wide tables moved to tabularx; the indicator 1 set with dsfont (amssymb has no blackboard-bold digits); the M-step equation split over two lines.

**Step 3 revision (Section 3 review, D78):** five review points and two small ones, each verified first (UCI page re-read; the UCI zip downloaded and hashed: byte-identical to our file; duplicated stamps and raw zeros recomputed; Foum El Oued zones 5–7 inspected around 26 Dec 2023; the warm-up read from `rules_v0.expected`). Section 3 now 891 words. Figures 1–3 exported in submission form (no built-in titles, TrueType fonts) by `paper/tools/export_figures.py`; figure text corrected (D77/D78); NB7 re-run.
- **Pitfall:** the Bash tool collapses `\\` to `\` in commands, so sed/perl patterns with LaTeX backslashes silently fail to match; LaTeX edits are made with the Edit tool or a Python file written with the Write tool.

**Step 4 revision (Section 4 review, D79):** nine points checked and applied (β of the real catalogue from results_summary §9.9; TCN structure from `src/graph_model.py`, receptive field 1 + 2·2·63 = 253; the 39 % prior sensitivity from F24/`robustness.csv`; rule IDs R19–R21 in the released label files). Section 4 now 1,673 words of body text (texcount), within its 1,700 budget.

**Section 4 accepted; Marrakech β (D80, F60):** the author accepted Section 4 and asked why Marrakech uses β = 0.5. Reason found in the code: β is tuned on the injection benchmark, which covers only the south (`src/inject.py`); Marrakech keeps NB3's provisional 0.5. New tool `tools/marrakech_beta_sensitivity.py` (seconds) re-fuses NB3's stored q and f: it reproduces all 281 stored labels at 0.5, and every β in [0.4, 1] gives the same 55 Marrakech labels (F60). §4.7 now states the reason and the insensitivity; two sentences shortened to keep Section 4 at 1,700 words (texcount).
- **Follow-up (author):** state what happens below β = 0.4. Labels change there (1 item at 0.1–0.3, 2 at 0), so §4.7 now says "identical for all β ≥ 0.4; lower values move at most two items from G3 to G4". The interval claim is exact because each pairwise log-ratio is linear in β (F60). Section 4 stays at 1,700 words.

**Step 5, §5 Experimental design (first draft, 796 words; D81):** injection benchmark (new table of injected types), methods compared, metrics Eqs (23)–(27) (event-wise P/R/F1 with matched sets, ECE, MASE, Diebold–Mariano with Newey–West, outage ratio), downstream and transfer protocols, statistics and reproducibility. Every protocol fact read from the code (`src/inject.py`, `src/benchmark.py`, `src/label_model.py`, `src/downstream.py`, `tools/dev_select_detector.py`) and the run summaries. 12 references verified and added (DOI records; PMLR, NeurIPS, JMLR pages; R's stl reference list for STL, which has no DOI). Budgets: §5 800, §6 1,950. Compiled; pages rendered and checked (Eq. 23 reset to fit one line; table placement fine).
- **Pitfall hit again:** a heredoc Python script with LaTeX backslashes failed its assert (nothing written); the file was rewritten with the Write tool.

**Section 5 review (minor revision; D82–D84, F61–F63):**
- **Deep baselines:** GDN and USAD re-implemented in `src/deep_baselines.py` from the papers and the authors' released code (GDN run.sh, models/, evaluate.py, process_swat.py; USAD commit e25af45), trained like our predictors, tuned on development seeds like every detector, scored on the 30 NB4 test datasets (`tools/deep_baselines.py`). A smoke test (`--quick`) passed first. A training-log bug (GDN loss divided by N twice) was found and fixed. A check against persistence then found GDN 10× worse than the last value; the authors' preprocessing turned out to min-max scale each sensor, which had been omitted: the run was stopped, partial outputs deleted, GDN retrained with scaling (USAD kept). Still 7–14× worse than persistence (F63): GDN's attention blends each feeder with its neighbours. Both baselines lose to the rules, the main detector and STL in every seed (F61).
- **Forecasting on all 30 datasets** (`tools/forecast_all_datasets.py`), NB5's 4 reproduced exactly: F53 and F54 confirmed (F62).
- **Text:** dev rates, the untuned setting, the bias of the benchmark towards the rules, the deep baselines, "all 30 datasets"; Section 5 880 words (budget 880; Results 1,870).

**Step 6, §6 Results (first draft, 1,741 words of 1,870; D85):** seven subsections, Figs 4–12, Tables 5–8. Numbers from results_summary and the result CSVs; the four tables generated from the CSVs (half-up rounding). Checks while drafting corrected four statements (D85). Figure 7 (detection, with GDN and USAD) and Figure 10 (downstream, panel (b) from 30 datasets) exported in submission form; the other Section 6 figures wait for the figure step (Figure 11 must be redrawn). Two numbers new to results_summary: final rule-item confidence (0.937; 13 below 0.7) and the naive reference's real-data DM p.

**Section 6 review (D86):** six text fixes checked against F04, F42, F58, the forecasting and DM files (clock calendars, no interpretability claim, "no regional outage is found", the 1-h forecasting result first, Tetouan A1 → G2 calibration, Fig 6 caption). The author pointed out that the Section 3 review had asked for titles to be removed from all figures: every main figure is now drawn in submission form by `paper/tools/export_figures.py` (new `src/paper_submission.py`); `sync_figures.py` deleted. Redrawing the episode figures from the catalogue items corrected two details (zero fill starts when the hold ends; 43 h side by side). `lmodern` added (no Type 3 fonts left). Section 6 1,798 words.
- **Section 6 accepted.** Fig 5 caption aligned with the text: the zero fill lasts 43.8 h (D117, 31 Mar 11:10 – 2 Apr 07:00) and the L1/L2 hold overlaps it for its first 43 h (F145, until 06:10).
