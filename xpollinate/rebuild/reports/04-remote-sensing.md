<!-- Saved verbatim by the coordinator from the agent's hand-back (the harness refused the agent's own write to
/home/user/xpw/9e3d5c/report.md). The harness's two-space indent is removed; nothing else is changed. -->

# Handpaint visualiser: establishing "unpainted" on uncontrolled captures

*Reviewed from the standpoint of target and anomaly detection in remote sensing under uncontrolled illumination, 22 November 2026.*

**I could not save this report to `/home/user/xpw/9e3d5c/report.md`.** The Write tool refuses report files from a subagent, and I did not work around that. The complete text is below, ready to save.

Both repositories were only read, with `git log` and `git show`. No real captures were available, so all experiments use synthetic captures. Code, data and figures are in `/home/user/xpw/9e3d5c/work/` (file list at the end).

---

## Verdict

Keep the TODO plan's frame:
- one script or small package;
- a box picker, with picks saved in `<name>.picks.json`;
- an automatic fallback labelled as such;
- exclusions drawn as hatching;
- three presets;
- words in the footer, never numbers.

Change the four things that decide whether the pictures can be trusted:

1. **Model "unpainted" physically and fit it robustly.** Don't use per-L\* band medians in CIELAB. Work in the log-chromaticity of the linearised image, which is a pair of band ratios. There, an unpainted print under uncontrolled light is:
   - a smooth curve in tone, f(L\*): the print's own tone, which may change with density;
   - plus a smooth light field across the frame, g(x, y);
   - plus one constant for each paper-margin or mount box.

   Fit it as an MM-estimator: a least-trimmed-squares start, then a Tukey-biweight step with the scale held fixed.
2. **Give the anchors distinct roles.** A paper margin or mount box measures the light only, because it is a different material from the image highlights. A box on unpainted image fixes the tone curve at its own tones. Boxes are needed only where paint covers most of some tone, and the picture says which tones no box covers.
3. **Show presence as a fixed departure from the reference, floored at three times the local noise.** This is like a fixed vegetation-index cut. It should not be a multiple of a spread fitted to the same pixels: v4.1's LRC and the plan's "2 to 5 spreads" both let a large wash inflate its own yardstick.
4. **Add a fourth panel, "Reference".** It shows what the tool took as unpainted, boosted like the boost panel, with the margin and boxes outlined. The footer carries a few worded checks. For anything that matters, a second capture with the light moved is the check.

**Result on synthetic captures.** These were a split-toned print on yellowed paper, under window-plus-lamp light with glare, through a phone-like tone curve, saturation boost, sharpening, lateral colour and 4:2:0 JPEG. This design was the only one tested that kept false colour on unpainted prints at about 4–6% of pixels while still showing large washes (§5):
- 38% of a painted backdrop automatically;
- 52% with the margin;
- 77% with the margin and one box.

Every earlier iteration either painted 15–48% of unpainted prints or lost faint and large paint entirely.

What would reverse this verdict is in §8.

---

## 1. The iterations, read as background models

Every version made one decision, mostly implicitly: what the unpainted photograph looks like. In detection terms that is the background model. The threshold, which changed in every version, only decides how far from it counts.

| Version (commit, date) | Feature | "Unpainted" taken to be | Threshold | What goes wrong on an uncontrolled capture |
|---|---|---|---|---|
| v1.1 / v1.2 Tk GUI (`9f4420e` Dec 2025; `0949bdc` Jul 2026) | OpenCV 8-bit Lab, C\*ab | neutral everywhere (a\* = b\* = 0) | Histogram peak of 3× chroma, walked down to 1% of the peak count; tiers at the 50th and 85th percentiles of what lies above | A toned print or a colour cast moves the whole substrate off neutral, and the floor rises with it. Faint paint falls below it. A wash that lowers chroma (blue over a warm print) cannot appear. Tiers are relative to each image. |
| v3.0 (`18fbd5a`, Aug 2026) | float CIELAB C\*ab | neutral | the same floor | As above, plus areas, Jaccard stability and numeric TIFFs. |
| v4.0 / 4.1 (`a365ea6`, Aug 2026) | custom RGB→XYZ→Lab; the white point was applied twice, so neutral grey read C\* 6–10 | Raw: neutral. LRC: median and IQR of C\* in each L\* band | noise floor, 90th percentile, Otsu or fixed | LRC is the first reference conditioned on tone, but on chroma magnitude only and from every pixel in the band. A large wash at one tone becomes that band's median. Woodii's decisions call it the "self-suppressing LRC baseline". |
| 4.1.1, 4.1.2 (`6176d62`, `4584a2f`, Nov 2026) | fixes; numbers removed | as 4.1 | `noise_floor` | Unchanged in substance. |
| TODO.md plan | CIELAB (a\*, b\*) vector | median (a\*, b\*) per L\* band, smoothed, from picks or by iterative trimming; the x–y plane "optional, later" | opacity rising from 2 to 5 spreads | §5–6 |
| Woodii Chroma mode (`c9242e7` → `5b1757d`; removed in `de6f9b1`, 22–29 Oct 2026) | optical density of linear raw counts | one straight silver axis through the paper (base pick), set by an untinted pick | Mahalanobis distance in units of the clutter in the picks, k = 4 | Built for copy-stand raw files and removed after its first real print ("a bust"). `decisions-0.4.md` records *what failed* as open. |

What the record already shows:
- **Thresholds kept changing because the reference was wrong.** The sequence was floor → LRC → percentile or Otsu → floor → spreads. No threshold can correct a reference that has taken in the paint, or one that cannot follow the light.
- **Woodii's own decisions hold the two warnings that matter most:**
  - "A windowed baseline absorbs large washes into itself, the self-suppression found in v4.1."
  - From a toy model: "density-dependent tone gave untinted areas a false signal about 5× a light wash."

  The plan's per-band median repeats the first. Woodii's single axis assumed away the second.
- **Complexity ran ahead of data.** The Woodii health check of 29 October counted about 2,000 lines of Chroma mode built before it met one real print. The plan's last line, "Try on real VDZ captures before anything else is added", is its most important.
- **Nobody recorded why Chroma mode failed.** Its tests "check the code, not the method", in their own words. My bench is consistent with two hypotheses, without proving either:
  - a threshold scaled to the small clutter inside the picks, which flags most of the image;
  - a single silver axis on prints whose tone changes with density.

  The test in §8 is designed to double as the missing post-mortem.

---

## 2. The problem in remote-sensing terms

- **Scene, sensor and target.** The scene is a near-planar object with three broad bands. The "sensor" is a phone pipeline: tone curve, white balance, saturation boost, sharpening, 4:2:0 JPEG, and local tone mapping. The target is applied colour on a structured background whose statistics are not stationary.
- **The background has one degree of freedom: tone.** An unpainted monochrome print is a single material whose colour changes only with density, so its pixels lie on a curve.
  - This is the remote-sensing **soil line**. Bare soils lie on a line in red–NIR space, and the Perpendicular Vegetation Index measures departure from it (Richardson & Wiegand 1977). The tasselled cap's brightness axis plays the same role, with greenness at right angles (Kauth & Thomas 1976).
  - Paint is the departure. Woodii's off-axis OD was a straight soil line; the plan's band medians are a non-parametric one.
- **Illumination-tolerant features are band ratios.**
  - Light level and a transparent wash both multiply the channels, so log channel-ratios (log-chromaticity) cancel both the light level and the density under a wash.
  - This is why ratios suppress topographic shading (Holben & Justice 1981), why the spectral angle mapper ignores scale (Kruse et al. 1993), and why log-chromaticity is illuminant-invariant (Finlayson et al. 2006).
  - A colour cast becomes the same shift at every tone. In CIELAB, by contrast, a cast's (a\*, b\*) offset grows roughly with (L\* + 16).
- **The identifiability limit.** A transparent wash and a change in the colour of the light are the same operation: a per-channel multiplication. From one capture they can be told apart only by:
  - **spatial structure**: light varies smoothly and ignores the picture, while paint has edges that follow brushwork. This is Retinex's assumption (Land & McCann 1971).
  - **anchors that share the light but not the paint**: these act like pseudo-invariant features in scene normalisation (Schott, Salvaggio & Volchok 1988), or the bright and dark targets of the empirical line method (Smith & Milton 1999).

  No algorithm escapes this. The design can only make the light model too stiff to follow a painted outline, use anchors, and show what it assumed.
- **Contamination is the real enemy.** Anomaly detectors estimate the background from the very pixels they test, and hand-colouring is often not rare.
  - Global RX (Reed & Yu 1990) whitens by a covariance that contains the paint.
  - Dual-window local RX self-suppresses anything larger than its guard window.
  - IR-MAD's no-change selection (Canty & Nielsen 2008) needs unchanged pixels to be the majority.
  - Per-tone medians fail sooner still: paint only has to dominate one tone band.

  What is needed is a high breakdown point, and an honest signal when it is exceeded.
- **The clutter is structured and heavy-tailed, not sensor noise.** Real backgrounds exceed chi-squared thresholds far more often than Gaussian theory predicts (Manolakis, Marden & Shaw 2003). Here the tails come from:
  - lateral colour and demosaicing fringes at edges (in change detection, the same effect comes from misregistration: Townshend et al. 1992);
  - JPEG chroma blocks;
  - glare, which behaves like sun glint: it adds the light's own colour and has no NIR band to correct it (Hedley, Harborne & Mumby 2005).

---

## 3. The design: components and how they connect

```
load → working image → features (linear RGB, log-chromaticity χ, tone L*, edge strength G)
     → exclusions (hatched) → [picks.json] → reference fit → noise model → departure d, threshold T
     → audit words → pictures (Original | Boost | Presence | Reference + tone strip) → files
```

Package layout, as the plan proposes: `load`, `feature`, `reference`, `audit`, `render`, `picks`, `cli`, with tests.

1. **load.** LittleCMS to sRGB; untagged files taken as sRGB; EXIF orientation applied. Record the JPEG chroma subsampling (v3/v4 already parse it).
2. **Working image.** About 3000 px on the long edge, by area averaging.
3. **Features.**
   - Linear RGB via the sRGB curve. Neutral stays neutral whatever the phone's curve, because the same curve is applied to all three channels.
   - χ = E · ln RGB, where E is the 2×3 orthonormal basis at right angles to (1, 1, 1). This equals Woodii's off-axis OD for a neutral axis.
   - Tone t = L\*.
   - G = |∇ ln Y|, the luminance gradient.
   - A 5-px median on χ. Any wider smoothing must be luminance-guided (guided or joint-bilateral filter; He, Sun & Tang 2013). Plain smoothing across an edge between two densities of a toned print makes a colour that matches neither side. In the bench, a 16-px plain smoothing doubled false colour (4.9% → 10.6%).
4. **Exclusions**, drawn as hatching, never as "no paint":
   - clipped: any channel ≥ 250;
   - near-black: L\* < 12 or any channel ≤ 4;
   - outside the object box;
   - with a margin boxed: anything brighter than the margin's paper (specular).
5. **Reference: χ_ref = f(L\*) + g(x, y) [+ c_k on margin or mount box k].**
   - f is a cubic B-spline with 4 interior knots at quantiles of the photograph's tones. Margin pixels contribute no f term.
   - g is a quadratic in x and y without a constant term: five terms per axis.
   - Fit:
     1. FAST-LTS start (Rousseeuw & Van Driessen 2006) on a stiffer model (f quadratic, g linear), keeping 60% of pixels.
     2. Tukey-biweight IRLS (c = 4.685) with the scale fixed from that start: an MM-estimator (Yohai 1987).
     3. Never let the scale fall below the median-based scale. Without this guard the fit collapsed in testing.
   - Unpainted boxes are weighted ×5 and never down-weighted.
   - For speed, f depends on L\* only, so it can be computed as a 1-D lookup table; g can be computed on a coarse grid.
6. **Noise.**
   - Half the covariance of residual differences 12 px apart, binned by ln Y and median-scaled. This is MNF's shift-difference estimate (Green et al. 1988).
   - Floor singular bins: quantised flat areas difference to exactly zero, which produced NaNs in testing.
   - Plus an edge term κ²G², with κ² fitted from the median squared residual against G² over all pixels.
7. **Departure and presence.**
   - d = |χ − χ_ref|; threshold T = max(T0, 3σ(t, G)).
   - Opacity rises from T to 2.5T; hue comes from the direction of χ − χ_ref.
   - Presets T0 = 0.06 / 0.04 / 0.025, roughly a 6 / 4 / 2.5% change in a channel ratio.
   - Speck filter: a 5-px median.
8. **Pictures.** All four are labelled "Visualisation only - not a measurement".
   - **Original.**
   - **Boost**: (χ − χ_ref) × 4 at the original's luminance, so the substrate renders neutral grey. This is the plan's choice and the most robust picture.
   - **Presence**: the grey print, coloured where the departure exceeds T, with hatching.
   - **Reference**: χ_ref × 4 at the original's luminance, with margin and boxes outlined. Beneath it, a tone strip: f from white to black, with tones no box covers shown hatched.
9. **Audit words.** Only when there is something to do, following Woodii's own rule that "a warning asks something of you, a note does not":
   - "automatic reference", or "reference from the margin and N boxes";
   - "tones L\* a–b: two colours at one tone; box an unpainted area there";
   - "margin not even after the light model";
   - "much of the frame hatched".
10. **Files**, as the plan has them: `<name>.picks.json` with two box kinds, `{"unpainted": [...], "paper": [...]}`; a folder default; a provenance JSON of settings and picks; a run log that lists failures.

The prototype (`work/methods.py`, the `Background` class and `m7_fixed`) is about 400 lines for the proposal. It takes 20–40 s per 1.8 MP image, unoptimised.

---

## 4. For each uncontrolled capture, how should the tool establish what the unpainted photograph looks like, and how would someone looking at its output know when that has gone wrong?

### Establishing it, per capture

1. **Assume nothing about neutrality, white balance or even light.** Unlike v1–v4, the substrate's colour is estimated, not assumed.
2. **Model it physically.** In linearised log-chromaticity, unpainted = the print's tone curve f(L\*) + the light field g(x, y) + one constant per margin or mount box. f follows real silver behaviour:
   - warm mid-tones;
   - selenium toning that changes the shadows first;
   - yellowed highlights.

   g follows window-plus-lamp light: smooth, and too stiff to trace a painted outline.
3. **Estimate it from the capture's own pixels with a high-breakdown fit.** Least trimmed squares needs the unpainted pixels to be a majority of the whole image, not of every tone band. The fixed-scale biweight step then stays with the substrate.
4. **Anchor it where the capture allows.**
   - The paper margin or mount fits g only, with its own constant. Treating the margin as the image's highlight tone is wrong whenever the image highlights carry stain that the bare margin lacks, and my simulator includes that case.
   - Unpainted boxes fix f at their tones. This is essential when paint covers most of a tone; the fully painted print in §5 cannot be rescued by boxes on light tones alone.
   - To keep the margin as an independent check, fit three sides and hold one out.
5. **Say how it was established**: automatic or anchored, and which tones have no anchor.

### Knowing when it has gone wrong: what a viewer sees

| What you see | What it means | What to do |
|---|---|---|
| The Reference panel shows an object in its own colour, e.g. an orange suit (Fig. 2) | Paint was taken into the reference | Box unpainted image at that tone, or read only the Boost against the print |
| The Boost shows a colour your eye does not see, especially the opposite of a colour you can see (an olive suit on an orange-painted suit), or tints things that cannot be painted (margin, deep blacks) | The reference is wrong at that tone | Same as above |
| Colour follows tones, not brushwork: all shadows purple, all highlights yellow, banding along contours | The tone curve is wrong (toning, flare, phone curve) | Box unpainted areas across the tones; check the tone strip |
| Colour drifts smoothly across the frame ignoring the picture, or the margin is not flat | The light model is wrong | Re-shoot with more even light, or read it as light |
| Soft, edgeless clouds over highlights in the light's colour (often bluish), with lowered contrast | Glare | Make a second capture with the light or camera moved: glare moves, paint does not |
| Thin red/cyan or purple/green outlines along light–dark edges | Lateral colour or demosaicing fringes | Ignore them; the edge term removes most |
| Blocky 16-px patches at the edge of a faint wash | JPEG 4:2:0 chroma blocks near the threshold | Trust the soft version in the Boost |
| The margin outline or boxes show colour in Presence | A negative control has lit up (62% of the margin in the automatic run on the fully painted print) | Nothing at those tones is reliable |
| Footer words appear | The tool's own audit fired | Act on the words |

The decisive check for any colour that matters is a second capture, with the light from the other side or the print turned. Paint stays with the print; light and glare do not. This is the multi-temporal logic behind pseudo-invariant features.

---

## 5. Evidence from synthetic captures

**Scenarios.**
- Base image: the skimage astronaut portrait used as the silver density.
- Paints: transparent washes (Beer–Lambert, double pass) and opaque touches.
- Negative controls:
  - N1: a neutral print under even light;
  - N2: a split-toned print on yellowed paper under even light;
  - N3: as N2, under mixed light with glare.
- Painted:
  - P1: lips, cheek wash, gold patch, and a blue wash over warm highlights;
  - P2: a blue backdrop covering 22% of the image, plus face and lips;
  - P3: fully hand-coloured, 65% of the image.

**Scoring.**
- The N columns give false colour: the share of unpainted pixels shown as paint, outside glare.
- The P columns give the share of painted pixels shown.
- AUC is a threshold-free measure of separability.

| Reference (presence rule) | N1 | N2 | N3 | P1 touch / wash / blue-on-warm | P2 backdrop | P2 AUC | P3 large | P3 AUC |
|---|---|---|---|---|---|---|---|---|
| v1–v3: neutral, C\* noise floor | 2 | 1 | 0 | 100 / 43 / 0 | 0 | 0.56 | 4 | 0.85 |
| v4.1 LRC | 6 | 1 | 0 | 100 / 12 / 0 | 0 | 0.32 | 1 | 0.57 |
| TODO plan, automatic (ramp from 2 spreads) | 45 | 34 | 29 | 100 / 94 / 77 | 31 | 0.66 | 23 | 0.61 |
| TODO plan + x–y plane | 45 | 34 | 27 | 100 / 100 / 73 | 18 | 0.55 | 25 | 0.55 |
| TODO plan, from margin + box picks | 23 | 13 | 32 | 100 / 100 / 96 | 69 | 0.78 | 98 | 0.44 |
| Woodii silver axis, automatic | 47 | 41 | 48 | 100 / 76 / 4 | 1 | 0.50 | 7 | 0.42 |
| Woodii silver axis, margin + box picks | 15 | 14 | 11 | 100 / 92 / 85 | 0 | 0.43 | 97 | 0.35 |
| Global RX (MCD) | 45 | 19 | 28 | 100 / 3 / 22 | 0 | 0.27 | 25 | 0.48 |
| Local dual-window RX (121/41 px) | 2 | 1 | 1 | 3 / 0 / 0 | 0 | 0.43 | 0 | 0.52 |
| Proposal, spread-normalised (3–6) | 12 | 4 | 3 | 100 / 96 / 35 | 0 | 0.69 | 11 | 0.64 |
| Proposal, the same in CIELAB | 14 | 6 | 4 | 100 / 96 / 41 | 9 | 0.72 | 24 | 0.64 |
| Proposal, no edge term | 33 | 15 | 14 | 100 / 98 / 48 | 0 | 0.57 | 16 | 0.60 |
| **Proposal, fixed departure, automatic** | 5 | 4 | 5 | 100 / 96 / 47 | 38 | 0.81 | 32 | 0.63 |
| **… + margin** | 5 | 5 | 6 | 100 / 97 / 45 | 52 | 0.89 | 32 | 0.67 |
| **… + margin + 1 box** | 6 | 5 | 5 | 100 / 96 / 46 | 77 | 0.95 | 32 | 0.67 |

Footnotes to the table:
- In P3 my box helper finds no unpainted mid-tone, so "+ 1 box" is the margin alone. Figure 2 shows that boxes on light tones do not fix the mid-tones.
- The "picks" rows show 79–89% false colour on P1 and P3, because tones the picks do not cover are held flat. The plan would flag those tones instead.

### What the table shows

- **v1–v4.1 are clean on unpainted prints only because they are blind.** Their floor rises to the print's own tone (C\* 18–26 on the toned print), so faint, large and blue-on-warm paint all disappear.
- **The TODO reference ranks small paint well (P1 AUC 0.85) but its presence rule paints large areas.**
  - It shows 29–45% false colour at 2 spreads and 12–39% at 3.
  - For a 2-D Gaussian background, 2 per-axis spreads are exceeded at exp(−2) = 13.5% of pixels.
  - The false colour is mostly lateral-colour fringes along every edge, plus the cast; the x–y plane removes the cast but not the fringes (Figure 3).
  - No spread floor gives both low false colour and the backdrop: floors of 0.3 to 2 a\*b\* units gave 45% → 6% false colour while backdrop detection went 18% → 1%.
- **Woodii's axis applied to phone JPEGs flags 41–48% of unpainted prints.**
- **RX is the wrong tool.** Global RX flags the structured background; local RX self-suppresses anything larger than its guard window, even lips.
- **In the proposal, the edge term cuts false colour by a factor of 3–7.**
- **A spread-normalised presence rule loses the backdrop even with anchors (0–15%), while the Boost shows it plainly (Figure 1).** The yardstick must not be fitted to the paint.
- **Glare remains: 24–48% of glare pixels show as paint.** Hence the second capture.
- **The "two colours at one tone" check is a hint, not a guarantee.** It fired on P3 at L\* 62–77 and not on any unpainted print, but it missed the P2 backdrop.

### Honest limits of this evidence

- One portrait and my own simulator, which shares my model's assumptions: multiplicative washes, smooth light, a monotone tone curve. It tests the logic and the code, not the method.
- I tuned the proposal on these same scenes. They exposed four bugs in it: a collapsing covariance, a NaN noise model, a degenerate margin design, and scale collapse. Treat its numbers as optimistic.
- CIELAB and log-chromaticity were not distinguishable here once the light field was modelled. My preference for log-chromaticity rests on physics, not on this bench.

### Figures

All in `/home/user/xpw/9e3d5c/work/fig/`:
- `fig_P2_backdrop.jpg` (Figure 1): the painted backdrop, automatic versus margin plus box.
- `fig_P3_full.jpg` (Figure 2): the fully painted print, where the reference absorbs the suit's orange.
- `fig_N3_unpainted.jpg` (Figure 3): the TODO plan versus the proposal on the unpainted print.
- `fig_fixed_presence.jpg`: the fixed-departure presence rule on three scenes.

---

## 6. TODO.md, item by item

**To decide first**
- **How the reference is given.** Keep the boxes, the picks file, the folder default and the labelled automatic fallback. Add two box kinds with different roles: "paper or mount" for the light, "unpainted" for the tone. Report which tones no box covers.
- **What the boost does with the substrate.** Keep "neutral grey". Include the light field in what is neutralised, so a cast does not show as paint.
- **Drop raw C\*ab and LRC.** Agree. The single new feature should be the log-chromaticity departure from the fitted reference.
- **Layout.** A small package with tests.

**Pipeline**
1. Load: agree.
2. Working size: agree.
3. Feature space: change CIELAB to log-chromaticity (a weak preference, see §5). Keep the 5-px median; make any wider smoothing luminance-guided.
4. Exclusions: agree. Add "brighter than the margin's paper". Partial glare cannot be excluded from one capture.
5. Reference: replace band medians with f + g fitted jointly as an MM-estimator. Band medians break down when paint holds one tone band.
6. The x–y light term: required from the start, not later. Every uncontrolled capture has uneven light.
7. Feature: keep the vector, since its direction gives hue and it still finds blue over warm. Change its yardstick to a fixed departure with a 3-σ floor.
8. Specks: keep the median filter, and add the edge term.

**Pictures**
- Add the Reference panel and its tone strip.
- Start opacity at T, not at 2 spreads.
- Presets T0 = 0.06 / 0.04 / 0.025.
- Footer words as in §3, item 9.

**Housekeeping**
- Agree with all items.
- Test scenes should include: a split tone, mixed light, glare, a one-tone backdrop and a fully painted print.
- Tests should assert that failures are visible (an object's colour in the reference, a lit margin), not just detection rates.
- Real VDZ captures come before anything else.

---

## 7. What this standpoint is likely to get wrong

1. **It treats the camera as a radiometer.** Phones segment scenes semantically. Apple documents on-device panoptic segmentation of sky, person, hair, skin, teeth and glasses, used by Smart HDR 4 to render skin tones per subject, and stored as masks in ProRAW. A face in a photographed print may be rendered differently from its surroundings: a local "cast" with sharp edges, exactly where colourists painted. My light model is smooth by construction, and the reference panel would not show it. The remedy is on the capture side: RAW, ProRAW, or an app without scene processing.
2. **It reaches for anomaly detection when the target is not rare.** RX, CFAR thresholds, IR-MAD and LTS all assume rarity and fail quietly when it does not hold (P3). "One colour per tone" plus anchors is the stronger prior.
3. **It wants numbers**: false-alarm rates and ROC curves. They belong in validation, never on a picture.
4. **It sees only colour.** Neutral media are invisible to any chroma method: graphite and pencil retouching, black spotting dye, grey or white gouache, varnish, gum. A blank map means "no colour departs here", not "no paint". The footer must say so.
5. **Prints are not Lambertian ground.** Gloss and texture produce glare. Silver mirroring, a bluish metallic sheen on deteriorated silver, appears at specular angles, often in dense areas, as false "blue paint in the shadows", and no tone curve explains it.
6. **It underrates the conservator's eye.** Magnification and raking light are the better second sensor. The tool's job is to say where to look.
7. **Simulations prove less than they appear to.** See §5's limits.

---

## 8. How to falsify this answer

Run this before anything else is added.

**Material.**
- Six known-unpainted gelatin silver prints: neutral, warm-tone, selenium split-toned, yellowed, one with silver mirroring, one glossy.
- Six hand-coloured prints mapped by a conservator under magnification before any tool is run:
  - small touches only;
  - one large wash at one tone (a backdrop);
  - fully coloured;
  - including the print Chroma mode failed on in October, if it can be identified.

**Captures.** Three phone captures of each print, in the default app with HDR on:
- window light from the left;
- overhead room light;
- mixed light with the print turned 180°.

Repeat the window-light capture in RAW or ProRAW.

**Runs.** Automatic; then with the margin; then with one unpainted box chosen before the outputs are seen.

**Scoring**, by someone other than the developer, marking areas on printed outputs. The answer is wrong if any of these holds:

| Test | The answer is wrong if… |
|---|---|
| F1: false colour | More than 1 of the 18 automatic captures of unpainted prints shows a coherent coloured area larger than about 1 cm on the print, outside hatching and not glare. |
| F2: misses | More than 2 of the 18 margin-plus-box captures of painted prints miss a documented area of 3 mm or more in both Boost and Presence. |
| F3: knowing it went wrong | Any large failure (a tenth of the image or more) was invisible in the reference panel, the margin outline, the footer words and the second capture alike. This is the central claim of §4. |
| F4: light versus paint | Across the three captures of a print, the presence maps disagree on painted areas more than they agree. |
| F5: the phone itself | Faces on unpainted prints show colour in default-app captures but not in RAW. Then single-capture use must require RAW, which reverses part of the verdict. |
| F6: the complexity is earned | v4.1.2 or a plain TODO-plan build does at least as well on F1–F3. Then the MM fit and the light field are not worth their cost. |

---

## 9. Sources

**Detection and remote sensing**
- Reed & Yu 1990, IEEE Trans. ASSP 38(10):1760–1770 (RX).
- Manolakis, Marden & Shaw 2003, Lincoln Laboratory Journal 14(1):79–116.
- Kruse et al. 1993, Remote Sensing of Environment 44:145–163 (spectral angle mapper).
- Schott, Salvaggio & Volchok 1988, Remote Sensing of Environment 26(1):1–16 (pseudo-invariant features).
- Canty, Nielsen & Schmidt 2004, Remote Sensing of Environment 91:441–451; Canty & Nielsen 2008, Remote Sensing of Environment 112:1025–1036 (IR-MAD).
- Smith & Milton 1999, International Journal of Remote Sensing 20(13):2653–2662 (empirical line method).
- Richardson & Wiegand 1977, Photogrammetric Engineering & Remote Sensing 43(12) (Perpendicular Vegetation Index).
- Kauth & Thomas 1976, LARS Symposium (tasselled cap).
- Holben & Justice 1981, International Journal of Remote Sensing 2(2) (band ratios).
- Gillespie, Kahle & Walker 1986, Remote Sensing of Environment 20:209–235 (decorrelation stretch).
- Green et al. 1988, IEEE Trans. Geoscience and Remote Sensing 26(1):65–74 (MNF).
- Townshend, Justice, Gurney & McManus 1992, IEEE Trans. Geoscience and Remote Sensing 30(5):1054–1060 (misregistration).
- Hedley, Harborne & Mumby 2005, International Journal of Remote Sensing 26(10) (sun glint).

**Colour and vision**
- Finlayson, Hordley, Lu & Drew 2006, IEEE TPAMI 28(1) (log-chromaticity).
- Land & McCann 1971, JOSA 61(1) (Retinex).
- He, Sun & Tang 2013, IEEE TPAMI 35(6) (guided filter).

**Robust statistics**
- Rousseeuw 1984, JASA 79 (least median of squares; least trimmed squares).
- Rousseeuw & Van Driessen 2006, Data Mining and Knowledge Discovery 12 (FAST-LTS).
- Yohai 1987, Annals of Statistics 15(2) (MM-estimators).

**Cultural heritage precedent**
- DStretch, Harman's decorrelation-stretch plug-in: Le Quellec, Harman, Defrasne & Duquesnoy 2013, Les Cahiers de l'AARS 16:177–198.
- L-DCS, a localised decorrelation stretch for rock art (Griffith University repository).

**Photographic materials**
- Silver mirroring as a bluish metallic sheen: AIC conservation wiki, "PMG Silver Mirroring".
- Selenium toning acting on shadows first: photographic print toning literature.
- The Met's James Van Der Zee Archive (press release, 7 December 2021).

**Phone processing**
- Apple Machine Learning Research, "panoptic segmentation" (Smart HDR 4).
- Apple WWDC 2021, session 10160 (ProRAW semantic masks).

---

## Files

All in `/home/user/xpw/9e3d5c/work/`:
- `sim.py` — synthetic capture simulator (print, light, glare, lateral colour, phone tone curve, JPEG).
- `methods.py` — every background model, M1–M7; the proposal is the `Background` class and `m7_fixed`.
- `bench.py` — scoring. Results are in `bench_full.json` (earlier methods) and `bench_m7final.json` (proposal, current code). The proposal rows in `bench_full.json` predate the fixes and should be ignored.
- `audit.py` — the "two colours at one tone" check.
- `figs.py` — the report figures, written to `fig/`.
- `caps/` — the six synthetic captures.
