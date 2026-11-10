"""The journal file: one canonical JSON record per line, appended and ``fsync``ed one record at a time (S-8.3).

Reading splits the file into complete records and, at most, one torn tail (SPEC 8.6, 10.1):

- the final line is a **torn tail** when it has no newline, does not parse as a canonical record, or its digest is
  wrong (SPEC 8.6, as specified); it was never committed;
- any such defect on an earlier line, or any other violation, is **corruption** (the investigation is ``CORRUPT``,
  read-only, nothing is repaired or guessed).

``repair_torn_tail`` follows Copy → Verify → Preserve (SPEC 10.1 step 2): the whole journal is copied to
``journal.jsonl.torn-<k>`` and verified byte for byte, the valid prefix is written to a temporary file, verified and
``fsync``ed, and only then renamed over ``journal.jsonl``. A complete record is never removed or rewritten.
"""

from __future__ import annotations

import contextlib
import os
import secrets
import stat
from dataclasses import dataclass
from typing import Any

from citerift.investigation import faults
from citerift.investigation.canonical import loads_record
from citerift.investigation.errors import CanonError, InvariantViolation, PathUnsafe, StorageError
from citerift.investigation.fsutil import (
    O_CLOEXEC,
    O_NOFOLLOW,
    fsync_dir,
    lstat_at,
    open_regular,
    read_all,
    write_all,
)
from citerift.investigation.ids import record_digest

JOURNAL = "journal.jsonl"
TORN_PREFIX = "journal.jsonl.torn-"
MAX_RECORD_BYTES = 1024 * 1024
MAX_JOURNAL_BYTES = 512 * 1024 * 1024


@dataclass(frozen=True)
class TornTail:
    """An uncommitted final line: ``offset`` is where the valid prefix ends; ``reason`` says why it is torn."""

    offset: int
    length: int
    reason: str


@dataclass(frozen=True)
class JournalRead:
    records: list[dict[str, Any]]
    lines: list[bytes]  # the raw bytes of each complete record, newline excluded
    size: int
    torn: TornTail | None


def _record_problem(line: bytes) -> tuple[dict[str, Any] | None, str]:
    if len(line) > MAX_RECORD_BYTES:
        return None, f"record larger than {MAX_RECORD_BYTES} bytes"
    try:
        value = loads_record(line)
    except CanonError as exc:
        return None, exc.detail
    if not isinstance(value, dict):
        return None, "record is not an object"
    if value.get("digest") != record_digest(value):
        return value, "digest does not match the record"
    return value, ""


def parse_journal(data: bytes) -> JournalRead:
    """Split journal bytes into records and a torn tail. Raises InvariantViolation (M-2) for corruption."""
    records: list[dict[str, Any]] = []
    lines: list[bytes] = []
    pos = 0
    while pos < len(data):
        nl = data.find(b"\n", pos)
        last = nl == -1 or nl == len(data) - 1
        line = data[pos:] if nl == -1 else data[pos:nl]
        if nl == -1:
            return JournalRead(records, lines, len(data), TornTail(pos, len(data) - pos, "final line has no newline"))
        value, problem = _record_problem(line)
        if problem:
            if last:
                return JournalRead(records, lines, len(data), TornTail(pos, len(data) - pos, problem))
            raise InvariantViolation("M-2", "JOURNAL_CORRUPT", f"line {len(records)}: {problem}", len(records))
        if value is None:  # unreachable: no problem means a parsed object
            raise InvariantViolation("M-2", "JOURNAL_CORRUPT", "unparsed record", len(records))
        records.append(value)
        lines.append(line)
        pos = nl + 1
    return JournalRead(records, lines, len(data), None)


def read_journal(inv_fd: int) -> JournalRead:
    """Read ``journal.jsonl`` of an investigation directory without taking the lock (a consistent prefix only)."""
    try:
        fd = open_regular(JOURNAL, inv_fd)
    except PathUnsafe as exc:
        raise InvariantViolation("M-2", "JOURNAL_CORRUPT", exc.detail) from exc
    try:
        data = read_all(fd, MAX_JOURNAL_BYTES)
    except PathUnsafe as exc:
        raise InvariantViolation("M-2", "JOURNAL_CORRUPT", exc.detail) from exc
    finally:
        os.close(fd)
    return parse_journal(data)


def open_for_append(inv_fd: int) -> int:
    return open_regular(JOURNAL, inv_fd, os.O_WRONLY | os.O_APPEND)


def append_line(fd: int, line: bytes) -> None:
    """Append one record line and make it durable.

    If anything fails before ``fsync`` returns (an ``OSError`` or any other exception), the file is truncated back to
    its length before the append and ``fsync``ed, so a failed append commits nothing (SPEC 10.2). If that truncation
    fails too, the outcome is uncertain and only a reopen decides: a partial line is a torn tail, a complete line is
    a record. The caller holds the lock, so no other writer can have appended in between."""
    data = line + b"\n"
    offset = os.fstat(fd).st_size
    faults.point("journal.before_append", fd=fd, data=data)
    try:
        faults.point("journal.during_append", fd=fd, data=data)
        write_all(fd, data)
        faults.point("journal.after_write")
        os.fsync(fd)
    except BaseException as exc:
        with contextlib.suppress(OSError):
            os.ftruncate(fd, offset)
            os.fsync(fd)
        if isinstance(exc, OSError):
            raise StorageError(f"journal append: {exc.strerror}") from exc
        raise
    faults.point("journal.after_fsync")


def write_new_file(name: str, dir_fd: int, data: bytes) -> None:
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0o600, dir_fd=dir_fd)
    try:
        write_all(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)


def _read_back(name: str, dir_fd: int, limit: int) -> bytes:
    fd = open_regular(name, dir_fd)
    try:
        return read_all(fd, limit)
    finally:
        os.close(fd)


def repair_torn_tail(inv_fd: int, read: JournalRead, original: bytes) -> str:
    """Preserve the whole journal, then replace it by its valid prefix (Copy → Verify → Preserve). Returns the name
    of the preserved copy. The caller holds the lock."""
    if read.torn is None:
        raise StorageError("no torn tail to repair")
    k = 0
    while lstat_at(f"{TORN_PREFIX}{k}", inv_fd) is not None:
        k += 1
    copy_name = f"{TORN_PREFIX}{k}"
    write_new_file(copy_name, inv_fd, original)
    if _read_back(copy_name, inv_fd, MAX_JOURNAL_BYTES) != original:
        raise StorageError(f"{copy_name} does not equal the journal it preserves")
    fsync_dir(inv_fd)
    faults.point("torn.copied")
    prefix = original[: read.torn.offset]
    tmp = f".journal.tmp-{secrets.token_hex(8)}"
    write_new_file(tmp, inv_fd, prefix)
    if _read_back(tmp, inv_fd, MAX_JOURNAL_BYTES) != prefix:
        os.unlink(tmp, dir_fd=inv_fd)
        raise StorageError("the valid prefix did not read back equal")
    faults.point("torn.prefix_written")
    os.rename(tmp, JOURNAL, src_dir_fd=inv_fd, dst_dir_fd=inv_fd)
    fsync_dir(inv_fd)
    return copy_name


def remove_stale_journal_temporaries(inv_fd: int) -> list[str]:
    """Temporaries of an interrupted torn-tail repair: the journal itself was never replaced by them."""
    removed = []
    for name in sorted(os.listdir(inv_fd)):
        if not name.startswith(".journal.tmp-"):
            continue
        st = lstat_at(name, inv_fd)
        if st is not None and (stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode)):
            os.unlink(name, dir_fd=inv_fd)
            removed.append(name)
    if removed:
        fsync_dir(inv_fd)
    return removed
