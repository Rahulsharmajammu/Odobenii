"""Prototype of the proposed handpaint visualiser core (evaluation only; not the shipped script).

Pipeline: load (ICC -> sRGB, EXIF orientation) -> working size -> CIELAB -> 5 px median on a*, b* -> masks (glare,
near-black, outside the object box) -> REFERENCE (what the unpainted print looks like) -> departure (Mahalanobis, in
units of the print's own variability) -> pictures (original, reference 'as if unpainted', boosted around the reference,
presence map) and checks in words.

The reference model, per pixel at lightness L and position (x, y):
    ab_unpainted(L, x, y) = m(L) + g(L) * phi(x, y) @ C,      residual ~ N(0, S(L))
  m(L)   the print's own tone curve: robust per-band medians of a*, b*, pooled across bands by robust local-linear
         smoothing (Cleveland's LOWESS with bisquare robustness weights)
  phi    a gentle colour field over the frame (x, y, r^2): light colour gradients, colour shading
  g(L)   (L + 16) / 116: a multiplicative colour cast moves a*, b* in proportion to f(Y) = Y^(1/3) in CIELAB
  S(L)   the print's own 2 x 2 variability per band (texture, noise, JPEG), smoothed, floored
Pixels are re-weighted by Tukey's biweight on their departure, so paint (large departure) drops out of the fit.
Options switch each refinement off, to reproduce the TODO.md baseline (isotropic spread, no pooling, no field).
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np
from PIL import Image, ImageCms, ImageDraw, ImageFont, ImageOps

BAND = 2.5                                  # L* band width
CENTRES = np.arange(BAND / 2, 100, BAND)
FLOOR_AB = 0.5                              # a*, b* units added to every band's sd (8-bit steps, JPEG)
MAX_ANISO = 5.0                             # largest ratio of the two sds of a band's variability
Z_SHOW = (2.0, 5.0)                         # presence opacity ramps from z = 2 to z = 5 ("normal" sensitivity)
SAMPLE = 400_000
TILES = 6                                   # the light's colour is read from a TILES x TILES grid of patches


# ----------------------------------------------------------------------------------------------------------------------
# loading
# ----------------------------------------------------------------------------------------------------------------------

def load_srgb(src) -> np.ndarray:
    """Any image as 8-bit sRGB: EXIF orientation applied, an embedded ICC profile converted by LittleCMS (relative
    colorimetric), untagged taken as sRGB.  ``src`` is a path or bytes."""
    im = Image.open(io.BytesIO(src) if isinstance(src, (bytes, bytearray)) else src)
    icc = im.info.get("icc_profile")
    im = ImageOps.exif_transpose(im)
    if im.mode not in ("RGB", "RGBA", "L", "CMYK"):
        im = im.convert("RGB")
    if icc:
        try:
            src_p = ImageCms.ImageCmsProfile(io.BytesIO(icc))
            dst_p = ImageCms.createProfile("sRGB")
            im = ImageCms.profileToProfile(im.convert("RGB") if im.mode == "RGBA" else im, src_p, dst_p,
                                           renderingIntent=ImageCms.Intent.RELATIVE_COLORIMETRIC, outputMode="RGB")
        except Exception:
            im = im.convert("RGB")
    return np.asarray(im.convert("RGB"))


def working(rgb8: np.ndarray, long_edge: int = 3000) -> np.ndarray:
    h, w = rgb8.shape[:2]
    s = min(1.0, long_edge / max(h, w))
    x = rgb8.astype(np.float32) / 255.0
    if s < 1.0:
        x = cv2.resize(x, (max(1, round(w * s)), max(1, round(h * s))), interpolation=cv2.INTER_AREA)
    return x


def to_lab(rgb: np.ndarray, median_px: int = 5) -> Tuple[np.ndarray, np.ndarray]:
    lab = cv2.cvtColor(rgb.astype(np.float32), cv2.COLOR_RGB2Lab)
    L = lab[..., 0]
    ab = lab[..., 1:].copy()
    if median_px >= 3:                     # JPEG 4:2:0 chroma blocks, demosaic and CA fringes; L untouched
        for c in range(2):
            ab[..., c] = cv2.medianBlur(np.ascontiguousarray(ab[..., c]), median_px)
    return L, ab


def masks(rgb: np.ndarray, L: np.ndarray, box: Optional[Sequence[int]] = None) -> Dict[str, np.ndarray]:
    """Pixels that cannot be judged: glare (a channel at or near clipping, grown by 3 px), near-black (chroma is
    noise there), outside an optional object box [x0, y0, x1, y1]."""
    glare = (rgb >= 250 / 255).any(axis=2).astype(np.uint8)
    glare = cv2.dilate(glare, np.ones((7, 7), np.uint8)) > 0
    black = cv2.blur(L.astype(np.float32), (5, 5)) < 7.0
    outside = np.zeros(L.shape, bool)
    if box is not None:
        x0, y0, x1, y1 = box
        outside[:] = True
        outside[y0:y1, x0:x1] = False
    return {"glare": glare, "black": black, "outside": outside, "valid": ~(glare | black | outside)}


# ----------------------------------------------------------------------------------------------------------------------
# the reference
# ----------------------------------------------------------------------------------------------------------------------

@dataclass
class Options:
    aniso: bool = True          # 2 x 2 variability per band (else one isotropic sd)
    pool: bool = True           # robust local-linear smoothing across bands (else a 5-band running mean)
    spatial: bool = True        # the gentle colour field over the frame
    rounds: int = 5
    span: float = 14.0          # L* half-width of the pooling window
    tukey_c: float = 4.0
    inlier_z: float = 3.0       # pixels used for the band medians
    edges: bool = True          # compare at chroma resolution, with the misregistration term (else as TODO.md)
    scale_q: float = 0.25       # quantile of distances the spread comes from (0.5: the median, as TODO.md reads)
    seed: int = 0


@dataclass
class Reference:
    m: np.ndarray               # (bands, 2) tone curve at CENTRES
    S: np.ndarray               # (bands, 2, 2) variability
    C: np.ndarray               # (3, 2) colour field coefficients
    support: np.ndarray         # (bands,) share of inlier pixels in each band (coverage)
    setaside: np.ndarray        # (bands,) share of the band's pixels set aside as departing
    how: str
    opts: Options
    shape: Tuple[int, int]
    weights: Optional[np.ndarray] = None   # per-pixel final weight on the sample (diagnostic)
    sample_idx: Optional[np.ndarray] = None
    notes: List[str] = field(default_factory=list)


def _phi(idx: np.ndarray, shape: Tuple[int, int]) -> np.ndarray:
    h, w = shape
    y, x = np.divmod(idx, w)
    xn = 2 * x / max(w - 1, 1) - 1
    yn = 2 * y / max(h - 1, 1) - 1
    return np.stack([xn, yn], axis=1)                         # a plane: a radial term absorbed corner washes


def _g(L):
    return (np.asarray(L) + 16.0) / 116.0


def _band_of(l):
    return np.clip((l / BAND).astype(int), 0, len(CENTRES) - 1)


def _lowess(x, y, wt, span, iters=2):
    """Robust local-linear smoothing of band values y (n, d) at x, with prior weights wt (0 = no data): tricube
    distance weights and bisquare robustness weights (Cleveland 1979).  Bands with no data are filled by the fit."""
    n, d = y.shape
    rob = np.ones(n)
    out = np.zeros_like(y)
    for _ in range(iters + 1):
        for j in range(n):
            u = np.abs(x - x[j]) / span
            k = np.where(u < 1, (1 - u ** 3) ** 3, 0.0) * wt * rob
            if k.sum() <= 1e-9:
                out[j] = np.nan
                continue
            X = np.stack([np.ones(n), x - x[j]], axis=1)
            W = k[:, None]
            A = X.T @ (W * X) + np.diag([1e-9, 1e-6])
            beta = np.linalg.solve(A, X.T @ (W * y))
            out[j] = beta[0]
        res = np.linalg.norm(np.where(np.isfinite(out), y - out, 0), axis=1)
        ok = wt > 0
        s = np.median(res[ok]) if ok.any() else 0.0
        rob = np.where(res < 6 * s + 1e-9, (1 - (res / (6 * s + 1e-9)) ** 2) ** 2, 0.0) if s > 0 else np.ones(n)
    # fill bands beyond the data by the nearest fitted value
    good = np.isfinite(out).all(axis=1)
    if good.any() and not good.all():
        for c in range(d):
            out[:, c] = np.interp(x, x[good], out[good, c])
    return out


def _running_mean(y, wt, k=5):
    """The TODO baseline: band medians, empty bands interpolated, a k-band running mean."""
    good = wt > 0
    out = y.copy()
    for c in range(y.shape[1]):
        out[:, c] = np.interp(CENTRES, CENTRES[good], y[good, c]) if good.any() else 0.0
    ker = np.ones(k) / k
    pad = k // 2
    for c in range(y.shape[1]):
        out[:, c] = np.convolve(np.pad(out[:, c], pad, mode="edge"), ker, mode="valid")
    return out


def _band_sd_iso(res, band, sel, nb, pool, span, q=0.5):
    """Isotropic sd per band from a quantile q of the distances (Rayleigh: the q-quantile is sd * sqrt(-2 ln(1 - q))),
    smoothed, floored.  A low q keeps a large wash in the band from widening the yardstick (a median distance is
    inflated well before 50 % contamination)."""
    k = np.sqrt(-2 * np.log(1 - q))
    sd = np.full(nb, np.nan)
    for b in range(nb):
        s = sel & (band == b)
        if s.sum() >= 30:
            sd[b] = np.quantile(np.linalg.norm(res[s], axis=1), q) / k
    ok = np.isfinite(sd)
    if not ok.any():
        return np.ones(nb)
    sd = np.interp(CENTRES, CENTRES[ok], sd[ok])
    if pool:
        sd = _lowess(CENTRES, sd[:, None], ok.astype(float), span, iters=0)[:, 0]
    return np.sqrt(np.maximum(sd, 1e-3) ** 2 + FLOOR_AB ** 2)


def _curve(r0, band, sel, nb, opts, anchor=None):
    """Band medians of r0 over ``sel``, pooled across bands.  ``anchor`` (bool over the sample): where a band holds
    at least 30 anchored pixels (picks), its median is theirs alone."""
    med = np.zeros((nb, 2))
    sup = np.zeros(nb)
    for b in range(nb):
        inb = band == b
        if anchor is not None:
            a = anchor & inb
            if a.sum() >= 30:
                med[b] = np.median(r0[a], axis=0)
                sup[b] = max(a.sum(), 200)
                continue
        s = sel & inb
        if s.sum() >= 30:
            med[b] = np.median(r0[s], axis=0)
            sup[b] = s.sum()
    wt = np.minimum(sup / 200.0, 1.0)
    return (_lowess(CENTRES, med, wt, opts.span) if opts.pool else _running_mean(med, wt)), sup


def _scale(sd, inl, band):
    """One number for the print's own variability: the median band sd over pixels the reference keeps."""
    return float(np.median(sd[band[inl]])) if inl.any() else float(np.median(sd))


def fit_reference(L: np.ndarray, ab: np.ndarray, valid: np.ndarray, picks: Optional[np.ndarray] = None,
                  opts: Options = Options(), grad: Optional[np.ndarray] = None) -> Reference:
    """Fit the reference in three stages, so that what paint does to one stage cannot leak into the next:
      A  the tone curve and an isotropic spread, high breakdown (band medians; median distances), no field;
      B  a gentle colour field (a plane over the frame), fitted on A's inliers with each tone band weighted alike,
         re-estimated with the curve a few times, and kept only if it clearly tightens the print's own variability;
      C  the shape of the variability (2 x 2 per band), measured only on the final inliers.
    With ``picks`` the picks are seeds: the curve is theirs wherever they have pixels; the rest of the image fills
    the curve and sets the yardstick, but only with pixels that agree with the picks.
    ``grad``: |grad L| per pixel; strong edges are left out of the fit (their chroma is not their own)."""
    rng = np.random.default_rng(opts.seed)
    shape = L.shape
    pool_mask = valid if grad is None else (valid & (grad < 2.0))
    idx = np.flatnonzero(pool_mask)
    if len(idx) < 500:
        raise ValueError("too few usable pixels for a reference")
    if len(idx) > SAMPLE:
        idx = np.sort(rng.choice(idx, SAMPLE, replace=False))
    if picks is not None:                                   # every picked pixel is in the sample
        pidx = np.flatnonzero(pool_mask & picks)
        idx = np.union1d(idx, pidx)
    l = L.ravel()[idx].astype(np.float64)
    v = ab.reshape(-1, 2)[idx].astype(np.float64)
    is_pick = None if picks is None else picks.ravel()[idx]
    if is_pick is not None and is_pick.sum() < 100:
        raise ValueError("the picks hold too few usable pixels")
    band = _band_of(l)
    nb = len(CENTRES)
    gl = _g(l)[:, None]
    P = _phi(idx, shape)
    notes = []
    counts_all = np.bincount(band, minlength=nb).astype(float)

    def stage_a(C, rounds, inl=None, only=None):
        inl = np.ones(len(l), bool) if inl is None else inl
        if only is not None:
            inl = inl & only
        field_ = gl * (P @ C)
        for _ in range(rounds):
            m, sup = _curve(v - field_, band, inl, nb, opts, anchor=is_pick if only is None else None)
            mp = np.stack([np.interp(l, CENTRES, m[:, c]) for c in range(2)], axis=1)
            res = v - mp - field_
            sd = _band_sd_iso(res, band, inl, nb, opts.pool, opts.span, opts.scale_q)
            z = np.linalg.norm(res, axis=1) / sd[band]
            inl = z < opts.inlier_z
            if only is not None:
                inl = inl & only
        return m, sd, res, z, inl

    def light_field(m, sd, res, z, inl, seedset=None):
        """The light's colour, read from a grid of patches: each patch votes once (the median cast of its pixels, in
        units of g(L)), and a plane is fitted robustly across patches, so a wash over a few patches is outvoted.
        Kept only if it clearly tightens the print's own variability."""
        s0 = _scale(sd, inl, band)
        h, w = shape
        yy, xx = np.divmod(idx, w)
        tile = (np.minimum(yy * TILES // h, TILES - 1) * TILES + np.minimum(xx * TILES // w, TILES - 1)).astype(int)
        Cn, mn, sdn, resn, zn, inln = np.zeros((2, 2)), m, sd, res, z, inl
        for _ in range(3):
            mp = np.stack([np.interp(l, CENTRES, mn[:, c]) for c in range(2)], axis=1)
            q = (v - mp) / gl
            keep = zn < 6.0
            casts, cx, cy = [], [], []
            for t in range(TILES * TILES):
                s = keep & (tile == t)
                if s.sum() >= 200:
                    casts.append(np.median(q[s], axis=0))
                    cx.append(P[s, 0].mean())
                    cy.append(P[s, 1].mean())
            if len(casts) < 9:
                break
            casts, X = np.asarray(casts), np.stack([np.ones(len(cx)), cx, cy], axis=1)
            wt = np.ones(len(casts))
            for _ in range(6):                                  # Tukey-reweighted plane across patches
                Wd = wt[:, None]
                beta = np.linalg.solve(X.T @ (Wd * X) + 1e-9 * np.eye(3), X.T @ (Wd * casts))
                rr = np.linalg.norm(casts - X @ beta, axis=1)
                sc = 1.4826 * np.median(rr) + 1e-6
                u = rr / (4.0 * sc)
                wt = np.where(u < 1, (1 - u ** 2) ** 2, 0.0)
            Cn = beta[1:]
            mn, sdn, resn, zn, inln = stage_a(Cn, 3, inl=seedset)
        if _scale(sdn, inln, band) < 0.85 * s0:
            return Cn, True
        return np.zeros((2, 2)), False

    # A and B on the whole frame: the tone curve, and the light (a property of the capture, so read from all of it)
    is_pick_saved, is_pick = is_pick, None
    C = np.zeros((2, 2))
    m, sd, res, z, inl = stage_a(C, 4)
    field_kept = False
    if opts.spatial:
        C, field_kept = light_field(m, sd, res, z, inl)
        if field_kept:
            notes.append("a gentle colour gradient across the frame was taken out (light, or anything else that "
                          "varies smoothly across the print)")
    m, sd, res, z, inl = stage_a(C, 3)
    is_pick = is_pick_saved
    if is_pick is not None:
        # picks are seeds: the curve is theirs where they have pixels; pixels that agree with them fill the rest and
        # set the yardstick (picks alone are too small to show the print's own variability)
        m, sd, res, z, inl = stage_a(C, 3, only=is_pick)
        seed = is_pick | (np.linalg.norm(res, axis=1) / (1.5 * sd[band]) < opts.inlier_z)
        m, sd, res, z, inl = stage_a(C, 3, inl=seed)
    # stage C: the variability's shape, on the final inliers only
    S = np.stack([np.eye(2) * s * s for s in sd])
    if opts.aniso:
        Sb = np.full((nb, 2, 2), np.nan)
        for b in range(nb):
            s = inl & (band == b)
            if s.sum() >= 60:
                q = res[s] - res[s].mean(axis=0)
                Sb[b] = q.T @ q / (len(q) - 1) * 1.04             # z < 3 truncation of a 2-D Gaussian
        okb = np.isfinite(Sb[:, 0, 0])
        if okb.any():
            flat = Sb.reshape(nb, 4)
            for c in range(4):
                flat[:, c] = np.interp(CENTRES, CENTRES[okb], flat[okb, c])
            if opts.pool:
                flat = _lowess(CENTRES, flat, okb.astype(float), opts.span, iters=0)
            Sb = flat.reshape(nb, 2, 2)
            for b in range(nb):
                ev, Vv = np.linalg.eigh((Sb[b] + Sb[b].T) / 2)
                ev = np.maximum(ev, 1e-6)
                ev = np.maximum(ev, ev.max() / MAX_ANISO ** 2)
                Sb[b] = Vv @ np.diag(ev) @ Vv.T + FLOOR_AB ** 2 * np.eye(2)
            S = Sb
            Si = np.linalg.inv(S)[band]
            z = np.sqrt(np.maximum(np.einsum("ni,nij,nj->n", res, Si, res), 0))
    setaside = np.bincount(band, weights=(z >= opts.inlier_z).astype(float), minlength=nb) / np.maximum(counts_all, 1)
    support = np.bincount(band, weights=(z < opts.inlier_z).astype(float), minlength=nb)
    how = "picked (seeds)" if picks is not None else "automatic"
    ref = Reference(m=m, S=S, C=C, support=support, setaside=setaside, how=how, opts=opts, shape=shape,
                    weights=(z < opts.inlier_z).astype(float), sample_idx=idx, notes=notes)
    ref.field_kept = field_kept
    return ref


def reference_ab(ref: Reference, L: np.ndarray) -> np.ndarray:
    """The reference a*, b* at every pixel: what the unpainted print would look like there."""
    h, w = L.shape
    idx = np.arange(h * w)
    P = _phi(idx, (h, w)).reshape(h, w, 2)
    m = np.stack([np.interp(L, CENTRES, ref.m[:, c]) for c in range(2)], axis=-1)
    return (m + _g(L)[..., None] * (P @ ref.C)).astype(np.float32)


SIGMA_C = 2.0      # px at working size: chroma compared at the camera's chroma resolution (4:2:0, chroma NR)
KAPPA = 2.0        # px of chroma-to-lightness misregistration allowed for (subsampling, lateral CA)
ALPHA_EDGE = 0.25  # a*, b* per (L* per px): colour a residual lateral CA puts on a neutral edge


def _blur(x, s):
    return cv2.GaussianBlur(x, (0, 0), s) if s > 0 else x


def departure(ref: Reference, L: np.ndarray, ab: np.ndarray, edges: bool = True) -> Tuple[np.ndarray, np.ndarray]:
    """The departure from the reference (a*, b* units) and its size z in the print's own variability.  With
    ``edges``, both are compared at chroma resolution, and the variability grows where the reference changes fast
    (misregistration) and at strong lightness edges (residual lateral CA)."""
    refab = reference_ab(ref, L)
    band = _band_of(L)
    S = ref.S[band].astype(np.float32)
    if edges:
        ab_b = np.stack([_blur(np.ascontiguousarray(ab[..., c]), SIGMA_C) for c in range(2)], axis=-1)
        rf_b = np.stack([_blur(np.ascontiguousarray(refab[..., c]), SIGMA_C) for c in range(2)], axis=-1)
        r = ab_b - rf_b
        Lb = _blur(L.astype(np.float32), SIGMA_C)
        gy, gx = np.gradient(Lb)
        gL2 = gx * gx + gy * gy
        J = np.stack([np.stack(np.gradient(rf_b[..., c])[::-1], axis=-1) for c in range(2)], axis=-2)   # (h,w,2,2)
        S = S + KAPPA ** 2 * np.einsum("...ij,...kj->...ik", J, J) + (ALPHA_EDGE ** 2 * gL2)[..., None, None] * np.eye(2)
    else:
        r = ab - refab
    Si = np.linalg.inv(S)
    z = np.sqrt(np.maximum(np.einsum("...i,...ij,...j->...", r, Si, r), 0)).astype(np.float32)
    return r.astype(np.float32), z


def presence_alpha(z: np.ndarray, valid: np.ndarray, lo=Z_SHOW[0], hi=Z_SHOW[1]) -> np.ndarray:
    z = cv2.medianBlur(np.nan_to_num(z).astype(np.float32), 3)          # specks: a 3 px median, not a component filter
    a = np.clip((z - lo) / (hi - lo), 0, 1)
    return np.where(valid, a * a * (3 - 2 * a), 0).astype(np.float32)


# ----------------------------------------------------------------------------------------------------------------------
# pictures
# ----------------------------------------------------------------------------------------------------------------------

def lab_to_rgb8(L, ab):
    lab = np.concatenate([L[..., None], ab], axis=-1).astype(np.float32)
    return np.clip(cv2.cvtColor(lab, cv2.COLOR_Lab2RGB) * 255 + 0.5, 0, 255).astype(np.uint8)


def hatch(shape, spacing=9, width=1, angle=1):
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w]
    return ((xx + angle * yy) % spacing) < width


def render(rgb: np.ndarray, L: np.ndarray, ab: np.ndarray, ref: Reference, mk: Dict[str, np.ndarray],
           boost: float = 4.0) -> Dict[str, np.ndarray]:
    r, z = departure(ref, L, ab, edges=ref.opts.edges)
    valid = mk["valid"]
    refab = reference_ab(ref, L)
    out = {"original": np.clip(rgb * 255 + 0.5, 0, 255).astype(np.uint8)}
    # reference: the print as the tool models it unpainted; pixels it set aside hatched, unjudged cross-hatched
    rp = lab_to_rgb8(L, refab)
    zz = cv2.medianBlur(np.nan_to_num(z), 3)
    aside = valid & (zz >= 3.0)
    hh = hatch(L.shape, 10, 2, 1)
    rp[aside & hh] = (rp[aside & hh] * 0.35 + np.array([255, 255, 255]) * 0.65).astype(np.uint8)
    nj = ~valid & (hh | hatch(L.shape, 10, 2, -1))
    rp[nj] = (170, 170, 170)
    out["reference"] = rp
    # boosted around the reference: the print's own tone neutral, departures cored below its variability, then amplified
    core = np.clip((z - 1.0) / 2.0, 0, 1)[..., None]
    out["boosted"] = lab_to_rgb8(L, boost * r * core)
    # presence map: the print in grey, departures in their own hue at fixed chroma, opacity rising from z 2 to 5
    alpha = presence_alpha(z, valid)
    Lc = 32 + 0.55 * L
    grey = lab_to_rgb8(Lc, np.zeros_like(ab)).astype(np.float32)
    ang = np.arctan2(r[..., 1], r[..., 0])
    ov = lab_to_rgb8(np.full(L.shape, 62.0, np.float32),
                     np.stack([58 * np.cos(ang), 58 * np.sin(ang)], axis=-1).astype(np.float32)).astype(np.float32)
    pm = grey * (1 - alpha[..., None]) + ov * alpha[..., None]
    pm[nj] = (205, 205, 205)
    out["presence"] = np.clip(pm, 0, 255).astype(np.uint8)
    out["z"] = z
    out["alpha"] = alpha
    return out


def tone_strip(ref: Reference, width=600, height=36, exaggerate=4.0) -> np.ndarray:
    """The reference tone curve, dark to light: as it is (top), and its colour exaggerated about neutral (bottom).
    Bands with little support are hatched."""
    Ls = np.linspace(3, 99, width).astype(np.float32)
    m = np.stack([np.interp(Ls, CENTRES, ref.m[:, c]) for c in range(2)], axis=-1).astype(np.float32)
    top = lab_to_rgb8(np.tile(Ls, (height // 2, 1)), np.tile(m, (height // 2, 1, 1)))
    bot = lab_to_rgb8(np.tile(np.clip(Ls, 25, 90), (height // 2, 1)), np.tile(exaggerate * m, (height // 2, 1, 1)))
    strip = np.concatenate([top, bot], axis=0)
    sup = np.interp(Ls, CENTRES, ref.support)
    weak = sup < 100
    hh = hatch(strip.shape[:2], 8, 2, 1)
    strip[np.tile(weak, (strip.shape[0], 1)) & hh] = (128, 128, 128)
    return strip


def checks(ref: Reference, L: np.ndarray, ab: np.ndarray, mk: Dict[str, np.ndarray], z: np.ndarray) -> List[str]:
    """Warnings in words (no numbers): what could make this picture wrong."""
    words = []
    names = {"dark": (7, 35), "middle": (35, 70), "light": (70, 100)}
    for nm, (lo, hi) in names.items():
        sel = (CENTRES >= lo) & (CENTRES < hi)
        tot = ref.support[sel].sum() + 1
        if tot < 300:
            words.append(f"few unpainted pixels in the {nm} tones: the reference there is extended, not seen")
        elif ref.setaside[sel].mean() > 0.4:
            words.append(f"much of the {nm} tones departs from the reference: if those areas are painted, the reference "
                         f"there may hold some paint (look for the opposite colour on unpainted {nm} tones); "
                         "picks would settle it")
    if mk["glare"].mean() > 0.002:
        words.append("glare left out (hatched)")
    # a strongly directional variability hides washes along that direction (sheen after AWB, staining, uneven toning)
    for nm, (lo, hi) in names.items():
        sel = np.flatnonzero((CENTRES >= lo) & (CENTRES < hi) & (ref.support > 100))
        if len(sel) < 3:
            continue
        ratios, angles = [], []
        for b in sel:
            ev, Vv = np.linalg.eigh(ref.S[b])
            ratios.append(np.sqrt(ev[1] / ev[0]))
            angles.append(np.degrees(np.arctan2(Vv[1, 1], Vv[0, 1])) % 180)
        if np.median(ratios) > 2.0:
            axis = "yellow-blue" if 45 <= float(np.median(angles)) < 135 else "red-green"
            words.append(f"in the {nm} tones this print's own colour varies most along {axis} (sheen, staining or "
                         f"uneven toning): faint washes in those colours may not show there")
    # split-frame check: does the tone curve differ between halves beyond the fitted field?
    h, w = L.shape
    valid = mk["valid"] & (z < 3)
    r, _ = departure(ref, L, ab, edges=ref.opts.edges)
    for nm, a_, b_ in (("left and right", np.s_[:, : w // 2], np.s_[:, w // 2:]),
                       ("top and bottom", np.s_[: h // 2, :], np.s_[h // 2:, :])):
        da = np.median(r[a_][valid[a_]], axis=0) if valid[a_].any() else np.zeros(2)
        db = np.median(r[b_][valid[b_]], axis=0) if valid[b_].any() else np.zeros(2)
        sd = np.sqrt(np.median(ref.S[:, 0, 0] + ref.S[:, 1, 1]) / 2)
        if np.linalg.norm(da - db) > 0.75 * sd:
            words.append(f"the print's colour differs between {nm} beyond a gentle light gradient: uneven light, a "
                         "stain or a broad wash; picks on both sides would settle it")
    return words


def run(src, picks_boxes=None, box=None, opts: Options = Options(), long_edge=3000, median_px=5):
    rgb8 = load_srgb(src)
    rgb = working(rgb8, long_edge)
    L, ab = to_lab(rgb, median_px)
    mk = masks(rgb, L, box)
    picks = None
    if picks_boxes:
        picks = np.zeros(L.shape, bool)
        for x0, y0, x1, y1 in picks_boxes:
            picks[y0:y1, x0:x1] = True
    Lb = cv2.GaussianBlur(L.astype(np.float32), (0, 0), SIGMA_C)
    gy, gx = np.gradient(Lb)
    ref = fit_reference(L, ab, mk["valid"], picks, opts, grad=np.hypot(gx, gy) if opts.edges else None)
    pics = render(rgb, L, ab, ref, mk)
    words = checks(ref, L, ab, mk, pics["z"])
    return {"rgb": rgb, "L": L, "ab": ab, "masks": mk, "ref": ref, "pics": pics, "words": ref.notes + words}


def montage(res, title: str, out_path, scale=0.5, font_size=18):
    pics = res["pics"]
    tiles = [pics["original"], pics["reference"], pics["boosted"], pics["presence"]]
    labels = ["Original", "Reference: as if unpainted (hatched: set aside)", "Boosted around the reference",
              "Presence map"]
    h, w = tiles[0].shape[:2]
    th, tw = int(h * scale), int(w * scale)
    tiles = [cv2.resize(t, (tw, th), interpolation=cv2.INTER_AREA) for t in tiles]
    strip = tone_strip(res["ref"], width=2 * tw - 20, height=36)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", font_size)
    except OSError:
        font = ImageFont.load_default()
    lines = [title + "   |   Visualisation only - not a measurement   |   reference: " + res["ref"].how] + \
            ["- " + w_ for w_ in res["words"]]
    foot = 30 + 36 + 10 + (font_size + 6) * len(lines) + 10
    canvas = Image.new("RGB", (2 * tw, 2 * th + 2 * (font_size + 8) + foot), "white")
    d = ImageDraw.Draw(canvas)
    for i, (t, lab) in enumerate(zip(tiles, labels)):
        x, y = (i % 2) * tw, (i // 2) * (th + font_size + 8)
        canvas.paste(Image.fromarray(t), (x, y))
        d.text((x + 6, y + th + 2), lab, fill="black", font=font)
    y0 = 2 * th + 2 * (font_size + 8) + 4
    d.text((10, y0), "Reference tone, dark to light (top: as is; bottom: its colour exaggerated about neutral)",
           fill="black", font=font)
    canvas.paste(Image.fromarray(strip), (10, y0 + font_size + 6))
    yl = y0 + font_size + 6 + 36 + 8
    for k, line in enumerate(lines):
        d.text((10, yl + k * (font_size + 6)), line, fill="black", font=font)
    canvas.save(out_path)
