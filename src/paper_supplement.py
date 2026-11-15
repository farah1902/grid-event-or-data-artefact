"""Supplementary figures S1-S9 in submission form (D107).

Same style as paper_submission (D86): drawn at 7.2 in, text 6.5-7 pt, no title inside the image (the caption carries
it), no internal codes (case, item or episode ids, notebook names), one PDF per figure (the caller sets
pdf.fonttype 42). Everything is read from stored results or rebuilt with the rule engine (rules_v1) and the injector
(inject), and every value printed in a figure is checked against the stored result it comes from. Nothing here changes
a result.

    S1  16-17 July 2023, all 15 southern zones          rule engine states (as Figures 4 and 5)
    S2  clock evidence at 30 October 2022                rules_v1.city_profile, the computation of rules_v1.clock_offset
    S3  Boujdour load transfer, 16 December 2023         rules_v0.transfers (kappa checked against the transfer item)
    S4  rule coverage, overlap and conflict              rule engine votes
    S5  signatures of the dead items                     results/catalogue_v1/items.csv + final labels
    S6  the typed catalogue on one timeline              results/catalogue_final/catalogue.csv
    S7  end model                                        results/end_model_v1/ + final catalogue
    S8  one injected event per type                      inject.Injector, 3 %, seed 0 (as NB4)
    S9  UCI Tetouan series                               transfer.load
"""
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

import paper_submission as PS
import rules_v1 as R1
from viz import COL, LABEL_COL

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
W, FS, INK, STYLE = PS.W, PS.FS, PS.INK, PS.STYLE
LABEL_COL_N = {**LABEL_COL, "N": "#9AA0A6"}
ORDER_CL = ["A1", "A2", "A3", "A4", "G1", "G2", "G3", "G4", "G5", "N"]
CITY = {"Laayoune": "Laâyoune", "Boujdour": "Boujdour", "Foum eloued": "Foum El Oued", "Marrakech": "Marrakech"}
CITY_COL = {"Laayoune": "#2F6690", "Boujdour": "#3A7D44", "Foum eloued": "#C8553D"}
FAMILY = {"simultaneity": "simultaneity", "hold": "holds", "restoration": "restoration", "city": "city",
          "single_zone": "single zone", "calendar": "calendar", "clock": "clock", "conservation": "conservation",
          "interpolation": "straight-line fills"}


def _save(fig, out, name):
    PS._save(fig, out, name)


# ---------------------------------------------------------------- S1: 16-17 July 2023
def figure_s1(res, out):
    """The only regional-outage candidate: exact zeros in Boujdour and Foum El Oued from 14:50, straight-line fill in
    every Laayoune zone from 15:30 (times from the catalogue items, checked here)."""
    it = res["items"]
    day = it[pd.to_datetime(it.start).dt.normalize() == pd.Timestamp("2023-07-16")]
    dead = day[(day.kind == "dead") & (day.n_zones == 10)]
    fill = day[(day.kind == "fill") & (day.zones == "L1,L2,L3,L4,L5")]
    assert len(dead) == 1 and pd.Timestamp(dead.start.iloc[0]) == pd.Timestamp("2023-07-16 14:50"), dead
    assert len(fill) == 1 and pd.Timestamp(fill.start.iloc[0]) == pd.Timestamp("2023-07-16 15:30"), fill
    PS._stack(res, "2023-07-16 08:00", "2023-07-17 14:00", ["2023-07-16 14:50", "2023-07-16 15:30"],
              "14:50: Boujdour and Foum El Oued at exact zero  ·  15:30: straight-line fill in Laâyoune", "2023-07-16 14:50",
              {"L1", "L2", "L3", "L4", "L5"}, out, "FigS1")


# ---------------------------------------------------------------- S2: clock evidence
def _clock_curves(res, c, D, days=7, max_min=120):
    """rules_v1.clock_offset with its profiles and correlation curve kept (same masks as rules_v1.clock_items)."""
    d, m = res["data"][c], res["masks"][c]
    bad = m["dead"] | m["hold"] | m["interp"]
    stp = pd.Timedelta(R1.STEP[c])
    pre = R1.city_profile(d, bad, D - pd.Timedelta(days=days), D - stp)
    post = R1.city_profile(d, bad, D + pd.Timedelta(days=1), D + pd.Timedelta(days=days + 1) - stp)
    mn = int(stp.total_seconds() // 60)
    ks = np.arange(-max_min // mn, max_min // mn + 1)
    corr = np.array([np.corrcoef(pre.values, np.roll(post.values, -k))[0, 1] for k in ks])
    return pre, post, ks * mn, corr, int(ks[int(np.nanargmax(corr))] * mn)


def figure_s2(res, out, day="2022-10-30"):
    D = pd.Timestamp(day)
    it = res["items"]
    clk = it[(it.kind == "clock") & (pd.to_datetime(it.start) == D)].set_index("cities")
    found = {}
    with plt.rc_context(STYLE):
        fig, axs = plt.subplots(1, 2, figsize=(W, 2.5), gridspec_kw=dict(width_ratios=[1.55, 1]))
        for c in R1.SOUTH:
            pre, post, shifts, corr, delta = _clock_curves(res, c, D)
            assert delta == clk.loc[c, "delta_star_min"], (c, delta, clk.loc[c, "delta_star_min"])
            found[c] = delta
            h = pre.index / 60
            axs[0].plot(h, pre.values, color=CITY_COL[c], lw=0.9, label=f"{CITY[c]}, 7 days before")
            axs[0].plot(h, post.values, color=CITY_COL[c], lw=0.9, ls="--", label=f"{CITY[c]}, 7 days after")
            axs[1].plot(shifts, corr, color=CITY_COL[c], lw=0.9, label=f"{CITY[c]}: δ* = {delta:+d} min")
            axs[1].axvline(delta, color=CITY_COL[c], lw=0.6, ls=":")
        axs[0].set_xlabel("time of day as recorded (h)"); axs[0].set_ylabel("normalised load"); axs[0].set_xticks(range(0, 25, 3))
        axs[0].set_xlim(0, 24)
        axs[0].set_title("(a) mean daily profiles")
        axs[0].legend(ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.2), handlelength=1.6, columnspacing=1.0)
        axs[1].axvline(0, color="#999", lw=0.5)
        axs[1].set_xlabel("shift δ (min)"); axs[1].set_ylabel("correlation")
        axs[1].set_title("(b) correlation with the shifted profile")
        axs[1].legend(loc="upper center", bbox_to_anchor=(0.5, -0.2))
        fig.tight_layout()
        _save(fig, out, "FigS2")
    return found


# ---------------------------------------------------------------- S3: load transfer
def figure_s3(res, out, city="Boujdour", day="2023-12-16"):
    """Daily means around the conserved transfer and the change of the 14-day medians (rules_v0.transfers)."""
    D = pd.Timestamp(day)
    d = res["data"][city]
    daily = d.where(d > 0).resample("1D").mean()
    pre = daily.rolling(14, min_periods=10).median()
    post = daily[::-1].rolling(14, min_periods=10).median()[::-1].shift(-1)
    dz = (post - pre).loc[D]
    kappa = abs(dz.sum()) / max(dz.max(), -dz.min())
    it = res["items"]
    t = it[(it.kind == "transfer") & (it.cities == city) & (pd.to_datetime(it.start) == D)]
    assert len(t) == 1 and round(kappa, 2) == float(t.kappa.iloc[0]), (kappa, t)
    code = {z: f"{R1.CITY_SHORT[city]}{z.replace('zone', '')}" for z in d.columns}
    cols = ["#2F6690", "#C8553D", "#3A7D44"]
    win = daily[D - pd.Timedelta(days=45): D + pd.Timedelta(days=45)]
    with plt.rc_context(STYLE):
        fig, axs = plt.subplots(1, 2, figsize=(W, 2.5), gridspec_kw=dict(width_ratios=[2.2, 1]))
        for z, k in zip(win.columns, cols):
            axs[0].plot(win.index, win[z], color=k, lw=0.9, label=code[z])
        axs[0].plot(win.index, win.sum(axis=1), color=INK, lw=0.9, ls="--", label="sum of the three zones")
        axs[0].axvline(D, color="#444", lw=0.7, ls=":")
        axs[0].set_ylabel("daily mean current (A)")
        axs[0].xaxis.set_major_formatter(mdates.DateFormatter("%d %b\n%Y"))
        axs[0].set_title("(a) daily means, 45 days either side")
        axs[0].legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.25), columnspacing=1.0)
        labels = [code[z] for z in dz.index] + ["sum"]
        axs[1].bar(labels, list(dz.values) + [dz.sum()], color=cols[:len(dz)] + [INK])
        axs[1].axhline(0, color="#999", lw=0.5)
        axs[1].set_ylabel("change (A)")
        axs[1].set_title(f"(b) change of the 14-day medians, κ = {kappa:.2f}")
        fig.tight_layout()
        _save(fig, out, "FigS3")
    return dict(kappa=round(kappa, 2), delta={code[z]: round(float(v), 1) for z, v in dz.items()})


# ---------------------------------------------------------------- S4: rule diagnostics
def figure_s4(res, out):
    V = res["votes"].set_index("item_id")
    rules = [r for r in R1.RULES if r in V.columns]
    fired = V[rules].notna()
    ov = pd.DataFrame(0, index=rules, columns=rules); cf = ov.copy()
    for i in V.index:
        f = [r for r in rules if fired.at[i, r]]
        for a in f:
            for b in f:
                if a != b:
                    ov.at[a, b] += 1
                    cf.at[a, b] += int(not R1.compatible(V.at[i, a], V.at[i, b]))
    cov = res["rule_summary"].set_index("rule").loc[rules]
    with plt.rc_context(STYLE):
        fig, axs = plt.subplots(1, 3, figsize=(W, 2.9), gridspec_kw=dict(width_ratios=[1, 1.15, 1.15]))
        cols = [LABEL_COL.get(str(l).split(",")[0], "#ccc") if isinstance(l, str) and l else "#ccc" for l in cov.labels]
        axs[0].barh(cov.index[::-1], cov.n_votes[::-1], color=cols[::-1])
        for y, (n, k) in enumerate(zip(cov.n_votes[::-1], cov.n_items_of_kind[::-1])):
            axs[0].text(n + 2, y, f"{n}/{k}", va="center", fontsize=5.5)
        axs[0].set_xlabel("items voted on"); axs[0].set_title("(a) coverage (of the items of its kind)")
        axs[0].tick_params(axis="y", labelsize=5.5); axs[0].set_xlim(0, cov.n_votes.max() * 1.35)
        for ax, M_, t, cmap in [(axs[1], ov, "(b) overlap: items where both fire", "Blues"),
                                (axs[2], cf, "(c) conflict: incompatible outputs", "Reds")]:
            m = np.log1p(M_.values)
            ax.imshow(m, cmap=cmap)
            ax.set_xticks(range(len(rules))); ax.set_xticklabels(rules, rotation=90, fontsize=5)
            ax.set_yticks(range(len(rules))); ax.set_yticklabels(rules, fontsize=5)
            for (a, b), val in np.ndenumerate(M_.values):
                if val:
                    ax.text(b, a, str(val), ha="center", va="center", fontsize=3.6, color="white" if m[a, b] > m.max() * .6 else "black")
            ax.set_title(t)
        fig.tight_layout()
        _save(fig, out, "FigS4")


# ---------------------------------------------------------------- S5: signatures of the dead items
def figure_s5(cat, out):
    items = pd.read_csv(RES / "catalogue_v1" / "items.csv")
    d = items[items.kind == "dead"].merge(cat[["item_id", "label"]], on="item_id", how="left")
    labs = [l for l in ORDER_CL if (d.label == l).any()]
    with plt.rc_context(STYLE):
        fig, axs = plt.subplots(1, 3, figsize=(W, 2.4))
        bins = np.linspace(0, 1, 11)
        bottom = np.zeros(len(bins) - 1)
        for l in labs:
            h, _ = np.histogram(d[d.label == l].eta.clip(0, 1), bins)
            axs[0].bar(bins[:-1], h, width=0.095, align="edge", bottom=bottom, color=LABEL_COL_N[l], label=l); bottom += h
        axs[0].set_xlabel("exact-zero share η"); axs[0].set_ylabel("dead items")
        axs[0].legend(title="final label", title_fontsize=FS["small"])
        axs[0].set_title("(a) exact zeros and noise floor")
        for l in labs:
            g = d[d.label == l]
            axs[1].scatter(g.restore_ratio, g.peak_ratio, s=9, color=LABEL_COL_N[l], alpha=0.85, edgecolor="white", lw=0.3)
        axs[1].axhline(1.15, color="#888", lw=0.6, ls="--")
        axs[1].text(2.95, 1.22, "π = 1.15", fontsize=FS["small"], ha="right", color="#666")
        axs[1].set_xlabel("restoration ratio r"); axs[1].set_ylabel("overshoot π"); axs[1].set_ylim(0, 3)
        axs[1].set_title("(b) restoration")
        for l in labs:
            g = d[d.label == l]
            axs[2].scatter(g.duration_h, g.ramp_min.fillna(0), s=9, color=LABEL_COL_N[l], alpha=0.85, edgecolor="white", lw=0.3)
        axs[2].set_xscale("log"); axs[2].set_xlabel("duration (h)"); axs[2].set_ylabel("ramp time τ (min)")
        axs[2].set_title("(c) duration and ramp time")
        fig.tight_layout()
        _save(fig, out, "FigS5")
    return dict(n_dead=len(d), labels=d.label.value_counts().to_dict())


# ---------------------------------------------------------------- S6: the typed catalogue on one timeline
def figure_s6(cat, res, out):
    zones = [(c, z, f"{R1.CITY_SHORT[c]}{z.replace('zone', '')}") for c in ["Laayoune", "Boujdour", "Foum eloued", "Marrakech"]
             for z in res["data"][c].columns]
    row = {code: k for k, (_, _, code) in enumerate(zones[::-1])}
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(W, 3.6))
        for (c, z, code) in zones:
            d = res["data"][c][z]
            ax.add_patch(Rectangle((mdates.date2num(d.index[0]), row[code] - 0.4),
                                   mdates.date2num(d.index[-1]) - mdates.date2num(d.index[0]), 0.8, fc="#F4F4F4", ec="none"))
        sub = cat[cat.kind.isin(["dead", "fill", "detector"])]
        for r in sub.itertuples():
            zs = [z for z in str(r.zones).split(",") if z in row]
            if not zs and str(r.zones).startswith("15 zones"):
                zs = [code for (_, _, code) in zones if code[0] in "LBF"]
            a, b = mdates.date2num(pd.Timestamp(r.start)), mdates.date2num(pd.Timestamp(r.end))
            for z in zs:
                if r.source == "detector":
                    ax.add_patch(Rectangle((a, row[z] - 0.4), max(b - a, 0.12), 0.8, fc="none", ec=LABEL_COL_N[r.label], lw=0.6))
                else:
                    ax.add_patch(Rectangle((a, row[z] - 0.4), max(b - a, 0.12), 0.8, fc=LABEL_COL_N[r.label], ec="none"))
        for r in cat[cat.kind == "clock"].itertuples():
            ax.axvline(mdates.date2num(pd.Timestamp(r.start)), color=LABEL_COL_N["A4"] if r.label == "A4" else "#CCCCCC", lw=0.7, ls=":")
        ax.set_yticks(range(len(zones))); ax.set_yticklabels([code for (_, _, code) in zones[::-1]], fontsize=FS["small"])
        ax.set_ylim(-0.7, len(zones) - 0.3)
        ax.set_xlim(mdates.date2num(pd.Timestamp("2022-09-10")), mdates.date2num(pd.Timestamp("2024-05-28")))
        ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10])); ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
        for y in (1.5, 8.5, 11.5):
            ax.axhline(y, color="#BBBBBB", lw=0.5)
        labs = [l for l in ORDER_CL if (sub.label == l).any()]
        hand = ([Rectangle((0, 0), 1, 1, fc=LABEL_COL_N[l]) for l in labs] + [Rectangle((0, 0), 1, 1, fc="none", ec="#666")]
                + [Line2D([0], [0], color=LABEL_COL_N["A4"], ls=":", lw=1), Line2D([0], [0], color="#CCCCCC", ls=":", lw=1)])
        ax.legend(hand, labs + ["detector-only (outline)", "clock day, A4", "clock day, N"], ncol=6, loc="upper center",
                  bbox_to_anchor=(0.5, -0.13), columnspacing=1.0, handlelength=1.4)
        fig.tight_layout()
        _save(fig, out, "FigS6")
    return dict(rule_items=int((sub.source == "rule").sum()), detector_only=int((sub.source == "detector").sum()))


# ---------------------------------------------------------------- S7: end model
def figure_s7(cat, out):
    pt = pd.read_csv(RES / "end_model_v1" / "p_type.csv")
    em = pd.read_csv(RES / "end_model_v1" / "end_model_metrics.csv")
    r = pt[pt.source == "rule"]
    with plt.rc_context(STYLE):
        fig, axs = plt.subplots(1, 3, figsize=(W, 2.5), gridspec_kw=dict(width_ratios=[1.0, 1.25, 1.1]))
        cm = pd.crosstab(pd.Series(r.label_q.values, name="label model"), pd.Series(r.label_f.values, name="end model"))
        axs[0].imshow(np.log1p(cm.values), cmap="Blues")
        axs[0].set_xticks(range(cm.shape[1])); axs[0].set_xticklabels(cm.columns)
        axs[0].set_yticks(range(cm.shape[0])); axs[0].set_yticklabels(cm.index)
        for (i, j), v in np.ndenumerate(cm.values):
            axs[0].text(j, i, v, ha="center", va="center", fontsize=5.5, color="white" if v > cm.values.max() * 0.5 else INK)
        axs[0].set_xlabel("end model, out of fold"); axs[0].set_ylabel("label model"); axs[0].set_title("(a) rule items, real data")
        e = em.set_index("variant")[["agree_rule_items", "normal_windows_as_N"]]
        y = np.arange(len(e))
        axs[1].barh(y - 0.2, e.agree_rule_items, height=0.38, color="#2F6690", label="agreement on rule items")
        axs[1].barh(y + 0.2, e.normal_windows_as_N, height=0.38, color="#9AA0A6", label="normal windows predicted N")
        axs[1].set_yticks(y); axs[1].set_yticklabels(e.index, fontsize=FS["small"]); axs[1].invert_yaxis(); axs[1].set_xlim(0, 1)
        axs[1].legend(loc="upper center", bbox_to_anchor=(0.4, -0.15), ncol=1)
        axs[1].set_title("(b) agreement by variant")
        det = cat[cat.source == "detector"]
        tab = det.groupby(["system", "label"]).size().unstack(fill_value=0)
        labs = [l for l in ORDER_CL if l in tab.columns]
        left = np.zeros(len(tab))
        for l in labs:
            axs[2].barh(range(len(tab)), tab[l], left=left, color=LABEL_COL_N[l], label=l); left += tab[l].to_numpy()
        names = {"south": "southern system\n(main detector)", "marrakech": "Marrakech\n(LightGBM residual)",
                 "Marrakech": "Marrakech\n(LightGBM residual)"}
        axs[2].set_yticks(range(len(tab))); axs[2].set_yticklabels([names.get(s, s) for s in tab.index], fontsize=FS["small"])
        axs[2].legend(ncol=len(labs), loc="upper center", bbox_to_anchor=(0.5, -0.32), columnspacing=0.8, handlelength=1.0)
        axs[2].set_xlabel("detector-only candidates"); axs[2].set_title("(c) final labels of the candidates")
        fig.tight_layout()
        _save(fig, out, "FigS7")
    return dict(confusion=cm.to_dict(), systems=tab.to_dict())


# ---------------------------------------------------------------- S8: one injected event per type
def figure_s8(res, out, rate=0.03, seed=0):
    import benchmark as B
    import detector as D
    import inject as INJ
    P = D.build_panel(res["data"], res["exp"], res["masks"], "south")
    clean = B.clean_region(P, None)
    zmap = INJ.zone_map(res["data"], B.SOUTH, R1.CITY_SHORT)
    inj = INJ.Injector(res["data"], res["exp"], clean, zmap)
    ex_data, ex_truth = inj.sample(np.ones(len(P["rho"].index), bool), rate, np.random.default_rng([int(round(rate * 1000)), seed]))
    show = ex_truth[ex_truth.type.isin(INJ.TYPES)].groupby("type").head(1).set_index("type")
    show = show.loc[[t for t in INJ.TYPES if t in set(show.index)]]
    pal = ["#2F6690", "#C8553D", "#3A7D44", "#7B5EA7"]
    with plt.rc_context(STYLE):
        nr = int(np.ceil(len(show) / 2))
        fig, axs = plt.subplots(nr, 2, figsize=(W, 1.45 * nr))
        axs = np.atleast_2d(axs)
        for k, (typ, r) in enumerate(show.iterrows()):
            ax = axs[k // 2, k % 2]
            zs = r.zones.split(",")[:4]
            a, b = r.start - pd.Timedelta(hours=10), r.end_affected + pd.Timedelta(hours=10)
            for z, col in zip(zs, pal):
                c, zc = zmap[z]
                ax.plot(res["data"][c][zc][a:b], color="#BBBBBB", lw=0.7)
                ax.plot(ex_data[c][zc][a:b], color=col, lw=0.8, label=z)
            ax.axvspan(r.start, r.end, color=LABEL_COL.get(typ, "#F2A541"), alpha=0.2, lw=0)
            ax.set_title(f"{typ}: {r.duration_h:.1f} h, {r.n_zones} zone{'s' if r.n_zones > 1 else ''}", fontsize=FS["base"])
            ax.set_ylabel("x (A)")
            ax.legend(ncol=4, loc="best", fontsize=5.5, handlelength=1.0, columnspacing=0.6)
            ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=4))
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b %H:%M"))
        for k in range(len(show), nr * 2):
            axs[k // 2, k % 2].axis("off")
        fig.tight_layout()
        _save(fig, out, "FigS8")
    return show[["duration_h", "n_zones", "mechanism", "pattern"]].reset_index().to_dict("records")


# ---------------------------------------------------------------- S9: UCI Tetouan
def figure_s9(out):
    import detector as D
    import transfer as T
    split = D.SPLIT
    T.register()                       # Tetouan in the city dictionaries; register() also moves D.SPLIT to 2017 ...
    D.SPLIT = split                    # ... which this figure does not need, so the Morocco split is restored
    raw, data, _ = T.load(ROOT / "data" / "raw" / "tetouan" / "Tetuan City power consumption.csv")
    x = data["Tetouan"].rename(columns={"zone1": "T1", "zone2": "T2", "zone3": "T3"})
    cols = ["#2F6690", "#C8553D", "#3A7D44"]
    with plt.rc_context(STYLE):
        fig, axs = plt.subplots(2, 1, figsize=(W, 3.6))
        for c, k in zip(x.columns, cols):
            axs[0].plot(x[c].resample("1D").mean(), lw=0.8, color=k, label=c)
            axs[1].plot(x[c].loc["2017-03-06":"2017-03-12"], lw=0.6, color=k)
        axs[0].set_ylabel("daily mean (kW)"); axs[0].set_title("(a) 2017, daily mean per zone")
        axs[0].legend(ncol=3, loc="lower left", bbox_to_anchor=(0.0, 1.0), frameon=False)
        axs[1].set_ylabel("kW"); axs[1].set_title("(b) one week, 10-min steps")
        axs[1].xaxis.set_major_formatter(mdates.DateFormatter("%a %d %b"))
        fig.tight_layout()
        _save(fig, out, "FigS9")
