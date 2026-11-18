"""The production detector of DETECT: dt-2, kappa, claims and their evidence (Stage 04 Step 9; SPEC 6.5, 7, 8.3).

``dt1_detector`` reads only committed content (the candidate inputs and lookup plan named by ``DetectInput``, the
lookup observations, the index identity and the extraction they name), builds the typed views of ``dt1``, decides
every candidate with the ordered table ``dt1.RULES`` and returns its evidence items and claims. It has no clock, no
randomness, no network and no model. D-5 and D-17 raise ``DetectFailure`` (``ADAPTER_INCONSISTENT``,
``DECISION_TABLE_GAP``): DETECT then fails terminally and no claim of the investigation is committed (SPEC 7.3).

Evidence written by DETECT (D-051 ids ``H(observation, pointer, kind)``; refs point only to earlier evidence):

- ``index_identity``: the committed index identity, pointer ``""``, value null;
- ``lookup_result``: a lookup observation at ``/result``, and at ``/result/projection/retraction_status`` for a
  projection a rule read, value null;
- ``lookup_event``: a lookup observation at ``/events/k``, and at ``/events/k/original_doi`` or ``/original_pmid``
  for the identifier field of a witness (S-7.3), value null;
- ``coherence``: the Q2 lookup observation of a PAIR at ``/query``, value kappa;
- ``work_candidate``: the extraction, at the first occurrence of the candidate's keys (``/identifiers/j``), or at
  ``/units/i`` for a NONE candidate; value ``{shape, keys, coherence}``.

B-8 (Step 8 carry-forward): a ``work_candidate`` item at the unit's pointer would give two CO_REPORTED_MULTIPLE
candidates of one unit the same evidence id with different values. Within one extraction the candidates of a unit
have disjoint key sets and every identifier occurrence belongs to one unit, so the first occurrence of a candidate's
keys names one candidate only; a NONE candidate is the only candidate of its unit. Distinct candidates therefore get
distinct ids, the same candidate always the same id (replay), and D-051 is unchanged. ``_Items.add`` refuses any
id that names two different items (fail closed), so a future change that broke the argument could not merge them.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from citerift.investigation import dt1, ids, sets
from citerift.investigation.adapters.detect import DetectFailure, DetectInput, Detection
from citerift.investigation.canonical import canon, sha256_hex

# Version 2 (Step 12, A-03): the occurrences of a tainted unit support every claim that carries a taint reason.
# Version 3 (corrective cycle, owner decision D-071): decision table dt-2; the view carries event flags and notice hits.
DETECTOR_IDENTITY = "citerift-dt1-detector/3 (dt-2)"
LIMIT_CODE = "LOOKUP_EVIDENCE_LIMIT_EXCEEDED"
TAINT_REASONS = frozenset({"IDENTIFIER_UNCONFIRMED", "IDENTIFIER_MALFORMED", "IDENTIFIER_ROLE_UNRESOLVED"})


def _flags(raw: Any) -> tuple[str, ...]:
    """Stage 02 event flags (required by the Stage 02 event schema). A missing value, or one that is not a list of
    strings, cannot show that an identifier has no notice role: it is read as both same-record collision flags (fail
    closed; LOOKUP validates every observation it commits, so production never reaches this)."""
    if isinstance(raw, list) and all(isinstance(f, str) for f in raw):
        return tuple(raw)
    return tuple(sorted(dt1.SAME_RECORD_FLAG.values()))


def _events(obs: Mapping[str, Any]) -> tuple[dt1.Event, ...]:
    return tuple(
        dt1.Event(
            position=k,
            event_id=str(e.get("event_id")),
            event_type=e.get("event_type"),
            matched_by=e.get("matched_by"),
            linked_via=e.get("linked_via"),
            original_doi=e.get("original_doi"),
            original_pmid=e.get("original_pmid"),
            flags=_flags(e.get("flags")),
            notice_doi=e.get("notice_doi"),
            notice_pmid=e.get("notice_pmid"),
        )
        for k, e in enumerate(obs.get("events") or ())
    )


def lookup_view(obs: Mapping[str, Any]) -> dt1.Lookup:
    """What dt-2 reads of one lookup observation: state, projection form, basis reasons and conflict groups, the
    PMID_ROLE_COLLISION events matched by PMID, the budget refusal, every event with its flags (never only the rendered
    page) and Stage 02's ``notice_hit_count`` (None when the result does not state a non-negative integer)."""
    res = obs["result"]
    events = _events(obs)
    proj = res.get("projection")
    status = proj.get("retraction_status") if isinstance(proj, Mapping) else None
    present = isinstance(status, Mapping)
    basis = (proj.get("basis") or {}) if isinstance(proj, Mapping) else {}
    by_id = {e.event_id: e for e in events}
    # D-7 alternatives: Stage 02's own alternatives of a conflicting status (one per asserted type, with provenance),
    # in Stage 02's order, each with the Retraction Watch events of its type that the basis conflict groups name. A
    # conflict-group assertion that is no event (a Crossref assertion, ``cr-...``) has no event item; its value is
    # supported by the alternative itself, whose provenance names the deposit. An event type outside the alternatives
    # is kept last so the detector can refuse it.
    stated = status.get("alternatives") if isinstance(status, Mapping) else None
    values = [str(a.get("value")) for a in (stated or ()) if isinstance(a, Mapping)]
    groups: dict[str, set[str]] = {v: set() for v in values}
    for g in basis.get("conflict_groups") or ():
        for assertion in g.get("assertions") or ():
            e = by_id.get(str(assertion).rsplit("/", 1)[0])
            if e is not None:
                groups.setdefault(str(e.event_type), set()).add(e.event_id)
    order = values + sorted(set(groups) - set(values))
    issues = res.get("issues") or ()
    collision = sorted(
        {
            str(eid)
            for i in issues
            if isinstance(i, Mapping) and i.get("code") == "PMID_ROLE_COLLISION"
            for eid in i.get("event_ids") or ()
            if eid in by_id and by_id[eid].matched_by == "pmid"
        }
    )
    hits = res.get("notice_hit_count")
    notice_hits = hits if isinstance(hits, int) and not isinstance(hits, bool) and hits >= 0 else None
    return dt1.Lookup(
        state=str(res.get("lookup_state")),
        projection=present,
        status=status.get("status") if present else None,  # type: ignore[union-attr]
        value=status.get("value") if present else None,  # type: ignore[union-attr]
        basis_reasons=tuple(str(r) for r in basis.get("reasons") or ()),
        conflict_groups=tuple((t, tuple(sorted(groups[t]))) for t in order),
        collision=tuple(collision),
        budget_refused=any(isinstance(i, Mapping) and i.get("code") == LIMIT_CODE for i in issues),
        events=events,
        notice_hits=notice_hits,
    )


def _query(doi: str | None, pmid: str | None) -> str:
    return canon({"doi": doi, "pmid": pmid}).decode()


def keys_of(cand: Mapping[str, Any]) -> tuple[str | None, str | None]:
    d = next((k["normalized"] for k in cand["keys"] if k["scheme"] == "doi"), None)
    p = next((k["normalized"] for k in cand["keys"] if k["scheme"] == "pmid"), None)
    return d, p


def lookup_roles(cand: Mapping[str, Any]) -> list[tuple[str, str]]:
    """``Lambda(c)`` of MM 4.5 as (role, canonical query): Q1 of each key, and Q2 for a PAIR."""
    d, p = keys_of(cand)
    out = []
    if d is not None:
        out.append((dt1.Q1_DOI, _query(d, None)))
    if p is not None:
        out.append((dt1.Q1_PMID, _query(None, p)))
    if cand["shape"] == "PAIR":
        out.append((dt1.Q2, _query(d, p)))
    return out


def candidate_view(
    cand: Mapping[str, Any], unit: Mapping[str, Any], lookups: Mapping[str, dt1.Lookup]
) -> dt1.Candidate:
    d, p = keys_of(cand)
    return dt1.Candidate(
        eligibility=unit["eligibility"],
        eligibility_reason=unit["reason"],
        shape=cand["shape"],
        doi=d,
        pmid=p,
        taint=tuple(cand["taint"]),
        multi="CO_REPORTED_MULTIPLE" in cand["flags"],
        lookups=tuple((role, lookups[q]) for role, q in lookup_roles(cand)),
    )


class _Items:
    """The evidence items of one DETECT run, by id. An id that would name two different items is refused (B-8)."""

    def __init__(self) -> None:
        self.items: dict[str, dict[str, Any]] = {}

    def add(self, kind: str, obs: str, pointer: str, refs: Iterable[str], value: Any) -> str:
        eid = ids.evidence_id(obs, pointer, kind)
        item = {
            "evidence_id": eid,
            "observation": obs,
            "pointer": pointer,
            "kind": kind,
            "refs": sorted(set(refs)),
            "value": value,
        }
        known = self.items.get(eid)
        if known is not None and known != item:
            raise DetectFailure(
                dt1.ADAPTER_INCONSISTENT,
                f"evidence id {eid} ({kind} at {pointer}) would name two different items (B-8 guard)",
            )
        self.items[eid] = item
        return eid


class _Run:
    """One DETECT run over committed content."""

    def __init__(self, inp: DetectInput) -> None:
        self.inp = inp
        ci = inp.candidate_inputs
        self.units = {u["unit_id"]: u for u in ci["units"]}
        plan = inp.lookup_plan
        self.index_obs = plan["index_identity"]
        self.observations: dict[str, str] = {}
        for entry in plan["lookups"]:
            q = canon(entry["query"]).decode()
            if self.observations.setdefault(q, entry["observation"]) != entry["observation"]:
                raise DetectFailure(dt1.ADAPTER_INCONSISTENT, f"the lookup plan answers query {q} twice")
        self.blobs: dict[str, Any] = {}
        self.views: dict[str, dt1.Lookup] = {}
        self.extraction = ci["extraction"]
        doc = inp.read_blob(self.extraction)
        # identifier_occurrence evidence id -> (pointer, key) of the extraction (NORMALIZE's /identifiers/j items)
        self.occurrence: dict[str, tuple[str, tuple[str, str] | None]] = {}
        for j, ident in enumerate(doc["identifiers"]):
            pointer = f"/identifiers/{j}"
            norm = ident.get("normalization") or {}
            key = (ident["scheme"], norm["normalized"]) if norm.get("valid") and norm.get("normalized") else None
            self.occurrence[ids.evidence_id(self.extraction, pointer, "identifier_occurrence")] = (pointer, key)
        self.items = _Items()
        self.index_ev = self.items.add("index_identity", self.index_obs, "", [], None)

    def observation(self, query: str) -> tuple[str, Mapping[str, Any]]:
        digest = self.observations.get(query)
        if digest is None:
            raise DetectFailure(dt1.ADAPTER_INCONSISTENT, f"no committed lookup observation answers {query}")
        if digest not in self.blobs:
            obs = self.inp.read_blob(digest)
            if canon(obs.get("query")).decode() != query:
                raise DetectFailure(dt1.ADAPTER_INCONSISTENT, f"lookup observation {digest} answers another query")
            self.blobs[digest] = obs
            self.views[digest] = lookup_view(obs)
        return digest, self.blobs[digest]

    # evidence helpers ---------------------------------------------------------------------------------------------

    def result_ev(self, obs: str) -> str:
        return self.items.add("lookup_result", obs, "/result", [self.index_ev], None)

    def projection_ev(self, obs: str) -> str:
        return self.items.add("lookup_result", obs, "/result/projection/retraction_status", [self.result_ev(obs)], None)

    def event_ev(self, obs: str, position: int) -> str:
        return self.items.add("lookup_event", obs, f"/events/{position}", [self.result_ev(obs)], None)

    def field_ev(self, obs: str, position: int, name: str) -> str:
        return self.items.add("lookup_event", obs, f"/events/{position}/{name}", [self.event_ev(obs, position)], None)

    # one candidate ------------------------------------------------------------------------------------------------

    def candidate(self, cand: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        unit = self.units.get(cand["unit_id"])
        if unit is None:
            raise DetectFailure(dt1.ADAPTER_INCONSISTENT, f"candidate {cand['cand_ref']} names no committed unit")
        roles = lookup_roles(cand)
        obs_of = {role: self.observation(q)[0] for role, q in roles}
        view = candidate_view(cand, unit, {q: self.views[obs_of[role]] for role, q in roles})
        out = dt1.decide(view)
        if out.failure is not None:
            detail = f"candidate {cand['cand_ref']} ({cand['unit_id']}): rule {out.rule}"
            if out.violations:
                detail += " " + ",".join(out.violations)
            raise DetectFailure(out.failure, detail)
        if out.cls is None:
            raise AssertionError("a class rule without a class")
        if out.rule == "D-16":
            # NOT_FOUND is scoped to the sources checked (SPEC D-16, provenance = checked sources): a no_record
            # answer that names no checked source is outside the Stage 02 contract (independent review F4).
            res = self.blobs[obs_of[str(view.deciding_role)]]["result"]
            checked = res.get("checked_sources")
            if not (
                isinstance(checked, list)
                and checked
                and all(isinstance(s, Mapping) and isinstance(s.get("source_id"), str) for s in checked)
            ):
                raise DetectFailure(
                    dt1.ADAPTER_INCONSISTENT, f"candidate {cand['cand_ref']}: NOT_FOUND names no checked source"
                )

        key_ev: list[str] = list(cand["key_evidence"])
        first_occ: dict[tuple[str, str], str] = {}
        for eid in key_ev:
            found = self.occurrence.get(eid)
            if found is None or found[1] is None:
                raise DetectFailure(dt1.ADAPTER_INCONSISTENT, f"key evidence {eid} is no keyed occurrence")
            first_occ.setdefault(found[1], eid)
        wanted = [(k["scheme"], k["normalized"]) for k in cand["keys"]]
        if sorted(first_occ) != sorted(wanted):
            raise DetectFailure(dt1.ADAPTER_INCONSISTENT, f"candidate {cand['cand_ref']}: key evidence and keys differ")

        supporting: set[str] = {unit["evidence"]["unit"], unit["evidence"]["use_eligibility"], *key_ev}
        refs = [unit["evidence"]["unit"], *first_occ.values()]
        if view.shape == "PAIR":
            coh = self.items.add(
                "coherence", obs_of[dt1.Q2], "/query", [self.result_ev(obs_of[r]) for r in dt1.ROLES], out.kappa
            )
            refs.append(coh)
            supporting.add(coh)
        pointer = self.occurrence[key_ev[0]][0] if key_ev else unit["pointer"]
        candidate = {"shape": cand["shape"], "keys": [dict(k) for k in cand["keys"]], "coherence": out.kappa}
        supporting.add(self.items.add("work_candidate", self.extraction, pointer, refs, candidate))

        rule = out.rule
        if rule in ("D-4", "D-8") or TAINT_REASONS.intersection(out.reasons):
            # Every taint reason has its chain (S-12.1): the unit's occurrences, malformed or unresolved ones included,
            # support any claim that carries one (D-4, D-8, and D-6 on a tainted unit; Step 12, A-03).
            supporting.update(unit["occurrences"])
        if view.shape != "NONE" and rule not in ("D-1", "D-2"):
            supporting.add(self.index_ev)
            supporting.update(self.result_ev(o) for o in obs_of.values())
        alternatives: list[tuple[Any, set[str]]] = []
        if rule == "D-6":
            supporting.update(self.event_ev(obs_of[r], k) for r, k in out.witnesses)
            alternatives = self.identity_alternatives(view, obs_of, out, first_occ)
        elif rule == "D-7":
            alternatives = self.type_alternatives(view, obs_of, out)
            supporting.add(self.projection_ev(obs_of[str(out.conflict_role)]))
        elif out.upstream_role is not None:
            o = obs_of[out.upstream_role]
            supporting.add(self.projection_ev(o))
            supporting.update(self.event_ev(o, e.position) for e in self.views[o].events)
        upstream: list[dict[str, Any]] = []
        if out.upstream_role is not None:
            o = obs_of[out.upstream_role]
            ev = self.result_ev(o)
            supporting.add(ev)
            upstream = [
                {"source": "stage02_projection_basis", "code": code, "evidence": ev}
                for code in dict.fromkeys(self.views[o].basis_reasons)
            ]
        value_set = sets.evidence_set(supporting, (), [a for _, a in alternatives])
        es = sha256_hex(canon(value_set))
        claim = {
            "cand_ref": cand["cand_ref"],
            "candidate": candidate,
            "class": out.cls,
            "rule": rule,
            "table_version": dt1.TABLE_VERSION,
            "status": out.status,
            "value": out.value,
            "alternatives": [{"value": v, "supporting_count": len(a)} for v, a in alternatives],
            "reasons": list(out.reasons),
            "upstream_reasons": upstream,
            "evidence_set": es,
            "supporting_count": len(value_set["supporting"]),
            "contradicting_count": 0,
        }
        claim["claim_id"] = ids.claim_id(cand["cand_ref"], out.cls, rule, dt1.TABLE_VERSION, es)
        return claim, value_set

    def identity_alternatives(
        self,
        c: dt1.Candidate,
        obs_of: Mapping[str, str],
        out: dt1.Outcome,
        first_occ: Mapping[tuple[str, str], str],
    ) -> list[tuple[Any, set[str]]]:
        """S-7.3: the work reached by the DOI and the work reached by the PMID, each with its Q1 lookup, its events and
        the key's occurrences; a side whose Q1 is unavailable is supported by the witness events' identifier field
        (S-7.3) and, when Q2 is available, by Q2's events reached by that key."""
        alts: list[tuple[Any, set[str]]] = []
        q2 = c.lookup(dt1.Q2)
        for scheme, role, key in (("doi", dt1.Q1_DOI, c.doi), ("pmid", dt1.Q1_PMID, c.pmid)):
            if key is None:
                raise AssertionError("a PAIR without both keys")
            other = "pmid" if scheme == "doi" else "doi"
            lk = c.lookup(role)
            src = role if lk is not None and lk.available else (dt1.Q2 if q2 is not None and q2.available else None)
            mine = []
            if src is not None:
                view = c.lookup(src)
                mine = [
                    e
                    for e in (view.events if view is not None else ())
                    if e.direct and e.matched_by == scheme and getattr(e, f"original_{scheme}") == key
                ]
            names = {getattr(e, f"original_{other}") for e in mine} - {None}
            work = {scheme: key, other: next(iter(names)) if len(names) == 1 else None}
            support = {self.result_ev(obs_of[role]), first_occ[(scheme, key)]}
            support.update(self.event_ev(obs_of[str(src)], e.position) for e in mine)
            if lk is None or not lk.available:  # S-7.3: always the witness field, Q2's events only beside it
                support.update(self.field_ev(obs_of[r], k, f"original_{scheme}") for r, k in out.witnesses)
            alts.append(({"reached_by": {"scheme": scheme, "normalized": key}, "work": work}, support))
        return alts

    def type_alternatives(
        self, c: dt1.Candidate, obs_of: Mapping[str, str], out: dt1.Outcome
    ) -> list[tuple[Any, set[str]]]:
        """D-7: one alternative per Stage 02 alternative of the first conflicting lookup (SPEC 7.3, "alternatives from
        Stage 02"), supported by that alternative's item and the events of its type the conflict groups name."""
        role = str(out.conflict_role)
        obs = obs_of[role]
        view = self.views[obs]
        stated = (self.blobs[obs]["result"]["projection"]["retraction_status"].get("alternatives")) or []
        position = {e.event_id: e.position for e in view.events}
        alts = []
        for i, (value, eids) in enumerate(view.conflict_groups):
            if value not in dt1.POSITIVE or i >= len(stated):
                raise DetectFailure(
                    dt1.ADAPTER_INCONSISTENT, f"a conflict names type {value!r} outside the alternatives"
                )
            item = self.items.add(
                "lookup_result",
                obs,
                f"/result/projection/retraction_status/alternatives/{i}",
                [self.projection_ev(obs)],
                None,
            )
            alts.append((value, {item, *(self.event_ev(obs, position[e]) for e in eids)}))
        if len(alts) < 2:
            raise DetectFailure(dt1.ADAPTER_INCONSISTENT, "a conflicting projection with fewer than two event types")
        return alts


def dt1_detector(inp: DetectInput) -> Detection:
    """The production detector: one claim per work candidate of the committed candidate inputs (SPEC 7.3)."""
    run = _Run(inp)
    claims = [run.candidate(c) for c in inp.candidate_inputs["candidates"]]
    evidence = tuple(run.items.items[k] for k in sorted(run.items.items))
    return Detection(evidence=evidence, claims=tuple(claims), identity=DETECTOR_IDENTITY)
