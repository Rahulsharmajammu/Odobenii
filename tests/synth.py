"""Synthetic prints for the tests: a warm-toned monochrome photograph whose own tone shifts with density, in pixel
noise, with optional washes.  They encode their author's assumptions; real captures decide (TODO.md, the gate)."""
import numpy as np

from handpaint import colour


def tone(L):
    """The unpainted print's own a*b* at each L*: neutral-ish shadows, warm highlights (a tone that shifts with
    density, which defeated a straight silver axis)."""
    t = np.clip((L - 12.0) / 83.0, 0.0, 1.0)
    return np.stack([0.6 + 1.2 * t, 1.5 + 7.0 * t ** 1.5], -1)


def scene(h=480, w=640, seed=0):
    """L* of a print: a light sky, a mid-tone figure, dark ground, and texture."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w] / np.array([h, w])[:, None, None]
    L = 88.0 - 30.0 * yy                                     # sky to ground
    face = ((xx - 0.35) ** 2 / 0.012 + (yy - 0.42) ** 2 / 0.03) < 1.0
    L = np.where(face, 62.0 + 10.0 * (0.42 - yy), L)
    coat = (np.abs(xx - 0.35) < 0.12) & (yy > 0.6)
    L = np.where(coat, 28.0 + 8.0 * xx, L)
    house = (xx > 0.6) & (xx < 0.9) & (yy > 0.3) & (yy < 0.75)
    L = np.where(house, 45.0 + 20.0 * (xx - 0.6), L)
    L = L + rng.normal(0, 0.6, L.shape)
    return np.clip(L, 9.5, 96.0), {"face": face, "coat": coat, "house": house,
                                    "sky": (yy < 0.25) & ~face & ~house}


def lab_print(L, seed=1, noise=0.35, washes=()):
    """CIELAB of the print, with (mask, da, db) washes added."""
    rng = np.random.default_rng(seed)
    ab = tone(L) + rng.normal(0, noise, L.shape + (2,))
    for mask, da, db in washes:
        ab[mask] += (da, db)
    return np.concatenate([L[..., None], ab], -1).astype(np.float32)


def linear(lab):
    return np.clip(colour.linear_from_lab(lab), 0.0, 1.0)


def make(washes=(), seed=0, h=480, w=640, noise=0.35):
    """(linear ProPhoto, clipped mask, info, masks) for a synthetic print."""
    L, masks = scene(h, w, seed)
    ws = [(masks[name] if isinstance(name, str) else name, da, db) for name, da, db in washes]
    lin = linear(lab_print(L, seed + 1, noise, ws))
    info = {"name": "synthetic", "size": [w, h], "bits": 16, "profile": None, "colour": "synthetic",
            "grey_file": False}
    return lin, np.zeros((h, w), bool), info, masks
