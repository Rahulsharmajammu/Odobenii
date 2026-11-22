# Rebuild plan

The aim: help a person see where paint is, or may be, on a monochrome photograph, from whatever capture comes in
(phone and document-camera JPEGs, uneven light, colour casts, glare). It is a visualiser, not a measuring tool:
- no areas, counts or statistics;
- no claim to colorimetric accuracy;
- it never claims a place is unpainted.

The reasoning and evidence are in `xpollinate/rebuild/`: start with its `README.md`, then `03-author-answers.md`.
All of it comes from synthetic test images, so the real-capture gate below comes before any new code.

## Done

- [x] 4.1.2: areas, counts, statistics, the Jaccard analysis and the numerical TIFFs removed; pictures labelled
      "Visualisation only - not a measurement".
- [x] 4.1.3: the last numbers removed (threshold on the footer and console, thresholds in the run log and JSON, the
      per-band LRC statistics). The README's overclaims are gone, and it states the known limitation.
- [x] The xpollinate review, and your answers of 22 Nov (`xpollinate/rebuild/03-author-answers.md`).

## Decided by your answers

- **Chroma mode failed on its method, and its output was too complex.**
  - Few pictures: the boosted picture comes first.
  - No maps of statistics, palettes or unmixing.
- **Priorities, in order:**
  1. **(a)** never show confident colour on unpainted print;
  2. **(c)** faint washes, which is where the tool helps;
  3. **(b)** moderate and strong paint, which the eye already sees.
- **One device.** A single photograph is the normal case.
- **No boxes in batch runs.** In a single-view mode, after the boosted picture is shown, the user may box areas known
  to be unpainted.

## Still open

- [ ] Having read how it works, will you try a second photograph with the same device? (See "Two photographs" below.)
- [ ] Should the paint mapper accept Woodii's registered IRR, and later UVR, as an optional second view?

## The gate: test captures before any code

- [ ] One print known to be unpainted, of the Van Der Zee kind.
- [ ] One print whose **faint washes** (and some moderate or strong paint) a conservator has marked under
      magnification, raking light and UV.
- [ ] Photograph each with your device, as real captures will be made. If you will try two photographs, take the
      second as described below.
- [ ] Measure how faint the marked washes really are. The plan assumes about 1.3 ΔE, a guess from the test benches.
- [ ] Judge every build by eye, side by side with:
  - 4.1.3;
  - DStretch;
  - an eyedropper white balance plus steeper Lab curves.

**Pass criteria** (these numbers are for the developer's test, never for the tool's output):
1. **(a) The unpainted print stays quiet.** A viewer who does not know it is unpainted marks no coloured area larger
   than a fingertip at print scale in its boosted picture. With pairs, its departure picture shows no coherent area
   beyond specks in more than 1 pair in 10.
2. **(c) Faint washes show.** The marked faint washes show at least as well as with DStretch or the eyedropper
   baseline, judged by someone who knows neither the print nor the tool.
3. **(b) Strong paint comes through.** Moderate and strong paint is not lost or distorted.
4. **No ghost.** A print with a broad wash must not show its *unpainted* areas in colour. This is the known weak
   point (below).
5. **A wrong reference is visible.** Shown a dozen pictures, one made with a deliberately wrong reference, people pick
   the wrong one better than chance.

## Build, in this order (each step tried on the test captures before the next)

1. [ ] **Batch, one photograph per print:**
   - Load: ICC to sRGB, untagged as sRGB, EXIF orientation; about 3,000 px long edge.
   - Find the print and its paper border.
   - Hatch what cannot be judged: clipped, near-white, near-black.
   - The reference, "this print unpainted in this photograph":
     - the print's own tone as a smooth curve in lightness, plus a smooth light field;
     - fitted to votes of places;
     - a high-breakdown fit, in log-chromaticity.
   - **Main output: the boosted picture**, the print's own tone drawn neutral grey with departures exaggerated, beside
     the original. Two boosts are compared at the gate:
     - the plain ×4 boost;
     - an updated DStretch: remove the print's own tone, then stretch what is left by how little the unpainted print
       varies in each colour direction, capped at about 2:1.
   - **A check sheet:**
     - the expected-unpainted picture ×4, judged against the session's known-unpainted print;
     - the strip showing how a thin wash looks in this capture at each tone;
     - the words, including "Blank does not mean unpainted".
   - Run the line-up check (pass criterion 5) as soon as the check sheet exists.
2. [ ] **Single view:** a small Tk window (as in v1.2).
   - Batch: folder in, folder out, Run, Cancel.
   - Single view:
     - it opens one print on the boosted picture;
     - keys flip to the original and to the expected-unpainted picture;
     - the user may box unpainted areas (cross-checked against one another) and refit.
3. [ ] **Two photographs** (if you will try them):
   - registration;
   - the departure picture "where colour departs from the print's own tone", drawn only where both photographs depart
     the same way, faded in from the threshold;
   - for faint washes, the two photographs' departures averaged in the boost (to test);
   - the session's known-unpainted print photographed the same two ways. If it shows colour, departure pictures are
     withheld for that session.
4. [ ] **Woodii IRR, and later UVR**, as an optional second view (if you want it).
5. [ ] **Housekeeping:**
   - one `.py` file plus tests, the version in git only;
   - remove `Chroma Diagnostic Tool v3.0`, which does not parse;
   - rewrite the README around what the pictures cannot show, including the known weak point.

## Two photographs: what they are for

**The problem.** In one photograph, the light, the lens and the phone also put colour on the print:
- warm window light on one side;
- colour fringes along edges;
- corner shading;
- glare;
- the phone's own processing.

A faint wash looks just like these. From one photograph no method can tell them apart; it can only guess.

**The idea.** Paint is fixed to the print, while light, glare and lens effects are fixed to the capture. So take a
second photograph that changes the capture but not the print. Colour that stays at the same place on the print, in
the same direction, in both photographs is probably on the print. Colour that moves or changes is the capture.

**How to take the second one with the same device:**
- **Change the light across the print.** Turning the print 180° under the same light is enough.
- **Change where the print sits in the frame.** Shift it off-centre, or change the distance, so the lens's fringes and
  corner shading fall on other parts of the print. Turning a centred print does not do this.
- **Use the same camera mode both times**, preferably a Pro or RAW mode. A phone's face and sky processing would be
  the same in both shots and would survive.

**What the tool does with the pair:**
1. It lines the second photograph up onto the first automatically. The print is flat, so one perspective warp does it.
2. It works out "unpainted" for each photograph separately.
3. It draws colour in the departure picture only where both depart the same way.
4. Colour seen in one photograph only is hatched.

**What it cannot fix:**
- things on the print that are not paint (foxing, stains, mirroring);
- the broad-wash weak point below;
- processing the phone applies identically to both shots.

On the test benches, the pair brought false colour on unpainted prints from up to 44% down to about 0–0.5%, at some
cost in faint-wash detection. The averaged boost (build step 3) is meant to win that back.

## The known weak point

When a broad wash covers most of a print at some tone, it enters the tool's idea of the unpainted print. Unpainted
areas at that tone then show in the opposite colour, in both photographs if there are two. The signature is colour
complementary to paint you can see, following one band of tone. The remedy is boxing unpainted areas at those tones in
single view. Pass criterion 4 tests it.

## Not now

Each of these waits until a real capture needs it:
- presets;
- multi-scale departures;
- lateral-colour removal;
- paper-margin anchoring;
- self-check statistics;
- a blink animation;
- HEIC.

## What the tool will never show

Neutral or tone-matched media (graphite, grey retouching, black spotting, white gouache, varnish). Colour that is not
paint (foxing, stains, silver mirroring, uneven toning) shows like paint; telling them apart is for the viewer, at the
object.
