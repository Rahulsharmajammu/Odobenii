import sys, numpy as np, cv2
from pathlib import Path
S = Path(sys.argv[1]); sys.path.insert(0, str(S / "scripts")); import cd41
def feat(lab, ref):
    L = lab[..., 0]; idx = np.clip(L.astype(int), 0, 99)
    med = np.full((100, 2), np.nan); sd = np.full(100, np.nan)
    for b in range(100):
        m = (idx == b) & ref
        if m.sum() < 50: continue
        ab = lab[m][:, 1:]; med[b] = np.median(ab, axis=0)
        sd[b] = max(1.4826 * np.median(np.linalg.norm(ab - med[b], axis=1)), 0.3)
    ok = np.isfinite(sd); x = np.arange(100)
    for j in range(2): med[:, j] = np.interp(x, x[ok], med[ok, j])
    sd = np.interp(x, x[ok], sd[ok])
    return np.linalg.norm(lab[..., 1:] - med[idx], axis=-1) / sd[idx]
for p in sorted((S / "in").glob("*_lin.npy")):
    name = p.name[:-8]; truth = np.load(S / "in" / f"{name}_truth.npy")
    rgb = cv2.cvtColor(cv2.imread(str(S / "in_img" / f"{name}.png")), cv2.COLOR_BGR2RGB).astype(np.float32) / 255
    lab = cd41._custom_rgb_to_lab(rgb, "sRGB")
    ref = np.zeros(truth.shape, bool)
    if "sky" in name: ref[:, 600:] = True; ref[:, :80] = True
    else: ref[950:, :] = True; ref[:, :80] = True
    z = cv2.medianBlur(np.clip(feat(lab, ref), 0, 50).astype(np.float32), 5)
    v = z > 3
    print(f"{name:24s} hit {v[truth].mean()*100 if truth.any() else float('nan'):5.1f}%  false {v[~truth].mean()*100:5.2f}%")
