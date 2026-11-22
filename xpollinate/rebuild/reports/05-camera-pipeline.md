<!-- Saved verbatim by the coordinator from the agent's hand-back (the harness refused the agent's own write to
/home/user/xpw/d99a4c/report.md). The harness's two-space indent is removed; nothing else is changed. -->

**I could not write `/home/user/xpw/d99a4c/report.md`: the harness refused the Write call ("Subagents should return findings as text, not write report files"), and I did not route round that with a shell redirect. The full report follows; please save it to that path if the file is needed.**

Repository notes:
- Both repositories were only read with `git log` and `git show`.
- Other sessions changed both checkouts while I worked: commit 74db2bb added a `.gitignore` to the visualiser (and an ignored `__pycache__` appeared there), and Woodii's HEAD moved to 8de1245. None of this was me.
- My analysis uses visualiser 4584a2f, Woodii 5b1757d and de6f9b1, and `origin/main:docs/AUTHOR-POSITIONS.md` as I read it.
- All code and results are in `/home/user/xpw/d99a4c/work/` (615 MB).

---

# The handpaint visualiser: what the iterations teach, what to change in the plan, and what to build

*Standpoint: a camera and phone imaging-pipeline engineer. Materials read:*
- *`handpaint_visualiser` at 4584a2f: v4.1.2, README and TODO.md, and its history back to v1.1;*
- *Woodii's Chroma mode at 5b1757d, its design note, and its removal at de6f9b1;*
- *`docs/AUTHOR-POSITIONS.md`.*

*Everything I ran is in `/home/user/xpw/d99a4c/work/`.*

## 0. The answer in brief

**Verdict: rebuild along the lines of TODO.md, with six changes.** The plan's core is right: measure each pixel's colour departure from the print's own colour at that lightness, as a vector, in units of the print's own variability, with no numbers on the pictures. Each of the six changes comes from a failure I reproduced on synthetic phone captures:

1. **Take uneven light out by default, not "optional, later".**
   - Read the light's colour from a 6 × 6 grid of patches, one robust vote per patch.
   - Fit a plane across the votes robustly, so a wash covering a few patches is outvoted.
   - Keep the plane only if it clearly tightens the print's own variability.
   - Under mixed window-and-lamp light, the TODO baseline separated paint from unpainted print at chance (AUC 0.50). With the plane: 0.97.
2. **Fit the reference in stages, so paint can never set the yardstick.**
   - First a high-breakdown tone curve with an isotropic spread, taken from the *lower quartile* of distances to the curve.
   - Then the light plane.
   - Then the 2 × 2 shape of the variability, from the pixels that survived.
   - Estimated together, a large blue wash defined the yardstick and vanished into it: clear paint shown 30%, against 92% when staged.
   - With a median-distance spread, a blue sky filling much of the light tones did the same: 13% shown, against 99% with the lower quartile.
3. **Pool the tone curve across lightness bands** with robust local-linear smoothing (Cleveland's LOWESS), not a 5-band running mean.
4. **Compare chroma at the camera's chroma resolution.**
   - Phone JPEGs carry chroma at half resolution (4:2:0) after the ISP's chroma noise reduction.
   - Blur both the image's a\*b\* and the reference by σ ≈ 2 px before comparing them.
   - Widen the yardstick where the reference changes fast, or where lightness edges are strong (residual lateral chromatic aberration).
   - This removed the coloured outline round every edge: unpainted pixels shown fell from 6.3% to 3.0%.
5. **Picks are seeds, not the whole reference.**
   - They set the tone curve where they have pixels.
   - Pixels that agree with them fill the rest of the curve and set the yardstick.
   - The light is read from the whole frame.
   - A reference fitted only inside small boxes is Woodii's failure: it showed 34–49% of unpainted pixels in the unruly scenes. As seeds: 1.9–3.8%.
6. **Add a fourth picture, "As if unpainted",** plus a tone strip and plain-language notes. They let a viewer see what the tool assumed, and so when it has gone wrong (section 7).

Also:
- Drop raw C\*ab, LRC, the threshold modes, the tiers and the 100 px component filter, as the plan proposes.
- Build one script plus a test file.
- Before adding anything else, run it on real VDZ captures (section 10).

**Why, in one paragraph.** A phone capture passes through AWB, a colour matrix, a tone curve, local tone mapping, a saturation "look", chroma noise reduction, 4:2:0 subsampling and JPEG quantisation. None of these can be undone from the file. Afifi et al. (CVPR 2019) show that even a white-balance error cannot be corrected in rendered sRGB by a diagonal gain. So the tool cannot recover the print's colour. It can only estimate *what the unpainted print looks like through this capture*, which has three parts: a tone curve, a gentle colour gradient across the frame, and the print's own variability. Paint is whatever departs from that by more than the variability. Two references are wrong: sensor noise (Woodii's yardstick) and neutral grey (v1–v4's reference).

---

## 1. What I did

- **Ran the real code, not paraphrases.** Read-only copies were run in `work/vendor/`:
  - v4.1.2's `_open_working_rgb`, `_compute_lrc` and `_threshold_and_map`;
  - Woodii's `tint_maps`, both as its JPEG quick look (bin 2, k = 4, `jpeg_mask`, `eight_bit`) and on linear flat-fielded counts with its tests' noise model.
- **Built a simulator** (`sim_print.py`, `gen_scenes.py`).
  - Print:
    - silver density from a greyscale portrait (scikit-image `astronaut`, Dmax about 2.1) in a cream paper margin, with paper texture and grain;
    - optionally, image tone that shifts with density and uneven yellowing.
  - Paint:
    - transparent Beer–Lambert washes with a double pass: pink cheeks, red lips, a blue garment, a faint yellow-green wash and four small touches;
    - in the "extensive" scenes, also a blue sky, flesh, hair and a red flag.
  - Capture:
    - mixed light and falloff;
    - sheen by the dichromatic model (Shafer 1985), as a neutral veil modulated by cockle plus a hot spot;
    - lateral CA, an RGGB mosaic with Poisson–Gaussian noise and OpenCV edge-aware demosaicing;
    - shades-of-grey AWB (Finlayson and Trezzi 2004), a saturating colour matrix, optional local tone mapping, a filmic curve and sRGB encoding;
    - a saturation look, chroma noise reduction, and JPEG quality 88 at 4:2:0.
- **Built a prototype** (`visualiser_proto.py`, about 600 lines, with ablation switches). With every switch off it is TODO.md as written. Scoring is for this evaluation only; the tool shows no numbers.
- **Run time:** 10–20 s per 1536 px frame, unoptimised.

**The limit of all this.** I wrote the simulator from the same standpoint as the method: transparent washes, my own ISP model, one portrait. Passing it checks the code against my model of the world, not the method against real prints. Woodii's own test file says this of its forward models ("check the code, not the method"). Real captures decide.

---

## 2. The earlier iterations, read from the pipeline side

| Version | "Unpainted" was | Feature | Threshold | Notes |
|---|---|---|---|---|
| v1.1–1.2 (Tk GUI) | a\*=b\*=0 in OpenCV 8-bit sRGB Lab | C\*ab | Histogram peak, walk to 1% of the peak. The "×3 boost" and later ÷3 only change the bin width | Tiers at the 50th and 85th percentiles of whatever exceeds the threshold, so three tiers appear on any image, noise included |
| v3.0 | same | C\*ab (float, ICC→sRGB) | same, plus Jaccard sensitivity | More measurement apparatus on the same null |
| v4.0 | same, plus LRC | C\*ab; LRC = (C\* − band median)/IQR | percentile, Otsu, fixed | White point applied twice, and untagged files decoded as ProPhoto. Woodii's lesson lines record neutral white reading C\* 10.2–14.3 and an sRGB tint of 21.3 reading 38.4. Both bugs manufacture chroma on neutral pixels, the worst possible error for a presence tool |
| v4.1.1 | same | same | noise floor | Decoding fixed |
| v4.1.2 | same | same | same | Numbers removed |

**LRC was the right idea.** It compares a pixel with the print's own chroma at the same lightness. It fails in two ways.

- **It is a scalar.** A blue wash over a warm print moves the colour *toward* neutral, so LRC reads it as less colour. On the benign scene, v4.1.2 showed 0% of the blue garment in raw C\* and 2% in LRC, while the lips and touches were 100%.
- **Its threshold is a histogram heuristic.** It always flags something (Woodii's log: "a percentile always flags something, even on a neutral print"). It also assumes the histogram's peak is unpainted substrate.

**The boost panels boosted about a\*=b\*=0.** On a warm print that turns the paper orange-brown and buries the paint. Your "boost around neutral" is the fix, provided the neutral is the *print's own* tone.

---

## 3. Woodii's Chroma mode, and why it most likely failed

**What it got right:**
- an off-axis optical-density vector;
- normalisation to the paper base;
- an edge mask tied to the threshold;
- qualitative labels;
- linear data, in which washes add in OD.

**What it assumed** (decisions of 20–21 Oct):
- one straight silver axis per image;
- sheen and flare "minimal";
- a threshold of k = 4 in noise measured *inside the picks*;
- picks only.

**What I found running its own code in its own setting.** The setting was linear flat-fielded counts with its tests' noise model, bin 2, k = 4, and good picks. I added, one at a time, the things it set aside:

| Linear condition | Woodii: paint shown | Woodii: unpainted shown (light / mid / dark) | Proposed, same data: paint / unpainted |
|---|---|---|---|
| L0 its tests' world | 92% | 0.0% | 89% / 0.0% |
| L1 + texture and grain | 92% | 0.0% | 89% / 0.0% |
| L2 + tone shifting with density | 90% | **44.5% (46 / 100 / 9%)** | 12% / 0.0% |
| L3 + uneven yellowing | 92% | 1.0% | 89% / 0.0% |
| L4 + 0.5% neutral sheen with cockle | 92% | **41.1% (38 / 100 / 16%)** | 82% / 0.0% |
| L5 all of these | 91% | **50.1% (46 / 100 / 27%)** | 12% / 0.0% |

**Two ordinary properties of gelatin silver prints make it light up every unpainted mid-tone pixel.** They are tone that shifts with density, and half a per cent of sheen. Its own toy models had already met both: tone shift gave "a false signal about 5× a light wash", and the 0.5% floor "cut dense-area tint to 0.79×". Nobody saw that the floor also bends the axis.

**The cause is the yardstick.** Noise in a small pick is about 0.001 OD at paper white. Everything the unpainted print does beyond that, across its whole area and tonal range, then becomes "significant". The method asked "different from sensor noise?" when the question was "different from the unpainted print as this capture shows it?"

The removal note leaves the cause open ("the method, the picks, or the maps"). This is evidence for "the method's null and yardstick", not proof. It would be confirmed if the areas flagged on the 28 Oct print followed lightness bands and surface sheen. On phone-like JPEGs, Woodii's quick look showed 25–59% of unpainted pixels in every scene.

**A correction to my own first reading.** In L2 and L5 the proposal loses the blue garment, while every other element is found. I first took this to be an unavoidable "wash running along the print's tone" ambiguity. It is not:
- With picks covering the suit's mid-tones the garment appears (70% shown, median z 5.8).
- The automatic tone curve had been pulled toward the garment (a\*b\* −0.2, 8.5 against the picks' 0.9, 10.4).
- The cause: the wash fills much of a lightness range in which the print's tone also bends, and pooling cannot tell a paint bump from a real bend there.
- This is a breakdown of the automatic reference that picks repair.

---

## 4. Compare and contrast

| | Visualiser v4.1.2 | Woodii Chroma (5b1757d) | TODO.md | Proposed |
|---|---|---|---|---|
| Input | any file; analytic sRGB, Adobe and ProPhoto | linear raw, flat-fielded; JPEG as "tier C" | any file, LittleCMS → sRGB | same; HEIC via pillow-heif |
| Null | neutral grey (C\*) or band-median chroma (LRC) | one straight silver axis through the paper point | per-L\* median (a\*, b\*) | tone curve m(L), light plane, variability S(L) |
| Feature | scalar | off-axis OD vector | vector in spreads | vector, Mahalanobis in S(L), at chroma resolution |
| Yardstick | histogram tail | sensor noise in the picks | robust spread | the print's own variability, staged, lower quartile |
| Light | none | flats | optional, later | patch-vote plane, kept only if it helps |
| Edges | 100 px filter | mask tied to the threshold | 5 px chroma median | median + matched resolution + misregistration term |
| Picks | none | required | optional, else automatic | optional seeds, else automatic |
| Fails on | warm prints, blue over warm, casts | tone shifts and sheen (mid-tones 100% flagged) | mixed light, edges, contamination | cool or brown washes on glossy, stained, toned prints (section 8) |

---

## 5. The plan in TODO.md, item by item

| Item | Verdict |
|---|---|
| Reference from boxes, folder default, automatic fallback | **Keep; picks become seeds; automatic is the default**, named on the picture. |
| Boost: substrate neutral, departure amplified | **Keep.** Add coring: nothing is amplified below z ≈ 1–3. |
| Drop raw C\*ab and LRC | **Keep** (section 2). |
| One script or a package | **One script and one test file**; a small separate Tk picker. Author positions 2 and 4. |
| Load via LittleCMS; untagged = sRGB; EXIF orientation | **Keep.** Pass relative colorimetric explicitly: Pillow defaults to perceptual, which coincides for matrix profiles such as iPhones' Display P3. |
| Working size about 3000 px, area averaging | **Keep.** It also averages away demosaic false colour near Nyquist. |
| Lab, 5 px median on a\*b\* | **Keep and add** matched-resolution comparison and the edge term (S1: 6.3% → 3.0% of unpainted pixels shown). |
| Masks: glare, near-black, box | **Keep.** Glare: any channel ≥ 250, grown 3 px. Near-black: 5 px mean L\* < 7. Unclipped sheen cannot be masked (section 9). |
| Reference: band medians, smoothed; robust spread; automatic trimming | **Keep the core and change it**: pooling, staging, a lower-quartile spread, picks as seeds. |
| Uneven light: optional, later | **Make it the default and automatic** (S3: AUC 0.50 → 0.97). |
| Feature: vector length in spreads, hue from angle | **Keep**, with a 2 × 2 yardstick. Sheen and yellowing vary mostly along yellow–blue, so the yardstick stays tight in the other directions. |
| Specks: small median, not the 100 px filter | **Keep** (a 3 px median on z). All touches were found in every scene. |
| Pictures; opacity 2→5 spreads; presets; footer words | **Keep, and add "As if unpainted" and the tone strip.** |
| Synthetic tests | **Widen** them to include what the method assumes away: tone shift, sheen, mixed light, local tone mapping, an unpainted control. |
| Real VDZ captures first | **Keep, and make it the gate** (section 10). |

---

## 6. The design: components and how they connect

```
 file ─► 1 LOAD (EXIF, ICC→sRGB, untagged sRGB) ─► 2 WORKING SIZE (~3000 px, area) ─► 3 LAB (+5 px median on a*b*)
                                                                                              │
          <name>.picks.json (optional) ─────────────────┐                                     ▼
                                                        ▼                    4 MASKS: glare, near-black, outside box
     5 REFERENCE  A  tone curve m(L): 2.5 L* band medians, pooled (robust LOWESS ±14 L*); isotropic spread from the
                     lower quartile of distances (Rayleigh-scaled); 4 rounds, inliers z < 3
                  B  light plane C: 6×6 patch votes (median cast / g(L)), Tukey-robust plane; kept only if the median
                     spread falls ≥ 15 %
                  C  2×2 variability S(L) from final inliers; pooled; floor 0.5 a*b*; anisotropy ≤ 5:1
                  picks: anchor m(L) where a band has ≥ 30 picked px; agreeing pixels fill the rest and set S
                                                        │
     6 DEPARTURE  r = blur(ab, 2 px) − blur(reference, 2 px);  z² = rᵀ [S(L) + κ²JJᵀ + (α|∇L|)²I]⁻¹ r   (κ 2 px, α 0.25)
                                                        │
     ┌───────────────┬──────────────────────────┬──────┴─────────────────────┬──────────────────────────────┐
  Original     As if unpainted               Boosted around the          Presence map                 7 CHECKS → footer
               (L from capture, a*b* from    reference (L as is;         (grey print L* 32–87; hue    words; JSON holds
               reference; set-aside hatched; a*b* = 4·r·coring z 1→3)    of r at C* 58; opacity       settings, reference
               tone strip below)                                         smoothstep z 2→5; 3 px       curve, notes; no
                                                                         median on z)                 statistics
```

**The reference model.** At lightness L and frame position (x, y), the unpainted print's colour is

> ab_unpainted = m(L) + g(L)·[x y]·C, with residual ~ N(0, S(L)) and g(L) = (L\* + 16)/116.

- **g** comes from CIELAB itself. A small multiplicative cast moves a\*b\* in proportion to f(Y) = Y^(1/3), so one plane serves every tone.
- **m** is the print's tone curve. It is a curve, not Woodii's straight axis: it bends wherever the print's tone, the camera's tone curve or its colour matrix bends it.

**Why the fit is staged.**
- A high-breakdown curve and spread come first. A lower quantile of distances resists a wash filling up to about three-quarters of a band; a median distance is inflated well before 50% contamination.
- The plane is estimated only from patches voting robustly. It is accepted on whether it tightens the *unpainted* variability. The share of pixels that depart is the wrong test, because without the plane the light inflates the spread until even paint stops departing.
- The variability's shape is measured last, on the survivors.
- The plane has no radial term; one absorbed a corner wash.

**Picks.**
- The light comes from the whole frame first, because it belongs to the capture.
- Picks anchor m(L) only in bands where they have pixels.
- Pixels within 3 × (1.5 × the picks' spread) fill the rest and set the yardstick.
- Picks need not span the frame or the tonal range.

**Departure.** The phone's chroma noise reduction and 4:2:0 leave chroma at about 2 px resolution at working size, so the comparison is made at that resolution. The κ term is the soft form of Woodii's edge mask: the yardstick widens where the reference itself changes fast. The α term covers lateral CA that the ISP left behind (Kang 2007).

**Pictures.**
- *Original.*
- *As if unpainted:* the capture's L\* with the reference's colour, so the print as the tool models it unpainted.
  - Pixels it set aside (z ≥ 3) are hatched light.
  - Glare, near-black and outside-box pixels are cross-hatched grey.
  - Below it is a tone strip from dark to light, shown as it is and with its colour ×4 about neutral.
- *Boosted around the reference:* "chroma boost around neutral" with the print's own neutral. The print renders grey; departures beyond its variability are amplified ×4.
- *Presence map:* faint departures are shown bright. Opacity is relative to this print's variability, so it is not comparable between prints; the README says so.
- *Footer:* file name, "Visualisation only - not a measurement", "reference: automatic" or "picked", and notes.

**Presets** are the only user setting:

| Preset | Presence opacity ramp | Boost |
|---|---|---|
| low | z 2.5 → 6 | 3 |
| normal | z 2 → 5 | 4 |
| high | z 1.5 → 4 | 6 |

**Dropped:**
- raw C\*, LRC, the threshold modes, tiers;
- the 100 px filter, CLAHE;
- the analytic Adobe RGB and ProPhoto decoders, the histograms;
- every per-image statistic.

Keep a five-line OpenCV fallback for 48-bit TIFFs that Pillow cannot open.

**Build order:**
1. Engine with the automatic reference and the four pictures. Done when the eight synthetic scenes in `work/` behave as in section 8.
2. The checks. Done when the extensive scene prints its contamination note.
3. **Gate:** the real-capture test of section 10.
4. Tk picker writing `<name>.picks.json` (boxes and an object box); picks as seeds.
5. Presets, HEIC, README: "it shows colour that departs from this print's own tone; what that is, is for you".

---

## 7. For each uncontrolled capture, how should the tool establish what the unpainted photograph looks like, and how would someone looking at its output know when that has gone wrong?

### How to establish it

**1. Model "unpainted" per capture, from the capture alone.** The phone's AWB, matrix, tone curve, local tone mapping and look change from shot to shot, and cannot be inverted from a JPEG (Afifi et al. 2019; Karaimer and Brown 2016). So every fixed reference fails on the next capture: neutral grey, a white card, a profile, the previous image.

What survives the pipeline is internal consistency. An unpainted monochrome print maps to a thin, curved tube of colours, one colour per lightness, gently tilted across the frame by the light. The tool estimates three things:
- the tube's centre, m(L);
- its tilt, C;
- its thickness, S(L).

This is colour constancy turned round. Grey-world (Buchsbaum 1980), white-patch/Retinex (Land and McCann 1971), shades of grey (Finlayson and Trezzi 2004) and grey-edge (van de Weijer, Gevers and Gijsenij 2007) each estimate one illuminant from an assumption about the scene. Here the scene is known to be achromatic *up to the print's tone, at each lightness*. So the tool estimates a tone-conditional "illuminant" curve. Separately, Retinex-style, it estimates a smooth illuminant gradient over the frame: light varies smoothly, paint changes at boundaries.

**2. Treat paint as outliers, and keep each estimate out of the others' reach.**
- The curve comes from band medians, pooled across bands.
- The light comes from one robust vote per patch, through a robust plane, kept only if it tightens the variability.
- The yardstick comes last, from a lower quantile, on the survivors.

Gamut-mapping colour constancy (Forsyth 1990) relies on the *extremes* of the observed gamut. On a captured print the extremes are glare, noise and paint, so it is the wrong tool here.

**3. Use picks only as seeds,** when someone knows an area is unpainted. They fix the curve where they sit. The image supplies the rest, and the yardstick, which picks alone always underestimate.

**4. Never use as the reference:**
- a\*=b\*=0;
- the brightest pixel (glare carries the light's colour, not the paper's);
- the histogram peak alone;
- a white card (it makes yellowed paper read as tint, as Woodii's own test showed).

**5. Say plainly what cannot be known.** A tint over the whole print cannot be told apart from tinted paper or coloured light. That is the illuminant/reflectance ambiguity every colour-constancy method has, so it is invisible by construction, and the README must say so.

### How a viewer would know it has gone wrong

| What the viewer sees | What has gone wrong | Where to confirm |
|---|---|---|
| **"As if unpainted" doesn't look like a plausible unpainted print** (a pink cast on faces, a sky still blue, a colour sweep the original lacks) | Paint in the reference, or a wrong plane | Tone strip (×4 half) shows a hue bump at that lightness. Visibly painted areas are *not hatched*, i.e. they were taken as unpainted |
| **A coloured area that is neither hatched nor shown** | The yardstick widened by paint or by the print's own directional variability | The boosted panel shows it faintly. Footer: "in the middle tones this print's own colour varies most along yellow–blue … faint washes in those colours may not show there" (fired on S6–S8, never on S1–S5) |
| **Complementary ghost**: unpainted areas at the same lightness as heavy paint take the opposite hue | Paint pulled the tone curve (grey-world's classic failure) | Footer: "much of the middle tones departs from the reference … look for the opposite colour"; picks settle it |
| **Tone-following**: everything at one lightness lights up | Curve wrong in a band (crowded band, or a bend smoothed over) | Tone strip; hatching covers a whole lightness range |
| **Sweep**: smooth warm-to-cool gradient across the frame, ignoring edges | Light not taken out, or taken out wrongly | Footer says whether "a gentle colour gradient … was taken out"; split-frame note |
| **Surface-following**: soft-edged departures that follow cockle, a reflection or sheen in the shadows; usually *cool* on warm prints | Sheen or silver mirroring. Interface reflection carries the light's colour, which reads cool once AWB has balanced a warm print. In S8 the unclipped halo of a glare hot spot showed as a blue blob centred on the visible glare | Move the light and recapture: paint stays, sheen moves. Silver mirroring is a "bluish-metallic" sheen (AIC PMG wiki) |
| **Edge lines or 16 px blocks** | CA, 4:2:0 chroma or JPEG blocking not absorbed (capture too small or compressed) | Visible at strong edges |

**Negative controls are the cheapest check.** The margin, the mount and any known-unpainted print should come out empty. On the synthetic unpainted, unruly print (S6):
- the proposal showed 2.7% of pixels, scattered at edges and in the sheen zone;
- the TODO baseline showed 7.4%, lighting the right half's mid-tones as a region;
- Woodii's quick look showed 58.6%.

---

## 8. Evidence from the synthetic captures

**The scenes.**

| Scene | Print | Capture |
|---|---|---|
| S1 benign | constant warm tone; basic paint (cheeks, lips, blue garment, faint yellow-green wash, 4 touches) | even light colour, falloff, CA, demosaic, AWB, matrix, filmic, look, chroma NR, JPEG q88 4:2:0 |
| S2 | + tone shifting with density | as S1 |
| S3 | as S1 | mixed light (warm left, cool right) |
| S4 | as S1 | sheen veil 1.2% × cockle; hot spot |
| S5 | + sky, flesh, hair, flag (about 45% of the image painted) | as S1 |
| S6 | no paint; tone shift; yellowing | mixed light, sheen, local tone mapping |
| S7 | S5 paint + tone shift + yellowing | as S6 |
| S8 | S1 paint + tone shift + yellowing | as S6 |

**Results.** Each cell gives elements found (at least half of an element's core pixels shown) / share of unpainted pixels shown:

| Scene (elements) | v4.1.2 raw C\* | v4.1.2 LRC | Woodii quick look | TODO baseline | **Proposed** | Proposed + picks |
|---|---|---|---|---|---|---|
| S1 (9) | 5 / 1.2% | 7 / 2.7% | 4 / 27.4% | 9 / 6.3% | **9 / 2.9%** | 9 / 3.1% |
| S2 (9) | 5 / 1.3% | 6 / 1.7% | 6 / 51.1% | 7 / 4.0% | **9 / 1.9%** | 9 / 1.9% |
| S3 (9) | 5 / 1.1% | 5 / 1.5% | 5 / 56.5% | 6 / 5.0% | **9 / 2.3%** | 9 / 3.3% |
| S4 (9) | 6 / 1.1% | 7 / 2.8% | 8 / 25.2% | 8 / 6.5% | **9 / 3.2%** | 9 / 2.2% |
| S5 (13) | 5 / 0.4% | 6 / 2.0% | 9 / 26.8% | 10 / 4.4% | **13 / 3.7%** | 13 / 3.8% |
| S6 (0) | – / 0.4% | – / 0.6% | – / 58.6% | – / 7.4% | **– / 2.7%** | – / 2.7% |
| S7 (13) | 3 / 0.2% | 5 / 0.3% | 13 / 49.1% | 10 / 3.9% | **9 / 3.4%** | 11 / 3.3% |
| S8 (9) | 5 / 0.5% | 5 / 0.5% | 9 / 53.2% | 6 / 4.0% | **8 / 1.6%** | 8 / 2.4% |
| **Total (71)** | 34 | 41 | 54 | 56 | **66** | 68 |

- Woodii's high element count comes from marking a quarter to three-fifths of the unpainted print.
- v4.1.2 is quiet because it misses: the blue garment in every scene, and faint washes.
- Proposed AUC: 0.96–0.98 on S1–S5, 0.81 on S7, 0.85 on S8. The TODO baseline's: 0.50 on S3 and S8.

**What each change did** (ablation chain, same code):

| Step | Change | Effect |
|---|---|---|
| D → E0 | matched-resolution comparison + edge term | S1 unpainted shown 6.3 → 3.0%; S4 6.5 → 4.8% |
| E0 → E2 | staged 2×2 yardstick + pooling | S1 garment 78 → 93%; S4 garment 34 → 83%; S6 unpainted 6.4 → 2.9% |
| E2 → E3 | light plane | S3 garment 1 → 89% (AUC 0.65 → 0.97); S8 AUC 0.67 → 0.85; plane declined on S1 and S5 |
| E3 → E4 | lower-quartile spread | S5 sky 13 → 99%, skin 54 → 92%, hair 62 → 83%; unpainted 2.8 → 3.7% |
| E4 → + picks | picks as seeds | S7 hair 38 → 64%, faint wash 48 → 61% |

**Versions that failed on the way:**
- an unstaged 2 × 2 yardstick: S1 clear paint 30%;
- a plane fitted in round one: it absorbed the garment;
- plane acceptance by "fewer departing": it rejected the plane everywhere, including where it was needed;
- a reference from picks only: 34–49% of unpainted pixels shown in S3, S6, S7 and S8;
- picks anchoring the light estimate: S3 garment 2%.

**Remaining misses (5 of 71), all on the glossy, stained, toned print under mixed light:**
- S7: garment 18%, sky 13%, hair 38%, faint wash 48%;
- S8: garment 1%.

There, the print's own variability runs along yellow–blue (sd about 4 a\*b\* along it, against 1.3 across it), and the cool and brown washes sit at z 1.3–1.7 inside it. The footer says so, and the boosted panel shows the garment faintly. Also in S8, the unclipped halo of the glare hot spot reads blue: a false positive that a viewer can recognise by its shape.

**Files:**
- montages: `work/results/S3_mixed_light__final_montage.png`, `S5_extensive__final_montage.png`, `S8_basic_unruly__final_montage.png`, and `<scene>__<method>.png` per method;
- scores: `results/elements.json`, `results/woodii_linear.json`.

---

## 9. What this standpoint is likely to get wrong

1. **It models the capture, not the object.** Everything that departs from the print's own tone becomes "colour":
   - partial toning, retouching and spotting media;
   - foxing, tape and adhesive stains, mat burn;
   - silver mirroring and bronzing, deteriorated coatings.

   VDZ prints were routinely retouched. Spotting dyes are matched to the print's tone, so they mostly vanish, but mismatched spotting will show. The tool must say "departs from this print's own tone", never "paint", and leave the reading to the viewer (author position 5).
2. **Phones do content-aware things that no per-capture reference removes.** Apple's Smart HDR 4 (iPhone 13) "recognises up to four people … and optimises … skin tones for each", and Google's Real Tone tunes white balance and exposure for skin. Faces *in a print* may count as people. If they do, the rendering changes locally, exactly where hand-colourists worked: cheeks and lips. One curve plus a plane cannot absorb that. I could not test it (no phone here, and no published test on photographs of photographs). The remedy is a capture choice, RAW/Pro mode or a scanner, which test F4 below checks.
3. **Sheen cannot be modelled away.** The dichromatic separations need body colour to differ from the light's colour: Klinker, Shafer and Kanade 1990; Tan and Ikeuchi 2005. On a near-achromatic print the two nearly coincide. Only clipped glare is masked. Partial sheen on glossy, cockled or mirrored prints hides cool washes and creates cool false positives (S8). Cross-polarisation is this standpoint's reflex answer, but handheld phones cannot do it and capture is the photographer's job, so this is a stated limit, not a fix.
4. **Robust statistics have breakdown points.** A print painted nearly all over defeats medians, pooling and patch votes alike. The tool then shows the unpainted remnants in the complementary colour, or shows nothing. The notes catch "much departs"; nothing catches an all-over wash.
5. **It is lightness-blind by construction.** Neutral media are invisible: graphite, grey retouching, white gouache highlights, varnish.
6. **Sensitivity is not uniform, and the map does not show that.**
   - The tone curve's shoulder compresses chroma in the highlights.
   - Quantisation and noise widen the yardstick in the shadows.
   - The JPEG chroma tables in my captures were coarse in the higher-frequency terms (24 against luma's 10–15), so broad washes survive in block means but the edges of fine touches do not.

   Strength is therefore not comparable across tones or captures.
7. **The urge to add machinery.** Every refinement here was added because a synthetic test failed. That is how ISP tuning goes, and also how Chroma mode reached 2,800 lines and failed on its first real print. Ship the automatic reference first; add only what a real capture asks for. In S2 the plane was kept although the light was even. It helped, but its note had to be reworded to "a gentle colour gradient … (light, or anything else that varies smoothly)".
8. **Picks assume someone knows where paint is not.** Often nobody does, which is why the tool is being used. A pick holding faint paint anchors the curve to paint.

---

## 10. How to falsify this answer

**The test.**
- **Prints:** ten real VDZ-period prints.
  - Five hand-coloured, with the paint mapped beforehand by a conservator under magnification, raking light and UV, independently of the tool.
  - Five known to be unpainted.
  - Include a warm or partly toned print, a semi-gloss or ferrotyped print, a print with silver mirroring, and a stained print.
- **Captures of each print:**
  - two with a phone in default mode, handheld, by two different people, in a room with a window on one side;
  - one in RAW/Pro mode, or on a scanner.
- **Procedure:** run the rebuilt tool automatically, without picks. A second conservator, blind to the paint maps, marks every region on each presence map that they would call paint.

**This answer is wrong if:**
- **F1:** on two or more of the unpainted prints, the reader marks a coherent region (a face, a background, a stripe, a corner) while neither the footer nor "As if unpainted" shows anything amiss.
- **F2:** on two or more of the painted prints, a mapped region visible to the eye in the capture is not marked, and nothing in the montage explains why (no ghost, no tinted reference or strip, no note).
- **F3:** the two default captures of one print lead to different marked *places*, not just different strengths.
- **F4:** a face in an unpainted portrait print is marked in the default capture but not in the RAW or scanner capture. Phone semantics would then need a capture rule, contradicting the claim that a per-capture reference suffices.
- **F5:** v4.1.2's LRC does as well by the same blind reading.

**A cheaper first pass:** unpainted prints only, two phone captures each. That tests F1 and F3 in an afternoon.

**What would reverse individual choices** without sinking the design:
- If the plane is kept where nobody sees a gradient, make it opt-in.
- If the 2 × 2 yardstick makes no visible difference on real prints, use the isotropic one.
- If picks are never needed, leave out the picker.

---

## 11. Sources

**Colour constancy and reflection**
- Shafer 1985, *Color Res. Appl.* 10(4) 210–218.
- Klinker, Shafer and Kanade 1990, *IJCV* 4(1) 7–38.
- Tan and Ikeuchi 2005, *IEEE TPAMI* 27(2) 178–193.
- Land and McCann 1971, *JOSA* 61(1) 1–11.
- Buchsbaum 1980, *J. Franklin Inst.* 310(1) 1–26.
- Forsyth 1990, *IJCV* 5(1) 5–35.
- Finlayson and Trezzi 2004, "Shades of gray and colour constancy", *IS&T CIC 12*, 37–41 (L6 norm best).
- van de Weijer, Gevers and Gijsenij 2007, "Edge-based color constancy", *IEEE TIP* 16(9).
- Gijsenij, Gevers and van de Weijer 2011, *IEEE TIP* 20(9) 2475–2489.
- Barron and Tsai 2017, "Fast Fourier Color Constancy", *CVPR*.
- Afifi, Price, Cohen and Brown 2019, "When color constancy goes wrong", *CVPR*.

**Camera and phone pipelines**
- Ramanath et al. 2005, *IEEE SPM* 22(1) 34–43.
- Karaimer and Brown 2016, *ECCV*.
- Brooks et al. 2019, "Unprocessing images for learned raw denoising", *CVPR*.
- Hasinoff et al. 2016 (HDR+), *ACM TOG* 35(6).
- Mertens, Kautz and Van Reeth 2007, "Exposure fusion".
- Delbracio, Kelly, Brown and Milanfar 2021, *Annu. Rev. Vis. Sci.* 7.
- Gunturk et al. 2005, *IEEE SPM* 22(1).
- Kang 2007 (lateral CA), *CVPR*.
- ITU-T T.81 / JFIF (4:2:0, Annex K tables).
- Apple iPhone 13 Smart HDR 4 ([MacRumors](https://www.macrumors.com/2021/09/14/all-new-iphone-13-camera-features/), [Trusted Reviews](https://www.trustedreviews.com/explainer/what-is-ios-smart-hdr-4264112)).
- Google Real Tone ([Google Store](https://store.google.com/au/magazine/inclusive-photography-real-tone/?hl=en-GB)).

**Statistics, enhancement and unmixing**
- Cleveland 1979, *JASA* 74(368) 829–836.
- Beaton and Tukey 1974, *Technometrics* 16(2) (biweight).
- Rousseeuw and Van Driessen 1999, *Technometrics* 41(3) (FAST-MCD, the heavier alternative).
- Gillespie, Kahle and Walker 1986, *Remote Sens. Environ.* 20(3) (decorrelation stretch).
- Harman, DStretch for ImageJ ([dstretch.com](https://dstretch.com/)): the nearest precedent, faint pigment from uncontrolled field photographs. Its global stretch cannot condition on lightness.
- Ruifrok and Johnston 2001, *AQCH* 23(4).
- Landini, Martinelli and Piccinini 2021, *Bioinformatics* 37(10).
- Kubelka and Munk 1931.

**Photographic materials**
- AIC PMG wiki, "Silver Mirroring" ([link](https://www.conservation-wiki.com/wiki/PMG_Silver_Mirroring)).
- *JAIC* 41(2) 2002, 111–126 (seen via a search summary; the host was blocked here).
- Lavédrine 2009, *Photographs of the Past* (Getty).

**Repositories**
- Woodii `docs/decisions-0.4.md` at 5b1757d (Chroma decisions; v4.1 lesson lines).
- `docs/chroma-mode-plan.md` at de6f9b1.
- `tests/test_chroma.py` docstring.
- `docs/AUTHOR-POSITIONS.md`.

**Work files** (`/home/user/xpw/d99a4c/work/`):

| File | What it is |
|---|---|
| `sim_print.py`, `gen_scenes.py` | Simulator and scenes |
| `visualiser_proto.py` | Proposed core: reference stages, picks as seeds, departure, four pictures, checks, montage |
| `run_eval.py`, `score_elements.py` | Every method on every scene, and per-element scoring |
| `test_woodii_linear.py` | Woodii's Chroma mode in its own setting |
| `vendor/` | Read-only copies of v4.1.2 and Woodii `chroma.py` |
| `results/` | Montages, JSON scores, logs |
