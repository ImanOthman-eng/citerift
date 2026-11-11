"""Owner decision D-053: performance of evidence commits before (``64e7aca``, one record per item) and after (batches).

One investigation runs end to end with the SYNTHETIC fake adapters of the tree being run, except DETECT, which
commits ``N`` lookup-result evidence items and one claim whose evidence set names all of them (the shape of the Step 7
closure measurement, ``closure/storage_bounds.py`` ``reader_memory``). Measured, on one machine, in one process:

- the wall time of the whole run and of DETECT's commit (append time per record and per evidence item);
- the journal size and record count, and the blob bytes;
- the wall time and Python heap peak (``tracemalloc``, measured in a second open so the timing is not slowed by it) of
  a read-only open, which reads every record and every blob it names and checks them.

Usage (one tree at a time; its ``src`` and ``tests/stage04`` are imported first)::

    uv run python docs/verification/stage-04/review/step7/d053/perf.py --tree <checkout> --n 20000 --out <file.json>
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path
from typing import Any


def measure(n: int) -> dict[str, Any]:
    from controller_support import LOOKUP, Env, Plan, StepClock, claim_and_set, create, digest, evidence, run_once  # noqa: PLC0415

    from citerift.investigation import faults, ids, sets, workflow  # noqa: PLC0415
    from citerift.investigation.adapters import ContentRecord, Succeeded  # noqa: PLC0415
    from citerift.investigation.memory import InvestigationMemory  # noqa: PLC0415

    kind = next(iter(workflow.ADAPTER_CONTENT_KINDS["DETECT"] - {"claim_recorded"}))  # evidence_recorded / evidence
    obs = digest(LOOKUP)
    evs = [evidence("lookup_result", obs, f"/results/{i}", [], None) for i in range(n)]
    value = sets.evidence_set([e["evidence_id"] for e in evs])
    claim, _ = claim_and_set("RETRACTED_WORK_CITED", [evs[0]["evidence_id"]] * 4)
    claim["evidence_set"], claim["supporting_count"] = digest(value), n
    claim["claim_id"] = ids.claim_id(claim["cand_ref"], claim["class"], claim["rule"], "dt-1", claim["evidence_set"])
    out = {"claims": [claim["claim_id"]]}
    recs = (*(ContentRecord(kind, e) for e in evs), ContentRecord("claim_recorded", claim))

    def detect(req: Any) -> Any:
        return Succeeded(records=recs, blobs=(value, out), outputs=(digest(out),))

    marks: dict[str, float] = {}

    def handler(name: str, ctx: dict[str, Any]) -> None:
        if ctx.get("step") == "DETECT" and name in ("controller.after_adapter", "controller.after_terminal"):
            marks[name] = time.perf_counter()

    with tempfile.TemporaryDirectory(dir=os.environ.get("PERF_TMP")) as d:
        clock = StepClock()
        root, key = create(Path(d), clock=clock)
        faults.install(handler)
        t0 = time.perf_counter()
        try:
            st = run_once(root, key, Plan({("DETECT", 1): detect}), Env(), clock)
        finally:
            faults.install(None)
        run_s = time.perf_counter() - t0
        if not (st.lifecycle == "COMPLETED"):
            raise SystemExit(str(st.lifecycle))
        journal = root / key / "journal.jsonl"
        size = journal.stat().st_size
        blob_bytes = sum(p.stat().st_size for p in (root / key / "blobs").iterdir())
        t0 = time.perf_counter()
        with InvestigationMemory.open(root, key, writable=False) as m:
            records = len(m.view.records)
            detect_records = sum(1 for r in m.view.records if r["step"] == "DETECT")
        open_s = time.perf_counter() - t0
        tracemalloc.start()
        with InvestigationMemory.open(root, key, writable=False) as m:
            peak = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
    commit_s = marks["controller.after_terminal"] - marks["controller.after_adapter"]
    return {
        "evidence_items": n,
        "adapter_kind": kind,
        "run_s": round(run_s, 3),
        "detect_commit_s": round(commit_s, 3),
        "detect_commit_ms_per_item": round(1000 * commit_s / n, 4),
        "detect_records": detect_records,
        "detect_commit_ms_per_record": round(1000 * commit_s / detect_records, 4),
        "journal_records": records,
        "journal_bytes": size,
        "blob_bytes": blob_bytes,
        "open_s": round(open_s, 3),
        "open_ms_per_item": round(1000 * open_s / n, 4),
        "open_peak_bytes": peak,
        "open_peak_per_journal_byte": round(peak / size, 3),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", type=Path, required=True)
    ap.add_argument("--n", type=int, nargs="+", required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    tree = args.tree.resolve()
    sys.path[:0] = [str(tree / "src"), str(tree / "tests" / "stage04")]
    import citerift  # noqa: PLC0415

    if not (Path(citerift.__file__).resolve().is_relative_to(tree)):
        raise SystemExit(citerift.__file__)
    from citerift.investigation.journal import JOURNAL_FORMAT  # noqa: PLC0415

    head = subprocess.run(["git", "-C", str(tree), "rev-parse", "HEAD"], capture_output=True, text=True, check=True)  # noqa: S603, S607
    rows = []
    for n in args.n:
        rows.append(measure(n))
        print(json.dumps(rows[-1]), flush=True)
    result = {
        "tree_head": head.stdout.strip(),
        "journal_format": JOURNAL_FORMAT,
        "machine": {"python": platform.python_version(), "platform": platform.platform(), "cpus": os.cpu_count()},
        "rows": rows,
    }
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
