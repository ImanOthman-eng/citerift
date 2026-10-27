"""Schema and semantic validation of Stage 02 records (schemas/retraction/v1, SPECIFICATION.md 10).

JSON Schema checks structure; the functions here add the rules a schema cannot express: references
between fields, unique ids, conflicting alternatives that differ, ordered bounds, accounting, and the
model-to-fact boundary.
"""

from __future__ import annotations

import json
import os
from functools import cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from citerift.contracts.formats import FORMAT_CHECKER
from citerift.contracts.validate import ContractProblem, ContractSet, _conflicts_without_disagreement, load_contracts

SCHEMA_ROOT_ENV = "CITERIFT_SCHEMAS"
PREFIX = "urn:citerift:schema:retraction:v1:"
EVENT = PREFIX + "event"
LOOKUP = PREFIX + "lookup-result"
TENSION = PREFIX + "tension-report"
ADVISORY = PREFIX + "advisory-response"
CORROBORATION = PREFIX + "corroboration-manifest"
RECEIPT = PREFIX + "receipt"
BUILD_MANIFEST = PREFIX + "build-manifest"
INVESTIGATION = "urn:citerift:schema:contracts:v1:investigation"
FORBIDDEN_MODEL_KEYS = frozenset({"verified_fact", "retraction_status", "status", "value", "provenance"})
_EVENT_TYPE_OF_LABEL = {
    "Retraction": "retracted",
    "Expression of concern": "expression_of_concern",
    "Correction": "correction",
    "Reinstatement": "reinstated",
}


def schema_root() -> Path:
    """The repository ``schemas`` directory (override with CITERIFT_SCHEMAS)."""
    override = os.environ.get(SCHEMA_ROOT_ENV)
    return Path(override) if override else Path(__file__).resolve().parents[3] / "schemas"


@cache
def contracts() -> ContractSet:
    root = schema_root()
    merged = {**load_contracts(root / "contracts").schemas, **load_contracts(root / "retraction").schemas}
    return ContractSet(merged)


def _p(code: str, path: str, message: str) -> ContractProblem:
    return ContractProblem(code, path, message)


@cache
def _validator(schema_id: str) -> Any:
    cs = contracts()
    return Draft202012Validator(cs.schemas[schema_id], registry=cs.registry, format_checker=FORMAT_CHECKER)


def validate(instance: Any, schema_id: str) -> list[ContractProblem]:
    """Schema problems (plus the v1 semantic checks for an investigation record)."""
    if schema_id == INVESTIGATION:
        return contracts().validate(instance, schema_id)
    return [
        ContractProblem(
            "SCHEMA_VIOLATION", "/" + "/".join(str(p) for p in err.absolute_path), err.message, str(err.validator)
        )
        for err in sorted(_validator(schema_id).iter_errors(instance), key=lambda e: list(e.absolute_path))
    ]


# Events -------------------------------------------------------------------------------------------------


def event_semantics(ev: dict[str, Any]) -> list[ContractProblem]:
    out: list[ContractProblem] = []
    if ev["event_id"] != f"ev-{ev['ordinal']:07d}":
        out.append(_p("EVENT_ID_MISMATCH", "/event_id", "event id does not encode the record ordinal"))
    if _EVENT_TYPE_OF_LABEL.get(ev["source_label"]) != ev["event_type"]:
        out.append(_p("EVENT_TYPE_MISMATCH", "/event_type", "event type is not the mapped source label"))
    if ev["original_doi"]:
        anchor = f"doi:{ev['original_doi']}"
    elif ev["original_pmid"]:
        anchor = f"pmid:{ev['original_pmid']}"
    else:
        anchor = f"rec:{ev['ordinal']}"
    if ev["anchor"] != anchor:
        out.append(_p("ANCHOR_INCONSISTENT", "/anchor", f"expected {anchor}"))
    if ev["notice_doi"]:
        notice = f"doi:{ev['notice_doi']}"
    elif ev["notice_pmid"]:
        notice = f"pmid:{ev['notice_pmid']}"
    else:
        notice = None
    if ev["notice_key"] != notice:
        out.append(_p("NOTICE_KEY_INCONSISTENT", "/notice_key", f"expected {notice}"))
    if ev["notice_doi"] and ev["notice_doi"] == ev["original_doi"]:
        out.append(_p("NOTICE_EQUALS_ORIGINAL", "/notice_doi", "a notice key equal to the original is not a notice"))
    if ev["notice_pmid"] and ev["notice_pmid"] == ev["original_pmid"]:
        out.append(_p("NOTICE_EQUALS_ORIGINAL", "/notice_pmid", "a notice key equal to the original is not a notice"))
    for name in ("notice_date", "original_date"):
        te = ev[name]
        if te["earliest"] is not None and te["latest"] is not None and te["earliest"] > te["latest"]:
            out.append(_p("BOUNDS_DISORDERED", f"/{name}", "earliest is after latest"))
        if te["earliest"] is not None and te["reported_calendar"] is None:
            out.append(_p("BOUNDS_WITHOUT_VALUE", f"/{name}", "bounds without a reported value"))
    rc = ev["original_date"]["reported_calendar"]
    if (int(rc[:4]) if rc else None) != ev["original_year"]:
        out.append(_p("ORIGINAL_YEAR_INCONSISTENT", "/original_year", "year differs from the original date"))
    return out


def validate_event_record(ev: dict[str, Any]) -> list[ContractProblem]:
    problems = validate(ev, EVENT)
    return problems or event_semantics(ev)


# Lookups ------------------------------------------------------------------------------------------------


def _model_fields(node: Any, path: str) -> list[ContractProblem]:
    """A projection never carries model output: no model, confidence or model_inference anywhere."""
    out: list[ContractProblem] = []
    if isinstance(node, dict):
        for key in ("model", "confidence"):
            if key in node:
                out.append(_p("MODEL_IN_FACT_PATH", f"{path}/{key}", "model output in a projection"))
        if node.get("status") == "model_inference":
            out.append(_p("MODEL_IN_FACT_PATH", f"{path}/status", "model_inference in a projection"))
        for key, value in node.items():
            out += _model_fields(value, f"{path}/{key}")
    elif isinstance(node, list):
        for i, value in enumerate(node):
            out += _model_fields(value, f"{path}/{i}")
    return out


def lookup_semantics(result: dict[str, Any]) -> list[ContractProblem]:
    out: list[ContractProblem] = []
    ids = [e["event_id"] for e in result["events"]]
    if len(ids) != len(set(ids)):
        out.append(_p("DUPLICATE_ID", "/events", "an event is listed twice on one page"))
    if ids != sorted(ids):
        out.append(_p("PAGE_ORDER", "/events", "events are not in event-id order"))
    if len(ids) > result["total_event_count"]:
        out.append(_p("COUNT_INCONSISTENT", "/total_event_count", "page holds more events than the total"))
    projection = result["projection"]
    if projection is not None:
        out += _model_fields(projection, "/projection")
        out += _conflicts_without_disagreement(projection, "/projection")
        status = projection["retraction_status"]
        date = projection["retraction_date"]
        if date is not None and status.get("value") != "retracted":
            out.append(_p("DATE_WITHOUT_RETRACTION", "/projection/retraction_date", "a date needs a retraction"))
        if status.get("status") == "verified_fact" and result["lookup_state"] != "matched":
            out.append(_p("FACT_WITHOUT_MATCH", "/projection/retraction_status", "verified_fact needs a match"))
        if status.get("value") == "not_found_in_checked_sources" and result["lookup_state"] != "no_record":
            out.append(_p("ABSENCE_WITH_RECORDS", "/projection/retraction_status", "not found, yet records exist"))
    groups = result["identity"]["candidate_groups"]
    if result["lookup_state"] == "ambiguous_identity" and len(groups) < 2:
        out.append(_p("AMBIGUITY_WITHOUT_GROUPS", "/identity", "ambiguous identity needs two or more groups"))
    return out


def validate_lookup(result: dict[str, Any]) -> list[ContractProblem]:
    problems = validate(result, LOOKUP)
    return problems or lookup_semantics(result)


def subject_projection(result: dict[str, Any], created_at: str) -> dict[str, Any] | None:
    """A v1 investigation record whose subject paper carries the lookup projection (gate 02-D).

    The record is a contract check, not an investigation: it has no citations or assessments."""
    if result["projection"] is None:
        return None
    identifiers = {}
    for scheme in ("doi", "pmid"):
        q = result["query"][scheme]
        if q is not None and q["valid"]:
            identifiers[scheme] = q["normalized"]
    paper: dict[str, Any] = {"identifiers": identifiers, "retraction_status": result["projection"]["retraction_status"]}
    if result["projection"]["retraction_date"] is not None:
        paper["retraction_date"] = result["projection"]["retraction_date"]
    digest = result["evidence_digest"]
    return {
        "schema_version": "1.0.1",
        "investigation_id": f"{digest[:8]}-{digest[8:12]}-{digest[12:16]}-{digest[16:20]}-{digest[20:32]}",
        "created_at": created_at,
        "status": "completed",
        "synthetic": False,
        "subject_paper": paper,
        "citations": [],
        "assessments": [],
        "events": [],
        "limitations": [],
    }


# Tension ------------------------------------------------------------------------------------------------


def tension_semantics(report: dict[str, Any]) -> list[ContractProblem]:
    out: list[ContractProblem] = []
    base = report["base"]["result"]
    for i, r in enumerate(report["interventions"]):
        changed = sorted(k for k in base if base[k] != r["result"][k])
        if changed != sorted(r["changed_fields"]):
            out.append(_p("CHANGED_FIELDS_INCONSISTENT", f"/interventions/{i}", "changed_fields do not match results"))
        if r["intervention"] == "exclude_origin" and not 1 <= len(r["origins"]) <= 2:
            out.append(_p("ORIGIN_LIMIT", f"/interventions/{i}/origins", "exclude_origin takes one or two origins"))
    known = {sp["assertion_id"] for sp in report["source_pointers"]}
    basis = report["base"]["basis"]
    cited = set(basis.get("supporting_assertions", []))
    for group in basis.get("conflict_groups", []):
        cited |= set(group["assertions"])
    for r in report["interventions"]:
        cited |= set(r["affected_assertions"])
    for missing in sorted(cited - known):
        out.append(_p("DANGLING_REFERENCE", "/source_pointers", f"assertion {missing} has no source pointer"))
    if "control" in report["diagnostic_classes"] and len(report["diagnostic_classes"]) > 1:
        out.append(_p("CONTROL_WITH_DIAGNOSTIC", "/diagnostic_classes", "control excludes every other class"))
    text = json.dumps(report)
    for word in ('"score"', '"probability"', '"confidence"'):
        if word in text:
            out.append(_p("SCORE_FORBIDDEN", "", f"tension reports carry no {word} field"))
    return out


def validate_tension(report: dict[str, Any]) -> list[ContractProblem]:
    problems = validate(report, TENSION)
    return problems or tension_semantics(report)


# Advisory responses -------------------------------------------------------------------------------------


def _forbidden_keys(node: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(node, dict):
        found |= FORBIDDEN_MODEL_KEYS & set(node)
        for value in node.values():
            found |= _forbidden_keys(value)
    elif isinstance(node, list):
        for value in node:
            found |= _forbidden_keys(value)
    return found


def advisory_problems(response: Any, candidate_ids: set[str], pointers: set[str]) -> list[ContractProblem]:
    """Every reason an advisory response must become an abstention (SPECIFICATION.md 12.1)."""
    if isinstance(response, dict) and (bad := _forbidden_keys(response)):
        return [_p("FORBIDDEN_KEY", "", f"forbidden keys {sorted(bad)}")]
    problems = validate(response, ADVISORY)
    if problems:
        return problems
    out = []
    if response["decision"] == "select" and response["candidate_id"] not in candidate_ids:
        out.append(_p("UNKNOWN_CANDIDATE", "/candidate_id", "candidate was not supplied"))
    for p in response["cited_pointers"]:
        if p not in pointers:
            out.append(_p("UNSUPPLIED_POINTER", "/cited_pointers", f"{p} is not in the bundle"))
    return out


def index_semantics(counts: dict[str, Any]) -> list[ContractProblem]:
    out = []
    if counts["records"] != counts["accepted"] + counts["quarantined"]:
        out.append(_p("ACCOUNTING", "/counts", "records != accepted + quarantined"))
    if counts["physical_lines"] != counts["header_lines"] + counts["record_lines"] + counts["blank_lines"]:
        out.append(_p("ACCOUNTING", "/counts", "line accounting does not add up"))
    return out
