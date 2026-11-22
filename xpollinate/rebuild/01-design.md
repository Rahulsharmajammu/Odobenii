# Xpollinate design

22 Nov 2026. Task type: evaluating a plan (TODO.md) and the prior iterations, then design ("how would you build
X"), with an audit of prior work run alongside, because the plan, the review behind it and its synthetic test were
all written by the coordinator in this same conversation.

## Hard question (identical wording to every agent)

"For each uncontrolled capture, how should the tool establish what the unpainted photograph looks like, and how would
someone looking at its output know when that has gone wrong?"

The whole design turns on this. Any boost, map or threshold measures departure from something, so every approach
needs an answer, including "neutral grey" or "the human decides". The second clause covers the user's "presence, or
lack thereof": absence is the claim a viewer is most likely to over-trust.

## Agents

All are general-purpose agents on the session's model (Opus 5.5), run in the background, each with its own opaque
working directory under /home/user/xpw/ (mapping in agent-dirs.json, kept here).

| # | Agent | Why chosen | Expected to catch |
|---|---|---|---|
| 01 | Control | Verbatim request and shared context, no stance | The model's default prior |
| 02 | Photograph conservation and technical examination | The domain: how hand-colouring on silver prints is actually examined, and what it is confused with | Confounders (toning, mirroring, staining, retouching); what the user really needs to decide |
| 03 | Visual perception and scientific visualisation | The output is a picture a person reads | Whether the panels make presence and absence legible; misleading colour maps; false confidence |
| 04 | Remote sensing: target and anomaly detection under uncontrolled illumination | A field that detects materials in images nobody lit, a different root from colour science | Background-model failure modes; illumination-invariant features; scene-based normalisation |
| 05 | Computational photography and camera pipelines | "Unruly captures": what the camera does to colour before the file exists | Artefacts that mimic paint or erase it; whether colour constancy can be had cheaply |
| 06 | Software history and premortem of this project | Five iterations and a removed sibling feature | Reinventing a known failure; the GUI that was dropped; the second-system pattern |
| 07 | Red team | Is the request ill-posed? | Whether "optimal" or "presence and absence" can be had at all from such captures |
| 08 | Audit of prior work | The coordinator wrote the review, the synthetic test and the plan | Conclusion in the framing; a test built to confirm; claim escalation across versions |

## Shared context (identical for 01-07; it is not framing)

- The repositories, read-only, history through git log / git show.
- The pointer to Woodii's Chroma mode code and design note.
- The author's standing positions written for Woodii, flagged as written for another project.
- That no real captures are available here.
- The installed packages.
- Write only in the agent's own directory; no subagents or skills.

The audit (08) gets its own template with the prior work: the coordinator's two replies, the synthetic test, the
plan, and the earlier versions' self-descriptions.

## The user's request as given to agents

The user's three messages, verbatim and oldest first, because the third is not understandable without the first two
(the aim, and the constraints). One edit: the opening of message 3 ("Hm. Please use xpollinate from
https://github.com/nickjrotundo/agent-skills") is omitted. Passed on, it would tell each agent to run this protocol
itself. The omission is marked in the agents' copy as "its opening words, which named a tool for the assistant to
use, are omitted".

The assistant's replies are withheld from 01-07. TODO.md, the plan they produced, is in the repository and is what
the user asked to be analysed, so all agents see it.

## What convergence would prove

If the control produces the same skeleton as the stance agents, that is a model prior, not independent
confirmation. Convergence counts only where a stance agent reaches a conclusion the control did not.

Every agent reads TODO.md, so agreement with TODO.md is partly inherited and counts for little. Agreement with
AUTHOR-POSITIONS.md is the user's own position, not evidence. All agents share the coordinator's model family.

## What is withheld from all agents

- This file and 00-precommit.md, kept in the coordinator's scratchpad, outside every path the agents are given.
  (Lesson from the Woodii runs: a pre-commit inside the reviewed tree was read by half the reviewers.)
- The other agents and their reports.
- The coordinator's earlier review and its synthetic test results (except for 08, whose job they are).

## Limitations known in advance

- **No real captures.** Every experiment an agent runs is on synthetic images it built, which encode its own
  assumptions.
- **One model family throughout.**

## Notes added during the run

- **Report files.** The harness refused report files written by subagents. Every agent returned its report as
  text, and the coordinator saved each one verbatim in reports/, with the agent's own one-line preface and the
  harness's indentation removed.
- **The repository changed once, without content.** One agent imported the visualiser script by path, leaving an
  untracked `__pycache__`. The coordinator removed it and committed a `.gitignore` (74db2bb) mid-run. Two agents
  noticed that commit.
- **No contamination found.** No report mentions the pre-commit or this file.
- **Rate limit.** A five-hour API limit stopped all three cross-pollination agents at their first step (06:56 UTC).
  They were resumed with their own contexts after the reset (13:01 UTC), not replaced.
- **The merges:**
  - [09] history × red team, with history integrating;
  - [10] camera × remote sensing, with camera integrating;
  - [11] perception × conservation, with perception integrating.
- **The final red-team pass** ([12]) built the synthesis's engine from its text and found two seams the merges
  created: the complementary ghost (B1) and boxes as a witness (B2), plus twelve smaller ones. The synthesis was
  amended in place, each amendment marked "[Amended, B#]", and section 8 records the status of each seam.
- **4.1.3.** After the final pass, the coordinator applied 4.1.2's leftover removals (red-team seam B11), ran the
  result on the coordinator's synthetic set, and committed it separately.
