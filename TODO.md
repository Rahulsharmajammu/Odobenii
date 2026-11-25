# Odobenii: the rebuild plan

The aim: help a person see where paint is, or may be, on a monochrome photograph. It is a way to see quickly how paint
is distributed, not a quantitative tool:
- no areas, counts or statistics;
- no claim to colorimetric accuracy;
- it never claims a place is unpainted.

**Two tools, written separately on purpose (redundancy):**
- **Odobenii** (this repository, the visualiser) is a viewer. It takes one visible photograph per print and nothing
  else. The photographs are ProPhoto RGB, taken under controlled lighting with DSLR or mirrorless cameras and calibrated
  with ICC profiles.
- **A Woodii module** comes later, in Woodii, like Chroma mode. It takes a registered visible and near-infrared pair
  (NIRR, at 850 nm) from Woodii's linear output.

The reasoning and evidence are in `xpollinate/rebuild/`: start with its `README.md`, then `03-author-answers.md`.
The design came from synthetic test images. The gate on your real test captures passed on 23 Nov (below).

## Done

- [x] 4.1.2: areas, counts, statistics, the Jaccard analysis and the numerical TIFFs removed; pictures labelled
      "Visualisation only - not a measurement".
- [x] 4.1.3: the last numbers removed. The README's overclaims are gone, and it states the known limitation.
- [x] 4.1.4: any RGB matrix/TRC ICC profile (eciRGB v2, a camera matrix profile, ...) applied at full bit depth.
      Before, a 16-bit file with such a profile was read as sRGB, up to 12 ΔE wrong.
- [x] 4.1.5: a matrix/TRC profile is applied from its own tone curves, whatever its name. Before, Woodii's linear
      ProPhoto export was decoded with ProPhoto's gamma 1.8, about 24 ΔE wrong. Woodii's 32-bit float TIFFs are still
      not read; the error now says to save them as 16-bit.
- [x] **The web app** (`python -m odobenii.app`), your request of 22 Nov, built like Woodii's: a first build of
      steps 1 and 2 below, with the guarded decorrelation stretch in two colour spaces and three emphases.
- [x] **The gate** (23 Nov): your two test captures, judged by eye beside 4.1.5, DStretch and a plain boost. All five
      pass criteria passed. One known issue came out of it: broad, soft patches of colour (below).
- [x] **Renamed Odobenii** (your note of 23 Nov): the package, the command, the page and the session folder. The
      logo waits for your image.
- [x] The xpollinate review, and your answers and notes of 22 Nov (`xpollinate/rebuild/03-author-answers.md`).

## Decided

- **The visualiser takes one photograph per print, and nothing else.**
  - The departure picture comes from that one photograph.
  - It takes no infrared, ultraviolet, second capture or session control. Infrared goes to the Woodii module.
  - The known-unpainted print checks the capture setup (the gate below); it is not an input.
- **Two codebases, no shared code** (redundancy is good). The single-photograph viewer stays here; the
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
- **It is a way to see quickly how paint is distributed, not a quantitative tool,** and the app reminds the user so
  (your note of 23 Nov).
- **The name is Odobenii,** for the walrus, a monochromat: the tool looks at monochrome prints and photographs with a
  paint layer on top (your note of 23 Nov).
- **It works on photographs already taken** (your answer of 25 Nov). Nothing in it may depend on a second shot, or on
  a check made when the photograph was taken. The viewer inspects the photograph before any call on presence or
  absence.

## Still open

- [ ] **The logo:** your image of a walrus in an Ottoman turban. It replaces the stand-in,
      `odobenii/app/static/logo.svg` (a PNG works too: say which and I will point the page at it).
- [ ] **Which colour spaces and emphases stay.** The plan keeps density, red-green and yellow-blue only if one showed
      a marked faint wash that balanced CIELAB missed. Your call, from what you saw at the gate.

**From the divergence check** (25 Nov, `xpollinate/rebuild/04-divergence.md`): where the build differs from the review
with no decision of yours behind it. Your answers of 25 Nov:
- [x] **The strip:** rebuilt from the print's own surface (your "good to try"), then removed the same day (your word:
      it hints at a measurement, and the colour accuracy that a 1.3 ΔE wash assumes is not there).
- [x] **The departure picture earns its place** (the review's criterion iii): it was useful. It stays.
- [x] **The light term:** not the remedy, since the false colour was blotches.
- [x] **T0 and the developer settings stay visible; the records stay as they are** (your word).
- [ ] **"Where colour departs" in density as an option**, for washes over dark tones (your "hm": open).
- [ ] **Boxes as checks.** Boxes already do part of the paper border's work: with boxes, the edge term is fitted on
      them, not on the print, and they anchor the reference. What they cannot do is test it, since a box that sets the
      reference cannot also check it. A box could be marked "check": kept out of the fit, judged like the print, and
      named if it shows colour. Proposed.
- [x] **A lone box** is no longer used: a box needs a second one, in another part of the print, at the same tones
      (your rule of 25 Nov).
- [ ] **A colour-deficiency check** of "Where colour departs": kept as a to-do (your word).

**From the reviewers, point by point** (25 Nov, `xpollinate/rebuild/05-reviewers.md`): what the twelve reports add to
the divergence check. Your answers of 25 Nov:
- [x] **What the blotches are:** the test (a second shot, the print turned) is not feasible, since Odobenii works on
      photographs already taken. The known issue now says the patches may come from the capture or from the print.
- [x] **The strip:** removed (your word), with the ΔE figure the page gave for a faint wash.
- [ ] **"Where colour departs": keep it, or leave it out?** Your question. The recommendation (`05-reviewers.md`) is to
      leave it out. The three items below wait on it.
  - [ ] **The edge term,** if it stays: fit it as the slope of the leftover colour against the squared gradient, so
        blotches fall into the intercept. Tried on a synthetic print.
  - [ ] **Safeguards,** if it stays: stripes over the tones where the reference is guessing; its premise in its words.
  - [ ] **Dark tones,** if it stays: [01]'s normalisation (your "fair").
- [x] **Boxes:** two or more, in different parts of the print, at the same tones (your rule). Boxes outside the print
      area, or too small to judge, are not used, and the stretch's statistics never come from outside the print area.
- [x] **Three sentences corrected:** neutral media show where the print's tone is not neutral; a wash over the whole
      print leaves no sign; sharp changes in lightness can raise the threshold.
- [ ] **More evidence, from photographs already taken:** prints known to be unpainted, of several kinds (warm, toned,
      yellowed, mirrored, glossy), and a painted print with a broad wash (criterion 4), run as a batch and judged by
      eye with the gate's criteria.

## The gate: passed on your test captures (23 Nov)

- [x] One print known to be unpainted, of the Van Der Zee kind.
- [x] One print whose **faint washes** (and some moderate or strong paint) a conservator has marked under
      magnification, raking light and UV.
- [x] Both captured exactly as real captures will be (same camera, lights and profile) and exported as 16-bit ProPhoto
      TIFF. At 8 bits, rounding alone moved colours by up to 0.65 ΔE in tests, against about 1.3 ΔE for a faint wash.
- [x] How faint the marked washes really are. Your note: not measured, since the tool is not quantitative; the washes
      can be seen, which is what matters.
- [x] Every build judged by eye, side by side with:
  - 4.1.5;
  - DStretch, in its own colour spaces;
  - a plain boost of the profiled image.

  Your note: "This seems to work, with some low frequency noise appearing as a false colour." It is flagged as a known
  issue (below), and the user is reminded that this is not a quantitative tool, but a way to quickly visualise paint
  distributions.

**Pass criteria** (these numbers are for the developer's test, never for the tool's output). All five passed:
1. **(a) The unpainted print stays quiet.** In its departure picture, a person who does not know it is unpainted marks
   no coloured area larger than a fingertip at print scale. **Passed.**
2. **(c) Faint washes show.** The marked faint washes show at least as well as with the baselines, judged by someone
   who knows neither the print nor the tool. **Passed.**
3. **(b) Strong paint comes through.** Moderate and strong paint is not lost or distorted. **Passed.**
4. **No ghost.** A print with a broad wash must not show its *unpainted* areas in colour. This is the known weak point
   (below). **Passed.**
5. **A wrong reference is visible.** Shown a dozen pictures, one made with a deliberately wrong reference, people pick
   the wrong one better than chance. **Passed.**

And the review's criterion (iii), asked after the gate: the departure picture was useful beside the boost and the
stretch, so it stays (your answer of 25 Nov).

**The setup check.** The unpainted print's capture also checks the capture setup. Repeat it whenever the camera,
lights or profile change. If its departure picture shows colour, departure pictures from that setup are not to be
trusted. It applies only to new photography: photographs already taken have none (your answer of 25 Nov).

## Build the visualiser (each step tried on the test captures before the next)

The web app (`odobenii/`) is a first build of steps 1 and 2, made before the gate at your request. It passed the gate
on 23 Nov.

1. [x] **Batch, one photograph per print.** Built and through the gate, except where marked:
   - Load: through the embedded ICC profile (4.1.5's decoding), held as linear ProPhoto RGB and CIELAB. Analysed at
     3,000 px long edge; drawn from the full photograph when zoomed in.
   - [ ] **Not built: finding the print and its paper border.** The user draws the print area instead.
   - Hatch what cannot be judged: clipped, near-white, near-black.
   - The reference, "this print unpainted":
     - the print's own tone as a stiff smooth curve in lightness (a P-spline);
     - fitted to votes of places (10 × 10 tiles, one vote per 2 L\* band);
     - least trimmed squares, then Tukey biweight steps, so paint cannot take it over;
     - [ ] **not built:** a light term across the frame, only if the setup check shows a gradient. It may answer
       the known issue, if that false colour is a gradient across the frame.
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
     - a space or an emphasis stays only if it showed a marked faint wash that balanced CIELAB missed (still open,
       above).

     No space separates a yellow wash from uneven yellowing of the paper: they are the same colour change.
   - **The departure picture**, "where colour departs from the print's own tone":
     - drawn bright on a dimmed print, so colour-deficient viewers see it too;
     - T = max(T0, 3σ), with σ from shift-difference noise by tone plus an edge term. The edge term is fitted on the
       places the reference holds as unpainted, so paint's own edges can still raise it;
     - faded in from T to 2T. T0 is 2 ΔE, as it passed the gate.
   - **The check sheet:** the expected-unpainted picture ×4 (hatched where the reference is guessing) and the words.
     The strip was removed on 25 Nov (your word).
   - [x] The line-up check (pass criterion 5): passed at the gate.
2. [x] **Single view**, as the web app rather than a Tk window, through the gate:
   - folders or files in, export of the picture shown, and batch runs;
   - keys 1-5 flip between the photograph, the boost, the stretch, the expected-unpainted picture and the departure
     picture; two pictures side by side, or flipped;
   - the user may draw the print area, and box unpainted areas. A box is used only inside the print area, and only
     where a box in another part of the print covers its tones and agrees with it; a box that disagrees with most of
     the others at its tones is not used. The reference is then refitted.
3. [ ] **Housekeeping:**
   - the version in git only;
   - remove `Chroma Diagnostic Tool v3.0`, which does not parse;
   - rewrite the README around what the pictures cannot show, including the known weak point and the known issue
     (begun for the web app).

## The Woodii module

Its design note is now in Woodii: `docs/colour-maps-vis-irr.md` (pushed 22 Nov, on Woodii's branch
`ccr-32ef416e-z8q8ld`). It covers the two-image model (VIS and IRR at 850 nm), its pictures, where it can mislead, how
it differs from Chroma mode, the redundancy with this tool as a cross-check, and its gate. Its last section answers
whether a decorrelation stretch can be used on Woodii's stacks: yes, on a composite, across the Analysis tab's planes,
or noise-adjusted with MNF's noise.

The two tools share the design but no code, by your choice. This visualiser's step 1 has passed the gate; the module
waits in Woodii's TODO, under "After 1.0", and the stretch on Woodii's stacks stays a to-do until most of Woodii's list
is validated (your word of 22 Nov).

## The known weak point

When a broad wash covers most of a print at some tone, it can enter the tool's idea of the unpainted print. Unpainted
areas at that tone then show in the opposite colour. The signature is colour complementary to paint you can see,
following one band of tone.
- **The remedy:** box unpainted areas at those tones in single view.
- **On a synthetic bench** (a wash over 80 % of a sky), the stiff curve held without boxes, and boxes brought it closer
  still.
- **On your test captures** (23 Nov), pass criterion 4 passed. It stays possible on other prints.
- **The Woodii module may resist it** (its note, in Woodii).

## Known issue: broad, soft patches of colour (from the gate, 23 Nov)

Broad, soft patches of colour can show in the boost and the stretch where there is no paint. They may come from the
capture (its light, lens or noise) or from the print itself (uneven toning, local yellowing, mat burn), exaggerated with
everything else. A faint wash looks the same, so no picture can tell them apart by colour alone.
- **The app says so:** in the Check tab's list of what the pictures cannot show, and under the picture.
- **The reminder:** every picture is labelled a visualisation, not a measurement. Odobenii is a way to see quickly how
  paint is distributed, not a quantitative tool.
- **It is blotches** (your answer of 25 Nov), not a gradient across the frame, so the light term would not remove it.
- **Telling them apart is the viewer's,** at the photograph and the object (your answer of 25 Nov). Odobenii works on
  photographs already taken, so a second shot is not part of it.

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
