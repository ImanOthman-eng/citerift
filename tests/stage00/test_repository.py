"""Checks on the real repository: approved plan, canonical state, CI hardening, secrets."""

from __future__ import annotations

import json
import re
import subprocess
import tomllib
from pathlib import Path

import pytest

from citerift.governance.orchestrator import Orchestrator, errors

REPO = Path(__file__).resolve().parents[2]

APPROVED_STAGES = [
    ("00", "Engineering Foundation"),
    ("01", "Independent Feasibility Investigation"),
    ("02", "Retraction Data Engine"),
    ("03", "Wikipedia Extraction Engine"),
    ("04", "Detection Engine and Vertical Slice"),
    ("05", "Citation Context and Evidence Preparation"),
    ("06", "AI Investigation and Scientific Evaluation"),
    ("07", "Cross-Wiki Intelligence and Backend API"),
    ("08", "Creative Interactive Frontend"),
    ("09", "Release, Research Report, and Submission"),
]


@pytest.mark.regression
def test_registry_matches_the_approved_ten_stage_plan() -> None:
    orc = Orchestrator(REPO)
    assert [(s["id"], s["name"]) for s in orc.stages] == APPROVED_STAGES
    executors = {s["id"]: s["executor"] for s in orc.stages}
    assert executors["01"] == "external-agent"
    assert all(e == "engineering-agent" for sid, e in executors.items() if sid != "01")
    gates = [g["id"] for g in orc.stage("00")["acceptance_gates"]]
    assert gates == [f"00-{c}" for c in "ABCDEFGHIJKLMNOP"]


@pytest.mark.regression
def test_no_stage_beyond_00_is_authorized_for_the_engineering_agent() -> None:
    orc = Orchestrator(REPO)
    for s in orc.stages:
        if s["id"] not in ("00", "01"):
            assert s["status"] == "NOT_STARTED", f"stage {s['id']} must not be started without owner authorization"
    assert orc.stage("01")["acceptance"] is None, "Stage 01 findings are not accepted"


@pytest.mark.regression
def test_real_repository_passes_governance_check() -> None:
    findings = Orchestrator(REPO).check()
    assert [str(f) for f in errors(findings)] == []


@pytest.mark.regression
def test_registry_is_canonical_json() -> None:
    text = (REPO / "governance/stage_registry.json").read_text(encoding="utf-8")
    assert text == json.dumps(json.loads(text), indent=2, ensure_ascii=False) + "\n"


@pytest.mark.regression
def test_python_constraints_are_consistent() -> None:
    project = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["requires-python"] == ">=3.12,<3.14"
    assert (REPO / ".python-version").read_text(encoding="utf-8").strip() == "3.12"
    workflow = (REPO / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert 'python: ["3.12", "3.13"]' in workflow
    assert (REPO / "uv.lock").is_file()


WORKFLOWS = sorted((REPO / ".github/workflows").glob("*.yml"))


@pytest.mark.security
@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_workflow_hardening(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    uses = re.findall(r"uses:\s*([^\s#]+)", text)
    assert uses, "expected at least one action"
    for ref in uses:
        assert re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", ref), f"action not pinned to a full SHA: {ref}"
    assert re.search(r"^permissions:\n  contents: read$", text, re.M), "top-level permissions must be read-only"
    assert "pull_request_target" not in text
    assert "secrets." not in text
    assert "persist-credentials: false" in text
    assert "${{ github.event." not in text, "untrusted event payload must not be interpolated into the workflow"
    assert "${{ github.head_ref" not in text


@pytest.mark.security
def test_required_check_name_exists() -> None:
    text = (REPO / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert re.search(r"^  ci-gate:\n    name: ci-gate$", text, re.M)


@pytest.mark.security
def test_secrets_are_ignored() -> None:
    ignored = (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()
    for pattern in (".env", ".env.*", "*.pem", "*.key", ".venv/"):
        assert pattern in ignored


SECRET_PATTERNS = [
    re.compile(p)
    for p in (
        r"gh[pousr]_[A-Za-z0-9]{36,}",
        r"github_pat_[A-Za-z0-9_]{50,}",
        r"AKIA[0-9A-Z]{16}",
        r"sk-ant-[A-Za-z0-9_-]{20,}",
        r"xox[abpr]-[A-Za-z0-9-]{10,}",
        "-----BEGIN " + r"(RSA |EC |OPENSSH )?PRIVATE KEY-----",
    )
]


def _repository_files() -> list[Path]:
    out = subprocess.run(
        ["git", "-C", str(REPO), "ls-files", "--cached", "--others", "--exclude-standard"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [REPO / line for line in out.stdout.splitlines() if (REPO / line).is_file()]


@pytest.mark.security
def test_no_secrets_in_repository_files() -> None:
    hits = []
    for path in _repository_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                hits.append(f"{path.relative_to(REPO)}: {pattern.pattern}")
    assert hits == []


@pytest.mark.security
def test_secret_scanner_detects_a_planted_token() -> None:
    token = "ghp_" + "A1b2C3d4" * 5
    assert any(p.search(f"token = {token}") for p in SECRET_PATTERNS)


@pytest.mark.security
def test_governance_code_runs_no_shell() -> None:
    for path in (REPO / "src").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "shell=True" not in text
        assert "os.system(" not in text
        assert not re.search(r"\beval\(|\bexec\(", text)


@pytest.mark.regression
def test_status_document_is_generated_from_registry() -> None:
    orc = Orchestrator(REPO)
    assert (REPO / "PROJECT_STATUS.md").read_text(encoding="utf-8") == orc.render_status()


@pytest.mark.regression
def test_application_layers_not_created_prematurely() -> None:
    package = REPO / "src" / "citerift"
    assert sorted(p.name for p in package.iterdir() if p.is_dir() and p.name != "__pycache__") == [
        "contracts",
        "governance",
    ]
    assert not (REPO / "frontend").exists()


@pytest.mark.regression
def test_documented_links_exist() -> None:
    """Every relative Markdown link in top-level and docs files points to an existing path."""
    broken = []
    for md in [*REPO.glob("*.md"), *(REPO / "docs").rglob("*.md")]:
        for target in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", md.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            if not (md.parent / target).exists():
                broken.append(f"{md.relative_to(REPO)} -> {target}")
    assert broken == []


@pytest.mark.security
def test_branch_ruleset_definition() -> None:
    """The committed ruleset is what the owner imports; it must match DECISIONS.md D-011."""
    ruleset = json.loads((REPO / ".github/rulesets/main-protection.json").read_text(encoding="utf-8"))
    assert ruleset["enforcement"] == "active"
    assert ruleset["bypass_actors"] == []
    assert ruleset["conditions"]["ref_name"]["include"] == ["~DEFAULT_BRANCH"]
    rules = {r["type"]: r.get("parameters", {}) for r in ruleset["rules"]}
    assert set(rules) == {"deletion", "non_fast_forward", "pull_request", "required_status_checks"}
    assert rules["pull_request"]["required_approving_review_count"] == 0
    assert rules["pull_request"]["allowed_merge_methods"] == ["merge"]
    checks = rules["required_status_checks"]["required_status_checks"]
    assert checks == [{"context": "ci-gate", "integration_id": 15368}]
