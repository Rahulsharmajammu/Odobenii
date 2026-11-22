"""Handpaint visualiser: a prototype of the recommended reference, departure, self-checks and pictures.

What the print would look like unpainted, per capture:
    expected (a*, b*) at a pixel = m(L*) + s(L*) * P [x, y]
* m(L*), the print's own tone from paper to shadow, is VOTED across places: at each lightness band, every tile of the
  frame (or every pick) with enough pixels at that band gives one vote, its median colour; the band's tone is the
  median of the votes.  Paint, stains and silvering are local, so they hold few votes; the print's tone is everywhere.
  The bands are then smoothed across lightness with robust weights; a band whose vote leaves its neighbours' trend is
  overruled, and the picture says so.
* P, the light's colour drift across the frame (an even drift, scaled by s(L*) = (L* + 16) / 116 so it acts like a
  change of illuminant), is fitted to the same votes, so a large painted area cannot tilt it much.
* The scale is the capture's own scatter about that expectation, measured over the whole judgeable frame (robustly):
  the 90th percentile of the distance at each lightness, widened where the edges are strong (colour fringes).  Compression
  error is heavy-tailed and blocky, so a quantile is used, not a Gaussian scale.
Departure: v = (a*, b*) - expected; z = |v| / scale, at two scales (a 5 px median for touches; a neighbourhood
average for broad, faint washes, with its own measured scale).  Opacity = smoothstep(z, 1, 2) (normal).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

import cv2
import numpy as np
from scipy.ndimage import median_filter
from skimage import color

PRESETS = {"low": (1.25, 2.5), "normal": (1.0, 2.0), "high": (0.85, 1.7)}
BAND = 2.0          # L* band width
BW = 6.0            # L* bandwidth of the smoothing across tones
TILES = 10          # tiles per side for the votes
MIN_VOTE_PX = 25    # pixels a tile needs at a band to vote
SPREAD_FLOOR = 0.6  # CIELAB units: about an 8-bit step near neutral at mid-tones
COARSE_FLOOR = 0.25
Q = 90.0            # the scale is this percentile of the distance from the expected colour
OVERRULE_C = 3.0    # a tone's vote is set aside (Tukey) as it nears this many pixel scales from its neighbours' trend


def smoothstep(x, lo, hi):
    t = np.clip((x - lo) / (hi - lo), 0, 1)
    return t * t * (3 - 2 * t)


def tukey(u, c):
    return np.where(np.abs(u) < c, (1 - (u / c) ** 2) ** 2, 0.0)


@dataclass
class Ref:
    grid: np.ndarray
    ma: np.ndarray
    mb: np.ndarray
    s: np.ndarray               # fine scale on the grid
    P: np.ndarray               # light's drift (rows a, b; columns x, y)
    kappa: float                # edge widening
    cover: Tuple[float, float]  # lightness the votes reach
    band_w: np.ndarray
    band_votes: np.ndarray
    weights: np.ndarray         # per-pixel weight as part of the unpainted print
    pool: np.ndarray            # pixels the tone may be drawn from (picks, or the judgeable frame)
    source: str
    notes: List[str] = field(default_factory=list)


def lab_planes(rgb_u8, med=5):
    lab = color.rgb2lab(rgb_u8.astype(np.float32) / 255.0).astype(np.float32)
    L = lab[..., 0]
    a = median_filter(lab[..., 1], size=med) if med > 1 else lab[..., 1]
    b = median_filter(lab[..., 2], size=med) if med > 1 else lab[..., 2]
    return L, a, b


def judgeable(rgb_u8, L, box=None):
    clipped = cv2.dilate((rgb_u8 >= 250).any(axis=2).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    dark = L < 8
    inside = np.ones(L.shape, bool)
    if box is not None:
        inside[:] = False
        x0, y0, x1, y1 = box
        inside[y0:y1, x0:x1] = True
    return ~clipped & ~dark & inside, clipped, dark, inside


def grad_mag(L):
    Ls = cv2.GaussianBlur(L, (0, 0), 1.0)
    gx = cv2.Sobel(Ls, cv2.CV_32F, 1, 0, ksize=3) / 8.0
    gy = cv2.Sobel(Ls, cv2.CV_32F, 0, 1, ksize=3) / 8.0
    return np.hypot(gx, gy)


LOCAL_LINEAR = True


def _smooth(xk, yk, wk, grid, bw=BW):
    """Kernel smoothing of yk(xk) onto grid: local-linear (no flattening at the ends of the tonal range), falling back
    to a local mean where the window is too narrow to fit a slope."""
    d = (xk[None, :] - grid[:, None])
    K = np.exp(-0.5 * (d / bw) ** 2) * wk[None, :]
    s0 = K.sum(axis=1)
    nw = (K @ yk) / np.maximum(s0, 1e-12)
    if not LOCAL_LINEAR:
        return nw
    s1 = (K * d).sum(axis=1)
    s2 = (K * d * d).sum(axis=1)
    t0 = K @ yk
    t1 = (K * d) @ yk
    den = s0 * s2 - s1 * s1
    ok = den > 1e-9 * np.maximum(s0 * s2, 1e-30)
    ll = np.where(ok, (s2 * t0 - s1 * t1) / np.where(ok, den, 1.0), nw)
    # beyond the data, hold the end value rather than extrapolate a slope
    lo, hi = xk.min(), xk.max()
    ll = np.where(grid < lo, np.interp(lo, grid, ll), ll)
    ll = np.where(grid > hi, np.interp(hi, grid, ll), ll)
    return ll


def _group_medians(key, va, vb, extra):
    """Median of va, vb and mean of each extra array per key (sorted grouping)."""
    order = np.argsort(key, kind="stable")
    k = key[order]
    cuts = np.flatnonzero(np.diff(k)) + 1
    starts = np.r_[0, cuts]
    ends = np.r_[cuts, len(k)]
    A, B = va[order], vb[order]
    E = [e[order] for e in extra]
    out = []
    for s0, e0 in zip(starts, ends):
        out.append((k[s0], e0 - s0, float(np.median(A[s0:e0])), float(np.median(B[s0:e0])),
                    *[float(np.mean(x[s0:e0])) for x in E]))
    return out


class Frame:
    """Coordinates shared by the fits."""

    def __init__(self, L):
        H, W = L.shape
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        self.H, self.W = H, W
        self.xn, self.yn = xx / W - 0.5, yy / H - 0.5
        self.sL = (L + 16.0) / 116.0
        self.edges = np.arange(0.0, 100.0 + BAND, BAND)
        self.centres = 0.5 * (self.edges[:-1] + self.edges[1:])
        self.idx = np.clip(np.digitize(L, self.edges) - 1, 0, len(self.centres) - 1)
        self.tile = ((yy * TILES // H) * TILES + (xx * TILES // W)).astype(np.int64)
        self.grid = np.arange(0.0, 100.0 + 1e-6, 0.5)
        self.Li = np.clip(np.round(L / 0.5).astype(int), 0, len(self.grid) - 1)


FRINGE = True


def radial_derivative(L):
    """r * dL/dr about the frame centre: lateral colour (channels scaled about the centre) puts colour in proportion to
    it."""
    H, W = L.shape
    Ls = cv2.GaussianBlur(L, (0, 0), 1.0)
    gx = cv2.Sobel(Ls, cv2.CV_32F, 1, 0, ksize=3) / 8.0
    gy = cv2.Sobel(Ls, cv2.CV_32F, 0, 1, ksize=3) / 8.0
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    return (gx * (xx - W / 2) + gy * (yy - H / 2)) / max(H, W)


def fit_reference(F: Frame, a, b, g, pool, spread_pool, places=None, rounds=4, plane=True, P_fixed=None,
                  edge_term=True, source="automatic", rdL=None, fill=None) -> Ref:
    """``places`` (H, W) int labels the voters (tiles, or picks); default the tiles.  ``fill`` = (ma, mb) of an
    automatic reference: at tones no voter reaches, the tone is taken from it instead of interpolated."""
    nb = len(F.centres)
    voters = F.tile if places is None else places
    nv = int(voters.max()) + 1
    w = pool.astype(np.float32)
    P = np.zeros((2, 2)) if P_fixed is None else np.asarray(P_fixed, float).copy()
    fit_plane = plane and P_fixed is None
    s_grid = np.full(len(F.grid), 2.0)
    kappa = 0.0
    band_w = np.ones(nb)
    votes = np.zeros(nb)
    ma = mb = None
    notes: List[str] = []
    rng = np.random.default_rng(0)
    for r in range(rounds):
        ra = a - F.sL * (P[0, 0] * F.xn + P[0, 1] * F.yn)
        rb = b - F.sL * (P[1, 0] * F.xn + P[1, 1] * F.yn)
        sel = (w > 0.5) & pool
        key = F.idx[sel].astype(np.int64) * nv + voters[sel]
        groups = _group_medians(key, ra[sel], rb[sel], [F.xn[sel], F.yn[sel], F.sL[sel]])
        groups = [gq for gq in groups if gq[1] >= MIN_VOTE_PX]
        if not groups:
            raise ValueError("too few reference pixels to model the print's own tone")
        gk = np.array([gq[0] // nv for gq in groups])
        gm = np.array([[gq[2], gq[3]] for gq in groups])
        gxy = np.array([[gq[4], gq[5], gq[6]] for gq in groups])
        bm = np.full((nb, 2), np.nan)
        bsc = np.full(nb, np.nan)
        votes[:] = 0
        split = np.zeros(nb)
        s_now = np.interp(F.centres, F.grid, s_grid)
        for k in np.unique(gk):
            m = gk == k
            bm[k] = np.median(gm[m], axis=0)
            votes[k] = m.sum()
            d = np.hypot(*(gm[m] - bm[k]).T)
            bsc[k] = max(np.median(d) / 1.1774 if m.sum() >= 3 else 0.0, 0.3)
            if m.sum() >= 4 and r:                              # places disagree: a share of votes far off the median
                split[k] = float((d > 1.5 * max(s_now[k], SPREAD_FLOOR)).mean())
        ok = np.isfinite(bm[:, 0])
        xk, yk, nk, sk = F.centres[ok], bm[ok], votes[ok], bsc[ok]
        if len(xk) < 2:
            raise ValueError("the reference covers too little of the tonal range")
        bwk = np.ones(len(xk))
        s_band = np.interp(xk, F.grid, s_grid)                  # the capture's pixel-level scale at each tone
        for _ in range(6):                                      # robust smoothing across tones: a tone is overruled
            wk = np.sqrt(nk) * bwk                              # only where its vote would itself show as colour
            fa = _smooth(xk, yk[:, 0], wk, xk)
            fb = _smooth(xk, yk[:, 1], wk, xk)
            dev = np.hypot(yk[:, 0] - fa, yk[:, 1] - fb) / np.maximum(s_band, SPREAD_FLOOR)
            bwk = np.maximum(tukey(dev, OVERRULE_C), 1e-3)
        band_w[:] = 1.0
        band_w[ok] = bwk
        wk = np.sqrt(nk) * bwk
        ma = _smooth(xk, yk[:, 0], wk, F.grid)
        mb = _smooth(xk, yk[:, 1], wk, F.grid)
        own = np.min(np.abs(F.grid[:, None] - xk[None, :]), axis=1)        # L* to the nearest tone with a vote
        if fill is not None:                                    # picks decide where they reach; the automatic votes
            wv = np.clip(1.0 - (own - 2.0) / 4.0, 0.0, 1.0)     # fill the tones they miss (blended over 4 L*)
            ma = wv * ma + (1 - wv) * fill[0]
            mb = wv * mb + (1 - wv) * fill[1]
        if fit_plane:                                           # the light's drift, from the votes
            gl = np.clip(np.round(F.centres[gk] / 0.5).astype(int), 0, len(F.grid) - 1)
            ra_g = gm[:, 0] + gxy[:, 2] * (P[0, 0] * gxy[:, 0] + P[0, 1] * gxy[:, 1]) - ma[gl]
            rb_g = gm[:, 1] + gxy[:, 2] * (P[1, 0] * gxy[:, 0] + P[1, 1] * gxy[:, 1]) - mb[gl]
            A = np.stack([gxy[:, 2] * gxy[:, 0], gxy[:, 2] * gxy[:, 1]], axis=1)
            ww = np.ones(len(A))
            for _ in range(6):
                Pa = np.linalg.lstsq(A * ww[:, None], ra_g * ww, rcond=None)[0]
                Pb = np.linalg.lstsq(A * ww[:, None], rb_g * ww, rcond=None)[0]
                res = np.hypot(ra_g - A @ Pa, rb_g - A @ Pb)
                sc = max(np.median(res) / 1.1774, 0.2)
                ww = np.sqrt(tukey(res / sc, 4.0)) + 1e-6
            P = np.array([Pa, Pb])
        va = a - ma[F.Li] - F.sL * (P[0, 0] * F.xn + P[0, 1] * F.yn)
        vb = b - mb[F.Li] - F.sL * (P[1, 0] * F.xn + P[1, 1] * F.yn)
        if rdL is not None:                                     # lateral colour, fitted on the frame and removed
            m = spread_pool & (np.abs(rdL) > np.quantile(np.abs(rdL[spread_pool]), 0.8))
            if r:
                m &= (w > 0.5) | ~pool
            sub = np.flatnonzero(m.ravel())
            if len(sub) > 200000:
                sub = rng.choice(sub, 200000, replace=False)
            x = rdL.ravel()[sub].astype(np.float64)
            ca = float(np.dot(x, va.ravel()[sub]) / max(np.dot(x, x), 1e-9))
            cb = float(np.dot(x, vb.ravel()[sub]) / max(np.dot(x, x), 1e-9))
            fringe = (ca, cb)
            va = va - ca * rdL
            vb = vb - cb * rdL
        else:
            fringe = (0.0, 0.0)
        rr = np.hypot(va, vb)
        # the scale: the capture's own scatter about the expectation, by lightness, over the whole judgeable frame
        prev_scale = np.sqrt(s_grid[F.Li] ** 2 + (kappa * g) ** 2)
        spool = spread_pool & (rr / prev_scale < (2.0 if r else 50.0))   # trim what is plainly not unpainted print
        low_g = g < np.quantile(g[spread_pool], 0.7)
        xs, ys, ns = [], [], []
        for k in range(nb):
            m = spool & low_g & (F.idx == k)
            n = int(m.sum())
            if n < 200:
                continue
            x = rr[m]
            if n > 50000:
                x = x[rng.choice(n, 50000, replace=False)]
            xs.append(F.centres[k])
            ys.append(max(np.percentile(x, Q), SPREAD_FLOOR))
            ns.append(n)
        xs, ys, ns = np.array(xs), np.array(ys), np.array(ns, float)
        s_grid = _smooth(xs, ys, np.sqrt(ns), F.grid)
        if edge_term:
            m = spool
            qs = np.quantile(g[m], np.linspace(0.5, 1.0, 9))
            X, Y = [], []
            for q0, q1 in zip(qs[:-1], qs[1:]):
                mm = m & (g >= q0) & (g <= q1)
                if mm.sum() < 200:
                    continue
                X.append(np.median(g[mm]) ** 2)
                Y.append(max(np.percentile(rr[mm], Q) ** 2 - np.median(s_grid[F.Li][mm]) ** 2, 0.0))
            X, Y = np.array(X), np.array(Y)
            kappa = float(np.sqrt(max((X @ Y) / max(X @ X, 1e-12), 0.0))) if len(X) else 0.0
        scale = np.sqrt(s_grid[F.Li] ** 2 + (kappa * g) ** 2)
        z = rr / scale
        w = pool * tukey(z, 2.0)
    covered = votes > 0
    lo = float(F.centres[covered].min()) if covered.any() else 0.0
    hi = float(F.centres[covered].max()) if covered.any() else 100.0
    if ((band_w < 0.5) & (votes >= 3)).any():
        notes.append("overruled")
    ref = Ref(F.grid, ma, mb, s_grid, P, kappa, (lo, hi), band_w, votes, w, pool, source, notes)
    ref.fringe = fringe
    ref.filled = (own > 4.0) if fill is not None else np.zeros(len(F.grid), bool)
    ref.split = split
    return ref


def covered(ref: Ref, reach=4.0):
    """True on the L* grid where a band with votes lies within ``reach`` L*: elsewhere (beyond the ends, or in a gap
    between picks) the expected tone is a guess."""
    centres = np.arange(1.0, 100.0, 2.0)[: len(ref.band_votes)]
    have = centres[ref.band_votes > 0]
    if not len(have):
        return np.zeros(len(ref.grid), bool)
    return np.min(np.abs(ref.grid[:, None] - have[None, :]), axis=1) <= reach


def expected(F: Frame, ref: Ref, rdL=None):
    ea = ref.ma[F.Li] + F.sL * (ref.P[0, 0] * F.xn + ref.P[0, 1] * F.yn)
    eb = ref.mb[F.Li] + F.sL * (ref.P[1, 0] * F.xn + ref.P[1, 1] * F.yn)
    fr = getattr(ref, "fringe", (0.0, 0.0))
    if rdL is not None and fr != (0.0, 0.0):
        ea = ea + fr[0] * rdL
        eb = eb + fr[1] * rdL
    return ea, eb


def norm_blur(x, valid, sigma):
    num = cv2.GaussianBlur(np.where(valid, x, 0).astype(np.float32), (0, 0), sigma)
    den = cv2.GaussianBlur(valid.astype(np.float32), (0, 0), sigma)
    return num / np.maximum(den, 1e-3)


def coarse(F: Frame, ref: Ref, va, vb, g, usable, spread_pool, sigma):
    ca, cb = norm_blur(va, usable, sigma), norm_blur(vb, usable, sigma)
    rc = np.hypot(ca, cb)
    gc = cv2.GaussianBlur(g, (0, 0), sigma)
    m0 = spread_pool & (ref.weights > 0.5)
    xs, ys, ns = [], [], []
    for k in range(len(F.centres)):
        m = m0 & (F.idx == k)
        if m.sum() < 400:
            continue
        xs.append(F.centres[k])
        ys.append(max(np.percentile(rc[m], Q), COARSE_FLOOR))
        ns.append(m.sum())
    sc = _smooth(np.array(xs), np.array(ys), np.sqrt(np.array(ns, float)), F.grid)[F.Li]
    qs = np.quantile(gc[m0], np.linspace(0.5, 1.0, 9))
    X, Y = [], []
    for q0, q1 in zip(qs[:-1], qs[1:]):
        mm = m0 & (gc >= q0) & (gc <= q1)
        if mm.sum() < 200:
            continue
        X.append(np.median(gc[mm]) ** 2)
        Y.append(max(np.percentile(rc[mm], Q) ** 2 - np.median(sc[mm]) ** 2, 0.0))
    X, Y = np.array(X), np.array(Y)
    kap = float(np.sqrt(max((X @ Y) / max(X @ X, 1e-12), 0.0))) if len(X) else 0.0
    return ca, cb, rc / np.sqrt(sc ** 2 + (kap * gc) ** 2)


@dataclass
class Result:
    L: np.ndarray
    va: np.ndarray
    vb: np.ndarray
    ha: np.ndarray
    hb: np.ndarray
    z: np.ndarray
    alpha: np.ndarray
    unjudgeable: np.ndarray
    extrapolated: np.ndarray
    ref: Ref
    F: Frame
    warnings: List[str]
    picks: Optional[list] = None
    odd: Sequence[int] = ()
    held: Optional[np.ndarray] = None


MIN_PICK_PX = 100   # pixels a pick needs at a tone to vote there
PICK_BW = 8.0       # L* bandwidth of a pick correction
PICK_REACH = 6.0    # a correction fades to nothing this far (L*) beyond the tones the picks reach
PICK_SHRINK = 1.0   # a pick moves the tone only by what exceeds this many scales (0: picks always anchor)


def pick_correction(F: Frame, auto: Ref, a, b, usable, places, rdL=None, exclude=None):
    """The picks as anchors: each pick votes, at each tone it covers, the median of its pixels' departure from the
    automatic expectation; the votes are smoothed across tones and fade beyond the tones the picks reach.  Returns the
    correction (ca, cb) on the L* grid, the reach on the grid, and the votes per band."""
    ea, eb = expected(F, auto, rdL)
    da, db = a - ea, b - eb
    nb = len(F.centres)
    xs, ya, yb, ns = [], [], [], []
    votes = np.zeros(nb)
    for i in range(int(places.max()) + 1):
        if exclude is not None and i == exclude:
            continue
        m0 = usable & (places == i)
        for k in np.unique(F.idx[m0]):
            m = m0 & (F.idx == k)
            if m.sum() < MIN_PICK_PX:
                continue
            xs.append(F.centres[k]); ya.append(np.median(da[m])); yb.append(np.median(db[m])); ns.append(m.sum())
            votes[k] += 1
    if not xs:
        return np.zeros(len(F.grid)), np.zeros(len(F.grid)), np.zeros(len(F.grid), bool), votes
    xs, ya, yb, ns = map(np.asarray, (xs, ya, yb, ns))
    w = np.sqrt(ns.astype(float))
    ca = _smooth(xs, ya, w, F.grid, PICK_BW)
    cb = _smooth(xs, yb, w, F.grid, PICK_BW)
    dist = np.min(np.abs(F.grid[:, None] - xs[None, :]), axis=1)
    fade = np.clip(1.0 - (dist - 2.0) / PICK_REACH, 0.0, 1.0)
    if PICK_SHRINK:                           # picks override only where they disagree with the automatic reference by
        m = np.hypot(ca, cb)                  # more than the capture's own scale (a local pick bias does not move it)
        k = np.clip(m - PICK_SHRINK * auto.s, 0, None) / np.maximum(m, 1e-6)
        ca, cb = ca * k, cb * k
    return ca * fade, cb * fade, dist <= 4.0, votes


def anchor_to_picks(F: Frame, auto: Ref, a, b, usable, places, rdL=None) -> Ref:
    ca, cb, reach, votes = pick_correction(F, auto, a, b, usable, places, rdL)
    ref = Ref(F.grid, auto.ma + ca, auto.mb + cb, auto.s, auto.P, auto.kappa, auto.cover, auto.band_w, auto.band_votes,
              (places >= 0).astype(np.float32), usable & (places >= 0), "picks", list(auto.notes))
    ref.fringe = getattr(auto, "fringe", (0.0, 0.0))
    ref.filled = ~reach                       # tones the picks do not reach: the automatic reference there
    ref.pick_votes = votes
    ref.auto = auto
    return ref


def run(rgb_u8, picks=None, box=None, sensitivity="normal", two_scales=True, plane=True, edge_term=True,
        checks=True, phone=False, fringe=None) -> Result:
    L, a, b = lab_planes(rgb_u8)
    usable, clipped, dark, inside = judgeable(rgb_u8, L, box)
    g = grad_mag(L)
    F = Frame(L)
    rdL = radial_derivative(L) if (FRINGE if fringe is None else fringe) else None
    if picks:
        places = np.full(L.shape, -1, np.int64)
        for i, (x0, y0, x1, y1) in enumerate(picks):
            places[y0:y1, x0:x1] = i
        auto = fit_reference(F, a, b, g, usable, usable, plane=plane, edge_term=edge_term, rdL=rdL)
        ref = anchor_to_picks(F, auto, a, b, usable, places, rdL)
    else:
        ref = fit_reference(F, a, b, g, usable, usable, plane=plane, edge_term=edge_term, rdL=rdL)
    ea, eb = expected(F, ref, rdL)
    va, vb = a - ea, b - eb
    scale = np.sqrt(ref.s[F.Li] ** 2 + (ref.kappa * g) ** 2)
    z = median_filter(np.hypot(va, vb) / scale, size=5)
    lo, hi = PRESETS[sensitivity]
    alpha = smoothstep(z, lo, hi)
    ha, hb = va, vb
    if two_scales:
        ca, cb, zc = coarse(F, ref, va, vb, g, usable, usable, max(L.shape) / 180.0)
        ac = smoothstep(zc, lo, hi)
        use = ac > alpha
        alpha = np.maximum(alpha, ac)
        ha, hb = np.where(use, ca, va), np.where(use, cb, vb)
        z = np.maximum(z, zc)
    alpha[~usable] = 0.0
    extrap = usable & ~covered(ref)[F.Li] & ~getattr(ref, "filled", np.zeros(len(F.grid), bool))[F.Li]
    res = Result(L, va, vb, ha, hb, z, alpha, ~usable, extrap, ref, F, [], picks)
    res.rdL = rdL
    if checks:
        res.warnings, res.held, res.odd = self_checks(res, a, b, g, usable, picks, lo, phone)
    return res


# -- how the viewer knows the reference has gone wrong -------------------------------------------------------------------

def self_checks(res: Result, a, b, g, usable, picks, lo, phone=False):
    F, ref, L = res.F, res.ref, res.L
    H, W = L.shape
    out: List[str] = []
    odd: List[int] = []
    held = np.zeros((H, W), bool)
    refpx = ref.pool & (ref.weights > 0.5)
    if not picks:
        # left out: refit on alternate tiles; each half must still be described by the other half's reference
        chk = (((F.tile // TILES) + (F.tile % TILES)) % 2) == 0
        zs = np.zeros((H, W), np.float32)
        for half in (chk, ~chk):
            r2 = fit_reference(F, a, b, g, usable & half, usable & half, rounds=3, P_fixed=None, edge_term=True,
                               rdL=res.rdL)
            ea, eb = expected(F, r2, res.rdL)
            sc = np.sqrt(r2.s[F.Li] ** 2 + (r2.kappa * g) ** 2)
            zz = np.hypot(a - ea, b - eb) / sc
            zs[~half] = zz[~half]
        zs = median_filter(zs, size=5)
        held = refpx & (zs > lo) & ~(res.z > lo)
        if held.sum() > 0.03 * max(refpx.sum(), 1):
            out.append("Parts of the print taken as unpainted show colour when the reference is made without them: "
                       "the print's own tone is not the same everywhere (light, yellowing or toning that varies).")
    else:
        places = np.full((H, W), -1, np.int64)
        for i, (x0, y0, x1, y1) in enumerate(picks):
            places[y0:y1, x0:x1] = i
        auto = getattr(ref, "auto", ref)
        for i in range(len(picks)):
            this = usable & (places == i)
            if this.sum() < 100:
                continue
            ca, cb, reach, _ = pick_correction(F, auto, a, b, usable, places, res.rdL, exclude=i)
            r2 = Ref(F.grid, auto.ma + ca, auto.mb + cb, auto.s, auto.P, auto.kappa, auto.cover, auto.band_w,
                     auto.band_votes, auto.weights, auto.pool, "picks")
            r2.fringe = getattr(auto, "fringe", (0.0, 0.0))
            ea, eb = expected(F, r2, res.rdL)
            zz = median_filter(np.hypot(a - ea, b - eb) / np.sqrt(r2.s[F.Li] ** 2 + (r2.kappa * g) ** 2), size=5)
            held |= this & (zz > lo)
            if (zz[this] > lo).mean() > 0.3:
                odd.append(i + 1)
        if odd:
            s = "s" if len(odd) > 1 else ""
            out.append(f"Unpainted pick{s} {', '.join(map(str, odd))} disagree{'' if s else 's'} in colour with the "
                       "reference made without it: it may hold colour, or the print's tone or the light differs there.")
        unc = usable & getattr(ref, "filled", ~covered(ref))[F.Li]
        if unc.sum() > 0.05 * usable.sum():
            Lu = L[unc]
            where = []
            if (Lu > 70).mean() > 0.2:
                where.append("light")
            if ((Lu >= 30) & (Lu <= 70)).mean() > 0.2:
                where.append("middle")
            if (Lu < 30).mean() > 0.2:
                where.append("dark")
            out.append(f"The picks miss some of the {' and '.join(where) or 'tonal'} tones: there the automatic "
                       "reference is used (dotted on the tone strip). Add a pick at those tones to decide them.")
    if "overruled" in ref.notes:
        out.append("At some tones the commonest colour was overruled as not the print's own (marked on the tone strip):"
                   " a large area of one colour at those tones?")
    # departure that follows tone, not form
    shown = res.alpha > 0.5
    cellid = F.tile
    for lo_b in range(0, 100, 5):
        m = usable & (L >= lo_b) & (L < lo_b + 5)
        if m.sum() < 0.02 * usable.sum():
            continue
        share = (shown & m).sum() / m.sum()
        spread = len(np.unique(cellid[m & shown])) / max(len(np.unique(cellid[m])), 1)
        if share > 0.3 and spread > 0.5:
            out.append("Colour departs at one range of tones all over the print: the expected tone may be wrong there "
                       "(or the print is coloured all over at those tones).")
            break
    if ref.kappa > 0.8:
        out.append("This capture has colour fringes along edges; the scale is widened there, but thin lines of colour "
                   "along edges are the camera's.")
    if np.abs(ref.P).sum() > 3.0:
        out.append("The light's colour drifts across the frame (see the expected-tone picture). An even drift is "
                   "allowed for; soft colour that spans the frame is the light's.")
    if phone:
        out.append("A phone capture: phones adjust colour on faces and skies. Colour that sits exactly on a face or a "
                   "sky may be the phone's.")
    return out, held, odd


# -- pictures ------------------------------------------------------------------------------------------------------------

def lab2u8(L, a, b):
    rgb = color.lab2rgb(np.stack([L, a, b], axis=-1).astype(np.float64))
    return np.round(np.clip(rgb, 0, 1) * 255).astype(np.uint8)


def hatch(img, mask, step=7, colour=(150, 150, 150)):
    H, W = mask.shape
    yy, xx = np.mgrid[0:H, 0:W]
    out = img.copy()
    out[mask & (((xx + yy) % step) < 2)] = colour
    return out


def vivid(ang):
    rgb = color.lab2rgb(np.stack([np.full_like(ang, 62.0), 58 * np.cos(ang), 58 * np.sin(ang)], -1).astype(np.float64))
    rgb = np.clip(rgb, 1e-4, 1)
    return (rgb / rgb.max(axis=-1, keepdims=True) * 255).astype(np.float32)


def render(res: Result, boost=4.0):
    """B (neutralised), C (where colour departs), D (expected unpainted, own tone amplified).  B + D is the capture's
    colour amplified: D the part expected of the print unpainted, B the part that is not."""
    L, F = res.L, res.F
    k = boost
    B = hatch(lab2u8(L, np.clip(k * res.va, -90, 90), np.clip(k * res.vb, -90, 90)), res.unjudgeable)
    grey = lab2u8(30 + 0.55 * L, np.zeros_like(L), np.zeros_like(L)).astype(np.float32)
    al = res.alpha[..., None]
    C = np.round(grey * (1 - al) + vivid(np.arctan2(res.hb, res.ha)) * al).astype(np.uint8)
    C = hatch(C, res.unjudgeable)
    C = hatch(C, res.extrapolated & (res.alpha > 0.2), step=11, colour=(235, 235, 235))
    ea, eb = expected(F, res.ref)            # the print's tone and the light's drift (not the camera's fringes)
    D = lab2u8(L, np.clip(k * ea, -90, 90), np.clip(k * eb, -90, 90))
    if res.picks:
        for i, (x0, y0, x1, y1) in enumerate(res.picks):
            col = (240, 120, 30) if (i + 1) in res.odd else (40, 210, 230)
            cv2.rectangle(D, (int(x0), int(y0)), (int(x1) - 1, int(y1) - 1), col, 3)
            cv2.putText(D, str(i + 1), (int(x0) + 4, int(y0) + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.9, col, 2)
    return B, C, D


def tone_strip(ref: Ref, width, height=56, boost=4.0):
    """Paper (left) to shadow (right).  Top: the expected colour amplified at one lightness (grey for a neutral print);
    bottom: the expected tone itself.  Hatched where no reference reaches; orange ticks where a band was overruled."""
    Ls = np.linspace(97, 8, width)
    Li = np.clip(np.round(Ls / 0.5).astype(int), 0, len(ref.grid) - 1)
    ma, mb = ref.ma[Li], ref.mb[Li]
    h2 = height // 2
    top = lab2u8(np.full((h2, width), 65.0), np.tile(boost * ma, (h2, 1)), np.tile(boost * mb, (h2, 1)))
    bot = lab2u8(np.tile(Ls, (h2, 1)), np.tile(ma, (h2, 1)), np.tile(mb, (h2, 1)))
    strip = np.concatenate([top, bot], axis=0)
    filled = getattr(ref, "filled", np.zeros(len(ref.grid), bool))[Li]
    outside = ~covered(ref)[Li] & ~filled
    strip = hatch(strip, np.tile(outside, (strip.shape[0], 1)), step=6, colour=(255, 255, 255))
    dots = np.zeros(strip.shape[:2], bool)
    dots[::6, ::6] = True
    strip[dots & np.tile(filled, (strip.shape[0], 1))] = (255, 255, 255)
    centres = np.arange(1.0, 100.0, 2.0)
    for c in centres[(ref.band_w < 0.5) & (ref.band_votes >= 3)]:
        x = int(round((97 - c) / 89 * (width - 1)))
        if 0 <= x < width:
            strip[:8, max(x - 2, 0):x + 3] = (240, 120, 30)
    return strip
