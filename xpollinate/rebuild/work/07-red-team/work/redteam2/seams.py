"""Seam checks of the synthesis's engine on the red team's bench.  Scores are shares of pixels shown at C opacity >= 0.25
(and >= 0.5), against ground truth in capture A's geometry.  Analysis only."""
import sys, json, time
sys.path.insert(0, "..")
import numpy as np, cv2
import sim, evalgt, picks, honest as Hn
import synth_engine as E

def gt_for(pr, Hm, cap, variant):
    gt = evalgt.gt_in_capture(pr, Hm, cap)
    if variant == "unpainted":
        gt["unpainted"] = ~gt["glare"] & ~cv2.dilate((gt["foxing"] | gt["mat_burn"]).astype(np.uint8), np.ones((13, 13))).astype(bool)
        gt["core"] = {k: np.zeros_like(m) for k, m in gt["core"].items()}
    return gt

KEYS = ("unpainted_shown", "wash", "cheeks", "lips", "patch_yellow", "foxing", "mat_burn")
def fmt(s): return "  ".join(f"{k}={100*s[k]:5.1f}%" if s.get(k) == s.get(k) else f"{k}=  n/a" for k in KEYS)

def capture(variant, cap):
    pr = sim.make_print(extensive=(variant == "extensive"))
    R = pr.R_unpainted if variant == "unpainted" else pr.R
    img, Hm = sim.capture(R, cap)
    return pr, img, Hm

def pair(rA, imgA, rB, imgB, gate):
    Hba, _ = Hn.register(imgB, imgA)
    w = lambda m, i=cv2.INTER_LINEAR: cv2.warpPerspective(m.astype(np.float32), Hba, (sim.P, sim.P), flags=i, borderValue=0)
    vB = np.stack([w(rB["v"][..., 0]), w(rB["v"][..., 1])], -1); dnB = w(rB["dn"]); uB = w(rB["F"]["usable"], cv2.INTER_NEAREST) > 0.5
    uA = rA["F"]["usable"]
    vA, dnA = rA["v"], rA["dn"]
    cos = (vA * vB).sum(-1) / (np.linalg.norm(vA, axis=-1) * np.linalg.norm(vB, axis=-1) + 1e-9)
    both = uA & uB
    keep = both & (dnA >= gate) & (dnB >= gate) & (cos >= 0.5)
    op = E.ramp(np.minimum(dnA, dnB)) * keep
    return op, both

out = {}
t0 = time.time()
for variant in ("unpainted", "normal", "extensive"):
    prA, imgA, HA = capture(variant, sim.UNRULY_A)
    prB, imgB, HB = capture(variant, sim.UNRULY_B)
    gtA = gt_for(prA, HA, sim.UNRULY_A, variant)
    boxesA = picks.to_capture(picks.GOOD, HA)
    rA = E.run_capture(imgA); rB = E.run_capture(imgB)
    rAb = E.run_capture(imgA, boxesA)
    res = {}
    # one photograph, automatic (C is NOT drawn under the synthesis's rule; shown for reference)
    res["one photo, automatic (not drawn)"] = (E.ramp(rA["dn"]), rA["F"]["usable"])
    # the boxes route: one photograph + examined boxes -> C drawn
    res["one photo + 5 examined boxes (C drawn)"] = (E.ramp(rAb["dn"]), rAb["F"]["usable"])
    # the witness route, as written: both exceed T, directions within 60 degrees
    res["two photos A+B, gate at T (as written)"] = pair(rA, imgA, rB, imgB, 1.0)
    # the same with the gate at T/2, where the ramp starts
    res["two photos A+B, gate at T/2"] = pair(rA, imgA, rB, imgB, 0.5)
    for name, (op, usable) in res.items():
        s25 = evalgt.score(op, usable, gtA, thr=0.25); s50 = evalgt.score(op, usable, gtA, thr=0.5)
        out[f"{variant} | {name}"] = {"op>=.25": s25, "op>=.5": s50}
        print(f"{variant:9s} | {name:40s} | op>=.25: {fmt(s25)}", flush=True)
    print(f"           kappa2 A {rA['kappa2']:.4g}, A+boxes {rAb['kappa2']:.4g}; votes {rA['nvotes']}; Tukey inlier share {rA['ref'].inlier_share:.2f}; median T {np.median(rA['T'][rA['F']['usable']]):.3f}  [{time.time()-t0:.0f}s]", flush=True)
json.dump(out, open("seams.json", "w"), indent=1)
