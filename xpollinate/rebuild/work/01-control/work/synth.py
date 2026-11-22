"""Synthetic hand-painted prints and unruly captures of them, for testing visualiser methods.

Deliberately NOT built from any visualiser's own model: the print has image tone that shifts with density,
yellowed and stained paper and paper texture; paint is transparent (Beer-Lambert, double pass) or opaque (cover);
the capture has auto white balance, colour shading / mixed light, a phone-like tone curve and saturation, chroma
noise reduction, sharpening, lateral colour, glare and JPEG 4:2:0.  Ground truth: paint amount per paint, and masks.
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field

import cv2
import numpy as np
import skimage.data as skd
from PIL import Image
from scipy.ndimage import gaussian_filter

RNG = np.random.default_rng


def srgb_decode(v):
    v = np.asarray(v, np.float32)
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4).astype(np.float32)


def srgb_encode(x):
    x = np.clip(np.asarray(x, np.float32), 0, 1)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055).astype(np.float32)


# ---------------------------------------------------------------- paints: single-pass OD per unit amount (R, G, B)
PAINTS = {
    "flesh": np.array([0.04, 0.30, 0.42]),
    "rouge": np.array([0.02, 0.60, 0.45]),
    "lips": np.array([0.02, 0.85, 0.60]),
    "blue": np.array([0.50, 0.22, 0.02]),
    "green": np.array([0.45, 0.06, 0.40]),
    "gold": np.array([0.02, 0.12, 0.75]),
    "brown": np.array([0.18, 0.33, 0.55]),
    "violet": np.array([0.25, 0.55, 0.05]),
}


def smooth_noise(shape, sigma, seed):
    n = gaussian_filter(RNG(seed).normal(size=shape), sigma)
    return (n / (n.std() + 1e-9)).astype(np.float32)


def soft(mask, sigma):
    return np.clip(gaussian_filter(mask.astype(np.float32), sigma), 0, 1)


@dataclass
class Paint:
    name: str
    mask: np.ndarray          # (H, W) float 0-1, the painted region (soft)
    amount: float             # OD amount (transparent) or cover (opaque)
    opaque_rgb: tuple | None = None   # reflectance of an opaque paint; None = transparent
    texture: float = 0.35     # brush unevenness


@dataclass
class PrintSpec:
    scene: str = "astronaut"
    size: int = 1400                      # long edge of the print, px
    paper: tuple = (0.86, 0.84, 0.76)     # paper base reflectance (yellowed a little)
    tone_hi: tuple = (0.90, 1.00, 1.15)   # silver OD per unit density at low density (warm: more blue absorbed)
    tone_lo: tuple = (0.97, 1.00, 1.05)   # ... at high density
    tone_scale: float = 0.6               # density over which tone moves from hi to lo
    dmax: float = 1.8
    yellowing: float = 0.10               # extra blue loss toward the edges
    foxing: int = 6                       # brown spots
    texture: float = 0.012                # paper/emulsion texture (luminance)
    seed: int = 1


@dataclass
class CaptureSpec:
    awb: str = "grayworld"                # grayworld | none | fixed
    fixed_gains: tuple = (1.0, 1.0, 1.0)
    cast: tuple = (1.0, 1.0, 1.0)         # illuminant gains before AWB (uniform)
    gradient: tuple | None = None         # (left gains, right gains) mixed light across x; or None
    gradient_axis: str = "x"
    vignette: float = 0.25
    light_tilt: float = 0.15              # intensity gradient across the frame
    saturation: float = 1.25              # phone colour boost
    contrast: float = 0.25                # S-curve strength
    noise: float = 0.006                  # sd of linear noise at mid grey
    chroma_nr: float = 1.2                # chroma blur (px) as a phone's noise reduction does
    chroma_mottle: float = 0.004          # low-frequency chroma noise amplitude (linear)
    sharpen: float = 0.6
    lateral_colour: float = 0.0012        # R and B scaled by 1 -/+ this about the centre
    glare: float = 0.0                    # veiling glare amplitude (linear, of white)
    glare_pos: tuple = (0.7, 0.3)
    speculars: int = 0
    background: str | None = None         # None | "wood" | "grey" | "cloth"
    border: float = 0.12                  # background border, share of the print's long edge
    jpeg_q: int | None = 85               # None: PNG (lossless)
    exposure: float = 0.92                # paper white maps to this before the tone curve
    seed: int = 2


def base_scene(name: str):
    if name == "astronaut":
        rgb = skd.astronaut()
    elif name == "camera":
        rgb = np.stack([skd.camera()] * 3, -1)
    elif name == "coffee":
        rgb = skd.coffee()
    elif name == "rocket":
        rgb = skd.rocket()
    elif name == "chelsea":
        rgb = skd.chelsea()
    else:
        raise ValueError(name)
    return rgb


def _resize(a, w, h, interp=cv2.INTER_CUBIC):
    return cv2.resize(a, (w, h), interpolation=interp)


def scene_regions(name: str, w: int, h: int):
    """Content-aligned regions for paint, from the colour original (masks at the print's size)."""
    rgb = base_scene(name)
    src = rgb.astype(np.float32) / 255
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32)
    H, S, V = hsv[..., 0] * 2, hsv[..., 1] / 255, hsv[..., 2] / 255
    reg = {}
    if name == "astronaut":
        yy, xx = np.mgrid[0:512, 0:512]
        face_box = (yy > 40) & (yy < 175) & (xx > 160) & (xx < 300)
        skin = face_box & (H > 5) & (H < 40) & (S > 0.25) & (S < 0.75) & (V > 0.45)
        skin = cv2.morphologyEx(skin.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8)) > 0
        hair = (yy < 110) & (xx > 140) & (xx < 330) & (H > 15) & (H < 45) & (S > 0.3) & ~skin & (V < 0.85)
        suit = (yy > 150) & (H < 30) & (S > 0.55) & (V > 0.35) & ~face_box
        flag_red = (xx < 110) & (H < 15) | (xx < 110) & (H > 340)
        flag_red &= (S > 0.45)
        flag_blue = (xx < 120) & (H > 200) & (H < 260) & (S > 0.35)
        cheeks = np.zeros((512, 512), bool)
        cv2.ellipse(cheeks.view(np.uint8), (205, 128), (14, 10), 0, 0, 360, 1, -1)
        cv2.ellipse(cheeks.view(np.uint8), (262, 128), (14, 10), 0, 0, 360, 1, -1)
        lips = np.zeros((512, 512), np.uint8)
        cv2.ellipse(lips, (233, 150), (17, 6), 0, 0, 360, 1, -1)
        patch = (yy > 195) & (yy < 255) & (xx > 75) & (xx < 125)
        badge = (yy > 195) & (yy < 222) & (xx > 160) & (xx < 195)
        bg = (V > 0.55) & (S < 0.15) & (xx > 290) & (yy < 300) & (yy > 0)
        reg = {"skin": skin, "hair": hair, "suit": suit, "flag_red": flag_red, "flag_blue": flag_blue,
               "cheeks": cheeks, "lips": lips.astype(bool), "patch": patch, "badge": badge, "bg": bg}
    elif name == "camera":
        g = skd.camera().astype(np.float32) / 255
        yy, xx = np.mgrid[0:512, 0:512]
        sky = (yy < 230) & (g > 0.62) & ~((xx > 120) & (xx < 300) & (yy > 60))
        sky = cv2.morphologyEx(sky.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)) > 0
        grass = (yy > 260) & (xx > 300) & (g > 0.3) & (g < 0.75)
        grass |= (yy > 300) & (xx > 180) & (xx < 300) & (g > 0.35) & (g < 0.75)
        face = (yy > 90) & (yy < 175) & (xx > 160) & (xx < 225) & (g > 0.35) & (g < 0.8)
        reg = {"sky": sky, "grass": grass, "face": face}
    out = {}
    for k, m in reg.items():
        out[k] = _resize(m.astype(np.float32), w, h, cv2.INTER_LINEAR) > 0.5
    return out


def make_print(spec: PrintSpec, paints: list[Paint]):
    """Linear reflectance (H, W, 3) of a monochrome print with paint, and the ground truth."""
    rgb = base_scene(spec.scene)
    h0, w0 = rgb.shape[:2]
    s = spec.size / max(h0, w0)
    w, h = int(round(w0 * s)), int(round(h0 * s))
    grey = srgb_decode(rgb.astype(np.float32) / 255) @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    grey = np.clip(_resize(grey, w, h), 0, 1)
    tex = 1 + spec.texture * smooth_noise((h, w), 0.8, spec.seed)
    rel = np.clip((0.015 + 0.985 * grey) * tex, 10 ** -spec.dmax, 1.0)
    D = -np.log10(rel)
    t = np.exp(-D / spec.tone_scale)[..., None]
    tone = np.asarray(spec.tone_lo) + (np.asarray(spec.tone_hi) - np.asarray(spec.tone_lo)) * t
    od = D[..., None] * tone
    # paper: yellowing toward the edges, foxing spots
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    edge = np.minimum.reduce([xx, yy, w - 1 - xx, h - 1 - yy]) / (0.25 * min(w, h))
    yel = spec.yellowing * np.exp(-np.clip(edge, 0, 10))
    paper = np.broadcast_to(np.asarray(spec.paper, np.float32), (h, w, 3)).copy()
    paper[..., 2] *= (1 - yel)
    paper[..., 1] *= (1 - 0.35 * yel)
    rng = RNG(spec.seed + 7)
    fox = np.zeros((h, w), np.float32)
    for _ in range(spec.foxing):
        cy, cx = rng.uniform(0.05, 0.95) * h, rng.uniform(0.05, 0.95) * w
        r = rng.uniform(4, 12) * spec.size / 1400
        fox += np.exp(-((yy - cy) ** 2 + (xx - cx) ** 2) / (2 * r * r)) * rng.uniform(0.15, 0.4)
    fox_od = fox[..., None] * np.array([0.10, 0.22, 0.45], np.float32)
    # paint
    truth = {}
    od_paint = np.zeros((h, w, 3), np.float32)
    opaque = []
    for i, p in enumerate(paints):
        m = p.mask.astype(np.float32)
        amt = m * p.amount * np.clip(1 + p.texture * smooth_noise((h, w), 6, 100 + i), 0.2, 2.0)
        truth[p.name] = amt
        if p.opaque_rgb is None:
            od_paint += 2 * amt[..., None] * PAINTS[p.name]
        else:
            opaque.append((np.clip(amt, 0, 1), np.asarray(p.opaque_rgb, np.float32)))
    refl = paper * np.power(10.0, -(od + od_paint + fox_od)).astype(np.float32)
    for cover, col in opaque:
        refl = refl * (1 - cover[..., None]) + col * cover[..., None]
    gt = {"amounts": truth, "foxing": fox > 0.05, "density": D}
    return refl.astype(np.float32), gt


def _illum(h, w, spec: CaptureSpec):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cy, cx = (h - 1) / 2, (w - 1) / 2
    r2 = ((yy - cy) ** 2 + (xx - cx) ** 2) / (cx ** 2 + cy ** 2)
    inten = (1 - spec.vignette * r2) * (1 + spec.light_tilt * ((xx - cx) / cx * 0.7 + (yy - cy) / cy * 0.3))
    gains = np.broadcast_to(np.asarray(spec.cast, np.float32), (h, w, 3)).copy()
    if spec.gradient is not None:
        a, b = np.log(np.asarray(spec.gradient[0], np.float32)), np.log(np.asarray(spec.gradient[1], np.float32))
        t = (xx / (w - 1)) if spec.gradient_axis == "x" else (yy / (h - 1))
        t = t[..., None]
        gains *= np.exp(a + (b - a) * t)
    return inten[..., None] * gains


def _background(h, w, kind, seed):
    rng = RNG(seed)
    if kind == "wood":
        base = np.array([0.32, 0.20, 0.11], np.float32)
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        grain = 0.5 + 0.5 * np.sin(xx / 7 + 3 * smooth_noise((h, w), 25, seed))
        return base * (0.75 + 0.35 * grain)[..., None]
    if kind == "grey":
        return np.full((h, w, 3), 0.18, np.float32) * (1 + 0.03 * smooth_noise((h, w), 3, seed))[..., None]
    if kind == "cloth":
        base = np.array([0.10, 0.16, 0.22], np.float32)
        return base * (1 + 0.08 * smooth_noise((h, w), 1.5, seed))[..., None]
    raise ValueError(kind)


def capture(refl: np.ndarray, spec: CaptureSpec):
    """An unruly capture of a print: returns (8-bit sRGB uint8 image as decoded from the file, print box in it,
    file bytes or None)."""
    rng = RNG(spec.seed)
    ph, pw = refl.shape[:2]
    if spec.background:
        b = int(round(spec.border * max(ph, pw)))
        H, W = ph + 2 * b, pw + 2 * b
        scene = _background(H, W, spec.background, spec.seed + 3)
        scene[b:b + ph, b:b + pw] = refl
        box = (b, b, b + pw, b + ph)
    else:
        scene, H, W, box = refl.copy(), ph, pw, (0, 0, pw, ph)
    # light: colour and intensity field
    cam = scene * _illum(H, W, spec)
    # veiling glare and speculars (surface reflection: the light's own colour, unfiltered by the print)
    if spec.glare > 0:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        gy, gx = spec.glare_pos[1] * H, spec.glare_pos[0] * W
        rr = 0.18 * max(H, W)
        blob = spec.glare * np.exp(-((yy - gy) ** 2 + (xx - gx) ** 2) / (2 * rr * rr))
        cam = cam + blob[..., None] * _illum(H, W, spec) / max(_illum(H, W, spec).mean(), 1e-6) * 0.9
    if spec.speculars:
        for _ in range(spec.speculars):
            cy, cx = rng.uniform(0.1, 0.9) * H, rng.uniform(0.1, 0.9) * W
            cv2.ellipse(cam, (int(cx), int(cy)), (int(rng.uniform(3, 9)), int(rng.uniform(2, 5))),
                        float(rng.uniform(0, 180)), 0, 360, (3.0, 3.0, 3.0), -1)
    # lateral colour: R and B magnified differently about the centre
    if spec.lateral_colour:
        for c, sgn in ((0, 1), (2, -1)):
            sc = 1 + sgn * spec.lateral_colour
            M = np.float32([[sc, 0, (1 - sc) * (W - 1) / 2], [0, sc, (1 - sc) * (H - 1) / 2]])
            cam[..., c] = cv2.warpAffine(cam[..., c], M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    # sensor noise (linear): shot + read, plus low-frequency chroma mottle
    sd = spec.noise * np.sqrt(np.clip(cam, 0, None) / 0.18 + 0.05)
    cam = cam + rng.normal(size=cam.shape).astype(np.float32) * sd
    if spec.chroma_mottle:
        for c in (0, 2):
            cam[..., c] += spec.chroma_mottle * smooth_noise((H, W), 12, spec.seed + 11 + c) * np.sqrt(np.clip(cam[..., 1], 0, None))
    # white balance
    if spec.awb == "grayworld":
        m = cam.reshape(-1, 3).mean(axis=0)
        cam = cam * (m[1] / m)
    elif spec.awb == "fixed":
        cam = cam * np.asarray(spec.fixed_gains, np.float32)
    # exposure: paper white (99th percentile of G) to spec.exposure
    white = np.percentile(cam[..., 1], 99.0)
    cam = cam * (spec.exposure / max(white, 1e-6))
    # colour boost about luminance (linear), as phones do
    Y = cam @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    cam = Y[..., None] + spec.saturation * (cam - Y[..., None])
    # tone: sRGB encode then an S-curve
    v = srgb_encode(np.clip(cam, 0, 1))
    if spec.contrast:
        v = np.clip(v + spec.contrast * (v - 0.5) * (1 - np.abs(2 * v - 1)), 0, 1)
    # chroma noise reduction and luma sharpening in YCbCr (as the ISP's last steps)
    ycc = cv2.cvtColor(v.astype(np.float32), cv2.COLOR_RGB2YCrCb)
    if spec.chroma_nr:
        for c in (1, 2):
            ycc[..., c] = cv2.GaussianBlur(ycc[..., c], (0, 0), spec.chroma_nr)
    if spec.sharpen:
        bl = cv2.GaussianBlur(ycc[..., 0], (0, 0), 1.2)
        ycc[..., 0] = ycc[..., 0] + spec.sharpen * (ycc[..., 0] - bl)
    v = np.clip(cv2.cvtColor(ycc, cv2.COLOR_YCrCb2RGB), 0, 1)
    u8 = (v * 255 + 0.5).astype(np.uint8)
    data = None
    if spec.jpeg_q:
        buf = io.BytesIO()
        Image.fromarray(u8).save(buf, format="JPEG", quality=spec.jpeg_q, subsampling=2)
        data = buf.getvalue()
        u8 = np.asarray(Image.open(io.BytesIO(data)).convert("RGB"))
    return u8, box, data
