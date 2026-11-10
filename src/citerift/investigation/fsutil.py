"""Small POSIX helpers: no symbolic links, regular files only, fsync of files and directories (S-15.3, S-8.2).

Files inside an investigation directory are opened relative to a directory file descriptor with ``O_NOFOLLOW``, so a
symbolic link swapped in for a file is refused, and a path is never built from request text: every name is a fixed
constant or a SHA-256 hex digest.
"""

from __future__ import annotations

import os
import re
import stat
from pathlib import Path

from citerift.investigation.errors import PathUnsafe

HEX64 = re.compile(r"^[0-9a-f]{64}$")
O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
O_DIRECTORY = getattr(os, "O_DIRECTORY", 0)
O_CLOEXEC = getattr(os, "O_CLOEXEC", 0)
O_NONBLOCK = getattr(os, "O_NONBLOCK", 0)


def is_hex64(name: object) -> bool:
    return isinstance(name, str) and HEX64.match(name) is not None


def open_dir(path: Path | str, *, dir_fd: int | None = None) -> int:
    """Open a real directory (not a symbolic link) and return its file descriptor."""
    try:
        fd = os.open(path, os.O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC, dir_fd=dir_fd)
    except OSError as exc:
        raise PathUnsafe("PATH_UNSAFE", f"{path}: not an accessible real directory ({exc.strerror})") from exc
    if not stat.S_ISDIR(os.fstat(fd).st_mode):
        os.close(fd)
        raise PathUnsafe("PATH_UNSAFE", f"{path} is not a directory")
    return fd


def lstat_at(name: str, dir_fd: int) -> os.stat_result | None:
    try:
        return os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None


def open_regular(name: str, dir_fd: int, flags: int = os.O_RDONLY) -> int:
    """Open an existing regular file relative to ``dir_fd``; symbolic links and other file types are refused.

    The open is non-blocking, so a FIFO or device swapped in for the file cannot block the caller; the type is then
    checked on the descriptor itself (no check-then-open race) and blocking mode restored for the regular file."""
    try:
        fd = os.open(name, flags | O_NOFOLLOW | O_CLOEXEC | O_NONBLOCK, dir_fd=dir_fd)
    except OSError as exc:
        raise PathUnsafe("PATH_UNSAFE", f"{name}: cannot open as a regular file ({exc.strerror})") from exc
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        raise PathUnsafe("PATH_UNSAFE", f"{name} is not a regular file")
    os.set_blocking(fd, True)
    return fd


def read_all(fd: int, limit: int) -> bytes:
    """Read a whole file, refusing one larger than ``limit`` bytes."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = os.read(fd, 1 << 20)
        if not chunk:
            return b"".join(chunks)
        total += len(chunk)
        if total > limit:
            raise PathUnsafe("PATH_UNSAFE", f"file larger than {limit} bytes")
        chunks.append(chunk)


def write_all(fd: int, data: bytes) -> None:
    view = memoryview(data)
    while view:
        written = os.write(fd, view)
        view = view[written:]


def fsync_dir(dir_fd: int) -> None:
    os.fsync(dir_fd)


def check_memory_root(path: Path | str, *, repository: Path | None = None) -> Path:
    """The memory root must be an absolute, existing real directory, not writable by group or others, and outside
    the repository working tree (S-15.3, MR-13). Returns the resolved path."""
    p = Path(path)
    if not p.is_absolute():
        raise PathUnsafe("MEMORY_ROOT_UNSAFE", f"{path} is not absolute")
    try:
        st = os.lstat(p)
    except OSError as exc:
        raise PathUnsafe("MEMORY_ROOT_UNSAFE", f"{path}: {exc.strerror}") from exc
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
        raise PathUnsafe("MEMORY_ROOT_UNSAFE", f"{path} is not a real directory")
    if st.st_mode & 0o022:
        raise PathUnsafe("MEMORY_ROOT_UNSAFE", f"{path} is writable by group or others")
    if st.st_uid != os.geteuid():
        raise PathUnsafe("MEMORY_ROOT_UNSAFE", f"{path} is not owned by this user")
    resolved = p.resolve(strict=True)
    for parent in (resolved, *resolved.parents):
        if os.path.lexists(parent / ".git"):
            raise PathUnsafe("MEMORY_ROOT_UNSAFE", f"{path} is inside a repository working tree ({parent})")
    if repository is not None:
        repo = repository.resolve()
        if resolved == repo or repo in resolved.parents:
            raise PathUnsafe("MEMORY_ROOT_UNSAFE", f"{path} is inside the repository {repo}")
    return resolved


def check_private_dir(fd: int, what: str, code: str = "PATH_UNSAFE") -> None:
    """Re-check an opened directory on its descriptor (no check-then-open race): a directory owned by this user and
    not writable by group or others (review finding R6-10)."""
    st = os.fstat(fd)
    if not stat.S_ISDIR(st.st_mode):
        raise PathUnsafe(code, f"{what} is not a directory")
    if st.st_uid != os.geteuid():
        raise PathUnsafe(code, f"{what} is not owned by this user")
    if st.st_mode & 0o022:
        raise PathUnsafe(code, f"{what} is writable by group or others")
