"""Snorkel's LabelModel as a label-model baseline on the same rule votes (D92).

A review of Section 2 noted that Snorkel's label model learns from labelling functions that abstain, and asked for it
as a baseline. This script fits snorkel.labeling.model.LabelModel (snorkel 0.10.0) on exactly the votes our label model
sees, on the real data and on the 30 NB4 test datasets.

How the votes are given to Snorkel (its input is one integer per labelling function and item, -1 = abstain):
  - one LabelModel per item kind, because Snorkel needs one class set for all items:
      dead {A1, G1, G2, G3, G4}, fill {A2, A3, N}, clock {A4, N}, transfer {G5, N};
  - the labelling functions are the rules of that kind (R1.RULE_KIND);
  - the family vote 'G' of R5 and R6 (any grid-event type) cannot be expressed in Snorkel's format: it becomes -1;
  - two variants: 'Snorkel' (its posterior as is) and 'Snorkel + feasible sets' (its posterior restricted to the
    item's feasible classes, label_model.feasible_classes, and renormalised).
Fit: n_epochs 500, lr 0.01 (the Snorkel tutorial settings), class balance not given (Snorkel's default).

Outputs:
  results/labels_v1/snorkel/  real data: probabilities (seed 0), stability over seeds 0-19, agreement, summary.json
  results/benchmark_v1/snorkel_baseline/  per test dataset: labels of the rule-matched typed test events;
      table_snorkel_attribution.csv (macro-F1 per rate, mean +- sd over 10 seeds), wilcoxon_snorkel.csv, summary.json
Run with an interpreter that has snorkel==0.10.0; it was installed in a separate virtual environment created with
--system-site-packages, so the project's pinned packages (LightGBM 4.6.0) stay untouched:
    python -m venv --system-site-packages .venv_snorkel
    .venv_snorkel/Scripts/python -m pip install snorkel==0.10.0 --no-deps
    .venv_snorkel/Scripts/python -m pip install munkres networkx
    .venv_snorkel/Scripts/python tools/snorkel_baseline.py          (resumable; ~1-2 min per test dataset)
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import numpy as np
import pandas as pd
from scipy.stats import wilcoxon
from sklearn.metrics import f1_score
from snorkel.labeling.model import LabelModel
import snorkel

import rules_v1 as R1, label_model as LM, detector as D, benchmark as B, inject as INJ

KIND_CLASSES = {"dead": ["A1", "G1", "G2", "G3", "G4"], "fill": ["A2", "A3", "N"], "clock": ["A4", "N"], "transfer": ["G5", "N"]}
ALL = ["A1", "A2", "A3", "A4", "G1", "G2", "G3", "G4", "G5", "N"]
TYPED = INJ.TYPED
CL = B.CL                                         # event classes of the benchmark (q_ columns)
FIT = dict(n_epochs=500, lr=0.01, log_freq=500)
OUT_R = ROOT / "results" / "labels_v1" / "snorkel"
OUT_B = ROOT / "results" / "benchmark_v1" / "snorkel_baseline"
RUNS = ROOT / "results" / "benchmark_v1" / "runs"
TEST = [(r, s) for r in (0.01, 0.03, 0.07) for s in range(10)]
NOT_MODELLED = set()                              # items of kinds with < 3 rules (Snorkel needs >= 3): majority vote


def snorkel_q(votes, items, seed):
    """Snorkel posteriors over ALL classes (zeros outside the item's kind), one LabelModel per kind."""
    votes = votes.reindex(items.item_id)
    rows = {}
    for kind, cls in KIND_CLASSES.items():
        ids = items.item_id[items.kind == kind].to_numpy()
        if not len(ids):
            continue
        rules = [r for r, k in R1.RULE_KIND.items() if k == kind and r in votes.columns]
        V = votes.loc[ids, rules]
        L = np.full(V.shape, -1, dtype=int)
        for j, r in enumerate(rules):
            for i, v in enumerate(V[r].to_numpy()):
                if isinstance(v, str) and v in cls:
                    L[i, j] = cls.index(v)
        if len(rules) < 3:
            # Snorkel's LabelModel needs >= 3 labelling functions; the transfer kind has one rule (R16).
            # Fallback: the majority vote, as a one-hot posterior (recorded in the summary as 'not modelled').
            mv = LM.majority_vote(votes.loc[ids], items[items.kind == kind])
            P = np.array([[1.0 if c == m else 0.0 for c in cls] for m in mv.to_numpy()])
            NOT_MODELLED.update(ids.tolist())
        else:
            lm = LabelModel(cardinality=len(cls), verbose=False)
            lm.fit(L, progress_bar=False, seed=seed, **FIT)
            P = lm.predict_proba(L)
        for i, iid in enumerate(ids):
            rows[iid] = dict(zip(cls, P[i]))
    return pd.DataFrame.from_dict(rows, orient="index").reindex(index=items.item_id, columns=ALL).fillna(0.0)


def restrict(q, items):
    """Snorkel + feasible sets: posterior restricted to the item's feasible classes and renormalised."""
    out = q.copy()
    for it in items.itertuples():
        feas = LM.feasible_classes(it)
        row = out.loc[it.item_id, feas]
        s = row.sum()
        out.loc[it.item_id] = 0.0
        out.loc[it.item_id, feas] = row / s if s > 0 else 1.0 / len(feas)
    return out


def labels(q):
    return q.idxmax(axis=1)


def real_data():
    OUT_R.mkdir(parents=True, exist_ok=True)
    items = pd.read_csv(ROOT / "results" / "catalogue_v1" / "items.csv")
    votes = pd.read_csv(ROOT / "results" / "catalogue_v1" / "votes.csv").set_index("item_id")
    ours = pd.read_csv(ROOT / "results" / "labels_v1" / "q.csv").set_index("item_id")
    labs, labs_f = {}, {}
    for s in range(20):
        q = snorkel_q(votes, items, s)
        labs[s], labs_f[s] = labels(q), labels(restrict(q, items))
        if s == 0:
            q.round(4).to_csv(OUT_R / "q_snorkel_seed0.csv")
            restrict(q, items).round(4).to_csv(OUT_R / "q_snorkel_feasible_seed0.csv")
    ref, ref_f = labs[0], labs_f[0]
    stab = pd.DataFrame([dict(seed=s, agree_with_seed0=float((labs[s] == ref).mean()),
                              agree_with_seed0_feasible=float((labs_f[s] == ref_f).mean())) for s in range(20)])
    stab.to_csv(OUT_R / "stability_seeds.csv", index=False)
    feas_ok = np.array([lab in LM.feasible_classes(it) for lab, it in zip(ref.to_numpy(), items.itertuples())])
    ours_lab = ours.loc[ref.index, "label"]; mv = ours.loc[ref.index, "label_majority_vote"]
    by_kind = {}
    for kind in KIND_CLASSES:
        m = (items.kind == kind).to_numpy()
        by_kind[kind] = dict(n=int(m.sum()), agree_with_ours=float((ref.to_numpy()[m] == ours_lab.to_numpy()[m]).mean()),
                             agree_with_ours_feasible=float((ref_f.to_numpy()[m] == ours_lab.to_numpy()[m]).mean()),
                             infeasible=int((~feas_ok[m]).sum()))
    summary = dict(snorkel_version=snorkel.__version__, fit=FIT, items=len(items),
                   not_modelled_by_snorkel=dict(n=len(NOT_MODELLED), why="kind with < 3 rules (transfer: R16 only); majority vote used"),
                   stability_min=float(stab.agree_with_seed0.min()), stability_mean=float(stab.agree_with_seed0.mean()),
                   stability_min_feasible=float(stab.agree_with_seed0_feasible.min()),
                   infeasible_labels=int((~feas_ok).sum()),
                   agree_with_ours=float((ref == ours_lab).mean()), agree_with_ours_feasible=float((ref_f == ours_lab).mean()),
                   agree_with_majority_vote=float((ref == mv).mean()), agree_with_majority_vote_feasible=float((ref_f == mv).mean()),
                   label_counts=ref.value_counts().to_dict(), label_counts_feasible=ref_f.value_counts().to_dict(),
                   by_kind=by_kind)
    (OUT_R / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


def injected():
    (OUT_B / "runs").mkdir(parents=True, exist_ok=True)
    res = R1.build(ROOT / "data" / "raw" / "Data Morocco.xlsx")
    P = D.build_panel(res["data"], res["exp"], res["masks"], "south")
    CLEAN = B.clean_region(P, None)
    INJECTOR = INJ.Injector(res["data"], res["exp"], CLEAN, INJ.zone_map(res["data"], B.SOUTH, R1.CITY_SHORT))
    idx = P["rho"].index
    for rate, seed in TEST:
        tag = f"r{int(round(rate * 100)):02d}_s{seed:02d}"
        f = OUT_B / "runs" / f"{tag}_labels.csv"
        if f.exists():
            continue
        t = time.time()
        data_inj, truth = INJECTOR.sample(np.ones(len(idx), bool), rate, np.random.default_rng([int(round(rate * 1000)), seed]))
        stored = pd.read_csv(RUNS / f"{tag}_truth.csv", parse_dates=["start"])
        assert len(stored) == len(truth) and (stored.start.values == truth.start.values).all(), f"{tag}: differs from NB4"
        r = R1.build_from_data(res["raw"], data_inj)
        items, votes = r["items"], r["votes"].set_index("item_id")
        q = snorkel_q(votes, items, 0)
        lab_s, lab_sf = labels(q), labels(restrict(q, items))
        mv_here = LM.majority_vote(votes.reindex(items.item_id), items)
        ev = pd.read_csv(RUNS / f"{tag}_events.csv")
        sub = ev[ev.type.isin(TYPED) & ev.detected & (ev.period == "test") & (ev.source == "rule")].copy()
        # the rebuilt items must be NB4's items: their majority vote must equal the stored one
        assert (mv_here.loc[sub.item_id].to_numpy() == sub.mv.to_numpy()).all(), f"{tag}: rebuilt votes differ from NB4"
        sub["label_ours"] = np.array(CL)[sub[[f"q_{c}" for c in CL]].to_numpy(float).argmax(1)]
        sub["label_mv"] = np.where(sub.mv.isin(CL), sub.mv, "N")
        sub["label_snorkel"] = lab_s.loc[sub.item_id].to_numpy()
        sub["label_snorkel_feasible"] = lab_sf.loc[sub.item_id].to_numpy()
        sub[["event_id", "type", "item_id", "label_ours", "label_mv", "label_snorkel", "label_snorkel_feasible"]].assign(
            rate=rate, seed=seed).to_csv(f, index=False)
        print(f"{tag}: {len(sub)} rule-matched typed test events, {time.time() - t:.0f} s", flush=True)

    allr = pd.concat([pd.read_csv(OUT_B / "runs" / f"r{int(round(r * 100)):02d}_s{s:02d}_labels.csv") for r, s in TEST],
                     ignore_index=True)
    allr.to_csv(OUT_B / "labels_rule_matched_test_events.csv", index=False)
    LAB = {"majority vote": "label_mv", "label model (ours)": "label_ours", "Snorkel": "label_snorkel",
           "Snorkel + feasible sets": "label_snorkel_feasible"}
    per = []
    for (rate, seed), g in allr.groupby(["rate", "seed"]):
        row = dict(rate=rate, seed=seed, n=len(g))
        for name, col in LAB.items():
            row[name] = f1_score(g.type, g[col], labels=TYPED, average="macro", zero_division=0)
            row[name + " | accuracy"] = float((g.type == g[col]).mean())
        per.append(row)
    per = pd.DataFrame(per); per.to_csv(OUT_B / "macro_f1_per_dataset.csv", index=False)
    tab, wil = [], []
    for rate in (0.01, 0.03, 0.07):
        g = per[per.rate == rate]
        tab.append(dict(rate=f"{rate:.0%}", n_events=int(g.n.sum()),
                        **{k: f"{g[k].mean():.3f} ± {g[k].std(ddof=1):.3f}" for k in LAB},
                        **{k + " | accuracy": round(g[k + " | accuracy"].mean(), 3) for k in LAB}))
        for other in ("majority vote", "Snorkel", "Snorkel + feasible sets"):
            d = g["label model (ours)"] - g[other]
            p = float(wilcoxon(g["label model (ours)"], g[other]).pvalue) if (d != 0).any() else 1.0
            wil.append(dict(rate=f"{rate:.0%}", comparison=f"label model (ours) vs {other}", ours=round(g["label model (ours)"].mean(), 4),
                            other=round(g[other].mean(), 4), ours_wins=int((d > 0).sum()), ties=int((d == 0).sum()), wilcoxon_p=p))
    tab, wil = pd.DataFrame(tab), pd.DataFrame(wil)
    tab.to_csv(OUT_B / "table_snorkel_attribution.csv", index=False); wil.to_csv(OUT_B / "wilcoxon_snorkel.csv", index=False)
    conf = {name: pd.crosstab(allr[allr.rate == 0.03].type, allr[allr.rate == 0.03][col]).to_dict() for name, col in LAB.items()}
    (OUT_B / "summary.json").write_text(json.dumps(dict(snorkel_version=snorkel.__version__, fit=FIT, datasets=len(per),
                                                        events=int(per.n.sum()), confusion_3pct=conf), indent=1, default=str))
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(tab.to_string(index=False)); print(wil.to_string(index=False))


if __name__ == "__main__":
    if "--real-only" in sys.argv:
        real_data()
    else:
        real_data()
        injected()
