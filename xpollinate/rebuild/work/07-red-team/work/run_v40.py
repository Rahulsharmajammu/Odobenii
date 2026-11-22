"""v4.0 / 4.1.0 as committed (a365ea6), the version behind the VDZ runs: its own internals on synthetic captures."""
import sys, types, json
from pathlib import Path
import numpy as np, cv2
from PIL import Image
import sim, evalgt

src = Path("hist/v4.0_a365ea6.py").read_text()
src = src.replace("INPUT_DIR = <INPUT PATH HERE>", "INPUT_DIR = 'in_v40'").replace("OUTPUT_DIR = <OUTPUT PATH HERE>", "OUTPUT_DIR = 'out_v40'")
mod = types.ModuleType("v40"); mod.__file__ = "v40.py"; sys.modules["v40"] = mod
exec(compile(src, "v40.py", "exec"), mod.__dict__)
IN = Path("in_v40"); OUT = Path("out_v40"); IN.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True)
cfg = mod.VisualizerConfig(input_dir=IN, output_dir=OUT, output_scale=1.0)
proc = mod.ImageProcessor(cfg)
print("v4.0 defaults:", cfg.threshold_mode, cfg.percentile, "min component", cfg.min_component_area_pixels)

# neutral greys through the v4.0 decode (untagged -> its default space)
for v in (0.25, 0.5, 0.75, 0.95):
    p = IN / "grey.png"; Image.fromarray(np.full((64, 64, 3), int(v * 255), np.uint8)).save(p)
    rgb, meta = proc._open_working_rgb(p)
    lab = proc._rgb_to_lab(rgb, meta["detected_colorspace"])
    print(f"neutral grey {v:.2f}: decoded as {meta['detected_colorspace']}, L* {lab[...,0].mean():.1f}, C*ab {np.hypot(lab[...,1], lab[...,2]).mean():.2f}")
out = {}
for variant in ("unpainted", "normal"):
    pr = sim.make_print()
    R = pr.R_unpainted if variant == "unpainted" else pr.R
    for cname, cap in (("clean", sim.CLEAN), ("A", sim.UNRULY_A)):
        img, Hm = sim.capture(R, cap)
        gt = evalgt.gt_in_capture(pr, Hm, cap)
        if variant == "unpainted":
            gt["unpainted"] = ~gt["glare"] & ~cv2.dilate((gt["foxing"] | gt["mat_burn"]).astype(np.uint8), np.ones((13, 13))).astype(bool)
            gt["core"] = {k: np.zeros_like(m) for k, m in gt["core"].items()}
        p = IN / f"{variant}_{cname}.jpg"; Image.fromarray(img).save(p, quality=97, subsampling=0)
        rgb, meta = proc._open_working_rgb(p)
        lab = proc._rgb_to_lab(rgb, meta["detected_colorspace"])
        chroma = proc._chroma_from_lab(lab)
        lrc, _ = proc._compute_lrc(lab, chroma)
        for space, feat in (("raw", chroma), ("lrc", lrc)):
            thr, alpha, binary, met = proc._threshold_and_map(feat, space)
            s = evalgt.score(alpha, np.ones(alpha.shape, bool), gt, thr=0.2)
            whole = float((alpha >= 0.2).mean())
            out[f"{variant} {cname} {space}"] = dict(s, whole_frame_shown=whole, space_decoded=meta["detected_colorspace"])
            print(f"{variant:9s} {cname:5s} {space}: frame shown {100*whole:4.1f}% | " + evalgt.fmt(s, keys=("unpainted_shown", "cheeks", "wash", "lips", "foxing")))
json.dump(out, open("out/v40_scores.json", "w"), indent=1)
