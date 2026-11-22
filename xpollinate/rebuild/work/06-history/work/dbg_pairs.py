import numpy as np, cv2, math
from PIL import Image
import pairs as P, methods as M, synth as S
name, recipe, tone, paper, cA, cB, extra = P.CASES[2]
out, (rgbA, rgbB, rA, zB, vaB, vbB, useB, Hm) = P.evaluate(name, recipe, tone, paper, cA, cB, seed=2, **extra)
import csv
print([ (r['view'], r['registration']) for r in out][:1])
cos = (rA.va*vaB + rA.vb*vbB)/np.maximum(np.hypot(rA.va,rA.vb)*np.hypot(vaB,vbB),1e-6)
both = (rA.z>=1.5)&(zB>=1.5)&(cos>=0.5)&useB&(P.lin_opacity(np.minimum(rA.z,zB))>=0.25)
def hue(va, vb, z):
    ang = np.arctan2(vb, va); al = np.clip((z-2)/4,0,1)[...,None]
    col = np.clip(cv2.cvtColor(np.stack([np.full_like(va,62),55*np.cos(ang),55*np.sin(ang)],-1).astype(np.float32), cv2.COLOR_LAB2RGB),0,1)
    return 0.5*(1-al)+col*al
tiles = [np.clip(rgbA,0,1), np.clip(rgbB,0,1), hue(rA.va,rA.vb,rA.z), hue(vaB,vbB,zB), np.repeat(both[...,None].astype(np.float32),3,2)]
sheet = np.concatenate([np.concatenate([t, np.ones((t.shape[0],6,3))],1) for t in tiles],1)
im = Image.fromarray((sheet*255).astype(np.uint8)); im.thumbnail((2000,600)); im.save("img/dbg_N4_pair.png")
# where are the survivors?
pA = P.prep_all(rgbA)
print("survivors by tone (L bands of 10):")
for lo in range(0,100,10):
    m = (pA.L>=lo)&(pA.L<lo+10)&useB&pA.usable
    if m.sum()>500: print(lo, f"{(both&m).sum()/m.sum():.2f}", "  mean dir A", np.round([np.median(rA.va[both&m]) if (both&m).any() else 0, np.median(rA.vb[both&m]) if (both&m).any() else 0],1))
