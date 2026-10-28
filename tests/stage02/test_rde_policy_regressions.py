"""Policy regressions found after the specification was frozen (SPECIFICATION.md 16)."""

from __future__ import annotations

from pathlib import Path

import pytest
import rde_support as S

from citerift.retraction import policy, tension
from citerift.retraction.query import Index, lookup


def _rows(second_date: str) -> list[dict[str, str]]:
    return [
        S.row(
            **{
                "Record ID": "1",
                "RetractionNature": "Retraction",
                "OriginalPaperDOI": "10.5555/o",
                "RetractionDOI": "10.5555/n2015",
                "RetractionDate": "7/24/2015 0:00",
            }
        ),
        S.row(
            **{
                "Record ID": "2",
                "RetractionNature": "Retraction",
                "OriginalPaperDOI": "10.5555/o",
                "RetractionDOI": "10.5555/n2017",
                "RetractionDate": second_date,
            }
        ),
    ]


PUBLISHER_CALLS_2015_A_CORRECTION = [
    {"original": "10.5555/o", "updated_by": [{"DOI": "10.5555/n2015", "type": "correction", "source": "publisher"}]}
]


@pytest.mark.regression
def test_rde_date_is_not_settled_by_a_type_conflict(tmp_path: Path) -> None:
    """C-9, found on 10.1007/s13277-014-2995-5: a publisher deposit typing one RW retraction notice as a
    correction must not make the other notice's date a verified fact."""
    idx = S.build_rows(tmp_path, _rows("4/20/2017 0:00"), PUBLISHER_CALLS_2015_A_CORRECTION)
    out = lookup(idx, "10.5555/o")
    proj = out["projection"]
    assert proj["retraction_status"]["value"] == "retracted"
    assert proj["retraction_date"]["status"] == "uncertain" and proj["retraction_date"]["value"] is None
    assert "MULTIPLE_RETRACTION_DATES" in proj["basis"]["reasons"]
    assert "CONFLICT_NOT_MATERIAL" in proj["basis"]["reasons"]
    with Index(idx) as ix:
        rep = tension.report(ix.gather("10.5555/o"), ix.snapshot_id)
    excl = next(
        r for r in rep["interventions"] if r["intervention"] == "exclude_origin" and r["origins"] == ["publisher"]
    )
    assert "retraction_date.status" not in excl["changed_fields"]  # the date no longer rests on the publisher


@pytest.mark.regression
def test_rde_equal_dates_survive_a_type_conflict(tmp_path: Path) -> None:
    rows = _rows("7/24/2015 0:00")
    idx = S.build_rows(tmp_path, rows, PUBLISHER_CALLS_2015_A_CORRECTION)
    date = lookup(idx, "10.5555/o")["projection"]["retraction_date"]
    assert date["status"] == "verified_fact" and date["value"] == "2015-07-24"


def _event(record_id: str, nature: str, date: str, **values: str) -> dict[str, str]:
    return S.row(**{"Record ID": record_id, "RetractionNature": nature, "RetractionDate": date} | values)


@pytest.mark.regression
@pytest.mark.parametrize(
    ("first", "second"),
    [
        (("Expression of concern", "7/2/2019 0:00"), ("Retraction", "11/22/2019 0:00")),
        (("Correction", "3/15/2016 0:00"), ("Retraction", "5/9/2018 0:00")),
        (("Retraction", "5/9/2018 0:00"), ("Correction", "3/15/2020 0:00")),
    ],
)
def test_rde_ordered_events_on_one_notice_are_a_sequence(
    tmp_path: Path, first: tuple[str, str], second: tuple[str, str]
) -> None:
    """C-12, found by the scientific review on 10.1038/nature16193: RW records an expression of concern or a
    correction and a later retraction under one notice DOI. A concern followed by a retraction is not a
    conflict, and a later correction does not undo a retraction (directive section 9)."""
    shared = {"OriginalPaperDOI": "10.5555/o", "RetractionDOI": "10.5555/n"}
    rows = [_event("1", *first, **shared), _event("2", *second, **shared)]
    proj = lookup(S.build_rows(tmp_path, rows), "10.5555/o")["projection"]
    assert (proj["retraction_status"]["status"], proj["retraction_status"]["value"]) == ("verified_fact", "retracted")
    assert "SEQUENTIAL_EVENTS_SHARE_NOTICE" in proj["basis"]["reasons"]
    assert proj["basis"]["conflict_groups"] == []


@pytest.mark.regression
@pytest.mark.parametrize("dates", [("3/12/2015 0:00", "3/12/2015 0:00"), ("7/1/2019 0:00", "11/1/2019 0:00")])
def test_rde_unordered_events_on_one_notice_stay_a_conflict(tmp_path: Path, dates: tuple[str, str]) -> None:
    """Equal dates, or day-1 dates whose order is not established, keep the frozen P20 conflict."""
    shared = {"OriginalPaperDOI": "10.5555/o", "RetractionDOI": "10.5555/n"}
    rows = [_event("1", "Expression of concern", dates[0], **shared), _event("2", "Retraction", dates[1], **shared)]
    proj = lookup(S.build_rows(tmp_path, rows), "10.5555/o")["projection"]
    assert proj["retraction_status"]["status"] == "conflicting"
    assert "SEQUENTIAL_EVENTS_SHARE_NOTICE" not in proj["basis"]["reasons"]


@pytest.mark.regression
def test_rde_publisher_disagreement_on_an_ordered_sequence_is_still_a_conflict(tmp_path: Path) -> None:
    shared = {"OriginalPaperDOI": "10.5555/o", "RetractionDOI": "10.5555/n"}
    rows = [_event("1", "Expression of concern", "7/2/2019 0:00", **shared)]
    rows.append(_event("2", "Retraction", "11/22/2019 0:00", **shared))
    deposit = [
        {"original": "10.5555/o", "updated_by": [{"DOI": "10.5555/n", "type": "correction", "source": "publisher"}]}
    ]
    proj = lookup(S.build_rows(tmp_path, rows, deposit), "10.5555/o")["projection"]
    assert proj["retraction_status"]["status"] == "conflicting"


@pytest.mark.regression
def test_rde_sole_reinstatement_is_unlinked(tmp_path: Path) -> None:
    """C-11 (frozen case P04 amended): a reinstatement that names no superseded event sets no current effect."""
    rows = [_event("1", "Reinstatement", "3/12/2015 0:00", OriginalPaperDOI="10.5555/o", RetractionDOI="10.5555/r")]
    status = lookup(S.build_rows(tmp_path, rows), "10.5555/o")["projection"]["retraction_status"]
    assert (status["status"], status["value"]) == ("uncertain", None)
    assert "supersedes" in status["reason"]


@pytest.mark.regression
def test_rde_proposition_includes_the_anchor(tmp_path: Path) -> None:
    """C-13: SPECIFICATION.md 11.1 rule 7 groups by (notice key, original anchor). A bridged PMID-only
    retraction sharing a notice key with the DOI's own correction is a different proposition, so there is no
    conflict group. Since C-25 (rule 7f, R-026) that bridged retraction no longer gives a verified retraction:
    it is the only retraction, so the result is uncertain (until 1.2.0 this test expected verified_fact)."""
    rows = [
        _event(
            "1",
            "Correction",
            "3/12/2015 0:00",
            OriginalPaperDOI="10.5555/o",
            OriginalPaperPubMedID="77",
            RetractionDOI="10.5555/n",
        ),
        _event("2", "Retraction", "3/12/2015 0:00", OriginalPaperPubMedID="77", RetractionDOI="10.5555/n"),
    ]
    idx = S.build_rows(tmp_path, rows)
    out = lookup(idx, "10.5555/o")
    assert out["identity"]["status"] == "bridged"
    status = out["projection"]["retraction_status"]
    assert (status["status"], status["value"]) == ("uncertain", None)
    assert "BRIDGE_ONLY_SUPPORT" in out["projection"]["basis"]["reasons"]
    # The grouping itself (rules 1 to 7e, the bridged record taken as it is): two propositions, no conflict.
    with Index(idx) as ix:
        es = ix.gather("10.5555/o").evidence_set
    assert es is not None
    full = policy._reduce(es)
    assert full["basis"]["conflict_groups"] == []
    assert (full["retraction_status"]["status"], full["retraction_status"]["value"]) == ("verified_fact", "retracted")


@pytest.mark.regression
def test_rde_unknown_origin_alone_does_not_establish_a_value(tmp_path: Path) -> None:
    """C-14: a retraction supported only by a relation of unknown origin is uncertain (INV-P1)."""
    rows = [_event("1", "Correction", "3/12/2015 0:00", OriginalPaperDOI="10.5555/o", RetractionDOI="10.5555/c")]
    unlabeled = [{"original": "10.5555/o", "updated_by": [{"DOI": "10.5555/r", "type": "retraction"}]}]
    proj = lookup(S.build_rows(tmp_path, rows, unlabeled), "10.5555/o")["projection"]
    assert (proj["retraction_status"]["status"], proj["retraction_status"]["value"]) == ("uncertain", None)
    assert "SUPPORT_ORIGIN_UNKNOWN" in proj["basis"]["reasons"]
