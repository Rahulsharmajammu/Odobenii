import json, numpy as np, cv2
import sim, evalgt, picks, todo_pipeline as T

def scen(label, variant, cap, pickset, save=None):
    pr = sim.make_print(extensive=(variant == "extensive"))
    R = pr.R_unpainted if variant == "unpainted" else pr.R
    img, Hm = sim.capture(R, cap)
    gt = evalgt.gt_in_capture(pr, Hm, cap)
    if variant == "unpainted":
        gt["unpainted"] = ~gt["glare"] & ~cv2.dilate((gt["foxing"] | gt["mat_burn"]).astype(np.uint8), np.ones((13, 13))).astype(bool)
        gt["core"] = {k: np.zeros_like(m) for k, m in gt["core"].items()}
    bx = picks.to_capture(pickset, Hm) if pickset else None
    res = T.run(img, bx)
    s = evalgt.score(res["opacity"], res["usable"], gt, thr=0.5)
    sp = res["ref"]["raw_spread"]; sp = sp[np.isfinite(sp)]
    cov = res["ref"]["centres"][res["ref"]["covered"]]
    print(f"{label:44s} | " + evalgt.fmt(s) + f" | spread med {np.median(sp):.2f} min {sp.min():.2f} | L* covered {cov.min():.0f}-{cov.max():.0f}", flush=True)
    if save:
        pic = T.presence_picture(img, res)
        if bx:
            for (x0, y0, x1, y1) in bx:
                cv2.rectangle(pic, (int(x0), int(y0)), (int(x1), int(y1)), (255, 255, 255), 2)
        cv2.imwrite(f"out/todo_{save}.png", cv2.cvtColor(np.hstack([img, pic]), cv2.COLOR_RGB2BGR))
    return s

R = {}
R["S0 clean capture, good picks"] = scen("S0 clean capture, good picks", "normal", sim.CLEAN, picks.GOOD, "S0")
R["S1 unruly A, good picks"] = scen("S1 unruly A, good picks", "normal", sim.UNRULY_A, picks.GOOD, "S1A")
R["S1 unruly B, good picks"] = scen("S1 unruly B, good picks", "normal", sim.UNRULY_B, picks.GOOD, "S1B")
R["S2 unruly A, one pick on the faint wash"] = scen("S2 unruly A, one pick on the faint wash", "normal", sim.UNRULY_A, picks.CONTAMINATED, "S2")
R["S2 clean, one pick on the faint wash"] = scen("S2 clean, one pick on the faint wash", "normal", sim.CLEAN, picks.CONTAMINATED, "S2clean")
R["S3 automatic, normal print, clean"] = scen("S3 automatic, normal print, clean", "normal", sim.CLEAN, None)
R["S3 automatic, normal print, unruly A"] = scen("S3 automatic, normal print, unruly A", "normal", sim.UNRULY_A, None)
R["S3 automatic, wash over 80%, clean"] = scen("S3 automatic, wash over 80%, clean", "extensive", sim.CLEAN, None, "S3ext")
R["S3 automatic, wash over 80%, unruly A"] = scen("S3 automatic, wash over 80%, unruly A", "extensive", sim.UNRULY_A, None)
R["S4 clean, picks on the suit only (mid-tones)"] = scen("S4 clean, picks on the suit only (mid-tones)", "normal", sim.CLEAN, picks.MIDTONES_ONLY, "S4")
R["S5 unpainted print, unruly A, good picks"] = scen("S5 unpainted print, unruly A, good picks", "unpainted", sim.UNRULY_A, picks.GOOD, "S5A")
R["S5 unpainted print, unruly B, good picks"] = scen("S5 unpainted print, unruly B, good picks", "unpainted", sim.UNRULY_B, picks.GOOD, "S5B")
R["S5 unpainted print, clean, good picks"] = scen("S5 unpainted print, clean, good picks", "unpainted", sim.CLEAN, picks.GOOD)
json.dump(R, open("out/todo_scores.json", "w"), indent=1)
