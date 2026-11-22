"""Experiment 1: the visualiser 4.1.1's own threshold options on the prior work's synthetic prints.

The prior work scored only the default (noise_floor, fraction 0.01, 100 px filter).  Here the same feature
code (cd41 = Chroma_diagnoser_v4.1 at cfbf66c) is run with the other modes it ships: percentile 90 (the
author's own default at a365ea6), Otsu, fixed thresholds, a looser noise fraction and no component filter.
Scored like evalcmp.py: % of painted pixels flagged / % of unpainted pixels flagged, on the filtered binary mask.
"""
import sys, warnings, numpy as np
from pathlib import Path
S = Path(sys.argv[1])
sys.path.insert(0, str(S / "scripts"))
import cd41

warnings.simplefilter("ignore")
cases = ["A_neutral_untinted", "B_warm_untinted", "C_warm_blue_wash", "D_warm_sky_painted",
         "E_warm_small_touches", "F_warm_strong_pink"]
configs = [
    ("noise_floor f=0.01 (default, scored)", dict()),
    ("noise_floor f=0.05", dict(noise_fraction=0.05)),
    ("noise_floor f=0.01, filter 0", dict(min_component_area_pixels=0)),
    ("percentile 90 (a365ea6 default)", dict(threshold_mode="percentile", percentile=90.0)),
    ("percentile 75", dict(threshold_mode="percentile", percentile=75.0)),
    ("otsu", dict(threshold_mode="otsu")),
]
fixed = {"raw": [5.0, 16.0, 18.0], "lrc": [0.5, 1.0, 2.0]}

def score(m, truth):
    hit = m[truth].mean() * 100 if truth.any() else float("nan")
    return hit, m[~truth].mean() * 100

rows = []
for name in cases:
    truth = np.load(S / "in" / f"{name}_truth.npy")
    base_cfg = cd41.VisualizerConfig(input_dir=S / "in_img", output_dir=S / "exp_tmp")
    proc = cd41.ImageProcessor(base_cfg)
    rgb, meta = proc._open_working_rgb(S / "in_img" / f"{name}.png")
    lab = proc._rgb_to_lab(rgb, meta["working_colorspace"])
    chroma = proc._chroma_from_lab(lab)
    lrc, _ = proc._compute_lrc(lab, chroma)
    feats = {"raw": chroma, "lrc": lrc}
    for label, kw in configs:
        cfg = cd41.VisualizerConfig(input_dir=S / "in_img", output_dir=S / "exp_tmp", **kw)
        p = cd41.ImageProcessor(cfg)
        for space in ("raw", "lrc"):
            thr, _, mask, _ = p._threshold_and_map(feats[space], space)
            rows.append((name, space, label, thr) + score(mask > 0, truth))
    for space, vals in fixed.items():
        for v in vals:
            cfg = cd41.VisualizerConfig(input_dir=S / "in_img", output_dir=S / "exp_tmp",
                                        threshold_mode="fixed", fixed_threshold=v)
            p = cd41.ImageProcessor(cfg)
            thr, _, mask, _ = p._threshold_and_map(feats[space], space)
            rows.append((name, space, f"fixed {v:g}", thr) + score(mask > 0, truth))

for space in ("raw", "lrc"):
    labels = [l for l, _ in configs] + [f"fixed {v:g}" for v in fixed[space]]
    print(f"\n== {space}: % painted flagged / % unpainted flagged (threshold)")
    print(f"{'setting':38s} " + " ".join(f"{c[:14]:>22s}" for c in cases))
    for lab_ in labels:
        cells = []
        for name in cases:
            r = next(r for r in rows if r[0] == name and r[1] == space and r[2] == lab_)
            h = "  nan" if np.isnan(r[4]) else f"{r[4]:5.1f}"
            cells.append(f"{h}/{r[5]:5.2f} ({r[3]:6.2f})")
        print(f"{lab_:38s} " + " ".join(f"{c:>22s}" for c in cells))
