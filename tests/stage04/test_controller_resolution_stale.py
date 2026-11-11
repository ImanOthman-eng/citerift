"""Step 7: needs-resolution routing, staleness and deterministic keys (owner Step 7 items 14, 15 and 16).

SPEC 7.6, 7.7, 9.4, 9.6, 10.3; MM 3.3, 10. SYNTHETIC fake adapters (``controller_support``).
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from controller_support import (
    Env,
    Plan,
    Session,
    StepClock,
    append_content,
    create,
    env_for,
    journal,
    run_once,
)

from citerift.investigation import ids, sets, workflow
from citerift.investigation.adapters import StepRequest, StepResult
from citerift.investigation.errors import InvestigationMemoryError
from citerift.investigation.fold import STEPS, Folder
from citerift.investigation.memory import InvestigationMemory

pytestmark = pytest.mark.integration


class Stop(BaseException):
    """Ends a process in the middle of a step without any record (like a kill), for the stale tests."""


def _stop(req: StepRequest) -> StepResult:
    raise Stop


def _payloads(root: Path, key: str, kind: str) -> list[dict[str, Any]]:
    return [r["payload"] for r in journal(root, key) if r["kind"] == kind]


def _fold(root: Path, key: str) -> Folder:
    f = Folder(None)
    for r in journal(root, key):
        f.apply(r)
    return f


# Needs-resolution (W-8, S-7.6) --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("cls", "qkind"),
    [("IDENTITY_CONFLICT", "identity_conflict"), ("CONTRADICTION_IN_SOURCES", "source_conflict")],
)
def test_conflict_routes_to_needs_resolution(tmp_path: Path, cls: str, qkind: str) -> None:
    clock = StepClock()
    root, key = create(tmp_path, clock=clock)
    st = run_once(root, key, Plan(classes=((cls, "c1"),)), Env(), clock)
    assert st.lifecycle == "NEEDS_RESOLUTION" and st.outcome == "partial" and st.next.action == "terminal"
    claims = _payloads(root, key, "claim_recorded")
    assert [c["class"] for c in claims] == [cls]
    cid = claims[0]["claim_id"]
    # The conflicting evidence is retained: every evidence id the claim names is committed.
    f = _fold(root, key)
    with InvestigationMemory.open(root, key, writable=False) as mem:
        named = sets.set_ids(json.loads(mem.blobs.get(claims[0]["evidence_set"])))
        committed = set(mem.view.committed.evidence)  # the id index is rebuilt from the journal and its batches
    assert named and named <= committed
    assert _payloads(root, key, "decision_recorded") == [
        {
            "decision_id": ids.decision_id(cid, "ROUTE_NEEDS_RESOLUTION"),
            "claim_id": cid,
            "disposition": "ROUTE_NEEDS_RESOLUTION",
        }
    ]
    assert _payloads(root, key, "question_opened") == [
        {"question_id": ids.question_id(cid, qkind), "claim_id": cid, "kind": qkind}
    ]
    assert f.open_questions() == [ids.question_id(cid, qkind)]
    # No positive or negative claim for that candidate (W-8).
    assert not [c for c in claims if c["class"] in workflow.POSITIVE | workflow.NEGATIVE]
    # NEEDS_RESOLUTION is terminal: a new run adds nothing and never reaches COMPLETED.
    before = journal(root, key)
    plan = Plan()
    st2 = run_once(root, key, plan, Env(), clock)
    assert st2.lifecycle == "NEEDS_RESOLUTION" and plan.calls == [] and journal(root, key) == before
    # Replay of the stored journal gives the same state.
    assert workflow.derive(_fold(root, key), clock()).lifecycle == "NEEDS_RESOLUTION"
    workflow.check_journal(_fold(root, key))


def test_conflict_and_finding_for_one_candidate_is_refused(tmp_path: Path) -> None:
    clock = StepClock()
    root, key = create(tmp_path, clock=clock)
    plan = Plan(classes=(("IDENTITY_CONFLICT", "c1"), ("RETRACTED_WORK_CITED", "c1")))
    st = run_once(root, key, plan, Env(), clock)
    assert st.lifecycle == "FAILED"
    fail = _payloads(root, key, "step_failed")[0]
    assert fail["code"] == "ADAPTER_INCONSISTENT" and "W-8" in fail["detail"]
    assert _fold(root, key).open_questions() == []  # the uncommitted question is not authoritative


def test_conflict_beside_a_finding_for_another_candidate_is_needs_resolution(tmp_path: Path) -> None:
    clock = StepClock()
    root, key = create(tmp_path, clock=clock)
    plan = Plan(classes=(("CONTRADICTION_IN_SOURCES", "c1"), ("RETRACTED_WORK_CITED", "c2")))
    assert run_once(root, key, plan, Env(), clock).lifecycle == "NEEDS_RESOLUTION"


def test_lookup_unavailable_completes_with_outcome_partial(tmp_path: Path) -> None:
    clock = StepClock()
    root, key = create(tmp_path, clock=clock)
    st = run_once(root, key, Plan(classes=(("LOOKUP_UNAVAILABLE", "c1"),)), Env(), clock)
    assert (st.lifecycle, st.outcome) == ("COMPLETED", "partial")


def test_unknown_claim_class_is_a_decision_table_gap(tmp_path: Path) -> None:
    clock = StepClock()
    root, key = create(tmp_path, clock=clock)

    def odd(req: StepRequest) -> StepResult:
        from controller_support import ok_result

        res = ok_result(req, (("NOT_FOUND_IN_CHECKED_SOURCES", "c"),))
        recs = tuple(
            type(r)(r.kind, {**r.payload, "class": "NOT_A_CLASS"}) if r.kind == "claim_recorded" else r
            for r in res.records  # type: ignore[union-attr]
        )
        return type(res)(records=recs, blobs=res.blobs, outputs=res.outputs)  # type: ignore[call-arg,union-attr]

    st = run_once(root, key, Plan({("DETECT", 1): odd}), Env(), clock)
    assert st.lifecycle == "FAILED" and _payloads(root, key, "step_failed")[0]["code"] == "DECISION_TABLE_GAP"


@pytest.mark.negative
@pytest.mark.parametrize("change", ["drop-question", "drop-decision", "wrong-disposition", "question-on-not-found"])
def test_guard_refuses_detect_content_that_breaks_w8(tmp_path: Path, change: str) -> None:
    """Forged DETECT content (not what the controller derives) is refused when the step would succeed."""
    clock = StepClock()
    root, key = create(tmp_path, clock=clock)
    cls = "NOT_FOUND_IN_CHECKED_SOURCES" if change == "question-on-not-found" else "IDENTITY_CONFLICT"
    with Session(root, key, Plan(classes=((cls, "c1"),)), Env(), clock) as ctl:
        while ctl.view.step_state("LOOKUP") != "succeeded":
            ctl.step()
        f = ctl.view
        from controller_support import ok_result

        digests = ctl.current_digests()
        k = workflow.step_key(f, "DETECT", digests)
        ctl._append("step_started", {"step_key": k}, "DETECT", 1)
        req = ctl._request("DETECT", 1, k)
        res = ok_result(req, ((cls, "c1"),))
        for blob in res.blobs:  # type: ignore[union-attr]
            ctl._mem.put_blob(blob)  # the evidence sets the claims name (D-047)
        from citerift.investigation.controller import _content

        content = _content("DETECT", res)  # type: ignore[arg-type]
        cid = next(p["claim_id"] for kk, p in content if kk == "claim_recorded")
        if change == "drop-question":
            content = [(kk, p) for kk, p in content if kk != "question_opened"]
        elif change == "drop-decision":
            content = [(kk, p) for kk, p in content if kk != "decision_recorded"]
        elif change == "wrong-disposition":
            content = [
                (kk, {**p, "disposition": "REPORT_FINDING", "decision_id": ids.decision_id(cid, "REPORT_FINDING")})
                if kk == "decision_recorded"
                else (kk, p)
                for kk, p in content
            ]
        else:
            q = ids.question_id(cid, "identity_conflict")
            content.append(("question_opened", {"question_id": q, "claim_id": cid, "kind": "identity_conflict"}))
        append_content(ctl, "DETECT", 1, content)
        man = ctl._mem.put_blob(workflow.manifest(ctl.view, "DETECT", k, digests))
        with pytest.raises(workflow.WorkflowRefused) as exc:
            ctl._append("step_succeeded", {"step_key": k, "outputs": [man], "root": None}, "DETECT", 1)
        assert exc.value.rule == "W-8"


# Staleness (SPEC 10.3, S-10.1) -------------------------------------------------------------------------------------


def _interrupted_at_detect(tmp_path: Path, live: bool = False) -> tuple[Path, str, StepClock]:
    clock = StepClock()
    root, key = create(tmp_path, live=live, clock=clock)
    with pytest.raises(Stop):
        run_once(root, key, Plan({("DETECT", 1): _stop}), env_for(live), clock)
    return root, key, clock


CHANGES: dict[str, tuple[str, Any]] = {
    # owner item 15 input -> (identity component that records it, mutation of the environment)
    "request identity": ("request_key", lambda e: e.values.__setitem__("request_key", {"capture_sha256": "0" * 64})),
    "root / capture digest": ("root", lambda e: setattr(e, "root_override", {"capture_sha256": "1" * 64})),
    "Stage 03 extractor": ("extraction", lambda e: e.values["extraction"].__setitem__("extractor", "SYNTHETIC-2")),
    "Stage 03 profile": ("extraction", lambda e: e.values["extraction"].__setitem__("profile", "2" * 64)),
    "Stage 03 config": ("extraction", lambda e: e.values["extraction"].__setitem__("normalizer", "n-2")),
    "Stage 02 index": ("index", lambda e: e.values["index"].__setitem__("index_sha256", "3" * 64)),
    "Stage 04 schema version": ("stage04", lambda e: e.values["stage04"].__setitem__("schema_version", "1.0.1")),
    "decision table version": ("stage04", lambda e: e.values["stage04"].__setitem__("table_version", "dt-2")),
    "effective config": ("config", lambda e: e.values["config"].__setitem__("extra", True)),
    "D-042 bound": ("config", lambda e: e.values["config"].__setitem__("t_acq_ms", 250_000)),
}


@pytest.mark.parametrize("what", sorted(CHANGES))
def test_changed_identity_is_stale_and_nothing_is_rerun(tmp_path: Path, what: str) -> None:
    name, mutate = CHANGES[what]
    root, key, clock = _interrupted_at_detect(tmp_path)
    env = Env()
    mutate(env)
    plan = Plan()
    st = run_once(root, key, plan, env, clock)
    assert st.lifecycle == "STALE" and plan.calls == []  # no committed output reused, nothing re-run in place
    recs = journal(root, key)
    assert [r["kind"] for r in recs[-2:]] == ["step_interrupted", "stale_detected"]  # W-6 first, then S-10.1
    p = recs[-1]["payload"]
    assert p["changed"] == [name]
    assert p["recorded"][name] != p["current"][name]
    # STALE is terminal.
    before = journal(root, key)
    assert run_once(root, key, Plan(), Env(), clock).lifecycle == "STALE" and journal(root, key) == before


@pytest.mark.parametrize("what", ["plan version", "retry budget", "deferral budget"])
def test_changed_controller_identity_is_stale(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, what: str) -> None:
    root, key, clock = _interrupted_at_detect(tmp_path)
    attr = {"plan version": ("PLAN_VERSION", "plan-2"), "retry budget": ("A_MAX", 4), "deferral budget": ("F_MAX", 7)}
    monkeypatch.setattr(workflow, *attr[what])
    plan = Plan()
    st = run_once(root, key, plan, Env(), clock)
    assert st.lifecycle == "STALE" and plan.calls == []
    assert journal(root, key)[-1]["payload"]["changed"] == ["stage04"]


def test_unchanged_identity_resumes_without_rerunning_committed_steps(tmp_path: Path) -> None:
    root, key, clock = _interrupted_at_detect(tmp_path)
    plan = Plan()
    st = run_once(root, key, plan, Env(), clock)
    assert st.lifecycle == "COMPLETED"
    assert plan.calls == [("DETECT", 2), ("ASSEMBLE", 1), ("VERIFY", 1)]


def test_identity_change_in_the_middle_of_a_run_stops_it(tmp_path: Path) -> None:
    clock = StepClock()
    root, key = create(tmp_path, clock=clock)
    env = Env()

    def changes_index(req: StepRequest) -> StepResult:
        from controller_support import ok_result

        env.values["index"]["index_sha256"] = "4" * 64  # the index is rebuilt while LOOKUP's output is committed
        return ok_result(req, ())

    plan = Plan({("NORMALIZE", 1): "ok", ("LOOKUP", 1): changes_index})
    st = run_once(root, key, plan, env, clock)
    assert st.lifecycle == "STALE" and ("DETECT", 1) not in plan.calls
    assert journal(root, key)[-1]["payload"]["changed"] == ["index"]


def test_identity_that_cannot_be_computed_is_a_failure_not_staleness(tmp_path: Path) -> None:
    root, key, clock = _interrupted_at_detect(tmp_path)
    env = Env()
    del env.values["index"]
    before = journal(root, key)
    with pytest.raises(InvestigationMemoryError) as exc:
        run_once(root, key, Plan(), env, clock)
    assert exc.value.code == "IDENTITY_UNAVAILABLE"
    after = journal(root, key)
    assert after[: len(before)] == before and [r["kind"] for r in after[len(before) :]] == ["step_interrupted"]


@pytest.mark.negative
def test_guard_refuses_an_inconsistent_stale_record(tmp_path: Path) -> None:
    root, key, clock = _interrupted_at_detect(tmp_path)
    with Session(root, key, Plan(), Env(), clock) as ctl:
        ctl.recover()
        f = ctl.view
        zero, one = "0" * 64, "1" * 64

        def rec(payload: dict[str, Any]) -> dict[str, Any]:
            return {"kind": "stale_detected", "step": None, "attempt": None, "payload": payload, "at": "x"}

        for payload in (
            {"changed": [], "recorded": {"config": zero}, "current": {"config": zero}},
            {"changed": ["config"], "recorded": {"config": zero}, "current": {"config": zero}},
            {"changed": ["index"], "recorded": {"config": zero}, "current": {"config": one}},
            {
                "changed": ["config"],
                "recorded": {"config": zero, "index": zero},
                "current": {"config": one, "index": one},
            },
        ):
            with pytest.raises(workflow.WorkflowRefused) as exc:
                workflow.guard(rec(payload), f, orphan=False)
            assert exc.value.rule == "T-STALE"
        good = {"changed": ["config"], "recorded": {"config": zero}, "current": {"config": one}}
        assert workflow.guard(rec(good), f, orphan=False) == "T-STALE"


# Deterministic keys and child ids (owner item 16) ------------------------------------------------------------------


def test_two_independent_runs_write_identical_journals(tmp_path: Path) -> None:
    out = []
    for name in ("a", "b"):
        base = tmp_path / name
        base.mkdir()
        clock = StepClock()
        root, key = create(base, clock=clock)
        run_once(
            root, key, Plan(classes=(("IDENTITY_CONFLICT", "c1"), ("NOT_FOUND_IN_CHECKED_SOURCES", "c2"))), Env(), clock
        )
        out.append([{k: v for k, v in r.items() if k not in ("prev", "digest")} for r in journal(root, key)])
    # The creation record names the memory root path, so the chain differs; every other field is identical.
    for a, b in zip(out[0][1:], out[1][1:], strict=True):
        assert a == b


def test_step_keys_ignore_titles_and_depend_on_inputs(tmp_path: Path) -> None:
    clock = StepClock()
    root, key = create(tmp_path, clock=clock)
    run_once(root, key, Plan(), Env(), clock)
    f = _fold(root, key)
    with Session(root, key, Plan(), Env(), clock) as ctl:
        digests = ctl.current_digests()
        # The bound root's display title is never passed to the environment, so it is in no identity or key.
        assert ctl.view.root is not None
        ctl.view.root["subject"]["display"]["title"] = "ANOTHER TITLE"
        assert ctl.current_digests() == digests
    recorded = {r["step"]: r["payload"]["step_key"] for r in f.records if r["kind"] == "step_succeeded"}
    assert {s: workflow.step_key(f, s, digests) for s in STEPS} == recorded
    # A dependency output changes the key.
    g = copy.deepcopy(f)
    end = next(r for r in g.records if r["kind"] == "step_succeeded" and r["step"] == "NORMALIZE")
    end["payload"]["outputs"] = ["5" * 64]
    assert workflow.step_key(g, "LOOKUP", digests) != recorded["LOOKUP"]
    assert workflow.step_key(g, "NORMALIZE", digests) == recorded["NORMALIZE"]  # its own outputs are not its input


def test_child_id_tags_are_distinct() -> None:
    x = "6" * 64
    values = {
        ids.evidence_id(x, "/a", "unit"),
        ids.claim_id(x, "IDENTITY_CONFLICT", "D-6", "dt-1", x),
        ids.decision_id(x, "ROUTE_NEEDS_RESOLUTION"),
        ids.question_id(x, "identity_conflict"),
        ids.identity_digest("config", x),
        ids.step_key("VALIDATE", "plan-1", [], {}, x),
    }
    assert len(values) == 6
    assert ids.claim_id(x, "C", "D-1", "dt-1", x) != ids.claim_id(x, "C", "D-1", "dt-1", "7" * 64)  # binds the set
