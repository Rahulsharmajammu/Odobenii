"""The synthesis's engine (synthesis.md 4.3), built as specified, on the red team's bench (work/sim.py).

Scaled to the bench's 1024 px frames (the synthesis's numbers are for 2,400-3,000 px): shift differences 4 px apart
(12 px at 3,000), chroma-resolution blur 1 px... kept at 2 px as specified for 4:2:0, place votes 10 x 10 tiles per
2 L* band with at least 20 pixels (25 at 1.3 MP).  Choices the synthesis leaves open are made plainly here.
"""
from __future__ import annotations

import numpy as np
import cv2
from scipy import ndimage as ndi
from scipy.interpolate import BSpline
from skimage import color

T0 = 0.04            # [10] 'normal' T0 in chi units (about a 4 % change in a channel ratio); synthesis: one constant
SHIFT = 4            # px between differenced pixels (12 px at 3,000 px)
SIGMA_C = 2.0        # chroma-resolution blur for 4:2:0
CLIP = 250
NEAR_BLACK = 12.0


def srgb_decode(u8):
    x = u8.astype(np.float32) / 255.0
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def features(rgb_u8):
    lin = np.maximum(srgb_decode(rgb_u8), 1e-4)
    ln = np.log(lin)
    chi = np.stack([(ln[..., 0] - ln[..., 1]) / np.sqrt(2), (ln[..., 0] + ln[..., 1] - 2 * ln[..., 2]) / np.sqrt(6)], -1)
    chi = np.stack([ndi.median_filter(chi[..., k], 5) for k in range(2)], -1).astype(np.float32)
    L = color.rgb2lab(rgb_u8 / 255.0)[..., 0].astype(np.float32)
    Y = lin @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    lnY = cv2.GaussianBlur(np.log(np.maximum(Y, 1e-4)), (0, 0), SIGMA_C)
    gy, gx = np.gradient(lnY)
    G = np.hypot(gx, gy).astype(np.float32)
    clipped = cv2.dilate((rgb_u8.max(-1) >= CLIP).astype(np.uint8), np.ones((7, 7))).astype(bool)
    dark = (cv2.blur(L, (5, 5)) < NEAR_BLACK) | (rgb_u8.min(-1) <= 4)
    usable = ~clipped & ~dark
    return dict(chi=chi, L=L, G=G, usable=usable, lnY=lnY)


def _bspline_basis(Lv, knots_int, deg=3, lo=0.0, hi=100.0):
    t = np.r_[[lo] * (deg + 1), knots_int, [hi] * (deg + 1)]
    n = len(t) - deg - 1
    B = np.zeros((len(Lv), n))
    for i in range(n):
        c = np.zeros(n); c[i] = 1
        B[:, i] = BSpline(t, c, deg, extrapolate=True)(np.clip(Lv, lo, hi))
    return B


def votes(F, boxes=None, tiles=10, band=2.0, min_px=20):
    H, W = F["L"].shape
    yy, xx = np.mgrid[0:H, 0:W]
    out = []
    ty = np.linspace(0, H, tiles + 1).astype(int); tx = np.linspace(0, W, tiles + 1).astype(int)
    bidx = np.floor(F["L"] / band).astype(int)
    for i in range(tiles):
        for j in range(tiles):
            sl = (slice(ty[i], ty[i + 1]), slice(tx[j], tx[j + 1]))
            u = F["usable"][sl]; b = bidx[sl]
            for k in np.unique(b[u]):
                m = u & (b == k)
                if m.sum() < min_px:
                    continue
                out.append([np.median(F["L"][sl][m]), np.median(F["chi"][sl][..., 0][m]),
                            np.median(F["chi"][sl][..., 1][m]), np.median(xx[sl][m]), np.median(yy[sl][m]), 1.0, 0.0])
    for bi, (x0, y0, x1, y1) in enumerate(boxes or []):
        sl = (slice(int(y0), int(y1)), slice(int(x0), int(x1)))
        u = F["usable"][sl]; b = bidx[sl]
        for k in np.unique(b[u]):
            m = u & (b == k)
            if m.sum() < 10:
                continue
            out.append([np.median(F["L"][sl][m]), np.median(F["chi"][sl][..., 0][m]), np.median(F["chi"][sl][..., 1][m]),
                        np.median(xx[sl][m]), np.median(yy[sl][m]), 5.0, 1.0])     # boxes x5, always kept
    return np.array(out)


class Reference:
    """chi_ref = f(L*) + g(x, y): FAST-LTS-like start (f quadratic, g linear, h = 0.6, boxes kept), then Tukey IRLS
    (c = 4.685) with f a cubic B-spline on 4 knots at tone quantiles and g quadratic, at the start's scale, never
    below the median-based scale."""

    def __init__(self, V, W_, H_, seed=0):
        self.W, self.H = W_, H_
        L, y, xv, yv, w, isbox = V[:, 0], V[:, 1:3], V[:, 3] / W_ - 0.5, V[:, 4] / H_ - 0.5, V[:, 5], V[:, 6] > 0
        rng = np.random.default_rng(seed)
        l = (L - 50) / 50
        A0 = np.stack([np.ones_like(l), l, l ** 2, xv, yv], -1)
        n, p = len(V), A0.shape[1]
        h = int(0.6 * n)
        best = None
        for _ in range(150):
            idx = rng.choice(n, p + 2, replace=False)
            for _c in range(6):
                cf = np.linalg.lstsq(A0[idx] * w[idx, None], y[idx] * w[idx, None], rcond=None)[0]
                r = np.linalg.norm(y - A0 @ cf, axis=1)
                order = np.argsort(np.where(isbox, -1.0, r))      # boxes always kept
                idx = order[:h]
            obj = np.sort(r[~isbox])[:max(h - isbox.sum(), 1)].sum() if (~isbox).any() else r.sum()
            if best is None or obj < best[0]:
                best = (obj, cf, idx)
        _, cf, idx = best
        r = np.linalg.norm(y - A0 @ cf, axis=1)
        s_lts = np.sqrt(np.mean(r[idx] ** 2) / 2) * 1.2           # rough consistency factor for 60 % trimming
        self.knots = np.quantile(L, [0.2, 0.4, 0.6, 0.8])
        A = self._design(L, V[:, 3], V[:, 4])
        coef = np.linalg.lstsq(A, y, rcond=None)[0]
        for _ in range(25):
            r = np.linalg.norm(y - A @ coef, axis=1)
            s_med = np.median(r) / 1.1774
            s = max(s_lts, s_med)
            u = r / (4.685 * s)
            wt = np.where(u < 1, (1 - u ** 2) ** 2, 0.0) * w
            coef = np.linalg.lstsq(A * np.sqrt(wt)[:, None], y * np.sqrt(wt)[:, None], rcond=None)[0]
        self.coef = coef
        self.scale = s
        self.inlier_share = float((u < 1).mean())
        self.L_lo, self.L_hi = np.percentile(L, 1), np.percentile(L, 99)

    def _design(self, L, x, y):
        B = _bspline_basis(L, self.knots)
        xv, yv = x / self.W - 0.5, y / self.H - 0.5
        return np.hstack([B, np.stack([xv, yv, xv ** 2, yv ** 2, xv * yv], -1)])

    def predict(self, Lmap):
        H, W = Lmap.shape
        yy, xx = np.mgrid[0:H, 0:W]
        A = self._design(Lmap.ravel(), xx.ravel().astype(float), yy.ravel().astype(float))
        return (A @ self.coef).reshape(H, W, 2).astype(np.float32)


def noise_and_threshold(F, resid):
    """sigma by tone from differences of pixels SHIFT apart (median-scaled), plus kappa^2 G^2 fitted from binned
    medians of the residual over the edgy half; T = max(T0, 3 sigma)."""
    chi, L, G, u = F["chi"], F["L"], F["G"], F["usable"]
    d = chi[:, SHIFT:] - chi[:, :-SHIFT]
    ok = u[:, SHIFT:] & u[:, :-SHIFT]
    Lm = 0.5 * (L[:, SHIFT:] + L[:, :-SHIFT])
    edges = np.arange(0, 105, 5)
    sig = np.zeros(len(edges) - 1)
    for k in range(len(sig)):
        m = ok & (Lm >= edges[k]) & (Lm < edges[k + 1])
        if m.sum() > 200:
            sig[k] = np.sqrt(((1.4826 * np.median(np.abs(d[m]), axis=0)) ** 2).mean() / 2)
    good = sig > 0
    centres = 0.5 * (edges[:-1] + edges[1:])
    sig = np.interp(centres, centres[good], sig[good])
    sigma_noise = np.interp(L, centres, sig)
    r = np.linalg.norm(resid, axis=-1)
    edgy = u & (G > np.median(G[u]))
    qs = np.quantile(G[edgy], np.linspace(0, 1, 11))
    k2 = []
    for a, b in zip(qs[:-1], qs[1:]):
        m = edgy & (G >= a) & (G < b)
        if m.sum() > 200:
            s_bin = np.median(r[m]) / 1.1774
            k2.append(max(s_bin ** 2 - np.median(sigma_noise[m]) ** 2, 0) / max(np.median(G[m]) ** 2, 1e-8))
    kappa2 = float(np.median(k2)) if k2 else 0.0
    sigma = np.sqrt(sigma_noise ** 2 + kappa2 * G ** 2)
    return np.maximum(T0, 3 * sigma).astype(np.float32), kappa2


def run_capture(rgb_u8, boxes=None):
    F = features(rgb_u8)
    H, W = F["L"].shape
    V = votes(F, boxes)
    ref = Reference(V, W, H)
    chi_ref = ref.predict(F["L"])
    blur = lambda a: np.stack([cv2.GaussianBlur(a[..., k], (0, 0), SIGMA_C) for k in range(2)], -1)
    v = blur(F["chi"]) - blur(chi_ref)
    T, kappa2 = noise_and_threshold(F, F["chi"] - chi_ref)
    dn = np.linalg.norm(v, axis=-1) / T          # departure in units of T
    return dict(F=F, ref=ref, chi_ref=chi_ref, v=v, T=T, dn=dn, kappa2=kappa2, nvotes=len(V))


def ramp(x):
    """Synthesis 4.4: opacity 0 at T/2, 1/2 at T, 1 at 1.5 T."""
    return np.clip(x - 0.5, 0, 1)
