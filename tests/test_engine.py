"""The analysis on synthetic prints: quiet where unpainted, washes shown, the guards doing what they say.

Synthetic prints encode their author's assumptions; these tests pin behaviour, and the real-capture gate (TODO.md)
decides whether it serves."""
import cv2
import numpy as np
import pytest

import synth
from odobenii import engine

S = engine.Settings()
H, W = 480, 640


def analyse(washes=(), boxes=(), lab=None):
    if lab is None:
        lin, clip, info, masks = synth.make(washes)
    else:
        lin, clip, masks = synth.linear(lab), np.zeros(lab.shape[:2], bool), {}
        info = {"name": "t", "size": [lab.shape[1], lab.shape[0]], "bits": 16, "profile": None, "colour": "",
                "grey_file": False}
    return engine.Analysis(lin, clip, info, S, boxes=boxes), masks


def drawn_chroma(an, look):
    pic = an.picture(look, 0, 0, an.W, an.H, an.W, an.H)
    return np.hypot(pic[..., 1], pic[..., 2])


def test_unpainted_print_stays_quiet():
    an, _ = analyse()
    assert (an.dep_alpha > 0).mean() < 0.002
    Lg = np.arange(30, 85, 3.0)
    assert np.linalg.norm(an.ref(Lg) - synth.tone(Lg), axis=1).max() < 0.2


def test_split_toned_print_stays_quiet():
    """A tone that turns from cool shadows to warm highlights is followed, not flagged."""
    L, _ = synth.scene(H, W, 3)
    t = np.clip((L - 12) / 83, 0, 1)
    rng = np.random.default_rng(4)
    ab = np.stack([2.0 - 2.5 * t, -4.0 + 12.0 * t ** 2], -1) + rng.normal(0, 0.35, L.shape + (2,))
    an, _ = analyse(lab=np.concatenate([L[..., None], ab], -1).astype(np.float32))
    assert (an.dep_alpha > 0).mean() < 0.005


def test_washes_shown_and_nothing_else():
    an, m = analyse((("face", 3.0, 2.0), ("sky", -2.5, -2.5)))
    lit = an.dep_alpha > 0
    assert lit[m["face"]].mean() > 0.9 and lit[m["sky"]].mean() > 0.9
    assert lit[~(m["face"] | m["sky"])].mean() < 0.005


def test_faint_wash_shows_in_the_boost():
    """A 1.4 ΔE wash is below the departure picture's floor, but the boost draws it well above the noise."""
    an, m = analyse((("sky", -1.0, -1.0),))
    assert (an.dep_alpha[m["sky"]] > 0).mean() < 0.05
    C = drawn_chroma(an, engine.Look(view="boost"))
    rest = ~m["sky"] & ~m["face"] & an.valid
    assert C[m["sky"]].mean() > 2.5 * C[rest].mean()


def test_broad_wash_does_not_become_the_reference():
    """The known weak point (B1): a wash over 80 % of the sky.  The clear fifth must not glow in the opposite colour;
    two boxes apart on it make the reference closer still."""
    L, masks = synth.scene(H, W, 0)
    xx = np.mgrid[0:H, 0:W][1] / W
    painted, clear = masks["sky"] & (xx < 0.8), masks["sky"] & (xx >= 0.8)
    lab = synth.lab_print(L, 1, 0.35, [(painted, -2.5, -2.5)])
    Lg = np.arange(80, 89, 2.0)
    for boxes, tol in (((), 0.3), ([[600, 10, 30, 80], [515, 10, 30, 80]], 0.15)):
        an, _ = analyse(lab=lab, boxes=boxes)
        assert np.linalg.norm(an.ref(Lg) - synth.tone(Lg), axis=1).max() < tol
        assert (an.dep_alpha[clear] > 0).mean() < 0.01
        assert (an.dep_alpha[painted] > 0).mean() > 0.9


def test_box_on_paint_is_dropped():
    L, masks = synth.scene(H, W, 0)
    xx = np.mgrid[0:H, 0:W][1] / W
    painted = masks["sky"] & (xx < 0.5)
    lab = synth.lab_print(L, 1, 0.35, [(painted, -3.0, -3.0)])
    an, _ = analyse(lab=lab, boxes=[[600, 10, 30, 80], [450, 10, 30, 80], [100, 10, 30, 80]])
    used = [b.used for b in an.boxes]
    assert used == [True, True, False], [b.note for b in an.boxes]
    assert "disagrees" in an.boxes[2].note


def test_gains_capped_and_strength_kept():
    C = np.diag([1.0, 16.0])                       # four times the spread along one direction
    for cap, ratio in ((True, 2.0), (False, 4.0)):
        s = np.linalg.svd(engine._gains(C, 4.0, cap), compute_uv=False)
        assert s[0] / s[1] == pytest.approx(ratio, rel=1e-6)
        assert np.sqrt(s[0] * s[1]) == pytest.approx(4.0, rel=1e-6)
    an, _ = analyse()
    for emph in engine.EMPHASES:
        s = np.linalg.svd(an.matrix(engine.Look(view="stretch", emphasis=emph)), compute_uv=False)
        assert np.sqrt(s[0] * s[1]) == pytest.approx(4.0, rel=1e-3)
        assert s[0] / s[1] <= 4.0 + 1e-6


def test_guard_one_keeps_the_tone_out():
    """With the print's tone kept (guard 1 off), an unpainted warm print's own toning is stretched into colour."""
    an, _ = analyse()
    on = drawn_chroma(an, engine.Look(view="stretch"))[an.valid].mean()
    off = drawn_chroma(an, engine.Look(view="stretch", tone=False))[an.valid].mean()
    assert off > 1.5 * on


@pytest.mark.parametrize("view", engine.VIEWS)
@pytest.mark.parametrize("space", engine.SPACES)
def test_every_view_draws_any_region(view, space):
    an, _ = analyse((("face", 3.0, 2.0),))
    lk = engine.Look(view=view, space=space)
    for region, size in (((0, 0, W, H), (320, 240)), ((100, 100, 50, 40), (400, 320)), ((-20, -20, 100, 100), (64, 64))):
        pic = an.picture(lk, *region, *size)
        assert pic.shape == (size[1], size[0], 3) and np.isfinite(pic).all()
    with pytest.raises(ValueError):
        an.picture(lk, W + 5, 0, 10, 10, 10, 10)


def test_a_box_needs_a_second_one_elsewhere():
    """A lone box is not used, nor are two side by side, which are one place. Two apart, at the same tones, are."""
    for boxes, used in (([[600, 10, 30, 80]], [False]),
                        ([[600, 10, 30, 80], [570, 10, 25, 80]], [False, False]),
                        ([[600, 10, 30, 80], [450, 10, 30, 80]], [True, True])):
        an, _ = analyse(boxes=boxes)
        assert [b.used for b in an.boxes] == used, [b.note for b in an.boxes]
    an, _ = analyse(boxes=[[600, 10, 30, 80]])
    assert "another part of the print" in an.boxes[0].note


def test_boxes_outside_the_print_area_or_too_small_are_not_used():
    """A margin is unpainted, but it is not the image's tone: boxes outside the drawn print area stay out of the fit."""
    lin, clip, info, _ = synth.make(())
    an = engine.Analysis(lin, clip, info, S, crop=[40, 40, 560, 400],
                         boxes=[[5, 5, 30, 30], [600, 420, 30, 30], [300, 60, 12, 12]])
    notes = [b.note for b in an.boxes]
    assert [b.used for b in an.boxes] == [False, False, False], notes
    assert "outside the print area" in notes[0] and "outside the print area" in notes[1] and "too small" in notes[2]


def test_look_checks_its_values():
    assert engine.Look.parse({"view": "stretch", "cs": "density", "emph": "redgreen", "k": "6", "tone": "0"}).k == 6
    for bad in ({"view": "x"}, {"cs": "rgb"}, {"emph": "x"}, {"k": "40"}, {"k": "nan"}, {"tone": "maybe"}):
        with pytest.raises(ValueError):
            engine.Look.parse(bad)
