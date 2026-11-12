"""VERIFY: named checks over the committed investigation, failing closed (Step 8; SPEC 9.7).

Opening Memory already proved M-1 to M-14 and the workflow invariants on the stored journal; VERIFY does not stop
there. It re-derives what can be re-derived from committed content alone, offline, and records one check per kind
(never one per claim, so the record stays bounded):

- ``STAGE03_CAPTURE_VERIFIED``: Stage 03 ``verify_bundle`` over the bundle rebuilt from Memory, with the committed
  extraction (capture schema, artifact hashes, listed files, source and render checks, extraction checks);
- ``EXTRACTION_ROOT_IDENTITY``: manifest, extraction and root name the same capture (S-4.6, F-15), and ``root_id``
  is recomputed;
- ``D043_UNIT_ANCHORS``: every unit evidence hash recomputed from the retained source bytes (D-043);
- ``EVIDENCE_POINTERS_RESOLVE``: every evidence pointer names a value in its observation (EV-1);
- ``EVIDENCE_SETS_RESOLVE``: every claim's evidence set is valid, agrees with the claim and resolves (D-047);
- ``D053_EVIDENCE_BATCHES``: each step's evidence batches are exactly the canonical batches of its items;
- ``D055_ENTRY_BATCHES``: the LOOKUP and DETECT batches are exactly the canonical parts of their logical entries;
- ``STAGE02_INDEX_IDENTITY``: one index identity, the same in every lookup observation and in the report;
- ``BOUNDED_LOOKUP_PROVENANCE``: every query of the candidate inputs has one committed, schema-valid lookup
  observation made within the configured budget, with all its events (D-048);
- ``NORMALIZE_REPLAY``, ``DETECT_REPLAY``, ``ASSEMBLE_REPLAY``: the pure steps re-run from committed content give
  the committed outputs (SPEC 9.7);
- ``COMPLETION_INVARIANTS``: every earlier step committed, one report, one decision per current claim with the
  disposition of its class, every conflict routed with an open question (W-7, W-8);
- ``D054_REPORT_GRAPH``: the report manifest graph is complete and equals the committed fold (D-054).

Any failing check makes the step fail with ``VERIFY_FAILED`` and the first failing check's code as its reason; no
verification record is written then.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable, Mapping
from typing import Any

from citerift.investigation import batches, ids, report, sets
from citerift.investigation.adapters import ContentRecord, Failed, StepRequest, StepResult, Succeeded
from citerift.investigation.adapters.acquire import SUBJECT_TYPE, committed_manifest, reconstruct
from citerift.investigation.adapters.assemble import committed_evidence, make_assemble
from citerift.investigation.adapters.detect import Detector, committed_plan, make_detect
from citerift.investigation.adapters.lookup import committed_inputs
from citerift.investigation.adapters.normalize import committed_extraction, normalize
from citerift.investigation.anchors import SourceArtifact, verify_unit_span
from citerift.investigation.canonical import canon, sha256_hex
from citerift.investigation.schemas import COMMON, LOOKUP_OBSERVATION, problems, ref_problems
from citerift.investigation.workflow import CONFLICT, DISPOSITION
from citerift.wiki.verify import verify_bundle

CHECKS = (
    "STAGE03_CAPTURE_VERIFIED",
    "EXTRACTION_ROOT_IDENTITY",
    "D043_UNIT_ANCHORS",
    "EVIDENCE_POINTERS_RESOLVE",
    "EVIDENCE_SETS_RESOLVE",
    "D053_EVIDENCE_BATCHES",
    "D055_ENTRY_BATCHES",
    "STAGE02_INDEX_IDENTITY",
    "BOUNDED_LOOKUP_PROVENANCE",
    "NORMALIZE_REPLAY",
    "DETECT_REPLAY",
    "ASSEMBLE_REPLAY",
    "COMPLETION_INVARIANTS",
    "D054_REPORT_GRAPH",
)
EARLIER = ("VALIDATE", "ACQUIRE", "EXTRACT", "NORMALIZE", "LOOKUP", "DETECT", "ASSEMBLE")


class CheckFailed(Exception):
    pass


def resolve(value: Any, pointer: str) -> Any:
    """RFC 6901: the value ``pointer`` names in ``value``; CheckFailed when it names none."""
    if pointer == "":
        return value
    for raw in pointer.split("/")[1:]:
        part = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(value, dict) and part in value:
            value = value[part]
        elif isinstance(value, list) and part.isdigit() and (part == "0" or not part.startswith("0")):
            if int(part) >= len(value):
                raise CheckFailed(f"pointer {pointer} is outside its observation")
            value = value[int(part)]
        else:
            raise CheckFailed(f"pointer {pointer} names no value")
    return value


def _outputs(req: StepRequest, step: str) -> tuple[str, ...]:
    return req.inputs.get(step) or ()


class _Verifier:
    def __init__(self, req: StepRequest, detector: Detector | None, stage04: Mapping[str, Any]) -> None:
        self.req = req
        self.detector = detector
        self.stage04 = stage04
        self.recs = list(req.committed)
        self.manifest = committed_manifest(req)
        self.ext_digest, self.doc = committed_extraction(req)
        self.inputs_digest, self.inputs = committed_inputs(req)
        self.plan = committed_plan(req)
        self.evidence = committed_evidence(self.recs, req.read_blob)
        superseded = {r["payload"]["old_claim_id"] for r in self.recs if r["kind"] == "claim_superseded"}
        self.claims = {
            r["payload"]["claim_id"]: r["payload"]
            for r in self.recs
            if r["kind"] == "claim_recorded" and r["payload"]["claim_id"] not in superseded
        }

    # Checks -------------------------------------------------------------------------------------------------------

    def stage03_capture_verified(self) -> None:
        with reconstruct(self.manifest, self.req.read_bytes) as path:
            result = verify_bundle(path, self.doc)
        if not result.get("verified"):
            codes = [i["code"] for i in result.get("issues") or [] if i.get("severity") == "error"]
            raise CheckFailed(f"Stage 03 verification failed: {codes[:5]}")
        if result.get("capture_sha256") != self.manifest["capture"]["blob"]:
            raise CheckFailed("the verified capture is not the retained one")

    def extraction_root_identity(self) -> None:
        root = self.req.root
        if root is None:
            raise ValueError("VERIFY without a bound root")
        ident = root["subject"]["identity"]
        if root["root_id"] != ids.root_id(SUBJECT_TYPE, dict(ident)):
            raise CheckFailed("root_id is not H(type, identity)")
        if self.manifest["identity"] != dict(ident):
            raise CheckFailed("the bundle manifest is not the bound root")
        cap = self.doc["capture"]
        if any(cap[n] != ident[n] for n in ("wiki", "page_id", "revision_id", "capture_sha256")):
            raise CheckFailed("the extraction's capture is not the bound root")
        if cap["source_artifact"] != self.manifest["source"]["artifact"]:
            raise CheckFailed("the extraction names another source artifact")
        if self.inputs["bundle"] != sha256_hex(canon(self.manifest)) or self.inputs["extraction"] != self.ext_digest:
            raise CheckFailed("the candidate inputs name another bundle or extraction")

    def d043_unit_anchors(self) -> None:
        cap = self.doc["capture"]
        source = SourceArtifact(self.req.read_bytes(cap["source_artifact"]), cap["source_artifact"])
        by_span: dict[tuple[Any, Any], list[Any]] = {}
        for ident in self.doc["identifiers"]:
            a = ident.get("source") or {}
            by_span.setdefault((a.get("byte_start"), a.get("byte_end")), []).append(ident)
        units = [e for e in self.evidence.values() if e["kind"] == "unit" and e["observation"] == self.ext_digest]
        if len(units) != len(self.doc["units"]):
            raise CheckFailed(f"{len(units)} unit anchors for {len(self.doc['units'])} units")
        root_cap = self.req.root["subject"]["identity"]["capture_sha256"]  # type: ignore[index]
        for e in units:
            span = resolve(self.doc, e["pointer"])["source"]
            if e["value"]["source_artifact"] != source.sha256:
                raise CheckFailed(f"unit evidence {e['evidence_id']} names another source artifact")
            verify_unit_span(
                e["value"]["unit_span_sha256"],
                source,
                span,
                extraction_capture=cap,
                root_capture_sha256=root_cap,
                identifiers=by_span.get((span["byte_start"], span["byte_end"]), []),
            )

    def evidence_pointers_resolve(self) -> None:
        cache: dict[str, Any] = {}
        for e in self.evidence.values():
            if e["evidence_id"] != ids.evidence_id(e["observation"], e["pointer"], e["kind"]):
                raise CheckFailed(f"evidence {e['evidence_id']} is not H(observation, pointer, kind)")
            if e["observation"] not in cache:
                cache[e["observation"]] = self.req.read_blob(e["observation"])
            resolve(cache[e["observation"]], e["pointer"])

    def evidence_sets_resolve(self) -> None:
        for cid, c in self.claims.items():
            value = self.req.read_blob(c["evidence_set"])
            problem = sets.evidence_set_problem(value) or sets.claim_set_problem(c, value)
            if problem:
                raise CheckFailed(f"claim {cid}: {problem}")
            named = [*value["supporting"], *value["contradicting"], *(i for a in value["alternatives"] for i in a)]
            missing = [i for i in named if i not in self.evidence]
            if missing:
                raise CheckFailed(f"claim {cid} names uncommitted evidence {missing[:3]}")

    def d053_evidence_batches(self) -> None:
        known: set[str] = set()
        by_step: dict[str, list[dict[str, Any]]] = {}
        for r in self.req.stored:
            if r["kind"] == "evidence_batch_recorded":
                by_step.setdefault(r["step"], []).append(r["payload"])
        for step in EARLIER:
            records = by_step.get(step, [])
            if not records:
                continue
            items = [i for p in records for i in self.req.read_blob(p["batch"])["items"]]
            again = batches.evidence_batches(items, lambda ref: ref in known)
            digests = [sha256_hex(canon(b)) for b in again]
            if digests != [p["batch"] for p in records] or len(records) != records[0]["batch_total"]:
                raise CheckFailed(f"{step}: the evidence batches are not the canonical ones")
            known.update(i["evidence_id"] for i in items)

    def d055_entry_batches(self) -> None:
        kinds = {
            "lookup_batch_recorded": (batches.lookup_key, batches.lookup_batch),
            "candidate_result_batch_recorded": (batches.candidate_key, batches.candidate_batch),
        }
        for kind, (key, build) in kinds.items():
            records = [r["payload"] for r in self.req.stored if r["kind"] == kind]
            if not records:
                continue
            entries = [e for p in records for e in self.req.read_blob(p["batch"])["entries"]]
            parts = batches.ordered_parts(entries, key, build)
            if [sha256_hex(canon(p)) for p in parts] != [p["batch"] for p in records]:
                raise CheckFailed(f"{kind}: the batches are not the canonical parts of their entries")
        lookups = [r["payload"] for r in self.recs if r["kind"] == "observation_recorded" and r["step"] == "LOOKUP"]
        logical = sorted(canon(p) for p in lookups if p["obs_kind"] == "lookup")
        stored = sorted(
            canon(e)
            for r in self.req.stored
            if r["kind"] == "lookup_batch_recorded"
            for e in self.req.read_blob(r["payload"]["batch"])["entries"]
        )
        if logical != stored:
            raise CheckFailed("the logical lookup observations are not the batch entries")

    def stage02_index_identity(self) -> None:
        ident = self.req.read_blob(self.plan["index_identity"])
        found = ref_problems(ident, COMMON + "#/$defs/index_identity")
        if found:
            raise CheckFailed(f"index identity: {found[0]}")
        committed = [
            r["payload"]["blob"]
            for r in self.recs
            if r["kind"] == "observation_recorded" and r["payload"]["obs_kind"] == "index_identity"
        ]
        if committed != [self.plan["index_identity"]]:
            raise CheckFailed("there is not exactly one committed index identity, the plan's")
        for entry in self.plan["lookups"]:
            if self.req.read_blob(entry["observation"])["index"] != ident:
                raise CheckFailed("a lookup observation names another index")

    def bounded_lookup_provenance(self) -> None:
        budget = self.req.request["config"]["lookup_evidence_budget_bytes"]
        if [e["query"] for e in self.plan["lookups"]] != self.inputs["queries"]:
            raise CheckFailed("the lookups are not the queries of the candidate inputs")
        if self.plan["candidate_inputs"] != self.inputs_digest:
            raise CheckFailed("the lookup plan names other candidate inputs")
        committed = {
            r["payload"]["blob"]
            for r in self.recs
            if r["kind"] == "observation_recorded" and r["payload"]["obs_kind"] == "lookup"
        }
        for entry in self.plan["lookups"]:
            if entry["observation"] not in committed:
                raise CheckFailed(f"lookup {entry['observation']} is not committed")
            obs = self.req.read_blob(entry["observation"])
            found = problems(obs, LOOKUP_OBSERVATION)
            if found:
                raise CheckFailed(f"lookup observation: {found[0]}")
            if obs["query"] != entry["query"] or obs["budget_bytes"] != budget:
                raise CheckFailed("a lookup answers another query or used another budget")
            res = obs["result"]
            if not obs["event_count"] == len(obs["events"]) == res["total_event_count"]:
                raise CheckFailed("a lookup observation does not hold all its events")
            if obs["events"][: len(res["events"])] != res["events"]:
                raise CheckFailed("the rendered page is not the start of the recorded events")
            codes = {i.get("code") for i in res["issues"]}
            if "LOOKUP_EVIDENCE_LIMIT_EXCEEDED" in codes and (res["lookup_state"] != "unavailable" or obs["events"]):
                raise CheckFailed("an over-budget lookup is not unavailable without events")

    def _replay_request(self, step: str) -> StepRequest:
        return dataclasses.replace(self.req, step=step)

    def normalize_replay(self) -> None:
        again = normalize(self._replay_request("NORMALIZE"))
        if not isinstance(again, Succeeded) or list(again.outputs) != [self.inputs_digest]:
            raise CheckFailed("NORMALIZE re-run from committed content gives another output")
        for rec in again.records:
            item = dict(rec.payload)
            if self.evidence.get(item["evidence_id"]) != item:
                raise CheckFailed(f"NORMALIZE re-run gives evidence {item['evidence_id']} that is not committed")

    def detect_replay(self) -> None:
        if self.detector is None:
            raise CheckFailed("no detector: DETECT cannot have committed")
        again = make_detect(self.detector)(self._replay_request("DETECT"))
        if not isinstance(again, Succeeded):
            raise CheckFailed("DETECT re-run did not succeed")
        claims = {dict(r.payload)["claim_id"] for r in again.records if r.kind == "claim_recorded"}
        if claims != set(self.claims):
            raise CheckFailed("DETECT re-run gives other claims")
        committed = [d for d in _outputs(self.req, "DETECT") if d in again.outputs]
        if not committed:
            raise CheckFailed("DETECT re-run gives another output")

    def assemble_replay(self) -> None:
        again = make_assemble(self.stage04)(self._replay_request("ASSEMBLE"))
        if not isinstance(again, Succeeded) or again.outputs[0] not in _outputs(self.req, "ASSEMBLE"):
            raise CheckFailed("ASSEMBLE re-run from committed content gives another report")

    def completion_invariants(self) -> None:
        missing = [s for s in EARLIER if not _outputs(self.req, s)]
        if missing:
            raise CheckFailed(f"steps without committed outputs: {missing}")
        reports = [r for r in self.recs if r["kind"] == "report_recorded"]
        if len(reports) != 1:
            raise CheckFailed(f"{len(reports)} committed reports")
        if any(r["kind"] == "verification_recorded" for r in self.recs):
            raise CheckFailed("a verification is already committed")
        decisions: dict[str, list[str]] = {}
        for r in self.recs:
            if r["kind"] == "decision_recorded":
                decisions.setdefault(r["payload"]["claim_id"], []).append(r["payload"]["disposition"])
        closed = {r["payload"]["question_id"] for r in self.recs if r["kind"] == "question_closed"}
        open_q = {
            r["payload"]["claim_id"]
            for r in self.recs
            if r["kind"] == "question_opened" and r["payload"]["question_id"] not in closed
        }
        candidates = {c["cand_ref"] for c in self.inputs["candidates"]}
        for cid, c in self.claims.items():
            if decisions.get(cid) != [DISPOSITION[c["class"]]]:
                raise CheckFailed(f"claim {cid} has decisions {decisions.get(cid)}")
            if c["class"] in CONFLICT and cid not in open_q:
                raise CheckFailed(f"conflict claim {cid} has no open question (W-8)")
            if c["cand_ref"] not in candidates:
                raise CheckFailed(f"claim {cid} decides a candidate NORMALIZE did not commit")

    def d054_report_graph(self) -> None:
        rec = next(r for r in self.recs if r["kind"] == "report_recorded")["payload"]
        manifest = self.req.read_blob(rec["report"])
        decisions = {
            r["payload"]["decision_id"]: {
                "claim_id": r["payload"]["claim_id"],
                "disposition": r["payload"]["disposition"],
            }
            for r in self.recs
            if r["kind"] == "decision_recorded"
        }
        questions: dict[str, dict[str, Any]] = {}
        for r in self.recs:
            p = r["payload"]
            if r["kind"] == "question_opened":
                questions[p["question_id"]] = {"claim_id": p["claim_id"], "kind": p["kind"], "open": True}
            elif r["kind"] == "question_closed":
                questions[p["question_id"]] = {**questions.get(p["question_id"], {}), "open": False}
        observations = [
            {"blob": r["payload"]["blob"], "obs_kind": r["payload"]["obs_kind"]}
            for r in self.recs
            if r["kind"] == "observation_recorded"
        ]
        evidence = [
            (r["payload"]["batch"], r["payload"]["evidence_count"])
            for r in self.recs
            if r["kind"] == "evidence_batch_recorded"
        ]
        problem = report.fold_problem(
            manifest,
            self.req.read_blob,
            investigation=self.req.investigation,
            root=self.req.root,
            claims=self.claims,
            decisions=decisions,
            questions=questions,
            observations=observations,
            evidence=evidence,
        )
        if problem:
            raise CheckFailed(problem)
        projections = self.req.read_blob(rec["projection_set"])
        found = sets.projection_set_problem(projections)
        if found or rec["projection_count"] != len(projections["projections"]):
            raise CheckFailed(f"projection set: {found or 'count'}")

    def run(self) -> list[dict[str, Any]]:
        out = []
        for name in CHECKS:
            try:
                getattr(self, name.lower())()
                out.append({"check": name, "passed": True, "detail": None})
            except Exception as exc:  # every failure of a check is that check failing (fail closed)
                out.append({"check": name, "passed": False, "detail": f"{type(exc).__name__}: {exc}"[:500]})
        return out


def make_verify(detector: Detector | None, stage04: Mapping[str, Any]) -> Callable[[StepRequest], StepResult]:
    """The VERIFY adapter. It runs every check and fails closed on the first failing one."""

    def verify(req: StepRequest) -> StepResult:
        if req.root is None:
            return Failed("VERIFY_FAILED", reason="EXTRACTION_ROOT_IDENTITY", detail="no bound root")
        try:
            results = _Verifier(req, detector, stage04).run()
        except Exception as exc:  # the committed inputs themselves cannot be read: fail closed
            return Failed("VERIFY_FAILED", reason="COMMITTED_INPUTS", detail=f"{type(exc).__name__}: {exc}"[:1000])
        failed = [r for r in results if not r["passed"]]
        if failed:
            first = failed[0]
            names = ", ".join(r["check"] for r in failed)
            return Failed("VERIFY_FAILED", reason=first["check"], detail=f"failed: {names}; {first['detail']}"[:1000])
        payload = {
            "result": "passed",
            "checks": [{"check": r["check"], "passed": True} for r in results],
            "content_digest": req.content_digest,
        }
        return Succeeded(records=(ContentRecord("verification_recorded", payload),))

    return verify
