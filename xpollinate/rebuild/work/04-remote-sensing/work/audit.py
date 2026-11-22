"""The proposal's self-checks, in words (no numbers reach the picture): what a viewer is told when the reference
for 'unpainted' may be wrong.

1. Tones where most of the photograph is far from the reference: either paint covers most of that tone, or the
   reference is wrong there.  The tool cannot tell which; the reference panel shows which colour it took.
2. The margin (when given) is not flat after the light model: the light model does not describe this capture.
3. The reference itself is strongly coloured somewhere: it may have taken paint for the photograph's own tone.
4. Little of the frame was usable (glare, clipping, near black).
"""
from __future__ import annotations

import numpy as np

import methods as M


def audit(p: dict, res: dict, margin: np.ndarray | None = None, picks: np.ndarray | None = None,
          far: float = 3.0, share: float = 0.35) -> dict:
    bg = res["bg"]
    j = p["judge"]
    calm = M.edge_strength(p) < np.quantile(M.edge_strength(p)[j], 0.8)
    z = res["S"]
    logy = bg._logy(p["L"])
    lo, hi = np.percentile(logy[j], [1, 99])
    edges = np.linspace(lo, hi, 11)
    flagged = []
    covered_by_picks = []
    for i in range(10):
        m = j & calm & (logy >= edges[i]) & (logy < edges[i + 1])
        if margin is not None:
            m &= ~margin
        if m.sum() < 0.02 * j.sum():
            continue
        s = float((z[m] > far).mean())
        Lr = (116 * np.exp(edges[i] / 3) - 16, 116 * np.exp(edges[i + 1] / 3) - 16)
        if s > share:
            picked = picks is not None and (picks & m).sum() > 400
            flagged.append((round(Lr[0]), round(Lr[1]), round(s, 2), picked))
    words = []
    open_flags = [f for f in flagged if not f[3]]
    if open_flags:
        rng = f"L* {open_flags[0][0]}-{open_flags[-1][1]}"
        words.append(f"At some tones ({rng}) most of the photograph differs from the reference: either it is painted "
                     "there, or the reference is wrong at those tones. The reference panel shows the colour taken as "
                     "unpainted; box an unpainted area of that tone to settle it.")
    margin_flag = None
    if margin is not None and (margin & j).sum() > 500:
        mm = margin & j & calm
        margin_flag = float((z[mm] > far).mean())
        if margin_flag > 0.10:
            words.append("The paper margin is not even after the light model: the light across this capture is more "
                         "uneven than the model allows. Expect soft colour gradients that are light, not paint.")
    # the reference's own colourfulness, in the same units as the boost
    ref = res["ref"][j]
    spread = np.linalg.norm(ref - np.median(ref, 0), axis=1)
    ref_flag = float(np.percentile(spread, 95))
    if ref_flag > 0.25:
        words.append("The reference changes colour strongly across tones or across the frame: check that the "
                     "reference panel shows only the photograph's own tone and the light, not painted objects.")
    usable = float(j[p["inbox"]].mean())
    if usable < 0.6:
        words.append("Much of the frame could not be judged (glare, clipping or near black): those parts are "
                     "hatched, not unpainted.")
    return dict(tones_flagged=flagged, margin_far_share=margin_flag, ref_spread95=ref_flag, usable=usable,
                words=words)


def two_colours(p: dict, res: dict, margin: np.ndarray | None = None, picks: np.ndarray | None = None,
                min_weight: float = 0.15, min_sep: float = 4.0, seed: int = 0) -> dict:
    """At each tone, do the photograph's colours form two groups?  An unpainted monochrome print has one colour per
    tone (after the light), so two well-separated groups mean paint at that tone, or a reference that is wrong there.
    It works on the colours themselves (log-chromaticity minus the light field), so it still fires when the
    reference has taken the paint in and the residuals are small.  Separation in units of the groups' own spread."""
    from sklearn.mixture import GaussianMixture
    bg = res["bg"]
    j = p["judge"]
    G = M.edge_strength(p)
    calm = j & (G < np.quantile(G[j], 0.7))
    if margin is not None:
        calm &= ~margin
    feat = (p["chi"] - res["g"]).reshape(-1, 2)          # the light removed, the tone curve not
    logy = bg._logy(p["L"]).ravel()
    lo, hi = np.percentile(logy[calm.ravel()], [2, 99])
    edges = np.linspace(lo, hi, 9)
    rng = np.random.default_rng(seed)
    flags = []
    for i in range(8):
        m = np.flatnonzero(calm.ravel() & (logy >= edges[i]) & (logy < edges[i + 1]))
        if len(m) < 0.03 * calm.sum():
            continue
        x = feat[rng.choice(m, min(6000, len(m)), replace=False)].astype(np.float64)
        g1 = GaussianMixture(1, random_state=seed).fit(x)
        g2 = GaussianMixture(2, random_state=seed, n_init=2).fit(x)
        w = g2.weights_
        d = g2.means_[0] - g2.means_[1]
        S = (g2.covariances_[0] + g2.covariances_[1]) / 2
        sep = float(np.sqrt(d @ np.linalg.solve(S, d)))
        better = g1.bic(x) - g2.bic(x) > 0.02 * len(x)
        if better and w.min() >= min_weight and sep >= min_sep:
            Lr = (round(116 * np.exp(edges[i] / 3) - 16), round(116 * np.exp(edges[i + 1] / 3) - 16))
            picked = picks is not None and (picks.ravel()[m]).sum() > 400
            flags.append(dict(L=Lr, minor_weight=round(float(w.min()), 2), sep=round(sep, 1), picked=picked))
    return dict(flags=flags)
