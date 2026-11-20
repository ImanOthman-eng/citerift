"""Final corrective cycle (owner decision D-083, item 6, reviewer finding N-01): the provenance every final-cycle tool
records with its output.

N-01 found that the corrective-cycle tools checked only ``src`` and ``schemas`` for uncommitted changes and did not
record their own digest. Here the uncommitted-change check covers every tree a final-cycle result depends on (the
engine, the schemas, the reference models and oracle tools, the final-cycle tools and the test support modules they
import), and the SHA-256 of the running tool is recorded. A result whose ``uncommitted`` list is not empty is not
evidence: every tool refuses to start from such a tree (``start``) and refuses to write a result when the tree
changed during the run (``finish``, reviewer finding D-03), and ``tests/stage04/test_final_provenance.py`` checks every
committed result against its commit.
"""

from __future__ import annotations

import hashlib
import sqlite3
import subprocess
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[4]
# The scientific dependency set of a final-cycle result (N-01): every path whose content can change a decision, a
# reference verdict or a measurement. ``uv.lock`` and ``pyproject.toml`` pin the third-party code.
CHECKED = (
    "src",
    "schemas",
    "simulations/stage04",
    "docs/verification/stage-04/final-cycle",
    "tests/stage04",
    "docs/verification/stage-04/evaluation",
    # inputs (reviewer finding D-03): the campaign bundles, the dt-2 regression a merge cross-checks against and the
    # step 7 generators behind the logical views and the storage bounds.
    "docs/verification/stage-04/evaluation-campaign",
    "docs/verification/stage-04/evaluation-p2-campaign",
    "docs/verification/stage-04/corrective/regression",
    "docs/verification/stage-04/review/step7",
    "pyproject.toml",
    "uv.lock",
)
# Reviewer reports are written while results are computed and never feed a result.
EXCLUDED = ("docs/verification/stage-04/final-cycle/review",)


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout  # noqa: S603, S607


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def index_identity(index_path: Path) -> dict[str, Any]:
    con = sqlite3.connect(f"file:{index_path}?mode=ro", uri=True)
    try:
        meta = dict(con.execute("SELECT key, value FROM meta").fetchall())
    finally:
        con.close()
    out = {k: meta.get(k) for k in ("snapshot_id", "artifact_digest", "semantic_digest", "source_sha256")}
    out["file_sha256"] = file_sha256(index_path)  # the bytes read, beside their own claimed identity (F-03)
    return out


def provenance(tool: Path, index_path: Path | None = None, extra: tuple[str, ...] = ()) -> dict[str, Any]:
    """The committed code a result was computed with: ``code_commit``, the uncommitted paths of the scientific
    dependency set (``CHECKED`` and ``extra``; must be empty), the running tool's SHA-256 and, when given, the index
    identity."""
    checked = (*CHECKED, *extra)
    spec = [*checked, *(f":(exclude){p}" for p in EXCLUDED)]
    dirty = [line[3:] for line in _git("status", "--porcelain", "--untracked-files=all", "--", *spec).splitlines()]
    out: dict[str, Any] = {
        "code_commit": _git("rev-parse", "HEAD").strip(),
        "checked_paths": list(checked),
        "excluded_paths": list(EXCLUDED),
        "uncommitted": sorted(p for p in dirty if "__pycache__" not in p),
        "tool": str(tool.resolve().relative_to(REPO)),
        "tool_sha256": file_sha256(tool),
    }
    if index_path is not None:
        out["index"] = index_identity(index_path)
    return out


def start(tool: Path, index_path: Path | None = None, extra: tuple[str, ...] = ()) -> dict[str, Any]:
    """Reviewer finding D-03: a tool refuses to run from a tree with uncommitted changes in its dependency set."""
    prov = provenance(tool, index_path, extra)
    if prov["uncommitted"]:
        raise SystemExit(f"uncommitted changes in the dependency set, no result is written: {prov['uncommitted']}")
    return prov


def finish(begun: dict[str, Any], tool: Path, index_path: Path | None = None, extra: tuple[str, ...] = ()) -> None:
    """Reviewer finding D-03: the tree must not have changed while the tool ran (call before writing the result)."""
    if provenance(tool, index_path, extra) != begun:
        raise SystemExit("the dependency set changed while the tool ran, no result is written")
