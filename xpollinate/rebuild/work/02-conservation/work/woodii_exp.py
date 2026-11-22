"""Woodii's Chroma mode (commit 5b1757d) on untinted prints that break its one-straight-silver-axis assumption.

Input as it intended: linear counts from an even copy-stand light, shot and read noise, a base pick on the margin and
an untinted pick over a broad area of image, threshold k = 4 noise sd.  Its own tests used an exact single axis.
"""
import json

import numpy as np

import methods as M
import sim
from bench import to_px


def flagged(counts, po, k=4.0):
    base = to_px(["margin"], po)
    unt = to_px([(30, 400, 480, 500), (100, 10, 300, 60)], po)        # broad untinted areas: suit, backdrop and hair
    flag, res = M.woodii(counts, [list(b) for b in unt], [list(b) for b in base], k=k)
    show = res["show"]
    image = np.zeros(show.shape, bool)
    s = po.size
    b = int(round(po.border * s))
    image[b:b + s, b:b + s] = True
    return float(flag[show & image].mean()), res


def main():
    out = {}
    cases = {
        "neutral (one exact axis, as in its tests)": dict(tone="neutral"),
        "warm-tone paper (tone changes with density)": dict(tone="warm"),
        "sulfide-toned, strongest in highlights": dict(tone="sepia"),
        "neutral, yellowed toward the edges, foxed": dict(tone="neutral", yellowing=1.0, foxing=25),
    }
    for name, kw in cases.items():
        po = sim.PrintOpts(**kw)
        refl, gray, truth = sim.make_print(po)
        row = {}
        for flare in (0.0, 0.005):
            counts = sim.linear_capture(refl + flare)
            for k in (4.0, 8.0, 16.0):
                f, res = flagged(counts, po, k)
                row[f"flare {flare:g}, k={k:g}"] = round(f, 4)
            row[f"flare {flare:g}: noise sd at paper (OD)"] = res["record"]["noise"]["sigma0_od"]
        out[name] = row
        print(name, row, flush=True)
    # and a painted print, to show what the same threshold finds when the model holds
    po = sim.PrintOpts(tone="neutral", paint="portrait")
    refl, gray, truth = sim.make_print(po)
    counts = sim.linear_capture(refl)
    f, res = flagged(counts, po, 4.0)
    hits = {kk: round(float(res["flag"][m & res["show"]].mean()), 3) for kk, m in truth.items() if kk.startswith("paint_")}
    out["neutral print, portrait media, k=4: share of each medium flagged"] = hits
    print(hits)
    with open("bench_out/woodii.json", "w") as fh:
        json.dump(out, fh, indent=1)


if __name__ == "__main__":
    main()
