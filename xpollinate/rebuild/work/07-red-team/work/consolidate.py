"""One visibility threshold for every pipeline: v4.x alpha >= 0.2 (half its faint tier); TODO and alternative
opacity >= 0.25.  Prints the tables used in the report."""
import json, numpy as np, cv2
import sim, evalgt, picks, todo_pipeline as T
import run_v412 as V            # its module code only defines helpers when imported

rows = {}
def gtv(pr, Hm, cap, variant):
    gt = evalgt.gt_in_capture(pr, Hm, cap)
    if variant == "unpainted":
        gt["unpainted"] = ~gt["glare"] & ~cv2.dilate((gt["foxing"] | gt["mat_burn"]).astype(np.uint8), np.ones((13, 13))).astype(bool)
        gt["core"] = {k: np.zeros_like(m) for k, m in gt["core"].items()}
    return gt

for variant in ("unpainted", "normal", "extensive"):
    pr = sim.make_print(extensive=(variant == "extensive"))
    R = pr.R_unpainted if variant == "unpainted" else pr.R
    for cname, cap in (("clean", sim.CLEAN), ("A", sim.UNRULY_A), ("B", sim.UNRULY_B)):
        img, Hm = sim.capture(R, cap)
        gt = gtv(pr, Hm, cap, variant)
        res, _ = V.run(img, f"c_{variant}_{cname}")
        for space in ("raw", "lrc"):
            rows[f"v4.1.2 {space} | {variant} | {cname}"] = evalgt.score(res[space][0], np.ones(img.shape[:2], bool), gt, thr=0.2)
        for pname, ps in (("good", picks.GOOD), ("auto", None)):
            r = T.run(img, picks.to_capture(ps, Hm) if ps else None)
            rows[f"TODO {pname} | {variant} | {cname}"] = evalgt.score(r["opacity"], r["usable"], gt, thr=0.25)
        print(variant, cname, flush=True)
json.dump(rows, open("out/consolidated.json", "w"), indent=1)
