"""The refined design: a prototype of the reference, the feature, the self-checks and the pictures.

Reference for "the print unpainted", per capture:
    expected (a*, b*) at a pixel = m(L*) + s(L*) * P [x, y]
    m(L*)  the print's own tone, paper to shadow: per-band 2-D modes (first round) then robust means, smoothed across
           tones by a kernel smoother whose band weights are Tukey weights (a band whose commonest colour leaves the
           trend of its neighbours is overruled, and that is reported);
    P      a 2 x 2 plane for the light's colour drift across the frame, scaled by s(L*) = (L* + 16) / 116, so a
           drift acts like a change of illuminant (larger in the light tones, smaller in the shadows);
    spread sqrt(s0(L*)^2 + (kappa |grad L*|)^2): the scatter of the reference pixels about the locus, by tone, plus a
           term for colour fringes at edges, both measured on the reference pixels of this capture.
Reference pixels: the user's picks (boxes on areas examined as unpainted) or, with none, every judgeable pixel in the
object box, robustly reweighted (the automatic reference: it assumes unpainted areas are the commonest colour at each
tone).  Departure: z = |v| / spread with v = (a*, b*) - expected.  Shown with opacity smoothstep(z, lo, hi).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from scipy.ndimage import median_filter
from skimage import color

PRESETS = {"low": (3.5, 7.0), "normal": (2.5, 5.0), "high": (2.0, 4.0)}


def smoothstep(x, lo, hi):
    t = np.clip((x - lo) / (hi - lo), 0, 1)
    return t * t * (3 - 2 * t)


def tukey(u, c):
    w = (1 - (u / c) ** 2) ** 2
    return np.where(np.abs(u) < c, w, 0.0)


@dataclass
class Ref:
    grid: np.ndarray            # L* grid
    ma: np.ndarray              # expected a* on the grid
    mb: np.ndarray
    s0: np.ndarray              # spread on the grid
    P: np.ndarray               # 2 x 2: rows a, b; columns x, y
    kappa: float
    cover: Tuple[float, float]  # L* range the reference pixels cover
    band_w: np.ndarray          # cross-band weights (overruled bands low)
    band_n: np.ndarray
    weights: np.ndarray         # per-pixel reference weights (H, W)
    pool: np.ndarray            # pixels the reference could draw on
    notes: List[str] = field(default_factory=list)


def lab_planes(rgb_u8, med=5):
    lab = color.rgb2lab(rgb_u8.astype(np.float32) / 255.0).astype(np.float32)
    L = lab[..., 0]
    a = median_filter(lab[..., 1], size=med) if med > 1 else lab[..., 1]
    b = median_filter(lab[..., 2], size=med) if med > 1 else lab[..., 2]
    return L, a, b


def masks(rgb_u8, L, box=None):
    clipped = (rgb_u8 >= 250).any(axis=2)
    clipped = cv2.dilate(clipped.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    dark = L < 8
    inside = np.ones(L.shape, bool)
    if box is not None:
        inside[:] = False
        x0, y0, x1, y1 = box
        inside[y0:y1, x0:x1] = True
    return clipped, dark, inside


def grad_mag(L):
    Ls = cv2.GaussianBlur(L, (0, 0), 1.0)
    gx = cv2.Sobel(Ls, cv2.CV_32F, 1, 0, ksize=3) / 8.0
    gy = cv2.Sobel(Ls, cv2.CV_32F, 0, 1, ksize=3) / 8.0
    return np.hypot(gx, gy)


def _mode2d(x, y, w, span=12.0, step=0.25, sig_bins=2.0):
    cx, cy = np.median(x), np.median(y)
    ex = np.arange(cx - span, cx + span + step, step)
    ey = np.arange(cy - span, cy + span + step, step)
    h, _, _ = np.histogram2d(x, y, bins=[ex, ey], weights=w)
    h = cv2.GaussianBlur(h.astype(np.float32), (0, 0), sig_bins)
    i, j = np.unravel_index(np.argmax(h), h.shape)
    return ex[i] + step / 2, ey[j] + step / 2


def _kernel_smooth(xk, yk, wk, grid, bw):
    d = (grid[:, None] - xk[None, :]) / bw
    K = np.exp(-0.5 * d ** 2) * wk[None, :]
    s = K.sum(axis=1)
    return (K @ yk) / np.maximum(s, 1e-12), s


def fit_reference(L, a, b, g, pool, band=2.0, bw=6.0, rounds=5, plane=True, gradient=True, c_pix=4.0,
                  c_band=2.5, auto=True, P_fixed=None) -> Ref:
    H, W = L.shape
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    xn, yn = xx / W - 0.5, yy / H - 0.5
    sL = (L + 16.0) / 116.0
    grid = np.arange(0.0, 100.0 + 1e-6, 0.5)
    edges = np.arange(0.0, 100.0 + band, band)
    centres = 0.5 * (edges[:-1] + edges[1:])
    nb = len(centres)
    idx = np.clip(np.digitize(L, edges) - 1, 0, nb - 1)
    w = pool.astype(np.float32)
    P = np.zeros((2, 2), np.float32) if P_fixed is None else np.asarray(P_fixed, np.float32).copy()
    if P_fixed is not None:
        plane = False
    kappa = 0.0
    ma = mb = s0 = None
    band_w = np.ones(nb)
    band_n = np.zeros(nb)
    notes: List[str] = []
    rng = np.random.default_rng(0)
    for r in range(rounds):
        ra = a - sL * (P[0, 0] * xn + P[0, 1] * yn)
        rb = b - sL * (P[1, 0] * xn + P[1, 1] * yn)
        mk = np.full((nb, 2), np.nan)
        sk = np.full(nb, np.nan)
        for k in range(nb):
            m = (idx == k) & (w > 0)
            n = int(m.sum())
            band_n[k] = n
            if n < 60:
                continue
            xa, xb, ww = ra[m], rb[m], w[m]
            if n > 40000:
                sel = rng.choice(n, 40000, replace=False)
                xa, xb, ww = xa[sel], xb[sel], ww[sel]
            if r == 0:
                mk[k] = _mode2d(xa, xb, ww)
            else:
                mk[k] = (np.average(xa, weights=ww), np.average(xb, weights=ww))
            rr = np.hypot(xa - mk[k, 0], xb - mk[k, 1])
            core = rr < np.percentile(rr, 60)
            sk[k] = max(np.median(rr[core]) / 1.1774 * 1.35, 0.35) if core.sum() > 10 else np.nan
        ok = np.isfinite(mk[:, 0]) & np.isfinite(sk)
        if ok.sum() < 3:
            raise ValueError("too few reference pixels to model the print's own tone")
        xk, yka, ykb, nk, sgk = centres[ok], mk[ok, 0], mk[ok, 1], band_n[ok], sk[ok]
        bwk = np.ones(ok.sum())
        for _ in range(6):                         # robust smoothing across tones
            wk = np.sqrt(nk) * bwk
            fa, _ = _kernel_smooth(xk, yka, wk, xk, bw)
            fb, _ = _kernel_smooth(xk, ykb, wk, xk, bw)
            dev = np.hypot(yka - fa, ykb - fb) / sgk
            bwk = tukey(dev, c_band)
            bwk = np.maximum(bwk, 1e-3)
        band_w[:] = 1.0
        band_w[ok] = bwk
        wk = np.sqrt(nk) * bwk
        ma, _ = _kernel_smooth(xk, yka, wk, grid, bw)
        mb, _ = _kernel_smooth(xk, ykb, wk, grid, bw)
        s0, _ = _kernel_smooth(xk, sgk, np.sqrt(nk) * np.maximum(bwk, 0.05), grid, bw)
        Li = np.clip(np.round(L / 0.5).astype(int), 0, len(grid) - 1)
        va = a - ma[Li]
        vb = b - mb[Li]
        if plane:                                   # the light's drift, scaled by lightness
            m = (w > 0)
            sub = np.flatnonzero(m.ravel())
            if len(sub) > 200000:
                sub = rng.choice(sub, 200000, replace=False)
            A = np.stack([(sL * xn).ravel()[sub], (sL * yn).ravel()[sub]], axis=1)
            ww = np.sqrt(w.ravel()[sub])
            P[0] = np.linalg.lstsq(A * ww[:, None], va.ravel()[sub] * ww, rcond=None)[0]
            P[1] = np.linalg.lstsq(A * ww[:, None], vb.ravel()[sub] * ww, rcond=None)[0]
        va = va - sL * (P[0, 0] * xn + P[0, 1] * yn)
        vb = vb - sL * (P[1, 0] * xn + P[1, 1] * yn)
        rr = np.hypot(va, vb)
        sig0 = s0[Li]
        if gradient:                                # colour fringes: scatter growing with edge strength
            m = (w > 0.5)
            gq = g[m]
            if gq.size > 1000:
                qs = np.quantile(gq, np.linspace(0, 1, 13))
                xs, ys = [], []
                for q0, q1 in zip(qs[:-1], qs[1:]):
                    mm = m & (g >= q0) & (g <= q1)
                    if mm.sum() < 100:
                        continue
                    sb = np.median(rr[mm]) / 1.1774
                    s0b = np.median(sig0[mm])
                    xs.append(np.median(g[mm]) ** 2)
                    ys.append(max(sb ** 2 - s0b ** 2, 0.0))
                xs, ys = np.array(xs), np.array(ys)
                kappa = float(np.sqrt(max((xs @ ys) / max(xs @ xs, 1e-12), 0.0)))
        spread = np.sqrt(sig0 ** 2 + (kappa * g) ** 2)
        z = rr / spread
        if auto or r < rounds - 1:
            w = pool * tukey(z, c_pix)
    covered = band_n > 200
    lo = float(centres[covered].min()) if covered.any() else 0.0
    hi = float(centres[covered].max()) if covered.any() else 100.0
    over = (band_w < 0.5) & (band_n > 200)
    if over.any() and auto:
        notes.append("overruled")
    return Ref(grid, ma, mb, s0, P, kappa, (lo, hi), band_w, band_n, w, pool, notes)


def departure(ref: Ref, L, a, b, g):
    H, W = L.shape
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    xn, yn = xx / W - 0.5, yy / H - 0.5
    sL = (L + 16.0) / 116.0
    Li = np.clip(np.round(L / 0.5).astype(int), 0, len(ref.grid) - 1)
    va = a - ref.ma[Li] - sL * (ref.P[0, 0] * xn + ref.P[0, 1] * yn)
    vb = b - ref.mb[Li] - sL * (ref.P[1, 0] * xn + ref.P[1, 1] * yn)
    spread = np.sqrt(ref.s0[Li] ** 2 + (ref.kappa * g) ** 2)
    z = np.hypot(va, vb) / spread
    return va, vb, z


@dataclass
class Result:
    va: np.ndarray
    vb: np.ndarray
    z: np.ndarray
    alpha: np.ndarray
    unjudgeable: np.ndarray
    extrapolated: np.ndarray
    ref: Ref
    warnings: List[str]
    source: str
    L: np.ndarray
    held_out_flag: Optional[np.ndarray] = None


def norm_blur(x, valid, sigma):
    w = valid.astype(np.float32)
    num = cv2.GaussianBlur(np.where(valid, x, 0).astype(np.float32), (0, 0), sigma)
    den = cv2.GaussianBlur(w, (0, 0), sigma)
    return num / np.maximum(den, 1e-3)


def coarse_z(ref: Ref, L, va, vb, g, usable, sigma, band=2.0, bw=6.0):
    """The departure averaged over a neighbourhood (broad, faint washes), in units of the same average's scatter over
    the reference pixels at that tone (so the scale is measured, not assumed)."""
    ca = norm_blur(va, usable, sigma)
    cb = norm_blur(vb, usable, sigma)
    rc = np.hypot(ca, cb)
    gc = cv2.GaussianBlur(g, (0, 0), sigma)
    refpx = ref.pool & (ref.weights > 0.5) & usable
    edges = np.arange(0.0, 100.0 + band, band)
    centres = 0.5 * (edges[:-1] + edges[1:])
    idx = np.clip(np.digitize(L, edges) - 1, 0, len(centres) - 1)
    xs, ys, ns = [], [], []
    for k in range(len(centres)):
        m = refpx & (idx == k)
        if m.sum() < 200:
            continue
        r = rc[m]
        core = r < np.percentile(r, 60)
        xs.append(centres[k])
        ys.append(max(np.median(r[core]) / 1.1774 * 1.35, 0.12))
        ns.append(m.sum())
    xs, ys, ns = np.array(xs), np.array(ys), np.array(ns, float)
    s0c, _ = _kernel_smooth(xs, ys, np.sqrt(ns), ref.grid, bw)
    Li = np.clip(np.round(L / 0.5).astype(int), 0, len(ref.grid) - 1)
    sig = s0c[Li]
    # fringes left after averaging, measured the same way
    kap = 0.0
    gq = gc[refpx]
    if gq.size > 1000:
        qs = np.quantile(gq, np.linspace(0, 1, 13))
        X, Y = [], []
        for q0, q1 in zip(qs[:-1], qs[1:]):
            mm = refpx & (gc >= q0) & (gc <= q1)
            if mm.sum() < 100:
                continue
            X.append(np.median(gc[mm]) ** 2)
            Y.append(max((np.median(rc[mm]) / 1.1774) ** 2 - np.median(sig[mm]) ** 2, 0.0))
        X, Y = np.array(X), np.array(Y)
        kap = float(np.sqrt(max((X @ Y) / max(X @ X, 1e-12), 0.0)))
    return ca, cb, rc / np.sqrt(sig ** 2 + (kap * gc) ** 2)


def run(rgb_u8, picks: Optional[List[Tuple[int, int, int, int]]] = None, box=None, sensitivity="normal",
        plane=True, gradient=True, checks=True, med=5, coarse=True, pick_plane="auto") -> Result:
    L, a, b = lab_planes(rgb_u8, med)
    clipped, dark, inside = masks(rgb_u8, L, box)
    usable = ~clipped & ~dark & inside
    g = grad_mag(L)
    H, W = L.shape
    if picks:
        pool = np.zeros((H, W), bool)
        for (x0, y0, x1, y1) in picks:
            pool[y0:y1, x0:x1] = True
        pool &= usable
        source = "picks"
        P_fixed = None
        if plane and pick_plane == "auto":         # the light's drift from the whole frame; the tone from the picks
            P_fixed = fit_reference(L, a, b, g, usable.copy(), plane=True, gradient=False, rounds=4).P
        ref = fit_reference(L, a, b, g, pool, plane=(plane and pick_plane == "picks"), gradient=gradient,
                            auto=False, P_fixed=P_fixed)
    else:
        pool = usable.copy()
        source = "automatic"
        ref = fit_reference(L, a, b, g, pool, plane=plane, gradient=gradient, auto=True)
    va, vb, z = departure(ref, L, a, b, g)
    z = median_filter(z, size=5)
    lo, hi = PRESETS[sensitivity]
    alpha = smoothstep(z, lo, hi)
    ha, hb = va, vb
    if coarse:
        sc = max(L.shape) / 180.0
        ca, cb, zc = coarse_z(ref, L, va, vb, g, usable, sc)
        ac = smoothstep(zc, lo, hi)
        use_c = ac > alpha
        alpha = np.maximum(alpha, ac)
        ha = np.where(use_c, ca, va)               # the overlay's hue from the scale that showed it
        hb = np.where(use_c, cb, vb)
        z = np.maximum(z, zc)
    unjudgeable = ~usable
    alpha[unjudgeable] = 0.0
    extrapolated = usable & ((L < ref.cover[0] - 2) | (L > ref.cover[1] + 2))
    warnings: List[str] = []
    held = None
    odd = []
    if checks:
        warnings, held, odd = self_checks(rgb_u8, L, a, b, g, usable, ref, z, alpha, picks, source, lo)
    res = Result(va, vb, z, alpha, unjudgeable, extrapolated, ref, warnings, source, L, held)
    res.ha, res.hb = ha, hb
    res.odd = odd
    res.picks = picks
    return res


# -- self-checks: how a viewer knows the reference has gone wrong ---------------------------------------------------------

def _tiles(H, W, n=8):
    yy, xx = np.mgrid[0:H, 0:W]
    return ((yy * n // H) + (xx * n // W)) % 2 == 0


def self_checks(rgb_u8, L, a, b, g, usable, ref: Ref, z, alpha, picks, source, lo):
    H, W = L.shape
    out: List[str] = []
    refpx = ref.pool & (ref.weights > 0.5)
    held = None
    odd = []
    # 1. held out: the reference refitted without half the print (or without each pick) must still describe it
    if source == "automatic":
        t = _tiles(H, W)
        zs = np.full((H, W), np.nan, np.float32)
        for half in (t, ~t):
            r2 = fit_reference(L, a, b, g, ref.pool & half, rounds=3)
            _, _, z2 = departure(r2, L, a, b, g)
            zs[~half] = z2[~half]
        zs = median_filter(np.nan_to_num(zs), size=5)
        held = refpx & (zs > lo)
        share_in = float((refpx & (z > lo)).sum()) / max(refpx.sum(), 1)
        share_out = float(held.sum()) / max(refpx.sum(), 1)
        if share_out > max(0.02, 3 * share_in):
            out.append("Parts of the print taken as unpainted show colour when the reference is made without them: "
                       "the reference does not describe the whole print (light that varies, or tone that varies "
                       "across the print).")
    else:
        boxes = [tuple(p) for p in picks]
        held = np.zeros((H, W), bool)
        for i, (x0, y0, x1, y1) in enumerate(boxes):
            others = np.zeros((H, W), bool)
            for j, (u0, v0, u1, v1) in enumerate(boxes):
                if j != i:
                    others[v0:v1, u0:u1] = True
            others &= usable
            if others.sum() < 500:
                continue
            try:
                r2 = fit_reference(L, a, b, g, others, rounds=3, auto=False)
            except ValueError:
                continue
            _, _, z2 = departure(r2, L, a, b, g)
            this = np.zeros((H, W), bool)
            this[y0:y1, x0:x1] = True
            this &= usable & (L >= r2.cover[0] - 2) & (L <= r2.cover[1] + 2)
            if this.sum() < 100:
                continue
            zz = median_filter(z2, size=5)
            held |= this & (zz > lo)
            if np.median(zz[this]) > 0.6 * lo or (zz[this] > lo).mean() > 0.25:
                odd.append(i + 1)
        if odd:
            out.append(f"Unpainted pick{'s' if len(odd) > 1 else ''} {', '.join(map(str, odd))} disagree"
                       f"{'' if len(odd) > 1 else 's'} with the others: it may hold colour, or the light differs "
                       "there.")
        lo_c, hi_c = ref.cover
        Lu = L[usable]
        if (Lu > hi_c + 2).mean() > 0.05:
            out.append("The picks do not reach the lightest tones: colour there is judged against a guess.")
        if (Lu < lo_c - 2).mean() > 0.05:
            out.append("The picks do not reach the darkest tones: colour there is judged against a guess.")
    # 2. bands overruled: the commonest colour at some tones was set aside
    if "overruled" in ref.notes:
        out.append("At some tones the commonest colour was set aside as not the print's own tone (a large area of "
                   "one colour at those tones?). Check the tone strip; pick unpainted areas if in doubt.")
    # 3. departure that follows tone, not form
    edges = np.arange(0, 101, 5)
    n = 8
    cell = (np.mgrid[0:H, 0:W][0] * n // H) * n + (np.mgrid[0:H, 0:W][1] * n // W)
    shown = alpha > 0.5
    for lo_b, hi_b in zip(edges[:-1], edges[1:]):
        m = usable & (L >= lo_b) & (L < hi_b)
        if m.sum() < 0.02 * usable.sum():
            continue
        share = (shown & m).sum() / m.sum()
        cells_with = np.unique(cell[m])
        cells_dep = np.unique(cell[m & shown])
        spread = len(cells_dep) / max(len(cells_with), 1)
        if share > 0.3 and spread > 0.5:
            out.append("Colour departs at one range of tones all over the print: the reference may not fit those "
                       "tones (or the print is coloured all over at them).")
            break
    # 4. fringes
    if ref.kappa > 1.0:
        out.append("This capture has colour fringes along edges: thin lines of colour along edges are the camera's.")
    # 5. light drift
    drift = float(np.hypot(*ref.P[:, 0]) + np.hypot(*ref.P[:, 1]))
    if drift > 3.0:
        out.append("The light's colour drifts across the frame (see the expected-tone picture); the tool allows for an "
                   "even drift only, so soft colour spanning the frame is the light's.")
    return out, held, odd


# -- pictures ------------------------------------------------------------------------------------------------------------

def lab2srgb_u8(L, a, b):
    rgb = color.lab2rgb(np.stack([L, a, b], axis=-1).astype(np.float64))
    return np.round(np.clip(rgb, 0, 1) * 255).astype(np.uint8)


def hatch(img, mask, step=7, colour=(150, 150, 150)):
    H, W = mask.shape
    yy, xx = np.mgrid[0:H, 0:W]
    lines = ((xx + yy) % step) < 2
    out = img.copy()
    out[mask & lines] = colour
    return out


def vivid(ang):
    """A vivid sRGB colour (0-255 float) for each departure direction: the CIELAB hue, brightened to full value so a
    yellow reads yellow (not olive) and a blue stays blue."""
    rgb = color.lab2rgb(np.stack([np.full_like(ang, 62.0), 58 * np.cos(ang), 58 * np.sin(ang)], -1).astype(np.float64))
    rgb = np.clip(rgb, 1e-4, 1)
    return (rgb / rgb.max(axis=-1, keepdims=True) * 255).astype(np.float32)


def expected(res: Result):
    """The expected (a*, b*) of the unpainted print at every pixel: the tone locus plus the light's drift."""
    L = res.L
    H, W = L.shape
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    xn, yn = xx / W - 0.5, yy / H - 0.5
    sL = (L + 16.0) / 116.0
    Li = np.clip(np.round(L / 0.5).astype(int), 0, len(res.ref.grid) - 1)
    P = res.ref.P
    ea = res.ref.ma[Li] + sL * (P[0, 0] * xn + P[0, 1] * yn)
    eb = res.ref.mb[Li] + sL * (P[1, 0] * xn + P[1, 1] * yn)
    return ea, eb


def render(rgb_u8, res: Result, boost=4.0, picks=None, odd=()):
    """Three pictures beside the capture.  B + D = the capture's colour amplified: D is the part the tool expects of
    the print unpainted, B the part it does not."""
    L = res.L
    k = boost
    # B: the print's own tone neutralised, departures amplified (unpainted areas should be grey)
    p2 = lab2srgb_u8(L, np.clip(k * res.va, -90, 90), np.clip(k * res.vb, -90, 90))
    p2 = hatch(p2, res.unjudgeable)
    # C: grey print, colour laid where it departs, hue from the departure's direction
    grey = lab2srgb_u8(30 + 0.55 * L, np.zeros_like(L), np.zeros_like(L)).astype(np.float32)
    ang = np.arctan2(getattr(res, "hb", res.vb), getattr(res, "ha", res.va))
    al = res.alpha[..., None]
    p3 = np.round(grey * (1 - al) + vivid(ang) * al).astype(np.uint8)
    p3 = hatch(p3, res.unjudgeable)
    p3 = hatch(p3, res.extrapolated & (res.alpha > 0.2), step=11, colour=(235, 235, 235))
    # D: the print as the tool expects it unpainted, its own tone amplified (tone by lightness, the light's drift)
    ea, eb = expected(res)
    p4 = lab2srgb_u8(L, np.clip(k * ea, -90, 90), np.clip(k * eb, -90, 90))
    if picks:
        for i, (x0, y0, x1, y1) in enumerate(picks):
            col = (240, 120, 30) if (i + 1) in odd else (40, 210, 230)
            cv2.rectangle(p4, (int(x0), int(y0)), (int(x1) - 1, int(y1) - 1), col, 3)
            cv2.putText(p4, str(i + 1), (int(x0) + 4, int(y0) + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.8, col, 2)
    return p2, p3, p4


def tone_strip(ref: Ref, width, height=60, boost=4.0):
    """The reference from paper (left) to shadow (right): top row the expected colour boosted (a neutral print is a
    grey strip; a warm one goes warm), bottom row as the tone itself; hatched where the reference pixels do not reach;
    marked where the commonest colour was overruled."""
    Ls = np.linspace(97, 8, width)
    Li = np.clip(np.round(Ls / 0.5).astype(int), 0, len(ref.grid) - 1)
    ma, mb = ref.ma[Li], ref.mb[Li]
    top = lab2srgb_u8(np.tile(np.full_like(Ls, 65.0), (height // 2, 1)), np.tile(boost * ma, (height // 2, 1)),
                      np.tile(boost * mb, (height // 2, 1)))
    bot = lab2srgb_u8(np.tile(Ls, (height // 2, 1)), np.tile(ma, (height // 2, 1)), np.tile(mb, (height // 2, 1)))
    strip = np.concatenate([top, bot], axis=0)
    outside = (Ls < ref.cover[0] - 2) | (Ls > ref.cover[1] + 2)
    m = np.tile(outside, (height, 1))
    strip = hatch(strip, m, step=6, colour=(255, 255, 255))
    edges = np.arange(0.0, 102.0, 2.0)
    centres = 0.5 * (edges[:-1] + edges[1:])
    over = (ref.band_w < 0.5) & (ref.band_n > 200)
    for c in centres[over]:
        x = int(round((97 - c) / (97 - 8) * (width - 1)))
        if 0 <= x < width:
            strip[:6, max(x - 2, 0):x + 3] = (240, 120, 30)
    return strip
