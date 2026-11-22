# Rebuild plan

The aim: help a person see where paint is, or may be, on a monochrome photograph, from whatever capture comes in
(phone and document-camera JPEGs, uneven light, colour casts, glare). It is a visualiser, not a measuring tool:
- no areas, counts or statistics;
- no claim to colorimetric accuracy;
- it never claims a place is unpainted.

This plan replaces the checklist of 22 Nov. The reasoning, the evidence and every dissent are in
`xpollinate/rebuild/` (start with its `README.md`). All of that evidence is from synthetic test images, so the
real-capture gate below comes before any new code.

## Done

- [x] 4.1.2: areas, counts, statistics, the Jaccard analysis and the numerical TIFFs removed; pictures labelled
      "Visualisation only - not a measurement".
- [x] 4.1.3: the last numbers removed:
  - the threshold on the montage footer and the console;
  - the computed thresholds in the run log and the JSON;
  - the per-band LRC statistics;
  - the README's "actual pigment", "Tier 1 (Solid)" and "faint residue and solid paint". The README now states the
    known limitation: large painted areas can be missed by the Segmented panel.

## Questions for you, before anything is built

1. **Which part of Woodii's Chroma mode failed on the real print: the method, the picks, or the maps?**
   - The record holds your reason, but not which part: "the results were not very user friendly, and while the
     chroma viewer might be inaccurate it allowed for useful visualisations, which were helpful".
   - "The chroma viewer" there could mean Chroma mode itself, or this visualiser.
   - Four test benches suggest the method itself lit up unpainted prints whose tone shifts with density.
2. **Would you take a second photograph of each print** under different light, ideally with another device or the
   print moved?
   - Yes: the tool can also draw a "where colour departs" picture, from what both photographs agree on. This is
     the only thing that kept false colour on unpainted prints near zero on the test benches.
   - No: the tool gives three pictures per print (the photograph, its assumed unpainted print, and the boost), and
     no departure picture.
3. **Would you mark two to four unpainted areas per print**, checked on the object, when the automatic
   reference visibly goes wrong? This is optional: the tool never needs them.
4. **Is this the right order of priorities?**
   1. never show confident colour on unpainted print;
   2. then show moderate and strong paint;
   3. show faint washes only where two photographs agree.

## The gate: four test captures before any code

- [ ] One print known to be unpainted, of the Van Der Zee kind.
- [ ] One print whose paint a conservator has marked under magnification, raking light and UV.
- [ ] Each photographed twice, the way real captures will be made; the second time under different light, with
      another device or the print moved.
- [ ] Judge every build below on these by eye, side by side with:
  - 4.1.3;
  - a DStretch-style decorrelation stretch;
  - an eyedropper white balance plus steeper Lab curves.
- [ ] Measure how faint the marked thin washes really are. The plan assumes about 1.3 ΔE, a guess from the test
      benches.

**Pass criteria** (these numbers are for the developer's test, never for the tool's output):
1. The unpainted print stays quiet in the departure picture: no coherent area beyond specks in more than 1 pair of
   photographs in 10.
2. Marked moderate and strong paint shows at least as well as with the baselines, judged by someone who knows
   neither the print nor the tool.
3. If the three pictures alone serve as well as all four, the departure picture and its machinery are dropped.
4. A print with a broad wash must not show its *unpainted* areas in the departure picture. This is the known weak
   point (below).
5. Turn on paper-margin anchoring only if it lowers false colour on most captures.
6. Shown a dozen montages, one with a deliberately wrong reference, people pick the wrong one better than chance.

## Build, in this order (each step tried on the test captures before the next)

1. [ ] **One photograph:**
   - Load: ICC to sRGB, untagged as sRGB, EXIF orientation; about 3,000 px long edge.
   - Find the print and its paper border.
   - Hatch what cannot be judged: clipped, near-white, near-black.
   - The reference, "this print unpainted in this photograph": the print's own tone as a smooth curve in lightness,
     plus a smooth light field across the frame.
     - Fitted to votes of places (each tile votes once per tone).
     - A high-breakdown fit (least trimmed squares, then Tukey).
     - Worked in log-chromaticity.
   - Three pictures:
     - **A** the photograph, with the print edge and the paper border outlined;
     - **D** the print as expected unpainted, colour ×4;
     - **B** departures ×4, linear and uncored. This is the "chroma boost around neutral", with the print's own tone
       as neutral.
   - The strip: a thin wash and a clear touch set into this capture's own noise, at each tone.
   - The words, including "Blank does not mean unpainted".
   - Right after D is built, run the line-up check (pass criterion 6).
2. [ ] **Second photograph** (if the answer to question 2 is yes):
   - Registration.
   - **C** "where colour departs from the print's own tone":
     - drawn bright on a dimmed print, only where both photographs depart the same way;
     - fading in from the threshold, with no hard edge;
     - a fixed threshold, set from unpainted controls.

     Marked boxes never stand in for the second photograph.
   - The session control: a known-unpainted print shot the same way.
     - If it shows colour, C is withheld for that session.
     - D is read against the control's D.
3. [ ] **Examined boxes**, only if step 1 or 2 fails on the test captures in a way boxes fix:
   - unpainted areas checked on the object;
   - cross-checked against one another;
   - they correct the reference only;
   - never required.
4. [ ] **Housekeeping:**
   - Restore the v1.2 Tk window: folder in, folder out, Run, Cancel.
   - One `.py` file plus tests; the version in git only.
   - Remove `Chroma Diagnostic Tool v3.0`, which does not parse.
   - Rewrite the README around what the pictures cannot show.
5. [ ] **Observer checks:**
   - Can someone pick out a montage whose reference is wrong?
   - Do viewers with a colour-vision deficiency see C?

## Not now

Each of these waits until a real capture needs it:
- presets;
- multi-scale departures;
- lateral-colour removal;
- paper-margin anchoring;
- self-check statistics;
- a blink animation;
- HEIC.

## The known weak point

When a broad wash covers most of a print at some tone, it enters the tool's idea of the unpainted print. Unpainted
areas at that tone then show in the departure picture in the opposite colour, in both photographs. The signature is
colour complementary to paint you can see, following one band of tone. The remedy is marking unpainted areas at those
tones (question 3). Pass criterion 4 tests it.

## What the tool will never show

Neutral or tone-matched media (graphite, grey retouching, black spotting, white gouache, varnish). Colour that is not
paint (foxing, stains, silver mirroring, uneven toning) shows like paint; telling them apart is for the viewer, at the
object.
