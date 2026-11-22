"""The web app's server: Woodii's request checks, and the whole flow on synthetic 16-bit ProPhoto TIFFs."""
import io
import json
import time

import numpy as np
import pytest
import tifffile
from PIL import Image

import iccmake as mk
import synth
from handpaint.app.server import TOKEN_HEADER, create_app

ROMM = [(0.7347, 0.2653), (0.1596, 0.8404), (0.0366, 0.0001)]


def write_print(path, washes=(), h=360, w=480, seed=0):
    lin, _, _, _ = synth.make(washes, seed=seed, h=h, w=w)
    icc, _ = mk.build("ProPhoto RGB", ROMM, mk.gamma_tag(1.8))
    enc = np.clip(lin, 0, 1) ** (256 / 461)
    tifffile.imwrite(path, np.round(enc * 65535).astype(np.uint16), photometric="rgb", iccprofile=icc)


@pytest.fixture()
def env(tmp_path):
    photos = tmp_path / "photos"
    photos.mkdir()
    write_print(photos / "a_unpainted.tif")
    write_print(photos / "b_face.tif", (("face", 3.0, 2.0),), seed=1)
    (photos / "notes.txt").write_text("not an image")
    app = create_app(tmp_path / "session")
    app.testing = True
    c = app.test_client()
    tok = app.config["HANDPAINT_TOKEN"]
    H = {TOKEN_HEADER: tok}

    def call(method, url, body=None, **kw):
        kw.setdefault("headers", H)
        if body is not None:
            kw["json"] = body
        return getattr(c, method)(url, **kw)
    return {"c": c, "tok": tok, "H": H, "call": call, "photos": photos, "tmp": tmp_path, "app": app}


def test_requests_are_checked(env):
    c, H = env["c"], env["H"]
    assert c.get("/api/state").status_code == 403                                     # no token
    assert c.get("/api/state", headers={TOKEN_HEADER: "wrong"}).status_code == 403
    assert c.get("/api/state", headers=H).status_code == 200
    assert c.get("/api/state", headers=H, base_url="http://evil.example").status_code == 403   # DNS rebinding
    assert c.post("/api/folder", headers={**H, "Origin": "http://evil.example"}, json={"path": "/"}).status_code == 403
    assert c.get("/api/state", headers={**H, "Sec-Fetch-Site": "cross-site"}).status_code == 403
    assert c.post("/api/folder", headers=H, data="path=/", content_type="text/plain").status_code == 415
    assert c.get("/api/instance").status_code == 200                                   # the launcher's question
    r = c.get("/")
    assert r.status_code == 200 and env["tok"].encode() in r.data and r.headers["X-Frame-Options"] == "DENY"
    assert c.get("/static/../server.py").status_code == 404
    assert c.get("/api/state", headers=H).headers["Cross-Origin-Resource-Policy"] == "same-origin"


def test_flow(env):
    call, photos = env["call"], env["photos"]
    r = call("post", "/api/folder", {"path": str(photos)})
    st = r.get_json()["state"]
    assert [f["name"] for f in st["files"]] == ["a_unpainted.tif", "b_face.tif"]
    assert call("post", "/api/open", {"path": str(env["tmp"] / "elsewhere.tif")}).status_code == 400
    r = call("post", "/api/open", {"path": str(photos / "b_face.tif")})
    assert r.status_code == 200, r.get_json()
    im = r.get_json()["state"]["image"]
    assert im["size"] == [480, 360] and "profile 'ProPhoto RGB'" in im["colour"]
    for view in ("original", "boost", "stretch", "expected", "departs"):
        q = f"view={view}&x=0&y=0&w=480&h=360&ow=240&oh=180&screen=srgb&cs=density&emph=redgreen&k=4"
        r = call("get", f"/api/view?{q}")
        assert r.status_code == 200 and r.mimetype == "image/png", (view, r.data[:200])
        assert Image.open(io.BytesIO(r.data)).size == (240, 180)
    assert call("get", "/api/view?view=boost&x=0&y=0&w=480&h=360&ow=99999&oh=10").status_code == 400
    assert call("get", "/api/view?view=nope&x=0&y=0&w=480&h=360&ow=10&oh=10").status_code == 400
    r = call("get", "/api/strip?view=stretch&k=4&screen=p3")
    assert r.status_code == 200 and Image.open(io.BytesIO(r.data)).size[0] > 100
    r = call("post", "/api/boxes", {"boxes": [[400, 10, 40, 40], [300, 10, 40, 40]]})
    assert [b["used"] for b in r.get_json()["state"]["image"]["boxes"]] == [True, True]
    r = call("post", "/api/crop", {"box": [10, 10, 460, 340]})
    im = r.get_json()["state"]["image"]
    assert im["crop"] == [10, 10, 460, 340] and len(im["boxes"]) == 2                  # boxes kept with the crop
    out = env["tmp"] / "out"
    r = call("post", "/api/export", {"look": {"view": "departs"}, "folder": str(out), "edge": "full"})
    assert r.status_code == 200, r.get_json()
    pic = Image.open(r.get_json()["data"]["path"])
    assert pic.size[0] == 480 and pic.size[1] > 360                                   # its words printed under it
    r = call("post", "/api/settings", {"T0": 2.5, "near_black": 9})
    assert r.get_json()["state"]["settings"]["T0"] == 2.5
    assert call("post", "/api/settings", {"T0": 99}).status_code == 400
    assert call("post", "/api/settings", {"nope": 1}).status_code == 400


def test_session_remembers(env):
    call, photos = env["call"], env["photos"]
    call("post", "/api/folder", {"path": str(photos)})
    call("post", "/api/open", {"path": str(photos / "a_unpainted.tif")})
    call("post", "/api/crop", {"box": [20, 20, 400, 300]})
    app2 = create_app(env["tmp"] / "session")
    c2 = app2.test_client()
    H2 = {TOKEN_HEADER: app2.config["HANDPAINT_TOKEN"]}
    st = c2.get("/api/state", headers=H2).get_json()["state"]
    assert st["folder"] == str(photos.resolve())
    r = c2.post("/api/open", headers=H2, json={"path": str(photos / "a_unpainted.tif")})
    assert r.get_json()["state"]["image"]["crop"] == [20, 20, 400, 300]


def test_upload(env):
    call = env["call"]
    buf = io.BytesIO()
    Image.fromarray(np.full((40, 60, 3), 120, np.uint8)).save(buf, format="PNG")
    r = env["c"].post("/api/upload", headers=env["H"], data={"file": (io.BytesIO(buf.getvalue()), "../../x y.png")},
                      content_type="multipart/form-data")
    assert r.status_code == 200, r.get_json()
    added = r.get_json()["state"]["added"]
    assert [a["name"] for a in added] == ["x_y.png"]                                  # the name made safe
    assert call("post", "/api/open", {"path": added[0]["path"]}).status_code == 200
    r = env["c"].post("/api/upload", headers=env["H"], data={"file": (io.BytesIO(b"x"), "a.exe")},
                      content_type="multipart/form-data")
    assert r.status_code == 400


def test_batch(env):
    call, photos = env["call"], env["photos"]
    out = env["tmp"] / "batch_out"
    looks = [{"view": "boost"}, {"view": "stretch", "cs": "lab", "emph": "balanced"}, {"view": "departs"}]
    r = call("post", "/api/batch", {"folder_in": str(photos), "folder_out": str(out), "looks": looks, "edge": 2000})
    assert r.status_code == 200, r.get_json()
    for _ in range(200):
        b = call("get", "/api/progress").get_json()["batch"]
        if b["finished"]:
            break
        time.sleep(0.1)
    assert b["finished"] and b["done"] == 2 and not b["errors"], b
    names = sorted(p.name for p in out.iterdir())
    assert "handpaint_run.json" in names and len([n for n in names if n.endswith(".png")]) == 6
    rec = json.loads((out / "handpaint_run.json").read_text())
    assert "No boxes are used in batch runs" in rec["note"]
    assert call("post", "/api/batch", {"folder_in": str(photos), "folder_out": str(photos), "looks": looks}).status_code == 400


def test_changes_run_in_order(env):
    """Removing boxes while the photograph is still being opened must not bring them back."""
    import threading
    call, photos = env["call"], env["photos"]
    call("post", "/api/folder", {"path": str(photos)})
    call("post", "/api/open", {"path": str(photos / "a_unpainted.tif")})
    call("post", "/api/boxes", {"boxes": [[400, 10, 40, 40]]})
    t = threading.Thread(target=lambda: call("post", "/api/open", {"path": str(photos / "a_unpainted.tif")}))
    t.start()
    time.sleep(0.02)
    call("post", "/api/boxes", {"boxes": []})
    t.join()
    assert call("get", "/api/state").get_json()["state"]["image"]["boxes"] == []
