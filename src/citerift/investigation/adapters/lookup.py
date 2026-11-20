"""LOOKUP: bounded Stage 02 lookups of the committed candidate inputs (Step 8; SPEC 6.4, S-3.1, S-3.2, D-048, D-062).

The index is opened once per attempt with Stage 02 ``Index(Path)``; an index that cannot be opened fails the step with
Stage 02's code (``INDEX_MISSING``, ``INDEX_CORRUPT``, ``INDEX_FORMAT_MISMATCH``). Its identity is the canonical Stage
02 content identity of owner decision D-062: snapshot id, policy version, lookup-result schema version and the Stage 02
``artifact_digest`` recomputed from the index content, with ``semantic_digest`` and ``export_lines`` as consistency
metadata. The identity is accepted only after the D-062 identity-verification profile (``verify_index_identity``, owner
decision OD-S12-1), built from Stage 02's own checks, proves that the content matches it; the raw SQLite bytes are never
part of it, so a byte-different but canonically equal rebuild is the same input. The identity is recorded once per
attempt, as the index identity observation. Every query of the committed candidate inputs (Q1 per key, Q2 per pair) runs
through ``citerift.investigation.lookup.bounded_gather``, that is ``Index.gather_bounded`` with
``config.lookup_evidence_budget_bytes``, and never through the unbounded ``gather``:

- within the budget the observation holds Stage 02's rendered result and every event, unpaged;
- over the budget it is ``unavailable`` with no events and ``LOOKUP_EVIDENCE_LIMIT_EXCEEDED`` (all or nothing);
- a query that raises is ``unavailable`` with its error code (S-6.10), never ``no_record``;
- beside the unchanged public events, ``records`` holds each event's bibliographic fields (title, authors, journal,
  original year) from the same Stage 02 event that ``Index.gather_bounded`` returned, bound to the public event by
  ``event_id`` and Stage 02's ``row_sha256`` (dt-3, owner decision D-083; Stage 02 HANDOFF: read through ``Index``).
  The D-048 byte budget already counts every stored event column, so the budget and the events are unchanged, but
  ``records`` repeats title and journal, so the observation's bytes per budget byte (rho) grow: measured at most
  13.07 over the D-048 shapes, with no analytic bound (reviewer finding E-07;
  ``docs/verification/stage-04/final-cycle/bounds/bounds.json``); an observation above the blob limit is
  ``BLOB_TOO_LARGE``, a ``STORAGE_ERROR`` (fail closed).

Each lookup observation is returned as an individual ``observation_recorded`` record; the controller batches them
(D-055). The index file must not change during the attempt: an operational guard (the file's stat fingerprint and its
SHA-256, before and after) fails the attempt closed when it does; the guard never enters any identity. The verified
identity must equal the index identity the step was keyed with (``StepRequest.identities``), so the step key and the
lookups always name the same index.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from citerift.investigation import lookup as bounded
from citerift.investigation.adapters import ContentRecord, Failed, StepRequest, StepResult, Succeeded
from citerift.investigation.canonical import canon, sha256_hex
from citerift.investigation.schemas import CANDIDATE_INPUTS, LOOKUP_OBSERVATION, LOOKUP_PLAN, problems
from citerift.retraction import export, policy
from citerift.retraction.query import MAX_PAGE, Evidence, Index, QueryError, normalize_query, public_event, render
from citerift.retraction.store import (
    APPLICATION_ID,
    DIGEST_KEYS,
    INDEX_FORMAT,
    SCHEMA_VERSION,
    IndexUnavailable,
    manifest_path_for,
    structural_problems,
)

# Version 2 (D-062): the observation's index identity is the canonical Stage 02 content identity.
# Version 3 (D-083): the observation records each event's bibliographic fields (``records``) for bib-1; unchanged
# for bib-2 (dt-4).
SCHEMA_VERSION_OBS = "3.0.0"
RECORD_FIELDS = ("title", "authors", "journal", "original_year")
SCHEMA_VERSION_PLAN = "1.0.0"
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


Fingerprint = tuple[int, int, int, int, int]


def fingerprint(path: Path) -> Fingerprint:
    """The file's stat fingerprint: device, inode, size, mtime_ns and ctime_ns (D-062). An operational signal only."""
    st = os.stat(path)
    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)


class IndexNotVerified(Exception):
    """The index content does not prove the canonical identity it claims (D-062); fails closed with ``code``."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def identity_verification_problems(index: Index) -> tuple[list[str], dict[str, str]]:
    """The D-062 identity-verification profile (owner decision OD-S12-1): Stage 02's own checks of everything LOOKUP
    and the canonical identity depend on, over the open index, and the digests recomputed from its content.

    - Stage 02 format and policy compatibility (``application_id``, ``user_version``, ``meta.policy_version``; also
      refused by Stage 02 ``Index`` on open);
    - ``PRAGMA integrity_check``, foreign keys and the accounting invariants (``structural_problems``);
    - ``artifact_digest``, ``semantic_digest`` and ``export_lines`` recomputed from the content (``compute_digests``)
      and compared with the stored metadata;
    - the build manifest published beside the index (``manifest_problems``; a missing manifest is a problem);
    - every derived table recomputed from the raw records and compared with the stored one (``derivation_problems``).

    This is not Stage 02's complete ``verify``: that certification of the artifact also re-validates every stored event
    against the event JSON Schema, and it stays Stage 02's (run in the Step 12 evidence, not in every Stage 04 process).
    The differential tamper evidence is ``docs/verification/stage-04/freeze/d062/tamper_differential.py``."""
    conn = index.conn
    manifest_path = manifest_path_for(index.path)
    problems = []
    app = conn.execute("PRAGMA application_id").fetchone()[0]
    ver = conn.execute("PRAGMA user_version").fetchone()[0]
    if app != APPLICATION_ID or ver != INDEX_FORMAT:
        problems.append(f"FORMAT_MISMATCH: application_id {app:#x}, user_version {ver}")
    meta = dict(conn.execute("SELECT key, value FROM meta").fetchall())
    if meta.get("policy_version") != policy.POLICY_VERSION:
        problems.append(f"POLICY_MISMATCH: {meta.get('policy_version')!r}")
    problems += structural_problems(conn)
    digests = export.compute_digests(conn)
    for key in DIGEST_KEYS:
        if meta.get(key) != digests[key]:
            problems.append(f"DIGEST_MISMATCH: {key} stored {meta.get(key)} recomputed {digests[key]}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        manifest = None
    problems += export.manifest_problems(meta, manifest if isinstance(manifest, dict) else None)
    problems += export.derivation_problems(conn)
    return problems, digests


def verify_index_identity(index: Index) -> dict[str, Any]:
    """The canonical Stage 02 identity of an open index, accepted only when the D-062 identity-verification profile
    (``identity_verification_problems``) finds no problem; ``IndexNotVerified`` (``INDEX_CORRUPT``) otherwise. Metadata
    alone is never trusted: the digests are recomputed."""
    try:
        problems, digests = identity_verification_problems(index)
    except (sqlite3.Error, KeyError, ValueError, TypeError) as exc:
        raise IndexNotVerified("INDEX_CORRUPT", f"verification raised {type(exc).__name__}: {exc}"[:1000]) from None
    if problems:
        raise IndexNotVerified("INDEX_CORRUPT", ("; ".join(problems[:3]) + f" ({len(problems)} problems)")[:1000])
    return index_identity(index, digests)


def index_identity(index: Index, digests: dict[str, str]) -> dict[str, Any]:
    """S-3.2 (D-062): the canonical index identity recorded once per LOOKUP attempt."""
    return {
        "snapshot_id": index.snapshot_id,
        "policy_version": policy.POLICY_VERSION,
        "lookup_schema_version": SCHEMA_VERSION,
        "artifact_digest": digests["artifact_digest"],
        "semantic_digest": digests["semantic_digest"],
        "export_lines": int(digests["export_lines"]),
    }


@dataclass
class IndexVerifier:
    """Process-local reuse of a verified canonical identity (D-062).

    An entry is keyed by the resolved path and the file's stat fingerprint (device, inode, size, mtime_ns, ctime_ns),
    re-read on every use, so any change of the fingerprint misses the entry and verifies again. The fingerprint is the
    one taken before the verified index was opened, and the entry is kept only when the path still has it after the
    verification, so a file replaced between the open and the verification is never stored under the new file's
    fingerprint (Step 12 D-062 test). Failures are never kept.
    Nothing is persisted and nothing is shared between processes or between ``Integration`` objects; with
    ``enabled=False`` every call verifies, which must give the same identities (cache-disabled equivalence)."""

    enabled: bool = True
    verifications: int = 0
    _entries: dict[tuple[str, Fingerprint], dict[str, Any]] = field(default_factory=dict, repr=False)

    def identity(
        self,
        path: Path,
        index: Index | None = None,
        opener: Callable[[Path], Index] = Index,
        *,
        before: Fingerprint | None = None,
    ) -> dict[str, Any]:
        """The verified identity of the index at ``path``. With an already open ``index``, ``before`` must be the
        fingerprint of ``path`` taken before that index was opened."""
        if index is not None and before is None:
            raise ValueError("an open index needs the fingerprint taken before it was opened")
        resolved = str(Path(path).resolve())
        if before is None:
            before = fingerprint(path)
        cached = self._entries.get((resolved, before)) if self.enabled else None
        if cached is not None:
            return _current_versions(cached)
        if index is None:
            with opener(path) as opened:
                ident = self._verify(opened)
        else:
            ident = self._verify(index)
        if fingerprint(path) != before:
            raise IndexNotVerified("INDEX_CORRUPT", "the index file changed during its verification")
        if self.enabled:
            self._entries = {k: v for k, v in self._entries.items() if k[0] != resolved}
            self._entries[(resolved, before)] = copy.deepcopy(ident)
        return _current_versions(ident)

    def _verify(self, index: Index) -> dict[str, Any]:
        self.verifications += 1
        return verify_index_identity(index)


def _current_versions(ident: dict[str, Any]) -> dict[str, Any]:
    """A reused identity with the policy and lookup-schema versions of the running code: they are not properties of
    the file, so a cached entry never carries an older code's versions."""
    out = copy.deepcopy(ident)
    out["policy_version"] = policy.POLICY_VERSION
    out["lookup_schema_version"] = SCHEMA_VERSION
    return out


def environment_identity(path: Path, verifier: IndexVerifier | None = None) -> dict[str, Any]:
    """The Stage 02 identity LOOKUP depends on (SPEC 10.3, D-062): the verified canonical identity, or the code it
    cannot be established with. An unavailable or unverifiable index is not a new identity: wherever a committed step
    depends on it, the controller refuses with that code instead of declaring the investigation stale (MM 10.2)."""
    try:
        return (verifier or IndexVerifier(enabled=False)).identity(path)
    except IndexUnavailable as exc:
        return {"unavailable": exc.code}
    except IndexNotVerified as exc:
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
    records = [
        {"event_id": e.get("event_id"), "row_sha256": e.get("row_sha256"), **{k: e.get(k) for k in RECORD_FIELDS}}
        for e in ev.events
    ]
    return {
        "schema": LOOKUP_OBSERVATION,
        "schema_version": SCHEMA_VERSION_OBS,
        "query": {"doi": doi, "pmid": pmid},
        "index": ident,
        "budget_bytes": budget,
        "result": result,
        "events": events,
        "records": records,
        "event_count": len(events),
    }


def committed_inputs(req: StepRequest) -> tuple[str, dict[str, Any]]:
    for digest in req.inputs.get("NORMALIZE") or ():
        value = req.read_blob(digest)
        if isinstance(value, dict) and value.get("schema") == CANDIDATE_INPUTS:
            return digest, value
    raise ValueError("no committed candidate inputs")


Opener = Callable[[Path], Index]


def make_lookup(opener: Opener = Index, verifier: IndexVerifier | None = None) -> Callable[[StepRequest], StepResult]:
    """The LOOKUP adapter. ``opener`` is Stage 02 ``Index`` (tests may wrap it to inject a failing query);
    ``verifier`` is the process-local verified-identity reuse of D-062 (a fresh, disabled one when omitted)."""
    check = verifier if verifier is not None else IndexVerifier(enabled=False)

    def lookup(req: StepRequest) -> StepResult:
        inputs_digest, inputs = committed_inputs(req)
        found = problems(inputs, CANDIDATE_INPUTS)
        if found:
            return Failed("ADAPTER_INCONSISTENT", detail="candidate inputs: " + "; ".join(found[:3]))
        budget = req.request["config"]["lookup_evidence_budget_bytes"]
        path = Path(req.request["index_path"])
        try:
            before = fingerprint(path)
            sha = file_sha256(path)
            index = opener(path)
        except IndexUnavailable as exc:
            code = exc.code if exc.code in INDEX_CODES else "INDEX_CORRUPT"
            return Failed(code, detail=str(exc)[:1000])
        except OSError as exc:
            return Failed("INDEX_MISSING", detail=f"{path.name}: {exc.strerror}"[:1000])
        with index:
            try:
                ident = check.identity(path, index, before=before)
            except IndexNotVerified as exc:
                return Failed(exc.code, detail=exc.detail)
            except OSError as exc:
                return Failed("INDEX_MISSING", detail=f"{path.name}: {exc.strerror}"[:1000])
            keyed = (req.identities or {}).get("index")
            if keyed is not None and keyed != ident:
                return Failed("INDEX_CORRUPT", detail="the index identity changed after the step was keyed")
            observations = [observe(index, ident, q["doi"], q["pmid"], budget) for q in inputs["queries"]]
        try:
            changed = fingerprint(path) != before or file_sha256(path) != sha
        except OSError:
            changed = True
        if changed:
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
            "schema_version": SCHEMA_VERSION_PLAN,
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
