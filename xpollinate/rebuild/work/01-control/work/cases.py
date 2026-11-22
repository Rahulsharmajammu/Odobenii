"""The synthetic test cases: prints x paint x capture, each with its ground truth on the capture's grid."""
from __future__ import annotations

import numpy as np

import synth as S


def _paints(name, w, h, which, scale=1.0):
    reg = S.scene_regions(name, w, h)
    soft = lambda m, s=3.0: S.soft(m, s)  # noqa: E731
    lib = {
        # name: (region, paint, amount)
        "flesh": ("skin", "flesh", 0.16),
        "flesh_faint": ("skin", "flesh", 0.05),
        "cheeks": ("cheeks", "rouge", 0.12),
        "lips": ("lips", "lips", 0.28),
        "hair": ("hair", "brown", 0.18),
        "suit": ("suit", "rouge", 0.10),
        "suit_blue": ("suit", "blue", 0.10),
        "flag_red": ("flag_red", "rouge", 0.30),
        "flag_blue": ("flag_blue", "blue", 0.30),
        "patch_gold": ("patch", "gold", 0.35),
        "badge_gold": ("badge", "gold", 0.35),
        "bg_blue": ("bg", "blue", 0.07),
        "bg_blue_faint": ("bg", "blue", 0.035),
        "sky_blue": ("sky", "blue", 0.06),
        "sky_blue_faint": ("sky", "blue", 0.03),
        "grass_green": ("grass", "green", 0.10),
        "face_flesh": ("face", "flesh", 0.15),
    }
    out = []
    for key in which:
        r, paint, amt = lib[key]
        p = S.Paint(paint, soft(reg[r], 6.0 if r in ("cheeks", "lips") else 3.0), amt * scale)
        p.key = key
        out.append(p)
    return out


def build(case: str):
    """Returns dict(img=uint8 HxWx3, box=print box, gt=dict, desc=str)."""
    P, C = S.PrintSpec, S.CaptureSpec
    if case == "neg_neutral":
        ps, paints, cs = P(paper=(0.88, 0.87, 0.85), tone_hi=(1, 1, 1), tone_lo=(1, 1, 1), yellowing=0.0, foxing=0), [], C()
        desc = "unpainted neutral print, phone capture"
    elif case == "neg_hard":
        ps = P(tone_hi=(0.86, 1.0, 1.22), tone_lo=(1.04, 1.0, 0.95), yellowing=0.18, foxing=10)
        paints, cs = [], C(gradient=((1.15, 1.0, 0.75), (0.92, 1.0, 1.10)), jpeg_q=75)
        desc = "unpainted split-toned print, yellowed and foxed, mixed light, JPEG q75"
    elif case == "portrait":
        ps = P()
        paints = ["flesh", "cheeks", "lips", "hair", "patch_gold", "badge_gold"]
        cs = C()
        desc = "warm print: flesh tint, cheeks, lips, hair, small gold touches; phone capture"
    elif case == "portrait_heavy":
        ps = P()
        paints = ["flesh", "cheeks", "lips", "hair", "suit", "flag_red", "flag_blue", "bg_blue", "patch_gold"]
        cs = C()
        desc = "warm print painted almost everywhere it is light: face, hair, suit, flag, background"
    elif case == "blue_over_warm":
        ps = P(tone_hi=(0.82, 1.0, 1.30), tone_lo=(0.9, 1.0, 1.15), paper=(0.86, 0.83, 0.70))
        paints = ["suit_blue", "bg_blue_faint"]
        cs = C(awb="none")
        desc = "strongly warm print, blue washes (lower its chroma); no white balance"
    elif case == "sky_mixed":
        ps = P(scene="camera")
        paints = ["sky_blue", "grass_green", "face_flesh"]
        cs = C(gradient=((1.12, 1.0, 0.80), (0.94, 1.0, 1.08)))
        desc = "faint blue sky (the lightest third), green grass, face; mixed light left to right"
    elif case == "sky_faint":
        ps = P(scene="camera")
        paints = ["sky_blue_faint"]
        cs = C()
        desc = "a faint blue wash over the whole sky (most of the light tones), nothing else"
    elif case == "glare_bg":
        ps = P()
        paints = ["flesh", "cheeks", "lips", "patch_gold"]
        cs = C(glare=0.12, glare_pos=(0.72, 0.35), speculars=5, background="wood", border=0.10)
        desc = "portrait on a wooden table, veiling glare and specular spots"
    elif case == "heavy_jpeg":
        ps = P()
        paints = ["flesh_faint", "cheeks", "lips", "badge_gold"]
        cs = C(jpeg_q=60, lateral_colour=0.003, sharpen=1.2, chroma_mottle=0.008, noise=0.012)
        desc = "faint flesh tint; heavy JPEG q60, strong lateral colour, sharpening, noise"
    elif case == "all_painted":
        ps = P()
        paints = ["flesh", "cheeks", "lips", "hair", "suit", "flag_red", "flag_blue", "bg_blue", "patch_gold",
                  "badge_gold"]
        cs = C()
        desc = "(see portrait_heavy)"
    else:
        raise ValueError(case)
    refl0, _ = S.make_print(ps, [])
    h, w = refl0.shape[:2]
    plist = _paints(ps.scene, w, h, paints) if paints else []
    if case == "all_painted":            # also the dark coat/suit shadow areas and the remaining light background
        reg = S.scene_regions(ps.scene, w, h)
        cover = np.zeros((h, w), np.float32)
        for p in plist:
            cover = np.maximum(cover, p.mask)
        rest = S.soft(cover < 0.05, 2) * 1.0
        extra = S.Paint("violet", rest, 0.05)
        extra.key = "rest_violet"
        plist.append(extra)
        desc = "every part of the print painted (a violet wash over all that was left)"
    refl, gt = S.make_print(ps, plist)
    img, box, data = S.capture(refl, cs)
    # ground truth on the capture's grid
    H, W = img.shape[:2]
    x0, y0, x1, y1 = box
    amt = {}
    for p in plist:
        a = np.zeros((H, W), np.float32)
        a[y0:y1, x0:x1] = gt["amounts"][p.name] if p.name in gt["amounts"] else 0
        # several paints share a name (e.g. rouge): keep each by its key
        m = np.zeros((H, W), np.float32)
        m[y0:y1, x0:x1] = p.mask
        amt[p.key] = (m, p.name)
    inside = np.zeros((H, W), bool)
    inside[y0:y1, x0:x1] = True
    painted = np.zeros((H, W), np.float32)
    for m, _ in amt.values():
        painted = np.maximum(painted, m)
    D = np.zeros((H, W), np.float32)
    D[y0:y1, x0:x1] = gt["density"]
    fox = np.zeros((H, W), bool)
    fox[y0:y1, x0:x1] = gt["foxing"]
    return {"img": img, "box": box, "inside": inside, "paint_masks": amt, "painted": painted, "density": D,
            "foxing": fox, "desc": desc, "print_spec": ps, "capture_spec": cs, "jpeg": data}


CASES = ["neg_neutral", "neg_hard", "portrait", "portrait_heavy", "blue_over_warm", "sky_mixed", "sky_faint",
         "glare_bg", "heavy_jpeg", "all_painted"]
