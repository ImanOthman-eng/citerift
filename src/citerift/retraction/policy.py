"""Evidence sets and the conservative projection reducer (SPECIFICATION.md 11.1).

The reducer is a pure function of an evidence set. It never reads row order, ids or dates other than
through ``definitely_before``, so it cannot implement latest-row-wins or greatest-date-wins, and it never
produces a value outside the v1 ``retraction_status`` enumeration.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from citerift.retraction.dates import TemporalEvidence, definitely_before

POLICY_VERSION = "citerift-rde-policy/1.0.0"
RW_ORIGIN = "retraction-watch"
COMPARISON_FIELDS = (
    "lookup_state",
    "retraction_status.status",
    "retraction_status.value",
    "retraction_date.status",
    "retraction_date.value",
    "support.observations",
    "support.origins",
    "identity.status",
    "notice_links",
    "definite_orderings",
)
REASON_TEXT = {
    "INDEX_UNAVAILABLE": "The index could not be opened; nothing is known from it.",
    "NO_SOURCE_IN_VIEW": "No checked source remains in this hypothetical view.",
    "IDENTITY_AMBIGUOUS": "The identifiers point to more than one work in the checked source; no work is chosen.",
    "NOTICE_ONLY": "The identifier is recorded only as a notice; this says nothing about an original paper.",
    "COVERAGE_GAP_RELEVANT_ROWS": "Quarantined rows or invalid identifiers that may concern this work exist.",
    "NOT_FOUND_IN_CHECKED_SOURCES": "No record in the checked sources; this is not evidence of no retraction.",
    "REINSTATEMENT_UNLINKED": "A reinstatement is recorded without evidence of which event it supersedes.",
    "SOURCE_RECORDED_RETRACTION": "The checked source records a retraction of this original.",
    "CONFLICT_NOT_MATERIAL": "A type conflict on another notice does not change the recorded retraction.",
    "SOURCE_TYPE_CONFLICT": "Sources assert different types for the same notice and original.",
    "MIXED_CURRENT_EFFECT": "Several non-retraction event types; no single current effect is established.",
    "SOURCE_RECORDED_TYPE": "The checked source records this event type for this original.",
    "DATE_NOT_IN_CHECKED_SOURCES": "No Retraction Watch notice date is available in this view.",
    "DATE_UNKNOWN": "The notice date is missing, unparseable or not a calendar date.",
    "MULTIPLE_RETRACTION_DATES": "Several retraction events report different dates.",
    "DATE_PRECISION_UNJUSTIFIED": "Day 1 in Retraction Watch can encode an unknown day, a month range, a season or a "
    "volume, so the reported date has no justified bounds.",
}


@dataclass(frozen=True)
class TypedAssertion:
    assertion_id: str
    origin: str
    channel: str
    type: str | None
    notice_key: str | None
    anchor: str
    source_ref: dict[str, Any]
    event_id: str | None = None
    notice_date: TemporalEvidence | None = None
    bridged: bool = False
    notice_ambiguous: bool = False
    depends_on: tuple[str, ...] = ()

    @property
    def proposition(self) -> str:
        return self.notice_key or f"solo:{self.assertion_id}"


@dataclass(frozen=True)
class EvidenceSet:
    state: str
    identity: str
    anchor: str | None
    assertions: tuple[TypedAssertion, ...]
    checked_sources: tuple[dict[str, Any], ...]
    supersessions: tuple[tuple[str, str], ...] = ()
    relevant_gap: bool = False
    collapse: bool = False
    notes: tuple[str, ...] = field(default=())

    @property
    def rw_events(self) -> tuple[TypedAssertion, ...]:
        return tuple(a for a in self.assertions if a.event_id is not None)


def _assertion(status: str, value: Any, reasons: list[str], provenance: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {"status": status, "value": value}
    if provenance:
        out["provenance"] = provenance
    if status in ("uncertain", "unavailable") or (status == "conflicting"):
        out["reason"] = " ".join(REASON_TEXT.get(r, r) for r in reasons) or "No reason recorded."
    return out


def _provenance(assertions: list[TypedAssertion]) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for a in assertions:
        key = repr(sorted(a.source_ref.items()))
        seen.setdefault(key, a.source_ref)
    return [seen[k] for k in sorted(seen)]


def reduce(ev: EvidenceSet) -> dict[str, Any]:
    """Return the projection: v1 ``retraction_status`` and ``retraction_date`` plus basis and comparison data."""
    basis: dict[str, Any] = {
        "scope": "checked_sources",
        "policy_version": POLICY_VERSION,
        "reasons": [],
        "supporting_assertions": [],
        "origins": [],
        "conflict_groups": [],
    }
    out: dict[str, Any] = {"retraction_status": None, "retraction_date": None, "basis": basis}
    rw = ev.rw_events
    notice_links = sorted({a.notice_key for a in rw if a.notice_key}) if ev.state == "matched" else []
    orderings = (
        sorted(
            [a.event_id, b.event_id]
            for a in rw
            for b in rw
            if a is not b and a.event_id and b.event_id and definitely_before(a.notice_date, b.notice_date)
        )
        if ev.state == "matched"
        else []
    )
    compare: dict[str, Any] = {
        "lookup_state": ev.state,
        "retraction_status.status": None,
        "retraction_status.value": None,
        "retraction_date.status": None,
        "retraction_date.value": None,
        "support.observations": 0,
        "support.origins": [],
        "identity.status": ev.identity,
        "notice_links": notice_links,
        "definite_orderings": orderings,
    }
    out["compare"] = compare

    def finish(status: str, value: Any, reasons: list[str], provenance: list[dict[str, Any]]) -> dict[str, Any]:
        basis["reasons"] = reasons
        out["retraction_status"] = _assertion(status, value, reasons, provenance)
        compare["retraction_status.status"] = status
        compare["retraction_status.value"] = value
        return out

    if ev.state == "invalid_query":
        compare["identity.status"] = "none"
        return out
    if ev.state == "unavailable" or not ev.checked_sources:
        compare.update({"lookup_state": "unavailable", "identity.status": "none", "notice_links": []})
        return finish(
            "unavailable", None, ["INDEX_UNAVAILABLE" if ev.state == "unavailable" else "NO_SOURCE_IN_VIEW"], []
        )
    if ev.state == "ambiguous_identity":
        return finish("uncertain", None, ["IDENTITY_AMBIGUOUS"], [])
    if ev.state == "notice_only":
        return finish("uncertain", None, ["NOTICE_ONLY"], [])
    if ev.state == "no_record":
        if ev.relevant_gap:
            return finish("uncertain", None, ["COVERAGE_GAP_RELEVANT_ROWS"], [])
        # retraction_date stays absent: no record means no date can be stated (v1 rule Y-12).
        return finish(
            "uncertain", "not_found_in_checked_sources", ["NOT_FOUND_IN_CHECKED_SOURCES"], list(ev.checked_sources)
        )
    if ev.state != "matched":
        raise ValueError(f"unknown lookup state {ev.state!r}")

    typed = [a for a in ev.assertions if a.type is not None]
    props: dict[str, set[str]] = {}
    for a in typed:
        props.setdefault(a.proposition, set()).add(a.type or "")
    conflict = {k for k, types in props.items() if len(types) > 1}
    clear = [a for a in typed if a.proposition not in conflict]
    basis["conflict_groups"] = [
        {
            "proposition": k,
            "types": sorted(props[k]),
            "assertions": sorted(a.assertion_id for a in typed if a.proposition == k),
        }
        for k in sorted(conflict)
    ]
    reins = [a for a in typed if a.type == "reinstated"]
    others = {a.type for a in typed} - {"reinstated"}
    value: str | None = None
    support: list[TypedAssertion] = []
    if reins and others:
        by_event = {a.event_id: a for a in rw}
        linked: dict[str, str] = {}
        for r_id, t_id in ev.supersessions:
            r, t = by_event.get(r_id), by_event.get(t_id)
            if r is not None and t is not None and definitely_before(t.notice_date, r.notice_date):
                linked[r_id] = t_id
        superseded = set(linked.values())
        remaining = [a for a in typed if a.type == "retracted" and a.event_id not in superseded]
        if all(a.event_id in linked for a in reins) and not remaining:
            value, status, reasons = "reinstated", "verified_fact", ["SOURCE_RECORDED_TYPE"]
            support = [a for a in clear if a.type == "reinstated"]
            if not support:  # every reinstatement sits in a type conflict: nothing clear supports the value
                value, status, reasons = None, "uncertain", ["REINSTATEMENT_UNLINKED"]
        else:
            status, reasons = "uncertain", ["REINSTATEMENT_UNLINKED"]
    elif any(a.type == "retracted" for a in clear):
        value, status = "retracted", "verified_fact"
        support = [a for a in clear if a.type == "retracted"]
        reasons = ["SOURCE_RECORDED_RETRACTION"] + (["CONFLICT_NOT_MATERIAL"] if conflict else [])
    elif conflict:
        status, reasons = "conflicting", ["SOURCE_TYPE_CONFLICT"]
    else:
        ctypes = {a.type for a in clear}
        if len(ctypes) == 1:
            value, status, reasons = ctypes.pop(), "verified_fact", ["SOURCE_RECORDED_TYPE"]
            support = [a for a in clear if a.type == value]
        else:
            status, reasons = "uncertain", ["MIXED_CURRENT_EFFECT"]
    if value is not None and ev.relevant_gap:
        value, status, support = None, "uncertain", []
        reasons = [*reasons, "COVERAGE_GAP_RELEVANT_ROWS"]
    if status == "conflicting":
        by_type: dict[str, list[TypedAssertion]] = {}
        for a in typed:
            if a.proposition in conflict:
                by_type.setdefault(a.type or "", []).append(a)
        finish(status, None, reasons, [])
        out["retraction_status"]["alternatives"] = [
            {"value": t, "provenance": _provenance(by_type[t])} for t in sorted(by_type)
        ]
    else:
        finish(status, value, reasons, _provenance(support) if status == "verified_fact" else [])
    origins = sorted({a.origin for a in support})
    basis["supporting_assertions"] = sorted(a.assertion_id for a in support)
    basis["origins"] = origins
    compare["support.origins"] = origins
    compare["support.observations"] = len(origins) if ev.collapse else len(support)
    if value == "retracted":
        out["retraction_date"] = _retraction_date([a for a in support if a.event_id is not None], basis)
        compare["retraction_date.status"] = out["retraction_date"]["status"]
        compare["retraction_date.value"] = out["retraction_date"]["value"]
    return out


def _retraction_date(events: list[TypedAssertion], basis: dict[str, Any]) -> dict[str, Any]:
    def uncertain(value: str | None, reason: str) -> dict[str, Any]:
        basis["reasons"].append(reason)
        return {"status": "uncertain", "value": value, "reason": REASON_TEXT[reason]}

    if not events:
        return uncertain(None, "DATE_NOT_IN_CHECKED_SOURCES")
    dates = [a.notice_date for a in events]
    if any(d is None or d.reported_calendar is None for d in dates):
        return uncertain(None, "DATE_UNKNOWN")
    reported = {d.reported_calendar for d in dates if d is not None}
    if len(reported) > 1:
        return uncertain(None, "MULTIPLE_RETRACTION_DATES")
    value = reported.pop()
    if all(d is not None and d.bounded for d in dates):
        return {"status": "verified_fact", "value": value, "provenance": _provenance(events)}
    return uncertain(value, "DATE_PRECISION_UNJUSTIFIED")


def with_assertions(ev: EvidenceSet, assertions: list[TypedAssertion], **changes: Any) -> EvidenceSet:
    return replace(ev, assertions=tuple(assertions), **changes)
