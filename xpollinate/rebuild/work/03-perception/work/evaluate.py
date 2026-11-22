"""Score each pipeline on each synthetic scenario against the known truth.

These numbers are the developer's test of the design on synthetic prints; none of them is something the visualiser
would show.  "Shown" means overlay opacity >= 0.2 (v4.1.2's faint tier tops out at 0.4).
"""
from __future__ import annotations

import json
import sys
import time

import numpy as np
from sklearn.metrics import roc_auc_score

import pipelines as PL
import synth

SHOWN = 0.2


def truth_masks(t):
    paint = t["paint"]
    any_paint = np.zeros(t["density"].shape, np.float32)
    for m in paint.values():
        any_paint = np.maximum(any_paint, m)
    unpainted = (any_paint < 0.02) & (t["stain"] < 0.05)
    d = t["density"]
    regions = {"margin": unpainted & t["margin"],
               "light": unpainted & ~t["margin"] & (d < 0.3),
               "mid": unpainted & (d >= 0.3) & (d < 1.0),
               "dark": unpainted & (d >= 1.0)}
    if t["glare"].max() > 0:
        regions["glare"] = unpainted & (t["glare"] > 0.03)
    return any_paint, unpainted, regions


def pooled_dprime(score, core, unpainted, valid, n=200, seed=0):
    """A region-pooled observer that knows the object's shape: the mean score over the object against the mean over
    the same shape moved to unpainted places (at least 98 % unpainted and usable)."""
    ys, xs = np.nonzero(core)
    if len(ys) == 0:
        return np.nan
    h, w = core.shape
    rng = np.random.default_rng(seed)
    y0, x0 = ys.min(), xs.min()
    dy, dx = ys - y0, xs - x0
    H, W = dy.max() + 1, dx.max() + 1
    target = float(np.mean(score[ys, xs]))
    null = []
    tries = 0
    ok_map = unpainted & valid
    while len(null) < n and tries < 20 * n:
        tries += 1
        oy, ox = rng.integers(0, h - H), rng.integers(0, w - W)
        yy, xx = dy + oy, dx + ox
        if ok_map[yy, xx].mean() < 0.98:
            continue
        null.append(float(np.mean(score[yy, xx])))
    if len(null) < 20:
        return np.nan
    null = np.asarray(null)
    return (target - null.mean()) / max(null.std(ddof=1), 1e-9)


def evaluate(res, t):
    any_paint, unpainted, regions = truth_masks(t)
    valid = res["valid"]
    score, op = res["score"], res["opacity"]
    core = any_paint >= 0.5
    rng = np.random.default_rng(0)
    pos = np.flatnonzero((core & valid).ravel())
    neg = np.flatnonzero((unpainted & valid).ravel())
    pos = rng.choice(pos, min(len(pos), 60000), replace=False)
    neg = rng.choice(neg, min(len(neg), 200000), replace=False)
    y = np.r_[np.ones(len(pos)), np.zeros(len(neg))]
    s = np.r_[score.ravel()[pos], score.ravel()[neg]]
    out = {"auc": float(roc_auc_score(y, s)),
           "left_out_share": float(1 - valid.mean()),
           "false_shown": {k: float((op[m & valid] >= SHOWN).mean()) if (m & valid).any() else None
                           for k, m in regions.items()},
           "false_shown_all": float((op[unpainted & valid] >= SHOWN).mean()),
           "objects": {}}
    for name, m in t["paint"].items():
        c = (m >= 0.5)
        cv = c & valid
        out["objects"][name] = {
            "shown": float((op[cv] >= SHOWN).mean()) if cv.any() else None,
            "usable": float(cv.sum() / max(c.sum(), 1)),
            "pooled_d_score": float(pooled_dprime(score, cv, unpainted, valid)),
            "pooled_d_display": float(pooled_dprime(op, cv, unpainted, valid)),
        }
    st = t["stain"] > 0.3
    out["stain_shown"] = float((op[st & valid] >= SHOWN).mean()) if (st & valid).any() else None
    return out


PIPES = {
    "v412_raw": lambda img: PL.run_v412(img, "raw"),
    "v412_lrc": lambda img: PL.run_v412(img, "lrc"),
    "todo": PL.run_todo,
    "proposed": lambda img: PL.run_proposed(img, space="lab"),
    "proposed_logc": lambda img: PL.run_proposed(img, space="logc"),
    "abl_additive_cast": lambda img: PL.run_proposed(img, space="lab", cast_scaled=False),
    "abl_plane_only": lambda img: PL.run_proposed(img, space="lab", spatial=1),
    "abl_no_position": lambda img: PL.run_proposed(img, space="lab", spatial=0),
    "abl_one_scale": lambda img: PL.run_proposed(img, space="lab", scales=(2.0,)),
    "abl_ungated": lambda img: PL.run_proposed(img, space="lab", gated=False, median=0),
    "abl_not_tolerant": lambda img: PL.run_proposed(img, space="lab", tolerant=False),
}


if __name__ == "__main__":
    scen = sys.argv[1].split(",") if len(sys.argv) > 1 else ["scan", "phone", "phone_mixed", "phone_glare",
                                                              "majority", "control", "toned"]
    pipes = sys.argv[2].split(",") if len(sys.argv) > 2 else list(PIPES)
    results = {}
    for sname in scen:
        img, t = synth.scenario(sname)
        results[sname] = {}
        for p in pipes:
            t0 = time.time()
            res = PIPES[p](img)
            ev = evaluate(res, t)
            ev["seconds"] = round(time.time() - t0, 1)
            results[sname][p] = ev
            fs = ev["false_shown"]
            objs = " ".join(f"{k.split(' ')[0][:6]}={v['shown']:.2f}/{v['pooled_d_score']:.0f}"
                            for k, v in ev["objects"].items() if v["shown"] is not None)
            print(f"{sname:12s} {p:18s} auc={ev['auc']:.3f} FA={ev['false_shown_all']:.3f} "
                  + " ".join(f"{k}={v:.3f}" for k, v in fs.items() if v is not None)
                  + f" stain={ev['stain_shown']} | {objs}  ({ev['seconds']}s)", flush=True)
    tag = sys.argv[3] if len(sys.argv) > 3 else "results"
    with open(f"{tag}.json", "w") as f:
        json.dump(results, f, indent=1)
