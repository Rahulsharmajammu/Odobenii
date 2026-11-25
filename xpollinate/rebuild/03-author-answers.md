# The author's answers, and what they change

22 November 2026, after the run. These are the author's words, verbatim: answers to the four questions in TODO.md
(§1-4), then later notes on the captures (§5), the inputs (§6), the stretch (§7), the infrared band and where the
code lives (§8), the web app (§9), the Woodii note (§10), and the gate and the name (§11). Where they conflict with
the synthesis, they win.

## 1. Which part of Chroma mode failed?

> "the method failed. in addition the output was too complex to be parsed by a user."

**What it settles.**
- Both the method and the output failed; the picks were not singled out.
- This matches the agents' reading of the code: a yardstick of sensor noise around a straight silver axis, flagging
  unpainted prints whose tone shifts with density (synthesis §2).
- The second half, "too complex to be parsed", is new. Chroma mode offered about 16 views.

**What changes.**
- **Few pictures.** The output is a boosted picture first, with everything else one step away.
- **No new maps of statistics.** No palette plots, unmixing or disagreement maps.
- **The 2 × 2 montage of the synthesis (§4.4) is too much as the main output.** It becomes a check sheet beside the
  boosted picture.

## 2. A second photograph?

> "in principle, i think for a single device capture, this will have to do. perhaps we can do an updated version of
> dstretch for the paint mapper. however, the chroma viewer in woodii allows for recording UVR and IRR images as
> well"

**Reading.** One device. Whether to take a second photograph with it is still open: the author asked for the
two-photograph idea to be explained first.

**What changes.**
- **A single photograph is the normal case.** It gives the boosted picture, the original and the expected-unpainted
  check, and no departure map.
- **"An updated DStretch" becomes a candidate for the boost** **[coordinator, untested]**:
  1. remove the print's own tone (the fitted reference);
  2. decorrelation-stretch what is left, with the stretch set by how little the unpainted print itself varies in each
     colour direction;
  3. cap the stretch so no direction gets more than about twice another, because a warm print's own variation runs
     along yellow–blue.

  It is compared at the gate with the plain ×4 boost and with DStretch itself.
- **Woodii captures have registered IRR and UVR.** These are a stronger second view than a second visible photograph.
  - **IRR:** the silver image stays dark in the infrared, while most transparent dyes and many watercolour pigments
    nearly vanish. IRR is therefore close to a measured picture of the print without its washes. This was Chroma
    mode's IR reference; it failed through its yardstick and its output, not through the idea. Exceptions: some
    colourants absorb in the IR (Prussian blue, carbon-based media), and IR focus differs at edges.
  - **UVR** could show UV-absorbing whites (zinc, titanium), which no colour method can see.
  - Both apply only to Woodii's controlled captures, not to unruly ones. Open question.

## 3. Boxes on unpainted areas?

> "might be dodgy for a batch operation, but in a single view operation might be doable, especially if the viewer is
> served a chroma boosted image first."

**What changes.**
- **No boxes in batch runs.**
- **A single-view mode:**
  - it opens on the boosted picture;
  - the user may box areas known to be unpainted;
  - the tool cross-checks the boxes against one another (synthesis §4.3) and refits.
- **Seeing the boost first lets the user avoid boxing visible colour.** Faint washes the boost does not show remain
  the risk, which the cross-check is there to catch.

## 4. Priorities

> "i think it should be a,c,b, because the user can see moderate and strong paint. it is the faint washes where
> things are helpful."

The order is now:
1. **(a)** never show confident colour on unpainted print;
2. **(c)** faint washes;
3. **(b)** moderate and strong paint, which the eye already sees.

**What changes.**
- **The gate judges faint washes first.**
- **The boost is the main instrument.** In the synthesis it is the picture that shows thin washes as forms (§4.4,
  from [11]).
- **Moderate and strong paint** need only come through undistorted.
- **The departure map matters less for (c).** It shows only a small share of faint washes at a threshold that keeps
  (a) [11].
- **With two photographs** **[coordinator, untested]**, the pair can also feed the boost. Averaging the two photographs'
  departures:
  - adds up the paint;
  - partly cancels light-driven errors, which point different ways in the two shots;
  - lowers noise by about √2.

## 5. Capture conditions (a later note, same day)

> "note that the images provided to this script will be taken in controlled lighting using DSLR or Mirrorless
> cameras, and will be calibrated using ICC profiles."

**What this corrects.** The agents and the coordinator read "unruly visualiser captures" as phone or
document-camera snapshots under uncontrolled light. Much of the synthesis was built for that case.

**No longer needed, or no longer the default:**
- **The second photograph as a witness** (synthesis §4.2–4.4, §5.1). It was there to separate paint from mixed light
  and phone processing. Under controlled light the departure picture can come from one photograph, checked by the
  session's known-unpainted print. A second capture stays useful only for glossy or mirrored prints, with the lights
  moved, to tell sheen from paint.
- **Phone-specific handling:** semantic face and sky processing, 4:2:0 chroma, local tone mapping, auto white
  balance. Comparison at chroma resolution is no longer needed for JPEG 4:2:0. A fitted edge term stays for lens and
  demosaicing fringes.
- **The light field across the frame, always fitted** ([10]). Controlled light makes it small. It is off by default,
  switched on only if the session's unpainted print shows a gradient. History's [06] warning still holds: an
  unguarded plane can hide a painted sky.
- **Log-chromaticity over CIELAB** ([10]). That case was argued under casts and mixed light. With ICC-calibrated
  captures, CIELAB from the profile is meaningful, so the departure and its threshold can be in ΔE.

**Still holds:**
- **The reference is the print's own tone**, per print. Calibration does not remove a print's toning, yellowing or
  split tone.
- **Votes of places and a high-breakdown fit**, so paint cannot become the reference.
- **A threshold the paint cannot raise.**
- **The boosted picture first.**
- **The expected-unpainted check**, read against the session's known-unpainted print.
- **The strip and the blank sentence.**
- **The broad-wash weak point (B1)**, which comes from the object, not the capture.
- **No numbers, and the real-capture gate.**
- **Woodii's Chroma mode failure mechanism.** It applies all the more, because controlled raw-derived captures were
  its own setting.

**New, and done.** Correct colour decoding became central. 4.1.4 applies any RGB matrix/TRC ICC profile (for example
eciRGB v2, or a camera matrix profile) at full bit depth. Before, a 16-bit file with such a profile was read as sRGB:
up to 12 ΔE wrong in tests.

**Better for priority (c).** Calibrated 16-bit captures carry far less noise than phone JPEGs, so faint washes are
easier to separate from capture noise. The thin-wash strength the strip assumes (about 1.3 ΔE) is still to be
measured on the test print.

## 6. Inputs: a viewer, and a Woodii module (later the same day)

> "1) the aim of this is to be a viewer, so assume that there will be no additional images. we can have a secondary
> module for woodi, like the chroma mode, wherein a registered vis and NIRR image is provided. 2) for the visualiser,
> I can specify prophoto. for the woodii module, i think the woodii linear out will be the best"

**What it settles: two tools.**
- **The visualiser is a viewer.** It takes one visible photograph per print, in ProPhoto RGB, and nothing else: no
  IRR, no UVR, no second photograph, no session control.
- **A Woodii module, like Chroma mode, takes a registered VIS and NIRR pair** from Woodii's linear exports:
  - VIS: linear ProPhoto RGB with its ICC profile (32-bit float by default, 16-bit with `--data uint16`);
  - NIRR: Woodii's standardised IRR band on VIS's grid (32-bit float by default; pixels with no value are NaN).

**What changes in the visualiser.**
- **Out of the visualiser:** IRR and UVR (now the module's), and the second capture for sheen.
- **The known-unpainted print becomes a check of the capture setup.** It is made at the gate, and again whenever the
  camera, lights or profile change; the visualiser never asks for it. The expected-unpainted picture is then read on
  its own: it should look like the print's own tone, with no forms in it.

**The module's idea** **[coordinator, untested]**: predict "this print unpainted" from the IR.
- **How.** The silver stays in the IR while most washes vanish. So the reference is the visible colour as a smooth
  curve of IR density, per print, fitted to place votes with the visualiser's high-breakdown fit (IR density in place
  of lightness). Departures are what the IR does not predict.
- **What IR may add:**
  1. **Darkening becomes evidence:** visible darker than the silver explains. A faint wash shows by its darkening as
     well as its colour (priority c).
  2. **Tone-matched media may show** if they are IR-transparent (dye retouching, say), though no visible-only method
     can see them. Graphite and carbon stay invisible: the IR takes them for silver.
  3. **A stiffer reference.** IR and visible density measure the same silver, so their relation is close to straight
     in density, bending where a print's tone shifts with density. A stiff curve may trim a broad wash confined to
     some densities (B1). IR does not cure B1 by itself: where most of the print at some density is washed, the votes
     there are still the wash's.
- **Where it can mislead:**
  - **IR-absorbing colourants** (Prussian blue, carbon-based media, copper greens and blues) read as silver. Their
    colour still departs, but their darkening is explained away.
  - **Edges:** residual misregistration and the IR's softer focus make false departures there.
  - **Toned and printed-out images** can be faint in the IR, which weakens the reference.

**What Chroma mode did with IR.** Its design note (Woodii `docs/chroma-mode-plan.md`, 22 Oct) fitted "each VIS
channel's OD to IR OD in the untinted pick as a curve", beside a straight image axis, and drew a disagreement map. The
module differs in three ways:
- the curve comes from votes across the whole print, not from a pick;
- the threshold is a fixed ΔE floor raised by measured noise, never a noise yardstick alone;
- the output is the visualiser's few pictures, the boost first.

§2 said Chroma mode's IR reference "failed through its yardstick and its output, not through the idea". That is a
reading, not a finding: the agents tested its image axis, and the record does not say how the IR reference did on the
real print.

**New, and done: 4.1.5.**
- **The bug.** Woodii names its linear export's profile "linear ProPhoto RGB (Woodii)". 4.1.4 trusted profile names
  first, so it decoded such a file with ProPhoto's gamma 1.8. In tests it was about 24 ΔE wrong, and 31 ΔE for linear
  sRGB.
- **The fix.** 4.1.5 applies every matrix/TRC profile from its own tone curves, whatever its name. Names now decide
  only for LUT profiles and untagged files.
- **Checked:**
  - A raw converter's ProPhoto (pure gamma 1.8) now decodes exactly; 4.1.4 was 0.29 ΔE off near black.
  - Untagged files are unchanged: 49 of 49 pictures identical.
  - The same print as a Woodii 16-bit linear file and as an sRGB PNG decodes to within 0.02 ΔE.
- **Not changed.** The viewer still cannot read Woodii's 32-bit float TIFFs; the error now says to save as 16-bit.

## 7. A suggestion: a decorrelation stretch in several colour spaces (later the same day)

> "for the viewer utility perhaps a decoorelation stretch with multiple colour spaces is what is needed?"

**Reading.** This extends §2's "updated version of dstretch". DStretch runs one stretch in many colour spaces, each
built to bring out certain hues.

**What changes** **[coordinator, untested]**:
- **The updated DStretch stays the leading candidate for the boost, with three guards** from the benches:
  1. **Stretch the departures, not the photograph.** A plain stretch pushes hardest where the print varies least. On a
     near-neutral print, that turns its toning and yellowed paper into the loudest colour, which breaks priority (a).
  2. **Take the statistics from the unpainted print:** the reference's inliers in batch, the user's boxes in single
     view. From all pixels, the amount of paint sets the stretch, and a broad wash steers it (the synthesis's finding
     that paint must not raise its own bar).
  3. **Cap the stretch at about 2:1** between directions, so the quietest direction, mostly noise, is not blown up.
- **A few colour spaces, not a dozen.** Once the print's tone is removed, a colour space mostly decides which hue is
  pushed hardest. The batch writes one balanced picture; single view adds two or three on keys. Chroma mode's lesson
  (§1) is the limit: each space is one more picture to read.
- **The gate decides which spaces stay**: a space stays only if it shows a marked faint wash that the balanced one
  misses. The baseline becomes DStretch in its own spaces.
- **One limit no space removes:** a yellow wash and uneven yellowing of the paper are the same colour change.

## 8. The infrared band, and where the code lives (later the same day)

> "the woodii IRR records 850nm. I think redundacny is good, so the VIS-IRR module can be in Woodii, whereas the
> single photo viewer can be in the handpaint viewer."

**What it settles.**
- **Woodii's IRR is at 850 nm.** At 850 nm most dyes and many watercolour pigments are transparent, so washes in them
  vanish from the IR, as the module needs. Some colourants do not vanish, and read as silver **[coordinator, general
  knowledge of infrared reflectography; to check on a real print]**:
  - Prussian blue;
  - carbon-based media;
  - copper greens and blues;
  - iron-oxide earths (siennas, umbers, ochres), perhaps in part.
- **Two codebases, no shared code.** The single-photograph viewer stays in this repository; the VIS and NIRR module
  goes in Woodii. This replaces the previous plan's recommendation: one core, with a pinned copy in Woodii.

**What changes.**
- **The module keeps Woodii's conventions.** Its plan, now in `TODO.md`, moves to Woodii when work on it starts.
- **The redundancy is also a check.** The same print's VIS can be exported from Woodii as 16-bit, which the visualiser
  reads since 4.1.5, and run through both tools. The boosts differ by design, but the decoded colour, the print's
  border and the hatching should broadly agree.
- **A new caveat.** Printed-out images (albumen, collodion) may be faint at 850 nm, since their fine silver absorbs
  mostly in the visible. That would weaken the module's reference.

## 9. A web app (later the same day)

> "Okay. Please make a web UI like woodii's for the handprint visualiser that incorporates the multiple colour
> spaces tc"

> "you are building in the decorrelation stretch into this, yes?"

**What it settles.**
- **Single view is a local web app like Woodii's**, not the Tk window of the plan. It runs batches too.
- **It is built before the gate, as the gate's instrument.** The plan had said no new code before the test captures;
  the request overrides that. What the gate rejects comes out.

**What was built** **[coordinator, synthetic prints only]**:
- the decoding of 4.1.5, the reference from place votes with a high-breakdown fit, and the five pictures: the
  photograph, the boost, the stretch, the expected-unpainted picture ×4 and the departure picture;
- the decorrelation stretch in two colour spaces (CIELAB and density) with three emphases (balanced, red-green,
  yellow-blue), and the three guards of §7, each switchable so a plain stretch can be compared;
- the strip, the words, the print area, unpainted boxes with their cross-check, export, and batch runs.

**Not built:** finding the print and its border (the user draws the print area), the light term, and the line-up
check (pass criterion 5), which needs the test captures.

## 10. The Woodii note, and a stretch on Woodii's stacks (later the same day)

> "please push a note to Woodii which uses the 2 image model with the Vis and NIR to create colour maps. i am also
> wondering if it is possible to use decorrelation stretch with the image stacks that Woodii generates?"

**Done.** The module's design moved to Woodii as `docs/colour-maps-vis-irr.md`, linked from Woodii's README and TODO.
`TODO.md` here keeps a pointer, so the two do not drift apart.

**The question** is answered in the note's last section: yes. The decorrelation stretch began as a multiband
technique, and Woodii's stacks are registered, standardised and linear. There are three ways:
- on a composite;
- across the Analysis tab's planes;
- noise-adjusted with MNF's noise.

The guards carry over.

> "as much as i would like it, i think it is best to keep it as a to do until we validate most of the todo tasks
> for woodii"

So the stretch stays a to-do in Woodii's TODO until most of that list is validated.

## 11. The gate, and the name (23 Nov, in TODO.md)

Your notes, made in `TODO.md` itself (commit `85f7892`), verbatim:

> "(note that this is not quantitative, the washes can be seen, which is what matters)"

> "This seems to work, with some low frequency noise appearing as a false colour. This can be flagged as a known
> issue. The user should be reminded that this is not a quantitative tool, but a way to quickly visualise paint
> distributions."

> "[x] this passed" (each of the five pass criteria)

> "rename the app to 'Odobenii'. I will provide an image of a walrus with an ottoman turban as a logo. The walrus is
> selected, as it is a monochromat; and this piepleine is built to ingest monochromatic images (prints and
> photographs) with a paint layer on top."

**What it settles.**
- **The gate passed** on your real test captures, judged by eye beside 4.1.5, DStretch and a plain boost: all five
  criteria. The design is no longer resting on synthetic prints alone.
- **A known issue:** low-frequency noise shows as false colour in the boost and the stretch. The app says so, in its
  list of what the pictures cannot show and under the picture.
- **The reminder:** the app, the README and the plan now call it a way to see quickly how paint is distributed, not a
  quantitative tool.
- **The name: Odobenii.** The package is `odobenii`, the command `python -m odobenii.app`, and the session folder
  `~/odobenii_sessions` (an older `~/handpaint_sessions` is used while it is the only one). The repository keeps its
  name. The logo waits for your image.

**Still open** (in `TODO.md`): the logo; which colour spaces and emphases stay; and whether the false colour was a
gradient (which the light term could remove) or blotches.
