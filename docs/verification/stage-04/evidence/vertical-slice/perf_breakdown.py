"""Where the time of one production investigation goes (Step 11, owner item 22: diagnose a case above the plan's
"warm investigation of a retained bundle <= 5 s p95" before claiming the gate).

Each sample is a fresh process in a network namespace with no interface (``unshare -rn``) that runs
``citerift-investigate run`` in process (``cli.main``) on a new memory root, with timers wrapped around:

- ``file_sha256``: SHA-256 of the whole Stage 02 index file (LOOKUP's identity and its unchanged-file check, and the
  Stage 02 component of every step's identity check, S-10.1);
- ``schema``: JSON Schema validation (``schemas._validator`` / ``_ref_validator`` and the v1 contract validation);
- ``memory_open``: ``InvestigationMemory.open`` (the journal is re-read and re-proved: M-1..M-14, D-054);
- ``show``: the read-only ``show`` the command prints after the run;
- ``index_verify`` (Step 12, D-062): the verification of the index's canonical Stage 02 identity
  (``lookup.verify_index_identity``, called once per process by the process-local reuse), and ``stage02_digests``
  within it (``export.compute_digests``).

Nothing is changed in what runs; the timers only add a clock read around the wrapped calls. A sample's
``unaccounted`` is ``run`` minus ``file_sha256``, ``index_verify`` and ``schema`` (``memory_open`` and ``show``
overlap them): the rest (the Stage 03 worker, Stage 02 queries, dt-1, canonical encoding, writes and fsyncs).

Run: ``uv run python docs/verification/stage-04/evidence/vertical-slice/perf_breakdown.py --index INDEX --work DIR
[--bundle DIR] [--samples 5] [--out FILE]``; writes ``results/perf_breakdown.json`` unless ``--out`` names another file.
"""

# ruff: noqa: PLC0415  (the child imports citerift late so that the import time is measured on its own)

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
TOTALS: dict[str, float] = defaultdict(float)
COUNTS: dict[str, int] = defaultdict(int)


def timed(name: str, fn: Callable[..., Any]) -> Callable[..., Any]:
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        t0 = time.perf_counter()
        try:
            return fn(*args, **kwargs)
        finally:
            TOTALS[name] += time.perf_counter() - t0
            COUNTS[name] += 1

    return wrapper


class _TimedValidator:
    def __init__(self, inner: Any) -> None:
        self.inner = inner

    def iter_errors(self, instance: Any) -> Any:
        t0 = time.perf_counter()
        try:
            return list(self.inner.iter_errors(instance))
        finally:
            TOTALS["schema"] += time.perf_counter() - t0
            COUNTS["schema"] += 1


def child(argv: list[str]) -> int:
    t_start = time.perf_counter()
    from citerift.investigation import cli, memory, operations, schemas
    from citerift.investigation.adapters import lookup

    t_import = time.perf_counter() - t_start
    from citerift.retraction import export

    lookup.file_sha256 = timed("file_sha256", lookup.file_sha256)
    lookup.verify_index_identity = timed("index_verify", lookup.verify_index_identity)
    export.compute_digests = timed("stage02_digests", export.compute_digests)
    v, rv = schemas._validator, schemas._ref_validator
    schemas._validator = lambda sid: _TimedValidator(v(sid))  # type: ignore[assignment]
    schemas._ref_validator = lambda ref: _TimedValidator(rv(ref))  # type: ignore[assignment]
    cs = schemas.contracts()
    cs.validate = timed("schema", cs.validate)  # type: ignore[method-assign]
    memory.InvestigationMemory.open = timed("memory_open", memory.InvestigationMemory.open)  # type: ignore[method-assign]
    operations.show = timed("show", operations.show)
    t0 = time.perf_counter()
    code = cli.main(argv)
    total = time.perf_counter() - t0
    out = {"exit_code": code, "import_s": round(t_import, 3), "run_s": round(total, 3)}
    out.update({f"{k}_s": round(v, 3) for k, v in TOTALS.items()})
    out.update({f"{k}_calls": n for k, n in COUNTS.items()})
    sys.stderr.write("BREAKDOWN " + json.dumps(out) + "\n")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", type=Path, required=True)
    ap.add_argument("--work", type=Path, required=True)
    vs1 = REPO / "docs/verification/stage-03/demonstrations/bundles/en-1381772671"
    ap.add_argument("--bundle", type=Path, default=vs1)
    ap.add_argument("--samples", type=int, default=5)
    ap.add_argument("--out", type=Path, default=HERE / "results" / "perf_breakdown.json")
    args = ap.parse_args(argv)
    samples = []
    for i in range(args.samples):
        root = args.work / f"perf-{i}"
        root.mkdir(parents=True, mode=0o700)
        cmd = ["unshare", "-rn", sys.executable, __file__, "--child", "run", "--bundle", str(args.bundle),
               "--index", str(args.index), "--memory-root", str(root), "--format", "json"]  # fmt: skip
        t0 = time.perf_counter()
        p = subprocess.run(cmd, capture_output=True, check=False, cwd=REPO)  # noqa: S603
        wall = time.perf_counter() - t0
        line = next(x for x in p.stderr.decode().splitlines() if x.startswith("BREAKDOWN "))
        s = json.loads(line.split(" ", 1)[1])
        s["process_wall_s"] = round(wall, 3)
        accounted = s.get("file_sha256_s", 0) + s.get("index_verify_s", 0) + s.get("schema_s", 0)
        s["unaccounted_s"] = round(s["run_s"] - accounted, 3)
        samples.append(s)
    keys = sorted({k for s in samples for k in s if k.endswith("_s")})
    summary = {k: round(statistics.median(s.get(k, 0) for s in samples), 3) for k in keys}
    out = {
        "bundle": str(args.bundle.relative_to(REPO)) if args.bundle.is_relative_to(REPO) else str(args.bundle),
        "index_bytes": args.index.stat().st_size,
        "samples": samples,
        "median": summary,
        "note": "file_sha256_s, index_verify_s and schema_s are disjoint; stage02_digests_s is within index_verify_s; "
        "memory_open_s and show_s include schema validation and overlap schema_s; unaccounted_s = run_s - "
        "file_sha256_s - index_verify_s - schema_s",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps(out["median"], indent=1))
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--child":
        sys.exit(child(sys.argv[2:]))
    sys.exit(main(sys.argv[1:]))
