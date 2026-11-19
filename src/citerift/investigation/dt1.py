"""The decision table dt-3 (dt-2 plus D-13a) and the coherence function kappa (SPEC 6.5, 7.1 to 7.3; MM 5.1 to 5.3):
Stage 04 Step 9, corrected by owner decisions D-071 (dt-2, after the failed gate 04-I) and D-083 (dt-3).

This module is the pure decision core of the production detector. It reads a typed view of one work candidate
(``Candidate``: use eligibility, shape, keys, taint, the CO_REPORTED_MULTIPLE flag and the candidate's lookups as
``Lookup`` views of committed Stage 02 lookup results) and returns one ``Outcome``: the first rule of dt-1 whose guard
holds, with its class, the reason codes the table attaches and kappa. It has no clock, no randomness, no network, no
model and no I/O; ``adapters.detector`` builds the views from committed blobs and turns an outcome into evidence and
a claim.

The table is the explicit ordered tuple ``RULES`` (rule id, guard): the first guard that holds decides, exactly as
SPEC 7.3 lists them. D-5 and D-17 are failures, never classes: they end DETECT with ``ADAPTER_INCONSISTENT`` or
``DECISION_TABLE_GAP`` and no claim. Every guard that reads a projection names the exact contract form it accepts
(Step 4 correction SC-1), so a projection outside the Stage 02 contract reaches D-5 (a lookup other than the deciding
one) or D-17 (the deciding lookup), never a finding.

dt-2 differs from dt-1 in one guard only: D-10 also holds when the deciding lookup has a role-ambiguous event
(``role_ambiguous``): an event attached to the citation through a key that the checked evidence also gives as a notice
identifier (``role_collided``: a record of the candidate's lookups gives the key both roles, flag
``NOTICE_<S>_EQUALS_ORIGINAL``, or another record gives it as its notice, ``notice_hit_count`` of the cited key's own
lookup), when no cited key discriminates (``discriminating``: a cited key with no notice role whose record gives a
different notice identifier in that scheme). Such a candidate is ``UNRESOLVED_IDENTITY`` with
``IDENTIFIER_ROLE_COLLISION`` (D-071 sections 3 and 4); where no event is role-ambiguous dt-2 decides exactly as dt-1.

dt-3 (final corrective cycle, owner decision D-083) is dt-2 with one rule inserted between D-13 and D-14: **D-13a**
holds when the D-14 guard holds (the deciding lookup is matched with a verified-fact projection) and some event of the
deciding lookup is in bib-1 MATERIAL_CONFLICT with the candidate's own bibliographic description
(``citerift.investigation.bibliographic``; normative text docs/verification/stage-04/final-cycle/BIBLIOGRAPHIC_SPEC.md).
Such a candidate is ``UNRESOLVED_IDENTITY`` with ``BIBLIOGRAPHIC_OBJECT_CONFLICT`` and the bib-1 reasons. Every other
case decides exactly as dt-2: D-13a can only replace a positive, never create one.

The dt-3 reference model (``simulations/stage04/dt3_reference.py``) and the independent bib-1 reference
(``bib_reference.py``) are the oracles of this code; the dt-2 model (``dt2_reference.py``) and the frozen Step 4 model
(``dt1_reference.py``) are kept unchanged as the oracles of the frozen engines. None imports anything from here and
this module imports nothing from them.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from citerift.investigation import bibliographic as bib

TABLE_VERSION = "dt-3"

Q1_DOI = "Q1_DOI"
Q1_PMID = "Q1_PMID"
Q2 = "Q2"
ROLES = (Q1_DOI, Q1_PMID, Q2)

STATES = frozenset({"matched", "notice_only", "ambiguous_identity", "no_record", "invalid_query", "unavailable"})
POSITIVE = {
    "retracted": "RETRACTED_WORK_CITED",
    "expression_of_concern": "CONCERN_CITED",
    "correction": "CORRECTION_CITED",
    "reinstated": "REINSTATED_WORK_CITED",
}
NOT_FOUND_VALUE = "not_found_in_checked_sources"
# Stage 02 import flags of a record giving one key as both its original and its notice identifier (Stage 02 SPEC 6.3).
SAME_RECORD_FLAG = {"doi": "NOTICE_DOI_EQUALS_ORIGINAL", "pmid": "NOTICE_PMID_EQUALS_ORIGINAL"}
ROLE_COLLISION = "IDENTIFIER_ROLE_COLLISION"
BIB_CONFLICT = "BIBLIOGRAPHIC_OBJECT_CONFLICT"

# Projection forms (MM 4.5): the (status, value) shapes a guard can name. ``none`` is "no projection".
VF, UNC, UNC_NOT_FOUND, CONF, UNAV, NONE, OTHER = "vf", "unc", "unc:not_found", "conf", "unavailable", "none", "other"
# The forms the Stage 02 contract allows for each state (F-1 to F-4, F-8; S-6.10 for unavailable).
CONTRACT: dict[str, frozenset[str]] = {
    "matched": frozenset({VF, UNC, CONF}),
    "notice_only": frozenset({UNC}),
    "ambiguous_identity": frozenset({UNC}),
    "no_record": frozenset({UNC, UNC_NOT_FOUND}),
    "invalid_query": frozenset({NONE}),
    "unavailable": frozenset({UNAV}),
}

INCOMPATIBLE, NOT_DETERMINED, COHERENT, UNDETERMINED = "INCOMPATIBLE", "NOT_DETERMINED", "COHERENT", "UNDETERMINED"

ADAPTER_INCONSISTENT = "ADAPTER_INCONSISTENT"
DECISION_TABLE_GAP = "DECISION_TABLE_GAP"

# SPEC 7.2: status of each class; SPEC 7.6: its disposition (the controller derives decisions from the class).
STATUS: dict[str, str | None] = {
    **dict.fromkeys(POSITIVE.values(), "verified_fact"),
    "NOT_FOUND_IN_CHECKED_SOURCES": "uncertain",
    "NOTICE_CITED": "uncertain",
    "IDENTITY_CONFLICT": "conflicting",
    "CONTRADICTION_IN_SOURCES": "conflicting",
    "UNRESOLVED_IDENTITY": "uncertain",
    "UNRESOLVED_IDENTIFIER": "uncertain",
    "UNRESOLVED_STATUS": "uncertain",
    "LOOKUP_UNAVAILABLE": "unavailable",
    "UNUSED_DEFINITION": None,
    "UNRESOLVED_USE": None,
    "NO_IDENTIFIER": None,
}


@dataclass(frozen=True)
class Event:
    """One event of a lookup observation, at ``position`` in its ``events`` list (Stage 02 public form)."""

    position: int
    event_id: str
    event_type: str | None
    matched_by: str | None
    linked_via: str | None
    original_doi: str | None
    original_pmid: str | None
    flags: tuple[str, ...] = ()  # Stage 02 event flags (dt-2 reads the same-record collision flags)
    # The record's notice identifiers as Stage 02 renders them (null when absent, or when equal to the original and
    # replaced by the flag): dt-2 reads them to tell whether a second identifier discriminates the work from the notice.
    notice_doi: str | None = None
    notice_pmid: str | None = None
    # dt-3: the record's bibliographic fields (None when the observation holds none for this event).
    record: bib.RecordObject | None = None

    @property
    def direct(self) -> bool:
        return self.linked_via is None


@dataclass(frozen=True)
class Lookup:
    """What dt-1 reads of one committed lookup result (MM 4.5)."""

    state: str
    projection: bool  # a projection is present (Stage 02 gives none for invalid_query)
    status: str | None
    value: Any
    basis_reasons: tuple[str, ...]
    conflict_groups: tuple[tuple[str, tuple[str, ...]], ...]  # (event type, event ids) of the basis conflict groups
    collision: tuple[str, ...]  # event ids a PMID_ROLE_COLLISION issue names that have matched_by = pmid
    budget_refused: bool  # an issue LOOKUP_EVIDENCE_LIMIT_EXCEEDED (S-6.10a, D-048)
    events: tuple[Event, ...]
    # Stage 02 ``notice_hit_count``: events of other records whose notice identifier is the query key (dt-2). None when
    # the observation does not state it (never so for a rendered Stage 02 result); read as "may be a notice".
    notice_hits: int | None = 0

    @property
    def available(self) -> bool:
        return self.state != "unavailable"

    @property
    def form(self) -> str:
        if not self.projection:
            return NONE
        s, v = self.status, self.value
        if s == "verified_fact" and isinstance(v, str) and v in POSITIVE:
            return VF
        if s == "uncertain" and v is None:
            return UNC
        if s == "uncertain" and v == NOT_FOUND_VALUE:
            return UNC_NOT_FOUND
        if s == "conflicting" and v is None:
            return CONF
        if s == "unavailable" and v is None:
            return UNAV
        return OTHER

    def in_contract(self) -> bool:
        """State and projection among the forms of F-1 to F-4 and F-8 (``Contract`` of MM 5.2)."""
        return self.form in CONTRACT.get(self.state, frozenset())

    def events_fit_state(self) -> bool:
        """The events a state can hold (F-5, F-6, gather): none for no_record, invalid_query and unavailable;
        direct notice events for notice_only; direct DOI or PMID events for ambiguous_identity; DOI or PMID events, at
        least one direct, for matched."""
        ev = self.events
        if self.state in ("no_record", "invalid_query", "unavailable"):
            return not ev
        if self.state == "notice_only":
            return bool(ev) and all(e.direct and e.matched_by == "notice" for e in ev)
        if self.state == "ambiguous_identity":
            return bool(ev) and all(e.direct and e.matched_by in ("doi", "pmid") for e in ev)
        if self.state == "matched":
            return any(e.direct for e in ev) and all(e.matched_by in ("doi", "pmid") for e in ev)
        return not ev


@dataclass(frozen=True)
class Candidate:
    """The inputs ``xi(c)`` of MM 5.1 for one work candidate."""

    eligibility: str
    eligibility_reason: str | None
    shape: str
    doi: str | None
    pmid: str | None
    taint: tuple[str, ...]
    multi: bool
    lookups: tuple[tuple[str, Lookup], ...]  # (role, lookup) in the order Q1_DOI, Q1_PMID, Q2, absent roles left out
    # dt-3: the unit's own bibliographic description (None for a unit without one, spec 2.1).
    cited: bib.CitedObject | None = None

    def lookup(self, role: str) -> Lookup | None:
        return next((lk for r, lk in self.lookups if r == role), None)

    @property
    def deciding_role(self) -> str | None:
        """``L(c)`` of SPEC S-6.11: Q2 for PAIR, Q1 of the single key otherwise, none for NONE."""
        return {"DOI": Q1_DOI, "PMID": Q1_PMID, "PAIR": Q2}.get(self.shape)

    @property
    def deciding(self) -> Lookup | None:
        role = self.deciding_role
        return self.lookup(role) if role is not None else None


@dataclass(frozen=True)
class Outcome:
    """The decision for one candidate. ``failure`` is set (and ``cls`` is None) for D-5 and D-17."""

    rule: str
    cls: str | None
    failure: str | None
    reasons: tuple[str, ...]
    kappa: str | None
    violations: tuple[str, ...] = ()
    witnesses: tuple[tuple[str, int], ...] = ()  # (role, event position) of every witness in an available lookup
    conflict_role: str | None = None  # D-7: the lookup whose conflict groups give the alternatives
    upstream_role: str | None = None  # the lookup whose Stage 02 basis reasons are kept
    # dt-3: (event position in the deciding lookup, bib-1 comparison) for every event of L, for D-13a and D-14.
    comparisons: tuple[tuple[int, bib.Comparison], ...] = ()

    @property
    def status(self) -> str | None:
        return STATUS[self.cls] if self.cls is not None else None

    @property
    def value(self) -> str | None:
        return None if self.cls is None else _VALUE.get(self.cls)


_VALUE = {cls: v for v, cls in POSITIVE.items()} | {"NOT_FOUND_IN_CHECKED_SOURCES": NOT_FOUND_VALUE}


# Coherence (SPEC 6.5, MM 5.3) ---------------------------------------------------------------------------------------


def is_witness(e: Event, d: str, p: str) -> bool:
    """A direct event stating that one key of the pair belongs to a work carrying another key of the other scheme."""
    if not e.direct:
        return False
    if e.matched_by == "doi":
        return e.original_doi == d and e.original_pmid not in (p, None)
    if e.matched_by == "pmid":
        return e.original_pmid == p and e.original_doi not in (d, None)
    return False


def witnesses(c: Candidate, role: str) -> tuple[Event, ...]:
    lk = c.lookup(role)
    if c.shape != "PAIR" or lk is None or c.doi is None or c.pmid is None:
        return ()
    d, p = c.doi, c.pmid
    return tuple(e for e in lk.events if is_witness(e, d, p))


def conaming(c: Candidate) -> tuple[tuple[str, int], ...]:
    """Direct events of an available Q1 that name both keys of the pair (the COHERENT clause of SPEC 6.5)."""
    out: list[tuple[str, int]] = []
    for role in (Q1_DOI, Q1_PMID):
        lk = c.lookup(role)
        if lk is None or not lk.available:
            continue
        out += [
            (role, e.position) for e in lk.events if e.direct and e.original_doi == c.doi and e.original_pmid == c.pmid
        ]
    return tuple(out)


def kappa(c: Candidate) -> str | None:
    """kappa of SPEC 6.5 over the direct events of the available lookups; None for shapes other than PAIR."""
    if c.shape != "PAIR":
        return None
    if any(witnesses(c, role) for role, lk in c.lookups if lk.available):
        return INCOMPATIBLE
    q1d, q1p = c.lookup(Q1_DOI), c.lookup(Q1_PMID)
    if q1d is None or q1p is None or not q1d.available or not q1p.available:
        return NOT_DETERMINED
    return COHERENT if conaming(c) else UNDETERMINED


# Role collisions (dt-2, owner decision D-071) ------------------------------------------------------------------------


def attached_keys(c: Candidate, e: Event) -> tuple[tuple[str, str], ...]:
    """The keys through which event ``e`` is attached to the citation: each original identifier of ``e`` that the
    candidate cites, and the one Stage 02 matched or bridged it by (``matched_by``)."""
    out: list[tuple[str, str]] = []
    for scheme, cited, own in (("doi", c.doi, e.original_doi), ("pmid", c.pmid, e.original_pmid)):
        if own is not None and (own == cited or e.matched_by == scheme):
            out.append((scheme, own))
    return tuple(out)


def notice_elsewhere(c: Candidate, scheme: str) -> bool:
    """The cited key of ``scheme`` is the notice identifier of another record per its own single-key lookup (``L`` for
    a DOI or PMID candidate, Q1 for a PAIR). An unavailable lookup states nothing; it never yields a positive (D-13)."""
    lk = c.lookup(Q1_DOI if scheme == "doi" else Q1_PMID)
    if lk is None or not lk.available:
        return False
    return lk.notice_hits is None or lk.notice_hits > 0


def role_collided(c: Candidate, scheme: str, key: str) -> bool:
    """The checked evidence of the candidate gives ``key`` also as a notice identifier: in **any** record of any of the
    candidate's lookups that has ``key`` as its original identifier and also as its notice identifier
    (``NOTICE_<S>_EQUALS_ORIGINAL``), or, for a cited key, as the notice identifier of another record. A property of the
    key, not of one event: a key that some record gives as a notice never resolves another event's collision."""
    flag = SAME_RECORD_FLAG[scheme]
    for _, lk in c.lookups:
        for e in lk.events:
            own = e.original_doi if scheme == "doi" else e.original_pmid
            if own == key and flag in e.flags:
                return True
    cited = c.doi if scheme == "doi" else c.pmid
    return key == cited and notice_elsewhere(c, scheme)


def discriminating(c: Candidate, e: Event, scheme: str) -> bool:
    """The citation's key of ``scheme`` is independent evidence that it names the work of ``e``, not its notice: the
    candidate cites it, it is ``e``'s original identifier, no checked evidence gives it a notice role
    (``role_collided``), and ``e``'s own record gives a **different** notice identifier in the same scheme, so that
    the key tells the work from the notice. A key whose record states no notice identifier in its scheme does not
    discriminate (absence of a notice identifier is not evidence of the work)."""
    cited = c.doi if scheme == "doi" else c.pmid
    own, notice = (e.original_doi, e.notice_doi) if scheme == "doi" else (e.original_pmid, e.notice_pmid)
    return (
        cited is not None
        and own == cited
        and not role_collided(c, scheme, cited)
        and notice is not None
        and notice != cited
    )


def role_ambiguous(c: Candidate) -> tuple[str, ...]:
    """Event ids of the matched deciding lookup whose publication object is not established (D-071 sections 3 and 4):
    an event attached through a role-collided key (or through no key at all; fail closed, Stage 02 never yields one)
    that no discriminating key of the citation (``discriminating``) resolves. Such an event cannot support a positive
    attachment. Nothing else resolves it: no non-cited bridge key, no title, publisher, prefix or notice type."""
    lk = c.deciding
    if lk is None or lk.state != "matched":
        return ()
    out = set()
    for e in lk.events:
        keys = attached_keys(c, e)
        collided = not keys or any(role_collided(c, scheme, key) for scheme, key in keys)
        if collided and not any(discriminating(c, e, scheme) for scheme in ("doi", "pmid")):
            out.add(e.event_id)
    return tuple(sorted(out))


# Bibliographic-object consistency (dt-3, owner decision D-083) --------------------------------------------------------


def comparisons(c: Candidate) -> tuple[tuple[int, bib.Comparison], ...]:
    """The bib-1 comparison of the candidate's description with every event of a matched deciding lookup (direct or
    bridged, in order); empty when the deciding lookup is absent or not matched."""
    lk = c.deciding
    if lk is None or lk.state != "matched":
        return ()
    return tuple((e.position, bib.compare(c.cited, e.record)) for e in lk.events)


def bib_conflicts(c: Candidate) -> tuple[tuple[int, bib.Comparison], ...]:
    """The comparisons of ``comparisons`` in MATERIAL_CONFLICT (spec 5): any one blocks a positive (fail closed)."""
    return tuple((k, cmp) for k, cmp in comparisons(c) if cmp.object == bib.MATERIAL_CONFLICT)


def implied_pair_state(state_d: str, state_p: str, witness: bool) -> str:
    """The Q2 state that F-6 and F-9 imply from the two single-key states and a single-key witness."""
    if witness:
        return "ambiguous_identity"
    if state_d == "matched" or state_p in ("matched", "ambiguous_identity"):
        return "matched"
    if "notice_only" in (state_d, state_p):
        return "notice_only"
    return "no_record"


# D-5: Stage 02 contract violations visible to Stage 04 (S-6.12, MM 5.2) -----------------------------------------------


def violations(c: Candidate) -> tuple[str, ...]:
    out: list[str] = []
    looks = c.lookups
    deciding = c.deciding_role
    if any(lk.state == "invalid_query" for _, lk in looks):
        out.append("INVALID_QUERY")
    if any(role != deciding and not lk.in_contract() for role, lk in looks):
        out.append("NON_DECIDING_OUTSIDE_CONTRACT")
    if any(not lk.events_fit_state() for _, lk in looks):
        out.append("EVENTS_OUTSIDE_STATE")
    q1d, q1p, q2 = c.lookup(Q1_DOI), c.lookup(Q1_PMID), c.lookup(Q2)
    if q1d is not None and q1d.state == "ambiguous_identity":
        out.append("DOI_QUERY_AMBIGUOUS")
    if c.shape == "PAIR":
        if q1d is None or q1p is None or q2 is None:
            out.append("PAIR_LOOKUP_MISSING")
            return tuple(out)
        wd, wp, w2 = (bool(witnesses(c, r)) for r in ROLES)
        if (wd and q1d.state != "matched") or (wp and q1p.state not in ("matched", "ambiguous_identity")):
            out.append("WITNESS_WITHOUT_EVENTS")
        if w2 != (q2.state == "ambiguous_identity"):
            out.append("PAIR_WITNESS_STATE")
        if q1p.state == "ambiguous_identity" and not wp:
            out.append("PMID_AMBIGUOUS_WITHOUT_WITNESS")
        avail_q1 = [lk for lk in (q1d, q1p) if lk.available]
        if conaming(c) and any(lk.state not in ("matched", "ambiguous_identity") for lk in avail_q1):
            out.append("CONAME_WITHOUT_EVENTS")
        if q1d.available and q1p.available and q2.available:
            if q2.state != implied_pair_state(q1d.state, q1p.state, wd or wp):
                out.append("PAIR_STATE_DISAGREES")
            if (kappa(c) == INCOMPATIBLE) != (q2.state == "ambiguous_identity"):
                out.append("KAPPA_Q2_DISAGREE")  # MM proposition P2
    return tuple(out)


# The table (SPEC 7.3) -------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Ctx:
    c: Candidate
    kappa: str | None
    violations: tuple[str, ...]

    @property
    def L(self) -> Lookup | None:
        return self.c.deciding

    def L_is(self, state: str, *forms: str) -> bool:
        lk = self.L
        return lk is not None and lk.state == state and lk.form in forms


def _conflicting_lookup(c: Candidate) -> str | None:
    """D-7: the first lookup, in the order L, Q1(DOI), Q1(PMID), that is matched with a conflicting projection."""
    order = [c.deciding_role, Q1_DOI, Q1_PMID]
    for role in dict.fromkeys(r for r in order if r is not None):
        lk = c.lookup(role)
        if lk is not None and lk.state == "matched" and lk.form == CONF:
            return role
    return None


def _d10(x: _Ctx) -> bool:
    lk = x.L
    return (
        lk is not None
        and lk.state == "matched"
        and lk.in_contract()
        and (bool(lk.collision) or bool(role_ambiguous(x.c)) or "BRIDGE_ONLY_SUPPORT" in lk.basis_reasons)
    )


Guard = Callable[[_Ctx], bool]

RULES: tuple[tuple[str, Guard], ...] = (
    ("D-1", lambda x: x.c.eligibility == "UNUSED"),
    ("D-2", lambda x: x.c.eligibility == "USE_NOT_ESTABLISHED"),
    ("D-3", lambda x: x.c.shape == "NONE" and not x.c.taint),
    ("D-4", lambda x: x.c.shape == "NONE" and bool(x.c.taint)),
    ("D-5", lambda x: bool(x.violations)),
    ("D-6", lambda x: x.c.shape == "PAIR" and x.kappa == INCOMPATIBLE),
    ("D-7", lambda x: _conflicting_lookup(x.c) is not None),
    ("D-8", lambda x: bool(x.c.taint)),
    ("D-9", lambda x: x.L_is("ambiguous_identity", UNC)),
    ("D-10", _d10),
    ("D-11", lambda x: x.L_is("matched", UNC)),
    ("D-12", lambda x: x.L_is("no_record", UNC)),
    ("D-13", lambda x: any(not lk.available for _, lk in x.c.lookups)),
    ("D-13a", lambda x: x.L_is("matched", VF) and bool(bib_conflicts(x.c))),
    ("D-14", lambda x: x.L_is("matched", VF)),
    ("D-15", lambda x: x.L_is("notice_only", UNC)),
    ("D-16", lambda x: x.L_is("no_record", UNC_NOT_FOUND)),
    ("D-17", lambda x: True),
)
RULE_IDS = tuple(r for r, _ in RULES)


def first_rule(x: _Ctx, rules: tuple[tuple[str, Guard], ...] = RULES) -> str:
    return next(rule for rule, guard in rules if guard(x))


def decide(c: Candidate, rules: tuple[tuple[str, Guard], ...] = RULES) -> Outcome:
    """dt-1 for one candidate: the first rule whose guard holds, its class and the reason codes it attaches."""
    k = kappa(c)
    viol = violations(c) if c.shape != "NONE" else ()
    x = _Ctx(c, k, viol)
    rule = first_rule(x, rules)
    wit = tuple((role, e.position) for role, lk in c.lookups if lk.available for e in witnesses(c, role))
    if rule == "D-5":
        return Outcome(rule, None, ADAPTER_INCONSISTENT, (), k, viol, wit)
    if rule == "D-17":
        return Outcome(rule, None, DECISION_TABLE_GAP, (), k, viol, wit)
    reasons: set[str] = set()
    cls: str
    conflict_role = upstream_role = None
    compared: tuple[tuple[int, bib.Comparison], ...] = ()
    L = c.deciding
    if rule == "D-1":
        cls = "UNUSED_DEFINITION"
        reasons = {c.eligibility_reason} if c.eligibility_reason else set()
    elif rule == "D-2":
        cls = "UNRESOLVED_USE"
        reasons = {c.eligibility_reason} if c.eligibility_reason else set()
    elif rule == "D-3":
        cls = "NO_IDENTIFIER"
    elif rule in ("D-4", "D-8"):
        cls, reasons = "UNRESOLVED_IDENTIFIER", set(c.taint)
    elif rule == "D-6":
        cls, reasons = "IDENTITY_CONFLICT", {"IDENTITY_WITNESSED", *c.taint}
        if any(not lk.available for _, lk in c.lookups):
            reasons.add("LOOKUP_PARTIAL")
    elif rule == "D-7":
        cls, reasons = "CONTRADICTION_IN_SOURCES", {"RETRACTION_EVENT_TYPE_CONFLICT"}
        conflict_role = upstream_role = _conflicting_lookup(c)
    elif rule == "D-9":
        cls, reasons, upstream_role = "UNRESOLVED_IDENTITY", {"KEY_NAMES_SEVERAL_WORKS"}, c.deciding_role
    elif rule == "D-10":
        if L is None:
            raise AssertionError("D-10 without a deciding lookup")
        cls, upstream_role = "UNRESOLVED_IDENTITY", c.deciding_role
        if L.collision:
            reasons.add("PMID_ROLE_COLLISION")
        if set(role_ambiguous(c)) - set(L.collision):
            reasons.add(ROLE_COLLISION)
        if "BRIDGE_ONLY_SUPPORT" in L.basis_reasons:
            reasons.add("BRIDGE_ONLY_SUPPORT")
    elif rule == "D-11":
        cls, reasons, upstream_role = "UNRESOLVED_STATUS", {"CURRENT_EFFECT_NOT_ESTABLISHED"}, c.deciding_role
    elif rule == "D-12":
        cls, reasons, upstream_role = "UNRESOLVED_STATUS", {"COVERAGE_GAP_RELEVANT_ROWS"}, c.deciding_role
    elif rule == "D-13":
        cls, reasons = "LOOKUP_UNAVAILABLE", {"LOOKUP_QUERY_FAILED"}
        if any(not lk.available and lk.budget_refused for _, lk in c.lookups):
            reasons.add("LOOKUP_EVIDENCE_LIMIT_EXCEEDED")
    elif rule == "D-13a":
        compared = comparisons(c)
        cls, upstream_role = "UNRESOLVED_IDENTITY", c.deciding_role
        reasons = {BIB_CONFLICT, *(r for _, cmp in compared for r in cmp.reasons)}
    elif rule == "D-14":
        if L is None:
            raise AssertionError("D-14 without a deciding lookup")
        cls, upstream_role = POSITIVE[L.value], c.deciding_role
        compared = comparisons(c)
    elif rule == "D-15":
        cls, reasons, upstream_role = "NOTICE_CITED", {"CITED_IDENTIFIER_IS_NOTICE"}, c.deciding_role
    elif rule == "D-16":
        cls, reasons, upstream_role = "NOT_FOUND_IN_CHECKED_SOURCES", {"NOT_FOUND_IN_CHECKED_SOURCES"}, c.deciding_role
    else:
        raise AssertionError(f"unknown rule {rule}")
    q1d, q1p = c.lookup(Q1_DOI), c.lookup(Q1_PMID)
    if c.shape == "PAIR" and q1d is not None and q1p is not None and q1d.state != q1p.state:
        reasons.add("KEY_RESULTS_DIFFER")
    if k == UNDETERMINED:
        reasons.add("PAIR_UNCORROBORATED")
    if c.multi:
        reasons.add("CO_REPORTED_MULTIPLE")
    return Outcome(rule, cls, None, tuple(sorted(reasons)), k, viol, wit, conflict_role, upstream_role, compared)
