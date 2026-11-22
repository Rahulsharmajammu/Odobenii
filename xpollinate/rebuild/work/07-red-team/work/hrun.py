"""Helpers shared by the alternative-design runs (no work at import)."""
import numpy as np, cv2
import sim, evalgt, picks, honest as Hn


def gt_for(pr, Hm, cap, variant):
    gt = evalgt.gt_in_capture(pr, Hm, cap)
    if variant == "unpainted":
        gt["unpainted"] = ~gt["glare"] & ~cv2.dilate((gt["foxing"] | gt["mat_burn"]).astype(np.uint8), np.ones((13, 13))).astype(bool)
        gt["core"] = {k: np.zeros_like(m) for k, m in gt["core"].items()}
    return gt


def single(variant, cap, pickset):
    pr = sim.make_print(extensive=(variant == "extensive"))
    R = pr.R_unpainted if variant == "unpainted" else pr.R
    img, Hm = sim.capture(R, cap)
    lab, usable = Hn.prepare(img)
    boxes = picks.to_capture(pickset, Hm)
    ref = Hn.Reference(lab, usable, boxes)
    d = Hn.departure(lab, usable, ref)
    op = Hn.ramp(d["z"]); op[d["uncovered"]] = 0
    words = Hn.tripwires(lab, usable, d, ref, op >= 0.25)
    return dict(pr=pr, img=img, Hm=Hm, lab=lab, usable=usable, ref=ref, d=d, op=op, words=words, boxes=boxes,
                gt=gt_for(pr, Hm, cap, variant))


def pair(rA, rB):
    Hba, ninl = Hn.register(rB["img"], rA["img"])
    w = lambda m, i=cv2.INTER_LINEAR: cv2.warpPerspective(m.astype(np.float32), Hba, (sim.P, sim.P), flags=i, borderValue=0)
    dBw = {k: w(rB["d"][k]) for k in ("va", "vb", "z")}
    uB = w(rB["usable"] & ~rB["d"]["uncovered"], cv2.INTER_NEAREST) > 0.5
    uA = rA["usable"] & ~rA["d"]["uncovered"]
    keep, one, zm = Hn.persistent(rA["d"], uA, dBw, uB)
    op = Hn.ramp(zm, 1.5, 5.0) * keep
    return dict(keep=keep, one=one, op=op, uA=uA, uB=uB, Hba=Hba, ninl=ninl)
