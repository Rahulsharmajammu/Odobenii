"""The finished prototype (local-linear tone curve, overrule test on the pixel scale, fringe term, gap check) on every
bench case: automatic (normal, high), picks, one bad pick, the object box where a table is in frame."""
import json
import sys
import time

import numpy as np

import bench as BE
import hpv_proto as HP
import sim

HP.LOCAL_LINEAR = True
HP.FRINGE = True
names = sys.argv[1:] or list(BE.CASES)
out = {}
for name in names:
    t0 = time.time()
    pk, ck = BE.CASES[name]
    po = sim.PrintOpts(**pk)
    refl, gray, truth = sim.make_print(po)
    co = sim.CaptureOpts(**ck)
    u8, truth = sim.capture(refl, truth, co, face_center=sim.face_ellipse(po))
    L, a, b = HP.lab_planes(u8)
    usable, _, _, _ = HP.judgeable(u8, L)
    pad = int(0.22 * refl.shape[0]) if co.table else 0
    runs = {"final_auto": dict(), "final_auto_high": dict(sensitivity="high", checks=False)}
    boxes = BE.to_px(BE.PICKS_CAMERA if po.content == "camera" else BE.PICKS_ASTRO, po, pad)
    runs["final_picks"] = dict(picks=boxes)
    if po.content == "astronaut":
        runs["final_badpick"] = dict(picks=BE.to_px(BE.PICKS_ASTRO + [BE.BAD_PICK], po, pad))
    if co.table:
        H, W = u8.shape[:2]
        runs["final_auto_box"] = dict(box=(pad, pad, W - pad, H - pad))
    out[name] = {}
    for rname, kw in runs.items():
        r = HP.run(u8, **kw)
        sc = BE.score(r.alpha, truth, usable)
        sc["warnings"] = r.warnings
        sc["odd_picks"] = list(r.odd)
        out[name][rname] = sc
        if rname in ("final_auto", "final_picks", "final_badpick", "final_auto_box"):
            B, C, D = HP.render(r)
            BE.montage([u8, B, C, D], ["A Capture", "B Print's own tone neutralised (x4)", "C Where colour departs",
                                       "D Expected unpainted, own tone (x4)"],
                       BE.OUT / f"{name}_{rname}.png", HP.tone_strip(r.ref, 600), r.warnings)
    print(name, round(time.time() - t0, 1), "s", flush=True)
    with open(BE.OUT / "final_scores.json", "w") as fh:
        json.dump(out, fh, indent=1)
