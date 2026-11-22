import sys, numpy as np, cv2
from pathlib import Path
S = Path(sys.argv[1])
H, W = 1200, 1600
rng = np.random.default_rng(1)
yy, xx = np.mgrid[0:H, 0:W]

def enc(l):
    l = np.clip(l, 0, 1)
    return np.where(l <= 0.0031308, 12.92 * l, 1.055 * l ** (1 / 2.4) - 0.055)

def density():
    d = 0.1 + 1.5 * xx / W
    d = d + 0.25 * np.sin(yy / 90.0) * np.sin(xx / 130.0)
    d[:, :80] = 0.0
    return np.clip(d, 0, 2.0)

def render(tone, tints=(), paper=(0.86, 0.84, 0.78), noise=0.004):
    d = density()
    od = d[..., None] * np.asarray(tone)[None, None, :]
    truth = np.zeros((H, W), bool)
    for mask, eps, c in tints:
        od = od + mask[..., None] * (c * np.asarray(eps))[None, None, :]
        truth |= mask > 0
    lin = np.asarray(paper) * 10 ** (-od)
    lin = lin + rng.normal(0, 1, lin.shape) * noise * np.sqrt(np.maximum(lin, 1e-4) / 0.5)
    return np.clip(lin, 0, 1).astype(np.float32), truth

def box(x0, y0, x1, y1):
    m = np.zeros((H, W), np.float32); m[y0:y1, x0:x1] = 1; return m

NEUTRAL, WARM = (1, 1, 1), (0.88, 1.0, 1.18)
BLUE, PINK = (1.0, 0.45, 0.1), (0.1, 0.8, 0.45)
sky = ((xx < 520) & (xx >= 80)).astype(np.float32)
cases = {
 "A_neutral_untinted": render(NEUTRAL),
 "B_warm_untinted": render(WARM),
 "C_warm_blue_wash": render(WARM, [(box(500, 300, 1100, 900), BLUE, 0.06)]),
 "D_warm_sky_painted": render(WARM, [(sky, BLUE, 0.10)]),
 "E_warm_small_touches": render(WARM, [(box(700, 500, 708, 508), PINK, 0.25), (box(900, 500, 930, 530), PINK, 0.25)]),
 "F_warm_strong_pink": render(WARM, [(box(500, 300, 1100, 900), PINK, 0.25)]),
}
for name, (lin, truth) in cases.items():
    cv2.imwrite(str(S / "in_img" / f"{name}.png"), cv2.cvtColor((enc(lin) * 255 + 0.5).astype(np.uint8), cv2.COLOR_RGB2BGR))
    np.save(S / "in" / f"{name}_lin.npy", lin); np.save(S / "in" / f"{name}_truth.npy", truth)
lin = cases["C_warm_blue_wash"][0]
cv2.imwrite(str(S / "in_img" / "G_16bit.tif"), cv2.cvtColor((enc(lin) * 65535 + 0.5).astype(np.uint16), cv2.COLOR_RGB2BGR))
