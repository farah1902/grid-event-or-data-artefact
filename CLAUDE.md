# CLAUDE.md — instructions for agents working in this repository

This is the working repository for a PhD paper, *Grid event or data artefact? Hierarchical weak supervision for
anomaly attribution in multi-city feeder telemetry*. The data is the UCI Morocco smart-meter dataset (id 1158).
The author is an EHTP PhD student. Code runs locally on Windows and on Google Colab.

## Read first, in this order

1. `docs/paper_handoff.md`: the state of the science. What the paper can claim, with which evidence, and what is still missing. **Start here if you are writing the paper.**
2. `docs/research_guide.md`: the original research plan (master spec, dated 2026-11-06). It holds equations 1–20, the 18 rules, the typology, the metrics and the roadmap. **Several parts were later corrected.** Check `docs/decisions.md` before trusting any guide detail.
3. `docs/decisions.md`: every design decision (D01, D02, …), with alternatives, reasons, evidence and code location. Decisions that deviate from the guide are marked **[guide deviation]**.
4. `docs/findings.md`: every empirical finding (F01, F02, …), with numbers, evidence files and implications for the paper.
5. `docs/results_summary.md`: the single source of truth for numbers to cite.
6. `docs/methods.md`: the method exactly as implemented, in paper-ready form.
7. `docs/research_log.md`: chronological log of all work sessions.
8. `docs/data_dictionary.md` (every output file and column) and `docs/figures_and_tables.md` (every figure, its source and its paper role).
9. `docs/transfer_protocol.md`: the Tetouan transfer. Every component is marked frozen, re-estimated, adapted or engineering. Keep it complete if the transfer code changes.

## Repository map

```
data/raw/                     input data (UCI Morocco xlsx, Tetouan csv) — never modify
docs/                         all documentation (see above)
src/rules_v0.py               rule engine v0 (frozen baseline; reproduces results/event_catalogue_v0 exactly)
src/rules_v1.py               rule engine v1: items, 19 rules, votes, episodes
src/label_model.py            Dawid–Skene label model (constrained one-coin variant + guide's full variant)
src/viz.py                    shared plotting style and stacked-zone plot
src/detector.py               predictors (LightGBM, sklearn fallback), phase-aligned MODWT, residual hierarchy, level scores (structural zeros excluded, D51)
src/end_model.py              detector-only candidates, normal windows, item features, soft-label end model, fusion
src/graph_model.py            TCN-GAT with a learned graph (guide eq. 13; D53) = the main detector's predictor (D61); hybrids on the LightGBM forecast (base=, D59)
src/inject.py                 injection of observed signatures into clean zone-time (D54)
src/benchmark.py              variants (VARIANTS, incl. the no-graph multi-scale ablation V_TCN_MS, D62), event formation per detector (D60), pipeline() on any dataset, run() on injected data, baselines, metrics
src/paper_figures.py          NB7: final catalogue, Fig 1 (basemap), Fig 2 (typology), Fig 6 (framework)
src/paper_regen.py            NB7: regenerated Fig 8, Fig 9, E4, E6, E19, E22 (D74)
src/paper_tables.py           NB7: paper tables, numbered figure set + MANIFEST.md, catalogue release (D72, D75)
src/transfer.py               NB6: Tetouan transfer (register the system, frozen label model, predictors trained on Tetouan, metrics)
src/downstream.py             NB5: cleaning strategies S0-S3, global LightGBM direct forecaster, seasonal naive, MASE/DM test, outage statistics
notebooks/NB1_evidence_figures.ipynb   Fig 1, 3, 4, 5, E1–E8 (executed)
notebooks/NB1b_rules_v1.ipynb          rule engine v1 diagnostics, Fig 7, E9–E11 (executed)
notebooks/NB2_label_model.ipynb        label model, E12–E15 (executed)
notebooks/NB3_detector_end_model.ipynb detector + end model, Fig 8, E16–E19 (executed locally with LightGBM 4.6.0 = reference run)
notebooks/NB4_benchmark.ipynb          TCN-GAT + injection benchmark, Tables 5–7, Figs 9–11, E20–E21 (executed on Colab GPU 2026-11-09 = reference run; its generator has since gained the V_TCN_MS row, not re-executed)
notebooks/NB5_downstream.ipynb         downstream test: cleaning strategies, Table 8, Fig 12, outage statistics (local CPU; resumable)
notebooks/NB6_tetouan.ipynb            transfer to Tetouan with the method frozen: Table 9, Fig 13, E22 (local CPU, ~13 min; resumable)
notebooks/NB7_final_figures.ipynb      final catalogue, Figs 1/2/6, regenerated figures, paper set (local, ~1 min; needs the LightGBM pickle)
tools/make_nb*.py             generators that write the notebooks (see "Notebooks" below)
tools/diag_structural_zeros.py diagnostic behind F35/D51 (writes results/detector_v1/structural_zeros.csv)
tools/dev_select_detector.py  development selection (seeds 100-104): event formation per detector + the main detector -> results/benchmark_v1/dev_selection.json (D60, D61)
tools/graph_ablation.py       post-run no-graph ablation of the main detector on the NB4 datasets -> results/benchmark_v1/graph_ablation/ (D62, F42)
tools/make_transfer_diagram.py Fig 14: the Tetouan transfer protocol diagram (D71; reads results/transfer_tetouan/summary.json)
tools/ablation_summary.py     Table 7e + Fig 9b: all ablations of the main detector, the learned graph first (D67; reads stored files, seconds)
tools/outage_all_datasets.py  outage statistics on all 30 NB4 test datasets (NB5's code unchanged) -> results/downstream_v1/outage_all/ (D76, F59)
results/event_catalogue_v0/   v0 outputs
results/catalogue_v1/         v1 items, votes, zone runs, rule summary
results/labels_v1/            label-model outputs (q.csv = probabilistic labels)
results/detector_v1/          detector metrics, hierarchy test, recall, detector-only candidates
results/end_model_v1/         item features, normal windows, end-model metrics, p_type.csv (fused labels)
results/benchmark_v1/         NB4 outputs; runs/ = one set of files per (rate, seed); models/ (the LightGBM pickle is git-ignored, on Drive); dev/ + dev_selection.json
results/main_detector/        NB4 §8b: south catalogue of the main (graph) detector, supersedes NB3's south detector outputs
results/downstream_v1/        NB5 outputs (real data + injected/ per dataset); outage_all/ = outage statistics on the 30 test datasets (D76)
results/transfer_tetouan/     NB6 outputs (real series, runs/, Table 9, models trained on Tetouan)
results/catalogue_final/      NB7: the released typed catalogue (catalogue, episodes, key events, README)
results/paper/                NB7: the paper set: MANIFEST.md (numbering, captions), figures/, tables/
data/external/natural_earth/  Natural Earth 1:50m land (public domain) for the Fig 1 basemap
results/figures/              all figures (png + pdf) and small csv tables
paper/                        the manuscript (LaTeX, Applied Energy): OUTLINE.md (plan), README.md (build, rules, status), sections/, references.bib (verified only)
_local_archive/               git-ignored scratch (duplicates, zips, old copies). Not part of the project
```

## Rules for every agent

- **Log everything.** After each work session:
  - Append to `docs/research_log.md`.
  - Add new decisions to `docs/decisions.md` (next free D-number) and new findings to `docs/findings.md` (next free F-number).
  - Update `docs/results_summary.md` with any number that changed, `docs/figures_and_tables.md` with new figures, and `docs/paper_handoff.md` if a claim changes.
  - The user explicitly asked for every decision and behaviour to be recorded so that another agent can write the paper.
- **Never cite a number that isn't in `results/` or `docs/results_summary.md`.** Re-run the code if unsure.
- **Git:** this folder is its own repository (branch `main`, remote `https://github.com/farah1902/grid-event-or-data-artefact`, private).
  - A parent repository exists at `C:\Users\Dell` with an unrelated remote (ESA_LandCover_Streamlit). **Never commit there.**
  - Commit and push after each completed step.
  - End commit messages with the attribution line given in the session instructions.
- **GitHub CLI:** installed at `C:\Program Files\GitHub CLI\gh.exe` and logged in as `farah1902`. It isn't on the bash PATH, so call it with its full path.
- **User preferences:** move fast; don't plan around the guide's week estimates; skip external-validation chores (emailing the dataset authors, ONEE/press searches); give full working code; push results to the repo.
- **Data conventions:**
  - Timestamps are **as recorded**, with no clock correction (see F04, D11).
  - Zone codes: `L1–L5` (Laâyoune), `B1–B3` (Boujdour), `F1–F7` (Foum El Oued), `M1–M2` (Marrakech).
  - Sheet names in the xlsx are `Laayoune`, `Boujdour`, `Foum eloued`, `Marrakech`, and columns are `zone1…`.
  - L, B and F share one 10-min logger timeline (the "south" system). Marrakech is a separate 30-min kW system.
- **Item ids** in `results/catalogue_v1`: `D###` dead, `F###` fill, `K###` clock, `T###` transfer, `EP###` episode. **They change if rules_v1 is re-run with different parameters.** Refer to events by date and zones in prose.
- **Labels:**
  - A1 zero-fill gap, A2 simultaneous fill (hold or linear), A3 single-zone fill, A4 clock error.
  - G1 regional outage, G2 city outage, G3 unplanned feeder outage, G4 planned work, G5 load transfer.
  - N normal. `G` = any grid event (family vote of R5/R6).

## How to run

```bash
pip install -r requirements.txt
python src/rules_v0.py "data/raw/Data Morocco.xlsx" results/event_catalogue_v0     # ~20 s
python src/rules_v1.py "data/raw/Data Morocco.xlsx" results/catalogue_v1           # ~30 s
cd notebooks
python -m jupyter nbconvert --to notebook --execute --inplace NB1_evidence_figures.ipynb   # ~2 min
python -m jupyter nbconvert --to notebook --execute --inplace NB1b_rules_v1.ipynb         # ~1 min
python -m jupyter nbconvert --to notebook --execute --inplace NB2_label_model.ipynb       # ~1.5 min
python -m jupyter nbconvert --to notebook --execute --inplace NB3_detector_end_model.ipynb # ~13 min
python tools/dev_select_detector.py            # before NB4: development selection, ~35 min (+ --extend for the extended grid)
# NB4: run on Colab (GPU), 2-3 h, resumable; locally the same command works (~2.5 h on 8 cores)
python tools/graph_ablation.py                 # after NB4: no-graph ablation on the NB4 datasets, ~30 min on CPU (D62)
python tools/make_nb5_downstream.py notebooks/NB5_downstream.ipynb   # then execute NB5 like the others (local CPU)
python tools/make_nb6_tetouan.py notebooks/NB6_tetouan.ipynb         # then execute NB6 (local CPU, ~13 min)
python tools/outage_all_datasets.py           # outage statistics on the 30 NB4 test datasets, ~1 h on CPU (D76); before NB7 (Fig 12c)
python tools/make_nb7_final_figures.py notebooks/NB7_final_figures.ipynb   # then execute NB7 (~2 min)
```
Sync the repo to the Drive copy before a Colab run, and pull the outputs after it:
```bash
python tools/sync_drive.py "G:/My Drive/grid-event-or-data-artefact"
python tools/sync_drive.py "G:/My Drive/grid-event-or-data-artefact" --pull results/benchmark_v1 results/figures notebooks/NB4_benchmark.ipynb
```
Notebooks resolve `ROOT` from the repo root or from `notebooks/`. On Colab they expect the repo copied to `MyDrive/grid-event-or-data-artefact/`.

## LightGBM on the author's Windows machine

LightGBM **4.7.0** crashes there (access violation in `LGBM_DatasetSetField`); **4.6.0 works** and is pinned in `requirements.txt` (D52). If LightGBM fails, `detector.predict_rho(backend="auto")` falls back to scikit-learn's HistGradientBoosting and prints the backend; `summary.json` records `backend` and `lightgbm_version`. Check them before citing NB3 numbers.

## Colab ↔ local sync

The author has Google Drive for desktop in Streaming mode: the Drive copy of the repo is `G:\My Drive\grid-event-or-data-artefact` (Colab: `/content/drive/MyDrive/grid-event-or-data-artefact`). It has no `.git`; the local repo is the master copy.
- Before a Colab run, hash-compare the files the notebook reads and copy changed ones to G:.
- After it, check timestamps and `summary.json` on G:, then copy only that notebook's outputs (results folders, its figures, the executed `.ipynb`) into the repo.
- Colab can leave files written to Drive unsent: NB3 ends with `drive.flush_and_unmount()`, and the user must press Ctrl+S to save the executed notebook.
- A PDF open in Foxit locks it; notebooks then fail when `savefig` overwrites it.

## Notebooks

Notebooks are **generated** by `tools/make_nb*.py`, then executed with nbconvert. To change a notebook, edit its generator, then regenerate and execute it:
```bash
python tools/make_nb2_label_model.py notebooks/NB2_label_model.ipynb
```
Editing the `.ipynb` directly also works, but the generator then goes stale. If you do that, say so in the research log.

## What comes next (roadmap)

See `docs/paper_handoff.md` § "What is still missing". In short:
- **NB3:** done (reference run local, LightGBM 4.6.0, with the D51 fix).
- **Main detector (D61):** the TCN-GAT multi-scale residual detector with tuned event formation (w 24, q 99.9, gap 12), chosen on development seeds with every detector tuned alike (D60). **Paper framing (D67, author's decision):** the learned graph is presented as an ablation (graph on/off; it adds no detection skill, F42); LightGBM is a predictor ablation. Read F36–F43 before writing about it.
- **NB4:** done (Colab run 2026-11-09; results_summary §9, F41–F50, no-graph ablation F42/D62). **The test seeds 0–9 are spent (D63):** do not change the design based on them.
- **NB5:** done (`src/downstream.py`, `tools/make_nb5_downstream.py`; results_summary §10, F51–F54). Outage statistics on all 30 test datasets: `tools/outage_all_datasets.py` (D76, F59, §10.1b); cite those.
- **NB6:** done (`src/transfer.py`, `tools/make_nb6_tetouan.py`; results_summary §11, F55–F58).
- **NB7:** done (D72–D75). **All notebooks are done; next is writing the paper** from `docs/paper_handoff.md`, `results/paper/MANIFEST.md` and `docs/results_summary.md`.
