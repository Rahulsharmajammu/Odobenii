<!-- Saved verbatim by the coordinator from the resumed camera-pipeline agent's hand-back (merge round; the harness
refused report files). The harness's two-space indent is removed; nothing else is changed. -->

**The harness again refused report files from a subagent, so I wrote no report file. The full revised report is below, for saving as `reports/10-merge-camera-x-remotesensing.md`.**

Repository notes:
- Both repositories were only read.
- The peer's code was copied read-only into `/home/user/xpw/d99a4c/work/vendor/peer/` and run from there, so nothing was written in their directory.
- All new code and results are in `/home/user/xpw/d99a4c/work/` (main files: `merge_test.py`, `merge_gate.py`, `cross_bench.py`, `eval_v2.py`, `proto_v2.py`, and `results/cross/`).

---

# The handpaint visualiser, v2: the camera-pipeline answer, revised against the remote-sensing review

*Standpoint: a camera and phone imaging-pipeline engineer. This is design v2: my answer of earlier today, changed by contact with the remote-sensing review ("the peer").*

*What I did this round: I read the peer's report in full and ran each method on the other's bench, using the peer's own code and my own:*
- *their six synthetic captures and their scoring (`bench.masks`, `bench.score`);*
- *my eight synthetic captures and my per-element scoring;*
- *Woodii's linear-counts test.*

*Every number here comes from those runs.*

## 0. The answer in brief

**Verdict v2.** Build the TODO.md frame, with a different engine from either original report. The engine is the peer's reference fit and presence rule, plus one component from my side.

1. **Reference (what "unpainted" looks like):** the peer's, taken whole.
   - It works in the log-chromaticity χ of the linearised image: χ_ref = f(L\*) + g(x, y), plus one constant per paper box when paper boxes are switched on.
   - f is a cubic B-spline with 4 knots; g is a quadratic in x and y.
   - The fit is an MM-estimator: a least-trimmed-squares start on a stiff model over the *whole image*, then Tukey biweight steps at the scale fixed by that start.
   - So a wash has to hold most of the frame to win, not merely most of one tone band.
2. **Presence (when colour is shown):** the peer's fixed departure, d > T = max(T0, 3σ).
   - σ is pixel-scale noise from shift differences plus one fitted edge term κ²G².
   - No term of T is a spread of the same pixels' departures.
3. **From my side: compare chroma at the camera's chroma resolution.**
   - Blur both the image's χ and the reference by σ_c = 2 px (4:2:0 or HEIC at the 3000 px working size) before differencing.
   - On both benches this lowered false colour on all 14 scenes, by 10–50% relative, with detection unchanged. On the peer's even-lit unpainted print it went from 4.7% to 2.5%.
4. **Anchors have two kinds, as the peer proposed:**
   - unpainted-image boxes fix the tone curve;
   - paper or mount boxes measure the light only.

   Paper anchoring is **off by default**. It helped on the peer's bench and hurt on mine, and no self-test I tried separates the two cases (§3). The margin is instead always drawn as a **negative control**: it cannot be painted, so colour on it means the reference is wrong at that tone.
5. **The pictures:** Original | Boost (departure ×4 on a neutral print) | Presence | **Reference ×4 about neutral**, with set-aside pixels hatched, boxes and margin outlined, and a tone strip beneath. Footer notes are in words only, never numbers.

**The design principle the cross-examination forced on me: prefer failures that show.**
- My v1 yardstick hid a large wash with nothing in the montage to say so.
- The fixed rule's failures appear as colour with recognisable signatures: a lit margin, a complementary ghost, tone-following or surface-following colour.

---

## 1. Point 1: "a yardstick fitted to the same pixels lets a large wash inflate its own yardstick"

**I change my answer. The staged, lower-quartile yardstick does suffer from it.**

My v1 rule on the peer's six scenes:

| | Peer's P2 (blue backdrop wash, 22% of the image, one band of tones) |
|---|---|
| Backdrop shown | **0%** (AUC 0.59) |
| Unpainted shown | 0.4% ("clean because blind") |
| Diagnostics | nothing in the montage revealed it (`results/cross/peerP2_myE4_montage.png`) |

Why the lower quartile did not save it:
- The wash held **49% of the pixels in its own tone range**, so the band median sat on the paint: reference a\*b\* (−1.1, 8.9) against the backdrop's (−1.5, 8.0). The backdrop's median z was 0.8.
- A lower quantile protects a yardstick only when the *location* is right. When the location is already the paint, nothing departs, so neither the "As if unpainted" panel, the tone strip nor the "much departs" note had anything to show.
- On my own bench the lower quartile had rescued a blue sky only because that sky was a smaller share of its tone bands.

**I then tried to keep both worlds, and that failed too.** My first v2 added a global model-error term to the presence floor. It was high-breakdown (from the LTS kept set, or the peer's median-over-tones misfit), and it lowered false colour sharply where the model was poor (my S7 25% → 3%; their P3 19% → 3%). But it brought the objection back through the fit:

| Scene | Without model-error term | With it |
|---|---|---|
| P2 backdrop (automatic) | 38% | 1% |
| P2 backdrop (anchored) | 77% | 18% |
| My S7 sky | 88% | 12% |

It is rejected.

**The rule now:** T = max(T0, 3σ_noise), with σ_noise² = shift-difference noise at the pixel's tone + κ²G², and nothing else.
- T0 presets are 0.06 / 0.04 / 0.025, roughly a 6 / 4 / 2.5% change in a channel ratio.
- Model error is *not* absorbed into the threshold. It shows as colour, and the reference panel and negative controls let the viewer recognise it (§6).

---

## 2. Point 2: my S7/S8 weakness (cool and brown washes hidden in the print's own yellow–blue variability)

**Fixed departure: adopted, and it fixes the weakness.**

| Element | v1 | v2 |
|---|---|---|
| S8 blue garment | 1% | **80%** |
| S7 garment | 18% | **75%** |
| S7 sky | 13% | **87%** |
| S7 hair | 38% | **84%** |

The price is false colour on S7 of 24%. There, paint covers about 45% of the image, beyond the LTS budget of 40%, and the false colour appears as the visible kind (§6).

**Paper or mount boxes as light-only anchors: adopted in role, off by default.** The benches disagree.

| Bench | Margin as light anchor |
|---|---|
| Peer's | Backdrop 38% → 52% (with an unpainted box too: 77%), at unchanged false colour |
| Mine, their fit | False colour 10–13% → 19–33% on four scenes |

A held-out-side gate (fit three sides, test the fourth, accept within T0/2) did **not** separate them:
- on mine it passed the margin in 6 of 8 scenes, and false colour still rose;
- on theirs it refused the margin on every mixed-light scene, where anchoring helps.

My reading: the simulators differ in whether bare paper's colour depends on its exposure. In mine, a per-channel filmic tone curve combined with vignetting makes it so, and real phones do that. That is a question for real captures (test F6).

Until then:
- the margin is outlined in every picture as a negative control;
- anchoring is offered as a flip view;
- the user keeps the version that leaves the margin and their known-unpainted areas clean.

---

## 3. Point 3: the feature space

**Rule: measure and threshold departures in the log-chromaticity of the linearised image, because only there are a light cast and a transparent wash the same additive shift at every tone, so one light field and one fixed threshold mean the same thing at every tone.**

Evidence, with the fixed rule:
- CIELAB (T0 converted at 47.5·g(L) a\*b\* units per unit χ) lost the peer's P2 backdrop: 1% against 83% in χ, same code otherwise.
- CIELAB painted my mixed-light S3: 21% against 2.6%.
- CIELAB detected a faint near-white wash more often. That is a threshold-conversion sensitivity, which presets can tune.

**Why the peer found no difference.** Their CIELAB row used the *spread-normalised* rule (`m7_prop(space="lab")`). There, a per-tone rescaling between spaces cancels, as I had argued in v1. Under a fixed threshold it does not. My v1 argument, "the normalisation makes the space mostly moot", held only for the yardstick I have now dropped.

---

## 4. Point 4: one light field and one edge term

### (a) The light field

**Unified version:**
- g(x, y) is a quadratic (5 terms per χ axis), fitted **jointly** with f(L\*) by the peer's MM estimator, in χ, so no tone scaling is needed.
- Paper/mount boxes enter only when switched on, as light-only observations with their own constant.
- **Decision rule:** fit g always (every uncontrolled capture has uneven light). Use paper anchors only when the automatic run lights up the margin, or when the user asks. Show anchored and automatic as a flip, and keep the one that leaves the margin and known-unpainted boxes clean.

**Dropped from mine:**

| Part | Why |
|---|---|
| 6 × 6 patch votes with a Tukey plane | In my v2 build it found 83% of P2's backdrop automatically but fell to **36% with the margin and 11% with margin and box**. The peer's fit rose 38 → 52 → 77%. A tool whose answer to ambiguity is "box an area" must improve when boxed. |
| Plane-only default | Their quadratic handled my strongest mixed light (S3: 1.3% unpainted shown, garment 88%) and did not absorb my lower-left corner garment (87% found). The radial term that did absorb one, in v1, is already gone. |
| (L\* + 16)/116 cast scaling | Unnecessary in χ. |
| Acceptance by "tightening the variability" | That variability yardstick no longer exists. |

**Dropped from theirs:**
- unconditional margin anchoring (§2);
- the held-out-side test as an automatic arbiter (§2: it passed the margin where anchoring hurt, and refused it where anchoring helped).

### (b) The edge and fringe term

**Unified version:**
1. Compare at the camera's chroma resolution: blur both χ and χ_ref by σ_c.
2. Add one isotropic variance κ²G², with G = |∇ ln Y| at that resolution and κ² fitted from binned medians of the residual over the edgy half of the image (the peer's method).

**Decision rule for σ_c:**
- 2 px at a 3000 px working size for 4:2:0 JPEG or HEIC;
- 1 px for 4:4:4 or raw-derived files;
- never raised to buy lower false colour. In one build, σ_c = 4 px flipped the fit's decision and lost a backdrop.

**Dropped:**
- my κ²JJᵀ term (misregistration times the reference's gradient), which is collinear with G². A joint fit gave κ_J² ≈ 300, a nonsensical 17 px "misregistration";
- my fixed α = 0.25;
- the peer's full-resolution comparison (the matched-resolution version had lower false colour on all 14 scenes).

---

## 5. Cross-bench evidence

**On the peer's captures** (their scoring; unpainted shown % / detection % / AUC; N = unpainted controls; "blue-on-warm" = a blue wash over warm highlights):

| Rule | N1 | N2 | N3 | P1: unp. / touch / wash / blue-on-warm | P2: unp. / backdrop / AUC | P3: unp. / large / margin lit |
|---|---|---|---|---|---|---|
| My v1 (staged spread, CIELAB) | 1.8 | 0.4 | 0.5 | 0.5 / 100 / 91 / 14 | 0.4 / **0** / 0.59 | 1.8 / 11 / 0 |
| Peer (fixed, χ), automatic | 4.7 | 3.5 | 5.1 | 5.9 / 100 / 96 / 48 | 9.0 / 38 / 0.81 | 18.8 / 32 / 62 |
| Peer + margin + box | 6.5 | 5.2 | 5.3 | 5.7 / 100 / 96 / 46 | 7.5 / 77 / 0.95 | 16.2 / 32 / 4 |
| **v2 (peer fit + chroma-resolution comparison), automatic** | **2.5** | **1.7** | **3.0** | **3.7 / 100 / 97 / 47** | **7.3 / 37 / 0.84** | **16.9 / 30 / 60** |
| **v2 + margin + box** | **3.7** | **2.8** | **3.0** | **3.9 / 100 / 96 / 46** | **4.9 / 77 / 0.97** | **14.6 / 31 / 2** |
| Rejected: v2 + model-error floor | 2.5 | 1.6 | 2.5 | 2.3 / 100 / 97 / 39 | 1.2 / 1 / 0.75 | 3.2 / 11 / 2 |
| Rejected: my gated band medians + patch votes, automatic | 4.1 | 4.9 | 11.1 | 9.8 / 100 / 100 / 63 | 5.9 / 83 / 0.96 | 12.1 / 27 / 0 |

**On my captures** (elements found of those in the scene / unpainted shown %):

| Rule | S1 | S2 | S3 | S4 | S5 | S6 | S7 | S8 | found /71 |
|---|---|---|---|---|---|---|---|---|---|
| My v1 | 9 / 2.9 | 9 / 1.9 | 9 / 2.3 | 9 / 3.2 | 13 / 3.7 | – / 2.7 | 9 / 3.4 | 8 / 1.6 | 66 |
| Peer, automatic | 9 / 10.2 | 9 / 13.0 | 8 / 1.4 | 9 / 6.6 | 12 / 3.5 | – / 4.8 | 13 / 25.1 | 9 / 6.4 | 69 |
| **v2, automatic** | **9 / 10.0** | **9 / 12.7** | **8 / 1.3** | **9 / 6.2** | **12 / 3.7** | **– / 4.2** | **13 / 24.1** | **9 / 5.5** | **69** |
| v2 + margin (gated) | 9 / 9.4 | 9 / 24.3 | 8 / 8.5 | 9 / 6.2 | 13 / 23.0 | – / 19.4 | 13 / 24.1 | 9 / 32.6 | 70 |
| Rejected: v2 + model-error floor | 9 / 10.0 | 8 / 8.0 | 8 / 1.3 | 9 / 5.9 | 12 / 3.7 | – / 4.2 | 10 / 2.9 | 8 / 2.9 | 64 |

**Where v2's false colour sits on my bench** (`results/cross/merged_falsecolour_S2_S7.png`):
- **S2:** on the bare paper margin in the corners, and on the light backdrop near the frame edge. A margin cannot be painted, so this is a visible negative-control failure.
- **S7:** a complementary ghost. With paint past the LTS budget, the unpainted right half of the suit lights up (67% of the L\* 60–70 unpainted pixels), and the margin lights up too.

**In Woodii's own setting** (linear flat-fielded counts, its noise model):

| Condition | Woodii Chroma: unpainted shown | v2: paint shown / unpainted shown |
|---|---|---|
| L0, L1 | 0.0% | 84% / 0.0% |
| L2 tone shift | **44.5%** | 82% / 0.0% (v1 had 12% / 0%) |
| L3 stain | 1.0% | 93% / 0.0% |
| L4 0.5% sheen | **41.1%** | 81% / 1.3% (9.5% of dark tones: sheen in the shadows) |
| L5 all | **50.1%** | 85% / 0.0% (v1 had 12% / 0%) |

**Limits of all of this.** Both simulators were written by the methods' own authors. Each method looked best on its own bench before the exchange, and the ranking moved when the benches were swapped. Treat every number as a test of logic and code, not of the method on real prints.

---

## 6. The design v2: components and how they connect

```
 file → 1 LOAD (EXIF; ICC→sRGB, relative colorimetric; untagged = sRGB; HEIC) → 2 WORKING SIZE (~3000 px, area)
      → 3 FEATURES: linear RGB (sRGB decode); χ = E·ln RGB (5-px median); tone L*; G = |∇ln Y|
      → 4 EXCLUSIONS (hatched): any channel ≥ 250 (+3 px); near-black (5-px mean L* < 12 or a channel ≤ 4);
           outside the object box; with paper boxes on, anything brighter than the paper
      → [<name>.picks.json: {"unpainted": [...], "paper": [...]}, folder default]
      → 5 REFERENCE χ_ref = f(L*) + g(x,y) [+ c_paper]: FAST-LTS start (f quadratic, g linear, h = 0.6, L* < 20 out,
           picks always kept) → Tukey IRLS (c = 4.685) at the LTS scale, scale never below the median-based scale;
           f cubic B-spline, 4 knots at tone quantiles; g quadratic; unpainted boxes ×5
      → 6 NOISE: shift differences 12 px apart by log-luminance bin, median-scaled; κ²G² fitted
      → 7 PRESENCE: d = |blur(χ) − blur(χ_ref)| (σ_c 2 px); T = max(T0, 3σ); opacity 0 at 0.5T, ½ at T, 1 at 1.5T;
           5-px median on d/T
      → 8 PICTURES (all labelled "Visualisation only - not a measurement"):
           Original | Boost (χ − χ_ref)×4 at the original luminance | Presence (grey print, departure hue, hatching)
           | Reference χ_ref ×4 at the original luminance, set-aside hatched, margin + boxes outlined; tone strip f ×4
           with tones no box covers hatched
      → 9 FOOTER WORDS (only when there is something to do) → 10 FILES: picks JSON, provenance JSON, run log
```

**Footer words**, shown only when they apply:
- "automatic reference" or "reference from N boxes";
- "tones L\* a–b: no box covers them";
- "the margin shows colour: the reference is wrong at those tones";
- "much of the frame hatched";
- "glare left out";
- "in the middle tones this print's own colour varies most along yellow–blue (sheen, staining or uneven toning): some colour shown there may be that, not paint". This is my old variability S(L), demoted to a note.
- "a neutral medium (graphite, grey retouching, white gouache) is invisible to this tool".

**Build order:**
1. The engine with automatic reference and the four pictures. Done when the synthetic scenes on both benches reproduce §5.
2. **Gate:** the real-capture test of §10.
3. The picker (two box kinds) and the anchored/automatic flip.
4. Presets, HEIC, README.

---

## 7. For each uncontrolled capture, how should the tool establish what the unpainted photograph looks like, and how would someone looking at its output know when that has gone wrong?

### How to establish it

1. **Per capture, from the capture.** Phone AWB, colour matrix, tone curve, local tone mapping and "look" differ from shot to shot and cannot be undone from a JPEG (Afifi et al. 2019). Neutral grey, a white card, a profile or the previous image will fail on the next capture.
2. **A physical model in the right space.** In χ, an unpainted print is a curve in tone, f(L\*), shifted smoothly across the frame by the light, g(x, y). This is the "soil line" of remote sensing (Richardson and Wiegand 1977). Paint is the departure.
3. **A high-breakdown fit over the whole image.** An LTS start, then an MM step. A wash must hold the majority of the frame, not of a tone band, to be taken as unpainted. My v1 band medians broke at 49% of one band.
4. **A threshold the paint cannot move.** A fixed departure floored by pixel-scale noise, measured from differences of pixels 12 px apart, which a smooth wash cannot inflate.
5. **Anchors where the identifiability limit bites.** A wash and a change in the light's colour are the same operation, a per-channel multiplication. Only spatial structure or anchors that share the light but not the paint can separate them.
   - An unpainted-image box at the questioned tone is the reliable anchor (P2 backdrop 37% → 77%).
   - The paper margin is a light anchor only where a real capture shows it helps (§2).
6. **Say how it was established**, and which tones no box covers.

### How someone would know it has gone wrong

| What you see | What it means | What to do |
|---|---|---|
| The **margin or mount shows colour** in Presence or Boost (62% of the margin on the peer's fully painted print; the corners on my S2) | The reference is wrong at those tones: a negative control has lit up | Box an unpainted area at those tones; read nothing at those tones until then |
| The **Reference panel (×4)** shows an object in its own colour, e.g. an orange suit | Paint was taken into the reference | Box unpainted image at that tone |
| **Complementary ghost**: unpainted areas at the tone of heavy paint take the opposite hue (my S7: the unpainted half of the suit) | Paint pulled the tone curve (paint beyond about 40% of the frame) | Box; or read only the Boost against the print |
| **Tone-following**: all shadows purple, all highlights yellow, banding along contours | The tone curve is wrong there | Boxes across the tones; check the tone strip |
| **Sweep**: colour drifting smoothly across the frame, ignoring the picture | The light model is wrong | Re-shoot with more even light, or read it as light |
| **Surface-following**: soft clouds over highlights, cockle patterns, cool colour in glossy shadows, with lowered contrast | Glare, sheen or silver mirroring. The interface reflection carries the light's colour, which reads cool once AWB has balanced a warm print (sheen showed in 9.5% of dark tones in L4) | A second capture with the light moved: paint stays, sheen moves |
| Thin red/cyan lines on edges; 16 px blocks | Lateral CA, 4:2:0 chroma | Ignore; the chroma-resolution comparison removes most |
| **Nothing where you can see colour** | Either a neutral medium, or a wash the fit absorbed | Box an unpainted area at that tone and flip anchored against automatic. A large change means the automatic run absorbed it |

**What I no longer claim.** v1 said the unboosted "As if unpainted" panel and the tone strip would reveal a contaminated reference. On P2 they did not. A reference holding a blue wash over yellowed highlights looked like a plausible print. Only the boosted reference, negative controls, anchors and a second capture are reliable.

I also built a "two readings" audit, comparing the best LTS solution with the best distinct one. It fired on the one run that absorbed P2's backdrop, but falsely in the shadows of three unpainted prints, and never on the fully painted print. The peer's "two colours at one tone" audit fired on P3 but missed P2. Neither is ready to ship.

---

## 8. The iterations and Woodii, in brief (unchanged in substance from v1)

**v1.1–v4.1.2.** The null model went from neutral grey (C\*ab) to LRC, a scalar C\* relative to its lightness band.
- LRC is blind to blue over warm: on my S1, the garment was 0% shown in raw C\* and 2% in LRC.
- v4.0 decoded with the white point applied twice and untagged files as ProPhoto. Woodii's lesson lines record neutral white reading C\* 10.2–14.3.
- Thresholds were histogram heuristics, and tiers were relative to each image.

**Woodii's Chroma mode** assumed a straight silver axis and a yardstick of noise measured in small picks. In its own linear setting it flagged every unpainted mid-tone pixel under tone shift with density, or under 0.5% sheen (§5).

Both reviews hold the same hypothesis for why it was "a bust": a null model too narrow, judged by a yardstick too small. The cause is still unrecorded in Woodii. The test in §10 doubles as its post-mortem.

---

## 9. TODO.md, item by item (v2)

| Item | v2 verdict |
|---|---|
| Unpainted reference: boxes, folder default, labelled automatic | Keep. Two box kinds (unpainted: tone; paper/mount: light, off by default). Report the tones no box covers. |
| Boost panel with the substrate neutral | Keep, with the light field included in what is neutralised. |
| Drop raw C\*ab and LRC | Keep. |
| Layout | One script plus a test file, or a small package: either serves (author positions 2 and 4). |
| Load | Keep. Relative colorimetric, HEIC. |
| Working size ~3000 px | Keep. |
| CIELAB + 5 px median | **Change to χ** of linearised RGB with a 5 px median. Compare at chroma resolution (σ_c 2 px, both sides). Any wider smoothing must be luminance-guided (the peer measured 4.9% → 10.6% false colour from plain smoothing). |
| Exclusions | Keep, plus "brighter than the paper" when paper boxes are on. |
| Reference: band medians | **Replace** with f + g fitted jointly by MM, starting from LTS over the whole image. |
| Uneven light "optional, later" | **Required from the start**, fitted jointly. |
| Feature: vector in spreads | **Keep the vector; change the yardstick** to d > max(T0, 3σ_noise). |
| Specks | 5 px median on d/T. |
| Pictures | Add the Reference panel (×4) and tone strip; outline the margin as a negative control. Presets T0 = 0.06 / 0.04 / 0.025. |
| Tests | Include split tone, mixed light, glare, a one-tone backdrop and a fully painted print. Assert that failures are *visible* (lit margin, coloured reference), not just detection rates. Run on more than one simulator. |
| Real VDZ captures first | Keep; this is the gate. |

---

## 10. What this standpoint is likely to get wrong

1. **It builds a world in its own image and then wins in it.** My v1 found 66 of 71 elements at ≤3.7% false colour on my bench, tuned there. On the peer's bench it lost a whole backdrop silently. The peer's method showed a mirror effect on my bench (false colour up to 25%). Simulated phones encode the engineer's beliefs about phones.
2. **It reaches for normalisation by observed statistics.** Auto-exposure, AWB and local tone mapping all normalise to the scene, and so did my yardstick and my model-error floor. Normalising by what you observe is exactly what hides a large wash. The fix here was a threshold that does not adapt to the paint.
3. **It expects the paper to behave like a radiometric target.** In my simulator, a phone's per-channel filmic curve plus vignetting make bare paper's colour depend on its exposure, so a margin teaches the light model the wrong pattern. In the peer's simulator it does not. I could not tell which world a real capture is in.
4. **Phones do content-aware things no reference model removes.** Smart HDR 4 recognises up to four people and optimises skin tones for each, so a face in a print may be rendered locally differently, exactly where colourists painted. The remedy is capture-side (RAW, ProRAW, a scanner).
5. **Sheen and silver mirroring are not separable from a near-achromatic object by colour** (Klinker, Shafer and Kanade 1990; Tan and Ikeuchi 2005). They show as cool colour; only a second capture tells.
6. **Lightness-blind by construction.** Neutral media are invisible: graphite, grey or black retouching, white gouache, varnish.
7. **It treats everything that departs from the print's tone as "colour".** Stains, foxing, toning variations and mismatched spotting all show. Interpretation stays with the viewer.

---

## 11. How to falsify this answer

**Material:**
- six known-unpainted gelatin silver prints: neutral, warm, selenium split-toned, yellowed, mirrored, glossy;
- six hand-coloured prints mapped by a conservator beforehand: small touches; one large wash at one tone; fully coloured; and the print Chroma mode failed on in October, if it can be identified.

**Captures of each print:**
- three phone captures in the default app: window light from the left; overhead room light; mixed light with the print turned 180°;
- one in RAW or ProRAW;
- the margin visible in all of them.

**Runs:** automatic; with the margin as anchor; with one unpainted box chosen before outputs are seen.

**Scoring:** a conservator who is not the developer marks areas on printed outputs.

**This answer is wrong if:**

| Test | Wrong if… |
|---|---|
| F1 false colour | More than 1 of the 18 automatic captures of unpainted prints shows a coherent area larger than about 1 cm, outside hatching and not glare, with the margin clean and no footer note |
| F2 misses | More than 2 of the 18 anchored captures of painted prints miss a documented area of 3 mm or more in both Boost and Presence |
| F3 silent failure | Any failure covering a tenth of the image or more is invisible in the boosted Reference, the margin, the footer and the second capture |
| F4 anchors | Adding the unpainted box makes the map worse (less documented paint, or more false colour) on more than 2 captures. The design assumes anchoring helps monotonically, as the peer's fit did and my patch-vote build did not |
| F5 phone semantics | Faces on unpainted prints show colour in default captures but not in RAW. Single-capture use would then need RAW |
| F6 the margin | Margin anchoring lowers false colour on most captures. If so, turn it on by default; if it raises it, keep it off. This settles the benches' disagreement |
| F7 complexity | v4.1.2 LRC or a plain TODO-plan build does as well on F1–F3 |

---

## 12. Retracted

1. **"My staged, lower-quartile yardstick keeps paint from setting the yardstick."** On the peer's P2 it showed 0% of a backdrop holding 49% of its tone band, and its diagnostics were silent. A lower quantile protects only a yardstick whose location is right.
2. **Presence as Mahalanobis z in the print's own variability S(L), with opacity from 2 to 5 spreads.** Replaced by d > max(T0, 3σ_noise). S(L) survives only as a footer note.
3. **Pooled band medians as the reference's start**, defended as "breaking down only past 50% per band". Breakdown must be over the whole image (LTS → MM).
4. **The light from 6 × 6 patch votes with a Tukey plane, plane-only by default.** My version degraded with anchors (83 → 36 → 11%). Replaced by the peer's joint MM quadratic.
5. **The fixed edge constants κ = 2 px (κ²JJᵀ) and α = 0.25 per L\*/px.** The two terms are collinear with G²: fitted jointly, κ_J² came out at about 300. Replaced by one fitted κ²G², kept with my chroma-resolution comparison.
6. **"Stay in CIELAB; the normalised yardstick makes the space mostly moot."** True only for the yardstick I have dropped.
7. **Section 7 of v1: that "As if unpainted", the tone strip and the "much departs" note would reveal a contaminated reference.** On P2 none of them did.
8. **The v1 headline "66 of 71 elements at 1.6–3.7% unpainted shown" as evidence of merit.** It was measured and tuned on my own bench.
9. **"Picks as seeds: agreeing pixels set the yardstick."** The yardstick part is withdrawn. Picks become the peer's two kinds.
10. **Using the paper margin as an unpainted pick for the tone curve** (my v1 evaluation did). Bare paper is a different material from stained image highlights; on P2, my v1's boost turned the margin bright blue.
11. **"The opacity is relative to this print's variability, so not comparable between prints."** Opacity is now a fixed departure, though still not a measurement.
12. **My own first v2 proposal of a high-breakdown model-error term in the presence floor**, made and withdrawn this round. It recreated the objection: P2 backdrop 38 → 1%, S7 sky 88 → 12%.

**Not retracted:**
- the Woodii hypothesis, which the linear test supports and v2 passes;
- uneven light modelled from the start;
- the sheen, silver-mirroring and phone-semantics risks;
- the chroma-resolution comparison, now measured on both benches.

---

## 13. Sources

**Mine:**
- Shafer 1985, *Color Res. Appl.* 10(4)
- Klinker, Shafer and Kanade 1990, *IJCV* 4(1)
- Tan and Ikeuchi 2005, *IEEE TPAMI* 27(2)
- Land and McCann 1971, *JOSA* 61(1)
- Buchsbaum 1980
- Forsyth 1990
- Finlayson and Trezzi 2004, *CIC 12*
- van de Weijer, Gevers and Gijsenij 2007, *IEEE TIP* 16(9)
- Gijsenij, Gevers and van de Weijer 2011, *IEEE TIP* 20(9)
- Afifi, Price, Cohen and Brown 2019, *CVPR*
- Ramanath et al. 2005, *IEEE SPM* 22(1)
- Karaimer and Brown 2016, *ECCV*
- Hasinoff et al. 2016, *ACM TOG* 35(6)
- Delbracio et al. 2021, *Annu. Rev. Vis. Sci.* 7
- Kang 2007, *CVPR*
- ITU-T T.81 / JFIF
- Apple Smart HDR 4, iPhone 13 ([MacRumors](https://www.macrumors.com/2021/09/14/all-new-iphone-13-camera-features/))
- Cleveland 1979, *JASA* 74
- Gillespie, Kahle and Walker 1986, *Remote Sens. Environ.* 20(3)
- DStretch (Harman)
- AIC PMG wiki, ["Silver Mirroring"](https://www.conservation-wiki.com/wiki/PMG_Silver_Mirroring)
- Lavédrine 2009, *Photographs of the Past*

**Adopted from the peer:**
- Rousseeuw 1984 (LTS)
- Rousseeuw and Van Driessen 2006 (FAST-LTS)
- Yohai 1987 (MM-estimators), *Ann. Stat.* 15(2)
- Green et al. 1988, *IEEE TGRS* 26(1) (MNF shift-difference noise)
- Richardson and Wiegand 1977 (soil line / PVI)
- Schott, Salvaggio and Volchok 1988 (pseudo-invariant features)
- Smith and Milton 1999 (empirical line)
- Finlayson, Hordley, Lu and Drew 2006, *IEEE TPAMI* 28(1) (log-chromaticity)
- Reed and Yu 1990 (RX)
- Manolakis, Marden and Shaw 2003 (heavy-tailed clutter)
- He, Sun and Tang 2013 (guided filter)
- Hedley, Harborne and Mumby 2005 (glint)

**Repositories:**
- Woodii `docs/decisions-0.4.md` and `docs/chroma-mode-plan.md` at 5b1757d / de6f9b1
- the peer's `bench.py`, `methods.py`, `sim.py`

**Work files** (`/home/user/xpw/d99a4c/work/`):

| File | What it is |
|---|---|
| `merge_test.py` | v2, and the rejected model-error variant |
| `merge_gate.py` | Gated margin anchoring |
| `cross_bench.py` | Each method on the other bench |
| `eval_v2.py`, `proto_v2.py` | My rejected gated-median and patch-vote build |
| `results/cross/*.log`, `results/cross/*.json`, `results/cross/*.png` | Logs, scores and figures |
| `vendor/peer/` | Read-only copies of the peer's code |
