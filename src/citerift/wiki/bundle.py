"""Capture bundles on disk: atomic publication, path safety and integrity checks (SPECIFICATION.md 9).

A bundle is a directory::

    capture.json            the capture record (schema urn:citerift:schema:wiki:v1:capture)
    artifacts/<sha256>      every retained body, named by the SHA-256 of its bytes

No path is ever derived from an article title. A bundle is written in a fresh temporary directory beside its final
location and renamed into place only when complete; an existing path is never replaced. On reading, the bundle
directory, ``capture.json``, ``artifacts`` and every artifact must be real files or directories (never symbolic
links), artifact names must be 64 lowercase hex digits, and every artifact must hash to its name.
"""

from __future__ import annotations

import os
import re
import shutil
import stat
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from citerift.wiki.canonical import StrictJSONError, loads_strict, pretty_bytes, sha256_hex
from citerift.wiki.issues import Issue

CAPTURE_FILE = "capture.json"
ARTIFACTS = "artifacts"
MAX_CAPTURE_JSON = 4 * 1024 * 1024
MAX_ARTIFACT = 64 * 1024 * 1024
_SHA = re.compile(r"^[0-9a-f]{64}$")


class BundleError(Exception):
    def __init__(self, issue: Issue) -> None:
        super().__init__(f"{issue.code}: {issue.detail}")
        self.issue = issue


def _unsafe(detail: str) -> BundleError:
    return BundleError(Issue("BUNDLE_PATH_UNSAFE", (), detail))


def _check_new_target(target: Path) -> Path:
    """The final path must not exist (not even as a broken link) and its parent must be a real directory."""
    if os.path.lexists(target):
        raise _unsafe(f"{target} already exists")
    parent = target.parent if str(target.parent) else Path(".")
    try:
        st = os.lstat(parent)
    except OSError as exc:
        raise _unsafe(f"parent directory {parent} is not accessible: {exc.strerror}") from exc
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
        raise _unsafe(f"parent {parent} is not a real directory")
    return parent


def _write_new(path: Path, data: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o644)
    try:
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


def publish_bundle(target: Path, capture: dict[str, Any], artifacts: dict[str, bytes]) -> Path:
    """Write a bundle at ``target`` atomically. ``artifacts`` maps SHA-256 to bytes (each is checked)."""
    target = Path(target)
    parent = _check_new_target(target)
    for sha, data in artifacts.items():
        if not _SHA.match(sha) or sha256_hex(data) != sha:
            raise BundleError(Issue("BUNDLE_ARTIFACT_CORRUPT", (), f"artifact {sha[:16]} does not hash to its name"))
    tmp = Path(tempfile.mkdtemp(prefix=".citerift-bundle-", dir=parent))
    try:
        os.mkdir(tmp / ARTIFACTS)
        for sha in sorted(artifacts):
            _write_new(tmp / ARTIFACTS / sha, artifacts[sha])
        _write_new(tmp / CAPTURE_FILE, pretty_bytes(capture))
        if os.path.lexists(target):
            raise _unsafe(f"{target} appeared while the bundle was written")
        os.rename(tmp, target)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    return target


def publish_file(target: Path, data: bytes) -> Path:
    """Write one output file atomically; an existing path is never replaced."""
    target = Path(target)
    parent = _check_new_target(target)
    fd, tmp_name = tempfile.mkstemp(prefix=".citerift-out-", dir=parent)
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        os.unlink(tmp)
        _write_new(tmp, data)
        if os.path.lexists(target):
            raise _unsafe(f"{target} appeared while the file was written")
        os.link(tmp, target)  # fails if target exists: no replacement, unlike rename
        os.unlink(tmp)
    except BaseException:
        if os.path.lexists(tmp):
            os.unlink(tmp)
        raise
    return target


@dataclass
class Bundle:
    path: Path
    capture: dict[str, Any]
    capture_bytes: bytes
    capture_sha256: str
    issues: list[Issue] = field(default_factory=list)

    def artifact(self, sha: str, limit: int = MAX_ARTIFACT) -> bytes:
        return read_artifact(self.path, sha, limit)


def _real(path: Path, kind: str) -> os.stat_result:
    try:
        st = os.lstat(path)
    except OSError as exc:
        raise BundleError(
            Issue(
                "BUNDLE_MALFORMED" if kind != "artifact" else "BUNDLE_ARTIFACT_MISSING",
                (),
                f"{path.name}: {exc.strerror}",
            )
        ) from exc
    if stat.S_ISLNK(st.st_mode):
        raise _unsafe(f"{path} is a symbolic link")
    want_dir = kind == "dir"
    if (want_dir and not stat.S_ISDIR(st.st_mode)) or (not want_dir and not stat.S_ISREG(st.st_mode)):
        raise _unsafe(f"{path} is not a regular {'directory' if want_dir else 'file'}")
    return st


def read_artifact(bundle: Path, sha: str, limit: int = MAX_ARTIFACT) -> bytes:
    if not isinstance(sha, str) or not _SHA.match(sha):
        raise _unsafe(f"artifact name {str(sha)[:80]!r} is not a SHA-256")
    _real(bundle / ARTIFACTS, "dir")
    path = bundle / ARTIFACTS / sha
    st = _real(path, "artifact")
    if st.st_size > limit:
        raise BundleError(Issue("BUNDLE_ARTIFACT_CORRUPT", (), f"artifact {sha[:16]} is larger than {limit} bytes"))
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, "rb") as f:
        data = f.read(limit + 1)
    if len(data) > limit:
        raise BundleError(Issue("BUNDLE_ARTIFACT_CORRUPT", (), f"artifact {sha[:16]} grew while read"))
    if sha256_hex(data) != sha:
        raise BundleError(Issue("BUNDLE_ARTIFACT_CORRUPT", (), f"artifact {sha[:16]} does not hash to its name"))
    return data


def open_bundle(path: Path) -> Bundle:
    """Read ``capture.json`` safely. Schema and semantic checks are in ``verify.py``."""
    path = Path(path)
    _real(path, "dir")
    cfile = path / CAPTURE_FILE
    st = _real(cfile, "file")
    if st.st_size > MAX_CAPTURE_JSON:
        raise BundleError(Issue("BUNDLE_MALFORMED", (), "capture.json is too large"))
    fd = os.open(cfile, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as f:
        data = f.read(MAX_CAPTURE_JSON + 1)
    try:
        capture = loads_strict(data)
    except StrictJSONError as exc:
        raise BundleError(Issue("BUNDLE_MALFORMED", (), str(exc))) from exc
    if not isinstance(capture, dict):
        raise BundleError(Issue("BUNDLE_MALFORMED", (), "capture.json is not an object"))
    return Bundle(path, capture, data, sha256_hex(data))
