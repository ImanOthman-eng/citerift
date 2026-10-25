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
from sandbox_repo import REPO, Sandbox, git

from citerift.governance import evidence
from citerift.governance.model import Status
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
@pytest.mark.parametrize(("refs", "code"), [(["."], "GATE_EVIDENCE_MISSING"), (["RISKS.md"], "GATE_EVIDENCE_UNPINNED")])
def test_f02_gate_evidence_must_be_a_pinned_file(sandbox: Sandbox, refs: list[str], code: str) -> None:
    for target in ("AUTHORIZED", "IN_PROGRESS"):
        assert sandbox.go("00", Status(target)).allowed
    rev = sandbox.commit("implement")
    assert sandbox.go("00", Status.IMPLEMENTED_NOT_VERIFIED, revision=rev).allowed
    sandbox.write_evidence("00", rev)
    gates = {gid: {"result": "pass", "evidence": refs} for gid in sandbox.gates("00")}
    result = sandbox.go("00", Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE, gates=gates, ci=sandbox.ci(rev))
    assert not result.allowed
    assert code in sandbox.codes(result.findings)


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
