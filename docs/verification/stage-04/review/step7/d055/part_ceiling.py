"""Owner decision D-055: does the D-053 ceiling ``MAX_PART_BYTES`` still hold with LOOKUP and DETECT entries?

D-055 reuses the D-053 primitive and ceiling for the LOOKUP batches and the DETECT candidate-result batches (SPEC 8.9)
and asks for a re-derivation only if the candidate entry maximum requires it, by the same method. This script applies
the D-053 method (``../d053/part_ceiling.py``) to the three batch kinds together and states whether the selected
ceiling changes; ``part_ceiling.json`` is its output and a test checks that ``batches.MAX_PART_BYTES`` equals
``selected_bytes`` there.

1. **Largest legal entry** of each kind at its schema maxima, validated against its batch schema: a lookup reference
   (locator of 4,096 characters in the longest-encoded character), and a candidate result (the largest valid claim
   of each class family with its decision and question). The sum-of-field-maxima claim (not a valid claim: no class
   allows all its fields together) is also measured, as an over-approximation. ``C >= E_max + envelope``.
2. **Blob limit**: ``C <= MAX_BLOB_BYTES``.
3. **Measured cost** of DETECT candidate-result batches at the same ceilings as D-053, on one DETECT attempt of
   ``N_ENTRIES`` candidate results shaped like an article at its caps (a not-found claim, its decision; one in eight
   an identity conflict with its question): commit and read-only open, median of ``REPEATS`` runs. The D-053 evidence
   measurements (``../d053/part_ceiling.json``) are kept: the selected ceiling must be within ``TOLERANCE`` of the
   best on both.
4. **Memory**: heap peak of reading and validating one candidate batch of about ``C`` bytes, typical and maximal.
5. **Record count**: the batch records of all three kinds of the worst legal investigation (every evidence item,
   lookup reference and candidate result of a run at the Stage 03 caps at its maximal size, ``A_max`` attempts each)
   stay within ``RECORD_SHARE`` of ``MAX_JOURNAL_BYTES``.
6. **Selection**: the smallest power of two satisfying 1, 2 and 5 whose times are within ``TOLERANCE`` of the best
   for both evidence (D-053) and candidate results (here).

Usage: ``uv run python docs/verification/stage-04/review/step7/d055/part_ceiling.py [--out FILE]``
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import statistics
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[5]
sys.path.insert(0, str(REPO / "tests" / "stage04"))

from memory_support import append_candidates, append_evidence, drive, h, new_memory  # noqa: E402

from citerift.investigation import batches, ids, sets, workflow  # noqa: E402
from citerift.investigation.blobs import MAX_BLOB_BYTES  # noqa: E402
from citerift.investigation.canonical import canon  # noqa: E402
from citerift.investigation.journal import MAX_JOURNAL_BYTES  # noqa: E402
from citerift.investigation.memory import InvestigationMemory, _record  # noqa: E402
from citerift.investigation.schemas import CANDIDATE_BATCH, LOOKUP_BATCH, RECORD, problems  # noqa: E402
from citerift.wiki import extract as stage03_extract  # noqa: E402

KIB = 1024
CEILINGS = [2**k * KIB for k in (5, 7, 9, 10, 11, 12, 13, 14)]  # 32 KiB .. 16 MiB, as D-053
N_ENTRIES = 20_000
REPEATS = 3
TOLERANCE = 0.10
RECORD_SHARE = 0.01
MAXINT = 9007199254740991
SHA = "f" * 64
D053 = json.loads((HERE.parent / "d053" / "part_ceiling.json").read_text(encoding="utf-8"))


def _closure() -> Any:
    spec = importlib.util.spec_from_file_location(
        "closure_storage_bounds", HERE.parent / "closure" / "storage_bounds.py"
    )
    if spec is None or spec.loader is None:
        raise SystemExit("cannot load closure/storage_bounds.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SB = _closure()


def maximal_lookup_entry() -> dict[str, Any]:
    entry = {
        "obs_kind": "lookup",
        "blob": SHA,
        "source_ref": {"engine": "citerift.retraction", "operation": "gather", "locator": SB.CTRL * 4096},
    }
    found = problems(batches.lookup_batch([entry]), LOOKUP_BATCH)
    if found:
        raise SystemExit(str(found))
    return entry


def _entry(claim: dict[str, Any], disposition: str, qkind: str | None) -> dict[str, Any]:
    q = None if qkind is None else {"question_id": SHA, "claim_id": SHA, "kind": qkind}
    return {
        "claim": claim,
        "decision": {"decision_id": SHA, "claim_id": SHA, "disposition": disposition},
        "question": q,
    }


def maximal_candidate_entries() -> dict[str, Any]:
    """The largest valid candidate results (validated) and the sum-of-field-maxima over-approximation (not valid)."""
    out: dict[str, Any] = {}
    for cls, disposition, qkind in (
        ("IDENTITY_CONFLICT", "ROUTE_NEEDS_RESOLUTION", "identity_conflict"),
        ("UNRESOLVED_STATUS", "ABSTAIN", None),
    ):
        entry = _entry(SB._claim(cls), disposition, qkind)
        found = problems(batches.candidate_batch([entry]), CANDIDATE_BATCH)
        if found:
            raise SystemExit(f"{cls}: {found[:3]}")
        out[cls] = entry
    both = SB._claim("IDENTITY_CONFLICT")
    both["upstream_reasons"] = SB._claim("UNRESOLVED_STATUS")["upstream_reasons"]
    out["sum of field maxima (not a valid entry)"] = _entry(both, "ROUTE_NEEDS_RESOLUTION", "identity_conflict")
    return out


def per_run() -> dict[str, int]:
    """Entries of one committed run at the Stage 03 caps (the counts of ``../d053/bounds.py``)."""
    ec = stage03_extract.ExtractConfig()
    units, occ = ec.max_refs, ec.max_candidates
    return {
        "evidence items": sum(D053["rule_5_record_count"]["evidence_items_per_run_at_caps"].values()),
        "lookup references": occ + min(units, occ // 2),
        "candidate results": occ + units,
    }


def largest_batch_record(kind: str, step: str) -> int:
    count = "evidence_count" if kind == "evidence_batch_recorded" else "entry_count"
    payload = {"batch": SHA, "batch_index": MAXINT - 1, "batch_total": MAXINT, count: MAXINT}
    rec = _record(MAXINT, SHA, kind, step, 3, "2026-11-10T12:00:00.000000Z", SHA, payload)
    rec["digest"] = SHA
    if problems(rec, RECORD):
        raise SystemExit(str(problems(rec, RECORD)))
    return len(canon(rec)) + 1


def typical_entry(i: int, set_of: dict[str, str]) -> dict[str, Any]:
    """A candidate result as an article at its caps produces it: a DOI of 48 characters; one in eight an identity
    conflict (pair, two alternatives, a question), the others not found in checked sources."""
    doi = {"scheme": "doi", "normalized": f"10.{1000 + i % 9000}/journal.{i:08d}.abcdefghijklmnopqr"}
    cand = h(f"cand-{i}")
    if i % 8 == 0:
        pmid = {"scheme": "pmid", "normalized": str(10_000_000 + i)}
        alt = {"reached_by": doi, "work": {"doi": doi["normalized"], "pmid": None}}
        claim = {
            "cand_ref": cand,
            "candidate": {"shape": "PAIR", "keys": [doi, pmid], "coherence": "INCOMPATIBLE"},
            "class": "IDENTITY_CONFLICT",
            "rule": "D-6",
            "table_version": "dt-1",
            "status": "conflicting",
            "value": None,
            "alternatives": [
                {"value": alt, "supporting_count": 1},
                {"value": {**alt, "reached_by": pmid}, "supporting_count": 1},
            ],
            "reasons": ["IDENTITY_WITNESSED", "KEY_RESULTS_DIFFER"],
            "upstream_reasons": [],
            "evidence_set": set_of["conflict"],
            "supporting_count": 0,
            "contradicting_count": 0,
        }
        disposition, qkind = "ROUTE_NEEDS_RESOLUTION", "identity_conflict"
    else:
        claim = {
            "cand_ref": cand,
            "candidate": {"shape": "DOI", "keys": [doi], "coherence": None},
            "class": "NOT_FOUND_IN_CHECKED_SOURCES",
            "rule": "D-16",
            "table_version": "dt-1",
            "status": "uncertain",
            "value": "not_found_in_checked_sources",
            "alternatives": [],
            "reasons": ["NOT_FOUND_IN_CHECKED_SOURCES"],
            "upstream_reasons": [],
            "evidence_set": set_of["not_found"],
            "supporting_count": 1,
            "contradicting_count": 0,
        }
        disposition, qkind = "REPORT_NOT_FOUND", None
    cid = ids.claim_id(cand, claim["class"], claim["rule"], "dt-1", claim["evidence_set"])
    claim = {"claim_id": cid, **claim}
    q = None if qkind is None else {"question_id": ids.question_id(cid, qkind), "claim_id": cid, "kind": qkind}
    decision = {"decision_id": ids.decision_id(cid, disposition), "claim_id": cid, "disposition": disposition}
    return {"claim": claim, "decision": decision, "question": q}


def _commit_and_open(base: Path, ceiling: int) -> dict[str, Any]:
    """One DETECT attempt of N_ENTRIES candidate results committed at ``ceiling``, then a read-only open."""
    batches.MAX_PART_BYTES = ceiling
    mem, root = new_memory(base)
    drive(mem, ("VALIDATE", "ACQUIRE", "EXTRACT", "NORMALIZE", "LOOKUP"))
    lookup = mem.put_blob({"lookup": "SYNTHETIC", "state": "no_record"})  # the LOOKUP observation (same bytes)
    evs = [
        {
            "evidence_id": ids.evidence_id(lookup, p, "lookup_result"),
            "observation": lookup,
            "pointer": p,
            "kind": "lookup_result",
            "refs": [],
            "value": None,
        }
        for p in ("", "/a", "/b")
    ]
    set_of = {
        "not_found": mem.put_blob(sets.evidence_set([evs[0]["evidence_id"]])),
        "conflict": mem.put_blob(sets.evidence_set([], [], [[evs[1]["evidence_id"]], [evs[2]["evidence_id"]]])),
    }
    entries = [typical_entry(i, set_of) for i in range(N_ENTRIES)]
    mem.append("step_started", {"step_key": h("DETECT")}, step="DETECT", attempt=1)
    append_evidence(mem, evs, "DETECT", 1)
    t0 = time.perf_counter()
    recs = append_candidates(mem, entries, "DETECT", 1)
    out = mem.put_blob({"claims": N_ENTRIES})
    mem.append("step_succeeded", {"step_key": h("DETECT"), "outputs": [out], "root": None}, step="DETECT", attempt=1)
    commit = time.perf_counter() - t0
    key = mem.key
    mem.close()
    t0 = time.perf_counter()
    with InvestigationMemory.open(root, key, writable=False) as ro:
        if ro.view.step_state("DETECT") != "succeeded" or len(ro.view.committed.claims) != N_ENTRIES:
            raise SystemExit("DETECT did not commit every candidate result")
    opened = time.perf_counter() - t0
    size = sum(len(canon(p)) for p in batches.ordered_parts(entries, batches.candidate_key, batches.candidate_batch))
    return {"commit_s": commit, "open_s": opened, "batches": len(recs), "entry_bytes": size}


def measure_costs(tmp: Path) -> list[dict[str, Any]]:
    rows = []
    for c in CEILINGS:
        runs = []
        for r in range(REPEATS):
            base = tmp / f"c{c}-{r}"
            base.mkdir()
            runs.append(_commit_and_open(base, c))
        rows.append(
            {
                "ceiling_bytes": c,
                "batches": runs[0]["batches"],
                "entry_bytes": runs[0]["entry_bytes"],
                "commit_s_median": round(statistics.median(x["commit_s"] for x in runs), 4),
                "open_s_median": round(statistics.median(x["open_s"] for x in runs), 4),
                "commit_s_runs": [round(x["commit_s"], 4) for x in runs],
                "open_s_runs": [round(x["open_s"], 4) for x in runs],
            }
        )
        print(rows[-1], flush=True)
    return rows


def batch_memory(entry: dict[str, Any], size: int) -> dict[str, Any]:
    """Peak Python heap of parsing and schema-validating one candidate batch of about ``size`` bytes."""
    n = max(1, (size - batches.CANDIDATE_ENVELOPE) // (batches.item_bytes(entry) + 1))
    entries = []
    for i in range(n):
        e = json.loads(json.dumps(entry))
        e["claim"]["cand_ref"] = h(f"{i}")
        entries.append(e)
    data = canon(batches.candidate_batch(entries))
    tracemalloc.start()
    tracemalloc.reset_peak()
    value = json.loads(data)
    if problems(value, CANDIDATE_BATCH):
        raise SystemExit(str(problems(value, CANDIDATE_BATCH)[:3]))
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {"batch_bytes": len(data), "entries": n, "peak_bytes": peak, "peak_over_batch": round(peak / len(data), 2)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=HERE / "part_ceiling.json")
    args = ap.parse_args()
    original = batches.MAX_PART_BYTES

    lookup_max = batches.item_bytes(maximal_lookup_entry())
    cands = maximal_candidate_entries()
    cand_sizes = {k: batches.item_bytes(v) for k, v in cands.items()}
    cand_valid_max = max(v for k, v in cand_sizes.items() if "not a valid" not in k)
    cand_over = cand_sizes["sum of field maxima (not a valid entry)"]
    e_max_evidence = D053["rule_1_largest_item"]["E_max"]
    lower = max(
        e_max_evidence + batches.BATCH_ENVELOPE,
        lookup_max + batches.LOOKUP_ENVELOPE,
        cand_over + batches.CANDIDATE_ENVELOPE,
    )

    counts = per_run()
    sizes = {"evidence items": e_max_evidence, "lookup references": lookup_max, "candidate results": cand_over}
    records = {
        "evidence items": largest_batch_record("evidence_batch_recorded", "DETECT"),
        "lookup references": largest_batch_record("lookup_batch_recorded", "LOOKUP"),
        "candidate results": largest_batch_record("candidate_result_batch_recorded", "DETECT"),
    }
    budget = RECORD_SHARE * MAX_JOURNAL_BYTES

    def record_bytes(c: int) -> int:
        return sum(-(-(counts[k] * (sizes[k] + 1)) // c) * workflow.A_MAX * records[k] for k in counts)

    record_lower = min(c for c in (2**k for k in range(10, 29)) if record_bytes(c) <= budget)
    with tempfile.TemporaryDirectory(dir=REPO.parent) as d:
        costs = measure_costs(Path(d))
    best_commit = min(r["commit_s_median"] for r in costs)
    best_open = min(r["open_s_median"] for r in costs)
    ev_rows = {r["ceiling_bytes"]: r for r in D053["rule_3_measured_costs"]["rows"]}
    ev_best_commit = D053["rule_3_measured_costs"]["best_commit_s"]
    ev_best_open = D053["rule_3_measured_costs"]["best_open_s"]
    admissible = [
        r["ceiling_bytes"]
        for r in costs
        if max(lower, record_lower) <= r["ceiling_bytes"] <= MAX_BLOB_BYTES
        and r["commit_s_median"] <= (1 + TOLERANCE) * best_commit
        and r["open_s_median"] <= (1 + TOLERANCE) * best_open
        and ev_rows[r["ceiling_bytes"]]["commit_s_median"] <= (1 + TOLERANCE) * ev_best_commit
        and ev_rows[r["ceiling_bytes"]]["open_s_median"] <= (1 + TOLERANCE) * ev_best_open
    ]
    if not admissible:
        raise SystemExit("no measured ceiling satisfies every rule")
    selected = min(admissible)
    typical = typical_entry(1, {"not_found": SHA, "conflict": SHA})
    memory = {
        "typical entries": [batch_memory(typical, c) for c in (selected, 4 * selected)],
        "maximal valid entries": [batch_memory(cands["UNRESOLVED_STATUS"], c) for c in (selected, 4 * selected)],
    }
    batches.MAX_PART_BYTES = original
    result = {
        "decision": "D-055 (owner message cmsg_018VCB51nDHP6HXmLU4ea5yP7cfPWf5UN6kmKGbSHoPG1n)",
        "machine": {"python": platform.python_version(), "platform": platform.platform()},
        "d053_selected_bytes": D053["selected_bytes"],
        "rule_1_largest_entry": {
            "evidence_item_E_max (D-053)": e_max_evidence,
            "lookup_reference_max": lookup_max,
            "candidate_result_bytes": cand_sizes,
            "candidate_result_valid_max": cand_valid_max,
            "envelopes": {
                "evidence": batches.BATCH_ENVELOPE,
                "lookup": batches.LOOKUP_ENVELOPE,
                "candidate": batches.CANDIDATE_ENVELOPE,
            },
            "lower_bound_bytes": lower,
        },
        "rule_2_blob_limit": {"MAX_BLOB_BYTES": MAX_BLOB_BYTES},
        "rule_3_measured_costs": {
            "candidate_results_per_attempt": N_ENTRIES,
            "repeats": REPEATS,
            "tolerance": TOLERANCE,
            "best_commit_s": best_commit,
            "best_open_s": best_open,
            "rows": costs,
            "evidence_rows": "../d053/part_ceiling.json rule_3_measured_costs (unchanged code path)",
        },
        "rule_4_memory_per_batch": memory,
        "rule_5_record_count": {
            "entries_per_run_at_caps": counts,
            "entry_bytes_max": sizes,
            "largest_batch_record_bytes": records,
            "A_max": workflow.A_MAX,
            "record_share": RECORD_SHARE,
            "budget_bytes": budget,
            "smallest_power_of_two_within_budget": record_lower,
            "batch_record_bytes_at_selected": record_bytes(selected),
        },
        "selected_bytes": selected,
        "admissible_ceilings": admissible,
        "changed_from_d053": selected != D053["selected_bytes"],
    }
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps({"selected_bytes": selected, "lower": lower, "record_lower": record_lower, "admissible": admissible})
    )


if __name__ == "__main__":
    main()
