"""The app's state: the folder of photographs, the one being looked at and its analysis, each photograph's print area
and boxes, the settings, and batch runs.  It lives in a session folder (``session.json``, and ``images/`` for files
added from the browser), so a restart reopens where the user left off."""
from __future__ import annotations

import json
import threading
import time
import traceback
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional

from .. import __version__, colour, engine, pictures

MAX_FILES = 2000                 # listed from one folder


class SessionError(Exception):
    """Something the user asked that cannot be done, with the reason in words."""


class Progress:
    def __init__(self):
        self.lock = threading.Lock()
        self.label, self.frac, self.t0, self.busy = "", 0.0, 0.0, False

    def start(self, label):
        with self.lock:
            self.label, self.frac, self.t0, self.busy = label, 0.0, time.time(), True

    def set(self, label, frac):
        with self.lock:
            self.label, self.frac = label, frac

    def end(self):
        with self.lock:
            self.busy = False

    def state(self):
        with self.lock:
            return {"busy": self.busy, "label": self.label, "frac": self.frac,
                    "seconds": round(time.time() - self.t0, 1) if self.busy else 0}


def _files(folder: Path) -> List[dict]:
    out = []
    for p in sorted(folder.iterdir(), key=lambda q: q.name.lower()):
        if p.is_file() and p.suffix.lower() in colour.READABLE and not p.name.startswith("."):
            st = p.stat()
            out.append({"name": p.name, "path": str(p), "mb": round(st.st_size / 1e6, 1)})
        if len(out) >= MAX_FILES:
            break
    return out


class Session:
    def __init__(self, root):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.images = self.root / "images"
        self.images.mkdir(exist_ok=True)
        self.lock = threading.RLock()
        self.ops = threading.RLock()                 # changes to the photograph run one at a time, in order
        self.progress = Progress()
        self.settings = engine.Settings()
        self.folder: Optional[Path] = None
        self.memory: Dict[str, dict] = {}            # per photograph: print area, boxes
        self.export_folder = str(self.root / "exports")
        self.path: Optional[Path] = None
        self.analysis: Optional[engine.Analysis] = None
        self.version = 0
        self.batch = {"running": False, "done": 0, "total": 0, "current": "", "out": "", "errors": [],
                      "finished": False, "cancelled": False}
        self._cancel = threading.Event()
        self._load()

    # persistence ----------------------------------------------------------------------------------------------------
    def _load(self):
        f = self.root / "session.json"
        if not f.is_file():
            return
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            self.settings = engine.Settings(**{k: v for k, v in d.get("settings", {}).items()
                                               if k in asdict(engine.Settings())}).check()
            folder = d.get("folder")
            self.folder = Path(folder) if folder and Path(folder).is_dir() else None
            self.memory = {k: v for k, v in d.get("memory", {}).items() if isinstance(v, dict)}
            self.export_folder = d.get("export_folder") or self.export_folder
        except Exception:
            traceback.print_exc()                    # a damaged session file: start clean, keep the file
            (self.root / "session.json").replace(self.root / f"session.damaged.{int(time.time())}.json")

    def _save(self):
        d = {"odobenii": __version__, "settings": asdict(self.settings),
             "folder": str(self.folder) if self.folder else None, "memory": self.memory,
             "export_folder": self.export_folder}
        tmp = self.root / "session.json.tmp"
        tmp.write_text(json.dumps(d, indent=1), encoding="utf-8")
        tmp.replace(self.root / "session.json")

    # state for the page ---------------------------------------------------------------------------------------------
    def state(self) -> dict:
        with self.lock:
            img = None
            if self.analysis is not None and self.path is not None:
                img = {**self.analysis.info, "path": str(self.path), **self.analysis.summary()}
            return {
                "version": __version__,
                "session": str(self.root),
                "folder": str(self.folder) if self.folder else "",
                "files": _files(self.folder) if self.folder else [],
                "added": _files(self.images),
                "settings": asdict(self.settings),
                "image": img,
                "export_folder": self.export_folder,
                "batch": dict(self.batch),
                "words": {"vis": engine.VIS_LABEL, "blank": engine.BLANK_LABEL},
            }

    # folders and files ----------------------------------------------------------------------------------------------
    def set_folder(self, path: str):
        p = Path(str(path)).expanduser()
        if not str(path).strip() or not p.is_dir():
            raise SessionError(f"not a folder: {path}")
        with self.lock:
            self.folder = p.resolve()
            self._save()

    def add_file(self, name: str, stream) -> str:
        from werkzeug.utils import secure_filename
        safe = secure_filename(name or "")
        if not safe or Path(safe).suffix.lower() not in colour.READABLE:
            raise SessionError(f"not a file type this tool reads: {name} (TIFF, PNG, JPEG, WebP, BMP)")
        dest = self.images / safe
        n = 1
        while dest.exists():
            dest = self.images / f"{Path(safe).stem}_{n}{Path(safe).suffix}"
            n += 1
        with open(dest, "wb") as f:
            while True:
                chunk = stream.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
        return str(dest)

    def _listed(self, path: str) -> Path:
        """A photograph the page may open: one listed from the folder or added to the session."""
        p = Path(str(path)).expanduser()
        try:
            p = p.resolve()
        except OSError:
            raise SessionError(f"no such file: {path}")
        allowed = [self.images] + ([self.folder] if self.folder else [])
        if not p.is_file() or p.parent not in allowed or p.suffix.lower() not in colour.READABLE:
            raise SessionError(f"not one of the listed photographs: {path}")
        return p

    # the photograph being looked at ---------------------------------------------------------------------------------
    def open(self, path: str):
        with self.ops:
            self._open(path)

    def _open(self, path: str):
        p = self._listed(path)
        self.progress.start(f"Reading {p.name}")
        try:
            self.progress.set(f"Reading {p.name}", 0.05)
            try:
                lin, clipped, info = colour.read_image(p, self.settings.default_space)
            except colour.ReadError as exc:
                raise SessionError(f"{p.name}: {exc}") from exc
            mem = self.memory.get(str(p), {})
            an = engine.Analysis(lin, clipped, info, self.settings, crop=mem.get("crop"),
                                 boxes=mem.get("boxes", ()), progress=self.progress.set)
            del lin
            with self.lock:
                self.path, self.analysis = p, an
                self.version += 1
        finally:
            self.progress.end()

    def _need(self) -> engine.Analysis:
        if self.analysis is None:
            raise SessionError("open a photograph first")
        return self.analysis

    def set_crop(self, box):
        with self.ops:
            self._set_crop(box)

    def _set_crop(self, box):
        with self.lock:
            an = self._need()
            try:
                crop = an._check_box(box) if box else None
            except ValueError as exc:
                raise SessionError(str(exc)) from exc
            mem = self.memory.setdefault(str(self.path), {})
            mem["crop"] = crop
            self._save()
        self.reanalyse()

    def set_boxes(self, boxes):
        if not isinstance(boxes, list) or len(boxes) > 12:
            raise SessionError("boxes must be a list of at most 12 [x, y, width, height]")
        with self.ops, self.lock:
            an = self._need()
            try:
                an.set_boxes(boxes)
            except ValueError as exc:
                raise SessionError(str(exc)) from exc
            self.memory.setdefault(str(self.path), {})["boxes"] = [b.box for b in an.boxes]
            self._save()
            self.version += 1

    def set_settings(self, d: dict):
        if not isinstance(d, dict):
            raise SessionError("settings must be an object")
        known = asdict(engine.Settings())
        bad = [k for k in d if k not in known]
        if bad:
            raise SessionError(f"unknown settings: {', '.join(bad)}")
        try:
            new = engine.Settings(**{**asdict(self.settings), **d})
            for k in ("T0", "near_black", "near_white"):
                setattr(new, k, float(getattr(new, k)))
            new.check()
        except (TypeError, ValueError) as exc:
            raise SessionError(str(exc)) from exc
        with self.ops:
            with self.lock:
                self.settings = new
                self._save()
            if self.analysis is not None:
                self.reanalyse()

    def reanalyse(self):
        if self.path is not None:
            with self.ops:
                self._open(str(self.path))

    # pictures -------------------------------------------------------------------------------------------------------
    def view(self, look: engine.Look, region, ow: int, oh: int, space: str) -> bytes:
        with self.lock:
            an = self._need()
        lab = an.picture(look, *region, ow, oh)
        return pictures.png(colour.lab_to_screen(lab, space), space)

    def export(self, look: engine.Look, folder: str, edge: Optional[int]) -> str:
        with self.lock:
            an, path = self._need(), self.path
        out = self._out_folder(folder)
        name = f"{path.stem}__{_slug(look)}.png"
        self.progress.start(f"Exporting {name}")
        try:
            data = pictures.exported(an, look, edge)
        finally:
            self.progress.end()
        (out / name).write_bytes(data)
        with self.lock:
            self.export_folder = str(out)
            self._save()
        return str(out / name)

    def _out_folder(self, folder: str) -> Path:
        p = Path(str(folder or "")).expanduser()
        if not str(folder or "").strip():
            raise SessionError("give a folder to write to")
        if p.exists() and not p.is_dir():
            raise SessionError(f"not a folder: {folder}")
        if not p.exists():
            if not p.parent.is_dir():
                raise SessionError(f"its parent folder does not exist: {p.parent}")
            p.mkdir()
        return p.resolve()

    # batch ----------------------------------------------------------------------------------------------------------
    def start_batch(self, folder_in: str, folder_out: str, looks: List[engine.Look], edge: Optional[int]):
        src = Path(str(folder_in or "")).expanduser()
        if not str(folder_in or "").strip() or not src.is_dir():
            raise SessionError(f"not a folder: {folder_in}")
        out = self._out_folder(folder_out)
        if out == src.resolve():
            raise SessionError("write the pictures to another folder than the photographs'")
        if not looks:
            raise SessionError("choose at least one picture to write")
        files = [Path(f["path"]) for f in _files(src.resolve())]
        if not files:
            raise SessionError(f"no photographs this tool reads in {folder_in}")
        with self.lock:
            if self.batch["running"]:
                raise SessionError("a batch run is already going")
            self._cancel.clear()
            self.batch = {"running": True, "done": 0, "total": len(files), "current": "", "out": str(out),
                          "errors": [], "finished": False, "cancelled": False}
        settings = engine.Settings(**asdict(self.settings))
        t = threading.Thread(target=self._run_batch, args=(files, out, looks, edge, settings), daemon=True)
        t.start()

    def cancel_batch(self):
        self._cancel.set()

    def _run_batch(self, files, out, looks, edge, settings):
        record = {"odobenii": __version__, "started": time.strftime("%Y-%m-%d %H:%M:%S"),
                  "settings": asdict(settings), "pictures": [lk.describe() for lk in looks],
                  "note": "No boxes are used in batch runs. " + engine.VIS_LABEL + ".", "files": []}
        for i, p in enumerate(files):
            if self._cancel.is_set():
                with self.lock:
                    self.batch["cancelled"] = True
                break
            with self.lock:
                self.batch["current"] = p.name
            try:
                lin, clipped, info = colour.read_image(p, settings.default_space)
                crop = self.memory.get(str(p), {}).get("crop")
                an = engine.Analysis(lin, clipped, info, settings, crop=crop)
                del lin
                written = []
                for lk in looks:
                    name = f"{p.stem}__{_slug(lk)}.png"
                    (out / name).write_bytes(pictures.exported(an, lk, edge))
                    written.append(name)
                record["files"].append({"file": p.name, "read": info["colour"], "print_area": crop, "wrote": written})
            except Exception as exc:
                msg = f"{p.name}: {exc}"
                with self.lock:
                    self.batch["errors"].append(msg)
                record["files"].append({"file": p.name, "error": str(exc)})
            with self.lock:
                self.batch["done"] = i + 1
        record["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            (out / "odobenii_run.json").write_text(json.dumps(record, indent=1), encoding="utf-8")
        except OSError as exc:
            with self.lock:
                self.batch["errors"].append(f"the run record could not be written: {exc}")
        with self.lock:
            self.batch["running"] = False
            self.batch["finished"] = True
            self.batch["current"] = ""


def _slug(look: engine.Look) -> str:
    if look.view in ("original", "expected", "departs"):
        return look.view
    if look.view == "boost":
        return f"boost{look.k:g}"
    guards = "" if (look.tone and look.unpainted and look.cap) else "_noguards" if not (
        look.tone or look.unpainted or look.cap) else "_" + "".join(
        c for c, on in (("t", look.tone), ("u", look.unpainted), ("c", look.cap)) if on)
    return f"stretch{look.k:g}_{look.space}_{look.emphasis}{guards}"
