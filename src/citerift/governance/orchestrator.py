"""CITERIFT Project Orchestrator.

Reads the canonical stage registry, validates it against repository evidence,
and decides whether a proposed stage transition is allowed.

A transition is allowed only when (1) the edge exists in the transition table,
(2) the actor may take it, and (3) the registry that would result from it
passes the full consistency check. Rule (3) means every invariant is enforced
in one place, for both proposed transitions and already-recorded state.

What this cannot enforce: it cannot tell whether an ``owner_ref`` really points
to the owner's words, and it cannot stop anyone from editing files by hand.
Hand edits are caught by the consistency check (run in CI), not prevented.
"""

from __future__ import annotations

import copy
import json
import os
import re
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from functools import cached_property
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from referencing.exceptions import Unresolvable

from citerift.contracts.formats import FORMAT_CHECKER, loads_strict, parse_utc_timestamp
from citerift.contracts.validate import ContractSet
from citerift.governance import evidence, gitutil, memory
from citerift.governance.model import (
    ACTIVE,
    NEEDS_AUTHORIZATION,
    NEEDS_IMPLEMENTATION,
    NEEDS_VERIFICATION,
    Actor,
    Status,
    find_edge,
)

REGISTRY_PATH = Path("governance/stage_registry.json")
REGISTRY_SCHEMA_PATH = Path("schemas/governance/stage_registry.schema.json")
STATUS_DOC_PATH = Path("PROJECT_STATUS.md")
CONTRACTS_DIR = "schemas/contracts"
CONTRACT_FIXTURES_DIR = "tests/stage00/fixtures/contracts/v1/valid"
DECISIONS_PATH = Path("DECISIONS.md")
RISKS_PATH = Path("RISKS.md")
# Stage fields that define what verification means; recorded as a hash at verification (F-03).
DEFINITION_FIELDS = (
    "id",
    "name",
    "executor",
    "depends_on",
    "verification_dir",
    "owned_paths",
    "required_artifacts",
    "required_test_suites",
    "ci_required",
    "acceptance_gates",
)

Registry = dict[str, Any]
StageRecord = dict[str, Any]


def _version(value: object) -> tuple[int, ...]:
    """``x-citerift-version`` as a comparable tuple; anything else sorts first."""
    if isinstance(value, str) and all(part.isdigit() for part in value.split(".")):
        return tuple(int(part) for part in value.split("."))
    return ()


def utc_now(offset: timedelta = timedelta(0)) -> str:
    return (datetime.now(UTC) + offset).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str  # "error" or "warning"
    stage: str | None
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "severity": self.severity, "stage": self.stage, "message": self.message}

    def __str__(self) -> str:
        where = f"[stage {self.stage}] " if self.stage else ""
        return f"{self.severity.upper()} {self.code}: {where}{self.message}"


def errors(findings: list[Finding]) -> list[Finding]:
    return [f for f in findings if f.severity == "error"]


# A recorded time may be ahead of this machine's clock by at most this much (F-16).
MAX_CLOCK_SKEW = timedelta(minutes=5)


def _future_problem(at: str, what: str) -> list[Finding]:
    limit = utc_now(MAX_CLOCK_SKEW)
    if at > limit:
        return [Finding("TIMESTAMP_IN_FUTURE", "error", None, f"{what} time {at} is later than now ({utc_now()})")]
    return []


@dataclass
class TransitionResult:
    allowed: bool
    findings: list[Finding] = field(default_factory=list)
    registry: Registry | None = None


class GovernanceError(RuntimeError):
    def __init__(self, findings: list[Finding]):
        self.findings = findings
        super().__init__("; ".join(str(f) for f in findings))


def find_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / REGISTRY_PATH).is_file():
            return candidate
    raise FileNotFoundError(f"no {REGISTRY_PATH} found at or above {start}")


class Orchestrator:
    def __init__(self, root: Path, registry: Registry | None = None):
        self.root = root
        if registry is None:
            registry = loads_strict((root / REGISTRY_PATH).read_text(encoding="utf-8"))
        self.registry: Registry = registry

    def _now(self, *, after_history: bool = False) -> str:
        """Default time for a new record: the local clock, but never before a time already recorded (V-11).

        A blocker opened at the same second as the last transition would be replayed as open before it,
        so ``after_history`` moves such a time one second past the last history entry.
        """
        recorded: list[str] = [h["at"] for h in self.registry["history"][-1:]]
        for s in self.stages:
            recorded += [b[k] for b in s["blockers"] for k in ("opened_at", "resolved_at") if b[k]]
            recorded += [a["recorded_at"] for a in s["amendments"]]
        now: str = max([utc_now(), *recorded])
        if after_history and self.registry["history"] and now <= self.registry["history"][-1]["at"]:
            last = datetime.strptime(self.registry["history"][-1]["at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
            now = (last + timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        return now

    # ------------------------------------------------------------------ access

    @cached_property
    def _schema(self) -> dict[str, Any]:
        schema: dict[str, Any] = loads_strict((self.root / REGISTRY_SCHEMA_PATH).read_text(encoding="utf-8"))
        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as exc:
            # A schema that parses but is not a schema is reported like an unreadable one (X-05).
            raise ValueError(f"not a valid JSON Schema: {exc.message}") from exc
        return schema

    @property
    def stages(self) -> list[StageRecord]:
        stages: list[StageRecord] = self.registry["stages"]
        return stages

    def stage(self, stage_id: str) -> StageRecord:
        for s in self.stages:
            if s["id"] == stage_id:
                return s
        raise KeyError(f"unknown stage {stage_id}")

    def _artifacts_for(self, stage: StageRecord) -> list[str]:
        names = list(stage.get("required_artifacts", self.registry["policy"]["required_artifacts"]))
        handoff = self.registry["policy"]["handoff_file"]
        if handoff not in names:
            names.append(handoff)  # every stage hands off, whatever it lists (V-03)
        return [f"{stage['verification_dir']}/{n}" for n in names]

    def _test_report_for(self, stage: StageRecord) -> str | None:
        if not stage["required_test_suites"]:
            return None
        return f"{stage['verification_dir']}/{self.registry['policy']['test_report_file']}"

    def _ci_required(self, stage: StageRecord) -> bool:
        return bool(stage.get("ci_required", stage["executor"] == Actor.ENGINEERING_AGENT))

    def _definition_sha256(self, stage: StageRecord) -> str:
        """Hash of the rules a verification was checked against: the stage definition and the policy."""
        definition = {k: stage.get(k) for k in DEFINITION_FIELDS}
        return evidence.canonical_sha256({"stage": definition, "policy": self.registry["policy"]})

    # ------------------------------------------------------------ read-only ops

    def dependencies(self, stage_id: str) -> dict[str, Any]:
        stage = self.stage(stage_id)
        by_id = {s["id"]: s for s in self.stages}
        return {
            "stage": stage_id,
            "depends_on": stage["depends_on"],
            "dependents": [s["id"] for s in self.stages if stage_id in s["depends_on"]],
            "unsatisfied": [
                d for d in stage["depends_on"] if d not in by_id or by_id[d]["status"] != Status.ACCEPTED_CLOSED
            ],
        }

    def open_blockers(self, stage: StageRecord) -> list[dict[str, Any]]:
        return [b for b in stage["blockers"] if b["resolved_at"] is None]

    def next_actions(self) -> list[str]:
        """What is authorized next. Never reports anything as authorized that the owner has not authorized."""
        actions: list[str] = []
        for s in self.stages:
            st = s["status"]
            label = f"Stage {s['id']} ({s['name']})"
            if st == Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE:
                actions.append(f"{label}: owner acceptance decision required; successors stay locked until then")
            elif st == Status.BLOCKED:
                actions.append(f"{label}: blocked; resolve open blockers")
            elif st in ACTIVE and s["executor"] == Actor.EXTERNAL_AGENT:
                actions.append(f"{label}: assigned to an external agent; awaiting its handoff for owner review ({st})")
            elif st in ACTIVE:
                actions.append(f"{label}: authorized work may continue ({st})")
        for s in self.stages:
            if s["status"] == Status.NOT_STARTED and not self.dependencies(s["id"])["unsatisfied"]:
                actions.append(
                    f"Stage {s['id']} ({s['name']}): dependencies accepted; "
                    "NOT authorized until the owner explicitly authorizes it"
                )
        if not actions:
            actions.append("No stage is authorized. Wait for an explicit owner instruction.")
        return actions

    def readiness(self, stage_id: str) -> list[Finding]:
        """Evidence problems that would block verification of this stage now."""
        stage = self.stage(stage_id)
        out: list[Finding] = []
        sid = stage_id
        for dep in self.dependencies(stage_id)["unsatisfied"]:
            out.append(Finding("DEPENDENCY_NOT_ACCEPTED", "error", sid, f"dependency {dep} is not accepted"))
        for b in self.open_blockers(stage):
            out.append(Finding("BLOCKER_OPEN", "error", sid, f"{b['id']}: {b['description']}"))
        if not stage["acceptance_gates"]:
            out.append(Finding("GATES_UNDEFINED", "error", sid, "no acceptance gates are defined"))
        impl = stage["implementation"]
        revision = impl["revision"] if impl else gitutil.head(self.root)
        if revision is None:
            out.append(Finding("REVISION_UNVERIFIABLE", "error", sid, "no revision to verify"))
            return out
        out.extend(self._evidence_findings(stage, revision, recorded=None))
        _, risks = self._risks()
        for r in memory.open_critical_defects(risks, sid):
            out.append(Finding("OPEN_CRITICAL_DEFECT", "error", sid, f"{r.id}: {r.title}"))
        return out

    # ----------------------------------------------------------- consistency

    def check(self, *, include_status_doc: bool = True) -> list[Finding]:
        findings = self._schema_findings()
        if findings:
            return findings
        findings += self._structure_findings()
        if errors(findings):
            return findings
        findings += self._history_findings()
        findings += self._single_active_findings()
        findings += self._record_findings()
        findings += self._record_history_findings()
        findings += self._dependency_findings()
        findings += self._revision_findings()
        findings += self._tree_findings()
        for stage in self.stages:
            if stage["status"] in NEEDS_VERIFICATION and stage["verification"]:
                v = stage["verification"]
                findings += self._evidence_findings(stage, v["revision"], recorded=v)
                findings += self._drift_findings(stage)
        findings += self._acceptance_findings()
        findings += self._amendment_findings()
        findings += self._memory_findings()
        if include_status_doc:
            findings += self._status_doc_findings()
        return findings

    def schema_findings(self) -> list[Finding]:
        """Registry schema violations; raises OSError or ValueError if the schema itself cannot be read."""
        return self._schema_findings()

    def _tree_findings(self) -> list[Finding]:
        """Committed files outside the owned paths that would change what the checks see or run.

        Evidence is hashed as checked out. The root .gitattributes (owned by Stage 00) fixes line endings;
        a nested one would change checkout bytes for part of the tree, outside any owned path (V-12).
        CI puts ``src`` on the import path, so a module there beside the ``citerift`` package (for example
        ``sitecustomize.py``, or a package that shadows a dependency) runs before the checks (X-04).
        """
        if not gitutil.is_repository(self.root) or gitutil.head(self.root) is None:
            return []
        try:
            tracked = gitutil.tracked_files(self.root, "HEAD", ".")
        except gitutil.GitUnavailableError:
            return []
        nested = [p for p in tracked if p.endswith("/.gitattributes")]
        foreign = sorted({p.split("/")[1] for p in tracked if p.startswith("src/")} - {"citerift"})
        return [
            Finding(
                "SRC_FOREIGN_MODULE",
                "error",
                None,
                f"src/{name} is importable beside the citerift package and would run or shadow code before "
                "the checks; only src/citerift may exist",
            )
            for name in foreign
        ] + [
            Finding(
                "ATTRIBUTES_NESTED",
                "error",
                None,
                f"{p} overrides the line-ending policy of the root .gitattributes, so evidence hashes would "
                "depend on the checkout; put attributes in the root file",
            )
            for p in nested
        ]

    def _schema_findings(self) -> list[Finding]:
        validator = Draft202012Validator(self._schema, format_checker=FORMAT_CHECKER)
        try:
            found = sorted(validator.iter_errors(self.registry), key=lambda e: list(e.absolute_path))
        except Unresolvable as exc:
            raise ValueError(f"the schema has an unresolvable reference: {exc}") from exc
        return [
            Finding(
                "REGISTRY_SCHEMA",
                "error",
                None,
                f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}",
            )
            for e in found
        ]

    def _structure_findings(self) -> list[Finding]:
        out: list[Finding] = []
        ids = [s["id"] for s in self.stages]
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        for d in dupes:
            out.append(Finding("STAGE_DUPLICATE", "error", d, "stage id appears more than once"))
        known = set(ids)
        for s in self.stages:
            if s["executor"] == Actor.ENGINEERING_AGENT and not s["required_test_suites"]:
                out.append(
                    Finding("TEST_SUITES_UNDEFINED", "error", s["id"], "an engineering stage must require test suites")
                )
            for d in s["depends_on"]:
                if d not in known:
                    out.append(Finding("DEPENDENCY_UNKNOWN", "error", s["id"], f"unknown dependency {d}"))
                if d == s["id"]:
                    out.append(Finding("DEPENDENCY_CYCLE", "error", s["id"], "stage depends on itself"))
        if not out:
            # Kahn's algorithm, O(V + E).
            indegree = {s["id"]: len(s["depends_on"]) for s in self.stages}
            dependents: dict[str, list[str]] = {i: [] for i in ids}
            for s in self.stages:
                for d in s["depends_on"]:
                    dependents[d].append(s["id"])
            ready = [i for i, n in indegree.items() if n == 0]
            visited = 0
            while ready:
                node = ready.pop()
                visited += 1
                for nxt in dependents[node]:
                    indegree[nxt] -= 1
                    if indegree[nxt] == 0:
                        ready.append(nxt)
            if visited != len(ids):
                cyclic = sorted(i for i, n in indegree.items() if n > 0)
                out.append(Finding("DEPENDENCY_CYCLE", "error", None, f"dependency cycle among {cyclic}"))
        return out

    def _history_findings(self) -> list[Finding]:
        out: list[Finding] = []
        replay = {s["id"]: Status.NOT_STARTED for s in self.stages}
        executors = {s["id"]: s["executor"] for s in self.stages}
        previous_at = ""
        for index, h in enumerate(self.registry["history"], start=1):
            sid = h["stage"]
            if h["seq"] != index:
                out.append(Finding("HISTORY_SEQUENCE", "error", sid, f"entry {index} has seq {h['seq']}"))
            if h["at"] < previous_at:
                out.append(Finding("HISTORY_TIME_ORDER", "error", sid, f"entry {index} is earlier than the one before"))
            previous_at = h["at"]
            for f in _future_problem(h["at"], f"history entry {index}"):
                out.append(Finding("HISTORY_FUTURE_TIMESTAMP", "error", sid, f.message))
            if sid not in replay:
                out.append(Finding("HISTORY_UNKNOWN_STAGE", "error", sid, f"entry {index} names an unknown stage"))
                continue
            source, target = Status(h["from"]), Status(h["to"])
            if replay[sid] != source:
                out.append(
                    Finding(
                        "HISTORY_INVALID_EDGE",
                        "error",
                        sid,
                        f"entry {index} starts from {source} but the stage was {replay[sid]}",
                    )
                )
            edge = find_edge(source, target)
            if edge is None:
                out.append(
                    Finding(
                        "HISTORY_INVALID_EDGE",
                        "error",
                        sid,
                        f"entry {index}: {source} -> {target} is not a permitted transition",
                    )
                )
            else:
                if edge.owner_only and h["actor"] != Actor.OWNER:
                    out.append(
                        Finding(
                            "HISTORY_ACTOR",
                            "error",
                            sid,
                            f"entry {index}: {source} -> {target} requires the owner, recorded actor is {h['actor']}",
                        )
                    )
                if not edge.owner_only and h["actor"] not in (Actor.OWNER, executors[sid]):
                    out.append(
                        Finding(
                            "HISTORY_ACTOR",
                            "error",
                            sid,
                            f"entry {index}: actor {h['actor']} is not the stage executor or the owner",
                        )
                    )
                if edge.owner_only and not h["owner_ref"]:
                    out.append(
                        Finding(
                            "HISTORY_OWNER_REF_MISSING",
                            "error",
                            sid,
                            f"entry {index}: owner decision without a reference to the owner's statement",
                        )
                    )
            if edge is not None:
                out += self._replay_step_findings(index, h, source, target, replay)
            replay[sid] = target
            if (
                target in ACTIVE
                and source not in ACTIVE
                and executors[sid] == Actor.ENGINEERING_AGENT
                and self.registry["policy"]["single_active_engineering_stage"]
            ):
                active = [i for i, st in replay.items() if executors[i] == Actor.ENGINEERING_AGENT and st in ACTIVE]
                if len(active) > 1:
                    out.append(
                        Finding(
                            "HISTORY_SINGLE_ACTIVE",
                            "error",
                            sid,
                            f"entry {index} made more than one engineering stage active: {active}",
                        )
                    )
        for s in self.stages:
            if replay[s["id"]] != s["status"]:
                out.append(
                    Finding(
                        "STATUS_HISTORY_CONFLICT",
                        "error",
                        s["id"],
                        f"recorded status {s['status']} conflicts with history, which gives {replay[s['id']]}",
                    )
                )
        return out

    def _replay_step_findings(
        self, index: int, h: dict[str, Any], source: Status, target: Status, replay: dict[str, Status]
    ) -> list[Finding]:
        """Rules that ``propose`` enforces, checked again at the time of each history entry (F-04, F-05).

        They follow the guards of the verified model (simulations/stage00/state_machine_model.py):
        dependencies at authorize, verify and accept; a correction amendment to reopen; blockers.
        """
        sid, at = h["stage"], h["at"]
        stage = self.stage(sid)
        out: list[Finding] = []
        if (source, target) in (
            (Status.NOT_STARTED, Status.AUTHORIZED),
            (Status.IMPLEMENTED_NOT_VERIFIED, Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE),
            (Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE, Status.ACCEPTED_CLOSED),
        ):
            pending = [d for d in stage["depends_on"] if replay.get(d) != Status.ACCEPTED_CLOSED]
            if pending:
                out.append(
                    Finding(
                        "HISTORY_DEPENDENCY",
                        "error",
                        sid,
                        f"entry {index}: {source} -> {target} while dependencies {pending} were not accepted",
                    )
                )
        if source == Status.ACCEPTED_CLOSED:
            ref = h.get("amendment")
            amendment = next((a for a in stage["amendments"] if a["id"] == ref), None)
            earlier = [
                e["seq"]
                for e in self.registry["history"]
                if e["seq"] < h["seq"]
                and e["stage"] == sid
                and e["from"] == Status.ACCEPTED_CLOSED
                and ref is not None
                and e.get("amendment") == ref
            ]
            if earlier:
                out.append(
                    Finding(
                        "HISTORY_AMENDMENT_REUSED",
                        "error",
                        sid,
                        f"entry {index} reopens the stage with {ref}, which already justified entry {earlier[0]}",
                    )
                )
            if amendment is None or amendment["kind"] != "correction" or amendment["recorded_at"] > at:
                out.append(
                    Finding(
                        "HISTORY_AMENDMENT_MISSING",
                        "error",
                        sid,
                        f"entry {index} reopens an accepted stage without a correction amendment recorded before it",
                    )
                )
        open_then = [b["id"] for b in stage["blockers"] if b["opened_at"] <= at and not (b["resolved_at"] or "~") <= at]
        if target == Status.BLOCKED and not open_then:
            out.append(Finding("HISTORY_BLOCKER", "error", sid, f"entry {index} blocks the stage with no open blocker"))
        if open_then and (
            (source, target)
            in (
                (Status.AUTHORIZED, Status.IN_PROGRESS),
                (Status.BLOCKED, Status.IN_PROGRESS),
                (Status.IMPLEMENTED_NOT_VERIFIED, Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE),
                (Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE, Status.ACCEPTED_CLOSED),  # X-10
            )
        ):
            out.append(
                Finding(
                    "HISTORY_BLOCKER",
                    "error",
                    sid,
                    f"entry {index}: {source} -> {target} while blockers {open_then} were open",
                )
            )
        return out

    def _record_history_findings(self) -> list[Finding]:
        """Each record must be the one its history entry created (F-17), and an acceptance must cite
        an owner statement that is not already cited by history from before the verification."""
        out: list[Finding] = []
        history = self.registry["history"]
        for s in self.stages:
            sid = s["id"]
            for name, target in (
                ("authorization", Status.AUTHORIZED),
                ("implementation", Status.IMPLEMENTED_NOT_VERIFIED),
                ("verification", Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE),
                ("acceptance", Status.ACCEPTED_CLOSED),
            ):
                record = s[name]
                if record is None:
                    continue
                entries = [h for h in history if h["stage"] == sid and h["to"] == target]
                if target == Status.AUTHORIZED:
                    entries = [h for h in entries if h["from"] == Status.NOT_STARTED]
                last = entries[-1] if entries else None
                if (
                    last is None
                    or last["at"] != record["recorded_at"]
                    or ("owner_ref" in record and last["owner_ref"] != record["owner_ref"])
                ):
                    out.append(
                        Finding(
                            "RECORD_HISTORY_MISMATCH",
                            "error",
                            sid,
                            f"the {name} record does not match the history entry that created it",
                        )
                    )
            acc = s["acceptance"]
            verified_at = [
                h["seq"] for h in history if h["stage"] == sid and h["to"] == Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE
            ]
            if acc is not None and verified_at:
                verified_entry = next(h for h in history if h["seq"] == verified_at[-1])
                reused = [
                    str(h["seq"]) for h in history if h["seq"] < verified_at[-1] and h["owner_ref"] == acc["owner_ref"]
                ]
                # Amendments cite owner statements too (V-07).
                reused += [
                    a["id"]
                    for st in self.stages
                    for a in st["amendments"]
                    if a["owner_ref"] == acc["owner_ref"] and a["recorded_at"] <= verified_entry["at"]
                ]
                if reused:
                    out.append(
                        Finding(
                            "OWNER_REF_REUSED",
                            "error",
                            sid,
                            f"the acceptance cites {acc['owner_ref']}, already cited by {', '.join(reused)} "
                            "from before the stage was verified",
                        )
                    )
        for s in self.stages:
            for b in s["blockers"]:
                for key in ("opened_at", "resolved_at"):
                    if b[key]:
                        for f in _future_problem(b[key], f"blocker {b['id']} {key}"):
                            out.append(Finding("HISTORY_FUTURE_TIMESTAMP", "error", s["id"], f.message))
            for a in s["amendments"]:
                for f in _future_problem(a["recorded_at"], f"amendment {a['id']}"):
                    out.append(Finding("HISTORY_FUTURE_TIMESTAMP", "error", s["id"], f.message))
        return out

    def _single_active_findings(self) -> list[Finding]:
        if not self.registry["policy"]["single_active_engineering_stage"]:
            return []
        active = [s["id"] for s in self.stages if s["executor"] == Actor.ENGINEERING_AGENT and s["status"] in ACTIVE]
        if len(active) > 1:
            return [
                Finding("MULTIPLE_ACTIVE_STAGES", "error", None, f"more than one engineering stage is active: {active}")
            ]
        return []

    def _record_findings(self) -> list[Finding]:
        out: list[Finding] = []
        for s in self.stages:
            sid, st = s["id"], Status(s["status"])
            for name, needed in (
                ("authorization", st in NEEDS_AUTHORIZATION),
                ("implementation", st in NEEDS_IMPLEMENTATION),
                ("verification", st in NEEDS_VERIFICATION),
                ("acceptance", st == Status.ACCEPTED_CLOSED),
            ):
                if needed and s[name] is None:
                    out.append(Finding("RECORD_MISSING", "error", sid, f"status {st} requires a {name} record"))
                if not needed and s[name] is not None:
                    out.append(
                        Finding("RECORD_UNEXPECTED", "error", sid, f"status {st} must not carry a {name} record")
                    )
            open_blockers = self.open_blockers(s)
            if st == Status.BLOCKED and not open_blockers:
                out.append(Finding("BLOCKED_WITHOUT_BLOCKER", "error", sid, "stage is BLOCKED but has no open blocker"))
            if st != Status.BLOCKED:
                # A verified or accepted stage cannot carry an open blocker; elsewhere it is reported.
                severity = "error" if st in NEEDS_VERIFICATION else "warning"
                for b in open_blockers:
                    out.append(
                        Finding("BLOCKER_OPEN", severity, sid, f"unresolved blocker {b['id']}: {b['description']}")
                    )
            for b in s["blockers"]:
                if (b["resolved_at"] is None) != (b["resolution"] is None):
                    out.append(
                        Finding(
                            "BLOCKER_RECORD",
                            "error",
                            sid,
                            f"{b['id']} needs both resolved_at and resolution, or neither",
                        )
                    )
        return out

    def _dependency_findings(self) -> list[Finding]:
        out: list[Finding] = []
        reopened = {h["stage"] for h in self.registry["history"] if h["from"] == Status.ACCEPTED_CLOSED}
        for s in self.stages:
            if s["status"] == Status.NOT_STARTED:
                continue
            for d in self.dependencies(s["id"])["unsatisfied"]:
                if d in reopened:
                    # The dependency was accepted and has been reopened for a correction (F-11). The
                    # history replay checked that it was accepted when this stage needed it.
                    out.append(
                        Finding(
                            "DEPENDENCY_REOPENED",
                            "warning",
                            s["id"],
                            f"dependency {d} was reopened for a correction; it must be accepted again "
                            f"before stage {s['id']} can be verified or accepted",
                        )
                    )
                    continue
                severity = "warning" if s["status"] == Status.BLOCKED else "error"
                out.append(
                    Finding(
                        "DEPENDENCY_NOT_ACCEPTED",
                        severity,
                        s["id"],
                        f"status {s['status']} but dependency {d} is not ACCEPTED_CLOSED",
                    )
                )
        return out

    def _revision_refs(self) -> list[tuple[str, str, str]]:
        refs: list[tuple[str, str, str]] = []
        for s in self.stages:
            sid = s["id"]
            if s["implementation"]:
                refs.append((sid, "implementation", s["implementation"]["revision"]))
            if s["verification"]:
                refs.append((sid, "verification", s["verification"]["revision"]))
                ci = s["verification"].get("ci")
                if ci:
                    refs.append((sid, "ci head", ci["head_sha"]))
            if s["acceptance"]:
                refs.append((sid, "acceptance", s["acceptance"]["accepted_revision"]))
            for a in s["amendments"]:
                if a["revision"]:
                    refs.append((sid, f"amendment {a['id']}", a["revision"]))
        return refs

    def _revision_findings(self) -> list[Finding]:
        refs = self._revision_refs()
        if not refs:
            return []
        if not gitutil.is_repository(self.root):
            return [
                Finding(
                    "REVISION_UNVERIFIABLE",
                    "error",
                    None,
                    "not a git repository; revision references cannot be checked",
                )
            ]
        head = gitutil.head(self.root)
        shallow = gitutil.is_shallow(self.root)
        out: list[Finding] = []
        for sid, what, sha in refs:
            if not gitutil.commit_exists(self.root, sha):
                hint = " (repository is shallow; fetch full history)" if shallow else ""
                out.append(Finding("REVISION_NOT_FOUND", "error", sid, f"{what} revision {sha} does not exist{hint}"))
            elif head is None or not gitutil.is_ancestor(self.root, sha, head):
                out.append(
                    Finding(
                        "REVISION_NOT_IN_HISTORY",
                        "error",
                        sid,
                        f"{what} revision {sha} is not part of the current history",
                    )
                )
        return out

    def _evidence_findings(self, stage: StageRecord, revision: str, recorded: dict[str, Any] | None) -> list[Finding]:
        sid = stage["id"]
        out: list[Finding] = []
        recorded_hashes = {a["path"]: a["sha256"] for a in recorded["artifacts"]} if recorded else {}
        for rel in self._artifacts_for(stage):
            if recorded is not None and rel not in recorded_hashes:
                out.append(
                    Finding(
                        "EVIDENCE_NOT_RECORDED", "error", sid, f"{rel} is required but not in the verification record"
                    )
                )
            for p in evidence.check_artifact(self.root, rel, recorded_hashes.get(rel)):
                out.append(Finding(p.code, "error", sid, p.message))
        handoff_rel = f"{stage['verification_dir']}/{self.registry['policy']['handoff_file']}"
        handoff = self.root / handoff_rel
        try:
            text = handoff.read_text(encoding="utf-8") if handoff.is_file() else None
        except UnicodeDecodeError as exc:
            out.append(Finding("EVIDENCE_UNREADABLE", "error", sid, f"{handoff_rel} is not UTF-8 text: {exc}"))
            text = None
        if text is not None:
            missing = evidence.missing_sections(text, self.registry["policy"]["handoff_required_sections"])
            if missing:
                out.append(
                    Finding("HANDOFF_INCOMPLETE", "error", sid, f"{handoff_rel} lacks sections: {', '.join(missing)}")
                )
            if not evidence.mentions_revision(text, revision):
                out.append(
                    Finding(
                        "HANDOFF_WRONG_REVISION",
                        "error",
                        sid,
                        f"{handoff_rel} does not cite the verified revision {revision[:12]}",
                    )
                )
        report_rel = self._test_report_for(stage)
        if report_rel is not None:
            recorded_report = recorded["test_report"] if recorded else None
            if recorded is not None and (recorded_report is None or recorded_report["path"] != report_rel):
                out.append(
                    Finding(
                        "TEST_EVIDENCE_NOT_RECORDED",
                        "error",
                        sid,
                        f"{report_rel} is required but not in the verification record",
                    )
                )
            for p in evidence.check_test_report(
                self.root,
                report_rel,
                recorded_report["sha256"] if recorded_report else None,
                revision,
                stage["required_test_suites"],
            ):
                out.append(Finding(p.code, "error", sid, p.message))
        if recorded is not None:
            out += self._manifest_findings(stage, recorded)
            out += self._definition_findings(stage, recorded)
            out += self._gate_findings(stage, recorded, revision)
            ci = recorded.get("ci")
            if ci is None and self._ci_required(stage):
                out.append(
                    Finding("CI_EVIDENCE_MISSING", "error", sid, "no CI run is recorded for the verified revision")
                )
            if ci is not None:
                repository = self.registry["project"]["repository"]
                # The whole URL is matched, not a prefix: dot segments could leave the repository (Z-02).
                run = re.fullmatch(
                    rf"https://github\.com/{re.escape(repository)}/actions/runs/[0-9]+", ci["run_url"], re.I
                )
                if run is None:
                    out.append(
                        Finding(
                            "CI_WRONG_REPOSITORY",
                            "error",
                            sid,
                            f"CI run {ci['run_url']} is not a run of {repository} (Y-10)",
                        )
                    )
                if ci["head_sha"] != revision:
                    out.append(
                        Finding(
                            "CI_WRONG_REVISION",
                            "error",
                            sid,
                            f"CI run tested {ci['head_sha'][:12]}, not {revision[:12]}",
                        )
                    )
                if ci["conclusion"] != "success":
                    out.append(Finding("CI_NOT_SUCCESSFUL", "error", sid, f"CI conclusion is '{ci['conclusion']}'"))
        _, risks = self._risks()
        if recorded is not None:
            for r in memory.open_critical_defects(risks, sid):
                out.append(
                    Finding(
                        "OPEN_CRITICAL_DEFECT", "error", sid, f"verified with open critical defect {r.id}: {r.title}"
                    )
                )
        return out

    def _gate_findings(self, stage: StageRecord, recorded: dict[str, Any], revision: str) -> list[Finding]:
        sid = stage["id"]
        out: list[Finding] = []
        defined = [g["id"] for g in stage["acceptance_gates"]]
        if not defined:
            out.append(
                Finding("GATES_UNDEFINED", "error", sid, "verification recorded but no acceptance gates are defined")
            )
        results = recorded["gates"]
        manifest_paths = {e["path"] for e in recorded["evidence_manifest"]}
        for gid in defined:
            result = results.get(gid)
            if result is None:
                out.append(Finding("GATE_RESULT_MISSING", "error", sid, f"gate {gid} has no recorded result"))
                continue
            if result["result"] != "pass":
                out.append(Finding("GATE_NOT_PASSED", "error", sid, f"gate {gid} is '{result['result']}'"))
            # A URL may be cited for context but is not pinned; every cited file must be pinned (in the
            # evidence manifest, or under an owned path whose content the drift check compares).
            pinned = False
            for ref in result["evidence"]:
                if evidence.is_url(ref):
                    continue
                if not (evidence.inside(self.root, ref) and (self.root / ref).is_file()):
                    out.append(
                        Finding("GATE_EVIDENCE_MISSING", "error", sid, f"gate {gid} cites {ref}, which is not a file")
                    )
                elif not evidence.is_plain_path(self.root, ref):
                    # Ownership and the manifest are decided on the path as written, so a path through
                    # ".." or a symlink could name a file outside both (X-01).
                    out.append(
                        Finding(
                            "GATE_EVIDENCE_UNPINNED",
                            "error",
                            sid,
                            f"gate {gid} cites {ref}, which goes through '..', '.' or a symbolic link",
                        )
                    )
                elif ref in manifest_paths or (self._owned(stage, ref) and self._committed(revision, ref)):
                    # An owned file is bound by the drift rule only if it is committed at the verified
                    # revision; an ignored or untracked one is bound by nothing (Y-09).
                    pinned = True
                else:
                    out.append(
                        Finding(
                            "GATE_EVIDENCE_UNPINNED",
                            "error",
                            sid,
                            f"gate {gid} cites {ref}, which is neither in the evidence manifest nor an owned file "
                            f"committed at {revision[:12]}",
                        )
                    )
            if not pinned:
                out.append(
                    Finding(
                        "GATE_EVIDENCE_UNPINNED",
                        "error",
                        sid,
                        f"gate {gid} cites no hash-pinned file (a URL alone is not pinned)",
                    )
                )
        for gid in results:
            if gid not in defined:
                out.append(Finding("GATE_UNKNOWN", "error", sid, f"result recorded for undefined gate {gid}"))
        return out

    def _committed(self, revision: str, rel: str) -> bool:
        try:
            return gitutil.exists_at(self.root, revision, rel)
        except gitutil.GitUnavailableError:
            return False

    @staticmethod
    def _owned(stage: StageRecord, rel: str) -> bool:
        return any(rel == p or rel.startswith(p.rstrip("/") + "/") for p in stage["owned_paths"])

    def _manifest_findings(self, stage: StageRecord, recorded: dict[str, Any]) -> list[Finding]:
        """Every file under the verification directory is pinned by hash at verification (F-02)."""
        sid = stage["id"]
        recorded_hashes = {e["path"]: e["sha256"] for e in recorded["evidence_manifest"]}
        try:
            current = {e["path"]: e["sha256"] for e in evidence.manifest(self.root, stage["verification_dir"])}
        except evidence.EvidenceNameError as exc:
            return [Finding("EVIDENCE_UNREADABLE", "error", sid, str(exc))]
        except gitutil.GitUnavailableError as exc:
            return [Finding("REVISION_UNVERIFIABLE", "error", sid, f"cannot list the evidence files: {exc}")]
        # Only an enhancement's test report may be added after verification; its own hash and revision are
        # checked by _amendment_findings. A correction leads to a new verification instead (V-05).
        later = {
            a["test_report"]["path"] for a in stage["amendments"] if a["test_report"] and a["kind"] == "enhancement"
        }
        out: list[Finding] = []
        for rel, sha in sorted(recorded_hashes.items()):
            if rel not in current:
                out.append(Finding("EVIDENCE_MISSING", "error", sid, f"recorded evidence {rel} no longer exists"))
            elif current[rel] != sha:
                out.append(
                    Finding("EVIDENCE_STALE", "error", sid, f"{rel} changed after verification (sha256 mismatch)")
                )
        for rel in sorted(set(current) - set(recorded_hashes) - later):
            out.append(
                Finding(
                    "EVIDENCE_UNLISTED", "error", sid, f"{rel} was added to the evidence directory after verification"
                )
            )
        return out

    def _definition_findings(self, stage: StageRecord, recorded: dict[str, Any]) -> list[Finding]:
        """The stage definition and policy must be the ones the stage was verified against (F-03)."""
        sid = stage["id"]
        out: list[Finding] = []
        if recorded["definition_sha256"] != self._definition_sha256(stage):
            out.append(
                Finding(
                    "DEFINITION_CHANGED",
                    "error",
                    sid,
                    "the stage definition or the policy changed after verification",
                )
            )
        if stage["executor"] == Actor.ENGINEERING_AGENT:
            for field_name in ("owned_paths", "required_test_suites", "acceptance_gates"):
                if not stage[field_name]:
                    out.append(
                        Finding(
                            "DEFINITION_WEAK",
                            "error",
                            sid,
                            f"an engineering stage cannot be verified with empty {field_name}",
                        )
                    )
        return out

    def _drift_findings(self, stage: StageRecord) -> list[Finding]:
        """Owned content at HEAD must equal the content at a covering revision.

        Content is compared, not history: "which commit last touched these
        paths" misses a merge that restores an older version (F-01).
        """
        sid = stage["id"]
        paths = stage["owned_paths"]
        if not paths or not gitutil.is_repository(self.root):
            return []
        covering = [stage["verification"]["revision"]]
        covering += [a["revision"] for a in self._current_enhancements(stage) if a["revision"] and a["test_report"]]
        out: list[Finding] = []
        try:
            changes = [
                gitutil.changed_paths(self.root, c, paths) for c in covering if gitutil.commit_exists(self.root, c)
            ]
            if changes and all(changes):
                last = gitutil.last_commit_touching(self.root, paths)
                shown = ", ".join(changes[0][:5]) + (" ..." if len(changes[0]) > 5 else "")
                out.append(
                    Finding(
                        "VERIFICATION_STALE",
                        "error",
                        sid,
                        f"owned content differs from the verified revision ({shown}; last change seen in history: "
                        f"{last[:12] if last else 'unknown'}), with no recorded amendment covering the change",
                    )
                )
            dirty = [
                p
                for p in gitutil.dirty_paths(self.root)
                if any(p == owned or p.startswith(owned.rstrip("/") + "/") for owned in paths)
            ]
        except gitutil.GitUnavailableError as exc:
            return [Finding("REVISION_UNVERIFIABLE", "error", sid, f"cannot inspect owned paths: {exc}")]
        if dirty:
            out.append(
                Finding(
                    "UNCOMMITTED_OWNED_CHANGE",
                    "warning",
                    sid,
                    f"uncommitted changes to owned paths ({', '.join(dirty[:5])}); "
                    "committing them makes the stage stale",
                )
            )
        return out

    def _current_enhancements(self, stage: StageRecord) -> list[dict[str, Any]]:
        """Enhancements of the stage's current acceptance. Only these can cover owned changes: one on a stage
        that is not accepted, or from before a later reopening, would cover code nobody accepted (Y-06)."""
        acc = stage["acceptance"]
        if stage["status"] != Status.ACCEPTED_CLOSED or not acc:
            return []
        since = parse_utc_timestamp(acc["recorded_at"])
        return [
            a
            for a in stage["amendments"]
            if a["kind"] == "enhancement"
            and since is not None
            and (t := parse_utc_timestamp(a["recorded_at"])) is not None
            and t >= since
        ]

    def _accepted_at(self, stage_id: str, at: str) -> bool:
        """True when the stage was accepted at ``at``: accepted after the entries before that second, or
        accepted by an entry in that same second. Entries later in the same second (a reopening that the
        amendment justifies) come after the amendment."""
        when = parse_utc_timestamp(at)
        if when is None:
            return False
        status = Status.NOT_STARTED.value
        same_second_acceptance = False
        for h in self.registry["history"]:
            t = parse_utc_timestamp(h["at"])
            if h["stage"] != stage_id or t is None:
                continue
            if t < when:
                status = h["to"]
            elif t == when and h["to"] == Status.ACCEPTED_CLOSED:
                same_second_acceptance = True
        return status == Status.ACCEPTED_CLOSED or same_second_acceptance

    def _acceptance_findings(self) -> list[Finding]:
        out: list[Finding] = []
        history = self.registry["history"]
        for s in self.stages:
            acc, ver = s["acceptance"], s["verification"]
            if not acc or not ver:
                continue
            sid = s["id"]
            if acc["accepted_revision"] != ver["revision"]:
                out.append(
                    Finding("ACCEPTANCE_STALE", "error", sid, "accepted revision differs from the verified revision")
                )
            if acc["recorded_at"] < ver["recorded_at"]:
                out.append(
                    Finding("ACCEPTANCE_STALE", "error", sid, "acceptance predates the current verification record")
                )
            into = [h for h in history if h["stage"] == sid and h["to"] == Status.ACCEPTED_CLOSED]
            if not into or into[-1]["owner_ref"] != acc["owner_ref"]:
                out.append(
                    Finding(
                        "ACCEPTANCE_UNTRACEABLE",
                        "error",
                        sid,
                        "acceptance record does not match the owner's history entry",
                    )
                )
        return out

    def _amendment_findings(self) -> list[Finding]:
        out: list[Finding] = []
        for s in self.stages:
            sid = s["id"]
            ids = [a["id"] for a in s["amendments"]]
            for kind, values in (("AMENDMENT", ids), ("BLOCKER", [b["id"] for b in s["blockers"]])):
                for dup in sorted({v for v in values if values.count(v) > 1}):
                    out.append(Finding(f"{kind}_DUPLICATE_ID", "error", sid, f"{dup} is recorded more than once"))
            reopen_refs = {
                h.get("amendment")
                for h in self.registry["history"]
                if h["stage"] == sid and h["from"] == Status.ACCEPTED_CLOSED
            }
            for a in s["amendments"]:
                if not a["id"].startswith(f"A-{sid}-"):
                    out.append(Finding("AMENDMENT_RECORD", "error", sid, f"{a['id']} does not belong to stage {sid}"))
                # The tool records an amendment only on an accepted stage; check holds a hand-written one to the
                # same rule, by the stage's status at the amendment's own time (Y-06, Y-07).
                if not self._accepted_at(sid, a["recorded_at"]):
                    out.append(
                        Finding(
                            "AMENDMENT_NOT_APPLICABLE",
                            "error",
                            sid,
                            f"{a['id']} is recorded at {a['recorded_at']}, when stage {sid} was not accepted",
                        )
                    )
                if a["kind"] == "enhancement":
                    if a["revision"] is None or a["test_report"] is None:
                        out.append(
                            Finding(
                                "AMENDMENT_UNVERIFIED",
                                "error",
                                sid,
                                f"enhancement {a['id']} needs a revision and a passing test report",
                            )
                        )
                    else:
                        report = a["test_report"]
                        for p in evidence.check_test_report(
                            self.root, report["path"], report["sha256"], a["revision"], s["required_test_suites"]
                        ):
                            out.append(Finding(p.code, "error", sid, f"amendment {a['id']}: {p.message}"))
                        out += self._enhancement_contract_findings(s, a)
                elif a["test_report"] is not None:
                    rel = a["test_report"]["path"]
                    if not (evidence.inside(self.root, rel) and (self.root / rel).is_file()):
                        out.append(Finding("EVIDENCE_MISSING", "error", sid, f"amendment {a['id']}: {rel} is missing"))
                    elif evidence.sha256_file(self.root / rel) != a["test_report"]["sha256"]:
                        out.append(
                            Finding(
                                "EVIDENCE_STALE",
                                "error",
                                sid,
                                f"amendment {a['id']}: {rel} changed after it was recorded",
                            )
                        )
                if a["kind"] != "enhancement" and a["id"] not in reopen_refs and s["status"] == Status.ACCEPTED_CLOSED:
                    out.append(
                        Finding(
                            "CORRECTION_PENDING",
                            "warning",
                            sid,
                            f"correction {a['id']} is recorded but the stage has not been reopened",
                        )
                    )
            for h in self.registry["history"]:
                ref = h.get("amendment")
                if h["stage"] == sid and ref is not None and ref not in ids:
                    out.append(Finding("AMENDMENT_UNKNOWN", "error", sid, f"history cites unknown amendment {ref}"))
        return out + self._amendment_ref_findings()

    def _amendment_ref_findings(self) -> list[Finding]:
        """An amendment records an owner decision of its own, so it must cite an owner statement that no
        earlier history entry or amendment cited (X-13: an enhancement reused the acceptance's reference)."""
        # Each citation: time, reference, where, and the amendment a reopening entry used (it may share the
        # amendment's reference, because one owner statement records the correction and the reopening).
        cited: list[tuple[str, str, str, str | None]] = [
            (h["at"], h["owner_ref"], f"history entry {h['seq']}", h.get("amendment"))
            for h in self.registry["history"]
            if h["owner_ref"]
        ]
        amendments = [(s["id"], a) for s in self.stages for a in s["amendments"]]
        cited += [(a["recorded_at"], a["owner_ref"], a["id"], None) for _, a in amendments]
        out = []
        for sid, a in amendments:
            mine = parse_utc_timestamp(a["recorded_at"])
            # At or before, not only before: a reference cited in the same second was cited first (Y-07).
            prior = [
                where
                for at, ref, where, used in cited
                if ref == a["owner_ref"]
                and where != a["id"]
                and used != a["id"]
                and mine is not None
                and (t := parse_utc_timestamp(at)) is not None
                and t <= mine
            ]
            if prior:
                out.append(
                    Finding(
                        "OWNER_REF_REUSED",
                        "error",
                        sid,
                        f"amendment {a['id']} cites {a['owner_ref']}, already cited by {', '.join(prior)}",
                    )
                )
        return out

    def _enhancement_contract_findings(self, stage: StageRecord, amendment: dict[str, Any]) -> list[Finding]:
        """A contract changed by an enhancement must raise its version and keep every valid fixture of the
        accepted revision valid (docs/data-contracts.md, Versioning; X-13)."""
        sid = stage["id"]
        base = (stage["verification"] or {}).get("revision")
        rev = amendment["revision"]
        if base is None:
            return []
        try:
            changed = [
                p
                for p in gitutil.changed_paths(self.root, base, [CONTRACTS_DIR], rev)
                if p.endswith(".schema.json") and self._owned(stage, p)
            ]
            if not changed:
                return []
            out = []
            for path in changed:
                old_text, new_text = gitutil.show(self.root, base, path), gitutil.show(self.root, rev, path)
                old = loads_strict(old_text) if old_text is not None else {}
                new = loads_strict(new_text) if new_text is not None else {}
                if _version(new.get("x-citerift-version")) <= _version(old.get("x-citerift-version")):
                    out.append(
                        Finding(
                            "CONTRACT_VERSION_NOT_INCREASED",
                            "error",
                            sid,
                            f"amendment {amendment['id']} changes {path} without raising its x-citerift-version "
                            f"({old.get('x-citerift-version')} -> {new.get('x-citerift-version')})",
                        )
                    )
            schemas = {}
            for path in gitutil.tracked_files(self.root, rev, CONTRACTS_DIR):
                text = gitutil.show(self.root, rev, path) if path.endswith(".schema.json") else None
                if text is not None:
                    schema = loads_strict(text)
                    schemas[schema["$id"]] = schema
            contracts = ContractSet(schemas)
            for path in gitutil.tracked_files(self.root, base, CONTRACT_FIXTURES_DIR):
                text = gitutil.show(self.root, base, path) if path.endswith(".json") else None
                if text is not None and (problems := contracts.validate(loads_strict(text))):
                    out.append(
                        Finding(
                            "CONTRACT_INCOMPATIBLE",
                            "error",
                            sid,
                            f"amendment {amendment['id']}: {path}, valid at the accepted revision, is now "
                            f"rejected: {problems[0]}",
                        )
                    )
        except (gitutil.GitUnavailableError, ValueError, KeyError, TypeError, AttributeError) as exc:
            return [
                Finding(
                    "CONTRACT_INCOMPATIBLE",
                    "error",
                    sid,
                    f"amendment {amendment['id']}: the contract change cannot be checked: {exc}",
                )
            ]
        return out

    def _risks(self) -> tuple[list[memory.MemoryProblem], list[memory.Entry]]:
        entries, problems = memory.check_risks(self.root / RISKS_PATH)
        return problems, entries

    def _memory_findings(self) -> list[Finding]:
        _, decision_problems = memory.check_decisions(self.root / DECISIONS_PATH)
        risk_problems, _ = self._risks()
        return [Finding(p.code, "error", None, f"{p.file}: {p.message}") for p in [*decision_problems, *risk_problems]]

    def _status_doc_findings(self) -> list[Finding]:
        path = self.root / STATUS_DOC_PATH
        try:
            current = path.read_text(encoding="utf-8") if path.is_file() else None
        except UnicodeDecodeError:
            current = None  # not UTF-8, so it cannot match (X-05)
        if current != self.render_status():
            return [
                Finding(
                    "STATUS_DOC_OUT_OF_DATE",
                    "error",
                    None,
                    "PROJECT_STATUS.md does not match the registry; run `citerift-gov render-status --write`",
                )
            ]
        return []

    # ------------------------------------------------------------ transitions

    def propose(
        self,
        stage_id: str,
        target: Status,
        *,
        actor: Actor,
        reason: str,
        owner_ref: str | None = None,
        recorded_by: Actor = Actor.ENGINEERING_AGENT,
        revision: str | None = None,
        gates: dict[str, Any] | None = None,
        ci: dict[str, Any] | None = None,
        amendment: str | None = None,
        at: str | None = None,
        _baseline: Registry | None = None,
    ) -> TransitionResult:
        """Dry-run a transition. Never writes anything.

        ``_baseline`` is the registry whose errors count as pre-existing, when this registry already holds
        part of the same change (a blocker resolution, X-08)."""
        at = at or self._now()
        if future := _future_problem(at, "transition"):
            return TransitionResult(False, future)
        try:
            stage = self.stage(stage_id)
        except KeyError as exc:
            return TransitionResult(False, [Finding("STAGE_UNKNOWN", "error", stage_id, str(exc))])
        source = Status(stage["status"])
        reject = [
            Finding(c, "error", stage_id, m)
            for c, m in self._edge_problems(stage, source, target, actor, owner_ref, amendment)
        ]
        if reject:
            return TransitionResult(False, reject)

        new = copy.deepcopy(self.registry)
        ns = next(s for s in new["stages"] if s["id"] == stage_id)
        ns["status"] = target.value
        if target == Status.AUTHORIZED:
            ns["authorization"] = {"owner_ref": owner_ref, "scope": reason, "recorded_at": at}
        elif target == Status.NOT_STARTED:
            ns["authorization"] = None
        elif target == Status.IMPLEMENTED_NOT_VERIFIED:
            if revision is None:
                return TransitionResult(
                    False, [Finding("REVISION_REQUIRED", "error", stage_id, "an implementation revision is required")]
                )
            ns["implementation"] = {"revision": revision, "recorded_at": at}
        elif target == Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE:
            rev = revision or (stage["implementation"] or {}).get("revision")
            if rev is None:
                return TransitionResult(
                    False, [Finding("REVISION_REQUIRED", "error", stage_id, "a verified revision is required")]
                )
            try:
                ns["verification"] = self._build_verification(stage, rev, gates or {}, ci, at)
            except evidence.EvidenceNameError as exc:
                return TransitionResult(False, [Finding("EVIDENCE_UNREADABLE", "error", stage_id, str(exc))])
            except gitutil.GitUnavailableError as exc:
                return TransitionResult(
                    False, [Finding("REVISION_UNVERIFIABLE", "error", stage_id, f"cannot list the evidence: {exc}")]
                )
        elif target == Status.ACCEPTED_CLOSED:
            ns["acceptance"] = {
                "owner_ref": owner_ref,
                "accepted_revision": revision or stage["verification"]["revision"],
                "recorded_at": at,
                "recorded_by": recorded_by.value,
                "method": "attested",
            }
        elif target == Status.IN_PROGRESS and source in (
            Status.IMPLEMENTED_NOT_VERIFIED,
            Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE,
            Status.ACCEPTED_CLOSED,
        ):
            ns["implementation"] = None
            ns["verification"] = None
            ns["acceptance"] = None
        entry: dict[str, Any] = {
            "seq": len(new["history"]) + 1,
            "at": at,
            "stage": stage_id,
            "from": source.value,
            "to": target.value,
            "actor": actor.value,
            "recorded_by": recorded_by.value,
            "reason": reason,
            "owner_ref": owner_ref,
        }
        if amendment is not None:
            entry["amendment"] = amendment
        new["history"].append(entry)

        candidate = Orchestrator(self.root, new)
        reference = self if _baseline is None else Orchestrator(self.root, _baseline)
        before = {(f.code, f.stage, f.message) for f in errors(reference.check(include_status_doc=False))}
        findings = [
            f
            if (f.code, f.stage, f.message) not in before
            else Finding(f.code, f.severity, f.stage, f"(pre-existing) {f.message}")
            for f in candidate.check(include_status_doc=False)
        ]
        if target == Status.IN_PROGRESS and source in (Status.AUTHORIZED, Status.BLOCKED) and self.open_blockers(stage):
            findings.append(Finding("BLOCKER_OPEN", "error", stage_id, "resolve open blockers first"))
        if errors(findings):
            return TransitionResult(False, findings)
        return TransitionResult(True, findings, new)

    def _edge_problems(
        self,
        stage: StageRecord,
        source: Status,
        target: Status,
        actor: Actor,
        owner_ref: str | None,
        amendment: str | None,
    ) -> list[tuple[str, str]]:
        edge = find_edge(source, target)
        if edge is None:
            return [("TRANSITION_INVALID", f"{source} -> {target} is not a permitted transition")]
        problems = []
        if edge.owner_only:
            if actor != Actor.OWNER:
                problems.append(
                    (
                        "OWNER_DECISION_REQUIRED",
                        f"{source} -> {target} is an owner decision; actor {actor} may not take it",
                    )
                )
            if not owner_ref:
                problems.append(
                    ("OWNER_REF_REQUIRED", "an owner decision needs a reference to the owner's own statement")
                )
        elif actor not in (Actor.OWNER, stage["executor"]):
            problems.append(("ACTOR_NOT_PERMITTED", f"actor {actor} is not the executor of stage {stage['id']}"))
        if source == Status.ACCEPTED_CLOSED:
            ids = {a["id"]: a for a in stage["amendments"]}
            if amendment is None or amendment not in ids or ids[amendment]["kind"] != "correction":
                problems.append(
                    ("AMENDMENT_REQUIRED", "reopening an accepted stage requires a recorded correction amendment")
                )
        return problems

    def _build_verification(
        self, stage: StageRecord, revision: str, gates: dict[str, Any], ci: dict[str, Any] | None, at: str
    ) -> dict[str, Any]:
        artifacts = []
        for rel in self._artifacts_for(stage):
            path = self.root / rel
            if path.is_file():
                artifacts.append({"path": rel, "sha256": evidence.sha256_file(path)})
        report_rel = self._test_report_for(stage)
        report = None
        if report_rel and (self.root / report_rel).is_file():
            report = {"path": report_rel, "sha256": evidence.sha256_file(self.root / report_rel)}
        record: dict[str, Any] = {
            "revision": revision,
            "recorded_at": at,
            "artifacts": artifacts,
            "test_report": report,
            "evidence_manifest": evidence.manifest(self.root, stage["verification_dir"]),
            "definition_sha256": self._definition_sha256(stage),
            "gates": gates,
        }
        if ci is not None:
            record["ci"] = ci
        return record

    def apply(self, result: TransitionResult) -> None:
        if not result.allowed or result.registry is None:
            raise GovernanceError(errors(result.findings))
        self.registry = result.registry
        self.write()

    def transition(self, stage_id: str, target: Status, **kwargs: Any) -> TransitionResult:
        result = self.propose(stage_id, target, **kwargs)
        self.apply(result)
        return result

    # ------------------------------------------------- blockers and amendments

    def _mutate(self, change: Any) -> list[Finding]:
        new = copy.deepcopy(self.registry)
        change(new)
        candidate = Orchestrator(self.root, new)
        before = {(f.code, f.stage, f.message) for f in errors(self.check(include_status_doc=False))}
        introduced = [
            f for f in errors(candidate.check(include_status_doc=False)) if (f.code, f.stage, f.message) not in before
        ]
        if introduced:
            raise GovernanceError(introduced)
        self.registry = new
        self.write()
        return candidate.check(include_status_doc=False)

    def add_blocker(self, stage_id: str, description: str, at: str | None = None) -> str:
        stage = self.stage(stage_id)
        bid = f"B-{stage_id}-{len(stage['blockers']) + 1:03d}"
        record = {
            "id": bid,
            "description": description,
            "opened_at": at or self._now(after_history=True),
            "resolved_at": None,
            "resolution": None,
        }
        self._mutate(lambda r: next(s for s in r["stages"] if s["id"] == stage_id)["blockers"].append(record))
        return bid

    def resolve_blocker(
        self,
        stage_id: str,
        blocker_id: str,
        resolution: str,
        at: str | None = None,
        *,
        actor: Actor = Actor.ENGINEERING_AGENT,
        recorded_by: Actor = Actor.ENGINEERING_AGENT,
    ) -> bool:
        """Resolve a blocker. Resolving the last open blocker of a BLOCKED stage also records
        BLOCKED -> IN_PROGRESS in the same change, so no inconsistent state is ever written.
        Returns True when that transition was recorded."""
        stage = self.stage(stage_id)
        if not any(b["id"] == blocker_id and b["resolved_at"] is None for b in stage["blockers"]):
            raise GovernanceError([Finding("BLOCKER_UNKNOWN", "error", stage_id, f"no open blocker {blocker_id}")])
        # Strictly after the last entry: a blocker resolved in the second of the BLOCKED entry would not
        # count as open at that entry (X-08).
        at = at or self._now(after_history=True)

        def change(r: Registry) -> None:
            for b in next(s for s in r["stages"] if s["id"] == stage_id)["blockers"]:
                if b["id"] == blocker_id:
                    b["resolved_at"] = at
                    b["resolution"] = resolution

        others_open = [b for b in self.open_blockers(stage) if b["id"] != blocker_id]
        if stage["status"] != Status.BLOCKED or others_open:
            self._mutate(change)
            return False
        new = copy.deepcopy(self.registry)
        change(new)
        result = Orchestrator(self.root, new).propose(
            stage_id,
            Status.IN_PROGRESS,
            actor=actor,
            recorded_by=recorded_by,
            reason=f"all blockers resolved ({blocker_id}: {resolution})",
            at=at,
            _baseline=self.registry,
        )
        self.apply(result)
        return True

    def add_amendment(
        self,
        stage_id: str,
        *,
        kind: str,
        reason: str,
        evidence_refs: list[str],
        owner_ref: str,
        revision: str | None = None,
        test_report: str | None = None,
        at: str | None = None,
    ) -> str:
        stage = self.stage(stage_id)
        if stage["status"] != Status.ACCEPTED_CLOSED:
            raise GovernanceError(
                [Finding("AMENDMENT_NOT_APPLICABLE", "error", stage_id, "amendments apply to accepted stages only")]
            )
        aid = f"A-{stage_id}-{len(stage['amendments']) + 1:03d}"
        report = None
        if test_report is not None:
            if not (evidence.inside(self.root, test_report) and (self.root / test_report).is_file()):
                raise GovernanceError(
                    [Finding("EVIDENCE_MISSING", "error", stage_id, f"test report {test_report} is not a file")]
                )
            report = {"path": test_report, "sha256": evidence.sha256_file(self.root / test_report)}
        record = {
            "id": aid,
            "kind": kind,
            "reason": reason,
            "evidence": evidence_refs,
            "owner_ref": owner_ref,
            "revision": revision,
            "test_report": report,
            "recorded_at": at or self._now(),
        }
        self._mutate(lambda r: next(s for s in r["stages"] if s["id"] == stage_id)["amendments"].append(record))
        return aid

    # ----------------------------------------------------------------- output

    def write(self) -> None:
        text = json.dumps(self.registry, indent=2, ensure_ascii=False) + "\n"
        _atomic_write(self.root / REGISTRY_PATH, text)
        _atomic_write(self.root / STATUS_DOC_PATH, self.render_status())

    def render_status(self) -> str:
        reg = self.registry
        lines = [
            "# CITERIFT Project Status",
            "",
            "<!-- GENERATED FILE: do not edit. Source: governance/stage_registry.json."
            " Regenerate with `citerift-gov render-status --write`. CI fails if this file is stale. -->",
            "",
            f"Repository: `{reg['project']['repository']}`. Owner: {reg['project']['owner']['display_name']}.",
            "",
            "Technical verification, owner acceptance and authorization of the next stage"
            " are three separate decisions.",
            "Only the owner can accept a stage or authorize one.",
            "",
            "## Stages",
            "",
            "| Stage | Name | Executor | Depends on | Status | Verified revision | Accepted |",
            "|---|---|---|---|---|---|---|",
        ]
        for s in self.stages:
            ver = s["verification"]["revision"][:12] if s["verification"] else "-"
            acc = "yes" if s["acceptance"] else "no"
            deps = ", ".join(s["depends_on"]) or "-"
            lines.append(f"| {s['id']} | {s['name']} | {s['executor']} | {deps} | `{s['status']}` | {ver} | {acc} |")
        lines += ["", "## Next actions", ""]
        lines += [f"- {a}" for a in self.next_actions()]
        blockers = [(s["id"], b) for s in self.stages for b in self.open_blockers(s)]
        lines += ["", "## Open blockers", ""]
        lines += [f"- Stage {sid} {b['id']}: {b['description']}" for sid, b in blockers] or ["- None recorded."]
        notes = [(s["id"], s["notes"]) for s in self.stages if s.get("notes")]
        if notes:
            lines += ["", "## Stage notes", ""]
            lines += [f"- Stage {sid}: {n}" for sid, n in notes]
        lines += ["", "## Recent history", ""]
        for h in reg["history"][-10:]:
            ref = f" (owner ref `{h['owner_ref']}`)" if h["owner_ref"] else ""
            lines.append(
                f"- {h['at']} stage {h['stage']}: {h['from']} -> {h['to']} by {h['actor']}{ref}. {h['reason']}"
            )
        if not reg["history"]:
            lines.append("- No transitions recorded.")
        lines += [
            "",
            "Decisions: [DECISIONS.md](DECISIONS.md). Risks and known defects: [RISKS.md](RISKS.md).",
            "Changes: [CHANGELOG.md](CHANGELOG.md). Rules: [GOVERNANCE.md](GOVERNANCE.md).",
            "",
        ]
        return "\n".join(lines)

    def handoff_summary(self, stage_id: str) -> str:
        s = self.stage(stage_id)
        lines = [f"# Handoff summary: stage {s['id']} ({s['name']})", "", f"- Status: `{s['status']}`"]
        if s["authorization"]:
            lines.append(
                f"- Authorized by owner ref `{s['authorization']['owner_ref']}` at {s['authorization']['recorded_at']}"
            )
        if s["implementation"]:
            lines.append(f"- Implementation revision: `{s['implementation']['revision']}`")
        v = s["verification"]
        if v:
            lines.append(f"- Verified revision: `{v['revision']}` (recorded {v['recorded_at']})")
            if v.get("ci"):
                lines.append(f"- CI run: {v['ci']['run_url']} ({v['ci']['conclusion']})")
            lines.append("- Evidence:")
            lines += [f"  - `{a['path']}` sha256 `{a['sha256'][:16]}...`" for a in v["artifacts"]]
            if v["test_report"]:
                lines.append(f"  - `{v['test_report']['path']}` sha256 `{v['test_report']['sha256'][:16]}...`")
            lines.append("- Gates:")
            lines += [f"  - {g}: {r['result']} ({', '.join(r['evidence'])})" for g, r in sorted(v["gates"].items())]
        if s["acceptance"]:
            a = s["acceptance"]
            lines.append(f"- Accepted by owner ref `{a['owner_ref']}` ({a['method']}) for `{a['accepted_revision']}`")
        else:
            lines.append("- Owner acceptance: not recorded")
        found = [f for f in self.check() if f.stage in (stage_id, None)]
        lines.append(f"- Consistency check: {len(errors(found))} errors, {len(found) - len(errors(found))} warnings")
        lines += [f"  - {f}" for f in found]
        lines.append("- Successor authorization: separate owner decision; not granted by this handoff")
        return "\n".join(lines) + "\n"

    def recover(self) -> dict[str, Any]:
        """Reconstruct project state from the repository alone."""
        decisions, _ = memory.check_decisions(self.root / DECISIONS_PATH)
        risks, _ = memory.check_risks(self.root / RISKS_PATH)
        findings = self.check()
        by = {st: [s["id"] for s in self.stages if s["status"] == st] for st in Status}
        try:
            uncommitted = gitutil.dirty_paths(self.root) if gitutil.is_repository(self.root) else None
        except gitutil.GitUnavailableError as exc:
            # A damaged index must not hide the rest of the state (Y-11).
            findings.append(Finding("REVISION_UNVERIFIABLE", "error", None, f"cannot list uncommitted changes: {exc}"))
            uncommitted = None
        return {
            "repository": self.registry["project"]["repository"],
            "head": gitutil.head(self.root),
            "branch": gitutil.branch(self.root),
            "uncommitted_changes": uncommitted,
            "authoritative_revisions": {
                s["id"]: {
                    "verified": s["verification"]["revision"] if s["verification"] else None,
                    "accepted": s["acceptance"]["accepted_revision"] if s["acceptance"] else None,
                }
                for s in self.stages
                if s["verification"] or s["acceptance"]
            },
            "completed_and_accepted": by[Status.ACCEPTED_CLOSED],
            "verified_awaiting_owner_acceptance": by[Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE],
            "open": {
                st.value: by[st]
                for st in (Status.AUTHORIZED, Status.IN_PROGRESS, Status.BLOCKED, Status.IMPLEMENTED_NOT_VERIFIED)
                if by[st]
            },
            "not_started": by[Status.NOT_STARTED],
            "open_blockers": [{"stage": s["id"], **b} for s in self.stages for b in self.open_blockers(s)],
            "open_risks_and_limitations": [
                {
                    "id": r.id,
                    "title": r.title,
                    "kind": r.get("Kind"),
                    "severity": r.get("Severity"),
                    "stage": r.get("Stage"),
                }
                for r in risks
                if r.get("Status") == "open"
            ],
            "pending_decisions": [
                {"id": d.id, "title": d.title} for d in decisions if d.get("Status") in ("proposed", "pending-owner")
            ],
            "recent_changes": self.registry["history"][-5:],
            "next_actions": self.next_actions(),
            "consistency": {
                "errors": [f.to_dict() for f in errors(findings)],
                "warnings": [f.to_dict() for f in findings if f.severity == "warning"],
            },
        }


def _atomic_write(path: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
