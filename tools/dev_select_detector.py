"""Development selection of the main detector and of every detector's event formation (D60). Run before NB4.

    python tools/dev_select_detector.py            # first grid, ~35 min on 8 CPU cores; writes results/benchmark_v1/dev/
    python tools/dev_select_detector.py --extend   # adds GRID_EXT (larger smoothing / thresholds / gaps) and reselects

Development datasets use seeds 100-104 (3 % x 3, 1 %, 7 %); the benchmark uses seeds 0-9, so nothing here touches
the datasets that are reported. For every tuned detector (the main candidates and the baselines; ablations inherit the main detector's setting), the event formation
(score smoothing w, threshold percentile q, merge gap) is chosen on these datasets by its own event F1 alone
(eq. 17, both periods pooled). The main detector is then the candidate (MAIN_CANDIDATES) with the best F1 of the
full method (rules + its detector-only candidates) at its chosen setting. The scoring area is the rule-based clean
region for every detector (D60). Output: dev_selection.json, read by NB4.
"""
import sys, time, json, pickle, itertools
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import numpy as np, pandas as pd
import rules_v1 as R1, detector as D, end_model as EM, graph_model as G, benchmark as B, inject as INJ

DEV = [(0.03, 100), (0.03, 101), (0.03, 102), (0.01, 103), (0.07, 104)]
W, Q, GAP = [1, 3, 6], [99.0, 99.5, 99.8], [1, 3]
GRID = list(itertools.product(W, Q, GAP))
# the first grid's optimum sat on its upper edge for almost every detector, so it was extended upwards
GRID_EXT = (list(itertools.product([6, 12, 24], [99.8, 99.9, 99.95], [3, 6]))
            + list(itertools.product([24, 48], [99.8, 99.9, 99.95, 99.98], [6, 12])))   # second extension: the optimum was again on the edge
OUT = ROOT / "results" / "benchmark_v1" / "dev"
MOD = ROOT / "results" / "benchmark_v1" / "models"
GRAPH_FILES = {"TCN": "tcn.pt", "TCN-GAT": "tcn_gat.pt", "LGB + TCN": "hybrid_tcn.pt", "LGB + GAT": "hybrid_gat.pt"}


def neg_mask(P):
    """Zone-steps away from rule states (own zone and multi-zone): where gamma is estimated (as benchmark.gamma_of)."""
    w = 2 * D.SPILL_STEPS + 1
    M = P["mask"].astype(float)
    near_own = M.rolling(w, center=True, min_periods=1).max() > 0
    near_multi = (M.sum(axis=1) >= 2).astype(float).rolling(w, center=True, min_periods=1).max() > 0
    return ((~near_own) & (~near_multi.to_numpy()[:, None])).to_numpy()


def grid_eval(P, Z0, zr, ev, truth, scope, tmask, index, cols, tag, grid, w_auc):
    fold = index >= D.SPLIT
    neg = neg_mask(P)
    empty = pd.DataFrame(columns=zr.columns)
    rows, arows = [], []
    for k, z0 in Z0.items():
        for w in sorted({g[0] for g in grid} | set(w_auc)):
            zw = B.smooth_score(z0, w); vals = zw.to_numpy()
            if w in w_auc:
                for per, pm in (("train", ~fold), ("test", fold)):
                    arows.append(dict(tag=tag, detector=k, w=w, period=per, auc_pr=B.step_auc(vals, tmask, scope, pm)))
            for q in sorted({g[1] for g in grid if g[0] == w}):
                gam = float(np.nanpercentile(np.where(neg & np.isfinite(vals), vals, np.nan), q))
                for gap in sorted({g[2] for g in grid if g[0] == w and g[1] == q}):
                    alone = EM.detector_items(P, zw, gam, empty, max_gap=gap)
                    dso = EM.detector_items(P, zw, gam, zr, max_gap=gap)
                    full = pd.concat([ev[["start", "end", "zones"]], dso[["start", "end", "zones"]] if len(dso) else None], ignore_index=True)
                    for per, pm in (("train", ~fold), ("test", fold)):
                        for what, pr in (("alone", alone), ("rules + detector", full)):
                            pr = pr[["start", "end", "zones"]].reset_index(drop=True) if len(pr) else pd.DataFrame(columns=["start", "end", "zones"])
                            m = B.detection_metrics(pr, truth, scope, index, cols, pm)
                            rows.append(dict(tag=tag, detector=k, w=w, q=q, gap=gap, what=what, period=per, n_det_only=len(dso),
                                             **{c: m[c] for c in ("n_pred", "n_true", "precision", "recall", "f1", "precision_zone",
                                                                  "recall_zone", "f1_zone", "recall_U_SHOCK", "recall_U_PARTIAL")}))
    return rows, arows


def select(det, real):
    """Best setting per detector by mean F1 alone; main = best candidate by mean F1 of rules + detector."""
    key = ["detector", "w", "q", "gap"]
    alone = det[det.what == "alone"].groupby(key)[["f1", "f1_zone", "precision", "recall"]].mean().reset_index()
    alone = alone.sort_values(["detector", "f1", "f1_zone"], ascending=[True, False, False])
    best = alone.drop_duplicates("detector").set_index("detector")
    settings = {k: dict(w=int(r.w), q=float(r.q), gap=int(r.gap)) for k, r in best.iterrows()}
    full = det[det.what == "rules + detector"].groupby(key)[["f1", "f1_zone"]].mean().reset_index()
    cand = []
    for k in B.MAIN_CANDIDATES:
        if k not in settings:
            continue
        st = settings[k]
        r = full[(full.detector == k) & (full.w == st["w"]) & (full.q == st["q"]) & (full.gap == st["gap"])].iloc[0]
        cand.append(dict(detector=k, **st, f1_full=r.f1, f1_zone_full=r.f1_zone, f1_alone=best.at[k, "f1"]))
    cand = pd.DataFrame(cand).sort_values(["f1_full", "f1_zone_full"], ascending=False)
    default = alone[(alone.w == 1) & (alone.q == 99.5) & (alone.gap == 1)].set_index("detector")
    table = best.join(default[["f1"]].rename(columns={"f1": "f1_nb3_setting"}))
    rb = real.merge(pd.DataFrame([dict(detector=k, **v) for k, v in settings.items()]), on=key)
    table = table.join(rb.set_index("detector").n_real_candidates)
    return settings, cand, table


def main():
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    extend = "--extend" in sys.argv
    old = dict(det=pd.read_csv(OUT / "dev_detection_grid.csv"), auc=pd.read_csv(OUT / "dev_auc.csv"),
               real=pd.read_csv(OUT / "real_candidates_by_setting.csv")) if extend else None
    done = set(map(tuple, old["det"][["w", "q", "gap"]].drop_duplicates().to_numpy().tolist())) if extend else set()
    grid = [g for g in (GRID_EXT if extend else GRID) if (float(g[0]), float(g[1]), float(g[2])) not in {tuple(map(float, d)) for d in done}]
    w_auc = sorted({g[0] for g in grid} - (set(old["auc"].w) if extend else set()))
    print("settings to evaluate:", grid, flush=True)
    res = R1.build(ROOT / "data" / "raw" / "Data Morocco.xlsx")
    P = D.build_panel(res["data"], res["exp"], res["masks"], "south")
    LGB = pickle.load(open(MOD / "lightgbm_models.pkl", "rb"))
    GM = {k: G.load_models(MOD / f, P, device=G.default_device()) for k, f in GRAPH_FILES.items() if (MOD / f).exists()}
    bench = B.Benchmark(res["raw"], P, None, LGB, GM, log=False)
    CLEAN = bench.clean
    INJECTOR = INJ.Injector(res["data"], res["exp"], CLEAN, INJ.zone_map(res["data"], B.SOUTH, R1.CITY_SHORT))
    index, cols = P["rho"].index, list(P["rho"].columns)
    print("graph models:", list(GM), f"| setup {time.time() - t0:.0f} s", flush=True)

    # real data: number of detector-only candidates at every setting (the false-alarm budget on the real series)
    Zr, _ = bench.raw_scores(P, bench.predictions(P))
    Zr = {k: v for k, v in Zr.items() if k in B.TUNED}
    negr, budget = neg_mask(P), []
    for k, z0 in Zr.items():
        for w in sorted({g[0] for g in grid}):
            zw = B.smooth_score(z0, w); vals = zw.to_numpy()
            for q in sorted({g[1] for g in grid if g[0] == w}):
                gam = float(np.nanpercentile(np.where(negr & np.isfinite(vals), vals, np.nan), q))
                for gap in sorted({g[2] for g in grid if g[0] == w and g[1] == q}):
                    budget.append(dict(detector=k, w=w, q=q, gap=gap,
                                       n_real_candidates=len(EM.detector_items(P, zw, gam, res["zone_runs"], max_gap=gap))))
    real = pd.concat([old["real"], pd.DataFrame(budget)], ignore_index=True) if extend else pd.DataFrame(budget)
    real.to_csv(OUT / "real_candidates_by_setting.csv", index=False)
    print(f"real data done, {time.time() - t0:.0f} s", flush=True)

    rows, arows, rules_rows = [], [], []
    for rate, seed in DEV:
        t = time.time(); tag = f"r{int(round(rate * 100)):02d}_s{seed}"
        data_inj, truth = INJECTOR.sample(np.ones(len(index), bool), rate, np.random.default_rng([int(round(rate * 1000)), seed]))
        r = R1.build_from_data(res["raw"], data_inj)
        Pi = D.build_panel(r["data"], r["exp"], r["masks"], "south")
        ev = r["items"][(r["items"].system == "south") & r["items"].kind.isin(["dead", "fill"])].reset_index(drop=True)
        Z0, _ = bench.raw_scores(Pi, bench.predictions(Pi))
        Z0 = {k: v for k, v in Z0.items() if k in B.TUNED}
        tmask = B._span_mask(truth, index, cols, "end")
        scope = CLEAN.to_numpy() | B._span_mask(truth, index, cols, "end_affected")
        rr, aa = grid_eval(Pi, Z0, r["zone_runs"], ev, truth, scope, tmask, index, cols, tag, grid, w_auc)
        rows += rr; arows += aa
        fold = index >= D.SPLIT
        for per, pm in (("train", ~fold), ("test", fold)):       # reference: the rules alone
            m = B.detection_metrics(ev[["start", "end", "zones"]].reset_index(drop=True), truth, scope, index, cols, pm)
            rules_rows.append(dict(tag=tag, period=per, **{c: m[c] for c in ("n_pred", "precision", "recall", "f1", "f1_zone")}))
        pd.DataFrame(rules_rows).to_csv(OUT / "dev_rules_only.csv", index=False)
        print(f"  {tag}: evaluated", flush=True)
        print(f"{tag}: {len(truth)} events, {time.time() - t:.0f} s", flush=True)

    det_all = pd.concat([old["det"], pd.DataFrame(rows)], ignore_index=True) if extend else pd.DataFrame(rows)
    auc_all = pd.concat([old["auc"], pd.DataFrame(arows)], ignore_index=True) if extend else pd.DataFrame(arows)
    det_all.to_csv(OUT / "dev_detection_grid.csv", index=False); auc_all.to_csv(OUT / "dev_auc.csv", index=False)
    settings, cand, table = select(det_all, real)
    table.to_csv(OUT / "dev_best_settings.csv"); cand.to_csv(OUT / "dev_main_candidates.csv", index=False)
    sel = dict(main=cand.iloc[0].detector, settings=settings, dev_datasets=[f"{r:.0%} seed {s}" for r, s in DEV],
               grid=sorted(set(map(tuple, det_all[["w", "q", "gap"]].drop_duplicates().to_numpy().tolist()))),
               rules_only_f1=float(pd.DataFrame(rules_rows).f1.mean()), criterion="settings: mean event F1 alone (eq. 17); main: mean F1 of rules + detector",
               main_candidates=cand.round(4).to_dict("records"), graph_models=list(GM), seconds=round(time.time() - t0))
    (ROOT / "results" / "benchmark_v1" / "dev_selection.json").write_text(json.dumps(sel, indent=2))
    pd.set_option("display.width", 220)
    print(table.round(3)); print(cand.round(4)); print("main:", sel["main"])


if __name__ == "__main__":
    main()
