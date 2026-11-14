# Forecasting test (NB5 section 4) on all 30 NB4 test datasets (D83).
# NB5 forecast on 4 injected datasets only (3 % seeds 0-2, 7 % seed 0), to keep the notebook short: each dataset
# trains 2 forecasters x 2 horizons x 4 strategies (3-4.5 min per dataset on CPU). A review of Section 5 asked why 4;
# the honest answer is run time, which is about 2 h for all 30, so this script runs them all.
#   - NB5 section 4's code is repeated unchanged (same masks, scoring area, forecasters, seed 0);
#   - each dataset is regenerated from its seed and checked against results/benchmark_v1/runs/*_truth.csv;
#   - the 4 NB5 datasets must reproduce results/downstream_v1/injected/*_forecast.csv and *_dm.csv;
#   - evaluation only: nothing is selected or tuned on these seeds (D63).
# Usage: python tools/forecast_all_datasets.py      (resumable, cached per dataset; a re-run only rebuilds the summary)
import sys, json, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import numpy as np, pandas as pd
from scipy.stats import wilcoxon
import rules_v1 as R1, detector as D, label_model as LM, benchmark as B, inject as INJ, downstream as DS

RATES, SEEDS = (0.01, 0.03, 0.07), range(10)
NB5_SETS = [(0.03, 0), (0.03, 1), (0.03, 2), (0.07, 0)]
SEED = 0
XLSX = ROOT / "data" / "raw" / "Data Morocco.xlsx"
OUT = ROOT / "results" / "downstream_v1" / "forecast_all"; (OUT / "runs").mkdir(parents=True, exist_ok=True)
NB5_DIR = ROOT / "results" / "downstream_v1" / "injected"
RUNS = ROOT / "results" / "benchmark_v1" / "runs"
GRID_T = ("G1", "G2", "G3", "G4", "U_SHOCK", "U_PARTIAL")


def one(res, P, CLEAN, INJECTOR, rate, seed):
    """NB5 section 4 (forecasting part), unchanged, on one dataset."""
    idx = P["x"].index
    tag = f"r{int(round(rate * 100)):02d}_s{seed:02d}"
    data_inj, truth = INJECTOR.sample(np.ones(len(idx), bool), rate, np.random.default_rng([int(round(rate * 1000)), seed]))
    stored = pd.read_csv(RUNS / f"{tag}_truth.csv", parse_dates=["start"])
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
    NORM_i = ~FLi & ~DS.span_mask(Pi, it[it.system == "south"]) & Pi["x"].notna()
    SCORE_i = NORM_i & CLEAN & ~INJ_ANY
    masks = {"S0": (None, None), "S1": (None, None), "S2": (ART2, GRID2), "S3": (ART3, GRID3)}
    fc, loss = DS.forecast_eval(Pi, FLi, masks, NORM_i, SCORE_i, XHi, seed=SEED, log=lambda *a, **k: None)
    return fc.assign(rate=rate, seed=seed), DS.dm_table(loss).assign(rate=rate, seed=seed), len(truth)


def main():
    t0 = time.time()
    res = R1.build(XLSX)
    P = D.build_panel(res["data"], res["exp"], res["masks"], "south")
    CLEAN = B.clean_region(P, None)
    INJECTOR = INJ.Injector(res["data"], res["exp"], CLEAN, INJ.zone_map(res["data"], B.SOUTH, R1.CITY_SHORT))
    order = NB5_SETS + [(r, s) for r in RATES for s in SEEDS if (r, s) not in NB5_SETS]   # reproduction first
    for rate, seed in order:
        tag = f"r{int(round(rate * 100)):02d}_s{seed:02d}"
        f_fc, f_dm = OUT / "runs" / f"{tag}_forecast.csv", OUT / "runs" / f"{tag}_dm.csv"
        if f_fc.exists() and f_dm.exists():
            continue
        t = time.time()
        fc, dm, n = one(res, P, CLEAN, INJECTOR, rate, seed)
        fc.to_csv(f_fc, index=False); dm.to_csv(f_dm, index=False)
        print(f"{tag}: {n} events, {time.time() - t:.0f} s", flush=True)

    # --- reproduction of NB5 (its 4 datasets)
    key = ["model", "horizon", "subset", "strategy"]
    rep = []
    for rate, seed in NB5_SETS:
        tag = f"r{int(round(rate * 100)):02d}_s{seed:02d}"
        a = pd.read_csv(OUT / "runs" / f"{tag}_forecast.csv").set_index(key).sort_index()
        b = pd.read_csv(NB5_DIR / f"{tag}_forecast.csv").set_index(key).sort_index()
        cols = ["MAE", "RMSE", "MASE", "sMAPE"]
        da = float((a.loc[b.index, cols] - b[cols]).abs().to_numpy().max())
        kd = ["model", "horizon", "subset", "comparison"]
        c = pd.read_csv(OUT / "runs" / f"{tag}_dm.csv").set_index(kd).sort_index()
        d = pd.read_csv(NB5_DIR / f"{tag}_dm.csv").set_index(kd).sort_index()
        dd = float((c.loc[d.index, ["mean_loss_diff", "DM"]] - d[["mean_loss_diff", "DM"]]).abs().to_numpy().max())
        rep.append(dict(dataset=tag, max_abs_diff_forecast=da, max_abs_diff_dm=dd))
    rep = pd.DataFrame(rep); rep.to_csv(OUT / "reproduction_nb5.csv", index=False)
    print(rep.to_string(index=False))
    assert (rep.max_abs_diff_forecast < 1e-3).all(), f"NB5 forecasts not reproduced:\n{rep}"

    # --- all 30 datasets
    fc = pd.concat([pd.read_csv(OUT / "runs" / f"r{int(round(r * 100)):02d}_s{s:02d}_forecast.csv") for r in RATES for s in SEEDS], ignore_index=True)
    dm = pd.concat([pd.read_csv(OUT / "runs" / f"r{int(round(r * 100)):02d}_s{s:02d}_dm.csv") for r in RATES for s in SEEDS], ignore_index=True)
    fc.to_csv(OUT / "forecast_per_dataset.csv", index=False); dm.to_csv(OUT / "dm_per_dataset.csv", index=False)
    piv = fc.pivot_table(index=["model", "horizon", "subset", "rate", "seed"], columns="strategy", values="MASE").reset_index()

    def summ(g, label):
        out = dict(rate=label, n=len(g))
        for s in ("S0", "S1", "S2", "S3"):
            out[f"MASE_{s}_mean"], out[f"MASE_{s}_sd"] = g[s].mean(), g[s].std(ddof=1)
        for a in ("S0", "S1"):
            d = g[a] - g["S2"]
            out[f"S2_better_than_{a}_n"] = int((d > 0).sum())
            out[f"wilcoxon_p_{a}_vs_S2"] = float(wilcoxon(g[a], g["S2"]).pvalue) if (d != 0).any() else np.nan
        d3 = g["S2"] - g["S3"]
        out["S2_minus_S3_mean"] = d3.mean()
        return out

    rows = []
    for (m, h, sub), g in piv.groupby(["model", "horizon", "subset"]):
        for r in RATES:
            rows.append(dict(model=m, horizon=h, subset=sub, **summ(g[g.rate == r], f"{r:.0%}")))
        rows.append(dict(model=m, horizon=h, subset=sub, **summ(g, "all")))
    tab = pd.DataFrame(rows); tab.to_csv(OUT / "forecast_summary.csv", index=False)
    # DM tests per dataset: how often S2 is significantly better (p < 0.05 and loss difference > 0)
    dm["S2_sig_better"] = (dm.p < 0.05) & (dm.mean_loss_diff > 0) & dm.comparison.isin(["S1 vs S2", "S0 vs S2"])
    dm["S2_sig_worse"] = (dm.p < 0.05) & (dm.mean_loss_diff < 0) & dm.comparison.isin(["S1 vs S2", "S0 vs S2"])
    dms = dm.groupby(["model", "horizon", "subset", "comparison"]).agg(n=("p", "size"), sig_better=("S2_sig_better", "sum"),
                                                                     sig_worse=("S2_sig_worse", "sum"), DM_mean=("DM", "mean")).reset_index()
    dms.to_csv(OUT / "dm_summary.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    print(tab[tab.rate == "all"].round(4).to_string(index=False)); print(dms.to_string(index=False))
    summary = dict(datasets=int(piv[["rate", "seed"]].drop_duplicates().shape[0]), rates=list(RATES), seeds=list(SEEDS),
                   reproduces_nb5=rep.to_dict("records"), minutes_this_call=round((time.time() - t0) / 60, 1))
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1))
    print("done in", summary["minutes_this_call"], "min")


if __name__ == "__main__":
    main()
