"""Content-addressed evidence and projection sets (owner decision D-047, Stage 04 Step 7 closure).

The journal is an audit and commit log, not a bulk-data container. The two collections of a record that grow with the
article (a claim's evidence, a report's v1 projections) are therefore blobs that the record names by digest:

- an **evidence set** holds a claim's supporting ids, contradicting ids and, per conflict alternative, the ids that
  support it. ``claim_id = H(cand_ref, class, rule, table version, evidence-set digest)``, so the claim binds the exact
  set and no second copy of the lists is kept in the record;
- a **projection set** holds the digests of a report's v1 projection blobs.

Each list is sorted ascending, holds unique ids and is never truncated, so a set has exactly one canonical form and
one digest. ``*_problem`` functions return ``""`` when a value is a valid set (schema, order) and agrees with the
record that names it; Investigation Memory runs them on append and on open, where a missing or corrupt set is a
violation, never an empty set.
"""

from __future__ import annotations

import itertools
from collections.abc import Iterable, Mapping
from typing import Any

from citerift.investigation.schemas import EVIDENCE_SET, PROJECTION_SET, problems

SET_VERSION = "1.0.0"


def _canonical_list(ids: Iterable[str], what: str) -> list[str]:
    out = sorted(ids)
    if len(set(out)) != len(out):
        raise ValueError(f"{what} lists an evidence id twice")
    return out


def evidence_set(
    supporting: Iterable[str], contradicting: Iterable[str] = (), alternatives: Iterable[Iterable[str]] = ()
) -> dict[str, Any]:
    """The canonical evidence set of a claim. A duplicate id within one list is refused (``ValueError``), never
    silently merged."""
    return {
        "schema": EVIDENCE_SET,
        "schema_version": SET_VERSION,
        "supporting": _canonical_list(supporting, "supporting"),
        "contradicting": _canonical_list(contradicting, "contradicting"),
        "alternatives": [_canonical_list(a, f"alternative {i}") for i, a in enumerate(alternatives)],
    }


def projection_set(digests: Iterable[str]) -> dict[str, Any]:
    out = sorted(digests)
    if len(set(out)) != len(out):
        raise ValueError("a projection is listed twice")
    return {"schema": PROJECTION_SET, "schema_version": SET_VERSION, "projections": out}


def _ascending(ids: list[Any]) -> bool:
    return all(a < b for a, b in itertools.pairwise(ids))


def evidence_set_problem(value: Any) -> str:
    found = problems(value, EVIDENCE_SET)
    if found:
        return "evidence set: " + "; ".join(found[:3])
    lists = [value["supporting"], value["contradicting"], *value["alternatives"]]
    if not all(_ascending(ids) for ids in lists):
        return "evidence set: a list is not sorted ascending"
    return ""


def projection_set_problem(value: Any) -> str:
    found = problems(value, PROJECTION_SET)
    if found:
        return "projection set: " + "; ".join(found[:3])
    if not _ascending(value["projections"]):
        return "projection set: projections are not sorted ascending"
    return ""


def set_ids(value: Mapping[str, Any]) -> set[str]:
    """Every evidence id an evidence set names."""
    out = set(value["supporting"]) | set(value["contradicting"])
    for ids in value["alternatives"]:
        out |= set(ids)
    return out


def claim_set_problem(claim: Mapping[str, Any], value: Mapping[str, Any]) -> str:
    """The claim's counts and alternatives agree with its set, and its upstream reasons cite evidence in the set."""
    if claim["supporting_count"] != len(value["supporting"]):
        return "supporting_count is not the length of the set's supporting list"
    if claim["contradicting_count"] != len(value["contradicting"]):
        return "contradicting_count is not the length of the set's contradicting list"
    alts = claim["alternatives"]
    if len(alts) != len(value["alternatives"]):
        return "the claim and its evidence set have different numbers of alternatives"
    if any(a["supporting_count"] != len(ids) for a, ids in zip(alts, value["alternatives"], strict=True)):
        return "an alternative's supporting_count is not the length of its list in the set"
    named = set_ids(value)
    if any(up["evidence"] not in named for up in claim["upstream_reasons"]):
        return "an upstream reason cites evidence that is not in the claim's evidence set"
    return ""
