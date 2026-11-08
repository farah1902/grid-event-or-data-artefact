# Generator for notebooks/NB4_benchmark.ipynb. Usage: python tools/make_nb4_benchmark.py notebooks/NB4_benchmark.ipynb
import sys
import nbformat as nbf
from nbformat.v4 import new_notebook, new_code_cell as C, new_markdown_cell as M

cells = []
cells.append(M(r"""# NB4 · Learned graph (TCN-GAT) and injection benchmark

Guide sections "Detector: multi-scale graph model" (eq. 13), "Synthetic injection protocol", "Metrics" (eq. 17–18) and "Baselines, ablations and generalisation". This is the first place where accuracy against **known** types can be measured.

**Part A: the learned graph (guide eq. 13 as written).**
- **TCN-GAT** for the 15 southern zones: a causal temporal convolutional network on each zone's past, plus graph attention over the *current* ρ of its neighbours (leave-one-zone-out).
- Same-city zones are neighbours. Cross-city edges are **learned** (GDN-style node embeddings, top-k = 4 by cosine similarity).
- Ablation: the same TCN without the graph.
- Both are trained with the masked Huber loss and the same two-fold temporal cross-fitting as NB3's LightGBM.
- They are compared with LightGBM on clean-data error and on the residual-hierarchy test of NB3.

**Part B: injection benchmark.**
- Observed signatures are injected into clean zone-time only, at **1 %, 3 % and 7 %**, over **10 seeds**: A1–A3 and G1–G4, plus two untyped cases required by F29 (an unflagged multi-zone shock) and F32 (a partial outage).
- The whole method is rerun on each injected dataset: rules → label model → detector → end model → fusion.
- Training and validation use Sep 2022 – Jun 2023 (β is tuned there); the test period is Jul 2023 – May 2024.
- **Detection** (Table 5, Fig 9): event-wise precision, recall and F1 (eq. 17), and step-wise AUC-PR.
- **Attribution** (Table 6, Figs 10–11): macro-F1, per-class F1, ECE (eq. 18) and Brier.
- **Ablations** (Table 7): pipeline stages, rule families, hierarchy, scale, graph, forecast vs nowcast, and threshold sensitivity (ε, hold length, τ).
- **Hard negatives:** false alarms on Ramadan, Eid, holidays and weekends.

**Baselines:** the rule engine alone, STL + MAD, Isolation Forest, LOF and majority vote (guide list). Not run: Matrix Profile, USAD, TranAD, Anomaly Transformer, TimesNet, GDN, MTAD-GAT and Snorkel (D57).

**Run on Colab (GPU recommended):**
1. *Runtime → Change runtime type → T4 GPU*.
2. *Run all*.

Every injected dataset is saved to `results/benchmark_v1/runs/` as soon as it finishes. If Colab disconnects, *Run all* again: finished runs are skipped. Expect about 4–6 min per injected dataset (30 datasets at the default settings), plus about 10 min of TCN-GAT training on a GPU. Set `QUICK = True` for a 10-minute test run.

**Decisions:** D53 (TCN-GAT), D54 (injection protocol and evaluation scope), D55 (one network on ρ, not per band), D56 (β tuning and abstention on injected data), D57 (baselines not run), D58 (rerun and caching protocol)."""))

cells.append(C(r"""import sys, subprocess, json, time, pickle, os
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
import torch, lightgbm, pywt, statsmodels
from scipy.stats import wilcoxon
import rules_v1 as R1, detector as D, end_model as EM, label_model as LM, graph_model as G, benchmark as B, inject as INJ
from viz import COL, LABEL_COL, savefig
LABEL_COL = {**LABEL_COL, "N": "#9AA0A6"}

# ---------------------------------------------------------------- configuration
RATES = [0.01, 0.03, 0.07]          # guide: 1 %, 3 %, 7 % of clean zone-time
SEEDS = list(range(10))             # guide: 10 seeds
FAMILY_ABLATION_RATE = 0.03         # rule-family ablation of the label model runs at this rate only
SENS_SEEDS = [0, 1, 2]              # threshold sensitivity (rules + label model only), at 3 %
QUICK = False                       # True: one rate, two seeds, short TCN training (tests the notebook in ~10 min)
if QUICK:
    RATES, SEEDS, SENS_SEEDS = [0.03], [0, 1], [0]
TCN_CFG = dict(epochs=40, patience=6) if not QUICK else dict(epochs=2, max_batches=10)
BASELINES = ("STL + MAD", "Isolation Forest", "LOF")

XLSX = ROOT / "data" / "raw" / "Data Morocco.xlsx"
OUT = ROOT / "results" / ("benchmark_v1" if not QUICK else "benchmark_quick")
RUNS, MODELS = OUT / "runs", OUT / "models"
for d in (RUNS, MODELS): d.mkdir(parents=True, exist_ok=True)
FIG = ROOT / "results" / "figures" if not QUICK else OUT / "figures"     # QUICK figures never overwrite the real ones
FIG.mkdir(parents=True, exist_ok=True)
DEVICE = G.default_device()
pd.set_option("display.width", 220); pd.set_option("display.max_columns", 40); pd.set_option("display.max_colwidth", 60)
print("ROOT =", ROOT, "| device", DEVICE, "| lightgbm", lightgbm.__version__, "| torch", torch.__version__, "| QUICK", QUICK)
T0 = time.time()"""))

cells.append(M("## 1. Real data, NB3's detector-only candidates and the clean region (where injection is allowed)"))
cells.append(C(r"""res = R1.build(XLSX)
items = res["items"]
cat = pd.read_csv(ROOT / "results" / "catalogue_v1" / "items.csv", parse_dates=["start", "end"])
assert (items.item_id.values == cat.item_id.values).all(), "rule engine output differs from catalogue_v1"
P = D.build_panel(res["data"], res["exp"], res["masks"], "south")
det_real = pd.read_csv(ROOT / "results" / "detector_v1" / "detector_items.csv", parse_dates=["start", "end"])
det_real = det_real[det_real.system == "south"]
CLEAN = B.clean_region(P, det_real)
fold = P["rho"].index >= D.SPLIT
print(f"south panel {P['rho'].shape}; clean share of zone-steps: all {CLEAN.to_numpy().mean():.3f}, "
      f"train {CLEAN.to_numpy()[~fold].mean():.3f}, test {CLEAN.to_numpy()[fold].mean():.3f}")"""))

cells.append(M(r"""## 2. Predictors trained once on the real data

- **LightGBM forecast and nowcast** (NB3, D39–D41).
- **TCN** (no graph) and **TCN-GAT** (learned graph, guide eq. 13; D53).

All four are cross-fitted in two temporal folds and trained on rule-clean steps only. During the benchmark they only *predict* the injected series: each half is predicted by models trained on the other half of the real data, so they have never seen an injected event."""))
cells.append(C(r"""f = MODELS / "lightgbm_models.pkl"
LGB = None
if f.exists():
    try:   # pickled locally with numpy 1.26 / scikit-learn 1.5 / LightGBM 4.6.0; refit if this environment cannot read it
        LGB = pickle.load(open(f, "rb")); print("LightGBM models loaded from", f)
        assert set(LGB) == {"forecast", "nowcast"}
        _ = D.apply_rho_models(P, LGB["forecast"], "forecast")     # smoke test: the loaded models must predict
    except Exception as e:
        print("could not use the saved LightGBM models (", type(e).__name__, e, "): refitting"); LGB = None
if LGB is None:
    t = time.time()
    LGB = {k: D.fit_rho_models(P, k, backend="lightgbm") for k in ("forecast", "nowcast")}
    pickle.dump(LGB, open(f, "wb")); print(f"LightGBM fitted in {time.time() - t:.0f} s")

GM, HIST = {}, []
for name, graph in (("TCN", False), ("TCN-GAT", True)):
    f = MODELS / f"{name.replace('-', '_').lower()}.pt"
    if f.exists():
        GM[name] = G.load_models(f, P, device=DEVICE); print(name, "loaded from", f)
    else:
        t = time.time()
        GM[name], h = G.fit_graph_models(P, graph=graph, cfg=TCN_CFG, device=DEVICE, log=True)
        G.save_models(GM[name], f, TCN_CFG); h.to_csv(MODELS / f"{f.stem}_history.csv", index=False)
        print(f"{name} trained in {time.time() - t:.0f} s")
for f in MODELS.glob("*_history.csv"):
    HIST.append(pd.read_csv(f).assign(model=f.stem.replace("_history", "")))
if HIST:
    hist = pd.concat(HIST)
    fig, axs = plt.subplots(1, 2, figsize=(11, 3))
    for (m, tf), g in hist.groupby(["model", "train_fold"]):
        axs[int(tf)].plot(g.epoch, g.val, label=f"{m} (validation)")
        axs[int(tf)].plot(g.epoch, g.train, ls=":", label=f"{m} (train)")
    for k, ax in enumerate(axs):
        ax.set_title(f"trained on {'≥' if k else '<'} {D.SPLIT.date()}"); ax.set_xlabel("epoch"); ax.set_ylabel("masked Huber loss"); ax.legend(fontsize=7)
    fig.tight_layout(); plt.show()"""))

cells.append(C(r"""PRED = {"LGB forecast": D.apply_rho_models(P, LGB["forecast"], "forecast"),
        "LGB nowcast (all zones, no learned edges)": D.apply_rho_models(P, LGB["nowcast"], "nowcast"),
        "TCN (no graph)": G.apply_graph_models(P, GM["TCN"]),
        "TCN-GAT (learned graph)": G.apply_graph_models(P, GM["TCN-GAT"])}
clean = ~P["mask"]
rows = []
for name, pr in PRED.items():
    e = (P["rho"] - pr).where(clean)
    for per, sel in [("all", slice(None)), ("Jul 2023 +", e.index >= D.SPLIT)]:
        v = e.loc[sel].abs().stack()
        rows.append(dict(predictor=name, period=per, MAE=v.mean(), median_abs=v.median(), RMSE=np.sqrt((v ** 2).mean())))
pred_cmp = pd.DataFrame(rows).round(4)
pred_cmp.to_csv(OUT / "predictor_comparison.csv", index=False)

# NB3's residual-hierarchy test (raw band) for every predictor
south_items = items[(items.system == "south") & items.kind.isin(["dead", "fill"])].copy()
ncity = {c: sum(1 for z in P["rho"].columns if P["city"][z] == c) for c in set(P["city"].values())}
def expected_level(r):
    if r.n_cities >= 2: return "g"
    if r.n_zones >= 2: return "u" if r.n_zones / ncity[r.cities] >= 0.9 else None
    return "v"
south_items["expected_level"] = [expected_level(r) for r in south_items.itertuples()]
south_items.loc[south_items.start < P["rho"].index[0] + pd.Timedelta(days=D.WARMUP_DAYS), "expected_level"] = None
hrows = []
for name, pr in PRED.items():
    S = D.level_scores(P, P["rho"] - pr, bands_used=["raw"])["raw"]
    tops = []
    for r in south_items.itertuples():
        if r.expected_level is None: tops.append(None); continue
        sl = slice(r.start, r.end - pd.Timedelta("10min")); zs = r.zones.split(","); cs = sorted(set(P["city"][z] for z in zs))
        vals = [S["g"][sl].max(), S["u"].loc[sl, cs].max().max(), S["v"].loc[sl, zs].max().max()]
        tops.append("guv"[int(np.nanargmax(vals))] if np.isfinite(vals).any() else None)
    south_items["top"] = tops
    ok = south_items.expected_level.notna()
    for k in ["dead", "fill"]:
        for lv in "guv":
            sel = ok & (south_items.kind == k) & (south_items.expected_level == lv)
            if sel.any():
                hrows.append(dict(predictor=name, kind=k, level=lv, n=int(sel.sum()), correct=(south_items.top[sel] == lv).mean()))
    hrows.append(dict(predictor=name, kind="all", level="all", n=int(ok.sum()), correct=(south_items.top[ok] == south_items.expected_level[ok]).mean()))
hier_cmp = pd.DataFrame(hrows).round(3)
hier_cmp.to_csv(OUT / "hierarchy_consistency_by_predictor.csv", index=False)
display(pred_cmp.pivot_table(index="predictor", columns="period", values="MAE"))
display(hier_cmp.pivot_table(index=["kind", "level", "n"], columns="predictor", values="correct"))"""))

cells.append(M(r"""### The learned graph
Rows are receiving zones and columns are sending zones. Grey cells are edges the model can use: same city, plus the 4 learned cross-city neighbours. The colour shows the mean attention weight on clean steps, averaged over both folds and both heads."""))
cells.append(C(r"""LG = G.learned_graph(P, GM["TCN-GAT"])
zones = list(P["rho"].columns)
adj = sum(a.astype(int) for a, _ in LG.values()); att = sum(t for _, t in LG.values()) / len(LG)
fig, axs = plt.subplots(1, 2, figsize=(12, 5), gridspec_kw=dict(width_ratios=[1, 1.15]))
axs[0].imshow(adj.values, cmap="Greys", vmin=0, vmax=2)
im = axs[1].imshow(att.values, cmap="viridis")
for ax, title in zip(axs, ["(a) edges (dark: in both folds)", "(b) mean attention weight"]):
    ax.set_xticks(range(len(zones))); ax.set_xticklabels(zones, rotation=90, fontsize=7)
    ax.set_yticks(range(len(zones))); ax.set_yticklabels(zones, fontsize=7); ax.set_title(title)
    for b in [4.5, 7.5]:
        ax.axhline(b, color="w" if ax is axs[1] else "#C8553D", lw=.8); ax.axvline(b, color="w" if ax is axs[1] else "#C8553D", lw=.8)
plt.colorbar(im, ax=axs[1], fraction=.046)
fig.suptitle("E20 — Graph learned by the TCN-GAT: which zones each zone reads at time t (L1–L5 | B1–B3 | F1–F7)", y=1.0)
fig.tight_layout(); savefig(fig, FIG, "E20_learned_graph"); plt.show()
cross = [(i, j, float(att.loc[i, j])) for i in zones for j in zones if adj.loc[i, j] > 0 and P["city"][i] != P["city"][j]]
edges = pd.DataFrame(cross, columns=["to", "from", "attention"]).sort_values("attention", ascending=False)
edges.to_csv(OUT / "learned_cross_city_edges.csv", index=False)
print("strongest learned cross-city edges:"); print(edges.head(10).to_string(index=False))
same = np.mean([att.loc[i, j] for i in zones for j in zones if adj.loc[i, j] > 0 and P["city"][i] == P["city"][j]])
print(f"mean attention per edge: same city {same:.3f}, cross city {edges.attention.mean():.3f}")"""))

cells.append(M(r"""## 3. Injection protocol (D54)
Each event copies a signature seen in the data (`src/inject.py`). Events are placed round-robin over the types until the injected zone-steps reach the target share of clean zone-time. Each event blocks its zones for ±12 h, and multi-city events block every zone for ±3 h, so injected events do not touch each other. A whole-city fill is followed by a zero fill with probability 0.5: the compound A2 → A1 pattern of C05/C06 and C12."""))
cells.append(C(r"""ZMAP = INJ.zone_map(res["data"], B.SOUTH, R1.CITY_SHORT)
INJECTOR = INJ.Injector(res["data"], res["exp"], CLEAN, ZMAP)
def make_dataset(rate, seed):
    return INJECTOR.sample(np.ones(len(P["rho"].index), bool), rate, np.random.default_rng([int(round(rate * 1000)), seed]))
ex_data, ex_truth = make_dataset(0.03, 0)
print(len(ex_truth), "events at 3 %, seed 0")
display(ex_truth.groupby("type").agg(n=("event_id", "size"), median_h=("duration_h", "median"), zone_steps=("zone_steps", "sum"),
                                     mechanisms=("mechanism", lambda m: ", ".join(sorted(set(",".join(m).split(",")))))))
show = ex_truth[ex_truth.type.isin(INJ.TYPES)].groupby("type").head(1).set_index("type").loc[[t for t in INJ.TYPES if t in set(ex_truth.type)]]
fig, axs = plt.subplots(len(show), 1, figsize=(11, 1.7 * len(show)))
for ax, (typ, r) in zip(np.atleast_1d(axs), show.iterrows()):
    zs = r.zones.split(",")[:4]
    a, b = r.start - pd.Timedelta(hours=10), r.end_affected + pd.Timedelta(hours=10)
    for z in zs:
        c, col = ZMAP[z]
        ax.plot(res["data"][c][col][a:b], color="#bbb", lw=.8)
        ax.plot(ex_data[c][col][a:b], lw=.9, label=z)
    ax.axvspan(r.start, r.end, color=LABEL_COL.get(typ, "#F2A541"), alpha=.2)
    ax.set_title(f"{typ} · {r.mechanism} · {r.duration_h:.1f} h · {r.n_zones} zone(s) ({r.pattern})", fontsize=8)
    ax.set_ylabel("x (A)"); ax.legend(fontsize=6, ncol=4, loc="upper right"); ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b %H:%M"))
fig.suptitle("E21 — Injected signatures (grey = original series)", y=1.0)
fig.tight_layout(); savefig(fig, FIG, "E21_injected_signatures"); plt.show()"""))

cells.append(M(r"""## 4. Benchmark runs (resumable)
For each rate and seed: inject, rerun the whole pipeline, score. Results go to `runs/` immediately."""))
cells.append(C(r"""bench = B.Benchmark(res["raw"], P, det_real, LGB, GM, gb_backend="lightgbm", log=False)
todo = [(r, s) for r in RATES for s in SEEDS]
t_start = time.time(); done = 0
for k, (rate, seed) in enumerate(todo):
    tag = f"r{int(round(rate * 100)):02d}_s{seed:02d}"
    if (RUNS / f"{tag}_info.json").exists():
        continue
    t = time.time()
    data_inj, truth = make_dataset(rate, seed)
    out = bench.run(data_inj, truth, seed=seed, baselines=BASELINES, family_ablation=(rate == FAMILY_ABLATION_RATE))
    truth.to_csv(RUNS / f"{tag}_truth.csv", index=False)
    out["detection"].to_csv(RUNS / f"{tag}_detection.csv", index=False)
    out["auc"].to_csv(RUNS / f"{tag}_auc.csv", index=False)
    out["events"].to_csv(RUNS / f"{tag}_events.csv", index=False)
    out["pred"].to_csv(RUNS / f"{tag}_pred.csv", index=False)
    (RUNS / f"{tag}_info.json").write_text(json.dumps({**out["info"], "rate": rate, "seed": seed}, default=str))
    done += 1
    left = sum(1 for r, s in todo if not (RUNS / f"r{int(round(r * 100)):02d}_s{s:02d}_info.json").exists())
    print(f"{tag}: {len(truth)} events, {time.time() - t:.0f} s | {left} left, about {left * (time.time() - t_start) / done / 60:.0f} min", flush=True)
print("all runs present:", all((RUNS / f"r{int(round(r * 100)):02d}_s{s:02d}_info.json").exists() for r, s in todo))"""))

cells.append(C(r"""def load(kind):
    out = []
    for r, s in todo:
        f = RUNS / f"r{int(round(r * 100)):02d}_s{s:02d}_{kind}.csv"
        if f.exists():
            out.append(pd.read_csv(f).assign(rate=r, seed=s))
    return pd.concat(out, ignore_index=True)
DET, AUC, EV, TRUTH = load("detection"), load("auc"), load("events"), load("truth")
print(len(DET.groupby(["rate", "seed"])), "runs;", len(TRUTH), "injected events;", TRUTH.type.value_counts().to_dict())
def ms(x):
    x = pd.Series(x).dropna()
    return f"{x.mean():.3f} ± {x.std(ddof=1):.3f}" if len(x) > 1 else (f"{x.mean():.3f}" if len(x) else "n/a")"""))

cells.append(M(r"""## 5. Detection (Table 5, Fig 9)
- Test period (Jul 2023 – May 2024), mean ± standard deviation over seeds.
- **F1 follows the guide's eq. 17:** a predicted event counts if it overlaps an injected event in time, including the restoration tail.
- **F1_zone_strict** also requires a shared zone. The two differ mainly because a multi-city event shifts the region median g, which makes the *unaffected* city look anomalous at the city level. Per-type recall is zone-strict.
- Wilcoxon signed-rank test over seeds: ours vs the best baseline."""))
cells.append(C(r"""ORDER = ["ours (rules + detector)", "rules only (rule engine v1)", B.MAIN, "TCN-GAT, hierarchy, multi-scale", "single scale (raw band)",
         "no hierarchy (flat residual)", "LGB nowcast (raw, hierarchy)", "TCN, no graph (raw, hierarchy)", "TCN-GAT (raw, hierarchy)",
         "STL + MAD", "Isolation Forest", "LOF"]
BASE = ["rules only (rule engine v1)", "STL + MAD", "Isolation Forest", "LOF"]
dt = DET[DET.period == "test"].merge(AUC[AUC.period == "test"], on=["method", "period", "rate", "seed"], how="left")
rows = []
for rate in RATES:
    d = dt[dt.rate == rate]
    for m in [o for o in ORDER if o in set(d.method)]:
        g = d[d.method == m]
        rows.append(dict(rate=f"{rate:.0%}", method=m, F1=ms(g.f1), precision=ms(g.precision), recall=ms(g.recall), F1_zone_strict=ms(g.f1_zone), AUC_PR=ms(g.auc_pr),
                         start_err_min=round(g.start_err_min.median(), 0), F1_mean=g.f1.mean()))
table5 = pd.DataFrame(rows)
tests = []
for rate in RATES:
    d = dt[dt.rate == rate]
    best = d[d.method.isin(BASE)].groupby("method").f1.mean().idxmax()
    a = d[d.method == "ours (rules + detector)"].set_index("seed").f1; b = d[d.method == best].set_index("seed").f1
    a, b = a.align(b, join="inner")
    p = wilcoxon(a, b).pvalue if len(a) >= 6 and (a != b).any() else np.nan
    tests.append(dict(rate=f"{rate:.0%}", best_baseline=best, ours_F1=a.mean(), baseline_F1=b.mean(), wilcoxon_p=p, n_seeds=len(a)))
table5.drop(columns="F1_mean").to_csv(OUT / "table5_detection.csv", index=False)
pd.DataFrame(tests).to_csv(OUT / "table5_wilcoxon.csv", index=False)
display(table5.drop(columns="F1_mean")); display(pd.DataFrame(tests).round(4))

rec_cols = [c for c in DET.columns if c.startswith("recall_")]
rec = dt[dt.method.isin(["ours (rules + detector)", "rules only (rule engine v1)", B.MAIN, "TCN-GAT, hierarchy, multi-scale", "LGB nowcast (raw, hierarchy)", "single scale (raw band)"])]
rec_t = rec.groupby(["rate", "method"])[rec_cols].mean().round(3)
rec_t.to_csv(OUT / "detection_recall_by_type.csv"); display(rec_t)

fig, axs = plt.subplots(1, len(RATES), figsize=(5 * len(RATES), 4.2), sharey=True, squeeze=False)
for ax, rate in zip(axs[0], RATES):
    d = dt[dt.rate == rate]; ms_ = [o for o in ORDER if o in set(d.method)]
    for i, m in enumerate(ms_):
        g = d[d.method == m]
        col = "#C8553D" if m.startswith("ours") else ("#2F6690" if m in BASE else "#7B5EA7")
        ax.errorbar(g.f1.mean(), i, xerr=g.f1.std(ddof=1) if len(g) > 1 else 0, fmt="o", color=col, ms=5, capsize=2)
        ax.errorbar(g.auc_pr.mean(), i + 0.25, xerr=g.auc_pr.std(ddof=1) if len(g) > 1 else 0, fmt="s", color=col, mfc="white", ms=4, capsize=2)
    ax.set_yticks(range(len(ms_))); ax.set_yticklabels(ms_, fontsize=7); ax.invert_yaxis(); ax.set_xlim(0, 1)
    ax.set_title(f"{rate:.0%} contamination"); ax.set_xlabel("event F1 (●) and step AUC-PR (□)")
fig.suptitle("Fig 9 — Detection on injected events (test period, mean ± sd over seeds; red = ours, blue = baselines, purple = ablations)", y=1.02)
fig.tight_layout(); savefig(fig, FIG, "fig9_detection"); plt.show()"""))

cells.append(M(r"""## 6. Attribution (Table 6, Figs 10–11)
- Scored on injected **typed** events that the full method detected. Each event takes the label of its best-overlapping predicted item. End-to-end numbers, which count missed events as wrong, are reported too.
- **β** for fusion (eq. 16) is tuned on the training period (Sep 2022 – Jun 2023), pooled over seeds at each rate, by macro-F1. It is then frozen for the test period (D56).
- On injected data, A1, G1 and G2 are no longer rare, so fusion is reported both with and without NB3's low-support abstention (D50)."""))
cells.append(C(r"""CL = EM.EVENT_CLASSES
typed = EV[EV.type.isin(INJ.TYPED)].copy()
det_ev = typed[typed.detected].reset_index(drop=True)
P_q = det_ev[[f"q_{c}" for c in CL]].to_numpy(float)
P_f = det_ev[[f"f_{c}" for c in CL]].to_numpy(float)
P_fn = det_ev[[f"fn_{c}" for c in CL]].to_numpy(float)
BETAS = np.round(np.arange(0, 1.01, 0.1), 1)
beta_rows, BETA = [], {}
for rate in RATES:
    tr = (det_ev.rate == rate) & (det_ev.period == "train")
    for b in BETAS:
        for ab in [True, False]:
            p = B.fused(det_ev[tr], b, abstain_low=("A1", "G1", "G2") if ab else ())
            beta_rows.append(dict(rate=rate, beta=b, abstain=ab, **B.attribution_scores(det_ev.type[tr].to_numpy(), probs=p)))
bt = pd.DataFrame(beta_rows)
for rate in RATES:
    for ab in [True, False]:
        g = bt[(bt.rate == rate) & (bt.abstain == ab)]
        BETA[(rate, ab)] = float(g.loc[(g.macro_f1 - 1e-9 * (g.beta - 0.5).abs()).idxmax(), "beta"])
bt.to_csv(OUT / "beta_tuning_train_period.csv", index=False)
print("tuned beta (train period, by macro-F1):", {f"{r:.0%}, abstain={a}": b for (r, a), b in BETA.items()})

def labelers(sub):
    yield "majority vote (rules)", None, np.where(sub.mv.isin(CL), sub.mv, "N")
    yield "label model q", sub[[f"q_{c}" for c in CL]].to_numpy(float), None
    yield "end model f, no detector features", sub[[f"fn_{c}" for c in CL]].to_numpy(float), None
    yield "end model f, all features", sub[[f"f_{c}" for c in CL]].to_numpy(float), None
    r = sub.rate.iloc[0]
    yield "fusion, no detector features (β*)", B.fused(sub, BETA[(r, True)], f_prefix="fn_"), None
    yield "fusion (β*, D50 abstention)", B.fused(sub, BETA[(r, True)]), None
    yield "fusion (β*, no abstention)", B.fused(sub, BETA[(r, False)], abstain_low=()), None

rows = []
for (rate, seed), sub in det_ev[det_ev.period == "test"].groupby(["rate", "seed"]):
    for name, probs, labels in labelers(sub):
        rows.append(dict(rate=rate, seed=seed, labeler=name, **B.attribution_scores(sub.type.to_numpy(), probs=probs, labels=labels)))
att = pd.DataFrame(rows)
e2e = []
for (rate, seed), sub in typed[typed.period == "test"].groupby(["rate", "seed"]):
    d = sub[sub.detected]
    lab = pd.Series("missed", index=sub.index)
    if len(d):
        lab.loc[d.index] = np.array(CL)[B.fused(d, BETA[(rate, True)]).argmax(1)]
    e2e.append(dict(rate=rate, seed=seed, detected_share=sub.detected.mean(), end_to_end_accuracy=(lab == sub.type).mean()))
e2e = pd.DataFrame(e2e)
t6 = []
for rate in RATES:
    for name in att.labeler.unique():
        g = att[(att.rate == rate) & (att.labeler == name)]
        t6.append(dict(rate=f"{rate:.0%}", labeler=name, macro_F1=ms(g.macro_f1), accuracy=ms(g.accuracy), ECE=ms(g.ece) if "ece" in g else "n/a",
                       Brier=ms(g.brier) if "brier" in g else "n/a", **{f"F1_{c}": round(g[f"f1_{c}"].mean(), 3) for c in INJ.TYPED}))
table6 = pd.DataFrame(t6)
table6.to_csv(OUT / "table6_attribution.csv", index=False); e2e.to_csv(OUT / "end_to_end.csv", index=False)
display(table6)
display(e2e.groupby("rate")[["detected_share", "end_to_end_accuracy"]].agg(["mean", "std"]).round(3))"""))

cells.append(C(r"""r0 = 0.03 if 0.03 in RATES else RATES[0]
sub = det_ev[(det_ev.rate == r0) & (det_ev.period == "test")]
pf = B.fused(sub, BETA[(r0, True)]); lab_p = np.array(CL)[pf.argmax(1)]
cm = pd.crosstab(pd.Categorical(sub.type, categories=INJ.TYPED), pd.Categorical(lab_p, categories=CL), dropna=False)
cm.to_csv(OUT / "fig10_confusion_fused.csv")
fig, axs = plt.subplots(1, 2, figsize=(13, 4.6), gridspec_kw=dict(width_ratios=[1.1, 1]))
norm = cm.div(cm.sum(axis=1).replace(0, 1), axis=0)
axs[0].imshow(norm.values, cmap="Blues", vmin=0, vmax=1)
axs[0].set_xticks(range(len(CL))); axs[0].set_xticklabels(CL); axs[0].set_yticks(range(len(INJ.TYPED))); axs[0].set_yticklabels(INJ.TYPED)
for (i, j), v in np.ndenumerate(cm.values):
    if v: axs[0].text(j, i, v, ha="center", va="center", fontsize=7, color="w" if norm.values[i, j] > .6 else "k")
axs[0].set_xlabel("fused label (β*)"); axs[0].set_ylabel("injected type"); axs[0].set_title(f"Fig 10 — Attribution confusion, {r0:.0%}, test period (pooled seeds)")
bins = np.linspace(0, 1, 11)
for name, probs, col in [("label model q", sub[[f"q_{c}" for c in CL]].to_numpy(float), "#9AA0A6"),
                         ("end model f", sub[[f"f_{c}" for c in CL]].to_numpy(float), "#7B5EA7"), ("fusion p (β*)", pf, "#C8553D")]:
    conf = probs.max(1); corr = np.array(CL)[probs.argmax(1)] == sub.type.to_numpy()
    k = np.clip(np.digitize(conf, bins) - 1, 0, 9)
    xs = [conf[k == i].mean() for i in range(10) if (k == i).sum() >= 5]; ys = [corr[k == i].mean() for i in range(10) if (k == i).sum() >= 5]
    axs[1].plot(xs, ys, "o-", color=col, label=f"{name} (ECE {LM.ece(conf, corr):.3f})")
axs[1].plot([0, 1], [0, 1], color="#bbb", lw=.8, ls="--"); axs[1].set_xlabel("confidence"); axs[1].set_ylabel("accuracy"); axs[1].legend(fontsize=7)
axs[1].set_title(f"Fig 11 — Reliability, {r0:.0%}, test period")
fig.tight_layout(); savefig(fig, FIG, "fig10_11_attribution"); plt.show()"""))

cells.append(M(r"""## 7. Ablations (Table 7)
- **(a) Pipeline:** rules (majority vote) → + label model → + end model without detector features → + detector features. These are scored on attribution, at the 3 % rate, in the test period.
- **(b) Detector design** (detection on the same runs):
  - hierarchy vs flat residual;
  - multi-scale vs single scale;
  - learned graph (TCN-GAT) vs no graph (TCN);
  - LightGBM nowcast (all zones, no learned edges) vs forecast.
  - **U_SHOCK recall** is the F29 test: does a predictor that sees neighbours explain shared shocks away?
- **(c) Rule families:** the label model refitted without one family at a time."""))
cells.append(C(r"""r0 = FAMILY_ABLATION_RATE if FAMILY_ABLATION_RATE in RATES else RATES[0]
a = att[att.rate == r0]
pipe = ["majority vote (rules)", "label model q", "fusion, no detector features (β*)", "fusion (β*, D50 abstention)"]
t7a = pd.DataFrame([dict(stage=s, macro_F1=ms(a[a.labeler == s].macro_f1), ECE=ms(a[a.labeler == s].ece) if s != pipe[0] else "n/a") for s in pipe])
d = dt[dt.rate == r0]
abl = [("hierarchy, multi-scale (ours)", B.MAIN), ("single scale (raw band)", "single scale (raw band)"),
       ("no hierarchy (flat residual)", "no hierarchy (flat residual)"), ("LGB nowcast, raw (all zones, no learned edges)", "LGB nowcast (raw, hierarchy)"),
       ("TCN, no graph, raw", "TCN, no graph (raw, hierarchy)"), ("TCN-GAT, learned graph, raw", "TCN-GAT (raw, hierarchy)"),
       ("TCN-GAT, learned graph, multi-scale", "TCN-GAT, hierarchy, multi-scale")]
t7b = pd.DataFrame([dict(variant=n, F1=ms(d[d.method == m].f1), AUC_PR=ms(d[d.method == m].auc_pr),
                         recall_U_SHOCK=ms(d[d.method == m].recall_U_SHOCK), recall_U_PARTIAL=ms(d[d.method == m].recall_U_PARTIAL),
                         recall_A2=ms(d[d.method == m].recall_A2), recall_G3=ms(d[d.method == m].recall_G3)) for n, m in abl if m in set(d.method)])
fam_cols = [c for c in EV.columns if c.startswith("lm_without_")]
t7c = []
if fam_cols:
    sub = det_ev[(det_ev.rate == r0) & (det_ev.period == "test")]
    base = []
    for seed, g in sub.groupby("seed"):
        base.append(B.attribution_scores(g.type.to_numpy(), probs=g[[f"q_{c}" for c in CL]].to_numpy(float))["macro_f1"])
    t7c.append(dict(label_model="all rule families", macro_F1=ms(base)))
    for c in fam_cols:
        vals = [B.attribution_scores(g.type.to_numpy(), labels=g[c].fillna("N").to_numpy())["macro_f1"] for seed, g in sub.groupby("seed")]
        t7c.append(dict(label_model=f"without {c.replace('lm_without_', '')}", macro_F1=ms(vals)))
t7c = pd.DataFrame(t7c)
for name, t in [("a_pipeline", t7a), ("b_detector", t7b), ("c_rule_families", t7c)]:
    t.to_csv(OUT / f"table7{name}.csv", index=False)
display(t7a); display(t7b); display(t7c)"""))

cells.append(M(r"""## 8. Threshold sensitivity (guide ablation 6)
The rules and the label model are rerun with one threshold changed: the dead threshold ε (0.02, 0.05, 0.1), the hold length (4, 6, 12 steps) or the simultaneity tolerance τ (0, 10, 20 min). The injected datasets are the same as in §4 (3 %). U_PARTIAL recall is the F32 question: would a larger ε catch the partial outages?"""))
cells.append(C(r"""SENS = [("baseline", {}), ("eps 0.02", dict(eps=0.02)), ("eps 0.10", dict(eps=0.10)), ("hold 4", dict(hold=4)),
        ("hold 12", dict(hold=12)), ("tau 0 min", dict(tol_min=0)), ("tau 20 min", dict(tol_min=20))]
sr, sl = [], []
for seed in SENS_SEEDS:
    data_inj, truth = make_dataset(0.03, seed)
    for name, kw in SENS:
        f1, f2 = RUNS / f"sens_s{seed:02d}_{name.replace(' ', '_')}_det.csv", RUNS / f"sens_s{seed:02d}_{name.replace(' ', '_')}_lab.csv"
        if not f1.exists():
            t = time.time()
            d_, l_ = B.rules_sensitivity(res["raw"], data_inj, truth, CLEAN, P["rho"].index, list(P["rho"].columns), **kw)
            d_.to_csv(f1, index=False); l_.to_csv(f2, index=False); print(f"sensitivity seed {seed} {name}: {time.time() - t:.0f} s", flush=True)
        sr.append(pd.read_csv(f1).assign(config=name, seed=seed)); sl.append(pd.read_csv(f2).assign(config=name, seed=seed))
sr, sl = pd.concat(sr), pd.concat(sl)
rows = []
for name, _ in SENS:
    d = sr[(sr.config == name) & (sr.period == "test")]; l = sl[(sl.config == name) & (sl.period == "test")]
    mf = [B.attribution_scores(g.type.to_numpy(), labels=g.label.to_numpy())["macro_f1"] for _, g in l.groupby("seed")]
    rows.append(dict(config=name, rules_F1=ms(d.f1), rules_recall=ms(d.recall), recall_U_PARTIAL=ms(d.recall_U_PARTIAL),
                     recall_G3=ms(d.recall_G3), recall_G4=ms(d.recall_G4), recall_A2=ms(d.recall_A2), recall_A3=ms(d.recall_A3), label_model_macro_F1=ms(mf)))
table7d = pd.DataFrame(rows); table7d.to_csv(OUT / "table7d_threshold_sensitivity.csv", index=False)
display(table7d)"""))

cells.append(M(r"""## 9. Hard negatives on the real data
The guide asks for false alarms on ordinary but unusual days. The table gives the detector flag rate (Z > γ) on rule-negative zone-steps of the real, uninjected data, by day type. A ratio well above 1 means the detector confuses that behaviour with anomalies."""))
cells.append(C(r"""cal = D.calendar(P["rho"].index)
day = pd.Series(np.select([cal.eid == 1, cal.holiday == 1, cal.ramadan == 1, cal.weekend == 1], ["Eid", "national holiday", "Ramadan", "weekend"], "ordinary weekday"), index=P["rho"].index)
hn = []
for name, pr in [("LGB forecast (ours)", PRED["LGB forecast"]), ("TCN-GAT (learned graph)", PRED["TCN-GAT (learned graph)"])]:
    Z = D.zone_max_score(P, D.level_scores(P, P["rho"] - pr))
    gam = B.gamma_of(P, Z)
    w = 2 * D.SPILL_STEPS + 1
    near = P["mask"].astype(float).rolling(w, center=True, min_periods=1).max() > 0
    neg = (~near) & Z.notna()
    flag = (Z > gam) & neg
    for cat_ in ["ordinary weekday", "weekend", "Ramadan", "national holiday", "Eid"]:
        sel = (day == cat_).to_numpy()[:, None] & neg.to_numpy()
        hn.append(dict(detector=name, day_type=cat_, zone_steps=int(sel.sum()), flag_rate=flag.to_numpy()[sel].mean() if sel.any() else np.nan))
hn = pd.DataFrame(hn)
hn["ratio_to_ordinary"] = hn.flag_rate / hn.groupby("detector").flag_rate.transform(lambda s: s.iloc[0])
hn.round(4).to_csv(OUT / "hard_negatives.csv", index=False); display(hn.round(4))"""))

cells.append(M("## 10. Summary (copied into docs/results_summary.md §9)"))
cells.append(C(r"""summary = dict(
    device=DEVICE, lightgbm_version=lightgbm.__version__, torch_version=torch.__version__, colab=IN_COLAB, quick=QUICK,
    rates=RATES, seeds=SEEDS, runs=int(len(DET.groupby(["rate", "seed"]))), injected_events=int(len(TRUTH)),
    injected_by_type=TRUTH.type.value_counts().to_dict(),
    predictor_MAE=pred_cmp[pred_cmp.period == "all"].set_index("predictor").MAE.to_dict(),
    hierarchy_all=hier_cmp[hier_cmp.kind == "all"].set_index("predictor").correct.to_dict(),
    detection_F1_test={f"{r:.0%} | {m}": round(float(dt[(dt.rate == r) & (dt.method == m)].f1.mean()), 3) for r in RATES for m in ORDER if m in set(dt.method)},
    attribution_macroF1_test={f"{r:.0%} | {l}": round(float(att[(att.rate == r) & (att.labeler == l)].macro_f1.mean()), 3) for r in RATES for l in att.labeler.unique()},
    beta={f"{r:.0%} | abstain={a}": b for (r, a), b in BETA.items()},
    runtime_min=round((time.time() - T0) / 60, 1))
summary = json.loads(json.dumps(summary, default=str))
(OUT / "summary.json").write_text(json.dumps(summary, indent=2))
summary"""))

cells.append(M("""## 11. Colab only: push every output to Google Drive
Colab caches writes to the mounted Drive and can leave files unsent. `flush_and_unmount` forces the upload. Afterwards, save the notebook (Ctrl+S) so the executed copy reaches Drive too."""))
cells.append(C(r"""if IN_COLAB:
    drive.flush_and_unmount()
    print("Drive flushed and unmounted: now press Ctrl+S to save this notebook to Drive")
else:
    print("local run: nothing to flush")"""))

nb = new_notebook(cells=cells)
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nb.metadata["accelerator"] = "GPU"
nb.metadata["colab"] = {"provenance": [], "gpuType": "T4"}
nbf.write(nb, sys.argv[1])
print("wrote", sys.argv[1])
