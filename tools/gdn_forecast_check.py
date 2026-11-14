"""GDN's forecast quality on the real series, against persistence (D82, F63).

The GDN baseline (src/deep_baselines.py, authors' released settings) detects through deviations from its forecast. This
script measures that forecast on rule-clean windows of the real southern series, in the min-max scaled units GDN is
trained on, for each cross-fitted model, in and out of sample, against two model-free forecasts (the last value and
the mean of the last 5 values = GDN's input window). It also reports the mean attention weight a zone puts on itself.
    python tools/gdn_forecast_check.py      (seconds; needs results/benchmark_v1/models/deep_baselines.pt)
Writes results/benchmark_v1/deep_baselines/gdn_forecast_vs_persistence.csv.
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import numpy as np, pandas as pd, torch
import torch.nn.functional as F
import rules_v1 as R1, detector as D, deep_baselines as DB


def main():
    torch.set_num_threads(4)
    res = R1.build(ROOT / "data" / "raw" / "Data Morocco.xlsx")
    P = D.build_panel(res["data"], res["exp"], res["masks"], "south")
    models = DB.load(ROOT / "results" / "benchmark_v1" / "models" / "deep_baselines.pt", P["rho"].shape[1])
    x, _, clean = DB._inputs(P)
    fold = P["rho"].index >= D.SPLIT
    win = DB.GDN_CFG["win"]
    rows = []
    for tr, (g, (lo, hi)) in models["GDN"].items():
        xs = DB._scale(x, lo, hi)
        for where, sel in (("training fold (in sample)", fold == tr), ("other fold (out of sample)", fold != tr)):
            ends = np.flatnonzero(DB._window_ok(clean, win + 1) & sel & (np.arange(len(fold)) >= win))
            pred = DB._predict_gdn(g, xs, ends, win, "cpu"); y = xs[ends]
            last = xs[ends - 1]; mean5 = xs[ends[:, None] - np.arange(1, win + 1)].mean(axis=1)
            with torch.no_grad():
                X = torch.as_tensor(xs); idx = torch.as_tensor(ends[:4096])
                inp = X[idx.unsqueeze(1) - torch.arange(win, 0, -1).unsqueeze(0)].permute(0, 2, 1)
                h = g.lin(inp); e = g.emb.weight.unsqueeze(0).expand(len(idx), -1, -1)
                si = (h * g.att_i).sum(-1) + (e * g.att_em_i).sum(-1); sj = (h * g.att_j).sum(-1) + (e * g.att_em_j).sum(-1)
                lg = F.leaky_relu(si.unsqueeze(2) + sj.unsqueeze(1), 0.2).masked_fill(~g.neighbours().unsqueeze(0), float("-inf"))
                self_att = float(torch.softmax(lg, -1).diagonal(dim1=1, dim2=2).mean())
            mse = lambda p: float(((p - y) ** 2).mean())
            rows.append(dict(model_trained_on=f"{'>=' if tr else '<'} {D.SPLIT.date()}", windows=where, n=len(ends),
                             mse_gdn=mse(pred), mse_last_value=mse(last), mse_mean_last5=mse(mean5),
                             ratio_gdn_to_last_value=mse(pred) / mse(last), mean_self_attention=self_att))
    out = pd.DataFrame(rows)
    out.to_csv(ROOT / "results" / "benchmark_v1" / "deep_baselines" / "gdn_forecast_vs_persistence.csv", index=False)
    print(out.round(5).to_string(index=False))


if __name__ == "__main__":
    main()
