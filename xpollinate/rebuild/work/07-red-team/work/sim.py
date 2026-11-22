"""Synthetic hand-coloured, toned silver print and an 'unruly' phone-like capture of it.

Nothing here is a claim about real VDZ prints.  It is a stand-in with known ground truth, built so the
failure modes named in the report can be shown with numbers and pictures.  The print model is the one the
plans themselves assume (Beer-Lambert washes over a toned silver image on a yellowed paper base), so a method
that fails here fails on its own assumptions.

Coordinates: the print is PxP pixels (P = 1024); the regions are given in the 512-px coordinates of
skimage's 'astronaut' portrait (doubled here).
"""
from __future__ import annotations

import io
import math
from dataclasses import dataclass, field

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import color, data, transform

P = 1024
S = P / 512.0


# ----------------------------------------------------------------------------- print

def _ellipse(cx, cy, rx, ry, feather):
    yy, xx = np.mgrid[0:P, 0:P].astype(np.float32)
    r = np.sqrt(((xx - cx * S) / (rx * S)) ** 2 + ((yy - cy * S) / (ry * S)) ** 2)
    m = (r <= 1.0).astype(np.float32)
    return ndi.gaussian_filter(m, feather * S) if feather else m


def _rect(x0, y0, x1, y1, feather):
    m = np.zeros((P, P), np.float32)
    m[int(y0 * S):int(y1 * S), int(x0 * S):int(x1 * S)] = 1.0
    return ndi.gaussian_filter(m, feather * S) if feather else m


@dataclass
class Print:
    R: np.ndarray                     # linear reflectance, (P, P, 3), the painted print
    R_unpainted: np.ndarray           # the same print with no applied media (deterioration kept)
    layers: dict                      # name -> (amount map, kind)
    gray: np.ndarray                  # the photograph's own tones, 0-1


def silver_print(split_tone=True, paper=(0.80, 0.78, 0.68), dmax=1.9, seed=1):
    """A toned gelatin-silver-like print: OD per channel = D * t(D), t warm in light tones and more neutral in
    the shadows when split_tone (selenium/sepia-like); paper base yellowed."""
    rng = np.random.default_rng(seed)
    g = color.rgb2gray(data.astronaut())
    g = transform.resize(g, (P, P), order=3, anti_aliasing=True)
    g = np.clip(g + ndi.gaussian_filter(rng.normal(0, 0.012, g.shape), 0.8), 0, 1)
    D = dmax * (1.0 - g) ** 1.15
    t_lo = np.array([0.78, 1.00, 1.32])
    t_hi = np.array([0.96, 1.00, 1.06]) if split_tone else t_lo
    s = np.clip(D / 1.4, 0, 1)[..., None]
    t = t_lo * (1 - s) + t_hi * s
    t = t / t.mean(axis=-1, keepdims=True)
    od = D[..., None] * t
    R = np.asarray(paper, np.float32) * np.power(10.0, -od)
    return R.astype(np.float32), g.astype(np.float32)


def paint_layers(extensive=False):
    """Amount maps (0-1) and Beer-Lambert absorbances per channel (R, G, B) for each applied medium."""
    L = {}
    # transparent washes: (amount map, eps per channel, kind)
    L["cheeks"] = (np.maximum(_ellipse(197, 128, 16, 12, 4), _ellipse(252, 128, 16, 12, 4)) * 0.30,
                   np.array([0.02, 0.22, 0.15]), "paint")
    L["lips"] = (_ellipse(224, 147, 15, 6, 1.5) * 0.7, np.array([0.03, 0.55, 0.40]), "paint")
    L["flag_red"] = (_rect(0, 110, 78, 330, 2) * 0.55, np.array([0.02, 0.50, 0.40]), "paint")
    L["flag_blue"] = (_rect(0, 0, 70, 108, 2) * 0.5, np.array([0.45, 0.25, 0.03]), "paint")
    L["patch_yellow"] = (_ellipse(172, 386, 26, 26, 2) * 0.6, np.array([0.00, 0.05, 0.45]), "paint")
    if extensive:
        m = _rect(0, 0, 512, 512, 0) * (1 - _ellipse(225, 112, 58, 78, 6))
        m *= 1 - _rect(282, 342, 512, 512, 3)
        L["wash"] = (np.clip(m, 0, 1) * 1.0, np.array([0.035, 0.018, 0.00]), "paint")
    else:
        m = np.maximum.reduce([_rect(296, 0, 360, 250, 6), _rect(452, 0, 512, 250, 6), _rect(92, 0, 168, 60, 6)])
        L["wash"] = (m * 1.0, np.array([0.035, 0.018, 0.00]), "paint")
    # neutral retouching: spotting dye matched to the image tone (no colour departure by construction) and a
    # neutral grey spotting on the warm print (a small departure toward cool)
    rng = np.random.default_rng(7)
    spots_matched = np.zeros((P, P), np.float32)
    spots_neutral = np.zeros((P, P), np.float32)
    for k in range(14):
        cx, cy = rng.uniform(60, 300), rng.uniform(380, 500)
        tgt = spots_matched if k % 2 == 0 else spots_neutral
        tgt += _ellipse(cx, cy, 3.5, 3.5, 0.6)
    L["retouch_matched"] = (np.clip(spots_matched, 0, 1), None, "retouch_matched")
    L["retouch_neutral"] = (np.clip(spots_neutral, 0, 1) * 0.6, np.array([0.30, 0.30, 0.30]), "retouch_neutral")
    return L


def deterioration(R, seed=3):
    """Foxing (brown spots) and a mat burn (yellow-brown band at the left and bottom): colour departures that are
    not paint."""
    rng = np.random.default_rng(seed)
    fox = np.zeros((P, P), np.float32)
    for _ in range(40):
        cx, cy = rng.uniform(10, 500), rng.uniform(10, 500)
        fox += _ellipse(cx, cy, rng.uniform(1.5, 4.0), rng.uniform(1.5, 4.0), 0.8) * rng.uniform(0.4, 1.0)
    fox = np.clip(fox, 0, 1)
    burn = np.maximum(_rect(0, 0, 14, 512, 3), _rect(0, 498, 512, 512, 3))
    out = R * np.power(10.0, -2 * fox[..., None] * np.array([0.04, 0.12, 0.28]))
    out = out * np.power(10.0, -2 * burn[..., None] * np.array([0.01, 0.03, 0.09]))
    return out.astype(np.float32), {"foxing": fox, "mat_burn": burn}


def make_print(extensive=False, split_tone=True, with_deterioration=True):
    R0, g = silver_print(split_tone=split_tone)
    det = {}
    if with_deterioration:
        R0, det = deterioration(R0)
    layers = paint_layers(extensive)
    R = R0.copy()
    for name, (amt, eps, kind) in layers.items():
        if kind == "retouch_matched":
            continue          # matched to the image tone: the print looks unpainted here, by design
        R = R * np.power(10.0, -2.0 * amt[..., None] * eps)     # double pass through a transparent layer
    gt = {k: v[0] for k, v in layers.items()}
    gt.update(det)
    return Print(R=R.astype(np.float32), R_unpainted=R0, layers=gt, gray=g)


def chromatic_paint_mask(pr: Print, frac=0.5):
    """Core of each chromatic paint region (amount at least frac of its peak)."""
    out = {}
    for k in ("cheeks", "lips", "flag_red", "flag_blue", "patch_yellow", "wash"):
        a = pr.layers[k]
        out[k] = a >= frac * a.max()
    return out


def any_medium(pr: Print, tol=0.02):
    m = np.zeros((P, P), bool)
    for k, a in pr.layers.items():
        m |= a > tol
    return m


# ----------------------------------------------------------------------------- capture

@dataclass
class Capture:
    tungsten_lr: tuple = (0.0, 0.0)     # tungsten share at left and right edges (mixed light gradient)
    tungsten_tb: tuple = (0.0, 0.0)     # ... at top and bottom
    vignette: float = 0.0
    falloff: float = 0.0               # linear intensity falloff left->right
    shading: float = 0.0               # residual lens colour shading (R up, B down toward the corners)
    ca: float = 0.0                    # lateral chromatic aberration: R scaled by (1 + ca), B by (1 - ca)
    awb: str = "perfect"               # perfect | grayworld | whitepatch
    sat: float = 1.0                   # 'look' saturation in linear RGB
    scurve: float = 0.0
    ltm: float = 0.0                   # local tone mapping strength
    chroma_blur: float = 0.0
    jpeg_q: int = 95
    subsampling: int = 0               # Pillow: 0 = 4:4:4, 2 = 4:2:0
    glare: tuple | None = None         # (cx, cy, radius) in print-512 coordinates
    rot_deg: float = 0.0
    persp: float = 0.0
    noise: float = 0.004
    seed: int = 0


TUNGSTEN = np.array([1.0, 0.74, 0.45], np.float32)     # relative to daylight, camera-native


def homography(c: Capture):
    th = math.radians(c.rot_deg)
    cx = cy = P / 2
    Rm = np.array([[math.cos(th), -math.sin(th), 0], [math.sin(th), math.cos(th), 0], [0, 0, 1]])
    T1 = np.array([[1, 0, -cx], [0, 1, -cy], [0, 0, 1]])
    T2 = np.array([[1, 0, cx], [0, 1, cy], [0, 0, 1]])
    Pp = np.array([[1, 0, 0], [0, 1, 0], [c.persp / P, 0.6 * c.persp / P, 1]])
    Sc = np.diag([1.04, 1.04, 1.0])                     # zoom in slightly so the warped print fills the frame
    return (T2 @ Sc @ Pp @ Rm @ T1).astype(np.float64)


def warp(img, Hm, interp=cv2.INTER_LINEAR):
    return cv2.warpPerspective(img, Hm, (P, P), flags=interp, borderMode=cv2.BORDER_REFLECT)


def _radial():
    yy, xx = np.mgrid[0:P, 0:P].astype(np.float32)
    return (((xx - P / 2) ** 2 + (yy - P / 2) ** 2) / (P / 2) ** 2)


def _scale_about_centre(ch, s):
    M = np.array([[s, 0, (1 - s) * P / 2], [0, s, (1 - s) * P / 2]], np.float32)
    return cv2.warpAffine(ch, M, (P, P), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def srgb_encode(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def capture(R, c: Capture):
    """R: linear reflectance (P, P, 3) of the print.  Returns (8-bit sRGB capture, homography print->capture)."""
    rng = np.random.default_rng(c.seed)
    Hm = homography(c)
    Rw = warp(R, Hm)
    yy, xx = np.mgrid[0:P, 0:P].astype(np.float32)
    w = (c.tungsten_lr[0] + (c.tungsten_lr[1] - c.tungsten_lr[0]) * xx / P
         + c.tungsten_tb[0] + (c.tungsten_tb[1] - c.tungsten_tb[0]) * yy / P)
    illum = (1 - w)[..., None] * np.ones(3, np.float32) + w[..., None] * TUNGSTEN
    inten = (1 - c.vignette * _radial()) * (1 - c.falloff * xx / P)
    raw = Rw * illum * inten[..., None]
    if c.glare:
        gx, gy, gr = c.glare
        blob = np.exp(-(((xx - gx * S) ** 2 + (yy - gy * S) ** 2) / (2 * (gr * S) ** 2)))
        raw = raw + 0.9 * blob[..., None] * illum
    rr = _radial()
    raw[..., 0] *= 1 + c.shading * rr
    raw[..., 2] *= 1 - c.shading * rr
    if c.ca:
        raw[..., 0] = _scale_about_centre(raw[..., 0], 1 + c.ca)
        raw[..., 2] = _scale_about_centre(raw[..., 2], 1 - c.ca)
    raw = raw + rng.normal(0, 1, raw.shape).astype(np.float32) * np.sqrt(c.noise ** 2 + 0.002 * np.maximum(raw, 0))\
        * 0.25
    # white balance
    core = raw[int(0.1 * P):int(0.9 * P), int(0.1 * P):int(0.9 * P)].reshape(-1, 3)
    if c.awb == "grayworld":
        m = core.mean(axis=0)
        gains = m[1] / m
    elif c.awb == "whitepatch":
        lum = core.sum(axis=1)
        sel = lum >= np.percentile(lum, 99.0)
        m = core[sel].mean(axis=0)
        gains = m[1] / m
    else:                                                     # the illuminant at the frame centre, removed
        wc = w[P // 2, P // 2]
        gains = 1.0 / ((1 - wc) + wc * TUNGSTEN)
    img = raw * gains
    # saturation look in linear RGB
    Y = img @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    img = Y[..., None] + c.sat * (img - Y[..., None])
    # exposure
    img = img * (0.93 / np.percentile(img[..., 1], 99.5))
    enc = srgb_encode(img)
    if c.scurve:
        enc = (1 - c.scurve) * enc + c.scurve * (3 * enc ** 2 - 2 * enc ** 3)
    enc = np.clip(enc, 0, 1).astype(np.float32)
    if c.ltm or c.chroma_blur:
        ycc = cv2.cvtColor(enc, cv2.COLOR_RGB2YCrCb)
        if c.ltm:
            y = ycc[..., 0]
            base = cv2.GaussianBlur(y, (0, 0), 40)
            ycc[..., 0] = np.clip(y + c.ltm * (y - base), 0, 1)
        if c.chroma_blur:
            for k in (1, 2):
                ycc[..., k] = cv2.GaussianBlur(ycc[..., k], (0, 0), c.chroma_blur)
        enc = np.clip(cv2.cvtColor(ycc, cv2.COLOR_YCrCb2RGB), 0, 1)
    u8 = (np.clip(enc, 0, 1) * 255 + 0.5).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(u8).save(buf, format="JPEG", quality=c.jpeg_q, subsampling=c.subsampling)
    buf.seek(0)
    out = np.asarray(Image.open(buf).convert("RGB"))
    return out, Hm


# Capture settings used in the report
CLEAN = Capture(awb="perfect", jpeg_q=95, subsampling=0, noise=0.002, seed=11)
UNRULY_A = Capture(tungsten_lr=(0.02, 0.40), vignette=0.25, falloff=0.15, shading=0.03, ca=0.0015, awb="grayworld",
                   sat=1.2, scurve=0.25, ltm=0.3, chroma_blur=1.2, jpeg_q=85, subsampling=2, glare=(420, 60, 18),
                   rot_deg=1.5, persp=0.02, seed=21)
UNRULY_B = Capture(tungsten_tb=(0.35, 0.0), vignette=0.15, falloff=-0.05, shading=-0.02, ca=-0.001, awb="whitepatch",
                   sat=1.1, scurve=0.15, ltm=0.15, chroma_blur=1.0, jpeg_q=80, subsampling=2, glare=(60, 470, 16),
                   rot_deg=-2.0, persp=-0.015, seed=33)
UNRULY_C = Capture(tungsten_lr=(0.30, 0.0), vignette=0.30, falloff=0.10, shading=0.04, ca=0.002, awb="grayworld",
                   sat=1.25, scurve=0.2, ltm=0.25, chroma_blur=1.5, jpeg_q=75, subsampling=2, glare=(250, 300, 14),
                   rot_deg=3.0, persp=0.03, seed=45)
