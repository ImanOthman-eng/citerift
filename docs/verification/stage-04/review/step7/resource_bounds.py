"""Stage 04 Step 7: resource-bound derivation for the record, journal and blob limits (owner Step 7 item 17).

Two parts.

1. **Exact maxima of the bounded record kinds.** For each record kind whose payload has no unbounded list, a record
   with every string at its schema ``maxLength`` filled with the character whose canonical encoding is longest under
   the field's pattern, and every integer at its schema maximum, is built, validated against
   ``urn:citerift:schema:investigation:v1:journal-record`` (so it is a record Memory's schema accepts), and its
   canonical line length is measured. Canonical JSON (``ensure_ascii=False``) writes a control character as ``\\u00XX``
   (6 bytes) and a non-BMP character as 4 UTF-8 bytes; a JSON Schema ``maxLength`` counts code points.

2. **Upstream counts.** The counts that bound the unbounded lists and the number of content records are read from the
   accepted Stage 03 and Stage 02 code (never copied by hand) and combined with the controller budgets.

Usage: ``uv run python docs/verification/stage-04/review/step7/resource_bounds.py [--out FILE]``
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from citerift.investigation import ids, workflow
from citerift.investigation.blobs import MAX_BLOB_BYTES
from citerift.investigation.canonical import canon
from citerift.investigation.journal import MAX_JOURNAL_BYTES, MAX_RECORD_BYTES
from citerift.investigation.schemas import RECORD, problems
from citerift.retraction import query as stage02_query
from citerift.retraction import source as stage02_source
from citerift.wiki import bundle as stage03_bundle
from citerift.wiki import capture as stage03_capture
from citerift.wiki import extract as stage03_extract
from citerift.wiki import verify as stage03_verify

SHA = "f" * 64
AT = "2026-11-10T12:00:00.000000Z"  # every timestamp Memory writes has this fixed width
CTRL = "\x01"  # 6 bytes in canonical JSON
WIDE = "\U0001f600"  # 4 bytes in canonical JSON, the widest character a pattern without control characters allows
MAXINT = 9007199254740991
DIGEST_ITEM = len(canon([SHA, SHA])) - len(canon([SHA]))  # 67: one more digest in a list


def _record(kind: str, step: str | None, attempt: int | None, payload: dict[str, Any], root: bool) -> dict[str, Any]:
    genesis = kind == "investigation_created"  # the genesis record is seq 0
    rec = {
        "v": 1,
        "seq": 0 if genesis else MAXINT,
        "prev": SHA,  # the genesis value is a fixed 64-hex string too, so the width is the same
        "kind": kind,
        "step": step,
        "attempt": attempt,
        "at": AT,
        "root_id": SHA if root else None,
        "payload": payload,
    }
    rec["digest"] = ids.record_digest(rec)
    return rec


def _root() -> dict[str, Any]:
    return {
        "root_id": SHA,
        "subject": {
            "type": "wikipedia_article_revision",
            "identity": {"wiki": "ar", "page_id": MAXINT, "revision_id": MAXINT, "capture_sha256": SHA},
            "display": {"title": CTRL * 1024, "revision_sha1": "f" * 40},
        },
    }


def _created() -> dict[str, Any]:
    path = "/" + WIDE * 4095
    request = {
        "schema": "urn:citerift:schema:investigation:v1:request",
        "schema_version": "1.0.0",
        "mode": "retained_bundle",
        "subject": {"type": "wikipedia_article_revision", "bundle_path": path},
        "index_path": path,
        "memory_root": path,
        "config": {
            "plan_version": "plan-1",
            "budgets": {"a_max": 3, "f_max": 6},
            "fetch_policy_sha256": None,
            "live_acquire_bound": None,
        },
    }
    return {
        "request": request,
        "request_key": {"capture_sha256": SHA},
        "investigation_key": SHA,
        "investigation_id": "ffffffff-ffff-4fff-bfff-ffffffffffff",
        "config_digest": SHA,
        "stage04": {
            "engine_version": "9" * 13 + "." + "9" * 13 + "." + "9" * 12,
            "table_version": "dt-1",
            "plan_version": "plan-1",
            "schema_version": "1.0.0",
        },
        "migrated_from": None,
    }


def bounded_kinds() -> dict[str, dict[str, Any]]:
    code = "A" * 80
    detail = CTRL * 4096
    locator = CTRL * 4096
    cases: dict[str, tuple[str, str | None, int | None, dict[str, Any], bool]] = {
        "investigation_created": ("investigation_created", None, None, _created(), False),
        "step_started": ("step_started", "ACQUIRE", 9, {"step_key": SHA}, False),
        "step_interrupted": ("step_interrupted", "ACQUIRE", 9, {"step_key": SHA}, False),
        "step_deferred": (
            "step_deferred",
            "ACQUIRE",
            9,
            {"step_key": SHA, "code": "DEFERRED_RETRY_AFTER", "not_before": AT},
            False,
        ),
        "step_failed": (
            "step_failed",
            "ACQUIRE",
            9,
            {
                "step_key": SHA,
                "code": "ACQUIRE_WALL_CLOCK_EXCEEDED",
                "retryable": False,
                "reason": code,
                "detail": detail,
                "wall_clock": {"t_acq_ms": MAXINT, "elapsed_ms": MAXINT},
                "not_before": AT,
            },
            False,
        ),
        "stale_detected": (
            "stale_detected",
            None,
            None,
            {
                "changed": list(workflow.IDENTITY_NAMES),
                "recorded": dict.fromkeys(workflow.IDENTITY_NAMES, SHA),
                "current": dict.fromkeys(workflow.IDENTITY_NAMES, SHA),
            },
            True,
        ),
        "observation_recorded": (
            "observation_recorded",
            "LOOKUP",
            3,
            {
                "obs_kind": "lookup",
                "blob": SHA,
                "source_ref": {"engine": "citerift.retraction", "operation": "gather", "locator": locator},
            },
            True,
        ),
        "decision_recorded": (
            "decision_recorded",
            "DETECT",
            3,
            {"decision_id": SHA, "claim_id": SHA, "disposition": "ROUTE_NEEDS_RESOLUTION"},
            True,
        ),
        "question_opened": (
            "question_opened",
            "DETECT",
            3,
            {"question_id": SHA, "claim_id": SHA, "kind": "identity_conflict"},
            True,
        ),
    }
    out: dict[str, dict[str, Any]] = {}
    for name, (kind, step, attempt, payload, root) in cases.items():
        rec = _record(kind, step, attempt, payload, root)
        found = problems(rec, RECORD)
        if found:
            raise SystemExit(f"{name} is not a valid maximal record: {found[:2]}")
        out[name] = {"bytes": len(canon(rec)), "fraction_of_limit": round(len(canon(rec)) / MAX_RECORD_BYTES, 4)}
    # step_succeeded of ACQUIRE with k outputs: a fixed part plus 67 bytes per output.
    base = _record("step_succeeded", "ACQUIRE", 9, {"step_key": SHA, "outputs": [SHA], "root": _root()}, True)
    if problems(base, RECORD):
        raise SystemExit("step_succeeded maximal record invalid")
    out["step_succeeded (1 output)"] = {"bytes": len(canon(base)), "per_more_output": DIGEST_ITEM}
    # verification_recorded (VERIFY, W-7) with k checks: a fixed part plus one {check, passed} item per check. The
    # schema sets no maxItems; the checks are those of SPEC 9.7.
    check = {"check": "A" * 64, "passed": True}  # the longest code the common schema allows
    one = {"result": "passed", "checks": [check], "content_digest": SHA}
    ver = _record("verification_recorded", "VERIFY", 3, one, True)
    if problems(ver, RECORD):
        raise SystemExit("verification_recorded maximal record invalid")
    per_check = len(canon([check, check])) - len(canon([check]))
    out["verification_recorded (1 check)"] = {"bytes": len(canon(ver)), "per_more_check": per_check}
    return out


def upstream() -> dict[str, Any]:
    ec = stage03_extract.ExtractConfig()
    return {
        "stage03": {
            "max_refs": ec.max_refs,
            "max_candidates": ec.max_candidates,
            "max_nodes": ec.max_nodes,
            "MAX_OUTPUT_BYTES (extraction document, canonical)": stage03_extract.MAX_OUTPUT_BYTES,
            "MAX_EXTRACTION_BYTES (verify)": stage03_verify.MAX_EXTRACTION_BYTES,
            "MAX_CAPTURE_JSON": stage03_bundle.MAX_CAPTURE_JSON,
            "MAX_ARTIFACT": stage03_bundle.MAX_ARTIFACT,
            "MAX_SOURCE_BYTES": stage03_capture.MAX_SOURCE_BYTES,
            "MAX_RENDER_BYTES": stage03_capture.MAX_RENDER_BYTES,
        },
        "stage02": {
            "ROW_LIMIT": stage02_source.ROW_LIMIT,
            "FIELD_LIMIT": stage02_source.FIELD_LIMIT,
            "MAX_PAGE (relevance listing; gather events are not paged)": stage02_query.MAX_PAGE,
        },
        "controller": {
            "A_max": workflow.A_MAX,
            "F_max": workflow.F_MAX,
            "attempts_retained": 8 * workflow.A_MAX,
            "attempts_live": 7 * workflow.A_MAX + workflow.A_MAX + workflow.F_MAX,
        },
    }


def content_floor() -> int:
    """Bytes of the smallest content record: an evidence_recorded record at seq 1 with the shortest pointer, no refs
    and a null value (a measured lower bound on every content record, not an assumed one)."""
    payload = {
        "evidence_id": SHA,
        "observation": SHA,
        "pointer": "",
        "kind": "lookup_result",
        "refs": [],
        "value": None,
    }
    rec = {
        "v": 1,
        "seq": 1,
        "prev": SHA,
        "kind": "evidence_recorded",
        "step": "DETECT",
        "attempt": 1,
        "at": AT,
        "root_id": SHA,
        "payload": payload,
    }
    rec["digest"] = ids.record_digest(rec)
    found = problems(rec, RECORD)
    if found:
        raise SystemExit(f"floor record invalid: {found[:2]}")
    return len(canon(rec))


def derived(up: dict[str, Any], kinds: dict[str, Any]) -> dict[str, Any]:
    s3, s2, ctl = up["stage03"], up["stage02"], up["controller"]
    refs, cands = s3["max_refs"], s3["max_candidates"]
    floor = content_floor()
    # Execution records: 1 creation + 2 per attempt (start, close) + 1 stale_detected (SPEC 9.2, Step 4 F-11),
    # each close at most the largest step_failed record.
    exec_records = 1 + 2 * ctl["attempts_live"] + 1
    exec_bytes = (
        kinds["investigation_created"]["bytes"]
        + 2 * ctl["attempts_live"] * kinds["step_failed"]["bytes"]
        + kinds["stale_detected"]["bytes"]
    )
    # One claim's evidence list (SPEC 6.3, 6.4): its unit, every candidate-role occurrence of its key in that unit
    # (Stage 03 allows up to max_candidates in one document, hence in one unit), Q1 and Q2 lookups and the coherence
    # result. A lower bound: the lookup *events* of the key are not counted.
    claim_ids = 1 + cands + 3 + 1
    claim_bytes_lower = claim_ids * DIGEST_ITEM
    # The same list counting one evidence id per Stage 02 event the key can match: no Stage 02 constant bounds the
    # events of one key below ROW_LIMIT.
    claim_bytes_with_events = (claim_ids + s2["ROW_LIMIT"]) * DIGEST_ITEM
    # Report projections: at most one per distinct work key, at most max_candidates.
    projections_bytes = cands * DIGEST_ITEM
    # Content records of one run whose number grows with the Stage 03 caps (lower bound, lookup events excluded):
    # NORMALIZE >= one use_eligibility per unit + one identifier evidence per candidate-role occurrence;
    # LOOKUP >= one observation per distinct key (<= cands) + the index identity; DETECT >= one claim and one decision
    # per candidate (each occurrence its own key: cands candidates).
    per_run_lower = (refs + cands) + (cands + 1) + 2 * cands
    # Failed or interrupted attempts keep their content in the journal (non-authoritative, SPEC 10.2), so a valid
    # investigation that commits on its last attempt holds A_max copies.
    journal_lower = exec_bytes + ctl["A_max"] * per_run_lower * floor
    # Lookup evidence: one record per event of each key; ROW_LIMIT events for a single key are within Stage 02's caps.
    journal_with_events = journal_lower + ctl["A_max"] * s2["ROW_LIMIT"] * floor
    # Count bounds per run (SPEC 6.2 to 6.5, 7, 12). Stage 03 caps every identifier occurrence that is not excluded at
    # max_candidates (wiki/source.py Scanner._add), whatever its role, and the units at max_refs.
    units, occ = refs, cands
    pairs = min(units, occ // 2)  # a PAIR needs one DOI and one PMID key in one unit, at most one per unit
    candidates_max = occ + units  # at most one candidate per key, plus one NONE candidate per keyless unit
    counts = {
        "units": units,
        "identifier_occurrences (all roles)": occ,
        "identifiers_per_unit (no per-unit cap)": occ,
        "distinct_keys": occ,
        "lookup_operations Q1 + Q2 + index identity": occ + pairs + 1,
        "work_candidates": candidates_max,
        "claims (one per candidate)": candidates_max,
        "decisions (one per claim)": candidates_max,
        "open_questions (at most one per claim)": candidates_max,
        "lookup_events_per_key (Stage 02 ROW_LIMIT only)": s2["ROW_LIMIT"],
        "attempts retained / live": [ctl["attempts_retained"], ctl["attempts_live"]],
        "deferrals": ctl["F_max"],
        "execution_records": exec_records,
        "report_records": 1,
        "verification_recorded (exactly one, by VERIFY: W-7)": 1,
    }
    return {
        "count_bounds_per_run": counts,
        "content_record_floor_bytes (measured)": floor,
        "execution_records_max": exec_records,
        "execution_bytes_max": exec_bytes,
        "claim_evidence_ids_lower_bound": claim_ids,
        "claim_record_bytes_lower_bound": claim_bytes_lower,
        "claim_record_lower_bound_over_limit": claim_bytes_lower > MAX_RECORD_BYTES,
        "claim_record_bytes_with_one_key_at_ROW_LIMIT_events": claim_bytes_with_events,
        "report_projection_list_bytes_worst_case": projections_bytes,
        "report_record_over_limit": projections_bytes > MAX_RECORD_BYTES,
        "content_records_per_run_lower_bound (caps only, events excluded)": per_run_lower,
        "journal_bytes_lower_bound (A_max runs, events excluded)": journal_lower,
        "journal_lower_bound_over_limit": journal_lower > MAX_JOURNAL_BYTES,
        "journal_bytes_with_one_key_at_ROW_LIMIT_events": journal_with_events,
        "journal_with_events_over_limit": journal_with_events > MAX_JOURNAL_BYTES,
        "lookup_blob_bytes_lower_bound_one_key_at_ROW_LIMIT_events (one digest per event)": s2["ROW_LIMIT"]
        * DIGEST_ITEM,
        "lookup_blob_over_limit_at_one_digest_per_event": s2["ROW_LIMIT"] * DIGEST_ITEM > MAX_BLOB_BYTES,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).with_name("resource_bounds.json")))
    args = ap.parse_args()
    kinds = bounded_kinds()
    up = upstream()
    result = {
        "limits": {
            "MAX_RECORD_BYTES": MAX_RECORD_BYTES,
            "MAX_JOURNAL_BYTES": MAX_JOURNAL_BYTES,
            "MAX_BLOB_BYTES": MAX_BLOB_BYTES,
        },
        "bounded_record_kinds_max_bytes": kinds,
        "upstream": up,
        "derived": derived(up, kinds),
    }
    Path(args.out).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
