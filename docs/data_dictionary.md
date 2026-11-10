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

## Detector — `results/detector_v1/` (from `src/detector.py`, NB3)

| File | Columns / content |
|---|---|
| `predictor_metrics.csv` | system, residual (forecast, nowcast, expected (rho_hat = 1), STL), period (all, Jul 2023 +), MAE, median_abs, RMSE of ρ on rule-clean steps |
| `ljung_box.csv` | zone, n (clean steps), acf_lag1, lb_stat_1, lb_stat_144 (statsmodels Ljung–Box Q), residual |
| `hierarchy_consistency.csv` | residual; share of items whose top-scoring level matches the expected level, overall and per expected level |
| `hierarchy_consistency_by_kind.csv` | residual, kind (dead or fill), level, n, correct (share) |
| `detector_recall_of_rule_items.csv` | system, label (label model), items, detected (share with Z > γ in the item), median_score |
| `detector_only_nature.csv` | system, nature, n, median_h, median_rho, n_multizone |
| `structural_zeros.csv` | check, band (raw, W1–W4, V4), unit (zone, city or all zones), value. Checks: `share_v_exactly_0` / `share_u_exactly_0` (share of non-warm-up steps where the zone or city part is exactly 0); `B1_16-18Mar2024_*` (window share of zeros, old MAD, old and fixed max score); `zone_steps_old_MAD_below_1e-4` and `zone_steps_with_scale`. From `tools/diag_structural_zeros.py` on the LightGBM forecast residual (F35, D51) |

**`detector_items.csv`** — one row per detector-only candidate.

| Column | Meaning |
|---|---|
| item_id | `X###` |
| start, end, duration_h | |
| zones, n_zones, cities, n_cities | |
| max_score | max Z over the candidate |
| system, kind | kind = detector |
| nature | partial drop, surge or other |
| rho_mean, rho_min | |

## End model — `results/end_model_v1/` (from `src/end_model.py`, NB3)

**`normal_windows.csv`** — item_id `N###`, system, kind = normal, start, end, zones, n_zones, cities, n_cities, duration_h.

**`item_features.csv`** — one row per rule item (D/F), normal window (N) and detector candidate (X). Columns: item_id, system, source (rule, normal or detector), plus the features in the table.

| Feature | Meaning |
|---|---|
| duration_h, n_zones, n_cities, frac_zones, multi_city | structure |
| share_zero, share_dead, share_hold, share_interp, share_missing | zone-step state shares |
| share_flat | share with Δx = 0 |
| rho_mean, rho_min, rho_std | zone-mean ρ during the item |
| pre_rho, post_rho | 30 min before / after |
| post_peak | max over 60 min after |
| start_hour, start_sin, start_cos, weekday, weekend | calendar |
| preceded_by_fill, followed_by_fill | fill adjacency |
| ep_n_items, ep_has_multizone_fill, ep_has_multicity_dead, ep_duration_h | episode context; 1, 0, 0 and own duration outside episodes |
| det_g_max, det_g_mean, det_u_max, det_u_mean, det_v_max, det_v_mean | raw-band level scores |
| det_top_g, det_top_u, det_top_v | one-hot of the top level |
| det_W1_max … det_W4_max, det_V4_max | band maxima over all levels |
| det_nb_max | nowcast zone score |

**`end_model_metrics.csv`**:

| Column | Meaning |
|---|---|
| variant | |
| agree_rule_items | OOF arg max vs label-model arg max |
| normal_windows_as_N | |
| soft_CE_rule, soft_CE_normal | soft cross-entropy |
| agree_A1 … agree_N | per label-model class |

**`p_type.csv`** — final probabilistic labels for event items (the guide's `p_type`). Columns:
- item_id;
- source (rule, normal or detector);
- q_{class}: the label-model q; NaN for detector candidates;
- f_{class}: the end model, out of fold for rule and normal items;
- p_{class}: fused, eq. 16;
- label_q, label_f, label_p, confidence_p.

The classes are A1, A2, A3, G1, G2, G3, G4, N. **For detector candidates, label N means that no typed class fits** (F32).

**`summary.json`** — headline numbers of the run: backend (`lightgbm` or `sklearn`), lightgbm_version, colab (true if run on Colab), γ, MAEs, hierarchy consistency, end-model agreement, fused changes, recall, nature counts, runtime. Check `backend` before citing any NB3 number.

## Figure-side tables — `results/figures/`

| File | Content |
|---|---|
| `clock_offsets.csv` | date, event, city, delta_star_min, corr_at_0, corr_best (NB1; calendar dates only) |
| `interp_runs.csv` | NB1's interpolation runs (≥ 6 points everywhere, before the v1 priority rules): city, zone, start, end, points, slope_per_step, group |

## Benchmark — `results/benchmark_v1/` (from `src/benchmark.py`, `src/inject.py`, `src/graph_model.py`, NB4)

| File | Content |
|---|---|
| `predictor_comparison.csv` | predictor (LGB forecast, LGB nowcast, TCN without graph, TCN-GAT, LightGBM + TCN correction, LightGBM + learned-graph correction, mean of LightGBM and TCN-GAT), period (all, Jul 2023 +), MAE, median_abs, RMSE of ρ on rule-clean real steps |
| `hierarchy_consistency_by_predictor.csv` | NB3's residual-hierarchy test per predictor: predictor, kind, level, n, correct |
| `learned_cross_city_edges.csv` | cross-city edges of the graph model shown in E20 (TCN-GAT): to (receiving zone), from (sending zone), mean attention on clean steps |
| `learned_cross_city_edges_tcn_gat.csv`, `learned_cross_city_edges_lgb_gat.csv` | the same for the TCN-GAT and for the graph hybrid (D59) |
| `table5_detection.csv` | rate, method, F1, precision, recall, F1_zone_strict, AUC_PR (mean ± sd over seeds, test period), F1_own_background_excluded (D60), real_data_alarms (detections on the uninjected series), start_err_min (median) |
| `table5_wilcoxon.csv` | rate, comparison (ours vs best baseline; main detector vs each other detector), F1 of both, Wilcoxon signed-rank p over seeds |
| `detection_recall_by_type.csv` | mean recall per injected type, per rate and method (test period) |
| `beta_tuning_train_period.csv` | rate, beta, abstain, attribution scores on training-period events |
| `table6_attribution.csv` | rate, labeler, macro_F1, accuracy, ECE, Brier (mean ± sd), per-class F1 (test period) |
| `end_to_end.csv` | rate, seed, share of typed events detected, end-to-end accuracy (missed = wrong) |
| `fig10_confusion_fused.csv` | injected type × fused label counts (3 %, test, pooled seeds) |
| `table7a_pipeline.csv`, `table7b_detector.csv`, `table7c_rule_families.csv`, `table7d_threshold_sensitivity.csv` | ablations (Table 7) |
| `hard_negatives.csv` | detector, day type (ordinary weekday, weekend, Ramadan, national holiday, Eid), rule-negative zone-steps, flag rate, ratio to ordinary weekdays (real data) |
| `summary.json` | headline numbers, device, versions, rates, seeds, tuned β, runtime |
| `models/` | trained predictors: `lightgbm_models.pkl` (git-ignored, on Drive), `tcn.pt`, `tcn_gat.pt`, `hybrid_tcn.pt`, `hybrid_gat.pt` (D59) and their training histories |
| `dev_selection.json` | development selection (D60, D61; `tools/dev_select_detector.py`): main detector, event formation {detector: w, q, gap}, development datasets, grid, rules-only F1, main candidates with their F1 |
| `dev/dev_detection_grid.csv` | development detection per dataset tag, detector, w, q, gap, what (alone, rules + detector), period: n_pred, n_true, precision, recall, f1, precision_zone, recall_zone, f1_zone, recall_U_SHOCK, recall_U_PARTIAL, n_det_only |
| `dev/dev_auc.csv` | development step-wise AUC-PR per tag, detector, smoothing w, period |
| `dev/dev_rules_only.csv` | the rules alone on the development datasets |
| `dev/real_candidates_by_setting.csv` | detector-only candidates on the real series per detector and setting (false-alarm budget) |
| `dev/dev_best_settings.csv`, `dev/dev_main_candidates.csv` | the chosen setting per detector (with F1 at NB3's setting and real-data alarms) and the ranking of the main candidates |

**`runs/`** — one set of files per injected dataset, tag `r{rate %}_s{seed}` (e.g. `r03_s00`):
- `_truth.csv`: injected events with event_id (`I####`), type (A1–A3, G1–G4, U_SHOCK, U_PARTIAL), start, end (core span, exclusive), end_affected (end of the restoration tail), duration_h, mechanism (zero, hold, linear, floor, x-factor), zone_steps, omega (overshoot), ramp_min, zones, n_zones, cities, n_cities, family, pattern (zone, zones, city, cities) and episode (`J####` for an A2 → A1 compound);
- `_detection.csv`: method, period, gamma, n_pred, n_true, precision, recall, f1, precision_zone, recall_zone, f1_zone, start_err_min, end_err_min, recall_{type}, and with own real-data detections excluded n_pred_bgx, precision_bgx, recall_bgx, f1_bgx, f1_zone_bgx (D60);
- `_auc.csv`: method, period, auc_pr (step-wise average precision);
- `_events.csv`: one row per injected event: type, period, detected, the matched predicted item (item_id, source rule/detector), its feasible set, majority-vote label, q_/f_/fn_ distributions over the 8 event classes (fn = end model without detector features) and, at 3 %, `lm_without_{family}` labels;
- `_info.json`: runtime, number of rule items and detector-only candidates, γ of the main detector;
- `sens_s{seed}_{config}_det.csv` / `_lab.csv`: threshold sensitivity (rule-only detection; label-model labels of typed events).

**`graph_ablation/`**: the no-graph ablation of the main detector, computed after the NB4 run by `tools/graph_ablation.py` (D62) on the same datasets:
- `dev_detection_grid.csv`: development seeds 100–104, detectors `TCN-GAT, hierarchy, multi-scale` and `TCN, no graph, hierarchy, multi-scale`, the 48 settings. Same columns as `dev/dev_detection_grid.csv`.
- `runs/r{rate}_s{seed}_detection.csv` and `test_detection.csv` (all runs). Columns:
  - method: the main detector recomputed; the no-graph TCN at the main setting; the no-graph TCN at its own tuned setting `(own tuned event formation)`;
  - period, gamma, w, q, gap, rate, seed;
  - the `_detection.csv` metrics of `runs/`, the `*_bgx` metrics and `auc_pr`.
- `table_graph_ablation.csv`: rate, method, setting, F1, precision, recall, F1_zone_strict, AUC_PR, F1_own_background_excluded, real_data_alarms, recall_U_SHOCK, recall_U_PARTIAL, start_err_min. Test period, mean ± sd over seeds.
- `wilcoxon_graph_ablation.csv`: rate, comparison, metric (f1, f1_bgx, auc_pr), means, main_wins, ties, Wilcoxon p, n_seeds.
- `reproduction_main_detector.csv`: the main detector's test F1 recomputed here (CPU) against the stored NB4 row (Colab GPU), per rate and seed.
- `summary.json`: development result (own setting of the no-graph TCN, its F1, the main detector's recomputed best setting), real-data alarms, reproduction statistics, test F1 per rate and method.

## Main detector on the real data — `results/main_detector/` (NB4 §8b, D61)

| File | Content |
|---|---|
| `detector_items_south.csv` | detector-only candidates of the main detector (TCN-GAT graph detector, tuned event formation) on the real south series: item_id `X###`, system, start, end, zones, n_zones, cities, n_cities, max_score, kind, duration_h |
| `p_type_south.csv` | every south rule item and detector-only candidate: q_ (label model), f_ (end model), fn_ (end model without detector features), p_ (fused, β tuned at 3 %, D50 abstention) over the 8 event classes, and label |
| `summary.json` | main detector, setting, γ, β, number of candidates (and NB3's), candidates shared with NB3, rule labels changed relative to NB3's p_type, label counts of the candidates |

## Downstream test — `results/downstream_v1/` (from `src/downstream.py`, NB5; D64–D66)

| File | Content |
|---|---|
| `outage_real.csv` | per south zone: naive_zone_hours and naive_outages (every flagged dead state), typed_zone_hours and typed_outages (dead steps of G-labelled items), artefact_dead_zone_hours and artefact_dead_runs (dead steps of A-labelled items), city |
| `forecast_real.csv` | strategy (S0, S1, S2), model (LightGBM, naive), horizon (1 h, 1 day), subset (all; after anomaly (2 days)), n_train (training rows), n (scored zone-steps), MAE, RMSE (A), MASE, sMAPE (%) |
| `loss_real.pkl` | per-time-step summed scaled absolute loss per (strategy, model, horizon, subset), for the DM tests |
| `dm_real.csv` | model, horizon, subset, comparison (S1 vs S2, S0 vs S2), mean_loss_diff (> 0: second better), share_steps_second_better, n_steps, DM, p (two-sided) |
| `injected/r{rate}_s{seed}_forecast.csv`, `_dm.csv` | the same on one injected dataset, with S3 (oracle) and the S2 vs S3 comparison; rate, seed |
| `injected/r{rate}_s{seed}_outage.csv` | strategy (truth (S3), naive (S0), interpolated away (S1), typed (S2)), zone_hours, outages (runs ≥ 3 steps), typed_precision_zone_steps, typed_recall_zone_steps, rate, seed |
| `table8_forecasting.csv` | mean MAE, RMSE, MASE, sMAPE by data (real, injected), model, horizon, subset, strategy |
| `table8_dm.csv` | every DM test (real and per injected dataset) |
| `outage_injected.csv` | mean outage zone-hours and counts by rate and strategy |
| `summary.json` | real-data outage totals and ratio, dead zone-hours by label, real-data forecast scores and DM tests, injected outage means and ratios to truth, runtime |
