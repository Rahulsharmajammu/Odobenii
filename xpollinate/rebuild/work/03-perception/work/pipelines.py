"""The pipelines compared.

* v412_raw / v412_lrc: the visualiser's own functions (Chroma_diagnoser_v4.1, version 4.1.2), loaded read-only from
  the repository and called on the decoded capture: C*ab or LRC, the noise_floor threshold, the three tiers and the
  100 px component filter.
* todo: TODO.md's pipeline as written (automatic reference): CIELAB, 5 px median on a* b*, glare and near-black left
  out, per-L*-band median (a*, b*) smoothed along L*, refitted a few rounds without far pixels, the vector to it in
  units of the band's robust spread, a small median on the length, opacity rising from 2 to 5 spreads.
* proposed: the design in the report (reference as a robust function of lightness and position; departures in units
  of the substrate's own spread at several spatial scales; pictures).
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import sys
from pathlib import Path

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter, binary_dilation, median_filter

import colour as C

REPO = Path("/home/user/handpaint_visualiser/Chroma_diagnoser_v4.1")
WORK = Path(__file__).resolve().parent

_v412 = None
_proc = None


def v412():
    global _v412, _proc
    if _v412 is None:
        loader = importlib.machinery.SourceFileLoader("chroma_v412", str(REPO))
        spec = importlib.util.spec_from_loader("chroma_v412", loader)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["chroma_v412"] = mod
        loader.exec_module(mod)
        (WORK / "v412_in").mkdir(exist_ok=True)
        cfg = mod.VisualizerConfig(input_dir=WORK / "v412_in", output_dir=WORK / "v412_out")
        _v412, _proc = mod, mod.ImageProcessor(cfg)
    return _v412, _proc


def run_v412(img8, space="raw"):
    mod, proc = v412()
    rgb = img8.astype(np.float32) / 255.0
    lab = mod._custom_rgb_to_lab(rgb, "sRGB")
    chroma = proc._chroma_from_lab(lab)
    if space == "lrc":
        feat, _ = proc._compute_lrc(lab, chroma)
    else:
        feat = chroma
    thr, alpha, binary, metrics = proc._threshold_and_map(feat, space)
    return {"score": feat, "opacity": alpha.astype(np.float32), "valid": np.ones(feat.shape, bool),
            "threshold": thr, "binary": binary}


# -- shared helpers -------------------------------------------------------------------------------------------------

def lab_of(img8):
    return C.srgb8_to_lab(img8)


def smooth_ab(lab, k=5):
    ab = np.ascontiguousarray(lab[..., 1:3])
    return np.stack([cv2.medianBlur(np.ascontiguousarray(ab[..., i]), k) for i in range(2)], -1)


def leave_out(img8, L, near_black=5.0, dilate=3, near_white=244.0, near_white_sigma=2.0):
    """Pixels whose colour cannot be judged: clipped in any channel (dilated), near white in any channel on a local
    mean (pixels that escape the clip in a mostly clipped area are the ones whose noise read low in that channel, so
    their colour is biased: paper reads tinted), and near black."""
    clipped = (img8 >= 250).any(axis=2)
    if dilate:
        clipped = binary_dilation(clipped, iterations=dilate)
    out = clipped | (L < near_black)
    if near_white:
        top = gaussian_filter(img8.max(axis=2).astype(np.float32), near_white_sigma)
        out |= top >= near_white
    return out


def smoothstep(x, lo, hi):
    t = np.clip((x - lo) / (hi - lo), 0, 1)
    return (t * t * (3 - 2 * t)).astype(np.float32)


# -- TODO.md as written -----------------------------------------------------------------------------------------------

def run_todo(img8, band=2.0, rounds=4, far=3.0, smooth_bands=5):
    lab = lab_of(img8)
    L = lab[..., 0]
    ab = smooth_ab(lab, 5)
    out = leave_out(img8, L)
    valid = ~out
    nb = int(np.ceil(100 / band))
    idx = np.clip((L / band).astype(int), 0, nb - 1)
    keep = valid.copy()
    for _ in range(rounds):
        med = np.full((nb, 2), np.nan, np.float32)
        spr = np.full(nb, np.nan, np.float32)
        for b in range(nb):
            sel = keep & (idx == b)
            if sel.sum() < 30:
                continue
            v = ab[sel]
            m = np.median(v, axis=0)
            med[b] = m
            spr[b] = np.median(np.linalg.norm(v - m, axis=1)) / 1.1774
        ok = np.isfinite(spr)
        x = np.arange(nb)
        for c in range(2):
            med[:, c] = np.interp(x, x[ok], med[ok, c])
        spr = np.interp(x, x[ok], spr[ok])
        k = np.ones(smooth_bands) / smooth_bands
        pad = smooth_bands // 2
        med = np.stack([np.convolve(np.pad(med[:, c], pad, mode="edge"), k, "valid") for c in range(2)], -1)
        spr = np.maximum(np.convolve(np.pad(spr, pad, mode="edge"), k, "valid"), 0.3)
        ref = med[idx]
        length = np.linalg.norm(ab - ref, axis=-1) / spr[idx]
        keep = valid & (length <= far)
    length = median_filter(length, 3)
    length[out] = 0
    return {"score": length.astype(np.float32), "opacity": smoothstep(length, 2.0, 5.0) * valid,
            "valid": valid, "ref": ref, "ab": ab, "L": L}


# -- proposed -------------------------------------------------------------------------------------------------------

def hat_basis(x, knots):
    """Piecewise-linear B-spline (hat) basis on ``knots``, (n, K)."""
    x = np.clip(x, knots[0], knots[-1])
    K = len(knots)
    B = np.zeros((x.size, K), np.float32)
    j = np.clip(np.searchsorted(knots, x, side="right") - 1, 0, K - 2)
    t = (x - knots[j]) / (knots[j + 1] - knots[j])
    B[np.arange(x.size), j] = 1 - t
    B[np.arange(x.size), j + 1] = t
    return B


def design(Lidx, xn, yn, knots, spatial, cast_scaled=False):
    """Columns: the lightness curve's hat basis, then the position terms.

    spatial: 0 none; 1 a plane in x and y; 2 a quadratic; 3 a plane whose tilt also changes linearly with lightness
    (x, y, x L~, y L~ with L~ = (L* - 60) / 40): uneven light moves a pixel's captured lightness, so a reference indexed
    by captured lightness errs in proportion to how fast the print's own tone changes with lightness; 4 the quadratic
    plus the lightness-dependent tilt.  ``cast_scaled``: position terms multiplied by (L* + 16) / 116, because in
    CIELAB a multiplicative colour cast shifts a* b* in proportion to the cube root of luminance; in log chromaticity
    a cast is additive and needs no scaling."""
    B = hat_basis(Lidx.ravel(), knots)
    cols = [B]
    Lr = Lidx.ravel()[:, None]
    g = (Lr + 16) / 116 if cast_scaled else 1.0
    x, y = xn.ravel()[:, None], yn.ravel()[:, None]
    lt = (Lr - 60.0) / 40.0
    if spatial >= 1:
        cols += [x * g, y * g]
    if spatial in (2, 4):
        cols += [(x * x - 1 / 3) * g, x * y * g, (y * y - 1 / 3) * g]
    if spatial in (3, 4):
        cols += [x * lt * g, y * lt * g]
    return np.concatenate(cols, 1).astype(np.float32)


def ref_at(Lq, xn, yn, beta, knots, spatial, cast_scaled=False):
    """The fitted reference at lightness ``Lq`` and position, without building the design matrix (the curve is a
    piecewise-linear interpolation on its knots; the position terms are linear)."""
    K = len(knots)
    out = np.stack([np.interp(Lq, knots, beta[:K, i]) for i in range(2)], -1).astype(np.float32)
    g = ((Lq + 16) / 116)[..., None] if cast_scaled else 1.0
    lt = ((Lq - 60.0) / 40.0)[..., None]
    k = K
    x, y = xn[..., None], yn[..., None]
    if spatial >= 1:
        out += (x * beta[k] + y * beta[k + 1]) * g
        k += 2
    if spatial in (2, 4):
        out += ((x * x - 1 / 3) * beta[k] + x * y * beta[k + 1] + (y * y - 1 / 3) * beta[k + 2]) * g
        k += 3
    if spatial in (3, 4):
        out += (x * lt * beta[k] + y * lt * beta[k + 1]) * g
    return out


def tolerant_residual(L, ab, xn, yn, beta, knots, spatial, cast_scaled, size=5, steps=5, Lsmooth=None):
    """The departure from the reference that no lightness found within ``size`` x ``size`` px explains: the smallest
    residual over lightness values spanning the window's range (and the smoothed lightness).  Chroma that lags
    lightness by a pixel or two at a sharp edge (4:2:0 subsampling, chroma noise reduction, sharpening) is then not
    taken for paint, whatever the capture did; a departure across the reference's own direction still counts."""
    from scipy.ndimage import minimum_filter, maximum_filter
    lo, hi = minimum_filter(L, size), maximum_filter(L, size)
    cands = [lo + (hi - lo) * f for f in np.linspace(0, 1, steps)] + [L] + ([Lsmooth] if Lsmooth is not None else [])
    best = None
    bestn = None
    for Lc in cands:
        r = ab - ref_at(Lc, xn, yn, beta, knots, spatial, cast_scaled)
        n = np.linalg.norm(r, axis=-1)
        if best is None:
            best, bestn = r, n
        else:
            take = n < bestn
            best = np.where(take[..., None], r, best)
            bestn = np.where(take, n, bestn)
    return best.astype(np.float32)


def band_spread(L, r, w, edges, min_px=150, floor=0.35, wmin=0.0):
    """Robust spread of the 2-D residual about the reference in each lightness band (median |r| / sqrt(2 ln 2)),
    from pixels weighted as substrate; bands with too few pixels interpolated."""
    nb = len(edges) - 1
    s = np.full(nb, np.nan, np.float32)
    n = np.zeros(nb, int)
    idx = np.clip(np.searchsorted(edges, L, side="right") - 1, 0, nb - 1)
    rr = np.linalg.norm(r, axis=-1)
    for b in range(nb):
        sel = (idx == b) & (w > wmin)
        n[b] = int(sel.sum())
        if n[b] >= min_px:
            s[b] = np.median(rr[sel]) / 1.1774
    ok = np.isfinite(s)
    if not ok.any():
        return np.full(nb, 1.0, np.float32), n
    x = np.arange(nb)
    s = np.interp(x, x[ok], s[ok])
    s = np.maximum(median_filter(s, 3, mode="nearest"), floor)
    return s.astype(np.float32), n


def fit_reference(L, ab, valid, picks=None, spatial=1, knot_step=4.0, lam=0.05, iters=10, c=3.5,
                  sample=250_000, seed=0, l_index_sigma=1.5, cast_scaled=False, floor=0.35, tolerant=True):
    """The unpainted photograph's colour as a function of lightness and position, robustly.

    ref(L, x, y) = c(L) + s(x, y): c a penalised piecewise-linear curve in lightness (knots every ``knot_step`` L*),
    s a plane (spatial=1) or quadratic (2) in position, none (0).  Fitted by iteratively reweighted least squares with
    Tukey's biweight on the 2-D residual in units of the band's robust spread, from a start at the band medians.
    ``picks``: a boolean mask of areas the user says are unpainted (weight x20, never down-weighted).
    Lightness is indexed after smoothing to the chroma's resolution (``l_index_sigma``), so JPEG's half-resolution
    chroma is compared with lightness at the same resolution.
    """
    h, w = L.shape
    Li = gaussian_filter(L, l_index_sigma) if l_index_sigma else L
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    xn, yn = 2 * xx / (w - 1) - 1, 2 * yy / (h - 1) - 1
    knots = np.arange(0.0, 100.0 + knot_step, knot_step, dtype=np.float32)
    edges = knots
    rng = np.random.default_rng(seed)
    pool = np.flatnonzero(valid.ravel())
    pk = np.zeros(h * w, bool) if picks is None else (picks.ravel() & valid.ravel())
    take = pool if pool.size <= sample else np.sort(rng.choice(pool, sample, replace=False))
    if pk.any():
        take = np.union1d(take, np.flatnonzero(pk)[:50_000])
    X = design(Li.ravel()[take], xn.ravel()[take], yn.ravel()[take], knots, spatial, cast_scaled)
    Y = ab.reshape(-1, 2)[take].astype(np.float32)
    Ls = Li.ravel()[take]
    prior = np.where(pk[take], 20.0, 1.0).astype(np.float32)
    K = len(knots)
    D = np.diff(np.eye(K, dtype=np.float32), 2, axis=0)
    P = np.zeros((X.shape[1], X.shape[1]), np.float32)
    P[:K, :K] = D.T @ D
    lam_eff = lam * len(take) / K
    # start: band medians as the curve, no spatial term
    nb = K - 1
    bidx = np.clip(np.searchsorted(edges, Ls, side="right") - 1, 0, nb - 1)
    wts = np.ones(len(take), np.float32)
    beta = None
    for it in range(iters + 1):
        if it == 0:
            med = np.full((K, 2), np.nan, np.float32)
            for k in range(K):
                sel = np.abs(Ls - knots[k]) <= knot_step
                if sel.sum() > 20:
                    med[k] = np.median(Y[sel], axis=0)
            ok = np.isfinite(med[:, 0])
            for cc in range(2):
                med[:, cc] = np.interp(knots, knots[ok], med[ok, cc])
            pred = hat_basis(Ls, knots) @ med
        else:
            WX = X * (wts * prior)[:, None]
            A = X.T @ WX + lam_eff * P
            beta = np.linalg.solve(A.astype(np.float64), (WX.T @ Y).astype(np.float64)).astype(np.float32)
            pred = X @ beta
        r = Y - pred
        s, _ = band_spread(Ls, r, np.ones(len(take)) if it == 0 else wts, edges, floor=floor)
        u = np.linalg.norm(r, axis=1) / (c * s[bidx])
        wts = np.where(u < 1, (1 - u * u) ** 2, 0.0).astype(np.float32)
        wts = np.where(pk[take], 1.0, wts)
    # everything for every pixel
    ref = ref_at(Li, xn, yn, beta, knots, spatial, cast_scaled)
    if tolerant:
        r_all = tolerant_residual(L, ab, xn, yn, beta, knots, spatial, cast_scaled, Lsmooth=Li)
    else:
        r_all = ab - ref
    rs = r_all.reshape(-1, 2)[take]
    us = np.linalg.norm(rs, axis=1) / (c * band_spread(Ls, rs, wts, edges, floor=floor)[0][bidx])
    s_all, _ = band_spread(Ls, rs, np.where(us < 1, 1.0, 0.0), edges, floor=floor)
    nbin = np.clip(np.searchsorted(edges, Li, side="right") - 1, 0, nb - 1)
    u_all = np.linalg.norm(r_all, axis=-1) / (c * s_all[nbin])
    w_all = np.where(u_all < 1, (1 - u_all ** 2) ** 2, 0.0).astype(np.float32) * valid
    # support: share of each band's valid pixels the fit kept as substrate
    support = np.zeros(nb, np.float32)
    count = np.zeros(nb, np.float32)
    for b in range(nb):
        sel = (bidx == b)
        count[b] = sel.sum()
        support[b] = (wts[sel] > 0.5).mean() if sel.any() else np.nan
    curve = beta[:K]
    return {"ref": ref.astype(np.float32), "resid": r_all.astype(np.float32), "w": w_all, "edges": edges,
            "spread": s_all, "Lidx": Li, "band": nbin, "curve": curve, "knots": knots, "beta": beta,
            "spatial": beta[K:] if spatial else None, "support": support, "count": count, "xn": xn, "yn": yn}


def multiscale(fit, valid, scales=(0.0, 2.0, 6.0, 18.0), min_px=150, floor=0.6):
    """Departure in units of the substrate's own spread at several spatial scales: the residual smoothed (normalised
    convolution over usable pixels), divided by the spread of the smoothed residual over pixels the fit kept as
    substrate, band by band.  Returns the per-scale normalised lengths and directions."""
    r = fit["resid"] * valid[..., None]
    wv = valid.astype(np.float32)
    out = []
    for s in scales:
        if s > 0:
            ws = gaussian_filter(wv, s)
            rs = np.stack([gaussian_filter(r[..., i], s) for i in range(2)], -1) / np.maximum(ws, 1e-3)[..., None]
        else:
            rs = r
        # floor: about one 8-bit code value; a camera's chroma noise reduction can flatten chroma so far that the
        # measured spread falls below what the reference can resolve, and then any misfit would read as paint
        spr, _ = band_spread(fit["Lidx"].ravel(), rs.reshape(-1, 2), fit["w"].ravel(), fit["edges"], min_px,
                             floor=floor)
        m = np.linalg.norm(rs, axis=-1) / spr[fit["band"]]
        m[~valid] = 0
        out.append({"sigma": s, "r": rs.astype(np.float32), "m": m.astype(np.float32), "spread": spr})
    # smoothing never widens a null field, so a finer scale's spread is at least the coarser one's: the coarse
    # spread carries the reference's own misfit down to the fine scales
    for k in range(len(out) - 2, -1, -1):
        sp = np.maximum(out[k]["spread"], out[k + 1]["spread"])
        if not np.array_equal(sp, out[k]["spread"]):
            m = np.linalg.norm(out[k]["r"], axis=-1) / sp[fit["band"]]
            m[~valid] = 0
            out[k]["spread"], out[k]["m"] = sp, m.astype(np.float32)
    return out


LOGC_EPS = 0.004      # linear offset that keeps log ratios finite near black


def log_chroma(img8, k=5):
    """Log chromaticity of the decoded capture, 100 x (ln(R/G), ln(B/G)), on linearised sRGB with a small offset, then
    a 5 px median: a neutral density change cancels, a colour cast or a transparent dye is an additive offset whatever
    the silver density, and a pure power-law tone curve only rescales it."""
    lin = C.srgb_decode(img8.astype(np.float32) / 255.0) + LOGC_EPS
    lg = np.log(lin)
    f = np.stack([lg[..., 0] - lg[..., 1], lg[..., 2] - lg[..., 1]], -1) * 100.0
    return np.stack([cv2.medianBlur(np.ascontiguousarray(f[..., i]).astype(np.float32), k) for i in range(2)], -1)


def presence_from_scales(ms, band, valid, lo=3.0, hi=5.5, median=5, gate=(0.75, 1.75), gate_median=5):
    """Presence from several scales without halos or hue mixing.

    The finest scale counts by itself, after a small median (thin lines along sharp edges, where half-resolution
    chroma meets full-resolution lightness, are removed; touches a few pixels across survive).  A larger scale counts
    only where the pixel's own fine-scale departure points the same way by at least about one fine spread: pooling
    finds faint washes, and the pixel's own evidence decides whether it belongs to one (so a strong patch does not
    light up a ring of unpainted pixels round it).  The hue shown is the finest scale's that stands out by itself,
    else the larger scale's."""
    fine = ms[0]
    m_f = median_filter(fine["m"], median) if median else fine["m"]
    layers = [smoothstep(m_f, lo, hi)]
    scores = [m_f]
    s_f = fine["spread"][band]
    for d in ms[1:]:
        n = np.linalg.norm(d["r"], axis=-1)
        u = d["r"] / np.maximum(n, 1e-6)[..., None]
        along = median_filter((fine["r"] * u).sum(-1), gate_median)
        proj = along / s_f
        # the pixel's own departure must stand out from noise (in fine spreads) and carry a fair share of the
        # pooled departure: in a ring round strong paint the pooled value is a diluted spill, the pixel's own ~0
        g = smoothstep(proj, *gate) * smoothstep(along / np.maximum(n, 1e-6), 0.25, 0.5)
        layers.append(smoothstep(d["m"], lo, hi) * g)
        scores.append(d["m"] * g)
    stack = np.stack(layers, 0)
    presence = stack.max(0) * valid
    score = np.stack(scores, 0).max(0) * valid
    direction = ms[-1]["r"].copy()
    for d, lay in zip(ms[::-1], layers[::-1]):          # coarse to fine: the finest that stands out wins
        direction = np.where((lay >= 0.2)[..., None], d["r"], direction)
    return presence.astype(np.float32), score.astype(np.float32), direction.astype(np.float32), stack


def run_proposed(img8, picks=None, spatial=3, scales=(2.0, 6.0, 18.0), lo=3.0, hi=5.5, l_index_sigma=1.5,
                 near_black=5.0, space="logc", cast_scaled=None, median=5, gated=True, tolerant=True, floor=None,
                 auto_position=True, cast_min=4.0, **fitkw):
    lab = lab_of(img8)
    L = lab[..., 0]
    if space == "logc":
        ab = log_chroma(img8)
        floor = 1.0 if floor is None else floor      # log-chroma units: about half an 8-bit code value at mid grey
    else:
        ab = smooth_ab(lab, 5)
        floor = 0.4 if floor is None else floor      # a* b* units: about half an 8-bit code value
    if cast_scaled is None:
        cast_scaled = space == "lab"
    out = leave_out(img8, L, near_black)
    valid = ~out
    fit = fit_reference(L, ab, valid, picks=picks, spatial=spatial, l_index_sigma=l_index_sigma,
                        cast_scaled=cast_scaled, floor=floor, tolerant=tolerant, **fitkw)
    fit["cast"] = float(np.abs(fit["beta"][len(fit["knots"]):]).max()) if spatial else 0.0
    if auto_position and spatial and fit["cast"] < cast_min:
        # no cast worth modelling: the position terms would only bend toward large painted areas
        fit = fit_reference(L, ab, valid, picks=picks, spatial=0, l_index_sigma=l_index_sigma,
                            cast_scaled=cast_scaled, floor=floor, tolerant=tolerant, **fitkw)
        fit["cast"] = 0.0
    ms = multiscale(fit, valid, scales, floor=floor)
    if gated:
        presence, score, direction, stack = presence_from_scales(ms, fit["band"], valid, lo, hi, median)
    else:
        stack = np.stack([smoothstep(d["m"], lo, hi) for d in ms], 0)
        win = np.argmax(stack, 0)
        presence = stack.max(0) * valid
        score = np.max(np.stack([d["m"] for d in ms], 0), 0)
        direction = np.zeros(L.shape + (2,), np.float32)
        for k, d in enumerate(ms):
            direction = np.where((win == k)[..., None], d["r"], direction)
    # pixels whose lightness the fit barely saw: cannot be judged
    supported = fit["count"] >= 0.002 * valid.sum()
    unsupported = ~supported[fit["band"]] & valid
    return {"score": score.astype(np.float32), "opacity": presence.astype(np.float32), "valid": valid,
            "fit": fit, "ms": ms, "lab": lab, "ab": ab, "L": L, "direction": direction, "leftout": out,
            "unsupported": unsupported, "space": space, "stack": stack}


def run_todo_fair(img8, band=2.0, rounds=4, far=3.0, smooth_bands=5, floor=0.4):
    """TODO.md as written, with one estimator fixed for a fair comparison: each band's spread is the robust spread of
    ALL its usable pixels about the band median (not of the pixels kept after the far ones are set aside, which
    shrinks it round by round), floored as in the proposed design.  This is the 'TODO.md' column of the report."""
    lab = lab_of(img8)
    L = lab[..., 0]
    ab = smooth_ab(lab, 5)
    out = leave_out(img8, L)
    valid = ~out
    nb = int(np.ceil(100 / band))
    idx = np.clip((L / band).astype(int), 0, nb - 1)
    keep = valid.copy()
    for _ in range(rounds):
        med = np.full((nb, 2), np.nan, np.float32)
        spr = np.full(nb, np.nan, np.float32)
        for b in range(nb):
            sel = keep & (idx == b)
            if sel.sum() < 30:
                continue
            med[b] = np.median(ab[sel], axis=0)
            allb = valid & (idx == b)
            spr[b] = np.median(np.linalg.norm(ab[allb] - med[b], axis=1)) / 1.1774
        ok = np.isfinite(spr)
        x = np.arange(nb)
        for c in range(2):
            med[:, c] = np.interp(x, x[ok], med[ok, c])
        spr = np.interp(x, x[ok], spr[ok])
        k = np.ones(smooth_bands) / smooth_bands
        pad = smooth_bands // 2
        med = np.stack([np.convolve(np.pad(med[:, c], pad, mode="edge"), k, "valid") for c in range(2)], -1)
        spr = np.maximum(np.convolve(np.pad(spr, pad, mode="edge"), k, "valid"), floor)
        length = np.linalg.norm(ab - med[idx], axis=-1) / spr[idx]
        keep = valid & (length <= far)
    length = median_filter(length, 3)
    length[out] = 0
    return {"score": length.astype(np.float32), "opacity": smoothstep(length, 2.0, 5.0) * valid, "valid": valid,
            "ab": ab, "ref": med[idx], "L": L}
