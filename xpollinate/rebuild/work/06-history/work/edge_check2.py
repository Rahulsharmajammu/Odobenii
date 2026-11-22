import numpy as np, cv2
import synth as S, methods as M, pairs as P, v2
sc = S.portrait_scene(seed=3); box = ~sc.mount
R0 = S.reflectance(sc, "neutral", "white", None, 0.0, 3)
for label, ca, q in (("CA + JPEG 4:2:0", P.CA, 92), ("no CA, JPEG 4:2:0", 0.0, 92), ("CA, no JPEG", P.CA, None), ("no CA, no JPEG", 0.0, None)):
    capd = dict(P.CLEAN); capd["jpeg_q"] = q
    rgb, _, _ = S.capture(P.lateral_ca(R0, ca), S.Capture(seed=21, **capd))
    p = P.prep_all(rgb); r = M.m3_proposed(p, mask=box, ring_plane=True, diagnostics=False)
    z2, j, g, x = v2.judge(p, r, box)
    shown = (P.lin_opacity(z2) >= 0.25) & j
    Lr = M.to_lab(rgb)[0]
    gx = cv2.Sobel(Lr, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(Lr, cv2.CV_32F, 0, 1, ksize=3)
    edge = cv2.dilate((np.hypot(gx, gy) > 20).astype(np.uint8), np.ones((5,5),np.uint8)) > 0
    ev = j & ~r.info["anchor_mask"]
    print(f"N1 neutral clean | {label:18s} | shown {shown[ev].mean():.3f} | edges {shown[ev & edge].mean():.3f} | flat {shown[ev & ~edge].mean():.3f}")
