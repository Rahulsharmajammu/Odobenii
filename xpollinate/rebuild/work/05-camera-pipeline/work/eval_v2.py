"""Score design v2 on both benches (my scenes: elements found / unpainted shown; the peer's: their bench.score)."""
from __future__ import annotations
import json, sys, time
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / "vendor" / "peer")); sys.path.insert(0, str(HERE))
import numpy as np
import sim as PS, methods as PM, bench as PB
import visualiser_proto as V
import proto_v2 as P2
from cross_bench import my_margin, score_mine
from run_eval import WORK, SCENES
from gen_scenes import SCENARIOS as MY

VARIANTS = {
    "v2_chi_auto": dict(opt=P2.Opt2(space="chi"), paper=False, box=False),
    "v2_lab_auto": dict(opt=P2.Opt2(space="lab"), paper=False, box=False),
    "v2_chi_margin": dict(opt=P2.Opt2(space="chi"), paper=True, box=False),
    "v2_chi_margin_box": dict(opt=P2.Opt2(space="chi"), paper=True, box=True),
}


def on_mine(names, variants):
    rows = {}
    for name in names:
        rgb8 = (V.working(V.load_srgb(str(SCENES / f"{name}.jpg")), WORK) * 255 + 0.5).astype(np.uint8)
        for vn in variants:
            cfg = VARIANTS[vn]
            if cfg["box"]:
                continue                     # no unpainted-box helper for my scenes
            t = time.time()
            out = P2.run2(rgb8, cfg["opt"], paper=my_margin() if cfg["paper"] else None)
            shown = out["pr"]["alpha"] >= 0.5
            sc = score_mine(name, shown, out["masks"]["valid"])
            sc["notes"] = out["ref"].notes
            rows[f"{name}|{vn}"] = sc
            print(f"{name:20s} {vn:18s} found {sc['found']}/{sc['of']} FP {sc['FP']*100:.1f}% {time.time()-t:.0f}s | "
                  + " ".join(f"{k[:6]}:{v:.2f}" for k, v in sc["per"].items()) + f" | {out['ref'].notes}", flush=True)
    return rows


def on_peer(names, variants):
    rows = {}
    rng = np.random.default_rng(0)
    for name in names:
        s = PS.build(name)
        p = PM.prepare(s["img"], s["box"])
        unp, border, gl, groups = PB.masks(s, p)
        for vn in variants:
            cfg = VARIANTS[vn]
            t = time.time()
            out = P2.run2(s["img"], cfg["opt"], box=s["box"], paper=PB.border_picks(s) if cfg["paper"] else None,
                          picks=PB.unpainted_box(s) if cfg["box"] else None)
            pr = out["pr"]
            sc = PB.score({"V": (pr["alpha"] >= 0.5) & p["judge"], "S": pr["d"] / pr["T"], "R": pr["d"]},
                          unp, border, gl, groups, rng)
            sc["notes"] = out["ref"].notes
            rows[f"{name}|{vn}"] = sc
            show = {k: round(v, 3) for k, v in sc.items() if isinstance(v, float) and not k.startswith(("R99", "AUC_R"))}
            print(f"{name:16s} {vn:18s} {show} {time.time()-t:.0f}s | {out['ref'].notes}", flush=True)
    return rows


if __name__ == "__main__":
    which = sys.argv[1]
    variants = sys.argv[2].split(",") if len(sys.argv) > 2 else list(VARIANTS)
    rows = on_mine(list(MY), variants) if which == "mine" else on_peer(list(PS.SCENARIOS), variants)
    (HERE / "results" / "cross").mkdir(parents=True, exist_ok=True)
    json.dump(rows, open(HERE / "results" / "cross" / f"v2_{which}_{'_'.join(variants)}.json", "w"), indent=1, default=str)
