"""Fail-first probe of the bib-1 corpus against any engine revision (reviewer findings F-01 to F-05, C-01, C-10).

Usage::

    uv run python corpus_probe.py <src directory of an engine checkout> [case id ...]

Loads ``citerift.investigation.bibliographic`` from the given ``src`` directory (for example the ``src`` of a
``git worktree`` at an older commit), decides every named case of ``../corpus/BIB_CORPUS.json`` (all cases when none
is named) and prints, per case, the verdict fields the corpus expects, the engine's values and MATCH or MISMATCH. The
exit status is 0 when every case matches. The committed fail-first logs (``review_f_fail_first.log``,
``review_c_fail_first.log``) are this tool's output before and after a fix, so they can be reproduced from the
repository. Synthetic and design-exposed inputs only; no label is read.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

CORPUS = Path(__file__).resolve().parents[1] / "corpus" / "BIB_CORPUS.json"


def _git(where: Path, *args: str) -> str:
    argv = ["git", "-C", str(where), *args]
    return subprocess.run(argv, capture_output=True, text=True, check=False).stdout.strip()  # noqa: S603


def main() -> int:
    src = Path(sys.argv[1]).resolve()
    sys.path.insert(0, str(src))
    from citerift.investigation import bibliographic as B  # noqa: PLC0415 - loaded from the named checkout

    if Path(B.__file__).resolve().parents[2] != src:
        raise SystemExit(f"loaded {B.__file__}, not the engine of {src}")
    head = _git(src, "rev-parse", "--short", "HEAD")
    dirty = _git(src, "status", "--porcelain", "--", ".")
    print(f"# engine: {src} at {head or '?'}{' (uncommitted changes in src)' if dirty else ''}")
    cases = json.loads(CORPUS.read_text(encoding="utf-8"))["cases"]
    wanted = set(sys.argv[2:])
    bad = 0
    for case in cases:
        if wanted and case["id"] not in wanted:
            continue
        cited = B.cited_object(case["source"], case["wiki"])
        record = B.RecordObject.from_json(case["record"]) if case["record"] is not None else None
        got = B.compare(cited, record).to_json()
        exp = case["expect"]
        seen = {k: (cited is None if k == "cited_none" else got.get(k)) for k in exp}
        ok = seen == exp
        bad += not ok
        print(case["id"], "MATCH" if ok else "MISMATCH", json.dumps(seen, ensure_ascii=False))
        if not ok:
            print("   expected", json.dumps(exp, ensure_ascii=False))
    print(f"# {bad} mismatched")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
