# The author's answers, and what they change

22 November 2026, after the run. These are the author's answers, verbatim, to the four questions in TODO.md. Where they
conflict with the synthesis, they win.

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
