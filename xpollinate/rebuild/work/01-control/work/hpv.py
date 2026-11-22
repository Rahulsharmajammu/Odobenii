"""hpv: a prototype of the rebuilt handpaint visualiser.

A VISUALISER, NOT A MEASURING TOOL.  For each capture it works out what the bare (unpainted) print looks like at
each tone, and draws where the capture departs from that.  Pictures only; no areas, counts or statistics.

Pipeline (one capture):
  load -> working size -> CIELAB, a* b* smoothed -> what cannot be judged (clipped, near black, outside the print)
  -> the bare-print reference (picked boxes, else automatic) -> each pixel's departure from it, in the bare print's
  own spread -> pictures: Original | Boosted (bare print drawn neutral, departures amplified) | Where colour departs |
  Taken as bare print, with the reference's checks in words.

The reference is fitted in lightness-normalised chromaticity, (a*, b*) * 116 / (L* + 16): a colour cast from the
light, or a transparent wash, moves it by about the same amount at every tone, and shading does not move it.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageCms, ImageDraw, ImageFont, ImageOps

VERSION = "5.0.0-proto"
VIS_LABEL = "Visualisation only - not a measurement"

WORK_LONG_EDGE = 2400      # analysis size; presence does not need more
CHROMA_MEDIAN = 5          # px at the working size: JPEG 4:2:0 chroma and colour noise
CLIP = 250 / 255           # any channel at or above: clipped (glare, blown paper)
L_DARK = 8.0               # L* below: not judged (chroma is noise there)
BAND = 2.5                 # L* per band of the reference
MIN_BAND_PX = 150          # sample pixels a band needs
SAMPLE = 300_000           # pixels the reference is fitted on (seeded sample)
SPAN = 30.0                # L*: the reference curve's smoothing span (stiff: it bridges a band paint has taken)
TUKEY_C = 3.5              # spreads beyond which a pixel has no say in the reference
SIGMA_FLOOR = 0.5          # the spread is never taken as smaller (8-bit quantisation)
ITER = 8
PRESETS = {"low": (3.0, 6.0), "normal": (2.0, 5.0), "high": (1.5, 3.5)}   # opacity ramp, in spreads
BOOST = 4.0
BOOST_CMAX = 55.0
BOOST_CORE = 1.0           # a*b*: departures this small are not boosted (JPEG blocks, colour noise)


# ----------------------------------------------------------------------------------------------------------- load
def load(path: Path) -> tuple[np.ndarray, dict]:
    """Float32 sRGB in 0-1.  EXIF orientation applied; any ICC profile converted to sRGB by LittleCMS; untagged
    files taken as sRGB; 16-bit TIFF/PNG read through OpenCV (8-bit precision is plenty for a picture)."""
    info: dict = {"file": str(path)}
    with Image.open(path) as im:
        icc = im.info.get("icc_profile")
        im = ImageOps.exif_transpose(im)
        if im.mode not in ("RGB", "RGBA", "L", "LA", "P", "CMYK"):
            arr = cv2.imdecode(np.fromfile(str(path), np.uint8), cv2.IMREAD_UNCHANGED)
            if arr is None:
                raise ValueError(f"cannot read {path.name} (mode {im.mode})")
            arr = arr.astype(np.float32) / (65535.0 if arr.dtype == np.uint16 else 255.0)
            if arr.ndim == 2:
                arr = np.repeat(arr[..., None], 3, 2)
            rgb = cv2.cvtColor(arr[..., :3], cv2.COLOR_BGR2RGB)
            info["colour"] = "read by OpenCV; taken as sRGB"
            return np.clip(rgb, 0, 1), info
        im = im.convert("CMYK" if im.mode == "CMYK" else "RGB")
        if icc:
            try:
                src = ImageCms.ImageCmsProfile(io.BytesIO(icc))
                name = ImageCms.getProfileName(src).strip()
                im = ImageCms.profileToProfile(im, src, ImageCms.createProfile("sRGB"), outputMode="RGB")
                info["colour"] = f"ICC profile '{name}' converted to sRGB"
            except Exception as exc:  # noqa: BLE001
                im = im.convert("RGB")
                info["colour"] = f"ICC profile could not be applied ({exc}); taken as sRGB"
        else:
            im = im.convert("RGB")
            info["colour"] = "no profile; taken as sRGB"
        return np.asarray(im, np.float32) / 255.0, info


def to_working(rgb: np.ndarray, long_edge: int = WORK_LONG_EDGE) -> np.ndarray:
    h, w = rgb.shape[:2]
    s = long_edge / max(h, w)
    if s >= 1:
        return rgb
    return cv2.resize(rgb, (max(1, round(w * s)), max(1, round(h * s))), interpolation=cv2.INTER_AREA)


# ------------------------------------------------------------------------------------------------- colour planes
def planes(rgb: np.ndarray):
    lab = cv2.cvtColor(np.ascontiguousarray(rgb, np.float32), cv2.COLOR_RGB2LAB)
    L = lab[..., 0]
    a = cv2.medianBlur(np.ascontiguousarray(lab[..., 1]), CHROMA_MEDIAN)
    b = cv2.medianBlur(np.ascontiguousarray(lab[..., 2]), CHROMA_MEDIAN)
    k = 116.0 / (np.maximum(L, 0) + 16.0)
    u = np.stack([a * k, b * k], axis=-1).astype(np.float32)          # lightness-normalised chromaticity
    return L, a, b, u


def find_print(rgb: np.ndarray):
    """The print in a capture that also shows the table or wall around it: pixels unlike the colours along the
    frame's border, the largest roughly rectangular region of them.  None when nothing like that is found (the print
    fills the frame, or the background is like it); then the whole frame is used."""
    h, w = rgb.shape[:2]
    f = 4
    small = cv2.resize(rgb, (max(8, w // f), max(8, h // f)), interpolation=cv2.INTER_AREA)
    lab = cv2.cvtColor(np.ascontiguousarray(small, np.float32), cv2.COLOR_RGB2LAB).reshape(-1, 3)
    sh, sw = small.shape[:2]
    bw = max(2, int(0.03 * min(sh, sw)))
    ring = np.zeros((sh, sw), bool)
    ring[:bw], ring[-bw:], ring[:, :bw], ring[:, -bw:] = True, True, True, True
    border = lab[ring.ravel()].astype(np.float32)
    k = 3
    _, lbl, cen = cv2.kmeans(border, k, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.1), 3,
                             cv2.KMEANS_PP_CENTERS)
    bd = np.linalg.norm(border - cen[lbl.ravel()], axis=1)
    thr = max(8.0, 3.0 * float(np.median(bd)))
    dist = np.min(np.linalg.norm(lab[:, None, :] - cen[None, :, :], axis=2), axis=1).reshape(sh, sw)
    fg = (dist > thr).astype(np.uint8)
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, lab_cc, stats, _ = cv2.connectedComponentsWithStats(fg, connectivity=8)
    if n < 2:
        return None
    i = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    comp = (lab_cc == i).astype(np.uint8)
    cnts, _ = cv2.findContours(comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnt = max(cnts, key=cv2.contourArea)
    hull = cv2.convexHull(cnt)
    area = cv2.contourArea(hull)
    (_, (rw, rh), _) = cv2.minAreaRect(hull)
    if not (0.2 < area / (sh * sw) < 0.97) or area / max(rw * rh, 1) < 0.85:
        return None
    m = np.zeros((sh, sw), np.uint8)
    cv2.fillPoly(m, [hull], 1)
    m = cv2.erode(m, np.ones((3, 3), np.uint8))                 # keep clear of the print's own edge
    return cv2.resize(m, (w, h), interpolation=cv2.INTER_NEAREST) > 0


def judgeable(rgb, L, box=None, exclude=()):
    """What can be judged: not clipped (any channel), not near black, inside the print.  ``box``: [x0, y0, x1, y1]
    of the print, "auto" to look for it (:func:`find_print`), or None for the whole frame."""
    clipped = (rgb >= CLIP).any(axis=2)
    clipped = cv2.dilate(clipped.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    dark = L < L_DARK
    inside = np.ones(L.shape, bool)
    if isinstance(box, str) and box == "auto":
        found = find_print(rgb)
        if found is not None:
            inside = found
    elif box is not None:
        inside[:] = False
        x0, y0, x1, y1 = box
        inside[y0:y1, x0:x1] = True
    for x0, y0, x1, y1 in exclude:
        inside[y0:y1, x0:x1] = False
    return ~clipped & ~dark & inside, {"clipped": clipped & inside, "dark": dark & inside & ~clipped,
                                        "outside": ~inside}


# ------------------------------------------------------------------------------------------------ the reference
def _mode2d(v: np.ndarray, h: float) -> np.ndarray:
    """The densest point of 2-D samples (histogram peak, then mean shift with bandwidth h)."""
    lo, hi = np.percentile(v, 1, axis=0), np.percentile(v, 99, axis=0)
    bw = max(h / 2, 0.05)
    nb = np.clip(((hi - lo) / bw).astype(int) + 1, 4, 256)
    H, xe, ye = np.histogram2d(v[:, 0], v[:, 1], bins=nb, range=[[lo[0], hi[0] + 1e-6], [lo[1], hi[1] + 1e-6]])
    from scipy.ndimage import gaussian_filter
    Hs = gaussian_filter(H, 2.0)
    i, j = np.unravel_index(int(np.argmax(Hs)), Hs.shape)
    m = np.array([(xe[i] + xe[i + 1]) / 2, (ye[j] + ye[j + 1]) / 2])
    for _ in range(15):
        w = np.exp(-((v - m) ** 2).sum(1) / (2 * h * h))
        m2 = (w[:, None] * v).sum(0) / max(w.sum(), 1e-9)
        if np.hypot(*(m2 - m)) < 1e-3:
            m = m2
            break
        m = m2
    return m


def _lowess(x, y, w, span=SPAN, robust=2):
    """Robust local-linear smoothing of y (n, 2) against x (n,), with prior weights w: a stiff curve that a few
    odd bands (paint taking a band over) do not bend."""
    n = len(x)
    out = y.copy()
    rw = np.ones(n)
    h = span / 2
    for it in range(robust + 1):
        for i in range(n):
            d = np.abs(x - x[i]) / h
            k = np.where(d < 1, (1 - d ** 3) ** 3, 0) * w * rw
            if k.sum() <= 0:
                continue
            A = np.stack([np.ones(n), x - x[i]], 1)
            AtW = A.T * k
            try:
                coef = np.linalg.solve(AtW @ A + 1e-9 * np.eye(2), AtW @ y)
            except np.linalg.LinAlgError:
                continue
            out[i] = coef[0]
        if it < robust:
            r = np.hypot(*(y - out).T)
            s = np.median(r[w > 0]) if (w > 0).any() else 1.0
            t = r / (6 * max(s, 1e-6))
            rw = np.where(t < 1, (1 - t ** 2) ** 2, 0)
    return out


@dataclass
class Reference:
    centres: np.ndarray            # band centres in L*
    T: np.ndarray                  # (nb, 2) bare print's chromaticity at each band (normalised a*, b*)
    sigma: np.ndarray              # (nb,) its spread
    S: np.ndarray                  # (2, nbasis) the change across the frame (uneven light): per channel
    source: str                    # "automatic" or "picked"
    support: np.ndarray            # (nb,) weight of bare print each band had
    spatial: str = "tilt"          # "none", "tilt" (a plane) or "tilt+radial" (and centre to edge)
    level: float = 1.0             # the spread's level over its shape along tone
    cover: tuple | None = None     # with picks: the tones they cover
    notes: list = field(default_factory=list)

    def field_at(self, X, Y):
        B = basis(X, Y, self.spatial)
        return (B @ self.S.T) if B.shape[-1] else np.zeros(np.shape(X) + (2,), np.float32)

    def at(self, L, X, Y):
        T0 = np.interp(L, self.centres, self.T[:, 0])
        T1 = np.interp(L, self.centres, self.T[:, 1])
        s = np.interp(L, self.centres, self.sigma)
        F = self.field_at(X, Y)
        return (np.stack([T0, T1], -1) + F).astype(np.float32), s.astype(np.float32)


def basis(X, Y, spatial):
    X, Y = np.asarray(X, np.float32), np.asarray(Y, np.float32)
    if spatial == "none":
        return np.zeros(X.shape + (0,), np.float32)
    cols = [X, Y]
    if spatial == "tilt+radial":
        cols.append(X * X + Y * Y - 0.4)
    return np.stack(cols, -1)


def _grid(shape):
    h, w = shape
    s = max(h, w) / 2
    Y, X = np.mgrid[0:h, 0:w].astype(np.float32)
    return (X - (w - 1) / 2) / s, (Y - (h - 1) / 2) / s


def _smooth_sigma(sig, ok):
    x = np.arange(len(sig))
    s = np.interp(x, x[ok], sig[ok]) if ok.any() else np.full(len(sig), 2.0)
    s = np.array([np.median(s[max(0, i - 1):i + 2]) for i in range(len(s))])
    s = np.convolve(np.pad(s, 1, mode="edge"), np.ones(3) / 3, mode="valid")
    return np.maximum(s, SIGMA_FLOOR)




def fit_reference(L, u, X, Y, valid, pick=None, spatial="tilt", seed=0) -> tuple[Reference, dict]:
    """The bare print's colour at each tone (and its change across the frame), and its spread.

    Always automatic first: each band's densest colour, a stiff robust curve through them, then reweighting so that
    pixels far from the reference (paint) have no say; the spread is the scatter of what each tone holds about the
    reference.  With picks (a mask of areas marked bare), the picks then correct the automatic curve at the tones
    they cover (a smooth correction, carried flat beyond them).  The change across the frame stays the automatic
    fit's, which the whole print measures better than a few boxes can; so does the spread, except at tones where the
    picks moved the curve, where it comes from the boxes' own scatter scaled by this capture's box-to-frame factor."""
    if spatial is True:
        spatial = "tilt"
    elif spatial is False or spatial is None:
        spatial = "none"
    auto, diag = _fit_auto(L, u, X, Y, valid, spatial, seed)
    if pick is None or not (pick & valid).any():
        return auto, diag
    centres, nb = auto.centres, len(auto.centres)
    edges = np.concatenate([centres - BAND / 2, [centres[-1] + BAND / 2]])
    pidx = np.flatnonzero(pick & valid)
    pL, pu = L.ravel()[pidx], u.reshape(-1, 2)[pidx]
    pr = pu - auto.at(pL, X.ravel()[pidx], Y.ravel()[pidx])[0]
    pb = np.clip(np.digitize(pL, edges) - 1, 0, nb - 1)
    corr = np.full((nb, 2), np.nan)
    wts = np.zeros(nb)
    for k in range(nb):
        m = pb == k
        if m.sum() >= 20:
            corr[k] = np.median(pr[m], axis=0)
            wts[k] = math.sqrt(m.sum())
    have = wts > 0
    if not have.any():
        raise ValueError("the marked areas hold no usable pixels (clipped, too dark or outside the box)")
    x = np.arange(nb)
    lo, hi = int(x[have].min()), int(x[have].max())
    for j in range(2):
        corr[:, j] = np.interp(x, x[have], corr[have, j])          # flat beyond the picks
    if have.sum() >= 3:
        sm = _lowess(centres, corr, np.where(have, wts, 0.0), span=15.0)
        corr[lo:hi + 1] = sm[lo:hi + 1]
        corr[:lo], corr[hi + 1:] = sm[lo], sm[hi]
    ref = Reference(centres, auto.T + corr, auto.sigma.copy(), auto.S.copy(), "picked", np.zeros(nb), auto.spatial)
    ref.cover = (float(centres[lo] - BAND / 2), float(centres[hi] + BAND / 2))
    # the spread.  Where the picks moved the curve, paint had taken that tone over and widened the automatic spread
    # there; the boxes measure the bare print's scatter directly, but only locally.  How much more bare print varies
    # across this capture than within a box is read off the tones where the picks agree with the automatic curve
    # (there the automatic spread is sound), and the boxes' scatter is scaled up by it where the picks moved the
    # curve.  Never wider than the automatic spread; unchanged at tones the boxes do not cover.
    pd = np.hypot(*(pu - ref.at(pL, X.ravel()[pidx], Y.ravel()[pidx])[0]).T)
    box = np.full(nb, np.nan)
    for k in range(nb):
        if (pb == k).sum() >= 20:
            box[k] = max(np.median(pd[pb == k]) / 1.1774, SIGMA_FLOOR)
    covered = np.isfinite(box)
    moved = covered & (np.hypot(*corr.T) > auto.sigma)
    agree = covered & ~moved
    rho = float(np.clip(np.median(auto.sigma[agree] / box[agree]), 1.0, 4.0)) if agree.sum() >= 2 else 2.0
    sig = auto.sigma.copy()
    sig[moved] = np.minimum(auto.sigma[moved], rho * box[moved])
    ref.sigma = np.maximum(sig, SIGMA_FLOOR)
    ref.notes.append(f"picks moved {int(moved.sum())} of {int(covered.sum())} covered bands; box-to-frame factor {rho:.2f}")
    Ls, us, Xs, Ys, bi = diag["Ls"], diag["us"], diag["Xs"], diag["Ys"], diag["bi"]
    r = us - ref.at(Ls, Xs, Ys)[0]
    tt = np.hypot(*r.T) / (TUKEY_C * np.interp(Ls, centres, ref.sigma))
    w = np.where(tt < 1, (1 - tt * tt) ** 2, 0.0)
    ref.support = np.bincount(bi, weights=w, minlength=nb)
    diag = {**diag, "w": w, "picked_cover": ref.cover, "auto": auto}
    return ref, diag


SPREAD_CAP = 1.25           # a tone's spread may stand this far above the smooth curve of spread against tone


def _cap_sigma(sig, centres, counts):
    """The bare print's spread falls smoothly with lightness (roughly as a power of 116 / (L* + 16): the scale the
    chromaticity is normalised by).  A tone that paint has taken over shows as a bump above that curve, widened by
    the paint itself; it is brought down to the curve.  The curve is fitted to log spread with bumps upward given no
    say (a robust fit that only distrusts high values)."""
    # crushed blacks (a tone curve flattens their colour to almost nothing) and spreads at the floor say nothing
    # about the curve's slope: they are left out of the fit
    ok = (counts >= MIN_BAND_PX) & (centres >= 15.0) & (sig > 1.5 * SIGMA_FLOOR)
    if ok.sum() < 4:
        return sig
    x = np.log(116.0 / (centres + 16.0))
    y = np.log(np.maximum(sig, 1e-6))
    w0 = ok.astype(float)                      # every usable tone counts once, however many pixels it holds
    w = w0.copy()
    A = np.stack([np.ones_like(x), x], 1)
    for _ in range(8):
        coef = np.linalg.lstsq(A * np.sqrt(w)[:, None], y * np.sqrt(w), rcond=None)[0]
        e = y - A @ coef
        s = 1.4826 * np.median(np.abs(e[ok])) + 1e-3
        t = np.where(e > 0, e / (2.5 * s), -e / (4.0 * s))      # high values distrusted sooner than low ones
        w = w0 * np.where(t < 1, (1 - t * t) ** 2, 0.0)
    capped = np.minimum(sig, SPREAD_CAP * np.exp(A @ coef))
    return np.where(ok | (centres >= 15.0), capped, sig)


def _consistent_tilt(Bs, resid, w, Ls):
    """The part of the change across the frame that dark, middle and light tones agree on."""
    cuts = np.percentile(Ls, [33.3, 66.7])
    groups = (Ls < cuts[0], (Ls >= cuts[0]) & (Ls < cuts[1]), Ls >= cuts[1])
    fits = []
    for g in groups:
        ww = w * g
        if ww.sum() < 500:
            return np.zeros((2, Bs.shape[1]))
        mx = (ww @ Bs) / ww.sum()
        Bc = (Bs - mx) * np.sqrt(ww)[:, None]
        fits.append(np.stack([np.linalg.lstsq(Bc, resid[:, j] * np.sqrt(ww), rcond=None)[0] for j in range(2)]))
    fits = np.stack(fits)                                   # (3, 2, nbasis)
    same = (np.sign(fits) == np.sign(fits[0])).all(axis=0)
    return np.where(same, np.sign(fits[0]) * np.abs(fits).min(axis=0), 0.0)


def _fit_auto(L, u, X, Y, valid, spatial, seed, cap_spread=True):
    rng = np.random.default_rng(seed)
    idx = np.flatnonzero(valid)
    if len(idx) < 2000:
        raise ValueError("too little of the print can be judged (clipped, too dark or outside the box)")
    if len(idx) > SAMPLE:
        idx = np.sort(rng.choice(idx, SAMPLE, replace=False))
    Ls, us = L.ravel()[idx], u.reshape(-1, 2)[idx]
    Xs, Ys = X.ravel()[idx], Y.ravel()[idx]
    edges = np.arange(L_DARK, 100 + BAND, BAND)
    centres = (edges[:-1] + edges[1:]) / 2
    nb = len(centres)
    x = np.arange(nb)
    bi = np.clip(np.digitize(Ls, edges) - 1, 0, nb - 1)
    counts = np.bincount(bi, minlength=nb)
    # stage 1: each band's densest colour, and a stiff robust curve through them
    T0 = np.full((nb, 2), np.nan)
    w0 = np.zeros(nb)
    for k in range(nb):
        sel = bi == k
        if sel.sum() < MIN_BAND_PX:
            continue
        v = us[sel]
        med = np.median(v, axis=0)
        spread = np.median(np.hypot(*(v - med).T)) / 1.1774
        T0[k] = _mode2d(v, h=float(np.clip(0.6 * spread, 0.6, 4.0)))
        w0[k] = np.sqrt(sel.sum())
    have = np.isfinite(T0[:, 0])
    if have.sum() < 2:
        raise ValueError("the print covers too few tones to set a reference")
    for j in range(2):
        T0[:, j] = np.interp(x, x[have], T0[have, j])             # constant beyond the ends
    T = _lowess(centres, T0, np.where(have, w0, 0.0))
    Bs = basis(Xs, Ys, spatial)
    S = np.zeros((2, Bs.shape[1]))
    r = us - np.stack([np.interp(Ls, centres, T[:, 0]), np.interp(Ls, centres, T[:, 1])], 1)
    rn = np.hypot(*r.T)
    sig = np.array([np.median(rn[bi == k]) / 1.1774 if counts[k] >= MIN_BAND_PX else np.nan for k in range(nb)])
    sig = _smooth_sigma(np.nan_to_num(sig, nan=2.0), np.isfinite(sig))
    w = np.ones(len(Ls))
    for it in range(ITER):
        F = Bs @ S.T
        r = us - (np.stack([np.interp(Ls, centres, T[:, 0]), np.interp(Ls, centres, T[:, 1])], 1) + F)
        rn = np.hypot(*r.T)
        t = rn / (TUKEY_C * np.interp(Ls, centres, sig))
        w = np.where(t < 1, (1 - t * t) ** 2, 0.0)
        # the change across the frame (uneven light).  A change in the light's colour shifts every tone alike;
        # paint along one side holds some tones only.  So the tilt is fitted in the dark, middle and light thirds
        # of the print separately, and only what all three agree on is kept (same sign, the smallest size).
        if Bs.shape[1]:
            S = _consistent_tilt(Bs, us - np.stack([np.interp(Ls, centres, T[:, 0]),
                                                    np.interp(Ls, centres, T[:, 1])], 1), w, Ls)
            F = Bs @ S.T
        # the curve: weighted mean per band, then the stiff robust smoother
        Tn = np.full((nb, 2), np.nan)
        sw = np.bincount(bi, weights=w, minlength=nb)
        for j in range(2):
            Tn[:, j] = np.bincount(bi, weights=w * (us[:, j] - F[:, j]), minlength=nb) / np.maximum(sw, 1e-9)
        okb = sw > 20
        if okb.sum() >= 2:
            for j in range(2):
                Tn[:, j] = np.interp(x, x[okb], Tn[okb, j])
            T = _lowess(centres, Tn, np.where(okb, np.sqrt(sw), 0.0))
        # the spread: median distance among the pixels still in play, per band (truncation bias is small at 3.5)
        inl = t < 1
        sg = np.full(nb, np.nan)
        for k in range(nb):
            sel = (bi == k) & inl
            if sel.sum() >= 40:
                sg[k] = np.median(rn[sel]) / 1.1774
        sig = _smooth_sigma(np.nan_to_num(sg, nan=0), np.isfinite(sg))
        if cap_spread:
            sig = np.maximum(_cap_sigma(sig, centres, counts), SIGMA_FLOOR)
    support = np.bincount(bi, weights=w, minlength=nb)
    ref = Reference(centres, T, sig, S, "automatic", support, spatial)
    diag = {"w": w, "Ls": Ls, "bi": bi, "counts": counts, "idx": idx, "Xs": Xs, "Ys": Ys, "us": us,
            "picked_cover": None}
    return ref, diag


# ------------------------------------------------------------------------------------------------- the checks
def checks(ref: Reference, diag: dict, L, u, X, Y, valid, seed=0) -> list[str]:
    """The reference's own checks, in words, each with what to do.  None of them is a number on the picture."""
    out = []
    w, counts, bi = diag["w"], diag["counts"], diag["bi"]
    share = float((w > 0.25).mean())
    if share < 0.5:
        out.append("Less than half of the print matches the bare-print reference: it may be painted nearly all "
                   "over, or the reference may be wrong. Compare the Original with the Boosted panel; if bare areas "
                   "come out coloured there, mark bare areas and run again.")
    # tones the reference had no bare print for
    lv = L[valid]
    lo5, hi95 = np.percentile(lv, 5), np.percentile(lv, 95)
    if ref.source == "picked":
        lo, hi = diag["picked_cover"]
        left = [t for t, miss in (("darker", lo5 < lo - 10), ("lighter", hi95 > hi + 10)) if miss]
        if left:
            out.append("Your marked areas leave out the " + " and ".join(left) + " tones of the print; there the "
                       "reference follows the automatic one's shape, joined on to yours. Mark a bare area in those "
                       "tones if they matter.")
    else:
        has = counts >= MIN_BAND_PX
        gap = has & ~(ref.support >= 0.15 * np.maximum(counts, 1))
        if gap.any():
            Ls = ref.centres[gap]
            part = ("darkest" if Ls.max() < 40 else "lightest" if Ls.min() > 60 else "middle")
            out.append(f"Little of the {part} tones matched the reference: there it is carried over from neighbouring "
                       "tones. If those tones are painted all over, mark a bare area in them.")
    # uneven light
    sig_med = float(np.median(ref.sigma))
    cx, cy = float(X.max()), float(Y.max())
    gx, gy = np.meshgrid(np.linspace(-cx, cx, 9), np.linspace(-cy, cy, 9))
    Fg = ref.field_at(gx, gy)
    tilt = float(np.hypot(*(Fg - Fg.reshape(-1, 2).mean(0)).reshape(-1, 2).T).max())
    if tilt > 1.5 * sig_med:
        out.append("The colour of the light changes across the frame; the reference follows it. A painted area "
                   "covering one side could be taken for it: check that side in the Boosted panel.")
    # strongly coloured reference
    mid = (ref.centres > 40) & (ref.centres < 70)
    if mid.any():
        c_ab = np.hypot(*ref.T[mid].T) * (ref.centres[mid] + 16) / 116
        if c_ab.max() > 12 and ref.source == "automatic":
            out.append("The bare-print reference is strongly coloured: a strong colour cast, a print painted nearly "
                       "all over, or something other than the print filling much of the frame. Check the Taken as "
                       "bare print panel; mark the print or a bare area if it is wrong.")
    # split check: do the two halves of the print agree about what bare print looks like?
    if ref.source == "automatic":
        for halves, tones in _split_disagreement(L, u, X, Y, valid, ref, seed):
            out.append(f"The {halves} halves of the print disagree about what bare print looks like in the {tones} "
                       "tones: paint may cover those tones in one half, and then the reference may have taken it for "
                       "bare print. If an area in those tones looks neutral in the Boosted panel but you think it is "
                       "painted, mark a bare area in those tones and run again.")
    return out


def _split_disagreement(L, u, X, Y, valid, ref, seed):
    """Do the two halves of the print (left and right, then top and bottom) agree about what bare print looks
    like?  Each half gets its own automatic curve; after the frame's tilt is allowed for, a disagreement of 2
    spreads or more over three neighbouring bands (7.5 L*) is reported, with the tones it is in."""
    found = []
    hx, hy = 0.5 * float(X.max()), 0.5 * float(Y.max())
    for name, side in (("left and right", X < 0), ("top and bottom", Y < 0)):
        curves = []
        for part in (side, ~side):
            m = valid & part
            if m.sum() < 20000:
                break
            curves.append(_fit_auto(L, u, X, Y, m, "none", seed + 1)[0])
        if len(curves) < 2:
            continue
        a, b = curves
        if name.startswith("left"):
            shift = ref.field_at(np.float32(-hx), np.float32(0)) - ref.field_at(np.float32(hx), np.float32(0))
        else:
            shift = ref.field_at(np.float32(0), np.float32(-hy)) - ref.field_at(np.float32(0), np.float32(hy))
        both = (a.support > 200) & (b.support > 200)
        score = np.hypot(*((a.T - b.T) - shift[None, :]).T) / ref.sigma
        hit = both & (score >= 2.0)
        run, best, end = 0, 0, -1
        for k, h in enumerate(hit):
            run = run + 1 if h else 0
            if run > best:
                best, end = run, k
        if best >= 3:
            Lc = float(ref.centres[end - best // 2])
            found.append((name, "darker" if Lc < 40 else "lighter" if Lc > 65 else "middle"))
    return found




# --------------------------------------------------------------------------------------------- edges and fringes
def edge_strength(L):
    """Lightness change per pixel, the largest within the chroma smoothing's reach (L* per px)."""
    gx = cv2.Sobel(L, cv2.CV_32F, 1, 0, ksize=3) / 8
    gy = cv2.Sobel(L, cv2.CV_32F, 0, 1, ksize=3) / 8
    g = np.hypot(gx, gy)
    return cv2.dilate(g, np.ones((CHROMA_MEDIAN, CHROMA_MEDIAN), np.uint8))


def fringe_scale(d, s, g, valid, diag, nbins=12):
    """How much colour this capture puts on lightness edges of bare print (lateral colour, sharpening, 4:2:0
    chroma, tone mixing across an edge), per unit of edge strength: the bare print's spread grows as
    sqrt(sigma^2 + (kappa * g)^2).  Fitted on the capture itself, from medians in bins of edge strength (most edges
    in a print are bare print, so a median is not moved by the edges of painted areas)."""
    idx = diag["idx"]
    dd = np.hypot(*d.reshape(-1, 2)[idx].T)
    ss = s.ravel()[idx]
    gg = g.ravel()[idx]
    q = np.quantile(gg, np.linspace(0.5, 0.995, nbins + 1))
    num = den = 0.0
    for i in range(nbins):
        m = (gg >= q[i]) & (gg < q[i + 1])
        if m.sum() < 200:
            continue
        eff = np.median(dd[m]) / 1.1774                 # the spread at these edges
        base = np.median(ss[m])
        gm = np.median(gg[m])
        excess = max(eff * eff - base * base, 0.0)
        num += gm * gm * excess * m.sum()
        den += gm ** 4 * m.sum()
    return float(np.sqrt(num / den)) if den > 0 else 0.0


SPECK_AREA = 1e-5           # share of the picture: departures smaller than this are dropped (20 px at 1400 x 1400)


def drop_specks(opacity, share=SPECK_AREA):
    """Remove isolated blobs too small to be a touch of paint (noise, JPEG blocks); a small touch (lips, an earring)
    is many times larger at the working size."""
    on = (opacity >= 0.25).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(on, connectivity=8)
    small = st[:, cv2.CC_STAT_AREA] < max(16, share * opacity.size)
    small[0] = False
    out = opacity.copy()
    out[small[lab]] = 0
    return out


# ---------------------------------------------------------------------------------------------------- analyse
def analyse(rgb: np.ndarray, picks=(), box="auto", exclude=(), sensitivity="normal", spatial="tilt", run_checks=True,
            edge_guard=True):
    L, a, b, u = planes(rgb)
    valid, masks = judgeable(rgb, L, box, exclude)
    X, Y = _grid(L.shape)
    pick = None
    if picks:
        pick = np.zeros(L.shape, bool)
        for x0, y0, x1, y1 in picks:
            pick[y0:y1, x0:x1] = True
        pick &= valid
    ref, diag = fit_reference(L, u, X, Y, valid, pick, spatial)
    r, s = ref.at(L, X, Y)
    d = u - r
    k = (np.maximum(L, 0) + 16) / 116
    d_ab = d * k[..., None]                                        # departure in a*, b* (for the pictures)
    g = edge_strength(L)
    kappa = fringe_scale(d, s, g, valid, diag) if edge_guard else 0.0
    ref.notes.append(f"fringe scale {kappa:.3g}")
    s_eff = np.sqrt(s * s + (kappa * g) ** 2)
    z = np.hypot(d[..., 0], d[..., 1]) / s_eff
    z = cv2.medianBlur(z.astype(np.float32), 5)                    # specks: single pixels go, small touches stay
    z0, z1 = PRESETS[sensitivity]
    t = np.clip((z - z0) / (z1 - z0), 0, 1)
    opacity = (t * t * (3 - 2 * t)).astype(np.float32)
    opacity[~valid] = 0
    opacity = drop_specks(opacity)
    # which pixels the reference took as bare print (for the picture)
    wmap = np.zeros(L.size, np.float32)
    wmap[diag["idx"]] = diag["w"]
    bare = np.zeros(L.shape, np.float32)
    rz = np.hypot(d[..., 0], d[..., 1]) / s_eff
    bare[:] = np.where(rz < TUKEY_C, (1 - (rz / TUKEY_C) ** 2) ** 2, 0)
    bare[~valid] = 0
    warnings = checks(ref, diag, L, u, X, Y, valid) if run_checks else []
    return {"rgb": rgb, "L": L, "d_ab": d_ab.astype(np.float32), "z": z, "opacity": opacity, "valid": valid,
            "masks": masks, "ref": ref, "bare": bare, "warnings": warnings, "sensitivity": sensitivity,
            "pick": pick, "alpha": opacity, "show": valid, "presence_at": 0.5}


# ---------------------------------------------------------------------------------------------------- pictures
def _lab_to_srgb(L, A, B):
    lab = np.stack([L, A, B], -1).astype(np.float32)
    return np.clip(cv2.cvtColor(lab, cv2.COLOR_LAB2RGB), 0, 1)


def _hatch(shape, step=7):
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w]
    return ((xx + yy) // step) % 2 == 0


def picture_boosted(res, k=BOOST):
    d = res["d_ab"]
    m = np.hypot(d[..., 0], d[..., 1])
    g = k / np.sqrt(1 + (k * m / BOOST_CMAX) ** 2)                 # gain k near neutral, rolling off before clipping
    g = g * m * m / (m * m + BOOST_CORE ** 2)                       # coring: the last unit of a*b* noise stays quiet
    out = _lab_to_srgb(res["L"], d[..., 0] * g, d[..., 1] * g)
    grey = np.repeat((res["L"] / 100)[..., None], 3, 2)
    nv = ~res["valid"]
    out[nv] = grey[nv] * 0.85 + 0.15 * _hatch(res["L"].shape)[nv][:, None]
    return out


def _hue_colours(d):
    h = np.arctan2(d[..., 1], d[..., 0])
    return _lab_to_srgb(np.full(h.shape, 62.0), 75 * np.cos(h), 75 * np.sin(h))


def picture_presence(res):
    base = 0.28 + 0.5 * (res["L"] / 100)
    out = np.repeat(base[..., None], 3, 2).astype(np.float32)
    col = _hue_colours(res["d_ab"])
    a = res["opacity"][..., None]
    out = out * (1 - a) + col * a
    nv = ~res["valid"]
    hat = _hatch(res["L"].shape)
    out[nv] = np.where(hat[nv][:, None], 0.92, 0.72)
    return out


def picture_bare(res):
    """Taken as bare print: the capture as it is where the reference took the print as bare; dimmed elsewhere."""
    rgb = res["rgb"]
    grey = np.repeat((0.15 + 0.35 * res["L"] / 100)[..., None], 3, 2)
    b = np.clip(cv2.GaussianBlur(res["bare"], (0, 0), 2.5) * 1.5, 0, 1)[..., None]
    out = grey * (1 - b) + rgb * b
    if res.get("pick") is not None:
        edge = cv2.morphologyEx(res["pick"].astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((5, 5), np.uint8)) > 0
        out[edge] = (1.0, 0.85, 0.0)
    nv = ~res["valid"]
    out[nv] = np.where(_hatch(res["L"].shape)[nv][:, None], 0.92, 0.72)
    return out


def _font(size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans.ttf"):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def montage(res, name="", panel=700):
    pics = [("Original", res["rgb"]), ("Boosted: bare print drawn neutral", picture_boosted(res)),
            ("Where colour departs from bare print", picture_presence(res)),
            ("Taken as bare print (" + res["ref"].source + ")", picture_bare(res))]
    h, w = res["L"].shape
    s = panel / max(h, w)
    pw, ph = round(w * s), round(h * s)
    font, small = _font(18), _font(15)
    lines = [f"{name}   {VIS_LABEL}.   Reference: " + (
        "automatic (the most common colour at each tone)" if res["ref"].source == "automatic"
        else "your marked bare areas") + f".   Sensitivity: {res['sensitivity']}.   Hatched: not judged."]
    lines += [f"- {t}" for t in res["warnings"]] or []
    draw0 = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    wrapped = []
    for ln in lines:
        cur = ""
        for word in ln.split(" "):
            trial = (cur + " " + word).strip()
            if cur and draw0.textlength(trial, font=small) > 2 * pw - 20:
                wrapped.append(cur)
                cur = word
            else:
                cur = trial
        wrapped.append(cur)
    foot = 14 + 21 * len(wrapped)
    M = Image.new("RGB", (2 * pw, 2 * (ph + 28) + foot), "white")
    d = ImageDraw.Draw(M)
    for i, (title, arr) in enumerate(pics):
        im = Image.fromarray((np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8)).resize((pw, ph), Image.LANCZOS)
        x, y = (i % 2) * pw, (i // 2) * (ph + 28)
        M.paste(im, (x, y + 28))
        d.text((x + 8, y + 5), title, fill="black", font=font)
    y = 2 * (ph + 28) + 7
    for ln in wrapped:
        d.text((8, y), ln, fill="black", font=small)
        y += 21
    return M


# ---------------------------------------------------------------------------------------------------- command line
def _sidecar(path: Path) -> dict:
    p = path.with_name(path.stem + ".bare.json")
    if p.exists():
        return json.loads(p.read_text())
    return {}


def run_one(path: Path, out_dir: Path, sensitivity="normal") -> dict:
    rgb, info = load(path)
    side = _sidecar(path)
    work = to_working(rgb)
    s = work.shape[1] / rgb.shape[1]
    scale = lambda bx: [int(round(v * s)) for v in bx]  # noqa: E731
    picks = [scale(b) for b in side.get("bare", [])]
    box = scale(side["print"]) if side.get("print") else None
    exclude = [scale(b) for b in side.get("exclude", [])]
    res = analyse(work, picks, box, exclude, sensitivity)
    out_dir.mkdir(parents=True, exist_ok=True)
    montage(res, path.name).save(out_dir / f"{path.stem}_montage.png")
    rec = {"software": f"hpv {VERSION}", "what": VIS_LABEL, "source": info,
           "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "sidecar": side or None,
           "reference": res["ref"].source, "sensitivity": sensitivity, "warnings": res["warnings"]}
    (out_dir / f"{path.stem}_record.json").write_text(json.dumps(rec, indent=2))
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser(description="Handpaint visualiser (prototype): pictures of where colour departs "
                                             "from the bare print. " + VIS_LABEL)
    ap.add_argument("inputs", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, default=Path("hpv_out"))
    ap.add_argument("--sensitivity", choices=list(PRESETS), default="normal")
    a = ap.parse_args(argv)
    files = []
    for p in a.inputs:
        files += sorted(q for q in p.rglob("*") if q.suffix.lower() in {".jpg", ".jpeg", ".png", ".tif", ".tiff",
                                                                         ".webp", ".heic"}) if p.is_dir() else [p]
    for f in files:
        try:
            rec = run_one(f, a.out, a.sensitivity)
            print(f"{f.name}: reference {rec['reference']}; " + ("; ".join(rec["warnings"]) or "no warnings"))
        except Exception as exc:  # noqa: BLE001
            print(f"{f.name}: FAILED: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
