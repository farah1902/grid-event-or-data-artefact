"""Deep multivariate baseline detectors (D82): GDN and USAD, re-implemented in plain PyTorch.

GDN  (Deng & Hooi, AAAI 2021, arXiv 2106.06947): learned top-k graph over sensor embeddings, graph attention on a
     sliding window, forecast of the current value; anomaly score = per-sensor forecast error normalised by its
     median and inter-quartile range, smoothed by a trailing mean. Settings of the authors' released run script
     (github.com/d-ailin/GDN, run.sh): window 5, dim 64, top-k 5, one output layer, batch 32, 30 epochs, Adam
     (lr 1e-3, no weight decay), validation ratio 0.2 (a random contiguous block, as get_loaders), early stopping after
     15 epochs without improvement; dropout 0.2, BatchNorm as models/GDN.py; error normalisation and 4-step trailing
     mean as evaluate.get_err_scores. torch_geometric is replaced by dense attention over the k neighbours (the same
     computation for 15 nodes).
USAD (Audibert et al., KDD 2020, doi 10.1145/3394486.3403392): one encoder, two decoders, adversarial two-phase
     training; score = alpha * ||W - AE1(W)||^2 + beta * ||W - AE2(AE1(W))||^2. Settings of the authors' code
     (github.com/manigalati/usad, commit e25af45: usad.py and USAD.ipynb): window 12, latent size 12 x 100, min-max
     scaling fitted on normal training data, first 80 % of the training windows used for training, batch 7,919,
     100 epochs, Adam with default settings, alpha = beta = 0.5.

Protocol shared with every predictor of the benchmark (D53, D54): inputs are the relative level rho (missing -> 1),
min-max scaled per zone on the clean steps of the training fold (both authors' pipelines scale each sensor to [0, 1]
on the training data: GDN scripts/process_swat.py, USAD.ipynb; GDN's errors are therefore in scaled units); models are trained on the real southern series with two-fold temporal cross-fitting at detector.SPLIT, on windows in
which no zone has a rule state, so every injected step is scored by a model that never saw it. Unlike our detector,
the baselines read the raw series at inference (rule states are not masked), like the Isolation Forest and LOF
baselines. Both return a zone score per time step (GDN: a_i(t); USAD: the score restricted to the zone's entries of
the window ending at t), which then goes through the same event formation as every detector (D60).
"""
import math, random, time
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F

import detector as _D

GDN_CFG = dict(win=5, dim=64, topk=5, batch=32, epochs=30, lr=1e-3, decay=0.0, val_ratio=0.2, early_stop=15, dropout=0.2)
USAD_CFG = dict(win=12, hidden=100, batch=7919, epochs=100, train_frac=0.8, alpha=0.5, beta=0.5)


def _inputs(P):
    """rho as float32 (missing -> 1), and the time steps at which no zone has a rule state or a missing value."""
    rho = P["rho"].to_numpy(dtype=np.float32)
    x = np.where(np.isnan(rho), 1.0, rho).astype(np.float32)
    clean_t = ~(P["mask"].to_numpy().any(axis=1) | np.isnan(rho).any(axis=1))
    return x, rho, clean_t


def _window_ok(clean_t, n):
    """ok[t] = steps t-n+1 .. t all clean."""
    c = pd.Series(clean_t.astype(float)).rolling(n, min_periods=n).min().to_numpy()
    return np.nan_to_num(c, nan=0.0) > 0.5


def _windows(x, ends, n):
    """Windows of n steps ending at each t in ends (inclusive): (len(ends), n, N)."""
    return x[ends[:, None] - np.arange(n - 1, -1, -1)[None, :]]


# ------------------------------------------------------------------ GDN
class GDN(nn.Module):
    def __init__(self, n_nodes, win, dim=64, topk=5, dropout=0.2):
        super().__init__()
        self.n, self.k = n_nodes, min(topk, n_nodes)
        self.emb = nn.Embedding(n_nodes, dim)
        nn.init.kaiming_uniform_(self.emb.weight, a=math.sqrt(5))
        self.lin = nn.Linear(win, dim, bias=False)
        self.att_i = nn.Parameter(torch.empty(dim)); self.att_j = nn.Parameter(torch.empty(dim))
        self.att_em_i = nn.Parameter(torch.zeros(dim)); self.att_em_j = nn.Parameter(torch.zeros(dim))
        bound = math.sqrt(6.0 / (1 + dim))                       # glorot on a (1, 1, dim) parameter, as GraphLayer
        nn.init.uniform_(self.att_i, -bound, bound); nn.init.uniform_(self.att_j, -bound, bound)
        nn.init.xavier_uniform_(self.lin.weight)
        self.bias = nn.Parameter(torch.zeros(dim))
        self.bn_gnn = nn.BatchNorm1d(dim)
        self.bn_out = nn.BatchNorm1d(dim)
        self.dp = nn.Dropout(dropout)
        self.out = nn.Linear(dim, 1)                              # OutLayer with out_layer_num = 1

    def neighbours(self):
        """Learned graph: for each node, its top-k nodes by cosine similarity of the embeddings (self included,
        as in models/GDN.py, where self-loops are then removed and re-added). Boolean (N, N): row i = neighbours of i."""
        w = self.emb.weight.detach()
        cos = (w @ w.T) / (w.norm(dim=1, keepdim=True) * w.norm(dim=1, keepdim=True).T)
        idx = torch.topk(cos, self.k, dim=-1).indices
        A = torch.zeros(self.n, self.n, dtype=torch.bool, device=w.device)
        A[torch.arange(self.n, device=w.device).unsqueeze(1), idx] = True
        A |= torch.eye(self.n, dtype=torch.bool, device=w.device)
        return A

    def forward(self, x):                                         # x: (B, N, win) -> (B, N)
        B_, N, _ = x.shape
        h = self.lin(x)                                           # (B, N, dim)
        e = self.emb.weight.unsqueeze(0).expand(B_, N, -1)
        si = (h * self.att_i).sum(-1) + (e * self.att_em_i).sum(-1)
        sj = (h * self.att_j).sum(-1) + (e * self.att_em_j).sum(-1)
        logits = F.leaky_relu(si.unsqueeze(2) + sj.unsqueeze(1), 0.2)          # (B, i, j)
        logits = logits.masked_fill(~self.neighbours().unsqueeze(0), float("-inf"))
        alpha = torch.softmax(logits, dim=-1)
        z = alpha @ h + self.bias                                 # (B, N, dim)
        z = F.relu(self.bn_gnn(z.reshape(B_ * N, -1))).reshape(B_, N, -1)
        z = z * self.emb.weight.unsqueeze(0)
        z = F.relu(self.bn_out(z.permute(0, 2, 1))).permute(0, 2, 1)
        return self.out(self.dp(z)).squeeze(-1)


def _fit_gdn(x, ends_train, cfg, seed, device, log):
    torch.manual_seed(seed); random.seed(seed); np.random.seed(seed)
    win = cfg["win"]
    n = len(ends_train)
    n_val = int(n * cfg["val_ratio"])
    v0 = random.randrange(n - n_val)                              # a random contiguous validation block (get_loaders)
    val = ends_train[v0:v0 + n_val]
    tr = np.concatenate([ends_train[:v0], ends_train[v0 + n_val:]])
    X = torch.as_tensor(x, device=device)
    model = GDN(x.shape[1], win, cfg["dim"], cfg["topk"], cfg["dropout"]).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=cfg["lr"], weight_decay=cfg["decay"])

    def batch(ends):
        idx = torch.as_tensor(ends, device=device)
        inp = X[idx.unsqueeze(1) - torch.arange(win, 0, -1, device=device).unsqueeze(0)]     # steps t-win .. t-1
        return inp.permute(0, 2, 1), X[idx]                                                  # (B, N, win), (B, N)

    best, best_state, bad, hist = np.inf, None, 0, []
    rng = np.random.default_rng(seed)
    for ep in range(cfg["epochs"]):
        model.train(); t0 = time.time(); tot = 0.0
        perm = rng.permutation(tr)
        for i in range(0, len(perm), cfg["batch"]):
            inp, y = batch(perm[i:i + cfg["batch"]])
            loss = F.mse_loss(model(inp), y)
            opt.zero_grad(); loss.backward(); opt.step(); tot += float(loss) * len(y)
        model.eval()
        with torch.no_grad():
            se = 0.0
            for i in range(0, len(val), 1024):
                inp, y = batch(val[i:i + 1024])
                se += F.mse_loss(model(inp), y, reduction="sum").item()
            vl = se / (len(val) * x.shape[1])
        hist.append(dict(epoch=ep, train=tot / len(tr), val=vl, sec=time.time() - t0))     # both: MSE per zone-step
        if log:
            print(f"    GDN epoch {ep:2d} train {hist[-1]['train']:.6f} val {vl:.6f} ({time.time() - t0:.0f} s)", flush=True)
        if vl < best:
            best, best_state, bad = vl, {k: v.detach().clone() for k, v in model.state_dict().items()}, 0
        else:
            bad += 1
            if bad >= cfg["early_stop"]:
                break
    model.load_state_dict(best_state); model.eval()
    return model, pd.DataFrame(hist)


@torch.no_grad()
def _predict_gdn(model, x, ends, win, device):
    X = torch.as_tensor(x, device=device)
    out = np.full((len(ends), x.shape[1]), np.nan, dtype=np.float64)
    for i in range(0, len(ends), 4096):
        idx = torch.as_tensor(ends[i:i + 4096], device=device)
        inp = X[idx.unsqueeze(1) - torch.arange(win, 0, -1, device=device).unsqueeze(0)].permute(0, 2, 1)
        out[i:i + 4096] = model(inp).cpu().numpy()
    return out


# ------------------------------------------------------------------ USAD
class _Enc(nn.Module):
    def __init__(self, n_in, n_lat):
        super().__init__()
        self.l1, self.l2, self.l3 = nn.Linear(n_in, n_in // 2), nn.Linear(n_in // 2, n_in // 4), nn.Linear(n_in // 4, n_lat)

    def forward(self, w):
        return F.relu(self.l3(F.relu(self.l2(F.relu(self.l1(w))))))


class _Dec(nn.Module):
    def __init__(self, n_lat, n_out):
        super().__init__()
        self.l1, self.l2, self.l3 = nn.Linear(n_lat, n_out // 4), nn.Linear(n_out // 4, n_out // 2), nn.Linear(n_out // 2, n_out)

    def forward(self, z):
        return torch.sigmoid(self.l3(F.relu(self.l2(F.relu(self.l1(z))))))


class USAD(nn.Module):
    def __init__(self, w_size, z_size):
        super().__init__()
        self.enc, self.dec1, self.dec2 = _Enc(w_size, z_size), _Dec(z_size, w_size), _Dec(z_size, w_size)


def _fit_usad(xs, ends_train, cfg, seed, device, log):
    torch.manual_seed(seed)
    win, N = cfg["win"], xs.shape[1]
    W = torch.as_tensor(_windows(xs, ends_train, win).reshape(len(ends_train), -1), device=device)
    W = W[: int(np.floor(cfg["train_frac"] * len(W)))]           # first 80 % (the notebook's windows_normal_train)
    m = USAD(win * N, win * cfg["hidden"]).to(device)
    o1 = torch.optim.Adam(list(m.enc.parameters()) + list(m.dec1.parameters()))
    o2 = torch.optim.Adam(list(m.enc.parameters()) + list(m.dec2.parameters()))
    hist = []
    for ep in range(cfg["epochs"]):
        n = ep + 1; t0 = time.time()
        for i in range(0, len(W), cfg["batch"]):                 # DataLoader(shuffle=False)
            b = W[i:i + cfg["batch"]]
            # as usad.training: each optimiser clears only its own parameters, so gradients of the other decoder
            # carry over to the next phase (kept, to reproduce the authors' training)
            z = m.enc(b); w1 = m.dec1(z); w3 = m.dec2(m.enc(w1))
            l1 = 1 / n * torch.mean((b - w1) ** 2) + (1 - 1 / n) * torch.mean((b - w3) ** 2)
            l1.backward(); o1.step(); o1.zero_grad()
            z = m.enc(b); w1 = m.dec1(z); w2 = m.dec2(z); w3 = m.dec2(m.enc(w1))
            l2 = 1 / n * torch.mean((b - w2) ** 2) - (1 - 1 / n) * torch.mean((b - w3) ** 2)
            l2.backward(); o2.step(); o2.zero_grad()
        hist.append(dict(epoch=ep, loss1=float(l1), loss2=float(l2), sec=time.time() - t0))
        if log and (ep % 20 == 0 or ep == cfg["epochs"] - 1):
            print(f"    USAD epoch {ep:3d} loss1 {float(l1):.6f} loss2 {float(l2):.6f}", flush=True)
    m.eval()
    return m, pd.DataFrame(hist)


@torch.no_grad()
def _score_usad(m, xs, ends, cfg, device):
    """Per-zone score of the window ending at t: alpha * mean_k (W - AE1(W))^2 + beta * mean_k (W - AE2(AE1(W)))^2
    over the zone's win entries (the official score is the same average over all entries of the window)."""
    win, N = cfg["win"], xs.shape[1]
    out = np.full((len(ends), N), np.nan, dtype=np.float64)
    for i in range(0, len(ends), 8192):
        e = ends[i:i + 8192]
        b = torch.as_tensor(_windows(xs, e, win).reshape(len(e), -1), device=device)
        w1 = m.dec1(m.enc(b)); w2 = m.dec2(m.enc(w1))
        s = cfg["alpha"] * (b - w1) ** 2 + cfg["beta"] * (b - w2) ** 2
        out[i:i + 8192] = s.reshape(len(e), win, N).mean(dim=1).cpu().numpy()
    return out


# ------------------------------------------------------------------ cross-fitted fit / score
def _minmax(x, sel):
    """Per-zone min-max scaling fitted on the selected (clean, training-fold) steps, as both authors' pipelines
    (GDN scripts/process_swat.py, USAD.ipynb: MinMaxScaler fitted on the normal training data)."""
    lo, hi = x[sel].min(axis=0), x[sel].max(axis=0)
    return lo, hi


def _scale(x, lo, hi):
    return ((x - lo) / np.where(hi > lo, hi - lo, 1.0)).astype(np.float32)


def fit(P, device="cpu", seed=0, log=True, which=("GDN", "USAD")):
    """Two-fold cross-fitted GDN and USAD on a (real) panel: {name: {train_fold: (model, (lo, hi))}}, histories.
    Both are trained on per-zone min-max scaled rho (scaler fitted on the clean steps of the training fold)."""
    x, _, clean_t = _inputs(P)
    fold = P["rho"].index >= _D.SPLIT
    out, hist = {k: {} for k in which}, []
    for tr_fold in (False, True):
        in_fold = fold == tr_fold
        lo, hi = _minmax(x, clean_t & in_fold)
        xs = _scale(x, lo, hi)
        if "GDN" in which:
            # target t and its window t-win..t-1 clean, all inside the training fold
            ends = np.flatnonzero(_window_ok(clean_t, GDN_CFG["win"] + 1) & in_fold & (np.arange(len(fold)) >= GDN_CFG["win"]))
            if log:
                print(f"  GDN  | trained on {'>=' if tr_fold else '<'} {_D.SPLIT.date()}: {len(ends)} windows", flush=True)
            t0 = time.time()
            m, h = _fit_gdn(xs, ends, GDN_CFG, seed + int(tr_fold), device, log)
            out["GDN"][tr_fold] = (m, (lo, hi))
            hist.append(h.assign(model="GDN", train_fold=tr_fold, seconds=time.time() - t0))
        if "USAD" in which:
            ends = np.flatnonzero(_window_ok(clean_t, USAD_CFG["win"]) & in_fold)      # windows of 12 clean steps
            if log:
                print(f"  USAD | trained on {'>=' if tr_fold else '<'} {_D.SPLIT.date()}: {len(ends)} windows", flush=True)
            t0 = time.time()
            m, h = _fit_usad(xs, ends, USAD_CFG, seed + int(tr_fold), device, log)
            out["USAD"][tr_fold] = (m, (lo, hi))
            hist.append(h.assign(model="USAD", train_fold=tr_fold, seconds=time.time() - t0))
    return out, pd.concat(hist, ignore_index=True)


def scores(P, models, device="cpu"):
    """Zone scores (time x zone frames) of GDN and USAD on any panel (real or injected); each fold is scored by the
    model trained on the other fold. NaN where rho is missing or no full window exists."""
    x, rho, _ = _inputs(P)
    T, N = x.shape
    fold = P["rho"].index >= _D.SPLIT
    Z = {}
    # GDN: forecast in scaled units, absolute error, robust normalisation per zone over the whole series, 4-step mean
    err = np.full((T, N), np.nan)
    for tr_fold, (m, (lo, hi)) in models["GDN"].items():
        ends = np.flatnonzero((fold != tr_fold) & (np.arange(T) >= GDN_CFG["win"]))
        pred = _predict_gdn(m, _scale(x, lo, hi), ends, GDN_CFG["win"], device)
        err[ends] = np.abs(_scale(rho, lo, hi)[ends] - pred)            # rho missing -> NaN error
    med = np.nanmedian(err, axis=0)
    iqr = np.nanpercentile(err, 75, axis=0) - np.nanpercentile(err, 25, axis=0)
    a = (err - med) / (np.abs(iqr) + 1e-2)
    a = pd.DataFrame(a).rolling(4, min_periods=1).mean().to_numpy()       # mean of t-3 .. t (before_num = 3)
    a[np.isnan(rho)] = np.nan
    Z["GDN"] = pd.DataFrame(a, index=P["rho"].index, columns=P["rho"].columns)
    # USAD: per-zone score of the window ending at t (min-max scaling of the model's training fold)
    s = np.full((T, N), np.nan)
    for tr_fold, (m, (lo, hi)) in models["USAD"].items():
        xs = _scale(x, lo, hi)
        ends = np.flatnonzero((fold != tr_fold) & (np.arange(T) >= USAD_CFG["win"] - 1))
        s[ends] = _score_usad(m, xs, ends, USAD_CFG, device)
    s[np.isnan(rho)] = np.nan
    Z["USAD"] = pd.DataFrame(s, index=P["rho"].index, columns=P["rho"].columns)
    return Z


def save(models, path):
    torch.save({name: {str(k): (m.state_dict(), ex) for k, (m, ex) in d.items()} for name, d in models.items()}, path)


def load(path, n_nodes, device="cpu"):
    blob = torch.load(path, map_location=device, weights_only=False)
    out = {}
    for name, d in blob.items():
        out[name] = {}
        for k, (sd, ex) in d.items():
            m = GDN(n_nodes, GDN_CFG["win"], GDN_CFG["dim"], GDN_CFG["topk"], GDN_CFG["dropout"]) if name == "GDN" else \
                USAD(USAD_CFG["win"] * n_nodes, USAD_CFG["win"] * USAD_CFG["hidden"])
            m.load_state_dict(sd); m.to(device).eval()
            out[name][k == "True"] = (m, ex)
    return out
