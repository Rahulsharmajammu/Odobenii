import sys, pickle, numpy as np, cv2
from PIL import Image
import hpv, evaluate as E
name = sys.argv[1]
c = E.load_case(name)
L, bare, cores = E.eval_masks(c)
res = hpv.analyse(c["img"].astype(np.float32)/255, run_checks=False)
on = res["alpha"] >= 0.5
fp = on & bare
print("FP", fp[bare].mean())
# where: distance from the print's edge, and tone
h, w = L.shape
yy, xx = np.mgrid[0:h, 0:w]
edge = np.minimum.reduce([xx, yy, w-1-xx, h-1-yy]) / (0.25*min(h, w))
for lo, hi in ((0, .25), (.25, .5), (.5, 1), (1, 9)):
    m = bare & (edge >= lo) & (edge < hi)
    print(f"edge-dist {lo}-{hi}: FP {on[m].mean():.3f} (n={m.sum()})")
# near luminance edges?
gx = cv2.Sobel(L, cv2.CV_32F, 1, 0); gy = cv2.Sobel(L, cv2.CV_32F, 0, 1)
g = np.hypot(gx, gy)
for lo, hi in ((0, 5), (5, 20), (20, 60), (60, 1e9)):
    m = bare & (g >= lo) & (g < hi)
    print(f"grad {lo}-{hi}: FP {on[m].mean():.3f} (n={m.sum()})")
# hue of FP departures
d = res["d_ab"][fp]
ang = np.degrees(np.arctan2(d[:,1], d[:,0])) % 360
print("FP hue hist (deg, 45 bins):", np.histogram(ang, bins=8, range=(0,360))[0])
vis = np.zeros((h, w, 3), np.uint8); vis[bare] = (90, 90, 90); vis[fp] = (255, 60, 60)
for k, m in cores.items(): vis[m] = (60, 160, 255)
Image.fromarray(vis).resize((600, 600)).save(f"look/fp_{name}.png")
