"""Owner decision D-055: performance and journal size of per-candidate content before (``0097a93``, journal format 3:
one record per lookup observation, claim, decision and question) and after (format 4: LOOKUP and DETECT batches).

One investigation runs end to end with the SYNTHETIC fake adapters of the tree being run, except LOOKUP, which
commits ``N`` lookup observations (``N`` distinct lookup blobs), and DETECT, which commits ``N`` candidate results
over them (one in eight an identity conflict with its question, the others not found in checked sources). At
``N = 70,000`` this is the Stage 03 cap (``max_candidates + max_refs`` candidates). Measured on one machine, in one
process:

- the journal record count and bytes, the per-candidate records, and the blob bytes;
- the wall time of LOOKUP's and DETECT's commit (from the adapter's return to the terminal record);
- the wall time of a read-only open (every record and every blob it names read and checked) and its Python heap peak
  (``tracemalloc``, in a second open so that the timing is not slowed by it).

Usage (one tree at a time; its ``src`` and ``tests/stage04`` are imported first)::

    uv run python docs/verification/stage-04/review/step7/d055/perf.py --tree <checkout> --n 1000 10000 70000 \\
        --out <file.json>
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

PER_CANDIDATE = ("claim_recorded", "decision_recorded", "question_opened")


def measure(n: int) -> dict[str, Any]:
    from controller_support import (  # noqa: PLC0415
        LOOKUP,
        Env,
        Plan,
        StepClock,
        claim_and_set,
        create,
        digest,
        lookup_evidence,
        run_once,
    )

    from citerift.investigation import faults  # noqa: PLC0415
    from citerift.investigation.adapters import ContentRecord, Succeeded  # noqa: PLC0415
    from citerift.investigation.memory import InvestigationMemory  # noqa: PLC0415

    values = [LOOKUP, *({"lookup": "SYNTHETIC", "candidate": i} for i in range(1, n))]
    refs = [
        {
            "obs_kind": "lookup",
            "blob": digest(v),
            "source_ref": {"engine": "citerift.retraction", "operation": "gather", "locator": f"doi:10.1000/{i}"},
        }
        for i, v in enumerate(values)
    ]
    evs = lookup_evidence()
    ev_ids = [e["evidence_id"] for e in evs]
    pairs = [
        claim_and_set("IDENTITY_CONFLICT" if i % 8 == 0 else "NOT_FOUND_IN_CHECKED_SOURCES", ev_ids, f"cand-{i}")
        for i in range(n)
    ]
    sets_ = {digest(v): v for _, v in pairs}
    out = {"claims": len(pairs)}

    def lookup(req: Any) -> Any:
        recs = tuple(ContentRecord("observation_recorded", r) for r in refs)
        return Succeeded(records=recs, blobs=tuple(values), outputs=(digest(LOOKUP),))

    def detect(req: Any) -> Any:
        recs = (*(ContentRecord("evidence", e) for e in evs), *(ContentRecord("claim_recorded", c) for c, _ in pairs))
        return Succeeded(records=recs, blobs=(*sets_.values(), out), outputs=(digest(out),))

    marks: dict[tuple[str, str], float] = {}

    def handler(name: str, ctx: dict[str, Any]) -> None:
        if ctx.get("step") in ("LOOKUP", "DETECT") and name in (
            "controller.after_adapter",
            "controller.after_terminal",
        ):
            marks[(ctx["step"], name)] = time.perf_counter()

    with tempfile.TemporaryDirectory(dir=os.environ.get("PERF_TMP")) as d:
        clock = StepClock()
        root, key = create(Path(d), clock=clock)
        faults.install(handler)
        t0 = time.perf_counter()
        try:
            st = run_once(root, key, Plan({("LOOKUP", 1): lookup, ("DETECT", 1): detect}), Env(), clock)
        finally:
            faults.install(None)
        run_s = time.perf_counter() - t0
        if st.lifecycle != "NEEDS_RESOLUTION":
            raise SystemExit(str(st.lifecycle))
        journal = root / key / "journal.jsonl"
        size = journal.stat().st_size
        blob_bytes = sum(p.stat().st_size for p in (root / key / "blobs").iterdir())
        t0 = time.perf_counter()
        with InvestigationMemory.open(root, key, writable=False) as m:
            records = m.view.records
            n_records = len(records)
            by_step = {s: sum(1 for r in records if r["step"] == s) for s in ("LOOKUP", "DETECT")}
            per_candidate = sum(
                1
                for r in records
                if r["kind"] in PER_CANDIDATE
                or (r["kind"] == "observation_recorded" and r["payload"]["obs_kind"] == "lookup")
            )
            logical = sum(
                1
                for r in m.view.committed_content()
                if r["kind"] in PER_CANDIDATE
                or (r["kind"] == "observation_recorded" and r["payload"]["obs_kind"] == "lookup")
            )
        open_s = time.perf_counter() - t0
        tracemalloc.start()
        with InvestigationMemory.open(root, key, writable=False) as m:
            peak = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()

    def commit(step: str) -> float:
        return marks[(step, "controller.after_terminal")] - marks[(step, "controller.after_adapter")]

    return {
        "candidates": n,
        "run_s": round(run_s, 3),
        "lookup_commit_s": round(commit("LOOKUP"), 3),
        "detect_commit_s": round(commit("DETECT"), 3),
        "detect_commit_ms_per_candidate": round(1000 * commit("DETECT") / n, 4),
        "journal_records": n_records,
        "journal_records_lookup_detect": by_step,
        "per_candidate_journal_records": per_candidate,
        "per_candidate_logical_records": logical,
        "journal_bytes": size,
        "blob_bytes": blob_bytes,
        "open_s": round(open_s, 3),
        "open_ms_per_candidate": round(1000 * open_s / n, 4),
        "open_peak_bytes": peak,
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

    if not Path(citerift.__file__).resolve().is_relative_to(tree):
        raise SystemExit(citerift.__file__)
    from citerift.investigation.journal import JOURNAL_FORMAT  # noqa: PLC0415

    head = subprocess.run(["git", "-C", str(tree), "rev-parse", "HEAD"], capture_output=True, text=True, check=True)  # noqa: S603, S607
    status = ["git", "-C", str(tree), "status", "--porcelain"]
    dirty = subprocess.run(status, capture_output=True, text=True, check=True)  # noqa: S603
    rows = []
    for n in args.n:
        rows.append(measure(n))
        print(json.dumps(rows[-1]), flush=True)
    result = {
        "tree_head": head.stdout.strip(),
        "tree_dirty": bool(dirty.stdout.strip()),
        "journal_format": JOURNAL_FORMAT,
        "machine": {"python": platform.python_version(), "platform": platform.platform(), "cpus": os.cpu_count()},
        "rows": rows,
    }
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
