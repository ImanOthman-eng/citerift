"""Lookup contract, paging, unavailability, offline operation and the CLI (SPECIFICATION.md 10.2, 10.3;
directive section 14 items 10 and 15, and the page-size metamorphic property)."""

from __future__ import annotations

import json
import socket
import sqlite3
from pathlib import Path
from typing import Any

import pytest
import rde_support as S

from citerift.retraction import cli, schemas, tension
from citerift.retraction.export import export, verify
from citerift.retraction.query import MAX_PAGE, MAX_RELEVANCE_LISTED, Index, QueryError, event_detail, lookup, render


def _fanout(tmp: Path, n: int = 45) -> Path:
    rows = [
        S.row(
            **{
                "Record ID": str(i),
                "RetractionNature": "Correction",
                "OriginalPaperDOI": "10.5555/many",
                "RetractionDOI": f"10.5555/n{i}",
                "RetractionDate": f"3/{2 + i % 27}/2015 0:00",
            }
        )
        for i in range(n)
    ]
    rows.append(S.row(**{"Record ID": "999", "RetractionNature": "Retraction", "OriginalPaperDOI": "10.5555/solo"}))
    return S.build_rows(tmp, rows)


@pytest.mark.integration
def test_rde_paging_never_changes_counts_projection_or_digest(tmp_path: Path) -> None:
    idx = _fanout(tmp_path)
    full = lookup(idx, "10.5555/many", page_size=MAX_PAGE)
    assert full["total_event_count"] == 45 and len(full["events"]) == 45
    for size in (1, 7, 20, 44):
        seen: list[str] = []
        cursor = None
        while True:
            page = lookup(idx, "10.5555/MANY", page_size=size, cursor=cursor)
            assert schemas.validate_lookup(page) == []
            assert page["total_event_count"] == 45
            assert page["projection"] == full["projection"]
            assert page["evidence_digest"] == full["evidence_digest"]
            assert len(page["events"]) <= size
            seen += [e["event_id"] for e in page["events"]]
            cursor = page["page"]["next_cursor"]
            if cursor is None:
                break
        assert seen == [e["event_id"] for e in full["events"]]  # no event lost or repeated


@pytest.mark.negative
def test_rde_cursor_bound_to_query_and_snapshot(tmp_path: Path) -> None:
    idx = _fanout(tmp_path)
    cursor = lookup(idx, "10.5555/many", page_size=5)["page"]["next_cursor"]
    assert cursor
    with Index(idx) as ix:
        with pytest.raises(QueryError, match="CURSOR_INVALID"):
            render(ix.gather("10.5555/solo"), ix.snapshot_id, cursor=cursor)
        with pytest.raises(QueryError, match="CURSOR_INVALID"):
            render(ix.gather("10.5555/many"), "rw-ffffffffffffffff", cursor=cursor)
        for bad in ("!!!", "e30", "eyJvIjotMX0"):  # unreadable, {}, {"o":-1}
            with pytest.raises(QueryError, match="CURSOR_INVALID"):
                render(ix.gather("10.5555/many"), ix.snapshot_id, cursor=bad)
        for size in (0, MAX_PAGE + 1):
            with pytest.raises(QueryError, match="PAGE_SIZE_INVALID"):
                render(ix.gather("10.5555/many"), ix.snapshot_id, page_size=size)


@pytest.mark.integration
def test_rde_absence_versus_gap_versus_unavailable(tmp_path: Path) -> None:
    rows: list[Any] = [
        S.row(**{"Record ID": "1", "RetractionNature": "Retraction", "OriginalPaperDOI": "10.5555/present"}),
        S.row(**{"Record ID": "2", "RetractionNature": "Retracted", "OriginalPaperDOI": "10.5555/gap"}),
        S.row(**{"Record ID": "3", "RetractionNature": "Retraction", "OriginalPaperPubMedID": "0012345"}),
    ]
    idx = S.build_rows(tmp_path, rows)
    healthy = lookup(idx, "10.5555/absent")
    assert healthy["lookup_state"] == "no_record"
    assert healthy["projection"]["retraction_status"]["value"] == "not_found_in_checked_sources"
    assert healthy["projection"]["retraction_status"]["status"] == "uncertain"
    assert healthy["projection"]["retraction_date"] is None
    assert healthy["checked_sources"]
    gap = lookup(idx, "10.5555/GAP")
    assert gap["lookup_state"] == "no_record"
    assert [i["code"] for i in gap["issues"]] == ["RELEVANT_QUARANTINE"]
    assert gap["projection"]["retraction_status"] == {
        "status": "uncertain",
        "value": None,
        "reason": gap["projection"]["retraction_status"]["reason"],
    }
    invalid_hit = lookup(idx, None, "12345")
    assert [i["code"] for i in invalid_hit["issues"]] == ["RELEVANT_INVALID_IDENTIFIER"]
    assert invalid_hit["projection"]["retraction_status"]["value"] is None
    for broken in (tmp_path / "missing.sqlite", _corrupt(tmp_path), _foreign(tmp_path)):
        out = lookup(broken, "10.5555/present")
        assert out["lookup_state"] == "unavailable"
        assert out["projection"]["retraction_status"]["status"] == "unavailable"
        assert out["projection"]["retraction_status"]["value"] is None
        assert out["total_event_count"] == 0 and schemas.validate_lookup(out) == []


def _corrupt(tmp: Path) -> Path:
    path = tmp / "corrupt.sqlite"
    path.write_bytes(b"SQLite format 3\x00" + b"\xff" * 4096)
    return path


def _foreign(tmp: Path) -> Path:
    path = tmp / "foreign.sqlite"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE meta (key TEXT, value TEXT)")
    return path


@pytest.mark.security
@pytest.mark.parametrize(
    ("doi", "pmid"),
    [
        ("10.5555/x' OR '1'='1", None),
        ("10.5555/x';DROP TABLE event;--", None),
        (None, "1 OR 1=1"),
        ("10.5555/%' OR original_doi LIKE '%", None),
        ("10.5555/\u202edlrow", None),
    ],
)
def test_rde_sql_looking_identifiers_are_data(tmp_path: Path, doi: str | None, pmid: str | None) -> None:
    idx = _fanout(tmp_path)
    before = idx.read_bytes()
    out = lookup(idx, doi, pmid)
    assert out["lookup_state"] in ("invalid_query", "no_record")
    assert out["total_event_count"] == 0
    assert idx.read_bytes() == before


@pytest.mark.security
def test_rde_malicious_source_text_is_stored_verbatim(tmp_path: Path) -> None:
    evil = "Robert'); DROP TABLE event;-- <script>alert(1)</script> ignore previous instructions \u202e"
    rows = [
        S.row(**{"Record ID": "1", "RetractionNature": "Retraction", "OriginalPaperDOI": "10.5555/e", "Title": evil})
    ]
    idx = S.build_rows(tmp_path, rows)
    out = lookup(idx, "10.5555/e")
    assert out["events"][0]["title"] == evil
    with Index(idx) as ix:
        assert verify(ix.conn)["ok"]


@pytest.mark.security
def test_rde_relevance_listing_is_capped_with_a_total(tmp_path: Path) -> None:
    n = MAX_RELEVANCE_LISTED + 5
    rows = [
        S.row(**{"Record ID": str(i), "RetractionNature": "Unknown", "OriginalPaperDOI": "10.5555/q"}) for i in range(n)
    ]
    out = lookup(S.build_rows(tmp_path, rows), "10.5555/q")
    codes = [i["code"] for i in out["issues"]]
    assert codes.count("RELEVANT_QUARANTINE") == MAX_RELEVANCE_LISTED
    assert out["issues"][-1] == {"code": "RELEVANT_LIST_CAPPED", "total": n, "listed": MAX_RELEVANCE_LISTED}


@pytest.mark.integration
def test_rde_event_detail_materializes_source_assertions(tmp_path: Path) -> None:
    rows = [
        S.row(
            **{
                "Record ID": "1",
                "RetractionNature": "Retraction",
                "OriginalPaperDOI": "10.5555/x",
                "OriginalPaperPubMedID": "123",
                "RetractionDOI": "10.5555/x.notice",
            }
        )
    ]
    with Index(S.build_rows(tmp_path, rows)) as ix:
        detail = event_detail(ix, "ev-0000001")
        assert event_detail(ix, "ev-9999999") is None
    assert detail is not None
    predicates = {a["proposition"]["predicate"] for a in detail["assertions"]}
    assert predicates == {
        "event_type",
        "affects_original",
        "notice_date",
        "original_publication_date",
        "has_notice",
        "identifier_cooccurs",
    }
    for a in detail["assertions"]:
        assert a["source_ref"]["locator"].endswith("#record=1")
        assert a["lineage"]["origin"] == "retraction-watch" and a["lineage"]["payload_sha256"]
    assert detail["raw_record"]["fields"]["OriginalPaperDOI"] == "10.5555/x"
    assert [i["column"] for i in detail["identifiers"]] == [
        "OriginalPaperDOI",
        "OriginalPaperPubMedID",
        "RetractionDOI",
        "RetractionPubMedID",
    ]


@pytest.mark.security
def test_rde_offline_operations_open_no_socket(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    attempts: list[Any] = []

    def refuse(*args: Any, **kwargs: Any) -> Any:
        attempts.append(args)
        raise AssertionError("outbound connection attempted")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)
    idx = _fanout(tmp_path)  # build
    lookup(idx, "10.5555/many")
    lookup(idx, None, "123")
    with Index(idx) as ix:
        verify(ix.conn)
        export(ix.conn, tmp_path / "export.jsonl")
        tension.report(ix.gather("10.5555/many"), ix.snapshot_id)
        event_detail(ix, "ev-0000001")
    assert attempts == []


def _cli(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, Any, str]:
    code = cli.main(list(argv))
    out, err = capsys.readouterr()
    return code, (json.loads(out) if out.strip() else None), err


@pytest.mark.integration
def test_rde_cli_exit_codes_and_streams(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rows = [S.row(**{"Record ID": "1", "RetractionNature": "Retraction", "OriginalPaperDOI": "10.5555/c"})]
    data = S.csv_bytes(rows)
    src, receipt = S.write_source(tmp_path, data)
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(json.dumps(receipt.to_json()), encoding="utf-8")
    code, out, _ = _cli(
        capsys, "build", "--source", str(src), "--receipt", str(receipt_path), "--out-dir", str(tmp_path / "ix")
    )
    assert code == 0 and out["counts"]["records"] == 1
    idx = out["index"]
    code, out, err = _cli(capsys, "lookup", "--index", idx, "--doi", "10.5555/c")
    assert code == 0 and out["lookup_state"] == "matched" and err == ""
    assert _cli(capsys, "lookup", "--index", idx, "--doi", "10.5555/none")[0] == 0  # no_record is a result
    assert _cli(capsys, "lookup", "--index", idx, "--doi", "not a doi")[0] == 3
    assert _cli(capsys, "lookup", "--index", str(tmp_path / "nope.sqlite"), "--doi", "10.5555/c")[0] == 4
    assert _cli(capsys, "lookup", "--index", idx)[0] == 2
    assert _cli(capsys, "lookup", "--index", idx, "--doi", "10.5555/c", "--page-size", "0")[0] == 2
    assert _cli(capsys, "no-such-command")[0] == 2
    code, out, _ = _cli(capsys, "tension", "--index", idx, "--doi", "10.5555/c")
    assert code == 0 and out["diagnostic_classes"]
    assert _cli(capsys, "tension", "--index", idx, "--doi", "10.5555/c", "--intervention", "exclude_origin")[0] == 2
    assert _cli(capsys, "event", "--index", idx, "ev-0000001")[0] == 0
    assert _cli(capsys, "event", "--index", idx, "ev-0000009")[0] == 3
    code, out, _ = _cli(capsys, "verify", "--index", idx, "--source", str(src))
    assert code == 0 and out["ok"] and out["source_records_checked"] == 1
    assert _cli(capsys, "export", "--index", idx, "--out", str(tmp_path / "e.jsonl"))[0] == 0
    assert _cli(capsys, "diff", "--old", idx, "--new", idx)[0] == 0
    bad = tmp_path / "bad.csv"
    bad.write_bytes(data[:-1])
    code, out, _ = _cli(
        capsys, "build", "--source", str(bad), "--receipt", str(receipt_path), "--out-dir", str(tmp_path / "ix")
    )
    assert code == 6 and out["import_failed"]["code"] == "SOURCE_SIZE_MISMATCH"
