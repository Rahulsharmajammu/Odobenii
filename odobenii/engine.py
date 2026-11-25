"""The analysis behind every picture: what this print looks like unpainted, and how far each place departs from it.

The design is the rebuild plan's (TODO.md, build step 1). It passed the gate on real test captures (23 Nov), judged by
eye:

- **The reference**, "this print unpainted": the print's own tone as a smooth, stiff curve of a*b* against L*, fitted
  to place votes (each tile of a 10 x 10 grid votes once per 2 L* band) with a high-breakdown fit (least trimmed
  squares, then Tukey biweight steps), so paint that is local cannot become the reference.  Boxes the user has
  examined on the object join the fit as anchors, at the tones where a box in another part of the print agrees.
- **Departures**: each pixel's a*b* minus the reference at its L*.
- **Pictures**: the original; the boost (departures x k, the print's tone drawn neutral grey); the decorrelation
  stretch in two spaces with three emphases and three guards; the expected-unpainted picture x 4; and "where colour
  departs", drawn bright on a dimmed print from a threshold that the paint's colour cannot raise: T = max(T0, 3 sigma),
  sigma from pixel noise and an edge term (so sharp changes in lightness raise it, the paint's own included).

No picture or answer here is a measurement: the server sends pictures, settings and words, never figures about paint.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np

from . import colour

# -- developer constants (not user presets; the gate scores them) -------------------------------------------------------
GRID = 10                     # tiles a side for the place votes
BAND = 2.0                    # L* width of a vote's band
MIN_VOTE_PX = 30              # pixels a tile needs in a band to vote
SEGMENTS = 10                 # B-spline segments across the judged tones
STIFF = 3.0                   # second-difference penalty, per vote and basis function
LTS_SHARE = 0.6               # share of votes the trimmed start keeps
LTS_STARTS = 16
BIWEIGHT_C = 4.685
SCALE_FLOOR = 0.25            # ΔE: the fit's scale never goes below this
BOX_WEIGHT = 5.0              # one box vote counts as this many place votes
MIN_BOX_PX = 400              # judged analysis pixels a box needs (about 20 x 20)
BOX_APART = 0.1               # boxes corroborate one another only this far apart (share of the print's shorter side)
NOISE_LAG = 3                 # px at analysis size, for the shift-difference noise
CAP = 2.0                     # guard 3: largest ratio between the stretch's two gains
EXPECTED_X = 4.0              # the expected-unpainted picture's exaggeration
EMPHASES = ("balanced", "redgreen", "yellowblue")
SPACES = ("lab", "density")
VIEWS = ("original", "boost", "stretch", "expected", "departs")
VIS_LABEL = "Visualisation only - not a measurement"
BLANK_LABEL = "Blank does not mean unpainted"
RELATIVE_LABEL = "Colour differences within this photograph, not absolute colour"


@dataclass
class Settings:
    """What the analysis uses; changed only from the page's advanced settings."""
    T0: float = 2.0               # ΔE: the departure picture's fixed floor
    near_black: float = 8.0       # L*: darker is not judged
    near_white: float = 97.0      # L*: lighter is not judged
    analysis_edge: int = 3000     # px, the analysis's long edge
    default_space: str = "sRGB"   # for files with no colour-space information

    def check(self) -> "Settings":
        if not 0.5 <= self.T0 <= 10.0:
            raise ValueError("T0 must be between 0.5 and 10 ΔE")
        if not 2.0 <= self.near_black <= 30.0 or not 80.0 <= self.near_white <= 99.5:
            raise ValueError("near-black must be 2-30 L* and near-white 80-99.5 L*")
        if not 800 <= int(self.analysis_edge) <= 6000:
            raise ValueError("the analysis size must be 800-6000 px")
        if self.default_space not in colour.DEFAULT_SPACES:
            raise ValueError(f"the default colour space must be one of {', '.join(colour.DEFAULT_SPACES)}")
        self.analysis_edge = int(self.analysis_edge)
        return self


@dataclass
class Look:
    """How one picture is drawn.  Pictures only: nothing here changes the analysis."""
    view: str = "boost"
    k: float = 4.0                # strength: the mean gain on departures
    space: str = "lab"            # the stretch's space: 'lab' (how colour looks) or 'density' (how much colourant)
    emphasis: str = "balanced"    # the stretch's emphasis
    tone: bool = True             # guard 1: stretch departures from the print's own tone
    unpainted: bool = True        # guard 2: statistics from unpainted places (or the boxes)
    cap: bool = True              # guard 3: at most CAP between the two gains
    hatch: bool = True            # hatch what is not judged

    @staticmethod
    def parse(d) -> "Look":
        """From a mapping of strings (a query) or values (JSON); every value checked."""
        def flag(name, default):
            v = d.get(name, default)
            if isinstance(v, bool):
                return v
            if str(v) in ("1", "true", "on"):
                return True
            if str(v) in ("0", "false", "off"):
                return False
            raise ValueError(f"{name} must be 0 or 1")
        lk = Look(view=str(d.get("view", "boost")), space=str(d.get("cs", d.get("space", "lab"))),
                  emphasis=str(d.get("emph", d.get("emphasis", "balanced"))),
                  tone=flag("tone", True), unpainted=flag("unpainted", True), cap=flag("cap", True),
                  hatch=flag("hatch", True))
        try:
            lk.k = float(d.get("k", 4.0))
        except (TypeError, ValueError):
            raise ValueError("k must be a number")
        if lk.view not in VIEWS:
            raise ValueError(f"view must be one of {', '.join(VIEWS)}")
        if lk.space not in SPACES:
            raise ValueError(f"space must be one of {', '.join(SPACES)}")
        if lk.emphasis not in EMPHASES:
            raise ValueError(f"emphasis must be one of {', '.join(EMPHASES)}")
        if not (math.isfinite(lk.k) and 1.0 <= lk.k <= 16.0):
            raise ValueError("k must be from 1 to 16")
        return lk

    def describe(self) -> str:
        """The picture in words, for labels and exported files."""
        if self.view == "original":
            return "The photograph"
        if self.view == "expected":
            return f"The print as expected unpainted, its colour x{EXPECTED_X:g}"
        if self.view == "departs":
            return "Where colour departs from the print's own tone"
        if self.view == "boost":
            return f"Boost x{self.k:g}: departures from the print's own tone"
        sp = {"lab": "CIELAB", "density": "density"}[self.space]
        em = {"balanced": "balanced", "redgreen": "red-green emphasis", "yellowblue": "yellow-blue emphasis"}
        off = [n for n, on in (("tone kept", not self.tone), ("statistics from every pixel", not self.unpainted),
                               ("no cap", not self.cap)) if on]
        return (f"Decorrelation stretch x{self.k:g}, {sp}, {em[self.emphasis]}"
                + (f" (guards off: {', '.join(off)})" if off else ""))


# -- small numerical pieces ----------------------------------------------------------------------------------------------

def bbase(x: np.ndarray, lo: float, hi: float, nseg: int = SEGMENTS, deg: int = 3) -> np.ndarray:
    """Cubic B-spline basis on equally spaced knots over [lo, hi] (P-spline style), one row per x."""
    dx = (hi - lo) / nseg
    knots = lo + dx * np.arange(-deg, nseg + deg + 1)
    x = np.clip(np.asarray(x, dtype=np.float64), lo, hi - 1e-9)
    B = ((x[:, None] >= knots[None, :-1]) & (x[:, None] < knots[None, 1:])).astype(np.float64)
    for d in range(1, deg + 1):
        left = (x[:, None] - knots[None, :-(d + 1)]) / (knots[None, d:-1] - knots[None, :-(d + 1)])
        right = (knots[None, d + 1:] - x[:, None]) / (knots[None, d + 1:] - knots[None, 1:-d])
        B = left * B[:, :-1] + right * B[:, 1:]
    return B


def _penalty(p: int) -> np.ndarray:
    D = np.diff(np.eye(p), n=2, axis=0)
    return D.T @ D


def _solve(A, Y, w, P, lam):
    Aw = A * w[:, None]
    return np.linalg.solve(Aw.T @ A + lam * P + 1e-9 * np.eye(A.shape[1]), Aw.T @ Y)


def robust_curve(Lv: np.ndarray, Y: np.ndarray, lo: float, hi: float, anchors: Optional[np.ndarray] = None,
                 seed: int = 0):
    """A stiff smooth curve Y(L) (Y has two columns) from votes, resistant to a minority of wrong votes anywhere.

    Least trimmed squares (random starts, concentration steps, LTS_SHARE kept) gives the start and a scale; Tukey
    biweight steps at that scale (never below the median-based scale) give the fit.  ``anchors`` marks votes that are
    never trimmed and keep BOX_WEIGHT.  Returns (coefficients, weights per vote, scale)."""
    n = len(Lv)
    A = bbase(Lv, lo, hi)
    p = A.shape[1]
    P = _penalty(p)
    anc = np.zeros(n, bool) if anchors is None else anchors.astype(bool)
    base_w = np.where(anc, BOX_WEIGHT, 1.0)
    lam = STIFF * max(1.0, base_w.sum() / p)
    if n < 6:
        beta = _solve(A, Y, base_w, P, lam * 10)
        return beta, np.ones(n), SCALE_FLOOR
    rng = np.random.default_rng(seed)
    h = max(int(LTS_SHARE * n), min(n, p + 2))
    best = None
    for _ in range(LTS_STARTS):
        sub = rng.choice(n, min(n, max(3 * p, 24)), replace=False)
        w = np.zeros(n)
        w[sub] = base_w[sub]
        w[anc] = base_w[anc]
        beta = _solve(A, Y, w, P, lam)
        for _ in range(8):
            r2 = ((Y - A @ beta) ** 2).sum(1)
            r2[anc] = -1.0
            keep = np.argpartition(r2, h - 1)[:h]
            w = np.zeros(n)
            w[keep] = base_w[keep]
            beta_new = _solve(A, Y, w, P, lam)
            if np.allclose(beta_new, beta, atol=1e-6):
                beta = beta_new
                break
            beta = beta_new
        r2 = ((Y - A @ beta) ** 2).sum(1)
        obj = np.partition(r2, h - 1)[:h].sum()
        if best is None or obj < best[0]:
            best = (obj, beta)
    beta = best[1]
    r2 = ((Y - A @ beta) ** 2).sum(1)
    # per-axis scale of 2-D residuals: |r|^2 ~ s^2 chi2(2); the kept 60 % have mean 0.779 s^2, all have median 1.386 s^2
    s_lts = math.sqrt(np.partition(r2, h - 1)[:h].mean() / 0.779)
    s_med = math.sqrt(np.median(r2) / 1.386)
    scale = max(SCALE_FLOOR, s_lts, s_med)
    w = base_w.copy()
    for _ in range(30):
        u = np.sqrt(((Y - A @ beta) ** 2).sum(1)) / (BIWEIGHT_C * scale)
        bw = np.where(u < 1.0, (1.0 - u * u) ** 2, 0.0)
        w = np.where(anc, BOX_WEIGHT, bw)
        beta_new = _solve(A, Y, w, P, lam)
        if np.allclose(beta_new, beta, atol=1e-5):
            beta = beta_new
            break
        beta = beta_new
    return beta, np.where(anc, 1.0, w), scale


def _gains(C: np.ndarray, k: float, cap: bool) -> np.ndarray:
    """The decorrelation stretch on a 2 x 2 covariance: the quieter direction gains more, by at most CAP (guard 3),
    with the gains' geometric mean k, so strength means the same in every stretch."""
    vals, vecs = np.linalg.eigh(C + 1e-12 * np.eye(2))
    vals = np.maximum(vals, 1e-12)
    ratio = math.sqrt(vals[1] / vals[0])          # vals ascending: vecs[:, 0] is the quieter direction
    ratio = min(ratio, CAP) if cap else min(ratio, 30.0)
    g_quiet, g_loud = k * math.sqrt(ratio), k / math.sqrt(ratio)
    return vecs @ np.diag([g_quiet, g_loud]) @ vecs.T


def _emphasis(name: str) -> np.ndarray:
    """A 2:1 emphasis along a space's own red-green (first) or yellow-blue (second) axis, geometric mean 1.  Both
    directions of the axis gain alike, so noise gains no cast."""
    if name == "redgreen":
        return np.diag([math.sqrt(2.0), 1.0 / math.sqrt(2.0)])
    if name == "yellowblue":
        return np.diag([1.0 / math.sqrt(2.0), math.sqrt(2.0)])
    return np.eye(2)


# density chroma plane: u ~ red-green (R minus G), v ~ yellow-blue ((R+G)/2 minus B), in log10 units
_E = np.array([[1.0, -1.0, 0.0], [0.5, 0.5, -1.0]]) / np.array([[math.sqrt(2.0)], [math.sqrt(1.5)]])


def _density_plane(lin: np.ndarray) -> np.ndarray:
    D = -np.log10(np.maximum(lin, 1e-4))
    return D @ _E.T.astype(np.float32)


def _density_to_ab() -> np.ndarray:
    """2 x 2 map from a density-plane departure to the a*b* it gives at a mid grey (L* 60), so density pictures show
    colourant the same at every tone."""
    grey = colour.linear_from_lab(np.array([[60.0, 0.0, 0.0]], np.float32))[0].astype(np.float64)
    J = np.zeros((2, 2))
    pinv = np.linalg.pinv(_E)
    for i in range(2):
        dD = pinv @ (np.eye(2)[i] * 0.01)          # density offsets per channel for 0.01 along axis i
        lab = colour.lab_from_linear((grey * 10.0 ** (-dD))[None].astype(np.float32))[0]
        J[:, i] = lab[1:] / 0.01
    return J


_D2AB = None


def density_to_ab() -> np.ndarray:
    global _D2AB
    if _D2AB is None:
        _D2AB = _density_to_ab()
    return _D2AB


# -- the analysis of one photograph --------------------------------------------------------------------------------------

@dataclass
class BoxResult:
    box: List[float]
    used: bool
    note: str


class Analysis:
    """One photograph, analysed.  Views draw any region of it at any size."""

    def __init__(self, lin: np.ndarray, clipped: np.ndarray, info: dict, settings: Settings,
                 crop: Optional[Sequence[float]] = None, boxes: Sequence[Sequence[float]] = (), progress=None):
        self.settings = settings
        self.info = info
        self.H, self.W = lin.shape[:2]
        say = progress or (lambda label, frac: None)
        say("Converting to CIELAB", 0.15)
        self.lab_full = np.empty(lin.shape, np.float16)
        for r0 in range(0, self.H, colour.ROWS):
            self.lab_full[r0:r0 + colour.ROWS] = colour.lab_from_linear(lin[r0:r0 + colour.ROWS])
        self.clip_full = clipped
        self.scale = min(1.0, settings.analysis_edge / max(self.H, self.W))
        self.h = max(1, int(round(self.H * self.scale)))
        self.w = max(1, int(round(self.W * self.scale)))
        say("Reducing to the analysis size", 0.3)
        lin_a = cv2.resize(lin, (self.w, self.h), interpolation=cv2.INTER_AREA) if self.scale < 1 else lin.copy()
        self.lab = colour.lab_from_linear(lin_a)
        self.clip_a = cv2.resize(clipped.astype(np.uint8), (self.w, self.h), interpolation=cv2.INTER_AREA) > 0 \
            if self.scale < 1 else clipped.copy()
        L = self.lab[..., 0]
        self.valid = (~self.clip_a) & (L > settings.near_black) & (L < settings.near_white)
        Lb = cv2.GaussianBlur(L, (0, 0), 1.0)
        gx, gy = cv2.Sobel(Lb, cv2.CV_32F, 1, 0, ksize=3) / 8.0, cv2.Sobel(Lb, cv2.CV_32F, 0, 1, ksize=3) / 8.0
        self.G = np.sqrt(gx * gx + gy * gy)
        self.lab_blur = np.stack([cv2.GaussianBlur(self.lab[..., i], (0, 0), 1.0) for i in range(3)], -1)
        self.crop = self._check_box(crop) if crop else None
        self.in_print = np.zeros((self.h, self.w), bool)
        x0, y0, x1, y1 = self._to_a(self.crop) if self.crop else (0, 0, self.w, self.h)
        self.in_print[y0:y1, x0:x1] = True
        self._stats: Dict[tuple, np.ndarray] = {}
        self._box_px = np.zeros((self.h, self.w), bool)
        say("Measuring the capture's noise", 0.45)
        self._noise()
        say("Voting places", 0.6)
        self._place_votes()
        self.boxes: List[BoxResult] = []
        say("Fitting the reference", 0.75)
        self.set_boxes(boxes)
        say("Done", 1.0)

    # geometry -------------------------------------------------------------------------------------------------------
    def _check_box(self, b) -> List[float]:
        if not (isinstance(b, (list, tuple)) and len(b) == 4 and all(isinstance(v, (int, float)) for v in b)):
            raise ValueError("a box is [x, y, width, height] in image pixels")
        x, y, w, h = (float(v) for v in b)
        if not all(math.isfinite(v) for v in (x, y, w, h)) or w <= 0 or h <= 0:
            raise ValueError("a box needs a positive width and height")
        x0, y0 = max(0.0, x), max(0.0, y)
        x1, y1 = min(float(self.W), x + w), min(float(self.H), y + h)
        if x1 - x0 < 2 or y1 - y0 < 2:
            raise ValueError("a box must lie on the image")
        return [x0, y0, x1 - x0, y1 - y0]

    def _to_a(self, b) -> Tuple[int, int, int, int]:
        x, y, w, h = b
        s = self.scale
        x0, y0 = int(math.floor(x * s)), int(math.floor(y * s))
        x1, y1 = int(math.ceil((x + w) * s)), int(math.ceil((y + h) * s))
        return max(0, x0), max(0, y0), min(self.w, max(x0 + 1, x1)), min(self.h, max(y0 + 1, y1))

    # noise ----------------------------------------------------------------------------------------------------------
    def _noise(self):
        """Per-axis chroma noise variance by tone, from differences of pixels NOISE_LAG apart (on the blurred image
        the departure picture uses), edges left out; median-based, so a wash cannot inflate it."""
        ab, L = self.lab_blur[..., 1:], self.lab_blur[..., 0]
        g_lo = np.percentile(self.G[self.valid], 60) if self.valid.any() else 1.0
        ok = self.valid & self.in_print & (self.G < g_lo)
        lag = NOISE_LAG
        ds, ls = [], []
        for dy, dx in ((0, lag), (lag, 0)):
            m = ok[: self.h - dy, : self.w - dx] & ok[dy:, dx:]
            ds.append(ab[: self.h - dy, : self.w - dx][m] - ab[dy:, dx:][m])
            ls.append(0.5 * (L[: self.h - dy, : self.w - dx][m] + L[dy:, dx:][m]))
        d = np.concatenate(ds).astype(np.float64)
        ll = np.concatenate(ls)
        lo, hi = self.settings.near_black, self.settings.near_white
        edges = np.linspace(lo, hi, 11)
        cen, var = [], []
        for i in range(10):
            m = (ll >= edges[i]) & (ll < edges[i + 1])
            if m.sum() >= 200:
                var.append(np.median((d[m] ** 2).sum(1)) / 2.77 + 1e-6)
                cen.append(float(np.median(ll[m])))
        if not cen:
            cen, var = [50.0], [0.05]
        self.noise_L, self.noise_var = np.array(cen), np.array(var)

    def noise_at(self, L: np.ndarray) -> np.ndarray:
        return np.interp(L, self.noise_L, self.noise_var)

    # votes and the reference ----------------------------------------------------------------------------------------
    def _place_votes(self):
        lo, hi = self.settings.near_black, self.settings.near_white
        m = self.valid & self.in_print
        ys, xs = np.nonzero(m)
        x0, y0, x1, y1 = self._to_a(self.crop) if self.crop else (0, 0, self.w, self.h)
        tx = np.minimum(((xs - x0) * GRID) // max(1, x1 - x0), GRID - 1)
        ty = np.minimum(((ys - y0) * GRID) // max(1, y1 - y0), GRID - 1)
        L = self.lab[ys, xs, 0]
        nb = int(math.ceil((hi - lo) / BAND))
        band = np.minimum(((L - lo) / BAND).astype(int), nb - 1)
        key = (ty * GRID + tx) * nb + band
        order = np.argsort(key, kind="stable")
        key_s = key[order]
        cuts = np.flatnonzero(np.diff(key_s)) + 1
        starts = np.concatenate([[0], cuts])
        ends = np.concatenate([cuts, [len(key_s)]])
        lab_s = self.lab[ys[order], xs[order]]
        votes, keys = [], []
        for s, e in zip(starts, ends):
            if e - s >= MIN_VOTE_PX:
                votes.append(np.median(lab_s[s:e], axis=0))
                keys.append(int(key_s[s]))
        self.nb = nb
        self.votes = np.array(votes, np.float64).reshape(-1, 3)
        self.vote_keys = np.array(keys, np.int64)
        # pixel -> vote key, for the inlier map
        self._px_key = np.full((self.h, self.w), -1, np.int64)
        self._px_key[ys, xs] = key

    def set_boxes(self, boxes: Sequence[Sequence[float]]):
        """Boxes the user examined on the object and knows are unpainted.  A box counts only inside the print area,
        only if it is large enough to judge, and only where a box in another part of the print covers the same tones
        and agrees with it.  There it anchors the reference, and the boxes set the stretch's statistics.  Refits the
        reference."""
        boxes = [self._check_box(b) for b in boxes][:12]
        lo = self.settings.near_black
        px0, py0, px1, py1 = self._to_a(self.crop) if self.crop else (0, 0, self.w, self.h)
        apart_px = BOX_APART * min(px1 - px0, py1 - py0)
        no_tones = "Not used: no judged tones in it (too dark, too light or clipped)."
        rects, per_box, why = [], [], []
        for b in boxes:
            x0, y0, x1, y1 = self._to_a(b)
            rects.append((x0, y0, x1, y1))
            inside = self.in_print[y0:y1, x0:x1]
            sub = self.lab[y0:y1, x0:x1][self.valid[y0:y1, x0:x1] & inside]
            bands = {}
            if not inside.any():
                why.append("Not used: it lies outside the print area. Boxes go on the image, not on the margin or "
                           "the mount.")
            elif not len(sub):
                why.append(no_tones)
            elif len(sub) < MIN_BOX_PX:
                why.append("Not used: too small to judge. Draw it larger.")
            else:
                bi = np.minimum(((sub[:, 0] - lo) / BAND).astype(int), self.nb - 1)
                for k in np.unique(bi):
                    sel = sub[bi == k]
                    if len(sel) >= 20:
                        bands[int(k)] = np.median(sel, axis=0)
                why.append(None if bands else no_tones)
            per_box.append(bands)

        def apart(i, j):
            (ax0, ay0, ax1, ay1), (bx0, by0, bx1, by1) = rects[i], rects[j]
            return math.hypot(max(0, bx0 - ax1, ax0 - bx1), max(0, by0 - ay1, ay0 - by1)) >= apart_px

        # a first fit from places only gives the capture's scatter for the cross-check
        self._fit(np.zeros((0, 3)))
        thr = max(1.0, 3.0 * self.fit_scale)
        results, anchors = [], []
        for i, b in enumerate(boxes):
            if why[i]:
                results.append(BoxResult(b, False, why[i]))
                continue
            partners = [j for j in range(len(boxes)) if j != i and not why[j] and apart(i, j)
                        and set(per_box[i]) & set(per_box[j])]
            if not partners:
                results.append(BoxResult(b, False, "Not used yet: no box in another part of the print covers its "
                                                   "tones. Draw a second one at the same tones, away from it."))
                continue
            agree = []
            for j in partners:
                common = set(per_box[i]) & set(per_box[j])
                if np.median([np.linalg.norm(per_box[i][c][1:] - per_box[j][c][1:]) for c in common]) <= thr:
                    agree.append(j)
            if 2 * (len(partners) - len(agree)) > len(partners):          # most of the boxes at its tones disagree
                results.append(BoxResult(b, False, "Not used: it disagrees with the other boxes at the same tones. "
                                                   "One of them may hold paint."))
                continue
            shared = set().union(*(set(per_box[i]) & set(per_box[j]) for j in agree))
            n = len(agree)
            results.append(BoxResult(b, True, f"Used: it agrees with {n} box{'es' if n > 1 else ''} elsewhere, at the "
                                              "tones they share."))
            anchors.extend(per_box[i][c] for c in sorted(shared))
        self.boxes = results
        self._box_px = np.zeros((self.h, self.w), bool)
        for r, (x0, y0, x1, y1) in zip(results, rects):
            if r.used:
                self._box_px[y0:y1, x0:x1] = True
        self._box_px &= self.valid & self.in_print
        self._fit(np.array(anchors, np.float64).reshape(-1, 3))

    def _fit(self, anchors: np.ndarray):
        lo, hi = self.settings.near_black, self.settings.near_white
        V = self.votes if len(anchors) == 0 else np.concatenate([self.votes, anchors])
        anc = np.concatenate([np.zeros(len(self.votes), bool), np.ones(len(anchors), bool)])
        if len(V) == 0:
            self.beta = None
            self.vote_w = np.zeros(0)
            self.fit_scale = SCALE_FLOOR
            self.ref_grid = np.zeros((401, 2), np.float32)
            self.support = np.zeros(self.nb, bool)
            self.inlier_px = np.zeros((self.h, self.w), bool)
            self._after_fit()
            return
        beta, w, scale = robust_curve(V[:, 0], V[:, 1:], lo, hi, anchors=anc)
        self.beta, self.fit_scale = beta, scale
        self.vote_w = w[: len(self.votes)]
        grid = np.linspace(0.0, 100.0, 401)
        g = np.clip(grid, lo, hi)
        self.ref_grid = (bbase(g, lo, hi) @ beta).astype(np.float32)
        # tones the reference is guessing: bands with fewer than two places agreeing
        inl = self.vote_keys[self.vote_w > 0.5]
        counts = np.bincount(inl % self.nb, minlength=self.nb)
        self.support = counts >= 2
        good = np.zeros(int(self._px_key.max()) + 2 if self._px_key.size else 1, bool)
        good[inl] = True
        k = self._px_key
        self.inlier_px = (k >= 0) & good[np.maximum(k, 0)]
        self._after_fit()

    def _after_fit(self):
        self._stats = {}
        lo, hi = self.settings.near_black, self.settings.near_white
        L = self.lab_blur[..., 0]
        d = self.lab_blur[..., 1:] - self.ref(L)
        de = np.sqrt((d ** 2).sum(-1))
        # the edge term: how the colour left over after pixel noise grows with the squared lightness gradient, on the
        # places the reference holds as unpainted, with any boxes (boxes alone are mostly flat and cannot show it).
        # It is a slope, so leftover colour that does not grow with the gradient (blotches, a misfit of the reference)
        # falls into the intercept and cannot raise the threshold at edges.  Paint's own edges still can.
        sel = (self.inlier_px & self.valid) | self._box_px
        kappa2 = 0.0
        if sel.sum() > 500:
            G, r2, nv = self.G[sel], (d[sel] ** 2).sum(-1), self.noise_at(L[sel])
            qs = np.quantile(G, np.linspace(0.0, 1.0, 11))
            xs, ys = [], []
            for a, b in zip(qs[:-1], qs[1:]):
                m = (G >= a) & (G <= b)
                if m.sum() > 50:
                    xs.append(float(np.median(G[m])) ** 2)
                    ys.append(float(np.median(r2[m]) / 1.386 - np.median(nv[m])))
            slopes = [(ys[j] - ys[i]) / (xs[j] - xs[i]) for i in range(len(xs)) for j in range(i + 1, len(xs))
                      if xs[j] - xs[i] > 1e-6]
            if slopes:                                    # Theil-Sen: a bin or two holding paint does not move it
                kappa2 = float(np.clip(np.median(slopes), 0.0, 0.5))
        self.kappa2 = kappa2
        sigma = np.sqrt(self.noise_at(L) + kappa2 * self.G ** 2)
        self.T = np.maximum(self.settings.T0, 3.0 * sigma).astype(np.float32)
        self.dep_alpha = np.clip((de - self.T) / self.T, 0.0, 1.0).astype(np.float32)
        self.dep_alpha[~(self.valid & self.in_print)] = 0.0
        self.dep_dir = (d / np.maximum(de, 1e-6)[..., None]).astype(np.float32)
        band = np.clip(((L - lo) / BAND).astype(int), 0, self.nb - 1)
        self.unsupported = ~self.support[band] & self.valid if self.nb else np.zeros_like(self.valid)

    def ref(self, L: np.ndarray) -> np.ndarray:
        """The reference a*b* at each L*."""
        idx = np.clip(np.rint(np.asarray(L, np.float32) * 4.0), 0, 400).astype(np.int32)
        return self.ref_grid[idx]

    # stretch statistics ---------------------------------------------------------------------------------------------
    def _plane(self, lab: np.ndarray, space: str, tone: bool) -> np.ndarray:
        """Departures in a space's chroma plane: from the print's own tone (guard 1) or from its mean colour."""
        if space == "lab":
            if tone:
                return lab[..., 1:] - self.ref(lab[..., 0])
            return lab[..., 1:] - self._mean_ab
        lin = colour.linear_from_lab(lab)
        u = _density_plane(lin)
        if tone:
            ref_lab = np.concatenate([lab[..., :1], self.ref(lab[..., 0])], -1)
            return u - _density_plane(colour.linear_from_lab(ref_lab))
        return u - self._mean_density

    @property
    def _mean_ab(self) -> np.ndarray:
        m = self.valid & self.in_print
        return self.lab[..., 1:][m].mean(0) if m.any() else np.zeros(2, np.float32)

    @property
    def _mean_density(self) -> np.ndarray:
        if not hasattr(self, "_mean_den"):
            m = self.valid & self.in_print
            self._mean_den = _density_plane(colour.linear_from_lab(self.lab[m])).mean(0) if m.any() \
                else np.zeros(2, np.float32)
        return self._mean_den

    def stats(self, space: str, tone: bool, unpainted: bool) -> np.ndarray:
        """Covariance of departures in a space's plane, over the unpainted places (or the boxes) or every pixel."""
        key = (space, tone, unpainted)
        if key not in self._stats:
            if unpainted:
                sel = self._box_px if self._box_px.any() else (self.inlier_px & self.valid)
            else:
                sel = self.valid & self.in_print
            if sel.sum() < 100:                        # never the frame outside the print area
                sel = self.valid & self.in_print
                if sel.sum() < 100:
                    sel = self.in_print
            ys, xs = np.nonzero(sel)
            if len(ys) > 200_000:
                pick = np.random.default_rng(1).choice(len(ys), 200_000, replace=False)
                ys, xs = ys[pick], xs[pick]
            d = self._plane(self.lab[ys, xs], space, tone).astype(np.float64)
            r = np.sqrt((d ** 2).sum(-1))
            d = d[r <= np.quantile(r, 0.98)] if len(r) > 50 else d
            d = d - d.mean(0) if not tone else d
            C = (d.T @ d) / max(1, len(d))
            self._stats[key] = C
        return self._stats[key]

    def matrix(self, look: Look) -> np.ndarray:
        """The 2 x 2 map from a departure to what is drawn."""
        if look.view == "boost":
            return np.eye(2) * look.k
        return _emphasis(look.emphasis) @ _gains(self.stats(look.space, look.tone, look.unpainted), look.k, look.cap)

    # pictures -------------------------------------------------------------------------------------------------------
    def region(self, x: float, y: float, w: float, h: float, ow: int, oh: int):
        """Lab, clipped mask and analysis-map sampler for a region of the full image drawn at ow x oh."""
        if w <= 0 or h <= 0 or x >= self.W or y >= self.H or x + w <= 0 or y + h <= 0:
            raise ValueError("the region lies outside the image")
        zoom_in = ow / w > self.scale * 1.05            # finer than the analysis size: use the full image
        x0, y0 = max(0, int(math.floor(x))), max(0, int(math.floor(y)))
        x1, y1 = min(self.W, int(math.ceil(x + w))), min(self.H, int(math.ceil(y + h)))
        interp = cv2.INTER_NEAREST if ow > (x1 - x0) else cv2.INTER_AREA
        if zoom_in:
            lab = self.lab_full[y0:y1, x0:x1].astype(np.float32)
            clip = self.clip_full[y0:y1, x0:x1]
        else:
            ax0, ay0, ax1, ay1 = self._to_a([x0, y0, x1 - x0, y1 - y0])
            lab = self.lab[ay0:ay1, ax0:ax1]
            clip = self.clip_a[ay0:ay1, ax0:ax1]
            interp = cv2.INTER_NEAREST if ow > (ax1 - ax0) else cv2.INTER_AREA
        lab = cv2.resize(lab, (ow, oh), interpolation=interp)
        clip = cv2.resize(clip.astype(np.uint8), (ow, oh), interpolation=cv2.INTER_NEAREST) > 0
        ax0, ay0, ax1, ay1 = self._to_a([x0, y0, x1 - x0, y1 - y0])

        def amap(arr, nearest=True):
            sub = arr[ay0:ay1, ax0:ax1]
            if sub.dtype == bool:
                return cv2.resize(sub.astype(np.uint8), (ow, oh), interpolation=cv2.INTER_NEAREST) > 0
            return cv2.resize(sub, (ow, oh), interpolation=cv2.INTER_NEAREST if nearest else cv2.INTER_LINEAR)
        return lab, clip, amap

    def picture(self, look: Look, x: float, y: float, w: float, h: float, ow: int, oh: int) -> np.ndarray:
        """CIELAB (oh x ow x 3) of a region drawn as ``look`` says."""
        lab, clip, amap = self.region(x, y, w, h, ow, oh)
        origin = (int(round(x * ow / w)), int(round(y * oh / h)))      # hatching stays put as the view pans
        return self.draw(look, lab, clip, amap, origin)

    def hatched(self, lab: np.ndarray, clip: np.ndarray) -> np.ndarray:
        L = lab[..., 0]
        return clip | (L <= self.settings.near_black) | (L >= self.settings.near_white)

    def draw(self, look: Look, lab: np.ndarray, clip: np.ndarray, amap=None, origin=(0, 0)) -> np.ndarray:
        L = lab[..., 0]
        out = np.empty_like(lab)
        out[..., 0] = L
        hat = self.hatched(lab, clip)
        if look.view == "original":
            out[...] = lab
            return out
        if look.view in ("boost", "stretch"):
            M = self.matrix(look)
            space = "lab" if look.view == "boost" else look.space
            d = self._plane(lab, space, look.tone or look.view == "boost")
            sd = d @ M.T.astype(np.float32)
            if space == "density":
                sd = sd @ density_to_ab().T.astype(np.float32)
            out[..., 1:] = sd
            out[..., 1:][hat] = 0.0
        elif look.view == "expected":
            out[..., 1:] = self.ref(L) * EXPECTED_X
            out[..., 1:][hat] = 0.0
            if amap is not None:
                guess = amap(self.unsupported)
                hat = hat | guess
        elif look.view == "departs":
            alpha = amap(self.dep_alpha, nearest=False) if amap is not None else np.zeros(L.shape, np.float32)
            dirs = amap(self.dep_dir, nearest=False) if amap is not None else np.zeros(L.shape + (2,), np.float32)
            alpha = np.clip(alpha, 0.0, 1.0)
            dim = 22.0 + 0.3 * L
            out[..., 0] = (1 - alpha) * dim + alpha * 80.0
            nrm = np.maximum(np.sqrt((dirs ** 2).sum(-1)), 1e-6)[..., None]
            out[..., 1:] = alpha[..., None] * 42.0 * dirs / nrm
            if amap is not None:                          # where the reference is guessing: stripes, not blanking
                hat = hat | amap(self.unsupported)
        if look.hatch and hat.any():
            yy, xx = np.indices(L.shape)
            stripe = ((xx + yy + origin[0] + origin[1]) % 7) < 2
            on = hat & stripe
            out[..., 0][on] = np.where(L[on] > 50, L[on] - 30, L[on] + 30)
            out[..., 1:][on] = 0.0
        return out

    def summary(self) -> dict:
        """What the page shows about the analysis, in words and settings only."""
        return {
            "size": [self.W, self.H],
            "analysis_size": [self.w, self.h],
            "crop": self.crop,
            "boxes": [asdict(b) for b in self.boxes],
            "guessing": bool(self.unsupported.any()),
            "no_votes": len(self.votes) == 0,
        }

