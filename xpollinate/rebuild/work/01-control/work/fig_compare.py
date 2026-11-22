"""One row per case: the capture, where the paint truly is, and what each method would draw as colour present."""
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
import evaluate as E
rows = ["neg_hard", "portrait", "portrait_heavy", "blue_over_warm", "sky_mixed", "glare_bg"]
cols = [("v1.2", "v1.2"), ("v4.1 C*", "v4.1_Cs"), ("v4.1 LRC", "v4.1_LRC"), ("Woodii, ideal pick", "Woodii_ideal_pick"),
        ("TODO plan", "TODO_plan"), ("Proposed, automatic", "proposed_auto")]
cell = 230
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14) if __import__("os").path.exists("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf") else ImageFont.load_default()
W = cell * (2 + len(cols)); H = 24 + cell * len(rows)
M = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(M)
for j, t in enumerate(["Capture", "Paint (truth)"] + [c[0] for c in cols]):
    d.text((j * cell + 6, 4), t, fill="black", font=font)
for i, n in enumerate(rows):
    c = E.load_case(n)
    img = c["img"].astype(np.float32) / 255
    g = (0.25 + 0.55 * cv2.cvtColor(img, cv2.COLOR_RGB2GRAY))[..., None].repeat(3, 2)
    truth = g.copy(); pm = c["painted"] > 0.3
    truth[pm] = 0.4 * truth[pm] + 0.6 * np.array([0.0, 0.75, 0.9])
    tiles = [img, truth]
    for _, key in cols:
        try:
            a = np.load(f"maps/{n}__{key}.npy").astype(np.float32)
        except FileNotFoundError:
            a = np.zeros(img.shape[:2], np.float32)
        thr = 0.2 if key.startswith("v") else 0.5
        on = a >= thr
        t = g.copy(); t[on] = 0.35 * t[on] + 0.65 * np.array([0.95, 0.1, 0.55])
        tiles.append(t)
    for j, t in enumerate(tiles):
        im = Image.fromarray((np.clip(t, 0, 1) * 255).astype(np.uint8)).resize((cell - 4, cell - 4), Image.LANCZOS)
        M.paste(im, (j * cell + 2, 24 + i * cell + 2))
    d.text((4, 24 + i * cell + 4), n, fill="yellow", font=font)
M.save("fig/compare_methods.png")
print(M.size)
