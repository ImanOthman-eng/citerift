"""Changes made to the frozen specification while implementing it (SPECIFICATION.md 16, items 2, 4 and 5)."""

from __future__ import annotations

from pathlib import Path

import pytest
import rde_support as S

from citerift.retraction import tension
from citerift.retraction.query import Index, lookup


def _retraction(record_id: str, **values: str) -> dict[str, str]:
    return S.row(
        **{"Record ID": record_id, "RetractionNature": "Retraction", "RetractionDate": "3/1/2020 0:00"} | values
    )


@pytest.mark.unit
def test_rde_no_record_has_no_date_assertion(tmp_path: Path) -> None:
    idx = S.build_rows(tmp_path, [_retraction("1", OriginalPaperDOI="10.5555/present")])
    out = lookup(idx, "10.5555/absent")
    assert out["lookup_state"] == "no_record"
    proj = out["projection"]
    assert proj["retraction_status"]["value"] == "not_found_in_checked_sources"
    assert proj.get("retraction_date") is None


@pytest.mark.unit
def test_rde_query_pair_links_only_when_the_doi_names_events(tmp_path: Path) -> None:
    rows = [
        _retraction("1", OriginalPaperDOI="10.5555/d", OriginalPaperPubMedID="11"),
        _retraction("2", OriginalPaperPubMedID="11"),
        _retraction("3", OriginalPaperPubMedID="22"),
    ]
    idx = S.build_rows(tmp_path, rows)
    paired = lookup(idx, "10.5555/d", "11", page_size=100)
    assert paired["identity"]["status"] == "bridged"
    assert {e["record_id"]: e["linked_via"] for e in paired["events"]} == {"1": None, "2": "query_pair"}
    # The DOI names no event: the PMID-only event is matched by its PMID, with no link through the pairing.
    unpaired = lookup(idx, "10.5555/unknown", "22", page_size=100)
    assert unpaired["lookup_state"] == "matched"
    assert unpaired["identity"]["status"] == "exact"
    assert [(e["record_id"], e["matched_by"], e["linked_via"]) for e in unpaired["events"]] == [("3", "pmid", None)]
    assert unpaired["identity"]["anchor"] == "pmid:22"  # C-10: no event carries the query's DOI


@pytest.mark.unit
def test_rde_single_origin_has_no_exclude_origin_step(tmp_path: Path) -> None:
    idx = S.build_rows(tmp_path, [_retraction("1", OriginalPaperDOI="10.5555/one")])
    with Index(idx) as ix:
        rep = tension.report(ix.gather("10.5555/one"), ix.snapshot_id)
    assert rep["single_origin"] is True
    assert "exclude_origin" not in {r["intervention"] for r in rep["interventions"]}
    two = [
        {"original": "10.5555/one", "updated_by": [{"DOI": "10.5555/n", "type": "retraction", "source": "publisher"}]}
    ]
    idx2 = S.build_rows(tmp_path / "two", [_retraction("1", OriginalPaperDOI="10.5555/one")], two)
    with Index(idx2) as ix:
        rep2 = tension.report(ix.gather("10.5555/one"), ix.snapshot_id)
    assert rep2["single_origin"] is False
    excluded = sorted(tuple(r["origins"]) for r in rep2["interventions"] if r["intervention"] == "exclude_origin")
    assert excluded == [("publisher",), ("retraction-watch",)]
