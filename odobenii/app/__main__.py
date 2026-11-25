"""Run the local web app:  python -m odobenii.app [--session FOLDER] [--port 8766] [--no-browser]

The server listens on 127.0.0.1 only; photographs stay on this machine.  If the port is taken, the next free one is
used and the console says so.  Launched again on a session folder whose server is still running, it opens that
server's page instead of starting a second one.  Stop it with the page's Stop server button, or Ctrl+C here.
"""
from __future__ import annotations

import argparse
import http.client
import json
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

PORT_TRIES = 20
RUNNING_FILE = ".odobenii_running.json"


def default_session() -> Path:
    """~/odobenii_sessions/default.  A session from before the rename (~/handpaint_sessions/default) is used while it
    is the only one, so its print areas and boxes are not lost."""
    new = Path.home() / "odobenii_sessions" / "default"
    old = Path.home() / "handpaint_sessions" / "default"
    return old if old.is_dir() and not new.exists() else new


def _answers(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def _running_instance(root: Path):
    """(port, instance) of a server already running on this session folder, or None."""
    f = root / RUNNING_FILE
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
        port, inst = int(d["port"]), str(d["instance"])
    except Exception:
        return None
    try:
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=1.0)
        c.request("GET", "/api/instance", headers={"Host": f"127.0.0.1:{port}"})
        r = c.getresponse()
        ok = r.status == 200 and json.loads(r.read()).get("instance") == inst
        c.close()
        return (port, inst) if ok else None
    except Exception:
        return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m odobenii.app",
                                 description="Odobenii, the handpaint visualiser's web app.")
    ap.add_argument("--session", type=Path, default=default_session(), help="session folder (default %(default)s)")
    ap.add_argument("--port", type=int, default=8766)
    ap.add_argument("--no-browser", action="store_true", help="do not open the page in a browser")
    a = ap.parse_args(argv)
    root = a.session.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    other = _running_instance(root)
    if other:
        url = f"http://127.0.0.1:{other[0]}/"
        print(f"Odobenii is already running on {root}: {url}")
        if not a.no_browser:
            webbrowser.open(url)
        return 0

    from werkzeug.serving import make_server
    from .server import create_app

    app = create_app(root)
    server, port = None, None
    for p in range(a.port, a.port + PORT_TRIES):
        if _answers(p):
            continue
        try:
            server = make_server("127.0.0.1", p, app, threaded=True)
            port = p
            break
        except OSError:
            continue
    if server is None:
        print(f"No free port from {a.port} to {a.port + PORT_TRIES - 1}.", file=sys.stderr)
        return 1
    if port != a.port:
        print(f"Port {a.port} is taken; using {port}.")
    running = root / RUNNING_FILE
    running.write_text(json.dumps({"port": port, "instance": app.config["ODOBENII_INSTANCE"], "pid": os.getpid()}),
                       encoding="utf-8")

    def stop():
        threading.Thread(target=lambda: (time.sleep(0.3), server.shutdown()), daemon=True).start()
    app.config["ODOBENII_STOP"] = stop
    url = f"http://127.0.0.1:{port}/"
    print(f"Odobenii is at {url}  (session folder {root}). Ctrl+C to stop.")
    if not a.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            if json.loads(running.read_text(encoding="utf-8")).get("instance") == app.config["ODOBENII_INSTANCE"]:
                running.unlink()
        except Exception:
            pass
        print("Stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
