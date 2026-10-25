"""Read-only git queries used to verify revision references."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class GitUnavailableError(RuntimeError):
    """Raised when git or the repository history cannot be queried."""


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    git = shutil.which("git")
    if git is None:
        raise GitUnavailableError("git executable not found")
    return subprocess.run(  # noqa: S603 - fixed executable, no shell, list arguments
        [git, "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def is_repository(root: Path) -> bool:
    try:
        return _git(root, "rev-parse", "--git-dir").returncode == 0
    except GitUnavailableError:
        return False


def is_shallow(root: Path) -> bool:
    out = _git(root, "rev-parse", "--is-shallow-repository")
    return out.returncode == 0 and out.stdout.strip() == "true"


def head(root: Path) -> str | None:
    out = _git(root, "rev-parse", "--verify", "--quiet", "HEAD")
    return out.stdout.strip() if out.returncode == 0 else None


def branch(root: Path) -> str | None:
    out = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    return out.stdout.strip() if out.returncode == 0 else None


def commit_exists(root: Path, sha: str) -> bool:
    if not SHA_RE.match(sha):
        return False
    return _git(root, "cat-file", "-e", f"{sha}^{{commit}}").returncode == 0


def is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    """True when ``ancestor`` is ``descendant`` or one of its ancestors."""
    return _git(root, "merge-base", "--is-ancestor", ancestor, descendant).returncode == 0


def last_commit_touching(root: Path, paths: list[str], rev: str = "HEAD") -> str | None:
    if not paths:
        return None
    out = _git(root, "log", "-1", "--format=%H", rev, "--", *paths)
    if out.returncode != 0:
        raise GitUnavailableError(out.stderr.strip())
    sha = out.stdout.strip()
    return sha or None


def changed_paths(root: Path, base: str, paths: list[str], rev: str = "HEAD") -> list[str]:
    """Files under ``paths`` whose content differs between ``base`` and ``rev``.

    This compares trees, not history, so a merge that brings back old content
    is seen as a change (``git log -- paths`` simplifies such merges away).
    """
    if not paths:
        return []
    out = _git(root, "diff", "--no-renames", "--name-only", base, rev, "--", *paths)
    if out.returncode != 0:
        raise GitUnavailableError(out.stderr.strip())
    return out.stdout.splitlines()


def dirty_paths(root: Path, exclude: tuple[str, ...] = ()) -> list[str]:
    """Paths with uncommitted changes, including untracked files."""
    out = _git(root, "status", "--porcelain", "--untracked-files=all")
    if out.returncode != 0:
        raise GitUnavailableError(out.stderr.strip())
    paths = []
    for line in out.stdout.splitlines():
        path = line[3:].split(" -> ")[-1].strip('"')
        if path not in exclude:
            paths.append(path)
    return paths
