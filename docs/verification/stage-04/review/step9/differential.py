"""Step 9 differential: the production dt-1 detector against the frozen Step 4 oracle (owner Step 9 item 15).

For every case of the Step 4 domain (``simulations/stage04/decision_space.py``, 12,632,448 cases in the canonical
order) the frozen oracle (``simulations/stage04/oracle``, read only and checked against its MANIFEST digests) gives
the reference decision. ``stage02_abstraction.valid`` selects the 244,884 cases Stage 02 and Stage 03 can produce.
Each case is made concrete by ``tests/stage04/step9_support.concretize`` (labeled synthetic blobs) and decided by the
production code: ``adapters.detector.lookup_view`` parses every lookup observation, ``dt1.decide`` decides, and the
claim fields are read from the outcome. Compared fields: rule; for a claim class, status, value, disposition, the
question kind and the reason codes (the model's placeholder reasons in production names, D-043); for D-5 and D-17,
the failure code. Every discrepancy is listed with its case.

The valid domain is the owner's acceptance set. ``--all`` also runs the 12,387,564 invalid cases and classifies their
discrepancies (they are outside what Stage 02 can produce; the model's encoding there is an abstraction).

Run: ``uv run python docs/verification/stage-04/review/step9/differential.py [--all] [--workers 4]``
Writes ``differential.json`` (``differential_all.json`` with ``--all``) beside itself.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
import time
from array import array
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[5]
SIM = REPO / "simulations" / "stage04"
ORACLE = SIM / "oracle"
sys.path.insert(0, str(SIM))
sys.path.insert(0, str(REPO / "tests" / "stage04"))

import decision_space as DS  # noqa: E402
import stage02_abstraction as A  # noqa: E402
import step9_support as S9  # noqa: E402

from citerift.investigation import dt1  # noqa: E402
from citerift.investigation.adapters.detector import candidate_view, lookup_roles, lookup_view  # noqa: E402
from citerift.investigation.canonical import canon  # noqa: E402
from citerift.investigation.workflow import CONFLICT, DISPOSITION  # noqa: E402

QUESTION = {"IDENTITY_CONFLICT": "identity_conflict", "CONTRADICTION_IN_SOURCES": "source_conflict"}


def oracle() -> tuple[array, list[dict[str, Any]], dict[str, Any]]:
    manifest = json.loads((ORACLE / "MANIFEST.json").read_text(encoding="utf-8"))
    for name, digest in manifest["files"].items():
        if hashlib.sha256((ORACLE / name).read_bytes()).hexdigest() != digest:
            raise SystemExit(f"oracle file {name} does not match its MANIFEST digest")
    raw = gzip.decompress((ORACLE / "dt1_table.u16le.gz").read_bytes())
    if hashlib.sha256(raw).hexdigest() != manifest["table_raw_sha256"]:
        raise SystemExit("the oracle table does not match its MANIFEST digest")
    table = array("H")
    table.frombytes(raw)
    if sys.byteorder != "little":
        table.byteswap()
    decisions = json.loads((ORACLE / "dt1_decisions.json").read_text(encoding="utf-8"))["decisions"]
    return table, decisions, manifest


def production(case: Any) -> dict[str, Any]:
    """The production decision of one abstract case, through the production parser and table."""
    inp, _ = S9.concretize(case)
    cand = inp.candidate_inputs["candidates"][0]
    unit = inp.candidate_inputs["units"][0]
    obs = {canon(e["query"]).decode(): inp.read_blob(e["observation"]) for e in inp.lookup_plan["lookups"]}
    views = {q: lookup_view(obs[q]) for _, q in lookup_roles(cand)}
    out = dt1.decide(candidate_view(cand, unit, views))
    if out.failure is not None:
        return {"rule": out.rule, "failure": out.failure}
    return {
        "rule": out.rule,
        "class": out.cls,
        "status": out.status,
        "value": out.value,
        "disposition": DISPOSITION[out.cls],  # type: ignore[index]
        "question": CONFLICT.get(out.cls),  # type: ignore[arg-type]
        "reasons": list(out.reasons),
    }


def reference(dec: dict[str, Any]) -> dict[str, Any]:
    if dec["kind"] == "failure":
        return {"rule": dec["rule"], "failure": dec["reasons"][0]}
    return {
        "rule": dec["rule"],
        "class": dec["class"],
        "status": dec["status"],
        "value": dec["value"],
        "disposition": dec["disposition"],
        "question": QUESTION.get(dec["class"]),
        "reasons": sorted(S9.MODEL_REASON.get(r, r) for r in dec["reasons"]),
    }


def offsets() -> list[int]:
    out, n = [], 0
    for shape, _, _ in DS.chunks():
        out.append(n)
        n += DS.chunk_size(shape)
    return out


def run_chunk(args: tuple[int, bool]) -> dict[str, Any]:
    index, everything = args
    table, decisions, _ = _ORACLE["value"]
    shape, use, t = DS.chunks()[index]
    base = offsets()[index]
    counts: Counter[str] = Counter()
    rules: Counter[str] = Counter()
    mismatches: list[dict[str, Any]] = []
    for i, case in enumerate(DS.iter_chunk(shape, use, t)):
        valid = A.valid(case)
        if not valid and not everything:
            continue
        domain = "valid" if valid else "invalid"
        ref = reference(decisions[table[base + i]])
        got = production(case)
        counts[domain] += 1
        rules[f"{domain}:{ref['rule']}"] += 1
        if got != ref:
            counts[f"{domain}_mismatch"] += 1
            if len(mismatches) < 50:
                mismatches.append(
                    {"case": case.key(), "invalid_reasons": A.invalid_reasons(case), "oracle": ref, "production": got}
                )
    return {"counts": counts, "rules": rules, "mismatches": mismatches}


_ORACLE: dict[str, tuple[array, list[dict[str, Any]], dict[str, Any]]] = {}


def _init() -> None:
    _ORACLE["value"] = oracle()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="also run the invalid cases")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", type=Path, default=None, help="write the result here instead of beside this script")
    args = ap.parse_args()
    _, _, manifest = oracle()
    t0 = time.perf_counter()
    counts: Counter[str] = Counter()
    rules: Counter[str] = Counter()
    mismatches: list[dict[str, Any]] = []
    jobs = [(i, args.all) for i in range(len(DS.chunks()))]
    with ProcessPoolExecutor(args.workers, initializer=_init) as pool:
        for r in pool.map(run_chunk, jobs):
            counts.update(r["counts"])
            rules.update(r["rules"])
            mismatches += r["mismatches"][: max(0, 200 - len(mismatches))]
    out = {
        "oracle_manifest_sha256": hashlib.sha256((ORACLE / "MANIFEST.json").read_bytes()).hexdigest(),
        "oracle_version": manifest["oracle_version"],
        "model_version": manifest["model_version"],
        "table_version": dt1.TABLE_VERSION,
        "cases_compared": dict(sorted(counts.items())),
        "rules_by_domain": dict(sorted(rules.items())),
        "mismatches_listed": mismatches,
        "seconds": round(time.perf_counter() - t0, 1),
        "compared_fields": ["rule", "class", "status", "value", "disposition", "question", "reasons", "failure"],
    }
    name = "differential_all.json" if args.all else "differential.json"
    target = args.out or Path(__file__).parent / name
    target.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(out["cases_compared"]), out["seconds"], "s")
    return 0 if not counts.get("valid_mismatch") else 1


if __name__ == "__main__":
    raise SystemExit(main())
