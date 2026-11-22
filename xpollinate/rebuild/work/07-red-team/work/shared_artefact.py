"""Is the A+C residue the shared lens fringing?  Where it sits, and what changing C's lens (sign of CA) does."""
import json, dataclasses, numpy as np, cv2
from scipy import ndimage as ndi
import sim, evalgt, picks, honest as Hn
from run_honest import single

def pair_unpainted(capB):
    rA = single("unpainted", sim.UNRULY_A, picks.GOOD); rB = single("unpainted", capB, picks.GOOD)
    Hba, _ = Hn.register(rB["img"], rA["img"])
    w = lambda m, i=cv2.INTER_LINEAR: cv2.warpPerspective(m.astype(np.float32), Hba, (sim.P, sim.P), flags=i, borderValue=0)
    dBw = {k: w(rB["d"][k]) for k in ("va", "vb", "z")}
    uB = w(rB["usable"] & ~rB["d"]["uncovered"], cv2.INTER_NEAREST) > 0.5
    uA = rA["usable"] & ~rA["d"]["uncovered"]
    keep, one, zm = Hn.persistent(rA["d"], uA, dBw, uB)
    op = Hn.ramp(zm, 1.5, 5.0) * keep
    unp = rA["gt"]["unpainted"] & uA & uB
    shown = (op >= 0.25) & unp
    L = rA["lab"][..., 0]
    edge = ndi.binary_dilation(np.hypot(*np.gradient(L)) > 3.0, iterations=2)
    return dict(fp=float(shown.sum() / unp.sum()), on_edges=float((shown & edge).sum() / max(shown.sum(), 1)),
                edge_share_of_unpainted=float((edge & unp).sum() / unp.sum()))

out = {}
out["A+C (same-sign fringing)"] = pair_unpainted(sim.UNRULY_C)
out["A+C' (C's lens fringing reversed)"] = pair_unpainted(dataclasses.replace(sim.UNRULY_C, ca=-0.002))
out["A+C'' (C with no fringing)"] = pair_unpainted(dataclasses.replace(sim.UNRULY_C, ca=0.0))
for k, v in out.items():
    print(f"{k:36s} unpainted shown {100*v['fp']:.2f}%  of which on edges {100*v['on_edges']:.0f}% (edges are {100*v['edge_share_of_unpainted']:.0f}% of unpainted)")
json.dump(out, open("out/shared_artefact.json", "w"), indent=1)
