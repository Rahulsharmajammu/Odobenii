"""The peer's tone-following check, run on v1 and v2 outputs: a 5 L* range whose pixels are lit (opacity >= 0.2) over
more than 30 % of them and in more than half the tiles that contain it."""
import numpy as np
import synth, pipelines as PL, pipelines_v2 as P2

def tone_following(res, grid=10, width=5.0, px_share=0.30, tile_share=0.5, min_tile_px=25):
    L = res["fit"]["Lidx"]; v = res["valid"]; lit = res["opacity"] >= 0.2
    h, w = L.shape
    ty = (np.arange(h) * grid) // h; tx = (np.arange(w) * grid) // w
    tile = ty[:, None] * grid + tx[None, :]
    fired = []
    for lo in np.arange(5, 100, width):
        sel = v & (L >= lo) & (L < lo + width)
        if sel.sum() < 0.01 * v.sum():
            continue
        if lit[sel].mean() <= px_share:
            continue
        tiles = np.unique(tile[sel])
        lit_t = [t_ for t_ in tiles if (sel & (tile == t_)).sum() >= min_tile_px and lit[sel & (tile == t_)].mean() > 0.3]
        tot_t = [t_ for t_ in tiles if (sel & (tile == t_)).sum() >= min_tile_px]
        if tot_t and len(lit_t) / len(tot_t) > tile_share:
            fired.append((float(lo), float(lo + width)))
    return fired

for scen in ("phone", "phone_mixed", "control", "thin", "toned", "phone_glare", "majority", "wide"):
    img, t = synth.scenario(scen)
    for name, fn in (("v1", lambda: PL.run_proposed(img, space="lab")), ("v2", lambda: P2.run_v2(img, votes=True, yardstick="rayleigh"))):
        res = fn()
        if "Lidx" not in res["fit"]:
            res["fit"]["Lidx"] = res["fit"].get("Lidx", res["L"])
        print(f"{scen:12s} {name}: tone-following fires on L* ranges {tone_following(res)}", flush=True)
