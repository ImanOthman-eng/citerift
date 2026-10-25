"""Regression tests for the Stage 00 corrective amendment A-00-001.

Each test reproduces one finding of the independent review
(docs/audits/stage-00-2026-10-25/independent-review.md) in a sandbox
repository. Every test here failed on the revision the finding was reported
against, and passes with the correction.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from sandbox_repo import FILLER, REPO, Sandbox, git

from citerift.governance import evidence
from citerift.governance.model import Actor, Status
from citerift.governance.orchestrator import Orchestrator, errors

pytestmark = [pytest.mark.regression, pytest.mark.security]

OWNED_FILE = "src/citerift/governance/owned_module.py"


@pytest.mark.integration
def test_f01_merge_restoring_old_owned_content_is_stale(sandbox: Sandbox) -> None:
    """F-01: a merge that is TREESAME to an old parent hides the change from ``git log -- paths``."""
    sandbox.write(OWNED_FILE, "version = 0\n")
    old = sandbox.commit("owned code, first version")
    sandbox.write(OWNED_FILE, "version = 1\ntests = 'many'\n")
    sandbox.commit("owned code, second version")
    sandbox.drive_to_verified("00")
    assert not errors(sandbox.orc().check())

    git(sandbox.root, "checkout", "-q", "-b", "old", old)
    sandbox.write("side-note.txt", "unrelated\n")
    sandbox.commit("unrelated side commit")
    git(sandbox.root, "checkout", "-q", "main")
    git(sandbox.root, "merge", "-q", "--no-ff", "--no-commit", "-s", "ours", "old")
    git(sandbox.root, "checkout", "old", "--", "src/citerift/governance", "side-note.txt")
    sandbox.commit("Merge branch old")

    # The bypass: history simplification attributes the owned content to an ancestor of the verified revision.
    assert git(sandbox.root, "log", "-1", "--format=%H", "--", "src/citerift/governance") == old
    findings = sandbox.orc().check()
    stale = [f for f in findings if f.code == "VERIFICATION_STALE"]
    assert stale, [str(f) for f in findings]
    assert OWNED_FILE in stale[0].message


@pytest.mark.integration
def test_f01_content_identical_to_verified_revision_is_not_stale(sandbox: Sandbox) -> None:
    """Touching owned paths without changing their content (a revert pair) is not drift."""
    sandbox.write(OWNED_FILE, "version = 1\n")
    sandbox.commit("owned code")
    sandbox.drive_to_verified("00")
    sandbox.write(OWNED_FILE, "version = 2\n")
    sandbox.commit("change")
    assert "VERIFICATION_STALE" in sandbox.codes(sandbox.orc().check())
    sandbox.write(OWNED_FILE, "version = 1\n")
    sandbox.commit("revert the change")
    assert not errors(sandbox.orc().check())


@pytest.mark.integration
def test_f19_uncommitted_owned_change_is_reported(sandbox: Sandbox) -> None:
    sandbox.drive_to_verified("00")
    sandbox.write(OWNED_FILE, "edited but not committed\n")
    findings = sandbox.orc().check()
    assert "UNCOMMITTED_OWNED_CHANGE" in sandbox.codes(findings, "warning")
    assert not errors(findings), "an uncommitted edit is not yet drift"
    sandbox.write("notes.txt", "not owned\n")
    (sandbox.root / OWNED_FILE).unlink()
    assert "UNCOMMITTED_OWNED_CHANGE" not in sandbox.codes(sandbox.orc().check(), "warning")


# ------------------------------------------------------------------ F-02


@pytest.mark.integration
@pytest.mark.parametrize(
    ("edit", "code"),
    [
        ("change", "EVIDENCE_STALE"),
        ("delete", "EVIDENCE_MISSING"),
        ("add", "EVIDENCE_UNLISTED"),
    ],
)
def test_f02_every_file_in_the_evidence_directory_is_pinned(sandbox: Sandbox, edit: str, code: str) -> None:
    sandbox.write("docs/verification/stage-00/simulation/results.json", '{"survived": 0}\n')
    sandbox.commit("supporting evidence")
    sandbox.drive_to_verified("00")
    assert not errors(sandbox.orc().check())
    target = sandbox.root / "docs/verification/stage-00/simulation/results.json"
    if edit == "change":
        target.write_text('{"survived": 3}\n', encoding="utf-8")
    elif edit == "delete":
        target.unlink()
    else:
        sandbox.write("docs/verification/stage-00/forged-results.txt", "all mutants killed\n")
    sandbox.commit(f"{edit} evidence after verification")
    assert code in sandbox.codes(sandbox.orc().check())


@pytest.mark.integration
@pytest.mark.parametrize(
    ("refs", "code"),
    [
        (["."], "GATE_EVIDENCE_MISSING"),
        (["RISKS.md"], "GATE_EVIDENCE_UNPINNED"),
        (["https://example.invalid/anything"], "GATE_EVIDENCE_UNPINNED"),
        (["docs/verification/stage-00/HANDOFF.md", "RISKS.md"], "GATE_EVIDENCE_UNPINNED"),
    ],
    ids=["dot", "unpinned_file", "url_only", "pinned_plus_unpinned"],
)
def test_f02_gate_evidence_must_be_a_pinned_file(sandbox: Sandbox, refs: list[str], code: str) -> None:
    """F-02; the last two cases are V-02 of the final independent review (a URL or one pinned file sufficed)."""
    for target in ("AUTHORIZED", "IN_PROGRESS"):
        assert sandbox.go("00", Status(target)).allowed
    rev = sandbox.commit("implement")
    assert sandbox.go("00", Status.IMPLEMENTED_NOT_VERIFIED, revision=rev).allowed
    sandbox.write_evidence("00", rev)
    gates = {gid: {"result": "pass", "evidence": refs} for gid in sandbox.gates("00")}
    result = sandbox.go("00", Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE, gates=gates, ci=sandbox.ci(rev))
    assert not result.allowed
    assert code in sandbox.codes(result.findings)


@pytest.mark.integration
def test_v02_owned_file_and_url_are_accepted_as_gate_evidence(sandbox: Sandbox) -> None:
    """An owned-path file is pinned by the drift check, so it counts; a URL may be cited next to a pinned file."""
    sandbox.write(OWNED_FILE, "version = 1\n")
    for target in ("AUTHORIZED", "IN_PROGRESS"):
        assert sandbox.go("00", Status(target)).allowed
    rev = sandbox.commit("implement")
    assert sandbox.go("00", Status.IMPLEMENTED_NOT_VERIFIED, revision=rev).allowed
    sandbox.write_evidence("00", rev)
    gates = {
        gid: {"result": "pass", "evidence": [OWNED_FILE, "https://example.invalid/run/1"]}
        for gid in sandbox.gates("00")
    }
    result = sandbox.go("00", Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE, gates=gates, ci=sandbox.ci(rev))
    assert result.allowed, [str(f) for f in result.findings]


# ------------------------------------------------------------------ F-03


def _edit_registry(sandbox: Sandbox, name: str) -> None:
    """The four registry edits of docs/audits/stage-00-2026-10-25/scripts/policy_edit.py, plus the policy flag."""
    reg = sandbox.registry()
    s0 = reg["stages"][0]
    if name == "gate_dot":
        for g in s0["verification"]["gates"].values():
            g["evidence"] = ["."]
    elif name == "drop_ci":
        s0["ci_required"] = False
        del s0["verification"]["ci"]
    elif name == "shrink_gates":
        s0["acceptance_gates"] = s0["acceptance_gates"][:1]
        s0["verification"]["gates"] = {"00-A": s0["verification"]["gates"]["00-A"]}
        s0["required_test_suites"] = ["unit"]
        reg["policy"]["handoff_required_sections"] = []
    elif name == "shrink_gates_keep_policy":
        s0["acceptance_gates"] = s0["acceptance_gates"][:1]
        s0["verification"]["gates"] = {"00-A": s0["verification"]["gates"]["00-A"]}
        s0["required_test_suites"] = ["unit"]
    elif name == "drop_owned_paths":
        s0["owned_paths"] = []
    elif name == "single_active_off":
        reg["policy"]["single_active_engineering_stage"] = False
    elif name == "fewer_artifacts":
        s0["required_artifacts"] = ["HANDOFF.md"]
    sandbox.save_registry(reg)


@pytest.mark.integration
@pytest.mark.parametrize(
    "name",
    [
        "gate_dot",
        "drop_ci",
        "shrink_gates",
        "shrink_gates_keep_policy",
        "drop_owned_paths",
        "single_active_off",
        "fewer_artifacts",
    ],
)
def test_f03_weakening_the_rules_in_the_registry_is_an_error(sandbox: Sandbox, name: str) -> None:
    sandbox.drive_to_verified("00")
    assert not errors(sandbox.orc().check())
    _edit_registry(sandbox, name)
    found = errors(sandbox.orc().check())
    assert found, f"{name} was accepted"
    assert {f.code for f in found} & {"REGISTRY_SCHEMA", "DEFINITION_CHANGED", "GATE_EVIDENCE_MISSING"}


@pytest.mark.negative
@pytest.mark.parametrize(
    "edit",
    ["single_active_off", "fewer_artifacts_policy", "no_handoff_sections", "other_report_file", "ci_not_required"],
)
def test_f03_policy_is_fixed_by_the_schema_before_any_verification(sandbox: Sandbox, edit: str) -> None:
    """Without a verification there is no definition hash yet; the schema alone must refuse the weakening.

    Found by mutant M33 of the correction's mutation check, which survived before this test existed.
    """
    assert sandbox.go("00", Status.AUTHORIZED).allowed
    reg = sandbox.registry()
    policy = reg["policy"]
    if edit == "single_active_off":
        policy["single_active_engineering_stage"] = False
    elif edit == "fewer_artifacts_policy":
        policy["required_artifacts"] = policy["required_artifacts"][:1]
    elif edit == "no_handoff_sections":
        policy["handoff_required_sections"] = []
    elif edit == "other_report_file":
        policy["test_report_file"] = "partial-report.json"
    else:
        reg["stages"][2]["ci_required"] = False
    sandbox.save_registry(reg)
    assert sandbox.codes(sandbox.orc().check()) == {"REGISTRY_SCHEMA"}


@pytest.mark.negative
@pytest.mark.parametrize(
    "edit",
    ["no_artifacts_override", "fewer_artifacts_override", "engineering_stage_as_external", "stage01_as_engineering"],
)
def test_v03_stage_overrides_cannot_weaken_the_policy_before_verification(sandbox: Sandbox, edit: str) -> None:
    """V-03 (final independent review): a stage-level artifact list or a changed executor bypassed the fixed policy."""
    reg = sandbox.registry()
    s00, s01, s02 = reg["stages"][0], reg["stages"][1], reg["stages"][2]
    if edit == "no_artifacts_override":
        s00["required_artifacts"] = []
    elif edit == "fewer_artifacts_override":
        s02["required_artifacts"] = ["HANDOFF.md"]
    elif edit == "engineering_stage_as_external":
        s02["executor"] = "external-agent"
        s02["ci_required"] = False
    else:
        s01["executor"] = "engineering-agent"
        s01["ci_required"] = True
    sandbox.save_registry(reg)
    assert "REGISTRY_SCHEMA" in sandbox.codes(sandbox.orc().check())


@pytest.mark.integration
def test_v03_handoff_is_required_even_if_a_stage_lists_other_artifacts(sandbox: Sandbox) -> None:
    reg = sandbox.registry()
    reg["stages"][1]["required_artifacts"] = ["NOTES.md"]
    sandbox.save_registry(reg)
    sandbox.commit("external stage lists its own artifact")
    assert sandbox.go("01", Status.AUTHORIZED).allowed
    assert sandbox.go("01", Status.IN_PROGRESS).allowed
    rev = sandbox.commit("feasibility work")
    assert sandbox.go("01", Status.IMPLEMENTED_NOT_VERIFIED, revision=rev).allowed
    sandbox.write("docs/verification/stage-01/NOTES.md", FILLER * 3)
    notes = "docs/verification/stage-01/NOTES.md"
    gates = {gid: {"result": "pass", "evidence": [notes]} for gid in sandbox.gates("01")}
    result = sandbox.go("01", Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE, gates=gates)
    assert not result.allowed
    assert "docs/verification/stage-01/HANDOFF.md" in " ".join(str(f) for f in result.findings)


@pytest.mark.integration
def test_v03_engineering_stage_with_an_empty_definition_cannot_be_verified(sandbox: Sandbox) -> None:
    """DEFINITION_WEAK had no test (hand mutant H12 survived)."""
    sandbox.drive_to_accepted("00")
    sandbox.drive_to_accepted("01")
    assert sandbox.go("02", Status.AUTHORIZED).allowed
    assert sandbox.go("02", Status.IN_PROGRESS).allowed
    sandbox.write("impl/02.txt", "stage 02\n")
    rev = sandbox.commit("stage 02 work")
    assert sandbox.go("02", Status.IMPLEMENTED_NOT_VERIFIED, revision=rev).allowed
    sandbox.write_evidence("02", rev)
    result = sandbox.go("02", Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE, gates=sandbox.gates("02"), ci=sandbox.ci(rev))
    assert not result.allowed
    assert "DEFINITION_WEAK" in sandbox.codes(result.findings)


# ------------------------------------------------------------------ F-07


def _plugin_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    (project / "tests").mkdir(parents=True)
    (project / "pyproject.toml").write_text('[tool.pytest.ini_options]\ntestpaths = ["tests"]\n', encoding="utf-8")
    (project / "tests" / "test_sample.py").write_text(
        "import pytest\n\n"
        "@pytest.mark.unit\ndef test_alpha():\n    pass\n\n"
        "@pytest.mark.unit\ndef test_beta():\n    pass\n\n"
        "@pytest.mark.negative\ndef test_gamma():\n    pass\n",
        encoding="utf-8",
    )
    (project / "tests" / "test_other.py").write_text(
        "import pytest\n\n@pytest.mark.unit\ndef test_delta():\n    pass\n", encoding="utf-8"
    )
    (project / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
    git(project, "init", "-q")
    git(project, "add", "-A")
    git(project, "commit", "-q", "-m", "init")
    return project


def _run_plugin(project: Path, report: Path, *args: str) -> tuple[int, dict[str, Any], str]:
    out = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-p",
            "citerift.governance.pytest_report",
            "--citerift-report",
            str(report),
            *args,
        ],
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
    )
    data = json.loads(report.read_text(encoding="utf-8")) if report.exists() else {}
    return out.returncode, data, out.stdout + out.stderr


@pytest.mark.integration
@pytest.mark.parametrize(
    "args",
    [
        ["-k", "alpha"],
        ["-m", "unit"],
        ["tests/test_sample.py::test_alpha"],
        ["--deselect", "tests/test_sample.py::test_beta"],
        ["--ignore", "tests/test_sample.py", "tests"],
    ],
    ids=["keyword", "marker", "node_id", "deselect", "ignore"],
)
def test_f07_partial_runs_are_recorded_as_partial(tmp_path: Path, args: list[str]) -> None:
    project = _plugin_project(tmp_path)
    reports = tmp_path / "reports"
    reports.mkdir()
    code, data, output = _run_plugin(project, reports / "full.json")
    assert code == 0 and data["selection"]["complete"] is True, output
    _, data, output = _run_plugin(project, reports / "partial.json", *args)
    assert data["selection"]["complete"] is False, output
    for name in ("full.json", "partial.json"):
        shutil.copy(reports / name, project / name)
    head = git(project, "rev-parse", "HEAD")
    assert evidence.check_test_report(project, "full.json", None, head, ["unit", "negative"]) == []
    partial = evidence.check_test_report(project, "partial.json", None, head, ["unit"])
    assert "TEST_EVIDENCE_PARTIAL" in {p.code for p in partial}


@pytest.mark.integration
def test_f07_run_stopped_early_is_partial(tmp_path: Path) -> None:
    project = _plugin_project(tmp_path)
    (project / "tests" / "test_sample.py").write_text(
        (project / "tests" / "test_sample.py")
        .read_text(encoding="utf-8")
        .replace("def test_alpha():\n    pass", "def test_alpha():\n    assert False"),
        encoding="utf-8",
    )
    _, data, _ = _run_plugin(project, project / "r.json", "-x")
    assert data["totals"].get("not_run") == 2
    assert data["selection"]["complete"] is False


@pytest.mark.integration
@pytest.mark.parametrize(
    ("conftest", "args"),
    [
        (None, ["-o", "python_files=test_sample.py"]),
        (None, ["-o", "testpaths=tests/test_sample.py"]),
        (None, ["-c", "other.ini"]),
        ("def pytest_collection_modifyitems(items):\n    items[:] = items[:1]\n", []),
        ("collect_ignore = ['test_other.py']\n", []),
    ],
    ids=["override_python_files", "override_testpaths", "other_ini_file", "conftest_drops_items", "collect_ignore"],
)
def test_v01_narrowing_by_configuration_or_conftest_is_partial(
    tmp_path: Path, conftest: str | None, args: list[str]
) -> None:
    """V-01 (final independent review): ini overrides and a committed conftest still gave a "complete" partial run."""
    project = _plugin_project(tmp_path)
    (project / "other.ini").write_text("[pytest]\ntestpaths = tests/test_sample.py\n", encoding="utf-8")
    if conftest is not None:
        (project / "tests" / "conftest.py").write_text(conftest, encoding="utf-8")
    git(project, "add", "-A")
    git(project, "commit", "-q", "-m", "narrowing")
    reports = tmp_path / "reports"
    reports.mkdir()
    code, data, output = _run_plugin(project, reports / "r.json", *args)
    assert code == 0 and data["totals"]["passed"] < 4, output
    shutil.copy(reports / "r.json", project / "r.json")
    head = git(project, "rev-parse", "HEAD")
    problems = evidence.check_test_report(project, "r.json", None, head, ["unit"])
    assert "TEST_EVIDENCE_PARTIAL" in {p.code for p in problems}, (data["selection"], problems)


@pytest.mark.integration
def test_v01_strict_markers_keeps_the_run_complete(tmp_path: Path) -> None:
    project = _plugin_project(tmp_path)
    code, data, output = _run_plugin(project, tmp_path / "r.json", "--strict-markers")
    assert code == 0 and data["selection"]["complete"] is True, output
    shutil.copy(tmp_path / "r.json", project / "r.json")
    head = git(project, "rev-parse", "HEAD")
    assert evidence.check_test_report(project, "r.json", None, head, ["unit", "negative"]) == []


@pytest.mark.negative
def test_v16_report_into_a_new_directory_is_written(tmp_path: Path) -> None:
    project = _plugin_project(tmp_path)
    target = tmp_path / "not-yet" / "there" / "report.json"
    code, data, output = _run_plugin(project, target)
    assert code == 0 and "Traceback" not in output, output
    assert data["selection"]["complete"] is True


# ------------------------------------------------------------------ F-14


@pytest.mark.negative
def test_f14_report_outside_the_repository_is_written(tmp_path: Path) -> None:
    project = _plugin_project(tmp_path)
    outside = tmp_path / "elsewhere" / "report.json"
    outside.parent.mkdir()
    code, data, output = _run_plugin(project, outside)
    assert code == 0, output
    assert "INTERNALERROR" not in output
    assert data["dirty"] is False and data["selection"]["complete"] is True


# ------------------------------------------------------------------ F-12


@pytest.mark.reproducibility
@pytest.mark.parametrize("with_attributes", [True, False])
def test_f12_crlf_checkout_does_not_change_evidence_hashes(
    sandbox: Sandbox, tmp_path: Path, with_attributes: bool
) -> None:
    if with_attributes:
        shutil.copy(REPO / ".gitattributes", sandbox.root / ".gitattributes")
        sandbox.commit("line endings")
    sandbox.drive_to_verified("00")
    clone = tmp_path / "crlf-clone"
    subprocess.run(
        [
            "git",
            "-c",
            "core.autocrlf=true",
            "clone",
            "-q",
            "--config",
            "core.autocrlf=true",
            str(sandbox.root),
            str(clone),
        ],
        check=True,
        capture_output=True,
    )
    codes = {f.code for f in errors(Orchestrator(clone).check())}
    if with_attributes:
        assert codes == set()
    else:
        assert "EVIDENCE_STALE" in codes, "control: without .gitattributes the CRLF checkout changes hashes"


# ------------------------------------------------------------- F-04, F-05


def _append_history(sandbox: Sandbox, sid: str, source: str, target: str, actor: str, **extra: Any) -> dict[str, Any]:
    reg = sandbox.registry()
    entry = {
        "seq": len(reg["history"]) + 1,
        "at": sandbox.tick(),
        "stage": sid,
        "from": source,
        "to": target,
        "actor": actor,
        "recorded_by": "engineering-agent",
        "reason": "hand edit",
        "owner_ref": extra.pop("owner_ref", None),
        **extra,
    }
    reg["history"].append(entry)
    sandbox.save_registry(reg)
    return entry


@pytest.mark.integration
def test_f04_history_with_a_past_second_active_stage_is_an_error(sandbox: Sandbox) -> None:
    """Two engineering stages were active at once, then one was withdrawn: the current state looks fine."""
    sandbox.drive_to_accepted("00")
    sandbox.drive_to_accepted("01")
    assert sandbox.go("02", Status.AUTHORIZED).allowed
    assert not errors(sandbox.orc().check(include_status_doc=False))
    _append_history(sandbox, "03", "NOT_STARTED", "AUTHORIZED", "owner", owner_ref="cmsg_HANDEDITREF0001")
    _append_history(sandbox, "03", "AUTHORIZED", "NOT_STARTED", "owner", owner_ref="cmsg_HANDEDITREF0002")
    codes = sandbox.codes(sandbox.orc().check(include_status_doc=False))
    assert codes == {"HISTORY_SINGLE_ACTIVE"}, codes


@pytest.mark.integration
def test_f04_history_with_a_past_dependency_violation_is_an_error(sandbox: Sandbox) -> None:
    sandbox.drive_to_accepted("01")
    _append_history(sandbox, "02", "NOT_STARTED", "AUTHORIZED", "owner", owner_ref="cmsg_HANDEDITREF0001")
    _append_history(sandbox, "02", "AUTHORIZED", "NOT_STARTED", "owner", owner_ref="cmsg_HANDEDITREF0002")
    codes = sandbox.codes(sandbox.orc().check(include_status_doc=False))
    assert codes == {"HISTORY_DEPENDENCY"}, codes


@pytest.mark.integration
def test_f05_reopening_without_a_correction_amendment_is_an_error(sandbox: Sandbox) -> None:
    sandbox.drive_to_accepted("00")
    _append_history(sandbox, "00", "ACCEPTED_CLOSED", "IN_PROGRESS", "owner", owner_ref="cmsg_HANDEDITREF0001")
    reg = sandbox.registry()
    reg["stages"][0].update(status="IN_PROGRESS", implementation=None, verification=None, acceptance=None)
    sandbox.save_registry(reg)
    codes = sandbox.codes(sandbox.orc().check(include_status_doc=False))
    assert codes == {"HISTORY_AMENDMENT_MISSING"}, codes


@pytest.mark.integration
def test_f05_starting_work_with_an_open_blocker_is_an_error(sandbox: Sandbox) -> None:
    assert sandbox.go("00", Status.AUTHORIZED).allowed
    sandbox.orc().add_blocker("00", "waiting for the owner", at=sandbox.tick())
    refused = sandbox.go("00", Status.IN_PROGRESS)
    assert not refused.allowed and "BLOCKER_OPEN" in sandbox.codes(refused.findings)
    _append_history(sandbox, "00", "AUTHORIZED", "IN_PROGRESS", "engineering-agent")
    reg = sandbox.registry()
    reg["stages"][0]["status"] = "IN_PROGRESS"
    sandbox.save_registry(reg)
    codes = sandbox.codes(sandbox.orc().check(include_status_doc=False))
    assert codes == {"HISTORY_BLOCKER"}, codes


@pytest.mark.integration
def test_f05_blocking_without_a_blocker_is_an_error_in_history(sandbox: Sandbox) -> None:
    for target in (Status.AUTHORIZED, Status.IN_PROGRESS):
        assert sandbox.go("00", target).allowed
    bid = sandbox.orc().add_blocker("00", "real blocker", at=sandbox.tick())
    assert sandbox.go("00", Status.BLOCKED).allowed
    assert sandbox.orc().resolve_blocker("00", bid, "done", at=sandbox.tick())
    assert not errors(sandbox.orc().check(include_status_doc=False))
    _append_history(sandbox, "00", "IN_PROGRESS", "BLOCKED", "engineering-agent")
    _append_history(sandbox, "00", "BLOCKED", "IN_PROGRESS", "engineering-agent")
    assert sandbox.codes(sandbox.orc().check(include_status_doc=False)) == {"HISTORY_BLOCKER"}


# ------------------------------------------------------------------ F-11


@pytest.mark.integration
def test_f11_foundation_can_be_reopened_after_a_dependent_was_accepted(sandbox: Sandbox) -> None:
    reg = sandbox.registry()
    reg["stages"][2]["owned_paths"] = ["impl/02.txt"]  # defined when a stage is authorized
    sandbox.save_registry(reg)
    sandbox.commit("define stage 02 paths")
    for sid in ("00", "01", "02"):
        sandbox.drive_to_accepted(sid)
    aid = sandbox.orc().add_amendment(
        "00",
        kind="correction",
        reason="foundation defect found after stage 02 was accepted",
        evidence_refs=["RISKS.md"],
        owner_ref="cmsg_TESTREOPENREF01",
        at=sandbox.tick(),
    )
    reopened = sandbox.go("00", Status.IN_PROGRESS, actor=Actor.OWNER, amendment=aid, owner_ref="cmsg_TESTREOPENREF01")
    assert reopened.allowed, [str(f) for f in reopened.findings]
    findings = sandbox.orc().check(include_status_doc=False)
    assert not errors(findings)
    assert "DEPENDENCY_REOPENED" in sandbox.codes(findings, "warning")
    # A dependent cannot be verified or accepted on top of the reopened foundation.
    assert sandbox.go("03", Status.AUTHORIZED).allowed is False
    sandbox.write("impl/00.txt", "corrected\n")
    rev = sandbox.commit("correct 00")
    assert sandbox.go("00", Status.IMPLEMENTED_NOT_VERIFIED, revision=rev).allowed
    sandbox.write_evidence("00", rev)
    gates, ci = sandbox.gates("00"), sandbox.ci(rev)
    assert sandbox.go("00", Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE, gates=gates, ci=ci).allowed
    assert sandbox.go("00", Status.ACCEPTED_CLOSED).allowed
    final = sandbox.orc().check(include_status_doc=False)
    assert not errors(final) and "DEPENDENCY_REOPENED" not in sandbox.codes(final, "warning")


def _reopen_and_reverify(sandbox: Sandbox, *, amendment_ref: str, reopen_ref: str) -> tuple[str, str]:
    """Accepted Stage 00 -> correction amendment -> reopen -> re-verify. Returns (amendment id, revision)."""
    aid = sandbox.orc().add_amendment(
        "00",
        kind="correction",
        reason="defect found by an independent review",
        evidence_refs=["RISKS.md"],
        owner_ref=amendment_ref,
        at=sandbox.tick(),
    )
    assert sandbox.go("00", Status.IN_PROGRESS, actor=Actor.OWNER, amendment=aid, owner_ref=reopen_ref).allowed
    sandbox.write("impl/00.txt", f"corrected {sandbox.clock}\n")
    rev = sandbox.commit("correct 00")
    assert sandbox.go("00", Status.IMPLEMENTED_NOT_VERIFIED, revision=rev).allowed
    sandbox.write_evidence("00", rev)
    gates, ci = sandbox.gates("00"), sandbox.ci(rev)
    assert sandbox.go("00", Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE, gates=gates, ci=ci).allowed
    return aid, rev


@pytest.mark.integration
def test_v07_acceptance_cannot_cite_the_amendment_reference(sandbox: Sandbox) -> None:
    """V-07: the reuse rule searched history only; the amendment's reference predates the verification too."""
    sandbox.drive_to_accepted("00")
    _reopen_and_reverify(sandbox, amendment_ref="cmsg_TESTAMENDREF01", reopen_ref="cmsg_TESTREOPENREF02")
    reused = sandbox.go("00", Status.ACCEPTED_CLOSED, owner_ref="cmsg_TESTAMENDREF01")
    assert not reused.allowed and "OWNER_REF_REUSED" in sandbox.codes(reused.findings)
    assert sandbox.go("00", Status.ACCEPTED_CLOSED, owner_ref="cmsg_TESTNEWACCEPT02").allowed


@pytest.mark.integration
def test_v08_a_correction_amendment_justifies_one_reopening(sandbox: Sandbox) -> None:
    sandbox.drive_to_accepted("00")
    aid, _ = _reopen_and_reverify(sandbox, amendment_ref="cmsg_TESTAMENDREF01", reopen_ref="cmsg_TESTAMENDREF01")
    assert sandbox.go("00", Status.ACCEPTED_CLOSED, owner_ref="cmsg_TESTNEWACCEPT02").allowed
    again = sandbox.go("00", Status.IN_PROGRESS, actor=Actor.OWNER, amendment=aid, owner_ref="cmsg_TESTREOPENREF03")
    assert not again.allowed
    assert "HISTORY_AMENDMENT_REUSED" in sandbox.codes(again.findings)


@pytest.mark.negative
@pytest.mark.parametrize("kind", ["amendment", "blocker"])
def test_v09_duplicate_record_ids_are_errors(sandbox: Sandbox, kind: str) -> None:
    sandbox.drive_to_accepted("00")
    reg = sandbox.registry()
    s00 = reg["stages"][0]
    if kind == "amendment":
        record = {
            "id": "A-00-001",
            "kind": "correction",
            "reason": "defect found by an independent review",
            "evidence": ["RISKS.md"],
            "owner_ref": "cmsg_TESTAMENDREF01",
            "revision": None,
            "test_report": None,
            "recorded_at": reg["history"][-1]["at"],
        }
        s00["amendments"] = [record, {**record, "kind": "enhancement"}]
        code = "AMENDMENT_DUPLICATE_ID"
    else:
        blocker = {
            "id": "B-00-001",
            "description": "d",
            "opened_at": reg["history"][0]["at"],
            "resolved_at": reg["history"][1]["at"],
            "resolution": "done",
        }
        s00["blockers"] = [blocker, dict(blocker)]
        code = "BLOCKER_DUPLICATE_ID"
    sandbox.save_registry(reg)
    assert code in sandbox.codes(sandbox.orc().check())


@pytest.mark.integration
def test_v05_a_correction_test_report_is_not_exempt_from_the_manifest(sandbox: Sandbox) -> None:
    """V-05: naming any file as an amendment test report exempted it from the evidence manifest."""
    sandbox.drive_to_accepted("00")
    late = "docs/verification/stage-00/late-evidence.md"
    sandbox.write(late, "added after verification\n")
    sandbox.orc().add_amendment(
        "00",
        kind="correction",
        reason="defect found by an independent review",
        evidence_refs=["RISKS.md"],
        owner_ref="cmsg_TESTAMENDREF01",
        test_report=late,
        at=sandbox.tick(),
    )
    assert "EVIDENCE_UNLISTED" in sandbox.codes(sandbox.orc().check())


# ------------------------------------------------------------------ F-06

CRITICAL = (
    "\n## R-{id} {dash} Critical defect\n- Status: open\n- Severity: critical\n- Kind: defect\n"
    "- Stage: {stage}\n\nBody.\n"
)


@pytest.mark.integration
@pytest.mark.parametrize(
    ("heading_dash", "stage", "extra", "code"),
    [
        ("-", "00", "", "MEMORY_MALFORMED"),
        ("–", "00", "", "MEMORY_MALFORMED"),
        ("—", "project", "", "OPEN_CRITICAL_DEFECT"),
        ("—", "00", "- Status: closed\n", "MEMORY_MALFORMED"),
    ],
    ids=["ascii_hyphen", "en_dash", "project_scope", "duplicate_field"],
)
def test_f06_malformed_or_project_wide_defects_fail_closed(
    sandbox: Sandbox, heading_dash: str, stage: str, extra: str, code: str
) -> None:
    sandbox.drive_to_verified("00")
    entry = CRITICAL.format(id="016", dash=heading_dash, stage=stage).replace("\n\nBody.", f"\n{extra}\nBody.")
    sandbox.write("RISKS.md", (sandbox.root / "RISKS.md").read_text(encoding="utf-8") + entry)
    assert code in sandbox.codes(sandbox.orc().check())


@pytest.mark.negative
def test_f06_heading_level_and_topic_case(tmp_path: Path) -> None:
    from citerift.governance import memory

    risks = tmp_path / "RISKS.md"
    risks.write_text("# Risks\n\n### R-001 — Wrong level\n- Status: open\n", encoding="utf-8")
    assert {p.code for p in memory.check_risks(risks)[1]} == {"MEMORY_MALFORMED"}
    decisions = tmp_path / "DECISIONS.md"
    body = "- Status: accepted\n- Topic: {topic}\n- Date: 2026-10-25\n- Stage: 00\n- Supersedes: none\n\nBody.\n"
    decisions.write_text(
        "# Decisions\n\n## D-001 — One\n"
        + body.format(topic="python-version")
        + "\n## D-002 — Two\n"
        + body.format(topic=" Python-Version "),
        encoding="utf-8",
    )
    assert "DECISION_CONTRADICTION" in {p.code for p in memory.check_decisions(decisions)[1]}


FIELDS = "- Status: open\n- Severity: critical\n- Kind: defect\n- Stage: 00\n\nBody.\n"


@pytest.mark.negative
@pytest.mark.parametrize(
    "heading",
    [
        "## R\u2013016 \u2014 Critical defect\n",
        "## R\u2011016 \u2014 Critical defect\n",
        "## R_016 \u2014 Critical defect\n",
        "## \uff32-016 \u2014 Critical defect\n",
        "## R016 \u2014 Critical defect\n",
        "R-016 \u2014 Critical defect\n-----------------------\n",
        "<h2>R-016 \u2014 Critical defect</h2>\n",
    ],
    ids=["en_dash_in_id", "non_breaking_hyphen", "underscore", "fullwidth_letter", "no_hyphen", "setext", "html"],
)
def test_v06_any_unparsed_entry_is_malformed(tmp_path: Path, heading: str) -> None:
    """V-06 (final independent review): these headings were skipped, hiding an open critical defect."""
    from citerift.governance import memory

    risks = tmp_path / "RISKS.md"
    risks.write_text("# Risks\n\n" + heading + FIELDS, encoding="utf-8")
    assert "MEMORY_MALFORMED" in {p.code for p in memory.check_risks(risks)[1]}


@pytest.mark.negative
@pytest.mark.parametrize("other", ["python version", "Python\u2011version", "\uff50ython-version", "python_version"])
def test_v06_topic_spelling_variants_are_one_topic(tmp_path: Path, other: str) -> None:
    from citerift.governance import memory

    decisions = tmp_path / "DECISIONS.md"
    body = "- Status: accepted\n- Topic: {topic}\n- Date: 2026-10-25\n- Stage: 00\n- Supersedes: none\n\nBody.\n"
    decisions.write_text(
        "# Decisions\n\n## D-001 \u2014 One\n"
        + body.format(topic="python-version")
        + "\n## D-002 \u2014 Two\n"
        + body.format(topic=other),
        encoding="utf-8",
    )
    assert "DECISION_CONTRADICTION" in {p.code for p in memory.check_decisions(decisions)[1]}


# ------------------------------------------------------------- F-13, F-18


@pytest.mark.negative
@pytest.mark.parametrize(
    "damage",
    ['{"registry_version": ', '{"registry_version": "1.0.0", "registry_version": "1.0.0"}', None],
    ids=["truncated", "duplicate_key", "missing"],
)
def test_f13_f18_unreadable_registry_is_reported_not_crashed(sandbox: Sandbox, damage: str | None) -> None:
    path = sandbox.root / "governance/stage_registry.json"
    if damage is None:
        path.unlink()
    else:
        path.write_text(damage, encoding="utf-8")
    for command in ("check", "recover"):
        out = subprocess.run(
            [sys.executable, "-m", "citerift.governance.cli", "--root", str(sandbox.root), command],
            capture_output=True,
            text=True,
            check=False,
        )
        assert out.returncode == 1, out.stdout + out.stderr
        assert "Traceback" not in out.stderr
        assert "REGISTRY_UNREADABLE" in out.stdout
    assert "HEAD:" in out.stdout


@pytest.mark.negative
@pytest.mark.parametrize(
    ("damage", "command"),
    [
        ("schema_missing", "check"),
        ("schema_truncated", "recover"),
        ("registry_empty_object", "recover"),
        ("registry_empty_object", "status"),
        ("risks_not_utf8", "check"),
    ],
)
def test_v10_damaged_inputs_are_reported_not_crashed(sandbox: Sandbox, damage: str, command: str) -> None:
    """V-10 (final independent review): residual tracebacks of F-13."""
    root = sandbox.root
    if damage == "schema_missing":
        (root / "schemas/governance/stage_registry.schema.json").unlink()
    elif damage == "schema_truncated":
        path = root / "schemas/governance/stage_registry.schema.json"
        path.write_text(path.read_text(encoding="utf-8")[:100], encoding="utf-8")
    elif damage == "registry_empty_object":
        (root / "governance/stage_registry.json").write_text("{}\n", encoding="utf-8")
    else:
        with (root / "RISKS.md").open("ab") as fh:
            fh.write(b"\xff\n")
    out = subprocess.run(
        [sys.executable, "-m", "citerift.governance.cli", "--root", str(root), command],
        capture_output=True,
        text=True,
        check=False,
    )
    assert out.returncode == 1, out.stdout + out.stderr
    assert "Traceback" not in out.stderr, out.stderr
    assert "ERROR" in out.stdout


@pytest.mark.negative
def test_f18_duplicate_key_in_test_report_is_invalid(sandbox: Sandbox) -> None:
    sandbox.drive_to_verified("00")
    report = sandbox.root / "docs/verification/stage-00/test-report.json"
    text = report.read_text(encoding="utf-8")
    report.write_text(text.replace('"exit_status": 0', '"exit_status": 1, "exit_status": 0', 1), encoding="utf-8")
    assert "TEST_EVIDENCE_INVALID" in sandbox.codes(sandbox.orc().check())


# ------------------------------------------------------------------ F-15


@pytest.mark.integration
def test_f15_blocker_resolution_records_who_resolved_it(sandbox: Sandbox, capsys: pytest.CaptureFixture[str]) -> None:
    from citerift.governance.cli import main

    for target in (Status.AUTHORIZED, Status.IN_PROGRESS):
        assert sandbox.go("00", target).allowed
    bid = sandbox.orc().add_blocker("00", "needs an owner answer", at=sandbox.tick())
    assert sandbox.go("00", Status.BLOCKED).allowed
    root = ["--root", str(sandbox.root)]
    who = ["--actor", "owner", "--recorded-by", "engineering-agent", "--at", sandbox.tick()]
    code = main([*root, "blocker", "resolve", "00", "owner answered", "--id", bid, *who])
    assert code == 0, capsys.readouterr().out
    last = sandbox.registry()["history"][-1]
    assert (last["from"], last["to"], last["actor"], last["recorded_by"]) == (
        "BLOCKED",
        "IN_PROGRESS",
        "owner",
        "engineering-agent",
    )


# ------------------------------------------------------------------ F-16


@pytest.mark.negative
def test_f16_future_timestamps_are_refused_and_detected(sandbox: Sandbox) -> None:
    refused = sandbox.go("00", Status.AUTHORIZED, at="2099-01-01T00:00:00Z")
    assert not refused.allowed and "TIMESTAMP_IN_FUTURE" in sandbox.codes(refused.findings)
    assert sandbox.go("00", Status.AUTHORIZED).allowed
    reg = sandbox.registry()
    reg["history"][-1]["at"] = reg["stages"][0]["authorization"]["recorded_at"] = "2099-01-01T00:00:00Z"
    sandbox.save_registry(reg)
    assert "HISTORY_FUTURE_TIMESTAMP" in sandbox.codes(sandbox.orc().check())


@pytest.mark.integration
def test_v11_default_times_never_precede_the_last_entry(sandbox: Sandbox) -> None:
    """V-11: an entry dated up to 5 minutes ahead made the next blocker or transition fail on a correct clock."""
    from datetime import timedelta

    from citerift.governance.orchestrator import utc_now

    assert sandbox.go("00", Status.AUTHORIZED).allowed
    assert sandbox.go("00", Status.IN_PROGRESS, at=utc_now(timedelta(minutes=4))).allowed
    orc = sandbox.orc()
    orc.add_blocker("00", "waiting for an owner decision")
    result = Orchestrator(sandbox.root).propose("00", Status.BLOCKED, actor=Actor.ENGINEERING_AGENT, reason="blocked")
    assert result.allowed, [str(f) for f in result.findings]


@pytest.mark.negative
@pytest.mark.parametrize(("minutes", "allowed"), [(4, True), (6, False)])
def test_v15_clock_skew_bound_is_five_minutes(sandbox: Sandbox, minutes: int, allowed: bool) -> None:
    """Hand mutant H6 (bound widened) survived: only a year-2030 time was tested."""
    from datetime import timedelta

    from citerift.governance.orchestrator import utc_now

    result = sandbox.go("00", Status.AUTHORIZED, at=utc_now(timedelta(minutes=minutes)))
    assert result.allowed is allowed


# ------------------------------------------------------------------ F-17


@pytest.mark.integration
def test_f17_acceptance_must_cite_a_new_owner_statement(sandbox: Sandbox) -> None:
    sandbox.drive_to_verified("00")
    reused = sandbox.go("00", Status.ACCEPTED_CLOSED, owner_ref=sandbox.registry()["history"][0]["owner_ref"])
    assert not reused.allowed and "OWNER_REF_REUSED" in sandbox.codes(reused.findings)
    assert sandbox.go("00", Status.ACCEPTED_CLOSED, owner_ref="cmsg_TESTNEWACCEPT01").allowed


@pytest.mark.integration
def test_f17_record_times_must_match_history(sandbox: Sandbox) -> None:
    sandbox.drive_to_accepted("00")
    reg = sandbox.registry()
    reg["stages"][0]["acceptance"]["recorded_at"] = reg["stages"][0]["verification"]["recorded_at"]
    sandbox.save_registry(reg)
    assert "RECORD_HISTORY_MISMATCH" in sandbox.codes(sandbox.orc().check())


@pytest.mark.integration
def test_v12_nested_gitattributes_is_an_error(sandbox: Sandbox) -> None:
    """V-12: a nested .gitattributes outside the owned paths changed checkout bytes, so every clone saw stale hashes."""
    sandbox.write("docs/.gitattributes", "*.md text eol=crlf\n")
    sandbox.commit("nested attributes")
    assert "ATTRIBUTES_NESTED" in sandbox.codes(sandbox.orc().check())


@pytest.mark.integration
def test_v13_replace_refs_do_not_hide_drift(sandbox: Sandbox) -> None:
    """V-13: ``git replace`` made the verified commit look like HEAD's tree to ``git diff``."""
    verified = sandbox.drive_to_verified("00")
    sandbox.write(OWNED_FILE, "tampered = True\n")
    sandbox.commit("tamper with owned code")
    assert "VERIFICATION_STALE" in sandbox.codes(sandbox.orc().check())
    tree = git(sandbox.root, "rev-parse", "HEAD^{tree}")
    fake = git(sandbox.root, "commit-tree", tree, "-p", f"{verified}^", "-m", "fake")
    git(sandbox.root, "replace", verified, fake)
    assert "VERIFICATION_STALE" in sandbox.codes(sandbox.orc().check())


@pytest.mark.negative
def test_v15_amendment_recorded_after_the_reopening_is_an_error(sandbox: Sandbox) -> None:
    """Hand mutant H1 (amendment time not compared) survived."""
    sandbox.drive_to_accepted("00")
    aid = sandbox.orc().add_amendment(
        "00",
        kind="correction",
        reason="defect found by an independent review",
        evidence_refs=["RISKS.md"],
        owner_ref="cmsg_TESTAMENDREF01",
        at=sandbox.tick(),
    )
    assert sandbox.go(
        "00", Status.IN_PROGRESS, actor=Actor.OWNER, amendment=aid, owner_ref="cmsg_TESTAMENDREF01"
    ).allowed
    reg = sandbox.registry()
    reg["stages"][0]["amendments"][0]["recorded_at"] = sandbox.tick()
    sandbox.save_registry(reg)
    assert "HISTORY_AMENDMENT_MISSING" in sandbox.codes(sandbox.orc().check())


# ------------------------------------------------------------- F-20, F-23


@pytest.mark.integration
@pytest.mark.parametrize(
    "path", [".github/workflows/ci.yml", ".github/rulesets/main-protection.json", ".gitattributes"]
)
def test_f20_change_to_the_ci_definition_makes_stage00_stale(sandbox: Sandbox, path: str) -> None:
    """F-20 (detection only): the files that define CI and protection are Stage 00 owned paths."""
    sandbox.drive_to_verified("00")
    assert not errors(sandbox.orc().check())
    sandbox.write(path, "weakened\n")
    sandbox.commit(f"edit {path}")
    assert "VERIFICATION_STALE" in sandbox.codes(sandbox.orc().check())


def test_f23_package_is_marked_typed_and_owned() -> None:
    stage00 = json.loads((REPO / "governance/stage_registry.json").read_text(encoding="utf-8"))["stages"][0]
    assert (REPO / "src/citerift/py.typed").is_file()
    assert "src/citerift/py.typed" in stage00["owned_paths"]


# ---------------------------------------- S-01, found while writing the package


@pytest.mark.integration
def test_s01_files_git_ignores_are_not_evidence(sandbox: Sandbox) -> None:
    """S-01 (found during A-00-001): the manifest hashed every file on disk, so a byte-code cache next to an
    evidence script (ignored by git, absent from any clone) was pinned at verification or reported as unlisted."""
    sandbox.write(".gitignore", "__pycache__/\n")
    sandbox.commit("ignore byte code")
    sandbox.drive_to_verified("00")
    vdir = sandbox.registry()["stages"][0]["verification_dir"]
    cache = sandbox.root / vdir / "__pycache__" / "script.cpython-312.pyc"
    cache.parent.mkdir()
    cache.write_bytes(b"\x00compiled")
    assert not errors(sandbox.orc().check())
    recorded = [e["path"] for e in sandbox.registry()["stages"][0]["verification"]["evidence_manifest"]]
    assert all("__pycache__" not in p for p in recorded)
    sandbox.write(f"{vdir}/added-later.md", "not ignored, so it is reported\n")
    assert "EVIDENCE_UNLISTED" in sandbox.codes(sandbox.orc().check())
