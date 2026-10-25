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


def _run_plugin(
    project: Path, report: Path, *args: str, env: dict[str, str] | None = None
) -> tuple[int, dict[str, Any], str]:
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
        env=env,
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
@pytest.mark.parametrize(
    ("conftest", "args", "field", "value"),
    [
        (None, ["-o", "python_functions=test_[adg]*"], "override_ini", ["python_functions=test_[adg]*"]),
        (
            "def pytest_collection_modifyitems(items):\n    items[:] = [i for i in items if i.name != 'test_beta']\n",
            [],
            "dropped",
            1,
        ),
    ],
    ids=["override_within_files", "conftest_drops_within_files"],
)
def test_v01_narrowing_that_keeps_every_file_is_partial(
    tmp_path: Path, conftest: str | None, args: list[str], field: str, value: object
) -> None:
    """Every test file still runs, so only the override or dropped-item rule can see the narrowing."""
    project = _plugin_project(tmp_path)
    if conftest is not None:
        (project / "tests" / "conftest.py").write_text(conftest, encoding="utf-8")
        git(project, "add", "-A")
        git(project, "commit", "-q", "-m", "narrowing")
    reports = tmp_path / "reports"
    reports.mkdir()
    code, data, output = _run_plugin(project, reports / "r.json", *args)
    assert code == 0 and data["totals"] == {"passed": 3}, output
    assert data["selection"]["files"] == ["tests/test_other.py", "tests/test_sample.py"]
    assert data["selection"][field] == value
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


@pytest.mark.negative
@pytest.mark.parametrize("heading", ["### R-001 — Wrong level", "## R-01 — Short id", "## R-001 - Hyphen"])
def test_f06_malformed_heading_without_fields_is_malformed(tmp_path: Path, heading: str) -> None:
    """The heading rule on its own: with no field lines below it, the orphan-field rule (V-06) cannot see it."""
    from citerift.governance import memory

    risks = tmp_path / "RISKS.md"
    risks.write_text(f"# Risks\n\n{heading}\n\nProse only.\n", encoding="utf-8")
    problems = memory.check_risks(risks)[1]
    assert [p.code for p in problems] == ["MEMORY_MALFORMED"]
    assert "heading is not" in problems[0].message


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


# ----------------------------- second final independent review (X-01 to X-13)


@pytest.mark.negative
@pytest.mark.parametrize("alias", ["dotdot", "symlink"])
def test_x01_gate_evidence_through_dotdot_or_symlink_is_not_pinned(sandbox: Sandbox, alias: str) -> None:
    """X-01: an owned-path prefix made a file outside the owned paths count as pinned."""
    sandbox.write(OWNED_FILE, "version = 1\n")
    sandbox.write("NOTES.md", "notes that are not pinned\n")
    if alias == "dotdot":
        ref = "src/citerift/governance/../../../NOTES.md"
    else:
        ref = "src/citerift/governance/evidence-link.md"
        (sandbox.root / ref).symlink_to("../../../NOTES.md")
    for target in ("AUTHORIZED", "IN_PROGRESS"):
        assert sandbox.go("00", Status(target)).allowed
    rev = sandbox.commit("implement")
    assert sandbox.go("00", Status.IMPLEMENTED_NOT_VERIFIED, revision=rev).allowed
    sandbox.write_evidence("00", rev)
    handoff = "docs/verification/stage-00/HANDOFF.md"
    gates = {gid: {"result": "pass", "evidence": [handoff, ref]} for gid in sandbox.gates("00")}
    result = sandbox.go("00", Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE, gates=gates, ci=sandbox.ci(rev))
    assert not result.allowed
    assert "GATE_EVIDENCE_UNPINNED" in sandbox.codes(result.findings)


@pytest.mark.integration
def test_x02_collection_settings_in_the_ini_file_make_the_run_partial(tmp_path: Path) -> None:
    """X-02: one committed ``python_functions`` line ran 92 of 308 tests and the report was "complete"."""
    project = _plugin_project(tmp_path)
    pyproject = project / "pyproject.toml"
    pyproject.write_text(
        pyproject.read_text(encoding="utf-8") + 'python_functions = ["test_alpha", "test_delta"]\n', encoding="utf-8"
    )
    git(project, "commit", "-q", "-am", "narrow collection in the ini file")
    reports = tmp_path / "reports"
    reports.mkdir()
    code, data, output = _run_plugin(project, reports / "r.json")
    assert code == 0 and data["totals"] == {"passed": 2}, output
    assert data["selection"]["files"] == ["tests/test_other.py", "tests/test_sample.py"]
    shutil.copy(reports / "r.json", project / "r.json")
    problems = evidence.check_test_report(project, "r.json", None, git(project, "rev-parse", "HEAD"), ["unit"])
    assert "TEST_EVIDENCE_PARTIAL" in {p.code for p in problems}, data["selection"]


PADDER = (
    "def pytest_collection_modifyitems(items):\n"
    "    keep = [i for i in items if i.name in ('test_alpha', 'test_delta')]\n"
    "    items[:] = (keep * len(items))[: len(items)]\n"
)


@pytest.mark.integration
@pytest.mark.parametrize("how", ["committed_conftest", "untracked_excluded_conftest", "outside_plugin"])
def test_x03_padding_or_untracked_collection_code_makes_the_run_partial(tmp_path: Path, how: str) -> None:
    """X-03: repeating kept items hid the dropped ones, and the code doing it need not be committed."""
    import os

    project = _plugin_project(tmp_path)
    args: list[str] = []
    env = None
    if how == "committed_conftest":
        (project / "tests" / "conftest.py").write_text(PADDER, encoding="utf-8")
        git(project, "add", "-A")
        git(project, "commit", "-q", "-m", "padding conftest")
    elif how == "untracked_excluded_conftest":
        (project / "tests" / "conftest.py").write_text(PADDER, encoding="utf-8")
        with (project / ".git" / "info" / "exclude").open("a", encoding="utf-8") as fh:
            fh.write("tests/conftest.py\n")
    else:
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "padder.py").write_text(PADDER, encoding="utf-8")
        env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(outside), os.environ.get("PYTHONPATH", "")])}
        args = ["-p", "padder"]
    reports = tmp_path / "reports"
    reports.mkdir()
    code, data, output = _run_plugin(project, reports / "r.json", *args, env=env)
    assert code == 0 and data["dirty"] is False, output
    shutil.copy(reports / "r.json", project / "r.json")
    problems = evidence.check_test_report(project, "r.json", None, git(project, "rev-parse", "HEAD"), ["unit"])
    assert "TEST_EVIDENCE_PARTIAL" in {p.code for p in problems}, data["selection"]


@pytest.mark.negative
def test_x04_a_module_beside_the_package_in_src_is_an_error(sandbox: Sandbox) -> None:
    """X-04: ``src/sitecustomize.py`` (or ``src/jsonschema/``) runs before the checks CI starts from ``src``."""
    sandbox.write(OWNED_FILE, "version = 1\n")
    sandbox.commit("package only")
    assert "SRC_FOREIGN_MODULE" not in sandbox.codes(sandbox.orc().check())
    sandbox.write("src/sitecustomize.py", "print('loaded before every check')\n")
    sandbox.commit("module beside the package")
    assert "SRC_FOREIGN_MODULE" in sandbox.codes(sandbox.orc().check())


def _cli(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "citerift.governance.cli", "--root", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _damage(sandbox: Sandbox, damage: str) -> list[str]:
    """Apply one damage of X-05 and return the extra command-line arguments it needs."""
    root = sandbox.root
    schema = root / "schemas/governance/stage_registry.schema.json"
    report = root / "docs/verification/stage-00/test-report.json"
    if damage in ("report_count_string", "report_suites_list", "handoff_not_utf8", "amend_missing_report"):
        sandbox.drive_to_accepted("00")
    if damage == "status_not_utf8":
        with (root / "PROJECT_STATUS.md").open("ab") as fh:
            fh.write(b"\xff\n")
    elif damage == "schema_type_int":
        schema.write_text('{"type": 5}\n', encoding="utf-8")
    elif damage == "schema_list":
        schema.write_text("[]\n", encoding="utf-8")
    elif damage == "schema_dangling_ref":
        schema.write_text('{"$ref": "#/nope"}\n', encoding="utf-8")
    elif damage == "record_list":
        (root / "record.json").write_text("[]\n", encoding="utf-8")
        return [str(root / "record.json")]
    elif damage == "record_gates_list":
        (root / "record.json").write_text('{"gates": []}\n', encoding="utf-8")
        return [str(root / "record.json")]
    elif damage == "report_count_string":
        data = json.loads(report.read_text(encoding="utf-8"))
        data["totals"]["passed"] = "many"
        report.write_text(json.dumps(data), encoding="utf-8")
    elif damage == "report_suites_list":
        data = json.loads(report.read_text(encoding="utf-8"))
        data["suites"] = {s: [] for s in data["suites"]}
        report.write_text(json.dumps(data), encoding="utf-8")
    elif damage == "handoff_not_utf8":
        with (root / "docs/verification/stage-00/HANDOFF.md").open("ab") as fh:
            fh.write(b"\xff\n")
    return []


@pytest.mark.negative
@pytest.mark.parametrize(
    ("damage", "command", "code"),
    [
        ("status_not_utf8", ["check"], "STATUS_DOC_OUT_OF_DATE"),
        ("status_not_utf8", ["render-status", "--check"], "PROJECT_STATUS.md"),
        ("status_not_utf8", ["recover"], "STATUS_DOC_OUT_OF_DATE"),
        ("none", ["deps", "99"], "STAGE_UNKNOWN"),
        ("none", ["readiness", "99"], "STAGE_UNKNOWN"),
        ("none", ["handoff", "99"], "STAGE_UNKNOWN"),
        ("none", ["blocker", "add", "99", "waiting"], "STAGE_UNKNOWN"),
        (
            "none",
            [
                "amend",
                "99",
                "--kind",
                "correction",
                "--reason",
                "x",
                "--evidence",
                "RISKS.md",
                "--owner-ref",
                "cmsg_TESTAMENDREF01",
            ],
            "STAGE_UNKNOWN",
        ),
        ("schema_type_int", ["check"], "REGISTRY_SCHEMA_UNREADABLE"),
        ("schema_list", ["check"], "REGISTRY_SCHEMA_UNREADABLE"),
        ("schema_dangling_ref", ["check"], "REGISTRY_SCHEMA_UNREADABLE"),
        (
            "record_list",
            ["transition", "00", "AUTHORIZED", "--actor", "owner", "--reason", "x", "--record"],
            "--record",
        ),
        (
            "record_gates_list",
            ["transition", "00", "AUTHORIZED", "--actor", "owner", "--reason", "x", "--record"],
            "--record",
        ),
        (
            "amend_missing_report",
            [
                "amend",
                "00",
                "--kind",
                "enhancement",
                "--reason",
                "x",
                "--evidence",
                "RISKS.md",
                "--owner-ref",
                "cmsg_TESTAMENDREF01",
                "--test-report",
                "missing.json",
            ],
            "EVIDENCE_MISSING",
        ),
        ("report_count_string", ["check"], "TEST_EVIDENCE_INVALID"),
        ("report_suites_list", ["check"], "TEST_EVIDENCE_INVALID"),
        ("handoff_not_utf8", ["check"], "EVIDENCE_UNREADABLE"),
    ],
)
def test_x05_more_damaged_inputs_are_reported_not_crashed(
    sandbox: Sandbox, damage: str, command: list[str], code: str
) -> None:
    """X-05: residual tracebacks of V-10."""
    extra = _damage(sandbox, damage)
    out = _cli(sandbox.root, *command, *extra)
    assert "Traceback" not in out.stderr, out.stderr
    # recover reports the consistency errors it finds and still exits 0, so that it always prints the state
    assert out.returncode in ((0,) if command[0] == "recover" else (1, 2)), out.stdout + out.stderr
    assert code in out.stdout + out.stderr, out.stdout + out.stderr


CRITICAL_FIELDS = "- Status: open\n- Severity: critical\n- Kind: defect\n- Stage: 00\n"


@pytest.mark.negative
@pytest.mark.parametrize(
    "entry",
    [
        "### R–020 — Hidden\n" + CRITICAL_FIELDS.replace("- ", "- **").replace(":", "**:"),
        "## R–020 — Hidden\n" + CRITICAL_FIELDS.lower(),
        "Hidden defect R-020\n---\n\n" + "".join("  " + line + "\n" for line in CRITICAL_FIELDS.splitlines()),
        "## R\u00a0020 — Hidden\n\nProse only.\n",
    ],
    ids=["bold_fields", "lowercase_fields", "indented_fields", "nbsp_heading"],
)
def test_x06_entries_written_differently_are_malformed(tmp_path: Path, entry: str) -> None:
    """X-06: a heading that does not parse was skipped when its fields were written differently too."""
    from citerift.governance import memory

    risks = tmp_path / "RISKS.md"
    risks.write_text("# Risks\n\n" + entry, encoding="utf-8")
    assert "MEMORY_MALFORMED" in {p.code for p in memory.check_risks(risks)[1]}


@pytest.mark.negative
@pytest.mark.parametrize("invisible", ["\u200b", "\u00ad", "\u2060", "\ufeff"])
def test_x06_invisible_characters_do_not_split_a_topic(tmp_path: Path, invisible: str) -> None:
    from citerift.governance import memory

    decisions = tmp_path / "DECISIONS.md"
    body = "- Status: accepted\n- Topic: {topic}\n- Date: 2026-10-25\n- Stage: 00\n- Supersedes: none\n\nBody.\n"
    decisions.write_text(
        "# Decisions\n\n## D-001 — One\n"
        + body.format(topic="sandbox")
        + "\n## D-002 — Two\n"
        + body.format(topic=f"sand{invisible}box"),
        encoding="utf-8",
    )
    assert "DECISION_CONTRADICTION" in {p.code for p in memory.check_decisions(decisions)[1]}


@pytest.mark.negative
@pytest.mark.parametrize(("stage", "deps"), [(2, ["00"]), (4, ["02"]), (1, ["00"]), (9, [])])
def test_x07_stage_dependencies_are_fixed_by_the_schema(sandbox: Sandbox, stage: int, deps: list[str]) -> None:
    """X-07: dropping Stage 01 from Stage 02's dependencies let Stage 02 be accepted while 01 was not started."""
    reg = sandbox.registry()
    reg["stages"][stage]["depends_on"] = deps
    sandbox.save_registry(reg)
    assert "REGISTRY_SCHEMA" in sandbox.codes(sandbox.orc().check(include_status_doc=False))


@pytest.mark.integration
def test_x08_add_block_and_resolve_within_one_second(sandbox: Sandbox, monkeypatch: pytest.MonkeyPatch) -> None:
    """X-08: with default times the resolution fell in the second of the BLOCKED entry and was refused."""
    from datetime import UTC, datetime, timedelta

    from citerift.governance import orchestrator

    frozen = datetime(2026, 10, 25, 12, tzinfo=UTC)
    monkeypatch.setattr(
        orchestrator,
        "utc_now",
        lambda delta=None: (frozen + (delta or timedelta())).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    for target in (Status.AUTHORIZED, Status.IN_PROGRESS):
        assert sandbox.go("00", target, at=None).allowed
    bid = sandbox.orc().add_blocker("00", "waiting for the owner")
    assert sandbox.go("00", Status.BLOCKED, at=None).allowed
    assert sandbox.orc().resolve_blocker("00", bid, "the owner answered")
    assert not errors(sandbox.orc().check(include_status_doc=False))


@pytest.mark.integration
def test_x08_a_refused_resolution_does_not_call_its_own_error_pre_existing(sandbox: Sandbox) -> None:
    for target in (Status.AUTHORIZED, Status.IN_PROGRESS):
        assert sandbox.go("00", target).allowed
    opened = sandbox.tick()
    bid = sandbox.orc().add_blocker("00", "waiting for the owner", at=opened)
    assert sandbox.go("00", Status.BLOCKED).allowed
    with pytest.raises(orchestrator_error()) as refused:
        sandbox.orc().resolve_blocker("00", bid, "resolved before it blocked", at=opened)
    messages = [f.message for f in refused.value.findings if f.code == "HISTORY_BLOCKER"]
    assert messages and not any("(pre-existing)" in m for m in messages), messages


def orchestrator_error() -> type[Exception]:
    from citerift.governance.orchestrator import GovernanceError

    return GovernanceError


@pytest.mark.negative
def test_x09_grafts_do_not_hide_a_rewritten_history(sandbox: Sandbox) -> None:
    """X-09: ``--no-replace-objects`` does not disable ``.git/info/grafts``."""
    sandbox.drive_to_accepted("00")
    old_head = sandbox.head()
    orphan = git(sandbox.root, "commit-tree", f"{old_head}^{{tree}}", "-m", "rewritten history")
    git(sandbox.root, "reset", "-q", "--hard", orphan)
    assert "REVISION_NOT_IN_HISTORY" in sandbox.codes(sandbox.orc().check())
    (sandbox.root / ".git" / "info").mkdir(exist_ok=True)
    (sandbox.root / ".git" / "info" / "grafts").write_text(f"{orphan} {old_head}\n", encoding="utf-8")
    assert "REVISION_NOT_IN_HISTORY" in sandbox.codes(sandbox.orc().check())


@pytest.mark.negative
def test_x10_acceptance_while_a_blocker_was_open_is_an_error_in_history(sandbox: Sandbox) -> None:
    """X-10: the replay checked blockers at block, start, unblock and verify, but not at acceptance."""
    sandbox.drive_to_accepted("00")
    reg = sandbox.registry()
    accepted_at = reg["history"][-1]["at"]
    reg["stages"][0]["blockers"].append(
        {
            "id": "B-00-001",
            "description": "hand-written blocker open at the acceptance",
            "opened_at": accepted_at,
            "resolved_at": sandbox.tick(),
            "resolution": "resolved after the acceptance",
        }
    )
    sandbox.save_registry(reg)
    assert sandbox.codes(sandbox.orc().check(include_status_doc=False)) == {"HISTORY_BLOCKER"}


@pytest.mark.contracts
@pytest.mark.parametrize("language", ["zh-classical", "zh-min-nan", "be-tarask", "simple", "ar"])
def test_x11_every_open_wikipedia_edition_code_is_valid(language: str) -> None:
    """X-11: ``zh-classical`` (an open edition) was rejected by the language pattern."""
    from citerift.contracts import load_contracts
    from citerift.contracts.formats import loads_strict

    contracts = load_contracts(REPO / "schemas/contracts")
    path = REPO / "tests/stage00/fixtures/contracts/v1/valid/investigation_full.json"
    record = loads_strict(path.read_text(encoding="utf-8"))
    record_text = json.dumps(record).replace('"language": "en"', f'"language": "{language}"')
    assert contracts.validate(json.loads(record_text)) == []


@pytest.mark.regression
def test_x12_the_authorization_rule_holds_after_later_owner_decisions(sandbox: Sandbox) -> None:
    """X-12: the repository test asserted today's state (Stage 02 not started), not the rule, so the next owner
    decisions would have failed CI. The rule: no stage is active or done without an owner authorization."""
    from test_repository import stages_without_owner_authorization

    sandbox.drive_to_accepted("00")
    sandbox.drive_to_accepted("01")
    assert sandbox.go("02", Status.AUTHORIZED).allowed
    assert stages_without_owner_authorization(sandbox.orc()) == []
    _append_history(sandbox, "03", "NOT_STARTED", "AUTHORIZED", "engineering-agent")
    reg = sandbox.registry()
    reg["stages"][3]["status"] = "AUTHORIZED"
    sandbox.save_registry(reg)
    assert stages_without_owner_authorization(sandbox.orc()) == ["03"]


def _enhance(sandbox: Sandbox, *, bump: bool, owner_ref: str, tighten: bool = False) -> str:
    """Accept Stage 00, change a v1 contract, and record an enhancement amendment for the change."""
    path = sandbox.root / "schemas/contracts/v1/investigation.schema.json"
    text = path.read_text(encoding="utf-8")
    text = text.replace('"x-citerift-version": "1.0.1"', '"x-citerift-version": "1.1.0"') if bump else text
    if tighten:
        text = text.replace('"required": [', '"required": ["new_mandatory_field", ', 1)
    else:
        text = text.replace('"description": "', '"description": "Enhanced. ', 1)
    path.write_text(text, encoding="utf-8")
    rev = sandbox.commit("enhance a v1 contract")
    report = "docs/verification/stage-00/enhancement-test-report.json"
    stage = sandbox.orc().stage("00")
    sandbox.write(
        report,
        json.dumps(
            {
                "format": "citerift.test-report/1",
                "revision": rev,
                "dirty": False,
                "exit_status": 0,
                "totals": {"passed": 10 * len(stage["required_test_suites"])},
                "selection": {"args": ["tests"], "deselected": 0, "complete": True, "files": []},
                "suites": {s: {"passed": 10} for s in stage["required_test_suites"]},
            }
        ),
    )
    return sandbox.orc().add_amendment(
        "00",
        kind="enhancement",
        reason="minor contract version for a later stage",
        evidence_refs=[report],
        owner_ref=owner_ref,
        revision=rev,
        test_report=report,
        at=sandbox.tick(),
    )


@pytest.fixture
def accepted_with_fixtures(sandbox: Sandbox) -> Sandbox:
    valid = "tests/stage00/fixtures/contracts/v1/valid"
    for fixture in sorted((REPO / valid).glob("*.json")):
        sandbox.write(f"{valid}/{fixture.name}", fixture.read_text(encoding="utf-8"))
    sandbox.commit("contract fixtures")
    sandbox.drive_to_accepted("00")
    return sandbox


@pytest.mark.negative
@pytest.mark.parametrize(
    ("bump", "ref", "tighten", "code"),
    [
        (False, "cmsg_TESTENHANCE001", False, "CONTRACT_VERSION_NOT_INCREASED"),
        (True, "accepted", False, "OWNER_REF_REUSED"),
        (True, "cmsg_TESTENHANCE001", True, "CONTRACT_INCOMPATIBLE"),
    ],
    ids=["no_version_increase", "reused_owner_ref", "breaks_old_records"],
)
def test_x13_an_enhancement_must_version_contracts_and_cite_a_new_owner_statement(
    accepted_with_fixtures: Sandbox, bump: bool, ref: str, tighten: bool, code: str
) -> None:
    """X-13: an enhancement changed an accepted contract with the acceptance's own reference and no version."""
    sandbox = accepted_with_fixtures
    owner_ref = sandbox.registry()["stages"][0]["acceptance"]["owner_ref"] if ref == "accepted" else ref
    with pytest.raises(orchestrator_error()) as refused:
        _enhance(sandbox, bump=bump, owner_ref=owner_ref, tighten=tighten)
    assert code in {f.code for f in refused.value.findings}, [str(f) for f in refused.value.findings]


@pytest.mark.integration
def test_x13_a_versioned_compatible_enhancement_is_accepted(accepted_with_fixtures: Sandbox) -> None:
    sandbox = accepted_with_fixtures
    _enhance(sandbox, bump=True, owner_ref="cmsg_TESTENHANCE001")
    sandbox.commit("record the enhancement")
    assert not errors(sandbox.orc().check(include_status_doc=False))
