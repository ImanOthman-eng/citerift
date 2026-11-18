"""Corrective cycle (owner decision D-071): identifier role collisions never become a positive attachment.

Principle (D-071 section 3): an identifier whose checked evidence gives incompatible publication-object roles never
produces a positive work attachment solely because one of those roles is original. dt-2 extends D-10: a matched
deciding lookup with a role-ambiguous event (attached through a key that the checked evidence also gives as a notice,
in the same record or another, and not resolved by a cited key that tells the work from the notice) is
UNRESOLVED_IDENTITY with
``IDENTIFIER_ROLE_COLLISION`` (``PMID_ROLE_COLLISION`` unchanged for the dt-1 case).

Three layers:

- synthetic Stage 02-shaped observations (LABELED SYNTHETIC keys ``10.5555/rc.*`` / ``91000xx``) decided through the
  production view (``adapters.detector.lookup_view``) and table (``dt1.decide``): the adversarial list of D-071 section
  7, the precedence of section 5 and fail-closed edges;
- real Retraction Watch rows (``fixtures/corrective/rw_role_collision.csv``, 22 attributed records selected by class,
  first in sorted order; an index built from them gives the full index's answer for every query) queried through the
  production LOOKUP adapter (``adapters.lookup.observe``);
- the exposed failed-campaign article ``en-39868218`` run end to end on that index (the historical JASIST unit).

The keys of the real layer are design-exposed after D-071 and recorded in the updated exposure manifest.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from citerift.investigation import dt1
from citerift.investigation.adapters.detector import lookup_view
from citerift.investigation.adapters.lookup import observe
from citerift.investigation.lookup import DEFAULT_LOOKUP_EVIDENCE_BUDGET_BYTES
from citerift.retraction.query import Index

pytestmark = pytest.mark.unit

REPO = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "corrective"
NEW = "IDENTIFIER_ROLE_COLLISION"
SAME_DOI, SAME_PMID = "NOTICE_DOI_EQUALS_ORIGINAL", "NOTICE_PMID_EQUALS_ORIGINAL"
D, P, D2, P2, PX = "10.5555/rc.work", "9100001", "10.5555/rc.notice", "9100002", "9100077"

# Synthetic observations -----------------------------------------------------------------------------------------


def ev(
    eid: str,
    by: str,
    doi: str | None,
    pmid: str | None,
    *,
    etype: str = "retracted",
    via: str | None = None,
    flags: tuple[str, ...] = (),
    notice_doi: str | None = None,
    notice_pmid: str | None = None,
) -> dict[str, Any]:
    return {
        "event_id": eid,
        "event_type": etype,
        "matched_by": by,
        "linked_via": via,
        "original_doi": doi,
        "original_pmid": pmid,
        "notice_doi": notice_doi,
        "notice_pmid": notice_pmid,
        "flags": sorted(flags),
        "issues": [],
    }


def proj(status: str, value: Any, reasons: list[str], groups: list[Any] | None = None) -> dict[str, Any]:
    return {
        "retraction_status": {"status": status, "value": value},
        "retraction_date": None,
        "basis": {"reasons": reasons, "conflict_groups": groups or [], "scope": "checked_sources"},
    }


def vf(value: str = "retracted") -> dict[str, Any]:
    return proj("verified_fact", value, ["SOURCE_RECORDED_TYPE"])


def obs(
    state: str,
    events: list[dict[str, Any]],
    projection: dict[str, Any] | None,
    *,
    notice_hits: int | None = 0,
    issues: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "lookup_state": state,
        "projection": projection,
        "issues": issues or [],
        "checked_sources": [{"source_id": "retraction-watch", "synthetic": True}],
    }
    if notice_hits is not None:
        result["notice_hit_count"] = notice_hits
        result["notice_hits"] = [{"event_id": f"ev-nh-{i}"} for i in range(notice_hits)]
    return {"query": {}, "result": result, "events": events, "event_count": len(events)}


UNAVAILABLE = obs("unavailable", [], proj("unavailable", None, ["INDEX_UNAVAILABLE"]), notice_hits=None)
NOTICE_ONLY = obs(
    "notice_only", [ev("ev-n", "notice", D2, None)], proj("uncertain", None, ["NOTICE_ONLY"]), notice_hits=1
)
NO_RECORD = obs("no_record", [], proj("uncertain", "not_found_in_checked_sources", ["NOT_FOUND_IN_CHECKED_SOURCES"]))


def decide(
    shape: str,
    d: dict[str, Any] | None = None,
    p: dict[str, Any] | None = None,
    q2: dict[str, Any] | None = None,
    *,
    taint: tuple[str, ...] = (),
    keys: tuple[str | None, str | None] = (D, P),
) -> dt1.Outcome:
    roles = [(dt1.Q1_DOI, d), (dt1.Q1_PMID, p), (dt1.Q2, q2)]
    lookups = tuple((r, lookup_view(o)) for r, o in roles if o is not None)
    doi = keys[0] if shape in ("DOI", "PAIR") else None
    pmid = keys[1] if shape in ("PMID", "PAIR") else None
    return dt1.decide(dt1.Candidate("CITED", None, shape, doi, pmid, taint, False, lookups))


def got(out: dt1.Outcome) -> tuple[str, str | None, tuple[str, ...]]:
    return (out.rule, out.cls, out.reasons)


# D-071 section 7: the adversarial list ---------------------------------------------------------------------------


def test_original_only_doi_stays_positive() -> None:
    assert got(decide("DOI", obs("matched", [ev("e1", "doi", D, None, notice_doi=D2)], vf()))) == (
        "D-14",
        "RETRACTED_WORK_CITED",
        (),
    )


def test_notice_only_doi_is_notice_cited() -> None:
    assert got(decide("DOI", NOTICE_ONLY, keys=(D2, None))) == ("D-15", "NOTICE_CITED", ("CITED_IDENTIFIER_IS_NOTICE",))


@pytest.mark.parametrize(
    ("etype", "value"),
    [
        ("retracted", "retracted"),
        ("correction", "correction"),
        ("expression_of_concern", "expression_of_concern"),
        ("reinstated", "reinstated"),
    ],
)
def test_same_doi_as_original_and_notice_abstains(etype: str, value: str) -> None:
    """Retraction, correction notice, EoC notice, reinstatement notice and a withdrawal item: one record gives the DOI
    in both roles (Stage 02 flag NOTICE_DOI_EQUALS_ORIGINAL)."""
    out = decide("DOI", obs("matched", [ev("e1", "doi", D, None, etype=etype, flags=(SAME_DOI,))], vf(value)))
    assert got(out) == ("D-10", "UNRESOLVED_IDENTITY", (NEW,))
    assert out.status == "uncertain" and out.value is None


def test_same_pmid_as_original_and_notice_keeps_the_dt1_reason() -> None:
    issue = {"code": "PMID_ROLE_COLLISION", "event_ids": ["e1"], "distinct_notice_doi": []}
    out = decide("PMID", p=obs("matched", [ev("e1", "pmid", None, P, flags=(SAME_PMID,))], vf(), issues=[issue]))
    assert got(out) == ("D-10", "UNRESOLVED_IDENTITY", ("PMID_ROLE_COLLISION",))


def test_original_doi_with_a_different_notice_doi_stays_positive() -> None:
    out = decide("DOI", obs("matched", [ev("e1", "doi", D, None, notice_doi=D2)], vf()))
    assert out.cls == "RETRACTED_WORK_CITED"


def test_doi_original_with_the_notice_pmid_is_unchanged() -> None:
    """The cited PMID is the notice's (another record's notice key); the event is attached through the DOI only, which
    is not collided, so dt-1's result stands (D-14 with KEY_RESULTS_DIFFER and PAIR_UNCORROBORATED)."""
    e = ev("e1", "doi", D, None, notice_pmid=P)
    q1d = obs("matched", [e], vf())
    q1p = obs(
        "notice_only",
        [ev("e1", "notice", D, None, notice_pmid=P)],
        proj("uncertain", None, ["NOTICE_ONLY"]),
        notice_hits=1,
    )
    q2 = obs("matched", [e], vf(), notice_hits=1)
    assert got(decide("PAIR", q1d, q1p, q2)) == (
        "D-14",
        "RETRACTED_WORK_CITED",
        ("KEY_RESULTS_DIFFER", "PAIR_UNCORROBORATED"),
    )


def test_d058_notice_doi_with_the_original_pmid_is_unchanged() -> None:
    """D-058: notice DOI + the original's PMID, no original DOI recorded: D-14 by the PMID, unchanged."""
    e = ev("e1", "pmid", None, P, notice_doi=D2)
    q1d = obs(
        "notice_only",
        [ev("e1", "notice", None, P, notice_doi=D2)],
        proj("uncertain", None, ["NOTICE_ONLY"]),
        notice_hits=1,
    )
    q1p = obs("matched", [e], vf())
    q2 = obs("matched", [e], vf(), notice_hits=1)
    out = decide("PAIR", q1d, q1p, q2, keys=(D2, P))
    assert got(out) == ("D-14", "RETRACTED_WORK_CITED", ("KEY_RESULTS_DIFFER", "PAIR_UNCORROBORATED"))


def test_record_missing_the_notice_identifier_stays_positive() -> None:
    out = decide("DOI", obs("matched", [ev("e1", "doi", D, None, flags=("NO_NOTICE_IDENTIFIER",))], vf()))
    assert out.cls == "RETRACTED_WORK_CITED"


def test_record_missing_the_original_identifier_is_reached_only_as_a_notice() -> None:
    e = ev("e1", "notice", None, None, notice_doi=D2, flags=("ORIGINAL_ANCHOR_SOURCE_RECORD_ONLY",))
    out = decide(
        "DOI", obs("notice_only", [e], proj("uncertain", None, ["NOTICE_ONLY"]), notice_hits=1), keys=(D2, None)
    )
    assert out.cls == "NOTICE_CITED"


def test_contradictory_source_rows_stay_a_contradiction_with_a_collision() -> None:
    a = ev("e1", "doi", D, None, flags=(SAME_DOI,))
    b = ev("e2", "doi", D, None, etype="correction")
    groups = [
        {"proposition": "p", "types": ["correction", "retracted"], "assertions": ["e1/event_type", "e2/event_type"]}
    ]
    conflicting = proj("conflicting", None, ["SOURCE_TYPE_CONFLICT"], groups)
    conflicting["retraction_status"]["alternatives"] = [{"value": "correction"}, {"value": "retracted"}]
    assert decide("DOI", obs("matched", [a, b], conflicting)).rule == "D-7"


def test_two_records_sharing_one_identifier_in_different_roles_abstain() -> None:
    """The DOI is the original of e1 and the notice of another record (notice_hit_count > 0)."""
    out = decide("DOI", obs("matched", [ev("e1", "doi", D, None, notice_doi=D2)], vf("correction"), notice_hits=1))
    assert got(out) == ("D-10", "UNRESOLVED_IDENTITY", (NEW,))


def test_cross_record_pmid_abstains() -> None:
    out = decide("PMID", p=obs("matched", [ev("e1", "pmid", None, P)], vf(), notice_hits=2))
    assert got(out) == ("D-10", "UNRESOLVED_IDENTITY", (NEW,))


# Independent evidence: a second identifier of the citation that tells the work from the notice ----------------------


def _pair(
    d_flags: tuple[str, ...],
    p_flags: tuple[str, ...] = (),
    d_hits: int = 0,
    p_hits: int = 0,
    *,
    notice_doi: str | None = None,
    notice_pmid: str | None = None,
) -> dt1.Outcome:
    flags = tuple(sorted({*d_flags, *p_flags}))
    e = ev("e1", "doi", D, P, flags=flags, notice_doi=notice_doi, notice_pmid=notice_pmid)
    issues = (
        [{"code": "PMID_ROLE_COLLISION", "event_ids": ["e1"], "distinct_notice_doi": []}] if SAME_PMID in flags else []
    )
    q1d = obs("matched", [e], vf(), notice_hits=d_hits, issues=issues)
    q1p = obs("matched", [{**e, "matched_by": "pmid"}], vf(), notice_hits=p_hits, issues=issues)
    q2 = obs("matched", [e], vf(), notice_hits=d_hits + p_hits, issues=issues)
    return decide("PAIR", q1d, q1p, q2)


def test_a_discriminating_pmid_naming_the_same_event_resolves_a_doi_collision() -> None:
    """The record gives a different notice PMID, so the cited PMID tells the work from the notice."""
    assert got(_pair((SAME_DOI,), notice_pmid=P2)) == ("D-14", "RETRACTED_WORK_CITED", ())


def test_a_clean_pmid_whose_record_states_no_notice_pmid_does_not_resolve() -> None:
    """Absence of a notice PMID is not evidence of the work (reviewer findings A-02, B-02)."""
    assert got(_pair((SAME_DOI,))) == ("D-10", "UNRESOLVED_IDENTITY", (NEW,))


def test_a_discriminating_doi_resolves_a_pmid_collision_as_in_dt1() -> None:
    assert got(_pair((), (SAME_PMID,), notice_doi=D2)) == ("D-14", "RETRACTED_WORK_CITED", ())


def test_a_clean_doi_whose_record_states_no_notice_doi_does_not_resolve_a_pmid_collision() -> None:
    assert got(_pair((), (SAME_PMID,))) == ("D-10", "UNRESOLVED_IDENTITY", (NEW,))


def test_both_identifiers_collided_abstain() -> None:
    assert got(_pair((SAME_DOI,), (SAME_PMID,), notice_doi=D2, notice_pmid=P2)) == (
        "D-10",
        "UNRESOLVED_IDENTITY",
        (NEW,),
    )


def test_a_cross_record_doi_is_resolved_by_a_discriminating_pmid() -> None:
    assert _pair((), d_hits=1, notice_pmid=P2).cls == "RETRACTED_WORK_CITED"
    assert _pair((), d_hits=1).cls == "UNRESOLVED_IDENTITY"


def test_a_same_record_doi_and_a_cross_record_pmid_abstain() -> None:
    assert got(_pair((SAME_DOI,), p_hits=1, notice_pmid=P2)) == ("D-10", "UNRESOLVED_IDENTITY", (NEW,))


def test_a_notice_identifier_that_equals_the_cited_key_never_discriminates() -> None:
    assert _pair((SAME_DOI,), notice_pmid=P).cls == "UNRESOLVED_IDENTITY"


def test_doi_and_pmid_collided_in_two_different_records_abstain() -> None:
    """Reviewer finding B-01: the DOI is both roles in record 1, the PMID both roles in record 2; each event looks
    resolvable by the other key, but a key that some record gives as a notice never resolves (a property of the key)."""
    e1 = ev("e1", "doi", D, P, flags=(SAME_DOI,), notice_pmid=P2)
    e2 = ev("e2", "pmid", D, P, etype="correction", flags=(SAME_PMID,), notice_doi=D2)
    q1d = obs("matched", [e1, {**e2, "matched_by": "doi"}], vf())
    q1p = obs("matched", [{**e1, "matched_by": "pmid"}, e2], vf())
    q2 = obs("matched", [e1], vf())
    assert got(decide("PAIR", q1d, q1p, q2)) == ("D-10", "UNRESOLVED_IDENTITY", (NEW,))


def test_a_non_cited_bridge_key_never_resolves_a_collided_cited_key() -> None:
    """Reviewer finding A-01: only an identifier the citation carries can resolve; a bridged event attached through a
    collided cited DOI stays ambiguous even when its own PMID (not cited) is clean and discriminating."""
    direct = ev("e1", "doi", D, None, notice_doi=D2)
    bridged = ev("e2", "pmid", D, PX, via="pmid_cooccurrence", flags=(SAME_DOI,), notice_pmid=P2)
    out = decide("DOI", obs("matched", [direct, bridged], vf()))
    assert got(out) == ("D-10", "UNRESOLVED_IDENTITY", (NEW,))


def test_malformed_event_flags_fail_closed() -> None:
    e = ev("e1", "doi", D, None, notice_doi=D2)
    for bad in ("NOTICE_DOI_EQUALS_ORIGINAL", None, [1]):
        assert decide("DOI", obs("matched", [{**e, "flags": bad}], vf())).cls == "UNRESOLVED_IDENTITY"


def test_a_bridged_event_attached_through_a_collided_doi_abstains() -> None:
    """PMID query: Stage 02 bridges every other record of the co-occurring DOI (doi_cooccurrence); that DOI is the
    bridged event's notice identifier too, so the bridged support is role-ambiguous."""
    direct = ev("e1", "pmid", "10.5555/rc.bridge", P)
    bridged = ev("e2", "doi", "10.5555/rc.bridge", None, via="doi_cooccurrence", flags=(SAME_DOI,))
    out = decide("PMID", p=obs("matched", [direct, bridged], vf()))
    assert got(out) == ("D-10", "UNRESOLVED_IDENTITY", (NEW,))


# Precedence (D-071 section 5) -------------------------------------------------------------------------------------

COLLIDED = [ev("e1", "doi", D, None, flags=(SAME_DOI,))]


def test_taint_precedes_the_collision() -> None:
    assert decide("DOI", obs("matched", COLLIDED, vf()), taint=("IDENTIFIER_MALFORMED",)).rule == "D-8"


def test_an_identity_witness_precedes_the_collision() -> None:
    w = ev("e1", "doi", D, "9100099", flags=(SAME_DOI,))
    q1d = obs("matched", [w], vf())
    q1p = obs("matched", [ev("e2", "pmid", None, P)], vf())
    q2 = obs("ambiguous_identity", [w, ev("e2", "pmid", None, P)], proj("uncertain", None, ["IDENTITY_AMBIGUOUS"]))
    assert decide("PAIR", q1d, q1p, q2).rule == "D-6"


def test_the_collision_precedes_an_unavailable_lookup() -> None:
    """Unresolved identity precedes operational failure, as dt-1's PMID collision already does."""
    q2 = obs("matched", COLLIDED, vf())
    assert got(decide("PAIR", obs("matched", COLLIDED, vf()), UNAVAILABLE, q2)) == (
        "D-10",
        "UNRESOLVED_IDENTITY",
        (NEW, "KEY_RESULTS_DIFFER"),
    )


def test_the_collision_precedes_an_uncertain_status() -> None:
    unc = proj("uncertain", None, ["MIXED_CURRENT_EFFECT"])
    assert got(decide("DOI", obs("matched", COLLIDED, unc))) == ("D-10", "UNRESOLVED_IDENTITY", (NEW,))


def test_bridge_only_and_collision_reasons_are_both_kept() -> None:
    bridge = proj("uncertain", None, ["BRIDGE_ONLY_SUPPORT", "BRIDGED_EVIDENCE_MATERIAL"])
    out = decide("DOI", obs("matched", COLLIDED, bridge))
    assert got(out) == ("D-10", "UNRESOLVED_IDENTITY", ("BRIDGE_ONLY_SUPPORT", NEW))


def test_a_collision_never_gives_notice_cited_or_a_negative() -> None:
    for etype in ("retracted", "correction", "expression_of_concern", "reinstated"):
        out = decide("DOI", obs("matched", [ev("e1", "doi", D, None, etype=etype, flags=(SAME_DOI,))], vf(etype)))
        assert out.cls == "UNRESOLVED_IDENTITY" and out.cls != "NOTICE_CITED" and out.value is None


def test_a_matched_deciding_lookup_without_notice_hit_evidence_fails_closed() -> None:
    """Stage 02 always renders notice_hit_count; an observation without it cannot show the key is not a notice."""
    out = decide("DOI", obs("matched", [ev("e1", "doi", D, None)], vf(), notice_hits=None))
    assert got(out) == ("D-10", "UNRESOLVED_IDENTITY", (NEW,))


def test_a_flag_on_an_event_not_attached_through_it_is_ignored() -> None:
    """A DOI query's event bridged by PMID co-occurrence carries a same-DOI flag about its own DOI, which the citation
    does not cite and through which the event is not attached: no role collision of a key the support depends on."""
    direct = ev("e1", "doi", D, PX)
    bridged = ev("e2", "pmid", "10.5555/rc.other", PX, via="pmid_cooccurrence", flags=(SAME_DOI,))
    assert decide("DOI", obs("matched", [direct, bridged], vf())).cls == "RETRACTED_WORK_CITED"


# Real Retraction Watch rows --------------------------------------------------------------------------------------

MANIFEST = json.loads((FIXTURES / "rw_role_collision.json").read_text(encoding="utf-8"))
CLASSES: dict[str, dict[str, str | None]] = MANIFEST["classes"]

# Expected dt-2 outcome per class (rule, class, reasons) and the frozen dt-1 rule for the record.
EXPECTED: dict[str, tuple[str, str, tuple[str, ...], str]] = {
    "jasist_failure": ("D-10", "UNRESOLVED_IDENTITY", (NEW,), "D-14"),
    "same_doi_retracted": ("D-10", "UNRESOLVED_IDENTITY", (NEW,), "D-14"),
    "same_doi_correction": ("D-10", "UNRESOLVED_IDENTITY", (NEW,), "D-11"),
    "same_doi_expression_of_concern": ("D-10", "UNRESOLVED_IDENTITY", (NEW,), "D-14"),
    "same_doi_reinstated": ("D-10", "UNRESOLVED_IDENTITY", (NEW,), "D-11"),
    # Record A gives the PMID both roles (dt-1's PMID_ROLE_COLLISION names it); record B's event is attached through
    # the same PMID, so it is role-ambiguous too (the collision is a property of the key): both reasons.
    "same_pmid": ("D-10", "UNRESOLVED_IDENTITY", (NEW, "PMID_ROLE_COLLISION"), "D-10"),
    "cross_record_doi": ("D-10", "UNRESOLVED_IDENTITY", (NEW,), "D-14"),
    "cross_record_pmid": ("D-10", "UNRESOLVED_IDENTITY", (NEW,), "D-14"),
    "same_doi_with_clean_pmid_pair": ("D-10", "UNRESOLVED_IDENTITY", (NEW,), "D-14"),
    "same_doi_with_discriminating_pmid_pair": ("D-14", "RETRACTED_WORK_CITED", (), "D-14"),
    "same_pmid_with_clean_doi_pair": ("D-10", "UNRESOLVED_IDENTITY", (NEW,), "D-14"),
    "same_pmid_with_discriminating_doi_pair": ("D-14", "RETRACTED_WORK_CITED", (), "D-14"),
    "doi_and_pmid_collided_in_two_records_pair": ("D-10", "UNRESOLVED_IDENTITY", (NEW,), "D-14"),
    "same_doi_with_clean_pmid_doi_only": ("D-10", "UNRESOLVED_IDENTITY", (NEW,), "D-14"),
    "both_schemes_equal_pair": ("D-10", "UNRESOLVED_IDENTITY", (NEW,), "D-14"),
    "no_notice_identifier": ("D-14", "RETRACTED_WORK_CITED", (), "D-14"),
    "no_original_identifier_notice_doi": ("D-15", "NOTICE_CITED", ("CITED_IDENTIFIER_IS_NOTICE",), "D-15"),
    "original_with_distinct_notice_doi": ("D-14", "RETRACTED_WORK_CITED", (), "D-14"),
    "original_with_distinct_notice_doi_notice_side": (
        "D-15",
        "NOTICE_CITED",
        ("CITED_IDENTIFIER_IS_NOTICE",),
        "D-15",
    ),
    "doi_original_pmid_notice_pair": (
        "D-14",
        "RETRACTED_WORK_CITED",
        ("KEY_RESULTS_DIFFER", "PAIR_UNCORROBORATED"),
        "D-14",
    ),
    "contradictory_source_rows": ("D-7", "CONTRADICTION_IN_SOURCES", ("RETRACTION_EVENT_TYPE_CONFLICT",), "D-7"),
}


def _build_index(tmp: Path) -> Path:
    from citerift.retraction.source import load_receipt, parse_receipt
    from citerift.retraction.store import build

    data = (FIXTURES / MANIFEST["fixture"]).read_bytes()
    assert MANIFEST["subset_equals_full_index"] and MANIFEST["synthetic_rows"] == 0
    assert hashlib.sha256(data).hexdigest() == MANIFEST["fixture_sha256"]
    tmp.mkdir(parents=True, exist_ok=True)
    path = tmp / MANIFEST["fixture"]
    path.write_bytes(data)
    fields = load_receipt().to_json()
    fields.update(
        path=MANIFEST["fixture"],
        expected_bytes=len(data),
        expected_sha256=MANIFEST["fixture_sha256"],
        git_blob_sha1=hashlib.sha1(f"blob {len(data)}\0".encode() + data, usedforsecurity=False).hexdigest(),
        attribution=MANIFEST["attribution"],
    )
    return build(path, parse_receipt(fields), tmp / "index").index_path


@pytest.fixture(scope="module")
def rc_index(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Path]:
    yield _build_index(tmp_path_factory.mktemp("rwrc"))


def real_decide(index_path: Path, doi: str | None, pmid: str | None) -> dt1.Outcome:
    with Index(index_path) as index:

        def look(d: str | None, p: str | None) -> dict[str, Any]:
            return observe(index, {}, d, p, DEFAULT_LOOKUP_EVIDENCE_BUDGET_BYTES)

        if doi and pmid:
            return decide("PAIR", look(doi, None), look(None, pmid), look(doi, pmid), keys=(doi, pmid))
        if doi:
            return decide("DOI", look(doi, None), keys=(doi, None))
        return decide("PMID", p=look(None, pmid), keys=(None, pmid))


def test_every_adversarial_class_has_a_real_query() -> None:
    assert set(CLASSES) == set(EXPECTED)


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_real_rows(rc_index: Path, name: str) -> None:
    q = CLASSES[name]
    rule, cls, reasons, _ = EXPECTED[name]
    assert got(real_decide(rc_index, q["doi"], q["pmid"])) == (rule, cls, reasons), name


@pytest.mark.integration
def test_the_jasist_record_is_the_failed_unit(rc_index: Path) -> None:
    """Record ID 40120 (ev ordinal 33558 in the full snapshot): OriginalPaperDOI = RetractionDOI = 10.1002/asi.23238."""
    with Index(rc_index) as index:
        o = observe(index, {}, "10.1002/asi.23238", None, DEFAULT_LOOKUP_EVIDENCE_BUDGET_BYTES)
    assert [(e["record_id"], e["event_type"], e["flags"]) for e in o["events"]] == [("40120", "retracted", [SAME_DOI])]
    assert o["result"]["identifier_role"] == "original" and o["result"]["notice_hit_count"] == 0


# The failed-campaign article, end to end -------------------------------------------------------------------------

EN_JASIST = REPO / "docs/verification/stage-04/evaluation-campaign/bundles/en-39868218"


@pytest.mark.integration
def test_historical_jasist_unit_end_to_end(tmp_path: Path, rc_index: Path) -> None:
    """The exposed campaign article en-39868218 (development evidence after D-071), run through the controller on the
    real-row index: the unit citing 10.1002/asi.23238 alone is UNRESOLVED_IDENTITY, the claim validates, the run
    completes and verifies."""
    import test_step9_real as T9

    run = T9.Run(tmp_path, EN_JASIST, rc_index)
    assert run.result.status == "COMPLETED"
    T9._verified(run)
    claims = [c for c in run.claims() if [k["normalized"] for k in c["candidate"]["keys"]] == ["10.1002/asi.23238"]]
    assert len(claims) == 1
    c = claims[0]
    assert (c["class"], c["rule"], c["status"], c["value"], c["reasons"]) == (
        "UNRESOLVED_IDENTITY",
        "D-10",
        "uncertain",
        None,
        [NEW],
    )
    assert not [x for x in run.claims() if x["status"] == "verified_fact" and "10.1002/asi.23238" in json.dumps(x)]
