"""v2 montage prototype (bench only): 2 x 2.
  1 Capture A, with the print edge (blue) and the paper taken as unpainted (yellow) outlined
  2 Assumed unpainted: the model's colour at every pixel's lightness, exaggerated about the paper by the same factor as
    panel 3; hatched where the model is guessing (a wide gap between supported tones) or not judging
  3 Boost: the model rendered neutral, departures x K (capture A)
  4 Seen in both: departures present in both captures in the same direction; hue = direction, opacity linear 2 -> 6
    units on the weaker capture; hatched where nothing can be judged or only one capture departs
"""
from __future__ import annotations

import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import pairs as P
import pairs2 as P2

K = 4.0


def lab2rgb(L, a, b):
    return np.clip(cv2.cvtColor(np.stack([L, a, b], -1).astype(np.float32), cv2.COLOR_LAB2RGB), 0, 1)


def soft(va, vb, k=K, lim=60.0):
    m = np.hypot(va, vb)
    f = lim * np.tanh(k * m / lim) / np.maximum(m, 1e-6)
    return va * f, vb * f


def hatch(shape, step=9):
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    return ((xx + yy) % step) < 2


def outline(img, m, col):
    if m is None or not m.any():
        return
    e = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
    img[e] = col


def montage(case_idx, out):
    name, recipe, tone, paper, cA, cB, extra = P.CASES[case_idx]
    keep = {}
    P2.evaluate2(name, recipe, tone, paper, cA, cB, seed=case_idx, keep=keep, **extra)
    p, r = keep["pA"], keep["rA"]
    H, W = p.L.shape
    hz = hatch((H, W))
    # 1 capture
    c1 = np.clip(keep["rgbA"], 0, 1).copy()
    outline(c1, keep["sc"].mount == 0, (0.1, 0.8, 1.0))
    outline(c1, r.info["anchor_mask"], (1.0, 0.85, 0.1))
    # 2 assumed unpainted
    ma, mb = p.a - r.va, p.b - r.vb
    anc = r.info["anchor_t"]
    pa_, pb_ = (anc[1], anc[2]) if anc is not None else (0.0, 0.0)
    da, db = soft(ma - pa_, mb - pb_)
    c2 = lab2rgb(p.L, pa_ + da, pb_ + db)
    notj = ~keep["jA"] & p.usable
    c2[(keep["gA"] | notj) & hz] = 0.5
    # 3 boost
    ba, bb = soft(r.va, r.vb)
    c3 = lab2rgb(p.L, ba, bb)
    c3[~p.usable & hz] = 0.5
    # 4 seen in both
    g = 0.30 + 0.55 * p.L / 100.0
    c4 = np.repeat(g[..., None], 3, 2)
    ang = np.arctan2(r.vb, r.va)
    hue = lab2rgb(np.full_like(p.L, 62.0), 55 * np.cos(ang), 55 * np.sin(ang))
    al = np.where(keep["both"], P.lin_opacity(np.minimum(keep["zA"], keep["zB"])), 0.0)[..., None]
    c4 = c4 * (1 - al) + hue * al
    one_only = ((P.lin_opacity(keep["zA"]) >= 0.25) ^ (P.lin_opacity(keep["zB"]) >= 0.25)) & ~keep["both"]
    nj = ~(keep["jA"] & keep["jB"]) & (keep["sc"].mount == 0)
    c4[(one_only | nj) & hz] = 0.45
    gap = np.ones((H, 10, 3))
    top = np.concatenate([c1, gap, c2], 1)
    bot = np.concatenate([c3, gap, c4], 1)
    img = np.concatenate([top, np.ones((40, top.shape[1], 3)), bot], 0)
    im = Image.fromarray((img * 255).astype(np.uint8))
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 22)
    except OSError:
        font = ImageFont.load_default()
    canvas = Image.new("RGB", (im.width, im.height + 80), "white")
    canvas.paste(im, (0, 40))
    d = ImageDraw.Draw(canvas)
    d.text((10, 8), "1 Photograph A (print edge, paper taken as unpainted)", fill="black", font=font)
    d.text((W + 20, 8), "2 Assumed unpainted (hatched: guessed)", fill="black", font=font)
    d.text((10, H + 48), "3 Boosted around the assumed unpainted tone", fill="black", font=font)
    d.text((W + 20, H + 48), "4 Seen in both photographs (hatched: one only, or not judged)", fill="black", font=font)
    d.text((10, im.height + 50), f"{name} | Visualisation only - not a measurement", fill="black", font=font)
    canvas.save(out)
    small = canvas.copy()
    small.thumbnail((1500, 2000))
    small.save(str(out).replace(".png", "_small.png"))


if __name__ == "__main__":
    for i in [int(a) for a in sys.argv[1:]]:
        montage(i, f"img/v2_{P.CASES[i][0].split()[0]}.png")
