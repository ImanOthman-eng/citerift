"""Fail-first probes for the Step 7 corrective closure (D-047, D-048, D-049, D-051), run on the tree BEFORE the fix.

Run from the repository root at the Step 7 code (``ab0ce66``):

    uv run python docs/verification/stage-04/review/step7/closure/fail_first_before.py

Each probe prints what the unfixed code does. The output is retained as ``fail_first_before.log``. After the fix the
same situations are covered by regression tests (named in ``STEP7_CLOSURE.md``); this script uses the Step 7 fixture
signatures and is not expected to run on the fixed tree.
"""

from __future__ import annotations

import sys
import tempfile
import tracemalloc
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[6]
sys.path[:0] = [str(REPO / "tests" / "stage04"), str(REPO / "tests" / "stage02")]

from controller_support import (  # noqa: E402
    EXTRACTION,
    Plan,
    StepClock,
    create,
    digest,
    env_for,
    evidence,
    journal,
    ok_result,
    run_once,
)
from memory_support import h  # noqa: E402

from citerift.investigation import ids  # noqa: E402
from citerift.investigation.adapters import ContentRecord, StepRequest, StepResult, Succeeded  # noqa: E402
from citerift.investigation.controller import AdapterDefect  # noqa: E402


def failures(root: Path, key: str) -> list[tuple[str, str, Any]]:
    return [
        (r["step"], r["payload"]["code"], r["payload"]["reason"], (r["payload"]["detail"] or "")[:90])
        for r in journal(root, key)
        if r["kind"] == "step_failed"
    ]


def run(script: dict[tuple[str, int], Any]) -> tuple[Path, str, Any]:
    tmp = Path(tempfile.mkdtemp())
    clock = StepClock()
    root, key = create(tmp, clock=clock)
    try:
        st: Any = run_once(root, key, Plan(script), env_for(False), clock).lifecycle
    except AdapterDefect as exc:
        st = f"AdapterDefect({exc})"
    return root, key, st


def probe_d051() -> None:
    """IA-6: two evidence kinds at one pointer of one observation get one id; Memory refuses the second."""
    ext = digest(EXTRACTION)
    a = evidence("unit", ext, "/units/0", [], {"source_artifact": h("src"), "unit_span_sha256": h("span")})
    b = evidence("use_eligibility", ext, "/units/0", [], {"eligibility": "CITED", "reason": None})
    print("D-051 same id for kinds unit and use_eligibility:", a["evidence_id"] == b["evidence_id"])

    def normalize(req: StepRequest) -> StepResult:
        out = {"normalized": [a["evidence_id"]]}
        recs = (ContentRecord("evidence_recorded", a), ContentRecord("evidence_recorded", b))
        return Succeeded(records=recs, blobs=(out,), outputs=(digest(out),))

    root, key, st = run({("NORMALIZE", 1): normalize})
    print("D-051 run:", st, failures(root, key))


def probe_d047() -> None:
    """RB-1: a claim with many evidence ids, and a report with many projections, exceed the 1 MiB record."""
    for n in (16_000, 50_000):

        def detect(req: StepRequest, n: int = n) -> StepResult:
            base = ok_result(req, (("RETRACTED_WORK_CITED", "cand"),))
            recs = list(base.records)  # type: ignore[union-attr]
            claim = dict(recs[-1].payload)
            claim["supporting"] = sorted(h(f"ev{i}") for i in range(n))
            recs[-1] = ContentRecord("claim_recorded", claim)
            return Succeeded(records=tuple(recs), blobs=base.blobs, outputs=base.outputs)  # type: ignore[union-attr]

        root, key, st = run({("DETECT", 1): detect})
        print(f"D-047 claim with {n} supporting ids:", st, failures(root, key))

    def assemble(req: StepRequest) -> StepResult:
        report = {"report": "SYNTHETIC"}
        projections = sorted(h(f"p{i}") for i in range(50_000))
        rec = ContentRecord("report_recorded", {"report": digest(report), "projections": projections})
        return Succeeded(records=(rec,), blobs=(report,), outputs=(digest(report),))

    root, key, st = run({("ASSEMBLE", 1): assemble})
    print("D-047 report with 50000 projections:", st, failures(root, key))


def probe_d049() -> None:
    """IA-11: in VALIDATE, EXTRACT and LOOKUP an adapter defect leaves the attempt open; W-6 and the retry budget end
    it as RETRY_BUDGET_EXHAUSTED / STEP_INTERRUPTED instead of a terminal defect."""
    for step in ("VALIDATE", "EXTRACT", "LOOKUP"):
        tmp = Path(tempfile.mkdtemp())
        clock = StepClock()
        root, key = create(tmp, clock=clock)
        outcomes = []
        for _ in range(3):
            try:
                outcomes.append(run_once(root, key, Plan({(step, a): "raise" for a in (1, 2, 3)}), env_for(False), clock).lifecycle)
            except AdapterDefect as exc:
                last = journal(root, key)[-1]
                outcomes.append(f"AdapterDefect; last record {last['kind']} {last['step']} {last['attempt']}")
        outcomes.append(run_once(root, key, Plan(), env_for(False), clock).lifecycle)
        print(f"D-049 {step} raising three times:", outcomes, failures(root, key))


def probe_d048() -> None:
    """RB-2: Index.gather materializes every event of a key; a cap applied to its result comes after that."""
    import rde_support as S

    from citerift.retraction import export, query

    for k in (200, 2000):
        tmp = Path(tempfile.mkdtemp())
        rows = [
            S.row(**{"Record ID": str(i + 1), "RetractionNature": "Correction", "OriginalPaperDOI": "10.5555/many",
                     "RetractionDOI": f"10.5555/n{i}"})
            for i in range(k)
        ]
        idx = S.build_rows(tmp, rows)
        made = 0
        original = query.event_from_row

        def counting(row: Any) -> Any:
            nonlocal made
            made += 1
            return original(row)

        query.event_from_row = counting
        try:
            with query.Index(idx) as ix:
                tracemalloc.start()
                ev = ix.gather("10.5555/many")
                capped = ev.events[:100]  # a post-materialization cap
                peak = tracemalloc.get_traced_memory()[1]
                tracemalloc.stop()
        finally:
            query.event_from_row = original
        assert export.EVENT_COLUMNS
        print(f"D-048 key with {k} events: rows materialized {made}, events returned {len(ev.events)}, "
              f"kept after a cap of 100 {len(capped)}, traced peak {peak} bytes")


if __name__ == "__main__":
    probe_d051()
    probe_d047()
    probe_d049()
    probe_d048()
