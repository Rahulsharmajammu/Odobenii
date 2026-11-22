"""Minimal ICC v2 RGB matrix/TRC profiles for the tests (D50 PCS): eciRGB v2-like (an L* curve table),
Display P3-like (a para type 3 curve) and linear ones (curv count 0, as Woodii writes)."""
import struct
import numpy as np

D50 = np.array([0.9642, 1.0, 0.8249])

def s15(v):
    return struct.pack(">i", int(round(v * 65536)))

def pad4(b):
    return b + b"\0" * ((-len(b)) % 4)

def xyz_tag(xyz):
    return b"XYZ " + b"\0" * 4 + b"".join(s15(v) for v in xyz)

def desc_tag(text):
    a = text.encode("ascii") + b"\0"
    return b"desc" + b"\0" * 4 + struct.pack(">I", len(a)) + a + struct.pack(">II", 0, 0) + struct.pack(">HB", 0, 0) + b"\0" * 67

def text_tag(text):
    return b"text" + b"\0" * 4 + text.encode("ascii") + b"\0"

def curv_table(values):
    v = np.clip(np.round(np.asarray(values) * 65535), 0, 65535).astype(">u2")
    return b"curv" + b"\0" * 4 + struct.pack(">I", len(v)) + v.tobytes()

def para_tag(ftype, params):
    return b"para" + b"\0" * 4 + struct.pack(">HH", ftype, 0) + b"".join(s15(p) for p in params)

def colorants(prims_xy, white=D50):
    cols = []
    for x, y in prims_xy:
        cols.append([x / y, 1.0, (1 - x - y) / y])
    P = np.array(cols).T                      # columns are primaries' XYZ (Y=1)
    S = np.linalg.solve(P, white)
    return P * S                              # columns scaled so R=G=B=1 gives the white

def build(name, prims_xy, trc_tag):
    M = colorants(prims_xy)
    tags = [(b"desc", desc_tag(name)), (b"cprt", text_tag("test")), (b"wtpt", xyz_tag(D50)),
            (b"rXYZ", xyz_tag(M[:, 0])), (b"gXYZ", xyz_tag(M[:, 1])), (b"bXYZ", xyz_tag(M[:, 2])),
            (b"rTRC", trc_tag), (b"gTRC", trc_tag), (b"bTRC", trc_tag)]
    n = len(tags)
    offset = 128 + 4 + 12 * n
    table, body = b"", b""
    for sig, data in tags:
        table += struct.pack(">4sII", sig, offset + len(body), len(data))
        body += pad4(data)
    size = offset + len(body)
    hdr = struct.pack(">I", size) + b"lcms" + struct.pack(">I", 0x02100000) + b"mntr" + b"RGB " + b"XYZ "
    hdr += struct.pack(">6H", 2026, 11, 22, 0, 0, 0) + b"acsp" + b"APPL" + b"\0" * 4 + b"\0" * 4 + b"\0" * 4 + b"\0" * 8
    hdr += struct.pack(">I", 0) + b"".join(s15(v) for v in D50) + b"test" + b"\0" * 16
    hdr += b"\0" * (128 - len(hdr))
    return hdr + struct.pack(">I", n) + table + body, M

# eciRGB v2-like: primaries and an L* tone curve
ECI = [(0.67, 0.33), (0.21, 0.71), (0.14, 0.08)]
def lstar_decode(v):
    L = np.asarray(v) * 100.0
    return np.where(L > 8.0, ((L + 16.0) / 116.0) ** 3, L / 903.2963)
def lstar_encode(y):
    y = np.asarray(y)
    return np.where(y > 0.008856, 116.0 * np.cbrt(y) - 16.0, 903.2963 * y) / 100.0
# Display P3-like primaries with an sRGB-style parametric curve (para type 3)
P3 = [(0.680, 0.320), (0.265, 0.690), (0.150, 0.060)]
SRGB_PARA = [2.4, 1 / 1.055, 0.055 / 1.055, 1 / 12.92, 0.04045]
def srgb_decode(v):
    v = np.asarray(v); return np.where(v >= 0.04045, ((v + 0.055) / 1.055) ** 2.4, v / 12.92)
def srgb_encode(y):
    y = np.asarray(y); return np.where(y > 0.0031308, 1.055 * y ** (1 / 2.4) - 0.055, 12.92 * y)

def profiles():
    eci_icc, eci_M = build("Test eciRGB v2 lookalike", ECI, curv_table(lstar_decode(np.linspace(0, 1, 4096))))
    p3_icc, p3_M = build("Test wide P3 para", P3, para_tag(3, SRGB_PARA))
    return {"eci": (eci_icc, eci_M, lstar_encode), "p3": (p3_icc, p3_M, srgb_encode)}


def linear_tag():
    """An identity tone curve: curv with no entries."""
    return b"curv" + b"\0" * 4 + struct.pack(">I", 0)


def gamma_tag(g):
    """A pure gamma tone curve: curv with one u8.8 entry."""
    return b"curv" + b"\0" * 4 + struct.pack(">IH", 1, int(round(g * 256)))
