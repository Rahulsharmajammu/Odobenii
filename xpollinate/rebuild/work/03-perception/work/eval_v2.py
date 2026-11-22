"""Bench for design v2: v1 against votes, the tail-quantile yardstick, both, and the fair TODO.md; thin washes too.

Besides v1's measures, a pooled observer on each picture: for the departure map (C), the region mean of opacity; for
the boosted picture (B), the length of the region mean of the displayed colour vector (a coherent hue survives
averaging, noise does not), each against the same shape moved to unpainted places.  B is tested two ways: v1's cored
soft-knee boost, and an uncored linear x4 boost (the peer's B).
"""
from __future__ import annotations

import json
import sys
import time

import numpy as np

import evaluate as E
import pipelines as PL
import pipelines_v2 as P2
import synth


def pooled_vec(vec, core, ok_null, n=200, seed=0):
    ys, xs = np.nonzero(core)
    if len(ys) == 0:
        return np.nan
    h, w = core.shape
    y0, x0 = ys.min(), xs.min()
    dy, dx = ys - y0, xs - x0
    H, W = dy.max() + 1, dx.max() + 1
    target = float(np.linalg.norm(vec[ys, xs].mean(0)))
    rng = np.random.default_rng(seed)
    null, tries = [], 0
    while len(null) < n and tries < 30 * n:
        tries += 1
        oy, ox = rng.integers(0, h - H), rng.integers(0, w - W)
        yy, xx = dy + oy, dx + ox
        if ok_null[yy, xx].mean() < 0.98:
            continue
        null.append(float(np.linalg.norm(vec[yy, xx].mean(0))))
    if len(null) < 20:
        return np.nan
    null = np.asarray(null)
    return (target - null.mean()) / max(null.std(ddof=1), 1e-9)


def boosted_vectors(res):
    """B's displayed departure: v1's cored soft-knee (unit direction x tanh(max(m - 1.5, 0) / 3.5), m at the finest
    scale), and the uncored linear x4 (the tolerant departure itself, x4)."""
    r = res["fit"]["resid"] if "resid" in res["fit"] else res["ms"][0]["r"]
    r = np.where(res["valid"][..., None], r, 0)
    m = res["ms"][0]["m"]
    if res.get("yardstick") == "p90":
        m = m * 2.146                       # p90 units -> Rayleigh sd units, for the same coring as v1
    n = np.linalg.norm(res["ms"][0]["r"], axis=-1, keepdims=True)
    unit = res["ms"][0]["r"] / np.maximum(n, 1e-6)
    v1 = unit * np.tanh(np.maximum(m - 1.5, 0) / 3.5)[..., None] * res["valid"][..., None]
    return {"B_v1_cored": v1, "B_linear_x4": 4 * r}


def evaluate_all(res, t):
    ev = E.evaluate(res, t)
    any_paint, unpainted, regions = E.truth_masks(t)
    ok_null = unpainted & res["valid"]
    B = boosted_vectors(res)
    for name, m in t["paint"].items():
        core = (m >= 0.5) & res["valid"]
        o = ev["objects"][name]
        for k, vec in B.items():
            o["pooled_" + k] = float(pooled_vec(vec, core, ok_null))
    return ev


CONFIGS = {
    "v1": lambda img: PL.run_proposed(img, space="lab"),
    "votes_rayleigh": lambda img: P2.run_v2(img, votes=True, yardstick="rayleigh"),
    "pixels_p90": lambda img: P2.run_v2(img, votes=False, yardstick="p90"),
    "v2_p90": lambda img: P2.run_v2(img, votes=True, yardstick="p90"),
    "v2": lambda img: P2.run_v2(img, votes=True, yardstick="rayleigh"),
    "v2_high": lambda img: P2.run_v2(img, votes=True, yardstick="p90", preset="high"),
    "todo_fair": PL.run_todo_fair,
    "v2p_14": lambda img: P2.run_v2(img, votes=True, yardstick="p90", ramp=(1.4, 2.6)),
    "v2p_16": lambda img: P2.run_v2(img, votes=True, yardstick="p90", ramp=(1.6, 3.0)),
    "v2p_18": lambda img: P2.run_v2(img, votes=True, yardstick="p90", ramp=(1.8, 3.4)),
}

if __name__ == "__main__":
    scen = sys.argv[1].split(",")
    confs = sys.argv[2].split(",")
    tag = sys.argv[3]
    out = {}
    for s in scen:
        img, t = synth.scenario(s)
        out[s] = {}
        for c in confs:
            t0 = time.time()
            res = CONFIGS[c](img)
            if "fit" not in res:            # todo_fair: give B something to read
                res["fit"] = {"resid": (res["ab"] - res["ref"]).astype(np.float32)}
                res["ms"] = [{"r": res["fit"]["resid"], "m": res["score"]}]
            ev = evaluate_all(res, t)
            ev["seconds"] = round(time.time() - t0, 1)
            out[s][c] = ev
            hits = " ".join(f"{k.split(' (')[0][:7]}={v['shown']:.2f}" for k, v in ev["objects"].items())
            print(f"{s:11s} {c:15s} auc={ev['auc']:.3f} FA={ev['false_shown_all']:.3f} | {hits}", flush=True)
    json.dump(out, open(f"{tag}.json", "w"), indent=1)
