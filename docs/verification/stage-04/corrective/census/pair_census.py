"""Stage 04 corrective cycle (D-071; reviewer findings B-01, B-02, B-06): every original DOI+PMID pair of the pinned
Stage 02 snapshot, cited together, decided by the frozen dt-1 table and by dt-2.

Read-only (the index is opened ``mode=ro`` for the pair list and through Stage 02's own query layer for the lookups);
no network; no clock in the output. For each distinct (original DOI, original PMID) pair that some event records, a
synthetic citation (eligibility CITED, shape PAIR, no taint) is built from the three production LOOKUP observations
(``adapters.lookup.observe``: Q1 DOI, Q1 PMID, Q2) and decided by both tables. The output tallies the transitions and
lists every pair whose decision changes, with the role evidence that changed it.

``--variant lenient`` measures the alternative put to the owner (decision card on resolution): a cited second key
that no evidence gives a notice role resolves a collision even when its record states no notice identifier in its
scheme. It replaces ``dt1.discriminating`` in this process only; production code is unchanged.

Usage: ``python pair_census.py INDEX.sqlite OUT.json [--shard k/n] [--variant strict|lenient]``
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from citerift.investigation import dt1
from citerift.investigation.adapters.detector import lookup_view
from citerift.investigation.adapters.lookup import observe
from citerift.investigation.lookup import DEFAULT_LOOKUP_EVIDENCE_BUDGET_BYTES as BUDGET
from citerift.retraction.query import Index

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import frozen_dt1 as F1


def pairs(path: Path) -> list[tuple[str, str]]:
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    rows = con.execute(
        "SELECT DISTINCT original_doi, original_pmid FROM event "
        "WHERE original_doi IS NOT NULL AND original_pmid IS NOT NULL ORDER BY 1, 2"
    ).fetchall()
    con.close()
    return [(str(d), str(p)) for d, p in rows]


def label(o: Any) -> str:
    return f"{o.rule} {o.cls or o.failure}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("index", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--variant", choices=("strict", "lenient"), default="strict")
    a = ap.parse_args()
    if a.variant == "lenient":

        def lenient(c: dt1.Candidate, e: dt1.Event, scheme: str) -> bool:
            cited = c.doi if scheme == "doi" else c.pmid
            own = e.original_doi if scheme == "doi" else e.original_pmid
            return cited is not None and own == cited and not dt1.role_collided(c, scheme, cited)

        dt1.discriminating = lenient  # type: ignore[assignment]
    k, n = (int(x) for x in a.shard.split("/"))
    todo = [q for i, q in enumerate(pairs(a.index)) if i % n == k]
    transitions: Counter[str] = Counter()
    changed: list[dict[str, Any]] = []
    with Index(a.index) as index:
        for doi, pmid in todo:
            obs = {
                dt1.Q1_DOI: observe(index, {}, doi, None, BUDGET),
                dt1.Q1_PMID: observe(index, {}, None, pmid, BUDGET),
                dt1.Q2: observe(index, {}, doi, pmid, BUDGET),
            }
            lookups = tuple((r, lookup_view(o)) for r, o in obs.items())
            cand = dt1.Candidate("CITED", None, "PAIR", doi, pmid, (), False, lookups)
            old, new = F1.decide(cand), dt1.decide(cand)
            transitions[f"{label(old)} -> {label(new)}"] += 1
            if (old.rule, old.cls, old.reasons) != (new.rule, new.cls, new.reasons):
                changed.append(
                    {
                        "doi": doi,
                        "pmid": pmid,
                        "dt1": [old.rule, old.cls or old.failure, list(old.reasons)],
                        "dt2": [new.rule, new.cls or new.failure, list(new.reasons)],
                        "role_ambiguous_events": list(dt1.role_ambiguous(cand)),
                    }
                )
    out = {
        "census": "citerift-stage04-pair-census/1",
        "shard": [k, n],
        "variant": a.variant,
        "pairs": len(todo),
        "transitions": dict(sorted(transitions.items())),
        "changed": changed,
    }
    a.out.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"pairs": len(todo), "changed": len(changed)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
