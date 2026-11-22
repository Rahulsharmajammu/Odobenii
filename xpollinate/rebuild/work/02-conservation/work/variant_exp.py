"""Targeted test of two refinements: local-linear smoothing across tones, and the lateral-colour (fringe) term."""
import json
import sys

import numpy as np

import bench as BE
import hpv_proto as HP
import sim

CASES = sys.argv[1:] or ["U1_warm", "U3_warm_capture", "U4_warm_aged_capture", "U5_sepia_landscape_capture",
                         "P2_portrait_aged_capture", "P3_heavy_aged_capture", "P4_landscape_sepia_capture"]
VARIANTS = {
    "as benched (local mean, no fringe term)": dict(ll=False, fringe=False),
    "local-linear": dict(ll=True, fringe=False),
    "local-linear + fringe term": dict(ll=True, fringe=True),
}
out = {}
for name in CASES:
    pk, ck = BE.CASES[name]
    po = sim.PrintOpts(**pk)
    refl, gray, truth = sim.make_print(po)
    co = sim.CaptureOpts(**ck)
    u8, truth = sim.capture(refl, truth, co, face_center=sim.face_ellipse(po))
    L, a, b = HP.lab_planes(u8)
    usable, _, _, _ = HP.judgeable(u8, L)
    out[name] = {}
    for vname, v in VARIANTS.items():
        HP.LOCAL_LINEAR = v["ll"]
        r = HP.run(u8, fringe=v["fringe"], checks=True)
        sc = BE.score(r.alpha, truth, usable)["shown>=0.2"]
        sc["overruled_warning"] = any("overruled" in w for w in r.warnings)
        sc["warnings"] = len(r.warnings)
        sc["fringe_coef"] = [round(float(x), 2) for x in getattr(r.ref, "fringe", (0, 0))]
        sc["kappa"] = round(r.ref.kappa, 2)
        out[name][vname] = sc
        print(name, '|', vname, '|', {k: (round(v2, 2) if isinstance(v2, float) else v2) for k, v2 in sc.items() if v2 is not None}, flush=True)
        if name == "U5_sepia_landscape_capture" and v["ll"] and v["fringe"]:
            B, C, D = HP.render(r)
            BE.montage([u8, B, C, D], ["A Capture", "B Neutralised (x4)", "C Where colour departs", "D Expected unpainted (x4)"],
                       BE.OUT / f"{name}_final.png", HP.tone_strip(r.ref, 600), r.warnings)
        if name == "P2_portrait_aged_capture" and v["ll"] and v["fringe"]:
            B, C, D = HP.render(r)
            BE.montage([u8, B, C, D], ["A Capture", "B Neutralised (x4)", "C Where colour departs", "D Expected unpainted (x4)"],
                       BE.OUT / f"{name}_final.png", HP.tone_strip(r.ref, 600), r.warnings)
with open(BE.OUT / "variants.json", "w") as fh:
    json.dump(out, fh, indent=1)
