"""TODO.md's proposed pipeline, as written (steps 1-8 and the presence map), for testing.

Choices TODO.md leaves open are made plainly and listed in REPORT_CHOICES; none is made to help or hurt it.
"""
from __future__ import annotations

import numpy as np
import cv2
from scipy import ndimage as ndi
from skimage import color

REPORT_CHOICES = {
    "band_width_L": 2.0, "smooth_bands": 5, "a_b_median_px": 5, "speck_median_px": 3, "clip_white": 0.97,
    "near_black_L": 8.0, "opacity_lo_hi": (2.0, 5.0), "opacity_gamma": 0.6, "spread_floor": 0.05,
    "auto_rounds": 4, "auto_keep_z": 3.0,
}


def boxes_to_mask(shape, boxes):
    m = np.zeros(shape, bool)
    for x0, y0, x1, y1 in boxes:
        m[int(y0):int(y1), int(x0):int(x1)] = True
    return m


def prepare(rgb_u8, c=REPORT_CHOICES):
    rgb = rgb_u8.astype(np.float32) / 255.0
    lab = color.rgb2lab(rgb).astype(np.float32)
    L = lab[..., 0]
    a = ndi.median_filter(lab[..., 1], size=c["a_b_median_px"])
    b = ndi.median_filter(lab[..., 2], size=c["a_b_median_px"])
    usable = (rgb.max(axis=-1) < c["clip_white"]) & (L > c["near_black_L"])
    return L, a, b, usable


def band_reference(L, a, b, sel, c=REPORT_CHOICES):
    """Median (a*, b*) and robust spread in each L* band over the pixels in sel; empty bands interpolated
    (constant beyond the covered range: the 'extrapolated and flagged' part), then smoothed along L*."""
    bw = c["band_width_L"]
    edges = np.arange(0, 100 + bw, bw)
    nb = len(edges) - 1
    idx = np.clip(np.digitize(L[sel], edges) - 1, 0, nb - 1)
    av, bv = a[sel], b[sel]
    med_a = np.full(nb, np.nan); med_b = np.full(nb, np.nan); spr = np.full(nb, np.nan); cnt = np.bincount(idx, minlength=nb)
    for k in range(nb):
        m = idx == k
        if m.sum() < 30:
            continue
        ma, mb = np.median(av[m]), np.median(bv[m])
        sa = 1.4826 * np.median(np.abs(av[m] - ma)); sb = 1.4826 * np.median(np.abs(bv[m] - mb))
        med_a[k], med_b[k], spr[k] = ma, mb, np.sqrt((sa ** 2 + sb ** 2) / 2)
    ok = np.isfinite(med_a)
    centres = 0.5 * (edges[:-1] + edges[1:])
    covered = (centres >= centres[ok].min() - bw) & (centres <= centres[ok].max() + bw) if ok.any() else np.zeros(nb, bool)
    fa = np.interp(centres, centres[ok], med_a[ok]); fb = np.interp(centres, centres[ok], med_b[ok])
    fs = np.interp(centres, centres[ok], spr[ok])
    k = c["smooth_bands"]
    ker = np.ones(k) / k
    pad = k // 2
    sm = lambda v: np.convolve(np.pad(v, pad, mode="edge"), ker, mode="valid")
    fa, fb, fs = sm(fa), sm(fb), np.maximum(sm(fs), c["spread_floor"])
    return dict(centres=centres, a=fa, b=fb, spread=fs, covered=covered, raw_spread=spr, counts=cnt)


def feature(L, a, b, ref):
    ra = np.interp(L, ref["centres"], ref["a"]); rb = np.interp(L, ref["centres"], ref["b"])
    s = np.interp(L, ref["centres"], ref["spread"])
    va, vb = a - ra, b - rb
    z = np.hypot(va, vb) / s
    return va, vb, z


def run(rgb_u8, picks=None, c=REPORT_CHOICES):
    L, a, b, usable = prepare(rgb_u8, c)
    if picks:
        sel = boxes_to_mask(L.shape, picks) & usable
        ref = band_reference(L, a, b, sel, c)
        how = "picked"
    else:                                                   # automatic fallback: fit, set aside, refit
        sel = usable.copy()
        for _ in range(c["auto_rounds"]):
            ref = band_reference(L, a, b, sel, c)
            _, _, z = feature(L, a, b, ref)
            sel = usable & (z < c["auto_keep_z"])
        ref = band_reference(L, a, b, sel, c)
        how = "automatic"
    va, vb, z = feature(L, a, b, ref)
    z = ndi.median_filter(z, size=c["speck_median_px"])
    lo, hi = c["opacity_lo_hi"]
    t = np.clip((z - lo) / (hi - lo), 0, 1)
    op = (t * t * (3 - 2 * t)) ** c["opacity_gamma"]        # smooth ramp, saturating early
    op[~usable] = 0
    return dict(L=L, a=a, b=b, usable=usable, ref=ref, va=va, vb=vb, z=z, opacity=op, how=how, sel=sel)


def presence_picture(rgb_u8, res):
    """Print in grey; colour over it, hue from the vector's angle, opacity from res['opacity']; hatched where it
    cannot judge."""
    g = cv2.cvtColor(rgb_u8, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    base = np.repeat((0.25 + 0.5 * g)[..., None], 3, axis=2)
    ang = np.arctan2(res["vb"], res["va"])
    hsv = np.stack([(np.degrees(ang) % 360) / 2, np.full_like(ang, 255), np.full_like(ang, 255)], -1).astype(np.uint8)
    col = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB).astype(np.float32) / 255.0
    op = res["opacity"][..., None]
    out = base * (1 - op) + col * op
    hatch = (~res["usable"]) & ((np.add.outer(np.arange(g.shape[0]), np.arange(g.shape[1])) // 6) % 2 == 0)
    out[hatch] = (0.85, 0.85, 0.85)
    return (np.clip(out, 0, 1) * 255).astype(np.uint8)
