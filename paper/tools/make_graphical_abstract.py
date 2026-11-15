"""Graphical abstract (Applied Energy): drawn at the size the journal checks, 13 x 5.2 cm, text >= 7.5 pt.

Three columns, colour = cause throughout (red: acquisition artefact, blue: grid event):
  (1) one feeder, two causes, on real recorded traces of F1 (Foum El Oued): January 2023, a straight-line fill (A2)
      and then exact zeros in all 15 zones at once (A1), shaded in red tints; 30 April 2024, 08:20-10:30, F1 alone at a
      noise floor during planned work (G4), shaded in a blue tint;
  (2) the method in three boxes (where, which trace, 19 rules + label model);
  (3) what changes: the real southern dead zone-hours split by type (outage_real.csv) and the outage time relative
      to the truth on the 30 injected test datasets, every dataset shown (outage_all/outage_per_dataset.csv).
Every number and label is read from stored results and asserted against the catalogue; the per-step states are
rebuilt with the rule engine as for Figures 4 and 5.

Journal rules (paper/OUTLINE.md): at least 1328 x 531 px (w x h), longest side horizontal, readable at 13 x 5 cm on a
96-dpi screen; TIFF, EPS, PDF or MS Office files. Outputs: paper/graphical_abstract.pdf (vector, TrueType fonts) and
paper/graphical_abstract.tif (300 dpi, 1535 x 614 px, RGB). Drawn with matplotlib from data; no generative AI.
    python paper/tools/make_graphical_abstract.py [--preview DIR]   (~1 min: rebuilds the rule-engine states)
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
import rules_v1 as R1          # noqa: E402
from viz import COL            # noqa: E402

PAPER = ROOT / "paper"
XLSX = ROOT / "data" / "raw" / "Data Morocco.xlsx"
OUTAGE = ROOT / "results" / "downstream_v1"
CAT = ROOT / "results" / "catalogue_final" / "catalogue.csv"
CM = 1 / 2.54
W, H = 13 * CM, 5.2 * CM
INK, MUTED = "#1F2328", "#57606A"
FS = dict(head=9, base=8, small=7.5)
ART, GRID = COL["artefact"], COL["grid"]          # red = acquisition artefact, blue = grid event

EXAMPLES = [  # (city, zone, key, start, end, colour, label, date) -- both on feeder F1 of Foum El Oued
    ("Foum eloued", "zone1", "artefact", "2023-01-25 12:00", "2023-01-29 18:00", ART, "Artefact: repair", "Jan 2023"),
    ("Foum eloued", "zone1", "grid", "2024-04-29 20:00", "2024-04-30 20:00", GRID, "Grid event: keep", "Apr 2024"),
]


def check_examples():
    """The labels the graphical abstract shows must be the catalogue's."""
    cat = pd.read_csv(CAT)
    jan = cat[(cat.start == "2023-01-26 02:10") & cat.zones.str.contains("F1")]
    zero = cat[(cat.start == "2023-01-28 21:10") & cat.zones.str.contains("F1")]
    pw = cat[(cat.start == "2024-04-30 08:20") & (cat.zones == "F1")]
    assert list(jan.label) == ["A2"] and list(zero.label) == ["A1"] and list(pw.label) == ["G4"], "catalogue changed"
    assert zero.n_zones.iloc[0] == 15 and pw.n_zones.iloc[0] == 1
    return dict(fill=(jan.label.iloc[0], jan.confidence.iloc[0]), zero=(zero.label.iloc[0], zero.confidence.iloc[0]),
                planned_work=(pw.label.iloc[0], pw.confidence.iloc[0], pw.duration_h.iloc[0]))


def trace(ax, res, city, zone, t0, t1):
    """Recorded series with its states shaded by cause: fills and zeros in red tints, the noise floor in blue."""
    x = res["data"][city][zone][t0:t1]
    mk = {k: res["masks"][city][k][zone][t0:t1] for k in ("dead", "hold", "interp")}
    zero, floor = mk["dead"] & x.eq(0), mk["dead"] & ~x.eq(0)
    tr = ax.get_xaxis_transform()
    for m, c, a in [(mk["hold"] | mk["interp"], ART, .20), (zero, ART, .45), (floor, GRID, .30)]:
        ax.fill_between(x.index, 0, 1, where=m.to_numpy(), step="post", color=c, alpha=a, lw=0, transform=tr)
    ax.plot(x.index, x.values, color=COL["trace"], lw=.6, drawstyle="steps-post")
    ax.set_xlim(x.index[0], x.index[-1]); ax.set_ylim(0, np.nanmax(x.values) * 1.5)   # room for the labels
    ax.set_xticks([]); ax.set_yticks([])
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#999")
    return dict(fill=mk["hold"] | mk["interp"], zero=zero, floor=floor)


def span_label(ax, mask, text, colour):
    """Direct label above the longest run of a state."""
    m = np.append(mask.to_numpy(), False)
    runs, start = [], None
    for i, v in enumerate(m):
        if v and start is None:
            start = i
        elif not v and start is not None:
            runs.append((start, i - 1)); start = None
    if not runs:
        return
    a, b = max(runs, key=lambda r: r[1] - r[0])
    mid = mask.index[a] + (mask.index[b] - mask.index[a]) / 2
    ax.text(mid, 0.99, text, transform=ax.get_xaxis_transform(), ha="center", va="top", fontsize=FS["small"],
            color=colour, weight="bold")


def box(ax, x, y, w, h, head, body, ec, fc="white"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.003,rounding_size=0.01", fc=fc, ec=ec, lw=.8))
    ax.text(x + 0.012, y + h - 0.03, head, ha="left", va="top", fontsize=FS["base"], weight="bold", color=INK,
            linespacing=1.05)
    ax.text(x + 0.012, y + 0.035, body, ha="left", va="bottom", fontsize=FS["small"], color=INK, linespacing=1.05)


def main(preview=None):
    labels = check_examples()
    real = pd.read_csv(OUTAGE / "outage_real.csv")
    art_h, grid_h = real.artefact_dead_zone_hours.sum(), real.typed_zone_hours.sum()
    naive_h = real.naive_zone_hours.sum()
    assert abs(art_h + grid_h - naive_h) < 0.1, (art_h, grid_h, naive_h)
    per = pd.read_csv(OUTAGE / "outage_all" / "outage_per_dataset.csv")
    assert len(per) == 30
    naive_r, typed_r = per.naive_ratio.to_numpy(), per.typed_ratio.to_numpy()
    res = R1.build(XLSX)

    plt.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "font.size": FS["base"]})
    fig = plt.figure(figsize=(W, H))
    ov = fig.add_axes([0, 0, 1, 1], zorder=0); ov.set_xlim(0, 1); ov.set_ylim(0, 1); ov.axis("off")
    # columns (figure fraction; 13 cm = 368.5 pt): 1: 0.012-0.345, 2: 0.378-0.585, 3: 0.618-0.990
    c1x, c1w, c2x, c2w, c3x, c3w = 0.012, 0.333, 0.378, 0.207, 0.618, 0.372
    for x, t in [(c1x, "One feeder, two causes"), (c2x, "No labels"), (c3x, "What it changes")]:
        ov.text(x, 0.975, t, ha="left", va="top", fontsize=FS["head"], weight="bold", color=INK)

    # column 1: two real traces of feeder F1
    found = {}
    for (city, zone, key, t0, t1, colr, lab, date), y0 in zip(EXAMPLES, [0.50, 0.075]):
        h = 0.245
        ov.text(c1x, y0 + h + 0.075, lab, ha="left", va="center", fontsize=FS["base"], weight="bold", color=colr)
        ov.text(c1x + c1w, y0 + h + 0.075, date, ha="right", va="center", fontsize=FS["small"], color=MUTED)
        ax = fig.add_axes([c1x, y0, c1w, h], zorder=2)
        st = trace(ax, res, city, zone, pd.Timestamp(t0), pd.Timestamp(t1))
        found[key] = {k: int(v.sum()) for k, v in st.items()}
        if key == "artefact":
            span_label(ax, st["fill"], "straight line", ART)
            span_label(ax, st["zero"], "zeros", ART)
            note = "all 15 zones"
        else:
            span_label(ax, st["floor"], "noise floor", GRID)
            note = "one feeder"
        ax.text(1.0, -0.05, note, transform=ax.transAxes, ha="right", va="top", fontsize=FS["small"], color=MUTED)

    # column 2: the method
    box(ov, c2x, 0.665, c2w, 0.24, "Where?", "feeder to region,\nor recording chain", "#8C959F")
    box(ov, c2x, 0.355, c2w, 0.24, "Which trace?", "line, zero,\nnoise floor", "#8C959F")
    box(ov, c2x, 0.02, c2w, 0.265, "19 rules +\nlabel model", "p(each cause)", INK, fc="#F6F8FA")
    for y_from, y_to in [(0.665, 0.595), (0.355, 0.285)]:
        ov.add_patch(FancyArrowPatch((c2x + c2w / 2, y_from), (c2x + c2w / 2, y_to), arrowstyle="-|>",
                                     mutation_scale=6, color=INK, lw=.8))
    for xa, xb in [(c1x + c1w + 0.006, c2x - 0.006), (c2x + c2w + 0.006, c3x - 0.006)]:
        ov.add_patch(FancyArrowPatch((xa, 0.46), (xb, 0.46), arrowstyle="-|>", mutation_scale=7, color=INK, lw=.8))

    # column 3a: real dead zone-hours by type
    ov.text(c3x, 0.865, "Dead zone-hours (our typing)", ha="left", va="top", fontsize=FS["small"], color=INK)
    a1 = fig.add_axes([c3x, 0.655, c3w, 0.1], zorder=2)
    fa = art_h / naive_h
    a1.barh(0, fa, color=ART, height=1, edgecolor="white", lw=1)
    a1.barh(0, 1 - fa, left=fa, color=GRID, height=1, edgecolor="white", lw=1)
    a1.set_xlim(0, 1); a1.set_ylim(-.5, .5); a1.axis("off")
    a1.text(0.025, 0, f"artefacts {fa:.0%}", ha="left", va="center", fontsize=FS["small"], color="white", weight="bold")
    a1.text(1 - (1 - fa) / 2, 0, f"{1 - fa:.0%}", ha="center", va="center", fontsize=FS["small"], color="white",
            weight="bold")
    ov.text(c3x + c3w, 0.63, "grid events", ha="right", va="top", fontsize=FS["small"], color=GRID, weight="bold")
    # column 3b: outage time relative to the truth, 30 injected datasets
    ov.text(c3x, 0.445, "Outage time vs truth", ha="left", va="top", fontsize=FS["small"], color=INK)
    a2 = fig.add_axes([c3x + 0.085, 0.075, c3w - 0.085, 0.27], zorder=2)
    rng = np.random.default_rng(0)
    for row, vals, colr in [(1, naive_r, MUTED), (0, typed_r, GRID)]:   # typed counting counts grid events: blue
        a2.scatter(vals, row + rng.uniform(-.15, .15, len(vals)), s=4, color=colr, alpha=.55, lw=0)
        a2.scatter([vals.mean()], [row], s=26, color=colr, edgecolor="white", lw=.6, zorder=3)
        a2.text(vals.mean() + 0.08, row + 0.2, f"{vals.mean():.2f}×", ha="left", va="bottom", fontsize=FS["base"],
                color=colr, weight="bold")
    a2.axvline(1, color=INK, lw=.7, ls=(0, (2, 1.5)))
    a2.text(1.0, -0.42, "truth", ha="center", va="top", fontsize=FS["small"], color=INK)
    a2.set_yticks([1, 0]); a2.set_yticklabels(["naive", "typed"], fontsize=FS["small"])
    a2.set_ylim(-.4, 1.65); a2.set_xlim(0.85, 2.7)
    a2.set_xticks([]); a2.tick_params(axis="y", length=0, pad=1)
    for s in ("top", "right", "left", "bottom"):
        a2.spines[s].set_visible(False)

    pdf, tif = PAPER / "graphical_abstract.pdf", PAPER / "graphical_abstract.tif"
    fig.savefig(pdf)
    fig.savefig(tif, dpi=300, facecolor="white", pil_kwargs={"compression": "tiff_lzw"})
    from PIL import Image
    Image.open(tif).convert("RGB").save(tif, compression="tiff_lzw", dpi=(300, 300))   # no alpha channel
    if preview:
        fig.savefig(Path(preview) / "ga_96dpi.png", dpi=96)      # the size the journal checks readability at
        fig.savefig(Path(preview) / "ga_300dpi.png", dpi=300)
    plt.close(fig)
    print("labels:", labels)
    print("state steps in the windows:", found)
    print(f"dead zone-hours: artefacts {art_h:.1f}, grid events {grid_h:.1f}, all {naive_h:.1f} ({fa:.1%} artefacts)")
    print(f"outage / truth: naive {naive_r.mean():.2f}, typed {typed_r.mean():.2f} (30 datasets)")
    print("written:", pdf, tif, Image.open(tif).size, Image.open(tif).mode)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", default=None)
    main(ap.parse_args().preview)
