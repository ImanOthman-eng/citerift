"""Maintenance transactions: an owner-authorized change to an accepted stage's owned files, validated in two phases.

An ordinary enhancement amendment needs a passing complete test report at its own revision. A change that
repairs a test of the governance check itself cannot produce that report: until an amendment covers the
change, ``check`` reports the stage stale, and the test that runs ``check`` on the repository fails. A
maintenance transaction breaks that cycle without weakening any check:

1. prepare: record the exact patch (each changed owned file with the SHA-256 of its content at a candidate
   revision) against the accepted revision, with the owner's reference. Nothing is verified yet.
2. validate: commit that pending record and run the complete test suite on the clean revision, once per
   supported Python version. While the record is pending, owned content that equals the declared patch is
   reported as ``MAINTENANCE_PENDING`` (a warning) instead of ``VERIFICATION_STALE``; any other owned
   change stays an error, and no stage can be verified or accepted.
3. finalize: record the validated revision and the reports. The amendment then covers the change like any
   enhancement and ordinary drift detection applies again.

Superseding a candidate records a new transaction; the old one keeps its record, marked superseded.
This module holds the pure rules; the orchestrator applies them to the registry and the repository.
"""

from __future__ import annotations

from typing import Any

from citerift.governance import evidence

PENDING = "pending_validation"
FINALIZED = "finalized"
SUPERSEDED = "superseded"
# The Python versions a finalization needs a complete passing report for: the CI matrix (test_repository).
REQUIRED_PYTHONS = ("3.12", "3.13")


def patch_sha256(scope: list[dict[str, Any]]) -> str:
    """Digest of the declared patch: each path with the SHA-256 of its content, or null for a deleted file."""
    return evidence.canonical_sha256(sorted([e["path"], e["sha256"]] for e in scope))


def python_minor(report: dict[str, Any]) -> str | None:
    """``3.12`` for a report written by Python 3.12.x; None when the report does not say."""
    version = report.get("python")
    if not isinstance(version, str):
        return None
    parts = version.split(".")
    return ".".join(parts[:2]) if len(parts) >= 2 and all(p.isdigit() for p in parts[:2]) else None


# The fields finalization fills in; everything else in the record is fixed when it is prepared.
FINALIZATION_FIELDS = ("revision", "test_report")
FINALIZATION_MAINTENANCE_FIELDS = ("phase", "reports", "finalized_at", "finalized_after_seq")
# A declared file must be a regular, non-executable file: its content digest then says everything git stores.
REGULAR_FILE = ("100644", "blob")


def as_prepared(amendment: dict[str, Any]) -> dict[str, Any]:
    """The amendment without the fields finalization fills in, for comparing a finalized record with the
    pending one the validated revision holds (every other field, ``recorded_at`` included, must be equal)."""
    out = {k: v for k, v in amendment.items() if k not in FINALIZATION_FIELDS}
    out["maintenance"] = {
        k: v for k, v in amendment.get("maintenance", {}).items() if k not in FINALIZATION_MAINTENANCE_FIELDS
    }
    return out


def interval_end(stage: dict[str, Any], amendment: dict[str, Any]) -> tuple[str | None, int | None]:
    """Where the barrier of a maintenance record ends, as (time, history length): its finalization, the
    recording of its successor, or (None, None) while it is pending (the barrier is open)."""
    m = amendment["maintenance"]
    if m["phase"] == FINALIZED:
        return m["finalized_at"], m["finalized_after_seq"]
    if m["phase"] == SUPERSEDED:
        successor = next((a for a in stage["amendments"] if a["id"] == m["superseded_by"]), None)
        if successor is not None and successor.get("maintenance"):
            return successor["recorded_at"], successor["maintenance"]["opened_after_seq"]
    return None, None
