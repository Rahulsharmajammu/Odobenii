"""Run every estimator on every synthetic case; report where each shows colour on unpainted print (false presence)
and how much visible paint it shows, by region; write a CSV and overlay pictures.  Developer's numbers, not outputs
of the tool."""
from __future__ import annotations

import csv
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

import methods as M
import synth as S

OUT = Path(__file__).resolve().parent
(OUT / "img").mkdir(exist_ok=True)

FULL = {"face": ("skin", 1.0), "hands": ("skin", 1.0), "lips": ("red", 1.0), "backdrop": ("blue", 0.5),
        "plant": ("green", 0.8), "pin": ("gold", 1.0)}
FAINT = {"face": ("skin", 0.35), "hands": ("skin", 0.35), "lips": ("red", 0.5), "backdrop": ("blue", 0.25)}
SKY = {"topthird": ("blue", 0.6), "lips": ("red", 1.0)}
LIGHTBAND = {"lightband": ("pink", 1.2)}
HEAVY = {"face": ("skin", 1.0), "hands": ("skin", 1.0), "backdrop": ("blue", 1.0), "suit": ("blue", 1.2),
         "floor": ("green", 0.9), "plant": ("green", 1.0), "lips": ("red", 1.0), "tie": ("red", 1.0)}

CLEAN = dict(falloff=0.10, gradient=0.0, saturation=1.0, contrast=0.2, jpeg_q=92)
PHONE_WARM = dict(cast_left=(1.0, 0.92, 0.78), cast_right=(1.0, 0.92, 0.78), saturation=1.25, jpeg_q=80)
PHONE_NOWB = dict(cast_left=(1.0, 0.90, 0.72), cast_right=(1.0, 0.90, 0.72), awb="none", saturation=1.2, jpeg_q=75)
MIXED = dict(cast_left=(1.0, 0.88, 0.70), cast_right=(0.90, 0.98, 1.10), gradient=0.2, saturation=1.25, jpeg_q=80)

CASES = [
    # name, recipe, tone, paper, capture, extra
    ("N1 neutral print, clean capture", None, "neutral", "white", CLEAN, {}),
    ("N2 warm print, yellowed paper, phone", None, "warm", "yellowed", PHONE_WARM, {}),
    ("N3 split-toned print, no white balance", None, "split", "yellowed", PHONE_NOWB, {}),
    ("N4 warm print, mixed light", None, "warm", "yellowed", MIXED, {}),
    ("N5 split print, mixed light, glare, mirroring", None, "split", "white", dict(MIXED, glare=0.6),
     {"mirroring": 0.02}),
    ("P1 portrait painted, warm print, phone", FULL, "warm", "yellowed", PHONE_WARM, {}),
    ("P2 faint washes, neutral print, clean", FAINT, "neutral", "white", CLEAN, {}),
    ("P3 portrait painted, split print, mixed light", FULL, "split", "yellowed", MIXED, {}),
    ("P4 painted sky (top), warm print, phone", SKY, "warm", "yellowed", PHONE_WARM, {}),
    ("P5 painted sky (top), warm print, mixed light", SKY, "warm", "yellowed", MIXED, {}),
    ("P6 one wash over every light grey", LIGHTBAND, "warm", "white", PHONE_WARM, {}),
    ("P7 heavily painted, warm print, phone", HEAVY, "warm", "yellowed", PHONE_WARM, {}),
]

REGIONS = ["face", "hands", "lips", "backdrop", "plant", "pin", "suit", "floor", "tie", "topthird", "lightband"]


def truth(case: S.Case):
    """Visible paint: some paint and a colour difference >= 2 a*b* units in the noise-free captures."""
    _, a1, b1 = M.to_lab(case.clean)
    _, a0, b0 = M.to_lab(case.clean_twin)
    dab = np.hypot(a1 - a0, b1 - b0)
    painted = case.amount > 0.02
    visible = painted & (dab >= 2.0)
    unpainted = ~painted & ~case.scene.mount
    return visible, unpainted, dab


def overlay(rgb, alpha, path, title=""):
    L, _, _ = M.to_lab(rgb)
    g = (0.25 + 0.6 * L / 100.0)
    base = np.repeat(g[..., None], 3, 2)
    col = np.array([1.0, 0.1, 0.6], np.float32)
    a = np.clip(alpha, 0, 1)[..., None]
    out = base * (1 - a) + col * a
    im = Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8))
    im.thumbnail((380, 500))
    return im


def run(selected=None, pictures=True):
    rows = []
    t0 = time.time()
    for ci, (name, recipe, tone, paper, capd, extra) in enumerate(CASES):
        if selected and not any(name.startswith(s) for s in selected):
            continue
        cap = S.Capture(seed=10 + ci, **capd)
        case = S.make_case(name, recipe, tone, paper, cap, seed=ci, **extra)
        visible, unpainted, dab = truth(case)
        p = M.prep(case.rgb)
        results = M.m0_m1(case.rgb)
        box = ~case.scene.mount                      # the TODO's 'optional object box', here exact
        results.append(M.m2_todo(p, mask=box, name="M2 TODO fallback"))
        results.append(M.m2_todo(p, plane=True, mask=box, name="M2p TODO + plane"))
        results.append(M.m3_proposed(p, name="M3 no box"))
        results.append(M.m3_proposed(p, mask=box, name="M3 proposed"))
        results.append(M.m3_proposed(p, mask=box, ring_plane=True, name="M3r + ring cast"))
        results.append(M.m3_proposed(p, mask=box, ring_plane=True, deg=3, name="M3r cubic"))
        tiles = [Image.fromarray((np.clip(case.rgb, 0, 1) * 255).astype(np.uint8))]
        tiles[0].thumbnail((380, 500))
        for r in results:
            shown = (r.alpha >= 0.5)
            ev = p.usable & ~case.scene.mount
            fp = float((shown & unpainted & ev).sum() / max((unpainted & ev).sum(), 1))
            tp = float((shown & visible & ev).sum() / max((visible & ev).sum(), 1)) if visible.any() else float("nan")
            reg = {}
            for rg in REGIONS:
                m = case.scene.regions.get(rg)
                if m is None:
                    if rg in S.REGION_FNS:
                        m = S.REGION_FNS[rg](case.scene)
                    else:
                        continue
                vm = visible & (m > 0.5) & ev
                if vm.sum() > 30:
                    reg[rg] = float((shown & vm).sum() / vm.sum())
            row = {"case": name, "method": r.name, "false_presence": round(fp, 4),
                   "paint_shown": None if np.isnan(tp) else round(tp, 3),
                   "regions": "; ".join(f"{k} {v:.2f}" for k, v in reg.items()),
                   "warnings": " | ".join(r.warnings)}
            if "cant_tell" in r.info:
                ct = r.info["cant_tell"] | r.info["unsure_colour"]
                row["unsure_on_unpainted"] = round(float((ct & unpainted & ev).sum() / max((unpainted & ev).sum(), 1)), 3)
                row["unsure_on_paint"] = (round(float((ct & visible & ev).sum() / max((visible & ev).sum(), 1)), 3)
                                          if visible.any() else None)
                row["missed_but_unsure"] = (round(float((r.info["cant_tell"] & visible & ev).sum()
                                                        / max((visible & ev & ~shown).sum(), 1)), 3)
                                            if visible.any() else None)
            if "share_on_curve" in r.info:
                row["share_on_curve"] = round(r.info["share_on_curve"], 3)
            for k in ("split_left to right", "split_top to bottom", "agree_span"):
                if k in r.info:
                    row[k] = round(r.info[k], 2)
            rows.append(row)
            tiles.append(overlay(case.rgb, r.alpha, None))
            extra_s = (f" | unsure: unp {row['unsure_on_unpainted']} missed-covered {row['missed_but_unsure']}"
                       if "unsure_on_unpainted" in row else "")
            print(f"{name[:44]:44s} | {r.name:24s} | FP {fp:6.3f} | TP {tp:5.2f}{extra_s} | {row['regions'][:70]}"
                  f"{' | W: ' + row['warnings'] if row['warnings'] else ''}", flush=True)
        # truth tile
        tt = overlay(case.rgb, visible.astype(np.float32), None)
        tiles.insert(1, tt)
        if pictures:
            w = sum(t.width for t in tiles) + 6 * len(tiles)
            h = max(t.height for t in tiles)
            sheet = Image.new("RGB", (w, h), "white")
            x = 0
            for t in tiles:
                sheet.paste(t, (x, 0)); x += t.width + 6
            sheet.save(OUT / "img" / f"bench_{name.split()[0]}.png")
    keys = sorted({k for r in rows for k in r}, key=lambda k: ["case", "method", "false_presence", "paint_shown",
                                                             "regions", "warnings"].index(k) if k in
                  ["case", "method", "false_presence", "paint_shown", "regions", "warnings"] else 99)
    with open(OUT / "bench_results.csv", "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=keys)
        wr.writeheader()
        for r in rows:
            wr.writerow(r)
    print(f"done in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    run(sys.argv[1:] or None)
