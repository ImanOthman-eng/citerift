"""Owner decision D-053: derivation of the evidence-batch byte ceiling ``MAX_PART_BYTES`` (SPEC 8.8).

The owner asked for a ceiling that is derived, not guessed, from the maximum item size, ``MAX_BLOB_BYTES``, the
encoding overhead, the parse and validation memory, the record count and measured write and open performance. This
script measures each and applies the selection rule below; ``part_ceiling.json`` is its output and
``batches.MAX_PART_BYTES`` must equal ``selected_bytes`` there (a test checks it).

1. **Largest legal item** ``E_max``: every evidence kind built at its schema maxima (pointer of 4,096 characters in
   the character with the longest canonical encoding, 8 refs, the widest key values), validated against the batch
   schema and measured. The ceiling must hold one such item with the batch envelope: ``C >= E_max + envelope``.
2. **Blob limit**: a part never exceeds ``C`` (an item larger than ``C`` would form its own part, but by rule 1 no
   legal item is), so ``C <= MAX_BLOB_BYTES`` keeps every batch a legal blob.
3. **Measured cost** at ceilings ``C`` in powers of two from 32 KiB to 16 MiB, on one NORMALIZE attempt of
   ``N_ITEMS`` items shaped like a Stage 03 article at its caps (a unit, its use eligibility, identifier occurrences
   and work candidates, with their refs): wall time to commit (order, cut, publish with fsync, append with Memory's
   check, which reads each batch back) and to open read-only (every batch read, hashed, parsed, schema-validated, every
   item checked, the canonical order and boundaries recomputed). The median of ``REPEATS`` runs.
4. **Memory**: Python heap peak (``tracemalloc``) of reading and validating one batch of about ``C`` bytes, for
   typical and maximal items; reported as a multiple of ``C``.
5. **Record count**: the batch records of the worst legal investigation (every evidence item of a run at the Stage 03
   caps, every item at its maximal size, ``A_max`` attempts that keep their records) must stay within
   ``RECORD_SHARE`` of ``MAX_JOURNAL_BYTES``, the representation's own overhead in the journal: with ``R`` the
   largest batch record, ``ceil(E_run_max / C) * A_max * R <= RECORD_SHARE * MAX_JOURNAL_BYTES``. This is the binding
   rule: it gives the lower bound on ``C``.
6. **Selection rule**: the smallest power of two that satisfies rules 1, 2 and 5 and at which both the commit time
   and the open time are within ``TOLERANCE`` of the best measured value. A larger ceiling buys no measurable speed and
   costs memory per batch (rule 4).

Usage: ``uv run python docs/verification/stage-04/review/step7/d053/part_ceiling.py [--out FILE]``
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(REPO / "tests" / "stage04"))

from memory_support import append_evidence, drive, h, new_memory  # noqa: E402

from citerift.investigation import batches, ids, workflow  # noqa: E402
from citerift.investigation.blobs import MAX_BLOB_BYTES  # noqa: E402
from citerift.investigation.canonical import canon  # noqa: E402
from citerift.investigation.journal import MAX_JOURNAL_BYTES  # noqa: E402
from citerift.investigation.memory import InvestigationMemory, _record  # noqa: E402
from citerift.investigation.schemas import EVIDENCE_BATCH, RECORD, problems  # noqa: E402
from citerift.wiki import extract as stage03_extract  # noqa: E402

KIB = 1024
CEILINGS = [2**k * KIB for k in (5, 7, 9, 10, 11, 12, 13, 14)]  # 32 KiB .. 16 MiB
N_ITEMS = 20_000
REPEATS = 3
TOLERANCE = 0.10
RECORD_SHARE = 0.01
MAXINT = 9007199254740991
SHA = "f" * 64
CTRL = "\x01"  # 6 bytes in canonical JSON (\u0001), the longest encoding of one character
WIDE = "\U0001f600"  # 4 bytes, the widest character the DOI key pattern allows
POINTER_MAX = "/" + CTRL * 4095  # json_pointer: maxLength 4096, control characters allowed
DOI_MAX = "10.1234/" + WIDE * (512 - len("10.1234/"))


def maximal_items() -> dict[str, dict[str, Any]]:
    """Each evidence kind at its schema maxima (common.schema.json ``$defs/evidence``)."""
    doi = {"scheme": "doi", "normalized": DOI_MAX}
    values: dict[str, Any] = {
        "bundle_identity": None,
        "extraction_identity": None,
        "unit": {"source_artifact": SHA, "unit_span_sha256": SHA},
        "use_eligibility": {"eligibility": "USE_NOT_ESTABLISHED", "reason": "CONFLICTING_DEFINITIONS"},
        "identifier_occurrence": {"status": "OBSERVATION_ROLE", "key": doi},
        "work_candidate": {
            "shape": "PAIR",
            "keys": [doi, {"scheme": "pmid", "normalized": "9" * 9}],
            "coherence": "UNDETERMINED",
        },
        "index_identity": None,
        "lookup_result": None,
        "lookup_event": None,
        "coherence": "NOT_DETERMINED",
    }
    out = {}
    for kind, value in values.items():
        item = {
            "evidence_id": SHA,
            "observation": SHA,
            "pointer": POINTER_MAX,
            "kind": kind,
            "refs": [f"{i:x}".rjust(64, "e") for i in range(8)],
            "value": value,
        }
        found = problems(batches.evidence_batch([item]), EVIDENCE_BATCH)
        if not (found == []):
            raise SystemExit(str((kind, found)))
        out[kind] = item
    return out


def evidence_per_run() -> dict[str, int]:
    """Evidence items of one committed run at the Stage 03 caps (the counts of the Step 7 closure storage derivation,
    ``closure/storage_bounds.py``: SPEC 6.1 to 6.5 and 7, and the Step 8 design condition of at most W = 4 witness
    lookup events per claim)."""
    ec = stage03_extract.ExtractConfig()
    units, occ = ec.max_refs, ec.max_candidates
    candidates = occ + units
    return {
        "unit": units,
        "use_eligibility": units,
        "identifier_occurrence": occ,
        "work_candidate": candidates,
        "lookup_result": occ + min(units, occ // 2),
        "lookup_event (W = 4 per claim)": 4 * candidates,
    }


def largest_batch_record() -> int:
    """Bytes (with its newline) of the largest legal ``evidence_batch_recorded`` record: every integer at the schema
    maximum."""
    payload = {"batch": SHA, "batch_index": MAXINT - 1, "batch_total": MAXINT, "evidence_count": MAXINT}
    rec = _record(MAXINT, SHA, "evidence_batch_recorded", "NORMALIZE", 3, "2026-11-10T12:00:00.000000Z", SHA, payload)
    rec["digest"] = SHA
    if problems(rec, RECORD):
        raise SystemExit(str(problems(rec, RECORD)))
    return len(canon(rec)) + 1


def article_items(obs: str, n: int) -> list[dict[str, Any]]:
    """``n`` NORMALIZE items in the proportions of a Stage 03 article at its caps (20,000 units, 50,000 identifier
    occurrences, 70,000 candidates): unit, use eligibility (ref unit), occurrence (ref unit), candidate (ref
    occurrence or unit). Pointers are the deepest the caps give."""

    def ev(kind: str, pointer: str, refs: list[str], value: Any) -> dict[str, Any]:
        return {"evidence_id": ids.evidence_id(obs, pointer, kind), "observation": obs, "pointer": pointer,
                "kind": kind, "refs": refs, "value": value}  # fmt: skip

    units = max(1, n * 20 // 160)
    occ = n * 50 // 160
    items: list[dict[str, Any]] = []
    unit_ids = []
    for i in range(units):
        u = ev("unit", f"/units/{i}", [], {"source_artifact": SHA, "unit_span_sha256": h(str(i))})
        unit_ids.append(u["evidence_id"])
        items.append(u)
        items.append(ev("use_eligibility", f"/units/{i}", [u["evidence_id"]],
                        {"eligibility": "CITED", "reason": None}))  # fmt: skip
    occ_ids = []
    for j in range(occ):
        doi = {"scheme": "doi", "normalized": f"10.{1000 + j % 9000}/journal.{j:08d}"}
        o = ev("identifier_occurrence", f"/identifiers/{j}", [unit_ids[j % units]], {"status": "CONFIRMED", "key": doi})
        occ_ids.append((o["evidence_id"], doi))
        items.append(o)
    k = 0
    while len(items) < n:
        if k < occ:
            oid, doi = occ_ids[k]
            items.append(ev("work_candidate", f"/candidates/{k}", [oid], {"shape": "DOI", "keys": [doi],
                                                                            "coherence": None}))  # fmt: skip
        else:
            items.append(ev("work_candidate", f"/candidates/{k}", [unit_ids[k % units]],
                            {"shape": "NONE", "keys": [], "coherence": None}))  # fmt: skip
        k += 1
    return items[:n]


def _commit_and_open(base: Path, items_of: Any, ceiling: int) -> dict[str, float | int]:
    """One NORMALIZE attempt committed at ``ceiling``, then a read-only open; times in seconds."""
    batches.MAX_PART_BYTES = ceiling
    mem, root = new_memory(base)
    drive(mem, ("VALIDATE", "ACQUIRE", "EXTRACT"))
    obs = mem.put_blob({"units": [{"id": "un-00001"}], "ratio": 0.5})  # the EXTRACT observation (same bytes)
    items = items_of(obs)
    mem.append("step_started", {"step_key": h("NORMALIZE")}, step="NORMALIZE", attempt=1)
    t0 = time.perf_counter()
    recs = append_evidence(mem, items, "NORMALIZE", 1)
    out = mem.put_blob({"normalized": len(items)})
    mem.append("step_succeeded", {"step_key": h("NORMALIZE"), "outputs": [out], "root": None}, step="NORMALIZE",
               attempt=1)  # fmt: skip
    commit = time.perf_counter() - t0
    key = mem.key
    mem.close()
    t0 = time.perf_counter()
    with InvestigationMemory.open(root, key, writable=False) as ro:
        if not (ro.view.step_state("NORMALIZE") == "succeeded"):
            raise SystemExit('check failed: ro.view.step_state("NORMALIZE") == "succeeded"')
    opened = time.perf_counter() - t0
    blob_bytes = sum(len(canon(b)) for b in batches.evidence_batches(items, lambda r: False, ceiling))
    return {"commit_s": commit, "open_s": opened, "batches": len(recs), "evidence_bytes": blob_bytes}


def measure_costs(tmp: Path) -> list[dict[str, Any]]:
    rows = []
    for c in CEILINGS:
        runs = []
        for r in range(REPEATS):
            base = tmp / f"c{c}-{r}"
            base.mkdir()
            runs.append(_commit_and_open(base, lambda obs: article_items(obs, N_ITEMS), c))
        rows.append(
            {
                "ceiling_bytes": c,
                "batches": runs[0]["batches"],
                "evidence_bytes": runs[0]["evidence_bytes"],
                "commit_s_median": round(statistics.median(x["commit_s"] for x in runs), 4),
                "open_s_median": round(statistics.median(x["open_s"] for x in runs), 4),
                "commit_s_runs": [round(x["commit_s"], 4) for x in runs],
                "open_s_runs": [round(x["open_s"], 4) for x in runs],
            }
        )
        print(rows[-1], flush=True)
    return rows


def batch_memory(item: dict[str, Any], size: int) -> dict[str, Any]:
    """Peak Python heap of reading (parse) and validating (schema, per-item id check) one batch of about ``size``
    bytes made of copies of ``item`` with distinct ids."""
    n = max(1, (size - batches.BATCH_ENVELOPE) // (batches.item_bytes(item) + 1))
    items = []
    for i in range(n):
        x = dict(item)
        x["evidence_id"] = h(f"{i}")
        items.append(x)
    data = canon(batches.evidence_batch(items), allow_float=True)
    tracemalloc.start()
    tracemalloc.reset_peak()
    value = json.loads(data)
    if problems(value, EVIDENCE_BATCH):
        raise SystemExit(str(problems(value, EVIDENCE_BATCH)))
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {"batch_bytes": len(data), "items": n, "peak_bytes": peak, "peak_over_batch": round(peak / len(data), 2)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path(__file__).with_suffix(".json"))
    args = ap.parse_args()
    original = batches.MAX_PART_BYTES

    maxima = {k: batches.item_bytes(v) for k, v in maximal_items().items()}
    e_max = max(maxima.values())
    lower = e_max + batches.BATCH_ENVELOPE
    per_run = evidence_per_run()
    e_run_max = sum(per_run.values()) * (e_max + 1)
    r_max = largest_batch_record()
    budget = RECORD_SHARE * MAX_JOURNAL_BYTES

    def record_bytes(c: int) -> int:
        return -(-e_run_max // c) * workflow.A_MAX * r_max

    record_lower = min(c for c in (2**k for k in range(10, 29)) if record_bytes(c) <= budget)
    with tempfile.TemporaryDirectory(dir=REPO.parent) as d:
        costs = measure_costs(Path(d))
    best_commit = min(r["commit_s_median"] for r in costs)
    best_open = min(r["open_s_median"] for r in costs)
    admissible = [
        r
        for r in costs
        if max(lower, record_lower) <= r["ceiling_bytes"] <= MAX_BLOB_BYTES
        and r["commit_s_median"] <= (1 + TOLERANCE) * best_commit
        and r["open_s_median"] <= (1 + TOLERANCE) * best_open
    ]
    selected = min(r["ceiling_bytes"] for r in admissible) if admissible else None
    if not (selected is not None):
        raise SystemExit("no measured ceiling satisfies every rule: extend CEILINGS")
    occurrence = next(i for i in article_items(SHA, 400) if i["kind"] == "identifier_occurrence")
    memory = {
        "typical items": [batch_memory(occurrence, c) for c in (selected, 4 * selected)],
        "maximal items": [batch_memory(maximal_items()["work_candidate"], c) for c in (selected, 4 * selected)],
    }
    batches.MAX_PART_BYTES = original
    result = {
        "decision": "D-053 (owner message cmsg_018VCB51nDHP6HXmLU4ea5yPT7kaAY3dV5Ewo8KzF3bTe8)",
        "machine": {"python": platform.python_version(), "platform": platform.platform()},
        "rule_1_largest_item": {
            "item_bytes_by_kind_at_schema_maxima": maxima,
            "E_max": e_max,
            "batch_envelope_bytes": batches.BATCH_ENVELOPE,
            "lower_bound_bytes": lower,
        },
        "rule_2_blob_limit": {"MAX_BLOB_BYTES": MAX_BLOB_BYTES},
        "rule_3_measured_costs": {
            "items_per_attempt": N_ITEMS,
            "repeats": REPEATS,
            "tolerance": TOLERANCE,
            "best_commit_s": best_commit,
            "best_open_s": best_open,
            "rows": costs,
        },
        "rule_4_memory_per_batch": memory,
        "rule_5_record_count": {
            "evidence_items_per_run_at_caps": per_run,
            "evidence_items_per_run_total": sum(per_run.values()),
            "E_run_max_bytes": e_run_max,
            "A_max": workflow.A_MAX,
            "largest_batch_record_bytes": r_max,
            "record_share": RECORD_SHARE,
            "budget_bytes": budget,
            "smallest_power_of_two_within_budget": record_lower,
            "batch_record_bytes_at_selected": None,
        },
        "selected_bytes": selected,
        "admissible_ceilings": [r["ceiling_bytes"] for r in admissible],
    }
    result["rule_5_record_count"]["batch_record_bytes_at_selected"] = record_bytes(selected)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"selected_bytes": selected, "E_max": e_max, "admissible": result["admissible_ceilings"]}))


if __name__ == "__main__":
    main()
