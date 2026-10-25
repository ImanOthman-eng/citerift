"""Evidence file checks: hashes, test reports and handoff completeness."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from citerift.contracts.formats import loads_strict
from citerift.governance import gitutil

TEST_REPORT_FORMAT = "citerift.test-report/1"
MIN_ARTIFACT_BYTES = 300


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest(root: Path, directory: str) -> list[dict[str, str]]:
    """sha256 of every file under ``directory`` that git does not ignore, sorted by repository-relative path.

    Ignored files (byte-code caches and the like) never reach a clone, so pinning them would make
    every clone report the evidence as missing.
    """
    base = root / directory
    if not base.is_dir():
        return []
    files = sorted(p.relative_to(root).as_posix() for p in base.rglob("*") if p.is_file())
    skip = gitutil.ignored(root, files)
    return [{"path": rel, "sha256": sha256_file(root / rel)} for rel in files if rel not in skip]


def canonical_sha256(data: Any) -> str:
    """Hash of a JSON value in canonical form (sorted keys, no whitespace)."""
    text = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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
        report: Any = loads_strict(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
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
    selection = report.get("selection")
    if not isinstance(selection, dict) or selection.get("complete") is not True:
        problems.append(
            Problem(
                "TEST_EVIDENCE_PARTIAL",
                f"{rel} does not record a run of the complete test suite (selection: {selection})",
            )
        )
    if isinstance(selection, dict):
        problems.extend(_files_not_run(root, rel, revision, selection.get("files")))
    if isinstance(totals, dict) and totals.get("not_run", 0):
        problems.append(Problem("TEST_EVIDENCE_PARTIAL", f"{rel} records {totals['not_run']} tests that did not run"))
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


TEST_ROOT = "tests"


def is_test_file(path: str) -> bool:
    """pytest's default test file pattern, applied independently of any configuration that a change could edit."""
    name = path.rsplit("/", 1)[-1]
    return name.endswith(".py") and (name.startswith("test_") or name.endswith("_test.py"))


def _files_not_run(root: Path, rel: str, revision: str, files: object) -> list[Problem]:
    """Every test file committed under ``tests/`` at ``revision`` must appear among the files the report ran."""
    try:
        committed = [p for p in gitutil.tracked_files(root, revision, TEST_ROOT) if is_test_file(p)]
    except gitutil.GitUnavailableError as exc:
        return [Problem("TEST_EVIDENCE_PARTIAL", f"cannot list the test files at {revision[:12]}: {exc}")]
    ran = set(files) if isinstance(files, list) else set()
    missing = [p for p in committed if p not in ran]
    if not missing:
        return []
    shown = ", ".join(missing[:5]) + (f" and {len(missing) - 5} more" if len(missing) > 5 else "")
    return [Problem("TEST_EVIDENCE_PARTIAL", f"{rel} did not run {len(missing)} committed test file(s): {shown}")]
