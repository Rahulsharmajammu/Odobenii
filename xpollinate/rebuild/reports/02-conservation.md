<!-- Saved verbatim by the coordinator from the agent's hand-back (the harness refused the agent's own write to
/home/user/xpw/ad19d6/report.md). The harness's two-space indent is removed; nothing else is changed. -->

# Rebuilding the handpaint visualiser: what the print looks like unpainted, and how the picture shows when that is wrong

I could not write `/home/user/xpw/ad19d6/report.md`: the environment refused it ("Subagents should return findings as text, not write report files"), and I did not work around that. The full report follows. Its supporting code and images are in `/home/user/xpw/ad19d6/work/` (section 10). Both repositories were only read: no checkouts, commits or edits.

## 1. The answer in brief

**Verdict: build `TODO.md`'s core, but change how it decides what "unpainted" is, and let it show that decision.**

The plan is right where every earlier version was wrong. It measures colour as a vector departure from the print's own tone at each lightness. That replaces:
- distance from neutral (v1.1 to v4.1, "raw C\*ab");
- one chroma number per lightness band (LRC);
- distance from one straight silver axis in sensor-noise units (Woodii's Chroma mode).

Keep the vector feature, the neutralised boost, dropping C\*ab and LRC, and showing unjudgeable areas as hatched.

As written, though, the plan would fail where it matters most to a conservator, and it would fail silently:
- Its reference, the median colour in each lightness band, follows whatever covers the most pixels at that tone: silvered shadows, a large painted backdrop, a table in frame.
- Its scale is not measured on what actually varies in an uncontrolled capture: heavy-tailed, blocky JPEG error, colour fringes at edges, and the light's drift.
- Nothing in its pictures shows what it took the unpainted print to be.

**The recommended design:**

1. **Vote the tone by places, not pixels.** At each lightness band, each tile of a 10×10 grid gives one vote, its median colour. The print's own tone is everywhere; paint, stains and silvering are local.
2. **Scale departures by this capture's own scatter.** Use the 90th percentile of the distance from the expected colour, by tone, over the whole judgeable frame. Measure the camera's lateral colour and remove it, and widen the scale at what edge noise remains.
3. **Make the light's drift standard.** Fit an even drift to the votes, scaled with lightness as an illuminant change would be.
4. **Look at two scales.** A fine one finds touches such as lips and jewellery. A neighbourhood one, with its own measured scatter, finds broad faint washes.
5. **Show four pictures:**
   - **A:** the capture.
   - **B:** the print's own tone neutralised, departures amplified ×4.
   - **C:** where colour departs.
   - **D:** the print as the tool expects it unpainted, its own tone amplified ×4.

   B plus D is the capture's colour ×4. Add a tone strip, warnings in words, and one fixed sentence on what a blank means.
6. **Make picks optional anchors.** They override the automatic tone only where they disagree with it by more than the capture's own scale. Ask for six or more, spread over the frame and the tones. Allow an object box.
7. **Test against what the method does not model** (Woodii's lesson). Then run the real falsification set in section 9.

**Bench headline (synthetic, so with caveats; section 4):**
- **False colour on unpainted areas:** across seven untinted controls, the refined design shows colour on 0.00–0.07 of clean areas against 0.03–0.21 for the plan as written, and on at most 0.07 of edges against 0.10–0.31.
- **Strong touches** are shown (0.71–1.00).
- **Faint washes** of about 1.3 CIELAB units are mostly not overlaid in C, but they are visible as forms in B.
- **The cost** is small touches over detailed areas: the gilt dots on a zipper show at 0.36 against the plan's 0.90 in the hardest capture, and 0.56 at the "high" preset.
- **Woodii's own code**, on its intended raw input, flags 56% of an untinted warm-tone print at its default threshold.

**What would reverse the verdict:**
- On real captures, the unpainted print's colour varies more from place to place than from tone to tone (uneven toning, mount burn or yellowing over large areas). A per-tone reference is then the wrong model, and a neighbourhood reference is needed.
- On known-unpainted real prints, the plan as written produces no more unrepeated false colour than the voted reference. The extra machinery has then not earned its place.
- Conservators shown B and D fail to see when the reference is wrong. The visibility design has then failed.

## 2. What the tool is up against

**Colour on a "monochrome" print is not all paint.** An untouched gelatin silver print can carry colour from:
- **Image tone.** Warm-tone (chlorobromide) developing-out papers give brown-black to brown tones that shift with density.
- **Toning.** Sulfide (sepia) toning is often strongest in the light tones; selenium acts first in the densest areas.
- **The paper base.** Cream, ivory or white. The Lens Media Lab's Paperbase (Paul Messier, Yale IPCH) records base colour and gloss for about 7,000 papers.
- **Deterioration.** Gawain Weaver's *A Guide to Fiber-Base Gelatin Silver Print Condition and Deterioration* (2008; *Topics in Photographic Preservation* 13, 2009) covers fifteen forms. Among them are yellowing, fading and silver mirroring: a bluish metallic sheen in dense areas and toward the edges.
- **Local damage.** Foxing, mount and adhesive stains, tide lines and tape residues.

None of this is paint, and none of it can be told from a thin wash by colour alone. Process and toner identification is analytical, not visual. That is the premise of the Getty Conservation Institute's *Atlas of Analytical Signatures of Photographic Processes* (Stulik and Kaplan, 2013), whose silver gelatin volume treats toning as part of the process signature.

**Not all paint is colour.** Some applied media add little or no departure from the print's tone:
- graphite and retouching pencil;
- India ink;
- spotting dyes mixed to match the image;
- opaque white body colour;
- washes matched to a sepia print's own brown.

Retouching, not colouring, is much of what was applied to prints. Sarah S. Wagner's annotated bibliography for the Mellon Collaborative Workshop *Finishing Photographs: Materials and Techniques for Retouching, Hand-Coloring, Coating & Presentation* (The Met, June 2001; *TPP* 9, 118–126) is a reminder of that. Henisch and Henisch, *The Painted Photograph 1839–1914* (Penn State, 1996), is the history of overpainting.

On the bench, an opaque neutral white does show on a warm, yellowed print, because it does not carry the print's tone. On a neutral print it would not show at all. So what a blank means depends on the print.

**Van Der Zee.** The National Gallery of Art's technical study (Panadero, Walker and Lomax, "James Van Der Zee's Portrait Photographs", *Facture* 7, 2025) reports the following. I saw it only through search summaries; `nga.gov` is not reachable from this sandbox.
- He coloured prints "in oil colors and transparent water colors".
- Thin washes prevented identification of many applied colours, even with in situ analysis.
- The prints were not coated overall.
- One orange proved fugitive under microfading.
- Much retouching was on the negative, including jewellery drawn in graphite.

The targets are therefore thin transparent washes, the faintest colour there is, alongside stronger oil colour. The Met established the archive in 2021 with the Studio Museum in Harlem: about 20,000 prints and 30,000 negatives. Batch triage, before examination under magnification, raking light and UV, is the real use.

**What an uncontrolled capture does to that colour.** Every step between print and file moves faint colour:
- **Auto white balance** removes part of the paper tone and the tint. Woodii's own decision log says so: "Auto white balance would remove paper tone and part of the tint". Grey-world and grey-edge methods (van de Weijer, Gevers and Gijsenij, *IEEE TIP* 16(9), 2007) assume the scene averages to neutral.
- **Tone curves** are not sRGB-standard.
- **Mixed light** drifts in colour across the frame.
- **Glare** from phone or document-camera lights veils and clips the image.
- **4:2:0 JPEG** halves chroma resolution and leaves heavy-tailed, block-shaped error.
- **Lateral colour** leaves fringes on edges.
- **Phones render content-aware.** Smart HDR 4 (iPhone 13) is reported to optimise skin tone per person.

In a photograph of a portrait, a phone can put colour on a face that was never there, which is exactly where hand-colourists worked. On the bench, a mild version lights an unpainted face over 47% of its area. Colour in such a file is evidence only relative to other parts of the same frame. The reference must come from the capture itself, every time.

**Precedent.** The nearest working precedent is DStretch for rock art: Jon Harman's ImageJ plug-in for enhancing faint pictographs in field photographs. It applies the decorrelation stretch of Gillespie, Kahle and Walker (*Remote Sensing of Environment* 20, 1986, 209–235). Le Quellec, Duquesnoy and Defrasne describe its use in *Digital Applications in Archaeology and Cultural Heritage* 2 (2015), 55–67. Its known weakness is this project's: whole-image statistics are ruled by what is commonest. Localised DStretch (Dyson, Jalandoni and Taçon, same journal, 2026) answers by localising the statistics.

For a monochrome print the right "decorrelation" is specific. Remove the one direction the print varies along, its own tone from paper to shadow, and amplify what is left. That is the TODO's neutralised boost. The design below takes its statistics by place, not by pixel.

## 3. The earlier iterations and the plan, compared

**v1.1–v1.2, the Tk GUI (Dec 2025 to Jul 2026)**
- **"Unpainted" meant:** neutral (a\* = b\* = 0, 8-bit OpenCV Lab).
- **How much counted as colour:** a histogram of 3× chroma over the whole image. The floor is set where counts drop below 1% of the peak.
- **What the viewer got:**
  - the original;
  - a ×3 boost around neutral;
  - three opacity tiers (0.4, 0.8, 1.0) cut at the 50th and 85th percentiles of each image's own above-floor chroma;
  - a CLAHE-enhanced foreground on a 15%-grey background.
- **What went wrong:**
  - On a warm or yellowed print the histogram peak is the print's own warmth and the floor sits above it. Faint paint in the warm direction (flesh, yellow, orange) never crosses it.
  - The tiers are percentiles of each image, so every image has a "solid" tier. The README still calls it "Opaque, unmodified pigment".
- **Keep:** the montage and the simplicity.

**v3.0 (Aug 2026)**
- **"Unpainted" meant:** the same model, in float Lab.
- **How much counted as colour:** the same floor, plus Jaccard sensitivity testing.
- **What the viewer got:** numerical TIFFs, area percentages, component counts.
- **What went wrong:**
  - The measurement framing the author has since removed.
  - The file in the tree does not parse. The opening docstring quote was lost in "Textual Updates" (f95e1f8).
- **Keep:** provenance and hashes.

**v4.0/4.1 (Aug 2026), 4.1.1 (7 Nov) and 4.1.2 (22 Nov)**
- **"Unpainted" meant:** neutral (raw C\*ab), or LRC: (C\* − band median)/IQR per L\* band.
- **How much counted as colour:** the noise floor, a percentile, Otsu, or a fixed value.
- **What the viewer got:** two colour spaces, each with a montage; a 100 px component filter.
- **What went wrong:**
  - As committed, the original did not parse.
  - It applied the white point twice, so neutral read C\* 6–14.
  - It defaulted to ProPhoto and lost 16-bit data. All of this was fixed in 4.1.1.
  - LRC is scalar. A wash that shifts hue at equal chroma (pink over warm brown), or lowers chroma (blue over warm), cannot register.
  - The band median includes the paint.
  - The 100 px filter removes lips and jewellery.
  - 4.1.2 still prints the threshold in the montage footer and the console, and keeps the tiers.
- **Keep:** the move to a print-relative reference, and provenance.

**Woodii Chroma mode (built 22–28 Oct, removed 29 Oct)**
- **"Unpainted" meant:** one straight silver axis through the paper base, in optical density of linear raw counts, set from an untinted pick.
- **How much counted as colour:** k = 4 standard deviations of sensor noise (Mahalanobis distance; the slider ran to 20).
- **What the viewer got:**
  - maps of magnitude, z-score and hue on black;
  - a palette triangle;
  - colour deconvolution and NNMF;
  - IR and UVL references;
  - a disagreement map.
- **What went wrong (see below):**
  - The threshold was scaled by the sensor, not by the print.
  - The axis was rigid.
  - The workflow was heavy.
- **Keep:** a reference from the capture itself; picks; masks for what cannot be judged; the "visualiser, not measurement" stance.

**`TODO.md` (22 Nov)**
- **"Unpainted" meant:** the median (a\*, b\*) per L\* band, smoothed along L\*; from picks, or automatic.
- **How much counted as colour:** 2–5 "robust spreads".
- **What the viewer got:** original, boost (neutralised or kept), and a presence map.
- **What went wrong:**
  - The per-band median follows whatever covers the most pixels at a tone.
  - The spread is not tied to heavy-tailed or blocky error, edges or drift.
  - The reference cannot be seen.
  - A folder-wide picks file is the default.
- **Keep:** almost all of it.

**Why Woodii's Chroma mode failed: my reading.** The removal note leaves the cause open: "Open: what failed on the real prints (the method, the picks, or the maps)". Its own record already held the warnings:
- "In a toy model, density-dependent tone gave untinted areas a false signal about 5× a light wash".
- "a 0.5% reflection floor cut dense-area tint to 0.79×".
- Its tests "check the code, not the method", because their synthetic prints used the method's own exact axis.

I ran its code (commit 5b1757d) on its intended input. That is linear counts with shot and read noise under even light, a base pick on the margin, and untinted picks over the suit, backdrop and hair. These are the shares of untinted image it flags:

| Untinted print | k = 4 | k = 8 | k = 16 |
|---|---|---|---|
| Neutral, one exact axis (as in its tests) | 0.04% | 0 | 0 |
| Warm-tone paper (tone changes with density) | 56% | 35% | 15% |
| Sulfide-toned, strongest in highlights | 62% | 51% | 0% |
| Neutral, yellowed toward the edges, foxed | 15% | 3% | 0% |

The sensor noise it measured at paper was 0.0023 OD. An untinted print's own departure from one straight axis is 5–20 times that. A threshold in sensor-noise units therefore lights up any print whose tone is not perfectly uniform. Its own pre-registered criterion was under 1% of an untinted print flagged.

Add the picks it required (base, untinted, tints), seven views, IR and UV. That is the opposite of the author's "If it is not easy, nobody will do it" (`AUTHOR-POSITIONS.md`, item 2).

Where its model holds, it is sensitive. On a neutral raw print it flags the blue wash at 65% and the flesh wash at 36%. The failure was rigidity and scale, not sensitivity.

## 4. Evidence from a synthetic bench

**The simulator** (`work/sim.py`) builds a print in per-channel optical density from two bundled images: a portrait and a landscape, 1024 px plus a 5% margin. It includes:
- tone that is neutral, warm (warm mid-tones, neutral Dmax) or sulfide-like (strongest in the light tones);
- a cream base;
- yellowing, uniform and stronger toward the top and left edges;
- 25 foxing spots, an adhesive band, and silvering in dense areas near the bottom edge;
- transparent media by Beer–Lambert with a double pass: rose cheeks and lips (about 5.6 CIELAB units), a flesh wash (about 1.3), a blue backdrop wash over about 11% of the frame (about 1.3), a yellow wash on an embroidered patch (about 2.7), and six gilt dots 9 px across (about 7);
- in the "heavy" case, red flag stripes and a blue suit;
- one opaque neutral white stroke and five near-neutral spotting-dye spots.

**The capture** adds:
- the light's colour drift, vignetting, and a glare veil with a clipped hot spot;
- grey-world auto white balance, auto exposure and a non-sRGB tone curve;
- ±0.15% lateral colour, sharpening and noise;
- JPEG at quality 80 with 4:2:0 subsampling;
- optionally, a phone's face rendering (a\* +3, b\* +3.6 on the face) or a brown table around the print.

Capture noise is about 0.7 units per pixel after the 5 px chroma median.

**The methods** (`work/methods.py`):
- **v4.1.2**, called through its own functions, loaded read-only from the repository file.
- **The TODO as written:** band medians with a three-band rolling mean; the robust spread taken fairly as the Rayleigh scale, median |v|/1.1774; four automatic refits; an optional plane; the 2→5 ramp.
- **The final prototype** (`work/hpv_proto.py`).

**The score** is the share of pixels shown at opacity ≥ 0.2. It is for this comparison only; the tool reports nothing numeric.

**False colour on untinted controls**: clean areas, with edges in brackets.

| Untinted control | 4.1.2 C\*ab | 4.1.2 LRC | TODO as written | Final, automatic |
|---|---|---|---|---|
| U0 neutral, plain capture | 0.00 (0.00) | 0.25 (0.31) | 0.21 (0.28) | 0.07 (0.07) |
| U1 warm-tone | 0.00 (0.00) | 0.00 (0.00) | 0.11 (0.31) | 0.05 (0.02) |
| U2 warm, aged | 0.00 (0.00) | 0.00 (0.00) | 0.04 (0.11) | 0.00 (0.00) |
| U3 warm, full capture | 0.00 (0.01) | 0.00 (0.02) | 0.09 (0.22) | 0.06 (0.03) |
| U4 warm, aged, full capture | 0.00 (0.00) | 0.00 (0.00) | 0.08 (0.23) | 0.00 (0.01) |
| U5 toned landscape, aged, full | 0.00 (0.00) | 0.00 (0.00) | 0.03 (0.10) | 0.05 (0.01) |
| U6 as U4, with phone face rendering | 0.00 (0.00) | 0.00 (0.01) | 0.07 (0.21); face 0.42 | 0.00 (0.01); face 0.47 |

Deterioration is shown, as it should be, since it is real colour. On U4 the final version shows adhesive 0.82, foxing 0.38, silvering 0.19 and glare veil 0.21.

**Media shown, hardest painted case** (P2: warm, aged, full capture).

| Medium | 4.1.2 C\*ab | 4.1.2 LRC | TODO | Final, normal | Final, high | Final, picks as anchors |
|---|---|---|---|---|---|---|
| Rose cheeks and lips | 0.00 | 0.15 | 0.85 | 0.86 | 0.99 | 0.98 |
| Gilt dots on the zipper | 0.00 | 0.00 | 0.90 | 0.36 | 0.56 | 0.32 |
| Yellow wash on the patch | 0.01 | 0.01 | 0.42 | 0.05 | 0.12 | 0.03 |
| Flesh wash | 0.00 | 0.01 | 0.17 | 0.05 | 0.08 | 0.12 |
| Blue backdrop wash | 0.00 | 0.00 | 0.27 | 0.23 | 0.27 | 0.48 |
| Opaque white (warm print) | 0.03 | 0.32 | 0.93 | 0.88 | 0.89 | 0.89 |
| Spotting dye | 0.00 | 0.00 | 0.00 | 0.02 | 0.15 | 0.14 |
| Clean false colour (edges) | 0.00 (0.00) | 0.00 (0.00) | 0.07 (0.22) | 0.00 (0.01) | 0.01 (0.02) | 0.09 (0.02) |

On the plain capture (P1), the final normal setting shows rose 1.00, gilt 0.92, yellow 0.34 and flesh 0.26, with clean false colour of 0.03.

On the heavily painted print (P3), the automatic reference absorbs part of the paint: flesh 0.06, blue 0.06. Picks used as anchors recover it (flesh 0.45, blue 0.29), at a cost of 0.13 clean false colour.

**Repeatability: two captures of one print**, with the light's drift reversed and the glare on the other side. These are shares shown at opacity ≥ 0.5, for capture 1 / capture 2 / both. They were run on the refined prototype before its last two refinements.

| Class | Refined | TODO as written |
|---|---|---|
| Deterioration | 0.31 / 0.28 / 0.26 | 0.35 / 0.07 / 0.03 |
| Glare | 0.09 / 0.11 / 0.003 | 0.10 / 0.09 / 0.014 |
| Edges | 0.04 / 0.07 / 0.003 | 0.17 / 0.11 / 0.05 |
| Clean | 0.001 / 0.001 / 0 | 0.07 / 0.04 / 0.002 |

What is on the object repeats; what the capture made does not. Faint washes near the detection limit repeat poorly in both designs: painted areas show 0.13 / 0.04 / 0.04 in the refined version.

**Lessons from what failed on the bench:**
1. **The commonest colour by pixels as the tone** (my first try): the silvered shadows took the reference (untinted aged print 0.20 clean false colour), and so did a table in frame (0.45).
2. **A Gaussian scale** gave "confetti", multicoloured blobs of amplified JPEG error, over 21% of a clean neutral print.
3. **Overruling a tone by comparison with the scatter between tiles** fired on ordinary tone curvature. It broke the paper end of a toned print: B's margin and sky turned cyan, and D's paper came out cream against the white margin in A.
4. **Picks as the sole source** gave 0.16–0.65 false colour. Five picks leave tonal gaps, and one pick in a yellowed corner sets the tone for the whole print.
5. **Picks as plain anchors** gave 0.09–0.22. Overriding only beyond the capture's own scale brought this down to 0.01–0.13 while keeping most of the gain on the heavily painted print.
6. **A table in frame, automatic mode, no object box: a silent failure in C.** Two checks I tried for it did not separate cleanly, so I removed them:
   - split votes (places disagreeing about one tone);
   - the scale compared with local pixel noise.

   C goes quiet: rose falls to 0.38, against 0.91 with an object box. It is caught only by the pictures. D shows the print's dark mid-tones orange-brown, and B shows the whole print cyan.

**Caveats.** I wrote the simulator from the same standpoint as the design. It includes much the methods do not model, but nothing I did not think of. Its colour is camera RGB as three bands, with no spectra, and its nuisance sizes are guesses. It tests code and ideas, not the method on real prints.

## 5. The recommended design: components and how they connect

```
file ─► 1 Load ─► 2 Working size ─► 3 CIELAB ─► 4 Judgeable mask ─┐
<name>.picks.json (optional: unpainted boxes, object box) ────────┤
                                                                  ▼
             5 Reference: tone (votes) + light drift + fringe + scale (+ pick anchors)
                    │                   │                     │
                    ▼                   ▼                     ▼
          6 Departure (2 scales)   7 Self-checks       D expected unpainted ×4
                    │                   │
                    ▼                   ▼
     B neutralised ×4, C where colour departs, footer (tone strip, words) ─► 8 Files
```

**Layout.** One module (prototype: `work/hpv_proto.py`, 615 lines), a thin command line, a Tk picker and tests.

**1. Load.**
- Read with Pillow, applying EXIF orientation.
- Convert any ICC profile to sRGB with LittleCMS; take untagged files as sRGB.
- Read EXIF Make, Model and Software, so phone captures get the phone note.

**2. Working size.**
- Long edge 2400 px, by area averaging. A 12 MP phone JPEG's chroma is already at about half resolution.
- Tie the tile size, the coarse σ and the minimum pixels per vote to this size.

**3. CIELAB.** Convert sRGB to CIELAB (D65). Apply a 5 px median to a\* and b\*; leave L\* untouched.

**4. Judgeable mask.** A pixel is judgeable when it is:
- not clipped: no channel at 250 or above, grown by 1 px;
- not near-black: L\* of 8 or above;
- inside the object box.

The rest is hatched, never drawn as "no colour".

**5. Reference** (the core; section 6 says why):
- **Tone m(L\*):**
  - Bands are 2 L\* wide.
  - Voters are 10×10 tiles. A tile votes at a band if it has at least 25 pixels there (at 1.3 MP); its vote is their median (a\*, b\*). The band's tone is the median of its votes.
  - Bands are smoothed across lightness with a local-linear kernel smoother (bandwidth 6 L\*) under Tukey weights. A band is overruled only when its vote would itself show as colour, at 3 pixel scales, against the trend of its neighbours. Overruled bands are marked.
- **The light's drift:** a plane in x and y times (L\*+16)/116, fitted robustly to the votes. A change of illuminant gain moves a\*, b\* in proportion to the cube root of luminance; in log-chromaticity the shift is additive (Finlayson, Hordley, Lu and Drew, *IEEE PAMI* 28(1), 2006).
- **Lateral colour:** the colour proportional to r·∂L\*/∂r about the frame centre, with its coefficient fitted on the frame's high-gradient pixels, then subtracted. This halved the edge widening where fringes existed.
- **Scale:** by tone, the 90th percentile of the distance from the expected colour, over the whole judgeable frame.
  - Trimmed iteratively at twice the scale.
  - Taken from low-gradient pixels.
  - Floor of 0.6 units, about one 8-bit step near neutral.
  - Widened to sqrt(s² + (κ|∇L\*|)²) with κ fitted from gradient bands.
- **Picks (optional anchors):**
  - Each pick votes, at each tone where it has at least 100 pixels, its median departure from the automatic expectation.
  - The votes are smoothed across tones (8 L\*) and shrunk by one scale, so a pick moves the tone only by what the automatic reference cannot explain.
  - The correction fades 6 L\* beyond the tones the picks reach. The automatic reference stands elsewhere, dotted on the tone strip.
  - The light's drift and the scale always come from the whole frame. Picks are small and uniform; their own scatter is far too tight.

**6. Departure.**
- Compute v = (a\*, b\*) − expected.
- Fine scale: z = |v|/scale, then a 5 px median.
- Coarse scale: v averaged with a normalised Gaussian (σ = long edge/180), with its own scale measured over the reference pixels.
- Opacity is the larger of smoothstep(z, lo, hi) at the two scales. Presets for (lo, hi): normal (1, 2), low (1.25, 2.5), high (0.85, 1.7).
- The overlay's hue is v's direction at the scale that showed it, drawn vivid.

**7. Self-checks** (words in the footer, marks in the pictures):
- **Leave-out:** in automatic mode, refit on alternate tiles; with picks, leave one pick out and outline it orange in D.
- **Coverage:** tones the picks miss, at the ends or in gaps.
- **Overruled tones:** ticks on the tone strip.
- **Tone-following:** a 5 L\* range lit in more than 30% of its pixels and in more than half the tiles that contain it.
- **Fringes.**
- **Light drift.**
- **Phone capture.**

**8. Pictures and files.**
- Pictures A, B, C and D, plus the footer:
  - the file name;
  - "Visualisation only - not a measurement";
  - the reference used: automatic, or your picks (n);
  - the tone strip: paper to shadow, the expected colour ×4 above and the tone itself below, hatched where no vote reaches, ticked where overruled;
  - the warnings;
  - always this sentence: "Blank means no colour departs from the print's own tone here, in this capture. It does not mean unpainted: colourless or tone-matched media, and anything hatched, cannot show."
- `<name>.json` holds the version, the SHA-256 of the file, the preset, boost and working size, the reference source, the picks and the warnings. No counts, areas, thresholds or statistics.
- `run_log.csv` lists each file, its reference source, its warnings and any error.
- The Tk picker, like the v1.x GUI, lets the user drag numbered "unpainted" boxes and one object box. It saves `<name>.picks.json` in oriented original pixels. A folder-wide file is used only with `--fixed-stand`; positions do not carry over between handheld framings.

**Left out:**
- numeric thresholds on the command line;
- tiers and histograms;
- C\*ab and LRC;
- CLAHE;
- optical density, deconvolution, NNMF, IR and UV (raw-only ideas, moot here as the author said).

**Run time.** The prototype takes about 9 s per 1.3 MP frame without checks and 16 s with them, in numpy on a shared machine. Fitting the reference at half the working size keeps a 2400 px frame under a minute.

## 6. For each uncontrolled capture, how should the tool establish what the unpainted photograph looks like, and how would someone looking at its output know when that has gone wrong?

**Establish it per capture, from that capture alone.** "The print unpainted" is modelled as four things:
1. One colour for each lightness: the print's own tone from paper to shadow, including base, image tone, toning and overall yellowing.
2. An even drift of the light's colour across the frame.
3. The camera's lateral colour.
4. A scatter measured on the same frame, by tone, widened at edges.

The tool never borrows a reference:
- not neutral;
- not another capture's reference;
- not a folder-wide pick set on handheld captures;
- not a colour target, since its colour under a phone's rendering is not the print's.

**Where the tone comes from:**
1. **First, what can be judged.** Clipped, near-black and outside-the-box pixels are hatched and never read as "no colour".
2. **Automatically, by votes of places.** At each lightness, every tile votes its median colour, and the tone is the median vote. The assumption is printed on the picture: "at each tone, most places on the print are unpainted". Paint, stains and silvering are local, so they cannot outvote the print's tone, which is everywhere. On the bench this is what kept silvered shadows, a yellowed edge and a stain out of the reference.
3. **The conservator's picks, as anchors.** These are areas examined on the object under magnification and raking light, not chosen on screen: six or more, spread across the frame and across light, middle and dark tones, away from corners and glare, with the margin included if there is one. They pull the tone only where they disagree with the automatic reference by more than the capture's own scale. That is what is needed when a print is coloured at most places at some tone, where the automatic votes fail.
4. **What no source can establish:**
   - colourless or tone-matched media;
   - tones the picks do not reach (these fall back to the automatic reference, marked);
   - colour as faint as the capture's own scatter. About 1.3 CIELAB units does not separate per pixel. B may show it as a form; C will not.
   - a phone's content-aware colour. It cannot be told from paint; only the phone note can warn.

**How a viewer knows it has gone wrong: look at the pictures.** The tool shows its reference so that a conservator, who knows what an unpainted silver print looks like, can see it fail.

| You see | It means | Do |
|---|---|---|
| In B, areas you know are unpainted (margin, a plain suit, the backdrop) are not grey | the expected tone is wrong at those tones or places | look at D; add picks there |
| In D, the "unpainted" print has a hue no silver print has (pink or green mid-tones, orange-brown darks) | paint, a mount or a table was taken as the print's tone | object box, or picks at those tones |
| In C, colour lights a whole range of tones everywhere, crossing objects | the tone is wrong at that range (the tone-following warning) | picks at that range |
| In C, soft colour spans the frame or rings a bright spot, ignoring forms | the light's drift, or a glare veil | read with care; recapture |
| In C, thin lines of colour along edges, the same hue on the same side | the camera's fringes | ignore lines |
| In C, multicoloured confetti everywhere | noise amplified | lower the preset |
| Colour sitting exactly on a face or sky in a phone capture | the phone's rendering | scan, or recapture without it |
| An orange pick outline in D | that pick disagrees with the rest | re-examine it on the object |
| Hatched or dotted stretches of the tone strip | tones guessed, or left to the automatic reference | pick at those tones |
| Two captures disagree | made by the capture | trust only what repeats |

Every row except the phone one occurred on the bench:
- the paper-end failure (B's margin cyan, D's paper cream);
- the picks' mid-tone gap (grass lit all over C);
- a pick in a yellowed corner outlined orange;
- the table (D's darks orange-brown, with C quiet);
- the confetti;
- the glare ring.

**Read the words.** The tool states, when its checks fire:
- picks that disagree;
- tones the picks miss;
- tones overruled;
- colour that follows a range of tones;
- fringes;
- the light's drift;
- a phone capture.

These checks catch gross errors only. A pick laid on a 1.3-unit wash passed the leave-one-pick-out check, and a table in frame raised no warning at all. The pictures carry the rest.

**Keep a habit outside the tool.** Capture twice, from different positions. On the bench what was on the object repeated and what the capture made did not.

## 7. `TODO.md`, revised

**To decide first**
- [ ] **Reference** (change the plan's method; keep its intent):
  - automatic is the default, by votes of places;
  - picks are optional anchors, overriding only beyond the capture's scale;
  - the light's drift and the scale come from the whole frame;
  - an object box goes in the same `picks.json`;
  - a folder-wide picks file only with `--fixed-stand`;
  - a leave-one-pick-out check.
- [ ] **Boost:** neutralise the print's own tone (keep). Add D, the expected unpainted print ×4, so the reference can be seen.
- [ ] **Drop raw C\*ab and LRC** (agree).
- [ ] **Layout:** one module, a Tk picker, a command line and tests.

**Pipeline**
1. Load: agree. Add EXIF Make and Model for the phone note.
2. Working size: 2400 px. Tie the tiles, the coarse σ and the vote minimum to it.
3. CIELAB with a 5 px median on a\*, b\*: agree.
4. Leave out what cannot be judged: agree. Grow clipped areas by 1 px; hatch.
5. Reference: votes by tile, not the band median of pixels.
   - Local-linear robust smoothing across tones.
   - Overrule a tone only where its vote would show as colour.
   - Coverage covers interior gaps, not just the ends. The plan's "L\* the picks do not cover is extrapolated and flagged" misses gaps between picks; on the bench such a gap lit the whole grass.
6. Uneven light: standard, not "later". A plane × (L\*+16)/116, fitted to the votes and shown in D.
7. New step, lateral colour: measure the colour proportional to r·∂L\*/∂r and remove it. Widen the scale only by what edge noise remains.
8. Feature: the vector (agree). The scale is the 90th percentile of the capture's own scatter by tone, not a Gaussian spread. Add the coarse scale.
9. Specks: a 5 px median on z (agree).

**Pictures**
- Capture | B neutralised | C "Where colour departs from the print's own tone" (rename "Presence map") | D expected unpainted.
- Ramp from 1 to 2 scales, with presets.
- Footer with the tone strip, the blank sentence and the warnings.

**Housekeeping**
- [ ] `.py`; the version in the file and in git; remove v3.0, which does not parse.
- [ ] Remove the remaining numbers now:
  - the threshold in 4.1.2's montage footer and console;
  - the threshold columns in `run_log.csv`;
  - the tiers;
  - the README's "Tier 1 (Solid): Opaque, unmodified pigment" and "distinguish between faint residue and solid paint".
- [ ] Tests on synthetic prints must include what the method does not model:
  - tone that changes with density, and toning strongest in highlights;
  - edge yellowing, foxing, adhesive and silvering;
  - glare, drift and fringes;
  - 4:2:0 JPEG;
  - phone face rendering, and a table in frame.

  Add a two-capture repeat test. `work/sim.py` and `work/bench.py` are a start.
- [ ] Before adding anything else, run the falsification set in section 9.

## 8. What this standpoint is likely to get wrong

1. **Reading hue as medium.** Conservators name colour as media ("a madder cheek"). The overlay's hue is a direction in a white-balanced, tone-mapped capture, not a pigment. The NGA could not identify Van Der Zee's thin washes even analytically.
2. **Taking the eye as ground truth.** Picks chosen by eye can sit on a thin wash. On the bench, a pick on a 1.3-unit wash passed the leave-one-pick-out check. Validation needs mock-ups with a recorded application, not visual calls; the NGA used mock-ups for the same reason.
3. **Trusting one's own picks too much.** On aged prints the unpainted tone varies from place to place, so a pick represents one place. On the bench, five picks gave more false colour than the automatic votes until they were made anchors that override only beyond the capture's scale.
4. **Wanting the tool to tell stains from paint.** By colour it cannot: a faded orange residue and foxing overlap. Labelling them would break the author's position that "the app makes images; the user interprets", which I assume carries over from Woodii. I have kept the warnings to statements about the capture.
5. **Reaching for controlled capture.** Targets, cross-polarisation and raking-light sets are this standpoint's reflex. Woodii was that, and it was dropped. The brief is unruly captures, and capture is the photographer's job (position 7). "Capture twice" must stay advice, not a requirement.
6. **Assuming tone depends only on lightness.** Patchy toning, local yellowing or mat burn over large areas break both the TODO's model and mine. The tool would then show colour where the print is merely uneven, and a conservator may misread it as a wash, or dismiss a real wash as "uneven toning".
7. **Using comparison prints as references.** Prints from the same negative differ in paper, toning, exposure and age by more than a thin wash. They help interpretation; they cannot serve as the reference.
8. **Underrating the camera.** My phone face-rendering model is a guess at its size, which may differ by model and software version.
9. **Preferring false negatives.** The normal preset is conservative, and faint washes live in B. Users who read only C will understate thin washes.
10. **A bench built from this standpoint's catalogue of nuisances.** If real VDZ captures are dominated by something else, such as the sheen of textured "silk" surfaces under document-camera lights, card mounts and folders, or mat burn, the bench is silent about it.

## 9. How to falsify this answer

**The test set:**
1. **Twelve known-unpainted prints** as negative controls, from period papers where possible: warm-tone, toned, yellowed, silvered, foxed and mounted.
2. **Six mock-ups**: fibre-base gelatin silver prints, each painted on one half with transparent watercolour and photo oil at three strengths:
   - faint: barely visible at 1×;
   - light;
   - clear.

   Add graphite, a tone-matched spotting dye and an opaque white touch. Record the application on a tracing at the time.
3. **Ten Van Der Zee prints** mapped by a conservator under magnification, raking light and UV.

**The captures.** Capture each print three times, varying position and light, with no targets:
- a phone in its default mode;
- a document camera (the "visualiser");
- one other device.

**The runs.** Run the rebuilt tool automatically and with picks, and run the TODO as written, blind to the truth maps.

**The predictions:**
- **P1 (reference).** In at least 10 of the 12 controls, C shows no overlay that repeats in two or more captures and is not explained by documented deterioration, the mount or the margin.
- **P2 (detection).** The light and clear applications appear in C in at least two of three captures. The faint ones appear in B in at least two of three. Colourless and tone-matched touches are not shown on neutral prints.
- **P3 (failure is visible).** Every capture whose C is wrong shows at least one tell or warning from section 6. "Wrong" means an overlay over an unpainted, undeteriorated area larger than a fingertip at print scale, or a missed clear application. At most one silent failure in the whole set.
- **P4 (worth it).** At equal detection on the mock-ups, the voted reference gives fewer non-repeating overlays on the controls than the TODO's band median.

**This answer is falsified if:**
- **P1 fails.** The per-tone model is wrong for real prints; go to a neighbourhood reference.
- **P3 fails.** Failures are silent. This is the most serious, because it defeats the purpose of showing the reference.
- **P4 fails.** Ship the simpler TODO version, keeping D and the words.
- **Captures disagree more than paint does.** Maps of the same print differ between captures more than painted and unpainted areas differ. The tool is then showing captures, not prints.

These numbers belong to the test, not to the tool.

## 10. Sources and files

**Repositories (read only):**
- Visualiser commits: 9f4420e and 0949bdc (v1.1, v1.2), 18fbd5a and f95e1f8 (v3.0), a365ea6 (v4.1), 6176d62 (4.1.1), 4584a2f (4.1.2 and `TODO.md`).
- Woodii: 5b1757d (the Chroma code and tests); de6f9b1 (removal, `docs/chroma-mode-plan.md`, `docs/decisions-0.4.md`); `origin/main:docs/AUTHOR-POSITIONS.md`.

**Literature:**
- Stulik and Kaplan, *The Atlas of Analytical Signatures of Photographic Processes*, Getty Conservation Institute, 2013 (silver gelatin volume).
- Panadero, Walker and Lomax, "James Van Der Zee's Portrait Photographs", *Facture* 7, NGA, 2025 (seen via search summaries only).
- The Met press release on the James Van Der Zee Archive, 7 December 2021.
- Wagner (compiler), "The Hand-Coloring and Retouching of Photographic Prints: An Annotated Bibliography", *TPP* 9 (2001) 118–126.
- Henisch and Henisch, *The Painted Photograph 1839–1914*, Penn State University Press, 1996.
- Weaver, *A Guide to Fiber-Base Gelatin Silver Print Condition and Deterioration*, 2008.
- Messier, Paperbase (Lens Media Lab, Yale IPCH).
- Gillespie, Kahle and Walker, *Remote Sensing of Environment* 20 (1986) 209–235.
- Le Quellec, Duquesnoy and Defrasne, *DAACH* 2 (2015) 55–67.
- Dyson, Jalandoni and Taçon, L-DCS, *DAACH* (2026).
- Finlayson, Hordley, Lu and Drew, *IEEE PAMI* 28(1), 2006.
- van de Weijer, Gevers and Gijsenij, *IEEE TIP* 16(9), 2007.
- Apple's Smart HDR 4 per-person skin tones, as reported in the press.
- Ruifrok and Johnston (2001) and Landini et al. (2021), as used by Woodii.

`getty.edu` and `nga.gov` could not be reached from this sandbox; the summaries above came through search.

**Files in `/home/user/xpw/ad19d6/work/`:**
- `hpv_proto.py`: the prototype.
- `sim.py`, `methods.py`, `bench.py`, `final_bench.py`, `picks_rerun.py`, `woodii_exp.py`, `repeat_exp.py`: the bench.
- `proposal.py`: the first, failed try.
- `bench_out/`:
  - scores: `scores.json`, `final_scores.json`, `picks_hybrid.json`, `woodii.json`, `repeat.json`;
  - key montages: `P2_portrait_aged_capture_final_auto.png`, `U5_sepia_landscape_capture_final_auto.png`, `P6_table_final_auto.png` (the table case), `U0_neutral_clean_proposal_auto.png` (the confetti), `P2_portrait_aged_capture_proposal_badpick.png`.
