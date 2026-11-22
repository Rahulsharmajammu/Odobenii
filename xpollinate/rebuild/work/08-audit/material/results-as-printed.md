# What the assistant's scripts printed, in the order they were run

## 1. `synth.py` then the visualiser v4.1.1 on the synthetic images (last 20 lines of its output)

```
Analysis scale: 1.0
Output scale:   0.5
Threshold mode: noise_floor
Noise fraction: 0.01
LRC bin width:  1.0
LRC smoothing:  3 bins
Spatial filter: 100 px
Alpha blur:     0.8 px
Max pixels:     100000000
Workers:        4
Color space:    ICC/EXIF-aware; sRGB default
[1/7 | 14.3%] A_neutral_untinted__7263867a | Space=C*ab Mode=noise_floor Threshold=5.22 | Chroma=0.00% | Components=0 | PNG lossless | Space=LRC Mode=noise_floor Threshold=1.98 | Chroma=0.00% | Components=0 | PNG lossless
[2/7 | 28.6%] B_warm_untinted__3ebdfd0a | Space=C*ab Mode=noise_floor Threshold=14.44 | Chroma=0.00% | Components=0 | PNG lossless | Space=LRC Mode=noise_floor Threshold=1.75 | Chroma=0.00% | Components=0 | PNG lossless
[3/7 | 42.9%] D_warm_sky_painted__68f8bba6 | Space=C*ab Mode=noise_floor Threshold=14.44 | Chroma=0.00% | Components=0 | PNG lossless | Space=LRC Mode=noise_floor Threshold=2.16 | Chroma=1.31% | Components=3 | PNG lossless
[4/7 | 57.1%] C_warm_blue_wash__c2bba7d0 | Space=C*ab Mode=noise_floor Threshold=14.53 | Chroma=0.00% | Components=0 | PNG lossless | Space=LRC Mode=noise_floor Threshold=1.74 | Chroma=0.00% | Components=0 | PNG lossless
[5/7 | 71.4%] E_warm_small_touches__cb9a87ae | Space=C*ab Mode=noise_floor Threshold=14.48 | Chroma=0.03% | Components=1 | PNG lossless | Space=LRC Mode=noise_floor Threshold=1.78 | Chroma=0.04% | Components=1 | PNG lossless
[6/7 | 85.7%] F_warm_strong_pink__697483d6 | Space=C*ab Mode=noise_floor Threshold=15.84 | Chroma=0.00% | Components=0 | PNG lossless | Space=LRC Mode=noise_floor Threshold=2.26 | Chroma=0.26% | Components=1 | PNG lossless
[7/7 | 100.0%] G_16bit__5cb3daf3 | Space=C*ab Mode=noise_floor Threshold=14.24 | Chroma=0.00% | Components=0 | TIFF (tiff_lzw) | Space=LRC Mode=noise_floor Threshold=1.68 | Chroma=0.00% | Components=0 | TIFF (tiff_lzw)

Done. 7/7 images processed successfully.
```

## 2. `evalcmp.py`

Columns:
- the visualiser's raw C\*ab mask;
- its LRC mask;
- a vector feature with whole-image L\*-band medians, thresholded at 4;
- Woodii's `tint_maps` on the linear data with hand-placed picks, scored only where Woodii "shows".

Each cell is percent of painted pixels flagged / percent of unpainted pixels flagged.

```
case                     paint% | raw hit/false | LRC hit/false | vec>4 hit/false | woodii hit/false(of shown)
A_neutral_untinted          0.0 |   nan/ 0.00 |   nan/ 0.00 |   nan/ 0.00 |   nan/ 0.04
B_warm_untinted             0.0 |   nan/ 0.00 |   nan/ 0.00 |   nan/ 0.00 |   nan/ 0.04
C_warm_blue_wash           18.8 |   0.0/ 0.00 |   0.0/ 0.00 |   0.0/ 0.00 |  91.1/ 0.04
D_warm_sky_painted         27.5 |   0.0/ 0.00 |   0.0/ 1.80 |   0.8/ 2.32 | 100.0/ 0.04
E_warm_small_touches        0.1 |  55.6/ 0.00 |  69.9/ 0.00 |  97.5/ 0.00 | 100.0/ 0.04
F_warm_strong_pink         18.8 |   0.0/ 0.00 |   1.4/ 0.00 |  48.2/ 2.21 | 100.0/ 0.04
```

## 3. `pickref.py`

The vector feature with the reference taken from a hand-chosen region: rows 950 onward plus the 80 px margin, or
for the sky case columns 600 onward plus the margin. Thresholded at 3 after a 5 px median.

```
A_neutral_untinted       hit   nan%  false  0.00%
B_warm_untinted          hit   nan%  false  0.00%
C_warm_blue_wash         hit  17.5%  false  0.00%
D_warm_sky_painted       hit 100.0%  false  0.00%
E_warm_small_touches     hit  97.5%  false  0.00%
F_warm_strong_pink       hit 100.0%  false  0.00%
```

## 4. `strip.py` on `Chroma_diagnoser_v4.1`, then the 4.1.2 run

`strip.py` edited the script (82,033 → 73,701 bytes). A first run of 4.1.2 crashed in `_write_summary`
(`KeyError: 'results'`). After the fix, and with histograms made opt-in, it processed 7/7 images. Its run log has one
row per image and space with the threshold settings only. The edits are in commit 4584a2f of
/home/user/handpaint_visualiser.
