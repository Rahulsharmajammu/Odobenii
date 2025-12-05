import os
import sys
import logging
import platform
import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import concurrent.futures
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Optional, Callable

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

# --- 1. Logging Infrastructure---

class QueueHandler(logging.Handler):
    """Sends log records to a queue so the GUI can read them safely."""
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(record)

# --- 2. Configuration Object ---
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
        self.input_dir = Path(self.input_dir)
        self.output_dir = Path(self.output_dir)

# --- 3. The Engine ---

class ImageProcessor:
    def __init__(self, config: VisualizerConfig):
        self.cfg = config
        self.font = self._load_system_font()

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
            return None

    def calculate_boost_assisted_threshold(self, img_rgb: np.ndarray) -> float:
        lab_img = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
        a = lab_img[:, :, 1] - 128
        b = lab_img[:, :, 2] - 128
        
        # Virtual Boost (3x) for detection
        boost = 3.0
        chroma_boosted = np.sqrt((a*boost)**2 + (b*boost)**2).flatten()

        counts, bin_edges = np.histogram(chroma_boosted, bins=np.linspace(0, 100, 200))
        peak_idx = np.argmax(counts)
        peak_val = bin_edges[peak_idx]
        
        noise_cutoff = counts[peak_idx] * 0.01
        cutoff_val = peak_val + 10.0
        for i in range(peak_idx, len(counts)):
            if counts[i] < noise_cutoff:
                cutoff_val = bin_edges[i]
                break
        
        base_threshold = cutoff_val / boost
        
        # Apply User Bias (Sensitivity Slider)
        final_threshold = base_threshold + self.cfg.threshold_bias
        
        return max(final_threshold, 1.0) # Safety floor

    def process_image(self, img_path: Path) -> str:
        base_name = img_path.stem
        original_np = self.load_and_resize(img_path)
        if original_np is None: 
            return f"Error loading {base_name}"

        # 1. Analyze
        if self.cfg.use_adaptive_threshold:
            threshold = self.calculate_boost_assisted_threshold(original_np)
            threshold_label = f"Smart:{threshold:.1f}"
        else:
            threshold = self.cfg.manual_threshold
            threshold_label = f"Manual:{threshold:.1f}"

        # 2. Base Visuals
        original_pil = Image.fromarray(original_np)
        chroma_pil = self._boost_chroma(original_np, self.cfg.chroma_boost_factor)
        
        # 3. Generate Segmented Map
        masked_map_pil, map_data_str = self._create_masked_boost_map(original_np, threshold)

        # 4. Save
        # Footers
        chroma_saved = self._add_footer(chroma_pil, base_name, f"Chroma Boost ({self.cfg.chroma_boost_factor}x)")
        masked_saved = self._add_footer(masked_map_pil, base_name, f"Segemented Boost | {map_data_str}")

        chroma_saved.save(self.cfg.output_dir / f"{base_name}_chroma.jpg", quality=95)
        masked_saved.save(self.cfg.output_dir / f"{base_name}_segmented.jpg", quality=95)

        # Montage
        montage = self._create_montage(
            original_pil, chroma_pil, masked_map_pil, 
            base_name, f"{threshold_label} | {map_data_str}"
        )
        montage.save(self.cfg.output_dir / f"{base_name}_montage.jpg", quality=90)
        
        return f"Processed {base_name} (Thresh: {threshold:.1f})"

    # --- Generators ---

    def _boost_chroma(self, img_rgb: np.ndarray, factor: float) -> Image.Image:
        lab_img = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
        L, a, b = cv2.split(lab_img)
        a = (a - 128) * factor + 128
        b = (b - 128) * factor + 128
        merged_lab = np.clip(cv2.merge([L, a, b]), 0, 255).astype(np.uint8)
        return Image.fromarray(cv2.cvtColor(merged_lab, cv2.COLOR_LAB2RGB))

    def _create_masked_boost_map(self, img_rgb: np.ndarray, threshold: float) -> Tuple[Image.Image, str]:
        # Dark Background (15%)
        gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
        background = cv2.cvtColor((gray * 0.15).astype(np.uint8), cv2.COLOR_GRAY2RGB)

        # Foreground (User Approved Boost)
        lab = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        l_enhanced = clahe.apply(l.astype(np.uint8)).astype(np.float32)

        a_boost = ((a - 128) * self.cfg.chroma_boost_factor + 128)
        b_boost = ((b - 128) * self.cfg.chroma_boost_factor + 128)
        merged = cv2.merge([l_enhanced, a_boost, b_boost])
        merged = np.clip(merged, 0, 255).astype(np.uint8)
        foreground = cv2.cvtColor(merged, cv2.COLOR_LAB2RGB).astype(np.float32)

        # Tiers
        chroma = np.sqrt((a-128)**2 + (b-128)**2)
        valid_chroma = chroma[chroma > threshold]

        if len(valid_chroma) == 0:
            t3_end, t2_end = threshold + 5.0, threshold + 15.0
        else:
            t3_end = np.percentile(valid_chroma, 50)
            t2_end = np.percentile(valid_chroma, 85)
            t3_end = max(t3_end, threshold + 2.0)
            t2_end = max(t2_end, t3_end + 2.0)

        # Masks
        mask_faint = np.clip((chroma - threshold) / (t3_end - threshold), 0, 1)
        mask_mid = np.clip((chroma - t3_end) / (t2_end - t3_end), 0, 1)
        mask_high = np.clip((chroma - t2_end) / 5.0, 0, 1)

        # Composite
        final = background.astype(np.float32)
        alpha_f = cv2.merge([mask_faint]*3) * 0.4
        final = final * (1.0 - alpha_f) + foreground * alpha_f
        alpha_m = cv2.merge([mask_mid]*3) * 0.8
        final = final * (1.0 - alpha_m) + foreground * alpha_m
        alpha_h = cv2.merge([mask_high]*3) * 1.0
        final = final * (1.0 - alpha_h) + foreground * alpha_h

        data_str = f"Flr:{threshold:.1f} Mid:{t3_end:.1f}"
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
            text_w = bbox[2] - bbox[0]
            draw.text((w - text_w - 10, h + 12), right_text, font=self.font, fill='black')
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
            text_w = bbox[2] - bbox[0]
            draw.text(((i * w) + (w - text_w) / 2, h + 5), text, font=self.font, fill='black')
            
        draw.line([(0, h + 40), (w * 3, h + 40)], fill='black', width=1)
        draw.text((20, h + 48), fname, font=self.font, fill='black')
        
        bbox = draw.textbbox((0, 0), footer_data, font=self.font)
        text_w = bbox[2] - bbox[0]
        draw.text(((w * 3) - text_w - 20, h + 48), footer_data, font=self.font, fill='black')
        return montage

# --- 4. Threaded Worker for GUI ---

def _worker_task(args):
    """Wrapper to allow pickling in multiprocessing"""
    path, config = args
    processor = ImageProcessor(config)
    return processor.process_image(path)

class ProcessingThread(threading.Thread):
    def __init__(self, config: VisualizerConfig, logger_queue):
        super().__init__()
        self.cfg = config
        self.logger_queue = logger_queue
        self.is_running = True

    def run(self):
        valid_exts = {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp'}
        
        # 1. Scan Files
        self.logger_queue.put(logging.makeLogRecord({'levelno': logging.INFO, 'msg': "Scanning for images..."}))
        image_paths = [p for p in self.cfg.input_dir.rglob("*") if p.suffix.lower() in valid_exts]
        
        if not image_paths:
            self.logger_queue.put(logging.makeLogRecord({'levelno': logging.WARNING, 'msg': "No images found!"}))
            return

        total = len(image_paths)
        self.logger_queue.put(logging.makeLogRecord({'levelno': logging.INFO, 'msg': f"Found {total} images. Starting..."}))
        
        # 2. Prepare Tasks
        tasks = [(p, self.cfg) for p in image_paths]
        
        # 3. Parallel Execute
        # Note: We use the Main Thread's executor to keep the GUI responsive
        with concurrent.futures.ProcessPoolExecutor() as executor:
            futures = [executor.submit(_worker_task, task) for task in tasks]
            
            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                try:
                    result_msg = future.result()
                    # Send progress update tuple: (Current, Total, Message)
                    self.logger_queue.put(("PROGRESS", i + 1, total, result_msg))
                except Exception as e:
                    self.logger_queue.put(logging.makeLogRecord({'levelno': logging.ERROR, 'msg': f"Error: {e}"}))
        
        self.logger_queue.put(("DONE", total, total, "Processing Complete."))

# --- 5. GUI Application ---

class VisualizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Forensic Image Segmenter")
        self.root.geometry("700x650")
        
        # Logging Queue
        self.log_queue = queue.Queue()
        
        # Style
        style = ttk.Style()
        style.theme_use('clam')
        
        # --- UI Construction ---
        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 1. Path Selection
        path_frame = ttk.LabelFrame(main_frame, text="Directories", padding="10")
        path_frame.pack(fill=tk.X, pady=5)
        
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        
        self._build_path_row(path_frame, "Input Folder:", self.input_path, 0)
        self._build_path_row(path_frame, "Output Folder:", self.output_path, 1)
        
        # 2. Settings
        settings_frame = ttk.LabelFrame(main_frame, text="Processing Parameters", padding="10")
        settings_frame.pack(fill=tk.X, pady=5)
        
        # Resolution
        ttk.Label(settings_frame, text="Output Resolution:").grid(row=0, column=0, sticky=tk.W)
        self.res_var = tk.StringVar(value="Standard (50%)")
        res_combo = ttk.Combobox(settings_frame, textvariable=self.res_var, state="readonly")
        res_combo['values'] = ["Draft (25%)", "Standard (50%)", "High (75%)", "Full (100%)"]
        res_combo.grid(row=0, column=1, sticky=tk.W, padx=10, pady=5)
        
        # Boost Slider
        ttk.Label(settings_frame, text="Chroma Boost:").grid(row=1, column=0, sticky=tk.W)
        self.boost_var = tk.DoubleVar(value=3.0)
        boost_scale = ttk.Scale(settings_frame, from_=1.0, to=10.0, variable=self.boost_var, command=lambda v: self.boost_label.config(text=f"{float(v):.1f}x"))
        boost_scale.grid(row=1, column=1, sticky=tk.EW, padx=10)
        self.boost_label = ttk.Label(settings_frame, text="3.0x")
        self.boost_label.grid(row=1, column=2, sticky=tk.W)
        
        # Sensitivity Slider
        ttk.Label(settings_frame, text="Threshold Bias:").grid(row=2, column=0, sticky=tk.W)
        self.bias_var = tk.DoubleVar(value=0.0)
        bias_scale = ttk.Scale(settings_frame, from_=-5.0, to=5.0, variable=self.bias_var, command=lambda v: self.bias_label.config(text=f"{float(v):.1f}"))
        bias_scale.grid(row=2, column=1, sticky=tk.EW, padx=10)
        self.bias_label = ttk.Label(settings_frame, text="0.0")
        self.bias_label.grid(row=2, column=2, sticky=tk.W)
        
        ttk.Label(settings_frame, text="(Neg = More Sensitive, Pos = Cleaner)").grid(row=3, column=1, sticky=tk.W, padx=10)
        
        # 3. Actions
        action_frame = ttk.Frame(main_frame, padding="10")
        action_frame.pack(fill=tk.X)
        
        self.run_btn = ttk.Button(action_frame, text="Start Processing", command=self.start_processing)
        self.run_btn.pack(side=tk.RIGHT)
        
        # 4. Progress
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=10)
        
        self.status_label = ttk.Label(main_frame, text="Ready.")
        self.status_label.pack(anchor=tk.W)
        
        # 5. Log
        self.log_area = scrolledtext.ScrolledText(main_frame, height=10, state='disabled', font=("Consolas", 9))
        self.log_area.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Start Polling
        self.root.after(100, self.poll_log_queue)

    def _build_path_row(self, parent, label, var, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W)
        ttk.Entry(parent, textvariable=var, width=50).grid(row=row, column=1, padx=5, pady=5)
        ttk.Button(parent, text="Browse", command=lambda: self.browse_dir(var)).grid(row=row, column=2)

    def browse_dir(self, var):
        d = filedialog.askdirectory()
        if d: var.set(d)

    def log(self, msg):
        self.log_area.configure(state='normal')
        self.log_area.insert(tk.END, msg + "\n")
        self.log_area.see(tk.END)
        self.log_area.configure(state='disabled')

    def poll_log_queue(self):
        while not self.log_queue.empty():
            record = self.log_queue.get()
            
            if isinstance(record, tuple) and record[0] == "PROGRESS":
                # ("PROGRESS", current, total, message)
                _, curr, total, msg = record
                pct = (curr / total) * 100
                self.progress_var.set(pct)
                self.status_label.config(text=f"Processing {curr}/{total}...")
                self.log(msg)
            elif isinstance(record, tuple) and record[0] == "DONE":
                self.run_btn.config(state='normal')
                self.status_label.config(text="Complete!")
                self.log("--- Batch Complete ---")
            elif hasattr(record, 'msg'):
                self.log(record.msg)
                
        self.root.after(100, self.poll_log_queue)

    def start_processing(self):
        inp = self.input_path.get()
        out = self.output_path.get()
        
        if not inp or not out:
            self.log("Error: Please select input and output folders.")
            return

        # Map Resolution String to Float
        res_map = {
            "Draft (25%)": 0.25,
            "Standard (50%)": 0.50,
            "High (75%)": 0.75,
            "Full (100%)": 1.0
        }
        
        config = VisualizerConfig(
            input_dir=inp,
            output_dir=out,
            scale_factor=res_map[self.res_var.get()],
            chroma_boost_factor=self.boost_var.get(),
            threshold_bias=self.bias_var.get(),
            use_adaptive_threshold=True
        )
        
        self.run_btn.config(state='disabled')
        self.progress_var.set(0)
        self.log("Starting Engine...")
        
        thread = ProcessingThread(config, self.log_queue)
        thread.start()

if __name__ == "__main__":
    # Required for PyInstaller/Multiprocessing to work correctly
    try:
        from multiprocessing import freeze_support
        freeze_support()
    except:
        pass

    root = tk.Tk()
    app = VisualizerApp(root)

    root.mainloop()
