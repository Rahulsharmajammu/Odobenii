"""Display constraints: (1) sRGB's room for chroma at each lightness, by hue; (2) whether a departure drawn
(a) at the print's own lightness (isoluminant overlay, as in a plain chroma boost or TODO.md's presence map) or
(b) bright on a dimmed grey context (the proposed Presence) stays visible after simulating protanopia, deuteranopia
and tritanopia (Machado, Oliveira and Fernandes 2009, severity 1); (3) hue drift when chroma is raised at a constant
CIELAB hue angle (blue turns purple) compared with Oklab."""
import json
import numpy as np
import colour as C

hues = {"red/pink (lips, cheeks)": 10, "orange": 55, "yellow/gold": 100, "green": 145, "cyan": 200,
        "blue": 255, "purple": 300, "magenta": 340}
out = {}

# (1) gamut room
Ls = [0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.80, 0.85, 0.95]
room = {}
for name, hdeg in hues.items():
    h = np.deg2rad(hdeg)
    room[name] = [round(float(C.max_chroma_oklab(L, h)), 3) for L in Ls]
out["max_oklab_chroma_by_L"] = {"L": Ls, "by_hue": room}

# (2) CVD visibility: CIELAB dE76 between a departure colour and its grey surround, before and after simulation
def to8(ok):
    lin = np.clip(C.oklab_to_lin(np.asarray(ok, np.float32)), 0, 1)
    return np.round(C.srgb_encode(lin) * 255).astype(np.uint8)

def dE(a8, b8):
    la, lb = C.srgb8_to_lab(a8), C.srgb8_to_lab(b8)
    return float(np.linalg.norm(la - lb))

rows = {}
for name, hdeg in hues.items():
    h = np.deg2rad(hdeg)
    res = {}
    # (a) isoluminant: grey at L 0.62 (a mid print tone), colour at the same L, chroma 0.08 (a clear boost)
    L = 0.62
    cc = min(0.08, 0.9 * float(C.max_chroma_oklab(L, h)))
    grey = to8([[L, 0, 0]]); col = to8([[L, cc * np.cos(h), cc * np.sin(h)]])
    # (b) proposed presence: dim grey context L 0.36, departure at L 0.80, chroma up to 0.16 within gamut
    g2 = to8([[0.36, 0, 0]])
    c2c = min(0.16, 0.9 * float(C.max_chroma_oklab(0.80, h)))
    col2 = to8([[0.80, c2c * np.cos(h), c2c * np.sin(h)]])
    for kind in ("normal", "protan", "deutan", "tritan"):
        f = (lambda x: x) if kind == "normal" else (lambda x, k=kind: C.simulate_cvd(x, k))
        res[kind] = {"isoluminant_overlay": round(dE(f(grey), f(col)), 1), "bright_on_dim": round(dE(f(g2), f(col2)), 1)}
    rows[name] = res
out["cvd_dE76"] = rows

# (3) hue drift when raising chroma at constant CIELAB hue angle (L* 60) vs constant Oklab hue
drift = {}
for name, hab in {"blue (CIELAB h 290)": 290, "blue (CIELAB h 270)": 270, "red (CIELAB h 20)": 20}.items():
    h = np.deg2rad(hab)
    oh = []
    for c in (5, 10, 20, 40):
        lab = np.array([[60.0, c * np.cos(h), c * np.sin(h)]], np.float32)
        ok = C.lin_to_oklab(np.clip(C.lab_to_lin(lab), 1e-6, None))
        oh.append(round(float(np.degrees(np.arctan2(ok[0, 2], ok[0, 1]))) % 360, 1))
    drift[name] = {"CIELAB chroma": [5, 10, 20, 40], "Oklab hue (deg)": oh}
out["cielab_constant_hue_drift_in_oklab"] = drift
json.dump(out, open("cvd_gamut.json", "w"), indent=1)
print(json.dumps(out["cvd_dE76"], indent=0)[:3000])
print(out["cielab_constant_hue_drift_in_oklab"])
print({k: v for k, v in room.items()})
