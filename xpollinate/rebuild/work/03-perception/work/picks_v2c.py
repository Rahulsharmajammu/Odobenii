import json
import numpy as np
import synth, pipelines as PL, pipelines_v2 as P2, eval_v2 as EV
S, PAD = synth.S, synth.PAD
def box(x0, y0, x1, y1, shape):
    m = np.zeros(shape, bool); m[PAD + S * y0:PAD + S * y1, PAD + S * x0:PAD + S * x1] = True; return m
out = {}
def show(tag, res, t):
    ev = EV.evaluate_all(res, t)
    o = {k.split(' (')[0]: (round(v["shown"], 2), round(v["pooled_B_linear_x4"], 1)) for k, v in ev["objects"].items()}
    print(f"{tag:44s} auc={ev['auc']:.3f} FA={ev['false_shown_all']:.3f} dropped={res['fit'].get('dropped')} | {o}", flush=True)
    out[tag] = {"auc": ev["auc"], "FA": ev["false_shown_all"], "objects": o, "dropped": res["fit"].get("dropped")}
for scen, goodb, badb in (
        ("thin", [(240, 345, 256, 430), (105, 300, 135, 335), (400, 300, 440, 330), (30, 250, 50, 300), (380, 120, 400, 200), (300, 440, 330, 470)],
                 (205, 160, 250, 178)),
        ("phone", [(240, 345, 256, 430), (105, 300, 135, 335), (400, 300, 440, 330), (30, 250, 50, 300), (380, 120, 400, 200), (208, 66, 248, 84)],
                  (186, 122, 206, 134)),          # bad: a pick on the left cheek (about 2.7 units)
        ("wide", [(240, 345, 256, 430), (105, 380, 135, 420), (400, 360, 440, 380), (300, 440, 330, 470), (150, 470, 200, 500), (60, 430, 90, 470)],
                 None)):
    img, t = synth.scenario(scen)
    sh = img.shape[:2]
    good = np.zeros(sh, bool)
    for b in goodb: good |= box(*b, sh)
    cases = [("automatic", None), ("good picks", good)]
    if badb is not None:
        cases.append(("good picks + one on a wash", good | box(*badb, sh)))
    for tag, pk in cases:
        if pk is not None:
            show(f"v2 corrob.  {scen}: {tag}", P2.run_v2(img, votes=True, yardstick="rayleigh", picks=pk, anchors="corroborated"), t)
json.dump(out, open("picks_v2c.json", "w"), indent=1)
