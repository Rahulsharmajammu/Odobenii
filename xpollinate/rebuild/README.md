# Rebuilding the handpaint visualiser: an xpollinate run

22 November 2026. The run used the xpollinate skill from
[nickjrotundo/agent-skills](https://github.com/nickjrotundo/agent-skills). The request was to analyse the
visualiser's earlier iterations, Woodii's removed Chroma mode and the plan in TODO.md, and to find the best design.

The plan that came out of it is `../../TODO.md`. This folder holds the reasoning and the evidence behind it.

> **Later notes (22 Nov), in `03-author-answers.md`:**
> - **§5:** the captures will be controlled and ICC-calibrated (DSLR or mirrorless), not the phone snapshots the agents
>   assumed. Finding 3 below, the second-photograph requirement and the phone-specific handling no longer apply as the
>   default.
> - **§6:** the visualiser is a viewer of one ProPhoto photograph per print. Infrared goes to a separate Woodii module.
> - **§7:** the boost's leading candidate is a guarded decorrelation stretch, in a few colour spaces.
> - **§8:** Woodii's IRR is at 850 nm, and the two tools are written separately, on purpose.
> - **§9:** the single view is a local web app like Woodii's, built before the gate as its instrument.
> - **§10:** the Woodii module's note moved to Woodii; a stretch on Woodii's stacks stays a to-do.
> - **§11:** the gate passed on real test captures (23 Nov); a known issue (low-frequency false colour); the app is
>   renamed Odobenii.
> - **§12:** your answers to the divergence check (`04-divergence.md`): the strip from the print itself; the departure
>   picture stays.

> **Read this first: limits of everything here.**
> - **No real capture of any print was available.** Every number comes from synthetic test images that the agents
>   built themselves, and they encode the agents' own assumptions about prints and phones.
> - **The benches disagreed.** Each method looked best on its own bench, and the rankings moved when benches were
>   swapped.
> - **All agents are the same model family** as the assistant that wrote the earlier plan. Their agreement is weak
>   evidence. Retractions, and findings the control did not reach, carry the weight.
> - The real-capture gate in the synthesis (section 4.10) decides everything.

## How to read it

1. **`02-synthesis.md`**, sections 4 (the design) and 8 (what the red team left standing). Each idea is tagged
   with the report it came from. **[coordinator]** marks ideas that appear only in the synthesis, and
   **[Amended, B#]** marks fixes adopted after the final red-team pass.
2. **`03-author-answers.md`**: your answers to the plan's four questions and your later notes, and what they change.
   Where they conflict with the synthesis, they win.
3. **`04-divergence.md`**: how Odobenii, as built and through the gate, diverges from the synthesis (25 Nov).
4. **`05-reviewers.md`**: the twelve reports point by point, against Odobenii as built (25 Nov).
5. **`00-precommit.md`**: the coordinator's own answer, written before any agent started. Section 6 of the
   synthesis diffs against it.
6. **`reports/`**: every report, saved verbatim.

| Report | What it is |
|---|---|
| 01 control | The request alone, no standpoint: the model's default answer |
| 02 conservation | Photograph conservation and technical examination |
| 03 perception | Visual perception and visualisation design |
| 04 remote sensing | Target and anomaly detection under uncontrolled light |
| 05 camera pipeline | Camera and phone image processing |
| 06 history | The two repositories' history, and a premortem |
| 07 red team | "The request is ill-posed", then the strongest honest version |
| 08 audit | Bias in how the coordinator's earlier review, test and plan were produced |
| 09 merge | History, revised against the red team |
| 10 merge | Camera pipeline, revised against remote sensing |
| 11 merge | Perception, revised against conservation |
| 12 red team, final | Seams the synthesis created, and a scorecard |

7. **`01-design.md`**: who was asked what, what was withheld, and what happened during the run.

## The findings that changed the answer most

1. **Your recorded reason for removing Chroma mode was "not very user friendly"** (Woodii 66d03e7), and the earlier
   plan had not read it. The plan was built on per-image picks; now nothing is required of the user per image.
   Whether the picks were what failed is not recorded, so it is the first question in TODO.md.
2. **Woodii's Chroma mode probably failed on its method as well.** Four agents ran its code on separately written
   simulators. It flagged 27–62% of *unpainted* prints whose tone shifts slightly with density, because it measured
   departures against sensor noise from small picks, around a straight axis. This is still a hypothesis about the
   real print.
3. **One photograph cannot tell paint from the light.** On every bench, a single uncontrolled capture showed false
   colour somewhere (a few percent to over 40%). A second photograph under different light, with only what both
   agree on drawn, brought unpainted prints to 0.0–0.5% on two independent benches. So the departure picture
   appears only with a second photograph. With one photograph the tool still gives three pictures: the photograph,
   the print as it assumes it unpainted, and the boost around the print's own tone.
4. **The tool must show its own assumption, exaggerated** (the "expected unpainted ×4" picture). It must judge
   departures against a threshold the paint cannot raise. Measured against a spread of the same pixels, a large
   wash raised its own bar and vanished.
5. **The known weak point, from the final red-team pass.** When a broad wash covers most of a print at some tone,
   it enters the reference. Unpainted areas at that tone then show in the departure picture in the opposite colour,
   in both photographs. There is no validated fix: it is stated, its signature goes in the README, and it is a gate
   criterion.

## The next action

Make the gate's two test captures with the real setup, as 16-bit ProPhoto TIFFs:
- a known-unpainted print;
- a print whose faint washes a conservator has marked.

Nothing else is built until the first build passes on those (`TODO.md`). The Woodii module's captures come later,
through Woodii.

## Figures (synthetic, downscaled; in `figures/`)

| File | What it shows | From |
|---|---|---|
| 01-merged-montage-thin-washes.jpg | The merged 2 × 2 layout: capture, where colour departs, expected unpainted ×4, departures ×4 | [11] |
| 02-votes-fail-wash-over-most-places.jpg | A wash over most places at a tone defeats the place votes: unpainted face and hair glow orange | [11] |
| 03-strip-thin-wash-in-capture-noise.jpg | The strip: a thin wash set into this capture's own noise, per tone | [11] |
| 04-colour-vision-deficiency.jpg | An overlay at the print's own lightness is lost to red–green deficient viewers; bright on dim survives | [03] |
| 05-assumed-unpainted-turns-olive.jpg | A wash over the whole picture is absorbed; only the expected-unpainted picture turns olive | [09] |
| 06-seen-in-both-unpainted-mixed-light.jpg | An unpainted print under mixed light: quiet in "seen in both" | [09] |
| 07-complementary-ghost-in-both-photographs.jpg | The final pass's B1: unpainted areas lit in the complementary colour, in both photographs | [12] |
| 08-reference-picture-weak-for-cool-wash.jpg | The final pass's B7: the reference picture of an unpainted split-toned print already turns hue | [12] |
| 09-todo-plan-failures.jpg | The 22 Nov plan as written: false colour on an unpainted print; a pick on a wash; an absorbed wash | [07] |
| 10-fixed-threshold-false-colour.jpg | Where the fixed threshold's false colour sits: margin corners, and a complementary ghost | [10] |
| 11-control-compare-methods.jpg | What each method draws (v1.2, v4.1, Woodii, TODO, the control's prototype) on six cases | [01] |
| 12-table-in-frame-silent-failure.jpg | A table in frame takes over the dark tones: a silent failure in the departure picture | [02] |

## The agents' code (`work/`)

Each agent's own prototype, bench and result tables, by role. Copies of historical versions, data and images are
left out. The reports cite these files under `/home/user/xpw/<id>/work/`, a path that no longer exists:

| Role | Path cited in the report |
|---|---|
| 01 control | 7984d2 |
| 02 conservation | ad19d6 |
| 03 perception | 45b29c |
| 04 remote sensing | 9e3d5c |
| 05 camera pipeline | d99a4c |
| 06 history | 121087 |
| 07 red team (and 12) | 6d8ad6 |
| 08 audit | 257605 (its `material/` is the coordinator's earlier review, test scripts and printed results) |

The scripts expect the bench images, which were not kept; each `synth.py` or `sim.py` regenerates them. The
control's `hpv.py` has eight passing tests (`tests/test_hpv.py`).
