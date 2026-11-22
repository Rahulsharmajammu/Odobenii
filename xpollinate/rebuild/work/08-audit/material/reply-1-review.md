# The assistant's reply to message 1, verbatim

# Review: handpaint visualiser vs Woodii's Chroma mode

**Which code I compared.** Woodii has no branch called "chroma". Chroma mode lives on `mbi-0.4-batch5.6` (through `5.6.4`) and was removed in 0.4.0rc2, so I reviewed the last version before removal. On the visualiser side I reviewed `Chroma_diagnoser_v4.1` on `main`.

## Main finding

The visualiser derives its threshold from the image itself, so the more paint a print carries, the less of it the Segmented panel shows. Its negative controls are clean, which is good, but large painted areas vanish.

I ran it on synthetic warm-toned prints with known paint (share of painted pixels flagged / share of unpainted pixels flagged):

| Case | Visualiser, raw C\*ab | Visualiser, LRC | Woodii Chroma maths |
|---|---|---|---|
| Untinted, neutral or warm | – / 0% | – / 0% | – / 0.04% |
| Faint blue wash, 19% of frame | 0% / 0% | 0% / 0% | 91% / 0.04% |
| Blue "sky", 27% of frame | 0% / 0% | 0% / 1.8% | 100% / 0.04% |
| Obvious pink wash, 19% of frame | 0% / 0% | 1.4% / 0% | 100% / 0.04% |
| Two small pink touches | 56% / 0% | 70% / 0% | 100% / 0.04% |

In the pink case the wash is plain in the Original and Chroma Boosted panels, yet the Segmented panel shows one small blob and the footer reads "Area: 0.26%". In the sky case LRC flags only unpainted pixels.

The comparison flatters Woodii: the scenes follow its own assumptions (transparent tints, shot noise), and it got linear data and hand-placed picks. Treat it as a demonstration of the mechanism, not a ranking.

Three causes in the visualiser:

- **The noise-floor walk measures how rare a value is, not the substrate's noise.** `_noise_floor_threshold` walks up from the histogram peak until counts fall below 1% of it. Extensive paint keeps the tail populated, so the threshold lands beyond the paint.
- **LRC baselines each L\* band on the whole image.** Where paint fills a band, paint becomes the median and unpainted pixels become the outliers.
- **Chroma is a scalar.** A blue wash over a warm print moves the colour toward neutral, so chroma falls and the pixel reads as "less than substrate". Presence needs the distance in (a\*, b\*) from the substrate's colour at that lightness.

## What would fix it

Woodii's central idea transfers without its machinery: let the user mark an unpainted reference (a margin, or an untinted area), take the per-L\* median (a\*, b\*) and spread from that, and threshold in multiples of that spread. I tried this in plain CIELAB on the same 8-bit PNGs: 100% of the pink wash, the sky and the larger touch, 17.5% of the very faint blue wash, 0% false. It needs a pick per image, which costs the batch workflow something.

## Compare and contrast

| | Handpaint visualiser | Woodii Chroma mode |
|---|---|---|
| Input | Any rendered JPEG/TIFF/PNG, batch folder | Linear raw counts, flat-fielded, one capture in a web app |
| Signal | Scalar C\*ab, or C\* relative to L\*-band median | 2-D optical-density vector off a fitted "silver axis" |
| Reference for "unpainted" | The whole image's histogram | User picks: base (paper) and untinted image |
| Threshold | Histogram tail; percentile, Otsu, fixed as options | Multiples of noise measured in the picks, scaled by density |
| Hue | Discarded for detection | Kept: hue map, palette plot, unmixing per colourant |
| Masks | Minimum component area (100 px) | Dark, saturated and edge/misregistration masks |
| Extra bands | None | IR and UVL references, disagreement map, NNMF |
| Area metrics | In the footer, JSON and CSV | Deliberately none ("a visualiser, not a measuring tool") |
| Tests | None | 38 maths tests on synthetic prints, plus app tests |
| Status | In use | Removed after the first real run ("a bust") |

They fail in opposite directions. The visualiser is easy to run on anything and produces a readable montage, but its detection logic is weak. Woodii's maths is principled, yet it did not survive real prints. The notes record the verdict, not the reason, so I can't say why. Its own tests show optical density stops adding under opaque paint, and it needs raw captures plus careful picks.

Given your aim, Woodii's "no area metrics, qualitative only" rule fits better than the visualiser's current output. The visualiser prints area percentages and carries Jaccard sensitivity runs, float TIFF sidecars and "FADGI-compliant" and "scientific integrity" wording. All of that invites a quantitative reading the method can't support.

## Smaller points in the visualiser

- **Chroma boost amplifies around neutral.** A warm print turns orange. Boosting around the substrate's colour would keep the paper quiet and make only paint stand out.
- **Faint paint is drawn faintest.** The lowest tier tops out at 40% opacity on a near-black background, which works against a presence viewer.
- **The 100 px component filter is not scaled to image size.** On small scans it removes small touches (lips, jewellery); my 8×8 px touch was dropped.
- **Images over 100 MP are refused by default**, which excludes 150 MP medium-format captures. `--max-image-pixels` does not update Pillow's own limit, so Pillow warns above 100 MP and refuses above 200 MP.
- **Colour management is larger than the aim needs.** Three analytic spaces, Bradford adaptation and a separate 16-bit path are where the 4.1 bugs were. A 16-bit file with an unrecognised profile is silently read as sRGB.
- **Speed.** Sensitivity analysis is on by default and adds five connected-component passes per feature space. The LRC loop makes 100 full-image masks.
- **Housekeeping.** The script has no `.py` extension and carries its version in the filename; v3.0 sits beside it. The README still says "distance from neutral gray (128, 128)". `matplotlib` is listed as required though described as optional. Failed images are left out of the CSV.

## Recommendation

Keep the visualiser's shell (batch, montage, provenance) and replace its detection core with a reference-pick, hue-aware baseline. Drop the area figures from the montage footer, and boost around the substrate. I'd leave Woodii's IR/UVL references and unmixing out unless you want to revisit why it failed on real prints.

I changed nothing in either repository. The synthetic inputs, outputs and scripts are in `/tmp/claude-0/-home-user/a732aacf-32bd-581b-a61a-7496ca71b081/scratchpad`; the pink-wash montage is `/tmp/claude-0/-home-user/a732aacf-32bd-581b-a61a-7496ca71b081/scratchpad/out/F_warm_strong_pink__697483d6/lrc/F_warm_strong_pink__697483d6_montage.png`.
