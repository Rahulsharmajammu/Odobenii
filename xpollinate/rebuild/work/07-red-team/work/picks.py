"""Picks (boxes) a careful user might draw, in print-512 coordinates, and their transfer to a capture."""
import numpy as np, cv2
import sim

GOOD = {                      # areas a user would take as unpainted, from light to dark
    "suit_left": (88, 338, 130, 385),
    "shoulder_right": (300, 262, 340, 318),
    "shuttle": (392, 120, 414, 200),
    "hair": (195, 22, 235, 48),
    "suit_low": (220, 440, 262, 490),
}
CONTAMINATED = dict(GOOD)
CONTAMINATED.pop("shoulder_right")
CONTAMINATED["backdrop"] = (306, 140, 350, 200)      # plain-looking studio backdrop: under the faint wash
MIDTONES_ONLY = {"suit_left": (88, 338, 130, 385), "shoulder_right": (300, 262, 340, 318)}


def to_capture(boxes, Hm, shrink=3):
    out = []
    for name, (x0, y0, x1, y1) in boxes.items():
        pts = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], np.float32) * sim.S
        q = cv2.perspectiveTransform(pts.reshape(-1, 1, 2), Hm).reshape(-1, 2)
        xa, ya = np.sort(q[:, 0]), np.sort(q[:, 1])
        out.append((xa[1] + shrink, ya[1] + shrink, xa[2] - shrink, ya[2] - shrink))   # inner box
    return out
