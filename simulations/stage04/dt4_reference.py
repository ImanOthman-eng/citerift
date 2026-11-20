"""Reference model of the Stage 04 decision table dt-4 (owner decisions D-086, D-087;
final-cycle/BIBLIOGRAPHIC_SPEC_2.md 6).

A new oracle version; the dt-3 model (``dt3_reference.py``), the dt-2 model (``dt2_reference.py``) and the frozen
Step 4 model (``dt1_reference.py``) and their oracles are kept unchanged. This module is a copy of the dt-3 model with
exactly the dt-4 change of BIBLIOGRAPHIC_SPEC_2.md section 6: the boolean ``bc`` is replaced by the field ``bib``
(below), and three rules lie between D-13 and D-14, in this order, each with the D-14 guard (the deciding lookup is
``matched`` with a ``verified_fact`` projection):

- D-13a (dt-3, unchanged): ``bib == "CONFLICT"`` -> UNRESOLVED_IDENTITY, reason ``BIBLIOGRAPHIC_OBJECT_CONFLICT``;
- D-13b (D-086): ``bib == "UNAVAILABLE"`` -> UNRESOLVED_IDENTITY, reason ``BIBLIOGRAPHIC_CHECK_UNAVAILABLE``;
- D-13c (D-087): ``bib == "NOT_ESTABLISHED"`` -> UNRESOLVED_IDENTITY, reason ``BIBLIOGRAPHIC_OBJECT_NOT_ESTABLISHED``.

As in dt-3, the bib-2 detail reasons (``BIB_*`` of the events, or the UNAVAILABLE reason ``r``) are abstracted away:
they are a function of the unit and the pair, tested against the independent ``bib2_reference.py``. D-13b and D-13c
take the status, value, disposition and common tail of D-13a. The per-rule tables are extended consistently: ``RULES``
lists D-13a, D-13b, D-13c in that order between D-13 and D-14, and ``TIER`` gives D-13b and D-13c tier 7, the tier of
D-13a and D-14 (the same guard). It imports nothing from ``citerift``, ``dt1_reference``, ``dt2_reference``,
``dt3_reference``, ``bib_reference`` or ``bib2_reference``.

Abstract input of one work candidate (``Case``):

- ``use``: use eligibility E(u) in {CITED, UNUSED, USE_NOT_ESTABLISHED};
- ``shape``: sigma in {NONE, DOI, PMID, PAIR};
- ``taint``: the set of taint reasons of the unit (empty = not tainted);
- ``multi``: the candidate carries CO_REPORTED_MULTIPLE (single-key shapes only);
- ``d``, ``p``, ``q2``: abstract lookup values of Q1(DOI), Q1(PMID) and the pair query Q2 (None when absent);
- ``wd``, ``wp``, ``w2``: a direct witness of incompatibility is visible in Q1(d), Q1(p), Q2;
- ``coname``: a direct event naming both the DOI and the PMID is visible in an available Q1;
- ``bib`` (dt-4), one of ``BIB_STATES``: ``CONFLICT`` (some event of the deciding lookup is in bib-2
  MATERIAL_CONFLICT with the unit's description), ``UNAVAILABLE`` (the unit's bibliographic check is
  UNAVAILABLE(r)), ``NOT_ESTABLISHED`` (some event is NOT_ESTABLISHED and none is in MATERIAL_CONFLICT), ``NONE``
  (no event of the deciding lookup is in conflict or not established, and the check was not unavailable). One value
  suffices: an UNAVAILABLE unit has no comparisons, and CONFLICT takes precedence over NOT_ESTABLISHED (section 6).
  Free here; meaningful only for a matched deciding lookup (production compares nothing otherwise).
- ``rc`` (dt-2): the deciding lookup holds a role-ambiguous event that the PMID_ROLE_COLLISION bit does not cover: an
  event attached through a key that the checked evidence also gives as a notice identifier (the same record's, or
  another record's), which no cited key with no notice role and a record-stated different notice identifier resolves
  (SPEC 7.3a). The bit is free here; how production computes it is tested separately. Meaningful only for a matched
  deciding lookup (``stage02_abstraction`` validity for dt-2: ``rc`` implies a matched deciding lookup).

An abstract lookup value is ``(state, shape, collision)``: the Stage 02 lookup state, the shape of its projection
(status and value class) and whether a PMID_ROLE_COLLISION issue names a PMID-matched event.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

MODEL_VERSION = "dt4-reference/1"
TABLE_VERSION = "dt-4"

USES = ("CITED", "UNUSED", "USE_NOT_ESTABLISHED")
SHAPES = ("NONE", "DOI", "PMID", "PAIR")
TAINT_REASONS = ("IDENTIFIER_MALFORMED", "IDENTIFIER_ROLE_UNRESOLVED", "IDENTIFIER_UNCONFIRMED")
POSITIVE_VALUES = ("retracted", "expression_of_concern", "correction", "reinstated")
BIB_STATES = ("NONE", "CONFLICT", "UNAVAILABLE", "NOT_ESTABLISHED")

# Projection shapes that the Stage 02 contract allows for each state (MATHEMATICAL_MODEL.md F-1 to F-4, F-8).
WELL_FORMED: dict[str, tuple[str, ...]] = {
    "matched": (*(f"vf:{v}" for v in POSITIVE_VALUES), "unc", "unc:bridge_only", "conf"),
    "notice_only": ("unc:notice",),
    "ambiguous_identity": ("unc:ambiguous",),
    "no_record": ("unc:not_found", "unc:gap"),
    "invalid_query": ("none",),
    "unavailable": ("none",),
}
# Shapes outside the contract, kept in the domain so that the table is shown to fail closed on them.
MALFORMED: dict[str, tuple[str, ...]] = {
    "matched": ("none", "status:unavailable", "vf:not_found", "vf:null", "unc:valued", "conf:valued"),
    "notice_only": ("vf:retracted",),
    "ambiguous_identity": ("vf:retracted",),
    "no_record": ("vf:retracted", "conf", "unc:valued"),
    "unknown_state": ("none",),
}

Lookup = tuple[str, str, bool]


def lookup_values() -> list[Lookup]:
    """The 32 abstract lookup values: 20 within the Stage 02 contract and 12 outside it."""
    out: list[Lookup] = []
    for state, shapes in WELL_FORMED.items():
        for shape in shapes:
            out.append((state, shape, False))
            if state == "matched":
                out.append((state, shape, True))
    for state, shapes in MALFORMED.items():
        out.extend((state, shape, False) for shape in shapes)
    return out


def well_formed(lk: Lookup) -> bool:
    state, shape, collision = lk
    return shape in WELL_FORMED.get(state, ()) and (not collision or state == "matched")


CLASS_STATUS = {
    "RETRACTED_WORK_CITED": "verified_fact",
    "CONCERN_CITED": "verified_fact",
    "CORRECTION_CITED": "verified_fact",
    "REINSTATED_WORK_CITED": "verified_fact",
    "NOT_FOUND_IN_CHECKED_SOURCES": "uncertain",
    "NOTICE_CITED": "uncertain",
    "IDENTITY_CONFLICT": "conflicting",
    "UNRESOLVED_IDENTITY": "uncertain",
    "UNRESOLVED_IDENTIFIER": "uncertain",
    "CONTRADICTION_IN_SOURCES": "conflicting",
    "UNRESOLVED_STATUS": "uncertain",
    "LOOKUP_UNAVAILABLE": "unavailable",
    "UNUSED_DEFINITION": None,
    "UNRESOLVED_USE": None,
    "NO_IDENTIFIER": None,
}
POSITIVE_CLASS = {
    "retracted": "RETRACTED_WORK_CITED",
    "expression_of_concern": "CONCERN_CITED",
    "correction": "CORRECTION_CITED",
    "reinstated": "REINSTATED_WORK_CITED",
}
DISPOSITION = {
    **dict.fromkeys(POSITIVE_CLASS.values(), "REPORT_FINDING"),
    "NOT_FOUND_IN_CHECKED_SOURCES": "REPORT_NOT_FOUND",
    "IDENTITY_CONFLICT": "ROUTE_NEEDS_RESOLUTION",
    "CONTRADICTION_IN_SOURCES": "ROUTE_NEEDS_RESOLUTION",
    "UNRESOLVED_IDENTITY": "ABSTAIN",
    "UNRESOLVED_IDENTIFIER": "ABSTAIN",
    "UNRESOLVED_STATUS": "ABSTAIN",
    "NOTICE_CITED": "ABSTAIN",
    "LOOKUP_UNAVAILABLE": "ABSTAIN_UNAVAILABLE",
    "UNUSED_DEFINITION": "OUT_OF_SCOPE",
    "UNRESOLVED_USE": "OUT_OF_SCOPE",
    "NO_IDENTIFIER": "OUT_OF_SCOPE",
}
KIND = {
    "REPORT_FINDING": "positive",
    "REPORT_NOT_FOUND": "not_found",
    "ROUTE_NEEDS_RESOLUTION": "needs_resolution",
    "ABSTAIN": "abstain",
    "ABSTAIN_UNAVAILABLE": "abstain_unavailable",
    "OUT_OF_SCOPE": "out_of_scope",
}
RULES = (*(f"D-{i}" for i in range(1, 14)), "D-13a", "D-13b", "D-13c", *(f"D-{i}" for i in range(14, 18)))
TIER = {
    "D-1": 2,
    "D-2": 2,
    "D-3": 2,
    "D-4": 2,
    "D-5": 3,
    "D-6": 4,
    "D-7": 4,
    "D-8": 5,
    "D-9": 5,
    "D-10": 5,
    "D-11": 5,
    "D-12": 5,
    "D-13": 6,
    "D-13a": 7,
    "D-13b": 7,
    "D-13c": 7,
    "D-14": 7,
    "D-15": 8,
    "D-16": 9,
    "D-17": 10,
}


@dataclass(frozen=True)
class Case:
    use: str
    shape: str
    taint: frozenset[str]
    multi: bool = False
    d: Lookup | None = None
    p: Lookup | None = None
    q2: Lookup | None = None
    wd: bool = False
    wp: bool = False
    w2: bool = False
    coname: bool = False
    rc: bool = False
    bib: str = "NONE"

    def lookups(self) -> list[Lookup]:
        return [lk for lk in (self.d, self.p, self.q2) if lk is not None]

    def deciding(self) -> Lookup | None:
        return {"DOI": self.d, "PMID": self.p, "PAIR": self.q2}.get(self.shape)

    def key(self) -> list[Any]:
        """Canonical JSON form of the case (used as the oracle key)."""
        return [
            self.use,
            self.shape,
            sorted(self.taint),
            self.multi,
            *(list(lk) if lk is not None else None for lk in (self.d, self.p, self.q2)),
            self.wd,
            self.wp,
            self.w2,
            self.coname,
            self.rc,
            self.bib,
        ]


def available(lk: Lookup | None) -> bool:
    return lk is not None and lk[0] != "unavailable"


def pair_state(state_d: str, state_p: str, witness: bool) -> str:
    """State of the pair query implied by the two single-key states (MATHEMATICAL_MODEL.md F-6, F-9)."""
    if witness:
        return "ambiguous_identity"
    if state_d == "matched" or state_p in ("matched", "ambiguous_identity"):
        return "matched"
    if "notice_only" in (state_d, state_p):
        return "notice_only"
    return "no_record"


def contract_violations(c: Case) -> list[str]:
    """Stage 02 contract violations visible to Stage 04 without reading the deciding projection (rule D-5)."""
    out = []
    lks = c.lookups()
    if any(lk[0] == "invalid_query" for lk in lks):
        out.append("INVALID_QUERY")
    deciding_slot = {"DOI": "d", "PMID": "p", "PAIR": "q2"}.get(c.shape)
    slots = {"d": c.d, "p": c.p, "q2": c.q2}
    if any(lk is not None and slot != deciding_slot and not well_formed(lk) for slot, lk in slots.items()):
        out.append("NON_DECIDING_SHAPE")
    if c.d is not None and c.d[0] == "ambiguous_identity":
        out.append("DOI_QUERY_AMBIGUOUS")
    if c.shape == "PAIR":
        if not (c.d is not None and c.p is not None and c.q2 is not None):
            raise AssertionError("model invariant")
        if (c.wd and c.d[0] != "matched") or (c.wp and c.p[0] not in ("matched", "ambiguous_identity")):
            out.append("WITNESS_WITHOUT_EVENTS")
        if c.w2 != (c.q2[0] == "ambiguous_identity"):
            out.append("PAIR_WITNESS_STATE")
        if c.p[0] == "ambiguous_identity" and not c.wp:
            out.append("PMID_AMBIGUOUS_WITHOUT_WITNESS")
        q1 = [lk for lk in (c.d, c.p) if available(lk)]
        if c.coname and (not q1 or any(lk[0] not in ("matched", "ambiguous_identity") for lk in q1)):
            out.append("CONAME_WITHOUT_EVENTS")
        if all(available(lk) for lk in (c.d, c.p, c.q2)) and c.q2[0] != pair_state(c.d[0], c.p[0], c.wd or c.wp):
            out.append("PAIR_STATE_DISAGREES")
    elif c.wd or c.wp or c.w2 or c.coname:
        out.append("WITNESS_WITHOUT_PAIR")
    return out


def coherence(c: Case) -> str | None:
    """kappa of MATHEMATICAL_MODEL.md 5.3 over the visible witnesses."""
    if c.shape != "PAIR":
        return None
    if c.wd or c.wp or c.w2:
        return "INCOMPATIBLE"
    if not (available(c.d) and available(c.p)):
        return "NOT_DETERMINED"
    return "COHERENT" if c.coname else "UNDETERMINED"


def guards(c: Case) -> dict[str, bool]:
    """Every guard of dt-4 evaluated on ``c`` (the table is the first true one)."""
    lks = c.lookups()
    L = c.deciding()
    tainted = bool(c.taint)
    kappa = coherence(c)
    st, sh, col = L if L is not None else (None, None, False)
    return {
        "D-1": c.use == "UNUSED",
        "D-2": c.use == "USE_NOT_ESTABLISHED",
        "D-3": c.shape == "NONE" and not tainted,
        "D-4": c.shape == "NONE" and tainted,
        "D-5": bool(contract_violations(c)),
        "D-6": c.shape == "PAIR" and kappa == "INCOMPATIBLE",
        "D-7": any(lk[0] == "matched" and lk[1] == "conf" for lk in lks),
        "D-8": tainted,
        "D-9": st == "ambiguous_identity" and sh == "unc:ambiguous",
        "D-10": st == "matched" and sh in WELL_FORMED["matched"] and (col or c.rc or sh == "unc:bridge_only"),
        "D-11": st == "matched" and sh == "unc",
        "D-12": st == "no_record" and sh == "unc:gap",
        "D-13": any(lk[0] == "unavailable" for lk in lks),
        "D-13a": st == "matched" and sh in tuple(f"vf:{v}" for v in POSITIVE_VALUES) and c.bib == "CONFLICT",
        "D-13b": st == "matched" and sh in tuple(f"vf:{v}" for v in POSITIVE_VALUES) and c.bib == "UNAVAILABLE",
        "D-13c": st == "matched" and sh in tuple(f"vf:{v}" for v in POSITIVE_VALUES) and c.bib == "NOT_ESTABLISHED",
        "D-14": st == "matched" and sh in tuple(f"vf:{v}" for v in POSITIVE_VALUES),
        "D-15": st == "notice_only" and sh == "unc:notice",
        "D-16": st == "no_record" and sh == "unc:not_found",
        "D-17": True,
    }


def decide(c: Case, rules: tuple[str, ...] = RULES) -> dict[str, Any]:
    """The decision of dt-4 for ``c``: rule, class, status, value, disposition, kind and reason codes."""
    g = guards(c)
    rule = next((r for r in rules if g.get(r)), None)
    reasons: set[str] = set()
    kappa = coherence(c)
    if rule is None:
        return {"rule": None, "class": None, "kind": "no_rule", "reasons": []}
    if rule in ("D-5", "D-17"):
        code = "ADAPTER_INCONSISTENT" if rule == "D-5" else "DECISION_TABLE_GAP"
        detail = contract_violations(c) if rule == "D-5" else []
        return {
            "rule": rule,
            "class": None,
            "kind": "failure",
            "reasons": [code, *detail],
            "status": None,
            "value": None,
            "disposition": None,
        }
    L = c.deciding()
    cls: str
    if rule == "D-1":
        cls, reasons = "UNUSED_DEFINITION", {"DEFINITION_UNUSED"}
    elif rule == "D-2":
        cls, reasons = "UNRESOLVED_USE", {"USE_NOT_ESTABLISHED"}
    elif rule == "D-3":
        cls = "NO_IDENTIFIER"
    elif rule in ("D-4", "D-8"):
        cls, reasons = "UNRESOLVED_IDENTIFIER", set(c.taint)
    elif rule == "D-6":
        cls = "IDENTITY_CONFLICT"
        reasons = {"IDENTITY_WITNESSED", *c.taint}
        if any(lk[0] == "unavailable" for lk in c.lookups()):
            reasons.add("LOOKUP_PARTIAL")
    elif rule == "D-7":
        cls, reasons = "CONTRADICTION_IN_SOURCES", {"SOURCE_TYPE_CONFLICT"}
    elif rule == "D-9":
        cls, reasons = "UNRESOLVED_IDENTITY", {"KEY_NAMES_SEVERAL_WORKS"}
    elif rule == "D-10":
        if not (L is not None):
            raise AssertionError("model invariant")
        cls = "UNRESOLVED_IDENTITY"
        reasons = (
            ({"PMID_ROLE_COLLISION"} if L[2] else set())
            | ({"IDENTIFIER_ROLE_COLLISION"} if c.rc else set())
            | ({"BRIDGE_ONLY_SUPPORT"} if L[1] == "unc:bridge_only" else set())
        )
    elif rule == "D-11":
        cls, reasons = "UNRESOLVED_STATUS", {"STAGE02_BASIS_REASONS"}
    elif rule == "D-12":
        cls, reasons = "UNRESOLVED_STATUS", {"COVERAGE_GAP_RELEVANT_ROWS"}
    elif rule == "D-13":
        cls, reasons = "LOOKUP_UNAVAILABLE", {"LOOKUP_UNAVAILABLE"}
    elif rule == "D-13a":
        cls, reasons = "UNRESOLVED_IDENTITY", {"BIBLIOGRAPHIC_OBJECT_CONFLICT"}
    elif rule == "D-13b":
        cls, reasons = "UNRESOLVED_IDENTITY", {"BIBLIOGRAPHIC_CHECK_UNAVAILABLE"}
    elif rule == "D-13c":
        cls, reasons = "UNRESOLVED_IDENTITY", {"BIBLIOGRAPHIC_OBJECT_NOT_ESTABLISHED"}
    elif rule == "D-14":
        if not (L is not None):
            raise AssertionError("model invariant")
        cls = POSITIVE_CLASS[L[1].split(":", 1)[1]]
    elif rule == "D-15":
        cls, reasons = "NOTICE_CITED", {"CITED_IDENTIFIER_IS_NOTICE"}
    else:  # D-16
        cls, reasons = "NOT_FOUND_IN_CHECKED_SOURCES", {"NOT_FOUND_IN_CHECKED_SOURCES"}
    if c.shape == "PAIR" and c.d is not None and c.p is not None and c.d[0] != c.p[0]:
        reasons.add("KEY_RESULTS_DIFFER")
    if kappa == "UNDETERMINED":
        reasons.add("PAIR_UNCORROBORATED")
    if c.multi:
        reasons.add("CO_REPORTED_MULTIPLE")
    value: str | None = None
    if cls in POSITIVE_CLASS.values():
        if not (L is not None):
            raise AssertionError("model invariant")
        value = L[1].split(":", 1)[1]
    elif cls == "NOT_FOUND_IN_CHECKED_SOURCES":
        value = "not_found_in_checked_sources"
    disposition = DISPOSITION[cls]
    return {
        "rule": rule,
        "class": cls,
        "status": CLASS_STATUS[cls],
        "value": value,
        "disposition": disposition,
        "kind": KIND[disposition],
        "reasons": sorted(reasons),
    }
