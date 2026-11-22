import json, numpy as np, cv2
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
    ref = Hn.Reference(lab, usable, picks.to_capture(pickset, Hm))
    d = Hn.departure(lab, usable, ref)
    op = Hn.ramp(d["z"]); op[d["uncovered"]] = 0
    words = Hn.tripwires(lab, usable, d, ref, op >= 0.25)
    return dict(pr=pr, img=img, Hm=Hm, lab=lab, usable=usable, ref=ref, d=d, op=op, words=words,
                gt=gt_for(pr, Hm, cap, variant))

def report(label, r, op=None, usable=None):
    op = r["op"] if op is None else op
    usable = (r["usable"] & ~r["d"]["uncovered"]) if usable is None else usable
    s25 = evalgt.score(op, usable, r["gt"], thr=0.25); s50 = evalgt.score(op, usable, r["gt"], thr=0.5)
    ref = r["ref"]
    print(f"{label:52s} | op>=.25: " + evalgt.fmt(s25))
    print(f"{'':52s} | op>=.50: " + evalgt.fmt(s50))
    print(f"{'':52s} | scale {ref.scale:.2f} (pix {ref.s_pix:.2f}, marks {ref.s_sys:.2f}) deg {ref.deg} plane {ref.plane} "
          f"L* {ref.L_lo:.0f}-{ref.L_hi:.0f}; mark residuals {np.round(np.linalg.norm(ref.loo,axis=1),1).tolist()}")
    for w in r["words"]:
        print(f"{'':52s} | TRIPWIRE: {w}")
    return dict(s25=s25, s50=s50, scale=ref.scale, words=r["words"], loo=np.linalg.norm(ref.loo, axis=1).tolist())

OUT = {}
runs = {}
for label, variant, cap, ps in (
        ("H0 clean, good marks", "normal", sim.CLEAN, picks.GOOD),
        ("H1 unruly A, good marks", "normal", sim.UNRULY_A, picks.GOOD),
        ("H1 unruly B, good marks", "normal", sim.UNRULY_B, picks.GOOD),
        ("H2 unruly A, one mark on the faint wash", "normal", sim.UNRULY_A, picks.CONTAMINATED),
        ("H2 clean, one mark on the faint wash", "normal", sim.CLEAN, picks.CONTAMINATED),
        ("H4 clean, marks on the suit only", "normal", sim.CLEAN, picks.MIDTONES_ONLY),
        ("H5 unpainted print, unruly A, good marks", "unpainted", sim.UNRULY_A, picks.GOOD),
        ("H5 unpainted print, unruly B, good marks", "unpainted", sim.UNRULY_B, picks.GOOD),
        ("H5 unpainted print, clean, good marks", "unpainted", sim.CLEAN, picks.GOOD)):
    r = single(variant, cap, ps)
    runs[label] = r
    OUT[label] = report(label, r)

# two captures: B registered onto A, each with its own marks
def pair(label, variant, psA, psB, capA=sim.UNRULY_A, capB=sim.UNRULY_B):
    rA = single(variant, capA, psA); rB = single(variant, capB, psB)
    Hba, ninl = Hn.register(rB["img"], rA["img"])
    w = lambda m, interp=cv2.INTER_LINEAR: cv2.warpPerspective(m.astype(np.float32), Hba, (sim.P, sim.P), flags=interp, borderValue=0)
    dBw = {"va": w(rB["d"]["va"]), "vb": w(rB["d"]["vb"]), "z": w(rB["d"]["z"])}
    uB = w(rB["usable"] & ~rB["d"]["uncovered"], cv2.INTER_NEAREST) > 0.5
    uA = rA["usable"] & ~rA["d"]["uncovered"]
    keep, one, zmin = Hn.persistent(rA["d"], uA, dBw, uB)
    op = Hn.ramp(zmin, 1.5, 5.0) * keep
    # registration error against the truth (both homographies known)
    HA, HB = rA["Hm"], rB["Hm"]
    true_Hba = HA @ np.linalg.inv(HB)
    pts = np.float32([[100, 100], [900, 100], [900, 900], [100, 900], [512, 512]]).reshape(-1, 1, 2)
    err = np.linalg.norm(cv2.perspectiveTransform(pts, Hba) - cv2.perspectiveTransform(pts, true_Hba), axis=-1).max()
    print(f"[{label}] registration: {ninl} inliers, max error {err:.2f} px")
    rr = dict(rA); rr["op"] = op
    res = report(label, rr, op=op, usable=uA & uB)
    one_unp = (one & rA["gt"]["unpainted"] & uA & uB).mean() / max((rA["gt"]["unpainted"] & uA & uB).mean(), 1e-9)
    print(f"{'':52s} | 'seen in one capture only' on unpainted: {100*one_unp:.1f}%")
    res["one_capture_only_unpainted"] = float(one_unp); res["reg_err_px"] = float(err)
    runs[label] = dict(rA=rA, rB=rB, keep=keep, one=one, op=op, uA=uA, uB=uB, Hba=Hba, dBw=dBw)
    return res

OUT["P1 two captures (A+B), good marks"] = pair("P1 two captures (A+B), good marks", "normal", picks.GOOD, picks.GOOD)
OUT["P2 two captures, A's marks contaminated"] = pair("P2 two captures, A's marks contaminated", "normal", picks.CONTAMINATED, picks.GOOD)
OUT["P5 two captures of the unpainted print"] = pair("P5 two captures of the unpainted print", "unpainted", picks.GOOD, picks.GOOD)
for nmA, nmB, cA, cB in (("A", "C", sim.UNRULY_A, sim.UNRULY_C), ("B", "C", sim.UNRULY_B, sim.UNRULY_C)):
    for variant in ("normal", "unpainted"):
        OUT[f"R {variant} {nmA}+{nmB}"] = pair(f"R {variant} print, captures {nmA}+{nmB}, good marks", variant, picks.GOOD, picks.GOOD, cA, cB)
for variant in ("normal", "unpainted"):
    r = single(variant, sim.UNRULY_C, picks.GOOD)
    OUT[f"R {variant} C single"] = report(f"R {variant} print, capture C alone, good marks", r)
json.dump(OUT, open("out/honest_scores.json", "w"), indent=1, default=float)
import pickle; pickle.dump({k: v for k, v in runs.items() if k.startswith(("H2 unruly", "P1", "P2", "H5 unpainted print, unruly A", "H1 unruly A"))}, open("out/honest_runs.pkl", "wb"))
