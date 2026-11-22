"""Panel D's decision rule ("one family of hue running smoothly from paper to shadow ... a hue foreign to the paper and
the shadows means the model took paint for the print") against what the model can produce.  Compare D for a split-toned
print with no paint, the same print under an 80 % wash (absorbed), and a single-tone print with and without the wash."""
import sys, json
sys.path.insert(0, "..")
import numpy as np, cv2
from skimage import color
import sim
import synth_engine as E

def chi_to_lab(chi, L):
    c1, c2 = chi[..., 0], chi[..., 1]
    cR = c1 / np.sqrt(2) + c2 / np.sqrt(6); cG = -c1 / np.sqrt(2) + c2 / np.sqrt(6); cB = -2 * c2 / np.sqrt(6)
    Y = color.lab2xyz(np.stack([L, np.zeros_like(L), np.zeros_like(L)], -1))[..., 1]
    es = Y / (0.2126 * np.exp(cR) + 0.7152 * np.exp(cG) + 0.0722 * np.exp(cB))
    lin = np.stack([es * np.exp(cR), es * np.exp(cG), es * np.exp(cB)], -1)
    enc = np.where(lin <= 0.0031308, 12.92 * lin, 1.055 * np.clip(lin, 0, None) ** (1 / 2.4) - 0.055)
    return color.rgb2lab(np.clip(enc, 0, 1))

out, pics = {}, []
for split in (True, False):
    for extensive in (False, True):
        pr = sim.make_print(extensive=extensive, split_tone=split)
        R = pr.R if extensive else pr.R_unpainted
        img, _ = sim.capture(R, sim.UNRULY_A)
        r = E.run_capture(img)
        L = r["F"]["L"]
        lab_ref = chi_to_lab(r["chi_ref"], L)
        u = r["F"]["usable"]
        rows = []
        for lo in range(15, 95, 10):
            m = u & (L >= lo) & (L < lo + 10)
            if m.sum() < 500:
                continue
            a, b = np.median(lab_ref[..., 1][m]), np.median(lab_ref[..., 2][m])
            rows.append((lo + 5, round(float(np.degrees(np.arctan2(b, a))), 1), round(float(np.hypot(a, b)), 2)))
        hues = [h for _, h, _ in rows]
        key = f"{'split-toned' if split else 'single-tone'}, {'wash over 80% (absorbed)' if extensive else 'no paint'}"
        out[key] = dict(curve=rows, hue_span_deg=round(max(hues) - min(hues), 1))
        print(f"{key:44s} hue span {max(hues)-min(hues):5.1f} deg | (L*, hue, chroma): {rows}")
        D = np.stack([L, 4 * lab_ref[..., 1], 4 * lab_ref[..., 2]], -1)
        Drgb = (np.clip(color.lab2rgb(D), 0, 1) * 255).astype(np.uint8)
        Drgb = cv2.resize(Drgb, (360, 360), interpolation=cv2.INTER_AREA)
        bar = np.full((28, 360, 3), 255, np.uint8)
        cv2.putText(bar, key[:52], (4, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1, cv2.LINE_AA)
        pics.append(np.vstack([bar, Drgb]))
cv2.imwrite("d_tell.jpg", cv2.cvtColor(np.hstack(pics), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 90])
json.dump(out, open("d_tell.json", "w"), indent=1)
