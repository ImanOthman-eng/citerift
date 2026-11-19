"""Stage 04 corrective cycle, owner decision D-075 (reviewer finding B-03): every (original DOI, notice PMID) pair that
one record of the pinned Stage 02 snapshot gives, cited together, decided by the frozen dt-1 table and by dt-2.

The mirror of D-058: the citation names the work by its original DOI and the notice by its PMID. Read-only (the index
is opened ``mode=ro`` for the pair list and through Stage 02's own query layer for the lookups); no network; no clock
in the output. Each pair is a synthetic citation (eligibility CITED, shape PAIR, no taint) built from the three
production LOOKUP observations and decided by both tables, as in ``pair_census.py``.

Usage: ``python b03_census.py INDEX.sqlite OUT.json``
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

POSITIVE = set(dt1.POSITIVE.values())


def pairs(path: Path) -> list[tuple[str, str]]:
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    rows = con.execute(
        "SELECT DISTINCT original_doi, notice_pmid FROM event WHERE original_doi IS NOT NULL AND notice_pmid IS NOT "
        "NULL AND notice_pmid IS NOT original_pmid ORDER BY 1, 2"
    ).fetchall()
    con.close()
    return [(str(d), str(p)) for d, p in rows]


def label(o: Any) -> str:
    return f"{o.rule} {o.cls or o.failure}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("index", type=Path)
    ap.add_argument("out", type=Path)
    a = ap.parse_args()
    prov = F1.provenance(a.index)
    todo = pairs(a.index)
    transitions: Counter[str] = Counter()
    changed: list[dict[str, Any]] = []
    positive = {"dt1": 0, "dt2": 0}
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
            positive["dt1"] += old.cls in POSITIVE
            positive["dt2"] += new.cls in POSITIVE
            if (old.rule, old.cls, old.reasons) != (new.rule, new.cls, new.reasons):
                changed.append(
                    {
                        "doi": doi,
                        "pmid": pmid,
                        "dt1": [old.rule, old.cls or old.failure, list(old.reasons)],
                        "dt2": [new.rule, new.cls or new.failure, list(new.reasons)],
                    }
                )
    out = {
        "census": "citerift-stage04-b03-census/1",
        "decision": "D-075",
        "provenance": prov,
        "pairs": len(todo),
        "positive": positive,
        "transitions": dict(sorted(transitions.items())),
        "changed": changed,
    }
    a.out.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("pairs", "positive")} | {"changed": len(changed)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
