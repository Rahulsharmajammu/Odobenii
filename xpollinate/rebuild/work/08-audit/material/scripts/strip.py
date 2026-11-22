import re, sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
n0 = len(s)
def cut(start, end, repl=""):
    """remove from the first occurrence of start up to (not including) the next occurrence of end"""
    global s
    i = s.index(start); j = s.index(end, i + len(start))
    s = s[:i] + repl + s[j:]
def sub(old, new, count=1):
    global s
    assert s.count(old) >= 1, old[:60]
    assert count == 0 or s.count(old) == count, (s.count(old), old[:60])
    s = s.replace(old, new)

# --- header
sub('"""\nChroma Diagnostic Tool v4.1\n=================================\n',
    '"""\nChroma Diagnostic Tool v4.1\n=================================\n\n'
    'A VISUALISER, NOT A MEASURING TOOL.  The images it writes show where colour\n'
    'stands out from a monochrome substrate; they are qualitative.  It reports no\n'
    'areas, counts or statistics, and its colour handling is only as careful as a\n'
    'legible picture needs.\n\n'
    'Changes in 4.1.2\n----------------\n'
    '- Everything that invited a quantitative reading is removed: area\n'
    '  percentages (montage footer, console, JSON, CSV), component counts,\n'
    '  feature statistics, the threshold-sensitivity (Jaccard) analysis, and the\n'
    '  numerical outputs (float / 16-bit feature TIFFs and the categorical mask).\n'
    '- Every picture is labelled "Visualisation only - not a measurement".\n'
    '- The batch CSV is now a plain run log (what was processed, and how).\n')
sub("bit-depth preservation, vectorized spatial filtering, and FADGI-compliant\ncolor-space management.",
    "bit-depth preservation, vectorized spatial filtering, and colour-space-aware\ndecoding.")
sub('VERSION = "4.1.1"', 'VERSION = "4.1.2"')
sub("# Colorimetric constants  (FADGI-compliant wide-gamut support)", "# Colour-space constants (sRGB, Adobe RGB and ProPhoto RGB sources)")
sub('FOOTER_HEIGHT = 60\nMONTAGE_FOOTER_HEIGHT = 60\n',
    'FOOTER_HEIGHT = 60\nMONTAGE_FOOTER_HEIGHT = 60\n\n# Printed on every picture this tool writes.\nVIS_LABEL = "Visualisation only - not a measurement"\n')
sub('"GIF uses an indexed palette of up to 256 colors; colorimetric "\n            "fidelity may be lower than the original RGB source."',
    '"GIF uses an indexed palette of up to 256 colors; faint colour "\n            "may be lost or banded."')

# --- config
sub("    lrc_sensitivity_scale: float = 0.5\n", "")
sub("    run_sensitivity_analysis: bool = True\n    sensitivity_factors: Tuple[float, ...] = (\n        0.90, 0.95, 1.00, 1.05, 1.10\n    )\n", "")
sub("    save_numerical_tiff: bool = True\n", "")
sub("    save_16bit_tiff_sidecar: bool = True\n", "")
sub('        if any(f <= 0 for f in self.sensitivity_factors):\n            raise ValueError("All sensitivity factors must be > 0")\n', "")
sub('        if self.lrc_sensitivity_scale <= 0:\n            raise ValueError("lrc_sensitivity_scale must be > 0")\n', "")

# --- sensitivity machinery
cut("    def _threshold_for_sensitivity(", "    def _apply_spatial_filter(")

# --- threshold metrics
cut("        total_pixels = feature.size\n", "        return threshold, alpha, binary_filtered, metrics\n",
    '        metrics = {\n'
    '            "chroma_space": space,\n'
    '            "threshold_method": self.cfg.threshold_mode,\n'
    '            "threshold": float(threshold),\n'
    '            "mid_threshold": float(mid),\n'
    '            "high_threshold": float(high),\n'
    '            "min_component_area_pixels": self.cfg.min_component_area_pixels,\n'
    '        }\n\n')
sub('    def _threshold_and_map(self, feature: np.ndarray, space: str) -> Tuple[float, np.ndarray, np.ndarray, dict]:\n',
    '    def _threshold_and_map(self, feature: np.ndarray, space: str) -> Tuple[float, np.ndarray, np.ndarray, dict]:\n'
    '        """Threshold, display alpha and mask for one feature.  The returned dict\n'
    '        holds the settings used (for the provenance record), no statistics."""\n')

# --- categorical mask + component statistics
cut("    @staticmethod\n    def _categorical_mask(", "    def _save_histogram(")
sub("(the boost is illustrative, not metrological)", "(the boost is illustrative only)")
sub("for the visual overlay since it is not used for metrology).", "for a picture).")

# --- per-space processing
cut('            metrics["mean_chroma"] = float(np.mean(chroma))\n', "            space_dir = img_dir / space\n")
cut("            if self.cfg.save_numerical_tiff:\n                # FIX: save as 16-bit", "            # Resize alpha to display resolution")
cut("            map_data = (\n", "            chroma_saved = self._save_footer(\n")
sub('f"Segmented ({space_label}) | {map_data} {fidelity_tag}"', 'f"Segmented ({space_label}) | {VIS_LABEL} {fidelity_tag}"')
sub('f"Chroma Boost {self.cfg.chroma_boost_factor:g}x {fidelity_tag}"', 'f"Chroma Boost {self.cfg.chroma_boost_factor:g}x | {VIS_LABEL} {fidelity_tag}"')
sub('f"{threshold_label} | {map_data} {fidelity_tag}"', 'f"{threshold_label} | {VIS_LABEL} {fidelity_tag}"')
sub('                "results": metrics,\n', '                "what": VIS_LABEL + ": the pictures are qualitative",\n                "thresholds": metrics,\n')
cut('                    "mask_tiff": ', '                    "chroma_boost_image"')
sub('                f"Chroma={metrics[\'chromatic_area_percent\']:.2f}% | "\n                f"Components={metrics[\'component_statistics\'][\'component_count\']} | "\n', "")
sub('                        "Custom RGB->XYZ->LAB pipeline with Bradford adaptation; "\n                        "D65 CIELAB reference; color-space aware."',
    '                        "RGB->XYZ->LAB with Bradford adaptation, D65 reference; "\n                        "for display, not colorimetry."')

# --- numerical outputs in process_image
cut("            numerical_dir = img_dir / \"numerical\"\n", "            # --- Presentation images (once) ---\n")

# --- manifest, summary, cli
sub('            "lrc_sensitivity_scale": config.lrc_sensitivity_scale,\n', "")
sub('            "sensitivity_factors": list(config.sensitivity_factors),\n', "")
sub('            "save_16bit_tiff_sidecar": config.save_16bit_tiff_sidecar,\n', "")
sub('        "software_version": VERSION,\n        "run_timestamp_utc"', '        "software_version": VERSION,\n        "what": VIS_LABEL + ": the pictures are qualitative",\n        "run_timestamp_utc"')
cut('        "chromatic_area_percent",\n        "faint_area_percent"', "    ]\n\n    with open(path, \"w\", newline=\"\"")
sub('    path = summary_dir / "batch_summary.csv"', '    path = summary_dir / "run_log.csv"   # what was processed and how; no statistics')
cut('                **record["results"],\n', "            writer.writerow({key: row.get(key, \"\") for key in fields})",
    '                **record["thresholds"],\n            }\n')
sub('    p.add_argument("--lrc-sensitivity-scale", type=float, default=0.5)\n', "")
sub('    p.add_argument("--no-sensitivity", action="store_true")\n', "")
sub('    p.add_argument("--no-numerical-tiff", action="store_true")\n', "")
sub('    p.add_argument("--no-16bit-sidecar", action="store_true")\n', "")
sub('        lrc_sensitivity_scale=args.lrc_sensitivity_scale,\n', "")
sub('        run_sensitivity_analysis=not args.no_sensitivity,\n', "")
sub('        save_numerical_tiff=not args.no_numerical_tiff,\n', "")
sub('        save_16bit_tiff_sidecar=not args.no_16bit_sidecar,\n', "")
sub('description="Chroma Diagnostic Tool v4.1 chroma analysis"', 'description="Chroma Diagnostic Tool v4.1: a visualiser of colour on monochrome photographs (qualitative; not a measuring tool)"')
sub('    print(f"Chroma Diagnostic Tool v{VERSION}")\n', '    print(f"Chroma Diagnostic Tool v{VERSION}")\n    print(f"{VIS_LABEL}.")\n')
open(p, "w", encoding="utf-8").write(s)
print("bytes", n0, "->", len(s))
