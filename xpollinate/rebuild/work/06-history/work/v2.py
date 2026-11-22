"""v2 departure unit and judgement rules, on top of methods.m3_proposed (the automatic consensus reference).

Adapted from the red team's leave-one-mark-out unit: without marks, the evidence is the tone bands' chosen peaks, so
the unit at each lightness is the noise spread combined with how badly the other tones predict that tone
(leave-a-window-out error).  Where the model is guessing, the unit grows and sensitivity falls.

Judgement rules:
* the paper taken as unpainted (the anchor / border ring) is reference, never judged;
* tones beyond the outermost supported tones are not judged (extrapolation): hatched;
* tones inside a gap of more than GAP L* between supported tones are 'guessed': judged, but marked;
* clipped and near-black pixels are not judged.
"""
from __future__ import annotations

import math

import numpy as np
from scipy.ndimage import median_filter

import methods as M

GAP = 15.0
WINDOW = 8.0
FLOOR = 0.8


def unit_and_support(res):
    bands = res.info["bands_obj"]
    pick = res.info["pick"]
    deg = res.info["deg"]
    anc = res.info["anchor_t"]
    K = len(bands.Lc)
    Lc = bands.Lc
    sup = np.array([p is not None for p in pick])
    err = np.full(K, np.nan)
    sp = np.full(K, np.nan)
    for k in range(K):
        if not sup[k]:
            continue
        keep = np.abs(Lc - Lc[k]) > WINDOW
        c = M._wls_curve(bands, pick, keep, anc, deg, FLOOR)
        pa_, pb_, fr, s = bands.peaks[k][pick[k]]
        sp[k] = s
        if c is None:
            continue
        pr = M._poly([Lc[k]], deg)[0]
        err[k] = math.hypot(pr @ c[0] - pa_, pr @ c[1] - pb_)
    ok = sup & np.isfinite(err)
    if ok.sum() >= 3:
        e = median_filter(err[ok], size=5, mode="nearest")
        s = median_filter(sp[ok], size=5, mode="nearest")
        Ls = Lc[ok]
    else:
        Ls, e, s = np.array([0.0, 100.0]), np.array([2.0, 2.0]), np.array([2.0, 2.0])
    Lsup = list(Lc[sup])
    if anc is not None:
        Lsup.append(anc[0])
    Lsup = np.sort(np.array(Lsup))

    def unit(L):
        ee = np.interp(L, Ls, e)
        ss = np.interp(L, Ls, s)
        return np.maximum(np.sqrt(ss * ss + ee * ee), FLOOR)

    return unit, Lsup


def judge(p, res, box):
    """Returns z2 (departure in v2 units), and masks: judged, guessed (inside a wide gap), extrapolated."""
    unit, Lsup = unit_and_support(res)
    L = p.L
    z2 = np.hypot(res.va, res.vb) / unit(L)
    lo, hi = (Lsup.min() - 2.0, Lsup.max() + 2.0) if len(Lsup) else (0, 100)
    extrap = (L < lo) | (L > hi)
    guessed = np.zeros_like(extrap)
    if len(Lsup) >= 2:
        gaps = np.diff(Lsup)
        for i in np.nonzero(gaps > GAP)[0]:
            guessed |= (L > Lsup[i] + 2.0) & (L < Lsup[i + 1] - 2.0)
    paper = res.info.get("anchor_mask")
    paper = np.zeros_like(extrap) if paper is None else paper
    use = p.usable & (box if box is not None else True)
    judged = use & ~paper & ~extrap
    return z2, judged, guessed & judged, extrap & use
