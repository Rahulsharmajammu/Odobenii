"""Synthetic hand-coloured monochrome prints and 'unruly' captures of them.

Purpose: a test bench for reference (unpainted-appearance) estimators.  It checks code against a model; it is not
evidence that any method works on real photographs (Woodii's own record says the same of its forward models).

Print model (linear reflectance, per channel):
    R = paper * 10^(-D * tone(D))                 silver image, tone may shift with density
    R_painted = R * 10^(-2 * sum_k c_k * eps_k)   transparent washes, double pass (Beer-Lambert)
Capture model: illumination (falloff, colour cast that may vary across the frame), glare, white balance
(grey world on the painted frame, as a phone would), Poisson-Gaussian noise, sRGB encode, S-curve, phone saturation,
JPEG 4:2:0.  The 'unpainted twin' is the same scene and capture with no paint (same white balance, same noise).
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

import cv2
import numpy as np
from PIL import Image


def smoothstep(e0, e1, x):
    t = np.clip((np.asarray(x, np.float64) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def soft_ellipse(H, W, cy, cx, ry, rx, soft=3.0):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((yy - cy) / ry) ** 2 + ((xx - cx) / rx) ** 2)
    return np.clip((1.0 - r) * min(ry, rx) / soft + 0.5, 0.0, 1.0).astype(np.float32)


def soft_poly(H, W, pts, soft=2.5):
    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [np.round(np.array(pts)).astype(np.int32)], 255)
    m = m.astype(np.float32) / 255.0
    return cv2.GaussianBlur(m, (0, 0), soft)


def smooth_noise(H, W, sigma, rng):
    n = rng.standard_normal((H, W)).astype(np.float32)
    n = cv2.GaussianBlur(n, (0, 0), sigma)
    return n / (n.std() + 1e-9)


@dataclass
class Scene:
    D: np.ndarray                 # silver density
    regions: Dict[str, np.ndarray]
    image_area: np.ndarray        # inside the print's image (not border, not mount)
    border: np.ndarray            # paper margin with no image
    mount: np.ndarray             # outside the print


def portrait_scene(H=1000, W=760, seed=0, backdrop=(0.32, 0.55)) -> Scene:
    """A studio portrait on a print with a white border, lying on a dark mount."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    D = np.zeros((H, W), np.float32)
    regions: Dict[str, np.ndarray] = {}

    py0, py1, px0, px1 = 40, H - 40, 40, W - 40          # the print
    iy0, iy1, ix0, ix1 = 90, H - 90, 90, W - 90          # its image area
    printm = np.zeros((H, W), bool); printm[py0:py1, px0:px1] = True
    img = np.zeros((H, W), bool); img[iy0:iy1, ix0:ix1] = True
    border = printm & ~img
    mount = ~printm

    # backdrop: light-mid, top to bottom, mottled (a painted studio backdrop), darker corners
    t = (yy - iy0) / (iy1 - iy0)
    back = backdrop[0] + (backdrop[1] - backdrop[0]) * t + 0.05 * smooth_noise(H, W, 25, rng)
    cx, cy = (ix0 + ix1) / 2, (iy0 + iy1) / 2
    back += 0.25 * (((xx - cx) / (ix1 - ix0)) ** 2 + ((yy - cy) / (iy1 - iy0)) ** 2)
    floor = (yy > iy0 + 0.70 * (iy1 - iy0)).astype(np.float32)
    floor = cv2.GaussianBlur(floor, (0, 0), 3)
    back = back * (1 - floor) + (0.95 + 0.1 * smooth_noise(H, W, 12, rng)) * floor
    D[img] = back[img]
    regions["backdrop"] = (img & (floor < 0.5)).astype(np.float32)
    regions["floor"] = (img & (floor >= 0.5)).astype(np.float32)

    def put(mask, dens):
        nonlocal D
        D = D * (1 - mask) + dens * mask

    # suit (dark), with folds
    suit = soft_poly(H, W, [(380 - 110, 430), (380 + 110, 430), (380 + 175, 905), (380 - 175, 905)])
    put(suit, 1.35 + 0.18 * smooth_noise(H, W, 9, rng))
    regions["suit"] = suit
    # shirt front (white) and tie
    shirt = soft_poly(H, W, [(380 - 40, 420), (380 + 40, 420), (380, 560)])
    put(shirt, 0.10 + 0.03 * smooth_noise(H, W, 6, rng))
    regions["shirt"] = shirt
    tie = soft_poly(H, W, [(372, 430), (388, 430), (395, 545), (380, 565), (365, 545)])
    put(tie, 1.0)
    regions["tie"] = tie
    # neck and face, shaded from one side
    neck = soft_poly(H, W, [(350, 340), (410, 340), (420, 430), (340, 430)])
    face = soft_ellipse(H, W, 300, 380, 82, 62)
    shade = 0.22 + 0.22 * smoothstep(-60, 60, xx - 380) + 0.05 * smooth_noise(H, W, 5, rng)
    put(np.maximum(neck, face), shade)
    regions["face"] = np.maximum(neck, face)
    # hair
    hair = soft_ellipse(H, W, 245, 380, 52, 66) * (yy < 262).astype(np.float32)
    hair = cv2.GaussianBlur(hair, (0, 0), 2)
    put(hair, 1.65 + 0.1 * smooth_noise(H, W, 4, rng))
    regions["hair"] = hair
    # eyes and lips
    for ex in (356, 404):
        put(soft_ellipse(H, W, 290, ex, 5, 9, 1.5), 1.1)
    lips = soft_ellipse(H, W, 343, 380, 7, 17, 1.5)
    put(lips, 0.55)
    regions["lips"] = lips
    # hands
    hands = np.maximum(soft_ellipse(H, W, 760, 262, 24, 30), soft_ellipse(H, W, 760, 498, 24, 30))
    put(hands, 0.30 + 0.06 * smooth_noise(H, W, 4, rng))
    regions["hands"] = hands
    # brooch / tie pin (bright, small)
    pin = soft_ellipse(H, W, 470, 382, 7, 7, 1.0)
    put(pin, 0.15)
    regions["pin"] = pin
    # a plant at the left: leaves of mid-dark tone
    plant = np.zeros((H, W), np.float32)
    for _ in range(14):
        cy_, cx_ = rng.uniform(470, 790), rng.uniform(120, 230)
        plant = np.maximum(plant, soft_ellipse(H, W, cy_, cx_, rng.uniform(12, 22), rng.uniform(30, 45), 2.0))
    plant *= img
    put(plant, 0.75 + 0.25 * smooth_noise(H, W, 6, rng))
    regions["plant"] = plant

    # film grain and paper texture (density, fine)
    D = D + img * 0.012 * rng.standard_normal((H, W)).astype(np.float32)
    D = np.clip(D, 0.0, 2.2)
    D[~img] = 0.0
    return Scene(D=D.astype(np.float32), regions=regions, image_area=img, border=border, mount=mount)


# ---- print tone, paper and paint ------------------------------------------------------------------------------------

TONES = {
    "neutral": lambda D: np.ones(D.shape + (3,), np.float32),
    # warm (sepia-like): more absorption in blue
    "warm": lambda D: np.broadcast_to(np.array([0.90, 1.0, 1.18], np.float32), D.shape + (3,)),
    # tone that shifts with density: warm highlights, near-neutral (slightly cool) shadows
    "split": lambda D: (np.array([0.86, 1.0, 1.26], np.float32) * (1 - smoothstep(0.25, 1.4, D)[..., None])
                        + np.array([1.03, 1.0, 0.97], np.float32) * smoothstep(0.25, 1.4, D)[..., None]),
}
PAPERS = {"white": (0.88, 0.88, 0.87), "yellowed": (0.86, 0.82, 0.68)}
MOUNT = (0.06, 0.06, 0.07)

# per unit amount, single-pass OD in R, G, B
PAINTS = {
    "skin": (0.010, 0.060, 0.085),
    "red": (0.02, 0.30, 0.24),
    "blue": (0.09, 0.035, 0.0),
    "green": (0.12, 0.0, 0.11),
    "gold": (0.0, 0.05, 0.25),
    "pink": (0.0, 0.05, 0.02),
}


def paint_layers(sc: Scene, recipe: Dict[str, Tuple[str, float]]) -> Tuple[np.ndarray, np.ndarray]:
    """recipe: region name -> (paint name, amount).  Returns paint OD (H, W, 3) single-pass and amount map (H, W)."""
    H, W = sc.D.shape
    od = np.zeros((H, W, 3), np.float32)
    amount = np.zeros((H, W), np.float32)
    for region, (paint, amt) in recipe.items():
        m = sc.regions[region] if region in sc.regions else REGION_FNS[region](sc)
        od += (m * amt)[..., None] * np.array(PAINTS[paint], np.float32)
        amount = np.maximum(amount, m * amt)
    return od, amount


def _light_band(sc: Scene) -> np.ndarray:
    """Every light-grey area of the image (D below 0.5), whatever the object: for a wash over a whole tone band."""
    return (sc.image_area & (sc.D < 0.5)).astype(np.float32)


def _top_third(sc: Scene) -> np.ndarray:
    H, W = sc.D.shape
    yy = np.mgrid[0:H, 0:W][0]
    return (sc.regions["backdrop"] * smoothstep(0.42 * H, 0.30 * H, yy)).astype(np.float32)


REGION_FNS = {"lightband": _light_band, "topthird": _top_third}


def reflectance(sc: Scene, tone="neutral", paper="white", paint_od=None, mirroring=0.0, seed=0) -> np.ndarray:
    D = sc.D
    t = TONES[tone](D)
    R = np.array(PAPERS[paper], np.float32) * np.power(10.0, -D[..., None] * t)
    if paint_od is not None:
        R = R * np.power(10.0, -2.0 * paint_od)
    if mirroring > 0:   # silver mirroring: bluish metallic sheen in dense areas, patchy
        rng = np.random.default_rng(seed + 7)
        patch = smoothstep(0.0, 1.0, smooth_noise(*D.shape, 30, rng))
        R = R + mirroring * (smoothstep(1.2, 1.7, D) * patch)[..., None] * np.array([0.7, 0.85, 1.1], np.float32)
    R[sc.mount] = MOUNT
    return R.astype(np.float32)


# ---- capture ------------------------------------------------------------------------------------------------------

@dataclass
class Capture:
    cast_left: Tuple[float, float, float] = (1.0, 1.0, 1.0)    # illuminant colour at the left edge
    cast_right: Tuple[float, float, float] = (1.0, 1.0, 1.0)   # ... and at the right edge
    falloff: float = 0.25          # vignetting strength
    gradient: float = 0.15         # intensity gradient left to right
    glare: float = 0.0             # peak of a specular blob (linear units)
    glare_at: Tuple[float, float] = (0.30, 0.70)
    awb: str = "greyworld"         # 'greyworld' (from the painted frame) or 'none'
    exposure: float = 1.0
    noise_a: float = 1.5e-4        # shot noise
    noise_b: float = 2.0e-3        # read noise
    contrast: float = 0.35         # S-curve
    saturation: float = 1.2        # phone 'look'
    jpeg_q: Optional[int] = 82     # None: no JPEG
    seed: int = 0


def _s_curve(y, k):
    return np.clip(y + k * 4.0 * (y - 0.5) * y * (1.0 - y), 0.0, 1.0)


def srgb_encode(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def _saturate(rgb, s):
    ycc = cv2.cvtColor(rgb.astype(np.float32), cv2.COLOR_RGB2YCrCb)
    ycc[..., 1:] = 0.5 + (ycc[..., 1:] - 0.5) * s
    return np.clip(cv2.cvtColor(ycc, cv2.COLOR_YCrCb2RGB), 0, 1)


def capture(R: np.ndarray, cap: Capture, wb_gains=None, noise_seed=None):
    """Linear reflectance -> decoded 8-bit sRGB (float 0-1).  Returns (rgb, wb_gains, noise-free rgb)."""
    H, W = R.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    u, v = xx / (W - 1), yy / (H - 1)
    inten = (1.0 - cap.falloff * ((u - 0.5) ** 2 + (v - 0.5) ** 2) * 2.0) * (1.0 + cap.gradient * (0.5 - u))
    col = (np.array(cap.cast_left, np.float32) * (1 - u)[..., None] + np.array(cap.cast_right, np.float32) * u[..., None])
    lin = R * inten[..., None] * col
    if cap.glare > 0:
        gy, gx = cap.glare_at[0] * H, cap.glare_at[1] * W
        blob = cap.glare * np.exp(-(((yy - gy) ** 2 + (xx - gx) ** 2) / (2 * (0.06 * W) ** 2)))
        lin = lin + blob[..., None]
    if wb_gains is None:
        if cap.awb == "greyworld":
            m = lin.reshape(-1, 3).mean(axis=0)
            wb_gains = m[1] / m
        else:
            wb_gains = np.ones(3, np.float32)
    lin = lin * np.asarray(wb_gains, np.float32) * cap.exposure
    rng = np.random.default_rng(cap.seed if noise_seed is None else noise_seed)
    clean = lin.copy()
    noisy = lin + rng.standard_normal(lin.shape).astype(np.float32) * np.sqrt(cap.noise_a * np.clip(lin, 0, None)
                                                                             + cap.noise_b ** 2)

    def render(x):
        y = _s_curve(srgb_encode(x), cap.contrast)
        return _saturate(y, cap.saturation)
    out = render(noisy)
    clean_out = render(clean)
    if cap.jpeg_q is not None:
        out = jpeg(out, cap.jpeg_q)
    return out.astype(np.float32), np.asarray(wb_gains, np.float32), clean_out.astype(np.float32)


def jpeg(rgb, q, subsampling=2):
    im = Image.fromarray(np.clip(np.round(rgb * 255), 0, 255).astype(np.uint8))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=q, subsampling=subsampling)
    buf.seek(0)
    return np.asarray(Image.open(buf).convert("RGB")).astype(np.float32) / 255.0


@dataclass
class Case:
    name: str
    rgb: np.ndarray            # the capture as decoded
    twin: np.ndarray           # the same capture with no paint
    clean: np.ndarray          # noise-free capture (for ground truth)
    clean_twin: np.ndarray
    amount: np.ndarray         # paint amount
    scene: Scene
    note: str = ""


def make_case(name, recipe=None, tone="neutral", paper="white", cap: Capture = None, seed=0, mirroring=0.0,
              note="", backdrop=(0.32, 0.55)):
    cap = cap or Capture(seed=seed)
    sc = portrait_scene(seed=seed, backdrop=backdrop)
    if recipe:
        pod, amount = paint_layers(sc, recipe)
    else:
        pod, amount = None, np.zeros(sc.D.shape, np.float32)
    R = reflectance(sc, tone, paper, pod, mirroring, seed)
    R0 = reflectance(sc, tone, paper, None, mirroring, seed)
    rgb, wb, clean = capture(R, cap)
    twin, _, clean_twin = capture(R0, cap, wb_gains=wb, noise_seed=cap.seed)
    return Case(name, rgb, twin, clean, clean_twin, amount, sc, note)
