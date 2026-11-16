"""The operations behind ``citerift-investigate`` (SPEC 13, 10.4, 9.7, S-9.2; owner decision D-052; Step 10).

Each operation returns a plain JSON-able result and an exit code from ``EXIT``; the command-line module only parses
arguments and prints. Every operation uses the production integration (``adapters.plan.Integration``: the accepted
Stage 03 and Stage 02 engines, the production dt-1 detector, the production ASSEMBLE and VERIFY); none has a
synthetic detector.

- ``run`` validates a request, derives its investigation key, creates the investigation or reopens the one the key
  names (never a second one for a key), and runs the controller until the lifecycle is terminal or the next step must
  wait. A terminal investigation is reported and not run again (S-9.4).
- ``resume`` runs an existing investigation from its journal and blobs: the controller closes an interrupted attempt
  (W-6), checks staleness (S-10.1) and runs only the next legal step; it never repeats a succeeded step and never
  sleeps (a step that may restart only later leaves the investigation ``BLOCKED`` with its ``not_before``).
- ``show`` is read-only and diagnostic: identities, lifecycle, report outcome, step states and attempts, the terminal
  record, counts, and the next legal transition with the rule that permits it (S-9.2). It prints no blob content.
- ``verify`` is read-only and runs no step: it opens the journal (Memory invariants and the D-054 report graph), checks
  the workflow invariants and the committed verification, re-runs the VERIFY checks over committed content, checks
  the current input identities (staleness) and, when given, a D-052 checkpoint. Opening the journal is not success.
- ``replay`` is read-only (S-10.3): staleness, Stage 03 ``verify_bundle`` and ``replay_bundle`` over the bundle
  retained in Memory, then NORMALIZE, production DETECT and ASSEMBLE re-run from committed content; exactly one of
  ``reproduced``, ``differs`` (with the first differing component) or ``stale`` (with the changed identities).
- ``export`` writes the user export of a verified investigation (``export.py``); ``checkpoint`` writes a D-052
  checkpoint (``checkpoint.py``).

Only ``run`` and ``resume`` of a live-capture request may use the network (through Stage 03 in the supervised ACQUIRE
child); every other operation is offline.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from citerift.contracts.formats import loads_strict
from citerift.investigation import checkpoint as d052
from citerift.investigation import explanations, workflow
from citerift.investigation import export as exporter
from citerift.investigation.adapters import StepRequest
from citerift.investigation.adapters.acquire import committed_manifest, reconstruct
from citerift.investigation.adapters.live import bound_for, make_live_acquire, policy_digest
from citerift.investigation.adapters.normalize import committed_extraction
from citerift.investigation.adapters.plan import STAGE04_IDENTITY, Integration
from citerift.investigation.adapters.verify import CheckFailed, _Verifier
from citerift.investigation.controller import run_investigation
from citerift.investigation.errors import (
    Busy,
    CorruptInvestigation,
    InvestigationMemoryError,
    PathUnsafe,
)
from citerift.investigation.fold import STEPS, Folder
from citerift.investigation.lookup import DEFAULT_LOOKUP_EVIDENCE_BUDGET_BYTES
from citerift.investigation.memory import InvestigationMemory, created_payload
from citerift.investigation.outputs import OperationError
from citerift.investigation.schemas import REQUEST, problems
from citerift.investigation.workflow import WorkflowCorrupt
from citerift.wiki.bundle import BundleError, open_bundle
from citerift.wiki.fetch import FetchPolicy
from citerift.wiki.verify import replay_bundle, verify_bundle

# Exit codes (SPEC 13). 0, 1, 2, 3 and 5 mean what they mean for the Stage 02 and Stage 03 command-line tools
# (``citerift-rde``, ``citerift-wiki``: success, internal, usage, invalid input, verification failed); 6, 8 and 9 mean
# what they mean for ``citerift-wiki`` (partial, deferred, failed); 4 is "unavailable" in both and is used for the
# closest case here, no investigation under that key; 7 is not used, because the two tools give it different meanings
# (unsupported, enrichment). 10 to 14 are investigation states those tools do not have. Every subcommand uses this one
# table. An exit code never carries a claim class.
EXIT = {
    "completed": 0,  # COMPLETED with outcome completed, and the command did what it was asked
    "internal": 1,  # an unexpected error (a defect); nothing is exported
    "usage": 2,  # the command line is wrong
    "invalid": 3,  # the request, a configuration, a checkpoint or an output path is invalid or unsafe
    "not_found": 4,  # no investigation with that key under the memory root
    "verify_failed": 5,  # a verification check failed, a replay differs, or a checkpoint does not match
    "partial": 6,  # COMPLETED with outcome partial (partial extraction or an unavailable lookup)
    "blocked": 8,  # BLOCKED: a step may restart only at or after not_before
    "failed": 9,  # FAILED: a step failed terminally
    "needs_resolution": 10,  # NEEDS_RESOLUTION: verified, with at least one open question
    "stale": 11,  # STALE, or an input identity differs from the recorded one
    "corrupt": 12,  # CORRUPT: the journal, a blob or the report graph is invalid
    "busy": 13,  # another process holds the investigation lock
    "incomplete": 14,  # CREATED or RUNNING: not terminal and not blocked (for example after a crash, before resume)
}
LIFECYCLE_STATUS = {
    "NEEDS_RESOLUTION": "needs_resolution",
    "BLOCKED": "blocked",
    "FAILED": "failed",
    "STALE": "stale",
    "CORRUPT": "corrupt",
    "CREATED": "incomplete",
    "RUNNING": "incomplete",
}
VERIFIED = ("COMPLETED", "NEEDS_RESOLUTION")
# VERIFY checks that re-run Stage 04 code (NORMALIZE, dt-1, ASSEMBLE, the v1 mapping) under the current Stage 04
# identity.
STAGE04_REDERIVED = ("NORMALIZE_REPLAY", "DETECT_REPLAY", "ASSEMBLE_REPLAY", "V1_PROJECTIONS")
MAX_REQUEST_BYTES = 1 << 20
STATEMENT = d052.STATEMENT


def status_of(lifecycle: str, outcome: str | None) -> str:
    """The status word of an investigation state (``EXIT`` key)."""
    if lifecycle == "COMPLETED":
        return "completed" if outcome == "completed" else "partial"
    return LIFECYCLE_STATUS[lifecycle]


# Requests ----------------------------------------------------------------------------------------------------------


def config(*, live: bool, budget: int = DEFAULT_LOOKUP_EVIDENCE_BUDGET_BYTES) -> dict[str, Any]:
    """The effective configuration of a request: plan-1, the plan budgets, the lookup evidence budget (D-048), and for
    a live capture the default Stage 03 fetch policy with its D-042 bound."""
    policy = FetchPolicy()
    return {
        "plan_version": workflow.PLAN_VERSION,
        "budgets": {"a_max": workflow.A_MAX, "f_max": workflow.F_MAX},
        "fetch_policy_sha256": policy_digest(policy) if live else None,
        "live_acquire_bound": bound_for(policy) if live else None,
        "lookup_evidence_budget_bytes": budget,
    }


def retained_request(bundle: Path, index: Path, memory_root: Path, *, budget: int | None = None) -> dict[str, Any]:
    return {
        "schema": REQUEST,
        "schema_version": "2.0.0",
        "mode": "retained_bundle",
        "subject": {"type": "wikipedia_article_revision", "bundle_path": str(bundle)},
        "index_path": str(index),
        "memory_root": str(memory_root),
        "config": config(live=False, budget=budget or DEFAULT_LOOKUP_EVIDENCE_BUDGET_BYTES),
    }


def live_request(
    wiki: str, revision_id: int, index: Path, memory_root: Path, *, budget: int | None = None
) -> dict[str, Any]:
    return {
        "schema": REQUEST,
        "schema_version": "2.0.0",
        "mode": "live_capture",
        "subject": {"type": "wikipedia_article_revision", "wiki": wiki, "revision_id": revision_id},
        "index_path": str(index),
        "memory_root": str(memory_root),
        "config": config(live=True, budget=budget or DEFAULT_LOOKUP_EVIDENCE_BUDGET_BYTES),
    }


def read_request(path: Path) -> dict[str, Any]:
    """A request file: strict JSON (no duplicate keys), at most 1 MiB, valid against the request schema."""
    try:
        with open(path, "rb") as f:
            data = f.read(MAX_REQUEST_BYTES + 1)
    except OSError as exc:
        raise OperationError("invalid", "REQUEST_UNREADABLE", f"{path}: {exc.strerror}") from exc
    if len(data) > MAX_REQUEST_BYTES:
        raise OperationError("invalid", "REQUEST_INVALID", f"{path} is larger than {MAX_REQUEST_BYTES} bytes")
    try:
        value = loads_strict(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise OperationError("invalid", "REQUEST_INVALID", f"{path}: {exc}") from exc
    if not isinstance(value, dict):
        raise OperationError("invalid", "REQUEST_INVALID", f"{path} is not a JSON object")
    return value


def check_request(request: Mapping[str, Any]) -> None:
    """The checks ``run`` makes before anything is created: the request schema, the live policy (the command line
    supports the default Stage 03 fetch policy only) and an absolute memory root."""
    found = problems(dict(request), REQUEST)
    if found:
        raise OperationError("invalid", "REQUEST_INVALID", "; ".join(found[:3]))
    if request["mode"] == "live_capture":
        want = config(live=True, budget=request["config"]["lookup_evidence_budget_bytes"])
        if request["config"] != want:
            raise OperationError(
                "invalid", "REQUEST_INVALID", "a live capture needs the default Stage 03 fetch policy and its bound"
            )
    elif request["config"]["fetch_policy_sha256"] is not None or request["config"]["live_acquire_bound"] is not None:
        raise OperationError("invalid", "REQUEST_INVALID", "a retained bundle has no fetch policy and no live bound")
    if not Path(request["memory_root"]).is_absolute():
        raise OperationError("invalid", "MEMORY_ROOT_UNSAFE", "the memory root must be an absolute path")


def integration_for(request: Mapping[str, Any]) -> Integration:
    live = make_live_acquire(FetchPolicy()) if request["mode"] == "live_capture" else None
    return Integration(live=live)


def created_for(request: Mapping[str, Any]) -> dict[str, Any]:
    """The ``investigation_created`` payload of a request (S-4.7). A retained bundle is opened with Stage 03
    ``open_bundle`` to read its capture digest, which is the request key."""
    capture = None
    if request["mode"] == "retained_bundle":
        try:
            capture = open_bundle(Path(request["subject"]["bundle_path"])).capture_sha256
        except BundleError as exc:
            raise OperationError("invalid", "BUNDLE_UNREADABLE", f"{exc.issue.code}: {exc.issue.detail}") from exc
        except OSError as exc:
            raise OperationError("invalid", "BUNDLE_UNREADABLE", str(exc.strerror)) from exc
    return created_payload(copy.deepcopy(dict(request)), dict(STAGE04_IDENTITY), bundle_capture_sha256=capture)


# Opening ---------------------------------------------------------------------------------------------------------


@contextmanager
def opened(memory_root: Path, key: str) -> Iterator[InvestigationMemory]:
    """A read-only open: the lock (busy), Memory's checks and the workflow invariants (corrupt). Nothing is written."""
    try:
        mem = InvestigationMemory.open(memory_root, key, writable=False)
    except Busy as exc:
        raise OperationError("busy", "INVESTIGATION_BUSY", str(exc)) from exc
    except CorruptInvestigation as exc:
        raise OperationError("corrupt", "INVESTIGATION_CORRUPT", str(exc)) from exc
    except PathUnsafe as exc:
        if exc.code == "MEMORY_ROOT_UNSAFE":
            raise OperationError("invalid", exc.code, exc.detail) from exc
        raise OperationError("not_found", "INVESTIGATION_NOT_FOUND", exc.detail) from exc
    except FileNotFoundError as exc:
        raise OperationError("not_found", "INVESTIGATION_NOT_FOUND", f"no investigation {key}") from exc
    except OSError as exc:
        raise OperationError("not_found", "INVESTIGATION_NOT_FOUND", f"{key}: {exc.strerror}") from exc
    try:
        try:
            workflow.check_journal(mem.view)
        except WorkflowCorrupt as exc:
            raise OperationError("corrupt", "INVESTIGATION_CORRUPT", str(exc)) from exc
        yield mem
    finally:
        mem.close()


def _outputs(f: Folder, step: str) -> tuple[str, ...]:
    ends = [a.end_seq for a in f.attempts[step] if a.end_kind == "step_succeeded"]
    if not ends or ends[-1] is None:
        return ()
    return tuple(f.records[ends[-1]]["payload"]["outputs"])


def readonly_request(mem: InvestigationMemory, step: str) -> StepRequest:
    """The request VERIFY was given, rebuilt from a read-only open: the committed content without the verification
    record, so the VERIFY checks can be re-run on a verified investigation."""
    f = mem.view
    created = workflow.created(f)
    blobs = mem.blobs
    return StepRequest(
        step=step,
        attempt=1,
        step_key="0" * 64,
        live=workflow.is_live(f),
        request=copy.deepcopy(created["request"]),
        request_key=copy.deepcopy(created["request_key"]),
        root=copy.deepcopy(f.root),
        inputs={s: _outputs(f, s) for s in STEPS if f.step_state(s) == "succeeded"},
        committed=tuple(r for r in copy.deepcopy(f.committed_content()) if r["kind"] != "verification_recorded"),
        stored=tuple(r for r in copy.deepcopy(f.committed_records()) if r["kind"] != "verification_recorded"),
        content_digest=f.content_digest(),
        read_blob=lambda d: json.loads(blobs.get(d)),
        read_bytes=blobs.get,
        now=datetime.now(UTC),
        investigation={k: created[k] for k in ("investigation_key", "investigation_id")},
    )


def report_of(mem: InvestigationMemory) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """The committed ``report_recorded`` payload and its manifest, or None before ASSEMBLE committed."""
    recs = [r for r in mem.view.committed_content() if r["kind"] == "report_recorded"]
    if not recs:
        return None
    payload = dict(recs[-1]["payload"])
    return payload, json.loads(mem.blobs.get(payload["report"]))


def claim_entries(mem: InvestigationMemory, manifest: Mapping[str, Any]) -> Iterator[dict[str, Any]]:
    """The claim entries of a report, chunk by chunk (each chunk read and verified by its digest)."""
    for ref in manifest["components"]["claims"]["chunks"]:
        yield from json.loads(mem.blobs.get(ref["chunk"]))["items"]


def stale_identities(mem: InvestigationMemory, integration: Integration) -> dict[str, Any] | None:
    """S-10.1 without writing: the committed steps whose key differs under the current input identities, and the
    identity components that changed; None when every committed step key still holds. A step key that differs
    while no identity changed is not staleness: ``CheckFailed`` (``STEP_KEY_MISMATCH``)."""
    f = mem.view
    created = workflow.created(f)
    root = f.root
    values = integration.environment(created)(copy.deepcopy(root["subject"]["identity"]) if root else None)
    digests = workflow.identity_digests(values)
    committed = [s for s in STEPS if f.step_state(s) == "succeeded"]
    recorded_keys = {}
    for s in committed:
        ends = [a.end_seq for a in f.attempts[s] if a.end_kind == "step_succeeded"]
        recorded_keys[s] = f.records[ends[-1]]["payload"]["step_key"]  # type: ignore[index]
    changed_steps = [s for s in committed if workflow.step_key(f, s, digests) != recorded_keys[s]]
    if not changed_steps:
        return None
    recorded: dict[str, str] = {}
    for s in committed:
        manifest = json.loads(mem.blobs.get(_outputs(f, s)[-1]))
        for name, digest in manifest["identities"].items():
            if name not in recorded or (recorded[name] == digests[name] and digest != digests[name]):
                recorded[name] = digest
    changed = sorted(n for n, d in recorded.items() if digests[n] != d)
    if not changed:
        # A recorded step key that the committed inputs do not derive, while no input identity changed: the journal
        # is inconsistent, not stale.
        raise CheckFailed(
            f"STEP_KEY_MISMATCH: the recorded step keys of {changed_steps} do not derive from the "
            "committed inputs, and no input identity changed"
        )
    return {"changed": changed, "steps": changed_steps}


# Show ------------------------------------------------------------------------------------------------------------


def show(memory_root: Path, key: str, *, explain_claims: bool = False) -> tuple[dict[str, Any], int]:
    with opened(memory_root, key) as mem:
        f = mem.view
        created = workflow.created(f)
        now = datetime.now(UTC)
        ex = workflow.explain(f, now)
        steps = []
        for s in STEPS:
            sv = workflow.step_view(f, s)
            steps.append(
                {
                    "step": s,
                    "state": sv.state,
                    "attempts": sv.attempts,
                    "not_before": _iso(sv.not_before),
                }
            )
        out: dict[str, Any] = {
            "investigation_key": created["investigation_key"],
            "investigation_id": created["investigation_id"],
            "lifecycle": ex["lifecycle"],
            "steps": steps,
            "next": ex["next"],
            "terminated_by": ex.get("terminated_by"),
            "open_questions": len(f.open_questions()),
            "claims_by_class": committed_claim_counts(f),
            "journal_records": len(f.records),
            "report": None,
        }
        rep = report_of(mem)
        outcome = None
        if rep is not None:
            payload, manifest = rep
            outcome = manifest["outcome"]
            entries = list(claim_entries(mem, manifest))
            out["report"] = {
                "report": payload["report"],
                "projection_set": payload["projection_set"],
                "projection_count": payload["projection_count"],
                "terminal_state": manifest["terminal_state"],
                "outcome": outcome,
                "claims_by_class": manifest["article_summary"]["claims_by_class"],
                "open_questions": manifest["article_summary"]["open_questions"],
                "snapshot_id": manifest["article_summary"]["snapshot_id"],
                "positive_works": manifest["components"]["positive_works"]["count"],
                "summary": explanations.summary_statement(manifest, manifest["components"]["positive_works"]["count"]),
                "limitations": explanations.limitations(manifest, [e["claim"] for e in entries]),
            }
            if explain_claims:
                out["report"]["claims"] = [explanations.claim_explanation(e) for e in entries]
        status = status_of(ex["lifecycle"], outcome)
        out["status"] = status
        return out, EXIT[status]


def committed_claim_counts(f: Folder) -> dict[str, int]:
    """Claim counts by class over the current committed claims (DETECT committed), before or without a report."""
    content = f.committed_content()
    superseded = {r["payload"]["old_claim_id"] for r in content if r["kind"] == "claim_superseded"}
    counts: dict[str, int] = {}
    for r in content:
        if r["kind"] == "claim_recorded" and r["payload"]["claim_id"] not in superseded:
            counts[r["payload"]["class"]] = counts.get(r["payload"]["class"], 0) + 1
    return dict(sorted(counts.items()))


def _iso(at: datetime | None) -> str | None:
    return at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ") if at is not None else None


# Run and resume --------------------------------------------------------------------------------------------------


def _after(memory_root: Path, key: str, detail: str) -> tuple[dict[str, Any], int]:
    out, code = show(memory_root, key)
    if detail:
        out["detail"] = detail
    return out, code


def run(request: Mapping[str, Any]) -> tuple[dict[str, Any], int]:
    check_request(request)
    payload = created_for(request)
    root = Path(request["memory_root"])
    try:
        InvestigationMemory.create(root, payload).close()
    except Busy as exc:
        raise OperationError("busy", "INVESTIGATION_BUSY", str(exc)) from exc
    except CorruptInvestigation as exc:
        raise OperationError("corrupt", "INVESTIGATION_CORRUPT", str(exc)) from exc
    except PathUnsafe as exc:
        raise OperationError("invalid", exc.code, exc.detail) from exc
    except InvestigationMemoryError as exc:
        if exc.code == "INVESTIGATION_REQUEST_DIFFERS":
            raise OperationError("invalid", exc.code, str(exc)) from exc
        raise
    return _drive(root, payload, integration_for(request))


def resume(memory_root: Path, key: str) -> tuple[dict[str, Any], int]:
    with opened(memory_root, key) as mem:
        created = copy.deepcopy(workflow.created(mem.view))
    return _drive(memory_root, created, integration_for(created["request"]))


def _drive(root: Path, created: Mapping[str, Any], integration: Integration) -> tuple[dict[str, Any], int]:
    key = created["investigation_key"]
    result = run_investigation(root, key, integration.adapters(), integration.environment(created))
    if result.status == "INVESTIGATION_BUSY":
        raise OperationError("busy", "INVESTIGATION_BUSY", result.detail)
    if result.status == "CORRUPT":
        raise OperationError("corrupt", "INVESTIGATION_CORRUPT", result.detail)
    return _after(root, key, result.detail)


# Verify ----------------------------------------------------------------------------------------------------------


def _check(name: str, fn: Callable[[], Any]) -> dict[str, Any]:
    try:
        fn()
    except Exception as exc:  # a failing check is that check failing (fail closed)
        return {"check": name, "passed": False, "detail": f"{type(exc).__name__}: {exc}"[:500]}
    return {"check": name, "passed": True, "detail": None}


def verify(
    memory_root: Path, key: str, *, checkpoint: Path | None = None, integration: Integration | None = None
) -> tuple[dict[str, Any], int]:
    supplied = d052.read(checkpoint) if checkpoint is not None else None  # a malformed checkpoint is invalid input
    integ = integration or Integration()
    try:
        with opened(memory_root, key) as mem:
            return _verify(mem, integ, supplied)
    except OperationError as exc:
        if exc.status in ("busy", "corrupt"):
            out = {"result": exc.status, "code": exc.code, "detail": exc.detail, "checks": []}
            return out, EXIT[exc.status]
        raise


def _verify(
    mem: InvestigationMemory, integ: Integration, supplied: dict[str, Any] | None
) -> tuple[dict[str, Any], int]:
    f = mem.view
    lifecycle = f.lifecycle()
    checks = [
        {"check": "MEMORY_OPEN", "passed": True, "detail": None},  # M-1..M-14, blobs, D-054 graph on open
        {"check": "WORKFLOW_INVARIANTS", "passed": True, "detail": None},  # W-2..W-8 (``opened``)
    ]
    verified = lifecycle in VERIFIED

    def committed_verification() -> None:
        ver = [r["payload"] for r in f.committed_content() if r["kind"] == "verification_recorded"]
        if len(ver) != 1 or ver[0]["result"] != "passed":
            raise CheckFailed(f"lifecycle {lifecycle}: no committed passed verification")
        if ver[0]["content_digest"] != f.content_digest():
            raise CheckFailed("the recorded content digest is not C(J)")

    checks.append(_check("COMMITTED_VERIFICATION", committed_verification))
    if verified:
        verifier = _Verifier(readonly_request(mem, "VERIFY"), integ.detector, integ.stage04)
        checks += verifier.run()
    stale = None

    def identities() -> None:
        nonlocal stale
        stale = stale_identities(mem, integ)
        if stale is not None:
            raise CheckFailed(f"changed input identities: {stale['changed']}")

    if lifecycle != "STALE":
        checks.append(_check("INPUT_IDENTITIES_CURRENT", identities))
    cp = None
    if supplied is not None:
        cp = d052.compare(supplied, mem.key, f.records)
        checks.append({"check": "D052_CHECKPOINT", "passed": cp == "CHECKPOINT_MATCH", "detail": cp})
    rep = report_of(mem)
    outcome = rep[1]["outcome"] if rep is not None else None

    def describes_state(c: Mapping[str, Any]) -> bool:
        # Only a not-yet-verified lifecycle explains a missing verification, and only changed identities (stale)
        # explain a step key that no longer holds; every other failed check is a failed verification. A check that
        # re-runs Stage 04 code under the current Stage 04 identity cannot reproduce content committed under another
        # one: when that identity changed, its failure is the staleness (Step 11, VS-10), as ``replay`` reports it.
        if c["check"] == "COMMITTED_VERIFICATION":
            return not verified
        if c["check"] in STAGE04_REDERIVED:
            return stale is not None and "stage04" in stale["changed"]
        return c["check"] == "INPUT_IDENTITIES_CURRENT" and stale is not None

    if any(not c["passed"] and not describes_state(c) for c in checks):
        result, code = "failed", EXIT["verify_failed"]
    elif lifecycle == "STALE" or stale is not None:
        result, code = "stale", EXIT["stale"]
    elif verified:
        result, code = "passed", EXIT[status_of(lifecycle, outcome)]
    else:
        result, code = "failed", EXIT[status_of(lifecycle, outcome)]
    out = {
        "result": result,
        "lifecycle": lifecycle,
        "outcome": outcome,
        "investigation_key": mem.key,
        "content_digest": f.content_digest(),
        "checks": checks,
        "stale": stale,
    }
    if cp is not None:
        out["checkpoint"] = {"result": cp, "statement": STATEMENT}
    return out, code


# Replay ----------------------------------------------------------------------------------------------------------


def replay(memory_root: Path, key: str, *, integration: Integration | None = None) -> tuple[dict[str, Any], int]:
    integ = integration or Integration()
    with opened(memory_root, key) as mem:
        f = mem.view
        lifecycle = f.lifecycle()
        rep = report_of(mem)
        outcome = rep[1]["outcome"] if rep is not None else None
        base: dict[str, Any] = {"investigation_key": mem.key, "lifecycle": lifecycle}
        if lifecycle == "STALE":
            return {**base, "result": "stale", "changed": _recorded_stale(f)}, EXIT["stale"]
        if lifecycle not in VERIFIED or rep is None:
            raise OperationError(
                status_of(lifecycle, outcome), "NOT_REPLAYABLE", f"lifecycle {lifecycle}: no verified report to replay"
            )
        try:
            stale = stale_identities(mem, integ)
        except CheckFailed as exc:
            keys = {"component": "step_keys", "detail": str(exc)[:500]}
            return {**base, "result": "differs", "first_difference": keys, "outcome": outcome}, EXIT["verify_failed"]
        if stale is not None:
            return {**base, "result": "stale", "changed": stale["changed"]}, EXIT["stale"]
        req = readonly_request(mem, "VERIFY")
        verifier = _Verifier(req, integ.detector, integ.stage04)
        payload, manifest = rep
        first = _first_difference(req, verifier, payload, manifest)
        claims = [e["claim"] for e in claim_entries(mem, manifest)]
        out = {
            **base,
            "result": "differs" if first else "reproduced",
            "first_difference": first,
            "report": payload["report"],
            "projection_set": payload["projection_set"],
            "projection_count": payload["projection_count"],
            "content_digest": f.content_digest(),
            "claims": len(claims),
            "identity_conflicts": sorted(c["claim_id"] for c in claims if c["class"] == "IDENTITY_CONFLICT"),
            "outcome": outcome,
        }
        return out, EXIT["verify_failed"] if first else EXIT[status_of(lifecycle, outcome)]


def _recorded_stale(f: Folder) -> list[str]:
    for rec in reversed(f.records):
        if rec["kind"] == "stale_detected":
            return list(rec["payload"]["changed"])
    return []


def _first_difference(
    req: StepRequest, verifier: _Verifier, payload: Mapping[str, Any], manifest: Mapping[str, Any]
) -> dict[str, Any] | None:
    """The first component whose re-derivation differs from the committed one, in pipeline order."""
    manifest_ = committed_manifest(req)
    _, doc = committed_extraction(req)
    with reconstruct(manifest_, req.read_bytes) as path:
        checked = verify_bundle(path, doc)
        if not checked.get("verified"):
            codes = [i["code"] for i in checked.get("issues") or [] if i.get("severity") == "error"]
            return {"component": "bundle", "detail": f"Stage 03 verification failed: {codes[:5]}"}
        again = replay_bundle(path, recorded=doc)
    if again.get("replay", {}).get("state") != "reproduced":
        return {"component": "extraction", "detail": json.dumps(again.get("replay"), sort_keys=True)[:500]}
    for component, method in (
        ("normalize", verifier.normalize_replay),
        ("detect", verifier.detect_replay),
    ):
        try:
            method()
        except CheckFailed as exc:
            return {"component": component, "detail": str(exc)[:500]}
    try:
        assembled = verifier._assembled()
    except CheckFailed as exc:
        return {"component": "report", "detail": str(exc)[:500]}
    new = dict(assembled.records[0].payload)
    if new["report"] != payload["report"]:
        blob = next(b for b in assembled.blobs if isinstance(b, dict) and b.get("schema") == manifest["schema"])
        for field in ("investigation_key", "investigation_id", "root", "terminal_state", "outcome"):
            if blob[field] != manifest[field]:
                return {"component": f"report.{field}", "detail": None}
        for field in ("article_summary", "limitations", "identities"):
            if blob[field] != manifest[field]:
                return {"component": f"report.{field}", "detail": None}
        for part in ("claims", "observations", "positive_works", "evidence"):
            if blob["components"][part] != manifest["components"][part]:
                return {"component": f"report.components.{part}", "detail": None}
        return {"component": "report", "detail": None}
    if new["projection_set"] != payload["projection_set"] or new["projection_count"] != payload["projection_count"]:
        return {"component": "projection_set", "detail": None}
    return None


# Export and checkpoint -------------------------------------------------------------------------------------------


def export(
    memory_root: Path, key: str, out: Path, *, integration: Integration | None = None
) -> tuple[dict[str, Any], int]:
    """The export gate and the export, under one read-only open (one lock): ``verify`` must give ``passed`` on the
    same journal the export is then derived from; otherwise nothing is written."""
    exporter.check_target(out, memory_root)
    integ = integration or Integration()
    try:
        with opened(memory_root, key) as mem:
            result, _ = _verify(mem, integ, None)
            lifecycle, outcome = result["lifecycle"], result["outcome"]
            if result["result"] != "passed":
                if result["result"] == "stale":
                    status = "stale"
                elif lifecycle in VERIFIED:
                    status = "verify_failed"
                else:
                    status = status_of(lifecycle, outcome)
                raise OperationError(status, "EXPORT_REFUSED", f"verification {result['result']}: nothing exported")
            written = exporter.write(mem, out, memory_root)
    except OperationError as exc:
        if exc.code in ("INVESTIGATION_BUSY", "INVESTIGATION_CORRUPT"):
            raise OperationError(exc.status, "EXPORT_REFUSED", f"{exc.code}: {exc.detail}") from exc
        raise
    return {"exported": str(out), **written}, EXIT[status_of(lifecycle, outcome)]


def checkpoint(memory_root: Path, key: str, out: Path | None, *, overwrite: bool = False) -> tuple[dict[str, Any], int]:
    if out is not None:
        d052.check_target(out, memory_root, overwrite=overwrite)
    with opened(memory_root, key) as mem:
        value = d052.make(mem.key, mem.view.records)
        lifecycle = mem.view.lifecycle()
        rep = report_of(mem)
        outcome = rep[1]["outcome"] if rep is not None else None
    if out is not None:
        d052.write(out, d052.encode(value), memory_root, overwrite=overwrite)
    result = {"checkpoint": value, "written": str(out) if out is not None else None, "statement": STATEMENT}
    return result, EXIT[status_of(lifecycle, outcome)]
