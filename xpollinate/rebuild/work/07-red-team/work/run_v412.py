"""The current script (4.1.2) on synthetic captures: its own internals, at full resolution."""
import importlib.util, sys, json
from pathlib import Path
import numpy as np, cv2
from PIL import Image
import sim, evalgt

spec = importlib.util.spec_from_file_location("v412", str(Path(__file__).with_name("v412.py")))
v = importlib.util.module_from_spec(spec); sys.modules["v412"] = v; spec.loader.exec_module(v)

IN = Path("in_v412"); OUT = Path("out_v412"); IN.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True)
cfg = v.VisualizerConfig(input_dir=IN, output_dir=OUT, output_scale=1.0)
proc = v.ImageProcessor(cfg)


def run(img_u8, name):
    path = IN / f"{name}.jpg"
    Image.fromarray(img_u8).save(path, quality=97, subsampling=0)   # near-lossless re-save of the capture
    rgb, meta = proc._open_working_rgb(path)
    lab = proc._rgb_to_lab(rgb, meta["working_colorspace"])
    chroma = proc._chroma_from_lab(lab)
    lrc, _ = proc._compute_lrc(lab, chroma)
    res = {}
    for space, feat in (("raw", chroma), ("lrc", lrc)):
        thr, alpha, binary, metrics = proc._threshold_and_map(feat, space)
        res[space] = (alpha, metrics)
    return res, rgb


if __name__ == "__main__":
    rows = []
    for variant in ("normal", "extensive", "unpainted"):
        pr = sim.make_print(extensive=(variant == "extensive"))
        R = pr.R_unpainted if variant == "unpainted" else pr.R
        for cname, cap in (("clean", sim.CLEAN), ("A", sim.UNRULY_A), ("B", sim.UNRULY_B)):
            img, Hm = sim.capture(R, cap)
            gt = evalgt.gt_in_capture(pr, Hm, cap)
            if variant == "unpainted":     # nothing is painted: every pixel away from glare and deterioration is 'unpainted'
                gt["unpainted"] = ~gt["glare"] & ~cv2.dilate((gt["foxing"] | gt["mat_burn"]).astype(np.uint8), np.ones((13, 13))).astype(bool)
                gt["core"] = {k: np.zeros_like(m) for k, m in gt["core"].items()}
            res, rgb = run(img, f"{variant}_{cname}")
            usable = np.ones(img.shape[:2], bool)
            for space in ("raw", "lrc"):
                alpha, met = res[space]
                s = evalgt.score(alpha, usable, gt, thr=0.4)
                rows.append((variant, cname, space, met["threshold"], s))
                print(f"{variant:9s} {cname:5s} {space:3s} thr={met['threshold']:6.2f} | " + evalgt.fmt(s), flush=True)
    json.dump([(a, b, c, d, e) for a, b, c, d, e in rows], open("out/v412_scores.json", "w"), indent=1)
