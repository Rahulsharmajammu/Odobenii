# Rebuild plan

The aim: help a person see where paint is, or may be, on a monochrome photograph. It is a visualiser, not a measuring
tool:
- no areas, counts or statistics;
- no claim to colorimetric accuracy;
- it never claims a place is unpainted.

**The inputs:** photographs taken under controlled lighting with DSLR or mirrorless cameras, calibrated with ICC
profiles.

The reasoning and evidence are in `xpollinate/rebuild/`: start with its `README.md`, then `03-author-answers.md`.
All of it comes from synthetic test images, so the real-capture gate below comes before any new code.

## Done

- [x] 4.1.2: areas, counts, statistics, the Jaccard analysis and the numerical TIFFs removed; pictures labelled
      "Visualisation only - not a measurement".
- [x] 4.1.3: the last numbers removed. The README's overclaims are gone, and it states the known limitation.
- [x] 4.1.4: any RGB matrix/TRC ICC profile (eciRGB v2, a camera matrix profile, ...) applied at full bit depth.
      Before, a 16-bit file with such a profile was read as sRGB, up to 12 ΔE wrong.
- [x] The xpollinate review, and your answers of 22 Nov (`xpollinate/rebuild/03-author-answers.md`).

## Decided

- **Captures are controlled and ICC-calibrated.**
  - The departure picture can come from one photograph.
  - Colour decoding through the embedded profile matters, and is now correct for matrix profiles.
- **Chroma mode failed on its method, and its output was too complex.**
  - Few pictures: the boosted picture first.
  - No maps of statistics, palettes or unmixing.
- **Priorities, in order:**
  1. **(a)** never show confident colour on unpainted print;
  2. **(c)** faint washes, which is where the tool helps;
  3. **(b)** moderate and strong paint, which the eye already sees.
- **No boxes in batch runs.** In single view, after the boosted picture is shown, the user may box areas known to be
  unpainted.

## Still open

- [ ] Will the captures come through Woodii, with registered IRR (and UVR)? If so, IRR can serve as a *measured*
      reference for the unpainted print: most washes vanish in the infrared and the silver does not. That is stronger
      than any reference fitted from the visible image alone.
- [ ] Which ICC profiles will the files carry: a working space such as Adobe RGB, ProPhoto or eciRGB v2, or the
      camera profile itself? Matrix profiles are now exact at 16-bit. LUT-based camera profiles go through LittleCMS
      at 8-bit precision, which may be too coarse for the faintest washes.

## The gate: test captures before any code

- [ ] One print known to be unpainted, of the Van Der Zee kind.
- [ ] One print whose **faint washes** (and some moderate or strong paint) a conservator has marked under
      magnification, raking light and UV.
- [ ] Both captured exactly as real captures will be: same camera, lights and profile.
- [ ] Measure how faint the marked washes really are. The plan assumes about 1.3 ΔE, a guess from the test benches.
- [ ] Judge every build by eye, side by side with:
  - 4.1.4;
  - DStretch;
  - a plain boost of the profiled image.

**Pass criteria** (these numbers are for the developer's test, never for the tool's output):
1. **(a) The unpainted print stays quiet.** In its departure picture, a viewer who does not know it is unpainted marks
   no coloured area larger than a fingertip at print scale.
2. **(c) Faint washes show.** The marked faint washes show at least as well as with the baselines, judged by someone
   who knows neither the print nor the tool.
3. **(b) Strong paint comes through.** Moderate and strong paint is not lost or distorted.
4. **No ghost.** A print with a broad wash must not show its *unpainted* areas in colour. This is the known weak point
   (below).
5. **A wrong reference is visible.** Shown a dozen pictures, one made with a deliberately wrong reference, people pick
   the wrong one better than chance.

## Build, in this order (each step tried on the test captures before the next)

1. [ ] **Batch, one photograph per print:**
   - Load: through the embedded ICC profile to CIELAB (4.1.4's decoding); about 3,000 px long edge.
   - Find the print and its paper border.
   - Hatch what cannot be judged: clipped, near-white, near-black.
   - The reference, "this print unpainted":
     - the print's own tone as a smooth curve in lightness;
     - fitted to votes of places;
     - a high-breakdown fit, so paint cannot take it over;
     - a light term across the frame only if the session's unpainted print shows a gradient.
   - **Main output: the boosted picture**, the print's own tone drawn neutral grey with departures exaggerated, beside
     the original. Two boosts are compared at the gate:
     - the plain ×4 boost;
     - an updated DStretch: remove the print's own tone, then stretch what is left by how little the unpainted print
       varies in each colour direction, capped at about 2:1.
   - **The departure picture**, "where colour departs from the print's own tone":
     - drawn bright on a dimmed print, so colour-deficient viewers see it too;
     - a fixed threshold in ΔE, raised only by measured pixel noise and never by the paint;
     - faded in from the threshold, with no hard edge.
   - **The session's known-unpainted print**, captured the same way: if its departure picture shows colour, departure
     pictures are withheld for that session.
   - **A check sheet:**
     - the expected-unpainted picture ×4, read against the known-unpainted print's;
     - the strip showing how a thin wash looks in this capture at each tone;
     - the words, including "Blank does not mean unpainted".
   - Run the line-up check (pass criterion 5) as soon as the check sheet exists.
2. [ ] **Single view:** a small Tk window (as in v1.2).
   - Batch: folder in, folder out, Run, Cancel.
   - Single view:
     - it opens one print on the boosted picture;
     - keys flip to the original, the expected-unpainted picture and the departure picture;
     - the user may box unpainted areas (cross-checked against one another) and refit.
3. [ ] **Woodii IRR, and later UVR**, as an optional measured reference (if you want it).
4. [ ] **A second capture with the lights moved**, only if glossy or mirrored prints show sheen that reads as paint.
       Sheen moves with the lights; paint does not.
5. [ ] **Housekeeping:**
   - one `.py` file plus tests, the version in git only;
   - remove `Chroma Diagnostic Tool v3.0`, which does not parse;
   - rewrite the README around what the pictures cannot show, including the known weak point.

## The known weak point

When a broad wash covers most of a print at some tone, it can enter the tool's idea of the unpainted print. Unpainted
areas at that tone then show in the opposite colour. The signature is colour complementary to paint you can see,
following one band of tone. The remedy is boxing unpainted areas at those tones in single view, or IRR where there is
one. Pass criterion 4 tests it.

## Not now

Each of these waits until a real capture needs it:
- presets;
- multi-scale departures;
- lateral-colour removal;
- paper-margin anchoring;
- self-check statistics;
- a blink animation.

Dropped with the move to controlled captures: phone-specific handling (semantic processing, JPEG 4:2:0 chroma) and the
two-photograph requirement.

## What the tool will never show

Neutral or tone-matched media (graphite, grey retouching, black spotting, white gouache, varnish). Colour that is not
paint (foxing, stains, silver mirroring, uneven toning) shows like paint; telling them apart is for the viewer, at the
object.
