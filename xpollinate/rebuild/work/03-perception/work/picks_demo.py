"""The majority-painted print: the automatic reference absorbs the painted backdrop; the signature shows; three boxes
on areas a user knows are unpainted (the white straps, the forehead, the suit) put the reference right."""
import json
import numpy as np
from PIL import Image
import synth, pipelines as PL, render as R, evaluate as E

S, PAD = synth.S, synth.PAD

def box(x0, y0, x1, y1, shape):
    m = np.zeros(shape, bool)
    m[PAD + S * y0:PAD + S * y1, PAD + S * x0:PAD + S * x1] = True
    return m

img, t = synth.scenario("majority")
shape = img.shape[:2]
picks = box(240, 345, 256, 430, shape) | box(208, 66, 248, 84, shape) | box(105, 300, 135, 335, shape)
out = {}
for name, pk in (("automatic", None), ("three boxes", picks)):
    res = PL.run_proposed(img, space="lab", picks=pk)
    ev = E.evaluate(res, t)
    out[name] = {"false_shown_all": ev["false_shown_all"], "false_shown": ev["false_shown"],
                 "objects": {k: v["shown"] for k, v in ev["objects"].items()}, "auc": ev["auc"]}
    print(name, round(ev["auc"], 3), "FA", round(ev["false_shown_all"], 3),
          {k.split(' (')[0]: round(v["shown"], 2) for k, v in ev["objects"].items()}, flush=True)
    pres = R.presence_picture(res)
    if pk is not None:
        from scipy.ndimage import binary_dilation
        edge = binary_dilation(pk, iterations=3) & ~pk
        pres = pres.copy(); pres[edge] = [255, 255, 255]
    m = R.montage([img, R.unpainted_picture(res), R.boosted_picture(res), pres],
                  ["Original", "As if unpainted", "Boosted (around neutral)", "Presence"], scale=0.45, cols=4)
    Image.fromarray(m).save(f"figs/majority_{name.replace(' ', '_')}.png")
    a, b = R.blink_frames(res)
    crop = (slice(60, 620), slice(250, 900))
    pair = np.concatenate([a[crop], np.full((560, 12, 3), 255, np.uint8), b[crop]], 1)
    Image.fromarray(pair).resize((pair.shape[1] // 2 * 1, pair.shape[0] // 2 * 1)).save(f"figs/blinkpair_majority_{name.replace(' ', '_')}.png")
json.dump(out, open("picks_demo.json", "w"), indent=1)
