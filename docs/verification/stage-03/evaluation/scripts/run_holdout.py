"""Run the extractor on the locked holdout and challenge bundles, verify and replay each, and write the scoring spec.

Usage: python run_holdout.py CAPTURE_DIR ANNOTATION_DIR OUT_DIR

Refuses to run unless ANNOTATION_DIR holds ANNOTATION_LOCK.json, every annotation file matches its locked SHA-256,
and the lock and the annotations are committed in the repository (FROZEN_PROTOCOL.md section 4.3: no holdout or
challenge extraction before that commit). For each article whose final capture produced a bundle it runs, through
the installed CLI, ``citerift-wiki extract``, ``verify --extraction`` and ``replay --extraction``, recording exit
codes, wall time and stdout. It then writes OUT_DIR/score_spec.json for ``evaluate.py score``.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[5]


def _locked(ann_dir: Path) -> dict[str, str]:
    lock = json.loads((ann_dir / "ANNOTATION_LOCK.json").read_text(encoding="utf-8"))
    for name, sha in lock.items():
        if hashlib.sha256((ann_dir / name).read_bytes()).hexdigest() != sha:
            raise SystemExit(f"{name} does not match its locked hash")
    rel = ann_dir.resolve().relative_to(REPO)
    tracked = subprocess.run(  # noqa: S603 - fixed argv
        ["git", "-C", str(REPO), "ls-files", "--error-unmatch", str(rel / "ANNOTATION_LOCK.json")],  # noqa: S607
        capture_output=True,
        check=False,
    )
    dirty = subprocess.run(  # noqa: S603 - fixed argv
        ["git", "-C", str(REPO), "status", "--porcelain", "--", str(rel)],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    if tracked.returncode != 0 or dirty.stdout.strip():
        raise SystemExit("the annotations and the lock must be committed, unchanged, before any extraction")
    return lock


def _run(argv: list[str]) -> dict[str, Any]:
    start = time.monotonic()
    proc = subprocess.run(argv, capture_output=True, text=True, check=False)  # noqa: S603 - fixed argv
    try:
        out = json.loads(proc.stdout) if proc.stdout.strip() else None
    except json.JSONDecodeError:
        out = None
    return {
        "argv": argv,
        "exit": proc.returncode,
        "seconds": round(time.monotonic() - start, 3),
        "stdout": out,
        "stderr": proc.stderr[-2000:],
    }


def main() -> int:
    capture_dir, ann_dir, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    lock = _locked(ann_dir)
    states = json.loads((capture_dir / "capture_states.json").read_text(encoding="utf-8"))
    out.mkdir(parents=True, exist_ok=False)
    runs: list[dict[str, Any]] = []
    spec: dict[str, Any] = {"splits": {}}
    for key, st in sorted(states["articles"].items()):
        split = st["split"]
        bundle = st["final"]["bundle"]
        row: dict[str, Any] = {"article": key, "split": split, "capture": st["final"]}
        if bundle is None:
            runs.append(row)
            continue
        cap = json.loads((Path(bundle) / "capture.json").read_text(encoding="utf-8"))
        name = f"{cap['page']['wiki']}-{cap['page']['revision_id']}"
        ext = out / "extractions" / f"{name}.json"
        ext.parent.mkdir(exist_ok=True)
        row["extract"] = _run(["citerift-wiki", "extract", "--bundle", bundle, "--out", str(ext)])
        row["verify"] = _run(["citerift-wiki", "verify", "--bundle", bundle, "--extraction", str(ext)])
        row["replay"] = _run(["citerift-wiki", "replay", "--bundle", bundle, "--extraction", str(ext)])
        runs.append(row)
        if f"{name}.json" not in lock:
            row["annotation"] = None
            continue
        row["annotation"] = f"{name}.json"
        entry = {
            "bundle": str(Path(bundle).resolve()),
            "extraction": str(ext.resolve()),
            "locked": str((ann_dir / f"{name}.json").resolve()),
        }
        adjudicated = ann_dir.parent / "adjudicated" / f"{name}.json"
        if adjudicated.exists():
            entry["adjudicated"] = str(adjudicated.resolve())
        spec["splits"].setdefault(split, []).append(entry)
    (out / "runs.json").write_text(json.dumps(runs, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (out / "score_spec.json").write_text(json.dumps(spec, indent=1) + "\n", encoding="utf-8")
    bad = [r["article"] for r in runs if "extract" in r and (r["verify"]["exit"] != 0 or r["replay"]["exit"] != 0)]
    print(
        json.dumps(
            {"articles": len(runs), "extracted": sum("extract" in r for r in runs), "verify_or_replay_failed": bad}
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
