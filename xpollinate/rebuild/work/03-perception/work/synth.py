"""Synthetic hand-tinted monochrome prints and uncontrolled captures of them, with ground truth.

Print: a gelatin-silver-like print of a greyscale portrait (skimage's astronaut), on yellowed paper with a margin;
silver tone that shifts with density (warm highlights, neutral or purple shadows); paper texture; transparent
colourants laid on by Beer-Lambert with a double pass (as in Woodii's test models); optional brown stains (colour that
is not paint).

Capture: illuminant colour and brightness fields (uniform, or mixed light across the frame), optional veiling glare,
shot and read noise, partial grey-world auto white balance, chroma noise reduction, a tone curve with an S, luminance
sharpening, 8-bit, and JPEG at quality 80 with 4:2:0 chroma subsampling (or lossless PNG for the "scan" case).
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
from skimage import data
from skimage.transform import resize

import colour as C

S = 2            # the 512 px portrait is drawn at 1024 px
#: amounts for the "thin" variant, set so each wash is about 1.3 CIELAB units on the capture (VDZ-like thin washes)
THIN = {"cheeks": 0.025, "backdrop": 0.0155, "canton": 0.068, "flesh": 0.031}
PAD = 48         # paper margin in px


def _ellipse(shape, cx, cy, rx, ry, feather=2.0):
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    m = (((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1).astype(np.float32)
    return gaussian_filter(m, feather) if feather else m


@dataclass
class Paint:
    name: str
    eps: tuple            # single-pass OD per unit amount, R G B
    amount: float
    mask: np.ndarray = field(repr=False, default=None)   # 0-1, soft edged


def portrait_density(dmax_floor=0.012):
    g = np.asarray(Image.fromarray(data.astronaut()).convert("L"), np.float32) / 255.0
    g = resize(g, (512 * S, 512 * S), order=3, anti_aliasing=False).astype(np.float32)
    lin = C.srgb_decode(np.clip(g, 0, 1))
    d = -np.log10(dmax_floor + (1 - dmax_floor) * lin)          # Dmax about 1.9
    d = np.pad(d, PAD, mode="constant", constant_values=0.0)     # paper margin: no silver
    return d.astype(np.float32)


def paints(shape, variant="normal"):
    """Paint regions in the padded 1120 px frame (coordinates given on the 512 px portrait)."""
    def P(x, y):
        return PAD + S * x, PAD + S * y

    h, w = shape
    out = []
    # faint pink on the cheeks
    m = np.zeros(shape, np.float32)
    for cx, cy in ((196, 128), (262, 128)):
        X, Y = P(cx, cy)
        m = np.maximum(m, _ellipse(shape, X, Y, 16 * S, 11 * S, 4))
    out.append(Paint("cheeks (faint pink)", (0.04, 0.40, 0.28), 0.05 if variant != "thin" else THIN["cheeks"], m))
    if variant == "thin":            # a thin flesh wash over the whole face (VDZ-like)
        X, Y = P(228, 120)
        face = _ellipse(shape, X, Y, 52 * S, 62 * S, 6)
        out.append(Paint("face (thin flesh wash)", (0.03, 0.15, 0.32), THIN["flesh"], face))
    # red lips: small, strong
    X, Y = P(222, 145)
    out.append(Paint("lips (red)", (0.02, 0.90, 0.60), 0.22, _ellipse(shape, X, Y, 20 * S, 6 * S, 1.5)))
    # faint blue wash over the backdrop (large; lowers chroma on warm paper)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    X0, Y0 = P(95, 0)
    X1, Y1 = P(360, 175)
    hx, hy = P(228, 105)
    head = (((xx - hx) / (82 * S)) ** 2 + ((yy - hy) / (110 * S)) ** 2) <= 1
    back = (xx >= X0) & (xx <= X1) & (yy >= PAD) & (yy <= Y1) & ~head
    if variant == "wide":           # the whole upper two thirds of the picture, every tone, except the head
        _, Y1w = P(0, 340)
        back = (yy >= PAD) & (yy <= Y1w) & (xx >= PAD) & (xx <= w - PAD) & ~head
    if variant == "majority":       # the whole light backdrop and the shuttle painted
        X1b, _ = P(511, 0)
        _, Y1b = P(0, 270)
        back = (xx >= X0) & (xx <= X1b) & (yy >= PAD) & (yy <= Y1b) & ~head
    out.append(Paint("backdrop (faint blue wash)", (0.40, 0.22, 0.02),
                     {"majority": 0.06, "thin": THIN["backdrop"], "wide": 0.05}.get(variant, 0.045),
                     gaussian_filter(back.astype(np.float32), 6)))
    # flag: blue canton (medium) and red on the dark stripes (over mid to dark silver)
    X0, Y0 = P(0, 0)
    X1, Y1 = P(62, 118)
    canton = ((xx >= X0) & (xx <= X1) & (yy >= Y0) & (yy <= Y1)).astype(np.float32)
    out.append(Paint("flag canton (blue)", (0.45, 0.25, 0.03), 0.10 if variant != "thin" else THIN["canton"],
                     gaussian_filter(canton, 2)))
    g = portrait_density()
    X0, _ = P(0, 0)
    X1, _ = P(92, 0)
    _, Y0 = P(0, 120)
    _, Y1 = P(0, 511)
    xlim = PAD + S * np.maximum(30.0, 92.0 - 0.47 * ((yy - PAD) / S - 120.0))   # the flag, not the suit's arm
    stripes = (xx >= X0) & (xx <= np.minimum(X1, xlim)) & (yy >= Y0) & (yy <= Y1) & (g > 0.45)
    out.append(Paint("flag stripes (red, over dark silver)", (0.03, 0.75, 0.55), 0.10,
                     gaussian_filter(stripes.astype(np.float32), 1.5)))
    # green over the mission patch (mid tones)
    X, Y = P(168, 385)
    out.append(Paint("mission patch (green)", (0.50, 0.06, 0.42), 0.07, _ellipse(shape, X, Y, 33 * S, 33 * S, 2)))
    # small gold touches on badges and fittings: dots of 3 to 6 px radius
    m = np.zeros(shape, np.float32)
    for (cx, cy, r) in ((300, 350, 3.0), (312, 352, 2.0), (245, 300, 2.5), (150, 378, 2.0), (186, 378, 1.5),
                        (168, 352, 2.0), (420, 230, 2.5)):
        X, Y = P(cx, cy)
        m = np.maximum(m, _ellipse(shape, X, Y, r * S, r * S, 0.8))
    out.append(Paint("small gold touches", (0.02, 0.12, 0.85), 0.25, m))
    return out


def stains(shape):
    """Brown foxing and a tide line: colour in the paper that is not paint."""
    h, w = shape
    m = np.zeros(shape, np.float32)
    rng = np.random.default_rng(7)
    for cx, cy, r in ((150, 980, 10), (175, 1010, 6), (900, 1040, 14), (1060, 300, 8)):
        blob = _ellipse(shape, cx, cy, r, r * 0.8, 3)
        m = np.maximum(m, blob * (0.7 + 0.3 * rng.random()))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    tide = np.exp(-((np.hypot(xx - 1120, yy - 1120) - 260) / 5.0) ** 2) * 0.8
    m = np.maximum(m, tide)
    return m


def make_print(variant="normal", tone="warm", with_paint=True, with_stains=True, seed=3):
    d = portrait_density()
    shape = d.shape
    rng = np.random.default_rng(seed)
    paper = np.array([0.84, 0.80, 0.68], np.float32)
    if tone == "warm":
        s_light, s_dark = np.array([0.90, 1.0, 1.18]), np.array([0.98, 1.0, 1.04])
    elif tone == "selenium":      # warm highlights, purple shadows
        s_light, s_dark = np.array([0.88, 1.0, 1.20]), np.array([0.96, 1.07, 0.94])
    else:
        s_light = s_dark = np.array([1.0, 1.0, 1.0])
    t = np.clip(d / 1.9, 0, 1)[..., None]
    od = d[..., None] * (s_light * (1 - t) + s_dark * t)
    texture_l = gaussian_filter(rng.normal(size=shape), 1.2) * 0.035
    texture_c = gaussian_filter(rng.normal(size=shape + (3,)), (2.0, 2.0, 0)) * 0.006
    od = od + texture_l[..., None] + texture_c
    truth = {}
    ps = paints(shape, variant) if with_paint else []
    for p in ps:
        od = od + 2 * p.amount * p.mask[..., None] * np.asarray(p.eps, np.float32)
        truth[p.name] = p.mask
    st = stains(shape) if with_stains else np.zeros(shape, np.float32)
    od = od + 0.12 * st[..., None] * np.array([0.10, 0.30, 0.75], np.float32)
    refl = paper * np.power(10.0, -od)
    margin = np.zeros(shape, bool)
    margin[:PAD - 4, :] = margin[-PAD + 4:, :] = True
    margin[:, :PAD - 4] = margin[:, -PAD + 4:] = True
    return refl.astype(np.float32), {"paint": truth, "paints": ps, "stain": st, "margin": margin, "density": d}


@dataclass
class Capture:
    name: str
    light: str = "uniform"          # uniform | mixed | neutral
    falloff: float = 0.05
    glare: float = 0.0
    awb: float = 0.7
    noise: float = 1.0
    chroma_nr: float = 1.5
    jpeg: int = 80                  # 0: PNG (lossless)
    scurve: float = 1.15
    sharpen: float = 0.5


SCENARIOS = {
    "scan": Capture("scan", light="neutral", falloff=0.0, glare=0.0, awb=0.0, noise=0.15, chroma_nr=0.0, jpeg=0,
                    scurve=1.0, sharpen=0.0),
    "phone": Capture("phone"),
    "phone_mixed": Capture("phone_mixed", light="mixed", falloff=0.25),
    "phone_glare": Capture("phone_glare", glare=0.20),
}


def capture(refl, cap: Capture, seed=11, gains=None, scale=None):
    h, w, _ = refl.shape
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u, v = xx / (w - 1), yy / (h - 1)
    r2 = (u - 0.5) ** 2 + (v - 0.5) ** 2
    bright = (1 - cap.falloff * u if cap.light == "mixed" else 1.0) - (0.4 if cap.falloff else 0.0) * r2
    if cap.light == "neutral":
        tint = np.ones((h, w, 3), np.float32)
    elif cap.light == "uniform":
        tint = np.broadcast_to(np.array([1.10, 1.0, 0.80], np.float32), (h, w, 3))
    else:
        left, right = np.array([1.18, 1.0, 0.70]), np.array([0.95, 1.0, 1.10])
        tint = (left * (1 - u[..., None]) + right * u[..., None]).astype(np.float32)
    E = bright[..., None] * tint
    lin = refl * E
    glare_map = np.zeros((h, w), np.float32)
    if cap.glare:
        glare_map = cap.glare * np.exp(-(((xx - 0.72 * w) / (0.16 * w)) ** 2 + ((yy - 0.25 * h) / (0.13 * h)) ** 2))
        lin = lin + glare_map[..., None] * E
    expo = (0.93 / np.percentile(lin[..., 1], 99.7)) if scale is None else scale
    lin = lin * expo                                               # exposure: paper about 0.93 of full scale
    sd = np.sqrt((1.5e-3 * cap.noise) ** 2 + 1.5e-4 * cap.noise * np.clip(lin, 0, None))
    lin = lin + rng.normal(size=lin.shape).astype(np.float32) * sd
    g = np.ones(3, np.float32)
    if cap.awb:
        if gains is None:
            m = lin.reshape(-1, 3).mean(0)
            g = (m[1] / m) ** cap.awb
        else:
            g = gains
        lin = lin * g
    lin = np.clip(lin, 0, 1)
    enc = C.srgb_encode(lin)
    if cap.scurve != 1.0:
        a = cap.scurve
        enc = enc ** a / (enc ** a + (1 - enc) ** a)
    # chroma noise reduction and luminance sharpening in YCbCr (as camera pipelines do)
    Y = 0.299 * enc[..., 0] + 0.587 * enc[..., 1] + 0.114 * enc[..., 2]
    Cb, Cr = enc[..., 2] - Y, enc[..., 0] - Y
    if cap.chroma_nr:
        Cb, Cr = gaussian_filter(Cb, cap.chroma_nr), gaussian_filter(Cr, cap.chroma_nr)
    if cap.sharpen:
        Y = Y + cap.sharpen * (Y - gaussian_filter(Y, 1.0))
    R = Cr + Y
    B = Cb + Y
    G = (Y - 0.299 * R - 0.114 * B) / 0.587
    enc = np.clip(np.stack([R, G, B], -1), 0, 1)
    img8 = np.round(enc * 255).astype(np.uint8)
    if cap.jpeg:
        buf = io.BytesIO()
        Image.fromarray(img8).save(buf, "JPEG", quality=cap.jpeg, subsampling=2)
        img8 = np.asarray(Image.open(io.BytesIO(buf.getvalue())).convert("RGB"))
    return img8, {"glare": glare_map, "illum_tint": tint, "gains": g, "scale": expo}


def scenario(name, seed=11):
    """Returns (8-bit sRGB capture, truth). Names: scan, phone, phone_mixed, phone_glare, majority, control, toned."""
    if name == "majority":
        refl, truth = make_print(variant="majority")
        img, extra = capture(refl, SCENARIOS["phone"], seed)
    elif name == "control":
        refl, truth = make_print(with_paint=False)
        img, extra = capture(refl, SCENARIOS["phone_mixed"], seed)
    elif name == "toned":
        refl, truth = make_print(tone="selenium")
        img, extra = capture(refl, SCENARIOS["phone"], seed)
    elif name == "wide":
        refl, truth = make_print(variant="wide")
        img, extra = capture(refl, SCENARIOS["phone"], seed)
    elif name in ("thin", "thin_mixed"):
        refl, truth = make_print(variant="thin")
        img, extra = capture(refl, SCENARIOS["phone" if name == "thin" else "phone_mixed"], seed)
    else:
        refl, truth = make_print()
        img, extra = capture(refl, SCENARIOS[name], seed)
    truth.update(extra)
    return img, truth


if __name__ == "__main__":
    import os
    os.makedirs("captures", exist_ok=True)
    for n in ("scan", "phone", "phone_mixed", "phone_glare", "majority", "control", "toned"):
        img, t = scenario(n)
        Image.fromarray(img).save(f"captures/{n}.png")
        print(n, img.shape, img.reshape(-1, 3).mean(0).round(1))


def paired(name, seed=11):
    """The capture of a scenario and the same capture of the same print without paint (same light, noise seed and
    camera), so the reference a pipeline infers can be compared with what the unpainted print really gives."""
    img, t = scenario(name, seed)
    if name == "majority":
        refl, _ = make_print(variant="majority", with_paint=False)
        cap = SCENARIOS["phone"]
    elif name == "control":
        return img, t, img
    elif name == "toned":
        refl, _ = make_print(tone="selenium", with_paint=False)
        cap = SCENARIOS["phone"]
    elif name in ("thin", "thin_mixed"):
        refl, _ = make_print(variant="thin", with_paint=False)
        cap = SCENARIOS["phone" if name == "thin" else "phone_mixed"]
    else:
        refl, _ = make_print(with_paint=False)
        cap = SCENARIOS[name]
    clean, _ = capture(refl, cap, seed, gains=t["gains"], scale=t["scale"])   # same white balance and exposure
    return img, t, clean
