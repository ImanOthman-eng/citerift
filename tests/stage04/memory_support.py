"""Helpers for the Stage 04 Investigation Memory tests (Step 6).

The workload is SYNTHETIC: it drives Memory with records shaped like the plan's (VALIDATE, ACQUIRE of a retained
bundle, EXTRACT, NORMALIZE, LOOKUP, DETECT) but its payloads are invented; it is not the Workflow Controller (Step 7)
and decides nothing. ``drive`` is resumable: from any state it closes an open attempt with ``step_interrupted`` and
continues with the first step that has not succeeded, so a crash at any point can be resumed and compared.
"""

from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from citerift.investigation import batches, ids, sets
from citerift.investigation.lookup import DEFAULT_LOOKUP_EVIDENCE_BUDGET_BYTES
from citerift.investigation.memory import InvestigationMemory, created_payload

SUBJECT = "wikipedia_article_revision"
STAGE04 = {"engine_version": "0.1.0", "table_version": "dt-1", "plan_version": "plan-1", "schema_version": "2.0.0"}
CAPTURE = hashlib.sha256(b"SYNTHETIC capture.json").hexdigest()


def h(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class Clock:
    """Deterministic clock: each call advances one second from a fixed instant."""

    def __init__(self) -> None:
        self.t = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        self.t += timedelta(seconds=1)
        return self.t


def memory_root(tmp: Path) -> Path:
    root = tmp / "memory"
    root.mkdir(mode=0o700)
    os.chmod(root, 0o700)
    return root


def bundle_request(root: Path) -> dict[str, Any]:
    return {
        "schema": "urn:citerift:schema:investigation:v1:request",
        "schema_version": "2.0.0",
        "mode": "retained_bundle",
        "subject": {"type": SUBJECT, "bundle_path": "/data/bundles/b1"},
        "index_path": "/data/index.sqlite",
        "memory_root": str(root),
        "config": {
            "plan_version": "plan-1",
            "budgets": {"a_max": 3, "f_max": 6},
            "fetch_policy_sha256": None,
            "live_acquire_bound": None,
            "lookup_evidence_budget_bytes": DEFAULT_LOOKUP_EVIDENCE_BUDGET_BYTES,
        },
    }


def live_request(root: Path) -> dict[str, Any]:
    return {
        "schema": "urn:citerift:schema:investigation:v1:request",
        "schema_version": "2.0.0",
        "mode": "live_capture",
        "subject": {"type": SUBJECT, "wiki": "ar", "revision_id": 76190003},
        "index_path": "/data/index.sqlite",
        "memory_root": str(root),
        "config": {
            "plan_version": "plan-1",
            "budgets": {"a_max": 3, "f_max": 6},
            "fetch_policy_sha256": h("policy"),
            "live_acquire_bound": {
                "deadline_ms": 180_000,
                "op_timeout_ms": 30_000,
                "safety_allowance_ms": 30_000,
                "t_acq_ms": 240_000,
            },
            "lookup_evidence_budget_bytes": DEFAULT_LOOKUP_EVIDENCE_BUDGET_BYTES,
        },
    }


def bundle_payload(root: Path, capture: str = CAPTURE) -> dict[str, Any]:
    return created_payload(bundle_request(root), STAGE04, bundle_capture_sha256=capture)


def root_object(capture: str = CAPTURE, *, wiki: str = "ar", page: int = 5, revision: int = 76190003) -> dict[str, Any]:
    identity = {"wiki": wiki, "page_id": page, "revision_id": revision, "capture_sha256": capture}
    return {
        "root_id": ids.root_id(SUBJECT, identity),
        "subject": {"type": SUBJECT, "identity": identity, "display": {"title": "SYNTHETIC", "revision_sha1": None}},
    }


def new_memory(tmp: Path) -> tuple[InvestigationMemory, Path]:
    root = memory_root(tmp)
    return InvestigationMemory.create(root, bundle_payload(root), clock=Clock()), root


# The synthetic plan ----------------------------------------------------------------------------------------------

STEPS = ("VALIDATE", "ACQUIRE", "EXTRACT", "NORMALIZE", "LOOKUP", "DETECT")


def _step_content(mem: InvestigationMemory, step: str, attempt: int) -> list[str]:
    """Write the step's blobs and content records; return its output blob digests."""
    if step == "VALIDATE":
        return [mem.put_blob({"validated": "SYNTHETIC"})]
    if step == "ACQUIRE":
        blob = mem.put_blob({"bundle": "SYNTHETIC", "capture_sha256": CAPTURE})
        mem.append("observation_recorded", _obs("bundle", blob, "open_bundle"), step=step, attempt=attempt)
        return [blob]
    if step == "EXTRACT":
        blob = mem.put_blob({"units": [{"id": "un-00001"}], "ratio": 0.5})
        mem.append("observation_recorded", _obs("extraction", blob, "extract_bundle"), step=step, attempt=attempt)
        return [blob]
    if step == "NORMALIZE":
        ext = mem.put_blob({"units": [{"id": "un-00001"}], "ratio": 0.5})  # same bytes: idempotent
        unit = _evidence("unit", ext, "/units/0", [], {"source_artifact": h("src"), "unit_span_sha256": h("span")})
        occ = _evidence(
            "identifier_occurrence",
            ext,
            "/units/0",
            [unit["evidence_id"]],
            {"status": "CONFIRMED", "key": {"scheme": "doi", "normalized": "10.1000/xyz"}},
        )
        append_evidence(mem, [unit, occ], step, attempt)
        return [mem.put_blob({"normalized": [unit["evidence_id"], occ["evidence_id"]]})]
    if step == "LOOKUP":
        blob = mem.put_blob({"lookup": "SYNTHETIC", "state": "no_record"})
        src = {"engine": "citerift.retraction", "operation": "gather", "locator": "doi:10.1000/xyz"}
        mem.append(
            "observation_recorded", {"obs_kind": "lookup", "blob": blob, "source_ref": src}, step=step, attempt=attempt
        )
        return [blob]
    # DETECT: a not-found claim with its decision.
    # Evidence over the committed LOOKUP observation (the same bytes give the same digest), then the claim.
    ev = _evidence("lookup_result", mem.put_blob({"lookup": "SYNTHETIC", "state": "no_record"}), "", [], None)
    append_evidence(mem, [ev], step, attempt)
    claim = not_found_claim(mem, ev["evidence_id"])
    mem.append("claim_recorded", claim, step=step, attempt=attempt)
    decision = {"decision_id": h("decision"), "claim_id": claim["claim_id"], "disposition": "REPORT_NOT_FOUND"}
    mem.append("decision_recorded", decision, step=step, attempt=attempt)
    return [mem.put_blob({"claims": [claim["claim_id"]]})]


def _obs(kind: str, blob: str, operation: str) -> dict[str, Any]:
    engine = "citerift.retraction" if kind in {"index_identity", "lookup"} else "citerift.wiki"
    return {"obs_kind": kind, "blob": blob, "source_ref": {"engine": engine, "operation": operation, "locator": None}}


def append_evidence(
    mem: InvestigationMemory, items: list[dict[str, Any]], step: str, attempt: int
) -> list[dict[str, Any]]:
    """Commit evidence items as the controller does (D-053): canonical batches, published, then one record each."""
    found = batches.evidence_batches(items, lambda ref: mem.view.evidence_batch(ref) is not None)
    digests = [mem.put_blob(b) for b in found]
    return [
        mem.append("evidence_batch_recorded", p, step=step, attempt=attempt)
        for p in batches.batch_records(digests, found)
    ]


def _evidence(kind: str, obs: str, pointer: str, refs: list[str], value: Any) -> dict[str, Any]:
    return {
        "evidence_id": ids.evidence_id(obs, pointer, kind),
        "observation": obs,
        "pointer": pointer,
        "kind": kind,
        "refs": refs,
        "value": value,
    }


def not_found_claim(mem: InvestigationMemory, evidence_id: str) -> dict[str, Any]:
    """A not-found claim whose evidence set (published here) names ``evidence_id`` (D-047)."""
    evidence_set = mem.put_blob(sets.evidence_set([evidence_id]))
    return {
        "claim_id": h("claim-" + evidence_id),
        "cand_ref": h("cand"),
        "candidate": {
            "shape": "DOI",
            "keys": [{"scheme": "doi", "normalized": "10.1000/xyz"}],
            "coherence": None,
        },
        "class": "NOT_FOUND_IN_CHECKED_SOURCES",
        "rule": "D-16",
        "table_version": "dt-1",
        "status": "uncertain",
        "value": "not_found_in_checked_sources",
        "alternatives": [],
        "reasons": ["NOT_FOUND_IN_CHECKED_SOURCES"],
        "upstream_reasons": [],
        "evidence_set": evidence_set,
        "supporting_count": 1,
        "contradicting_count": 0,
    }


def drive(mem: InvestigationMemory, steps: tuple[str, ...] = STEPS) -> None:
    """Run (or resume) the synthetic plan to the end of ``steps``."""
    view = mem.view
    if view.open is not None:
        mem.append("step_interrupted", {"step_key": h(view.open.step)}, step=view.open.step, attempt=view.open.number)
    for step in steps:
        if view.step_state(step) == "succeeded":
            continue
        attempt = len(view.attempts[step]) + 1
        mem.append("step_started", {"step_key": h(step)}, step=step, attempt=attempt)
        outputs = _step_content(mem, step, attempt)
        payload: dict[str, Any] = {"step_key": h(step), "outputs": outputs, "root": None}
        if step == "ACQUIRE":
            payload["root"] = root_object()
        mem.append("step_succeeded", payload, step=step, attempt=attempt)
