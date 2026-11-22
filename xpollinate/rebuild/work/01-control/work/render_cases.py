import sys, numpy as np
import hpv, evaluate as E
names = sys.argv[1].split(",")
for n in names:
    c = E.load_case(n)
    rgb = c["img"].astype(np.float32) / 255
    res = hpv.analyse(rgb)
    M = hpv.montage(res, f"{n}.jpg", panel=620)
    M.save(f"fig/montage_{n}.png")
    print(n, M.size, res["ref"].source, len(res["warnings"]), "warnings")
