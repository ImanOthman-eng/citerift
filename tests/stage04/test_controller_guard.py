"""Step 7: the append guard (MM 8) and the workflow invariants W-1 to W-8 (owner Step 7 items 5, 6, 7 and 21).

``test_transition_matrix`` proposes every record kind in every step state of SPEC 9.2 and checks the guard's answer
against a table written from SPEC 9.2 (not from the code). The W tests each have a positive case (a controller run
satisfies the invariant) and a negative one: a journal that Memory accepts (M-1 to M-14 hold) but that breaks the
invariant is refused on open (``WorkflowCorrupt``, CORRUPT, nothing changed), or the record is refused before it is
written. SYNTHETIC fake adapters.
"""

from __future__ import annotations

import copy
import os
from collections import Counter
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from controller_support import (
    BUNDLE,
    Env,
    Plan,
    Session,
    StepClock,
    create,
    digest,
    env_for,
    journal,
    raw_records,
    run_once,
)
from memory_support import root_object

from citerift.investigation import batches, workflow
from citerift.investigation.adapters import Deferred, Failed
from citerift.investigation.controller import WorkflowController, run_investigation
from citerift.investigation.fold import STEPS, Folder
from citerift.investigation.memory import InvestigationMemory

pytestmark = pytest.mark.unit

RULES = (
    "T-CREATE",
    "T-START",
    "T-CONTENT",
    "T-SUCCEED",
    "T-FAIL-R",
    "T-FAIL-T",
    "T-DEFER",
    "T-RESTART",
    "T-INTERRUPT",
    "T-STALE",
)


def _rules(root: Path, key: str) -> list[str]:
    """The transition rule of each stored record, replayed as ``check_journal`` does (D-055: the replay takes the
    logical content of the batches from the validated fold)."""
    with InvestigationMemory.open(root, key, writable=False) as mem:
        view = mem.view
    f = Folder(None, expected_key=view.expected_key, source=view)
    out = []
    for r in view.records:
        out.append(workflow.guard(r, f, orphan=None))
        f.apply(r)
    return out


# Every legal and every forbidden transition (SPEC 9.2) -------------------------------------------------------------

OBS = {
    "obs_kind": "bundle",
    "blob": digest(BUNDLE),
    "source_ref": {"engine": "citerift.wiki", "operation": "open_bundle", "locator": None},
}


def _proposal(kind: str, f: Folder, which: str) -> dict[str, Any]:
    """An ACQUIRE record of ``kind`` proposed in the fold ``f`` (live capture)."""
    n = len(f.attempts["ACQUIRE"])
    attempt = {"next": n + 1, "same": n, "skip": n + 2}.get(which, f.open.number if f.open else n)
    key = "7" * 64
    payload: dict[str, Any] = {"step_key": key}
    if kind == "content":
        return {
            "kind": "observation_recorded",
            "step": "ACQUIRE",
            "attempt": attempt,
            "payload": OBS,
            "at": "2099-01-01T00:00:00Z",
        }
    if kind == "step_succeeded":
        if f.open is not None:
            key = f.records[f.open.start_seq]["payload"]["step_key"]
        payload = {"step_key": key, "outputs": [digest(BUNDLE)], "root": root_object()}
    if kind == "step_failed":
        code, retryable, reason = {
            "retryable": ("HTTP_TIMEOUT", True, None),
            "terminal": ("PAGE_MISSING", False, None),
            "budget": ("RETRY_BUDGET_EXHAUSTED", False, "HTTP_TIMEOUT"),
            "deferral_budget": ("DEFERRAL_BUDGET_EXHAUSTED", False, "DEFERRED_RETRY_AFTER"),
        }[which]
        payload = {
            "step_key": key,
            "code": code,
            "retryable": retryable,
            "reason": reason,
            "detail": None,
            "wall_clock": None,
            "not_before": None,
        }
    if kind == "step_deferred":
        payload = {"step_key": key, "code": "DEFERRED_RETRY_AFTER", "not_before": "2099-01-01T00:00:00Z"}
    return {"kind": kind, "step": "ACQUIRE", "attempt": attempt, "payload": payload, "at": "2099-01-01T00:00:00Z"}


PROPOSALS = [
    ("step_started", "next"),
    ("step_started", "same"),
    ("step_started", "skip"),
    ("content", ""),
    ("step_succeeded", ""),
    ("step_failed", "retryable"),
    ("step_failed", "terminal"),
    ("step_failed", "budget"),
    ("step_failed", "deferral_budget"),
    ("step_deferred", ""),
    ("step_interrupted", ""),
]
_ALL_M6 = {p: "M-6" for p in PROPOSALS if p[0] != "step_started"}
_RUNNING = {
    ("step_started", "next"): "W-3",
    ("step_started", "same"): "W-3",
    ("step_started", "skip"): "W-3",
    ("content", ""): "+T-CONTENT",
    ("step_succeeded", ""): "T-SUCCEED",  # refused: no content written yet
    ("step_failed", "retryable"): "+T-FAIL-R",
    ("step_failed", "terminal"): "+T-FAIL-T",
    ("step_failed", "budget"): "W-4",
    ("step_failed", "deferral_budget"): "W-4",
    ("step_deferred", ""): "+T-DEFER",
    ("step_interrupted", ""): "W-6",
}
# Expected guard answer per ACQUIRE state (written from SPEC 9.2): "+RULE" legal by RULE, "RULE" refused by RULE.
EXPECTED: dict[str, dict[tuple[str, str], str]] = {
    "pending": {
        ("step_started", "next"): "+T-START",
        ("step_started", "same"): "M-6",
        ("step_started", "skip"): "M-6",
        **_ALL_M6,
    },
    "running": _RUNNING,
    "running_with_content": {**_RUNNING, ("step_succeeded", ""): "+T-SUCCEED"},
    "running_orphan": {
        **{p: "W-6" for p in _RUNNING if p[0] != "step_started"},
        ("step_started", "next"): "W-3",
        ("step_started", "same"): "W-3",
        ("step_started", "skip"): "W-3",
        ("step_failed", "budget"): "W-4",  # W-6 permits budget exhaustion only at phi + 1 = A_max
        ("step_interrupted", ""): "+T-INTERRUPT",
    },
    "succeeded": {
        ("step_started", "next"): "TR-2",
        ("step_started", "same"): "M-6",
        ("step_started", "skip"): "M-6",
        **_ALL_M6,
    },
    "failed_retryable": {
        ("step_started", "next"): "+T-RESTART",
        ("step_started", "same"): "M-6",
        ("step_started", "skip"): "M-6",
        **_ALL_M6,
    },
    "pending_after_interrupt": {
        ("step_started", "next"): "+T-RESTART",
        ("step_started", "same"): "M-6",
        ("step_started", "skip"): "M-6",
        **_ALL_M6,
    },
    "deferred_not_ready": {
        ("step_started", "next"): "T-RESTART",
        ("step_started", "same"): "M-6",
        ("step_started", "skip"): "M-6",
        **_ALL_M6,
    },
    "deferred_ready": {
        ("step_started", "next"): "+T-RESTART",
        ("step_started", "same"): "M-6",
        ("step_started", "skip"): "M-6",
        **_ALL_M6,
    },
    "failed_terminal": dict.fromkeys(PROPOSALS, "W-5"),
}


def _state(tmp_path: Path, name: str) -> Folder:
    clock = StepClock()
    root, key = create(tmp_path, live=True, clock=clock)
    script: dict[tuple[str, int], Any] = {
        "succeeded": {},
        "failed_retryable": {("ACQUIRE", 1): Failed("HTTP_TIMEOUT")},
        "failed_terminal": {("ACQUIRE", 1): Failed("PAGE_MISSING")},
        "deferred_not_ready": {("ACQUIRE", 1): Deferred(clock.t + timedelta(days=36500))},
        "deferred_ready": {("ACQUIRE", 1): Deferred(clock.t + timedelta(seconds=1))},
    }.get(name, {})
    with Session(root, key, Plan(script), env_for(True), clock) as ctl:
        ctl.step()  # VALIDATE
        if name in ("succeeded", "failed_retryable", "failed_terminal", "deferred_not_ready", "deferred_ready"):
            ctl.step()
        elif name != "pending":
            k = workflow.step_key(ctl.view, "ACQUIRE", ctl.current_digests())
            ctl._append("step_started", {"step_key": k}, "ACQUIRE", 1)
            if name == "running_with_content":
                ctl._mem.put_blob(BUNDLE)
                ctl._append("observation_recorded", OBS, "ACQUIRE", 1)
            if name == "running":
                ctl._own.add(("ACQUIRE", 1))
        f = copy.deepcopy(ctl.view)
    if name == "pending_after_interrupt":
        with Session(root, key, Plan(), env_for(True), clock) as ctl:
            ctl.recover()
            f = copy.deepcopy(ctl.view)
    return f


def test_transition_matrix(tmp_path: Path) -> None:
    counts: Counter[str] = Counter()
    for i, (name, table) in enumerate(EXPECTED.items()):
        base = tmp_path / str(i)
        base.mkdir()
        f = _state(base, name)
        orphan = name == "running_orphan"
        for prop, want in table.items():
            rec = _proposal(prop[0], f, prop[1])
            if prop[0] == "step_started" and rec["attempt"] < 1:
                rec["attempt"] = 0
            try:
                got = "+" + workflow.guard(rec, f, orphan=orphan)
            except workflow.WorkflowRefused as exc:
                got = exc.rule
            assert got == want, (name, prop, got)
            counts["legal" if got.startswith("+") else "refused"] += 1
        # Step k + 1 never starts before step k succeeded (W-3).
        if name != "succeeded":
            start = {
                "kind": "step_started",
                "step": "EXTRACT",
                "attempt": 1,
                "payload": {},
                "at": "2099-01-01T00:00:00Z",
            }
            with pytest.raises(workflow.WorkflowRefused) as exc:
                workflow.guard(start, f, orphan=False)
            assert exc.value.rule in ("W-3", "W-5")
            counts["refused"] += 1
    assert counts == {"legal": 14, "refused": 105}  # 10 states x 11 proposals + 9 early EXTRACT starts


def test_every_transition_rule_is_used_by_controller_runs(tmp_path: Path) -> None:
    used: Counter[str] = Counter()
    scenarios: list[tuple[bool, dict[tuple[str, int], Any], Env | None]] = [
        (False, {("EXTRACT", 1): Failed("EXTRACTION_WORKER_FAILED")}, None),
        (True, {("ACQUIRE", 1): lambda r: Deferred(r.now + timedelta(seconds=1))}, None),
        (False, {("NORMALIZE", 1): Failed("NORMALIZE_INVALID")}, None),
    ]
    for i, (live, script, _) in enumerate(scenarios):
        base = tmp_path / str(i)
        base.mkdir()
        clock = StepClock()
        root, key = create(base, live=live, clock=clock)
        for _ in range(3):
            st = run_once(root, key, Plan(script), env_for(live), clock)
            if st.next.action == "wait" and st.next.not_before:
                clock.t = st.next.not_before
        used.update(_rules(root, key))
    # An interruption and a staleness record.
    base = tmp_path / "x"
    base.mkdir()
    clock = StepClock()
    root, key = create(base, clock=clock)

    class Stop(BaseException):
        pass

    def stop(req: Any) -> Any:
        raise Stop

    with pytest.raises(Stop):
        run_once(root, key, Plan({("LOOKUP", 1): stop}), Env(), clock)
    env = Env()
    env.values["config"]["extra"] = 1
    assert run_once(root, key, Plan(), env, clock).lifecycle == "STALE"
    used.update(_rules(root, key))
    assert set(used) == set(RULES), sorted(set(RULES) - set(used))


# W-1 to W-8 -------------------------------------------------------------------------------------------------------


def _forge(
    root: Path, key: str, clock: StepClock, records: list[tuple[str, dict[str, Any], str | None, int | None]]
) -> None:
    """Append records with Memory's checks only (no workflow guard): a journal Memory accepts."""
    with InvestigationMemory.open(root, key, clock=clock) as mem:
        for kind, payload, step, attempt in records:
            if kind == "blob":
                mem.put_blob(payload)
                continue
            mem.append(kind, payload, step=step, attempt=attempt)


def _batched(
    items: list[dict[str, Any]], step: str, attempt: int
) -> list[tuple[str, dict[str, Any], str | None, int | None]]:
    """Forge entries that commit ``items`` (no references outside them) as canonical evidence batches (D-053)."""
    evidence = batches.evidence_batches(items, lambda ref: False)
    digests = [digest(b) for b in evidence]
    out: list[tuple[str, dict[str, Any], str | None, int | None]] = [("blob", b, None, None) for b in evidence]
    out += [("evidence_batch_recorded", r, step, attempt) for r in batches.batch_records(digests, evidence)]
    return out


def _candidates(
    entries: list[dict[str, Any]], step: str, attempt: int
) -> list[tuple[str, dict[str, Any], str | None, int | None]]:
    """Forge entries that commit DETECT candidate results as canonical candidate-result batches (D-055)."""
    parts = batches.ordered_parts(entries, batches.candidate_key, batches.candidate_batch)
    digests = [digest(b) for b in parts]
    out: list[tuple[str, dict[str, Any], str | None, int | None]] = [("blob", b, None, None) for b in parts]
    out += [("candidate_result_batch_recorded", r, step, attempt) for r in batches.entry_records(digests, parts)]
    return out


def _assert_corrupt(root: Path, key: str, clock: StepClock, rule: str) -> None:
    inv = root / key
    before = {p.name: p.read_bytes() for p in inv.iterdir() if p.is_file() and p.name != "lock"}
    res = run_investigation(root, key, Plan().adapters(), Env(), clock=clock)
    assert res.status == "CORRUPT" and f"{rule}:" in res.detail, res.detail
    after = {p.name: p.read_bytes() for p in inv.iterdir() if p.is_file() and p.name != "lock"}
    assert after == before  # CORRUPT: nothing changed


def _until(
    tmp_path: Path, step: str, *, live: bool = False, script: dict[tuple[str, int], Any] | None = None
) -> tuple[Path, str, StepClock]:
    """A journal in which ``step`` and everything before it succeeded (closed between processes)."""
    clock = StepClock()
    root, key = create(tmp_path, live=live, clock=clock)
    with Session(root, key, Plan(script), env_for(live), clock) as ctl:
        while ctl.view.step_state(step) not in ("succeeded", "failed_terminal", "failed_retryable", "deferred"):
            ctl.step()
    return root, key, clock


def _key(root: Path, key: str, clock: StepClock, step: str, live: bool = False) -> str:
    with Session(root, key, Plan(), env_for(live), clock) as ctl:
        return workflow.step_key(ctl.view, step, ctl.current_digests())


@pytest.mark.integration
def test_w1_state_is_a_function_of_the_journal(tmp_path: Path) -> None:
    clock = StepClock()
    root, key = create(tmp_path, clock=clock)
    with Session(root, key, Plan({("EXTRACT", 1): Failed("EXTRACTION_WORKER_FAILED")}), Env(), clock) as ctl:
        for _ in range(20):
            if ctl.state().next.action == "terminal":
                break
            ctl.step()
            now = clock.t
            fresh = Folder(None)
            for r in raw_records(root, key):
                fresh.apply(r)
            # Only the time is an input besides the journal. The instance's one field (attempts it opened) does not
            # enter the state.
            ctl._own.clear()
            assert ctl.state() == workflow.derive(fresh, now + clock.tick)
            clock.t = now


@pytest.mark.negative
def test_w2_illegal_path_in_a_memory_valid_journal_is_corrupt(tmp_path: Path) -> None:
    root, key, clock = _until(tmp_path, "VALIDATE")  # retained bundle: ACQUIRE is never deferred
    k = _key(root, key, clock, "ACQUIRE")
    _forge(
        root,
        key,
        clock,
        [
            ("step_started", {"step_key": k}, "ACQUIRE", 1),
            (
                "step_deferred",
                {"step_key": k, "code": "DEFERRED_RETRY_AFTER", "not_before": "2099-01-01T00:00:00Z"},
                "ACQUIRE",
                1,
            ),
        ],
    )
    _assert_corrupt(root, key, clock, "T-DEFER")


@pytest.mark.negative
def test_w3_plan_order_violation_is_corrupt(tmp_path: Path) -> None:
    root, key, clock = _until(tmp_path, "ACQUIRE")
    _forge(root, key, clock, [("step_started", {"step_key": "8" * 64}, "NORMALIZE", 1)])  # EXTRACT never ran
    _assert_corrupt(root, key, clock, "W-3")


@pytest.mark.negative
def test_w3_overlapping_attempt_is_refused_before_it_is_written(tmp_path: Path) -> None:
    root, key, clock = _until(tmp_path, "ACQUIRE")
    with Session(root, key, Plan(), Env(), clock) as ctl:
        k = workflow.step_key(ctl.view, "EXTRACT", ctl.current_digests())
        ctl._append("step_started", {"step_key": k}, "EXTRACT", 1)
        n = len(ctl.view.records)
        for step, attempt in (("EXTRACT", 2), ("NORMALIZE", 1)):
            with pytest.raises(workflow.WorkflowRefused) as exc:
                ctl._append("step_started", {"step_key": k}, step, attempt)
            assert exc.value.rule == "W-3"
        assert len(ctl.view.records) == n


@pytest.mark.negative
def test_w4_budget_exhaustion_before_the_budget_is_corrupt(tmp_path: Path) -> None:
    root, key, clock = _until(tmp_path, "ACQUIRE")
    k = _key(root, key, clock, "EXTRACT")
    payload = {
        "step_key": k,
        "code": "RETRY_BUDGET_EXHAUSTED",
        "retryable": False,
        "reason": "EXTRACTION_WORKER_FAILED",
        "detail": None,
        "wall_clock": None,
    }
    _forge(root, key, clock, [("step_started", {"step_key": k}, "EXTRACT", 1), ("step_failed", payload, "EXTRACT", 1)])
    _assert_corrupt(root, key, clock, "W-4")


@pytest.mark.negative
def test_w4_retryable_failure_past_the_budget_is_corrupt(tmp_path: Path) -> None:
    script = {("EXTRACT", a): Failed("EXTRACTION_WORKER_FAILED") for a in (1, 2)}
    root, key, clock = _until(tmp_path, "ACQUIRE", script=script)
    with Session(root, key, Plan(script), Env(), clock) as ctl:
        ctl.step()
        ctl.step()
    k = _key(root, key, clock, "EXTRACT")
    payload = {
        "step_key": k,
        "code": "EXTRACTION_WORKER_FAILED",
        "retryable": True,
        "reason": None,
        "detail": None,
        "wall_clock": None,
    }
    _forge(root, key, clock, [("step_started", {"step_key": k}, "EXTRACT", 3), ("step_failed", payload, "EXTRACT", 3)])
    _assert_corrupt(root, key, clock, "W-4")


@pytest.mark.negative
@pytest.mark.parametrize("lifecycle", ["FAILED", "COMPLETED"])
def test_w5_record_after_terminal_is_corrupt_and_refused(tmp_path: Path, lifecycle: str) -> None:
    clock = StepClock()
    root, key = create(tmp_path, clock=clock)
    script = {("LOOKUP", 1): Failed("INDEX_MISSING")} if lifecycle == "FAILED" else {}
    assert run_once(root, key, Plan(script), Env(), clock).lifecycle == lifecycle
    with InvestigationMemory.open(root, key, clock=clock) as mem:
        g = copy.deepcopy(mem.view)
    for kind, step, attempt in (("step_started", "LOOKUP", 2), ("stale_detected", None, None)):
        rec = {"kind": kind, "step": step, "attempt": attempt, "payload": {}, "at": "2099-01-01T00:00:00Z"}
        with pytest.raises(workflow.WorkflowRefused) as exc:
            workflow.guard(rec, g, orphan=False)
        assert exc.value.rule == "W-5"
    zero, one = "0" * 64, "1" * 64
    _forge(
        root,
        key,
        clock,
        [
            (
                "stale_detected",
                {"changed": ["config"], "recorded": {"config": zero}, "current": {"config": one}},
                None,
                None,
            )
        ],
    )
    _assert_corrupt(root, key, clock, "W-5")


@pytest.mark.integration
def test_w6_resume_closes_the_open_attempt_first(tmp_path: Path) -> None:
    root, key, clock = _until(tmp_path, "ACQUIRE")
    k = _key(root, key, clock, "EXTRACT")
    _forge(root, key, clock, [("step_started", {"step_key": k}, "EXTRACT", 1)])  # a process died here
    n = len(journal(root, key))
    st = run_once(root, key, Plan(), Env(), clock)
    recs = journal(root, key)
    assert st.lifecycle == "COMPLETED"
    assert (recs[n]["kind"], recs[n]["step"], recs[n]["attempt"]) == ("step_interrupted", "EXTRACT", 1)
    assert recs[n]["payload"] == {"step_key": k}


@pytest.mark.negative
def test_w6_an_orphan_attempt_cannot_be_continued(tmp_path: Path) -> None:
    root, key, clock = _until(tmp_path, "ACQUIRE")
    k = _key(root, key, clock, "EXTRACT")
    _forge(root, key, clock, [("step_started", {"step_key": k}, "EXTRACT", 1)])
    with Session(root, key, Plan(), Env(), clock) as ctl:
        f = ctl.view
        for kind, payload in (
            ("observation_recorded", OBS),
            ("step_succeeded", {"step_key": k, "outputs": [], "root": None}),
            ("step_failed", {"step_key": k, "code": "EXTRACTION_FAILED", "retryable": False}),
        ):
            rec = {"kind": kind, "step": "EXTRACT", "attempt": 1, "payload": payload, "at": "2099-01-01T00:00:00Z"}
            with pytest.raises(workflow.WorkflowRefused) as exc:
                workflow.guard(rec, f, orphan=True)
            assert exc.value.rule == "W-6"
        live = {
            "kind": "step_interrupted",
            "step": "EXTRACT",
            "attempt": 1,
            "payload": {},
            "at": "2099-01-01T00:00:00Z",
        }
        with pytest.raises(workflow.WorkflowRefused) as exc:
            workflow.guard(live, f, orphan=False)  # a live process never marks its own attempt interrupted
        assert exc.value.rule == "W-6"
        # The controller refuses to "recover" an attempt it opened itself (an impossible state).
        ctl._own.add(("EXTRACT", 1))
        with pytest.raises(workflow.WorkflowRefused) as exc:
            ctl.recover()
        assert exc.value.rule == "W-6"


def _verify_forgery(tmp_path: Path, content: Callable[[str], list[Any]], rule: str) -> None:
    root, key, clock = _until(tmp_path, "ASSEMBLE")
    k = _key(root, key, clock, "VERIFY")
    with InvestigationMemory.open(root, key, writable=False) as mem:
        cj = mem.view.content_digest()
    man = {"forged": True}
    _forge(
        root,
        key,
        clock,
        [
            ("blob", man, None, None),
            ("step_started", {"step_key": k}, "VERIFY", 1),
            *content(cj),
            ("step_succeeded", {"step_key": k, "outputs": [digest(man)], "root": None}, "VERIFY", 1),
        ],
    )
    _assert_corrupt(root, key, clock, rule)


@pytest.mark.negative
@pytest.mark.parametrize(
    ("name", "content", "rule"),
    [
        pytest.param("no-verification", lambda cj: [], "T-SUCCEED", id="no-verification"),
        pytest.param(
            "failed-verification",
            lambda cj: [
                (
                    "verification_recorded",
                    {
                        "result": "failed",
                        "checks": [{"check": "W_INVARIANTS", "passed": False}],
                        "content_digest": None,
                    },
                    "VERIFY",
                    1,
                )
            ],
            "W-7",
            id="failed-verification",
        ),
        pytest.param(
            "wrong-digest",
            lambda cj: [
                (
                    "verification_recorded",
                    {
                        "result": "passed",
                        "checks": [{"check": "W_INVARIANTS", "passed": True}],
                        "content_digest": "9" * 64,
                    },
                    "VERIFY",
                    1,
                )
            ],
            "W-7",
            id="wrong-content-digest",
        ),
    ],
)
def test_w7_completion_without_the_predicate_is_corrupt(
    tmp_path: Path, name: str, content: Callable[[str], list[Any]], rule: str
) -> None:
    _verify_forgery(tmp_path, content, rule)


@pytest.mark.integration
def test_w7_positive_completed_has_a_passed_verification_of_cj(tmp_path: Path) -> None:
    clock = StepClock()
    root, key = create(tmp_path, clock=clock)
    run_once(root, key, Plan(), Env(), clock)
    with InvestigationMemory.open(root, key, writable=False) as mem:
        ver = [r["payload"] for r in mem.view.records if r["kind"] == "verification_recorded"]
        assert ver == [
            {
                "result": "passed",
                "checks": [{"check": "W_INVARIANTS", "passed": True}],
                "content_digest": mem.view.content_digest(),
            }
        ]


@pytest.mark.negative
def test_w8_conflict_claim_without_its_question_is_corrupt(tmp_path: Path) -> None:
    from controller_support import claim_and_set, lookup_evidence

    from citerift.investigation import ids

    root, key, clock = _until(tmp_path, "LOOKUP")
    k = _key(root, key, clock, "DETECT")
    evs = lookup_evidence()
    c, evidence_set = claim_and_set("IDENTITY_CONFLICT", [e["evidence_id"] for e in evs])
    decision = {
        "decision_id": ids.decision_id(c["claim_id"], "ROUTE_NEEDS_RESOLUTION"),
        "claim_id": c["claim_id"],
        "disposition": "ROUTE_NEEDS_RESOLUTION",
    }
    out = {"claims": [c["claim_id"]]}
    _forge(
        root,
        key,
        clock,
        [
            ("blob", out, None, None),
            ("blob", evidence_set, None, None),
            ("step_started", {"step_key": k}, "DETECT", 1),
            *_batched(evs, "DETECT", 1),
            *_candidates([{"claim": c, "decision": decision, "question": None}], "DETECT", 1),
            ("step_succeeded", {"step_key": k, "outputs": [digest(out)], "root": None}, "DETECT", 1),
        ],
    )
    _assert_corrupt(root, key, clock, "W-8")


@pytest.mark.negative
def test_corrupt_journal_with_a_torn_tail_is_not_repaired(tmp_path: Path) -> None:
    """D-044 order kept by the controller: a workflow-corrupt journal is checked read-only before any writable open."""
    root, key, clock = _until(tmp_path, "ACQUIRE")
    _forge(root, key, clock, [("step_started", {"step_key": "8" * 64}, "NORMALIZE", 1)])
    with open(root / key / "journal.jsonl", "ab") as fh:
        fh.write(b'{"v":2,"seq')  # an interrupted append
        os.fsync(fh.fileno())
    _assert_corrupt(root, key, clock, "W-3")
    assert not [p for p in (root / key).iterdir() if ".torn-" in p.name]


@pytest.mark.negative
def test_controller_construction_refusals(tmp_path: Path) -> None:
    from citerift.investigation.controller import MonotoneClock
    from citerift.investigation.errors import InvestigationMemoryError

    clock = StepClock()
    root, key = create(tmp_path, clock=clock)
    mono = MonotoneClock(clock)
    with InvestigationMemory.open(root, key, writable=False, clock=mono) as ro:
        with pytest.raises(InvestigationMemoryError) as exc:
            WorkflowController(ro, Plan().adapters(), Env(), mono)
        assert exc.value.code == "READ_ONLY"
    with InvestigationMemory.open(root, key, clock=clock) as mem:
        with pytest.raises(InvestigationMemoryError) as exc:
            WorkflowController(mem, Plan().adapters(), Env(), mono)
        assert exc.value.code == "CLOCK_NOT_SHARED"
    with InvestigationMemory.open(root, key, clock=mono) as mem:
        adapters = Plan().adapters()
        del adapters["VERIFY"]
        with pytest.raises(InvestigationMemoryError) as exc:
            WorkflowController(mem, adapters, Env(), mono)
        assert exc.value.code == "ADAPTER_MISSING"


def test_steps_constant_is_the_fixed_plan() -> None:
    assert STEPS == ("VALIDATE", "ACQUIRE", "EXTRACT", "NORMALIZE", "LOOKUP", "DETECT", "ASSEMBLE", "VERIFY")
    assert workflow.PLAN_VERSION == "plan-1" and (workflow.A_MAX, workflow.F_MAX) == (3, 6)
