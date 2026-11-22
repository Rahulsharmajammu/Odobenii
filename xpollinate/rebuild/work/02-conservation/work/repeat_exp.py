"""Two captures of the same print, the light and glare on the other side: do the departures repeat?

What is on the object should repeat; what the capture made (drift, glare, fringes, noise) should not.  Reported per
class: the share of pixels shown (opacity >= 0.5) in capture 1, in capture 2, and in both.
"""
import json

import numpy as np

import hpv_proto as HP
import methods as M
import sim
from bench import AGED, FULL_CAP


def captures(po):
    refl, gray, truth = sim.make_print(po)
    c1 = sim.CaptureOpts(**FULL_CAP)
    u1, t1 = sim.capture(refl, truth, c1, face_center=sim.face_ellipse(po))
    # the second: the light's drift reversed, the glare on the other side (mirror the frame, capture, mirror back)
    c2 = sim.CaptureOpts(**dict(FULL_CAP, seed=5))
    u2, t2 = sim.capture(refl[:, ::-1].copy(), {k: v[:, ::-1].copy() for k, v in truth.items()}, c2)
    u2 = u2[:, ::-1].copy()
    t2 = {k: v[:, ::-1].copy() for k, v in t2.items()}
    return u1, t1, u2, t2


def classes(t1, t2):
    paint = np.zeros(t1["edge"].shape, bool)
    for k, m in t1.items():
        if k.startswith("paint_") and k not in ("paint_white", "paint_spotting"):
            paint |= m
    obj = np.zeros_like(paint)
    for k in ("foxing", "adhesive", "mirroring"):
        obj |= t1.get(k, np.zeros_like(paint))
    cap = t1.get("glare", np.zeros_like(paint)) | t2.get("glare", np.zeros_like(paint))
    clean = ~paint & ~obj & ~cap & ~t1["edge"]
    return {"painted (transparent media)": paint, "deterioration (foxing, adhesive, silvering)": obj & ~paint,
            "glare in either capture": cap & ~paint & ~obj, "clean, away from edges": clean,
            "edges": t1["edge"] & ~paint & ~obj}


def main():
    po = sim.PrintOpts(tone="warm", paint="portrait", **AGED)
    u1, t1, u2, t2 = captures(po)
    out = {}
    for name, f in (("refined (automatic)", lambda u: HP.run(u, checks=False).alpha),
                    ("TODO as written", lambda u: M.todo_plan(u)[0])):
        a1, a2 = f(u1) >= 0.5, f(u2) >= 0.5
        row = {}
        for cname, m in classes(t1, t2).items():
            row[cname] = {"capture 1": round(float(a1[m].mean()), 3), "capture 2": round(float(a2[m].mean()), 3),
                          "both": round(float((a1 & a2)[m].mean()), 3)}
        out[name] = row
        print(name, json.dumps(row, indent=1))
    with open("bench_out/repeat.json", "w") as fh:
        json.dump(out, fh, indent=1)


if __name__ == "__main__":
    main()
