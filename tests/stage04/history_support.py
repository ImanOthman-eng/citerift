"""Earlier engine modules read from git (owner decision D-074 style: a historical check runs the historical code).

``module_at(commit, path, name)`` executes the file ``path`` as it is at ``commit`` as a module named ``name`` (never
the working tree's version). The history is required, never skipped: CI checks out the full history.
"""

from __future__ import annotations

import subprocess
import sys
import types
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
# The bib-1 engine of the freeze-3 candidate that owner decision D-085 did not accept (dt-3, engine 0.4.0).
C3854B8 = "c3854b8f386d507ad129ebfb81cf96be7202549e"
BIB_PATH = "src/citerift/investigation/bibliographic.py"


def module_at(commit: str, path: str, name: str) -> types.ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    found = subprocess.run(["git", "cat-file", "-e", commit], cwd=REPO, check=False)
    assert found.returncode == 0, f"commit {commit} is needed (a full git checkout)"
    source = subprocess.run(
        ["git", "show", f"{commit}:{path}"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout
    module = types.ModuleType(name)
    module.__file__ = f"{commit}:{path}"
    sys.modules[name] = module
    exec(compile(source, module.__file__, "exec"), module.__dict__)  # noqa: S102
    return module


def bib1() -> types.ModuleType:
    """bib-1 as committed in the candidate c3854b8 (its alias profile is the unchanged bib-profile-1)."""
    return module_at(C3854B8, BIB_PATH, "bib1_c3854b8")
