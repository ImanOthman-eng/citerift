"""Step 7: process death at every controller boundary, then resume (owner Step 7 item 10; SPEC 10.1, 10.2).

For every boundary in ``citerift.investigation.controller.POINTS``, every time an uninterrupted run reaches it, and
inside every step's adapter, a forked child runs the controller and dies there with ``os._exit`` (real process
death: no ``finally``, no flush, the kernel releases the lock). The parent then resumes in a new controller and
checks:

* the journal reopens (no CORRUPT) and the workflow check passes;
* an attempt left open is closed first, by ``step_interrupted`` of that attempt (W-6), so its step's retry count
  ``phi`` went up by one;
* no step that had succeeded is run again (its adapter is not called) and every step has exactly one success;
* content of the interrupted attempt is not authoritative: the committed content equals the uninterrupted run's;
* a terminal investigation stays terminal (nothing appended).

Then crash and failure are mixed until the retry budget ends the step. SYNTHETIC fake adapters. Limitation, as in
Step 6: process death keeps the page cache; power loss is argued from the fsync order, not tested.
"""

from __future__ import annotations

import os
from collections import Counter
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from controller_support import DIE, T0, Env, Plan, StepClock, create, journal, run_once

from citerift.investigation import faults, workflow
from citerift.investigation.adapters import Failed
from citerift.investigation.controller import POINTS
from citerift.investigation.fold import STEPS, Folder

pytestmark = pytest.mark.simulation

CRASH = 77
CLASSES = (("IDENTITY_CONFLICT", "c1"), ("NOT_FOUND_IN_CHECKED_SOURCES", "c2"))


def _committed(records: list[dict[str, Any]]) -> list[Any]:
    f = Folder(None)
    for r in records:
        f.apply(r)
    return [[r["kind"], r["step"], r["payload"]] for r in f.committed_content()]


def _fold(records: list[dict[str, Any]]) -> Folder:
    f = Folder(None)
    for r in records:
        f.apply(r)
    return f


class Reference:
    def __init__(self, base: Path) -> None:
        clock = StepClock()
        root, key = create(base, clock=clock)
        seen: Counter[str] = Counter()
        faults.install(lambda name, ctx: seen.update([name]))
        try:
            st = run_once(root, key, Plan(classes=CLASSES), Env(), clock)
        finally:
            faults.install(None)
        assert st.lifecycle == "NEEDS_RESOLUTION"
        self.records = journal(root, key)
        self.content = _committed(self.records)
        self.seen = seen


@pytest.fixture(scope="module")
def reference(tmp_path_factory: pytest.TempPathFactory) -> Reference:
    return Reference(tmp_path_factory.mktemp("ctl-ref"))


def _child(root: Path, key: str, plan: Plan, point: str | None, occurrence: int, clock: StepClock) -> int:
    pid = os.fork()
    if pid == 0:  # child: dies at the boundary, never returns
        code = 1
        try:
            seen: Counter[str] = Counter()

            def handler(name: str, ctx: dict[str, Any]) -> None:
                seen.update([name])
                if name == point and seen[name] == occurrence:
                    os._exit(CRASH)

            faults.install(handler)
            run_once(root, key, plan, Env(), clock)
            code = 0
        except BaseException:
            code = 2
        finally:
            os._exit(code)
    _, status = os.waitpid(pid, 0)
    return os.waitstatus_to_exitcode(status)


def _resume_and_check(ref: Reference, root: Path, key: str, label: str) -> dict[str, Any]:
    before = journal(root, key)  # reopens: a CORRUPT journal would raise here
    f = _fold(before)
    workflow.check_journal(f)
    open_attempt = (f.open.step, f.open.number) if f.open is not None else None
    phi_before = {s: workflow.step_view(f, s).phi for s in STEPS}
    succeeded_before = {s for s in STEPS if f.step_state(s) == "succeeded"}
    terminal_before = f.lifecycle() in workflow.LIFECYCLE_TERMINAL
    plan = Plan(classes=CLASSES)
    st = run_once(root, key, plan, Env(), StepClock(T0 + timedelta(days=1)))
    after = journal(root, key)
    assert after[: len(before)] == before, label  # history is never rewritten
    assert st.lifecycle == "NEEDS_RESOLUTION", label
    if terminal_before:
        assert after == before and plan.calls == [], label
    if open_attempt is not None:
        first = after[len(before)]
        assert (first["kind"], first["step"], first["attempt"]) == ("step_interrupted", *open_attempt), label
        g = _fold(after)
        assert workflow.step_view(g, open_attempt[0]).phi == phi_before[open_attempt[0]] + 1, label
        # The interrupted attempt's content records are not in the committed view.
        interrupted = next(a for a in g.attempts[open_attempt[0]] if a.number == open_attempt[1])
        assert not set(interrupted.content) & set(g.committed_seqs), label
    assert not {s for s, _ in plan.calls} & succeeded_before, label  # no succeeded step repeats
    assert Counter(r["step"] for r in after if r["kind"] == "step_succeeded") == dict.fromkeys(STEPS, 1), label
    assert _committed(after) == ref.content, label  # same committed content as the uninterrupted run
    return {"label": label, "open": open_attempt, "appended": len(after) - len(before)}


def _fresh(base: Path, name: str) -> tuple[Path, str, StepClock]:
    d = base / name
    d.mkdir()
    clock = StepClock()
    root, key = create(d, clock=clock)
    return root, key, clock


def test_crash_at_every_occurrence_of_every_controller_boundary(reference: Reference, tmp_path: Path) -> None:
    rows = []
    for point in POINTS:
        assert reference.seen[point] > 0, point
        for k in range(1, reference.seen[point] + 1):
            root, key, clock = _fresh(tmp_path, f"{point}-{k}")
            code = _child(root, key, Plan(classes=CLASSES), point, k, clock)
            assert code == CRASH, f"{point}#{k}: child ended with {code}"
            rows.append(_resume_and_check(reference, root, key, f"{point}#{k}"))
    total = sum(reference.seen[p] for p in POINTS)
    assert len(rows) == total
    # Every kind of boundary left an open attempt at least once, except the ones between attempts.
    with_open = {r["label"].split("#")[0] for r in rows if r["open"]}
    assert with_open == {
        "controller.after_start",
        "controller.after_adapter",
        "controller.after_blobs",
        "controller.after_batch",
        "controller.after_content",
    }


@pytest.mark.parametrize("step", STEPS)
def test_process_death_inside_the_adapter(reference: Reference, tmp_path: Path, step: str) -> None:
    root, key, clock = _fresh(tmp_path, step)
    code = _child(root, key, Plan({(step, 1): "die"}, classes=CLASSES), None, 0, clock)
    assert code == DIE
    row = _resume_and_check(reference, root, key, f"adapter:{step}")
    assert row["open"] == (step, 1)


def test_terminal_investigation_stays_terminal_after_death(reference: Reference, tmp_path: Path) -> None:
    root, key, clock = _fresh(tmp_path, "terminal")
    n = reference.seen["controller.after_terminal"]
    assert _child(root, key, Plan(classes=CLASSES), "controller.after_terminal", n, clock) == CRASH
    assert _resume_and_check(reference, root, key, "after VERIFY")["appended"] == 0


def test_crash_mixed_with_failure_exhausts_the_retry_budget(tmp_path: Path) -> None:
    """EXTRACT: process death (attempt 1), a retryable failure (attempt 2), death again (attempt 3): the resume ends
    the step with RETRY_BUDGET_EXHAUSTED, and later processes change nothing."""
    root, key, clock = _fresh(tmp_path, "mixed")
    script = {("EXTRACT", 1): "die", ("EXTRACT", 2): Failed("EXTRACTION_WORKER_FAILED"), ("EXTRACT", 3): "die"}
    assert _child(root, key, Plan(script), None, 0, clock) == DIE
    assert _child(root, key, Plan(script), None, 0, StepClock(T0 + timedelta(hours=1))) == DIE
    st = run_once(root, key, Plan(), Env(), StepClock(T0 + timedelta(hours=2)))
    assert st.lifecycle == "FAILED"
    ext = [(r["kind"], r["attempt"], r["payload"].get("code")) for r in journal(root, key) if r["step"] == "EXTRACT"]
    assert ext == [
        ("step_started", 1, None),
        ("step_interrupted", 1, None),
        ("step_started", 2, None),
        ("step_failed", 2, "EXTRACTION_WORKER_FAILED"),
        ("step_started", 3, None),
        ("step_failed", 3, "RETRY_BUDGET_EXHAUSTED"),
    ]
    before = journal(root, key)
    plan = Plan()
    run_once(root, key, plan, Env(), StepClock(T0 + timedelta(hours=3)))
    assert journal(root, key) == before and plan.calls == []


def test_repeated_death_of_a_step_without_retryable_codes_ends_it(tmp_path: Path) -> None:
    """SPEC 9.2: a step that keeps killing the process ends (W-6 with phi + 1 = A_max)."""
    root, key, _clock = _fresh(tmp_path, "killer")
    script = {("DETECT", a): "die" for a in (1, 2, 3)}
    for hours in (0, 1, 2):
        assert _child(root, key, Plan(script), None, 0, StepClock(T0 + timedelta(hours=hours))) == DIE
    st = run_once(root, key, Plan(), Env(), StepClock(T0 + timedelta(hours=3)))
    last = journal(root, key)[-1]
    assert st.lifecycle == "FAILED"
    assert (last["kind"], last["step"], last["attempt"]) == ("step_failed", "DETECT", 3)
    assert (last["payload"]["code"], last["payload"]["reason"]) == ("RETRY_BUDGET_EXHAUSTED", "STEP_INTERRUPTED")
