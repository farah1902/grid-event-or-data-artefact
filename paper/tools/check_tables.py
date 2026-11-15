"""Rebuild the paper's result tables from unrounded sources and compare them with the LaTeX, cell by cell.

Written for the final check (D102), after 12 cells were found off by one unit in the last digit: they had been typed
from 3-decimal summary strings and rounded again (double rounding). Every value here is computed from per-seed or
unrounded files and rounded once.

    Table 4  rules             results/paper/tables/Table3_rules.csv (coverage 3 d., precision 2 d., defining dagger)
    Table 6  detection         results/benchmark_v1/runs/*_detection.csv + deep_baselines/test_detection.csv (test period)
    Table 7  attribution       results/benchmark_v1/table6_attribution.csv (3 d., printed as stored)
    Table 8  forecasting       results/downstream_v1/table8_forecasting.csv, forecast_all/forecast_summary.csv
    Table 9  Tetouan           results/transfer_tetouan/runs/*_detection.csv

    python paper/tools/check_tables.py        (exit code 1 if any cell differs)
"""
import re
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
TEX = {"04": (ROOT / "paper/sections/04_method.tex").read_text(encoding="utf-8"),
       "06": (ROOT / "paper/sections/06_results.tex").read_text(encoding="utf-8")}


def block(sec, label):
    t = TEX[sec]
    t = t[t.index(r"\label{" + label + "}"):]
    return t[:t.index(r"\end{table}")]


def row(blk, name):
    line = next(l for l in blk.splitlines() if l.startswith(name + " &"))
    return [c.strip().rstrip("\\").strip() for c in line.split("&")[1:]]


def once(x, nd):
    """Round an unrounded value once, half up."""
    return str(Decimal(repr(float(x))).quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP))


def runs(folder, test_only):
    df = pd.concat([pd.read_csv(f).assign(rate=int(f.name[1:3]), seed=int(f.name[5:7]))
                    for f in sorted(folder.glob("r??_s??_detection.csv"))])
    return df[df.period == "test"] if test_only else df


def mean3(df, method, col):
    out = []
    for rate in (1, 3, 7):
        v = df[(df.method == method) & (df.rate == rate)][col].astype(float)
        assert len(v) == 10, (method, rate, col, len(v))
        out.append(once(v.mean(), 2))
    return out


def table4():
    src = pd.read_csv(ROOT / "results/paper/tables/Table3_rules.csv").set_index("rule")
    bad = []
    for line in block("04", "tab:rules").splitlines():
        m = re.match(r"(R\d+)(\$\^\{\\dagger\}\$)?\s*&.*&\s*(\S+)\s*&\s*(\S+)\s*\\\\", line)
        if not m:
            continue
        r, dag, cov, prec = m.groups()
        s = src.loc[r]
        exp = ("0" if s.coverage == 0 else once(s.coverage, 3),
               "--" if s.n_votes == 0 else once(s.learned_precision, 2), str(s.defining) == "True")
        if (cov, prec, bool(dag)) != exp:
            bad.append(f"Table 4 {r}: {(cov, prec, bool(dag))} vs {exp}")
    return bad


def table6():
    bm = ROOT / "results/benchmark_v1"
    deep = pd.read_csv(bm / "deep_baselines/test_detection.csv")
    deep = deep[deep.period == "test"].assign(rate=lambda d: (d.rate.astype(float) * 100).round().astype(int))
    data = pd.concat([runs(bm / "runs", True), deep], ignore_index=True)
    rows = {"Full method": "ours (rules + detector)", "Rules alone": "rules only (rule engine v1)",
            "Main detector": "TCN-GAT, hierarchy, multi-scale", "LightGBM residual": "LightGBM forecast, hierarchy, multi-scale",
            "STL": "STL + MAD", "LOF": "LOF", "Isolation Forest": "Isolation Forest", "GDN": "GDN", "USAD": "USAD"}
    bad, blk = [], block("06", "tab:detection")
    for name, src in rows.items():
        cells = row(blk, name)
        for col, cell in zip(["precision", "recall", "f1_bgx", "f1_zone"], cells[:4]):
            exp = "/".join(mean3(data, src, col))
            if cell != exp:
                bad.append(f"Table 6 {name} {col}: {cell} vs {exp}")
    return bad


def table7():
    t = pd.read_csv(ROOT / "results/benchmark_v1/table6_attribution.csv")
    rows = {"Majority vote": "majority vote (rules)", "Label model $q$": "label model q",
            "End model $f$": "end model f, all features", "Fusion $p$": "fusion (β*, D50 abstention)"}
    bad, blk = [], block("06", "tab:attribution")
    for name, src in rows.items():
        cells = row(blk, name)
        for i, rate in enumerate(("1%", "3%", "7%")):
            r = t[(t.rate == rate) & (t.labeler == src)].iloc[0]
            if cells[i].replace("$\\pm$", "±") != r.macro_F1:
                bad.append(f"Table 7 {name} {rate} macro-F1: {cells[i]} vs {r.macro_F1}")
            ece = "--" if str(r.ECE) in ("n/a", "nan") else str(r.ECE).split("±")[0].strip()
            if cells[3 + i] != ece:
                bad.append(f"Table 7 {name} {rate} ECE: {cells[3 + i]} vs {ece}")
    return bad


def table8():
    ds = ROOT / "results/downstream_v1"
    real = pd.read_csv(ds / "table8_forecasting.csv"); real = real[real.data == "real"]
    inj = pd.read_csv(ds / "forecast_all/forecast_summary.csv"); inj = inj[inj.rate == "all"]
    sub = {"after": "after anomaly (2 days)", "all": "all"}
    bad = []
    for line in block("06", "tab:downstream").splitlines():
        if not (line.startswith("LightGBM &") or line.startswith("Naive &")):
            continue
        c = [x.strip().rstrip("\\").strip() for x in line.split("&")]
        model = "LightGBM" if c[0] == "LightGBM" else "naive"
        r = real[(real.model == model) & (real.horizon == c[1]) & (real.subset == sub[c[2]])].set_index("strategy").MASE
        i = inj[(inj.model == model) & (inj.horizon == c[1]) & (inj.subset == sub[c[2]])].iloc[0]
        exp_real = "/".join(once(r[s], 3) for s in ("S0", "S1", "S2"))
        exp_inj = "/".join(once(i[f"MASE_{s}_mean"], 3) for s in ("S0", "S1", "S2", "S3"))
        if c[3] != exp_real:
            bad.append(f"Table 8 {model} {c[1]} {c[2]} real: {c[3]} vs {exp_real}")
        if c[5] != exp_inj:
            bad.append(f"Table 8 {model} {c[1]} {c[2]} injected: {c[5]} vs {exp_inj}")
        if not c[6].startswith(f"{int(i.S2_better_than_S1_n)} ("):
            bad.append(f"Table 8 {model} {c[1]} {c[2]} count: {c[6]} vs {int(i.S2_better_than_S1_n)}")
    return bad


def table9():
    data = runs(ROOT / "results/transfer_tetouan/runs", False)
    rows = {"Full method": "ours (rules + detector)", "Rules alone": "rules only (rule engine v1)",
            "Main detector": "TCN-GAT, hierarchy, multi-scale", "Main detector, no graph": "TCN, no graph, hierarchy, multi-scale",
            "LightGBM residual": "LightGBM forecast, hierarchy, multi-scale", "STL": "STL + MAD",
            "Isolation Forest": "Isolation Forest", "LOF": "LOF"}
    bad, blk = [], block("06", "tab:tetouan")
    for name, src in rows.items():
        cells = row(blk, name)
        for col, cell in zip(["precision", "recall", "auc_pr"], cells[:3]):
            exp = " / ".join(mean3(data, src, col))
            if cell != exp:
                bad.append(f"Table 9 {name} {col}: {cell} vs {exp}")
    return bad


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    bad = []
    for f in (table4, table6, table7, table8, table9):
        b = f(); bad += b
        print(f"{f.__name__}: {'ok' if not b else f'{len(b)} mismatch(es)'}")
    for b in bad:
        print("  ", b)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
