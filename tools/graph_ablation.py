"""No-graph ablation of the main detector, added after the NB4 run (D62).

NB4 compared the main detector (TCN-GAT, hierarchy, multi-scale) with a no-graph TCN only on the raw band. This
script adds the missing row: the same multi-scale hierarchical detector built on the TCN without the graph
(benchmark.V_TCN_MS), on exactly the datasets of NB4.

    python tools/graph_ablation.py          # ~1 min per dataset on 8 CPU cores; resumable (results/benchmark_v1/graph_ablation/runs)

1. Development seeds 100-104 (as tools/dev_select_detector.py, full grid of 48 settings): the no-graph TCN gets its
   own tuned event formation, chosen by the same criterion as every tuned detector (mean event F1 alone). The main
   detector is evaluated on the same grid as a reproduction check of dev_selection.json.
2. Test seeds 0-9 at 1 %, 3 %, 7 % (the NB4 datasets, regenerated from the same seeds and checked against
   runs/*_truth.csv): three rows, scored exactly as benchmark.Benchmark.run (primary F1, own-background-excluded
   F1, zone-strict F1, step AUC-PR, per-type recall):
   - the main detector, recomputed here (CPU) and compared with the stored NB4 rows (Colab, GPU);
   - the no-graph TCN with the main detector's event formation (the ablation: one thing changed);
   - the no-graph TCN with its own tuned event formation (fair-tuning check).
Outputs: results/benchmark_v1/graph_ablation/.
"""
import sys, time, json, itertools
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "tools"))
import numpy as np, pandas as pd
from scipy.stats import wilcoxon
import rules_v1 as R1, detector as D, end_model as EM, graph_model as G, benchmark as B, inject as INJ
from dev_select_detector import DEV, GRID, GRID_EXT, grid_eval

OUT = ROOT / "results" / "benchmark_v1" / "graph_ablation"
RUNS_NB4 = ROOT / "results" / "benchmark_v1" / "runs"
MOD = ROOT / "results" / "benchmark_v1" / "models"
TEST = [(r, s) for r in (0.01, 0.03, 0.07) for s in range(10)]
V_OWN = B.V_TCN_MS + " (own tuned event formation)"
EMPTY3 = pd.DataFrame(columns=["start", "end", "zones"])


def scores(P, GM):
    """Unsmoothed zone scores of the main detector and of its no-graph ablation (as Benchmark.raw_scores)."""
    Z = {}
    for v, k in ((B.V_GAT, "TCN-GAT"), (B.V_TCN_MS, "TCN")):
        E = P["rho"] - G.apply_graph_models(P, GM[k])
        Z[v] = D.zone_max_score(P, D.level_scores(P, E))
    return Z


def detect(P, z0, st):
    """The detector alone (no rule runs excluded), as Benchmark.pipeline's DET."""
    S = B.smooth_score(z0, st["w"])
    gam = B.gamma_of(P, S, st["q"])
    empty = pd.DataFrame(columns=["system", "code", "start", "end"])
    return S, gam, EM.detector_items(P, S, gam, empty, max_gap=st["gap"])


def main():
    t0 = time.time()
    (OUT / "runs").mkdir(parents=True, exist_ok=True)
    sel = json.loads((ROOT / "results" / "benchmark_v1" / "dev_selection.json").read_text())
    assert sel["main"] == B.V_GAT, sel["main"]
    st_main = {**B.DEFAULT_SETTING, **sel["settings"][B.V_GAT]}
    res = R1.build(ROOT / "data" / "raw" / "Data Morocco.xlsx")
    P = D.build_panel(res["data"], res["exp"], res["masks"], "south")
    dev = G.default_device()
    GM = {k: G.load_models(MOD / f, P, device=dev) for k, f in (("TCN", "tcn.pt"), ("TCN-GAT", "tcn_gat.pt"))}
    CLEAN = B.clean_region(P, None)
    INJECTOR = INJ.Injector(res["data"], res["exp"], CLEAN, INJ.zone_map(res["data"], B.SOUTH, R1.CITY_SHORT))
    index, cols = P["rho"].index, list(P["rho"].columns)
    fold = index >= D.SPLIT
    print(f"setup {time.time() - t0:.0f} s | device {dev} | main setting {st_main}", flush=True)

    # ------------------------------------------------------------ 1. development seeds: own event formation
    grid = sorted(set(GRID) | set(GRID_EXT))
    w_auc = sorted({g[0] for g in grid})
    f_dev = OUT / "dev_detection_grid.csv"
    if f_dev.exists():
        dev_rows = pd.read_csv(f_dev)
    else:
        rows = []
        for rate, seed in DEV:
            t = time.time(); tag = f"r{int(round(rate * 100)):02d}_s{seed}"
            data_inj, truth = INJECTOR.sample(np.ones(len(index), bool), rate, np.random.default_rng([int(round(rate * 1000)), seed]))
            r = R1.build_from_data(res["raw"], data_inj)
            Pi = D.build_panel(r["data"], r["exp"], r["masks"], "south")
            ev = r["items"][(r["items"].system == "south") & r["items"].kind.isin(["dead", "fill"])].reset_index(drop=True)
            tmask = B._span_mask(truth, index, cols, "end")
            scope = CLEAN.to_numpy() | B._span_mask(truth, index, cols, "end_affected")
            rr, _ = grid_eval(Pi, scores(Pi, GM), r["zone_runs"], ev, truth, scope, tmask, index, cols, tag, grid, [])
            rows += rr
            print(f"dev {tag}: {time.time() - t:.0f} s", flush=True)
        dev_rows = pd.DataFrame(rows); dev_rows.to_csv(f_dev, index=False)
    key = ["detector", "w", "q", "gap"]
    alone = dev_rows[dev_rows.what == "alone"].groupby(key)[["f1", "f1_zone", "precision", "recall"]].mean().reset_index()
    alone = alone.sort_values(["detector", "f1", "f1_zone"], ascending=[True, False, False])
    best = alone.drop_duplicates("detector").set_index("detector")
    st_own = dict(w=int(best.at[B.V_TCN_MS, "w"]), q=float(best.at[B.V_TCN_MS, "q"]), gap=int(best.at[B.V_TCN_MS, "gap"]))
    at_main = alone[(alone.w == st_main["w"]) & (alone.q == st_main["q"]) & (alone.gap == st_main["gap"])].set_index("detector")
    dev_summary = dict(own_setting_tcn=st_own, f1_alone_tcn_own=float(best.at[B.V_TCN_MS, "f1"]),
                       f1_alone_tcn_at_main_setting=float(at_main.at[B.V_TCN_MS, "f1"]),
                       main_best_setting_recomputed=dict(w=int(best.at[B.V_GAT, "w"]), q=float(best.at[B.V_GAT, "q"]), gap=int(best.at[B.V_GAT, "gap"])),
                       f1_alone_main_recomputed=float(best.at[B.V_GAT, "f1"]),
                       f1_alone_main_dev_selection=[c for c in sel["main_candidates"] if c["detector"] == B.V_GAT][0]["f1_alone"])
    print("development:", dev_summary, flush=True)
    configs = {B.V_GAT: (B.V_GAT, st_main), B.V_TCN_MS: (B.V_TCN_MS, st_main), V_OWN: (B.V_TCN_MS, st_own)}

    # ------------------------------------------------------------ 2. background: detections on the uninjected data
    Zr = scores(P, GM)
    bg, real_alarms = {}, {}
    for name, (v, st) in configs.items():
        _, _, d = detect(P, Zr[v], st)
        bg[name] = d[["start", "end", "zones"]].reset_index(drop=True) if len(d) else EMPTY3
        real_alarms[name] = len(d)
    print("real-data alarms:", real_alarms, flush=True)

    # ------------------------------------------------------------ 3. test seeds (the NB4 datasets)
    for rate, seed in TEST:
        tag = f"r{int(round(rate * 100)):02d}_s{seed:02d}"
        f = OUT / "runs" / f"{tag}_detection.csv"
        if f.exists():
            continue
        t = time.time()
        data_inj, truth = INJECTOR.sample(np.ones(len(index), bool), rate, np.random.default_rng([int(round(rate * 1000)), seed]))
        stored = pd.read_csv(RUNS_NB4 / f"{tag}_truth.csv", parse_dates=["start", "end", "end_affected"])
        assert len(stored) == len(truth) and (stored.zones.values == truth.zones.values).all() \
            and (stored.start.values == truth.start.values).all(), f"{tag}: injected data differ from NB4"
        r = R1.build_from_data(res["raw"], data_inj)
        Pi = D.build_panel(r["data"], r["exp"], r["masks"], "south")
        Z0 = scores(Pi, GM)
        tmask = B._span_mask(truth, index, cols, "end")
        scope = CLEAN.to_numpy() | B._span_mask(truth, index, cols, "end_affected")
        rows = []
        for name, (v, st) in configs.items():
            S, gam, d = detect(Pi, Z0[v], st)
            pr = d[["start", "end", "zones"]].reset_index(drop=True) if len(d) else EMPTY3
            hit = B.match_events(pr, bg[name].assign(end_affected=bg[name].end), need_zone=True) if len(pr) and len(bg[name]) else pd.DataFrame(columns=["p"])
            for per, pm in (("train", ~fold), ("test", fold)):
                m = B.detection_metrics(pr, truth, scope, index, cols, pm)
                m2 = B.detection_metrics(pr.drop(index=set(hit.p)).reset_index(drop=True), truth, scope, index, cols, pm)
                rows.append(dict(method=name, period=per, gamma=gam, w=st["w"], q=st["q"], gap=st["gap"], **m,
                                 n_pred_bgx=m2["n_pred"], precision_bgx=m2["precision"], recall_bgx=m2["recall"],
                                 f1_bgx=m2["f1"], f1_zone_bgx=m2["f1_zone"],
                                 auc_pr=B.step_auc(S.to_numpy(), tmask, scope, pm), rate=rate, seed=seed))
        pd.DataFrame(rows).to_csv(f, index=False)
        left = sum(1 for r_, s_ in TEST if not (OUT / "runs" / f"r{int(round(r_ * 100)):02d}_s{s_:02d}_detection.csv").exists())
        print(f"{tag}: {time.time() - t:.0f} s | {left} left", flush=True)

    # ------------------------------------------------------------ 4. tables
    det = pd.concat([pd.read_csv(OUT / "runs" / f"r{int(round(r * 100)):02d}_s{s:02d}_detection.csv") for r, s in TEST], ignore_index=True)
    det.to_csv(OUT / "test_detection.csv", index=False)
    te = det[det.period == "test"].copy()
    nb4 = pd.concat([pd.read_csv(RUNS_NB4 / f"r{int(round(r * 100)):02d}_s{s:02d}_detection.csv").assign(rate=r, seed=s) for r, s in TEST])
    nb4 = nb4[(nb4.period == "test") & (nb4.method == B.V_GAT)][["rate", "seed", "f1", "f1_bgx", "n_pred"]]
    chk = te[te.method == B.V_GAT].merge(nb4, on=["rate", "seed"], suffixes=("_here", "_nb4"))
    repro = dict(max_abs_diff_f1=float((chk.f1_here - chk.f1_nb4).abs().max()),
                 mean_abs_diff_f1=float((chk.f1_here - chk.f1_nb4).abs().mean()),
                 max_abs_diff_f1_bgx=float((chk.f1_bgx_here - chk.f1_bgx_nb4).abs().max()),
                 identical_runs=int(((chk.f1_here - chk.f1_nb4).abs() < 1e-9).sum()), runs=len(chk))
    chk.to_csv(OUT / "reproduction_main_detector.csv", index=False)
    print("reproduction of the stored main-detector rows:", repro, flush=True)

    def ms(x):
        x = pd.Series(x).dropna()
        return f"{x.mean():.3f} ± {x.std(ddof=1):.3f}"
    tab, wil = [], []
    for rate in (0.01, 0.03, 0.07):
        g = te[te.rate == rate]
        for name in configs:
            h = g[g.method == name]
            tab.append(dict(rate=f"{rate:.0%}", method=name, setting=f"w {int(h.w.iloc[0])}, q {h.q.iloc[0]}, gap {int(h.gap.iloc[0])}",
                            F1=ms(h.f1), precision=ms(h.precision), recall=ms(h.recall), F1_zone_strict=ms(h.f1_zone),
                            AUC_PR=ms(h.auc_pr), F1_own_background_excluded=ms(h.f1_bgx), real_data_alarms=real_alarms[name],
                            recall_U_SHOCK=ms(h.recall_U_SHOCK), recall_U_PARTIAL=ms(h.recall_U_PARTIAL), start_err_min=float(h.start_err_min.median())))
        a = g[g.method == B.V_GAT].set_index("seed")
        for name in (B.V_TCN_MS, V_OWN):
            b = g[g.method == name].set_index("seed").loc[a.index]
            for metric in ("f1", "f1_bgx", "auc_pr"):
                d = a[metric] - b[metric]
                p = float(wilcoxon(a[metric], b[metric]).pvalue) if (d != 0).any() else 1.0
                wil.append(dict(rate=f"{rate:.0%}", comparison=f"main detector vs {name}", metric=metric,
                                main=round(a[metric].mean(), 4), other=round(b[metric].mean(), 4),
                                main_wins=int((d > 0).sum()), ties=int((d == 0).sum()), wilcoxon_p=p, n_seeds=len(d)))
    tab, wil = pd.DataFrame(tab), pd.DataFrame(wil)
    tab.to_csv(OUT / "table_graph_ablation.csv", index=False); wil.to_csv(OUT / "wilcoxon_graph_ablation.csv", index=False)
    summary = dict(development=dev_summary, real_data_alarms=real_alarms, reproduction=repro, device=dev,
                   torch_version=__import__("torch").__version__, seconds=round(time.time() - t0),
                   test_f1={f"{r.rate} | {r.method}": r.F1 for r in tab.itertuples()},
                   test_f1_bgx={f"{r.rate} | {r.method}": r.F1_own_background_excluded for r in tab.itertuples()})
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(tab.to_string()); print(wil.to_string())


if __name__ == "__main__":
    main()
