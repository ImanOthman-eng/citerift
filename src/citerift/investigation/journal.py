"""The journal file: one canonical JSON record per line, appended and ``fsync``ed one record at a time (S-8.3).

Reading splits the file into complete records and, at most, one torn tail (SPEC 8.6, 10.1; owner decision D-044):

- a **torn tail** is an incomplete physical record: final bytes without the terminating newline that an interrupted
  append could have left (a prefix of one record line and its newline, possibly with zero-filled blocks;
  ``_tail_problem``). Only that is an interrupted append; it was never committed. Final bytes without a newline that
  no append can leave (longer than one append, not starting a record, a complete value followed by other bytes, or a
  complete value that is not the valid next record) are ``CORRUPT`` (re-review findings D44-R2, D44-R2a, D44-R2b).
  A complete record without its newline is torn only if the fold accepts it as the next record, with the same
  ``Folder.check`` that every append passes (owner decision D-046; checked in ``memory.open``);
- a newline-terminated line is a complete physical record. If it is not strict canonical JSON or has a wrong digest
  (both checked here), or (checked by the fold) has a wrong ``prev``, violates the schema or an invariant, or names a
  missing blob, the investigation is ``CORRUPT`` (read-only; nothing is repaired, dropped or guessed), whether the
  line is the last one or not.

``repair_torn_tail`` follows Copy → Verify → Preserve (SPEC 10.1), and the caller runs it only after the whole prefix
has validated: the whole journal is copied to
``journal.jsonl.torn-<k>`` and verified byte for byte, the valid prefix is written to a temporary file, verified and
``fsync``ed, and only then renamed over ``journal.jsonl``. A complete record is never removed or rewritten.
"""

from __future__ import annotations

import contextlib
import json
import os
import secrets
import stat
from dataclasses import dataclass, field
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
_DECODER = json.JSONDecoder()  # structure only: is the final fragment one complete JSON value? (D44-R2)


@dataclass(frozen=True)
class TornTail:
    """An uncommitted final line: ``offset`` is where the valid prefix ends; ``reason`` says why it is torn.

    ``record`` is set when the final bytes hold one complete record (strict canonical JSON, correct digest). Such a
    tail is torn only if that record is a fully valid next record; the caller checks it with the fold that checks
    every append (``Folder.check``), after the prefix, and treats any failure as ``CORRUPT`` (D-046)."""

    offset: int
    length: int
    reason: str
    record: dict[str, Any] | None = field(default=None, compare=False)


@dataclass(frozen=True)
class JournalRead:
    records: list[dict[str, Any]]
    lines: list[bytes]  # the raw bytes of each complete record, newline excluded
    size: int
    torn: TornTail | None


def _tail_problem(tail: bytes) -> tuple[str, dict[str, Any] | None]:
    """Classify final bytes without a newline (D-044; D44-R2; D-046).

    Returns ``(problem, record)``. ``problem`` is non-empty when no interrupted append can have left the bytes;
    ``record`` is the complete record they hold, if any, which the caller must still validate as the next record.

    An append writes one valid next record line (an object, so ``{`` … ``}``, at most ``MAX_RECORD_BYTES``) and its
    newline in one write. A crash leaves a prefix of those bytes, and blocks that never reached the disk may read back
    as zero bytes anywhere in it. So the final bytes are corruption, not a torn tail, when they are longer than that
    write, when their first byte is neither ``{`` nor zero, when they hold a complete JSON value followed by anything
    other than zero bytes, or when that complete value is not a record line (``_record_problem``, the check every
    complete line passes). Whether a complete record is a legal *next* record is not decided here: the fold decides
    it, with the same check as an append (D-046). Fragments whose content cannot be checked (a prefix of a record, or
    bytes after a zero-filled block) remain torn tails; they are preserved, never read as authority."""
    if len(tail) > MAX_RECORD_BYTES + 1:
        return f"final bytes without a newline are longer than one append ({len(tail)} > {MAX_RECORD_BYTES + 1})", None
    if tail[:1] not in (b"{", b"\x00"):
        return "final bytes without a newline cannot start a record", None
    head, _, rest = tail.partition(b"\x00")
    if not head:  # the start is zero-filled: what follows cannot be checked
        return "", None
    text = head.decode("utf-8", errors="replace")
    try:
        _complete, end = _DECODER.raw_decode(text)
    except ValueError:
        return "", None  # an incomplete record: the interrupted append
    except RecursionError:
        return "final bytes without a newline nest deeper than any record", None
    if end != len(text) or rest.strip(b"\x00"):
        return "final bytes without a newline hold a complete value followed by other bytes", None
    value, problem = _record_problem(head)
    if problem or value is None:
        return f"final bytes without a newline hold a complete value that is not a valid record: {problem}", None
    return "", value  # D-046: torn only if the fold accepts it as the next record


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
        if nl == -1:  # D-044: only an incomplete physical record (no terminating newline) can be a torn tail
            tail_problem, complete = _tail_problem(data[pos:])
            if tail_problem:  # D44-R2: bytes no interrupted append can leave are corruption
                raise InvariantViolation("M-2", "JOURNAL_CORRUPT", f"line {len(records)}: {tail_problem}", len(records))
            torn = TornTail(pos, len(data) - pos, "final line has no newline", complete)
            return JournalRead(records, lines, len(data), torn)
        value, problem = _record_problem(data[pos:nl])
        if problem:  # a complete physical record that is invalid: corruption, final line or not (D-044)
            raise InvariantViolation("M-2", "JOURNAL_CORRUPT", f"line {len(records)}: {problem}", len(records))
        if value is None:  # unreachable: no problem means a parsed object
            raise InvariantViolation("M-2", "JOURNAL_CORRUPT", "unparsed record", len(records))
        records.append(value)
        lines.append(data[pos:nl])
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
