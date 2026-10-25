"""Unit tests for the transition table, evidence checks and memory parsing."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path

import pytest

from citerift.governance import evidence, memory
from citerift.governance.model import ACTIVE, EDGES, Status, find_edge

pytestmark = [pytest.mark.unit]


def test_transition_table_shape() -> None:
    assert len(EDGES) == 11
    assert len({(e.source, e.target) for e in EDGES}) == 11
    owner_only = {(e.source, e.target) for e in EDGES if e.owner_only}
    assert owner_only == {
        (Status.NOT_STARTED, Status.AUTHORIZED),
        (Status.AUTHORIZED, Status.NOT_STARTED),
        (Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE, Status.ACCEPTED_CLOSED),
        (Status.ACCEPTED_CLOSED, Status.IN_PROGRESS),
    }


def test_only_path_into_acceptance_is_from_verified_and_owner_gated() -> None:
    into = [e for e in EDGES if e.target == Status.ACCEPTED_CLOSED]
    assert [(e.source, e.owner_only) for e in into] == [(Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE, True)]
    into_verified = [e.source for e in EDGES if e.target == Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE]
    assert into_verified == [Status.IMPLEMENTED_NOT_VERIFIED]


def test_every_state_reachable_and_no_dead_end() -> None:
    seen = {Status.NOT_STARTED}
    queue = deque([Status.NOT_STARTED])
    while queue:
        node = queue.popleft()
        for e in EDGES:
            if e.source == node and e.target not in seen:
                seen.add(e.target)
                queue.append(e.target)
    assert seen == set(Status)
    assert all(any(e.source == s for e in EDGES) for s in Status)


@pytest.mark.negative
def test_self_loops_and_skips_are_not_edges() -> None:
    for s in Status:
        assert find_edge(s, s) is None
    assert find_edge(Status.NOT_STARTED, Status.IN_PROGRESS) is None
    assert find_edge(Status.IN_PROGRESS, Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE) is None
    assert find_edge(Status.IMPLEMENTED_NOT_VERIFIED, Status.ACCEPTED_CLOSED) is None


def test_active_set() -> None:
    assert Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE not in ACTIVE
    assert Status.ACCEPTED_CLOSED not in ACTIVE
    assert Status.BLOCKED in ACTIVE


def test_sha256_and_artifact_checks(tmp_path: Path) -> None:
    f = tmp_path / "a.md"
    f.write_text("x" * 400, encoding="utf-8")
    digest = evidence.sha256_file(f)
    assert len(digest) == 64
    assert evidence.check_artifact(tmp_path, "a.md", digest) == []
    assert [p.code for p in evidence.check_artifact(tmp_path, "a.md", "0" * 64)] == ["EVIDENCE_STALE"]
    assert [p.code for p in evidence.check_artifact(tmp_path, "missing.md", None)] == ["EVIDENCE_MISSING"]


@pytest.mark.negative
@pytest.mark.security
def test_evidence_paths_outside_repository_rejected(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    secret = tmp_path / "outside.json"
    secret.write_text("{}", encoding="utf-8")
    (root / "link.json").symlink_to(secret)
    for rel in ("../outside.json", "link.json"):
        assert [p.code for p in evidence.check_artifact(root, rel, None)] == ["EVIDENCE_OUTSIDE_REPOSITORY"]
        assert [p.code for p in evidence.check_test_report(root, rel, None, "a" * 40, [])] == [
            "EVIDENCE_OUTSIDE_REPOSITORY"
        ]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("commit 0123456789abcdef", True),
        ("commit 0123456", True),
        ("commit 012345", False),
        ("commit 0123457", False),
        ("x0123456789abcdefx", False),
    ],
)
def test_mentions_revision(text: str, expected: bool) -> None:
    assert evidence.mentions_revision(text, "0123456789abcdef" + "0" * 24) is expected


def test_missing_sections_is_case_insensitive() -> None:
    text = "# Title\n\n## Stage And Status\n\n### test evidence\n"
    assert evidence.missing_sections(text, ["Stage and status", "Test evidence", "Open blockers"]) == ["Open blockers"]


@pytest.mark.negative
def test_test_report_rejects_non_json_and_wrong_format(tmp_path: Path) -> None:
    (tmp_path / "r.json").write_text("{not json", encoding="utf-8")
    assert [p.code for p in evidence.check_test_report(tmp_path, "r.json", None, "a" * 40, [])] == [
        "TEST_EVIDENCE_INVALID"
    ]
    (tmp_path / "r.json").write_text(json.dumps({"format": "other"}), encoding="utf-8")
    assert [p.code for p in evidence.check_test_report(tmp_path, "r.json", None, "a" * 40, [])] == [
        "TEST_EVIDENCE_INVALID"
    ]


DECISIONS_OK = """# Decisions

## D-001 — First choice
- Status: superseded
- Topic: lang
- Superseded-by: D-002

Body.

## D-002 — Second choice
- Status: accepted
- Topic: lang
- Supersedes: D-001

## D-003 — Open question
- Status: pending-owner
- Topic: license
"""


def test_decisions_parse_and_supersession(tmp_path: Path) -> None:
    path = tmp_path / "DECISIONS.md"
    path.write_text(DECISIONS_OK, encoding="utf-8")
    entries, problems = memory.check_decisions(path)
    assert problems == []
    assert [e.id for e in entries] == ["D-001", "D-002", "D-003"]
    assert entries[1].refs("Supersedes") == ["D-001"]


@pytest.mark.negative
@pytest.mark.parametrize(
    ("text", "code"),
    [
        (DECISIONS_OK.replace("- Status: superseded", "- Status: accepted"), "DECISION_CONTRADICTION"),
        (DECISIONS_OK.replace("- Superseded-by: D-002", "- Superseded-by: D-009"), "DECISION_BAD_REFERENCE"),
        (DECISIONS_OK.replace("- Supersedes: D-001", "- Supersedes: D-007"), "DECISION_BAD_REFERENCE"),
        (DECISIONS_OK.replace("- Status: pending-owner", "- Status: maybe"), "DECISION_INVALID_STATUS"),
        (DECISIONS_OK.replace("- Topic: license", ""), "DECISION_NO_TOPIC"),
        (DECISIONS_OK.replace("## D-003", "## D-002"), "DECISION_DUPLICATE_ID"),
        (
            DECISIONS_OK.replace(
                "- Status: superseded\n- Topic: lang\n- Superseded-by: D-002", "- Status: rejected\n- Topic: lang"
            ),
            "DECISION_SUPERSESSION_MISMATCH",
        ),
    ],
)
def test_decision_contradictions_detected(tmp_path: Path, text: str, code: str) -> None:
    path = tmp_path / "DECISIONS.md"
    path.write_text(text, encoding="utf-8")
    _, problems = memory.check_decisions(path)
    assert code in {p.code for p in problems}


RISKS_OK = """# Risks

## R-001 — Something
- Status: open
- Severity: critical
- Kind: defect
- Stage: 00, 02

## R-002 — Project level
- Status: mitigated
- Severity: low
- Kind: risk
- Stage: project
"""


def test_risks_parse_and_critical_defects(tmp_path: Path) -> None:
    path = tmp_path / "RISKS.md"
    path.write_text(RISKS_OK, encoding="utf-8")
    entries, problems = memory.check_risks(path)
    assert problems == []
    assert [r.id for r in memory.open_critical_defects(entries, "02")] == ["R-001"]
    assert memory.open_critical_defects(entries, "03") == []


@pytest.mark.negative
@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("- Severity: critical", "- Severity: catastrophic"),
        ("- Kind: defect", "- Kind: bug"),
        ("- Status: mitigated", "- Status: fixed"),
        ("- Stage: project", "- Stage: 2"),
        ("## R-002", "## R-001"),
    ],
)
def test_invalid_risk_records_detected(tmp_path: Path, old: str, new: str) -> None:
    path = tmp_path / "RISKS.md"
    path.write_text(RISKS_OK.replace(old, new), encoding="utf-8")
    _, problems = memory.check_risks(path)
    assert problems


@pytest.mark.negative
def test_missing_memory_files_reported(tmp_path: Path) -> None:
    assert memory.check_decisions(tmp_path / "DECISIONS.md")[1][0].code == "MEMORY_FILE_MISSING"
    assert memory.check_risks(tmp_path / "RISKS.md")[1][0].code == "MEMORY_FILE_MISSING"
