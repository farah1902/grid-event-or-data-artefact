"""viz.py - shared plotting style and helpers (one hue per class family, spans shaded by state)."""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

COL = dict(
    artefact="#C8553D", grid="#2F6690", normal="#9AA0A6",
    hold="#F2A541", interp="#2A9D8F", zero="#C8553D", dead="#7B5EA7", missing="#222222",
    expected="#6C757D", trace="#1F2328",
)
LABEL_COL = {  # artefacts warm, grid events blue, family-only votes light
    "A1": "#C8553D", "A2": "#F2A541", "A3": "#E9C46A", "A4": "#8C2F39",
    "G1": "#0B2545", "G2": "#1D4E89", "G3": "#3E7CB1", "G4": "#6CC3E0", "G5": "#2A9D8F", "G": "#A3BFD9",
}
CITY_SHORT = {"Laayoune": "L", "Boujdour": "B", "Foum eloued": "F", "Marrakech": "M"}

plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": 200, "font.size": 9, "axes.titlesize": 10,
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
})


def savefig(fig, folder, name):
    for ext in ("png", "pdf"):
        fig.savefig(f"{folder}/{name}.{ext}", bbox_inches="tight")
    print("saved", f"{folder}/{name}.png")


def zone_list(data, cities):
    return [(c, z) for c in cities for z in data[c].columns]


def stack_plot(data, exp, masks, t0, t1, zones, title="", marks=(), highlight=(), row_h=0.55):
    """One row per zone: raw x (black), expected x_hat (grey dashed), spans shaded by state."""
    t0, t1 = pd.Timestamp(t0), pd.Timestamp(t1)
    fig, axes = plt.subplots(len(zones), 1, figsize=(10, row_h * len(zones) + 1.4), sharex=True)
    axes = np.atleast_1d(axes)
    for ax, (c, z) in zip(axes, zones):
        x, xh = data[c][z][t0:t1], exp[c][z][t0:t1]
        dead = masks[c]["dead"][z][t0:t1]
        spans = [("hold", masks[c]["hold"][z][t0:t1], .45), ("interp", masks[c]["interp"][z][t0:t1], .35),
                 ("zero", dead & x.eq(0), .35), ("dead", dead & ~x.eq(0), .35), ("missing", x.isna(), .25)]
        tr = ax.get_xaxis_transform()
        for k, m, a in spans:
            ax.fill_between(x.index, 0, 1, where=m.to_numpy(), step="post", color=COL[k], alpha=a, lw=0, transform=tr)
        ax.plot(xh.index, xh.values, color=COL["expected"], lw=.7, ls="--")
        ax.plot(x.index, x.values, color=COL["trace"], lw=.8, drawstyle="steps-post")
        hl = (c, z) in highlight
        ax.set_ylabel(f"{CITY_SHORT[c]}{z.replace('zone', '')}", rotation=0, ha="right", va="center", fontsize=8,
                      fontweight="bold" if hl else "normal", color=COL["artefact"] if hl else "black")
        ax.set_yticks([])
        ax.spines["left"].set_visible(False)
        ymax = np.nanmax([x.max(), xh.max()]) if len(x) else 1
        ax.set_ylim(0, (ymax if np.isfinite(ymax) and ymax > 0 else 1) * 1.15)
        for tm, _ in marks:
            ax.axvline(pd.Timestamp(tm), color="#444", lw=.8, ls=":")
    for i, (tm, txt) in enumerate(marks):
        axes[0].annotate(txt, (pd.Timestamp(tm), 1.02 + 0.35 * (i % 2)), xycoords=("data", "axes fraction"),
                         fontsize=7.5, ha="left", va="bottom")
    axes[-1].set_xlim(t0, t1)
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%d %b\n%H:%M"))
    leg = [Patch(color=COL["hold"], alpha=.6, label="held value"),
           Patch(color=COL["interp"], alpha=.5, label="linear interpolation"),
           Patch(color=COL["zero"], alpha=.5, label="exact zero"),
           Patch(color=COL["dead"], alpha=.5, label="dead, noise floor"),
           Patch(color=COL["missing"], alpha=.4, label="missing stamp"),
           Line2D([], [], color=COL["trace"], lw=1, label="x (as recorded)"),
           Line2D([], [], color=COL["expected"], lw=1, ls="--", label="expected x̂")]
    fig.legend(handles=leg, loc="lower center", ncol=4, fontsize=7.5, bbox_to_anchor=(.5, -.01))
    fig.suptitle(title, y=1.0)
    fig.tight_layout(rect=(0, .07, 1, .97))
    fig.subplots_adjust(hspace=.08)
    return fig, axes
