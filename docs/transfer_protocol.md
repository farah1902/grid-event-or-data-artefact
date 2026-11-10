# Transfer protocol and adaptation register (NB6, Tetouan)

This is the complete list of what was done to run the method on the UCI Tetouan dataset. Every component of the pipeline is listed with one status:
- **Frozen:** taken unchanged from the Morocco study.
- **Re-estimated:** learned from Tetouan's own *unlabelled* series, as the method does on any new system.
- **Adapted:** a structural consequence of Tetouan having one city.
- **Engineering:** code made general, with no threshold or setting changed.

**Nothing was tuned on Tetouan.** No threshold, hyper-parameter, event-formation setting, rule weight or label-model parameter was chosen, changed or selected using Tetouan data. The chronology in §5 shows that no code changed after the first injected Tetouan result was seen.

Decisions: D68 (protocol), D69 (single-city adaptations and engineering), D70 (evaluation), D71 (this register and Fig 14). Findings: F55–F58. Numbers: results_summary §11. Diagram: `results/figures/fig14_transfer_protocol.png` (Fig 14, `tools/make_transfer_diagram.py`).

## 1. Data

| Item | What was done | Status | Where |
|---|---|---|---|
| Source file | `data/raw/tetouan/Tetuan City power consumption.csv` (UCI Tetouan, Salam & El Hibaoui 2018): 52,416 rows, 1 Jan – 30 Dec 2017, 10-min steps | — | `transfer.load` |
| Columns used | `Zone 1/2/3 Power Consumption` → `zone1..zone3` → codes T1–T3. The weather columns (temperature, humidity, wind, diffuse flows) are loaded but **not used**; the method uses power only, as for Morocco | engineering | `transfer.load` |
| Regularisation | The same `rules_v0.regularise` as Morocco (average duplicate stamps, sort, regular 10-min grid). Tetouan has no duplicate or missing stamp, so it is a no-op | frozen | `rules_v0.regularise` |
| Units | Tetouan is in kW, Morocco in A. **No conversion is needed:** every threshold is relative or unit-free | frozen | see §2 |
| Timestamps | As recorded, with no clock correction (D11, as for Morocco) | frozen | — |
| Audit | 0 duplicate or missing stamps, 0 zeros, longest run of equal values 3 steps, no linear-fill run: a pre-cleaned series | — | NB6 §1, F55 |

## 2. Rule engine and label model

| Component | Value used on Tetouan | Status | Note |
|---|---|---|---|
| Dead state (eq. 4) | x ≤ ε·x̂ with ε = 0.05, ≥ 3 steps | frozen | relative to x̂: unit-free |
| Hold state (eq. 6) | ≥ 6 identical non-zero values (10-min systems) | frozen | exact equality: unit-free |
| Linear-fill state (eq. 21) | ≥ 6 collinear points; tolerance 1e-8 × max(1, \|x\|) | frozen | relative tolerance: unit-free |
| Expected value x̂ (eq. 1) | median of the same time of day over the previous 14 days, zeros excluded | **re-estimated** (computed on Tetouan's own series) | 35-day burn-in excluded from scoring |
| Simultaneity τ, co-extension IoU, R1–R21 thresholds (η, r, π, κ, δ\*, hours, durations) | Morocco values (rules_v1 constants) | frozen | ratios, shares, minutes and hours: unit-free |
| Clock dates | 2017 EU changes (26 Mar, 29 Oct) and Moroccan changes (26 Mar, 21 May, 2 Jul, 29 Oct) added to the date lists | engineering (calendar input) | dates outside a dataset's range are ignored, so Morocco is unchanged |
| Rules that cannot fire | R1 (multi-city zero) and R7 (regional outage) need ≥ 2 cities | **adapted** (single city) | the cause of A1 → G2 (F58) |
| Label model | constrained Dawid–Skene fitted on the **Morocco** votes (NB2 settings: 20 restarts, seed 0) and applied to Tetouan items by **one E-step** with the frozen π and θ (`DawidSkene.predict`) | frozen | no refit. Rule outputs unseen in Morocco would count as abstentions: none occurred |
| Item schema | Tetouan items are aligned with the frozen catalogue columns. On the clean series only clock items exist, and they lack the dead/fill feature columns | engineering | `transfer.analyse_rules` |
| End model and fusion | not run on Tetouan | — | they do not beat the label model on injected data (F46); attribution uses the frozen label model, with majority vote as baseline |

## 3. Detectors

| Component | Value used on Tetouan | Status | Note |
|---|---|---|---|
| Main detector architecture | TCN-GAT: 6 residual blocks, kernel 3, dilations 1–32, 32 channels, 2 attention heads, embedding 16 | frozen | `graph_model` defaults |
| Training hyper-parameters | masked Huber (δ 0.1), AdamW lr 2e-3, weight decay 1e-4, cosine schedule, up to 40 epochs, patience 6, last 15 % of each fold for validation, seed 0 | frozen | NB4 config (`TCN_CFG`) |
| Predictor weights | trained on Tetouan's rule-clean steps, cross-fitted in two folds at **1 Jul 2017** | **re-estimated** | the cross-fitting boundary is the year's midpoint, the same rule as Morocco's split; `transfer.register` sets `detector.SPLIT` |
| Graph | 3 same-city edges per direction; the learned cross-city top-k = 4 has no candidate | **adapted** (single city) | top-k clamped to the number of zones (engineering) |
| Graph ablation | the same TCN without graph attention, at the main setting and at its own Morocco development setting (48, 99.9, 12) | frozen | D62 protocol |
| LightGBM forecast detector | Morocco features and parameters; weights trained on Tetouan | architecture frozen, weights **re-estimated** | predictor ablation |
| STL + MAD, Isolation Forest, LOF | the same code as NB4, fitted unsupervised on each dataset | frozen code, fits **re-estimated** | exactly as in NB4 |
| MODWT bands, phase alignment, robust z (eq. 15) | LA(8), J = 4, 28-day window, 21-day warm-up, structural zeros excluded | frozen | the scales are computed on Tetouan's residuals (**re-estimated**) |
| Residual hierarchy (eq. 14) | region, city and zone parts | **adapted** (single city) | city part u ≡ 0 (the city is the region), so the zone score is max(region, zone), as for Marrakech |
| Event formation | main detector w 24, q 99.9, gap 12; LightGBM 24, 99.8, 6; STL + MAD and LOF 24, 99.8, 12; Isolation Forest 3, 99.5, 3; minimum run 3 steps | frozen | from `dev_selection.json` (D60) |
| Threshold γ | the frozen percentile q of Tetouan's own rule-negative zone-steps, per dataset | **re-estimated** | the same rule as in NB4 (γ is always the q-th percentile of the dataset at hand) |
| Calendar features | 2017 Ramadan (27 May – 25 Jun), Eid (26–27 Jun, 1–2 Sep), Moroccan GMT periods (1 Jan – 26 Mar, 21 May – 2 Jul, 29 Oct – 31 Dec) added | engineering (calendar input) | religious dates can differ by one day (the same caveat as 2023–24) |

## 4. Injection and evaluation

| Component | Value used on Tetouan | Status | Note |
|---|---|---|---|
| Signatures | the NB4 injector: copied Morocco signatures, noise floors and shocks as fractions of x̂, durations as in D54 | frozen | relative levels: unit-free |
| Types | A1, A2, A3, G2, G3, G4, U_SHOCK, U_PARTIAL | **adapted** | G1 is not injected: in one city a regional outage is a city outage (G2) |
| Multi-city patterns | A1 and U_SHOCK become city-wide (all 3 zones). A2 is 50 % 2–3 zones and 50 % the whole city (Morocco: 50 / 25 / 25 % zones / city / cities). A city-wide A2 is followed by an A1 zero fill with p = 0.5 (compound, as in Morocco) | **adapted** | `Injector._pick_zones` single-city branch |
| Rates and seeds | 1 %, 3 %, 7 % × seeds 0–9; RNG `default_rng([rate × 1000, seed])`, the same scheme as NB4 | frozen | fresh datasets: no Tetouan seed had been used before |
| Clean region | rule-based, as NB4 (D60): away from rule states, burn-in (35 days) and clock days | frozen code | 0.871 of zone-steps on Tetouan |
| Scoring period | whole year after the burn-in | **adapted** (evaluation) | nothing is selected on Tetouan, and cross-fitting keeps every prediction out of sample (D70) |
| Metrics | eq. 17 F1, precision, recall, zone-strict F1, own-background-excluded F1, step AUC-PR, per-type recall, Wilcoxon over seeds | frozen | `benchmark.detection_metrics`, `step_auc`, `match_events` |
| Attribution score | macro-F1 over the injected classes; predictions of G1 or N count as errors | **adapted** (G1 absent) | `transfer.macro_f1` |

## 5. Engineering changes (code made general; no threshold changed) and their regression checks

| Change | Why it was needed | File |
|---|---|---|
| `zone_runs` returns typed empty columns | a series with no dead, hold or fill run produced a column-less table (first crash on Tetouan) | `src/rules_v1.py` |
| `clock_items` accepts an empty timestamp audit | a perfectly regular timeline has no duplicate or missing stamp (second crash) | `src/rules_v1.py` |
| `build_from_data` skips empty item kinds; drops helper columns only if present | a clean series has no dead or fill item (third crash) | `src/rules_v1.py` |
| `DawidSkene.predict` | apply the frozen label model to new items without refitting | `src/label_model.py` |
| `Injector` single-city patterns, `sample(types=...)` | multi-city types would sample 2–3 of 1 city | `src/inject.py` |
| `graph_model` reads `detector.SPLIT` at call time; top-k clamped to the number of zones | 2017 cross-fitting split; 4 cross-city neighbours of 3 zones would fail | `src/graph_model.py` |
| `build_panel` selects the cities of any named system; Tetouan registered (code T, 10-min) | the panel builder knew only "south" and Marrakech | `src/detector.py` |
| 2017 calendar and clock dates | the date lists covered 2022–2024 only | `src/detector.py`, `src/rules_v1.py` |
| `transfer.register` (adds Tetouan to the city dictionaries, sets the split), item-schema alignment | a third system | `src/transfer.py` |

**Regression on Morocco after these changes** (all exact):
- catalogue_v1 items, votes and zone runs are reproduced;
- the label model's `predict` on the Morocco votes equals its fitted q (max difference 0.0) and NB2's labels;
- the injector regenerates NB4's r03_s00 truth;
- the TCN-GAT MAE is still 0.0294.

**Chronology, 10 Nov 2026** (file modification times):
1. **21:18–21:19:** library changes (graph model, detector, label model, injector).
2. **21:22–21:25:** run on the real Tetouan series. The three empty-table crashes were fixed here, and the item-schema alignment was the last code change (`transfer.py` 21:25:56). The only result seen at that point was the real series' zero rule items.
3. **21:28:44:** NB6 generator written.
4. **21:28–21:30:** prototype (`Transfer.fit_predictors`, the same call as the notebook) trains the predictors, saved to `results/transfer_tetouan/models/` and later reloaded by NB6. It then scores one injected dataset (3 %, seed 0), which is the first injected result seen.
5. **21:32–21:44:** NB6 runs the 30 datasets with the code unchanged.
- No source, setting or generator file was modified after 21:30, so no design choice depends on an injected Tetouan result.

## 6. What the transfer shows (F55–F58)
- **Real clean year:** 0 false rule items. The main detector raises 7 alarms in 36 zone-months.
- **Injected events:** full-method F1 0.945 / 0.919 / 0.890 at 1 / 3 / 7 %, precision 0.98–1.00, above the rules alone at every rate (10/10 seeds, p = 0.002).
- **Attribution:** 5 of 6 classes at 0.85–1.00 accuracy (macro-F1 without A1 0.95–0.98). A1 → G2 is the single-city limit.
- **Detector alone:** the main detector is best at 1 %. The data-efficient LightGBM is better at 3–7 % on this one-year, 3-zone system.
