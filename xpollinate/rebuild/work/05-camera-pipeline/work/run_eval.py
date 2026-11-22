"""Run every method on every scenario and score it against the ground truth (for this evaluation only)."""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import time
import warnings
from pathlib import Path

import cv2
import numpy as np
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / "vendor"))
sys.path.insert(0, str(HERE))
import visualiser_proto as V  # noqa: E402
from woodii_chroma import chroma as WC  # noqa: E402
from woodii_chroma.render import srgb_decode  # noqa: E402

spec = importlib.util.spec_from_file_location("cd412", HERE / "vendor" / "chroma_diagnoser_v412.py")
CD = importlib.util.module_from_spec(spec)
sys.modules["cd412"] = CD
spec.loader.exec_module(CD)

SCENES = HERE / "scenes"
OUT = HERE / "results"
WORK = 1536                       # working size for a 2048 capture (3000 px for a 4032 px phone frame)
FRAME = 2048
MARGIN = round(0.05 * FRAME)
S_CONTENT = (FRAME - 2 * MARGIN) / 1024

# unpainted picks a user could make (1024 content grid): light backdrop right of the rocket, unpainted suit, dark
# backdrop; and the paper margin as Woodii's base
UNTINTED_1024 = [(910, 10, 1010, 300), (540, 560, 700, 680), (760, 560, 1000, 690)]
BASE_FRAME = [(12, 200, 90, 1800)]


def to_frame(b):
    return tuple(int(round(MARGIN + v * S_CONTENT)) for v in b)


def scale_box(b, s):
    return tuple(int(round(v * s)) for v in b)


def ground_truth(name):
    g = np.load(SCENES / f"{name}_gt.npz")
    rs = lambda a: cv2.resize(np.asarray(a, np.float32), (WORK, WORK), interpolation=cv2.INTER_AREA)  # noqa: E731
    pod = rs(g["paint_od"])
    return {"paint": pod.max(axis=2), "D": rs(g["D"]), "sheen": rs(g["sheen"]), "clear": rs(g["clear"]),
            "faint": rs(g["faint"]), "touch": rs(g["touch"])}


def m_v412(jpg):
    with tempfile.TemporaryDirectory() as tin, tempfile.TemporaryDirectory() as tout:
        cfg = CD.VisualizerConfig(input_dir=tin, output_dir=tout)
        proc = CD.ImageProcessor(cfg)
        rgb, meta = proc._open_working_rgb(jpg)
        lab = proc._rgb_to_lab(rgb, meta["working_colorspace"])
        chroma = proc._chroma_from_lab(lab)
        lrc, _ = proc._compute_lrc(lab, chroma)
        out = {}
        for space, feat in (("raw", chroma), ("lrc", lrc)):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                thr, alpha, binf, _ = proc._threshold_and_map(feat, space)
            score = cv2.resize(feat.astype(np.float32), (WORK, WORK), interpolation=cv2.INTER_AREA)
            shown = cv2.resize(binf.astype(np.float32), (WORK, WORK), interpolation=cv2.INTER_AREA) > 0.5
            out[space] = {"score": score, "shown": shown, "note": f"threshold {thr:.2f}"}
        return out


def m_woodii(jpg):
    rgb8 = V.load_srgb(str(jpg))
    counts = srgb_decode(rgb8 / 255.0).astype(np.float32)
    valid = ~WC.jpeg_mask(counts)
    work, valid = WC.bin_counts(counts, valid, 2)
    unt = [scale_box(to_frame(b), 0.5) for b in UNTINTED_1024]
    base = [scale_box(b, 0.5) for b in BASE_FRAME]
    try:
        res = WC.tint_maps(work, unt, base, valid, smooth_px=0.0, k=WC.DEFAULT_K, edge_shift_px=WC.EDGE_SHIFT_PX / 2,
                           eight_bit=True)
    except WC.ChromaError as exc:
        return {"error": str(exc)}
    z = np.nan_to_num(res["z"], nan=0.0)
    score = cv2.resize(z, (WORK, WORK), interpolation=cv2.INTER_LINEAR)
    shown = cv2.resize(res["flag"].astype(np.uint8), (WORK, WORK), interpolation=cv2.INTER_NEAREST) > 0
    return {"score": score, "shown": shown, "note": f"axis angle {res['record']['axis']['angle_from_neutral_deg']} deg"}


def m_proto(jpg, opts, picks=False, label=""):
    s = WORK / FRAME
    boxes = None
    if picks:
        boxes = [scale_box(to_frame(b), s) for b in UNTINTED_1024] + [scale_box(b, s) for b in BASE_FRAME]
    res = V.run(str(jpg), picks_boxes=boxes, opts=opts, long_edge=WORK)
    z = res["pics"]["z"]
    return {"score": np.nan_to_num(z), "shown": res["pics"]["alpha"] >= 0.5, "res": res, "words": res["words"]}


METHODS = {
    "A_v412_rawC": None, "B_v412_LRC": None, "C_woodii_quicklook": None,
    "D_todo_baseline": V.Options(aniso=False, pool=False, spatial=False, edges=False, scale_q=0.5),
    "E0_edges": V.Options(aniso=False, pool=False, spatial=False, edges=True, scale_q=0.5),
    "E1_aniso": V.Options(aniso=True, pool=False, spatial=False, scale_q=0.5),
    "E2_aniso_pool": V.Options(aniso=True, pool=True, spatial=False, scale_q=0.5),
    "E3_full": V.Options(aniso=True, pool=True, spatial=True, scale_q=0.5),
    "E3_full_picks": V.Options(aniso=True, pool=True, spatial=True, scale_q=0.5),
    "E4_proposed": V.Options(aniso=True, pool=True, spatial=True, scale_q=0.25),
    "E4_proposed_picks": V.Options(aniso=True, pool=True, spatial=True, scale_q=0.25),
}


def score(gt, valid, m):
    s, shown = m["score"], m["shown"]
    unp = (gt["paint"] < 0.004) & (gt["clear"] < 0.02) & (gt["faint"] < 0.02) & (gt["touch"] < 0.02) & valid
    clear = (gt["clear"] > 0.5) & (gt["paint"] > 0.03) & valid
    faint = (gt["faint"] > 0.5) & (gt["paint"] > 0.02) & valid
    touch = (gt["touch"] > 0.5) & valid
    pos = clear | faint | touch
    rng = np.random.default_rng(0)
    ip, iu = np.flatnonzero(pos), np.flatnonzero(unp)
    ip = rng.choice(ip, min(len(ip), 60000), replace=False)
    iu = rng.choice(iu, min(len(iu), 120000), replace=False)
    y = np.r_[np.ones(len(ip)), np.zeros(len(iu))]
    sc = np.r_[s.ravel()[ip], s.ravel()[iu]]
    out = {"AUC": float(roc_auc_score(y, sc))}
    for nm, sel in (("TPR_clear", clear), ("TPR_faint", faint), ("TPR_touch", touch)):
        out[nm] = float(shown[sel].mean()) if sel.any() else float("nan")
    out["FPR_all"] = float(shown[unp].mean())
    D = gt["D"]
    for nm, sel in (("FPR_light", unp & (D < 0.35)), ("FPR_mid", unp & (D >= 0.35) & (D < 1.1)),
                    ("FPR_dark", unp & (D >= 1.1))):
        out[nm] = float(shown[sel].mean()) if sel.any() else float("nan")
    h, w = D.shape
    left = np.zeros_like(unp)
    left[:, : w // 2] = True
    out["FPR_left"] = float(shown[unp & left].mean())
    out["FPR_right"] = float(shown[unp & ~left].mean())
    sheen = unp & (gt["sheen"] > 0.012)
    out["FPR_sheen"] = float(shown[sheen].mean()) if sheen.any() else float("nan")
    return out


def main(scenes, methods):
    OUT.mkdir(exist_ok=True)
    table = {}
    for name in scenes:
        jpg = SCENES / f"{name}.jpg"
        gt = ground_truth(name)
        # common valid set: the proposed masks (glare and near-black), so every method is scored on the same pixels
        rgb = V.working(V.load_srgb(str(jpg)), WORK)
        L, _ = V.to_lab(rgb, 5)
        valid = V.masks(rgb, L)["valid"]
        v412 = m_v412(jpg) if any(m.startswith(("A_", "B_")) for m in methods) else {}
        for meth in methods:
            t = time.time()
            if meth == "A_v412_rawC":
                m = v412["raw"]
            elif meth == "B_v412_LRC":
                m = v412["lrc"]
            elif meth == "C_woodii_quicklook":
                m = m_woodii(jpg)
            else:
                m = m_proto(jpg, METHODS[meth], picks=meth.endswith("picks"))
            if "error" in m:
                table[(name, meth)] = {"error": m["error"]}
                print(name, meth, "ERROR", m["error"], flush=True)
                continue
            sc = score(gt, valid, m)
            sc["words"] = m.get("words", [])
            table[(name, meth)] = sc
            print(f"{name:22s} {meth:20s} AUC {sc['AUC']:.3f} TPRc {sc['TPR_clear']:.2f} TPRf {sc['TPR_faint']:.2f} "
                  f"TPRt {sc['TPR_touch']:.2f} FPR {sc['FPR_all']:.3f} (L {sc['FPR_light']:.3f} M {sc['FPR_mid']:.3f} "
                  f"D {sc['FPR_dark']:.3f} l {sc['FPR_left']:.3f} r {sc['FPR_right']:.3f} sheen {sc['FPR_sheen']:.3f}) "
                  f"{time.time() - t:.0f}s", flush=True)
            if "res" in m:
                np.save(OUT / f"{name}__{meth}__alpha.npy", m["res"]["pics"]["alpha"].astype(np.float16))
                V.montage(m["res"], f"{name} / {meth}", OUT / f"{name}__{meth}.png", scale=0.5)
            else:
                np.save(OUT / f"{name}__{meth}__shown.npy", m["shown"])
    with open(OUT / f"table_{'_'.join(scenes) if len(scenes) < 3 else 'all'}.json", "w") as f:
        json.dump({f"{k[0]}|{k[1]}": v for k, v in table.items()}, f, indent=1)


if __name__ == "__main__":
    sc = sys.argv[1].split(",") if len(sys.argv) > 1 and sys.argv[1] != "all" else sorted(p.stem for p in SCENES.glob("*.jpg"))
    me = sys.argv[2].split(",") if len(sys.argv) > 2 else list(METHODS)
    main(sc, me)
