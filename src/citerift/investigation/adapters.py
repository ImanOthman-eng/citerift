"""The adapter protocol between the Workflow Controller and the engines that perform a step (Stage 04 Step 7).

An adapter performs one step of the fixed plan (SPEC 9.1) and returns one value of the closed type ``StepResult``.
It never writes to Investigation Memory: the controller validates the result, publishes its blobs, appends its
content records and the terminal record, and so keeps every workflow rule in one place (SPEC S-9.1). An adapter
receives a ``StepRequest`` that holds copies of what it may read; nothing in it lets the adapter change the journal.

Step 7 provides only this protocol and deterministic fake adapters (in the tests). The Stage 02 and Stage 03
adapters are Step 8.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class StepRequest:
    """What an adapter may read for one attempt. Every mapping is a copy; changing it changes nothing."""

    step: str
    attempt: int
    step_key: str
    live: bool  # a live-capture request (only then has ACQUIRE network codes and deferral)
    request: Mapping[str, Any]
    root: Mapping[str, Any] | None  # the bound root, None before ACQUIRE commits
    inputs: Mapping[str, tuple[str, ...]]  # committed output blob digests of every succeeded step
    committed: tuple[Mapping[str, Any], ...]  # the committed content records (copies), in journal order
    content_digest: str  # C(J) of the committed content (MM 7.3), which VERIFY records
    read_blob: Callable[[str], Any]  # the parsed JSON of a published blob
    now: datetime
    investigation: Mapping[str, str]  # investigation_key and investigation_id, which the report names (D-054)


@dataclass(frozen=True)
class ContentRecord:
    """One content record the step wants committed (SPEC 8.3). The controller decides its order and appends it."""

    kind: str
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class Succeeded:
    """The step completed. ``blobs`` are JSON values to publish before any record names them (M-3); ``outputs`` are
    the step's output blob digests (published here or already committed); ``root`` only for ACQUIRE."""

    records: tuple[ContentRecord, ...] = ()
    blobs: tuple[Any, ...] = ()
    outputs: tuple[str, ...] = ()
    root: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class WallClock:
    """D-042: the bound the parent enforced and the elapsed child time, for ``ACQUIRE_WALL_CLOCK_EXCEEDED``."""

    t_acq_ms: int
    elapsed_ms: int


@dataclass(frozen=True)
class Failed:
    """The step failed with ``code``. The adapter reports what happened; the controller alone decides retryability
    from SPEC 9.3 and the budgets (SPEC 9.2).

    ``not_before`` (ACQUIRE only) is a Retry-After instant the attempt observed. ``retry_after_known`` is false when
    the attempt cannot tell whether it observed one (a killed live capture, D-042): such a failure is never retried.
    ``evidence`` (EXTRACT only) is the failed Stage 03 document, kept as an uncommitted observation of the failing
    attempt (owner decision D-050, ``extraction.extraction_failure``)."""

    code: str
    reason: str | None = None
    detail: str | None = None
    not_before: datetime | None = None
    wall_clock: WallClock | None = None
    retry_after_known: bool = True
    evidence: Any = None


@dataclass(frozen=True)
class Deferred:
    """Stage 03 deferred the capture until ``not_before`` (ACQUIRE of a live capture only, SPEC 9.3)."""

    not_before: datetime


StepResult = Succeeded | Failed | Deferred
StepAdapter = Callable[[StepRequest], StepResult]
