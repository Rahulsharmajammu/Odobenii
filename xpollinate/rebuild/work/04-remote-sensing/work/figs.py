"""Figures for the report: what the proposal's four panels look like when the reference is right and when it is
wrong, on the synthetic captures."""
from __future__ import annotations

import json
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import audit as A
import bench
import methods as M
import sim

FONT = None
for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",):
    try:
        FONT = ImageFont.truetype(f, 15)
    except OSError:
        pass
FONT = FONT or ImageFont.load_default()


def tile(img01, label, w=430):
    im = Image.fromarray((np.clip(img01, 0, 1) * 255).astype(np.uint8))
    im = im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)
    canvas = Image.new("RGB", (im.width, im.height + 24), "white")
    canvas.paste(im, (0, 24))
    ImageDraw.Draw(canvas).text((4, 3), label, fill="black", font=FONT)
    return np.asarray(canvas)


def row(tiles, gap=6):
    h = max(t.shape[0] for t in tiles)
    tiles = [np.pad(t, ((0, h - t.shape[0]), (0, gap), (0, 0)), constant_values=255) for t in tiles]
    return np.concatenate(tiles, 1)


def stack(rows, gap=10, title=None):
    w = max(r.shape[1] for r in rows)
    rows = [np.pad(r, ((0, gap), (0, w - r.shape[1]), (0, 0)), constant_values=255) for r in rows]
    out = np.concatenate(rows, 0)
    if title:
        head = Image.new("RGB", (out.shape[1], 30), "white")
        ImageDraw.Draw(head).text((6, 6), title, fill="black", font=FONT)
        out = np.concatenate([np.asarray(head), out], 0)
    return out


def outline(img, mask, colour=(0.0, 0.9, 0.9)):
    import cv2
    m = mask.astype(np.uint8)
    edge = cv2.morphologyEx(m, cv2.MORPH_GRADIENT, np.ones((5, 5), np.uint8)).astype(bool)
    out = img.copy()
    out[edge] = colour
    return out


def panels(s, p, res, label, picks=None, margin=None, gain=4.0):
    x0, y0, x1, y1 = s["box"]
    c = lambda a: a[y0:y1, x0:x1]
    pres = M.presence_picture(p, res["S"], res["resid"], ramp=res.get("ramp", (3.0, 6.0)))
    if picks is not None:
        pres = outline(pres, picks)
    if margin is not None:
        pres = outline(pres, margin, (0.9, 0.9, 0.0))
    return row([tile(c(p["rgb"]), f"{label}: original"),
                tile(c(M.boost_picture(p, res, gain)), "boost: substrate neutral, x4"),
                tile(c(pres), "presence"),
                tile(c(M.reference_picture(p, res, gain)), "reference: taken as unpainted, x4")])


def truth_tile(s):
    x0, y0, x1, y1 = s["box"]
    t = np.zeros(s["paint_any"].shape + (3,))
    t[s["paint_any"]] = 1
    t[(s["glare"] > 0.03) & ~s["paint_any"]] = (0.4, 0.4, 0.9)
    return tile(t[y0:y1, x0:x1], "truth: paint white, glare blue")


def fixed(p, **kw):
    r = M.m7_fixed(p, **kw)
    r["ramp"] = (1.0, 2.5)
    return r


def main(out_dir):
    notes = {}
    # Figure 1: painted backdrop, automatic vs margin + one unpainted box
    s = sim.build("P2_backdrop")
    p = M.prepare(s["img"], s["box"])
    marg = bench.border_picks(s)
    box = bench.unpainted_box(s)
    r_auto = fixed(p)
    r_pk = fixed(p, light=marg, picks=box)
    notes["P2 auto"] = A.two_colours(p, r_auto)
    notes["P2 margin+box"] = A.two_colours(p, r_pk, margin=marg, picks=box)
    fig = stack([panels(s, p, r_auto, "automatic"), panels(s, p, r_pk, "margin + 1 box", box, marg),
                 row([truth_tile(s)])],
                title="P2: a blue wash over a third of the backdrop, face wash, lips; split-toned print, mixed light, glare")
    Image.fromarray(fig).save(f"{out_dir}/fig_P2_backdrop.jpg", quality=88)

    # Figure 2: fully hand-coloured
    s = sim.build("P3_full")
    p = M.prepare(s["img"], s["box"])
    marg = bench.border_picks(s)
    import cv2
    # what an operator would box as unpainted here: the shuttle body (clear of the glare) and the dark collar edge
    box = np.zeros_like(marg)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))
    near = cv2.dilate(s["paint_any"].astype(np.uint8), k).astype(bool)
    sh = s["regions"]["shuttle"] & ~near & (s["glare"] < 0.01) & p["judge"]
    ys, xs = np.nonzero(sh)
    for cy in np.percentile(ys, [20, 75]).astype(int):
        cx = int(np.median(xs[np.abs(ys - cy) < 30]))
        b = np.zeros_like(marg)
        b[cy - 40:cy + 40, cx - 25:cx + 25] = True
        box |= b & sh
    r_auto = fixed(p)
    r_pk = fixed(p, light=marg, picks=box)
    notes["P3 auto"] = A.two_colours(p, r_auto)
    notes["P3 margin+box"] = A.two_colours(p, r_pk, margin=marg, picks=box)
    fig = stack([panels(s, p, r_auto, "automatic"), panels(s, p, r_pk, "margin + 2 boxes", box, marg),
                 row([truth_tile(s)])],
                title="P3: fully hand-coloured (65 % of the image painted); unpainted: shuttle, blacks, margin")
    Image.fromarray(fig).save(f"{out_dir}/fig_P3_full.jpg", quality=88)

    # Figure 3: unpainted, split-toned print under mixed light: TODO plan vs proposal
    s = sim.build("N3_split_mixed")
    p = M.prepare(s["img"], s["box"])
    r3 = M.m3_todo(p, plane=True)
    r7 = fixed(p)
    notes["N3 auto"] = A.two_colours(p, r7)
    x0, y0, x1, y1 = s["box"]
    c = lambda a: a[y0:y1, x0:x1]
    # the TODO plan's presence: opacity from 2 to 5 spreads; its residual in a*b* shown as hue
    lab_res = np.stack(r3["resid"], -1) / 60.0
    pres3 = M.presence_picture(p, r3["S"], lab_res @ np.array([[1, 0], [0, 1]]), ramp=(2.0, 5.0))
    fig = stack([row([tile(c(p["rgb"]), "unpainted print: original"),
                      tile(c(pres3), "TODO plan + plane (auto, 2 to 5 spreads)"),
                      tile(c(M.presence_picture(p, r7["S"], r7["resid"], ramp=r7["ramp"])), "proposal (auto)"),
                      tile(c(M.boost_picture(p, r7)), "proposal boost x4")])],
                title="N3: no paint at all. Split-toned print on yellowed paper, warm light left, cool right, glare")
    Image.fromarray(fig).save(f"{out_dir}/fig_N3_unpainted.jpg", quality=88)
    with open(f"{out_dir}/audit_notes.json", "w") as f:
        json.dump(notes, f, indent=1, default=str)
    for k, v in notes.items():
        print(k, json.dumps(v, default=str)[:600])


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "fig")
