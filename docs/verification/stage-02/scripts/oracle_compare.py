"""Compare the index with the independent streaming oracle (gate 02-C).

The oracle (simulations/stage02/oracle_stream.py) shares no code with the engine. This script checks, for every
valid DOI and PMID key of the snapshot, that the engine's original-role and notice-role events are exactly the
records the oracle lists; that the engine has no key the oracle lacks; that accounting and event-type counts
agree; and that every absent synthetic key gives ``no_record`` through the full lookup path.

Run: python docs/verification/stage-02/scripts/oracle_compare.py --oracle ORACLE.json --index INDEX --out OUT.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

from citerift.retraction.query import Index, render

NATURE = {
    "Retraction": "retracted",
    "Expression of concern": "expression_of_concern",
    "Correction": "correction",
    "Reinstatement": "reinstated",
}


def _ordinals(ix: Index, column: str, key: str) -> list[int]:
    return sorted(e["ordinal"] for e in ix.events_by(column, key))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--oracle", type=Path, required=True)
    ap.add_argument("--index", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    started = time.perf_counter()
    oracle = json.loads(args.oracle.read_text(encoding="utf-8"))
    mismatches: list[dict[str, Any]] = []
    checked = {"doi": 0, "pmid": 0}
    with Index(args.index) as ix:
        counts = json.loads(ix.meta["counts"])
        account = {
            k: (oracle[k] if k != "quarantined" else len(oracle[k]), counts[k])
            for k in ("records", "accepted", "quarantined", "blank_lines", "physical_lines")
        }
        for k, (o, e) in account.items():
            if o != e:
                mismatches.append({"check": "accounting", "field": k, "oracle": o, "engine": e})
        natures = {NATURE[n]: c for n, c in oracle["nature_counts"].items()}
        if natures != counts["by_event_type"]:
            mismatches.append({"check": "event_types", "oracle": natures, "engine": counts["by_event_type"]})
        if oracle["source"]["sha256"] != ix.meta["source_sha256"]:
            mismatches.append(
                {"check": "source", "oracle": oracle["source"]["sha256"], "engine": ix.meta["source_sha256"]}
            )
        for scheme in ("doi", "pmid"):
            for key, roles in oracle[scheme].items():
                for role in ("original", "notice"):
                    got = _ordinals(ix, f"{role}_{scheme}", key)
                    if got != sorted(roles[role]):
                        mismatches.append(
                            {
                                "check": "key",
                                "scheme": scheme,
                                "key": key,
                                "role": role,
                                "oracle": roles[role],
                                "engine": got,
                            }
                        )
                checked[scheme] += 1
            engine_keys = set()
            for role in ("original", "notice"):
                engine_keys |= {
                    k
                    for (k,) in ix.conn.execute(
                        f"SELECT DISTINCT {role}_{scheme} FROM event WHERE {role}_{scheme} IS NOT NULL"  # noqa: S608 - fixed column names
                    )
                }
            extra = sorted(engine_keys - set(oracle[scheme]))
            if extra:
                mismatches.append({"check": "extra_keys", "scheme": scheme, "count": len(extra), "sample": extra[:20]})
        invalid_engine = dict(
            ix.conn.execute(
                "SELECT column_name, COUNT(*) FROM ident WHERE norm IS NULL AND missing = 0 GROUP BY column_name"
            )
        )
        for column, n in oracle["invalid_identifiers"].items():
            if invalid_engine.get(column, 0) != n:
                mismatches.append(
                    {
                        "check": "invalid_identifiers",
                        "column": column,
                        "oracle": n,
                        "engine": invalid_engine.get(column, 0),
                    }
                )
        absent = {"doi": 0, "pmid": 0}
        for scheme, keys in oracle["absent_keys"].items():
            for key in keys:
                ev = ix.gather(key, None) if scheme == "doi" else ix.gather(None, key)
                out = render(ev, ix.snapshot_id)
                if out["lookup_state"] != "no_record" or out["total_event_count"] != 0:
                    mismatches.append({"check": "absent", "scheme": scheme, "key": key, "state": out["lookup_state"]})
                absent[scheme] += 1
        snapshot = ix.snapshot_id
        digests = {k: ix.meta[k] for k in ("artifact_digest", "semantic_digest")}
    report = {
        "comparison": "index vs independent streaming oracle (gate 02-C)",
        "oracle_version": oracle["oracle_version"],
        "oracle_sha256": hashlib.sha256(args.oracle.read_bytes()).hexdigest(),
        "snapshot_id": snapshot,
        "index_digests": digests,
        "keys_checked": checked,
        "key_role_comparisons": 2 * (checked["doi"] + checked["pmid"]),
        "absent_keys_checked": absent,
        "accounting": {k: {"oracle": o, "engine": e} for k, (o, e) in account.items()},
        "mismatch_count": len(mismatches),
        "mismatches": mismatches[:100],
        "seconds": round(time.perf_counter() - started, 2),
        "scope": "Checks extraction and query fidelity against the source bytes, not the truth of source assertions.",
    }
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("keys_checked", "absent_keys_checked", "mismatch_count", "seconds")}))
    return 0 if not mismatches else 1


if __name__ == "__main__":
    sys.exit(main())
