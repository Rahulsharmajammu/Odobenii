"""Colour conversions used by the experiments (float32, D65, sRGB primaries).

CIELAB is the space the visualiser already uses; Oklab (Ottosson 2020) is tried for the display boost because
CIELAB's constant-hue-angle lines bend for blues (Hung and Berns 1995).
"""
import numpy as np

M_RGB2XYZ = np.array([[0.4124564, 0.3575761, 0.1804375],
                      [0.2126729, 0.7151522, 0.0721750],
                      [0.0193339, 0.1191920, 0.9503041]], np.float32)
M_XYZ2RGB = np.linalg.inv(M_RGB2XYZ).astype(np.float32)
WHITE = np.array([0.95047, 1.0, 1.08883], np.float32)


def srgb_decode(v):
    v = np.asarray(v, np.float32)
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4).astype(np.float32)


def srgb_encode(x):
    x = np.clip(np.asarray(x, np.float32), 0, None)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055).astype(np.float32)


def _f(t):
    d = 6 / 29
    return np.where(t > d ** 3, np.cbrt(t), t / (3 * d * d) + 4 / 29)


def _finv(t):
    d = 6 / 29
    return np.where(t > d, t ** 3, 3 * d * d * (t - 4 / 29))


def lin_to_lab(lin):
    xyz = lin @ M_RGB2XYZ.T / WHITE
    fx, fy, fz = _f(xyz[..., 0]), _f(xyz[..., 1]), _f(xyz[..., 2])
    return np.stack([116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)], -1).astype(np.float32)


def lab_to_lin(lab):
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    fy = (L + 16) / 116
    xyz = np.stack([_finv(fy + a / 500), _finv(fy), _finv(fy - b / 200)], -1) * WHITE
    return (xyz @ M_XYZ2RGB.T).astype(np.float32)


def srgb8_to_lab(rgb8):
    return lin_to_lab(srgb_decode(np.asarray(rgb8, np.float32) / 255.0))


def lab_to_srgb8(lab):
    return np.clip(np.round(srgb_encode(np.clip(lab_to_lin(lab), 0, 1)) * 255), 0, 255).astype(np.uint8)


# -- Oklab (Ottosson 2020) ---------------------------------------------------------------------------------------------
M1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929],
               [0.2119034982, 0.6806995451, 0.1073969566],
               [0.0883024619, 0.2817188376, 0.6299787005]], np.float32)
M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468],
               [1.9779984951, -2.4285922050, 0.4505937099],
               [0.0259040371, 0.7827717662, -0.8086757660]], np.float32)
M2I = np.linalg.inv(M2).astype(np.float32)
M1I = np.linalg.inv(M1).astype(np.float32)


def lin_to_oklab(lin):
    lms = np.cbrt(np.asarray(lin, np.float32) @ M1.T)
    return (lms @ M2.T).astype(np.float32)


def oklab_to_lin(ok):
    lms = (np.asarray(ok, np.float32) @ M2I.T) ** 3
    return (lms @ M1I.T).astype(np.float32)


def in_gamut(lin, tol=1e-4):
    return ((lin >= -tol) & (lin <= 1 + tol)).all(axis=-1)


def max_chroma_oklab(L, h, iters=18):
    """Largest Oklab chroma inside sRGB at lightness L and hue h (radians), by bisection; arrays broadcast."""
    L, h = np.broadcast_arrays(np.asarray(L, np.float32), np.asarray(h, np.float32))
    lo = np.zeros(L.shape, np.float32)
    hi = np.full(L.shape, 0.4, np.float32)
    for _ in range(iters):
        mid = (lo + hi) / 2
        ok = np.stack([L, mid * np.cos(h), mid * np.sin(h)], -1)
        good = in_gamut(oklab_to_lin(ok))
        lo = np.where(good, mid, lo)
        hi = np.where(good, hi, mid)
    return lo


def max_chroma_lab(L, h, iters=18):
    L, h = np.broadcast_arrays(np.asarray(L, np.float32), np.asarray(h, np.float32))
    lo = np.zeros(L.shape, np.float32)
    hi = np.full(L.shape, 160.0, np.float32)
    for _ in range(iters):
        mid = (lo + hi) / 2
        lab = np.stack([L, mid * np.cos(h), mid * np.sin(h)], -1)
        good = in_gamut(lab_to_lin(lab))
        lo = np.where(good, mid, lo)
        hi = np.where(good, hi, mid)
    return lo


# -- colour-vision-deficiency simulation (Machado, Oliveira and Fernandes 2009, severity 1.0, linear RGB) -------------
CVD = {
    "protan": np.array([[0.152286, 1.052583, -0.204868],
                        [0.114503, 0.786281, 0.099216],
                        [-0.003882, -0.048116, 1.051998]], np.float32),
    "deutan": np.array([[0.367322, 0.860646, -0.227968],
                        [0.280085, 0.672501, 0.047413],
                        [-0.011820, 0.042940, 0.968881]], np.float32),
    "tritan": np.array([[1.255528, -0.076749, -0.178779],
                        [-0.078411, 0.930809, 0.147602],
                        [0.004733, 0.691367, 0.303900]], np.float32),
}


def simulate_cvd(rgb8, kind):
    lin = srgb_decode(np.asarray(rgb8, np.float32) / 255.0)
    out = np.clip(lin @ CVD[kind].T, 0, 1)
    return np.clip(np.round(srgb_encode(out) * 255), 0, 255).astype(np.uint8)
