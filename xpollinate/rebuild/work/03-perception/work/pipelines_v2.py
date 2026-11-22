"""Design v2, after contact with the conservation report (peer-report.md).

Changes against pipelines.run_proposed (v1), each switchable so the bench can test it alone:

* votes=True     the tone is voted by places: each tile of a 10 x 10 grid gives, at each 2 L* band where it has
                 enough pixels, one vote, its median (a*, b*) (the peer's mechanism).  v1's model (penalised curve in
                 L*, cast terms scaled by (L* + 16)/116 with a lightness-dependent tilt) is then fitted to the votes,
                 not to pixels, by the same Tukey IRLS: a place counts once per tone, whatever its area.
* yardstick="p90" each tone band's and scale's yardstick is the 90th percentile of the departure over judgeable,
                 low-gradient pixels, trimmed iteratively at twice itself (the peer's yardstick), instead of v1's
                 median-based Rayleigh spread; the departure map ramps from 1 to 2 yardsticks (normal preset).
* anchors        picks pull the tone only by what the automatic reference cannot explain: per tone, the picks'
                 median departure from the automatic expectation, smoothed across tones, shrunk by one yardstick,
                 faded 6 L* beyond the tones the picks reach (the peer's rule).  v1 weighted picks x20 in the fit.
v1's edge-tolerant departure, floor, monotone scales, gated coarse scales and 5 x 5 median are kept.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter, median_filter, sobel

import pipelines as PL


def tile_votes(Li, ab, valid, grid=10, band=2.0, min_px=None):
    """One vote per (tile, lightness band): the median a*, b* (and the median L*, x, y) of the tile's usable pixels in
    that band, when there are enough of them (25 at 1.3 MP, scaled with the frame)."""
    h, w = Li.shape
    if min_px is None:
        min_px = max(10, int(round(25 * h * w / 1.3e6)))
    ty = (np.arange(h) * grid) // h
    tx = (np.arange(w) * grid) // w
    tile = (ty[:, None] * grid + tx[None, :]).astype(np.int64)
    nb = int(np.ceil(100 / band))
    b = np.clip((Li / band).astype(np.int64), 0, nb - 1)
    key = (tile * nb + b)[valid]
    yy, xx = np.nonzero(valid)
    order = np.argsort(key, kind="stable")
    k = key[order]
    starts = np.r_[0, np.flatnonzero(np.diff(k)) + 1]
    ends = np.r_[starts[1:], len(k)]
    A = ab[valid][order]
    Ls = Li[valid][order]
    Y = yy[order].astype(np.float32)
    X = xx[order].astype(np.float32)
    out = []
    for s, e in zip(starts, ends):
        if e - s < min_px:
            continue
        out.append((np.median(Ls[s:e]), np.median(X[s:e]), np.median(Y[s:e]), *np.median(A[s:e], axis=0), e - s,
                    k[s] // nb))
    v = np.array(out, np.float32)
    return {"L": v[:, 0], "x": 2 * v[:, 1] / (w - 1) - 1, "y": 2 * v[:, 2] / (h - 1) - 1, "ab": v[:, 3:5],
            "n": v[:, 5], "tile": v[:, 6].astype(int)}


def fit_votes(L, ab, valid, spatial=3, knot_step=4.0, lam=0.05, iters=10, c=3.5, l_index_sigma=1.5,
              cast_scaled=True, floor=0.4, auto_position=True, cast_min=4.0):
    """v1's reference model fitted to the votes of places (Tukey IRLS on votes, each vote weight 1)."""
    h, w = L.shape
    Li = gaussian_filter(L, l_index_sigma) if l_index_sigma else L
    votes = tile_votes(Li, ab, valid)
    knots = np.arange(0.0, 100.0 + knot_step, knot_step, dtype=np.float32)
    edges = knots
    K = len(knots)

    def fit(sp):
        X = PL.design(votes["L"], votes["x"], votes["y"], knots, sp, cast_scaled)
        Y = votes["ab"]
        D = np.diff(np.eye(K, dtype=np.float32), 2, axis=0)
        P = np.zeros((X.shape[1], X.shape[1]), np.float32)
        P[:K, :K] = D.T @ D
        lam_eff = lam * len(Y) / K
        nbv = K - 1
        bidx = np.clip(np.searchsorted(edges, votes["L"], side="right") - 1, 0, nbv - 1)
        wts = np.ones(len(Y), np.float32)
        # start: per-band median of votes
        med = np.full((K, 2), np.nan, np.float32)
        for kk in range(K):
            sel = np.abs(votes["L"] - knots[kk]) <= knot_step
            if sel.sum() >= 3:
                med[kk] = np.median(Y[sel], axis=0)
        ok = np.isfinite(med[:, 0])
        for cc in range(2):
            med[:, cc] = np.interp(knots, knots[ok], med[ok, cc])
        pred = PL.hat_basis(votes["L"], knots) @ med
        beta = None
        for it in range(iters):
            r = Y - pred
            s, _ = PL.band_spread(votes["L"], r, np.ones(len(Y)) if it == 0 else wts, edges, min_px=3, floor=0.1)
            u = np.linalg.norm(r, axis=1) / (c * s[bidx])
            wts = np.where(u < 1, (1 - u * u) ** 2, 0.0).astype(np.float32)
            WX = X * wts[:, None]
            A = X.T @ WX + lam_eff * P
            beta = np.linalg.solve(A.astype(np.float64), (WX.T @ Y).astype(np.float64)).astype(np.float32)
            pred = X @ beta
        return beta

    beta = fit(spatial)
    cast = float(np.abs(beta[K:]).max()) if spatial else 0.0
    if auto_position and spatial and cast < cast_min:
        spatial, beta, cast = 0, fit(0), 0.0
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    xn, yn = 2 * xx / (w - 1) - 1, 2 * yy / (h - 1) - 1
    ref = PL.ref_at(Li, xn, yn, beta, knots, spatial, cast_scaled)
    return {"beta": beta, "knots": knots, "edges": edges, "spatial": spatial, "cast": cast, "Li": Li, "xn": xn,
            "yn": yn, "ref": ref, "votes": votes, "cast_scaled": cast_scaled}


def fit_pixels(L, ab, valid, spatial=3, cast_scaled=True, floor=0.4, auto_position=True, cast_min=4.0, picks=None):
    """v1's pixel fit, repackaged (picks, if given, are v1's x20 weights)."""
    f = PL.fit_reference(L, ab, valid, picks=picks, spatial=spatial, cast_scaled=cast_scaled, floor=floor,
                         tolerant=False)
    f["cast"] = float(np.abs(f["beta"][len(f["knots"]):]).max()) if spatial else 0.0
    sp = spatial
    if auto_position and spatial and f["cast"] < cast_min:
        f = PL.fit_reference(L, ab, valid, picks=picks, spatial=0, cast_scaled=cast_scaled, floor=floor,
                             tolerant=False)
        f["cast"], sp = 0.0, 0
    return {"beta": f["beta"], "knots": f["knots"], "edges": f["edges"], "spatial": sp, "cast": f["cast"],
            "Li": f["Lidx"], "xn": f["xn"], "yn": f["yn"], "ref": f["ref"], "cast_scaled": cast_scaled}


def band_yardstick(Lb, d, mask, edges, kind="p90", floor=0.4, min_px=150, trim=2.0, rounds=3):
    """Per lightness band, the yardstick of the departure length ``d``: 'p90' the 90th percentile over ``mask``
    pixels, trimmed iteratively at twice itself; 'rayleigh' v1's median |r| / 1.1774.  Floored, smoothed."""
    nb = len(edges) - 1
    idx = np.clip(np.searchsorted(edges, Lb, side="right") - 1, 0, nb - 1)
    s = np.full(nb, np.nan, np.float32)
    for b in range(nb):
        v = d[(idx == b) & mask]
        if v.size < min_px:
            continue
        if kind == "p90":
            q = np.percentile(v, 90)
            for _ in range(rounds):
                vv = v[v <= trim * q]
                if vv.size < min_px:
                    break
                q = np.percentile(vv, 90)
            s[b] = q
        else:
            s[b] = np.median(v) / 1.1774
    ok = np.isfinite(s)
    if not ok.any():
        return np.full(nb, 1.0, np.float32)
    x = np.arange(nb)
    s = np.interp(x, x[ok], s[ok])
    return np.maximum(median_filter(s, 3, mode="nearest"), floor).astype(np.float32)


def anchor_correction(fit, L, ab, valid, picks, yard_fine, smooth_L=8.0, fade_L=6.0, min_px=100):
    """Picks as anchors: per 2 L* band where the picks have enough pixels, their median departure from the automatic
    expectation; smoothed across tones; shrunk by one fine yardstick (a pick moves the tone only by what the
    automatic reference cannot explain); faded beyond the tones the picks reach.  Returns c(L) correction on knots."""
    knots, edges = fit["knots"], fit["edges"]
    Li = fit["Li"]
    sel = picks & valid
    centres = np.arange(1.0, 100.0, 2.0)
    d = np.full((len(centres), 2), np.nan, np.float32)
    r = ab - fit["ref"]
    for i, cL in enumerate(centres):
        m = sel & (np.abs(Li - cL) <= 1.0)
        if m.sum() >= min_px:
            d[i] = np.median(r[m], axis=0)
    have = np.isfinite(d[:, 0])
    if not have.any():
        return None
    # smooth across tones (Gaussian in L*, over the bands that have votes)
    sm = np.zeros_like(d)
    for i, cL in enumerate(centres):
        wgt = np.exp(-0.5 * ((centres[have] - cL) / smooth_L) ** 2)
        sm[i] = (wgt[:, None] * d[have]).sum(0) / max(wgt.sum(), 1e-6)
    # shrink by one yardstick at that tone
    nb = len(edges) - 1
    bi = np.clip(np.searchsorted(edges, centres, side="right") - 1, 0, nb - 1)
    n = np.linalg.norm(sm, axis=1)
    shrink = np.maximum(0, 1 - yard_fine[bi] / np.maximum(n, 1e-6))
    sm = sm * shrink[:, None]
    # fade beyond the reached tones
    reach = centres[have]
    dist = np.where(centres < reach.min(), reach.min() - centres, np.where(centres > reach.max(), centres - reach.max(), 0))
    # interior gaps: distance to the nearest band with picks
    gap = np.array([np.min(np.abs(reach - cL)) for cL in centres])
    dist = np.maximum(dist, np.maximum(gap - 2.0, 0))
    fade = np.clip(1 - dist / fade_L, 0, 1)
    sm = sm * fade[:, None]
    corr = np.stack([np.interp(knots, centres, sm[:, i]) for i in range(2)], -1)
    return corr, fade


def run_v2(img8, votes=True, yardstick="p90", picks=None, anchors=True, scales=(2.0, 6.0, 18.0), preset="normal",
           floor=None, gated=True, median=5, ramp=None):
    lab = PL.lab_of(img8)
    L = lab[..., 0]
    ab = PL.smooth_ab(lab, 5)
    out = PL.leave_out(img8, L)
    valid = ~out
    if floor is None:
        floor = 0.6 if yardstick == "p90" else 0.4
    if votes:
        fit = fit_votes(L, ab, valid)
    else:
        fit = fit_pixels(L, ab, valid, picks=None if anchors else picks)
    knots, edges, beta = fit["knots"], fit["edges"], fit["beta"]
    nb = len(edges) - 1
    Li = fit["Li"]
    band = np.clip(np.searchsorted(edges, Li, side="right") - 1, 0, nb - 1)
    # low-gradient pixels for the yardstick
    gm = np.hypot(sobel(L, 0), sobel(L, 1))
    lowgrad = valid & (gm <= np.percentile(gm[valid], 85))
    r = PL.tolerant_residual(L, ab, fit["xn"], fit["yn"], beta, knots, fit["spatial"], fit["cast_scaled"], Lsmooth=Li)
    corr = None
    dropped = []
    if picks is not None and anchors:
        # a pick moves the tone only by what the capture's own per-pixel scatter cannot explain: its 90th percentile
        y0 = band_yardstick(Li.ravel(), np.linalg.norm(r, axis=-1).ravel(), (lowgrad).ravel(), edges, "p90", 0.6)
        got = anchor_correction_hard(fit, L, ab, valid, picks, y0, corroborate=(anchors == "corroborated")) \
            if anchors in ("hard", "corroborated") else anchor_correction(fit, L, ab, valid, picks, y0)
        if got is not None:
            corr, fade = got[0], got[1]
            dropped = got[2] if len(got) > 2 else []
            beta = beta.copy()
            beta[:len(knots)] += corr
            fit["beta"] = beta
            fit["ref"] = PL.ref_at(Li, fit["xn"], fit["yn"], beta, knots, fit["spatial"], fit["cast_scaled"])
            r = PL.tolerant_residual(L, ab, fit["xn"], fit["yn"], beta, knots, fit["spatial"], fit["cast_scaled"],
                                     Lsmooth=Li)
    # yardsticks per scale, from judgeable low-gradient pixels (p90) or v1's way
    ms = []
    rv = r * valid[..., None]
    wv = valid.astype(np.float32)
    for s in scales:
        if s > 0:
            ws = gaussian_filter(wv, s)
            rs = np.stack([gaussian_filter(rv[..., i], s) for i in range(2)], -1) / np.maximum(ws, 1e-3)[..., None]
        else:
            rs = r
        dl = np.linalg.norm(rs, axis=-1)
        y = band_yardstick(Li.ravel(), dl.ravel(), lowgrad.ravel(), edges, yardstick, floor)
        ms.append({"sigma": s, "r": rs.astype(np.float32), "d": dl, "spread": y})
    for k in range(len(ms) - 2, -1, -1):               # finer scales never narrower than coarser ones
        ms[k]["spread"] = np.maximum(ms[k]["spread"], ms[k + 1]["spread"])
    for d_ in ms:
        m = d_["d"] / d_["spread"][band]
        m[~valid] = 0
        d_["m"] = m.astype(np.float32)
    lo, hi = {"p90": {"normal": (1.0, 2.0), "low": (1.25, 2.5), "high": (0.85, 1.7)},
              "rayleigh": {"normal": (3.0, 5.5), "low": (3.5, 6.5), "high": (2.6, 4.8)}}[yardstick][preset]
    if ramp is not None:
        lo, hi = ramp
    gate = (0.35, 0.8) if yardstick == "p90" else (0.75, 1.75)
    if gated:
        presence, score, direction, stack = PL.presence_from_scales(ms, band, valid, lo, hi, median, gate=gate)
    else:
        stack = np.stack([PL.smoothstep(d_["m"], lo, hi) for d_ in ms], 0)
        presence = stack.max(0) * valid
        score = np.max(np.stack([d_["m"] for d_ in ms], 0), 0)
        direction = ms[0]["r"]
    supported = np.bincount(band[valid].ravel(), minlength=nb) >= 0.002 * valid.sum()
    unsupported = ~supported[band] & valid
    fitd = {"ref": fit["ref"], "resid": r, "knots": knots, "edges": edges, "beta": fit["beta"], "band": band,
            "Lidx": Li, "spatial": fit["spatial"], "cast": fit["cast"], "cast_scaled": fit["cast_scaled"],
            "xn": fit["xn"], "yn": fit["yn"], "corr": corr, "votes": fit.get("votes"), "dropped": dropped}
    return {"score": score.astype(np.float32), "opacity": presence.astype(np.float32), "valid": valid, "fit": fitd,
            "ms": ms, "lab": lab, "ab": ab, "L": L, "direction": direction, "leftout": out, "unsupported": unsupported,
            "space": "lab", "stack": stack, "yardstick": yardstick, "lo_hi": (lo, hi)}


def anchor_correction_hard(fit, L, ab, valid, picks, scatter, fade_L=6.0, min_px=100, smooth_L=3.0,
                           corroborate=False):
    """Picks as anchors, v2: each pick (a connected box) gives, per 2 L* band where it has enough pixels, its median
    departure from the automatic expectation.  A pick that disagrees with the other picks at the same tones by more
    than the per-pixel scatter is dropped (leave-one-pick-out) and reported.  Where the remaining picks' median
    departure exceeds the scatter, the tone moves by all of it; within the scatter, not at all (a thin wash under a
    pick cannot move the tone).  Lightly smoothed, faded 6 L* beyond the tones the picks reach."""
    from scipy.ndimage import label
    knots, edges = fit["knots"], fit["edges"]
    Li = fit["Li"]
    lab_, n = label(picks & valid)
    centres = np.arange(1.0, 100.0, 2.0)
    r = ab - fit["ref"]
    per = np.full((n, len(centres), 2), np.nan, np.float32)
    for i in range(n):
        m = lab_ == i + 1
        for j, cL in enumerate(centres):
            mm = m & (np.abs(Li - cL) <= 1.0)
            if mm.sum() >= min_px:
                per[i, j] = np.median(r[mm], axis=0)
    nb = len(edges) - 1
    bi = np.clip(np.searchsorted(edges, centres, side="right") - 1, 0, nb - 1)
    tol = scatter[bi]
    dropped = []
    for i in range(n):
        others = np.delete(per, i, axis=0)
        cmp_ = 0
        bad = 0
        for j in range(len(centres)):
            if np.isnan(per[i, j, 0]) or n < 3:
                continue
            o = others[:, j]
            o = o[np.isfinite(o[:, 0])]
            if len(o) < 2:
                continue
            cmp_ += 1
            if np.linalg.norm(per[i, j] - np.median(o, axis=0)) > tol[j]:
                bad += 1
        if cmp_ and bad / cmp_ > 0.5:
            dropped.append(i + 1)
    keep = [i for i in range(n) if i + 1 not in dropped]
    if not keep:
        return None
    d = np.full((len(centres), 2), np.nan, np.float32)
    for j in range(len(centres)):
        v = per[keep, j]
        v = v[np.isfinite(v[:, 0])]
        if len(v):
            d[j] = np.median(v, axis=0)
    have = np.isfinite(d[:, 0])
    if not have.any():
        return None
    nrm = np.linalg.norm(np.nan_to_num(d), axis=1)
    if corroborate:
        # below the per-pixel scatter, a correction stands only if picks at two or more places agree on it
        # (the tone is everywhere, a wash is local); above it, any pick that survived the cross-check counts
        nagree = np.zeros(len(centres), bool)
        for j in range(len(centres)):
            v = per[keep, j]
            v = v[np.isfinite(v[:, 0])]
            if len(v) >= 2:
                spread_ = max(np.linalg.norm(a - b) for a in v for b in v)
                nagree[j] = spread_ <= tol[j]
        accept = have & ((nrm > tol) | nagree)
    else:
        accept = have & (nrm > tol)
    d = np.where(accept[:, None], np.nan_to_num(d), 0.0)
    sm = np.zeros_like(d)
    for j, cL in enumerate(centres):
        wgt = np.exp(-0.5 * ((centres[have] - cL) / smooth_L) ** 2)
        sm[j] = (wgt[:, None] * d[have]).sum(0) / max(wgt.sum(), 1e-6)
    reach = centres[have]
    gap = np.array([np.min(np.abs(reach - cL)) for cL in centres])
    fade = np.clip(1 - np.maximum(gap - 2.0, 0) / fade_L, 0, 1)
    sm = sm * fade[:, None]
    corr = np.stack([np.interp(knots, centres, sm[:, i]) for i in range(2)], -1)
    return corr, fade, dropped
