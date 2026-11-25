"""Pictures as files: PNGs for the screen, and exported pictures with their words printed under them."""
from __future__ import annotations

import io
from typing import Optional, Sequence

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import colour, engine


def png(rgb8: np.ndarray, space: str = "srgb", fast: bool = True) -> bytes:
    """An 8-bit RGB array as PNG bytes, tagged with the screen space's profile."""
    buf = io.BytesIO()
    Image.fromarray(rgb8, "RGB").save(buf, format="PNG", icc_profile=colour.screen_icc(space),
                                      compress_level=1 if fast else 6)
    return buf.getvalue()


def _font(size: int):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:                                    # Pillow before 10.1: the fixed bitmap font
        return ImageFont.load_default()


def with_words(rgb8: np.ndarray, title: str, words: Sequence[str] = ()) -> np.ndarray:
    """The picture with a footer: what it is, then its words (that it is a visualisation, not a measurement)."""
    h, w = rgb8.shape[:2]
    size = max(12, min(28, w // 70))
    lines = [title] + (list(words) or [engine.VIS_LABEL])
    foot = int(size * 1.5 * len(lines) + size)
    out = Image.new("RGB", (w, h + foot), (24, 26, 30))
    out.paste(Image.fromarray(rgb8, "RGB"), (0, 0))
    d = ImageDraw.Draw(out)
    f = _font(size)
    for i, line in enumerate(lines):
        d.text((size // 2, h + size // 2 + int(i * size * 1.5)), line, fill=(225, 228, 232) if i == 0 else
               (170, 176, 184), font=f)
    return np.asarray(out)


def whole(an: "engine.Analysis", look: "engine.Look", edge: Optional[int] = None) -> np.ndarray:
    """The whole photograph drawn as ``look`` says, sRGB 8-bit, at ``edge`` px on its long side (None: full size)."""
    s = 1.0 if not edge else min(1.0, edge / max(an.W, an.H))
    ow, oh = max(1, int(round(an.W * s))), max(1, int(round(an.H * s)))
    rows = []
    step = max(1, 4_000_000 // max(1, ow))               # rows per band, to bound memory at full size
    for y0 in range(0, oh, step):
        y1 = min(oh, y0 + step)
        lab = an.picture(look, 0, y0 / s, an.W, (y1 - y0) / s, ow, y1 - y0)
        rows.append(colour.lab_to_screen(lab, "srgb"))
    return np.concatenate(rows, 0)


def exported(an: "engine.Analysis", look: "engine.Look", edge: Optional[int] = None) -> bytes:
    """An exported picture: PNG, sRGB, with its words under it."""
    words = [engine.VIS_LABEL + (f". {engine.BLANK_LABEL}" if look.view == "departs" else "")]
    if look.view in ("boost", "departs") or (look.view == "stretch" and look.tone):
        words.append(engine.RELATIVE_LABEL)
    return png(with_words(whole(an, look, edge), look.describe(), words), "srgb", fast=False)

