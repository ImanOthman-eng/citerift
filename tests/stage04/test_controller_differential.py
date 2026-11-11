"""Step 7: differential test of the production controller against the frozen Step 4 model (owner Step 7 item 8).

The reference is ``simulations/stage04/controller_model.py``, written in Step 4 without importing ``citerift`` and
pinned here by digest; it is never changed to make production pass. Seeded random walks follow the model's own
``successors`` (controller moves and environment events) and perform each event on real Investigation Memory with the
production controller's primitives (``recover``, ``check_stale``, guarded appends). After every event the two are
compared on: step states, attempt counters ``phi``, ``f`` and attempts, the lifecycle, the next legal action, the
open-question flag and the terminal outcome. In every state, every record of the model's ``record_alphabet`` is
proposed to both: the model's ``legal`` against production's guard followed by Memory's append check.

Discrepancies are classified (``classify``); the test fails on any discrepancy outside the classified categories:

* ``W6_STRICTER`` (spec, not a defect of either): in a state with an attempt of a dead process, the model's
  ``legal`` (MM 8 alone) permits records that continue the attempt; production refuses them by W-6 (SPEC 9.9),
  which the model enforces in ``successors`` instead (recovery is the only move from such a state).
* ``SUCCESS_FLAG`` (abstraction): the model's ``step_succeeded`` carries a flag "opens a question"; in production
  that is a property of the step's content, so only the flag matching the scenario's DETECT content is compared.
* ``BATCH_SERIES_CLOSED`` (spec, owner decision D-053): the model's "content" is any number of content records in
  an open attempt; in production NORMALIZE's and DETECT's evidence is one series of batch records numbered
  ``batch_index`` of ``batch_total`` (SPEC 8.8), so once an attempt has written its content, a further batch record is
  refused (S-8.8 ``BATCH_SEQUENCE``). Checked by ``test_batch_series_closed_is_the_batch_sequence_rule``.

Input changes are applied only once a step has committed (see ``test_input_change_before_any_commit``): before
that, the model's sticky ``env_changed`` flag makes a later resume STALE, while SPEC S-10.1 defines staleness by the
keys of committed steps, and production (which keys the first committed step with the changed identities) is not
stale. That case is classified as a reference-model over-approximation and checked separately.
"""

from __future__ import annotations

import copy
import hashlib
import random
import sys
from collections import Counter
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from controller_support import (
    BUNDLE,
    EXTRACTION,
    LOOKUP,
    Env,
    Plan,
    StepClock,
    append_content,
    digest,
    env_for,
    evidence,
    lookup_evidence,
    ok_result,
    synthetic_report,
)
from memory_support import bundle_payload, memory_root, root_object

from citerift.investigation import batches, sets, workflow
from citerift.investigation.controller import _content, open_controller, run_investigation
from citerift.investigation.errors import Busy, CorruptInvestigation, InvariantViolation
from citerift.investigation.fold import STEPS
from citerift.investigation.memory import InvestigationMemory, created_payload

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "simulations" / "stage04"))
import controller_model as C  # noqa: E402

pytestmark = pytest.mark.simulation

# The frozen Step 4 reference model (accepted at 244c4b6). A change to it must be visible here.
MODEL_SHA256 = "90a52fb4373911aaf77620028c1539678e765fd7ec8e566f20744ad9e4629138"

TERMINAL_CODE = {
    "VALIDATE": ("INPUT_INVALID", "WIKI_UNSUPPORTED"),
    "ACQUIRE": ("PAGE_MISSING", None),
    "EXTRACT": ("EXTRACTION_FAILED", None),
    "NORMALIZE": ("NORMALIZE_INVALID", None),
    "LOOKUP": ("INDEX_MISSING", None),
    "DETECT": ("ADAPTER_INCONSISTENT", None),
    "ASSEMBLE": ("REPORT_INVALID", None),
    "VERIFY": ("VERIFY_FAILED", "CHECK_FAILED"),
}
RETRYABLE_CODE = {"ACQUIRE": "HTTP_TIMEOUT", "EXTRACT": "EXTRACTION_WORKER_FAILED"}
PROJECTIONS = sets.projection_set([])


def test_reference_model_is_the_frozen_one() -> None:
    data = (ROOT / "simulations" / "stage04" / "controller_model.py").read_bytes()
    assert hashlib.sha256(data).hexdigest() == MODEL_SHA256


class Prod:
    """The production side of one walk: real Memory, the production controller, the fake environment."""

    def __init__(self, base: Path, live: bool, conflict: bool) -> None:
        self.base, self.live, self.conflict = base, live, conflict
        self.root = memory_root(base)
        self.clock = StepClock()
        self.env: Env = env_for(live)
        self.key = ""
        self.mem: InvestigationMemory | None = None
        self.ctl: Any = None
        self.corrupt = False
        self.attempt: dict[str, Any] = {}  # step_key, digests and result of the open attempt
        self.classes = (("IDENTITY_CONFLICT", "c1"),) if conflict else (("NOT_FOUND_IN_CHECKED_SOURCES", "c1"),)

    # Process events --------------------------------------------------------------------------------------------

    def create(self) -> None:
        if self.live:
            from memory_support import STAGE04, live_request

            payload = created_payload(live_request(self.root), STAGE04)
        else:
            payload = bundle_payload(self.root)
        self.key = str(payload["investigation_key"])
        with InvestigationMemory.create(self.root, payload, clock=self.clock) as mem:
            for b in (BUNDLE, EXTRACTION, LOOKUP, PROJECTIONS):  # probe records name these blobs
                mem.put_blob(b)

    def open(self) -> None:
        if not self.key:  # a new process before anything was created: it will create the investigation
            return
        self.mem, self.ctl = open_controller(self.root, self.key, Plan().adapters(), self.env, clock=self.clock)

    def close(self) -> None:
        if self.mem is not None:
            self.mem.close()
        self.mem, self.ctl = None, None

    def corrupt_journal(self) -> None:
        self.close()
        path = self.root / self.key / "journal.jsonl"
        data = bytearray(path.read_bytes())
        data[60] ^= 0x01  # inside record 0: a bit flip, CORRUPT on open
        path.write_bytes(bytes(data))
        self.corrupt = True

    # Controller moves --------------------------------------------------------------------------------------------

    def start(self, step: str) -> None:
        f = self.ctl.view
        digests = self.ctl.current_digests()
        key = workflow.step_key(f, step, digests)
        attempt = len(f.attempts[step]) + 1
        self.ctl._append("step_started", {"step_key": key}, step, attempt)
        self.ctl._own.add((step, attempt))
        self.attempt = {"step": step, "attempt": attempt, "key": key, "digests": digests, "result": None}

    def _result(self) -> Any:
        if self.attempt["result"] is None:
            a = self.attempt
            req = self.ctl._request(a["step"], a["attempt"], a["key"])
            a["result"] = ok_result(req, self.classes)
        return self.attempt["result"]

    def write_content(self) -> None:
        a, r = self.attempt, self._result()
        for b in r.blobs:
            self.mem.put_blob(b)  # type: ignore[union-attr]
        append_content(self.ctl, a["step"], a["attempt"], _content(a["step"], r))

    def succeed(self) -> None:
        a, r = self.attempt, self._result()
        for b in r.blobs:
            self.mem.put_blob(b)  # type: ignore[union-attr]
        man = self.mem.put_blob(workflow.manifest(self.ctl.view, a["step"], a["key"], a["digests"]))  # type: ignore[union-attr]
        payload = {"step_key": a["key"], "outputs": list(dict.fromkeys([*r.outputs, man])), "root": r.root}
        self.ctl._append("step_succeeded", payload, a["step"], a["attempt"])

    def fail(self, detail: str) -> None:
        a = self.attempt
        step = a["step"]
        if detail == "retryable":
            code, retryable, reason = RETRYABLE_CODE[step], True, None
        elif detail == "budget":
            code, retryable, reason = "RETRY_BUDGET_EXHAUSTED", False, RETRYABLE_CODE.get(step, "STEP_INTERRUPTED")
        elif detail == "deferral_budget":
            code, retryable, reason = "DEFERRAL_BUDGET_EXHAUSTED", False, "DEFERRED_RETRY_AFTER"
        else:
            code, reason = TERMINAL_CODE[step]
            retryable = False
        payload = self.ctl._failure_payload(step, a["key"], code, retryable, reason, None, None, None)
        self.ctl._append("step_failed", payload, step, a["attempt"])

    def defer(self) -> None:
        a = self.attempt
        nb = self.clock.t + timedelta(days=1)
        payload = {
            "step_key": a["key"],
            "code": "DEFERRED_RETRY_AFTER",
            "not_before": nb.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        }
        self.ctl._append("step_deferred", payload, a["step"], a["attempt"])

    # Legality of a model record (the record alphabet) ---------------------------------------------------------------

    def legal(self, rec: Any, orphan: bool) -> str | None:
        kind, i, detail = rec
        f = self.ctl.view
        proposal = self._proposal(kind, i, detail)
        if proposal is None:
            return None
        try:
            rule = workflow.guard(proposal, f, orphan=orphan)
        except workflow.WorkflowRefused:
            return None
        full = self._full(proposal)
        try:
            f.check(full)
        except InvariantViolation:
            return None
        return rule

    def _proposal(self, kind: str, i: int, detail: Any) -> dict[str, Any] | None:
        f = self.ctl.view
        at = self.clock.t.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        if kind == "investigation_created":
            return {"kind": kind, "step": None, "attempt": None, "payload": copy.deepcopy(f.created), "at": at}
        if kind == "stale_detected":
            payload = self.ctl.stale_payload(self.ctl.current_digests())  # errors propagate (review F6)
            if payload is None:
                return None  # production emits stale_detected only when a recomputed key differs
            return {"kind": kind, "step": None, "attempt": None, "payload": payload, "at": at}
        step = STEPS[i]
        n = len(f.attempts[step])
        open_here = f.open is not None and f.open.step == step
        attempt = (
            f.open.number
            if open_here and kind != "step_started"
            else {"next": n + 1, "same": n, "skip": n + 2}.get(detail, max(n, 1))
        )
        key = f.records[f.open.start_seq]["payload"]["step_key"] if open_here else "7" * 64
        p: dict[str, Any] = {"step_key": key}
        if kind == "content":
            kind, p = self._probe_content(step)
        elif kind == "step_succeeded":
            p = {"step_key": key, "outputs": [digest(BUNDLE)], "root": root_object() if step == "ACQUIRE" else None}
        elif kind == "step_failed":
            code, retryable, reason = {
                "retryable": (RETRYABLE_CODE.get(step, "HTTP_TIMEOUT"), True, None),
                "terminal": (*TERMINAL_CODE[step][:1], False, TERMINAL_CODE[step][1]),
                "budget": ("RETRY_BUDGET_EXHAUSTED", False, RETRYABLE_CODE.get(step, "STEP_INTERRUPTED")),
                "deferral_budget": ("DEFERRAL_BUDGET_EXHAUSTED", False, "DEFERRED_RETRY_AFTER"),
            }[detail]
            p = {
                "step_key": key,
                "code": code,
                "retryable": retryable,
                "reason": reason,
                "detail": None,
                "wall_clock": None,
            }
            if step == "ACQUIRE":
                p["not_before"] = None
        elif kind == "step_deferred":
            p = {"step_key": key, "code": "DEFERRED_RETRY_AFTER", "not_before": at}
        return {"kind": kind, "step": step, "attempt": attempt, "payload": p, "at": at}

    def _probe_content(self, step: str) -> tuple[str, dict[str, Any]]:
        def obs(kind: str, blob: dict[str, Any], op: str) -> dict[str, Any]:
            engine = "citerift.retraction" if kind == "lookup" else "citerift.wiki"
            return {
                "obs_kind": kind,
                "blob": digest(blob),
                "source_ref": {"engine": engine, "operation": op, "locator": None},
            }

        if step in ("VALIDATE", "ACQUIRE"):
            return "observation_recorded", obs("bundle", BUNDLE, "open_bundle")
        if step == "EXTRACT":
            return "observation_recorded", obs("extraction", EXTRACTION, "extract_bundle")
        if step == "LOOKUP":
            return "observation_recorded", obs("lookup", LOOKUP, "gather")
        if step in ("NORMALIZE", "DETECT"):
            if step == "NORMALIZE":
                item = evidence(
                    "unit",
                    digest(EXTRACTION),
                    "/probe",
                    [],
                    {"source_artifact": "a" * 64, "unit_span_sha256": "b" * 64},
                )
            else:
                e = lookup_evidence()[0]
                item = {
                    **e,
                    "pointer": "/probe",
                    "evidence_id": evidence("lookup_result", e["observation"], "/probe", [], None)["evidence_id"],
                }
            # D-053: content of these steps is a batch record; the probe publishes its one-item batch (an orphan blob
            # unless the record is written) and takes the next index of the attempt's series.
            batch = batches.evidence_batch([item])
            d = self.mem.put_blob(batch)  # type: ignore[union-attr]
            pending = self.ctl.view.pending
            index = len(pending.batches)
            total = pending.batch_total if pending.batch_total is not None else index + 1
            return "evidence_batch_recorded", {
                "batch": d,
                "batch_index": index,
                "batch_total": total,
                "evidence_count": 1,
            }
        if step == "ASSEMBLE":
            # D-054: Memory proves the report graph against the fold, so the probe publishes a true manifest of the
            # committed content (and its chunks) before proposing the record.
            f = self.ctl.view
            if f.root_id is None:  # no root is bound: the record is illegal on both sides whatever it names
                return "report_recorded", {
                    "report": digest(PROJECTIONS),
                    "projection_set": digest(PROJECTIONS),
                    "projection_count": 0,
                }
            created = workflow.created(f)
            chunks: list[Any] = []
            ids_ = {k: created[k] for k in ("investigation_key", "investigation_id")}
            manifest = synthetic_report(
                f.committed_content(), f.root, ids_, created["request"], workflow.is_live(f), chunks
            )
            for blob in (*chunks, manifest, PROJECTIONS):
                self.mem.put_blob(blob)  # type: ignore[union-attr]
            return "report_recorded", {
                "report": digest(manifest),
                "projection_set": digest(PROJECTIONS),
                "projection_count": 0,
            }
        return "verification_recorded", {
            "result": "passed",
            "checks": [{"check": "PROBE", "passed": True}],
            "content_digest": "c" * 64,
        }

    def _full(self, proposal: dict[str, Any]) -> dict[str, Any]:
        from citerift.investigation.memory import _record

        f = self.ctl.view
        p = proposal["payload"]
        binds = proposal["kind"] == "step_succeeded" and proposal["step"] == "ACQUIRE"
        root_id = p["root"]["root_id"] if binds and isinstance(p.get("root"), dict) else f.root_id
        at = max(proposal["at"], f.records[-1]["at"])
        return _record(
            len(f.records), f.last_digest, proposal["kind"], proposal["step"], proposal["attempt"], at, root_id, p
        )


def classify(rec: Any, s: Any, model_rule: str | None, prod_rule: str | None, conflict: bool) -> str | None:
    """The category of a legality discrepancy, or None when it is not one of the classified categories."""
    kind, i, detail = rec
    if s.orphan and model_rule is not None and prod_rule is None:
        run = C.running_index(s)
        if i == run and kind in ("content", "step_succeeded", "step_failed", "step_deferred"):
            return "W6_STRICTER"
    if kind == "step_succeeded" and detail != (conflict and C.STEPS[i] == "DETECT"):
        return "SUCCESS_FLAG"
    if (
        kind == "content"
        and C.STEPS[i] in ("NORMALIZE", "DETECT")
        and s.steps[i].content
        and model_rule == "T-CONTENT"
        and prod_rule is None
    ):
        return "BATCH_SERIES_CLOSED"
    return None


def _compare(s: Any, prod: Prod, live: bool, conflict: bool, stats: Counter[str]) -> None:
    if not s.created:  # an event before creation (a crash of the creating process): nothing exists on either side
        assert not prod.key or not (prod.root / prod.key / "journal.jsonl").exists()
        return
    lc = C.lam(s)
    if lc == "CORRUPT":
        with pytest.raises(CorruptInvestigation):
            InvestigationMemory.open(prod.root, prod.key, writable=False)
        stats["compared_states"] += 1
        return
    f = prod.ctl.view if prod.ctl is not None else _read_fold(prod)
    assert f.lifecycle() == lc, (f.lifecycle(), lc)
    for i, st in enumerate(s.steps):
        sv = workflow.step_view(f, STEPS[i])
        assert sv.state == st.status, (STEPS[i], sv.state, st.status)
        if st.status != "succeeded":  # the model forgets succeeded steps' counters (quotient R-1)
            assert (sv.phi, sv.f, sv.attempts) == (st.phi, st.f, st.attempts), STEPS[i]
        stats["max_phi"] = max(stats["max_phi"], sv.phi)
        stats["max_f"] = max(stats["max_f"], sv.f)
        stats["max_attempts"] = max(stats["max_attempts"], sv.attempts)
    assert bool(f.open_questions()) == s.question
    out = workflow.outcome(f)
    if lc in ("COMPLETED", "NEEDS_RESOLUTION"):
        assert out == ("partial" if s.question else "completed")
    stats["compared_states"] += 1


def _read_fold(prod: Prod) -> Any:
    with InvestigationMemory.open(prod.root, prod.key, writable=False) as mem:
        return copy.deepcopy(mem.view)


def _compare_next(s: Any, edges: list[Any], prod: Prod, stats: Counter[str]) -> None:
    """The model's controller move from a live, recovered state against production's ``next_action``."""
    if prod.ctl is None or not s.alive or s.fresh or C.running_index(s) is not None or C.lam(s) in C.TERMINAL:
        return
    na = workflow.next_action(prod.ctl.view, prod.clock.t)
    moves = [(label, rec) for label, rec, _ in edges if label.startswith(("ctl:", "proc:exit_blocked"))]
    assert len(moves) == 1, moves
    label, rec = moves[0]
    if label == "ctl:start":
        i = rec[1]
        assert (na.action, na.step, na.attempt) == ("start", STEPS[i], s.steps[i].attempts + 1)
    else:
        assert label == "proc:exit_blocked" and na.action == "wait"
    stats["compared_next_actions"] += 1


def _compare_legal(s: Any, prod: Prod, live: bool, conflict: bool, stats: Counter[str], found: Counter[str]) -> None:
    if prod.ctl is None or C.lam(s) == "CORRUPT":
        return
    for rec in C.record_alphabet():
        m = C.legal(rec, s, live)
        p = prod.legal(rec, s.orphan)
        stats["proposals"] += 1
        if (m is None) == (p is None) and (m is None or m == p):
            stats["agree"] += 1
            continue
        cat = classify(rec, s, m, p, conflict)
        assert cat is not None, {"record": rec, "model": m, "production": p, "state": s}
        found[cat] += 1


def _step(prod: Prod, label: str, rec: Any, s: Any, t: Any) -> None:
    """Perform the model event ``label`` on the production side."""
    if label == "ctl:create":
        prod.create()
        prod.open()
    elif label == "run:open":
        prod.open()
    elif label in ("env:crash", "proc:exit", "proc:exit_blocked"):
        prod.close()
    elif label == "env:corrupt":
        prod.corrupt_journal()
    elif label == "env:input_changed":
        prod.env.values["config"]["changed"] = True
    elif label == "env:time_reaches_not_before":
        f = prod.ctl.view if prod.ctl is not None else _read_fold(prod)
        nb = workflow.step_view(f, "ACQUIRE").not_before
        assert nb is not None
        prod.clock.t = max(prod.clock.t, nb)
    elif label == "run:busy_noop":
        before = (prod.root / prod.key / "journal.jsonl").read_bytes()
        with pytest.raises(Busy):
            InvestigationMemory.open(prod.root, prod.key, writable=False)
        assert (prod.root / prod.key / "journal.jsonl").read_bytes() == before
    elif label == "run:terminal_noop":
        before = (prod.root / prod.key / "journal.jsonl").read_bytes()
        res = run_investigation(prod.root, prod.key, Plan().adapters(), prod.env, clock=prod.clock)
        assert res.status == C.lam(s)
        assert (prod.root / prod.key / "journal.jsonl").read_bytes() == before
    elif label == "ctl:recover":
        prod.ctl.recover()
    elif label == "ctl:stale":
        assert prod.ctl.check_stale() is not None
    elif label == "ctl:recovered":
        if any(st.status == "succeeded" for st in s.steps):
            assert prod.ctl.stale_payload(prod.ctl.current_digests()) is None
    elif label == "ctl:start":
        prod.start(STEPS[rec[1]])
    elif label == "ctl:write_content":
        prod.write_content()
    elif label == "env:step_succeeds":
        prod.succeed()
    elif label in ("env:step_fails_terminal", "env:step_fails_retryable"):
        prod.fail(rec[2])
    elif label == "env:stage03_defers":
        if rec[0] == "step_deferred":
            prod.defer()
        else:
            prod.fail("deferral_budget")
    else:
        raise AssertionError(label)


# Event weights: terminal outcomes rarely, so walks reach later steps, retries, deferrals and recoveries.
WEIGHT = {
    "env:corrupt": 0.005,
    "env:crash": 0.08,
    "env:input_changed": 0.02,
    "run:busy_noop": 0.02,
    "env:step_fails_terminal": 0.03,
}


# Directed toward the budgets (review F6): ACQUIRE defers and fails retryably far more often than it succeeds, so walks
# reach f = F_max, the seventh deferral, phi = A_max - 1 and the ninth attempt, and both sides are compared there.
BOUNDARY_WEIGHT = {
    **WEIGHT,
    "env:stage03_defers": 12.0,
    "env:step_fails_retryable": 3.0,
    "env:step_succeeds": 0.3,
    "env:crash": 0.02,
    "env:input_changed": 0.0,
}


def walk(
    base: Path,
    live: bool,
    conflict: bool,
    seed: int,
    stats: Counter[str],
    found: Counter[str],
    weight: dict[str, float] | None = None,
) -> list[str]:
    weight = WEIGHT if weight is None else weight
    rnd = random.Random(seed)
    prod = Prod(base, live, conflict)
    s = C.State()
    labels: list[str] = []
    try:
        for _ in range(600):
            edges = C.successors(s, live, conflict)
            if prod.ctl is not None:
                _compare_next(s, edges, prod, stats)
            # Input changes only after a commit (module docstring); terminal no-ops end the walk.
            committed = any(st.status == "succeeded" for st in s.steps)
            choices = [e for e in edges if not (e[0] == "env:input_changed" and not committed)]
            if C.lam(s) in C.TERMINAL and s.created:
                stats["end:" + str(C.lam(s))] += 1
                ends = [e for e in choices if e[0] in ("run:terminal_noop", "proc:exit")]
                label, rec, t = ends[0]
                _step(prod, label, rec, s, t)
                labels.append(label)
                if label == "proc:exit":
                    s = t
                    edges = C.successors(s, live, conflict)
                    label, rec, t = next(e for e in edges if e[0] == "run:terminal_noop")
                    _step(prod, label, rec, s, t)
                    labels.append(label)
                break
            weights = [weight.get(e[0], 1.0) for e in choices]
            label, rec, t = rnd.choices(choices, weights)[0]
            _step(prod, label, rec, s, t)
            labels.append(label)
            s = t
            _compare(s, prod, live, conflict, stats)
            _compare_legal(s, prod, live, conflict, stats, found)
        else:
            raise AssertionError("walk did not terminate")
    finally:
        prod.close()
    stats["events"] += len(labels)
    return labels


SCENARIOS = [(False, False), (False, True), (True, False), (True, True)]
WALKS = 10


@pytest.mark.parametrize(
    ("live", "conflict"), SCENARIOS, ids=["retained", "retained-conflict", "live", "live-conflict"]
)
def test_differential_random_walks(tmp_path: Path, live: bool, conflict: bool) -> None:
    stats: Counter[str] = Counter()
    found: Counter[str] = Counter()
    ends: Counter[str] = Counter()
    labels: Counter[str] = Counter()
    for seed in range(WALKS):
        base = tmp_path / str(seed)
        base.mkdir()
        walked = walk(base, live, conflict, 1000 * (2 * live + conflict) + seed, stats, found)
        labels.update(walked)
        ends[walked[-1]] += 1
    assert stats["compared_states"] > 0 and stats["proposals"] > 0
    assert set(found) <= {"W6_STRICTER", "SUCCESS_FLAG", "BATCH_SERIES_CLOSED"}
    print({"scenario": (live, conflict), **stats, "classified": dict(found), "labels": dict(labels)})


def test_differential_at_the_budget_boundaries(tmp_path: Path) -> None:
    """Live capture walks directed at the retry and deferral budgets: the model and production are compared in states
    with f = F_max and nine ACQUIRE attempts, and on the records that end the step there."""
    stats: Counter[str] = Counter()
    found: Counter[str] = Counter()
    labels: Counter[str] = Counter()
    for seed in range(WALKS):
        base = tmp_path / str(seed)
        base.mkdir()
        labels.update(walk(base, True, False, 9000 + seed, stats, found, BOUNDARY_WEIGHT))
    assert set(found) <= {"W6_STRICTER", "SUCCESS_FLAG", "BATCH_SERIES_CLOSED"}
    assert stats["max_f"] == workflow.F_MAX and stats["max_phi"] == workflow.A_MAX - 1
    assert stats["max_attempts"] == workflow.A_MAX + workflow.F_MAX
    print({"scenario": "budget boundaries", **stats, "classified": dict(found), "labels": dict(labels)})


def test_input_change_before_any_commit(tmp_path: Path) -> None:
    """Classified reference-model over-approximation (module docstring), shown on both sides."""
    # Model: env_changed before any commit, then VALIDATE commits; the next open is STALE.
    s = C.apply(C.State(), ("investigation_created", -1, None))
    s = C.replace(s, env_changed=True, fresh=False)
    s = C.apply(s, ("step_started", 0, "next"))
    s = C.apply(s, ("step_succeeded", 0, False))
    s = C.replace(s, alive=False)
    s = C.replace(s, alive=True, fresh=True)
    assert [lab for lab, _, _ in C.successors(s, False, False) if lab.startswith("ctl:")] == ["ctl:stale"]
    # Production: VALIDATE was keyed with the changed identity, so no committed key differs (S-10.1).
    prod = Prod(tmp_path, False, False)
    prod.create()
    prod.open()
    prod.env.values["config"]["changed"] = True
    prod.start("VALIDATE")
    prod.succeed()
    prod.close()
    prod.open()
    try:
        assert prod.ctl.check_stale() is None and prod.ctl.view.lifecycle() == "RUNNING"
    finally:
        prod.close()


def test_w6_stricter_is_the_only_orphan_discrepancy(tmp_path: Path) -> None:
    """A crash with an open attempt, then a fresh open: compare every record in the orphan state."""
    prod = Prod(tmp_path, True, False)
    prod.create()
    prod.open()
    s = C.apply(C.State(), ("investigation_created", -1, None))
    s = C.replace(s, fresh=False)
    for rec in (("step_started", 0, "next"), ("step_succeeded", 0, False), ("step_started", 1, "next")):
        s = C.apply(s, rec, True)
    prod.start("VALIDATE")
    prod.succeed()
    prod.start("ACQUIRE")
    prod.close()
    prod.open()
    s = C.replace(s, orphan=True, fresh=True)
    found: Counter[str] = Counter()
    stats: Counter[str] = Counter()
    try:
        _compare_legal(s, prod, True, False, stats, found)
    finally:
        prod.close()
    # Model-legal continuations of the dead attempt: content, terminal and retryable failure, deferral. (Success needs
    # content first and the deferral budget needs six deferrals, so the model refuses those too.)
    assert found == {"W6_STRICTER": 4}


def test_batch_series_closed_is_the_batch_sequence_rule(tmp_path: Path) -> None:
    """``BATCH_SERIES_CLOSED`` is exactly S-8.8 BATCH_SEQUENCE: before an attempt's content both sides accept a batch
    record; after it, production refuses a further batch by that rule and no other."""
    prod = Prod(tmp_path, False, False)
    prod.create()
    prod.open()
    try:
        for step in ("VALIDATE", "ACQUIRE", "EXTRACT"):
            prod.start(step)
            if step != "VALIDATE":
                prod.write_content()
            prod.succeed()
        i = STEPS.index("NORMALIZE")
        prod.start("NORMALIZE")
        assert prod.legal(("content", i, None), False) == "T-CONTENT"
        prod.write_content()
        assert prod.legal(("content", i, None), False) is None
        proposal = prod._proposal("content", i, None)
        assert proposal is not None
        assert workflow.guard(proposal, prod.ctl.view, orphan=False) == "T-CONTENT"
        with pytest.raises(InvariantViolation) as exc:
            prod.ctl.view.check(prod._full(proposal))
        assert (exc.value.invariant, exc.value.code) == ("S-8.8", "BATCH_SEQUENCE")
    finally:
        prod.close()
