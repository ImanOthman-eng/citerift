"""Canonical export, digests, verification, snapshot diff and reproducibility (SPECIFICATION.md 10.4, 10.5;
directive section 14 item 13 and the metamorphic properties on permutation, added events and rebuilds)."""

from __future__ import annotations

import json
import random
import shutil
import sqlite3
from pathlib import Path
from typing import Any

import pytest
import rde_support as S

from citerift.retraction.export import diff, export, verify
from citerift.retraction.query import Index, lookup


def _corpus() -> list[dict[str, str]]:
    rows = []
    natures = ["Retraction", "Correction", "Expression of concern", "Reinstatement"]
    for i in range(24):
        rows.append(
            S.row(
                **{
                    "Record ID": str(100 + i),
                    "RetractionNature": natures[i % 4],
                    "OriginalPaperDOI": f"10.5555/p{i // 2}",
                    "OriginalPaperPubMedID": str(5000 + i // 2) if i % 3 else "",
                    "RetractionDOI": f"10.5555/n{i}" if i % 5 else "",
                    "RetractionDate": f"{1 + i % 12}/{1 + i % 28}/20{10 + i % 9} 0:00",
                    "Title": f"Synthetic title {i // 2}",
                }
            )
        )
    rows.append(dict(rows[0]))  # an identical duplicate
    rows.append(S.row(**{"Record ID": "900", "RetractionNature": "Unknown label"}))  # quarantined
    return rows


def _meta(idx: Path) -> dict[str, str]:
    with sqlite3.connect(idx) as conn:
        return dict(conn.execute("SELECT key, value FROM meta"))


def _lookups(idx: Path) -> list[dict[str, Any]]:
    out = []
    for i in range(13):
        r = lookup(idx, f"10.5555/p{i}")
        out.append({k: v for k, v in r.items() if k != "snapshot_id"} | {"events": len(r["events"])})
    return out


@pytest.mark.reproducibility
def test_rde_double_build_same_digests_and_query_output(tmp_path: Path) -> None:
    a = S.build_rows(tmp_path / "a", _corpus())
    b = S.build_rows(tmp_path / "b", _corpus())
    ma, mb = _meta(a), _meta(b)
    for key in ("artifact_digest", "semantic_digest", "export_lines", "snapshot_id", "counts"):
        assert ma[key] == mb[key], key
    assert [lookup(a, f"10.5555/p{i}") for i in range(13)] == [lookup(b, f"10.5555/p{i}") for i in range(13)]
    with Index(a) as ia, Index(b) as ib:
        ea = export(ia.conn, tmp_path / "a.jsonl")
        eb = export(ib.conn, tmp_path / "b.jsonl")
    assert ea == eb
    assert (tmp_path / "a.jsonl").read_bytes() == (tmp_path / "b.jsonl").read_bytes()
    assert "run_built_at" not in (tmp_path / "a.jsonl").read_text(encoding="utf-8")  # run metadata is not content


@pytest.mark.reproducibility
def test_rde_row_permutation_keeps_semantic_digest(tmp_path: Path) -> None:
    rows = _corpus()
    shuffled = rows[:]
    random.Random(7).shuffle(shuffled)  # a fixed test permutation
    a = S.build_rows(tmp_path / "a", rows)
    b = S.build_rows(tmp_path / "b", shuffled)
    ma, mb = _meta(a), _meta(b)
    assert ma["snapshot_id"] != mb["snapshot_id"]  # different bytes, different snapshot and ids
    assert ma["artifact_digest"] != mb["artifact_digest"]
    assert ma["semantic_digest"] == mb["semantic_digest"]
    la, lb = _lookups(a), _lookups(b)
    for x, y in zip(la, lb, strict=True):
        assert x["projection"]["retraction_status"]["value"] == y["projection"]["retraction_status"]["value"]
        assert x["total_event_count"] == y["total_event_count"]
        assert x["lookup_state"] == y["lookup_state"]


@pytest.mark.reproducibility
def test_rde_adding_events_never_loses_events(tmp_path: Path) -> None:
    rows = _corpus()
    extra = S.row(**{"Record ID": "777", "RetractionNature": "Correction", "OriginalPaperDOI": "10.5555/p3"})
    a = S.build_rows(tmp_path / "a", rows)
    b = S.build_rows(tmp_path / "b", [*rows, extra])
    for i in range(13):
        before = {e["row_sha256"] for e in lookup(a, f"10.5555/p{i}", page_size=100)["events"]}
        after = {e["row_sha256"] for e in lookup(b, f"10.5555/p{i}", page_size=100)["events"]}
        assert before <= after
    assert lookup(b, "10.5555/p3")["total_event_count"] == lookup(a, "10.5555/p3")["total_event_count"] + 1


@pytest.mark.regression
def test_rde_disappearance_is_a_source_version_difference(tmp_path: Path) -> None:
    rows = _corpus()
    old = S.build_rows(tmp_path / "old", rows)
    changed = dict(rows[2], Notes="+edited later")
    new = S.build_rows(tmp_path / "new", [r for i, r in enumerate(rows) if i not in (1, 2)] + [changed])
    with Index(old) as o, Index(new) as n:
        d = diff(o.conn, n.conn)
    assert d["absent_in_new_records"] == 2 and d["added_records"] == 1
    assert d["changed_record_ids"] == 1 and d["changed_record_ids_sample"] == ["102"]
    assert d["record_ids_absent_in_new"] == 1 and d["record_ids_absent_in_new_sample"] == ["101"]
    assert d["absence_reason"] == "SOURCE_VERSION_DIFFERENCE"
    assert "reinstat" not in json.dumps({k: v for k, v in d.items() if k != "note"})
    # the old snapshot is untouched and still answers as before
    gone = lookup(old, "10.5555/p0")
    assert gone["total_event_count"] == 3
    after = lookup(new, "10.5555/p0")
    assert after["projection"]["retraction_status"]["value"] != "reinstated"


@pytest.mark.reproducibility
def test_rde_export_is_canonical_and_complete(tmp_path: Path) -> None:
    idx = S.build_rows(tmp_path, _corpus())
    with Index(idx) as ix:
        digest = export(ix.conn, tmp_path / "e.jsonl")
    lines = (tmp_path / "e.jsonl").read_text(encoding="utf-8").splitlines()
    records = [json.loads(line) for line in lines]
    for line, rec in zip(lines, records, strict=True):
        assert line == json.dumps(rec, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    kinds = [r["kind"] for r in records]
    assert kinds[0] == "snapshot" and kinds[-1] == "digest"
    order = ["snapshot", "record", "event", "quarantine", "dup_group", "cr_assertion", "digest"]
    assert [order.index(k) for k in kinds] == sorted(order.index(k) for k in kinds)
    assert kinds.count("record") == 26 and kinds.count("event") == 25 and kinds.count("quarantine") == 1
    assert digest["lines"] == len(lines) - 1
    assert digest["artifact_digest"] == _meta(idx)["artifact_digest"]


@pytest.mark.negative
def test_rde_verify_detects_tampering(tmp_path: Path) -> None:
    rows = _corpus()
    idx = S.build_rows(tmp_path, rows)
    src = tmp_path / "source.csv"
    with Index(idx) as ix:
        report = verify(ix.conn, src)
        assert report["ok"] and report["source_records_checked"] == 26
    copy = tmp_path / "tampered.sqlite"
    shutil.copy(idx, copy)
    with sqlite3.connect(copy) as conn:
        conn.execute("UPDATE event SET event_type = 'retracted' WHERE event_type = 'correction'")
    with Index(copy) as ix:
        report = verify(ix.conn)
    assert not report["ok"]
    assert any(p.startswith("DIGEST_MISMATCH") for p in report["problems"])
    assert any("EVENT_TYPE_MISMATCH" in p for p in report["problems"])
    shutil.copy(idx, copy)
    with sqlite3.connect(copy) as conn:
        conn.execute("DELETE FROM quarantine")
    with Index(copy) as ix:
        problems = verify(ix.conn)["problems"]
    assert any(p.startswith("INV-A1") for p in problems)
    other = tmp_path / "other.csv"
    other.write_bytes(S.csv_bytes(rows[:-1]))
    with Index(idx) as ix:
        problems = verify(ix.conn, other)["problems"]
    assert any(p.startswith("SOURCE_CHECK_FAILED") for p in problems)
