"""Read-only git queries used to verify revision references."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _env() -> dict[str, str]:
    # Replace refs and grafts can make a commit look like another one; never honour them (V-13).
    # ``--no-replace-objects`` does not disable .git/info/grafts, so the graft file is pointed at
    # an empty one as well (X-09).
    return {**os.environ, "GIT_NO_REPLACE_OBJECTS": "1", "GIT_GRAFT_FILE": os.devnull}


class GitUnavailableError(RuntimeError):
    """Raised when git or the repository history cannot be queried."""


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    git = shutil.which("git")
    if git is None:
        raise GitUnavailableError("git executable not found")
    return subprocess.run(  # noqa: S603 - fixed executable, no shell, list arguments
        [git, "--no-replace-objects", "-C", str(root), *args],
        capture_output=True,
        text=True,
        # A file name that is not UTF-8 must reach the caller, which reports it, not break decoding (Y-11).
        encoding="utf-8",
        errors="surrogateescape",
        check=False,
        env=_env(),
    )


def is_repository(root: Path) -> bool:
    try:
        return _git(root, "rev-parse", "--git-dir").returncode == 0
    except GitUnavailableError:
        return False


def ignored(root: Path, paths: list[str]) -> set[str]:
    """The subset of untracked ``paths`` that git ignores; empty outside a repository."""
    if not paths or not is_repository(root):
        return set()
    git = shutil.which("git")
    if git is None:
        return set()
    out = subprocess.run(  # noqa: S603 - fixed executable, no shell, list arguments
        [git, "--no-replace-objects", "-C", str(root), "check-ignore", "-z", "--stdin"],
        input="\0".join(paths) + "\0",
        capture_output=True,
        text=True,
        check=False,
        env=_env(),
    )
    if out.returncode not in (0, 1):
        raise GitUnavailableError(out.stderr.strip())
    return {p for p in out.stdout.split("\0") if p}


def tracked_files(root: Path, rev: str, path: str) -> list[str]:
    """Files committed under ``path`` at ``rev``; raises when the revision cannot be read."""
    out = _git(root, "ls-tree", "-r", "-z", "--name-only", rev, "--", path)
    if out.returncode != 0:
        raise GitUnavailableError(out.stderr.strip() or f"cannot read {rev}")
    return [p for p in out.stdout.split("\0") if p]


def show(root: Path, rev: str, path: str) -> str | None:
    """The committed content of ``path`` at ``rev``, or None when the file does not exist there."""
    out = _git(root, "cat-file", "-e", f"{rev}:{path}")
    if out.returncode != 0:
        return None
    out = _git(root, "show", f"{rev}:{path}")
    if out.returncode != 0:
        raise GitUnavailableError(out.stderr.strip())
    return out.stdout


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
    """Paths with uncommitted changes, including untracked files, and tracked files whose changes git
    is told to hide (``--assume-unchanged`` or ``--skip-worktree``, which ``git status`` does not show; Y-02)."""
    out = _git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    if out.returncode != 0:
        raise GitUnavailableError(out.stderr.strip())
    paths = []
    fields = out.stdout.split("\0")
    i = 0
    while i < len(fields):
        entry = fields[i]
        i += 1
        if len(entry) < 4:
            continue
        paths.append(entry[3:])
        if entry[0] in "RC":
            # With -z a rename is "XY new\0old\0"; the old path is changed too (O-5 of the third review).
            paths.append(fields[i])
            i += 1
    flags = _git(root, "ls-files", "-v", "-z")
    if flags.returncode != 0:
        raise GitUnavailableError(flags.stderr.strip())
    paths += [e[2:] for e in flags.stdout.split("\0") if len(e) > 2 and (e[0].islower() or e[0] == "S")]
    return [p for p in dict.fromkeys(paths) if p not in exclude]


def is_tracked(root: Path, path: str) -> bool:
    """True when ``path`` is a file in the index."""
    return _git(root, "ls-files", "--error-unmatch", "--", path).returncode == 0


def exists_at(root: Path, rev: str, path: str) -> bool:
    """True when ``path`` is committed at ``rev``."""
    return _git(root, "cat-file", "-e", f"{rev}:{path}").returncode == 0
