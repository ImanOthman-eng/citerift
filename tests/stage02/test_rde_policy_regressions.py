"""Policy regressions found after the specification was frozen (SPECIFICATION.md 16)."""

from __future__ import annotations

from pathlib import Path

import pytest
import rde_support as S

from citerift.retraction import tension
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
