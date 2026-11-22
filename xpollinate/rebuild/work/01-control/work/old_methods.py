"""The earlier methods, run as they are (copied code or the copied modules), on one decoded capture.

Each returns a dict with "alpha" (H, W) 0-1: what the method would draw as colour present, and "show" (H, W) bool:
pixels it judged (False where it masks).  Nothing here is changed in the repositories.
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True


# ---------------------------------------------------------------------------- v1.2 (copied from Image_Visualiser_GUI_v.1.2.py)
def v12(img_u8: np.ndarray, boost=3.0, bias=0.0):
    img_rgb = img_u8
    lab_img = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    a = lab_img[:, :, 1] - 128
    b = lab_img[:, :, 2] - 128
    detection_gain = 3.0
    chroma_boosted = np.sqrt((a * detection_gain) ** 2 + (b * detection_gain) ** 2).flatten()
    max_val = max(100.0, float(chroma_boosted.max()))
    counts, bin_edges = np.histogram(chroma_boosted, bins=np.linspace(0, max_val, 200))
    peak_idx = np.argmax(counts)
    peak_val = bin_edges[peak_idx]
    if peak_idx > len(counts) * 0.9:
        base_threshold = np.percentile(chroma_boosted, 75) / detection_gain
    else:
        noise_cutoff = counts[peak_idx] * 0.01
        cutoff_val = peak_val + 10.0
        for i in range(peak_idx, len(counts)):
            if counts[i] < noise_cutoff:
                cutoff_val = bin_edges[i]
                break
        base_threshold = cutoff_val / detection_gain
    threshold = max(base_threshold + bias, 1.0)
    l, a8, b8 = cv2.split(lab_img)
    chroma = np.sqrt((a8 - 128) ** 2 + (b8 - 128) ** 2)
    valid_chroma = chroma[chroma > threshold]
    if len(valid_chroma) == 0:
        t3_end, t2_end = threshold + 5.0, threshold + 15.0
    else:
        t3_end = np.percentile(valid_chroma, 50)
        t2_end = np.percentile(valid_chroma, 85)
        t3_end = max(t3_end, threshold + 2.0)
        t2_end = max(t2_end, t3_end + 2.0)
    high_ramp = max(5.0, (t2_end - threshold) * 0.25)
    mask_faint = np.clip((chroma - threshold) / (t3_end - threshold), 0, 1)
    mask_mid = np.clip((chroma - t3_end) / (t2_end - t3_end), 0, 1)
    mask_high = np.clip((chroma - t2_end) / high_ramp, 0, 1)
    alpha = np.maximum.reduce([mask_faint * 0.4, mask_mid * 0.8, mask_high * 1.0])
    # its "chroma boosted" panel: a*, b* times the boost around absolute neutral
    L, A, B = cv2.split(lab_img)
    A2 = (A - 128) * boost + 128
    B2 = (B - 128) * boost + 128
    boosted = cv2.cvtColor(np.clip(cv2.merge([L, A2, B2]), 0, 255).astype(np.uint8), cv2.COLOR_LAB2RGB)
    return {"alpha": alpha.astype(np.float32), "show": np.ones(alpha.shape, bool), "threshold": threshold,
            "boosted": boosted, "presence_at": 0.2}


# ---------------------------------------------------------------------------- v4.1.2 (the copied script, imported)
_v41 = None


def _v41_mod():
    global _v41
    if _v41 is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location("v412", HERE / "v412.py")
        _v41 = importlib.util.module_from_spec(spec)
        sys.modules["v412"] = _v41
        spec.loader.exec_module(_v41)
    return _v41


def v41(img_u8: np.ndarray, space="raw"):
    m = _v41_mod()
    (HERE / "tmp_in").mkdir(exist_ok=True)
    cfg = m.VisualizerConfig(input_dir=HERE / "tmp_in", output_dir=HERE / "tmp_out")
    proc = m.ImageProcessor(cfg)
    rgb = img_u8.astype(np.float32) / 255.0
    lab = proc._rgb_to_lab(rgb, "sRGB")
    chroma = proc._chroma_from_lab(lab)
    if space == "raw":
        feature = chroma
    else:
        feature, _ = proc._compute_lrc(lab, chroma)
    threshold, alpha, binary, metrics = proc._threshold_and_map(feature, space)
    return {"alpha": alpha.astype(np.float32), "show": np.ones(alpha.shape, bool), "threshold": threshold,
            "presence_at": 0.2}


# ---------------------------------------------------------------------------- Woodii Chroma mode, JPEG quick look (tier C)
def woodii(img_u8: np.ndarray, untinted_mask: np.ndarray, base_mask=None, k=4.0, bin_=2):
    from wchroma import chroma as C
    from wchroma.render import srgb_decode
    counts = srgb_decode(img_u8.astype(np.float32) / 255.0).astype(np.float32)
    valid = ~C.jpeg_mask(counts)
    work, valid = C.bin_counts(counts, valid, bin_)
    h, w = work.shape[:2]
    um = cv2.resize(untinted_mask.astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST) > 0
    bm = None if base_mask is None else cv2.resize(base_mask.astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST) > 0
    try:
        res = C.tint_maps(work, um, bm, valid, smooth_px=0.0, k=k, edge_shift_px=C.EDGE_SHIFT_PX / bin_, eight_bit=True)
    except C.ChromaError as exc:
        return {"error": str(exc)}
    H, W = img_u8.shape[:2]
    up = lambda a: cv2.resize(a.astype(np.float32), (w * bin_, h * bin_), interpolation=cv2.INTER_NEAREST)  # noqa: E731
    flag = np.zeros((H, W), np.float32)
    show = np.zeros((H, W), bool)
    fu, su = up(res["flag"]), up(res["show"]) > 0.5
    flag[:fu.shape[0], :fu.shape[1]] = fu
    show[:su.shape[0], :su.shape[1]] = su
    return {"alpha": flag, "show": show, "record": res["record"], "presence_at": 0.5}
