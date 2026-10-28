"""Maintenance transactions on an accepted stage (A-00-002): prepare, validate, finalize.

Every scenario runs the real orchestrator on a throwaway git repository. The lifecycle is:
accept Stage 00 at a baseline, commit a patch to its owned files (the candidate), record the patch as
pending, commit that state (the validated revision), write complete reports at it for each Python
version, and finalize.
"""

from __future__ import annotations

import json
import os
from typing import Any

import pytest
from sandbox_repo import Sandbox

from citerift.governance import maintenance
from citerift.governance.model import Actor, Status
from citerift.governance.orchestrator import GovernanceError, Orchestrator, errors

pytestmark = [pytest.mark.integration, pytest.mark.security]

PATCHED = "src/citerift/governance/patched_module.py"
OTHER = "src/citerift/governance/other_module.py"
REPORT_DIR = "docs/verification/maintenance/A-00-001"


def _report(sandbox: Sandbox, revision: str, python: str, overrides: dict[str, Any] | None = None) -> str:
    suites = sandbox.orc().stage("00")["required_test_suites"]
    data: dict[str, Any] = {
        "format": "citerift.test-report/1",
        "revision": revision,
        "dirty": False,
        "exit_status": 0,
        "python": f"{python}.1",
        "finished_at": sandbox.tick(),
        "totals": {"passed": 10 * len(suites)},
        "selection": {"args": ["tests"], "deselected": 0, "complete": True},
        "suites": {s: {"passed": 10} for s in suites},
    }
    data.update(overrides or {})
    rel = f"{REPORT_DIR}/test-report-py{python}.json"
    sandbox.write(rel, json.dumps(data, indent=2))
    return rel


class Lifecycle:
    """One sandbox driven through the maintenance phases, with the revisions each phase produced."""

    def __init__(self, sandbox: Sandbox):
        self.sb = sandbox
        sandbox.write(PATCHED, "version = 0\n")
        sandbox.commit("owned module, accepted version")
        self.baseline = sandbox.drive_to_accepted("00")
        self.acceptance = sandbox.orc().stage("00")["acceptance"]
        self.owner_ref = sandbox.new_ref()
        sandbox.write(PATCHED, "version = 1\n")
        self.candidate = sandbox.commit("maintenance patch")
        self.aid = ""
        self.validated = ""

    def prepare(self, paths: list[str] | None = None, **kwargs: Any) -> str:
        kwargs.setdefault("owner_ref", self.owner_ref)
        kwargs.setdefault("candidate", self.candidate)
        self.aid = self.sb.orc().prepare_maintenance(
            "00",
            paths=paths or [PATCHED],
            purpose="Repair a test assumption of the governance check",
            reason="Owner-authorized maintenance of a Stage 00 owned file",
            evidence_refs=["RISKS.md"],
            at=self.sb.tick(),
            **kwargs,
        )
        return self.aid

    def validate(self) -> list[str]:
        self.validated = self.sb.commit("record pending maintenance")
        return [_report(self.sb, self.validated, py) for py in maintenance.REQUIRED_PYTHONS]

    def finalize(self, reports: list[str], revision: str | None = None) -> None:
        self.sb.orc().finalize_maintenance(
            "00", self.aid, revision=revision or self.validated, reports=reports, at=self.sb.tick()
        )

    def record(self) -> dict[str, Any]:
        return next(a for a in self.sb.orc().stage("00")["amendments"] if a["id"] == self.aid)


@pytest.fixture
def life(sandbox: Sandbox) -> Lifecycle:
    return Lifecycle(sandbox)


def _codes(sandbox: Sandbox, severity: str = "error") -> set[str]:
    return sandbox.codes(sandbox.orc().check(), severity)


def _rejected(call: Any) -> set[str]:
    with pytest.raises(GovernanceError) as exc:
        call()
    return {f.code for f in exc.value.findings}


# ------------------------------------------------------------------ the valid path


def test_valid_lifecycle_prepare_validate_finalize(life: Lifecycle) -> None:
    sb = life.sb
    assert "VERIFICATION_STALE" in _codes(sb)
    life.prepare()
    found = sb.orc().check()
    assert not errors(found)
    assert "MAINTENANCE_PENDING" in sb.codes(found, "warning")
    assert life.record()["maintenance"]["phase"] == maintenance.PENDING
    assert life.record()["revision"] is None and life.record()["test_report"] is None

    reports = life.validate()
    assert not errors(sb.orc().check())
    life.finalize(reports)
    sb.commit("finalize maintenance")
    found = sb.orc().check()
    assert not errors(found)
    assert "MAINTENANCE_PENDING" not in sb.codes(found, "warning")
    stage = sb.orc().stage("00")
    assert stage["status"] == Status.ACCEPTED_CLOSED
    assert stage["acceptance"] == life.acceptance  # history and acceptance are not rewritten
    rec = life.record()
    assert rec["maintenance"]["phase"] == maintenance.FINALIZED
    assert rec["revision"] == life.validated
    assert sorted(r["python"] for r in rec["maintenance"]["reports"]) == list(maintenance.REQUIRED_PYTHONS)


def test_after_finalization_ordinary_drift_is_detected_again(life: Lifecycle) -> None:
    life.prepare()
    life.finalize(life.validate())
    life.sb.commit("finalize maintenance")
    life.sb.write(PATCHED, "version = 2\n")
    life.sb.commit("an unauthorized later change")
    assert "VERIFICATION_STALE" in _codes(life.sb)


def test_finalizing_twice_is_refused(life: Lifecycle) -> None:
    life.prepare()
    reports = life.validate()
    life.finalize(reports)
    assert "MAINTENANCE_STATE" in _rejected(lambda: life.finalize(reports))


def test_restart_between_phases_reads_the_same_state(life: Lifecycle) -> None:
    life.prepare()
    before = life.sb.orc().check()
    restarted = Orchestrator(life.sb.root)
    assert [str(f) for f in restarted.check()] == [str(f) for f in before]
    reports = life.validate()
    life.finalize(reports)
    assert not errors(Orchestrator(life.sb.root).check())


def test_a_crash_while_writing_leaves_the_previous_registry(life: Lifecycle, monkeypatch: pytest.MonkeyPatch) -> None:
    registry = (life.sb.root / "governance/stage_registry.json").read_text(encoding="utf-8")

    def crash(src: Any, dst: Any) -> None:
        raise OSError("simulated crash before the rename")

    monkeypatch.setattr(os, "replace", crash)
    with pytest.raises(OSError):
        life.prepare()
    monkeypatch.undo()
    assert (life.sb.root / "governance/stage_registry.json").read_text(encoding="utf-8") == registry
    assert not list((life.sb.root / "governance").glob(".stage_registry.json.*.tmp"))
    life.prepare()  # the retry after the crash records the transaction once
    assert [a["id"] for a in life.sb.orc().stage("00")["amendments"]] == [life.aid]


# ------------------------------------------------------------------ prepare refusals


def test_prepare_refuses_a_path_the_candidate_does_not_change(life: Lifecycle) -> None:
    codes = _rejected(lambda: life.prepare(paths=[PATCHED, "src/citerift/governance/never_changed.py"]))
    assert "MAINTENANCE_PATCH_MISMATCH" in codes


def test_prepare_refuses_an_undeclared_change_beside_the_patch(life: Lifecycle) -> None:
    life.sb.write(OTHER, "x = 1\n")
    life.candidate = life.sb.commit("patch plus an undeclared owned change")
    codes = _rejected(lambda: life.prepare(paths=[PATCHED]))
    assert "MAINTENANCE_PATCH_MISMATCH" in codes


def test_prepare_refuses_a_path_the_stage_does_not_own(life: Lifecycle) -> None:
    life.sb.write("docs/notes.md", "not owned\n")
    life.candidate = life.sb.commit("unowned file")
    assert "MAINTENANCE_SCOPE" in _rejected(lambda: life.prepare(paths=[PATCHED, "docs/notes.md"]))


def test_prepare_refuses_a_candidate_that_is_not_a_commit(life: Lifecycle) -> None:
    assert "MAINTENANCE_PATCH_MISMATCH" in _rejected(lambda: life.prepare(candidate="0" * 40))


def test_prepare_refuses_a_reused_owner_reference(life: Lifecycle) -> None:
    codes = _rejected(lambda: life.prepare(owner_ref=life.acceptance["owner_ref"]))
    assert "OWNER_REF_REUSED" in codes


def test_prepare_refuses_a_missing_owner_reference(life: Lifecycle) -> None:
    assert _rejected(lambda: life.prepare(owner_ref=""))


def test_prepare_refuses_a_stage_that_is_not_accepted(sandbox: Sandbox) -> None:
    sandbox.drive_to_verified("00")
    sandbox.write(PATCHED, "version = 1\n")
    rev = sandbox.commit("patch on a stage that is only verified")
    with pytest.raises(GovernanceError) as exc:
        sandbox.orc().prepare_maintenance(
            "00",
            candidate=rev,
            paths=[PATCHED],
            purpose="Repair a test assumption",
            reason="Not applicable here",
            evidence_refs=["RISKS.md"],
            owner_ref=sandbox.new_ref(),
        )
    assert "AMENDMENT_NOT_APPLICABLE" in {f.code for f in exc.value.findings}


def test_a_second_pending_transaction_is_refused(life: Lifecycle) -> None:
    life.prepare()
    assert "MAINTENANCE_CONCURRENT" in _rejected(lambda: life.prepare(owner_ref=life.sb.new_ref()))


# ------------------------------------------------------------------ while pending


def test_unrelated_drift_beside_a_pending_patch_is_an_error(life: Lifecycle) -> None:
    life.prepare()
    life.sb.write(OTHER, "x = 1\n")
    life.sb.commit("undeclared owned change while pending")
    codes = _codes(life.sb)
    assert {"VERIFICATION_STALE", "MAINTENANCE_PATCH_MISMATCH"} <= codes


def test_patch_changed_after_prepare_is_an_error_until_superseded(life: Lifecycle) -> None:
    first = life.prepare()
    life.sb.write(PATCHED, "version = 1.5\n")
    life.candidate = life.sb.commit("candidate changed after prepare")
    assert {"VERIFICATION_STALE", "MAINTENANCE_PATCH_MISMATCH"} <= _codes(life.sb)
    second = life.prepare(supersedes=first)
    assert not errors(life.sb.orc().check())
    amendments = {a["id"]: a for a in life.sb.orc().stage("00")["amendments"]}
    assert amendments[first]["maintenance"]["phase"] == maintenance.SUPERSEDED
    assert amendments[first]["maintenance"]["superseded_by"] == second
    life.finalize(life.validate())
    assert not errors(life.sb.orc().check())


def test_patch_changed_after_validation_cannot_be_finalized(life: Lifecycle) -> None:
    life.prepare()
    reports = life.validate()
    life.sb.write(PATCHED, "version = 'smuggled'\n")
    life.sb.commit("change after the validated revision")
    assert _rejected(lambda: life.finalize(reports))
    assert life.record()["maintenance"]["phase"] == maintenance.PENDING


def test_no_stage_can_be_verified_or_accepted_while_maintenance_is_pending(sandbox: Sandbox) -> None:
    sandbox.write(PATCHED, "version = 0\n")
    sandbox.commit("owned module")
    sandbox.drive_to_accepted("00")
    accepted_01 = sandbox.drive_to_accepted("01")  # accepted before the maintenance: stays valid
    for target in (Status.AUTHORIZED, Status.IN_PROGRESS):
        assert sandbox.go("02", target).allowed
    sandbox.write("impl/02.txt", "stage 02\n")
    rev02 = sandbox.commit("stage 02 work")
    assert sandbox.go("02", Status.IMPLEMENTED_NOT_VERIFIED, revision=rev02).allowed
    sandbox.write_evidence("02", rev02)
    sandbox.commit("stage 02 evidence")

    sandbox.write(PATCHED, "version = 1\n")
    candidate = sandbox.commit("maintenance patch")
    aid = sandbox.orc().prepare_maintenance(
        "00",
        candidate=candidate,
        paths=[PATCHED],
        purpose="Repair a test assumption of the governance check",
        reason="Owner-authorized maintenance",
        evidence_refs=["RISKS.md"],
        owner_ref=sandbox.new_ref(),
        at=sandbox.tick(),
    )
    assert not errors(sandbox.orc().check())
    assert sandbox.orc().stage("01")["acceptance"]["accepted_revision"] == accepted_01

    blocked = sandbox.go(
        "02", Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE, gates=sandbox.gates("02"), ci=sandbox.ci(rev02)
    )
    assert not blocked.allowed
    assert "MAINTENANCE_BARRIER" in sandbox.codes(blocked.findings)

    validated = sandbox.commit("record pending maintenance")
    reports = [_report(sandbox, validated, py) for py in maintenance.REQUIRED_PYTHONS]
    sandbox.orc().finalize_maintenance("00", aid, revision=validated, reports=reports, at=sandbox.tick())
    sandbox.commit("finalize maintenance")
    allowed = sandbox.go(
        "02", Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE, gates=sandbox.gates("02"), ci=sandbox.ci(rev02)
    )
    assert allowed.allowed, [str(f) for f in allowed.findings]


def test_a_hand_written_acceptance_inside_the_interval_is_an_error(life: Lifecycle) -> None:
    life.prepare()
    reg = life.sb.registry()
    reg["history"].append(
        {
            **reg["history"][-1],
            "seq": len(reg["history"]) + 1,
            "at": life.sb.tick(),
        }
    )
    life.sb.save_registry(reg)
    assert "MAINTENANCE_BARRIER" in _codes(life.sb)


def test_two_active_engineering_stages_still_fail_while_pending(sandbox: Sandbox) -> None:
    """Maintenance does not reopen Stage 00: a reopening while Stage 02 is active is still refused."""
    sandbox.write(PATCHED, "version = 0\n")
    sandbox.commit("owned module")
    sandbox.drive_to_accepted("00")
    sandbox.drive_to_accepted("01")
    for target in (Status.AUTHORIZED, Status.IN_PROGRESS):
        assert sandbox.go("02", target).allowed
    sandbox.write(PATCHED, "version = 1\n")
    candidate = sandbox.commit("maintenance patch")
    sandbox.orc().prepare_maintenance(
        "00",
        candidate=candidate,
        paths=[PATCHED],
        purpose="Repair a test assumption of the governance check",
        reason="Owner-authorized maintenance",
        evidence_refs=["RISKS.md"],
        owner_ref=sandbox.new_ref(),
        at=sandbox.tick(),
    )
    correction = sandbox.orc().add_amendment(
        "00",
        kind="correction",
        reason="A correction that would need a reopening",
        evidence_refs=["RISKS.md"],
        owner_ref=sandbox.new_ref(),
        at=sandbox.tick(),
    )
    reopened = sandbox.go("00", Status.IN_PROGRESS, actor=Actor.OWNER, amendment=correction)
    assert not reopened.allowed
    assert "MULTIPLE_ACTIVE_STAGES" in sandbox.codes(reopened.findings)


# ------------------------------------------------------------------ finalize refusals


@pytest.mark.parametrize(
    ("overrides", "code"),
    [
        ({"exit_status": 1, "totals": {"passed": 79, "failed": 1}}, "TESTS_FAILED"),
        ({"selection": {"args": ["tests/stage00"], "deselected": 0, "complete": False}}, "TEST_EVIDENCE_PARTIAL"),
        ({"dirty": True}, "TEST_EVIDENCE_DIRTY"),
        ({"totals": {"passed": 79, "skipped": 1}}, "TEST_EVIDENCE_PARTIAL"),
        ({"suites": {"unit": {"passed": 10}}}, "TEST_SUITE_MISSING"),
        ({"revision": "f" * 40}, "TEST_EVIDENCE_WRONG_REVISION"),
        ({"finished_at": "2099-01-01T00:00:00Z"}, "MAINTENANCE_REPORT"),
    ],
)
def test_a_report_that_does_not_prove_the_patch_cannot_finalize(
    life: Lifecycle, overrides: dict[str, Any], code: str
) -> None:
    life.prepare()
    reports = life.validate()
    reports[0] = _report(life.sb, life.validated, maintenance.REQUIRED_PYTHONS[0], overrides)
    assert code in _rejected(lambda: life.finalize(reports))
    rec = life.record()
    assert rec["maintenance"]["phase"] == maintenance.PENDING  # the failure leaves the transaction pending
    assert life.sb.orc().stage("00")["acceptance"] == life.acceptance


def test_finalizing_needs_every_python_version(life: Lifecycle) -> None:
    life.prepare()
    reports = life.validate()
    assert "MAINTENANCE_PYTHON_MISSING" in _rejected(lambda: life.finalize(reports[:1]))


def test_a_report_of_a_revision_without_the_pending_record_cannot_finalize(life: Lifecycle) -> None:
    life.prepare()
    life.validate()
    early = [_report(life.sb, life.candidate, py) for py in maintenance.REQUIRED_PYTHONS]
    assert "MAINTENANCE_NOT_VALIDATED" in _rejected(lambda: life.finalize(early, revision=life.candidate))


# ------------------------------------------------------------------ forged records


def test_a_report_edited_after_finalization_is_stale(life: Lifecycle) -> None:
    life.prepare()
    reports = life.validate()
    life.finalize(reports)
    path = life.sb.root / reports[1]
    path.write_text(path.read_text(encoding="utf-8").replace('"passed": 10', '"passed": 11'), encoding="utf-8")
    assert "TEST_EVIDENCE_STALE" in _codes(life.sb)


def test_a_hand_finalized_record_without_reports_is_an_error(life: Lifecycle) -> None:
    life.prepare()
    validated = life.sb.commit("record pending maintenance")
    reg = life.sb.registry()
    rec = next(a for a in reg["stages"][0]["amendments"] if a["id"] == life.aid)
    rec["revision"] = validated
    rec["test_report"] = {"path": "RISKS.md", "sha256": "0" * 64}
    rec["maintenance"].update(phase=maintenance.FINALIZED, finalized_at=life.sb.tick())
    life.sb.save_registry(reg)
    assert "MAINTENANCE_STATE" in _codes(life.sb)


def test_a_forged_patch_digest_is_an_error(life: Lifecycle) -> None:
    life.prepare()
    reg = life.sb.registry()
    rec = next(a for a in reg["stages"][0]["amendments"] if a["id"] == life.aid)
    rec["maintenance"]["scope"].append({"path": OTHER, "sha256": None})
    life.sb.save_registry(reg)
    assert "MAINTENANCE_RECORD" in _codes(life.sb)


def test_a_superseded_record_needs_its_successor(life: Lifecycle) -> None:
    life.prepare()
    reg = life.sb.registry()
    rec = next(a for a in reg["stages"][0]["amendments"] if a["id"] == life.aid)
    rec["maintenance"].update(phase=maintenance.SUPERSEDED, superseded_by="A-00-009")
    life.sb.save_registry(reg)
    assert "MAINTENANCE_STATE" in _codes(life.sb)


def test_an_ordinary_enhancement_keeps_its_rules(life: Lifecycle) -> None:
    """A record without maintenance metadata is checked as before: it needs its own passing report."""
    reg = life.sb.registry()
    reg["stages"][0]["amendments"].append(
        {
            "id": "A-00-001",
            "kind": "enhancement",
            "reason": "ordinary enhancement without a report",
            "evidence": ["RISKS.md"],
            "owner_ref": life.owner_ref,
            "revision": life.candidate,
            "test_report": None,
            "recorded_at": life.sb.tick(),
        }
    )
    life.sb.save_registry(reg)
    codes = _codes(life.sb)
    assert "AMENDMENT_UNVERIFIED" in codes
    assert "VERIFICATION_STALE" in codes


def test_maintenance_cli_round_trip(life: Lifecycle, capsys: pytest.CaptureFixture[str]) -> None:
    from citerift.governance.cli import main

    root = ["--root", str(life.sb.root)]
    code = main(
        [
            *root,
            "maintenance",
            "prepare",
            "00",
            "--candidate",
            life.candidate,
            "--path",
            PATCHED,
            "--purpose",
            "Repair a test assumption of the governance check",
            "--reason",
            "Owner-authorized maintenance",
            "--evidence",
            "RISKS.md",
            "--owner-ref",
            life.owner_ref,
            "--at",
            life.sb.tick(),
        ]
    )
    assert code == 0, capsys.readouterr().out
    life.aid = "A-00-001"
    reports = life.validate()
    flags = [x for r in reports for x in ("--report", r)]
    at = ["--at", life.sb.tick()]
    assert main([*root, "maintenance", "finalize", "00", "A-00-001", "--revision", life.validated, *flags, *at]) == 0
    assert main([*root, "maintenance", "finalize", "00", "A-00-001", "--revision", life.validated, *flags]) == 1
    assert "MAINTENANCE_STATE" in capsys.readouterr().out


def test_report_python_version_parsing() -> None:
    assert maintenance.python_minor({"python": "3.13.7"}) == "3.13"
    assert maintenance.python_minor({"python": "3"}) is None
    assert maintenance.python_minor({}) is None
    scope = [{"path": "b", "sha256": None}, {"path": "a", "sha256": "1" * 64}]
    assert maintenance.patch_sha256(scope) == maintenance.patch_sha256(list(reversed(scope)))


# ------------------------------------------------- regressions of the adversarial review


def _stage02_ready_with_pending_maintenance(sandbox: Sandbox, *, gap: int = 0) -> tuple[str, str, str]:
    """Stage 02 implemented and ready to verify, then a pending Stage 00 maintenance prepared ``gap``
    seconds after the last history entry. Returns (stage 02 revision, amendment id, prepare time)."""
    sandbox.write(PATCHED, "version = 0\n")
    sandbox.commit("owned module")
    sandbox.drive_to_accepted("00")
    sandbox.drive_to_accepted("01")
    for target in (Status.AUTHORIZED, Status.IN_PROGRESS):
        assert sandbox.go("02", target).allowed
    sandbox.write("impl/02.txt", "stage 02\n")
    rev02 = sandbox.commit("stage 02 work")
    assert sandbox.go("02", Status.IMPLEMENTED_NOT_VERIFIED, revision=rev02).allowed
    sandbox.write_evidence("02", rev02)
    sandbox.commit("stage 02 evidence")
    sandbox.write(PATCHED, "version = 1\n")
    candidate = sandbox.commit("maintenance patch")
    sandbox.clock += gap
    at = sandbox.tick()
    aid = sandbox.orc().prepare_maintenance(
        "00",
        candidate=candidate,
        paths=[PATCHED],
        purpose="Repair a test assumption of the governance check",
        reason="Owner-authorized maintenance",
        evidence_refs=["RISKS.md"],
        owner_ref=sandbox.new_ref(),
        at=at,
    )
    return rev02, aid, at


def test_a_verification_dated_before_the_pending_record_is_still_barred(sandbox: Sandbox) -> None:
    """Review finding 1: the window is anchored to history positions, so ``--at`` cannot date around it."""
    rev02, _aid, at = _stage02_ready_with_pending_maintenance(sandbox, gap=5)
    before = f"{at[:-3]}{int(at[-3:-1]) - 1:02d}Z"
    result = sandbox.go(
        "02", Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE, gates=sandbox.gates("02"), ci=sandbox.ci(rev02), at=before
    )
    assert not result.allowed
    assert "MAINTENANCE_BARRIER" in sandbox.codes(result.findings)


def test_rewriting_the_prepare_time_after_validation_cannot_finalize(life: Lifecycle) -> None:
    """Review finding 2: the finalized record must equal the pending record the validated revision holds."""
    life.prepare()
    reports = life.validate()
    reg = life.sb.registry()
    rec = next(a for a in reg["stages"][0]["amendments"] if a["id"] == life.aid)
    rec["recorded_at"] = life.sb.tick()
    life.sb.save_registry(reg)
    assert "MAINTENANCE_NOT_VALIDATED" in _rejected(lambda: life.finalize(reports))


def test_a_report_from_before_the_prepare_cannot_finalize(life: Lifecycle) -> None:
    life.prepare()
    validated = life.sb.commit("record pending maintenance")
    life.validated = validated
    early = _report(life.sb, validated, "3.12", {"finished_at": "2025-12-31T00:00:00Z"})
    late = _report(life.sb, validated, "3.13")
    assert "MAINTENANCE_REPORT" in _rejected(lambda: life.finalize([early, late]))


def test_a_contract_change_in_the_patch_needs_its_version_raised(sandbox: Sandbox) -> None:
    """Review finding 3: a maintenance patch keeps the contract versioning rule of every enhancement."""
    path = "schemas/contracts/v1/common.schema.json"
    sandbox.drive_to_accepted("00")
    schema = json.loads((sandbox.root / path).read_text(encoding="utf-8"))
    schema["description"] = f"{schema.get('description', '')} (edited)"
    sandbox.write(path, json.dumps(schema, indent=2) + "\n")
    candidate = sandbox.commit("contract edit without a version increase")
    codes = _rejected(
        lambda: sandbox.orc().prepare_maintenance(
            "00",
            candidate=candidate,
            paths=[path],
            purpose="Repair a test assumption of the governance check",
            reason="Owner-authorized maintenance",
            evidence_refs=["RISKS.md"],
            owner_ref=sandbox.new_ref(),
            at=sandbox.tick(),
        )
    )
    assert "CONTRACT_VERSION_NOT_INCREASED" in codes


def test_an_ordinary_enhancement_cannot_cover_a_pending_patch(life: Lifecycle) -> None:
    """Review finding 4: refused by the tool, and caught by check if the pending record is deleted by hand."""
    life.prepare()
    reports = life.validate()

    def enhance() -> str:
        return life.sb.orc().add_amendment(
            "00",
            kind="enhancement",
            reason="cover the patch without finalizing",
            evidence_refs=["RISKS.md"],
            owner_ref=life.sb.new_ref(),
            revision=life.validated,
            test_report=reports[0],
            at=life.sb.tick(),
        )

    assert "MAINTENANCE_BARRIER" in _rejected(enhance)
    reg = life.sb.registry()
    stage = reg["stages"][0]
    stage["amendments"] = [a for a in stage["amendments"] if a["id"] != life.aid]
    stage["amendments"].append(
        {
            "id": life.aid,
            "kind": "enhancement",
            "reason": "cover the patch without finalizing",
            "evidence": ["RISKS.md"],
            "owner_ref": life.sb.new_ref(),
            "revision": life.validated,
            "test_report": {"path": reports[0], "sha256": _sha(life.sb, reports[0])},
            "recorded_at": life.sb.tick(),
        }
    )
    life.sb.save_registry(reg)
    assert "MAINTENANCE_BARRIER" in _codes(life.sb)


def _sha(sandbox: Sandbox, rel: str) -> str:
    import hashlib

    return hashlib.sha256((sandbox.root / rel).read_bytes()).hexdigest()


def test_an_executable_bit_on_a_declared_file_is_not_the_declared_patch(life: Lifecycle) -> None:
    """Review finding 5: the digest covers content only, so a declared file must stay a regular file."""
    life.prepare()
    os.chmod(life.sb.root / PATCHED, 0o744)  # owner-executable is enough for git
    life.sb.commit("make the patched file executable")
    assert "MAINTENANCE_PATCH_MISMATCH" in _codes(life.sb)


def test_prepare_refuses_a_directory_or_a_non_regular_entry(life: Lifecycle) -> None:
    """Review findings 5 and 7: a directory or an executable is refused with a finding, not a traceback."""
    assert "MAINTENANCE_SCOPE" in _rejected(lambda: life.prepare(paths=["src/citerift/governance"]))
    os.chmod(life.sb.root / PATCHED, 0o744)  # owner-executable is enough for git
    life.candidate = life.sb.commit("executable patch")
    assert "MAINTENANCE_SCOPE" in _rejected(life.prepare)


def test_superseding_in_the_same_second_may_cite_the_same_decision(life: Lifecycle) -> None:
    """Review finding 6: the supersession chain is exempt from reference reuse in both directions."""
    life.prepare()
    first = life.aid
    life.sb.write(PATCHED, "version = 2\n")
    life.candidate = life.sb.commit("changed candidate")
    at = life.sb.registry()["stages"][0]["amendments"][-1]["recorded_at"]
    life.aid = life.sb.orc().prepare_maintenance(
        "00",
        candidate=life.candidate,
        paths=[PATCHED],
        purpose="Repair a test assumption of the governance check",
        reason="Owner-authorized maintenance, changed candidate",
        evidence_refs=["RISKS.md"],
        owner_ref=life.owner_ref,
        supersedes=first,
        at=at,
    )
    assert not errors(life.sb.orc().check())


def _hand_verified_02(sandbox: Sandbox, rev02: str, at: str, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """A registry with Stage 02 verified, as a hand edit could write it: the tool's own transition computed
    with the barrier switched off."""
    with monkeypatch.context() as m:
        m.setattr(Orchestrator, "_maintenance_barrier_findings", lambda self, records: [])
        result = sandbox.orc().propose(
            "02",
            Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE,
            actor=Actor.ENGINEERING_AGENT,
            reason="hand-written verification",
            gates=sandbox.gates("02"),
            ci=sandbox.ci(rev02),
            at=at,
        )
    assert result.allowed, [str(f) for f in result.findings]
    return result.registry


def test_a_finalization_cannot_end_the_window_before_the_validated_history(
    sandbox: Sandbox, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Second review, finding 1: finalized_after_seq set back over a verification the validated revision holds."""
    rev02, aid, _at = _stage02_ready_with_pending_maintenance(sandbox)
    opened = sandbox.registry()["stages"][0]["amendments"][-1]["maintenance"]["opened_after_seq"]
    t_report, t_final, t_entry = sandbox.tick(), sandbox.tick(), sandbox.tick()
    sandbox.save_registry(_hand_verified_02(sandbox, rev02, t_entry, monkeypatch))
    validated = sandbox.commit("validated revision holding a verification inside the window")
    reports = [_report(sandbox, validated, py, {"finished_at": t_report}) for py in maintenance.REQUIRED_PYTHONS]
    reg = sandbox.registry()
    rec = reg["stages"][0]["amendments"][-1]
    entries = [
        {"path": r, "sha256": _sha(sandbox, r), "python": py}
        for r, py in zip(reports, maintenance.REQUIRED_PYTHONS, strict=True)
    ]
    rec.update(revision=validated, test_report={"path": reports[0], "sha256": entries[0]["sha256"]})
    rec["maintenance"].update(phase="finalized", reports=entries, finalized_at=t_final, finalized_after_seq=opened)
    sandbox.save_registry(reg)
    sandbox.commit("hand finalization")
    assert aid == rec["id"]
    assert "MAINTENANCE_STATE" in _codes(sandbox)


def test_a_raised_window_opening_is_an_error(sandbox: Sandbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """Second review, finding 2: the opening must be the history length the candidate revision holds."""
    rev02, aid, at = _stage02_ready_with_pending_maintenance(sandbox, gap=5)
    before = f"{at[:-3]}{int(at[-3:-1]) - 1:02d}Z"  # after the last history entry, before the prepare
    reg = _hand_verified_02(sandbox, rev02, before, monkeypatch)
    rec = next(a for a in reg["stages"][0]["amendments"] if a["id"] == aid)
    rec["maintenance"]["opened_after_seq"] = len(reg["history"])
    sandbox.save_registry(reg)
    assert "MAINTENANCE_STATE" in _codes(sandbox)


def test_a_transition_in_the_second_of_the_finalization_is_allowed(sandbox: Sandbox) -> None:
    """Second review, finding 3: the window ends by position, so the same second is not inside it."""
    rev02, aid, _at = _stage02_ready_with_pending_maintenance(sandbox)
    validated = sandbox.commit("record pending maintenance")
    reports = [_report(sandbox, validated, py) for py in maintenance.REQUIRED_PYTHONS]
    t = sandbox.tick()
    sandbox.orc().finalize_maintenance("00", aid, revision=validated, reports=reports, at=t)
    sandbox.commit("finalize maintenance")
    result = sandbox.go(
        "02", Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE, gates=sandbox.gates("02"), ci=sandbox.ci(rev02), at=t
    )
    assert result.allowed, [str(f) for f in result.findings]
