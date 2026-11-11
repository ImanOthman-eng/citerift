"""Validation of a journal against the Memory invariants, and the fold it yields (SPEC 8.6, 8.7; MM 7).

``Folder.apply`` checks one record against everything already applied and then updates the state. It is used in two
places with the same code:

- on open, over the whole journal: any violation makes the investigation ``CORRUPT`` (nothing is repaired);
- before an append, on the proposed record: a violation is a defect and the record is never written (S-9.1).

``apply`` checks before it changes anything, so a refused record leaves the state unchanged.

What Memory checks (the parts of M-1 to M-14 that belong to Memory; the transition rules T-* and W-1 to W-8 are the
Workflow Controller's, Step 7):

- schema of every record (``urn:citerift:schema:investigation:v1:journal-record``) and journal version ``v = 3``;
- M-1 ``seq`` without gaps, ``at`` never decreasing; M-2 ``prev`` chain and ``digest``;
- the creation identities: genesis, ``config_digest``, ``request_key``, ``investigation_key``, ``investigation_id``
  and the D-042 bound arithmetic (S-4.7, MM 2.3, 3.2);
- M-3 and M-5: every blob a record names exists, is a regular file, hashes to its name and is canonical;
- M-6 commit discipline: one open attempt at a time; content and terminal records belong to the open attempt;
  attempt numbers count up from 1; content counts only when its attempt ends ``step_succeeded``;
- M-4, M-7, M-10: every id a content record refers to is defined by an earlier record of the right layer that is
  committed, or earlier in the same attempt; ids are defined once in the committed view. A claim's evidence and a
  report's projections are content-addressed sets (owner decision D-047, ``sets.py``): the set blob must exist, be
  valid, agree with the record, and every id it names must resolve; a missing or corrupt set is a violation, never an
  empty set;
- evidence batches (owner decision D-053, SPEC 8.8): evidence is committed in content-addressed batches, one
  ``evidence_batch_recorded`` record each. Every batch must exist, be canonical and schema-valid (M-3), hold the
  count its record states, and every item must have the D-051 id (CH-1), name a recorded observation (M-10), refer
  only to evidence defined before it (M-4) and be defined once (M-14). When the attempt ends ``step_succeeded``, its
  batches must be numbered 0..total-1 and be exactly the canonical batches of its items (dependency order, byte
  ceiling, ``batches.py``). The batches of an attempt become authoritative only then; the evidence index (id to batch)
  is rebuilt from the journal and the blobs on every open and is never stored;
- M-8: a supersession links two claims and the successor has evidence the old claim did not have;
- M-9: ``root_id`` is null until the ACQUIRE ``step_succeeded``, which binds exactly the root its payload holds,
  whose id is recomputed from the subject identity and must match the request; every later record carries it;
- M-14: no step is started again after it succeeded, so there is at most one ``step_succeeded`` per step;
- M-12 is carried by the claim and report schemas (no global negative is representable).
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from citerift.contracts.formats import parse_utc_timestamp
from citerift.investigation import batches, ids, report, sets
from citerift.investigation.canonical import H
from citerift.investigation.errors import BlobError, CanonError, InvariantViolation
from citerift.investigation.journal import JOURNAL_FORMAT
from citerift.investigation.schemas import EVIDENCE_BATCH, RECORD, problems

STEPS = ("VALIDATE", "ACQUIRE", "EXTRACT", "NORMALIZE", "LOOKUP", "DETECT", "ASSEMBLE", "VERIFY")
TERMINAL = {"step_succeeded", "step_failed", "step_deferred", "step_interrupted"}
CONTENT_LAYER = {
    "observation_recorded": "observation",
    "evidence_batch_recorded": "evidence",
    "claim_recorded": "claim",
    "decision_recorded": "decision",
    "question_opened": "question",
    "question_closed": "question",
    "report_recorded": "report",
    "claim_superseded": "history",
    "verification_recorded": "verification",
}
# MM 7.3: C(J) covers the committed content of these layers only.
DIGEST_LAYERS = {"observation", "evidence", "claim", "decision", "question", "report"}
CONTENT_TAG = "citerift-investigation-content/1"

BlobCheck = Callable[[str], None]
BlobRead = Callable[[str], Any]  # the parsed canonical JSON of a verified blob


@dataclass
class Attempt:
    step: str
    number: int
    start_seq: int
    end_seq: int | None = None
    end_kind: str | None = None
    retryable: bool | None = None
    content: list[int] = field(default_factory=list)


@dataclass
class _Defs:
    """Ids defined by content records: by layer. ``evidence`` maps an evidence id to the batch that holds it (D-053);
    ``batches`` are the batch digests in commit order, and ``items`` the (id, refs, canonical size) of the open
    attempt's evidence in batch order, kept only until the attempt ends (its canonical form is checked then)."""

    observations: set[str] = field(default_factory=set)
    observation_list: list[dict[str, str]] = field(default_factory=list)  # {blob, obs_kind} in commit order
    evidence: dict[str, str] = field(default_factory=dict)
    batches: list[str] = field(default_factory=list)
    batch_counts: list[int] = field(default_factory=list)
    batch_total: int | None = None
    items: list[tuple[str, tuple[str, ...], int]] = field(default_factory=list)
    claims: dict[str, dict[str, Any]] = field(default_factory=dict)
    decisions: dict[str, dict[str, str]] = field(default_factory=dict)  # id -> {claim_id, disposition}
    questions: dict[str, dict[str, Any]] = field(default_factory=dict)  # id -> {claim_id, kind, open}
    superseded: dict[str, str] = field(default_factory=dict)


def _violation(invariant: str, code: str, detail: str, seq: int | None) -> InvariantViolation:
    return InvariantViolation(invariant, code, detail, seq)


class Folder:
    """``blob_check`` verifies that a named blob exists and is intact; ``blob_read`` returns its parsed content (the
    evidence and projection sets). Both are None for a replay over records Memory has already validated (the
    workflow check), which then checks no blob and resolves no set."""

    def __init__(
        self, blob_check: BlobCheck | None, *, expected_key: str | None = None, blob_read: BlobRead | None = None
    ) -> None:
        self.blob_check = blob_check
        self.blob_read = blob_read
        self.expected_key = expected_key
        self.records: list[dict[str, Any]] = []
        self.created: dict[str, Any] | None = None
        self.key: str | None = None
        self.last_digest: str | None = None
        self.last_at: datetime | None = None
        self.root_id: str | None = None
        self.root: dict[str, Any] | None = None
        self.bind_seq: int | None = None
        self.attempts: dict[str, list[Attempt]] = {s: [] for s in STEPS}
        self.open: Attempt | None = None
        self.committed = _Defs()
        self.pending = _Defs()
        self.committed_seqs: list[int] = []
        self.stale = False

    # Lookups across the committed view and the open attempt --------------------------------------------------------

    def _has_observation(self, digest: str) -> bool:
        return digest in self.committed.observations or digest in self.pending.observations

    def evidence_batch(self, eid: str) -> str | None:
        """The digest of the batch that holds evidence ``eid``, committed or in the open attempt."""
        return self.committed.evidence.get(eid) or self.pending.evidence.get(eid)

    def evidence_item(self, eid: str) -> dict[str, Any] | None:
        """The evidence item ``eid`` read from its batch; None when it is not defined or this fold reads no blobs."""
        digest = self.evidence_batch(eid)
        if digest is None or self.blob_read is None:
            return None
        found = [i for i in self.blob_read(digest)["items"] if i["evidence_id"] == eid]
        return found[0] if found else None

    def _claim(self, cid: str) -> dict[str, Any] | None:
        return self.committed.claims.get(cid) or self.pending.claims.get(cid)

    def _question(self, qid: str) -> dict[str, Any] | None:
        return self.pending.questions.get(qid) or self.committed.questions.get(qid)

    def _defined(self, layer: str, ident: str) -> bool:
        both = (self.committed, self.pending)
        if layer == "evidence":
            return any(ident in d.evidence for d in both)
        if layer == "claim":
            return any(ident in d.claims for d in both)
        if layer == "decision":
            return any(ident in d.decisions for d in both)
        return any(ident in d.questions for d in both)

    # Checks --------------------------------------------------------------------------------------------------------

    def _blob(self, digest: str, seq: int, invariant: str) -> None:
        if self.blob_check is None:
            return
        try:
            self.blob_check(digest)
        except BlobError as exc:
            raise _violation(invariant, exc.code, f"blob {digest}: {exc.detail}", seq) from exc

    def _read_set(self, digest: str, seq: int) -> Any:
        """The parsed set blob, or None when this fold reads no blobs. A missing or corrupt set is a violation."""
        if self.blob_read is None:
            return None
        try:
            return self.blob_read(digest)
        except (BlobError, CanonError) as exc:
            raise _violation("M-3", exc.code, f"set {digest}: {exc}", seq) from exc

    def _evidence_set(self, claim: dict[str, Any], seq: int) -> set[str] | None:
        """D-047: the evidence ids of a claim, from its validated evidence set; None when this fold reads no blobs."""
        value = self._read_set(claim["evidence_set"], seq)
        if value is None:
            return None
        problem = sets.evidence_set_problem(value) or sets.claim_set_problem(claim, value)
        if problem:
            raise _violation("M-7", "EVIDENCE_SET_INVALID", f"claim {claim['claim_id']}: {problem}", seq)
        return sets.set_ids(value)

    def _check_created(self, rec: dict[str, Any], seq: int) -> str:
        p = rec["payload"]
        request, cfg = p["request"], p["request"]["config"]
        if not ids.live_bound_consistent(cfg):
            raise _violation("D-042", "CONFIG_INVALID", "t_acq_ms is not deadline + op_timeout + 30000", seq)
        if p["stage04"]["plan_version"] != cfg["plan_version"]:
            raise _violation("S-4.7", "INVESTIGATION_IDENTITY_MISMATCH", "plan version differs from config", seq)
        cdig = ids.config_digest(cfg)
        if p["config_digest"] != cdig:
            raise _violation(
                "S-4.7", "INVESTIGATION_IDENTITY_MISMATCH", "config_digest is not SHA-256(canon(config))", seq
            )
        live = ids.live_request_key(request)
        if live is not None and p["request_key"] != live:
            raise _violation("S-4.7", "INVESTIGATION_IDENTITY_MISMATCH", "request_key differs from the request", seq)
        key = ids.investigation_key(p["request_key"], cfg["plan_version"], cdig)
        if p["investigation_key"] != key:
            raise _violation("S-4.7", "INVESTIGATION_IDENTITY_MISMATCH", "investigation_key is not derived", seq)
        if p["investigation_id"] != ids.investigation_id(key):
            raise _violation("S-4.8", "INVESTIGATION_IDENTITY_MISMATCH", "investigation_id is not derived", seq)
        if self.expected_key is not None and key != self.expected_key:
            raise _violation("S-8.1", "INVESTIGATION_IDENTITY_MISMATCH", "directory name is not the key", seq)
        return key

    def _check_root(self, rec: dict[str, Any], seq: int) -> None:
        """M-9 and S-4.4: the bind carries exactly the root its payload holds, matching the request."""
        if self.created is None:
            raise _violation("M-9", "ROOT_IDENTITY_MISMATCH", "no investigation_created record", seq)
        root = rec["payload"]["root"]
        subject = root["subject"]
        want = ids.root_id(subject["type"], subject["identity"])
        if root["root_id"] != want or rec["root_id"] != want:
            raise _violation("M-9", "ROOT_IDENTITY_MISMATCH", "root_id is not H(type, identity) of the bound root", seq)
        rk = self.created["request_key"]
        ident = subject["identity"]
        if "capture_sha256" in rk:
            ok = ident["capture_sha256"] == rk["capture_sha256"]
        else:
            ok = ident["wiki"] == rk["wiki"] and ident["revision_id"] == rk["revision_id"]
        if not ok:
            raise _violation("M-9", "ROOT_IDENTITY_MISMATCH", "the bound root does not match the request", seq)

    def _check_batch(self, p: dict[str, Any], seq: int) -> list[tuple[str, tuple[str, ...], int]] | None:
        """D-053: one evidence batch record against everything before it; returns (id, refs, size) of its items, or
        None when this fold reads no blobs (a replay over validated records)."""
        d = self.pending
        if p["batch_index"] != len(d.batches):
            raise _violation("S-8.8", "BATCH_SEQUENCE", f"batch_index {p['batch_index']} where {len(d.batches)}", seq)
        if p["batch_index"] >= p["batch_total"] or (d.batch_total is not None and p["batch_total"] != d.batch_total):
            raise _violation("S-8.8", "BATCH_SEQUENCE", f"batch_total {p['batch_total']} is inconsistent", seq)
        if p["batch"] in d.batches or p["batch"] in self.committed.batches:
            raise _violation("M-14", "DUPLICATE_ID", f"batch {p['batch']} is already recorded", seq)
        value = self._read_set(p["batch"], seq)
        if value is None:
            return None
        found = problems(value, EVIDENCE_BATCH)
        if found:
            raise _violation("M-3", "EVIDENCE_BATCH_INVALID", f"batch {p['batch']}: " + "; ".join(found[:3]), seq)
        items = value["items"]
        if len(items) != p["evidence_count"]:
            raise _violation("M-3", "EVIDENCE_BATCH_INVALID", "evidence_count is not the number of items", seq)
        local: set[str] = set()
        out = []
        for item in items:
            eid = item["evidence_id"]
            if eid != ids.evidence_id(item["observation"], item["pointer"], item["kind"]):
                raise _violation(
                    "CH-1", "EVIDENCE_ID_INVALID", f"evidence {eid} is not H(observation, pointer, kind)", seq
                )
            if not self._has_observation(item["observation"]):
                raise _violation("M-10", "DANGLING_REFERENCE", f"observation {item['observation']} not recorded", seq)
            for r in item["refs"]:
                if r not in local and not self._defined("evidence", r):
                    raise _violation("M-4", "DANGLING_REFERENCE", f"evidence ref {r} is not earlier evidence", seq)
            if eid in local or self._defined("evidence", eid):
                raise _violation("M-14", "DUPLICATE_ID", f"evidence {eid} is already defined", seq)
            local.add(eid)
            out.append((eid, tuple(item["refs"]), batches.item_bytes(item)))
        return out

    def _check_attempt_batches(self, seq: int) -> None:
        """D-053 at ``step_succeeded``: the attempt's batches are complete and are exactly the canonical batches of its
        items (dependency order with the evidence-id tie-break, then the byte ceiling)."""
        d = self.pending
        if not d.batches:
            return
        if len(d.batches) != d.batch_total:
            raise _violation("S-8.8", "BATCH_SEQUENCE", f"{len(d.batches)} of {d.batch_total} batches recorded", seq)
        if self.blob_read is None:
            return
        attempt = {eid for eid, _, _ in d.items}
        nodes = [{"evidence_id": eid, "refs": list(refs)} for eid, refs, _ in d.items]
        try:
            order = [n["evidence_id"] for n in batches.dependency_order(nodes, lambda r: r not in attempt)]
        except batches.BatchError as exc:  # unreachable after the per-batch checks; kept fail-closed
            raise _violation("S-8.8", exc.code, exc.detail, seq) from exc
        if order != [eid for eid, _, _ in d.items]:
            raise _violation(
                "S-8.8", "BATCH_NOT_CANONICAL", "the evidence is not in the canonical dependency order", seq
            )
        counts = batches.boundaries([size for _, _, size in d.items], batches.BATCH_ENVELOPE)
        if counts != d.batch_counts:
            raise _violation("S-8.8", "BATCH_NOT_CANONICAL", "the batch boundaries are not the canonical ones", seq)

    def _check_report(self, digest: str, seq: int) -> None:
        """D-054: the report manifest and every chunk it names, against the committed fold (``report.py``)."""
        manifest = self._read_set(digest, seq)
        if manifest is None:
            return
        read = self.blob_read
        if read is None or self.created is None:  # the manifest was read, so neither can be None
            raise _violation("M-3", "REPORT_INVALID", "the report cannot be checked without its investigation", seq)
        c = self.committed
        problem = report.fold_problem(
            manifest,
            read,
            investigation=self.created,
            root=self.root,
            claims={cid: v for cid, v in c.claims.items() if cid not in c.superseded},
            decisions=c.decisions,
            questions=c.questions,
            observations=c.observation_list,
            evidence=list(zip(c.batches, c.batch_counts, strict=True)),
        )
        if problem:
            raise _violation("M-3", "REPORT_INVALID", f"report {digest}: {problem}", seq)

    def _check_refs(self, rec: dict[str, Any], seq: int) -> Any:
        kind, p = rec["kind"], rec["payload"]

        def need(layer: str, ident: str, what: str) -> None:
            if layer == "evidence" and self.blob_read is None:
                return  # a replay over validated records reads no batch, so it knows no evidence id (D-053)
            if not self._defined(layer, ident):
                raise _violation("M-4", "DANGLING_REFERENCE", f"{what} {ident} is not an earlier {layer}", seq)

        def fresh(layer: str, ident: str) -> None:
            if self._defined(layer, ident):
                raise _violation("M-14", "DUPLICATE_ID", f"{layer} {ident} is already defined", seq)

        if kind == "observation_recorded":
            self._blob(p["blob"], seq, "M-3")
        elif kind == "evidence_batch_recorded":
            return self._check_batch(p, seq)
        elif kind == "claim_recorded":
            self._blob(p["evidence_set"], seq, "M-3")
            for e in sorted(self._evidence_set(p, seq) or ()):
                need("evidence", e, "claim evidence")
            fresh("claim", p["claim_id"])
        elif kind == "decision_recorded":
            need("claim", p["claim_id"], "decision claim")
            fresh("decision", p["decision_id"])
        elif kind == "question_opened":
            need("claim", p["claim_id"], "question claim")
            fresh("question", p["question_id"])
        elif kind == "question_closed":
            q = self._question(p["question_id"])
            if q is None or not q["open"]:
                raise _violation("M-4", "DANGLING_REFERENCE", f"question {p['question_id']} is not open", seq)
            if q["claim_id"] != p["claim_id"] or q["kind"] != p["kind"]:
                raise _violation("M-4", "DANGLING_REFERENCE", "question_closed does not match the opened question", seq)
            for e in p["evidence"]:
                need("evidence", e, "closing evidence")
        elif kind == "report_recorded":
            self._blob(p["report"], seq, "M-3")
            self._blob(p["projection_set"], seq, "M-3")
            value = self._read_set(p["projection_set"], seq)
            if value is not None:
                problem = sets.projection_set_problem(value)
                if not problem and p["projection_count"] != len(value["projections"]):
                    problem = "projection_count is not the number of projections in the set"
                if problem:
                    raise _violation("M-3", "PROJECTION_SET_INVALID", problem, seq)
                for d in value["projections"]:
                    self._blob(d, seq, "M-3")
            self._check_report(p["report"], seq)
        elif kind == "claim_superseded":
            old, new = self._claim(p["old_claim_id"]), self._claim(p["new_claim_id"])
            if old is None or new is None:
                raise _violation("M-8", "DANGLING_REFERENCE", "supersession names an undefined claim", seq)
            if p["old_claim_id"] in self.committed.superseded or p["old_claim_id"] in self.pending.superseded:
                raise _violation("M-8", "DUPLICATE_ID", "claim already superseded", seq)
            added = set(p["new_evidence"])
            new_ev, old_ev = self._evidence_set(new, seq), self._evidence_set(old, seq)
            if new_ev is not None and old_ev is not None and (not added <= new_ev or added & old_ev):
                raise _violation(
                    "M-8", "SUPERSESSION_INVALID", "new_evidence must be new evidence of the successor", seq
                )

    def _define(self, rec: dict[str, Any], checked: Any) -> None:
        kind, p, d = rec["kind"], rec["payload"], self.pending
        if kind == "observation_recorded":
            d.observations.add(p["blob"])
            d.observation_list.append({"blob": p["blob"], "obs_kind": p["obs_kind"]})
        elif kind == "evidence_batch_recorded":
            d.batches.append(p["batch"])
            d.batch_counts.append(p["evidence_count"])
            d.batch_total = p["batch_total"]
            for eid, refs, size in checked or ():
                d.evidence[eid] = p["batch"]
                d.items.append((eid, refs, size))
        elif kind == "claim_recorded":
            d.claims[p["claim_id"]] = p
        elif kind == "decision_recorded":
            d.decisions[p["decision_id"]] = {"claim_id": p["claim_id"], "disposition": p["disposition"]}
        elif kind == "question_opened":
            d.questions[p["question_id"]] = {"claim_id": p["claim_id"], "kind": p["kind"], "open": True}
        elif kind == "question_closed":
            q = self._question(p["question_id"]) or {}
            d.questions[p["question_id"]] = {**q, "open": False}
        elif kind == "claim_superseded":
            d.superseded[p["old_claim_id"]] = p["new_claim_id"]

    def _commit_pending(self) -> None:
        c, d = self.committed, self.pending
        c.observations |= d.observations
        c.observation_list.extend(d.observation_list)
        c.evidence.update(d.evidence)
        c.batches.extend(d.batches)
        c.batch_counts.extend(d.batch_counts)
        c.claims.update(d.claims)
        c.decisions.update(d.decisions)
        c.questions.update(d.questions)
        c.superseded.update(d.superseded)
        self.pending = _Defs()

    # Apply ---------------------------------------------------------------------------------------------------------

    def check(self, rec: Any) -> None:
        """Every check of ``apply`` without changing the state."""
        self._apply(rec, mutate=False)

    def apply(self, rec: Any) -> None:
        self._apply(rec, mutate=True)

    def _apply(self, rec: Any, *, mutate: bool) -> None:
        seq = len(self.records)
        if not isinstance(rec, dict):
            raise _violation("S-8.2", "JOURNAL_CORRUPT", "record is not an object", seq)
        if rec.get("v") != JOURNAL_FORMAT or isinstance(rec.get("v"), bool):
            raise _violation("S-8.7", "JOURNAL_VERSION_UNSUPPORTED", f"journal version {rec.get('v')!r}", seq)
        found = problems(rec, RECORD)
        if found:
            raise _violation("SCHEMA", "RECORD_INVALID", "; ".join(found[:3]), seq)
        # M-1
        if rec["seq"] != seq:
            raise _violation("M-1", "SEQUENCE_BROKEN", f"seq {rec['seq']} where {seq} was expected", seq)
        at = parse_utc_timestamp(rec["at"])
        if at is None:
            raise _violation("SCHEMA", "RECORD_INVALID", "at is not a UTC timestamp", seq)
        if self.last_at is not None and at < self.last_at:
            raise _violation("M-1", "SEQUENCE_BROKEN", "at decreases", seq)
        # M-2
        if rec["digest"] != ids.record_digest(rec):
            raise _violation("M-2", "CHAIN_BROKEN", "digest does not match the record", seq)
        kind, step, attempt = rec["kind"], rec["step"], rec["attempt"]
        if seq == 0:
            key = self._check_created(rec, seq)
            if rec["prev"] != ids.genesis(key):
                raise _violation("M-2", "CHAIN_BROKEN", "prev of seq 0 is not the genesis value", seq)
        elif rec["prev"] != self.last_digest:
            raise _violation("M-2", "CHAIN_BROKEN", "prev is not the digest of the previous record", seq)
        # M-9: root binding
        binds = kind == "step_succeeded" and step == "ACQUIRE"
        if binds:
            if self.root_id is not None:
                raise _violation("M-9", "ROOT_REBIND", "the root is already bound", seq)
            self._check_root(rec, seq)
        elif rec["root_id"] != self.root_id:
            raise _violation("M-9", "ROOT_MISMATCH", f"root_id {rec['root_id']} where {self.root_id} is bound", seq)
        # M-6, M-14: attempts
        if kind == "step_started":
            if self.open is not None:
                raise _violation("M-6", "ATTEMPT_OVERLAP", f"{self.open.step} attempt {self.open.number} is open", seq)
            history = self.attempts[step]
            if any(a.end_kind == "step_succeeded" for a in history):
                raise _violation("M-14", "STEP_ALREADY_SUCCEEDED", f"{step} already succeeded", seq)
            if attempt != len(history) + 1:
                raise _violation("M-6", "ATTEMPT_NUMBER", f"attempt {attempt} where {len(history) + 1} is next", seq)
        elif kind in TERMINAL or kind in CONTENT_LAYER:
            if self.open is None or self.open.step != step or self.open.number != attempt:
                raise _violation(
                    "M-6", "OUTSIDE_ATTEMPT", f"{kind} for {step} attempt {attempt} has no open attempt", seq
                )
        checked = self._check_refs(rec, seq) if kind in CONTENT_LAYER else None
        if kind == "step_succeeded":
            self._check_attempt_batches(seq)
            for out in rec["payload"]["outputs"]:
                self._blob(out, seq, "M-5")
        if not mutate:
            return
        # State update ----------------------------------------------------------------------------------------------
        self.records.append(rec)
        self.last_digest = rec["digest"]
        self.last_at = at
        if seq == 0:
            self.created = rec["payload"]
            self.key = rec["payload"]["investigation_key"]
        if kind == "stale_detected":
            self.stale = True
        if kind == "step_started":
            a = Attempt(step, attempt, seq)
            self.attempts[step].append(a)
            self.open = a
        elif kind in CONTENT_LAYER and self.open is not None:
            self._define(rec, checked)
            self.open.content.append(seq)
        elif kind in TERMINAL and self.open is not None:
            self.open.end_seq, self.open.end_kind = seq, kind
            if kind == "step_failed":
                self.open.retryable = bool(rec["payload"]["retryable"])
            if kind == "step_succeeded":
                self.committed_seqs.extend(self.open.content)
                self._commit_pending()
                if binds:
                    self.root = copy.deepcopy(rec["payload"]["root"])
                    self.root_id = rec["root_id"]
                    self.bind_seq = seq
            else:
                self.pending = _Defs()
            self.open = None

    # Derived views -------------------------------------------------------------------------------------------------

    def step_state(self, step: str) -> str:
        """MM 7.2: the state of a step from its last attempt."""
        history = self.attempts[step]
        if not history:
            return "pending"
        last = history[-1]
        if last.end_kind is None:
            return "running"
        return {
            "step_succeeded": "succeeded",
            "step_deferred": "deferred",
            "step_interrupted": "pending",
            "step_failed": "failed_retryable" if last.retryable else "failed_terminal",
        }[last.end_kind]

    def lifecycle(self) -> str:
        """MM 7.2 lifecycle of a valid journal (CORRUPT is decided by the caller before folding)."""
        states = [self.step_state(s) for s in STEPS]
        if self.stale:
            return "STALE"
        if "failed_terminal" in states:
            return "FAILED"
        if all(s == "succeeded" for s in states):
            return "NEEDS_RESOLUTION" if self.open_questions() else "COMPLETED"
        if "deferred" in states:
            return "BLOCKED"
        if any(self.attempts[s] for s in STEPS):
            return "RUNNING"
        return "CREATED"

    def open_questions(self) -> list[str]:
        return sorted(q for q, v in self.committed.questions.items() if v["open"])

    def committed_content(self) -> list[dict[str, Any]]:
        return [self.records[i] for i in self.committed_seqs]

    def content_digest(self) -> str:
        """``C(J)`` of MM 7.3: committed content of the layers observation to report, without execution data."""
        items = [
            [r["kind"], r["step"], r["payload"]]
            for r in self.committed_content()
            if CONTENT_LAYER[r["kind"]] in DIGEST_LAYERS
        ]
        return H(CONTENT_TAG, self.key, self.root_id, items)

    def referenced_blobs(self) -> set[str]:
        out: set[str] = set()
        for r in self.records:
            p = r["payload"]
            if r["kind"] == "observation_recorded":
                out.add(p["blob"])
            elif r["kind"] == "evidence_batch_recorded":
                out.add(p["batch"])
            elif r["kind"] == "claim_recorded":
                out.add(p["evidence_set"])
            elif r["kind"] == "report_recorded":
                out.update((p["report"], p["projection_set"]))
                out.update(self._projections(p["projection_set"]))
            elif r["kind"] == "step_succeeded":
                out.update(p["outputs"])
        return out

    def _projections(self, digest: str) -> list[str]:
        """The projection digests of a set, for ``referenced_blobs``; empty when the set cannot be read here."""
        if self.blob_read is None:
            return []
        try:
            value = self.blob_read(digest)
        except (BlobError, CanonError):
            return []
        found = value.get("projections") if isinstance(value, dict) else None
        return [d for d in found if isinstance(d, str)] if isinstance(found, list) else []
