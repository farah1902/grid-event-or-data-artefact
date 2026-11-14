# Paper outline — Applied Energy (step 1 of the writing plan, 2026-11-13)

**Title (kept):** *Grid event or data artefact? Hierarchical weak supervision for anomaly attribution in multi-city feeder telemetry.* No "graph" in the title or the abstract claims (D67).

**Journal:** Applied Energy (author's decision, 2026-11-13). Format: LaTeX, Elsevier `elsarticle` class, in `paper/`.

**Journal requirements** (official guide for authors, "Writing and formatting" section, pasted by the author from the ScienceDirect page on 2026-11-13; the page blocks automated download):
- **Files:** .tex source (PDF is not a source file); double-column layout allowed for LaTeX; Elsevier LaTeX template encouraged; all editable sources supplied.
- **Title page:** concise title without abbreviations or formulae; given and family names; affiliations with lowercase superscript letters and full postal address including country; corresponding author with e-mail (published); present address as a superscript Arabic-numeral footnote if needed.
- **Abstract:** ≤ 250 words; purpose, procedures, main findings with statistical significance, principal conclusions, what is new; stands alone; no references (or author + year); non-standard abbreviations avoided or defined.
- **Keywords:** 1–7, in English; avoid multi-word keywords with "and" or "of"; abbreviations only if firmly established.
- **Highlights:** 3–5 bullets, ≤ 85 characters each including spaces; separate editable file with "highlights" in the file name; novel results and new methods.
- **Graphical abstract:** encouraged; separate file; ≥ 1328 px wide, longest side horizontal, readable at 13 cm width; TIFF, EPS, PDF or MS Office; generative-AI use must follow Elsevier's GenAI policy.
- **Math:** editable text, not images; simple formulae in line; solidus (X/Y) for small fractions; variables in italics; powers of e as exp; display equations numbered consecutively in the order they are referred to.
- **Tables:** editable text; cited in the text; numbered in order of appearance; caption with each table; notes below the body; **no vertical rules and no shading** (booktabs); **used sparingly and not duplicating results shown elsewhere** (so each main table must carry what its figure does not: statistics, other views, p-values).
- **Figures:** each a separate file named in a logical way (Figure_1, Figure_2, ...), cited and numbered in order of appearance; vector drawings as EPS or PDF with embedded fonts; bitmaps ≥ 300 dpi (single column ≥ 1063 px, full page ≥ 2244 px), bitmapped line drawings ≥ 1000 dpi; every figure has a caption (brief title + description, symbols explained); **no multiple images combined into one file** unless they are meant to be compared; colour accessible to colour-vision deficiency.
- **Still not seen in the pasted section:** total length limit, declarations (competing interests, CRediT, data availability, generative-AI statement), reference style. To be checked on the "Article structure / References / Declarations" parts of the guide.
- **Length: working budget 8,000 words of body text** (excluding references, captions and tables). Third-party sources disagree (8,000; 7,000–10,000; 12,000; an outdated 2015 author pack says 5,000); 8,000 is the commonly cited and the safer figure.

**Consequences for this paper:**
- the two real logger episodes stay **two separate figures** (Figs 4 and 5), not one composite file;
- figures are re-exported as PDF with TrueType fonts embedded (matplotlib `pdf.fonttype = 42`) and checked for size and legibility at print width in the figure step;
- tables use `booktabs`, and each main table adds information its figure does not show;
- the submission package will name files Figure_1 … Figure_12.

**Source rule for every sentence:** numbers come only from `docs/results_summary.md` (F/D numbers given per item). External references are added only after their metadata is fetched from Crossref or the publisher (DOI resolved) and the cited claim is checked against the paper; never from memory.

---

## The value of the work (the thread through every section)

Five claims, each with its evidence. The introduction states them; the results prove them in this order; the conclusion returns to them.

| # | Claim | Evidence | Where |
|---|---|---|---|
| V1 | **What the telemetry contains.** A public smart-meter dataset's apparent outages are mostly data-logger artefacts; straight-line fills are the commonest fill; restoration "ramps" are synthetic; counting every dead state overstates southern outage time **4.15×** (1,220.5 vs 294.0 zone-h) | F01, F05, F16, F51; Figs 4, 5 | §6.1 |
| V2 | **Label-free typing that works on sparse rules.** The standard Dawid–Skene model cannot use single-label rules (posterior = prior, F20) and is unstable (≤ 63 % restart agreement, F21); the constrained model is fully stable (100 %, F22) and gives calibrated probabilities (ECE 0.07–0.10) at macro-F1 0.90–0.94 | F20–F22, F46 | §4.5, §6.2, §6.5 |
| V3 | **A detector that extends the rules.** Best of eight detectors at 3 % and 7 % (p ≤ 0.02; F41); adding it to the rules raises recall at every rate (10/10 seeds) and F1 at every rate once each method's own real-data alarms are excluded (F44). Strict view and zone-strict view reported next to it | F41–F45 | §6.4 |
| V4 | **Practical impact for distribution operators.** Typed outage counting 1.26× the truth vs 1.88× naive, closer in **30/30** injected datasets (F59); typed cleaning gives the best forecasts after anomalies (real day-ahead MASE 1.061 vs 1.233 interpolation vs 1.501 raw; F53) | F51–F54, F59 | §6.6 |
| V5 | **It transfers.** Frozen method on another city (Tetouan): zero false rule items on a clean year; F1 0.945 / 0.919 / 0.890 at precision 0.98–1.00, above the rules alone at every rate (F55, F56) | F55–F58 | §6.7 |
| + | **Released resource:** typed, probabilistic catalogue of 404 events + code | D72 | Data availability |

Honesty items that protect the value (each stated where it belongs, never hidden): the strict 1 % F1 loss and zone-strict loss (F44); label model ≈ majority vote on accuracy (F46); the learned graph adds no detection skill (F42, ablation); A1 → G1 confusion (F47); single-city A1 limit (F58); no utility ground truth.

---

## Word budget (8,000 words of body text)

| Section | Words |
|---|---|
| 1 Introduction | 850 |
| 2 Related work | 850 |
| 3 Data, hierarchy and typology | 850 |
| 4 Method | 1,750 |
| 5 Experimental design | 750 |
| 6 Results | 2,000 |
| 7 Discussion | 700 |
| 8 Conclusions | 250 |
| **Total** | **8,000** |

Main paper: **12 figures, 9 tables, 27 equations**; the rest in the supplement. Captions, tables and references do not count towards the 8,000 words.

## Structure, with the place of every figure, table and equation

Paper numbering follows the order of first citation. Source files: `results/paper/figures/` and `results/paper/tables/`. "S" = supplementary.

### Front matter
- Title, authors (later), highlights (3–5, ≤ 85 characters; drafted last), graphical abstract (a simplified Fig 3 with the V1, V4, V5 numbers; drawn last), abstract (≤ 250 words; written last), keywords (proposed: weak supervision; anomaly attribution; feeder telemetry; data quality; outage statistics; load forecasting; distribution networks — count to be checked against the guide).

### 1 Introduction (no figures)
1.1 Motivation: feeder telemetry feeds reliability reporting and forecasting; anomalies are cleaned blind.
1.2 The problem: the same zero or flat line can be a real outage or a logger failure; deleting one or keeping the other biases outage statistics and forecasts.
1.3 Gap (each point backed by verified references): no labelled feeder-event data; detectors flag anomalies but do not say *what* they are; the electrical and logger hierarchy is not used as evidence; synthetic-benchmark limits.
1.4 Contributions (V1–V5 + catalogue).
1.5 Research questions RQ1–RQ5 and hypotheses H1–H3 (answered in §7.1, including H2's negative answer).
1.6 Organisation.

### 2 Related work (references verified one by one in the writing step)
2.1 Anomaly detection in load and smart-meter data (statistical, ML, deep).
2.2 Physical events vs data-quality faults: outage detection from metering data, sensor and acquisition faults, imputation and cleaning.
2.3 Weak supervision: Dawid–Skene, data programming / Snorkel, label models and end models.
2.4 Multivariate and graph-based time-series anomaly detection (temporal convolution, graph attention, learned graphs, wavelet multi-scale analysis).
2.5 Evaluating time-series anomaly detection (event-level metrics, point-adjust criticism, synthetic injection limits).
2.6 Positioning. **Table 1**: related approaches vs ours on: label-free, typed attribution (event vs artefact), hierarchy used as evidence, calibrated probabilities, downstream evaluation, transfer test.

### 3 Data, hierarchy and typology
3.1 Datasets. UCI 1158 Morocco (south: Laâyoune, Boujdour, Foum El Oued, 15 zones, one logger, 10 min, A; Marrakech, 2 zones, 30 min, kW) and UCI Tetouan (3 zones, 2017). Timestamps as recorded (D11). **Fig 1** (map + anomalous-state coverage; `fig1_map_coverage`). **Table 2** (inventory; `Table1_data_inventory`).
3.2 The telemetry hierarchy: logger → region → city → zone; what each level's evidence means.
3.3 Problem formulation: detection (events), attribution (probabilistic type), localisation (level), type-aware cleaning. **Eq. (1)** expected value x̂ (guide eq 1); **Eq. (2)** relative level ρ = x / x̂ (guide eq 2).
3.4 Typology: A1 zero-fill gap, A2 simultaneous fill (hold or linear), A3 single-zone fill, A4 clock error; G1 regional outage, G2 city outage, G3 unplanned feeder outage, G4 planned work, G5 load transfer; N normal. **Fig 2** (`fig2_typology`). **Table 3** (typology, signatures, levels, real-data counts; `Table2_typology`).
- *Changed from the first plan:* A3 is a single-zone fill, not a "stuck sensor"; no "S structural change" class (structural level changes are context, Fig S19).

### 4 Method
4.1 Overview. **Fig 3** (framework; `fig6_framework`).
4.2 Per-step states and signatures (methods §2–3). **Eq. (3)** dead state (guide eq 4, ε = 0.05, no exact-zero requirement, D15); **Eq. (4)** exact-zero share η (eq 5); **Eq. (5)** hold (eq 6); **Eq. (6)** straight-line fill (new signature, F01); **Eq. (7)** cross-city simultaneity (eq 7); **Eq. (8)** restoration measured after the fill ramp (eq 3 as implemented, D22); **Eq. (9)** conservation index κ (eq 8); **Eq. (10)** clock offset δ* (eq 9). Items and episodes.
4.3 Labelling rules: 19 rules in families. **Table 4** (rules: family, label, condition, coverage, learned precision; `Table3_rules`, compact; full version in the supplement).
4.4 Why the standard label model fails here. **Eq. (11)**: with single-label rules θ_r(y, l) = 1 and the posterior equals the prior (F20).
4.5 The constrained (one-coin) label model with abstention. **Eq. (12)** likelihood with feasibility and applicability; **Eq. (13)** one-coin parameterisation; **Eq. (14)** EM updates with Beta pseudo-counts.
4.6 Multi-scale hierarchical residual detector: predictor (TCN-GAT; the learned graph is evaluated as an ablation) and residual **Eq. (15)**; MODWT bands **Eq. (16)**; region / city / zone decomposition g, u, v **Eq. (17)** (guide eq 14); robust level score **Eq. (18)** (guide eq 15); event formation (smoothing w, percentile q, merge gap) **Eq. (19)**.
4.7 End model and fusion. **Eq. (20)** soft-label cross-entropy (guide eq 12); **Eq. (21)** fusion p ∝ q^β f^(1−β) on the feasible set (guide eq 16, corrected).
4.8 Type-aware cleaning S0–S3. **Eq. (22)** artefact imputation: x̂ scaled to join both edges.

### 5 Experimental design
5.1 Injection benchmark: observed signatures injected into clean zone-time (D54), types, rates 1 / 3 / 7 %, development seeds 100–104 for every choice, test seeds 0–9 untouched until the final run (D60, D63). Fig S10.
5.2 Methods compared: rules; main detector; its ablations (graph off, single scale, flat, raw residual, LightGBM predictor, NB3 event formation); hybrids; STL + MAD; LOF; Isolation Forest. Event formation tuned alike for every detector (D60).
5.3 Metrics: **Eq. (23)** event F1 (guide eq 17), zone-strict variant, step AUC-PR, onset error; **Eq. (24)** ECE (guide eq 18), macro-F1; **Eq. (25)** MASE (guide eq 19); **Eq. (26)** Diebold–Mariano statistic on summed scaled loss (guide eq 20, D66); **Eq. (27)** outage ratio and its distance |log ratio| (D76).
5.4 Statistics: mean ± sd over 10 seeds; paired Wilcoxon signed-rank tests.
5.5 Downstream protocol (D64–D66): strategies S0–S3, LightGBM direct forecaster + naive reference, test period 1 Jan – 24 May 2024, scoring area.
5.6 Transfer protocol (D68–D71): frozen / re-estimated / adapted, in text; the diagram opens §6.7.
5.7 Implementation and reproducibility (software versions, runtimes, seeds, repository).
- *Changed from the first plan:* baselines that were not run (Matrix Profile, USAD, TranAD, Anomaly Transformer, TimesNet, N-BEATS, GDN, MTAD-GAT, Snorkel, k-means, HDBSCAN) and metrics not computed (VUS-PR, balanced accuracy) are not listed as run; the reasons go to §7.3 (D-register). No temperature scaling (ECE reported as is). No external-validation rule (news records). No 30-min robustness test.

### 6 Results
6.1 What the telemetry contains (V1). **Fig 4** the January 2023 logger episode (`fig3_C05_C06_jan2023`); **Fig 5** the 31 Mar – 2 Apr 2024 compound episode (`fig4_C12_mar2024`); clock evidence δ* = −60 min in the text, figure in the supplement (`fig5_clock_2022-10-30`); key real-data events with final labels and episode sequences in the supplement (`Table4_key_events`). The July 2023 regional-outage candidate is most probably an acquisition failure (F03, confidence *strong*, not *solid*; Fig S1); synthetic restoration ramps (F05, F16); the 4.15× real-data overstatement (F51).
6.2 Weak supervision on the real data (V2): coverage and conflicts (Fig S-rules, `fig7_rule_diagnostics`), stability and parameter recovery (F21, F22), robustness (F24, F48), the released catalogue (404 entries).
6.3 The residual hierarchy on real data. **Fig 6** (`fig8_residual_hierarchy`): logger failures load the region part (g up to 218), a feeder outage only the zone part.
6.4 Detection on injected events (V3). **Fig 7** (`fig9_detection`); **Table 5** (`Table5_detection`: what Fig 7 does not show — precision, recall, the background-excluded and zone-strict views, Wilcoxon p against the rules); **Fig 8** ablations (`fig9b_ablations`, learned graph first).
6.5 Attribution (V2). **Fig 9** (`fig10_11_attribution`: confusion, reliability); **Table 6** (`Table6_attribution`: majority vote, label model, end model, fusion; macro-F1, ECE).
6.6 Downstream: outage statistics and forecasting (V4). **Fig 10** (`fig12_downstream`); **Table 7** (outage ratios on 30 datasets from `Table8_outage_all_datasets` + MASE after anomalies from `Table8_forecasting`, DM p-values).
6.7 Transfer to another city (V5). **Fig 11** transfer protocol (`fig14_transfer_protocol`); **Fig 12** Tetouan results (`fig13_tetouan`); **Table 8** (`Table9_tetouan_detection` + attribution with and without A1).

### 7 Discussion
7.1 Answers to RQ1–RQ5 and H1–H3. **Table 9** (question, answer, evidence).
7.2 What this means for distribution operators: reliability reporting, telemetry quality checks, forecasting pipelines.
7.3 Limitations and threats to validity: no utility-confirmed labels; few large real events; injection realism and circularity (signatures injected are the ones the rules know); A1 → G1 confusion; zone spill-over of the detector; threshold sensitivity (hold length, ε); timestamps as recorded; single-city transfer; baselines not run and why.

### 8 Conclusions and future work
Summary of V1–V5; future work: utility event records, more cities, online use.

### Declarations (wording to be checked against the guide)
Data availability (UCI 1158, UCI Tetouan, catalogue, code), CRediT, funding, competing interests, generative-AI statement (if the guide requires it).

### Supplementary material
A typology details and the key real-data events (Table S, `Table4_key_events`); clock evidence (Figs S); B full rules (Table S-rules, S1 parameters); C label-model derivations and recovery (S2, S3); D full catalogue (CSV); E all baselines and ablations (Table 7b–7f, S6); F sensitivity (S3, Table 7d); G injection parameters and signatures (Fig S10, S21); H reproducibility (versions, runtimes, seeds). Supplementary figures S1–S28 per `results/paper/MANIFEST.md`, plus the rule-diagnostics figure.

---

## Writing order (step by step, each step reviewed by the author before the next)

1. This outline (approve or change).
2. LaTeX skeleton in `paper/` (elsarticle, one file per section, figures linked from `results/paper/figures/`, `references.bib` filled only from verified metadata).
3. §3 Data, hierarchy and typology.
4. §4 Method.
5. §5 Experimental design.
6. §6 Results.
7. §7 Discussion.
8. §2 Related work (web research, every reference verified).
9. §1 Introduction.
10. §8 Conclusions, abstract, highlights, graphical abstract, declarations.
11. Supplementary material.
12. Final check: every number against `docs/results_summary.md`, every reference against its DOI, the guide's formal requirements.

Methods and results come first because they fix the exact claims; the introduction and abstract are written last so that they promise only what the results show.
