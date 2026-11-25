# The reviewers, point by point, against Odobenii

25 November 2026. `04-divergence.md` compared Odobenii with the review's merged answer, the synthesis. This note goes
back to the twelve reports and follows each reviewer's points to Odobenii as it stands on main (PR #6). It looks for
what the synthesis dropped or changed on the way, and for anything in Odobenii that a reviewer warned against or later
retracted. Where your answers and a reviewer conflict, your answers win.

Each report was read in full against the code, and every claim here about the code was checked in it. The one number
measured for this note (section 2, item 3) comes from a synthetic print. Reports are numbered as in `reports/`:
- [01] control;
- [02] conservation;
- [03] perception;
- [04] remote sensing;
- [05] camera pipeline;
- [06] history;
- [07] red team;
- [08] audit;
- [09] to [11] the merges;
- [12] the final red-team pass.

## In short

- **Most points reach Odobenii as the synthesis changed them, or were set aside by your decisions.** These covered:
  - controlled captures;
  - one photograph per print;
  - CIELAB;
  - the web app and the stretch;
  - judging by eye.

  Together they retire everything about phones, the second photograph, the session's control print, log-chromaticity
  and the montage.
- **Odobenii keeps two things the reviewers retracted, by your decisions:**
  - the departure picture drawn from one photograph's guess about itself ([09], its retraction 1; [07]: "no automatic
    presence map");
  - CIELAB ([10], its retraction 6).

  The gate supports the first: the unpainted print stayed quiet, and the picture was useful.
- **Three more survive in milder forms, with no decision behind them:**
  - a lone box is used with no other box to corroborate it, where [11] replaced [03]'s unchecked picks with
    corroborated anchors (its retraction 5; already `04-divergence.md` item 6);
  - a box can put the paper margin into the tone curve ([10], its retraction 10);
  - the edge term carries error that has nothing to do with edges ([10], its retraction 12).
- **What the reports add to `04-divergence.md`: nine points** (section 2). The three that matter most:
  1. the blotches may be the print's own colour, and one more photograph would tell;
  2. the strip promises more than the departure picture delivers, and more in the darks than in the lights;
  3. the edge term counts blotches as edges, so on a blotchy capture the departure picture goes blind along sharp
     edges.
- **Your answers to the divergence check were recorded correctly.** They follow the numbers of my chat message, which
  had eight items where the file has ten. `04-divergence.md` and `03-author-answers.md` now say so (section 3).

## 1. Report by report

**The statuses:**
- **Built:** as the reviewer asked.
- **Built, changed:** as a merge or the synthesis changed it.
- **You:** your decision, by its section in `03-author-answers.md`.
- **Moot:** it does not arise with controlled captures of one photograph.
- **Not built:** no decision behind it.
- **Risk:** it still applies.
- **Retracted:** by the reviewers themselves.

Items refer to section 2: numbers 1–9, letters a–i.

### [01] Control, the default answer

**Its answer:**
- the most common colour at each tone, joined by a stiff curve, with a tilt across the frame kept only if all tones
  agree;
- departures judged against the bare print's own scatter, widened at edges;
- four pictures, one of them "Taken as bare print";
- worded checks that say what to do.

**Against Odobenii:**
- **Built, changed:**
  - place votes and a P-spline, not the densest colour;
  - a fixed threshold raised by pixel noise and an edge term, not the print's scatter;
  - the edge term fitted per capture.
- **You:** CIELAB, not its lightness-normalised (a\*, b\*) × 116/(L\* + 16) (§5); no tilt (§5, §12).
- **Not built:**
  - the "Taken as bare print" picture: the map is computed but never drawn (item g);
  - worded checks;
  - automatic print finding (`04-divergence.md` item 4).
- **Risk:** it warned that pixel differences miss low-frequency mottle. In its prototype, a measure taken from pixels
  6 px apart let false colour in the shadows rise to 22–51 %, so it judged departures against the print's own scatter.
  That mottle is your blotches. Only T0 keeps them out of the departure picture, and the boost and the stretch have no
  threshold.
- **New:** its normalisation removes the 2.3 times dark-tone loss of `04-divergence.md` item 3, exactly (item 9).

### [02] Conservation

**Its answer:**
- the tone voted by places;
- departures scaled by the capture's own scatter (a 90th percentile);
- a standard drift of the light;
- two spatial scales;
- four pictures;
- picks as anchors that act only beyond the capture's scale, six or more.

**Against Odobenii:**
- **Built:**
  - the place votes, its mechanism and Odobenii's core;
  - toning, foxing and mirroring named as colour that is not paint.
- **Built, changed:**
  - a fixed threshold, not the 90th percentile ([11] showed that a tail quantile breaks down once a tenth of a tone is
    painted);
  - boxes always pull once they pass the cross-check, and nothing says how many to draw.
- **You:** no drift of the light (§5, §12); separate pictures, not a montage (§1).
- **Not built:**
  - the neighbourhood scale for broad washes (`TODO.md`, "Not now");
  - the premise printed on the picture: "at each tone, most places on the print are unpainted" (item 4).
- **Contradicted:** it found that "an opaque neutral white does show on a warm, yellowed print". The app says neutral
  media "never show" (item 6).
- **Risk:**
  - patchy toning, local yellowing and mat burn break a reference that depends on tone alone (item 1);
  - picks chosen by eye can sit on a thin wash;
  - its falsification set was 12 unpainted controls, 6 mock-ups and 10 Van Der Zee prints; the gate used two prints
    (item 7).

### [03] Perception

**Its answer:**
- a P-spline tone curve with a cast scaled by lightness;
- departures judged at three spatial scales;
- an uncored boost;
- departures drawn bright on dim, so colour-deficient viewers see them;
- a blink;
- words under each picture.

**Against Odobenii:**
- **Built:** the P-spline (Odobenii's curve is its idea); the uncored boost; bright on dim.
- **Built, changed:** a fixed T0 in place of its spreads; one scale.
- **Not built:**
  - lifting the boost's shadows, and Oklch hue (`04-divergence.md`, smaller);
  - words for the hatching under the pictures;
  - the blink. F cannot stand in for it, since every pair of pictures also changes the unpainted areas (item e).
- **Retracted, kept milder:** its picks weighted ×20 and never down-weighted were retracted in [11], for corroborated
  anchors. Odobenii's boxes weigh ×5, are cross-checked against one another, and are never down-weighted; a lone box is
  used with nothing to corroborate it (`04-divergence.md` item 6).
- **Risk:**
  - faint forms vanish on an uncalibrated laptop in a bright room (item f);
  - its falsifier was never asked of the boost or the stretch (item d): unpainted prints called "painted" more often
    than with the photograph alone.

### [04] Remote sensing

**Its answer:**
- log-chromaticity;
- the tone curve plus a light field, plus one constant per paper box;
- least trimmed squares, then biweight steps;
- T = max(T0, 3σ), with σ from pixels 12 px apart;
- a picture of the reference;
- a second capture as the decisive check.

**Against Odobenii:**
- **Built, changed:** its fit and its threshold are Odobenii's, fitted to votes, with noise taken 3 px apart and a ramp
  from T to 2T.
- **You:** CIELAB (§5); no light field (§5, §12); no second capture (§6).
- **Not built:**
  - **Two kinds of box.** It held that a paper margin or mount measures only the light: "Treating the margin as the
    image's highlight tone is wrong whenever the image highlights carry stain that the bare margin lacks." Odobenii
    has one kind of box, used wherever it is drawn, even outside the print area (item 5).
  - **Its estimator for the edge term**, which first takes out what calm places hold (item 3).
- **Risk:** glare and silver mirroring read as "blue paint in the shadows". The app names mirroring, but not sheen or
  glare (item b).
- **New:** "Paint stays with the print; light and glare do not." Its check, a second shot with the print turned, would
  tell what your blotches are (item 1).

### [05] Camera pipeline

**Its answer:**
- uneven light taken out by default;
- a staged fit;
- chroma compared at the camera's chroma resolution;
- picks as seeds;
- an "As if unpainted" picture and a tone strip.

**Against Odobenii:**
- **Retracted:** its staged yardstick, its plane fitted to patch votes, and its claim for "As if unpainted" ([10]).
  None of them is in Odobenii.
- **Built, changed:** the chroma-resolution comparison, as [10] set it for files from a raw converter (a 1 px blur).
- **Moot:** phone processing (§5).
- **Not built:** relative colorimetric intent. Neither Odobenii nor the batch tool passes an intent to LittleCMS, so
  Pillow applies perceptual. ProPhoto exports never take that path; other profiles built from lookup tables do
  (item a).
- **Risk:**
  - "A tint over the whole print cannot be told apart from tinted paper or coloured light, … and the README must say
    so." The app says a broad wash leaves a sign, but a wash over the whole print leaves none (item 6).
  - "Mismatched spotting will show" (item 6).
  - Sheen varies mostly along yellow–blue, the axis the yellow–blue emphasis doubles (item c).

### [06] History, and a premortem

**Its answer:**
- keep what worked;
- no per-image picking;
- no light plane;
- find the print's edge;
- a small window;
- real captures before features.

**Against Odobenii:**
- **Built:**
  - an automatic reference that asks nothing of you per image;
  - no light plane;
  - no numbers on the pictures;
  - a gate on real captures.
- **You:**
  - five pictures on keys, not the montage (§1);
  - the web app, not a Tk window (§9);
  - a setup check, not a control print in every batch (§6).
- **Not built:**
  - the curve anchored at the paper (the reviewers disagreed; item h);
  - finding the print's edge, or saying "whole frame used" when no area is drawn (item h);
  - the file name and the evidence on each picture (you kept the records as they are).
- **Risk:**
  - **Size.** It warned against a second system. Odobenii has about 2,000 lines of Python and 900 of page, about the
    size Chroma mode reached, with 48 combinations of stretch settings (item i).
  - **Tests built in the estimator's own model** (item 7).
- **Its falsification:** at least 12 painted and 8 untinted prints judged blind, a line-up, and a count of use. Only
  the line-up was run, and it passed.

### [07] Red team

**Its answer:** as posed, the request cannot rule out a misleading answer. What survives is a tool that says where to
look:
- marks drawn by the user;
- an explicit model;
- a unit that fails safe;
- no automatic presence map without marks;
- a second capture.

**Against Odobenii:**
- **Built:**
  - words for what cannot show;
  - the hue described as the direction of departure;
  - DStretch and a plain boost as baselines at the gate.
- **You:** departures drawn from one photograph with no marks (§5, §6), against its "no automatic presence map". Its
  label, "automatic: assumes most of the print is unpainted", is on no picture (item 4).
- **Built, changed:** marks optional and cross-checked by majority, with no check that they span the tones.
- **Not built:** hatching wherever the evidence does not reach. Tones where the reference is guessing are hatched in
  the expected-unpainted picture, but drawn at full strength in the departure picture (item 4).
- **Risk:** the real error in one capture is coherent, not pixel noise. That is the blotches (items 1 and 3).

### [08] Audit: the process, not the design

**Its findings:**
- the conclusion was in the material read before the survey;
- the test bed was the favoured side's;
- claims grew between documents;
- limits were disclosed unevenly.

**Against Odobenii:**
- **Answered by the gate:** real captures, judged by eye beside DStretch and a plain boost, with no segmentation
  score.
- **Recurs:**
  - the design was fixed before the evidence. All the code came before the gate, which passed the whole without
    testing which parts earn their place;
  - T0 = 2 ΔE was the default before the gate, and no other value is recorded as tried;
  - the tests, and the broad-wash claim in `TODO.md`, are the developer's own (item 7).

### [09] History, revised against the red team

**It adopted:**
- a second photograph ("seen in both");
- a session control;
- the line-up test;
- automatic print and border finding;
- a unit that leaves tones out.

**Against Odobenii:**
- **Retracted, kept by you:** its retraction 1, "an automatic presence map from one photograph" (§5, §6).
- **Retracted, not kept:** early-saturating opacity; the three presets.
- **Not built:**
  - the unit that leaves tones out. With no witness, nothing now covers the misfit it caught (item 4);
  - print finding (`04-divergence.md` item 4).
- **You:** the session control became the setup check, which is only in `TODO.md` (item 4).
- **Built:** the line-up, which passed.

### [10] Camera pipeline, revised against remote sensing

**It adopted:**
- [04]'s reference and fixed threshold, whole;
- the chroma-resolution comparison, kept;
- two kinds of anchor;
- paper anchoring offered as a flip.

**Against Odobenii:**
- **Built:** the fixed threshold; one fitted edge term (its retraction 5).
- **Retracted, kept by you:** "Stay in CIELAB" (its retraction 6), kept for calibration (§5). Calibration answers
  casts, not how a wash scales with tone (item 9).
- **Retracted, partly back:**
  - a model-error term in the floor (its retraction 12) returns at edges through the edge term (item 3);
  - the margin used as an unpainted pick (its retraction 10) is possible through a box (item 5).
- **Risk:** in its simulation of Woodii's own controlled, flat-fielded captures, 0.5 % sheen lit 9.5 % of the dark
  tones (item b).
- **Not built:** a flip between the reference with boxes and without them, which shows a wash absorbed into the
  reference.

### [11] Perception, revised against conservation

**It adopted:**
- votes of places;
- a median-based yardstick;
- the uncored boost;
- the expected-unpainted picture and the departure picture;
- the strip and the blank sentence.

**Against Odobenii:**
- **Built, changed:**
  - the strip, made from patches of the print since 25 Nov, closer to its "block bootstrap of this capture's own
    residual";
  - boxes cross-checked against one another, not against the automatic tone.
- **Not built as it specified:**
  - the strip's wash "scaled with (L\*+16)/116 as a transparent dye's is", and "drawn as B and as C would draw them"
    (item 2);
  - its full blank sentence, shortened to "Blank does not mean unpainted" (item 2).
- **Retracted, not kept:** "presence"; coring; the three panels; a separate reference strip.
- **Risk:** "A vivid C remains persuasive" even with the sentence under it; tone that varies from place to place.

### [12] The final red-team pass

`04-divergence.md` covered B1, B3, B4, B5 and B13. The others:

| Seam | Now |
|---|---|
| **B2:** boxes as a witness rebuild single-photograph maps | Moot. Every departure picture is single-photograph, by your decision. |
| **B6:** the blank sentence and the strip describe a threshold the departure picture does not use | Still true (item 2). |
| **B7:** the expected-unpainted picture cannot tell a cool wash on a warm print from split toning | Your §6: it is read alone, and the line-up passed. |
| **B8–B11** | Answered by the gate's criteria, the ramp, your §3 and version 4.1.3. `Chroma Diagnostic Tool v3.0` is still in the tree, as `TODO.md` housekeeping says. |
| **B12:** "Van Der Zee washes ≈ 1 ΔE" is a bench parameter | The app still states "about 1.3 ΔE for a faint wash" as a fact (item a). |
| **B14:** the control tests the capture, not the reference | The setup check is only in `TODO.md` (item 4). |

**What B1 adds:**
- a faint wash taken into the reference leaves a ghost fainter than T0, so the departure picture cannot show it;
- the marked print is not recorded as having a broad wash, so criterion 4 may not have been tested (item 7).

## 2. What the reports add to `04-divergence.md`

Numbered for your answers, most important first.

1. **What the blotches are: one test.** ([04], [02], [11])
   - The app calls them low-frequency noise in the capture. [02] and [11] name patchy toning, local yellowing and mat
     burn as what breaks a reference that depends on tone alone. Those are the print's own colour, and a faint wash
     looks the same.
   - [04]'s rule tells them apart: "Paint stays with the print; light and glare do not." Photograph the setup-check
     print twice, turned 180° between the shots, and flip between the two:
     - **Blotches that stay put in the frame** come from the capture: the lens, the light or the sensor. A flat field,
       as Woodii uses, would remove them.
     - **Blotches that change from shot to shot** are noise.
     - **Blotches that turn with the print** belong to the print. Then the known issue should say so, and on a painted
       print they could be faint washes.
   - **Proposal:** this test, at the next setup check. No code.
2. **The strip promises more than the departure picture delivers, and more in the darks.** ([12] B6; [11])
   - **The wrong picture.** The hint says the strip is "drawn as the picture you are looking at draws". With the
     departure picture on screen (or the expected-unpainted one), it is drawn as the boost. At T0 = 2 ΔE the
     departure picture never draws the strip's 1.3 ΔE wash at all. So "Where you cannot see the wash here, a wash that
     thin would not show in the picture either" invites the converse reading, which is false there.
   - **The darks.** The wash is 1.3 ΔE at every tone. [11] scaled it as a transparent dye's: the same dye gives about
     half that at L\* 35 and a third at L\* 15. So the dark columns flatter.
   - **Proposal:**
     - with the departure picture shown, draw the strip through its own threshold: the wash will vanish and the touch
       will show;
     - scale the wash by (L\* + 16)/96;
     - restore [11]'s full sentence: "Blank in C means no colour departs from the print's own tone here, in this
       capture, by more than this capture's own error. It does not mean unpainted: thin washes (see the strip),
       colourless or tone-matched media, and anything hatched cannot show."
3. **The edge term counts blotches as edges.** ([04]'s estimator; [10], its retraction 12)
   - **How it is fitted.** The edge term is what is left of the departures after pixel noise, divided by the squared
     lightness gradient. Blotches have nothing to do with edges, but they sit in what is left. [04]'s code first took
     out what calm places hold.
   - **Measured on a synthetic print:**
     - blotches of only 0.15 ΔE per axis raised the edge term from 0.06 to its cap of 0.5;
     - at the sharpest 5 % of pixels, the threshold's 90th percentile went from 6.5 to 19 ΔE.
   - **The effect.** On a blotchy capture, the departure picture goes blind along sharp edges: lips, eyes, jewellery,
     the edge of a sleeve.
   - **Proposal:** take out the calm places' excess before dividing, as [04] did. Small, and testable on your captures.
4. **The safeguards for a departure picture from one photograph.** ([07], [09], [12] B14) Your decision (§5, §6)
   keeps a picture the reviewers would draw only with a second photograph. Most of what they put in its place is
   missing:
   - **The setup check is only in `TODO.md`.** Neither the README nor the app tells you to photograph the
     known-unpainted print when the camera, lights or profile change, or to distrust departure pictures if it shows
     colour.
   - **Guessed tones are judged at full strength.** Tones where the reference is guessing are hatched in the
     expected-unpainted picture, but drawn as usual in the departure picture.
   - **No picture states its premise**, "at each tone, most places on the print are unpainted" ([02], [07]).

   **Proposal:**
   - a line on the setup check in the README and the Check tab;
   - the expected-unpainted picture's guess stripes over the departure picture as well. Stripes, not blanking, so a
     wash the curve rejected still shows;
   - the premise in the departure picture's words.
5. **A box on the margin or the mount pulls the reference.** ([04]; [10], its retraction 10; [12] B4)
   - **Why it happens.** The margin is unpainted, so it is a natural place for a box. But bare paper is not the image's
     highlight tone wherever the image carries stain or toning that the margin lacks, and a mount is another material.
   - **What Odobenii does.** It uses a box wherever it is drawn, even outside the print area, at five times a place's
     weight. Two boxes on the margin agree with each other, so they pass the cross-check.
   - **A correction.** `04-divergence.md` said the print area "keeps the rest out of the fit". That is true of the
     places' votes, not of boxes (corrected there).
   - **Proposal:** a box outside the print area becomes a "check" box, as already proposed in `TODO.md`: kept out of
     the fit, judged, and named if it shows colour. The hint would ask for boxes on the image, not on the margin or
     the mount.
6. **Three sentences in the app say more than is true.**
   - **"Neutral or tone-matched media never show: graphite, grey retouching, black spotting, white gouache, varnish."**
     [02] found that "an opaque neutral white does show on a warm, yellowed print", and [05] that "mismatched
     spotting will show". Neutral media show as a shift towards grey wherever the print's tone is not neutral, and
     that can read as a cool wash.
   - **"A broad wash over most of the print at some tone can enter the reference. Its sign: …"** A wash over the whole
     print leaves no sign at all: it becomes the print's tone ([05]: "the README must say so").
   - **"Measured noise can only raise it, never the paint"** (in Settings; similar words in the README and the
     engine's notes). The edge term rises at paint's own edges ([12] B5), and, with item 3, wherever there are
     blotches.
   - **Proposal:** reword all three.
7. **The evidence is two prints.** ([06], [09], [02], [04], [05], [10]; [12] B1)
   - **The reviewers' sets.** They asked for 6 to 12 unpainted prints (warm, toned, yellowed, mirrored and glossy among
     them) and as many painted ones. The synthesis said the gate would be "extended later to the larger sets".
     `TODO.md` does not schedule that.
   - **Criterion 4 (no ghost)** asks for a print with a broad wash. The marked print is recorded with faint washes and
     some moderate or strong paint, not a broad wash. Did it have one? If not, criterion 4 has not been tried on a
     real capture.
   - **Tests in the method's own model.** The tests in `tests/`, and the broad-wash sentence in `TODO.md`, are the
     developer's own, built on the method's own model of a print ([01], [08]).
   - **Proposal:**
     - a few known-unpainted prints of different kinds at the next setup check, judged by eye with the same criteria;
     - your word on criterion 4.
8. **Small boxes switch off the boxes' other jobs.** ([02], [07])
   - Once a box is used, the boxes alone give the edge term and the stretch's statistics.
   - Under about 500 analysis pixels in all (a box of about 45 × 45 px on a 6000 px capture), the edge term is set to
     zero.
   - Under 100, the statistics fall back to every pixel in the frame, even outside the print area, while guard 2 still
     shows as on.
   - **Proposal:** pool the boxes with the inlier places, or ask for a minimum size.
9. **A cheaper route for the dark tones.** ([01]; `04-divergence.md` item 3, your "hm")
   - [01]'s normalisation is exactly the factor item 3 found: (a\*, b\*) × 116/(L\* + 16) is 2.52 at L\* 30 and 1.09
     at L\* 90, a ratio of 2.3.
   - Dividing the departures by (L\* + 16)/116 before the threshold would make the departure picture as sensitive to a
     transparent wash over the darks as over the lights, within CIELAB. The cost: it raises the darks' noise by the
     same factor.
   - **Proposal:** try it beside the density option, on your marked print.

**Smaller:**
- **a. Small corrections.**
  - Pass relative colorimetric intent to LittleCMS, in Odobenii and in the batch tool.
  - Retire three stale labels:
    - the stretch's "untested" badge;
    - "tested so far only on synthetic prints" in the engine's notes;
    - "about 1.3 ΔE for a faint wash", stated as a fact, though it is an assumption ([12] B12).
- **b. Sheen, glare and mirroring.** They show as soft, usually cool colour that follows the surface in dense or glossy
  areas ([04], [05], [10]). One line in "What the pictures cannot show". [05] set cross-polarisation aside because
  handheld phones cannot do it; a copy stand can.
- **c. The yellow–blue emphasis.** Its tooltip, "yellows; blues, skies", could add "and the print's own yellowing,
  staining and sheen" ([05], [10]).
- **d. Colour-deficient viewers.** The boost and the stretch show departures by hue alone. The to-do could cover them
  as well as the departure picture ([03], [11]).
- **e. A "photograph ×4" view** would give the blink of [03] and [11] with F: flipped against the expected-unpainted
  picture, only paint changes.
- **f. Viewing.** One line: judge faint forms on a calibrated screen in a dim room ([03], [11]).
- **g. "Taken as unpainted."** The places the reference used are computed but never shown ([01]). That map would show
  a wash absorbed into the reference, whatever its hue.
- **h. The print area and the paper.**
  - With no print area drawn, the whole frame votes, in batch runs too, and nothing says so ([06]).
  - Anchoring at the paper was parked as "Not now" while the reviewers disagreed: [06] and [09] for it, [07] and [10]
    against.
- **i. Size.** Odobenii has 48 combinations of stretch settings, and needs a terminal to start ([06], [09]). Once you
  have chosen which spaces stay:
  - the guard switches could move to a developer mode;
  - a double-click launcher would let others run it.

## 3. Corrections to the earlier notes

- **Your answers to the divergence check.** They follow the numbers of my chat message of 25 Nov, which had eight
  items:
  - its item 4 joined the border and the edge term, items 4 and 5 of `04-divergence.md`;
  - its item 8 joined the two dropped checks, items 9 and 10.

  So "6 is okay, as is 7" means T0 and the records, as recorded, and the lone box (its item 5) is unanswered. Both
  files now say which list the numbers come from.
- **`04-divergence.md`, item 4:** the print area keeps the rest out of the places' votes, but boxes outside it still
  join the fit (item 5).
- **`04-divergence.md`, section 2:** the expected-unpainted picture plus the boost equals the capture ×4 only at the
  default strength, 4.

## Your answers (25 Nov)

> "1) i think that ps perhaps not feasible. this is a visualisation tol that can be used for aready captured images. the
> viewer has to visually inspect the photograph before making any calls on presence or lack thereof.
> 2) the strip can perhaps go, as it hints towards quantifiable, when nothing is actually quantifiable. assuming we have
> the colour accuracy for a de1.3 measurement is false.
> 3) what is the reccomendations for a fix.
> 4) perhaps when colour departs is better left our?
> 5) perhaps we should specify 2 or more boxes in areas that are dosconnected?
> 7) can be adressed?
> 8) true
> 9) hm. fair."

- **1, the blotches:** the test is not feasible. Odobenii works on photographs already taken, and the viewer inspects
  the photograph before any call. The known issue now says the patches may come from the capture or from the print
  itself, and that no picture can tell them apart.
- **2, the strip:** removed, with the "about 1.3 ΔE for a faint wash" the page gave. It suggested a measurement, and
  the colour accuracy it assumed is not there.
- **3, the fix for the edge term:** it depends on 4.
  - If "Where colour departs" goes, nothing needs fixing: the edge term only sets that picture's threshold.
  - If it stays, fit the edge term as the slope of the leftover colour against the squared gradient, so blotches,
    which do not grow with the gradient, fall into the intercept. About ten lines.
  - Tried on the synthetic print with faint lens-like fringes added: the current fit went from 0.18 to its cap of 0.5
    once blotches of 0.3 ΔE per axis were added, while the slope stayed at 0.09 (0.10 without them). Without fringes
    the slope finds no edge term, with or without blotches.
- **4, leave "Where colour departs" out?** Recommended: yes, for your own reasons in 1 and 2.
  - It is the one picture that makes a call: a fixed cut-off, T0 = 2 ΔE, decides what is drawn and what is left
    blank. In 1 you put that call with the viewer, and in 2 you set aside the ΔE accuracy it rests on.
  - On photographs already taken, nothing can give it the checks the reviewers required: no second photograph, no
    setup check.
  - Its faults would all need work: it goes blind along sharp edges on blotchy captures (3), judges the tones where
    the reference is guessing at full strength (4), is weaker over the darks (9), and draws a broad wash's ghost
    brightly.
  - Leaving it out also removes T0, the noise model and the edge term, and with them the ΔE figure left in Settings.
  - What it costs: you found it useful at the gate, and it is the one picture that does not rely on hue, for
    colour-deficient viewers. The boost and the stretch would carry everything, and the colour-deficiency to-do would
    move to them. The gate's criteria would then be read on the boost and the stretch.
  - Your call. Nothing is removed yet.
- **5, boxes:** done as you suggest. A box is used only where a box in another part of the print (at least a tenth of
  the print's shorter side away) covers the same tones and agrees with it, and only at those tones. That also settles
  the lone box. On its own, the rule would not stop two boxes on the margin from agreeing with each other, so boxes
  outside the print area are not used either. The hint asks for boxes on the image, not on the margin or the mount.
- **6:** not answered. Its three sentences were wrong whatever you decide, so they are corrected in the app and the
  README.
- **7, more evidence:** yes, without new photography. It can come from photographs already taken: prints known from
  the collection's records or past examination to be unpainted, of several kinds (warm, toned, yellowed, mirrored,
  glossy), and a painted print with a broad wash for criterion 4, run as a batch and judged by eye with the gate's
  criteria. I cannot supply them; `TODO.md` lists it.
- **8, small boxes:** done. A box too small to judge is not used ("draw it larger"), so the boxes always hold enough
  pixels for the edge term and the stretch's statistics. Those statistics never fall back to pixels outside the print
  area.
- **9, the dark tones:** fair, and it waits on 4.

