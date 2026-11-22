<!-- Saved verbatim by the coordinator from the agent's hand-back (the harness refused the agent's own write to
/home/user/xpw/257605/report.md). The harness's two-space indent is removed; nothing else is changed. -->

I could not write `/home/user/xpw/257605/report.md`: the harness refused it ("Subagents should return findings as text, not write report files"), and I did not work around that. The complete report is below, ready to save to that path. My re-runs and their outputs are in `/home/user/xpw/257605/work/`.

Neither repository was changed. An untracked `/home/user/handpaint_visualiser/__pycache__/Chroma_diagnoser_v4.cpython-313.pyc` appeared there at 05:26 UTC during the audit. My scripts only import copies under `work/`, so another process created it; I left it as found.

---

# Process audit: the prior work on the handpaint visualiser and Woodii's Chroma mode

**What was audited.** The documents listed in `material/README.md`: the two replies, `results-as-printed.md` and the four scripts. Also commit 4584a2f and `TODO.md` in /home/user/handpaint_visualiser, and the earlier iterations and Woodii documents that the README names.

**The question.** Could the way the work was done have reached a different conclusion? Whether its conclusions are right is not assessed.

**Citations.**
- `reply-1-review.md:33` and `scripts/pickref.py:21` are files in `material/`.
- `visualiser@4584a2f:TODO.md:59` and `Woodii@66d03e7:docs/decisions-0.4.md:1295` are line numbers of `git show <commit>:<path>`.
- Two shorthands:
  - **plan** = `Woodii@971f484:docs/chroma-mode-plan.md`, the version step 1 read.
  - **decisions** = `Woodii@de6f9b1:docs/decisions-0.4.md`. Its lines 705-762 are the same at 971f484.
- `work/expN` are my re-runs.

**Terms.**
- "Hand reference" is the favoured approach as `pickref.py` tried it: the (a\*, b\*) distance from the median of an unpainted region, per L\* band, thresholded in robust spreads.
- "LRC" is the visualiser's lightness-relative chroma.
- Each score is "% of painted pixels shown / % of unpainted pixels shown", as the prior work printed them.

## Summary

1. **The closest precedent's recorded critique is missing, and it targets the core of the recommendation.**
   - The favoured approach is Woodii's Chroma mode moved into CIELAB (§7).
   - The user's recorded reason for removing Chroma mode ends: "keep the pictures and drop the picking" (`Woodii@66d03e7:docs/decisions-0.4.md:1295-1298`). It was committed on `main` 43 minutes after the removal commit the prior work read.
   - reply-1 says "The notes record the verdict, not the reason" (`reply-1-review.md:50`), then recommends a pick per image (`:33`, `:66`).
   - reply-2 and TODO.md build the plan on picks (`reply-2-plan.md:36`; `TODO.md:14-16`) without naming Chroma mode.
2. **The recommendation was in the material read before the survey.**
   - The design note read in step 1 already says what to keep from the visualiser and what to drop (plan:44-45). reply-1's recommendation restates it (`reply-1-review.md:66`).
   - Two of reply-1's findings were already in Woodii's decisions log by 22 Oct: LRC self-suppression, and failed images missing from the CSV (§8).
3. **The test bed was the favoured side's own test design, and it was scored unevenly.**
   - `synth.py` is Woodii's Chroma test fixture, scaled up (§2).
   - The hand reference got a region placed from the ground truth, plus its own tuning: threshold 3, spread floor 0.3, a region chosen per case.
   - The visualiser ran at one default setting.
   - The "flatters" caveat was attached to Woodii only (§5).
4. **Other reasonable choices move both headlines** (§9).
   - **Visualiser.** Under its author's own v4.1 default (percentile 90), it shows about half the large pink wash (49.7%) rather than losing it. The `noise_floor` default that was scored came from a Claude commit on 7 Nov (6176d62).
   - **Hand reference, faint wash.** 17.5% falls to 2.0% at threshold 4, to 3.6% when the wash runs into the picked rows, and to 1.2% under a ±3% colour cast.
   - **Hand reference, false paint.** A margin-only reference flags 92-94% of unpainted pixels on warm prints; this is one of the two options reply-1 offers. A q85 JPEG gives 3-24% false paint at the chosen floor.
5. **Quantifiers grew on the way up** (§4).
   - The faint wash: 17.5% → "is still found" → "all show".
   - Woodii's end: the record's "Open: … the method, the picks, or the maps" → "did not survive real prints".
6. **Limitations were disclosed unevenly** (§6).
   - Woodii's own caveat, that tests built on this forward model "check the code, not the method", applies to the same model. It is not carried to the favoured result.
   - reply-2's "still misses large painted areas" is missing from the README, docstring and commit written in the same step.
7. **What held up** (§10):
   - every printed number reproduces exactly;
   - "the more paint, the less shown" holds over six wash sizes;
   - scalar chroma misses the blue washes at every setting;
   - the pick adds real value on these scenes;
   - the visualiser's negative controls stay clean under JPEG and a cast.

## 1. The conclusion stated before the survey

**It was in what step 1 read.**
- Step 1 read Woodii's design note and removal commit (`material/README.md:5-6`).
- The design note says: "Carry from the Chroma Diagnostic Tool: provenance, SHA-256 hashes, the run manifest. Not its colour pipeline, percentile areas or LRC baseline." (plan:44-45; the same in decisions:720).

**reply-1 and the plan reproduce all four parts, without citing the source.**

| Woodii's decision (plan:44-45) | Prior work |
|---|---|
| Keep provenance | "Keep the visualiser's shell (batch, montage, provenance)" (`reply-1-review.md:66`) |
| Drop the colour pipeline | "Colour management is larger than the aim needs" (`:60`); drop the analytic paths (`TODO.md:25-26`) |
| Drop percentile areas | "Drop the area figures" (`reply-1-review.md:66`) |
| Drop the LRC baseline | Drop raw C\*ab and LRC (`TODO.md:20`; `reply-2-plan.md:38`) |

**The test set encodes the predicted failure and leaves out the favoured design's recorded weaknesses.**
- Three of the four painted cases are washes covering 19-27% of the frame (`synth.py:38-41`). That is the condition decisions:735 names: "A windowed baseline absorbs large washes into itself".
- No scored case contains a weakness that Woodii's own record names:
  - JPEG "compression blocks would read as tint" (decisions:744);
  - 8-bit input making the noise measured in the picks "nearly degenerate" (plan:167-169);
  - flare (plan:29-30);
  - a colour cast.
- This held even after the user said the captures are "unruly", and after reply-2 called a cast "the main risk" (`reply-2-plan.md:32`).

**The measure turned a visualisation question into a segmentation question.**
- Only the Segmented panel's binary mask was scored (`evalcmp.py:34`; `reply-1-review.md:11`).
- That is the standard of the tool's earlier self-descriptions: "Forensic Image Segmenter" (`visualiser@0949bdc:Image_Visualiser_GUI_v.1.2.py:302`) and "Scientific batch chroma analysis and segmentation" (`visualiser@18fbd5a:Chroma Diagnostic Tool v3.0:8`).
- It is not the user's stated aim: "visualize the presence, or lack thereof".
- The montage was looked at once, after scoring (`material/README.md:14`). reply-1 itself says the pink wash "is plain in the Original and Chroma Boosted panels" (`:21`).
- I viewed the faint-blue and sky montages: both washes are visible in the Boosted panel too (`work/montage_C_lrc_small.png`, `work/montage_D_raw_small.png`).
- Scored on the montage, "large painted areas vanish" (`:9`) would read "visible in two panels, hidden in the third".

**The options were framed after message 2.**
- The first decision asks how the pick is supplied, not whether to pick (`reply-2-plan.md:36`; `TODO.md:14-16`). The pick-free route appears only as a fallback that "will fail on heavily painted prints".
- The user wrote "chroma boost around neutral". reply-2 re-reads this as its own substrate-centred idea ("I think what you want is…", `:19`).
- Both options it offers are substrate-centred (`TODO.md:17-19`). The literal reading, today's boost around neutral, is not among them, though reply-2 does flag the choice.

## 2. Identical structure across documents presented as independent

**(a) The comparison's test bed is the favoured side's test suite.**
- reply-1 presents the synthetic run as a test of both tools (`:11`).
- It notes the scenes follow Woodii's assumptions, but only as favouring Woodii (`:23`).

| `synth.py` (prior work) | `Woodii@971f484:mbi_workbench/tests/test_chroma.py` |
|---|---|
| Paper margin, x < 80 (`:15`) | `MARGIN`, x < 40 (`:19`) |
| Density rising left to right (`:13`) | `ramp()`, left to right (`:25-29`) |
| paper·10^-(d·tone + c·ε) (`:20-25`) | `beer_lambert` (`tests/chroma_models.py:10-20`) |
| Yellowed paper (`:18`) | `PAPER`, "yellowed" (`:15`) |
| `PINK`/`BLUE` ε vectors (`:33`) | `RED`/`BLUE` ε vectors (`:16-17`) |
| Shot noise (`:26`) | Shot noise (`:18`, `:40-42`) |
| Untinted reference along the whole ramp (`evalcmp.py:44`; `pickref.py:22`) | `UNTINTED` "across the whole silver ramp" (`:20`) |

- That file states the limit of such scenes: "these tests check the code, not the method" (`:3-4`).

**(b) The rebuild plan is Chroma mode's design, item for item.** TODO.md, reply-2 and commit 4584a2f never name Woodii or Chroma mode.

| TODO.md | Chroma mode (plan) |
|---|---|
| "A visualiser, not a measuring tool" (`:4-5`) | The same words (`:21-22`) |
| Unpainted boxes saved as JSON; a labelled automatic fallback (`:14-16`) | Base pick, else the brightest untinted area, flagged (`:28`); picks saved as JSON (decisions:733) |
| Reference and spread per L\* band; threshold in spreads (`:33-34`, `:49`) | Threshold in multiples of the noise in the untinted pick (`:36-38`) |
| A vector whose angle gives hue (`:39-41`, `:48`) | "its angle … sets hue" (`:110-111`) |
| Leave out clipped highlights and near-black (`:30-32`) | Dark areas, near-black and near-white masked (`:40`, `:42-43`) |
| Downscale; smooth a\*, b\* (`:27-29`) | Half-size decode; smoothing radius (`:41`, `:24-25`) |
| Sensitivity presets (`:51-52`) | A threshold slider (`:36`) |
| Drop raw C\*ab, LRC and the colour paths (`:20`, `:25-26`) | "Not its colour pipeline … or LRC baseline" (`:44-45`) |

**(c) The compare-and-contrast table is drawn up on Woodii's design headings.**
- Its rows (`reply-1-review.md:37-48`) are Woodii's design headings (plan:21-45, 108-116).
- So the visualiser is scored as lacking ("None", "Discarded") on the favoured design's checklist.
- Its own design points (montage, CLAHE texture, batch use; README.md:13-29) mostly have no row.

**(d) The future acceptance tests are the tuning set.**
- `TODO.md:59-60` repeats `synth.py`'s six cases (`:36-41`), on which threshold, floor and regions were chosen.
- Only "a cast across the frame" is new.

## 3. The same source counted more than once as independent confirmation

**(a) One construction gives two confirmations.**
- Woodii's column (`:13-19`) and the hand-reference result (`:33`) come from the same scenes.
- In those scenes the substrate colour depends on lightness alone (`synth.py:19-25`).
- The reference is unpainted by construction (`evalcmp.py:44`; `pickref.py:21-22`).
- reply-1 caveats the first (`:23`) but uses the second to say "Woodii's central idea transfers" (`:33`).

**(b) The user's own rule comes back as Woodii's merit.**
- reply-1 says: "Given your aim, Woodii's 'no area metrics, qualitative only' rule fits better" (`:52`).
- That rule is the user's own recorded decision: decisions:722 (source "You") and decisions:734.
- The quoted phrase "a visualiser, not a measuring tool" (`:46`) is the handover's wording (decisions:722).
- So the criterion and the evidence are one source.

**(c) Both sides come from the same model family, and this is not disclosed.**
- Every commit to Woodii's Chroma design note and `chroma.py` is authored by "Claude": c9242e7, 08f4a2a, 4c8f1e0, 4658dea, 159d2e7, efd1adf, de6f9b1.
- So is the visualiser commit that set the tested default (6176d62).
- reply-1 calls that design "principled" (`:50`) and adopts it.
- Woodii's own review notes: "The reviewers are not independent of the work … Their agreement is weak evidence" (`Woodii@origin/xpollinate/adversarial-review:xpollinate/README.md:26-28`).

## 4. Claim escalation between documents

1. **The faint, chroma-lowering wash.**
   - The claim grows at each step:
     - "17.5%" (`results-as-printed.md:56`; `reply-1-review.md:33`);
     - "so a wash that lowers chroma is still found" (`reply-2-plan.md:28`; `TODO.md:41`);
     - tests in which such a wash and the rest "all show" (`TODO.md:59-60`).
   - Re-runs: 2.0% at `evalcmp`'s threshold of 4, and 9.0-10.4% with three 100×100 picks. It reaches 100% only with the plan's a\*/b\* median (`TODO.md:29`), which the prior work never ran (`work/exp3`, `exp4`, `exp8`).
2. **How Woodii's Chroma mode ended.**
   - The record says: "Open: what failed on the real prints (the method, the picks, or the maps)" (decisions:1294-1295).
   - reply-1 narrows this in three steps: "Removed after the first real run" (`:48`), then "did not survive real prints" (`:50`), then "why it failed on real prints" (`:66`).
   - The later record calls the pictures "helpful" (§7).
3. **One setting becomes "the visualiser".**
   - The evidence covers one of four shipped modes; reply-1 itself lists the others (`:42`).
   - Yet the claims are about "the visualiser" and its "detection logic" (`:9`, `:50`; `reply-2-plan.md:3`).
   - The author's own v4.1 default, percentile 90 (`visualiser@a365ea6:Chroma_diagnoser_v4.1:564-565`), shows the pink wash at 49.7% raw and 37.0% LRC, with no false paint in that image. It does give the neutral untinted print 7.2% false paint (`work/exp1`).
4. **A figure that was never printed.**
   - reply-1 says "100% of … the larger touch" (`:33`). The printout gives only 97.5% for both touches together (`results-as-printed.md:58`).
   - Re-run: 98.7% for the 30×30 touch and 81.2% for the 8×8 (`work/exp2`).
5. **A qualifier that was dropped.**
   - Woodii was "scored only where Woodii 'shows'" (`results-as-printed.md:34`). reply-1 gives a plain "100% / 0.04%" (`:19`).
   - If masked pixels count as not shown, the small-touches case is 93.9% (`work/exp2`).

## 5. Critique applied only to rejected options

1. **The "flatters" caveat.**
   - reply-1 attaches it to Woodii only (`:23`).
   - The hand reference (`:33`) had the same scenes, plus a region placed per case from the ground truth (`material/README.md:12-13`).
   - In the sky case that region is 67.5% of the frame, because the sky fills columns 80-520 (`pickref.py:21-22`).
   - It also had settings used nowhere else: threshold 3 against 4 (`pickref.py:24`; `evalcmp.py:38`), and floor 0.3 against 0.5 (`pickref.py:11`; `evalcmp.py:23`).
   - Threshold 4 alone takes the faint wash from 17.5% to 2.0%.
2. **Real-world record.**
   - Woodii's removal after a real run counts against it (`:48`, `:50`).
   - The visualiser's "In use" counts for nothing.
   - The favoured approach has no real-print evidence, yet it shares the precedent's one real-print outcome (§7).
3. **"Careful picks".**
   - reply-1 names this as Woodii's weakness (`:50`), but never tests the favoured approach's sensitivity to picks.
   - On the prior work's own scenes, a margin-only reference flags 92-94% of unpainted pixels on warm prints and 6.6% on the neutral print. "A margin" is one of the two options at `:33`.
   - A faint wash that continues into the picked rows is shown at 3.6% (`work/exp3`, A4 and B3).
   - `TODO.md:34` anticipates part of this.
4. **Which settings were explored.**
   - The visualiser ran at its default only.
   - That default was set two weeks earlier by a Claude commit (`visualiser@6176d62`: "New default threshold mode 'noise_floor'"), replacing the author's percentile default. reply-1 says only "on `main`" (`:5`).
5. **Speed.**
   - reply-1 faults "The LRC loop makes 100 full-image masks" (`:61`).
   - The favoured feature runs the same loop (`pickref.py:7-8`; `TODO.md:33-34`) and takes 1.09 s against LRC's 0.50 s (`work/exp5_timing.txt`).
6. **Applied evenly (for balance).** The critique of a threshold derived from the image itself is applied to the plan's own fallback too (`TODO.md:35-36`).

## 6. Limitations disclosed in one document and absent from siblings produced the same way

1. **The synthetic-test caveat.**
   - It is disclosed for Woodii (`reply-1-review.md:23`), and by Woodii itself for the same forward model: `test_chroma.py:3-4`, `mbi_workbench/README.md:222` (at 971f484), and decisions:740.
   - It is absent from the hand-reference result (`:33`), from Woodii's "38 maths tests" counted as a plus (`:47`), from reply-2, and from `TODO.md:59-60`.
2. **How the scores were made.**
   - `results-as-printed.md:34` (Woodii scored only where shown) and `:50-51` (a hand region, threshold 3, a 5 px median) appear only in the printout.
   - Neither reaches reply-1's table (`:13-19`) or `:33`.
3. **A known detection failure, missing from the repository text.**
   - reply-2 says the tool "still misses large painted areas" (`reply-2-plan.md:3`).
   - The README, docstring and commit written in the same step add "not a measuring tool" but not this failure.
   - The README still says the noise floor "Automatically calculates the statistical threshold between the background substrate (noise) and actual pigment (signal)" (`visualiser@4584a2f:README.md:20`; also `:7`, `:66`).
4. **Numbers still on the pictures.**
   - reply-2 places the threshold values only in "the JSON record and run log" (`:15`).
   - Running 4.1.2 shows them on every montage footer as well: "noise_floor(LRC):2.26 | Visualisation only - not a measurement" (`Chroma_diagnoser_v4.1:1359`, `:1382`; `work/montage412_footer.png`).
5. **JPEG and 8-bit input.**
   - Woodii's record warns about both: "compression blocks would read as tint" (decisions:744), and 8-bit noise measured in the picks "nearly degenerate and flagged 38 % of untinted pixels" until a floor was added (plan:167-169).
   - The favoured approach targets JPEGs (`TODO.md:3-4`, `:27-29`), but its floor was set on lossless PNGs (`pickref.py:11`).
   - At floor 0.3, q85 JPEG gives 3.0-7.5% false paint with the hand region and 6.8-23.7% with three 100×100 picks; on the untinted print these are 5.7% and 21.2%.
   - The plan's a\*/b\* median does not help. Floor 0.6 brings false paint down to 0.3-1.0%, and the faint wash is still found (`work/exp4`, `exp6`).
   - So the result depends on a parameter that was never chosen on the user's kind of input.

## 7. The closest historical precedent and its canonical critique

**The precedent is Woodii's Chroma mode** (designed 22 Oct, built 23-28 Oct, removed 29 Oct 2026). It has the same core as the favoured approach:
- an unpainted reference picked by the user (plan:28; decisions:733);
- a threshold in multiples of the noise measured in the picks (plan:36-38);
- hue from the angle of the vector off the reference (plan:110-111);
- qualitative pictures only (plan:21-22).

reply-1 names this lineage once (`:33`). reply-2, TODO.md and the commit do not.

**Its critique is already in the repositories:**
- **The user's reason for removing it**, committed 43 minutes after de6f9b1: "the results were not very user friendly, and while the chroma viewer might be inaccurate it allowed for useful visualisations, which were helpful". Hence: "keep the pictures and drop the picking" (`Woodii@66d03e7:docs/decisions-0.4.md:1295-1298`).
- **A second note of 30 Oct.** The output was "confusing and not useful", and "nothing from Chroma mode comes back without it" (`Woodii@ebed85e:docs/decisions-0.4.md:1407-1410`). Woodii's main still has "A tint visualisation (on hold: which visualiser, your note)" (`Woodii@8de1245:TODO.md:634`).
- **The removal commit names the picks as a suspect** (decisions:1294-1295).
- **Woodii's red team caught the same move on 5 Nov.** It found that "conditioning on each print's own untinted density curve, with picks, was Chroma mode's C3 under another name". Its fix: name the lineage, ask what failed, and if it was the picking, build "without picking" (`Woodii@origin/xpollinate/adversarial-review:xpollinate/README.md:336-349`; `xpollinate/path-review/reports/12-red-team-final.md:55-77`).
- **The synthetic-test and 8-bit warnings** (§6, items 1 and 5).

**None of this appears in the prior work.**
- reply-1 says "The notes record the verdict, not the reason, so I can't say why" (`:50`).
- It lists "careful picks" among Woodii's problems (`:50`), yet keeps the picks and drops the "machinery" (`:33`, `:66`).
- Picking appears only as a cost to batch use (`:33`; `reply-2-plan.md:36`).
- **Cause:** the reading stopped at the removal commit (`material/README.md:5-6`; `reply-1-review.md:5`). Yet `git log main -- docs/decisions-0.4.md` lists 66d03e7 just two entries above de6f9b1.
- The user then accepted the suggestions (message 2) without being shown their own recorded reason.

**The visualiser's own history offers an earlier answer to a bad threshold.** It was a control set once per batch, not a pick per image:
- a manual threshold and a "Threshold Bias (Adaptive)" slider (`visualiser@0949bdc:Image_Visualiser_GUI_v.1.2.py:346-365`);
- "User-Friendly GUI: No command line required" (`visualiser@27d8180:README.md:29`).

The plan's presets (`TODO.md:51-52`) echo this, but are not offered as an alternative to picking.

## 8. "Found" claims where the thing found was supplied in advance

| Claim | Where | Already supplied | Note |
|---|---|---|---|
| LRC self-suppression, one of the "Three causes" | `reply-1-review.md:28` (`:11`, `:25`) | decisions:719 "self-suppressing LRC baseline"; decisions:735; plan:44-45 | Recorded by 22 Oct; not cited |
| Failed images left out of the CSV | `:62` | decisions:719 "failed files missing from the summary" | Not cited |
| Where the 4.1 bugs were | `:60` | decisions:718; `visualiser@cfbf66c:Chroma_diagnoser_v4.1:5-23` | Stated as history, without a source |
| The recommendation | `:66` | plan:44-45; decisions:720 | See §1 |
| The hand reference's success | `:33` | The region was placed from the ground truth (`material/README.md:12-13`; `pickref.py:21-22`) | A paint-free reference spanning the lightness range is the method's working condition, and the scorer supplied it. If the wash runs into the picked rows, 17.5% falls to 3.6% |
| The rebuild's tests passing | `TODO.md:59-60` | The tuning set | See §2(d) |

**Not supplied in advance:** the noise-floor walk finding (`:27`). The `noise_floor` mode post-dates Woodii's record (6176d62, 7 Nov), so this finding is the prior work's own. It held up.

## 9. Would other choices have changed a result? (re-runs)

**How the re-runs were done.**
- I rebuilt the synthetic images with the prior work's own scripts; every printed figure reproduced exactly.
- `work/synthlib.py` is `synth.py`'s model as functions, and gives identical arrays.
- The new images use noise seed 11. Their lossless baseline matches the printed figures: the faint wash at 17.7% against 17.5%, the other cases equal, no false paint (`work/exp8`).

**Rejected option: visualiser 4.1.1** (cells are raw C\*ab / LRC)

| Setting | Pink (F) | Sky (D), faint wash (C) | False paint on untinted prints |
|---|---|---|---|
| `noise_floor`, as scored | 0.0 / 1.4 | 0 / 0 | 0.00 / 0.00 |
| Percentile 90 (a365ea6's default) | 49.7 / 37.0 | 0 / 0 | raw 7.2 neutral, 0.04 warm; LRC 0.00 |
| Percentile 75 | 99.5 / 58.9 | 0 / 0 | raw 15-19 |
| Any setting | — | 0, unless more than 90% of unpainted pixels are flagged | — |
| q85 JPEG; ±3% cast | raw 0.5, 0.0; LRC 49.3, 0.0 | ≤ 2.2 | raw 0.00 throughout; LRC ≤ 0.9 on untinted (7.6 on the JPEG sky) |

**Favoured option: hand reference** (cells are % painted shown / % unpainted shown)

| Variant | Faint (C) | Sky (D) | Touches (E) | Pink (F) | Untinted, false | File |
|---|---|---|---|---|---|---|
| As printed: hand region, threshold 3, floor 0.3, PNG | 17.5/0.00 | 100/0.00 | 97.5/0.00 | 100/0.00 | 0.00 | exp3 A1 |
| Threshold 4 | 2.0/0.00 | 99.9/0.00 | 97.5/0.00 | 100/0.00 | 0.00 | A2 |
| Margin + three 100×100 picks | 9.0/0.00 | 100/0.00 | 97.5/0.00 | 100/0.00 | 0.00 | A5 |
| Margin only | 100/93.4 | 100/93.1 | 100/93.5 | 100/92.0 | 93.5 | A4 |
| Whole image as reference, threshold 3 | 7.7/0.00 | 3.2/5.48 | 97.5/0.00 | 50.2/3.34 | 0.00 | A3 |
| No pick: robust refit, 5 rounds | 8.3/0.00 | 4.7/6.95 | 97.5/0.00 | 56.1/3.94 | 0.00 | A6 |
| The plan's a\*/b\* median | 100/0.02 | 100/0.02 | 98.3/0.00 | 100/0.06 | 0.00 | exp4 |
| Wash runs into the picked rows | 3.6/0.15 | — | — | 17.2/9.09 | — | B3 |
| ±3% cast | 1.2/2.46 | 96.2/0.00 | 97.5/2.00 | 100/2.46 | 2.00 | B2 |
| ±3% cast, three picks | 2.4/8.50 | 100/0.11 | 97.5/6.91 | 100/8.51 | 6.90 | exp4 |
| ±3% cast, floor 1.0 | 0.0/0.08 | — | — | 100/0.08 | 0.06 | exp7 |
| q85 JPEG | 99.7/6.96 | 100/2.98 | 100/5.73 | 100/7.49 | 5.66 | B1 |
| q85 JPEG, three picks | 99.7/23.2 | 100/6.75 | 100/21.3 | 100/23.7 | 21.2 | exp4 |
| q85 JPEG, three picks, floor 0.6 | 99.4/0.37 | — | — | 100/0.99 | 0.30 | exp6 |

Adding the plan's a\*/b\* median to the cast gives 41-49% false paint (exp4).

**What changes.**
- **The visualiser.** "Large painted areas vanish" is a property of the `noise_floor` default. The blue-wash miss does not depend on the setting.
- **The favoured approach.** Its "0% false" and "17.5%" hold for lossless input, an oracle region, threshold 3 and floor 0.3. Under JPEG, a mild cast, or paint inside the pick, it either shows false paint or loses the faint wash, depending on the floor. The visualiser keeps clean negatives in the same conditions.
- **The comparison.** On the inputs the user described, it is a trade-off, not the dominance shown in reply-1's table.

## 10. Checks that did not change the result

- **Reproduction.** Every printed number reproduces exactly. `strip.py` reproduces 4.1.2 (82,033 → 73,701 bytes), apart from the two later edits that `results-as-printed.md:64-66` describes.
- **"The more paint, the less shown"** (`:9`) holds for the strong pink at 0.5, 2, 5, 10, 18.75 and 30% of the frame. LRC shows 70.8, 12.6, 5.4, 3.4, 1.4 and 0.1% (`work/exp3` C).
- **"Chroma is a scalar"** (`:29`): no 4.1.1 setting shows the blue washes without flagging most of the frame (`exp1`).
- **The pick matters on these scenes.** With the whole image as reference, the pink wash drops to 50%, and my pick-free refit did not recover it (A3, A6).
- **The visualiser's negative controls** stay clean in raw C\*ab under JPEG and a cast.

## 11. Could the process have reached a different conclusion?

Yes, at four points:
1. **Reading one commit past de6f9b1.** At 66d03e7, the user's "drop the picking" would have stood against a recommendation built on picking. Then `:50` could not have called the reason unrecorded, and reply-2's first decision would have been whether to pick, not how.
2. **Starting from the visualiser's own options and history.** These are the percentile default (a365ea6), the GUI bias slider, and the `noise_floor` default added by 6176d62. Starting there would have split the main finding into a recent default and a structural hue problem.
3. **Building the test set from the user's inputs and the favoured design's recorded weaknesses.** That means JPEG and uneven light (decisions:744; plan:167-169), with references placed without the ground truth. At the chosen settings this would have shown false paint or a lost wash, and forced the floor and threshold to be chosen on that input.
4. **Scoring the montage instead of the Segmented mask.** The large washes would have been recorded as visible in the Boosted panel.

None of this says the recommendation is wrong; the process as run could not have found out.

## Files in /home/user/xpw/257605/work/

- **Reproduction:**
  - `S/` holds the images and 4.1.1 outputs in the layout the scripts expect, with Woodii's `chroma.py`; `evalcmp`/`pickref` were re-run there.
  - `synthlib.py` is `synth.py`'s model as functions.
- **Experiments:**
  - `exp_visualiser_modes.py` → `exp1_visualiser_modes.txt`
  - `exp_shown_and_touches.py` → `exp2_shown_and_touches.txt`
  - `exp_favoured_variants.py` → `exp3_favoured_variants.txt` (images in `exp3_img/`)
  - `exp_todo_mitigation.py` → `exp4_todo_mitigation.txt`
  - `exp5_timing.txt`
  - `exp_floor_jpeg.py` / `exp_floor_cast.py` → `exp6` / `exp7`
  - `exp_seed11_baseline.py` → `exp8_seed11_baseline.txt`
- **Images:** `montage_*_small.png` and `montage412_footer.png` (from the 4.1.2 run in `S412/`).
- **Copies read from the repositories:** `cd411.py`, `cd412_committed.py`, `cd412_strip.py`, `decisions-0.4_de6f9b1.md`, `chroma-mode-plan_971f484.md`, `chroma-mode-plan_de6f9b1.md`, `xpollinate_README.md`.
