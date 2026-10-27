"""Canonical export, digests, verification and snapshot comparison (SPECIFICATION.md 10.4, 10.5)."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from citerift.retraction.canonical import canonical, sha256_text
from citerift.retraction.schemas import validate_event_record
from citerift.retraction.source import ImportFailure, check_bytes, iter_records, parse_receipt

EVENT_COLUMNS = (
    "event_id",
    "ordinal",
    "event_type",
    "source_label",
    "record_id",
    "original_doi",
    "original_pmid",
    "notice_doi",
    "notice_pmid",
    "anchor",
    "notice_key",
    "notice_date",
    "original_date",
    "title",
    "authors",
    "journal",
    "original_year",
    "flags",
    "issues",
)
_JSON_EVENT_COLUMNS = {"notice_date", "original_date", "flags", "issues"}
CR_COLUMNS = (
    "assertion_id",
    "predicate",
    "original_doi",
    "notice_doi",
    "notice_key",
    "relation_type",
    "mapped_type",
    "label",
    "source_label",
    "origin",
    "channel",
    "depends_on",
    "retrieved_at",
    "locator",
    "payload_sha256",
    "pointer",
    "record_id_raw",
    "updated_raw",
)
_JSON_CR_COLUMNS = {"depends_on", "updated_raw"}


def event_from_row(row: tuple[Any, ...]) -> dict[str, Any]:
    out = dict(zip(EVENT_COLUMNS, row, strict=True))
    for key in _JSON_EVENT_COLUMNS:
        out[key] = json.loads(out[key])
    return out


def cr_from_row(row: tuple[Any, ...]) -> dict[str, Any]:
    out = dict(zip(CR_COLUMNS, row, strict=True))
    for key in _JSON_CR_COLUMNS:
        out[key] = json.loads(out[key]) if out[key] is not None else None
    return out


def _header(conn: sqlite3.Connection) -> list[str]:
    header: list[str] = json.loads(conn.execute("SELECT value FROM meta WHERE key='header'").fetchone()[0])
    return header


def semantic_event(event: dict[str, Any], fields: list[str], header: list[str]) -> dict[str, Any]:
    """Event content without ordinals, ids, line numbers or snapshot ids (permutation-invariant)."""
    anchor = event["anchor"]
    return {
        "kind": "event",
        "fields": dict(zip(header, fields, strict=True)),
        "event_type": event["event_type"],
        "original_doi": event["original_doi"],
        "original_pmid": event["original_pmid"],
        "notice_doi": event["notice_doi"],
        "notice_pmid": event["notice_pmid"],
        "anchor": "rec:*" if anchor.startswith("rec:") else anchor,
        "notice_key": event["notice_key"],
        "notice_date": event["notice_date"],
        "original_date": event["original_date"],
        "flags": event["flags"],
        "issues": event["issues"],
    }


def iter_artifact_lines(conn: sqlite3.Connection) -> Iterator[tuple[str, str | None]]:
    """Yield (artifact line, semantic line or None) in canonical export order."""
    meta = dict(conn.execute("SELECT key, value FROM meta").fetchall())
    header = json.loads(meta["header"])
    yield (
        canonical(
            {
                "kind": "snapshot",
                "snapshot_id": meta["snapshot_id"],
                "policy_version": meta["policy_version"],
                "parser_version": meta["parser_version"],
                "schema_version": meta["schema_version"],
                "receipt": json.loads(meta["receipt"]),
                "source_sha256": meta["source_sha256"],
                "header": header,
                "counts": json.loads(meta["counts"]),
            }
        ),
        None,
    )
    for row in conn.execute(
        "SELECT ordinal, line_start, line_end, record_id, fields, row_sha256, disposition, reasons "
        "FROM raw_record ORDER BY ordinal"
    ):
        fields = json.loads(row[4])
        rec = {
            "kind": "record",
            "ordinal": row[0],
            "line_start": row[1],
            "line_end": row[2],
            "record_id": row[3],
            "fields": fields,
            "row_sha256": row[5],
            "disposition": row[6],
            "reasons": json.loads(row[7]),
        }
        semantic = None
        if row[6] == "quarantined":
            semantic = canonical({"kind": "quarantine", "fields": fields, "reasons": rec["reasons"]})
        yield canonical(rec), semantic
    columns = ", ".join(f"e.{c}" for c in EVENT_COLUMNS)
    query = f"SELECT {columns}, r.fields FROM event e JOIN raw_record r ON r.ordinal = e.ordinal ORDER BY e.ordinal"  # noqa: S608
    for row in conn.execute(query):
        ev = event_from_row(row[:-1])
        fields = json.loads(row[-1])
        yield canonical({"kind": "event", **ev}), canonical(semantic_event(ev, fields, header))
    for row in conn.execute("SELECT ordinal, reasons FROM quarantine ORDER BY ordinal"):
        yield canonical({"kind": "quarantine", "ordinal": row[0], "reasons": json.loads(row[1])}), None
    for row in conn.execute("SELECT kind, group_key, ordinal FROM dup_group ORDER BY kind, group_key, ordinal"):
        yield canonical({"kind": "dup_group", "group": row[0], "group_key": row[1], "ordinal": row[2]}), None
    for row in conn.execute(f"SELECT {', '.join(CR_COLUMNS)} FROM cr_assertion ORDER BY assertion_id"):  # noqa: S608
        cr = cr_from_row(row)
        line = canonical({"kind": "cr_assertion", **cr})
        yield line, line


def compute_digests(conn: sqlite3.Connection) -> dict[str, str]:
    artifact = hashlib.sha256()
    semantic_hashes: list[str] = []
    lines = 0
    for line, semantic in iter_artifact_lines(conn):
        artifact.update(line.encode("utf-8") + b"\n")
        lines += 1
        if semantic is not None:
            semantic_hashes.append(sha256_text(semantic))
    semantic_hashes.sort()
    semantic = hashlib.sha256("\n".join(semantic_hashes).encode("ascii")).hexdigest()
    return {"artifact_digest": artifact.hexdigest(), "semantic_digest": semantic, "export_lines": str(lines)}


def export(conn: sqlite3.Connection, out: Path) -> dict[str, Any]:
    """Stream the canonical JSONL export to ``out`` and return its digest record."""
    artifact = hashlib.sha256()
    semantic_hashes: list[str] = []
    lines = 0
    with out.open("w", encoding="utf-8", newline="\n") as handle:
        for line, semantic in iter_artifact_lines(conn):
            handle.write(line + "\n")
            artifact.update(line.encode("utf-8") + b"\n")
            lines += 1
            if semantic is not None:
                semantic_hashes.append(sha256_text(semantic))
        semantic_hashes.sort()
        digest = {
            "kind": "digest",
            "artifact_digest": artifact.hexdigest(),
            "semantic_digest": hashlib.sha256("\n".join(semantic_hashes).encode("ascii")).hexdigest(),
            "lines": lines,
        }
        handle.write(canonical(digest) + "\n")
    return digest


def verify(conn: sqlite3.Connection, source: Path | None = None) -> dict[str, Any]:
    """Integrity, accounting, digest, schema and semantic checks of an index (and, with ``source``,
    a record-by-record comparison with the source bytes)."""
    from citerift.retraction.store import structural_problems  # noqa: PLC0415 - store imports this module

    problems = structural_problems(conn)
    meta = dict(conn.execute("SELECT key, value FROM meta").fetchall())
    digests = compute_digests(conn)
    for key in ("artifact_digest", "semantic_digest", "export_lines"):
        if meta.get(key) != digests[key]:
            problems.append(f"DIGEST_MISMATCH: {key} stored {meta.get(key)} recomputed {digests[key]}")
    schema_checked = 0
    for row in conn.execute(f"SELECT {', '.join(EVENT_COLUMNS)} FROM event ORDER BY ordinal"):  # noqa: S608
        ev = event_from_row(row)
        for p in validate_event_record(ev):
            problems.append(f"EVENT_INVALID {ev['event_id']}: {p}")
        schema_checked += 1
    source_checked = None
    if source is not None:
        receipt = parse_receipt(json.loads(meta["receipt"]))
        try:
            check_bytes(source, receipt)
            _header, records, _stats = iter_records(source)
            stored = conn.execute("SELECT ordinal, row_sha256 FROM raw_record ORDER BY ordinal")
            source_checked = 0
            for rec, (ordinal, sha) in zip(records, stored, strict=True):
                if rec.ordinal != ordinal or rec.sha256 != sha:
                    problems.append(f"SOURCE_RECORD_MISMATCH at record {ordinal}")
                source_checked += 1
        except ImportFailure as exc:
            problems.append(f"SOURCE_CHECK_FAILED: {exc}")
        except ValueError:
            problems.append("SOURCE_RECORD_COUNT_MISMATCH")
    return {
        "snapshot_id": meta.get("snapshot_id"),
        "ok": not problems,
        "problems": problems[:200],
        "problem_count": len(problems),
        "events_schema_checked": schema_checked,
        "source_records_checked": source_checked,
        "digests": digests,
    }


def _record_map(conn: sqlite3.Connection) -> tuple[Counter[str], dict[str, set[str]]]:
    shas: Counter[str] = Counter()
    by_id: dict[str, set[str]] = {}
    for record_id, sha in conn.execute("SELECT record_id, row_sha256 FROM raw_record"):
        shas[sha] += 1
        if record_id:
            by_id.setdefault(record_id, set()).add(sha)
    return shas, by_id


def diff(old: sqlite3.Connection, new: sqlite3.Connection, limit: int = 100) -> dict[str, Any]:
    """Non-destructive comparison of two snapshots. Absence is a source-version difference, nothing more."""
    old_meta = dict(old.execute("SELECT key, value FROM meta").fetchall())
    new_meta = dict(new.execute("SELECT key, value FROM meta").fetchall())
    a, a_ids = _record_map(old)
    b, b_ids = _record_map(new)
    absent = a - b
    added = b - a
    unchanged = a & b
    changed_ids = sorted(rid for rid in a_ids.keys() & b_ids.keys() if a_ids[rid] != b_ids[rid])
    only_old_ids = sorted(a_ids.keys() - b_ids.keys())
    return {
        "old_snapshot": old_meta.get("snapshot_id"),
        "new_snapshot": new_meta.get("snapshot_id"),
        "unchanged_records": sum(unchanged.values()),
        "added_records": sum(added.values()),
        "absent_in_new_records": sum(absent.values()),
        "changed_record_ids": len(changed_ids),
        "changed_record_ids_sample": changed_ids[:limit],
        "record_ids_absent_in_new": len(only_old_ids),
        "record_ids_absent_in_new_sample": only_old_ids[:limit],
        "absence_reason": "SOURCE_VERSION_DIFFERENCE",
        "note": (
            "A record absent from the newer snapshot is a difference between source versions. It is not a "
            "reinstatement, a removed retraction or any assertion about a paper."
        ),
        "semantic_digest_equal": old_meta.get("semantic_digest") == new_meta.get("semantic_digest"),
    }
