"""Hand edits of Persistent Project Memory that the consistency check must detect.

Each case starts from a sandbox in which Stage 00 is legitimately verified,
applies one hand edit to the registry or a memory file, and requires the named
error. Covers the integrity rules of Prompt 02 section 7.4 that the scenario
tests do not name directly.
"""

from __future__ import annotations

import copy
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from sandbox_repo import OWNER_REF, RISKS, Sandbox

from citerift.governance.model import Actor, Status
from citerift.governance.orchestrator import Orchestrator

pytestmark = [pytest.mark.negative, pytest.mark.integration]

Edit = Callable[[Sandbox, dict[str, Any]], None]


def _cycle(sb: Sandbox, reg: dict[str, Any]) -> None:
    reg["stages"][0]["depends_on"] = ["02"]  # 02 already depends on 00


def _unknown_dependency(sb: Sandbox, reg: dict[str, Any]) -> None:
    reg["stages"][2]["depends_on"] = ["00", "01", "99"]


def _duplicate_stage(sb: Sandbox, reg: dict[str, Any]) -> None:
    reg["stages"].append(copy.deepcopy(reg["stages"][9]))


def _sequence_gap(sb: Sandbox, reg: dict[str, Any]) -> None:
    reg["history"][1]["seq"] = 7


def _time_reversed(sb: Sandbox, reg: dict[str, Any]) -> None:
    reg["history"][2]["at"] = "2025-01-01T00:00:00Z"


def _invalid_edge(sb: Sandbox, reg: dict[str, Any]) -> None:
    reg["history"][1]["from"] = "NOT_STARTED"  # NOT_STARTED -> IN_PROGRESS is not an edge


def _unknown_history_stage(sb: Sandbox, reg: dict[str, Any]) -> None:
    reg["history"][1]["stage"] = "99"


def _schema_violation(sb: Sandbox, reg: dict[str, Any]) -> None:
    reg["registry_version"] = "2.0.0"


def _record_for_unreached_state(sb: Sandbox, reg: dict[str, Any]) -> None:
    reg["stages"][3]["implementation"] = copy.deepcopy(reg["stages"][0]["implementation"])


def _unknown_gate(sb: Sandbox, reg: dict[str, Any]) -> None:
    gates = reg["stages"][0]["verification"]["gates"]
    gates["00-Z"] = copy.deepcopy(gates["00-A"])


def _duplicate_risk(sb: Sandbox, reg: dict[str, Any]) -> None:
    sb.write("RISKS.md", RISKS + RISKS.split("\n", 1)[1])


def _invalid_risk_field(sb: Sandbox, reg: dict[str, Any]) -> None:
    sb.write("RISKS.md", RISKS.replace("- Severity: low", "- Severity: catastrophic"))


def _half_resolved_blocker(sb: Sandbox, reg: dict[str, Any]) -> None:
    reg["stages"][0]["blockers"] = [
        {
            "id": "B-00-001",
            "description": "resolved without saying how",
            "opened_at": "2026-01-01T00:00:01Z",
            "resolved_at": "2026-01-01T00:00:02Z",
            "resolution": None,
        }
    ]


def _unknown_amendment(sb: Sandbox, reg: dict[str, Any]) -> None:
    reg["history"][-1]["amendment"] = "A-00-999"


def _artifact_dropped_from_record(sb: Sandbox, reg: dict[str, Any]) -> None:
    reg["stages"][0]["verification"]["artifacts"].pop()


def _test_report_dropped_from_record(sb: Sandbox, reg: dict[str, Any]) -> None:
    reg["stages"][0]["verification"]["test_report"]["path"] = "docs/verification/stage-00/other-report.json"


def _gates_removed(sb: Sandbox, reg: dict[str, Any]) -> None:
    reg["stages"][0]["acceptance_gates"] = []


def _suites_removed(sb: Sandbox, reg: dict[str, Any]) -> None:
    reg["stages"][0]["required_test_suites"] = []


def _foreign_amendment(sb: Sandbox, reg: dict[str, Any]) -> None:
    reg["stages"][0]["amendments"] = [copy.deepcopy(_AMENDMENT)]


_AMENDMENT = {
    "id": "A-02-001",
    "kind": "correction",
    "reason": "filed under stage 00 but numbered for stage 02",
    "evidence": ["docs/verification/stage-00/HANDOFF.md"],
    "owner_ref": OWNER_REF,
    "revision": None,
    "test_report": None,
    "recorded_at": "2026-01-01T00:00:09Z",
}


CASES: list[tuple[str, Edit, str]] = [
    # Dependencies are fixed per stage by the schema (X-07), which reports these edits before the graph checks.
    ("dependency cycle", _cycle, "REGISTRY_SCHEMA"),
    ("unknown dependency", _unknown_dependency, "REGISTRY_SCHEMA"),
    ("duplicate stage", _duplicate_stage, "STAGE_DUPLICATE"),
    ("history sequence gap", _sequence_gap, "HISTORY_SEQUENCE"),
    ("history time reversed", _time_reversed, "HISTORY_TIME_ORDER"),
    ("history invalid edge", _invalid_edge, "HISTORY_INVALID_EDGE"),
    ("history unknown stage", _unknown_history_stage, "HISTORY_UNKNOWN_STAGE"),
    ("registry schema violation", _schema_violation, "REGISTRY_SCHEMA"),
    ("record for a state not reached", _record_for_unreached_state, "RECORD_UNEXPECTED"),
    ("gate not defined for the stage", _unknown_gate, "GATE_UNKNOWN"),
    ("duplicate risk id", _duplicate_risk, "RISK_DUPLICATE_ID"),
    ("invalid risk field", _invalid_risk_field, "RISK_INVALID_FIELD"),
    ("blocker resolved without resolution", _half_resolved_blocker, "BLOCKER_RECORD"),
    ("history cites unknown amendment", _unknown_amendment, "AMENDMENT_UNKNOWN"),
    ("artifact missing from verification record", _artifact_dropped_from_record, "EVIDENCE_NOT_RECORDED"),
    ("test report missing from verification record", _test_report_dropped_from_record, "TEST_EVIDENCE_NOT_RECORDED"),
    ("acceptance gates removed after verification", _gates_removed, "GATES_UNDEFINED"),
    ("required test suites removed", _suites_removed, "TEST_SUITES_UNDEFINED"),
    ("amendment filed under the wrong stage", _foreign_amendment, "AMENDMENT_RECORD"),
]


@pytest.fixture
def verified(tmp_path: Path) -> Sandbox:
    sb = Sandbox(tmp_path / "repo")
    sb.drive_to_verified("00")
    assert sb.codes(sb.orc().check()) == set()
    return sb


@pytest.mark.parametrize(("name", "edit", "code"), CASES, ids=[c[0] for c in CASES])
def test_hand_edit_is_detected(verified: Sandbox, name: str, edit: Edit, code: str) -> None:
    reg = verified.registry()
    edit(verified, reg)
    verified.save_registry(reg)
    assert code in verified.codes(verified.orc().check()), name


def test_copy_without_git_history_cannot_vouch_for_revisions(verified: Sandbox, tmp_path: Path) -> None:
    export = tmp_path / "export"
    shutil.copytree(verified.root, export, ignore=shutil.ignore_patterns(".git"))
    assert "REVISION_UNVERIFIABLE" in verified.codes(Orchestrator(export).check())


def test_unknown_stage_and_missing_revision_are_refused(tmp_path: Path) -> None:
    sb = Sandbox(tmp_path / "repo")
    unknown = sb.orc().propose("99", Status.AUTHORIZED, actor=Actor.OWNER, reason="test", owner_ref=OWNER_REF)
    assert not unknown.allowed
    assert "STAGE_UNKNOWN" in sb.codes(unknown.findings)
    sb.go("00", Status.AUTHORIZED)
    sb.go("00", Status.IN_PROGRESS)
    no_revision = sb.orc().propose(
        "00", Status.IMPLEMENTED_NOT_VERIFIED, actor=Actor.ENGINEERING_AGENT, reason="test", revision=None
    )
    assert not no_revision.allowed
    assert "REVISION_REQUIRED" in sb.codes(no_revision.findings)


@pytest.mark.parametrize(("edit", "code"), [(_cycle, "DEPENDENCY_CYCLE"), (_unknown_dependency, "DEPENDENCY_UNKNOWN")])
def test_dependency_graph_checks_still_hold_behind_the_schema(verified: Sandbox, edit: Edit, code: str) -> None:
    """The schema now fixes every stage's dependencies (X-07) and reports these edits first. The graph checks
    stay as a second line, for example if the schema itself were changed; this runs them directly."""
    reg = verified.registry()
    edit(verified, reg)
    assert code in verified.codes(Orchestrator(verified.root, reg)._structure_findings())
