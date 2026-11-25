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
    boxes on it make the reference closer still."""
    L, masks = synth.scene(H, W, 0)
    xx = np.mgrid[0:H, 0:W][1] / W
    painted, clear = masks["sky"] & (xx < 0.8), masks["sky"] & (xx >= 0.8)
    lab = synth.lab_print(L, 1, 0.35, [(painted, -2.5, -2.5)])
    Lg = np.arange(80, 89, 2.0)
    for boxes, tol in (((), 0.3), ([[600, 10, 30, 80], [560, 10, 30, 80]], 0.15)):
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


def test_strip_from_the_print_itself():
    """The strip's columns are windows of the print at each tone; tones the print lacks are hatched; the right half of
    each cell carries the wash."""
    an, _ = analyse()
    s = an.strip(engine.Look(view="boost"))
    cell = s.shape[0] // len(engine.STRIP_HUES)
    assert s.shape == (cell * len(engine.STRIP_HUES), cell * len(engine.STRIP_TONES), 3)
    wins = an._strip_windows(2 * cell)
    assert wins[0] is None and wins[-1] is None          # the scene has no surface at L* 15 or 93
    used = [j for j, w in enumerate(wins) if w is not None]
    assert len(used) >= 4
    for j in used:
        blk = s[:cell, j * cell:(j + 1) * cell, 1:]
        left, right = blk[:, : cell // 2].mean((0, 1)), blk[:, cell // 2:].mean((0, 1))
        assert np.linalg.norm(right - left) > 3.0          # 1.3 ΔE x 4, less the residual
        y0, x0 = wins[j]
        assert abs(an.lab[y0:y0 + 2 * cell, x0:x0 + 2 * cell, 0].mean() - engine.STRIP_TONES[j]) <= engine.STRIP_TONE_TOL
    hatched = s[:, :cell]                                  # stripes in the hatched first column
    assert hatched[..., 0].std() > 5.0


def test_strip_shows_the_capture_s_blotches():
    """Low-frequency colour blotches in an unpainted print show in the strip, as they do in the boost. White noise at
    the measured pixel noise could not show them: shift differences cancel them out of that measure."""
    L, _ = synth.scene(H, W, 0)
    rng = np.random.default_rng(9)
    field = cv2.GaussianBlur(rng.normal(0, 1, (H, W, 2)).astype(np.float32), (0, 0), 25)
    field /= field.std()                                   # about 1 ΔE per axis, in soft blotches
    clean = synth.lab_print(L, 1, 0.35)
    blotchy = clean.copy()
    blotchy[..., 1:] += field
    drawn = []
    for lab in (clean, blotchy):
        an, _ = analyse(lab=lab)
        s = an.strip(engine.Look(view="boost"))
        cell = s.shape[0] // len(engine.STRIP_HUES)
        lefts = [s[:cell, j * cell:j * cell + cell // 2, 1:].reshape(-1, 2).mean(0)
                 for j, w in enumerate(an._strip_windows(2 * cell)) if w is not None]
        drawn.append(np.mean([np.hypot(*v) for v in lefts]))   # the unwashed halves' drawn colour
    assert drawn[1] > 1.5 * drawn[0], drawn


def test_look_checks_its_values():
    assert engine.Look.parse({"view": "stretch", "cs": "density", "emph": "redgreen", "k": "6", "tone": "0"}).k == 6
    for bad in ({"view": "x"}, {"cs": "rgb"}, {"emph": "x"}, {"k": "40"}, {"k": "nan"}, {"tone": "maybe"}):
        with pytest.raises(ValueError):
            engine.Look.parse(bad)
