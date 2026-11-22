"""Run the methods on synthetic uncontrolled captures and score them against the simulator's truth.

Scores are for this comparison only (the tool reports nothing numeric):
* clean: share of judgeable, unpainted pixels away from edges and known deterioration where colour is shown;
* per nuisance (foxing, adhesive, mirroring, glare, edges, semantic, yellowed edges): share shown;
* per medium: share of its pixels shown.
"Shown" is opacity >= 0.2 (visible) and >= 0.5 (plain).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

import methods as M
import proposal as PR
import hpv_proto as HP
import sim

OUT = Path(__file__).resolve().parent / "bench_out"
OUT.mkdir(exist_ok=True)

BASE_CAP = dict(gradient=0.0, vignette=0.0, glare=0.0, hotspot=False, ca=0.0, sharpen=0.0, jpeg=85)
FULL_CAP = dict(gradient=1.0, vignette=1.0, glare=0.10, hotspot=True, ca=0.0015, sharpen=0.6, jpeg=80)
AGED = dict(yellowing=1.0, foxing=25, adhesive=True, mirroring=1.0)

CASES = {
    "U0_neutral_clean":   (dict(tone="neutral"), BASE_CAP),
    "U1_warm":            (dict(tone="warm"), BASE_CAP),
    "U2_warm_aged":       (dict(tone="warm", **AGED), BASE_CAP),
    "U3_warm_capture":    (dict(tone="warm"), FULL_CAP),
    "U4_warm_aged_capture": (dict(tone="warm", **AGED), FULL_CAP),
    "U5_sepia_landscape_capture": (dict(content="camera", tone="sepia", **AGED), FULL_CAP),
    "P1_portrait_warm":   (dict(tone="warm", paint="portrait"), BASE_CAP),
    "P2_portrait_aged_capture": (dict(tone="warm", paint="portrait", **AGED), FULL_CAP),
    "P3_heavy_aged_capture": (dict(tone="warm", paint="heavy", **AGED), FULL_CAP),
    "P4_landscape_sepia_capture": (dict(content="camera", tone="sepia", paint="landscape", **AGED), FULL_CAP),
    "P5_portrait_semantic": (dict(tone="warm", paint="portrait", **AGED), dict(FULL_CAP, semantic_skin=3.0)),
    "U6_unpainted_semantic": (dict(tone="warm", **AGED), dict(FULL_CAP, semantic_skin=3.0)),
    "P6_portrait_table":  (dict(tone="warm", paint="portrait", **AGED), dict(FULL_CAP, table=True)),
}

# unpainted picks, in 512-content coordinates (x0, y0, x1, y1); "margin" is special (the paper border)
PICKS_ASTRO = [(110, 20, 150, 80), (60, 420, 120, 500), (180, 25, 240, 55), (385, 285, 500, 335), "margin"]
PICKS_CAMERA = [(20, 300, 80, 400), (380, 10, 470, 60), (300, 120, 380, 165), "margin"]
BAD_PICK = (320, 120, 360, 200)      # over the faint blue backdrop wash


def to_px(boxes, po: sim.PrintOpts, pad=0):
    s = po.size
    b = int(round(po.border * s))
    k = s / 512.0
    out = []
    for bx in boxes:
        if bx == "margin":
            out.append((pad + int(0.15 * b), pad + b + int(0.2 * s), pad + int(0.85 * b), pad + b + int(0.8 * s)))
        else:
            x0, y0, x1, y1 = bx
            out.append((pad + int(b + x0 * k), pad + int(b + y0 * k), pad + int(b + x1 * k), pad + int(b + y1 * k)))
    return out


def score(alpha, truth, judge):
    paint = np.zeros(alpha.shape, bool)
    for k, m in truth.items():
        if k.startswith("paint_"):
            paint |= m
    paint_d = cv2.dilate(paint.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    nuis = np.zeros(alpha.shape, bool)
    for k in ("foxing", "adhesive", "mirroring", "glare", "hotspot", "semantic", "table"):
        if k in truth:
            nuis |= truth[k]
    nuis_d = cv2.dilate(nuis.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    edge = truth["edge"]
    inprint = truth["image_area"] | truth["border"]
    clean = judge & inprint & ~paint_d & ~nuis_d & ~edge
    if "yellowing_edge" in truth:
        clean &= ~truth["yellowing_edge"]
    out = {}
    for thr in (0.2, 0.5):
        r = {"clean": float((alpha[clean] >= thr).mean()) if clean.any() else None}
        e = judge & inprint & edge & ~paint_d & ~nuis_d
        r["edges"] = float((alpha[e] >= thr).mean()) if e.any() else None
        for k in ("foxing", "adhesive", "mirroring", "glare", "semantic", "yellowing_edge", "table"):
            if k in truth:
                m = truth[k] & judge & ~paint_d
                if k == "yellowing_edge":
                    m &= ~nuis_d & ~edge
                r[k] = float((alpha[m] >= thr).mean()) if m.sum() > 50 else None
        for k, m in truth.items():
            if k.startswith("paint_"):
                mm = m & judge
                r[k] = float((alpha[mm] >= thr).mean()) if mm.sum() > 20 else None
        out[f"shown>={thr}"] = r
    return out


def montage(panels, labels, path, strip=None, words=()):
    h = max(p.shape[0] for p in panels)
    ims = [cv2.resize(p, (int(p.shape[1] * h / p.shape[0]), h)) if p.shape[0] != h else p for p in panels]
    row = np.concatenate(ims, axis=1)
    pieces = [row]
    if strip is not None:
        s = cv2.resize(strip, (row.shape[1] // 2, strip.shape[0]), interpolation=cv2.INTER_NEAREST)
        pad = np.full((strip.shape[0], row.shape[1] - s.shape[1], 3), 255, np.uint8)
        pieces.append(np.concatenate([s, pad], axis=1))
    img = Image.fromarray(np.concatenate(pieces, axis=0))
    from PIL import ImageDraw
    foot = Image.new("RGB", (img.width, 30 + 22 * (len(words) + 1)), "white")
    d = ImageDraw.Draw(foot)
    x = 0
    for lab, p in zip(labels, ims):
        d.text((x + 10, 6), lab, fill="black")
        x += p.shape[1]
    for i, w in enumerate(words):
        d.text((10, 28 + 22 * i), w[:220], fill="black")
    out = Image.new("RGB", (img.width, img.height + foot.height), "white")
    out.paste(img, (0, 0))
    out.paste(foot, (0, img.height))
    out.thumbnail((2400, 2400))
    out.save(path)


def main(only=None):
    results = {}
    for name, (pk, ck) in CASES.items():
        if only and name not in only:
            continue
        t0 = time.time()
        po = sim.PrintOpts(**pk)
        refl, gray, truth = sim.make_print(po)
        co = sim.CaptureOpts(**ck)
        u8, truth = sim.capture(refl, truth, co, face_center=sim.face_ellipse(po))
        Image.fromarray(u8).save(OUT / f"{name}_capture.png")
        pad = int(0.22 * refl.shape[0]) if co.table else 0
        L, a, b = PR.lab_planes(u8)
        clipped, dark, _ = PR.masks(u8, L)
        judge = ~clipped & ~dark
        res = {}
        alphas = {}
        alphas["v41_raw"] = M.v41(u8, "raw")
        alphas["v41_lrc"] = M.v41(u8, "lrc")
        alphas["todo"], _ = M.todo_plan(u8, plane=False)
        alphas["todo_plane"], _ = M.todo_plan(u8, plane=True)
        alphas["first_try_auto"] = PR.run(u8, checks=False).alpha
        r_auto = HP.run(u8)
        alphas["prop_auto"] = r_auto.alpha
        alphas["prop_auto_high"] = HP.run(u8, sensitivity="high", checks=False).alpha
        alphas["prop_auto_fine_only"] = HP.run(u8, two_scales=False, checks=False).alpha
        alphas["prop_auto_no_plane"] = HP.run(u8, plane=False, checks=False).alpha
        alphas["prop_auto_no_edge_term"] = HP.run(u8, edge_term=False, checks=False).alpha
        boxes = to_px(PICKS_CAMERA if po.content == "camera" else PICKS_ASTRO, po, pad)
        r_pick = HP.run(u8, picks=boxes)
        alphas["prop_picks"] = r_pick.alpha
        warn = {"prop_auto": r_auto.warnings, "prop_picks": r_pick.warnings}
        if po.content == "astronaut":
            bad = to_px(PICKS_ASTRO + [BAD_PICK], po, pad)
            r_bad = HP.run(u8, picks=bad)
            alphas["prop_badpick"] = r_bad.alpha
            warn["prop_badpick"] = r_bad.warnings
        if co.table:
            H, W = u8.shape[:2]
            box = (pad, pad, W - pad, H - pad)
            r_box = HP.run(u8, box=box)
            alphas["prop_auto_box"] = r_box.alpha
            warn["prop_auto_box"] = r_box.warnings
        for m, al in alphas.items():
            res[m] = score(al, truth, judge)
        res["warnings"] = warn
        res["seconds"] = round(time.time() - t0, 1)
        results[name] = res
        B, C, D = HP.render(r_auto)
        montage([u8, B, C, D], ["A Capture", "B Print's own tone neutralised (x4)", "C Where colour departs (automatic)",
                                "D Expected unpainted, own tone x4"],
                OUT / f"{name}_proposal_auto.png", HP.tone_strip(r_auto.ref, 600), r_auto.warnings)
        B, C, D = HP.render(r_pick)
        montage([u8, B, C, D], ["A Capture", "B Neutralised (picks)", "C Departs (picks)", "D Expected unpainted (picks)"],
                OUT / f"{name}_proposal_picks.png", HP.tone_strip(r_pick.ref, 600), r_pick.warnings)
        if po.content == "astronaut":
            B, C, D = HP.render(r_bad)
            montage([u8, B, C, D], ["A Capture", "B Neutralised (one bad pick)", "C Departs", "D Expected unpainted"],
                    OUT / f"{name}_proposal_badpick.png", HP.tone_strip(r_bad.ref, 600), r_bad.warnings)
        grey = cv2.cvtColor(cv2.cvtColor(u8, cv2.COLOR_RGB2GRAY), cv2.COLOR_GRAY2RGB).astype(np.float32) * 0.6
        panels = []
        for m in ("v41_raw", "v41_lrc", "todo", "prop_auto"):
            al = alphas[m][..., None]
            panels.append(np.round(grey * (1 - al) + np.array([255, 40, 160]) * al).astype(np.uint8))
        montage(panels, ["4.1.2 raw C*ab", "4.1.2 LRC", "TODO as written", "Refined (automatic)"],
                OUT / f"{name}_compare.png")
        print(name, res["seconds"], "s", flush=True)
    with open(OUT / "scores.json", "w") as f:
        json.dump(results, f, indent=1)
    return results


if __name__ == "__main__":
    main(sys.argv[1:] or None)
