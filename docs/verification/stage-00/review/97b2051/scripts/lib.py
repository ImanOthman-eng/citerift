"""Shared helpers for the review3 reproduction scripts.

Every script works only in throwaway directories under $W/sandbox-*; nothing in the
reviewed working copy is changed. Run with the reviewed tree's interpreter, e.g.
    $W/base/.venv/bin/python $W/scripts/<script>.py
where $W/base is a clone of the reviewed revision 4a396fb.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

W = Path(os.environ.get("W", "/tmp/claude-0/-home-user-citerift/0bbaf0e6-71eb-560d-84bf-668fa4ffb288/scratchpad/review4"))
BASE = W / "base"
sys.path[:0] = [str(BASE / "src"), str(BASE / "tests" / "stage00")]

from sandbox_repo import Sandbox, git  # noqa: E402

PY = str(BASE / ".venv" / "bin" / "python")


def new_sandbox(name: str) -> Sandbox:
    parent = W / f"sandbox-{name}"
    if parent.exists():
        shutil.rmtree(parent)
    parent.mkdir(parents=True)
    return Sandbox(parent / "repo")


def clone_base(name: str) -> Path:
    """A fresh clone of the reviewed revision, for experiments that need the real tree."""
    dest = W / f"sandbox-{name}"
    if dest.exists():
        shutil.rmtree(dest)
    subprocess.run(["git", "clone", "-q", str(BASE), str(dest)], check=True)
    return dest


def run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    full = {**os.environ, "PYTHONPATH": str(BASE / "src"), **(env or {})}
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=full)


def codes(findings) -> list[str]:
    return sorted({f.code for f in findings if f.severity == "error"})
