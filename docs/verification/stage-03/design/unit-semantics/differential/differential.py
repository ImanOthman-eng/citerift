"""Differential: baseline engine (3e51792 semantics) versus the corrected engine, on every retained real bundle.

Unit references are compared by (kind, span) because unit ids are renumbered when units disappear. Everything
except the units, identifier-to-unit links, container unit lists, unit issues, the exception ledger and the unit
accounting must be identical; any other difference is reported as unexpected.
"""

import json
import sys
from collections import Counter
from pathlib import Path

base, new = Path(sys.argv[1]), Path(sys.argv[2])
UNIT_CODES = {
    "UNIT_CLASSIFICATION_UNRESOLVED",
    "CITATION_TEMPLATE_UNSUPPORTED",
    "UNIT_BOUNDARY_UNRESOLVED",
    "CO_REPORTED_IDENTIFIERS",
    "DUPLICATE_TEMPLATE_PARAMETER",
}


def unit_key(doc):
    return {u["id"]: (u["kind"], u["source"]["cp_start"], u["source"]["cp_end"]) for u in doc["units"]}


def norm(doc):
    uk = unit_key(doc)
    d = json.loads(json.dumps(doc))
    for k in ("extractor", "extraction_digest", "schema_version"):
        d.pop(k, None)
    for c in d["containers"]:
        c["unit_ids"] = sorted(uk[x] for x in c["unit_ids"])
    for i in d["identifiers"]:
        i["unit_id"] = uk.get(i["unit_id"]) if i["unit_id"] else None
    d["issues"] = sorted(
        json.dumps([i["code"], [uk.get(e, e) for e in i["entities"]], i["detail"]]) for i in d["issues"]
    )
    return d


report = {"bundles": 0, "unchanged": 0, "changed": [], "unexpected": []}
totals = Counter()
for f in sorted(base.glob("*.json")):
    if f.name.startswith("_"):
        continue
    b, n = json.loads(f.read_text()), json.loads((new / f.name).read_text())
    report["bundles"] += 1
    nb, nn = norm(b), norm(n)
    unexpected = sorted(
        k
        for k in set(nb) | set(nn)
        if k not in ("units", "identifiers", "containers", "issues", "exceptions", "accounting")
        and nb.get(k) != nn.get(k)
    )
    # containers: only unit_ids may differ
    for cb, cn in zip(nb["containers"], nn["containers"], strict=False):
        if {k: v for k, v in cb.items() if k != "unit_ids"} != {k: v for k, v in cn.items() if k != "unit_ids"}:
            unexpected.append(f"container {cb['id']}")
    if len(nb["containers"]) != len(nn["containers"]):
        unexpected.append("container count")
    for ib, inn in zip(nb["identifiers"], nn["identifiers"], strict=False):
        if {k: v for k, v in ib.items() if k != "unit_id"} != {k: v for k, v in inn.items() if k != "unit_id"}:
            unexpected.append(f"identifier {ib['id']}")
    if len(nb["identifiers"]) != len(nn["identifiers"]):
        unexpected.append("identifier count")
    other_issues = Counter(i for i in nb["issues"] if json.loads(i)[0] not in UNIT_CODES)
    other_issues_n = Counter(i for i in nn["issues"] if json.loads(i)[0] not in UNIT_CODES)
    if other_issues != other_issues_n:
        unexpected.append("non-unit issues")

    def acc(a):
        out = {k: v for k, v in a.items() if k not in ("units", "checks")}
        out["checks"] = [
            c if c["name"] != "every unit in exactly one container" else {"name": c["name"], "ok": c["ok"]}
            for c in a.get("checks", [])
        ]
        return out

    acc_b, acc_n = acc(nb["accounting"]), acc(nn["accounting"])
    if not all(c["ok"] for c in nn["accounting"].get("checks", [])):
        unexpected.append("an accounting check fails")
    if acc_b != acc_n:
        unexpected.append("accounting (other than units)")
    ex_b = [e for e in nb["exceptions"] if e["code"] != "UNIT_CLASSIFICATION_UNRESOLVED"]
    ex_n = [e for e in nn["exceptions"] if e["code"] != "UNIT_CLASSIFICATION_UNRESOLVED"]
    if ex_b != ex_n:
        unexpected.append("exceptions (other than unit classification)")
    ub = Counter((u["kind"], u["source"]["cp_start"], u["source"]["cp_end"]) for u in b["units"])
    un = Counter((u["kind"], u["source"]["cp_start"], u["source"]["cp_end"]) for u in n["units"])
    removed, added = ub - un, un - ub
    text = None
    defs = {d["id"]: (c, d) for c in n["containers"] for d in c["definitions"]}
    rows = []
    unresolved = {
        (i["entities"][0], i["detail"].split(":")[0])
        for i in n["issues"]
        if i["code"] == "UNIT_CLASSIFICATION_UNRESOLVED"
    }
    for (kind, s, e), k in sorted(removed.items()):
        bu = next(u for u in b["units"] if (u["kind"], u["source"]["cp_start"], u["source"]["cp_end"]) == (kind, s, e))
        c, d = defs.get(bu["definition_id"], (None, None))
        idx = bu["definition_id"].rsplit("/d", 1)[1] if bu["definition_id"] else None
        g = [
            u
            for u in n["units"]
            if u["definition_id"] == bu["definition_id"] and u["kind"] == "unsupported_citation_template"
        ]
        if kind != "unstructured_text":
            cls = "template unit removed: " + (bu["template"] or {}).get("canonical", "?")
        elif g:
            cls = "G"
        elif c is not None and (c["id"], f"definition {idx}") in unresolved:
            cls = "H"
        elif d is not None and d.get("origin") == "efn":
            cls = "F"
        else:
            cls = "E-or-empty"
        totals[cls] += k
        rows.append(
            {
                "removed": kind,
                "cp": [s, e],
                "class": cls,
                "body": (bu["source"].get("raw") or "")[:160] if isinstance(bu["source"], dict) else None,
                "identifiers": len(bu["identifier_ids"]),
            }
        )
    for (kind, s, e), k in sorted(added.items()):
        totals["added " + kind] += k
        rows.append({"added": kind, "cp": [s, e]})
    lost_ids = sum(
        1 for ib, inn in zip(nb["identifiers"], nn["identifiers"], strict=False) if ib["unit_id"] and not inn["unit_id"]
    )
    moved_ids = sum(
        1
        for ib, inn in zip(nb["identifiers"], nn["identifiers"], strict=False)
        if ib["unit_id"] and inn["unit_id"] and ib["unit_id"] != inn["unit_id"]
    )
    totals["identifiers losing a unit"] += lost_ids
    totals["identifiers moving unit"] += moved_ids
    if rows or unexpected or lost_ids or moved_ids:
        report["changed"].append(
            {
                "bundle": f.name[:-5].replace("__", "/"),
                "units": rows,
                "identifiers_losing_unit": lost_ids,
                "identifiers_moving_unit": moved_ids,
                "unexpected": unexpected,
            }
        )
    else:
        report["unchanged"] += 1
    if unexpected:
        report["unexpected"].append({"bundle": f.name, "what": unexpected})
report["totals"] = dict(totals)
print(json.dumps(report, ensure_ascii=False, indent=1))
