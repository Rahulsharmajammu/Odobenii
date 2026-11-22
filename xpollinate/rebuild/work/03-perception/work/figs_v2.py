import numpy as np
from PIL import Image
import synth, pipelines as PL, pipelines_v2 as P2, render as R, render_v2 as R2
from tone_follow import tone_following

def words(res, picked=False):
    w = ["Visualisation only - not a measurement.",
         "Reference: votes of places" + (", anchored by your examined boxes." if picked else ", automatic.")]
    if res["fit"].get("cast", 0) >= 4:
        w.append("A colour cast across the frame was allowed for.")
    if (res["leftout"] | res["unsupported"]).mean() > 0.05:
        w.append("Hatched: too bright or too dark to judge.")
    tf = tone_following(res)
    if tf:
        w.append("Colour follows a range of tones across the frame: the tone may be wrong there.")
    return " ".join(w)

S, PAD = synth.S, synth.PAD
def box(x0, y0, x1, y1, shape):
    m = np.zeros(shape, bool); m[PAD + S * y0:PAD + S * y1, PAD + S * x0:PAD + S * x1] = True; return m

for scen, pk in (("thin", None), ("thin_mixed", None), ("majority", None), ("wide", None), ("wide", "boxes"), ("control", None)):
    img, t = synth.scenario(scen)
    picks = None
    if pk:
        sh = img.shape[:2]
        picks = np.zeros(sh, bool)
        for b in [(240, 345, 256, 430), (105, 380, 135, 420), (400, 360, 440, 380), (300, 440, 330, 470), (150, 470, 200, 500), (60, 430, 90, 470)]:
            picks |= box(*b, sh)
    res = P2.run_v2(img, votes=True, yardstick="rayleigh", picks=picks, anchors="corroborated")
    res["fit"]["Lidx"] = res["fit"]["Lidx"]
    m, p = R2.montage2x2(img, res, words(res, picks is not None))
    tag = scen + ("_boxes" if pk else "")
    Image.fromarray(m).save(f"figs_v2/montage_{tag}.png")
    Image.fromarray(R2.strip(res)).save(f"figs_v2/strip_{tag}.png")
    R.save_blink(f"figs_v2/blink_{tag}.png", p["D"], p["A4"], 0.5)
    print(tag, words(res, picks is not None), flush=True)
