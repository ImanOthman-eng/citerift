"""Deterministic fake adapters and a fake environment for the Workflow Controller tests (Stage 04 Step 7).

Everything here is SYNTHETIC. The adapters return results shaped like the plan's (owner Step 7 item 9) and decide
nothing scientific; the real Stage 02 and Stage 03 adapters are Step 8. A ``Plan`` maps each step to a fake adapter
whose outcome for an attempt is scripted: ``ok`` (default), a ``Failed`` or ``Deferred`` value, ``raise``, ``die``
(``os._exit`` inside the adapter: process death during the step), or any callable on the request.
"""

from __future__ import annotations

import copy
import os
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from memory_support import CAPTURE, STAGE04, bundle_payload, h, live_request, memory_root, root_object

from citerift.investigation import batches, ids, report, sets, workflow
from citerift.investigation.adapters import ContentRecord, Deferred, Failed, StepRequest, StepResult, Succeeded
from citerift.investigation.canonical import canon, sha256_hex
from citerift.investigation.controller import MonotoneClock, WorkflowController, open_controller
from citerift.investigation.fold import STEPS
from citerift.investigation.memory import InvestigationMemory, created_payload

DIE = 91
T0 = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)


class StepClock:
    """Deterministic clock: each call advances ``tick`` from ``t`` (set ``tick`` to zero to hold the time)."""

    def __init__(self, t: datetime = T0, tick: timedelta = timedelta(seconds=1)) -> None:
        self.t, self.tick = t, tick

    def __call__(self) -> datetime:
        self.t += self.tick
        return self.t


def digest(value: Any) -> str:
    return sha256_hex(canon(value, allow_float=True))


# The fake environment (input identity vector, SPEC 10.3) -----------------------------------------------------------


class Env:
    """Current identity values. ``root`` is the bound root's identity (as the controller passes it) unless a test
    overrides it."""

    def __init__(self) -> None:
        self.values: dict[str, Any] = {
            "request_key": {"capture_sha256": CAPTURE},
            "extraction": {"extractor": "SYNTHETIC-1", "profile": h("profile"), "normalizer": "n-1"},
            "index": {"index_sha256": h("index"), "format": "1"},
            "stage04": dict(STAGE04),
            "config": {"plan_version": "plan-1", "budgets": {"a_max": 3, "f_max": 6}},
        }
        self.root_override: Any = None
        self.calls = 0

    def __call__(self, root: Mapping[str, Any] | None) -> Mapping[str, Any]:
        self.calls += 1
        out = copy.deepcopy(self.values)
        out["root"] = self.root_override if self.root_override is not None else root
        return out


# Content of each step -------------------------------------------------------------------------------------------

BUNDLE = {"bundle": "SYNTHETIC", "capture_sha256": CAPTURE}
EXTRACTION = {"units": [{"id": "un-00001", "identifiers": [{"doi": "10.1000/xyz"}]}], "status": "complete"}
LOOKUP = {"lookup": "SYNTHETIC", "state": "no_record", "results": [{"a": 1}, {"b": 2}, {"c": 3}, {"d": 4}]}
DOI = {"scheme": "doi", "normalized": "10.1000/xyz"}
PMID = {"scheme": "pmid", "normalized": "24476881"}


def _obs(kind: str, blob: str, operation: str) -> dict[str, Any]:
    engine = "citerift.retraction" if kind in {"index_identity", "lookup"} else "citerift.wiki"
    return {"obs_kind": kind, "blob": blob, "source_ref": {"engine": engine, "operation": operation, "locator": None}}


def evidence(kind: str, obs: str, pointer: str, refs: list[str], value: Any) -> dict[str, Any]:
    return {
        "evidence_id": ids.evidence_id(obs, pointer, kind),
        "observation": obs,
        "pointer": pointer,
        "kind": kind,
        "refs": refs,
        "value": value,
    }


def lookup_evidence() -> list[dict[str, Any]]:
    obs = digest(LOOKUP)
    return [evidence("lookup_result", obs, f"/results/{i}", [], None) for i in range(4)]


def claim(cls: str, ev: list[str], cand: str = "cand") -> dict[str, Any]:
    """A schema-valid claim of ``cls`` over the evidence ids ``ev`` (four needed for the conflict classes). Its
    evidence set (D-047) is ``evidence_set_of(claim)``; the DETECT fake publishes it."""
    claim_, _ = claim_and_set(cls, ev, cand)
    return claim_


def claim_and_set(cls: str, ev: list[str], cand: str = "cand") -> tuple[dict[str, Any], dict[str, Any]]:
    """The claim of ``claim`` and the evidence-set blob value it names."""
    base: dict[str, Any] = {
        "cand_ref": h(cand),
        "candidate": {"shape": "DOI", "keys": [dict(DOI)], "coherence": None},
        "class": cls,
        "rule": "D-14",
        "table_version": "dt-1",
        "status": "verified_fact",
        "value": "retracted",
        "alternatives": [],
        "reasons": [],
        "upstream_reasons": [],
        "supporting": [ev[0]],
        "contradicting": [],
    }
    if cls == "NOT_FOUND_IN_CHECKED_SOURCES":
        base.update(
            rule="D-16",
            status="uncertain",
            value="not_found_in_checked_sources",
            reasons=["NOT_FOUND_IN_CHECKED_SOURCES"],
        )
    elif cls == "IDENTITY_CONFLICT":
        base.update(
            rule="D-6",
            status="conflicting",
            value=None,
            candidate={"shape": "PAIR", "keys": [dict(DOI), dict(PMID)], "coherence": "INCOMPATIBLE"},
            reasons=["IDENTITY_WITNESSED", "KEY_RESULTS_DIFFER"],
            alternatives=[
                {
                    "value": {"reached_by": dict(DOI), "work": {"doi": "10.1000/xyz", "pmid": "24476891"}},
                    "supporting": [ev[0]],
                },
                {
                    "value": {"reached_by": dict(PMID), "work": {"doi": "10.1000/other", "pmid": "24476881"}},
                    "supporting": [ev[1]],
                },
            ],
            supporting=[ev[2], ev[3]],
        )
    elif cls == "CONTRADICTION_IN_SOURCES":
        base.update(
            rule="D-7",
            status="conflicting",
            value=None,
            reasons=["RETRACTION_EVENT_TYPE_CONFLICT"],
            alternatives=[
                {"value": "retracted", "supporting": [ev[0]]},
                {"value": "correction", "supporting": [ev[1]]},
            ],
        )
    elif cls == "LOOKUP_UNAVAILABLE":
        base.update(rule="D-13", status="unavailable", value=None, reasons=["LOOKUP_QUERY_FAILED"])
    elif cls != "RETRACTED_WORK_CITED":
        raise ValueError(cls)
    value = sets.evidence_set(
        base.pop("supporting"), base.pop("contradicting"), [a["supporting"] for a in base["alternatives"]]
    )
    base["alternatives"] = [
        {"value": a["value"], "supporting_count": len(a["supporting"])} for a in base["alternatives"]
    ]
    base["evidence_set"] = digest(value)
    base["supporting_count"] = len(value["supporting"])
    base["contradicting_count"] = len(value["contradicting"])
    base["claim_id"] = ids.claim_id(base["cand_ref"], cls, base["rule"], "dt-1", base["evidence_set"])
    return base, value


def ok_result(req: StepRequest, classes: tuple[tuple[str, str], ...]) -> StepResult:
    """The successful result of each step for the synthetic investigation."""
    step = req.step
    if step == "VALIDATE":
        blob = {"validated": "SYNTHETIC"}
        return Succeeded(blobs=(blob,), outputs=(digest(blob),))
    if step == "ACQUIRE":
        return Succeeded(
            records=(ContentRecord("observation_recorded", _obs("bundle", digest(BUNDLE), "open_bundle")),),
            blobs=(BUNDLE,),
            outputs=(digest(BUNDLE),),
            root=root_object(),
        )
    if step == "EXTRACT":
        rec = ContentRecord("observation_recorded", _obs("extraction", digest(EXTRACTION), "extract_bundle"))
        return Succeeded(records=(rec,), blobs=(EXTRACTION,), outputs=(digest(EXTRACTION),))
    if step == "NORMALIZE":
        ext = digest(EXTRACTION)
        unit = evidence("unit", ext, "/units/0", [], {"source_artifact": h("src"), "unit_span_sha256": h("span")})
        occ = evidence(
            "identifier_occurrence",
            ext,
            "/units/0/identifiers/0",
            [unit["evidence_id"]],
            {"status": "CONFIRMED", "key": dict(DOI)},
        )
        out = {"normalized": [unit["evidence_id"], occ["evidence_id"]]}
        return Succeeded(
            records=(ContentRecord("evidence", unit), ContentRecord("evidence", occ)),
            blobs=(out,),
            outputs=(digest(out),),
        )
    if step == "LOOKUP":
        rec = ContentRecord("observation_recorded", _obs("lookup", digest(LOOKUP), "gather"))
        return Succeeded(records=(rec,), blobs=(LOOKUP,), outputs=(digest(LOOKUP),))
    if step == "DETECT":
        evs = lookup_evidence()
        ev_ids = [e["evidence_id"] for e in evs]
        pairs = [claim_and_set(cls, ev_ids, cand) for cls, cand in classes]
        claims = [c for c, _ in pairs]
        recs = [ContentRecord("evidence", e) for e in evs]
        recs += [ContentRecord("claim_recorded", c) for c in claims]
        out = {"claims": [c["claim_id"] for c in claims]}
        return Succeeded(records=tuple(recs), blobs=(*(v for _, v in pairs), out), outputs=(digest(out),))
    if step == "ASSEMBLE":
        blobs: list[Any] = []
        manifest = synthetic_report(req.committed, req.root, req.investigation, req.request, req.live, blobs)
        projections = sets.projection_set([])
        rec = ContentRecord(
            "report_recorded",
            {"report": digest(manifest), "projection_set": digest(projections), "projection_count": 0},
        )
        return Succeeded(records=(rec,), blobs=(*blobs, manifest, projections), outputs=(digest(manifest),))
    ver = {
        "result": "passed",
        "checks": [{"check": "W_INVARIANTS", "passed": True}],
        "content_digest": req.content_digest,
    }
    return Succeeded(records=(ContentRecord("verification_recorded", ver),))


CHECKED = [{"source_id": "retraction-watch", "locator": "rw-0123456789abcdef", "retrieved_at": "2026-10-27T00:00:00Z"}]
SNAPSHOT = "rw-0123456789abcdef"


def synthetic_report(
    committed: Any,
    root: Mapping[str, Any] | None,
    investigation: Mapping[str, str],
    request: Mapping[str, Any],
    live: bool,
    blobs: list[Any],
) -> dict[str, Any]:
    """A D-054 report manifest over the committed content records, its chunks appended to ``blobs``. Everything the
    fold cannot give (unit anchors, checked sources, identities other than the request key and the configuration) is
    SYNTHETIC and schema-valid; what the fold holds (claims, decisions, questions, observations, evidence batches,
    investigation and root) is exact, as Investigation Memory checks it (``report.fold_problem``)."""
    assert root is not None
    recs = list(committed)
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
    entries = []
    for i, c in enumerate(sorted(claims, key=lambda c: c["claim_id"])):
        d = decisions[c["claim_id"]]
        entries.append(
            {
                "claim": copy.deepcopy(c),  # an adapter builds its own values; it may not share its input
                "decision": {"decision_id": d["decision_id"], "disposition": d["disposition"]},
                "question": questions.get(c["claim_id"]),
                "unit": {
                    "unit_id": "un-00001",
                    "byte_start": 100 * i,
                    "byte_end": 100 * i + 50,
                    "unit_span_sha256": h("span"),
                },
                "checked_sources": copy.deepcopy(CHECKED) if c["class"] == "NOT_FOUND_IN_CHECKED_SOURCES" else [],
            }
        )
    works: dict[str, dict[str, Any]] = {}
    for c in claims:
        if c["class"] in report.POSITIVE:
            work = {k["scheme"]: k["normalized"] for k in c["candidate"]["keys"]}
            w = works.setdefault(canon(work).decode(), {"work": work, "classes": [], "claim_ids": []})
            w["classes"] = sorted({*w["classes"], c["class"]})
            w["claim_ids"] = sorted([*w["claim_ids"], c["claim_id"]])
    observations = [
        {"blob": r["payload"]["blob"], "obs_kind": r["payload"]["obs_kind"]}
        for r in recs
        if r["kind"] == "observation_recorded"
    ]
    evidence_refs = [
        (r["payload"]["batch"], r["payload"]["evidence_count"]) for r in recs if r["kind"] == "evidence_batch_recorded"
    ]
    open_q = bool(questions)
    unavailable = any(c["class"] == "LOOKUP_UNAVAILABLE" for c in claims)
    limitations = ["CHECKED_SOURCES_ONLY"]
    if open_q:
        limitations.append("OPEN_QUESTIONS")
    if unavailable:
        limitations.append("LOOKUP_UNAVAILABLE_FOR_SOME_CANDIDATES")
    ident = root["subject"]["identity"]
    request_key = (
        {"wiki": ident["wiki"], "revision_id": ident["revision_id"]}
        if live
        else {"capture_sha256": ident["capture_sha256"]}
    )
    header = {
        **investigation,
        "root": copy.deepcopy(dict(root)),
        "terminal_state": "NEEDS_RESOLUTION" if open_q else "COMPLETED",
        "outcome": "partial" if open_q or unavailable else "completed",
        "limitations": limitations,
        "snapshot_id": SNAPSHOT,
        "identities": {
            "request_key": request_key,
            "extraction": {
                "extractor": {
                    "name": "citerift-wiki",
                    "version": "0.3.0",
                    "profile": {"version": "1", "digest": h("profile")},
                    "parsers": {"wikitext": "mwparserfromhell 0.6.6", "html": "html5lib"},
                    "normalizer": "citerift-rde-normalizer/1",
                },
                "config_digest": h("x-config"),
                "extraction_digest": digest(EXTRACTION),
                "status": "complete",
            },
            "index": {
                "snapshot_id": SNAPSHOT,
                "policy_version": "citerift-rde-policy/1.2.0",
                "lookup_schema_version": "1.0.0",
                "index_sha256": h("index"),
            },
            "stage04": {**STAGE04},
            "config": copy.deepcopy(dict(request["config"])),
            "config_digest": h("config"),
        },
    }

    def publish(blob: Any) -> str:
        blobs.append(blob)
        return digest(blob)

    return report.build(header, entries, observations, works.values(), evidence_refs, publish)


Outcome = Any  # "ok", "raise", "die", a StepResult, or a callable(StepRequest) -> StepResult


class Plan:
    """Fake adapters for the eight steps with a per-attempt script; ``calls`` records every adapter call."""

    def __init__(
        self,
        script: Mapping[tuple[str, int], Outcome] | None = None,
        classes: tuple[tuple[str, str], ...] = (("NOT_FOUND_IN_CHECKED_SOURCES", "cand"),),
    ) -> None:
        self.script = dict(script or {})
        self.classes = classes
        self.calls: list[tuple[str, int]] = []

    def adapter(self, step: str) -> Callable[[StepRequest], StepResult]:
        def run(req: StepRequest) -> StepResult:
            self.calls.append((req.step, req.attempt))
            outcome = self.script.get((step, req.attempt), "ok")
            if outcome == "ok":
                return ok_result(req, self.classes)
            if outcome == "raise":
                raise RuntimeError("SYNTHETIC adapter failure")
            if outcome == "die":
                os._exit(DIE)
            if callable(outcome):
                return outcome(req)  # type: ignore[no-any-return]
            return outcome  # type: ignore[no-any-return]

        return run

    def adapters(self) -> dict[str, Callable[[StepRequest], StepResult]]:
        return {s: self.adapter(s) for s in STEPS}


# Investigations -----------------------------------------------------------------------------------------------------


def live_payload(root: Path) -> dict[str, Any]:
    return created_payload(live_request(root), STAGE04)


def create(tmp: Path, *, live: bool = False, clock: StepClock | None = None) -> tuple[Path, str]:
    root = memory_root(tmp)
    payload = live_payload(root) if live else bundle_payload(root)
    with InvestigationMemory.create(root, payload, clock=clock or StepClock()):
        pass
    return root, str(payload["investigation_key"])


def env_for(live: bool) -> Env:
    env = Env()
    if live:
        env.values["request_key"] = {"wiki": "ar", "revision_id": 76190003}
    return env


class Session:
    """One open controller over an investigation, closed on exit."""

    def __init__(self, root: Path, key: str, plan: Plan, env: Env, clock: StepClock) -> None:
        self.mem, self.ctl = open_controller(root, key, plan.adapters(), env, clock=clock)

    def __enter__(self) -> WorkflowController:
        return self.ctl

    def __exit__(self, *exc: object) -> None:
        self.mem.close()


def run_once(root: Path, key: str, plan: Plan, env: Env, clock: StepClock) -> Any:
    with Session(root, key, plan, env, clock) as ctl:
        return ctl.run()


def journal(root: Path, key: str) -> list[dict[str, Any]]:
    with InvestigationMemory.open(root, key, writable=False) as mem:
        return copy.deepcopy(mem.view.records)


def append_content(ctl: WorkflowController, step: str, attempt: int, content: list[tuple[str, dict[str, Any]]]) -> None:
    """Append an attempt's content as the controller's ``_succeed`` does (through its guard): the evidence items in
    canonical batches first (D-053), each batch published, then the other records in their order."""
    items = [p for kind, p in content if kind == workflow.EVIDENCE]
    found = batches.evidence_batches(items, lambda ref: ctl.view.evidence_batch(ref) is not None)
    digests = [ctl._mem.put_blob(b) for b in found]
    for payload in batches.batch_records(digests, found):
        ctl._append("evidence_batch_recorded", payload, step, attempt)
    for kind, p in content:
        if kind != workflow.EVIDENCE:
            ctl._append(kind, p, step, attempt)


def evidence_items(root: Path, key: str) -> list[dict[str, Any]]:
    """Every committed evidence item, read from its batch (D-053), in commit order."""
    with InvestigationMemory.open(root, key, writable=False) as mem:
        items = [mem.view.evidence_item(eid) for eid in mem.view.committed.evidence]
    assert all(i is not None for i in items)
    return [i for i in items if i is not None]


def kinds(root: Path, key: str) -> list[tuple[str, str | None, int | None]]:
    return [(r["kind"], r["step"], r["attempt"]) for r in journal(root, key)]


def failed(code: str, **kw: Any) -> Failed:
    return Failed(code, **kw)


def deferred(at: datetime) -> Deferred:
    return Deferred(at)


def monotone(clock: StepClock) -> MonotoneClock:
    return MonotoneClock(clock)


def raw_records(root: Path, key: str) -> list[dict[str, Any]]:
    """The records of the journal file, read without the lock (for checks while a controller holds it)."""
    from citerift.investigation.journal import parse_journal

    return list(parse_journal((root / key / "journal.jsonl").read_bytes()).records)
