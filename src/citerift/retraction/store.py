"""SQLite index: atomic build and read-only opening (SPECIFICATION.md section 10.1)."""

from __future__ import annotations

import contextlib
import datetime as dt
import json
import os
import platform
import secrets
import sqlite3
import time
import urllib.parse
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from citerift.retraction import ingest
from citerift.retraction.canonical import canonical
from citerift.retraction.corroboration import ingest_replay
from citerift.retraction.search import title_tokens
from citerift.retraction.source import (
    PARSER_VERSION,
    ImportFailure,
    RawRecord,
    Receipt,
    check_bytes,
    iter_records,
    receipt_digest,
)

POLICY_VERSION = "citerift-rde-policy/1.1.0"
SCHEMA_VERSION = "1.0.0"
INDEX_FORMAT = 2001
APPLICATION_ID = 0x43525244  # "CRRD"
BATCH = 5000

DDL = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL) WITHOUT ROWID;
CREATE TABLE raw_record (
  ordinal INTEGER PRIMARY KEY,
  line_start INTEGER NOT NULL,
  line_end INTEGER NOT NULL,
  record_id TEXT NOT NULL,
  fields TEXT NOT NULL,
  row_sha256 TEXT NOT NULL,
  disposition TEXT NOT NULL CHECK (disposition IN ('accepted', 'quarantined')),
  reasons TEXT NOT NULL
);
CREATE TABLE ident (
  id INTEGER PRIMARY KEY,
  ordinal INTEGER NOT NULL REFERENCES raw_record(ordinal),
  role TEXT NOT NULL CHECK (role IN ('original', 'notice')),
  scheme TEXT NOT NULL CHECK (scheme IN ('doi', 'pmid')),
  column_name TEXT NOT NULL,
  raw TEXT NOT NULL,
  input_form TEXT NOT NULL,
  norm TEXT,
  missing INTEGER NOT NULL CHECK (missing IN (0, 1)),
  transformations TEXT NOT NULL,
  issues TEXT NOT NULL
);
CREATE INDEX ident_norm ON ident (scheme, norm, role);
CREATE INDEX ident_ordinal ON ident (ordinal);
CREATE INDEX ident_invalid ON ident (scheme) WHERE norm IS NULL AND missing = 0;
CREATE TABLE event (
  event_id TEXT PRIMARY KEY,
  ordinal INTEGER NOT NULL UNIQUE REFERENCES raw_record(ordinal),
  event_type TEXT NOT NULL CHECK (event_type IN ('retracted', 'expression_of_concern', 'correction', 'reinstated')),
  source_label TEXT NOT NULL,
  record_id TEXT NOT NULL,
  original_doi TEXT,
  original_pmid TEXT,
  notice_doi TEXT,
  notice_pmid TEXT,
  anchor TEXT NOT NULL,
  notice_key TEXT REFERENCES notice(notice_key),
  notice_date TEXT NOT NULL,
  original_date TEXT NOT NULL,
  title TEXT NOT NULL,
  authors TEXT NOT NULL,
  journal TEXT NOT NULL,
  original_year INTEGER,
  flags TEXT NOT NULL,
  issues TEXT NOT NULL
) WITHOUT ROWID;
CREATE INDEX event_original_doi ON event (original_doi);
CREATE INDEX event_original_pmid ON event (original_pmid);
CREATE INDEX event_notice_doi ON event (notice_doi);
CREATE INDEX event_notice_pmid ON event (notice_pmid);
CREATE INDEX event_anchor ON event (anchor);
CREATE INDEX event_notice_key ON event (notice_key);
CREATE TABLE notice (
  notice_key TEXT PRIMARY KEY,
  scheme TEXT NOT NULL CHECK (scheme IN ('doi', 'pmid')),
  norm TEXT NOT NULL,
  n_events INTEGER NOT NULL CHECK (n_events >= 1)
) WITHOUT ROWID;
CREATE TABLE event_notice (
  event_id TEXT NOT NULL REFERENCES event(event_id),
  notice_key TEXT NOT NULL REFERENCES notice(notice_key),
  PRIMARY KEY (event_id, notice_key)
) WITHOUT ROWID;
CREATE TABLE quarantine (
  ordinal INTEGER PRIMARY KEY REFERENCES raw_record(ordinal),
  reasons TEXT NOT NULL
);
CREATE TABLE dup_group (
  kind TEXT NOT NULL CHECK (kind IN ('identical_record', 'record_id_reused', 'same_event_signature')),
  group_key TEXT NOT NULL,
  ordinal INTEGER NOT NULL REFERENCES raw_record(ordinal),
  PRIMARY KEY (kind, group_key, ordinal)
) WITHOUT ROWID;
CREATE INDEX dup_group_ordinal ON dup_group (ordinal);
CREATE TABLE cr_attempt (
  attempt_id TEXT PRIMARY KEY,
  work_doi TEXT NOT NULL,
  url TEXT NOT NULL,
  outcome TEXT NOT NULL CHECK (outcome IN ('ok', 'failed')),
  failure TEXT,
  http_status INTEGER,
  retrieved_at TEXT NOT NULL,
  payload_sha256 TEXT,
  bytes INTEGER,
  attempts INTEGER NOT NULL,
  channel TEXT NOT NULL
) WITHOUT ROWID;
CREATE INDEX cr_attempt_work ON cr_attempt (work_doi);
CREATE TABLE cr_assertion (
  assertion_id TEXT PRIMARY KEY,
  predicate TEXT NOT NULL CHECK (predicate IN ('update_relation', 'notice_record_exists')),
  original_doi TEXT,
  notice_doi TEXT,
  notice_key TEXT,
  relation_type TEXT,
  mapped_type TEXT,
  label TEXT,
  source_label TEXT,
  origin TEXT NOT NULL,
  channel TEXT NOT NULL,
  depends_on TEXT NOT NULL,
  dependence TEXT NOT NULL CHECK (dependence IN ('known', 'unknown')),
  retrieved_at TEXT NOT NULL,
  locator TEXT NOT NULL,
  payload_sha256 TEXT NOT NULL,
  pointer TEXT NOT NULL,
  record_id_raw TEXT,
  updated_raw TEXT
) WITHOUT ROWID;
CREATE INDEX cr_assertion_original ON cr_assertion (original_doi);
CREATE TABLE title_token (
  token TEXT NOT NULL,
  event_id TEXT NOT NULL REFERENCES event(event_id),
  PRIMARY KEY (token, event_id)
) WITHOUT ROWID;
CREATE TABLE token_df (token TEXT PRIMARY KEY, df INTEGER NOT NULL) WITHOUT ROWID;
"""


class IndexUnavailable(Exception):
    """The index cannot be opened or fails its format checks: lookups report 'unavailable'."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


def snapshot_id_for(sha256: str) -> str:
    return f"rw-{sha256[:16]}"


def _j(value: Any) -> str:
    return canonical(value)


def _batched(rows: Iterable[Sequence[Any]], size: int = BATCH) -> Iterable[list[Sequence[Any]]]:
    batch: list[Sequence[Any]] = []
    for row in rows:
        batch.append(row)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


@dataclass
class BuildResult:
    index_path: Path
    manifest_path: Path
    manifest: dict[str, Any]


FailHook = Callable[[str], None]


_EVENT_INSERT = "INSERT INTO event VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"


def _event_row(e: ingest.Event) -> tuple[Any, ...]:
    return (
        e.event_id,
        e.ordinal,
        e.event_type,
        e.source_label,
        e.record_id,
        e.original_doi,
        e.original_pmid,
        e.notice_doi,
        e.notice_pmid,
        e.anchor,
        e.notice_key,
        _j(e.notice_date.to_json()),
        _j(e.original_date.to_json()),
        e.title,
        e.authors,
        e.journal,
        e.original_year,
        _j(e.flags),
        _j(e.issues),
    )


def build(
    source: Path,
    receipt: Receipt,
    out_dir: Path,
    *,
    corroboration: Path | None = None,
    fail_hook: FailHook | None = None,
) -> BuildResult:
    """Build a new index for ``source`` and publish it atomically. Raises ImportFailure on fatal errors."""
    started = time.monotonic()
    check = check_bytes(source, receipt)
    out_dir.mkdir(parents=True, exist_ok=True)
    snapshot = snapshot_id_for(check.sha256)
    final = out_dir / f"{snapshot}.sqlite"
    manifest_final = out_dir / f"{snapshot}.manifest.json"
    nonce = secrets.token_hex(4)
    tmp = out_dir / f".{snapshot}.sqlite.tmp-{os.getpid()}-{nonce}"
    tmp_manifest = out_dir / f".{snapshot}.manifest.json.tmp-{os.getpid()}-{nonce}"
    hook = fail_hook or (lambda _stage: None)
    try:
        manifest = _build_into(tmp, source, receipt, check, snapshot, corroboration, hook)
        manifest["run_build_seconds"] = round(time.monotonic() - started, 3)
        from citerift.retraction.schemas import BUILD_MANIFEST, validate  # noqa: PLC0415

        invalid = validate(manifest, BUILD_MANIFEST)
        if invalid:
            raise ImportFailure("ARTIFACT_INVALID", f"build manifest: {invalid[0]}")
        _refuse_replacing_other_build(final, manifest_final, manifest["digests"])
        hook("before_publish")
        tmp_manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n", "utf-8")
        _fsync(tmp_manifest)
        os.replace(tmp, final)
        hook("between_index_and_manifest")
        os.replace(tmp_manifest, manifest_final)
        _fsync_dir(out_dir)
    except BaseException:
        for leftover in (tmp, tmp_manifest):
            leftover.unlink(missing_ok=True)
        raise
    return BuildResult(final, manifest_final, manifest)


DIGEST_KEYS = ("artifact_digest", "semantic_digest", "export_lines")


def manifest_path_for(index_path: Path) -> Path:
    return index_path.with_name(index_path.name.removesuffix(".sqlite") + ".manifest.json")


def _refuse_replacing_other_build(final: Path, manifest_final: Path, digests: dict[str, str]) -> None:
    """An artifact of the same snapshot is replaced only by an equal build: a rebuild with other evidence (for
    example another corroboration bundle) never deletes earlier evidence (SPECIFICATION.md 16, C-15)."""
    want = {k: digests[k] for k in DIGEST_KEYS}
    if final.exists():
        try:
            conn = open_index(final)
        except IndexUnavailable:
            have: dict[str, str | None] | None = None
        else:
            try:
                meta = read_meta(conn)
            finally:
                conn.close()
            have = {k: meta.get(k) for k in DIGEST_KEYS}
        if have != want:
            raise ImportFailure(
                "ARTIFACT_EXISTS", f"{final.name} holds another build of this snapshot; build into another directory"
            )
    if manifest_final.exists():
        try:
            recorded = json.loads(manifest_final.read_text(encoding="utf-8")).get("digests", {})
        except (OSError, ValueError, AttributeError):
            recorded = None
        if not isinstance(recorded, dict) or {k: recorded.get(k) for k in DIGEST_KEYS} != want:
            raise ImportFailure(
                "ARTIFACT_EXISTS", f"{manifest_final.name} records another build; build into another directory"
            )


def _fsync(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _fsync_dir(path: Path) -> None:
    with contextlib.suppress(OSError):  # some filesystems refuse to fsync a directory; the rename stays atomic
        _fsync(path)


def raw_row(rec: RawRecord, d: ingest.Disposition, sha: str) -> tuple[Any, ...]:
    return (
        rec.ordinal,
        rec.line_start,
        rec.line_end,
        d.record_id,
        _j(list(rec.fields)),
        sha,
        "accepted" if d.accepted else "quarantined",
        _j(list(d.reasons)),
    )


def ident_rows(d: ingest.Disposition) -> list[tuple[Any, ...]]:
    """``ident`` rows of one record, without the row id (insertion order is the source order)."""
    return [
        (
            occ.ordinal,
            occ.role,
            occ.scheme,
            occ.column,
            occ.norm.raw,
            occ.norm.input_form,
            occ.norm.normalized,
            int(occ.norm.missing),
            _j(list(occ.norm.transformations)),
            _j(list(occ.norm.issues)),
        )
        for occ in d.idents
    ]


def derive_tables(events: list[ingest.Event], compact: list[tuple[int, str, str]]) -> dict[str, list[tuple[Any, ...]]]:
    """Rows of every table derived from the accepted events, in canonical order. The build inserts them and
    ``verify`` recomputes them from the stored raw records, so a derived table cannot drift from its source."""
    ingest.finalize_events(events)
    notices: dict[str, list[str]] = {}
    for e in events:
        if e.notice_key:
            notices.setdefault(e.notice_key, []).append(e.event_id)
    tokens = sorted({(tok, e.event_id) for e in events if e.original_doi for tok in title_tokens(e.title)})
    df = Counter(tok for tok, _ in tokens)
    row_sha = {o: sha for o, _rid, sha in compact}
    dups = ingest.duplicate_groups(compact, events, row_sha)
    return {
        "notice": [(k, k.split(":", 1)[0], k.split(":", 1)[1], len(v)) for k, v in sorted(notices.items())],
        "event": sorted((_event_row(e) for e in events), key=lambda r: r[0]),
        "event_notice": sorted((e.event_id, e.notice_key) for e in events if e.notice_key),
        "title_token": tokens,
        "token_df": sorted(df.items()),
        "dup_group": [(m.kind, m.group_key, m.ordinal) for m in dups],
    }


def _build_into(
    tmp: Path,
    source: Path,
    receipt: Receipt,
    check: Any,
    snapshot: str,
    corroboration: Path | None,
    hook: FailHook,
) -> dict[str, Any]:
    conn = sqlite3.connect(tmp, isolation_level=None)
    try:
        conn.execute("PRAGMA journal_mode=OFF")
        conn.execute("PRAGMA synchronous=OFF")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute(f"PRAGMA application_id={APPLICATION_ID}")
        conn.execute(f"PRAGMA user_version={INDEX_FORMAT}")
        conn.executescript(DDL)
        conn.execute("BEGIN")
        header, records, stats = iter_records(source)
        events: list[ingest.Event] = []
        compact: list[tuple[int, str, str]] = []
        quarantined = 0
        raw_buffer: list[tuple[Any, ...]] = []
        ident_buffer: list[tuple[Any, ...]] = []

        def flush() -> None:
            # Parents first, so every identifier row references an existing record when it is inserted.
            conn.executemany("INSERT INTO raw_record VALUES (?,?,?,?,?,?,?,?)", raw_buffer)
            _insert_idents(conn, ident_buffer)
            raw_buffer.clear()
            ident_buffer.clear()

        for rec in records:
            d = ingest.dispose(rec, header)
            sha = rec.sha256
            compact.append((rec.ordinal, d.record_id, sha))
            if d.event is not None:
                events.append(d.event)
            else:
                quarantined += 1
            ident_buffer += ident_rows(d)
            raw_buffer.append(raw_row(rec, d, sha))
            if len(raw_buffer) >= BATCH:
                flush()
        flush()
        hook("after_records")
        derived = derive_tables(events, compact)
        conn.executemany("INSERT INTO notice VALUES (?,?,?,?)", derived["notice"])
        for batch in _batched(derived["event"]):
            conn.executemany(_EVENT_INSERT, batch)
        conn.executemany("INSERT INTO event_notice VALUES (?,?)", derived["event_notice"])
        conn.execute("INSERT INTO quarantine SELECT ordinal, reasons FROM raw_record WHERE disposition='quarantined'")
        for batch in _batched(derived["title_token"]):
            conn.executemany("INSERT INTO title_token VALUES (?,?)", batch)
        conn.executemany("INSERT INTO token_df VALUES (?,?)", derived["token_df"])
        conn.executemany("INSERT INTO dup_group VALUES (?,?,?)", derived["dup_group"])
        dups = derived["dup_group"]
        corroboration_summary: dict[str, Any] = {"manifests": []}
        if corroboration is not None:
            corroboration_summary = ingest_replay(conn, corroboration)
        hook("before_validate")
        accepted = len(events)
        n_records = stats.records
        line_total = stats.header_lines + stats.record_lines + stats.blank_lines
        if n_records != accepted + quarantined or line_total != check.physical_lines:
            raise ImportFailure(
                "ACCOUNTING_MISMATCH",
                f"records {n_records} vs accepted {accepted} + quarantined {quarantined}; "
                f"lines {line_total} vs physical {check.physical_lines}",
            )
        counts = {
            "records": n_records,
            "accepted": accepted,
            "quarantined": quarantined,
            "events": accepted,
            "physical_lines": check.physical_lines,
            "header_lines": stats.header_lines,
            "record_lines": stats.record_lines,
            "blank_lines": stats.blank_lines,
            "duplicate_group_members": len(dups),
            "by_event_type": dict(
                sorted(conn.execute("SELECT event_type, COUNT(*) FROM event GROUP BY event_type").fetchall())
            ),
            "cr_assertions": conn.execute("SELECT COUNT(*) FROM cr_assertion").fetchone()[0],
        }
        meta = {
            "snapshot_id": snapshot,
            "policy_version": POLICY_VERSION,
            "parser_version": PARSER_VERSION,
            "schema_version": SCHEMA_VERSION,
            "index_format": str(INDEX_FORMAT),
            "receipt": _j(receipt.to_json()),
            "receipt_sha256": receipt_digest(receipt),
            "source_sha256": check.sha256,
            "source_bytes": str(check.size),
            "source_git_blob_sha1": check.git_blob_sha1,
            "header": _j(header),
            "counts": _j(counts),
            "corroboration": _j(corroboration_summary),
            "run_built_at": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "run_python": platform.python_version(),
            "run_sqlite": sqlite3.sqlite_version,
        }
        conn.executemany("INSERT INTO meta VALUES (?,?)", sorted(meta.items()))
        conn.execute("COMMIT")
        conn.execute("ANALYZE")
        from citerift.retraction.export import compute_digests  # noqa: PLC0415 - export imports this module

        digests = compute_digests(conn)
        conn.execute("BEGIN")
        conn.executemany("INSERT INTO meta VALUES (?,?)", sorted(digests.items()))
        conn.execute("COMMIT")
        problems = structural_problems(conn)
        if problems:
            raise ImportFailure("ACCOUNTING_MISMATCH", "; ".join(problems))
        hook("before_event_validation")
        from citerift.retraction.export import EVENT_COLUMNS, event_from_row  # noqa: PLC0415
        from citerift.retraction.schemas import event_problems  # noqa: PLC0415

        rows = conn.execute(f"SELECT {', '.join(EVENT_COLUMNS)} FROM event ORDER BY ordinal")  # noqa: S608
        invalid = event_problems(event_from_row(r) for r in rows)
        if invalid:
            raise ImportFailure("ARTIFACT_INVALID", f"{len(invalid)} event problems; first: {'; '.join(invalid[:3])}")
        conn.execute("PRAGMA journal_mode=DELETE")
    finally:
        conn.close()
    _fsync(tmp)
    return {
        "manifest_version": "1.0.0",
        "snapshot_id": snapshot,
        "policy_version": POLICY_VERSION,
        "parser_version": PARSER_VERSION,
        "schema_version": SCHEMA_VERSION,
        "index_format": INDEX_FORMAT,
        "receipt": receipt.to_json(),
        "source": {"sha256": check.sha256, "bytes": check.size, "git_blob_sha1": check.git_blob_sha1},
        "counts": counts,
        "corroboration": corroboration_summary,
        "digests": digests,
        "run_built_at": meta["run_built_at"],
        "run_python": meta["run_python"],
        "run_sqlite": meta["run_sqlite"],
    }


def _insert_idents(conn: sqlite3.Connection, rows: list[tuple[Any, ...]]) -> None:
    if rows:
        conn.executemany(
            "INSERT INTO ident (ordinal, role, scheme, column_name, raw, input_form, norm, missing, "
            "transformations, issues) VALUES (?,?,?,?,?,?,?,?,?,?)",
            rows,
        )


def structural_problems(conn: sqlite3.Connection) -> list[str]:
    """Integrity, foreign keys and the accounting invariants INV-A1 to INV-A3, read from the index itself."""
    problems = []
    integrity = conn.execute("PRAGMA integrity_check").fetchall()
    if integrity != [("ok",)]:
        problems.append(f"integrity_check: {integrity[:3]}")
    fk = conn.execute("PRAGMA foreign_key_check").fetchall()
    if fk:
        problems.append(f"foreign_key_check: {len(fk)} violations")
    meta = dict(conn.execute("SELECT key, value FROM meta").fetchall())
    counts = json.loads(meta.get("counts", "{}"))
    n = conn.execute("SELECT COUNT(*) FROM raw_record").fetchone()[0]
    acc = conn.execute("SELECT COUNT(*) FROM raw_record WHERE disposition='accepted'").fetchone()[0]
    qua = conn.execute("SELECT COUNT(*) FROM quarantine").fetchone()[0]
    ev = conn.execute("SELECT COUNT(*) FROM event").fetchone()[0]
    if n != acc + qua:
        problems.append(f"INV-A1: records {n} != accepted {acc} + quarantined {qua}")
    if ev != acc:
        problems.append(f"INV-A3: events {ev} != accepted {acc}")
    if counts and (counts.get("records") != n or counts.get("accepted") != acc or counts.get("quarantined") != qua):
        problems.append("meta counts differ from the tables")
    if counts and counts["header_lines"] + counts["record_lines"] + counts["blank_lines"] != counts["physical_lines"]:
        problems.append("INV-A2: line accounting does not add up")
    spans = conn.execute("SELECT COALESCE(SUM(line_end - line_start + 1), 0) FROM raw_record").fetchone()[0]
    if counts and spans != counts["record_lines"]:
        problems.append(f"INV-A2: record spans {spans} != record_lines {counts['record_lines']}")
    bad_ord = conn.execute("SELECT COUNT(*) FROM raw_record WHERE ordinal < 1 OR ordinal > ?", (n,)).fetchone()[0]
    if bad_ord:
        problems.append("record ordinals are not 1..n")
    return problems


def open_index(path: Path) -> sqlite3.Connection:
    """Open an index read-only and immutable; raise IndexUnavailable when it is missing or not an index."""
    if not path.is_file():
        raise IndexUnavailable("INDEX_MISSING", f"{path} does not exist")
    resolved = path.resolve()
    # The path is percent-encoded: '#', '?' and '%' in a file name must not end or alter the URI (C-16).
    uri = f"file:{urllib.parse.quote(resolved.as_posix(), safe='/')}?mode=ro&immutable=1"
    try:
        conn = sqlite3.connect(uri, uri=True, isolation_level=None)
        conn.execute("PRAGMA query_only=ON")
        app = conn.execute("PRAGMA application_id").fetchone()[0]
        ver = conn.execute("PRAGMA user_version").fetchone()[0]
    except sqlite3.DatabaseError as exc:
        raise IndexUnavailable("INDEX_CORRUPT", str(exc)) from None
    if app != APPLICATION_ID or ver != INDEX_FORMAT:
        conn.close()
        raise IndexUnavailable("INDEX_FORMAT_MISMATCH", f"application_id {app:#x}, user_version {ver}")
    try:
        meta = dict(conn.execute("SELECT key, value FROM meta").fetchall())
    except sqlite3.DatabaseError as exc:
        conn.close()
        raise IndexUnavailable("INDEX_CORRUPT", str(exc)) from None
    digests_ok = all(_is_sha256(meta.get(k)) for k in ("artifact_digest", "semantic_digest"))
    if meta.get("policy_version") != POLICY_VERSION or not digests_ok:
        conn.close()
        raise IndexUnavailable("INDEX_FORMAT_MISMATCH", f"policy {meta.get('policy_version')!r} or digests missing")
    opened = [row[2] for row in conn.execute("PRAGMA database_list") if row[1] == "main"]
    if not opened or Path(opened[0]).resolve() != resolved:
        conn.close()
        raise IndexUnavailable("INDEX_CORRUPT", f"SQLite opened {opened!r}, not {resolved}")
    return conn


def _is_sha256(value: str | None) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def read_meta(conn: sqlite3.Connection) -> dict[str, str]:
    return dict(conn.execute("SELECT key, value FROM meta").fetchall())
