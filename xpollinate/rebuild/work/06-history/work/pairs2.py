"""Single capture vs 'Seen in both', with the v2 unit and judgement rules (v2.py).  Developer's numbers only."""
from __future__ import annotations

import csv
import math
import sys
import time
from pathlib import Path

import cv2
import numpy as np

import methods as M
import pairs as P
import synth as S
import v2

OUT = Path(__file__).resolve().parent


def evaluate2(name, recipe, tone, paper, capA, capB, seed, caA=P.CA, caB=-P.CA, mirroring=0.0, glare=0.0,
              tau=1.5, keep=None):
    capA = dict(capA, glare=glare) if glare else capA
    capB = dict(capB, glare=glare) if glare else capB
    sc, amount, rgbA, cleanA, cleanTA, rgbB, boxB = P.make_pair(recipe, tone, paper, capA, capB, seed, caA, caB,
                                                                mirroring=mirroring)
    boxA = ~sc.mount
    _, a1, b1 = M.to_lab(cleanA)
    _, a0, b0 = M.to_lab(cleanTA)
    visible = (amount > 0.02) & (np.hypot(a1 - a0, b1 - b0) >= 2.0)
    unpainted = (amount <= 0.02) & boxA
    pA, pB = P.prep_all(rgbA), P.prep_all(rgbB)
    rA = M.m3_proposed(pA, mask=boxA, ring_plane=True, diagnostics=False)
    rB = M.m3_proposed(pB, mask=boxB, ring_plane=True, diagnostics=False)
    zA, jA, gA, xA = v2.judge(pA, rA, boxA)
    zB_, jB_, gB_, xB_ = v2.judge(pB, rB, boxB)
    Hm, ninl, rms = P.register(rgbA, rgbB)
    H_, W_ = rgbA.shape[:2]

    def toA(x, interp=cv2.INTER_LINEAR):
        return cv2.warpPerspective(np.ascontiguousarray(x, np.float32), Hm, (W_, H_), flags=interp,
                                   borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    zB = toA(zB_)
    vaB, vbB = toA(rB.va), toA(rB.vb)
    jB = toA(jB_.astype(np.float32), cv2.INTER_NEAREST) > 0.5
    gB = toA(gB_.astype(np.float32), cv2.INTER_NEAREST) > 0.5
    # evaluate on print pixels usable in both captures, excluding the paper border (reference, not judged)
    paperA = rA.info.get("anchor_mask")
    ev = pA.usable & boxA & (toA((pB.usable & boxB).astype(np.float32), cv2.INTER_NEAREST) > 0.5) & ~paperA
    rows = []

    def score(label, shown, judged):
        fp = float((shown & unpainted & ev).sum() / max((unpainted & ev).sum(), 1))
        tp = float((shown & visible & ev).sum() / max((visible & ev).sum(), 1)) if visible.any() else float("nan")
        notj = float((~judged & ev).sum() / max(ev.sum(), 1))
        reg = {}
        for rg in ("face", "lips", "backdrop", "topthird", "lightband", "suit", "floor", "plant"):
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
        rows.append({"case": name, "view": label, "false_presence": round(fp, 4),
                     "paint_shown": None if math.isnan(tp) else round(tp, 3), "not_judged": round(notj, 3),
                     "regions": "; ".join(f"{k} {v:.2f}" for k, v in reg.items()),
                     "registration": f"{ninl} inliers, rms {rms:.2f} px"})
        print(f"{name[:40]:40s} | {label:30s} | FP {fp:6.3f} | TP {tp:5.2f} | not judged {notj:4.2f} | "
              f"{rows[-1]['regions'][:80]}", flush=True)

    # v1 rule (band spread, everything in the print judged), for comparison
    score("A alone, v1 unit", (P.lin_opacity(rA.z) >= 0.25) & boxA, boxA)
    score("A alone, v2 unit", (P.lin_opacity(zA) >= 0.25) & jA, jA)
    cos = (rA.va * vaB + rA.vb * vbB) / np.maximum(np.hypot(rA.va, rA.vb) * np.hypot(vaB, vbB), 1e-6)
    both = jA & jB & (zA >= tau) & (zB >= tau) & (cos >= math.cos(math.radians(60)))
    both_shown = both & (P.lin_opacity(np.minimum(zA, zB)) >= 0.25)
    score("seen in both, v2 unit", both_shown, jA & jB)
    if keep is not None:
        keep.update(dict(rgbA=rgbA, rgbB=rgbB, rA=rA, zA=zA, zB=zB, vaB=vaB, vbB=vbB, jA=jA, jB=jB, gA=gA,
                         both=both_shown, Hm=Hm, pA=pA, visible=visible, unpainted=unpainted, sc=sc))
    return rows


if __name__ == "__main__":
    sel = sys.argv[1:]
    rows = []
    t0 = time.time()
    for i, (name, recipe, tone, paper, cA, cB, extra) in enumerate(P.CASES):
        if sel and not any(name.startswith(s) for s in sel):
            continue
        rows.extend(evaluate2(name, recipe, tone, paper, cA, cB, seed=i, **extra))
    with open(OUT / "pairs2_results.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"done in {time.time() - t0:.0f} s")
