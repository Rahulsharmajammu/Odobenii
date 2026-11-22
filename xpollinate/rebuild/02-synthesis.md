# Synthesis

22 November 2026. Produced from:
- a pre-committed answer;
- eight independent agents (a control, five stances, a red team and an audit of the coordinator's own prior work);
- three cross-pollination rounds.

Raw reports are in `reports/`. The pre-commit is `00-precommit.md`; section 6 diffs against it.

**How ideas are attributed.** Each load-bearing idea carries the report it came from:
- [01] control;
- [02] conservation;
- [03] perception;
- [04] remote sensing;
- [05] camera pipeline;
- [06] history;
- [07] red team;
- [08] audit;
- [09] merge history × red team;
- [10] merge camera × remote sensing;
- [11] merge perception × conservation.

Ideas found only in this file are marked **[coordinator]**.

## 1. Method

**The request.** Analyse the visualiser's earlier iterations, Woodii's removed Chroma mode and the plan in TODO.md, and find the best design. The user's constraints:
- show the presence, or lack thereof, of paint on monochrome photographs;
- not colorimetric;
- nothing that invites a quantitative reading;
- "unruly" captures;
- no luminescence.

**The hard question** (put identically to every agent): *For each uncontrolled capture, how should the tool establish what the unpainted photograph looks like, and how would someone looking at its output know when that has gone wrong?*

**The pre-commit.** It was written before any agent launched and kept in the coordinator's scratchpad, outside every path the agents were given. No report mentions it.

**The agents.** All eight ran on the coordinator's model (Opus 5.5), as general-purpose agents in separate directories:
- the control got the user's messages verbatim;
- the stances got the same plus a named standpoint and anchor ideas;
- the red team was asked to argue the request is ill-posed first;
- the audit got the coordinator's two replies, the synthetic test and TODO.md.

**What was given to the agents, and what was withheld.**
- **The user's messages.** The opening of the third ("Hm. Please use xpollinate from <url>") was removed and the removal marked, so the agents would not run this protocol themselves.
- **The materials, identical for all:**
  - both repositories, read-only;
  - pointers to Chroma mode and its removal;
  - Woodii's AUTHOR-POSITIONS.md, flagged as written for Woodii;
  - "no real captures exist here".
- **Withheld:** the coordinator's replies (except from the audit), the pre-commit, and each other's reports.

**How reports were saved.** The harness refused report files from subagents. Each agent returned its report as text, and the coordinator saved it verbatim.

**Cross-pollination.**
- Three merges, each resuming one original agent with SendMessage so it had to defend or retract its own work:
  - [09] history v2, against the red team;
  - [10] camera v2, against remote sensing;
  - [11] perception v2, against conservation.
- A five-hour API rate limit stopped all three at their first step (06:56 UTC). They resumed with their contexts intact at 13:01 UTC.

**The final red-team pass** is section 8.

**The evidence base, and its limits.**
- **No real capture of any print was available.** Every number in this file comes from a synthetic bench.
- **There are seven different benches**, written by the agents, with different prints, phone models and ground truths. All come from one model family, so they share its beliefs about prints and phones.
- **Each method looked best on its own bench, and the rankings moved when benches were swapped** [10 §5]. Read every number as a test of logic and code, not of the method on real prints.

**Events during the run.**
- One agent imported the visualiser script by path, which left an untracked `__pycache__` in the repository. The coordinator removed it and committed a `.gitignore` (74db2bb); two agents noticed the commit.
- Woodii's checkout was not changed.

## 2. Convergence, discounted for the control

An idea counts as **convergence** only where stance agents reached it and the control did not. Where the control reached it too, it is a **model prior**: what this model says by default, whoever asks.

### Convergence beyond the control

1. **A second photograph, with the light or position changed, separates the print from the capture.** Paint repeats; light, glare and fringes do not.
   - Proposed by [07], [02], [04], [05] and [03].
   - Replicated by [09] on a different simulator: untinted prints went from 1–44% shown to 0.0–0.4%, against the red team's 0.1%.
   - Not in the control.
2. **Phones render faces and skies semantically**, putting colour where colourists worked, and no smooth reference removes it.
   - Raised by [05], [04], [06], [02], [03] and [07]; not in the control.
   - The remedy is on the capture side: RAW, Pro mode or a scanner, plus a control print shot the same way.
   - **[Amended after the final red-team pass, 12 C.9]** This is agreement on a hypothesis, not evidence. The sources are vendor and press descriptions, and no agent photographed a print with a phone.
3. **DStretch (decorrelation stretch) is the closest surviving precedent** and the simplest serious rival. So is "eyedropper white balance plus steeper Lab curves" [07].
   - Raised by [07], [06], [05], [02] and [04]; not in the control.
   - Any rebuild must beat them on real captures.
4. **4.1.2 is unfinished.** It still has:
   - the threshold on every montage footer and on the console;
   - thresholds in `run_log.csv`;
   - LRC band statistics in the JSON;
   - the README's "actual pigment", "Tier 1 (Solid): Opaque, unmodified pigment" and "faint residue and solid paint".

   Found by [08], [07], [06], [02] and [09]; not in the control. **Verified** in the files.
5. **Edges are the largest source of false colour for TODO as written, and comparing at the camera's chroma resolution reduces it.**
   - Proposed by [05], [03], [07] and [04]. The control used a fringe term instead.
   - [10] measured a 10–50% relative reduction on all 14 scenes of two benches.
   - The cause is disputed. [07] blamed smoothing a\*b\* but not L\*; [09] did not reproduce that, finding fringing made worse by 4:2:0 instead.
   - **[Amended, 12 A]** The red team has since withdrawn its cause. The fix rests on [10]'s measurements alone.

### Model priors

The control said these too. They may be right, but agreement on them is not evidence:
- **The reference for "unpainted" is the crux.** This was also induced by the hard question.
- **Drop C\*ab and LRC; use the 2-D departure vector.** Inherited from TODO.md, but demonstrated on six benches: a blue wash over a warm print *lowers* C\*. LRC scored AUC 0.29–0.40 on warm prints.
- **The reference is automatic by default.** **[Amended, B10]** This is the coordinator's choice, pending the author. The user's record does not settle it (see the two readings below).
- **The yardstick is never sensor noise.**
- **Uneven light is modelled now, not later.**
- **A fourth picture shows the tool's own reference.** Every designing report has one; the pre-commit did not.
- **Find the print, or take an object box.**
- **"Blank" never means "unpainted".**
- **Real captures come first.**

### A model prior, replicated as an experiment

**Woodii's Chroma mode lights up unpainted prints whose tone shifts with density.** Four agents ran its code on separately written simulators:

| Agent | Unpainted print flagged |
|---|---|
| [01] | 27–58% |
| [05] | 44–50% |
| [02] | 56–62% |
| [10] (L2, L5) | 44.5–50.1% |

[03] reached the same conclusion from the code. The cause is a yardstick of sensor noise in small picks, and a straight silver axis.

This is the strongest mechanical explanation of the "bust". It sits alongside the user's own recorded complaint: the results were "not very user friendly", while the old visualiser's pictures "were helpful" (Woodii 66d03e7). It remains a hypothesis about what happened to the real print.

### The user's own positions (not agent evidence)

- **The sentence of 30 Oct** (Woodii 66d03e7): "the results were not very user friendly, and while the chroma viewer might be inaccurate it allowed for useful visualisations, which were helpful". **[Amended, B10]** It has two readings:
  1. "The chroma viewer" is Chroma mode: good pictures, an unfriendly workflow. This is the commit's own gloss, followed by an assistant's "keep the pictures and drop the picking".
  2. "The chroma viewer" is this GitHub visualiser. The author's note of the same day supports this: "here, I refer to the Chroma visualier in github" (Woodii ebed85e).

  Neither reading says the picks were what failed, as [06] and [09] point out.
- "If it is not easy, nobody will do it";
- "The app makes images; the user interprets them".

## 3. Where reports broke the pre-commit

| Pre-commit claim | What broke it |
|---|---|
| Picks per image as the override, in a sidecar; a folder-wide default allowed | **[08] §7, [06] §2.1.** The user's recorded reason for dropping Chroma mode: unfriendly results. **[Amended, B10]** Whether the picks were the cause is not recorded. The pre-commit's own "what would change my mind" named this case. **[01], [03], [02]:** a folder box lands on different content in the next, differently framed capture |
| "Woodii got the reference right (picked untinted areas)" | **[01], [05], [02], [03].** Its straight axis and sensor-noise yardstick flag 27–62% of unpainted prints, even with ideal picks on its intended raw input |
| Automatic reference: trim and refit band medians, three to five rounds | **[07], [03]:** the spread shrinks each round (20–30% false colour as written). **[06]:** band medians absorb a wash that dominates a tone (sky 23%). **[08]:** a no-pick refit showed 56% of a pink wash and 4.7% of a sky. **[10]:** band medians break at 49% of one band |
| Light smoothing of a\*b\* only | **[07]:** false colour at toned-print edges. **[09]:** did not reproduce the cause, but the fix survives as comparison at the camera's chroma resolution **[10]** |
| An optional tilt, off by default, additive in a\*b\* | **[05], [03], [01], [02], [10]:** needed by default. **[03]:** in CIELAB it must scale with lightness. **[06]:** an unguarded plane hid a painted sky silently |
| Presence opacity from 2.5 to 5 robust spreads | **[04], [10]:** a spread fitted to the same pixels lets a large wash inflate its own yardstick (a backdrop shown 0–15%; 0% in [05]'s v1 on [04]'s bench) |
| A presence map drawn from every capture | **[07], [09]:** one photograph judged by its own guess showed 1–44% false colour across benches. Only a witness brought it to 0.0–0.4% |
| "Faint signals shown bright": early-saturating opacity | **[07], [09], [11].** [11], via [02]'s bench: with thin washes of about 1 ΔE, the map cannot show them. **[Amended, B12]** That strength is a bench assumption, not a measurement of Van Der Zee prints. Also, and saturating early makes weak and strong evidence look alike. Faint washes belong in the uncored boost [11] |
| Three panels | **Every designer** adds the tool's own reference as a fourth; **[10], [11]** show it must be exaggerated (×4) to reveal contamination |
| Warnings like "much of the frame departs; the reference may be wrong" will reveal failure | **[06], [03], [11]:** such statistics cannot tell a genuine whole-tone wash from a wrong reference. The pictures and a control must carry the check |
| Sensitivity presets | **[07], [09]:** they keep the decision and hide it. **[10], [11]** kept them. Resolved in section 5 |
| Validation as item 11 of 11 | **[06]** (Gall's law), **[07]**, **[08]**: a gate before code, as Woodii's own health check had said |
| CIELAB (least sure) | Answered: compute departures in log-chromaticity under a fixed threshold [10]; display in Oklab or CIELAB [11] |

**What survived:**
- the reframe: show departures from the print's own tone, and be honest about where the tool cannot see;
- the vector feature;
- the print's tone drawn as neutral grey in the boost;
- hatching for what cannot be judged;
- no numbers;
- one small module;
- loading and working size;
- "colourless and tone-matched media cannot show".

## 4. The merged answer

### 4.1 What the tool promises

> **For each print, it shows the photograph's colour boosted around the print's own monochrome tone, and the tone it assumed. Where a witness supports it, it also shows where colour departs from that tone in both of two different photographs. These are places to look at on the object. They may be paint, retouching, staining, foxing, toning or mirroring. A place with no departure is not shown to be unpainted.**

Sources:
- [07] Part 2: the "where to look" claim;
- [11] and [02]: "departs from the print's own tone" and the blank sentence;
- [09]: witness-gated departures.

**It never:**
- claims absence;
- names a material;
- gives an area or a number;
- hides its assumption.

### 4.2 Inputs, and the one thing asked of the photographer

**Minimum:** one photograph per print. That always gives three pictures (4.4: A, D and B).

**Recommended,** to unlock the departure picture C [09], [07]:
- **A second photograph that differs deliberately:**
  - in light: window against lamp, or another direction;
  - **and** in device or lens, or with the print elsewhere in the frame.
- **One known-unpainted print of the same kind**, photographed in the same session the same way. It is the session's negative control.

**Advice, never required** [02], [03], [05], [04]:
- keep the paper border in frame and unclipped;
- use one light if possible;
- where faces matter, use RAW, Pro mode or a scanner, because phones render faces.

### 4.3 Pipeline

1. **Load** [all; detail from 10, 02, 09]:
   - Pillow; EXIF orientation;
   - any ICC profile to sRGB through LittleCMS, relative colorimetric;
   - untagged files taken as sRGB;
   - HEIC if pillow-heif is present;
   - read EXIF make, model, lens and software (for the same-camera warning and the phone note).
2. **Working size:** about 2,400–3,000 px on the long edge, area-averaged [all].
3. **Find the print** [06], [01]: the largest bright, smooth region forming a ring, filled. It is outlined on the photograph. If it fails, the tool uses the whole frame and says so.
4. **Not judged, and hatched** [all; detail from 03, 10]:
   - any channel clipped (≥ 250, grown 3 px);
   - near-white on a local mean;
   - near-black (L\* below about 8–12);
   - outside the print.

   **[Amended, B4]** The paper border is a negative control [10]:
   - it is kept out of the fit;
   - it is judged like the print, outlined, and drawn in B and C;
   - colour on it raises warning 4.

   It tests only paper tones. If paper anchoring is switched on, the border enters the fit and the montage says it is no longer a control.
5. **Features** [10]:
   - linearise sRGB;
   - χ = the 2-D log-chromaticity of linear RGB, with a 5 px median;
   - tone L\*, and G = |∇ ln Y|.

   In χ a colour cast and a transparent wash are the same additive shift at every tone. Under a fixed threshold that mattered: CIELAB lost a backdrop (1% against 83%) and painted a mixed-light print (21% against 2.6%) [10 §3].
6. **The reference: what this print looks like unpainted in this photograph.**
   - **Model:** χ_ref = f(L\*) + g(x, y). f is a stiff smooth curve in tone; g is a quadratic light field [10], [04].
   - **Observations are place votes** [11], [02]. Each tile of a 10 × 10 grid gives one vote per 2 L\* band: the median χ, L\*, x and y. Paint, stains and silvering are local, so they cannot outvote a tone that is everywhere. Votes took a majority-painted backdrop from AUC 0.66 to 0.83, and its false colour from 14.6% to 0.7%, with no boxes [11 §3].
   - **Fit:** a least-trimmed-squares start, then Tukey-biweight steps at that fixed scale, never below the median-based scale. Breakdown is then over the whole picture, not one tone band [10], [04].
   - **[coordinator]** Fitting [10]'s LTS → MM model to [11]'s place votes, rather than to pixels, is a combination neither merge tested. Check it on both benches before real captures. If it does worse, fall back to [10]'s fit on pixels.
   - **Boxes are an optional remedy, never required:**
     - unpainted areas the user has **examined on the object** [02], [11];
     - used as **corroborated anchors**: a box that disagrees with the others beyond the capture's scatter is dropped and outlined, and a correction smaller than the scatter stands only where boxes at two or more places agree [11 §3].
   - **Paper-margin anchoring is off by default.** It helped on one bench and hurt on another [10 §2]. **[Amended, B8]** Gate criterion (v) in section 4.10 decides.
   - No folder-wide boxes, except on a fixed copy stand [02].
   - **[Amended, B4]** Votes come from inside the print only, never from the border.
   - **[Amended, B2]** Boxes correct the reference used by D, B and the two-photograph route. They are not a witness for C.
7. **Threshold** [10]: T = max(T0, 3σ). σ² is pixel-scale noise from differences of pixels 12 px apart, by tone, plus one edge term κ²G². No term of T is a spread of the departures.
   - **[Amended, B5]** κ² is fitted on the session control's capture (same camera and light, no paint), or failing that on the border ring. Fitted on the judged print, paint raised κ² from 0.19 to 0.33 on [12]'s bench.
   - Paint that makes its own luminance edges still raises G, and so T, there.
   - Compare at the camera's chroma resolution: blur both χ and χ_ref by 2 px for 4:2:0 or HEIC (1 px for 4:4:4 or raw) [10].
   - T0 is one developer constant, set from negative controls; there are no user presets (section 5).
8. **Departure:** v = blur(χ) − blur(χ_ref). Its direction gives hue, read as "direction of departure from the model", never as the paint's colour [09], [11].
9. **Seen in both** [09], [07]:
   - register photograph 2 to photograph 1 by SIFT plus a RANSAC homography;
   - a departure counts where both photographs exceed T and their directions lie within 60°;
   - departures in one photograph only are hatched;
   - **[Amended, B2]** the second photograph is the only witness. One photograph plus five examined boxes drew C over 26.1% of an unpainted print under the fixed threshold [12].

### 4.4 Pictures: a 2 × 2 montage, a strip and words

Layout from [11]: **[A | C] above [D | B]**, so D and B side by side add up to the capture ×4.

| Panel | What it shows | Always? | Source |
|---|---|---|---|
| **A** the photograph | The photograph, with the print's edge, the paper border (negative control) and any boxes outlined | yes | [09], [10] |
| **D** the print as expected unpainted, colour ×4 | The print's own lightness, with the reference's colour exaggerated ×4 (Oklch, constant lightness and hue). Hatched where the reference is guessing: tones with no support | yes | [11], [09], [10] |
| **B** departures ×4 | The print's lightness, with shadows lifted slightly; departures ×4, linear and **uncored**; Oklch gamut mapping. This is the "chroma boost around neutral", with the print's own tone as neutral, and where thin washes show as forms. **[Amended, B13]** B is the display-space difference between the capture and the reference rendered into that space, so D + B = the capture ×4 holds. B and C therefore use different measures and can disagree tone by tone | yes | [11], [10] |
| **C** where colour departs from the print's own tone | The print dimmed to grey. Departures drawn **bright** (Oklab L 0.80) in their direction's hue, so viewers with red–green deficiency see them too. **[Amended, B9]** Opacity is linear from 0 at T to 1 at 2T, so a drawn departure has no hard edge. Hatched where not judged or seen in one photograph only | **[Amended, B2] only with a second photograph that agrees**; boxes no longer count. Otherwise the panel states why and how to unlock it | [11], [10], [09] |

**The strip under D** [11]. Along one axis, from paper to shadow:
- the expected colour ×4, and the tone itself;
- **[Amended, B6, B12]** a thin wash and a small clear touch, set into this capture's own residual at that tone, as B would draw them:
  - the wash is about 1.3 ΔE, an assumed strength to be measured on the conservator-marked print;
  - a row showing how C would draw them appears only when a second photograph exists, and is drawn from both;
- hatching where the capture lacks clean surface at a tone.

It shows how sensitive *this* capture is at each tone, before anyone reads a blank.

**Words** [11], [09], [10]:
- **Always:**
  - the file name;
  - "Visualisation only – not a measurement";
  - the evidence used: "automatic, votes of places" / "with N examined boxes" / "seen in both photographs";
  - **[Amended, B6]** the blank sentence: "Blank means no colour departs from the print's own tone here, in this capture, by more than its pixel noise or a fixed minimum. It does not mean unpainted: thin washes (see the strip), colourless or tone-matched media, and anything hatched cannot show. Errors in the tool's model show as colour: compare D."
- **At most two warnings, in this order:**
  1. the session control shows colour (C withheld for the session);
  2. **[Amended, B2]** one photograph (no C);
  3. both photographs from the same camera (fringes and face or sky processing may survive);
  4. the paper border shows colour (the reference is wrong at those tones);
  5. no paper border found.

**[Amended, B1] Failure signatures in the README.** The README carries [10]'s table of failure signatures, restored. It includes the **complementary ghost**: when a broad wash has entered the reference, unpainted areas can show in C in the complementary colour, in both photographs, following one tonal band.

**Optional output:** a blink file, D ↔ the capture ×4, 700 ms each with no blank between; only departures flash [03], [11].

### 4.5 The session control

A known-unpainted print of the same kind, photographed the same way in the same session, goes in `controls/`. It is processed first by the same rules, and its montage is always written [09].
- **If its C shows colour beyond specks**, C is withheld for the whole session and every montage says why. The specks constant starts at 0.5% of the judged print, with no patch over 0.1% of the frame. A, D and B are still drawn.
- **With one photograph per print**, the control's own D and B are still written, so the user can see what "unpainted" looks like in this session's pipeline. **[coordinator]** This visual-reference use is an addition; [09] specifies only the gating.
- **The control never defines the reference** [09]: a control that sets the reference cannot test it.
- **[Amended, B14] What the control tests:** the capture (light, fringes, glare, processing). It holds no paint, so it cannot reveal a reference contaminated by paint (B1). The specks constant was set under [09]'s unit; recalibrate it under the adopted T on the gate captures. On [12]'s bench the control pair sat at exactly 0.5%.
- **[Amended, B7]** D is judged against the control's D from the same session, not against an abstract rule. Split toning and auto white balance can make an *unpainted* print's D turn hue smoothly too.

### 4.6 Records

- A JSON per print: source SHA-256, settings, evidence used, warnings.
- A run log listing files, failures and their reasons.
- No statistics, no thresholds and no counts anywhere a person reads [08], [09], [03].

### 4.7 Dropped

**From the current tool:**
- raw C\*ab and LRC;
- the four threshold modes and the tiers;
- the 100 px component filter;
- CLAHE;
- the analytic Adobe RGB and ProPhoto paths;
- histograms;
- every per-image statistic.

**From TODO.md:**
- per-band medians;
- the trimming loop;
- the optional additive tilt;
- the per-image picker as the main path;
- folder-wide boxes;
- presets;
- early-saturating opacity;
- coring the boost.

**From the proposals:**
- multi-scale gating [03]/[11];
- lateral-colour removal [02];
- the 2 × 2 variability yardstick [05];
- the tone-following and "two readings" self-checks [10], [11].

These are deferred under [06]'s rule: anything later must answer a real capture that needed it.

### 4.8 Order of work

1. **Now:** remove 4.1.2's leftover numbers and claims (section 2, item 4). **[Amended, B11]** Done after the final pass, as 4.1.3, and checked by running it on the synthetic set.
2. **Ask the author:**
   - Which part of Chroma mode failed: the method, the picks or the maps? [07], [09]
   - Is a second photograph per print acceptable?
   - **[Amended, B10]** Would you draw two to four boxes per print, examined on the object?
   - Confirm the objective: never show confident colour on unpainted print; then show moderate and strong paint; faint washes only where two photographs agree [07].
3. **Make four test captures before code** [07], [09]: one known-unpainted print and one print whose paint a conservator has marked under magnification, raking light and UV, each photographed twice as in 4.2.
4. **Build A, D and B,** the strip and the words for one photograph. Run them on the test captures against v4.1.2, TODO.md as written, and a DStretch or eyedropper-plus-Lab-curves baseline.
   - **[Amended, B7]** Right after D is built, not at the end, run a minimal line-up test: a dozen montages, one with a contaminated reference.
5. **Add the second photograph**, "seen in both", C and the control rule. Run again.
6. **Add examined boxes** only if the test captures show the automatic reference failing in ways boxes fix.
7. **Housekeeping:**
   - restore v1.2's small Tk window [06];
   - a `.py` file with the version in git only;
   - remove "Chroma Diagnostic Tool v3.0", which does not parse;
   - rewrite the README around what the pictures cannot show.
8. **Observer tests:**
   - the line-up test (Buja et al. 2009; Wickham et al. 2010): can viewers pick out a montage whose reference is wrong [06], [09]?
   - colour-deficient observers on C [03].

### 4.9 The answer to the hard question

**How the tool establishes the unpainted photograph.**
- From that capture alone, never from neutral grey, a card, a profile or another capture [05], [01], [02].
- It fits an explicit model, the print's own tone as a smooth curve in lightness plus a smooth light field across the frame. The fit uses votes of places and a high-breakdown estimate, in a space where a cast and a wash are additive [10], [11].
- A paint layer must hold most places at a tone, or most of the frame, before it is taken for the print.
- Examined boxes can correct it, cross-checked against one another.
- Its departures are judged against a threshold the paint cannot move [10].

**How a viewer knows it has gone wrong.**
- **D,** the tool's assumption ×4, must look like a plausible untouched print [09], [11]. **[Amended, B7]** Judge it against the session control's D: same session, same pipeline, no paint. A hue the control's D lacks at the same tones means the model took paint for the print there. Judged alone, the rule "one family of hue" also fails on unpainted split-toned prints in auto-white-balanced captures [12].
- **The paper border** is outlined, judged like the print, and must stay grey in B and C [10]. It tests paper tones only.
- **The departure picture C** appears only when a second, different photograph agrees, and **the session's unpainted control** must stay quiet [09], [07]. **[Amended, B14]** The control tests the capture, not the reference.
- **The strip** says how faint a wash this capture can show at each tone [11].
- **[Amended, B1] The complementary ghost.** Colour in C on things you know are unpainted, complementary to paint you can see, and following one band of tone, means a broad wash has entered the reference. C is then wrong at those tones in both photographs. Box examined unpainted areas at those tones before reading C.

**What still gets through:**
- **[Amended, B1]** a wash over most of the picture. It enters the reference in both photographs, and C can then show *unpainted* areas in the complementary hue as paint, agreed by both photographs (22.4% of an unpainted face on [12]'s bench). Only the ghost's signature, D compared with the control's D, and examined boxes stand against it;
- phone processing shared by both shots, unless the device differs;
- object-side colour that is not paint;
- neutral and tone-matched media, never shown.

Final confirmation is at the object [07], [02].

### 4.10 Gate criteria [Amended, B8]

The gate uses the four test captures, extended later to the larger sets in [09] §8, [10] §11 and [11] §10. The rebuild passes only if all of these hold:
1. **(i) Control quiet.** In "seen in both", the unpainted control shows no coherent area beyond specks in more than 1 pair in 10.
2. **(ii) Beats the baselines.** Conservator-marked moderate and strong paint is shown at least as well as by the DStretch or eyedropper-plus-Lab-curves baseline. A conservator who knows neither the print nor the tool judges this.
3. **(iii) C earns its place.** If A, D and B alone serve the conservator as well as A to D with C, drop C's machinery.
4. **(iv) No ghost.** A conservator-marked print with a broad wash does not show its unpainted areas in C. If it does, fall back to [11]'s median spread and test again.
5. **(v) The margin decision** (formerly [10]'s F6). Turn paper-margin anchoring on by default only if it lowers false colour on most captures.
6. **(vi) A wrong reference is visible.** In the line-up test, viewers pick the montage with a contaminated reference better than chance (one in four).

At the gate, also measure the colour difference of the conservator-marked thin washes, which the strip assumes is about 1.3 ΔE (B12).

These numbers belong to the developer's test, never to the tool's output.

## 5. Disputes resolved in cross-pollination, and how

1. **Per-image marks.** The red team required 4–6 boxes per image; history ruled out per-image interaction.
   - **Rule [09]:** *no departure picture rests on one photograph's guess about itself; it needs a second, deliberately different photograph that agrees, or the user's own unpainted marks.*
   - History retracted its certainty that picking sank Chroma mode, since that came from an agent's gloss.
   - The red team's marks become one route among two.
   - **[Amended, B2]** After the final pass, marks are no longer a witness for C. Under the fixed threshold, one photograph plus five examined boxes drew C over 26.1% of an unpainted print [12]. Boxes now only correct the reference.
2. **The yardstick.** Camera's staged lower-quartile spread [05], against remote sensing's fixed departure [04].
   - **[10]:** camera retracted. Its spread showed 0% of a backdrop holding 49% of its tone band, with silent diagnostics.
   - Rule: *nothing the paint can influence may enter the threshold; misfit should show as colour, where the reference panel and negative controls can catch it* ("prefer failures that show").
   - [11] kept a median-based spread per tone and scale, but tested it only against a 90th percentile, not against a fixed threshold.
   - **[coordinator] resolution:** adopt [10]'s fixed threshold. Under the witness rule, false colour from misfit that differs between captures is removed by agreement. A spread fitted to the print's own variability hid cool washes on glossy toned prints (S7/S8: 1–18% shown, against 75–87% with the fixed threshold [10 §2]).
   - **[Amended, B3] The price, on the same scenes:**
     - S7 showed 24% false colour, a complementary ghost;
     - [04]'s P3 showed 16.9%, with the margin 60% lit [10 §5].

     That misfit is caused by the paint, so it does not differ between captures, and it passes the witness (B1).
   - **The fallback:** switch to [11]'s median spread if gate criterion (iv) fails, that is, if a broad-wash print shows its unpainted areas in C. A quiet control is not enough reason to keep the fixed threshold, because a control holds no paint and cannot show a ghost.
3. **Feature space.** **[10] rule:** *threshold departures in log-chromaticity, where a cast and a wash are the same shift at every tone.* [04] had seen no difference only because its comparison used a spread-normalised rule. Display stays in Oklab or CIELAB [11].
4. **Light field and edge term.** **[10]:** one quadratic light field fitted jointly with the tone curve by the MM estimator. Camera's patch votes were dropped: they got worse when anchored, 83 → 36 → 11%. The edge term is one fitted κ²G² plus comparison at the camera's chroma resolution; camera's collinear κ²JJᵀ term was dropped (it fitted a 17 px "misregistration").
5. **Place votes against pixel majorities.** **[11]** adopted the votes, which fixed its majority-painted failure without boxes. Its stated cost: broad faint washes move from C to B, which is acceptable because B is uncored.
6. **The reference picture.** **[09], [10], [11]** all ended at an *exaggerated* reference, ×4. An unexaggerated one failed to reveal contamination on [04]'s P2 [10] and was a weak tell on [03]'s bench [11]. Three variants were folded into D: history's separate tone strip, perception's "As if unpainted" at natural strength, and the red team's unexaggerated panel.
7. **Presets.** [09] dropped them, because they hide decisions; [10] and [11] kept them. **[coordinator] resolution:** drop them for the rebuild. A single T0 is set from negative controls, and presets come back only if real captures show one setting cannot serve.
8. **"Presence".** Retracted by [11] and [09]. Renamed "Where colour departs from the print's own tone".

**Retractions, which matter most:**
- **[09], 13 retractions:**
  - an automatic presence map from one photograph;
  - early-saturating opacity;
  - presets;
  - the folder pick;
  - the band-spread unit;
  - "the montage is the working simple system";
  - hue as the paint's colour.
- **[10], 12 retractions:**
  - its own yardstick;
  - Mahalanobis in the print's own variability;
  - band medians;
  - patch votes;
  - CIELAB;
  - its claim that "As if unpainted" reveals contamination;
  - its own headline numbers, tuned on its own bench.
- **[11], 11 retractions:**
  - "Presence";
  - the claim to find faint washes (its washes had been twice Van Der Zee's);
  - the key as specified;
  - coring;
  - picks weighted ×20;
  - the three-panel montage.

## 6. Diff against the pre-commit

**Changed:**

| Part | Pre-commit | Now |
|---|---|---|
| The reference | Band medians trimmed and refitted, in CIELAB | Place votes, a high-breakdown fit of a tone curve plus a light field, in log-chromaticity |
| Picks | A per-image override with a folder default | Examined boxes, optional and cross-checked; none folder-wide |
| Light | An optional additive plane | A light field always fitted jointly |
| Yardstick | Spreads of the residual | A fixed departure floored by pixel-scale noise |
| Smoothing | a\*b\* only | Comparison at the camera's chroma resolution |
| The presence map | Drawn from every capture | Drawn only when a second photograph agrees; renamed; bright on dim, with no hard edge **[Amended, B2, B9]** |
| Pictures | Three panels | Four, including the reference ×4 |
| The boost | Cored | Uncored |
| Validation | The last step | The first gate |

**Survived:**
- the reframe;
- the vector departure;
- the boost around the print's own tone, drawn neutral;
- hatching for what cannot be judged;
- no numbers;
- one small module;
- the load and working-size steps;
- "neutral and tone-matched media cannot show";
- picks are never required.

**Added:**
- a second photograph and "seen in both";
- the session's unpainted control;
- the paper border as a negative control;
- the strip of thin and clear marks in this capture's own noise;
- the blank sentence;
- capture advice on phone face and sky processing;
- the DStretch and eyedropper baselines;
- the line-up test;
- colour-deficiency-safe drawing;
- asking the author which part of Chroma mode failed;
- finishing 4.1.2's removals now.

## 7. Residual risks and open items

1. **All evidence is synthetic, from one model family**, and benches disagreed with each other (section 1). The real-capture gate decides everything.
2. **Whether a second photograph per print is acceptable is the user's call.** If not, the tool is A, D, B and the strip, and C is never drawn. **[coordinator]**
3. **[Amended, B1, B7] A wash over most of the picture** enters the reference in both photographs. C then shows unpainted areas in the complementary hue, in both photographs (22.4% on [12]'s bench). D may not reveal it: a cool wash over a warm print, in an auto-white-balanced capture, stays inside the smooth hue turn that unpainted prints also show. No validated fix exists. It is gate criterion (iv); its signature is in the README, and examined boxes are the remedy.
4. **Phone processing shared by two shots from the same phone** survives "seen in both". It is mitigated only by a different device or raw capture, plus the same-camera warning [09], [05].
5. **Paper-margin anchoring.** The benches disagree; real captures decide (test F6) [10].
6. **The place-vote and LTS → MM combination is untested** **[coordinator]**.
7. **[Amended, B12] Thin washes at the capture's own noise.** If Van Der Zee's thin washes are about 1 ΔE (a bench assumption, to be measured at the gate), they sit at the capture's own noise. They may then show only as forms in B, and only on a decent display [11].
8. **Object-side colour that is not paint** (foxing, stains, mirroring, uneven toning) is shown, and the user interprets it [02], [03].
9. **Neutral and tone-matched media are invisible** [all].
10. **Whether viewers can see a wrong D at all is untested** (line-up test) [06], [09], [11].
11. **The control's speck threshold, and T0**, are developer constants with no real-capture basis yet [09], [10]. **[Amended, B14]** The speck threshold must be recalibrated under the adopted T.
12. **[Amended, B13] B and C use different measures** (display space against χ) and can disagree tone by tone.
13. **[Amended, 12 C] Load-bearing claims that rest only on the advocates' own benches:**
    - the witness's 0.0–0.4%;
    - Chroma mode's mechanism;
    - "Van Der Zee washes ≈ 1 ΔE";
    - "D ×4 reveals contamination";
    - votes fixing majority-painted tones;
    - a fixed T over an adaptive spread;
    - χ over CIELAB;
    - the 10–50% edge reduction;
    - phones' semantic processing.
14. **UV fluorescence is parked.** It is the cheapest way to tell stain from paint [09], but the user's "the luminescence stuff is moot" rules it out for now [12 A, 1.2-6].
15. **The pictures still encode a decision** [07] 1.2-1. T0 is a developer constant, scored only by the gate criteria (4.10), and the user never sees it.

## 8. Red-team verdict

Appended after the final pass. The full report is `reports/12-red-team-final.md`.

### Scorecard of the red team's original objections

**Answered by mechanism:**
- 1.1a picks are circular (boxes examined on the object, cross-checked);
- 1.1c "unpainted = neutral";
- 1.1e wash against cast in one photograph (the witness);
- 1.1f coherent blobs (the witness, for pairs);
- 1.2-2 "lack thereof" (the blank sentence and the strip; the sentence reworded, B6);
- 1.2-3 consistency within the frame;
- 1.2-5 early-saturating opacity;
- 1.4 undefined terms;
- 1.5: the histogram floor, "one photograph tells the light", "the iterations improved";
- 1.6 trivial answers (the baselines, now with a criterion, B8);
- 1.7 the sceptics;
- 1.8 ill-posed (narrowed to "places to look").

**Partly answered:**
- 1.1b extensive paint: votes and a high-breakdown fit raise the breakdown point; past it, the ghost (B1).
- 1.1d in-frame reference: the border's roles are now consistent (B4).
- 1.1g pictures not revealing their errors: decoding faults are answered; model contamination is moved into D compared with the control's D (B7).
- 1.2-7 garbage in: capture garbage is answered; object garbage still stands.
- 1.5 pixel noise as the unit: answered for pairs; at edges, κ² is now fitted on the control (B5).

**Absorbed rhetorically, and where each moved:**
- 1.2-1 presence is a decision: moved into T0, a developer constant, now scored by gate criteria (4.10).
- 1.2-4 the README's promise: now done in 4.1.3, but the rebuild's README is still to write.
- 1.3 the feedback channel: now the gate criteria.
- 1.5 "synthetic tests validate": the resolution in 5.2 now cites both halves of the evidence.
- 1.5 "a label prevents a quantitative reading": C is no longer hard-edged (B9), but it is still a bright overlay.

**Still standing:**
- 1.2-6 luminescence (residual 14);
- 1.2-8 4.1.2's leftovers: now fixed in this delivery (4.1.3).

### Seams the merges created

| Seam | Status |
|---|---|
| B1 Paint fakes agreement: the complementary ghost in both photographs | **Accepted residual risk**, with a fix of wording and order: stated in 4.4, 4.9 and residual 3, its signature restored to the README, gate criterion (iv) added. No validated mechanism |
| B2 Boxes as a witness rebuild single-photograph maps | **Adopted fix:** the second photograph is C's only witness |
| B3 The fixed threshold quoted half its evidence | **Adopted fix:** both halves cited; the fallback tied to criterion (iv) |
| B4 The border was both reference and control | **Adopted fix:** a judged negative control kept out of the fit; anchoring switches its role off, visibly |
| B5 "The paint cannot move T" was false at edges | **Partial fix:** κ² is fitted on the control or the border; paint's own edges still raise G |
| B6 The blank sentence described another yardstick | **Adopted fix:** reworded; the strip's C row only with two photographs |
| B7 D carries the worst failure and is tested last | **Partial fix:** D is judged against the control's D; a minimal line-up test moves up to step 4. D stays weak for a cool wash over a warm print |
| B8 A gate with no criteria, and an orphaned F6 | **Adopted fix:** section 4.10 |
| B9 The opacity ramp and the gate disagreed | **Adopted fix:** the gate stays at T; the ramp runs T → 2T |
| B10 A retracted premise carried the automatic default | **Adopted fix:** marked as the coordinator's choice; both readings quoted; the boxes question added for the author |
| B11 "Done" was not done | **Adopted fix:** 4.1.3 committed with this delivery, after a test run |
| B12 A bench parameter stated as a fact | **Adopted fix:** labelled an assumption; measured at the gate |
| B13 Two colour spaces under one decomposition | **Adopted fix:** B rendered in display space so D + B holds; the different measures stated |
| B14 The control tests the capture, not the reference | **Adopted fix** in wording; the speck constant is to recalibrate at the gate (partial) |

### Verdict

**Where the synthesis is more than the red team's own maximum honest version:**
- an automatic reference that needs no marks (with two photographs it beat the red team's marks-based pair on its own bench: 0.2% false colour with 88.5% of the faint wash, against 0.0% with 78.9%);
- departures in log-chromaticity, compared at the camera's chroma resolution;
- the session control, the strip and colour-deficiency-safe drawing;
- finding the print, and the capture advice;
- the baselines and the line-up test;
- asking the author;
- the retraction record.

**Where it was secretly less, before these amendments:**
- no criteria;
- "fail-visible" without the visibility;
- a boxes route that rebuilt single-photograph maps;
- D overloaded;
- work called done that was not done;
- a gloss treated as a mandate.

The amendments address all six except D's weakness for cool washes and the ghost. Both are stated as residual risks with a gate criterion; neither has a mechanism.

**Claims resting only on the advocates' evidence** are listed in residual 13. The red team's own bench, running the synthesis's engine as specified, gave 0.5% false colour on the control and 0.2% on a normally painted print's unpainted areas, but 22.4% on a broad-wash print. The design works in the normal case, and its stated worst case is real.
