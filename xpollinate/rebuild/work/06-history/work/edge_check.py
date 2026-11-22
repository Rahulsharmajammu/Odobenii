import numpy as np, cv2
import synth as S, methods as M, pairs as P, v2
rows = []
for name, tone, paper, capd, seed in [("N2 warm, phone", "warm", "yellowed", P.PHONE, 1), ("N3 split, no WB", "split", "yellowed",
        dict(cast_left=(1.0,0.90,0.72), cast_right=(1.0,0.90,0.72), awb="none", saturation=1.2, jpeg_q=75), 2),
        ("N1 neutral clean", "neutral", "white", P.CLEAN, 3)]:
    sc = S.portrait_scene(seed=seed)
    R0 = S.reflectance(sc, tone, paper, None, 0.0, seed)
    rgb, _, _ = S.capture(P.lateral_ca(R0, P.CA), S.Capture(seed=seed*7, **capd))
    box = ~sc.mount
    for label, prep in (("a*b* median only (TODO)", M.prep), ("same median on L*, a*, b*", P.prep_all)):
        p = prep(rgb)
        r = M.m3_proposed(p, mask=box, ring_plane=True, diagnostics=False)
        z2, j, g, x = v2.judge(p, r, box)
        shown = (P.lin_opacity(z2) >= 0.25) & j
        Lr = M.to_lab(rgb)[0]
        gx = cv2.Sobel(Lr, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(Lr, cv2.CV_32F, 0, 1, ksize=3)
        edge = cv2.dilate((np.hypot(gx, gy) > 20).astype(np.uint8), np.ones((5,5),np.uint8)) > 0
        paper_m = r.info["anchor_mask"]
        ev = j & ~paper_m
        print(f"{name:18s} | {label:26s} | shown on unpainted {shown[ev].mean():.3f} | on edges {shown[ev & edge].mean():.3f} | flat {shown[ev & ~edge].mean():.3f}")
