# handpaint_visualiser
A quick tool to visualise colour applied to monochrome photographs, initially developed for the Van Der Zee applied media project at The Metropolitan Museum of Art

**A visualiser, not a measuring tool.** Its pictures show where colour stands out from a monochrome substrate. They are qualitative: the tool reports no areas, counts or statistics, and its colour handling is only as careful as a legible picture needs.

The program boosts the colour in a photograph and draws where colour stands out from the image's own colour statistics, to help the eye find faint colour on paper, parchment or canvas. It does not identify pigments, and a place where nothing is drawn is not shown to be unpainted.

**Known limitation.** With the default `noise_floor` threshold, the threshold is set from the image's own chroma histogram, so it rises with the paint: the Segmented panel can miss large painted areas, and a blue wash over a warm print can lower chroma and disappear. The Chroma Boosted panel still shows them. A rebuild that addresses this is planned (see `TODO.md`).

**Output**

![2021 443 694_montage](https://github.com/user-attachments/assets/fb07c8a6-0813-449a-a5dd-b0f9d9ae2760)

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
- `--default-colorspace {sRGB,"Adobe RGB","ProPhoto RGB"}`: the colour space assumed for images with no ICC profile or EXIF colour-space tag (default sRGB). Files with an embedded sRGB, Adobe RGB or ProPhoto profile are decoded in that space automatically. Any other RGB matrix/TRC profile (eciRGB v2, a camera matrix profile, ...) is applied from its own colorants and tone curves at full bit depth; LUT-based profiles are converted with LittleCMS at 8-bit precision.
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
