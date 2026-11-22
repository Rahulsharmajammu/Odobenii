"""The report's figures, with the final settings (CIELAB, normal preset)."""
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_dilation
import synth, pipelines as PL, render as R, colour as C

def save(a, p):
    Image.fromarray(a).save(p)

S, PAD = synth.S, synth.PAD
def box(x0, y0, x1, y1, shape):
    m = np.zeros(shape, bool); m[PAD + S * y0:PAD + S * y1, PAD + S * x0:PAD + S * x1] = True; return m

# 1. four-panel montages
for s in ("phone_mixed", "control", "phone_glare", "toned", "scan"):
    img, t = synth.scenario(s)
    res = PL.run_proposed(img, space="lab")
    save(R.four_panel(img, res), f"figs/final_{s}.png")
    save(R.key_strip(res), f"figs/key_{s}.png")
    print(s, R.footer_words(res), flush=True)
    if s == "phone_mixed":
        a, b = R.blink_frames(res)
        R.save_blink("figs/blink_phone_mixed.png", a, b, 0.5)
        resmix = res; imgmix = img

# 2. the majority-painted print: automatic, then three boxes
img, t = synth.scenario("majority")
shape = img.shape[:2]
picks = box(240, 345, 256, 430, shape) | box(208, 66, 248, 84, shape) | box(105, 300, 135, 335, shape)
for name, pk in (("auto", None), ("boxes", picks)):
    res = PL.run_proposed(img, space="lab", picks=pk)
    m = R.four_panel(img, res, picked=pk is not None)
    if pk is not None:   # outline the boxes on the Presence panel
        pass
    save(m, f"figs/final_majority_{name}.png")
    a, b = R.blink_frames(res)
    R.save_blink(f"figs/blink_majority_{name}.png", a, b, 0.5)
    crop = (slice(60, 620), slice(250, 900))
    pair = np.concatenate([a[crop], np.full((560, 12, 3), 255, np.uint8), b[crop]], 1)
    save(np.asarray(Image.fromarray(pair).resize((pair.shape[1] // 2, pair.shape[0] // 2), Image.LANCZOS)),
         f"figs/blinkpair_majority_{name}.png")
    print("majority", name, R.footer_words(res, pk is not None), flush=True)

# 3. the versions side by side on the mixed-light capture
mod, proc = PL.v412()
img, res = imgmix, resmix
rgb = img.astype(np.float32) / 255.0
panels, titles = [img], ["Original (phone, mixed light)"]
for space, title in (("raw", "v4.1.2 Segmented, raw C*ab"), ("lrc", "v4.1.2 Segmented, LRC")):
    r = PL.run_v412(img, space)
    vis = np.asarray(proc._create_segmented_visual(rgb, r["opacity"]))
    panels.append(vis); titles.append(title)
td = PL.run_todo(img)
# TODO.md's presence map as specified: the print in grey, colour over it with hue from the vector's angle
Lok = R.lightness_ok({"L": td["L"]})
d = td["ab"] - td["ref"]
lab = np.stack([np.full(Lok.shape, 60, np.float32), d[..., 0] * 4, d[..., 1] * 4], -1)
okd = C.lin_to_oklab(np.clip(C.lab_to_lin(lab), 1e-6, None))
h = np.arctan2(okd[..., 2], okd[..., 1])
cm = C.max_chroma_oklab(Lok, h)
fg = R.oklch(Lok, 0.9 * cm, h)
bg = R.oklch(Lok, np.zeros_like(Lok), np.zeros_like(Lok))
a_ = td["opacity"][..., None]
panels.append(R.ok_to_srgb8(bg * (1 - a_) + fg * a_)); titles.append("TODO.md presence map, as specified")
panels.append(R.presence_picture(res)); titles.append("Proposed Presence")
save(R.montage(panels, titles, scale=0.4, cols=5), "figs/versions_phone_mixed.png")

# 4. colour-vision deficiency: TODO-style isoluminant overlay vs proposed Presence, face crop, simulated deutan
crop = (slice(180, 470), slice(330, 760))
todo_pic = panels[3][crop]; prop_pic = panels[4][crop]
rows = []
for kind in (None, "deutan", "protan"):
    a1 = todo_pic if kind is None else C.simulate_cvd(todo_pic, kind)
    a2 = prop_pic if kind is None else C.simulate_cvd(prop_pic, kind)
    rows.append(np.concatenate([a1, np.full((a1.shape[0], 10, 3), 255, np.uint8), a2], 1))
    rows.append(np.full((10, rows[-1].shape[1], 3), 255, np.uint8))
cvd = np.concatenate(rows[:-1], 0)
im = Image.fromarray(cvd)
W = Image.new("RGB", (im.width + 170, im.height), "white"); W.paste(im, (170, 0))
dd = ImageDraw.Draw(W); f = R.font(18)
for i, lab_ in enumerate(("normal", "deuteranope", "protanope")):
    dd.text((6, i * (todo_pic.shape[0] + 10) + todo_pic.shape[0] // 2), lab_, fill="black", font=f)
save(np.asarray(W), "figs/cvd_face.png")
print("done")
