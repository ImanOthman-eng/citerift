"""Evidence file checks: hashes, test reports and handoff completeness."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TEST_REPORT_FORMAT = "citerift.test-report/1"
MIN_ARTIFACT_BYTES = 300


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_url(ref: str) -> bool:
    return ref.startswith("https://")


@dataclass(frozen=True)
class Problem:
    code: str
    message: str


def inside(root: Path, rel: str) -> bool:
    """True when ``rel`` resolves (following symlinks) to a location inside ``root``."""
    return (root / rel).resolve().is_relative_to(root.resolve())


def _outside(rel: str) -> list[Problem]:
    return [Problem("EVIDENCE_OUTSIDE_REPOSITORY", f"{rel} resolves outside the repository")]


def check_artifact(root: Path, rel: str, expected_sha: str | None) -> list[Problem]:
    path = root / rel
    if not inside(root, rel):
        return _outside(rel)
    if not path.is_file():
        return [Problem("EVIDENCE_MISSING", f"required artifact {rel} does not exist")]
    problems = []
    if path.stat().st_size < MIN_ARTIFACT_BYTES:
        problems.append(
            Problem(
                "EVIDENCE_TRIVIAL",
                f"{rel} is under {MIN_ARTIFACT_BYTES} bytes and cannot hold real evidence",
            )
        )
    if expected_sha is not None and sha256_file(path) != expected_sha:
        problems.append(
            Problem(
                "EVIDENCE_STALE",
                f"{rel} changed after it was recorded as evidence (sha256 mismatch)",
            )
        )
    return problems


def missing_sections(text: str, sections: list[str]) -> list[str]:
    headings = {m.group(1).strip().lower() for m in re.finditer(r"^#{1,6}\s+(.+?)\s*$", text, re.M)}
    return [s for s in sections if s.lower() not in headings]


def mentions_revision(text: str, revision: str) -> bool:
    """True when the full SHA or a prefix of at least 7 characters appears."""
    return any(revision.startswith(m.group(0)) for m in re.finditer(r"\b[0-9a-f]{7,40}\b", text))


def check_test_report(
    root: Path,
    rel: str,
    expected_sha: str | None,
    revision: str,
    required_suites: list[str],
) -> list[Problem]:
    path = root / rel
    if not inside(root, rel):
        return _outside(rel)
    if not path.is_file():
        return [Problem("TEST_EVIDENCE_MISSING", f"test report {rel} does not exist")]
    problems: list[Problem] = []
    if expected_sha is not None and sha256_file(path) != expected_sha:
        problems.append(Problem("TEST_EVIDENCE_STALE", f"test report {rel} changed after it was recorded"))
    try:
        report: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [*problems, Problem("TEST_EVIDENCE_INVALID", f"{rel} is not valid JSON: {exc}")]
    if not isinstance(report, dict) or report.get("format") != TEST_REPORT_FORMAT:
        return [*problems, Problem("TEST_EVIDENCE_INVALID", f"{rel} is not a {TEST_REPORT_FORMAT}")]
    if report.get("revision") != revision:
        problems.append(
            Problem(
                "TEST_EVIDENCE_WRONG_REVISION",
                f"{rel} was produced at {report.get('revision')}, not at {revision}",
            )
        )
    if report.get("dirty") is not False:
        problems.append(
            Problem(
                "TEST_EVIDENCE_DIRTY",
                f"{rel} was produced from a working tree with uncommitted changes",
            )
        )
    totals = report.get("totals", {})
    if not isinstance(totals, dict) or totals.get("passed", 0) <= 0:
        problems.append(Problem("TEST_EVIDENCE_EMPTY", f"{rel} records no passed tests"))
    elif totals.get("failed", 0) or totals.get("error", 0):
        problems.append(
            Problem(
                "TESTS_FAILED",
                f"{rel} records {totals.get('failed', 0)} failed and {totals.get('error', 0)} errored tests",
            )
        )
    if report.get("exit_status") != 0:
        problems.append(Problem("TESTS_FAILED", f"{rel} records pytest exit status {report.get('exit_status')}"))
    suites = report.get("suites", {})
    for suite in required_suites:
        counts = suites.get(suite) if isinstance(suites, dict) else None
        if not counts or counts.get("passed", 0) <= 0:
            problems.append(Problem("TEST_SUITE_MISSING", f"required test suite '{suite}' has no passed tests"))
        elif counts.get("failed", 0) or counts.get("error", 0):
            problems.append(Problem("TESTS_FAILED", f"required test suite '{suite}' has failures"))
    return problems
