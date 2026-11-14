# Methods as implemented

This file describes what the code actually does, in paper-ready form. Equations (1)–(20) are the guide's
(`docs/research_guide.md`) and keep their numbers. Where the implementation differs from them, this file says so.
New equations start at (21). Decision numbers (D…) point to `docs/decisions.md`; finding numbers (F…) to
`docs/findings.md`.

## 1. Data and preprocessing

**Data.**
- The UCI "High-resolution load dataset from smart meters across various cities in Morocco" (id 1158), one xlsx with four sheets.
- Laâyoune (5 zones), Boujdour (3) and Foum El Oued (7) are recorded in amperes every 10 min on one shared timeline (14 Sep 2022 17:10 – 24 May 2024 00:00, 88,890 rows each). Because of that shared timeline we call them the **southern system**.
- Marrakech (2 zones) is recorded in kW every 30 min (9 Jan 2023 – 8 Jan 2024, 17,501 rows). It is a separate system.

**Regular grid** (`rules_v0.regularise`). Duplicate timestamps are averaged and rows sorted. The series is reindexed on a regular grid from first to last stamp, so missing stamps become NaN. Timestamps are used **as recorded**, with no clock correction (D11).

**Expected value** (eq. 1, `rules_v0.expected`): for each zone, the median of the same time-of-day slot over the previous K = 14 days, excluding zeros. P = 144 steps per day in the south, 48 in Marrakech. Marrakech's first 14 days have no or partial baseline.

**Relative level** (eq. 2): ρ = x / x̂.

## 2. Per-step states (rule engine v1)

For each zone series x_t the code computes four boolean states (`rules_v1.state_masks`).

**Exact zero:** x_t = 0.

**Linear interpolation** (new, D07). With Δ the first difference:

```latex
\ell_t = \mathbb{1}\left[\, |\Delta^2 x_t| < 10^{-8}\max(1, |x_t|) \;\wedge\; |\Delta x_t| > 10^{-12} \;\wedge\; x_t \neq 0 \,\right] \tag{21}
```

A point is interpolated if it belongs to a run of ≥ m_i collinear points. That is a run of ≥ m_i − 2 consecutive ℓ_t = 1, extended by the two points before it. m_i = 6 in the south and 12 in Marrakech (D17).

**Hold** (eq. 6): a point is held if it belongs to a run of ≥ m_h identical non-zero values, with m_h = 6 in the south and 12 in Marrakech.

**Dead** (eq. 4 with priority, D16). Let n_t = 𝟙[x_t ≤ ε x̂_t] with ε = 0.05 (the noise floor). Then

```latex
d_t = \mathbb{1}[x_t = 0] \;\vee\; \left(n_t \wedge \neg \text{interp}_t\right), \qquad
\text{hold}_t \leftarrow \text{hold}_t \wedge \neg d_t, \qquad
\text{interp}_t \leftarrow \text{interp}_t \wedge \neg d_t \wedge \neg \text{hold}_t \tag{22}
```

so the priority is exact zero > linear interpolation > noise floor > hold.

**Zone runs.** Maximal runs of each state per zone:
- dead runs need ≥ 3 steps, and since D15 no exact zero;
- hold and interpolation runs need ≥ m_h and ≥ m_i points.

Each run stores start, end (exclusive), number of steps, number of exact zeros, the held value and the slope.

## 3. Items: the units rules vote on (D13)

**Dead items.**
- Dead runs of one system are sorted by start. A run joins the current item if its start is within τ = 10 min of the item's **first** start; otherwise it opens a new item. This is eq. 7, keeping v0's semantics (D14).
- Features:
  - start, end, duration;
  - cities, n_cities = S_E, zones, n_zones;
  - frac_zones: the maximum, over the involved cities, of the share of the city's zones involved;
  - η (eq. 5) = exact zeros / steps over all the item's runs;
  - restoration features (§3.1);
  - start hour and weekday;
  - context features (§3.2).

**Fill items.** Hold and interpolation runs of one system, grouped the same way (hold and interpolation together). Features:
- n_hold_zones, n_interp_zones;
- fill_kind ∈ {hold, interp, mixed};
- max_points;
- neighbours_vary (single-zone items only): the share of (other zones of the same city × steps of the run) that are in no anomalous state, not NaN, and have Δx ≠ 0;
- fill_to_dead: number of zones where a dead run starts exactly at the fill end;
- coext_dead_zones (§3.2).

**Clock items** (city, date).
- Candidate dates are the union of:
  - Europe's DST dates (2022-10-30, 2023-03-26, 2023-10-29, 2024-03-31);
  - Morocco's Ramadan switches (2023-03-19 → GMT, 2023-04-23 → GMT+1, 2024-03-10 → GMT, 2024-04-14 → GMT+1);
  - every date with duplicate or missing stamps in the timestamp audit.
- Features:
  - the number of duplicated stamps and of missing steps that day;
  - Europe or Morocco calendar flags;
  - δ\* (eq. 9) with the correlation at δ = 0 and at δ\*.

**δ\* as computed** (D08). The profile is the mean daily shape over 7 days: dead, held and interpolated steps are removed, each zone is divided by its mean, and zones are averaged. "pre" is [D − 7 d, D) and "post" is [D + 1 d, D + 8 d). δ ∈ [−120, 120] min in steps of the data resolution, applied as a circular shift. Sign: δ\* > 0 means post-D behaviour is stamped δ later. The item is NaN if 7 days are not available on both sides.

**Transfer items.** v0's detector (`rules_v0.transfers`):
- Daily means with zeros excluded.
- Δ_z(d) = median of daily means over [d + 1, d + 14] minus median over [d − 13, d]. Rolling 14-day medians need at least 10 days. **This is a one-day shift relative to eq. 8.**
- A day is a candidate if the largest increase exceeds 0.25 × the zone's long-run mean level and the largest decrease is below −0.25 × that level.
- κ = |Σ_z Δ_z| / max(Δ_up, −Δ_down).
- The best day per (city, zone pair, calendar month) is kept, ranked by (Δ_up − Δ_down) / (1 + κ).

### 3.1 Restoration features (eq. 3 as implemented, D22)

For each dead run of the item:
- The alignment index k is the first step after the run. If an interpolation run in the same zone starts exactly there, k moves to the first step after that interpolation run, so a synthetic straight-line "ramp" is skipped (F05).
- The sums below run over the item's zones, each aligned at its own k:

```latex
r_E = \frac{\sum_z \sum_{j=0}^{n_{30}-1} x^z_{k_z+j}}{\sum_z \sum_{j=0}^{n_{30}-1} \hat x^z_{k_z+j}}, \qquad
\pi_E = \max_{0 \le j < n_{60}} \frac{\sum_z x^z_{k_z+j}}{\sum_z \hat x^z_{k_z+j}}, \qquad
\tau_E = \Delta \cdot \min\{ j < n_{6h} : \text{ratio}_j \ge 0.9 \} \tag{3'}
```

Here n_30 = 3, n_60 = 6 and n_6h = 36 steps at 10 min (1, 2 and 12 at 30 min). τ_E is NaN if the ratio never reaches 0.9 within 6 h. The pre-event ratio uses the n_30 steps before each run's start.

### 3.2 Context features (D19)

For a dead item E = [s, e) and a fill run F = [s_F, e_F) in a zone **not** in E (same system):

```latex
\mathrm{IoU}(E, F) = \frac{|E \cap F|}{|E \cup F|}, \qquad F \text{ is co-extensive with } E \iff \mathrm{IoU}(E, F) \ge 0.5 \tag{23}
```

- coext_hold_zones and coext_interp_zones count zones with co-extensive hold or interpolation runs.
- hold_to_dead and interp_to_dead count the item's zones where a hold or interpolation run ends exactly where the dead run starts.
- others_alive is the minimum, over the other cities of the system, of the median of Σx / Σx̂ during [s, e).

### 3.3 Episodes

Two dead or fill items of one system are linked if both hold:
1. they overlap or touch, with a gap of at most 10 min;
2. either some zone-run boundary (start or end) of one is within 10 min of a boundary of the other, or their time IoU is ≥ 0.5.

Episodes are the connected components (union–find), numbered in time order (EP000, EP001, …).

## 4. Labelling rules (v1)

Each rule votes one label or abstains. Parameters are the guide's defaults unless noted.

| Rule | Item | Votes | Condition as implemented |
|---|---|---|---|
| R1 | dead | A1 | n_cities ≥ 2 ∧ η ≥ 0.95 ∧ \|r_E − 1\| ≤ 0.2 ∧ τ_E ≤ 10 min |
| R2 | fill | A2 | n_hold_zones ≥ 2 |
| R3 | dead | A1 | hold_to_dead ≥ 1 |
| R4 | dead | A1 | coext_hold_zones ≥ 1 (IoU ≥ 0.5; the guide uses any-step overlap, D19) |
| R5 | dead | G | π_E ≥ 1.15 |
| R6 | dead | G | η < 0.9 |
| R7 | dead | G1 | n_cities ≥ 2 ∧ ¬(R3 ∨ R4 ∨ R21) ∧ (R5 ∨ R6 ∨ ¬(τ_E ≤ 30 min)) (D20) |
| R8 | dead | G2 | n_cities = 1 ∧ frac_zones ≥ 0.9 ∧ (others_alive > 0.5 or no other city in the system) |
| R9 | dead | G3 | n_zones = 1 |
| R10 | dead | G4 | R9 ∧ 6 ≤ start hour ≤ 11 ∧ duration ≤ 6 h (D24) |
| R11 | dead | G3 | R9 ∧ duration > 24 h |
| R12 | fill | A3 | n_zones = 1 ∧ fill_kind = hold ∧ neighbours_vary ≥ 0.8 |
| R13 | clock | A4 | duplicated stamps on that date > 0 |
| R14 | clock | A4 | missing steps on that date > 0 ∧ the date is a Europe or Morocco clock date |
| R15 | clock | A4 | \|δ\*\| ≥ 50 min ∧ corr(δ\*) ≥ 0.9 ∧ corr(δ\*) − corr(0) ≥ 0.05 (D21) |
| R16 | transfer | G5 | κ ≤ 0.3 |
| R19 | fill | A2 | n_interp_zones ≥ 2 (new) |
| R20 | fill | A3 | n_zones = 1 ∧ fill_kind = interp ∧ neighbours_vary ≥ 0.8 (new) |
| R21 | dead | A1 | interp_to_dead ≥ 1 ∨ coext_interp_zones ≥ 1 (new) |

R17 and R18 (external evidence) are not implemented (D26).

**Rule families** (for ablation):
- simultaneity {R1, R7}
- hold {R2, R3, R4, R12}
- restoration {R5, R6}
- city {R8}
- single zone {R9, R11}
- calendar {R10, R14}
- clock {R13, R15}
- conservation {R16}
- interpolation {R19, R20, R21}

## 5. Label model (`src/label_model.py`)

**Classes:** Y = {A1, A2, A3, A4, G1, G2, G3, G4, G5, N}.

**Feasible set** 𝒴(i) per item, from its kind and level (D29):

| Item | 𝒴(i) |
|---|---|
| dead, n_cities ≥ 2 | {A1, G1} |
| dead, one city, ≥ 2 zones | {A1, G2, G3} |
| dead, one zone | {A1, G3, G4} |
| fill, ≥ 2 zones | {A2, N} |
| fill, one zone | {A3, N} |
| clock | {A4, N} |
| transfer | {G5, N} |

**Applicability** 𝒜(i) (D30): the rules whose precondition can observe item i.
- R2 and R12 apply to fills containing a hold; R19 and R20 to fills containing interpolation.
- R13 applies to clock items that are not spring-forward dates; R14 only to spring-forward dates (Europe Mar; Morocco → GMT+1).
- R15 applies where δ\* is computable.
- Every other rule applies to all items of its kind.

**What an output speaks for** (D31): S(r, l) = {l}, except S(·, G) = {G1, …, G5} and S(R9, G3) = {G3, G4}.

**Likelihood with abstention** (replaces eq. 10, D28):

```latex
q_i(y) \;\propto\; \mathbb{1}[y \in \mathcal{Y}(i)]\; \pi_{k(i)}(y) \prod_{r \in \mathcal{A}(i)} \theta_r\big(y, o_{ir}\big), \qquad o_{ir} \in \{\varnothing\} \cup \mathrm{out}(r) \tag{24}
```

**Constrained (one-coin) parameterisation** (D32):

```latex
\theta_r(y, l) = \begin{cases} a_{rl} & y \in S(r,l) \\ b_{rl} & y \notin S(r,l) \end{cases}, \qquad \theta_r(y, \varnothing) = 1 - \sum_{l} \theta_r(y, l) \tag{25}
```

**M-step** with Beta pseudo-counts (replaces eq. 11; D32–D34). The sums run over items where r is applicable, and m_i, n_i are the posterior masses on S(r, l) and on its complement:

```latex
a_{rl} = \frac{\alpha_1 + \sum_i m_i \mathbb{1}[o_{ir} = l]}{\alpha_1 + \alpha_0 + \sum_i m_i}, \quad
b_{rl} = \frac{\beta_1 + \sum_i n_i \mathbb{1}[o_{ir} = l]}{\beta_1 + \beta_0 + \sum_i n_i}, \quad
\pi_k(y) \propto \gamma + \sum_{i: k(i) = k} q_i(y) \tag{26}
```

**Settings:**
- (α_1, α_0) = (1, 1) for ordinary rules and (9, 1) for **defining** rules (R2, R8, R10, R12, R13, R14, R16, R19, R20; D33);
- (β_1, β_0) = (1, 9);
- γ = 1 per class of the kind.

**EM.**
- Initialise π uniform over each kind's classes, a = 0.7 and b = 0.05.
- 20 restarts: restart 0 is deterministic; the others multiply the initial a and b by exp(N(0, 0.5²)), clipped to [0.001, 0.95].
- Stop when |Δ log-likelihood| < 1e-6 (at most 3,000 iterations).
- Keep the restart with the highest log-likelihood + log Beta prior.

**Guide-style baseline** (`structure="full"`): one free row θ_r(y, ·) per class with Dirichlet α = 1, with the same feasibility, applicability and π prior.

**Majority vote** (D37): plurality over 𝒴(i), with weight split evenly across the feasible classes an output speaks for.

**Diagnostics** (D36):
- restart agreement;
- learned propensity a and false-positive rate b per rule, and log(a/b);
- learned precision (mean posterior mass on S(r, l) over the items r fired on);
- parameter recovery: simulate classes and votes for the same items from the fitted model, refit, and score accuracy, macro-F1, ECE (eq. 18, 10 bins) and Brier score;
- robustness: the share of items whose arg-max label changes when one rule family is removed or one prior is changed.

**Outputs.**
- q.csv: one row per item with q(y) for every class, label = arg max, confidence = max q, entropy, and the majority-vote and full-model labels.
- Episodes are summarised as the time-ordered sequence of their items' labels.

## 6. Detector: residuals, multi-scale bands, residual hierarchy (`src/detector.py`, NB3)

**Systems.** South: 15 zones (L1–L5, B1–B3, F1–F7) on one 10-min timeline. Marrakech: 2 zones at 30 min; its hierarchy is degenerate (one city, so u ≡ 0).

**Target and mask.** ρ_t^z = x_t^z / x̂_t^z (eq. 2), clipped to [0, 3]. M_t^z = 1 if the step is dead, held or interpolated (rule engine v1 states) or ρ is missing.

**Predictors** (D39–D41). Each zone gets a LightGBM regressor with the Huber objective (δ = 0.1), trained on steps with M = 0 only (the guide's masked loss). Two-fold temporal cross-fitting at 2023-07-01 makes every prediction out of sample.

- *Forecast features:*
  - the zone's own lags at 1, 2, 3 and 6 steps, 1 day, 2 days and 7 days, with flagged steps set to NaN;
  - the mean of the last 6 steps and the median of the previous day (both masked);
  - calendar (D48).
- *Nowcast features* (guide eq. 13): the forecast features plus the current ρ of every other zone of the system.
  - **Paper text (requested by the author, 2026-11-08):** this nowcast is a fully connected "graph" with no learned edges: every other zone's current value is a plain input to the tree model. It adds nothing (clean-data MAE 0.0292 vs 0.0288 for the forecast), so it is used only as a comparison and as an end-model feature, not as the main residual (D40, F29). The learned graph model of the guide (TCN-GAT) is evaluated separately in NB4. There it becomes the main detector (§6.1, D61).

```latex
e_t^{z} = \rho_t^{z} - \hat\rho_t^{z} \tag{27}
```

**Multi-scale bands** (D42). MODWT pyramid with the LA(8) filters g̃ = g/√2 and h̃_l = (−1)^l g̃_{L−1−l}:

```latex
W_{j,t} = \sum_{l=0}^{L-1} \tilde h_l\, V_{j-1,\,t-2^{j-1} l}, \qquad V_{j,t} = \sum_{l=0}^{L-1} \tilde g_l\, V_{j-1,\,t-2^{j-1} l}, \qquad V_{0} = e \tag{28}
```

for j = 1…4. Each band is then phase-aligned: W_j and V_4 are shifted back by their group delay ν (4, 11, 25 and 53 steps for W1–W4, 43 for V4), measured as the energy centroid of the band's impulse response. That shift makes them approximately zero-phase: non-causal, which is fine for a retrospective catalogue. The bands are b ∈ {raw (e itself), W1, W2, W3, W4, V4}.

**Residual hierarchy** (eq. 14), per band b: g_t = median over the system's zones, u_t^c = median over city c minus g_t, v_t^z = e_t^z − g_t − u_t^{c(z)}.

**Level scores** (eq. 15, D43): a trailing 28-day robust z-score of |ε| for ε ∈ {g, u^c, v^z}, with a minimum of 7 days of history. The median and MAD use only steps that are rule-clean at that level and exclude **structural zeros** (|ε| ≤ 10⁻¹²). A median over an odd number of zones is attained by one of them, so that zone's v is exactly 0 by construction. Left in, these zeros collapse the scale whenever one zone is its city's median for half the window (D51, F35). Scores are undefined during a 21-day warm-up.

z_t = (|ε_t| − med_W|ε|) / (1.4826 · MAD_W|ε| + 10⁻⁶), W = {s ∈ (t − 28 d, t] : s rule-clean at the level, |ε_s| > 10⁻¹²}   (eq. 15 as implemented)

**Zone-step score and flags:**

```latex
Z_t^{z} = \max_{b}\, \max\left( s_{t}^{g,b},\; s_{t}^{u,c(z),b},\; s_{t}^{v,z,b} \right), \qquad \text{flag}_t^z = \mathbb{1}[Z_t^z > \gamma], \quad \gamma = Q_{0.995}\{Z_t^z : (t, z) \text{ rule-negative}\} \tag{29}
```

**Residual-hierarchy test** (D40). For each southern dead or fill item, take the arg max over {max s^g, max s^u (item cities), max s^v (item zones)} over its span (raw band). Compare it with the structural level: multi-city → g; ≥ 90 % of one city → u; one zone → v.

A zone-step is rule-negative if two conditions hold:
- its zone has no rule state within ±53 steps (half the support of the widest band);
- the system has no multi-zone rule state within ±53 steps.

**Detector-only candidates** (D44): flag runs of ≥ 3 steps (gaps ≤ 1) that do not overlap a rule zone-run of the same zone extended by ±53 steps, grouped across zones by start within 10 min. They are described as follows (not typed):
- partial drop: mean ρ < 0.7 and minimum ρ < 0.5;
- surge: mean ρ > 1.4;
- other.

**Baseline residual:** statsmodels STL (period 1 day, non-robust, D49). **Residual diagnostics:** statsmodels Ljung–Box at lags 1 and 144, and lag-1 autocorrelation of clean residuals.

### 6.1 The main detector: TCN-GAT multi-scale graph residual detector (NB4; D53, D60, D61)

This replaces the LightGBM forecast as the predictor of eq. 27 for the south. Bands, hierarchy and level scores are unchanged. Marrakech keeps LightGBM.

**Predictor** (`src/graph_model.py`, guide eq. 13). The nodes are the 15 southern zones.

1. *Temporal encoder.* A causal temporal convolutional network, shared by all zones, reads each zone's past (ρ, with flagged steps set to 1, and the mask flag):
   - 6 residual blocks, kernel 3, dilations 1–32, 32 channels;
   - receptive field 253 steps (about 42 h).
2. *Graph attention* (2 heads). Zone z attends to the *current* value and mask of its neighbours; its own current value is never an input.
   - Masked neighbours are excluded.
   - Neighbours are the same-city zones plus k = 4 cross-city zones. These are learned: each zone has a 16-d embedding and keeps the 4 zones of other cities with the highest cosine similarity (GDN-style, recomputed at every forward pass).
3. *Head* (MLP). It combines the TCN state, the attention message, the node embedding, the calendar (11 features) and the zone's own value and mask 1 day and 7 days earlier.

*Training:*
- masked Huber loss (δ = 0.1), on rule-clean steps only;
- the same two-fold cross-fitting as LightGBM;
- AdamW (lr 2·10⁻³, weight decay 10⁻⁴, cosine schedule);
- early stopping on the last 15 % of each fold (patience 6, at most 40 epochs);
- chunked, fully convolutional training (warm-up = receptive field, chunks of 256 steps).

**Event formation** (D60), replacing the γ of eq. 29 and D44's gap for every compared detector:

```latex
\tilde Z_t^{z} = \frac{1}{w}\sum_{k=-\lfloor w/2\rfloor}^{\lceil w/2\rceil-1} Z_{t+k}^{z}, \qquad
\text{flag}_t^z = \mathbb{1}[\tilde Z_t^z > \gamma_q], \quad \gamma_q = Q_{q}\{\tilde Z_t^z : (t, z) \text{ rule-negative}\} \tag{29'}
```

- Flag runs of ≥ 3 steps, with gaps up to `gap` steps, form the events.
- The main detector uses w = 24 (4 h), q = 99.9 % and gap = 12. NB3 used w = 1, q = 99.5 % and gap = 1.
- w, q and gap are chosen per detector on separate development datasets, by the detector's own event F1 (seeds 100–104; `tools/dev_select_detector.py`). Every baseline gets the same tuning budget, and ablations inherit the main detector's setting.

**Selection.** Among TCN-GAT, LightGBM, their average and the graph hybrid, the main detector is the one whose detector-only candidates best complement the rules (F1 of rules + detector on the development datasets; F39).

**Ablations and alternatives evaluated in NB4:**
- LightGBM forecast;
- the average of LightGBM and TCN-GAT;
- the hybrids LightGBM + learned-graph correction and LightGBM + TCN correction (D59; the correction starts at 0, and the graph also reads the neighbours' current LightGBM residuals);
- TCN without graph;
- the main detector at a single scale and without the hierarchy;
- TCN-GAT and LightGBM with NB3's event formation.

**Scoring area** (D60): rule-based, the same for every detector.



### 6.2 The learned graph as an ablation (D62, D67)

The learned graph is evaluated as an **ablation of the main detector**: graph attention on or off, everything else unchanged.
- **Without the graph:** the same TCN (encoder and head, no attention message), trained the same way (`graph=False`, D53).
- Its residual goes through the same MODWT bands, region/city/zone hierarchy and robust scores (`benchmark.V_TCN_MS`, "TCN, no graph, hierarchy, multi-scale").
- It is scored on the same injected datasets in two ways:
  1. with the main detector's event formation, so that only the graph changes;
  2. with its own event formation, tuned on the development seeds like every other detector, so that it is not handicapped by a setting chosen for the graph.
- Paired Wilcoxon tests over the 10 seeds compare it with the main detector at each rate (Table 7e, Fig 9b; `tools/graph_ablation.py`, `tools/ablation_summary.py`).
- **The other ablations in Table 7e:** the predictor (LightGBM instead of TCN-GAT, own tuning), the scales (raw band only), the hierarchy (flat robust z of the zone residual), graph and scales together (TCN, raw band), and the event formation (NB3's setting).
- **Result (F42):** removing the graph leaves event F1 equal or slightly higher. The paper therefore presents the graph as an ablation that adds no detection skill (D86: no interpretability claim, because the paper does not analyse the learned edges). The detection gain comes from the neural residual, the multi-scale scoring and the tuned event formation (F41–F43).

## 7. End model and fusion (`src/end_model.py`, NB3)

**Items:**
- rule items (dead and fill; targets q from the label model);
- normal windows (target N; D45);
- detector-only candidates (unlabelled).

Clock and transfer items keep their label-model q (D46). The classes are EVENT_CLASSES = {A1, A2, A3, G1, G2, G3, G4, N}.

**Features φ_i**, computed identically for every item from its span [s, e) and zone set:

| Group | Features |
|---|---|
| Structure | duration, n_zones, n_cities, frac_zones, multi-city |
| States (zone-step shares) | exact zero, dead, held, interpolated, missing, flat (Δx = 0) |
| ρ dynamics | zone-mean ρ: mean, minimum and standard deviation during the item; mean over 30 min before (pre) and after (post); maximum over 60 min after (post-peak) |
| Calendar | start hour (raw, sin, cos), weekday, weekend |
| Adjacency | preceded by a fill run ending at s; followed by a fill run starting at e (any zone) |
| Episode context | number of items in the episode, episode contains a multi-zone fill, episode contains a multi-city dead item, episode duration |
| Detector | max and mean of the raw-band s^g, s^u (item cities) and s^v (item zones); one-hot of the top level; maximum score in each of W1–W4 and V4; maximum nowcast zone score |

**Learners** (eq. 12, D47). The soft-label loss L(φ) = −(1/n) Σ_i Σ_y q_i(y) log f_φ(y | φ_i) is implemented two ways:
- LightGBM multiclass on rows (φ_i, y) weighted by q_i(y), keeping rows with q_i(y) > 10⁻³;
- a 2-layer MLP trained directly on the soft cross-entropy.

All rule items and normal windows are predicted out of fold (GroupKFold, 5 folds, groups = episode). Detector-only candidates are predicted by the model trained on all labelled items.

**Fusion** (eq. 16): p_i(y) ∝ 𝟙[y ∈ 𝒴(i)] q_i(y)^β f_i(y)^{1−β}, with β = 0.5 until NB4. The end model abstains (p = q) on items whose label-model class has less than 3 items of training mass (D50). Detector-only candidates use a uniform q, so p follows f.

**Evaluation without ground truth:**
- out-of-fold agreement of arg max f with arg max q on rule items, overall and per class;
- the share of normal windows predicted N;
- soft cross-entropy;
- ablations: without detector features, without episode features, detector features only, the MLP;
- the list of rule items whose fused label differs from the label model.

## 8. Downstream test (`src/downstream.py`, NB5; D64–D66)

**Flagged zone-steps:** dead, hold or linear-fill states inside a qualifying rule zone run, in the southern system. Only these are changed by a cleaning strategy.

| Strategy | Flagged steps of artefact items (A1–A3) | Flagged steps of grid-event items (G*) |
|---|---|---|
| S0 raw | kept | kept |
| S1 naive | linear interpolation between the run's edges | linear interpolation |
| S2 typed | x̂ (eq. 1) × a ratio moving linearly from the left-edge to the right-edge x / x̂ (median of up to 3 valid neighbours within 6 h) | kept; event indicator = 1 (a forecaster feature); excluded from the training loss |
| S3 oracle | S2 with the injected truth inside injected spans (injected data only) | S2 with the injected truth |

- Items labelled N, clock and transfer items, and detector-only candidates are left as recorded. Timestamps are not re-aligned (D11).

**Forecasters:**
- **LightGBM:** a global direct model per horizon h ∈ {6, 144} steps (1 h, 1 day), on each zone's series divided by its median on normal pre-test steps.
  - Features at the origin t: lags 0, 1, 2, 5, 11; means over the last hour and the last day; the same time of day as the target 1, 2 and 7 days earlier; the event indicator now and over the last day; the target-time calendar; zone id.
  - L2 loss, 500 trees, learning rate 0.05, 63 leaves. Trained from day 35 to 31 Dec 2023.
- **Naive reference:** persistence x̂(t) = y(t − 6) at 1 h, seasonal naive x̂(t) = y(t − 144) at 1 day, on the cleaned series y.

**Scoring:**
- 1 Jan – 24 May 2024, on zone-steps that every strategy treats as normal: no flagged state, no rule item, no detector-only candidate and, on injected data, inside NB4's clean region and outside every injected span. The comparison is against the recorded values.
- Subsets: all scored steps; steps whose zone had a flagged state in the preceding 2 days.
- MAE and RMSE (A), MASE (eq. 19, per-zone seasonal-naive scale on normal training steps), sMAPE.

**Diebold–Mariano test (eq. 20):** on the per-time-step loss L_t = Σ_z |e_{t,z}| / s_z over the scored zones, d_t = L_t(first) − L_t(second), with a Newey–West variance and Bartlett lag = h.

**Outage statistics:** zone-hours and runs (≥ 3 steps) of
- every flagged dead state (naive, what S0 reports; S1 reports none);
- flagged dead states inside G-labelled items (typed, S2);
- the injected G1–G4 core spans (truth), inside NB4's scoring area.

## 9. Transfer test (`src/transfer.py`, NB6; D68–D70)

**Frozen from Morocco:**
- the rules (all thresholds) and the item and episode definitions;
- the label model: the parameters (π, θ) fitted on the Morocco votes, applied to the new items by one E-step (`DawidSkene.predict`);
- the detector architectures and training hyper-parameters;
- each detector's event formation (w, q, gap);
- the injected signatures and the metrics.

**Re-estimated from the new system's unlabelled series:**
- x̂ (eq. 1) and the robust-score scales;
- the predictor weights (trained on rule-clean steps, cross-fitted in two folds split at mid-year);
- γ, as the frozen percentile q of the system's own rule-negative zone-steps.

**Single-city system** (Tetouan):
- u ≡ 0, so the zone score is max(region, zone);
- the graph has only same-city edges;
- R1 and R7 cannot fire;
- G1 is not injected, and multi-city injected types become city-wide.

**Evaluation:** the guide's three outputs, on the whole year after the burn-in:
1. items and alarms on the real series (false alarms);
2. recall, precision and F1 on injected events (eq. 17);
3. the label distribution (attribution by the frozen label model's arg max, with majority vote as the baseline).
