"""Woodii's Chroma mode in its own setting: linear, flat-fielded copy-stand counts with its tests' noise model, bin 2,
k = 4, picks of untinted image and of the paper margin.  Conditions add, one at a time, what its decisions set aside:
paper texture and grain, tone that shifts with density, uneven yellowing, and a 0.5 % sheen floor (with cockle).
The proposed reference (on the same counts, sRGB-encoded) is run alongside."""
from __future__ import annotations

import json
import math
import sys
from dataclasses import replace
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / "vendor"))
sys.path.insert(0, str(HERE))
from woodii_chroma import chroma as WC  # noqa: E402
import visualiser_proto as V  # noqa: E402
from sim_print import PrintSpec, make_print, srgb_enc  # noqa: E402
from gen_scenes import TONE_SHIFT, STAIN  # noqa: E402
from run_eval import UNTINTED_1024, BASE_FRAME, to_frame, scale_box  # noqa: E402

GAIN, READ = 2e-5, 2e-4          # Woodii's tests: var = READ^2 + GAIN * counts, full scale 1


def counts_for(ps: PrintSpec, veil: float, seed=3):
    p = make_print(ps)
    n = p["R"].shape[0]
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    cockle = 1 + 0.7 * np.sin(2 * np.pi * xx / (n / 3.3)) * np.sin(2 * np.pi * yy / (n / 2.6) + 0.7)
    clean = (p["R"] + (veil * cockle)[..., None]) * (0.80 / 0.86)        # flat-fielded: light uniform after the flat
    rng = np.random.default_rng(seed)
    noisy = clean + rng.standard_normal(clean.shape).astype(np.float32) * np.sqrt(READ ** 2 + GAIN * np.clip(clean, 0, None))
    return noisy.astype(np.float32), p


def gt_masks(p, size):
    rs = lambda a: cv2.resize(np.asarray(a, np.float32), (size, size), interpolation=cv2.INTER_AREA)  # noqa: E731
    paint = rs(p["paint_od"]).max(axis=2)
    g = {k: rs(p["groups"][k]) for k in ("clear", "faint", "touch")}
    D = rs(p["D"])
    unp = (paint < 0.004) & (g["clear"] < 0.02) & (g["faint"] < 0.02) & (g["touch"] < 0.02)
    pos = ((g["clear"] > 0.5) | (g["faint"] > 0.5) | (g["touch"] > 0.5)) & (paint > 0.02)
    return unp, pos, D


def summarise(shown, unp, pos, D, usable):
    unp = unp & usable
    pos = pos & usable
    return {"TPR": float(shown[pos].mean()), "FPR": float(shown[unp].mean()),
            "FPR_light": float(shown[unp & (D < 0.35)].mean()), "FPR_mid": float(shown[unp & (D >= 0.35) & (D < 1.1)].mean()),
            "FPR_dark": float(shown[unp & (D >= 1.1)].mean())}


CONDITIONS = {
    "L0_tests_world": (dict(texture=False), 0.0),
    "L1_texture": ({}, 0.0),
    "L2_tone_shift": (dict(**TONE_SHIFT), 0.0),
    "L3_stain": (dict(**STAIN), 0.0),
    "L4_sheen_0.5pc": ({}, 0.005),
    "L5_all": (dict(**TONE_SHIFT, **STAIN), 0.005),
}


def main():
    out = {}
    for name, (kw, veil) in CONDITIONS.items():
        counts, p = counts_for(PrintSpec(**kw), veil)
        work, valid = WC.bin_counts(counts, None, 2)
        unt = [scale_box(to_frame(b), 0.5) for b in UNTINTED_1024]
        base = [scale_box(b, 0.5) for b in BASE_FRAME]
        res = WC.tint_maps(work, unt, base, valid, smooth_px=0.0, k=WC.DEFAULT_K, edge_shift_px=WC.EDGE_SHIFT_PX / 2)
        size = work.shape[0]
        unp, pos, D = gt_masks(p, size)
        usable = res["show"]
        w = summarise(res["flag"], unp, pos, D, usable)
        w["noise_how"] = res["record"]["noise"]["how"]
        w["sigma0_od"] = res["record"]["noise"]["sigma0_od"]
        w["axis_deg"] = res["record"]["axis"]["angle_from_neutral_deg"]
        # the proposed reference on the same counts, encoded for display (no other processing)
        enc = np.clip(srgb_enc(np.clip(work, 0, 1)) * 255 + 0.5, 0, 255).astype(np.uint8)
        from PIL import Image
        import io
        buf = io.BytesIO()
        Image.fromarray(enc).save(buf, "PNG")
        r = V.run(buf.getvalue(), long_edge=size, opts=V.Options())
        valid_p = r["masks"]["valid"]
        pr = summarise(r["pics"]["alpha"] >= 0.5, unp, pos, D, valid_p & usable)
        out[name] = {"woodii": w, "proposed": pr}
        print(f"{name:16s} Woodii: TPR {w['TPR']:.2f} FPR {w['FPR']:.3f} (L {w['FPR_light']:.3f} M {w['FPR_mid']:.3f} "
              f"D {w['FPR_dark']:.3f}) noise {w['noise_how']} sigma0 {w['sigma0_od']} | proposed: TPR {pr['TPR']:.2f} "
              f"FPR {pr['FPR']:.3f} (L {pr['FPR_light']:.3f} M {pr['FPR_mid']:.3f} D {pr['FPR_dark']:.3f})", flush=True)
        if name in ("L1_texture", "L5_all"):
            hm = WC.hue_map(res["off"], res["flag"])
            Image.fromarray(np.clip(hm * 255, 0, 255).astype(np.uint8)).save(HERE / "results" / f"woodii_{name}_hue_flag.png")
            V.montage(r, f"linear {name} / proposed", HERE / "results" / f"linear_{name}_proposed.png", scale=0.5)
    json.dump(out, open(HERE / "results" / "woodii_linear.json", "w"), indent=1)


if __name__ == "__main__":
    main()
