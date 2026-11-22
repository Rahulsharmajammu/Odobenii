"""Run every background model on every synthetic capture and score it against the truth.

Scores (all on the image area, pixels that are judgeable for every method: not clipped, not near black):
  FC      share of unpainted pixels (6 px away from any paint, outside the glare) shown as paint
  FCbord  the same on the paper border (an unpainted margin: a negative control)
  FCglare the same inside the glare patch
  DET:g   share of painted pixels (4 px inside the paint) shown as paint, by paint group
  AUC     threshold-free separability of painted from unpainted pixels by the method's statistic
These scores are for choosing a method; the tool itself reports none of them.
"""
from __future__ import annotations

import json
import sys
import time

import cv2
import numpy as np
from sklearn.metrics import roc_auc_score

import methods as M
import sim


def masks(s, p):
    j = p["judge"]
    k = lambda n: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * n + 1, 2 * n + 1))
    near_paint = cv2.dilate(s["paint_any"].astype(np.uint8), k(6)).astype(bool)
    glare = s["glare"] > 0.03
    unp = s["image_area"] & j & ~near_paint & ~glare
    border = cv2.erode(s["border"].astype(np.uint8), k(6)).astype(bool) & j
    gl = glare & s["image_area"] & j & ~near_paint
    groups = {}
    for name, (m, grp) in s["truth"].items():
        core = cv2.erode(m.astype(np.uint8), k(4)).astype(bool) & j & s["image_area"]
        groups.setdefault(grp, np.zeros_like(core))
        groups[grp] |= core
    return unp, border, gl, groups


def score(res, unp, border, gl, groups, rng):
    V, S = res["V"], res["S"]
    out = {"FC": float(V[unp].mean()), "FCbord": float(V[border].mean()) if border.any() else None,
           "FCglare": float(V[gl].mean()) if gl.any() else None}
    allp = np.zeros_like(unp)
    for g, m in groups.items():
        out[f"DET:{g}"] = float(V[m].mean()) if m.any() else None
        allp |= m
    if allp.any():
        neg = S[unp]
        pos = S[allp]
        neg = neg[rng.choice(len(neg), min(60000, len(neg)), replace=False)]
        pos = pos[rng.choice(len(pos), min(60000, len(pos)), replace=False)]
        out["AUC"] = float(roc_auc_score(np.r_[np.zeros(len(neg)), np.ones(len(pos))], np.r_[neg, pos]))
        R = res.get("R")
        if R is not None:
            rn, rp = R[unp], R[allp]
            rn = rn[rng.choice(len(rn), min(60000, len(rn)), replace=False)]
            rp = rp[rng.choice(len(rp), min(60000, len(rp)), replace=False)]
            out["AUC_R"] = float(roc_auc_score(np.r_[np.zeros(len(rn)), np.ones(len(rp))], np.r_[rn, rp]))
            for g, m in groups.items():   # painted share above the unpainted's 99th percentile of |r|
                out[f"R99:{g}"] = float((R[m] > np.percentile(R[unp], 99)).mean()) if m.any() else None
    return out


def border_picks(s):
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17))
    return cv2.erode(s["border"].astype(np.uint8), k).astype(bool)


def unpainted_box(s):
    """What an operator would box as unpainted mid-tone: the largest unpainted part of the suit or backdrop."""
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))
    near = cv2.dilate(s["paint_any"].astype(np.uint8), k).astype(bool)
    out = np.zeros_like(near)
    for reg in ("suit", "backdrop"):
        m = s["regions"][reg] & ~near & s["image_area"] & (s["glare"] < 0.01)
        if m.sum() > 20000:
            ys, xs = np.nonzero(m)
            cy, cx = int(np.median(ys)), int(np.median(xs))
            box = np.zeros_like(m)
            box[cy - 60:cy + 60, cx - 60:cx + 60] = True
            out |= box & m
    return out


RUNS = {
    "M1 v3 C* floor": lambda p, s: M.m1_v3(p),
    "M2 v4.1 LRC": lambda p, s: M.m2_lrc(p),
    "M3 TODO auto": lambda p, s: M.m3_todo(p),
    "M3p TODO auto+plane": lambda p, s: M.m3_todo(p, plane=True),
    "M4 Woodii axis auto": lambda p, s: M.m4_woodii(p),
    "M5 global RX": lambda p, s: M.m5_grx(p),
    "M6 local RX": lambda p, s: M.m6_lrx(p),
    "M7 proposal auto": lambda p, s: M.m7_prop(p),
    "M7 + margin": lambda p, s: M.m7_prop(p, light=border_picks(s)),
    "M7 + margin + unpainted box": lambda p, s: M.m7_prop(p, light=border_picks(s), picks=unpainted_box(s)),
    "M7 in CIELAB": lambda p, s: M.m7_prop(p, space="lab"),
    "M7 no edge guard": lambda p, s: M.m7_prop(p, edge=False),
    "M7flex auto": lambda p, s: M.m7_prop(p, knots=8, xy_deg=4),
    "M7F fixed auto": lambda p, s: M.m7_fixed(p),
    "M7F fixed + margin": lambda p, s: M.m7_fixed(p, light=border_picks(s)),
    "M7F fixed + margin + box": lambda p, s: M.m7_fixed(p, light=border_picks(s), picks=unpainted_box(s)),
    "M3 TODO + picks": lambda p, s: M.m3_todo(p, picks=border_picks(s) | unpainted_box(s)),
    "M4 Woodii + picks": lambda p, s: M.m4_woodii(p, picks=border_picks(s) | unpainted_box(s)),
}


def main(scenarios, runs, out_json):
    rng = np.random.default_rng(0)
    table = {}
    for name in scenarios:
        s = sim.build(name)
        p = M.prepare(s["img"], s["box"])
        unp, border, gl, groups = masks(s, p)
        for rn in runs:
            t0 = time.time()
            try:
                res = RUNS[rn](p, s)
                sc = score(res, unp, border, gl, groups, rng)
                sc["note"] = res.get("note", "")
                if "V3" in res:
                    sc["FC@3"] = float(res["V3"][unp].mean())
                    for g, m in groups.items():
                        sc[f"DET@3:{g}"] = float(res["V3"][m].mean()) if m.any() else None
            except Exception as exc:  # keep going; record the failure
                sc = {"error": f"{type(exc).__name__}: {exc}"}
            sc["secs"] = round(time.time() - t0, 1)
            table.setdefault(name, {})[rn] = sc
            show = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in sc.items()}
            print(name, "|", rn, "|", show, flush=True)
    with open(out_json, "w") as f:
        json.dump(table, f, indent=1)


if __name__ == "__main__":
    sc = sys.argv[1].split(",") if len(sys.argv) > 1 and sys.argv[1] != "all" else list(sim.SCENARIOS)
    rn = sys.argv[2].split(",") if len(sys.argv) > 2 and sys.argv[2] != "all" else list(RUNS)
    main(sc, rn, sys.argv[3] if len(sys.argv) > 3 else "bench.json")
