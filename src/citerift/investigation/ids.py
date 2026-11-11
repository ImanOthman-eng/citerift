"""Identities that Investigation Memory derives and checks (SPEC 4.1, 4.2, 8.2; MM 2 and 3).

Child ids of SPEC 4.3 and MM 3.3 (evidence, claim, decision, question) are values of ``H`` with distinct tags over the
parent id and the child's anchor or content, never over ``seq``, attempt or time (CH-1). The Workflow Controller
(Step 7) derives decision and question ids itself and checks evidence and claim ids before it commits a step; Memory
checks that every id is defined once and resolves (M-4, M-7, M-10). Step keys (S-9.3, MM 10.1) are derived here too.
"""

from __future__ import annotations

from typing import Any

from citerift.investigation.canonical import H, canon, sha256_hex, uuid_from_key

GENESIS_TAG = "citerift-journal-genesis/1"
INVESTIGATION_TAG = "citerift-investigation/1"
ROOT_TAG = "citerift-investigation-root/1"
EVIDENCE_TAG = "citerift-evidence/1"
CLAIM_TAG = "citerift-claim/1"
DECISION_TAG = "citerift-decision/1"
QUESTION_TAG = "citerift-question/1"
STEP_TAG = "citerift-step/1"
IDENTITY_TAG = "citerift-identity/1"
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


# Child identities (SPEC 4.3, MM 3.3; Step 7) -----------------------------------------------------------------------


def evidence_id(observation: str, pointer: str, kind: str) -> str:
    """``H(observation digest, JSON pointer, evidence kind)`` (owner decision D-051): what one kind of evidence states
    about the value a pointer selects in one observation. Two kinds at one pointer are two evidence items."""
    return H(EVIDENCE_TAG, observation, pointer, kind)


def claim_id(cand_ref: str, claim_class: str, rule: str, table_version: str, evidence_set: str) -> str:
    """``H(cand_ref, class, rule id, table version, evidence-set digest)`` (owner decision D-047): the claim binds the
    exact content of its evidence set (supporting, contradicting and per-alternative ids, ``sets.py``)."""
    return H(CLAIM_TAG, cand_ref, claim_class, rule, table_version, evidence_set)


def decision_id(claim: str, disposition: str) -> str:
    """``H(claim_id, disposition)``: one decision per claim (SPEC 7.6)."""
    return H(DECISION_TAG, claim, disposition)


def question_id(claim: str, kind: str) -> str:
    """``H(claim_id, "question", kind)`` (SPEC 4.3, S-7.6)."""
    return H(QUESTION_TAG, claim, "question", kind)


def identity_digest(name: str, value: Any) -> str:
    """Digest of one component of the input identity vector (SPEC 10.3), as ``stale_detected`` records it."""
    return H(IDENTITY_TAG, name, value)


def step_key(
    step: str, plan_version: str, dependencies: list[list[Any]], identities: dict[str, str], cfg_digest: str
) -> str:
    """``K(s) = H("citerift-step/1", s, plan version, out(dep(s)), id_s, config digest)`` (S-9.3, MM 10.1).

    ``dependencies`` is ``[[step, [output digests]], ...]`` of the committed steps ``s`` reads, in plan order;
    ``identities`` maps each identity component ``s`` depends on to its ``identity_digest``."""
    return H(STEP_TAG, step, plan_version, dependencies, identities, cfg_digest)
