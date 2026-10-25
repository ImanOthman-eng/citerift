"""The twelve mandatory Orchestrator-Memory integration scenarios (Prompt 02, section 8).

Each test drives a real git sandbox through the orchestrator and asserts both
the permitted and the rejected behavior.
"""

from __future__ import annotations

import json

import pytest
from sandbox_repo import OWNER_REF, Sandbox, git

from citerift.governance.model import Actor, Status
from citerift.governance.orchestrator import GovernanceError, errors

pytestmark = [pytest.mark.integration]

VA = Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE
AC = Status.ACCEPTED_CLOSED
IP = Status.IN_PROGRESS


def test_01_valid_stage_authorization(sandbox: Sandbox) -> None:
    result = sandbox.go("00", Status.AUTHORIZED)
    assert result.allowed
    reg = sandbox.registry()
    stage = reg["stages"][0]
    assert stage["status"] == "AUTHORIZED"
    assert stage["authorization"]["owner_ref"] == OWNER_REF
    assert reg["history"][-1] | {"at": None} == {
        "seq": 1,
        "at": None,
        "stage": "00",
        "from": "NOT_STARTED",
        "to": "AUTHORIZED",
        "actor": "owner",
        "recorded_by": "engineering-agent",
        "reason": "sandbox AUTHORIZED",
        "owner_ref": OWNER_REF,
    }
    assert "AUTHORIZED" in (sandbox.root / "PROJECT_STATUS.md").read_text(encoding="utf-8")
    assert not errors(sandbox.orc().check())


@pytest.mark.negative
def test_01b_authorization_requires_owner_and_reference(sandbox: Sandbox) -> None:
    by_agent = sandbox.go("00", Status.AUTHORIZED, actor=Actor.ENGINEERING_AGENT)
    assert not by_agent.allowed
    assert "OWNER_DECISION_REQUIRED" in sandbox.codes(by_agent.findings)
    no_ref = sandbox.go("00", Status.AUTHORIZED, actor=Actor.OWNER, owner_ref=None)
    assert not no_ref.allowed
    assert "OWNER_REF_REQUIRED" in sandbox.codes(no_ref.findings)
    assert sandbox.registry()["stages"][0]["status"] == "NOT_STARTED"


def test_02_stage_with_all_tests_passing_is_verified_but_not_accepted(sandbox: Sandbox) -> None:
    rev = sandbox.drive_to_verified("00")
    orc = sandbox.orc()
    stage = orc.stage("00")
    assert stage["status"] == VA
    assert stage["verification"]["revision"] == rev
    assert stage["acceptance"] is None
    assert not errors(orc.check())
    # Verification does not unlock anything: the successor is untouched and still locked.
    assert orc.stage("02")["status"] == "NOT_STARTED"
    assert any("owner acceptance decision required" in a for a in orc.next_actions())
    assert not any(a.startswith("Stage 02") for a in orc.next_actions())


@pytest.mark.negative
@pytest.mark.parametrize(
    ("kwargs", "code"),
    [
        ({"omit": ("test-report.json",)}, "TEST_EVIDENCE_MISSING"),
        ({"report_overrides": {"suites": {"unit": {"passed": 3}}}}, "TEST_SUITE_MISSING"),
        ({"report_overrides": {"totals": {"passed": 0}}}, "TEST_EVIDENCE_EMPTY"),
    ],
)
def test_03_missing_tests_block_verification(sandbox: Sandbox, kwargs: dict[str, object], code: str) -> None:
    _prepare_implemented(sandbox)
    rev = sandbox.orc().stage("00")["implementation"]["revision"]
    sandbox.write_evidence("00", rev, **kwargs)  # type: ignore[arg-type]
    result = sandbox.go("00", VA, gates=sandbox.gates("00"), ci=sandbox.ci(rev))
    assert not result.allowed
    assert code in sandbox.codes(result.findings)
    assert sandbox.orc().stage("00")["status"] == "IMPLEMENTED_NOT_VERIFIED"


@pytest.mark.negative
@pytest.mark.parametrize(
    ("overrides", "code"),
    [
        ({"totals": {"passed": 70, "failed": 1}, "exit_status": 1}, "TESTS_FAILED"),
        ({"suites": {"unit": {"passed": 9, "failed": 1}}}, "TESTS_FAILED"),
        ({"revision": "0" * 40}, "TEST_EVIDENCE_WRONG_REVISION"),
        ({"dirty": True}, "TEST_EVIDENCE_DIRTY"),
        ({"format": "junit"}, "TEST_EVIDENCE_INVALID"),
    ],
)
def test_04_failed_or_untrustworthy_tests_block_verification(
    sandbox: Sandbox, overrides: dict[str, object], code: str
) -> None:
    _prepare_implemented(sandbox)
    rev = sandbox.orc().stage("00")["implementation"]["revision"]
    sandbox.write_evidence("00", rev, report_overrides=overrides)
    result = sandbox.go("00", VA, gates=sandbox.gates("00"), ci=sandbox.ci(rev))
    assert not result.allowed
    assert code in sandbox.codes(result.findings)


@pytest.mark.negative
@pytest.mark.parametrize(
    ("kwargs", "code"),
    [
        ({"handoff_sections": ["Stage and status", "Test evidence"]}, "HANDOFF_INCOMPLETE"),
        ({"omit": ("HANDOFF.md",)}, "EVIDENCE_MISSING"),
        ({"omit": ("RISK_ANALYSIS.md",)}, "EVIDENCE_MISSING"),
        ({"handoff_revision": "1234567"}, "HANDOFF_WRONG_REVISION"),
    ],
)
def test_05_incomplete_handoff_blocks_verification(sandbox: Sandbox, kwargs: dict[str, object], code: str) -> None:
    _prepare_implemented(sandbox)
    rev = sandbox.orc().stage("00")["implementation"]["revision"]
    sandbox.write_evidence("00", rev, **kwargs)  # type: ignore[arg-type]
    result = sandbox.go("00", VA, gates=sandbox.gates("00"), ci=sandbox.ci(rev))
    assert not result.allowed
    assert code in sandbox.codes(result.findings)


@pytest.mark.negative
def test_05b_trivial_artifact_and_gates_block_verification(sandbox: Sandbox) -> None:
    _prepare_implemented(sandbox)
    rev = sandbox.orc().stage("00")["implementation"]["revision"]
    sandbox.write_evidence("00", rev)
    sandbox.write("docs/verification/stage-00/SIMULATION_REPORT.md", "# TODO\n")
    gates = sandbox.gates("00")
    gates["00-K"]["result"] = "not_verified"
    del gates["00-L"]
    gates["00-M"]["evidence"] = ["docs/does-not-exist.md"]
    result = sandbox.go("00", VA, gates=gates, ci=sandbox.ci(rev, conclusion="failure"))
    codes = sandbox.codes(result.findings)
    assert not result.allowed
    assert {"EVIDENCE_TRIVIAL", "GATE_NOT_PASSED", "GATE_RESULT_MISSING", "GATE_EVIDENCE_MISSING"} <= codes
    assert "CI_NOT_SUCCESSFUL" in codes
    no_ci = sandbox.go("00", VA, gates=sandbox.gates("00"), ci=None)
    assert "CI_EVIDENCE_MISSING" in sandbox.codes(no_ci.findings)


@pytest.mark.negative
def test_06_missing_owner_acceptance(sandbox: Sandbox) -> None:
    sandbox.drive_to_verified("00")
    by_agent = sandbox.go("00", AC, actor=Actor.ENGINEERING_AGENT)
    assert not by_agent.allowed
    assert "OWNER_DECISION_REQUIRED" in sandbox.codes(by_agent.findings)
    no_ref = sandbox.go("00", AC, actor=Actor.OWNER, owner_ref=None)
    assert "OWNER_REF_REQUIRED" in sandbox.codes(no_ref.findings)
    # A verified stage pending acceptance does not unlock its successor.
    sandbox.drive_to_accepted("01")
    successor = sandbox.go("02", Status.AUTHORIZED)
    assert not successor.allowed
    assert "DEPENDENCY_NOT_ACCEPTED" in sandbox.codes(successor.findings)
    assert sandbox.orc().stage("00")["status"] == VA


@pytest.mark.negative
def test_06b_fabricated_acceptance_in_files_is_detected(sandbox: Sandbox) -> None:
    rev = sandbox.drive_to_verified("00")
    reg = sandbox.registry()
    stage = reg["stages"][0]
    stage["status"] = "ACCEPTED_CLOSED"
    stage["acceptance"] = {
        "owner_ref": OWNER_REF,
        "accepted_revision": rev,
        "recorded_at": "2026-11-02T00:00:00Z",
        "recorded_by": "engineering-agent",
        "method": "attested",
    }
    sandbox.save_registry(reg)
    codes = sandbox.codes(sandbox.orc().check())
    assert {"STATUS_HISTORY_CONFLICT", "ACCEPTANCE_UNTRACEABLE"} <= codes
    # Adding a history entry that claims the agent accepted it is also rejected.
    reg["history"].append(
        {
            "seq": len(reg["history"]) + 1,
            "at": "2026-11-02T00:00:00Z",
            "stage": "00",
            "from": "VERIFIED_AWAITING_OWNER_ACCEPTANCE",
            "to": "ACCEPTED_CLOSED",
            "actor": "engineering-agent",
            "recorded_by": "engineering-agent",
            "reason": "tests passed so I accepted it",
            "owner_ref": None,
        }
    )
    sandbox.save_registry(reg)
    codes = sandbox.codes(sandbox.orc().check())
    assert {"HISTORY_ACTOR", "HISTORY_OWNER_REF_MISSING"} <= codes


@pytest.mark.negative
def test_06c_acceptance_of_another_revision_is_detected(sandbox: Sandbox) -> None:
    sandbox.drive_to_accepted("00")
    assert "ACCEPTANCE_STALE" not in sandbox.codes(sandbox.orc().check())
    reg = sandbox.registry()
    acceptance = reg["stages"][0]["acceptance"]
    acceptance["accepted_revision"] = "0" * 40
    sandbox.save_registry(reg)
    assert "ACCEPTANCE_STALE" in sandbox.codes(sandbox.orc().check())
    # An acceptance recorded before the verification it claims to accept is also stale.
    acceptance["accepted_revision"] = reg["stages"][0]["verification"]["revision"]
    acceptance["recorded_at"] = "2000-01-01T00:00:00Z"
    sandbox.save_registry(reg)
    assert "ACCEPTANCE_STALE" in sandbox.codes(sandbox.orc().check())


@pytest.mark.negative
def test_07_unauthorized_next_stage_request(sandbox: Sandbox) -> None:
    jump = sandbox.go("02", IP, actor=Actor.ENGINEERING_AGENT)
    assert not jump.allowed
    assert "TRANSITION_INVALID" in sandbox.codes(jump.findings)
    self_authorized = sandbox.go("02", Status.AUTHORIZED, actor=Actor.ENGINEERING_AGENT)
    assert "OWNER_DECISION_REQUIRED" in sandbox.codes(self_authorized.findings)
    owner_but_deps_open = sandbox.go("02", Status.AUTHORIZED)
    assert "DEPENDENCY_NOT_ACCEPTED" in sandbox.codes(owner_but_deps_open.findings)
    # With dependencies accepted, the owner may authorize; a second active stage is still refused.
    sandbox.drive_to_accepted("00")
    sandbox.drive_to_accepted("01")
    assert sandbox.go("02", Status.AUTHORIZED).allowed
    parallel = sandbox.go("03", Status.AUTHORIZED)
    assert not parallel.allowed
    assert "MULTIPLE_ACTIVE_STAGES" in sandbox.codes(parallel.findings)
    external_actor = sandbox.go("02", IP, actor=Actor.EXTERNAL_AGENT)
    assert "ACTOR_NOT_PERMITTED" in sandbox.codes(external_actor.findings)


@pytest.mark.negative
def test_08_conflicting_stage_state_records(sandbox: Sandbox) -> None:
    sandbox.go("00", Status.AUTHORIZED)
    reg = sandbox.registry()
    reg["stages"][0]["status"] = "IN_PROGRESS"
    sandbox.save_registry(reg)
    assert "STATUS_HISTORY_CONFLICT" in sandbox.codes(sandbox.orc().check())

    reg["stages"][0]["status"] = "AUTHORIZED"
    reg["stages"][2]["status"] = "IN_PROGRESS"
    reg["stages"][2]["authorization"] = {"owner_ref": OWNER_REF, "scope": "x", "recorded_at": "2026-11-01T00:00:00Z"}
    sandbox.save_registry(reg)
    codes = sandbox.codes(sandbox.orc().check())
    assert {"MULTIPLE_ACTIVE_STAGES", "STATUS_HISTORY_CONFLICT", "DEPENDENCY_NOT_ACCEPTED"} <= codes

    reg["stages"][2].update(status="NOT_STARTED", authorization=None)
    reg["stages"][0]["authorization"] = None
    sandbox.save_registry(reg)
    assert "RECORD_MISSING" in sandbox.codes(sandbox.orc().check())

    reg["stages"][0]["authorization"] = {"owner_ref": OWNER_REF, "scope": "x", "recorded_at": "2026-11-01T00:00:00Z"}
    sandbox.save_registry(reg)
    assert not errors(sandbox.orc().check(include_status_doc=False))
    sandbox.write("PROJECT_STATUS.md", "# Everything is accepted\n")
    assert "STATUS_DOC_OUT_OF_DATE" in sandbox.codes(sandbox.orc().check())


@pytest.mark.negative
def test_09_missing_or_stale_verification_evidence(sandbox: Sandbox) -> None:
    rev = sandbox.drive_to_verified("00")
    assert not errors(sandbox.orc().check())

    handoff = sandbox.root / "docs/verification/stage-00/HANDOFF.md"
    original = handoff.read_text(encoding="utf-8")
    handoff.write_text(original + "\nEdited after verification.\n", encoding="utf-8")
    assert "EVIDENCE_STALE" in sandbox.codes(sandbox.orc().check())
    handoff.write_text(original, encoding="utf-8")

    report = sandbox.root / "docs/verification/stage-00/test-report.json"
    data = json.loads(report.read_text(encoding="utf-8"))
    report.write_text(json.dumps({**data, "totals": {"passed": 999}}), encoding="utf-8")
    assert "TEST_EVIDENCE_STALE" in sandbox.codes(sandbox.orc().check())
    report.write_text(json.dumps(data, indent=2), encoding="utf-8")
    handoff.unlink()
    assert "EVIDENCE_MISSING" in sandbox.codes(sandbox.orc().check())
    handoff.write_text(original, encoding="utf-8")
    assert not errors(sandbox.orc().check())

    # A change to a path the stage owns, committed after verification, makes it stale.
    sandbox.write("src/citerift/governance/new_module.py", "x = 1\n")
    changed = sandbox.commit("change owned code after verification")
    findings = sandbox.orc().check()
    assert "VERIFICATION_STALE" in sandbox.codes(findings)
    assert any(changed[:12] in f.message for f in findings)

    # References to revisions that do not exist, or are not in history, are rejected.
    reg = sandbox.registry()
    reg["stages"][0]["verification"]["revision"] = "f" * 40
    sandbox.save_registry(reg)
    assert "REVISION_NOT_FOUND" in sandbox.codes(sandbox.orc().check())

    reg["stages"][0]["verification"]["revision"] = rev
    sandbox.save_registry(reg)
    # A real commit object that is not part of the current history.
    side = git(sandbox.root, "commit-tree", f"{rev}^{{tree}}", "-m", "unrelated commit")
    reg = sandbox.registry()
    reg["stages"][0]["verification"]["ci"]["head_sha"] = side
    sandbox.save_registry(reg)
    codes = sandbox.codes(sandbox.orc().check())
    assert {"REVISION_NOT_IN_HISTORY", "CI_WRONG_REVISION"} <= codes


def test_10_session_restart_recovers_from_repository_only(sandbox: Sandbox) -> None:
    # Covered in depth by test_recovery.py (fresh clone, clean environment). Here: same process, new object.
    rev = sandbox.drive_to_verified("00")
    data = type(sandbox.orc())(sandbox.root).recover()
    assert data["verified_awaiting_owner_acceptance"] == ["00"]
    assert data["authoritative_revisions"]["00"]["verified"] == rev
    assert data["consistency"]["errors"] == []


def test_11_accepted_stage_evidence_supported_correction(sandbox: Sandbox) -> None:
    first = sandbox.drive_to_accepted("00")

    no_amendment = sandbox.go("00", IP, actor=Actor.OWNER)
    assert not no_amendment.allowed
    assert "AMENDMENT_REQUIRED" in sandbox.codes(no_amendment.findings)

    orc = sandbox.orc()
    aid = orc.add_amendment(
        "00",
        kind="correction",
        reason="Defect found in accepted stage: evidence in issue link",
        evidence_refs=["https://github.com/example/repo/issues/1"],
        owner_ref=OWNER_REF,
        at=sandbox.tick(),
    )
    assert "CORRECTION_PENDING" in sandbox.codes(sandbox.orc().check(), "warning")
    by_agent = sandbox.go("00", IP, actor=Actor.ENGINEERING_AGENT, amendment=aid)
    assert "OWNER_DECISION_REQUIRED" in sandbox.codes(by_agent.findings)

    reopened = sandbox.go("00", IP, actor=Actor.OWNER, amendment=aid)
    assert reopened.allowed, [str(f) for f in reopened.findings]
    stage = sandbox.orc().stage("00")
    assert stage["verification"] is None and stage["acceptance"] is None
    assert sandbox.registry()["history"][-1]["amendment"] == aid

    sandbox.write("impl/00.txt", "corrected implementation\n")
    second = sandbox.commit("correct stage 00")
    assert sandbox.go("00", Status.IMPLEMENTED_NOT_VERIFIED, revision=second).allowed
    sandbox.write_evidence("00", second)
    assert sandbox.go("00", VA, gates=sandbox.gates("00"), ci=sandbox.ci(second)).allowed
    assert sandbox.go("00", AC).allowed
    assert second != first
    assert not errors(sandbox.orc().check())


@pytest.mark.negative
def test_11b_reopening_while_successor_active_is_refused(sandbox: Sandbox) -> None:
    sandbox.drive_to_accepted("00")
    sandbox.drive_to_accepted("01")
    assert sandbox.go("02", Status.AUTHORIZED).allowed
    aid = sandbox.orc().add_amendment(
        "00", kind="correction", reason="Defect report with evidence", evidence_refs=["RISKS.md"], owner_ref=OWNER_REF
    )
    reopened = sandbox.go("00", IP, actor=Actor.OWNER, amendment=aid)
    assert not reopened.allowed
    assert "MULTIPLE_ACTIVE_STAGES" in sandbox.codes(reopened.findings)


def test_12_future_enhancement_preserving_contracts(sandbox: Sandbox) -> None:
    sandbox.drive_to_accepted("00")
    sandbox.write("src/citerift/governance/extension.py", "# additive enhancement\n")
    rev = sandbox.commit("additive enhancement to stage 00 code")
    assert "VERIFICATION_STALE" in sandbox.codes(sandbox.orc().check())

    with pytest.raises(GovernanceError) as missing_tests:
        sandbox.orc().add_amendment(
            "00",
            kind="enhancement",
            reason="Additive extension",
            evidence_refs=["RISKS.md"],
            owner_ref=OWNER_REF,
            revision=rev,
        )
    assert "AMENDMENT_UNVERIFIED" in {f.code for f in missing_tests.value.findings}

    report_rel = "docs/verification/stage-00/amendments/A-00-001-test-report.json"
    failing = {
        "format": "citerift.test-report/1",
        "revision": rev,
        "dirty": False,
        "exit_status": 1,
        "totals": {"passed": 79, "failed": 1},
        "suites": {s: {"passed": 10} for s in sandbox.orc().stage("00")["required_test_suites"]},
    }
    sandbox.write(report_rel, json.dumps(failing))
    with pytest.raises(GovernanceError) as failed_tests:
        sandbox.orc().add_amendment(
            "00",
            kind="enhancement",
            reason="Additive extension",
            evidence_refs=["RISKS.md"],
            owner_ref=OWNER_REF,
            revision=rev,
            test_report=report_rel,
        )
    assert "TESTS_FAILED" in {f.code for f in failed_tests.value.findings}

    sandbox.write(report_rel, json.dumps({**failing, "exit_status": 0, "totals": {"passed": 80}}))
    aid = sandbox.orc().add_amendment(
        "00",
        kind="enhancement",
        reason="Additive extension",
        evidence_refs=["RISKS.md"],
        owner_ref=OWNER_REF,
        revision=rev,
        test_report=report_rel,
    )
    orc = sandbox.orc()
    assert aid == "A-00-001"
    assert orc.stage("00")["status"] == AC
    assert not errors(orc.check())


@pytest.mark.negative
def test_blocker_lifecycle(sandbox: Sandbox) -> None:
    sandbox.go("00", Status.AUTHORIZED)
    sandbox.go("00", IP)
    no_blocker = sandbox.go("00", Status.BLOCKED)
    assert "BLOCKED_WITHOUT_BLOCKER" in sandbox.codes(no_blocker.findings)
    bid = sandbox.orc().add_blocker("00", "GitHub permission missing", at=sandbox.tick())
    assert sandbox.go("00", Status.BLOCKED).allowed
    still_open = sandbox.go("00", IP)
    assert "BLOCKER_OPEN" in sandbox.codes(still_open.findings)
    assert sandbox.orc().resolve_blocker("00", bid, "permission granted", at=sandbox.tick()) is True
    assert sandbox.registry()["history"][-1]["from"] == "BLOCKED"
    assert sandbox.orc().stage("00")["status"] == IP
    assert not errors(sandbox.orc().check())


@pytest.mark.negative
def test_open_blocker_prevents_verification(sandbox: Sandbox) -> None:
    _prepare_implemented(sandbox)
    rev = sandbox.orc().stage("00")["implementation"]["revision"]
    sandbox.write_evidence("00", rev)
    sandbox.orc().add_blocker("00", "unresolved defect", at=sandbox.tick())
    result = sandbox.go("00", VA, gates=sandbox.gates("00"), ci=sandbox.ci(rev))
    assert "BLOCKER_OPEN" in sandbox.codes(result.findings)


@pytest.mark.negative
def test_open_critical_defect_prevents_verification(sandbox: Sandbox) -> None:
    _prepare_implemented(sandbox)
    rev = sandbox.orc().stage("00")["implementation"]["revision"]
    sandbox.write_evidence("00", rev)
    risks = (sandbox.root / "RISKS.md").read_text(encoding="utf-8")
    sandbox.write(
        "RISKS.md",
        risks
        + "\n## R-002 — Registry can be corrupted\n- Status: open\n- Severity: critical\n- Kind: defect\n- Stage: 00\n",
    )
    result = sandbox.go("00", VA, gates=sandbox.gates("00"), ci=sandbox.ci(rev))
    assert "OPEN_CRITICAL_DEFECT" in sandbox.codes(result.findings)


def _prepare_implemented(sandbox: Sandbox) -> None:
    sandbox.go("00", Status.AUTHORIZED)
    sandbox.go("00", IP)
    sandbox.write("impl/00.txt", "implementation\n")
    rev = sandbox.commit("implement")
    assert sandbox.go("00", Status.IMPLEMENTED_NOT_VERIFIED, revision=rev).allowed
