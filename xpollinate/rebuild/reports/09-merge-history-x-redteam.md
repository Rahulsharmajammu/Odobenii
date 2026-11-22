<!-- Saved verbatim by the coordinator from the resumed history agent's hand-back (merge round; the harness refused
report files). The harness's two-space indent is removed; nothing else is changed. -->

The harness again refused report files, so the full revised report is below; it can be saved verbatim as reports/09-merge-history-x-redteam.md. I did not modify either repository in this round. New bench code, results and figures are in /home/user/xpw/121087/work/ (listed in section 10).

---

# The handpaint visualiser, v2: history meets the red team

Standpoint: software history and the premortem, revised after reading the red-team report (`/home/user/xpw/121087/peer-report.md`) in full. Both benches are synthetic: they check code against a model, not the method on real prints.

## 0. What changed from v1, in brief

- **Uneven light.** In v1, one photograph under mixed light showed colour on 38–52% of untinted prints, and the warnings fired on painted prints as well.
  - I adopted the red team's "Seen in both" and tested it on my own simulator, with a second photograph under reversed light, a different lens and the print moved.
  - I adapted their unit: their leave-one-mark-out disagreement becomes a leave-tones-out error for the automatic model.
  - Result: untinted prints fall to 0.0–0.4% shown (their bench: 0.1%).
- **The departure picture needs a witness.** It is drawn only when a second, deliberately different photograph agrees, or the user has marked unpainted areas on that image. Marks become one way in, not a requirement.
- **One picture of the model.** "Assumed unpainted", exaggerated by the same factor as the boost and hatched where the model is guessing, replaces both my tone strip and their unexaggerated panel.
- **One negative control per session.** It decides whether any departure picture from that session is shown.
- **Retractions.** About a dozen, listed in section 9.

---

## 1. Verdict (v2)

**Rebuild the model of the unpainted print, and draw no departure picture without a witness.**

For each print the tool shows four panels, with no numbers anywhere:
1. the photograph, with the print's edge and the paper taken as unpainted outlined;
2. **Assumed unpainted**: the model's colour at each pixel's lightness, exaggerated about the paper, hatched where it is guessing;
3. the **boost** around that model;
4. **Seen in both**: departures present in both of two deliberately different photographs, in the same direction.

Rules:
- Panel 4 needs a witness that is not the judged pixels: a second photograph, or the user's marks.
- With one photograph and no marks, the tool shows panels 1–3 only.
- A known-unpainted print photographed in the same session gates the session.
- Grey in panel 4 never means "unpainted".
- Hue means "direction of departure from the model", not "colour of the paint".

**Before any code:**
- ask the author which part of Chroma mode failed;
- make four test captures: one known-unpainted print and one conservator-marked print, two photographs each.

**What would reverse this:**
- Real pairs from the same phone keep colour on the control in both photographs, because the phone's face and sky processing is the same each time. Then the witness must be a different device or a raw capture, or marks.
- The author will neither take second photographs nor mark images. Then only panels 1–3 remain, and they must be judged on their own.
- Real untinted but stained prints light up in "Seen in both". Then the control rule withholds everything on deteriorated prints, and departure pictures are the wrong product.

---

## 2. The red team's Part 1, objection by objection

"Answered" means a mechanism in the v2 design responds to the objection. "Accepted" means I concede it, and I say what is lost. The red team's section numbers are kept.

### 2.1 What does the unpainted print look like (their 1.1)

| # | Objection | Response |
|---|---|---|
| 1.1a | User picks are circular. A pick on a faint wash flips the answer. Narrow picks are extrapolated. | **Accepted for picks as the only evidence**, answered for the default. Marks become optional, and when used they carry the red team's own guard: leave-one-mark-out disagreement, so a mark on paint lowers sensitivity and says so. On their bench that fails safe. The default witness is a second photograph, which needs no judgement. *Loss:* a mark on a wash still hides that wash. |
| 1.1b | An automatic fit assumes paint is a minority; a wash over most of the sheet becomes the reference. | **Partly answered, partly accepted.** My consensus fits one smooth curve through the densest colour of the tone bands, anchored at the paper. That assumes paint dominates only a minority of tones, not a minority of pixels. Single photograph: a painted sky 100% and a wash over every light grey 100% shown, against 23% and 8% for TODO.md's fallback. **Accepted for a wash over the whole picture** (P8, section 7): the model absorbs it in both photographs (4% shown). Only panel 2, whose model turns olive for a sepia print, reveals it. *Loss:* whole-sheet washes are not shown, only exposed. |
| 1.1c | "Unpainted = neutral" is wrong for toned prints, and camera white balance reacts to paint. | **Accepted.** Neither design uses that prior. |
| 1.1d | An in-frame reference is excluded by "unruly"; a margin gives the paper's colour, not the image tone at each density. | **Answered in part.** A paper border is part of the object, not a target, and "unruly" does not remove it. v2 uses it only to anchor the light end of the curve and to show the light's gradient, and never judges it: it is reference. *Accepted:* it does not give the tone at each density, so tones far from both paper and supported bands are hatched as guessed. |
| 1.1e | In one photograph a smooth wash and a smooth cast are the same signal. | **Accepted for one photograph, answered for two.** A cast changes with the light and a wash does not; with reversed light the cast's departures point opposite ways and are rejected by the 60° test. My bench: mixed-light controls go from 1–44% shown to 0.0–0.4%. *Loss:* one photograph gets no departure picture. |
| 1.1f | Unruly captures put unpainted print 1.4–2.0 units from a good reference, and false pixels form blobs a speck filter cannot remove. | **Accepted.** v1's 5 px median on z does not address it. The two-photograph agreement removes coherent cast blobs. My v1 unit (band spread) was the wrong unit; v2 adds the model's leave-tones-out error (N4, one photograph: 44% → 1.0%). |
| 1.1g | Pictures do not reveal their own errors; the VDZ-era faults were found by code review. | **Accepted for decoding faults.** A uniform decode bias cancels in every panel, so only tests against known colours catch it; keep 4.1.1's colour tests. **Answered for model contamination:** panel 2 exposed both absorbed washes on my bench (P1's olive mid-greys, P8's olive print). |

### 2.2 Internal contradictions (their 1.2)

| # | Objection | Response |
|---|---|---|
| 1.2-1 | Presence/absence is a decision; removing numbers hides the rule. Position 5 rules out the call. | **Accepted that it is a decision.** The rule is fixed in code, and its error rates are scored on controls below the surface (their section 2.5). On position 5: it was written for Woodii's brightener question, and this author asked this tool to "visualize the presence, or lack thereof". The panel is renamed "where colour departs from the assumed unpainted print"; the user makes the call. *Loss:* the word "presence". |
| 1.2-2 | A chroma method cannot show "lack thereof". | **Accepted.** v2 never shows absence; grey means "no departure seen". Out of scope, stated in the README: neutral and tone-matched media, deep shadows, washes flattened by 4:2:0, absorbed washes. *Loss:* the literal "lack thereof". |
| 1.2-3 | "Not colorimetrically accurate" conflates absolute accuracy with within-frame consistency. | **Accepted.** Within-frame consistency is what the second photograph and the control test. |
| 1.2-4 | The README promises "details invisible to the naked eye". | **Accepted.** Rewrite the README around what the pictures cannot show. |
| 1.2-5 | Early-saturating opacity and the a\*b\*-only median raise false alarms; TODO's prototype shows 15% on a clean print. | **Accepted, with a correction.** Adopted: linear opacity 2→6 units, and the same median on L\*, a\*, b\*. My bench did *not* reproduce their edge mechanism: filtering L\* changed nothing (6.7% → 6.5%). My edge false colour is fringing made worse by 4:2:0: 31% of edge pixels with both, 7% fringing only, 0.1% 4:2:0 only. A further point: TODO.md leaves the spread floor open. Their prototype used 0.05 and found 79% false colour on an unpainted clean print; mine used 0.75 and found 0–2%. That open choice alone moves the result about 40-fold. |
| 1.2-6 | "Luminescence is moot" cuts the wrong way. | **Accepted as an ambiguity.** If the test captures show stains being confused with paint, a UV-fluorescence photograph is the cheapest discriminator, and the author's Woodii kit already uses a filtered 365 nm source. Parked, not adopted. |
| 1.2-7 | "Garbage in, garbage out" presumes controlled kit. | **Answered.** The session control and the second photograph make garbage show as garbage: the control lights up and the session's departure pictures are withheld. |
| 1.2-8 | 4.1.2 still contradicts message 2. | **Accepted, and v1's list was incomplete.** Add the JSON's LRC band counts, medians and IQRs (`Chroma_diagnoser_v4.1` lines 948–957 and 1437) to the footer threshold, console, CSV and README items. |
| 1.2-9 | Position 2 clashes with boxes per image. | **Answered by the rule in section 3.** Marks are optional. |

### 2.3 Scope, terms and refuted assumptions (their 1.3–1.5)

**1.3 The scope deletes the only feedback channel.** Accepted. Restored below the surface:
- their two developer-side scores: the session control's share shown, and conservator-marked paint shown;
- the four test captures before code;
- my line-up test (section 8).

**1.4 Terms with no operational definition.** Answered with definitions:

| Term | Definition in v2 |
|---|---|
| Paint | Any added colourant that departs from the model by more than the unit in both photographs. Neutral and tone-matched media are out of scope. |
| Presence | "Seen in both". Absence is never claimed. |
| Monochrome | The print's own colour is a smooth function of lightness, plus at most a frame-spanning gradient. Stains, foxing and uneven toning break this and show as departures. |
| Unpainted reference | The model, drawn as panel 2. |
| Neutral (for the boost) | The model, rendered grey in panel 3. |
| Unruly | What the second photograph can separate (light, fringing, glare) and what it cannot (shared processing, object-side colour). |
| Spread / unit | √(noise spread² + leave-tones-out error²), or leave-one-mark-out with marks, floored at 0.8 a\*b\*. |
| Faint | Below 3 units, so under 25% opacity. |
| Visualisation only | No number in any picture, log or README. The rule lives in code and in the developer's scores. |
| Optimal | Their objective, ordered (section 4). |

**1.5 Assumptions already refuted:**

| # | Assumption | Response |
|---|---|---|
| 1 | Synthetic tests validate the method. | Accepted, including for my bench. |
| 2 | A self-estimated baseline copes with extensive paint. | Answered for washes that dominate some tones (P4, P6). Accepted for whole-picture washes (P8). |
| 3 | A histogram noise floor separates pigment. | Accepted. |
| 4 | Pixel noise is the right unit. | Accepted; v2's unit adds the model's own error. |
| 5 | One photograph tells you the light. | Accepted. v1's paper-border light correction is retracted as a solution (section 9). |
| 6 | A label prevents a quantitative reading. | Accepted. Overlays still read as segmentation; mitigated only by the witness rule and the hatching. |
| 7 | The iterations improved the pictures. | Accepted, and it corrects v1. The picture rule was the same in v1.1 and 4.1.2, so the montage's survival shows familiarity, not validity. The same rule produced the VDZ outputs Woodii later called unusable. |

### 2.4 Trivial answers, sceptics and the verdict (their 1.6–1.9)

**1.6 Trivial or vacuous answers.**
- Eyedropper white balance plus steeper a\*b\* curves (Margulis 2005, as they cite), and DStretch: accepted as the **baseline v2 must beat** in the falsification test.
- Per-image normalisation always shows something: answered by the control and the second photograph (0.0–0.4% on my controls).
- Labels and presets hide decisions: accepted; presets dropped.
- Tests from the tool's own forward model: accepted.
- "Optimal" with no criterion: accepted; their explicit objective adopted.

**1.7 What competent sceptics would say.** All accepted:
- *Conservator:* the output is triage; confirmation happens at the object.
- *Imaging scientist:* the second photograph must differ in light *and* lens or device, or the print must move in the frame. My bench agrees: a shared lens left 0.4% against 0.0%; theirs 3.1% against 0.1%. Extended (section 3): a shared *phone pipeline* is the same risk.
- *Statistician:* error rates come only from controls and marked prints, kept as developer-side scores.
- *Rock-art recorders:* "where to look".

**1.8 The request is ill-posed.** Accepted for the literal request from one unruly photograph. v2 makes the narrower "where to look" claim, which can be checked against a witness and a control.

**1.9 The limits of their experiments.** Noted. The same limits apply to mine. My bench independently reproduces their two-photograph result, but both simulators share Beer–Lambert washes and a caricature of phone processing.

**One factual correction to Part 1.** They say the reason Chroma mode was dropped "was never recorded", citing `de6f9b1`'s "Open:" line. The next commit, `66d03e7`, records the author's answer of 30 October: "the results were not very user friendly, and while the chroma viewer might be inaccurate it allowed for useful visualisations, which were helpful." It does not say whether the method, the picks or the maps failed, so their "ask the author first" stands.

### 2.5 What v2 keeps that their Part 2 lacks, and what I concede

**Defended:**
1. **An automatic model, with no marks needed.**
   - It is what makes the zero-interaction path possible: a second photograph instead of 4–6 boxes per image.
   - Bench: two photographs plus the automatic model gave 0.0–0.4% on untinted prints, matching their marks-plus-two-photographs figure of 0.1%.
2. **Consensus across tones, anchored at the paper**, for the automatic path, rather than per-band medians. Single photograph: 100% against 23% and 8% (P4, P6). Conceded: it fails on whole-picture washes (P8), and marks are better when the user knows where the print is unpainted.
3. **Automatic finding of the print's edge and paper border.**
   - Cheap, and keeps the surroundings out (v1 bench: TODO fallback 24% → 2.5% false colour with the box).
   - The paper border is never judged.
   - Their "mark the margin" is the fallback when finding fails.
4. **The leave-tones-out unit.** New, and owed to their leave-one-mark-out idea. N4, one photograph: 44% → 1.0%.
5. **The line-up test** (section 8), which asks whether viewers can see a wrong model. Their design scores maps against ground truth but does not test whether its panel and tripwires are noticed.
6. **A restored small Tk window.** Position 2 applies. Conceded on order: it comes after the test captures pass.
7. **A cap of two warnings per picture**, against alarm fatigue. Their tripwire list is longer.

**Conceded as better in theirs, and adopted:**
- the explicit objective;
- asking the author first;
- four test captures before code;
- linear opacity 2→6;
- dropping presets;
- the same smoothing on all three channels;
- never showing absence;
- hue as direction of departure;
- SIFT plus RANSAC registration;
- the shared-lens warning;
- leave-one-mark-out for marks;
- rewriting the README around limits.

**Conceded as unnecessary:** the paper-border light plane as a fix for mixed light. It is kept only so that panel 2 shows the light's gradient as a gradient.

---

## 3. Per-image marks: the conflict and the rule that resolves it

**The disagreement.**
- The red team shows no departure picture without 4–6 user boxes on each image. Their reason: in one photograph, marks are the only evidence that does not come from the judged pixels, and automatic fits fail in plausible ways.
- v1 ruled out per-image interaction, citing the author's 30 October reason and position 2.

**Both were partly wrong.**
- The author's sentence does not say that picking sank Chroma mode; that was an agent's gloss, and v1 leaned on it too hard.
- Marks are not the only independent evidence. A second, deliberately different photograph is another witness, and it needs no judgement.

On my bench a second photograph plus the automatic model gave 0.0–0.4% on untinted prints. On theirs, marks plus one photograph gave 0.5–2.8%, and marks plus two gave 0.1%. Either witness works on the benches. What fails on both benches is one photograph judged by its own guess (1–44% here; their 20% for the TODO's automatic reference in an unruly capture).

**The rule, in one sentence:** No departure picture rests on one photograph's guess about itself: it needs a second, deliberately different photograph that agrees, or the user's own unpainted marks on that image.

**Consequences:**
- Per-image interaction stays optional and per-print evidence is required. The cost moves from the desk (minutes of marking) to the camera (seconds for a second shot under other light). That is where position 7 puts capture: "Capture conditions are the photographer's job".
- With one photograph and no marks, the tool still draws panels 1–3. The footer says: "One photograph and no marks: no departure picture. Add a second photograph under other light, with another camera or the print moved, or mark unpainted areas."
- **What "deliberately different" means:** different light (window against lamp, or another direction), *and* a different lens or device, or the print elsewhere in the frame.
  - The tool compares EXIF make, model, lens and software.
  - If they match, it warns: "Both photographs from the same camera: its colour fringes, and any processing it applies to faces and skies, may survive."
  - This extends the red team's shared-lens point to shared phone processing (Apple's per-person skin-tone processing, as reported, would be identical in both shots).

---

## 4. The design, v2: components and connections

**Flow:** two photographs of a print (or one, plus optional marks) and the session's control → load → prep → find the print → pair and register → model per photograph → unit and judgement → departures → "Seen in both" → four panels and words → record. The control goes through the same path first.

| Component | v2 behaviour | Source |
|---|---|---|
| load | Pillow, EXIF orientation, any ICC profile to sRGB through LittleCMS, untagged files as sRGB, about 2,400–3,000 px on the long edge | both |
| prep | Same 5 px median on L\*, a\*, b\*. Not judged: clipped (any channel ≥ 0.98, dilated) and near-black (L\* < 8) | theirs (median), both (exclusions) |
| find_print | Largest bright, smooth ring, filled: the print and its paper border. Outlined. Falls back to the whole frame and says so | v1 |
| pairing | `<print>_1`, `<print>_2`. SIFT plus RANSAC homography, photograph 2 onto 1 (bench: 137–149 inliers, 0.48–0.65 px RMS under a 4° rotation, 5% scale change and shift). EXIF comparison for the same-camera warning | theirs (registration, lens); v2 (shared pipeline) |
| model | **With marks:** their model. f(L\*) is a cubic if the marks cover at least 40 L\* with no gap over 15, otherwise a line; g(x, y) is a plane if the marks span at least 40% of the frame both ways. **Without marks:** consensus quadratic f(L\*) through one density peak per 2 L\* band (RANSAC over bands, Tukey refit), anchored at the brightest paper; g(x, y) a plane measured only on the paper border, if it surrounds the picture | theirs; v1 |
| unit | Marks: leave-one-mark-out disagreement combined with texture. Automatic: √(spread² + leave-8-L\*-out error²). Floor 0.8 a\*b\* | theirs; adapted |
| judgement | Paper border: reference, not judged. Tones beyond the supported range: not judged. Tones inside a gap of more than 15 L\* between supported tones: judged but "guessed" | v2 |
| departure | v = (a\*, b\*) − model; z = \|v\| / unit, per photograph | both |
| Seen in both | z ≥ 1.5 in both photographs, directions within 60°. Opacity linear on the weaker one, 2→6 units. Hatched: one photograph only, or not judged | theirs |
| panels | 2 × 2: (1) photograph with outlines; (2) Assumed unpainted, section 5; (3) boost: the model grey, departure ×4, soft-limited; (4) Seen in both, only under the section 3 rule | merged |
| control | Section 5 | merged |
| words | Standing: name, "Visualisation only – not a measurement", the evidence used. At most two warnings, in this order: control lit (session withheld); one photograph with no marks (no departure picture); same camera for both photographs; no paper border found. With marks, their tripwires: marks disagree, marks do not span, colour sits mostly on edges | merged |
| record | JSON provenance; a run log with no thresholds; failures with reasons | both |
| front ends | CLI; the v1.2 Tk window restored after the gate | v1 |

**The objective** (theirs, to be confirmed by the author):
1. On the session control, nothing in panel 4 beyond specks.
2. Then show moderate and strong paint.
3. Show faint washes only where both photographs agree.

**Order of work:**
1. Ask which part of Chroma mode failed.
2. Make the four test captures.
3. Remove 4.1.2's leftovers: footer threshold, console, CSV, JSON LRC band data, README.
4. Build panels 1–3 for one photograph and run them on the test captures.
5. Add the second photograph, "Seen in both" and the control rule, and run again.
6. Add marks only if the test captures show the automatic model failing in ways marks fix.
7. Then the window, packaging, the `.py` extension, and removing v3.0.
8. Then the line-up test.

---

## 5. One model picture and one negative control

### (a) The model picture: "Assumed unpainted" (panel 2)

**What it shows:** for every pixel, the model's colour at that pixel's lightness, light gradient included. It is exaggerated about the paper's colour by the same factor as the boost (×4, soft-limited), so contamination is as visible as paint. It is hatched where the model is guessing (a gap of more than 15 L\* with no supporting tone) or not judging. The evidence it rests on (print edge, paper border, marks) is outlined on panel 1.

**Decision rule:** Panel 2 must look like a plausible untouched print: one family of hue changing smoothly from paper to black, plus at most an even gradient that the paper border shares. Wherever it shows a hue that the paper and the shadows do not share, the model has taken a wash for the print at those tones, and panels 3 and 4 are not to be read at those tones.

**On the bench:**
- P8 (one wash over the whole picture): panel 2 turned a sepia print olive, while panel 4 showed almost nothing.
- P1: the mid-greys went olive.
- N4 (untinted, mixed light): sepia with a warm-left, blue-right border, which is the light, visible as a gradient.

**Dropped from v1:** the separate tone strip. Its two jobs, the exaggerated tone ramp and the hatching of unsupported tones, moved into panel 2. There the viewer checks them on the objects instead of mapping a lightness ramp to the picture in their head. Also dropped: v1's "ambiguous tones" hatch, which was erratic on the bench (13–20% hatched on untinted prints).

**Dropped from the red team's version:**
- Rendering the model at its true, unexaggerated colour. Their own note says it "reveals gross failures, but not subtle contamination"; exaggeration is what made P1's olive mid-greys visible.
- Requiring marks before the model is drawn. The automatic model is drawn the same way.

### (b) The negative control

**What it is:** one print known to be unpainted, of the same kind as the session's prints. It is photographed in the same session in exactly the same way: same cameras, same lights, both photographs if pairs are used. It goes in `controls/`, is processed first, by the same rules, and its montage is always written.

**Decision rule:** If the control's departure picture shows colour beyond scattered specks, the departure pictures of the whole session are withheld, and every montage says: "The unpainted control shows colour: these pictures may show the capture, not the prints." Panels 1–3 are still drawn. "Specks" is a developer-side constant: start at 0.5% of the control's judged print, with no single patch over 0.1% of the frame. My bench controls in pairs gave 0.0–0.4%; the red team's same-lens pair gave 3.1% and would be withheld.

**Dropped from v1:**
- The control as a pooled reference shape (v1's first level of evidence). VDZ prints differ in paper and toning, so a pooled shape would import another print's tone. A control that defines the reference also cannot test it.
- The folder pick: a box's position does not carry over between different prints.

**Dropped from the red team's version:** "read nothing from that session" is narrowed to "withhold the departure pictures". The boost and the model picture make no call, and the author valued them.

**Kept from both:** the control as the only check that does not judge the tool by its own assumptions.

---

## 6. For each uncontrolled capture, how should the tool establish what the unpainted photograph looks like, and how would someone looking at its output know when that has gone wrong?

### Establishing it

The tool cannot measure the unpainted photograph. It builds an explicit model, a\*b\* = f(L\*) + g(x, y), from the best evidence that capture offers:
- **The user's unpainted marks, when given.** f is a cubic or a line depending on their coverage; g is a plane only if they span the frame; the unit is their mutual disagreement.
- **Otherwise, the photograph's own monochrome law.** One smooth curve threaded by consensus through the densest colour of the tone bands, anchored at the brightest paper. The paper border is found automatically and used as reference, never judged. The light gradient is measured on that border only, and only when the border surrounds the picture.

The unit grows wherever the model is guessing (leave-tones-out error), so sensitivity drops honestly there.

**What the model cannot know from one photograph:**
- a wash over most of the picture;
- a cast that varies across the frame, when there is no border;
- processing the camera applied to faces and skies.

So one photograph's departures are never drawn. A departure picture appears only where a second, deliberately different photograph of the same print departs the same way, or the user has marked unpainted areas.

### Knowing it has gone wrong

- **Panel 2, the model.** It must look like an untouched print, by the rule in section 5(a). Colour there that is foreign to the paper and the shadows means the model has taken paint for the print at those tones (P1, P8).
- **The outlines on panel 1.** If the paper outline sits on a painted area, or the print's edge is wrong, nothing downstream holds.
- **Panel 4's hatching.** Colour seen in one photograph only is hatched, not shown. Persistent single-photograph colour means the capture, not the print.
- **The control.** If it lights up, the whole session's departure pictures are withheld, and the montages say so.
- **The words:** at most two, in a fixed order.
- **What still gets through.** Colour that belongs to the object but is not paint (foxing, mat burn, uneven toning) persists in both photographs and on no control, and is shown. The hue of a departure is relative to the model: on P8 a blue wash showed as orange where the model had absorbed more blue than the floor carried. Neutral and tone-matched media never show. Grey therefore means "no departure seen", never "unpainted". Final confirmation is at the object.

---

## 7. Bench evidence for v2 (synthetic; checks code, not method)

**Set-up** (`pairs.py`, `pairs2.py`, `v2.py`):
- Photograph A is the first capture setting: a phone with a warm cast, or mixed light (warm left, cool right).
- Photograph B uses reversed mixed light, different saturation, contrast and JPEG quality, opposite-sign lateral fringing, and the print rotated 4°, scaled 0.95 and shifted.
- B is registered to A by SIFT plus RANSAC: 137–149 inliers, 0.48–0.65 px RMS.
- "Shown" means opacity ≥ 0.25 on the linear 2→6 ramp.
- Scoring uses print pixels usable in both photographs; the paper border is excluded.
- Disclosure: on my bench the "backdrop" paint mask covers everything above the floor line, figure included. P8's wash therefore covers the whole picture, not "about 80%" as first labelled.

**Untinted prints: share shown as colour**

| Case (A / B) | A alone, v1 unit | A alone, v2 unit | Seen in both |
|---|---:|---:|---:|
| N2 warm print, yellowed paper (phone / mixed reversed) | 10.6% | 4.9% | **0.0%** |
| N3 split-toned, no white balance / mixed reversed | 22.6% | 3.2% | **0.1%** |
| N4 warm print, mixed / mixed reversed | 43.6% | 1.0% | **0.0%** |
| N5 split, glare, mirroring, mixed / reversed | 33.1% | 19.7% | **0.1%** |
| N4s as N4, same-sign fringing (shared lens) | 39.7% | 1.6% | **0.4%** |

**Painted prints: visible paint shown, with false colour in brackets**

| Case | A alone, v1 unit | A alone, v2 unit | Seen in both | Notes on "Seen in both" |
|---|---|---|---|---|
| P4 painted sky, phone / mixed reversed | 99% (12%) | 95% (6.2%) | 50% (0.0%) | sky 55% |
| P5 the same sky, mixed / reversed | 96% (42%) | 89% (5.0%) | 65% (0.0%) | sky 71%; the rest hatched "one only" |
| P6 one wash over every light grey | 99.5% (18%) | 99.4% (12%) | 97% (2.1%) | |
| P1 portrait under a faint wash, face, lips, plant | 20% (68%) | 16% (30%) | 13% (0.2%) | lips 100%, face 92%; wash absorbed (9%); the floor's complementary ghost gone |
| P3 portrait, split-toned, mixed light | 38% (49%) | 23% (29%) | 13% (1.9%) | |
| P8 one wash over the whole picture | 22% | 15% | 4% | absorbed in both photographs; only panel 2 (olive) exposes it |

**What this supports:**
- **Two photographs fix v1's weakness on the model of light used here.** Untinted prints go to 0.0–0.4%, matching the red team's 0.1% on a different simulator.
- **The price is sensitivity to faint and moderate washes.** The sky fell from about 95% to 55–71%. This is the objective's third item, accepted knowingly.
- **Object-driven contamination survives both photographs** (P8). Panel 2 is the only per-print signal for it.
- **Edges.** On one photograph, false colour sits on edges and comes from lateral fringing made worse by 4:2:0 subsampling, not from the median. Opposite-sign fringing removes it in pairs.

**Kept from v1's single-photograph bench:**
- The TODO fallback showed 23% of a painted sky and 8% of a wash over every light grey; consensus showed 100% of both.
- The TODO with plane hid the sky under mixed light (3%) without a warning.

**Figures** (`/home/user/xpw/121087/work/img/`):
- `v2_P8_small.png`: the olive model;
- `v2_P5_small.png`: sky and lips only, the weak side hatched;
- `v2_N4_small.png`: untinted under mixed light, panel 4 quiet;
- `v2_P1_small.png`;
- `dbg_N4_pair.png`: where the survivors lay before the v2 unit: the paper border and the darkest band.

---

## 8. What this standpoint is likely to get wrong, and how to falsify this answer

### What this standpoint is likely to get wrong

1. **I adopted the red team's mechanism largely because it fixed my own weakness, on a simulator I wrote.** On real phones, two shots may share processing (scene detection, local tone curves, face and skin rendering) that no simulator of mine models. "Seen in both" may then pass the camera's own colour as paint.
2. **The history standpoint still over-weights the montage.** The red team showed that the picture rule never changed and that the same rule produced unusable VDZ outputs. "Familiar" is not "validated", and v2 still keeps three of the four panels on testimony alone.
3. **It reads intent from a record that assistants mostly wrote.** v1 over-read "drop the picking". v2 may now over-read the camera as cheap: a second photograph under different light *and* a different device is a real cost in a reading room.
4. **Brooks and Gall predict that v2 is itself a second system.** Pairing, registration, two models, a control rule and a mark path are more than v1 proposed. The order of work (single-photograph panels first, pairs only after the test captures) is the only defence, and it depends on discipline.
5. **The red team's statistical framing may be the better one.** This is detection with unknown error rates. A standpoint that prefers pictures to error rates may keep pictures the data would condemn.
6. **Abandonment may still be success.** The VDZ study may end, and the tool with it.

### How to falsify this answer

**Before code.** Ask the author which part of Chroma mode failed (method, picks or maps). Make the four test captures:
- a known-unpainted print of the VDZ kind;
- a print whose paint a conservator has marked under magnification and UV;
- each photographed twice, the second time under different light and with another device or the print moved.

**Test 1: agreement with the object.**
- Use at least 12 painted and at least 8 untinted VDZ prints, each photographed in pairs as above. Before anyone sees an output, a conservator records object by object (face, backdrop, clothing, jewellery…) whether it is painted.
- Viewers who know neither the print nor the method mark each object "paint", "no paint" or "can't tell" from the pictures of each of:
  - 4.1.2;
  - TODO.md as written;
  - a DStretch or eyedropper baseline;
  - v2 panels 1–3 alone;
  - v2 with "Seen in both";
  - v2 with marks.
- **v2 is falsified if any of these holds:**
  - its "Seen in both" lights any untinted print beyond specks in more than 1 pair in 10;
  - it shows conservator-marked moderate or strong paint no better than the DStretch baseline;
  - panels 1–3 alone do as well as panels 1–4, in which case the departure picture is not worth its machinery.

**Test 2: can viewers see a contaminated model?** This is the line-up protocol (Buja et al. 2009; Wickham et al. 2010).
- For each painted pair, make four montages; one uses a deliberately contaminated model (a mark on the wash, or a model borrowed from another print).
- Viewers pick the montage "wrong about the unpainted print".
- If they do no better than chance (one in four), panel 2's decision rule fails and should be dropped, not decorated.

**Test 3: use.**
- If, after a month, second photographs exist for fewer than half the prints and marks for fewer still, the default path is wrong. The tool then reduces to panels 1–3 and must be judged as such.
- If the control withholds more than one session in three, departure pictures are the wrong product for these prints.

**Already runnable:** `python3 pairs2.py` in `/home/user/xpw/121087/work/`. If "Seen in both" exceeds 1% on any N case, or P6's wash falls below 90%, the bench claims in section 7 are falsified.

---

## 9. Retracted

1. **An automatic presence map from one photograph** (v1's default). Retracted by the section 3 rule. It flooded under mixed light (38–52% in v1; 33–44% here) and lit the floor's complementary ghost (P1, 68%).
2. **"Faint signals shown bright"**, early-saturating opacity (smoothstep 2.5→5). Retracted for linear 2→6.
3. **The three sensitivity presets.** Retracted: they hide decisions, and one fixed rule scored on controls replaces them.
4. **The tone strip as a separate picture.** Folded into panel 2.
5. **`controls/` as a pooled reference shape**, and **the folder pick.** Retracted (section 5b).
6. **The band-spread unit.** Retracted for √(spread² + leave-tones-out error²). It was "precision against the wrong noise", the very fault v1 diagnosed in Woodii.
7. **"Measure the light on the paper border" as the fix for mixed light.** It kept the sky but left 38% false colour. Kept only as the gradient shown in panel 2.
8. **The warnings** "the two halves disagree" and "colour covers most of the … greys". They fired on genuinely painted prints. Replaced by panel 2's decision rule, the one-photograph statement and the control.
9. **The certainty of premortem story 1** ("the picker will go unused"). It rested on an agent's gloss; whether picking sank Chroma mode is unknown. The v2 rule no longer depends on it.
10. **"The montage is the working simple system."** Retracted to "the familiar simple system". Its rule was unchanged from v1.1 to 4.1.2 and produced the unusable VDZ outputs.
11. **The generality of "consensus does not assume a pixel majority".** It fails on a wash over the whole picture (P8); the record now says so.
12. **The implication that hue shows the paint's colour.** Hue is the direction of departure from the model (P8: a blue wash shown orange).
13. **v1's list of 4.1.2 leftovers**, corrected: it missed the JSON's LRC band data.

**Not retracted:**
- the archaeology of authorship (assistant-written records, the GUI lost without a decision, unparseable committed versions);
- the TODO fallback's absorption of washes that dominate some tones (P4, P6);
- the image-wide plane's silent loss of a sky;
- automatic print finding;
- the line-up test.

The red team's evidence either supports these or does not touch them.

---

## 10. Sources and files

**Primary records:**
- Visualiser commits `9f4420e`, `0949bdc`, `18fbd5a`, `f95e1f8`, `a365ea6`, `6176d62`, `4584a2f`.
- Woodii `5b1757d` (Chroma mode code); `de6f9b1` (removal; the "Open:" line); `66d03e7` (the author's 30 October answer); `docs/health-check-2026-10-29.md`; `docs/AUTHOR-POSITIONS.md` on `origin/main`.
- The red-team report, `/home/user/xpw/121087/peer-report.md`: their bench figures are cited as theirs.

**Literature:**
- Brooks (1975), ch. 5.
- Gall (1975).
- Lehman, *Proc. IEEE* 68(9), 1980.
- Klein, *HBR* 85(9), 2007.
- Mitchell, Russo and Pennington, *J. Behav. Decis. Making* 2(1), 1989.
- Gillespie, Kahle and Walker, *Remote Sens. Environ.* 20, 1986.
- Harman, DStretch.
- Land and McCann, *JOSA* 61(1), 1971.
- Fischler and Bolles, *CACM* 24(6), 1981.
- Buja et al., *Phil. Trans. R. Soc. A* 367, 2009.
- Wickham, Cook, Hofmann and Buja, *IEEE TVCG* 16(6), 2010.
- Apple's per-person skin-tone processing in Smart HDR 4, as reported by Trusted Reviews.
- Cited from the red team, not checked by me: Buchsbaum 1980; Barnard et al. 2002; Margulis 2005; Delbracio et al. 2021; Green and Swets 1966; Lavédrine 2009; Stulik and Kaplan 2013; Tiggemann et al. 2013.

**v2 files** (`/home/user/xpw/121087/work/`):
- `pairs.py`: two photographs, fringing, registration;
- `pairs2.py`: single against two photographs with the v2 unit, writing `pairs2_results.csv`;
- `v2.py`: unit and judgement rules;
- `proto_v2.py`: the 2 × 2 montage, writing `img/v2_*.png`;
- `edge_check.py`, `edge_check2.py`: the edge attribution;
- `dbg_pairs.py`, `img/dbg_N4_pair.png`;
- v1 files unchanged: `synth.py`, `methods.py` (now also exposing the fit's bands), `bench.py`, `hpv5_proto.py`.
