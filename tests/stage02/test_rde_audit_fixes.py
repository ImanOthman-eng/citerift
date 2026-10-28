"""Fixes F1 and F3 of the independent Stage 02 audit (owner authorization of 2026-10-28; SPECIFICATION.md 16
items 27 and 28).

F1: a PMID-only query reached the records of its co-occurring DOI only when they carried no PMID; records of
that DOI under a different PMID were dropped without a trace, so the PMID query could state a correction as a
verified fact for a work whose DOI is retracted (real case: PMID 23649173). They are now bridged candidates
(``doi_cooccurrence``) under rule 7f with the issue ``IDENTITY_SECONDARY_DIVERGENT``, as the DOI query already
reports it.

F3: a record whose original PMID equals its notice PMID cannot say which of the two works the PMID names; the
lookup now reports ``PMID_ROLE_COLLISION`` (an issue only: no value changes).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import rde_support as S

from citerift.retraction import schemas
from citerift.retraction.query import lookup

D, P, P2 = "10.5555/w", "4242", "5353"


def _event(record_id: str, nature: str, notice: str, date: str, **values: str) -> dict[str, str]:
    return S.row(
        **{"Record ID": record_id, "RetractionNature": nature, "RetractionDOI": notice, "RetractionDate": date} | values
    )


def _look(idx: Path, doi: str | None, pmid: str | None) -> dict[str, Any]:
    out = lookup(idx, doi, pmid, page_size=100)
    assert schemas.validate_lookup(out) == []
    return out


def _status(out: dict[str, Any]) -> tuple[Any, ...]:
    proj = out["projection"]
    date = proj["retraction_date"] or {}
    return (proj["retraction_status"]["status"], proj["retraction_status"]["value"], date.get("status"))


def _issues(out: dict[str, Any], code: str) -> list[dict[str, Any]]:
    return [i for i in out["issues"] if i["code"] == code]


# F1 --------------------------------------------------------------------------------------------------------------


def _divergent(tmp: Path) -> Path:
    """The shape of PMID 23649173: RW records a correction under (D, P) and the retraction of D under another
    PMID, P2."""
    rows = [
        _event("1", "Correction", "10.5555/n-c", "5/6/2013 0:00", OriginalPaperDOI=D, OriginalPaperPubMedID=P),
        _event("2", "Retraction", "10.5555/n-r", "9/19/2018 0:00", OriginalPaperDOI=D, OriginalPaperPubMedID=P2),
    ]
    return S.build_rows(tmp, rows)


@pytest.mark.regression
def test_rde_pmid_query_does_not_state_a_correction_for_a_retracted_doi(tmp_path: Path) -> None:
    out = _look(_divergent(tmp_path), None, P)
    assert out["lookup_state"] == "matched"
    assert _status(out)[:2] == ("uncertain", None)
    assert "BRIDGED_EVIDENCE_MATERIAL" in out["projection"]["basis"]["reasons"]
    assert out["identity"]["status"] == "bridged"
    # The record under the other PMID is listed as a bridged candidate, and the divergence is reported.
    assert {e["record_id"]: e["linked_via"] for e in out["events"]} == {"1": None, "2": "doi_cooccurrence"}
    [issue] = _issues(out, "IDENTITY_SECONDARY_DIVERGENT")
    assert issue["pmids"] == sorted([P, P2])
    assert out["projection"]["basis"]["bridged_assertions"]


@pytest.mark.regression
def test_rde_divergence_is_reported_from_both_query_directions(tmp_path: Path) -> None:
    """The DOI query keeps its DOI-first answer (both records are the DOI's own), and both directions now report
    the same divergence."""
    idx = _divergent(tmp_path)
    by_doi = _look(idx, D, None)
    assert _status(by_doi)[:2] == ("verified_fact", "retracted")
    for out in (by_doi, _look(idx, None, P), _look(idx, None, P2)):
        [issue] = _issues(out, "IDENTITY_SECONDARY_DIVERGENT")
        assert issue["pmids"] == sorted([P, P2])


@pytest.mark.regression
def test_rde_divergent_record_that_agrees_does_not_withhold_the_answer(tmp_path: Path) -> None:
    """Adequate direct support keeps its conclusion: a record of the DOI under another PMID that says the same
    thing is listed, not counted."""
    rows = [
        _event("1", "Retraction", "10.5555/n-r", "9/19/2018 0:00", OriginalPaperDOI=D, OriginalPaperPubMedID=P),
        _event("2", "Retraction", "10.5555/n-r", "9/19/2018 0:00", OriginalPaperDOI=D, OriginalPaperPubMedID=P2),
    ]
    out = _look(S.build_rows(tmp_path, rows), None, P)
    assert _status(out) == ("verified_fact", "retracted", "verified_fact")
    basis = out["projection"]["basis"]
    assert "BRIDGED_EVIDENCE_NOT_COUNTED" in basis["reasons"]
    assert len(basis["supporting_assertions"]) == 1
    assert _issues(out, "IDENTITY_SECONDARY_DIVERGENT")


@pytest.mark.regression
def test_rde_pmid_query_without_divergence_is_unchanged(tmp_path: Path) -> None:
    rows = [
        _event("1", "Correction", "10.5555/n-c", "5/6/2013 0:00", OriginalPaperDOI=D, OriginalPaperPubMedID=P),
        _event("2", "Correction", "10.5555/n-c2", "5/6/2014 0:00", OriginalPaperDOI=D, OriginalPaperPubMedID=P),
    ]
    out = _look(S.build_rows(tmp_path, rows), None, P)
    assert out["identity"]["status"] == "exact"
    assert _status(out)[:2] == ("verified_fact", "correction")
    assert not _issues(out, "IDENTITY_SECONDARY_DIVERGENT")


@pytest.mark.regression
def test_rde_two_identifier_query_with_divergent_pmid_stays_ambiguous(tmp_path: Path) -> None:
    """Step 5 already refuses the union: (D, P) is incompatible with the record (D, P2)."""
    out = _look(_divergent(tmp_path), D, P)
    assert out["lookup_state"] == "ambiguous_identity"
    assert out["projection"]["retraction_status"]["status"] == "uncertain"


# F3 --------------------------------------------------------------------------------------------------------------


def _collision_rows(notice_doi: str) -> list[dict[str, str]]:
    return [
        _event(
            "1",
            "Retraction",
            notice_doi,
            "2/23/2026 0:00",
            OriginalPaperDOI=D,
            OriginalPaperPubMedID=P,
            RetractionPubMedID=P,
        )
    ]


@pytest.mark.regression
@pytest.mark.parametrize("key", [(D, None), (None, P)])
def test_rde_pmid_role_collision_is_reported_without_changing_the_value(tmp_path: Path, key: tuple[Any, Any]) -> None:
    out = _look(S.build_rows(tmp_path / "c", _collision_rows("10.5555/n-r")), *key)
    [issue] = _issues(out, "PMID_ROLE_COLLISION")
    [event] = out["events"]
    assert issue["event_ids"] == [event["event_id"]]
    # The notice has a DOI of its own, different from the original's: the PMID more likely names the notice.
    assert issue["distinct_notice_doi"] == [event["event_id"]]
    plain = _event("1", "Retraction", "10.5555/n-r", "2/23/2026 0:00", OriginalPaperDOI=D, OriginalPaperPubMedID=P)
    reference = _look(S.build_rows(tmp_path / "p", [plain]), *key)
    # The same value, date and reasons as the record without the collision (provenance differs: another row).
    assert _status(out) == _status(reference) == ("verified_fact", "retracted", "verified_fact")
    assert out["projection"]["retraction_date"]["value"] == reference["projection"]["retraction_date"]["value"]
    assert out["projection"]["basis"]["reasons"] == reference["projection"]["basis"]["reasons"]


@pytest.mark.regression
def test_rde_pmid_role_collision_without_a_notice_doi(tmp_path: Path) -> None:
    out = _look(S.build_rows(tmp_path, _collision_rows("")), None, P)
    [issue] = _issues(out, "PMID_ROLE_COLLISION")
    assert issue["distinct_notice_doi"] == []
    assert len(issue["event_ids"]) == 1


@pytest.mark.regression
def test_rde_no_role_collision_issue_for_distinct_pmids(tmp_path: Path) -> None:
    rows = [
        _event(
            "1",
            "Retraction",
            "10.5555/n-r",
            "2/23/2026 0:00",
            OriginalPaperDOI=D,
            OriginalPaperPubMedID=P,
            RetractionPubMedID=P2,
        )
    ]
    assert not _issues(_look(S.build_rows(tmp_path, rows), None, P), "PMID_ROLE_COLLISION")
