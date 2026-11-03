"""Differential: baseline engine (3e51792 semantics) versus the corrected engine, on every retained real bundle.

Unit references are compared by (kind, span) because unit ids are renumbered when units disappear. Everything
except the units, identifier-to-unit links, container unit lists, unit issues, the exception ledger and the unit
accounting must be identical; any other difference is reported as unexpected.
"""

import json
import re
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


def entity_fits(doc, issue):
    """Whether a container- or unit-naming issue names an entity that fits it (review RV-2)."""
    cs = {c["id"]: c for c in doc["containers"]}
    us = {u["id"]: u for u in doc["units"]}
    code, ents = issue["code"], issue["entities"]
    if code in ("REF_DEFINITIONS_CONFLICT", "REF_DEFINITIONS_DUPLICATE"):
        m = re.search(r"name '(.*)'$", issue["detail"])
        if m is None:
            return all(cs[e]["binding_state"] in ("conflicting_definitions", "identical_definitions") for e in ents)
        return all(cs[e]["name"] == m.group(1) for e in ents)
    if code == "LIST_DEFINED_UNUSED":
        return all(cs[e]["kind"] == "list_defined_note" and not cs[e]["use_ids"] for e in ents)
    if code == "CITATION_TEMPLATE_UNSUPPORTED":
        return all(us[e]["kind"] == "unsupported_citation_template" for e in ents)
    if code == "DUPLICATE_TEMPLATE_PARAMETER":
        return all(",".join(us[e]["duplicate_params"]) == issue["detail"] for e in ents)
    if code == "UNIT_CLASSIFICATION_UNRESOLVED":
        return all(e in cs and cs[e]["kind"] != "bibliography_entry" for e in ents)
    return True


def bibliography_g_reconciliation(b, n):
    """A bibliography entry is matched to the render through its template unit (reconcile.py). An entry whose unit
    became an ``unsupported_citation_template`` is therefore now found in the render. Exactly these differences
    follow, and nothing else may differ:
    - the entry's render state;
    - the render state of its identifiers;
    - the inspection of its marker region;
    - the render-only identifiers that were the entry's own links;
    - the exceptions that recorded them;
    - status, components and the accounting that counts them.
    Returns the list of differences that this does not explain."""
    g = {
        u["container_id"]
        for u in n["units"]
        if u["kind"] == "unsupported_citation_template"
        and any(c["id"] == u["container_id"] and c["kind"] == "bibliography_entry" for c in n["containers"])
    }
    if not g:
        return None
    left = []
    for cb, cn in zip(b["containers"], n["containers"], strict=True):
        diff = {k for k in cb if k not in ("unit_ids",) and cb[k] != cn[k]}
        if diff and not (cb["id"] in g and diff == {"render"} and cn["render"]["state"] == "matched"):
            left.append(f"container {cb['id']}")
    regions = {c["render"]["region_id"] for c in n["containers"] if c["id"] in g}
    for ib, inn in zip(b["identifiers"], n["identifiers"], strict=True):
        diff = {k for k in ib if k != "unit_id" and ib[k] != inn[k]}
        if diff and not (
            inn["container_id"] in g and diff == {"render"} and inn["render"]["state"] == "render_link_found"
        ):
            left.append(f"identifier {ib['id']}")
    for mb, mn in zip(b["markers"], n["markers"], strict=True):
        if mb != mn and not (mn["container_id"] in g and mb["state"] == "not_inspected"):
            left.append(f"marker of {mb['container_id']}")
    gone = [r for r in b["render_only"]["identifiers"] if r not in n["render_only"]["identifiers"]]
    if [r for r in n["render_only"]["identifiers"] if r not in b["render_only"]["identifiers"]] or any(
        r["list_item"] not in regions for r in gone
    ):
        left.append("render_only")
    ex_gone = [e for e in b["exceptions"] if e not in n["exceptions"]]
    if [e for e in n["exceptions"] if e not in b["exceptions"] and e["code"] != "UNIT_CLASSIFICATION_UNRESOLVED"]:
        left.append("exceptions added")
    for e in ex_gone:
        if e["code"] == "MARKER_REGION_NOT_INSPECTED" and e["entity"] in g:
            continue
        if e["code"] == "RENDER_ONLY_IDENTIFIER" and any(
            e["entity"] == "render-link:" + r["locator"]["path"] for r in gone
        ):
            continue
        left.append(f"exception {e['code']} {e['entity']}")
    return left


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


report = {
    "explained": [],
    "bundles": 0,
    "unchanged": 0,
    "changed": [],
    "unexpected": [],
    "issue_entities": {"base_misnamed": 0, "new_misnamed": 0},
}
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
    renamed = 0
    if other_issues != other_issues_n:
        # Container issues made before the containers were renumbered named the former id (review RV-2). A change
        # of entity alone, with the same code and detail, is that correction when the new entity fits the issue.
        def strip(c):
            return Counter(json.dumps([json.loads(i)[0], json.loads(i)[2]]) for i in c.elements())

        if strip(other_issues) == strip(other_issues_n):
            renamed = sum((other_issues_n - other_issues).values())
        else:
            unexpected.append("non-unit issues")
    report["issue_entities"]["base_misnamed"] += sum(1 for i in b["issues"] if not entity_fits(b, i))
    misnamed = sum(1 for i in n["issues"] if not entity_fits(n, i))
    report["issue_entities"]["new_misnamed"] += misnamed
    if misnamed:
        unexpected.append("an issue names an entity that does not fit it")

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
            cls = "F"  # an efn without own text (efn text without a locator is H since review RV-6)
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
    totals["issue entity corrected (RV-2)"] += renamed
    if rows or unexpected or lost_ids or moved_ids or renamed:
        report["changed"].append(
            {
                "bundle": f.name[:-5].replace("__", "/"),
                "units": rows,
                "identifiers_losing_unit": lost_ids,
                "identifiers_moving_unit": moved_ids,
                "issue_entities_corrected": renamed,
                "unexpected": unexpected,
            }
        )
    else:
        report["unchanged"] += 1
    if unexpected:
        left = bibliography_g_reconciliation(b, n)
        acc_keys = {k for k in set(acc_b) | set(acc_n) if acc_b.get(k) != acc_n.get(k)}
        allowed = {"components", "markers", "render_only", "status", "accounting (other than units)"}
        allowed.add("exceptions (other than unit classification)")
        if (
            left == []
            and acc_keys <= {"identifiers_render", "markers", "render_only_identifiers"}
            and all(u in allowed or u.startswith(("container ", "identifier ")) for u in unexpected)
        ):
            report["explained"].append(
                {"bundle": f.name, "why": "bibliography entries reconciled through their G units", "what": unexpected}
            )
            unexpected = []
    if unexpected:
        report["unexpected"].append({"bundle": f.name, "what": unexpected})
report["totals"] = dict(totals)
print(json.dumps(report, ensure_ascii=False, indent=1))
