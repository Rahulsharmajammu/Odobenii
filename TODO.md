# Rebuild plan

The aim: help a person see where paint is, or may be, on a monochrome photograph. It is a visualiser, not a measuring
tool:
- no areas, counts or statistics;
- no claim to colorimetric accuracy;
- it never claims a place is unpainted.

**Two tools, written separately on purpose (redundancy):**
- **The visualiser** (this repository) is a viewer. It takes one visible photograph per print and nothing else. The
  photographs are ProPhoto RGB, taken under controlled lighting with DSLR or mirrorless cameras and calibrated with ICC
  profiles.
- **A Woodii module** comes later, in Woodii, like Chroma mode. It takes a registered visible and near-infrared pair
  (NIRR, at 850 nm) from Woodii's linear output.

The reasoning and evidence are in `xpollinate/rebuild/`: start with its `README.md`, then `03-author-answers.md`.
All of it comes from synthetic test images, so the real-capture gate below comes before any new code.

## Done

- [x] 4.1.2: areas, counts, statistics, the Jaccard analysis and the numerical TIFFs removed; pictures labelled
      "Visualisation only - not a measurement".
- [x] 4.1.3: the last numbers removed. The README's overclaims are gone, and it states the known limitation.
- [x] 4.1.4: any RGB matrix/TRC ICC profile (eciRGB v2, a camera matrix profile, ...) applied at full bit depth.
      Before, a 16-bit file with such a profile was read as sRGB, up to 12 ΔE wrong.
- [x] 4.1.5: a matrix/TRC profile is applied from its own tone curves, whatever its name. Before, Woodii's linear
      ProPhoto export was decoded with ProPhoto's gamma 1.8, about 24 ΔE wrong. Woodii's 32-bit float TIFFs are still
      not read; the error now says to save them as 16-bit.
- [x] **The web app** (`python -m handpaint.app`), your request of 22 Nov, built like Woodii's: a first build of
      steps 1 and 2 below, with the guarded decorrelation stretch in two colour spaces and three emphases. It is built
      and tested on synthetic prints only (34 tests), and not yet tried on a real capture.
- [x] The xpollinate review, and your answers and notes of 22 Nov (`xpollinate/rebuild/03-author-answers.md`).

## Decided

- **The visualiser takes one photograph per print, and nothing else.**
  - The departure picture comes from that one photograph.
  - It takes no infrared, ultraviolet, second capture or session control. Infrared goes to the Woodii module.
  - The known-unpainted print checks the capture setup (the gate below); it is not an input.
- **Two codebases, no shared code** (your choice: redundancy is good). The single-photograph viewer stays here; the
  module for VIS and NIRR goes in Woodii.
- **The captures are controlled and ICC-calibrated**, so decoding through the embedded profile matters. It is now
  correct for every matrix/TRC profile, ProPhoto included.
- **Chroma mode failed on its method, and its output was too complex.**
  - Few pictures: the boosted picture first.
  - No maps of statistics, palettes or unmixing.
- **Priorities, in order:**
  1. **(a)** never show confident colour on unpainted print;
  2. **(c)** faint washes, which is where the tool helps;
  3. **(b)** moderate and strong paint, which the eye already sees.
- **No boxes in batch runs.** In single view, after the boosted picture is shown, the user may box areas known to be
  unpainted.
- **Single view is a local web app like Woodii's** (your request of 22 Nov), not a Tk window. It runs batches too; the
  4.1 batch tool stays as it is.

## Still open

Nothing. The gate's test captures are next: run the web app on them.

## The gate: test captures, before anything more is built

- [ ] One print known to be unpainted, of the Van Der Zee kind.
- [ ] One print whose **faint washes** (and some moderate or strong paint) a conservator has marked under
      magnification, raking light and UV.
- [ ] Both captured exactly as real captures will be (same camera, lights and profile) and exported as 16-bit ProPhoto
      TIFF. At 8 bits, rounding alone moved colours by up to 0.65 ΔE in tests, against about 1.3 ΔE for a faint wash.
- [ ] Measure how faint the marked washes really are. The plan assumes about 1.3 ΔE, a guess from the test benches.
- [ ] Judge every build by eye, side by side with:
  - 4.1.5;
  - DStretch, in its own colour spaces;
  - a plain boost of the profiled image.

**Pass criteria** (these numbers are for the developer's test, never for the tool's output):
1. **(a) The unpainted print stays quiet.** In its departure picture, a person who does not know it is unpainted marks
   no coloured area larger than a fingertip at print scale.
2. **(c) Faint washes show.** The marked faint washes show at least as well as with the baselines, judged by someone
   who knows neither the print nor the tool.
3. **(b) Strong paint comes through.** Moderate and strong paint is not lost or distorted.
4. **No ghost.** A print with a broad wash must not show its *unpainted* areas in colour. This is the known weak point
   (below).
5. **A wrong reference is visible.** Shown a dozen pictures, one made with a deliberately wrong reference, people pick
   the wrong one better than chance.

**The setup check.** The unpainted print's capture also checks the capture setup. Repeat it whenever the camera,
lights or profile change. If its departure picture shows colour, departure pictures from that setup are not to be
trusted.

## Build the visualiser (each step tried on the test captures before the next)

The web app (`handpaint/`) is a first build of steps 1 and 2, made before the gate at your request. It is the
instrument for the gate: what the gate rejects comes out.

1. [ ] **Batch, one photograph per print.** Built, except where marked:
   - Load: through the embedded ICC profile (4.1.5's decoding), held as linear ProPhoto RGB and CIELAB. Analysed at
     3,000 px long edge; drawn from the full photograph when zoomed in.
   - **Not built: finding the print and its paper border.** The user draws the print area instead.
   - Hatch what cannot be judged: clipped, near-white, near-black.
   - The reference, "this print unpainted":
     - the print's own tone as a stiff smooth curve in lightness (a P-spline);
     - fitted to votes of places (10 × 10 tiles, one vote per 2 L\* band);
     - least trimmed squares, then Tukey biweight steps, so paint cannot take it over;
     - **not built:** a light term across the frame, only if the setup check shows a gradient.
   - **The boosted picture**, the print's own tone drawn neutral grey with departures exaggerated. Two candidates for
     the gate:
     - the plain boost (×4 by default);
     - **the updated DStretch**, a decorrelation stretch of the departures with three guards. Each guard can be
       switched off, so a plain stretch can be compared:
       - the print's own tone is removed first. Otherwise its toning and yellowed paper are stretched with everything
         else, and show as colour that follows the tones;
       - its statistics come from the unpainted print (the reference's inliers, or the user's boxes, as DStretch's own
         selection works), not from all pixels. Otherwise the amount of paint sets the stretch, and a broad wash
         steers it;
       - it is capped at 2:1 between directions, so the quietest direction, mostly noise, is not blown up.
   - **The updated DStretch in a few colour spaces** (your suggestion of 22 Nov):
     - two spaces: CIELAB (departures as they look) and density (as amounts of colourant). In density, a wash over the
       dark tones shows as strongly as over the light, and so does noise there;
     - three emphases: balanced, red-green and yellow-blue. An emphasis gives 2:1 along its axis, to both directions
       alike, so noise gains no cast;
     - the strength means the same in all of them: the guards and the emphasis only share it out between directions;
     - the gate keeps a space or an emphasis only if it shows a marked faint wash that balanced CIELAB misses.

     No space separates a yellow wash from uneven yellowing of the paper: they are the same colour change.
   - **The departure picture**, "where colour departs from the print's own tone":
     - drawn bright on a dimmed print, so colour-deficient viewers see it too;
     - T = max(T0, 3σ), with σ from shift-difference noise by tone plus an edge term. The edge term is fitted on the
       places the reference holds as unpainted, so paint's own edges can still raise it;
     - faded in from T to 2T. T0 is 2 ΔE for now, a developer setting for the gate.
   - **The check sheet:** the expected-unpainted picture ×4 (hatched where the reference is guessing), the strip, and
     the words.
   - [ ] **Not built: the line-up check** (pass criterion 5). It needs the test captures.
2. [x] **Single view**, as the web app rather than a Tk window:
   - folders or files in, export of the picture shown, and batch runs;
   - keys 1-5 flip between the photograph, the boost, the stretch, the expected-unpainted picture and the departure
     picture; two pictures side by side, or flipped;
   - the user may draw the print area, and box unpainted areas. Boxes are cross-checked: a box that disagrees with
     most of the others at its tones is not used. The reference is then refitted.
3. [ ] **Housekeeping:**
   - the version in git only;
   - remove `Chroma Diagnostic Tool v3.0`, which does not parse;
   - rewrite the README around what the pictures cannot show, including the known weak point (begun for the web app).

## The Woodii module

Its design note is now in Woodii: `docs/colour-maps-vis-irr.md` (pushed 22 Nov, on Woodii's branch
`ccr-32ef416e-z8q8ld`). It covers the two-image model (VIS and IRR at 850 nm), its pictures, where it can mislead, how
it differs from Chroma mode, the redundancy with this tool as a cross-check, and its gate. Its last section answers
whether a decorrelation stretch can be used on Woodii's stacks: yes, on a composite, across the Analysis tab's planes,
or noise-adjusted with MNF's noise.

The two tools share the design but no code, by your choice. The module is tried after this visualiser's step 1
passes the gate.

## The known weak point

When a broad wash covers most of a print at some tone, it can enter the tool's idea of the unpainted print. Unpainted
areas at that tone then show in the opposite colour. The signature is colour complementary to paint you can see,
following one band of tone.
- **The remedy:** box unpainted areas at those tones in single view.
- **On a synthetic bench** (a wash over 80 % of a sky), the stiff curve held without boxes, and boxes brought it closer
  still. Real prints decide.
- **The Woodii module may resist it** (its note, in Woodii).
- **Pass criterion 4 tests it.**

## Not now

Each of these waits until a real capture needs it:
- presets;
- multi-scale departures;
- lateral-colour removal;
- paper-margin anchoring;
- self-check statistics;
- a blink animation;
- UVR in the Woodii module, for UV-absorbing whites.

Dropped:
- with the move to controlled captures: phone-specific handling (semantic processing, JPEG 4:2:0 chroma) and the
  two-photograph requirement;
- with the visualiser taking one photograph: a second capture with the lights moved for sheen, and the session's
  control print.

## What the tool will never show

- **Neutral or tone-matched media:** graphite, grey retouching, black spotting, white gouache, varnish. The Woodii
  module may show the IR-transparent ones (untested).
- **Colour that is not paint shows like paint:** foxing, stains, silver mirroring, uneven toning. Telling them apart is
  for the person looking, at the object.
