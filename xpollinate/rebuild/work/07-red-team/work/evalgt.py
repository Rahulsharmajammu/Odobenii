"""Ground truth in a capture's geometry, and the scores used in the report (analysis only, not tool output)."""
import numpy as np, cv2
from scipy import ndimage as ndi
import sim

PAINT = ("cheeks", "lips", "flag_red", "flag_blue", "patch_yellow", "wash")


def gt_in_capture(pr, Hm, cap):
    w = lambda m: sim.warp(m.astype(np.float32), Hm, cv2.INTER_NEAREST) > 0.5
    core = {k: w(v) for k, v in sim.chromatic_paint_mask(pr).items()}
    anymed = w(sim.any_medium(pr, tol=0.01))
    det = w((pr.layers["foxing"] > 0.05) | (pr.layers["mat_burn"] > 0.05))
    near = ndi.binary_dilation(anymed | det, iterations=6)
    glare = np.zeros((sim.P, sim.P), bool)
    if cap.glare:
        gx, gy, gr = cap.glare
        yy, xx = np.mgrid[0:sim.P, 0:sim.P]
        glare = (xx - gx * sim.S) ** 2 + (yy - gy * sim.S) ** 2 <= (3 * gr * sim.S) ** 2
    unpainted = ~near & ~glare
    fox = w(pr.layers["foxing"] > 0.5)
    burn = w(pr.layers["mat_burn"] > 0.5)
    ret_m = w(pr.layers["retouch_matched"] > 0.5)
    ret_n = w(pr.layers["retouch_neutral"] > 0.3)
    return dict(core=core, unpainted=unpainted, foxing=fox, mat_burn=burn, retouch_matched=ret_m,
                retouch_neutral=ret_n, glare=glare)


def score(op, usable, gt, thr=0.5):
    """op: opacity/alpha map in [0,1].  Returns dict of shares of pixels shown at >= thr."""
    out = {}
    u = gt["unpainted"] & usable
    out["unpainted_shown"] = float((op[u] >= thr).mean()) if u.any() else np.nan
    for k, m in gt["core"].items():
        mm = m & usable
        out[k] = float((op[mm] >= thr).mean()) if mm.any() else np.nan
    for k in ("foxing", "mat_burn", "retouch_matched", "retouch_neutral"):
        mm = gt[k] & usable
        out[k] = float((op[mm] >= thr).mean()) if mm.any() else np.nan
    out["usable_unpainted_px"] = int(u.sum())
    return out


def fmt(d, keys=("unpainted_shown",) + PAINT + ("foxing", "mat_burn", "retouch_matched", "retouch_neutral")):
    return "  ".join(f"{k}={100*d[k]:5.1f}%" if d.get(k) == d.get(k) else f"{k}=  n/a" for k in keys)
