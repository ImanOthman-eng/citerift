"""D-045 proof: the only registry difference is the current `notes` value of Stage 01.

Usage (from the repository root):
    uv run python docs/audits/governance-2026-11-10-d045/verify_d045_registry_diff.py [BASE] [TARGET]

BASE defaults to cf2e411 (the commit before the correction). TARGET defaults to the working tree; give a commit
to compare two committed registries. The script compares the parsed JSON values field by field (not the text),
prints every path that differs, and exits non-zero unless exactly one path differs and it is Stage 01 `notes`
with the old and new values recorded in D-045.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REGISTRY = "governance/stage_registry.json"
OLD = (
    "Executed by a separate external agent. The owner reports the investigation was reported externally; its "
    "handoff has not been supplied to this repository and none of its findings are accepted. The exact evidence "
    "file set is fixed when the owner delivers the handoff."
)
NEW = (
    "Executed by a separate external agent. The Stage 01 handoff and supporting evidence are retained under "
    "docs/verification/stage-01/, verified at revision 85da719ac43fc46170310b225c9190b63a046df8 and accepted by "
    "the owner on 2026-10-27. This current-state note supersedes the earlier pre-handoff note recorded before "
    "Stage 01 evidence and acceptance were available."
)


def load(rev: str | None) -> Any:
    if rev is None:
        return json.loads(Path(REGISTRY).read_text(encoding="utf-8"))
    out = subprocess.run(["git", "show", f"{rev}:{REGISTRY}"], check=True, capture_output=True)
    return json.loads(out.stdout.decode("utf-8"))


def diff(a: Any, b: Any, path: str, out: list[tuple[str, Any, Any]]) -> None:
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            diff(a.get(k, "<absent>"), b.get(k, "<absent>"), f"{path}.{k}", out)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b, strict=True)):
            label = x.get("id") if isinstance(x, dict) and "id" in x and path == "$.stages" else i
            diff(x, y, f"{path}[{label}]", out)
    elif a != b or type(a) is not type(b):
        out.append((path, a, b))


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else "cf2e411"
    target = sys.argv[2] if len(sys.argv) > 2 else None
    changes: list[tuple[str, Any, Any]] = []
    diff(load(base), load(target), "$", changes)
    for path, a, b in changes:
        print(f"CHANGED {path}\n  old: {a!r}\n  new: {b!r}")
    ok = changes == [("$.stages[01].notes", OLD, NEW)]
    print(f"paths changed: {len(changes)}; only Stage 01 notes with the D-045 values: {ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
