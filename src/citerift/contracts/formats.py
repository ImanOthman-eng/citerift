"""Format and JSON-parsing rules shared by every CITERIFT validator.

JSON Schema treats ``format`` as an annotation unless a validator is given a
format checker, and the ``date-time`` checker in ``jsonschema`` depends on an
optional library. CITERIFT schemas rely on ``date-time`` to reject impossible
calendar values (for example 2026-02-31), so the checker here implements it
with the standard library and every CITERIFT validator passes it explicitly.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any

from jsonschema import FormatChecker

# The shape the CITERIFT schemas allow: UTC, a trailing Z, optional fraction.
_UTC_TIMESTAMP = re.compile(r"\A([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2})(\.[0-9]{1,6})?Z\Z")
_PARTIAL_DATE = re.compile(r"\A([0-9]{4})(?:-([0-9]{2})(?:-([0-9]{2}))?)?\Z")


def parse_utc_timestamp(value: str) -> datetime | None:
    """Return the instant ``value`` names, or None if it is not a valid UTC timestamp."""
    m = _UTC_TIMESTAMP.match(value)
    if not m:
        return None
    try:
        base = datetime.strptime(m.group(1), "%Y-%m-%dT%H:%M:%S").replace(tzinfo=UTC)
    except ValueError:
        return None
    fraction = m.group(2)
    if fraction:
        base = base.replace(microsecond=int(fraction[1:].ljust(6, "0")))
    return base


def is_calendar_partial_date(value: str) -> bool:
    """True for a real year, year-month or year-month-day (no 2020-02-30)."""
    m = _PARTIAL_DATE.match(value)
    if not m:
        return False
    year, month, day = m.groups()
    try:
        datetime(int(year), int(month or 1), int(day or 1))
    except ValueError:
        return False
    return True


FORMAT_CHECKER = FormatChecker(formats=())


@FORMAT_CHECKER.checks("date-time")
def _is_date_time(instance: object) -> bool:
    # Non-strings are left to the "type" keyword, as the specification requires.
    return not isinstance(instance, str) or parse_utc_timestamp(instance) is not None


class DuplicateKeyError(ValueError):
    pass


def _reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise DuplicateKeyError(f"duplicate JSON key {key!r}")
        out[key] = value
    return out


def loads_strict(text: str) -> Any:
    """Parse JSON, rejecting duplicate object keys (the stdlib keeps the last one silently)."""
    return json.loads(text, object_pairs_hook=_reject_duplicates)
