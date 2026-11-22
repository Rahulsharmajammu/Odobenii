"""Design v2 (merged with the remote-sensing review): reference location and presence rule rebuilt.

Reference ("what unpainted looks like"), in feature space F = CIELAB a*b* or log-chromaticity chi of linear RGB:
  1. LTS start on a stiff model over the WHOLE image (tone quadratic + light plane, 60 % kept, shadows out): what is
     unpainted is decided by majority over the frame, not per tone band, so a wash filling one tone band cannot
     win its band.
  2. Flexible tone curve m(L) = pooled band medians (robust LOWESS) over the LTS inliers only, re-admission at a
     FIXED scale taken from the LTS kept set (an MM step for a non-parametric curve).
  3. Light field from patch votes, LTS over patches then biweight (an MM estimator over patches): a plane; a
     quadratic only when paper/mount boxes anchor it AND a held-out side agrees.
  4. Paper/mount boxes are light-only anchors (own intercept, no tone curve); unpainted boxes anchor m(L) at their
     tones.
Presence: departure d = |F - F_ref| compared at the camera's chroma resolution; shown where d > T,
  T = max(T0(L), 3 * sigma_n), sigma_n^2 = shift-difference noise (lag 12, by tone) + an edge variance with
  coefficients fitted from the residuals.  No term of T is a spread of the same pixels' departures.
The print's own variability S(L) is kept only for a footer note.  Evaluation prototype."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import cv2
import numpy as np

import visualiser_proto as V

E = np.array([[2, -1, -1], [0, 1, -1]], float)
E[0] /= np.sqrt(6)
E[1] /= np.sqrt(2)
LUM = np.array([0.2126, 0.7152, 0.0722])
LAB_PER_CHI = 47.5          # a*b* units per unit of chi at g(L) = 1 (a mid-grey's response to one channel's ratio)


@dataclass
class Opt2:
    space: str = "chi"        # 'chi' (log-chromaticity) or 'lab'
    T0: float = 0.04          # chi units (about a 4 % change in a channel ratio); presets 0.06 / 0.04 / 0.025
    k_noise: float = 3.0
    lts_h: float = 0.6
    lts_starts: int = 16
    span: float = 14.0
    sigma_c: float = 2.0      # px: compare at chroma resolution
    lag: int = 12
    quad_with_paper: bool = True
    deg_auto: int = 1         # light field degree without paper anchors (1 plane, 2 quadratic)
    gate_share: float = 0.3   # a band uses only the LTS inliers when they are at least this share of it
    misfit: bool = True       # add the LTS kept set's model error to the presence floor
    tiles: int = 6            # patch grid for the light votes
    seed: int = 0


@dataclass
class Ref2:
    m: np.ndarray             # (bands, 2) tone curve at V.CENTRES (photo)
    C: np.ndarray             # (k, 2) light field coefficients on basis phi
    deg: int                  # 1 plane, 2 quadratic
    c_paper: Optional[np.ndarray]
    sigma_fit: float
    noise: tuple              # (centres, var per axis)
    kJ2: float
    kG2: float
    S: np.ndarray             # (bands, 2, 2) the print's own variability (diagnostic only)
    support: np.ndarray
    misfit2: float = 0.0      # per-axis model-error variance from the LTS kept set (global)
    notes: List[str] = field(default_factory=list)


def features(rgb: np.ndarray, space: str, median_px: int = 5):
    L, ab = V.to_lab(rgb, median_px)
    lin = np.where(rgb <= 0.04045, rgb / 12.92, ((np.clip(rgb, 0.04045, None) + 0.055) / 1.055) ** 2.4).astype(np.float32)
    Y = lin @ LUM.astype(np.float32)
    if space == "lab":
        return L, ab, Y
    chi = np.log(np.maximum(lin, 1e-3)) @ E.T.astype(np.float32)
    chi = np.stack([cv2.medianBlur(np.ascontiguousarray(chi[..., k]), median_px) for k in (0, 1)], -1)
    return L, chi.astype(np.float32), Y


def g_cast(L, space):
    return V._g(L) if space == "lab" else np.ones_like(np.asarray(L, float))


def T0_of(L, opt: Opt2):
    return opt.T0 * (LAB_PER_CHI * V._g(L) if opt.space == "lab" else np.ones_like(np.asarray(L, float)))


def phi(xn, yn, deg):
    cols = [xn, yn] + ([xn * xn, xn * yn, yn * yn] if deg >= 2 else [])
    return np.stack(cols, -1)


def _lts(A, Fv, h, starts, rng, force=None, all_solutions=False):
    n = len(Fv)
    hn = max(int(h * n), A.shape[1] + 2)
    sols = []
    for _ in range(starts):
        sub = rng.choice(n, min(n, max(40, 4 * A.shape[1])), replace=False)
        beta = np.linalg.lstsq(A[sub], Fv[sub], rcond=None)[0]
        for _ in range(6):
            d = ((Fv - A @ beta) ** 2).sum(1)
            if force is not None:
                d[force] = -1.0
            keep = np.argpartition(d, hn - 1)[:hn]
            beta = np.linalg.lstsq(A[keep], Fv[keep], rcond=None)[0]
        d = ((Fv - A @ beta) ** 2).sum(1)
        obj = np.partition(d, hn - 1)[:hn].sum()
        sols.append((obj, beta, keep))
    sols.sort(key=lambda s: s[0])
    if all_solutions:
        return sols
    return sols[0][1], sols[0][2]


def shift_noise(r, L, ok, lag):
    """Per-axis noise variance by tone: half the covariance of differences of pixels `lag` apart (across and down),
    pairs on edges or outside the judgeable area left out, median-scaled (MNF's estimate; a wash cannot inflate it)."""
    ds, ls = [], []
    for dy, dx in ((0, lag), (lag, 0)):
        a = ok[: ok.shape[0] - dy, : ok.shape[1] - dx] & ok[dy:, dx:]
        d = r[: r.shape[0] - dy, : r.shape[1] - dx][a] - r[dy:, dx:][a]
        ll = 0.5 * (L[: L.shape[0] - dy, : L.shape[1] - dx][a] + L[dy:, dx:][a])
        ds.append(d)
        ls.append(ll)
    d = np.concatenate(ds).astype(np.float64)
    ll = np.concatenate(ls)
    edges = np.linspace(0, 100, 11)
    cen, var = [], []
    for i in range(10):
        m = (ll >= edges[i]) & (ll < edges[i + 1])
        if m.sum() < 200:
            continue
        q = (d[m] ** 2).sum(1)
        var.append(np.median(q) / 2.77 + 1e-10)          # |diff|^2 ~ 2 s^2 chi2_2: median 2.77 s^2 (s per axis)
        cen.append(float(np.median(ll[m])))
    if not cen:
        return np.array([50.0]), np.array([1e-6])
    return np.array(cen), np.array(var)


def fit(L, F, Y, valid, grad, opt: Opt2, picks=None, paper=None) -> Ref2:
    rng = np.random.default_rng(opt.seed)
    h, w = L.shape
    yy, xx = np.mgrid[0:h, 0:w]
    XN = (2 * xx / (w - 1) - 1).astype(np.float32)
    YN = (2 * yy / (h - 1) - 1).astype(np.float32)
    base = valid & (grad < np.quantile(grad[valid], 0.8))
    photo_mask = base if paper is None else base & ~paper
    idx = np.flatnonzero(photo_mask)
    if len(idx) > 200_000:
        idx = np.sort(rng.choice(idx, 200_000, replace=False))
    pidx = np.flatnonzero(base & picks) if picks is not None else np.zeros(0, int)
    qidx = np.flatnonzero(base & paper) if paper is not None else np.zeros(0, int)
    if len(qidx) > 40_000:
        qidx = np.sort(rng.choice(qidx, 40_000, replace=False))
    allidx = np.concatenate([idx, pidx, qidx])
    is_pick = np.r_[np.zeros(len(idx), bool), np.ones(len(pidx), bool), np.zeros(len(qidx), bool)]
    is_paper = np.r_[np.zeros(len(idx) + len(pidx), bool), np.ones(len(qidx), bool)]
    l = L.ravel()[allidx].astype(np.float64)
    v = F.reshape(-1, 2)[allidx].astype(np.float64)
    gl = g_cast(l, opt.space)[:, None]
    xn, yn = XN.ravel()[allidx].astype(np.float64), YN.ravel()[allidx].astype(np.float64)
    band = V._band_of(l)
    nb = len(V.CENTRES)
    notes = []
    # 1. LTS start, stiff model over the whole image (shadows out; picks and paper always kept)
    tn = (l - 50) / 50
    A0 = np.c_[np.ones_like(tn), tn, tn ** 2, gl[:, 0] * xn, gl[:, 0] * yn]
    if is_paper.any():
        A0[is_paper, :3] = 0.0
        A0 = np.c_[A0, is_paper.astype(float)]
    use = (l > 20) | is_pick | is_paper
    sols = _lts(A0[use], v[use], opt.lts_h, opt.lts_starts, rng, force=(is_pick | is_paper)[use], all_solutions=True)
    beta0, keep = sols[0][1], sols[0][2]
    # two readings? the best solution against the best one that keeps a substantially different set of pixels
    Ls = np.arange(20, 96, 1.0)
    tq = (Ls - 50) / 50
    curve_of = lambda b: b[0] + np.outer(tq, b[1]) + np.outer(tq ** 2, b[2])
    best_set = set(keep.tolist())
    for obj, b, k in sols[1:]:
        jac = len(best_set & set(k.tolist())) / len(best_set | set(k.tolist()))
        if jac < 0.8 and obj < 1.15 * sols[0][0]:
            diff = np.linalg.norm(curve_of(b) - curve_of(beta0), axis=1)
            far = diff > T0_of(Ls, opt)
            if far.any():
                lo, hi = Ls[far].min(), Ls[far].max()
                notes.append(f"the image reads two ways in the tones L* {lo:.0f}-{hi:.0f} (one colour or another there "
                             "is paint): box an unpainted area at those tones")
            break
    r0 = v - A0 @ beta0
    kept = np.zeros(len(l), bool)
    kept[np.flatnonzero(use)[keep]] = True
    q = -2 * np.log(1 - opt.lts_h)
    cons = 2.0 / (2 - q * (1 - opt.lts_h) / opt.lts_h)
    s2 = float(np.mean((r0[kept] ** 2).sum(1)) * cons / 2)              # per-axis variance, consistency-corrected
    sigma = np.sqrt(max(s2, 1e-12))
    inl = (np.linalg.norm(r0, axis=1) < 3 * sigma) | is_pick | is_paper
    # 2-3. flexible curve over inliers at the fixed scale, and the light field from patch votes
    C = np.zeros((2, 2))
    deg = 1
    c_paper = None
    TILES = opt.tiles
    tile = (np.minimum(((yy.ravel()[allidx]) * TILES) // h, TILES - 1) * TILES
            + np.minimum(((xx.ravel()[allidx]) * TILES) // w, TILES - 1)).astype(int)

    def curve(field_):
        res = v - field_
        med = np.zeros((nb, 2))
        sup = np.zeros(nb)
        photo = ~is_paper
        for b in range(nb):
            inb = (band == b) & photo
            a = inb & is_pick
            if a.sum() >= 30:
                med[b] = np.median(res[a], 0)
                sup[b] = max(a.sum(), 200)
                continue
            s = inb & inl
            if s.sum() >= 30 and s.sum() >= opt.gate_share * inb.sum():
                med[b] = np.median(res[s], 0)              # the stiff start describes this band: its inliers
                sup[b] = s.sum()
            elif inb.sum() >= 30:
                med[b] = np.median(res[inb], 0)            # it does not (e.g. deep shadows): the plain band median
                sup[b] = inb.sum()
        return V._lowess(V.CENTRES, med, np.minimum(sup / 200.0, 1.0), opt.span), sup

    def light(m, deg_, with_paper=True, hold=None):
        mp = np.stack([np.interp(l, V.CENTRES, m[:, c]) for c in range(2)], axis=1)
        qq = (v - mp) / gl
        casts, X, isp = [], [], []
        for t in range(TILES * TILES):
            s = inl & (tile == t) & ~is_paper
            if s.sum() >= 150:
                casts.append(np.median(qq[s], 0))
                X.append(phi(xn[s].mean(), yn[s].mean(), deg_))
                isp.append(0.0)
        if with_paper and is_paper.any():
            # paper patches: by tile, the paper's own colour (no tone curve), with its own intercept
            for t in range(TILES * TILES):
                s = is_paper & (tile == t)
                if hold is not None:
                    s &= ~hold
                if s.sum() >= 60:
                    casts.append(np.median(v[s] / gl[s], 0))
                    X.append(phi(xn[s].mean(), yn[s].mean(), deg_))
                    isp.append(1.0)
        if len(casts) < 9:
            return np.zeros((2 if deg_ == 1 else 5, 2)), None
        casts = np.asarray(casts)
        X = np.c_[np.ones(len(casts)), np.asarray(X), np.asarray(isp)] if np.any(isp) else \
            np.c_[np.ones(len(casts)), np.asarray(X)]
        rngp = np.random.default_rng(opt.seed + 7)
        bta, kp = _lts(X, casts, 0.6, 24, rngp)                       # LTS over patches
        rr = np.linalg.norm(casts - X @ bta, axis=1)
        sc = 1.4826 * np.median(rr[kp]) + 1e-9                       # scale fixed from the LTS kept patches
        for _ in range(6):                                           # biweight step at that fixed scale (MM)
            u = rr / (4.0 * sc)
            wt = np.where(u < 1, (1 - u ** 2) ** 2, 0.0)
            bta = np.linalg.solve(X.T @ (wt[:, None] * X) + 1e-9 * np.eye(X.shape[1]), X.T @ (wt[:, None] * casts))
            rr = np.linalg.norm(casts - X @ bta, axis=1)
        k = 2 if deg_ == 1 else 5
        Cn = bta[1:1 + k]
        cp = bta[-1] + bta[0] if np.any(isp) else None
        return Cn, cp

    def field_of(Cn, deg_):
        return gl * (phi(xn, yn, deg_) @ Cn)

    m, _ = curve(np.zeros_like(v))
    s_before = None
    for it in range(3):
        mp = np.stack([np.interp(l, V.CENTRES, m[:, c]) for c in range(2)], axis=1)
        res = v - mp
        s_now = float(np.sqrt(np.median((res[inl & ~is_paper] ** 2).sum(1)) / 1.386 / 1))
        s_before = s_now if s_before is None else s_before
        Cn, cp = light(m, opt.deg_auto, with_paper=paper is not None)
        m, _ = curve(field_of(Cn, opt.deg_auto))
        mp = np.stack([np.interp(l, V.CENTRES, m[:, c]) for c in range(2)], axis=1)
        res = v - mp - field_of(Cn, opt.deg_auto)
        inl = (np.linalg.norm(res, axis=1) < 3 * sigma) | is_pick | is_paper
    s_after = float(np.sqrt(np.median((res[inl & ~is_paper] ** 2).sum(1)) / 1.386))
    if paper is not None or s_after < 0.85 * s_before:
        C, deg, c_paper = Cn, opt.deg_auto, cp
        notes.append("a gentle colour gradient across the frame was taken out")
    # quadratic only with paper anchors and a held-out side that agrees
    if paper is not None and opt.quad_with_paper and is_paper.sum() > 500:
        hold = is_paper & (xn < -0.8)                                  # the left side held out
        Cq, cpq = light(m, 2, with_paper=True, hold=hold)
        if cpq is not None and hold.any():
            pred = gl[hold] * (phi(xn[hold], yn[hold], 2) @ Cq + cpq)
            miss = float(np.linalg.norm(np.median(v[hold] - pred, 0)))
            T0h = float(np.median(T0_of(l[hold], opt)))
            if miss < 0.5 * T0h:
                Cq, cpq = light(m, 2, with_paper=True)
                C, deg, c_paper = Cq, 2, cpq
                notes.append("the light was read from the paper margin")
            else:
                notes.append("the margin does not agree with itself across the frame: the light was read from the image")
    # final residuals; the print's own variability (for the footer only)
    m, sup = curve(field_of(C, deg))
    mp = np.stack([np.interp(l, V.CENTRES, m[:, c]) for c in range(2)], axis=1)
    res = v - mp - field_of(C, deg)
    inl = (np.linalg.norm(res, axis=1) < 3 * sigma) | is_pick
    S = np.tile(np.eye(2) * sigma ** 2, (nb, 1, 1))
    for b in range(nb):
        s = inl & (band == b) & ~is_paper
        if s.sum() >= 60:
            qd = res[s] - res[s].mean(0)
            S[b] = qd.T @ qd / (len(qd) - 1)
    support = np.bincount(band[inl & ~is_paper], minlength=nb).astype(float)
    return Ref2(m=m, C=C, deg=deg, c_paper=c_paper, sigma_fit=sigma, noise=(np.array([50.0]), np.array([1e-6])),
                kJ2=0.0, kG2=0.0, S=S, support=support, notes=notes, misfit2=float(sigma ** 2))


def reference_map(ref: Ref2, L, space, paper=None):
    h, w = L.shape
    yy, xx = np.mgrid[0:h, 0:w]
    xn = (2 * xx / (w - 1) - 1).astype(np.float32)
    yn = (2 * yy / (h - 1) - 1).astype(np.float32)
    m = np.stack([np.interp(L, V.CENTRES, ref.m[:, c]) for c in range(2)], -1)
    fld = g_cast(L, space)[..., None] * (phi(xn, yn, ref.deg) @ ref.C)
    out = m + fld
    if paper is not None and ref.c_paper is not None:
        out = np.where(paper[..., None], fld + g_cast(L, space)[..., None] * ref.c_paper, out)
    return out.astype(np.float32)


def presence(ref: Ref2, L, F, Y, valid, opt: Opt2, paper=None):
    """Departure at chroma resolution; noise floor from shift differences; edge variance fitted from residuals."""
    refF = reference_map(ref, L, opt.space, paper)
    bl = lambda a: np.stack([cv2.GaussianBlur(np.ascontiguousarray(a[..., c]), (0, 0), opt.sigma_c) for c in range(2)], -1)
    Fb, Rb = bl(F), bl(refF)
    r = Fb - Rb
    lY = cv2.GaussianBlur(np.log(np.maximum(Y, 1e-3)).astype(np.float32), (0, 0), opt.sigma_c)
    gy, gx = np.gradient(lY)
    G2 = gx * gx + gy * gy
    J2 = np.zeros_like(G2)
    for c in range(2):
        jy, jx = np.gradient(Rb[..., c])
        J2 += jx * jx + jy * jy
    J2 /= 2.0
    calm = valid & (G2 < np.quantile(G2[valid], 0.8))
    cen, var = shift_noise(r, L, calm, opt.lag)
    nvar = np.interp(L, cen, var)
    ref.misfit2 = max(float(ref.sigma_fit ** 2 - np.median(var)), 0.0) if opt.misfit else 0.0
    # one edge term kG2 * G2 (G = |grad ln Y| at chroma resolution), kG2 from binned medians over the edgy half
    q = (r ** 2).sum(-1) / 2.0
    sel = valid & (G2 > np.quantile(G2[valid], 0.5))
    xs, ys = [], []
    gq = np.quantile(G2[sel], np.linspace(0, 1, 11))
    for i in range(10):
        mm = sel & (G2 >= gq[i]) & (G2 <= gq[i + 1])
        if mm.sum() > 100:
            xs.append(np.median(G2[mm]))
            ys.append(np.median(q[mm]) / 0.693 - np.median(nvar[mm]) - ref.misfit2)
    kJ2, kG2 = 0.0, 0.0
    if len(xs) >= 4:
        xs, ys = np.asarray(xs), np.asarray(ys)
        kG2 = max(float(np.sum(xs * ys) / np.sum(xs * xs)), 0.0)
    ref.noise, ref.kJ2, ref.kG2 = (cen, var), kJ2, kG2
    sd = np.sqrt(np.maximum(nvar + ref.misfit2 + kG2 * G2, 0))
    T = np.maximum(T0_of(L, opt), opt.k_noise * sd)
    d = np.linalg.norm(r, axis=-1)
    qn = cv2.medianBlur((d / T).astype(np.float32), 3)
    a = np.clip((qn - 0.5) / 1.0, 0, 1)
    alpha = np.where(valid, a * a * (3 - 2 * a), 0).astype(np.float32)      # 0.5 at d = T, 1 at d = 1.5 T
    return {"r": r, "d": d, "T": T, "q": qn, "alpha": alpha, "ref": refF}


def run2(rgb8, opt: Opt2 = Opt2(), box=None, picks=None, paper=None):
    rgb = rgb8.astype(np.float32) / 255.0
    L, F, Y = features(rgb, opt.space)
    mk = V.masks(rgb, L, box)
    lY = cv2.GaussianBlur(np.log(np.maximum(Y, 1e-3)).astype(np.float32), (0, 0), opt.sigma_c)
    gy, gx = np.gradient(lY)
    grad = np.hypot(gx, gy)
    ref = fit(L, F, Y, mk["valid"], grad, opt, picks=picks, paper=paper)
    pr = presence(ref, L, F, Y, mk["valid"], opt, paper)
    return {"L": L, "F": F, "Y": Y, "masks": mk, "ref": ref, "pr": pr}
