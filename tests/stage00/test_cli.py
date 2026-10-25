"""Command-line interface of the Project Orchestrator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sandbox_repo import OWNER_REF, Sandbox

from citerift.governance.cli import main

pytestmark = [pytest.mark.integration]


def run(sandbox: Sandbox, capsys: pytest.CaptureFixture[str], *args: str) -> tuple[int, str]:
    code = main(["--root", str(sandbox.root), *args])
    return code, capsys.readouterr().out


def test_read_only_commands(sandbox: Sandbox, capsys: pytest.CaptureFixture[str]) -> None:
    before = (sandbox.root / "governance/stage_registry.json").read_bytes()
    code, out = run(sandbox, capsys, "status")
    assert code == 0 and "NOT_STARTED" in out and "No stage is authorized" not in out
    code, out = run(sandbox, capsys, "deps", "04")
    assert code == 0 and "depends on: 02, 03" in out and "Dependents: 05" in out
    code, out = run(sandbox, capsys, "--json", "deps", "02")
    assert json.loads(out)["unsatisfied"] == ["00", "01"]
    code, out = run(sandbox, capsys, "--json", "transitions")
    assert code == 0 and sum(row["owner_only"] for row in json.loads(out)) == 4
    code, out = run(sandbox, capsys, "check")
    assert code == 0 and "0 errors" in out
    code, out = run(sandbox, capsys, "render-status", "--check")
    assert code == 0
    code, out = run(sandbox, capsys, "handoff", "00")
    assert code == 0 and "Owner acceptance: not recorded" in out
    code, out = run(sandbox, capsys, "recover")
    assert code == 0 and "Next actions:" in out
    assert (sandbox.root / "governance/stage_registry.json").read_bytes() == before


def test_transition_is_dry_run_unless_applied(sandbox: Sandbox, capsys: pytest.CaptureFixture[str]) -> None:
    args = ["transition", "00", "AUTHORIZED", "--actor", "owner", "--owner-ref", OWNER_REF, "--reason", "go"]
    code, out = run(sandbox, capsys, *args)
    assert code == 0 and "ALLOWED" in out and "Dry run" in out
    assert sandbox.registry()["stages"][0]["status"] == "NOT_STARTED"
    code, out = run(sandbox, capsys, *args, "--apply")
    assert code == 0 and "Applied" in out
    assert sandbox.registry()["stages"][0]["status"] == "AUTHORIZED"
    code, _ = run(sandbox, capsys, "render-status", "--check")
    assert code == 0


@pytest.mark.negative
def test_rejected_transition_exits_nonzero_and_writes_nothing(
    sandbox: Sandbox, capsys: pytest.CaptureFixture[str]
) -> None:
    before = (sandbox.root / "governance/stage_registry.json").read_bytes()
    code, out = run(
        sandbox, capsys, "transition", "00", "AUTHORIZED", "--actor", "engineering-agent", "--reason", "self", "--apply"
    )
    assert code == 1 and "REJECTED" in out and "OWNER_DECISION_REQUIRED" in out
    assert (sandbox.root / "governance/stage_registry.json").read_bytes() == before


def test_verification_from_record_file(sandbox: Sandbox, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    run(
        sandbox,
        capsys,
        "transition",
        "00",
        "AUTHORIZED",
        "--actor",
        "owner",
        "--owner-ref",
        OWNER_REF,
        "--reason",
        "x",
        "--apply",
    )
    run(sandbox, capsys, "transition", "00", "IN_PROGRESS", "--actor", "engineering-agent", "--reason", "x", "--apply")
    sandbox.write("impl.txt", "x\n")
    rev = sandbox.commit("impl")
    run(
        sandbox,
        capsys,
        "transition",
        "00",
        "IMPLEMENTED_NOT_VERIFIED",
        "--actor",
        "engineering-agent",
        "--reason",
        "x",
        "--revision",
        rev,
        "--apply",
    )
    sandbox.write_evidence("00", rev)
    code, out = run(sandbox, capsys, "readiness", "00")
    assert code == 0 and "READY" in out
    record = tmp_path / "record.json"
    record.write_text(json.dumps({"gates": sandbox.gates("00"), "ci": sandbox.ci(rev)}), encoding="utf-8")
    code, out = run(
        sandbox,
        capsys,
        "transition",
        "00",
        "VERIFIED_AWAITING_OWNER_ACCEPTANCE",
        "--actor",
        "engineering-agent",
        "--reason",
        "verified",
        "--record",
        str(record),
        "--apply",
    )
    assert code == 0, out
    code, out = run(sandbox, capsys, "handoff", "00")
    assert "Verified revision" in out and "00-P: pass" in out


@pytest.mark.negative
def test_readiness_reports_missing_evidence(sandbox: Sandbox, capsys: pytest.CaptureFixture[str]) -> None:
    code, out = run(sandbox, capsys, "readiness", "00")
    assert code == 1 and "NOT READY" in out and "EVIDENCE_MISSING" in out


def test_blocker_commands(sandbox: Sandbox, capsys: pytest.CaptureFixture[str]) -> None:
    code, out = run(sandbox, capsys, "blocker", "add", "00", "waiting for access")
    assert code == 0 and "B-00-001" in out
    code, out = run(sandbox, capsys, "blocker", "resolve", "00", "access granted", "--id", "B-00-001")
    assert code == 0
    code, out = run(sandbox, capsys, "blocker", "resolve", "00", "again", "--id", "B-00-001")
    assert code == 1 and "BLOCKER_UNKNOWN" in out
    assert main(["--root", str(sandbox.root), "blocker", "resolve", "00", "x"]) == 2


@pytest.mark.negative
def test_amend_requires_accepted_stage(sandbox: Sandbox, capsys: pytest.CaptureFixture[str]) -> None:
    code, out = run(
        sandbox,
        capsys,
        "amend",
        "00",
        "--kind",
        "correction",
        "--reason",
        "a reason here",
        "--evidence",
        "RISKS.md",
        "--owner-ref",
        OWNER_REF,
    )
    assert code == 1 and "AMENDMENT_NOT_APPLICABLE" in out


@pytest.mark.negative
def test_missing_registry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["status"]) == 2


@pytest.mark.negative
def test_bad_gate_syntax(sandbox: Sandbox) -> None:
    with pytest.raises(SystemExit):
        main(
            [
                "--root",
                str(sandbox.root),
                "transition",
                "00",
                "AUTHORIZED",
                "--actor",
                "owner",
                "--reason",
                "x",
                "--gate",
                "00-A",
            ]
        )
