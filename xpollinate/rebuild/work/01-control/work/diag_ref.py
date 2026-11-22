import sys, numpy as np, cv2
import hpv, evaluate as E
name = sys.argv[1]
c = E.load_case(name); L, bare, cores = E.eval_masks(c)
rgb = c["img"].astype(np.float32)/255
picks = E.auto_picks(c, L, bare)
print("picks", picks, [round(float(L[y0:y1, x0:x1].mean()),1) for x0,y0,x1,y1 in picks])
Lp, a, b, u = hpv.planes(rgb)
valid, _ = hpv.judgeable(rgb, Lp)
X, Y = hpv._grid(Lp.shape)
# the true bare colour per band (oracle): median u over bare pixels
edges = np.arange(hpv.L_DARK, 100 + hpv.BAND, hpv.BAND); cen = (edges[:-1]+edges[1:])/2
bi = np.clip(np.digitize(Lp, edges)-1, 0, len(cen)-1)
for mode, pk in (("auto", None), ("picks", picks)):
    pm = None
    if pk:
        pm = np.zeros(Lp.shape, bool)
        for x0,y0,x1,y1 in pk: pm[y0:y1, x0:x1] = True
        pm &= valid
    ref, diag = hpv.fit_reference(Lp, u, X, Y, valid, pm, "tilt")
    print(f"--- {mode}: S={np.round(ref.S,2).tolist()}")
    print(" L    T(auto)        oracle(bare)    sigma  | paint median dep/sigma per key")
    for k in range(0, len(cen), 3):
        sel = bare & (bi == k) & valid
        orc = np.median(u[sel], 0) if sel.sum() > 300 else [np.nan, np.nan]
        line = f"{cen[k]:5.1f} ({ref.T[k,0]:6.2f},{ref.T[k,1]:6.2f})  ({orc[0]:6.2f},{orc[1]:6.2f})  {ref.sigma[k]:5.2f} |"
        r, s = ref.at(Lp, X, Y)
        for key, m in cores.items():
            ss = m & (bi == k)
            if ss.sum() > 200:
                dd = np.hypot(*(u[ss] - r[ss]).T) / s[ss]
                line += f" {key}:{np.median(dd):.1f}"
        print(line)
