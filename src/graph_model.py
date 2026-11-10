"""TCN-GAT nowcaster (guide eq. 13 with its graph section) for the southern system: NB4.

Nodes are the 15 southern zones. Each zone's past (rho and its rule mask) goes through a causal temporal
convolutional network (TCN) shared by all zones; its receptive field is 253 steps (about 42 h). A graph-attention
layer then lets zone z read the *current* rho of its neighbours (leave-one-zone-out: z's own current value is never
an input):
  - same-city zones are always neighbours;
  - cross-city edges are learned, GDN-style: every zone has a trainable embedding and keeps the top-k = 4 zones of
    other cities with the highest cosine similarity (recomputed at every forward pass).
Masked neighbours (rule-flagged or missing at t) are excluded from the attention. The head combines the TCN state,
the attention message, the node embedding, calendar features and the zone's own value 1 day and 7 days earlier.

`graph=False` is the ablation without a graph: the TCN on the zone's own past only, the analogue of the LightGBM
forecast.

Hybrid (D59; `base=` in fit/apply): the network also receives a base forecast (NB3's cross-fitted LightGBM forecast)
and outputs base + a learned correction. The last layer starts at zero, so training starts from the base exactly, and
the graph attention also reads each neighbour's current base residual. On the real data the correction does not
generalise to the validation months, with or without the graph: both hybrids end at LightGBM's MAE (F38). Training uses the masked Huber loss (delta 0.1) and the same two-fold temporal cross-fitting as the
LightGBM predictors (D41), so every prediction is out of sample. The decomposition (eq. 14-16) is unchanged: the
residual e = rho - rho_hat goes through the same phase-aligned MODWT, hierarchy and level scores (D42, D43, D51).

Efficiency: the TCN is fully convolutional, so it runs once over contiguous chunks (warm-up = receptive field, then
C target steps) instead of once per window. Predictions do not depend on chunk boundaries because the warm-up
covers the receptive field.

Deviation from the guide's text (D55): one network on rho, not one per MODWT band; the bands are taken of the
residual afterwards, exactly as for LightGBM (D42).
"""
import time
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F

import detector as _D
from detector import calendar   # the cross-fitting split is read from detector.SPLIT at call time (NB6 sets it for 2017)

CAL_COLS = ["tod_sin", "tod_cos", "dow_sin", "dow_cos", "weekend", "month_sin", "month_cos", "ramadan", "eid",
            "holiday", "morocco_gmt"]
LAGS = (144, 1008)   # 1 day and 7 days at 10 min


def default_device():
    return "cuda" if torch.cuda.is_available() else "cpu"


def calendar_matrix(index):
    c = calendar(index)
    c["dow_sin"], c["dow_cos"] = np.sin(2 * np.pi * c.dow / 7), np.cos(2 * np.pi * c.dow / 7)
    c["month_sin"], c["month_cos"] = np.sin(2 * np.pi * (c.month - 1) / 12), np.cos(2 * np.pi * (c.month - 1) / 12)
    return c[CAL_COLS].to_numpy(dtype=np.float32)


def panel_arrays(P, base=None):
    """Inputs from a panel: value (masked or missing -> 1 = expected), mask flag, target and its validity.
    base: optional frame like P["rho"] with a base forecast (the LightGBM forecast for the hybrid; D59)."""
    rho = P["rho"].to_numpy(dtype=np.float32)
    bad = P["mask"].to_numpy() | np.isnan(rho)
    x = np.where(bad, 1.0, rho).astype(np.float32)
    arr = dict(x=x, m=bad.astype(np.float32), y=np.nan_to_num(rho, nan=0.0).astype(np.float32),
               valid=(~bad).astype(np.float32), cal=calendar_matrix(P["rho"].index))
    if base is not None:
        arr["base"] = np.nan_to_num(base.reindex_like(P["rho"]).to_numpy(dtype=np.float32), nan=1.0)
    return arr


class CausalBlock(nn.Module):
    def __init__(self, cin, cout, k, d, dropout):
        super().__init__()
        self.pad = (k - 1) * d
        self.c1 = nn.Conv1d(cin, cout, k, dilation=d)
        self.c2 = nn.Conv1d(cout, cout, k, dilation=d)
        self.drop = nn.Dropout(dropout)
        self.skip = nn.Conv1d(cin, cout, 1) if cin != cout else nn.Identity()

    def forward(self, x):
        h = self.drop(F.relu(self.c1(F.pad(x, (self.pad, 0)))))
        h = self.drop(F.relu(self.c2(F.pad(h, (self.pad, 0)))))
        return F.relu(h + self.skip(x))


class TCNGAT(nn.Module):
    def __init__(self, n_nodes, city_idx, n_cal, graph=True, ch=32, emb=16, k_cross=4, heads=2,
                 dilations=(1, 2, 4, 8, 16, 32), kernel=3, dropout=0.1, use_base=False):
        super().__init__()
        self.Z, self.graph, self.k_cross, self.heads, self.use_base = n_nodes, graph, k_cross, heads, use_base
        self.rf = 1 + 2 * (kernel - 1) * sum(dilations)                                 # receptive field (steps)
        city = torch.as_tensor(city_idx)
        self.register_buffer("same_city", (city[:, None] == city[None, :]) & ~torch.eye(n_nodes, dtype=torch.bool))
        self.register_buffer("other_city", city[:, None] != city[None, :])
        self.emb = nn.Embedding(n_nodes, emb)
        layers, cin = [], 2
        for d in dilations:
            layers.append(CausalBlock(cin, ch, kernel, d, dropout)); cin = ch
        self.tcn = nn.Sequential(*layers)
        if graph:
            nc = 3 if use_base else 2      # hybrid: neighbours also send their current base-forecast residual
            self.q = nn.Linear(ch + emb, heads * ch)
            self.k = nn.Linear(ch + emb + nc, heads * ch)
            self.v = nn.Linear(ch + nc, heads * ch)
            self.att = nn.Parameter(torch.randn(heads, 2 * ch) * 0.1)
        head_in = ch + emb + n_cal + 2 * len(LAGS) + (heads * ch if graph else 0) + (1 if use_base else 0)
        self.head = nn.Sequential(nn.Linear(head_in, 64), nn.ReLU(), nn.Dropout(dropout), nn.Linear(64, 1))
        if use_base:                       # hybrid: start from the base forecast exactly (zero correction)
            nn.init.zeros_(self.head[-1].weight); nn.init.zeros_(self.head[-1].bias)

    def adjacency(self):
        """Allowed edges i <- j: same city, plus the top-k most similar zones of other cities (GDN-style)."""
        e = F.normalize(self.emb.weight, dim=1)
        sim = (e @ e.T).masked_fill(~self.other_city, -2.0)
        top = sim.topk(min(self.k_cross, self.Z), dim=1).indices      # a single-city system has no cross-city edge (NB6)
        cross = torch.zeros_like(self.same_city).scatter_(1, top, True) & self.other_city
        return self.same_city | cross

    def encode(self, xm):
        """xm: (N, Z, 2, L) value and mask -> (N, Z, ch, L); output at position p uses inputs up to p."""
        N, Z, _, L = xm.shape
        return self.tcn(xm.reshape(N * Z, 2, L)).reshape(N, Z, -1, L)

    def step(self, h, cur, lags, cal, return_attention=False, base=None):
        """h: (B, Z, ch) TCN state from inputs up to t-1; cur: (B, Z, 2) current value and mask of every zone;
        lags: (B, Z, 4) own value and mask 1 day and 7 days earlier; cal: (B, n_cal);
        base: (B, Z) base forecast at t (hybrid only): the output is base + a learned correction."""
        B, Z, C = h.shape
        emb = self.emb.weight.unsqueeze(0).expand(B, -1, -1)
        parts = [h, emb, cal.unsqueeze(1).expand(-1, Z, -1), lags]
        if self.use_base:
            parts.append(base.unsqueeze(-1))
        alpha = None
        if self.graph:
            H = self.heads
            cin = cur
            if self.use_base:                                                            # residual of neighbour j now
                cin = torch.cat([cur, ((cur[..., 0] - base) * (1 - cur[..., 1])).unsqueeze(-1)], -1)
            q = self.q(torch.cat([h, emb], -1)).view(B, Z, H, C)
            k = self.k(torch.cat([h, emb, cin], -1)).view(B, Z, H, C)
            v = self.v(torch.cat([h, cin], -1)).view(B, Z, H, C)
            sq = (q * self.att[:, :C]).sum(-1)                                           # (B, Z, H)
            sk = (k * self.att[:, C:]).sum(-1)
            logits = F.leaky_relu(sq.unsqueeze(2) + sk.unsqueeze(1), 0.2)                # (B, Zi, Zj, H)
            allowed = self.adjacency().unsqueeze(0) & (cur[:, :, 1] < 0.5).unsqueeze(1)  # neighbour j unmasked at t
            logits = logits.masked_fill(~allowed.unsqueeze(-1), -1e9)
            alpha = torch.softmax(logits, dim=2) * allowed.unsqueeze(-1).float()         # no usable neighbour -> 0
            parts.append(torch.einsum("bijh,bjhc->bihc", alpha, v).reshape(B, Z, H * C))
        out = self.head(torch.cat(parts, -1)).squeeze(-1)                                 # (B, Z)
        if self.use_base:
            out = base + out
        return (out, alpha) if return_attention else out


class Chunks:
    """Builds chunk inputs on the device: warm-up of `rf` steps, then C consecutive target steps."""
    def __init__(self, arr, rf, device):
        self.rf, self.dev = rf, device
        for k in ("x", "m", "y", "valid", "cal"):
            setattr(self, k, torch.as_tensor(arr[k], device=device))
        self.base = torch.as_tensor(arr["base"], device=device) if "base" in arr else None
        self.T, self.Z = self.x.shape

    def gather(self, a, idx, fill):
        bad = (idx < 0) | (idx >= self.T)
        out = a[idx.clamp(0, self.T - 1)]
        return out.masked_fill(bad.reshape(bad.shape + (1,) * (out.dim() - bad.dim())), fill)

    def __call__(self, starts, C):
        """starts: (N,) first target index of each chunk. Returns per-target tensors flattened to B = N*C rows."""
        s = torch.as_tensor(starts, device=self.dev, dtype=torch.long)
        L = self.rf + C - 1
        pos = s[:, None] - self.rf + torch.arange(L, device=self.dev)[None, :]          # input positions (N, L)
        xm = torch.stack([self.gather(self.x, pos, 1.0), self.gather(self.m, pos, 1.0)], dim=-1)   # (N, L, Z, 2)
        xm = xm.permute(0, 2, 3, 1)                                                      # (N, Z, 2, L)
        t = s[:, None] + torch.arange(C, device=self.dev)[None, :]                       # targets (N, C)
        tf = t.reshape(-1)
        cur = torch.stack([self.gather(self.x, tf, 1.0), self.gather(self.m, tf, 1.0)], dim=-1)
        lag = []
        for Lg in LAGS:
            lag += [self.gather(self.x, tf - Lg, 1.0), self.gather(self.m, tf - Lg, 1.0)]
        return dict(xm=xm, t=tf, cur=cur, lags=torch.stack(lag, -1), cal=self.gather(self.cal, tf, 0.0),
                    y=self.gather(self.y, tf, 0.0), valid=self.gather(self.valid, tf, 0.0),
                    base=self.gather(self.base, tf, 1.0) if self.base is not None else None)


def run_chunks(model, b, C):
    """Forward over chunk inputs b; returns predictions (N*C, Z) and the batch."""
    h = model.encode(b["xm"])                                                           # (N, Z, ch, L)
    N = h.shape[0]
    hs = h[..., model.rf - 1: model.rf - 1 + C]                                         # state for target j = input pos t-1
    hs = hs.permute(0, 3, 1, 2).reshape(N * C, h.shape[1], h.shape[2])                 # (N*C, Z, ch)
    return hs


def huber(err, delta=0.1):
    a = err.abs()
    return torch.where(a < delta, 0.5 * a ** 2, delta * (a - 0.5 * delta))


DEFAULT_CFG = dict(ch=32, emb=16, k_cross=4, lr=2e-3, wd=1e-4, chunk=256, chunks_per_batch=8, epochs=30,
                   patience=4, val_frac=0.15, max_batches=None)


def _make_model(n_nodes, city_idx, graph, cfg, device):
    return TCNGAT(n_nodes, city_idx, len(CAL_COLS), graph=graph, ch=cfg["ch"], emb=cfg["emb"],
                  k_cross=cfg["k_cross"], use_base=cfg.get("use_base", False)).to(device)


def _loss_over(model, ck, starts, C, weight_mask):
    tot, n = 0.0, 0.0
    for i in range(0, len(starts), 32):
        b = ck(starts[i:i + 32], C)
        pred = model.step(run_chunks(model, b, C), b["cur"], b["lags"], b["cal"], base=b["base"])
        w = b["valid"] * ck.gather(weight_mask, b["t"], 0.0).unsqueeze(1)
        tot += float((huber(pred - b["y"]) * w).sum()); n += float(w.sum())
    return tot / max(n, 1.0)


def _train_one(arr, train_mask, val_mask, city_idx, graph, cfg, device, seed, log):
    torch.manual_seed(seed); rng = np.random.default_rng(seed)
    model = _make_model(arr["x"].shape[1], city_idx, graph, cfg, device)
    ck = Chunks(arr, model.rf, device)
    C, NB = cfg["chunk"], cfg["chunks_per_batch"]
    tr_w = torch.as_tensor(train_mask.astype(np.float32), device=device)
    va_w = torch.as_tensor(val_mask.astype(np.float32), device=device)
    tr_idx, va_idx = np.flatnonzero(train_mask), np.flatnonzero(val_mask)
    va_starts = np.arange(va_idx.min(), va_idx.max() + 1, C)
    n_chunks = max(1, len(tr_idx) // C)
    n_batches = max(1, n_chunks // NB)
    if cfg.get("max_batches"):
        n_batches = min(n_batches, cfg["max_batches"])
    opt = torch.optim.AdamW(model.parameters(), lr=cfg["lr"], weight_decay=cfg["wd"])
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=cfg["epochs"] * n_batches)
    best, best_state, bad, hist = np.inf, None, 0, []
    for ep in range(cfg["epochs"]):
        model.train(); t0 = time.time(); tot = 0.0
        for _ in range(n_batches):
            starts = rng.choice(tr_idx, size=NB)                                       # chunk starts inside the fold
            b = ck(starts, C)
            pred = model.step(run_chunks(model, b, C), b["cur"], b["lags"], b["cal"], base=b["base"])
            w = b["valid"] * ck.gather(tr_w, b["t"], 0.0).unsqueeze(1)
            loss = (huber(pred - b["y"]) * w).sum() / w.sum().clamp(min=1)
            opt.zero_grad(); loss.backward(); nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step(); sched.step()
            tot += float(loss)
        model.eval()
        with torch.no_grad():
            vl = _loss_over(model, ck, va_starts, C, va_w)
        hist.append(dict(epoch=ep, train=tot / n_batches, val=vl, sec=time.time() - t0))
        if log:
            print(f"    epoch {ep:2d}  train {tot / n_batches:.5f}  val {vl:.5f}  ({time.time() - t0:.0f} s)", flush=True)
        if vl < best - 1e-7:
            best, best_state, bad = vl, {k: v.detach().clone() for k, v in model.state_dict().items()}, 0
        else:
            bad += 1
            if bad >= cfg["patience"]:
                break
    model.load_state_dict(best_state); model.eval()
    return model, pd.DataFrame(hist)


def _city_idx(P):
    cities = sorted(set(P["city"].values()))
    return [cities.index(P["city"][z]) for z in P["rho"].columns]


def fit_graph_models(P, graph=True, cfg=None, device=None, seed=0, log=True, base=None):
    """Two-fold cross-fitted TCN(-GAT) models: {train_fold: model} (train_fold True = trained on t >= SPLIT),
    plus the training history. Early stopping on the last 15 % of each training fold.
    base: out-of-sample base forecast (the cross-fitted LightGBM forecast) -> hybrid model (D59)."""
    cfg = {**DEFAULT_CFG, **(cfg or {}), "use_base": base is not None}
    device = device or default_device()
    arr = panel_arrays(P, base)
    fold = (P["rho"].index >= _D.SPLIT)
    has_target = arr["valid"].sum(axis=1) > 0
    models, hist = {}, []
    for tr_fold in (False, True):
        idx = np.flatnonzero(fold == tr_fold)
        cut = idx[int(len(idx) * (1 - cfg["val_frac"]))]
        train_mask = (fold == tr_fold) & has_target & (np.arange(len(fold)) < cut)
        val_mask = (fold == tr_fold) & has_target & (np.arange(len(fold)) >= cut)
        if log:
            print(f"  {'TCN-GAT' if graph else 'TCN (no graph)'} | trained on {'>=' if tr_fold else '<'} {_D.SPLIT.date()}: "
                  f"{int(train_mask.sum())} train / {int(val_mask.sum())} validation steps on {device}", flush=True)
        m, h = _train_one(arr, train_mask, val_mask, _city_idx(P), graph, cfg, device, seed + int(tr_fold), log)
        models[tr_fold] = m
        hist.append(h.assign(train_fold=tr_fold, graph=graph))
    return models, pd.concat(hist, ignore_index=True)


@torch.no_grad()
def apply_graph_models(P, models, chunk=512, base=None):
    """Out-of-sample rho_hat: each fold predicted by the model trained on the other fold (P may be injected data).
    base: the base forecast on the same panel (required by hybrid models)."""
    if any(m.use_base for m in models.values()) and base is None:
        raise ValueError("hybrid graph model: pass base= (the LightGBM forecast on this panel)")
    arr = panel_arrays(P, base)
    fold = (P["rho"].index >= _D.SPLIT)
    out = np.full(arr["x"].shape, np.nan, dtype=np.float64)
    for tr_fold, m in models.items():
        dev = m.emb.weight.device
        ck = Chunks(arr, m.rf, dev)
        idx = np.flatnonzero(fold != tr_fold)
        starts = np.arange(idx.min(), idx.max() + 1, chunk)
        for i in range(0, len(starts), 16):
            b = ck(starts[i:i + 16], chunk)
            pred = m.step(run_chunks(m, b, chunk), b["cur"], b["lags"], b["cal"], base=b["base"]).cpu().numpy()
            t = b["t"].cpu().numpy()
            keep = (t < len(fold)) & np.isin(t, idx)
            out[t[keep]] = pred[keep]
    return pd.DataFrame(out, index=P["rho"].index, columns=P["rho"].columns)


@torch.no_grad()
def learned_graph(P, models, n_chunks=40, chunk=256, seed=0, base=None):
    """Edges and mean attention of each graph model, averaged over clean target steps and heads.
    Returns {train_fold: (adjacency DataFrame (bool, row i <- column j), attention DataFrame)}."""
    arr = panel_arrays(P, base)
    zones = list(P["rho"].columns)
    fold = (P["rho"].index >= _D.SPLIT)
    rng = np.random.default_rng(seed)
    out = {}
    for tr_fold, m in models.items():
        if not m.graph:
            continue
        dev = m.emb.weight.device
        ck = Chunks(arr, m.rf, dev)
        idx = np.flatnonzero(fold != tr_fold)
        starts = rng.choice(idx[: -chunk], size=n_chunks, replace=False)
        acc = torch.zeros(len(zones), len(zones), device=dev); n = 0
        clean = torch.as_tensor(arr["m"].sum(axis=1) == 0, device=dev)
        for i in range(0, len(starts), 8):
            b = ck(starts[i:i + 8], chunk)
            _, a = m.step(run_chunks(m, b, chunk), b["cur"], b["lags"], b["cal"], return_attention=True, base=b["base"])
            keep = clean[b["t"].clamp(max=len(fold) - 1)]
            acc += a.mean(-1)[keep].sum(0); n += int(keep.sum())
        out[tr_fold] = (pd.DataFrame(m.adjacency().cpu().numpy(), index=zones, columns=zones),
                        pd.DataFrame((acc / max(n, 1)).cpu().numpy(), index=zones, columns=zones))
    return out


def save_models(models, path, cfg=None):
    m0 = next(iter(models.values()))
    torch.save({"cfg": {**DEFAULT_CFG, **(cfg or {}), "use_base": bool(m0.use_base)},
                "models": {str(k): {"state": m.state_dict(), "graph": m.graph} for k, m in models.items()}}, path)


def load_models(path, P, device=None):
    device = device or default_device()
    blob = torch.load(path, map_location=device)
    cfg = blob["cfg"]
    models = {}
    for k, v in blob["models"].items():
        m = _make_model(len(P["rho"].columns), _city_idx(P), v["graph"], cfg, device)
        m.load_state_dict(v["state"]); m.eval()
        models[k == "True"] = m
    return models
