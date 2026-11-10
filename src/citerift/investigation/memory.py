"""Investigation Memory: one investigation directory, its journal, blobs and lock (SPEC 8, 10.1, 10.2).

Layout under the memory root (S-8.1)::

    <investigation_key>/        64 lowercase hex digits; no path component comes from request text
        journal.jsonl           the authoritative record (canonical JSON lines, hash chained)
        blobs/<sha256>          canonical JSON blobs addressed by their SHA-256
        lock                    flock target; content informational only
        journal.jsonl.torn-<k>  preserved copies of journals that had a torn tail (never read as authority)

The journal is the only authoritative state. ``InvestigationMemory`` holds no other state: on open it reads the
journal, verifies every record and the blobs it names, and rebuilds its view with ``Folder``; every append is checked
against that view before it is written. There is no index, cache or status file that could disagree with the journal.

Creation is atomic: the directory is prepared under a temporary name in the memory root (journal holding the
``investigation_created`` record, empty ``blobs``), ``fsync``ed, and renamed into place. A second creation of the same
request finds the directory and opens it (S-9.4).
"""

from __future__ import annotations

import contextlib
import copy
import os
import secrets
import shutil
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from citerift.investigation import faults, ids
from citerift.investigation.blobs import BlobStore
from citerift.investigation.canonical import canon
from citerift.investigation.errors import (
    AppendRefused,
    CorruptInvestigation,
    InvariantViolation,
    InvestigationMemoryError,
    PathUnsafe,
    StorageError,
)
from citerift.investigation.fold import Folder
from citerift.investigation.fsutil import (
    check_memory_root,
    check_private_dir,
    fsync_dir,
    is_hex64,
    lstat_at,
    open_dir,
    open_regular,
    read_all,
)
from citerift.investigation.journal import (
    JOURNAL,
    MAX_JOURNAL_BYTES,
    MAX_RECORD_BYTES,
    TORN_PREFIX,
    JournalRead,
    append_line,
    open_for_append,
    parse_journal,
    remove_stale_journal_temporaries,
    repair_torn_tail,
    write_new_file,
)
from citerift.investigation.lock import LOCK, InvestigationLock

BLOBS = "blobs"
CREATING_PREFIX = ".creating-"
Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _fmt(at: datetime) -> str:
    return at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def created_payload(
    request: dict[str, Any],
    stage04: dict[str, Any],
    *,
    bundle_capture_sha256: str | None = None,
) -> dict[str, Any]:
    """The ``investigation_created`` payload a request implies (S-4.7, MM 2.3). A retained-bundle request needs the
    bundle's ``capture_sha256``, which the caller reads and verifies with Stage 03 first."""
    live = ids.live_request_key(request)
    if live is not None:
        request_key = live
    else:
        if bundle_capture_sha256 is None:
            raise InvestigationMemoryError("INPUT_INVALID", "a retained-bundle request needs the capture digest")
        request_key = {"capture_sha256": bundle_capture_sha256}
    cfg = request.get("config") or {}
    cdig = ids.config_digest(cfg)
    key = ids.investigation_key(request_key, str(cfg.get("plan_version")), cdig)
    return {
        "request": copy.deepcopy(request),  # never shared with the caller (review finding R6-4)
        "request_key": request_key,
        "investigation_key": key,
        "investigation_id": ids.investigation_id(key),
        "config_digest": cdig,
        "stage04": copy.deepcopy(stage04),
        "migrated_from": None,
    }


def _record(
    seq: int, prev: str, kind: str, step: str | None, attempt: int | None, at: str, root_id: str | None, payload: Any
) -> dict[str, Any]:
    rec = {
        "v": 1,
        "seq": seq,
        "prev": prev,
        "kind": kind,
        "step": step,
        "attempt": attempt,
        "at": at,
        "root_id": root_id,
        "payload": payload,
    }
    rec["digest"] = ids.record_digest(rec)
    return rec


class InvestigationMemory:
    """An open investigation. Writable instances hold the lock until ``close``."""

    def __init__(
        self,
        root_fd: int,
        inv_fd: int,
        blobs_fd: int,
        lock: InvestigationLock,
        key: str,
        folder: Folder,
        torn: JournalRead | None,
        writable: bool,
        clock: Clock,
    ) -> None:
        self._root_fd, self._inv_fd, self._blobs_fd = root_fd, inv_fd, blobs_fd
        self._lock = lock
        self.key = key
        self.view = folder
        self.blobs = BlobStore(blobs_fd)
        self.torn_tail = torn.torn if torn is not None else None
        self.writable = writable
        self._clock = clock
        self._append_fd = open_for_append(inv_fd) if writable else -1
        self._poisoned = False

    # Opening and creating ------------------------------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        memory_root: Path | str,
        payload: dict[str, Any],
        *,
        clock: Clock = _utc_now,
        repository: Path | None = None,
    ) -> InvestigationMemory:
        """Create the investigation the payload names, or open it when it exists with the same payload."""
        root = check_memory_root(memory_root, repository=repository)
        key = payload.get("investigation_key")
        if not isinstance(key, str) or not is_hex64(key):
            raise PathUnsafe("PATH_UNSAFE", "investigation_key is not 64 hex digits")
        payload = copy.deepcopy(payload)
        rec0 = _record(0, ids.genesis(key), "investigation_created", None, None, _fmt(clock()), None, payload)
        try:
            Folder(None, expected_key=key).check(rec0)
        except InvariantViolation as exc:
            raise AppendRefused(exc.invariant, exc.code, exc.reason, 0) from exc
        root_fd = open_dir(root)
        try:
            if lstat_at(key, root_fd) is None:
                cls._create_dir(root_fd, key, canon(rec0))
        finally:
            os.close(root_fd)
        mem = cls.open(root, key, clock=clock, repository=repository)
        if mem.view.created != payload:
            mem.close()
            raise InvestigationMemoryError(
                "INVESTIGATION_REQUEST_DIFFERS", f"{key} exists with another creation payload; nothing was changed"
            )
        return mem

    @staticmethod
    def _create_dir(root_fd: int, key: str, line: bytes) -> None:
        tmp = f"{CREATING_PREFIX}{secrets.token_hex(8)}"
        os.mkdir(tmp, 0o700, dir_fd=root_fd)
        try:
            tmp_fd = open_dir(tmp, dir_fd=root_fd)
            try:
                os.mkdir(BLOBS, 0o700, dir_fd=tmp_fd)
                write_new_file(JOURNAL, tmp_fd, line + b"\n")
                write_new_file(LOCK, tmp_fd, b"")
                blobs_fd = open_dir(BLOBS, dir_fd=tmp_fd)
                try:
                    fsync_dir(blobs_fd)
                finally:
                    os.close(blobs_fd)
                fsync_dir(tmp_fd)
            finally:
                os.close(tmp_fd)
            faults.point("create.prepared")
            try:
                os.rename(tmp, key, src_dir_fd=root_fd, dst_dir_fd=root_fd)
            except OSError:
                if lstat_at(key, root_fd) is None:
                    raise
                # another creator won the race; its directory is opened instead
            faults.point("create.renamed")
            fsync_dir(root_fd)
        finally:
            if lstat_at(tmp, root_fd) is not None:
                shutil.rmtree(tmp, dir_fd=root_fd, ignore_errors=True)

    @classmethod
    def open(
        cls,
        memory_root: Path | str,
        key: str,
        *,
        writable: bool = True,
        clock: Clock = _utc_now,
        repository: Path | None = None,
    ) -> InvestigationMemory:
        """Open an investigation, taking its lock (SPEC 10.1). A torn tail is preserved and removed when ``writable``;
        a read-only open reports it and changes nothing. Any other violation raises CorruptInvestigation."""
        root = check_memory_root(memory_root, repository=repository)
        if not is_hex64(key):
            raise PathUnsafe("PATH_UNSAFE", f"{str(key)[:80]!r} is not an investigation key")
        root_fd = open_dir(root)
        fds = [root_fd]
        lock: InvestigationLock | None = None
        try:
            check_private_dir(root_fd, str(root), "MEMORY_ROOT_UNSAFE")
            inv_fd = open_dir(key, dir_fd=root_fd)
            fds.append(inv_fd)
            check_private_dir(inv_fd, "the investigation directory")
            lock = InvestigationLock(inv_fd, writable=writable)
            blobs_fd = open_dir(BLOBS, dir_fd=inv_fd)
            fds.append(blobs_fd)
            check_private_dir(blobs_fd, "the blobs directory")
            try:
                read, raw = _read(inv_fd)
                found = read  # what was found on disk; ``torn_tail`` reports it even after a repair
                store = BlobStore(blobs_fd)
                folder = Folder(store.verify, expected_key=key)
                if not read.records:
                    raise InvariantViolation("M-1", "JOURNAL_CORRUPT", "the journal holds no record", 0)
                # Validate everything before changing anything: a CORRUPT investigation is never repaired, not even
                # its torn tail or its temporaries (SPEC 8.6, 10.1; D-044).
                for rec in read.records:
                    folder.apply(rec)
                if read.torn is not None and writable:
                    remove_stale_journal_temporaries(inv_fd)
                    repair_torn_tail(inv_fd, read, raw)
                    again, _ = _read(inv_fd)
                    if again.torn is not None or again.lines != read.lines:
                        raise InvariantViolation("M-2", "JOURNAL_CORRUPT", "repaired journal is not the valid prefix")
                if writable:
                    remove_stale_journal_temporaries(inv_fd)
                    store.remove_temporaries()
                    # A crash may have left a rename or link not yet durable (for example between the creation
                    # rename and the memory root fsync): make the directory entries durable before the first append
                    # (review finding R6-5).
                    for fd in (blobs_fd, inv_fd, root_fd):
                        fsync_dir(fd)
            except InvariantViolation as exc:
                raise CorruptInvestigation(exc) from exc
            mem = cls(root_fd, inv_fd, blobs_fd, lock, key, folder, found, writable, clock)
            return mem
        except BaseException:
            if lock is not None:
                lock.release()
            for fd in fds:
                os.close(fd)
            raise

    @staticmethod
    def creation_leftovers(memory_root: Path | str, *, repository: Path | None = None) -> list[str]:
        """``.creating-*`` directories left by a crash before a creation rename. They are never an investigation and
        are reported, not removed: removing them safely would need a lock on the memory root, which SPEC 10.1 does
        not define."""
        root = check_memory_root(memory_root, repository=repository)
        return sorted(n for n in os.listdir(root) if n.startswith(CREATING_PREFIX))

    # Writing -------------------------------------------------------------------------------------------------------

    def put_blob(self, value: Any) -> str:
        """Publish a JSON value as a canonical blob (S-8.2); returns its digest. Must precede any record naming it."""
        self._writable()
        return self.blobs.put(canon(value, allow_float=True))

    def put_blob_bytes(self, data: bytes) -> str:
        self._writable()
        return self.blobs.put(data)

    def append(self, kind: str, payload: Any, *, step: str | None = None, attempt: int | None = None) -> dict[str, Any]:
        """Append one record after checking it against every Memory invariant; returns the written record.

        ``seq``, ``prev``, ``at``, ``root_id`` and ``digest`` are set here: ``root_id`` is the bound root (null before
        the bind), and for the ACQUIRE ``step_succeeded`` the root its payload binds. ``at`` never decreases (M-1)."""
        self._writable()
        payload = copy.deepcopy(payload)  # the record never aliases the caller's objects (review finding R6-4)
        f = self.view
        seq = len(f.records)
        binds = kind == "step_succeeded" and step == "ACQUIRE" and isinstance(payload, dict)
        root = payload.get("root") if binds else None
        root_id = root.get("root_id") if isinstance(root, dict) else f.root_id
        now = self._clock()
        if f.last_at is not None and now < f.last_at:
            now = f.last_at
        if f.last_digest is None:
            raise InvestigationMemoryError("JOURNAL_CORRUPT", "no record to chain to")
        rec = _record(seq, f.last_digest, kind, step, attempt, _fmt(now), root_id, payload)
        line = canon(rec)
        if len(line) > MAX_RECORD_BYTES:
            raise AppendRefused("S-8.3", "RECORD_TOO_LARGE", f"{len(line)} bytes", seq)
        if os.fstat(self._append_fd).st_size + len(line) + 1 > MAX_JOURNAL_BYTES:
            raise AppendRefused(
                "S-8.3", "JOURNAL_TOO_LARGE", f"the journal would exceed {MAX_JOURNAL_BYTES} bytes", seq
            )
        try:
            f.check(rec)
        except InvariantViolation as exc:
            raise AppendRefused(exc.invariant, exc.code, exc.reason, exc.seq) from exc
        if not self._lock.still_held():  # M-11: the lock file was removed or replaced under us
            self._poisoned = True
            raise InvestigationMemoryError("LOCK_LOST", "the lock file no longer designates the held lock")
        # From here on any failure, of any type, leaves the instance unusable: the file and the view may disagree,
        # and only a reopen (which folds the journal) can tell which records are committed (review finding R6-1).
        try:
            append_line(self._append_fd, line)
            f.apply(rec)
        except BaseException:
            self._poisoned = True
            raise
        return copy.deepcopy(rec)

    def _writable(self) -> None:
        if not self.writable:
            raise InvestigationMemoryError("READ_ONLY", "opened read-only")
        if self._poisoned:
            raise StorageError("a previous write failed; reopen the investigation to recover")

    # Inspection ----------------------------------------------------------------------------------------------------

    def torn_copies(self) -> list[str]:
        return sorted(n for n in os.listdir(self._inv_fd) if n.startswith(TORN_PREFIX))

    def orphan_blobs(self) -> list[str]:
        """Published blobs no record names (a crash between publication and the record, SPEC 10.2); kept."""
        named = self.view.referenced_blobs()
        return [n for n in self.blobs.names() if n not in named]

    def close(self) -> None:
        if self._append_fd >= 0:
            os.close(self._append_fd)
            self._append_fd = -1
        self._lock.release()
        for fd in (self._blobs_fd, self._inv_fd, self._root_fd):
            with contextlib.suppress(OSError):
                os.close(fd)
        self._blobs_fd = self._inv_fd = self._root_fd = -1

    def __enter__(self) -> InvestigationMemory:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def _read(inv_fd: int) -> tuple[JournalRead, bytes]:
    try:
        fd = open_regular(JOURNAL, inv_fd)
    except PathUnsafe as exc:
        raise InvariantViolation("M-2", "JOURNAL_CORRUPT", exc.detail) from exc
    try:
        raw = read_all(fd, MAX_JOURNAL_BYTES)
    except PathUnsafe as exc:
        raise InvariantViolation("M-2", "JOURNAL_CORRUPT", exc.detail) from exc
    finally:
        os.close(fd)
    return parse_journal(raw), raw
