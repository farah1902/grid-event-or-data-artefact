# Outage statistics on all 30 NB4 test datasets (D76).
# NB5 measured them on 4 datasets only (3 % seeds 0-2, 7 % seed 0), because NB5 also trains forecasters on each one.
# The outage count needs only the rules and the label model, so this script repeats NB5 section 4's outage part,
# unchanged, on every NB4 test dataset (rates 1/3/7 %, seeds 0-9).
#   - each dataset is regenerated from its seed and checked against results/benchmark_v1/runs/*_truth.csv;
#   - the 4 NB5 datasets must reproduce results/downstream_v1/injected/*_outage.csv exactly;
#   - evaluation only: nothing is selected or tuned on these seeds (D63).
# Usage: python tools/outage_all_datasets.py          (0.5-4 min per dataset on CPU, longer at 7 %; the full run took
#        58 min on the author's 8-core machine; resumable, cached per dataset, a re-run only rebuilds the summary)
import sys, json, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import numpy as np, pandas as pd
from scipy.stats import wilcoxon
import rules_v1 as R1, detector as D, label_model as LM, benchmark as B, inject as INJ, downstream as DS

RATES, SEEDS = (0.01, 0.03, 0.07), range(10)
NB5_SETS = [(0.03, 0), (0.03, 1), (0.03, 2), (0.07, 0)]
XLSX = ROOT / "data" / "raw" / "Data Morocco.xlsx"
OUT = ROOT / "results" / "downstream_v1" / "outage_all"; (OUT / "runs").mkdir(parents=True, exist_ok=True)
NB5_DIR = ROOT / "results" / "downstream_v1" / "injected"
RUNS = ROOT / "results" / "benchmark_v1" / "runs"
NAMES = {"truth": "truth (S3)", "naive": "naive: every dead state (S0)", "S1": "interpolated away (S1)",
         "typed": "typed, label model (S2)"}


def one(res, P, CLEAN, INJECTOR, rate, seed):
    """NB5 section 4, outage part, on one dataset. Returns the NB5-format outage table plus a breakdown row."""
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
    FLi = DS.run_mask(Pi, r["zone_runs"])
    ART2, GRID2 = DS.typed_masks(Pi, FLi, ev[["start", "end", "zones", "label"]])
    INJ_ANY = DS.span_mask(Pi, truth, "end_affected")
    REGION = CLEAN | INJ_ANY
    DEADi = Pi["states"]["dead"] & FLi
    truth_out = DS.span_mask(Pi, truth[truth.type.isin(["G1", "G2", "G3", "G4"])]) & REGION
    typed = DEADi & GRID2 & REGION
    naive = DEADi & REGION
    rows = []
    for name, m in ((NAMES["truth"], truth_out), (NAMES["naive"], naive), (NAMES["S1"], DEADi & False), (NAMES["typed"], typed)):
        _, tot = DS.outage_stats(Pi, m); rows.append(dict(strategy=name, **tot))
    outage = pd.DataFrame(rows).assign(rate=rate, seed=seed)
    tp = (typed & truth_out).to_numpy().sum(); pp = typed.to_numpy().sum(); tt = truth_out.to_numpy().sum()
    outage["typed_precision_zone_steps"], outage["typed_recall_zone_steps"] = tp / max(pp, 1), tp / max(tt, 1)
    # where the extra outage zone-hours come from (10-min steps -> hours)
    h = 1 / 6
    A1m = DS.span_mask(Pi, truth[truth.type == "A1"], "end_affected")
    ARTm = DS.span_mask(Pi, truth[truth.type.isin(DS.ART)], "end_affected")
    fp_t, fp_n = typed & ~truth_out, naive & ~truth_out
    brk = dict(rate=rate, seed=seed, n_injected=len(truth), n_A1=int((truth.type == "A1").sum()),
               typed_extra_h=fp_t.to_numpy().sum() * h, typed_extra_in_A1_h=(fp_t & A1m).to_numpy().sum() * h,
               typed_extra_in_other_artefacts_h=(fp_t & ARTm & ~A1m).to_numpy().sum() * h,
               typed_extra_elsewhere_h=(fp_t & ~ARTm).to_numpy().sum() * h,
               naive_extra_h=fp_n.to_numpy().sum() * h, naive_extra_in_artefacts_h=(fp_n & ARTm).to_numpy().sum() * h,
               naive_extra_elsewhere_h=(fp_n & ~ARTm).to_numpy().sum() * h,
               typed_missed_h=(truth_out & ~typed).to_numpy().sum() * h)
    return outage, brk


def main():
    t0 = time.time()
    res = R1.build(XLSX)
    P = D.build_panel(res["data"], res["exp"], res["masks"], "south")
    CLEAN = B.clean_region(P, None)
    INJECTOR = INJ.Injector(res["data"], res["exp"], CLEAN, INJ.zone_map(res["data"], B.SOUTH, R1.CITY_SHORT))
    for rate in RATES:
        for seed in SEEDS:
            tag = f"r{int(round(rate * 100)):02d}_s{seed:02d}"
            f_out, f_brk = OUT / "runs" / f"{tag}_outage.csv", OUT / "runs" / f"{tag}_breakdown.json"
            if f_out.exists() and f_brk.exists():
                continue
            t = time.time()
            outage, brk = one(res, P, CLEAN, INJECTOR, rate, seed)
            outage.to_csv(f_out, index=False); f_brk.write_text(json.dumps(brk, indent=1))
            print(f"{tag}: {brk['n_injected']} events, {time.time() - t:.0f} s", flush=True)

    # --- reproduction of NB5 (the 4 datasets it measured)
    rep = []
    for rate, seed in NB5_SETS:
        tag = f"r{int(round(rate * 100)):02d}_s{seed:02d}"
        a = pd.read_csv(OUT / "runs" / f"{tag}_outage.csv").set_index("strategy")
        b = pd.read_csv(NB5_DIR / f"{tag}_outage.csv").set_index("strategy")
        cols = ["zone_hours", "outages", "typed_precision_zone_steps", "typed_recall_zone_steps"]
        d = float((a.loc[b.index, cols] - b[cols]).abs().to_numpy().max())
        rep.append(dict(dataset=tag, max_abs_diff=d))
    rep = pd.DataFrame(rep); rep.to_csv(OUT / "reproduction_nb5.csv", index=False)
    assert (rep.max_abs_diff < 1e-9).all(), f"NB5 not reproduced:\n{rep}"

    # --- per dataset: estimate / truth
    allo = pd.concat([pd.read_csv(OUT / "runs" / f"r{int(round(r * 100)):02d}_s{s:02d}_outage.csv") for r in RATES for s in SEEDS],
                     ignore_index=True)
    brk = pd.DataFrame([json.loads((OUT / "runs" / f"r{int(round(r * 100)):02d}_s{s:02d}_breakdown.json").read_text())
                        for r in RATES for s in SEEDS])
    piv = allo.pivot_table(index=["rate", "seed"], columns="strategy", values="zone_hours")
    pivn = allo.pivot_table(index=["rate", "seed"], columns="strategy", values="outages")
    per = pd.DataFrame({
        "truth_zone_hours": piv[NAMES["truth"]], "naive_zone_hours": piv[NAMES["naive"]], "typed_zone_hours": piv[NAMES["typed"]],
        "naive_ratio": piv[NAMES["naive"]] / piv[NAMES["truth"]], "typed_ratio": piv[NAMES["typed"]] / piv[NAMES["truth"]],
        "truth_outages": pivn[NAMES["truth"]], "naive_outages": pivn[NAMES["naive"]], "typed_outages": pivn[NAMES["typed"]],
        "naive_count_ratio": pivn[NAMES["naive"]] / pivn[NAMES["truth"]],
        "typed_count_ratio": pivn[NAMES["typed"]] / pivn[NAMES["truth"]],
    }).reset_index()
    pr = allo[allo.strategy == NAMES["typed"]].set_index(["rate", "seed"])[["typed_precision_zone_steps", "typed_recall_zone_steps"]]
    per = per.merge(pr.reset_index(), on=["rate", "seed"]).merge(brk, on=["rate", "seed"])
    per["typed_extra_share_A1"] = per.typed_extra_in_A1_h / per.typed_extra_h.where(per.typed_extra_h > 0)
    per["naive_extra_share_artefacts"] = per.naive_extra_in_artefacts_h / per.naive_extra_h.where(per.naive_extra_h > 0)
    per.to_csv(OUT / "outage_per_dataset.csv", index=False)

    # --- summary per rate and pooled; Wilcoxon on the distance to the truth, |log ratio| (symmetric over/under)
    def summ(g, label):
        dn, dt = np.abs(np.log(g.naive_ratio)), np.abs(np.log(g.typed_ratio))
        w = wilcoxon(dn, dt) if (dn - dt).abs().sum() > 0 else None
        return dict(rate=label, n=len(g),
                    naive_ratio_mean=g.naive_ratio.mean(), naive_ratio_sd=g.naive_ratio.std(ddof=1),
                    naive_ratio_min=g.naive_ratio.min(), naive_ratio_max=g.naive_ratio.max(),
                    typed_ratio_mean=g.typed_ratio.mean(), typed_ratio_sd=g.typed_ratio.std(ddof=1),
                    typed_ratio_min=g.typed_ratio.min(), typed_ratio_max=g.typed_ratio.max(),
                    typed_closer_n=int((dt < dn).sum()),
                    wilcoxon_p=(float(w.pvalue) if w is not None else np.nan),
                    naive_count_ratio_mean=g.naive_count_ratio.mean(), typed_count_ratio_mean=g.typed_count_ratio.mean(),
                    typed_precision_mean=g.typed_precision_zone_steps.mean(), typed_recall_mean=g.typed_recall_zone_steps.mean(),
                    typed_extra_share_A1=g.typed_extra_in_A1_h.sum() / max(g.typed_extra_h.sum(), 1e-12),
                    naive_extra_share_artefacts=g.naive_extra_in_artefacts_h.sum() / max(g.naive_extra_h.sum(), 1e-12),
                    truth_zone_hours_mean=g.truth_zone_hours.mean())
    rows = [summ(per[per.rate == r], f"{r:.0%}") for r in RATES] + [summ(per, "all")]
    tab = pd.DataFrame(rows); tab.to_csv(OUT / "outage_summary.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    print(tab.round(3).to_string(index=False))
    summary = dict(datasets=len(per), rates=list(RATES), seeds=list(SEEDS), reproduces_nb5=True,
                   minutes_this_call=round((time.time() - t0) / 60, 1), minutes_full_run=58.2,
                   by_rate={r["rate"]: {k: (float(f"{v:.4g}") if isinstance(v, float) else v) for k, v in r.items() if k != "rate"} for r in rows})
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1))
    print("done in", summary["minutes_this_call"], "min")


if __name__ == "__main__":
    main()
