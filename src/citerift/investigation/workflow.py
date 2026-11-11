"""Workflow rules of the Investigation Workflow Controller (SPEC 9, 10.1, 10.3; MM 8 to 10; Stage 04 Step 7).

Everything here is a pure function of the fold (``Folder``) and, where named, of the current time or the current
input identities. There is no other workflow state (W-1).

- ``guard`` is the append guard of MM 8: for a proposed record and the fold before it, the transition rule that
  permits it (T-CREATE … T-STALE), or ``WorkflowRefused``. The controller calls it before every append, in addition
  to the Memory checks (M-1 to M-14) that ``InvestigationMemory.append`` runs.
- ``check_journal`` replays every record of a journal through the same guard, so a journal that Memory accepts but
  that breaks a workflow rule (W-2 to W-8) is refused on open, read-only.
- ``derive`` computes the controller state (step states, counters, lifecycle, next action, outcome) and ``explain``
  says why (S-9.2).
- ``step_key`` and the step manifest implement S-9.3 and the staleness test of SPEC 10.3.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from citerift.contracts.formats import parse_utc_timestamp
from citerift.investigation import ids
from citerift.investigation.errors import InvariantViolation, InvestigationMemoryError
from citerift.investigation.fold import CONTENT_LAYER, STEPS, Attempt, Folder

PLAN_VERSION = "plan-1"
A_MAX = 3  # SPEC 9.2: a step is abandoned at its third failed or interrupted attempt
F_MAX = 6  # SPEC 9.2: ACQUIRE is abandoned when Stage 03 defers it a seventh time
LIFECYCLE_TERMINAL = frozenset({"NEEDS_RESOLUTION", "COMPLETED", "FAILED", "STALE", "CORRUPT"})
RETRY_BUDGET_EXHAUSTED = "RETRY_BUDGET_EXHAUSTED"
DEFERRAL_BUDGET_EXHAUSTED = "DEFERRAL_BUDGET_EXHAUSTED"
WALL_CLOCK = "ACQUIRE_WALL_CLOCK_EXCEEDED"
INTERRUPTED_REASON = "STEP_INTERRUPTED"

# SPEC 9.3: the only retryable codes. ACQUIRE's are network codes, so they exist only for a live capture; EXTRACT's
# are resource limits of the isolated Stage 03 worker.
NETWORK_CODES = frozenset(
    {
        "HTTP_TIMEOUT",
        "HTTP_CONNECTION_FAILED",
        "HTTP_SERVER_ERROR",
        "HTTP_UNAVAILABLE",
        "HTTP_RATE_LIMITED",
        "API_RATELIMITED",
        "API_MAXLAG",
        "ATTEMPTS_EXHAUSTED",
        "NETWORK_GATE_BUSY",
    }
)
EXTRACT_RETRYABLE = frozenset(
    {"EXTRACTION_DEADLINE_EXCEEDED", "EXTRACTION_MEMORY_EXCEEDED", "EXTRACTION_WORKER_FAILED"}
)

# SPEC 8.3, 9.1 and the record schema: the content kinds each step writes. DETECT's decisions and questions are
# derived by the controller from its claims (SPEC 7.6, 7.7). Evidence is committed in batches (D-053, SPEC 8.8).
CONTENT_KINDS: dict[str, frozenset[str]] = {
    "VALIDATE": frozenset(),
    "ACQUIRE": frozenset({"observation_recorded"}),
    "EXTRACT": frozenset({"observation_recorded"}),
    "NORMALIZE": frozenset({"evidence_batch_recorded"}),
    "LOOKUP": frozenset({"observation_recorded", "lookup_batch_recorded"}),
    "DETECT": frozenset({"evidence_batch_recorded", "candidate_result_batch_recorded"}),
    "ASSEMBLE": frozenset({"report_recorded"}),
    "VERIFY": frozenset({"verification_recorded"}),
}
# What an adapter supplies (adapters.ContentRecord kinds). ``EVIDENCE`` is one evidence item; the controller orders
# the attempt's items, cuts them into batches and commits each batch (D-053). LOOKUP supplies its observations and
# DETECT its claims one by one; the controller commits lookup observations and candidate results (claim, derived
# decision and question) in step-local batches (D-055). An adapter never supplies a batch.
EVIDENCE = "evidence"
ADAPTER_CONTENT_KINDS: dict[str, frozenset[str]] = {
    **CONTENT_KINDS,
    "LOOKUP": frozenset({"observation_recorded"}),
    "NORMALIZE": frozenset({EVIDENCE}),
    "DETECT": frozenset({EVIDENCE, "claim_recorded"}),
}

# SPEC 7.2 and 7.6.
POSITIVE = frozenset({"RETRACTED_WORK_CITED", "CONCERN_CITED", "CORRECTION_CITED", "REINSTATED_WORK_CITED"})
NEGATIVE = frozenset({"NOT_FOUND_IN_CHECKED_SOURCES"})  # missing evidence: the nearest to a negative (S-7.5)
CONFLICT = {"IDENTITY_CONFLICT": "identity_conflict", "CONTRADICTION_IN_SOURCES": "source_conflict"}
DISPOSITION = {
    **dict.fromkeys(POSITIVE, "REPORT_FINDING"),
    "NOT_FOUND_IN_CHECKED_SOURCES": "REPORT_NOT_FOUND",
    "IDENTITY_CONFLICT": "ROUTE_NEEDS_RESOLUTION",
    "CONTRADICTION_IN_SOURCES": "ROUTE_NEEDS_RESOLUTION",
    "UNRESOLVED_IDENTITY": "ABSTAIN",
    "UNRESOLVED_IDENTIFIER": "ABSTAIN",
    "UNRESOLVED_STATUS": "ABSTAIN",
    "NOTICE_CITED": "ABSTAIN",
    "LOOKUP_UNAVAILABLE": "ABSTAIN_UNAVAILABLE",
    "UNUSED_DEFINITION": "OUT_OF_SCOPE",
    "UNRESOLVED_USE": "OUT_OF_SCOPE",
    "NO_IDENTIFIER": "OUT_OF_SCOPE",
}

# S-9.3, MM 10.1: what each step reads. Dependencies are committed steps whose outputs enter the key; identities are
# the components of the input identity vector (SPEC 10.3) the step depends on.
IDENTITY_NAMES = ("request_key", "root", "extraction", "index", "stage04", "config")
STEP_DEPENDENCIES: dict[str, tuple[str, ...]] = {
    "VALIDATE": (),
    "ACQUIRE": ("VALIDATE",),
    "EXTRACT": ("ACQUIRE",),
    "NORMALIZE": ("EXTRACT",),
    "LOOKUP": ("NORMALIZE",),
    "DETECT": ("NORMALIZE", "LOOKUP"),
    "ASSEMBLE": ("VALIDATE", "ACQUIRE", "EXTRACT", "NORMALIZE", "LOOKUP", "DETECT"),
    "VERIFY": ("VALIDATE", "ACQUIRE", "EXTRACT", "NORMALIZE", "LOOKUP", "DETECT", "ASSEMBLE"),
}
_BASE_IDENTITIES = ("request_key", "stage04", "config")
STEP_IDENTITIES: dict[str, tuple[str, ...]] = {
    "VALIDATE": _BASE_IDENTITIES,
    "ACQUIRE": _BASE_IDENTITIES,
    "EXTRACT": (*_BASE_IDENTITIES, "root", "extraction"),
    "NORMALIZE": (*_BASE_IDENTITIES, "root", "extraction"),
    "LOOKUP": (*_BASE_IDENTITIES, "root", "extraction", "index"),
    "DETECT": IDENTITY_NAMES,
    "ASSEMBLE": IDENTITY_NAMES,
    "VERIFY": IDENTITY_NAMES,
}
MANIFEST_TAG = "citerift-step-manifest/1"


class WorkflowRefused(InvestigationMemoryError):
    """A record no transition rule permits (MM 8, S-9.1). ``rule`` names the rule or invariant that refuses it."""

    def __init__(self, rule: str, detail: str, seq: int | None = None) -> None:
        super().__init__("WORKFLOW_REFUSED", f"{rule}: {detail}")
        self.rule = rule
        self.reason = detail
        self.seq = seq


class WorkflowCorrupt(InvestigationMemoryError):
    """A journal that Memory accepts but that breaks a workflow invariant (W-2 to W-8): CORRUPT, read-only."""

    def __init__(self, cause: WorkflowRefused) -> None:
        super().__init__("WORKFLOW_CORRUPT", str(cause))
        self.cause = cause


# Counters and per-step facts ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class StepView:
    step: str
    state: str
    attempts: int
    phi: int  # attempts closed by step_failed(retryable) or step_interrupted (SPEC 9.2)
    f: int  # attempts closed by step_deferred
    not_before: datetime | None  # of the last attempt (deferred, or a failed ACQUIRE that recorded one)
    open_attempt: int | None


def _end(f: Folder, a: Attempt) -> dict[str, Any] | None:
    return f.records[a.end_seq] if a.end_seq is not None else None


def step_view(f: Folder, step: str) -> StepView:
    history = f.attempts[step]
    phi = sum(1 for a in history if a.end_kind == "step_interrupted" or (a.end_kind == "step_failed" and a.retryable))
    deferrals = sum(1 for a in history if a.end_kind == "step_deferred")
    nb: datetime | None = None
    if history:
        end = _end(f, history[-1])
        if end is not None and end["kind"] in ("step_deferred", "step_failed"):
            raw = end["payload"].get("not_before")
            nb = parse_utc_timestamp(raw) if isinstance(raw, str) else None
    open_number = f.open.number if f.open is not None and f.open.step == step else None
    return StepView(step, f.step_state(step), len(history), phi, deferrals, nb, open_number)


def is_live(f: Folder) -> bool:
    return bool(f.created and f.created["request"]["mode"] == "live_capture")


def retryable_code(step: str, code: str, live: bool) -> bool:
    """SPEC 9.3: whether ``code`` is in the step's retryable set for this request."""
    if step == "ACQUIRE":
        return live and (code in NETWORK_CODES or code == WALL_CLOCK)
    if step == "EXTRACT":
        return code in EXTRACT_RETRYABLE
    return False


def has_retryable_codes(step: str, live: bool) -> bool:
    return step == "EXTRACT" or (step == "ACQUIRE" and live)


# The append guard (MM 8) -------------------------------------------------------------------------------------------


def _refuse(rule: str, detail: str, seq: int | None) -> WorkflowRefused:
    return WorkflowRefused(rule, detail, seq)


def guard(rec: Mapping[str, Any], f: Folder, *, orphan: bool | None = None) -> str:
    """The rule of MM 8 that permits ``rec`` after the fold ``f``; raises ``WorkflowRefused`` otherwise.

    ``orphan`` says whether the open attempt belongs to a process that died (SPEC 10.1, W-6): True or False when the
    caller knows (the controller), None when it cannot (``check_journal`` over a stored journal)."""
    seq = len(f.records)
    kind, step = rec.get("kind"), rec.get("step")
    lc = f.lifecycle() if f.created is not None else None
    if lc in LIFECYCLE_TERMINAL:
        raise _refuse("W-5", f"{kind} after the terminal lifecycle {lc}", seq)
    if kind == "investigation_created":
        if f.records:
            raise _refuse("T-CREATE", "the journal already exists", seq)
        return "T-CREATE"
    if f.created is None:
        raise _refuse("T-CREATE", "no investigation_created record", seq)
    if kind == "stale_detected":
        if lc not in ("RUNNING", "BLOCKED"):
            raise _refuse("T-STALE", f"stale_detected in lifecycle {lc}", seq)
        if f.open is not None:
            raise _refuse("W-6", "stale_detected while an attempt is open", seq)
        if not any(f.step_state(s) == "succeeded" for s in STEPS):
            raise _refuse("T-STALE", "no committed step can be stale", seq)
        problem = _stale_problem(rec.get("payload"))
        if problem:
            raise _refuse("T-STALE", problem, seq)
        return "T-STALE"
    if not isinstance(step, str) or step not in STEPS:
        raise _refuse("SCHEMA", f"{kind} names no plan step", seq)
    live = is_live(f)
    sv = step_view(f, step)
    index = STEPS.index(step)
    if kind == "step_started":
        return _guard_start(rec, f, sv, index, lc, seq)
    # Every other record belongs to the open attempt of its step.
    if f.open is None or f.open.step != step or f.open.number != rec.get("attempt"):
        raise _refuse("M-6", f"{kind} of {step} attempt {rec.get('attempt')} has no open attempt", seq)
    if kind == "step_interrupted":
        if orphan is False:
            raise _refuse("W-6", "only a resume closes an attempt as interrupted", seq)
        if sv.phi + 1 >= A_MAX:
            raise _refuse("W-4", "the retry budget is spent: the attempt ends RETRY_BUDGET_EXHAUSTED", seq)
        return "T-INTERRUPT"
    if orphan and not (kind == "step_failed" and rec["payload"].get("code") == RETRY_BUDGET_EXHAUSTED):
        raise _refuse("W-6", f"{kind} continues an attempt of a process that died", seq)
    if kind in CONTENT_LAYER:
        if kind not in CONTENT_KINDS[step]:
            raise _refuse("T-CONTENT", f"{step} does not write {kind}", seq)
        return "T-CONTENT"
    if kind == "step_succeeded":
        _guard_success(rec, f, step, seq)
        return "T-SUCCEED"
    if kind == "step_deferred":
        if not (step == "ACQUIRE" and live):
            raise _refuse("T-DEFER", "only ACQUIRE of a live capture is deferred", seq)
        if sv.f >= F_MAX:
            raise _refuse("W-4", "the deferral budget is spent: the attempt ends DEFERRAL_BUDGET_EXHAUSTED", seq)
        return "T-DEFER"
    if kind == "step_failed":
        return _guard_failure(rec, f, sv, step, live, orphan, seq)
    raise _refuse("SCHEMA", f"unknown record kind {kind}", seq)


def _stale_problem(p: Any) -> str:
    """SPEC 10.3: ``changed`` names exactly the recorded components whose current digest differs, and is not empty."""
    if not isinstance(p, Mapping):
        return "stale_detected has no payload"
    changed, recorded, current = p.get("changed"), p.get("recorded"), p.get("current")
    if not (isinstance(changed, list) and isinstance(recorded, Mapping) and isinstance(current, Mapping)):
        return "stale_detected payload is malformed"
    differ = sorted(n for n in recorded if n in current and current[n] != recorded[n])
    if not changed or sorted(changed) != differ:
        return f"changed {changed} is not the set of differing components {differ}"
    return ""


def _guard_start(rec: Mapping[str, Any], f: Folder, sv: StepView, index: int, lc: str | None, seq: int) -> str:
    step = sv.step
    if f.open is not None:
        raise _refuse("W-3", f"{f.open.step} attempt {f.open.number} is open", seq)
    earlier = [s for s in STEPS[:index] if f.step_state(s) != "succeeded"]
    if earlier:
        raise _refuse("W-3", f"{step} before {earlier[0]} succeeded", seq)
    if rec.get("attempt") != sv.attempts + 1:
        raise _refuse("M-6", f"attempt {rec.get('attempt')} where {sv.attempts + 1} is next", seq)
    at = parse_utc_timestamp(rec["at"]) if isinstance(rec.get("at"), str) else None
    if sv.state == "pending" and sv.attempts == 0:
        if (index == 0) != (lc == "CREATED"):
            raise _refuse("T-START", f"{step} cannot start in lifecycle {lc}", seq)
        return "T-START"
    if sv.state == "pending":  # after step_interrupted
        return "T-RESTART"
    if sv.state in ("failed_retryable", "deferred"):
        if sv.not_before is not None and (at is None or at < sv.not_before):
            raise _refuse("T-RESTART", f"{step} restarts before not_before {sv.not_before.isoformat()}", seq)
        return "T-RESTART"
    raise _refuse("TR-2", f"{step} is {sv.state}", seq)


def _attempt_records(f: Folder) -> list[dict[str, Any]]:
    """The logical content of the open attempt: D-055 batches stand for the records they hold."""
    return f.attempt_content()


def _guard_success(rec: Mapping[str, Any], f: Folder, step: str, seq: int) -> None:
    if f.open is None:
        raise _refuse("M-6", "step_succeeded without an open attempt", seq)
    if f.unexpanded:
        raise _refuse("M-3", "a D-055 batch was folded without its content: the attempt cannot be judged", seq)
    content = _attempt_records(f)
    if step != "VALIDATE" and not content:
        raise _refuse("T-SUCCEED", f"{step} commits no content", seq)
    started = f.records[f.open.start_seq]["payload"]["step_key"]
    if rec["payload"].get("step_key") != started:
        raise _refuse("S-9.3", "step_succeeded names another step key than its step_started", seq)
    kinds = [r["kind"] for r in content]
    if step == "ASSEMBLE" and "report_recorded" not in kinds:
        raise _refuse("W-7", "ASSEMBLE commits no report", seq)
    if step == "VERIFY":
        ver = [r["payload"] for r in content if r["kind"] == "verification_recorded"]
        if len(ver) != 1 or ver[0]["result"] != "passed":
            raise _refuse("W-7", "VERIFY succeeds only with one passed verification", seq)
        if ver[0]["content_digest"] != f.content_digest():
            raise _refuse("W-7", "the verified content digest is not C(J)", seq)
    # CH-1 (evidence ids are H(observation, pointer, kind)) is checked by Investigation Memory for every item of
    # every evidence batch, on append and on open (D-053).
    if step == "DETECT":
        problem = detect_problem(content)
        if problem:
            raise _refuse("W-8", problem, seq)


def detect_problem(content: list[dict[str, Any]]) -> str:
    """W-8 and SPEC 7.6, 7.7, 4.3 over the content records of one DETECT attempt; ``""`` when they hold."""
    claims = [r["payload"] for r in content if r["kind"] == "claim_recorded"]
    decisions = [r["payload"] for r in content if r["kind"] == "decision_recorded"]
    questions = [r["payload"] for r in content if r["kind"] == "question_opened"]
    by_claim: dict[str, list[dict[str, Any]]] = {}
    for d in decisions:
        by_claim.setdefault(d["claim_id"], []).append(d)
    claim_ids = {c["claim_id"] for c in claims}
    if set(by_claim) - claim_ids:
        return "a decision names a claim of no DETECT claim"
    q_by_claim: dict[str, list[dict[str, Any]]] = {}
    for q in questions:
        q_by_claim.setdefault(q["claim_id"], []).append(q)
    if set(q_by_claim) - claim_ids:
        return "a question names a claim of no DETECT claim"
    decided_cands: dict[str, list[str]] = {}
    for c in claims:
        cls, cid = c["class"], c["claim_id"]
        if cid != ids.claim_id(c["cand_ref"], cls, c["rule"], c["table_version"], c["evidence_set"]):
            return f"claim {cid} is not H(cand_ref, class, rule, table version, evidence set)"
        want = DISPOSITION.get(cls)
        got = by_claim.get(cid, [])
        if want is None or len(got) != 1 or got[0]["disposition"] != want:
            return f"claim {cid} of class {cls} needs exactly one decision {want}"
        if got[0]["decision_id"] != ids.decision_id(cid, want):
            return f"decision of claim {cid} is not H(claim_id, disposition)"
        qs = q_by_claim.get(cid, [])
        if cls in CONFLICT:
            if len(qs) != 1 or qs[0]["kind"] != CONFLICT[cls]:
                return f"conflict claim {cid} needs one open question {CONFLICT[cls]}"
            if qs[0]["question_id"] != ids.question_id(cid, CONFLICT[cls]):
                return f"question of claim {cid} is not H(claim_id, question, kind)"
        elif qs:
            return f"claim {cid} of class {cls} opens a question"
        decided_cands.setdefault(c["cand_ref"], []).append(cls)
    for cand, classes in decided_cands.items():
        if set(classes) & set(CONFLICT) and set(classes) & (POSITIVE | NEGATIVE):
            return f"candidate {cand} has a conflict claim and a positive or negative claim"
        if len(classes) > 1:  # SPEC 7.1: the first rule whose guard holds decides the one class of a candidate
            return f"candidate {cand} has {len(classes)} claims ({', '.join(sorted(classes))})"
    return ""


def _guard_failure(
    rec: Mapping[str, Any], f: Folder, sv: StepView, step: str, live: bool, orphan: bool | None, seq: int
) -> str:
    p = rec["payload"]
    code, retryable = p.get("code"), p.get("retryable")
    if retryable:
        if not retryable_code(step, code, live):
            raise _refuse("T-FAIL-R", f"{code} is not retryable for {step}", seq)
        if sv.phi + 1 >= A_MAX:
            raise _refuse("W-4", "the retry budget is spent: the attempt ends RETRY_BUDGET_EXHAUSTED", seq)
        if code == WALL_CLOCK and step != "ACQUIRE":
            raise _refuse("T-FAIL-R", "only ACQUIRE has a wall-clock bound", seq)
        return "T-FAIL-R"
    if code == RETRY_BUDGET_EXHAUSTED:
        if sv.phi + 1 != A_MAX:
            raise _refuse("W-4", f"RETRY_BUDGET_EXHAUSTED with {sv.phi} earlier failures", seq)
        if orphan is False and not has_retryable_codes(step, live):
            raise _refuse("W-4", f"{step} has no retryable codes for this request", seq)
        if orphan is False and not retryable_code(step, p.get("reason") or "", live):
            raise _refuse("W-4", "RETRY_BUDGET_EXHAUSTED must name the retryable code that spent the budget", seq)
        return "T-FAIL-T"
    if code == DEFERRAL_BUDGET_EXHAUSTED:
        if not (step == "ACQUIRE" and live) or sv.f != F_MAX:
            raise _refuse("W-4", f"DEFERRAL_BUDGET_EXHAUSTED after {sv.f} deferrals", seq)
        return "T-FAIL-T"
    if retryable_code(step, code, live) and code != WALL_CLOCK:
        raise _refuse("T-FAIL-T", f"{code} is retryable for {step}: record it retryable or as exhaustion", seq)
    return "T-FAIL-T"


# Whole-journal workflow check (W-2 to W-8) -------------------------------------------------------------------------


def check_journal(view: Folder) -> None:
    """Replay every record of a folded journal through ``guard``; raises ``WorkflowCorrupt`` at the first record no
    rule permits. Process boundaries are not in the journal, so ``orphan`` is unknown here (W-6 is enforced when
    records are appended)."""
    replay = Folder(None, expected_key=view.expected_key, source=view)
    for rec in view.records:
        try:
            guard(rec, replay, orphan=None)
        except WorkflowRefused as exc:
            raise WorkflowCorrupt(exc) from exc
        try:
            replay.apply(rec)
        except InvariantViolation as exc:  # cannot happen for a journal Memory accepted; fail closed anyway
            raise WorkflowCorrupt(WorkflowRefused(exc.invariant, exc.reason, exc.seq)) from exc


# Controller state (W-1) ----------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class NextAction:
    """What the controller does next and the rule that permits it (S-9.2)."""

    action: str  # "terminal", "recover", "start", "wait"
    step: str | None
    attempt: int | None
    rule: str
    reason: str
    not_before: datetime | None = None


@dataclass(frozen=True)
class WorkflowState:
    lifecycle: str
    steps: tuple[StepView, ...]
    open_questions: tuple[str, ...]
    next: NextAction
    outcome: str | None  # "completed" or "partial" when COMPLETED or NEEDS_RESOLUTION (S-9.7), else None
    root_id: str | None

    def step(self, name: str) -> StepView:
        return self.steps[STEPS.index(name)]


def next_action(f: Folder, now: datetime) -> NextAction:
    """The next legal action from the fold alone, at time ``now`` (SPEC 9.2, 10.1)."""
    lc = f.lifecycle()
    if lc in LIFECYCLE_TERMINAL:
        return NextAction("terminal", None, None, "W-5", f"the lifecycle {lc} is terminal")
    if f.open is not None:
        sv = step_view(f, f.open.step)
        rule = "T-INTERRUPT" if sv.phi + 1 < A_MAX else "T-FAIL-T"
        return NextAction(
            "recover", f.open.step, f.open.number, rule, "an attempt without a terminal record is closed first (W-6)"
        )
    for step in STEPS:
        sv = step_view(f, step)
        if sv.state == "succeeded":
            continue
        if sv.state == "failed_terminal":  # unreachable: the lifecycle would be FAILED
            return NextAction("terminal", step, None, "TR-2", f"{step} failed")
        prev = STEPS[STEPS.index(step) - 1] if step != STEPS[0] else None
        why = f"previous step {prev} succeeded" if prev else "VALIDATE is the first step"
        if sv.state in ("failed_retryable", "deferred") and sv.not_before is not None and now < sv.not_before:
            return NextAction(
                "wait",
                step,
                sv.attempts + 1,
                "T-RESTART",
                f"{step} is {sv.state}; it may restart at or after not_before",
                sv.not_before,
            )
        if sv.attempts == 0:
            return NextAction("start", step, 1, "T-START", f"{step} pending; {why}")
        return NextAction("start", step, sv.attempts + 1, "T-RESTART", f"{step} {sv.state}; attempt {sv.attempts + 1}")
    return NextAction("terminal", None, None, "W-5", "every step succeeded")  # unreachable: lifecycle is terminal


def outcome(f: Folder) -> str | None:
    """S-9.7 from what the fold holds: ``partial`` with an open question or a LOOKUP_UNAVAILABLE claim. (The
    extraction status also makes the outcome partial; it is read from the extraction from Step 8 on.)"""
    if f.lifecycle() not in ("COMPLETED", "NEEDS_RESOLUTION"):
        return None
    if f.open_questions() or any(c["class"] == "LOOKUP_UNAVAILABLE" for c in f.committed.claims.values()):
        return "partial"
    return "completed"


def derive(f: Folder, now: datetime) -> WorkflowState:
    """The whole controller state, from the fold and the time (W-1)."""
    return WorkflowState(
        lifecycle=f.lifecycle(),
        steps=tuple(step_view(f, s) for s in STEPS),
        open_questions=tuple(f.open_questions()),
        next=next_action(f, now),
        outcome=outcome(f),
        root_id=f.root_id,
    )


def explain(f: Folder, now: datetime) -> dict[str, Any]:
    """A structured explanation of the current state (S-9.2): why the next step, why blocked, why terminal."""
    st = derive(f, now)
    out: dict[str, Any] = {
        "lifecycle": st.lifecycle,
        "next": {
            "action": st.next.action,
            "step": st.next.step,
            "attempt": st.next.attempt,
            "rule": st.next.rule,
            "reason": st.next.reason,
            "not_before": st.next.not_before.isoformat() if st.next.not_before else None,
        },
        "steps": {
            s.step: {"state": s.state, "attempts": s.attempts, "phi": s.phi, "f": s.f, "a_max": A_MAX, "f_max": F_MAX}
            for s in st.steps
        },
        "open_questions": list(st.open_questions),
        "outcome": st.outcome,
    }
    if st.lifecycle in ("FAILED", "STALE", "NEEDS_RESOLUTION", "COMPLETED"):
        out["terminated_by"] = _terminating_record(f)
    return out


def _terminating_record(f: Folder) -> dict[str, Any]:
    for rec in reversed(f.records):
        if rec["kind"] == "stale_detected":
            return {"seq": rec["seq"], "kind": rec["kind"], "changed": rec["payload"]["changed"]}
        if rec["kind"] == "step_failed" and not rec["payload"]["retryable"]:
            p = rec["payload"]
            return {
                "seq": rec["seq"],
                "kind": "step_failed",
                "step": rec["step"],
                "code": p["code"],
                "reason": p["reason"],
                "detail": p["detail"],
            }
        if rec["kind"] == "step_succeeded" and rec["step"] == "VERIFY":
            return {"seq": rec["seq"], "kind": rec["kind"], "step": "VERIFY", "open_questions": f.open_questions()}
    return {}


# Step keys and staleness (S-9.3, SPEC 10.3, MM 10) -----------------------------------------------------------------


def controller_identity() -> dict[str, Any]:
    """The controller's own part of the Stage 04 identity: the plan, its budgets and its code tables. A change to any
    of them changes the ``stage04`` digest, so a committed step keyed under the old rules is STALE (SPEC 10.3)."""
    return {
        "plan_version": PLAN_VERSION,
        "steps": list(STEPS),
        "a_max": A_MAX,
        "f_max": F_MAX,
        "network_codes": sorted(NETWORK_CODES),
        "extract_retryable": sorted(EXTRACT_RETRYABLE),
        "disposition": dict(sorted(DISPOSITION.items())),
        "conflict": dict(sorted(CONFLICT.items())),
        "step_identities": {s: list(v) for s, v in STEP_IDENTITIES.items()},
    }


def identity_digests(values: Mapping[str, Any]) -> dict[str, str]:
    """Digests of the input identity vector (SPEC 10.3). ``values`` holds the six components as the environment
    reports them now; the controller's own identity is added to ``stage04``. A missing component is a failure,
    never staleness (MM 10.2)."""
    missing = [n for n in IDENTITY_NAMES if n not in values]
    if missing:
        raise InvestigationMemoryError("IDENTITY_UNAVAILABLE", f"identity components missing: {missing}")
    full = {n: copy.deepcopy(values[n]) for n in IDENTITY_NAMES}
    full["stage04"] = {"environment": full["stage04"], "controller": controller_identity()}
    return {n: ids.identity_digest(n, full[n]) for n in IDENTITY_NAMES}


def dependencies(f: Folder, step: str) -> list[list[Any]]:
    out: list[list[Any]] = []
    for d in STEP_DEPENDENCIES[step]:
        done = [a for a in f.attempts[d] if a.end_kind == "step_succeeded"]
        if not done:
            raise InvestigationMemoryError("WORKFLOW_REFUSED", f"{step} reads {d}, which has not succeeded")
        end = f.records[done[-1].end_seq] if done[-1].end_seq is not None else None
        out.append([d, list(end["payload"]["outputs"]) if end else []])
    return out


def created(f: Folder) -> dict[str, Any]:
    if f.created is None:
        raise InvestigationMemoryError("JOURNAL_CORRUPT", "no investigation_created record")
    return f.created


def step_key(f: Folder, step: str, digests: Mapping[str, str]) -> str:
    c = created(f)
    return ids.step_key(
        step,
        c["request"]["config"]["plan_version"],
        dependencies(f, step),
        {n: digests[n] for n in STEP_IDENTITIES[step]},
        c["config_digest"],
    )


def manifest(f: Folder, step: str, key: str, digests: Mapping[str, str]) -> dict[str, Any]:
    """The step manifest blob: the inputs of a committed step's key, so a later resume can name what changed."""
    return {
        "manifest": MANIFEST_TAG,
        "step": step,
        "step_key": key,
        "dependencies": dependencies(f, step),
        "identities": {n: digests[n] for n in STEP_IDENTITIES[step]},
    }
