"""The peer's reference fit (joint MM: LTS start, B-spline tone curve + light field, anchors) with the fixed-departure
presence rule, and my two additions tested one at a time on both benches:
  +misfit : the fit's own model-error term (median over tone bins) added to the presence floor
  +res    : departure compared at chroma resolution (both sides blurred, sigma_c = 2 px)
Evaluation only; the peer's code is a read-only copy in vendor/peer."""
from __future__ import annotations
import json, sys, time
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / "vendor" / "peer")); sys.path.insert(0, str(HERE))
import cv2
import numpy as np
import sim as PS, methods as PM, bench as PB
import visualiser_proto as V
from cross_bench import my_margin, score_mine
from run_eval import WORK, SCENES
from gen_scenes import SCENARIOS as MY


def merged(p, T0=0.04, misfit=False, res=False, light=None, picks=None, sigma_c=2.0):
    bg = PM.Background().fit(p, picks, light=light)
    out = bg.apply(p)
    r = np.nan_to_num(out["resid"]).astype(np.float32)
    if res:
        ref = np.nan_to_num(out["ref"]).astype(np.float32)
        chi = p["chi"].astype(np.float32)
        bl = lambda a: np.stack([cv2.GaussianBlur(np.ascontiguousarray(a[..., k]), (0, 0), sigma_c) for k in (0, 1)], -1)
        r = bl(chi) - bl(ref)
    d = np.linalg.norm(r, axis=-1)
    sd = PM.noise_sd(bg, p)
    if misfit:
        sd = np.sqrt(sd ** 2 + bg.misfit)
    floor = np.maximum(T0, 3.0 * sd)
    S = PM.speck(d / floor, p["judge"])
    return {"V": (S > 1.0) & p["judge"], "S": S, "R": d, "misfit": float(bg.misfit)}


VARIANTS = {"peer": {}, "peer+misfit": {"misfit": True}, "peer+res": {"res": True},
            "peer+misfit+res": {"misfit": True, "res": True}}


def main(which, anchors):
    rows = {}
    rng = np.random.default_rng(0)
    if which == "mine":
        for name in MY:
            rgb8 = (V.working(V.load_srgb(str(SCENES / f"{name}.jpg")), WORK) * 255 + 0.5).astype(np.uint8)
            L, _ = V.to_lab(rgb8.astype(np.float32) / 255, 5)
            valid = V.masks(rgb8.astype(np.float32) / 255, L)["valid"]
            p = PM.prepare(rgb8, (0, 0, WORK, WORK))
            for vn, kw in VARIANTS.items():
                t = time.time()
                res = merged(p, light=my_margin() if anchors == "margin" else None, **kw)
                sc = score_mine(name, res["V"], valid)
                rows[f"{name}|{vn}|{anchors}"] = sc
                print(f"{name:20s} {vn:16s} {anchors:6s} found {sc['found']}/{sc['of']} FP {sc['FP']*100:5.1f}% "
                      f"misfit sd {np.sqrt(res['misfit']):.4f} {time.time()-t:.0f}s | "
                      + " ".join(f"{k[:6]}:{v:.2f}" for k, v in sc["per"].items() if k in ("garment", "rocket_faint", "sky", "hair")), flush=True)
    else:
        for name in PS.SCENARIOS:
            s = PS.build(name)
            p = PM.prepare(s["img"], s["box"])
            unp, border, gl, groups = PB.masks(s, p)
            for vn, kw in VARIANTS.items():
                t = time.time()
                light = PB.border_picks(s) if anchors in ("margin", "box") else None
                picks = PB.unpainted_box(s) if anchors == "box" else None
                res = merged(p, light=light, picks=picks, **kw)
                sc = PB.score(res, unp, border, gl, groups, rng)
                rows[f"{name}|{vn}|{anchors}"] = sc
                show = {k: round(v, 3) for k, v in sc.items() if isinstance(v, float) and k in ("FC", "FCbord", "AUC") or k.startswith("DET")}
                print(f"{name:16s} {vn:16s} {anchors:6s} {show} {time.time()-t:.0f}s", flush=True)
    (HERE / "results" / "cross").mkdir(parents=True, exist_ok=True)
    json.dump(rows, open(HERE / "results" / "cross" / f"merge_{which}_{anchors}.json", "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "auto")
