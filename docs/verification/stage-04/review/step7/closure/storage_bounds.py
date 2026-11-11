"""Stage 04 Step 7 closure: re-derivation of the record, journal and blob limits after D-047 and D-048.

Copied from ``../resource_bounds.py`` (the Step 7 derivation at ``ab0ce66``, kept unchanged as evidence; it builds
format-1 records and does not run on the closure tree) and extended:

1. **Record limit (``MAX_RECORD_BYTES``).** Every record kind is built at its schema maximum (every list at
   ``maxItems``, every string at ``maxLength`` in the character whose canonical encoding is longest under its pattern,
   integers at their maximum), validated against the format-2 record schema, and measured. A kind whose maximum is
   within the limit is PROVEN for every valid record of that kind. For ``claim_recorded`` a sum-of-field-maxima bound
   is also given (it holds whatever the class rules allow together).
2. **Journal limit (``MAX_JOURNAL_BYTES``).** The content records of one investigation whose number grows with the
   article (SPEC 6.1 to 6.5, 7, 12; Stage 03 caps) times their size, typical and maximal, times the attempts that keep
   content (``A_max``); and the reader memory of opening a journal (measured).
3. **Blob limit (``MAX_BLOB_BYTES``).** The blobs a valid investigation writes: the Stage 03 extraction (Stage 03
   caps it), the lookup observation (D-048 derivation, ``lookup_budget.json``), the evidence and projection sets
   (D-047) and the report.

Usage: ``uv run python docs/verification/stage-04/review/step7/closure/storage_bounds.py [--out FILE]``
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(REPO / "tests" / "stage04"))

from controller_support import LOOKUP, Env, Plan, StepClock, claim_and_set, create, digest, evidence, run_once  # noqa: E402

from citerift.investigation import ids, sets, workflow  # noqa: E402
from citerift.investigation.adapters import ContentRecord, Succeeded  # noqa: E402
from citerift.investigation.blobs import MAX_BLOB_BYTES  # noqa: E402
from citerift.investigation.canonical import canon  # noqa: E402
from citerift.investigation.journal import JOURNAL_FORMAT, MAX_JOURNAL_BYTES, MAX_RECORD_BYTES  # noqa: E402
from citerift.investigation.lookup import DEFAULT_LOOKUP_EVIDENCE_BUDGET_BYTES  # noqa: E402
from citerift.investigation.memory import InvestigationMemory  # noqa: E402
from citerift.investigation.schemas import RECORD, problems  # noqa: E402
from citerift.wiki import extract as stage03_extract  # noqa: E402

SHA = "f" * 64
AT = "2026-11-10T12:00:00.000000Z"  # every timestamp Memory writes has this fixed width
CTRL = "\x01"  # 6 bytes in canonical JSON
WIDE = "\U0001f600"  # 4 bytes in canonical JSON, the widest character a pattern without control characters allows
MAXINT = 9007199254740991
# The widest DOI key the schemas allow: 512 characters, the suffix in 4-byte characters (no upper case, no controls).
DOI = "10.1234/" + WIDE * (512 - len("10.1234/"))
PMID = "9" * 9
POINTER = "/" + CTRL * 4095  # the json_pointer pattern allows control characters; maxLength 4096
CODE = "A" * 80
MIB = 1024 * 1024


def _record(kind: str, step: str | None, attempt: int | None, payload: dict[str, Any], root: bool) -> dict[str, Any]:
    genesis = kind == "investigation_created"
    rec = {
        "v": JOURNAL_FORMAT,
        "seq": 0 if genesis else MAXINT,
        "prev": SHA,
        "kind": kind,
        "step": step,
        "attempt": attempt,
        "at": AT,
        "root_id": SHA if root else None,
        "payload": payload,
    }
    rec["digest"] = ids.record_digest(rec)
    return rec


def _measure(name: str, rec: dict[str, Any]) -> dict[str, Any]:
    found = problems(rec, RECORD)
    if found:
        raise SystemExit(f"{name} is not a valid maximal record: {found[:3]}")
    n = len(canon(rec))
    return {"bytes": n, "fraction_of_limit": round(n / MAX_RECORD_BYTES, 4)}


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
        "schema_version": "2.0.0",
        "mode": "retained_bundle",
        "subject": {"type": "wikipedia_article_revision", "bundle_path": path},
        "index_path": path,
        "memory_root": path,
        "config": {
            "plan_version": "plan-1",
            "budgets": {"a_max": 3, "f_max": 6},
            "fetch_policy_sha256": None,
            "live_acquire_bound": None,
            "lookup_evidence_budget_bytes": DEFAULT_LOOKUP_EVIDENCE_BUDGET_BYTES,
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
            "schema_version": "2.0.0",
        },
        "migrated_from": None,
    }


def _claim(cls: str) -> dict[str, Any]:
    doi = {"scheme": "doi", "normalized": DOI}
    pmid = {"scheme": "pmid", "normalized": PMID}
    base: dict[str, Any] = {
        "claim_id": SHA,
        "cand_ref": SHA,
        "candidate": {"shape": "PAIR", "keys": [doi, pmid], "coherence": "COHERENT"},
        "class": cls,
        "table_version": "dt-1",
        "alternatives": [],
        "upstream_reasons": [],
        "evidence_set": SHA,
        "supporting_count": MAXINT,
        "contradicting_count": MAXINT,
    }
    if cls == "IDENTITY_CONFLICT":
        alt = {"reached_by": doi, "work": {"doi": DOI, "pmid": PMID}}
        base.update(
            rule="D-6",
            status="conflicting",
            value=None,
            candidate={"shape": "PAIR", "keys": [doi, pmid], "coherence": "INCOMPATIBLE"},
            reasons=["IDENTITY_WITNESSED", "KEY_RESULTS_DIFFER"],
            alternatives=[
                {"value": alt, "supporting_count": MAXINT},
                {"value": {**alt, "reached_by": pmid}, "supporting_count": MAXINT},
            ],
        )
    else:  # UNRESOLVED_STATUS: the only class with upstream reasons, at maxItems 192
        base.update(
            rule="D-11",
            status="uncertain",
            value=None,
            reasons=["CURRENT_EFFECT_NOT_ESTABLISHED"],
            upstream_reasons=[
                {"source": "stage02_projection_basis", "code": f"{CODE[:76]}{i:04d}", "evidence": SHA}
                for i in range(192)
            ],
        )
    return base


def _evidence(kind: str) -> dict[str, Any]:
    doi = {"scheme": "doi", "normalized": DOI}
    values: dict[str, Any] = {
        "work_candidate": {
            "shape": "PAIR",
            "keys": [doi, {"scheme": "pmid", "normalized": PMID}],
            "coherence": "UNDETERMINED",
        },
        "identifier_occurrence": {"status": "OBSERVATION_ROLE", "key": doi},
        "unit": {"source_artifact": SHA, "unit_span_sha256": SHA},
    }
    return {
        "evidence_id": SHA,
        "observation": SHA,
        "pointer": POINTER,
        "kind": kind,
        "refs": [f"{i:x}".rjust(64, "f") for i in range(8)],
        "value": values.get(kind),
    }


def record_kinds() -> dict[str, Any]:
    detail = CTRL * 4096
    out: dict[str, Any] = {
        "investigation_created": _measure("created", _record("investigation_created", None, None, _created(), False)),
        "step_started": _measure("started", _record("step_started", "ACQUIRE", 9, {"step_key": SHA}, False)),
        "step_interrupted": _measure(
            "interrupted", _record("step_interrupted", "ACQUIRE", 9, {"step_key": SHA}, False)
        ),
        "step_deferred": _measure(
            "deferred",
            _record(
                "step_deferred",
                "ACQUIRE",
                9,
                {"step_key": SHA, "code": "DEFERRED_RETRY_AFTER", "not_before": AT},
                False,
            ),
        ),
        "step_failed": _measure(
            "failed",
            _record(
                "step_failed",
                "ACQUIRE",
                9,
                {
                    "step_key": SHA,
                    "code": "ACQUIRE_WALL_CLOCK_EXCEEDED",
                    "retryable": False,
                    "reason": CODE,
                    "detail": detail,
                    "wall_clock": {"t_acq_ms": MAXINT, "elapsed_ms": MAXINT},
                    "not_before": AT,
                },
                False,
            ),
        ),
        "step_succeeded (ACQUIRE, 16 outputs, root)": _measure(
            "succeeded",
            _record(
                "step_succeeded",
                "ACQUIRE",
                9,
                {"step_key": SHA, "outputs": [f"{i:x}".rjust(64, "e") for i in range(16)], "root": _root()},
                True,
            ),
        ),
        "stale_detected": _measure(
            "stale",
            _record(
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
        ),
        "observation_recorded": _measure(
            "observation",
            _record(
                "observation_recorded",
                "LOOKUP",
                3,
                {
                    "obs_kind": "lookup",
                    "blob": SHA,
                    "source_ref": {"engine": "citerift.retraction", "operation": "gather", "locator": CTRL * 4096},
                },
                True,
            ),
        ),
        "decision_recorded": _measure(
            "decision",
            _record(
                "decision_recorded",
                "DETECT",
                3,
                {"decision_id": SHA, "claim_id": SHA, "disposition": "ROUTE_NEEDS_RESOLUTION"},
                True,
            ),
        ),
        "question_opened": _measure(
            "question",
            _record(
                "question_opened", "DETECT", 3, {"question_id": SHA, "claim_id": SHA, "kind": "identity_conflict"}, True
            ),
        ),
        "question_closed (64 ids)": _measure(
            "closed",
            _record(
                "question_closed",
                "DETECT",
                3,
                {
                    "question_id": SHA,
                    "claim_id": SHA,
                    "kind": "identity_conflict",
                    "evidence": [f"{i:x}".rjust(64, "d") for i in range(64)],
                },
                True,
            ),
        ),
        "claim_superseded (64 ids)": _measure(
            "superseded",
            _record(
                "claim_superseded",
                "DETECT",
                3,
                {
                    "old_claim_id": SHA,
                    "new_claim_id": "e" * 64,
                    "reason": CODE,
                    "new_evidence": [f"{i:x}".rjust(64, "d") for i in range(64)],
                },
                True,
            ),
        ),
        "report_recorded": _measure(
            "report",
            _record(
                "report_recorded",
                "ASSEMBLE",
                3,
                {"report": SHA, "projection_set": SHA, "projection_count": MAXINT},
                True,
            ),
        ),
        "verification_recorded (64 checks)": _measure(
            "verification",
            _record(
                "verification_recorded",
                "VERIFY",
                3,
                {
                    "result": "passed",
                    "checks": [{"check": f"{CODE[:76]}{i:04d}", "passed": True} for i in range(64)],
                    "content_digest": SHA,
                },
                True,
            ),
        ),
    }
    for kind in ("work_candidate", "identifier_occurrence", "unit", "lookup_event"):
        out[f"evidence_recorded ({kind})"] = _measure(
            f"evidence {kind}", _record("evidence_recorded", "NORMALIZE", 3, _evidence(kind), True)
        )
    for cls in ("IDENTITY_CONFLICT", "UNRESOLVED_STATUS"):
        out[f"claim_recorded ({cls})"] = _measure(
            f"claim {cls}", _record("claim_recorded", "DETECT", 3, _claim(cls), True)
        )
    # Over-approximation for claim_recorded: the largest identity-conflict claim plus all 192 upstream reasons, which
    # no class allows together; it bounds every claim whatever the class rules combine.
    both = _claim("IDENTITY_CONFLICT")
    both["upstream_reasons"] = _claim("UNRESOLVED_STATUS")["upstream_reasons"]
    over = len(canon(_record("claim_recorded", "DETECT", 3, both, True)))
    out["claim_recorded (sum of field maxima, not a valid record)"] = {
        "bytes": over,
        "fraction_of_limit": round(over / MAX_RECORD_BYTES, 4),
    }
    return out


def typical_content_sizes() -> dict[str, int]:
    """Content records as a Stage 03 article at its caps produces them: realistic pointers (the deepest index the
    caps allow), SHA-256 ids, no control characters."""
    doi = {"scheme": "doi", "normalized": "10.1234/" + "x" * 40}
    unit_ptr = "/units/19999"
    occ_ptr = "/identifiers/49999"
    shapes = {
        "unit": {"source_artifact": SHA, "unit_span_sha256": SHA},
        "use_eligibility": {"eligibility": "USE_NOT_ESTABLISHED", "reason": "NO_BOUND_USE"},
        "identifier_occurrence": {"status": "CONFIRMED", "key": doi},
        "work_candidate": {"shape": "DOI", "keys": [doi], "coherence": None},
    }
    out = {}
    for kind, value in shapes.items():
        payload = {
            "evidence_id": SHA,
            "observation": SHA,
            "pointer": occ_ptr if kind == "identifier_occurrence" else unit_ptr,
            "kind": kind,
            "refs": [SHA],
            "value": value,
        }
        out[f"evidence {kind}"] = len(canon(_record("evidence_recorded", "NORMALIZE", 1, payload, True)))
    claim = _claim("IDENTITY_CONFLICT")
    claim.update(rule="D-16", status="uncertain", value="not_found_in_checked_sources", alternatives=[])
    claim["candidate"] = {"shape": "DOI", "keys": [doi], "coherence": None}
    claim["reasons"] = ["NOT_FOUND_IN_CHECKED_SOURCES"]
    claim["supporting_count"], claim["contradicting_count"] = 6, 0
    out["claim"] = len(canon(_record("claim_recorded", "DETECT", 1, claim, True)))
    dec = {"decision_id": SHA, "claim_id": SHA, "disposition": "REPORT_NOT_FOUND"}
    out["decision"] = len(canon(_record("decision_recorded", "DETECT", 1, dec, True)))
    obs = {
        "obs_kind": "lookup",
        "blob": SHA,
        "source_ref": {"engine": "citerift.retraction", "operation": "gather", "locator": "doi:10.1234/xxxxxxxx"},
    }
    out["lookup observation"] = len(canon(_record("observation_recorded", "LOOKUP", 1, obs, True)))
    out["lookup_result evidence"] = len(
        canon(
            _record(
                "evidence_recorded",
                "DETECT",
                1,
                {
                    "evidence_id": SHA,
                    "observation": SHA,
                    "pointer": "",
                    "kind": "lookup_result",
                    "refs": [],
                    "value": None,
                },
                True,
            )
        )
    )
    return out


def journal_bound(kinds: dict[str, Any], typical: dict[str, int]) -> dict[str, Any]:
    ec = stage03_extract.ExtractConfig()
    units, occ = ec.max_refs, ec.max_candidates
    candidates = occ + units  # SPEC 6.3: one per key, plus one NONE candidate per keyless unit
    a_max = workflow.A_MAX
    # Records whose number grows with the article, per committed run (SPEC 6.1 to 6.5, 7; Step 8 design condition:
    # lookup_event evidence only for the events a claim cites as its witness, at most W per claim, here W = 4).
    counts = {
        "evidence unit": units,
        "evidence use_eligibility": units,
        "evidence identifier_occurrence": occ,
        "evidence work_candidate": candidates,
        "lookup observation": occ + min(units, occ // 2) + 1,
        "lookup_result evidence": occ + min(units, occ // 2),
        "lookup_event witness evidence (W = 4 per claim)": 4 * candidates,
        "claim": candidates,
        "decision": candidates,
    }
    size_typical = {
        "evidence unit": typical["evidence unit"],
        "evidence use_eligibility": typical["evidence use_eligibility"],
        "evidence identifier_occurrence": typical["evidence identifier_occurrence"],
        "evidence work_candidate": typical["evidence work_candidate"],
        "lookup observation": typical["lookup observation"],
        "lookup_result evidence": typical["lookup_result evidence"],
        "lookup_event witness evidence (W = 4 per claim)": typical["lookup_result evidence"] + 16,
        "claim": typical["claim"],
        "decision": typical["decision"],
    }
    worst_evidence = max(v["bytes"] for k, v in kinds.items() if k.startswith("evidence_recorded"))
    worst_claim = kinds["claim_recorded (sum of field maxima, not a valid record)"]["bytes"]
    size_max = dict.fromkeys(counts, worst_evidence)
    size_max["lookup observation"] = kinds["observation_recorded"]["bytes"]
    size_max["claim"] = worst_claim
    size_max["decision"] = kinds["decision_recorded"]["bytes"]
    run_typical = sum(counts[k] * size_typical[k] for k in counts)
    run_max = sum(counts[k] * size_max[k] for k in counts)
    return {
        "stage03_caps": {"max_refs (units)": units, "max_candidates (identifier occurrences)": occ},
        "records_per_committed_run": counts,
        "records_per_committed_run_total": sum(counts.values()),
        "typical_record_bytes": size_typical,
        "journal_bytes_one_run_typical": run_typical,
        "journal_bytes_A_max_runs_typical": a_max * run_typical,
        "journal_bytes_A_max_runs_maximal": a_max * run_max,
        "fraction_of_limit_typical": round(a_max * run_typical / MAX_JOURNAL_BYTES, 3),
        "fraction_of_limit_maximal": round(a_max * run_max / MAX_JOURNAL_BYTES, 3),
        "proven_within_limit": a_max * run_max <= MAX_JOURNAL_BYTES,
    }


def reader_memory(n: int = 3000) -> dict[str, Any]:
    """Measured cost of opening a journal of ``n`` evidence records: Python memory and time per journal byte."""

    def detect(req: Any) -> Any:
        obs = digest(LOOKUP)
        evs = [evidence("lookup_result", obs, f"/results/{i}", [], None) for i in range(n)]
        value = sets.evidence_set([e["evidence_id"] for e in evs])
        claim, _ = claim_and_set("RETRACTED_WORK_CITED", [evs[0]["evidence_id"]] * 4)
        claim["evidence_set"], claim["supporting_count"] = digest(value), n
        claim["claim_id"] = ids.claim_id(
            claim["cand_ref"], claim["class"], claim["rule"], "dt-1", claim["evidence_set"]
        )
        out = {"claims": [claim["claim_id"]]}
        recs = (*(ContentRecord("evidence_recorded", e) for e in evs), ContentRecord("claim_recorded", claim))
        return Succeeded(records=recs, blobs=(value, out), outputs=(digest(out),))

    with tempfile.TemporaryDirectory() as d:
        clock = StepClock()
        root, key = create(Path(d), clock=clock)
        started = time.monotonic()
        run_once(root, key, Plan({("DETECT", 1): detect}), Env(), clock)
        write_s = time.monotonic() - started
        size = (root / key / "journal.jsonl").stat().st_size
        tracemalloc.start()
        started = time.monotonic()
        with InvestigationMemory.open(root, key, writable=False) as m:
            records = len(m.view.records)
            peak = tracemalloc.get_traced_memory()[1]
        open_s = time.monotonic() - started
        tracemalloc.stop()
    per_byte = peak / size
    return {
        "records": records,
        "journal_bytes": size,
        "open_peak_bytes": peak,
        "open_peak_per_journal_byte": round(per_byte, 2),
        "append_ms_per_record": round(1000 * write_s / records, 2),
        "open_ms_per_record": round(1000 * open_s / records, 2),
        "open_peak_at_MAX_JOURNAL_BYTES": round(per_byte * MAX_JOURNAL_BYTES),
        "open_seconds_at_MAX_JOURNAL_BYTES_estimate": round(open_s / size * MAX_JOURNAL_BYTES),
    }


def blob_bound(journal: dict[str, Any]) -> dict[str, Any]:
    lookup = json.loads((Path(__file__).with_name("lookup_budget.json")).read_text(encoding="utf-8"))
    counts = journal["records_per_committed_run"]
    evidence_items = sum(v for k, v in counts.items() if "evidence" in k)
    sha_item = len(canon([SHA, SHA])) - len(canon([SHA]))
    worst_evidence_item = 4096 * 6 + 1200  # a maximal pointer plus the rest of a maximal evidence object
    typical_evidence_item = 400
    return {
        "stage03 extraction (Stage 03 MAX_OUTPUT_BYTES)": {
            "bytes_max": stage03_extract.MAX_OUTPUT_BYTES,
            "within_limit": stage03_extract.MAX_OUTPUT_BYTES <= MAX_BLOB_BYTES,
        },
        "lookup observation (D-048)": {
            "bytes_max": lookup["worst_observation_at_selected_bytes"],
            "within_limit": lookup["selected_fits_blob_limit"],
        },
        "evidence set (one claim; ids <= evidence items of the run)": {
            "bytes_max": evidence_items * sha_item,
            "within_limit": evidence_items * sha_item <= MAX_BLOB_BYTES,
        },
        "projection set (one per work key, <= candidates)": {
            "bytes_max": counts["claim"] * sha_item,
            "within_limit": counts["claim"] * sha_item <= MAX_BLOB_BYTES,
        },
        "report (claims[] + evidence[] inline, SPEC 11.1)": {
            "evidence_items": evidence_items,
            "bytes_typical_evidence_only": evidence_items * typical_evidence_item,
            "bytes_max_evidence_only": evidence_items * worst_evidence_item,
            "within_limit_typical": evidence_items * typical_evidence_item <= MAX_BLOB_BYTES,
            "within_limit_max": evidence_items * worst_evidence_item <= MAX_BLOB_BYTES,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).with_name("storage_bounds.json")))
    args = ap.parse_args()
    kinds = record_kinds()
    typical = typical_content_sizes()
    journal = journal_bound(kinds, typical)
    result = {
        "limits": {
            "MAX_RECORD_BYTES": MAX_RECORD_BYTES,
            "MAX_JOURNAL_BYTES": MAX_JOURNAL_BYTES,
            "MAX_BLOB_BYTES": MAX_BLOB_BYTES,
        },
        "record_kinds_max_bytes": kinds,
        "record_limit_proven": all(v["bytes"] <= MAX_RECORD_BYTES for v in kinds.values()),
        "largest_record_bytes": max(v["bytes"] for v in kinds.values()),
        "typical_content_record_bytes": typical,
        "journal": journal,
        "reader_memory": reader_memory(),
        "blobs": blob_bound(journal),
    }
    Path(args.out).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
