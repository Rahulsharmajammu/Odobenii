"""Synthetic hand-coloured gelatin silver prints and uncontrolled captures of them.

A test bench, not a model of any real print.  The print is built in per-channel optical density (camera R, G, B taken
as three broad bands): a silver image whose tone may change with density, a paper base, yellowing, foxing, an
adhesive stain, silvering in the shadows near the edges, transparent media (Beer-Lambert, double pass), an opaque
white and a near-neutral spotting dye.  The capture adds what a phone or document camera adds: uneven light whose
colour drifts across the frame, vignetting, a glare veil with a clipped hot spot, auto white balance, auto exposure,
a non-sRGB tone curve, lateral colour fringes, sharpening, noise and 4:2:0 JPEG.  Optional: a phone's semantic
skin-tone rendering on the face, and a table around the print.

Everything returns ground-truth masks so the methods can be scored here (the tool itself reports nothing numeric).
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import Dict, Optional

import cv2
import numpy as np
from PIL import Image
from skimage import color, data


def srgb_decode(v):
    v = np.clip(v, 0, 1)
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def srgb_encode(v):
    v = np.clip(v, 0, 1)
    return np.where(v <= 0.0031308, 12.92 * v, 1.055 * np.power(v, 1 / 2.4) - 0.055)


def soft(mask, sigma):
    m = mask.astype(np.float32)
    if sigma > 0:
        m = cv2.GaussianBlur(m, (0, 0), sigma)
    return np.clip(m, 0, 1)


def ellipse(H, W, cx, cy, ax, ay):
    yy, xx = np.mgrid[0:H, 0:W]
    return ((xx - cx) / ax) ** 2 + ((yy - cy) / ay) ** 2 <= 1.0


# single-pass OD per unit amount, channels R, G, B
INKS = {
    "rose": np.array([0.02, 0.36, 0.17]),      # cheeks, lips
    "flesh": np.array([0.02, 0.14, 0.26]),     # an overall flesh tint
    "blue": np.array([0.30, 0.14, 0.03]),      # a backdrop or sky wash
    "yellow": np.array([0.02, 0.07, 0.42]),    # a yellow wash: the same direction as yellowing
    "green": np.array([0.30, 0.04, 0.28]),
    "red": np.array([0.02, 0.45, 0.40]),
    "gold": np.array([0.03, 0.12, 0.45]),
}


@dataclass
class PrintOpts:
    content: str = "astronaut"         # or "camera"
    size: int = 1024                   # long edge of the image area
    border: float = 0.05               # paper margin, fraction of the size
    dmax: float = 1.7
    tone: str = "warm"                 # neutral | warm (tone changes with density) | sepia (strongest in highlights)
    paper: tuple = (0.84, 0.82, 0.75)  # base reflectance per channel (cream)
    yellowing: float = 0.0             # 0 none, 1 typical: uniform plus stronger toward the top and left edges
    foxing: int = 0                    # number of foxing spots
    adhesive: bool = False             # a yellow-brown band along the right edge (mount adhesive)
    mirroring: float = 0.0             # silvering in the shadows near the bottom edge
    paint: str = "none"                # none | portrait | heavy | landscape
    paint_scale: float = 1.0
    seed: int = 0


@dataclass
class CaptureOpts:
    gradient: float = 0.0              # colour drift of the light across the frame (1 = typical mixed light)
    vignette: float = 0.0
    glare: float = 0.0                 # veil strength
    hotspot: bool = False
    awb: bool = True
    tone_curve: bool = True
    ca: float = 0.0                    # lateral colour: R scaled by 1 + ca, B by 1 - ca, about the centre
    sharpen: float = 0.0
    noise: float = 0.003
    jpeg: Optional[int] = 80           # quality; None for a lossless 8-bit capture
    semantic_skin: float = 0.0         # a phone's skin-tone rendering on the face (a* and b* added)
    table: bool = False                # the print on a brown table filling the rest of the frame
    seed: int = 1


def _content(name, size):
    if name == "astronaut":
        g = color.rgb2gray(data.astronaut())
    elif name == "camera":
        g = data.camera().astype(np.float64) / 255.0
    else:
        raise ValueError(name)
    g = cv2.resize(g.astype(np.float32), (size, size), interpolation=cv2.INTER_CUBIC)
    return np.clip(g, 0, 1)


def make_print(o: PrintOpts):
    rng = np.random.default_rng(o.seed)
    g = _content(o.content, o.size)
    s = o.size
    b = int(round(o.border * s))
    H = W = s + 2 * b
    gray = np.ones((H, W), np.float32)           # paper margin reads as paper (no silver)
    gray[b:b + s, b:b + s] = g
    image_area = np.zeros((H, W), bool)
    image_area[b:b + s, b:b + s] = True
    # silver density: content lightness to reflectance relative to paper, with a little grain
    lin = srgb_decode(gray)
    rmin = 10 ** (-o.dmax)
    rrel = rmin + (1 - rmin) * lin
    grain = 1 + 0.015 * cv2.GaussianBlur(rng.normal(size=(H, W)).astype(np.float32), (0, 0), 0.8)
    rrel = np.clip(rrel * np.where(image_area, grain, 1.0), rmin, 1.0)
    D = -np.log10(rrel)
    D[~image_area] = 0.0
    # tone along density
    if o.tone == "neutral":
        w = np.zeros(3)
        f = np.zeros_like(D)
    elif o.tone == "warm":                       # warm mid-tones, near neutral at Dmax: a warm-tone developing-out paper
        w = np.array([-0.10, 0.0, 0.20])
        f = np.exp(-((D - 0.55) / 0.45) ** 2)
    elif o.tone == "sepia":                      # sulfide-toned, strongest in the highlights
        w = np.array([-0.25, 0.0, 0.40])
        f = np.clip(1.0 - 0.45 * D / o.dmax, 0, 1)
    else:
        raise ValueError(o.tone)
    od = D[..., None] * (1.0 + w[None, None, :] * f[..., None])
    truth: Dict[str, np.ndarray] = {}
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    # yellowing: uniform plus a gradient toward the top and left edges
    if o.yellowing > 0:
        prox = np.exp(-np.minimum(xx, yy) / (0.15 * W))
        y = o.yellowing * (0.35 + 0.9 * prox)
        od += y[..., None] * np.array([0.004, 0.018, 0.075])
        truth["yellowing_edge"] = prox > 0.35
    if o.foxing:
        fm = np.zeros((H, W), np.float32)
        for _ in range(o.foxing):
            cx, cy = rng.uniform(0.05, 0.95, 2) * [W, H]
            r = rng.uniform(2.5, 9.0)
            amp = rng.uniform(0.6, 1.4)
            fm = np.maximum(fm, amp * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * r ** 2)))
        od += fm[..., None] * np.array([0.03, 0.10, 0.17])
        truth["foxing"] = fm > 0.25
    if o.adhesive:
        n = cv2.GaussianBlur(rng.normal(size=(H, W)).astype(np.float32), (0, 0), 12)
        n = n / (np.abs(n).max() + 1e-9)
        band = (xx > 0.9 * W + 0.03 * W * n * 3) & (yy > 0.1 * H) & (yy < 0.85 * H)
        a = soft(band, 6) * 0.9
        od += a[..., None] * np.array([0.01, 0.05, 0.12])
        truth["adhesive"] = a > 0.25
    # media
    amounts = {k: np.zeros((H, W), np.float32) for k in INKS}
    white = np.zeros((H, W), np.float32)
    spot = np.zeros((H, W), np.float32)
    k = s / 512.0

    def P(x, y):
        return b + x * k, b + y * k

    if o.paint in ("portrait", "heavy") and o.content == "astronaut":
        cx, cy = P(225, 112)
        face = ellipse(H, W, cx, cy, 44 * k, 54 * k)
        amounts["flesh"] += soft(face, 6 * k) * 0.035
        for xc in (198, 252):
            cx, cy = P(xc, 128)
            amounts["rose"] += soft(ellipse(H, W, cx, cy, 13 * k, 9 * k), 5 * k) * 0.05
        cx, cy = P(225, 147)
        amounts["rose"] += soft(ellipse(H, W, cx, cy, 14 * k, 5 * k), 1.5 * k) * 0.16
        backdrop = (xx > b + 300 * k) & (yy < b + 250 * k) & (gray > 0.45) & (gray < 0.80) & image_area
        backdrop = cv2.morphologyEx(backdrop.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)) > 0
        amounts["blue"] += soft(backdrop, 3 * k) * 0.045
        cx, cy = P(170, 385)
        amounts["yellow"] += soft(ellipse(H, W, cx, cy, 37 * k, 37 * k), 2 * k) * 0.05
        for i in range(6):
            cx, cy = P(242, 300 + 30 * i)
            amounts["gold"] += soft(ellipse(H, W, cx, cy, 2.2 * k, 2.2 * k), 0.8) * 0.20
        cx, cy = P(430, 55)
        white += soft((np.abs(xx - cx) < 18 * k) & (np.abs(yy - cy) < 4 * k), 1.0) * 0.6
        for i in range(5):
            cx, cy = P(330 + 35 * i, 30 + 12 * (i % 2))
            spot += soft(ellipse(H, W, cx, cy, 2.0 * k, 2.0 * k), 0.7) * 0.5
        if o.paint == "heavy":
            flag = (xx < b + 80 * k) & (yy > b + 0 * k) & image_area & (gray < 0.45)
            amounts["red"] += soft(flag, 1.5 * k) * 0.10
            suit = (xx > b + 25 * k) & (xx < b + 360 * k) & (yy > b + 230 * k) & (gray > 0.3) & (gray < 0.72)
            suit &= ~ellipse(H, W, *P(170, 385), 40 * k, 40 * k)
            amounts["blue"] += soft(suit, 3 * k) * 0.05
            amounts["flesh"] += soft(face, 6 * k) * 0.05
            amounts["blue"] += soft(backdrop, 3 * k) * 0.06
    elif o.paint == "landscape" and o.content == "camera":
        sky = (yy < b + 175 * k) & (gray > 0.62) & image_area
        sky = cv2.morphologyEx(sky.astype(np.uint8), cv2.MORPH_OPEN, np.ones((7, 7), np.uint8)) > 0
        amounts["blue"] += soft(sky, 4 * k) * 0.04
        grass = (yy > b + 250 * k) & (xx > b + 150 * k) & (gray > 0.30) & (gray < 0.78) & image_area
        grass = cv2.morphologyEx(grass.astype(np.uint8), cv2.MORPH_OPEN, np.ones((7, 7), np.uint8)) > 0
        amounts["green"] += soft(grass, 4 * k) * 0.035
    for name in amounts:
        amounts[name] *= o.paint_scale
        od += 2.0 * amounts[name][..., None] * INKS[name][None, None, :]
    spot_od = spot[..., None] * np.array([0.25, 0.25, 0.27])
    od += spot_od
    paper = np.asarray(o.paper, np.float32)
    refl = paper[None, None, :] * 10 ** (-od)
    if o.mirroring > 0:
        prox = np.exp(-(H - yy) / (0.12 * H))
        dens = np.clip(D / o.dmax, 0, 1) ** 2
        m = o.mirroring * prox * dens
        refl += m[..., None] * np.array([0.020, 0.026, 0.040])
        truth["mirroring"] = m > 0.15 * o.mirroring
    refl = (1 - white[..., None]) * refl + white[..., None] * np.array([0.86, 0.86, 0.84])
    for name, a in amounts.items():
        if a.max() > 0:
            truth[f"paint_{name}"] = a > 0.25 * a.max()
    if white.max() > 0:
        truth["paint_white"] = white > 0.3
    if spot.max() > 0:
        truth["paint_spotting"] = spot > 0.25
    truth["border"] = ~image_area
    truth["image_area"] = image_area
    gy, gx = np.gradient(cv2.GaussianBlur(gray, (0, 0), 1.0))
    truth["edge"] = np.hypot(gx, gy) > 0.02
    return refl.astype(np.float32), gray, truth


def capture(refl, truth, c: CaptureOpts, face_center=None):
    rng = np.random.default_rng(c.seed)
    H, W = refl.shape[:2]
    if c.table:
        pad = int(0.22 * max(H, W))
        HH, WW = H + 2 * pad, W + 2 * pad
        tex = cv2.GaussianBlur(rng.normal(size=(HH, WW)).astype(np.float32), (0, 0), 3)
        streak = cv2.GaussianBlur(rng.normal(size=(HH, 8)).astype(np.float32), (0, 0), 2)
        streak = cv2.resize(streak, (WW, HH), interpolation=cv2.INTER_LINEAR)
        wood = np.array([0.36, 0.22, 0.11]) * (1 + 0.08 * tex + 0.15 * streak)[..., None]
        big = wood.astype(np.float32)
        big[pad:pad + H, pad:pad + W] = refl
        refl = big
        nt = {}
        for kk, m in truth.items():
            mm = np.zeros((HH, WW), bool)
            mm[pad:pad + H, pad:pad + W] = m
            nt[kk] = mm
        tm = np.ones((HH, WW), bool)
        tm[pad:pad + H, pad:pad + W] = False
        nt["table"] = tm
        truth = nt
        H, W = HH, WW
        if face_center is not None:
            face_center = (face_center[0] + pad, face_center[1] + pad)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    u, v = xx / W - 0.5, yy / H - 0.5
    E = 1.0 - c.vignette * 0.35 * (u ** 2 + v ** 2) / 0.5
    gamma = c.gradient * np.array([0.06, 0.0, -0.08])
    delta = c.gradient * np.array([0.02, 0.0, -0.03])
    gain = np.exp(gamma[None, None, :] * 2 * u[..., None] + delta[None, None, :] * 2 * v[..., None])
    lin = refl * E[..., None] * gain
    if c.glare > 0:
        cx, cy, sg = 0.72 * W, 0.30 * H, 0.12 * W
        V = c.glare * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * sg ** 2))
        lin = lin + V[..., None] * np.array([1.0, 1.0, 1.05])
        truth = dict(truth)
        truth["glare"] = V > 0.25 * c.glare
        if c.hotspot:
            hs = np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * (0.015 * W) ** 2))
            lin = lin + 2.0 * hs[..., None]
            truth["hotspot"] = hs > 0.2
    if c.ca:
        out = np.empty_like(lin)
        for ch, sc in ((0, 1 + c.ca), (1, 1.0), (2, 1 - c.ca)):
            M = np.array([[sc, 0, (1 - sc) * W / 2], [0, sc, (1 - sc) * H / 2]], np.float32)
            out[..., ch] = cv2.warpAffine(lin[..., ch].astype(np.float32), M, (W, H), flags=cv2.INTER_LINEAR,
                                          borderMode=cv2.BORDER_REFLECT)
        lin = out
    lin = lin + rng.normal(size=lin.shape).astype(np.float32) * np.sqrt(c.noise ** 2 + 0.0008 * np.clip(lin, 0, None))
    if c.awb:                                       # grey world over the frame
        m = lin.reshape(-1, 3).mean(axis=0)
        lin = lin * (m[1] / m)[None, None, :]
    lin = lin * (0.90 / np.percentile(lin[..., 1], 99.0))
    enc = srgb_encode(np.clip(lin, 0, 1))
    if c.tone_curve:
        enc = enc - 0.05 * np.sin(2 * np.pi * enc)
    if c.sharpen:
        blur = cv2.GaussianBlur(enc.astype(np.float32), (0, 0), 1.2)
        enc = enc + c.sharpen * (enc - blur)
    enc = np.clip(enc, 0, 1)
    if c.semantic_skin and face_center is not None:
        lab = color.rgb2lab(enc)
        fx, fy, rx, ry = face_center
        fm = soft(ellipse(H, W, fx, fy, rx, ry), 0.02 * W)
        lab[..., 1] += c.semantic_skin * fm
        lab[..., 2] += 1.2 * c.semantic_skin * fm
        enc = np.clip(color.lab2rgb(lab), 0, 1)
        truth = dict(truth)
        truth["semantic"] = fm > 0.3
    u8 = np.round(enc * 255).astype(np.uint8)
    if c.jpeg:
        buf = io.BytesIO()
        Image.fromarray(u8).save(buf, format="JPEG", quality=c.jpeg, subsampling=2)
        u8 = np.asarray(Image.open(io.BytesIO(buf.getvalue())).convert("RGB"))
    return u8, truth


def linear_capture(refl, seed=1, gain=2e-5, read=2e-4):
    """A copy-stand raw-like capture: linear counts, even light, shot and read noise (Woodii's intended input)."""
    rng = np.random.default_rng(seed)
    x = refl * 0.9
    return (x + rng.normal(size=x.shape) * np.sqrt(read ** 2 + gain * np.clip(x, 0, None))).astype(np.float32)


def face_ellipse(o: PrintOpts):
    s = o.size
    b = int(round(o.border * s))
    k = s / 512.0
    return (b + 225 * k, b + 112 * k, 44 * k, 54 * k)
