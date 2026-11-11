"""Owner decisions D-053 and D-054: the journal limit, the per-file blob limit and the total storage of one
investigation, for journal format 3 (evidence batches) and report 3.0.0 (manifest graph).

Builds on the Step 7 closure derivation (``../closure/storage_bounds.py``, kept unchanged as the format-2 record): its
maximal record builders are reused for every kind that format 3 keeps; the evidence record is replaced by the batch
record. Nothing here is measured on time; ``perf.py`` measures time and memory.

1. **Records.** The largest legal record of each format-3 kind, validated against the format-3 record schema.
2. **Journal** (``MAX_JOURNAL_BYTES``, 512 MiB, not raised). Every record a legal investigation can write at the
   Stage 03 caps: creation; every execution record of every attempt (``A_max`` attempts per step, ``A_max + F_max``
   for ACQUIRE, deferrals and interruptions included); the content of every attempt, also of attempts that failed
   after writing it (``A_max`` copies); report and verification records. Two representations of the per-candidate
   records (lookup observations, claims, decisions, questions) are computed: **as now** (one record each, only
   evidence batched; owner decision pending) and **batched** like evidence (the option recommended to the owner).
3. **Blobs** (``MAX_BLOB_BYTES``, 256 MiB): every blob kind with its bound and the reason it holds.
4. **Total storage**: the mathematical worst case, the operational bound under the configured budgets, and what the
   pinned index gives.

Usage: ``uv run python docs/verification/stage-04/review/step7/d053/bounds.py [--out FILE]``
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[5]
sys.path.insert(0, str(REPO / "tests" / "stage04"))

from citerift.investigation import batches, report, workflow  # noqa: E402
from citerift.investigation.blobs import MAX_BLOB_BYTES  # noqa: E402
from citerift.investigation.canonical import canon  # noqa: E402
from citerift.investigation.journal import JOURNAL_FORMAT, MAX_JOURNAL_BYTES, MAX_RECORD_BYTES  # noqa: E402
from citerift.wiki import capture as stage03_capture  # noqa: E402
from citerift.wiki import extract as stage03_extract  # noqa: E402

MIB = 1024 * 1024


def _closure() -> Any:
    spec = importlib.util.spec_from_file_location(
        "closure_storage_bounds", HERE.parent / "closure" / "storage_bounds.py"
    )
    if not (spec is not None and spec.loader is not None):
        raise SystemExit("check failed: spec is not None and spec.loader is not None")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SB = _closure()
SHA = SB.SHA


def record_kinds() -> dict[str, Any]:
    """The closure's maximal records of every kind format 3 keeps, plus the evidence batch record."""
    real = SB._measure
    SB._measure = lambda name, rec: None if name.startswith("evidence ") else real(name, rec)
    try:
        kinds = {k: v for k, v in SB.record_kinds().items() if v is not None and not k.startswith("evidence_recorded")}
    finally:
        SB._measure = real
    payload = {"batch": SHA, "batch_index": SB.MAXINT - 1, "batch_total": SB.MAXINT, "evidence_count": SB.MAXINT}
    kinds["evidence_batch_recorded"] = SB._measure("batch", SB._record("evidence_batch_recorded", "DETECT", 3, payload,
                                                                       True))  # fmt: skip
    return kinds


def typical() -> dict[str, int]:
    """Bytes with newline of the per-candidate records as a Stage 03 article at its caps produces them (closure
    ``typical_content_sizes``), the question record, and the canonical size of typical evidence items."""
    t = SB.typical_content_sizes()
    q = SB._record("question_opened", "DETECT", 1, {"question_id": SHA, "claim_id": SHA, "kind": "identity_conflict"},
                   True)  # fmt: skip
    out = {k: v + 1 for k, v in t.items() if not k.startswith("evidence") and "evidence" not in k}
    out["question"] = len(canon(q)) + 1
    return out


def evidence_bytes_per_run() -> dict[str, Any]:
    ceiling = json.loads((HERE / "part_ceiling.json").read_text(encoding="utf-8"))
    per_run = ceiling["rule_5_record_count"]["evidence_items_per_run_at_caps"]
    n = sum(per_run.values())
    typical_item = 380  # canonical bytes of the article-shaped items of part_ceiling.py (7,646,956 B / 20,000 items)
    return {
        "items": n,
        "typical_bytes": n * typical_item,
        "max_bytes": ceiling["rule_5_record_count"]["E_run_max_bytes"],
    }


def journal(kinds: dict[str, Any], tsize: dict[str, int]) -> dict[str, Any]:
    ec = stage03_extract.ExtractConfig()
    units, occ = ec.max_refs, ec.max_candidates
    candidates = occ + units
    a_max, f_max = workflow.A_MAX, workflow.F_MAX
    c = batches.MAX_PART_BYTES
    rmax = {k.split(" ")[0]: v["bytes"] + 1 for k, v in kinds.items()}  # with newline; first word is the kind
    batch_rec = rmax["evidence_batch_recorded"]
    ev = evidence_bytes_per_run()

    # Fixed records of one investigation (independent of the article), at their maximal sizes.
    attempts = {s: a_max for s in workflow.STEPS if s != "ACQUIRE"} | {"ACQUIRE": a_max + f_max}
    execution = sum(
        n * (rmax["step_started"] + max(rmax["step_failed"], rmax["step_succeeded"])) for n in attempts.values()
    )
    execution += sum(n * rmax["step_interrupted"] for n in attempts.values())  # an interruption before each terminal
    fixed = {
        "investigation_created": rmax["investigation_created"],
        "execution records of every attempt (incl. interruptions)": execution,
        "stale_detected": rmax["stale_detected"],
        "ACQUIRE, EXTRACT observations (every attempt)": (attempts["ACQUIRE"] + a_max) * rmax["observation_recorded"],
        "report_recorded (every ASSEMBLE attempt)": a_max * rmax["report_recorded"],
        "verification_recorded (every VERIFY attempt)": a_max * rmax["verification_recorded"],
        "questions closed (<= questions)": 0,  # Stage 04 closes none (SPEC 8.5); listed for completeness
    }
    fixed_total = sum(fixed.values())

    ceiling = json.loads((HERE / "part_ceiling.json").read_text(encoding="utf-8"))
    largest_item = max(ceiling["rule_1_largest_item"]["E_max"], rmax["observation_recorded"], rmax["claim_recorded"])
    # A part closes only when the next item (<= largest_item bytes, plus a comma) would pass the ceiling, so a closed
    # part is larger than c - largest_item - 1. Each item adds its size plus at most one comma, at most twice its size,
    # so the items of a closed part total at least (c - largest_item - envelope) / 2 bytes. Rigorous for any item mix.
    per_closed_part = (c - largest_item - batches.BATCH_ENVELOPE) // 2
    series = sum(1 for kinds in workflow.CONTENT_KINDS.values() if "evidence_batch_recorded" in kinds)

    def batch_records(total_bytes: int) -> int:
        return math.ceil(total_bytes / per_closed_part) + series  # each series may end in one partial part

    lookup_obs = occ + min(units, occ // 2) + 1
    per_candidate_counts = {"lookup observation": lookup_obs, "claim": candidates, "decision": candidates,
                            "question": candidates}  # fmt: skip
    size_typ = {"lookup observation": tsize["lookup observation"], "claim": tsize["claim"],
                "decision": tsize["decision"], "question": tsize["question"]}  # fmt: skip
    size_max = {"lookup observation": rmax["observation_recorded"],
                "claim": kinds["claim_recorded (sum of field maxima, not a valid record)"]["bytes"] + 1,
                "decision": rmax["decision_recorded"], "question": rmax["question_opened"]}  # fmt: skip

    def option(per_candidate_batched: bool, sizes: dict[str, int], ev_bytes: int) -> dict[str, Any]:
        content = batch_records(ev_bytes) * batch_rec
        if per_candidate_batched:
            content += sum(batch_records(per_candidate_counts[k] * sizes[k]) * batch_rec for k in sizes)
        else:
            content += sum(per_candidate_counts[k] * sizes[k] for k in sizes)
        total = fixed_total + a_max * content  # every attempt may write its content and then fail
        return {
            "content_bytes_one_attempt_each_step": content,
            "journal_bytes": total,
            "fraction_of_limit": round(total / MAX_JOURNAL_BYTES, 4),
            "headroom_factor": round(MAX_JOURNAL_BYTES / total, 1),
            "proven_within_limit": total <= MAX_JOURNAL_BYTES,
        }

    return {
        "limit": MAX_JOURNAL_BYTES,
        "stage03_caps": {
            "units (max_refs)": units,
            "identifier occurrences (max_candidates)": occ,
            "candidates": candidates,
        },
        "A_max": a_max,
        "F_max": f_max,
        "max_part_bytes": c,
        "fixed_records_bytes": fixed,
        "fixed_total_bytes": fixed_total,
        "evidence_per_run": ev,
        "per_candidate_records_per_run": per_candidate_counts,
        "per_candidate_record_bytes_typical": size_typ,
        "per_candidate_record_bytes_max": size_max,
        "as_now (evidence batched, per-candidate records one each)": {
            "typical": option(False, size_typ, ev["typical_bytes"]),
            "maximal": option(False, size_max, ev["max_bytes"]),
        },
        "batched (evidence and per-candidate records batched)": {
            "typical": option(True, size_typ, ev["typical_bytes"]),
            "maximal": option(True, size_max, ev["max_bytes"]),
        },
    }


def blobs(j: dict[str, Any]) -> dict[str, Any]:
    lookup = json.loads((HERE.parent / "closure" / "lookup_budget.json").read_text(encoding="utf-8"))
    c = batches.MAX_PART_BYTES
    ceiling = json.loads((HERE / "part_ceiling.json").read_text(encoding="utf-8"))
    e_max = ceiling["rule_1_largest_item"]["E_max"]
    items = j["evidence_per_run"]["items"]
    candidates = j["stage03_caps"]["candidates"]
    sha_item = len(canon([SHA, SHA])) - len(canon([SHA]))
    obs_max = lookup["worst_observation_at_selected_bytes"]
    claim_max = j["per_candidate_record_bytes_max"]["claim"]
    # A claim entry: the claim, decision, question, unit anchor and the checked sources of its deciding lookup, which
    # are part of that lookup's observation (D-048), so at most the observation's bound.
    entry_max = claim_max + 4096 + obs_max
    chunk_refs_max = candidates + 2  # every entry its own chunk, plus the partial chunks
    manifest_max = (
        64 * 1024
        + chunk_refs_max * len(canon({"chunk": SHA, "count": SB.MAXINT})) * 3
        + (math.ceil(ceiling["rule_5_record_count"]["E_run_max_bytes"] / c) + 2)
        * len(canon({"batch": SHA, "count": SB.MAXINT}))
    )
    source = 6 * (stage03_capture.MAX_SOURCE_BYTES + stage03_capture.MAX_RENDER_BYTES)
    rows = {
        "Stage 03 extraction (byte-for-byte, no wrapper)": {
            "bound_bytes": stage03_extract.MAX_OUTPUT_BYTES,
            "why": "Stage 03 refuses a worker output over MAX_OUTPUT_BYTES; the worker writes canonical_bytes, the "
            "same encoding as Stage 04 canon (sort_keys, compact separators, UTF-8, no ASCII escaping), so the blob "
            "is the worker's output byte for byte. Equal to the limit: no headroom, never over it.",
        },
        "ACQUIRE observation (bundle)": {
            "bound_bytes": source + 64 * 1024,
            "why": "Conditional on the Step 8 representation: the capture document plus at most the bundle's source "
            "(<= 4 MiB) and render (<= 16 MiB), each embedded as a JSON string (<= 6 bytes per input byte). The "
            "capture document is not bounded by its schema (attempts, issues, failure_artifacts have no maxItems); "
            "measured 3,796 to 5,235 bytes on retained bundles; 64 KiB is allowed. Over the limit is BLOB_TOO_LARGE, "
            "a STORAGE_ERROR (fail closed). Step 8 design condition.",
        },
        "LOOKUP observation (D-048)": {"bound_bytes": obs_max, "why": "D-048 budget, lookup_budget.json"},
        "evidence batch": {
            "bound_bytes": max(c, e_max + batches.BATCH_ENVELOPE),
            "why": "SPEC 8.8: a batch is cut at MAX_PART_BYTES; the largest legal item fits one",
        },
        "evidence set (one claim)": {
            "bound_bytes": items * sha_item + 256,
            "why": "at most every evidence id of the run",
        },
        "projection set": {"bound_bytes": candidates * sha_item + 256, "why": "at most one per candidate"},
        "report claim chunk": {
            "bound_bytes": max(c, entry_max),
            "why": "cut at MAX_PART_BYTES; an entry larger than that is a chunk of its own, and "
            "an entry is at most a maximal claim, its decision, question and anchor, and the "
            "checked sources of one lookup observation",
        },
        "report observations chunk": {"bound_bytes": c, "why": "entries are about 110 bytes"},
        "report positive-works chunk": {
            "bound_bytes": max(c, 4096 + candidates * sha_item),
            "why": "a work lists at most every claim id",
        },
        "report manifest": {
            "bound_bytes": manifest_max,
            "why": "fixed fields (< 64 KiB with identities) plus one reference per chunk and per evidence batch",
        },
        "step output manifests (workflow.manifest) and VALIDATE output": {
            "bound_bytes": 64 * 1024,
            "why": "fixed shape",
        },
    }
    for r in rows.values():
        r["within_limit"] = r["bound_bytes"] <= MAX_BLOB_BYTES
        r["fraction_of_limit"] = round(r["bound_bytes"] / MAX_BLOB_BYTES, 4)
    return rows


def total(j: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    a_max = j["A_max"]
    candidates = j["stage03_caps"]["candidates"]
    lookups = j["per_candidate_records_per_run"]["lookup observation"]
    ev = j["evidence_per_run"]
    obs_max = b["LOOKUP observation (D-048)"]["bound_bytes"]
    lookup_typ = 1300  # bytes: a no_record / single-event lookup observation (lookup_budget.json intercepts)
    math_worst = (
        MAX_JOURNAL_BYTES
        + a_max * (b["Stage 03 extraction (byte-for-byte, no wrapper)"]["bound_bytes"]
                   + b["ACQUIRE observation (bundle)"]["bound_bytes"])
        + a_max * lookups * obs_max
        + a_max * ev["max_bytes"]
        + a_max * candidates * b["evidence set (one claim)"]["bound_bytes"]
        + a_max * candidates * b["report claim chunk"]["bound_bytes"]
    )  # fmt: skip
    return {
        "mathematical_worst_case_bytes": math_worst,
        "mathematical_worst_case_note": "every attempt of every step at every cap with every blob at its bound: "
        "every lookup at the D-048 budget, every claim naming every evidence id, every claim entry carrying a "
        "maximal lookup's checked sources. Not reachable by a real article and index; no global cap is imposed "
        "(owner D-053/D-054). Disk exhaustion is a STORAGE_ERROR, never a silent truncation.",
        "operational_bound_bytes": MAX_JOURNAL_BYTES
        + b["Stage 03 extraction (byte-for-byte, no wrapper)"]["bound_bytes"]
        + b["ACQUIRE observation (bundle)"]["bound_bytes"]
        + lookups * lookup_typ
        + ev["typical_bytes"]
        + candidates * (b["evidence set (one claim)"]["bound_bytes"] // 1000 + 1500),
        "operational_note": "one committed run at the Stage 03 caps with typical item sizes, lookups of the pinned "
        "index's common shape (no record or one event), evidence sets of tens of ids, claim entries of about "
        "1.5 kB; blobs are content-addressed, so a repeated attempt with equal content adds nothing.",
        "pinned_index_observation": "The largest lookup observation the pinned index gives for any key is "
        "recorded by the D-048 derivation (closure/lookup_budget.json); every observation is within the "
        "configured budget by construction, and over it the lookup is LOOKUP_EVIDENCE_LIMIT_EXCEEDED, not a blob.",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=HERE / "bounds.json")
    args = ap.parse_args()
    kinds = record_kinds()
    j = journal(kinds, typical())
    b = blobs(j)
    result = {
        "journal_format": JOURNAL_FORMAT,
        "report_version": report.REPORT_VERSION,
        "limits": {
            "MAX_RECORD_BYTES": MAX_RECORD_BYTES,
            "MAX_JOURNAL_BYTES": MAX_JOURNAL_BYTES,
            "MAX_BLOB_BYTES": MAX_BLOB_BYTES,
            "MAX_PART_BYTES": batches.MAX_PART_BYTES,
        },
        "record_kinds_max_bytes": kinds,
        "largest_record_bytes": max(v["bytes"] for v in kinds.values()),
        "record_limit_proven": all(v["bytes"] <= MAX_RECORD_BYTES for v in kinds.values()),
        "journal": j,
        "blobs": b,
        "blob_limit_proven_except_ACQUIRE_observation": all(
            r["within_limit"] for k, r in b.items() if not k.startswith("ACQUIRE")
        ),
        "ACQUIRE_observation": "conditional on the Step 8 representation (see its row)",
        "total_storage": total(j, b),
    }
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"journal": {k: v for k, v in j.items() if k.startswith(("as_now", "batched"))},
                      "blobs": {k: (v["bound_bytes"], v["within_limit"]) for k, v in b.items()},
                      "total": {k: v for k, v in result["total_storage"].items() if k.endswith("bytes")}},
                     indent=1))  # fmt: skip


if __name__ == "__main__":
    main()
