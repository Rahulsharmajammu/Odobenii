import numpy as np, cv2
from skimage import color
import sim, picks, honest as Hn, todo_pipeline as T
from hrun import single, pair

F = cv2.FONT_HERSHEY_SIMPLEX

def label(img, text, scale=0.6):
    words, lines, cur = text.split(" "), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if cv2.getTextSize(t, F, scale, 1)[0][0] > img.shape[1] - 16 and cur:
            lines.append(cur); cur = w
        else:
            cur = t
    lines.append(cur)
    lh = int(28 * scale / 0.6)
    bar = np.full((lh * len(lines) + 8, img.shape[1], 3), 255, np.uint8)
    for k, ln in enumerate(lines):
        cv2.putText(bar, ln, (8, lh * (k + 1) - 4), F, scale, (0, 0, 0), 1, cv2.LINE_AA)
    return np.vstack([bar, img])

def small(img, s=0.36):
    return cv2.resize(img, (int(img.shape[1] * s), int(img.shape[0] * s)), interpolation=cv2.INTER_AREA)

def with_boxes(img, boxes, col=(255, 255, 255)):
    out = img.copy()
    for k, (x0, y0, x1, y1) in enumerate(boxes):
        cv2.rectangle(out, (int(x0), int(y0)), (int(x1), int(y1)), col, 3)
        cv2.putText(out, str(k + 1), (int(x0) + 4, int(y0) + 24), F, 0.8, col, 2, cv2.LINE_AA)
    return out

def save(name, rows):
    w = max(r.shape[1] for r in rows)
    rows = [np.hstack([r, np.full((r.shape[0], w - r.shape[1], 3), 255, np.uint8)]) if r.shape[1] < w else r for r in rows]
    cv2.imwrite(f"out/{name}", cv2.cvtColor(np.vstack(rows), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 90])

def todo_pic(variant, cap, ps):
    pr = sim.make_print(extensive=(variant == "extensive"))
    R = pr.R_unpainted if variant == "unpainted" else pr.R
    img, Hm = sim.capture(R, cap)
    bx = picks.to_capture(ps, Hm) if ps else []
    res = T.run(img, bx or None)
    return with_boxes(img, bx), with_boxes(T.presence_picture(img, res), bx)

def boosted(lab, d, k=3.0):
    lab2 = np.stack([lab[..., 0], d["ra"] + k * (lab[..., 1] - d["ra"]), d["rb"] + k * (lab[..., 2] - d["rb"])], -1)
    return (np.clip(color.lab2rgb(lab2), 0, 1) * 255).astype(np.uint8)

# Figure 1: TODO.md's pipeline in three situations
rows = []
for title, args in (("Print with NO paint, unruly capture A, five good marks: TODO.md presence map", ("unpainted", sim.UNRULY_A, picks.GOOD)),
                    ("Painted print, capture A, mark 5 on the faint backdrop wash: the wash vanishes, the face turns 'paint'", ("normal", sim.UNRULY_A, picks.CONTAMINATED)),
                    ("Wash over 80% of the print, clean capture, automatic reference: the unpainted face reads as paint", ("extensive", sim.CLEAN, None))):
    a, b = todo_pic(*args)
    rows.append(label(np.hstack([small(a), small(b)]), title))
save("fig1_todo_failures.jpg", rows)

# Figure 2: the alternative design on capture A, good marks and contaminated marks, with capture B as the second
rB = single("normal", sim.UNRULY_B, picks.GOOD)
rows = []
for title, ps in (("good marks", picks.GOOD), ("mark 5 on the faint wash", picks.CONTAMINATED)):
    rA = single("normal", sim.UNRULY_A, ps)
    pz = pair(rA, rB)
    d = rA["d"]
    p1 = with_boxes(rA["img"], rA["boxes"])
    p2 = with_boxes(Hn.assumed_unpainted(rA["lab"], d), rA["boxes"])
    p3 = boosted(rA["lab"], d)
    p4 = Hn.picture(rA["img"], d["va"], d["vb"], rA["op"], hatch_masks=(d["uncovered"], ~rA["usable"]))
    p5 = Hn.picture(rA["img"], d["va"], d["vb"], pz["op"], hatch_masks=(~(pz["uA"] & pz["uB"]),), grey_mask=pz["one"])
    strip = np.hstack([small(p) for p in (p1, p2, p3, p4, p5)])
    words = "; ".join(rA["words"]) or "no tripwire"
    rows.append(label(strip, f"Capture A, {title}.  Panels: capture | assumed unpainted | boost about it (x3) | departure (one capture) | seen in both A and B"))
    rows.append(label(np.full((4, strip.shape[1], 3), 255, np.uint8), "Words: " + words))
save("fig2_alternative.jpg", rows)

# Figure 3: negative control, the print with no paint
rA = single("unpainted", sim.UNRULY_A, picks.GOOD); rBu = single("unpainted", sim.UNRULY_B, picks.GOOD)
pz = pair(rA, rBu)
a, b = todo_pic("unpainted", sim.UNRULY_A, picks.GOOD)
d = rA["d"]
p3 = Hn.picture(rA["img"], d["va"], d["vb"], rA["op"], hatch_masks=(d["uncovered"], ~rA["usable"]))
p4 = Hn.picture(rA["img"], d["va"], d["vb"], pz["op"], hatch_masks=(~(pz["uA"] & pz["uB"]),), grey_mask=pz["one"])
save("fig3_negative_control.jpg", [label(np.hstack([small(a), small(b), small(p3), small(p4)]),
     "No paint. Capture A | TODO.md map | alternative, one capture | alternative, seen in both A and B (grey: one capture only)")])
print("figures written")
