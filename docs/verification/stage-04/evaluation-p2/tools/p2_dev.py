"""Stage 04 P2: the development run of the baseline and the sensitivity variants (plan 8.4, E-08, D-069).

DEVELOPMENT EVIDENCE ONLY. The set is the design-exposed one of Step 9: every Stage 03 capture bundle tracked in git
(``git ls-files``), one bundle per distinct (wiki, revision), a complete capture before a partial one, then the first
path. Every one of these revisions is already exposed to Stage 04 design (owner decision D-5) and excluded from the
frame. No label exists for them, so nothing here is precision, recall or an evaluation: the run shows that the
evaluation tooling computes on real investigations, that its faithfulness self-checks hold on every one, and which
variant is computable for how many candidates, before the draw.

Each revision runs one investigation offline through the production plan with the frozen detector (in this process,
every socket refused), as Step 9 did. Then, on its retained evidence:

- ``p2_sensitivity.variants`` (self-checks, then variants a, b, c);
- ``p2_baseline.flagged_units`` on the retained extraction.

P2: the same run on the frozen freeze-2 engine (dt-2), refused unless ``p2_common.engine_check`` passes (D-076);
the historical result ``evaluation/dev/DEV_RUN.json`` (dt-1) is unchanged.

Run (three shards in parallel, then merge; ``T`` = ``docs/verification/stage-04/evaluation-p2/tools``)::

    uv run python -P T/p2_dev.py run --index <rw index> --shard 0/3 --out part0.json   # and 1/3, 2/3
    uv run python -P T/p2_dev.py merge --index <rw index> --parts part0.json part1.json part2.json --out DEV_RUN.json
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import p2_baseline as BL
import p2_sensitivity as SV
from p2_common import REPO, engine_check, file_sha256, git, write_json

sys.path.insert(0, str(REPO / "tests" / "stage04"))

import pytest
import step8_support as S8

from citerift.investigation.adapters.plan import Integration

EXECUTED = ("p2_baseline.py", "p2_common.py", "p2_dev.py", "p2_sensitivity.py")
POSITIVE = ("RETRACTED_WORK_CITED", "CONCERN_CITED", "CORRECTION_CITED", "REINSTATED_WORK_CITED")


def bundles() -> list[tuple[tuple[str, int], Path, dict[str, Any]]]:
    files = git("ls-files", "*capture.json").split()
    best: dict[tuple[str, int], tuple[tuple[int, str], Path, dict[str, Any]]] = {}
    for f in files:
        d = (REPO / f).parent
        cap = json.loads((d / "capture.json").read_text(encoding="utf-8"))
        if "request" not in cap or "page" not in cap:
            continue
        key = (cap["request"]["wiki"], cap["page"]["revision_id"])
        rank = (0 if cap["status"] == "complete" else 1, str(d.relative_to(REPO)))
        if key not in best or rank < best[key][0]:
            best[key] = (rank, d, cap)
    return [(k, v[1], v[2]) for k, v in sorted(best.items())]


def unit_sets(per_candidate: dict[str, Any]) -> dict[str, frozenset[str]]:
    return {u: frozenset(c) for u, c in SV.unit_classes(per_candidate).items()}


def one(tmp: Path, bundle: Path, index: Path, conn: sqlite3.Connection) -> dict[str, Any]:
    root = S8.memory_root(tmp)
    payload = S8.create(root, S8.request(bundle, index, root))
    result = S8.run(root, payload, Integration())
    row: dict[str, Any] = {"lifecycle": result.status}
    if result.status not in ("COMPLETED", "NEEDS_RESOLUTION"):
        return row
    try:
        var = SV.variants(root, payload["investigation_key"])
    except SV.Unfaithful as exc:
        row["unfaithful"] = str(exc)
        return row
    row["self_checks"] = "passed"
    frozen = unit_sets(var["frozen"])
    row["engine_unit_classes"] = dict(Counter("+".join(sorted(c)) for c in frozen.values()))
    for v in ("a", "b", "c"):
        other = unit_sets(var[v])
        changed = {
            u: ("+".join(sorted(frozen.get(u, ()))) or "NO_CANDIDATE", "+".join(sorted(c)))
            for u, c in other.items()
            if c != frozen.get(u)
        }
        changed.update({u: ("+".join(sorted(c)), "NO_CANDIDATE") for u, c in frozen.items() if u not in other})
        row[f"variant_{v}"] = {
            "candidates": len(var[v]),
            "not_computable": sum(1 for c in var[v].values() if c["class"] == SV.NOT_COMPUTABLE),
            "positive_units": sum(1 for c in other.values() if set(c) & set(POSITIVE)),
            "changed_units": dict(Counter(f"{a} -> {b}" for a, b in changed.values())),
        }
    extraction = SV.Retained(root, payload["investigation_key"]).one(SV.EXTRACTION)[1]
    flagged = BL.flagged_units(extraction, conn)
    row["baseline"] = {
        "flagged_units": len(flagged),
        "flagged_by_engine_classes": dict(
            Counter("+".join(sorted(frozen.get(u, ()))) or "NO_CANDIDATE" for u in flagged)
        ),
    }
    row["engine_positive_units"] = sum(1 for c in frozen.values() if set(c) & set(POSITIVE))
    return row


def run_shard(index: Path, shard: int, shards: int) -> dict[str, Any]:
    out: dict[str, Any] = {"shard": [shard, shards], "revisions": {}}
    rows = [r for i, r in enumerate(bundles()) if i % shards == shard]
    with (
        tempfile.TemporaryDirectory() as d,
        pytest.MonkeyPatch.context() as mp,
        sqlite3.connect(f"file:{index}?mode=ro", uri=True) as conn,
    ):
        offline = S8.NoNetwork(mp)
        for i, ((wiki, rev), bundle, cap) in enumerate(rows):
            row = {"bundle": str(bundle.relative_to(REPO)), "capture_status": cap["status"]}
            row.update(one(Path(d) / str(i), bundle, index, conn))
            out["revisions"][f"{wiki}-{rev}"] = row
            print(shard, i, wiki, rev, row["lifecycle"], row.get("self_checks") or row.get("unfaithful"), flush=True)
        out["network_attempts"] = len(offline.attempts)
    return out


def totals_of(revisions: dict[str, Any]) -> dict[str, Any]:
    revs = list(revisions.values())
    totals: dict[str, Any] = {
        "revisions": len(revs),
        "lifecycle": dict(Counter(r["lifecycle"] for r in revs)),
        "self_checks_passed": sum(1 for r in revs if r.get("self_checks") == "passed"),
        "unfaithful": sum(1 for r in revs if "unfaithful" in r),
        "engine_positive_units": sum(r.get("engine_positive_units", 0) for r in revs),
        "baseline_flagged_units": sum(r["baseline"]["flagged_units"] for r in revs if "baseline" in r),
    }
    flagged: Counter[str] = Counter()
    for r in revs:
        flagged.update((r.get("baseline") or {}).get("flagged_by_engine_classes") or {})
    totals["baseline_flagged_by_engine_classes"] = dict(sorted(flagged.items()))
    for v in ("a", "b", "c"):
        changed: Counter[str] = Counter()
        for r in revs:
            changed.update((r.get(f"variant_{v}") or {}).get("changed_units") or {})
        totals[f"variant_{v}"] = {
            "candidates": sum((r.get(f"variant_{v}") or {}).get("candidates", 0) for r in revs),
            "not_computable": sum((r.get(f"variant_{v}") or {}).get("not_computable", 0) for r in revs),
            "positive_units": sum((r.get(f"variant_{v}") or {}).get("positive_units", 0) for r in revs),
            "changed_units": dict(sorted(changed.items())),
        }
    return totals


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Stage 04 P2 development run of the baseline and variants")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="one shard of the revisions (every n-th, from k)")
    r.add_argument("--index", type=Path, required=True)
    r.add_argument("--shard", required=True, help="k/n")
    r.add_argument("--out", type=Path, required=True)
    m = sub.add_parser("merge", help="the shards into one result with totals")
    m.add_argument("--index", type=Path, required=True)
    m.add_argument("--parts", type=Path, nargs="+", required=True)
    m.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    index = a.index.resolve()
    identity = engine_check()
    if a.cmd == "run":
        k, n = (int(x) for x in a.shard.split("/"))
        t0 = time.perf_counter()
        part = run_shard(index, k, n)
        part["seconds"] = round(time.perf_counter() - t0, 1)
        part["engine_identity"] = identity
        write_json(a.out, part)
        return 0
    parts = [json.loads(p.read_text(encoding="utf-8")) for p in a.parts]
    if any(p.get("engine_identity", {}).get("identity") != identity["identity"] for p in parts):
        sys.exit("a shard ran on another engine identity")
    shards = sorted(p["shard"][0] for p in parts)
    if shards != list(range(parts[0]["shard"][1])):
        sys.exit(f"shards {shards} do not cover 0..{parts[0]['shard'][1] - 1}")
    revisions = {k: v for p in parts for k, v in p["revisions"].items()}
    if len(revisions) != len(bundles()):
        sys.exit("the shards do not cover every revision")
    out: dict[str, Any] = {
        "label": "DEVELOPMENT EVIDENCE ONLY (design-exposed revisions, owner decision D-5); no labels, not an "
        "evaluation",
        "index_sha256": file_sha256(index),
        "engine_identity": identity,
        "tools": {n: file_sha256(Path(__file__).resolve().parent / n) for n in EXECUTED},
        "head": git("rev-parse", "HEAD"),
        "shards": len(parts),
        "seconds_per_shard": [p["seconds"] for p in sorted(parts, key=lambda p: p["shard"][0])],
        "network_attempts": sum(p["network_attempts"] for p in parts),
        "totals": totals_of(revisions),
        "revisions": dict(sorted(revisions.items())),
    }
    write_json(a.out, out)
    print(json.dumps(out["totals"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
