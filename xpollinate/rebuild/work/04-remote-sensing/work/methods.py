"""Background models for 'what the unpainted photograph looks like', each giving a paint statistic per pixel.

M1  v1-v3: global C*ab against a histogram noise floor (the substrate is assumed neutral)
M2  v4.1: lightness-relative chroma (C*ab magnitude against its L*-band median and IQR)
M3  TODO.md (4.1.2 plan), automatic fallback: per-L*-band median (a*, b*), smoothed along L*, robust spread,
    pixels far from the fit set aside and refitted; M3p adds the plan's optional x-y plane
M4  Woodii Chroma mode, automatic: OD of base-normalised linear values, one silver axis, off-axis OD in units of
    the clutter covariance binned by density (no picks: iterative trimming stands in for the untinted pick)
M5  global robust RX (MCD covariance) on log-chromaticity
M6  local dual-window RX on log-chromaticity
M7  proposed: log-chromaticity = f(tone) + g(x, y) + clutter, fitted by robust IRLS (Tukey biweight), the clutter's
    2 x 2 covariance conditional on tone, its spread inflated at luminance edges (lateral colour)
"""
from __future__ import annotations

import math

import cv2
import numpy as np
from scipy.interpolate import BSpline
from skimage import color

from sim import srgb_decode, srgb_encode, smoothstep

E = np.array([[2, -1, -1], [0, 1, -1]], float)
E[0] /= math.sqrt(6)
E[1] /= math.sqrt(2)                      # orthonormal basis of the plane at right angles to (1, 1, 1)
LUM = np.array([0.2126, 0.7152, 0.0722])


# ---------------------------------------------------------------------------------------------------------------
# shared preparation
# ---------------------------------------------------------------------------------------------------------------

def prepare(img_u8: np.ndarray, box, smooth: str = "median5") -> dict:
    rgb = img_u8.astype(np.float32) / 255.0
    lin = srgb_decode(rgb).astype(np.float32)
    lab = color.rgb2lab(rgb).astype(np.float32)
    H, W = img_u8.shape[:2]
    inbox = np.zeros((H, W), bool)
    x0, y0, x1, y1 = box
    inbox[y0:y1, x0:x1] = True
    clipped = (img_u8 >= 250).any(axis=2)
    dark = (lab[..., 0] < 12) | (img_u8 <= 4).any(axis=2)
    judge = inbox & ~clipped & ~dark
    a = cv2.medianBlur(np.ascontiguousarray(lab[..., 1]), 5)
    b = cv2.medianBlur(np.ascontiguousarray(lab[..., 2]), 5)
    logr = np.log(np.maximum(lin, 1e-3))
    chi = logr @ E.T
    chi = np.stack([cv2.medianBlur(np.ascontiguousarray(chi[..., k].astype(np.float32)), 5) for k in (0, 1)], -1)
    if smooth == "mcu":
        # 4:2:0 JPEG codes chroma in 16 x 16 blocks: smooth chroma over about one block, after the median
        chi = np.stack([cv2.GaussianBlur(np.ascontiguousarray(chi[..., k]), (0, 0), 5.0) for k in (0, 1)], -1)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    xn = (xx - (x0 + x1) / 2) / ((x1 - x0) / 2)
    yn = (yy - (y0 + y1) / 2) / ((y1 - y0) / 2)
    Y = lin @ LUM
    return dict(rgb=rgb, lin=lin, lab=lab, L=lab[..., 0], a=a, b=b, chi=chi, judge=judge, inbox=inbox,
                clipped=clipped, dark=dark, xn=xn, yn=yn, Y=Y, box=box)


def speck(S: np.ndarray, judge: np.ndarray) -> np.ndarray:
    """The TODO plan's speck filter: a small median on the statistic map (5 px)."""
    s = np.where(judge, S, 0).astype(np.float32)
    return cv2.medianBlur(s, 5)


# ---------------------------------------------------------------------------------------------------------------
# M1: v3 global chroma noise floor
# ---------------------------------------------------------------------------------------------------------------

def noise_floor_v3(flat: np.ndarray, fraction: float = 0.01) -> float:
    max_val = max(100.0, float(flat.max()))
    counts, edges = np.histogram(flat, bins=np.linspace(0, max_val, 200))
    peak = int(np.argmax(counts))
    if peak > len(counts) * 0.9:
        return float(np.percentile(flat, 75))
    cutoff = counts[peak] * fraction
    val = float(edges[peak]) + 10.0
    for i in range(peak, len(counts)):
        if counts[i] < cutoff:
            val = float(edges[i])
            break
    return max(val, 1.0)


def m1_v3(p: dict) -> dict:
    C = np.hypot(p["a"], p["b"])
    thr = noise_floor_v3(C[p["judge"]])
    S = speck(C / thr, p["judge"])
    return dict(S=S, V=(S > 1.0) & p["judge"], R=C, note=f"floor C*={thr:.1f}")


# ---------------------------------------------------------------------------------------------------------------
# M2: v4.1 LRC
# ---------------------------------------------------------------------------------------------------------------

def noise_floor_41(flat: np.ndarray, bin_width: float = 0.1, fraction: float = 0.01) -> float:
    lo = float(min(0.0, flat.min()))
    hi = float(flat.max())
    n = int(np.clip(np.ceil((hi - lo) / bin_width), 1, 4096))
    counts, edges = np.histogram(flat, bins=n, range=(lo, hi))
    peak = int(np.argmax(counts))
    if peak > n * 0.9:
        return float(np.percentile(flat, 75))
    below = np.nonzero(counts[peak:] < counts[peak] * fraction)[0]
    return float(edges[peak + below[0]]) if below.size else float(edges[peak]) + 2.0


def m2_lrc(p: dict) -> dict:
    L, C = p["L"], np.hypot(p["a"], p["b"])
    j = p["judge"]
    nb = 100
    idx = np.clip(L.astype(int), 0, nb - 1)
    med = np.full(nb, np.nan)
    iqr = np.full(nb, np.nan)
    for k in range(nb):
        v = C[j & (idx == k)]
        if v.size:
            med[k] = np.median(v)
            q1, q3 = np.percentile(v, [25, 75])
            iqr[k] = max(q3 - q1, 1.0)
    ok = ~np.isnan(med)
    xs = np.arange(nb)
    med = np.interp(xs, xs[ok], med[ok])
    iqr = np.interp(xs, xs[ok], iqr[ok])
    ker = np.ones(3) / 3
    med = np.convolve(np.pad(med, 1, mode="edge"), ker, "same")[1:-1]
    iqr = np.maximum(np.convolve(np.pad(iqr, 1, mode="edge"), ker, "same")[1:-1], 1.0)
    f = np.clip(L - 0.5, 0, nb - 1)
    lo = np.floor(f).astype(int)
    hi = np.clip(lo + 1, 0, nb - 1)
    fr = f - lo
    lrc = (C - (med[lo] * (1 - fr) + med[hi] * fr)) / (iqr[lo] * (1 - fr) + iqr[hi] * fr)
    thr = noise_floor_41(lrc[j])
    S = speck(lrc - thr, j)
    return dict(S=S, V=(S > 0) & j, R=lrc, note=f"LRC floor {thr:.2f}")


# ---------------------------------------------------------------------------------------------------------------
# M3: the TODO plan's automatic reference (CIELAB)
# ---------------------------------------------------------------------------------------------------------------

def _band_fill_smooth(vals: np.ndarray, window: int) -> np.ndarray:
    ok = ~np.isnan(vals)
    xs = np.arange(len(vals))
    if not ok.any():
        return np.zeros_like(vals)
    v = np.interp(xs, xs[ok], vals[ok])
    pad = window // 2
    return np.convolve(np.pad(v, pad, mode="edge"), np.ones(window) / window, "same")[pad:pad + len(v)]


def m3_todo(p: dict, plane: bool = False, picks: np.ndarray | None = None, bw: float = 2.0, rounds: int = 4,
            zcut: float = 3.0, ramp=(2.0, 5.0), floor: float = 0.3) -> dict:
    L, a, b = p["L"], p["a"], p["b"]
    j = p["judge"]
    fit = (picks & j) if picks is not None else j.copy()
    nb = int(round(100 / bw))
    idx = np.clip((L / bw).astype(int), 0, nb - 1)
    pa = np.zeros_like(a)
    pb = np.zeros_like(b)
    inl = fit.copy()
    for r in range(rounds):
        ma = np.full(nb, np.nan)
        mb = np.full(nb, np.nan)
        for k in range(nb):
            m = inl & (idx == k)
            if m.sum() >= 20:
                ma[k] = np.median((a - pa)[m])
                mb[k] = np.median((b - pb)[m])
        ma = _band_fill_smooth(ma, 5)
        mb = _band_fill_smooth(mb, 5)
        ca, cb = ma[idx], mb[idx]
        if plane:
            for _ in range(2):
                X = np.stack([p["xn"][inl], p["yn"][inl]], 1)
                X = X - X.mean(0)
                ka = np.linalg.lstsq(X, (a - ca)[inl] - np.median((a - ca)[inl]), rcond=None)[0]
                kb = np.linalg.lstsq(X, (b - cb)[inl] - np.median((b - cb)[inl]), rcond=None)[0]
                xm, ym = p["xn"][inl].mean(), p["yn"][inl].mean()
                pa = ka[0] * (p["xn"] - xm) + ka[1] * (p["yn"] - ym)
                pb = kb[0] * (p["xn"] - xm) + kb[1] * (p["yn"] - ym)
        ra, rb = a - ca - pa, b - cb - pb
        mag = np.hypot(ra, rb)
        sp = np.full(nb, np.nan)
        for k in range(nb):
            m = inl & (idx == k)
            if m.sum() >= 20:
                sp[k] = np.median(mag[m]) / 1.1774
        sp = np.maximum(_band_fill_smooth(sp, 5), floor)
        z = mag / sp[idx]
        if picks is None:
            inl = fit & (z < zcut)
    S = speck(z, j)
    return dict(S=S, V=(S > ramp[0]) & j, V3=(S > 3) & j, z=z, ref=(ca + pa, cb + pb), resid=(ra, rb), R=mag,
                note="TODO plan" + (" + plane" if plane else ""))


# ---------------------------------------------------------------------------------------------------------------
# M4: Woodii's silver axis, automatic
# ---------------------------------------------------------------------------------------------------------------

def _plane_basis(axis):
    a = axis / np.linalg.norm(axis)
    basis = []
    for i in range(3):
        e = np.zeros(3)
        e[i] = 1
        e -= (e @ a) * a
        for q in basis:
            e -= (e @ q) * q
        if np.linalg.norm(e) > 1e-8:
            basis.append(e / np.linalg.norm(e))
        if len(basis) == 2:
            break
    basis[1] = np.cross(a, basis[0])
    return np.array(basis)


def m4_woodii(p: dict, picks: np.ndarray | None = None, rounds: int = 4, k: float = 4.0) -> dict:
    lin = p["lin"].astype(np.float64)
    j = p["judge"]
    fit = (picks & j) if picks is not None else j.copy()
    s = lin.sum(axis=2)
    pool = fit
    cut = np.percentile(s[pool], 98)
    base = np.median(lin[pool & (s >= cut)], axis=0)
    od = -np.log10(np.maximum(lin, 1e-4) / base)
    inl = fit.copy()
    for r in range(rounds):
        x = od[inl]
        w, v = np.linalg.eigh(x.T @ x / len(x))
        ax = v[:, -1] * (1 if v[:, -1].sum() >= 0 else -1)
        Eb = _plane_basis(ax)
        dsc = ax.sum() / 3
        d = od @ (ax * dsc)
        u = od @ Eb.T
        # clutter covariance binned by density (0.1 OD), robust, interpolated
        bins = np.arange(-0.1, 2.2, 0.1)
        cen, covs = [], []
        for lo in bins:
            m = inl & (d >= lo) & (d < lo + 0.1)
            if m.sum() >= 200:
                uu = u[m]
                med = np.median(uu, 0)
                mad = 1.4826 * np.median(np.abs(uu - med), 0)
                keep = (np.abs(uu - med) <= 5 * np.maximum(mad, 1e-9)).all(1)
                uu = uu[keep] - uu[keep].mean(0)
                covs.append(uu.T @ uu / max(len(uu) - 1, 1) + np.eye(2) * 1e-8)
                cen.append(float(np.median(d[m])))
        cen = np.array(cen)
        covs = np.array(covs)
        dd = np.clip(d, cen.min(), cen.max())
        c00 = np.interp(dd, cen, covs[:, 0, 0])
        c01 = np.interp(dd, cen, covs[:, 0, 1])
        c11 = np.interp(dd, cen, covs[:, 1, 1])
        det = c00 * c11 - c01 ** 2
        q = (c11 * u[..., 0] ** 2 - 2 * c01 * u[..., 0] * u[..., 1] + c00 * u[..., 1] ** 2) / np.maximum(det, 1e-18)
        z = np.sqrt(np.maximum(q, 0))
        if picks is None:
            inl = fit & (z < k)
    S = speck(z, j)
    return dict(S=S, V=(S > k) & j, z=z, R=np.linalg.norm(u, axis=-1),
                note="Woodii axis" + (" (picks)" if picks is not None else " (auto)"))


# ---------------------------------------------------------------------------------------------------------------
# M5, M6: RX on log-chromaticity
# ---------------------------------------------------------------------------------------------------------------

RX_K = math.sqrt(-2 * math.log(1e-3))    # 3.72: a 2-D Gaussian background exceeds it with probability 1e-3


def m5_grx(p: dict, seed: int = 0) -> dict:
    from sklearn.covariance import MinCovDet
    chi = p["chi"].astype(np.float64)
    j = p["judge"]
    X = chi[j]
    rng = np.random.default_rng(seed)
    Xs = X[rng.choice(len(X), min(20000, len(X)), replace=False)]
    mcd = MinCovDet(random_state=seed).fit(Xs)
    z = np.sqrt(mcd.mahalanobis(chi.reshape(-1, 2)).reshape(chi.shape[:2]))
    S = speck(z, j)
    return dict(S=S, V=(S > RX_K) & j, note="global RX (MCD)")


def m6_lrx(p: dict, outer: int = 121, inner: int = 41) -> dict:
    chi = p["chi"].astype(np.float64)
    j = p["judge"].astype(np.float64)
    x, y = chi[..., 0], chi[..., 1]
    terms = [j, j * x, j * y, j * x * x, j * x * y, j * y * y]

    def box(a, n):
        return cv2.boxFilter(a, -1, (n, n), normalize=False, borderType=cv2.BORDER_CONSTANT)

    o = [box(t, outer) for t in terms]
    i = [box(t, inner) for t in terms]
    n, sx, sy, sxx, sxy, syy = [oo - ii for oo, ii in zip(o, i)]
    n = np.maximum(n, 1)
    mx, my = sx / n, sy / n
    cxx = sxx / n - mx ** 2 + 1e-8
    cxy = sxy / n - mx * my
    cyy = syy / n - my ** 2 + 1e-8
    dx, dy = x - mx, y - my
    det = np.maximum(cxx * cyy - cxy ** 2, 1e-16)
    z = np.sqrt(np.maximum((cyy * dx * dx - 2 * cxy * dx * dy + cxx * dy * dy) / det, 0))
    S = speck(z, p["judge"])
    return dict(S=S, V=(S > RX_K) & p["judge"], note=f"local RX {outer}/{inner}")


# ---------------------------------------------------------------------------------------------------------------
# M7: the proposal
# ---------------------------------------------------------------------------------------------------------------

def bspline_basis(t: np.ndarray, knots_inner: np.ndarray, lo: float, hi: float, k: int = 3) -> np.ndarray:
    tt = np.concatenate([[lo] * (k + 1), knots_inner, [hi] * (k + 1)])
    n = len(tt) - k - 1
    tc = np.clip(t, lo, hi - 1e-6)
    out = np.empty((len(t), n))
    for i in range(n):
        c = np.zeros(n)
        c[i] = 1
        out[:, i] = BSpline(tt, c, k, extrapolate=False)(tc)
    return np.nan_to_num(out)


def poly_xy(x: np.ndarray, y: np.ndarray, deg: int) -> np.ndarray:
    cols = []
    for dx in range(deg + 1):
        for dy in range(deg + 1 - dx):
            if dx + dy == 0:
                continue
            cols.append(x ** dx * y ** dy)
    return np.stack(cols, 1) if cols else np.zeros((len(x), 0))


class Background:
    """chi(pixel) = f(tone) + g(x, y) + clutter; clutter covariance a function of tone, inflated at edges."""

    def __init__(self, knots: int = 4, xy_deg: int = 2, space: str = "logchroma", tone: str = "L",
                 iters: int = 15, c: float = 4.685, edge: bool = True, shrink: float = 0.2, sample: int = 120000,
                 seed: int = 0, spread: str = "split", lag: int = 12, start: str = "lts", h: float = 0.6):
        self.knots, self.xy_deg, self.space, self.tone = knots, xy_deg, space, tone
        self.iters, self.c, self.edge, self.shrink, self.sample, self.seed = iters, c, edge, shrink, sample, seed
        self.kappa2, self._g = 0.0, None
        self.spread, self._noise, self.misfit, self.lag = spread, None, 0.0, lag
        self.start, self.h, self._misfit_fixed = start, h, None

    # -- design --
    def _design(self, t, x, y):
        Bt = bspline_basis(t, self.kin, self.tlo, self.thi)
        Bx = poly_xy(x, y, self.xy_deg)
        return np.concatenate([Bt, Bx], 1)

    @staticmethod
    def _logy(t):
        """Tone (L*) as log luminance: the clutter's size follows 1 / luminance in the shadows."""
        return np.log(np.maximum((np.asarray(t, np.float64) + 16) / 116, 1e-3) ** 3)

    def _cov_by_tone(self, r, t, w, prev=None):
        if self.spread == "split" and self._noise is not None:
            return self._cov_split(r, t, prev)
        return self._cov_pooled(r, t, w, prev)

    def _cov_split(self, r, t, prev):
        """Clutter = pixel-scale noise (measured from differences of pixels `lag` apart, which a smooth wash cannot
        inflate) + one model-error term, isotropic, pooled over the tone bins by a median (which one tone band taken
        over by paint cannot inflate)."""
        cen_n, cov_n = self._noise
        if self._g is not None:                    # edges' lateral colour is the edge term's, not model error
            calm = self._g < np.quantile(self._g, 0.8)
            pooled = self._cov_pooled(r[calm], t[calm], None, None, smooth=False, shrink=False)
        else:
            pooled = self._cov_pooled(r, t, None, None, smooth=False, shrink=False)   # median-scaled per bin
        cen_p, cov_p = pooled
        u = np.clip(cen_p, cen_n.min(), cen_n.max())
        nz = np.stack([np.interp(u, cen_n, cov_n[:, i, j]) for i in range(2) for j in range(2)], 1).reshape(-1, 2, 2)
        excess = (np.trace(cov_p, axis1=1, axis2=2) - np.trace(nz, axis1=1, axis2=2)) / 2
        self.misfit = float(max(np.median(excess), 0.0)) if self._misfit_fixed is None else self._misfit_fixed
        covs = cov_n + self.misfit * np.eye(2)
        iso = np.trace(covs, axis1=1, axis2=2)[:, None, None] / 2 * np.eye(2)
        covs = (1 - self.shrink) * covs + self.shrink * iso
        floor = (0.004 if self.space == "logchroma" else 0.3) ** 2
        return cen_n, covs + floor * np.eye(2)

    def _noise_by_tone(self, p, feat, t_all, lag=8):
        """MNF's noise estimate (half the covariance of differences of pixels `lag` apart, across and down), in bins
        of log luminance, pairs on luminance edges or outside the judgeable area left out, median-scaled per bin."""
        j = p["judge"]
        G = edge_strength(p)
        gcut = np.quantile(G[j], 0.8)
        ok = j & (G < gcut)
        u_all = self._logy(t_all)
        diffs, us = [], []
        for dy, dx in ((0, lag), (lag, 0)):
            a = ok[: ok.shape[0] - dy, : ok.shape[1] - dx] & ok[dy:, dx:]
            d = feat[: feat.shape[0] - dy, : feat.shape[1] - dx][a] - feat[dy:, dx:][a]
            uu = 0.5 * (u_all[: u_all.shape[0] - dy, : u_all.shape[1] - dx][a] + u_all[dy:, dx:][a])
            diffs.append(d)
            us.append(uu)
        d = np.concatenate(diffs).astype(np.float64)
        uu = np.concatenate(us)
        rng = np.random.default_rng(self.seed)
        if len(d) > 400000:
            k = rng.choice(len(d), 400000, replace=False)
            d, uu = d[k], uu[k]
        lo, hi = np.percentile(uu, [0.5, 99.5])
        edges = np.linspace(lo, hi, 15)
        edges[0], edges[-1] = -np.inf, np.inf
        cen, covs = [], []
        for i in range(14):
            m = (uu >= edges[i]) & (uu < edges[i + 1])
            if m.sum() < 200:
                continue
            dd = d[m] - np.median(d[m], 0)
            C = dd.T @ dd / len(dd) + 1e-8 * np.eye(2)          # quantised flats can difference to exactly 0
            ma2 = np.einsum("ni,ij,nj->n", dd, np.linalg.inv(C), dd)
            med = float(np.median(ma2))
            C = C * (med / 1.386 if med > 0 else 1.0) / 2.0 + 1e-8 * np.eye(2)
            covs.append(C)
            cen.append(float(np.median(uu[m])))
        self._noise = (np.array(cen), np.array(covs))

    def _cov_pooled(self, r, t, w, prev=None, smooth=True, shrink=True):
        """The clutter's 2 x 2 covariance in bins of log luminance (even in log Y, so the shadows, where it grows
        fast, get bins of their own).  Each bin: the plain covariance of the pixels within the biweight's reach
        (m < c under the previous estimate; all of them at first), not a weighted one, which collapses."""
        u = self._logy(t)
        lo, hi = np.percentile(u, [0.5, 99.5])
        nb = 14
        edges = np.linspace(lo, hi, nb + 1)
        edges[0], edges[-1] = -np.inf, np.inf
        if prev is not None:
            keep = self._maha(r, t, prev) < self.c
        else:
            keep = np.ones(len(t), bool)
        cen, covs = [], []
        for i in range(nb):
            inb = (u >= edges[i]) & (u < edges[i + 1])
            m = inb & keep
            if m.sum() < 80:
                continue
            rr = r[m]
            if prev is None:                       # start: a median-scaled covariance (breakdown 50 %)
                med = np.median(rr, 0)
                d = rr - med
                C = d.T @ d / len(d) + 1e-8 * np.eye(2)
                ma2 = np.einsum("ni,ij,nj->n", d, np.linalg.inv(C), d)
                mm = float(np.median(ma2))
                C = C * (mm / 1.386 if mm > 0 else 1.0) + 1e-8 * np.eye(2)
            else:
                d = rr - rr.mean(0)
                C = d.T @ d / max(len(d) - 1, 1)
            covs.append(C)
            cen.append(float(np.median(u[inb])))
        covs = np.array(covs)
        if not smooth:
            return np.array(cen), covs
        if len(covs) >= 3:
            sm = covs.copy()
            for i in range(1, len(covs) - 1):
                sm[i] = (covs[i - 1] + 2 * covs[i] + covs[i + 1]) / 4
            covs = sm
        iso = np.trace(covs, axis1=1, axis2=2)[:, None, None] / 2 * np.eye(2)
        covs = (1 - self.shrink) * covs + self.shrink * iso
        floor = (0.004 if self.space == "logchroma" else 0.3) ** 2
        covs = covs + floor * np.eye(2)
        return np.array(cen), covs

    def _maha(self, r, t, model=None):
        cen, covs = model if model is not None else (self.cen, self.covs)
        tt = np.clip(self._logy(t), cen.min(), cen.max())
        c00 = np.interp(tt, cen, covs[:, 0, 0])
        c01 = np.interp(tt, cen, covs[:, 0, 1])
        c11 = np.interp(tt, cen, covs[:, 1, 1])
        if self.kappa2 and self._g is not None:
            extra = self.kappa2 * self._g ** 2
            c00, c11 = c00 + extra, c11 + extra
        det = np.maximum(c00 * c11 - c01 ** 2, 1e-18)
        q = (c11 * r[..., 0] ** 2 - 2 * c01 * r[..., 0] * r[..., 1] + c00 * r[..., 1] ** 2) / det
        return np.sqrt(np.maximum(q, 0))

    def _maha_old(self, r, t):
        tt = np.clip(t, self.cen.min(), self.cen.max())
        c00 = np.interp(tt, self.cen, self.covs[:, 0, 0])
        c01 = np.interp(tt, self.cen, self.covs[:, 0, 1])
        c11 = np.interp(tt, self.cen, self.covs[:, 1, 1])
        det = np.maximum(c00 * c11 - c01 ** 2, 1e-18)
        q = (c11 * r[..., 0] ** 2 - 2 * c01 * r[..., 0] * r[..., 1] + c00 * r[..., 1] ** 2) / det
        return np.sqrt(np.maximum(q, 0))

    def fit(self, p: dict, picks: np.ndarray | None = None, pick_weight: float = 5.0,
            light: np.ndarray | None = None):
        """picks: areas of the photograph known to be unpainted (anchor the tone curve and the light field).
        light: paper margin or mount (another material: its own offset, so it anchors the light field only)."""
        self._light_mask = light
        feat = p["chi"] if self.space == "logchroma" else np.stack([p["a"], p["b"]], -1)
        t_all = p["L"] if self.tone == "L" else p["tone"]
        j = p["judge"]
        rng = np.random.default_rng(self.seed)
        idx = np.flatnonzero(j)
        if len(idx) > self.sample:
            idx = np.sort(rng.choice(idx, self.sample, replace=False))
        pk = np.zeros(len(idx), bool)
        if light is not None:                      # margin pixels join the fit, always kept, with their own offset
            lidx = np.flatnonzero(light & j)
            if len(lidx) > self.sample // 4:
                lidx = np.sort(rng.choice(lidx, self.sample // 4, replace=False))
            idx = np.concatenate([idx[~np.isin(idx, lidx)], lidx])
            pk = np.concatenate([np.zeros(len(idx) - len(lidx), bool), np.ones(len(lidx), bool)])
        if picks is not None:
            pidx = np.flatnonzero(picks & j)
            if len(pidx) > self.sample // 4:
                pidx = np.sort(rng.choice(pidx, self.sample // 4, replace=False))
            idx = np.concatenate([idx, pidx])
            pk = np.concatenate([pk, np.ones(len(pidx), bool)])
        flat = lambda a: a.reshape(-1, *a.shape[2:])[idx]
        F = flat(feat).astype(np.float64)
        t = flat(t_all).astype(np.float64)
        x, y = flat(p["xn"]).astype(np.float64), flat(p["yn"]).astype(np.float64)
        self._is_light = (light.reshape(-1)[idx] if light is not None else np.zeros(len(idx), bool))
        tp = t[~self._is_light]                    # the tone curve is the photograph's: knots from its pixels
        self.tlo, self.thi = float(np.percentile(tp, 0.2)) - 1, float(np.percentile(tp, 99.8)) + 1
        self.kin = np.quantile(tp, np.linspace(0, 1, self.knots + 2)[1:-1])
        A = self._design(t, x, y)
        if light is not None:                      # margin or mount: its own offset plus the light, no tone curve
            nt = A.shape[1] - poly_xy(x[:1], y[:1], self.xy_deg).shape[1]
            A[self._is_light, :nt] = 0.0
            A = np.c_[A, self._is_light.astype(float)]
        self.kappa2, self._g = 0.0, None
        G = flat(edge_strength(p)).astype(np.float64) if self.edge else None
        # start: per-tone-band medians (robust where paint is a minority in each band), no x-y term
        nb = 20
        photo = ~self._is_light
        eb = np.unique(np.quantile(t[photo], np.linspace(0, 1, nb + 1)))
        nb = len(eb) - 1
        bi = np.clip(np.searchsorted(eb, t, side="right") - 1, 0, nb - 1)
        start = np.zeros_like(F)
        start_b = np.full((nb, F.shape[1]), np.nan)
        cb = np.full(nb, np.nan)
        for k in range(nb):
            m = (bi == k) & photo
            if m.any():
                start_b[k] = np.median(F[m], 0)
                cb[k] = np.median(t[m])
                start[(bi == k)] = start_b[k]
        okb = ~np.isnan(cb)
        cb, start_b = cb[okb], start_b[okb]
        if self.spread == "split":
            # the residual from a first tone curve (band medians, interpolated in L*), differenced locally
            f0 = np.stack([np.interp(t_all, cb, start_b[:, i]) for i in range(F.shape[1])], -1)
            self._noise_by_tone(p, (feat - f0).astype(np.float64), t_all, lag=self.lag)
        if self.start == "lts":
            start = self._lts_start(F, t, x, y, pk)
        r = F - start
        model = self._cov_by_tone(r, t, None)
        self.cen, self.covs = model
        m = self._maha(r, t)
        m = self._scale_guard(m, pk, r, t)
        w = np.where(m < self.c, (1 - (m / self.c) ** 2) ** 2, 0.0)
        for it in range(self.iters):
            ww = w.copy()
            if pk.any():
                ww[pk] = pick_weight
            sw = np.sqrt(ww)[:, None]
            beta = np.linalg.lstsq(A * sw, F * sw, rcond=1e-8)[0]
            r = F - A @ beta
            if G is not None and it >= 1:
                self._fit_edge(r, t, G)
            self._g = G
            self.cen, self.covs = self._cov_by_tone(r, t, w, (self.cen, self.covs))
            m = self._maha(r, t)
            m = self._scale_guard(m, pk, r, t)
            w_new = np.where(m < self.c, (1 - (m / self.c) ** 2) ** 2, 0.0)
            if np.abs(w_new - w).mean() < 1e-3 and it >= 3:
                w = w_new
                break
            w = w_new
        self.beta = beta
        self.inlier_share = float((w[~pk] > 0.5).mean())
        self.weights = w
        self.misfit_mstep = self.misfit
        if self.spread == "split" and self._noise is not None:
            inl = w > 0.5
            self._misfit_fixed = None                           # display spread: the final inliers' own
            if inl.sum() > 500:
                self._g = G[inl] if G is not None else None
                self.cen, self.covs = self._cov_split(r[inl], t[inl], None)
        self._g = None
        return self

    def _scale_guard(self, m, pk, r, t):
        """The M-step's scale may not be smaller than the photograph's own median-based scale (half its pixels
        within 1.18 sd, as for a 2-D Gaussian): otherwise every weight goes to zero and the fit collapses."""
        s2 = float(np.median(m[~pk] ** 2) / 1.386) if (~pk).any() else 1.0
        if s2 > 2.0:
            self.covs = self.covs * s2
            m = self._maha(r, t)
        return m

    def _lts_start(self, F, t, x, y, pk):
        """A high-breakdown start (least trimmed squares, FAST-LTS style random starts and C-steps) on a stiff model:
        f quadratic in tone, g linear in x and y.  It needs the unpainted pixels to be the majority of the whole
        image (h of them), not of every tone band, as band medians do.  Shadows (L* < 20) are left out: their noise
        would steer it.  Picks, if any, are always kept.  Also fixes the model-error term from the kept pixels."""
        rng = np.random.default_rng(self.seed + 1)
        tn = (t - 50.0) / 50.0
        A0 = np.c_[np.ones_like(tn), tn, tn ** 2, x, y]
        if self._is_light.any():
            A0[self._is_light, :3] = 0.0
            A0 = np.c_[A0, self._is_light.astype(float)]
        use = (t > 20) | pk
        Au, Fu, pku = A0[use], F[use], pk[use]
        n = len(Fu)
        hn = int(self.h * n)
        best = None
        for trial in range(16):
            sub = rng.choice(n, 40, replace=False)
            beta = np.linalg.lstsq(Au[sub], Fu[sub], rcond=None)[0]
            for _ in range(6):
                d = ((Fu - Au @ beta) ** 2).sum(1)
                d[pku] = -1.0
                keep = np.argpartition(d, hn)[:hn]
                beta = np.linalg.lstsq(Au[keep], Fu[keep], rcond=None)[0]
            d = ((Fu - Au @ beta) ** 2).sum(1)
            obj = np.partition(d, hn)[:hn].sum()
            if best is None or obj < best[0]:
                best = (obj, beta, keep)
        _, beta, keep = best
        self.lts_beta = beta
        if self._noise is not None:            # MM: the scale for the M-step, from the LTS-kept set, then fixed
            r = Fu[keep] - Au[keep] @ beta
            tk = t[use][keep]
            cen_n, cov_n = self._noise
            u = np.clip(self._logy(tk), cen_n.min(), cen_n.max())
            nz = np.interp(u, cen_n, cov_n[:, 0, 0] + cov_n[:, 1, 1])
            # the kept set is the h closest: E[chi2_2 | below its h-quantile q] = 2 - q (1 - h) / h
            q = -2 * np.log(1 - self.h)
            cons = 2.0 / (2 - q * (1 - self.h) / self.h)
            self._misfit_fixed = float(max((np.mean((r ** 2).sum(1)) * cons - np.mean(nz)) / 2, 0.0))
        return A0 @ beta

    def _fit_edge(self, r, t, G):
        """Lateral colour and demosaicing put false colour on luminance edges, growing with the edge's gradient G:
        an isotropic term kappa2 * G^2 added to the clutter covariance.  kappa2 from the median squared residual
        in bins of G over all pixels (not only inliers: the edges' own outliers are what it has to explain)."""
        self._g = None
        q = (r ** 2).sum(1)
        tr = np.interp(np.clip(self._logy(t), self.cen.min(), self.cen.max()), self.cen,
                       self.covs[:, 0, 0] + self.covs[:, 1, 1])
        gq = np.quantile(G, np.linspace(0.5, 1, 11))
        xs, ys = [], []
        for i in range(10):
            mm = (G >= gq[i]) & (G <= gq[i + 1])
            if mm.sum() > 50:
                xs.append(np.median(G[mm] ** 2))
                ys.append(np.median(q[mm]) / 0.693 - np.median(tr[mm]))
        if len(xs) >= 3:
            xs, ys = np.array(xs), np.array(ys)
            k2 = float(np.sum(xs * ys) / np.sum(xs * xs)) / 2.0
            self.kappa2 = max(k2, 0.0)

    def apply(self, p: dict):
        feat = p["chi"] if self.space == "logchroma" else np.stack([p["a"], p["b"]], -1)
        t_all = p["L"] if self.tone == "L" else p["tone"]
        H, W = t_all.shape
        Bt = bspline_basis(t_all.ravel().astype(np.float64), self.kin, self.tlo, self.thi)
        Bx = poly_xy(p["xn"].ravel().astype(np.float64), p["yn"].ravel().astype(np.float64), self.xy_deg)
        nt, nx = Bt.shape[1], Bx.shape[1]
        f_part = (Bt @ self.beta[:nt]).reshape(H, W, 2)
        g_part = (Bx @ self.beta[nt:nt + nx]).reshape(H, W, 2) if nx else np.zeros((H, W, 2))
        ref = f_part + g_part
        if self._light_mask is not None and len(self.beta) > nt + nx:
            lm = self._light_mask[..., None]
            ref = np.where(lm, g_part + self.beta[nt + nx][None, None, :], ref)
            f_part = np.where(lm, 0.0, f_part)
        r = feat - ref
        self._g = edge_strength(p).astype(np.float64) if self.edge else None
        z = self._maha(r, t_all)
        self._g = None
        return dict(ref=ref, f=f_part, g=g_part, resid=r, z=z)


def edge_strength(p: dict) -> np.ndarray:
    """Local gradient of log luminance (per px), lightly smoothed: where lateral colour and demosaicing put false
    colour."""
    if "_edge" in p:
        return p["_edge"]
    lY = np.log(np.maximum(p["Y"], 1e-3)).astype(np.float32)
    lY = cv2.GaussianBlur(lY, (0, 0), 1.0)
    gx = cv2.Sobel(lY, cv2.CV_32F, 1, 0, ksize=3) / 8
    gy = cv2.Sobel(lY, cv2.CV_32F, 0, 1, ksize=3) / 8
    g = cv2.GaussianBlur(np.hypot(gx, gy), (0, 0), 1.5)
    p["_edge"] = g
    return g


def noise_sd(bg: "Background", p: dict) -> np.ndarray:
    """Per-pixel noise sd (per axis) at the pixel's tone, with the edge term: no model error."""
    cen, cov = bg._noise
    u = np.clip(bg._logy(p["L"]), cen.min(), cen.max())
    var = np.interp(u, cen, (cov[:, 0, 0] + cov[:, 1, 1]) / 2)
    if bg.edge and bg.kappa2:
        var = var + bg.kappa2 * edge_strength(p).astype(np.float64) ** 2
    return np.sqrt(var + 0.004 ** 2)


def m7_fixed(p: dict, T0: float = 0.04, picks=None, light=None, k: float = 3.0, **kw) -> dict:
    """The proposal's reference, with presence as a fixed departure from it (log-chromaticity, like a fixed index
    threshold) and a floor of k noise sd at the pixel's tone and edge strength: paint cannot raise the threshold."""
    bg = Background(**kw).fit(p, picks, light=light)
    out = bg.apply(p)
    d = np.linalg.norm(np.nan_to_num(out["resid"]), axis=-1)
    floor = np.maximum(T0, k * noise_sd(bg, p))
    S = speck(d / floor, p["judge"])
    return dict(S=S, V=(S > 1.0) & p["judge"], bg=bg, R=d, **out,
                note=f"proposal, fixed departure {T0} with {k} noise sd floor")


def m7_prop(p: dict, picks=None, ramp=(3.0, 6.0), light=None, **kw) -> dict:
    bg = Background(**kw).fit(p, picks, light=light)
    out = bg.apply(p)
    S = speck(out["z"], p["judge"])
    return dict(S=S, V=(S > ramp[0]) & p["judge"], V2=(S > 2) & p["judge"], bg=bg,
                R=np.linalg.norm(np.nan_to_num(out["resid"]), axis=-1), **out,
                note=f"proposal knots={bg.knots} xy={bg.xy_deg} space={bg.space} inliers={bg.inlier_share:.2f} misfit(M)={getattr(bg, 'misfit_mstep', 0):.2g} misfit(show)={bg.misfit:.2g} k2={bg.kappa2:.2g}")


# ---------------------------------------------------------------------------------------------------------------
# pictures
# ---------------------------------------------------------------------------------------------------------------

def chroma_picture(Y: np.ndarray, chi: np.ndarray, gain: float = 1.0) -> np.ndarray:
    """An sRGB picture with luminance Y and log-chromaticity chi * gain (0 = neutral)."""
    c = np.exp((chi * gain) @ E)
    c = c / (c @ LUM)[..., None]
    return srgb_encode(np.clip(Y[..., None] * c, 0, 1))


def boost_picture(p: dict, res: dict, gain: float = 4.0) -> np.ndarray:
    """The substrate rendered neutral, the departure from it amplified."""
    return chroma_picture(p["Y"], np.nan_to_num(res["resid"]), gain)


def reference_picture(p: dict, res: dict, gain: float = 4.0) -> np.ndarray:
    """What the tool takes the unpainted photograph to be: the reference's colour, amplified by the same gain."""
    return chroma_picture(p["Y"], res["ref"], gain)


def presence_picture(p: dict, S: np.ndarray, resid: np.ndarray, ramp=(3.0, 6.0)) -> np.ndarray:
    grey = srgb_encode(np.clip(p["Y"], 0, 1))[..., None].repeat(3, 2) * 0.85
    alpha = smoothstep(S, ramp[0], ramp[1])[..., None]
    d = np.nan_to_num(resid)
    n = np.linalg.norm(d, axis=-1, keepdims=True)
    hue = chroma_picture(np.full(S.shape, 0.35), d / np.maximum(n, 1e-9) * 0.9, 1.0)
    out = grey * (1 - alpha) + hue * alpha
    hatch = (~p["judge"]) & p["inbox"]
    yy, xx = np.mgrid[0:S.shape[0], 0:S.shape[1]]
    stripes = ((xx + yy) // 6) % 2 == 0
    out[hatch & stripes] = 0.55
    return out
