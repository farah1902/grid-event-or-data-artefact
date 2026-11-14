"""Sensitivity of the Marrakech labels to the fusion weight beta (D80, F60).

The injection benchmark (NB4) covers only the southern system, so beta cannot be tuned for Marrakech, whose items keep
NB3's untuned default beta = 0.5. This script re-fuses NB3's stored label-model posteriors q and end-model
probabilities f (results/end_model_v1/p_type.csv, 4 decimals) with the same feasible sets and the same D50 abstention,
for beta = 0, 0.1, ..., 1, and counts the Marrakech labels that differ from beta = 0.5. It first checks that
beta = 0.5 reproduces every stored rule-item label. Seconds.
    python tools/marrakech_beta_sensitivity.py
Writes results/end_model_v1/marrakech_beta_sensitivity.csv and marrakech_beta_sensitivity.json.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import end_model as EM  # noqa: E402

CL = ["A1", "A2", "A3", "G1", "G2", "G3", "G4", "N"]          # EVENT_CLASSES of the end model (NB3)
OUT = ROOT / "results" / "end_model_v1"


def main():
    pt = pd.read_csv(OUT / "p_type.csv")
    q = pd.read_csv(ROOT / "results" / "labels_v1" / "q.csv").set_index("item_id")
    rule = pt[pt.source == "rule"].reset_index(drop=True)
    rule["system"] = rule.item_id.map(q.system)
    Q = rule[[f"q_{c}" for c in CL]].to_numpy(float)
    F = rule[[f"f_{c}" for c in CL]].to_numpy(float)
    feas = np.array([[c in q.at[i, "feasible"].split(",") for c in CL] for i in rule.item_id], float)
    low = EM.low_support_classes(Q, CL)                             # D50: computed over all rule items, as in NB3
    abst = np.isin(np.array(CL)[Q.argmax(1)], low)

    lab = lambda b: np.array(CL)[EM.fuse(Q, F, feas, beta=b, abstain=abst).argmax(1)]
    ref = lab(0.5)
    reproduced = float((ref == rule.label_p.to_numpy()).mean())
    assert reproduced == 1.0, f"beta = 0.5 reproduces only {reproduced:.3f} of the stored labels"

    m = (rule.system == "Marrakech").to_numpy()
    rows = []
    for b in np.round(np.arange(0, 1.01, 0.1), 1):
        lb = lab(b)
        rows.append(dict(beta=b, marrakech_items=int(m.sum()), changed_vs_beta_0_5=int((lb[m] != ref[m]).sum()),
                         **{f"n_{c}": int((lb[m] == c).sum()) for c in CL}))
    tab = pd.DataFrame(rows)
    tab.to_csv(OUT / "marrakech_beta_sensitivity.csv", index=False)
    stable = tab[tab.changed_vs_beta_0_5 == 0].beta
    disagree = rule[m & (rule.label_q != rule.label_f)][["item_id", "label_q", "label_f", "label_p"]]
    summary = dict(marrakech_rule_items=int(m.sum()), stored_labels_reproduced_at_beta_0_5=reproduced,
                   q_f_argmax_agree=int((rule.label_q[m] == rule.label_f[m]).sum()),
                   q_f_disagree_items=disagree.to_dict("records"),
                   beta_range_same_labels_as_0_5=[float(stable.min()), float(stable.max())],
                   max_changed=int(tab.changed_vs_beta_0_5.max()), low_support_classes=low)
    (OUT / "marrakech_beta_sensitivity.json").write_text(json.dumps(summary, indent=2))
    print(tab.to_string(index=False))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
