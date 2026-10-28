"""CITERIFT Evidence Tension v0 (SPECIFICATION.md 11.2).

Evidence Tension asks one question of a fixed policy: which declared parts of the evidence does the result
rest on? Each intervention builds a hypothetical view of the gathered evidence (a copy; nothing is written)
and reruns the same reducer. The report lists which comparison fields change. It gives no score and no
probability, and it never searches over subsets: each intervention is one O(|E|) pass.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from citerift.retraction import policy
from citerift.retraction.canonical import digest
from citerift.retraction.query import Evidence

TENSION_VERSION = "citerift-evidence-tension/0.3.0"
INTERVENTIONS = ("collapse_shared_origin", "exclude_origin", "exclude_ambiguous_links", "require_temporal_bounds")
MAX_ORIGINS_PER_CALL = 2
CLASS_FIELDS = {
    "origin_dependence": (
        "lookup_state",
        "retraction_status.status",
        "retraction_status.value",
        "retraction_date.status",
        "retraction_date.value",
    ),
}


class TensionError(ValueError):
    pass


def set_digest(es: policy.EvidenceSet) -> str:
    """Digest of an evidence set or view: assertions, dates, sources and flags, in canonical order."""
    return digest(
        {
            "state": es.state,
            "identity": es.identity,
            "anchor": es.anchor,
            "collapse": es.collapse,
            "relevant_gap": es.relevant_gap,
            "supersessions": sorted(list(s) for s in es.supersessions),
            "checked_sources": sorted(digest(s) for s in es.checked_sources),
            "assertions": sorted(
                (
                    {
                        "id": a.assertion_id,
                        "origin": a.origin,
                        "type": a.type,
                        "notice_key": a.notice_key,
                        "anchor": a.anchor,
                        "bridged": a.bridged,
                        "depends_on": list(a.depends_on),
                        "dependence": a.dependence,
                        "notice_date": None if a.notice_date is None else a.notice_date.to_json(),
                    }
                    for a in es.assertions
                ),
                key=lambda d: str(d["id"]),
            ),
        }
    )


def _identity_after(es: policy.EvidenceSet, assertions: list[policy.TypedAssertion]) -> str:
    if es.state != "matched":
        return es.identity
    return "bridged" if any(a.bridged for a in assertions) else "exact"


def view(es: policy.EvidenceSet, name: str, origins: tuple[str, ...] = ()) -> tuple[policy.EvidenceSet, list[str]]:
    """Return (view, affected assertion ids). The input evidence set is never changed."""
    if name == "collapse_shared_origin":
        support = policy.reduce(es)["basis"]["supporting_assertions"]
        by_origin: dict[str, list[str]] = {}
        for a in es.assertions:
            if a.assertion_id in support:
                by_origin.setdefault(a.origin, []).append(a.assertion_id)
        affected = sorted(i for ids in by_origin.values() if len(ids) > 1 for i in ids)
        return replace(es, collapse=True), affected
    if name == "exclude_origin":
        if not origins or len(origins) > MAX_ORIGINS_PER_CALL:
            raise TensionError(f"exclude_origin takes 1 to {MAX_ORIGINS_PER_CALL} origins")
        drop = set(origins)
        kept = [a for a in es.assertions if a.origin not in drop and not drop & set(a.depends_on)]
        affected = sorted(a.assertion_id for a in es.assertions if a not in kept)
        sources = tuple(s for s in es.checked_sources if s.get("source_id") not in drop)
        if not kept:
            sources = ()
        return replace(
            es, assertions=tuple(kept), checked_sources=sources, identity=_identity_after(es, kept)
        ), affected
    if name == "exclude_ambiguous_links":
        # Bridged assertions include Crossref relations reached through a co-occurring DOI (C-25).
        exact_anchors = {a.anchor for a in es.assertions if a.event_id is not None and not a.bridged}
        kept = []
        affected = []
        for a in es.assertions:
            if a.bridged or (a.event_id is None and a.anchor not in exact_anchors):
                affected.append(a.assertion_id)
                continue
            if a.notice_ambiguous and a.notice_key is not None:
                affected.append(a.assertion_id)
                kept.append(replace(a, notice_key=None))
            else:
                kept.append(a)
        return replace(es, assertions=tuple(kept), identity=_identity_after(es, kept)), sorted(affected)
    if name == "require_temporal_bounds":
        out = []
        affected = []
        for a in es.assertions:
            withheld = a.notice_date.without_unjustified_value() if a.notice_date is not None else None
            if withheld is not None and withheld != a.notice_date:
                affected.append(a.assertion_id)
                out.append(replace(a, notice_date=withheld))
            else:
                out.append(a)
        return replace(es, assertions=tuple(out)), sorted(affected)
    raise TensionError(f"unknown intervention {name!r}")


def _changed(base: dict[str, Any], other: dict[str, Any]) -> list[str]:
    return sorted(k for k in policy.COMPARISON_FIELDS if base[k] != other[k])


def run_intervention(es: policy.EvidenceSet, name: str, origins: tuple[str, ...] = ()) -> dict[str, Any]:
    base = policy.reduce(es)
    v, affected = view(es, name, origins)
    reduced = policy.reduce(v)
    changed = _changed(base["compare"], reduced["compare"])
    applicable = bool(affected) or (name == "exclude_origin" and v.checked_sources != es.checked_sources)
    out: dict[str, Any] = {
        "intervention": name,
        "origins": list(origins),
        "applicable": applicable,
        "result": reduced["compare"],
        "changed_fields": changed,
        "affected_assertions": affected,
        "reason_codes": reduced["basis"]["reasons"],
        "evidence_digest": set_digest(v),
    }
    if name == "exclude_origin":
        out["dependence_unknown"] = sorted(a.assertion_id for a in v.assertions if a.dependence == "unknown")
    if not applicable:
        out["not_applicable_reason"] = {
            "collapse_shared_origin": "NO_ORIGIN_WITH_REPEATED_SUPPORT",
            "exclude_origin": "ORIGIN_NOT_IN_EVIDENCE",
            "exclude_ambiguous_links": "NO_AMBIGUOUS_LINK",
            "require_temporal_bounds": "NO_UNJUSTIFIED_DATE_VALUE",
        }[name]
    return out


def diagnostic_classes(results: list[dict[str, Any]]) -> list[str]:
    classes = set()
    for r in results:
        changed = set(r["changed_fields"])
        if r["intervention"] == "collapse_shared_origin" and "support.observations" in changed:
            classes.add("redistributed_support")
        elif r["intervention"] == "exclude_origin" and changed & set(CLASS_FIELDS["origin_dependence"]):
            classes.add("origin_dependence")
        elif r["intervention"] == "exclude_ambiguous_links" and changed:
            classes.add("uncertain_identity_or_notice")
        elif r["intervention"] == "require_temporal_bounds" and changed:
            classes.add("unsupported_temporal_precision")
    return sorted(classes) or ["control"]


def origins_in(es: policy.EvidenceSet) -> list[str]:
    return sorted({a.origin for a in es.assertions})


def default_plan(es: policy.EvidenceSet) -> list[tuple[str, tuple[str, ...]]]:
    """All interventions; exclude_origin once per origin when at least two origins are present (with one
    origin the result trivially rests on it, which the report states as ``single_origin``)."""
    plan: list[tuple[str, tuple[str, ...]]] = [("collapse_shared_origin", ())]
    origins = origins_in(es)
    if len(origins) > 1:
        plan += [("exclude_origin", (o,)) for o in origins]
    plan += [("exclude_ambiguous_links", ()), ("require_temporal_bounds", ())]
    return plan


def event_log_baseline(ev: Evidence) -> dict[str, Any]:
    """The conventional design (SPECIFICATION.md 11.2): every row for the original identifier, 'retracted' if
    any row is a retraction, that row's date, and one confirming source per row or relation."""
    d, p = ev.keys.get("doi"), ev.keys.get("pmid")
    rows = [e for e in ev.events if (d and e["original_doi"] == d) or (not d and p and e["original_pmid"] == p)]
    if ev.state not in ("matched", "ambiguous_identity"):
        rows = []
    rows.sort(key=lambda e: e["ordinal"])
    relations = [c for c in ev.crossref if d and c["original_doi"] == d]
    retractions = [e for e in rows if e["event_type"] == "retracted"]
    if retractions:
        answer: str = "retracted"
        date = retractions[0]["notice_date"]["reported_calendar"]
    elif rows:
        answer = "+".join(sorted({e["event_type"] for e in rows}))
        date = None
    else:
        answer, date = "no_record", None
    return {
        "design": "event_log_baseline",
        "answer": answer,
        "date": date,
        "rows": [e["event_id"] for e in rows],
        "confirming_sources": len(rows) + len(relations),
        "diagnostics": [],
    }


def report(
    ev: Evidence, snapshot_id: str | None, plan: list[tuple[str, tuple[str, ...]]] | None = None
) -> dict[str, Any]:
    if ev.evidence_set is None:
        raise TensionError("tension needs a valid query")
    es = ev.evidence_set
    base = policy.reduce(es)
    steps = plan if plan is not None else default_plan(es)
    results = [run_intervention(es, name, origins) for name, origins in steps]
    return {
        "tension_version": TENSION_VERSION,
        "policy_version": policy.POLICY_VERSION,
        "snapshot_id": snapshot_id,
        "query": ev.query,
        "lookup_state": ev.state,
        "base": {
            "result": base["compare"],
            "retraction_status": base["retraction_status"],
            "retraction_date": base["retraction_date"],
            "basis": base["basis"],
            "evidence_digest": set_digest(es),
        },
        "interventions": results,
        "diagnostic_classes": diagnostic_classes(results),
        "origins": origins_in(es),
        "single_origin": len(origins_in(es)) == 1,
        "base_unresolved": base["compare"]["retraction_status.status"] != "verified_fact",
        "baseline": event_log_baseline(ev),
        "source_pointers": [
            {"assertion_id": a.assertion_id, "source_ref": a.source_ref}
            for a in sorted(es.assertions, key=lambda a: a.assertion_id)
        ],
        "note": "Hypothetical views of the same evidence under a fixed policy. Not a score or a probability.",
    }
