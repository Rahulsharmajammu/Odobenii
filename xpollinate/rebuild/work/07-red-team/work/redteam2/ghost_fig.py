import sys
sys.path.insert(0, "..")
import numpy as np, cv2
from skimage import color
import sim, evalgt, honest as Hn
import synth_engine as E

pr = sim.make_print(extensive=True)
imgA, HA = sim.capture(pr.R, sim.UNRULY_A); imgB, HB = sim.capture(pr.R, sim.UNRULY_B)
rA = E.run_capture(imgA); rB = E.run_capture(imgB)
Hba, _ = Hn.register(imgB, imgA)
w = lambda m, i=cv2.INTER_LINEAR: cv2.warpPerspective(m.astype(np.float32), Hba, (sim.P, sim.P), flags=i, borderValue=0)
vB = np.stack([w(rB["v"][..., 0]), w(rB["v"][..., 1])], -1); dnB = w(rB["dn"]); uB = w(rB["F"]["usable"], cv2.INTER_NEAREST) > 0.5
vA, dnA, uA = rA["v"], rA["dn"], rA["F"]["usable"]
cos = (vA * vB).sum(-1) / (np.linalg.norm(vA, axis=-1) * np.linalg.norm(vB, axis=-1) + 1e-9)
keep = uA & uB & (dnA >= 1) & (dnB >= 1) & (cos >= 0.5)
op = E.ramp(np.minimum(dnA, dnB)) * keep
gt = evalgt.gt_in_capture(pr, HA, sim.UNRULY_A)
face = gt["unpainted"] & uA & uB
print(f"unpainted (face, helmet) shown in 'seen in both': {100*(op[face]>=0.25).mean():.1f}%; wash core shown: {100*(op[gt['core']['wash'] & uA & uB]>=0.25).mean():.1f}%")
# direction of the ghost on the unpainted face vs the wash's own direction
ang = lambda v, m: np.degrees(np.arctan2(np.median(v[..., 1][m]), np.median(v[..., 0][m])))
print(f"median departure direction (chi): unpainted shown {ang(vA, face & (op>=0.25)):.0f} deg; wash core {ang(vA, gt['core']['wash'] & uA):.0f} deg")
# picture: C as the synthesis draws it: print dimmed, departures bright in their hue
g = cv2.cvtColor(imgA, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
base = np.repeat((0.15 + 0.3 * g)[..., None], 3, -1)
h = (np.degrees(np.arctan2(vA[..., 1], vA[..., 0])) % 360) / 2
hsv = np.stack([h, np.full_like(h, 200), np.full_like(h, 255)], -1).astype(np.uint8)
col = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB).astype(np.float32) / 255
C = base * (1 - op[..., None]) + col * op[..., None]
outline = cv2.dilate(face.astype(np.uint8), np.ones((3, 3))) - face.astype(np.uint8)
C[outline.astype(bool)] = (1, 1, 1)
pic = np.hstack([cv2.resize(imgA, (480, 480), interpolation=cv2.INTER_AREA), cv2.resize((np.clip(C, 0, 1) * 255).astype(np.uint8), (480, 480), interpolation=cv2.INTER_AREA)])
cv2.imwrite("ghost_pair.jpg", cv2.cvtColor(pic, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 90])
