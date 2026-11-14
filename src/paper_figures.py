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


# ====================================================================== Fig 6: framework
def _box(ax, x, y, w, h, title, body, ec, fc, fs=8.0, tfs=9.0, wrap=None):
    import textwrap
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.004,rounding_size=0.01", fc=fc, ec=ec, lw=1.4))
    if wrap:
        body = "\n".join(textwrap.fill(p, wrap, break_on_hyphens=False) for p in body.split("\n"))
    ax.text(x + 0.008, y + h - 0.012, title, ha="left", va="top", fontsize=tfs, weight="bold", color=ec)
    ax.text(x + 0.008, y + h - 0.042, body, ha="left", va="top", fontsize=fs, color=INK, linespacing=1.28)


def _arr(ax, p, q, text=None, color=INK, rad=0.0, fs=7.2, tx=None):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=11, color=color, lw=1.2,
                                 connectionstyle=f"arc3,rad={rad}"))
    if text:
        x, y = tx if tx else ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
        ax.text(x, y, text, fontsize=fs, color=color, ha="center", va="center", style="italic",
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.9))


def fig6_framework(fig_dir, n_items=327, n_det=77, paper_name=None):
    fig = plt.figure(figsize=(17.5, 9.4))
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    BL, OR, GR, RD, TE = "#2F6690", "#C77C11", "#5F6B76", "#C8553D", "#2A9D8F"
    ax.add_patch(Rectangle((0.145, 0.505), 0.565, 0.40, fc="#F4F7FB", ec="none"))
    ax.add_patch(Rectangle((0.145, 0.17), 0.565, 0.30, fc="#FBF6EE", ec="none"))
    ax.text(0.152, 0.893, "WEAK SUPERVISION: no manual labels", fontsize=9, color=BL, weight="bold", va="top")
    ax.text(0.152, 0.458, "RESIDUAL DETECTOR: anomalies no rule covers", fontsize=9, color=OR, weight="bold", va="top")
    # input
    _box(ax, 0.01, 0.30, 0.12, 0.42, "INPUT", "feeder series x per zone\n\nzone → city → region\n(one shared timeline in the south)\n\n10-min A (south), 30-min kW (Marrakech)\n\ntimestamps as recorded", GR, "white", wrap=22)
    # weak supervision lane
    _box(ax, 0.155, 0.70, 0.17, 0.165, "1 · Per-step states", "x̂ = 14-day same-slot median\nexact zero · noise floor (≤ 5 % of x̂)\nhold (≥ 6 equal values)\nstraight-line fill (≥ 6 collinear points)", BL, "white")
    _box(ax, 0.155, 0.515, 0.17, 0.165, "2 · Items and episodes", f"dead · fill · clock · transfer items\n({n_items} on the real data)\nitems sharing boundaries → episodes\n(e.g. hold → zero fill)", BL, "white")
    _box(ax, 0.345, 0.70, 0.17, 0.165, "3 · 19 labelling rules", "vote or abstain, in 9 families:\nsimultaneity · hold · straight line ·\nrestoration · city · single zone ·\ncalendar · clock · conservation", BL, "white")
    _box(ax, 0.345, 0.515, 0.17, 0.165, "4 · Constrained label model", "Dawid–Skene with feasible classes\nby level, applicability domains,\none-coin parameters and priors\n→ q(y) over A1–A4, G1–G5, N", BL, "white")
    # detector lane
    _box(ax, 0.155, 0.19, 0.17, 0.235, "5 · Predictor", "TCN-GAT forecast of ρ = x / x̂,\ncross-fitted, trained on\nrule-clean steps\nablations: learned graph on/off;\nLightGBM predictor", OR, "white")
    _box(ax, 0.345, 0.19, 0.17, 0.235, "6 · Multi-scale residual\n    hierarchy", "\nphase-aligned MODWT bands\nregion g · city u · zone v\nrobust z-scores\nmax over bands and levels", OR, "white")
    _box(ax, 0.535, 0.19, 0.165, 0.235, "7 · Event formation", "smoothing w · threshold at\npercentile q · merge gap\n(tuned on development data,\nthe same budget for every\ndetector)\n→ detector-only candidates", OR, "white")
    # end model and fusion
    _box(ax, 0.535, 0.70, 0.165, 0.165, "8 · End model", "gradient boosting on item\nfeatures (shape, timing,\nepisode context, level scores\nfrom step 6), trained on q\nout of fold → f(y)", TE, "white")
    _box(ax, 0.535, 0.515, 0.165, 0.165, "9 · Fusion", r"$p \propto q^{\beta}\, f^{1-\beta}$" + "\non feasible classes;\nabstain on rare classes", TE, "white")
    # catalogue
    _box(ax, 0.725, 0.40, 0.125, 0.34, "TYPED\nPROBABILISTIC\nCATALOGUE", f"\n\n{n_items + n_det} entries:\n{n_items} rule items\n+ {n_det} detector-only\n\nlabel, confidence,\np(y) per class\n\nepisodes as label\nsequences", RD, "#FBE9E5", tfs=9.2)
    # evaluation
    _box(ax, 0.865, 0.64, 0.128, 0.20, "Injection benchmark", "30 datasets, 1/3/7 %\ndetection, attribution,\nablations", GR, "white", wrap=26)
    _box(ax, 0.865, 0.405, 0.128, 0.20, "Downstream test", "typed cleaning:\nforecasts and outage\nstatistics", GR, "white", wrap=26)
    _box(ax, 0.865, 0.17, 0.128, 0.20, "Transfer test", "Tetouan, with the\nmethod frozen", GR, "white", wrap=26)
    # arrows
    _arr(ax, (0.13, 0.62), (0.155, 0.78)); _arr(ax, (0.13, 0.42), (0.155, 0.31))
    _arr(ax, (0.24, 0.70), (0.24, 0.68))
    _arr(ax, (0.325, 0.60), (0.345, 0.78))
    ax.text(0.3345, 0.69, "items", fontsize=7.2, style="italic", ha="center", va="center", bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none"))
    _arr(ax, (0.43, 0.70), (0.43, 0.68))
    _arr(ax, (0.515, 0.60), (0.535, 0.60), "q", tx=(0.525, 0.628))
    _arr(ax, (0.515, 0.66), (0.535, 0.76), "q as soft\ntargets", tx=(0.516, 0.735))
    _arr(ax, (0.6175, 0.70), (0.6175, 0.68), "f", tx=(0.628, 0.69))
    _arr(ax, (0.325, 0.31), (0.345, 0.31)); _arr(ax, (0.515, 0.31), (0.535, 0.31))
    _arr(ax, (0.6175, 0.425), (0.6175, 0.515), "candidates (labelled by f)", tx=(0.6175, 0.47))
    _arr(ax, (0.70, 0.60), (0.725, 0.60))
    for y in (0.74, 0.505, 0.27):
        _arr(ax, (0.85, 0.57), (0.865, y))
    if not paper_name:
        ax.text(0.5, 0.965, "Fig 6 — Framework: weak supervision from hierarchical rules, a multi-scale residual detector, an end model and fusion "
                "produce a typed, probabilistic event catalogue", ha="center", fontsize=12, weight="bold", color=INK)
    ax.text(0.5, 0.11, "A1 zero-fill gap · A2 simultaneous fill · A3 single-zone fill · A4 clock error · G1 regional outage · G2 city outage · "
            "G3 unplanned feeder outage · G4 planned work · G5 load transfer · N normal / untyped", ha="center", fontsize=8.5, color="#444")
    _save(fig, fig_dir, "fig6_framework", paper_name)
    return fig
