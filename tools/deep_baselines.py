"""Deep multivariate baselines GDN and USAD on the injection benchmark, added after the NB4 run (D82).

A review of Section 5 asked for at least one deep multivariate detector next to STL + MAD, Isolation Forest and LOF.
This script adds two, from two families: GDN (learned graph + attention forecasting; the closest published method to
our graph component) and USAD (adversarially trained autoencoders; reconstruction). Both are re-implemented in
src/deep_baselines.py with the authors' released settings.

    python tools/deep_baselines.py           # CPU; resumable (results/benchmark_v1/deep_baselines/runs)
    python tools/deep_baselines.py --quick   # 1 epoch each, 1 development and 1 test dataset (smoke test, separate folder)

1. Train both models on the real southern series, two-fold cross-fitted (as every predictor of NB4, D53/D54).
2. Development seeds 100-104 (tools/dev_select_detector.DEV, the same 48 settings): each baseline gets its own event
   formation, chosen by the same criterion as every tuned detector (mean event F1 alone, D60).
3. Test seeds 0-9 at 1 %, 3 %, 7 % (the NB4 datasets, regenerated and checked against runs/*_truth.csv): scored
   exactly as benchmark.Benchmark.run (primary F1, own-background-excluded F1, zone-strict F1, step AUC-PR, per-type
   recall, onset error).
4. Paired Wilcoxon tests over seeds against the stored NB4 rows (main detector, rules alone, rules + detector, and the
   classical baselines). Nothing about our method is changed or selected here (D63).
Outputs: results/benchmark_v1/deep_baselines/ (models in results/benchmark_v1/models/deep_baselines.pt).
"""
import sys, time, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "tools"))
import numpy as np, pandas as pd
import torch
from scipy.stats import wilcoxon
import rules_v1 as R1, detector as D, end_model as EM, benchmark as B, inject as INJ
import deep_baselines as DB
from dev_select_detector import DEV, GRID, GRID_EXT, grid_eval

QUICK = "--quick" in sys.argv
OUT = ROOT / "results" / "benchmark_v1" / ("deep_baselines_quick" if QUICK else "deep_baselines")
RUNS_NB4 = ROOT / "results" / "benchmark_v1" / "runs"
MODEL_FILE = ROOT / "results" / "benchmark_v1" / "models" / ("deep_baselines_quick.pt" if QUICK else "deep_baselines.pt")
TEST = [(r, s) for r in (0.01, 0.03, 0.07) for s in range(10)]
NAMES = ["GDN", "USAD"]
EMPTY3 = pd.DataFrame(columns=["start", "end", "zones"])
NB4_REF = {"main": B.V_GAT, "rules": "rules only (rule engine v1)", "ours": "ours (rules + detector)",
           "STL + MAD": "STL + MAD", "Isolation Forest": "Isolation Forest", "LOF": "LOF"}


def detect(P, z0, st):
    """The detector alone, as Benchmark.pipeline's DET."""
    S = B.smooth_score(z0, st["w"])
    gam = B.gamma_of(P, S, st["q"])
    empty = pd.DataFrame(columns=["system", "code", "start", "end"])
    return S, gam, EM.detector_items(P, S, gam, empty, max_gap=st["gap"])


def main():
    t0 = time.time()
    torch.set_num_threads(4)
    if QUICK:
        DB.GDN_CFG["epochs"] = 1; DB.USAD_CFG["epochs"] = 1
    (OUT / "runs").mkdir(parents=True, exist_ok=True)
    res = R1.build(ROOT / "data" / "raw" / "Data Morocco.xlsx")
    P = D.build_panel(res["data"], res["exp"], res["masks"], "south")
    index, cols = P["rho"].index, list(P["rho"].columns)
    fold = index >= D.SPLIT
    CLEAN = B.clean_region(P, None)
    INJECTOR = INJ.Injector(res["data"], res["exp"], CLEAN, INJ.zone_map(res["data"], B.SOUTH, R1.CITY_SHORT))

    # ------------------------------------------------------------ 1. models (real data, cross-fitted)
    if MODEL_FILE.exists():
        models = DB.load(MODEL_FILE, len(cols))
        hist = pd.read_csv(OUT / "training_history.csv")
        if models["GDN"][False][1] is None:
            # first run trained GDN on unscaled rho; the authors' pipeline min-max scales each sensor (D82):
            # retrain GDN only; USAD was trained on scaled inputs from the start and is kept
            print("GDN models were trained without min-max scaling: retraining GDN", flush=True)
            g, hg = DB.fit(P, device="cpu", seed=0, log=True, which=("GDN",))
            models["GDN"] = g["GDN"]
            hist = pd.concat([hist[hist.model != "GDN"], hg], ignore_index=True)
            DB.save(models, MODEL_FILE); hist.to_csv(OUT / "training_history.csv", index=False)
    else:
        models, hist = DB.fit(P, device="cpu", seed=0, log=True)
        DB.save(models, MODEL_FILE); hist.to_csv(OUT / "training_history.csv", index=False)
    print(f"models ready ({time.time() - t0:.0f} s)", flush=True)

    # ------------------------------------------------------------ 2. development seeds: own event formation
    grid = sorted(set(GRID) | set(GRID_EXT))
    dev_sets = DEV[:1] if QUICK else DEV
    f_dev = OUT / "dev_detection_grid.csv"
    if f_dev.exists():
        dev_rows = pd.read_csv(f_dev)
    else:
        rows = []
        for rate, seed in dev_sets:
            t = time.time(); tag = f"r{int(round(rate * 100)):02d}_s{seed}"
            data_inj, truth = INJECTOR.sample(np.ones(len(index), bool), rate, np.random.default_rng([int(round(rate * 1000)), seed]))
            r = R1.build_from_data(res["raw"], data_inj)
            Pi = D.build_panel(r["data"], r["exp"], r["masks"], "south")
            ev = r["items"][(r["items"].system == "south") & r["items"].kind.isin(["dead", "fill"])].reset_index(drop=True)
            tmask = B._span_mask(truth, index, cols, "end")
            scope = CLEAN.to_numpy() | B._span_mask(truth, index, cols, "end_affected")
            rr, _ = grid_eval(Pi, DB.scores(Pi, models), r["zone_runs"], ev, truth, scope, tmask, index, cols, tag, grid, [])
            rows += rr
            print(f"dev {tag}: {time.time() - t:.0f} s", flush=True)
        dev_rows = pd.DataFrame(rows); dev_rows.to_csv(f_dev, index=False)
    key = ["detector", "w", "q", "gap"]
    alone = dev_rows[dev_rows.what == "alone"].groupby(key)[["f1", "f1_zone", "precision", "recall"]].mean().reset_index()
    alone = alone.sort_values(["detector", "f1", "f1_zone"], ascending=[True, False, False])
    best = alone.drop_duplicates("detector").set_index("detector")
    settings = {k: dict(w=int(best.at[k, "w"]), q=float(best.at[k, "q"]), gap=int(best.at[k, "gap"])) for k in NAMES}
    dev_summary = {k: dict(**settings[k], f1_alone_dev=float(best.at[k, "f1"])) for k in NAMES}
    print("development:", dev_summary, flush=True)

    # ------------------------------------------------------------ 3. background: detections on the uninjected data
    Zr = DB.scores(P, models)
    bg, real_alarms = {}, {}
    for k in NAMES:
        _, _, d = detect(P, Zr[k], settings[k])
        bg[k] = d[["start", "end", "zones"]].reset_index(drop=True) if len(d) else EMPTY3
        real_alarms[k] = len(d)
    print("real-data alarms:", real_alarms, flush=True)

    # ------------------------------------------------------------ 4. test seeds (the NB4 datasets)
    test_sets = TEST[10:11] if QUICK else TEST
    for rate, seed in test_sets:
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
        Z0 = DB.scores(Pi, models)
        tmask = B._span_mask(truth, index, cols, "end")
        scope = CLEAN.to_numpy() | B._span_mask(truth, index, cols, "end_affected")
        rows = []
        for k in NAMES:
            st = settings[k]
            S, gam, d = detect(Pi, Z0[k], st)
            pr = d[["start", "end", "zones"]].reset_index(drop=True) if len(d) else EMPTY3
            hit = B.match_events(pr, bg[k].assign(end_affected=bg[k].end), need_zone=True) if len(pr) and len(bg[k]) else pd.DataFrame(columns=["p"])
            for per, pm in (("train", ~fold), ("test", fold)):
                m = B.detection_metrics(pr, truth, scope, index, cols, pm)
                m2 = B.detection_metrics(pr.drop(index=set(hit.p)).reset_index(drop=True), truth, scope, index, cols, pm)
                rows.append(dict(method=k, period=per, gamma=gam, w=st["w"], q=st["q"], gap=st["gap"], **m,
                                 n_pred_bgx=m2["n_pred"], precision_bgx=m2["precision"], recall_bgx=m2["recall"],
                                 f1_bgx=m2["f1"], f1_zone_bgx=m2["f1_zone"],
                                 auc_pr=B.step_auc(S.to_numpy(), tmask, scope, pm), rate=rate, seed=seed))
        pd.DataFrame(rows).to_csv(f, index=False)
        left = sum(1 for r_, s_ in test_sets if not (OUT / "runs" / f"r{int(round(r_ * 100)):02d}_s{s_:02d}_detection.csv").exists())
        print(f"{tag}: {time.time() - t:.0f} s | {left} left", flush=True)
    if QUICK:
        print("quick run done:", pd.read_csv(OUT / "runs" / "r03_s00_detection.csv")[["method", "period", "f1", "n_pred"]].to_string())
        return

    # ------------------------------------------------------------ 5. tables and tests
    det = pd.concat([pd.read_csv(OUT / "runs" / f"r{int(round(r * 100)):02d}_s{s:02d}_detection.csv") for r, s in TEST], ignore_index=True)
    det.to_csv(OUT / "test_detection.csv", index=False)
    te = det[det.period == "test"].copy()
    nb4 = pd.concat([pd.read_csv(RUNS_NB4 / f"r{int(round(r * 100)):02d}_s{s:02d}_detection.csv").assign(rate=r, seed=s) for r, s in TEST])
    nb4 = nb4[nb4.period == "test"]

    def ms(x):
        x = pd.Series(x).dropna()
        return f"{x.mean():.3f} ± {x.std(ddof=1):.3f}"
    tab, wil = [], []
    for rate in (0.01, 0.03, 0.07):
        g = te[te.rate == rate]
        for k in NAMES:
            h = g[g.method == k]
            tab.append(dict(rate=f"{rate:.0%}", method=k, setting=f"w {settings[k]['w']}, q {settings[k]['q']}, gap {settings[k]['gap']}",
                            F1=ms(h.f1), precision=ms(h.precision), recall=ms(h.recall), F1_zone_strict=ms(h.f1_zone),
                            AUC_PR=ms(h.auc_pr), F1_own_background_excluded=ms(h.f1_bgx), real_data_alarms=real_alarms[k],
                            recall_U_SHOCK=ms(h.recall_U_SHOCK), recall_U_PARTIAL=ms(h.recall_U_PARTIAL),
                            start_err_min=float(h.start_err_min.median()),
                            **{f"recall_{c}": ms(h[f"recall_{c}"]) for c in ("A1", "A2", "A3", "G1", "G2", "G3", "G4")}))
            a = h.set_index("seed")
            for ref, meth in NB4_REF.items():
                b = nb4[(nb4.rate == rate) & (nb4.method == meth)].set_index("seed").loc[a.index]
                for metric in ("f1", "f1_bgx", "f1_zone"):
                    d = b[metric] - a[metric]
                    p = float(wilcoxon(b[metric], a[metric]).pvalue) if (d != 0).any() else 1.0
                    wil.append(dict(rate=f"{rate:.0%}", baseline=k, reference=ref, metric=metric,
                                    reference_mean=round(b[metric].mean(), 4), baseline_mean=round(a[metric].mean(), 4),
                                    reference_wins=int((d > 0).sum()), ties=int((d == 0).sum()), wilcoxon_p=p, n_seeds=len(d)))
    tab, wil = pd.DataFrame(tab), pd.DataFrame(wil)
    tab.to_csv(OUT / "table_deep_baselines.csv", index=False); wil.to_csv(OUT / "wilcoxon_deep_baselines.csv", index=False)
    summary = dict(development=dev_summary, real_data_alarms=real_alarms, device="cpu", torch_version=torch.__version__,
                   gdn_cfg=DB.GDN_CFG, usad_cfg=DB.USAD_CFG,
                   training_seconds={f"{m} | fold {f}": round(float(g.seconds.iloc[0])) for (m, f), g in hist.groupby(["model", "train_fold"])},
                   epochs_run={f"{m} | fold {f}": int(g.epoch.max() + 1) for (m, f), g in hist.groupby(["model", "train_fold"])},
                   seconds=round(time.time() - t0),
                   test_f1={f"{r.rate} | {r.method}": r.F1 for r in tab.itertuples()},
                   test_f1_bgx={f"{r.rate} | {r.method}": r.F1_own_background_excluded for r in tab.itertuples()})
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(tab.to_string()); print(wil[wil.metric == "f1"].to_string())


if __name__ == "__main__":
    main()
