"""Synthetic injection of observed anomaly signatures into the southern system (guide: injection protocol; NB4).

Events are written into the regularised raw series x (amperes), only inside a *clean region*: zone-steps far from
every real rule state, real multi-zone state and NB3 detector-only candidate, outside the expected-value burn-in and
the detector warm-up, and away from clock-change days. The rule engine, label model, detector and end model are then
re-run on the injected data, so injected events are found (or missed) exactly as real ones would be.

Typed classes (the end model's event classes; signatures copied from the data):
  A1  zero fill          all zones of 2-3 cities set to exact 0                          31 Mar 2024 (C12)
  A2  simultaneous fill  >= 2 zones held or linearly interpolated (per zone 50/50);       26-28 Jan 2023 (C05)
                         with whole-city patterns, optionally followed by A1 (episode)    C05 -> C06, C12
  A3  single-zone fill   one zone held or linearly interpolated, 1-6 h                     81 short runs; F01
  G1  regional outage    2 cities at a noise floor, ramp restore, decaying overshoot        guide spec (no real G1)
  G2  city outage        one city as G1                                                    guide spec
  G3  feeder outage      one zone at a noise floor, any hour, ramp and overshoot           C02, C07
  G4  planned work       one zone at a noise floor, start 06:00-11:59, 70 % weekends       51 candidates (v0)
Untyped (detection only; required by F29 and F32):
  U_SHOCK    all zones of 2-3 cities scaled by 0.5-0.8 for 0.5-4 h (no rule fires: tests forecast vs nowcast)
  U_PARTIAL  one zone scaled by 0.10-0.45 for 1-8 h (above the dead threshold: tests epsilon)
Not injected: A4 clock errors (calendar-gated rules) and G5 transfers (weeks long; day-level rule items outside the
end model, D46). See D54.
"""
import numpy as np
import pandas as pd

TYPED = ["A1", "A2", "A3", "G1", "G2", "G3", "G4"]
UNTYPED = ["U_SHOCK", "U_PARTIAL"]
TYPES = TYPED + UNTYPED
FAMILY = {**{t: "artefact" for t in ["A1", "A2", "A3"]}, **{t: "grid" for t in ["G1", "G2", "G3", "G4"]},
          **{t: "untyped" for t in UNTYPED}}
DUR_H = {"A1": (0.5, 24), "A2": (1, 48), "A3": (1, 6), "G1": (1, 18), "G2": (1 / 3, 6), "G3": (1, 48),
         "G4": (1, 6), "U_SHOCK": (0.5, 4), "U_PARTIAL": (1, 8)}
COMPOUND_P = 0.5          # whole-city A2 followed by an A1 zero fill (C05 -> C06, C12)
GUARD_H = 12              # an event blocks its zones for +-12 h
GUARD_SYSTEM_H = 3        # multi-city events block every zone for +-3 h
PAD_H = 1                 # the clean region must extend 1 h around the affected span


def zone_map(data, cities, short):
    """code -> (city, column) for the given cities, e.g. 'L1' -> ('Laayoune', 'zone1')."""
    return {f"{short[c]}{z.replace('zone', '')}": (c, z) for c in cities for z in data[c].columns}


def _logu(rng, lo, hi):
    return float(np.exp(rng.uniform(np.log(lo), np.log(hi))))


class Injector:
    def __init__(self, data, exp, clean, zmap, step_min=10):
        """data/exp: dicts city -> DataFrame (raw x and expected x_hat); clean: bool frame (time x zone code) on the
        south timeline; zmap: code -> (city, column)."""
        self.data0, self.exp, self.zmap = data, exp, zmap
        self.idx = clean.index
        self.codes = list(clean.columns)
        self.city_of = {z: zmap[z][0] for z in self.codes}
        self.cities = sorted(set(self.city_of.values()))
        self.clean = clean.to_numpy()
        self.step = pd.Timedelta(minutes=step_min)
        self.per_h = int(pd.Timedelta(hours=1) / self.step)
        # positions of the south timeline in each city's own index
        self.pos = {c: data[c].index.get_indexer(self.idx) for c in self.cities}
        self.xhat = {z: exp[c][col].reindex(self.idx).to_numpy() for z, (c, col) in zmap.items() if z in self.codes}
        self.x0 = {z: data[c][col].reindex(self.idx).to_numpy() for z, (c, col) in zmap.items() if z in self.codes}

    # ------------------------------------------------------------------ zone patterns
    def _city_zones(self, c):
        return [z for z in self.codes if self.city_of[z] == c]

    def _pick_zones(self, typ, rng):
        if typ in ("A1", "G1", "U_SHOCK"):
            k = 2 if typ == "G1" else int(rng.integers(2, 4))
            cs = list(rng.choice(self.cities, size=k, replace=False))
            return sum((self._city_zones(c) for c in cs), []), ("cities" if k >= 2 else "city")
        if typ == "G2":
            return self._city_zones(rng.choice(self.cities)), "city"
        if typ == "A2":
            u = rng.uniform()
            if u < 0.5:
                c = rng.choice(self.cities); zs = self._city_zones(c)
                return list(rng.choice(zs, size=int(rng.integers(2, len(zs) + 1)), replace=False)), "zones"
            if u < 0.75:
                return self._city_zones(rng.choice(self.cities)), "city"
            cs = list(rng.choice(self.cities, size=int(rng.integers(2, 4)), replace=False))
            return sum((self._city_zones(c) for c in cs), []), "cities"
        return [self.codes[int(rng.integers(len(self.codes)))]], "zone"

    # ------------------------------------------------------------------ placement
    def _start(self, typ, rng, lo, hi, n):
        if typ == "G4":
            for _ in range(50):
                a = int(rng.integers(lo, hi - n))
                t = self.idx[a]
                if 6 <= t.hour <= 11 and ((t.dayofweek >= 5) == (rng.uniform() < 0.7)):
                    return a
            return None
        return int(rng.integers(lo, hi - n))

    def _free(self, free, cols, a, b):
        a, b = max(0, a), min(len(self.idx), b)
        return free[a:b][:, cols].all()

    def sample(self, period_mask, rate, rng, max_fail=400):
        """Place events round-robin over TYPES until injected zone-steps reach `rate` x clean zone-steps of the
        period. Returns (modified copy of data, truth table)."""
        data = {c: d.copy() for c, d in self.data0.items()}
        free = self.clean & period_mask[:, None]
        budget = rate * free.sum()
        lo, hi = int(np.argmax(period_mask)), int(len(period_mask) - np.argmax(period_mask[::-1]))
        truth, used, fails, k = [], 0, 0, 0
        while used < budget and fails < max_fail:
            order = list(rng.permutation(TYPES))
            progress = False
            for typ in order:
                if used >= budget:
                    break
                ev = self._place(typ, data, free, rng, lo, hi, k)
                if ev is None:
                    fails += 1
                    continue
                for e in ev:
                    truth.append(e); used += e["zone_steps"]
                k += 1; progress = True
            if not progress:
                fails += 1
        tr = pd.DataFrame(truth)
        if len(tr):
            tr.insert(0, "event_id", [f"I{i:04d}" for i in range(len(tr))])
        return data, tr

    def _place(self, typ, data, free, rng, lo, hi, k, tries=300):
        col_of = {z: i for i, z in enumerate(self.codes)}
        for _ in range(tries):
            zs, pattern = self._pick_zones(typ, rng)
            dur = _logu(rng, *DUR_H[typ]) if typ != "G4" else float(rng.uniform(*DUR_H[typ]))
            n = max(2, int(round(dur * self.per_h)))
            compound = typ == "A2" and pattern in ("city", "cities") and rng.uniform() < COMPOUND_P
            n2 = max(3, int(round(_logu(rng, 0.5, 12) * self.per_h))) if compound else 0
            if typ in ("G1", "G2", "G3", "G4"):
                ramp = int(round(rng.uniform(*((10, 30) if typ == "G4" else (20, 90))) / 10))
                decay = 0 if typ == "G4" else int(round(rng.uniform(1, 2) * self.per_h))
                omega = 1.0 if typ == "G4" else float(rng.uniform(1.1, 1.5))
            else:
                ramp, decay, omega = 0, 0, 1.0
            tail = ramp + decay
            a = self._start(typ, rng, lo, hi, n + n2 + tail + 2 * self.per_h)
            if a is None:
                continue
            b = a + n
            cols = [col_of[z] for z in zs]
            pad = PAD_H * self.per_h
            if not self._free(free, cols, a - pad, b + n2 + tail + pad):
                continue
            if any(np.isnan(self.x0[z][a - 1]) or np.isnan(self.x0[z][min(b + n2, len(self.idx) - 1)]) for z in zs):
                continue
            span_ok = all((self.pos[self.zmap[z][0]][max(0, a - 1):b + n2 + tail + 1] >= 0).all() for z in zs)
            if not span_ok:
                continue
            # write the signature (all positions checked above, so an event is written completely or not at all)
            mech = []
            f_event = float(rng.uniform(0.5, 0.8)) if typ == "U_SHOCK" else float(rng.uniform(0.10, 0.45))
            for z in zs:
                c, col = self.zmap[z]
                x = data[c][col].to_numpy(copy=True)
                p = self.pos[c]
                pa, pb = p[a], p[b]
                xh = self.xhat[z]
                if typ == "A1":
                    x[p[a + int(rng.integers(0, 2))]:pb] = 0.0; mech.append("zero")
                elif typ in ("A2", "A3"):
                    if rng.uniform() < 0.5:
                        x[pa:pb] = x[pa - 1]; mech.append("hold")
                    else:
                        x[pa:pb] = np.linspace(x[pa - 1], x[pb], pb - pa + 2)[1:-1]; mech.append("linear")
                    if compound:
                        x[pb:p[b + n2]] = 0.0
                elif typ in ("G1", "G2", "G3", "G4"):
                    eta = float(rng.uniform(0, 0.3))                       # share of exact zeros in the noise floor
                    base = np.where(np.isfinite(xh[a:b]) & (xh[a:b] > 0), xh[a:b], np.abs(x[pa:pb]))
                    fl = base * rng.uniform(0, 0.03, size=b - a)
                    fl[rng.uniform(size=b - a) < eta] = 0.0
                    x[pa:pb] = fl
                    lev0 = float(fl[-1] / base[-1]) if base[-1] > 0 else 0.0
                    for i in range(tail):                                  # linear ramp, then decaying overshoot
                        mlt = lev0 + (omega - lev0) * (i + 1) / ramp if i < ramp else                             1 + (omega - 1) * np.exp(-3 * (i - ramp + 1) / max(decay, 1))
                        x[p[b + i]] = x[p[b + i]] * mlt
                    mech.append("floor")
                else:                                                      # U_SHOCK (one factor for all zones), U_PARTIAL
                    x[pa:pb] = x[pa:pb] * f_event; mech.append(f"x{f_event:.2f}")
                data[c][col] = x
            g = GUARD_H * self.per_h
            end_aff = b + n2 + tail
            free[max(0, a - g):end_aff + g, cols] = False
            if pattern == "cities" or typ in ("A1", "G1", "U_SHOCK"):
                gs = GUARD_SYSTEM_H * self.per_h
                free[max(0, a - gs):end_aff + gs, :] = False
            cities = sorted(set(self.city_of[z] for z in zs))
            common = dict(zones=",".join(sorted(zs)), n_zones=len(zs), cities="+".join(cities), n_cities=len(cities),
                          family=FAMILY[typ], pattern=pattern, episode=f"J{k:04d}" if compound else "")
            evs = [dict(type=typ, start=self.idx[a], end=self.idx[b], end_affected=self.idx[min(b + tail, len(self.idx) - 1)],
                        duration_h=n / self.per_h, mechanism=",".join(sorted(set(mech))), zone_steps=n * len(zs),
                        omega=omega, ramp_min=ramp * 10, **common)]
            if compound:
                evs.append(dict(type="A1", start=self.idx[b], end=self.idx[b + n2], end_affected=self.idx[b + n2],
                                duration_h=n2 / self.per_h, mechanism="zero (after fill)", zone_steps=n2 * len(zs),
                                omega=1.0, ramp_min=0, **{**common, "family": "artefact"}))
            return evs
        return None
