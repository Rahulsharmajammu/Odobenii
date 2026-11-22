"""Generate and cache the scenario captures (JPEG) and their ground truth."""
from __future__ import annotations

import sys
import time
from dataclasses import replace
from pathlib import Path

import cv2
import numpy as np

from sim_print import BASIC, EXTENSIVE, CaptureSpec, PrintSpec, capture, make_print

OUT = Path(__file__).parent / "scenes"
TONE_SHIFT = dict(tone_hi=(0.86, 1.0, 1.18), tone_lo=(1.04, 1.0, 0.97))
STAIN = dict(stain_od=(0.006, 0.014, 0.035))
MIXED = dict(light_left=(1.07, 1.0, 0.84), light_right=(0.93, 1.0, 1.12), falloff=0.35)
SHEEN = dict(veil=0.012, hot=1.5)
PHONE_TM = dict(local_tm=0.35)

SCENARIOS = {
    "S1_benign": (PrintSpec(), CaptureSpec()),
    "S2_tone_shift": (PrintSpec(**TONE_SHIFT), CaptureSpec()),
    "S3_mixed_light": (PrintSpec(), CaptureSpec(**MIXED)),
    "S4_sheen": (PrintSpec(), CaptureSpec(**SHEEN)),
    "S5_extensive": (PrintSpec(layers=list(EXTENSIVE)), CaptureSpec()),
    "S6_unpainted_unruly": (PrintSpec(layers=[], **TONE_SHIFT, **STAIN), CaptureSpec(**MIXED, **SHEEN, **PHONE_TM)),
    "S7_extensive_unruly": (PrintSpec(layers=list(EXTENSIVE), **TONE_SHIFT, **STAIN),
                            CaptureSpec(**MIXED, **SHEEN, **PHONE_TM)),
    "S8_basic_unruly": (PrintSpec(**TONE_SHIFT, **STAIN), CaptureSpec(**MIXED, **SHEEN, **PHONE_TM)),
}


def main(names):
    OUT.mkdir(exist_ok=True)
    for name in names:
        ps, cs = SCENARIOS[name]
        t = time.time()
        p = make_print(ps)
        c = capture(p["R"], cs)
        (OUT / f"{name}.jpg").write_bytes(c["jpeg"])
        np.savez_compressed(OUT / f"{name}_gt.npz", paint_od=p["paint_od"].astype(np.float16),
                            D=p["D"].astype(np.float16), sheen=c["sheen"].astype(np.float16),
                            clear=p["groups"]["clear"].astype(np.float16), faint=p["groups"]["faint"].astype(np.float16),
                            touch=p["groups"]["touch"].astype(np.float16), margin=p["margin"])
        print(f"{name}: {time.time() - t:.1f} s, {len(c['jpeg']) // 1024} kB", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:] or list(SCENARIOS))
