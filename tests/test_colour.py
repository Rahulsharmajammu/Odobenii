"""The web app reads files as the batch tool (4.1.5) does, and draws colour for the screen without changing hue."""
import importlib.util
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest
import tifffile
from PIL import Image, ImageCms

import iccmake as mk
from odobenii import colour

ROOT = Path(__file__).resolve().parents[1]
LAB_D50 = np.array([[50, 0, 0], [80, 2, 8], [30, 1, 4], [60, 20, 10], [55, -15, -25], [70, -20, 30],
                    [45, 40, 20], [85, 5, 25], [40, 10, -35], [25, 0, 0], [92, 0, 2], [65, 3, 3]], float)


def lab_to_xyz(lab, white):
    L, a, b = lab[:, 0], lab[:, 1], lab[:, 2]
    fy = (L + 16) / 116
    inv = lambda t: np.where(t ** 3 > 216 / 24389, t ** 3, (116 * t - 16) / (24389 / 27))
    return np.stack([inv(fy + a / 500), inv(fy), inv(fy - b / 200)], -1) * white


XYZ = lab_to_xyz(LAB_D50, colour.WHITE)


@pytest.fixture(scope="module")
def batch_tool():
    """The batch tool loaded as a module (its file has no .py extension)."""
    copy = Path(tempfile.mkdtemp()) / "cd_for_tests.py"
    shutil.copy(ROOT / "Chroma_diagnoser_v4.1", copy)
    spec = importlib.util.spec_from_file_location("cd_for_tests", copy)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["cd_for_tests"] = mod
    spec.loader.exec_module(mod)
    return mod


def write_patches(path, enc, icc=None, bits=16):
    tile = np.repeat(np.repeat(enc[None], 8, 0), 8, 1)
    arr = np.round(np.clip(tile, 0, 1) * (65535 if bits == 16 else 255)).astype(np.uint16 if bits == 16 else np.uint8)
    tifffile.imwrite(path, arr, photometric="rgb", iccprofile=icc)


def patches_lab(lin):
    return colour.lab_from_linear(lin)[4, 4::8][: len(LAB_D50)]


def cases(tmp):
    """(name, path) of files whose true colour is LAB_D50, through several kinds of profile."""
    out = []
    for key, (icc, M, encode) in mk.profiles().items():
        lin = np.linalg.solve(M, XYZ.T).T
        p = tmp / f"{key}.tif"
        write_patches(p, encode(lin), icc)
        out.append((key, p))
    M_pp = colour.M_PP
    lin_pp = np.linalg.solve(M_pp, XYZ.T).T
    romm = [(0.7347, 0.2653), (0.1596, 0.8404), (0.0366, 0.0001)]
    icc_lin, _ = mk.build("linear ProPhoto RGB (Woodii)", romm, mk.linear_tag())
    p = tmp / "woodii_linear.tif"
    write_patches(p, lin_pp, icc_lin)
    out.append(("woodii linear", p))
    icc_g, _ = mk.build("ProPhoto RGB", romm, mk.gamma_tag(1.8))
    p = tmp / "prophoto_gamma.tif"
    write_patches(p, lin_pp ** (256 / 461), icc_g)
    out.append(("prophoto gamma 1.8", p))
    srgb_icc = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    xyz65 = XYZ @ colour.BRADFORD_D50_TO_D65.T
    lin_s = np.linalg.solve(colour.M_RGB_TO_XYZ["sRGB"], xyz65.T).T
    p = tmp / "srgb_tagged.tif"
    write_patches(p, colour.encode_srgb(lin_s), srgb_icc)
    out.append(("sRGB tagged", p))
    p = tmp / "untagged.tif"
    write_patches(p, colour.encode_srgb(lin_s))
    out.append(("untagged (default sRGB)", p))
    return out


def test_known_colours(tmp_path):
    """Every kind of profile gives the patches' true CIELAB (16-bit)."""
    for name, p in cases(tmp_path):
        lin, clipped, info = colour.read_image(p)
        de = np.linalg.norm(patches_lab(lin) - LAB_D50, axis=1)
        assert de.max() < 0.1, (name, de.round(3), info["colour"])
        assert not clipped.any()


def test_same_as_batch_tool(tmp_path, batch_tool):
    """The web app and 4.1.5 agree on every file (4.1.5 works in CIELAB D65, so both are compared there)."""
    proc = batch_tool.ImageProcessor(batch_tool.VisualizerConfig(input_dir=tmp_path, output_dir=tmp_path / "o"))
    for name, p in cases(tmp_path):
        rgb, meta = proc._open_working_rgb(p)
        theirs = proc._rgb_to_lab(rgb, meta["working_colorspace"])[4, 4::8][: len(LAB_D50)]
        lin, _, _ = colour.read_image(p)
        xyz = lin[4, 4::8][: len(LAB_D50)].astype(np.float64) @ colour.M_PP.T * 100.0
        ours = batch_tool._xyz_to_lab(batch_tool._bradford_adapt_d50_to_d65(xyz.astype(np.float32)))
        de = np.linalg.norm(ours - theirs, axis=1)
        assert de.max() < 0.05, (name, de.round(3))


def test_lut_profile_through_littlecms(tmp_path, monkeypatch):
    """A LUT profile with an unrecognised name goes through LittleCMS at 8 bits, and says so."""
    icc, M, encode = mk.profiles()["eci"]
    p = tmp_path / "lut.tif"
    write_patches(p, encode(np.linalg.solve(M, XYZ.T).T), icc)
    monkeypatch.setattr(colour, "icc_matrix_shaper", lambda b: None)
    lin, _, info = colour.read_image(p)
    assert "LittleCMS" in info["colour"] and "8-bit" in info["colour"]
    assert np.linalg.norm(patches_lab(lin) - LAB_D50, axis=1).max() < 1.0


def test_float_tiff_refused(tmp_path):
    p = tmp_path / "f.tif"
    tifffile.imwrite(p, np.full((8, 8, 3), 0.25, np.float32), photometric="rgb")
    with pytest.raises(colour.ReadError, match="16-bit"):
        colour.read_image(p)


def test_clipping_and_8bit(tmp_path):
    a = np.full((10, 10, 3), 128, np.uint8)
    a[0, 0] = 255
    p = tmp_path / "c.png"
    Image.fromarray(a).save(p)
    lin, clipped, info = colour.read_image(p)
    assert clipped[0, 0] and clipped.sum() == 1 and info["bits"] == 8
    assert "default" in info["colour"]


def test_lab_round_trip():
    rng = np.random.default_rng(0)
    lab = np.stack([rng.uniform(5, 95, 1000), rng.uniform(-30, 30, 1000), rng.uniform(-30, 30, 1000)], -1)
    lin = colour.linear_from_lab(lab.astype(np.float32))
    real = (lin >= 0).all(-1)                       # colours a file can hold (dark and very chromatic ones cannot)
    assert real.mean() > 0.8
    back = colour.lab_from_linear(lin[real])
    assert np.abs(back - lab[real]).max() < 0.02


@pytest.mark.parametrize("space", ["srgb", "p3"])
def test_screen_keeps_hue_and_lightness(space):
    """A strongly boosted colour, outside the screen's gamut, keeps its lightness and hue."""
    lab = np.array([[[60.0, 120.0, 40.0], [40.0, -90.0, -80.0], [80.0, 10.0, 110.0], [50.0, 0.0, 0.0]]], np.float32)
    rgb8 = colour.lab_to_screen(lab, space).astype(np.float64) / 255.0
    lin = np.where(rgb8 <= 0.04045, rgb8 / 12.92, ((rgb8 + 0.055) / 1.055) ** 2.4)
    M = colour.M_P3_TO_XYZ if space == "p3" else colour.M_RGB_TO_XYZ["sRGB"]
    xyz50 = lin @ (colour.BRADFORD_D65_TO_D50 @ M).T
    back = colour.lab_from_linear((xyz50 @ colour.M_PP_INV.T).astype(np.float32))[0]
    assert np.abs(back[:, 0] - lab[0, :, 0]).max() < 1.0
    hue = lambda v: np.degrees(np.arctan2(v[:, 2], v[:, 1]))
    dh = (hue(back[:3]) - hue(lab[0, :3]) + 180) % 360 - 180
    assert np.abs(dh).max() < 4.0
    assert np.abs(back[3, 1:]).max() < 0.5
