import sys, numpy as np
import hpv, evaluate as E
for name in sys.argv[1].split(","):
    c = E.load_case(name)
    rgb = c["img"].astype(np.float32)/255
    L, a, b, u = hpv.planes(rgb); valid, _ = hpv.judgeable(rgb, L); X, Y = hpv._grid(L.shape)
    ref, d = hpv.fit_reference(L, u, X, Y, valid, None, "tilt")
    Ls, us, Xs, Ys, w = d["Ls"], d["us"], d["Xs"], d["Ys"], d["w"]
    r = us - np.stack([np.interp(Ls, ref.centres, ref.T[:, 0]), np.interp(Ls, ref.centres, ref.T[:, 1])], 1)
    out = []
    for nm, sel in (("dark", Ls < np.percentile(Ls, 33)), ("mid", (Ls >= np.percentile(Ls, 33)) & (Ls < np.percentile(Ls, 67))), ("light", Ls >= np.percentile(Ls, 67))):
        ww = w * sel
        B = np.stack([Xs, Ys], 1); mx = (ww @ B)/ww.sum(); Bc = (B - mx)*np.sqrt(ww)[:, None]
        S = np.stack([np.linalg.lstsq(Bc, r[:, j]*np.sqrt(ww), rcond=None)[0] for j in range(2)])
        out.append((nm, np.round(S, 2).tolist()))
    print(f"{name:15s} full S={np.round(ref.S,2).tolist()} sigma_med={np.median(ref.sigma):.2f}  by tone: {out}")
