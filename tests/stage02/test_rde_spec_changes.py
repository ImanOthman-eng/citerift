"""Changes made to the frozen specification while implementing it (SPECIFICATION.md 16, items 2, 4, 5, 23 and 26)."""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

import pytest
import rde_support as S

from citerift.retraction import policy, store, tension
from citerift.retraction.query import Index, lookup
from citerift.retraction.store import IndexUnavailable, open_index


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


@pytest.mark.negative
@pytest.mark.parametrize(
    "earlier", ["citerift-rde-policy/1.0.0", "citerift-rde-policy/1.1.0", "citerift-rde-policy/1.2.0"]
)
def test_rde_index_of_another_policy_version_is_refused(tmp_path: Path, earlier: str) -> None:
    """Items 23, 26 and 29: the policy rules changed after freezing (1.1.0), for R-026 (1.2.0) and for the
    audit fix F1 (1.3.0), so an index built under an earlier policy must not be read as the current one."""
    assert policy.POLICY_VERSION == "citerift-rde-policy/1.3.0"
    assert store.POLICY_VERSION == policy.POLICY_VERSION
    idx = S.build_rows(tmp_path, [_retraction("1", OriginalPaperDOI="10.5555/one")])
    old = tmp_path / "old" / idx.name
    old.parent.mkdir()
    shutil.copy(idx, old)
    conn = sqlite3.connect(old)
    conn.execute("UPDATE meta SET value = ? WHERE key = 'policy_version'", (earlier,))
    conn.commit()
    conn.close()
    with pytest.raises(IndexUnavailable) as exc:
        open_index(old)
    assert exc.value.code == "INDEX_FORMAT_MISMATCH"
    status = lookup(old, "10.5555/one")["projection"]["retraction_status"]
    assert (status["status"], status["value"]) == ("unavailable", None)
