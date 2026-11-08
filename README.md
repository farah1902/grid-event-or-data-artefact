# Grid event or data artefact?

*Hierarchical weak supervision for anomaly attribution in multi-city feeder telemetry.*

Utilities often clean feeder telemetry without knowing what the anomalies are: zeros and flat lines get deleted or interpolated whether they record a real outage or a data failure. This project uses the grid's own hierarchy (zone → city → region → data logger) to tell **grid events** (keep and flag) from **data artefacts** (impute), with no manual labels. The output is a typed, probabilistic event catalogue for the UCI Morocco smart-meter dataset (id 1158).

**Documentation:** start with [docs/README.md](docs/README.md).
- To write the paper: [docs/paper_handoff.md](docs/paper_handoff.md).
- Every number: [docs/results_summary.md](docs/results_summary.md).
- Every design choice: [docs/decisions.md](docs/decisions.md).
- Every finding: [docs/findings.md](docs/findings.md).
- The original plan (equations 1–20, typology, roadmap): [docs/research_guide.md](docs/research_guide.md). Several parts were corrected later; see paper_handoff §3.

Agents working in the repo: read [CLAUDE.md](CLAUDE.md).

## Repository layout

```
├── data/raw/
│   ├── Data Morocco.xlsx                    # UCI 1158: Laâyoune, Boujdour, Foum El Oued (10 min, A), Marrakech (30 min, kW)
│   └── tetouan/Tetuan City power consumption.csv   # transfer-test dataset (UCI Tetouan, 2017, 10 min)
├── CLAUDE.md                                # instructions for agents working in the repo
├── docs/                                    # research guide + full documentation (see docs/README.md)
├── src/
│   ├── rules_v0.py                          # rule engine v0 (pandas + numpy only)
│   ├── rules_v1.py                          # rule engine v1: 19 rules voting on items (see below)
│   ├── label_model.py                       # constrained Dawid–Skene label model (+ guide-style baseline)
│   └── viz.py                               # shared plotting style + stacked-zone plot
├── notebooks/
│   ├── NB1_evidence_figures.ipynb           # evidence figures (executed, outputs included)
│   ├── NB1b_rules_v1.ipynb                  # rule engine v1: votes, diagnostics, key events (executed)
│   └── NB2_label_model.ipynb                # label model: probabilistic labels, recovery, robustness (executed)
├── tools/make_nb*.py                        # generators that write the notebooks
└── results/
    ├── event_catalogue_v0/                  # rule engine v0 outputs
    │   ├── zero_events.csv                  # 72 dead-feeder events + features + provisional type
    │   ├── stuck_runs.csv                   # 220 runs of ≥ 6 identical non-zero values
    │   ├── transfers.csv                    # load-transfer candidates (conservation index κ)
    │   └── timestamp_audit.csv              # duplicate / missing / out-of-order stamps
    ├── catalogue_v1/                        # rule engine v1 outputs (input to the NB2 label model)
    │   ├── items.csv                        # 327 items (126 dead, 155 fill, 33 clock, 13 transfer) + features + votes
    │   ├── votes.csv                        # item × rule label matrix (empty = abstain)
    │   ├── zone_runs.csv                    # per-zone dead / hold / interpolation runs behind the items
    │   ├── rule_summary.csv                 # coverage, overlap, conflict per rule
    │   ├── key_events_v1.csv                # guide catalogue IDs (C01–C12) → v1 items and episodes
    │   └── episodes_compound.csv            # linked items, e.g. hold → zero fill
    ├── labels_v1/                           # label-model outputs
    │   ├── q.csv                            # probabilistic catalogue: q(y) per item, label, confidence
    │   ├── episodes_labelled.csv            # episodes as label sequences, e.g. A2 → A1
    │   ├── rule_params.csv                  # learned propensity a / false-positive rate b per rule
    │   └── recovery_*, robustness.csv, ...  # diagnostics
    └── figures/                             # all figures (png + pdf) + clock_offsets.csv, interp_runs.csv
```

## Rule engine v1

The items voted on are **dead** events (x = 0 or ≤ 5 % of expected), **fill** events (held values or straight-line interpolation), **clock** dates and **transfer** days. Items that share boundaries are linked into **episodes**, for example C12 = hold → zero fill.

| Family | Rules | Labels |
|---|---|---|
| Simultaneity | R1 multi-city zero, R7 regional outage | A1, G1 |
| Hold | R2 simultaneous hold, R3 hold → zero, R4 hold co-extensive with dead zones, R12 single-zone stuck | A2, A1, A1, A3 |
| **Interpolation (new)** | R19 multi-zone linear fill, R20 single-zone linear fill, R21 linear fill + dead | A2, A3, A1 |
| Restoration | R5 cold-load pickup (π ≥ 1.15), R6 noise floor (η < 0.9) | G (any grid event) |
| City / zone | R8 city outage, R9 single zone, R11 single zone > 24 h | G2, G3, G3 |
| Calendar / clock | R10 maintenance window, R13 duplicate stamps, R14 missing hour, R15 profile shift | G4, A4, A4, A4 |
| Conservation | R16 conserved transfer | G5 |

The rules are allowed to conflict, and NB2's Dawid–Skene label model resolves the conflicts. R17/R18 (external records) are not implemented. Deviations from the guide are listed at the top of `NB1b_rules_v1.ipynb`.

## Quick start

```bash
pip install -r requirements.txt

# 1. Rule engine v0 -> event catalogue (reproduces results/event_catalogue_v0 exactly)
python src/rules_v0.py "data/raw/Data Morocco.xlsx" results/event_catalogue_v0

# 2. Rule engine v1 -> results/catalogue_v1 (about 30 s)
python src/rules_v1.py "data/raw/Data Morocco.xlsx" results/catalogue_v1

# 3. Notebooks -> results/figures
jupyter nbconvert --to notebook --execute --inplace notebooks/NB1_evidence_figures.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/NB1b_rules_v1.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/NB2_label_model.ipynb
```

**Google Colab:** copy or clone the repo to `MyDrive/grid-event-or-data-artefact/`, open `notebooks/NB1_evidence_figures.ipynb` and run all cells. The first cell mounts Drive and installs `openpyxl`.

## Figures (NB1)

| File | Content |
|---|---|
| `fig1_map_coverage` | Cities (schematic) + per-zone state bars: held, linearly interpolated, exact zero, noise floor, missing |
| `fig3_C05_C06_jan2023` | 25–29 Jan 2023: simultaneous holds, then zero fill across all 15 southern zones |
| `fig4_C12_mar2024` | 31 Mar – 2 Apr 2024: L1/L2 held for 43 h while the other zones are zero-filled |
| `fig5_clock_2022-10-30`, `figS_clock_*` | Clock offset δ* (eq. 9) at each clock-change date |
| `E1_C09_jul2023`, `E1b_C09_stack` | 16 Jul 2023: B and F zeros next to linearly interpolated Laâyoune |
| `E2_C11_transfer` | Boujdour zone 1 → zone 2 load transfer, κ = 0.07 |
| `E3_single_zone_timing` | Single-zone events cluster in a 06:00–11:00 maintenance window |
| `E4_signatures` | Exact-zero share η, restoration ratio r, overshoot π, ramp time τ by type |
| `E5_single_zone_gallery` | Single-zone outages C01, C02, C04, C07 |
| `E6_catalogue_timeline` | Every v0 event on one timeline |
| `E7_FoumElOued_structural` | Foum El Oued level decline (−50 %) and midday/evening ratio |
| `E8_Marrakech_timestamps` | Marrakech midnight rows out of order |
| `fig7_rule_diagnostics` | v1 rule coverage, overlap and conflict (NB1b) |
| `E9_vote_matrix` | v1 votes on every multi-zone, clock and transfer item (NB1b) |
| `E10_C01_relabelled` | C01: zeros → straight-line fill → zeros, not a noise floor (NB1b) |
| `E11_short_simultaneous_freezes` | Daily 08:00 short freezes across all Laâyoune zones until Apr 2023 (NB1b) |
| `E12_label_model_rules` | Learned rule propensity a vs false-positive rate b, evidence log(a/b) (NB2) |
| `E13_label_confidence` | Posterior confidence per type and entropy per item kind (NB2) |
| `E14_key_event_posteriors` | Full posterior q(y) for the key events (NB2) |
| `E15_label_robustness` | Label changes when rule families or priors change (NB2) |

Roles and caveats for each figure: [docs/figures_and_tables.md](docs/figures_and_tables.md).

## Findings beyond the guide (full register: docs/findings.md)

- **Linear-interpolation artefact.** 275 runs (102 groups, 48 spanning ≥ 2 zones at once) where the series is a perfect straight line, with a constant first difference. Rule engine v0 doesn't detect it, because R2 only catches identical values.
- **C05 (Jan 2023)** involves all 15 zones: F1–F3 and F5–F7 are interpolated over the same span as the F4 hold.
- **C09 (16 Jul 2023)** is probably an artefact rather than a regional outage. Laâyoune was linearly interpolated while B and F read exact zeros.
- **Clock-offset sign.** The notebook reports δ* = −60 min for Oct 2022, meaning the same behaviour is stamped 60 min earlier after the change. The guide's "+60" is the same offset with the opposite sign convention.
- **Synthetic restoration ramps.** 25 of 117 southern dead runs (21 %), including C02, C04 and C07, return through a straight-line fill. v1 measures restoration after that ramp. C02's "slow return" (r = 0.22 in v0) becomes r = 1.01 with no ramp.
- **C01 is not a noise-floor outage.** It is zeros, then a 7 h perfectly straight line at ≤ 5 % of expected, then zeros.
- **No clean regional outage remains.** R7 fires on 0 items: every multi-city dead event comes with hold or linear-fill evidence. G1 will have to be learned from injected events.
- **Daily logger freeze.** Laâyoune had 218 freezes of 3–5 points across ≥ 2 zones at once (120 starting in the 08:00 hour, one per day on 186 days), which stop in Apr 2023.
- **Morning overlap.** Most multi-zone linear fills start 08:00–10:30, inside R10's 06–11 h "planned work" window. Some G4 candidates may be data-side maintenance.
- **R15 needs a fit-quality guard.** Without it, δ* fires on Ramadan dates and on noisy Marrakech dates. With the guard, it fires on Oct 2022 (L, B, F), Oct 2023 (L, B) and Boujdour on 31 Mar 2024 (+60 min, the European spring-forward date and the C12 date).
- **The guide's label model cannot work on these rules.** Each rule emits a single label, so P(vote | class, fired) = 1 and the votes carry no information. The unconstrained Dawid–Skene is also not identifiable on sparse votes (63 % restart agreement). A constrained, level-gated one-coin model is stable (100 %) and recovers its parameters: accuracy 0.922 vs 0.682, ECE 0.033 vs 0.276 on synthetic votes.
- **Restoration overshoot is uninformative.** R5's learned log(a/b) is 0.12, against 1.8–4.8 for the other rules.
- **Artefacts dominate anomalous time** (provisional). In the south there are 2,605 artefact zone-hours against 294 grid-event zone-hours. Counting every zero as an outage would overstate outage time about 4.2×.

## Status

- [x] Rule engine v0 + provisional catalogue
- [x] NB1 evidence figures
- [x] Rules v1 (R3–R6, R11, R12, R15 + interpolation family R19–R21)
- [x] NB2 label model (constrained Dawid–Skene, recovery, robustness, labelled catalogue)
- [ ] NB3 multi-scale graph detector + end model
- [ ] NB4 injection benchmark · NB5 downstream forecasting · NB6 Tetouan transfer

## Data

- Bensalah, M. & Hair, A. (2025). *High-Resolution Load Dataset from Smart Meters Across Various Cities in Morocco*. UCI ML Repository, [DOI 10.24432/C5FC8R](https://doi.org/10.24432/C5FC8R) (CC BY 4.0).
- Salam, A. & El Hibaoui, A. (2018). *Power consumption of Tetouan city*. UCI ML Repository (CC BY 4.0).
