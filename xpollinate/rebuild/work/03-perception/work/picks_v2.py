"""Picks: v1 (x20 weights in the fit) against v2 (anchors acting only beyond the capture's per-pixel scatter), with
good picks, and with one pick laid on a thin wash (the face), on the thin-wash print; and on a print washed over most
places at the light tones, where votes cannot recover the tone."""
import json
import numpy as np
import synth, pipelines as PL, pipelines_v2 as P2, evaluate as E, eval_v2 as EV

S, PAD = synth.S, synth.PAD
def box(x0, y0, x1, y1, shape):
    m = np.zeros(shape, bool); m[PAD + S * y0:PAD + S * y1, PAD + S * x0:PAD + S * x1] = True; return m

out = {}
def show(tag, res, t):
    ev = EV.evaluate_all(res, t)
    o = {k.split(' (')[0]: (round(v["shown"], 2), round(v["pooled_B_linear_x4"], 1)) for k, v in ev["objects"].items()}
    print(f"{tag:42s} auc={ev['auc']:.3f} FA={ev['false_shown_all']:.3f} | (C shown, pooled d' in linear B) {o}", flush=True)
    out[tag] = {"auc": ev["auc"], "FA": ev["false_shown_all"], "objects": o}

img, t = synth.scenario("thin")
sh = img.shape[:2]
good = box(240, 345, 256, 430, sh) | box(105, 300, 135, 335, sh) | box(400, 300, 440, 330, sh) | box(30, 250, 50, 300, sh) \
       | box(380, 120, 400, 200, sh) | box(300, 440, 330, 470, sh)
bad = good | box(205, 160, 250, 178, sh)        # plus a pick on the chin: inside the thin flesh wash
for tag, pk in (("thin: automatic", None), ("thin: good picks", good), ("thin: good picks + one on the wash", bad)):
    show("v1 " + tag, PL.run_proposed(img, space="lab", picks=pk), t)
    show("v2 " + tag, P2.run_v2(img, votes=True, yardstick="rayleigh", picks=pk), t)

img, t = synth.scenario("wide")
sh = img.shape[:2]
good_w = box(240, 345, 256, 430, sh) | box(105, 380, 135, 420, sh) | box(400, 360, 440, 380, sh) | box(300, 440, 330, 470, sh) \
         | box(150, 470, 200, 500, sh) | box(60, 430, 90, 470, sh)
for tag, pk in (("wide: automatic", None), ("wide: good picks", good_w)):
    show("v1 " + tag, PL.run_proposed(img, space="lab", picks=pk), t)
    show("v2 " + tag, P2.run_v2(img, votes=True, yardstick="rayleigh", picks=pk), t)
json.dump(out, open("picks_v2.json", "w"), indent=1)
