# How Odobenii diverges from the review

25 November 2026. The review's answer is `02-synthesis.md`: section 4, as amended after the final red-team pass, with
its residual risks (section 7) and the red team's verdict (section 8). The current state is Odobenii as merged in
PR #5: the code in `odobenii/`, `TODO.md`, and your answers in `03-author-answers.md`. Where your answers and the
review conflict, your answers win.

## In short

**The core survived intact.** Each of these is built as the review specified:
- votes of places on a 10 × 10 grid, one per 2 L\* band;
- least trimmed squares, then Tukey biweight steps;
- a stiff curve of the print's own tone;
- a threshold the paint cannot raise, T = max(T0, 3σ), faded in from T to 2T;
- the expected-unpainted picture ×4, hatched where the reference is guessing;
- departures drawn bright on a dimmed print;
- the strip, the blank sentence, and no numbers anywhere a person reads.

On your test captures, this core passed the review's own gate criteria, adapted to your priorities.

**The largest differences are yours** (section 1):
- one photograph per print, with no second photograph as a witness and no session control;
- CIELAB in place of log-chromaticity;
- a web app in place of the Tk window;
- the decorrelation stretch.

**About ten differences have no decision of yours behind them** (section 3). Two of them bear directly on the
low-frequency false colour you saw at the gate:
- the strip is drawn from synthetic white noise, not from the capture's own residual;
- the light field across the frame is not built.

## 1. Changed by your decisions

| The review | Now | Your decision |
|---|---|---|
| A second photograph, deliberately different, is the only witness for the departure picture (C); "seen in both", SIFT registration | One photograph per print; C is drawn from it | §5 controlled captures; §6 "no additional images" |
| A known-unpainted control print in every session, processed first; C withheld if it shows colour; D judged against the control's D | No control as an input. The known-unpainted print checks the capture setup, at the gate and when the setup changes | §6 |
| Phone and document-camera captures: HEIC, EXIF make and model, a same-camera warning, comparison at 4:2:0 chroma resolution | DSLR or mirrorless, ICC-calibrated, 16-bit ProPhoto; none of the phone handling | §5 |
| Departures and threshold in log-chromaticity (χ), where a cast and a wash are the same shift at every tone | CIELAB, in ΔE | §5: calibrated captures make CIELAB meaningful |
| Load through LittleCMS to sRGB; drop the analytic Adobe RGB and ProPhoto paths | Each matrix/TRC profile read exactly from its own curves at full bit depth; LittleCMS only for LUT profiles | 4.1.4 and 4.1.5: LittleCMS through Pillow works at 8 bits |
| A 2 × 2 montage, [A \| C] over [D \| B], as the output | Five pictures on keys, the boost first; two side by side or flipped; batch writes separate pictures | §1: the output was too complex |
| Boxes added only if the test captures showed the reference failing | Boxes available in single view from the start | §3 |
| A Tk window | A local web app like Woodii's | §9 |
| The thin wash's strength measured at the gate (about 1.3 ΔE assumed) | Judged by eye: the washes can be seen | §11 |
| No decorrelation stretch (DStretch only as a baseline) | A guarded decorrelation stretch, in CIELAB and density, with three emphases | §2, §7 |

## 2. Settled by the build or by the gate

- **Synthetic evidence only** (residual 1): the gate passed on your real test captures on 23 Nov.
- **Votes with the LTS → MM fit, untested together** (residual 6): built, and through the gate.
- **The broad-wash ghost** (B1, criterion iv): it passed on your test print. It stays possible on other prints, and no
  mechanism prevents it.
- **Can viewers see a wrong reference?** (residual 10, criterion vi): the line-up check passed.
- **B and C used different measures** (B13): both are now CIELAB. In a\*b\*, D + B equals the capture ×4 exactly.
- **The fixed threshold or the median-spread fallback** (B3): the fallback was tied to criterion (iv), which passed,
  so the fixed threshold stays.
- **T0** (residuals 11 and 15): 2 ΔE passed the gate.

## 3. Divergences with no decision behind them

Ordered by how much they matter.

1. **The strip uses synthetic white noise.**
   - The review: a thin wash and a small clear touch set into *this capture's own residual* at each tone.
   - Now: Gaussian noise at the measured pixel noise, and no clear touch.
   - Why it matters: real residual holds texture and low-frequency variation, and white noise holds neither. So the
     strip overstates how visible a thin wash is, and cannot show the low-frequency noise you saw.
   - Proposal: build each cell from real patches of the departure field, taken from unpainted places at that tone,
     and add the clear touch.
2. **No light field across the frame.**
   - The review: the reference is the print's own tone plus a quadratic light field, fitted jointly.
   - Now: the tone curve only. Your answer §5 made the light field conditional on the setup check showing a gradient.
   - Why it matters: if the false colour is a smooth gradient across the frame, this is what would remove it.
   - Proposal: tell me whether it was a gradient or blotches. A gradient is the case for the light field; blotches
     cannot be told from a faint wash.
3. **"Where colour departs" is less sensitive over dark tones.**
   - The review chose χ because there a cast and a transparent wash are the same shift at every tone. In CIELAB the
     same wash gives a smaller ΔE the darker the tone: about 2.3 times less at L\* 30 than at L\* 90. A fixed ΔE
     threshold is therefore less sensitive in the darks. With the same code otherwise, CIELAB lost a painted backdrop
     on the camera agent's bench: 1 % against 83 %.
   - Now: C is in CIELAB. The density stretch shows dark-tone washes in the boost-type pictures, but C does not
     follow.
   - Proposal: an option to draw C in density, judged as the spaces are.
4. **No paper border, so no in-photograph negative control** (B4).
   - The review: find the print and its border automatically; keep the border out of the fit, but judge it, outline
     it, and warn when it shows colour.
   - Now: neither is built. The user may draw the print area, which keeps the rest out of the fit, but nothing
     outside it is judged or warned about.
5. **The edge term is fitted on the judged print** (B5 not adopted).
   - The review: fit κ² on the session control, or failing that on the border ring. On the red team's bench, fitting
     it on the print let paint raise κ² from 0.19 to 0.33.
   - Now: it is fitted on the print's unpainted-looking places (or the boxes), and capped.
   - Note: with no control and no border, the review's remedy is not available. It would return with item 4.
6. **A lone box is used as an anchor.**
   - The review: "a correction smaller than the scatter stands only where boxes at two or more places agree".
   - Now: a single box, or one with no other box at its tones, is used and labelled "not cross-checked".
   - Proposal: use such a box only when its correction is larger than the capture's scatter, or not at all.
7. **T0 is visible and editable.**
   - The review: one developer constant that the user never sees, with no presets.
   - Now: Settings shows T0, the judged tones and the analysis size, labelled for the test captures.
   - Proposal: now that the gate has passed at 2 ΔE, move these behind a developer switch.
8. **Records are thinner.**
   - The review: a JSON per print with the source's SHA-256, the settings, the evidence used and the warnings, and
     words naming the evidence on every picture ("automatic, votes of places" or "with N examined boxes").
   - Now: a batch run writes one record with no hashes, and exported pictures carry neither the file name nor the
     evidence used.
   - Proposal: add the hash, the file name and the evidence. All three are cheap.
9. **No observer test for colour deficiency.**
   - The review's order of work ends with colour-deficient observers on C.
   - Now: C is drawn bright on dim for them, but the check is not in the plan.
   - Proposal: a simulation on the gate captures is cheap, with real observers if you can find them.
10. **Criterion (iii), "C earns its place", was dropped.**
    - The review: if the photograph, D and the boost serve as well without C, drop C's machinery.
    - Now: your gate notes do not say whether C helped beyond the boost and the stretch. Your call.

**Smaller:**
- Clipped areas are not grown by 3 px, so colour fringes around clipped highlights can show.
- Outside the print area is not hatched.
- The boost does not lift the shadows slightly.
- Gamut mapping keeps CIELAB hue, not Oklch hue. At strong boosts, blues can drift towards purple.
- Noise is measured from pixels 3 px apart at analysis size (about 6 px at full size), not 12 px. Both are short
  enough that a smooth wash cancels in the differences. A longer spacing would be safer if a raw converter's noise
  reduction makes the noise correlated over several pixels.
- Hatching can be switched off.
- "All off" makes exactly the plain stretch the review warned about. It is labelled, and there for comparison.

## 4. Beyond the review

- **The decorrelation stretch** with its guards, two spaces and three emphases. Its "statistics from the unpainted
  print" are a 2 × 2 spread of departures. The review dropped such a spread as a threshold ([05]'s yardstick); here it
  only shares gain between directions, capped at 2:1, and never decides what is drawn.
- **Full-resolution viewing** when zoomed in.
- **Exact 16-bit decoding** of every matrix/TRC profile, Woodii's linear exports included.
- **Compare and flip** in the viewer, batch export, and a session that keeps each print's area and boxes.
- **The Woodii module's note** (`docs/colour-maps-vis-irr.md` in Woodii). The IR is the measured witness the review
  could not have from one visible photograph.
