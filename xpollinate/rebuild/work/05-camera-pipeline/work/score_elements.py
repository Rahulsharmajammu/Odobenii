"""Per-element scoring of the saved maps: for each painted element, the share of its core pixels shown; for the
unpainted print, the share shown by tone and in the sheen zone.  Evaluation only (the tool shows no numbers)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from gen_scenes import SCENARIOS  # noqa: E402
from sim_print import layer_mask  # noqa: E402
import visualiser_proto as V  # noqa: E402
from run_eval import ground_truth, WORK, FRAME, SCENES  # noqa: E402

RES = HERE / "results"
METHODS = ["A_v412_rawC", "B_v412_LRC", "C_woodii_quicklook", "D_todo_baseline", "E0_edges", "E2_aniso_pool",
           "E3_full", "E3_full_picks", "E4_proposed", "E4_proposed_picks"]


def element_masks(name):
    ps, _ = SCENARIOS[name]
    m = round(ps.margin * FRAME)
    cn = FRAME - 2 * m
    out = {}
    for layer in ps.layers:
        mk = np.zeros((FRAME, FRAME), np.float32)
        mk[m:m + cn, m:m + cn] = layer_mask(layer, cn)
        out[layer.name] = cv2.resize(mk, (WORK, WORK), interpolation=cv2.INTER_AREA) > 0.7
    return out


def shown_map(name, meth):
    a = RES / f"{name}__{meth}__alpha.npy"
    if a.exists():
        return np.load(a).astype(np.float32) >= 0.5
    s = RES / f"{name}__{meth}__shown.npy"
    return np.load(s) if s.exists() else None


def main():
    table = {}
    for name in SCENARIOS:
        gt = ground_truth(name)
        rgb = V.working(V.load_srgb(str(SCENES / f"{name}.jpg")), WORK)
        L, _ = V.to_lab(rgb, 5)
        valid = V.masks(rgb, L)["valid"]
        els = element_masks(name)
        unp = (gt["paint"] < 0.004) & (gt["clear"] < 0.02) & (gt["faint"] < 0.02) & (gt["touch"] < 0.02) & valid
        for meth in METHODS:
            sh = shown_map(name, meth)
            if sh is None:
                continue
            row = {}
            for el, mk in els.items():
                sel = mk & valid
                row[el] = float(sh[sel].mean()) if sel.sum() > 20 else float("nan")
            D = gt["D"]
            row["FP_all"] = float(sh[unp].mean())
            row["FP_light"] = float(sh[unp & (D < 0.35)].mean())
            row["FP_mid"] = float(sh[unp & (D >= 0.35) & (D < 1.1)].mean())
            row["FP_dark"] = float(sh[unp & (D >= 1.1)].mean())
            sheen = unp & (gt["sheen"] > 0.012)
            row["FP_sheen"] = float(sh[sheen].mean()) if sheen.any() else float("nan")
            table[f"{name}|{meth}"] = row
    json.dump(table, open(RES / "elements.json", "w"), indent=1)
    # print compactly
    for k, row in table.items():
        els = " ".join(f"{e}:{v:.2f}" for e, v in row.items() if not e.startswith("FP"))
        print(f"{k:42s} FP {row['FP_all']:.3f} (L {row['FP_light']:.3f} M {row['FP_mid']:.3f} D {row['FP_dark']:.3f}) | {els}")


if __name__ == "__main__":
    main()
