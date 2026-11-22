import numpy as np, cv2
from skimage import color
import sim

pr = sim.make_print()
lab_p = color.rgb2lab(sim.srgb_encode(pr.R))
lab_u = color.rgb2lab(sim.srgb_encode(pr.R_unpainted))
dE = np.sqrt(((lab_p - lab_u) ** 2).sum(-1))
core = sim.chromatic_paint_mask(pr)
for k, m in core.items():
    print(f"{k:14s} area {m.mean()*100:5.1f}%  dE76 median {np.median(dE[m]):5.2f}  p10 {np.percentile(dE[m],10):5.2f}  dC*: {np.median(np.hypot(lab_p[...,1],lab_p[...,2])[m]-np.hypot(lab_u[...,1],lab_u[...,2])[m]):+5.2f}  L* {np.median(lab_u[...,0][m]):4.0f}")
for k in ("retouch_neutral","foxing","mat_burn"):
    m = pr.layers[k] > 0.5*pr.layers[k].max()
    print(f"{k:14s} area {m.mean()*100:5.2f}%  dE76 median {np.median(dE[m]) if k.startswith('ret') else np.nan:5.2f}")
# the unpainted print's own tone: a*, b* vs L*
L, a, b = lab_u[...,0], lab_u[...,1], lab_u[...,2]
for lo in range(10, 100, 10):
    m = (L >= lo) & (L < lo+10) & ~sim.any_medium(pr)
    if m.sum(): print(f"unpainted L* {lo}-{lo+10}: a* {np.median(a[m]):5.2f} b* {np.median(b[m]):5.2f}  n={m.sum()}")
pr_ext = sim.make_print(extensive=True)
print("extensive wash covers", (pr_ext.layers['wash']>0.5).mean())
cv2.imwrite('out/print_painted.png', cv2.cvtColor((sim.srgb_encode(pr.R)*255).astype(np.uint8), cv2.COLOR_RGB2BGR))
cv2.imwrite('out/print_unpainted.png', cv2.cvtColor((sim.srgb_encode(pr.R_unpainted)*255).astype(np.uint8), cv2.COLOR_RGB2BGR))
for name, c in (("clean", sim.CLEAN), ("A", sim.UNRULY_A), ("B", sim.UNRULY_B)):
    img, H = sim.capture(pr.R, c)
    cv2.imwrite(f'out/capture_{name}.jpg', cv2.cvtColor(img, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])
    imgu, _ = sim.capture(pr.R_unpainted, c)
    lab_c = color.rgb2lab(img/255.0); lab_cu = color.rgb2lab(imgu/255.0)
    # how far does the capture move the unpainted print's colour across the frame: a*, b* of the unpainted capture in mid-tone suit area, left vs right
    for (x0,y0,x1,y1) in ((60,300,110,360),(300,260,340,320)):
        pts = np.array([[x0*2,y0*2],[x1*2,y1*2]],np.float32).reshape(-1,1,2)
        q = cv2.perspectiveTransform(pts, H).reshape(-1,2).astype(int)
        sl = (slice(q[0,1],q[1,1]), slice(q[0,0],q[1,0]))
        print(name, 'unpainted suit box', (x0,y0), 'L*a*b* median', np.round(np.median(lab_cu[sl].reshape(-1,3),axis=0),2))
