# Generator for notebooks/NB5_downstream.ipynb. Usage: python tools/make_nb5_downstream.py notebooks/NB5_downstream.ipynb
import sys
import nbformat as nbf
from nbformat.v4 import new_notebook, new_code_cell as C, new_markdown_cell as M

cells = []
cells.append(M(r"""# NB5 · Downstream test: does type-aware cleaning matter?

Guide section "Downstream forecasting evaluation" (eq. 19–20), RQ4, Table 8 and Fig 12. Southern system (15 zones, 10-min steps).

**Cleaning strategies.** They act on flagged zone-steps: dead, hold or linear-fill states inside a qualifying rule zone run.

| Strategy | Artefacts (A1–A3) | Grid events (G1–G5) |
|---|---|---|
| S0 raw | kept | kept |
| S1 naive | linearly interpolated | linearly interpolated (outages erased) |
| S2 typed (ours) | imputed with x̂ (eq. 1), scaled to join the series at both edges | kept, with an event indicator the forecaster sees, excluded from the training loss |
| S3 oracle | as S2, with the true types | as S2, with the true types (injected data only) |

- **Labels on the real data:** the fused labels of the main-detector catalogue (`results/main_detector/p_type_south.csv`, NB4 §8b).
- **Labels on injected data:** the label model's arg max (it matches fusion there, F46).
- **Not changed by any strategy:** items labelled N, clock items and detector-only candidates are left as recorded. A4 stamps are not re-aligned: timestamps stay as recorded (D11).

**Forecasters.**
- A global LightGBM direct forecaster per horizon: 1 h (6 steps) and 1 day (144 steps), rolling origin. Inputs: zone-scaled lags, same-time-of-day lags, the event indicator and target-time calendar.
- A model-free reference on the same cleaned series: persistence at 1 h, seasonal naive (one day earlier) at 1 day.
- They are trained before 1 Jan 2024 and scored on **1 Jan – 24 May 2024** (the guide's test period).
- Scoring uses only zone-steps that every strategy treats as normal (no flagged state, rule item, detector-only candidate or injected event). It compares with the recorded values.
- **Metrics:** MAE, RMSE (A), MASE (eq. 19, seasonal-naive scale), sMAPE.
- **Diebold–Mariano test** (eq. 20) on the per-step scaled absolute loss summed over the scored zones (so its mean follows the pooled MASE difference), with a Newey–West variance (lag = horizon).
- Also scored separately: the subset of steps whose zone had a flagged state in the 2 days before. There the history the forecaster reads contains anomalies.

**Outage statistics** (SAIDI-style check): zone-hours and counts of outages under "every dead state is an outage" (what S0 reports and S1 erases) and under the typed labels (S2), against the injected truth (S3).

**Runtime:** about 10 min for the real data plus about 8 min per injected dataset on 8 CPU cores. Outputs are cached in `results/downstream_v1/`, so the notebook resumes. Decisions: D64–D66."""))

cells.append(C(r"""import sys, subprocess, json, time
from pathlib import Path
IN_COLAB = "google.colab" in sys.modules
if IN_COLAB:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "lightgbm==4.6.0", "PyWavelets", "statsmodels", "openpyxl"], check=True)
    from google.colab import drive
    drive.mount("/content/drive")
    ROOT = Path("/content/drive/MyDrive/grid-event-or-data-artefact")
else:
    ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(ROOT / "src"))
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
import lightgbm
import rules_v1 as R1, detector as D, label_model as LM, benchmark as B, inject as INJ, downstream as DS
from viz import COL, savefig

INJ_SETS = [(0.03, 0), (0.03, 1), (0.03, 2), (0.07, 0)]   # NB4 test datasets reused for the oracle and the outage truth
SEED = 0
XLSX = ROOT / "data" / "raw" / "Data Morocco.xlsx"
OUT = ROOT / "results" / "downstream_v1"; (OUT / "injected").mkdir(parents=True, exist_ok=True)
FIG = ROOT / "results" / "figures"
pd.set_option("display.width", 220); pd.set_option("display.max_columns", 30)
print("ROOT =", ROOT, "| lightgbm", lightgbm.__version__)
T0 = time.time()"""))

cells.append(M("## 1. Real data: flagged steps, typed masks, scoring area"))
cells.append(C(r"""res = R1.build(XLSX)
P = D.build_panel(res["data"], res["exp"], res["masks"], "south")
XH = DS.exp_panel(res["exp"], P)
FLAG = DS.run_mask(P, res["zone_runs"])
cat = pd.read_csv(ROOT / "results" / "main_detector" / "p_type_south.csv", parse_dates=["start", "end"])
rule_lab = cat[cat.source == "rule"][["start", "end", "zones", "label"]]
ART, GRID = DS.typed_masks(P, FLAG, rule_lab)
items = res["items"]; south_items = items[items.system == "south"]
ANY_ITEM = DS.span_mask(P, south_items)                         # every rule item, all kinds
DETONLY = DS.span_mask(P, cat[cat.source == "detector"])
NORMAL = ~FLAG & ~ANY_ITEM & ~DETONLY & P["x"].notna()
idx = P["x"].index
print(f"flagged zone-steps {FLAG.to_numpy().mean():.4f}; artefact {ART.to_numpy().sum()}, grid {GRID.to_numpy().sum()} zone-steps;"
      f" normal {NORMAL.to_numpy().mean():.3f}")
print("labels of south rule items:", rule_lab.label.value_counts().to_dict())"""))

cells.append(M(r"""## 2. Outage statistics on the real data (F26 revisited)
A naive count treats every dead state (zero or noise floor, ≥ 30 min) as an outage. The typed count keeps only dead steps inside items labelled G. There is no truth on the real data, so §4 does the same on injected data."""))
cells.append(C(r"""DEAD = P["states"]["dead"] & FLAG
naive_z, naive = DS.outage_stats(P, DEAD)
typed_z, typed = DS.outage_stats(P, DEAD & GRID)
art_z, art = DS.outage_stats(P, DEAD & ART)
out_real = naive_z.rename(columns={"zone_hours": "naive_zone_hours", "outages": "naive_outages"}).merge(
    typed_z.rename(columns={"zone_hours": "typed_zone_hours", "outages": "typed_outages"}), on="code").merge(
    art_z.rename(columns={"zone_hours": "artefact_dead_zone_hours", "outages": "artefact_dead_runs"}), on="code")
out_real["city"] = out_real.code.map(P["city"])
out_real.to_csv(OUT / "outage_real.csv", index=False)
by_city = out_real.groupby("city")[["naive_zone_hours", "typed_zone_hours", "artefact_dead_zone_hours", "naive_outages", "typed_outages"]].sum()
display(by_city.round(1))
lab_dead = {}
for r in rule_lab.itertuples():          # dead zone-hours by label (an item's dead steps)
    m = DS.span_mask(P, pd.DataFrame([r._asdict()])) & DEAD
    lab_dead[r.label] = lab_dead.get(r.label, 0) + m.to_numpy().sum() / 6
print("dead zone-hours by item label:", {k: round(v, 1) for k, v in sorted(lab_dead.items())})
print(f"naive: {naive['zone_hours']:.1f} zone-h in {naive['outages']} runs | typed: {typed['zone_hours']:.1f} zone-h in {typed['outages']} runs"
      f" | ratio {naive['zone_hours'] / max(typed['zone_hours'], 1e-9):.2f}")"""))

cells.append(M(r"""## 3. Forecasting on the real data (S0, S1, S2)"""))
cells.append(C(r"""f_real, f_loss = OUT / "forecast_real.csv", OUT / "loss_real.pkl"
if f_real.exists() and f_loss.exists():
    fc_real = pd.read_csv(f_real); loss_real = pd.read_pickle(f_loss)
else:
    masks = {"S0": (None, None), "S1": (None, None), "S2": (ART, GRID)}
    fc_real, loss_real = DS.forecast_eval(P, FLAG, masks, NORMAL, NORMAL, XH, seed=SEED)
    fc_real.to_csv(f_real, index=False); pd.to_pickle(loss_real, f_loss)
dm_real = DS.dm_table(loss_real); dm_real.to_csv(OUT / "dm_real.csv", index=False)
display(fc_real.pivot_table(index=["model", "horizon", "subset"], columns="strategy", values="MASE").round(4))
display(dm_real.round(4))"""))

cells.append(M(r"""## 4. Injected data: the oracle (S3) and the outage truth
NB4's test datasets are regenerated from their seeds and checked against `results/benchmark_v1/runs/*_truth.csv`.
- **On each dataset:** the rules and the label model give the S2 labels; the injected truth gives the S3 labels.
- **Scoring area:** NB4's clean region plus the injected spans, as in NB4.
- **Forecasts:** scored on clean steps outside every injected event (truth = the real series there).
- **Outages:** counted inside the same area. Truth = injected G1–G4 core spans."""))
cells.append(C(r"""CLEAN = B.clean_region(P, None)
INJECTOR = INJ.Injector(res["data"], res["exp"], CLEAN, INJ.zone_map(res["data"], B.SOUTH, R1.CITY_SHORT))
GRID_T = ("G1", "G2", "G3", "G4", "U_SHOCK", "U_PARTIAL")
for rate, seed in INJ_SETS:
    tag = f"r{int(round(rate * 100)):02d}_s{seed:02d}"
    if (OUT / "injected" / f"{tag}_forecast.csv").exists():
        continue
    t = time.time()
    data_inj, truth = INJECTOR.sample(np.ones(len(idx), bool), rate, np.random.default_rng([int(round(rate * 1000)), seed]))
    stored = pd.read_csv(ROOT / "results" / "benchmark_v1" / "runs" / f"{tag}_truth.csv", parse_dates=["start"])
    assert len(stored) == len(truth) and (stored.start.values == truth.start.values).all(), f"{tag}: differs from NB4"
    r = R1.build_from_data(res["raw"], data_inj)
    it = r["items"]; votes = r["votes"].set_index("item_id")
    q = LM.DawidSkene().fit(votes, it, R1.RULE_KIND).q_; q.index = it.item_id.values
    ev = it[(it.system == "south") & it.kind.isin(["dead", "fill"])].copy()
    ev["label"] = q.loc[ev.item_id].idxmax(axis=1).values
    Pi = D.build_panel(r["data"], r["exp"], r["masks"], "south")
    XHi = DS.exp_panel(r["exp"], Pi)
    FLi = DS.run_mask(Pi, r["zone_runs"])
    ART2, GRID2 = DS.typed_masks(Pi, FLi, ev[["start", "end", "zones", "label"]])
    INJ_ANY = DS.span_mask(Pi, truth, "end_affected")
    ART3 = (ART2 & ~INJ_ANY) | DS.span_mask(Pi, truth[truth.type.isin(DS.ART)])
    GRID3 = ((GRID2 & ~INJ_ANY) | DS.span_mask(Pi, truth[truth.type.isin(GRID_T)], "end_affected")) & ~ART3
    REGION = CLEAN | INJ_ANY
    NORM_i = ~FLi & ~DS.span_mask(Pi, it[it.system == "south"]) & Pi["x"].notna()
    SCORE_i = NORM_i & CLEAN & ~INJ_ANY
    masks = {"S0": (None, None), "S1": (None, None), "S2": (ART2, GRID2), "S3": (ART3, GRID3)}
    fc, loss = DS.forecast_eval(Pi, FLi, masks, NORM_i, SCORE_i, XHi, seed=SEED)
    # outage statistics inside the scoring area
    DEADi = Pi["states"]["dead"] & FLi
    truth_out = DS.span_mask(Pi, truth[truth.type.isin(["G1", "G2", "G3", "G4"])]) & REGION
    rows = []
    for name, m in (("truth (S3)", truth_out), ("naive: every dead state (S0)", DEADi & REGION),
                    ("interpolated away (S1)", DEADi & False), ("typed, label model (S2)", DEADi & GRID2 & REGION)):
        _, tot = DS.outage_stats(Pi, m); rows.append(dict(strategy=name, **tot))
    outage = pd.DataFrame(rows).assign(rate=rate, seed=seed)
    tp = (DEADi & GRID2 & truth_out).to_numpy().sum(); pp = (DEADi & GRID2 & REGION).to_numpy().sum(); tt = truth_out.to_numpy().sum()
    outage["typed_precision_zone_steps"], outage["typed_recall_zone_steps"] = tp / max(pp, 1), tp / max(tt, 1)
    fc.assign(rate=rate, seed=seed).to_csv(OUT / "injected" / f"{tag}_forecast.csv", index=False)
    DS.dm_table(loss).assign(rate=rate, seed=seed).to_csv(OUT / "injected" / f"{tag}_dm.csv", index=False)
    outage.to_csv(OUT / "injected" / f"{tag}_outage.csv", index=False)
    print(f"{tag}: {len(truth)} injected events, {time.time() - t:.0f} s", flush=True)"""))

cells.append(M(r"""## 5. Table 8 and the outage check"""))
cells.append(C(r"""def load(kind):
    return pd.concat([pd.read_csv(OUT / "injected" / f"r{int(round(r * 100)):02d}_s{s:02d}_{kind}.csv") for r, s in INJ_SETS], ignore_index=True)
fc_inj, dm_inj, out_inj = load("forecast"), load("dm"), load("outage")
t8 = pd.concat([fc_real.assign(data="real"), fc_inj.assign(data="injected")], ignore_index=True)
table8 = t8.groupby(["data", "model", "horizon", "subset", "strategy"])[["MAE", "RMSE", "MASE", "sMAPE"]].mean().round(4)
table8.to_csv(OUT / "table8_forecasting.csv")
display(table8)
dm_all = pd.concat([dm_real.assign(data="real"), dm_inj.assign(data="injected")], ignore_index=True)
dm_all.to_csv(OUT / "table8_dm.csv", index=False)
display(dm_all.groupby(["data", "model", "horizon", "subset", "comparison"]).agg(
    mean_loss_diff=("mean_loss_diff", "mean"), DM=("DM", "mean"), p_max=("p", "max"), p_min=("p", "min"), n=("p", "size")).round(4))
outage_tab = out_inj.groupby(["rate", "strategy"])[["zone_hours", "outages"]].mean().round(1)
outage_tab.to_csv(OUT / "outage_injected.csv"); display(outage_tab)
truth_h = out_inj[out_inj.strategy == "truth (S3)"].set_index(["rate", "seed"]).zone_hours
for s in out_inj.strategy.unique():
    est = out_inj[out_inj.strategy == s].set_index(["rate", "seed"]).zone_hours
    print(f"{s:32s} outage zone-hours / truth: {(est / truth_h).mean():.2f}")
print("typed outage zone-steps: precision", round(out_inj.typed_precision_zone_steps.mean(), 3), "recall", round(out_inj.typed_recall_zone_steps.mean(), 3))"""))

cells.append(M(r"""## 6. Fig 12: forecast error by strategy and horizon, and outage-hours error"""))
cells.append(C(r"""SC = {"S0": "#9AA0A6", "S1": "#F2A541", "S2": "#C8553D", "S3": "#2F6690"}
fig, axs = plt.subplots(1, 3, figsize=(15, 4.2))
for ax, (data, sub) in zip(axs[:2], [("real", "after anomaly (2 days)"), ("injected", "after anomaly (2 days)")]):
    g = t8[(t8.data == data) & (t8.subset == sub) & (t8.model == "LightGBM")].groupby(["horizon", "strategy"]).MASE.mean().unstack()
    g = g.reindex(["1 h", "1 day"])
    g.plot.bar(ax=ax, color=[SC[c] for c in g.columns], rot=0, width=0.8)
    ax.set_ylabel("MASE (LightGBM)"); ax.set_xlabel(""); ax.set_title(f"({'ab'[axs.tolist().index(ax)]}) {data} data, {sub} test steps")
    ax.set_ylim(0, g.max().max() * 1.08); ax.legend(fontsize=8, ncol=2)
    for cont in ax.containers:
        ax.bar_label(cont, fmt="%.2f", fontsize=6, padding=1)
ratio = []
for s in out_inj.strategy.unique():
    est = out_inj[out_inj.strategy == s].set_index(["rate", "seed"]).zone_hours
    ratio.append((s, (est / truth_h).mean()))
lbl, val = zip(*ratio)
axs[2].barh(range(len(val)), val, color=["#2F6690", "#9AA0A6", "#F2A541", "#C8553D"][:len(val)])
axs[2].axvline(1, color="k", lw=.8, ls="--"); axs[2].set_yticks(range(len(val))); axs[2].set_yticklabels(lbl, fontsize=8)
for i, v in enumerate(val):
    axs[2].text(v + 0.02, i, f"{v:.2f}" + (" (outages erased)" if v == 0 else ""), va="center", fontsize=7)
axs[2].set_xlabel("outage zone-hours / injected truth"); axs[2].set_title("(c) outage statistics, injected data")
fig.suptitle("Fig 12 — Downstream: forecast error by cleaning strategy (test period 1 Jan – 24 May 2024) and outage-hours error", y=1.02)
fig.tight_layout(); savefig(fig, FIG, "fig12_downstream"); plt.show()"""))

cells.append(M("## 7. Summary"))
cells.append(C(r"""summary = dict(
    outage_real=dict(naive=naive, typed=typed, artefact_dead=art, ratio_naive_to_typed=naive["zone_hours"] / max(typed["zone_hours"], 1e-9),
                     dead_zone_hours_by_label={k: round(v, 1) for k, v in lab_dead.items()}),
    forecast_real={f"{r.model} | {r.horizon} | {r.subset} | {r.strategy}": dict(MAE=round(r.MAE, 4), MASE=round(r.MASE, 4), n=r.n)
                   for r in fc_real.itertuples()},
    dm_real={f"{r.model} | {r.horizon} | {r.subset} | {r.comparison}": dict(DM=round(r.DM, 3), p=r.p, mean_loss_diff=r.mean_loss_diff)
             for r in dm_real.itertuples()},
    outage_injected=out_inj.groupby("strategy")[["zone_hours", "outages"]].mean().round(2).to_dict("index"),
    outage_ratio_to_truth={s: round(float((out_inj[out_inj.strategy == s].set_index(["rate", "seed"]).zone_hours / truth_h).mean()), 3)
                           for s in out_inj.strategy.unique()},
    injected_sets=[f"{r:.0%} seed {s}" for r, s in INJ_SETS], lightgbm_version=lightgbm.__version__, runtime_min=round((time.time() - T0) / 60, 1))
summary = json.loads(json.dumps(summary, default=float))
(OUT / "summary.json").write_text(json.dumps(summary, indent=2))
print(json.dumps(summary["outage_real"], indent=1)); print(summary["outage_ratio_to_truth"])"""))

cells.append(C(r"""if IN_COLAB:
    drive.flush_and_unmount()
    print("Drive flushed and unmounted: now press Ctrl+S to save this notebook to Drive")"""))

nb = new_notebook(cells=cells)
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nbf.write(nb, sys.argv[1])
print("wrote", sys.argv[1])
