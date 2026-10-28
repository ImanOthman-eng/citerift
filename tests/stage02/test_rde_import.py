"""Import failures, record accounting, quarantine, duplicates and atomic publication (SPECIFICATION.md 5, 10.1;
directive section 14 items 6, 11 and 12)."""

from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest
import rde_support as S

from citerift.retraction import source
from citerift.retraction.export import verify
from citerift.retraction.query import Index
from citerift.retraction.source import ImportFailure, load_receipt, parse_receipt
from citerift.retraction.store import build, open_index


def _rows() -> list[dict[str, str]]:
    return [
        S.row(**{"Record ID": "1", "RetractionNature": "Retraction", "OriginalPaperDOI": "10.5555/a1"}),
        S.row(**{"Record ID": "2", "RetractionNature": "Correction", "OriginalPaperDOI": "10.5555/a2"}),
    ]


def _fail(tmp: Path, data: bytes, **receipt: Any) -> ImportFailure:
    tmp.mkdir(parents=True, exist_ok=True)
    path = tmp / "source.csv"
    path.write_bytes(data)
    with pytest.raises(ImportFailure) as info:
        build(path, S.receipt_for(data, **receipt), tmp / "index")
    assert not list((tmp / "index").glob("*.sqlite")) if (tmp / "index").exists() else True
    return info.value


def _counts(idx: Path) -> dict[str, Any]:
    with sqlite3.connect(idx) as conn:
        counts: dict[str, Any] = json.loads(conn.execute("SELECT value FROM meta WHERE key='counts'").fetchone()[0])
    return counts


@pytest.mark.negative
def test_rde_wrong_hash_and_partial_download_fail(tmp_path: Path) -> None:
    data = S.csv_bytes(_rows())
    path = tmp_path / "source.csv"
    path.write_bytes(data[:-10])  # a partial download
    with pytest.raises(ImportFailure) as info:
        build(path, S.receipt_for(data), tmp_path / "index")
    assert info.value.code == "SOURCE_SIZE_MISMATCH"
    tampered = data.replace(b"10.5555/a1", b"10.5555/a9")
    path.write_bytes(tampered)
    with pytest.raises(ImportFailure) as info:
        build(path, S.receipt_for(data), tmp_path / "index")
    assert info.value.code == "SOURCE_HASH_MISMATCH"
    blob_bad = S.receipt_for(data, git_blob_sha1=hashlib.sha1(b"x", usedforsecurity=False).hexdigest())
    path.write_bytes(data)
    with pytest.raises(ImportFailure) as info:
        build(path, blob_bad, tmp_path / "index")
    assert info.value.code == "SOURCE_HASH_MISMATCH"
    assert not (tmp_path / "index").exists() or not list((tmp_path / "index").iterdir())


@pytest.mark.negative
def test_rde_unreadable_source(tmp_path: Path) -> None:
    with pytest.raises(ImportFailure) as info:
        build(tmp_path / "absent.csv", S.receipt_for(b""), tmp_path / "index")
    assert info.value.code == "SOURCE_UNREADABLE"


@pytest.mark.negative
@pytest.mark.parametrize(
    ("data", "code"),
    [
        (b"", "HEADER_MISSING"),
        (b"\n", "HEADER_MISSING"),
        (S.csv_bytes([], header=[*S.HEADER, "Title"]), "HEADER_DUPLICATE"),
        (S.csv_bytes([], header=[h for h in S.HEADER if h != "RetractionNature"]), "HEADER_CRITICAL_MISSING"),
        (S.csv_bytes([], header=[h for h in S.HEADER if h != "OriginalPaperPubMedID"]), "HEADER_CRITICAL_MISSING"),
        (S.csv_bytes(_rows()) + b'"unterminated,quote\n', "CSV_STRUCTURE_INVALID"),
        (S.csv_bytes(_rows()) + b'"a"b,c\n', "CSV_STRUCTURE_INVALID"),
        (S.csv_bytes(_rows()).replace(b"Synthetic record", b"Synth\xffetic", 1), "ENCODING_INVALID"),
        (S.csv_bytes(_rows()).replace(b"Synthetic record", b"Synth\xc3", 1), "ENCODING_INVALID"),
        (S.csv_bytes(_rows()).replace(b"Synthetic record", b"Synth\x00etic", 1), "NUL_BYTE"),
        (S.csv_bytes(_rows()).replace(b"\n", b"\r\n"), "CR_UNSUPPORTED"),
        (S.csv_bytes(_rows()).replace(b"Synthetic record", b"Synth\retic", 1), "CR_UNSUPPORTED"),
    ],
    ids=[
        "empty",
        "blank-first-line",
        "duplicate-header",
        "missing-nature",
        "missing-original-pmid",
        "unterminated-quote",
        "text-after-quote",
        "invalid-utf8",
        "truncated-utf8",
        "nul",
        "crlf",
        "bare-cr",
    ],
)
def test_rde_fatal_import_failures(tmp_path: Path, data: bytes, code: str) -> None:
    failure = _fail(tmp_path, data)
    assert failure.code == code
    assert set(failure.to_json()) == {"code", "message", "position"}


@pytest.mark.negative
def test_rde_field_and_row_limits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    limit_before = csv.field_size_limit()
    big = S.row(**{"Record ID": "1", "RetractionNature": "Retraction", "Notes": "x" * (source.FIELD_LIMIT + 1)})
    assert _fail(tmp_path / "a", S.csv_bytes([big])).code == "FIELD_TOO_LARGE"
    monkeypatch.setattr(source, "ROW_LIMIT", 2)
    rows = [S.row(**{"Record ID": str(i), "RetractionNature": "Retraction"}) for i in range(3)]
    assert _fail(tmp_path / "b", S.csv_bytes(rows)).code == "ROW_LIMIT_EXCEEDED"
    assert csv.field_size_limit() == limit_before  # the process-wide csv limit is restored after a failure


@pytest.mark.negative
@pytest.mark.parametrize(
    "receipt",
    [
        {"commit": "A" * 40},
        {"expected_sha256": "0" * 63},
        {"url": "http://example.invalid/x"},
        {"expected_bytes": True},
    ],
)
def test_rde_receipt_invalid(receipt: dict[str, Any]) -> None:
    with pytest.raises(ImportFailure) as info:
        S.receipt_for(b"x", **receipt)
    assert info.value.code == "RECEIPT_INVALID"


@pytest.mark.negative
def test_rde_receipt_keys_exact_and_duplicate_json_keys(tmp_path: Path) -> None:
    good = S.receipt_for(b"x").to_json()
    with pytest.raises(ImportFailure):
        parse_receipt({**good, "extra": "x"})
    text = json.dumps(good)
    dup = text[:-1] + ', "commit": "' + "1" * 40 + '"}'
    path = tmp_path / "r.json"
    path.write_text(dup, encoding="utf-8")
    with pytest.raises(ImportFailure) as info:
        load_receipt(path)
    assert info.value.code == "RECEIPT_INVALID"


@pytest.mark.unit
def test_rde_packaged_receipt_is_the_pinned_snapshot() -> None:
    r = load_receipt()
    assert r.commit == "a987928a816e0a6f8bb7f8ebc68ad15fe44ab3c4"
    assert r.expected_bytes == 68076023
    assert r.expected_sha256 == "2f116e9ffed718e6b2e37cd6ff652c091fd1971e1ad9c0639f0de16e7f50a655"


@pytest.mark.integration
def test_rde_embedded_newlines_and_blank_lines_are_accounted(tmp_path: Path) -> None:
    rows = _rows()
    rows[0]["Title"] = "A title\nwith two\nembedded newlines"
    body = S.csv_bytes(rows)
    header_end = body.index(b"\n") + 1
    data = body[:header_end] + b"\n\n" + body[header_end:] + b"\n"  # two blank lines after the header, one at the end
    source_path, receipt = S.write_source(tmp_path, data)
    result = build(source_path, receipt, tmp_path / "index")
    c = result.manifest["counts"]
    assert (c["records"], c["accepted"], c["quarantined"]) == (2, 2, 0)
    assert c["blank_lines"] == 3 and c["header_lines"] == 1
    assert c["record_lines"] == 3 + 1
    assert c["physical_lines"] == c["header_lines"] + c["record_lines"] + c["blank_lines"] == 8
    with Index(result.index_path) as ix:
        first = ix.conn.execute("SELECT line_start, line_end FROM raw_record WHERE ordinal = 1").fetchone()
        assert first == (4, 6)
        assert verify(ix.conn)["ok"]


@pytest.mark.integration
def test_rde_no_trailing_newline_and_bom_optional(tmp_path: Path) -> None:
    data = S.csv_bytes(_rows(), bom=False).rstrip(b"\n")
    source_path, receipt = S.write_source(tmp_path, data)
    c = build(source_path, receipt, tmp_path / "index").manifest["counts"]
    assert c["physical_lines"] == 3 and c["records"] == 2


@pytest.mark.integration
def test_rde_quarantine_keeps_raw_rows_with_reasons(tmp_path: Path) -> None:
    rows: list[Any] = [
        S.row(**{"Record ID": "1", "RetractionNature": "", "OriginalPaperDOI": "10.5555/q1"}),
        S.row(**{"Record ID": "2", "RetractionNature": "retraction", "OriginalPaperDOI": "10.5555/q2"}),
        S.row(**{"Record ID": "3", "RetractionNature": "Retraction ", "OriginalPaperDOI": "10.5555/q3"}),
        ["4", "too", "few", "fields"],
        S.row(**{"Record ID": "", "RetractionNature": "Retraction"}),  # no ids at all: accepted, not quarantined
    ]
    source_path, receipt = S.write_source(tmp_path, S.csv_bytes(rows))
    result = build(source_path, receipt, tmp_path / "index")
    c = result.manifest["counts"]
    assert (c["records"], c["accepted"], c["quarantined"]) == (5, 1, 4)
    with Index(result.index_path) as ix:
        reasons = dict(ix.conn.execute("SELECT ordinal, reasons FROM quarantine"))
        assert json.loads(reasons[1]) == ["EVENT_TYPE_MISSING"]
        assert json.loads(reasons[2]) == ["EVENT_TYPE_UNKNOWN"]  # labels are exact and case-sensitive
        assert json.loads(reasons[3]) == ["EVENT_TYPE_UNKNOWN"]
        assert json.loads(reasons[4]) == ["FIELD_COUNT_MISMATCH"]
        stored = json.loads(ix.conn.execute("SELECT fields FROM raw_record WHERE ordinal = 4").fetchone()[0])
        assert stored == ["4", "too", "few", "fields"]
        ev = ix.conn.execute("SELECT anchor, flags, issues FROM event").fetchone()
        assert ev[0] == "rec:5" and "ORIGINAL_ANCHOR_SOURCE_RECORD_ONLY" in json.loads(ev[1])
        assert "RECORD_ID_MISSING" in json.loads(ev[2])
        assert verify(ix.conn)["ok"]


@pytest.mark.integration
def test_rde_duplicates_are_grouped_never_merged(tmp_path: Path) -> None:
    a = S.row(**{"Record ID": "7", "RetractionNature": "Retraction", "OriginalPaperDOI": "10.5555/d1"})
    changed = dict(a, Reason="+Changed payload")
    same_event = S.row(
        **{"Record ID": "8", "RetractionNature": "Retraction", "OriginalPaperDOI": "10.5555/d1", "Notes": "other"}
    )
    source_path, receipt = S.write_source(tmp_path, S.csv_bytes([a, a, changed, same_event]))
    result = build(source_path, receipt, tmp_path / "index")
    c = result.manifest["counts"]
    assert (c["records"], c["accepted"], c["events"]) == (4, 4, 4)  # grouping never changes accounting
    with Index(result.index_path) as ix:
        groups: dict[str, set[int]] = {}
        for kind, _key, ordinal in ix.conn.execute("SELECT kind, group_key, ordinal FROM dup_group"):
            groups.setdefault(kind, set()).add(ordinal)
        assert groups["identical_record"] == {1, 2}
        assert groups["record_id_reused"] == {1, 2, 3}
        assert groups["same_event_signature"] == {1, 2, 3, 4}
        assert c["duplicate_group_members"] == sum(len(v) for v in groups.values())
        assert ix.conn.execute("SELECT COUNT(*) FROM event WHERE original_doi = '10.5555/d1'").fetchone()[0] == 4


@pytest.mark.regression
@pytest.mark.parametrize("stage", ["after_records", "before_validate", "before_publish"])
def test_rde_failed_build_preserves_last_valid_artifact(tmp_path: Path, stage: str) -> None:
    source_path, receipt = S.write_source(tmp_path, S.csv_bytes(_rows()))
    good = build(source_path, receipt, tmp_path / "index")
    before = good.index_path.read_bytes()
    manifest_before = good.manifest_path.read_bytes()

    def crash(at: str) -> None:
        if at == stage:
            raise RuntimeError(f"injected crash at {at}")

    with pytest.raises(RuntimeError):
        build(source_path, receipt, tmp_path / "index", fail_hook=crash)
    assert good.index_path.read_bytes() == before
    assert good.manifest_path.read_bytes() == manifest_before
    assert sorted(p.name for p in (tmp_path / "index").iterdir()) == sorted(
        [good.index_path.name, good.manifest_path.name]
    )
    open_index(good.index_path).close()


@pytest.mark.regression
def test_rde_crash_between_index_and_manifest_leaves_a_valid_index(tmp_path: Path) -> None:
    """The index is published first and is self-describing (meta); the manifest beside it is a copy."""
    source_path, receipt = S.write_source(tmp_path, S.csv_bytes(_rows()))

    def crash(at: str) -> None:
        if at == "between_index_and_manifest":
            raise RuntimeError("injected")

    with pytest.raises(RuntimeError):
        build(source_path, receipt, tmp_path / "index", fail_hook=crash)
    [index] = list((tmp_path / "index").glob("*.sqlite"))
    assert not list((tmp_path / "index").glob(".*tmp*"))
    with Index(index) as ix:
        assert verify(ix.conn)["ok"]


@pytest.mark.regression
def test_rde_failed_import_of_other_bytes_keeps_earlier_snapshot(tmp_path: Path) -> None:
    source_path, receipt = S.write_source(tmp_path, S.csv_bytes(_rows()))
    good = build(source_path, receipt, tmp_path / "index")
    bad = S.csv_bytes(_rows()) + b'"broken\n'
    bad_path = tmp_path / "bad.csv"
    bad_path.write_bytes(bad)
    with pytest.raises(ImportFailure):
        build(bad_path, S.receipt_for(bad), tmp_path / "index")
    assert [p.name for p in (tmp_path / "index").glob("*.sqlite")] == [good.index_path.name]


@pytest.mark.security
def test_rde_reader_is_read_only(tmp_path: Path) -> None:
    source_path, receipt = S.write_source(tmp_path, S.csv_bytes(_rows()))
    idx = build(source_path, receipt, tmp_path / "index").index_path
    before = idx.read_bytes()
    conn = open_index(idx)
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("DELETE FROM event")
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("CREATE TABLE t (a)")
    conn.close()
    assert idx.read_bytes() == before
