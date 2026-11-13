"""NB7: the paper's table set, the numbered figure set with draft captions (MANIFEST.md) and the released catalogue
(D72, D75). Tables are copied or assembled from stored results; no number is recomputed by a method."""
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
PAPER = RES / "paper"

# ---------------------------------------------------------------- the paper's figure numbering (D75)
MAIN_FIGURES = [
    ("Fig 1", "fig1_map_coverage", "Data. (a) The UCI 1158 sites: Laâyoune, Foum El Oued and Boujdour share one data logger (15 zones, 10 min, A); "
     "Marrakech is a separate 30-min kW system; the UCI Tetouan set (3 zones, 2017) is the transfer test. Coastline: Natural Earth 1:50m; no boundaries drawn. "
     "(b) Anomalous states per zone found by rule engine v1 (qualifying runs of holds, straight-line fills, exact zeros and noise floors; missing steps); "
     "dotted lines mark clock-change dates. Timestamps as recorded."),
    ("Fig 2", "fig2_typology", "Typology. Four data artefacts (A1–A4) and five grid events (G1–G5), each with a measurable signature at a level of the "
     "zone–city–region hierarchy and the rules that vote for it (schematic). Straight-line fills, a signature the original plan did not anticipate, are part of A2 and A3."),
    ("Fig 3", "fig3_C05_C06_jan2023", "The January 2023 logger episode (C05/C06): simultaneous holds and straight-line fills across all 15 southern zones, "
     "then a 15-zone zero fill. Final labels: A2 → A2 → A1."),
    ("Fig 4", "fig4_C12_mar2024", "31 March – 2 April 2024 (C12): L1 and L2 held for 43 h while the other zones are zero-filled. Final labels: A2 → A1 → A2 → G4."),
    ("Fig 5", "fig5_clock_2022-10-30", "Clock evidence at 30 October 2022: daily profiles before and after the date and the correlation as a function of the "
     "shift δ. δ* = −60 min in the three southern cities (stamped earlier after the date)."),
    ("Fig 6", "fig6_framework", "Framework. Per-step states and typed items feed 19 labelling rules and a constrained Dawid–Skene label model (weak supervision, "
     "no manual labels); a multi-scale residual detector finds anomalies no rule covers; an end model and fusion produce the typed, probabilistic catalogue, "
     "which is evaluated by injection (NB4), downstream (NB5) and transfer (NB6)."),
    ("Fig 7", "fig7_rule_diagnostics", "Rule diagnostics on the real data: coverage per rule and the rule × rule overlap and conflict matrices (rule engine v1)."),
    ("Fig 8", "fig8_residual_hierarchy", "Level scores (robust z, eq. 15) of the residual hierarchy. During the January 2023 logger zero fill the region part g "
     "reaches 218 (forecast residual) while a feeder outage (C02, F4) moves only the zone part v. The nowcast residual of the original plan (eq. 13) behaves the same."),
    ("Fig 9", "fig9_detection", "Detection on injected events (30 datasets, test period, mean ± sd over 10 seeds): event F1 (eq. 17) and step-wise AUC-PR of "
     "the full method, the rules, the main detector, its ablations, other predictors and the baselines, at 1, 3 and 7 % contamination."),
    ("Fig 10", "fig9b_ablations", "Ablations of the main detector: change in event F1 relative to the main detector (mean ± sd of per-seed differences; filled: "
     "Wilcoxon p < 0.05). The learned-graph ablation (shaded) leaves F1 equal or slightly higher; the multi-scale bands and the tuned event formation carry the gain."),
    ("Fig 11", "fig10_11_attribution", "Attribution on injected events (3 %, test period): (a) confusion of the injected type against the fused label; "
     "(b) reliability of the label model q, the end model f and the fusion p."),
    ("Fig 12", "fig12_downstream", "Downstream test: LightGBM forecast error (MASE) by cleaning strategy after anomalies, (a) real and (b) injected data, "
     "test period 1 Jan – 24 May 2024; (c) outage zone-hours relative to the injected truth, naive counting (S0) and typed counting (S2), "
     "on the 30 injected test datasets (points: seeds; markers: mean ± sd per rate and over all 30). Naive interpolation (S1) reports 0."),
    ("Fig 13", "fig14_transfer_protocol", "Transfer protocol: stage by stage, what is frozen from Morocco, what is re-estimated from Tetouan's unlabelled series, "
     "and what a single-city system changes, with the results. Every adaptation is listed in docs/transfer_protocol.md."),
    ("Fig 14", "fig13_tetouan", "Transfer to Tetouan without re-tuning: (a) event F1 of every method at 1, 3 and 7 %; (b) attribution confusion of the frozen "
     "label model at 3 %. City-wide zero gaps (A1) are read as city outages (G2), the single-city limit."),
]
SUPP_FIGURES = [
    ("Fig S1", "E1b_C09_stack", "16 July 2023 (C09): Boujdour and Foum El Oued zeros next to a linearly interpolated Laâyoune; the original plan's only G1 candidate is an artefact.", ""),
    ("Fig S2", "E10_C01_relabelled", "C01: zeros → a straight-line fill → zeros, not a noise-floor outage.", ""),
    ("Fig S3", "E12_label_model_rules", "Learned rule propensity a vs false-positive rate b and evidence log(a/b) (label model).", ""),
    ("Fig S4", "E14_key_event_posteriors", "Full posterior q(y) for the items of the key events.", ""),
    ("Fig S5", "E4_signatures", "Signatures of the 126 dead items (v1, restoration after the ramp), coloured by final label.", "regenerated in NB7 (v0 before)"),
    ("Fig S6", "E6_catalogue_timeline", "The typed catalogue on one timeline (final labels).", "regenerated in NB7 (v0 types before)"),
    ("Fig S7", "E18_detector_only_gallery", "Detector-only candidates: partial drops, surges, short system-wide disturbances (NB3 LightGBM detector).", "NB3 detector"),
    ("Fig S8", "E19_end_model", "End model on the real data: agreement with the label model, ablations, final labels of detector-only candidates.", "regenerated in NB7"),
    ("Fig S9", "E20_learned_graph", "The graph learned by the TCN-GAT (edges and mean attention).", ""),
    ("Fig S10", "E21_injected_signatures", "One injected event per type over the original series.", ""),
    ("Fig S11", "E22_tetouan_series", "UCI Tetouan 2017: daily means and one week.", "regenerated in NB7"),
    ("Fig S12", "E9_vote_matrix", "Rule votes on every multi-zone, clock and transfer item.", ""),
    ("Fig S13", "E11_short_simultaneous_freezes", "The daily short multi-zone freezes in Laâyoune until April 2023.", ""),
    ("Fig S14", "E13_label_confidence", "Label-model confidence per type and entropy per item kind.", ""),
    ("Fig S15", "E15_label_robustness", "Label changes when a rule family or a prior changes.", ""),
    ("Fig S16", "E16_predictor_example", "Out-of-sample prediction of ρ, one normal week (LightGBM).", ""),
    ("Fig S17", "E17_detector_only_candidates", "Detector-only candidates over time (NB3 LightGBM detector).", "NB3 detector"),
    ("Fig S18", "E2_C11_transfer", "Boujdour zone 1 → zone 2 load transfer (κ = 0.07).", ""),
    ("Fig S19", "E7_FoumElOued_structural", "Foum El Oued level decline and midday/evening ratio.", ""),
    ("Fig S20", "E8_Marrakech_timestamps", "Marrakech midnight rows out of order.", ""),
    ("Fig S21", "E1_C09_jul2023", "16–17 July 2023: city totals vs expected and restoration.", ""),
    ("Fig S22", "E3_single_zone_timing", "Single-zone events: start hour, weekday, duration.", "uses v0 events and types"),
    ("Fig S23", "E5_single_zone_gallery", "Single-zone outages C01, C02, C04, C07.", "C01 panel superseded by Fig S2"),
] + [(f"Fig S{24 + k}", f"figS_clock_{d}", f"Clock evidence at {d}.", "Ramadan dates confounded (F12)" if d in ("2023-03-19", "2023-04-23", "2024-03-10", "2024-04-14") else "")
     for k, d in enumerate(["2023-03-19", "2023-04-23", "2023-10-29", "2024-03-10", "2024-04-14"])]


# ---------------------------------------------------------------- tables
def table1_inventory(res, tet_data):
    rows = []
    unit = {"Laayoune": "A", "Boujdour": "A", "Foum eloued": "A", "Marrakech": "kW", "Tetouan": "kW"}
    system = {"Laayoune": "south (one logger)", "Boujdour": "south (one logger)", "Foum eloued": "south (one logger)", "Marrakech": "Marrakech", "Tetouan": "Tetouan (transfer)"}
    for c, d in list(res["data"].items()) + list(tet_data.items()):
        step = (d.index[1] - d.index[0]).seconds // 60
        rows.append(dict(city=c, system=system[c], zones=d.shape[1], step_min=step, unit=unit[c], start=str(d.index[0]), end=str(d.index[-1]),
                         regular_steps=len(d), missing_steps=int(d.isna().any(axis=1).sum()), exact_zero_zone_steps=int((d == 0).sum().sum())))
    return pd.DataFrame(rows)


def table3_rules():
    rs = pd.read_csv(RES / "catalogue_v1" / "rule_summary.csv")
    rp = pd.read_csv(RES / "labels_v1" / "rule_params.csv")
    agg = rp.groupby("rule").agg(outputs=("output", lambda s: ", ".join(s)), learned_precision=("learned_precision", "max"),
                                 log_odds_a_over_b=("log_odds_a_over_b", "max"), defining=("defining", "max")).reset_index()
    out = rs[["rule", "family", "item_kind", "n_votes", "coverage", "overlap", "conflict"]].merge(agg, on="rule", how="left")
    order = {r: i for i, r in enumerate(["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9", "R10", "R11", "R12", "R13", "R14", "R15", "R16", "R19", "R20", "R21"])}
    return out.sort_values("rule", key=lambda s: s.map(order)).reset_index(drop=True)


def corrections_table():
    """paper_handoff §3 (corrections to the original plan) as a table."""
    t = (ROOT / "docs" / "paper_handoff.md").read_text(encoding="utf-8")
    sec = t.split("## 3. Corrections to the guide")[1].split("## 4.")[0]
    rows = [l for l in sec.splitlines() if l.startswith("| ") and not l.startswith("| #") and not l.startswith("|---")]
    recs = []
    for l in rows:
        safe = l.strip().replace("\\|", "¦")                     # escaped pipes inside a cell (e.g. |δ*|)
        cells = [c.strip().replace("¦", "|").replace("\\*", "*") for c in safe.strip("|").split("|")]
        if len(cells) == 5:
            recs.append(dict(no=cells[0], guide_item=cells[1], problem_found=cells[2], fix=cells[3], ref=cells[4]))
    return pd.DataFrame(recs)


def build_tables(res, tet_data, cat, eps, ke, typology):
    T = PAPER / "tables"; T.mkdir(parents=True, exist_ok=True)
    B = RES / "benchmark_v1"; DS = RES / "downstream_v1"; TT = RES / "transfer_tetouan"
    made = {}
    def save(name, df, source):
        df.to_csv(T / f"{name}.csv", index=False); made[name] = source
    save("Table1_data_inventory", table1_inventory(res, tet_data), "computed from the regularised data (rules_v0.regularise)")
    save("Table2_typology", typology, "paper_figures.TYPOLOGY + final catalogue counts")
    save("Table3_rules", table3_rules(), "results/catalogue_v1/rule_summary.csv + results/labels_v1/rule_params.csv")
    save("Table4_key_events", ke, "results/catalogue_v1/key_events_v1.csv + final catalogue")
    copies = [("Table5_detection", B / "table5_detection.csv"), ("Table5_wilcoxon", B / "table5_wilcoxon.csv"),
              ("Table6_attribution", B / "table6_attribution.csv"), ("Table7a_pipeline", B / "table7a_pipeline.csv"),
              ("Table7b_detector_ablations_3pct", B / "table7b_detector.csv"), ("Table7c_rule_families", B / "table7c_rule_families.csv"),
              ("Table7d_threshold_sensitivity", B / "table7d_threshold_sensitivity.csv"), ("Table7e_ablations_main_detector", B / "table7e_ablations_main_detector.csv"),
              ("Table7f_graph_ablation", B / "graph_ablation" / "table_graph_ablation.csv"),
              ("Table8_forecasting", DS / "table8_forecasting.csv"), ("Table8_dm_tests", DS / "table8_dm.csv"), ("Table8_outage_injected", DS / "outage_injected.csv"),
              ("Table8_outage_all_datasets", DS / "outage_all" / "outage_summary.csv"),
              ("Table9_tetouan_detection", TT / "table9_detection.csv"), ("Table9_tetouan_wilcoxon", TT / "table9_wilcoxon.csv"),
              ("Table9_tetouan_recall_by_type", TT / "table9_recall_by_type.csv"), ("Table9_tetouan_attribution", TT / "table9_attribution.csv"),
              ("TableS1_rule_parameters", RES / "labels_v1" / "rule_params.csv"), ("TableS2_label_model_recovery", RES / "labels_v1" / "recovery_summary.csv"),
              ("TableS3_label_robustness", RES / "labels_v1" / "robustness.csv"), ("TableS4_dev_selection", B / "dev" / "dev_best_settings.csv"),
              ("TableS5_hard_negatives", B / "hard_negatives.csv"), ("TableS6_predictor_comparison", B / "predictor_comparison.csv")]
    for name, src in copies:
        shutil.copyfile(src, T / f"{name}.csv"); made[name] = str(src.relative_to(ROOT)).replace("\\", "/")
    save("TableS7_corrections_to_the_plan", corrections_table(), "docs/paper_handoff.md section 3")
    return made


def build_figures():
    F = PAPER / "figures"; F.mkdir(parents=True, exist_ok=True)
    rows = []
    for num, stem, cap in MAIN_FIGURES:
        tag = num.replace("Fig ", "Fig").zfill(2) if False else f"Fig{int(num.split()[1]):02d}"
        for ext in ("pdf", "png"):
            shutil.copyfile(RES / "figures" / f"{stem}.{ext}", F / f"{tag}_{stem}.{ext}")
        rows.append(dict(number=num, file=stem, caption=cap, note=""))
    for num, stem, cap, note in SUPP_FIGURES:
        tag = f"FigS{int(num.split('S')[1]):02d}"
        for ext in ("pdf", "png"):
            shutil.copyfile(RES / "figures" / f"{stem}.{ext}", F / f"{tag}_{stem}.{ext}")
        rows.append(dict(number=num, file=stem, caption=cap, note=note))
    return pd.DataFrame(rows)


def write_manifest(figs, tables, cat_counts):
    L = ["# Paper set: figures and tables (NB7)", "",
         "Generated by `notebooks/NB7_final_figures.ipynb` (`src/paper_figures.py`, `src/paper_regen.py`, `src/paper_tables.py`). "
         "Captions are drafts for the writing agent; every number in them is in `docs/results_summary.md`. "
         "Figure files: `figures/FigNN_<source>.pdf|png` (copies of `results/figures/<source>`). Tables: `tables/*.csv`.", "",
         "## Main figures", "", "| Number | Source file | Draft caption |", "|---|---|---|"]
    for r in figs[~figs.number.str.contains("S")].itertuples():
        L.append(f"| {r.number} | `{r.file}` | {r.caption} |")
    L += ["", "## Supplementary figures", "", "| Number | Source file | Content | Note |", "|---|---|---|---|"]
    for r in figs[figs.number.str.contains("S")].itertuples():
        L.append(f"| {r.number} | `{r.file}` | {r.caption} | {r.note} |")
    L += ["", "## Tables", "", "| Table | Source |", "|---|---|"]
    for k, v in tables.items():
        L.append(f"| `{k}.csv` | {v} |")
    L += ["", "## Catalogue", "", f"Released in `results/catalogue_final/` ({cat_counts}). See its README."]
    (PAPER / "MANIFEST.md").write_text("\n".join(L) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- the released catalogue
CATALOGUE_README = """# Typed, probabilistic event catalogue for UCI 1158 (Morocco smart-meter feeder data)

Release of the paper *Grid event or data artefact? Hierarchical weak supervision for anomaly attribution in multi-city
feeder telemetry*. Built from the UCI Machine Learning Repository dataset 1158 (licence: CC BY 4.0) without manual labels.

## Files
- `catalogue.csv`: one row per item (rule-engine v1 item or detector-only candidate).
- `episodes.csv`: items linked into episodes, with the sequence of final labels (e.g. `A2(1.00) → A2(1.00) → A1(0.99)`).
- `key_events.csv`: the key events of the paper (guide ids C01–C12) with their final labels.

## Columns of `catalogue.csv`
| Column | Meaning |
|---|---|
| item_id | `D###` dead, `F###` fill, `K###` clock, `T###` transfer (rule engine v1); `XS###` detector-only candidate in the south (main detector), `XM###` in Marrakech (NB3 detector) |
| system | `south` (Laâyoune, Boujdour, Foum El Oued: one shared 10-min logger, A) or `Marrakech` (30 min, kW) |
| kind | dead (x = 0 or x ≤ 5 % of expected), fill (held or straight-line interpolated values), clock (a clock-change day), transfer (a load-transfer day), detector |
| source | `rule` (an item of the rule engine) or `detector` (a detector-only candidate: no rule covers it) |
| start, end | the item's span, timestamps **as recorded** (no clock correction); end exclusive |
| duration_h, cities, zones, n_cities, n_zones | extent; zone codes L1–L5, B1–B3, F1–F7, M1–M2 |
| episode | the episode the item belongs to (items sharing boundaries) |
| label | final type: A1 zero-fill gap, A2 simultaneous fill, A3 single-zone fill, A4 clock error, G1 regional outage, G2 city outage, G3 unplanned feeder outage, G4 planned work, G5 load transfer, N normal / untyped |
| confidence | the probability of the label |
| family | artefact (A*), grid event (G*), normal / untyped (N) |
| label_source | how the distribution was obtained: fusion of label model and end model with the main detector (south dead/fill and south candidates), NB3 fusion (Marrakech), or the label model alone (clock and transfer items) |
| votes | the rule votes on the item (`rule:label`) |
| p_A1 … p_N | the probability of each type |

## How to read it
- **Artefacts (A\\*) should be imputed** before using the series; **grid events (G\\*) are real** and should be kept and flagged.
- **Labels on the real data are not validated against external records.** They were validated on injected events: attribution macro-F1 0.91–0.94 and detection F1 0.72–0.91 (paper, NB4).
- **Detector-only candidates labelled N are untyped, not normal:** anomalies outside the typology (partial drops, surges, short disturbances).
- Item ids are stable only for this release: they change if the rule engine is re-run with other parameters.
- G1 does not occur on the real data; every multi-city dead event comes with hold or straight-line-fill evidence.
"""


def release_catalogue(cat, eps, ke):
    out = RES / "catalogue_final"; out.mkdir(parents=True, exist_ok=True)
    c = cat.copy()
    c["start"] = pd.to_datetime(c.start).dt.strftime("%Y-%m-%d %H:%M"); c["end"] = pd.to_datetime(c.end).dt.strftime("%Y-%m-%d %H:%M")
    c.to_csv(out / "catalogue.csv", index=False)
    eps[["episode", "start", "end", "n_items", "cities", "n_zones_max", "items", "sequence_final", "families_final", "duration_h"]].rename(
        columns={"sequence_final": "sequence", "families_final": "families"}).to_csv(out / "episodes.csv", index=False)
    ke.to_csv(out / "key_events.csv", index=False)
    (out / "README.md").write_text(CATALOGUE_README, encoding="utf-8")
    return out
