# Generator for notebooks/NB2_label_model.ipynb. Usage: python tools/make_nb2_label_model.py notebooks/NB2_label_model.ipynb
import sys
import nbformat as nbf
from nbformat.v4 import new_notebook, new_code_cell as C, new_markdown_cell as M

cells = []
cells.append(M(r"""# NB2 · Label model — from rule votes to probabilistic labels

Input: `results/catalogue_v1/{items,votes}.csv` (rule engine v1). Output: `results/labels_v1/` (q per item, rule parameters, diagnostics, labelled episodes).

**Model.** Dawid–Skene (guide eq. 10–12) in numpy (`src/label_model.py`), with the changes the real votes forced. Each is documented in `docs/decisions.md`:

| # | Change | Why |
|---|---|---|
| D28 | Abstention is an observed output | Every v1 rule emits one label. Under the guide's likelihood (fired rules only), P(vote = l \| y, fired) = 1 for every class, so votes carry no information |
| D29 | Feasible classes per item from kind and hierarchy level | The typology defines each type at one level (multi-city dead → A1/G1; one zone → A1/G3/G4; …) |
| D30 | Applicability domains | Hold vs interpolation, and repeated vs missing hour, are mutually exclusive sub-signatures. Without domains they read as contradictions |
| D31 | R9 speaks for {G3, G4}; 'G' speaks for every G type | R10 and R11 refine R9 |
| D32 | Constrained one-coin parameters (a = propensity, b = false-positive rate) | The unconstrained model is not identifiable on these sparse, single-label votes |
| D33 | Defining rules get propensity prior (9, 1) | A class whose only evidence is one rule cannot otherwise be held (G4, G5) |
| D34 | Dirichlet(1) prior on class priors π | Prevents empty-class fixed points (vote-less fill items, singleton G5) |

**Baselines:** majority vote (plurality over feasible classes) and the guide's unconstrained Dawid–Skene (`structure="full"`, same feasibility and applicability).

**What this notebook can and cannot show.** There is no ground truth on real data. Here we show stability, parameter recovery on data drawn from the fitted model, robustness to rule families and priors, and agreement with the rules. Accuracy against known types comes from the injection benchmark (NB4)."""))

cells.append(C(r"""import sys, subprocess
from pathlib import Path
IN_COLAB = "google.colab" in sys.modules
if IN_COLAB:
    from google.colab import drive
    drive.mount("/content/drive")
    ROOT = Path("/content/drive/MyDrive/grid-event-or-data-artefact")
else:
    ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(ROOT / "src"))

import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import rules_v1 as R1, label_model as LM, viz
from label_model import DawidSkene, CLASSES, majority_vote, entropy, ece, feasible_classes
from viz import LABEL_COL, savefig
LABEL_COL = {**LABEL_COL, "N": "#9AA0A6"}

CAT = ROOT / "results" / "catalogue_v1"
OUT = ROOT / "results" / "labels_v1"; OUT.mkdir(parents=True, exist_ok=True)
FIG = ROOT / "results" / "figures"
pd.set_option("display.width", 220); pd.set_option("display.max_columns", 40); pd.set_option("display.max_colwidth", 60)

items = pd.read_csv(CAT / "items.csv", parse_dates=["start", "end"])
votes = pd.read_csv(CAT / "votes.csv").set_index("item_id")
assert (votes.index == items.item_id).all()
print(items.kind.value_counts().to_dict(), "| rules:", list(votes.columns))"""))

cells.append(M("## Fit: constrained Dawid–Skene (ours), unconstrained Dawid–Skene (guide), majority vote"))
cells.append(C(r"""ds = DawidSkene(structure="constrained").fit(votes, items, R1.RULE_KIND)
full = DawidSkene(structure="full").fit(votes, items, R1.RULE_KIND)
mv = majority_vote(votes, items)

lab = ds.q_.idxmax(axis=1); conf = ds.q_.max(axis=1)
lab_full = full.q_.idxmax(axis=1)
print("constrained: penalised loglik", round(ds.restarts_.penalised.max(), 2), "| restart agreement min", ds.restarts_.agree_with_best.min())
print("full       : loglik", round(full.loglik_, 2), "| restart agreement min", full.restarts_.agree_with_best.min())
stab = pd.DataFrame({"constrained": ds.restarts_.agree_with_best.describe(), "full (guide)": full.restarts_.agree_with_best.describe()}).T
stab.to_csv(OUT / "restart_stability.csv"); ds.restarts_.to_csv(OUT / "restarts_constrained.csv", index=False)
stab.round(3)"""))

cells.append(M("### Learned class priors π (per item kind) and rule parameters"))
cells.append(C(r"""pi = ds.pi_.loc[:, (ds.pi_ > 0.0005).any()].round(3)
pi.to_csv(OUT / "class_priors.csv")
params = ds.params_table().merge(ds.rule_precision(votes), on="rule")
params["log_odds_a_over_b"] = np.log(params.a_propensity / params.b_false_positive).round(2)
params["defining"] = params.rule.isin(LM.DEFINING_RULES)
params["family"] = params.rule.map(R1.RULE_FAMILY)
params.to_csv(OUT / "rule_params.csv", index=False)
display(pi) if "display" in dir() else print(pi)
params"""))

cells.append(M("""## E12 — What the label model learned about each rule
For each rule: propensity *a* = P(fires | a class it speaks for) and false-positive rate *b* = P(fires | another feasible class).
log(a/b) is the evidence a vote carries."""))
cells.append(C(r"""p = params.sort_values("log_odds_a_over_b")
fig, axs = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw=dict(width_ratios=[1.2, 1]))
y = np.arange(len(p))
axs[0].hlines(y, p.b_false_positive, p.a_propensity, color="#ccc", lw=2)
axs[0].scatter(p.b_false_positive, y, color="#9AA0A6", label="b: false-positive rate", zorder=3)
axs[0].scatter(p.a_propensity, y, c=[LABEL_COL.get(o if o != "G" else "G", "#999") for o in p.output], edgecolor="k", lw=.4, label="a: propensity", zorder=3, s=40)
axs[0].set_yticks(y); axs[0].set_yticklabels([f"{r} → {o}{' *' if d else ''}" for r, o, d in zip(p.rule, p.output, p.defining)], fontsize=8)
axs[0].set_xscale("log"); axs[0].set_xlabel("probability (log scale)"); axs[0].legend(fontsize=7, loc="lower right")
axs[0].set_title("(a) a vs b per rule (* = defining rule, prior (9,1))")
axs[1].barh(y, p.log_odds_a_over_b, color=[LABEL_COL.get(o, "#999") for o in p.output])
for yy, (n, pr) in enumerate(zip(p.n_fired, p.learned_precision)):
    axs[1].text(p.log_odds_a_over_b.iloc[yy] + .05, yy, f"n={n}, prec={pr:.2f}" if n else "never fires", va="center", fontsize=6.5)
axs[1].set_yticks(y); axs[1].set_yticklabels([])
axs[1].set_xlabel("log(a / b) = evidence per vote"); axs[1].set_title("(b) evidence strength, votes cast, learned precision")
fig.suptitle("E12 — Label model: learned rule propensities and false-positive rates", y=1.02)
fig.tight_layout(); savefig(fig, FIG, "E12_label_model_rules"); plt.show()"""))

cells.append(M("## Labels: counts, confidence, agreement with the baselines"))
cells.append(C(r"""print(pd.crosstab(lab.rename("label"), items.kind.values, margins=True).to_string())
print("\nconstrained DS vs majority vote (rows = MV):")
print(pd.crosstab(mv.rename("MV"), lab.rename("DS")).to_string())
print("\nconstrained DS vs unconstrained (guide) DS (rows = full):")
print(pd.crosstab(lab_full.rename("DS full"), lab.rename("DS")).to_string())
agree = pd.Series({"DS vs MV": (lab == mv).mean(), "DS vs DS-full": (lab == lab_full).mean(), "MV vs DS-full": (mv == lab_full).mean()}).round(3)
agree.to_csv(OUT / "labeler_agreement.csv"); agree"""))

cells.append(C(r"""fig, axs = plt.subplots(1, 2, figsize=(12, 3.6))
cls = [c for c in CLASSES if (lab == c).any()]
data_ = [conf[lab == c].values for c in cls]
bp = axs[0].boxplot(data_, labels=cls, patch_artist=True, widths=.6)
for patch, c in zip(bp["boxes"], cls): patch.set_facecolor(LABEL_COL.get(c, "#999"))
for i, c in enumerate(cls): axs[0].text(i + 1, 1.02, f"n={int((lab == c).sum())}", ha="center", fontsize=7)
axs[0].set_ylim(0.4, 1.06); axs[0].set_ylabel("confidence = max q"); axs[0].set_title("(a) confidence per assigned type")
H = entropy(ds.q_.values)
for k, col in zip(["dead", "fill", "clock", "transfer"], ["#C8553D", "#F2A541", "#8C2F39", "#2A9D8F"]):
    axs[1].hist(H[items.kind == k], bins=np.linspace(0, 1.1, 23), alpha=.6, color=col, label=k)
axs[1].set_xlabel("posterior entropy (nats)"); axs[1].set_ylabel("items"); axs[1].legend(fontsize=7); axs[1].set_title("(b) uncertainty per item kind")
fig.suptitle("E13 — Label-model posteriors on the real data", y=1.03)
fig.tight_layout(); savefig(fig, FIG, "E13_label_confidence"); plt.show()"""))

cells.append(M("""## E14 — Key events: full posterior q(y)
Items that make up the guide's key events (C01–C12), plus the G2 candidate and the clock and transfer items with votes."""))
cells.append(C(r"""key_items = {"D052": "C01 zeros (1)", "D053": "C01 zeros (2)", "F026": "C01 linear fill", "D058": "C02 F4 108 h",
             "D064": "C04 F1", "F051": "C05 L hold", "F052": "C05 B/F hold+fill", "D077": "C06 15-zone zero",
             "D079": "C07 F6 42 h", "D096": "C09 B+F zero", "F086": "C09 L linear fill", "F144": "C12 B/F hold",
             "F145": "C12 L1/L2 hold", "D117": "C12 13-zone zero", "D118": "C12 L1 tail zero", "D048": "G2 cand. L 26 Sep 22",
             "K000": "L 30 Oct 22 (A4?)", "K003": "L 23 Apr 23 (A4?)", "K014": "B 31 Mar 24 (A4?)", "T000": "C11 B transfer"}
Q = ds.q_.loc[list(key_items)]
fig, ax = plt.subplots(figsize=(10, 6.4))
left = np.zeros(len(Q))
for c in CLASSES:
    if Q[c].sum() < 1e-3: continue
    ax.barh(range(len(Q)), Q[c], left=left, color=LABEL_COL.get(c, "#999"), label=c, edgecolor="white", lw=.4)
    for i, v in enumerate(Q[c]):
        if v > .12: ax.text(left[i] + v / 2, i, f"{c} {v:.2f}", ha="center", va="center", fontsize=6.5, color="white" if c[0] == "G" or c == "A1" else "black")
    left += Q[c].values
ax.set_yticks(range(len(Q))); ax.set_yticklabels([f"{k}  {v}  [{items.set_index('item_id').votes.get(k) if isinstance(items.set_index('item_id').votes.get(k), str) else 'no votes'}]" for k, v in key_items.items()], fontsize=7)
ax.invert_yaxis(); ax.set_xlim(0, 1); ax.set_xlabel("posterior probability q(y)")
ax.legend(ncol=10, fontsize=7, loc="upper center", bbox_to_anchor=(.5, -.08))
ax.set_title("E14 — Label-model posteriors for the key events")
fig.tight_layout(); savefig(fig, FIG, "E14_key_event_posteriors"); plt.show()"""))

cells.append(M("""## Parameter recovery (synthetic votes drawn from the fitted model)
For 20 seeds: draw true types and votes for the same 327 items (same feasible sets and applicability) from the fitted model, refit from scratch, and score against the drawn truth.
This checks identifiability and calibration **under the model's own assumptions**. It does not test the rules. That is NB4."""))
cells.append(C(r"""def macro_f1(y, p):
    f = []
    for c in sorted(set(y)):
        tp = sum((a == c) and (b == c) for a, b in zip(y, p)); fp = sum((a != c) and (b == c) for a, b in zip(y, p)); fn = sum((a == c) and (b != c) for a, b in zip(y, p))
        f.append(2 * tp / (2 * tp + fp + fn) if tp else 0.0)
    return float(np.mean(f))

rec = []
for s in range(20):
    rng = np.random.default_rng(100 + s)
    v_syn, y_true = ds.sample(items, rng)
    v_syn.index = votes.index
    for name, model in [("DS constrained", DawidSkene(n_restarts=5, seed=s)), ("DS full (guide)", DawidSkene(structure="full", n_restarts=5, seed=s))]:
        m = model.fit(v_syn, items, R1.RULE_KIND)
        pred = m.q_.idxmax(axis=1).values; cf = m.q_.max(axis=1).values
        onehot = np.array([[1.0 if c == t else 0.0 for c in CLASSES] for t in y_true])
        rec.append(dict(seed=s, labeler=name, accuracy=np.mean(pred == np.array(y_true)), macro_f1=macro_f1(y_true, pred),
                        ece=ece(cf, pred == np.array(y_true)), brier=float(((m.q_.values - onehot) ** 2).sum(axis=1).mean())))
    p_mv = majority_vote(v_syn, items).values
    rec.append(dict(seed=s, labeler="majority vote", accuracy=np.mean(p_mv == np.array(y_true)), macro_f1=macro_f1(y_true, p_mv), ece=np.nan, brier=np.nan))
rec = pd.DataFrame(rec)
rec.to_csv(OUT / "recovery_runs.csv", index=False)
recovery = rec.groupby("labeler")[["accuracy", "macro_f1", "ece", "brier"]].agg(["mean", "std"]).round(3)
recovery.to_csv(OUT / "recovery_summary.csv"); recovery"""))

cells.append(M("""## Robustness on the real data: how many labels change?
(a) Drop one rule family at a time (guide ablation 2, plus the new interpolation family).
(b) Change one prior at a time: the false-positive prior b, the defining-rule prior, the Dirichlet prior on π."""))
cells.append(C(r"""def relabel_rate(model, cols):
    m = model.fit(votes[cols], items, R1.RULE_KIND)
    new = m.q_.idxmax(axis=1)
    return float((new != lab).mean()), {k: float((new[items.kind.values == k] != lab[items.kind.values == k]).mean()) for k in ["dead", "fill", "clock", "transfer"]}

rows = []
for fam in sorted(set(R1.RULE_FAMILY.values())):
    cols = [r for r in votes.columns if R1.RULE_FAMILY[r] != fam]
    tot, per = relabel_rate(DawidSkene(n_restarts=5), cols)
    rows.append(dict(test="drop family", setting=fam, rules_removed=",".join(r for r in votes.columns if R1.RULE_FAMILY[r] == fam), changed=tot, **{f"changed_{k}": v for k, v in per.items()}))
for name, kw in [("prior_b=(1,4)", dict(prior_b=(1, 4))), ("prior_b=(1,19)", dict(prior_b=(1, 19))), ("no defining prior", dict(use_defining=False)),
                 ("prior_pi=0.5", dict(prior_pi=0.5)), ("prior_pi=2", dict(prior_pi=2)), ("init a=0.9,b=0.02", dict(init_fire=.9, init_other=.02))]:
    tot, per = relabel_rate(DawidSkene(n_restarts=5, **kw), list(votes.columns))
    rows.append(dict(test="prior / init", setting=name, rules_removed="", changed=tot, **{f"changed_{k}": v for k, v in per.items()}))
robust = pd.DataFrame(rows).round(3)
robust.to_csv(OUT / "robustness.csv", index=False)
robust"""))

cells.append(C(r"""fig, ax = plt.subplots(figsize=(10, 4))
r = robust.copy(); r["name"] = r.test.str.replace("drop family", "drop") + ": " + r.setting
x = np.arange(len(r)); w = .2
for i, (k, col) in enumerate(zip(["dead", "fill", "clock", "transfer"], ["#C8553D", "#F2A541", "#8C2F39", "#2A9D8F"])):
    ax.bar(x + (i - 1.5) * w, 100 * r[f"changed_{k}"], w, color=col, label=k)
ax.set_xticks(x); ax.set_xticklabels(r.name, rotation=40, ha="right", fontsize=7.5)
ax.set_ylabel("% of items whose label changes"); ax.legend(fontsize=7, ncol=4)
ax.set_title("E15 — Robustness of the real-data labels to rule families and priors")
fig.tight_layout(); savefig(fig, FIG, "E15_label_robustness"); plt.show()"""))

cells.append(M("""## Labelled catalogue: items and episodes
`q.csv` holds one row per item with the full posterior. `episodes_labelled.csv` lists compound episodes as a sequence of item labels, for example `A2 → A1` for C12."""))
cells.append(C(r"""q = items[["item_id", "kind", "episode", "system", "start", "end", "duration_h", "cities", "zones", "n_cities", "n_zones", "votes", "mv_label"]].copy()
q = q.rename(columns={"mv_label": "inspection_label_v1"})
q["feasible"] = [",".join(feasible_classes(it)) for it in items.itertuples()]
for c in CLASSES: q[f"q_{c}"] = ds.q_[c].values.round(4)
q["label"] = lab.values; q["confidence"] = conf.values.round(4); q["entropy"] = entropy(ds.q_.values).round(4)
q["label_majority_vote"] = mv.values; q["label_ds_full"] = lab_full.values
q["family"] = np.where(q.label.str.startswith("A"), "artefact", np.where(q.label.str.startswith("G"), "grid event", "normal"))
q.to_csv(OUT / "q.csv", index=False)

ep = q[q.episode.notna()].sort_values("start").groupby("episode")
episodes = pd.DataFrame({
    "start": ep.start.min(), "end": ep.end.max(), "n_items": ep.size(),
    "cities": ep.cities.agg(lambda c: "+".join(sorted(set("+".join(c).split("+"))))),
    "n_zones_max": ep.n_zones.max(),
    "sequence": ep[["label", "confidence"]].apply(lambda g: " → ".join(f"{l}({c:.2f})" for l, c in zip(g.label, g.confidence))),
    "items": ep.item_id.agg(",".join),
    "families": ep.family.agg(lambda f: "+".join(sorted(set(f)))),
})
episodes["duration_h"] = ((episodes.end - episodes.start).dt.total_seconds() / 3600).round(1)
episodes.to_csv(OUT / "episodes_labelled.csv")
big = episodes[(episodes.n_items >= 2) | (episodes.n_zones_max >= 2)].sort_values("start")
print(len(episodes), "episodes;", len(big), "with >= 2 items or >= 2 zones")
big[["start", "duration_h", "cities", "n_zones_max", "sequence", "families"]]"""))

cells.append(M("## Summary numbers (copied into docs/results_summary.md)"))
cells.append(C(r"""summary = {
    "items": len(items), "labels": lab.value_counts().to_dict(),
    "artefact_items": int(q.family.eq("artefact").sum()), "grid_items": int(q.family.eq("grid event").sum()), "normal_items": int(q.family.eq("normal").sum()),
    "mean_confidence": round(float(conf.mean()), 3), "items_conf_below_0.7": int((conf < .7).sum()),
    "restart_agreement_min_constrained": float(ds.restarts_.agree_with_best.min()), "restart_agreement_min_full": float(full.restarts_.agree_with_best.min()),
    "agreement_DS_MV": float(agree["DS vs MV"]), "agreement_DS_DSfull": float(agree["DS vs DS-full"]),
}
import json
(OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
summary"""))

nb = new_notebook(cells=cells)
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nbf.write(nb, sys.argv[1])
print("wrote", sys.argv[1])
