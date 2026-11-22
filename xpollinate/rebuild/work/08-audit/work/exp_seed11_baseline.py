"""Experiment 8 (control): experiment 3's new images used noise seed 11.  The same scenes as lossless PNG at seed 11,
scored the same way, so the JPEG and cast rows can be read against their own baseline."""
import sys, numpy as np, cv2
from pathlib import Path
W_ = Path(__file__).resolve().parent
src = open(W_ / "exp_todo_mitigation.py").read().split("sky = ((L.xx")[0]
exec(src)                                    # feat, presence, lab_of, fmt, ref_a1, ref_a5, L, IMG, cd41
sky = ((L.xx < 520) & (L.xx >= 80)).astype(np.float32)
defs = {"B_warm_untinted": (L.WARM, []),
        "C_warm_blue_wash": (L.WARM, [(L.box(500, 300, 1100, 900), L.BLUE, 0.06)]),
        "D_warm_sky_painted": (L.WARM, [(sky, L.BLUE, 0.10)]),
        "E_warm_small_touches": (L.WARM, [(L.box(700, 500, 708, 508), L.PINK, 0.25), (L.box(900, 500, 930, 530), L.PINK, 0.25)]),
        "F_warm_strong_pink": (L.WARM, [(L.box(500, 300, 1100, 900), L.PINK, 0.25)])}
print(f"{'seed 11, PNG':22s} {'vis raw':>12s} {'vis LRC':>12s} {'A1':>12s} {'A5':>12s}")
for n, (tone, tints) in defs.items():
    lin, truth = L.render(tone, tints, seed=11)
    p = IMG / f"{n}_seed11.png"
    cv2.imwrite(str(p), cv2.cvtColor(L.to_png8(lin), cv2.COLOR_RGB2BGR))
    proc = cd41.ImageProcessor(cd41.VisualizerConfig(input_dir=IMG, output_dir=W_ / "exp_tmp"))
    rgb, meta = proc._open_working_rgb(p)
    lab_v = proc._rgb_to_lab(rgb, meta["working_colorspace"]); ch = proc._chroma_from_lab(lab_v); lrc, _ = proc._compute_lrc(lab_v, ch)
    vis = [fmt(proc._threshold_and_map(f, s)[2] > 0, truth) for s, f in (("raw", ch), ("lrc", lrc))]
    lab = lab_of(p)
    print(f"{n:22s} {vis[0]:>12s} {vis[1]:>12s} {fmt(presence(feat(lab, ref_a1(n))), truth):>12s} {fmt(presence(feat(lab, ref_a5(n))), truth):>12s}")
