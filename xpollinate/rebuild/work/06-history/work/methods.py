"""Reference (unpainted-appearance) estimators and the presence feature, for the bench.

M0  v4.1.2 raw C*ab (distance from a*=b*=0), noise-floor threshold, three tiers, 100 px component filter
M1  v4.1.2 LRC (C*ab relative to its L*-band median, over the IQR), noise-floor threshold
M2  TODO.md as written, no picks: per-L*-band median (a*, b*), smoothed along L*, robust spread; 'fit on the whole
    image, set aside pixels far from the fit, refit, a few rounds'; M2p adds step 6, a plane in x and y
M3  proposed: a smooth tone curve (a*, b*) = g(L*) threaded through the density peaks of the tone bands by consensus
    (RANSAC over bands, Tukey refit), anchored on the brightest paper; spread from the curve's own cluster;
    M3r adds a cast plane fitted on the paper anchor only (the border ring), never on the image
"""
from __future__ import annotations

import importlib.util
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent


# ---- common ---------------------------------------------------------------------------------------------------------

def to_lab(rgb):
    lab = cv2.cvtColor(np.ascontiguousarray(rgb, np.float32), cv2.COLOR_RGB2LAB)
    return lab[..., 0].copy(), lab[..., 1].copy(), lab[..., 2].copy()


@dataclass
class Prep:
    L: np.ndarray
    a: np.ndarray
    b: np.ndarray
    usable: np.ndarray
    clipped: np.ndarray
    dark: np.ndarray


def prep(rgb, median=5, dark_L=8.0, clip=0.98):
    L, a, b = to_lab(rgb)
    if median:
        a = cv2.medianBlur(a, median)
        b = cv2.medianBlur(b, median)
    clipped = (rgb >= clip).any(axis=2)
    clipped = cv2.dilate(clipped.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    dark = L < dark_L
    return Prep(L, a, b, ~clipped & ~dark, clipped, dark)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


@dataclass
class Result:
    name: str
    alpha: np.ndarray                  # presence opacity 0-1 (shown where >= 0.5)
    va: Optional[np.ndarray] = None    # departure vector, a*
    vb: Optional[np.ndarray] = None
    z: Optional[np.ndarray] = None
    ref_fn: Optional[object] = None    # L -> (a, b), for the strip
    warnings: List[str] = field(default_factory=list)
    info: Dict = field(default_factory=dict)


# ---- M0 / M1: the v4.1.2 script's own feature and thresholds --------------------------------------------------------

_V412 = None


def v412():
    global _V412
    if _V412 is None:
        spec = importlib.util.spec_from_file_location("hpv_412", HERE / "hpv_412.py")
        mod = importlib.util.module_from_spec(spec)
        import sys
        sys.modules["hpv_412"] = mod
        spec.loader.exec_module(mod)
        tmp = HERE / "_v412_io"
        (tmp / "in").mkdir(parents=True, exist_ok=True)
        cfg = mod.VisualizerConfig(input_dir=tmp / "in", output_dir=tmp / "out")
        _V412 = (mod, mod.ImageProcessor(cfg))
    return _V412


def m0_m1(rgb):
    mod, proc = v412()
    lab = mod._custom_rgb_to_lab(rgb.astype(np.float32), "sRGB")
    chroma = proc._chroma_from_lab(lab)
    lrc, _ = proc._compute_lrc(lab, chroma)
    out = []
    for space, feat in (("raw", chroma), ("lrc", lrc)):
        thr, alpha, binary, metrics = proc._threshold_and_map(feat, space)
        # the 4.1.2 tiers give 0.4 / 0.8 / 1.0; 'shown' is any opacity at all in its picture, but for a like-for-like
        # count we take alpha >= 0.4 (the faint tier fully on) as 'shown'
        out.append(Result("M0 v4.1.2 C*ab" if space == "raw" else "M1 v4.1.2 LRC", alpha=np.clip(alpha / 0.4, 0, 1) * 1.0,
                          info={"threshold": thr}))
    return out


# ---- M2: TODO.md's automatic fallback -------------------------------------------------------------------------------

def _band_index(L, bw):
    nb = int(math.ceil(100.0 / bw))
    return np.clip((L / bw).astype(np.int32), 0, nb - 1), nb


def _interp_bands(vals, ok):
    x = np.arange(len(vals))
    if not ok.any():
        return np.zeros_like(vals)
    return np.interp(x, x[ok], vals[ok])


def _smooth_bands(v, k=5):
    from scipy.ndimage import median_filter, uniform_filter1d
    return uniform_filter1d(median_filter(v, size=k, mode="nearest"), 3, mode="nearest")


def _at_L(curve, L, bw):
    f = L / bw - 0.5
    lo = np.clip(np.floor(f).astype(np.int32), 0, len(curve) - 1)
    hi = np.clip(lo + 1, 0, len(curve) - 1)
    t = np.clip(f - lo, 0, 1)
    return curve[lo] * (1 - t) + curve[hi] * t


def m2_todo(p: Prep, bw=2.0, rounds=4, zcut=3.0, plane=False, lo=2.0, hi=5.0, min_px=50, floor=0.75, name=None,
            mask=None):
    H, W = p.L.shape
    idx, nb = _band_index(p.L, bw)
    use = p.usable if mask is None else (p.usable & mask)
    keep = use.copy()
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    u, v = xx / W - 0.5, yy / H - 0.5
    pa = np.zeros((H, W), np.float32)
    pb = np.zeros((H, W), np.float32)
    for _ in range(rounds):
        aa, bb = p.a - pa, p.b - pb
        flat = idx[keep]
        cnt = np.bincount(flat, minlength=nb)
        ma = np.full(nb, np.nan, np.float32)
        mb = np.full(nb, np.nan, np.float32)
        sp = np.full(nb, np.nan, np.float32)
        A, B = aa[keep], bb[keep]
        order = np.argsort(flat, kind="stable")
        bounds = np.searchsorted(flat[order], np.arange(nb + 1))
        for k in range(nb):
            if cnt[k] < min_px:
                continue
            sel = order[bounds[k]:bounds[k + 1]]
            ma[k] = np.median(A[sel])
            mb[k] = np.median(B[sel])
            d = np.hypot(A[sel] - ma[k], B[sel] - mb[k])
            sp[k] = np.median(d) / 1.1774
        ok = np.isfinite(ma)
        ma, mb, sp = _interp_bands(ma, ok), _interp_bands(mb, ok), _interp_bands(sp, ok)
        ma, mb = _smooth_bands(ma), _smooth_bands(mb)
        sp = np.maximum(_smooth_bands(sp), floor)
        ra, rb, s = _at_L(ma, p.L, bw), _at_L(mb, p.L, bw), _at_L(sp, p.L, bw)
        va, vb = p.a - pa - ra, p.b - pb - rb
        z = np.hypot(va, vb) / s
        inl = use & (z < zcut)
        if plane:
            Xd = np.stack([np.ones(inl.sum()), u[inl], v[inl]], 1)
            ca = np.linalg.lstsq(Xd, (p.a - ra)[inl], rcond=None)[0]
            cb = np.linalg.lstsq(Xd, (p.b - rb)[inl], rcond=None)[0]
            pa = (ca[0] + ca[1] * u + ca[2] * v).astype(np.float32)
            pb = (cb[0] + cb[1] * u + cb[2] * v).astype(np.float32)
        keep = inl
    z = cv2.medianBlur(np.ascontiguousarray(z, np.float32), 5)
    alpha = smoothstep(lo, hi, z) * use
    Lg = np.arange(nb) * bw + bw / 2
    return Result(name or ("M2p TODO + plane" if plane else "M2 TODO fallback"), alpha=alpha, va=va, vb=vb, z=z,
                  ref_fn=lambda L: (np.interp(L, Lg, ma), np.interp(L, Lg, mb)),
                  info={"plane": plane})


# ---- M3: proposed ---------------------------------------------------------------------------------------------------

def _peaks_2d(A, B, max_peaks=3, binw=0.5, span=40.0, sigma_bins=2.0, min_frac=0.08, radius=3.0):
    """Up to max_peaks density peaks of the (a*, b*) cloud: (centre, mass fraction within radius), heaviest first."""
    ca, cb = np.median(A), np.median(B)
    lo_a, lo_b = ca - span, cb - span
    nbins = int(2 * span / binw)
    ia = np.clip(((A - lo_a) / binw).astype(np.int32), 0, nbins - 1)
    ib = np.clip(((B - lo_b) / binw).astype(np.int32), 0, nbins - 1)
    h = np.zeros((nbins, nbins), np.float32)
    np.add.at(h, (ia, ib), 1.0)
    h = cv2.GaussianBlur(h, (0, 0), sigma_bins)
    mx = cv2.dilate(h, np.ones((7, 7), np.uint8))
    cand = np.argwhere((h >= mx) & (h > 0))
    vals = h[cand[:, 0], cand[:, 1]]
    order = np.argsort(-vals)
    out = []
    n = len(A)
    for i in order[: max_peaks * 4]:
        pa_ = lo_a + (cand[i, 0] + 0.5) * binw
        pb_ = lo_b + (cand[i, 1] + 0.5) * binw
        for _ in range(4):                                   # mean shift
            d = np.hypot(A - pa_, B - pb_)
            m = d < radius
            if m.sum() < 5:
                break
            pa_, pb_ = A[m].mean(), B[m].mean()
        d = np.hypot(A - pa_, B - pb_)
        frac = float((d < radius).mean())
        if frac < min_frac:
            continue
        if any(math.hypot(pa_ - q[0], pb_ - q[1]) < radius for q in out):
            continue
        out.append((pa_, pb_, frac))
        if len(out) >= max_peaks:
            break
    if not out:
        out.append((float(np.median(A)), float(np.median(B)), 1.0))
    return out


def _spread_about(A, B, ca, cb, frac):
    d = np.hypot(A - ca, B - cb)
    q = max(min(frac, 1.0) * 0.5, 0.02)                     # the median of the cluster's own distances
    return float(np.quantile(d, q)) / 1.1774


def _poly(Lc, deg):
    u = (np.asarray(Lc, np.float64) - 50.0) / 50.0
    return np.stack([u ** k for k in range(deg + 1)], -1)


@dataclass
class Bands:
    Lc: np.ndarray
    n: np.ndarray
    peaks: List[List[tuple]]


def tone_bands(L, A, B, mask, bw=2.0, min_px=150, max_px=6000, seed=0):
    rng = np.random.default_rng(seed)
    idx, nb = _band_index(L, bw)
    Lc, n, peaks = [], [], []
    li, la, lb = idx[mask], A[mask], B[mask]
    order = np.argsort(li, kind="stable")
    bounds = np.searchsorted(li[order], np.arange(nb + 1))
    for k in range(nb):
        sel = order[bounds[k]:bounds[k + 1]]
        if len(sel) < min_px:
            continue
        if len(sel) > max_px:
            sel = rng.choice(sel, max_px, replace=False)
        pk = _peaks_2d(la[sel], lb[sel])
        pk = [(pa_, pb_, fr, _spread_about(la[sel], lb[sel], pa_, pb_, fr)) for pa_, pb_, fr in pk]
        Lc.append((k + 0.5) * bw)
        n.append(bounds[k + 1] - bounds[k])
        peaks.append(pk)
    return Bands(np.array(Lc), np.array(n, float), peaks)


def fit_curve(bands: Bands, anchor=None, deg=2, tol=2.5, floor=0.8, trials=2500, seed=0):
    """Consensus tone curve through one peak per band.  anchor: (L, a, b, s, weight) or None.
    Returns coef_a, coef_b, chosen peak per band (or None), score share."""
    rng = np.random.default_rng(seed)
    K = len(bands.Lc)
    w = np.sqrt(bands.n)
    total = w.sum()
    P = _poly(bands.Lc, deg)
    # flatten candidates
    cand = [(k, j) for k in range(K) for j in range(len(bands.peaks[k]))]
    cw = np.array([bands.peaks[k][j][2] for k, j in cand])

    def score(ca, cb):
        ga, gb = P @ ca, P @ cb
        sc = 0.0
        pick = [None] * K
        for k in range(K):
            best = None
            for j, (pa_, pb_, fr, s) in enumerate(bands.peaks[k]):
                d = math.hypot(pa_ - ga[k], pb_ - gb[k]) / max(s, floor)
                if d < tol and (best is None or fr > bands.peaks[k][best][2]):
                    best = j
            if best is not None:
                pick[k] = best
                sc += w[k] * math.sqrt(bands.peaks[k][best][2])
        if anchor is not None:
            La, aa, ab, s_, wt = anchor
            ua = _poly([La], deg)[0]
            if math.hypot(ua @ ca - aa, ua @ cb - ab) / max(s_, floor) < tol:
                sc += wt * total
        return sc, pick

    best = (-1.0, None, None, None)
    if K < deg + 1:
        raise ValueError("too few tone bands")
    for _ in range(trials):
        ks = rng.choice(K, deg + 1, replace=False)
        rows, ya, yb = [], [], []
        for k in ks:
            pk = bands.peaks[k]
            pr = np.array([q[2] for q in pk]); pr = pr / pr.sum()
            j = rng.choice(len(pk), p=pr)
            rows.append(P[k]); ya.append(pk[j][0]); yb.append(pk[j][1])
        M = np.array(rows)
        if abs(np.linalg.det(M)) < 1e-9:
            continue
        ca, cb = np.linalg.solve(M, ya), np.linalg.solve(M, yb)
        sc, pick = score(ca, cb)
        if sc > best[0]:
            best = (sc, ca, cb, pick)
    sc, ca, cb, pick = best
    # Tukey refit on the chosen peaks (and the anchor)
    for _ in range(5):
        rows, ya, yb, ww = [], [], [], []
        ga, gb = P @ ca, P @ cb
        for k in range(K):
            if pick[k] is None:
                continue
            pa_, pb_, fr, s = bands.peaks[k][pick[k]]
            r = math.hypot(pa_ - ga[k], pb_ - gb[k]) / max(s, floor) / 4.685
            if r >= 1:
                continue
            rows.append(P[k]); ya.append(pa_); yb.append(pb_)
            ww.append(w[k] * math.sqrt(fr) * (1 - r * r) ** 2)
        if anchor is not None:
            La, aa, ab, s_, wt = anchor
            rows.append(_poly([La], deg)[0]); ya.append(aa); yb.append(ab); ww.append(wt * total * 0.5)
        if len(rows) < deg + 1:
            break
        Wt = np.sqrt(np.array(ww))[:, None]
        M = np.array(rows) * Wt
        ca = np.linalg.lstsq(M, np.array(ya) * Wt[:, 0], rcond=None)[0]
        cb = np.linalg.lstsq(M, np.array(yb) * Wt[:, 0], rcond=None)[0]
        sc, pick = score(ca, cb)
    share = sc / (total * (1 + (anchor[4] if anchor is not None else 0)))
    return ca, cb, pick, share


def _robust_plane(X, y, iters=8):
    """Huber-weighted least squares (scale from the MAD), for a cast measured on paper."""
    w = np.ones(len(y))
    c = np.linalg.lstsq(X, y, rcond=None)[0]
    for _ in range(iters):
        r = y - X @ c
        s = 1.4826 * np.median(np.abs(r - np.median(r))) + 1e-6
        t = np.abs(r) / (1.345 * s)
        w = np.where(t <= 1, 1.0, 1.0 / t)
        sw = np.sqrt(w)
        c = np.linalg.lstsq(X * sw[:, None], y * sw, rcond=None)[0]
    return c


def paper_anchor(p: Prep, frac=0.02, mask=None):
    """The brightest usable pixels ('white patch'): taken as unpainted paper.  Returns (anchor tuple, paper mask): the
    paper mask also holds every pixel near the anchor in lightness and colour (the border ring, when there is one)."""
    use = p.usable if mask is None else (p.usable & mask)
    Lu = p.L[use]
    if Lu.size < 1000:
        return None, np.zeros_like(p.usable)
    cut = np.quantile(Lu, 1 - frac)
    m = use & (p.L >= cut)
    A, B = p.a[m], p.b[m]
    ca, cb = float(np.median(A)), float(np.median(B))
    s = float(np.median(np.hypot(A - ca, B - cb)) / 1.1774)
    Lp = float(np.median(p.L[m]))
    paper = use & (p.L >= Lp - 6) & (np.hypot(p.a - ca, p.b - cb) < max(4 * s, 3.0))
    return (Lp, ca, cb, s, 0.25), paper


def m3_proposed(p: Prep, anchor=True, ring_plane=False, deg=2, lo=2.5, hi=5.0, floor=0.8, name=None, seed=0,
                diagnostics=True, mask=None):
    H, W = p.L.shape
    use = p.usable if mask is None else (p.usable & mask)
    anc, amask = paper_anchor(p, mask=mask) if anchor else (None, np.zeros_like(p.usable))
    pa = np.zeros((H, W), np.float32)
    pb = np.zeros((H, W), np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    u, v = xx / W - 0.5, yy / H - 0.5
    warnings = []
    if ring_plane and anc is not None:
        # a cast plane from the paper alone (bright, smooth, near the anchor's lightness; colour loosely), and only if
        # that paper surrounds the picture: it cannot hold paint, so the plane cannot take paint into the reference
        Lp_ = anc[0]
        mu = cv2.blur(p.L, (9, 9)); sd = np.sqrt(np.maximum(cv2.blur(p.L * p.L, (9, 9)) - mu * mu, 0))
        amask = use & (p.L >= Lp_ - 8) & (sd < 2.5) & (np.hypot(p.a - anc[1], p.b - anc[2]) < 15)
        ys, xs = np.nonzero(amask)
        spread_x = (np.quantile(xs, 0.9) - np.quantile(xs, 0.1)) / W
        spread_y = (np.quantile(ys, 0.9) - np.quantile(ys, 0.1)) / H
        if spread_x > 0.5 and spread_y > 0.5:
            Xd = np.stack([np.ones(len(xs)), u[amask], v[amask]], 1)
            ca_ = _robust_plane(Xd, p.a[amask])
            cb_ = _robust_plane(Xd, p.b[amask])
            k_ = (p.L + 16.0) / (Lp_ + 16.0)              # a cast's a*b* shift shrinks towards black (cube root)
            pa = ((ca_[1] * u + ca_[2] * v) * k_).astype(np.float32)
            pb = ((cb_[1] * u + cb_[2] * v) * k_).astype(np.float32)
            for nm, i in (("left to right", 1), ("top to bottom", 2)):
                if math.hypot(ca_[i], cb_[i]) > 2.5:     # change across the frame, on the paper itself
                    warnings.append(f"the paper border changes colour {nm}: the light was uneven; allowed for as "
                                    "measured on the paper")
        else:
            warnings.append("no paper around the picture to measure the light by: no cast correction")
    A, B = p.a - pa, p.b - pb
    bands = tone_bands(p.L, A, B, use, seed=seed)
    ca, cb, pick, share = fit_curve(bands, anchor=anc, deg=deg, floor=floor, seed=seed)
    # spread curve from the chosen peaks
    Ls = [bands.Lc[k] for k in range(len(bands.Lc)) if pick[k] is not None]
    ss = [bands.peaks[k][pick[k]][3] for k in range(len(bands.Lc)) if pick[k] is not None]
    if len(Ls) >= 2:
        from scipy.ndimage import median_filter
        ss = median_filter(np.array(ss), size=5, mode="nearest")
        s_at = lambda L: np.maximum(np.interp(L, Ls, ss), floor)
    else:
        s_at = lambda L: np.full_like(L, 2.0)

    def ref(L):
        Pm = _poly(np.ravel(L), deg)
        return (Pm @ ca).reshape(np.shape(L)), (Pm @ cb).reshape(np.shape(L))
    ra, rb = ref(p.L)
    va, vb = A - ra, B - rb
    s = s_at(p.L)
    z = np.hypot(va, vb) / s
    z = cv2.medianBlur(np.ascontiguousarray(z, np.float32), 5)
    alpha = smoothstep(lo, hi, z) * use
    info = {"bands_obj": bands, "coef": (ca, cb), "deg": deg, "anchor_t": anc, "share": share, "bands": len(bands.Lc), "agree": int(sum(k is not None for k in pick)),
            "anchor": anc is not None, "pick": pick, "Lc": bands.Lc}
    res = Result(name or ("M3 proposed" + (" + ring cast" if ring_plane else "") + ("" if anchor else " (no anchor)")),
                 alpha=alpha, va=va, vb=vb, z=z, ref_fn=ref, warnings=warnings, info=info)
    res.info["anchor_mask"] = amask
    amb = ambiguous_bands(bands, pick, anc, deg, floor)
    res.info["ambiguous_L"] = [float(bands.Lc[k]) for k in range(len(amb)) if amb[k]]
    idx_, _ = _band_index(p.L, 2.0)
    amb_px = np.zeros_like(use)
    for k in range(len(amb)):
        if amb[k]:
            amb_px |= use & (idx_ == int(bands.Lc[k] // 2.0))
    res.info["cant_tell"] = amb_px & (res.alpha < 0.5)
    res.info["unsure_colour"] = amb_px & (res.alpha >= 0.5)
    if diagnostics:
        diagnose(p, res, bands, pick, anc, deg, floor, seed, use)
    return res


def _wls_curve(bands, pick, keep, anc, deg, floor):
    rows, ya, yb, ww = [], [], [], []
    P = _poly(bands.Lc, deg)
    for k in range(len(bands.Lc)):
        if pick[k] is None or not keep[k]:
            continue
        pa_, pb_, fr, s = bands.peaks[k][pick[k]]
        rows.append(P[k]); ya.append(pa_); yb.append(pb_); ww.append(math.sqrt(bands.n[k]) * math.sqrt(fr))
    if anc is not None:
        rows.append(_poly([anc[0]], deg)[0]); ya.append(anc[1]); yb.append(anc[2])
        ww.append(0.25 * float(np.sqrt(bands.n).sum()))
    if len(rows) < deg + 1:
        return None
    Wt = np.sqrt(np.array(ww))[:, None]
    M_ = np.array(rows) * Wt
    return (np.linalg.lstsq(M_, np.array(ya) * Wt[:, 0], rcond=None)[0],
            np.linalg.lstsq(M_, np.array(yb) * Wt[:, 0], rcond=None)[0])


def ambiguous_bands(bands, pick, anc, deg, floor, window=12.0, k_sd=3.0):
    """A tone is ambiguous when the colour the curve took there as unpainted is not what the other tones predict:
    refit without the tones within +-window L* and compare.  The photograph alone cannot say whether such a tone is
    the print's own colour or a wash over everything of that tone."""
    K = len(bands.Lc)
    out = np.zeros(K, bool)
    for k in range(K):
        if pick[k] is None:
            continue
        keep = np.abs(bands.Lc - bands.Lc[k]) > window
        c = _wls_curve(bands, pick, keep, anc, deg, floor)
        if c is None:
            continue
        pr = _poly([bands.Lc[k]], deg)[0]
        pa_, pb_, fr, s = bands.peaks[k][pick[k]]
        d = math.hypot(pr @ c[0] - pa_, pr @ c[1] - pb_) / max(s, floor)
        out[k] = d > k_sd
    return out


# ---- diagnostics: when has the reference gone wrong? ------------------------------------------------------------------

def _curve_only(p, use, anc, deg, floor, seed):
    bands = tone_bands(p.L, p.a, p.b, use, seed=seed, min_px=100)
    if len(bands.Lc) < deg + 2:
        return None
    ca, cb, pick, share = fit_curve(bands, anchor=anc, deg=deg, floor=floor, seed=seed, trials=1200)
    lo_, hi_ = np.quantile(p.L[use], [0.05, 0.95])
    return ca, cb, (lo_, hi_)


def diagnose(p: Prep, res: Result, bands: Bands, pick, anc, deg, floor, seed, use):
    H, W = p.L.shape
    w = res.warnings
    shown = res.alpha >= 0.5
    # D1: how much of the photograph sits on the curve at all
    on_curve = (res.z < 2.0) & use
    share_unpainted = on_curve.sum() / max(use.sum(), 1)
    res.info["share_on_curve"] = float(share_unpainted)
    if share_unpainted < 0.35:
        w.append("most of the photograph carries colour: the unpainted tone is a guess; compare with the original")
    # D2: the tones that agree should span the range
    Lc = bands.Lc
    agree = np.array([k is not None for k in pick])
    if agree.any():
        span = (Lc[agree].max() - Lc[agree].min()) / max(Lc.max() - Lc.min(), 1e-6)
        res.info["agree_span"] = float(span)
        if span < 0.5:
            w.append("the unpainted tone was found in only part of the tonal range; elsewhere it is extended")
    # D3: split halves: does the unpainted tone differ left to right, or top to bottom?
    s_mid = 1.5
    for name, m1, m2 in (("left to right", np.s_[:, : W // 2], np.s_[:, W // 2:]),
                         ("top to bottom", np.s_[: H // 2, :], np.s_[H // 2:, :])):
        u1 = np.zeros_like(use); u1[m1] = True
        u2 = np.zeros_like(use); u2[m2] = True
        c1 = _curve_only(p, use & u1, anc, deg, floor, seed)
        c2 = _curve_only(p, use & u2, anc, deg, floor, seed)
        if c1 is None or c2 is None:
            continue
        lo_ = max(c1[2][0], c2[2][0]); hi_ = min(c1[2][1], c2[2][1])
        if hi_ <= lo_:
            continue
        Lg = np.linspace(lo_, hi_, 25)
        Pm = _poly(Lg, deg)
        d = np.hypot(Pm @ c1[0] - Pm @ c2[0], Pm @ c1[1] - Pm @ c2[1])
        res.info[f"split_{name}"] = float(np.median(d))
        if np.median(d) > 2.0:
            # a localised wash makes the halves disagree just as uneven light does: say both
            w.append(f"the two halves disagree about the unpainted tone ({name}): uneven light, or paint mostly on "
                     "one side")
    # D4: colour that covers most of one tone (paint follows objects; a wrong reference follows tone)
    idx, nb = _band_index(p.L, 2.0)
    for k in np.unique(idx[use]):
        inb = use & (idx == k)
        n = inb.sum()
        if n < 0.03 * use.sum():
            continue
        f = (shown & inb).sum() / n
        if f > 0.6:
            tone = "light" if k * 2 > 66 else ("mid" if k * 2 > 33 else "dark")
            msg = f"colour covers most of the {tone} greys: compare with the original; it may be the print's own tone"
            if msg not in w:
                w.append(msg)
