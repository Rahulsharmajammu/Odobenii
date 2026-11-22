"""Cross-bench: the peer's fixed-departure method on my scenes, and my methods on the peer's scenes.

Each side is scored by its own bench's rules: my scenes by elements found (half or more of an element's core shown)
and the share of unpainted pixels shown; the peer's scenes by their bench.masks / bench.score (FC, FCbord, FCglare,
DET by group, AUC).  Evaluation only.  The peer's code is a read-only copy in vendor/peer."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / "vendor" / "peer"))
sys.path.insert(0, str(HERE))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

import sim as PS  # noqa: E402  (peer simulator)
import methods as PM  # noqa: E402  (peer methods)
import bench as PB  # noqa: E402  (peer scoring)
import visualiser_proto as V  # noqa: E402
from score_elements import element_masks  # noqa: E402
from run_eval import ground_truth, WORK, SCENES  # noqa: E402
from gen_scenes import SCENARIOS as MY_SCENES  # noqa: E402

OUT = HERE / "results" / "cross"


def my_margin(n=WORK, width=None, inset=8):
    """The paper margin of my scenes (5 % of the frame), eroded from both sides: a 'paper' box set."""
    w = round(0.05 * n) if width is None else width
    m = np.zeros((n, n), bool)
    m[inset:n - inset, inset:n - inset] = True
    inner = np.zeros((n, n), bool)
    inner[w + inset:n - w - inset, w + inset:n - w - inset] = True
    return m & ~inner


def score_mine(name, shown, valid):
    gt = ground_truth(name)
    els = element_masks(name)
    unp = (gt["paint"] < 0.004) & (gt["clear"] < 0.02) & (gt["faint"] < 0.02) & (gt["touch"] < 0.02) & valid
    per = {k: float(shown[m & valid].mean()) for k, m in els.items() if (m & valid).sum() > 20}
    return {"found": int(sum(v >= 0.5 for v in per.values())), "of": len(per), "FP": float(shown[unp].mean()),
            "per": per}


def peer_on_mine(names, variants=("auto", "margin")):
    rows = {}
    for name in names:
        rgb8 = (V.working(V.load_srgb(str(SCENES / f"{name}.jpg")), WORK) * 255 + 0.5).astype(np.uint8)
        L, _ = V.to_lab(rgb8.astype(np.float32) / 255, 5)
        valid = V.masks(rgb8.astype(np.float32) / 255, L)["valid"]
        p = PM.prepare(rgb8, (0, 0, WORK, WORK))
        for var in variants:
            t = time.time()
            res = PM.m7_fixed(p, light=my_margin() if var == "margin" else None)
            sc = score_mine(name, res["V"], valid)
            rows[f"{name}|peer_fixed_{var}"] = sc
            print(f"{name:20s} peer_fixed_{var:6s} found {sc['found']}/{sc['of']} FP {sc['FP']*100:.1f}% "
                  f"{time.time()-t:.0f}s | " + " ".join(f"{k}:{v:.2f}" for k, v in sc["per"].items()), flush=True)
    return rows


def run_array(rgb8, box=None, opts=V.Options(), picks=None):
    """visualiser_proto.run() from an array (no resizing)."""
    rgb = rgb8.astype(np.float32) / 255.0
    L, ab = V.to_lab(rgb, 5)
    mk = V.masks(rgb, L, box)
    Lb = cv2.GaussianBlur(L.astype(np.float32), (0, 0), V.SIGMA_C)
    gy, gx = np.gradient(Lb)
    ref = V.fit_reference(L, ab, mk["valid"], picks, opts, grad=np.hypot(gx, gy) if opts.edges else None)
    pics = V.render(rgb, L, ab, ref, mk)
    words = V.checks(ref, L, ab, mk, pics["z"])
    return {"rgb": rgb, "L": L, "ab": ab, "masks": mk, "ref": ref, "pics": pics, "words": ref.notes + words}


def mine_on_peer(names, methods):
    rows = {}
    rng = np.random.default_rng(0)
    for name in names:
        s = PS.build(name)
        p = PM.prepare(s["img"], s["box"])
        unp, border, gl, groups = PB.masks(s, p)
        x0, y0, x1, y1 = s["box"]
        for label, fn in methods.items():
            t = time.time()
            res = fn(s, p)
            sc = PB.score({"V": res["V"] & p["judge"], "S": res["S"], "R": res.get("R")}, unp, border, gl, groups, rng)
            rows[f"{name}|{label}"] = sc
            show = {k: round(v, 3) for k, v in sc.items() if isinstance(v, float) and not k.startswith(("R99", "AUC_R"))}
            print(f"{name:16s} {label:22s} {show} {time.time()-t:.0f}s | {res.get('words', '')}", flush=True)
    return rows


def mine_e4(s, p, picks=None):
    x0, y0, x1, y1 = s["box"]
    r = run_array(s["img"], box=(x0, y0, x1, y1), picks=picks)
    z = np.nan_to_num(r["pics"]["z"])
    return {"V": r["pics"]["alpha"] >= 0.5, "S": z, "words": r["words"]}


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    part = sys.argv[1]
    if part == "peer_on_mine":
        rows = peer_on_mine(sys.argv[2].split(",") if len(sys.argv) > 2 else list(MY_SCENES))
    else:
        rows = mine_on_peer(list(PS.SCENARIOS), {"mine_E4_auto": mine_e4})
    json.dump(rows, open(OUT / f"{part}.json", "w"), indent=1)
