# Prior work to audit

Produced by an AI assistant in one conversation with the user, before 22 Nov 2026 05:00 UTC, in this order:

1. **Read the code.** The visualiser's `Chroma_diagnoser_v4.1`, and Woodii's Chroma mode (`chroma.py` and
   `docs/chroma-mode-plan.md` at commit 971f484 of /home/user/Woodii) with its removal commit de6f9b1.
2. **Built synthetic prints** with `scripts/synth.py`: six cases plus a 16-bit TIFF of one of them.
3. **Ran the visualiser v4.1.1 on them.**
4. **Scored the outputs** with `scripts/evalcmp.py` against the synthetic ground truth, alongside:
   - a vector feature baselined on the whole image's L\*-band medians;
   - Woodii's `tint_maps` on the linear synthetic data, with hand-placed picks.
5. **Tried a hand-chosen reference** with `scripts/pickref.py`: the vector feature with its reference taken from a
   region chosen by hand per case.
6. **Looked at one output montage** (the pink-wash case, LRC).
7. **Wrote `reply-1-review.md`.**
8. **After the user's second message:**
   - wrote `scripts/strip.py` and applied it to make 4.1.2;
   - ran it, fixed a crash, made histograms opt-in;
   - edited README.md;
   - wrote TODO.md;
   - committed as 4584a2f on branch ccr-32ef416e-z8q8ld of /home/user/handpaint_visualiser.
9. **Wrote `reply-2-plan.md`.**

What each script printed is in `results-as-printed.md`.

Also part of the prior work, inside the repositories:
- TODO.md and commit 4584a2f;
- the earlier iterations' own descriptions of themselves: README history (`git log -p -- README.md`), the docstrings
  of Image_Visualiser_GUI_v.1.2.py (commit 0949bdc), "Chroma Diagnostic Tool v3.0", and Chroma_diagnoser_v4.1 at
  a365ea6 and 6176d62;
- Woodii's docs/chroma-mode-plan.md (at de6f9b1) and the Chroma section of docs/decisions-0.4.md at the same commit.
