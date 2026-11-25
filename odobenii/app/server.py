"""The local web app: a Flask server on 127.0.0.1 that serves the page and the pictures.  Built as Woodii's is.

Photographs never leave the machine: files picked in the browser go to this local server only, into the session
folder.  Every picture is drawn here; the browser only shows them and sends what the user picks.

Other web pages open in the same browser must not be able to drive the server, so every request is checked, as in
Woodii:

- the ``Host`` header must name this machine (127.0.0.1, localhost or [::1]), which refuses DNS rebinding;
- a request carrying an ``Origin`` header must come from this server's own page;
- every /api request must carry the per-launch token that the page receives when it loads, in the
  ``X-Odobenii-Token`` header (pictures too, so another site's <img> can neither draw nor probe), except
  /api/instance, which the launcher asks;
- an /api request the browser marks as cross-site (``Sec-Fetch-Site``) is refused, every /api answer says
  ``Cross-Origin-Resource-Policy: same-origin``, and JSON bodies must be sent as ``application/json``.
"""
from __future__ import annotations

import hmac
import math
import secrets
import traceback
from pathlib import Path
from urllib.parse import urlsplit

from flask import Flask, Response, jsonify, request, send_file

from .. import __version__, engine
from .session import Session, SessionError

STATIC = Path(__file__).with_name("static")
LOCAL_HOSTS = ("127.0.0.1", "localhost", "[::1]", "::1")
TOKEN_HEADER = "X-Odobenii-Token"
TOKEN_PLACEHOLDER = '<meta name="odobenii-token" content="">'
SAFE_METHODS = ("GET", "HEAD", "OPTIONS")
OPEN_READS = ("/api/instance",)
OWN_SITE = ("same-origin", "none")
VIEW_MAX_SIDE = 4096
SCREEN_SPACES = ("srgb", "p3")


def _hostname(h: str) -> str:
    h = (h or "").strip().lower()
    if h.startswith("["):
        return h[: h.find("]") + 1] if "]" in h else h
    return h.rsplit(":", 1)[0] if h.count(":") == 1 else h


def create_app(session_dir) -> Flask:
    app = Flask(__name__, static_folder=None)
    app.json.sort_keys = False
    app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 ** 3        # 2 GB per upload
    session = Session(session_dir)
    token = secrets.token_urlsafe(32)                        # new on every launch; never written to disk
    app.config.update(ODOBENII_SESSION=session, ODOBENII_TOKEN=token,
                      ODOBENII_INSTANCE=secrets.token_hex(8), ODOBENII_STOP=None)

    def refuse(why: str, code: int = 403):
        return jsonify({"ok": False, "error": f"refused: {why}"}), code

    @app.before_request
    def _guard():
        if _hostname(request.host) not in LOCAL_HOSTS:
            return refuse(f"this server answers only to 127.0.0.1 or localhost, not {request.host!r}")
        origin = request.headers.get("Origin")
        if origin and origin != "null":
            parts = urlsplit(origin)
            if _hostname(parts.netloc) not in LOCAL_HOSTS or parts.netloc.lower() != request.host.lower():
                return refuse(f"request from another site ({origin})")
        elif origin == "null" and request.method not in SAFE_METHODS:
            return refuse("request from a sandboxed or local-file page")
        site = request.headers.get("Sec-Fetch-Site")
        if request.path.startswith("/api/") and site is not None and site.lower() not in OWN_SITE:
            return refuse(f"request from another site (Sec-Fetch-Site: {site})")
        if not request.path.startswith("/api/") or request.path in OPEN_READS:
            return None if request.method in SAFE_METHODS else refuse("method not allowed here", 405)
        sent = request.headers.get(TOKEN_HEADER, "")
        if not hmac.compare_digest(sent.encode(), token.encode()):
            return refuse("missing or wrong session token: reload the page")
        if request.content_length and not request.mimetype.startswith("multipart/") and not request.is_json:
            return refuse(f"expected application/json, got {request.mimetype or 'no content type'}", 415)
        return None

    @app.after_request
    def _headers(resp):
        if request.path.startswith("/api/"):
            resp.headers["Cross-Origin-Resource-Policy"] = "same-origin"
            resp.headers.setdefault("Cache-Control", "no-store")
        return resp

    @app.errorhandler(SessionError)
    def _session_error(exc):
        return jsonify({"ok": False, "error": str(exc)}), 400

    @app.errorhandler(Exception)
    def _any(exc):
        if isinstance(getattr(exc, "code", None), int) and exc.code < 500:
            return jsonify({"ok": False, "error": str(exc)}), exc.code
        traceback.print_exc()
        return jsonify({"ok": False, "error": f"{type(exc).__name__}: {exc}. Something went wrong inside "
                                              "Odobenii; the console has the details."}), 500

    def body() -> dict:
        if not request.get_data(cache=True):
            return {}
        d = request.get_json(silent=True)
        if not isinstance(d, dict):
            raise SessionError("the request body must be a JSON object")
        return d

    def ok(payload=None):
        return jsonify({"ok": True, **({} if payload is None else {"data": payload}), "state": session.state()})

    def look_from(d) -> engine.Look:
        try:
            return engine.Look.parse(d)
        except ValueError as exc:
            raise SessionError(str(exc)) from exc

    # -- the page ---------------------------------------------------------------------------------------------------
    page = (STATIC / "index.html").read_text(encoding="utf-8")
    if TOKEN_PLACEHOLDER not in page:
        raise RuntimeError("index.html has no session-token placeholder")
    page = page.replace(TOKEN_PLACEHOLDER, f'<meta name="odobenii-token" content="{token}">')

    @app.get("/")
    def index():
        return Response(page, mimetype="text/html", headers={"Cache-Control": "no-store", "X-Frame-Options": "DENY",
                                                             "Content-Security-Policy": "frame-ancestors 'none'"})

    @app.get("/static/<path:name>")
    def static_file(name):
        p = (STATIC / name).resolve()
        if STATIC.resolve() not in p.parents or not p.is_file():
            return jsonify({"ok": False, "error": "not found"}), 404
        return send_file(p, max_age=0)

    # -- state ------------------------------------------------------------------------------------------------------
    @app.get("/api/state")
    def state():
        return jsonify({"ok": True, "state": session.state()})

    @app.get("/api/progress")
    def progress():
        return jsonify({"ok": True, "progress": session.progress.state(), "batch": session.state()["batch"]})

    @app.get("/api/instance")
    def instance():
        return jsonify({"ok": True, "instance": app.config["ODOBENII_INSTANCE"], "version": __version__})

    @app.post("/api/shutdown")
    def shutdown():
        stop = app.config.get("ODOBENII_STOP")
        if stop is None:
            return jsonify({"ok": False, "error": "this server was not started by the launcher; stop it where it "
                                                  "was started"}), 400
        stop()
        return jsonify({"ok": True})

    # -- photographs ------------------------------------------------------------------------------------------------
    @app.post("/api/folder")
    def folder():
        session.set_folder(body().get("path", ""))
        return ok()

    @app.post("/api/upload")
    def upload():
        files = request.files.getlist("file")
        if not files:
            raise SessionError("no file was sent")
        saved = [session.add_file(f.filename, f.stream) for f in files]
        return ok({"saved": saved})

    @app.post("/api/open")
    def open_():
        session.open(body().get("path", ""))
        return ok()

    @app.post("/api/settings")
    def settings():
        session.set_settings(body())
        return ok()

    @app.post("/api/crop")
    def crop():
        session.set_crop(body().get("box"))
        return ok()

    @app.post("/api/boxes")
    def boxes():
        session.set_boxes(body().get("boxes", []))
        return ok()

    # -- pictures ---------------------------------------------------------------------------------------------------
    def region_args():
        a = request.args
        try:
            region = [float(a.get(k, "nan")) for k in ("x", "y", "w", "h")]
            ow, oh = int(a.get("ow", 800)), int(a.get("oh", 600))
        except ValueError:
            raise SessionError("x, y, w, h, ow and oh must be numbers")
        if not all(math.isfinite(v) for v in region) or region[2] <= 0 or region[3] <= 0:
            raise SessionError("x, y, w and h must give the region to draw, w and h above 0")
        if not (1 <= ow <= VIEW_MAX_SIDE and 1 <= oh <= VIEW_MAX_SIDE):
            raise SessionError(f"picture size {ow} x {oh} is outside 1-{VIEW_MAX_SIDE} a side")
        space = a.get("screen", "srgb")
        if space not in SCREEN_SPACES:
            raise SessionError("screen must be srgb or p3")
        return region, ow, oh, space

    @app.get("/api/view")
    def view():
        region, ow, oh, space = region_args()
        try:
            data = session.view(look_from(request.args), region, ow, oh, space)
        except ValueError as exc:
            raise SessionError(str(exc)) from exc
        return Response(data, mimetype="image/png")

    @app.get("/api/strip")
    def strip():
        space = request.args.get("screen", "srgb")
        if space not in SCREEN_SPACES:
            raise SessionError("screen must be srgb or p3")
        return Response(session.strip(look_from(request.args), space), mimetype="image/png")

    # -- files out --------------------------------------------------------------------------------------------------
    def edge_from(d):
        e = d.get("edge")
        if e in (None, "", "full"):
            return None
        try:
            e = int(e)
        except (TypeError, ValueError):
            raise SessionError("edge must be a number of pixels, or full")
        if not 200 <= e <= 20000:
            raise SessionError("edge must be 200-20000 px")
        return e

    @app.post("/api/export")
    def export():
        d = body()
        path = session.export(look_from(d.get("look", {})), d.get("folder", ""), edge_from(d))
        return ok({"path": path})

    @app.post("/api/batch")
    def batch():
        d = body()
        looks = d.get("looks", [])
        if not isinstance(looks, list) or len(looks) > 12:
            raise SessionError("looks must be a list of at most 12 pictures")
        session.start_batch(d.get("folder_in", ""), d.get("folder_out", ""), [look_from(lk) for lk in looks],
                            edge_from(d))
        return ok()

    @app.post("/api/batch/cancel")
    def batch_cancel():
        session.cancel_batch()
        return ok()

    return app
