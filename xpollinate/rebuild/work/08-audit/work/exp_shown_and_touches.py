"""Experiment 2: two numbers the replies state that the printed output does not show.

(a) Woodii's column was scored only where Woodii "shows" (evalcmp.py:46).  How much of each frame, and of the
    paint, is that?  And the hit rate if masked pixels count as not flagged.
(b) reply-1 says the hand-chosen reference found "100% of ... the larger touch"; pickref.py printed one figure for
    both touches (97.5%).  Per touch, what did it find?
"""
import sys, warnings, numpy as np, cv2, importlib.util
from pathlib import Path
S = Path(sys.argv[1])
sys.path.insert(0, str(S / "scripts"))
import cd41
spec = importlib.util.spec_from_file_location("chroma", S / "wc/mbi_workbench/src/mbi_workbench/chroma.py")
C = importlib.util.module_from_spec(spec); spec.loader.exec_module(C)

print("(a) Woodii tint_maps, picks exactly as evalcmp.py:44")
print(f"{'case':24s} {'shown% frame':>12s} {'shown% paint':>12s} {'hit% of shown':>13s} {'hit% all paint':>14s}")
for name in ["A_neutral_untinted", "B_warm_untinted", "C_warm_blue_wash", "D_warm_sky_painted",
             "E_warm_small_touches", "F_warm_strong_pink"]:
    lin = np.load(S / "in" / f"{name}_lin.npy"); truth = np.load(S / "in" / f"{name}_truth.npy")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = C.tint_maps(lin, untinted=[[1150, 950, 1600, 1200], [200, 950, 1100, 1200]] if "sky" not in name
                        else [[600, 0, 1600, 1200]], base=[[0, 0, 80, 1200]], k=4.0)
    f, sh = r["flag"], r["show"]
    hs = f[truth & sh].mean() * 100 if (truth & sh).any() else float("nan")
    ha = f[truth].mean() * 100 if truth.any() else float("nan")
    sp = sh[truth].mean() * 100 if truth.any() else float("nan")
    print(f"{name:24s} {sh.mean()*100:12.1f} {sp:12.1f} {hs:13.1f} {ha:14.1f}")

print("\n(b) pickref.py's feature on E, per touch (threshold 3 after a 5 px median, as printed)")
pr = {"np": np}
exec(open(Path(sys.argv[2])).read().split("for p in sorted")[0].split("import cd41")[1], pr)  # defines feat()
feat = pr["feat"]
name = "E_warm_small_touches"
truth = np.load(S / "in" / f"{name}_truth.npy")
rgb = cv2.cvtColor(cv2.imread(str(S / "in_img" / f"{name}.png")), cv2.COLOR_BGR2RGB).astype(np.float32) / 255
lab = cd41._custom_rgb_to_lab(rgb, "sRGB")
ref = np.zeros(truth.shape, bool); ref[950:, :] = True; ref[:, :80] = True
z = cv2.medianBlur(np.clip(feat(lab, ref), 0, 50).astype(np.float32), 5)
v = z > 3
small = np.zeros_like(truth); small[500:508, 700:708] = True
large = np.zeros_like(truth); large[500:530, 900:930] = True
print(f"8x8 touch  ({small.sum()} px): {v[small].mean()*100:5.1f}% flagged")
print(f"30x30 touch ({large.sum()} px): {v[large].mean()*100:5.1f}% flagged")
print(f"both: {v[truth].mean()*100:5.1f}% flagged")
