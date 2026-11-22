"""Experiment 4: does the plan's own step 3 (TODO.md:29, a 5 px median on a* and b* only) remove what experiment 3
found on JPEG and on a cast?  Same images as experiment 3 (exp3_img/, regenerated identically by it), same scoring;
reference as printed (A1) or the margin plus three 100x100 boxes along the bottom (A5).  Also the PNG originals."""
import sys, numpy as np, cv2
from pathlib import Path
W_ = Path(__file__).resolve().parent
S = W_ / "S"
sys.path.insert(0, str(S / "scripts")); sys.path.insert(0, str(W_))
import cd41, synthlib as L
IMG = W_ / "exp3_img"


def feat(lab, ref, floor=0.3):                      # pickref.py:4-15
    Lc = lab[..., 0]; idx = np.clip(Lc.astype(int), 0, 99)
    med = np.full((100, 2), np.nan); sd = np.full(100, np.nan)
    for b in range(100):
        m = (idx == b) & ref
        if m.sum() < 50: continue
        ab = lab[m][:, 1:]; med[b] = np.median(ab, axis=0)
        sd[b] = max(1.4826 * np.median(np.linalg.norm(ab - med[b], axis=1)), floor)
    ok = np.isfinite(sd); x = np.arange(100)
    for j in range(2): med[:, j] = np.interp(x, x[ok], med[ok, j])
    sd = np.interp(x, x[ok], sd[ok])
    return np.linalg.norm(lab[..., 1:] - med[idx], axis=-1) / sd[idx]


def smooth_ab(lab, k=5):
    out = lab.copy()
    for j in (1, 2):
        out[..., j] = cv2.medianBlur(np.ascontiguousarray(lab[..., j]).astype(np.float32), k)
    return out


def presence(z, thr=3.0):
    return cv2.medianBlur(np.clip(z, 0, 50).astype(np.float32), 5) > thr


def lab_of(path):
    rgb = cv2.cvtColor(cv2.imread(str(path)), cv2.COLOR_BGR2RGB).astype(np.float32) / 255
    return cd41._custom_rgb_to_lab(rgb, "sRGB")


def fmt(m, t):
    h = m[t].mean() * 100 if t.any() else float("nan")
    return ("  nan" if np.isnan(h) else f"{h:5.1f}") + f"/{m[~t].mean()*100:5.2f}"


def ref_a1(n):
    r = np.zeros((L.H, L.W), bool)
    if "sky" in n: r[:, 600:] = True
    else: r[950:, :] = True
    r[:, :80] = True
    return r


def ref_a5(n):
    r = np.zeros((L.H, L.W), bool); r[:, :80] = True
    boxes = [(650, 100, 750, 200), (1000, 600, 1100, 700), (1400, 1000, 1500, 1100)] if "sky" in n else \
            [(150, 1000, 250, 1100), (750, 1000, 850, 1100), (1350, 1000, 1450, 1100)]
    for x0, y0, x1, y1 in boxes: r[y0:y1, x0:x1] = True
    return r


sky = ((L.xx < 520) & (L.xx >= 80)).astype(np.float32)
defs = {
    "B_warm_untinted": (L.WARM, []),
    "C_warm_blue_wash": (L.WARM, [(L.box(500, 300, 1100, 900), L.BLUE, 0.06)]),
    "D_warm_sky_painted": (L.WARM, [(sky, L.BLUE, 0.10)]),
    "E_warm_small_touches": (L.WARM, [(L.box(700, 500, 708, 508), L.PINK, 0.25), (L.box(900, 500, 930, 530), L.PINK, 0.25)]),
    "F_warm_strong_pink": (L.WARM, [(L.box(500, 300, 1100, 900), L.PINK, 0.25)]),
}
print("% painted flagged / % unpainted flagged.  'ab5' = TODO.md:29's 5 px median on a*, b* before the feature")
print(f"{'input':14s} {'case':22s} {'A1':>12s} {'A1+ab5':>12s} {'A5':>12s} {'A5+ab5':>12s}")
for n, (tone, tints) in defs.items():
    for tag, path, truth in (
        ("PNG (prior)", S / "in_img" / f"{n}.png", np.load(S / "in" / f"{n}_truth.npy")),
        ("JPEG q85", IMG / f"{n}_q85.jpg", L.render(tone, tints, seed=11)[1]),
        ("cast +-3%", IMG / f"{n}_cast3.png", L.render(tone, tints, seed=11)[1]),
    ):
        lab = lab_of(path); lab5 = smooth_ab(lab)
        cells = [fmt(presence(feat(x, r(n))), truth) for r in (ref_a1, ref_a5) for x in (lab, lab5)]
        print(f"{tag:14s} {n:22s} " + " ".join(f"{c:>12s}" for c in (cells[0], cells[1], cells[2], cells[3])))
