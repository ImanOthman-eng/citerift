"""Content-addressed blob store: ``blobs/<sha256>`` (SPEC S-8.2, M-3; owner Step 6 item 5).

A blob is canonical JSON named by the SHA-256 of its bytes, or, for the exact bytes of a retained Stage 03 capture
(``capture.json`` and its artifacts, Step 8 IF-7), a *raw* blob: the same content addressing and publication, without
the canonical-JSON requirement. A raw blob is named only from a bundle observation manifest, which states its size, so
Memory checks it by hash and size (``verify_raw``) and never parses it. Publication:

1. create a temporary file in ``blobs/`` (``O_CREAT | O_EXCL | O_NOFOLLOW``);
2. write, then ``fsync``;
3. re-read the temporary file and verify its digest;
4. publish it under its digest with ``link``, which never replaces an existing name (unlike ``rename``);
5. remove the temporary name and ``fsync`` the directory;
6. only then may a journal record name the blob (the caller appends after ``put`` returns).

An existing blob of the same name is verified and treated as success (idempotent). An existing name whose bytes do
not hash to it is corruption: it is reported and never overwritten. Readers see either no blob or a complete one,
because a name appears only by the atomic ``link`` of a complete, verified file.
"""

from __future__ import annotations

import contextlib
import os
import secrets
import stat
from collections.abc import Callable

from citerift.investigation import faults
from citerift.investigation.canonical import loads_blob, sha256_hex
from citerift.investigation.errors import BlobError, CanonError, PathUnsafe, StorageError
from citerift.investigation.fsutil import (
    O_CLOEXEC,
    O_NOFOLLOW,
    fsync_dir,
    is_hex64,
    lstat_at,
    open_regular,
    read_all,
    write_all,
)

MAX_BLOB_BYTES = 256 * 1024 * 1024  # the Stage 03 extraction bound (src/citerift/wiki/verify.py)
TEMP_PREFIX = ".tmp-"


class BlobStore:
    """Blobs of one investigation. ``dir_fd`` is an open descriptor of the real ``blobs`` directory."""

    def __init__(self, dir_fd: int) -> None:
        self.dir_fd = dir_fd

    # Reading -----------------------------------------------------------------------------------------------------

    def get(self, digest: str, *, limit: int = MAX_BLOB_BYTES) -> bytes:
        """The verified bytes of a blob: BLOB_MISSING, BLOB_CORRUPT or BLOB_TOO_LARGE otherwise."""
        if not is_hex64(digest):
            raise BlobError("BLOB_MISSING", f"{str(digest)[:80]!r} is not a blob name")
        st = lstat_at(digest, self.dir_fd)
        if st is None:
            raise BlobError("BLOB_MISSING", digest)
        if not stat.S_ISREG(st.st_mode):
            raise BlobError("BLOB_CORRUPT", f"{digest} is not a regular file")
        if st.st_size > limit:
            raise BlobError("BLOB_TOO_LARGE", f"{digest} has {st.st_size} bytes")
        try:
            fd = open_regular(digest, self.dir_fd)
        except PathUnsafe as exc:
            raise BlobError("BLOB_CORRUPT", exc.detail) from exc
        try:
            data = read_all(fd, limit)
        except PathUnsafe as exc:
            raise BlobError("BLOB_TOO_LARGE", f"{digest} grew while read") from exc
        finally:
            os.close(fd)
        if sha256_hex(data) != digest:
            raise BlobError("BLOB_CORRUPT", f"{digest} does not hash to its name")
        return data

    def verify(self, digest: str) -> None:
        """M-3: the blob exists, is a regular file, hashes to its name and is canonical JSON."""
        data = self.get(digest)
        try:
            loads_blob(data)
        except CanonError as exc:
            raise BlobError("BLOB_CORRUPT", f"{digest}: {exc.detail}") from exc

    def verify_raw(self, digest: str, size: int) -> None:
        """M-3 for a raw blob (IF-7): it exists, is a regular file of ``size`` bytes and hashes to its name."""
        data = self.get(digest, limit=max(size, 0))
        if len(data) != size:
            raise BlobError("BLOB_CORRUPT", f"{digest} has {len(data)} bytes, not the {size} its manifest states")

    def exists(self, digest: str) -> bool:
        return is_hex64(digest) and lstat_at(digest, self.dir_fd) is not None

    # Writing -----------------------------------------------------------------------------------------------------

    def put(self, data: bytes) -> str:
        """Publish canonical JSON bytes; return their digest. Idempotent for equal bytes."""
        if len(data) > MAX_BLOB_BYTES:
            raise BlobError("BLOB_TOO_LARGE", f"{len(data)} bytes")
        loads_blob(data)  # CanonError unless canonical JSON
        return self._publish(data, self.verify)

    def put_raw(self, data: bytes) -> str:
        """Publish exact bytes of any content as a raw blob (IF-7); return their digest. Idempotent for equal bytes."""
        if not isinstance(data, bytes):
            raise BlobError("BLOB_CORRUPT", f"a raw blob is bytes, not {type(data).__name__}")
        if len(data) > MAX_BLOB_BYTES:
            raise BlobError("BLOB_TOO_LARGE", f"{len(data)} bytes")
        return self._publish(data, lambda d: self.verify_raw(d, len(data)))

    def _publish(self, data: bytes, check: Callable[[str], None]) -> str:
        digest = sha256_hex(data)
        if self.exists(digest):
            check(digest)
            # The name may come from a put whose directory fsync failed or never ran: make it durable again before
            # any record may name it (M-3 order; review finding R6-3).
            try:
                fd = open_regular(digest, self.dir_fd)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
                fsync_dir(self.dir_fd)
            except OSError as exc:
                raise StorageError(f"blob {digest}: {exc.strerror}") from exc
            return digest
        tmp = f"{TEMP_PREFIX}{os.getpid()}-{secrets.token_hex(8)}"
        fd = -1
        try:
            fd = os.open(tmp, os.O_RDWR | os.O_CREAT | os.O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0o600, dir_fd=self.dir_fd)
            faults.point("blob.before_write", fd=fd, data=data)
            faults.point("blob.during_write", fd=fd, data=data)
            write_all(fd, data)
            os.fsync(fd)
            faults.point("blob.after_fsync")
            os.lseek(fd, 0, os.SEEK_SET)
            if sha256_hex(read_all(fd, MAX_BLOB_BYTES)) != digest:
                raise BlobError("BLOB_CORRUPT", f"temporary file for {digest} does not hash to it after writing")
            os.close(fd)
            fd = -1
            faults.point("blob.before_link")
            try:
                os.link(tmp, digest, src_dir_fd=self.dir_fd, dst_dir_fd=self.dir_fd, follow_symlinks=False)
            except FileExistsError:
                check(digest)  # a concurrent publisher won; equal bytes, or corruption reported
            faults.point("blob.after_link")
            os.unlink(tmp, dir_fd=self.dir_fd)
            fsync_dir(self.dir_fd)
            faults.point("blob.published")
        except OSError as exc:
            raise StorageError(f"blob {digest}: {exc.strerror}") from exc
        finally:
            if fd >= 0:
                os.close(fd)
            if lstat_at(tmp, self.dir_fd) is not None:
                with contextlib.suppress(OSError):
                    os.unlink(tmp, dir_fd=self.dir_fd)
        return digest

    def temporaries(self) -> list[str]:
        """Leftover temporary files of interrupted publications (never named by a record)."""
        return sorted(n for n in os.listdir(self.dir_fd) if n.startswith(TEMP_PREFIX))

    def remove_temporaries(self) -> list[str]:
        """Remove leftover temporaries. Only the lock holder calls this; a temporary is never a blob name."""
        removed = []
        for name in self.temporaries():
            st = lstat_at(name, self.dir_fd)
            if st is not None and (stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode)):
                os.unlink(name, dir_fd=self.dir_fd)
                removed.append(name)
        if removed:
            fsync_dir(self.dir_fd)
        return removed

    def names(self) -> list[str]:
        """Published blob names (orphans included: blobs no record names, kept and reported, SPEC 10.2)."""
        return sorted(n for n in os.listdir(self.dir_fd) if is_hex64(n))
