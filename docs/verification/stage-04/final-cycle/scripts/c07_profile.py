"""Reviewer finding C-07 (owner decision D-083, item 6): profile the dt-3 decision on candidates with many events.

Read-only. Two measurements of ``dt1.decide`` (the production table, dt-3):

1. synthetic: a PAIR candidate with three matched lookups (Q1_DOI, Q1_PMID, Q2) of ``n`` events each, every event
   attached through the cited keys, every record a full bib-1 record, the citation a full cited object (so the role
   scans, the bib-1 comparisons and the D-13a guard all run over every event); ``n`` in 10, 100, 300, 1,000, 3,000;
2. real: the keys of the pinned Stage 02 index with the most events (top 5 original DOIs and PMIDs), decided as a
   DOI or PMID candidate on the observation the production LOOKUP adapter builds, with a cited object.

Each timing is the median of ``REPEATS`` runs of ``decide`` (``time.perf_counter``). Usage:
``uv run python c07_profile.py INDEX.sqlite OUT.json``.
"""

from __future__ import annotations

import json
import platform
import sqlite3
import statistics
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fc_provenance import provenance

from citerift.investigation import bibliographic as bib
from citerift.investigation import dt1
from citerift.investigation.adapters.detector import lookup_view
from citerift.investigation.adapters.lookup import observe
from citerift.investigation.lookup import DEFAULT_LOOKUP_EVIDENCE_BUDGET_BYTES
from citerift.retraction.query import Index

REPEATS = 5
SIZES = (10, 100, 300, 1000, 3000)
DOI, PMID = "10.1000/example.1", "1000001"
CITED = bib.CitedObject(
    titles=("A randomised trial of an example intervention in adults",),
    authors=("Example", "Sample", "Placeholder"),
    year="2010",
)


def record(i: int) -> bib.RecordObject:
    return bib.RecordObject(
        title=f"A randomised trial of an example intervention in adults {i}",
        authors="Ann Example;Bo Sample;Cy Placeholder",
        journal="Journal of Examples",
        original_year=2010,
    )


def synthetic(n: int) -> dt1.Candidate:
    def lookup(matched_by: str) -> dt1.Lookup:
        events = tuple(
            dt1.Event(
                position=i,
                event_id=f"ev-{matched_by}-{i:05d}",
                event_type="retracted",
                matched_by=matched_by,
                linked_via=None,
                original_doi=DOI,
                original_pmid=PMID,
                flags=(),
                notice_doi=f"10.1000/notice.{i}",
                notice_pmid=str(2000000 + i),
                record=record(i),
            )
            for i in range(n)
        )
        return dt1.Lookup(
            state="matched",
            projection=True,
            status="verified_fact",
            value="retracted",
            basis_reasons=("SOURCE_RECORDED_RETRACTION",),
            conflict_groups=(),
            collision=(),
            budget_refused=False,
            events=events,
            notice_hits=0,
        )

    lookups = ((dt1.Q1_DOI, lookup("doi")), (dt1.Q1_PMID, lookup("pmid")), (dt1.Q2, lookup("doi")))
    return dt1.Candidate("CITED", None, "PAIR", DOI, PMID, (), False, lookups, CITED)


def timed(c: dt1.Candidate) -> tuple[float, dt1.Outcome]:
    runs = []
    out = dt1.decide(c)
    for _ in range(REPEATS):
        t0 = time.perf_counter()
        out = dt1.decide(c)
        runs.append(time.perf_counter() - t0)
    return statistics.median(runs), out


def largest_keys(path: Path) -> list[tuple[str, str, int]]:
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        out = []
        for scheme, col in (("doi", "original_doi"), ("pmid", "original_pmid")):
            sql = f"SELECT {col}, COUNT(*) c FROM event WHERE {col} IS NOT NULL GROUP BY {col} ORDER BY c DESC, {col} LIMIT 5"  # noqa: S608, E501 - fixed columns
            out += [(scheme, k, n) for k, n in con.execute(sql)]
    finally:
        con.close()
    return out


def main() -> int:
    path, target = Path(sys.argv[1]), Path(sys.argv[2])
    report: dict[str, Any] = {"repeats": REPEATS, "synthetic": [], "real": []}
    for n in SIZES:
        seconds, out = timed(synthetic(n))
        report["synthetic"].append({"events_per_lookup": n, "seconds": round(seconds, 6), "rule": out.rule})
        print(n, round(seconds, 4), out.rule, flush=True)
    with Index(path) as index:
        for scheme, key, n in largest_keys(path):
            doi, pmid = (key, None) if scheme == "doi" else (None, key)
            lk = lookup_view(observe(index, {}, doi, pmid, DEFAULT_LOOKUP_EVIDENCE_BUDGET_BYTES))
            role = dt1.Q1_DOI if scheme == "doi" else dt1.Q1_PMID
            cand = dt1.Candidate("CITED", None, scheme.upper(), doi, pmid, (), False, ((role, lk),), CITED)
            seconds, out = timed(cand)
            report["real"].append(
                {
                    "scheme": scheme,
                    "key": key,
                    "index_events": n,
                    "lookup_events": len(lk.events),
                    "seconds": round(seconds, 6),
                    "rule": out.rule,
                }
            )
            print(scheme, key, n, len(lk.events), round(seconds, 4), out.rule, flush=True)
    report["platform"] = {"python": platform.python_version(), "machine": platform.machine()}
    report["table_version"] = dt1.TABLE_VERSION
    report["provenance"] = provenance(Path(__file__), path)
    target.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
