"""Can any threshold on the departure separate the faint wash (or the cheeks) from unpainted print?  ROC AUC of
|departure| (TODO's reference from good picks), painted core vs unpainted, per capture.  Analysis only."""
import json, numpy as np, cv2
from sklearn.metrics import roc_auc_score
import sim, evalgt, picks, todo_pipeline as T

out = {}
pr = sim.make_print()
for nm, cap in (("clean", sim.CLEAN), ("A", sim.UNRULY_A), ("B", sim.UNRULY_B)):
    img, Hm = sim.capture(pr.R, cap)
    gt = evalgt.gt_in_capture(pr, Hm, cap)
    res = T.run(img, picks.to_capture(picks.GOOD, Hm))
    mag = np.hypot(res["va"], res["vb"]); u = res["usable"]
    neg = mag[gt["unpainted"] & u]
    row = {"unpainted_median": float(np.median(neg)), "unpainted_p90": float(np.percentile(neg, 90)),
           "unpainted_p99": float(np.percentile(neg, 99))}
    for k in ("wash", "cheeks", "flag_blue"):
        pos = mag[gt["core"][k] & u]
        y = np.r_[np.ones(len(pos)), np.zeros(len(neg))]
        row[k + "_median"] = float(np.median(pos))
        row[k + "_auc"] = float(roc_auc_score(y, np.r_[pos, neg]))
        # share of unpainted pixels at least as far from the reference as the median wash pixel
        row[k + "_unpainted_beyond_median"] = float((neg >= np.median(pos)).mean())
    out[nm] = row
    print(nm, {k: round(v, 3) for k, v in row.items()})
json.dump(out, open("out/separability.json", "w"), indent=1)
