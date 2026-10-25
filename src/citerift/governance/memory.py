"""Persistent Project Memory: structured records kept in DECISIONS.md and RISKS.md.

Both files are written for humans. Each entry starts with a level-2 heading
``## D-001 — Title`` (or ``R-001``) followed by ``- Field: value`` lines, so the
records can be checked mechanically without a second, duplicated store.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

DECISION_STATUSES = frozenset({"proposed", "pending-owner", "accepted", "rejected", "superseded"})
RISK_STATUSES = frozenset({"open", "mitigated", "accepted", "closed"})
RISK_SEVERITIES = frozenset({"critical", "high", "medium", "low"})
RISK_KINDS = frozenset({"risk", "defect", "limitation"})

_HEADING = re.compile(r"^## ([DR]-\d{3}) — (.+?)\s*$")
# Anything that looks like an entry heading but is not exactly the form above (another dash,
# another heading level, missing digits) is reported instead of being skipped (F-06).
_HEADING_LIKE = re.compile(r"^\s{0,3}#+\s*\**\s*([DR])\s*-?\s*\d+")
_FIELD = re.compile(r"^- ([A-Z][A-Za-z-]+): (.+?)\s*$")
# Fields that only an entry carries. One of them outside a parsed entry means the entry's heading
# was not recognized (another dash, a setext or HTML heading, ...), so it is reported (V-06).
_ENTRY_FIELDS = frozenset({"Status", "Severity", "Kind", "Topic"})
_SEPARATORS = re.compile(r"[\s_\-\u2010-\u2015\u2212]+")


@dataclass
class Entry:
    id: str
    title: str
    line: int
    fields: dict[str, str] = field(default_factory=dict)
    duplicate_fields: list[str] = field(default_factory=list)

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


def malformed_headings(text: str, prefix: str) -> list[tuple[int, str]]:
    """Lines that look like an entry heading for ``prefix`` but do not parse as one."""
    out = []
    for number, line in enumerate(text.splitlines(), start=1):
        m = _HEADING_LIKE.match(line)
        if m and m.group(1) == prefix[0] and not _HEADING.match(line):
            out.append((number, line.strip()))
    return out


def _structure_problems(entries: list[Entry], text: str, prefix: str, name: str) -> list[MemoryProblem]:
    problems = [
        MemoryProblem("MEMORY_MALFORMED", name, f"line {n}: heading is not '## {prefix}NNN — Title': {line!r}")
        for n, line in malformed_headings(text, prefix)
    ]
    problems += [
        MemoryProblem("MEMORY_MALFORMED", name, f"line {n}: field outside any recognized entry heading: {line!r}")
        for n, line in orphan_fields(text, prefix)
    ]
    for e in entries:
        for f in e.duplicate_fields:
            problems.append(MemoryProblem("MEMORY_MALFORMED", name, f"{e.id} sets field '{f}' more than once"))
    return problems


def normalize_topic(topic: str) -> str:
    """Compatibility-normalized, case-folded, with every run of spaces, hyphens or underscores as one hyphen."""
    return _SEPARATORS.sub("-", unicodedata.normalize("NFKC", topic)).strip("-").casefold()


def orphan_fields(text: str, prefix: str) -> list[tuple[int, str]]:
    """Entry field lines that do not belong to any parsed entry heading."""
    out = []
    attached = False
    for number, line in enumerate(text.splitlines(), start=1):
        heading = _HEADING.match(line)
        if heading and heading.group(1).startswith(prefix):
            attached = True
            continue
        m = _FIELD.match(line)
        if m:
            if not attached and m.group(1) in _ENTRY_FIELDS:
                out.append((number, line.strip()))
        elif line.strip():
            attached = False
    return out


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
            if m.group(1) in current.fields:
                current.duplicate_fields.append(m.group(1))
            current.fields[m.group(1)] = m.group(2)
        elif line.strip():
            in_fields = False
    return entries


def check_decisions(path: Path) -> tuple[list[Entry], list[MemoryProblem]]:
    name = path.name
    if not path.is_file():
        return [], [MemoryProblem("MEMORY_FILE_MISSING", name, f"{name} does not exist")]
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [], [MemoryProblem("MEMORY_UNREADABLE", name, f"{name} cannot be read as UTF-8 text: {exc}")]
    entries = parse_entries(text, "D-")
    problems = _structure_problems(entries, text, "D-", name)
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
            accepted_by_topic.setdefault(normalize_topic(topic), []).append(e.id)
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
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [], [MemoryProblem("MEMORY_UNREADABLE", name, f"{name} cannot be read as UTF-8 text: {exc}")]
    entries = parse_entries(text, "R-")
    problems = _structure_problems(entries, text, "R-", name)
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
    """Open critical defects that block ``stage_id``; a defect with ``Stage: project`` blocks every stage."""
    return [
        r
        for r in risks
        if r.get("Kind") == "defect"
        and r.get("Severity") == "critical"
        and r.get("Status") == "open"
        and (stage_id in r.refs("Stage") or r.get("Stage") == "project")
    ]
