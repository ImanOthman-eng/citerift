"""The Investigation Workflow Controller (SPEC 9, 10.1, 10.3; MM 8 to 10; Stage 04 Step 7).

The controller runs the fixed plan ``plan-1`` over an open ``InvestigationMemory``. Its whole state is the fold of the
journal (W-1): every decision is taken by ``workflow.next_action`` and ``workflow.guard`` from ``memory.view`` and the
time. The only thing it keeps in the instance is the set of attempts this instance opened, which tells an attempt
of a process that died (closed on resume, W-6) from its own; losing it can only make an attempt look orphaned, never
make a refused record legal.

Flow of one step (S-9.1): next action → ``step_started`` → adapter (fake in Step 7) → the controller validates the
result → blobs published → content records appended → ``step_succeeded``, ``step_failed`` or ``step_deferred``. Every
record passes ``workflow.guard`` and then Memory's own checks before it is written. The controller never sleeps: a
step that may restart only later leaves the run with action ``wait`` (SPEC 9.2).

Adapter defects (owner decision D-049). An adapter that raises an ordinary exception, returns something other than a
``StepResult``, supplies content that the guard or Memory refuses, violates the protocol or returns contradictory
metadata ends its attempt at once with the terminal, non-retryable code ``ADAPTER_INCONSISTENT``, which every step has.
Nothing is left open for W-6 or the retry budget. A genuine domain failure that the adapter reports (``Failed``) keeps
its own code, and a size limit keeps ``STORAGE_ERROR`` (SPEC 10.2). Only a process death or a ``BaseException`` leaves
an attempt open.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from citerift.investigation import batches, faults, ids, workflow
from citerift.investigation.adapters import (
    ContentRecord,
    Deferred,
    Failed,
    StepAdapter,
    StepRequest,
    Succeeded,
)
from citerift.investigation.errors import (
    AppendRefused,
    BlobError,
    Busy,
    CanonError,
    CorruptInvestigation,
    InvestigationMemoryError,
    StorageError,
)
from citerift.investigation.fold import STEPS, Folder
from citerift.investigation.memory import InvestigationMemory
from citerift.investigation.workflow import (
    A_MAX,
    DEFERRAL_BUDGET_EXHAUSTED,
    F_MAX,
    INTERRUPTED_REASON,
    RETRY_BUDGET_EXHAUSTED,
    WALL_CLOCK,
    NextAction,
    WorkflowCorrupt,
    WorkflowRefused,
    WorkflowState,
)
from citerift.wiki.issues import CATALOG as WIKI_CODES

Clock = Callable[[], datetime]
IdentitySource = Callable[[Mapping[str, Any] | None], Mapping[str, Any]]  # bound root identity -> components

# Controller boundaries for fault injection (owner Step 7 item 10). "During the adapter" is the adapter's own code.
POINTS = (
    "controller.before_start",  # next action decided, step_started not written
    "controller.after_start",  # step_started durable, adapter not called
    "controller.after_adapter",  # adapter returned, nothing of its result written
    "controller.after_blobs",  # the result's blobs published, no content record written
    "controller.after_batch",  # one evidence_batch_recorded durable (context: index), D-053
    "controller.after_entry_batch",  # one D-055 batch record durable (context: kind, index)
    "controller.after_content",  # one content record durable (context: index), terminal record not written
    "controller.after_terminal",  # the attempt's terminal record durable, before the next start
)

# D-049: the terminal code of a defective adapter result, the same in every step.
ADAPTER_INCONSISTENT = "ADAPTER_INCONSISTENT"
DEFECT_CODE: dict[str, tuple[str, str | None]] = dict.fromkeys(STEPS, (ADAPTER_INCONSISTENT, None))
CONTROLLER_CODES = frozenset({RETRY_BUDGET_EXHAUSTED, DEFERRAL_BUDGET_EXHAUSTED})
# SPEC 9.3: ACQUIRE ends with a Stage 03 code or one of these. The record schema cannot enumerate the Stage 03 codes,
# so the controller checks them (D-049: any other code is an illegal result, ADAPTER_INCONSISTENT).
ACQUIRE_STAGE04_CODES = frozenset(
    {"ROOT_IDENTITY_MISMATCH", WALL_CLOCK, ADAPTER_INCONSISTENT, "STORAGE_ERROR", "CANON_INVALID"}
)
CAPACITY = frozenset({"RECORD_TOO_LARGE", "JOURNAL_TOO_LARGE", "BLOB_TOO_LARGE"})  # Memory's size refusals
MAX_DETAIL = 4096
# Upper bound on the actions of one run: every attempt the budgets allow, plus recovery and staleness.
MAX_ACTIONS = (len(STEPS) - 1) * A_MAX + (A_MAX + F_MAX) + 2


class StorageExhausted(InvestigationMemoryError):
    """A size limit refused an execution record (start, close, interruption or staleness), so the controller cannot
    record the outcome. Nothing is written, an open attempt stays open, and every later run stops here too until the
    limit is resolved (Step 7 resource-bound review, owner decision RB-2). Never reported as any lifecycle."""

    def __init__(self, kind: str, step: str | None, limit: str, detail: str) -> None:
        super().__init__("STORAGE_EXHAUSTED", f"{kind} of {step or 'the investigation'} refused by {limit}: {detail}")
        self.kind = kind
        self.step = step
        self.limit = limit


EXECUTION_KINDS = frozenset({"step_started", "step_failed", "step_deferred", "step_interrupted", "stale_detected"})


class _Defect(Exception):
    """Internal: a refused adapter result, with the reason recorded as the failure detail."""

    def __init__(self, detail: str, code: tuple[str, str | None] | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.code = code


class MonotoneClock:
    """A clock that never goes back. Shared by Memory and the controller, so a record's ``at`` (read by Memory after
    the controller checked the time) is never earlier than the time the guard checked (T-RESTART, ``not_before``)."""

    def __init__(self, source: Clock) -> None:
        self._source = source
        self._last: datetime | None = None

    def __call__(self) -> datetime:
        now = self._source()
        if self._last is not None and now < self._last:
            now = self._last
        self._last = now
        return now


def _fmt(at: datetime) -> str:
    return at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _detail(text: str) -> str:
    return text[:MAX_DETAIL]


class WorkflowController:
    """Runs the plan over one writable ``InvestigationMemory`` opened with the same ``MonotoneClock``."""

    def __init__(
        self,
        memory: InvestigationMemory,
        adapters: Mapping[str, StepAdapter],
        identities: IdentitySource,
        clock: MonotoneClock,
    ) -> None:
        if not memory.writable:
            raise InvestigationMemoryError("READ_ONLY", "the controller needs a writable investigation")
        if getattr(memory, "_clock", None) is not clock:
            raise InvestigationMemoryError("CLOCK_NOT_SHARED", "Memory and the controller must share one clock")
        missing = [s for s in STEPS if s not in adapters]
        if missing:
            raise InvestigationMemoryError("ADAPTER_MISSING", f"no adapter for {missing}")
        workflow.check_journal(memory.view)  # W-2 to W-8 over the stored journal; WorkflowCorrupt otherwise
        self._mem = memory
        self._adapters = dict(adapters)
        self._identities = identities
        self._clock = clock
        self._own: set[tuple[str, int]] = set()
        self._broken = False

    # Reading -------------------------------------------------------------------------------------------------------

    @property
    def view(self) -> Folder:
        return self._mem.view

    def state(self) -> WorkflowState:
        return workflow.derive(self.view, self._clock())

    def explain(self) -> dict[str, Any]:
        return workflow.explain(self.view, self._clock())

    # Writing -------------------------------------------------------------------------------------------------------

    def _usable(self) -> None:
        if self._broken:
            raise InvestigationMemoryError("CONTROLLER_UNUSABLE", "an earlier action did not complete; reopen")

    def _append(
        self, kind: str, payload: dict[str, Any], step: str | None, attempt: int | None, *, orphan: bool = False
    ) -> dict[str, Any]:
        """Guard (MM 8), then Memory's append (M-1 to M-14). ``at`` of the proposal is a lower bound of the ``at``
        Memory writes, because both read the same monotone clock and Memory never goes below the last record."""
        f = self.view
        now = self._clock()
        if f.last_at is not None and now < f.last_at:
            now = f.last_at
        proposal = {"kind": kind, "step": step, "attempt": attempt, "payload": payload, "at": _fmt(now)}
        workflow.guard(proposal, f, orphan=orphan)
        try:
            return self._mem.append(kind, payload, step=step, attempt=attempt)
        except StorageError:  # Memory refuses every later write until reopened; the attempt stays open (W-6)
            self._broken = True
            raise
        except AppendRefused as exc:
            if kind in EXECUTION_KINDS and exc.code in CAPACITY:  # the outcome itself cannot be recorded
                self._broken = True
                raise StorageExhausted(kind, step, exc.code, str(exc)) from exc
            raise

    # Recovery and staleness (SPEC 10.1, 10.3) ----------------------------------------------------------------------

    def recover(self) -> dict[str, Any] | None:
        """W-6: close an attempt that a process that died left open, before anything else is appended."""
        self._usable()
        f = self.view
        if f.open is None:
            return None
        step, number = f.open.step, f.open.number
        if (step, number) in self._own:
            raise WorkflowRefused("W-6", f"{step} attempt {number} of this controller is still open", len(f.records))
        key = f.records[f.open.start_seq]["payload"]["step_key"]
        sv = workflow.step_view(f, step)
        if sv.phi + 1 < A_MAX:
            return self._append("step_interrupted", {"step_key": key}, step, number, orphan=True)
        payload = self._failure_payload(
            step, key, RETRY_BUDGET_EXHAUSTED, False, INTERRUPTED_REASON, "the attempt's process died", None, None
        )
        return self._append("step_failed", payload, step, number, orphan=True)

    def current_digests(self) -> dict[str, str]:
        """The input identity vector now (SPEC 10.3). The environment sees the bound root's identity only, never its
        display title, so no key depends on a title (owner Step 7 item 16)."""
        root = self.view.root
        values = self._identities(copy.deepcopy(root["subject"]["identity"]) if root is not None else None)
        return workflow.identity_digests(values)

    def stale_payload(self, digests: Mapping[str, str]) -> dict[str, Any] | None:
        """S-10.1: recompute every committed step's key; the ``stale_detected`` payload if one differs, else None."""
        f = self.view
        committed = [s for s in STEPS if f.step_state(s) == "succeeded"]
        changed_steps = [s for s in committed if workflow.step_key(f, s, digests) != self._recorded_key(s)]
        if not changed_steps:
            return None
        # Per component, the digest a committed step recorded; where steps recorded different digests (an identity
        # changed between steps of one process), the first that differs from now, so ``changed`` names it.
        recorded: dict[str, str] = {}
        for s in committed:
            for name, digest in self._manifest(s)["identities"].items():
                if name not in recorded or (recorded[name] == digests[name] and digest != digests[name]):
                    recorded[name] = digest
        changed = sorted(n for n, d in recorded.items() if digests[n] != d)
        if not changed:
            raise WorkflowCorrupt(WorkflowRefused("S-10.1", f"step keys of {changed_steps} differ, no identity does"))
        return {"changed": changed, "recorded": recorded, "current": dict(digests)}

    def check_stale(self) -> dict[str, Any] | None:
        self._usable()
        lc = self.view.lifecycle()
        if lc not in ("RUNNING", "BLOCKED") or self.view.open is not None:
            return None
        payload = self.stale_payload(self.current_digests())
        if payload is None:
            return None
        return self._append("stale_detected", payload, None, None)

    def _succeeded_record(self, step: str) -> dict[str, Any]:
        ends = [a.end_seq for a in self.view.attempts[step] if a.end_kind == "step_succeeded"]
        if not ends or ends[-1] is None:
            raise WorkflowRefused("M-14", f"{step} has not succeeded", len(self.view.records))
        return self.view.records[ends[-1]]

    def _recorded_key(self, step: str) -> str:
        return str(self._succeeded_record(step)["payload"]["step_key"])

    def _manifest(self, step: str) -> dict[str, Any]:
        """The manifest of a committed step (its last output), checked against the recorded step key."""
        rec = self._succeeded_record(step)
        outputs = rec["payload"]["outputs"]
        bad = WorkflowCorrupt(WorkflowRefused("S-9.3", f"{step} has no valid step manifest", rec["seq"]))
        if not outputs:
            raise bad
        try:
            m = json.loads(self._mem.blobs.get(outputs[-1]))
        except (InvestigationMemoryError, ValueError) as exc:
            raise bad from exc
        f = self.view
        c = workflow.created(f)
        try:
            ok = (
                m["manifest"] == workflow.MANIFEST_TAG
                and m["step"] == step
                and m["step_key"] == rec["payload"]["step_key"]
                and m["dependencies"] == workflow.dependencies(f, step)
                and sorted(m["identities"]) == sorted(workflow.STEP_IDENTITIES[step])
                and ids.step_key(
                    step,
                    c["request"]["config"]["plan_version"],
                    m["dependencies"],
                    m["identities"],
                    c["config_digest"],
                )
                == m["step_key"]
            )
        except (KeyError, TypeError) as exc:
            raise bad from exc
        if not ok:
            raise bad
        return dict(m)

    # Running -------------------------------------------------------------------------------------------------------

    def run(self) -> WorkflowState:
        """Resume and run until the lifecycle is terminal or the next step must wait (S-9.4). Never sleeps."""
        self._usable()
        self.recover()
        self.check_stale()
        for _ in range(MAX_ACTIONS):
            action = workflow.next_action(self.view, self._clock())
            if action.action in ("terminal", "wait"):
                return self.state()
            self.step()
        raise WorkflowRefused("W-4", f"more than {MAX_ACTIONS} actions in one run", len(self.view.records))

    def step(self) -> NextAction:
        """Perform the next legal action once; returns the action taken (or ``terminal`` / ``wait``)."""
        self._usable()
        action = workflow.next_action(self.view, self._clock())
        if action.action == "recover":
            self.recover()
        elif action.action == "start" and action.step is not None and action.attempt is not None:
            self._attempt(action.step, action.attempt)
        return action

    def _attempt(self, step: str, attempt: int) -> None:
        digests = self.current_digests()
        if self.stale_payload(digests) is not None:  # an identity changed during the run: stop, reuse nothing
            self.check_stale()
            return
        f = self.view
        key = workflow.step_key(f, step, digests)
        faults.point("controller.before_start", step=step, attempt=attempt)
        self._append("step_started", {"step_key": key}, step, attempt)
        self._own.add((step, attempt))
        faults.point("controller.after_start", step=step, attempt=attempt)
        request = self._request(step, attempt, key)
        try:
            result = self._adapters[step](request)
        except Exception as exc:
            self._defect(step, attempt, key, _Defect(f"adapter raised {type(exc).__name__}: {exc}"))
            return
        except BaseException:
            self._broken = True  # the attempt stays open; only a resume (W-6) closes it
            raise
        faults.point("controller.after_adapter", step=step, attempt=attempt)
        try:
            if isinstance(result, Succeeded):
                self._succeed(step, attempt, key, digests, result)
            elif isinstance(result, Failed):
                self._fail(step, attempt, key, result)
            elif isinstance(result, Deferred):
                self._defer(step, attempt, key, result)
            else:
                raise _Defect(f"adapter returned {type(result).__name__}, not a StepResult")
        except _Defect as defect:
            self._defect(step, attempt, key, defect)
            return
        faults.point("controller.after_terminal", step=step, attempt=attempt)

    def _request(self, step: str, attempt: int, key: str) -> StepRequest:
        f = self.view
        request = workflow.created(f)["request"]
        inputs = {
            s: tuple(self._succeeded_record(s)["payload"]["outputs"]) for s in STEPS if f.step_state(s) == "succeeded"
        }
        blobs = self._mem.blobs

        def read_blob(digest: str) -> Any:
            return json.loads(blobs.get(digest))

        def read_bytes(digest: str) -> bytes:
            return blobs.get(digest)

        return StepRequest(
            step=step,
            attempt=attempt,
            step_key=key,
            live=workflow.is_live(f),
            request=copy.deepcopy(request),
            request_key=copy.deepcopy(workflow.created(f)["request_key"]),
            root=copy.deepcopy(f.root),
            inputs=inputs,
            committed=tuple(copy.deepcopy(f.committed_content())),
            stored=tuple(copy.deepcopy(f.committed_records())),
            content_digest=f.content_digest(),
            read_blob=read_blob,
            read_bytes=read_bytes,
            now=self._clock(),
            investigation={k: workflow.created(f)[k] for k in ("investigation_key", "investigation_id")},
        )

    # Results -------------------------------------------------------------------------------------------------------

    def _succeed(self, step: str, attempt: int, key: str, digests: Mapping[str, str], r: Succeeded) -> None:
        records = _content(step, r)
        items = [p for kind, p in records if kind == workflow.EVIDENCE]
        records = [(kind, p) for kind, p in records if kind != workflow.EVIDENCE]
        try:  # D-053: the attempt's evidence in its canonical batches (SPEC 8.8)
            evidence = batches.evidence_batches(items, lambda ref: self.view.evidence_batch(ref) is not None)
        except (batches.BatchError, KeyError, TypeError, CanonError) as exc:
            raise _Defect(f"the evidence cannot be batched: {exc}") from exc
        entry_kind, entries, records = _entries(step, records)
        try:  # D-055: the attempt's lookup observations or candidate results in canonical batches (SPEC 8.9)
            if entry_kind == "lookup_batch_recorded":
                parts = batches.ordered_parts(entries, batches.lookup_key, batches.lookup_batch)
            elif entry_kind == "candidate_result_batch_recorded":
                parts = batches.ordered_parts(entries, batches.candidate_key, batches.candidate_batch)
            else:
                parts = []
        except (KeyError, TypeError, CanonError) as exc:
            raise _Defect(f"the {step} results cannot be batched: {exc}") from exc
        if (r.root is not None) != (step == "ACQUIRE"):
            raise _Defect("only ACQUIRE binds a root, and it must")
        if not isinstance(r.outputs, tuple) or not all(isinstance(d, str) for d in r.outputs):
            raise _Defect("outputs is not a tuple of digests")
        if not isinstance(r.raw_blobs, tuple) or not all(isinstance(b, bytes) for b in r.raw_blobs):
            raise _Defect("raw_blobs is not a tuple of bytes")
        if r.raw_blobs and step != "ACQUIRE":
            raise _Defect("only ACQUIRE retains raw upstream bytes (IF-7)")
        try:
            for data in r.raw_blobs:  # the retained bytes first: the manifest that names them follows (M-3)
                self._mem.put_raw_blob(data)
            for blob in r.blobs:
                self._mem.put_blob(blob)
            batch_digests = [self._mem.put_blob(b) for b in evidence]
            part_digests = [self._mem.put_blob(b) for b in parts]
        except CanonError as exc:
            raise _Defect(f"a blob is not canonical JSON: {exc}") from exc
        except BlobError as exc:
            if exc.code in CAPACITY:
                raise _Defect(str(exc), ("STORAGE_ERROR", exc.code)) from exc
            raise
        except StorageError as exc:  # SPEC 10.2: a failed blob write (full disk) ends the attempt if a record fits
            raise _Defect(str(exc), ("STORAGE_ERROR", None)) from exc
        faults.point("controller.after_blobs", step=step, attempt=attempt)
        for d in r.outputs:
            if not self._mem.blobs.exists(d):
                raise _Defect(f"output {d[:80]!r} is not a published blob")
        for index, payload in enumerate(batches.batch_records(batch_digests, evidence)):
            self._content_append("evidence_batch_recorded", payload, step, attempt)
            faults.point("controller.after_batch", step=step, attempt=attempt, index=index)
        for index, payload in enumerate(batches.entry_records(part_digests, parts)):
            self._content_append(entry_kind, payload, step, attempt)  # type: ignore[arg-type]
            faults.point("controller.after_entry_batch", step=step, attempt=attempt, kind=entry_kind, index=index)
        for index, (kind, payload) in enumerate(records):
            self._content_append(kind, payload, step, attempt)
            faults.point("controller.after_content", step=step, attempt=attempt, index=index)
        f = self.view
        try:
            manifest = self._mem.put_blob(workflow.manifest(f, step, key, digests))
        except StorageError as exc:
            raise _Defect(str(exc), ("STORAGE_ERROR", None)) from exc
        if manifest in r.outputs:  # the manifest is the controller's, and the last output (S-9.3)
            raise _Defect("an adapter output is the step manifest")
        outputs = [*dict.fromkeys(r.outputs), manifest]
        root = copy.deepcopy(dict(r.root)) if r.root is not None else None
        payload = {"step_key": key, "outputs": outputs, "root": root}
        try:
            self._append("step_succeeded", payload, step, attempt)
        except WorkflowRefused as exc:  # W-7, W-8, CH-1 over what the adapter supplied
            raise _Defect(str(exc)) from exc
        except AppendRefused as exc:
            if exc.invariant == "M-9":
                raise _Defect(str(exc), ("ROOT_IDENTITY_MISMATCH", None)) from exc
            raise _Defect(str(exc), _capacity_code(exc)) from exc

    def _content_append(self, kind: str, payload: dict[str, Any], step: str, attempt: int) -> None:
        try:
            self._append(kind, payload, step, attempt)
        except WorkflowRefused as exc:
            raise _Defect(f"{kind} refused: {exc}") from exc
        except AppendRefused as exc:
            raise _Defect(f"{kind} refused: {exc}", _capacity_code(exc)) from exc
        except CanonError as exc:  # not in the canonical data model (a float, a non-string key, ...)
            raise _Defect(f"{kind} refused: {exc}") from exc

    def _fail(self, step: str, attempt: int, key: str, r: Failed) -> None:
        live = workflow.is_live(self.view)
        sv = workflow.step_view(self.view, step)
        if not isinstance(r.code, str) or r.code in CONTROLLER_CODES:
            raise _Defect(f"adapter failure code {r.code!r} is not an engine code")
        if step == "ACQUIRE" and r.code not in WIKI_CODES and r.code not in ACQUIRE_STAGE04_CODES:
            raise _Defect(
                f"ACQUIRE failure code {r.code[:80]!r} is neither a Stage 03 code nor a Stage 04 ACQUIRE code"
            )
        if r.not_before is not None and (step != "ACQUIRE" or not _aware(r.not_before)):
            raise _Defect("not_before belongs to ACQUIRE only and must be a UTC instant")
        if (r.wall_clock is not None) != (r.code == WALL_CLOCK) or (r.code == WALL_CLOCK and not live):
            raise _Defect("wall_clock goes with ACQUIRE_WALL_CLOCK_EXCEEDED of a live capture, and only with it")
        if not r.retry_after_known and r.code != WALL_CLOCK:
            raise _Defect("only a killed live capture cannot tell whether it observed a Retry-After instant")
        if r.evidence is not None and step != "EXTRACT":
            raise _Defect("only EXTRACT keeps a failed upstream document as evidence")
        wall = {"t_acq_ms": r.wall_clock.t_acq_ms, "elapsed_ms": r.wall_clock.elapsed_ms} if r.wall_clock else None
        code, reason, detail, retryable = r.code, r.reason, r.detail, False
        if workflow.retryable_code(step, code, live) and r.retry_after_known:
            if sv.phi + 1 < A_MAX:
                retryable = True
            else:  # W-4: the budget is spent; the original code becomes the reason
                code, reason, wall = RETRY_BUDGET_EXHAUSTED, r.code, None
                detail = f"{r.code}: {r.detail or ''}"[:MAX_DETAIL]
        if r.evidence is not None:
            detail = self._keep_failed_document(step, attempt, r.evidence, detail)
        payload = self._failure_payload(step, key, code, retryable, reason, detail, r.not_before, wall)
        try:
            self._append("step_failed", payload, step, attempt)
        except (WorkflowRefused, AppendRefused) as exc:
            raise _Defect(f"failure {r.code} refused: {exc}") from exc

    def _keep_failed_document(self, step: str, attempt: int, document: Any, detail: str | None) -> str | None:
        """D-050: the failed Stage 03 document stays in the journal as an observation of the failing attempt (never
        committed). Where it cannot be kept safely (not canonical JSON, or a storage limit), the failure is still
        recorded, and its detail says the document was not kept."""
        try:
            blob = self._mem.put_blob(document)
        except (CanonError, BlobError, StorageError) as exc:
            return _detail(f"{detail or ''} [failed document not kept: {exc}]".strip())
        obs = {
            "obs_kind": "extraction",
            "blob": blob,
            "source_ref": {"engine": "citerift.wiki", "operation": "extract_bundle", "locator": None},
        }
        self._content_append("observation_recorded", obs, step, attempt)
        return detail

    def _defer(self, step: str, attempt: int, key: str, r: Deferred) -> None:
        if not (step == "ACQUIRE" and workflow.is_live(self.view)):
            raise _Defect("only ACQUIRE of a live capture is deferred")
        if not _aware(r.not_before):
            raise _Defect("not_before must be a UTC instant")
        sv = workflow.step_view(self.view, step)
        nb = _fmt(r.not_before)
        if sv.f < F_MAX:
            payload = {"step_key": key, "code": "DEFERRED_RETRY_AFTER", "not_before": nb}
            try:
                self._append("step_deferred", payload, step, attempt)
            except (WorkflowRefused, AppendRefused) as exc:
                raise _Defect(f"deferral refused: {exc}") from exc
            return
        payload = self._failure_payload(
            step,
            key,
            DEFERRAL_BUDGET_EXHAUSTED,
            False,
            "DEFERRED_RETRY_AFTER",
            f"deferred a seventh time (F_max = {F_MAX})",
            r.not_before,
            None,
        )
        try:
            self._append("step_failed", payload, step, attempt)
        except (WorkflowRefused, AppendRefused) as exc:
            raise _Defect(f"deferral budget failure refused: {exc}") from exc

    def _defect(self, step: str, attempt: int, key: str, defect: _Defect) -> None:
        """D-049: a defective result ends the attempt terminally, never left open for W-6."""
        code = defect.code or DEFECT_CODE[step]
        payload = self._failure_payload(step, key, code[0], False, code[1], _detail(defect.detail), None, None)
        self._append("step_failed", payload, step, attempt)
        faults.point("controller.after_terminal", step=step, attempt=attempt)

    @staticmethod
    def _failure_payload(
        step: str,
        key: str,
        code: str,
        retryable: bool,
        reason: str | None,
        detail: str | None,
        not_before: datetime | None,
        wall_clock: dict[str, int] | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "step_key": key,
            "code": code,
            "retryable": retryable,
            "reason": reason,
            "detail": _detail(detail) if detail is not None else None,
            "wall_clock": wall_clock,
        }
        if step == "ACQUIRE":
            payload["not_before"] = _fmt(not_before) if not_before is not None else None
        return payload


def _capacity_code(exc: AppendRefused) -> tuple[str, str | None] | None:
    """A record refused for size is a storage limit, not an adapter defect: ``STORAGE_ERROR`` (SPEC 10.2), legal in
    every step, with the limit as the reason (Step 7 resource-bound review)."""
    return ("STORAGE_ERROR", exc.code) if exc.code in CAPACITY else None


def _aware(value: Any) -> bool:
    """An aware datetime that is a UTC instant the record schema can hold (a four-digit year)."""
    if not (isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None):
        return False
    try:
        return 1000 <= value.astimezone(UTC).year <= 9999
    except (OverflowError, ValueError):
        return False


def _content(step: str, r: Succeeded) -> list[tuple[str, dict[str, Any]]]:
    """The content records of a successful result, with DETECT's decisions and questions derived (SPEC 7.6, 7.7)."""
    if not isinstance(r.records, tuple) or not all(isinstance(c, ContentRecord) for c in r.records):
        raise _Defect("records is not a tuple of ContentRecord")
    allowed = workflow.ADAPTER_CONTENT_KINDS[step]
    out: list[tuple[str, dict[str, Any]]] = []
    for c in r.records:
        if c.kind not in allowed or not isinstance(c.payload, Mapping):
            raise _Defect(f"{step} may not supply {c.kind!r}")
        out.append((c.kind, copy.deepcopy(dict(c.payload))))
    if step != "DETECT":
        return out
    derived: list[tuple[str, dict[str, Any]]] = []
    for kind, p in out:
        if kind != "claim_recorded":
            continue
        cls, cid = p.get("class"), p.get("claim_id")
        disposition = workflow.DISPOSITION.get(cls) if isinstance(cls, str) else None
        if disposition is None or not isinstance(cid, str):
            raise _Defect(f"no decision-table disposition for class {cls!r}", ("DECISION_TABLE_GAP", None))
        derived.append(
            (
                "decision_recorded",
                {"decision_id": ids.decision_id(cid, disposition), "claim_id": cid, "disposition": disposition},
            )
        )
        if cls in workflow.CONFLICT:
            qkind = workflow.CONFLICT[cls]
            derived.append(
                ("question_opened", {"question_id": ids.question_id(cid, qkind), "claim_id": cid, "kind": qkind})
            )
    return out + derived


def _entries(
    step: str, records: list[tuple[str, dict[str, Any]]]
) -> tuple[str | None, list[dict[str, Any]], list[tuple[str, dict[str, Any]]]]:
    """D-055: split a result's logical records into the entries of the step's batches and the records written on
    their own. LOOKUP: every lookup observation reference is an entry (the observation stays its own blob). DETECT:
    each claim with the decision and the question derived for it is one entry (one candidate result)."""
    if step == "LOOKUP":
        entries = [p for kind, p in records if kind == "observation_recorded" and p.get("obs_kind") == "lookup"]
        rest = [(k, p) for k, p in records if not (k == "observation_recorded" and p.get("obs_kind") == "lookup")]
        return "lookup_batch_recorded", entries, rest
    if step != "DETECT":
        return None, [], records
    decisions: dict[Any, dict[str, Any]] = {}
    questions: dict[Any, dict[str, Any]] = {}
    for kind, p in records:
        if kind == "decision_recorded":
            decisions[p["claim_id"]] = p
        elif kind == "question_opened":
            questions[p["claim_id"]] = p
    entries = [
        {"claim": p, "decision": decisions[p.get("claim_id")], "question": questions.get(p.get("claim_id"))}
        for kind, p in records
        if kind == "claim_recorded"
    ]
    rest = [(k, p) for k, p in records if k not in ("claim_recorded", "decision_recorded", "question_opened")]
    return "candidate_result_batch_recorded", entries, rest


# Opening and running an investigation --------------------------------------------------------------------------------


@dataclass(frozen=True)
class RunResult:
    """What one run reports. ``status`` is the lifecycle, or ``INVESTIGATION_BUSY`` when another process holds the
    lock (nothing written). ``CORRUPT`` is computed, never recorded."""

    status: str
    state: WorkflowState | None
    explanation: dict[str, Any] | None
    detail: str = ""


def open_controller(
    memory_root: Path | str,
    key: str,
    adapters: Mapping[str, StepAdapter],
    identities: IdentitySource,
    *,
    clock: Clock | None = None,
    repository: Path | None = None,
) -> tuple[InvestigationMemory, WorkflowController]:
    """Open an investigation for the controller. The journal is checked read-only first (Memory and W-2 to W-8), so a
    workflow-corrupt journal is never repaired (D-044 order), then opened writable."""
    mono = MonotoneClock(clock or (lambda: datetime.now(UTC)))
    with InvestigationMemory.open(memory_root, key, writable=False, clock=mono, repository=repository) as ro:
        workflow.check_journal(ro.view)
    mem = InvestigationMemory.open(memory_root, key, writable=True, clock=mono, repository=repository)
    try:
        return mem, WorkflowController(mem, adapters, identities, mono)
    except BaseException:
        mem.close()
        raise


def run_investigation(
    memory_root: Path | str,
    key: str,
    adapters: Mapping[str, StepAdapter],
    identities: IdentitySource,
    *,
    clock: Clock | None = None,
    repository: Path | None = None,
) -> RunResult:
    """Open, resume and run one investigation (S-9.4); a busy, corrupt or terminal investigation is reported and not
    changed. ``StorageExhausted`` propagates after the investigation is closed (the attempt stays open for W-6)."""
    try:
        mem, ctl = open_controller(memory_root, key, adapters, identities, clock=clock, repository=repository)
    except Busy as exc:
        return RunResult("INVESTIGATION_BUSY", None, None, str(exc))
    except (CorruptInvestigation, WorkflowCorrupt) as exc:
        return RunResult("CORRUPT", None, None, str(exc))
    with mem:
        try:
            state = ctl.run()
        except WorkflowCorrupt as exc:  # found while running (a step manifest), not by the check on open
            return RunResult("CORRUPT", None, None, str(exc))
        return RunResult(state.lifecycle, state, ctl.explain())
