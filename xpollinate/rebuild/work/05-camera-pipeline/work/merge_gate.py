"""The merged design with the paper margin as a light-only anchor, gated by a held-out side: fit with the margin's
left side withheld; if the withheld side's departure from the fitted reference is under T0/2, refit with the whole
margin; otherwise fit without it (automatic) and say so.  Departure at chroma resolution, fixed threshold, no
model-error term.  Evaluation only."""
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


def present(p, bg, out, T0=0.04, sigma_c=2.0):
    ref = np.nan_to_num(out["ref"]).astype(np.float32)
    chi = p["chi"].astype(np.float32)
    bl = lambda a: np.stack([cv2.GaussianBlur(np.ascontiguousarray(a[..., k]), (0, 0), sigma_c) for k in (0, 1)], -1)
    r = bl(chi) - bl(ref)
    d = np.linalg.norm(r, axis=-1)
    floor = np.maximum(T0, 3.0 * PM.noise_sd(bg, p))
    S = PM.speck(d / floor, p["judge"])
    return {"V": (S > 1.0) & p["judge"], "S": S, "R": d}


def gated(p, margin, picks=None, T0=0.04):
    h, w = margin.shape
    xs = np.nonzero(margin.any(axis=0))[0]
    left = np.zeros_like(margin)
    left[:, : xs.min() + (xs.max() - xs.min()) // 8] = True
    held = margin & left
    bg = PM.Background().fit(p, picks, light=margin & ~held)
    out = bg.apply(p)
    miss = float(np.linalg.norm(np.median(np.nan_to_num(out["resid"])[held & p["judge"]], axis=0)))
    if miss < T0 / 2:
        bg = PM.Background().fit(p, picks, light=margin)
        note = f"margin used (held-out side off by {miss:.3f})"
    else:
        bg = PM.Background().fit(p, picks)
        note = f"margin refused (held-out side off by {miss:.3f})"
    out = bg.apply(p)
    res = present(p, bg, out, T0)
    res["note"] = note
    return res


def main(which):
    rows = {}
    rng = np.random.default_rng(0)
    if which == "mine":
        for name in MY:
            rgb8 = (V.working(V.load_srgb(str(SCENES / f"{name}.jpg")), WORK) * 255 + 0.5).astype(np.uint8)
            L, _ = V.to_lab(rgb8.astype(np.float32) / 255, 5)
            valid = V.masks(rgb8.astype(np.float32) / 255, L)["valid"]
            p = PM.prepare(rgb8, (0, 0, WORK, WORK))
            t = time.time()
            res = gated(p, my_margin())
            sc = score_mine(name, res["V"], valid)
            rows[name] = {**sc, "note": res["note"]}
            print(f"{name:20s} gated margin  found {sc['found']}/{sc['of']} FP {sc['FP']*100:5.1f}% {time.time()-t:.0f}s | {res['note']} | "
                  + " ".join(f"{k[:6]}:{v:.2f}" for k, v in sc["per"].items() if k in ("garment", "rocket_faint", "sky", "hair")), flush=True)
    else:
        for name in PS.SCENARIOS:
            s = PS.build(name)
            p = PM.prepare(s["img"], s["box"])
            unp, border, gl, groups = PB.masks(s, p)
            for lab, picks in (("margin", None), ("margin+box", PB.unpainted_box(s))):
                t = time.time()
                res = gated(p, PB.border_picks(s), picks=picks)
                sc = PB.score(res, unp, border, gl, groups, rng)
                rows[f"{name}|{lab}"] = {**sc, "note": res["note"]}
                show = {k: round(v, 3) for k, v in sc.items() if isinstance(v, float) and (k in ("FC", "FCbord", "AUC") or k.startswith("DET"))}
                print(f"{name:16s} gated {lab:11s} {show} {time.time()-t:.0f}s | {res['note']}", flush=True)
    json.dump(rows, open(HERE / "results" / "cross" / f"gate_{which}.json", "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1])
