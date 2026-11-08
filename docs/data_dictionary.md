# Data dictionary

All times are as recorded in the source file (no clock correction). `end` is exclusive (the first step after the
run or item) unless stated otherwise.

## Input — `data/raw/`

| File | Content |
|---|---|
| `Data Morocco.xlsx` | Sheets `Laayoune`, `Boujdour`, `Foum eloued`, `Marrakech`. Column `DateTime` plus `zone1…zoneN`. The southern sheets are in A at 10 min; Marrakech is in kW at 30 min, whole numbers. Source: UCI 1158, CC BY 4.0. |
| `tetouan/Tetuan City power consumption.csv` | UCI Tetouan dataset (2017, 10 min, 3 zones in kW, plus weather). Not used yet (NB6). |

## Rule engine v0 — `results/event_catalogue_v0/` (from `src/rules_v0.py`)

**`zero_events.csv`** — one row per dead event (v0 definition: ≥ 3 steps with x = 0 or x ≤ 5 % x̂ and at least one exact zero, grouped across **all** cities by start within 10 min).

| Column | Meaning |
|---|---|
| event | v0 event id |
| start, end | first step; end of the last run (exclusive) |
| duration_h | hours |
| cities, n_cities | cities involved |
| zones | `City:zoneA,zoneB;City2:…` |
| n_zones | number of (city, zone) pairs |
| frac_zones | maximum, over cities, of the share of the city's zones involved |
| same_start | n_cities > 1 |
| exact_zero_share | η (eq. 5) |
| weekday, start_hour | start calendar |
| pre_ratio, restore_ratio, peak_ratio | Σx/Σx̂ over 30 min before, 30 min after (r), and the maximum over 60 min after (π), all on the main city's aggregate |
| ramp_to_90pct_min | τ, minutes until the ratio reaches 0.9 |
| provisional_type, rule | v0 classification and the rule that set it |

**`stuck_runs.csv`** — city, zone, start (first point), end (exclusive), points (identical values in the run), value.

**`transfers.csv`** — city, day, zone_up, delta_up, zone_down, delta_down, conservation_index (κ), score = (Δ_up − Δ_down)/(1 + κ).

**`timestamp_audit.csv`** — city, kind ∈ {duplicate, backward_jump, missing_run}, timestamp, n (copies of the stamp, 1 for a jump, or steps in the missing run).

## Rule engine v1 — `results/catalogue_v1/` (from `src/rules_v1.py`, NB1b)

**`zone_runs.csv`** — one row per qualifying run of one state in one zone.

| Column | Meaning |
|---|---|
| system | `south` (L, B, F) or `Marrakech` |
| city, zone, code | code is L1…, B1…, F1…, M1… |
| kind | `dead`, `hold` or `interp` |
| start, end | first step; first step after the run |
| steps | points in the run |
| n_zero | exact zeros in the run |
| value | last held value (hold runs) |
| slope | Δx per step (interp runs) |
| quantised | every value in the run is an integer |

**`items.csv`** — one row per item (the unit rules vote on). Columns present for every kind:

| Column | Meaning |
|---|---|
| item_id | `D###` dead, `F###` fill, `K###` clock, `T###` transfer (ids change if the engine is re-run with new parameters) |
| kind | dead, fill, clock or transfer |
| episode | `EP###` for dead and fill items (linked compound episodes); empty for clock and transfer |
| system, start, end, duration_h | |
| cities, zones | zones as codes, e.g. `B1,B2,F4` |
| n_cities, n_zones | |
| mv_label | v1 inspection label (plurality; `conflict:X\|Y` on ties; `G?` when only family votes; `abstain`) |
| n_votes, votes | `R9:G3;R10:G4` format |

Dead-item columns:

| Column | Meaning |
|---|---|
| frac_zones | as in v0 |
| eta | exact-zero share over the item's dead runs |
| restore_ratio, peak_ratio, ramp_min, pre_ratio | r_E, π_E, τ_E, pre-event ratio, aligned per zone and measured after a synthetic linear ramp if there is one (methods §3.1) |
| fill_ramp_zones | zones whose dead run is followed directly by a linear fill |
| fill_ramp_min | longest such fill, in minutes |
| start_hour, weekday | |
| hold_to_dead, interp_to_dead | zones where a hold or interpolation run ends exactly where the dead run starts |
| coext_hold_zones, coext_interp_zones | other zones with a hold or interpolation run co-extensive with the item (IoU ≥ 0.5) |
| others_alive | minimum, over the other cities of the system, of the median Σx/Σx̂ during the item (NaN if there are none) |

Fill-item columns:

| Column | Meaning |
|---|---|
| n_hold_zones, n_interp_zones | |
| fill_kind | hold, interp or mixed |
| max_points | longest run in the item |
| start_hour, weekday | |
| neighbours_vary | single-zone items only: share of neighbour zone-steps that are normal and moving |
| fill_to_dead | zones where a dead run starts exactly at the fill end |
| coext_dead_zones | other zones with co-extensive dead runs |

Clock-item columns:

| Column | Meaning |
|---|---|
| europe_date, morocco_date | the date is in that calendar of clock changes |
| n_duplicate_stamps, n_missing_steps | on that date |
| delta_star_min | δ\* (eq. 9; sign per D08) |
| corr_at_0, corr_best | profile correlation at δ = 0 and at δ\* |

Transfer-item columns: zone_up, delta_up, zone_down, delta_down, kappa.

**`votes.csv`** — item_id, then one column per rule (R1–R16, R19–R21) holding the voted label or empty (abstain).

**`rule_summary.csv`**:

| Column | Meaning |
|---|---|
| rule, family | |
| item_kind | the kind it votes on |
| n_items_of_kind | |
| n_votes, coverage | |
| labels | labels it emitted |
| overlap | items where another rule also fired |
| conflict | items where another rule emitted an incompatible label ("G" is compatible with any G type) |

**`key_events_v1.csv`** — the guide's C01–C12 and the G2 candidate mapped to v1 items. Columns: guide_id, item, episode, kind, start, h, zones, votes, mv.

**`episodes_compound.csv`** — episodes with ≥ 2 items: start, end, n_items, items, kinds, labels (v1 mv_label), cities.

## Label model — `results/labels_v1/` (from `src/label_model.py`, NB2)

**`q.csv`** — the probabilistic catalogue, one row per item.

| Column | Meaning |
|---|---|
| item_id, kind, episode, system, start, end, duration_h, cities, zones, n_cities, n_zones, votes | as in items.csv |
| inspection_label_v1 | v1 mv_label |
| feasible | classes allowed by kind and level (D29) |
| q_A1 … q_N | posterior probability per class (0 outside the feasible set) |
| label | arg max |
| confidence | max q |
| entropy | nats |
| label_majority_vote | baseline (D37) |
| label_ds_full | guide-style unconstrained Dawid–Skene |
| family | artefact (A*), grid event (G*) or normal (N) |

**`episodes_labelled.csv`**:

| Column | Meaning |
|---|---|
| episode, start, end, n_items | |
| cities, n_zones_max | |
| sequence | time-ordered `label(confidence)` joined by → |
| items | item ids |
| families | `+`-joined set of families |
| duration_h | |

**`rule_params.csv`**:

| Column | Meaning |
|---|---|
| rule, output | |
| speaks_for | classes the output supports |
| n_applicable | items in the rule's applicability domain |
| a_propensity, b_false_positive | |
| n_fired | |
| learned_precision | mean posterior mass on speaks_for over the items it fired on |
| log_odds_a_over_b | |
| defining | the rule gets the (9, 1) propensity prior |
| family | |

Other files:

| File | Content |
|---|---|
| `class_priors.csv` | π per item kind (rows) and class (columns) |
| `restarts_constrained.csv` | per restart: restart, loglik, penalised, n_iter, agree_with_best |
| `restart_stability.csv` | describe() of agree_with_best for the constrained and full models |
| `labeler_agreement.csv` | pairwise agreement between DS, MV and DS-full |
| `recovery_runs.csv` | per seed and labeler: accuracy, macro_f1, ece, brier (synthetic votes from the fitted model) |
| `recovery_summary.csv` | mean and std of the above |
| `robustness.csv` | test (drop family, or prior/init), setting, rules_removed, changed (share of all items whose label changes), changed_dead, changed_fill, changed_clock, changed_transfer |
| `summary.json` | headline counts used in the docs |

## Figure-side tables — `results/figures/`

| File | Content |
|---|---|
| `clock_offsets.csv` | date, event, city, delta_star_min, corr_at_0, corr_best (NB1; calendar dates only) |
| `interp_runs.csv` | NB1's interpolation runs (≥ 6 points everywhere, before the v1 priority rules): city, zone, start, end, points, slope_per_step, group |
