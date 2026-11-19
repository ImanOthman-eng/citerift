"""Stage 04 final closure audit, item 25: read-only secret scan of the Stage 04 evidence.

Uses the patterns and readings of the D-036 secret gate (``docs/verification/stage-03/evaluation/confirmation-d036/
scripts/secret_gate.py``: the accepted Stage 00 ``SECRET_PATTERNS`` plus the access-bearing URL and key shapes, on the
text and its once- and twice-percent-decoded readings), but changes nothing: it scans every file git tracks under the
given repository paths and every file under the given extra directories (such as an extracted run archive), and prints
and records only paths and match counts, never matched text.

Usage (from the repository root): python secret_scan.py --out RESULT.json [--extra DIR ...] PATH ...
Exit 0 when nothing matches, 1 otherwise.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
GATE = ROOT / "docs/verification/stage-03/evaluation/confirmation-d036/scripts/secret_gate.py"


def gate_module():  # type: ignore[no-untyped-def]
    spec = importlib.util.spec_from_file_location("d036_secret_gate", GATE)
    if spec is None or spec.loader is None:
        raise SystemExit(2)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def tracked(paths: list[str]) -> list[Path]:
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z", "--", *paths], capture_output=True, check=True)  # noqa: S603, S607
    return [ROOT / p.decode() for p in out.stdout.split(b"\0") if p and (ROOT / p.decode()).is_file()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="read-only secret scan (Stage 04 closure)")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--extra", type=Path, action="append", default=[])
    ap.add_argument("paths", nargs="+")
    a = ap.parse_args(argv)
    gate = gate_module()
    pats = gate.patterns()
    files = [(str(p.relative_to(ROOT)), p) for p in tracked(a.paths)]
    for d in a.extra:
        files += [(f"<extra:{d.name}>/{p.relative_to(d).as_posix()}", p) for p in sorted(d.rglob("*")) if p.is_file()]
    hits = []
    for name, path in files:
        data = path.read_bytes()
        n = sum(len(p.findall(text)) for text in gate.scanned(data) for p in pats)
        if n:
            hits.append({"path": name, "matches": n})
            print(f"match: {name} ({n})")
    result = {
        "format": "citerift-stage04-closure-secret-scan/1",
        "patterns": len(pats),
        "paths": a.paths,
        "extra_dirs": [d.name for d in a.extra],
        "files_scanned": len(files),
        "files_with_matches": hits,
    }
    a.out.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"scanned {len(files)} files, {len(hits)} with matches")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
