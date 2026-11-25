"""Colour: files read through their ICC profile into linear ProPhoto RGB and CIELAB, and CIELAB drawn for the screen.

Decoding follows the batch tool's rules (Chroma_diagnoser_v4.1, 4.1.5):

- an RGB matrix/TRC profile is applied from its own colorants and tone curves at full bit depth, whatever its name
  (a linear profile may be named "ProPhoto", as Woodii's are);
- a LUT-based profile with a recognised name (sRGB, Adobe RGB, ProPhoto) is decoded analytically, and any other LUT
  profile goes through LittleCMS to sRGB at 8-bit precision;
- an untagged file is read as its EXIF colour space, then filename words, then the default the user chose.

Everything is then held as linear ProPhoto RGB (D50) and CIELAB relative to ProPhoto's white, so a neutral grey in the
file is a*b* = 0.  Pictures go to the screen as sRGB, or Display P3 when the browser reports a P3 screen; colours
outside the screen's gamut keep their lightness and hue and lose chroma until they fit.
"""
from __future__ import annotations

import io
import struct
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageCms, ImageOps

Image.MAX_IMAGE_PIXELS = 200_000_000

READABLE = {".tif", ".tiff", ".png", ".jpg", ".jpeg", ".webp", ".bmp"}
DEFAULT_SPACES = ("sRGB", "Adobe RGB", "ProPhoto RGB")

# RGB -> XYZ (column vectors).  sRGB and Adobe RGB are D65; ProPhoto is D50.
M_RGB_TO_XYZ = {
    "sRGB": np.array([[0.4124564, 0.3575761, 0.1804375],
                      [0.2126729, 0.7151522, 0.0721750],
                      [0.0193339, 0.1191920, 0.9503041]]),
    "Adobe RGB": np.array([[0.5767309, 0.1855540, 0.1881852],
                           [0.2973769, 0.6273491, 0.0752741],
                           [0.0270343, 0.0706872, 0.9911085]]),
    "ProPhoto RGB": np.array([[0.7976749, 0.1351917, 0.0313534],
                              [0.2880402, 0.7118741, 0.0000857],
                              [0.0000000, 0.0000000, 0.8252100]]),
}
# Display P3 (D65), for P3 screens
M_P3_TO_XYZ = np.array([[0.4865709, 0.2656677, 0.1982173],
                        [0.2289746, 0.6917385, 0.0792869],
                        [0.0000000, 0.0451134, 1.0439444]])
BRADFORD_D50_TO_D65 = np.array([[0.95557930, -0.02303755, 0.06316926],
                                [-0.02828613, 1.00993728, 0.02100921],
                                [0.01229970, -0.02048587, 1.32994705]])
BRADFORD_D65_TO_D50 = np.linalg.inv(BRADFORD_D50_TO_D65)
M_PP = M_RGB_TO_XYZ["ProPhoto RGB"]
M_PP_INV = np.linalg.inv(M_PP)
WHITE = M_PP.sum(axis=1)                 # ProPhoto's white (D50): the CIELAB reference white here
ROWS = 512                               # rows per block, to bound memory on large files


class ReadError(Exception):
    """A file that cannot be read, with the reason in words."""


# -- ICC profiles ------------------------------------------------------------------------------------------------------

def _s15(b: bytes) -> float:
    return struct.unpack(">i", b)[0] / 65536.0


def icc_tone_curve(data: bytes):
    """Decoder (encoded 0-1 to linear 0-1) for an ICC 'curv' or 'para' tag, or None if unsupported."""
    sig = data[:4]
    if sig == b"curv":
        n = struct.unpack(">I", data[8:12])[0]
        if n == 0:
            return lambda v: np.clip(v, 0.0, 1.0)
        if n == 1:
            g = struct.unpack(">H", data[12:14])[0] / 256.0
            return lambda v: np.power(np.clip(v, 0.0, 1.0), g)
        table = np.frombuffer(data[12:12 + 2 * n], dtype=">u2").astype(np.float64) / 65535.0
        xs = np.linspace(0.0, 1.0, n)
        return lambda v: np.interp(np.clip(v, 0.0, 1.0), xs, table)
    if sig == b"para":
        ftype = struct.unpack(">H", data[8:10])[0]
        count = {0: 1, 1: 3, 2: 4, 3: 5, 4: 7}.get(ftype)
        if count is None or len(data) < 12 + 4 * count:
            return None
        g, a, b, c, d, e, f = [_s15(data[12 + 4 * i:16 + 4 * i]) for i in range(count)] + [0.0] * (7 - count)
        if ftype == 0:
            return lambda v: np.power(np.clip(v, 0.0, 1.0), g)

        def para(v):
            v = np.clip(v, 0.0, 1.0)
            if ftype in (1, 2):
                cut = -b / a if a else 0.0
                offset = c if ftype == 2 else 0.0
                return np.where(v >= cut, np.power(np.clip(a * v + b, 0.0, None), g) + offset, offset)
            return np.where(v >= d, np.power(np.clip(a * v + b, 0.0, None), g) + (e if ftype == 4 else 0.0),
                            c * v + (f if ftype == 4 else 0.0))
        return para
    return None


def icc_matrix_shaper(icc: bytes):
    """(colorants, curves) of an RGB matrix/TRC profile: a 3 x 3 matrix from linear RGB to PCS XYZ (D50) and one
    decoder per channel.  None for any other profile (LUT-based, not RGB, unreadable)."""
    try:
        if len(icc) < 132 or icc[16:20] != b"RGB " or icc[36:40] != b"acsp":
            return None
        tags = {}
        for i in range(struct.unpack(">I", icc[128:132])[0]):
            sig, off, size = struct.unpack(">4sII", icc[132 + 12 * i:144 + 12 * i])
            tags[sig] = icc[off:off + size]
        if any(k in tags for k in (b"A2B0", b"A2B1", b"A2B2")):
            return None
        cols = []
        for key in (b"rXYZ", b"gXYZ", b"bXYZ"):
            t = tags.get(key)
            if t is None or t[:4] != b"XYZ ":
                return None
            cols.append([_s15(t[8 + 4 * j:12 + 4 * j]) for j in range(3)])
        curves = [icc_tone_curve(tags[k]) if k in tags else None for k in (b"rTRC", b"gTRC", b"bTRC")]
        if any(c is None for c in curves):
            return None
        return np.array(cols, dtype=np.float64).T, curves
    except Exception:
        return None


def profile_name(icc: Optional[bytes]) -> Optional[str]:
    if not icc:
        return None
    try:
        name = ImageCms.getProfileName(ImageCms.ImageCmsProfile(io.BytesIO(icc))).strip()
        return name or "embedded ICC profile"
    except Exception:
        return "embedded ICC profile (name unavailable)"


def space_from_name(name: str) -> Optional[str]:
    """One of the analytic spaces from a profile description, or None."""
    n = name.lower()
    if "prophoto" in n or "romm" in n:
        return "ProPhoto RGB"
    if "adobe" in n and "rgb" in n:
        return "Adobe RGB"
    if "srgb" in n or "iec61966-2" in n or "iec 61966-2" in n:
        return "sRGB"
    return None


def _exif_space(img: Image.Image) -> Optional[str]:
    try:
        exif = img.getexif()
        tag = exif.get_ifd(0x8769).get(0xA001)
        tag = exif.get(0xA001) if tag is None else tag
    except Exception:
        return None
    return {1: "sRGB", 2: "Adobe RGB"}.get(tag)


# -- analytic decoding -------------------------------------------------------------------------------------------------

def decode_tone(v: np.ndarray, space: str) -> np.ndarray:
    """Encoded 0-1 to linear 0-1 for an analytic space."""
    v = np.clip(v, 0.0, 1.0)
    if space == "ProPhoto RGB":
        return np.where(v < 16.0 / 512.0, v / 16.0, np.power(v, 1.8))
    if space == "Adobe RGB":
        return np.power(v, 563.0 / 256.0)
    return np.where(v < 0.04045, v / 12.92, np.power((v + 0.055) / 1.055, 2.4))


def encode_srgb(lin: np.ndarray) -> np.ndarray:
    lin = np.clip(lin, 0.0, 1.0)
    return np.where(lin <= 0.0031308, 12.92 * lin, 1.055 * np.power(lin, 1.0 / 2.4) - 0.055)


def _to_prophoto_matrix(space: str) -> np.ndarray:
    """Linear RGB of an analytic space to linear ProPhoto (row vectors: rgb @ M.T)."""
    M = M_RGB_TO_XYZ[space]
    if space != "ProPhoto RGB":
        M = BRADFORD_D65_TO_D50 @ M
    return M_PP_INV @ M


# -- reading files -----------------------------------------------------------------------------------------------------

def _is_16bit_colour(img: Image.Image, path: Path) -> bool:
    if img.mode not in ("RGB", "RGBA"):
        return False
    try:
        if path.suffix.lower() in (".tif", ".tiff"):
            bps = img.tag_v2.get(258)
            bps = bps[0] if isinstance(bps, (tuple, list)) else bps
            return bps == 16
        if path.suffix.lower() == ".png":
            with open(path, "rb") as f:
                head = f.read(26)
            return len(head) >= 25 and head[24] == 16
    except Exception:
        return False
    return False


def _read_16bit(path: Path) -> Optional[np.ndarray]:
    """16-bit RGB TIFF or PNG through OpenCV (Pillow reduces them to 8 bits); EXIF orientation applied."""
    try:
        arr = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_ANYDEPTH | cv2.IMREAD_COLOR)
    except Exception:
        return None
    if arr is None or arr.dtype != np.uint16 or arr.ndim != 3:
        return None
    return cv2.cvtColor(arr, cv2.COLOR_BGR2RGB).astype(np.float32) / 65535.0


def _pil_to_float(img: Image.Image) -> Tuple[np.ndarray, int]:
    mode = img.mode
    if mode.startswith("I;16"):
        arr, bits = np.asarray(img).astype(np.float32) / 65535.0, 16
    elif mode == "I":
        raw = np.asarray(img).astype(np.float64)
        top = 65535.0 if raw.max() <= 65535 else float(raw.max())
        arr, bits = (raw / top).astype(np.float32), 16
    elif mode == "F":
        raw = np.asarray(img).astype(np.float32)
        arr, bits = (raw / raw.max() if raw.max() > 1.0 else raw), 32
    else:
        if mode not in ("RGB", "L"):
            img = img.convert("RGB")
        arr, bits = np.asarray(img).astype(np.float32) / 255.0, 8
    if arr.ndim == 2:
        arr = np.repeat(arr[:, :, None], 3, axis=2)
    elif arr.shape[2] == 4:
        arr = arr[:, :, :3]
    return np.clip(arr, 0.0, 1.0), bits


def _float_tiff(path: Path) -> bool:
    if path.suffix.lower() not in (".tif", ".tiff"):
        return False
    try:
        probe = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_UNCHANGED)
        return probe is not None and probe.dtype.kind == "f"
    except Exception:
        return False


def read_image(path, default_space: str = "sRGB"):
    """A file as linear ProPhoto RGB (float32, H x W x 3), a mask of pixels the file clipped, and what was done.

    Returns (linear_prophoto, clipped, info).  Raises ReadError with the reason in words."""
    path = Path(path)
    if default_space not in DEFAULT_SPACES:
        raise ReadError(f"the default colour space must be one of {', '.join(DEFAULT_SPACES)}")
    try:
        img = Image.open(path)
    except Exception as exc:
        if _float_tiff(path):
            raise ReadError("a 32-bit floating-point TIFF, which this tool does not read: save it as 16-bit "
                            "(Woodii: --data uint16)") from exc
        raise ReadError(f"not an image this tool can read ({exc})") from exc
    with img:
        icc = img.info.get("icc_profile")
        name = profile_name(icc)
        size = (img.width, img.height)
        mode = img.mode
        space, why = None, ""
        if name:
            space = space_from_name(name)
            why = f"profile '{name}'"
        if space is None and not icc:
            space = _exif_space(img)
            why = "EXIF colour space" if space else ""
            if space is None:
                stem = path.stem.lower()
                if "prophoto" in stem:
                    space, why = "ProPhoto RGB", "the word 'prophoto' in its name"
                elif "adobergb" in stem or "adobe_rgb" in stem:
                    space, why = "Adobe RGB", "the word 'adobergb' in its name"
                else:
                    space, why = default_space, "no colour-space information: the default you chose"
        rgb = _read_16bit(path) if _is_16bit_colour(img, path) else None
        if rgb is not None:
            bits, img_t = 16, None
        else:
            img_t = ImageOps.exif_transpose(img)
            rgb, bits = _pil_to_float(img_t)
        clipped = (rgb >= 0.999).any(axis=-1)
        grey_file = mode in ("L", "I", "I;16", "I;16L", "I;16B", "F", "LA")

        shaper = icc_matrix_shaper(icc) if icc else None
        lin = np.empty(rgb.shape, np.float32)
        if shaper is not None:
            colorants, curves = shaper
            to_pp = (M_PP_INV @ colorants).T.astype(np.float32)
            for r0 in range(0, rgb.shape[0], ROWS):
                blk = rgb[r0:r0 + ROWS]
                dec = np.stack([curves[i](blk[..., i]) for i in range(3)], axis=-1).astype(np.float32)
                lin[r0:r0 + ROWS] = dec @ to_pp
            how = f"through its profile '{name}' (matrix and tone curves) at {bits}-bit precision"
        elif icc and space is None:
            try:                                      # a LUT profile with no recognised name: LittleCMS, 8 bits
                src = img_t if (bits == 8 and img_t is not None and img_t.mode in ("RGB", "L", "CMYK")) else \
                    Image.fromarray(np.clip(rgb * 255.0 + 0.5, 0, 255).astype(np.uint8))
                out = ImageCms.profileToProfile(src, ImageCms.ImageCmsProfile(io.BytesIO(icc)),
                                                ImageCms.createProfile("sRGB"), outputMode="RGB")
                rgb8, _ = _pil_to_float(out)
            except Exception as exc:
                raise ReadError(f"its profile '{name}' could not be applied ({exc})") from exc
            space = "sRGB"
            M = _to_prophoto_matrix(space).T.astype(np.float32)
            for r0 in range(0, rgb8.shape[0], ROWS):
                lin[r0:r0 + ROWS] = decode_tone(rgb8[r0:r0 + ROWS], space).astype(np.float32) @ M
            how = (f"through its profile '{name}' (LUT-based) with LittleCMS at 8-bit precision"
                   + (f", reduced from {bits}-bit" if bits != 8 else ""))
        else:
            M = _to_prophoto_matrix(space).T.astype(np.float32)
            for r0 in range(0, rgb.shape[0], ROWS):
                lin[r0:r0 + ROWS] = decode_tone(rgb[r0:r0 + ROWS], space).astype(np.float32) @ M
            how = f"as {space} ({why}) at {bits}-bit precision"
    np.clip(lin, 0.0, None, out=lin)
    info = {"name": path.name, "size": list(size), "bits": bits, "profile": name,
            "colour": f"Read {how}.", "grey_file": grey_file}
    return lin, clipped, info


# -- CIELAB ------------------------------------------------------------------------------------------------------------

def _f(t):
    return np.where(t > (6 / 29) ** 3, np.cbrt(t), t / (3 * (6 / 29) ** 2) + 4 / 29)


def _finv(t):
    return np.where(t > 6 / 29, t ** 3, 3 * (6 / 29) ** 2 * (t - 4 / 29))


def lab_from_linear(lin: np.ndarray) -> np.ndarray:
    """Linear ProPhoto RGB (..., 3) to CIELAB relative to ProPhoto's white, float32."""
    out = np.empty(lin.shape, np.float32)
    M = (M_PP / WHITE[:, None]).T.astype(np.float32)     # to X/Xn, Y/Yn, Z/Zn
    flat_in, flat_out = lin.reshape(-1, 3), out.reshape(-1, 3)
    step = ROWS * 4096
    for i in range(0, flat_in.shape[0], step):
        f = _f(np.maximum(flat_in[i:i + step] @ M, 0.0))
        flat_out[i:i + step, 0] = 116.0 * f[:, 1] - 16.0
        flat_out[i:i + step, 1] = 500.0 * (f[:, 0] - f[:, 1])
        flat_out[i:i + step, 2] = 200.0 * (f[:, 1] - f[:, 2])
    return out


def linear_from_lab(lab: np.ndarray) -> np.ndarray:
    """CIELAB (relative to ProPhoto's white) to linear ProPhoto RGB, float32 (not clipped)."""
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    fy = (L + 16.0) / 116.0
    xyz = np.stack([_finv(fy + a / 500.0), _finv(fy), _finv(fy - b / 200.0)], axis=-1) * WHITE
    return (xyz @ M_PP_INV.T).astype(np.float32)


# -- to the screen -----------------------------------------------------------------------------------------------------

def _xyz_to_screen(space: str) -> np.ndarray:
    M = M_P3_TO_XYZ if space == "p3" else M_RGB_TO_XYZ["sRGB"]
    return np.linalg.inv(M) @ BRADFORD_D50_TO_D65


def _lab_to_screen_linear(lab: np.ndarray, space: str) -> np.ndarray:
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    fy = (L + 16.0) / 116.0
    xyz = np.stack([_finv(fy + a / 500.0), _finv(fy), _finv(fy - b / 200.0)], axis=-1) * WHITE
    return xyz @ _xyz_to_screen(space).T


def lab_to_screen(lab: np.ndarray, space: str = "srgb") -> np.ndarray:
    """CIELAB (H x W x 3) to 8-bit RGB for the screen ('srgb' or 'p3').  Out-of-gamut colours keep their lightness
    and hue and lose chroma until they fit (12 halvings), so a boosted colour never turns into another hue."""
    lab = lab.astype(np.float32, copy=True)
    lab[..., 0] = np.clip(lab[..., 0], 0.0, 100.0)
    rgb = _lab_to_screen_linear(lab, space)
    bad = ((rgb < -1e-4) | (rgb > 1.0 + 1e-4)).any(axis=-1)
    if bad.any():
        sub = lab[bad]
        lo, hi = np.zeros(len(sub), np.float32), np.ones(len(sub), np.float32)
        for _ in range(12):
            mid = (lo + hi) / 2
            t = sub.copy()
            t[:, 1:] *= mid[:, None]
            r = _lab_to_screen_linear(t, space)
            ok = ((r >= -1e-4) & (r <= 1.0 + 1e-4)).all(axis=-1)
            lo = np.where(ok, mid, lo)
            hi = np.where(ok, hi, mid)
        sub[:, 1:] *= lo[:, None]
        rgb[bad] = _lab_to_screen_linear(sub, space)
    return np.round(encode_srgb(rgb) * 255.0).astype(np.uint8)


def screen_icc(space: str) -> bytes:
    """An ICC profile for pictures sent to the screen: sRGB, or Display P3 (sRGB's tone curve)."""
    if space != "p3":
        return ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    return _P3_PROFILE


def _matrix_trc_profile(rgb_to_xyz_d50: np.ndarray, description: str) -> bytes:
    """A minimal ICC v2 display profile with sRGB's tone curve (para type 3)."""
    def s15(v):
        return struct.pack(">i", int(round(v * 65536)))

    def xyz(v):
        return b"XYZ " + b"\0" * 4 + b"".join(s15(x) for x in v)

    def pad(b):
        return b + b"\0" * ((-len(b)) % 4)
    d50 = (0.9642, 1.0, 0.8249)
    text = description.encode("ascii") + b"\0"
    desc = b"desc" + b"\0" * 4 + struct.pack(">I", len(text)) + text + struct.pack(">II", 0, 0) + \
        struct.pack(">HB", 0, 0) + b"\0" * 67
    trc = b"para" + b"\0" * 4 + struct.pack(">HH", 3, 0) + b"".join(
        s15(p) for p in (2.4, 1 / 1.055, 0.055 / 1.055, 1 / 12.92, 0.04045))
    tags = [(b"desc", desc), (b"cprt", b"text" + b"\0" * 4 + b"No copyright\0"), (b"wtpt", xyz(d50)),
            (b"rXYZ", xyz(rgb_to_xyz_d50[:, 0])), (b"gXYZ", xyz(rgb_to_xyz_d50[:, 1])),
            (b"bXYZ", xyz(rgb_to_xyz_d50[:, 2])), (b"rTRC", trc), (b"gTRC", trc), (b"bTRC", trc)]
    offset = 128 + 4 + 12 * len(tags)
    table, body = b"", b""
    for sig, data in tags:
        table += struct.pack(">4sII", sig, offset + len(body), len(data))
        body += pad(data)
    size = offset + len(body)
    head = struct.pack(">I", size) + b"odbn" + bytes([2, 0x10, 0, 0]) + b"mntr" + b"RGB " + b"XYZ "
    head += struct.pack(">6H", 2026, 1, 1, 0, 0, 0) + b"acsp" + b"\0" * 24 + b"\0" * 4 + b"".join(s15(v) for v in d50)
    head += b"odbn" + b"\0" * (128 - len(head) - 4)
    return head[:128] + struct.pack(">I", len(tags)) + table + body


_P3_PROFILE = _matrix_trc_profile(BRADFORD_D65_TO_D50 @ M_P3_TO_XYZ, "Display P3 (Odobenii)")
