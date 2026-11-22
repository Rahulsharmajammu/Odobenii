"""Experiment 3: would other reasonable choices have changed the favoured result, or the rejected one?

Feature code is pickref.py's `feat` (copied, floor made a parameter) and evalcmp.py's `vec_feature`; the
visualiser is cd41 = Chroma_diagnoser_v4.1 at cfbf66c, default settings, via its own functions.
Scores: % of painted pixels flagged / % of unpainted pixels flagged (as evalcmp.py and pickref.py print them).

A. Same PNGs as the prior work: threshold, reference size and placement, and a pick-free reference.
B. New images from synth.py's model: JPEG q85, a +-3% colour cast, a wash that runs into the reference rows.
C. The visualiser default on pink washes of six sizes (the "more paint, less shown" claim).
"""
import sys, warnings, numpy as np, cv2
from pathlib import Path
W_ = Path(__file__).resolve().parent
S = W_ / "S"
sys.path.insert(0, str(S / "scripts")); sys.path.insert(0, str(W_))
import cd41, synthlib as L
warnings.simplefilter("ignore")
OUT = W_ / "exp3_img"; OUT.mkdir(exist_ok=True)


def feat(lab, ref, floor=0.3):                      # pickref.py:4-15, floor a parameter
    Lc = lab[..., 0]; idx = np.clip(Lc.astype(int), 0, 99)
    med = np.full((100, 2), np.nan); sd = np.full(100, np.nan)
    for b in range(100):
        m = (idx == b) & ref
        if m.sum() < 50: continue
        ab = lab[m][:, 1:]; med[b] = np.median(ab, axis=0)
        sd[b] = max(1.4826 * np.median(np.linalg.norm(ab - med[b], axis=1)), floor)
    ok = np.isfinite(sd); x = np.arange(100)
    for j in range(2): med[:, j] = np.interp(x, x[ok], med[ok, j])
    sd = np.interp(x, x[ok], sd[ok])
    return np.linalg.norm(lab[..., 1:] - med[idx], axis=-1) / sd[idx]


def feat_robust(lab, rounds=5, k=3.0, floor=0.3):
    """No picks: start from the whole image (as evalcmp.py), then drop pixels beyond k spreads and refit, `rounds`
    times; bands are interpolated as in pickref.py.  The TODO's 'automatic fallback' (TODO.md:35), in its simplest form."""
    ref = np.ones(lab.shape[:2], bool)
    for _ in range(rounds):
        z = feat(lab, ref, floor)
        ref = z < k
    return feat(lab, ref, floor)


def presence(z, thr=3.0, med=5):
    z = np.clip(z, 0, 50).astype(np.float32)
    if med: z = cv2.medianBlur(z, med)
    return z > thr


def score(m, truth):
    return (m[truth].mean() * 100 if truth.any() else float("nan"), m[~truth].mean() * 100)


def fmt(hf):
    h, f = hf
    return ("  nan" if np.isnan(h) else f"{h:5.1f}") + f"/{f:5.2f}"


def lab_of_png(path):
    rgb = cv2.cvtColor(cv2.imread(str(path)), cv2.COLOR_BGR2RGB).astype(np.float32) / 255   # as pickref.py:18
    return cd41._custom_rgb_to_lab(rgb, "sRGB")


def visualiser_default(path, truth):
    cfg = cd41.VisualizerConfig(input_dir=OUT, output_dir=W_ / "exp_tmp")
    p = cd41.ImageProcessor(cfg)
    rgb, meta = p._open_working_rgb(Path(path))
    lab = p._rgb_to_lab(rgb, meta["working_colorspace"])
    chroma = p._chroma_from_lab(lab); lrc, _ = p._compute_lrc(lab, chroma)
    out = {}
    for space, f in (("raw", chroma), ("lrc", lrc)):
        _, _, mask, _ = p._threshold_and_map(f, space)
        out[space] = score(mask > 0, truth)
    return out


def pick(boxes, margin=True):
    r = np.zeros((L.H, L.W), bool)
    if margin: r[:, :80] = True
    for x0, y0, x1, y1 in boxes: r[y0:y1, x0:x1] = True
    return r


cases = ["A_neutral_untinted", "B_warm_untinted", "C_warm_blue_wash", "D_warm_sky_painted",
         "E_warm_small_touches", "F_warm_strong_pink"]

# ---------------------------------------------------------------- A
print("A. Same PNGs.  Each cell: % painted flagged / % unpainted flagged")
printed_ref = {}
for n in cases:
    r = np.zeros((L.H, L.W), bool)
    if "sky" in n: r[:, 600:] = True; r[:, :80] = True
    else: r[950:, :] = True; r[:, :80] = True
    printed_ref[n] = r
three_boxes = [(150, 1000, 250, 1100), (750, 1000, 850, 1100), (1350, 1000, 1450, 1100)]
three_boxes_sky = [(650, 100, 750, 200), (1000, 600, 1100, 700), (1400, 1000, 1500, 1100)]
variants = [
    ("A1 as printed: hand region, thr 3, floor 0.3", lambda n, lab: presence(feat(lab, printed_ref[n]))),
    ("A2 same region, thr 4 (evalcmp's)", lambda n, lab: presence(feat(lab, printed_ref[n]), thr=4)),
    ("A3 whole image as reference, thr 3", lambda n, lab: presence(feat(lab, np.ones(lab.shape[:2], bool)))),
    ("A4 margin strip only (paper)", lambda n, lab: presence(feat(lab, pick([])))),
    ("A5 margin + three 100x100 boxes", lambda n, lab: presence(feat(lab, pick(three_boxes_sky if "sky" in n else three_boxes)))),
    ("A6 no picks: robust refit, 5 rounds", lambda n, lab: presence(feat_robust(lab))),
]
print(f"{'variant':44s} " + " ".join(f"{c[2:16]:>14s}" for c in cases))
print(f"{'  reference share of frame (A1)':44s} " + " ".join(f"{printed_ref[c].mean()*100:13.1f}%" for c in cases))
labs = {n: lab_of_png(S / "in_img" / f"{n}.png") for n in cases}
truths = {n: np.load(S / "in" / f"{n}_truth.npy") for n in cases}
for label, fn in variants:
    print(f"{label:44s} " + " ".join(f"{fmt(score(fn(n, labs[n]), truths[n])):>14s}" for n in cases))

# ---------------------------------------------------------------- B
print("\nB. New images from synth.py's model")
sky = ((L.xx < 520) & (L.xx >= 80)).astype(np.float32)
defs = {
    "B_warm_untinted": (L.WARM, []),
    "C_warm_blue_wash": (L.WARM, [(L.box(500, 300, 1100, 900), L.BLUE, 0.06)]),
    "D_warm_sky_painted": (L.WARM, [(sky, L.BLUE, 0.10)]),
    "E_warm_small_touches": (L.WARM, [(L.box(700, 500, 708, 508), L.PINK, 0.25), (L.box(900, 500, 930, 530), L.PINK, 0.25)]),
    "F_warm_strong_pink": (L.WARM, [(L.box(500, 300, 1100, 900), L.PINK, 0.25)]),
}
rows = []
for n, (tone, tints) in defs.items():
    lin, truth = L.render(tone, tints, seed=11)
    # B1 JPEG q85, 4:2:0
    p = OUT / f"{n}_q85.jpg"
    params = [cv2.IMWRITE_JPEG_QUALITY, 85]
    if hasattr(cv2, "IMWRITE_JPEG_SAMPLING_FACTOR"):
        params += [cv2.IMWRITE_JPEG_SAMPLING_FACTOR, cv2.IMWRITE_JPEG_SAMPLING_FACTOR_420]
    cv2.imwrite(str(p), cv2.cvtColor(L.to_png8(lin), cv2.COLOR_RGB2BGR), params)
    lab = lab_of_png(p)
    ref = printed_ref.get(n, printed_ref["B_warm_untinted"])
    v = visualiser_default(p, truth)
    rows.append(("B1 JPEG q85 4:2:0", n, v["raw"], v["lrc"], score(presence(feat(lab, ref)), truth),
                 score(presence(feat_robust(lab)), truth)))
    # B2 +-3% colour cast (top warm, bottom cool), PNG
    lin_c, truth_c = L.render(tone, tints, seed=11, cast=L.vertical_cast(0.03))
    p = OUT / f"{n}_cast3.png"
    cv2.imwrite(str(p), cv2.cvtColor(L.to_png8(lin_c), cv2.COLOR_RGB2BGR))
    lab = lab_of_png(p)
    v = visualiser_default(p, truth_c)
    rows.append(("B2 +-3% vertical cast", n, v["raw"], v["lrc"], score(presence(feat(lab, ref)), truth_c),
                 score(presence(feat_robust(lab)), truth_c)))
# B3: the faint blue wash runs on into the bottom rows the hand-chosen reference used
lin_x, truth_x = L.render(L.WARM, [(L.box(500, 300, 1100, 1200), L.BLUE, 0.06)], seed=11)
p = OUT / "C_wash_into_reference.png"
cv2.imwrite(str(p), cv2.cvtColor(L.to_png8(lin_x), cv2.COLOR_RGB2BGR))
lab = lab_of_png(p); v = visualiser_default(p, truth_x)
rows.append(("B3 wash runs into rows 950+", "C_warm_blue_wash", v["raw"], v["lrc"],
             score(presence(feat(lab, printed_ref["C_warm_blue_wash"])), truth_x), score(presence(feat_robust(lab)), truth_x)))
# B3b: same, the strong pink
lin_x, truth_x = L.render(L.WARM, [(L.box(500, 300, 1100, 1200), L.PINK, 0.25)], seed=11)
p = OUT / "F_wash_into_reference.png"
cv2.imwrite(str(p), cv2.cvtColor(L.to_png8(lin_x), cv2.COLOR_RGB2BGR))
lab = lab_of_png(p); v = visualiser_default(p, truth_x)
rows.append(("B3 wash runs into rows 950+", "F_warm_strong_pink", v["raw"], v["lrc"],
             score(presence(feat(lab, printed_ref["F_warm_strong_pink"])), truth_x), score(presence(feat_robust(lab)), truth_x)))
print(f"{'variant':30s} {'case':22s} {'vis raw':>12s} {'vis LRC':>12s} {'hand ref A1':>12s} {'no picks A6':>12s}")
for r in rows:
    print(f"{r[0]:30s} {r[1]:22s} {fmt(r[2]):>12s} {fmt(r[3]):>12s} {fmt(r[4]):>12s} {fmt(r[5]):>12s}")

# ---------------------------------------------------------------- C
print("\nC. Visualiser default on the strong pink (F's colourant and strength), six wash sizes, centred as F")
print(f"{'paint % of frame':>16s} {'vis raw':>12s} {'vis LRC':>12s}")
for side in (98, 196, 310, 438, 600, 759):
    x0, y0 = 800 - side // 2, 600 - side // 2
    lin_s, truth_s = L.render(L.WARM, [(L.box(x0, y0, x0 + side, y0 + side), L.PINK, 0.25)], seed=11)
    p = OUT / f"F_side{side}.png"
    cv2.imwrite(str(p), cv2.cvtColor(L.to_png8(lin_s), cv2.COLOR_RGB2BGR))
    v = visualiser_default(p, truth_s)
    print(f"{truth_s.mean()*100:16.2f} {fmt(v['raw']):>12s} {fmt(v['lrc']):>12s}")
