<!-- Saved verbatim by the coordinator from the agent's hand-back (the harness refused the agent's own write to
/home/user/xpw/7984d2/report.md). The harness's two-space indent is removed; nothing else is changed. -->

I couldn't write `/home/user/xpw/7984d2/report.md`: the harness refuses report files from a subagent. The full report follows and can be saved to that path unchanged. Everything else (prototype, bench, tests, figures, scores) is in `/home/user/xpw/7984d2/work/`. Neither repository was changed; both `git status` checks are clean.

# Handpaint visualiser: the iterations, the plan, and a recommended design

22 November 2026. Written for the author of `handpaint_visualiser` and Woodii.

## Summary

The visualiser's job is to show where paint is, or is not, on a monochrome photograph, from whatever capture arrives. Everything else depends on one judgement made fresh for every capture: **what this print would look like here if it were bare**. Each iteration so far has got that judgement wrong in a different way:

- **v1.x and v3.0** took bare print to be absolute neutral (a\* = b\* = 0). Warm or yellowed prints and colour casts then read as paint.
- **v4.x** took it to be the median chroma of each lightness band, measured over all pixels. Paint suppresses itself that way, and chroma magnitude cannot see a blue wash over a warm print.
- **Woodii's Chroma mode** took it to be one "silver axis" from a pick, and measured departures in units of pixel noise. On a clean capture of an *unpainted* print whose image tone shifts slightly with density, Woodii's own code flags 27-58% of the print (section 3).

The plan in `TODO.md` is pointed the right way. It uses a per-tone reference and a departure *vector*, not chroma magnitude, and it removes the numbers. Tested as written, though, it flags 7-36% of bare print on typical phone captures: on colour fringes at lightness edges, on the table or wall in frame, and under mixed light. It also loses any wash that dominates a band of tones.

I built a synthetic test bench whose model none of the methods share. I ran every earlier iteration's own code on it, the plan as written, and a prototype of the design below (`work/hpv.py`, eight passing tests). The recommended design:

1. **Reference.** Automatic by default, taken as the *most common* colour at each tone: the densest cluster, not the median. A stiff robust curve runs through those colours, plus a tilt across the frame that is kept only where dark, middle and light tones agree on it. Marked bare areas are a remedy, used when the pictures show the automatic reference failed.
2. **Yardstick.** Departures are measured against how far the bare print *itself* scatters at each tone. That spread is widened at lightness edges by the capture's own fringe strength. It is kept from being widened by paint, by capping it at a smooth curve of spread against tone.
3. **Four pictures.** Original, Boosted (bare print drawn neutral grey, departures amplified), Where colour departs from bare print, and Taken as bare print. Plus the reference's own checks, in words, each saying what to do.

On the bench the automatic design shows 1-5% of bare print as colour in every case; the earlier methods range from 0% to 69%. It finds the same washes and touches as the best earlier method wherever paint does not dominate a tone. Where paint does dominate a tone, the pictures and warnings show that the reference has failed, and marking bare areas recovers part of the paint.

The explicit answer to your closing question is in section 7.

**Caveat.** All of this is on synthetic captures. No real captures were available here. The first thing to do with the rebuild is run it on real VDZ captures, including the one behind the README's montage.

---

## 1. What was examined, and how

- **The visualiser's history.** I read every version in the history, as committed:
  - `Image_Visualiser_GUI_v.1.1.py` (Dec 2025) and `v.1.2.py` (Jul 2026), a Tk GUI.
  - `Chroma Diagnostic Tool v3.0` (Aug 2026, still in the tree).
  - `Chroma_diagnoser_v4.1` as first merged (a365ea6, Aug 2026); 4.1.1 (6176d62); and 4.1.2 with `TODO.md` (4584a2f).
- **Woodii.** Chroma mode at 5b1757d: `chroma.py`, `chromarun.py`, the tab and the tests. Also its design note, the removal commit de6f9b1 with the removal note, the Chroma sections of `docs/decisions-0.4.md`, and `docs/AUTHOR-POSITIONS.md` on main.
- **The bench** (`work/synth.py`, `work/cases.py`). Woodii's own tests "share the additive-OD model with the maps, so these tests check the code, not the method". So the bench is built from things none of the methods model:
  - **Prints:** image tone that shifts with density (warm highlights, cool shadows); paper yellowed more towards its edges; foxing spots; paper texture.
  - **Paint:** transparent paint, as Beer-Lambert with a double pass, uneven like brushwork; and opaque paint.
  - **Captures:** auto white balance; mixed light (warm on one side, cool on the other); vignetting; a phone-like saturation boost and S-curve; chroma noise reduction and low-frequency colour mottle; sharpening; lateral colour; JPEG 4:2:0 at quality 60-85; veiling glare and specular spots; a wooden table around the print.
- **Ten cases:** two unpainted negative controls; a lightly painted portrait; a heavily painted portrait; blue washes over a strongly warm print; a painted sky under mixed light; a faint wash over the whole sky; a portrait on a table with glare; a heavy-JPEG capture; a print painted all over. Each keeps its ground truth.
- **Methods compared**, each on the same decoded capture:
  - v1.2's algorithm, copied verbatim;
  - v4.1.2's raw C\* and LRC paths, imported from a copy of the script;
  - Woodii's `tint_maps` in its JPEG quick-look mode, imported from a copy of `chroma.py`, given either an oracle pick of *every* bare pixel or four boxes on bare print;
  - the TODO plan, implemented as written (`work/todo_method.py`);
  - the prototype (`work/hpv.py`), automatic and with the same four boxes.
- **Scores**, used only to judge designs; the tool itself shows none:
  - the share of bare print drawn as colour present, counted 8 px or more from any paint, in L\* 12-95, not clipped, not on a foxing spot;
  - the share of each paint's core drawn as colour present.

## 2. The visualiser's iterations

| Version | What "unpainted" meant | Feature and threshold | What it got right | What failed |
|---|---|---|---|---|
| v1.1 / v1.2 (GUI) | Absolute neutral, a\* = b\* = 0, from OpenCV 8-bit Lab | C\*, with a noise floor from the histogram peak of 3×C\* (the 1% tail); tiers at the 50th and 85th percentiles of what lies above it | The three-panel montage; the boost; the idea that the substrate is the histogram's peak | A warm or yellowed print *is* the peak, so its tail is flagged: 20-69% of bare print shown where paint is light. When paint dominates, or a table is in frame, the floor rises and hides the paint (heavily painted portrait: flesh 4%, suit 20%) |
| v3.0 | As v1, in float Lab | As v1, plus Jaccard sensitivity, numeric TIFFs, area percentages | Provenance (hash, manifest, JSON) | The file in the tree does not parse: the "Textual Updates" commit removed the docstring's opening quotes. The ICC profile was never applied: profile bytes were passed to `ImageCmsProfile`, the exception fell back to plain RGB |
| v4.0 / v4.1 (Aug) | Raw C\*, and LRC: the C\* median of each L\* band over *all* pixels | Percentile-90 default, so about 10% is always flagged; 100 px component filter; three tiers | LRC is the first appearance of "bare print's colour depends on lightness", the right instinct | Untagged files decoded as ProPhoto; the white point applied twice, so neutral grey read C\* 6-14 (Woodii's review measured 10.2-14.3); as merged it did not parse (`INPUT_DIR = <INPUT PATH HERE>`). LRC suppresses itself: a wash that fills its band moves the band's median |
| 4.1.1 (Nov 7) | As 4.1 | Noise-floor default | Colorimetry and loading fixed | The core is unchanged. On the bench, raw C\* shows almost nothing of the paint: flesh tint 9%, hair 0%, painted sky 0%, blue over warm 0%. LRC: flesh 41%, hair 3%, washes in the other cases near 0. Both find strong small touches |
| 4.1.2 + TODO (today) | As 4.1 | As 4.1 | Areas, counts, statistics and numeric TIFFs removed; pictures labelled; a plan | (the plan is assessed in section 4) |

The pattern across the iterations: each version added machinery around the same weak core. That machinery was colour management, provenance, statistics, two feature spaces and sensitivity analysis. The core is the reference for "unpainted", and it was either an absolute (neutral) or a self-suppressing band median of a scalar.

Your instruction that the tool is not colorimetric is right, and it frees the rebuild. Accurate Lab values do not help when the question is "does this differ from the bare print beside it, under this light, through this phone".

C\* (chroma magnitude) has a further, separate blindness. A blue wash over a warm print *lowers* C\*, so any method built on C\* cannot see it. On the bench, v1.2, v4.1 C\* and LRC all show 0% of the blue washes in the blue-over-warm case.

## 3. Woodii's Chroma mode: compare and contrast

**What it was.**
- The input was optical density of base-normalised *linear raw* counts.
- One silver axis came from an untinted pick, and a base pick (or the brightest untinted area) gave paper white.
- The map was the off-axis OD, thresholded as a Mahalanobis distance in multiples of *pixel noise*, measured in the picks (default k = 4).
- It had an edge mask, a hue map, a palette plot, colour deconvolution, NNMF, IR and UVL references, and a JPEG quick look.
- It was about 2,800 lines, removed after its first real run. Its record leaves the cause open: "what failed on the real prints (the method, the picks, or the maps)".

**Shared ground with the visualiser.**
- A visualiser, not a measuring tool; no areas.
- A reference from the print itself; picks.
- Provenance; no material identification.
- Pictures labelled as qualitative.

**Differences.**
- **Capture:** controlled raw under copy-stand light with flats, against unruly rendered JPEGs; OD, linearity and flat-fielding are not available to the visualiser.
- **Yardstick:** pixel-noise units, against the bare print's own scatter, which includes everything that varies without paint.
- **Reference:** one straight axis through paper white, against a curve that can follow tone shifting with density.
- **Effort:** three kinds of pick before anything showed, against none.

**Why Chroma mode probably failed on real prints.** I ran Woodii's own `tint_maps` on *controlled* captures of *unpainted* prints. They were linear, with no cast, no JPEG and light noise, and had an ideal pick covering the whole print.

| Unpainted print | Light-minus-dark b\* in the capture | Woodii flags | Proposed shows |
|---|---|---|---|
| Neutral silver, white paper | — | 0.0% | 0% |
| Uniformly warm silver | — | 0.1% | 0% |
| Tone shifting with density, ×0.1 | 3.2 (mostly the paper) | 0.6% | 0% |
| ×0.25 | 3.9 | 27% | 0% |
| ×0.5 | 5.1 | 54% | 0% |
| ×1 | 7.4 | 58% | 0% |

Going from ×0.1 to ×0.25 of this tone shift changes the shadow-to-highlight b\* difference by less than one unit, invisible to the eye. It takes Woodii from 0.6% to over a quarter of the bare print flagged. Woodii's own decision record anticipated this as a "known limitation" ("in a toy model, density-dependent tone gave untinted areas a false signal about 5× a light wash"). Its tests could not catch it, because they were built from the method's own model. Real silver prints shift tone with density, especially toned or warm-tone papers, so this is the most likely cause of the bust, though it remains a hypothesis.

The same trap caught me once while building the prototype. I tried to take the spread's shape from differences between pixels 6 px apart, a pixel-noise measure. Bare-print false flags in the shadows rose to 22-51%, because the measure misses low-frequency colour mottle. The lesson carries over: **the yardstick must be the bare print's own variation, never pixel noise.**

On the unruly synthetic captures (JPEG quick look), Woodii flagged 2-29% of bare print with the oracle pick and 2-50% with four boxes. On the print painted all over it refused to run: no untinted pick was possible.

**What carries over from Woodii:**
- substrate-relative departure (its base normalisation, generalised to a per-tone reference);
- an edge guard (as the fringe term below);
- "the map says what it can see";
- labelling, provenance, and no areas;
- warnings only when you can act on them;
- tests built from a model the method does not share.

**What does not carry over:**
- OD, raw and flats;
- pixel-noise thresholds;
- IR and UVL references (moot, as you said; I read your "luminescence stuff" as these, and any controlled-capture assumption);
- deconvolution, NNMF and palette plots;
- mandatory picks.

**Your standing positions.** Several of the Woodii positions carry over directly:
- the competent operator (1);
- "if it is not easy, nobody will do it" (2);
- complexity under the surface (3);
- a utility, not a product (4);
- the app makes images and the user interprets; qualitative visibility (5);
- invariance to scale (12): fixed pixel parameters such as v4.1's 100 px filter break across capture sizes, so sizes should be relative to the picture.

Positions 8-10 are about Woodii's kit and do not apply. Position 7 applies only in spirit: the tool cannot fix glare or a coloured background, but it must say when it cannot judge.

## 4. The current plan (`TODO.md`), item by item

The TODO plan as written, measured on the bench (the share of bare print shown as colour):

| Case | TODO plan | Main cause |
|---|---|---|
| Unpainted neutral print | 7% | colour fringes at lightness edges |
| Lightly painted portrait | 9% | fringes: on bare print, 33% of pixels on moderate edges and 52% on strong edges are flagged, against 1% in flat areas |
| Unpainted, mixed light, yellowed | 16% | no change across the frame in the model |
| Portrait on a table, glare | 36% | the table, and the glare, enter the reference |
| Heavy JPEG | 11% | fringes, chroma blocks |

Its detection is good where paint is a minority of each tone: flesh 94%, small touches 100%. It loses washes that dominate a band of tones (painted sky 0%, blue over warm 2%, painted background 3%), because a band's median *is* the paint there.

| TODO item | Recommendation | Why |
|---|---|---|
| Reference: picks first, a folder-wide `picks.json`, automatic fallback | **Reverse the order: automatic by default, picks as the remedy.** Drop folder-wide picks | "If it is not easy, nobody will do it." Unruly captures do not share framing. Boxes help where the automatic reference failed (painted sky 1→48%, blue suit 2→39%, the camera case's face 24→49%) and hurt where it was right (plain portrait 3→9% false flags). A box records the bare colour in one place, and bare print varies across the frame |
| Boost panel: neutralise the substrate or keep its tone | **Neutralise** (the "boost around neutral" you liked) | Bare print drawn grey gives a crisp expectation anyone can check. Errors in the reference are amplified by the boost and show as tint on bare areas: this panel is the failure detector (section 7) |
| Drop raw C\* and LRC | **Agree** | Section 2, and the blue-over-warm case |
| Package or one script | **One importable module plus tests** | A utility; the prototype is one file of about 790 lines |
| 1 Load via LittleCMS, untagged as sRGB | Agree | 8 bits is plenty for pictures; read 16-bit through OpenCV only if Pillow cannot |
| 2 Working size about 3000 px | Agree; 2400 px is enough | About 10 s per capture at 2400 px, with every check |
| 3 CIELAB, 5 px median on a\*, b\* | Agree, but **fit in lightness-normalised chromaticity** (a\*, b\*) × 116 / (L\* + 16) | A colour cast, or a transparent wash over silver, moves it equally at every tone, and shading does not move it. Casts are then one offset, and the tilt is one plane |
| 4 Leave out what cannot be judged | Agree; **add an automatic print finder** | A table in frame cost the plan 36% false flags. With the print found, the prototype's flesh tint goes from 27% to 62% shown. The finder: colours unlike the frame's border; the largest, roughly rectangular region; else the whole frame |
| 5 Reference: per-band median; set far pixels aside and refit | **Densest colour per band, a stiff robust curve, reweighting** | A median is captured by paint that fills half a band; the densest cluster survives far more, because hand-colouring is uneven and bare print compact. Not invincible (limits, 5.8) |
| — the spread "about it in each band" | **The hardest part; three rules** (5.3) | It must be bare-print scatter, not pixel noise; widened at edges by the capture's own fringe strength; not widened by paint (the cap) |
| 6 Uneven light, optional and later | **Needed now, but only the part all tones agree on** | Mixed light is common in phone captures (the plan: 16% on the hard negative). A naive plane absorbs paint along one side; fitted in dark, middle and light thirds separately, it is kept only where they agree |
| 7 Departure vector, its length in spreads, its angle as hue | **Agree: the core improvement** | It sees washes that lower chroma |
| 8 Specks: median on the length map | Agree, **plus removing blobs under 1/100,000 of the picture** | Noise and JPEG blocks leave 5-15 px blobs; lips and earrings stay |
| Pictures, presets, footer | Agree; **add a fourth panel, "Taken as bare print"**, and actionable warnings | Section 5.4 |
| Tests | Agree; **include what the method does not model** | Woodii's lesson |

**What the plan misses entirely:** edge fringes, the largest source of false flags on the plain portrait; the background in frame; the spread's vulnerability to paint; and a way for the output to show that the reference failed.

## 5. The recommended design

### 5.1 Principles

- **One question per capture:** what would this print look like here if it were bare? Answer it from the capture alone, show the answer, and draw departures from it.
- **Default automatic; picks are a remedy.**
- **The pictures must make a wrong answer visible.**
- **No numbers on anything the user sees;** words where the tool needs to say something.
- **"Where colour departs from bare print", not "where paint is".** Stains, foxing, yellowing and glare also depart; the user interprets.

### 5.2 Pipeline (one capture)

1. **Load.** EXIF orientation; any ICC profile to sRGB by LittleCMS; untagged files as sRGB.
2. **Working size.** 2400 px long edge, area averaging. All sizes below are relative to this.
3. **Colour planes.** CIELAB; a 5 px median on a\*, b\* only. Use u = (a\*, b\*) × 116/(L\* + 16) for fitting, and a\*, b\* for pictures.
4. **What can be judged.** Inside the print (found or marked); no channel clipped (≥ 250, dilated); L\* ≥ 8. Everything else is hatched, never drawn as "no paint".
5. **Reference** (5.3). A curve T(L\*), a tilt S·(x, y), and a spread σ(L\*).
6. **Departure.** d = u − T − S·(x, y), converted back to a\*, b\* for display. Its size is z = |d| / √(σ² + (κ·g)²), where g is the local lightness gradient and κ the capture's fringe scale. Then a 5 px median on z, and tiny blobs dropped.
7. **Pictures and checks** (5.4, 5.5). A JSON record (source, hash, sidecar, which reference, sensitivity, warnings) and a run log with failures and their reasons. No result statistics anywhere.

### 5.3 The reference, in detail (as in `work/hpv.py`)

1. **Sample** up to 300,000 judgeable pixels; split L\* into bands of 2.5.
2. **Starting curve.** In each band take the densest point of the u cloud: a 2-D histogram peak refined by mean shift. Join these points with a stiff robust local-linear smoother (span 30 L\*, Tukey across bands), so that a band taken over by paint is bridged by its neighbours.
3. **Reweight, eight rounds.** Pixels beyond 3.5 spreads get no say (Tukey biweight). Each round refits three things:
   - **The tilt**, fitted in the dark, middle and light thirds separately, keeping each coefficient only where all three agree in sign, at the smallest size. A change in the light's colour shifts every tone; paint along one side holds some tones only. On the bench this kept a real mixed-light gradient (13.9 units) and cut a gradient that paint created from 4.5 to 1.0.
   - **The curve:** the weighted mean per band, then the stiff smoother.
   - **The spread:** the median distance of the pixels still in play, per band.
4. **Cap the spread.** Bare-print spread falls smoothly with lightness (roughly as a power of 116/(L\* + 16)). Fit that curve to log σ with high values distrusted, leaving out crushed blacks and floor values, and cap every band at 1.25 times it. In tones paint dominates, the spread was 1.5-4 times the bare spread. Effect: heavily painted portrait, suit 27→48% and cheeks 64→84% shown, with bare-print false flags unchanged.
5. **Fringe scale κ, fitted per capture.** It comes from the excess of the median departure over σ, binned by lightness gradient: lateral colour, sharpening and 4:2:0 vary from capture to capture. Effect: plain portrait, false flags from 9% to 3%.
6. **With picks** (boxes marked bare):
   - The boxes *correct* the automatic curve at the tones they cover: a smooth correction, carried flat beyond. Elsewhere the curve keeps the automatic shape.
   - The tilt stays automatic: three boxes cannot pin a tilt, and fitting one from them gave a wild one.
   - At tones where the picks moved the curve, the spread comes from the boxes' own scatter, scaled up by this capture's box-to-frame factor. That factor is read off the tones where the picks agree with the automatic curve.

### 5.4 Pictures (a 2×2 montage per capture, plus a footer)

| Panel | What it shows | Why it is there |
|---|---|---|
| Original | The capture | The viewer's own eyes are the final check |
| Boosted: bare print drawn neutral | L\* unchanged; chroma = departure × 4, rolling off softly before clipping, with the last unit of a\*b\* noise cored out | The most sensitive picture. It depends only on the curve, not on the spread, so it still shows a wash whose spread was widened (blue over warm, automatic: the suit is plainly blue here and absent from the next panel) |
| Where colour departs from bare print | The print in grey; colour over it, hue from the departure's angle, opacity rising smoothly from 2 to 5 spreads (low 3-6, high 1.5-3.5); hatched where not judged | A clean summary; faint shown bright, with no hard edges |
| Taken as bare print (automatic / picked) | The capture where the reference took the print as bare, dimmed elsewhere; marked boxes outlined | Shows the reference's assumption, so it can be checked |

**Footer:** the file name, "Visualisation only - not a measurement", the reference used, the sensitivity, "Hatched: not judged", then the warnings.

### 5.5 The reference's checks (words in the footer; each says what to do)

| Check | Fires when | On the bench (final code) |
|---|---|---|
| Halves disagree | Separate automatic curves for the left and right halves (then top and bottom) differ by 2 spreads or more over three neighbouring bands, after the tilt is allowed for. Names the tones | The faint sky; the painted sky under mixed light; the heavily painted portrait; blue over warm; painted all over; glare. Also fired on the unpainted split-toned, yellowed print under mixed light, where bare print really does differ side to side. Silent on the plain portrait, the neutral negative and the heavy JPEG |
| Light changes across the frame | The agreed tilt exceeds 1.5 spreads across the frame | Both mixed-light cases. Silent where paint sits on one side |
| Strongly coloured reference | Mid-tone reference chroma above 12 a\*b\* units (automatic only) | A strongly warm print with no white balance |
| Little of a tone matched | A band holding print has under 15% bare support | Fired in development runs, not in the final run |
| Picks leave out tones | Marked boxes do not reach the print's darker or lighter tones | Whenever the boxes cover few tones |
| Less than half matched | Under half the print is near the reference | Did not fire |

### 5.6 Interaction

- **No input needed:** `python hpv.py folder --out out [--sensitivity low|normal|high]`.
- **Optional sidecar** beside a capture, `<name>.bare.json`: `{"bare": [[x0,y0,x1,y1], ...], "print": [...], "exclude": [[...]]}`.
  - `bare`: areas known to be bare, ideally at a light, a middle and a dark tone;
  - `print`: overrides the finder;
  - `exclude`: a chart, a label, a hand.
- **A small marking window is still to build** (`hpv.py mark photo.jpg`; matplotlib RectangleSelector, about 40 lines). Not built or tested here, as there is no display.

### 5.7 Results on the bench

The share of **bare print** shown as colour (%); lower is better. "4 boxes" means the same boxes on bare print for both methods.

| Case | v1.2 | v4.1 C\* | v4.1 LRC | Woodii, oracle pick | Woodii, 4 boxes | TODO plan | **Proposed, auto** | Proposed, 4 boxes |
|---|---|---|---|---|---|---|---|---|
| Unpainted, neutral | 20 | 1 | 6 | 3 | 15 | 7 | **3** | 6 |
| Unpainted, split tone, yellowed, mixed light | 20 | 0 | 0 | 29 | 46 | 16 | **3** | 7 |
| Lightly painted portrait | 44 | 0 | 1 | 5 | 17 | 9 | **3** | 9 |
| Heavily painted portrait | 0 | 0 | 0 | 2 | 11 | 3 | **2** | 2 |
| Blue over warm | 2 | 0 | 1 | 13 | 31 | 6 | **2** | 2 |
| Painted sky, mixed light | 28 | 0 | 0 | 3 | 41 | 1 | **1** | 5 |
| Faint wash over the sky | 69 | 0 | 1 | 4 | 2 | 6 | **2** | 1 |
| On a table, glare | 0 | 0 | 1 | 7 | 50 | 36 | **3** | 6 |
| Heavy JPEG | 41 | 1 | 1 | 7 | 15 | 11 | **5** | 7 |

The share of each **paint** shown (%); higher is better, read with the table above.

| Case: paint | v1.2 | v4.1 C\* | LRC | Woodii, oracle | TODO | **Proposed, auto** | Proposed, 4 boxes |
|---|---|---|---|---|---|---|---|
| Portrait: flesh tint | 97 | 9 | 41 | 82 | 94 | **84** | 88 |
| Portrait: hair | 96 | 0 | 3 | 47 | 63 | **57** | 46 |
| Portrait: lips, gold touches | 100 | 78-100 | 99-100 | 20-92 | 100 | **100** | 99-100 |
| Heavy: suit | 20 | 7 | 3 | 92 | 25 | **48** | 54 |
| Heavy: painted background (light tones) | 0 | 0 | 0 | 77 | 3 | **2** | 14 |
| Blue over warm: suit | 0 | 0 | 0 | 40 | 2 | **2** | 39 |
| Painted sky (mixed light): sky | 47 | 0 | 0 | 52 | 0 | **0** | 19 |
| Faint wash over the sky | 65 | 0 | 0 | 20 | 2 | **1** | 48 |
| Glare and table: flesh tint | 2 | 2 | 6 | 78 | 88 | **62** | 67 |
| Heavy JPEG: faint flesh tint | 66 | 4 | 9 | 30 | 31 | **15** | 16 |

**Reading the tables.**
- v1.2 finds everything, along with a quarter to two thirds of the bare print.
- v4.1 is quiet but nearly blind.
- Woodii with an oracle pick of every bare pixel is the best finder, but no user can make that pick; with realistic boxes its false flags reach 50%.
- The TODO plan is close to the proposal wherever paint is a minority, and is undone by fringes, mixed light and the background.
- The proposal holds bare print at 1-5% everywhere. It gives up only the washes that dominate a tone, says so (section 7), and boxes recover part of them.

**Figures.**
- `work/fig/compare_methods.png`: what each method draws, six cases.
- `work/fig/montage_*.png`: the prototype's montages, including `blue_over_warm` and `sky_faint`, both automatic and `_picked`, and `all_painted`.

**Tests.** `work/tests/test_hpv.py`, eight tests, all passing:
- the negative controls are quiet;
- a cast is quiet;
- a wash and small touches show;
- a chroma-lowering blue wash shows, in blue;
- a cast across the frame is followed and reported;
- paint on one side is not taken for uneven light;
- a painted sky is flagged, and marked bare areas bring it out;
- the print is found on a table.

### 5.8 Known limits

- **A wash that covers most of a tone over most of the print is taken for bare print** by the automatic reference (the faint sky, the painted background, the blue suit over a warm print). In one uncontrolled capture this cannot be told from the print's own tone; only a bare area or the viewer's knowledge can settle it. The tool states its assumption, shows the signs (section 7), and takes marked bare areas.
- **Faint washes in deep shadows show weakly.** The spread is wide there.
- **Bare print that varies unevenly across the frame shows as colour departing:** edge yellowing, stains, foxing, mat burn. Honest, but not paint.
- **Veiling glare** lifts and desaturates dark tones locally. It shows as a soft patch or a wider spread; there is no glare check yet.
- **Colourless retouching** (neutral spotting, white gouache) is invisible to any colour method.
- **The strongest lateral-colour fringes** remain as thin outlines.

## 6. Revised checklist

**Decided by this analysis:**
- [ ] Automatic reference by default; `<name>.bare.json` as the remedy; no folder-wide boxes.
- [ ] The Boosted panel draws bare print neutral; four panels (5.4).
- [ ] Drop C\* and LRC; the departure vector in lightness-normalised chromaticity, sized in the bare print's spread.

**Rebuild (port from `work/hpv.py`):**
- [ ] Load, working size, planes, judgeable mask, print finder.
- [ ] Reference: densest colour per band, stiff robust curve, Tukey reweighting, tilt agreed by tone thirds, per-band spread with the cap.
- [ ] Fringe scale κ fitted per capture, and the edge term in the spread.
- [ ] Picks: curve correction at covered tones, automatic tilt, box spread × the box-to-frame factor at moved tones.
- [ ] Specks: 5 px median on z, and blobs under 1/100,000 of the picture removed.
- [ ] Pictures (×4 boost, soft roll-off, 1-unit coring; 2-5 spread ramp with presets; hatching; footer).
- [ ] Checks worded as in 5.5, each saying what to do.
- [ ] JSON record and run log (failures and their reasons); no statistics.
- [ ] Parallel batch over files.

**Housekeeping:**
- [ ] `.py` extension; version in the file and in git only; remove `Chroma Diagnostic Tool v3.0`, which does not parse.
- [ ] Keep `synth.py` and the tests, built from a model the method does not share.
- [ ] README rewritten around the four pictures and how to read them (section 7).
- [ ] **Before adding anything:** run on real VDZ captures, including one known unpainted, one painted all over, and one phone capture under mixed light; compare Boosted with Original by eye.

**Later, only if real captures ask for it:** the marking window, a glare check, speed-ups.

---

## 7. The answer to your question

### For each uncontrolled capture, how should the tool establish what the unpainted photograph looks like?

From that capture alone, as a model of the bare print's colour that the capture itself is fitted to:

1. **Never from an absolute.** Not a\* = b\* = 0, not a chart, not another capture. The print's tone, the paper's yellowing, the light's colour and the phone's processing are unknown and change with every capture.
2. **First decide what can be judged.** Only pixels inside the print count: found automatically when the frame shows a table or wall, or marked. Leave out clipped and near-black pixels, and hatch them; never draw them as "no paint".
3. **Model bare print as a colour that depends smoothly on tone, plus a gentle tilt across the frame.** Fit it in lightness-normalised chromaticity, (a\*, b\*) × 116 / (L\* + 16). A cast or a transparent wash then moves every tone alike, and shading moves none.
4. **Estimate it automatically as the most common colour at each tone:** the densest cluster in each lightness band, not its mean or median. Join these with a stiff, robust curve, so that a tone taken over by paint is bridged by its neighbours. Then give no say to pixels far from it. Keep a tilt across the frame only where dark, middle and light tones all agree on it.
5. **Measure departures against the bare print's own scatter at each tone, never pixel noise.** Widen that scatter at lightness edges by this capture's own fringe strength. Keep paint from widening it by capping each tone at the smooth curve that bare-print scatter follows with lightness.
6. **When the user marks areas known to be bare** (paper, bare photograph, ideally light, middle and dark), let them correct the curve at the tones they cover. Beyond those tones the curve keeps the automatic shape. At corrected tones the scatter comes from the boxes, scaled by this capture's box-to-frame factor.
7. **Say on the picture which reference was used:** "automatic (the most common colour at each tone)" or "your marked bare areas". Its assumption then travels with the image.

### How would someone looking at its output know when that has gone wrong?

Because the output is built so that a wrong reference shows, in four places:

1. **In the Boosted panel, bare print must come out neutral grey.** That is how the panel is drawn, and the boost amplifies any reference error fourfold. So:
   - **Bare paper or bare photograph that comes out tinted** means the reference is wrong there.
   - **Tint that follows tone**, such as all the light areas or all the shadows, means the curve is wrong at that tone.
   - **Tint that follows position**, such as one side, a corner or a gradient, means uneven light was not followed, or a painted area was taken for it.
   - **"Negative paint"** is bare areas in the *complementary* colour of a wash elsewhere at the same tone: yellowish bare sky where the sky's blue was taken in, or orange skin where a blue suit was taken in. It looks like paint; the tell is that its colour is the opposite of another area of the same tone.
   - **Something plainly coloured in the Original that comes out grey here** was taken as bare.
2. **Boosted against Where colour departs.** Boosted depends only on the reference curve; the departure map also depends on the spread. Colour visible in Boosted but absent from the departure map means the reference or its spread has taken that colour in. Read it as unresolved, not bare (blue over warm, automatic: the suit is plainly blue in Boosted and missing from the map).
3. **The Taken as bare print panel shows the assumption itself.** It goes wrong when:
   - a visibly tinted area, or one the viewer knows is painted, is lit there;
   - most of the print is dim (the reference describes little of it).
4. **The footer says it in words, with what to do.** The warnings are:
   - "the … halves of the print disagree about what bare print looks like in the lighter (middle, darker) tones";
   - "the colour of the light changes across the frame";
   - "the bare-print reference is strongly coloured";
   - "little of the … tones matched";
   - "your marked areas leave out the … tones".

   On the bench the halves warning fired in every case where the automatic reference took in a wash. It also fired on an unpainted print whose bare colour really varies side to side. It stayed silent on the plain portrait, the neutral unpainted print and the heavy JPEG.

**The remedy is the same in every case.** Mark bare areas at the tones named (and the print, if the finder missed it) and run again; the footer then reads "Reference: your marked bare areas". If no bare area can be named, because the print may be painted all over, the honest reading is the tool's stated one. The pictures then show departures from the most common colour at each tone, and a wash covering a whole tone cannot be seen in that single capture.

---

### Files

All under `/home/user/xpw/7984d2/work/`:

- `hpv.py`: the prototype, a library and a command line; tested end to end with and without sidecars in `cli_in/` and `cli_out/`.
- `tests/test_hpv.py`: eight tests, all passing.
- `synth.py`, `cases.py`, `gen_cases.py`: the bench and its ten cases, stored in `cases/`.
- Scores:
  - `results.json`: every method;
  - `eval_final.txt`: all methods, but its proposed rows predate the last fix;
  - `eval_final_proposed.txt`: the proposal after that fix.
- Copies of the earlier methods, unmodified, used for the comparison: `old_methods.py`, `todo_method.py`, `v412.py` (4.1.2), `v12_gui.py` (v1.2), `wchroma/chroma.py` (Woodii 5b1757d).
- `fig/`: the figures.
