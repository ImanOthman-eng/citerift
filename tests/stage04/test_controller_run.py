"""Step 7: the Workflow Controller over fake adapters: plan order, budgets, not_before and the D-042 wall clock.

Owner Step 7 items 3, 4, 6, 9, 11, 12, 13 and 20. SPEC 9.1 to 9.3; MM 7.2, 8. All adapters are SYNTHETIC fakes
(``controller_support``); the real Stage 02/03 adapters and the real Retry-After handoff and kill wrapper are Step 8.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from controller_support import (
    T0,
    Env,
    Plan,
    Session,
    StepClock,
    create,
    env_for,
    journal,
    kinds,
    monotone,
    run_once,
)

from citerift.investigation import workflow
from citerift.investigation.adapters import Deferred, Failed, WallClock
from citerift.investigation.fold import STEPS, Folder

pytestmark = pytest.mark.integration


def _failures(root: Path, key: str, step: str) -> list[dict[str, Any]]:
    return [r["payload"] for r in journal(root, key) if r["kind"] == "step_failed" and r["step"] == step]


def _starts(root: Path, key: str, step: str) -> list[int]:
    return [r["attempt"] for r in journal(root, key) if r["kind"] == "step_started" and r["step"] == step]


# Plan order and the record sequence --------------------------------------------------------------------------------


@pytest.mark.parametrize("live", [False, True], ids=["retained", "live"])
def test_happy_path_runs_the_fixed_plan_in_order(tmp_path: Path, live: bool) -> None:
    clock = StepClock()
    root, key = create(tmp_path, live=live, clock=clock)
    plan = Plan()
    st = run_once(root, key, plan, env_for(live), clock)
    assert st.lifecycle == "COMPLETED" and st.outcome == "completed"
    assert [s for s, _ in plan.calls] == list(STEPS)  # each step once, in plan order, no optional step
    recs = journal(root, key)
    started = [r["step"] for r in recs if r["kind"] == "step_started"]
    succeeded = [r["step"] for r in recs if r["kind"] == "step_succeeded"]
    assert started == succeeded == list(STEPS)
    for i, r in enumerate(recs):  # step k + 1 starts only after step k succeeded
        if r["kind"] == "step_started" and r["step"] != "VALIDATE":
            prev = STEPS[STEPS.index(r["step"]) - 1]
            assert any(x["kind"] == "step_succeeded" and x["step"] == prev for x in recs[:i])
    # The started and succeeded records of each step name the same step key; every key is distinct.
    keys = {r["step"]: r["payload"]["step_key"] for r in recs if r["kind"] == "step_started"}
    assert all(r["payload"]["step_key"] == keys[r["step"]] for r in recs if r["kind"] == "step_succeeded")
    assert len(set(keys.values())) == len(STEPS)


def test_run_on_a_terminal_investigation_reports_it_and_appends_nothing(tmp_path: Path) -> None:
    clock = StepClock()
    root, key = create(tmp_path, clock=clock)
    run_once(root, key, Plan(), Env(), clock)
    before = journal(root, key)
    plan = Plan()
    st = run_once(root, key, plan, Env(), clock)  # S-9.4: a second run is a resume of a terminal investigation
    assert st.lifecycle == "COMPLETED" and plan.calls == [] and journal(root, key) == before
    assert st.next.action == "terminal" and st.next.rule == "W-5"


def test_explanation_names_rule_and_reason(tmp_path: Path) -> None:
    clock = StepClock()
    root, key = create(tmp_path, clock=clock)
    plan = Plan({("EXTRACT", 1): Failed("EXTRACTION_WORKER_FAILED", detail="SYNTHETIC")})
    with Session(root, key, plan, Env(), clock) as ctl:
        e = ctl.explain()
        assert e["next"] == {
            "action": "start",
            "step": "VALIDATE",
            "attempt": 1,
            "rule": "T-START",
            "reason": "VALIDATE pending; VALIDATE is the first step",
            "not_before": None,
        }
        for _ in range(3):
            ctl.step()
        e = ctl.explain()
        assert e["steps"]["EXTRACT"] == {
            "state": "failed_retryable",
            "attempts": 1,
            "phi": 1,
            "f": 0,
            "a_max": 3,
            "f_max": 6,
        }
        assert e["next"]["rule"] == "T-RESTART" and e["next"]["attempt"] == 2


# Retry budget A_max = 3 (SPEC 9.2, W-4) ----------------------------------------------------------------------------


@pytest.mark.parametrize("failures", [0, 1, 2])
def test_extract_retries_below_the_budget_then_succeeds(tmp_path: Path, failures: int) -> None:
    clock = StepClock()
    root, key = create(tmp_path, clock=clock)
    plan = Plan({("EXTRACT", a): Failed("EXTRACTION_DEADLINE_EXCEEDED") for a in range(1, failures + 1)})
    st = run_once(root, key, plan, Env(), clock)
    assert st.lifecycle == "COMPLETED"
    assert _starts(root, key, "EXTRACT") == list(range(1, failures + 2))
    assert [p["retryable"] for p in _failures(root, key, "EXTRACT")] == [True] * failures
    assert st.step("EXTRACT").phi == failures


def test_third_retryable_failure_is_retry_budget_exhausted(tmp_path: Path) -> None:
    clock = StepClock()
    root, key = create(tmp_path, clock=clock)
    plan = Plan({("EXTRACT", a): Failed("EXTRACTION_MEMORY_EXCEEDED", detail="d") for a in (1, 2, 3, 4)})
    st = run_once(root, key, plan, Env(), clock)
    assert st.lifecycle == "FAILED" and st.next.action == "terminal"
    fails = _failures(root, key, "EXTRACT")
    assert [(p["code"], p["retryable"], p["reason"]) for p in fails] == [
        ("EXTRACTION_MEMORY_EXCEEDED", True, None),
        ("EXTRACTION_MEMORY_EXCEEDED", True, None),
        ("RETRY_BUDGET_EXHAUSTED", False, "EXTRACTION_MEMORY_EXCEEDED"),
    ]
    assert _starts(root, key, "EXTRACT") == [1, 2, 3]  # exactly A_max attempts, never a fourth
    assert ("EXTRACT", 4) not in plan.calls


def test_restart_after_exhaustion_does_nothing(tmp_path: Path) -> None:
    clock = StepClock()
    root, key = create(tmp_path, clock=clock)
    run_once(root, key, Plan({("EXTRACT", a): Failed("EXTRACTION_WORKER_FAILED") for a in (1, 2, 3)}), Env(), clock)
    before = journal(root, key)
    plan = Plan()  # everything would now succeed: no counter is reset by a new process
    st = run_once(root, key, plan, Env(), clock)
    assert st.lifecycle == "FAILED" and plan.calls == [] and journal(root, key) == before


def test_budget_counts_across_processes(tmp_path: Path) -> None:
    """Each failure in its own process: the third is still the last (no reset on restart)."""
    clock = StepClock()
    root, key = create(tmp_path, clock=clock)
    for attempt in (1, 2, 3):
        plan = Plan({("EXTRACT", attempt): Failed("EXTRACTION_WORKER_FAILED")})
        with Session(root, key, plan, Env(), clock) as ctl:  # one process per failure
            while len(ctl.view.attempts["EXTRACT"]) < attempt:
                ctl.step()
    fails = _failures(root, key, "EXTRACT")
    assert [p["code"] for p in fails] == ["EXTRACTION_WORKER_FAILED"] * 2 + ["RETRY_BUDGET_EXHAUSTED"]


def test_non_retryable_code_is_terminal_at_once(tmp_path: Path) -> None:
    clock = StepClock()
    root, key = create(tmp_path, clock=clock)
    st = run_once(root, key, Plan({("NORMALIZE", 1): Failed("NORMALIZE_INVALID")}), Env(), clock)
    assert st.lifecycle == "FAILED"
    assert [(p["code"], p["retryable"]) for p in _failures(root, key, "NORMALIZE")] == [("NORMALIZE_INVALID", False)]


@pytest.mark.parametrize("live", [False, True], ids=["retained", "live"])
def test_network_code_is_retryable_only_for_a_live_capture(tmp_path: Path, live: bool) -> None:
    clock = StepClock()
    root, key = create(tmp_path, live=live, clock=clock)
    st = run_once(root, key, Plan({("ACQUIRE", 1): Failed("HTTP_TIMEOUT")}), env_for(live), clock)
    assert st.lifecycle == ("COMPLETED" if live else "FAILED")
    assert _failures(root, key, "ACQUIRE")[0]["retryable"] is live


# Deferral budget F_max = 6 and the ACQUIRE maximum of 9 attempts ------------------------------------------------------


def _deferring_plan(deferrals: int, failures: int = 0, final: Any = "ok") -> tuple[Plan, StepClock]:
    clock = StepClock()
    script: dict[tuple[str, int], Any] = {}
    a = 1
    for _ in range(failures):
        script[("ACQUIRE", a)] = Failed("HTTP_SERVER_ERROR", not_before=None)
        a += 1
    for _ in range(deferrals):
        script[("ACQUIRE", a)] = lambda req: Deferred(req.now + timedelta(seconds=30))
        a += 1
    script[("ACQUIRE", a)] = final
    return Plan(script), clock


def _run_until_terminal(root: Path, key: str, plan: Plan, clock: StepClock, env: Env) -> Any:
    """Resume repeatedly, moving the clock past each not_before (the controller never sleeps)."""
    for _ in range(20):
        st = run_once(root, key, plan, env, clock)
        if st.next.action != "wait":
            return st
        assert st.next.not_before is not None
        clock.t = st.next.not_before
    raise AssertionError("did not finish")


@pytest.mark.parametrize("deferrals", [1, 5, 6])
def test_deferrals_up_to_the_budget_then_success(tmp_path: Path, deferrals: int) -> None:
    plan, clock = _deferring_plan(deferrals)
    root, key = create(tmp_path, live=True, clock=clock)
    st = _run_until_terminal(root, key, plan, clock, env_for(True))
    assert st.lifecycle == "COMPLETED"
    assert st.step("ACQUIRE").f == deferrals and st.step("ACQUIRE").attempts == deferrals + 1


def test_seventh_deferral_is_deferral_budget_exhausted(tmp_path: Path) -> None:
    plan, clock = _deferring_plan(6, final=lambda req: Deferred(req.now + timedelta(seconds=30)))
    root, key = create(tmp_path, live=True, clock=clock)
    st = _run_until_terminal(root, key, plan, clock, env_for(True))
    assert st.lifecycle == "FAILED"
    last = _failures(root, key, "ACQUIRE")[-1]
    assert (last["code"], last["retryable"], last["reason"]) == (
        "DEFERRAL_BUDGET_EXHAUSTED",
        False,
        "DEFERRED_RETRY_AFTER",
    )
    assert st.step("ACQUIRE").attempts == 7 and st.step("ACQUIRE").f == 6


def test_acquire_reaches_nine_attempts_and_no_more(tmp_path: Path) -> None:
    """Two failures, six deferrals and a final attempt (SPEC 9.2: at most A_max + F_max = 9)."""
    plan, clock = _deferring_plan(6, failures=2, final=Failed("HTTP_TIMEOUT"))
    root, key = create(tmp_path, live=True, clock=clock)
    st = _run_until_terminal(root, key, plan, clock, env_for(True))
    assert st.lifecycle == "FAILED"
    assert _starts(root, key, "ACQUIRE") == list(range(1, 10))
    assert _failures(root, key, "ACQUIRE")[-1]["code"] == "RETRY_BUDGET_EXHAUSTED"


def test_nine_attempts_can_still_succeed(tmp_path: Path) -> None:
    plan, clock = _deferring_plan(6, failures=2)
    root, key = create(tmp_path, live=True, clock=clock)
    st = _run_until_terminal(root, key, plan, clock, env_for(True))
    assert st.lifecycle == "COMPLETED" and st.step("ACQUIRE").attempts == 9


def test_deferral_only_for_live_acquire(tmp_path: Path) -> None:
    clock = StepClock()
    root, key = create(tmp_path, clock=clock)  # retained bundle: ACQUIRE defect code is ADAPTER_INCONSISTENT
    st = run_once(root, key, Plan({("ACQUIRE", 1): Deferred(T0 + timedelta(hours=1))}), Env(), clock)
    assert st.lifecycle == "FAILED"
    assert _failures(root, key, "ACQUIRE")[0]["code"] == "ADAPTER_INCONSISTENT"


# not_before (SPEC 9.2 T-RESTART, D-042) ----------------------------------------------------------------------------


def _blocked_on(tmp_path: Path, result: Any) -> tuple[Path, str, StepClock, Any]:
    clock = StepClock()
    root, key = create(tmp_path, live=True, clock=clock)
    st = run_once(root, key, Plan({("ACQUIRE", 1): result}), env_for(True), clock)
    return root, key, clock, st


@pytest.mark.parametrize("kind", ["deferred", "failed"])
def test_future_not_before_makes_the_run_wait_without_sleeping(tmp_path: Path, kind: str) -> None:
    nb = T0 + timedelta(hours=2)
    result = Deferred(nb) if kind == "deferred" else Failed("HTTP_RATE_LIMITED", not_before=nb)
    root, key, clock, st = _blocked_on(tmp_path, result)
    assert st.next.action == "wait" and st.next.not_before == nb and st.next.rule == "T-RESTART"
    assert st.lifecycle == ("BLOCKED" if kind == "deferred" else "RUNNING")
    before = journal(root, key)
    plan = Plan()
    st2 = run_once(root, key, plan, env_for(True), clock)  # still before not_before: nothing happens
    assert plan.calls == [] and journal(root, key) == before and st2.next.action == "wait"


@pytest.mark.parametrize(
    ("offset", "starts"),
    [
        pytest.param(timedelta(microseconds=-1), False, id="just-before"),
        pytest.param(timedelta(0), True, id="exact-boundary"),
        pytest.param(timedelta(microseconds=1), True, id="just-after"),
    ],
)
@pytest.mark.parametrize("kind", ["deferred", "failed"])
def test_not_before_boundary(tmp_path: Path, kind: str, offset: timedelta, starts: bool) -> None:
    nb = T0 + timedelta(hours=2)
    result = Deferred(nb) if kind == "deferred" else Failed("HTTP_RATE_LIMITED", not_before=nb)
    root, key, clock, _ = _blocked_on(tmp_path, result)
    clock.t, clock.tick = nb + offset, timedelta(0)  # hold the time exactly there
    plan = Plan()
    st = run_once(root, key, plan, env_for(True), clock)
    assert (("ACQUIRE", 2) in plan.calls) is starts
    if starts:
        start = next(r for r in journal(root, key) if r["kind"] == "step_started" and r["attempt"] == 2)
        assert start["at"] >= nb.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        assert st.lifecycle == "COMPLETED"


def test_no_not_before_restarts_at_once(tmp_path: Path) -> None:
    root, key, _clock, st = _blocked_on(tmp_path, Failed("HTTP_TIMEOUT", not_before=None))
    assert st.lifecycle == "COMPLETED" and _starts(root, key, "ACQUIRE") == [1, 2]


def test_not_before_survives_process_death(tmp_path: Path) -> None:
    """The instant is in the journal: a new process with an early clock still waits."""
    nb = T0 + timedelta(hours=2)
    root, key, _clock, _ = _blocked_on(tmp_path, Failed("HTTP_RATE_LIMITED", not_before=nb))
    for t, expect in ((nb - timedelta(seconds=5), "wait"), (nb, "terminal")):
        fresh = StepClock(t, timedelta(0))  # a new process whose clock knows nothing of the earlier one
        assert run_once(root, key, Plan(), env_for(True), fresh).next.action == expect


def test_guard_refuses_a_restart_record_before_not_before(tmp_path: Path) -> None:
    nb = T0 + timedelta(hours=2)
    root, key, _, _ = _blocked_on(tmp_path, Deferred(nb))
    f = Folder(None)
    for r in journal(root, key):
        f.apply(r)
    early = {
        "kind": "step_started",
        "step": "ACQUIRE",
        "attempt": 2,
        "at": "2026-11-10T13:59:59.999999Z",
        "payload": {},
    }
    with pytest.raises(workflow.WorkflowRefused) as exc:
        workflow.guard(early, f, orphan=False)
    assert exc.value.rule == "T-RESTART"
    on_time = dict(early, at="2026-11-10T14:00:00.000000Z")
    assert workflow.guard(on_time, f, orphan=False) == "T-RESTART"


def test_monotone_clock_never_goes_back() -> None:
    src = StepClock(T0, timedelta(0))
    mono = monotone(src)
    first = mono()
    src.t = T0 - timedelta(days=1)
    assert mono() == first


# ACQUIRE_WALL_CLOCK_EXCEEDED (D-042) --------------------------------------------------------------------------------

WALL = WallClock(t_acq_ms=240_000, elapsed_ms=240_012)


def test_wall_clock_with_known_retry_after_is_retryable_and_honours_not_before(tmp_path: Path) -> None:
    nb = T0 + timedelta(minutes=10)
    root, key, _clock, st = _blocked_on(tmp_path, Failed("ACQUIRE_WALL_CLOCK_EXCEEDED", not_before=nb, wall_clock=WALL))
    p = _failures(root, key, "ACQUIRE")[0]
    assert (p["code"], p["retryable"], p["wall_clock"]) == (
        "ACQUIRE_WALL_CLOCK_EXCEEDED",
        True,
        {"t_acq_ms": 240_000, "elapsed_ms": 240_012},
    )
    assert p["not_before"] == nb.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    assert st.next.action == "wait" and st.step("ACQUIRE").phi == 1
    # The killed attempt bound no root and committed nothing.
    assert all(r["root_id"] is None for r in journal(root, key))


def test_wall_clock_with_unknown_retry_after_is_terminal(tmp_path: Path) -> None:
    result = Failed("ACQUIRE_WALL_CLOCK_EXCEEDED", wall_clock=WALL, retry_after_known=False)
    root, key, _, st = _blocked_on(tmp_path, result)
    p = _failures(root, key, "ACQUIRE")[0]
    assert st.lifecycle == "FAILED" and (p["code"], p["retryable"]) == ("ACQUIRE_WALL_CLOCK_EXCEEDED", False)
    assert p["wall_clock"] == {"t_acq_ms": 240_000, "elapsed_ms": 240_012}


def test_third_wall_clock_failure_exhausts_the_retry_budget(tmp_path: Path) -> None:
    clock = StepClock()
    root, key = create(tmp_path, live=True, clock=clock)
    plan = Plan({("ACQUIRE", a): Failed("ACQUIRE_WALL_CLOCK_EXCEEDED", wall_clock=WALL) for a in (1, 2, 3)})
    st = run_once(root, key, plan, env_for(True), clock)
    fails = _failures(root, key, "ACQUIRE")
    assert st.lifecycle == "FAILED"
    assert [(p["code"], p["retryable"]) for p in fails] == [
        ("ACQUIRE_WALL_CLOCK_EXCEEDED", True),
        ("ACQUIRE_WALL_CLOCK_EXCEEDED", True),
        ("RETRY_BUDGET_EXHAUSTED", False),
    ]
    assert fails[-1]["reason"] == "ACQUIRE_WALL_CLOCK_EXCEEDED" and fails[-1]["wall_clock"] is None


@pytest.mark.negative
@pytest.mark.parametrize(
    "result",
    [
        pytest.param(Failed("ACQUIRE_WALL_CLOCK_EXCEEDED"), id="no-wall-clock-data"),
        pytest.param(Failed("HTTP_TIMEOUT", wall_clock=WALL), id="wall-clock-on-another-code"),
        pytest.param(Failed("HTTP_TIMEOUT", retry_after_known=False), id="unknown-retry-after-on-another-code"),
        pytest.param(Failed("RETRY_BUDGET_EXHAUSTED"), id="controller-code-from-adapter"),
        pytest.param(Failed("DEFERRAL_BUDGET_EXHAUSTED"), id="controller-deferral-code-from-adapter"),
    ],
)
def test_malformed_acquire_failures_are_adapter_defects(tmp_path: Path, result: Failed) -> None:
    root, key, _, st = _blocked_on(tmp_path, result)
    assert st.lifecycle == "FAILED"
    assert [p["code"] for p in _failures(root, key, "ACQUIRE")] == ["ADAPTER_INCONSISTENT"]


@pytest.mark.negative
def test_wall_clock_on_a_retained_bundle_is_a_defect(tmp_path: Path) -> None:
    clock = StepClock()
    root, key = create(tmp_path, clock=clock)
    run_once(root, key, Plan({("ACQUIRE", 1): Failed("ACQUIRE_WALL_CLOCK_EXCEEDED", wall_clock=WALL)}), Env(), clock)
    assert [p["code"] for p in _failures(root, key, "ACQUIRE")] == ["ADAPTER_INCONSISTENT"]


def test_journal_kinds_of_a_retry(tmp_path: Path) -> None:
    clock = StepClock()
    root, key = create(tmp_path, clock=clock)
    run_once(root, key, Plan({("EXTRACT", 1): Failed("EXTRACTION_WORKER_FAILED")}), Env(), clock)
    k = [x for x in kinds(root, key) if x[1] == "EXTRACT"]
    assert k == [
        ("step_started", "EXTRACT", 1),
        ("step_failed", "EXTRACT", 1),
        ("step_started", "EXTRACT", 2),
        ("observation_recorded", "EXTRACT", 2),
        ("step_succeeded", "EXTRACT", 2),
    ]
