"""Synthetic 'unruly' captures of a hand-painted monochrome print, with ground truth.

A silver image (density from the skimage astronaut portrait) on paper, optionally toned with a tone that
changes with density, with paint (transparent washes by Beer-Lambert with a double pass; opaque touches by
mixing), photographed under uneven, mixed-colour light with glare, lateral chromatic aberration, noise, a
phone-like tone curve, saturation boost, sharpening and 4:2:0 JPEG.

Everything here is a stand-in for real captures, which this environment does not have.
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field

import cv2
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, map_coordinates
from skimage import color, data

IMG = 1024          # image area (px)
BORDER = 56         # paper border round the image (px)
MOUNT = 64          # mount board round the print (px)
TABLE = 40          # table round the mount (px)


def srgb_decode(v):
    v = np.asarray(v, np.float64)
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def srgb_encode(x):
    x = np.clip(np.asarray(x, np.float64), 0, 1)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * x ** (1 / 2.4) - 0.055)


def smoothstep(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------------------------------------------------------
# masks in the 512 px coordinates of the astronaut image, scaled to IMG
# ---------------------------------------------------------------------------------------------------------------

def _ellipse(shape, cx, cy, ax, ay, s):
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    return ((xx - cx * s) / (ax * s)) ** 2 + ((yy - cy * s) / (ay * s)) ** 2 <= 1.0


def _poly(shape, pts, s):
    m = np.zeros(shape, np.uint8)
    cv2.fillPoly(m, [np.round(np.array(pts, float) * s).astype(np.int32)], 1)
    return m.astype(bool)


def region_masks(grey512: np.ndarray) -> dict:
    """Regions of the portrait (booleans at IMG x IMG)."""
    s = IMG / 512.0
    shape = (IMG, IMG)
    g = cv2.resize(grey512, shape, interpolation=cv2.INTER_CUBIC).astype(float) / 255
    face = _ellipse(shape, 229, 112, 46, 62, s) & (g > 0.35)
    hair = _ellipse(shape, 228, 62, 72, 52, s) & ~_ellipse(shape, 229, 118, 46, 60, s) & (g < 0.45)
    lips = _ellipse(shape, 224, 143, 21, 8, s)
    cheek_l = _ellipse(shape, 197, 125, 13, 10, s)
    cheek_r = _ellipse(shape, 258, 125, 13, 10, s)
    head = _ellipse(shape, 229, 100, 80, 95, s)
    flag = _poly(shape, [[0, 0], [95, 0], [95, 230], [70, 300], [0, 300]], s)
    shuttle = _poly(shape, [[360, 10], [455, 10], [455, 250], [360, 250]], s)
    suit = _poly(shape, [[40, 250], [130, 225], [330, 225], [360, 260], [370, 512], [30, 512]], s) & (g > 0.25)
    patch = _ellipse(shape, 172, 384, 38, 38, s)
    # the backdrop: light grey behind the sitter, the flag and the shuttle left out
    backdrop = (g > 0.55) & (g < 0.92)
    yy, xx = np.mgrid[0:IMG, 0:IMG]
    backdrop &= (yy < 290 * s) & ~head & ~flag & ~shuttle & ~suit
    backdrop &= ~_poly(shape, [[110, 150], [320, 150], [330, 300], [100, 300]], s)
    backdrop = cv2.morphologyEx(backdrop.astype(np.uint8), cv2.MORPH_OPEN, np.ones((9, 9), np.uint8)).astype(bool)
    return dict(face=face, hair=hair, lips=lips, cheeks=cheek_l | cheek_r, flag=flag, shuttle=shuttle,
                suit=suit, patch=patch, backdrop=backdrop, grey=g)


# ---------------------------------------------------------------------------------------------------------------
# the print
# ---------------------------------------------------------------------------------------------------------------

@dataclass
class Paint:
    name: str
    mask: str               # a region name, or a combination 'a|b'
    kind: str               # 'wash' (transparent, Beer-Lambert, double pass) or 'opaque'
    colour: tuple           # wash: single-pass OD per unit amount (R, G, B); opaque: reflectance
    amount: float           # wash: amount; opaque: coverage alpha
    feather: float = 3.0    # px (Gaussian sd of the edge)
    group: str = "touch"    # for scoring: touch, wash, large, lowchroma


@dataclass
class PrintSpec:
    paper: tuple = (0.86, 0.83, 0.72)        # yellowed paper reflectance
    tone: str = "split"                      # 'neutral', 'warm' (uniform) or 'split' (tone changes with density)
    paints: list = field(default_factory=list)


def silver_od(D: np.ndarray, tone: str) -> np.ndarray:
    """OD per channel of the silver image at density D (H, W) -> (H, W, 3)."""
    if tone == "neutral":
        s = np.ones(D.shape + (3,))
        return D[..., None] * s
    if tone == "warm":
        return D[..., None] * np.array([0.92, 1.0, 1.10])
    # split: warm-brown mid-tones, purple-brown shadows (selenium tones the dense areas first), and a yellow stain
    # in the highlights (highlight yellowing)
    mid = np.array([0.90, 1.0, 1.13])
    shadow = np.array([1.02, 1.07, 0.96])
    w = smoothstep(D, 0.7, 1.35)[..., None]
    od = D[..., None] * ((1 - w) * mid + w * shadow)
    stain = 0.035 * (1 - smoothstep(D, 0.0, 0.45))[..., None] * np.array([0.15, 0.35, 1.0])
    return od + stain


def make_print(spec: PrintSpec, regions: dict):
    """Reflectance of the print (image area plus paper border), the paint truth and the density."""
    g = regions["grey"]
    ylin = srgb_decode(g)
    D = -np.log10(np.clip(ylin, 10 ** -1.85, 1.0)) + 0.02
    od = silver_od(D, spec.tone)
    paper = np.asarray(spec.paper, float)
    rho = paper * 10.0 ** (-od)
    truth = {}
    strength = np.zeros(D.shape)
    for p in spec.paints:
        m = np.zeros(D.shape, bool)
        for part in p.mask.split("|"):
            m |= regions[part]
        soft = gaussian_filter(m.astype(float), p.feather)
        if p.kind == "wash":
            rho = rho * 10.0 ** (-2 * p.amount * soft[..., None] * np.asarray(p.colour, float))
        else:
            a = p.amount * soft[..., None]
            rho = (1 - a) * rho + a * np.asarray(p.colour, float)
        truth[p.name] = (soft > 0.5, p.group)
        strength = np.maximum(strength, soft)
    # paper border
    H = IMG + 2 * BORDER
    out = np.empty((H, H, 3))
    out[:] = paper
    out[BORDER:BORDER + IMG, BORDER:BORDER + IMG] = rho
    pad = lambda a: np.pad(a, BORDER, constant_values=0)
    truth = {k: (pad(v), grp) for k, (v, grp) in truth.items()}
    return out, truth, pad(strength), np.pad(D, BORDER, constant_values=0.0)


# ---------------------------------------------------------------------------------------------------------------
# the capture
# ---------------------------------------------------------------------------------------------------------------

@dataclass
class CaptureSpec:
    light: str = "mixed"          # 'uniform' or 'mixed' (warm left, cool right, falloff, vignetting)
    glare: float = 0.30           # peak of a specular patch (fraction of paper white)
    veil: float = 0.012           # even flare
    ca: float = 0.0012            # lateral chromatic aberration (relative magnification R +ca, B -ca)
    tone_curve: str = "phone"     # 'srgb' or 'phone' (S-curve and saturation boost)
    sat: float = 1.15
    sharpen: float = 0.6
    jpeg_q: int = 80
    noise: float = 1.0
    wb_error: tuple = (1.0, 1.0, 1.0)  # an extra global cast (camera white balance off)
    seed: int = 0


def capture(rho_print: np.ndarray, spec: CaptureSpec):
    rng = np.random.default_rng(spec.seed)
    P = rho_print.shape[0]
    F = P + 2 * MOUNT + 2 * TABLE
    scene = np.empty((F, F, 3))
    scene[:] = (0.10, 0.065, 0.04)                       # dark wooden table
    m0 = TABLE
    scene[m0:F - m0, m0:F - m0] = (0.42, 0.42, 0.40)     # grey mount board
    p0 = TABLE + MOUNT
    scene[p0:p0 + P, p0:p0 + P] = rho_print
    yy, xx = np.mgrid[0:F, 0:F] / (F - 1.0)
    if spec.light == "uniform":
        E = np.ones((F, F, 3))
    else:
        r2 = (xx - 0.5) ** 2 + (yy - 0.5) ** 2
        intensity = (0.62 + 0.38 * xx) * (1 - 0.55 * r2) * (1 + 0.08 * yy)
        left = np.array([1.07, 1.0, 0.86])
        right = np.array([0.95, 1.0, 1.09])
        w = smoothstep(xx, 0.0, 1.0)[..., None]
        E = intensity[..., None] * ((1 - w) * left + w * right)
    E = E * np.asarray(spec.wb_error)
    rad = scene * E
    if spec.glare > 0:
        gx, gy = 0.66, 0.30
        G = spec.glare * np.exp(-(((xx - gx) / 0.055) ** 2 + ((yy - gy) / 0.04) ** 2) / 2)
        rad = rad + (G + spec.veil)[..., None] * E[int(gy * F), int(gx * F)] * 0.9
    else:
        G = np.zeros((F, F))
    # lateral chromatic aberration: R magnified, B shrunk about the centre
    if spec.ca:
        c = (F - 1) / 2.0
        yy_p, xx_p = np.mgrid[0:F, 0:F].astype(float)
        for ch, k in ((0, 1 + spec.ca), (2, 1 - spec.ca)):
            src_y = c + (yy_p - c) / k
            src_x = c + (xx_p - c) / k
            rad[..., ch] = map_coordinates(rad[..., ch], [src_y, src_x], order=1, mode="nearest")
    expo = 0.82 / np.percentile(rad[p0:p0 + P, p0:p0 + P].mean(axis=2), 99.0)
    sig = rad * expo
    if spec.noise:
        sig = sig + rng.normal(size=sig.shape) * np.sqrt(0.0025 ** 2 + 0.00035 * np.clip(sig, 0, None)) * spec.noise
    sig = np.clip(sig, 0, 1)
    v = srgb_encode(sig)
    if spec.tone_curve == "phone":
        v = v + 0.22 * v * (1 - v) * (2 * v - 1)         # a mild S-curve, equal in every channel
        ycc = cv2.cvtColor(v.astype(np.float32), cv2.COLOR_RGB2YCrCb)
        ycc[..., 1:] = 0.5 + (ycc[..., 1:] - 0.5) * spec.sat
        v = cv2.cvtColor(ycc, cv2.COLOR_YCrCb2RGB).astype(np.float64)
    if spec.sharpen:
        blur = cv2.GaussianBlur(v.astype(np.float32), (0, 0), 1.2).astype(np.float64)
        v = v + spec.sharpen * (v - blur)
    u8 = np.clip(np.round(np.clip(v, 0, 1) * 255), 0, 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(u8).save(buf, "JPEG", quality=spec.jpeg_q, subsampling=2)
    out = np.asarray(Image.open(io.BytesIO(buf.getvalue())).convert("RGB"))
    geo = dict(frame=F, print0=p0, print_size=P, image0=p0 + BORDER, image_size=IMG,
               glare=G, illum=E)
    return out, geo


# ---------------------------------------------------------------------------------------------------------------
# scenarios
# ---------------------------------------------------------------------------------------------------------------

FLESH = (0.02, 0.10, 0.20)
BLUE = (0.22, 0.10, 0.015)
ORANGE = (0.01, 0.14, 0.34)
BROWN = (0.05, 0.11, 0.17)
RED_W = (0.015, 0.26, 0.20)
LIPRED = (0.50, 0.10, 0.11)
GOLD = (0.62, 0.50, 0.16)

SCENARIOS = {
    # negative controls
    "N1_neutral_even": (PrintSpec(paper=(0.88, 0.88, 0.86), tone="neutral"), CaptureSpec(light="uniform", glare=0.0)),
    "N2_split_even": (PrintSpec(tone="split"), CaptureSpec(light="uniform", glare=0.0)),
    "N3_split_mixed": (PrintSpec(tone="split"), CaptureSpec(light="mixed")),
    # small touches and faint washes, a blue wash over warm highlights (lowers chroma)
    "P1_touches": (PrintSpec(tone="split", paints=[
        Paint("lips", "lips", "opaque", LIPRED, 0.8, 1.5, "touch"),
        Paint("cheeks", "cheeks", "wash", FLESH, 0.35, 4.0, "wash"),
        Paint("patch", "patch", "opaque", GOLD, 0.55, 2.0, "touch"),
        Paint("shuttle_blue", "shuttle", "wash", BLUE, 0.10, 3.0, "lowchroma"),
    ]), CaptureSpec(light="mixed")),
    # a large painted backdrop (a third of the image) plus face and lips
    "P2_backdrop": (PrintSpec(tone="split", paints=[
        Paint("backdrop", "backdrop", "wash", BLUE, 0.12, 5.0, "large"),
        Paint("face", "face", "wash", FLESH, 0.30, 4.0, "wash"),
        Paint("lips", "lips", "opaque", LIPRED, 0.8, 1.5, "touch"),
    ]), CaptureSpec(light="mixed")),
    # fully hand-coloured: little of the image is left unpainted
    "P3_full": (PrintSpec(tone="split", paints=[
        Paint("backdrop", "backdrop", "wash", BLUE, 0.12, 5.0, "large"),
        Paint("face", "face", "wash", FLESH, 0.30, 4.0, "wash"),
        Paint("hair", "hair", "wash", BROWN, 0.25, 4.0, "wash"),
        Paint("suit", "suit", "wash", ORANGE, 0.22, 4.0, "large"),
        Paint("flag", "flag", "wash", RED_W, 0.20, 3.0, "large"),
        Paint("lips", "lips", "opaque", LIPRED, 0.8, 1.5, "touch"),
        Paint("patch", "patch", "opaque", GOLD, 0.55, 2.0, "touch"),
    ]), CaptureSpec(light="mixed")),
}


def build(name: str, seed: int = 0):
    pspec, cspec = SCENARIOS[name]
    cspec = CaptureSpec(**{**cspec.__dict__, "seed": seed})
    grey = (color.rgb2gray(data.astronaut()) * 255).astype(np.uint8)
    regions = region_masks(grey)
    rho, truth, strength, D = make_print(pspec, regions)
    img, geo = capture(rho, cspec)
    F, p0 = geo["frame"], geo["print0"]
    P = geo["print_size"]

    def place(a, fill=0):
        out = np.full((F, F) + a.shape[2:], fill, a.dtype)
        out[p0:p0 + P, p0:p0 + P] = a
        return out

    truth = {k: (place(v), grp) for k, (v, grp) in truth.items()}
    paint_any = place(strength) > 0.02
    i0, n = geo["image0"], geo["image_size"]
    image_area = np.zeros((F, F), bool)
    image_area[i0:i0 + n, i0:i0 + n] = True
    print_area = np.zeros((F, F), bool)
    print_area[p0:p0 + P, p0:p0 + P] = True
    border = print_area & ~image_area
    regions_f = {k: place(np.pad(v, BORDER, constant_values=False)) for k, v in regions.items() if k != "grey"}
    return dict(img=img, truth=truth, paint_any=paint_any, image_area=image_area, print_area=print_area,
                border=border, glare=geo["glare"], illum=geo["illum"], density=place(D), regions=regions_f,
                box=(p0, p0, p0 + P, p0 + P), geo=geo)


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    for name in SCENARIOS:
        s = build(name)
        Image.fromarray(s["img"]).save(f"{out}/{name}.jpg", quality=95)
        print(name, s["img"].shape, "paint px share of image:",
              round(float((s["paint_any"] & s["image_area"]).sum() / s["image_area"].sum()), 3))
