"""DETECT: the thin integration boundary around a detector (Step 8; the production detector is Step 9).

The decision table dt-4 and the coherence function κ (SPEC 6.5, 7.3) are ``citerift.investigation.dt1``, and the
production detector that builds claims and evidence from them is ``adapters.detector.dt1_detector`` (Step 9). This
module only connects the committed NORMALIZE and LOOKUP outputs to a
``Detector`` and returns what the detector decides as individual logical records (evidence items, claims and the
evidence-set blobs the claims name). The controller derives decisions and questions (SPEC 7.6, 7.7) and owns all
batching (D-053, D-055); the boundary never builds a batch.

With no detector supplied, DETECT fails terminally with ``DECISION_TABLE_GAP`` and says why: nothing is decided, and
no claim is fabricated. A detector that reaches D-5 or D-17 raises ``DetectFailure``: DETECT then fails terminally with
that code (``ADAPTER_INCONSISTENT`` or ``DECISION_TABLE_GAP``) and commits no claim (SPEC 7.3).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from citerift.investigation.adapters import ContentRecord, Failed, StepRequest, StepResult, Succeeded
from citerift.investigation.adapters.lookup import committed_inputs
from citerift.investigation.canonical import canon, sha256_hex
from citerift.investigation.schemas import CANDIDATE_INPUTS, LOOKUP_PLAN, problems

NO_DETECTOR = "no detector is supplied: DETECT decides nothing without the decision table dt-4"
OUTPUT_TAG = "citerift-detect-output/1"


class DetectFailure(Exception):
    """A terminal DETECT failure decided by the table (D-5 ``ADAPTER_INCONSISTENT``, D-17 ``DECISION_TABLE_GAP``)
    or by a defect of the committed inputs the detector reads (``ADAPTER_INCONSISTENT``)."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail[:1000]


@dataclass(frozen=True)
class DetectInput:
    """What a detector reads: the committed candidate inputs and lookup plan, and a reader of committed blobs (the
    lookup observations, the extraction and the bundle manifest). All of it is committed content."""

    candidate_inputs: Mapping[str, Any]
    lookup_plan: Mapping[str, Any]
    read_blob: Callable[[str], Any]
    root: Mapping[str, Any]


@dataclass(frozen=True)
class Detection:
    """A detector's output: evidence items (D-051 ids), and per claim its payload and the evidence-set value it names
    (D-047). Decisions and questions are derived by the controller, never by the detector."""

    evidence: tuple[Mapping[str, Any], ...]
    claims: tuple[tuple[Mapping[str, Any], Mapping[str, Any]], ...]
    identity: str  # the detector's identity (for example its table version); recorded in the DETECT output


Detector = Callable[[DetectInput], Detection]


def committed_plan(req: StepRequest) -> dict[str, Any]:
    for digest in req.inputs.get("LOOKUP") or ():
        value = req.read_blob(digest)
        if isinstance(value, dict) and value.get("schema") == LOOKUP_PLAN:
            return value
    raise ValueError("no committed lookup plan")


def detect_input(req: StepRequest) -> DetectInput:
    if req.root is None:
        raise ValueError("DETECT without a bound root")
    _, inputs = committed_inputs(req)
    plan = committed_plan(req)
    for value, schema in ((inputs, CANDIDATE_INPUTS), (plan, LOOKUP_PLAN)):
        found = problems(value, schema)
        if found:
            raise ValueError(f"{schema}: " + "; ".join(found[:3]))
    return DetectInput(inputs, plan, req.read_blob, req.root)


def make_detect(detector: Detector | None) -> Callable[[StepRequest], StepResult]:
    """The DETECT adapter around ``detector`` (None: DETECT fails with ``DECISION_TABLE_GAP``)."""

    def detect(req: StepRequest) -> StepResult:
        if detector is None:
            return Failed("DECISION_TABLE_GAP", detail=NO_DETECTOR)
        try:
            out = detector(detect_input(req))
        except DetectFailure as exc:
            return Failed(exc.code, detail=exc.detail)
        records = [ContentRecord("evidence", dict(e)) for e in out.evidence]
        records += [ContentRecord("claim_recorded", dict(c)) for c, _ in out.claims]
        output = {
            "detect_output": OUTPUT_TAG,
            "detector": out.identity,
            "claims": sorted(str(c["claim_id"]) for c, _ in out.claims),
        }
        return Succeeded(
            records=tuple(records),
            blobs=(*(dict(s) for _, s in out.claims), output),
            outputs=(sha256_hex(canon(output)),),
        )

    return detect
