"""Evidence sets and the conservative projection reducer (SPECIFICATION.md 11.1).

The reducer is a pure function of an evidence set. It never reads row order, ids or dates other than
through ``definitely_before``, so it cannot implement latest-row-wins or greatest-date-wins, and it never
produces a value outside the v1 ``retraction_status`` enumeration.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from citerift.retraction.dates import TemporalEvidence, definitely_before

POLICY_VERSION = "citerift-rde-policy/1.2.0"
RW_ORIGIN = "retraction-watch"
UNKNOWN_ORIGIN = "unknown"
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
    "SEQUENTIAL_EVENTS_SHARE_NOTICE": "Events of different types from one source share a notice key but are "
    "definitely ordered in time, so they are a sequence of events, not a conflict.",
    "SUPPORT_ORIGIN_UNKNOWN": "The only support for this value comes from relations whose origin is unknown.",
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
    "BRIDGE_ONLY_SUPPORT": "The value would rest only on records reached through an unverified identifier link (an "
    "identifier that co-occurs with the queried one elsewhere, or the pairing given in the query); such a link is a "
    "source assertion, not proof that the records concern the same work.",
    "BRIDGED_EVIDENCE_MATERIAL": "Records reached through an unverified identifier link would change the result of "
    "the directly matched records, so it is not stated as a fact.",
    "BRIDGED_EVIDENCE_NOT_COUNTED": "Records reached through an unverified identifier link are listed but not counted "
    "as support.",
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
    dependence: str = "known"  # "unknown": may rest on another origin's notice (SPECIFICATION.md 8)

    @property
    def proposition(self) -> str:
        """(notice key, original anchor) of SPECIFICATION.md 11.1 rule 7; no notice key: its own proposition."""
        return f"{self.notice_key}|{self.anchor}" if self.notice_key else f"solo:{self.assertion_id}"


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
    """Return the projection: v1 ``retraction_status`` and ``retraction_date`` plus basis and comparison data.

    Rule 7f (SPECIFICATION.md 11.1, R-026): bridged assertions never support a value or a date. The projection is
    that of the direct assertions alone, and it stays a verified fact only when accepting the bridges would not
    change it; otherwise it is ``uncertain``, null. Sufficiency is read from the supporting assertions, not from
    ``identity``: direct support keeps its conclusion beside immaterial bridged records.
    """
    full = _reduce(ev)
    bridged = sorted(a.assertion_id for a in ev.assertions if a.bridged and a.type is not None)
    if ev.state != "matched" or not bridged:
        return full
    direct = [a for a in ev.assertions if not a.bridged]
    out = _reduce(replace(ev, assertions=tuple(direct)))
    basis, compare = out["basis"], out["compare"]
    basis["bridged_assertions"] = bridged
    for key in ("notice_links", "definite_orderings"):  # these describe the evidence, bridged records included
        compare[key] = full["compare"][key]
    status, base = out["retraction_status"], full["retraction_status"]
    bridge_only = base["status"] == "verified_fact" and set(full["basis"]["supporting_assertions"]) <= set(bridged)
    if status["status"] == "verified_fact" and base["status"] == "verified_fact" and base["value"] == status["value"]:
        basis["reasons"].append("BRIDGED_EVIDENCE_NOT_COUNTED")
        date, full_date = out["retraction_date"], full["retraction_date"] or {}
        if (
            date is not None
            and date["status"] == "verified_fact"
            and (full_date.get("status") != "verified_fact" or full_date.get("value") != date["value"])
        ):
            # A bridged retraction that reports another date bears on the date, as a conflicted one does (C-9).
            basis["reasons"].append("BRIDGED_EVIDENCE_MATERIAL")
            out["retraction_date"] = {
                "status": "uncertain",
                "value": None,
                "reason": REASON_TEXT["BRIDGED_EVIDENCE_MATERIAL"],
            }
            compare["retraction_date.status"], compare["retraction_date.value"] = "uncertain", None
        return out
    if status["status"] == "verified_fact":
        # The direct value would change if the bridges were accepted: it is not stated.
        reasons = ["BRIDGE_ONLY_SUPPORT", "BRIDGED_EVIDENCE_MATERIAL"] if bridge_only else ["BRIDGED_EVIDENCE_MATERIAL"]
        basis.update(reasons=reasons, supporting_assertions=[], origins=[])
        out["retraction_status"] = _assertion("uncertain", None, reasons, [])
        out["retraction_date"] = None
        compare.update(
            {
                "retraction_status.status": "uncertain",
                "retraction_status.value": None,
                "retraction_date.status": None,
                "retraction_date.value": None,
                "support.observations": 0,
                "support.origins": [],
            }
        )
        return out
    # The direct records settle no value (uncertain or conflicting): that result stands, and the bridged records
    # cannot settle one either.
    if not any(a.type is not None for a in direct):
        basis["reasons"] = []
    added = "BRIDGE_ONLY_SUPPORT" if bridge_only else "BRIDGED_EVIDENCE_NOT_COUNTED"
    basis["reasons"].append(added)
    out["retraction_status"] = {
        **status,
        "reason": " ".join(REASON_TEXT.get(r, r) for r in basis["reasons"]),
    }
    return out


def _reduce(ev: EvidenceSet) -> dict[str, Any]:
    """Rules 1 to 7e and 8 of SPECIFICATION.md 11.1, every assertion taken as it is (bridges included)."""
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
    prop_of, sequential = propositions(typed)
    props: dict[str, set[str]] = {}
    for a in typed:
        props.setdefault(prop_of[a.assertion_id], set()).add(a.type or "")
    conflict = {k for k, types in props.items() if len(types) > 1}
    clear = [a for a in typed if prop_of[a.assertion_id] not in conflict]
    basis["conflict_groups"] = [
        {
            "proposition": k,
            "types": sorted(props[k]),
            "assertions": sorted(a.assertion_id for a in typed if prop_of[a.assertion_id] == k),
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
        if ctypes == {"reinstated"}:
            # A reinstatement with no recorded event it supersedes cannot establish a current effect (C-11).
            status, reasons = "uncertain", ["REINSTATEMENT_UNLINKED"]
        elif len(ctypes) == 1:
            value, status, reasons = ctypes.pop(), "verified_fact", ["SOURCE_RECORDED_TYPE"]
            support = [a for a in clear if a.type == value]
        else:
            status, reasons = "uncertain", ["MIXED_CURRENT_EFFECT"]
    if sequential:
        reasons = [*reasons, "SEQUENTIAL_EVENTS_SHARE_NOTICE"]
    if value is not None and support and all(a.origin == UNKNOWN_ORIGIN for a in support):
        value, status, support = None, "uncertain", []
        reasons = [*reasons, "SUPPORT_ORIGIN_UNKNOWN"]
    if value is not None and ev.relevant_gap:
        value, status, support = None, "uncertain", []
        reasons = [*reasons, "COVERAGE_GAP_RELEVANT_ROWS"]
    if status == "conflicting":
        by_type: dict[str, list[TypedAssertion]] = {}
        for a in typed:
            if prop_of[a.assertion_id] in conflict:
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
        # A retraction event inside a type conflict still bears on the date: whether its notice is a retraction
        # is unresolved, so a date that differs from the clear ones cannot be stated as a fact.
        conflicted = [
            a for a in typed if a.type == "retracted" and a.event_id is not None and prop_of[a.assertion_id] in conflict
        ]
        dated = [a for a in support if a.event_id is not None]
        out["retraction_date"] = _retraction_date(dated, basis, conflicted)
        compare["retraction_date.status"] = out["retraction_date"]["status"]
        compare["retraction_date.value"] = out["retraction_date"]["value"]
    return out


def propositions(typed: list[TypedAssertion]) -> tuple[dict[str, str], bool]:
    """Proposition key per assertion id, and whether a sequence was split (SPECIFICATION.md 16, C-12).

    Assertions sharing (notice key, anchor) form one proposition, except that Retraction Watch events of
    different types on one notice key that are pairwise definitely ordered in time are a sequence (an
    expression of concern, then a retraction): they are split by type. A redistributed Retraction Watch copy
    (no event of its own) joins the events of its type. Assertions of other origins, or events whose order is
    not established, stay together, so a disagreement among them is a conflict.
    """
    groups: dict[str, list[TypedAssertion]] = {}
    for a in typed:
        groups.setdefault(a.proposition, []).append(a)
    out: dict[str, str] = {}
    split = False
    for key, members in groups.items():
        events = [a for a in members if a.event_id is not None]
        ordered = (
            len({a.type for a in members}) > 1
            and all(a.origin == RW_ORIGIN for a in members)
            and {a.type for a in members} == {a.type for a in events}
            and all(
                definitely_before(a.notice_date, b.notice_date) or definitely_before(b.notice_date, a.notice_date)
                for i, a in enumerate(events)
                for b in events[i + 1 :]
                if a.type != b.type
            )
        )
        split = split or ordered
        for a in members:
            out[a.assertion_id] = f"{key}#{a.type}" if ordered else key
    return out, split


def _retraction_date(
    events: list[TypedAssertion], basis: dict[str, Any], conflicted: list[TypedAssertion] | None = None
) -> dict[str, Any]:
    def uncertain(value: str | None, reason: str) -> dict[str, Any]:
        basis["reasons"].append(reason)
        return {"status": "uncertain", "value": value, "reason": REASON_TEXT[reason]}

    if not events:
        return uncertain(None, "DATE_NOT_IN_CHECKED_SOURCES")
    dates = [a.notice_date for a in [*events, *(conflicted or [])]]
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
