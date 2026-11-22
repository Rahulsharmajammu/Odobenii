"""Run every method on every case; score against the ground truth (for design work only: the tool shows no numbers).

FP: share of bare print (8 px from any paint, L* 12-95, not clipped, not a foxing stain) drawn as colour present.
Detection: share of each paint's core drawn as colour present.
"""
from __future__ import annotations

import json
import pickle
import sys
import time
from pathlib import Path

import cv2
import numpy as np

import hpv
import old_methods as OM
import todo_method as TM

HERE = Path(__file__).resolve().parent


def load_case(name):
    with open(HERE / "cases" / f"{name}.pkl", "rb") as f:
        return pickle.load(f)


def eval_masks(c):
    img = c["img"]
    lab = cv2.cvtColor(img.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)
    L = lab[..., 0]
    clipped = (img >= 250).any(2)
    painted = cv2.dilate((c["painted"] > 0.01).astype(np.uint8), np.ones((17, 17), np.uint8)) > 0
    fox = cv2.dilate(c["foxing"].astype(np.uint8), np.ones((13, 13), np.uint8)) > 0
    judge = (L >= 12) & (L <= 95) & ~clipped
    bare = c["inside"] & ~painted & ~fox & judge
    cores = {}
    for key, (m, _) in c["paint_masks"].items():
        core = cv2.erode((m > 0.8).astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
        core &= judge
        if core.sum() > 50:
            cores[key] = core
    return L, bare, cores


def auto_picks(c, L, bare, n=4, size=None, seed=0):
    """An idealised user's boxes on bare print: four boxes wholly on bare print, from the darkest to the lightest
    tone the bare print offers."""
    h, w = L.shape
    size = size or max(20, int(0.025 * max(h, w)))
    ok = cv2.erode(bare.astype(np.uint8), np.ones((size, size), np.uint8)) > 0
    ys, xs = np.nonzero(ok[size // 2:h - size // 2:4, size // 2:w - size // 2:4])
    if len(ys) == 0:
        return []
    ys, xs = ys * 4 + size // 2, xs * 4 + size // 2
    Lc = L[ys, xs]
    boxes = []
    for q in (3, 35, 65, 97):
        t = np.percentile(Lc, q)
        i = int(np.argmin(np.abs(Lc - t)))
        y, x = ys[i], xs[i]
        boxes.append((int(x - size // 2), int(y - size // 2), int(x + size // 2), int(y + size // 2)))
    return boxes


def score(res, L, bare, cores, inside):
    a = res["alpha"]
    t = res.get("presence_at", 0.5)
    on = a >= t
    out = {"FP": float(on[bare].mean()) if bare.any() else None}
    for nm, sel in (("FP_dark", L < 35), ("FP_mid", (L >= 35) & (L < 70)), ("FP_light", L >= 70)):
        m = bare & sel
        out[nm] = float(on[m].mean()) if m.sum() > 500 else None
    out["det"] = {k: float(on[m].mean()) for k, m in cores.items()}
    if "show" in res:
        out["unjudged_bare"] = float((~res["show"][bare]).mean())
    return out


def run(names, methods, save_maps=True):
    results = {}
    for n in names:
        c = load_case(n)
        L, bare, cores = eval_masks(c)
        results[n] = {"desc": c["desc"]}
        picks = auto_picks(c, L, bare)
        for m in methods:
            t0 = time.time()
            if m == "v1.2":
                res = OM.v12(c["img"])
            elif m == "v4.1 C*":
                res = OM.v41(c["img"], "raw")
            elif m == "v4.1 LRC":
                res = OM.v41(c["img"], "lrc")
            elif m == "Woodii (ideal pick)":
                um = cv2.erode(bare.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
                res = OM.woodii(c["img"], um)
            elif m == "Woodii (3 boxes)":
                um = np.zeros(L.shape, bool)
                for x0, y0, x1, y1 in picks:
                    um[y0:y1, x0:x1] = True
                res = OM.woodii(c["img"], um)
            elif m == "TODO plan":
                res = TM.todo(c["img"])
            elif m == "proposed (auto)":
                res = hpv.analyse(c["img"].astype(np.float32) / 255, run_checks=True)
            elif m == "proposed (auto, no tilt)":
                res = hpv.analyse(c["img"].astype(np.float32) / 255, spatial=False, run_checks=False)
            elif m == "proposed (3 boxes)":
                res = hpv.analyse(c["img"].astype(np.float32) / 255, picks=picks, run_checks=True)
            elif m == "proposed (auto, print box)":
                x0, y0, x1, y1 = c["box"]
                res = hpv.analyse(c["img"].astype(np.float32) / 255, box=c["box"], run_checks=True)
            else:
                raise ValueError(m)
            if "error" in res:
                results[n][m] = {"error": res["error"]}
                print(f"{n:16s} {m:26s} ERROR {res['error'][:90]}")
                continue
            s = score(res, L, bare, cores, c["inside"])
            s["time"] = round(time.time() - t0, 1)
            if "warnings" in res:
                s["warnings"] = res["warnings"]
            results[n][m] = s
            det = " ".join(f"{k}={v:.2f}" for k, v in s["det"].items())
            fp = lambda v: "  -  " if v is None else f"{v:.3f}"  # noqa: E731
            print(f"{n:16s} {m:26s} FP={fp(s['FP'])} (d {fp(s['FP_dark'])} m {fp(s['FP_mid'])} "
                  f"l {fp(s['FP_light'])})  {det}  [{s['time']}s]")
            if save_maps:
                np.save(HERE / "maps" / f"{n}__{m.replace(' ', '_').replace('(', '').replace(')', '').replace('*', 's').replace(',', '')}.npy",
                        np.clip(res["alpha"], 0, 1).astype(np.float16))
            if "warnings" in res and res["warnings"]:
                for wtxt in res["warnings"]:
                    print(f"{'':43s}! {wtxt[:150]}")
    return results


if __name__ == "__main__":
    (HERE / "maps").mkdir(exist_ok=True)
    names = sys.argv[1].split(",") if len(sys.argv) > 1 and sys.argv[1] != "all" else __import__("cases").CASES
    methods = sys.argv[2].split(";") if len(sys.argv) > 2 else [
        "v1.2", "v4.1 C*", "v4.1 LRC", "Woodii (ideal pick)", "Woodii (3 boxes)", "TODO plan", "proposed (auto)",
        "proposed (3 boxes)"]
    res = run(names, methods)
    out = HERE / "results.json"
    old = json.loads(out.read_text()) if out.exists() else {}
    for k, v in res.items():
        old.setdefault(k, {}).update(v)
    out.write_text(json.dumps(old, indent=1))
