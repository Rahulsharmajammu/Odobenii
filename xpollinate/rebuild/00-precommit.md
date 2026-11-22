# Pre-committed answer (22 Nov 2026, before any agent report)

Written by the coordinator, outside every tree the agents are pointed at, before any agent was launched.

## The request

Analyse the earlier versions of the handpaint visualiser (v1.1/1.2 Tk GUI, v3.0, v4.0/4.1, now 4.1.2), Woodii's
Chroma mode (a later attempt at the same aim, removed after its first real run), and the plan I wrote in TODO.md.
Then give the best design for a rebuilt visualiser. The user's constraints: show the presence, or absence, of paint
on monochrome photographs; no colorimetric accuracy; nothing that invites a quantitative reading; inputs are
"unruly visualiser captures" (uncontrolled, probably phone or document-camera JPEGs, auto white balance, uneven light);
no luminescence or IR. The user liked "chroma boost around neutral".

## The reframe

The tool's job is not to detect paint. It is to make departures from the print's own monochrome tone easy to see,
and to be honest about where it cannot see. Everything hangs on the reference for "unpainted". A monochrome print's
unpainted colour is not neutral grey and not a single colour: it is a curve in colour space, paper colour at the top
and image tone (warm, cold, toned, yellowed) in the shadows. Paint is a departure from that curve. Every earlier
version measured departure from neutral grey (v1.2, v3.0, v4.1 raw C\*ab), or from statistics of the whole image (the
noise floor, LRC). Both break on warm prints and on prints with a lot of paint. Woodii got the reference right
(picked untinted areas) but tied it to raw captures, noise physics and an apparatus nobody would run on a phone JPEG.

"Chroma boost around neutral" fits this: subtract the print's own tone, so it renders neutral grey, then amplify
only what is left.

## The answer

A small batch tool, plus an optional picker, built in this order:

1. **Load.** Any ICC profile converted to sRGB (LittleCMS); untagged files taken as sRGB; EXIF orientation applied;
   16-bit read and reduced. Drop the analytic Adobe RGB / ProPhoto paths.
2. **Working size.** About 2,500-3,000 px on the long edge, area-averaged. Presence does not need 100 MP; averaging
   tames noise and JPEG chroma blocks. The output pictures are at this size.
3. **CIELAB** (D65, display-referred). Light smoothing of a\* and b\* only (median about 5 px, or a guided filter
   steered by L\*), so JPEG 4:2:0 chroma noise and blocks fall away and lightness keeps its detail.
4. **Not judged.** Masked and drawn as "not judged", never as "no paint":
   - near black (L\* below about 8-10);
   - clipped or glare highlights (any channel near 255, or a specular blob);
   - strong edges where lateral colour or chroma subsampling makes fringes (an edge guard on |∇L\*|);
   - outside an optional object box.
5. **Reference ("unpainted").** a\*(L\*) and b\*(L\*) as smooth curves (binned medians, smoothed, interpolated), with
   a robust spread s(L\*):
   - **Default, automatic:** fit on all usable pixels, trim the pixels furthest from the fit, refit, three to five
     rounds. This assumes unpainted pixels are the majority at each lightness. The picture says "automatic
     reference".
   - **Override, picked:** one or more boxes on paper and untinted image, in a sidecar `<image>.picks.json`, made
     with a tiny picker (a matplotlib or web page window). A folder-wide default is allowed. The picture says
     "reference from picks" and outlines the boxes.
   - **Optional spatial tilt:** a low-order plane in (x, y) added to the reference, fitted on the same trimmed or
     picked pixels, for a colour cast that changes across the frame (window light on one side). Off by default.
6. **Feature.** The residual vector r = (a\*, b\*) − ref(L\*, x, y):
   - z = |r| / s(L\*), how far from the print's tone in units of its own variability;
   - hue = angle of r.
   A vector, so a blue wash over a warm print, which lowers C\*ab, is still found.
7. **Pictures** (no numbers anywhere):
   - **Original.**
   - **Boosted:** L\* kept, a\*b\* replaced by G·r. The print's tone renders neutral grey and paint shows in an
     exaggerated version of its own hue. Continuous, no threshold. This is the main view. A switch keeps the print's
     tone instead.
   - **Presence map:** the print in dark grey, with colour laid over it: hue from r's angle, opacity a smooth ramp of
     z (about 2.5 to 5), no tiers. "Not judged" areas are hatched.
   - **Footer, in words:** "Visualisation only - not a measurement", the reference source, and warnings: heavy JPEG;
     glare left out; reference covers little of the tonal range; much of the frame departs from the reference, so
     the reference may be wrong.
8. **Sensitivity:** three presets (low, normal, high) that move the ramp. The value goes in the JSON only.
9. **Outputs:** the montage, each panel, and a JSON provenance record (source hash, settings, reference source). No
   masks, no TIFFs, no CSV of statistics. The run log lists failures with their reasons.
10. **Code:** one module of about 600-800 lines (`handpaint.py`), a picker, and tests on synthetic prints. A `.py`
    file; the version in git only; v3.0 and v4.1 removed from the tree (they stay in history).
11. **Validation, before anything else is added:**
    - a known-untinted print captured badly (phone, mixed light) as the negative control;
    - known hand-coloured prints with paint marked by a conservator;
    - the same print captured three ways, to see if the picture is stable.

## Answer to the hard question

*For each uncontrolled capture, how should the tool establish what the unpainted photograph looks like, and how would
someone looking at its output know when that has gone wrong?*

**How the reference is established.** As a smooth curve of colour against lightness, the print's own tone, with an
optional gentle spatial tilt. By default it is estimated from the image itself by robust trimming, which assumes most
pixels at each lightness are unpainted. From picked unpainted areas whenever paint is extensive, or whenever the
automatic one looks wrong.

**How the viewer knows it has gone wrong:**
- The boosted panel renders the reference as neutral grey. A wrong reference shows as a broad colour cast over areas
  the viewer can see are unpainted (the margin, untinted shadows), and the eye is good at that.
- The picture states which reference was used and outlines any picks.
- Words in the footer when the fit is poor or the reference does not cover the tonal range.
- "Not judged" areas are drawn as such.
- Absence is only "no departure from the print's tone that this capture can show". Paint matching the print's tone
  (grey or black retouching, sepia-matching paint, white highlights) is invisible to any colour method. The README
  and the footer say so.

## Least sure about

1. **Whether the automatic reference survives real Van Der Zee prints:** painted backgrounds that fill a whole tonal
   range; split or uneven toning; staining and silver mirroring that colour unpainted areas. And whether the author
   will tolerate a pick per image. ("If it is not easy, nobody will do it.")
2. **Whether phone pipelines break the premise.** Local tone mapping, saturation boosts, skin smoothing and noise
   reduction can make unpainted colour vary in space in ways no smooth model captures, and can erase faint paint.
3. **Whether the presence map earns its place.** It may invite exactly the confident "no paint here" reading the
   user wants to avoid. Boosted panel plus a slider might be the better product, which argues for an interactive
   viewer over batch montages.
4. **Whether CIELAB is the right space.** It is perceptual, not physical; a ratio or log-RGB angle might be steadier
   under uneven light.

## What would change my mind

- **Real captures** where untinted areas vary in colour more than paint departs from them: I would drop the map and
  keep only the boosted view, with honest words.
- **The author saying picks are too much work:** automatic only, with the failure stated plainly.
- **Evidence that conservators read colour on photographs mostly in an interactive viewer:** I would build that first
  and make the batch montage secondary.
- **A much simpler method doing as well on real captures** (e.g. white-balance on the paper, then a plain saturation
  boost): take the simpler one.
- **Evidence that Woodii's Chroma mode failed for a reason this design shares:** e.g. picks that users could not make
  well, or a reference that no real print fits.
