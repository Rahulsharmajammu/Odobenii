"""Markdown tables for the report from results_all.json (and results_final.json for the final defaults)."""
import json, sys
R = json.load(open("results_all.json"))
F = json.load(open("results_final.json")) if len(sys.argv) > 1 else {}
scen = ["scan", "phone", "phone_mixed", "phone_glare", "toned", "majority", "control"]
names = {"scan": "scan (even light, lossless)", "phone": "phone (even warm light)", "phone_mixed": "phone, mixed light",
         "phone_glare": "phone, glare", "toned": "phone, purple-toned print", "majority": "phone, backdrop mostly painted",
         "control": "phone, mixed light, UNPAINTED"}
pipes = ["v412_raw", "v412_lrc", "todo", "proposed"]
def get(s, p):
    if p == "proposed" and F:
        return F[s]["proposed"]
    return R[s][p]
print("| capture | " + " | ".join(pipes) + " |")
print("|---|" + "---|" * len(pipes))
for s in scen:
    cells = []
    for p in pipes:
        r = get(s, p)
        auc = r["auc"]
        auc_s = "-" if auc != auc else f"{auc:.2f}"
        cells.append(f"{auc_s} / {100 * r['false_shown_all']:.1f}%")
    print(f"| {names[s]} | " + " | ".join(cells) + " |")
print()
objs = ["cheeks (faint pink)", "lips (red)", "backdrop (faint blue wash)", "flag canton (blue)",
        "flag stripes (red, over dark silver)", "mission patch (green)", "small gold touches"]
short = ["cheeks", "lips", "backdrop wash", "canton", "stripes", "patch", "gold touches"]
for s in ["phone", "phone_mixed", "toned"]:
    print(f"**{names[s]}**: share of each painted area shown")
    print()
    print("| pipeline | " + " | ".join(short) + " |")
    print("|---|" + "---|" * len(short))
    for p in pipes:
        r = get(s, p)
        print(f"| {p} | " + " | ".join(f"{100 * r['objects'][o]['shown']:.0f}%" for o in objs) + " |")
    print()
abl = ["proposed", "abl_additive_cast", "abl_no_position", "abl_one_scale", "abl_ungated", "abl_not_tolerant", "proposed_logc"]
print("| ablation | " + " | ".join(names[s].split(',')[0] if False else s for s in scen[:-1]) + " | control FA |")
print("|---|" + "---|" * (len(scen)) )
for p in abl:
    cells = []
    for s in scen[:-1]:
        r = get(s, p) if p == "proposed" else R[s][p]
        cells.append(f"{r['auc']:.2f} / {100 * r['false_shown_all']:.1f}%")
    rc = get("control", p) if p == "proposed" else R["control"][p]
    cells.append(f"{100 * rc['false_shown_all']:.1f}%")
    print(f"| {p} | " + " | ".join(cells) + " |")
