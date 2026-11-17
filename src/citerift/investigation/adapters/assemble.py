"""ASSEMBLE: the D-054 report manifest over the committed fold, with real identities and anchors (Step 8).

No report or CLI expansion: the manifest and its chunks are built by ``report.build`` (D-054) exactly as in Step 7.
What Step 8 adds is that every value the fold alone cannot give is read from committed content instead of being
synthetic: the unit anchor of each claim (from the committed candidate inputs, the unit evidence and the extraction),
the checked sources of a ``NOT_FOUND_IN_CHECKED_SOURCES`` claim (from its deciding lookup, S-6.11), the extraction
identity (from the committed extraction), the index identity (from the committed index identity observation), the
request key and the configuration.

Step 10 (production ASSEMBLE): the positive works are grouped by the Stage 02 identity anchor of each positive claim's
deciding lookup (SPEC 11.1, 11.2: one entry per distinct Stage 02 work, never merged because one identifier matches),
and the projection set names one v1 projection body per positive work (``citerift.investigation.projections``), each
valid against the unchanged v1 contract. ASSEMBLE reads committed content only: the fold's records and the blobs they
name (lookup observations, the extraction, the bundle manifest and the retained ``capture.json``). It never queries
Stage 02, re-runs Stage 03, uses the network, changes a claim, resolves a question or infers a missing claim. A
projection that cannot be formed or does not validate fails the step closed with ``REPORT_INVALID``.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Callable, Mapping
from typing import Any

from citerift.investigation import explanations, ids, projections, report, sets
from citerift.investigation.adapters import ContentRecord, Failed, StepRequest, StepResult, Succeeded
from citerift.investigation.adapters.acquire import committed_manifest
from citerift.investigation.adapters.detect import committed_plan
from citerift.investigation.adapters.lookup import committed_inputs
from citerift.investigation.adapters.normalize import committed_extraction
from citerift.investigation.canonical import canon, sha256_hex

UNSTRUCTURED = "unstructured_text"


def committed_evidence(committed: Any, read_blob: Callable[[str], Any]) -> dict[str, dict[str, Any]]:
    """Every committed evidence item by id, read from its batch (D-053)."""
    out: dict[str, dict[str, Any]] = {}
    for r in committed:
        if r["kind"] == "evidence_batch_recorded":
            for item in read_blob(r["payload"]["batch"])["items"]:
                out[item["evidence_id"]] = item
    return out


def deciding_query(candidate: Mapping[str, Any]) -> dict[str, str | None] | None:
    """S-6.11: Q2 for a PAIR, Q1 of the single key otherwise, none for NONE."""
    keys = candidate["keys"]
    if candidate["shape"] == "PAIR":
        return {"doi": keys[0]["normalized"], "pmid": keys[1]["normalized"]}
    if not keys:
        return None
    k = keys[0]
    return {"doi": k["normalized"], "pmid": None} if k["scheme"] == "doi" else {"doi": None, "pmid": k["normalized"]}


def make_assemble(stage04: Mapping[str, Any]) -> Callable[[StepRequest], StepResult]:
    """The ASSEMBLE adapter; ``stage04`` is the engine identity the investigation was created with."""

    def assemble(req: StepRequest) -> StepResult:
        if req.root is None:
            raise ValueError("ASSEMBLE without a bound root")
        recs = list(req.committed)
        _, doc = committed_extraction(req)
        _, inputs = committed_inputs(req)
        plan = committed_plan(req)
        evidence = committed_evidence(recs, req.read_blob)
        superseded = {r["payload"]["old_claim_id"] for r in recs if r["kind"] == "claim_superseded"}
        claims = [
            r["payload"] for r in recs if r["kind"] == "claim_recorded" and r["payload"]["claim_id"] not in superseded
        ]
        decisions = {r["payload"]["claim_id"]: r["payload"] for r in recs if r["kind"] == "decision_recorded"}
        closed = {r["payload"]["question_id"] for r in recs if r["kind"] == "question_closed"}
        questions = {
            r["payload"]["claim_id"]: {"question_id": r["payload"]["question_id"], "kind": r["payload"]["kind"]}
            for r in recs
            if r["kind"] == "question_opened" and r["payload"]["question_id"] not in closed
        }
        candidates = {c["cand_ref"]: c for c in inputs["candidates"]}
        units = {u["unit_id"]: u for u in inputs["units"]}
        lookups = {canon(entry["query"]): entry["observation"] for entry in plan["lookups"]}
        entries = []
        for c in claims:
            cand = candidates.get(c["cand_ref"])
            if cand is None:
                raise ValueError(f"claim {c['claim_id']} names a candidate NORMALIZE did not commit")
            unit = units[cand["unit_id"]]
            index = int(unit["pointer"].rsplit("/", 1)[1])
            span = doc["units"][index]["source"]
            anchor = evidence[unit["evidence"]["unit"]]["value"]
            checked: list[Any] = []
            if c["class"] == "NOT_FOUND_IN_CHECKED_SOURCES":
                q = deciding_query(cand)
                obs = req.read_blob(lookups[canon(q)])
                checked = copy.deepcopy(obs["result"]["checked_sources"])
            d = decisions[c["claim_id"]]
            entries.append(
                {
                    "claim": copy.deepcopy(c),
                    "decision": {"decision_id": d["decision_id"], "disposition": d["disposition"]},
                    "question": questions.get(c["claim_id"]),
                    "unit": {
                        "unit_id": unit["unit_id"],
                        "byte_start": span["byte_start"],
                        "byte_end": span["byte_end"],
                        "unit_span_sha256": anchor["unit_span_sha256"],
                    },
                    "checked_sources": checked,
                }
            )
        observations = [
            {"blob": r["payload"]["blob"], "obs_kind": r["payload"]["obs_kind"]}
            for r in recs
            if r["kind"] == "observation_recorded"
        ]
        batches_ = [
            (r["payload"]["batch"], r["payload"]["evidence_count"])
            for r in recs
            if r["kind"] == "evidence_batch_recorded"
        ]
        open_q = bool(questions)
        unavailable = any(c["class"] == "LOOKUP_UNAVAILABLE" for c in claims)
        limitations = ["CHECKED_SOURCES_ONLY", "MARKERS_NOT_INTERPRETED"]
        if doc["status"] == "partial":
            limitations.append("EXTRACTION_PARTIAL")
        if unavailable:
            limitations.append("LOOKUP_UNAVAILABLE_FOR_SOME_CANDIDATES")
        if open_q:
            limitations.append("OPEN_QUESTIONS")
        if inputs["observation_keys"]:
            limitations.append("OBSERVATION_ROLE_IDENTIFIERS_NOT_DECIDED")
        if any(u["kind"] == UNSTRUCTURED for u in doc["units"]):
            limitations.append("UNSTRUCTURED_TEXT_AS_STAGE03_DEFINES")
        index_identity = req.read_blob(plan["index_identity"])
        config = copy.deepcopy(dict(req.request["config"]))
        header = {
            **req.investigation,
            "root": copy.deepcopy(dict(req.root)),
            "terminal_state": "NEEDS_RESOLUTION" if open_q else "COMPLETED",
            "outcome": report.outcome(doc["status"], open_questions=open_q, lookup_unavailable=unavailable),
            "limitations": limitations,
            "snapshot_id": index_identity["snapshot_id"],
            "identities": {
                "request_key": copy.deepcopy(dict(req.request_key)),
                "extraction": {
                    "extractor": copy.deepcopy(doc["extractor"]),
                    "config_digest": doc["config_digest"],
                    "extraction_digest": doc["extraction_digest"],
                    "status": doc["status"],
                },
                "index": copy.deepcopy(index_identity),
                "stage04": copy.deepcopy(dict(stage04)),
                "config": config,
                "config_digest": ids.config_digest(config),
            },
        }
        entries.sort(key=report.claim_key)
        statements = explanations.limitations(
            {
                "limitations": limitations,
                "article_summary": {"snapshot_id": header["snapshot_id"], "open_questions": len(questions)},
                "identities": {"config": config},
            },
            [e["claim"] for e in entries],
        )

        def deciding(claim: Mapping[str, Any]) -> Mapping[str, Any]:
            q = deciding_query(candidates[claim["cand_ref"]])
            if q is None or canon(q) not in lookups:
                raise projections.ProjectionError(f"claim {claim['claim_id']} has no committed deciding lookup")
            obs: Mapping[str, Any] = req.read_blob(lookups[canon(q)])
            return obs

        manifest_ = committed_manifest(req)
        capture = json.loads(req.read_bytes(manifest_["capture"]["blob"]))
        try:
            works, bodies = projections.build_bodies(
                entries,
                deciding,
                investigation_id=req.investigation["investigation_id"],
                root=req.root,
                capture=capture,
                source_artifact=manifest_["source"]["artifact"],
                outcome=header["outcome"],
                limitations=statements,
            )
        except projections.ProjectionError as exc:
            return Failed("REPORT_INVALID", reason="V1_PROJECTION", detail=str(exc)[:1000])
        for i, body in enumerate(bodies):
            found = projections.body_problems(body)
            if found:
                return Failed("REPORT_INVALID", reason="V1_PROJECTION", detail=f"projection {i}: {found[0]}"[:1000])
        blobs: list[Any] = []

        def publish(blob: Any) -> str:
            blobs.append(blob)
            return sha256_hex(canon(blob))

        manifest = report.build(header, entries, observations, works, batches_, publish)
        projection_set = sets.projection_set(projections.digest(b) for b in bodies)
        digest = sha256_hex(canon(manifest))
        rec = {
            "report": digest,
            "projection_set": sha256_hex(canon(projection_set)),
            "projection_count": len(bodies),
        }
        return Succeeded(
            records=(ContentRecord("report_recorded", rec),),
            blobs=(*blobs, *bodies, manifest, projection_set),
            outputs=(digest,),
        )

    return assemble
