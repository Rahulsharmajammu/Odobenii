"""TODO.md's proposed pipeline, as written: CIELAB, a 5 px median on a* and b*, clipped / near-black masks, the
reference as the median (a*, b*) in each L* band smoothed along L*, its robust spread per band, the automatic
fallback (fit on the whole image, set pixels far from the fit aside, refit, a few rounds), the vector length in
spreads, a small median on the length map, and an opacity ramp from 2 to 5 spreads."""
from __future__ import annotations

import cv2
import numpy as np

BAND = 2.0          # L* per band
SMOOTH = 5          # bands in the running mean along L*
ROUNDS = 3
FAR = 3.0           # spreads beyond which a pixel is set aside for the next round
RAMP = (2.0, 5.0)


def _bands(L):
    return np.clip((L / BAND).astype(int), 0, int(100 / BAND))


def _fit(L, a, b, keep):
    nb = int(100 / BAND) + 1
    idx = _bands(L[keep])
    med = np.full((nb, 2), np.nan)
    spr = np.full(nb, np.nan)
    aa, bb = a[keep], b[keep]
    for k in range(nb):
        s = idx == k
        if s.sum() < 50:
            continue
        ma, mb = np.median(aa[s]), np.median(bb[s])
        med[k] = ma, mb
        r = np.hypot(aa[s] - ma, bb[s] - mb)
        spr[k] = max(np.median(r) / 1.1774, 0.3)
    ok = np.isfinite(spr)
    x = np.arange(nb)
    for j in range(2):
        med[:, j] = np.interp(x, x[ok], med[ok, j])
    spr = np.interp(x, x[ok], spr[ok])
    ker = np.ones(SMOOTH) / SMOOTH
    pad = SMOOTH // 2
    for j in range(2):
        med[:, j] = np.convolve(np.pad(med[:, j], pad, mode="edge"), ker, mode="valid")
    spr = np.convolve(np.pad(spr, pad, mode="edge"), ker, mode="valid")
    return med, spr


def _eval(L, med, spr):
    xf = np.clip(L / BAND - 0.5, 0, len(spr) - 1)
    x = np.arange(len(spr))
    ra = np.interp(xf, x, med[:, 0])
    rb = np.interp(xf, x, med[:, 1])
    s = np.interp(xf, x, spr)
    return ra, rb, s


def todo(img_u8: np.ndarray):
    rgb = img_u8.astype(np.float32) / 255.0
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    L = lab[..., 0]
    a = cv2.medianBlur(np.ascontiguousarray(lab[..., 1]), 5)
    b = cv2.medianBlur(np.ascontiguousarray(lab[..., 2]), 5)
    clipped = (img_u8 >= 250).any(axis=2)
    dark = L < 10
    valid = ~clipped & ~dark
    keep = valid.copy()
    for _ in range(ROUNDS):
        med, spr = _fit(L, a, b, keep)
        ra, rb, s = _eval(L, med, spr)
        z = np.hypot(a - ra, b - rb) / s
        keep = valid & (z < FAR)
    z = cv2.medianBlur(z.astype(np.float32), 5)
    t = np.clip((z - RAMP[0]) / (RAMP[1] - RAMP[0]), 0, 1)
    alpha = t * t * (3 - 2 * t)
    alpha[~valid] = 0
    return {"alpha": alpha.astype(np.float32), "show": valid, "z": z, "presence_at": 0.5,
            "ref": (med, spr), "da": a - ra, "db": b - rb, "L": L}
