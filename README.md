# handpaint_visualiser
A quick tool to visualise colour applied to monochrome photographs, initially developed for the Van Der Zee applied media project at The Metropolitan Museum of Art

**A visualiser, not a measuring tool.** Its pictures show where colour stands out from a monochrome substrate. They are qualitative: the tool reports no areas, counts or statistics, and its colour handling is only as careful as a legible picture needs.

The program, as is, utilizes statistical color analysis to separate faint pigments, washes, and residues from substrates (paper, parchment, canvas).
Unlike standard saturation sliders, this tool algorithmically calculates the "Noise Floor" of the substrate to isolate legitimate color signals, creating high-contrast visualizations that reveal details invisible to the naked eye.

**Output**

![2021 443 694_montage](https://github.com/user-attachments/assets/fb07c8a6-0813-449a-a5dd-b0f9d9ae2760)

The tool generates a 3-panel montage for every image processed:
*Original*: The raw input image.
*Chroma Boost*: Linearly expanded color variance to highlight general hue presence.
*Segmented Boost Map*: A high-contrast, segmented visualization where pigment opacity is determined by signal strength, overlaying a texture-enhanced (CLAHE) background.

**Cool things**

Adaptive Noise Floor Detection: Automatically calculates the statistical threshold between the background substrate (noise) and actual pigment (signal) using histogram peak analysis.

3-Tier Segmentation 
Tier 3 (Faint): Visualized as semi-transparent "ghost" layers.
Tier 2 (Mid-Tones): High opacity washes.
Tier 1 (Solid): Opaque, unmodified pigment.

Texture Enhancement: Applies CLAHE (Contrast Limited Adaptive Histogram Equalization) to reveal topology.

Batch Processing: Multi-process engine that processes a folder of images (including 16-bit TIFF/PNG) in parallel across CPU cores.

**Usage**

```bash
pip install -r requirements.txt
python3 Chroma_diagnoser_v4.1 /path/to/input /path/to/output
```

Useful options (`--help` for all):

- `--threshold-mode {noise_floor,percentile,otsu,fixed}` (default `noise_floor`, described below) and `--noise-fraction` (default 0.01; smaller is stricter).
- `--default-colorspace {sRGB,"Adobe RGB","ProPhoto RGB"}`: the colour space assumed for images with no ICC profile or EXIF colour-space tag (default sRGB). Files with an embedded sRGB, Adobe RGB or ProPhoto profile are decoded in that space automatically.
- `--output-scale` (default 0.5): size of the presentation images. Analysis always runs at full resolution unless `--analysis-scale` is set.
- `--max-workers N`: lower this for very large images; each worker needs several GB for a 100-megapixel file.

- `--histograms`: also save a histogram of each feature with its thresholds, as a diagnostic for choosing a threshold.

Each image produces pictures in two feature spaces, raw C\*ab and lightness-relative chroma (LRC), plus a JSON provenance record (source, hash, settings). The batch writes a run log (`summary/run_log.csv`) of what was processed and how. Every picture is labelled "Visualisation only - not a measurement".

**How It Works** 
The processing pipeline:

1. Pre-processing & Normalization
Images are decoded in their source colour space (sRGB, Adobe RGB or ProPhoto RGB, with Bradford adaptation for ProPhoto) and converted to CIELAB (D65). Chroma (colour intensity) is each pixel's distance from neutral in the a\*b\* plane.

2. Statistical Thresholding
The tool generates a histogram of the image's chroma values. It identifies the "Noise Mountain" (the statistical peak representing the paper/substrate) and finds the exact point where the noise variance drops off (the 1% cutoff). This value becomes the Noise Floor.

3. The "Segmented Boost" Map

Instead of applying a global filter, the tool treats data differently based on its intensity relative to the Noise Floor:

Substrate Removal: Pixels below the floor are rendered as dark grayscale to reduce visual distraction. Connected regions smaller than `--min-component-area` pixels are discarded.

Signal Isolation: Pixels above the floor are segmented into three statistical tiers (Median, 85th Percentile, Max).

Visualization: Faint signals are rendered with high transparency (preserving the context of the background), while strong signals are rendered opaque. This allows researchers to distinguish between faint residue and solid paint.
