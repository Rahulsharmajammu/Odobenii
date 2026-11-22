"""Diagnostic pictures for one scenario and one method."""
from __future__ import annotations

import sys

import numpy as np
from PIL import Image, ImageDraw

import bench
import methods as M
import sim


def tile(img01, label, w=520):
    im = Image.fromarray((np.clip(img01, 0, 1) * 255).astype(np.uint8))
    im = im.resize((w, int(im.height * w / im.width)))
    canvas = Image.new("RGB", (im.width, im.height + 22), "white")
    canvas.paste(im, (0, 22))
    ImageDraw.Draw(canvas).text((4, 4), label, fill="black")
    return np.asarray(canvas)


def zpic(z, judge, top=8.0):
    v = np.clip(np.nan_to_num(z) / top, 0, 1)
    out = np.stack([v, v, v], -1)
    out[~judge] = (0.3, 0.3, 0.6)
    out[judge & (z > 3)] = (1.0, 0.6, 0.0) * np.ones(3) * 1
    return out


def run(scen, rn, out):
    s = sim.build(scen)
    p = M.prepare(s["img"], s["box"])
    res = bench.RUNS[rn](p, s)
    x0, y0, x1, y1 = s["box"]
    crop = lambda a: a[y0:y1, x0:x1]
    tiles = [tile(crop(p["rgb"]), f"{scen} original")]
    if "resid" in res and "ref" in res and np.ndim(res["ref"]) == 3:
        tiles.append(tile(crop(M.boost_picture(p, res)), "boost (substrate neutral, x4)"))
        tiles.append(tile(crop(M.reference_picture(p, res)), "reference (x4)"))
        tiles.append(tile(crop(M.presence_picture(p, res["S"], res["resid"])), "presence (3->6)"))
    tiles.append(tile(crop(zpic(res["S"], p["judge"])), f"{rn}: statistic, orange > 3"))
    truth = np.zeros(p["judge"].shape + (3,))
    truth[s["paint_any"]] = 1
    tiles.append(tile(crop(truth), "paint truth"))
    h = max(t.shape[0] for t in tiles)
    tiles = [np.pad(t, ((0, h - t.shape[0]), (0, 4), (0, 0)), constant_values=255) for t in tiles]
    rows = [np.concatenate(tiles[i:i + 3], 1) for i in range(0, len(tiles), 3)]
    wmax = max(r.shape[1] for r in rows)
    rows = [np.pad(r, ((0, 4), (0, wmax - r.shape[1]), (0, 0)), constant_values=255) for r in rows]
    Image.fromarray(np.concatenate(rows, 0)).save(out, quality=88)
    print(res.get("note"), getattr(res.get("bg"), "kappa2", None))


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2], sys.argv[3])
