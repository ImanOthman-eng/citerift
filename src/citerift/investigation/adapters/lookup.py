"""LOOKUP: bounded Stage 02 lookups of the committed candidate inputs (Step 8; SPEC 6.4, S-3.1, S-3.2, D-048).

The index is opened once per attempt with Stage 02 ``Index(Path)``; an index that cannot be opened fails the step with
Stage 02's code (``INDEX_MISSING``, ``INDEX_CORRUPT``, ``INDEX_FORMAT_MISMATCH``). Its identity (snapshot, policy
version, lookup-result schema version and the SHA-256 of the index file) is recorded once, as the index identity
observation. Every query of the committed candidate inputs (Q1 per key, Q2 per pair) runs through
``citerift.investigation.lookup.bounded_gather``, that is ``Index.gather_bounded`` with
``config.lookup_evidence_budget_bytes``, and never through the unbounded ``gather``:

- within the budget the observation holds Stage 02's rendered result and every event, unpaged;
- over the budget it is ``unavailable`` with no events and ``LOOKUP_EVIDENCE_LIMIT_EXCEEDED`` (all or nothing);
- a query that raises is ``unavailable`` with its error code (S-6.10), never ``no_record``.

Each lookup observation is returned as an individual ``observation_recorded`` record; the controller batches them
(D-055). The index file must not change during the attempt: its identity is compared before and after.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Any

from citerift.investigation import lookup as bounded
from citerift.investigation.adapters import ContentRecord, Failed, StepRequest, StepResult, Succeeded
from citerift.investigation.canonical import canon, sha256_hex
from citerift.investigation.schemas import CANDIDATE_INPUTS, LOOKUP_OBSERVATION, LOOKUP_PLAN, problems
from citerift.retraction import policy
from citerift.retraction.query import MAX_PAGE, Evidence, Index, QueryError, normalize_query, public_event, render
from citerift.retraction.store import SCHEMA_VERSION, IndexUnavailable

SCHEMA_VERSION_OBS = "1.0.0"
# The record schema's source_ref operations (common.schema.json): the bounded call is Stage 02's ``gather`` operation
# with a byte budget (``Index.gather_bounded``); the budget is in every lookup observation (``budget_bytes``).
INDEX_REF = {"engine": "citerift.retraction", "operation": "index_identity", "locator": None}
GATHER_REF = {"engine": "citerift.retraction", "operation": "gather", "locator": None}
INDEX_CODES = frozenset({"INDEX_MISSING", "INDEX_CORRUPT", "INDEX_FORMAT_MISMATCH"})


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _stat(path: Path) -> tuple[int, int, int, int]:
    st = os.stat(path)
    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns)


def index_identity(index: Index, sha256: str) -> dict[str, Any]:
    """S-3.2: the index identity recorded once per LOOKUP attempt."""
    return {
        "snapshot_id": index.snapshot_id,
        "policy_version": policy.POLICY_VERSION,
        "lookup_schema_version": SCHEMA_VERSION,
        "index_sha256": sha256,
    }


def environment_identity(path: Path) -> dict[str, Any]:
    """The Stage 02 identity LOOKUP depends on (SPEC 10.3): the index identity, or the code it cannot be opened with
    (an unavailable index is an identity value too, so a repaired or replaced index is a change, never a match)."""
    try:
        sha = file_sha256(path)
        with Index(path) as index:
            return index_identity(index, sha)
    except IndexUnavailable as exc:
        return {"unavailable": exc.code}
    except OSError as exc:
        return {"unavailable": "INDEX_MISSING", "errno": exc.errno}


def failed_query(doi: str | None, pmid: str | None, code: str, detail: str) -> Evidence:
    """S-6.10: a query that raised is an unavailable lookup with the error code; never a negative."""
    query, keys, _ = normalize_query(doi, pmid)
    ev = Evidence(query, keys, "unavailable")
    ev.evidence_set = policy.EvidenceSet("unavailable", "none", None, (), ())
    ev.issues.append({"code": code, "detail": detail[:300]})
    return ev


def observe(index: Index, ident: dict[str, Any], doi: str | None, pmid: str | None, budget: int) -> dict[str, Any]:
    """One lookup observation blob."""
    try:
        ev = bounded.bounded_gather(index, doi, pmid, budget)
    except QueryError as exc:
        ev = failed_query(doi, pmid, exc.code, str(exc))
    except sqlite3.Error as exc:
        ev = failed_query(doi, pmid, "INDEX_QUERY_FAILED", f"{type(exc).__name__}: {exc}")
    result = render(ev, index.snapshot_id, page_size=MAX_PAGE)
    events = [public_event(e) for e in ev.events]
    return {
        "schema": LOOKUP_OBSERVATION,
        "schema_version": SCHEMA_VERSION_OBS,
        "query": {"doi": doi, "pmid": pmid},
        "index": ident,
        "budget_bytes": budget,
        "result": result,
        "events": events,
        "event_count": len(events),
    }


def committed_inputs(req: StepRequest) -> tuple[str, dict[str, Any]]:
    for digest in req.inputs.get("NORMALIZE") or ():
        value = req.read_blob(digest)
        if isinstance(value, dict) and value.get("schema") == CANDIDATE_INPUTS:
            return digest, value
    raise ValueError("no committed candidate inputs")


Opener = Callable[[Path], Index]


def make_lookup(opener: Opener = Index) -> Callable[[StepRequest], StepResult]:
    """The LOOKUP adapter. ``opener`` is Stage 02 ``Index`` (tests may wrap it to inject a failing query)."""

    def lookup(req: StepRequest) -> StepResult:
        inputs_digest, inputs = committed_inputs(req)
        found = problems(inputs, CANDIDATE_INPUTS)
        if found:
            return Failed("ADAPTER_INCONSISTENT", detail="candidate inputs: " + "; ".join(found[:3]))
        budget = req.request["config"]["lookup_evidence_budget_bytes"]
        path = Path(req.request["index_path"])
        try:
            before = _stat(path)
            sha = file_sha256(path)
            index = opener(path)
        except IndexUnavailable as exc:
            code = exc.code if exc.code in INDEX_CODES else "INDEX_CORRUPT"
            return Failed(code, detail=str(exc)[:1000])
        except OSError as exc:
            return Failed("INDEX_MISSING", detail=f"{path.name}: {exc.strerror}"[:1000])
        with index:
            ident = index_identity(index, sha)
            observations = [observe(index, ident, q["doi"], q["pmid"], budget) for q in inputs["queries"]]
        if _stat(path) != before or file_sha256(path) != sha:
            return Failed("INDEX_CORRUPT", detail="the index file changed during the lookup")
        for o in observations:
            bad = problems(o, LOOKUP_OBSERVATION)
            if bad:
                return Failed("ADAPTER_INCONSISTENT", detail="lookup observation: " + "; ".join(bad[:3]))
        ident_digest = sha256_hex(canon(ident))
        records = [
            ContentRecord(
                "observation_recorded", {"obs_kind": "index_identity", "blob": ident_digest, "source_ref": INDEX_REF}
            )
        ]
        digests = [sha256_hex(canon(o)) for o in observations]
        records += [
            ContentRecord("observation_recorded", {"obs_kind": "lookup", "blob": d, "source_ref": GATHER_REF})
            for d in dict.fromkeys(digests)
        ]
        plan = {
            "schema": LOOKUP_PLAN,
            "schema_version": SCHEMA_VERSION_OBS,
            "candidate_inputs": inputs_digest,
            "index_identity": ident_digest,
            "lookups": [{"query": dict(q), "observation": d} for q, d in zip(inputs["queries"], digests, strict=True)],
        }
        return Succeeded(
            records=tuple(records),
            blobs=(ident, *observations, plan),
            outputs=(sha256_hex(canon(plan)),),
        )

    return lookup
