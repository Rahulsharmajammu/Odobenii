"""Synthetic hand-painted monochrome prints and an 'unruly' phone-like capture of them.

Scene (linear reflectance per channel):
    R_c(x) = P_c(x) * texture_c(x) * 10^-(D(x) * s_c(D) + 2 * sum_k a_k(x) * eps_kc)
  D      silver density from a greyscale portrait (skimage 'astronaut'), Dmax about 2.1, in a paper margin
  s_c(D) image tone per unit density: constant (one tone) or shifting with density (warm highlights, cool shadows)
  P_c    cream paper, optionally with a low-frequency stain field (uneven yellowing)
  paint  transparent washes, double pass (Beer-Lambert), soft edges
Capture (camera-like, display-referred output):
  light   intensity falloff and optionally a colour gradient across the frame (mixed light)
  sheen   dichromatic model (Shafer 1985): radiance = E_c * (R_c + m_s), m_s neutral interface reflection:
          a veil modulated by cockle, and a hot spot
  optics  lateral chromatic aberration (R and B magnified differently about the centre)
  sensor  RGGB mosaic, Poisson-Gaussian noise, edge-aware demosaic (OpenCV EA)
  ISP     shades-of-grey AWB (p = 4), a saturating CCM, optional local tone mapping (shadow lift from blurred
          luminance), a filmic tone curve, sRGB encoding, a saturation 'look', chroma noise reduction,
          JPEG 4:2:0 at quality 88 (Pillow / libjpeg)
Everything is seeded.  Ground truth: the paint's OD per channel at each pixel.
"""
from __future__ import annotations

import io
import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import cv2
import numpy as np
from PIL import Image
from skimage import data

CONTENT = 1024            # paint coordinates are given on a 1024 x 1024 grid of the portrait


def srgb_dec(v):
    v = np.asarray(v, np.float64)
    return np.where(v <= 0.04045, v / 12.92, ((np.clip(v, 0.04045, None) + 0.055) / 1.055) ** 2.4)


def srgb_enc(v):
    v = np.clip(np.asarray(v, np.float64), 0, None)
    return np.where(v <= 0.0031308, 12.92 * v, 1.055 * np.power(np.clip(v, 0.0031308, None), 1 / 2.4) - 0.055)


# ----------------------------------------------------------------------------------------------------------------------
# paint layers (shape, colourant, amount); eps = single-pass OD per unit amount in R, G, B
# ----------------------------------------------------------------------------------------------------------------------

PINK = (0.02, 0.35, 0.22)       # cheeks
RED = (0.03, 0.60, 0.42)        # lips, small touches
BLUE = (0.45, 0.22, 0.03)       # a garment wash: lowers chroma on a warm print
SKY = (0.36, 0.14, 0.02)        # background wash
FLESH = (0.02, 0.13, 0.30)      # an overall flesh tint (orange-pink)
HAIR = (0.06, 0.22, 0.42)       # brown
YGREEN = (0.20, 0.03, 0.30)     # a faint yellow-green wash
GOLD = (0.02, 0.10, 0.55)       # a gold touch


@dataclass
class Layer:
    name: str
    kind: str                  # 'ellipse' | 'poly' | 'rect_minus_ellipse'
    geom: tuple
    eps: Tuple[float, float, float]
    amount: float
    soft: float = 4.0          # edge softness (px on the 1024 grid)
    group: str = "clear"       # 'clear' | 'faint' | 'touch'


BASIC = [
    Layer("cheek_L", "ellipse", ((405, 262), (34, 26)), PINK, 0.14, 7, "faint"),
    Layer("cheek_R", "ellipse", ((528, 262), (34, 26)), PINK, 0.14, 7, "faint"),
    Layer("lips", "ellipse", ((452, 290), (46, 15)), RED, 0.30, 2.5, "clear"),
    Layer("garment", "poly", ([(80, 520), (250, 440), (330, 470), (330, 1020), (60, 1020)],), BLUE, 0.14, 3, "clear"),
    Layer("rocket_faint", "poly", ([(770, 160), (900, 160), (905, 470), (760, 470)],), YGREEN, 0.045, 5, "faint"),
    Layer("touch1", "ellipse", ((330, 760), (9, 9)), RED, 0.45, 1.0, "touch"),
    Layer("touch2", "ellipse", ((362, 805), (7, 7)), RED, 0.45, 1.0, "touch"),
    Layer("touch3", "ellipse", ((612, 700), (10, 6)), GOLD, 0.40, 1.0, "touch"),
    Layer("touch4", "ellipse", ((494, 646), (6, 6)), RED, 0.45, 1.0, "touch"),
]

EXTENSIVE = BASIC + [
    Layer("sky", "rect_minus_ellipse", ((150, 0, 740, 345), ((455, 185), (165, 185))), SKY, 0.11, 6, "clear"),
    Layer("skin", "ellipse", ((455, 245), (112, 125)), FLESH, 0.12, 8, "clear"),
    Layer("hair", "ellipse", ((455, 105), (150, 85)), HAIR, 0.14, 8, "clear"),
    Layer("flag", "poly", ([(0, 0), (185, 0), (195, 700), (0, 700)],), RED, 0.16, 3, "clear"),
]


def layer_mask(layer: Layer, n: int) -> np.ndarray:
    """A soft 0-1 mask for a layer on an n x n content grid (geometry given on the 1024 grid)."""
    s = n / CONTENT
    m = np.zeros((n, n), np.float32)
    if layer.kind == "ellipse":
        (cx, cy), (ax, ay) = layer.geom
        cv2.ellipse(m, (int(round(cx * s)), int(round(cy * s))), (max(1, int(round(ax * s))), max(1, int(round(ay * s)))),
                    0, 0, 360, 1.0, -1, lineType=cv2.LINE_AA)
    elif layer.kind == "poly":
        pts = np.array([[int(round(x * s)), int(round(y * s))] for x, y in layer.geom[0]], np.int32)
        cv2.fillPoly(m, [pts], 1.0, lineType=cv2.LINE_AA)
    elif layer.kind == "rect_minus_ellipse":
        (x0, y0, x1, y1), ((cx, cy), (ax, ay)) = layer.geom
        m[int(y0 * s):int(y1 * s), int(x0 * s):int(x1 * s)] = 1.0
        cv2.ellipse(m, (int(cx * s), int(cy * s)), (int(ax * s), int(ay * s)), 0, 0, 360, 0.0, -1, lineType=cv2.LINE_AA)
    if layer.soft > 0:
        m = cv2.GaussianBlur(m, (0, 0), layer.soft * s)
    return np.clip(m, 0, 1)


# ----------------------------------------------------------------------------------------------------------------------
# the print
# ----------------------------------------------------------------------------------------------------------------------

@dataclass
class PrintSpec:
    size: int = 2048                    # frame (capture) size in px, square
    margin: float = 0.05                # paper margin round the image, share of the frame
    paper: Tuple[float, float, float] = (0.86, 0.82, 0.70)
    tone_hi: Tuple[float, float, float] = (0.96, 1.0, 1.06)     # OD per unit density, light end
    tone_lo: Tuple[float, float, float] = (0.96, 1.0, 1.06)     # dark end (equal: one tone)
    stain_od: Tuple[float, float, float] = (0.0, 0.0, 0.0)      # low-frequency uneven yellowing, peak OD
    layers: List[Layer] = field(default_factory=lambda: list(BASIC))
    texture: bool = True                # paper texture and silver grain (off: the forward models' clean world)
    seed: int = 7


def _smooth_field(shape, sigma, rng):
    """A smooth random field with correlation length about ``sigma`` px, made small and enlarged (fast)."""
    k = max(4, int(round(8 * shape[0] / sigma)))
    small = cv2.GaussianBlur(rng.standard_normal((k, k)).astype(np.float32), (0, 0), 8 * shape[0] / sigma / 8)
    f = cv2.resize(small, (shape[1], shape[0]), interpolation=cv2.INTER_CUBIC)
    f -= f.mean()
    return f / (np.abs(f).max() + 1e-9)


def make_print(spec: PrintSpec) -> Dict[str, np.ndarray]:
    rng = np.random.default_rng(spec.seed)
    n = spec.size
    m = int(round(spec.margin * n))
    cn = n - 2 * m                                                      # content size
    grey = np.asarray(Image.fromarray(data.astronaut()).convert("L"), np.float64) / 255.0
    lin = srgb_dec(grey)
    lin = cv2.resize(lin.astype(np.float32), (cn, cn), interpolation=cv2.INTER_CUBIC).astype(np.float64)
    lin = np.clip(lin / np.percentile(lin, 99.7), 10 ** -2.1, 1.0)          # brightest image areas reach paper
    D = np.zeros((n, n))
    D[m:m + cn, m:m + cn] = -np.log10(lin)
    # silver grain: neutral density noise growing with density, a little blurred
    grain = cv2.GaussianBlur(rng.standard_normal((n, n)).astype(np.float32), (0, 0), 0.8)
    if spec.texture:
        D = np.clip(D + grain * (0.004 + 0.010 * D), 0, None)
    # image tone, possibly shifting with density
    t = np.clip((D - 0.2) / 1.4, 0, 1)[..., None]
    t = t * t * (3 - 2 * t)
    s = np.asarray(spec.tone_hi) * (1 - t) + np.asarray(spec.tone_lo) * t
    od = D[..., None] * s
    # paper, its stain field and its texture
    stain = (0.5 + 0.5 * _smooth_field((n, n), n / 5, rng))[..., None] * np.asarray(spec.stain_od)
    tex_n = cv2.GaussianBlur(rng.standard_normal((n, n)).astype(np.float32), (0, 0), 1.2)[..., None] * 0.015
    tex_c = np.stack([cv2.GaussianBlur(rng.standard_normal((n, n)).astype(np.float32), (0, 0), 1.2) for _ in range(3)],
                     axis=-1) * 0.003
    texture = 1.0 + tex_n + tex_c if spec.texture else np.ones((n, n, 1))
    # paint: transparent washes, double pass
    paint_od = np.zeros((n, n, 3))
    groups = {g: np.zeros((n, n), np.float32) for g in ("clear", "faint", "touch")}
    for L in spec.layers:
        mk = np.zeros((n, n), np.float32)
        mk[m:m + cn, m:m + cn] = layer_mask(L, cn)
        paint_od += 2 * L.amount * mk[..., None] * np.asarray(L.eps)
        groups[L.group] = np.maximum(groups[L.group], mk)
    R = np.asarray(spec.paper) * texture * 10 ** -(od + stain + paint_od)
    return {"R": R.astype(np.float32), "D": D.astype(np.float32), "paint_od": paint_od.astype(np.float32),
            "groups": groups, "margin": m}


# ----------------------------------------------------------------------------------------------------------------------
# the capture
# ----------------------------------------------------------------------------------------------------------------------

@dataclass
class CaptureSpec:
    light_left: Tuple[float, float, float] = (1.0, 1.0, 1.0)    # light colour at the left edge (per channel gain)
    light_right: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    falloff: float = 0.25                # intensity falls by this share toward the right, plus a vignette
    veil: float = 0.0                    # neutral interface reflection (sheen), share of the light, modulated by cockle
    hot: float = 0.0                     # peak of a specular hot spot
    lca: float = 0.0008                  # relative magnification of R (+) and B (-) about the centre
    read: float = 0.003
    gain: float = 4e-5
    awb_p: float = 4.0
    local_tm: float = 0.0                # strength of local shadow lift (0 = global tone curve only)
    look_sat: float = 1.15
    chroma_nr: float = 2.0               # Gaussian sd of the ISP's chroma noise reduction, px
    quality: int = 88
    seed: int = 11


CCM = np.array([[1.55, -0.40, -0.15], [-0.22, 1.42, -0.20], [-0.05, -0.45, 1.50]])


def _magnify(ch, k):
    if k == 0:
        return ch
    h, w = ch.shape
    M = np.array([[1 + k, 0, -k * (w - 1) / 2], [0, 1 + k, -k * (h - 1) / 2]], np.float32)
    return cv2.warpAffine(ch, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def _mosaic_demosaic(rgb, rng, read, gain):
    """RGGB mosaic with Poisson-Gaussian noise, then OpenCV's edge-aware demosaic."""
    h, w, _ = rgb.shape
    mos = np.empty((h, w), np.float32)
    mos[0::2, 0::2] = rgb[0::2, 0::2, 0]
    mos[0::2, 1::2] = rgb[0::2, 1::2, 1]
    mos[1::2, 0::2] = rgb[1::2, 0::2, 1]
    mos[1::2, 1::2] = rgb[1::2, 1::2, 2]
    mos = mos + rng.standard_normal(mos.shape).astype(np.float32) * np.sqrt(read ** 2 + gain * np.clip(mos, 0, None))
    m16 = np.clip(mos * 65535, 0, 65535).astype(np.uint16)
    # OpenCV names the pattern by the 2x2 block starting at (1, 1); for RGGB data that is BG.  Checked by test_bayer().
    out = cv2.cvtColor(m16, cv2.COLOR_BayerBG2RGB_EA)
    return out.astype(np.float32) / 65535.0


def test_bayer():
    rgb = np.ones((16, 16, 3), np.float32) * np.array([0.8, 0.4, 0.1], np.float32)
    out = _mosaic_demosaic(rgb, np.random.default_rng(0), 0.0, 0.0)
    assert np.allclose(out[4:-4, 4:-4], [0.8, 0.4, 0.1], atol=2e-3), out[8, 8]


def _filmic(x):
    """A filmic S-curve on linear values (paper about 0.8 maps to about 0.93 before encoding)."""
    x = np.clip(x, 0, None)
    a = x * (1 + x / 4.0) / (1 + x)                   # Reinhard extended, white at 2
    return np.clip(a * 1.33, 0, 1)


def capture(R: np.ndarray, spec: CaptureSpec) -> Dict[str, np.ndarray]:
    rng = np.random.default_rng(spec.seed)
    h, w, _ = R.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u = xx / (w - 1)
    r2 = ((xx - w / 2) ** 2 + (yy - h / 2) ** 2) / (0.5 * math.hypot(w, h)) ** 2
    intensity = (1 - spec.falloff * u) * (1 - 0.18 * r2)
    col = (1 - u)[..., None] * np.asarray(spec.light_left) + u[..., None] * np.asarray(spec.light_right)
    E = intensity[..., None] * col
    # sheen: neutral interface reflection of the light (dichromatic model), veil modulated by cockle, plus a hot spot
    cockle = 1 + 0.7 * np.sin(2 * np.pi * xx / (w / 3.3)) * np.sin(2 * np.pi * yy / (h / 2.6) + 0.7)
    hot = np.exp(-(((xx - 0.78 * w) ** 2 + (yy - 0.20 * h) ** 2) / (2 * (0.06 * w) ** 2)))
    m_s = spec.veil * cockle + spec.hot * hot
    radiance = E * (R + m_s[..., None])
    exposure = 0.80 / (0.86 * float(np.percentile(E[..., 1], 99)))
    cam = (radiance * exposure).astype(np.float32)
    lin_counts = cam.copy()                                        # before optics and ISP (for linear tests)
    cam = np.stack([_magnify(cam[..., 0], spec.lca), cam[..., 1], _magnify(cam[..., 2], -spec.lca)], axis=-1)
    cam = _mosaic_demosaic(np.clip(cam, 0, 1), rng, spec.read, spec.gain)
    # AWB: shades of grey (Finlayson and Trezzi 2004), p = awb_p, unclipped pixels
    ok = (cam < 0.98).all(axis=2)
    est = np.power(np.mean(np.power(np.clip(cam[ok], 1e-6, None), spec.awb_p), axis=0), 1 / spec.awb_p)
    cam = cam * (est[1] / est)
    lin = np.clip(cam @ CCM.T, 0, None)
    if spec.local_tm > 0:                                          # local tone mapping: lift dark neighbourhoods
        Y = lin @ np.array([0.2126, 0.7152, 0.0722])
        Yb = cv2.GaussianBlur(Y.astype(np.float32), (0, 0), w / 50)
        g = np.clip(((Yb + 0.04) / 0.84) ** (-spec.local_tm), 1.0, 3.0)
        lin = lin * g[..., None]
    enc = srgb_enc(_filmic(lin))
    # look: saturation in YCbCr, then the ISP's chroma noise reduction
    ycc = cv2.cvtColor(np.clip(enc, 0, 1).astype(np.float32), cv2.COLOR_RGB2YCrCb)
    ycc[..., 1:] = 0.5 + (ycc[..., 1:] - 0.5) * spec.look_sat
    if spec.chroma_nr > 0:
        for c in (1, 2):
            ycc[..., c] = cv2.GaussianBlur(ycc[..., c], (0, 0), spec.chroma_nr)
    enc = np.clip(cv2.cvtColor(ycc, cv2.COLOR_YCrCb2RGB), 0, 1)
    img8 = np.round(enc * 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(img8).save(buf, "JPEG", quality=spec.quality, subsampling=2)
    jpeg_bytes = buf.getvalue()
    decoded = np.asarray(Image.open(io.BytesIO(jpeg_bytes)).convert("RGB"))
    return {"jpeg": jpeg_bytes, "decoded": decoded, "lin_counts": lin_counts, "sheen": m_s.astype(np.float32),
            "intensity": intensity.astype(np.float32)}


if __name__ == "__main__":
    test_bayer()
    print("bayer ok")
