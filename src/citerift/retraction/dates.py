"""Temporal evidence for Retraction Watch date fields (SPECIFICATION.md section 7.2 and 7.3).

A date in the CSV is a reported calendar value with a source convention, not an observed instant. Bounds
are given only when the source's own precision justifies them; everything else stays unknown.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from typing import Any

_SHAPES = (
    re.compile(r"([0-9]{1,2})/([0-9]{1,2})/([0-9]{4}) ([0-9]{1,2}):([0-9]{2})", re.ASCII),
    re.compile(r"([0-9]{1,2})/([0-9]{1,2})/([0-9]{4}) ([0-9]{1,2}):([0-9]{2}):([0-9]{2}) (AM|PM)", re.ASCII),
)
KINDS = ("notice_date", "original_publication_date")


@dataclass(frozen=True)
class TemporalEvidence:
    raw: str
    kind: str
    reported_calendar: str | None
    stated_precision: str
    effective_precision: str
    earliest: str | None
    latest: str | None
    convention_flags: tuple[str, ...]
    issues: tuple[str, ...]

    @property
    def bounded(self) -> bool:
        return self.earliest is not None and self.latest is not None

    def to_json(self) -> dict[str, Any]:
        return {
            "raw": self.raw,
            "kind": self.kind,
            "reported_calendar": self.reported_calendar,
            "stated_precision": self.stated_precision,
            "effective_precision": self.effective_precision,
            "earliest": self.earliest,
            "latest": self.latest,
            "convention_flags": list(self.convention_flags),
            "issues": list(self.issues),
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> TemporalEvidence:
        return cls(
            raw=data["raw"],
            kind=data["kind"],
            reported_calendar=data["reported_calendar"],
            stated_precision=data["stated_precision"],
            effective_precision=data["effective_precision"],
            earliest=data["earliest"],
            latest=data["latest"],
            convention_flags=tuple(data["convention_flags"]),
            issues=tuple(data["issues"]),
        )

    def without_unjustified_value(self) -> TemporalEvidence:
        """The require_temporal_bounds view: a value without justified bounds is withheld."""
        if self.bounded or self.reported_calendar is None:
            return self
        return TemporalEvidence(
            self.raw,
            self.kind,
            None,
            self.stated_precision,
            self.effective_precision,
            None,
            None,
            self.convention_flags,
            (*self.issues, "WITHHELD_UNJUSTIFIED_PRECISION"),
        )


def parse_rw_date(raw: str, kind: str) -> TemporalEvidence:
    """Parse one RW date field into temporal evidence. Never raises for bad input."""
    if kind not in KINDS:
        raise ValueError(f"unknown date kind {kind!r}")
    value = raw.strip()
    if value == "":
        return TemporalEvidence(raw, kind, None, "none", "unknown", None, None, (), ("DATE_EMPTY",))
    match = None
    twelve_hour = False
    for i, shape in enumerate(_SHAPES):
        match = shape.fullmatch(value)
        if match:
            twelve_hour = i == 1
            break
    if match is None:
        return TemporalEvidence(raw, kind, None, "none", "unknown", None, None, (), ("DATE_UNPARSEABLE",))
    month, day, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
    hour, minute = int(match.group(4)), int(match.group(5))
    try:
        calendar = dt.date(year, month, day)
    except ValueError:
        return TemporalEvidence(raw, kind, None, "none", "unknown", None, None, (), ("DATE_CALENDAR_INVALID",))
    flags = []
    issues: tuple[str, ...] = ()
    if twelve_hour:
        second, half = int(match.group(6)), match.group(7)
        time_valid = 1 <= hour <= 12 and minute <= 59 and second <= 59
        midnight = (hour, minute, second, half) == (12, 0, 0, "AM")
    else:
        time_valid = hour <= 23 and minute <= 59
        midnight = (hour, minute) == (0, 0)
    if not time_valid:
        issues = ("DATE_TIME_PART_INVALID",)
    flags.append("MIDNIGHT_NOT_INSTANT" if midnight else "TIME_PART_IGNORED")
    reported = calendar.isoformat()
    if day == 1:
        flags.append("DAY_ONE_CONVENTION_POSSIBLE")
        return TemporalEvidence(raw, kind, reported, "day", "unknown", None, None, tuple(flags), issues)
    return TemporalEvidence(raw, kind, reported, "day", "day", reported, reported, tuple(flags), issues)


def definitely_before(a: TemporalEvidence | None, b: TemporalEvidence | None) -> bool:
    """A is definitely before B only when A.latest < B.earliest (both known)."""
    if a is None or b is None or a.latest is None or b.earliest is None:
        return False
    return a.latest < b.earliest


def interval_difference_days(cause: TemporalEvidence, effect: TemporalEvidence) -> tuple[int, int] | None:
    """Bounds of (cause - effect) in days: [C.earliest - E.latest, C.latest - E.earliest]; None if unknown."""
    if cause.earliest is None or cause.latest is None or effect.earliest is None or effect.latest is None:
        return None
    c0, c1 = dt.date.fromisoformat(cause.earliest), dt.date.fromisoformat(cause.latest)
    e0, e1 = dt.date.fromisoformat(effect.earliest), dt.date.fromisoformat(effect.latest)
    return (c0 - e1).days, (c1 - e0).days
