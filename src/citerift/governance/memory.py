"""Persistent Project Memory: structured records kept in DECISIONS.md and RISKS.md.

Both files are written for humans. Each entry starts with a level-2 heading
``## D-001 — Title`` (or ``R-001``) followed by ``- Field: value`` lines, so the
records can be checked mechanically without a second, duplicated store.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

DECISION_STATUSES = frozenset({"proposed", "pending-owner", "accepted", "rejected", "superseded"})
RISK_STATUSES = frozenset({"open", "mitigated", "accepted", "closed"})
RISK_SEVERITIES = frozenset({"critical", "high", "medium", "low"})
RISK_KINDS = frozenset({"risk", "defect", "limitation"})

_HEADING = re.compile(r"^## ([DR]-\d{3}) — (.+?)\s*$")
_FIELD = re.compile(r"^- ([A-Z][A-Za-z-]+): (.+?)\s*$")


@dataclass
class Entry:
    id: str
    title: str
    line: int
    fields: dict[str, str] = field(default_factory=dict)

    def get(self, name: str) -> str:
        return self.fields.get(name, "").strip()

    def refs(self, name: str) -> list[str]:
        value = self.get(name)
        if not value or value.lower() == "none":
            return []
        return [v.strip() for v in value.split(",") if v.strip()]


@dataclass(frozen=True)
class MemoryProblem:
    code: str
    file: str
    message: str


def parse_entries(text: str, prefix: str) -> list[Entry]:
    entries: list[Entry] = []
    current: Entry | None = None
    in_fields = False
    for number, line in enumerate(text.splitlines(), start=1):
        heading = _HEADING.match(line)
        if heading and heading.group(1).startswith(prefix):
            current = Entry(heading.group(1), heading.group(2), number)
            entries.append(current)
            in_fields = True
            continue
        if line.startswith("## "):
            current = None
            continue
        if current is None or not in_fields:
            continue
        m = _FIELD.match(line)
        if m:
            current.fields[m.group(1)] = m.group(2)
        elif line.strip():
            in_fields = False
    return entries


def check_decisions(path: Path) -> tuple[list[Entry], list[MemoryProblem]]:
    name = path.name
    if not path.is_file():
        return [], [MemoryProblem("MEMORY_FILE_MISSING", name, f"{name} does not exist")]
    entries = parse_entries(path.read_text(encoding="utf-8"), "D-")
    problems: list[MemoryProblem] = []
    by_id: dict[str, Entry] = {}
    for e in entries:
        if e.id in by_id:
            problems.append(MemoryProblem("DECISION_DUPLICATE_ID", name, f"{e.id} appears twice"))
        by_id[e.id] = e
    accepted_by_topic: dict[str, list[str]] = {}
    for e in entries:
        status = e.get("Status")
        if status not in DECISION_STATUSES:
            problems.append(MemoryProblem("DECISION_INVALID_STATUS", name, f"{e.id} has status '{status}'"))
        topic = e.get("Topic")
        if not topic:
            problems.append(MemoryProblem("DECISION_NO_TOPIC", name, f"{e.id} has no Topic"))
        if status == "accepted" and topic:
            accepted_by_topic.setdefault(topic, []).append(e.id)
        for ref in e.refs("Supersedes"):
            target = by_id.get(ref)
            if target is None:
                problems.append(MemoryProblem("DECISION_BAD_REFERENCE", name, f"{e.id} supersedes unknown {ref}"))
            elif target.get("Status") != "superseded" or e.id not in target.refs("Superseded-by"):
                problems.append(
                    MemoryProblem(
                        "DECISION_SUPERSESSION_MISMATCH",
                        name,
                        f"{e.id} supersedes {ref}, but {ref} is not marked superseded by {e.id}",
                    )
                )
        if status == "superseded":
            successors = e.refs("Superseded-by")
            if not successors or any(s not in by_id for s in successors):
                problems.append(
                    MemoryProblem(
                        "DECISION_BAD_REFERENCE",
                        name,
                        f"{e.id} is superseded but names no existing successor",
                    )
                )
    for topic, ids in accepted_by_topic.items():
        if len(ids) > 1:
            problems.append(
                MemoryProblem(
                    "DECISION_CONTRADICTION",
                    name,
                    f"topic '{topic}' has more than one accepted decision: {', '.join(ids)}",
                )
            )
    return entries, problems


def check_risks(path: Path) -> tuple[list[Entry], list[MemoryProblem]]:
    name = path.name
    if not path.is_file():
        return [], [MemoryProblem("MEMORY_FILE_MISSING", name, f"{name} does not exist")]
    entries = parse_entries(path.read_text(encoding="utf-8"), "R-")
    problems: list[MemoryProblem] = []
    seen: set[str] = set()
    for e in entries:
        if e.id in seen:
            problems.append(MemoryProblem("RISK_DUPLICATE_ID", name, f"{e.id} appears twice"))
        seen.add(e.id)
        for fname, allowed in (
            ("Status", RISK_STATUSES),
            ("Severity", RISK_SEVERITIES),
            ("Kind", RISK_KINDS),
        ):
            if e.get(fname) not in allowed:
                problems.append(
                    MemoryProblem("RISK_INVALID_FIELD", name, f"{e.id} has invalid {fname} '{e.get(fname)}'")
                )
        if not re.fullmatch(r"\d{2}(, ?\d{2})*|project", e.get("Stage")):
            problems.append(MemoryProblem("RISK_INVALID_FIELD", name, f"{e.id} has invalid Stage '{e.get('Stage')}'"))
    return entries, problems


def open_critical_defects(risks: list[Entry], stage_id: str) -> list[Entry]:
    return [
        r
        for r in risks
        if r.get("Kind") == "defect"
        and r.get("Severity") == "critical"
        and r.get("Status") == "open"
        and stage_id in r.refs("Stage")
    ]
