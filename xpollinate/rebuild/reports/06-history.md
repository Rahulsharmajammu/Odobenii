<!-- Saved verbatim by the coordinator from the agent's hand-back (the harness refused the agent's own write to
/home/user/xpw/121087/report.md). The harness's two-space indent is removed; nothing else is changed. -->

I could not save the report to /home/user/xpw/121087/report.md: the environment refuses report files written by a subagent. The full text is below and can be saved there as-is.

Neither repository was changed by me. The visualiser's branch did gain a commit during my run, 74db2bb "Ignore Python bytecode caches" (it only adds .gitignore); I did not make it. The analysis covers 4584a2f and earlier. All my working files, code and figures are in /home/user/xpw/121087/work/.

---

# The handpaint visualiser: what its history says, a premortem of the rebuild, and the smallest tool that could survive it

Standpoint: software history and the premortem. The evidence is the two repositories' own record (read with git log and git show; neither repository was changed), the author's words where the record quotes them, and a synthetic bench written for this report (/home/user/xpw/121087/work/). No real captures were available, so the bench checks code against a model. It does not show that any method works on real photographs.

## 1. Verdict

**Rebuild only one thing: how the tool decides what the unpainted photograph looks like.** Keep the three-panel montage that has survived every version since December 2025. Make that decision visible on every picture, and test it on real captures that include known-untinted prints before adding anything else.

TODO.md is right about its aims: no numbers, the vector feature, hue from direction, faint shown bright, hatched exclusions and presets. The premortem places the likely failure in four of its choices:

1. **The per-image picker** (`<name>.picks.json`), listed as the first decision. The author's own reason for dropping Woodii's Chroma mode was that its results "were not very user friendly". Woodii's record glosses this as "keep the pictures and drop the picking". A per-image picker repeats that workflow.
2. **The automatic fallback as written:** per-tone medians refitted after setting outliers aside. This is the path every image will actually take, and it is the least specified. It absorbs any wash that covers most of a tone. On the bench it showed 23% of a painted sky and 8% of a wash over every light grey; the alternative below showed 100% of each.
3. **Step 6, a light plane fitted to the whole image.** On the bench it hid a painted sky under mixed light (3% shown) and gave no warning. That is the failure most likely to destroy trust, because the map looks clean.
4. **The object box as "optional".** Surroundings in the frame took over the dark tones' reference. Without the box, the TODO fallback showed colour on 24% of one print's unpainted area; with it, 2.5%.

**What would reverse this verdict.** The line-up test in section 9 on real VDZ captures could show that the TODO fallback finds large washes as often as the consensus reference. Or the author could, in practice, draw a pick on most images. Or mixed-light captures without a paper border could turn out to be the common case. In that last case the image-wide plane's cast correction would be worth its hidden skies, provided the picture says the light was flattened.

## 2. The record: what was tried, kept and removed

### 2.1 Sources, and how far to trust them

In an assistant-built project, most of the written record is the assistants' text: commit messages, design notes, decision logs, and even AUTHOR-POSITIONS.md. The author's voice survives mainly as short quotations inside those logs, a few terse commit titles, the December 2025 README, and the three messages in this request.

The rest of this report keeps the two apart:
- **Primary evidence:** the code at each commit, and the author's quoted words.
- **Secondary evidence:** an agent's gloss of those words (for example, "drop the picking").

| Date | Version (commit) | Lines | Written by (evidence) | Added | Removed, and the reason recorded |
|---|---|---:|---|---|---|
| 5 Dec 2025 | GUI v1.1 (9f4420e) | 436 | Author upload. Comment style suggests assistant help | Tk window "Forensic Image Segmenter". Montage Original / Chroma Boosted / Segmented Boost Map. Histogram-peak "noise floor" on C*ab measured from a*=b*=0. Three opacity tiers. Bias slider | nothing |
| 28 Jul 2026 | v1.2 (0949bdc) | 479 | "Fix:" comments throughout (an assistant's review pass) | Cancel button, manual/adaptive toggle, error handling | "fixed errors in computation of outliers, fixed broken LAB chroma math, corrected file ingestion" |
| 10 Aug 2026 | Chroma Diagnostic Tool v3.0 (18fbd5a) | 1,302 | **ChatGPT:** the file is a code-interpreter script that writes itself to /mnt/data/chroma_diagnostic_tool_v3.py | "Scientific batch chroma analysis". Numerical TIFFs, Jaccard threshold-sensitivity, area percentages, component statistics, manifest, SHA-256 | **The GUI deleted, no reason recorded.** The next commit, "Textual Updates" (f95e1f8), removed the wrapper together with the docstring's opening quotes, so the file in the tree today does not parse (SyntaxError at line 24) |
| 11 Aug 2026 | v4.1.0 (a365ea6). v4.0 was never committed | 1,873 | Assistant (docstring: "Key fixes from v4.0") | "FADGI-compliant" colour handling that read untagged files as ProPhoto. LRC (per-L* band median chroma). Raw and LRC maps for every image | Committed with `INPUT_DIR = <INPUT PATH HERE>`, so it could not run as committed |
| 20–21 Oct 2026 | Woodii handover review of v4.1 | docs | Agent review, author's decisions | Five critical findings (white point applied twice, ICC never read, EXIF branch dead, ProPhoto default, 16-bit lost) and a "self-suppressing LRC baseline" | "Do not use Chroma Diagnostic Tool v4.0 or v4.1 numbers"; "Earlier VDZ numbers came from v4.1 and are unusable"; "The provenance design worked; the measurement design did not." |
| 22–29 Oct 2026 | Woodii Chroma mode (built 23 Oct; code at 5b1757d) | ~2,800 | Claude, from the author's choices ("all five extras") | Optical density on linear raw. Silver axis from a required untinted pick. Noise covariance and Mahalanobis threshold. IR and UVL references, NNMF, colour deconvolution, palette plot | **Removed after the first real run** (de6f9b1): "the chroma mode is a bust, and probably needs to go" |
| 30 Oct 2026 | Woodii 0.4.0 (66d03e7) | docs | Author quoted | — | **Why:** "the results were not very user friendly, and while the chroma viewer might be inaccurate it allowed for useful visualisations, which were helpful." Agent's gloss: "keep the pictures and drop the picking" |
| 7 Nov 2026 | v4.1.1 (6176d62) | 2,077 | Claude | Fixes for the Woodii findings: neutral grey now reads C*ab 0, ICC and EXIF actually read, sRGB default, 16-bit read | — |
| 22 Nov 2026 | v4.1.2 + TODO.md (4584a2f) | 1,895 | Claude | "Visualisation only" label, run log, the rebuild checklist | Area percentages, counts, statistics, Jaccard analysis, numerical TIFFs (the author's request) |

### 2.2 Five things the record shows

1. **The montage is the one thing that never changed.** Every version from v1.1 to v4.1.2 makes the same three panels. The README's only illustration is one of them (file name `2021 443 694_montage`). The author's verdict on Chroma mode values its "useful visualisations". This is the working simple system.
2. **The reference is the one thing every version rewrote, and none tested on a known-untinted print.** The answer to "what does unpainted look like?" changed each time:
   - v1.1: a*=b*=0, with a threshold set by the image's whole chroma histogram.
   - v4.1.0: the median chroma of each lightness band (LRC).
   - Woodii: a picked untinted area, giving a silver axis and a noise model.
   - TODO.md: per-image picks, or the iterative band medians, plus a plane.

   Woodii's handover found the LRC version "self-suppressing" (a large wash becomes its own reference). The TODO's fallback is a two-dimensional version of the same estimator.
3. **Measurement crept in through rewrites and was removed by the author.** Numbers arrived with v3.0's "scientific" rewrite and were removed on request in 4.1.2. The removal is incomplete:
   - the montage still prints the threshold (Chroma_diagnoser_v4.1 lines 1359 and 1382);
   - the console still prints it (line 1444);
   - the run log keeps threshold, mid_threshold and high_threshold (lines 1672–1674);
   - the README still promises "3-Tier Segmentation" that lets researchers "distinguish between faint residue and solid paint" (README lines 22–25 and 66).
4. **The interface was lost without a decision.** The README advertised "User-Friendly GUI: No command line required" from December 2025 until 7 November 2026. The GUI had been deleted on 10 August.
5. **Both big rebuilds were judged on first contact.** Chroma mode took about 2,800 lines and one day to build. It was adversarially reviewed (27 findings) and tested only on synthetic prints. Woodii's own README says of those tests that the forward models "share its additive-OD model, so they check the code, not the method". The plan called for "Chroma on one print"; the verdict came the same day. Woodii's 29 October health check had already named the pattern: "each was built and extended before the one before it was tried on real captures". The record leaves "what failed on the real prints (the method, the picks, or the maps)" open. Only the author's 30 October sentence answers it.

## 3. Reading the record with Brooks and Gall

**The second-system effect** (Brooks, *The Mythical Man-Month*, 1975, ch. 5): "The general tendency is to over-design the second system, using all the ideas and frills that were cautiously sidetracked on the first one." The record shows it twice.
- v3.0/v4.x took a 479-line GUI tool to about 1,900 lines of batch "scientific" machinery. That included three colour spaces with Bradford adaptation, a FADGI compliance claim, numerical TIFFs and a Jaccard stability analysis.
- Chroma mode then repeated the pattern at larger scale, with "all five extras".

There is a modern twist. When an assistant writes the code, a frill costs the generator nothing. The costs fall where Brooks put them: on understanding, on testing, and on the user's time per image (Chroma mode's required picks). An assistant has no "cautiously sidetracked" list, so the first and second systems blur together. Note also that v4.0, the version between the two, never reached version control.

**Gall's law** (*Systemantics*, 1975): "A complex system that works is invariably found to have evolved from a simple system that worked." Chroma mode was a complex system designed from scratch on top of a pipeline the author already felt was bloated ("I think there is already a degree of bloat and feature creep happening", 29 October). It could not be patched after its first real run, so it was removed.

The health check's growth table shows Lehman's law of increasing complexity (Lehman, *Proc. IEEE* 68(9), 1980) at work. Python source grew 80% from batch 1 to batch 5.6.2, all within the nine days between the 20 October import and the 29 October check.

TODO.md is much smaller than Chroma mode. It still proposes a from-scratch package (load, reference, feature, render, cli), a per-image picker, a folder default, an automatic fallback and a spatial plane. Its most important line is its last: "Try on real VDZ captures before anything else is added." Gall's law says that line should be first.

**A precedent that survived.** The closest long-lived analogue is Jon Harman's DStretch (ImageJ plugin, about 2005 onwards). It applies the decorrelation stretch of Gillespie, Kahle and Walker (*Remote Sensing of Environment* 20, 1986) to faint pictographs on rock, photographed in the field by anyone, with any camera. In the uses described here it makes no claim to colorimetry or measurement. It has:
- one button;
- a few colour-space presets;
- a scale;
- an optional selection that restricts the statistics to a region while the stretch applies to the whole image.

It has no thresholds and no maps. Its known weakness is the one examined here: it takes its statistics from every pixel in the frame. Griffith University's localised stretch (Dyson, Jalandoni and Taçon, L-DCS) exists because crowded scenes defeat a whole-frame reference. Two lessons follow: zero required interaction per image, and an honest label on false colour, are what long-lived tools of this kind share.

## 4. Premortem: it is November 2027, and the rebuilt visualiser is abandoned or distrusted

The method is Klein's premortem (*Harvard Business Review* 85(9), 2007). It rests on prospective hindsight (Mitchell, Russo and Pennington, *J. Behavioral Decision Making* 2(1), 1989): imagining that a failure has already happened helps people name more reasons for it. Each story below gives its evidence and the countermeasure built into the design in section 5. They are ranked by likelihood times damage.

1. **The picker was never used, so every image ran on the fallback.**
   - Evidence: the author's 30 October reason; AUTHOR-POSITIONS #2 ("If it is not easy, nobody will do it"); TODO.md lists picks first and calls the automatic path a fallback that "extensive paint defeats".
   - Countermeasure: no per-image interaction. The automatic reference is the designed and tested path. External evidence comes per folder, not per image.
2. **Large washes vanished: painted backdrops and skies came out grey.**
   - Evidence: Woodii's "self-suppressing LRC baseline" finding.
   - Bench: the TODO fallback showed 23% of a painted sky (P4) and 8% of a wash over every light grey (P6). The consensus reference showed 100% of both.
   - Countermeasure: a consensus tone curve anchored at the paper, not per-tone medians.
3. **The light plane hid the sky, and nobody noticed.**
   - Bench P5: the TODO with plane showed 3% of the sky. Its planned warnings (heavy JPEG, glare, tonal coverage) would not have fired.
   - A clean, wrong map found once makes every other map suspect.
   - Countermeasure: no image-wide spatial term. Uneven light is measured only on the paper border, which cannot hold paint, and otherwise is reported, not corrected.
4. **Mixed-light captures flooded the map, and viewers learned to ignore its colour and its words.**
   - Bench: under mixed light the consensus reference showed colour on 38–52% of untinted prints. Its words fire on genuinely painted prints too.
   - This is the design's own weak point and is not solved here.
   - Countermeasures: at most two warnings per picture. A plain capture note: one light, or the paper border in frame. An opt-in "flatten the light" that is labelled on the picture.
5. **The surroundings set the reference.** The mount or table entered the dark tones (P1: 24% of unpainted print shown without the box, 2.5% with it). Countermeasure: find the print's edge automatically, outline it on the original, and say so when it cannot be found.
6. **The phone painted the photograph.** Apple describes Smart HDR 4 (2021) as optimising skin tone per person, and semantic rendering (iPhone 11 onwards) as adjusting skin, hair and sky locally. A photographed portrait's face is exactly where such processing, and hand colouring, both put colour. The tool cannot tell them apart. Countermeasures: a capture note (RAW or a camera mode without scene processing), and a known-untinted print photographed the same way in every batch. A colourless face on that control is the only proof.
7. **Numbers crept back:** the threshold on the montage, tiers read as "faint residue vs solid paint", a CSV someone sorted. Countermeasure: finish 4.1.2's removal (section 2.2, item 3) and keep numbers out of the README too.
8. **Nobody but the author could run it.** The GUI disappeared in 2026 without a decision. Countermeasure: restore v1.2's small Tk window (folder in, folder out, sensitivity, Run, Cancel).
9. **It passed its tests and failed its first real batch**, as Chroma mode did. Synthetic prints made with the same monochrome law the estimator assumes cannot fail it. Countermeasure: tests that break the model on purpose (tone that shifts with density, mirroring, glare, mixed light, washes over a whole tone), and a real-capture gate before any feature.

## 5. The design: the smallest tool that survives the premortem

The v1 montage is kept. One component, the reference, is replaced. Its assumptions are drawn on the pictures.

Flow: image file -> load -> prep -> find print -> evidence -> reference -> departure -> pictures + words -> record.

| Component | What it does | Default | What the picture says about it |
|---|---|---|---|
| load | Pillow open, EXIF orientation, any ICC profile to sRGB through LittleCMS, untagged files as sRGB, area-average to about 2,400–3,000 px | as TODO steps 1–2 | — |
| prep | CIELAB; 5 px median on a*, b* only; exclusions: clipped (any channel ≥ 0.98, dilated) and near-black (L* < 8) | as TODO steps 3–4 | hatched, never "no paint" |
| find_print | The largest bright, smooth region forming a ring, filled: the print and its paper border. Optional folder box.json | automatic | blue outline, or "No paper border found: the whole frame was used" |
| evidence | Picks the reference source, in order: (1) controls/, known-untinted prints from the same session, pooled into one curve with a per-image offset only; (2) a folder pick, one box on one image reused for the folder; (3) the photograph itself | (3) unless (1) or (2) are given | "Unpainted tone: from the controls / the folder pick / the photograph itself" |
| reference | Tone bands of 2 L*. Up to three density peaks of (a*, b*) per band. A quadratic g(L*) through one peak per band, chosen by consensus across bands (RANSAC; Fischler and Bolles 1981), with the brightest paper as a weighted anchor and a Tukey refit. Spread s(L*) from the chosen cluster, floored at 0.8. Light: a plane fitted only on the border ring, scaled by (L*+16)/(L*paper+16) | as left | yellow outline on the paper taken as unpainted. Strip of the assumed tone; tones without unpainted evidence hatched |
| departure | v = (a*, b*) − g(L*); z = \|v\|/s; 5 px median on z | as TODO steps 7–8 | — |
| render | **Original** with outlines and the strip. **Boosted**: the assumed tone rendered grey, departure ×5, soft-limited. **Presence**: the print in grey, hue from v's direction, opacity smoothstep(z; 2.5→5) (presets 3.5→7 and 1.8→3.8); paper border not judged | as TODO "Pictures" | — |
| words | File name; "Visualisation only – not a measurement"; the evidence used; at most two warnings, in order: the paper border changes colour (uneven light); most of the photograph carries colour; colour covers most of one tone; the two halves disagree ("uneven light, or paint mostly on one side") | — | footer |
| record | JSON provenance (hash, settings, evidence path, warnings), run log, failed files with reasons. No thresholds anywhere a person reads | — | — |
| front ends | `python hpv.py IN OUT [--sensitivity low\|normal\|high]`; v1.2's Tk window restored | — | — |

**Deleted from TODO.md:**
- the per-image picker and `<name>.picks.json` (replaced by the folder pick and controls/);
- step 6's image-wide plane (replaced by light measured on the border only; an opt-in "flatten the light" switch, if kept, must be printed on the picture);
- the five-module package (one file of at most about 600 lines, plus the window and tests).

**Kept from TODO.md:** steps 1–4 and 7–8, the pictures, the presets, the footer, the housekeeping, the removal of v3.0 from the tree, and real captures first, now as a gate (section 9) rather than the last checklist item.

**Rule for anything later:** it needs a real capture that needed it.

A bench prototype of the pictures is /home/user/xpw/121087/work/hpv5_proto.py. It reuses the estimators in methods.py and shows the montages in section 7. It illustrates the design; it is not the rebuild.

## 6. For each uncontrolled capture, how should the tool establish what the unpainted photograph looks like, and how would someone looking at its output know when that has gone wrong?

### Establishing it

The tool cannot measure the unpainted photograph; it can only assume it. For each capture it should use the strongest evidence available:

1. **Known-untinted prints photographed in the same session** (controls/). These share the paper, toning, light, camera and processing. Their tone curves are pooled into one reference shape, and each image may shift it only by a global offset (its own white balance), never reshape it. This is the only evidence that is not inferred from the image being judged. It also makes a negative control part of every batch.
2. **A folder pick:** one box of unpainted print on one image, reused for the folder. This is TODO.md's folder-wide picks.json, promoted from fallback to option and demoted from per-image chore.
3. **By default, the photograph's own monochrome law:**
   - unpainted pixels of the same lightness share one colour;
   - that colour changes smoothly from paper to black (a quadratic in L*);
   - the paper is the brightest smooth area, normally the border.

   The tool estimates the curve **by consensus across tones**: the curve through the densest colour of as many tones as possible, anchored at the paper. It does not use a median per tone. A wash that dominates one range of tones then fails to bend a curve that the other tones and the paper hold in place.

   **Light that varies across the frame is taken only from the paper border**, which cannot hold paint, and never from the image. Clipped highlights, near-black and the surroundings are left out.

What the photograph alone cannot settle, and the tool must say so rather than guess silently:
- **A wash over most of one tone** (all the light greys, or a backdrop that is the only thing of its tone) looks like the print's own toning.
- **Without a paper border, a colour gradient across the frame** looks like a wash on one side.

On the bench, a faint backdrop wash with no unpainted area of the same tone (P1) was absorbed by every estimator.

### Knowing it has gone wrong

The montage carries the assumption and its symptoms:
- **The strip under the original:** the assumed unpainted tone from black to paper, shown as it looks and boosted around the paper. A monochrome print's strip changes smoothly within one hue family. In P1 the strip swung to olive in the mid-greys, between warm shadows and the paper: the tool had taken the blue backdrop for the print's tone there. Hatched stretches mark tones where no unpainted evidence was found; in P6 they mark the light greys, so the pink there is judged from the paper and the shadows alone.
- **The outlines:** yellow around what was taken as paper, blue around the print. If the yellow sits on a painted sky or a painted highlight, nothing downstream can be trusted.
- **Grey where grey is known:** in the boosted panel the paper border and the deepest shadows must be neutral. Colour there means the reference is wrong at that end.
- **The shape of the colour:**
  - Paint follows objects.
  - A wrong reference follows tone (every area of one grey, across objects) or position (a gradient across the frame).
  - A wash taken into the reference leaves a complementary ghost. In P1 the unpainted floor turned orange because the absorbed backdrop was blue. Where a large area is coloured but the original shows it in the print's own tone, look for the missing paint in the tones that went quiet.
- **The words:** at most two, from the paper-border light check, the share of the photograph near the curve, colour covering most of one tone, and the halves disagreeing.
- **The control:** the known-untinted print in the batch must come out quiet. If it does not, nothing in that batch can be trusted. This is the only check that does not judge the tool by its own assumptions.

**Limits.** On the bench the words could not tell a genuine wash over a whole tone (P4, P6) from a wrong reference (N3, N4): both raised "colour covers most of the … greys". The halves check fired on every painted portrait. The warnings therefore direct the viewer's attention; they do not decide. The deciding check is the competent viewer (AUTHOR-POSITIONS #1) comparing the strip and the presence map with the original, and with the control.

## 7. Bench evidence (synthetic; checks code, not method)

**Set-up.**
- Twelve synthetic portraits (synth.py):
  - prints: neutral, warm or split-toned; white or yellowed paper;
  - washes: Beer–Lambert, double pass;
  - captures: phone white balance, mixed light, glare, silver mirroring, an S-curve, saturation ×1.2–1.25, JPEG 4:2:0 at quality 75–92.
- Each case has an unpainted twin captured identically. "Visible paint" means a colour difference of at least 2 a*b* units between the noise-free twin captures.
- The estimators (methods.py):
  - the 4.1.2 script's own C*ab and LRC code;
  - TODO.md's fallback as written, with and without its plane;
  - the consensus reference, with and without light from the border.
- Full results are in bench_results.csv and bench_log.txt.

**Share of unpainted print shown as colour** (lower is better):

| Case | 4.1.2 C*ab | 4.1.2 LRC | TODO fallback | TODO + plane | Consensus | Consensus + border light |
|---|---:|---:|---:|---:|---:|---:|
| N1 neutral, clean | 0.00 | 0.04 | 0.00 | 0.00 | 0.00 | 0.00 |
| N2 warm, yellowed, phone | 0.00 | 0.01 | 0.02 | 0.02 | 0.04 | 0.04 |
| N3 split-toned, no white balance | **0.79** | 0.02 | 0.02 | 0.02 | 0.13 | 0.15 |
| N4 warm, mixed light | 0.00 | 0.00 | 0.19 | 0.02 | **0.52** | **0.38** |
| N5 split, mixed light, glare, mirroring | 0.00 | 0.00 | 0.23 | 0.03 | **0.43** | **0.39** |

**Share of the visibly painted area shown** (higher is better):

| Case | 4.1.2 C*ab | 4.1.2 LRC | TODO fallback | TODO + plane | Consensus | Consensus + border light |
|---|---:|---:|---:|---:|---:|---:|
| P4 painted sky (top third), phone | 0.00 | 0.00 | 0.23 | 0.26 | **1.00** | **1.00** |
| P5 the same sky, mixed light | 0.00 | 0.00 | 0.06 | **0.03** (no warning) | 0.59 | 0.97 (but 0.56 false colour) |
| P6 one wash over every light grey | 0.00 | 0.00 | 0.08 | 0.11 | **1.00** | **1.00** |
| P1 faint backdrop wash, no unpainted mid-tones | 0.03 | 0.07 | 0.17 | 0.16 | 0.24 | 0.12 |
| P2 faint face wash, neutral print | 0.78 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

**What the tables support:**
- **4.1.2's C*ab is either blind or flooded.** Its histogram threshold adapts to whatever the print's tone is, so washes inside that range vanish (P4, P6: 0%), and a capture with no white balance colours 79% of an untinted print.
- **LRC and the TODO fallback absorb any wash that dominates a range of tones.**
- **The image-wide plane fixes uneven light (N4, N5) at the price of a sky it hides silently (P5).**
- **The anchored consensus keeps such washes.** It costs some false colour on strongly toned prints (N3: 0.13; a cubic halves that but absorbs more) and floods under mixed light.
- **Measuring the light on the paper border kept the sky under mixed light** but transferred badly to the mid-tones: the phone's S-curve amplifies a cast there. The prototype's border finder also missed the darker side of the frame.
- **No estimator found P1's faint backdrop wash.** Nothing unpainted shares its tones, which is the limit stated in section 6.

Pictures, in /home/user/xpw/121087/work/img/:
- proto_P1_small.png: the absorbed backdrop, the orange floor ghost and the olive strip;
- proto_P4_small.png: the sky;
- proto_P6_small.png: the light-grey wash, with hatched tones in the strip;
- proto_N2_small.png: an untinted warm print;
- proto_N4_small.png: the mixed-light flood and its warnings;
- tone_curves.png: the true unpainted curves against each estimate. Even untinted prints bend strongly in b* against L*, so a straight-line reference would be wrong on every toned print;
- bench_P5.png and bench_P6.png: all estimators side by side.

## 8. What this standpoint is likely to get wrong

1. **It reads intent from a record that assistants mostly wrote.** "Drop the picking" is an agent's gloss on one sentence. "The results were not very user friendly" may mean the grey optical-density maps, the session flow, or the picks. If the author would happily draw one box per image, the TODO's picker is cheaper and more reliable than any inference, and this design over-invests in automation.
2. **Premortem stories are invented, not observed.** Prospective hindsight raises the number of failure reasons people produce; it says nothing about their accuracy. The ranking in section 4 is a judgment.
3. **Brooks and Gall are aphorisms with survivorship bias.** The systems remembered are those that grew from simple ones. For a script of about 600 lines the decisive issue may be colour science, not architecture. One example: a log-RGB (pseudo-optical-density) space might straighten the unpainted curve, as Woodii's silver axis did for raw data, and make the consensus easier. This standpoint defaults to keeping what survived (Lab) rather than finding what is right.
4. **It treats abandonment as failure.** A project tool laid aside when the VDZ study ends has succeeded.
5. **It may under-rate the plane.** If most real captures are under mixed light with no border in frame, a correction that occasionally hides a sky may serve better than a flooded map every time.
6. **"Show the assumption" may be its own unfriendliness.** The strip, the outlines and the words add exactly the kind of interpretive load that made Chroma mode's results "not very user friendly". The bench already shows the words firing on genuinely painted prints.
7. **The bench repeats Woodii's circularity knowingly.** The prints were generated with the monochrome law that the estimator assumes. "1.00 against 0.23" shows that the code does what it was designed to do, not that it sees paint. Real prints add retouching, foxing, varnish, sheen, cockle and semantic phone processing, which the bench barely models.
8. **It assumes the Woodii positions carry over.** Colleagues at the Met may want rough numbers for triage, and the author's no-numbers rule may not be theirs.

## 9. How to falsify this answer

**Materials.**
- At least 12 hand-coloured VDZ prints, including at least three with large backdrop or sky washes, and at least eight untinted prints from the same series as negative controls, including at least three warm-toned or yellowed.
- Each photographed twice the "unruly" way (phone, room light), once with mixed light.
- Before anyone sees an output, a conservator records for each print, object by object (face, backdrop, clothing, jewellery…), whether it is painted. This is judged from the physical print under magnification and raking light.

**Test 1: is paint shown, and only paint?** Viewers who know neither the print nor the method see each montage and mark each listed object "paint", "no paint" or "can't tell". The montages come from 4.1.2, from TODO.md as written (no picks: fallback plus plane), and from this design. **This answer is falsified if either:**
- the TODO-as-written finds the large washes at least as often as this design; or
- this design marks paint on more than 2 in 10 objects of the untinted prints taken under a single light.

**Test 2: can a viewer see that the reference went wrong?** This uses the line-up protocol of Buja et al. (*Phil. Trans. R. Soc. A* 367, 2009) and Wickham et al. (*IEEE TVCG* 16(6), 2010).
- For each painted print, make four montages of the same capture. Three use the default reference. One uses a deliberately wrong reference: fitted with the backdrop forced in, or borrowed from another print.
- Viewers pick the montage that is "wrong about the unpainted tone".
- **If they do no better than chance (one in four), the strip, outlines and words do not reveal failure. Section 6's second half is then falsified,** and the design should drop them rather than keep decorations.

**Test 3: use.** After three months, count how often controls/ or a folder pick was supplied, and how often warnings appeared.
- If the author supplied per-image picks on most images when offered them, premortem story 1 is falsified.
- If warnings appeared on more than half of all montages, the warning design has failed (alarm fatigue).

**Already runnable now:** the synthetic cases P4, P5 and P6 (`python3 bench.py P4 P5 P6` in /home/user/xpw/121087/work/). If a corrected TODO fallback shows these washes as fully as the consensus does, story 2 is falsified on the model as well.

## 10. Sources

**Primary: the two repositories.**
- Visualiser commits: 9f4420e, 0949bdc, 18fbd5a, f95e1f8, a365ea6, 6176d62, 4584a2f.
- Files: Chroma_diagnoser_v4.1, README.md, TODO.md.
- Woodii, Chroma mode code at 5b1757d: chroma.py, chromarun.py, app/chroma_tab.py, test_chroma.py.
- Woodii documents: docs/chroma-mode-plan.md and docs/health-check-2026-10-29.md at de6f9b1; docs/decisions-0.4.md at de6f9b1 and 66d03e7; docs/AUTHOR-POSITIONS.md on origin/main.

**Literature.**
- F. P. Brooks, *The Mythical Man-Month* (Addison-Wesley, 1975), ch. 5.
- J. Gall, *Systemantics* (Quadrangle, 1975).
- M. M. Lehman, "Programs, life cycles, and laws of software evolution", *Proc. IEEE* 68(9), 1980.
- G. Klein, "Performing a project premortem", *Harvard Business Review* 85(9):18–19, 2007.
- D. J. Mitchell, J. E. Russo and N. Pennington, "Back to the future: temporal perspective in the explanation of events", *J. Behavioral Decision Making* 2(1), 1989.
- A. R. Gillespie, A. B. Kahle and R. E. Walker, "Color enhancement of highly correlated images. I. Decorrelation and HSI contrast stretches", *Remote Sensing of Environment* 20:209–235, 1986.
- J. Harman, DStretch (dstretch.com, help and algorithm pages).
- Dyson, Jalandoni and Taçon, "Localised decorrelation stretch (L-DCS) for improved visibility of large, dense rock art scenes" (Griffith Research Online).
- M. A. Fischler and R. C. Bolles, RANSAC, *Comm. ACM* 24(6), 1981.
- A. Buja et al., "Statistical inference for exploratory data analysis and model diagnostics", *Phil. Trans. R. Soc. A* 367, 2009.
- H. Wickham, D. Cook, H. Hofmann and A. Buja, "Graphical inference for infovis", *IEEE TVCG* 16(6):973–979, 2010.
- Apple's description of Smart HDR 4's per-person skin-tone processing, as reported by Trusted Reviews ("What is iOS Smart HDR?"), and of semantic rendering, as reported by Digital Trends and Fstoppers (2019).

The DStretch, Griffith and Apple items were checked through search summaries only: dstretch.com could not be fetched from this sandbox.

**This report's working files** (all in /home/user/xpw/121087/work/):
- synth.py: synthetic prints and captures;
- methods.py: the estimators, including a copy-run of the 4.1.2 script as hpv_412.py;
- bench.py, bench_results.csv, bench_log.txt;
- hpv5_proto.py and run_proto.py: the montage prototype;
- curves.py: the tone-curve figure;
- img/: all figures;
- v1.1.py, v1.2.py, v3.0_initial.py, v4.0_a365ea6.py, v4.1.1_6176d62.py: the historical versions, extracted with git show.
