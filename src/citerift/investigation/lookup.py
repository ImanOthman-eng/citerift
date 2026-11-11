"""The bounded Stage 02 lookup of the LOOKUP step (owner decision D-048; Stage 04 Step 7 closure).

A lookup reads at most ``lookup_evidence_budget_bytes`` stored bytes of index rows (Stage 04 configuration, so part of
``config_digest``). ``Index.gather_bounded`` (Stage 02, maintenance A-02-001) enforces the budget before it reads the
rows that would exceed it. Over the budget the result is all-or-nothing: the lookup is ``unavailable`` with no events,
no projection value and the issue ``LOOKUP_EVIDENCE_LIMIT_EXCEEDED`` (the code of the failed query, kept in the lookup
observation, SPEC 7.3 D-13). It can therefore never give a positive finding or ``NOT_FOUND_IN_CHECKED_SOURCES``: under
dt-1 an unavailable lookup decides the candidate as ``LOOKUP_UNAVAILABLE`` (D-13) unless an earlier rule's guard
holds on the other lookups (SPEC 7.1); such a claim carries the reason ``LOOKUP_EVIDENCE_LIMIT_EXCEEDED`` besides
``LOOKUP_QUERY_FAILED`` (SPEC S-6.10a). Nothing is truncated.

The default budget is derived in ``docs/verification/stage-04/review/step7/closure/STEP7_CLOSURE.md`` (section
D-048) from the Stage 02 event representation, the canonical JSON encoding, the blob limit and the query's memory.
"""

from __future__ import annotations

from citerift.retraction import policy
from citerift.retraction.query import Evidence, EvidenceBudgetExceeded, Index, normalize_query

DEFAULT_LOOKUP_EVIDENCE_BUDGET_BYTES = 16 * 1024 * 1024
LIMIT_CODE = "LOOKUP_EVIDENCE_LIMIT_EXCEEDED"


def unavailable(doi: str | None, pmid: str | None, budget: int, needed: int) -> Evidence:
    """The lookup result of a query over the budget: ``unavailable``, no events, the limit as its issue."""
    query, keys, _ = normalize_query(doi, pmid)
    ev = Evidence(query, keys, "unavailable")
    ev.evidence_set = policy.EvidenceSet("unavailable", "none", None, (), ())
    ev.issues.append({"code": LIMIT_CODE, "budget_bytes": budget, "needed_at_least_bytes": needed})
    return ev


def bounded_gather(index: Index, doi: str | None, pmid: str | None, budget_bytes: int) -> Evidence:
    """``Index.gather`` when the lookup fits ``budget_bytes``; otherwise the unavailable result, never a part."""
    try:
        return index.gather_bounded(doi, pmid, budget_bytes=budget_bytes)
    except EvidenceBudgetExceeded as exc:
        return unavailable(doi, pmid, exc.budget, exc.needed)
