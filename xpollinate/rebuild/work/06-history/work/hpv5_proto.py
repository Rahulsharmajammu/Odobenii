"""Prototype of the proposed montage (bench only; not the rebuild itself).

Original (+ the print's outline, the paper taken as unpainted, and the strip 'unpainted tone, as assumed') |
Boosted (the assumed unpainted tone rendered grey, departures from it x k) |
Presence (the print in grey; colour where it departs from the assumed tone, hue from the departure's direction,
opacity rising smoothly; hatched where nothing can be judged) + a footer in words, no numbers.
"""
from __future__ import annotations

import io
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageCms, ImageDraw, ImageFont, ImageOps

import methods as M

LABEL = "Visualisation only - not a measurement"
SENSITIVITY = {"low": (3.5, 7.0), "normal": (2.5, 5.0), "high": (1.8, 3.8)}


def load(path, long_edge=2400):
    with Image.open(path) as im:
        icc = im.info.get("icc_profile")
        im = ImageOps.exif_transpose(im)
        if icc:
            try:
                src = ImageCms.ImageCmsProfile(io.BytesIO(icc))
                im = ImageCms.profileToProfile(im.convert("RGB"), src, ImageCms.createProfile("sRGB"), outputMode="RGB")
            except Exception:
                im = im.convert("RGB")
        im = im.convert("RGB")
        w, h = im.size
        s = long_edge / max(w, h)
        if s < 1:
            im = im.resize((round(w * s), round(h * s)), Image.Resampling.BOX)
        return np.asarray(im).astype(np.float32) / 255.0


def find_print(p: M.Prep):
    """The print as the region inside its paper border: the largest bright, smooth component, filled.  None when no
    border surrounds the picture (then the whole frame is used, and the footer says so)."""
    H, W = p.L.shape
    Lu = p.L[p.usable]
    T = np.quantile(Lu, 0.97) - 12
    mu = cv2.blur(p.L, (9, 9))
    sd = np.sqrt(np.maximum(cv2.blur(p.L * p.L, (9, 9)) - mu * mu, 0))
    m = ((p.L > T) & (sd < 3) & ~p.clipped).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    if n <= 1:
        return None
    k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    x, y, w, h, area = st[k]
    if w * h < 0.3 * W * H or area > 0.6 * w * h:            # not big, or not a ring
        return None
    cs, _ = cv2.findContours((lab == k).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = np.zeros((H, W), np.uint8)
    cv2.drawContours(out, cs, -1, 1, thickness=-1)
    return out.astype(bool)


def lab_to_rgb(L, a, b):
    lab = np.stack([L, a, b], -1).astype(np.float32)
    return np.clip(cv2.cvtColor(lab, cv2.COLOR_LAB2RGB), 0, 1)


def hatch(shape, step=9):
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    return ((xx + yy) % step) < 2


def render(rgb, p, res, box, k_boost=5.0):
    H, W = p.L.shape
    # boosted: the assumed tone neutral, departures x k, soft-limited so nothing clips into flat colour
    va, vb = res.va, res.vb
    mag = np.hypot(va, vb)
    lim = 60.0 * np.tanh(k_boost * mag / 60.0) / np.maximum(mag, 1e-6)
    boosted = lab_to_rgb(p.L, va * lim, vb * lim)
    # presence: grey print, colour by the departure's direction, opacity from z
    g = 0.30 + 0.55 * (p.L / 100.0)
    base = np.repeat(g[..., None], 3, 2)
    ang = np.arctan2(vb, va)
    hue = lab_to_rgb(np.full_like(p.L, 62.0), 55 * np.cos(ang), 55 * np.sin(ang))
    al = np.clip(res.alpha, 0, 1)
    paper = res.info.get("anchor_mask")
    if paper is not None:
        al = np.where(paper, 0.0, al)                   # the paper taken as unpainted is reference, not judged
    al = al[..., None]
    pres = base * (1 - al) + hue * al
    excl = ~p.usable
    if box is not None:
        excl = excl & box
    hz = hatch((H, W))
    pres[excl] = np.where(hz[excl][:, None], 0.55, 0.80)
    boosted[excl & hz] = 0.55
    # original with outlines: the print's edge (if found) and the paper taken as unpainted
    orig = rgb.copy()
    for m, col in ((box, (0.1, 0.8, 1.0)), (res.info.get("anchor_mask"), (1.0, 0.85, 0.1))):
        if m is None or not m.any():
            continue
        e = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
        orig[e] = col
    return orig, boosted, pres


def strip(res, p, width, height=60, k_boost=5.0):
    """The unpainted tone the tool assumed, black to paper: as it looks (top) and boosted around the paper (bottom),
    so a bend toward a paint colour is easy to see.  Tones with no unpainted evidence are hatched."""
    Lmin, Lmax = np.quantile(p.L[p.usable], [0.01, 0.995])
    Lg = np.linspace(Lmin, Lmax, width)
    ra, rb = res.ref_fn(Lg)
    top = lab_to_rgb(Lg[None, :].repeat(height // 2, 0), ra[None, :].repeat(height // 2, 0),
                     rb[None, :].repeat(height // 2, 0))
    pa, pb = ra[-1], rb[-1]
    ba, bb = pa + k_boost * (ra - pa), pb + k_boost * (rb - pb)
    bot = lab_to_rgb(np.full((height // 2, width), 60.0), ba[None, :].repeat(height // 2, 0),
                     bb[None, :].repeat(height // 2, 0))
    out = np.concatenate([top, bot], 0)
    Lc = res.info["Lc"]
    pick = res.info["pick"]
    unsupported = np.ones(width, bool)
    for k, L in enumerate(Lc):
        if pick[k] is not None:
            unsupported &= ~(np.abs(Lg - L) <= 1.5)
    hz = hatch(out.shape[:2], 7)
    for y in range(out.shape[0]):
        row = unsupported & hz[y]
        out[y, row] = 0.5
    return out


def footer_words(res, box_found, ring_used):
    w = [LABEL]
    if box_found:
        w.append("The print's edge was found (blue outline); only the print was used.")
    else:
        w.append("No paper border found: the whole frame was used, surroundings included.")
    w.append("Unpainted tone: taken from the photograph itself; paper from the brightest areas (yellow outline).")
    if ring_used:
        w.append("The light across the frame was measured on the paper border and allowed for.")
    w.extend(s[0].upper() + s[1:] + "." for s in res.warnings)
    return w


def montage(rgb, name, sensitivity="normal", ring=True, box=None, out=None):
    p = M.prep(rgb)
    found = find_print(p) if box is None else box
    lo, hi = SENSITIVITY[sensitivity]
    res = M.m3_proposed(p, mask=found, ring_plane=ring, lo=lo, hi=hi)
    ring_used = ring and not any("no paper around" in s for s in res.warnings)
    orig, boosted, pres = render(rgb, p, res, found)
    H, W = p.L.shape
    st = strip(res, p, W)
    orig2 = np.concatenate([orig, np.ones((6, W, 3)), st], 0)
    pad = np.ones((st.shape[0] + 6, W, 3))
    panels = [orig2, np.concatenate([boosted, pad], 0), np.concatenate([pres, pad], 0)]
    gap = np.ones((orig2.shape[0], 10, 3))
    img = np.concatenate([panels[0], gap, panels[1], gap, panels[2]], 1)
    im = Image.fromarray((img * 255).astype(np.uint8))
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 22)
    except OSError:
        font = ImageFont.load_default()
    words = [name] + footer_words(res, found is not None, ring_used)
    lh = 30
    canvas = Image.new("RGB", (im.width, im.height + 40 + lh * len(words)), "white")
    canvas.paste(im, (0, 40))
    d = ImageDraw.Draw(canvas)
    for i, t in enumerate(["Original (and the unpainted tone it assumed)", "Boosted around the unpainted tone",
                           "Where colour departs from it"]):
        d.text((i * (W + 10) + 10, 8), t, fill="black", font=font)
    for i, t in enumerate(words):
        d.text((12, im.height + 46 + i * lh), t, fill="black", font=font)
    if out:
        canvas.save(out)
    return canvas, res
