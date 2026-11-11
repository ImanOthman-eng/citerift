"""Step 7: adversarial inputs to the controller; it must fail closed (owner Step 7 items 9 and 21).

Adapter exceptions, malformed and impossible results, a result that tries to change what it was given, duplicate
and concurrent invocation, corrupt and busy Memory. SYNTHETIC fake adapters (``controller_support``).
"""

from __future__ import annotations

import copy
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from controller_support import (
    BUNDLE,
    EXTRACTION,
    Env,
    Plan,
    Session,
    StepClock,
    create,
    digest,
    env_for,
    journal,
    ok_result,
    raw_records,
    run_once,
)
from memory_support import root_object

from citerift.investigation import ids, workflow
from citerift.investigation.adapters import ContentRecord, Deferred, Failed, StepRequest, StepResult, Succeeded
from citerift.investigation.controller import ADAPTER_INCONSISTENT, DEFECT_CODE, StorageExhausted, run_investigation
from citerift.investigation.fold import STEPS

pytestmark = pytest.mark.negative


def _failures(root: Path, key: str) -> list[tuple[str, str, str | None]]:
    return [
        (r["step"], r["payload"]["code"], r["payload"]["reason"])
        for r in journal(root, key)
        if r["kind"] == "step_failed"
    ]


def _run(tmp_path: Path, script: dict[tuple[str, int], Any], live: bool = False) -> tuple[Path, str, StepClock, Any]:
    clock = StepClock()
    root, key = create(tmp_path, live=live, clock=clock)
    st = run_once(root, key, Plan(script), env_for(live), clock)
    return root, key, clock, st


# Adapter exceptions ------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("step", STEPS)
def test_adapter_exception_fails_closed(tmp_path: Path, step: str) -> None:
    """D-049: an exception ends the attempt at once with the terminal ADAPTER_INCONSISTENT in every step; it is never
    left open for W-6 and never retried."""
    root, key, clock, st = _run(tmp_path, {(step, 1): "raise"})
    assert st.lifecycle == "FAILED"
    assert DEFECT_CODE[step] == (ADAPTER_INCONSISTENT, None)
    assert _failures(root, key) == [(step, ADAPTER_INCONSISTENT, None)]
    recs = [r for r in journal(root, key) if r["step"] == step]
    assert [r["kind"] for r in recs if r["kind"] in ("step_started", "step_interrupted")] == ["step_started"]
    assert [r["payload"]["retryable"] for r in recs if r["kind"] == "step_failed"] == [False]
    plan = Plan()
    assert run_once(root, key, plan, env_for(False), clock).lifecycle == "FAILED"
    assert plan.calls == []


def test_controller_stays_usable_after_a_recorded_defect(tmp_path: Path) -> None:
    """D-049: a defect is recorded, so the controller is not left broken; the investigation is terminal."""
    clock = StepClock()
    root, key = create(tmp_path, clock=clock)
    with Session(root, key, Plan({("VALIDATE", 1): "raise"}), Env(), clock) as ctl:
        ctl.step()
        assert ctl.state().lifecycle == "FAILED"
        assert ctl.step().action == "terminal"
        assert ctl.check_stale() is None
    assert _failures(root, key) == [("VALIDATE", ADAPTER_INCONSISTENT, None)]


def test_base_exception_in_an_adapter_leaves_the_attempt_open(tmp_path: Path) -> None:
    class Kill(BaseException):
        pass

    def kill(req: StepRequest) -> StepResult:
        raise Kill

    clock = StepClock()
    root, key = create(tmp_path, clock=clock)
    with pytest.raises(Kill):
        run_once(root, key, Plan({("NORMALIZE", 1): kill}), Env(), clock)
    assert journal(root, key)[-1]["kind"] == "step_started"
    assert run_once(root, key, Plan(), Env(), clock).lifecycle == "COMPLETED"


# Malformed and impossible results ----------------------------------------------------------------------------------


def _with(step: str, change: Any) -> Any:
    def adapter(req: StepRequest) -> StepResult:
        return change(ok_result(req, (("NOT_FOUND_IN_CHECKED_SOURCES", "c"),)))  # type: ignore[no-any-return]

    return adapter


BAD: list[Any] = [
    pytest.param("NORMALIZE", lambda r: None, "ADAPTER_INCONSISTENT", id="none-instead-of-result"),
    pytest.param("NORMALIZE", lambda r: {"ok": True}, "ADAPTER_INCONSISTENT", id="dict-instead-of-result"),
    pytest.param(
        "NORMALIZE", lambda r: Succeeded(records=list(r.records)), "ADAPTER_INCONSISTENT", id="records-not-a-tuple"
    ),  # type: ignore[arg-type]
    pytest.param(
        "NORMALIZE",
        lambda r: Succeeded(records=(ContentRecord("claim_recorded", {}),)),
        "ADAPTER_INCONSISTENT",
        id="kind-of-another-step",
    ),
    pytest.param(
        "DETECT",
        lambda r: Succeeded(records=(*r.records, ContentRecord("question_opened", {}))),
        "ADAPTER_INCONSISTENT",
        id="detect-supplies-its-own-question",
    ),
    pytest.param(
        "NORMALIZE",
        lambda r: Succeeded(records=(ContentRecord("evidence_recorded", []),)),
        "ADAPTER_INCONSISTENT",
        id="payload-not-an-object",
    ),  # type: ignore[arg-type]
    pytest.param(
        "NORMALIZE",
        lambda r: Succeeded(records=r.records, blobs=(float("nan"),), outputs=r.outputs),
        "ADAPTER_INCONSISTENT",
        id="blob-not-canonical",
    ),
    pytest.param(
        "NORMALIZE",
        lambda r: Succeeded(records=r.records, outputs=("a" * 64,)),
        "ADAPTER_INCONSISTENT",
        id="output-not-published",
    ),
    pytest.param(
        "NORMALIZE",
        lambda r: Succeeded(records=r.records, outputs=("../x",)),
        "ADAPTER_INCONSISTENT",
        id="output-not-a-digest",
    ),
    pytest.param(
        "NORMALIZE",
        lambda r: Succeeded(records=r.records, blobs=r.blobs, outputs=r.outputs, root=root_object()),
        "ADAPTER_INCONSISTENT",
        id="root-outside-acquire",
    ),
    pytest.param(
        "ACQUIRE",
        lambda r: Succeeded(records=r.records, blobs=r.blobs, outputs=r.outputs),
        "ADAPTER_INCONSISTENT",
        id="acquire-without-root",
    ),
    pytest.param(
        "ACQUIRE",
        lambda r: Succeeded(records=r.records, blobs=r.blobs, outputs=r.outputs, root=root_object(capture="f" * 64)),
        "ROOT_IDENTITY_MISMATCH",
        id="acquire-root-of-another-capture",
    ),
    pytest.param(
        "NORMALIZE",
        lambda r: Succeeded(
            records=tuple(ContentRecord(c.kind, {**c.payload, "evidence_id": "b" * 64}) for c in r.records),
            blobs=r.blobs,
            outputs=r.outputs,
        ),
        "ADAPTER_INCONSISTENT",
        id="evidence-id-not-derived",
    ),
    pytest.param(
        "NORMALIZE",
        lambda r: Succeeded(
            records=(ContentRecord("evidence_recorded", {**r.records[1].payload}),), blobs=r.blobs, outputs=r.outputs
        ),
        "ADAPTER_INCONSISTENT",
        id="dangling-evidence-reference",
    ),
    pytest.param(
        "ASSEMBLE",
        lambda r: Succeeded(blobs=r.blobs, outputs=r.outputs),
        "ADAPTER_INCONSISTENT",
        id="assemble-without-report",
    ),
    pytest.param(
        "VERIFY",
        lambda r: Succeeded(
            records=(
                ContentRecord(
                    "verification_recorded",
                    {"result": "failed", "checks": [{"check": "X", "passed": False}], "content_digest": None},
                ),
            )
        ),
        "ADAPTER_INCONSISTENT",
        id="verify-succeeds-with-failed-verification",
    ),
    pytest.param(
        "VERIFY",
        lambda r: Succeeded(
            records=(
                ContentRecord(
                    "verification_recorded",
                    {"result": "passed", "checks": [{"check": "X", "passed": True}], "content_digest": "c" * 64},
                ),
            )
        ),
        "ADAPTER_INCONSISTENT",
        id="verify-of-another-content-digest",
    ),
    pytest.param("NORMALIZE", lambda r: Failed("HTTP_TIMEOUT"), "ADAPTER_INCONSISTENT", id="code-not-allowed-for-step"),
    pytest.param("NORMALIZE", lambda r: Failed("lower case"), "ADAPTER_INCONSISTENT", id="code-malformed"),
    pytest.param(
        "NORMALIZE",
        lambda r: Failed("NORMALIZE_INVALID", not_before=datetime(2030, 1, 1).astimezone()),
        "ADAPTER_INCONSISTENT",
        id="not-before-outside-acquire",
    ),
    pytest.param(
        "DETECT",
        lambda r: Deferred(datetime(2030, 1, 1).astimezone()),
        "ADAPTER_INCONSISTENT",
        id="deferral-outside-acquire",
    ),
]


@pytest.mark.parametrize(("step", "change", "code"), BAD)
def test_malformed_result_is_refused_and_recorded_as_a_defect(
    tmp_path: Path, step: str, change: Any, code: str
) -> None:
    root, key, _, st = _run(tmp_path, {(step, 1): _with(step, change)})
    assert st.lifecycle == "FAILED"
    fails = _failures(root, key)
    assert [f[:2] for f in fails] == [(step, code)]
    # Nothing of the refused attempt is committed.
    recs = journal(root, key)
    assert not any(r["kind"] == "step_succeeded" and r["step"] == step for r in recs)


def test_live_acquire_root_of_another_revision_is_refused(tmp_path: Path) -> None:
    def other(req: StepRequest) -> StepResult:
        r = ok_result(req, ())
        assert isinstance(r, Succeeded)
        return Succeeded(records=r.records, blobs=r.blobs, outputs=r.outputs, root=root_object(revision=1))

    root, key, _, st = _run(tmp_path, {("ACQUIRE", 1): other}, live=True)
    assert st.lifecycle == "FAILED" and _failures(root, key) == [("ACQUIRE", "ROOT_IDENTITY_MISMATCH", None)]
    assert all(r["root_id"] is None for r in journal(root, key))


@pytest.mark.parametrize(
    "change",
    [
        pytest.param(lambda r: None, id="none"),
        pytest.param(lambda r: Failed("NOT_AN_EXTRACT_CODE"), id="code-not-allowed"),
        pytest.param(lambda r: Succeeded(records=(ContentRecord("claim_recorded", {}),)), id="wrong-kind"),
    ],
)
def test_malformed_extract_result_is_terminal_adapter_inconsistent(tmp_path: Path, change: Any) -> None:
    """D-049: EXTRACT had no defect code before (the attempt was left open); now it ends terminally too."""
    root, key, _, st = _run(tmp_path, {("EXTRACT", 1): _with("EXTRACT", change)})
    assert st.lifecycle == "FAILED"
    assert _failures(root, key) == [("EXTRACT", ADAPTER_INCONSISTENT, None)]
    assert journal(root, key)[-1]["kind"] == "step_failed"


def test_naive_datetime_is_refused(tmp_path: Path) -> None:
    root, key, _, st = _run(tmp_path, {("ACQUIRE", 1): Deferred(datetime(2030, 1, 1))}, live=True)
    assert st.lifecycle == "FAILED" and _failures(root, key)[0][1] == "ADAPTER_INCONSISTENT"


def test_adapter_cannot_change_what_it_was_given(tmp_path: Path) -> None:
    def vandal(req: StepRequest) -> StepResult:
        result = ok_result(req, (("NOT_FOUND_IN_CHECKED_SOURCES", "cand"),))
        req.request["mode"] = "live_capture"  # type: ignore[index]
        for rec in req.committed:
            rec["payload"].clear()  # type: ignore[attr-defined]
        if req.root is not None:
            req.root["root_id"] = "d" * 64  # type: ignore[index]
        return result

    clock = StepClock()
    root, key = create(tmp_path, clock=clock)
    st = run_once(root, key, Plan({(s, 1): vandal for s in STEPS}), Env(), clock)
    assert st.lifecycle == "COMPLETED"
    ref = tmp_path / "ref"
    ref.mkdir()
    clock2 = StepClock()
    root2, key2 = create(ref, clock=clock2)
    run_once(root2, key2, Plan(), Env(), clock2)
    strip = [{k: v for k, v in r.items() if k not in ("prev", "digest")} for r in journal(root, key)[1:]]
    assert strip == [{k: v for k, v in r.items() if k not in ("prev", "digest")} for r in journal(root2, key2)[1:]]


def test_idempotent_blobs_and_repeated_outputs(tmp_path: Path) -> None:
    """A result that repeats an output or a committed blob is accepted once (S-8.2, S-9.5)."""

    def repeat(req: StepRequest) -> StepResult:
        r = ok_result(req, ())
        assert isinstance(r, Succeeded)
        return Succeeded(records=r.records, blobs=(*r.blobs, EXTRACTION, BUNDLE), outputs=(*r.outputs, *r.outputs))

    clock = StepClock()
    root, key = create(tmp_path, clock=clock)
    run_once(root, key, Plan({("LOOKUP", 1): repeat}), Env(), clock)
    end = next(r for r in journal(root, key) if r["kind"] == "step_succeeded" and r["step"] == "LOOKUP")
    assert len(end["payload"]["outputs"]) == len(set(end["payload"]["outputs"])) == 2


# Duplicate and concurrent invocation, corrupt and busy Memory -------------------------------------------------------


def test_second_invocation_while_running_is_busy_and_writes_nothing(tmp_path: Path) -> None:
    clock = StepClock()
    root, key = create(tmp_path, clock=clock)
    seen: list[Any] = []

    def nested(req: StepRequest) -> StepResult:
        seen.append(run_investigation(root, key, Plan().adapters(), Env(), clock=clock))
        return ok_result(req, ())

    st = run_once(root, key, Plan({("VALIDATE", 1): nested}), Env(), clock)
    assert st.lifecycle == "COMPLETED"
    assert [s.status for s in seen] == ["INVESTIGATION_BUSY"]
    assert sum(1 for r in journal(root, key) if r["kind"] == "step_started") == len(STEPS)


@pytest.mark.parametrize("where", ["record", "blob"])
def test_corrupt_memory_is_reported_and_not_changed(tmp_path: Path, where: str) -> None:
    clock = StepClock()
    root, key = create(tmp_path, clock=clock)
    assert run_once(root, key, Plan({("EXTRACT", 1): "raise"}), Env(), clock).lifecycle == "FAILED"
    inv = root / key
    if where == "record":
        data = bytearray((inv / "journal.jsonl").read_bytes())
        data[100] ^= 0x01
        (inv / "journal.jsonl").write_bytes(bytes(data))
    else:
        blob = inv / "blobs" / digest(BUNDLE)
        blob.chmod(0o600)
        blob.write_bytes(blob.read_bytes() + b" ")
    before = {p: p.read_bytes() for p in inv.rglob("*") if p.is_file() and p.name != "lock"}
    plan = Plan()
    res = run_investigation(root, key, plan.adapters(), Env(), clock=clock)
    assert res.status == "CORRUPT" and plan.calls == []
    assert {p: p.read_bytes() for p in inv.rglob("*") if p.is_file() and p.name != "lock"} == before


def test_stale_investigation_is_terminal_for_every_later_run(tmp_path: Path) -> None:
    clock = StepClock()
    root, key = create(tmp_path, clock=clock)
    with Session(root, key, Plan(), Env(), clock) as ctl:  # stop after NORMALIZE, before LOOKUP starts
        while ctl.view.step_state("NORMALIZE") != "succeeded":
            ctl.step()
    env = Env()
    env.values["stage04"]["engine_version"] = "0.2.0"
    assert run_once(root, key, Plan(), env, clock).lifecycle == "STALE"
    before = journal(root, key)
    for e in (Env(), env):
        plan = Plan()
        res = run_investigation(root, key, plan.adapters(), e, clock=clock)
        assert res.status == "STALE" and plan.calls == [] and journal(root, key) == before
        assert res.explanation is not None and res.explanation["terminated_by"]["kind"] == "stale_detected"


def test_explanations_say_why(tmp_path: Path) -> None:
    clock = StepClock()
    root, key = create(tmp_path, live=True, clock=clock)
    nb = clock.t + timedelta(hours=1)
    res = run_investigation(root, key, Plan({("ACQUIRE", 1): Deferred(nb)}).adapters(), env_for(True), clock=clock)
    assert res.status == "BLOCKED" and res.explanation is not None
    assert res.explanation["next"]["action"] == "wait" and res.explanation["next"]["not_before"] == nb.isoformat()
    res = run_investigation(
        root,
        key,
        Plan({("ACQUIRE", 2): Failed("PAGE_MISSING", detail="SYNTHETIC")}).adapters(),
        env_for(True),
        clock=StepClock(nb),
    )
    assert res.status == "FAILED" and res.explanation is not None
    assert res.explanation["terminated_by"] == {
        "seq": res.explanation["terminated_by"]["seq"],
        "kind": "step_failed",
        "step": "ACQUIRE",
        "code": "PAGE_MISSING",
        "reason": None,
        "detail": "SYNTHETIC",
    }


def test_copy_of_request_is_independent(tmp_path: Path) -> None:
    clock = StepClock()
    root, key = create(tmp_path, clock=clock)
    with Session(root, key, Plan(), Env(), clock) as ctl:
        req = ctl._request("VALIDATE", 1, "e" * 64)
        snapshot = copy.deepcopy(ctl.view.created)
        req.request["config"]["plan_version"] = "x"  # type: ignore[index]
        assert ctl.view.created == snapshot


# Size limits are storage failures, not adapter defects (Step 7 resource-bound review) --------------------------------


@pytest.mark.parametrize("step", ["NORMALIZE", "DETECT"])
def test_record_over_the_size_limit_fails_the_step_with_storage_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, step: str
) -> None:
    from citerift.investigation import memory as memory_module

    def big(req: StepRequest) -> StepResult:
        r = ok_result(req, (("NOT_FOUND_IN_CHECKED_SOURCES", "cand"),))
        assert isinstance(r, Succeeded)
        first = r.records[0]
        pointer = "/" + "x" * 4095  # the longest JSON pointer the schema allows
        payload = {**first.payload, "pointer": pointer}
        monkeypatch.setattr(memory_module, "MAX_RECORD_BYTES", 4000)  # smaller than this record, larger than the rest
        return Succeeded(records=(ContentRecord(first.kind, payload), *r.records[1:]), blobs=r.blobs, outputs=r.outputs)

    root, key, _, st = _run(tmp_path, {(step, 1): big})
    assert st.lifecycle == "FAILED"
    assert _failures(root, key) == [(step, "STORAGE_ERROR", "RECORD_TOO_LARGE")]


def test_blob_over_the_size_limit_fails_the_step_with_storage_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from citerift.investigation import blobs as blobs_module

    def big(req: StepRequest) -> StepResult:
        r = ok_result(req, ())
        assert isinstance(r, Succeeded)
        monkeypatch.setattr(blobs_module, "MAX_BLOB_BYTES", 10)
        return r

    root, key, _, st = _run(tmp_path, {("LOOKUP", 1): big})
    assert st.lifecycle == "FAILED"
    assert _failures(root, key) == [("LOOKUP", "STORAGE_ERROR", "BLOB_TOO_LARGE")]


def _fill_journal(room: int, monkeypatch: pytest.MonkeyPatch, where: list[Path]) -> Any:
    """A NORMALIZE adapter that leaves ``room`` bytes in the journal and then returns a 4.7 kB evidence record."""
    from citerift.investigation import memory as memory_module

    def full(req: StepRequest) -> StepResult:
        r = ok_result(req, (("NOT_FOUND_IN_CHECKED_SOURCES", "cand"),))
        assert isinstance(r, Succeeded)
        monkeypatch.setattr(memory_module, "MAX_JOURNAL_BYTES", where[0].stat().st_size + room)
        pointer = "/" + "x" * 4095
        first = r.records[0]
        payload = {
            **first.payload,
            "pointer": pointer,
            "evidence_id": ids.evidence_id(first.payload["observation"], pointer, first.payload["kind"]),
        }
        return Succeeded(records=(ContentRecord(first.kind, payload), *r.records[1:]), blobs=r.blobs, outputs=r.outputs)

    return full


def test_journal_limit_with_room_for_the_failure_fails_the_step_with_storage_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = StepClock()
    root, key = create(tmp_path, clock=clock)
    st = run_once(
        root,
        key,
        Plan({("NORMALIZE", 1): _fill_journal(2000, monkeypatch, [root / key / "journal.jsonl"])}),
        Env(),
        clock,
    )
    assert st.lifecycle == "FAILED"
    assert _failures(root, key) == [("NORMALIZE", "STORAGE_ERROR", "JOURNAL_TOO_LARGE")]


def test_journal_limit_without_room_for_the_failure_stops_and_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The record that would close the attempt is refused too: StorageExhausted, the attempt stays open, the journal
    is unchanged from the refusal on, a later run under the same limit stops at recovery, and once the limit allows it
    the resume closes the attempt (W-6) and the investigation finishes."""
    from citerift.investigation import memory as memory_module

    clock = StepClock()
    root, key = create(tmp_path, clock=clock)
    path = root / key / "journal.jsonl"
    with pytest.raises(StorageExhausted) as info:
        run_once(root, key, Plan({("NORMALIZE", 1): _fill_journal(300, monkeypatch, [path])}), Env(), clock)
    assert (info.value.kind, info.value.step, info.value.limit) == ("step_failed", "NORMALIZE", "JOURNAL_TOO_LARGE")
    before = raw_records(root, key)
    assert (before[-1]["kind"], before[-1]["step"], before[-1]["attempt"]) == ("step_started", "NORMALIZE", 1)
    with pytest.raises(StorageExhausted) as again:
        run_once(root, key, Plan(), Env(), clock)
    assert again.value.kind == "step_interrupted"
    assert raw_records(root, key) == before
    monkeypatch.setattr(memory_module, "MAX_JOURNAL_BYTES", 512 * 1024 * 1024)
    st = run_once(root, key, Plan(), Env(), clock)
    after = journal(root, key)
    assert after[: len(before)] == before
    assert (after[len(before)]["kind"], after[len(before)]["attempt"]) == ("step_interrupted", 1)
    assert st.lifecycle == "COMPLETED"


# Step 7 review findings F1 to F4 (fail-first evidence: STEP7_REVIEW.md) -------------------------------------------


@pytest.mark.parametrize("step", ["ACQUIRE", "NORMALIZE", "DETECT"])
def test_non_canonical_content_is_a_defect_of_the_step_not_a_crash(tmp_path: Path, step: str) -> None:
    """F1: a float in a content payload is refused by canonical JSON; the step ends with its defect code at once."""

    def floaty(req: StepRequest) -> StepResult:
        r = ok_result(req, (("NOT_FOUND_IN_CHECKED_SOURCES", "cand"),))
        assert isinstance(r, Succeeded)
        first = r.records[0]
        bad = ContentRecord(first.kind, {**first.payload, "extra_float": 1.5})
        return Succeeded(records=(bad, *r.records[1:]), blobs=r.blobs, outputs=r.outputs, root=r.root)

    root, key, _, st = _run(tmp_path, {(step, 1): floaty})
    assert st.lifecycle == "FAILED"
    assert _failures(root, key) == [(step, *DEFECT_CODE[step])]


@pytest.mark.parametrize(
    "instant",
    [datetime(5, 1, 1, tzinfo=UTC), datetime.min.replace(tzinfo=timezone(timedelta(hours=1)))],
    ids=["year-5", "min-plus-1h"],
)
@pytest.mark.parametrize("kind", ["deferred", "failed"])
def test_not_before_outside_the_schema_range_is_a_defect(tmp_path: Path, instant: datetime, kind: str) -> None:
    """F1: an instant the record schema cannot hold (or that overflows in UTC) is refused before any append."""
    result = Deferred(instant) if kind == "deferred" else Failed("HTTP_RATE_LIMITED", not_before=instant)
    root, key, _, st = _run(tmp_path, {("ACQUIRE", 1): result}, live=True)
    assert st.lifecycle == "FAILED"
    assert _failures(root, key) == [("ACQUIRE", *DEFECT_CODE["ACQUIRE"])]


def test_disk_full_while_publishing_a_blob_is_storage_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """F2, SPEC 10.2: the blob is not committed and the attempt ends STORAGE_ERROR (not retryable)."""
    from citerift.investigation import blobs as blobs_module
    from citerift.investigation.errors import StorageError

    real = blobs_module.BlobStore.put

    def full(self: Any, data: bytes) -> str:
        if b"normalized" in data:
            raise StorageError("blob: No space left on device")
        return real(self, data)

    monkeypatch.setattr(blobs_module.BlobStore, "put", full)
    root, key, _, st = _run(tmp_path, {})
    assert st.lifecycle == "FAILED"
    assert _failures(root, key) == [("NORMALIZE", "STORAGE_ERROR", None)]
    assert [r["payload"]["retryable"] for r in journal(root, key) if r["kind"] == "step_failed"] == [False]


def test_adapter_output_equal_to_the_step_manifest_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """F3: the manifest is the controller's last output; an adapter cannot place it elsewhere."""
    fixed = {"manifest": "forged"}
    monkeypatch.setattr(workflow, "manifest", lambda *a, **k: dict(fixed))

    def sneaky(req: StepRequest) -> StepResult:
        r = ok_result(req, ())
        assert isinstance(r, Succeeded)
        return Succeeded(records=r.records, blobs=(*r.blobs, fixed), outputs=(digest(fixed), *r.outputs))

    root, key, _, st = _run(tmp_path, {("NORMALIZE", 1): sneaky})
    assert st.lifecycle == "FAILED"
    assert _failures(root, key) == [("NORMALIZE", *DEFECT_CODE["NORMALIZE"])]


def test_workflow_corruption_found_while_running_is_reported_corrupt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F3: ``run_investigation`` reports CORRUPT (not a raw exception) when the run itself finds a broken journal."""
    from citerift.investigation import controller as controller_module

    clock = StepClock()
    root, key = create(tmp_path, clock=clock)
    before = raw_records(root, key)

    def broken(self: Any) -> None:
        raise workflow.WorkflowCorrupt(workflow.WorkflowRefused("S-9.3", "VALIDATE has no valid step manifest"))

    monkeypatch.setattr(controller_module.WorkflowController, "check_stale", broken)
    res = run_investigation(root, key, Plan().adapters(), Env(), clock=clock)
    assert res.status == "CORRUPT" and "S-9.3" in res.detail
    assert raw_records(root, key) == before


@pytest.mark.parametrize(
    "classes",
    [("RETRACTED_WORK_CITED", "NOT_FOUND_IN_CHECKED_SOURCES"), ("IDENTITY_CONFLICT", "LOOKUP_UNAVAILABLE")],
    ids=["finding-and-not-found", "conflict-and-unavailable"],
)
def test_two_claims_for_one_candidate_are_refused(tmp_path: Path, classes: tuple[str, str]) -> None:
    """F4, SPEC 7.1: one candidate gets exactly one claim class."""
    root, key, _, st = _run(tmp_path, {("DETECT", 1): lambda req: ok_result(req, tuple((c, "cand") for c in classes))})
    assert st.lifecycle == "FAILED"
    assert _failures(root, key) == [("DETECT", "ADAPTER_INCONSISTENT", None)]
    assert not [r for r in journal(root, key) if r["kind"] == "step_succeeded" and r["step"] == "DETECT"]
