# Grid event or data artefact?

*Hierarchical weak supervision for anomaly attribution in multi-city feeder telemetry.*

Utilities often clean feeder telemetry without knowing what the anomalies are: zeros and flat lines get deleted or interpolated whether they record a real outage or a data failure. This project uses the grid's own hierarchy (zone → city → region → data logger) to tell **grid events** (keep and flag) from **data artefacts** (impute), with no manual labels. The output is a typed, probabilistic event catalogue for the UCI Morocco smart-meter dataset (id 1158).

The full method, equations (1–20), 18 labelling rules, typology, metrics and roadmap are in **[docs/research_guide.md](docs/research_guide.md)**.

## Repository layout

```
├── data/raw/
│   ├── Data Morocco.xlsx                    # UCI 1158: Laâyoune, Boujdour, Foum El Oued (10 min, A), Marrakech (30 min, kW)
│   └── tetouan/Tetuan City power consumption.csv   # transfer-test dataset (UCI Tetouan, 2017, 10 min)
├── docs/research_guide.md                   # research guide & roadmap (master spec)
├── src/rules_v0.py                          # rule engine v0 (pandas + numpy only)
├── notebooks/NB1_evidence_figures.ipynb     # evidence figures (executed, outputs included)
└── results/
    ├── event_catalogue_v0/                  # rule engine v0 outputs
    │   ├── zero_events.csv                  # 72 dead-feeder events + features + provisional type
    │   ├── stuck_runs.csv                   # 220 runs of ≥ 6 identical non-zero values
    │   ├── transfers.csv                    # load-transfer candidates (conservation index κ)
    │   └── timestamp_audit.csv              # duplicate / missing / out-of-order stamps
    └── figures/                             # all figures (png + pdf) + clock_offsets.csv, interp_runs.csv
```

## Quick start

```bash
pip install -r requirements.txt

# 1. Rule engine v0 -> event catalogue (reproduces results/event_catalogue_v0 exactly)
python src/rules_v0.py "data/raw/Data Morocco.xlsx" results/event_catalogue_v0

# 2. Evidence figures -> results/figures
jupyter nbconvert --to notebook --execute --inplace notebooks/NB1_evidence_figures.ipynb
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

## Findings beyond the guide (NB1)

- **Linear-interpolation artefact.** 275 runs (102 groups, 48 spanning ≥ 2 zones at once) where the series is a perfect straight line, with a constant first difference. Rule engine v0 doesn't detect it, because R2 only catches identical values.
- **C05 (Jan 2023)** involves all 15 zones: F1–F3 and F5–F7 are interpolated over the same span as the F4 hold.
- **C09 (16 Jul 2023)** is probably an artefact rather than a regional outage. Laâyoune was linearly interpolated while B and F read exact zeros.
- **Clock-offset sign.** The notebook reports δ* = −60 min for Oct 2022, meaning the same behaviour is stamped 60 min earlier after the change. The guide's "+60" is the same offset with the opposite sign convention.

## Status

- [x] Rule engine v0 + provisional catalogue
- [x] NB1 evidence figures
- [ ] Rules v1 (R3–R6, R11, R12, R15 + linear-interpolation rule)
- [ ] NB2 Dawid–Skene label model
- [ ] NB3 multi-scale graph detector + end model
- [ ] NB4 injection benchmark · NB5 downstream forecasting · NB6 Tetouan transfer

## Data

- Bensalah, M. & Hair, A. (2025). *High-Resolution Load Dataset from Smart Meters Across Various Cities in Morocco*. UCI ML Repository, [DOI 10.24432/C5FC8R](https://doi.org/10.24432/C5FC8R) (CC BY 4.0).
- Salam, A. & El Hibaoui, A. (2018). *Power consumption of Tetouan city*. UCI ML Repository (CC BY 4.0).
