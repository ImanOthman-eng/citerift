"""R-038 differential: the engine before the correction (ec81c7f, the D-035 candidate's engine) versus after, on
every retained real bundle. Expected differences are confined to the render pairing of uses that share a name inside
one template's output, and to what follows from it (container render state, marker observations, witnesses, the
reconciliation issues, the exception ledger, the accounting and the digests). Any other difference is reported as
unexpected."""

import json
import sys
from collections import Counter
from pathlib import Path

base, new = Path(sys.argv[1]), Path(sys.argv[2])
EXPECTED_TOP = {
    "extractor",
    "extraction_digest",
    "schema_version",
    "uses",
    "containers",
    "markers",
    "issues",
    "exceptions",
    "accounting",
    "components",
    "status",
    "identifiers",
    "units",
    "render_only",
}
NEW_BASES = {"reference_role_in_template_output", "anchor_in_template_output", "elimination_in_template_output"}
report = {"bundles": 0, "unchanged_uses": 0, "changed_bundles": [], "unexpected": [], "totals": Counter()}
for f in sorted(base.glob("*.json")):
    if f.name.startswith("_"):
        continue
    b, n = json.loads(f.read_text()), json.loads((new / f.name).read_text())
    report["bundles"] += 1
    unexpected = [k for k in set(b) | set(n) if k not in EXPECTED_TOP and b.get(k) != n.get(k)]
    if len(b["uses"]) != len(n["uses"]):
        unexpected.append("use count")
    rows = []
    changed_use_ids = set()
    for ub, un in zip(b["uses"], n["uses"], strict=False):
        if {k: v for k, v in ub.items() if k != "render"} != {k: v for k, v in un.items() if k != "render"}:
            unexpected.append(f"use {ub['id']} outside render")
        rb, rn = ub["render"], un["render"]
        if rb == rn:
            report["unchanged_uses"] += 1
            continue
        changed_use_ids.add(ub["id"])
        pb = (rb.get("locator") or {}).get("element_id") or (rb.get("locator") or {}).get("path")
        pn = (rn.get("locator") or {}).get("element_id") or (rn.get("locator") or {}).get("path")
        if rb["state"] == "matched" and rn["state"] == "matched":
            kind = "same_marker_new_basis" if pb == pn else "different_marker"
        elif rb["state"] == "matched":
            kind = "matched_to_" + rn["state"]
        elif rn["state"] == "matched":
            kind = rb["state"] + "_to_matched"
        else:
            kind = rb["state"] + "_to_" + rn["state"]
        if rb.get("basis") not in (None, "name_in_template_output") or (
            rn.get("basis") not in NEW_BASES | {None, "name_in_template_output"}
        ):
            unexpected.append(f"use {ub['id']} basis {rb.get('basis')} -> {rn.get('basis')}")
        report["totals"][kind] += 1
        rows.append(
            {
                "use": ub["id"],
                "name": ub.get("name"),
                "cp": ub["source"]["cp_start"],
                "kind": kind,
                "before": [rb["state"], rb.get("basis"), pb],
                "after": [rn["state"], rn.get("basis"), pn],
            }
        )
    # identifiers and units: must be unchanged apart from render-derived fields
    for key in ("identifiers", "units"):

        def strip(x):
            return {k: v for k, v in x.items() if k not in ("render", "witness", "witnesses", "observation")}

        if [strip(x) for x in b[key]] != [strip(x) for x in n[key]]:
            unexpected.append(f"{key} outside render fields")
    if rows or unexpected:
        report["changed_bundles"].append(
            {"bundle": f.name, "article": f"{b['capture']['wiki']}-{b['capture']['revision_id']}", "uses": rows}
        )
    if unexpected:
        report["unexpected"].append({"bundle": f.name, "what": sorted(set(unexpected))})
    if not all(c["ok"] for c in n["accounting"].get("checks", [])):
        report["unexpected"].append({"bundle": f.name, "what": ["an accounting check fails after"]})
report["totals"] = dict(report["totals"])
print(json.dumps(report, ensure_ascii=False, indent=1))
