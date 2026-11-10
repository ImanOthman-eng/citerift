"""Single writer: an exclusive, non-blocking ``flock`` on the investigation's ``lock`` file (SPEC 10.1, M-11).

Ownership is the kernel lock alone. The kernel releases it when the holder exits or is killed, so a stale lock
cannot exist on a local file system. The file's content (process id, start time) is informational and is never
read to decide ownership; the file's existence means nothing. Network file systems are not supported (RA R4-26).
"""

from __future__ import annotations

import fcntl
import os
import stat
import time

from citerift.investigation.errors import Busy, PathUnsafe
from citerift.investigation.fsutil import O_CLOEXEC, O_NOFOLLOW, O_NONBLOCK, lstat_at, write_all

LOCK = "lock"


class InvestigationLock:
    """The lock file is created once, with the investigation, and never again: an open of an investigation whose lock
    file is missing is refused (``PATH_UNSAFE``), because recreating it could admit a second writer while a process
    still holds a lock on the unlinked file (review finding R6-7). ``writable`` rewrites the informational content;
    a read-only open writes nothing (a CORRUPT investigation is not changed by being looked at, R6-8)."""

    def __init__(self, inv_fd: int, *, writable: bool = True) -> None:
        for _ in range(3):
            fd = self._open(inv_fd, writable)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                os.close(fd)
                raise Busy("another process holds the investigation lock") from exc
            except OSError:
                os.close(fd)
                raise
            # The lock is the inode, not the name: if ``lock`` was unlinked or replaced while we waited, our flock is
            # on a file nobody else will lock. Lock the file the name designates now (review finding R6-7).
            held, now = os.fstat(fd), lstat_at(LOCK, inv_fd)
            if now is not None and (now.st_dev, now.st_ino) == (held.st_dev, held.st_ino):
                break
            os.close(fd)
        else:
            raise Busy("the lock file keeps changing under the lock")
        self.fd = fd
        self._inv_fd = inv_fd
        if writable:
            try:
                os.ftruncate(fd, 0)
                os.lseek(fd, 0, os.SEEK_SET)
                write_all(fd, f"pid {os.getpid()} since {time.time():.0f}\n".encode())
            except OSError:
                pass  # informational only

    @staticmethod
    def _open(inv_fd: int, writable: bool) -> int:
        flags = os.O_RDWR if writable else os.O_RDONLY
        try:
            fd = os.open(LOCK, flags | O_NOFOLLOW | O_CLOEXEC | O_NONBLOCK, 0o600, dir_fd=inv_fd)
        except OSError as exc:
            raise PathUnsafe("PATH_UNSAFE", f"lock file: {exc.strerror}") from exc
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            os.close(fd)
            raise PathUnsafe("PATH_UNSAFE", "lock is not a regular file")
        os.set_blocking(fd, True)
        return fd

    def still_held(self) -> bool:
        """The name ``lock`` still designates the locked file (checked before every append)."""
        if self.fd < 0:
            return False
        held, now = os.fstat(self.fd), lstat_at(LOCK, self._inv_fd)
        return now is not None and (now.st_dev, now.st_ino) == (held.st_dev, held.st_ino)

    def release(self) -> None:
        if self.fd >= 0:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_UN)
            finally:
                os.close(self.fd)
                self.fd = -1
