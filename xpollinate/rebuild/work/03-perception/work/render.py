"""Pictures for the proposed design: Original | As if unpainted | Boosted (around neutral) | Presence, the blink pair,
the 'cannot judge' hatch, and the detectability key.

Display colour is handled in Oklab / Oklch (Ottosson 2020), so a departure keeps its hue when its chroma is raised
and is gamut-mapped by lowering chroma at constant lightness and hue.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter

import colour as C
import pipelines as PL

FONT = None


def font(size=22):
    global FONT
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()


def ok_to_srgb8(ok):
    lin = C.oklab_to_lin(ok)
    return np.clip(np.round(C.srgb_encode(np.clip(lin, 0, 1)) * 255), 0, 255).astype(np.uint8)


def oklch(L, Cc, h):
    return np.stack([L, Cc * np.cos(h), Cc * np.sin(h)], -1).astype(np.float32)


def departure_hue(res):
    """Oklab hue angle of each pixel's departure from the reference: the colour the departure, taken as a filter,
    would give a neutral grey."""
    d = res["direction"]
    if res.get("space", "logc") == "logc":
        lin = np.stack([np.exp(d[..., 0] / 100.0), np.ones(d.shape[:2], np.float32), np.exp(d[..., 1] / 100.0)], -1)
        lin = lin / (lin @ np.array([0.2126, 0.7152, 0.0722], np.float32))[..., None] * 0.25
        ok = C.lin_to_oklab(lin.astype(np.float32))
    else:
        lab = np.stack([np.full(d.shape[:2], 60.0, np.float32), d[..., 0] * 4, d[..., 1] * 4], -1)
        ok = C.lin_to_oklab(np.clip(C.lab_to_lin(lab), 1e-6, None))
    return np.arctan2(ok[..., 2], ok[..., 1]).astype(np.float32)


def hatch(shape, period=10, width=3):
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    return ((xx + yy) % period) < width


def lightness_ok(res):
    lin = C.lab_to_lin(np.stack([res["L"], np.zeros_like(res["L"]), np.zeros_like(res["L"])], -1))
    return C.lin_to_oklab(np.clip(lin, 0, None))[..., 0]


def presence_picture(res, fg_L=0.80, bg=(0.20, 0.32)):
    """The print as a dim grey context; departures shown bright and coloured with opacity rising with how far they
    stand out at any scale; 'cannot judge' areas hatched."""
    Lok = lightness_ok(res)
    base = oklch(bg[0] + bg[1] * Lok, np.zeros_like(Lok), np.zeros_like(Lok))
    h = departure_hue(res)
    cmax = C.max_chroma_oklab(np.full(h.shape, fg_L, np.float32), h)
    fg = oklch(np.full(h.shape, fg_L, np.float32), np.minimum(0.9 * cmax, 0.16), h)
    a = res["opacity"][..., None]
    out = base * (1 - a) + fg * a
    cj = res["leftout"] | res["unsupported"]
    hz = hatch(Lok.shape) & cj
    out[cj] = oklch(np.full(cj.sum(), 0.33, np.float32), np.zeros(cj.sum(), np.float32), np.zeros(cj.sum()))
    out[hz] = oklch(np.full(hz.sum(), 0.55, np.float32), np.zeros(hz.sum(), np.float32), np.zeros(hz.sum()))
    return ok_to_srgb8(out)


def boost_amount(res, lo=1.5, soft=3.5):
    """How strongly Boosted draws a departure: from the finest scale (paint that follows fine detail stays crisp),
    nothing below 1.5 spreads, then rising softly toward the gamut's edge."""
    m = res["ms"][0]["m"]
    return np.tanh(np.maximum(m - lo, 0) / soft).astype(np.float32) * res["valid"]


def boosted_picture(res, frac=0.9):
    """'Chroma boost around neutral': the print's own lightness, the substrate rendered neutral grey, and the
    departure from it drawn in its own hue with a chroma that rises (softly) with how far it stands out."""
    Lok = 0.15 + 0.83 * lightness_ok(res)      # deepest shadows lifted a little, so colour has room there
    h = departure_hue(res)
    amt = boost_amount(res)
    cmax = C.max_chroma_oklab(Lok, h)
    out = oklch(Lok, frac * cmax * amt, h)
    cj = res["leftout"]
    hz = hatch(Lok.shape) & cj
    out[hz] = oklch(np.full(hz.sum(), 0.55, np.float32), np.zeros(hz.sum(), np.float32), np.zeros(hz.sum()))
    return ok_to_srgb8(out)


def reference_lin(res):
    """Linear sRGB of the reference: the pixel's own lightness with the unpainted photograph's colour there."""
    ref = res["fit"]["ref"]
    L = res["L"]
    if res.get("space", "logc") == "logc":
        ratio = np.stack([np.exp(ref[..., 0] / 100.0), np.ones(L.shape, np.float32), np.exp(ref[..., 1] / 100.0)], -1)
        Y = C.lab_to_lin(np.stack([L, np.zeros_like(L), np.zeros_like(L)], -1))[..., 1]
        Y = np.clip(Y, 0, None) + PL.LOGC_EPS
        lin = ratio * (Y / (ratio @ np.array([0.2126, 0.7152, 0.0722], np.float32)))[..., None] - PL.LOGC_EPS
    else:
        lin = C.lab_to_lin(np.stack([L, ref[..., 0], ref[..., 1]], -1))
    return np.clip(lin, 0, 1).astype(np.float32)


def unpainted_picture(res):
    return np.clip(np.round(C.srgb_encode(reference_lin(res)) * 255), 0, 255).astype(np.uint8)


def blink_frames(res, frac=0.9):
    """The blink pair: the reference ('as if unpainted') and the same with the departures added back, amplified as in
    Boosted.  Unpainted areas should not change between them; paint should flash."""
    ref_ok = C.lin_to_oklab(np.clip(reference_lin(res), 1e-6, None))
    h = departure_hue(res)
    amt = boost_amount(res)
    cmax = C.max_chroma_oklab(ref_ok[..., 0], h)
    add = oklch(np.zeros_like(h), frac * cmax * amt, h)
    painted = ref_ok + add
    painted[..., 0] = ref_ok[..., 0]
    cc = np.hypot(painted[..., 1], painted[..., 2])
    hh = np.arctan2(painted[..., 2], painted[..., 1])
    cm = C.max_chroma_oklab(painted[..., 0], hh)
    scale = np.minimum(1.0, cm / np.maximum(cc, 1e-6))
    painted[..., 1:] *= scale[..., None]
    return ok_to_srgb8(ref_ok), ok_to_srgb8(painted)


def label(img, text, size=24):
    im = Image.fromarray(img)
    w, h = im.size
    out = Image.new("RGB", (w, h + size + 14), "white")
    out.paste(im, (0, 0))
    d = ImageDraw.Draw(out)
    d.text((8, h + 6), text, fill="black", font=font(size))
    return np.asarray(out)


def montage(panels, titles, scale=0.5, cols=4, footer=None):
    ims = []
    for p, t in zip(panels, titles):
        im = Image.fromarray(p)
        if scale != 1:
            im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
        ims.append(label(np.asarray(im), t))
    h, w = ims[0].shape[:2]
    rows = (len(ims) + cols - 1) // cols
    canvas = Image.new("RGB", (w * cols, h * rows + (40 if footer else 0)), "white")
    for i, im in enumerate(ims):
        canvas.paste(Image.fromarray(im), ((i % cols) * w, (i // cols) * h))
    if footer:
        ImageDraw.Draw(canvas).text((8, h * rows + 8), footer, fill="black", font=font(20))
    return np.asarray(canvas)


def save_blink(path, a, b, scale=0.5, ms=700):
    A = Image.fromarray(a)
    B = Image.fromarray(b)
    if scale != 1:
        A = A.resize((int(A.width * scale), int(A.height * scale)), Image.LANCZOS)
        B = B.resize((int(B.width * scale), int(B.height * scale)), Image.LANCZOS)
    A.save(path, save_all=True, append_images=[B], duration=ms, loop=0)


def key_strip(res, tones=(95, 85, 72, 58, 44, 30, 18), dye=(0.04, 0.40, 0.28), amount=0.03, cell=120,
              lo=3.0, hi=5.5):
    """How a standard faint wash (a transparent pink dye, double pass) would show in this capture's Presence picture
    at each tone, for a broad wash (all scales pooled) and a small touch (finest scale only).  Built from this
    capture's own reference and spreads; nothing is drawn on the photograph.  Hatched: tones the tool leaves out."""
    fit = res["fit"]
    space = res.get("space", "logc")
    knots, beta = fit["knots"], fit["beta"]
    ms = res["ms"]
    edges = fit["edges"]
    rows = []
    T = np.power(10.0, -2 * amount * np.asarray(dye, np.float32))
    Lall = res["L"][res["valid"]]
    lo_ok, hi_ok = (np.percentile(Lall, 0.5), np.percentile(Lall, 99.5)) if Lall.size else (0, 100)
    out_rows = []
    for row in ("broad", "small"):
        cells = []
        for Lt in tones:
            Lq = np.array([[float(Lt)]], np.float32)
            z = np.zeros((1, 1), np.float32)
            ref = PL.ref_at(Lq, z, z, beta, knots, 3 if len(beta) > len(knots) + 2 else (1 if len(beta) > len(knots) else 0),
                            cast_scaled=(space == "lab"))[0, 0]
            if space == "lab":
                lin = C.lab_to_lin(np.array([Lt, ref[0], ref[1]], np.float32)[None])[0]
                dyed = C.lin_to_lab((np.clip(lin, 0, 1) * T)[None])[0]
                ref2 = PL.ref_at(np.array([[dyed[0]]], np.float32), z, z, beta, knots,
                                 3 if len(beta) > len(knots) + 2 else (1 if len(beta) > len(knots) else 0), True)[0, 0]
                delta = dyed[1:] - ref2
                Lband = dyed[0]
            else:
                Y = float(C.lab_to_lin(np.array([[Lt, 0, 0]], np.float32))[0, 1])
                ratio = np.array([np.exp(ref[0] / 100), 1.0, np.exp(ref[1] / 100)], np.float32)
                lin = ratio * Y / float(ratio @ np.array([0.2126, 0.7152, 0.0722], np.float32))
                d = np.log(lin * T + PL.LOGC_EPS) - np.log(lin + PL.LOGC_EPS)
                delta = np.array([d[0] - d[1], d[2] - d[1]], np.float32) * 100
                Lband = float(C.lin_to_lab((lin * T)[None])[0, 0])
            b = int(np.clip(np.searchsorted(edges, Lband, side="right") - 1, 0, len(edges) - 2))
            s_f = ms[0]["spread"][b]
            p_f = float(PL.smoothstep(np.array(np.linalg.norm(delta) / s_f), lo, hi))
            if row == "broad":
                g = float(PL.smoothstep(np.array(np.linalg.norm(delta) / s_f), 0.75, 1.75))
                p = max([p_f] + [float(PL.smoothstep(np.array(np.linalg.norm(delta) / d_["spread"][b]), lo, hi)) * g
                                 for d_ in ms[1:]])
            else:
                p = p_f
            # the cell: presence context grey at this tone, a disc in the dye's presence colour at that opacity
            Lok = float(C.lin_to_oklab(np.clip(C.lab_to_lin(np.array([[Lt, 0, 0]], np.float32)), 0, None))[0, 0])
            bgL = 0.20 + 0.32 * Lok
            img = np.zeros((cell, cell, 3), np.float32)
            img[..., 0] = bgL
            yy, xx = np.mgrid[0:cell, 0:cell]
            disc = (xx - cell / 2) ** 2 + (yy - cell / 2) ** 2 <= (cell * (0.38 if row == "broad" else 0.12)) ** 2
            lin_d = np.array([np.exp(delta[0] / 100), 1.0, np.exp(delta[1] / 100)], np.float32) if space != "lab" else None
            if space == "lab":
                okd = C.lin_to_oklab(np.clip(C.lab_to_lin(np.array([[60, delta[0] * 4, delta[1] * 4]], np.float32)), 1e-6, None))[0]
            else:
                okd = C.lin_to_oklab((lin_d / float(lin_d @ np.array([0.2126, 0.7152, 0.0722], np.float32)) * 0.25)[None])[0]
            h = float(np.arctan2(okd[2], okd[1]))
            cm = float(C.max_chroma_oklab(0.80, h))
            fg = np.array([0.80, min(0.9 * cm, 0.16) * np.cos(h), min(0.9 * cm, 0.16) * np.sin(h)], np.float32)
            img[disc] = img[disc] * (1 - p) + fg * p
            if not (lo_ok <= Lt <= hi_ok):
                hz = hatch((cell, cell))
                img[..., 0] = 0.33
                img[..., 1:] = 0
                img[hz] = [0.55, 0, 0]
            cells.append(ok_to_srgb8(img))
        out_rows.append(np.concatenate(cells, 1))
    strip = np.concatenate(out_rows, 0)
    im = Image.fromarray(strip)
    W = Image.new("RGB", (im.width + 330, im.height + 34), "white")
    W.paste(im, (330, 0))
    d = ImageDraw.Draw(W)
    f = font(20)
    d.text((8, cell * 0.4), "a faint wash, broad", fill="black", font=f)
    d.text((8, cell * 1.4), "a faint wash, a small touch", fill="black", font=f)
    d.text((338, strip.shape[0] + 6), "paper  ->  light  ->  mid tones  ->  shadow", fill="black", font=f)
    return np.asarray(W)


TONES = {"shadows": (0, 30), "dark mid-tones": (30, 55), "light mid-tones": (55, 75), "light tones": (75, 100)}


def footer_words(res, picked=False):
    """The footer, in words: what the reference came from, what was allowed for, what is hatched, and where the
    reference rests on little of the picture.  No numbers."""
    f = res["fit"]
    words = ["Visualisation only - not a measurement.",
             "Reference: from your boxes and the picture." if picked else "Reference: automatic, from the picture."]
    sp = f["beta"][len(f["knots"]):]
    if sp.size and float(np.abs(sp).max()) > 5:
        words.append("A colour cast across the frame was allowed for.")
    if (res["leftout"] | res["unsupported"]).mean() > 0.05:
        words.append("Hatched: too bright or too dark to judge.")
    cnt = f["count"]
    share = cnt / max(cnt.sum(), 1)
    weak = []
    for n, (a, b) in TONES.items():
        sel = (f["edges"][:-1] >= a) & (f["edges"][:-1] < b) & (share > 0.002)
        if sel.any() and share[sel].sum() > 0.10:
            if np.average(1 - f["support"][sel], weights=share[sel]) > 0.40:
                weak.append(n)
    if weak:
        words.append(f"Much of the {' and '.join(weak)} departs from the reference: if 'As if unpainted' shows colour "
                     "there, box an area you know is unpainted.")
    return " ".join(words)


def four_panel(img, res, picked=False, scale=0.45):
    return montage([img, unpainted_picture(res), boosted_picture(res), presence_picture(res)],
                   ["Original", "As if unpainted", "Boosted (around neutral)", "Presence"], scale=scale, cols=4,
                   footer=footer_words(res, picked))


def reference_strip(res, k=3.0, width=900, height=70):
    """The unpainted print's colour as the tool takes it, from deep shadow to paper, exaggerated k times around
    neutral (at the frame's centre).  A toned print changes smoothly; a kink of another hue in one stretch of tone
    means paint has been taken into the reference there."""
    f = res["fit"]
    knots, beta = f["knots"], f["beta"]
    Lv = res["L"][res["valid"]]
    lo, hi = (np.percentile(Lv, 0.5), np.percentile(Lv, 99.5)) if Lv.size else (5, 95)
    Ls = np.linspace(4, 98, width).astype(np.float32)
    z = np.zeros_like(Ls)
    sp = 3 if len(beta) > len(knots) + 2 else (1 if len(beta) > len(knots) else 0)
    ab = PL.ref_at(Ls, z, z, beta, knots, sp, cast_scaled=res.get("space") == "lab")
    Ldisp = np.full_like(Ls, 62.0)                     # one lightness, so only the colour changes along the strip
    lab = np.stack([Ldisp, k * ab[:, 0], k * ab[:, 1]], -1)
    row = C.lab_to_srgb8(lab[None])[0]
    img = np.repeat(row[None], height, 0)
    outside = (Ls < lo) | (Ls > hi)
    hz = hatch((height, width))
    img[:, outside] = 200
    img[hz & outside[None, :]] = 150
    im = Image.fromarray(img)
    W = Image.new("RGB", (width + 330, height + 30), "white")
    W.paste(im, (330, 0))
    d = ImageDraw.Draw(W)
    d.text((8, height * 0.15), "the unpainted print's colour,", fill="black", font=font(18))
    d.text((8, height * 0.5), "as the tool takes it (exaggerated)", fill="black", font=font(18))
    d.text((338, height + 4), "shadow  ->  mid tones  ->  light  ->  paper", fill="black", font=font(18))
    return np.asarray(W)
