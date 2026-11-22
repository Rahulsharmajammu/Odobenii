import numpy as np, sys
from PIL import Image
import synth as S, bench as B, hpv5_proto as H
want = sys.argv[1:] or ["N2", "P1", "P4", "P5", "P6"]
for ci, (name, recipe, tone, paper, capd, extra) in enumerate(B.CASES):
    if name.split()[0] not in want: continue
    cap = S.Capture(seed=10 + ci, **capd)
    case = S.make_case(name, recipe, tone, paper, cap, seed=ci, **extra)
    canvas, res = H.montage(case.rgb, name, out=f"img/proto_{name.split()[0]}.png")
    small = canvas.copy(); small.thumbnail((1800, 1200)); small.save(f"img/proto_{name.split()[0]}_small.png")
    print(name, "| warnings:", res.warnings)
