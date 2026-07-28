import os
import sys
import platform
import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import concurrent.futures
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Optional

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

# 1. Security: Prevent Decompression Bomb attacks
Image.MAX_IMAGE_PIXELS = 100_000_000 

# --- Configuration Object ---
@dataclass
class VisualizerConfig:
    input_dir: Path
    output_dir: Path
    scale_factor: float = 0.5        
    chroma_boost_factor: float = 3.0 
    use_adaptive_threshold: bool = True
    manual_threshold: float = 5.0
    threshold_bias: float = 0.0     
    font_size: int = 24              
    
    def __post_init__(self):
        self.input_dir = Path(self.input_dir).resolve()
        self.output_dir = Path(self.output_dir).resolve()
        # Fix: Ensure output directory exists to prevent FileNotFoundError
        self.output_dir.mkdir(parents=True, exist_ok=True)

# --- Core ---

class ImageProcessor:
    def __init__(self, config: VisualizerConfig):
        self.cfg = config
        self.font = self._load_system_font()
        # Fix: Instantiate CLAHE once per worker, not per image
        self.clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))

    def _load_system_font(self) -> ImageFont.ImageFont:
        system = platform.system()
        font_names = []
        if system == "Windows": font_names = ["arial.ttf", "calibri.ttf"]
        elif system == "Darwin": font_names = ["Arial.ttf", "Helvetica.ttc"]
        else: font_names = ["DejaVuSans.ttf", "LiberationSans-Regular.ttf"]
        
        for name in font_names:
            try: return ImageFont.truetype(name, self.cfg.font_size)
            except IOError: continue
        return ImageFont.load_default()

    def load_and_resize(self, image_path: Path) -> Optional[np.ndarray]:
        try:
            with Image.open(image_path) as img:
                img = ImageOps.exif_transpose(img)
                if img.mode != 'RGB': img = img.convert('RGB')
                if self.cfg.scale_factor != 1.0:
                    w, h = img.size
                    img = img.resize((int(w * self.cfg.scale_factor), int(h * self.cfg.scale_factor)), Image.Resampling.LANCZOS)
                return np.array(img)
        except Exception as e:
            # Fix: Don't fail silently
            raise RuntimeError(f"File load error: {e}")

    def calculate_boost_assisted_threshold(self, img_rgb: np.ndarray) -> float:
        lab_img = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
        a = lab_img[:, :, 1] - 128
        b = lab_img[:, :, 2] - 128
        
        # Fix: Clarify dual meaning of "boost"
        detection_gain = 3.0
        chroma_boosted = np.sqrt((a * detection_gain)**2 + (b * detection_gain)**2).flatten()

        # Fix: Dynamic histogram bins to prevent truncation of high chroma values
        max_val = max(100.0, float(chroma_boosted.max()))
        counts, bin_edges = np.histogram(chroma_boosted, bins=np.linspace(0, max_val, 200))
        
        peak_idx = np.argmax(counts)
        peak_val = bin_edges[peak_idx]
        
        # Fix: Guard against fragile peak assumption (e.g., solid blue backgrounds)
        if peak_idx > len(counts) * 0.9:
            base_threshold = np.percentile(chroma_boosted, 75) / detection_gain
        else:
            noise_cutoff = counts[peak_idx] * 0.01
            cutoff_val = peak_val + 10.0
            for i in range(peak_idx, len(counts)):
                if counts[i] < noise_cutoff:
                    cutoff_val = bin_edges[i]
                    break
            base_threshold = cutoff_val / detection_gain
        
        final_threshold = base_threshold + self.cfg.threshold_bias
        return max(final_threshold, 1.0)

    def process_image(self, img_path: Path) -> Tuple[bool, str]:
        try:
            base_name = img_path.stem
            
            # Fix: Prevent filename collisions across subdirectories
            try:
                rel_path = img_path.relative_to(self.cfg.input_dir)
                out_prefix = str(rel_path.parent / base_name).replace(os.sep, "_")
                if out_prefix.startswith("_"): out_prefix = base_name # Fallback
            except ValueError:
                out_prefix = base_name
                
            original_np = self.load_and_resize(img_path)
            
            if self.cfg.use_adaptive_threshold:
                threshold = self.calculate_boost_assisted_threshold(original_np)
                threshold_label = f"Smart:{threshold:.1f}"
            else:
                threshold = self.cfg.manual_threshold
                threshold_label = f"Manual:{threshold:.1f}"

            original_pil = Image.fromarray(original_np)
            chroma_pil = self._boost_chroma(original_np, self.cfg.chroma_boost_factor)
            masked_map_pil, map_data_str = self._create_masked_boost_map(original_np, threshold)

            # Fix: Typo "Segemented" -> "Segmented"
            chroma_saved = self._add_footer(chroma_pil, base_name, f"Chroma Boost ({self.cfg.chroma_boost_factor}x)")
            masked_saved = self._add_footer(masked_map_pil, base_name, f"Segmented Boost | {map_data_str}")

            chroma_saved.save(self.cfg.output_dir / f"{out_prefix}_chroma.jpg", quality=95)
            masked_saved.save(self.cfg.output_dir / f"{out_prefix}_segmented.jpg", quality=95)

            montage = self._create_montage(
                original_pil, chroma_pil, masked_map_pil, 
                base_name, f"{threshold_label} | {map_data_str}"
            )
            # Standardized quality
            montage.save(self.cfg.output_dir / f"{out_prefix}_montage.jpg", quality=95)
            
            return True, f"Processed {out_prefix} (Thresh: {threshold:.1f})"
        except Exception as e:
            return False, f"Failed {img_path.name}: {e}"

    def _boost_chroma(self, img_rgb: np.ndarray, factor: float) -> Image.Image:
        lab_img = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
        L, a, b = cv2.split(lab_img)
        a = (a - 128) * factor + 128
        b = (b - 128) * factor + 128
        merged_lab = np.clip(cv2.merge([L, a, b]), 0, 255).astype(np.uint8)
        return Image.fromarray(cv2.cvtColor(merged_lab, cv2.COLOR_LAB2RGB))

    def _create_masked_boost_map(self, img_rgb: np.ndarray, threshold: float) -> Tuple[Image.Image, str]:
        gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
        background = cv2.cvtColor((gray * 0.15).astype(np.uint8), cv2.COLOR_GRAY2RGB)

        lab = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
        l, a, b = cv2.split(lab)
        l_enhanced = self.clahe.apply(l.astype(np.uint8)).astype(np.float32)

        a_boost = ((a - 128) * self.cfg.chroma_boost_factor + 128)
        b_boost = ((b - 128) * self.cfg.chroma_boost_factor + 128)
        merged = cv2.merge([l_enhanced, a_boost, b_boost])
        merged = np.clip(merged, 0, 255).astype(np.uint8)
        foreground = cv2.cvtColor(merged, cv2.COLOR_LAB2RGB).astype(np.float32)

        chroma = np.sqrt((a-128)**2 + (b-128)**2)
        valid_chroma = chroma[chroma > threshold]

        if len(valid_chroma) == 0:
            t3_end, t2_end = threshold + 5.0, threshold + 15.0
        else:
            t3_end = np.percentile(valid_chroma, 50)
            t2_end = np.percentile(valid_chroma, 85)
            t3_end = max(t3_end, threshold + 2.0)
            t2_end = max(t2_end, t3_end + 2.0)

        # Fix: Dynamic ramp for High mask instead of fixed 5.0 decay window
        high_ramp = max(5.0, (t2_end - threshold) * 0.25)
        
        mask_faint = np.clip((chroma - threshold) / (t3_end - threshold), 0, 1)
        mask_mid = np.clip((chroma - t3_end) / (t2_end - t3_end), 0, 1)
        mask_high = np.clip((chroma - t2_end) / high_ramp, 0, 1)

        # Fix: Independent Alpha Compositing rather than sequential overwrite
        # Calculate maximum alpha per pixel across the tiers
        alpha_f = mask_faint * 0.4
        alpha_m = mask_mid * 0.8
        alpha_h = mask_high * 1.0
        max_alpha = np.maximum.reduce([alpha_f, alpha_m, alpha_h])
        
        alpha_3d = cv2.merge([max_alpha]*3)
        final = background.astype(np.float32) * (1.0 - alpha_3d) + foreground * alpha_3d

        # Fix: Include High tier in reporting
        data_str = f"Thr:{threshold:.1f} Mid:{t3_end:.1f} High:{t2_end:.1f}"
        return Image.fromarray(final.astype(np.uint8)), data_str

    def _add_footer(self, img: Image.Image, left_text: str, right_text: str = "") -> Image.Image:
        w, h = img.size
        footer_height = 50
        new_img = Image.new('RGB', (w, h + footer_height), 'white')
        new_img.paste(img, (0, 0))
        draw = ImageDraw.Draw(new_img)
        draw.text((10, h + 12), left_text, font=self.font, fill='black')
        if right_text:
            bbox = draw.textbbox((0, 0), right_text, font=self.font)
            draw.text((w - (bbox[2] - bbox[0]) - 10, h + 12), right_text, font=self.font, fill='black')
        return new_img

    def _create_montage(self, orig: Image.Image, chroma: Image.Image, paint: Image.Image, 
                       fname: str, footer_data: str) -> Image.Image:
        w, h = orig.size
        montage = Image.new('RGB', (w * 3, h + 80), 'white')
        montage.paste(orig, (0, 0))
        montage.paste(chroma, (w, 0))
        montage.paste(paint, (w * 2, 0))
        draw = ImageDraw.Draw(montage)
        
        labels = ["Original", "Chroma Boosted", "Segmented Boost Map"]
        for i, text in enumerate(labels):
            bbox = draw.textbbox((0, 0), text, font=self.font)
            draw.text(((i * w) + (w - (bbox[2] - bbox[0])) / 2, h + 5), text, font=self.font, fill='black')
            
        draw.line([(0, h + 40), (w * 3, h + 40)], fill='black', width=1)
        draw.text((20, h + 48), fname, font=self.font, fill='black')
        
        bbox = draw.textbbox((0, 0), footer_data, font=self.font)
        draw.text(((w * 3) - (bbox[2] - bbox[0]) - 20, h + 48), footer_data, font=self.font, fill='black')
        return montage

# --- ProcessPool Initialization ---

_proc = None
def _init_worker(config: VisualizerConfig):
    """ Fix: Instantiates ImageProcessor and fonts ONCE per worker process. """
    global _proc
    # Fix: Prevent OpenCV threading collisions with ProcessPoolExecutor
    cv2.setNumThreads(1)
    _proc = ImageProcessor(config)

def _worker_task(path: Path) -> Tuple[bool, str]:
    return _proc.process_image(path)

# --- Threaded Worker for GUI ---

class ProcessingThread(threading.Thread):
    def __init__(self, config: VisualizerConfig, logger_queue: queue.Queue):
        super().__init__(daemon=True) # Fix: Daemon thread allows clean exit
        self.cfg = config
        self.logger_queue = logger_queue
        self.is_running = True

    def run(self):
        try:
            valid_exts = {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp'}
            self.logger_queue.put(("LOG", "Scanning for images..."))
            
            # Fix: Guard against path traversal symlink attacks
            image_paths = [p for p in self.cfg.input_dir.rglob("*") 
                           if p.suffix.lower() in valid_exts and p.is_file() 
                           and p.resolve().is_relative_to(self.cfg.input_dir)]
            
            if not image_paths:
                self.logger_queue.put(("LOG", "Warning: No valid images found!"))
                return # Jumps to 'finally' block to reset UI

            total = len(image_paths)
            self.logger_queue.put(("LOG", f"Found {total} images. Starting pool..."))
            
            # Fix: Pass initializer to reuse processor state
            with concurrent.futures.ProcessPoolExecutor(
                initializer=_init_worker, initargs=(self.cfg,)
            ) as executor:
                
                futures = {executor.submit(_worker_task, p): p for p in image_paths}
                
                for i, future in enumerate(concurrent.futures.as_completed(futures)):
                    # Fix: Cancellation check
                    if not self.is_running:
                        executor.shutdown(wait=False, cancel_futures=True)
                        self.logger_queue.put(("LOG", "Job cancelled by user."))
                        break

                    success, result_msg = future.result()
                    # Fix: Progress always updates, even on failure
                    self.logger_queue.put(("PROGRESS", i + 1, total, result_msg))

        except Exception as e:
            # Fix: Catch global execution crashes (e.g., bad permissions on root)
            self.logger_queue.put(("LOG", f"Fatal Error: {e}"))
        finally:
            # Fix: Guarantee UI is unlocked
            self.logger_queue.put(("DONE", 0, 0, "Batch Processing Finished."))

# --- GUI Application ---

class VisualizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Forensic Image Segmenter")
        self.root.geometry("750x700")
        
        # Fix: Handle window close properly
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.log_queue = queue.Queue()
        self.processing_thread = None
        
        style = ttk.Style()
        style.theme_use('clam')
        
        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 1. Path Selection
        path_frame = ttk.LabelFrame(main_frame, text="Directories", padding="10")
        path_frame.pack(fill=tk.X, pady=5)
        path_frame.columnconfigure(1, weight=1)
        
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        
        self._build_path_row(path_frame, "Input Folder:", self.input_path, 0)
        self._build_path_row(path_frame, "Output Folder:", self.output_path, 1)
        
        # 2. Settings
        settings_frame = ttk.LabelFrame(main_frame, text="Processing Parameters", padding="10")
        settings_frame.pack(fill=tk.X, pady=5)
        # Fix: Column weights so sliders actually expand
        settings_frame.columnconfigure(1, weight=1) 
        
        ttk.Label(settings_frame, text="Output Resolution:").grid(row=0, column=0, sticky=tk.W)
        self.res_var = tk.StringVar(value="Standard (50%)")
        res_combo = ttk.Combobox(settings_frame, textvariable=self.res_var, state="readonly")
        res_combo['values'] = ["Draft (25%)", "Standard (50%)", "High (75%)", "Full (100%)"]
        res_combo.grid(row=0, column=1, sticky=tk.W, padx=10, pady=5)
        
        # Fix: Expose Manual vs Adaptive Threshold
        ttk.Label(settings_frame, text="Threshold Mode:").grid(row=1, column=0, sticky=tk.W)
        self.thresh_mode_var = tk.BooleanVar(value=True)
        thresh_check = ttk.Checkbutton(settings_frame, text="Use Adaptive (Smart) Threshold", variable=self.thresh_mode_var)
        thresh_check.grid(row=1, column=1, sticky=tk.W, padx=10, pady=5)

        ttk.Label(settings_frame, text="Manual Threshold (if off):").grid(row=2, column=0, sticky=tk.W)
        self.manual_th_var = tk.DoubleVar(value=5.0)
        manual_scale = ttk.Scale(settings_frame, from_=1.0, to=20.0, variable=self.manual_th_var, command=lambda v: self.manual_th_label.config(text=f"{float(v):.1f}"))
        manual_scale.grid(row=2, column=1, sticky=tk.EW, padx=10)
        self.manual_th_label = ttk.Label(settings_frame, text="5.0")
        self.manual_th_label.grid(row=2, column=2, sticky=tk.W)

        ttk.Label(settings_frame, text="Chroma Boost (Visual):").grid(row=3, column=0, sticky=tk.W)
        self.boost_var = tk.DoubleVar(value=3.0)
        boost_scale = ttk.Scale(settings_frame, from_=1.0, to=10.0, variable=self.boost_var, command=lambda v: self.boost_label.config(text=f"{float(v):.1f}x"))
        boost_scale.grid(row=3, column=1, sticky=tk.EW, padx=10)
        self.boost_label = ttk.Label(settings_frame, text="3.0x")
        self.boost_label.grid(row=3, column=2, sticky=tk.W)
        
        ttk.Label(settings_frame, text="Threshold Bias (Adaptive):").grid(row=4, column=0, sticky=tk.W)
        self.bias_var = tk.DoubleVar(value=0.0)
        bias_scale = ttk.Scale(settings_frame, from_=-5.0, to=5.0, variable=self.bias_var, command=lambda v: self.bias_label.config(text=f"{float(v):.1f}"))
        bias_scale.grid(row=4, column=1, sticky=tk.EW, padx=10)
        self.bias_label = ttk.Label(settings_frame, text="0.0")
        self.bias_label.grid(row=4, column=2, sticky=tk.W)
        
        # 3. Actions
        action_frame = ttk.Frame(main_frame, padding="10")
        action_frame.pack(fill=tk.X)
        
        self.run_btn = ttk.Button(action_frame, text="Start Processing", command=self.start_processing)
        self.run_btn.pack(side=tk.RIGHT, padx=5)
        
        self.cancel_btn = ttk.Button(action_frame, text="Cancel", command=self.cancel_processing, state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.RIGHT)
        
        # 4. Progress
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=10)
        
        self.status_label = ttk.Label(main_frame, text="Ready.")
        self.status_label.pack(anchor=tk.W)
        
        # 5. Log
        self.log_area = scrolledtext.ScrolledText(main_frame, height=10, state='disabled', font=("Consolas", 9))
        self.log_area.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.is_closing = False
        self.root.after(100, self.poll_log_queue)

    def _build_path_row(self, parent, label, var, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W)
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        ttk.Button(parent, text="Browse", command=lambda: self.browse_dir(var)).grid(row=row, column=2)

    def browse_dir(self, var):
        d = filedialog.askdirectory()
        if d: var.set(d)

    def log(self, msg):
        self.log_area.configure(state='normal')
        self.log_area.insert(tk.END, msg + "\n")
        self.log_area.see(tk.END)
        self.log_area.configure(state='disabled')

    def on_closing(self):
        self.is_closing = True
        if self.processing_thread and self.processing_thread.is_alive():
            self.cancel_processing()
        self.root.destroy()

    def cancel_processing(self):
        if self.processing_thread:
            self.processing_thread.is_running = False
            self.cancel_btn.config(state=tk.DISABLED)
            self.log("Cancelling... waiting for current items to finish.")

    def poll_log_queue(self):
        if self.is_closing:
            return

        while not self.log_queue.empty():
            record = self.log_queue.get()
            
            if record[0] == "PROGRESS":
                _, curr, total, msg = record
                self.progress_var.set((curr / total) * 100)
                self.status_label.config(text=f"Processing {curr}/{total}...")
                self.log(msg)
            elif record[0] == "DONE":
                self.run_btn.config(state='normal')
                self.cancel_btn.config(state='disabled')
                self.status_label.config(text="Finished.")
                self.log(record[3])
                self.progress_var.set(100)
            elif record[0] == "LOG":
                self.log(record[1])
                
        self.root.after(100, self.poll_log_queue)

    def start_processing(self):
        inp = self.input_path.get()
        out = self.output_path.get()
        
        if not inp or not out or not os.path.isdir(inp):
            messagebox.showerror("Error", "Please select a valid input directory.")
            return

        res_map = {"Draft (25%)": 0.25, "Standard (50%)": 0.50, "High (75%)": 0.75, "Full (100%)": 1.0}
        
        config = VisualizerConfig(
            input_dir=inp,
            output_dir=out,
            scale_factor=res_map.get(self.res_var.get(), 0.5),
            chroma_boost_factor=self.boost_var.get(),
            use_adaptive_threshold=self.thresh_mode_var.get(),
            manual_threshold=self.manual_th_var.get(),
            threshold_bias=self.bias_var.get()
        )
        
        self.run_btn.config(state='disabled')
        self.cancel_btn.config(state='normal')
        self.progress_var.set(0)
        self.log("\n--- Starting New Batch ---")
        
        self.processing_thread = ProcessingThread(config, self.log_queue)
        self.processing_thread.start()

if __name__ == "__main__":
    try:
        from multiprocessing import freeze_support
        freeze_support()
    except:
        pass

    root = tk.Tk()
    app = VisualizerApp(root)
    root.mainloop()
