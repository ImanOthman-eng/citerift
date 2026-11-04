"""Post-exposure check: every render link in every retained locked or adjudicated label (all campaigns), compared
with the engine before (ec81c7f) and after the R-038 correction. For each labelled use with a render_ref_id the
engine's matched marker id is compared; adjudicated labels replace locked ones of the same campaign and article.
These labels were exposed before the correction: this is a regression check, not a gate."""

import json
import sys
from collections import Counter
from pathlib import Path

root, base, new = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])


def docs(d):
    out = {}
    for f in d.glob("*.json"):
        if f.name.startswith("_"):
            continue
        x = json.loads(f.read_text())
        c = x["capture"]
        out[f"{c['wiki']}-{c['revision_id']}"] = x
    return out


B, N = docs(base), docs(new)
labels = {}
ev = root / "docs/verification/stage-03/evaluation"
for f in sorted(ev.glob("**/annotations/locked/**/*.json")):
    if f.name.startswith(("ANNOTATION", "_")):
        continue
    camp = str(f.relative_to(ev)).split("/annotations/")[0]
    labels[(camp, f.stem)] = f
for f in sorted(ev.glob("**/adjudication/adjudicated/*.json")):
    if "/returned/" in str(f):
        continue
    camp = str(f.relative_to(ev)).split("/adjudication/")[0]
    labels[(camp, f.stem)] = f
tot = {"before": Counter(), "after": Counter()}
rows = []
for (camp, art), f in sorted(labels.items()):
    try:
        lab = json.loads(f.read_text())
    except ValueError:
        print(f"unreadable label file {f}", file=sys.stderr)
        continue
    if not isinstance(lab, dict) or "uses" not in lab or art not in B:
        continue
    for which, D in (("before", B), ("after", N)):
        eng = {u["source"]["cp_start"]: u for u in D[art]["uses"]}
        for lu in lab["uses"]:
            want = lu.get("render_ref_id")
            cp = (lu.get("at") or {}).get("cp")
            u = eng.get(cp)
            if u is None:
                tot[which]["label_without_engine_use"] += 1
                continue
            got = (u["render"].get("locator") or {}).get("element_id") if u["render"]["state"] == "matched" else None
            if want is None and got is None:
                k = "both_none"
            elif want is None:
                k = "engine_link_label_none"
            elif got is None:
                k = "engine_abstained_label_link"
            elif got == want:
                k = "correct"
            else:
                k = "false_attachment"
            tot[which][k] += 1
            if which == "after":
                ub = next(x for x in B[art]["uses"] if x["source"]["cp_start"] == cp)
                gb = (
                    (ub["render"].get("locator") or {}).get("element_id")
                    if ub["render"]["state"] == "matched"
                    else None
                )
                if gb != got:
                    rows.append({"campaign": camp, "article": art, "cp": cp, "label": want, "before": gb, "after": got})
print(
    json.dumps(
        {"label_files": len(labels), "before": tot["before"], "after": tot["after"], "changed": rows},
        ensure_ascii=False,
        indent=1,
    )
)
