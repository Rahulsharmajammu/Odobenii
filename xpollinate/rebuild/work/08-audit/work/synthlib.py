"""synth.py's model (material/scripts/synth.py), unchanged, as functions, so variants can be made.

Same frame, density pattern, paper, tones, colourants, noise law and encoding.  `render` takes its own seed so a
variant is reproducible on its own; `cast` adds a smooth colour cast in linear RGB (uneven light), which synth.py
has no case for.
"""
import numpy as np

H, W = 1200, 1600
yy, xx = np.mgrid[0:H, 0:W]
NEUTRAL, WARM = (1, 1, 1), (0.88, 1.0, 1.18)
BLUE, PINK = (1.0, 0.45, 0.1), (0.1, 0.8, 0.45)


def enc(l):
    l = np.clip(l, 0, 1)
    return np.where(l <= 0.0031308, 12.92 * l, 1.055 * l ** (1 / 2.4) - 0.055)


def density():
    d = 0.1 + 1.5 * xx / W
    d = d + 0.25 * np.sin(yy / 90.0) * np.sin(xx / 130.0)
    d[:, :80] = 0.0
    return np.clip(d, 0, 2.0)


def render(tone, tints=(), paper=(0.86, 0.84, 0.78), noise=0.004, seed=1, cast=None):
    rng = np.random.default_rng(seed)
    d = density()
    od = d[..., None] * np.asarray(tone)[None, None, :]
    truth = np.zeros((H, W), bool)
    for mask, eps, c in tints:
        od = od + mask[..., None] * (c * np.asarray(eps))[None, None, :]
        truth |= mask > 0
    lin = np.asarray(paper) * 10 ** (-od)
    if cast is not None:
        lin = lin * cast
    lin = lin + rng.normal(0, 1, lin.shape) * noise * np.sqrt(np.maximum(lin, 1e-4) / 0.5)
    return np.clip(lin, 0, 1).astype(np.float32), truth


def box(x0, y0, x1, y1):
    m = np.zeros((H, W), np.float32); m[y0:y1, x0:x1] = 1; return m


def vertical_cast(amp=0.03):
    """Linear-RGB gains that run from warm at the top (R up, B down) to cool at the bottom: +-amp."""
    t = (yy / (H - 1)) * 2 - 1          # -1 at top, +1 at bottom
    g = np.ones((H, W, 3), np.float32)
    g[..., 0] = 1 - amp * t
    g[..., 2] = 1 + amp * t
    return g


def to_png8(lin):
    return (enc(lin) * 255 + 0.5).astype(np.uint8)          # RGB uint8, as synth.py writes (before BGR)
