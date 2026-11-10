"""Finite abstraction of what Stage 02 can return for the lookups of one Stage 04 work candidate.

This module states, independently of any Stage 04 production code and without importing ``citerift``, which
combinations of abstract lookup values (``dt1_reference.Lookup``) and coherence witnesses Stage 02 can produce. It is
written from the Stage 02 facts F-1 to F-7 of MATHEMATICAL_MODEL.md 4.5 (``gather`` in
``src/citerift/retraction/query.py``). ``stage02_conformance.py`` checks it against the real Stage 02 engine.

A **world** is the part of one index that decides the lookups of a pair ``(d, p)``:

- ``coname``: events with ``original_doi = d`` and ``original_pmid = p`` exist;
- ``d_null``: events with ``original_doi = d`` and no PMID exist;
- ``d_other``: events with ``original_doi = d`` and a PMID other than ``p`` exist (a witness in ``O_d``);
- ``p_null``: events with ``original_pmid = p`` and no DOI exist;
- ``p_other`` in {0, 1, 2}: the number of distinct DOIs other than ``d`` among events with ``original_pmid = p``
  (2 stands for "two or more"; any of them is a witness in ``O_p``);
- ``nd``, ``np``: a notice event names ``d`` as its notice DOI, ``p`` as its notice PMID.

There are 2 * 2 * 2 * 2 * 3 * 2 * 2 = 192 worlds. Every one of them is buildable as a Stage 02 index (the
conformance module builds all 192).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from itertools import product

from dt1_reference import (
    MALFORMED,
    TAINT_REASONS,
    WELL_FORMED,
    Case,
    Lookup,
    well_formed,
)


@dataclass(frozen=True)
class World:
    coname: bool
    d_null: bool
    d_other: bool
    p_null: bool
    p_other: int
    nd: bool
    np: bool

    def o_d(self) -> bool:
        return self.coname or self.d_null or self.d_other

    def o_p(self) -> bool:
        return self.coname or self.p_null or self.p_other > 0

    def compatible(self) -> bool:
        return not self.d_other and self.p_other == 0

    def q1_doi(self) -> str:
        """State of gather(doi=d) (F-1, F-5): a DOI-only query is never ambiguous."""
        if self.o_d():
            return "matched"
        return "notice_only" if self.nd else "no_record"

    def q1_pmid(self) -> str:
        """State of gather(pmid=p): ambiguous when the PMID's events carry two or more distinct DOIs."""
        if int(self.coname) + self.p_other >= 2:
            return "ambiguous_identity"
        if self.o_p():
            return "matched"
        return "notice_only" if self.np else "no_record"

    def q2(self) -> str:
        """State of gather(doi=d, pmid=p) (F-6)."""
        if not self.compatible():
            return "ambiguous_identity"
        if self.o_d() or self.o_p():
            return "matched"
        return "notice_only" if self.nd or self.np else "no_record"


def worlds() -> list[World]:
    return [
        World(*v)
        for v in product(
            (False, True), (False, True), (False, True), (False, True), (0, 1, 2), (False, True), (False, True)
        )
    ]


# A signature is what dt-1 reads apart from projections: (state of Q1(d), Q1(p), Q2, wd, wp, w2, coname), with the
# witness bits as visible in the available lookups.
Signature = tuple[str, str, str, bool, bool, bool, bool]


def signature(w: World, avail_d: bool, avail_p: bool, avail_2: bool) -> Signature:
    sd = w.q1_doi() if avail_d else "unavailable"
    sp = w.q1_pmid() if avail_p else "unavailable"
    s2 = w.q2() if avail_2 else "unavailable"
    wd = avail_d and w.d_other  # direct doi-labelled events of Q1(d) are O_d (F-5)
    wp = avail_p and w.p_other > 0  # direct pmid-labelled events of Q1(p) are O_p, in both branches (F-5)
    w2 = avail_2 and not w.compatible()  # F-6: Q2 has a witness exactly when it is ambiguous_identity
    coname = w.coname and (avail_d or avail_p)
    return (sd, sp, s2, wd, wp, w2, coname)


def pair_signatures() -> dict[Signature, list[tuple[World, tuple[bool, bool, bool]]]]:
    """Every signature reachable for a PAIR candidate, with the worlds and availability masks that produce it."""
    out: dict[Signature, list[tuple[World, tuple[bool, bool, bool]]]] = {}
    for w in worlds():
        for mask in product((True, False), repeat=3):
            out.setdefault(signature(w, *mask), []).append((w, mask))
    return out


DOI_STATES = ("matched", "notice_only", "no_record", "unavailable")
PMID_STATES = ("matched", "ambiguous_identity", "notice_only", "no_record", "unavailable")
_PAIR_SIGNATURES = frozenset(pair_signatures())


def single_states() -> dict[str, frozenset[str]]:
    """States reachable for a single-key query, derived from the worlds (plus the adapter's ``unavailable``)."""
    doi = {w.q1_doi() for w in worlds()} | {"unavailable"}
    pmid = {w.q1_pmid() for w in worlds()} | {"unavailable"}
    return {"DOI": frozenset(doi), "PMID": frozenset(pmid)}


_SINGLE = single_states()


def _ok_lookup(lk: Lookup | None) -> bool:
    return lk is not None and (lk[0] == "unavailable" or (lk[0] in WELL_FORMED and well_formed(lk)))


def invalid_reasons(c: Case) -> list[str]:
    """Why ``c`` cannot be produced by Stage 02 and Stage 03 under their accepted contracts (empty when valid).

    Validity is an over-approximation of reachability for projections: any well-formed projection shape of a state
    is admitted (cross-lookup constraints between projections are not modelled), so properties checked on the valid
    domain are checked on a superset of what Stage 02 can produce. States and witness bits are exact (worlds).
    """
    out: list[str] = []
    if c.shape == "NONE":
        if "IDENTIFIER_UNCONFIRMED" in c.taint:
            out.append("UNCONFIRMED_WITHOUT_KEY")  # an UNCONFIRMED occurrence is a key (S-6.4)
        if c.wd or c.wp or c.w2 or c.coname:
            out.append("WITNESS_WITHOUT_PAIR")
        return out
    if any(lk[0] == "invalid_query" for lk in c.lookups()):
        out.append("INVALID_QUERY_FOR_VALID_KEY")  # keys are valid Stage 02 normalizations (MM 4.3)
    if any(not _ok_lookup(lk) for lk in c.lookups()):
        out.append("PROJECTION_OUTSIDE_CONTRACT")  # F-2, F-3, F-4 and the unknown state
    if c.shape in ("DOI", "PMID"):
        lk = c.d if c.shape == "DOI" else c.p
        if not (lk is not None):
            raise AssertionError("model invariant")
        if lk[0] not in _SINGLE[c.shape]:
            out.append("STATE_UNREACHABLE")  # a DOI-only query is never ambiguous_identity
        if c.wd or c.wp or c.w2 or c.coname:
            out.append("WITNESS_WITHOUT_PAIR")
        return sorted(set(out))
    if not (c.d is not None and c.p is not None and c.q2 is not None):
        raise AssertionError("model invariant")
    if c.multi:
        out.append("MULTI_ON_PAIR")  # CD-1: a PAIR candidate is the only candidate of its unit
    sig = (c.d[0], c.p[0], c.q2[0], c.wd, c.wp, c.w2, c.coname)
    if sig not in _PAIR_SIGNATURES:
        out.append("SIGNATURE_UNREACHABLE")
    return sorted(set(out))


def valid(c: Case) -> bool:
    return not invalid_reasons(c)


def taint_sets() -> list[frozenset[str]]:
    out: list[frozenset[str]] = []
    for bits in product((False, True), repeat=len(TAINT_REASONS)):
        out.append(frozenset(r for r, b in zip(TAINT_REASONS, bits, strict=True) if b))
    return out


def iter_valid_pair_lookups() -> Iterator[tuple[Lookup, Lookup, Lookup, Signature]]:
    """Every (Q1(d), Q1(p), Q2) triple of the valid domain with its signature (projections over-approximated)."""

    def values(state: str) -> list[Lookup]:
        if state == "unavailable":
            return [("unavailable", "none", False)]
        vals: list[Lookup] = [(state, sh, False) for sh in WELL_FORMED[state]]
        if state == "matched":
            vals += [(state, sh, True) for sh in WELL_FORMED[state]]
        return vals

    for sig in sorted(_PAIR_SIGNATURES):
        for d in values(sig[0]):
            for p in values(sig[1]):
                for q2 in values(sig[2]):
                    yield d, p, q2, sig


__all__ = ["MALFORMED", "World", "invalid_reasons", "pair_signatures", "signature", "valid", "worlds"]
