"""The methods compared on the bench.

* v41_raw, v41_lrc: Chroma_diagnoser_v4.1 (4.1.2) as it is, loaded read-only from the visualiser repository.
* todo: TODO.md's pipeline as written (L*-band median reference, rolling smoothing along L*, robust spread,
  automatic refits; the optional plane in x, y; vector feature; 2-5 spread opacity ramp).
* proposal: the refined design of the report (see proposal.py).
* woodii: Woodii's Chroma mode maps (commit 5b1757d), on a linear capture with picks, k = 4.

Each returns an opacity map in [0, 1] on the working grid (what a viewer would see as "colour here").
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import sys
from pathlib import Path

import cv2
import numpy as np
from scipy.ndimage import median_filter
from skimage import color

WORK = Path(__file__).resolve().parent
REPO_SCRIPT = Path("/home/user/handpaint_visualiser/Chroma_diagnoser_v4.1")


def _load_v41():
    loader = importlib.machinery.SourceFileLoader("cd41", str(REPO_SCRIPT))
    spec = importlib.util.spec_from_loader("cd41", loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["cd41"] = mod
    loader.exec_module(mod)
    return mod


_V41 = None
_PROC = None


def v41(rgb_u8: np.ndarray, space: str) -> np.ndarray:
    """4.1.2's segmented-map opacity for ``space`` 'raw' (C*ab) or 'lrc', default settings, analysis at full size."""
    global _V41, _PROC
    if _V41 is None:
        _V41 = _load_v41()
        (WORK / "v41_in").mkdir(exist_ok=True)
        cfg = _V41.VisualizerConfig(input_dir=WORK / "v41_in", output_dir=WORK / "v41_out")
        _PROC = _V41.ImageProcessor(cfg)
    rgb = rgb_u8.astype(np.float32) / 255.0
    lab = _PROC._rgb_to_lab(rgb, "sRGB")
    chroma = _PROC._chroma_from_lab(lab)
    feature = chroma
    if space == "lrc":
        feature, _ = _PROC._compute_lrc(lab, chroma)
    _, alpha, _, _ = _PROC._threshold_and_map(feature, space)
    return alpha.astype(np.float32)


# -- TODO.md as written ------------------------------------------------------------------------------------------------

def lab_of(rgb_u8):
    return color.rgb2lab(rgb_u8.astype(np.float32) / 255.0).astype(np.float32)


def smoothstep(x, lo, hi):
    t = np.clip((x - lo) / (hi - lo), 0, 1)
    return t * t * (3 - 2 * t)


def todo_plan(rgb_u8, plane=False, picks=None, bands=2.0, rounds=4):
    lab = lab_of(rgb_u8)
    L = lab[..., 0]
    a = median_filter(lab[..., 1], size=5)
    b = median_filter(lab[..., 2], size=5)
    clipped = (rgb_u8 >= 250).any(axis=2)
    dark = L < 8
    usable = ~clipped & ~dark
    H, W = L.shape
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    xn, yn = xx / W - 0.5, yy / H - 0.5
    keep = usable.copy() if picks is None else (usable & picks)
    edges = np.arange(0, 100 + bands, bands)
    nb = len(edges) - 1
    idx = np.clip(np.digitize(L, edges) - 1, 0, nb - 1)
    pa = pb = np.zeros_like(L)
    for _ in range(rounds if picks is None else 1):
        ma, mb, sp = np.full(nb, np.nan), np.full(nb, np.nan), np.full(nb, np.nan)
        ra, rb = a - pa, b - pb
        for k in range(nb):
            m = keep & (idx == k)
            if m.sum() < 50:
                continue
            ma[k], mb[k] = np.median(ra[m]), np.median(rb[m])
        ok = np.isfinite(ma)
        xs = np.arange(nb)
        ma = np.interp(xs, xs[ok], ma[ok])
        mb = np.interp(xs, xs[ok], mb[ok])
        kern = np.ones(3) / 3
        ma = np.convolve(np.pad(ma, 1, mode="edge"), kern, mode="valid")
        mb = np.convolve(np.pad(mb, 1, mode="edge"), kern, mode="valid")
        va, vb = a - ma[idx], b - mb[idx]
        if plane:
            m = keep
            A = np.stack([xn[m], yn[m]], axis=1)
            ca = np.linalg.lstsq(A, va[m], rcond=None)[0]
            cb = np.linalg.lstsq(A, vb[m], rcond=None)[0]
            pa = ca[0] * xn + ca[1] * yn
            pb = cb[0] * xn + cb[1] * yn
            va, vb = va - pa, vb - pb
        r = np.hypot(va, vb)
        for k in range(nb):
            m = keep & (idx == k)
            if m.sum() < 50:
                continue
            # the robust spread of a 2-D scatter: the Rayleigh scale, median |v| / 1.1774 (fair to the TODO)
            sp[k] = max(np.median(r[m]) / 1.1774, 0.35)
        ok = np.isfinite(sp)
        sp = np.interp(xs, xs[ok], sp[ok])
        z = r / sp[idx]
        if picks is None:
            keep = usable & (z < 3)
    z = median_filter(z, size=5)
    alpha = smoothstep(z, 2, 5)
    alpha[~usable] = 0
    return alpha.astype(np.float32), dict(z=z, va=va, vb=vb, usable=usable)


# -- Woodii's Chroma mode -----------------------------------------------------------------------------------------------

def woodii_module():
    if "woodii_chroma" in sys.modules:
        return sys.modules["woodii_chroma"]
    loader = importlib.machinery.SourceFileLoader("woodii_chroma", str(WORK / "woodii_chroma.py"))
    spec = importlib.util.spec_from_loader("woodii_chroma", loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["woodii_chroma"] = mod
    loader.exec_module(mod)
    return mod


def woodii(counts, untinted_boxes, base_boxes, k=4.0):
    C = woodii_module()
    res = C.tint_maps(counts, untinted_boxes, base_boxes, k=k)
    return res["flag"].astype(np.float32), res
