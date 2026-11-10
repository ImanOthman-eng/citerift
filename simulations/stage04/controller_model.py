"""Independent state-space model of the Stage 04 Investigation Workflow Controller (Step 4 items 5 and 6).

Written from SPECIFICATION.md 9.1 to 10.3 and MATHEMATICAL_MODEL.md 7 to 9, without importing ``citerift``. Two
separate formulations are kept apart on purpose:

- ``successors``: what the controller and its environment can do (SPEC 9.2 step outcomes, 9.3 per-step codes, 10.1
  recovery, crashes, time, input changes, corruption, duplicate invocations). It generates the reachable states.
- ``legal``: the append guard of MM section 8 (rules T-CREATE ... T-STALE plus the root-binding rule M-9 and the
  forbidden list of SPEC 9.2), applied to every record the controller emits and to every record of the full record
  alphabet in every reachable state.

The lifecycle ``lam`` is MM 7.2's ``first(...)`` over the fold. Budgets: ``A_MAX`` failures or interruptions,
``F_MAX`` deferrals (SPEC 9.2).

A state is explored for each of four scenarios: request kind (retained bundle, live capture) x DETECT outcome (no
open question, an open question such as an identity conflict).
"""

from __future__ import annotations

import json
import sys
from collections import Counter, deque
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

STEPS = ("VALIDATE", "ACQUIRE", "EXTRACT", "NORMALIZE", "LOOKUP", "DETECT", "ASSEMBLE", "VERIFY")
A_MAX = 3
F_MAX = 6
BUDGET = {"A": A_MAX, "F": F_MAX}  # the explored budgets (plan-1 values; smaller ones only for the quotient check)
QUOTIENT = {"on": True}  # reduction R-1 (see ``normalize``)
STEP_STATES = ("pending", "running", "succeeded", "failed_retryable", "failed_terminal", "deferred")
LIFECYCLE = ("CREATED", "RUNNING", "BLOCKED", "NEEDS_RESOLUTION", "COMPLETED", "FAILED", "STALE", "CORRUPT")
TERMINAL = frozenset({"NEEDS_RESOLUTION", "COMPLETED", "FAILED", "STALE", "CORRUPT"})
# SPEC 9.3: steps with retryable codes (network in ACQUIRE for a capture, worker limits in EXTRACT).
RETRYABLE = {"ACQUIRE": "live", "EXTRACT": "any"}
NO_CONTENT = frozenset({"VALIDATE"})  # VALIDATE's output is in its step_succeeded payload (SPEC 8.3)


@dataclass(frozen=True)
class Step:
    status: str = "pending"
    phi: int = 0  # attempts closed by step_failed(retryable) or step_interrupted
    f: int = 0  # attempts closed by step_deferred
    attempts: int = 0
    interrupted: bool = False  # the last attempt ended step_interrupted
    content: bool = False  # the open attempt has appended content records


@dataclass(frozen=True)
class State:
    steps: tuple[Step, ...] = tuple(Step() for _ in STEPS)
    created: bool = False
    alive: bool = True  # a controller process holds the lock
    fresh: bool = True  # the process has just opened the journal (recovery not finished)
    orphan: bool = False  # a running attempt belongs to a dead process
    ready: bool = False  # time has reached not_before of the current deferral
    env_changed: bool = False  # an input identity differs from the recorded one
    stale: bool = False  # stale_detected recorded
    corrupt: bool = False  # the journal was damaged (computed on open, never recorded)
    question: bool = False  # DETECT committed with an open question
    root_bound: bool = False
    root_k: int = 0  # the ACQUIRE attempt whose output was committed
    capture_id: int = -1  # identity of the committed capture bytes: 0 for a retained bundle, root_k for a live capture
    committed_content: tuple[str, ...] = ()  # steps whose content was committed, in order


def lam(s: State) -> str | None:
    """MM 7.2: first(corrupt, stale, failed, needs_resolution, completed, blocked, running, created)."""
    if s.corrupt:
        return "CORRUPT"
    if s.stale:
        return "STALE"
    if any(st.status == "failed_terminal" for st in s.steps):
        return "FAILED"
    if all(st.status == "succeeded" for st in s.steps):
        return "NEEDS_RESOLUTION" if s.question else "COMPLETED"
    if any(st.status == "deferred" for st in s.steps):
        return "BLOCKED"
    if any(st.status != "pending" or st.attempts > 0 for st in s.steps):
        return "RUNNING"  # some step_started record exists
    if s.created:
        return "CREATED"
    return None


Record = tuple[str, int, Any]  # (kind, step index or -1, detail)


def record_alphabet() -> list[Record]:
    """Every record kind the journal can hold, for every step, with the details that matter to the guard."""
    out: list[Record] = [("investigation_created", -1, None), ("stale_detected", -1, None)]
    for i in range(len(STEPS)):
        out += [
            ("step_started", i, "next"),
            ("step_started", i, "same"),
            ("step_started", i, "skip"),
            ("content", i, None),
            ("step_succeeded", i, False),
            ("step_succeeded", i, True),
            ("step_failed", i, "retryable"),
            ("step_failed", i, "terminal"),
            ("step_failed", i, "budget"),
            ("step_failed", i, "deferral_budget"),
            ("step_deferred", i, None),
            ("step_interrupted", i, None),
        ]
    return out


def running_index(s: State) -> int | None:
    found = [i for i, st in enumerate(s.steps) if st.status == "running"]
    return found[0] if found else None


def legal(rec: Record, s: State, live: bool) -> str | None:
    """The append guard (MM 8). Returns the rule that permits ``rec`` in ``s``, or None (refused)."""
    kind, i, detail = rec
    lc = lam(s)
    if lc in TERMINAL:
        return None  # TR-3, W-5
    if kind == "investigation_created":
        return "T-CREATE" if not s.created else None
    if not s.created:
        return None
    run = running_index(s)
    if kind == "stale_detected":
        committed = any(st.status == "succeeded" for st in s.steps)
        return "T-STALE" if lc in ("RUNNING", "BLOCKED") and s.env_changed and committed and run is None else None
    st = s.steps[i]
    if kind == "step_started":
        if run is not None or lc not in ("CREATED", "RUNNING", "BLOCKED"):
            return None
        if any(x.status != "succeeded" for x in s.steps[:i]):
            return None
        if detail != "next":  # the attempt number must be the previous one plus one
            return None
        if st.status == "pending" and st.attempts == 0 and lc in ("CREATED", "RUNNING"):
            return "T-START" if (i == 0) == (lc == "CREATED") else None
        if lc == "BLOCKED" and not (st.status == "deferred" and s.ready):
            return None
        if st.status == "failed_retryable" or (st.status == "pending" and st.interrupted):
            return "T-RESTART"
        if st.status == "deferred" and s.ready:
            return "T-RESTART"
        return None
    if st.status != "running" or run != i:
        return None
    if kind == "content":
        if STEPS[i] in NO_CONTENT:
            return None
        if STEPS[i] != "ACQUIRE" and not s.root_bound:
            return None  # M-9 / F-15: no content of another step before the root is bound
        return "T-CONTENT"
    if kind == "step_succeeded":
        if detail and STEPS[i] != "DETECT":
            return None  # only DETECT opens questions
        if STEPS[i] != "VALIDATE" and not st.content:
            return None  # a step that commits outputs has written them first (M-3, M-5)
        return "T-SUCCEED"
    if kind == "step_failed":
        retryable_step = STEPS[i] in RETRYABLE and (RETRYABLE[STEPS[i]] == "any" or live)
        if detail == "retryable":
            return "T-FAIL-R" if retryable_step and st.phi + 1 < BUDGET["A"] else None
        if detail == "terminal":
            return "T-FAIL-T"
        if detail == "budget":
            return "T-FAIL-T" if st.phi + 1 == BUDGET["A"] and (retryable_step or s.orphan) else None
        if detail == "deferral_budget":
            return "T-FAIL-T" if STEPS[i] == "ACQUIRE" and live and st.f == BUDGET["F"] else None
    if kind == "step_deferred":
        return "T-DEFER" if STEPS[i] == "ACQUIRE" and live and st.f < BUDGET["F"] else None
    if kind == "step_interrupted":
        return "T-INTERRUPT" if s.orphan and st.phi + 1 < BUDGET["A"] else None
    return None


def apply(s: State, rec: Record, live: bool = False) -> State:
    kind, i, detail = rec
    if kind == "investigation_created":
        return replace(s, created=True)
    if kind == "stale_detected":
        return replace(s, stale=True)
    steps = list(s.steps)
    st = steps[i]
    if kind == "step_started":
        ready = False if st.status == "deferred" else s.ready
        steps[i] = replace(st, status="running", attempts=st.attempts + 1, interrupted=False, content=False)
        return replace(s, steps=tuple(steps), ready=ready)
    if kind == "content":
        steps[i] = replace(st, content=True)
        return replace(s, steps=tuple(steps))
    if kind == "step_succeeded":
        steps[i] = replace(st, status="succeeded", content=False)
        out = replace(s, steps=tuple(steps), committed_content=(*s.committed_content, STEPS[i]))
        if STEPS[i] == "ACQUIRE":
            # A retained bundle is the same bytes on every attempt; a live capture fetches anew on each attempt, and
            # its capture.json records fetch times, so each ACQUIRE attempt has its own capture identity (F-09).
            out = replace(out, root_bound=True, root_k=st.attempts, capture_id=st.attempts if live else 0)
        if STEPS[i] == "DETECT" and detail:
            out = replace(out, question=True)
        return out
    if kind == "step_failed":
        if detail == "retryable":
            steps[i] = replace(st, status="failed_retryable", phi=st.phi + 1, content=False)
        else:
            steps[i] = replace(st, status="failed_terminal", content=False)
        return replace(s, steps=tuple(steps), orphan=False)
    if kind == "step_deferred":
        steps[i] = replace(st, status="deferred", f=st.f + 1, content=False)
        return replace(s, steps=tuple(steps), ready=False)
    if kind == "step_interrupted":
        steps[i] = replace(st, status="pending", phi=st.phi + 1, interrupted=True, content=False)
        return replace(s, steps=tuple(steps), orphan=False)
    raise AssertionError(rec)


Edge = tuple[str, Record | None, State]  # (event label, record appended or None, next state)


def normalize(s: State) -> State:
    """Reduction R-1 (history quotient): forget the counters of succeeded steps.

    Nothing that ``legal``, ``successors``, ``lam`` or any checked property reads depends on the ``phi``, ``f``,
    ``attempts`` or ``interrupted`` of a step whose status is ``succeeded`` (they are read only for the running,
    retryable, deferred or pending step; the ACQUIRE attempt that bound the root is kept in ``root_k``). Two states
    that differ only there have the same future, so one representative is explored. Per-step attempt maxima are
    taken before normalization (``peak``). ``quotient_check`` compares the quotient with the full space."""
    if not QUOTIENT["on"]:
        return s
    steps = tuple(Step(status="succeeded") if st.status == "succeeded" else st for st in s.steps)
    return s if steps == s.steps else replace(s, steps=steps)


def successors(s: State, live: bool, conflict: bool) -> list[Edge]:
    """Controller and environment moves from ``s`` (SPEC 9.2, 9.3, 10.1, 10.2)."""
    out: list[Edge] = []
    lc = lam(s)
    # Environment: corruption, input change and time can happen at any moment before the end.
    if not s.corrupt and lc not in TERMINAL:
        out.append(("env:corrupt", None, replace(s, corrupt=True, alive=False)))
    if not s.env_changed and lc not in TERMINAL:
        out.append(("env:input_changed", None, replace(s, env_changed=True)))
    if lc == "BLOCKED" and not s.ready:
        out.append(("env:time_reaches_not_before", None, replace(s, ready=True)))
    if not s.alive:
        # A new invocation: a terminal or corrupt investigation is reported and left as it is (S-9.4, CORRUPT
        # read-only); otherwise the process takes the lock and recovers.
        if lc in TERMINAL or s.corrupt:
            out.append(("run:terminal_noop", None, s))
        else:
            out.append(("run:open", None, replace(s, alive=True, fresh=True)))
        return out
    # A second invocation while a process holds the lock: INVESTIGATION_BUSY, nothing written.
    out.append(("run:busy_noop", None, s))
    if lc in TERMINAL:
        out.append(("proc:exit", None, replace(s, alive=False)))
        return out
    out.append(("env:crash", None, replace(s, alive=False, orphan=s.orphan or running_index(s) is not None)))
    if not s.created:
        out.append(
            ("ctl:create", ("investigation_created", -1, None), apply(s, ("investigation_created", -1, None), live))
        )
        return out
    run = running_index(s)
    if s.fresh:
        # SPEC 10.1 step 4: close an attempt left open by a dead process before anything else (W-6).
        if s.orphan:
            if not (run is not None):
                raise AssertionError("model invariant")
            st = s.steps[run]
            rec: Record = (
                ("step_interrupted", run, None) if st.phi + 1 < BUDGET["A"] else ("step_failed", run, "budget")
            )
            out.append(("ctl:recover", rec, apply(s, rec, live)))
            return out
        # SPEC 10.1 step 5: recompute step keys; a difference is STALE.
        committed = any(st.status == "succeeded" for st in s.steps)
        if s.env_changed and committed:
            rec = ("stale_detected", -1, None)
            out.append(("ctl:stale", rec, apply(s, rec, live)))
            return out
        out.append(("ctl:recovered", None, replace(s, fresh=False)))
        return out
    if run is not None:
        st = s.steps[run]
        name = STEPS[run]
        if name not in NO_CONTENT and not st.content:
            rec = ("content", run, None)
            out.append(("ctl:write_content", rec, apply(s, rec, live)))
        if name in NO_CONTENT or st.content:
            rec = ("step_succeeded", run, conflict if name == "DETECT" else False)
            out.append(("env:step_succeeds", rec, apply(s, rec, live)))
        rec = ("step_failed", run, "terminal")
        out.append(("env:step_fails_terminal", rec, apply(s, rec, live)))
        if name in RETRYABLE and (RETRYABLE[name] == "any" or live):
            rec = ("step_failed", run, "retryable") if st.phi + 1 < BUDGET["A"] else ("step_failed", run, "budget")
            out.append(("env:step_fails_retryable", rec, apply(s, rec, live)))
        if name == "ACQUIRE" and live:
            rec = ("step_deferred", run, None) if st.f < BUDGET["F"] else ("step_failed", run, "deferral_budget")
            out.append(("env:stage03_defers", rec, apply(s, rec, live)))
        return out
    nxt = next(i for i, st in enumerate(s.steps) if st.status != "succeeded")
    st = s.steps[nxt]
    if st.status == "deferred" and not s.ready:
        out.append(("proc:exit_blocked", None, replace(s, alive=False)))  # the controller never sleeps
        return out
    rec = ("step_started", nxt, "next")
    out.append(("ctl:start", rec, apply(s, rec, live)))
    return out


FORBIDDEN_CATEGORIES = (
    "out_of_succeeded",
    "out_of_failed_terminal",
    "pending_to_succeeded_or_failed",
    "second_open_attempt",
    "start_before_previous_succeeded",
    "start_while_another_running",
    "content_outside_open_attempt",
    "second_step_succeeded",
    "content_before_root_bound",
    "wrong_attempt_number",
    "any_record_after_terminal",
)


def forbidden_category(rec: Record, s: State) -> list[str]:
    """The SPEC 9.2 forbidden list, written independently of ``legal``: which listed prohibitions ``rec`` breaks."""
    kind, i, detail = rec
    cats: list[str] = []
    if lam(s) in TERMINAL:
        cats.append("any_record_after_terminal")
    if i < 0:
        return cats
    st = s.steps[i]
    run = running_index(s)
    step_record = kind in (
        "step_started",
        "step_succeeded",
        "step_failed",
        "step_deferred",
        "step_interrupted",
        "content",
    )
    if step_record and st.status == "succeeded":
        cats.append("out_of_succeeded")
    if kind == "step_succeeded" and st.status == "succeeded":
        cats.append("second_step_succeeded")
    if step_record and st.status == "failed_terminal":
        cats.append("out_of_failed_terminal")
    if kind in ("step_succeeded", "step_failed") and st.status == "pending":
        cats.append("pending_to_succeeded_or_failed")
    if kind == "step_started":
        if st.status == "running":
            cats.append("second_open_attempt")
        if any(x.status != "succeeded" for x in s.steps[:i]):
            cats.append("start_before_previous_succeeded")
        if run is not None and run != i:
            cats.append("start_while_another_running")
        if detail != "next":
            cats.append("wrong_attempt_number")
    if kind == "content" and st.status != "running":
        cats.append("content_outside_open_attempt")
    if kind == "content" and STEPS[i] not in ("ACQUIRE",) and not s.root_bound:
        cats.append("content_before_root_bound")
    return cats


LIMIT = {"states": 400_000}


def explore(live: bool, conflict: bool) -> dict[str, Any]:
    start = State()
    seen: dict[State, int] = {start: 0}
    order = [start]
    edges: list[tuple[int, str, Record | None, int]] = []
    monotone_violations: list[Any] = []  # counters compared before normalization (R-1 resets succeeded steps)
    queue = deque([start])
    peak = [0] * len(STEPS)
    truncated = False
    while queue:
        if len(order) > LIMIT["states"]:
            truncated = True  # reported as a violation: the declared machine is finite well below this limit
            break
        s = queue.popleft()
        for label, rec, t0 in successors(s, live, conflict):
            for i, st in enumerate(t0.steps):
                peak[i] = max(peak[i], st.attempts)
                x = s.steps[i]
                if x.status != "succeeded" and not (st.phi >= x.phi and st.f >= x.f and st.attempts >= x.attempts):
                    monotone_violations.append([label, STEPS[i]])
            t = normalize(t0)
            if t not in seen:
                seen[t] = len(order)
                order.append(t)
                queue.append(t)
            edges.append((seen[s], label, rec, seen[t]))
    return {
        "states": order,
        "edges": edges,
        "peak": peak,
        "monotone_violations": monotone_violations,
        "truncated": truncated,
    }


def check(live: bool, conflict: bool) -> dict[str, Any]:
    g = explore(live, conflict)
    states: list[State] = g["states"]
    edges = g["edges"]
    v: Counter[str] = Counter()
    examples: dict[str, list[Any]] = {}
    checked: Counter[str] = Counter()

    def fail(name: str, ok: bool, detail: Any) -> None:
        checked[name] += 1
        if not ok:
            v[name] += 1
            if len(examples.setdefault(name, [])) < 3:
                examples[name].append(detail)

    fail("STATE_SPACE_FINITE", not g["truncated"], LIMIT["states"])
    step_state_seen = {(STEPS[i], st.status) for s in states for i, st in enumerate(s.steps)}
    lifecycle_seen = Counter(str(lam(s)) for s in states)
    rules_used: Counter[str] = Counter()
    alphabet = record_alphabet()
    legal_props = forbidden_props = 0
    forbidden_by_cat: Counter[str] = Counter()
    for s in states if not g["truncated"] else []:  # on a truncated (mutated) space only edge checks run
        for rec in alphabet:
            rule = legal(rec, s, live)
            cats = forbidden_category(rec, s)
            for c in cats:
                forbidden_by_cat[c] += 1
            if rule is None:
                forbidden_props += 1
            else:
                legal_props += 1
            fail("FORBIDDEN_REFUSED", not (cats and rule is not None), {"record": rec, "categories": cats})
        if lam(s) in TERMINAL:
            fail("TERMINAL_REFUSES_ALL", all(legal(r, s, live) is None for r in alphabet), lam(s))
    for a, label, rec, b in edges:
        s, t = states[a], states[b]
        if rec is not None:
            rule = legal(rec, s, live)
            fail("EMITTED_RECORD_LEGAL", rule is not None, {"label": label, "record": rec})
            if rule:
                rules_used[rule] += 1
        for i in range(len(STEPS)):
            x, y = s.steps[i], t.steps[i]
            if x.status in ("succeeded", "failed_terminal"):
                fail(
                    "NO_ESCAPE_FROM_TERMINAL_STEP",
                    x.status == y.status and x.attempts == y.attempts,
                    {"step": STEPS[i], "label": label},
                )
        if lam(s) in TERMINAL:
            fail("NO_ESCAPE_FROM_TERMINAL_LIFECYCLE", rec is None and lam(t) == lam(s), {"label": label})
        if s.root_bound:
            fail("ROOT_IMMUTABLE", t.root_bound and t.root_k == s.root_k, label)
        if rec is not None and rec[0] == "content" and STEPS[rec[1]] != "ACQUIRE":
            fail("NO_CONTENT_BEFORE_ROOT", s.root_bound, {"label": label, "record": rec})
        if label == "ctl:recover":
            fail("RECOVERY_FIRST", rec is not None and rec[0] in ("step_interrupted", "step_failed"), rec)
        if label in ("run:busy_noop", "run:terminal_noop"):
            fail("DUPLICATE_INVOCATION_IDEMPOTENT", s == t, label)
    checked["COUNTERS_MONOTONE"] += len(edges)
    if g["monotone_violations"]:
        v["COUNTERS_MONOTONE"] += len(g["monotone_violations"])
        examples["COUNTERS_MONOTONE"] = g["monotone_violations"][:3]
    for s in states:
        lc = lam(s)
        for st in s.steps:
            fail("RETRY_BUDGET", st.phi < BUDGET["A"], st)
            fail("DEFERRAL_BUDGET", st.f <= BUDGET["F"], st)
        if lc == "BLOCKED":
            dfr = [STEPS[i] for i, st in enumerate(s.steps) if st.status == "deferred"]
            fail("BLOCKED_ONLY_WHEN_DEFERRED", live and dfr == ["ACQUIRE"], dfr)
        if lc == "COMPLETED":
            fail("COMPLETED_ALL_SUCCEEDED", all(st.status == "succeeded" for st in s.steps), s)
            fail("CONFLICT_NEVER_COMPLETED", not s.question, s)
        if lc == "NEEDS_RESOLUTION":
            fail("NEEDS_RESOLUTION_PARTIAL", s.question and all(st.status == "succeeded" for st in s.steps), s)
        if s.question:
            fail("CONFLICT_NEVER_COMPLETED", lc != "COMPLETED", s)
    # Cycles: every strongly connected component may contain only edges that append no record.
    scc = _sccs(len(states), [(a, b) for a, _, _, b in edges])
    comp_of = {n: k for k, comp in enumerate(scc) for n in comp}
    cyc_records = [(label, rec) for a, label, rec, b in edges if comp_of[a] == comp_of[b] and rec is not None]
    fail("NO_RECORD_IN_ANY_CYCLE", not cyc_records, cyc_records[:3])
    if g["truncated"]:
        return {
            "scenario": {"request": "live_capture" if live else "retained_bundle"},
            "truncated": True,
            "properties": {
                k: {"checked": checked[k], "violations": v.get(k, 0), "examples": examples.get(k, [])}
                for k in sorted(checked)
            },
        }
    # Liveness (TR-5): every non-terminal state can reach a terminal one.
    rev: dict[int, list[int]] = {}
    for a, _, _, b in edges:
        rev.setdefault(b, []).append(a)
    good = {i for i, s in enumerate(states) if lam(s) in TERMINAL}
    frontier = deque(good)
    while frontier:
        n = frontier.popleft()
        for m in rev.get(n, []):
            if m not in good:
                good.add(m)
                frontier.append(m)
    stuck = [i for i in range(len(states)) if i not in good]
    fail("TERMINAL_REACHABLE_FROM_EVERY_STATE", not stuck, [states[i].__dict__ for i in stuck[:1]])
    longest = _longest_records(len(states), edges, comp_of)
    terminal_states = [s for s in states if lam(s) in TERMINAL]
    max_attempts = {STEPS[i]: g["peak"][i] for i in range(len(STEPS))}
    # F-09: content identity of completed runs. C depends on the committed ACQUIRE output; for a retained bundle it
    # is the same bundle on every attempt, for a live capture each ACQUIRE attempt captures anew (root_k).
    done = [s for s in states if lam(s) in ("COMPLETED", "NEEDS_RESOLUTION")]
    contents = Counter((s.capture_id, s.question, s.committed_content) for s in done)
    if not live:
        # P6 / F-09: with a retained bundle, every completed run (any interruptions, retries) has one content identity.
        fail("RETAINED_RESUME_CONVERGES", len(contents) <= 1, sorted(contents)[:3])
    return {
        "scenario": {"request": "live_capture" if live else "retained_bundle", "detect_opens_question": conflict},
        "states": len(states),
        "transitions": len(edges),
        "transitions_appending_a_record": sum(1 for e in edges if e[2] is not None),
        "step_states_reached": sorted(f"{a}:{b}" for a, b in step_state_seen),
        "lifecycle_states_reached": dict(sorted(lifecycle_seen.items())),
        "terminal_states": len(terminal_states),
        "terminal_by_lifecycle": dict(Counter(str(lam(s)) for s in terminal_states)),
        "rules_used": dict(sorted(rules_used.items())),
        "proposals_checked": legal_props + forbidden_props,
        "proposals_legal": legal_props,
        "proposals_refused": forbidden_props,
        "forbidden_by_category": dict(sorted(forbidden_by_cat.items())),
        "max_attempts_per_step": max_attempts,
        "max_records_on_any_path": longest,
        "sccs": len(scc),
        "nontrivial_sccs": sum(1 for c in scc if len(c) > 1),
        "completed_content_identities": len(contents),
        "completed_capture_ids": sorted({k for k, _, _ in contents}),
        "properties": {
            k: {"checked": checked[k], "violations": v.get(k, 0), "examples": examples.get(k, [])}
            for k in sorted(checked)
        },
    }


def _sccs(n: int, edges: list[tuple[int, int]]) -> list[list[int]]:
    """Tarjan's algorithm, iterative."""
    adj: list[list[int]] = [[] for _ in range(n)]
    for a, b in edges:
        adj[a].append(b)
    index = [0] * n
    low = [0] * n
    onstack = [False] * n
    visited = [False] * n
    stack: list[int] = []
    out: list[list[int]] = []
    counter = 1
    for root in range(n):
        if visited[root]:
            continue
        work = [(root, 0)]
        visited[root] = True
        index[root] = low[root] = counter
        counter += 1
        stack.append(root)
        onstack[root] = True
        while work:
            node, pos = work[-1]
            if pos < len(adj[node]):
                work[-1] = (node, pos + 1)
                nxt = adj[node][pos]
                if not visited[nxt]:
                    visited[nxt] = True
                    index[nxt] = low[nxt] = counter
                    counter += 1
                    stack.append(nxt)
                    onstack[nxt] = True
                    work.append((nxt, 0))
                elif onstack[nxt]:
                    low[node] = min(low[node], index[nxt])
            else:
                work.pop()
                if work:
                    parent = work[-1][0]
                    low[parent] = min(low[parent], low[node])
                if low[node] == index[node]:
                    comp = []
                    while True:
                        x = stack.pop()
                        onstack[x] = False
                        comp.append(x)
                        if x == node:
                            break
                    out.append(comp)
    return out


def _longest_records(n: int, edges: list[tuple[int, str, Record | None, int]], comp_of: dict[int, int]) -> int:
    """Longest number of appended records on any path (finite because no cycle appends a record)."""
    cadj: dict[int, list[tuple[int, int]]] = {}
    for a, _, rec, b in edges:
        ca, cb = comp_of[a], comp_of[b]
        if ca != cb:
            cadj.setdefault(ca, []).append((cb, 1 if rec is not None else 0))
    memo: dict[int, int] = {}
    sys.setrecursionlimit(100000)

    def best(c: int) -> int:
        if c not in memo:
            memo[c] = max((w + best(d) for d, w in cadj.get(c, [])), default=0)
        return memo[c]

    return max(best(comp_of[0]), 0)


def quotient_check(a: int, f: int) -> dict[str, Any]:
    """Soundness of reduction R-1 on smaller budgets: the full space, projected by ``normalize``, equals the
    quotient space, and every property gives the same verdict in both."""
    saved = dict(BUDGET)
    BUDGET.update(A=a, F=f)
    try:
        out = []
        for live in (False, True):
            for conflict in (False, True):
                QUOTIENT["on"] = False
                full = explore(live, conflict)
                full_props = {k: v["violations"] for k, v in check(live, conflict)["properties"].items()}
                QUOTIENT["on"] = True
                quot = explore(live, conflict)
                quot_props = {k: v["violations"] for k, v in check(live, conflict)["properties"].items()}
                projected = {normalize(x) for x in full["states"]}
                out.append(
                    {
                        "live": live,
                        "conflict": conflict,
                        "full_states": len(full["states"]),
                        "quotient_states": len(quot["states"]),
                        "projection_equal": projected == set(quot["states"]),
                        "peaks_equal": full["peak"] == quot["peak"],
                        "property_verdicts_equal": full_props == quot_props,
                    }
                )
        return {
            "a_max": a,
            "f_max": f,
            "runs": out,
            "sound": all(r["projection_equal"] and r["peaks_equal"] and r["property_verdicts_equal"] for r in out),
        }
    finally:
        BUDGET.clear()
        BUDGET.update(saved)
        QUOTIENT["on"] = True


def run(out: Path | None = None) -> dict[str, Any]:
    results = [check(live, conflict) for live in (False, True) for conflict in (False, True)]
    summary = {
        "a_max": A_MAX,
        "f_max": F_MAX,
        "scenarios": results,
        "quotient_checks": [quotient_check(2, 1), quotient_check(2, 2)],
        "total_states": sum(r["states"] for r in results),
        "total_transitions": sum(r["transitions"] for r in results),
        "violations": {
            k: sum(r["properties"].get(k, {}).get("violations", 0) for r in results)
            for r in results
            for k in r["properties"]
        },
    }
    if out is not None:
        out.mkdir(parents=True, exist_ok=True)
        (out / "controller_model_summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    return summary


if __name__ == "__main__":
    s = run(Path(sys.argv[1]) if len(sys.argv) > 1 else None)
    for r in s["scenarios"]:
        print(
            json.dumps(
                {
                    k: r[k]
                    for k in (
                        "scenario",
                        "states",
                        "transitions",
                        "lifecycle_states_reached",
                        "max_attempts_per_step",
                        "max_records_on_any_path",
                        "completed_content_identities",
                        "completed_capture_ids",
                    )
                }
            )
        )
    print(json.dumps(s["violations"]))
    print(
        json.dumps(
            [
                {k: q[k] for k in ("a_max", "f_max", "sound")}
                | {"runs": [(r["full_states"], r["quotient_states"]) for r in q["runs"]]}
                for q in s["quotient_checks"]
            ]
        )
    )
    raise SystemExit(1 if any(s["violations"].values()) or not all(q["sound"] for q in s["quotient_checks"]) else 0)
