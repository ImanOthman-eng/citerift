"""Identities that Investigation Memory derives and checks (SPEC 4.1, 4.2, 8.2; MM 2 and 3).

Child ids of SPEC 4.3 (evidence, claim, decision, question) are computed by the steps that write them and checked by
VERIFY (Step 7 onward); Memory checks that they are defined once and resolve (M-4, M-7, M-10).
"""

from __future__ import annotations

from typing import Any

from citerift.investigation.canonical import H, canon, sha256_hex, uuid_from_key

GENESIS_TAG = "citerift-journal-genesis/1"
INVESTIGATION_TAG = "citerift-investigation/1"
ROOT_TAG = "citerift-investigation-root/1"
SAFETY_ALLOWANCE_MS = 30_000  # owner decision D-042


def genesis(investigation_key: str) -> str:
    """``prev`` of the record with ``seq = 0`` (SPEC 8.2)."""
    return H(GENESIS_TAG, investigation_key)


def config_digest(config: dict[str, Any]) -> str:
    """SHA-256 of the canonical effective configuration (SPEC S-4.7, D-042)."""
    return sha256_hex(canon(config))


def investigation_key(request_key: dict[str, Any], plan_version: str, cfg_digest: str) -> str:
    """``H("citerift-investigation/1", request_key, plan_version, config_digest)`` (S-4.7)."""
    return H(INVESTIGATION_TAG, request_key, plan_version, cfg_digest)


def root_id(subject_type: str, identity: dict[str, Any]) -> str:
    """``H("citerift-investigation-root/1", type, identity)``; the title is never part of it (S-4.2)."""
    return H(ROOT_TAG, subject_type, identity)


def investigation_id(key: str) -> str:
    return uuid_from_key(key)


def record_digest(record: dict[str, Any]) -> str:
    """SHA-256 of the canonical record without ``digest`` (SPEC 8.2)."""
    return sha256_hex(canon({k: v for k, v in record.items() if k != "digest"}))


def live_request_key(request: dict[str, Any]) -> dict[str, Any] | None:
    """The request key a live-capture request implies, or None for a retained bundle (its key needs the bundle)."""
    if request.get("mode") != "live_capture":
        return None
    subject = request.get("subject") or {}
    return {"wiki": subject.get("wiki"), "revision_id": subject.get("revision_id")}


def live_bound_consistent(config: dict[str, Any]) -> bool:
    """D-042: ``t_acq_ms = deadline_ms + op_timeout_ms + 30000`` when a live bound is present."""
    bound = config.get("live_acquire_bound")
    if bound is None:
        return True
    try:
        return bool(
            bound["safety_allowance_ms"] == SAFETY_ALLOWANCE_MS
            and bound["t_acq_ms"] == bound["deadline_ms"] + bound["op_timeout_ms"] + bound["safety_allowance_ms"]
        )
    except (KeyError, TypeError):
        return False
