"""Reviewer finding A-04 (owner decision D-083, item 6): prove on the whole pinned snapshot that a non-cited bridge key
cannot create a positive the cited key does not support.

Read-only. For every distinct original DOI and original PMID of the Stage 02 index, a synthetic citation carrying only
that key (eligibility CITED, no taint, no description) is decided by the working-tree table (dt-3) on the observation
the production LOOKUP adapter builds. For every positive (D-14) the script checks the invariant

    I-A04: the deciding lookup has a direct event (attached through the cited key, ``linked_via`` null) that is not
    role-ambiguous, whose own type gives the claim's class, and the lookup's basis has no BRIDGE_ONLY_SUPPORT;

and it measures the exposure of A-04: positives whose lookup also holds a bridged event attached through a non-cited
key that some record gives as a notice identifier. Usage: ``uv run python a04_invariant.py INDEX.sqlite OUT.json``
(the output belongs outside the repository or in ``../lows/``; it holds no clock and no path).
"""

from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fc_provenance import finish, start

from citerift.investigation import dt1
from citerift.investigation.adapters.detector import lookup_view
from citerift.investigation.adapters.lookup import observe
from citerift.investigation.lookup import DEFAULT_LOOKUP_EVIDENCE_BUDGET_BYTES
from citerift.retraction.query import Index

# The production type-to-class map (dt1.POSITIVE); a hand copy here once mapped "retraction" instead of "retracted".
CLASS_OF_TYPE = dt1.POSITIVE


def keys(path: Path) -> list[tuple[str, str]]:
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        out = [
            ("doi", k) for (k,) in con.execute("SELECT DISTINCT original_doi FROM event WHERE original_doi IS NOT NULL")
        ]
        out += [
            ("pmid", k)
            for (k,) in con.execute("SELECT DISTINCT original_pmid FROM event WHERE original_pmid IS NOT NULL")
        ]
    finally:
        con.close()
    return sorted(out)


def main() -> int:
    path, target = Path(sys.argv[1]), Path(sys.argv[2])
    prov = start(Path(__file__), path)
    rules: Counter[str] = Counter()
    types: Counter[str] = Counter()
    violations: list[dict[str, Any]] = []
    exposure: list[dict[str, Any]] = []
    with Index(path) as index:
        for scheme, key in keys(path):
            doi, pmid = (key, None) if scheme == "doi" else (None, key)
            obs = observe(index, {}, doi, pmid, DEFAULT_LOOKUP_EVIDENCE_BUDGET_BYTES)
            lk = lookup_view(obs)
            role = dt1.Q1_DOI if scheme == "doi" else dt1.Q1_PMID
            cand = dt1.Candidate("CITED", None, scheme.upper(), doi, pmid, (), False, ((role, lk),))
            out = dt1.decide(cand)
            rules[out.rule] += 1
            if out.rule != "D-14":
                continue
            ambiguous = set(dt1.role_ambiguous(cand))
            support = [
                e
                for e in lk.events
                if e.direct and e.event_id not in ambiguous and CLASS_OF_TYPE.get(str(e.event_type)) == out.cls
            ]
            types[str(out.cls)] += 1
            if not support or "BRIDGE_ONLY_SUPPORT" in lk.basis_reasons:
                violations.append({"scheme": scheme, "key": key, "class": out.cls, "events": len(lk.events)})
            other = "pmid" if scheme == "doi" else "doi"
            for e in lk.events:
                bridge = e.original_pmid if other == "pmid" else e.original_doi
                if e.direct or bridge is None:
                    continue
                if index.events_by(f"notice_{other}", bridge):
                    exposure.append(
                        {
                            "scheme": scheme,
                            "key": key,
                            "class": out.cls,
                            "bridged_event": e.event_id,
                            "bridge_key": bridge,
                            "direct_support": [s.event_id for s in support][:5],
                        }
                    )
    report = {
        "invariant": "I-A04 (see the docstring)",
        "keys_decided": sum(rules.values()),
        "rules": dict(sorted(rules.items())),
        "positives_by_class": dict(sorted(types.items())),
        "violations": violations,
        "exposure_bridged_through_a_notice_key": exposure,
        "exposure_keys": sorted({(x["scheme"], x["key"]) for x in exposure}),
        "table_version": dt1.TABLE_VERSION,
        "provenance": prov,
    }
    finish(prov, Path(__file__), path)
    target.write_text(json.dumps(report, indent=1, sort_keys=True, default=list) + "\n", encoding="utf-8")
    print(
        json.dumps({k: v for k, v in report.items() if k != "exposure_bridged_through_a_notice_key"}, indent=1)[:4000]
    )
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
