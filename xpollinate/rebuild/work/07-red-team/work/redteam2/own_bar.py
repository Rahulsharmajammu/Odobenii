"""Does paint raise its own bar?  Median T (and its edge term) over each painted region, for the same print with and
without paint, in the same capture geometry (A)."""
import sys, json
sys.path.insert(0, "..")
import numpy as np, cv2
import sim, evalgt
import synth_engine as E

out = {}
prU = sim.make_print(); imgU, HA = sim.capture(prU.R_unpainted, sim.UNRULY_A)
rU = E.run_capture(imgU)
for variant in ("normal", "extensive"):
    pr = sim.make_print(extensive=(variant == "extensive"))
    img, _ = sim.capture(pr.R, sim.UNRULY_A)
    r = E.run_capture(img)
    gt = evalgt.gt_in_capture(pr, HA, sim.UNRULY_A)
    row = {}
    for k in ("wash", "cheeks", "lips", "patch_yellow"):
        m = gt["core"][k] & r["F"]["usable"] & rU["F"]["usable"]
        ring = cv2.dilate(m.astype(np.uint8), np.ones((9, 9))).astype(bool) & ~cv2.erode(m.astype(np.uint8), np.ones((9, 9))).astype(bool)
        row[k] = dict(T_unpainted=float(np.median(rU["T"][m])), T_painted=float(np.median(r["T"][m])),
                      edge_T_unpainted=float(np.median(rU["T"][ring & rU["F"]["usable"]])),
                      edge_T_painted=float(np.median(r["T"][ring & r["F"]["usable"]])))
    out[variant] = dict(kappa2_unpainted=rU["kappa2"], kappa2_painted=r["kappa2"], regions=row)
    print(f"{variant}: kappa2 {rU['kappa2']:.3f} (no paint) -> {r['kappa2']:.3f} (painted)")
    for k, v in row.items():
        print(f"   {k:12s} T inside: {v['T_unpainted']:.3f} -> {v['T_painted']:.3f}   T on its rim: {v['edge_T_unpainted']:.3f} -> {v['edge_T_painted']:.3f}")
json.dump(out, open("own_bar.json", "w"), indent=1)
