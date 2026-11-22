# handpaint_visualiser
A quick tool to visualise colour applied to monochrome photographs, initially developed for the Van Der Zee applied media project at The Metropolitan Museum of Art

**A visualiser, not a measuring tool.** Its pictures show where colour stands out from a monochrome substrate. They are qualitative: the tool reports no areas, counts or statistics, and its colour handling is only as careful as a legible picture needs.

The program boosts the colour in a photograph and draws where colour stands out from the image's own colour statistics, to help the eye find faint colour on paper, parchment or canvas. It does not identify pigments, and a place where nothing is drawn is not shown to be unpainted.

There are two programs:
- **the web app** (`python -m handpaint.app`), new: one photograph at a time, with the decorrelation stretch, and batch runs. It is built and tested on synthetic prints only; real captures decide (`TODO.md`, the gate);
- **the batch tool** (`Chroma_diagnoser_v4.1`), described further below.

## The web app

```bash
pip install -r requirements.txt
python -m handpaint.app            # opens http://127.0.0.1:8766/ in your browser
```

It is built like Woodii's app: a local server on 127.0.0.1, so photographs stay on this computer, with Woodii's checks against other web pages (a per-launch token, local host names only, no cross-site requests). Options: `--session FOLDER` (default `~/handpaint_sessions/default`), `--port`, `--no-browser`. Stop it with the page's Stop server button or Ctrl+C. The session folder keeps files added from the browser, each photograph's print area and boxes, and the settings.

Open a folder of photographs (16-bit ProPhoto TIFF from your raw converter is best; any ICC-tagged file is read through its profile), pick one, and flip between five pictures with keys 1-5:

1. **The photograph.**
2. **Boost:** the print's own tone drawn neutral grey, and departures from it multiplied by the strength.
3. **Stretch:** a decorrelation stretch of those departures.
   - Two colour spaces: CIELAB (departures as they look) and density (as amounts of colourant, so a wash over the dark tones shows as strongly as over the light).
   - Three emphases: balanced, red-green and yellow-blue.
   - Three guards, on by default and each with a switch, so a plain stretch can be compared: the print's own tone is removed first; the statistics come from the unpainted print (or your boxes); no direction gains more than twice another.
4. **Expected unpainted ×4:** the tool's assumption about this print, exaggerated. It should show the print's own tone and no forms.
5. **Where colour departs:** drawn bright on a dimmed print (so colour-deficient viewers see it), from a threshold that measured noise can raise but the paint cannot.

"The print's own tone" is a smooth curve of colour against lightness, fitted per print to votes of places with a high-breakdown fit, so local paint cannot become the reference.

The other tabs:
- **Look:** draw the print area, and box areas you have examined on the object and know are unpainted. Boxes are cross-checked, and a box that disagrees with the others is not used.
- **Check:** the strip, a thin wash set into this capture's own noise at each tone, and what the pictures cannot show.
- **Export:** the picture shown as a PNG with its words printed under it, or a batch run over a folder (no boxes are used in batch runs).

Compare puts two pictures side by side, panned and zoomed together, or one at a time (F flips).

Tests: `python -m pytest tests` (needs pytest and tifffile).

## The batch tool (4.1)

**Known limitation.** With the default `noise_floor` threshold, the threshold is set from the image's own chroma histogram, so it rises with the paint: the Segmented panel can miss large painted areas, and a blue wash over a warm print can lower chroma and disappear. The Chroma Boosted panel still shows them. The web app addresses this; see `TODO.md`.

**Output**


The tool generates a 3-panel montage for every image processed:
*Original*: The raw input image.
*Chroma Boost*: Linearly expanded color variance to highlight general hue presence.
*Segmented Boost Map*: where chroma exceeds the threshold, the boosted colour is drawn over a darkened, texture-enhanced (CLAHE) print; stronger departures are drawn more opaque.

**Cool things**

Adaptive threshold: by default the threshold is set from the image's own chroma histogram (its peak and where the counts fall away). It is a display setting, not a boundary between substrate and pigment (see the known limitation above).

Three display opacities: weaker departures are drawn more transparent and stronger ones more opaque. The levels are relative to each image; they are not classes of paint.

Texture Enhancement: Applies CLAHE (Contrast Limited Adaptive Histogram Equalization) to reveal topology.

Batch Processing: Multi-process engine that processes a folder of images (including 16-bit TIFF/PNG) in parallel across CPU cores.

**Usage**

```bash
pip install -r requirements.txt
python3 Chroma_diagnoser_v4.1 /path/to/input /path/to/output
```

Useful options (`--help` for all):

- `--threshold-mode {noise_floor,percentile,otsu,fixed}` (default `noise_floor`, described below) and `--noise-fraction` (default 0.01; smaller is stricter).
- `--default-colorspace {sRGB,"Adobe RGB","ProPhoto RGB"}`: the colour space assumed for images with no ICC profile or EXIF colour-space tag (default sRGB). Files with an embedded profile are decoded through it:
  - any RGB matrix/TRC profile (sRGB, Adobe RGB, ProPhoto, eciRGB v2, a camera matrix profile, or a linear profile such as Woodii's) from its own colorants and tone curves, at full bit depth;
  - LUT-based profiles analytically when named sRGB, Adobe RGB or ProPhoto, and otherwise with LittleCMS at 8-bit precision.

  32-bit floating-point TIFFs (Woodii's default export) are not read: save them as 16-bit (Woodii: `--data uint16`).
- `--output-scale` (default 0.5): size of the presentation images. Analysis always runs at full resolution unless `--analysis-scale` is set.
- `--max-workers N`: lower this for very large images; each worker needs several GB for a 100-megapixel file.

- `--histograms`: also save a histogram of each feature with its thresholds, as a diagnostic for choosing a threshold.

Each image produces pictures in two feature spaces, raw C\*ab and lightness-relative chroma (LRC), plus a JSON provenance record (source, hash, settings). The batch writes a run log (`summary/run_log.csv`) of what was processed and how. Every picture is labelled "Visualisation only - not a measurement".

**How It Works** 
The processing pipeline:

1. Pre-processing & Normalization
Images are decoded in their source colour space (sRGB, Adobe RGB or ProPhoto RGB, with Bradford adaptation for ProPhoto) and converted to CIELAB (D65). Chroma (colour intensity) is each pixel's distance from neutral in the a\*b\* plane.

2. Statistical Thresholding
The tool makes a histogram of the image's chroma values, takes its peak (usually the paper and the image's own tone), and walks up from it until the counts fall below 1% of the peak. That point is used as the threshold.

3. The "Segmented Boost" Map

The picture is drawn differently above and below the threshold:

Below the threshold: pixels are rendered as dark grayscale to reduce visual distraction. Connected regions smaller than `--min-component-area` pixels are discarded.

Above the threshold: pixels are drawn at three display opacities, set at the median and 85th percentile of what lies above it.

Visualization: weaker departures are drawn more transparent (keeping the print visible), stronger ones more opaque. The opacity shows how far colour departs in this image; it does not tell faint residue from solid paint.
