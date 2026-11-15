"""NB7: the final catalogue, the figures drawn for the paper (Fig 1, 2, 6), the regenerated figures (Fig 8, Fig 9,
E4, E6, E19, E22) and the paper table set. Everything reads stored results; nothing here changes a method result.
Decisions D72-D75."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Polygon, Rectangle

from viz import COL, LABEL_COL, savefig

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
CLASSES = ["A1", "A2", "A3", "A4", "G1", "G2", "G3", "G4", "G5", "N"]
INK = "#1F2328"
LABEL_COL_N = {**LABEL_COL, "N": "#9AA0A6"}

# Approximate city locations (degrees, WGS84; city centres, for a country-scale map only)
CITIES = {"Laayoune": (-13.20, 27.15), "Foum eloued": (-13.40, 27.19), "Boujdour": (-14.48, 26.13),
          "Marrakech": (-7.99, 31.63), "Tetouan": (-5.37, 35.57)}
CITY_NAME = {"Laayoune": "Laâyoune", "Boujdour": "Boujdour", "Foum eloued": "Foum El Oued", "Marrakech": "Marrakech", "Tetouan": "Tetouan"}


# ====================================================================== final catalogue (D72)
def final_catalogue():
    """One table of every item and detector-only candidate with its final label and distribution.
    Sources: south dead/fill = fusion with the main detector (NB4 sec. 8b); Marrakech dead/fill = NB3 fusion;
    clock and transfer = label model (NB2); detector-only = end model via fusion (south: main detector, XS###;
    Marrakech: NB3 LightGBM detector, XM###)."""
    q = pd.read_csv(RES / "labels_v1" / "q.csv", parse_dates=["start", "end"])
    south = pd.read_csv(RES / "main_detector" / "p_type_south.csv", parse_dates=["start", "end"])
    nb3 = pd.read_csv(RES / "end_model_v1" / "p_type.csv")
    det_s = pd.read_csv(RES / "main_detector" / "detector_items_south.csv", parse_dates=["start", "end"])
    det_3 = pd.read_csv(RES / "detector_v1" / "detector_items.csv", parse_dates=["start", "end"])
    rows = []
    base_cols = ["item_id", "kind", "episode", "system", "start", "end", "duration_h", "cities", "zones", "n_cities", "n_zones", "votes"]
    s_rule = south[south.source == "rule"].set_index("item_id")
    n_rule = nb3[nb3.source == "rule"].set_index("item_id")
    for r in q.itertuples():
        d = {c: getattr(r, c) for c in base_cols}
        d["source"] = "rule"
        if r.kind in ("dead", "fill") and r.system == "south":
            p = {c: float(s_rule.at[r.item_id, f"p_{c}"]) if f"p_{c}" in s_rule.columns else 0.0 for c in CLASSES}
            d["label_source"] = "fusion, main detector (NB4 8b)"
        elif r.kind in ("dead", "fill"):
            p = {c: float(n_rule.at[r.item_id, f"p_{c}"]) if f"p_{c}" in n_rule.columns else 0.0 for c in CLASSES}
            d["label_source"] = "fusion, NB3"
        else:
            p = {c: float(getattr(r, f"q_{c}")) for c in CLASSES}
            d["label_source"] = "label model (NB2)"
        d.update({f"p_{c}": round(v, 4) for c, v in p.items()})
        rows.append(d)
    s_det = south[south.source == "detector"].set_index("item_id")
    for r in det_s.itertuples():
        d = dict(item_id="XS" + r.item_id[1:], kind="detector", episode=np.nan, system="south", start=r.start, end=r.end,
                 duration_h=r.duration_h, cities=r.cities, zones=r.zones, n_cities=r.n_cities, n_zones=r.n_zones, votes="",
                 source="detector", label_source="fusion, main detector (NB4 8b)")
        d.update({f"p_{c}": round(float(s_det.at[r.item_id, f"p_{c}"]), 4) if f"p_{c}" in s_det.columns else 0.0 for c in CLASSES})
        rows.append(d)
    n_det = nb3[nb3.source == "detector"].set_index("item_id")
    for r in det_3[det_3.system == "Marrakech"].itertuples():
        d = dict(item_id="XM" + r.item_id[1:], kind="detector", episode=np.nan, system="Marrakech", start=r.start, end=r.end,
                 duration_h=r.duration_h, cities=r.cities, zones=r.zones, n_cities=r.n_cities, n_zones=r.n_zones, votes="",
                 source="detector", label_source="fusion, NB3")
        d.update({f"p_{c}": round(float(n_det.at[r.item_id, f"p_{c}"]), 4) if f"p_{c}" in n_det.columns else 0.0 for c in CLASSES})
        rows.append(d)
    cat = pd.DataFrame(rows)
    P = cat[[f"p_{c}" for c in CLASSES]].to_numpy()
    cat["label"] = np.array(CLASSES)[P.argmax(1)]
    cat["confidence"] = P.max(1).round(4)
    cat["family"] = cat.label.map(lambda l: "artefact" if l.startswith("A") else ("grid event" if l.startswith("G") else "normal / untyped"))
    first = ["item_id", "system", "kind", "source", "start", "end", "duration_h", "cities", "zones", "n_cities", "n_zones",
             "episode", "label", "confidence", "family", "label_source", "votes"]
    return cat[first + [f"p_{c}" for c in CLASSES]].sort_values(["system", "start"]).reset_index(drop=True)


def final_episodes(cat):
    ep = pd.read_csv(RES / "labels_v1" / "episodes_labelled.csv", parse_dates=["start", "end"])
    lab = cat.set_index("item_id")
    seqs, fams = [], []
    for r in ep.itertuples():
        ids = [i for i in r.items.split(",") if i in lab.index]
        ids = sorted(ids, key=lambda i: lab.at[i, "start"])
        seqs.append(" → ".join(f"{lab.at[i, 'label']}({lab.at[i, 'confidence']:.2f})" for i in ids))
        fams.append(",".join(sorted(set(lab.loc[ids, "family"]))))
    return ep.assign(sequence_final=seqs, families_final=fams)


def key_events_table(cat, eps):
    ke = pd.read_csv(RES / "catalogue_v1" / "key_events_v1.csv")
    lab = cat.set_index("item_id"); epi = eps.set_index("episode")
    rows = []
    for r in ke.itertuples():
        it = lab.loc[r.item] if r.item in lab.index else None
        rows.append(dict(guide_id=r.guide_id, item=r.item, kind=r.kind, start=r.start, duration_h=r.h, zones=r.zones,
                         label=None if it is None else it.label, confidence=None if it is None else it.confidence,
                         episode=r.episode, episode_sequence=epi.at[r.episode, "sequence_final"] if r.episode in epi.index else ""))
    return pd.DataFrame(rows)


# ====================================================================== Fig 1: basemap + coverage (D73)
def _save(fig, fig_dir, name, paper_name=None):
    """Repo figures: png + pdf under the source name (viz.savefig). Paper mode (paper_name given): one PDF under the
    submission name; the caller sets TrueType fonts (pdf.fonttype 42), and the caption carries the title."""
    if paper_name:
        fig.savefig(f"{fig_dir}/{paper_name}.pdf", bbox_inches="tight")
        print("saved", f"{fig_dir}/{paper_name}.pdf")
    else:
        savefig(fig, fig_dir, name)


def _land(path, bbox):
    gj = json.loads(Path(path).read_text())
    x0, x1, y0, y1 = bbox
    polys = []
    for f in gj["features"]:
        g = f["geometry"]
        rings = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        for poly in rings:
            ring = np.asarray(poly[0])
            if ring[:, 0].max() < x0 or ring[:, 0].min() > x1 or ring[:, 1].max() < y0 or ring[:, 1].min() > y1:
                continue
            polys.append(ring)
    return polys


def fig1_map_coverage(res, fig_dir, land_path, paper_name=None):
    fig = plt.figure(figsize=(15, 7.2))
    ax = fig.add_axes([0.02, 0.08, 0.36, 0.84])
    bbox = (-19.5, 1.0, 20.5, 37.5)
    for ring in _land(land_path, bbox):
        ax.add_patch(Polygon(ring, closed=True, fc="#F3F1EC", ec="#8A8A8A", lw=0.6))
    ax.set_xlim(bbox[0], bbox[1]); ax.set_ylim(bbox[2], bbox[3])
    ax.set_aspect(1 / np.cos(np.radians(29)))
    ax.set_facecolor("#E8F1F8")
    styles = {"Laayoune": ("#C8553D", "o"), "Foum eloued": ("#C8553D", "o"), "Boujdour": ("#C8553D", "o"),
              "Marrakech": ("#2F6690", "s"), "Tetouan": ("#5F6B76", "D")}
    for c, (x, y) in CITIES.items():
        col, mk = styles[c]
        ax.plot(x, y, mk, color=col, ms=8 if c in ("Marrakech", "Tetouan") else 5, mec="white", mew=1.0, zorder=5)
    wb = dict(boxstyle="round,pad=0.3", fc="white", ec="none", alpha=0.9)
    ax.text(CITIES["Tetouan"][0] + 0.5, CITIES["Tetouan"][1] - 0.15, "Tetouan", ha="left", va="center", fontsize=9, weight="bold", color=INK, zorder=6)
    ax.text(-10.2, 35.9, "transfer test (UCI Tetouan)\n3 zones · 10 min · 2017", ha="center", va="center", fontsize=7.6, color="#5F6B76", bbox=wb, zorder=6)
    ax.text(CITIES["Marrakech"][0] + 0.5, CITIES["Marrakech"][1], "Marrakech", ha="left", va="center", fontsize=9, weight="bold", color=INK, zorder=6)
    ax.text(-12.6, 31.8, "separate system\n2 zones · 30 min · kW · 2023", ha="center", va="center", fontsize=7.6, color="#2F6690", bbox=wb, zorder=6)
    zx0, zx1, zy0, zy1 = -15.1, -12.4, 25.7, 27.7
    ax.add_patch(Rectangle((zx0, zy0), zx1 - zx0, zy1 - zy0, fc="none", ec="#C8553D", lw=1.3, ls="--", zorder=4))
    ax.text(-17.6, 24.1, "southern system\none shared timeline\n15 zones · 10 min · A\nSep 2022 – May 2024", ha="center", va="center",
            fontsize=7.6, color="#C8553D", bbox=wb, zorder=6)
    # inset: the three southern cities (Laâyoune and Foum El Oued are about 20 km apart)
    ins = ax.inset_axes([0.56, 0.06, 0.41, 0.34])
    for ring in _land(land_path, (zx0 - 1, zx1 + 1, zy0 - 1, zy1 + 1)):
        ins.add_patch(Polygon(ring, closed=True, fc="#F3F1EC", ec="#8A8A8A", lw=0.6))
    ins.set_xlim(zx0, zx1); ins.set_ylim(zy0, zy1); ins.set_aspect(1 / np.cos(np.radians(26.7))); ins.set_facecolor("#E8F1F8")
    for c, (dx, dy, ha) in {"Laayoune": (0.05, -0.2, "center"), "Foum eloued": (-0.08, 0.13, "right"), "Boujdour": (0.1, 0.0, "left")}.items():
        x, y = CITIES[c]
        ins.plot(x, y, "o", color="#C8553D", ms=6, mec="white", mew=1.0, zorder=5)
        ins.text(x + dx, y + dy, CITY_NAME[c] + {"Laayoune": " (L1–L5)", "Foum eloued": " (F1–F7)", "Boujdour": " (B1–B3)"}[c],
                 ha=ha, va="center", fontsize=7.5, weight="bold", color=INK)
    ins.set_xticks([]); ins.set_yticks([])
    for sp in ins.spines.values():
        sp.set_visible(True); sp.set_edgecolor("#C8553D"); sp.set_linestyle("--")
    ax.indicate_inset_zoom(ins, edgecolor="#C8553D", alpha=0.6)
    # scale bar: 200 km at 22 N
    km_per_deg = 111.32 * np.cos(np.radians(22))
    ax.plot([-12.8, -12.8 + 200 / km_per_deg], [21.2, 21.2], color=INK, lw=2.5)
    ax.text(-12.8 + 100 / km_per_deg, 21.55, "200 km (at 22°N)", ha="center", fontsize=7.5)
    ax.set_xticks([-15, -10, -5, 0]); ax.set_xticklabels(["15°W", "10°W", "5°W", "0°"], fontsize=7.5)
    ax.set_yticks([22, 26, 30, 34]); ax.set_yticklabels(["22°N", "26°N", "30°N", "34°N"], fontsize=7.5)
    ax.set_title("(a) data sets (coastline: Natural Earth 1:50m; no boundaries drawn)", fontsize=9)

    # (b) coverage: flagged states inside qualifying rule runs (rule engine v1 priority, D16), missing steps
    axb = fig.add_axes([0.45, 0.1, 0.53, 0.8])
    zr = res["zone_runs"]
    rows = []
    for c in ["Laayoune", "Boujdour", "Foum eloued", "Marrakech"]:
        for z in res["data"][c].columns:
            rows.append((c, z, f"{CITY_NAME[c][0] if c != 'Foum eloued' else 'F'}{z.replace('zone', '')}"))
    yt = []
    for k, (c, z, code) in enumerate(rows[::-1]):
        d = res["data"][c][z]
        axb.add_patch(Rectangle((mdates.date2num(d.index[0]), k - 0.35), mdates.date2num(d.index[-1]) - mdates.date2num(d.index[0]), 0.7,
                                fc="#F4F4F4", ec="none"))
        sub = zr[(zr.city == c) & (zr.zone == z)]
        for r in sub.itertuples():
            if r.kind == "dead":
                seg = d.loc[r.start:r.end - pd.Timedelta(minutes=1)].to_numpy()
                kind = "zero" if np.nanmean(seg == 0) >= 0.5 else "dead"
            else:
                kind = r.kind
            a, b = mdates.date2num(r.start), mdates.date2num(r.end)
            axb.add_patch(Rectangle((a, k - 0.35), max(b - a, 0.06), 0.7, fc=COL[kind], ec="none"))
        miss = d.isna().to_numpy()
        for a, b in _runs(miss):
            axb.add_patch(Rectangle((mdates.date2num(d.index[a]), k - 0.35), max(mdates.date2num(d.index[b]) - mdates.date2num(d.index[a]), 0.06),
                                    0.7, fc=COL["missing"], ec="none"))
        yt.append(code)
    axb.set_yticks(range(len(rows))); axb.set_yticklabels(yt, fontsize=7.5)
    axb.set_ylim(-0.7, len(rows) - 0.3)
    axb.set_xlim(mdates.date2num(pd.Timestamp("2022-09-10")), mdates.date2num(pd.Timestamp("2024-05-28")))
    axb.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10])); axb.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
    for y in (1.5, 8.5, 11.5):
        axb.axhline(y, color="#BBBBBB", lw=0.6)
    import rules_v1 as R1
    for dte in R1.EUROPE_DST + R1.MOROCCO_DST:
        t = pd.Timestamp(dte)
        if pd.Timestamp("2022-09-01") < t < pd.Timestamp("2024-06-01"):
            axb.axvline(mdates.date2num(t), color="#888", lw=0.6, ls=":")
    handles = [Rectangle((0, 0), 1, 1, fc=COL[k]) for k in ("hold", "interp", "zero", "dead", "missing")]
    axb.legend(handles, ["hold (frozen value)", "straight-line fill", "exact zeros", "noise floor (≤ 5 % of x̂)", "missing step"],
               ncol=5, fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, -0.07), frameon=False)
    axb.set_title("(b) anomalous states per zone (qualifying runs; dotted: clock-change dates)", fontsize=9)
    for sp in ("top", "right"):
        axb.spines[sp].set_visible(False)
    if not paper_name:
        fig.suptitle("Fig 1 — Data: the southern system, Marrakech and the Tetouan transfer set; where the anomalous states are", y=0.99, fontsize=11)
    _save(fig, fig_dir, "fig1_map_coverage", paper_name)
    return fig


def _runs(m):
    m = np.asarray(m, bool)
    if not m.any():
        return []
    d = np.diff(np.r_[0, m.astype(int), 0])
    return list(zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1) - 1))


# ====================================================================== Fig 2: typology (schematic signatures)
TYPOLOGY = [
    # code, name, family, level, signature, rules
    ("A1", "zero-fill gap", "artefact", "region (≥ 2 cities) or episode",
     "exact zeros (η = 1) in ≥ 2 cities at once, often after a hold or straight-line fill; returns at once", "R1, R3, R4, R21"),
    ("A2", "simultaneous fill", "artefact", "≥ 2 zones",
     "≥ 2 zones frozen (identical values) or straight-line interpolated over the same span", "R2, R19"),
    ("A3", "single-zone fill", "artefact", "zone",
     "one zone frozen or straight-line interpolated; neighbours move normally", "R12, R20"),
    ("A4", "clock error", "artefact", "system, one day",
     "daily profile shifted by δ* ≈ ±60 min after a clock-change date; duplicated or missing stamps", "R13, R14, R15"),
    ("G1", "regional outage", "grid event", "region (≥ 2 cities)",
     "noise floor (η < 0.9) in ≥ 2 cities; hypothesised: ramp restoration with cold-load overshoot π ≥ 1.15", "R5, R6, R7"),
    ("G2", "city outage", "grid event", "city",
     "all zones of one city at the noise floor, the other cities normal", "R8 (+ R5, R6)"),
    ("G3", "unplanned feeder outage", "grid event", "zone",
     "one zone at the noise floor at any hour, possibly > 24 h; hypothesised: ramp restoration", "R9, R11 (+ R6)"),
    ("G4", "planned work", "grid event", "zone",
     "one zone at the noise floor, starting 06:00–11:59, short (< 6 h)", "R10"),
    ("G5", "load transfer", "grid event", "≥ 2 zones of a city",
     "one zone steps down while another steps up by the same amount (conservation κ ≈ 0)", "R16"),
]


def _profile(t, phase=0.0, level=1.0):
    h = (t % 24)
    return level * (0.75 + 0.18 * np.sin(2 * np.pi * (h - 9 + phase) / 24) + 0.1 * np.exp(-((h - 20 + phase) / 2.2) ** 2))


def fig2_typology(fig_dir, paper_name=None):
    t = np.arange(0, 48, 1 / 6)
    fig, axs = plt.subplots(3, 3, figsize=(15, 10.2))
    rng = np.random.default_rng(3)
    for ax, (code, name, fam, level, sig, rules) in zip(axs.ravel(), TYPOLOGY):
        c_ev = LABEL_COL_N[code]
        offs = [2.4, 1.2, 0.0]                                  # three zones: zone 1 of city X, zones 1-2 of city Y
        labels = ["city X · zone 1", "city Y · zone 1", "city Y · zone 2"]
        lv = [1.0, 0.8, 0.9]
        a, b = 18, 30                                           # event span (hours)
        seg = (t >= a) & (t < b)
        for k in range(3):
            exp = _profile(t, 0, lv[k])
            x = exp + rng.normal(0, 0.015, len(t))
            hit = {"A1": [0, 1, 2], "A2": [1, 2], "A3": [2], "G1": [0, 1, 2], "G2": [1, 2], "G3": [2], "G4": [2], "G5": [1, 2], "A4": [0, 1, 2]}[code]
            if k in hit:
                if code == "A1":
                    if k == 0:                                                                # compound: hold, then zeros
                        hs = (t >= a - 5) & (t < a)
                        x[hs] = x[np.flatnonzero(hs)[0] - 1]
                    x[seg] = 0.0
                elif code == "A2" or code == "A3":
                    i0, i1 = np.flatnonzero(seg)[[0, -1]]
                    if k == 2 or code == "A3":
                        x[seg] = np.linspace(x[i0 - 1], x[i1 + 1], seg.sum())                  # straight-line fill
                    else:
                        x[seg] = x[i0 - 1]                                                    # hold
                elif code in ("G1", "G2", "G3"):
                    x[seg] = 0.03 * lv[k] + rng.uniform(0, 0.015, seg.sum())
                    rs = (t >= b) & (t < b + 2.5)
                    ramp = np.linspace(0.2, 1.25, rs.sum())
                    x[rs] = exp[rs] * ramp
                elif code == "G4":
                    s4 = (t >= 32) & (t < 36)
                    x[s4] = 0.03 * lv[k]
                elif code == "G5":
                    s5 = t >= a
                    x[s5] = x[s5] + (-0.25 if k == 1 else 0.25)
                elif code == "A4":
                    s6 = t >= 24
                    x[s6] = _profile(t[s6], phase=1.0, level=lv[k]) + rng.normal(0, 0.015, s6.sum())
            ax.plot(t, exp + offs[k], color="#9AA0A6", lw=0.8, ls="--")
            ax.plot(t, x + offs[k], color=INK, lw=1.0)
            ax.text(-0.5, offs[k] + lv[k] * 0.75, labels[k], ha="right", va="center", fontsize=7, color="#555")
        span = {"G4": (32, 36), "G5": (a, 48), "A4": (24, 48)}.get(code, (a, b))
        ax.axvspan(*span, color=c_ev, alpha=0.18, lw=0)
        note = {"A1": "exact zeros, instant return\n(here after a hold)", "G1": "noise floor, then ramp + overshoot\n(hypothesised)",
                "G2": "one city at the noise floor", "A2": "hold + straight line", "A3": "straight line", "A4": "profile shifted 60 min",
                "G5": "−Δ / +Δ (conserved)"}.get(code)
        if note:
            ax.text(span[0] + 0.4, 4.32, note, fontsize=7.2, color=INK, va="top", style="italic")
        if code == "A1":
            hs0 = a - 5
            ax.axvspan(hs0, a, color=LABEL_COL_N["A2"], alpha=0.18, lw=0)
        ax.set_title(f"{code} · {name}", fontsize=10.5, weight="bold", color=c_ev if code != "N" else INK, loc="left")
        ax.set_xlim(-0.2, 48); ax.set_ylim(-0.25, 4.4)
        ax.set_yticks([]); ax.set_xticks([0, 12, 24, 36, 48]); ax.set_xticklabels(["0 h", "12 h", "24 h", "36 h", "48 h"], fontsize=7)
        for sp in ("top", "right", "left"):
            ax.spines[sp].set_visible(False)
        import textwrap
        ax.text(0.0, -0.13, f"level: {level}\n" + textwrap.fill(f"signature: {sig}", 62) + f"\nrules: {rules}",
                transform=ax.transAxes, ha="left", va="top", fontsize=7.6, color=INK, linespacing=1.3)
    fig.text(0.5, 0.005, "dashed: expected value x̂ (Eq. 1) · black: observed · shaded: the event span · "
             "artefacts A1–A4 are data failures (impute); grid events G1–G5 are real (keep and flag)",
             ha="center", fontsize=8.5, color="#444")
    if not paper_name:
        fig.suptitle("Fig 2 — Typology: four artefacts and five grid events, each with a measurable signature at a level of the hierarchy "
                     "(schematic; straight-line fills are part of A2 and A3)", y=0.995, fontsize=11)
    fig.tight_layout(rect=(0.03, 0.03, 1, 0.975 if not paper_name else 1.0), h_pad=6.0, w_pad=4.5)
    _save(fig, fig_dir, "fig2_typology", paper_name)
    return fig


def table2_typology(cat):
    n = cat[cat.source == "rule"].groupby("label").size()
    nd = cat[cat.source == "detector"].groupby("label").size()
    inj = {"A1": "yes", "A2": "yes", "A3": "yes", "A4": "no (calendar-gated rules)", "G1": "yes (no real example)", "G2": "yes",
           "G3": "yes", "G4": "yes", "G5": "no (weeks long)"}
    return pd.DataFrame([dict(type=c, name=nm, family=f, hierarchy_level=lv, measurable_signature=s, rules=r,
                              real_rule_items=int(n.get(c, 0)), real_detector_only=int(nd.get(c, 0)), injected_in_NB4=inj[c])
                         for c, nm, f, lv, s, r in TYPOLOGY])


# ====================================================================== Fig 6: framework (paper Figure 3)
# Drawn in points: the drawing area is FW_W x FW_H pt (17.5 x 9.4 in) and 1 data unit = 1 pt in both directions. The paper
# prints it at the text width (390 pt, x 0.31), so the text is as large as the boxes allow (D104): body 14.5 pt, titles and
# lane headers 16 pt, arrow labels and the type key 13.5 pt. Boxes are drawn exactly on their outline (no outer pad) and
# arrows are not shortened, so every arrow starts on the source box's border and its tip touches the target's border.
# _fw_check fails the figure if a box text comes within 3 pt of its border or a free text touches a box.
FW_W, FW_H = 1260.0, 676.8
FW_FS, FW_TFS, FW_SFS = 14.5, 16.0, 13.5
FW_PAD, FW_GAP, FW_LS = 9.0, 6.0, 1.3       # inner padding, title-to-body gap (pt), body line spacing
FW_IND = " " * 5                             # hanging indent of a title's second line (the width of "6 · " in bold)


def _pt_bbox(ax, artist):
    """Extent of a drawn artist in data units (points in Fig 6)."""
    return artist.get_window_extent(ax.figure.canvas.get_renderer()).transformed(ax.transData.inverted())


def _box(ax, boxes, name, x, y, w, h, title, body, ec, fc="white"):
    """Rounded box on (x, y, w, h): bold title at the top left, body below the title's measured extent."""
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=8", fc=fc, ec=ec, lw=1.8))
    t = ax.text(x + FW_PAD, y + h - FW_PAD, title, ha="left", va="top", fontsize=FW_TFS, weight="bold", color=ec,
                linespacing=1.15)
    b = ax.text(x + FW_PAD, _pt_bbox(ax, t).y0 - FW_GAP, body, ha="left", va="top", fontsize=FW_FS, color=INK,
                linespacing=FW_LS)
    boxes[name] = ((x, y, w, h), [t, b])
    return x, y, w, h


def _arr(ax, free, p, q, text=None, tx=None, ha="center", color=INK):
    """Arrow from p (on the source box's border) to q (on the target's border), not shortened at either end."""
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=16, color=color, lw=1.6, shrinkA=0, shrinkB=0))
    if text:
        x, y = tx if tx else ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
        free.append(ax.text(x, y, text, fontsize=FW_SFS, color=color, ha=ha, va="center", style="italic",
                            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.9)))


def _fw_check(ax, boxes, free, tol=3.0):
    """Every box text at least tol pt inside its box; no free text outside the drawing or on a box.
    Returns the smallest margin (pt) and its box."""
    ax.figure.canvas.draw()
    bad, worst = [], (np.inf, "")
    for name, ((x, y, w, h), texts) in boxes.items():
        for t in texts:
            b = _pt_bbox(ax, t)
            m = min(b.x0 - x, x + w - b.x1, b.y0 - y, y + h - b.y1)
            worst = min(worst, (m, name))
            if m < tol:
                bad.append(f"box {name}: text {m:.1f} pt from the border")
    for t in free:
        b = _pt_bbox(ax, t)
        if b.x0 < 0 or b.x1 > FW_W or b.y0 < 0 or b.y1 > FW_H:
            bad.append(f"{t.get_text()[:30]!r} outside the drawing")
        bad += [f"{t.get_text()[:30]!r} touches box {n}" for n, ((x, y, w, h), _) in boxes.items()
                if b.x0 < x + w and b.x1 > x and b.y0 < y + h and b.y1 > y]
    if bad:
        raise ValueError("Fig 6 layout: " + "; ".join(bad))
    return worst


def fig6_framework(fig_dir, n_items=327, n_det=77, paper_name=None):
    W, H, m = FW_W, FW_H, 4.0
    band = 0.0 if paper_name else 43.2                     # repo copy (NB7): a title band above the drawing
    fig = plt.figure(figsize=(W / 72, (H + band) / 72))
    ax = fig.add_axes([0, 0, 1, H / (H + band)]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")
    BL, OR, GR, RD, TE = "#2F6690", "#C77C11", "#5F6B76", "#C8553D", "#2A9D8F"
    boxes, free = {}, []
    # columns: input | two lanes of three box columns | catalogue | evaluations
    x_in, w_in = m, 146.0
    w_ev = 146.0; x_ev = W - m - w_ev
    w_cat = 156.0; x_cat = x_ev - 16 - w_cat
    lx0, lx1, gc = x_in + w_in + 18, x_cat - 18, 22.0
    C = (lx1 - lx0 - 16 - 2 * gc) / 3
    xc = [lx0 + 8 + i * (C + gc) for i in range(3)]
    # rows: A and B in the weak-supervision lane, C in the detector lane, the type key below
    head, gr, gl, key_gap, key_h = 34.0, 34.0, 34.0, 12.0, 32.0
    hr = (H - 2 * m - 2 * head - gr - gl - 20 - key_gap - key_h) / 3
    l1_top = H - m
    yA = l1_top - head - hr
    yB = yA - gr - hr
    l1_bot = yB - 10
    l2_top = l1_bot - gl
    yC = l2_top - head - hr
    l2_bot = yC - 10
    mid_y = (yC + yA + hr) / 2                              # middle of the three rows
    ax.add_patch(Rectangle((lx0, l1_bot), lx1 - lx0, l1_top - l1_bot, fc="#F4F7FB", ec="none"))
    ax.add_patch(Rectangle((lx0, l2_bot), lx1 - lx0, l2_top - l2_bot, fc="#FBF6EE", ec="none"))
    free.append(ax.text(xc[0], l1_top - 8, "WEAK SUPERVISION: no manual labels", fontsize=FW_TFS, color=BL, weight="bold",
                        va="top"))
    free.append(ax.text(xc[0], l2_top - 8, "RESIDUAL DETECTOR: anomalies no rule covers", fontsize=FW_TFS, color=OR,
                        weight="bold", va="top"))
    # input
    bi = _box(ax, boxes, "input", x_in, mid_y - 155, w_in, 310, "INPUT",
              "feeder series x\nper zone\n\nzone → city →\nregion\n(one shared\ntimeline in the\nsouth)\n\n"
              "10-min A (south),\n30-min kW\n(Marrakech)\n\ntimestamps as\nrecorded", GR)
    # weak-supervision lane
    b1 = _box(ax, boxes, "1", xc[0], yA, C, hr, "1 · Per-step states",
              "x̂ = 14-day same-slot median\nexact zero\nnoise floor (≤ 5 % of x̂)\nhold (≥ 6 equal values)\n"
              "straight-line fill\n(≥ 6 collinear points)", BL)
    b2 = _box(ax, boxes, "2", xc[0], yB, C, hr, "2 · Items and episodes",
              f"dead · fill · clock · transfer\nitems ({n_items} on the real data)\nitems sharing boundaries\n→ episodes\n"
              "(e.g. hold → zero fill)", BL)
    b3 = _box(ax, boxes, "3", xc[1], yA, C, hr, "3 · 19 labelling rules",
              "vote or abstain, in 9 families:\nsimultaneity · hold ·\nstraight line · restoration ·\n"
              "city · single zone · calendar ·\nclock · conservation", BL)
    b4 = _box(ax, boxes, "4", xc[1], yB, C, hr, f"4 · Constrained\n{FW_IND}label model",
              "Dawid–Skene with feasible\nclasses by level, applicability\ndomains, one-coin\nparameters and priors\n"
              "→ q(y) over A1–A4, G1–G5, N", BL)
    # detector lane
    b5 = _box(ax, boxes, "5", xc[0], yC, C, hr, "5 · Predictor",
              "TCN-GAT forecast of\nρ = x / x̂, cross-fitted,\ntrained on rule-clean steps\nablations: learned graph\n"
              "on/off; LightGBM predictor", OR)
    b6 = _box(ax, boxes, "6", xc[1], yC, C, hr, f"6 · Multi-scale residual\n{FW_IND}hierarchy",
              "phase-aligned MODWT bands\nregion g · city u · zone v\nrobust z-scores\nmax over bands and levels", OR)
    b7 = _box(ax, boxes, "7", xc[2], yC, C, hr, "7 · Event formation",
              "smoothing w · threshold at\npercentile q · merge gap\n(tuned on development data,\n"
              "the same budget for every\ndetector)\n→ detector-only candidates", OR)
    # end model and fusion
    b8 = _box(ax, boxes, "8", xc[2], yA, C, hr, "8 · End model",
              "gradient boosting on item\nfeatures (shape, timing,\nepisode context, level scores\n"
              "from step 6), trained on q\nout of fold → f(y)", TE)
    b9 = _box(ax, boxes, "9", xc[2], yB, C, hr, "9 · Fusion",
              r"$p \propto q^{\beta}\, f^{1-\beta}$" + "\non feasible classes;\nabstain on rare classes", TE)
    # catalogue and evaluations
    bc = _box(ax, boxes, "catalogue", x_cat, yB + hr / 2 - 125, w_cat, 250, "TYPED\nPROBABILISTIC\nCATALOGUE",
              f"{n_items + n_det} entries:\n{n_items} rule items\n+ {n_det} detector-only\n\nlabel, confidence,\n"
              "p(y) per class\n\nepisodes as label\nsequences", RD, "#FBE9E5")
    be = [_box(ax, boxes, nm, x_ev, y, w_ev, hr, tt, bd, GR) for nm, y, tt, bd in [    # aligned with rows A, B, C
        ("injection", yA, "Injection\nbenchmark", "30 datasets,\n1/3/7 %\ndetection,\nattribution,\nablations"),
        ("downstream", yB, "Downstream\ntest", "typed cleaning:\nforecasts and\noutage statistics"),
        ("transfer", yC, "Transfer\ntest", "Tetouan, with the\nmethod frozen")]]
    # arrows: every one starts on a border and ends on a border
    R = lambda b, y: (b[0] + b[2], y)          # noqa: E731  point on the right border at height y
    L = lambda b, y: (b[0], y)                 # noqa: E731
    T = lambda b, x: (x, b[1] + b[3])          # noqa: E731
    B = lambda b, x: (x, b[1])                 # noqa: E731
    M = lambda b: b[1] + b[3] / 2              # noqa: E731
    gap_A = (yA + yB + hr) / 2                 # middle of the gap between rows A and B
    _arr(ax, free, R(bi, bi[1] + bi[3] - 20), L(b1, M(b1)))
    _arr(ax, free, R(bi, bi[1] + 20), L(b5, M(b5)))
    _arr(ax, free, B(b1, xc[0] + C / 2), T(b2, xc[0] + C / 2))
    _arr(ax, free, R(b2, yB + hr - 22), L(b3, yA + 22), "items")
    _arr(ax, free, B(b3, xc[1] + C / 2), T(b4, xc[1] + C / 2))
    _arr(ax, free, R(b4, M(b4)), L(b9, M(b9)), "q", tx=(xc[1] + C + gc / 2, M(b4) + 13))
    _arr(ax, free, R(b4, yB + hr - 16), B(b8, xc[2] + 22), "q as soft targets", tx=(xc[2] + 34, gap_A), ha="left")
    _arr(ax, free, B(b8, xc[2] + C - 40), T(b9, xc[2] + C - 40), "f", tx=(xc[2] + C - 29, gap_A))
    _arr(ax, free, R(b5, M(b5)), L(b6, M(b6)))
    _arr(ax, free, R(b6, M(b6)), L(b7, M(b7)))
    _arr(ax, free, T(b7, xc[2] + C / 2), B(b9, xc[2] + C / 2), "candidates (labelled by f)",
         tx=(xc[2] + C / 2, (l1_bot + l2_top) / 2))
    _arr(ax, free, R(b9, M(b9)), L(bc, M(b9)))
    _arr(ax, free, R(bc, bc[1] + bc[3] - 20), L(be[0], be[0][1] + 22))
    _arr(ax, free, R(bc, M(bc)), L(be[1], M(be[1])))
    _arr(ax, free, R(bc, bc[1] + 20), L(be[2], be[2][1] + be[2][3] - 22))
    free.append(ax.text(W / 2, l2_bot - key_gap,
                        "A1 zero-fill gap · A2 simultaneous fill · A3 single-zone fill · A4 clock error\n"
                        "G1 regional outage · G2 city outage · G3 unplanned feeder outage · G4 planned work · "
                        "G5 load transfer · N normal / untyped", ha="center", va="top", fontsize=FW_SFS, color="#444",
                        linespacing=1.3))
    if not paper_name:
        fig.text(0.5, 1 - band / 2 / (H + band), "Fig 6 — Framework: weak supervision from hierarchical rules, a multi-scale "
                 "residual detector, an end model and fusion produce a typed, probabilistic event catalogue", ha="center",
                 va="center", fontsize=12, weight="bold", color=INK)
    worst = _fw_check(ax, boxes, free)
    print(f"Fig 6 layout check: every text inside its box (smallest margin {worst[0]:.1f} pt, box {worst[1]})")
    _save(fig, fig_dir, "fig6_framework", paper_name)
    return fig
