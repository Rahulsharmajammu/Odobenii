"""Picks with the hybrid reference (picks decide the tones they reach; the automatic votes fill the rest) and the
gap-aware leave-one-pick-out check, on every bench case."""
import json
import sys

import bench as BE
import hpv_proto as HP
import sim

HP.LOCAL_LINEAR = True
HP.FRINGE = True
names = sys.argv[1:] or list(BE.CASES)
out = {}
for name in names:
    pk, ck = BE.CASES[name]
    po = sim.PrintOpts(**pk)
    refl, gray, truth = sim.make_print(po)
    co = sim.CaptureOpts(**ck)
    u8, truth = sim.capture(refl, truth, co, face_center=sim.face_ellipse(po))
    L, a, b = HP.lab_planes(u8)
    usable, _, _, _ = HP.judgeable(u8, L)
    pad = int(0.22 * refl.shape[0]) if co.table else 0
    runs = {"hybrid_picks": BE.to_px(BE.PICKS_CAMERA if po.content == "camera" else BE.PICKS_ASTRO, po, pad)}
    if po.content == "astronaut":
        runs["hybrid_badpick"] = BE.to_px(BE.PICKS_ASTRO + [BE.BAD_PICK], po, pad)
    out[name] = {}
    for rname, boxes in runs.items():
        r = HP.run(u8, picks=boxes)
        sc = BE.score(r.alpha, truth, usable)
        sc["warnings"] = r.warnings
        sc["odd_picks"] = list(r.odd)
        out[name][rname] = sc
        if name in ("P2_portrait_aged_capture", "U5_sepia_landscape_capture", "U1_warm"):
            B, C, D = HP.render(r)
            BE.montage([u8, B, C, D], ["A Capture", "B Neutralised (x4)", "C Where colour departs",
                                       "D Expected unpainted (x4), picks"],
                       BE.OUT / f"{name}_{rname}.png", HP.tone_strip(r.ref, 600), r.warnings)
        d = sc["shown>=0.2"]
        print(name, rname, {k: round(v, 2) for k, v in d.items() if v is not None}, "odd", list(r.odd), flush=True)
        for w in r.warnings:
            print("    -", w[:120], flush=True)
    with open(BE.OUT / "picks_hybrid.json", "w") as fh:
        json.dump(out, fh, indent=1)
