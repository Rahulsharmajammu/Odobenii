<!-- Saved verbatim by the coordinator from the resumed red-team agent's hand-back (final pass on the synthesis; the
harness refused report files). The harness's two-space indent is removed; nothing else is changed. Line numbers it
cites refer to the synthesis as it stood before the amendments (the copy at /home/user/xpw/6d8ad6/final/synthesis.md). -->

# Final red-team pass on the synthesis (report 12)

The synthesis's design beats mine on the ordinary case, but two of its merges break its own rules. The fixes are small, and both are needed before the gate.

- **Paint can fake agreement.** When a broad wash takes over the tool's model of the unpainted print, C shows the *unpainted* face as paint, in both photographs (22.4% of the unpainted face and helmet on my bench). The synthesis describes this case as silent absorption.
- **Boxes bring back single-photograph maps.** One photograph plus examined boxes counts as a witness. Under the fixed threshold, that draws C over 26.1% of a print with no paint.

**What I read**
- `final/synthesis.md` and `final/00-precommit.md`.
- Reports 07 (mine, verbatim), 09, 10 and 11, in full.
- Reports 02, 03, 06 and 08, for the claims the synthesis cites from them.
- Checked against the repositories: Woodii 66d03e7, and the visualiser at HEAD 74db2bb.

**What I ran**
- I built the synthesis's engine as specified in §4.3–4.4, on my own bench: a toned silver print, Beer–Lambert paint, and phone-like captures A and B.
  - departures in 2-D log-chromaticity (χ) with a 5 px median;
  - place votes: 10 × 10 tiles × 2 L\* bands;
  - an LTS-style start, then Tukey at a fixed scale;
  - f(L\*) is a 4-knot cubic B-spline and g(x, y) is quadratic;
  - T = max(T0, 3σ) + κ²G², with T0 = 0.04 ([10]'s normal value);
  - a 2 px chroma-resolution blur;
  - witness rule: "both exceed T, within 60°";
  - boxes weighted ×5 and always kept.
- Constants are scaled to my 1024 px frames (shift differences 4 px apart, standing for 12 px at 3,000 px).
- This is my reading of the spec, not the advocates' code. The two main failures (B1, B2) are structural; the bench only illustrates them.
- Code and results are in `/home/user/xpw/6d8ad6/work/redteam2/`. Neither repository was changed.

**Bench results.** Shares shown in C (opacity ≥ 0.25), in capture A's geometry.

| Print | One photo, automatic (C not drawn) | One photo + 5 examined boxes (C drawn) | Two photos, gate at T (as written) | Two photos, gate at T/2 |
|---|---|---|---|---|
| No paint (session control): unpainted shown | 21.4% | **26.1%** | 0.5% | 1.8% |
| Painted, wash on 13.5% of frame: unpainted / wash / cheeks | 7.8 / 92.1 / 92.7% | 8.0 / 96.4 / 93.2% | **0.2 / 88.5 / 84.4%** | 1.1 / 90.2 / 92.5% |
| Wash over 80% (face and helmet unpainted): unpainted / wash | 38.8 / 34.5% | 35.4 / 45.0% | **22.4 / 18.2%** | 29.1 / 21.5% |

---

## A. Scorecard of my original objections

The three classes:
- **Mechanism:** the objection is answered by a named mechanism.
- **Rhetorical:** the problem was renamed or moved, not solved.
- **Standing:** the objection still stands.

| My objection (07) | Class | How the synthesis responds, or where the problem moved |
|---|---|---|
| 1.1a Picks are circular; a pick on a wash flips the answer | Mechanism | Boxes are examined on the object, so the judgement moves to the object (legitimately). A cross-check drops a box that disagrees [11 §3]. Residual: boxes as a witness for C (B2). |
| 1.1b The automatic fit fails under extensive paint | Partly mechanism, partly standing | Place votes and a high-breakdown fit raise the breakdown. Past that budget the synthesis calls the wash "absorbed … visible only as a wrong-looking D". In fact C paints the unpainted areas in the complementary hue, in both photographs (B1). |
| 1.1c "Unpainted = neutral" | Mechanism | That prior is not used. |
| 1.1d In-frame reference | Partly mechanism | The print is found and its border used, but the border's role contradicts itself (B4). |
| 1.1e One photo cannot tell a wash from a cast | Mechanism | A second photograph changes the light and agreement must hold within 60°; no C from one photograph. Not for misfit caused by the paint itself (B1). |
| 1.1f Coherent blobs; pixel noise is the wrong unit | Mechanism, for pairs | On the control, 21.4% → 0.5%. The boxes route reopens it (B2). |
| 1.1g The pictures do not reveal their own errors | Split | **Decode faults: mechanism.** A per-capture reference absorbs uniform and tone-dependent decode bias. **Model contamination: rhetorical.** It moves into D ×4, whose rule fails on unpainted AWB captures on my bench (B7), and whose test comes last. |
| 1.2-1 Presence is a decision; author position 5 | Rhetorical | Renamed to "where colour departs from the print's own tone". The decision moves into T0, a developer constant, with no error-rate criterion anywhere (B8), and is drawn as a hard-edged bright overlay (B9). |
| 1.2-2 "Lack thereof" cannot be shown | Mechanism | The blank sentence and the strip. The sentence names the wrong yardstick (B6). |
| 1.2-3 Within-frame consistency | Mechanism | A joint quadratic light field, plus the witness. |
| 1.2-4 README's "invisible to the naked eye" | Commitment only | A rewrite is listed but not done. |
| 1.2-5 Early-saturating opacity | Mechanism | A linear ramp and no presets. My own edge mechanism is withdrawn (below). |
| 1.2-6 "Luminescence" ambiguity | Standing | Settled by fiat as "no luminescence". [09]'s note that UV fluorescence is the cheapest way to tell stain from paint is not carried. |
| 1.2-7 GIGO presumes controlled kit | Mechanism for capture garbage; standing for object garbage | The session control and the witness catch capture garbage. The control holds no paint, so it cannot see reference contamination (B1, B14). |
| 1.2-8 4.1.2's leftovers | Standing | The synthesis says "done with this delivery". It is not done (B11). |
| 1.2-9 Position 2 against per-image boxes | Mechanism, by relocation | The cost moves to the camera: a second photograph, and a control per session. Whether the author accepts that is still asked. |
| 1.3 The scope deletes the feedback channel | Rhetorical | Validation is called "the first gate", but the synthesis states no pass/fail criterion, and cites a test, F6, that it never defines (B8). |
| 1.4 Terms with no definition | Mechanism | Defined: C's name, the blank sentence, "examined", "deliberately different", and an ordered objective pending the author. |
| 1.5 "Synthetic tests validate" | Rhetorical | Conceded in §1, yet §5.2 picks the threshold on bench numbers and quotes only the favourable half (B3). |
| 1.5 Self-estimated baseline | As 1.1b | |
| 1.5 Histogram noise floor | Mechanism | Dropped. |
| 1.5 Pixel noise as the unit | Mechanism for pairs; standing for the boxes route and paint-driven misfit | And "the paint cannot move T" is false at edges (B5). |
| 1.5 "One photo tells the light" | Mechanism | The witness. |
| 1.5 "A label prevents a quantitative reading" | Rhetorical | Renamed and captioned, but C is still a bright, hard-edged overlay (B9). |
| 1.5 "The iterations improved the pictures" | Mechanism | Conceded, and the order of work rebuilds. |
| 1.6 Trivial answers (DStretch, eyedropper plus Lab curves) | Mechanism | Both are baselines in step 4, with no criterion for "beat" (B8). |
| 1.7 Sceptics | Mechanism | "Places to look"; confirmation at the object; a conservator-marked print in the test set. |
| 1.8 Ill-posed | Mechanism, by narrowed scope | The claim is narrowed to "places to look", with a witness. |

**Corrections to my own report.** The merges were right on four points.

1. **"Why Chroma mode failed was never recorded" was wrong, by 43 minutes.** Woodii 66d03e7 records the author's answer: "the results were not very user friendly, and while the chroma viewer might be inaccurate it allowed for useful visualisations, which were helpful". It still does not say which part failed.
2. **My edge mechanism is withdrawn.** I had blamed smoothing a\*b\* but not L\*; [09] was right that this was not the cause.
   - On my own bench, adding the same median to L\* does not help: capture A 10.2% → 8.4%, and the clean capture *doubles*, 7.1% → 14.1%.
   - The drop to 1.5% came from the larger spread you get with no median (0.68 against 0.39).
   - So my Part 2 line, that equal smoothing removes the edge artefact, is unsupported. The gain came from the unit.
3. **My 79% for TODO's automatic reference on a clean print depends on my own choice of spread floor (0.05).** [09] got 0–2% with 0.75. The mechanism stands; the number does not generalise.
4. **My phone-semantics point is still a hypothesis** (section C).

---

## B. Seams created by the merges

Ordered by how much depends on them.

### B1. The witness passes misfit caused by the paint, and the synthesis misdescribes its own worst case

- **What.** Two components combine here: [10]'s rule that misfit "should show as colour", and [09]'s "seen in both". The coordinator's resolution (line 364) says: "false colour from misfit that differs between captures is removed by agreement". But misfit caused by the object's paint does not differ between captures.
  - Where paint dominates the votes at a tone, unpainted areas at that tone depart from the reference by minus the paint's departure.
  - They do so identically in every photograph, so they pass the 60° test.
- **On my bench.** With a wash over 80%, 22.4% of the unpainted face and helmet lights up in "seen in both", bright yellow. Its direction is 181° from the wash's (64° against −117°), and the wash itself shows at only 18% (`ghost_pair.jpg`).
  - The synthesis says this case is "visible only as a wrong-looking D" (line 347; §7.3: "Only D reveals it").
  - It is not silent. C asserts paint on the unpainted face, and two photographs agree.
  - [10]'s S7 (24% false colour, "a complementary ghost") is this same case. It is also the scene §5.2 cites *for* the fixed threshold.
- **Why it is load-bearing.**
  - Objective 1 ("never show confident colour on unpainted print") rests on the witness.
  - C is drawn bright (Oklab L 0.80).
  - The control holds no paint, so it cannot catch this.
- **Fix.** There is no validated fix within the stated scope. [10]'s "two readings", [04]'s "two colours at one tone" and [11]'s tone-following check all failed or were "not ready". The smallest honest change:
  - (a) Say it in §4.9 and §7.3: "C can show unpainted areas in the complement of a broad wash, in both photographs."
  - (b) Restore [10]'s signature for it to the README: colour complementary to visible paint, following one tonal band.
  - (c) Make it a gate criterion: a conservator-marked print with a broad wash must not show its unpainted areas in C.
  - (d) The existing remedy (examined boxes at those tones) then applies before C is read.

### B2. The boxes route to C rebuilds the single-photograph map the synthesis bans

- **What.** C is drawn "only with a witness: a second photograph that agrees, or corroborated examined boxes" (line 245).
  - [09] admitted marks as a witness because, in my design, the marks' leave-one-out disagreement *set the unit*. That made the map fail safe: one photo plus marks gave 0.5–2.8% on my bench.
  - The synthesis replaced that unit with [10]'s fixed T. Boxes now fix the reference at the boxed places, but nothing accounts for the capture's misfit elsewhere: glare halos, colour fringes, local tone mapping, or light the quadratic misses.
- **On my bench.**
  - One photo plus 5 examined boxes shows 26.1% of the unpainted control, and 8.0% of the painted print's unpainted areas.
  - Flooring T by the boxes' leave-one-box-out disagreement only reaches 13.0% and 4.7%. The place votes swamp the boxes, so the boxes' disagreement never sees the capture's misfit.
  - So either the control lights up and C is withheld every session (the route is dead), or C is drawn with false colour.
- **Fix.** Delete "or corroborated examined boxes" from C's witness. Boxes correct the reference used by D, B and the pair route. C needs a second photograph.

### B3. The fixed-threshold resolution quotes half its evidence

- **What.** §5.2 adopts [10]'s fixed T on the strength of S7/S8 detection (1–18% → 75–87%).
- It omits [10]'s reported price on the same scenes: S7 had 24% false colour, a complementary ghost; P3 had 16.9%, with the margin lit 60%. Those are exactly the misfits the witness cannot remove (B1).
- **Fix.**
  - Cite both halves.
  - Make the fallback to [11]'s median spread depend on a stated criterion, not on "if real controls cannot be kept quiet": controls cannot see ghosts.

### B4. The paper border is both reference and control

- **What.** The synthesis gives the border four roles that cannot coexist:
  - "used as a reference and a negative control. It is never judged as paint" (line 211);
  - margin anchoring is off by default (line 226);
  - it "must stay grey in B and C" (line 342);
  - warning 4: "the paper border shows colour" (line 264).

  A border never judged cannot light up in C. A border that anchors the reference cannot test it. That is the synthesis's own rule for the session control (line 274).
- **Why it is load-bearing.** The lit margin is [10]'s main per-print sign of a wrong reference, and it is the synthesis's warning 4.
- **Fix.**
  - With anchoring off (the default), the border never enters the fit. It is judged, outlined, and drawn in B and C, and warning 4 is computed from it.
  - With anchoring on, the montage says the border is no longer a control.
  - It tests only paper tones, so it would not catch B1 at face tones.

### B5. "A threshold the paint cannot move" is a slogan at edges

- **What.** Line 227 says: "No term of T is a spread of the same pixels' departures, so a wash cannot raise its own bar". But κ² is fitted from the residuals of the *judged* print's edgy half ([10] §4b), and G is computed on the painted image.
- **On my bench** (same geometry, same print with and without paint):

  | | No paint | Painted (normal) | Wash over 80% |
  |---|---|---|---|
  | κ² | 0.19 | 0.26 | 0.33 |

  | T inside | No paint | Painted |
  |---|---|---|
  | lips | 0.13 | 0.25 |
  | cheeks | 0.086 | 0.102 |
  | the 80% wash | 0.064 | 0.080 |
  | a smooth wash at the T0 floor | 0.040 | 0.040 (unaffected) |
- **Fix.**
  - Fit κ² on the session control's capture (same camera and light, no paint) or on the border.
  - Say that paint which makes its own luminance edges raises G there.

### B6. The blank sentence describes a yardstick the engine does not use

- **What.** Line 259 says: "by more than this capture's own error". That was [11]'s yardstick, the capture's own spread. The adopted T excludes model error by design.
  - The strip ("set into this capture's own residual … as C would draw them") also describes [11]'s rule.
  - Under the witness rule, C needs two photographs, while the strip sits under D and is drawn from one.
- **Fix.**
  - Reword: "by more than this capture's pixel noise or a fixed minimum; errors in the tool's model show as colour (compare D)."
  - Draw the strip's C row only when a second photograph exists, from both photographs.

### B7. D carries the worst failure, contradicts unpainted captures, and is tested last

- **What.** D ×4 comes with the rule "one family of hue running smoothly from paper to shadow; a hue foreign to the paper and the shadows means the model took paint for the print". But the model can only draw smooth curves. Contamination therefore appears as a smooth turn in hue, and so do auto white balance (AWB), tone curves and split toning.
- **On my bench** (`d_tell.jpg`):
  - D for an *unpainted* split-toned print in capture A runs from yellow shadows (hue 86–92°) to bluish paper (−103° at L\* 90). It breaks the rule with no paint at all.
  - With the 80% wash absorbed, D differs only in where the blue sets in (L\* 80 instead of 90) and in slightly lower chroma. Side by side the two are hard to tell apart; seen alone, impossible.
  - [10] and [11] showed ×4 exposing washes in hues foreign to toning (olive, orange). A cool wash over a warm print, in an AWB capture, falls inside the family.
- **Why it is load-bearing.** §7.3 makes D the only sign of B1's case, and §4.9 lists it first.
- **Fix.**
  - (a) Judge D against the session control's D (same session, same pipeline; the coordinator already writes it), not against an abstract rule.
  - (b) Move a minimal line-up test (a dozen montages, one with a contaminated reference) to step 4, right after D is built.

### B8. A gate with no criteria, and an orphaned test

- **What.** Validation is "the first gate" (§6), and "the real-capture gate decides everything" (§7.1). Yet the synthesis contains no pass/fail criterion.
  - [09] §8, [10] §11, [11] §10 and my own pass condition were all dropped.
  - Line 226 and §7.5 still defer the margin decision to "test F6", which exists only in [10].
  - "Must beat DStretch" (§2) has no measure.
- **Fix.** Add one short section:
  - (i) the control, in "seen in both": no coherent area beyond specks in more than 1 pair in 10;
  - (ii) conservator-marked moderate and strong paint shown at least as well as the DStretch or eyedropper baseline;
  - (iii) A, D and B against A–D with C: if they are equal, drop C's machinery;
  - (iv) a broad-wash print does not show its unpainted areas in C (B1);
  - (v) F6, restated;
  - (vi) the line-up test above chance.

### B9. The opacity ramp and the gate disagree

- **What.** C's opacity is "0 at T/2, ½ at T" (line 245), which is [10]'s single-capture ramp. But the witness counts a departure only where "both photographs exceed T" (line 233).
  - The ramp's lower half is dead. Every drawn departure starts at ½ opacity: a hard edge, in effect a segmentation, which "no tiers" was meant to prevent.
  - [09] had a lower per-capture bar (1.5 units), because agreement earns it.
- **On my bench.** Gating at T/2 instead raises the control's false colour from 0.5% to 1.8%, and the painted print's from 0.2% to 1.1%.
- **Fix.** Keep the gate at T, and ramp from T to 2T (0 at T).

### B10. A retracted premise still carries the automatic default

- **What.**
  - Line 106: "The reference is automatic by default. The user's record settles this."
  - Line 139 cites "The user's recorded reason for dropping Chroma mode" via [08] §7. But [08] quoted the assistant's gloss ("keep the pictures and drop the picking") as if it were the user's words.
  - Lines 131 and 358 demote that gloss.
  - The primary sentence is ambiguous. The commit's own gloss reads "the chroma viewer" as Chroma mode (good pictures, bad workflow). The synthesis reads it as "the old visualiser's pictures were helpful".
- **Fix.**
  - Mark automatic-by-default as the coordinator's choice, pending the author.
  - Add "Would you draw two to four boxes per print?" to step 2 of §4.8.
  - Quote the sentence with both readings.

### B11. "Done with this delivery" is not done

- **What.** §4.8 step 1 says 4.1.2's leftovers are removed "with this delivery". At HEAD 74db2bb (a `.gitignore` commit only), they are all still there:
  - `Chroma_diagnoser_v4.1:953` (LRC band counts);
  - `:1359` (the threshold in the footer);
  - `:1672` (thresholds in the CSV);
  - README lines 20, 25 and 66.
- **Fix.** Do it, or write "to do now".

### B12. An advocate's bench parameter is stated as a fact about the objects

- **What.** The synthesis says "real Van Der Zee washes of about 1 ΔE" (§3) and "Thin Van Der Zee washes (about 1 ΔE)" (§7.7).
  - The source is [02]'s bench choice (1.3 units).
  - That choice rests on a *search summary* of NGA *Facture* 7: thin washes "prevented identification … even with in situ analysis". That is a statement about identifying colourants, not about colour difference.
  - [02] never read the article itself.
  - The §3 row credits [07], [09] and [11] jointly. The figure is [11]'s, via [02].
- **Why it is load-bearing.** It justifies moving faint washes into B, and it calibrates the strip (1.3 ΔE).
- **Fix.** Label it an assumption, and measure ΔE on the conservator-marked print during the test captures.

### B13. Two colour spaces under one decomposition

- **What.** Departures and T are computed in χ ([10]). D and B are drawn in Oklch or CIELAB ×4 ([11]).
  - [11]'s reasons for the 2×2 layout and the blink ("D + B = the capture ×4", "only departures flash") hold only within a single space.
  - B and C can therefore disagree tone by tone. Under a fixed threshold, [10] §3 had the same paint at 1% in CIELAB against 83% in χ.
- **Fix.**
  - Render B as the display-space difference between the capture and the reference rendered into that space, so that D + B = capture ×4 holds.
  - Say that B and C use different measures.

### B14. The session control tests the capture, not the reference, and its constant was calibrated under another rule

- **What.**
  - §4.9 counts the quiet control as a check on C. But the control holds no paint, so it cannot reveal reference contamination (B1).
  - Its specks constant (0.5%) comes from [09]'s pairs under [09]'s unit, which gave 0.0–0.4%.
  - Under the adopted T, my bench's control pair sits at exactly 0.5%, on the line.
- **Fix.**
  - State what the control tests.
  - Recalibrate the constant under the adopted T.

---

## C. Verdict

**Where the synthesis is more than my maximum honest version**
- **An automatic reference that needs no marks:** place votes, a high-breakdown fit and a joint light field.
  - With two photographs it beat my marks-based pair on my own bench: 0.2% false colour with 88.5% of the faint wash, against my 0.0% with 78.9%.
  - Boxes become optional and examined at the object, which is better than my on-screen marks.
- **Log-chromaticity departures**, compared at the camera's chroma resolution.
- **The session control, the strip and colour-deficiency-safe drawing in C.**
- **Finding the print, and capture advice.**
- **The DStretch and eyedropper baselines, and the line-up test.**
- **Asking the author.**
- **An honest retraction record**, and cross-bench testing in [10].

These are real gains, and in the normal case my own bench confirms them.

**Where it is secretly less**
- **No criteria.** My Part 2 had a pass condition, and three merges had falsification tests. The synthesis has none, and cites one that is not there (B8).
- **Fail-safe was traded for fail-visible, without the visibility.**
  - My unit lowered sensitivity where marks disagreed, and said so.
  - [10] made failures show as colour, and gave a table of their signatures.
  - The synthesis kept [10]'s fixed threshold but dropped the signature table and the self-checks. It caps warnings at two, and only one (the border, at paper tones) concerns reference contamination.
  - Its worst failure is a confident C on unpainted areas that two photographs agree on (B1), plus a single-photograph C via boxes (B2).
- **D carries more than it can bear (B7).** The border check is neutralised (B4), and the blank sentence describes the wrong yardstick (B6).
- **It claims work as done that is not (B11)**, and treats a gloss as the user's mandate (B10).

**Claims that rest only on the advocates' own evidence.** Every number does, as §1 says. These ones are load-bearing and should be marked:
1. **The witness brings false colour down to 0.0–0.4%.** This comes from [09]'s bench and mine, which share Beer–Lambert washes and a caricature of a phone. Under the synthesis's own engine, my bench gives 0.5% on the control and 22.4% on a broad-wash print's unpainted areas.
2. **Chroma mode's mechanism (27–62% flagged under tone shift).** This comes from four simulators.
   - The only primary record (66d03e7) is about user-friendliness.
   - Woodii's own design note had already listed tone shift with density as a known limitation, before the run.
3. **"Van Der Zee washes ≈ 1 ΔE"** is a bench parameter (B12).
4. **"D ×4 reveals contamination."** This holds on [10]'s and [11]'s benches, for washes in hues foreign to toning. My bench contradicts it for a cool wash (B7).
5. **Votes fix tones that are mostly painted (AUC 0.66 → 0.83).** This rests on [11]'s bench alone. Votes fitted by LTS → MM were never tested by the advocates. On my bench the normal case works and the broad wash fails.
6. **A fixed T beats an adaptive spread.** This rests on [10]'s S7/S8, with the price omitted (B3).
7. **χ beats CIELAB (1% against 83%).** This depends on the T0 conversion the advocate chose, as [10] itself says.
8. **The chroma-resolution comparison cuts false colour by 10–50%.** This is from [10]'s benches only.
9. **Phones' semantic processing of faces and skies puts colour where colourists worked.** The sources are vendor marketing and press (Smart HDR 4, via MacRumors and Trusted Reviews). No agent tested a phone photographing a monochrome print. This is agreement on a hypothesis, not evidence.

**Bottom line.** Make the two cheap changes before the gate: take boxes out of C's witness (B2), and say plainly that a broad wash can make C show unpainted areas in both photographs, with a criterion to test it (B1, B8). The rest is wording, wiring and order (B3–B14).

**Files** (all in `/home/user/xpw/6d8ad6/work/redteam2/`):
- `synth_engine.py`: the synthesis's engine, as I read the spec.
- `seams.py` and `seams.json`: the table above.
- `own_bar.py` and `own_bar.json`: B5.
- `boxes_fix.py`: B2's floor test.
- `d_tell.py`, `d_tell.json` and `d_tell.jpg`: B7.
- `ghost_fig.py` and `ghost_pair.jpg`: B1.
- `edge_recheck.py`: my withdrawn edge claim.
