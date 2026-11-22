# Rebuild checklist

The aim: show where paint is, or is not, on a monochrome photograph, from whatever capture comes in
(phone and handheld JPEGs, uneven light, colour casts, glare). A visualiser, not a measuring tool:
no areas, counts or statistics, and no claim to colorimetric accuracy.

## Done (4.1.2)

- [x] Area percentages, component counts, feature statistics, the Jaccard sensitivity analysis and the
      numerical TIFFs removed; pictures labelled "Visualisation only - not a measurement"; histograms opt-in.

## To decide first

- [ ] **How the unpainted reference is given.** Proposed: boxes drawn once per image in a small picker,
      saved beside the image as `<name>.picks.json`; a folder-wide `picks.json` as a default; an automatic
      fallback, labelled as such on the picture, when there are none.
- [ ] **What the boost panel does with the substrate.** Proposed: the substrate's own tone is rendered
      neutral grey and only the departure from it is amplified (paper and image stay quiet, paint stands out).
      The alternative keeps the print's tone and amplifies around it.
- [ ] **Raw C\*ab and LRC:** proposed to drop both for the one new feature below (v4.1 stays in the history).
- [ ] **Layout:** a small package (`load`, `reference`, `feature`, `render`, `cli`) with tests, or one script.

## Pipeline

1. **Load.** Any ICC profile converted to sRGB by LittleCMS; untagged files taken as sRGB. Drop the
   analytic Adobe RGB / ProPhoto paths and the separate 16-bit reader. Apply EXIF orientation.
2. **Working size.** Downscale to about 3000 px on the long edge (area averaging). Presence does not need
   100 MP, and it tames noise and JPEG chroma blocks. Remove the pixel-count refusal.
3. **To CIELAB**, then smooth a\* and b\* only (a 5 px median): JPEG 4:2:0 chroma noise, lightness untouched.
4. **Leave out what cannot be judged:** clipped highlights and glare (any channel near white), near-black
   (chroma is noise there), and anything outside an optional object box. Drawn as a flat hatch or tint,
   never as "no paint".
5. **Reference.** From the picked unpainted areas: the median (a\*, b\*) in each L\* band, smoothed along L\*,
   and the robust spread about it in each band. L\* the picks do not cover is extrapolated and flagged.
   - Automatic fallback: fit on the whole image, set aside pixels far from the fit, refit, a few rounds.
     Extensive paint defeats it; the picture says "automatic reference".
6. **Uneven light (optional, later).** With picks spread across the frame, let the reference's a\*, b\*
   also tilt with position (a plane in x and y). Without that, a cast across the frame reads as faint paint.
7. **Feature.** The vector from the substrate's colour at that L\* to the pixel's (a\*, b\*). Its length, in
   units of the reference's spread, is "how far from substrate"; its angle is "toward which colour".
   A vector, not chroma's size: a blue wash over a warm print lowers chroma and is still found.
8. **Specks.** A small median on the length map in place of the 100 px component filter, so small touches
   (lips, jewellery) survive and single-pixel noise does not.

## Pictures

- **Original** | **Boosted** (step 7's vector times a factor, on the neutralised or kept substrate) |
  **Presence map** (the print in grey; colour laid over it with hue from the vector's angle and opacity
  rising smoothly from about 2 to 5 spreads, so there is no hard edge to read as a boundary).
- Faint signals are shown bright, not faint: opacity saturates early. Strength is a look, not a tier.
- Three sensitivity presets (low, normal, high) in place of numeric thresholds on the command line; the
  value used goes in the JSON only.
- Footer: file name, "Visualisation only - not a measurement", the reference used (picked or automatic),
  and warnings in words (heavy JPEG, glare left out, reference covers little of the tonal range).

## Housekeeping

- [ ] `.py` extension, the version in the file and git only, v3.0 removed from the tree.
- [ ] Tests on synthetic prints: untinted neutral and warm prints show nothing; a wash over a fifth of the
      frame, a painted sky, a wash that lowers chroma and small touches all show; a cast across the frame.
- [ ] Failed images listed in the run log with their reason.
- [ ] `requirements.txt`: matplotlib truly optional; README rewritten for the new flow.
- [ ] Try on real VDZ captures before anything else is added.
