"""Step 9 development measurements on the 232 design-exposed Stage 03 revisions (owner Step 9 items 17 to 19).

The set is the planning join probe's (STAGE04_MASTER_EXECUTION_PACKAGE.md 2.3, owner decision D-5): every retained
Stage 03 capture bundle in the repository, 257 bundle directories naming 232 distinct revisions (ar 113, en 119).
Every one of them is already exposed to Stage 04 design; this is DEVELOPMENT EVIDENCE ONLY. Nothing here is precision,
recall or an evaluation; no rule, reason or threshold was changed after these numbers were seen, and no Stage 04
evaluation frame or holdout is drawn or read.

For each distinct revision (one bundle per revision: a complete capture before a partial one, then the first path),
one investigation runs offline through the production plan (VALIDATE to VERIFY) with the production detector dt-1 and
the Stage 02 index built from the pinned Retraction Watch snapshot (receipt ``rw-a987928``); every socket is refused
in this process. The script records each investigation's lifecycle and terminal code, its claims by class and rule,
the reason codes, and the lookups; then it compares the naive baseline the plan defines ("flag a unit if any
candidate key appears in a Retraction Watch identifier column", here: a Q1 lookup of the key that is not
``no_record``, i.e. the key is in an original or notice identifier column of the index) with the engine, unit by
unit. A second variant also counts the keys of observation roles (marker targets, mentions) of the unit.

Run: ``uv run python docs/verification/stage-04/review/step9/dev_measurements.py <index.sqlite>``
Writes ``dev_measurements.json`` beside itself (one row per revision plus the totals).
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO / "tests" / "stage04"))

import step8_support as S8  # noqa: E402

from citerift.investigation.adapters.lookup import file_sha256  # noqa: E402
from citerift.investigation.adapters.plan import Integration  # noqa: E402
from citerift.investigation.canonical import canon  # noqa: E402

FOUND = ("matched", "notice_only", "ambiguous_identity")


def bundles() -> list[tuple[tuple[str, int], Path, dict[str, Any]]]:
    """One bundle per distinct (wiki, revision): a complete capture first, then the first path."""
    dirs = sorted({p.parent for p in REPO.glob("**/capture.json") if not ({".venv", ".git"} & set(p.parts))})
    best: dict[tuple[str, int], tuple[tuple[int, str], Path, dict[str, Any]]] = {}
    for d in dirs:
        cap = json.loads((d / "capture.json").read_text(encoding="utf-8"))
        key = (cap["request"]["wiki"], cap["page"]["revision_id"])
        rank = (0 if cap["status"] == "complete" else 1, str(d.relative_to(REPO)))
        if key not in best or rank < best[key][0]:
            best[key] = (rank, d, cap)
    return [(k, v[1], v[2]) for k, v in sorted(best.items())]


def one(tmp: Path, bundle: Path, index: Path) -> dict[str, Any]:
    root = S8.memory_root(tmp)
    payload = S8.create(root, S8.request(bundle, index, root))
    result = S8.run(root, payload, Integration())
    recs, blobs = S8.committed(root, payload)
    out: dict[str, Any] = {"lifecycle": result.status}
    term = result.explanation.get("terminated_by") or {}
    if result.status not in ("COMPLETED", "NEEDS_RESOLUTION"):
        out["terminated_by"] = {k: term.get(k) for k in ("step", "code", "reason")}
    claims = [r["payload"] for r in recs if r["kind"] == "claim_recorded"]
    inputs = next(
        (v for v in blobs.values() if isinstance(v, dict) and str(v.get("schema", "")).endswith("candidate-inputs")),
        None,
    )
    plan = next(
        (v for v in blobs.values() if isinstance(v, dict) and str(v.get("schema", "")).endswith("lookup-plan")), None
    )
    out["claims_by_class"] = dict(Counter(c["class"] for c in claims))
    out["claims_by_rule"] = dict(Counter(c["rule"] for c in claims))
    out["reasons"] = dict(Counter(r for c in claims for r in c["reasons"]))
    out["upstream_reasons"] = dict(Counter(u["code"] for c in claims for u in c["upstream_reasons"]))
    out["positive_works"] = sorted(
        {canon(c["candidate"]["keys"]).decode() for c in claims if c["status"] == "verified_fact"}
    )
    out["conflict_alternatives"] = [
        {"keys": c["candidate"]["keys"], "class": c["class"], "alternatives": [a["value"] for a in c["alternatives"]]}
        for c in claims
        if c["status"] == "conflicting"
    ]
    if inputs is None or plan is None:
        return out
    states = {canon(e["query"]).decode(): blobs[e["observation"]]["result"]["lookup_state"] for e in plan["lookups"]}
    out["lookup_states"] = dict(Counter(states.values()))
    out["candidates"] = len(inputs["candidates"])
    out["multi_candidate_units"] = len(
        {c["unit_id"] for c in inputs["candidates"] if "CO_REPORTED_MULTIPLE" in c["flags"]}
    )
    ext = blobs[inputs["extraction"]]
    by_cand = {c["cand_ref"]: c for c in claims}
    unit_classes: dict[str, set[str]] = {}
    unit_keys: dict[str, set[str]] = {}
    for cand in inputs["candidates"]:
        claim = by_cand.get(cand["cand_ref"])
        unit_classes.setdefault(cand["unit_id"], set()).add(claim["class"] if claim else "NO_CLAIM")
        for k in cand["keys"]:
            unit_keys.setdefault(cand["unit_id"], set()).add(
                canon(
                    {"doi": k["normalized"], "pmid": None}
                    if k["scheme"] == "doi"
                    else {"doi": None, "pmid": k["normalized"]}
                ).decode()
            )
    obs_keys: dict[str, set[str]] = {}
    for ident in ext["identifiers"]:
        norm = ident.get("normalization") or {}
        if ident.get("unit_id") and norm.get("valid") and norm.get("normalized"):
            q = {"doi": None, "pmid": None, ident["scheme"]: norm["normalized"]}
            obs_keys.setdefault(ident["unit_id"], set()).add(canon(q).decode())
    naive: dict[str, Counter[str]] = {"candidate_keys": Counter(), "all_unit_keys": Counter()}
    for unit, classes in unit_classes.items():
        label = "+".join(sorted(classes))
        if any(states.get(q) in FOUND for q in unit_keys.get(unit, ())):
            naive["candidate_keys"][label] += 1
        if any(states.get(q) in FOUND for q in unit_keys.get(unit, set()) | obs_keys.get(unit, set())):
            naive["all_unit_keys"][label] += 1
    out["naive_flagged_units_by_engine_class"] = {k: dict(v) for k, v in naive.items()}
    # Occurrence level (the planning probe's unit of count, STAGE04_MASTER_EXECUTION_PACKAGE.md 2.3): every valid
    # identifier occurrence of the extraction, any role, with its Q1 lookup state and, when matched, the value.
    values = {
        canon(e["query"]).decode(): (
            ((blobs[e["observation"]]["result"].get("projection") or {}).get("retraction_status") or {}).get("value")
        )
        for e in plan["lookups"]
    }
    occ: Counter[str] = Counter()
    for ident in ext["identifiers"]:
        norm = ident.get("normalization") or {}
        if not (norm.get("valid") and norm.get("normalized")):
            continue
        q = canon({"doi": None, "pmid": None, ident["scheme"]: norm["normalized"]}).decode()
        state = states.get(q, "not_looked_up")
        if state == "matched":
            state = f"matched:{values.get(q)}"
        occ[f"{ident.get('role')}|{state}"] += 1
    out["occurrences_by_role_and_q1_state"] = dict(sorted(occ.items()))
    return out


def main() -> int:
    index = Path(sys.argv[1]).resolve()
    out: dict[str, Any] = {
        "label": "DEVELOPMENT EVIDENCE ONLY (design-exposed revisions, owner decision D-5); not an evaluation",
        "index": {"file": index.name, "sha256": file_sha256(index)},
        "detector": "dt-1 (citerift.investigation.adapters.detector.dt1_detector)",
        "revisions": {},
    }
    t0 = time.perf_counter()
    rows = bundles()
    out["bundle_directories"] = len(
        {p.parent for p in REPO.glob("**/capture.json") if not ({".venv", ".git"} & set(p.parts))}
    )
    out["distinct_revisions"] = len(rows)
    with tempfile.TemporaryDirectory() as d, pytest.MonkeyPatch.context() as mp:
        offline = S8.NoNetwork(mp)
        for i, ((wiki, rev), bundle, cap) in enumerate(rows):
            row = {"bundle": str(bundle.relative_to(REPO)), "capture_status": cap["status"]}
            row.update(one(Path(d) / str(i), bundle, index))
            out["revisions"][f"{wiki}-{rev}"] = row
            print(i, wiki, rev, row["lifecycle"], row.get("claims_by_class"), flush=True)
        out["network_attempts"] = len(offline.attempts)
    totals: dict[str, Counter[str]] = {
        k: Counter()
        for k in (
            "lifecycle",
            "claims_by_class",
            "claims_by_rule",
            "reasons",
            "upstream_reasons",
            "lookup_states",
            "terminated_by",
            "occurrences_by_role_and_q1_state",
        )
    }
    naive: dict[str, Counter[str]] = {"candidate_keys": Counter(), "all_unit_keys": Counter()}
    for row in out["revisions"].values():
        totals["lifecycle"][row["lifecycle"]] += 1
        for k in (
            "claims_by_class",
            "claims_by_rule",
            "reasons",
            "upstream_reasons",
            "lookup_states",
            "occurrences_by_role_and_q1_state",
        ):
            totals[k].update(row.get(k) or {})
        if "terminated_by" in row:
            totals["terminated_by"][f"{row['terminated_by']['step']}:{row['terminated_by']['code']}"] += 1
        for k, v in (row.get("naive_flagged_units_by_engine_class") or {}).items():
            naive[k].update(v)
    out["totals"] = {k: dict(sorted(v.items())) for k, v in totals.items()}
    out["totals"]["revisions_with_positive_claim"] = sum(
        1 for r in out["revisions"].values() if r.get("positive_works")
    )
    out["totals"]["multi_candidate_units"] = sum(r.get("multi_candidate_units", 0) for r in out["revisions"].values())
    out["naive_baseline"] = {k: dict(sorted(v.items())) for k, v in naive.items()}
    out["seconds"] = round(time.perf_counter() - t0, 1)
    path = Path(__file__).parent / "dev_measurements.json"
    path.write_text(json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(out["totals"], indent=1))
    return 0 if out["network_attempts"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
