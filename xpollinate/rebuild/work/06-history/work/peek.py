import numpy as np
from PIL import Image
import synth as S
FULL = {"face": ("skin", 1.0), "lips": ("red", 1.0), "hands": ("skin", 1.0), "backdrop": ("blue", 0.5),
        "plant": ("green", 0.8), "pin": ("gold", 1.0)}
cases = [
  S.make_case("neg_neutral", None, "neutral", "white", S.Capture(seed=1, cast_left=(1,1,1), cast_right=(1,1,1))),
  S.make_case("painted_warm_cast", FULL, "warm", "yellowed", S.Capture(seed=2, cast_left=(1.0,0.93,0.80), cast_right=(1.0,0.93,0.80))),
  S.make_case("painted_split_mixedlight", FULL, "split", "yellowed", S.Capture(seed=3, cast_left=(1.0,0.90,0.74), cast_right=(0.93,0.98,1.06), glare=0.5)),
]
row = []
for c in cases:
    a = (np.clip(c.rgb,0,1)*255).astype(np.uint8); b = (np.clip(c.twin,0,1)*255).astype(np.uint8)
    row.append(np.concatenate([a, np.full((a.shape[0],8,3),255,np.uint8), b], axis=1))
big = np.concatenate([np.concatenate([r, np.full((r.shape[0],16,3),255,np.uint8)],axis=1) for r in row], axis=1)
Image.fromarray(big).resize((big.shape[1]//3, big.shape[0]//3), Image.LANCZOS).save("img/peek_cases.png")
print(big.shape)
