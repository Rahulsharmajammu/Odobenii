"""How far each pipeline's idea of the unpainted photograph is from the real unpainted capture, in units of the
substrate's spread, by region: the developer's check of the reference itself (not something the tool shows)."""
import sys, json
import numpy as np
from scipy.ndimage import gaussian_filter
import synth, pipelines as PL, evaluate as E

def ideal_feature(clean, space):
    if space == "logc":
        f = PL.log_chroma(clean)
    else:
        f = PL.smooth_ab(PL.lab_of(clean), 5)
    return np.stack([gaussian_filter(f[..., i], 4) for i in range(2)], -1)

def run(scen, variants):
    img, t, clean = synth.paired(scen)
    any_paint, unpainted, regions = E.truth_masks(t)
    out = {}
    for name, kw in variants.items():
        res = PL.run_proposed(img, **kw)
        ideal = ideal_feature(clean, res["space"])
        err = np.linalg.norm(res["fit"]["ref"] - ideal, axis=-1) / res["fit"]["spread"][res["fit"]["band"]]
        v = res["valid"]
        row = {k: float(np.median(err[m & v])) for k, m in regions.items()}
        for pname, pm in t["paint"].items():
            c = (pm >= 0.5) & v
            if c.any():
                row["under " + pname.split(" (")[0]] = float(np.median(err[c]))
        out[name] = row
        print(scen, name, {k: round(x, 2) for k, x in row.items()}, flush=True)
    return out

if __name__ == "__main__":
    variants = {"logc": dict(space="logc"), "lab": dict(space="lab")}
    scen = sys.argv[1].split(",")
    res = {s: run(s, variants) for s in scen}
    json.dump(res, open("reference_error.json", "w"), indent=1)
