<!-- Saved verbatim by the coordinator from the agent's hand-back (the harness refused the agent's own write to
/home/user/xpw/45b29c/report.md). The harness's two-space indent is removed; nothing else is changed. -->

**Note:** `/home/user/xpw/45b29c/report.md` was not written. The harness refused it ("subagents should return findings as text, not write report files"), so the full report is below, ready to save to that path. Code, results and figures are under `/home/user/xpw/45b29c/work/`. Both repositories were only read (git log and git show; v4.1.2's functions were imported read-only to run them).

# The handpaint visualiser: what to build, from the standpoint of visual perception

*A review of the visualiser's iterations (v1.1 to 4.1.2), its rebuild plan (TODO.md) and Woodii's removed Chroma mode, by a vision scientist who designs visualisations. No real VDZ capture was available. Every number below comes from synthetic captures built for this review (`work/synth.py`), so nothing here has yet been shown on a real capture.*

## 1. Verdict

The tool serves a detection task for a human observer: *is there colour here that the unpainted photograph would not have?* Each earlier version got one of three things wrong. The rebuild should get all three right.

1. **What "unpainted" looks like.**
   - Earlier choices:
     - v1 to v4 used *neutral* (raw C\*ab), or *the image's typical chroma magnitude at each lightness* (LRC).
     - Woodii used *one straight silver axis through the paper*.
     - TODO.md uses *the median colour at each lightness*, with no term for the light.
   - For uncontrolled captures, the unpainted photograph is **a colour that varies with tone and drifts across the frame with the light**.
   - The tool should fit that per capture, robustly, with no user input. Optional boxes on known-unpainted areas serve as anchors.
2. **What counts as standing out.** Judge a departure against *the substrate's own measured spread* at that tone, at several spatial scales, with a floor of about half an 8-bit code value. Do not use a global chroma histogram (v1 to v4) or sensor noise (Woodii).
3. **How it is shown.**
   - **Boosted** (chroma boost around neutral): the substrate is drawn grey and departures are drawn in their own hue.
   - **Presence**: departures are drawn bright on a dimmed print, so they pop out *by lightness* for every observer, including the roughly 1 man in 12 with a red-green deficiency.
   - **As if unpainted**: the fitted reference, made visible and blinked against Boosted. If the reference is wrong, the wrong things flash.
   - **A key**: shows how a standard faint wash would look in *this* capture at each tone.
   - **A footer in words.** There are no numbers, tiers, areas or outlines anywhere.

**Results.** On the synthetic captures, false presence on an *unpainted* print under mixed light is **0.4 % of the area**. Lips, red stripes, a green patch and gold touches 3 to 12 px across are found 95 to 100 % of the time.

**Where it fails.** It fails where it must: when paint covers most of a range of tone. It fails *visibly*, and three user boxes repair it (false presence falls from 14.6 % to 0.7 %).

**What would reverse this verdict:**
- **Phone processing.** Real negative controls might show *content-aligned* false colour from phone processing (warmer faces, bluer skies) in most captures. A reference built from tone and position cannot model that. The remedy would then be capture discipline (fixed white balance or raw, or a grey card in the frame), not a better algorithm.
- **Observers.** Observers might fail to see a broken reference in the blink (§7).

## 2. The iterations, read as detection experiments

Each version chooses an evidence variable, a reference ("no paint"), and a criterion plus a display.

| Version | Evidence | Reference | Criterion and display | Right / wrong |
|---|---|---|---|---|
| v1.1 and v1.2 (Tk GUI) | C\*ab from OpenCV 8-bit Lab | neutral | <ul><li>Histogram peak of 3×-boosted chroma, then walk out to 1 % of the peak.</li><li>Three tiers, at the median and 85th percentile of above-threshold chroma.</li><li>Boosted colour over the print at 15 % grey.</li></ul> | <ul><li>Right: bright colour on a dark context gives luminance pop-out.</li><li>Wrong: a toned print is not neutral.</li><li>Wrong: tiers are relative to each image's own paint, so "solid" means different things in different images.</li></ul> |
| v3.0 | float Lab C\*ab | neutral | <ul><li>Same threshold.</li><li>Adds float TIFFs, area percentages and Jaccard stability.</li></ul> | Turned a picture into a measurement; the author has since asked for that to go (4.1.2). |
| v4.0 and v4.1 | <ul><li>C\*ab.</li><li>LRC = (C − band median) / band IQR.</li></ul> | neutral, or the typical chroma *magnitude* per L\* band | <ul><li>Threshold modes: noise_floor, percentile, otsu or fixed.</li><li>100 px component filter.</li></ul> | <ul><li>Right: the reference depends on lightness.</li><li>Wrong: a magnitude cannot see paint that lowers or shifts chroma.</li><li>Wrong: the 100 px filter deletes small touches.</li><li>Woodii's decision log (decisions-0.4.md) records v4.1's colour bugs: neutral white read C\* 10 to 14.</li></ul> |
| TODO.md | the (a\*, b\*) *vector* from the reference | <ul><li>median (a\*, b\*) per L\* band</li><li>position terms "optional, later"</li></ul> | <ul><li>Opacity rises from 2 to 5 spreads.</li><li>Hue from the vector's angle, over the grey print.</li></ul> | <ul><li>Right: the vector, the per-band spread, the soft ramp, words in the footer.</li><li>Wrong for unruly captures: the light reads as paint.</li><li>Wrong: no edge handling.</li><li>Wrong: the colour overlay sits at the print's own lightness, which is close to invisible to dichromats for red and pink (§3.4).</li></ul> |
| Woodii Chroma mode (removed after its first real run) | optical density off the silver axis, as a Mahalanobis distance | one straight axis through the paper, from a required "untinted" pick | <ul><li>k = 4 multiples of *sensor* noise.</li><li>Default view: an off-axis map on black.</li><li>Up to about 16 views.</li></ul> | <ul><li>Right: the physics (a dye is a constant OD offset), the vector, boxes as picks, a flip view.</li><li>Wrong: see below.</li></ul> |

**Why chroma magnitude fails on a toned print** (measured on the synthetic warm print):
- Unpainted paper and silver read C\*ab 7 to 10.
- The faint blue backdrop wash reads 6.5 to 9.5, the same as paper.
- The blue flag canton reads **3.5 to 4.9, less chromatic than unpainted paper**, because blue cancels the warmth.
- v4.1.2's threshold sits at 13 to 16, so only the lips and the gold clear it.
- LRC gives the wash and the canton *negative* values (−0.8 to −1.4). No LRC threshold can ever show them, which is why LRC scores below chance (AUC 0.35).

**What most likely sank Woodii's Chroma mode.** Its removal note leaves the cause open. Three choices in the code at 5b1757d predict a map that lights up on real prints:
- **A straight axis.** `silver_axis` fits one line through OD zero. Woodii's own decision log says that, in a toy model, density-dependent tone gave untinted areas a false signal "about 5× a light wash". That limitation was "set aside".
- **The wrong null distribution.** `_robust_cov` measures noise around each density bin's *own mean*, but `zscore` measures distance *from the axis*. Any bin whose mean sits off the axis is therefore flagged wholesale. In detection-theory terms, the criterion sat on sensor noise, while what decides false alarms on a real print is the substrate's own variability.
- **A picture without the photograph.** The default view, `ch:tint`, was a scalar map auto-levelled to its 99.5th percentile and shown on black, one of up to about 16 views. Nothing related a flagged region to the image content, yet that is the cue that separates paint (it follows a face) from artefact (it follows tone or light).

It also demanded an "untinted, mid-tone to shadow" pick before running, which is circular for a tool meant to find where the paint is.

## 3. The design: components and how they connect

```
capture → 1 load → 2 working size → 3 CIELAB, a*b* 5×5 median → 4 leave out (hatched)
            optional <name>.boxes.json → 5 reference fit ← all usable pixels
                     c(L*) + cast(x, y, L*), robust; cast terms only if a cast is found
          → 6 edge-tolerant departure (2-D vector)
          → 7 spread per tone band × 3 scales (floored, monotone)
          → 8 presence (fine scale + gated coarse scales)
          → 9 Original | Boosted | Presence + key strip + footer words;
              As if unpainted + blink (APNG); optional static HTML contact sheet (F flips)
          → 10 JSON record (settings and words, no statistics)
```

### 3.1 Steps 1 to 4

As in TODO.md:
- ICC profiles go to sRGB through LittleCMS; untagged files are taken as sRGB; EXIF orientation is applied.
- Area-average down to 2000 to 3000 px on the long edge.
- Convert to CIELAB and apply a 5×5 median to a\* and b\* only.

Two changes:
- **(a) Leave out *near white*, not just clipped.** A pixel goes if its maximum channel, averaged locally (σ 2 px), is at or above 244. In mostly clipped areas, the pixels that escape the clip are the ones whose noise read low in that channel. That biases their colour, so paper reads as tinted.
- **(b) Hatch what is left out.** Also leave out L\* < 5 and anything outside an optional object box. All left-out pixels are drawn hatched, never as "no paint".

### 3.2 Step 5: the reference, per capture, automatic

**The model:**

ref = c(L\*) + g·[s₁x + s₂y + (s₃x + s₄y)(L\* − 60)/40], with g = (L\*+16)/116.

- **c, the print's own tone colour.** A piecewise-linear curve with knots every 4 L\* and a second-difference penalty (a P-spline; Eilers and Marx 1996). It follows warm highlights and neutral or purple shadows.
- **The cast terms model the light, which is multiplicative.** A cast is multiplicative in linear light, so in CIELAB it grows with lightness.
  - A plain additive plane in a\*b\* gives AUC 0.75 and 7.0 % false presence under mixed light (14.2 % on the unpainted control).
  - The scaled plane gives 0.95 and 1.3 % (1.0 % on the control).
  - Plane plus lightness-dependent tilt gives 0.95 and 0.9 % (0.4 % on the control).
  - The tilt also absorbs brightness falloff, under which a dim corner of paper would otherwise be compared with a darker tone.
- **Cast terms only when needed.** They are kept only if the fit finds a cast (largest coefficient at least 4 a\*b\*). Under even light they only bend toward large painted areas; dropping them raised the share of the faint wash found from 60 % to 82 %.

**Fitting:**
- Iteratively reweighted least squares with Tukey's biweight (Beaton and Tukey 1974), cut at 3.5 band spreads of the 2-D residual.
- Ten rounds, starting from the band medians, on up to 250 000 sampled pixels.
- Lightness is indexed after smoothing to the chroma's resolution (σ 1.5 px).

**Boxes:**
- Optional; saved beside the image as `<name>.boxes.json`.
- Weighted 20× and never down-weighted.
- **No folder-wide default.** Unruly captures are framed differently, so one capture's box lands on different content in the next.

The fit holds while paint is a minority within each stretch of tone, which is the breakdown property of robust regression (Rousseeuw 1984).

### 3.3 Steps 6 to 8

**Edge-tolerant departure.**
- At each pixel, take the smallest residual over the lightness values found in its 5×5 neighbourhood.
- Chroma that lags lightness at a sharp edge is then not taken for paint, whether the lag comes from 4:2:0 subsampling, camera chroma noise reduction or sharpening.
- A departure *across* the reference's own direction still counts.
- Without it, false presence doubles to triples, and AUC on the toned print falls from 0.95 to 0.88.

**Spreads.**
- Measured per tone band (4 L\* wide) and per scale: the departure is smoothed at σ = 2, 6 and 18 px (a ×3 ladder up to about 1.5 % of the long edge; add 54 px at 3000 px).
- The spread at each scale is the robust spread of pixels the fit kept as substrate.
- **Floor 0.4 a\*b\*.** One 8-bit code step is 0.4 to 0.85 a\*b\* at every lightness. Camera chroma noise reduction can push the measured spread below what the reference resolves. In an intermediate run with the same pipeline otherwise, false presence on the even-light capture was 12 % without the floor and 0.8 % with it.
- **Finer scales are never narrower than coarser ones.** Smoothing cannot widen a null field, so this carries the model's misfit down to every scale.

**Presence.**
- **Fine scale:** after a 5×5 median, presence ramps smoothly from 3 to 5.5 spreads.
- **Coarse scales:** each counts only where the pixel's *own* fine departure points the same way, by at least about one fine spread, and carries at least a third of the pooled departure. Pooling finds faint broad washes (60 % vs 37 % with one scale, under even light). The gate stops rings of false colour round strong patches and stops hues mixing across a boundary. Ungated, false presence is 2.2 to 2.9 %, against 0.1 to 0.9 % gated.
- **Combination:** presence is the maximum over scales.
- **Hue:** taken from the finest scale that stands out by itself.

### 3.4 Step 9: the pictures

**Montage: Original | Boosted | Presence**, in one row at one scale. This is juxtaposition plus two explicit encodings of the difference, in Gleicher et al.'s (2011) terms.

**Boosted** (chroma boost around neutral):
- Lightness is the print's own, with shadows lifted slightly (Oklab L = 0.15 + 0.83 L). At L 0.25, sRGB allows only about 0.05 of chroma for yellow or cyan, so without the lift gold on a dark ground cannot show.
- The substrate is grey.
- The departure is drawn in its own hue, at chroma = 0.9 × gamut max × tanh(max(m − 1.5, 0)/3.5).
- Why grey: any colour on a uniform achromatic field is a feature singleton. Search for it is efficient (Treisman and Gelade 1980), because similarity to the distractors is low and the distractors are homogeneous (Duncan and Humphreys 1989).
- This is the low-criterion evidence view. The observer pools over area here: the faint wash that Presence shows only in patches appears as a coherent tint.
- Use Oklch (Ottosson 2020) for the boost and for gamut mapping, at constant lightness and hue. At a constant CIELAB hue angle, a blue drifts about 10° in Oklab hue between C\* 5 and 40, consistent with CIELAB's known bent blue hue lines (Hung and Berns 1995). This is a small refinement.

**Presence:**
- The context is the print in dim grey (Oklab L 0.20 to 0.52).
- Departures are drawn at L 0.80, chroma min(0.9 × gamut, 0.16), in the departure's hue, with opacity equal to presence. Left-out pixels are hatched.
- **Why the lightness step: colour-vision deficiency.** Simulated with Machado, Oliveira and Fernandes (2009):
  - A pink departure drawn at the print's own lightness (an isoluminant overlay, which is what TODO.md's map and a plain chroma boost amount to) falls from ΔE 26 for normal vision to **ΔE 4 for protanopes and 8 for deuteranopes**.
  - Drawn bright on dim, it stays at ΔE 46 to 53.
  - Red and pink are the colourist's commonest portrait hues, and about 8 % of men of Northern European descent are red-green deficient (Birch 2012).
  - In `figs/cvd_face.png`, TODO.md's overlay loses the lips for a simulated deuteranope; Presence keeps cheeks and lips.
- **Hue carries one meaning, "which colour"**, checkable against the object. There is no rainbow colour map, which would add false boundaries and uneven salience (Borland and Taylor 2007; Kovesi 2015), and no tiers or colour bar.

**Key strip** (under the montage):
- Built from this capture's own reference and spreads.
- Two rows: "a faint wash, broad" and "a faint wash, a small touch", using a fixed pink dye.
- Seven tones from paper to shadow, each drawn as Presence would draw it.
- Where the key shows nothing, a quiet Presence means "could not tell", not "no paint". In effect it gives the observer's sensitivity before they read a "no".
- In `figs/key_compare.png`, the scan shows the wash at every tone; on the mixed-light phone capture a small faint touch shows only in light and mid tones.

**Footer**, in words generated from the fit:
- "Visualisation only - not a measurement."
- "Reference: automatic, from the picture" (or "from your boxes").
- "A colour cast across the frame was allowed for."
- "Hatched: too bright or too dark to judge."
- "Much of the light tones departs from the reference: if 'As if unpainted' shows colour there, box an area you know is unpainted."

**As if unpainted and the blink:**
- *As if unpainted* is the print's lightness with the reference's colour. It is literally the tool's idea of the unpainted photograph.
- *The blink* is an APNG that alternates, 700 ms each with no blank between, As if unpainted and the same image with Boosted's departures added. Unpainted areas do not change, so only paint flashes.
- A direct transition lets motion transients carry the difference. A blank between frames would cause change blindness (Rensink, O'Regan and Clark 1997).
- This is Tombaugh's 1930 blink comparator, applied to a hypothesis instead of a second plate.
- 1 to 2 Hz is well inside chromatic temporal sensitivity (Kelly 1983).
- Woodii already uses "F to flip", so the optional HTML contact sheet can reuse it.

### 3.5 Records, and what is dropped

**The JSON record keeps:**
- source and hash;
- the preset: low / normal / high, meaning a spread floor of 0.5 / 0.4 / 0.3 a\*b\*;
- whether boxes and cast terms were used;
- the footer words.

**Dropped:**
- raw C\*ab and LRC;
- the four threshold modes;
- tiers;
- the 100 px component filter;
- CLAHE;
- the analytic Adobe RGB and ProPhoto paths;
- histograms;
- threshold numbers in the run log.

### 3.6 TODO.md's "to decide first", answered

1. **Reference:** automatic by default, with optional per-image boxes and no folder-wide picks.
2. **Boost:** neutralise the substrate. "Keep the tone" survives only as the blink's second frame.
3. **Raw C\*ab and LRC:** drop both (§2, §5).
4. **Layout:** a small package (`load`, `reference`, `departure`, `pictures`, `cli`) plus synthetic tests. `work/synth.py` and `work/evaluate.py` are a start.

## 4. For each uncontrolled capture, how should the tool establish what the unpainted photograph looks like, and how would someone looking at its output know when that has gone wrong?

**Establishing it.** No "before" photograph exists. What does exist is a model of any unpainted monochrome print seen through any camera and light, fitted to the capture in hand:

1. **The premise.** In an unpainted print, colour is a function of tone (paper, then silver from light to dense, possibly toned), seen through light that varies smoothly across the frame. So unpainted = c(L\*) + g·cast(x, y, L\*). Paint is whatever this cannot explain.
2. **Fit it to the capture itself**, robustly, on every usable pixel, with no input from the user (§3.2).
   - Paint is the outlying population, and the fit holds while paint is a minority within each stretch of tone.
   - Cast terms are included only if a cast is found.
   - Boxes on known-unpainted areas (paper border, white collar, teeth, the whites of the eyes) are corrections, not prerequisites.
   - In the synthetic tests, the fitted reference sits within about 0.6 to 1.7 fine-scale spreads of what the *same print captured unpainted* gives, and 0.8 to 0.9 under the faint wash, so the wash is not absorbed.
3. **Judge departures against what unpainted pixels of this capture actually do:** the substrate's spread at that tone and scale, floored at half a code value.
4. **Discount what the capture cannot resolve:** edges, near-white areas, near-black areas, and tones the fit barely saw. All are hatched.

**Knowing when it has gone wrong.** The tool cannot know from its own statistics. When paint is the majority in a range of tone, the fit adopts the paint as "substrate" and the real unpainted pixels become the outliers. The inlier share in the light tones was 0.54 for the majority-painted print, against 0.66 to 0.79 for the other captures. Other tones of normal captures reach 0.54 too, so the share cannot tell them apart. What the tool can do is make every failure produce a picture that a person who knows the objects will read as wrong:

| Failure | What the viewer sees | Figure |
|---|---|---|
| Paint taken into the reference (paint dominates a range of tone) | <ul><li>Unpainted things of that tone glow in the **complementary** hue: hair, face and a halo round the head turn orange when a blue backdrop is swallowed.</li><li>The colour **follows a band of tone across unrelated objects**.</li><li>Paint visible in the Original is missing from Presence.</li><li>In the blink, the halo flashes.</li><li>The footer cautions about that range of tone.</li></ul> | `final_majority_auto.png`, `blinkpair_majority_auto.png` |
| Light the model cannot follow | Broad washes that **cross object boundaries**, line up with the light, and take **opposite hues on opposite sides** | `versions_phone_mixed.png` (the TODO.md panel) |
| Glare or sheen | A soft **cool** wash exactly where the Original shows a sheen. Here it lit the unpainted shuttle blue, right beside the real blue wash, so only the sheen tells them apart. | `final_phone_glare.png` |
| Tones the reference never saw | Hatched as "cannot judge", never drawn as "no paint" | all montages |
| A capture too poor for faint paint at some tones | The key's faint wash does not show at those tones | `key_compare.png` |

**The viewer's check, in seconds per capture:**
1. Known-unpainted places (paper border, collar, teeth, eye whites) must be quiet in Presence.
2. Colour must follow objects, not tone or light. Paint stops at a lip line; reference error runs along a tonal band or a light gradient. Grouping by common region and good continuation is effortless for the viewer, and no statistic offers it.
3. In the blink, only paint flashes. If something flashes that cannot be paint, or visible paint does not flash, box an unpainted area at that tone and rerun. On the majority print, three boxes cut false presence from 14.6 % to 0.7 % (AUC 0.66 to 0.85; `final_majority_boxes.png`).
4. Read the key before reading an absence.

**The one failure with no signature.** Colour that the *camera* put on objects (semantic skin or sky rendering) aligns with objects exactly as paint does. Only negative controls reveal it (§7).

## 5. Evidence from synthetic captures

**The print:**
- A gelatin-silver-like print of a greyscale portrait, on yellowed paper with a margin.
- Silver warm in the highlights and neutral in the shadows; a "toned" variant goes purple in the shadows.
- Paper texture and foxing.
- Seven transparent colourants, laid by Beer-Lambert with a double pass:
  - faint pink cheeks;
  - red lips;
  - a faint blue backdrop wash;
  - a blue canton;
  - red over dark stripes;
  - a green patch;
  - gold touches 3 to 12 px across.

**The captures:**
- A lossless scan.
- Phone captures with shot and read noise, grey-world auto white balance, chroma noise reduction, an S-curve, sharpening and JPEG at quality 80 with 4:2:0, in five versions:
  - even warm light;
  - mixed light (tungsten on one side, daylight on the other, with 25 % falloff);
  - glare;
  - a purple-toned print;
  - a mostly painted backdrop.
- An **unpainted** control in mixed light.

**What was measured:**
- **AUC:** of each pipeline's evidence map against the truth.
- **False presence:** the share of unpainted, usable area drawn at opacity 0.2 or more.
- **Hits:** the share of each painted area drawn.
- **Pooled d′:** a region-pooled d′.

**How each pipeline was run:**
- v4.1.2 runs its own functions, imported read-only.
- "TODO.md" is the plan as written, with one estimator fixed for fairness: each band's spread is taken over all its pixels and floored like mine. Taken literally, its spread shrinks round by round, giving 20 to 30 % false presence on every phone capture.

**AUC / false presence:**

| Capture | v4.1.2 C\*ab | v4.1.2 LRC | TODO.md | Proposed |
|---|---|---|---|---|
| Scan, even light | 0.44 / 0.0 % | 0.35 / 0.0 % | 1.00 / 0.4 % | 1.00 / 0.1 % |
| Phone, even warm light | 0.51 / 0.0 % | 0.35 / 0.2 % | 0.90 / 5.1 % | 0.96 / 0.9 % |
| Phone, mixed light | 0.57 / 0.0 % | 0.66 / 0.0 % | 0.52 / 15.6 % | 0.95 / 0.9 % |
| Phone, glare | 0.51 / 0.0 % | 0.36 / 0.0 % | 0.86 / 8.0 % | 0.91 / 6.9 % |
| Phone, purple-toned print | 0.54 / 0.0 % | 0.40 / 0.1 % | 0.88 / 4.1 % | 0.96 / 0.8 % |
| Phone, backdrop mostly painted | 0.50 / 0.0 % | 0.29 / 0.1 % | 0.57 / 15.0 % | 0.66 / 14.6 %; **0.85 / 0.7 % with three boxes** |
| Phone, mixed light, **unpainted** | – / 0.0 % | – / 0.0 % | – / 16.4 % | – / **0.4 %** |

**Share of each painted area shown** (even light / mixed light / toned):

| | cheeks | lips | faint wash | canton | stripes | patch | gold |
|---|---|---|---|---|---|---|---|
| v4.1.2 C\*ab (even light) | 0 | 99 | 0 | 0 | 5 | 7 | 89 |
| TODO.md | 81/9/55 | 100/100/100 | 46/1/26 | 39/2/34 | 85/40/41 | 94/22/84 | 100/82/100 |
| Proposed | 96/84/72 | 100/100/100 | 82/17/36 | 37/66/52 | 100/100/100 | 100/100/95 | 100/100/100 |

**Ablations** (AUC / false presence; every row except the first has the cast terms always on):

| Variant | scan | even | mixed | glare | toned | unpainted control |
|---|---|---|---|---|---|---|
| Final (cast terms only if a cast is found) | 1.00/0.1 | 0.96/0.9 | 0.95/0.9 | 0.91/6.9 | 0.96/0.8 | 0.4 |
| Cast terms always on | 1.00/0.1 | 0.95/0.8 | 0.95/0.9 | 0.90/6.6 | 0.95/1.0 | 0.4 |
| No cast terms | 1.00/0.1 | 0.96/0.9 | **0.64/26.8** | 0.91/6.9 | 0.96/0.8 | **25.3** |
| One scale | 1.00/0.0 | 0.95/0.5 | 0.93/0.5 | 0.90/5.9 | 0.93/0.7 | 0.4 |
| Ungated scales | 0.99/2.2 | 0.97/2.9 | 0.95/2.9 | 0.91/9.5 | 0.95/2.5 | 0.5 |
| No edge tolerance | 1.00/0.4 | 0.94/2.1 | 0.91/1.0 | 0.89/8.5 | 0.88/2.4 | 1.0 |
| Log-chromaticity instead of CIELAB | 1.00/0.2 | 0.95/2.8 | 0.91/2.1 | 0.90/8.3 | 0.91/8.3 | 2.2 |

**Reading the tables:**
- **v4.1.2 is quiet because it is blind.** Its AUC is 0.29 to 0.66.
- **TODO.md is sound on a clean scan but fails under uneven light.** On the unpainted print in mixed light it draws 16 % of the area, at near-chance AUC, because the light itself reads as paint (yellow on the warm side, blue on the cool side; `versions_phone_mixed.png`).
- **Each part of the proposed design earns its place:**
  - the cast model;
  - edge tolerance;
  - gating;
  - multi-scale pooling, which finds more faint wash for slightly more false presence.
- **CIELAB beats log-chromaticity here** at equal sensitivity, although log-chromaticity is the cleaner theory (Finlayson, Drew and Lu 2004).
- **What stays hard:**
  - **The faint wash under mixed light.** Only 17 % of it is drawn, although its pooled d′ is about 50. At large scales, an uncontrolled capture is limited by the reference's misfit to the light, not by noise. That is why the uncored Boosted panel is kept: there the wash reads as a coherent tint.
  - **Glare**, at 6.9 % false presence.
  - **The majority-painted print.**
- **Limits of these tests.** They share the design's assumptions (smooth multiplicative casts, colour as a function of tone), so they check the code more than the method, as Woodii's own note said of its models. Phone local tone mapping, semantic rendering and HDR merging were not simulated.

## 6. What this standpoint is likely to get wrong

1. **Polishing the display when the problem is upstream.** Oklab against CIELAB, or the shape of a ramp, moves results by a few percent. The reference's misfit to real light and phone processing moves them by tens of percent. Most effort belongs in the reference and in real negative controls.
2. **Treating colour as paint.**
   - *Paint that does not show:* neutral retouching, pencil, opaque white highlights, varnish.
   - *Colour that is not paint but does show:* silver mirroring (a bluish sheen in dense areas of old gelatin silver prints), uneven toning, foxing, stains, phone processing.
   - Vivid maps lend authority the evidence may lack.
3. **Treating the expert as the lab observer.**
   - Conservators may extract more from the uncored Boosted panel at full zoom than Presence's criterion allows.
   - Expectation shifts their criterion: a known colourist's studio raises the prior of paint.
   - Rare targets are missed far more often (Wolfe, Horowitz and Kenner 2005). In a mostly unpainted batch, faint paint will be missed whatever the display does.
4. **Overvaluing pop-out and blink.**
   - Real prints are cluttered. Stains, hatching and specks are heterogeneous distractors that slow search (Duncan and Humphreys 1989).
   - The blink helps only if users open it. The author's own rule applies: if it is not easy, nobody will do it.
5. **Assuming lab viewing conditions.** On an uncalibrated laptop in a bright room, the dim context crushes, faint hues vanish, and the key's predictions drift.
6. **Trusting stimuli the designer built.** Every number in §5 comes from a camera simulated by the pipeline's designer. The failure that matters most, content-aligned colour from phones, cannot be simulated honestly without the phones.

## 7. How to falsify this answer

Run this before adding anything (TODO.md's last item, made concrete).

**Part A: negative controls and paired captures** (no observers needed).

*Materials and captures:*
- 10 unpainted gelatin silver prints of the period: toned, yellowed, stained, silvered.
- 6 mock-ups photographed before and after a conservator tints them.
- Each print photographed by 3 people on their own phones, under 3 lights (window, room, mixed), handheld. The mock-ups are shot from a tripod, so before and after register.
- The truth is the after-minus-before difference.

*Falsified if:*
1. On the unpainted prints, Presence shows a coherent region (bigger than a fingertip at print scale) on more than 1 capture in 10, at the normal preset.
2. On the mock-ups, the reference fitted to the *after* capture differs from the *before* capture by more than 2 spreads over more than 5 % of the unpainted area.
3. False regions align with faces or skies repeatedly across phones. This would reverse §1's verdict toward capture discipline.

**Part B: observers** (8 to 12 conservators or curators, at least 2 of them colour-vision deficient).

*Procedure:*
- Show the Part A captures in four display conditions:
  - the original alone;
  - v4.1.2's montage;
  - TODO.md as specified;
  - the proposed montage, with the blink and the key.
- Per print, collect "painted?" yes or no with a confidence rating, plus marked regions.
- Analyse with rating-ROC d′ and the criterion c (Macmillan and Creelman 2005), and JAFROC for localisation (Chakraborty and Berbaum 2004).
- Seed some captures with an uncorrected majority-painted reference, and ask "does the reference look wrong?".

*Falsified if:*
1. The proposed display's d′ does not exceed both the original alone and TODO.md's (95 % confidence intervals).
2. Observers call more unpainted controls "painted" with the proposed display than with the original alone.
3. Broken references are spotted at no better than chance.
4. Colour-deficient observers' d′ with Presence falls more than 20 % below that of normal observers.
5. Hit rates by tone contradict the key.

## 8. Checklist replacing TODO.md's

- [ ] Steps 1 to 4 (§3.1).
- [ ] Reference fit (§3.2): P-spline in L\*; cast terms scaled by (L\*+16)/116, with the lightness tilt, kept only if a cast is found; IRLS with Tukey's biweight; optional `<name>.boxes.json`.
- [ ] Departure and presence (§3.3): edge-tolerant departure; spreads per tone band at {2, 6, 18 (54)} px, floor 0.4, monotone; gated presence.
- [ ] Pictures (§3.4): Original | Boosted | Presence; the key; the footer words; As if unpainted plus the APNG blink; optionally the HTML contact sheet.
- [ ] Presets low / normal / high, recorded in the JSON only.
- [ ] Remove everything in §3.5's "Dropped" list.
- [ ] Tests from `work/`:
  - the unpainted control is quiet;
  - mixed light is quiet;
  - the scan finds all seven colourants;
  - the majority print shows its signature and boxes fix it;
  - Presence is visible to colour-deficient observers.
- [ ] README advice (not checks; capture is the photographer's job): keep the paper border in frame and unclipped; avoid glare; use one light if you can. Later, if glare or mirroring proves common, a second shot from another angle helps: surface sheen moves with the viewpoint, paint does not.
- [ ] Part A of §7 on real captures before anything else.

## Sources

- Beaton, A. E. and Tukey, J. W. (1974). The fitting of power series, meaning polynomials, illustrated on band-spectroscopic data. *Technometrics* 16, 147-185.
- Birch, J. (2012). Worldwide prevalence of red-green color deficiency. *JOSA A* 29(3), 313-320.
- Borland, D. and Taylor, R. M. (2007). Rainbow color map (still) considered harmful. *IEEE CG&A* 27(2), 14-17.
- Chakraborty, D. P. and Berbaum, K. S. (2004). Observer studies involving detection and localization: modeling, analysis, and validation. *Medical Physics* 31(8), 2313-2330.
- Duncan, J. and Humphreys, G. W. (1989). Visual search and stimulus similarity. *Psychological Review* 96, 433-458.
- Eilers, P. H. C. and Marx, B. D. (1996). Flexible smoothing with B-splines and penalties. *Statistical Science* 11(2), 89-121.
- Finlayson, G. D., Drew, M. S. and Lu, C. (2004). Intrinsic images by entropy minimization. *ECCV*.
- Gleicher, M., Albers, D., Walker, R., Jusufi, I., Hansen, C. D. and Roberts, J. C. (2011). Visual comparison for information visualization. *Information Visualization* 10(4), 289-309.
- Healey, C. G. and Enns, J. T. (2012). Attention and visual memory in visualization and computer graphics. *IEEE TVCG* 18(7), 1170-1188.
- Hung, P.-C. and Berns, R. S. (1995). Determination of constant hue loci for a CRT gamut and their predictions using color appearance spaces. *Color Research & Application* 20(5), 285-295.
- Kelly, D. H. (1983). Spatiotemporal variation of chromatic and achromatic contrast thresholds. *JOSA* 73(6), 742-750.
- Kovesi, P. (2015). Good colour maps: how to design them. arXiv:1509.03700.
- Machado, G. M., Oliveira, M. M. and Fernandes, L. A. F. (2009). A physiologically-based model for simulation of color vision deficiency. *IEEE TVCG* 15(6), 1291-1298.
- Macmillan, N. A. and Creelman, C. D. (2005). *Detection Theory: A User's Guide*, 2nd ed.
- Mullen, K. T. (1985). The contrast sensitivity of human colour vision to red-green and blue-yellow chromatic gratings. *J. Physiol.* 359, 381-400.
- Ottosson, B. (2020). A perceptual color space for image processing (Oklab).
- Rensink, R. A., O'Regan, J. K. and Clark, J. J. (1997). To see or not to see: the need for attention to perceive changes in scenes. *Psychological Science* 8(5), 368-373.
- Rousseeuw, P. J. (1984). Least median of squares regression. *JASA* 79, 871-880.
- Treisman, A. M. and Gelade, G. (1980). A feature-integration theory of attention. *Cognitive Psychology* 12, 97-136.
- Wolfe, J. M., Horowitz, T. S. and Kenner, N. M. (2005). Rare items often missed in visual searches. *Nature* 435, 439-440.
- Repositories read:
  - handpaint_visualiser, all history to 4584a2f;
  - Woodii at 5b1757d (chroma.py, chromarun.py, the tests, views.py, app.js);
  - Woodii's de6f9b1 (the removal) and docs/decisions-0.4.md;
  - Woodii origin/main's docs/AUTHOR-POSITIONS.md.

## Files (all under `/home/user/xpw/45b29c/work/`)

- **Code:**
  - `synth.py`: prints and captures, plus paired unpainted captures.
  - `pipelines.py`: v4.1.2 via its own functions; TODO.md, both literal and fair; the proposed design.
  - `render.py`: the pictures, the key, the blink and the footer words.
  - `evaluate.py`, `reference_error.py`, `floor_sweep.py`, `picks_demo.py`, `cvd_gamut.py`, `final_figs.py`, `versions_figs.py`, `tables.py`.
- **Results:** `results_all.json`, `results_final.json`, `todo_fair.json`, `cast_model_test.json`, `floor_sweep.json`, `reference_error.json`, `picks_demo.json`, `cvd_gamut.json`.
- **Figures (`figs/`, final code):**
  - `final_*.png`: four-panel montages with footers; As if unpainted is included for review.
  - `versions_phone_mixed.png`.
  - `final_majority_auto.png` and `final_majority_boxes.png`.
  - `blinkpair_majority_*.png`, and the animated `blink_*.png`.
  - `key_*.png` and `key_compare.png`.
  - `cvd_face.png`.
  - `reference_strips.png`: a weak diagnostic, not recommended.
  - `figs/intermediate/` holds superseded versions.
