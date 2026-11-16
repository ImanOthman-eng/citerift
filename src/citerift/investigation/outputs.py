"""Writing user-selected outputs safely: exports and D-052 checkpoints (Step 10, owner item 25; SPEC S-15.3).

An output is written only to the path the user names, never inside the memory root (checked on the resolved path, so
a symbolic link into the memory root is refused too), never over an existing path unless the user asked for it (files
only), and never partially: the content goes to a new temporary entry in the same directory (``O_CREAT | O_EXCL |
O_NOFOLLOW``), is ``fsync``-ed, and is then moved into place in one step and the directory ``fsync``-ed. Any failure
removes the temporary entry and leaves the target absent. Names inside an export are fixed names and digests: no title
or article text ever appears in a path.
"""

from __future__ import annotations

import contextlib
import os
import secrets
import shutil
import stat
from collections.abc import Mapping
from pathlib import Path

from citerift.investigation.fsutil import O_CLOEXEC, O_DIRECTORY, O_NOFOLLOW, fsync_dir, write_all


class OperationError(Exception):
    """An operation that cannot proceed; ``status`` names its exit code (``operations.EXIT``)."""

    def __init__(self, status: str, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.status, self.code, self.detail = status, code, detail


def _unsafe(detail: str) -> OperationError:
    return OperationError("invalid", "OUTPUT_PATH_UNSAFE", detail)


def target(out: Path, memory_root: Path, *, overwrite: bool = False) -> tuple[Path, str]:
    """The resolved parent directory and the final name of an output path, after every refusal."""
    name = out.name
    if name in ("", ".", "..") or "/" in name or "\x00" in str(out):
        raise _unsafe(f"{out} does not name a file or directory")
    try:
        parent = out.parent.resolve(strict=True)
    except OSError as exc:
        raise _unsafe(f"{out.parent}: {exc.strerror or exc}") from exc
    st = os.lstat(parent)
    if not stat.S_ISDIR(st.st_mode):
        raise _unsafe(f"{parent} is not a directory")
    try:
        root = Path(memory_root).resolve(strict=True)
    except OSError as exc:
        raise _unsafe(f"memory root {memory_root}: {exc.strerror or exc}") from exc
    final = parent / name
    if final == root or root in final.parents:
        raise _unsafe(f"{out} is inside the memory root; outputs are never written into Investigation Memory")
    if os.path.lexists(final):
        existing = os.lstat(final)
        if stat.S_ISLNK(existing.st_mode):
            raise _unsafe(f"{out} is a symbolic link")
        if not overwrite:
            raise OperationError("invalid", "OUTPUT_EXISTS", f"{out} exists; nothing was overwritten")
        if not stat.S_ISREG(existing.st_mode):
            raise _unsafe(f"{out} exists and is not a regular file")
    return parent, name


def _new_file(dir_fd: int, name: str, data: bytes) -> None:
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0o600, dir_fd=dir_fd)
    try:
        write_all(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)


def write_file(out: Path, data: bytes, memory_root: Path, *, overwrite: bool = False) -> None:
    parent, name = target(out, memory_root, overwrite=overwrite)
    dir_fd = os.open(parent, os.O_RDONLY | O_DIRECTORY | O_CLOEXEC)
    tmp = f".{name}.tmp-{secrets.token_hex(6)}"
    try:
        try:
            _new_file(dir_fd, tmp, data)
            if overwrite:
                os.replace(tmp, name, src_dir_fd=dir_fd, dst_dir_fd=dir_fd)
            else:
                os.link(tmp, name, src_dir_fd=dir_fd, dst_dir_fd=dir_fd, follow_symlinks=False)  # fails if it exists
                os.unlink(tmp, dir_fd=dir_fd)
            fsync_dir(dir_fd)
        except OSError as exc:
            raise OperationError("invalid", "OUTPUT_WRITE_FAILED", f"{out}: {exc.strerror or exc}") from exc
    finally:
        with contextlib.suppress(OSError):
            os.unlink(tmp, dir_fd=dir_fd)
        os.close(dir_fd)


def write_tree(out: Path, files: Mapping[str, bytes], memory_root: Path) -> None:
    """A new directory holding ``files`` (relative paths of fixed names and digests, at most one level deep)."""
    parent, name = target(out, memory_root)
    for rel in files:
        parts = rel.split("/")
        if len(parts) > 2 or any(p in ("", ".", "..") for p in parts):
            raise _unsafe(f"export entry {rel!r} is not a fixed relative name")
    tmp = parent / f".{name}.tmp-{secrets.token_hex(6)}"
    try:
        try:
            os.mkdir(tmp, 0o700)
            tmp_fd = os.open(tmp, os.O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW)
            try:
                subdirs: dict[str, int] = {}
                try:
                    for rel, data in sorted(files.items()):
                        if "/" in rel:
                            sub, leaf = rel.split("/")
                            if sub not in subdirs:
                                os.mkdir(sub, 0o700, dir_fd=tmp_fd)
                                subdirs[sub] = os.open(sub, os.O_RDONLY | O_DIRECTORY | O_CLOEXEC, dir_fd=tmp_fd)
                            _new_file(subdirs[sub], leaf, data)
                        else:
                            _new_file(tmp_fd, rel, data)
                    for fd in subdirs.values():
                        fsync_dir(fd)
                finally:
                    for fd in subdirs.values():
                        os.close(fd)
                fsync_dir(tmp_fd)
            finally:
                os.close(tmp_fd)
            if os.path.lexists(parent / name):
                raise OperationError("invalid", "OUTPUT_EXISTS", f"{out} appeared during the export; nothing replaced")
            os.rename(tmp, parent / name)
            parent_fd = os.open(parent, os.O_RDONLY | O_DIRECTORY | O_CLOEXEC)
            try:
                fsync_dir(parent_fd)
            finally:
                os.close(parent_fd)
        except OSError as exc:
            raise OperationError("invalid", "OUTPUT_WRITE_FAILED", f"{out}: {exc.strerror or exc}") from exc
    finally:
        if os.path.lexists(tmp):
            shutil.rmtree(tmp, ignore_errors=True)
