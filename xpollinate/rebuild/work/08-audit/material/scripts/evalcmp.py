import sys, numpy as np, cv2, warnings
from pathlib import Path
from PIL import Image
S = Path(sys.argv[1])
sys.path.insert(0, str(S / "scripts"))
import cd41
sys.path.insert(0, str(S / "wc/mbi_workbench/src/mbi_workbench"))
import importlib.util
spec = importlib.util.spec_from_file_location("chroma", S / "wc/mbi_workbench/src/mbi_workbench/chroma.py")
C = importlib.util.module_from_spec(spec); spec.loader.exec_module(C)

def vec_feature(lab):
    """|ab - median ab of the L* band| / robust sd: a hue-aware version of LRC"""
    L = lab[..., 0]; idx = np.clip(L.astype(int), 0, 99)
    out = np.zeros(L.shape, np.float32)
    med = np.zeros((100, 2)); sd = np.ones(100)
    for b in range(100):
        m = idx == b
        if m.sum() < 50: continue
        ab = lab[m][:, 1:]
        med[b] = np.median(ab, axis=0)
        r = np.linalg.norm(ab - med[b], axis=1)
        sd[b] = max(1.4826 * np.median(r), 0.5)
    d = np.linalg.norm(lab[..., 1:] - med[idx], axis=-1) / sd[idx]
    return d

print(f"{'case':24s} {'paint%':>6s} | raw hit/false | LRC hit/false | vec>4 hit/false | woodii hit/false(of shown)")
for p in sorted((S / "in").glob("*_lin.npy")):
    name = p.name[:-8]
    truth = np.load(S / "in" / f"{name}_truth.npy")
    d = next((S / "out").glob(f"{name}__*"))
    res = []
    for space in ("raw", "lrc"):
        m = np.asarray(Image.open(next((d / space).glob("*_mask.tif")))) > 0
        res.append((m[truth].mean() if truth.any() else float('nan'), m[~truth].mean()))
    rgb = cv2.cvtColor(cv2.imread(str(S / "in_img" / f"{name}.png")), cv2.COLOR_BGR2RGB).astype(np.float32) / 255
    lab = cd41._custom_rgb_to_lab(rgb, "sRGB")
    v = cv2.medianBlur(np.clip(vec_feature(lab), 0, 50).astype(np.float32), 5) > 4
    res.append((v[truth].mean() if truth.any() else float('nan'), v[~truth].mean()))
    lin = np.load(p)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            r = C.tint_maps(lin, untinted=[[1150, 950, 1600, 1200], [200, 950, 1100, 1200]] if "sky" not in name else [[600, 0, 1600, 1200]], base=[[0, 0, 80, 1200]], k=4.0)
            f, sh = r["flag"], r["show"]
            res.append((f[truth & sh].mean() if (truth & sh).any() else float('nan'), f[~truth & sh].mean()))
        except Exception as e:
            res.append((str(e)[:40], ""))
    print(f"{name:24s} {truth.mean()*100:6.1f} | " + " | ".join(f"{a if isinstance(a,str) else format(a*100,'5.1f')}/{b if isinstance(b,str) else format(b*100,'5.2f')}" for a, b in res))
