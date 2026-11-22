import json, numpy as np
import hpv, evaluate as E
jobs = [("portrait", False), ("neg_hard", False), ("blue_over_warm", False), ("blue_over_warm", True),
        ("sky_faint", False), ("sky_faint", True), ("glare_bg", False), ("all_painted", False), ("portrait_heavy", False)]
for n, picked in jobs:
    c = E.load_case(n)
    rgb = c["img"].astype(np.float32) / 255
    picks = ()
    if picked:
        L, bare, cores = E.eval_masks(c)
        picks = E.auto_picks(c, L, bare)
    res = hpv.analyse(rgb, picks=picks)
    tag = n + ("_picked" if picked else "")
    hpv.montage(res, f"{n}.jpg", panel=560).save(f"fig/montage_{tag}.png")
    print(tag, res["ref"].source, res["warnings"])
