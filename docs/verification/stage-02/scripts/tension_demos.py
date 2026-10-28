"""Real Evidence Tension demonstrations against the event-log baseline (gate 02-E).

The queries are fixed below, chosen from the real cases and the bounded Crossref run before this script
was written; they are not filtered by outcome. The index is the pinned snapshot built with the pinned Crossref
replay bundle. Each report is validated against the tension-report schema and semantics.

Run: python docs/verification/stage-02/scripts/tension_demos.py --index INDEX --out OUT.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from citerift.retraction import schemas, tension
from citerift.retraction.query import Index

DEMOS = [
    ("D1", "redistributed support", {"doi": "10.1016/s0140-6736(97)11096-0"}),
    ("D2", "redistributed support and origin dependence", {"doi": "10.2217/nnm.14.183"}),
    ("D3", "type conflict between origins", {"doi": "10.1007/s13277-014-2995-5"}),
    ("D4", "uncertain identity link (one-hop bridge)", {"pmid": "26700683"}),
    ("D5", "uncertain identity (one PMID, several DOIs)", {"pmid": "11430323"}),
    ("D6", "unsupported temporal precision (day 1)", {"doi": "10.1001/archneur.1985.04060020080021"}),
    ("D7", "reinstatement without a supersession link", {"doi": "10.1159/000443123"}),
    (
        "D8",
        "control: RW only, exact date, Crossref request failed",
        {"doi": "10.1002/1096-9098(200007)74:3%3c201::aid-jso8%3e3.0.co;2-5"},
    ),
]


def baseline_errors(rep: dict[str, Any]) -> list[str]:
    """Mechanical differences between the event-log baseline and the tension report."""
    base = rep["base"]["result"]
    bl = rep["baseline"]
    out = []
    origins = len(base["support.origins"])
    if bl["confirming_sources"] > max(origins, 0) and origins:
        out.append(f"baseline counts {bl['confirming_sources']} confirming sources; they come from {origins} origin(s)")
    if rep["lookup_state"] == "ambiguous_identity" and bl["answer"] not in ("no_record",):
        out.append(f"baseline answers '{bl['answer']}' although the identifier names several works")
    value = base["retraction_status.value"]
    if bl["answer"] == "retracted" and value != "retracted":
        out.append(f"baseline says retracted; the policy result is {base['retraction_status.status']} {value}")
    if bl["date"] and base["retraction_date.status"] != "verified_fact":
        out.append(
            f"baseline states the date {bl['date']} as given; the policy result is {base['retraction_date.status']}"
        )
    for r in rep["interventions"]:
        if r["changed_fields"]:
            out.append(
                f"baseline cannot show that {r['intervention']}{r['origins'] or ''} changes {r['changed_fields']}"
            )
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    demos = []
    classes: set[str] = set()
    with Index(args.index) as ix:
        cr = json.loads(ix.meta["corroboration"])
        for demo_id, intent, q in DEMOS:
            ev = ix.gather(q.get("doi"), q.get("pmid"))
            rep = tension.report(ev, ix.snapshot_id)
            problems = [str(p) for p in schemas.validate_tension(rep)]
            classes |= set(rep["diagnostic_classes"]) - {"control"}
            demos.append(
                {
                    "id": demo_id,
                    "intent": intent,
                    "query": q,
                    "lookup_state": rep["lookup_state"],
                    "origins": rep["origins"],
                    "single_origin": rep["single_origin"],
                    "base": rep["base"]["result"],
                    "base_reasons": rep["base"]["basis"]["reasons"],
                    "diagnostic_classes": rep["diagnostic_classes"],
                    # "control" with an unresolved base (uncertain, conflicting, unavailable) is no change on an
                    # answer that was never settled, not a control in the sense of SPECIFICATION.md 11.2.
                    "base_unresolved": rep["base_unresolved"],
                    "interventions": [
                        {
                            k: r[k]
                            for k in ("intervention", "origins", "applicable", "changed_fields", "affected_assertions")
                        }
                        | (
                            {"not_applicable_reason": r["not_applicable_reason"]}
                            if "not_applicable_reason" in r
                            else {}
                        )
                        | ({"dependence_unknown": r["dependence_unknown"]} if "dependence_unknown" in r else {})
                        | {"changed_values": {k: r["result"][k] for k in r["changed_fields"]}}
                        for r in rep["interventions"]
                    ],
                    "baseline": rep["baseline"],
                    "baseline_errors": baseline_errors(rep),
                    "evidence_digest": rep["base"]["evidence_digest"],
                    "schema_problems": problems,
                }
            )
    report = {
        "snapshot_id": demos and ix.snapshot_id,
        "tension_version": tension.TENSION_VERSION,
        "corroboration": cr,
        "demonstrations": demos,
        "diagnostic_classes_shown": sorted(classes),
        "limits": [
            "Only RW and Crossref evidence exist for these works; publisher text was not read.",
            "Whether an RW-sourced Crossref relation and the RW CSV row describe the same notice is known; whether a "
            "publisher deposit depends on the same notice is not, and stays unknown.",
            "A changed field shows what a result rests on under a fixed policy; it is not a probability.",
        ],
    }
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    for d in demos:
        print(
            d["id"],
            d["diagnostic_classes"],
            "unresolved" if d["base_unresolved"] else "resolved",
            "|",
            "; ".join(d["baseline_errors"])[:220],
            "| schema",
            d["schema_problems"] or "ok",
        )
    print("classes:", report["diagnostic_classes_shown"])
    return 0 if all(not d["schema_problems"] for d in demos) else 1


if __name__ == "__main__":
    sys.exit(main())
