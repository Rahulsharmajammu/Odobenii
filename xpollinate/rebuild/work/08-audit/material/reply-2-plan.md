# The assistant's reply to message 2, verbatim

The quantitative outputs are out of the script (now 4.1.2), and the rebuild checklist is written as `TODO.md`; both are pushed to `ccr-32ef416e-z8q8ld`, with no pull request opened. The stripped script ran end to end on my seven synthetic images; the detection itself is unchanged, so it still misses large painted areas until the rebuild.

## What I removed

- **Area figures:** the "Area: x%" in the montage footer, the percentages on the console, and the area fields in the JSON and CSV.
- **Statistics:** component counts and sizes, and the mean, median and max of each feature.
- **Sensitivity analysis:** the Jaccard threshold-stability run and its options.
- **Numerical files:** the float and 16-bit feature TIFFs and the categorical mask.
- **Wording:** "FADGI-compliant", "metrology" and "scientific integrity" in the script and README.

Every picture now carries "Visualisation only - not a measurement". The batch CSV is now a plain run log, renamed `summary/run_log.csv`. Threshold histograms are off unless you pass `--histograms`.

Threshold values stay in the JSON record and run log as settings, so a run can be repeated. Say if you want those gone too.

## One clarification on the boost

My suggestion was to boost around the substrate's colour, not around neutral; today's script boosts around neutral, which is why a warm print turns orange. I think what you want is the version where the substrate's own tone is drawn as neutral grey and only the departure from it is amplified. That is what I put in the checklist as the proposal.

## Proposed flow for the rebuild

1. **Load:** convert any ICC profile to sRGB, treat untagged files as sRGB, and drop the separate Adobe RGB, ProPhoto and 16-bit paths.
2. **Working size:** downscale to about 3000 px on the long edge, which also tames noise and JPEG chroma blocks.
3. **Smooth colour only:** a small median on a\* and b\*, leaving lightness alone.
4. **Leave out what can't be judged:** glare, clipped highlights and near-black, drawn as "not judged" and never as "no paint".
5. **Reference:** from picked unpainted areas, take the substrate's colour and spread at each lightness. An automatic fallback is labelled as such on the picture.
6. **Feature:** the vector from the substrate's colour to the pixel's colour. Its length is "how far from substrate" and its angle is "toward which colour", so a wash that lowers chroma is still found.
7. **Specks:** a small median in place of the 100 px component filter, so small touches survive.
8. **Pictures:** Original, Boosted, and a Presence map with hue from the vector's angle and opacity rising smoothly, so faint paint shows bright and there is no hard boundary to read.

For unruly captures, the main risk is a colour cast across the frame reading as faint paint. The checklist has an optional later step that lets the reference tilt with position when picks are spread across the frame.

## Decisions I need from you before building

- **How the unpainted reference is supplied.** I propose boxes drawn once per image in a small picker and saved beside the image, with the automatic fallback when there are none. This costs a pick per image; the fallback alone will fail on heavily painted prints.
- **Substrate in the boost panel:** neutral grey (my proposal) or the print's own tone kept.
- **Raw C\*ab and LRC:** I propose dropping both for the single new feature; v4.1 stays in the history.
- **Layout:** a small package with tests on synthetic prints, or one script as now.
