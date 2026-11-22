<!-- Saved verbatim by the coordinator from the resumed perception agent's hand-back (merge round; the harness refused
report files). The harness's two-space indent is removed; nothing else is changed. -->

# Handpaint visualiser, design v2: perception, revised against the conservation report

*This is my design changed by the conservation analyst's report (`peer-report.md`; "the peer" below). It is not a summary of both. Both repositories were only read. New code, results and figures are in `/home/user/xpw/45b29c/work/`:*
- *`pipelines_v2.py`, `render_v2.py`, `eval_v2.py`, `picks_v2*.py`, `tone_follow.py`;*
- *`v2_full.json`, `v2_yard.json`, `picks_v2*.json`;*
- *`figs_v2/`.*

*Everything numeric comes from my synthetic bench. Since the first version I made it harsher: thin washes of about 1 to 1.5 CIELAB units, and paired captures that share the same white balance. No real VDZ capture was available. The harness does not let me write report files, so this text is the report.*

## 1. Verdict, v2

The tool shows **where colour departs from the print's own tone, by more than this capture's own error**, and it shows the reference it judged against. It does not show paint. Five changes follow from that.

1. **The tone is voted by places, not pixels** (the peer's mechanism), and my model is fitted to the votes. The model is a smooth tone curve, plus a cast scaled with lightness and allowed to tilt with lightness, used only when a cast is found. On my bench this fixes the case I could not fix without boxes: a backdrop painted over most of a range of tone, where AUC went from 0.66 to 0.83 and false colour from 14.6 % to 0.7 % of the unpainted area. It raises AUC on every other capture too. When paint covers most *places* at a tone, votes fail as well. Boxes the conservator has **examined on the object** then repair it, used as *corroborated anchors* (§3).
2. **The yardstick stays a median-based spread per tone and scale.** It does not become a 90th percentile. A tail quantile breaks down when a tenth of a tone is painted, so the painted tones raise their own bar. At matched false colour on an unpainted control, the median-based yardstick shows far more known paint (§4).
3. **The boosted picture (B) is uncored, departures ×4.** It is where thin washes live, as forms the eye pools. My v1 coring removed exactly those washes.
4. **Two pictures replace four of mine.** One shows the reference: D, "the print as expected unpainted, colour ×4" (the peer's), blinked against the capture ×4 (mine). One shows departures: C, "Where colour departs from the print's own tone" (the peer's name), drawn bright on a dimmed print (my lightness step, so it survives colour-vision deficiency).
5. **One strip and one fixed sentence say what a blank means.** The strip shows, per tone, a thin wash and a small clear touch set into *this capture's own noise*, as B and as C would draw them. The sentence says a blank is not "unpainted".

**What would reverse this verdict:**
- *Phone colour on objects.* Real negative controls show content-aligned colour from phone processing (faces warmed, skies blued) in most captures.
- *Tone that varies by place.* The unpainted print's colour varies more from place to place than from tone to tone: patchy toning, mat burn, or local yellowing over large areas. That is the peer's reverser, and it applies to both designs.
- *Blind observers.* Observers do not see a wrong reference in D or the blink.

## 2. What the pictures promise, given thin washes

**The objection, in numbers.**
- *Washes at the capture's own scatter.* VDZ colouring is largely thin transparent watercolour, about 1.3 CIELAB units on the peer's bench. My bench's capture scatter, per pixel after the 5 px chroma median, has a 90th percentile of about 1.2 units.
- *Colour that is not paint.* Much colour on a monochrome print is not paint: toning, yellowing, silver mirroring, foxing, adhesive.
- *Paint that is not colour.* Some applied media carry no colour: graphite, tone-matched spotting, opaque white.
- *Picks on washes.* A pick chosen on screen can sit on a thin wash.

**Where v1 promised too much, measured.**
- **"Presence".** The name promised paint. The map shows departures, and on the bench it showed foxing, a tide line and glare as readily as paint.
- **The key.** Its "faint wash" was a pink dye of 1.9 a\*b\* units in the light tones (1.4 mid, 0.9 dark). It was drawn as a flat, noise-free disc, and only as the presence map would draw it. Set into this capture's real noise, a wash of that size shows in C only as fragments (`figs_v2/strip_compare.png`). So the key told the viewer a faint wash would show where it would not.
- **The bench.** My "faint" washes were 1.7 to 2.8 units, about twice the target. With thin washes of about 1 unit, C shows 19 to 32 % of a face wash and 0 to 2 % of a backdrop wash (v1 and v2 alike).
- **Boosted's coring** (nothing below 1.5 spreads) suppressed the thinnest washes. The pooled observer described in §8 got d′ 19 from the cored B against 33 from an uncored B for the 1-unit backdrop wash, and 61 against 132 with the voted reference.
- **Picks weighted ×20** absorb a wash they sit on. A pick on the 1-unit face wash lowered the face's pooled evidence in B from 38 to 30.

**What each picture promises now.**
- **C, "Where colour departs from the print's own tone":**
  - *It shows:* "here, in this capture, the colour departs from the print's own tone at this lightness by more than this capture's own departures do, at this tone and scale". That includes local deterioration (foxing, adhesive, mirroring), glare and phone rendering, as readily as paint. Interpreting them is the user's job, per the author's position 5.
  - *It does not show:* washes at the capture's own scatter, colourless or tone-matched media, anything hatched, or *tone-wide* toning and overall yellowing. Those are absorbed into D, because they are the print's tone. On the bench, warm-toned and purple-toned prints and yellowed paper drew under about 1 %. So the objection's "much colour is not paint" applies to *local* deterioration, and that is shown, deliberately. It does not apply to uniform toning, which is not shown.
- **B, departures ×4, uncored:**
  - *It shows:* every departure, thresholded by nothing, noise included.
  - *For thin washes:* this is the picture for them, as forms a viewer pools over area (spatial summation). Chromatic vision is itself low-pass (Mullen 1985), which favours broad faint forms.
  - *Its limit:* under mixed light even B carries a 1-unit broad wash weakly (pooled d′ about 6 to 10, against 40 to 130 in even light), because the reference's misfit to the light is as broad as the wash.
- **D, the print as expected unpainted, ×4:**
  - *It shows:* the reference itself.
  - *What to look for:* a hue or a form no unpainted silver print has means the reference is wrong (§5).
- **The strip:**
  - *What it shows:* at each tone, a thin wash (1.3 units at L\* 80, scaled with (L\*+16)/116 as a transparent dye's is) and a small clear touch (5 units, 9 px). Both are set into a block bootstrap of this capture's own residual at that tone, and drawn as B and as C would draw them.
  - *What it promises:* only "a wash this thin looks like this here". It does not certify absence.
  - *Hatching:* where the capture holds too little clean surface at a tone.
- **The sentence, always printed:** "Blank in C means no colour departs from the print's own tone here, in this capture, by more than this capture's own error. It does not mean unpainted: thin washes (see the strip), colourless or tone-matched media, and anything hatched cannot show." This is adapted from the peer's.
- **Picks:**
  - *What they are:* boxes the conservator has examined on the object under magnification and raking light, not chosen on screen.
  - *How they act:* as corroborated anchors (§3).
  - *Against a pick on a wash:* a pick that disagrees with the other picks beyond the capture's per-pixel scatter is dropped and outlined in D. On the bench, the cross-check caught a pick on the thin face wash (it also dropped one good pick, which the user sees outlined).

## 3. The tone voted by places: adopted, adapted

**Mechanism:**
- Each tile of a 10×10 grid gives one vote at each 2 L\* band where it has at least 25 pixels (at 1.3 MP; scaled with the frame).
- The vote is the median (a\*, b\*), with the median L\*, x and y.
- My model (the P-spline curve in L\*, plus cast terms ×(L\*+16)/116 with a lightness-dependent tilt) is fitted to the votes by Tukey IRLS, each vote weight 1. A place counts once per tone, whatever its area.
- The premise is printed with the reference: "at each tone, most places on the print are unpainted".

**Evidence (v1 = pixels; v2 = votes; everything else equal):**
- *AUC:*
  - phone 0.963 → 0.969;
  - mixed light 0.950 → 0.967;
  - glare 0.909 → 0.912;
  - toned 0.960 → 0.969;
  - thin washes 0.801 → 0.865;
  - thin washes in mixed light 0.808 → 0.870;
  - **majority-painted 0.664 → 0.830, false colour 14.6 % → 0.7 %, with no boxes.**
- *Unpainted control:* 0.4 % → 0.7 %.
- *Self-check:* the tone-following check (below) fires on v1's majority failure and is silent on v2's.

**Cost.** Where the light tone lives mostly *in* a painted backdrop, the places themselves are backdrop. Votes then absorb more of a broad faint wash than pixels do: shown in C, 82 → 37 % on the phone capture and 91 → 37 % on the scan. B keeps it (pooled d′ 54 → 50 on the phone capture; 33 → 132 for the thin backdrop). The design accepts this cost because thin washes are B's job.

**Limit, and what then.** When paint covers most *places* at a tone, votes fail. I tested a wash over the upper two-thirds of the picture: AUC 0.42, false colour 8.0 %. Four rules for boxes were compared on that print:

| Pick rule | AUC / false colour |
|---|---|
| peer's soft rule: shrink by the scale, smooth over 8 L\* | 0.45 / 5.8 % |
| hard rule: act fully beyond the per-pixel 90th percentile, nothing below, plus a leave-one-pick-out cross-check | 0.71 / 0.4 % |
| **corroborated rule (v2)** | **0.83 / 0.4 %** |
| v1's ×20 trust | 0.79 / 0.6 % |

The corroborated rule is the hard rule plus one addition: a correction *below* the scatter stands where picks at two or more places agree on it. That uses the votes' own premise: the tone is everywhere, and a wash is local.

## 4. The yardstick

**The rule:** *the yardstick must be an estimator that paint cannot move, a median-based spread per tone band and scale, which breaks down only when half a tone is painted, not a 90th percentile, which breaks down when a tenth is; the departure map's ramp on it is then set by negative controls so that an unpainted capture shows under 1 % of its area, and everything weaker is left to B.*

**Evidence.** Votes in both arms, with the 90th-percentile ramp raised until the unpainted control matched:

| Capture | median-based, ramp 3 → 5.5 (control 0.7 %) | 90th percentile, ramp 1.6 → 3.0 (control 0.5 %) |
|---|---|---|
| thin washes, mixed light | AUC 0.870; stripes 100 %, patch 100 %, cheeks 57 % | AUC 0.802; 28 %, 69 %, 17 % |
| purple-toned print | AUC 0.969; backdrop 39 %, stripes 100 % | AUC 0.914; 1 %, 30 % |
| glare | false colour 6.1 %; stripes 100 %, patch 99 % | 1.1 %; 6 %, 12 % |

The 90th percentile is larger in dark bands, where JPEG error is heavy-tailed and where the red-over-dark stripes are, so paint there masks itself. AUC, which does not depend on the ramp, favours the median-based spread everywhere. With the peer's own ramp (1 → 2), it showed 4.0 to 4.3 % of the unpainted control on my bench.

**Kept from the peer:**
- the yardstick is taken from low-gradient pixels;
- the 90th percentile *is* the right tolerance for a different question: whether a pick disagrees with the automatic tone by more than the capture's per-pixel scatter (§2, §3).

**Kept from v1:**
- the floor of 0.4 a\*b\* (one 8-bit code step is 0.4 to 0.85);
- finer scales never narrower than coarser;
- coarse scales gated by the pixel's own fine evidence (ungated, false colour was 2 to 3 %);
- the edge-tolerant lookup.

## 5. One reference picture, one departure picture

**(a) The reference: D, blink and strip.**
- **D**, "the print as expected unpainted, colour ×4" (the peer's): the print's lightness (shadows lifted slightly), with the reference's a\*, b\* ×4, gamut-mapped in Oklch at constant lightness and hue.
- **Layout:** the montage is a 2×2 grid, with A (the capture) beside C on top and D beside B below. D + B = the capture ×4, so the viewer reads the split directly. This is juxtaposition with an explicit encoding of each part (Gleicher et al. 2011).
- **Blink:** D ↔ capture ×4, 700 ms each, no blank between (the blank is what causes change blindness: Rensink, O'Regan and Clark 1997). Only departures flash. The two frames share one lightness, so the flash is pure colour.
- **Strip**, on one axis from paper to shadow, five rows:
  - the expected colour ×4 (the peer's);
  - the tone (the peer's);
  - a thin wash, as B shows it;
  - a thin wash, as C shows it;
  - a small clear touch, as C shows it.

  Hatched where the capture lacks clean surface at a tone; ticked where boxes moved the tone; dotted beyond the tones boxes reach.
- **Decision rule:** *D is always shown.* If D shows a hue or a form no unpainted silver print has, or the blink flashes on things that cannot be paint, the reference is wrong at those tones. Box unpainted areas there that you have examined on the object.
- **Dropped from mine:**
  - "As if unpainted" at natural strength: my own test showed it a weak tell, and ×4 makes the reference's structure visible;
  - the soft-knee second blink frame (B is now linear, so the blink must be too);
  - the separate ×3 reference strip at one lightness (weak; toned prints legitimately change hue);
  - the old key: noise-free discs, one strength, C only.
- **Dropped from the peer's:** the band "overrule" step. My penalised curve with Tukey weights does that job. Its strip tick now means "boxes moved this tone".

**(b) The departures: C.**
- **Name:** "Where colour departs from the print's own tone" (the peer's).
- **Context:** the print as a dim grey, Oklab L 0.20 to 0.52.
- **Departures:** drawn bright, at L 0.80 and chroma up to the gamut's 90 %, in the departure's own hue (the finest scale that stands out). Opacity follows the §4 ramp.
- **Hatch:** for what cannot be judged.
- **Decision rule:** *a departure is always carried by a lightness step and by hue, never by hue alone.* Simulated with Machado, Oliveira and Fernandes (2009), a pink departure at the print's own lightness falls from ΔE 26 to 4 (protanope) and 8 (deuteranope). Bright on dim, it stays at 46 to 53. Red and pink are the colourist's commonest portrait hues.
- **Dropped from mine:** the name "Presence", and the claim to find faint washes.
- **Dropped from the peer's:** the colour overlay at the print's own lightness, which dichromats lose, and the 90th-percentile ramp (1, 2).

**B** is the peer's: departures ×4, linear and uncored. From mine it keeps the Oklch gamut compression and the slight shadow lift: at L 0.25, sRGB allows only about 0.05 of chroma for yellow, so gold on a dark ground otherwise cannot show.

## 6. Design v2: components and connections

```
capture → 1 load (ICC → sRGB; EXIF orientation; EXIF make, model, software for the phone note)
        → 2 working size 2000–3000 px (area average)
        → 3 CIELAB; a*b* 5×5 median
        → 4 leave out, hatched: clipped (dilated); near white on a local mean; L* < 5; outside the object box
        → 5 reference: votes of places → curve(L*) + [cast ×(L*+16)/116, tilt with L*, only if a cast is found]
             (+ lateral-colour removal, the peer's step, untested here)
             (+ examined boxes as corroborated anchors, cross-checked)
        → 6 edge-tolerant departure: smallest residual over the lightness found in each 5×5 neighbourhood
        → 7 yardstick per 4 L* band × scales σ = 2, 6, 18 px: median-based, low-gradient pixels, floor 0.4,
            finer ≥ coarser
        → 8 C opacity: fine scale after a 5×5 median, ramp 3 → 5.5; coarse scales gated by the pixel's own
            evidence; presets low / normal / high
        → 9 pictures: [A | C] / [D | B]; strip; words; the blank sentence; blink D ↔ capture ×4
        → 10 JSON: source, hash, preset, reference source, boxes, whether a cast was modelled, the words
             (no statistics)
```

**Self-checks, in words:**
- **Tone-following** (the peer's): a 5 L\* range lit in more than 30 % of its pixels and in more than half the tiles that contain it. It was silent on all seven normal captures and fired on both of v1's failures. It *missed* v2's failure on the widely washed print, where the pictures still showed it (orange glow on face and hair in C; cooler light tones in D).
- **Boxes dropped by the cross-check**, outlined in D.
- **"A colour cast across the frame was allowed for."**
- **"Phone capture: colour may have been added to faces or skies."**
- **"Hatched: too bright or too dark to judge."**

**Advice, not requirement:**
- Capture twice from different positions, and trust what repeats (the peer showed glare and fringes do not repeat; deterioration does).
- Keep the paper border in frame and unclipped.

## 7. For each uncontrolled capture, how should the tool establish what the unpainted photograph looks like, and how would someone looking at its output know when that has gone wrong?

**Establish it from that capture alone.** The unpainted print is modelled as its own tone (colour as a function of lightness, from paper to shadow: base, image tone, toning and overall yellowing), seen through light that drifts evenly across the frame.

1. **Leave out what cannot be judged.** That is clipped, near-white and near-black pixels and anything outside the object box. It is hatched, never read as "no colour".
2. **Vote the tone by places.** Each tile gives one vote per tone band, and the model is fitted to the votes. Paint, stains and silvering are local, so they cannot outvote a tone that is everywhere. Cast terms are added only if the fit finds a cast.
3. **Use examined boxes as corroborated anchors.** Where votes fail (paint at most places at some tone), boxes examined on the object move the tone:
   - by any amount beyond the capture's per-pixel scatter, from any box that survives the cross-check;
   - below that, only where boxes at two or more places agree.
4. **Judge departures against this capture's own spread** at that tone and scale. Use a median-based estimate that paint cannot move, set by negative controls.
5. **What no source can establish:**
   - washes at the capture's own scatter (B may show them as forms);
   - colourless or tone-matched media;
   - colour a phone added to objects;
   - tones the capture lacks.

**Know it has gone wrong: look at D, C, B and the blink.** Five signatures:

| What you see | What it means | What to do |
|---|---|---|
| D has a hue or form no unpainted print has: a cool band in warm light tones, or coloured mid-tones | paint (or a mount or table) was taken as the tone | box examined unpainted areas at those tones, or set an object box |
| C lights unpainted things of one tone in the **complement** of visible paint (face and hair orange beside a blue wash); the colour follows a tonal band across objects | the same | the same; the tone-following words may fire |
| C or B carries a soft wash that spans the frame or rings a bright spot, ignoring forms | the light's drift or glare | read with care; capture again |
| In the blink, something flashes that cannot be paint, or paint visible in A does not flash | the reference is wrong there | box at that tone |
| The strip's thin wash does not show at a tone | blank means "could not tell" there | look in B; capture again |

The pictures carry what the words miss. On the bench the tone-following check missed v2's one automatic failure, and the peer reports the same for a table in frame.

## 8. Evidence (synthetic bench; `work/v2_full.json`, `v2_yard.json`, `picks_v2*.json`)

**Thin washes, measured on paired captures sharing white balance:**
- face flesh wash 1.0 unit;
- backdrop 1.0 to 1.2;
- canton 1.4 to 1.5;
- cheeks 2.0 to 2.2 (on top of the flesh).

**AUC / false colour on unpainted area:**

| Capture | v1 | v2 | TODO.md (fair) |
|---|---|---|---|
| scan, even light | 0.999 / 0.1 % | 0.999 / 0.1 % | 0.999 / 0.4 % |
| phone, even warm light | 0.963 / 0.9 % | 0.969 / 0.6 % | 0.903 / 5.1 % |
| phone, mixed light | 0.950 / 0.9 % | 0.967 / 0.6 % | 0.518 / 15.6 % |
| phone, glare | 0.909 / 6.9 % | 0.912 / 6.1 % | 0.863 / 8.0 % |
| purple-toned | 0.960 / 0.8 % | 0.969 / 1.3 % | 0.884 / 4.1 % |
| backdrop mostly painted | 0.664 / 14.6 % | **0.830 / 0.7 %** | 0.570 / 15.0 % |
| thin washes | 0.801 / 0.8 % | 0.865 / 0.7 % | 0.716 / 5.8 % |
| thin washes, mixed light | 0.808 / 0.9 % | 0.870 / 0.9 % | 0.487 / 17.0 % |
| unpainted, mixed light | – / 0.4 % | – / 0.7 % | – / 16.4 % |

**Thin washes:**
- *Shown in C* (v2; even light / mixed light): face 19 / 22 %, backdrop 0 / 2 %, canton 28 / 61 %.
- *Strong media:* lips, stripes, patch and gold at 100 %.
- *What B carries:* a pooled observer reads the length of the region's mean colour vector. A coherent hue survives averaging; noise does not. Against the same shape moved to unpainted places, the backdrop scores d′ 132 / 9.5 and the face 40 / 10.
  - These d′ values come from an ideal integrator over very large regions. Read them as comparisons between designs, not as human performance.

## 9. What this standpoint is likely to get wrong

1. **The bench was kind, and is still mine.**
   - My first "faint" washes were twice the real target, and I did not notice until the conservation report said what VDZ washes are.
   - Phone semantic rendering, uneven toning, mat burn, lateral colour and textured silk surfaces are not simulated.
2. **Pooling in B is a laboratory idealisation.** The pooled d′ assumes perfect integration and a calibrated display. A conservator glancing at B on a laptop, at ×4 with ×4 noise, may see neither the wash nor its absence.
3. **Hue is read as medium.** The direction of a departure in a white-balanced, tone-mapped capture is not a pigment. Van Der Zee's thin washes could not be identified even analytically (NGA, *Facture* 7, 2025, via the peer).
4. **Display over upstream.** Most of the gains in v2 came from the reference (votes, anchors), not from pictures. The pictures matter for *seeing failure*, not for detection.
5. **Pop-out on cluttered prints.** Stains, hatch and B's ×4 speckle are heterogeneous distractors (Duncan and Humphreys 1989). Rare paint in a batch of mostly unpainted prints will be missed whatever the display (Wolfe, Horowitz and Kenner 2005).
6. **Correct promises still lend authority.** A vivid C remains persuasive even with the blank sentence under it.

## 10. How to falsify this answer

**Merge the peer's test set and mine.**
- *Prints:*
  - twelve known-unpainted period prints (warm-tone, toned, yellowed, silvered, foxed, mounted);
  - six mock-ups painted on half with transparent watercolour and photo oil at three strengths, plus graphite, tone-matched spotting and opaque white, with the application recorded on a tracing;
  - ten VDZ prints mapped by a conservator under magnification, raking light and UV.
- *Captures:* each print three times (phone default, document camera, one other device), varying position and light.
- *Observers:* 8 to 12 conservators, including at least 2 with a colour-vision deficiency. Conditions: capture alone, the TODO as written, and v2. Analysis by rating-ROC d′ and JAFROC (Macmillan and Creelman 2005; Chakraborty and Berbaum 2004).

**The answer is wrong if:**
1. **C finds unpainted colour.** In more than 2 of the 12 controls, C shows an overlay larger than a fingertip at print scale, repeated in two captures, and not explained by documented deterioration, mount or margin.
2. **Votes do not earn their place.** On the mock-ups, the voted reference fitted to the *painted* half's capture differs from the unpainted half's tone by more than 2 spreads over more than 5 % of unpainted area, or gives no fewer non-repeating overlays than the TODO's band median at equal detection (the peer's P4).
3. **The strip mispredicts.** Light and clear applications should appear in C in at least two of three captures. Faint ones should appear in B as forms to at least half the observers *at the tones where the strip shows the thin wash*, and not where it shows none. Falsified if either fails.
4. **Failures are silent.** A capture whose C is wrong shows no tell in D, C, B or the blink, and observers do not flag it, more than once in the set.
5. **CVD observers lose C.** Their d′ with C falls more than 20 % below normal observers'.
6. **Captures disagree more than paint.** Maps of one print differ between captures more than painted and unpainted areas differ. The tool then shows captures, not prints.

## 11. Retracted

1. **"Presence"**, as a name and as a promise of paint. It shows departures beyond the capture's own error. Now "Where colour departs from the print's own tone".
2. **The claim that the design finds faint washes** (cheeks 84 to 96 %, backdrop up to 82 %). Those washes were 1.7 to 2.8 units, about twice VDZ's. At about 1 unit, C shows 0 to 2 % of a backdrop wash and about 20 % of a face wash.
3. **The key as specified.** A noise-free 1.9-unit pink disc, one strength, drawn only as C would draw it: it overpromised. It is replaced by the strip's thin and clear strengths, set into this capture's own residual and shown in both B and C.
4. **Boosted's coring** (nothing below 1.5 spreads, soft knee). It suppressed thin washes. B is now linear ×4 and uncored.
5. **Picks weighted ×20 and never down-weighted.** A pick on a thin wash erased it. Replaced by examined boxes as corroborated anchors with a cross-check.
6. **That only boxes can fix majority-painted tones.** Votes of places fix the case I tested. Boxes are needed only when paint covers most *places* at a tone.
7. **The inlier-share caution in the footer.** It did not separate failures from normal captures (0.54 against 0.54 to 0.89). Replaced by the peer's tone-following check. My separate claim stands: no statistic internal to the fit can say *which* population is paint.
8. **The three-panel montage, with "As if unpainted" at natural strength as a separate file.** It was a weak tell. Replaced by D ×4 in a 2×2 montage.
9. **The separate exaggerated reference strip** (×3 at one lightness). It was weak, and it is merged into the unified strip.
10. **The soft-knee second blink frame.** Replaced by the capture ×4, consistent with a linear B.
11. **Headline numbers.** The headline false colour on the unpainted control is 0.7 % in v2 (it was 0.4 % in v1). The cost of votes is stated: broad faint washes move from C to B.

**Not retracted:**
- the median-based yardstick (§4 shows why);
- the lightness step for colour-vision deficiency;
- the edge-tolerant lookup;
- the gated scales;
- cast terms scaled with lightness. The peer reaches the same scaling.

## 12. Sources and files

**Sources:**
- *Added in v2, via the peer:*
  - Panadero, Walker and Lomax, "James Van Der Zee's Portrait Photographs", *Facture* 7 (NGA, 2025);
  - Weaver, *A Guide to Fiber-Base Gelatin Silver Print Condition and Deterioration* (2008);
  - Stulik and Kaplan, *Atlas of Analytical Signatures of Photographic Processes* (GCI, 2013);
  - the peer's run of Woodii's code on its intended input (56 % of an untinted warm-tone print flagged at k = 4), which confirms my code-reading of why Chroma mode failed.
- *Kept from v1:* Treisman and Gelade 1980; Duncan and Humphreys 1989; Healey and Enns 2012; Gleicher et al. 2011; Borland and Taylor 2007; Kovesi 2015; Machado, Oliveira and Fernandes 2009; Birch 2012; Rensink, O'Regan and Clark 1997; Mullen 1985; Kelly 1983; Eilers and Marx 1996; Rousseeuw 1984; Beaton and Tukey 1974; Hung and Berns 1995; Ottosson 2020; Macmillan and Creelman 2005; Chakraborty and Berbaum 2004; Wolfe, Horowitz and Kenner 2005.

**Files (`/home/user/xpw/45b29c/work/`):**
- `pipelines_v2.py`: votes, yardsticks, the anchor rules.
- `render_v2.py`: the 2×2 montage, D, B, strip, blink.
- `eval_v2.py`, `picks_v2.py`, `picks_v2b.py`, `picks_v2c.py`, `tone_follow.py`, `figs_v2.py`.
- `synth.py`: adds the thin and wide variants and paired captures sharing white balance.
- Results: `v2_full.json`, `v2_yard.json`, `picks_v2.json`, `picks_v2b.json`, `picks_v2c.json`.
- `figs_v2/`:
  - `montage_thin.png`, `montage_wide.png` (v2's failure, shown in pictures), `montage_wide_boxes.png`, `montage_majority.png`, `montage_control.png`;
  - `strip_*.png`, `strip_compare.png`;
  - `blink_*.png` (animated).
- v1's files are unchanged.
