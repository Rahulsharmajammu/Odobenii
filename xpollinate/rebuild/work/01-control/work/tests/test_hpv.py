"""Tests of the prototype on synthetic prints and captures built from a model the visualiser does not share
(tone that shifts with density, yellowed paper, auto white balance, phone tone curve, JPEG 4:2:0, lateral colour).
Shares are used here only to test the code; the tool itself shows none."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hpv  # noqa: E402
import synth as S  # noqa: E402

SIZE = 700


def run(scene="astronaut", paints=(), cap=None, print_kw=None, **kw):
    ps = S.PrintSpec(scene=scene, size=SIZE, **(print_kw or {}))
    refl0, _ = S.make_print(ps, [])
    h, w = refl0.shape[:2]
    reg = S.scene_regions(scene, w, h)
    plist, masks = [], {}
    for region, paint, amount in paints:
        m = S.soft(reg[region], 3.0)
        plist.append(S.Paint(paint, m, amount))
        masks[region] = m
    refl, _ = S.make_print(ps, plist)
    img, box, _ = S.capture(refl, cap or S.CaptureSpec())
    return img, box, masks


def shown(res, mask):
    return float((res["opacity"][mask] >= 0.5).mean())


def bare_mask(img, masks, box=None):
    import cv2
    m = np.ones(img.shape[:2], bool)
    for v in masks.values():
        m &= cv2.dilate((v >= 0.01).astype(np.uint8), np.ones((17, 17), np.uint8)) == 0     # 8 px clear of paint
    if box is not None:
        x0, y0, x1, y1 = box
        inside = np.zeros_like(m)
        inside[y0:y1, x0:x1] = True
        m &= inside
    import cv2
    L = cv2.cvtColor(img.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)[..., 0]
    return m & (L > 12) & (L < 95) & ~(img >= 250).any(2)


def test_unpainted_neutral_print_shows_almost_nothing_and_warns_of_nothing():
    img, _, _ = run(print_kw=dict(paper=(0.88, 0.87, 0.85), tone_hi=(1, 1, 1), tone_lo=(1, 1, 1), yellowing=0,
                                  foxing=0))
    res = hpv.analyse(img.astype(np.float32) / 255)
    assert shown(res, res["valid"]) < 0.05
    assert res["warnings"] == []


def test_unpainted_warm_print_under_a_uniform_cast_shows_almost_nothing():
    img, _, _ = run(cap=S.CaptureSpec(awb="none", cast=(1.15, 1.0, 0.8)), print_kw=dict(foxing=0))
    res = hpv.analyse(img.astype(np.float32) / 255)
    assert shown(res, res["valid"]) < 0.06


def test_a_wash_and_small_touches_are_shown():
    img, _, masks = run(paints=[("skin", "flesh", 0.16), ("lips", "lips", 0.3), ("badge", "gold", 0.35)],
                        print_kw=dict(foxing=0))
    res = hpv.analyse(img.astype(np.float32) / 255)
    core = {k: (v > 0.8) for k, v in masks.items()}
    assert shown(res, core["skin"]) > 0.6
    assert shown(res, core["lips"]) > 0.8 and shown(res, core["badge"]) > 0.6
    assert shown(res, bare_mask(img, masks)) < 0.06


def test_a_blue_wash_that_lowers_chroma_on_a_warm_print_is_shown():
    img, _, masks = run(paints=[("patch", "blue", 0.15)],
                        cap=S.CaptureSpec(awb="none"), print_kw=dict(tone_hi=(0.85, 1.0, 1.25)))
    res = hpv.analyse(img.astype(np.float32) / 255)
    core = masks["patch"] > 0.8
    assert shown(res, core) > 0.5
    hue = np.degrees(np.arctan2(*res["d_ab"][core][:, ::-1].T)) % 360
    assert 180 < np.median(hue) < 300                     # drawn as a blue departure, though its chroma fell


def test_a_cast_across_the_frame_is_followed_and_said():
    img, _, _ = run(cap=S.CaptureSpec(gradient=((1.15, 1.0, 0.75), (0.92, 1.0, 1.10))), print_kw=dict(foxing=0))
    res = hpv.analyse(img.astype(np.float32) / 255)
    assert shown(res, res["valid"]) < 0.06
    assert any("light changes across the frame" in w for w in res["warnings"])


def test_paint_along_one_side_is_not_taken_for_uneven_light():
    img, _, masks = run(paints=[("flag_red", "rouge", 0.3), ("flag_blue", "blue", 0.3), ("bg", "blue", 0.07)])
    res = hpv.analyse(img.astype(np.float32) / 255)
    assert not any("light changes across the frame" in w for w in res["warnings"])


def test_a_wash_over_most_of_the_light_tones_is_flagged_and_a_bare_box_brings_it_out():
    img, _, masks = run(scene="camera", paints=[("sky", "blue", 0.06)])
    rgb = img.astype(np.float32) / 255
    auto = hpv.analyse(rgb)
    sky = masks["sky"] > 0.8
    assert shown(auto, sky) < 0.2                          # taken for bare print: the most common colour there
    assert any("halves of the print disagree" in w and "lighter" in w for w in auto["warnings"])
    # the user marks bare areas: a light, a middle and a dark one (found here from the truth, as a user would by eye)
    import cv2
    L = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)[..., 0]
    bare = cv2.erode(((masks["sky"] < 0.01) & (L < 95)).astype(np.uint8), np.ones((17, 17), np.uint8)) > 0
    boxes = []
    for lo, hi in ((72, 95), (40, 60), (12, 30)):
        ys, xs = np.nonzero(bare & (L > lo) & (L < hi))
        i = len(ys) // 2
        boxes.append([int(xs[i]) - 8, int(ys[i]) - 8, int(xs[i]) + 8, int(ys[i]) + 8])
    picked = hpv.analyse(rgb, picks=boxes)
    assert picked["ref"].source == "picked"
    assert shown(picked, sky) > 2 * shown(auto, sky) + 0.15


def test_the_print_is_found_on_a_table():
    img, box, _ = run(paints=[("skin", "flesh", 0.16)], cap=S.CaptureSpec(background="wood", border=0.12))
    found = hpv.find_print(img.astype(np.float32) / 255)
    assert found is not None
    x0, y0, x1, y1 = box
    inside = np.zeros(found.shape, bool)
    inside[y0:y1, x0:x1] = True
    assert found[inside].mean() > 0.95 and found[~inside].mean() < 0.15
