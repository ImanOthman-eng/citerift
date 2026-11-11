"""Owner decision D-055: the record, journal, blob and total storage bounds for journal format 4.

Recomputed from the format-4 records as implemented (owner D-055: "recompute it from the actual format-4 records",
"the ~8.6 MB inference must become an executable, retained bound"). Builds on ``../d053/bounds.py`` (kept as the
format-3 record; it builds format-3 records and runs on its own tree, ``0097a93``) and on the closure's maximal record
builders (``../closure/storage_bounds.py``).

1. **Records** (``MAX_RECORD_BYTES``, 1 MiB). The largest legal record of every format-4 kind, each validated against
   the format-4 record schema; the set of kinds measured must equal the schema's kind enum.
2. **Journal** (``MAX_JOURNAL_BYTES``, 512 MiB, not raised). Every record a legal investigation can write at the
   Stage 03 caps: creation; every execution record of every attempt (``A_max`` attempts per step, ``A_max + F_max``
   for ACQUIRE: deferrals and interruptions included, failed and interrupted attempts included); the bundle,
   extraction and index-identity observations of every attempt; and for every content step ``A_max`` copies of its
   content (an attempt may write all its content and then fail): the evidence batch records (NORMALIZE, DETECT), the
   LOOKUP batch records and the DETECT candidate-result batch records, each counted by the rigorous closed-part bound
   of SPEC 8.8 (d); report and verification records. Typical and maximal entry sizes.
3. **Blobs** (``MAX_BLOB_BYTES``, 256 MiB): the D-053 rows plus the LOOKUP batch and the candidate-result batch.
4. **Total storage**: the D-053 mathematical worst case and operational bound plus the new batch blobs.

Usage: ``uv run python docs/verification/stage-04/review/step7/d055/bounds.py [--out FILE]``
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
from citerift.investigation.journal import JOURNAL_FORMAT, MAX_JOURNAL_BYTES, MAX_RECORD_BYTES  # noqa: E402
from citerift.investigation.schemas import RECORD, contracts  # noqa: E402
from citerift.wiki import extract as stage03_extract  # noqa: E402


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


D053 = _load("d053_bounds", HERE.parent / "d053" / "bounds.py")
CEIL = _load("d055_part_ceiling", HERE / "part_ceiling.py")
SB = D053.SB
SHA = SB.SHA
# Kinds of format 3 that format 4 no longer writes as records (D-055: their payloads are batch entries).
GONE = ("claim", "decision", "question", "observation")


def record_kinds() -> dict[str, Any]:
    """The closure's maximal records of every kind format 4 keeps, then the format-4 observation (the largest of the
    kinds a record may still carry) and the three batch records, all validated against the format-4 schema."""
    real = SB._measure
    SB._measure = lambda name, rec: None if name.startswith(GONE) or name.startswith("evidence ") else real(name, rec)
    try:
        kinds = {k: v for k, v in SB.record_kinds().items() if v is not None and not k.startswith("claim_recorded")}
    finally:
        SB._measure = real
    for obs_kind, step, op in (
        ("index_identity", "LOOKUP", "index_identity"),
        ("bundle", "ACQUIRE", "capture_revision"),
        ("extraction", "EXTRACT", "extract_bundle"),
    ):
        engine = "citerift.retraction" if obs_kind == "index_identity" else "citerift.wiki"
        payload = {
            "obs_kind": obs_kind,
            "blob": SHA,
            "source_ref": {"engine": engine, "operation": op, "locator": SB.CTRL * 4096},
        }
        kinds[f"observation_recorded ({obs_kind})"] = SB._measure(
            "observation",
            SB._record("observation_recorded", step, 3 if step != "ACQUIRE" else 9, payload, step != "ACQUIRE"),
        )
    for kind, step, count in (
        ("evidence_batch_recorded", "DETECT", "evidence_count"),
        ("lookup_batch_recorded", "LOOKUP", "entry_count"),
        ("candidate_result_batch_recorded", "DETECT", "entry_count"),
    ):
        payload = {"batch": SHA, "batch_index": SB.MAXINT - 1, "batch_total": SB.MAXINT, count: SB.MAXINT}
        kinds[kind] = SB._measure(kind, SB._record(kind, step, 3, payload, True))
    enum = set(contracts().schemas[RECORD]["properties"]["kind"]["enum"])
    measured = {k.split(" ")[0] for k in kinds}
    if measured != enum:
        raise SystemExit(f"kinds measured {sorted(measured)} != schema kinds {sorted(enum)}")
    return kinds


def entry_sizes() -> dict[str, dict[str, int]]:
    """Canonical bytes of one entry of each batch kind: typical (an article at its caps) and maximal."""
    ev_ceiling = json.loads((HERE.parent / "d053" / "part_ceiling.json").read_text(encoding="utf-8"))
    lookup_typ = {
        "obs_kind": "lookup",
        "blob": SHA,
        "source_ref": {"engine": "citerift.retraction", "operation": "gather", "locator": "doi:10.1234/" + "x" * 40},
    }
    sets_ = {"not_found": SHA, "conflict": SHA}
    cand_typ = math.ceil(sum(batches.item_bytes(CEIL.typical_entry(i, sets_)) for i in range(8)) / 8)
    cand = CEIL.maximal_candidate_entries()
    return {
        "typical": {
            "evidence item": 380,  # ../d053/bounds.py: 7,646,956 B over 20,000 article-shaped items
            "lookup reference": batches.item_bytes(lookup_typ),
            "candidate result": cand_typ,
        },
        "maximal": {
            "evidence item": ev_ceiling["rule_1_largest_item"]["E_max"],
            "lookup reference": batches.item_bytes(CEIL.maximal_lookup_entry()),
            "candidate result": batches.item_bytes(cand["sum of field maxima (not a valid entry)"]),
        },
    }


def journal(kinds: dict[str, Any], sizes: dict[str, dict[str, int]]) -> dict[str, Any]:
    ec = stage03_extract.ExtractConfig()
    units, occ = ec.max_refs, ec.max_candidates
    candidates = occ + units
    a_max, f_max = workflow.A_MAX, workflow.F_MAX
    c = batches.MAX_PART_BYTES
    rmax: dict[str, int] = {}
    for k, v in kinds.items():  # with newline; the largest of each kind
        rmax[k.split(" ")[0]] = max(rmax.get(k.split(" ")[0], 0), v["bytes"] + 1)

    attempts = {s: a_max for s in workflow.STEPS if s != "ACQUIRE"} | {"ACQUIRE": a_max + f_max}
    execution = sum(
        n * (rmax["step_started"] + max(rmax["step_failed"], rmax["step_succeeded"], rmax["step_deferred"]))
        for n in attempts.values()
    )
    execution += sum(n * rmax["step_interrupted"] for n in attempts.values())  # an interruption before each terminal
    fixed = {
        "investigation_created": rmax["investigation_created"],
        "execution records of every attempt (deferrals, interruptions, failures included)": execution,
        "stale_detected": rmax["stale_detected"],
        "ACQUIRE bundle, EXTRACT extraction, LOOKUP index-identity observations (every attempt)": (
            attempts["ACQUIRE"] + 2 * a_max
        )
        * rmax["observation_recorded"],
        "report_recorded (every ASSEMBLE attempt)": a_max * rmax["report_recorded"],
        "verification_recorded (every VERIFY attempt)": a_max * rmax["verification_recorded"],
        "question_closed, claim_superseded": 0,  # Stage 04 writes neither (SPEC 8.5); listed for completeness
    }
    fixed_total = sum(fixed.values())

    counts = {
        "evidence item": sum(
            json.loads((HERE.parent / "d053" / "part_ceiling.json").read_text(encoding="utf-8"))["rule_5_record_count"][
                "evidence_items_per_run_at_caps"
            ].values()
        ),
        "lookup reference": occ + min(units, occ // 2),
        "candidate result": candidates,
    }
    record_of = {
        "evidence item": "evidence_batch_recorded",
        "lookup reference": "lookup_batch_recorded",
        "candidate result": "candidate_result_batch_recorded",
    }
    envelope = {
        "evidence item": batches.BATCH_ENVELOPE,
        "lookup reference": batches.LOOKUP_ENVELOPE,
        "candidate result": batches.CANDIDATE_ENVELOPE,
    }
    # Series per run (each may end in one partial part): evidence in NORMALIZE and DETECT, one LOOKUP, one DETECT.
    series = {"evidence item": 2, "lookup reference": 1, "candidate result": 1}

    def option(which: str) -> dict[str, Any]:
        sz = sizes[which]
        rows = {}
        for k, n_entries in counts.items():
            largest = sizes["maximal"][k]
            # SPEC 8.8 (d): a part closes only when the next entry (<= largest, plus a comma) would pass the ceiling,
            # so a closed part holds at least (c - largest - envelope) / 2 bytes of entries (each entry adds its size
            # and at most one comma, at most twice its size). Rigorous for any entry mix.
            per_closed = (c - largest - envelope[k]) // 2
            entry_bytes = n_entries * sz[k]
            n = math.ceil(entry_bytes / per_closed) + series[k]
            rows[k] = {
                "entries": n_entries,
                "entry_bytes": entry_bytes,
                "batch_records": n,
                "record_bytes": n * rmax[record_of[k]],
            }
        content = sum(r["record_bytes"] for r in rows.values())
        total = fixed_total + a_max * content
        return {
            "batch_records_one_attempt_each_step": rows,
            "content_bytes_one_attempt_each_step": content,
            "journal_bytes": total,
            "fraction_of_limit": round(total / MAX_JOURNAL_BYTES, 5),
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
        "largest_record_bytes_with_newline": rmax,
        "fixed_records_bytes": fixed,
        "fixed_total_bytes": fixed_total,
        "entries_per_run": counts,
        "entry_bytes": sizes,
        "typical": option("typical"),
        "maximal": option("maximal"),
        "format_3_per_candidate_records_one_attempt (0097a93, for comparison)": {
            "records": counts["lookup reference"] + 1 + 3 * candidates,
            "note": "format 3 wrote one record per lookup observation, claim, decision and question: about "
            "280,000 records per attempt at the caps (../d053/bounds.json); format 4 writes the batch records above",
        },
    }


def blobs(j: dict[str, Any]) -> dict[str, Any]:
    c = batches.MAX_PART_BYTES
    # The D-053 rows need the format-3 field names of the journal section.
    jj = {
        "evidence_per_run": {"items": j["entries_per_run"]["evidence item"]},
        "stage03_caps": j["stage03_caps"],
        "per_candidate_record_bytes_max": {"claim": j["entry_bytes"]["maximal"]["candidate result"]},
    }
    rows = D053.blobs(jj)
    for name, k, env in (
        ("LOOKUP batch (D-055)", "lookup reference", batches.LOOKUP_ENVELOPE),
        ("DETECT candidate-result batch (D-055)", "candidate result", batches.CANDIDATE_ENVELOPE),
    ):
        bound = max(c, j["entry_bytes"]["maximal"][k] + env)
        rows[name] = {
            "bound_bytes": bound,
            "why": "SPEC 8.9 / 8.8 (d): a batch is cut at MAX_PART_BYTES; one maximal entry fits a batch of its own",
            "within_limit": bound <= MAX_BLOB_BYTES,
            "fraction_of_limit": round(bound / MAX_BLOB_BYTES, 4),
        }
    return rows


def total(j: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    a_max = j["A_max"]
    ev_ceiling = json.loads((HERE.parent / "d053" / "part_ceiling.json").read_text(encoding="utf-8"))
    jj = {
        "A_max": a_max,
        "stage03_caps": j["stage03_caps"],
        "per_candidate_records_per_run": {"lookup observation": j["entries_per_run"]["lookup reference"] + 1},
        "evidence_per_run": {
            "items": j["entries_per_run"]["evidence item"],
            "typical_bytes": j["entries_per_run"]["evidence item"] * j["entry_bytes"]["typical"]["evidence item"],
            "max_bytes": ev_ceiling["rule_5_record_count"]["E_run_max_bytes"],
        },
    }
    out = D053.total(jj, b)
    batch_max = sum(
        j["maximal"]["batch_records_one_attempt_each_step"][k]["entry_bytes"]
        for k in ("lookup reference", "candidate result")
    )
    batch_typ = sum(
        j["typical"]["batch_records_one_attempt_each_step"][k]["entry_bytes"]
        for k in ("lookup reference", "candidate result")
    )
    out["mathematical_worst_case_bytes"] += a_max * batch_max
    out["operational_bound_bytes"] += batch_typ
    out["d055_batch_blobs"] = {"maximal_bytes_per_attempt": batch_max, "typical_bytes_per_run": batch_typ}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=HERE / "bounds.json")
    args = ap.parse_args()
    kinds = record_kinds()
    j = journal(kinds, entry_sizes())
    b = blobs(j)
    result = {
        "decision": "D-055 (owner message cmsg_018VCB51nDHP6HXmLU4ea5yP7cfPWf5UN6kmKGbSHoPG1n)",
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
        "journal_limit_proven": j["maximal"]["proven_within_limit"],
        "blobs": b,
        "blob_limit_proven_except_ACQUIRE_observation": all(
            r["within_limit"] for k, r in b.items() if not k.startswith("ACQUIRE")
        ),
        "ACQUIRE_observation": "conditional on the Step 8 representation (IF-7, see its row)",
        "total_storage": total(j, b),
    }
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "journal": {k: j[k]["journal_bytes"] for k in ("typical", "maximal")},
                "fraction": j["maximal"]["fraction_of_limit"],
                "headroom": j["maximal"]["headroom_factor"],
                "largest_record": result["largest_record_bytes"],
                "blobs_ok": result["blob_limit_proven_except_ACQUIRE_observation"],
            },
            indent=1,
        )
    )


if __name__ == "__main__":
    main()
