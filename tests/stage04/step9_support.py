"""Step 9 test support: concrete, contract-shaped DETECT inputs built from the abstract cases of the Step 4 model.

``concretize(case)`` turns one ``dt1_reference.Case`` (use, shape, taint, CO_REPORTED_MULTIPLE, the three abstract
lookups ``(state, projection shape, collision)`` and the witness and co-naming bits) into the committed blobs DETECT
reads: candidate inputs with one unit and one candidate, a minimal extraction (its ``identifiers``), a lookup plan,
an index identity and one lookup observation per query in Stage 02's rendered form. Every input is LABELED
SYNTHETIC: the keys are made up (``10.5555/syn.d`` and ``9000001``), and nothing here is real Retraction Watch data.

The production code under test reads these blobs exactly as it reads committed ones (``adapters.detector``). The
mapping from the abstraction to concrete content is stated once, here, and used by the differential harness
(``docs/verification/stage-04/review/step9/differential.py``) and by the tests:

- a witness bit puts a direct event naming the key with another key of the other scheme into the lookup; the
  co-naming bit puts a direct event naming both keys into each available Q1 that can hold one (else into the first
  available Q1, else into Q1(DOI));
- every state that holds events gets the events Stage 02 gives it (one direct event of the key; notice events for
  ``notice_only``), and a ``conf`` projection of a matched lookup gets two events of different types and the conflict
  group that names them;
- a collision adds a PMID_ROLE_COLLISION issue naming a PMID-matched event (a bridged one for a DOI query);
- projection shapes map to Stage 02 forms: ``vf:v`` verified_fact v, ``unc`` uncertain null (MIXED_CURRENT_EFFECT),
  ``unc:bridge_only`` uncertain null with BRIDGE_ONLY_SUPPORT, ``conf`` conflicting null (SOURCE_TYPE_CONFLICT),
  ``unc:notice``/``unc:ambiguous``/``unc:gap`` uncertain null, ``unc:not_found`` uncertain
  not_found_in_checked_sources, ``none`` the unavailable projection for ``unavailable`` and no projection otherwise;
  the malformed shapes as their names say (``unc:valued`` and ``conf:valued`` carry the value ``retracted``).
"""

from __future__ import annotations

import copy
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from citerift.investigation import ids
from citerift.investigation.adapters.detect import DetectInput
from citerift.investigation.canonical import canon, sha256_hex

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "simulations" / "stage04"))

import dt1_reference as R  # noqa: E402

D, P = "10.5555/syn.d", "9000001"
OTHER_PMID, OTHER_DOI = "9000002", "10.5555/syn.other"
LABEL = "SYNTHETIC (Step 9 test input; not Retraction Watch data)"
CHECKED_SOURCE = {"source_id": "retraction-watch", "locator": "https://example.invalid/synthetic/rw", "synthetic": True}
INDEX = {
    "snapshot_id": "rw-synthetic",
    "policy_version": "citerift-rde-policy/1.3.0",
    "lookup_schema_version": "1.1.0",
    "index_sha256": "0" * 64,
}
REASON_OF_USE = {"CITED": None, "UNUSED": "LIST_DEFINED_UNUSED", "USE_NOT_ESTABLISHED": "NO_BOUND_USE"}

# Placeholder reasons of the frozen model and the production names (review/step5/STEP5_PLACEHOLDER_MAPPING.md, D-043).
MODEL_REASON = {
    "DEFINITION_UNUSED": "LIST_DEFINED_UNUSED",
    "USE_NOT_ESTABLISHED": "NO_BOUND_USE",
    "STAGE02_BASIS_REASONS": "CURRENT_EFFECT_NOT_ESTABLISHED",
    "LOOKUP_UNAVAILABLE": "LOOKUP_QUERY_FAILED",
    "SOURCE_TYPE_CONFLICT": "RETRACTION_EVENT_TYPE_CONFLICT",
}


def event(
    eid: str, by: str, doi: str | None, pmid: str | None, *, etype: str = "retracted", via: str | None = None
) -> dict[str, Any]:
    return {
        "event_id": eid,
        "event_type": etype,
        "matched_by": by,
        "linked_via": via,
        "original_doi": doi,
        "original_pmid": pmid,
        "notice_doi": None,
        "notice_pmid": None,
        "flags": [],
        "issues": [],
    }


def projection(state: str, shape: str) -> dict[str, Any] | None:
    """The Stage 02 projection of an abstract projection shape (module docstring)."""
    if shape == "none":
        if state == "unavailable":
            return _proj("unavailable", None, ["INDEX_UNAVAILABLE"])
        return None
    table: dict[str, tuple[str, Any, list[str]]] = {
        "unc": ("uncertain", None, ["MIXED_CURRENT_EFFECT"]),
        "unc:bridge_only": ("uncertain", None, ["BRIDGE_ONLY_SUPPORT", "BRIDGED_EVIDENCE_MATERIAL"]),
        "conf": ("conflicting", None, ["SOURCE_TYPE_CONFLICT"]),
        "unc:notice": ("uncertain", None, ["NOTICE_ONLY"]),
        "unc:ambiguous": ("uncertain", None, ["IDENTITY_AMBIGUOUS"]),
        "unc:not_found": ("uncertain", "not_found_in_checked_sources", ["NOT_FOUND_IN_CHECKED_SOURCES"]),
        "unc:gap": ("uncertain", None, ["COVERAGE_GAP_RELEVANT_ROWS"]),
        "status:unavailable": ("unavailable", None, ["INDEX_UNAVAILABLE"]),
        "vf:not_found": ("verified_fact", "not_found_in_checked_sources", ["SOURCE_RECORDED_TYPE"]),
        "vf:null": ("verified_fact", None, ["SOURCE_RECORDED_TYPE"]),
        "unc:valued": ("uncertain", "retracted", ["MIXED_CURRENT_EFFECT"]),
        "conf:valued": ("conflicting", "retracted", ["SOURCE_TYPE_CONFLICT"]),
    }
    if shape.startswith("vf:") and shape[3:] in R.POSITIVE_VALUES:
        return _proj("verified_fact", shape[3:], ["SOURCE_RECORDED_TYPE"])
    status, value, reasons = table[shape]
    return _proj(status, value, reasons)


def _proj(status: str, value: Any, reasons: list[str]) -> dict[str, Any]:
    return {
        "retraction_status": {"status": status, "value": value},
        "retraction_date": None,
        "basis": {"reasons": list(reasons), "conflict_groups": [], "scope": "checked_sources"},
    }


def observation(query: dict[str, str | None], lk: R.Lookup, extra: list[dict[str, Any]], role: str) -> dict[str, Any]:
    """One lookup observation for an abstract lookup ``lk`` of ``role`` (``d``, ``p`` or ``q2``) with ``extra`` events
    (witness and co-naming events) added."""
    state, shape, collision = lk
    events: list[dict[str, Any]] = []
    by = "pmid" if role == "p" else "doi"
    base_doi, base_pmid = (None, P) if role == "p" else (D, None)
    if state in ("matched", "ambiguous_identity"):
        events.append(event(f"ev-{role}-base", by, base_doi, base_pmid))
    elif state == "notice_only":
        events.append(event(f"ev-{role}-notice", "notice", "10.5555/syn.original", "9000099"))
    proj = projection(state, shape)
    if state == "matched" and shape == "conf" and proj is not None:
        a = event(f"ev-{role}-c1", by, base_doi, base_pmid, etype="retracted")
        b = event(f"ev-{role}-c2", by, base_doi, base_pmid, etype="expression_of_concern")
        events += [a, b]
        proj["basis"]["conflict_groups"] = [
            {
                "proposition": "p",
                "types": ["expression_of_concern", "retracted"],
                "assertions": [f"{a['event_id']}/event_type", f"{b['event_id']}/event_type"],
            }
        ]
        # Stage 02 (policy.project) states one alternative per type, sorted, with the provenance of its assertions.
        proj["retraction_status"]["alternatives"] = [
            {"value": "expression_of_concern", "provenance": []},
            {"value": "retracted", "provenance": []},
        ]
    issues: list[dict[str, Any]] = []
    if collision:
        if role == "p":
            named = f"ev-{role}-base"
        else:
            bridged = event(f"ev-{role}-bridge", "pmid", None, "9000077", via="pmid_cooccurrence")
            events.append(bridged)
            named = bridged["event_id"]
        issues.append({"code": "PMID_ROLE_COLLISION", "event_ids": [named], "distinct_notice_doi": []})
    events += copy.deepcopy(extra)
    return {
        "schema": "urn:citerift:schema:investigation:v1:lookup-observation",
        "schema_version": "1.0.0",
        "label": LABEL,
        "query": query,
        "index": INDEX,
        "budget_bytes": 16777216,
        "result": {"lookup_state": state, "projection": proj, "issues": issues, "checked_sources": [CHECKED_SOURCE]},
        "events": events,
        "event_count": len(events),
    }


def witness_events(c: R.Case) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {"d": [], "p": [], "q2": []}
    if c.wd:
        out["d"].append(event("ev-wd", "doi", D, OTHER_PMID))
    if c.wp:
        out["p"].append(event("ev-wp", "pmid", OTHER_DOI, P))
    if c.w2:
        out["q2"].append(event("ev-w2", "doi", D, OTHER_PMID))
    if c.coname:
        slots = {"d": c.d, "p": c.p}
        avail = [s for s, lk in slots.items() if lk is not None and lk[0] != "unavailable"]
        able = [s for s in avail if slots[s] is not None and slots[s][0] in ("matched", "ambiguous_identity")]  # type: ignore[index]
        for s in able or avail[:1] or ["d"]:
            out[s].append(event(f"ev-co-{s}", "doi" if s == "d" else "pmid", D, P))
    return out


def keys_of_shape(shape: str) -> list[dict[str, str]]:
    return {
        "NONE": [],
        "DOI": [{"scheme": "doi", "normalized": D}],
        "PMID": [{"scheme": "pmid", "normalized": P}],
        "PAIR": [{"scheme": "doi", "normalized": D}, {"scheme": "pmid", "normalized": P}],
    }[shape]


def concretize(c: R.Case) -> tuple[DetectInput, dict[str, Any]]:
    """The committed DETECT input of one abstract case, and its blobs by digest."""
    blobs: dict[str, Any] = {}

    def put(value: Any) -> str:
        digest = sha256_hex(canon(value))
        blobs[digest] = value
        return digest

    keys = keys_of_shape(c.shape)
    identifiers = [
        {
            "id": f"id-{i}",
            "scheme": k["scheme"],
            "unit_id": "un-1",
            "normalization": {"valid": True, "normalized": k["normalized"], "scheme": k["scheme"]},
        }
        for i, k in enumerate(keys)
    ]
    extraction = {"label": LABEL, "identifiers": identifiers}
    ext = put(extraction)
    occ = [ids.evidence_id(ext, f"/identifiers/{i}", "identifier_occurrence") for i in range(len(keys))]
    unit_ref = "1" * 64
    unit = {
        "unit_id": "un-1",
        "pointer": "/units/0",
        "unit_ref": unit_ref,
        "eligibility": c.use,
        "reason": REASON_OF_USE[c.use],
        "taint": sorted(c.taint),
        "evidence": {
            "unit": ids.evidence_id(ext, "/units/0", "unit"),
            "use_eligibility": ids.evidence_id(ext, "/units/0", "use_eligibility"),
        },
        "occurrences": occ,
    }
    cand = {
        "cand_ref": ids.cand_ref(unit_ref, keys),
        "unit_id": "un-1",
        "unit_ref": unit_ref,
        "shape": c.shape,
        "keys": keys,
        "flags": ["CO_REPORTED_MULTIPLE"] if c.multi else [],
        "taint": sorted(c.taint),
        "key_evidence": occ,
    }
    extra = witness_events(c)
    lookups = []
    for role, lk, q in (
        ("d", c.d, {"doi": D, "pmid": None}),
        ("p", c.p, {"doi": None, "pmid": P}),
        ("q2", c.q2, {"doi": D, "pmid": P}),
    ):
        if lk is not None:
            lookups.append({"query": q, "observation": put(observation(q, lk, extra[role], role))})
    inputs = {
        "schema": "urn:citerift:schema:investigation:v1:candidate-inputs",
        "schema_version": "1.0.0",
        "root_id": "2" * 64,
        "bundle": "3" * 64,
        "extraction": ext,
        "identity_evidence": {"bundle_identity": "4" * 64, "extraction_identity": "5" * 64},
        "units": [unit],
        "candidates": [cand],
        "observation_keys": [],
        "queries": [e["query"] for e in lookups],
    }
    plan = {
        "schema": "urn:citerift:schema:investigation:v1:lookup-plan",
        "schema_version": "1.0.0",
        "candidate_inputs": put(inputs),
        "index_identity": put(INDEX),
        "lookups": lookups,
    }
    return DetectInput(inputs, plan, blobs.__getitem__, {"root_id": "2" * 64}), blobs


def expected(c: R.Case) -> dict[str, Any]:
    """The frozen model's decision with its placeholder reasons in production names."""
    dec = R.decide(c)
    if dec["kind"] == "failure":
        return {"rule": dec["rule"], "failure": dec["reasons"][0]}
    return {**dec, "reasons": sorted(MODEL_REASON.get(r, r) for r in dec["reasons"])}


def model_key(dec: Mapping[str, Any]) -> tuple[Any, ...]:
    return tuple(sorted((k, str(v)) for k, v in dec.items()))
