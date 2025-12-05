# handpaint_visualiser
A quick tool to visualise colour applied to monochrome photographs, initially developed for the Van Der Zee applied media project at The Metropolitan Museum of Art

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

Batch Processing: Multi-threaded engine capable of processing hundreds of high-resolution TIFFs simultaneously using all available CPU cores.

User-Friendly GUI: No command line required. Includes real-time progress tracking and sensitivity controls.

**How It Works** 
The processing pipeline follows a strict mathematical approach to ensure scientific integrity:

1. Pre-processing & Normalization
Images are converted to the CIELAB color space. The Euclidean distance from neutral gray (128, 128) is calculated for every pixel to determine Chroma (Color Intensity).

2. Statistical Thresholding
The tool generates a histogram of the image's chroma values. It identifies the "Noise Mountain" (the statistical peak representing the paper/substrate) and finds the exact point where the noise variance drops off (the 1% cutoff). This value becomes the Noise Floor.

3. The "Segmented Boost" Map

Instead of applying a global filter, the tool treats data differently based on its intensity relative to the Noise Floor:

Substrate Removal: Pixels below the floor are rendered as dark grayscale to reduce visual distraction.

Signal Isolation: Pixels above the floor are segmented into three statistical tiers (Median, 85th Percentile, Max).

Visualization: Faint signals are rendered with high transparency (preserving the context of the background), while strong signals are rendered opaque. This allows researchers to distinguish between faint residue and solid paint.
