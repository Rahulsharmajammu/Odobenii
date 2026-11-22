import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import synth as S, methods as M, bench as B
sel = ["N2", "N3", "N4", "P1", "P4", "P6"]
fig, axes = plt.subplots(2, len(sel), figsize=(4*len(sel), 7), sharex=True)
for j, (name, recipe, tone, paper, capd, extra) in enumerate([c for c in B.CASES if c[0].split()[0] in sel]):
    ci = [c[0] for c in B.CASES].index(name)
    cap = S.Capture(seed=10+ci, **capd)
    case = S.make_case(name, recipe, tone, paper, cap, seed=ci, **extra)
    pt = M.prep(case.twin); p = M.prep(case.rgb)
    inprint = ~case.scene.mount
    use_t = pt.usable & inprint
    Lg = np.arange(10, 98, 2.0)
    idx = np.clip((pt.L/2).astype(int), 0, 49)
    ta = [np.median(pt.a[use_t & (idx==k)]) if (use_t & (idx==k)).sum()>100 else np.nan for k in (Lg/2).astype(int)]
    tb = [np.median(pt.b[use_t & (idx==k)]) if (use_t & (idx==k)).sum()>100 else np.nan for k in (Lg/2).astype(int)]
    res = {"M2 (box)": M.m2_todo(p, name="M2"), "M3 (box)": M.m3_proposed(p, mask=inprint, diagnostics=False),
           "M3 line (box)": M.m3_proposed(p, mask=inprint, deg=1, diagnostics=False)}
    # M2 with box: emulate by masking usable
    import copy
    pb = copy.copy(p); pb.usable = p.usable & inprint
    res["M2 (box)"] = M.m2_todo(pb)
    for i, (comp, tv) in enumerate((("a*", ta), ("b*", tb))):
        ax = axes[i, j]
        ax.plot(Lg, tv, "k-", lw=3, label="true unpainted (twin)")
        for k, r in res.items():
            ra, rb = r.ref_fn(Lg)
            ax.plot(Lg, ra if i == 0 else rb, label=k)
        # scatter a sample of the capture
        sm = np.random.default_rng(0).choice(np.flatnonzero(p.usable & inprint), 4000, replace=False)
        ax.scatter(p.L.ravel()[sm], (p.a if i==0 else p.b).ravel()[sm], s=1, c="0.6", alpha=0.4)
        ax.set_title(f"{name[:30]}\n{comp}", fontsize=8)
        if j == 0 and i == 0: ax.legend(fontsize=6)
plt.tight_layout(); plt.savefig("img/tone_curves.png", dpi=80)
print("ok")
