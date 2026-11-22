"""'Seen in both' on this bench: two deliberately different captures of the same print, each with its own automatic
reference, a departure kept only where both captures depart, in the same direction.  Also: the same smoothing on L*
as on a*, b* (the red team's finding), linear opacity 2 -> 6 units ('shown' = opacity >= 0.25, i.e. z >= 3), lateral
colour fringing (CA) with the same or the opposite sign in the two captures, and registration by SIFT + RANSAC.

Developer's numbers only.  Synthetic: checks code, not method.
"""
from __future__ import annotations

import csv
import math
import sys
import time
from dataclasses import replace
from pathlib import Path

import cv2
import numpy as np

import methods as M
import synth as S

OUT = Path(__file__).resolve().parent

MIX = dict(cast_left=(1.0, 0.88, 0.70), cast_right=(0.90, 0.98, 1.10), gradient=0.2, saturation=1.25, jpeg_q=80)
MIX_REV = dict(cast_left=(0.90, 0.98, 1.10), cast_right=(1.0, 0.88, 0.70), gradient=-0.2, saturation=1.15,
               contrast=0.30, jpeg_q=85)
PHONE = dict(cast_left=(1.0, 0.92, 0.78), cast_right=(1.0, 0.92, 0.78), saturation=1.25, jpeg_q=80)
CLEAN = dict(falloff=0.10, gradient=0.0, saturation=1.0, contrast=0.2, jpeg_q=92)

FULL = {"face": ("skin", 1.0), "hands": ("skin", 1.0), "lips": ("red", 1.0), "backdrop": ("blue", 0.5),
        "plant": ("green", 0.8), "pin": ("gold", 1.0)}
SKY = {"topthird": ("blue", 0.6), "lips": ("red", 1.0)}
LIGHTBAND = {"lightband": ("pink", 1.2)}
SHEET80 = {"backdrop": ("blue", 0.5), "floor": ("blue", 0.5), "suit": ("blue", 0.6), "plant": ("blue", 0.5),
           "tie": ("blue", 0.5)}                       # ~80% of the picture washed; face, hands, shirt, hair bare

GEOM_B = dict(angle=4.0, scale=0.95, tx=18.0, ty=-12.0)
CA = 0.0012                                            # radial scale of R (+) and B (-) about the centre


def lateral_ca(R, k):
    if not k:
        return R
    H, W = R.shape[:2]
    cy, cx = (H - 1) / 2, (W - 1) / 2
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    out = R.copy()
    for c, s in ((0, 1 + k), (2, 1 - k)):
        mx = (cx + (xx - cx) / s).astype(np.float32)
        my = (cy + (yy - cy) / s).astype(np.float32)
        out[..., c] = cv2.remap(R[..., c], mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return out


def affine(shape, angle, scale, tx, ty):
    H, W = shape
    A = cv2.getRotationMatrix2D(((W - 1) / 2, (H - 1) / 2), angle, scale)
    A[:, 2] += (tx, ty)
    return A


def warp_scene(R, A, fill):
    H, W = R.shape[:2]
    return cv2.warpAffine(R, A, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                          borderValue=tuple(float(v) for v in fill))


def register(rgbA, rgbB):
    """Homography taking B onto A: SIFT on grey, ratio test, RANSAC.  Returns (H, inliers, rms)."""
    ga = cv2.cvtColor((np.clip(rgbA, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
    gb = cv2.cvtColor((np.clip(rgbB, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
    sift = cv2.SIFT_create(nfeatures=4000)
    ka, da = sift.detectAndCompute(ga, None)
    kb, db = sift.detectAndCompute(gb, None)
    m = cv2.BFMatcher(cv2.NORM_L2).knnMatch(db, da, k=2)
    good = [p[0] for p in m if len(p) == 2 and p[0].distance < 0.75 * p[1].distance]
    src = np.float32([kb[g.queryIdx].pt for g in good])
    dst = np.float32([ka[g.trainIdx].pt for g in good])
    Hm, inl = cv2.findHomography(src, dst, cv2.RANSAC, 2.0)
    inl = inl.ravel().astype(bool)
    proj = cv2.perspectiveTransform(src[inl][None], Hm)[0]
    rms = float(np.sqrt(np.mean(np.sum((proj - dst[inl]) ** 2, axis=1))))
    return Hm, int(inl.sum()), rms


def lin_opacity(z, lo=2.0, hi=6.0):
    return np.clip((z - lo) / (hi - lo), 0, 1)


def prep_all(rgb):
    """The red team's change: the same 5 px median on L* as on a*, b*."""
    p = M.prep(rgb)
    p.L = cv2.medianBlur(np.ascontiguousarray(p.L, np.float32), 5)
    return p


def make_pair(recipe, tone, paper, capA, capB, seed, caA=CA, caB=-CA, geom=GEOM_B, mirroring=0.0,
              glareB_at=(0.65, 0.30)):
    sc = S.portrait_scene(seed=seed)
    if recipe:
        pod, amount = S.paint_layers(sc, recipe)
    else:
        pod, amount = None, np.zeros(sc.D.shape, np.float32)
    R = S.reflectance(sc, tone, paper, pod, mirroring, seed)
    R0 = S.reflectance(sc, tone, paper, None, mirroring, seed)
    A_ = affine(sc.D.shape, **geom)
    RA, R0A = lateral_ca(R, caA), lateral_ca(R0, caA)
    RB = lateral_ca(warp_scene(R, A_, S.MOUNT), caB)
    R0B = lateral_ca(warp_scene(R0, A_, S.MOUNT), caB)
    cA = S.Capture(seed=seed * 10 + 1, **capA)
    cB = S.Capture(seed=seed * 10 + 2, glare_at=glareB_at, **capB)
    rgbA, wbA, cleanA = S.capture(RA, cA)
    twinA, _, cleanTA = S.capture(R0A, cA, wb_gains=wbA, noise_seed=cA.seed)
    rgbB, _, _ = S.capture(RB, cB)
    boxB = warp_scene((~sc.mount).astype(np.float32)[..., None].repeat(3, 2), A_, (0, 0, 0))[..., 0] > 0.5
    return sc, amount, rgbA, cleanA, cleanTA, rgbB, boxB


def departures(p, box, ring=True):
    r = M.m3_proposed(p, mask=box, ring_plane=ring, diagnostics=False)
    return r


def evaluate(name, recipe, tone, paper, capA, capB, seed, caA=CA, caB=-CA, mirroring=0.0, glare=0.0, taus=(1.5, 2.0)):
    capA = dict(capA, glare=glare) if glare else capA
    capB = dict(capB, glare=glare) if glare else capB
    sc, amount, rgbA, cleanA, cleanTA, rgbB, boxB = make_pair(recipe, tone, paper, capA, capB, seed, caA, caB,
                                                              mirroring=mirroring)
    boxA = ~sc.mount
    # truth in A's frame
    _, a1, b1 = M.to_lab(cleanA)
    _, a0, b0 = M.to_lab(cleanTA)
    visible = (amount > 0.02) & (np.hypot(a1 - a0, b1 - b0) >= 2.0)
    unpainted = (amount <= 0.02) & boxA
    # each capture on its own
    pA, pB = prep_all(rgbA), prep_all(rgbB)
    rA, rB = departures(pA, boxA), departures(pB, boxB)
    Hm, ninl, rms = register(rgbA, rgbB)
    H_, W_ = rgbA.shape[:2]

    def toA(x, interp=cv2.INTER_LINEAR):
        return cv2.warpPerspective(np.ascontiguousarray(x, np.float32), Hm, (W_, H_), flags=interp,
                                   borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    zB = toA(rB.z)
    vaB, vbB = toA(rB.va), toA(rB.vb)
    useB = toA((pB.usable & boxB).astype(np.float32), cv2.INTER_NEAREST) > 0.5
    ev = pA.usable & boxA & useB
    out = []

    def score(label, shown):
        fp = float((shown & unpainted & ev).sum() / max((unpainted & ev).sum(), 1))
        tp = float((shown & visible & ev).sum() / max((visible & ev).sum(), 1)) if visible.any() else float("nan")
        reg = {}
        for rg in ("face", "lips", "backdrop", "topthird", "lightband", "suit", "floor", "plant", "pin"):
            m = sc.regions.get(rg)
            if m is None:
                m = S.REGION_FNS[rg](sc) if rg in S.REGION_FNS else None
            if m is None:
                continue
            vm = visible & (m > 0.5) & ev
            if vm.sum() > 30:
                reg[rg] = float((shown & vm).sum() / vm.sum())
        um = unpainted & ev & (sc.regions["face"] > 0.5)
        if um.sum() > 30:
            reg["bare face"] = float((shown & um).sum() / um.sum())
        out.append({"case": name, "view": label, "false_presence": round(fp, 4),
                    "paint_shown": None if math.isnan(tp) else round(tp, 3),
                    "regions": "; ".join(f"{k} {v:.2f}" for k, v in reg.items()),
                    "registration": f"{ninl} inliers, rms {rms:.2f} px"})
        print(f"{name[:40]:40s} | {label:26s} | FP {fp:6.3f} | TP {tp:5.2f} | {out[-1]['regions'][:90]}", flush=True)

    shownA = lin_opacity(rA.z) >= 0.25
    shownB = lin_opacity(zB) >= 0.25
    score("A alone", shownA)
    score("B alone (registered)", shownB & useB)
    cosang = (rA.va * vaB + rA.vb * vbB) / np.maximum(np.hypot(rA.va, rA.vb) * np.hypot(vaB, vbB), 1e-6)
    same_dir = cosang >= math.cos(math.radians(60))
    for tau in taus:
        both = (rA.z >= tau) & (zB >= tau) & same_dir & useB
        score(f"seen in both (z>={tau:g} each)", both & (lin_opacity(np.minimum(rA.z, zB)) >= 0.25 if tau < 3 else both))
    return out, (rgbA, rgbB, rA, zB, vaB, vbB, useB, Hm)


CASES = [
    # name, recipe, tone, paper, capA, capB, extra
    ("N2 warm print: phone | mixed light", None, "warm", "yellowed", PHONE, MIX_REV, {}),
    ("N3 split print: no WB | mixed light", None, "split", "yellowed",
     dict(cast_left=(1.0, 0.90, 0.72), cast_right=(1.0, 0.90, 0.72), awb="none", saturation=1.2, jpeg_q=75), MIX_REV, {}),
    ("N4 warm print: mixed | mixed reversed", None, "warm", "yellowed", MIX, MIX_REV, {}),
    ("N5 split, glare, mirroring: mixed | rev", None, "split", "white", MIX, MIX_REV, {"mirroring": 0.02, "glare": 0.6}),
    ("N4s same-sign fringing (shared lens)", None, "warm", "yellowed", MIX, MIX_REV, {"caB": CA}),
    ("P1 portrait painted: phone | mixed rev", FULL, "warm", "yellowed", PHONE, MIX_REV, {}),
    ("P3 portrait, split: mixed | mixed rev", FULL, "split", "yellowed", MIX, MIX_REV, {}),
    ("P4 sky: phone | mixed rev", SKY, "warm", "yellowed", PHONE, MIX_REV, {}),
    ("P5 sky: mixed | mixed rev", SKY, "warm", "yellowed", MIX, MIX_REV, {}),
    ("P6 light-grey wash: phone | mixed rev", LIGHTBAND, "warm", "white", PHONE, MIX_REV, {}),
    ("P8 wash over ~80%: phone | mixed rev", SHEET80, "warm", "yellowed", PHONE, MIX_REV, {}),
]


if __name__ == "__main__":
    sel = sys.argv[1:]
    rows = []
    t0 = time.time()
    for i, (name, recipe, tone, paper, cA, cB, extra) in enumerate(CASES):
        if sel and not any(name.startswith(s) for s in sel):
            continue
        r, _ = evaluate(name, recipe, tone, paper, cA, cB, seed=i, **extra)
        rows.extend(r)
    with open(OUT / "pairs_results.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"done in {time.time() - t0:.0f} s")
