# Generator for notebooks/NB6_tetouan.ipynb. Usage: python tools/make_nb6_tetouan.py notebooks/NB6_tetouan.ipynb
import sys
import nbformat as nbf
from nbformat.v4 import new_notebook, new_code_cell as C, new_markdown_cell as M

cells = []
cells.append(M(r"""# NB6 · Transfer test: Tetouan, without re-tuning

Guide section "Generalisation to Tetouan", RQ5, Table 9. UCI Tetouan dataset: 3 distribution zones of one city, 2017, 10-min steps, power in kW (Salam & El Hibaoui 2018). The guide asks for three things:
1. the false-alarm rate on the real data;
2. recall on injected events;
3. the type distribution found.

**Frozen from the Morocco study** (nothing is chosen on Tetouan):
- every rule threshold, item and episode definition (rule engine v1);
- the **label model's parameters**, fitted on the Morocco votes and applied with `DawidSkene.predict` (one E-step, no refit);
- the detector architectures and training hyper-parameters (TCN-GAT main detector, its no-graph ablation, LightGBM);
- each detector's event formation (smoothing w, threshold percentile q, merge gap) from `dev_selection.json`;
- the injected signatures and the evaluation code (eq. 17).

**Re-estimated from Tetouan's own unlabelled data**, as the method prescribes for any new system:
- the expected value x̂ (eq. 1) and the robust-score scales;
- the predictor weights, trained on Tetouan's rule-clean steps and cross-fitted in two folds split at 1 Jul 2017;
- the threshold γ, as the frozen q-th percentile of Tetouan's own rule-negative zone-steps.

**Single-city limits** (D69):
- The city and region parts of the hierarchy coincide.
- The graph has only same-city edges.
- R1 (multi-city zero) and R7 (regional outage) cannot fire.
- G1 is the same event as G2 in one city, so it is not injected; multi-city types become city-wide.

**Evaluation:** 1 %, 3 % and 7 % × seeds 0–9 (30 injected datasets). Metrics over the whole year after the burn-in, since no Tetouan data is used for any choice.

**Runtime:** about 5 min for training plus about 1 min per dataset on CPU. Resumable. Decisions D68–D70."""))

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
import matplotlib.pyplot as plt, matplotlib.dates as mdates
from scipy.stats import wilcoxon
import rules_v1 as R1, detector as D, benchmark as B, inject as INJ, graph_model as G, transfer as T
from viz import COL, LABEL_COL, savefig

RATES, SEEDS = [0.01, 0.03, 0.07], list(range(10))
TCN_CFG = dict(epochs=40, patience=6)            # as NB4
OUT = ROOT / "results" / "transfer_tetouan"; RUNS = OUT / "runs"; RUNS.mkdir(parents=True, exist_ok=True)
FIG = ROOT / "results" / "figures"
CSV = ROOT / "data" / "raw" / "tetouan" / "Tetuan City power consumption.csv"
pd.set_option("display.width", 220); pd.set_option("display.max_columns", 40); pd.set_option("display.max_colwidth", 60)
T.register()
SEL = json.loads((ROOT / "results" / "benchmark_v1" / "dev_selection.json").read_text())
print("main detector:", SEL["main"], "| device", G.default_device(), "| split", D.SPLIT.date())
T0 = time.time()"""))

cells.append(M("## 1. The Tetouan series"))
cells.append(C(r"""raw, data, weather = T.load(CSV)
x = data["Tetouan"]
st = raw["Tetouan"].DateTime
audit = dict(start=str(x.index[0]), end=str(x.index[-1]), steps=len(x), duplicate_stamps=int(st.duplicated().sum()),
             missing_steps=int(len(pd.date_range(st.min(), st.max(), freq="10min").difference(st))),
             zeros=int((x == 0).sum().sum()), longest_equal_run=int(max(x[c].groupby((x[c].diff() != 0).cumsum()).size().max() for c in x)))
print(audit)
display(x.describe().round(0))
fig, axs = plt.subplots(2, 1, figsize=(12, 5))
x.resample("1D").mean().plot(ax=axs[0], lw=1); axs[0].set_ylabel("daily mean (kW)"); axs[0].set_title("(a) 2017, daily mean per zone")
x.loc["2017-03-06":"2017-03-12"].plot(ax=axs[1], lw=.8, legend=False); axs[1].set_ylabel("kW"); axs[1].set_title("(b) one week, 10-min steps")
fig.suptitle("E22 — UCI Tetouan: three zones of one city (transfer test)", y=1.0); fig.tight_layout(); savefig(fig, FIG, "E22_tetouan_series"); plt.show()"""))

cells.append(M(r"""## 2. Frozen rules and frozen label model on the real series (false alarms of the rules, type distribution)"""))
cells.append(C(r"""ds, _ = T.frozen_label_model(ROOT / "data" / "raw" / "Data Morocco.xlsx")
tr = T.Transfer(raw, data, ds, SEL)
it = tr.real["items"]
print("items on the real Tetouan series:", it.kind.value_counts().to_dict(), "| zone runs:", len(tr.real["zr"]),
      "| rule outputs unseen in Morocco:", tr.real["unseen"])
display(it[["item_id", "kind", "start", "votes", "label", "confidence", "delta_star_min", "corr_best", "n_duplicate_stamps", "n_missing_steps"]])
it.to_csv(OUT / "real_items.csv", index=False)
print(f"clean region (where injection is allowed): {tr.clean.to_numpy().mean():.3f} of zone-steps")"""))

cells.append(M(r"""## 3. Predictors trained on Tetouan (frozen hyper-parameters), and the detectors on the real series"""))
cells.append(C(r"""tr.fit_predictors(TCN_CFG, G.default_device(), OUT / "models", log=False)
P = tr.P; pred = tr.predictions(P); ok = ~P["mask"] & P["rho"].notna()
mae = pd.DataFrame([dict(predictor=k, MAE=round(float((P["rho"] - v).abs()[ok].stack().mean()), 4)) for k, v in pred.items()])
mae.to_csv(OUT / "predictor_mae.csv", index=False); display(mae)
REAL = tr.analyse(data); tr.set_background(REAL)
months = (P["rho"].index[-1] - P["rho"].index[0]).days / 30.44
alarms = pd.DataFrame([dict(detector=k, w=tr.st[k]["w"], q=tr.st[k]["q"], gap=tr.st[k]["gap"], gamma=round(REAL["GAM"][k], 2),
                            real_alarms=len(d), per_zone_month=round(len(d) / (3 * months), 2),
                            alarm_zone_hours=round(float((d.duration_h * d.n_zones).sum()) if len(d) else 0.0, 1))
                       for k, d in REAL["DET"].items()])
alarms.to_csv(OUT / "real_alarms_by_detector.csv", index=False); display(alarms)
cal = D.calendar(P["rho"].index)
do = REAL["DET"][B.V_GAT].copy()
if len(do):
    pos = P["rho"].index.get_indexer(do.start)
    do["weekday"] = do.start.dt.day_name(); do["ramadan"] = cal.ramadan.to_numpy()[pos]; do["eid"] = cal.eid.to_numpy()[pos]
    do["holiday"] = cal.holiday.to_numpy()[pos]
    do.to_csv(OUT / "real_alarms_main_detector.csv", index=False)
    display(do[["start", "end", "zones", "duration_h", "max_score", "weekday", "ramadan", "eid", "holiday"]])"""))

cells.append(M(r"""## 4. Injection benchmark (resumable)
Observed Morocco signatures are injected into Tetouan's clean zone-time at 1 %, 3 % and 7 % (seeds 0–9). Types: A1 (city-wide exact zeros), A2, A3, G2 (city-wide noise floor), G3, G4, U_SHOCK (city-wide) and U_PARTIAL."""))
cells.append(C(r"""inj = INJ.Injector(data, tr.real["r"]["exp"], tr.clean, INJ.zone_map(data, [T.CITY], R1.CITY_SHORT))
todo = [(r, s) for r in RATES for s in SEEDS]
t_start = time.time(); done = 0
for rate, seed in todo:
    tag = f"r{int(round(rate * 100)):02d}_s{seed:02d}"
    if (RUNS / f"{tag}_detection.csv").exists():
        continue
    t = time.time()
    d_inj, truth = inj.sample(np.ones(len(tr.index), bool), rate, np.random.default_rng([int(round(rate * 1000)), seed]), types=T.TYPES_T)
    out = tr.analyse(d_inj, seed=seed)
    det, att = tr.metrics(out, truth)
    truth.to_csv(RUNS / f"{tag}_truth.csv", index=False)
    att.to_csv(RUNS / f"{tag}_attribution.csv", index=False)
    det.to_csv(RUNS / f"{tag}_detection.csv", index=False)
    done += 1
    left = sum(1 for r, s in todo if not (RUNS / f"r{int(round(r * 100)):02d}_s{s:02d}_detection.csv").exists())
    print(f"{tag}: {len(truth)} events, {time.time() - t:.0f} s | {left} left", flush=True)
print("all runs present:", all((RUNS / f"r{int(round(r * 100)):02d}_s{s:02d}_detection.csv").exists() for r, s in todo))"""))

cells.append(M(r"""## 5. Table 9: detection and attribution after transfer
Every alarm counts (primary). The own-background-excluded F1 removes each method's detections on the uninjected Tetouan series. Per-type recall is zone-strict."""))
cells.append(C(r"""def load(kind):
    return pd.concat([pd.read_csv(RUNS / f"r{int(round(r * 100)):02d}_s{s:02d}_{kind}.csv").assign(rate=r, seed=s) for r, s in todo], ignore_index=True)
DET, ATT, TRUTH = load("detection"), load("attribution"), load("truth")
print(len(todo), "datasets;", len(TRUTH), "injected events;", TRUTH.type.value_counts().to_dict())
def ms(x):
    x = pd.Series(x).dropna(); return f"{x.mean():.3f} ± {x.std(ddof=1):.3f}" if len(x) > 1 else "n/a"
ORDER = ["ours (rules + detector)", "rules only (rule engine v1)"] + T.DETECTORS
rows = []
for rate in RATES:
    for m in ORDER:
        g = DET[(DET.rate == rate) & (DET.method == m)]
        rows.append(dict(rate=f"{rate:.0%}", method=m, F1=ms(g.f1), precision=ms(g.precision), recall=ms(g.recall), F1_zone_strict=ms(g.f1_zone),
                         F1_own_background_excluded=ms(g.f1_bgx), AUC_PR=ms(g.auc_pr), real_alarms=len(REAL["DET"].get(m, [])) if m in REAL["DET"] else np.nan))
table9 = pd.DataFrame(rows); table9.to_csv(OUT / "table9_detection.csv", index=False); display(table9)
wil = []
for rate in RATES:
    a = DET[(DET.rate == rate) & (DET.method == B.V_GAT)].set_index("seed").f1
    for m in ORDER:
        if m == B.V_GAT:
            continue
        b = DET[(DET.rate == rate) & (DET.method == m)].set_index("seed").f1.reindex(a.index)
        d = a - b
        wil.append(dict(rate=f"{rate:.0%}", comparison=f"main detector vs {m}", main=round(a.mean(), 4), other=round(b.mean(), 4),
                        main_wins=int((d > 0).sum()), p=float(wilcoxon(a, b).pvalue) if (d != 0).any() else 1.0))
wil = pd.DataFrame(wil); wil.to_csv(OUT / "table9_wilcoxon.csv", index=False); display(wil)
rec_cols = [f"recall_{t}" for t in T.TYPES_T]
rec = DET[DET.method.isin(["ours (rules + detector)", "rules only (rule engine v1)", B.V_GAT, B.V_TCN_MS, B.V_LGB])].groupby(["rate", "method"])[rec_cols].mean().round(3)
rec.to_csv(OUT / "table9_recall_by_type.csv"); display(rec)"""))

cells.append(C(r"""att_rows = []
for (rate, seed), g in ATT.groupby(["rate", "seed"]):
    d = g[g.detected]
    att_rows.append(dict(rate=rate, seed=seed, detected_share=g.detected.mean(),
                         macro_F1_label_model=T.macro_f1(d.type, d.label), macro_F1_majority_vote=T.macro_f1(d.type, d.mv),
                         accuracy_label_model=(d.label == d.type).mean(), accuracy_majority_vote=(d.mv == d.type).mean(),
                         end_to_end=(g.label == g.type).mean()))
att_tab = pd.DataFrame(att_rows)
att_sum = att_tab.groupby("rate").agg(**{c: (c, ms) for c in att_tab.columns if c not in ("rate", "seed")})
att_sum.to_csv(OUT / "table9_attribution.csv"); display(att_sum)
r0 = 0.03; sub = ATT[(ATT.rate == r0) & ATT.detected]
cm = pd.crosstab(pd.Categorical(sub.type, categories=T.TYPED_T), pd.Categorical(sub.label, categories=T.TYPED_T + ["G1", "N"]), dropna=False)
cm.to_csv(OUT / "confusion_label_model_3pct.csv"); display(cm)
per_class = {c: round(float(((sub.type == c) & (sub.label == c)).sum() / max((sub.type == c).sum(), 1)), 3) for c in T.TYPED_T}
print("per-class accuracy (3 %):", per_class)"""))

cells.append(M(r"""## 6. Morocco vs Tetouan (same method, same settings)
Morocco: NB4 test period (Jul 2023 – May 2024, 15 zones, 3 cities). Tetouan: the whole of 2017 after the burn-in (3 zones, 1 city). The datasets differ, so this is context, not a paired test."""))
cells.append(C(r"""mor = pd.read_csv(ROOT / "results" / "benchmark_v1" / "table5_detection.csv")
mor6 = pd.read_csv(ROOT / "results" / "benchmark_v1" / "table6_attribution.csv")
cmp_rows = []
for rate in RATES:
    rs = f"{rate:.0%}"
    for m in ["ours (rules + detector)", "rules only (rule engine v1)", B.V_GAT, B.V_LGB, "STL + MAD"]:
        mo = mor[(mor.rate == rs) & (mor.method == m)]
        te = table9[(table9.rate == rs) & (table9.method == m)]
        cmp_rows.append(dict(rate=rs, method=m, Morocco_F1=mo.F1.iloc[0] if len(mo) else "n/a", Tetouan_F1=te.F1.iloc[0] if len(te) else "n/a"))
    mo = mor6[(mor6.rate == rs) & (mor6.labeler == "label model q")]
    cmp_rows.append(dict(rate=rs, method="attribution: label model macro-F1", Morocco_F1=mo.macro_F1.iloc[0] if len(mo) else "n/a",
                         Tetouan_F1=att_sum.loc[rate, "macro_F1_label_model"]))
cmp = pd.DataFrame(cmp_rows); cmp.to_csv(OUT / "morocco_vs_tetouan.csv", index=False); display(cmp)"""))

cells.append(M("## 7. Fig 13"))
cells.append(C(r"""SHOW = ["ours (rules + detector)", "rules only (rule engine v1)", B.V_GAT, B.V_TCN_MS, B.V_LGB, "STL + MAD", "Isolation Forest", "LOF"]
COLM = {"ours (rules + detector)": "#C8553D", B.V_GAT: "#C8553D", "rules only (rule engine v1)": "#2F6690", "STL + MAD": "#2F6690",
        "Isolation Forest": "#2F6690", "LOF": "#2F6690", B.V_TCN_MS: "#7B5EA7", B.V_LGB: "#7B5EA7"}
fig, axs = plt.subplots(1, 2, figsize=(14, 4.6), gridspec_kw=dict(width_ratios=[1.5, 1]))
ys = np.arange(len(SHOW))[::-1]
for k, (rate, mk) in enumerate(zip(RATES, ["o", "s", "D"])):
    for y, m in zip(ys, SHOW):
        g = DET[(DET.rate == rate) & (DET.method == m)].f1
        axs[0].errorbar(g.mean(), y + (k - 1) * 0.22, xerr=g.std(ddof=1), fmt=mk, color=COLM[m], ms=6, capsize=0, lw=1,
                        mfc=COLM[m] if rate == 0.03 else "white", label=f"{rate:.0%}" if y == ys[0] else None)
axs[0].set_yticks(ys); axs[0].set_yticklabels([m.replace(", hierarchy, multi-scale", "") for m in SHOW], fontsize=8)
axs[0].set_xlim(0, 1); axs[0].set_xlabel("event F1 (eq. 17), mean ± sd over 10 seeds"); axs[0].legend(title="contamination", fontsize=8)
axs[0].set_title("(a) detection on Tetouan, frozen method")
norm = cm.div(cm.sum(axis=1).replace(0, 1), axis=0)
axs[1].imshow(norm.values, cmap="Blues", vmin=0, vmax=1)
axs[1].set_xticks(range(cm.shape[1])); axs[1].set_xticklabels(cm.columns); axs[1].set_yticks(range(cm.shape[0])); axs[1].set_yticklabels(cm.index)
for (i, j), v in np.ndenumerate(cm.values):
    if v: axs[1].text(j, i, v, ha="center", va="center", fontsize=7, color="w" if norm.values[i, j] > .6 else "k")
axs[1].set_xlabel("frozen label model"); axs[1].set_ylabel("injected type"); axs[1].set_title("(b) attribution, 3 %, detected typed events")
fig.suptitle("Fig 13 — Transfer to Tetouan without re-tuning (rules, label model and event formation frozen from Morocco)", y=1.02)
fig.tight_layout(); savefig(fig, FIG, "fig13_tetouan"); plt.show()"""))

cells.append(M("## 8. Summary"))
cells.append(C(r"""f1 = lambda m, r: round(float(DET[(DET.rate == r) & (DET.method == m)].f1.mean()), 3)
summary = dict(
    audit=audit, real_items=it.kind.value_counts().to_dict(), real_item_labels=it.label.value_counts().to_dict(),
    real_zone_runs=int(len(tr.real["zr"])), predictor_MAE=mae.set_index("predictor").MAE.to_dict(),
    real_alarms={r.detector: dict(n=r.real_alarms, per_zone_month=r.per_zone_month) for r in alarms.itertuples()},
    detection_F1={f"{r:.0%} | {m}": f1(m, r) for r in RATES for m in ORDER},
    detection_F1_bgx={f"{r:.0%} | {m}": round(float(DET[(DET.rate == r) & (DET.method == m)].f1_bgx.mean()), 3) for r in RATES for m in ORDER},
    recall={f"{r:.0%} | {m}": round(float(DET[(DET.rate == r) & (DET.method == m)].recall.mean()), 3) for r in RATES for m in ORDER},
    attribution={f"{r:.0%}": att_tab[att_tab.rate == r].drop(columns=["rate", "seed"]).mean().round(3).to_dict() for r in RATES},
    injected_events=int(len(TRUTH)), injected_by_type=TRUTH.type.value_counts().to_dict(), runtime_min=round((time.time() - T0) / 60, 1))
summary = json.loads(json.dumps(summary, default=float))
(OUT / "summary.json").write_text(json.dumps(summary, indent=2)); print(json.dumps(summary["detection_F1"], indent=1))"""))

nb = new_notebook(cells=cells)
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nbf.write(nb, sys.argv[1])
print("wrote", sys.argv[1])
