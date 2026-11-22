<!-- Saved verbatim by the coordinator from the agent's hand-back (the harness refused the agent's own write to
/home/user/xpw/6d8ad6/report.md). The harness's two-space indent is removed; nothing else is changed. -->

**I could not write `/home/user/xpw/6d8ad6/report.md`.** The harness refused the write ("Subagents should return findings as text, not write report files") and I did not work around it. The full report is below; save it to that path if you need the file.

Everything else is in `/home/user/xpw/6d8ad6/work/`: the code, the score files (`out/*.json`) and three figures:
- `out/fig1_todo_failures.jpg`
- `out/fig2_alternative.jpg`
- `out/fig3_negative_control.jpg`

I did not change either repository. One untracked file appeared in the visualiser repository during my session that is not mine: `/home/user/handpaint_visualiser/__pycache__/Chroma_diagnoser_v4.cpython-313.pyc`, created at 05:26:30 UTC. It was compiled from the repository script by some process that loaded it by path. My runs used a copy, `work/v412.py`. I left the file where it is.

---

# The handpaint visualiser request: why it is ill-posed, and what survives

**What I read.** Both repositories, read-only:
- `handpaint_visualiser` at 4584a2f (script 4.1.2, README, TODO.md) and its history back to v1.1.
- Woodii at 5b1757d (Chroma mode's code) and de6f9b1 (its removal note and commit message).
- Woodii's `origin/main:docs/AUTHOR-POSITIONS.md`.

**What I ran.** Synthetic experiments in `/home/user/xpw/6d8ad6/work/`, with no real captures. I ran four pipelines on the same synthetic prints:
- v4.0 as committed (the VDZ-era version);
- 4.1.2's own internals;
- a faithful prototype of TODO.md;
- a prototype of the design proposed in Part 2.

## Summary

1. **As posed, the request cannot be met in a way that excludes a misleading answer.**
   - It asks for "presence, or lack thereof", which is a detection decision.
   - It forbids anything quantitative, which is the only way that decision could be checked.
   - It names no objective, so "optimal" (message 3) means nothing.
   - It assumes unruly captures. In those, the one thing every proposed picture depends on cannot be observed: what the *unpainted* print looks like in that photograph.
2. **That counterfactual is the crux, and every way of getting it fails silently.**
   - User picks are circular, and a pick on a faint wash reverses the answer.
   - An automatic fit fails when paint covers most of the print.
   - A "neutral" prior is wrong for toned prints.
   - An in-frame reference is excluded by "unruly".
   - Each failure produces a *plausible* picture (Fig. 1).
3. **The project's history shows the pictures do not reveal their own errors.**
   - The VDZ-era v4.0/4.1.0 decoded every file as ProPhoto, with the white point applied twice. In my rerun, neutral greys read C\*ab 6.2–13.9.
   - It thresholded each image at its own 90th percentile.
   - It was used on the VDZ captures. The faults were found later by code review on synthetic images, not from the pictures.
   - Woodii's Chroma mode was built and tested only on synthetic prints. It was dropped as "a bust" after its first real run, and why was never recorded: "Open: what failed on the real prints (the method, the picks, or the maps)".
   - TODO.md transplants Chroma mode's design (picked reference, departure in noise units, hue from angle) from linear raw data to phone JPEGs.
4. **What survives is a *where-to-look* tool, not a presence/absence tool.** It does four things:
   - **(a)** shows its own model of the unpainted print as a picture;
   - **(b)** measures departure in units of how much the user's own marks disagree with each other, not pixel noise;
   - **(c)** says in words when its assumptions are visibly broken;
   - **(d)** with two *deliberately different* photographs, separates departures that belong to the object from those that belong to the capture.

   What it cannot do:
   - It never shows absence.
   - It cannot tell paint from stain, foxing or uneven toning.
   - It cannot confirm, from one unruly capture, a wash as faint as the capture's own colour casts.
   - It is blind to tone-matched retouching.
5. **Do first:**
   - Ask the author what failed in Chroma mode's real run.
   - Photograph one known-unpainted print, and one whose paint a conservator has marked, twice each, the way real captures will be made.
   - Judge the output against them by eye, before building anything.

**Key results.** These come from my synthetic set, and section 1.9 gives the caveats. "Shown" means overlay opacity ≥ 0.25 (alpha ≥ 0.2 for v4.x).

On a print with **no paint**, the share shown as paint:

| Pipeline | Clean capture | One unruly capture (A) |
|---|---:|---:|
| TODO.md pipeline, good picks | 15% | 15% |
| TODO.md, automatic reference | 79% | 20% |
| VDZ-era v4.0 | 0.1% | 5.2% |
| Alternative, one capture | 0.5% | 2.8% |
| Alternative, two deliberately different captures | | 0.1% |
| Alternative, two captures sharing the same lens fringing | | 3.1% |

For the TODO.md pipeline, the figures at half opacity or more are 7% (clean) and 10% (capture A). The 3.1% for the alternative is because shared artefacts survive the two-capture test.

A **faint wash** (ΔE\*ab ≈ 4.5 on the print) against unpainted print gives AUC 0.995 in a clean capture and 0.84–0.85 in unruly captures. Stronger paint stays separable (AUC 0.98–1.0).

---

# Part 1. The request is ill-posed

## 1.1 The central question: what does the unpainted print look like in this photograph?

Every picture the plan proposes is a departure from an estimate of the unpainted print's appearance in that capture:
- The boost "around neutral" amplifies distance from that estimate.
- The presence map's opacity is that distance divided by a "spread".
- The hue is the direction of that distance.

In an unruly capture, that appearance depends on things the file does not record:
- the illuminant's colour, and how it varies across the frame (window plus lamp);
- auto white balance, which is computed from the scene, so from the paint itself;
- a scene-adaptive, local tone curve;
- lens colour shading and lateral chromatic aberration (CA);
- chroma subsampling and chroma denoising.

There are four ways to estimate it, and each fails:

| Reference from | How it fails | Shown here |
|---|---|---|
| **User picks** (TODO.md) | Circular: it needs the judgement the tool is meant to support. A pick on a faint wash flips the answer: the wash vanishes and unpainted areas take the opposite hue. Narrow-lightness picks are extrapolated. | Fig. 1, row 2: the wash drops from 32% to 5% shown (half opacity), and the unpainted face turns yellow-green. Picks on the suit only light 49% of the unpainted print. |
| **Automatic fit** (TODO.md fallback) | Assumes paint is a minority. A wash over most of the sheet becomes the reference, and the unpainted face reads as paint. This is the v4.1 LRC self-suppression that Woodii's log rejected: "A windowed baseline absorbs large washes into itself". Iterative trimming also shrinks the spread each round. | Fig. 1, row 3: unpainted areas shown at 34% (clean) and 69% (capture A). On a print with no paint, the clean capture shows 79%. |
| **Prior** ("unpainted = neutral") | Toned prints change hue with density; the synthetic print runs from b\* 5 to 14. Camera AWB has already applied a grey-world-like prior (Buchsbaum 1980), and that prior reacts to the paint. | Gray-world capture A moved unpainted mid-tones from b\* 13.7 to 4.0. |
| **In-frame reference** | Excluded by "unruly". A paper margin, when present, gives the paper's colour, not the image tone at each density. | |

**Identifiability.** In one capture, a smooth wash and a smooth cast are the same kind of signal. Retinex separates the two only by assuming illumination is smooth and reflectance is sharp (Land and McCann 1971), and a feathered wash is smooth too.

In the simulation, unruly captures put unpainted print at a median distance of 1.4–2.0 a\*b\* units from a well-picked reference, with a 90th percentile of 3.3–4.2. The faint wash sits at a median of 3.3–7.0. 89% of the falsely lit pixels lie in blobs of 50 px or more: they look like washes, and a speck filter cannot remove them.

**Would someone looking at the output know when this has gone wrong?** Not from the pictures. A wrong reference gives paint in plausible places (the face, the area around glare), or a plausible absence. The evidence is the VDZ-era version, per Woodii's log entries "Do not use Chroma Diagnostic Tool v4.0 or v4.1 numbers" and "Earlier VDZ numbers came from v4.1 and are unusable":
- Its ICC read failed silently (bytes were passed to `ImageCmsProfile`), and its EXIF read came after `exif_transpose`. So every file was decoded as ProPhoto.
- The white point was applied twice.
- The default threshold was each image's 90th percentile, before a 100-px speck filter.
- Those faults surfaced through code review against synthetic images, not through the pictures.
- Rerun on a print with no paint in capture A, it shows 5.2% as paint, and it misses the cheeks and the wash on the painted print.

## 1.2 Internal contradictions

1. **Presence/absence is a decision, and a decision is quantitative.** Removing the numbers hides the decision rule; it does not remove it. TODO.md decides with opacity "from about 2 to 5 spreads", and with three presets whose "value used goes in the JSON only".

   If the author's standing position 5 carries over, it rules this out: "even 'brighteners present/absent' counts as characterisation, so the app does not make that call." A presence map makes exactly that call.
2. **A chroma method cannot show "lack thereof".** It misses:
   - tone-matched spotting (0–0.1% shown by every pipeline here);
   - neutral media;
   - deep shadows (masked);
   - faint washes flattened by 4:2:0 chroma quantisation;
   - paint absorbed into the reference (Fig. 1, rows 2–3).
3. **"Not colorimetrically accurate" conflates two needs.** Absolute accuracy is genuinely not needed. Within-frame consistency finer than a faint wash *is* needed, and that is what unruly captures destroy (wash AUC 0.995 → 0.84).
4. **The README promises what only measurement could confirm.** It says the tool will "reveal details invisible to the naked eye" (README:7). The only check the request allows is the naked eye.
5. **"Faint signals are shown bright" works against "lack thereof".**
   - With opacity that saturates early, weak and strong evidence look alike.
   - For 2-D noise, the share beyond k spreads is exp(−k²/2): 13.5% at k = 2 and 1.1% at k = 3.
   - On a *clean* capture with good picks, the TODO prototype shows 15% of the unpainted print.
   - Part of the cause: the spread is measured on median-filtered a\*b\* and is tiny (median 0.33).
   - The other part: filtering a\*/b\* but not L\* breaks the hue–lightness link at every edge of a toned print. At half opacity, edges are shown at 15% against 5% for flat areas. Without that median, the total is 1.5%.
6. **"The luminescence stuff is moot" cuts the wrong way under either reading.**
   - If it means UV luminescence, it discards the modality conservators actually use to tell many applied media from the print.
   - If it means luminance, it is backwards: unruly captures make the neutral axis bend with lightness more. TODO.md silently keeps the lightness dependence.
7. **"Garbage in, garbage out" (positions 6–7) presumes controlled kit.** Here the input is unruly by premise, and garbage at the output looks like a finding.
8. **4.1.2 still contradicts message 2.**
   - The montage footer prints `noise_floor(LRC):3.16` (`Chroma_diagnoser_v4.1:1359,1382`).
   - `run_log.csv` holds the thresholds (:1672–1673).
   - The JSON holds the lightness-band counts, medians and IQRs (:953, :1437).
   - The README still claims a "threshold between the background substrate (noise) and actual pigment (signal)" (:20), "Tier 1 (Solid): Opaque, unmodified pigment" (:25), and that researchers can "distinguish between faint residue and solid paint" (:66).
9. **"If it is not easy, nobody will do it" (position 2) clashes with boxes drawn per image** (TODO.md's first open decision). Whether that burden sank Chroma mode is unknown.

## 1.3 Scope that deletes the only feedback channel

Only something that *knows* can validate a map: the object under magnification, raking light or UV; a known-unpainted print; or a spot measurement. The scope removes all three:
- The request removes quantitative reading.
- Woodii's log records "Chroma mode is qualitative, not quantitative: no ground-truth validation maps" (*no reason recorded*), and "Spectrophotometer spot readings … Parked".
- 4.1.2 removed the Jaccard stability analysis, the numerical outputs and the area percentages. Those are the only quantities a negative control could be scored with.
- Neither repository holds one real capture with known paint.

What happens without that channel is already on record:
- Chroma mode was about 2,800 lines, tested only on synthetic prints, and removed after one real run.
- Woodii's own note says those synthetic tests "check the code, not the method" (decisions-0.4.md:740).
- The health check written the same day says features were "built and extended before the one before it was tried on real captures", and recommends "one feature per batch, each tried on real captures before the next is started".

TODO.md repeats the pattern. "Try on real VDZ captures before anything else is added" is its *last* line. Before that, it builds eight pipeline steps, three pictures, presets, and synthetic tests drawn from its own model.

## 1.4 Terms without an operational definition

| Term | Problem |
|---|---|
| **paint / applied media** | Does it include dyes, watercolour, oil, pastel, pencil, retouching, spotting, varnish? The neutral and tone-matched ones are silently out of scope. |
| **presence / lack thereof** | A hidden decision rule with unknown error rates. |
| **monochrome** | Toned prints change hue with density. Deteriorated prints carry stains: foxing and mat burn are shown as paint by every pipeline here. |
| **unpainted reference / substrate** | The paper base, or the image tone at each density, in *this* capture? |
| **neutral** (for "boost around neutral") | D65 neutral (what 4.1.2 boosts around), the paper, or the image tone? |
| **unruly** | An unbounded set of degradations, so no test set can cover it. |
| **spread** | Pixel noise, when the dominant error is a systematic, coherent cast. |
| **faint** | Relative to what? |
| **"visualisation only"** | The picture still encodes a decision. |
| **luminescence** | Two possible readings (item 6 above). |
| **optimal** | No objective and no data. |

## 1.5 Assumptions already refuted by history or the literature

- **"Synthetic tests validate the method."** Chroma mode, and Woodii's own note that they check the code, not the method. TODO.md's planned tests are of the same kind.
- **"A self-estimated, image-wide baseline copes with extensive paint."** The v4.1 LRC self-suppression. Woodii's log accepted "Do not carry v4.1's … LRC baseline" and decided "No windowed baseline". TODO.md's automatic fallback reintroduces it.
- **"A histogram-peak noise floor separates pigment from substrate."**
  - On a toned print it sets the C\*ab threshold at the print's own chroma (12–20 here).
  - In capture A, 4.1.2's C\*ab view shows 0% of the cheeks and the wash, but 15% of the foxing.
  - Its LRC view shows 12% of the cheeks and 0.2% of the wash: the wash lowers chroma, so its signed LRC is negative.
  - TODO.md is right to switch to a vector.
- **"Pixel noise is the right unit."** In unruly captures the error is a coherent cast of 2–4 a\*b\* units.
- **"One photograph tells you the light."** Single-image colour constancy is under-determined. Grey world fails when one colour dominates (Buchsbaum 1980), and comparisons on real images found substantial residual errors for every algorithm tested (Barnard et al. 2002).
- **"A label prevents a quantitative reading."** A coloured overlay reads as a segmentation. As an analogy only, disclaimer labels on retouched images do little to blunt their effect (Tiggemann et al. 2013).
- **"The iterations improved the pictures."**
  - The C\*ab picture rule is the same in v1.1 (Dec 2025) and 4.1.2 (Nov 2026): histogram peak, a 1%-of-peak cut-off, tiers at the 50th/85th percentiles, opacities 0.4/0.8/1.0 over 15% grey, and a\*b\* ×3 with CLAHE.
  - What changed was the framing: "Forensic Image Segmenter" → "Scientific batch chroma analysis" → "FADGI-compliant" → "A visualiser, not a measuring tool". The FADGI claim was attached to the ProPhoto default, and the guidelines give no basis for decoding untagged files as ProPhoto. Provenance and decoding also changed.
  - Two of the six committed versions could not run as committed. v3.0 was a wrapper writing to `/mnt/data/…`, and "Textual Updates" stripped the wrapper along with the opening quotes; it has not parsed since 10 Aug 2026. v4.0 contained `INPUT_DIR = <INPUT PATH HERE>`.

## 1.6 Trivial or vacuous ways to satisfy the request

- **Eyedropper white balance plus steeper Lab a\*/b\* curves** (Margulis 2005) is "boost around neutral" in two clicks. DStretch (Harman; decorrelation stretch, Gillespie et al. 1986; Le Quellec et al. 2015) is the established free tool for faint pigment in field photos.
- **Per-image normalisation always shows something.** v4.0's percentile threshold did exactly this.
- **Labels and presets** hide the numbers but keep the decisions.
- **Tests drawn from the tool's own forward model** pass by construction.
- **Calling the result "optimal"** with no criterion.

## 1.7 What a competent sceptic would say

- **A photograph conservator:** hand colouring is identified at the object, with a stereo microscope, raking or transmitted light, UV fluorescence, and XRF, FORS or Raman (Lavédrine 2009; Stulik and Kaplan 2013). Tone-matched spotting is designed to be invisible. Foxing, mat burn, silver mirroring and uneven toning all change colour. A phone-photo map is triage at best.
- **An imaging scientist:** this is colour constancy, and a wash cannot be told from a cast. Phone pipelines tone-map locally, white-balance on scene content, denoise chroma and process by content (Hasinoff et al. 2016; Delbracio et al. 2021). Demosaicking produces false colour (Gunturk et al. 2005). 4:2:0 subsampling (Wallace 1992), lateral CA, and failure of the Luther condition do the rest.
- **A statistician:** this is detection, and the criterion sets the error rates (Green and Swets 1966). Millions of pixels guarantee false alarms, and without ground truth neither error rate is known.
- **Rock-art recorders** (the nearest precedent): enhancement guides *where to look*, finds are confirmed at the panel, and mineral stains are a standing confound.

## 1.8 Part 1's answer to the question

**How should the tool establish what the unpainted print looks like?** Within the request's scope it can only assume it: from picks, from a majority-unpainted fit, or from neutrality. In-frame references are excluded.

**How would someone looking at its output know when that has gone wrong?** They would not:
- wrong assumptions yield plausible pictures;
- measurement, ground truth and stability checks are all removed;
- the VDZ-era faults passed through real use unnoticed.

The output's correctness cannot be established from inside the specification. That is why the request is ill-posed.

## 1.9 What the experiments do and do not show

**The synthetic print.** A split-toned, silver-like print on yellowed paper, built from skimage's "astronaut" portrait. It carries:
- Beer–Lambert washes (Chroma mode's own model): cheeks ΔE 7.8, lips 40, flag 10–22, yellow patch 18, and a chroma-lowering backdrop wash ΔE 4.5;
- neutral and tone-matched spotting;
- foxing and mat burn.

**The captures.** Phone-like, with:
- mixed light, vignetting and colour shading;
- lateral CA;
- gray-world or white-patch white balance;
- saturation and S-curve looks, and local tone mapping;
- chroma blur, glare, and 4:2:0 JPEG.

**What this shows:** that the failure mechanisms exist, and how large they are.

**What it does not show:** how often they occur on VDZ prints. Several real failure modes are not simulated: content-aware face processing, HDR merges, gloss and texture, real retouching.

**The alternative was tuned on this set.** I chose its floor (0.8 a\*b\*) and its two-capture threshold (1.5) after seeing the A+B results. Capture C was added afterwards as a check, and it exposed the shared-fringing failure.

---

# Part 2. The maximum honest version

## 2.1 The claim that survives

> For this print, the tool shows where the photograph's colour departs from the tool's own displayed model of the unpainted print, by more than that model's own uncertainty in this photograph. With two deliberately different photographs, it shows where both depart in the same direction. Those places are worth examining on the object. They may be paint, retouching, staining, foxing or uneven toning; in a single photograph they may also be the photograph. Places with no departure are not shown to be unpainted.

**What it does not claim:** absence; paint as opposed to other causes; amounts or areas; faint washes from one unruly capture; neutral or tone-matched media.

**An explicit objective**, since "optimal" needs one. This is the author's call to confirm:
1. Never show confident paint where there is none.
2. Then, show moderate and strong paint.
3. Show faint washes only when two captures agree.

## 2.2 How the tool should establish the unpainted print, per capture

1. **Marks.** The user draws 4–6 boxes believed to be unpainted, spanning light to dark and spread over the frame, plus the paper margin if there is one.
   - Coverage is shown as a picture, not a number.
   - Marks are carried to a second capture by SIFT plus a RANSAC homography. Prints are flat, and the prototype registered to within 0.13–0.42 px.
2. **An explicit model.** a\*, b\* = f(L\*) + g(x, y), fitted robustly on the marked pixels.
   - f is a cubic only if the marks cover at least 40 L\* units with no gap over 15; otherwise it is a line. This is the lesson of Woodii's adversarial review.
   - g is a plane only if the marks span at least 40% of the frame in both directions.
   - The same light smoothing is applied to L\*, a\* and b\*.
3. **The unit.** Leave-one-mark-out disagreement, combined with the texture inside each mark, with a floor of 0.8 a\*b\* (one or two 8-bit code steps). In unruly captures the unit grows from 0.8 to 1.6–2.7, which honestly lowers sensitivity.
4. **No automatic presence map.** Without marks, the tool shows only the boost picture, labelled "automatic: assumes most of the print is unpainted".

## 2.3 How a viewer would know when the reference has gone wrong

**The pictures (Fig. 2):**
1. The capture, with the marks drawn on it.
2. **"Assumed unpainted"**: the capture's own L\* with the model's a\*/b\*. If it shows colour or a gradient the user knows is not on the print, the model is wrong. It reveals gross failures, but not subtle contamination; the words caught that.
3. **The boost about the model**: model + k·(pixel − model), with k fixed.
4. **The departure picture.**
   - Opacity is *linear* from 2 to 6 units.
   - Hue shows the direction of departure, not the paint's colour.
   - Hatching marks pixels that cannot be judged, and lightness or places the marks do not cover.
5. **"Seen in both"** (needs two captures): both captures at 1.5 units or more, pointing within 60° of each other. Grey hatching marks departures seen in one capture only.

**The tripwires.** All of these exist in the prototype except the last:
- "The marks disagree with each other by more than their own texture: one may hold paint, or the light varies more than the model allows; the map is shown at lower sensitivity." This fired on the contaminated capture A.
- "Mark *n* disagrees with the others." This fired on the clean contaminated capture.
- "The marks do not span the frame."
- "The marks cover little of the lightness range: tones outside it are guessed (hatched)."
- "Much of what is shown sits on edges: colour fringes … are likely."
- "Most of what is shown changes smoothly across the frame, as uneven light does … a second photograph under other light tells them apart."
- With one capture, always: "one photograph: departures may come from the photograph." (This one is not yet in the prototype.)

**The second capture must differ in light** (window against lamp, or another direction) **and in lens or device**, or the print must sit elsewhere in the frame.
- Rotating a centred print does nothing: lateral CA and vignetting are radial.
- Pairs with opposite-sign fringing (A+B, B+C) leave 0.1% of the unpainted print shown.
- The same-sign pair (A+C) leaves 3.1%, 98% of it on edges. Reversing C's fringing leaves 0.04%.
- So the tool should warn when both captures share a lens; the EXIF lens model is enough to tell.

**The negative control.** One known-unpainted print, captured in the same session. If it lights up in "Seen in both", read nothing from that session.

## 2.4 What the prototype shows

These are synthetic results. "Shown" means opacity ≥ 0.25, or alpha ≥ 0.2 for v4.x.

**Negative control: share of the unpainted print shown as paint (%)**

| Pipeline | clean | unruly A | unruly B |
|---|---:|---:|---:|
| v4.0/4.1.0 (VDZ-era), C\*ab / LRC | 0.1 / 0.2 | 5.2 / 5.1 | not run |
| v4.1.2, C\*ab / LRC | 0.0 / 0.0 | 0.2 / 0.3 | 0.0 / 0.3 |
| TODO.md prototype, good picks | 15.0 | 14.9 | 12.0 |
| TODO.md prototype, automatic reference | 78.8 | 19.6 | 18.2 |
| Alternative, one capture | 0.5 | 2.8 | 1.4 |
| Alternative, A+B | | 0.1 | |
| Alternative, A+C (same-sign fringing) | | 3.1 | |
| Alternative, B+C | | | 0.1 |

**Painted print, capture A unless stated: share of each region shown (%)**

| Pipeline | unpainted | wash | cheeks | lips | patch | foxing | mat burn | spot (matched) | spot (neutral) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| v4.0 C\*ab | 0.2 | 0.1 | 0.2 | 100 | 93.5 | 46.1 | 13.7 | 0.0 | 0.3 |
| v4.0 LRC | 0.9 | 0.4 | 2.5 | 100 | 98.9 | 48.0 | 28.2 | 0.0 | 1.1 |
| v4.1.2 C\*ab | 0.0 | 0.0 | 0.0 | 99.6 | 68.8 | 15.3 | 7.6 | 0.0 | 0.0 |
| v4.1.2 LRC | 0.2 | 0.2 | 12.4 | 99.7 | 97.5 | 28.6 | 13.0 | 0.0 | 0.0 |
| TODO.md, good picks (clean) | 20.3 | 99.7 | 100 | 100 | 100 | 100 | 99.9 | 21.4 | 69.5 |
| TODO.md, good picks | 12.7 | 45.2 | 87.3 | 100 | 100 | 89.0 | 63.8 | 0.8 | 16.7 |
| TODO.md, automatic | 11.9 | 15.7 | 95.8 | 100 | 100 | 99.2 | 92.9 | 3.4 | 36.8 |
| TODO.md, automatic, wash over 80% | 68.9 | 34.4 | 100 | 100 | 100 | 98.5 | 83.5 | 26.6 | 36.9 |
| Alternative, one capture (clean) | 0.5 | 94.7 | 100 | 100 | 100 | 100 | 89.7 | 0.1 | 28.2 |
| Alternative, one capture | 2.3 | 91.9 | 90.8 | 100 | 100 | 93.9 | 78.7 | 0.0 | 29.5 |
| Alternative, one capture, mark on wash | 0.0 | 0.1 | 0.0 | 100 | 96.8 | 35.2 | 19.7 | 0.0 | 1.4 |
| Alternative, A+B | 0.0 | 78.9 | 96.9 | 100 | 100 | 94.3 | 59.8 | 0.0 | 7.4 |
| Alternative, A+B, A's mark on wash | 0.0 | 0.2 | 12.9 | 100 | 99.5 | 61.9 | 28.6 | 0.0 | 0.0 |
| Alternative, A+C | 3.1 | 94.1 | 91.7 | 100 | 99.9 | 89.8 | 83.3 | 0.0 | 35.0 |
| Alternative, B+C | 0.1 | 79.1 | 91.0 | 100 | 99.9 | 85.5 | 56.1 | 0.0 | 7.3 |

How to read the last rows:
- A contaminated mark makes the alternative fail *safe*: it shows less, and the words say why.
- Foxing and mat burn persist across captures because they are on the object. No chroma tool can call them "not paint".
- Tone-matched spotting is invisible to every pipeline.

**Separability** (distance from TODO's well-picked reference):

| Capture | Unpainted median / p90 | Wash median, AUC | Cheeks AUC | Blue-flag AUC |
|---|---|---|---|---|
| clean | 0.6 / 1.2 | 4.4, 0.995 | 1.000 | 1.000 |
| A | 2.0 / 4.2 | 7.0, 0.841 | 0.984 | 0.998 |
| B | 1.4 / 3.3 | 3.3, 0.849 | 0.993 | 0.999 |

**Figures** (in `/home/user/xpw/6d8ad6/work/out/`):
- **`fig1_todo_failures.jpg`**: the TODO.md pipeline on a print with no paint (purple face and backdrop, fringed edges); with one pick on the wash (the wash vanishes and the face turns yellow-green); and with an automatic reference under an 80% wash (the unpainted face turns yellow).
- **`fig2_alternative.jpg`**: the five panels plus the words, for good and contaminated marks.
- **`fig3_negative_control.jpg`**: no paint. The TODO map; the alternative from one capture (glare halo and foxing); and from two captures (foxing only).

## 2.5 The feedback channel, kept below the surface

This is consistent with the author's position 3 (complexity under the surface) and position 14 (the real test is objects). It is not a statistical exercise.

1. **Before code:** ask what failed in Chroma mode's real run: the method, the picks, or the maps. TODO.md inherits all three.
2. **Four test captures:**
   - one known-unpainted print of the same kind;
   - one print whose paint a conservator has marked under magnification and UV;
   - each photographed twice, the way the real captures will be made.

   Judge side by side, by eye.
3. **Two developer-side numbers, never shown to users:**
   - the share of the negative control shown in "Seen in both" (should be nil);
   - the share of the conservator-marked paint that is shown.

   Add features only after both pass.

## 2.6 Checklist replacing TODO.md's order

- [ ] Record why Chroma mode failed.
- [ ] Assemble the four test captures before any code.
- [ ] Now, cheaply, remove 4.1.2's leftover contradictions with message 2:
  - the threshold number in the footer;
  - the CSV thresholds;
  - the LRC band data in the JSON;
  - the README's "actual pigment", "Solid: opaque, unmodified pigment" and "faint residue and solid paint".
- [ ] Build the minimum, then run it on the four captures:
  - load: ICC to sRGB, untagged as sRGB, EXIF orientation, roughly 2–3k px;
  - the can't-judge mask;
  - the marks and the model;
  - the assumed-unpainted panel;
  - the linear departure panel;
  - the words.
- [ ] Add the second capture: registration, "Seen in both", and the shared-lens warning. Run it on the four captures again.
- [ ] Only then: boost styling, settings, packaging, a `.py` extension, and removing the unparseable v3.0.
- [ ] Drop from TODO.md:
  - the automatic presence map;
  - early-saturating opacity;
  - the a\*b\*-only median;
  - per-band medians (replaced by a smooth curve with visible coverage);
  - the three presets.
- [ ] Rewrite the README around what the tool shows and what it cannot.

## 2.7 The answer to the question, both parts

**Part 1.** From one uncontrolled capture, the tool can only *assume* what the unpainted print looks like. Pictures from a wrong assumption are as convincing as pictures from a right one. With measurement and ground truth excluded, no viewer can tell them apart, and the project's history (the VDZ-era decoding, Chroma mode) records exactly that.

**Part 2.** The tool should:
- model the unpainted print explicitly, from marks and the margin;
- **show** that model as a picture;
- scale departures by how much the marks disagree with each other;
- say in words where it is guessing, or where it is contradicted;
- use agreement between two deliberately different photographs, plus a negative-control print, to separate the object from the capture.

A viewer knows something went wrong when:
- the "assumed unpainted" picture shows colour they know is absent;
- a tripwire fires;
- a departure appears in one capture only;
- the negative control lights up.

The tool cannot show that it went right. Only the object can.

---

## Appendix A: files

Everything below is in `/home/user/xpw/6d8ad6/work/`.

| File | Purpose |
|---|---|
| `sim.py` | Print and captures (clean, A, B, C) |
| `evalgt.py` | Ground truth in capture geometry |
| `picks.py` | The user's marks |
| `run_v412.py` | 4.1.2's internals, run on the copy `v412.py` |
| `run_v40.py` | v4.0 as committed, placeholders filled |
| `todo_pipeline.py`, `run_todo.py` | The TODO.md prototype. Its open choices: 2-L\* bands, 5-band smoothing, 5-px a\*b\* median, 3-px speck median, opacity smoothstep 2–5 raised to the power 0.6, spread floor 0.05, automatic fit 4 rounds keeping z < 3 |
| `honest.py`, `hrun.py`, `run_honest.py` | The alternative design |
| `separability.py`, `shared_artefact.py`, `consolidate.py`, `tables.py`, `figures.py` | Analyses, tables, figures |

Results are in `out/*.json`. `out_cli/` holds 4.1.2's own CLI montages; their footer reads `noise_floor(LRC):3.16`. Run any script with `python3 <script>` from `work/`.

## Appendix B: sources

- Barnard, Cardei and Funt (2002), and Barnard, Martin, Coath and Funt (2002): A comparison of computational color constancy algorithms, Parts I and II, *IEEE TIP* 11(9).
- Buchsbaum (1980), *J. Franklin Inst.* 310(1):1–26.
- Delbracio, Kelly, Brown and Milanfar (2021), Mobile computational photography: a tour, *Annu. Rev. Vis. Sci.* 7.
- Gillespie, Kahle and Walker (1986), *Remote Sens. Environ.* 20(3):209–235.
- Green and Swets (1966), *Signal Detection Theory and Psychophysics*.
- Gunturk et al. (2005), *IEEE Signal Processing Magazine* 22(1):44–54.
- Harman, DStretch (dstretch.com).
- Hasinoff et al. (2016), *ACM TOG* 35(6).
- Land and McCann (1971), *JOSA* 61(1):1–11.
- Lavédrine (2009), *Photographs of the Past*, Getty Conservation Institute.
- Le Quellec, Duquesnoy and Defrasne (2015), Digital image enhancement with DStretch, *Digital Applications in Archaeology and Cultural Heritage*.
- Margulis (2005), *Photoshop LAB Color*.
- Stulik and Kaplan (2013), *The Atlas of Analytical Signatures of Photographic Processes*, Getty Conservation Institute.
- Tiggemann et al. (2013), *Body Image* 10(1):45–53.
- Wallace (1992), *IEEE Trans. Consumer Electronics* 38(1).

**Project records:**
- Visualiser commits 9f4420e, 0949bdc, 18fbd5a, f95e1f8, a365ea6, 6176d62 and 4584a2f.
- Woodii `docs/chroma-mode-plan.md` (de6f9b1).
- Woodii `docs/decisions-0.4.md`: 5b1757d lines 705–745, and the "Chroma mode removed" section at de6f9b1.
- Woodii `docs/health-check-2026-10-29.md`.
- Woodii `docs/AUTHOR-POSITIONS.md` (origin/main).
