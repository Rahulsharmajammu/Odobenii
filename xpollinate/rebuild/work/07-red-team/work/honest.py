"""A prototype of the design argued for in Part 2 of the report.

1. The unpainted print is modelled explicitly, per capture: a*, b* = f(L*) + g(x, y), fitted on marked areas
   (f a cubic only when the marks cover the lightness range, g a plane only when they span the frame).
2. That model is SHOWN: the 'assumed unpainted' picture (the capture's own L* with the model's a*, b*).
3. The unit of departure is the marks' disagreement with each other (leave one mark out), not pixel noise, with a
   floor of about one or two 8-bit code steps.
4. Tripwires, in words: a mark that disagrees with the others; lightness or places the marks do not cover; departures
   that sit on edges; departures that change smoothly across the frame.
5. With a second capture of the same print (other light, other device), departures are kept only where both captures
   show them in a similar direction; the rest is drawn as 'seen in one capture only'.
"""
from __future__ import annotations

import numpy as np
import cv2
from scipy import ndimage as ndi
from skimage import color

FLOOR = 0.8            # a*b* units: about one or two 8-bit sRGB code steps; nothing finer is claimed
CLIP_WHITE = 0.97
NEAR_BLACK_L = 8.0


def prepare(rgb_u8, smooth=1.0):
    rgb = rgb_u8.astype(np.float32) / 255.0
    lab = color.rgb2lab(rgb).astype(np.float32)
    if smooth:                                          # the same light smoothing on all three: no L*/a*b* mismatch
        lab = np.stack([ndi.gaussian_filter(lab[..., k], smooth) for k in range(3)], -1)
    usable = (rgb.max(axis=-1) < CLIP_WHITE) & (lab[..., 0] > NEAR_BLACK_L)
    usable = ndi.binary_erosion(usable, iterations=2)
    return lab, usable


def _design(Lv, xv, yv, deg, plane, W, H):
    l = (Lv - 50.0) / 50.0
    cols = [np.ones_like(l)] + [l ** k for k in range(1, deg + 1)]
    if plane:
        cols += [(xv / W) - 0.5, (yv / H) - 0.5]
    return np.stack(cols, -1)


def _fit(Lv, xv, yv, av, bv, deg, plane, W, H):
    A = _design(Lv, xv, yv, deg, plane, W, H)
    keep = np.ones(len(Lv), bool)
    for _ in range(3):                                 # trimmed refits: a stray speck in a mark does not steer it
        ca = np.linalg.lstsq(A[keep], av[keep], rcond=None)[0]
        cb = np.linalg.lstsq(A[keep], bv[keep], rcond=None)[0]
        r = np.hypot(av - A @ ca, bv - A @ cb)
        s = 1.4826 * np.median(np.abs(r - np.median(r))) + 1e-6
        keep = r <= np.median(r) + 4 * s
    return ca, cb


class Reference:
    def __init__(self, lab, usable, boxes):
        H, W = usable.shape
        self.H, self.W = H, W
        self.boxes = boxes
        Lc, ac, bc = lab[..., 0], lab[..., 1], lab[..., 2]
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        self.marks = []
        for (x0, y0, x1, y1) in boxes:
            m = np.zeros((H, W), bool)
            m[int(y0):int(y1), int(x0):int(x1)] = True
            m &= usable
            if m.sum() < 50:
                continue
            idx = np.flatnonzero(m)
            if len(idx) > 4000:
                idx = np.random.default_rng(0).choice(idx, 4000, replace=False)
            self.marks.append(dict(box=(x0, y0, x1, y1), L=Lc.ravel()[idx], x=xx.ravel()[idx], y=yy.ravel()[idx],
                                   a=ac.ravel()[idx], b=bc.ravel()[idx]))
        allL = np.concatenate([m["L"] for m in self.marks])
        self.L_lo, self.L_hi = np.percentile(allL, 1), np.percentile(allL, 99)
        hist, _ = np.histogram(allL, bins=np.arange(self.L_lo, self.L_hi + 5, 5))
        gap = 0; run = 0
        for c in hist:
            run = run + 1 if c < 20 else 0
            gap = max(gap, run)
        self.deg = 3 if (self.L_hi - self.L_lo >= 40 and gap * 5 <= 15) else 1
        cx = np.array([np.mean(m["x"]) for m in self.marks]); cy = np.array([np.mean(m["y"]) for m in self.marks])
        self.plane = len(self.marks) >= 4 and np.ptp(cx) >= 0.4 * W and np.ptp(cy) >= 0.4 * H
        cat = lambda k: np.concatenate([m[k] for m in self.marks])
        self.ca, self.cb = _fit(cat("L"), cat("x"), cat("y"), cat("a"), cat("b"), self.deg, self.plane, W, H)
        # leave one mark out: how far each mark sits from the model fitted without it
        self.loo = []
        for j, mj in enumerate(self.marks):
            others = [m for i, m in enumerate(self.marks) if i != j]
            if len(others) < 2:
                self.loo.append(np.array([np.nan, np.nan]))
                continue
            catj = lambda k: np.concatenate([m[k] for m in others])
            plane_j = self.plane and len(others) >= 3
            ca, cb = _fit(catj("L"), catj("x"), catj("y"), catj("a"), catj("b"), self.deg, plane_j, W, H)
            A = _design(mj["L"], mj["x"], mj["y"], self.deg, plane_j, W, H)
            self.loo.append(np.array([np.median(mj["a"] - A @ ca), np.median(mj["b"] - A @ cb)]))
        self.loo = np.array(self.loo)
        mags = np.linalg.norm(self.loo, axis=1)
        good = np.isfinite(mags)
        # within-mark texture and noise, about each mark's own median residual
        res_pix = []
        for mj in self.marks:
            A = _design(mj["L"], mj["x"], mj["y"], self.deg, self.plane, W, H)
            ra, rb = mj["a"] - A @ self.ca, mj["b"] - A @ self.cb
            res_pix.append(np.hypot(ra - np.median(ra), rb - np.median(rb)))
        s_pix = float(np.median(np.concatenate(res_pix))) * 1.2
        s_sys = float(np.sqrt(np.median(mags[good] ** 2))) if good.sum() >= 2 else np.nan
        self.s_pix, self.s_sys = s_pix, s_sys
        self.scale = float(max(FLOOR, np.sqrt(s_pix ** 2 + (s_sys if np.isfinite(s_sys) else 2.0) ** 2)))
        med = np.nanmedian(mags) if np.isfinite(mags).any() else np.nan
        self.disagree = [j for j, mg in enumerate(mags) if np.isfinite(mg) and mg > max(3 * med, 2 * s_pix, 1.5)]
        self.hull = None
        pts = np.array([[x, y] for (x0, y0, x1, y1) in [m["box"] for m in self.marks]
                        for (x, y) in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))], np.float32)
        self.hull = cv2.convexHull(pts)

    def predict(self, lab):
        H, W = lab.shape[:2]
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        Lc = np.clip(lab[..., 0], self.L_lo - 3, self.L_hi + 3)  # held flat outside what the marks cover
        A = _design(Lc.ravel(), xx.ravel(), yy.ravel(), self.deg, self.plane, W, H)
        return (A @ self.ca).reshape(H, W), (A @ self.cb).reshape(H, W)

    def uncovered(self, lab):
        """Lightness the marks do not cover, and (with a plane) places far outside the marks' hull."""
        L = lab[..., 0]
        out = (L < self.L_lo - 3) | (L > self.L_hi + 3)
        if self.plane:
            hull = np.zeros(L.shape, np.uint8)
            c = self.hull.reshape(-1, 2).mean(axis=0)
            big = (self.hull.reshape(-1, 2) - c) * 1.25 + c
            cv2.fillConvexPoly(hull, big.astype(np.int32), 1)
            out |= hull == 0
        return out


def departure(lab, usable, ref: Reference):
    ra, rb = ref.predict(lab)
    va, vb = lab[..., 1] - ra, lab[..., 2] - rb
    z = np.hypot(va, vb) / ref.scale
    z[~usable] = 0
    return dict(va=va, vb=vb, z=z, ra=ra, rb=rb, uncovered=ref.uncovered(lab) & usable)


def assumed_unpainted(lab, d):
    lab2 = np.stack([lab[..., 0], d["ra"], d["rb"]], -1)
    return (np.clip(color.lab2rgb(lab2), 0, 1) * 255).astype(np.uint8)


def ramp(z, lo=2.0, hi=6.0):
    return np.clip((z - lo) / (hi - lo), 0, 1)           # linear: strength reads as strength; no early saturation


def tripwires(lab, usable, d, ref: Reference, shown):
    words = []
    for j in ref.disagree:
        words.append(f"mark {j + 1} disagrees with the others: it may hold paint, or the light varies more than the "
                     "model allows")
    if np.isfinite(ref.s_sys) and ref.s_sys > max(2 * ref.s_pix, 1.5):
        words.append("the marks disagree with each other by more than their own texture: one may hold paint, or the "
                     "light varies more than the model allows; the map is shown at lower sensitivity")
    if not ref.plane:
        words.append("the marks do not span the frame: a colour cast across the frame cannot be told from a wash")
    if ref.deg == 1:
        words.append("the marks cover little of the lightness range: tones outside it are guessed (hatched)")
    if shown.any():
        L = lab[..., 0]
        g = np.hypot(*np.gradient(L))
        edge = ndi.binary_dilation(g > 3.0, iterations=2) & usable
        r_edge = (shown & edge).sum() / max(shown.sum(), 1)
        base = edge.sum() / max(usable.sum(), 1)
        if r_edge > max(2 * base, 0.3):
            words.append("much of what is shown sits on edges: colour fringes from the lens or the file are likely")
        # smooth across the frame?  fit a quadratic surface in x, y to the departure over usable pixels
        H, W = L.shape
        yy, xx = np.mgrid[0:H:8, 0:W:8]
        sub = usable[::8, ::8]
        X = np.stack([np.ones(sub.sum()), xx[sub] / W, yy[sub] / H, (xx[sub] / W) ** 2, (yy[sub] / H) ** 2,
                      xx[sub] * yy[sub] / (W * H)], -1)
        fa = np.linalg.lstsq(X, d["va"][::8, ::8][sub], rcond=None)[0]
        fb = np.linalg.lstsq(X, d["vb"][::8, ::8][sub], rcond=None)[0]
        Xf = np.stack([np.ones(H * W), (np.mgrid[0:H, 0:W][1].ravel()) / W, (np.mgrid[0:H, 0:W][0].ravel()) / H,
                       (np.mgrid[0:H, 0:W][1].ravel() / W) ** 2, (np.mgrid[0:H, 0:W][0].ravel() / H) ** 2,
                       (np.mgrid[0:H, 0:W][1].ravel() * np.mgrid[0:H, 0:W][0].ravel()) / (W * H)], -1)
        sa, sb = (Xf @ fa).reshape(H, W), (Xf @ fb).reshape(H, W)
        z2 = np.hypot(d["va"] - sa, d["vb"] - sb) / ref.scale
        gone = shown & (z2 < 2.0)
        if gone.sum() > 0.5 * shown.sum():
            words.append("most of what is shown changes smoothly across the frame, as uneven light does; a wash can "
                         "look the same: a second photograph under other light tells them apart")
    return words


def register(src_u8, dst_u8):
    """Homography taking src onto dst (SIFT, ratio test, RANSAC)."""
    sift = cv2.SIFT_create(4000)
    g1 = cv2.cvtColor(src_u8, cv2.COLOR_RGB2GRAY); g2 = cv2.cvtColor(dst_u8, cv2.COLOR_RGB2GRAY)
    k1, d1 = sift.detectAndCompute(g1, None); k2, d2 = sift.detectAndCompute(g2, None)
    m = cv2.BFMatcher().knnMatch(d1, d2, k=2)
    good = [a for a, b in m if a.distance < 0.75 * b.distance]
    p1 = np.float32([k1[a.queryIdx].pt for a in good]); p2 = np.float32([k2[a.trainIdx].pt for a in good])
    Hm, inl = cv2.findHomography(p1, p2, cv2.RANSAC, 2.0)
    return Hm, int(inl.sum())


def persistent(dA, usableA, dB_warped, usableB_warped, zmin=1.5, cos_min=0.5):
    va, vb, za = dA["va"], dA["vb"], dA["z"]
    wa, wb, zb = dB_warped["va"], dB_warped["vb"], dB_warped["z"]
    both = usableA & usableB_warped
    cos = (va * wa + vb * wb) / (np.hypot(va, vb) * np.hypot(wa, wb) + 1e-6)
    keep = both & (za >= zmin) & (zb >= zmin) & (cos >= cos_min)
    one = both & ((za >= zmin) | (zb >= zmin)) & ~keep
    zmin_map = np.minimum(za, zb)
    return keep, one, zmin_map


def picture(rgb_u8, va, vb, op, hatch_masks=(), grey_mask=None):
    g = cv2.cvtColor(rgb_u8, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    base = np.repeat((0.25 + 0.5 * g)[..., None], 3, axis=2)
    ang = np.arctan2(vb, va)
    hsv = np.stack([(np.degrees(ang) % 360) / 2, np.full_like(ang, 255), np.full_like(ang, 255)], -1).astype(np.uint8)
    col = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB).astype(np.float32) / 255.0
    out = base * (1 - op[..., None]) + col * op[..., None]
    H, W = g.shape
    diag = (np.add.outer(np.arange(H), np.arange(W)) // 5) % 2 == 0
    anti = (np.subtract.outer(np.arange(H), np.arange(W)) // 5) % 2 == 0
    if grey_mask is not None:
        out[grey_mask & anti] = (0.55, 0.55, 0.55)
    for m in hatch_masks:
        out[m & diag] = (0.9, 0.9, 0.9)
    return (np.clip(out, 0, 1) * 255).astype(np.uint8)
