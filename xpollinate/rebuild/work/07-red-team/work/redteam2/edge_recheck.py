"""Re-test the red team's own claim: is TODO.md's edge false colour caused by median-filtering a*b* but not L*?
Compare a*b*-only median, the same median on L* too, and no median, on the unpainted print (opacity >= 0.5)."""
import sys
sys.path.insert(0, "..")
import numpy as np, cv2
from scipy import ndimage as ndi
from skimage import color
import sim, evalgt, picks, todo_pipeline as T

def run_variant(img, boxes, mode):
    c = dict(T.REPORT_CHOICES)
    rgb = img.astype(np.float32) / 255
    lab = color.rgb2lab(rgb).astype(np.float32)
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    if mode in ("ab", "Lab"):
        a = ndi.median_filter(a, 5); b = ndi.median_filter(b, 5)
    if mode == "Lab":
        L = ndi.median_filter(L, 5)
    usable = (rgb.max(-1) < c["clip_white"]) & (L > c["near_black_L"])
    sel = T.boxes_to_mask(L.shape, boxes) & usable
    ref = T.band_reference(L, a, b, sel, c)
    va, vb, z = T.feature(L, a, b, ref)
    z = ndi.median_filter(z, 3)
    t = np.clip((z - 2) / 3, 0, 1); op = (t * t * (3 - 2 * t)) ** 0.6; op[~usable] = 0
    return op, usable, L, np.median(ref["spread"])

pr = sim.make_print()
for cname, cap in (("clean", sim.CLEAN), ("A", sim.UNRULY_A)):
    img, Hm = sim.capture(pr.R_unpainted, cap)
    gt = evalgt.gt_in_capture(pr, Hm, cap)
    unp = ~gt["glare"] & ~cv2.dilate((gt["foxing"] | gt["mat_burn"]).astype(np.uint8), np.ones((13, 13))).astype(bool)
    boxes = picks.to_capture(picks.GOOD, Hm)
    for mode in ("ab", "Lab", "none"):
        op, usable, L, spr = run_variant(img, boxes, mode)
        g = np.hypot(*np.gradient(ndi.gaussian_filter(L, 1.0))); edge = g > 2.0
        u = usable & unp
        sh = op >= 0.5
        print(f"{cname:5s} median on {mode:4s}: shown {100*sh[u].mean():5.1f}%  flat {100*sh[u & ~edge].mean():5.1f}%  edges {100*sh[u & edge].mean():5.1f}%  (median band spread {spr:.2f})")
