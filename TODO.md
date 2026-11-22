# Rebuild plan

The aim: help a person see where paint is, or may be, on a monochrome photograph. It is a visualiser, not a measuring
tool:
- no areas, counts or statistics;
- no claim to colorimetric accuracy;
- it never claims a place is unpainted.

**Two tools:**
- **The visualiser** (this repository) is a viewer. It takes one visible photograph per print and nothing else. The
  photographs are ProPhoto RGB, taken under controlled lighting with DSLR or mirrorless cameras and calibrated with ICC
  profiles.
- **A Woodii module** comes later, like Chroma mode. It takes a registered visible and near-infrared (NIRR) pair from
  Woodii's linear output.

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
- [x] The xpollinate review, and your answers and notes of 22 Nov (`xpollinate/rebuild/03-author-answers.md`).

## Decided

- **The visualiser takes one photograph per print, and nothing else.**
  - The departure picture comes from that one photograph.
  - It takes no infrared, ultraviolet, second capture or session control. Infrared goes to the Woodii module.
  - The known-unpainted print checks the capture setup (the gate below); it is not an input.
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

## Still open

- [ ] **For the module:** which near-infrared band does Woodii's IRR record (behind a 720 nm or an 850 nm filter, say)?
      It decides which colourants vanish: most grow more transparent further into the infrared.
- [ ] **When the module starts:** where the shared core lives. Recommended: written once here, as a plain module
      without a window. Woodii keeps a pinned copy, with a test that both give the same pictures from the same
      photograph.

## The gate: test captures before any code

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

## Build the visualiser, in this order (each step tried on the test captures before the next)

1. [ ] **Batch, one photograph per print:**
   - Load: through the embedded ICC profile to CIELAB (4.1.5's decoding); about 3,000 px long edge.
   - Find the print and its paper border.
   - Hatch what cannot be judged: clipped, near-white, near-black.
   - The reference, "this print unpainted":
     - the print's own tone as a smooth curve in lightness;
     - fitted to votes of places;
     - a high-breakdown fit, so paint cannot take it over;
     - a light term across the frame only if the setup check shows a gradient.
   - **Main output: the boosted picture**, the print's own tone drawn neutral grey with departures exaggerated, beside
     the original. Two boosts are compared at the gate:
     - the plain ×4 boost;
     - **an updated DStretch**, a decorrelation stretch with three guards:
       - it stretches the departures, not the photograph. The print's own tone is removed first; otherwise the
         stretch pushes hardest where the print varies least, and its toning and yellowed paper become the loudest
         colour;
       - its statistics come from the unpainted print, not from all pixels: the reference's inliers in batch, and the
         user's boxes in single view (as DStretch's own selection works). Otherwise the amount of paint sets the
         stretch, and a broad wash steers it;
       - it is capped at about 2:1 between directions, so the quietest direction, mostly noise, is not blown up.
   - **The updated DStretch in a few colour spaces** (your suggestion of 22 Nov). Once the print's tone is removed, a
     colour space mostly decides which hue is pushed hardest:
     - the batch writes one picture, balanced;
     - single view adds two or three on keys (reds and pinks; yellows; blues and greens);
     - the gate keeps a space only if it shows a marked faint wash that the balanced one misses.

     No space separates a yellow wash from uneven yellowing of the paper: they are the same colour change.
   - **The departure picture**, "where colour departs from the print's own tone":
     - drawn bright on a dimmed print, so colour-deficient viewers see it too;
     - a fixed threshold in ΔE, raised only by measured pixel noise and never by the paint;
     - faded in from the threshold, with no hard edge.
   - **A check sheet:**
     - the expected-unpainted picture ×4, which should look like the print's own tone with no forms or washes in it;
     - the strip showing how a thin wash looks in this capture at each tone;
     - the words, including "Blank does not mean unpainted".
   - Run the line-up check (pass criterion 5) as soon as the check sheet exists.
2. [ ] **Single view:** a small Tk window (as in v1.2).
   - Batch: folder in, folder out, Run, Cancel.
   - Single view:
     - it opens one print on the boosted picture;
     - keys flip to the original, the expected-unpainted picture and the departure picture;
     - the user may box unpainted areas (cross-checked against one another) and refit.
3. [ ] **Housekeeping:**
   - one `.py` file plus tests, the version in git only;
   - remove `Chroma Diagnostic Tool v3.0`, which does not parse;
   - rewrite the README around what the pictures cannot show, including the known weak point.

## The Woodii module (after the visualiser's step 1 passes the gate)

Like Chroma mode, it lives in Woodii. Its idea is untested.

**Inputs:** Woodii's linear exports, both on VIS's grid.
- **VIS:** linear ProPhoto RGB with its ICC profile (32-bit float by default).
- **NIRR:** the standardised IRR band, linear (one plane or three; 32-bit float by default). Its no-value pixels are
  NaN, and are hatched.
- **Reading:** with tifffile. The module checks each file's description, and refuses Woodii's "picture" TIFFs, which
  have levels applied and are not data.

**The idea: predict "this print unpainted" from the IR.** The silver stays in the IR while most washes vanish.
- The reference is the visible colour as a smooth curve of IR density, per print. It is fitted with the visualiser's
  place votes and high-breakdown fit, with IR density in place of lightness.
- Departures are what the IR does not predict: in colour, and now in lightness too (visible darker than the silver
  explains).
- The pictures are the visualiser's, the boost first.

**What it may add over the visualiser:**
- Faint washes (priority c) show by their darkening as well as their colour.
- Washes matched to the print's own tone, which the visualiser cannot see, may show if they are IR-transparent (dye
  retouching, say). Graphite and carbon stay invisible.
- A stiffer reference:
  - IR and visible density measure the same silver, so their relation is close to straight in density. It bends
    where a print's tone shifts with density.
  - A stiff curve may therefore trim a broad wash confined to some densities (the known weak point).
  - IR does not cure that weak point alone: where most of the print at some density is washed, the votes there are
    still the wash's.

**Where it can mislead:**
- **IR-absorbing colourants** (Prussian blue, carbon-based media, copper greens and blues) read as silver. Their colour
  still departs, but their darkening is explained away.
- **Edges:** residual misregistration and the IR's softer focus make false departures. The noise's edge term takes
  gradients from both frames, or the comparison is made at the IR's sharpness.
- **Toned and printed-out images** can be faint in the IR, which weakens the reference.

**Lessons from Chroma mode,** whose IR reference fitted each channel's density to IR density in the user's untinted
pick:
- fit from votes across the whole print, not from a pick;
- a fixed ΔE floor raised by measured noise, never a noise yardstick alone;
- a curve that can bend with the print's tone, not a straight axis;
- few pictures: no disagreement map, palette plot or unmixing.

**Shared with the visualiser:** decoding to CIELAB, finding the print, hatching, the votes and the fit, the threshold,
the pictures and the words.

**Its gate:** the gate's two prints captured through Woodii, plus a print with Prussian blue or carbon-based paint if
one is to hand. Each is judged beside the visualiser on the same VIS:
1. the visualiser's pass criteria hold;
2. the marked faint washes show at least as well as in the visualiser;
3. IR-absorbing paint is not lost.

## The known weak point

When a broad wash covers most of a print at some tone, it can enter the tool's idea of the unpainted print. Unpainted
areas at that tone then show in the opposite colour. The signature is colour complementary to paint you can see,
following one band of tone.
- **The remedy:** box unpainted areas at those tones in single view.
- **The Woodii module may resist it** (above).
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
