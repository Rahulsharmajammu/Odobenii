"""Smallest fix for the boxes route: floor T by the boxes' leave-one-box-out disagreement (examined-unpainted boxes,
so paint cannot move it), as the red team's original unit did.  Unpainted print (the session control) and painted print,
capture A, five good boxes."""
import sys
sys.path.insert(0, "..")
import numpy as np, cv2
import sim, evalgt, picks
import synth_engine as E

def loo_scale(img, boxes):
    F = E.features(img); H, W = F["L"].shape
    V = E.votes(F, boxes)
    isbox = V[:, 6] > 0
    # identify which box each box-vote came from by recomputing per box
    res = []
    for j in range(len(boxes)):
        Vj = E.votes(F, [boxes[j]])
        Vj = Vj[Vj[:, 6] > 0]
        others = [b for i, b in enumerate(boxes) if i != j]
        ref = E.Reference(E.votes(F, others), W, H)
        A = ref._design(Vj[:, 0], Vj[:, 3], Vj[:, 4])
        r = Vj[:, 1:3] - A @ ref.coef
        res.append(np.median(r, axis=0))
    mags = np.linalg.norm(np.array(res), axis=1)
    return float(np.sqrt(np.median(mags ** 2))), mags

for variant in ("unpainted", "normal"):
    pr = sim.make_print()
    R = pr.R_unpainted if variant == "unpainted" else pr.R
    img, Hm = sim.capture(R, sim.UNRULY_A)
    gt = evalgt.gt_in_capture(pr, Hm, sim.UNRULY_A)
    if variant == "unpainted":
        gt["unpainted"] = ~gt["glare"] & ~cv2.dilate((gt["foxing"] | gt["mat_burn"]).astype(np.uint8), np.ones((13, 13))).astype(bool)
        gt["core"] = {k: np.zeros_like(m) for k, m in gt["core"].items()}
    boxes = picks.to_capture(picks.GOOD, Hm)
    r = E.run_capture(img, boxes)
    s_sys, mags = loo_scale(img, boxes)
    d = r["dn"] * r["T"]
    for k in (2.0, 3.0):
        Tfix = np.maximum(r["T"], k * s_sys)
        op = E.ramp(d / Tfix)
        s = evalgt.score(op, r["F"]["usable"], gt, thr=0.25)
        print(f"{variant:9s} s_LOO={s_sys:.3f} (box residuals {np.round(mags,3).tolist()}), T floor {k}*s_LOO: unpainted {100*s['unpainted_shown']:.1f}%  wash {100*s.get('wash',np.nan):.1f}%  cheeks {100*s.get('cheeks',np.nan):.1f}%  lips {100*s.get('lips',np.nan):.1f}%")
