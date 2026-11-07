# Grid event or data artefact? — Complete research guide & roadmap

Nov 6, 2026 · @farah

## Summary

Without any labels, the grid's own hierarchy can tell a real outage from a data-pipeline failure. Rule engine v0 already separates the 72 dead-feeder events and 220 frozen-value runs in this dataset into grid events and data artefacts.

The clearest case is 31 March 2024. From 09:10, every Boujdour and Foum El Oued zone holds a constant value for 2 h. At 11:10 they all switch to exact zeros for 43.8 h, while two Laâyoune zones hold a constant 73.598 A and 63.652 A for the same 43 h. No physical outage produces held and zeroed feeders side by side, so this is an acquisition failure.

**Core idea.** Every anomaly type shows up at a different level of the hierarchy (zone → city → region → data logger). Simultaneity, exact zeros versus a noise floor, held last values, restoration dynamics and conservation of current become labelling rules. A label model turns the rules into probabilistic labels, a multi-scale graph detector adds coverage, and the result is a typed event catalogue.

**Contributions**

1. A typology of anomalies in feeder telemetry with measurable signatures: 4 artefact types and 5 grid-event types.
2. A hierarchical weak-supervision method that needs no manual annotation, with calibrated probabilistic labels.
3. A detector that splits prediction residuals into region, city and zone parts, matching the typology levels.
4. A released, typed event catalogue for the UCI Morocco dataset (id 1158).
5. Evidence that type-aware cleaning improves load forecasts and outage statistics compared with naive cleaning.
6. A transfer test on the UCI Tetouan dataset.

Working title: *Grid event or data artefact? Hierarchical weak supervision for anomaly attribution in multi-city feeder telemetry.*

## Main problem and research questions

Utilities clean feeder telemetry blind. Zeros and flat lines get deleted or interpolated without anyone knowing whether they record a real outage or a data failure. A real outage is information that reliability statistics and forecasting models need. A data failure should be imputed. Getting this wrong damages both, and no labels exist to learn from.

**Problem statement.** Given multi-zone, multi-city feeder series with no annotations, assign every anomalous segment a calibrated probability over the anomaly types, and show that this attribution changes downstream results.

**Research questions**

1. **RQ1.** Can the physical and telemetry hierarchy alone produce reliable type labels without manual annotation?
2. **RQ2.** Which signatures separate grid events from artefacts? The candidates are simultaneity across cities, exact zeros versus a noise floor, held last values, restoration dynamics and conservation of current.
3. **RQ3.** Does learning on top of the rules (label model, end model and residual detector) beat rules alone and unsupervised state-of-the-art detectors?
4. **RQ4.** Does type-aware cleaning improve forecasting error and outage statistics compared with naive cleaning?
5. **RQ5.** Does the method transfer to another city's data without re-tuning?

**Working hypotheses**, all testable in this data:

- **H1.** Acquisition failures leave exact zeros or simultaneous held values across zones. A de-energised feeder reads a small noise floor.
- **H2.** Real outages restore with a ramp or a cold-load-pickup overshoot. Data gaps return straight to the expected value.
- **H3.** Load transfers conserve the city's total current. Faults and data gaps don't.

## Data inventory and verified quirks

The file holds 17 zone series in four sheets. The three southern cities share one 10-minute timeline, so they behave as one logger group. That shared timeline is what makes cross-city simultaneity testable. Source: [UCI dataset 1158](https://archive.ics.uci.edu/dataset/1158/high-resolution+load+dataset+from+smart+meters+across+various+cities+in+morocco).

| City | Zones | Step | Unit | Period | Rows | Exact zeros |
| --- | --- | --- | --- | --- | --- | --- |
| Laâyoune (L) | 5 | 10 min | A | 14 Sep 2022 – 24 May 2024 | 88,890 | 1,465 |
| Boujdour (B) | 3 | 10 min | A | 14 Sep 2022 – 24 May 2024 | 88,890 | 1,413 |
| Foum El Oued (F) | 7 | 10 min | A | 14 Sep 2022 – 24 May 2024 | 88,890 | 4,329 |
| Marrakech (M) | 2 | 30 min | kW | 9 Jan 2023 – 8 Jan 2024 | 17,501 | 101 |

**Quirks found by rule engine v0** (all reproducible with `rules_v0.py`):

| Quirk | Where | Evidence |
| --- | --- | --- |
| Hour repeated at 02:00 on 30 Oct 2022 and 29 Oct 2023 | L, B, F | 6 duplicate stamps each time. This is Europe's clock change; Morocco's clock doesn't move then. The daily profile shifts by +50 to +60 min (all 3 cities in 2022, 2 of 3 in 2023). |
| Hour missing at 02:00 on 23 Apr 2023 and 14 Apr 2024 | L, B, F | Matches Morocco's return to GMT+1 at 02:00 after Ramadan ([official date 2023](https://www.fnh.ma/article/actualites-marocaines/maroc-ramadan-heure-gmt)). |
| No repeated hour at Morocco's switch to GMT (19 Mar 2023, 10 Mar 2024, 03:00) | L, B, F | 18 regular rows. The repeated hour was probably overwritten, so one hour of data is silently lost (open question). |
| Midnight rows out of order | M | 366 backward jumps: each day's 00:00 row sits after 23:30, probably a 24:00 reading stamped with the same date. Plus 3 duplicates and 4 missing runs (25 steps, 19 of them at the start). |
| Dead-feeder events | all | 72 events of at least 30 min (x at most 5% of expected, at least one exact zero) |
| Frozen values | all | 220 runs of 6 or more identical non-zero values. The 11 runs longer than 24 h all fall inside two episodes (Jan 2023, Mar 2024). |
| Load transfer | B | 16 Dec 2023: zone 1 drops 31.9 A, zone 2 gains 33.0 A, conservation index 0.07 |
| Structural decline | F | Quarterly mean falls 40–50% from 2022 to 2024. The midday/evening ratio rises from 0.88 to 1.03, which doesn't fit rooftop PV. |
| Metadata errors | UCI page | Says 5 instances and 5 features. There are about 284,000 rows. |

Two cautions. Marrakech's expected-value baseline is unreliable for its first 14 days, because there's no history yet. Boujdour reads in whole amperes during frozen periods (77.000, 12.000), which hints at a different encoding in the telemetry path.

## Corrections to the proposed plan

The plan's structure holds: typology, weak supervision, multi-scale graph detector, injection, downstream test, Tetouan. Running it against the real data showed 13 places where it would mislabel events or get through review with avoidable weaknesses.

| # | Plan item | Problem found | Fix in this guide |
| --- | --- | --- | --- |
| 1 | y1 requires *all cities, all zones* at exact zero | Marrakech is a separate system and period, and never goes all-zero. On 31 Mar 2024, 2 Laâyoune zones were frozen rather than zeroed, so the rule misses the clearest gap in the data. | At least 2 cities of the shared 10-min group, starting within 10 min, each zone dead **or frozen** (R1, R4) |
| 2 | Restoration ratio x after / x before | Confounded by time of day: the 28 Jan 2023 event starts at 21:10 (evening peak) and ends at 10:50 (morning) | Ratio to the expected value for the same time slot (eq. 3) |
| 3 | Outages = exact zeros | De-energised feeders often read a noise floor. Several single-zone outages are only 12–51% exact zeros. | Dead state = x at most 5% of expected. The exact-zero share becomes a discriminating feature (eq. 4–5). |
| 4 | Typology has no "held value" class | The two largest artefacts in the data are simultaneous last-value holds across zones (Jan 2023: 1.5–2.8 days) | New class A2 plus rules R2 and R3 |
| 5 | y3 single-zone = fault or sensor | 57 of 68 single-zone events start between 06:00 and 11:00, mostly at weekends: a maintenance window | Split into G3 unplanned feeder outage and G4 planned work (R10) |
| 6 | y6 = European clock change only | The data shows both Europe's October change and Morocco's April change | A4 covers both calendars, plus a profile-alignment test (eq. 9) |
| 7 | Residual at scale j uses the raw series minus the scale-j prediction | Mixes scales: the raw value is compared with one band | Residual on the band itself: the wavelet coefficient at level j minus its prediction (eq. 13) |
| 8 | Fusion p ∝ p\_rules · exp(γ s) | The term scales every anomaly class equally, so the detector can never change which type wins, and it's undefined when all rules abstain | Two stages: the detector gives anomaly-ness, the end model gives type, combined as a product of experts (eq. 16) |
| 9 | ΔMAPE as headline metric | MAPE explodes near zero (Boujdour zone 2 is about 15 A, and dead states exist) | MAE, RMSE, MASE, sMAPE, plus a Diebold–Mariano test |
| 10 | Snorkel label model | Extra dependency and version churn on Colab | Dawid–Skene EM in about 40 lines of numpy (eq. 10–12). Snorkel stays as a baseline. |
| 11 | Injection of y1 into all cities, contamination up to 12% | Same over-strict signature as #1. Observed anomalies cover about 3% of time, so 12% is unrealistic. | Inject observed signatures (hold-then-zero, noise floor, ramp) at 1%, 3% and 7% |
| 12 | Load transfer injected as ±δ for a window | Real transfers are persistent level shifts lasting weeks | Sustained step with a conserved total (κ near 0) |
| 13 | Tetouan as a detection test | Tetouan has no anomaly labels, so it can't measure recall on its own | Use it for false-alarm rate on normal data plus recall on injected events |

## Anomaly typology

There are nine types plus normal. They split into four data artefacts (A), which should be imputed, and five grid events (G), which should be kept and flagged. Each type has a signature that can be measured at a specific level of the hierarchy. Compound events are common: both of the largest episodes are an A2 hold followed by an A1 zero fill.

| Code | Type | Level | Measurable signature | Observed example |
| --- | --- | --- | --- | --- |
| A1 | Zero-fill gap | Logger | At least 2 cities start within 10 min, exact-zero share ≥ 0.95, restoration ratio about 1 with no ramp | 31 Mar 2024 11:10, 43.8 h (B, F, L zones 3–5) |
| A2 | Simultaneous hold | Logger | At least 2 zones freeze at their last value at the same time, for ≥ 6 steps | 26 Jan 2023 ≈ 02:00: all L zones (1.5 d), all B zones (2.8 d) |
| A3 | Stuck sensor | Zone | One zone constant for ≥ 6 steps while its neighbours vary | 81 short runs (1–2 h) |
| A4 | Clock error | Logger | Repeated or missing hour on a clock-change date, daily profile shifted by about 60 min | 30 Oct 2022, 23 Apr 2023, 29 Oct 2023, 14 Apr 2024 |
| G1 | Regional outage | Region | At least 2 cities dead, noise floor or cold-load pickup, no holds | Candidate: 16 Jul 2023 14:50, B and F, 16.2 h, overshoot 1.38 |
| G2 | Substation or city outage | City | ≥ 90% of a city's zones dead while other cities stay normal | 1 event, 0.8 h |
| G3 | Unplanned feeder outage | Zone | One zone dead at any hour, often reading a noise floor | 17 events, e.g. F zone 4 from 29 Oct 2022, 108 h |
| G4 | Planned work | Zone | One zone dead, starting 06:00–11:00, lasting ≤ 6 h | 51 candidate events |
| G5 | Load transfer | City | Two zones show opposite, sustained level shifts with a conserved total (κ ≤ 0.3) | B, 16 Dec 2023: zone 1 → zone 2, about 32 A |
| N | Normal | — | Every rule abstains and the detector score stays low | Includes Ramadan, Eid and weekend behaviour (hard negatives) |

A structural change, such as F's 40–50% decline, is a level shift without conservation. It gets its own flag (S) but isn't scored as an anomaly type, because one example can't be validated.

## Notation and preprocessing equations

Every rule and feature below is computed from nine quantities, all relative to an expected value. That makes amperes and kilowatts comparable and removes the time-of-day confound.

**Notation.** Cities c ∈ {L, B, F, M}. Zone z of city c has series x\_t^{c,z} on a regular grid with step Δ (10 or 30 min) and P steps per day (144 or 48). Duplicate stamps are averaged and flagged. Missing stamps become NaN and are flagged.

**(1) Expected value**: the median of the same time slot over the previous K = 14 days, zeros excluded.

```latex
\hat{x}_t^{c,z} = \operatorname{median}\left\{ x_{t-kP}^{c,z} : k = 1,\dots,K,\; x_{t-kP}^{c,z} > 0 \right\}
```

**(2) Relative level**, unit-free:

```latex
\rho_t^{c,z} = x_t^{c,z} / \hat{x}_t^{c,z}
```

**(3) Restoration ratio and overshoot** of an event E ending at t\_e, with W+ the first 30 min after the end:

```latex
r_E = \frac{\sum_{t \in W^{+}} \sum_{z \in E} x_t^{c,z}}{\sum_{t \in W^{+}} \sum_{z \in E} \hat{x}_t^{c,z}}, \qquad \pi_E = \max_{t_e \le t < t_e + 60\,\text{min}} \frac{\sum_{z \in E} x_t^{c,z}}{\sum_{z \in E} \hat{x}_t^{c,z}}
```

Ramp time τ\_E is the delay until that ratio first reaches 0.9.

**(4) Dead state**, with ε = 0.05:

```latex
d_t^{c,z} = \mathbb{1}\left[ x_t^{c,z} = 0 \;\lor\; \rho_t^{c,z} \le \varepsilon \right]
```

**(5) Exact-zero share** of a dead run E:

```latex
\eta_E = \frac{1}{|E|} \sum_{t \in E} \mathbb{1}\left[ x_t = 0 \right]
```

**(6) Hold indicator**: a run of h ≥ 6 identical non-zero values is a hold.

```latex
h_t^{c,z} = \mathbb{1}\left[ x_t^{c,z} = x_{t-1}^{c,z} \neq 0 \right]
```

**(7) Simultaneity** of an event whose zone runs start at s\_{c,z}, with tolerance τ = 10 min:

```latex
S_E = \left| \left\{ c : \exists z,\; |s_{c,z} - s_E| \le \tau \right\} \right|, \qquad s_E = \min_{c,z} s_{c,z}
```

**(8) Conservation index** at day d, where Δ\_z is the change in the 14-day median of daily means:

```latex
\Delta_z(d) = \operatorname{med}_{[d,\,d+13]} \bar{x}^{z} - \operatorname{med}_{[d-14,\,d-1]} \bar{x}^{z}, \qquad \kappa(d) = \frac{\left| \sum_z \Delta_z(d) \right|}{\max_z \left| \Delta_z(d) \right|}
```

κ near 0 means current moved between zones. κ near 1 means load appeared or vanished.

**(9) Clock offset** at a candidate date D, with p the mean daily profile over 7 days before and after:

```latex
\delta^{*}(D) = \arg\max_{\delta \in [-120,\,120]\,\text{min}} \operatorname{corr}\left( p_{\text{pre}},\; \operatorname{shift}_{\delta}(p_{\text{post}}) \right)
```

This is reliable on dates with stable behaviour, such as October. It's confounded at the start and end of Ramadan, when people's routines change at the same time as the clock.

**Normalisation for learning.** Models use ρ or a robust z-score ((x − median) / MAD per zone and season), never raw amperes or kilowatts.

## Labelling rules

There are 18 rules. Each votes for one type or abstains, and the unit voted on is an event, not a timestamp. Rules R1–R4 target artefacts, R5–R11 and R16 target grid events, R12–R15 cover single zones and clocks, and R17–R18 bring in evidence from outside the dataset. Rules are allowed to conflict; resolving conflicts is the label model's job. The thresholds are starting values, and each one gets a sensitivity sweep (Risks section).

| Rule | Votes | Condition (symbols from eq. 1–9) | Default parameters |
| --- | --- | --- | --- |
| R1 multi-city zero | A1 | S\_E ≥ 2 and η\_E ≥ 0.95 and \|r\_E − 1\| ≤ 0.2 and τ\_E ≤ 10 min | τ = 10 min |
| R2 simultaneous hold | A2 | ≥ 2 zones with hold runs ≥ 6 steps, starts within τ | 6 steps, τ = 10 min |
| R3 hold → zero | A1 | A hold run ends at the exact timestamp a zero run starts in the same zone | exact match |
| R4 mixed hold/zero | A1 | Within one event, some zones are held while others are dead. A grid can't do this. | — |
| R5 cold-load pickup | G (any) | π\_E ≥ 1.15 | 60 min window |
| R6 noise floor | G (any) | η\_E < 0.9: the dead state isn't exact zeros | 0.9 |
| R7 regional outage | G1 | S\_E ≥ 2 and not R2/R3/R4 and (R5 or R6 or τ\_E ≥ 30 min) | — |
| R8 city outage | G2 | ≥ 90% of one city's zones dead while every other city stays alive (ρ > 0.5) | 0.9, 0.5 |
| R9 single zone | G3 | Exactly one zone dead, any time | — |
| R10 maintenance window | G4 | R9 and start 06:00–11:00 local and duration ≤ 6 h | 06–11 h, 6 h |
| R11 long single-zone | G3 | R9 and duration > 24 h (feeder out of service) | 24 h |
| R12 single-zone stuck | A3 | One zone holds for ≥ 6 steps while its city's other zones vary | 6 steps |
| R13 duplicate stamps | A4 | Repeated timestamps | — |
| R14 missing hour | A4 | Missing stamps on a clock-change date (Europe: last Sunday of Mar and Oct, 02:00; Morocco: Ramadan dates) | calendar |
| R15 profile shift | A4 | \|δ\*(D)\| ≥ 50 min on a candidate date | 50 min |
| R16 conserved transfer | G5 | Δ\_up > 0.25 of level and Δ\_down < −0.25 of level and κ ≤ 0.3 | 0.25, 0.3 |
| R17 grid milestone | G (any) | Event within ± 3 days of a published ONEE grid works date | ± 3 days |
| R18 news record | G1/G2 | A press or ONEE report of an outage in that city on that date | manual lookup |

Three rules in formal form:

```latex
\lambda_{\mathrm{R1}}(E) = \begin{cases} \mathrm{A1} & \text{if } S_E \ge 2 \,\wedge\, \eta_E \ge 0.95 \,\wedge\, |r_E - 1| \le 0.2 \,\wedge\, \tau_E \le 10\,\text{min} \\ \varnothing & \text{otherwise} \end{cases}
```

```latex
\lambda_{\mathrm{R4}}(E) = \mathrm{A1} \;\text{ if }\; \exists\, z_1, z_2 \in E,\; t \in E :\; d_t^{z_1} = 1 \,\wedge\, h_t^{z_2} = 1, \quad \varnothing \text{ otherwise}
```

```latex
\lambda_{\mathrm{R16}}(d) = \mathrm{G5} \;\text{ if }\; \Delta_{\uparrow}(d) > 0.25\,\bar{x}^{\uparrow} \,\wedge\, \Delta_{\downarrow}(d) < -0.25\,\bar{x}^{\downarrow} \,\wedge\, \kappa(d) \le 0.3, \quad \varnothing \text{ otherwise}
```

R17 and R18 are kept separate in evaluation. The model is scored both with and without them, so external evidence never leaks into the test of the data-only method.

**What v0 implements today:** R1, R2 (as hold runs), R7, R8, R9, R10, R13, R14 and R16, plus the features that R3–R6, R11, R12 and R15 need. The remaining rules are about 10 lines each.

## Label model and end model

A Dawid–Skene label model learns how accurate each rule is and turns the votes into a soft label q\_i(y) for each event i. An end model trained on those soft labels then covers events that no rule fires on. This two-step design is what separates the method from a hand-tuned rule engine.

**Items.** The items are candidate events: dead runs, hold runs, clock-change dates and transfer days, plus an equal number of sampled windows where every rule abstains (the N class). Rule r gives a vote λ\_r(i) ∈ Y ∪ {∅}.

**(10) Generative model.** Each rule has a confusion matrix θ\_r(y, l) = P(λ\_r = l | true type y), and π\_y is the class prior. The posterior for item i is:

```latex
q_i(y) = \frac{\pi_y \prod_{r:\,\lambda_r(i) \neq \varnothing} \theta_r\big(y, \lambda_r(i)\big)}{\sum_{y'} \pi_{y'} \prod_{r:\,\lambda_r(i) \neq \varnothing} \theta_r\big(y', \lambda_r(i)\big)}
```

**(11) M-step** with Dirichlet smoothing α = 1:

```latex
\pi_y = \frac{1}{n} \sum_i q_i(y), \qquad \theta_r(y, l) = \frac{\alpha + \sum_i q_i(y)\, \mathbb{1}[\lambda_r(i) = l]}{\alpha |Y| + \sum_i q_i(y)\, \mathbb{1}[\lambda_r(i) \neq \varnothing]}
```

Initialise θ with 0.7 on the diagonal, iterate until the change in log-likelihood is below 1e-6, and run 20 random restarts. The model is identifiable because most items get several votes: R2 and R4 co-fire on both large episodes.

**(12) End model.** A classifier f\_φ is trained on event features φ\_i with a noise-aware cross-entropy:

```latex
\mathcal{L}(\phi) = -\frac{1}{n} \sum_i \sum_{y \in Y} q_i(y) \log f_\phi(y \mid \phi_i)
```

**The features φ\_i** are duration, S\_E, number and share of zones, η\_E, r\_E, π\_E, τ\_E, pre-event ρ, start hour, weekday, hold share, κ and δ\*, plus the detector's region, city and zone residual scores (next section). The detector features are what let the end model generalise beyond the rules.

**Model choice.** LightGBM with soft targets (expanded into one row per class, weighted by q) is the fast, strong option. A 2-layer MLP is the comparison. Calibrate with temperature scaling on the synthetic validation split.

**Abstain handling.** Items with no votes take the prior as q. The end model learns them from features, which is how coverage grows.

## Detector: multi-scale graph model, scores and fusion

The detector predicts each zone from its own history and from the other zones at the same moment, then splits the residual into region, city and zone parts. This idea carries the paper. An artefact on the logger moves the region part, a substation outage moves the city part, and a feeder fault moves only the zone part, so the residual hierarchy mirrors the typology.

**Input.** Relative level ρ (eq. 2) for the 15 southern zones as one graph. Marrakech is a separate 2-node graph at 30 min. A mask M\_t = 1 wherever rules flagged a dead, held or clock-error step: those steps are excluded from the training loss but still scored.

**Graph.** Nodes are zones. Zones in the same city are fully connected. Cross-city edges are learned: GDN-style node embeddings, with the top-k = 4 neighbours chosen by cosine similarity.

**(13) Multi-scale nowcast.** A MODWT (LA8, J = 4: detail bands covering periods of 20 min to about 5 h at 10-min resolution, plus a smooth part) splits ρ into bands D\_j and A\_J. At each band, a temporal convolutional network (TCN) with graph attention predicts zone z from the window W of its own past plus the *current* values of its neighbours (leave-one-zone-out):

```latex
\hat{D}_{j,t}^{z} = f_{\theta_j}\!\left( D_{j,\,t-W:t-1}^{z},\; \{ D_{j,t}^{z'} \}_{z' \in \mathcal{N}(z)} \right), \qquad e_{j,t}^{z} = D_{j,t}^{z} - \hat{D}_{j,t}^{z}
```

The fused residual is e\_t^z = Σ\_j α\_j e\_{j,t}^z, with α = softmax(w), learned on the synthetic validation split. The plan used ‖x − x̂^j‖, which compares the raw value with a single band; this compares each band with its own prediction.

**Training loss:** masked Huber, ℒ = Σ\_t Σ\_z (1 − M\_t^z) Huber(e\_t^z).

**(14) Residual hierarchy.** For city c with zones Z\_c, and the southern region R:

```latex
g_t = \operatorname{med}_{z \in R}\, e_t^{z}, \qquad u_t^{c} = \operatorname{med}_{z \in Z_c}\, e_t^{z} - g_t, \qquad v_t^{c,z} = e_t^{z} - g_t - u_t^{c}
```

**(15) Level scores**: a robust z-score per level, computed over a rolling 28-day window:

```latex
s_t^{\ell} = \frac{|\epsilon_t^{\ell}| - \operatorname{med}(|\epsilon^{\ell}|)}{1.4826\, \operatorname{MAD}(|\epsilon^{\ell}|) + 10^{-6}}, \qquad \epsilon^{\ell} \in \{ g,\; u^{c},\; v^{c,z} \}
```

An event's detector features are the maximum and mean of s^g, s^u and s^v over the event. A step is anomalous if max\_ℓ s\_t^ℓ > γ, with γ set at the 99.5th percentile of rule-negative data.

**(16) Fusion** as a product of experts, replacing the plan's exp(γ s) term:

```latex
p(y \mid E) \;\propto\; q_E(y)^{\beta} \; f_\phi(y \mid \phi_E)^{1-\beta}, \qquad \beta \in [0,1] \text{ tuned on synthetic validation}
```

The label model q brings rule evidence, and the end model f brings feature and residual evidence. Both are full distributions over types, so the detector can change which type wins. When every rule abstains, q falls back to the prior and the end model decides.

**Cheaper fallback.** If the TCN-GAT doesn't reach good residuals within a week of tuning, use LightGBM nowcasts with neighbour-zone and calendar features. Eq. 14–16 don't change, because the decomposition doesn't depend on which predictor produced the residual.

## Architecture

Two branches run in parallel and meet at the end model. The rules give typed but sparse evidence, and the graph nowcast gives dense but untyped evidence.

&#91;embedded content: framework · two branches meet at the end model\]

Rule flags mask the nowcast's training loss, so it learns normal behaviour only. The label model's soft labels become the end model's training targets, and the residual level scores become its features.

## Synthetic injection protocol

Every injected anomaly copies a signature actually seen in this data, so the benchmark tests realistic cases rather than textbook spikes. Injection goes only into rule-negative windows, at 1%, 3% and 7% of time (the observed rate is about 3%), with 10 seeds. Each type is injected alone and in mixtures.

| Type | Injection procedure | Parameters (sampled) | Signature copied from |
| --- | --- | --- | --- |
| A1 zero fill | All zones of 2–3 southern cities set to exact 0, starting within one step of each other. Return directly to x̂ × U(0.9, 1.1). | 30 min – 48 h | 31 Mar 2024 |
| A2 hold | 2 or more zones frozen at their last value, optionally followed by A1 at the hold's end | 1 h – 3 d | 26–28 Jan 2023 |
| A3 stuck | One zone frozen at its last value | 1 – 6 h | 81 short runs |
| A4 clock | Duplicate or delete one hour at a clock-change date, and shift the following stamps by ±60 min | European and Moroccan dates | Oct 2022, Apr 2023 |
| G1 regional | 2 cities set to a noise floor ρ \~ U(0, 0.03) with additive noise. Restore with a ramp of 20–90 min and an overshoot factor ω \~ U(1.1, 1.5) that decays over 1–2 h. | 1 – 18 h | 16 Jul 2023 |
| G2 city | All zones of one city as in G1, other cities untouched | 20 min – 6 h | — |
| G3 feeder | One zone at a noise floor, any hour | 1 h – 5 d | F zone 4, Oct 2022 |
| G4 planned | One zone at a noise floor, starting 06:00–11:00, mostly at weekends | 1 – 6 h | 51 candidates |
| G5 transfer | Sustained step: +δ on zone i and −δ on zone j of the same city for ≥ 14 days | δ = 0.15–0.40 × mean | B, Dec 2023 |

**Hard negatives.** Windows that must not be flagged: Ramadan weeks, Eid days, national holidays, heat waves and weekends. They measure false alarms caused by ordinary behaviour.

**Splits.** Inject into Sep 2022 – Jun 2023 for training and validation, and Jul 2023 – May 2024 for testing. The test seeds are never used for tuning thresholds, β or α.

## Metrics

The headline results are event-level detection F1, macro-F1 for type attribution, and calibration error. Point-adjusted F1 is reported only for comparison with older papers, because it is known to inflate weak detectors ([Kim et al., AAAI 2022](https://arxiv.org/abs/2109.05257)).

| Question | Metric | Level | Notes |
| --- | --- | --- | --- |
| Is the anomaly found? | Event-wise precision, recall, F1 (eq. 17) | Event | A detection counts if it overlaps the true event by at least one step |
| Is the score ranking good? | AUC-PR and VUS-PR | Time step | VUS-PR is robust to boundary lag ([Paparrizos et al., VLDB 2022](https://www.vldb.org/pvldb/vol15/p2774-paparrizos.pdf)) |
| Are the boundaries right? | Median absolute start and end error | Event | In minutes |
| Is the type right? | Macro-F1, per-class F1, confusion matrix, balanced accuracy | Event | The headline attribution result |
| Are the probabilities honest? | Brier score, ECE (eq. 18) | Event | Matters because the catalogue is released with confidences |
| Are the rules good? | Coverage, overlap, conflict, learned accuracy per rule | Rule | Standard weak-supervision diagnostics |
| Does it match reality? | Agreement with ONEE and press records, precision@k for G events | Event | External validation |
| Does cleaning matter? | MAE, RMSE, MASE, sMAPE, and Δ between strategies with a DM test | Forecast | Next section |
| Are outage statistics right? | Outage-hours error and outage-count error versus truth | Zone | A SAIDI/SAIFI-style check |

**(17) Event-wise F1.** With true events 𝓔 and predicted events 𝓔̂:

```latex
P = \frac{|\{\hat{E} \in \hat{\mathcal{E}} : \exists E \in \mathcal{E},\, \hat{E} \cap E \neq \varnothing\}|}{|\hat{\mathcal{E}}|}, \quad R = \frac{|\{E \in \mathcal{E} : \exists \hat{E} \in \hat{\mathcal{E}},\, \hat{E} \cap E \neq \varnothing\}|}{|\mathcal{E}|}, \quad F_1 = \frac{2PR}{P+R}
```

**(18) Expected calibration error** over M = 10 confidence bins B\_m:

```latex
\mathrm{ECE} = \sum_{m=1}^{M} \frac{|B_m|}{n} \left| \operatorname{acc}(B_m) - \operatorname{conf}(B_m) \right|
```

**(19) MASE** with a seasonal-naive scale (lag P, one day), safe when values are near zero:

```latex
\mathrm{MASE} = \frac{\frac{1}{h} \sum_{t=T+1}^{T+h} |x_t - \hat{x}_t|}{\frac{1}{T-P} \sum_{t=P+1}^{T} |x_t - x_{t-P}|}
```

**Reporting.** Mean ± standard deviation over 10 seeds, with paired Wilcoxon tests against the best baseline. On real data there are only about 10 large events, so report counts and case studies rather than percentages.

## Downstream forecasting evaluation

The downstream test shows that attribution matters. The same forecaster is trained on four cleaned versions of the data, and two things are measured: forecast error on a clean held-out period, and how much real outage time each cleaning strategy wrongly erases.

| Strategy | Artefacts (A1–A4) | Grid events (G1–G5) | Expected effect |
| --- | --- | --- | --- |
| S0 raw | kept | kept | Errors from zeros and frozen values |
| S1 naive | All zeros and flat runs interpolated | Interpolated as well | Real outages erased, so outage statistics are understated |
| S2 typed (ours) | Imputed (A1–A3); A4 stamps re-aligned | Kept, with an event indicator fed to the model and excluded from the loss | Best error and correct outage statistics |
| S3 oracle | True types (synthetic runs only) | True types | Upper bound |

**Imputation for artefacts.** Use x̂ from eq. 1, scaled so the series joins smoothly at both edges of the gap. A stronger option, and an ablation, is the graph nowcast from eq. 13.

**Forecasters.** LightGBM with lags and calendar features (Ramadan flag, holidays, weekday) as the main model, because it's fast and strong. PatchTST or N-BEATS as the deep model, to show the effect doesn't depend on the architecture.

**Horizons.** 1 h ahead (6 steps) and day ahead (144 steps), with a rolling origin.

**Test period.** 1 Jan – 24 May 2024, scored only on steps that every strategy treats as normal, so the comparison is fair.

**(20) Diebold–Mariano test** on the loss differential between S1 and S2, with a HAC variance estimate σ̂²:

```latex
d_t = L\big(e_t^{S1}\big) - L\big(e_t^{S2}\big), \qquad \mathrm{DM} = \frac{\bar{d}}{\sqrt{\hat{\sigma}^2_{d} / n}} \;\sim\; \mathcal{N}(0,1)
```

**Outage-statistics check.** Total outage hours and outage counts per zone under S1 and S2, compared with the injected truth. This is a reliability-reporting argument that utilities and reviewers in power systems care about.

## Event catalogue

Rule engine v0 finds 13 large events in the real data. Six are artefacts with high confidence, two are ambiguous grid-or-artefact cases that need outside records, and the rest are feeder-level grid events. Types and confidences are provisional (rules only, before the label model). Every number comes from `zero_events.csv`, `stuck_runs.csv`, `transfers.csv` and `timestamp_audit.csv`, which are attached in the chat.

| ID | Start (stamp as recorded) | Duration | Cities and zones | Measured signature | Provisional type | Confidence | To validate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C13 | 2024-04-14 02:00 | 1 h missing | L, B, F | 6 stamps missing | A4 (Morocco back to GMT+1) | High | — |
| C12 | 2024-03-31 09:10 | 2 h hold, then 43.8 h | Hold: all B and F zones. Zero: B, F, L3–L5. L1 and L2 held for 43 h. | Hold → zero at 11:10 exactly, η = 1.00, r = 1.10, ramp 0 min, mixed hold and zero | A2 → A1 | High | Ask authors or ONEE about a logger outage. Note: same date as Europe's spring clock change. |
| C11 | 2023-12-16 (day) | sustained | B zone 1 → zone 2 | Δ = −31.9 A and +33.0 A, κ = 0.07 | G5 load transfer | High | ONEE feeder reconfiguration |
| C10 | 2023-10-29 02:00 | 1 h repeated | L, B, F | 6 duplicate stamps, profile shift +60 min (L +120) | A4 (European fall-back) | High | — |
| C09 | 2023-07-16 14:50 | 16.2 h | All B zones and all F zones. L normal. | η = 1.00, overshoot π = 1.38, r = 1.32, no holds | G1 regional outage (candidate) | Medium | 9 days before ONEE announced the southern grid's switch to 400 kV ([Medias24, 25 Jul 2023](https://medias24.com/2023/07/25/le-parc-eolien-de-boujdour-mis-en-exploitation/)). Look for an outage notice. |
| C08 | 2023-04-23 02:00 | 1 h missing | L, B, F | 6 stamps missing | A4 (Morocco back to GMT+1) | High | — |
| C07 | 2023-02-10 08:20 | 43.0 h | F zone 6 | η = 0.98, single zone, slow return (r = 0.06) | G3 feeder outage | Medium | — |
| C06 | 2023-01-28 21:10 | 13.7 h | All 15 southern zones | η = 1.00, r = 0.87, ramp 60 min, no overshoot. Follows C05 directly: the B hold ends at 21:10. | A1 (after A2), with a possible G1 component | Medium | Two days after Boujdour II was commissioned ([le360](https://fr.le360.ma/economie/onee-mise-en-service-du-nouveau-poste-de-transformation-electrique-boujdour-ii_AHMJ5DREIVGC3FPQZ7YLWV7CHQ/)). Ask ONEE whether there were switching works. |
| C05 | 2023-01-26 01:20–02:20 | L 1.5 d, F4 1.6 d, B 2.8 d | All L zones, all B zones, F zone 4 | Simultaneous holds of 216–402 identical values | A2 simultaneous hold | High | The commissioning date of Boujdour II |
| C04 | 2022-11-16 22:40 | 10.3 h | F zone 1 | η = 0.97, night start | G3 feeder outage | Medium | — |
| C03 | 2022-10-30 02:00 | 1 h repeated | L, B, F | 6 duplicate stamps, profile shift +50 to +60 min in all 3 cities | A4 (European fall-back) | High | — |
| C02 | 2022-10-29 20:40 | 108.2 h | F zone 4 | η = 1.00, single zone, comes back at 0.22 of expected | G3 (feeder out of service) or A3 | Low | Exact zeros for 4.5 days is unusual for a live CT |
| C01 | 2022-10-23 11:10 | 22.3 h | L zone 5 | η = 0.51, noise floor | G3 feeder outage | Medium | — |

**Aggregates, also in the CSV files.**

- **G4 planned-work candidates:** 51 events, 82.6 h in total, mostly at weekends and starting 06:00–11:00.
- **G3 unplanned single-zone outages:** 17 events, 274.8 h in total (C01, C02, C04 and C07 included).
- **A3 short stuck runs:** 81 runs of 1–2 h in the southern cities. Marrakech has 125 runs, but its whole-kilowatt readings repeat naturally, so it needs a longer threshold.
- **A4 in Marrakech:** 366 misordered midnight rows, 3 duplicates, 4 missing runs.

&#91;embedded content: events C05/C06 and C12 · hold and zero spans by zone group\]

Both large episodes are compound. Telemetry freezes first, then zeros appear at the exact timestamp the freeze ends. In 2024, frozen and zeroed zones overlap for 43 h, which is the strongest single piece of evidence for an acquisition failure.

## Baselines, ablations and generalisation

Baselines come in two groups. Detectors are compared on finding anomalies. Labelers are compared on assigning types, because no published detector outputs types. Every deep baseline gets the same window (1 day), training budget, early stopping and synthetic validation split.

| Group | Baseline | Why it's there | Colab package |
| --- | --- | --- | --- |
| Rules / statistics | Rule engine alone (v1) | Shows what learning adds | ours |
| Rules / statistics | STL plus Hampel / MAD filter | What utilities use | statsmodels |
| Rules / statistics | Isolation Forest, LOF on ρ and residuals | Classic unsupervised methods | scikit-learn |
| Rules / statistics | Matrix Profile discords | Strong, parameter-light | stumpy |
| Deep, reconstruction | USAD, TranAD, Anomaly Transformer | Common in published comparisons | authors' code |
| Deep, forecasting | TimesNet, N-BEATS residual detector | Strong general models | Time-Series-Library, darts |
| Graph | GDN, MTAD-GAT | Closest to our graph component | authors' code |
| Labelers | Majority vote, Snorkel LabelModel | Weak-supervision baselines | snorkel |
| Labelers | k-means / HDBSCAN on event features, mapped to types | Unsupervised typing | scikit-learn, hdbscan |

**Ablations**, each scored on detection F1, attribution macro-F1 and ECE:

1. Rules only, then plus label model, then plus end model, then plus detector features (the full method).
2. Remove each rule family in turn: simultaneity (R1, R7), hold (R2–R4), restoration (R5, R6), calendar (R10, R14), conservation (R16).
3. Without the residual hierarchy (eq. 14): one flat residual.
4. Single scale versus MODWT multi-scale; GAT versus no graph.
5. With and without the external rules R17 and R18.
6. Threshold sensitivity: ε ∈ {0.02, 0.05, 0.1}, hold length ∈ {4, 6, 12}, τ ∈ {0, 10, 20} min.

**Generalisation to Tetouan.** The UCI Tetouan dataset (power consumption of 3 zones in Tetouan, 2017, 10-minute steps, kW, with weather) is the transfer test. Rules are frozen as tuned on the Morocco data, and only the expected-value baseline is re-estimated. Report three things: the false-alarm rate on real data, recall on injected events, and the type distribution found. Tetouan has a single city, so city-level and regional rules can't fire there. That limit belongs in the paper.

**Extra robustness check.** Downsample the southern cities to 30 min and re-run the method. That tests whether it works at Marrakech's resolution, which is the only honest form of the "multi-resolution" idea.

## Figures and tables for the paper

The paper's argument rests on Fig. 3 and Fig. 4: two real events where held and zeroed zones sit side by side. Put them early, before any model. A reviewer who sees those two panels accepts the problem before reading the method.

| No. | Content | Form | Built in |
| --- | --- | --- | --- |
| Fig. 1 | The four cities on a map, plus coverage bars for each zone's series | Map + Gantt-style bars | NB0 |
| Fig. 2 | Typology: 9 types placed at their hierarchy level (logger, region, city, zone) | Diagram | Paper |
| Fig. 3 | 26–29 Jan 2023: 15 zone traces stacked, hold and zero spans shaded, Boujdour II date marked | Small multiples | NB1 |
| Fig. 4 | 31 Mar – 2 Apr 2024: held zones L1 and L2 next to zeroed zones | Small multiples | NB1 |
| Fig. 5 | Clock evidence: daily profile 7 days before and after 30 Oct 2022, with the correlation over shift δ | Two lines + curve | NB1 |
| Fig. 6 | Framework (architecture diagram in this guide) | Diagram | Paper |
| Fig. 7 | Rule coverage, overlap and conflict | Heatmap (rules × rules) | NB2 |
| Fig. 8 | Residual hierarchy g, u, v during C05/C06 versus a G3 event | Three-lane trace | NB3 |
| Fig. 9 | Detection PR curves: ours versus baselines, 3% contamination | Lines | NB4 |
| Fig. 10 | Attribution confusion matrix (synthetic test) | Heatmap | NB4 |
| Fig. 11 | Calibration (reliability diagram) | Line plus diagonal | NB4 |
| Fig. 12 | Downstream: MASE by strategy and horizon, and outage-hours error | Grouped bars | NB5 |
| Table 1 | Data inventory (Data inventory section) | Table | — |
| Table 2 | Typology and signatures | Table | — |
| Table 3 | Labelling rules | Table | — |
| Table 4 | Event catalogue, top 13 events (full list in supplementary material) | Table | NB1 |
| Table 5 | Detection results: F1, AUC-PR and VUS-PR at 1%, 3% and 7% | Table | NB4 |
| Table 6 | Attribution results: macro-F1, per-class F1, ECE | Table | NB4 |
| Table 7 | Ablations | Table | NB4 |
| Table 8 | Forecasting: MAE, RMSE, MASE, DM p-values | Table | NB5 |
| Table 9 | Tetouan transfer | Table | NB6 |

**Style.** Use one colour per class family: artefacts in one hue, grid events in another, normal in grey. Shade spans rather than marking points. Put time on the x-axis in local time, with the clock-correction step stated in the caption.

## Roadmap

The plan runs 14 weeks to submission. Each phase ends at a gate you can check, so a slip shows up early. The week counts are estimates for one person working part time on Colab.

&#91;embedded content: roadmap · 6 phases, 14 weeks, a gate at each phase end\]

**Colab notebooks**, one per phase, each reading the outputs of the one before it:

| Notebook | Builds | Inputs → outputs |
| --- | --- | --- |
| NB0\_audit | Regular grid, clock audit, duplicate flags | xlsx → `grid.parquet`, `timestamp_audit.csv` |
| NB1\_rules | All 18 rules, event features, catalogue, Fig. 3–5 | grid → `events.parquet`, `votes.parquet` |
| NB2\_labelmodel | Dawid–Skene EM, rule diagnostics, Fig. 7 | votes → `q.parquet` |
| NB3\_detector | MODWT, TCN-GAT nowcast, residual hierarchy, end model, fusion | grid, q → `scores.parquet`, `p_type.parquet` |
| NB4\_benchmark | Injection, baselines, metrics, ablations | grid → tables 5–7, Fig. 9–11 |
| NB5\_forecast | Strategies S0–S3, LightGBM + PatchTST, DM test | grid, p\_type → table 8, Fig. 12 |
| NB6\_tetouan | Transfer test with frozen rules | Tetouan csv → table 9 |
| NB7\_figures | Final figures in a consistent style | all → PDFs |

**This week**

- [ ] Run `rules_v0.py` on Colab and check C05, C06 and C12 by plotting the raw traces
- [ ] Email the dataset authors about the logger history in Jan 2023 and Mar 2024
- [ ] Search ONEE and regional press for outage notices on 16 Jul 2023 and 28 Jan 2023
- [ ] Add the rules not yet implemented (R3–R6, R11, R12, R15, R17)

## Risks and threats to validity

The biggest risk is circularity: rules make the labels, and the same rules are then scored against them. Three separate evaluations break the loop: injected events, outside records, and the downstream test. The rules are never scored against labels they produced.

| Risk | Why it matters | Mitigation |
| --- | --- | --- |
| No ground truth on real data | Reviewers will ask how you know C06 is an artefact | Release confidences, not hard labels. Validate against ONEE and press records (R17 and R18 kept apart). Email the dataset authors (address on the UCI page) and ask ONEE about C05, C06, C09 and C12. |
| Only about 13 large real events | Percentages on real data mean little | Real events as case studies. Statistical claims come from injection with 10 seeds. |
| Thresholds tuned by eye on the same data | Optimistic results | Sensitivity sweep (ablation 6). Thresholds frozen before the Tetouan test. |
| Timestamps in the wrong time zone | Planned-work rule R10 and the Ramadan analysis depend on local time | Estimate δ\* per period (eq. 9) and correct before applying R10. Report results both with and without the correction. |
| "It's just data cleaning" | Desk rejection risk | Lead with the typology, the residual hierarchy and the released benchmark. The downstream outage-hours result is the utility-facing argument. |
| Zone names and customer types unknown | Can't separate residential and industrial behaviour | State it as a limitation. The method doesn't need it. |
| The authors may know the logger history | Could confirm or overturn C05/C06 | Contact them early (week 2). Confirmation strengthens the paper either way. |
| Deep baselines are expensive on Colab | Time budget | 15 nodes × 88k steps is small. Use the T4 GPU, about 1 h per model. LightGBM fallback for the detector. |
| Marrakech is a different system | Cross-city rules don't apply to it | Treat it as a separate graph, report it separately, and use it as a second single-system transfer test. |

## References and sources

**Dataset and its papers**

- Bensalah, M. & Hair, A. (2025). [High-Resolution Load Dataset from Smart Meters Across Various Cities in Morocco](https://archive.ics.uci.edu/dataset/1158/high-resolution+load+dataset+from+smart+meters+across+various+cities+in+morocco). UCI ML Repository, DOI 10.24432/C5FC8R.
- [Zenodo record v2](https://zenodo.org/records/16423697). Links the OPSEARCH article (DOI 10.1007/s12597-025-00950-w) and the Data in Brief paper (DOI 10.1016/j.dib.2025.112067).

**External records used for validation**

- [le360, 1 Feb 2023](https://fr.le360.ma/economie/onee-mise-en-service-du-nouveau-poste-de-transformation-electrique-boujdour-ii_AHMJ5DREIVGC3FPQZ7YLWV7CHQ/): ONEE commissioned Boujdour II (400/225 kV) on 26 Jan 2023.
- [Medias24, 1 Feb 2023](https://medias24.com/2023/02/01/le-nouveau-poste-de-transformation-electrique-boujdour-ii-mis-en-service/): first wind-farm power from 31 Jan 2023.
- [Medias24, 25 Jul 2023](https://medias24.com/2023/07/25/le-parc-eolien-de-boujdour-mis-en-exploitation/): Boujdour wind farm in full commercial operation and the southern grid switched to 400 kV.
- [FNH, Mar 2023](https://www.fnh.ma/article/actualites-marocaines/maroc-ramadan-heure-gmt): Morocco to GMT on 19 Mar 2023 at 03:00, back to GMT+1 on 23 Apr 2023 at 02:00.

**Evaluation methodology (checked)**

- Kim, S. et al. (2022). [Towards a Rigorous Evaluation of Time-Series Anomaly Detection](https://ojs.aaai.org/index.php/AAAI/article/view/20680). AAAI 36(7), 7194–7201.
- Paparrizos, J. et al. (2022). [Volume Under the Surface: A New Accuracy Evaluation Measure for Time-Series Anomaly Detection](https://www.vldb.org/pvldb/vol15/p2774-paparrizos.pdf). PVLDB 15(11), 2774–2787.

**Method references.** These are cited from memory; check each one in your reference manager.

- Dawid, A. P. & Skene, A. M. (1979). Maximum likelihood estimation of observer error-rates using the EM algorithm. *Applied Statistics* 28(1).
- Ratner, A. et al. (2017). Snorkel: Rapid training data creation with weak supervision. *PVLDB* 11(3).
- Percival, D. B. & Walden, A. T. (2000). *Wavelet Methods for Time Series Analysis*. Cambridge University Press (MODWT).
- Deng, A. & Hooi, B. (2021). Graph neural network-based anomaly detection in multivariate time series (GDN). *AAAI*.
- Zhao, H. et al. (2020). Multivariate time-series anomaly detection via graph attention network (MTAD-GAT). *ICDM*.
- Audibert, J. et al. (2020). USAD: Unsupervised anomaly detection on multivariate time series. *KDD*.
- Tuli, S. et al. (2022). TranAD: Deep transformer networks for anomaly detection in multivariate time series. *PVLDB* 15(6).
- Xu, J. et al. (2022). Anomaly Transformer: Time series anomaly detection with association discrepancy. *ICLR*.
- Wu, H. et al. (2023). TimesNet: Temporal 2D-variation modeling for general time series analysis. *ICLR*.
- Diebold, F. X. & Mariano, R. S. (1995). Comparing predictive accuracy. *Journal of Business & Economic Statistics* 13(3).
- Hyndman, R. J. & Koehler, A. B. (2006). Another look at measures of forecast accuracy. *International Journal of Forecasting* 22(4) (MASE).
- Salam, A. & El Hibaoui, A. (2018). Comparison of machine learning algorithms for the power consumption prediction: case study of Tetouan city. *IRSEC* (the source of the Tetouan dataset).
