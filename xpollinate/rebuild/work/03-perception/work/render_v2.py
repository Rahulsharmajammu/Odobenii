"""Pictures for design v2 (after the merge with the conservation report).

A capture | C where colour departs from the print's own tone (bright on a dimmed print)
D the print as expected unpainted, its colour x4 | B departures from it x4 (so D + B = the capture's colour x4)
Blink: D <-> capture x4.  Strip (one tone axis, paper to shadow): the expected colour x4; the tone; a thin wash and a
small clear touch, injected into this capture's own residual texture at that tone, as B and C draw them.  Footer:
words, and the fixed sentence on what a blank means.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter

import colour as C
import pipelines as PL
import render as R

BLANK = ("Blank in C means no colour departs from the print's own tone here, in this capture, by more than this "
         "capture's own error. It does not mean unpainted: thin washes (see the strip), colourless or tone-matched "
         "media, and anything hatched cannot show.")
GAIN = 4.0


def lift(Lstar):
    return 15.0 + 0.83 * Lstar                    # shadows lifted a little, so colour has room there


def lab_picture(Lstar, a, b, frac=0.95):
    """(L*, a*, b*) to 8-bit sRGB, out-of-gamut colours brought in by lowering chroma at constant lightness and hue."""
    lab = np.stack([Lstar, a, b], -1).astype(np.float32)
    ok = C.lin_to_oklab(C.lab_to_lin(lab))
    Lo = np.clip(ok[..., 0], 0, 1)
    cc = np.hypot(ok[..., 1], ok[..., 2])
    h = np.arctan2(ok[..., 2], ok[..., 1])
    cm = C.max_chroma_oklab(Lo, h) * frac
    cc = np.minimum(cc, cm)
    return R.ok_to_srgb8(R.oklch(Lo, cc, h))


def hatch_over(img, mask, grey=(150, 150, 150)):
    out = img.copy()
    hz = R.hatch(mask.shape) & mask
    out[mask] = (0.55 * out[mask] + 0.45 * 90).astype(np.uint8)
    out[hz] = grey
    return out


def pictures(img8, res):
    L = res["L"]
    Ll = lift(L)
    ref = res["fit"]["ref"]
    dep = np.where(res["valid"][..., None], res["fit"]["resid"], 0)
    D = lab_picture(Ll, GAIN * ref[..., 0], GAIN * ref[..., 1])
    B = lab_picture(Ll, GAIN * dep[..., 0], GAIN * dep[..., 1])
    A4 = lab_picture(Ll, GAIN * (ref[..., 0] + dep[..., 0]), GAIN * (ref[..., 1] + dep[..., 1]))
    Cp = R.presence_picture(res)
    lo = res["leftout"]
    return {"A": img8, "B": hatch_over(B, lo), "C": Cp, "D": hatch_over(D, lo), "A4": hatch_over(A4, lo)}


def _patch_window(res, t, size=96):
    """The size x size window whose pixels are most often usable, near tone t and not drawn in C."""
    L, v = res["L"], res["valid"]
    m = (v & (np.abs(L - t) <= 4) & (res["opacity"] < 0.2)).astype(np.float32)
    s = gaussian_filter(m, size / 4)
    s[:size // 2] = s[-size // 2:] = 0
    s[:, :size // 2] = s[:, -size // 2:] = 0
    y, x = np.unravel_index(np.argmax(s), s.shape)
    if m[y - size // 2:y + size // 2, x - size // 2:x + size // 2].mean() < 0.3:
        return None
    return y - size // 2, x - size // 2


def _bootstrap_patch(res, t, size=96, block=8, seed=0):
    """This capture's own residual texture at tone t: size x size assembled from 8 x 8 blocks of the residual field
    whose pixels are all usable, within 4 L* of t and not drawn in C (a block bootstrap keeps the noise's local
    correlation, JPEG blocks included).  None if the capture has too few such blocks."""
    L, v, r = res["L"], res["valid"], res["fit"]["resid"]
    ok = v & (np.abs(L - t) <= 4) & (res["opacity"] < 0.2)
    h, w = ok.shape
    hb, wb = h // block, w // block
    okb = ok[:hb * block, :wb * block].reshape(hb, block, wb, block).all(axis=(1, 3))
    ys, xs = np.nonzero(okb)
    if len(ys) < 20:
        return None
    rng = np.random.default_rng(seed)
    n = (size // block) ** 2
    pick = rng.integers(0, len(ys), n)
    out = np.zeros((size, size, 2), np.float32)
    k = 0
    for by in range(size // block):
        for bx in range(size // block):
            y, x = ys[pick[k]] * block, xs[pick[k]] * block
            out[by * block:(by + 1) * block, bx * block:(bx + 1) * block] = r[y:y + block, x:x + block]
            k += 1
    return out


def strip(res, tones=None, size=96, thin=1.3, clear=5.0, hue_deg=35.0):
    """The unified strip.  Wash sizes are a*b* units at L* 80, scaled with (L* + 16)/116 as a transparent dye's are."""
    fit = res["fit"]
    edges = fit["edges"]
    nb = len(edges) - 1
    Lv = res["L"][res["valid"]]
    if tones is None:
        tones = [95, 85, 75, 63, 50, 38, 26, 15]
    lo_ok, hi_ok = np.percentile(Lv, 0.5), np.percentile(Lv, 99.5)
    yy, xx = np.mgrid[0:size, 0:size]
    big = ((xx - size / 2) ** 2 + (yy - size / 2) ** 2) <= (size * 0.34) ** 2
    big = gaussian_filter(big.astype(np.float32), 2)
    small = ((xx - size / 2) ** 2 + (yy - size / 2) ** 2) <= 4.5 ** 2
    small = gaussian_filter(small.astype(np.float32), 0.8)
    hv = np.array([np.cos(np.deg2rad(hue_deg)), np.sin(np.deg2rad(hue_deg))], np.float32)
    rows = {k: [] for k in ("expected", "tone", "thinB", "thinC", "clearC")}
    for t in tones:
        b = int(np.clip(np.searchsorted(edges, t, side="right") - 1, 0, nb - 1))
        z = np.zeros((1, 1), np.float32)
        refc = PL.ref_at(np.array([[t]], np.float32), z, z, fit["beta"], fit["knots"], fit["spatial"],
                         fit["cast_scaled"])[0, 0]
        cell_L = np.full((size, size), lift(t), np.float32)
        rows["expected"].append(lab_picture(cell_L, np.full_like(cell_L, GAIN * refc[0]), np.full_like(cell_L, GAIN * refc[1])))
        rows["tone"].append(lab_picture(cell_L, np.zeros_like(cell_L), np.zeros_like(cell_L)))
        rpatch = _bootstrap_patch(res, t, size)
        usable = (lo_ok <= t <= hi_ok) and rpatch is not None
        if not usable:
            blank = np.full((size, size, 3), 110, np.uint8)
            blank[R.hatch((size, size))] = 170
            for k in ("thinB", "thinC", "clearC"):
                rows[k].append(blank)
            continue
        scale = (t + 16) / 96.0
        for key, mask, amt in (("thin", big, thin), ("clear", small, clear)):
            pr = rpatch + (mask[..., None] * hv * amt * scale)
            if key == "thin":
                rows["thinB"].append(lab_picture(cell_L, GAIN * pr[..., 0], GAIN * pr[..., 1]))
            # C as the capture's own yardsticks at this tone would draw it
            ms = []
            for d in res["ms"]:
                s = d["sigma"]
                rs = np.stack([gaussian_filter(pr[..., i], s) for i in range(2)], -1) if s > 0 else pr
                m = np.linalg.norm(rs, axis=-1) / d["spread"][b]
                ms.append({"sigma": s, "r": rs, "m": m.astype(np.float32), "spread": d["spread"]})
            band = np.full((size, size), b)
            lo, hi = res.get("lo_hi", ((3.0, 5.5)))
            gate = (0.35, 0.8) if res.get("yardstick") == "p90" else (0.75, 1.75)
            pres, _, direc, _ = PL.presence_from_scales(ms, band, np.ones((size, size), bool), lo, hi, 5, gate=gate)
            fake = {"L": np.full((size, size), float(t), np.float32), "direction": direc, "opacity": pres,
                    "leftout": np.zeros((size, size), bool), "unsupported": np.zeros((size, size), bool),
                    "space": "lab"}
            rows["thinC" if key == "thin" else "clearC"].append(R.presence_picture(fake))
    labels = {"expected": "the print as expected, x4", "tone": "its tone",
              "thinB": "a thin wash, as B shows it", "thinC": "a thin wash, as C shows it",
              "clearC": "a small clear touch, as C shows it"}
    lines = [np.concatenate(rows[k], 1) for k in labels]
    body = np.concatenate([np.concatenate([l, np.full((4, l.shape[1], 3), 255, np.uint8)], 0) for l in lines], 0)
    im = Image.fromarray(body)
    W = Image.new("RGB", (im.width + 330, im.height + 30), "white")
    W.paste(im, (330, 0))
    d = ImageDraw.Draw(W)
    for i, k in enumerate(labels):
        d.text((8, i * (size + 4) + size // 2 - 10), labels[k], fill="black", font=R.font(18))
    d.text((338, im.height + 4), "paper  ->  light  ->  mid tones  ->  shadow", fill="black", font=R.font(18))
    return np.asarray(W)


def montage2x2(img8, res, words, scale=0.45):
    p = pictures(img8, res)
    tiles = [("A  the capture", p["A"]), ("C  where colour departs from the print's own tone", p["C"]),
             ("D  the print as expected unpainted, colour x4", p["D"]), ("B  departures from it, x4", p["B"])]
    ims = []
    for title, a in tiles:
        im = Image.fromarray(a)
        im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
        ims.append(R.label(np.asarray(im), title, size=20))
    h, w = ims[0].shape[:2]
    canvas = Image.new("RGB", (2 * w, 2 * h + 70), "white")
    for i, im in enumerate(ims):
        canvas.paste(Image.fromarray(im), ((i % 2) * w, (i // 2) * h))
    dr = ImageDraw.Draw(canvas)
    f = R.font(15)
    dr.text((8, 2 * h + 6), words, fill="black", font=f)
    dr.text((8, 2 * h + 30), BLANK[:118], fill="black", font=f)
    dr.text((8, 2 * h + 48), BLANK[118:], fill="black", font=f)
    return np.asarray(canvas), p
