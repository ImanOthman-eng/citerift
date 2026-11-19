"""Corrective cycle (owner decision D-071; reviewer finding A-03): an exhaustive property test of how dt-2 computes
role ambiguity, against a separate restatement of SPEC 7.3a written from the specification, not from the code. It
catches implementation slips, not a wrong reading of the principle (reviewer finding A-12); the edges outside its
domain (missing ``notice_hit_count``, malformed flags, an unavailable Q1) are named tests of the adversarial suite.

The dt-2 oracle (``test_corrective_oracle.py``) checks the decision table given the abstract input ``rc``; this test
checks the production computation of ``rc`` (``dt1.role_ambiguous`` through ``adapters.detector.lookup_view``) on every
combination of a small synthetic domain: the citation shape, each original and notice identifier of one deciding
event (cited key, another key, absent), its same-record flags, the scheme it was matched by, a second record that gives
the DOI or the PMID both roles (reviewer finding B-01), and the cross-record notice count of each cited key.
"""

from __future__ import annotations

import itertools
from typing import Any

import pytest

from citerift.investigation import dt1
from citerift.investigation.adapters.detector import lookup_view

pytestmark = pytest.mark.unit

D, D2, D3 = "10.5555/w", "10.5555/n", "10.5555/x"
P, P2, P3 = "9100001", "9100002", "9100003"
FLAG = {"doi": "NOTICE_DOI_EQUALS_ORIGINAL", "pmid": "NOTICE_PMID_EQUALS_ORIGINAL"}
VF = {
    "retraction_status": {"status": "verified_fact", "value": "retracted"},
    "retraction_date": None,
    "basis": {"reasons": ["SOURCE_RECORDED_TYPE"], "conflict_groups": [], "scope": "checked_sources"},
}
POSITIVE = set(dt1.POSITIVE.values())


def event(eid: str, by: str, od: Any, op: Any, nd: Any, np_: Any, flags: tuple[str, ...]) -> dict[str, Any]:
    return {
        "event_id": eid,
        "event_type": "retracted",
        "matched_by": by,
        "linked_via": None,
        "original_doi": od,
        "original_pmid": op,
        "notice_doi": nd,
        "notice_pmid": np_,
        "flags": sorted(flags),
        "issues": [],
    }


def observation(events: list[dict[str, Any]], hits: int) -> dict[str, Any]:
    result = {
        "lookup_state": "matched",
        "projection": VF,
        "issues": [],
        "checked_sources": [{"source_id": "retraction-watch", "synthetic": True}],
        "notice_hit_count": hits,
        "notice_hits": [{"event_id": f"nh-{i}"} for i in range(hits)],
    }
    # lookup observation version 3 (dt-3, owner decision D-083): one bib-1 record per event, bound to it; no field
    records = [
        {"event_id": e.get("event_id"), "row_sha256": e.get("row_sha256"), "title": None, "authors": None,
         "journal": None, "original_year": None}
        for e in events
    ]  # fmt: skip
    return {"query": {}, "result": result, "events": events, "event_count": len(events), "records": records}


# The restatement of SPEC 7.3a --------------------------------------------------------------------------------------


def spec_ambiguous(cited: dict[str, str | None], lookups: dict[str, list[dict[str, Any]]], hits: dict[str, int],
                   deciding: list[dict[str, Any]]) -> set[str]:  # fmt: skip
    every = [e for evs in lookups.values() for e in evs]

    def has_notice_role(scheme: str, key: str) -> bool:
        if any(e[f"original_{scheme}"] == key and FLAG[scheme] in e["flags"] for e in every):
            return True
        return cited[scheme] == key and hits[scheme] > 0

    out = set()
    for e in deciding:
        through = [
            (s, e[f"original_{s}"])
            for s in ("doi", "pmid")
            if e[f"original_{s}"] is not None and (e[f"original_{s}"] == cited[s] or e["matched_by"] == s)
        ]
        contested = not through or any(has_notice_role(s, k) for s, k in through)
        tells_apart = any(
            cited[s] is not None
            and e[f"original_{s}"] == cited[s]
            and not has_notice_role(s, cited[s])  # type: ignore[arg-type]
            and e[f"notice_{s}"] is not None
            and e[f"notice_{s}"] != cited[s]
            for s in ("doi", "pmid")
        )
        if contested and not tells_apart:
            out.add(e["event_id"])
    return out


def cases() -> Any:
    shapes = {"DOI": (D, None), "PMID": (None, P), "PAIR": (D, P)}
    flag_sets = [(), (FLAG["doi"],), (FLAG["pmid"],), (FLAG["doi"], FLAG["pmid"])]
    for shape, (cd, cp) in shapes.items():
        for od, op, nd, np_, flags, by, other, hd, hp in itertools.product(
            (D, D3, None), (P, P3, None), (None, D, D2), (None, P, P2), flag_sets, ("doi", "pmid"),
            (None, "doi", "pmid"), (0, 1), (0, 1),
        ):  # fmt: skip
            yield shape, cd, cp, event("e1", by, od, op, nd, np_, flags), other, hd, hp


def build(shape: str, cd: Any, cp: Any, e1: dict[str, Any], other: Any, hd: int, hp: int) -> Any:
    extra = []
    if other == "doi":  # another record gives the cited DOI both roles
        extra = [event("e2", "doi", cd or D, P3, None, P2, (FLAG["doi"],))]
    elif other == "pmid":  # another record gives the cited PMID both roles
        extra = [event("e2", "pmid", D3, cp or P, D2, None, (FLAG["pmid"],))]
    raw: dict[str, list[dict[str, Any]]] = {}
    if cd is not None:
        raw[dt1.Q1_DOI] = [e1, *(x for x in extra if other == "doi")]
    if cp is not None:
        raw[dt1.Q1_PMID] = [e1, *(x for x in extra if other == "pmid")]
    if shape == "PAIR":
        raw[dt1.Q2] = [e1]
    hits = {dt1.Q1_DOI: hd, dt1.Q1_PMID: hp, dt1.Q2: 0}
    order = [r for r in (dt1.Q1_DOI, dt1.Q1_PMID, dt1.Q2) if r in raw]
    lookups = tuple((r, lookup_view(observation(raw[r], hits[r]))) for r in order)
    cand = dt1.Candidate("CITED", None, shape, cd, cp, (), False, lookups)
    deciding = raw[{"DOI": dt1.Q1_DOI, "PMID": dt1.Q1_PMID, "PAIR": dt1.Q2}[shape]]
    spec = spec_ambiguous(
        {"doi": cd, "pmid": cp},
        raw,
        {"doi": hd if cd is not None else 0, "pmid": hp if cp is not None else 0},
        deciding,
    )
    return cand, spec


def test_role_ambiguity_equals_the_independent_formulation_on_the_whole_domain() -> None:
    checked = ambiguous = 0
    for case in cases():
        cand, spec = build(*case)
        assert set(dt1.role_ambiguous(cand)) == spec, case
        checked += 1
        ambiguous += bool(spec)
    assert checked == 3 * 3 * 3 * 3 * 3 * 4 * 2 * 3 * 2 * 2
    assert 0 < ambiguous < checked


EARLIER = {f"D-{i}" for i in range(1, 10)}


def test_no_positive_and_no_notice_from_a_role_ambiguous_case() -> None:
    reached = 0
    for case in cases():
        cand, spec = build(*case)
        out = dt1.decide(cand)
        earlier = out.rule in EARLIER  # identity conflict, adapter inconsistency (D-5) or taint keep their place
        if spec:
            assert out.cls not in POSITIVE and out.cls != "NOTICE_CITED", case
            if not earlier:
                assert (out.rule, out.cls) == ("D-10", "UNRESOLVED_IDENTITY"), case
                assert "IDENTIFIER_ROLE_COLLISION" in out.reasons, case
                reached += 1
        else:
            assert "IDENTIFIER_ROLE_COLLISION" not in out.reasons, case
    assert reached > 0
