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

## Repository map

```
data/raw/                     input data (UCI Morocco xlsx, Tetouan csv) — never modify
docs/                         all documentation (see above)
src/rules_v0.py               rule engine v0 (frozen baseline; reproduces results/event_catalogue_v0 exactly)
src/rules_v1.py               rule engine v1: items, 19 rules, votes, episodes
src/label_model.py            Dawid–Skene label model (constrained one-coin variant + guide's full variant)
src/viz.py                    shared plotting style and stacked-zone plot
notebooks/NB1_evidence_figures.ipynb   Fig 1, 3, 4, 5, E1–E8 (executed)
notebooks/NB1b_rules_v1.ipynb          rule engine v1 diagnostics, Fig 7, E9–E11 (executed)
notebooks/NB2_label_model.ipynb        label model, E12–E15 (executed)
tools/make_nb*.py             generators that write the notebooks (see "Notebooks" below)
results/event_catalogue_v0/   v0 outputs
results/catalogue_v1/         v1 items, votes, zone runs, rule summary
results/labels_v1/            label-model outputs (q.csv = probabilistic labels)
results/figures/              all figures (png + pdf) and small csv tables
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
```
Notebooks resolve `ROOT` from the repo root or from `notebooks/`. On Colab they expect the repo copied to `MyDrive/grid-event-or-data-artefact/`.

## Notebooks

Notebooks are **generated** by `tools/make_nb*.py`, then executed with nbconvert. To change a notebook, edit its generator, then regenerate and execute it:
```bash
python tools/make_nb2_label_model.py notebooks/NB2_label_model.ipynb
```
Editing the `.ipynb` directly also works, but the generator then goes stale. If you do that, say so in the research log.

## What comes next (roadmap)

See `docs/paper_handoff.md` § "What is still missing". In short:
- **NB3:** multi-scale graph detector + end model + fusion.
- **NB4:** injection benchmark and baselines. This is the only place accuracy against known types can be measured.
- **NB5:** downstream forecasting.
- **NB6:** Tetouan transfer.
- **NB7:** final figures.
