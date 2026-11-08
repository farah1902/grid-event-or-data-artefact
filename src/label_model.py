"""
label_model.py - Dawid-Skene label model for rule votes (guide eq. 10-12), numpy only.

Turns the votes of rule engine v1 (results/catalogue_v1/votes.csv) into a probability distribution q_i(y)
over the anomaly types for every item. Design history and reasons are in docs/decisions.md (D28-D35).

Changes from the guide's formulation, each forced by the real votes:

1. Abstention is an observed output (D28). The guide multiplies only over rules that fire, with
   theta_r(y, l) = P(lambda_r = l | y, fired). Every v1 rule emits one label, so that is 1 for every class
   and the votes would carry no information. Here theta_r(y, o) = P(lambda_r = o | y), o in {abstain} U outputs(r).

2. Feasible classes per item (D29). Each type is defined at one level of the hierarchy (guide typology table),
   so the item's own kind and level decide which types it can carry:
       dead, >= 2 cities                -> A1, G1
       dead, 1 city, >= 2 zones         -> A1, G2, G3
       dead, 1 zone                     -> A1, G3, G4
       fill, >= 2 zones                 -> A2, N
       fill, 1 zone                     -> A3, N
       clock                            -> A4, N
       transfer                         -> G5, N
   A1 stays feasible at every dead level, so the episode evidence (R3, R21) can still call a single-zone zero
   an artefact. Class priors pi are estimated per item kind and renormalised over each item's feasible set.

3. Applicability (D30). A rule only says something about items its precondition can see: R2/R12 look at held
   runs, R19/R20 at interpolated runs, R13 (repeated hour) at dates where clocks cannot jump forward,
   R14 (missing hour) at spring-forward dates, R15 at dates where delta* is computable. Non-applicable rules
   contribute no factor. Without this, mutually exclusive sub-signatures of
   one class (hold vs interpolation for A3) look like contradictions under conditional independence.

4. What a vote speaks for (D31). 'G' (R5, R6) speaks for every grid-event type. R9 (one zone dead) speaks for
   {G3, G4}: R10 (maintenance window) and R11 (> 24 h) are refinements of R9 and split the two.

5. Defining rules (D33): R2, R8, R10, R12, R13, R14, R16, R19, R20 fire, inside their domain, exactly when the
   typology's definition of their class holds, so their propensity a gets pseudo-counts (9, 1).

6. Class priors pi get a Dirichlet(1) pseudo-count per class of the item kind (D34). Without it, a class whose
   prior reaches ~0 can never come back (an EM fixed point): the 6 vote-less fill items went to A3 at 100 %
   because N had emptied, and the single G5 item (C11) went to N.

7. structure="constrained" (default, D32): one-coin parameters per rule output,
       P(lambda_r = l | y) = a_rl  if l speaks for y   (propensity)
                           = b_rl  otherwise            (false-positive rate)
   with Beta pseudo-counts a: (1, 1) (the guide's alpha = 1) and b: (1, 9) (rules rarely fire on classes they do
   not speak for; this also stops empty classes from making abstention look unlikely). The guide's unconstrained
   model (structure="full": one free row per class, Dirichlet alpha = 1) is kept for comparison. Without
   constraints it is not identifiable on these sparse votes: restarts disagree and the best solution loses the
   class meanings (C06 and C12 become G3).

EM: stop when |delta| < 1e-6, 20 restarts (restart 0 = deterministic init a = 0.7, b = 0.05; others add
log-normal noise), keep the restart with the highest penalised log-likelihood (log-lik + log Beta prior).
"""
import numpy as np
import pandas as pd

CLASSES = ["A1", "A2", "A3", "A4", "G1", "G2", "G3", "G4", "G5", "N"]
KIND_CLASSES = {"dead": ["A1", "G1", "G2", "G3", "G4"], "fill": ["A2", "A3", "N"],
                "clock": ["A4", "N"], "transfer": ["G5", "N"]}
G_TYPES = ["G1", "G2", "G3", "G4", "G5"]
SPEAKS_FOR = {"R9": {"G3", "G4"}}        # rule-specific override of the label it emits
ABSTAIN = "-"

# D33 - defining rules: inside its applicability domain, the rule's firing condition IS the typology's
# definition of the class it votes for (G2: >= 90% of one city dead; G4: one zone, 06-11 h, <= 6 h; G5: conserved
# transfer; A2: >= 2 zones held / interpolated together; A3: one zone held / interpolated while neighbours move;
# A4: repeated / missing hour on a clock-change date). Their propensity a gets pseudo-counts (9, 1) instead of (1, 1).
# Without this, EM cannot hold a class whose only evidence is one rule (G4 merged into G3-like mass, G5 emptied).
DEFINING_RULES = {"R2", "R8", "R10", "R12", "R13", "R14", "R16", "R19", "R20"}
PRIOR_A_DEFINING = (9.0, 1.0)

# Clock-change direction decides which clock rule can observe anything (D30):
# clocks go back -> an hour repeats (R13); clocks go forward -> an hour is missing (R14).
FALL_BACK = pd.to_datetime(["2022-10-30", "2023-10-29", "2023-03-19", "2024-03-10"])     # Europe Oct; Morocco -> GMT
SPRING_FORWARD = pd.to_datetime(["2023-03-26", "2024-03-31", "2023-04-23", "2024-04-14"])  # Europe Mar; Morocco -> GMT+1


def speaks_for(rule, label):
    if rule in SPEAKS_FOR:
        return set(SPEAKS_FOR[rule])
    return set(G_TYPES) if label == "G" else {label}


def feasible_classes(it):
    """Classes an item can carry, from its kind and hierarchy level (D29)."""
    if it.kind == "dead":
        if it.n_cities >= 2:
            return ["A1", "G1"]
        return ["A1", "G2", "G3"] if it.n_zones >= 2 else ["A1", "G3", "G4"]
    if it.kind == "fill":
        return ["A2", "N"] if it.n_zones >= 2 else ["A3", "N"]
    return list(KIND_CLASSES[it.kind])


def applicability(items, rules, rule_kind):
    """n x m boolean: does rule r's precondition see item i (D30)?"""
    k = items.kind.to_numpy()
    spring = pd.to_datetime(items.start).dt.normalize().isin(SPRING_FORWARD).to_numpy()
    out = np.zeros((len(items), len(rules)), dtype=bool)
    for j, r in enumerate(rules):
        m = k == rule_kind[r]
        if r in ("R2", "R12"):
            m &= items.n_hold_zones.fillna(0).to_numpy() >= 1
        elif r in ("R19", "R20"):
            m &= items.n_interp_zones.fillna(0).to_numpy() >= 1
        elif r == "R13":
            m &= ~spring
        elif r == "R14":
            m &= spring
        elif r == "R15":
            m &= items.delta_star_min.notna().to_numpy()
        out[:, j] = m
    return out


class DawidSkene:
    def __init__(self, structure="constrained", alpha=1.0, prior_a=(1.0, 1.0), prior_b=(1.0, 9.0), prior_pi=1.0, use_defining=True,
                 tol=1e-6, max_iter=3000, n_restarts=20, init_fire=0.7, init_other=0.05, noise=0.5, seed=0):
        assert structure in ("constrained", "full")
        self.structure, self.alpha, self.prior_a, self.prior_b = structure, alpha, prior_a, prior_b
        self.use_defining, self.prior_pi = use_defining, prior_pi
        self.tol, self.max_iter, self.n_restarts = tol, max_iter, n_restarts
        self.init_fire, self.init_other, self.noise, self.seed = init_fire, init_other, noise, seed

    # ------------------------------------------------------------ setup
    def _prepare(self, votes, items, rule_kind):
        self.rules = list(votes.columns)
        self.vocab = {r: [ABSTAIN] + sorted(votes[r].dropna().unique().tolist()) for r in self.rules}
        n, m, K = len(votes), len(self.rules), len(CLASSES)
        O = np.zeros((n, m), dtype=int)
        for j, r in enumerate(self.rules):
            idx = {l: k for k, l in enumerate(self.vocab[r])}
            O[:, j] = [0 if pd.isna(v) else idx[v] for v in votes[r]]
        self.kinds = sorted(KIND_CLASSES)
        kind_idx = np.array([self.kinds.index(k) for k in items.kind])
        feas = np.zeros((n, K), dtype=bool)
        for i, it in enumerate(items.itertuples()):
            feas[i, [CLASSES.index(c) for c in feasible_classes(it)]] = True
        app = applicability(items, self.rules, rule_kind)
        # a fired rule must be applicable (sanity: preconditions are a superset of firing conditions)
        assert not ((O > 0) & ~app).any(), "a rule fired outside its applicability domain"
        self._match = {r: [None] + [np.isin(CLASSES, list(speaks_for(r, l))) for l in self.vocab[r][1:]] for r in self.rules}
        return O, kind_idx, feas, app

    def _prior_a(self, r):
        return PRIOR_A_DEFINING if (self.use_defining and r in DEFINING_RULES) else self.prior_a

    def _theta(self, params):
        """Per rule: K x V matrix of P(output | class)."""
        if self.structure == "full":
            return params
        th = []
        for r in self.rules:
            V = len(self.vocab[r])
            t = np.zeros((len(CLASSES), V))
            for o in range(1, V):
                a, b = params[r][o]
                t[:, o] = np.where(self._match[r][o], a, b)
            s = t[:, 1:].sum(axis=1)
            over = s > 0.999
            if over.any():
                t[over, 1:] *= (0.999 / s[over])[:, None]
            t[:, 0] = 1 - t[:, 1:].sum(axis=1)
            th.append(t)
        return th

    def _init_params(self, rng, noisy):
        def jit(p):
            return float(np.clip(p * np.exp(rng.normal(0, self.noise)), 1e-3, 0.95)) if noisy else p
        if self.structure == "constrained":
            return {r: [None] + [(jit(self.init_fire), jit(self.init_other)) for _ in self.vocab[r][1:]] for r in self.rules}
        th = []
        for r in self.rules:
            V = len(self.vocab[r])
            t = np.zeros((len(CLASSES), V))
            for o in range(1, V):
                t[:, o] = [jit(self.init_fire) if mt else jit(self.init_other) for mt in self._match[r][o]]
            s = t[:, 1:].sum(axis=1, keepdims=True)
            t[:, 1:] = np.where(s > 0.99, t[:, 1:] * 0.99 / s, t[:, 1:])
            t[:, 0] = 1 - t[:, 1:].sum(axis=1)
            th.append(t)
        return th

    # ------------------------------------------------------------ EM
    def _estep(self, O, kind_idx, feas, app, pi, th):
        with np.errstate(divide="ignore"):
            L = np.log(pi[kind_idx])
            for j, t in enumerate(th):
                L = L + np.where(app[:, [j]], np.log(t[:, O[:, j]]).T, 0.0)
        L[~feas] = -np.inf
        mx = L.max(axis=1, keepdims=True)
        e = np.exp(L - mx)
        ll = float((mx[:, 0] + np.log(e.sum(axis=1))).sum())
        return e / e.sum(axis=1, keepdims=True), ll

    def _log_prior(self, params):
        if self.structure == "full":
            return float(sum(self.alpha * np.log(np.clip(t, 1e-12, 1)).sum() for t in params))
        (b1, b0) = self.prior_b
        lp = 0.0
        for r in self.rules:
            a1, a0 = self._prior_a(r)
            for a, b in params[r][1:]:
                lp += a1 * np.log(a) + a0 * np.log(1 - a) + b1 * np.log(b) + b0 * np.log(1 - b)
        return float(lp)

    def _mstep(self, O, kind_idx, feas, app, q):
        pi = np.zeros((len(self.kinds), len(CLASSES)))
        for k in range(len(self.kinds)):
            sel = kind_idx == k
            dom = np.isin(CLASSES, KIND_CLASSES[self.kinds[k]])
            s = (q[sel].sum(axis=0) if sel.any() else 0) + self.prior_pi * dom    # D34: Dirichlet(prior_pi) on pi
            pi[k] = s / s.sum()
        if self.structure == "full":
            th = []
            for j, r in enumerate(self.rules):
                V = len(self.vocab[r])
                qa = q[app[:, j]]
                cnt = qa.T @ np.eye(V)[O[app[:, j], j]]
                th.append((self.alpha + cnt) / (self.alpha * V + qa.sum(axis=0)[:, None]))
            return pi, th
        (b1, b0) = self.prior_b
        params = {}
        for j, r in enumerate(self.rules):
            params[r] = [None]
            a1, a0 = self._prior_a(r)
            sel = app[:, j]
            for o in range(1, len(self.vocab[r])):
                mt = self._match[r][o]
                mass_m, mass_n = q[sel][:, mt].sum(axis=1), q[sel][:, ~mt].sum(axis=1)
                fired = O[sel, j] == o
                a = (a1 + mass_m[fired].sum()) / (a1 + a0 + mass_m.sum())
                b = (b1 + mass_n[fired].sum()) / (b1 + b0 + mass_n.sum())
                params[r].append((a, b))
        return pi, params

    def _run(self, O, kind_idx, feas, app, params):
        pi = np.zeros((len(self.kinds), len(CLASSES)))
        for k in range(len(self.kinds)):
            d = np.isin(CLASSES, KIND_CLASSES[self.kinds[k]])
            pi[k] = d / d.sum()
        q, ll = self._estep(O, kind_idx, feas, app, pi, self._theta(params))
        prev, it = -np.inf, 0
        for it in range(1, self.max_iter + 1):
            pi, params = self._mstep(O, kind_idx, feas, app, q)
            q, ll = self._estep(O, kind_idx, feas, app, pi, self._theta(params))
            if abs(ll - prev) < self.tol:
                break
            prev = ll
        return dict(q=q, ll=ll, lp=ll + self._log_prior(params), pi=pi, params=params, theta=self._theta(params), n_iter=it)

    # ------------------------------------------------------------ public API
    def fit(self, votes, items, rule_kind):
        """votes: items x rules (label or NaN); items: rows of items.csv aligned with votes; rule_kind: rule -> kind."""
        items = items.reset_index(drop=True)
        O, kind_idx, feas, app = self._prepare(votes, items, rule_kind)
        self._app, self._feas = app, feas
        rng = np.random.default_rng(self.seed)
        runs = [self._run(O, kind_idx, feas, app, self._init_params(rng, noisy=r > 0)) for r in range(self.n_restarts)]
        best = int(np.argmax([r["lp"] for r in runs]))
        self.best_ = runs[best]
        lab = self.best_["q"].argmax(axis=1)
        self.restarts_ = pd.DataFrame([dict(restart=i, loglik=round(r["ll"], 4), penalised=round(r["lp"], 4), n_iter=r["n_iter"],
                                            agree_with_best=round(float((r["q"].argmax(axis=1) == lab).mean()), 4))
                                       for i, r in enumerate(runs)])
        self.q_ = pd.DataFrame(self.best_["q"], index=votes.index, columns=CLASSES)
        self.pi_ = pd.DataFrame(self.best_["pi"], index=self.kinds, columns=CLASSES)
        self.loglik_ = self.best_["ll"]
        return self

    def params_table(self):
        """a = propensity on the classes an output speaks for, b = false-positive rate (constrained structure)."""
        rows = []
        for j, r in enumerate(self.rules):
            t = self.best_["theta"][j]
            for o in range(1, len(self.vocab[r])):
                mt = self._match[r][o]
                rows.append(dict(rule=r, output=self.vocab[r][o], speaks_for="+".join(sorted(speaks_for(r, self.vocab[r][o]))),
                                 n_applicable=int(self._app[:, j].sum()),
                                 a_propensity=round(float(t[mt, o].mean()), 4), b_false_positive=round(float(t[~mt, o].mean()), 4)))
        return pd.DataFrame(rows)

    def rule_precision(self, votes):
        """Learned accuracy per rule: mean posterior mass on the classes its vote speaks for, over the items it fired on."""
        rows = []
        for r in self.rules:
            fired = votes[r].notna()
            if not fired.any():
                rows.append(dict(rule=r, n_fired=0, learned_precision=np.nan))
                continue
            prec = [self.q_.loc[i, list(speaks_for(r, votes.at[i, r]))].sum() for i in votes.index[fired]]
            rows.append(dict(rule=r, n_fired=int(fired.sum()), learned_precision=round(float(np.mean(prec)), 3)))
        return pd.DataFrame(rows)

    def sample(self, items, rng):
        """Synthetic votes drawn from the fitted model for the same items (feasible sets and applicability kept)."""
        items = items.reset_index(drop=True)
        ys, rows = [], []
        for i, it in enumerate(items.itertuples()):
            p = self.best_["pi"][self.kinds.index(it.kind)] * self._feas[i]
            y = rng.choice(len(CLASSES), p=p / p.sum())
            v = {}
            for j, r in enumerate(self.rules):
                if not self._app[i, j]:
                    v[r] = np.nan
                    continue
                pr = np.clip(self.best_["theta"][j][y], 0, None)
                o = rng.choice(len(self.vocab[r]), p=pr / pr.sum())
                v[r] = np.nan if o == 0 else self.vocab[r][o]
            ys.append(CLASSES[y]); rows.append(v)
        return pd.DataFrame(rows, columns=self.rules), ys


def majority_vote(votes, items):
    """Baseline labeler: plurality over specific labels within the feasible set; ties -> first in CLASSES order;
    no usable vote -> 'N' for fill/clock/transfer, first feasible class for dead."""
    out = []
    for (i, row), it in zip(votes.iterrows(), items.itertuples()):
        feas = feasible_classes(it)
        score = pd.Series(0.0, index=feas)
        for r, l in row.dropna().items():
            sp = [c for c in speaks_for(r, l) if c in feas]
            for c in sp:
                score[c] += 1 / len(sp)
        out.append(score.idxmax() if score.max() > 0 else ("N" if "N" in feas else feas[0]))
    return pd.Series(out, index=votes.index)


def entropy(q):
    p = np.clip(np.asarray(q, dtype=float), 1e-12, 1)
    return -(p * np.log(p)).sum(axis=1)


def ece(conf, correct, n_bins=10):
    """Expected calibration error (guide eq. 18)."""
    conf, correct = np.asarray(conf, dtype=float), np.asarray(correct, dtype=float)
    bins = np.minimum((conf * n_bins).astype(int), n_bins - 1)
    return float(sum(abs(correct[bins == b].mean() - conf[bins == b].mean()) * (bins == b).mean()
                     for b in range(n_bins) if (bins == b).any()))
