"""Build every case once and store it (image as the capture file would decode, plus ground truth)."""
import pickle, time, sys
import numpy as np
from PIL import Image
import cases

names = sys.argv[1:] or cases.CASES
for n in names:
    t = time.time()
    c = cases.build(n)
    Image.fromarray(c["img"]).save(f"cases/{n}.png")
    if c["jpeg"]:
        open(f"cases/{n}.jpg", "wb").write(c["jpeg"])
    with open(f"cases/{n}.pkl", "wb") as f:
        pickle.dump({k: v for k, v in c.items() if k not in ("jpeg",)}, f)
    small = Image.fromarray(c["img"]); small.thumbnail((500, 500)); small.save(f"cases/{n}_thumb.png")
    print(n, c["img"].shape, f"{time.time()-t:.1f}s", c["desc"])
