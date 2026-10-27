"""Projection of every original DOI and PMID key of an index, for comparing two policy revisions.

Run the same script with two code revisions (for example in a git worktree of the earlier one) against
indexes of the same pinned snapshot, then compare the outputs with ``--compare A.json B.json``.

Run: python docs/verification/stage-02/scripts/policy_impact.py --index INDEX --out OUT.json
     python docs/verification/stage-02/scripts/policy_impact.py --compare OLD.json NEW.json --out DIFF.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

FIELDS = ("lookup_state", "status", "value", "date_status", "date_value")


def project(index: Path) -> dict[str, Any]:
    from citerift.retraction.query import Index, render  # noqa: PLC0415 - the revision under test

    out: dict[str, list[Any]] = {}
    with Index(index) as ix:
        dois = [r[0] for r in ix.conn.execute("SELECT DISTINCT original_doi FROM event WHERE original_doi IS NOT NULL")]
        pmids = [
            r[0] for r in ix.conn.execute("SELECT DISTINCT original_pmid FROM event WHERE original_pmid IS NOT NULL")
        ]
        for scheme, keys in (("doi", dois), ("pmid", pmids)):
            for key in sorted(keys):
                ev = ix.gather(key, None) if scheme == "doi" else ix.gather(None, key)
                r = render(ev, ix.snapshot_id)
                proj = r["projection"] or {}
                status = proj.get("retraction_status") or {}
                date = proj.get("retraction_date") or {}
                out[f"{scheme}:{key}"] = [
                    r["lookup_state"],
                    status.get("status"),
                    status.get("value"),
                    date.get("status"),
                    date.get("value"),
                ]
        return {"snapshot_id": ix.snapshot_id, "keys": len(out), "projections": out}


def compare(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    changed = {
        k: {"old": old["projections"][k], "new": v}
        for k, v in new["projections"].items()
        if old["projections"].get(k) != v
    }
    kind = {
        k: f"{c['old'][1]}/{c['old'][2]} -> {c['new'][1]}/{c['new'][2]}"
        + (" (date)" if c["old"][1:3] == c["new"][1:3] else "")
        for k, c in changed.items()
    }
    kinds = Counter(kind.values())
    examples: dict[str, dict[str, Any]] = {}
    for k in sorted(changed):  # the first ten keys of each transition
        bucket = examples.setdefault(kind[k], {})
        if len(bucket) < 10:
            bucket[k] = changed[k]
    return {
        "snapshot_id": new["snapshot_id"],
        "keys_compared": len(new["projections"]),
        "keys_only_in_one": len(set(old["projections"]) ^ set(new["projections"])),
        "changed": len(changed),
        "by_transition": dict(sorted(kinds.items())),
        "examples": examples,
        "changed_keys": sorted(changed),
        "fields": list(FIELDS),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", type=Path)
    ap.add_argument("--compare", type=Path, nargs=2)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    if args.compare:
        old, new = (json.loads(p.read_text(encoding="utf-8")) for p in args.compare)
        result = compare(old, new)
    else:
        result = project(args.index)
    args.out.write_text(json.dumps(result, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in ("projections", "examples", "changed_keys")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
