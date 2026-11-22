import json, numpy as np
import synth, pipelines as PL, evaluate as E
caps = {s: synth.scenario(s) for s in ("control", "phone", "phone_mixed", "scan", "toned", "phone_glare")}
out = {}
for space, floors in (("lab", (0.3, 0.4, 0.5)), ("logc", (0.7, 1.0))):
    for fl in floors:
        row = {}
        for s, (img, t) in caps.items():
            res = PL.run_proposed(img, space=space, floor=fl)
            ev = E.evaluate(res, t)
            row[s] = {"auc": ev["auc"], "FA": ev["false_shown_all"],
                      "hits": {k.split(' (')[0]: round(v["shown"], 2) for k, v in ev["objects"].items()}}
        out[f"{space}_{fl}"] = row
        print(space, fl, " | ".join(f"{s}: FA={r['FA']:.3f} auc={r['auc']:.3f} " +
              (" ".join(f"{k[:5]}={v}" for k, v in r['hits'].items()) if s != 'control' else '') for s, r in row.items()), flush=True)
json.dump(out, open("floor_sweep.json", "w"), indent=1)
