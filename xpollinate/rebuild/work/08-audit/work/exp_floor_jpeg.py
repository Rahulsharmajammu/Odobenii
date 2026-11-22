"""Experiment 6: the JPEG false positives against pickref.py's spread floor (0.3).  Woodii's design note says an
8-bit input made the pick-measured noise 'nearly degenerate' (chroma-mode-plan.md:167-169).  Same JPEGs and
scoring as experiment 4; reference A1 (as printed) and A5 (margin + three 100x100 boxes)."""
import sys, numpy as np
from pathlib import Path
W_ = Path(__file__).resolve().parent
src = open(W_ / "exp_todo_mitigation.py").read().split("sky = ((L.xx")[0]
exec(src)                                    # feat, presence, lab_of, fmt, ref_a1, ref_a5, L, IMG
sky = ((L.xx < 520) & (L.xx >= 80)).astype(np.float32)
defs = {"B_warm_untinted": (L.WARM, []),
        "C_warm_blue_wash": (L.WARM, [(L.box(500, 300, 1100, 900), L.BLUE, 0.06)]),
        "F_warm_strong_pink": (L.WARM, [(L.box(500, 300, 1100, 900), L.PINK, 0.25)])}
print(f"{'JPEG q85 case':22s} {'ref':4s} " + " ".join(f"{'floor '+str(f):>12s}" for f in (0.3, 0.6, 1.0, 1.5)))
for n, (tone, tints) in defs.items():
    truth = L.render(tone, tints, seed=11)[1]
    lab = lab_of(IMG / f"{n}_q85.jpg")
    for rn, rf in (("A1", ref_a1), ("A5", ref_a5)):
        print(f"{n:22s} {rn:4s} " + " ".join(f"{fmt(presence(feat(lab, rf(n), floor=f)), truth):>12s}" for f in (0.3, 0.6, 1.0, 1.5)))
