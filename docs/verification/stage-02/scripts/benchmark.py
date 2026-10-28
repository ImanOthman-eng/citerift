"""Stage 02 resource benchmarks (SPECIFICATION.md 13; gate 02-H) and the double-build check (gate 02-B).

Protocol, declared before measurement:
- builds: N full builds of the pinned CSV, each in a fresh Python process that reports its own peak RSS
  (getrusage ru_maxrss); wall time measured by the parent; database size from the published file.
- warm lookups: 2,000 queries in the mix SPECIFICATION.md 13 declares (MIX below), one process, the index opened
  once; the OS page cache is whatever the earlier builds left (warm); no claim of cache eviction is made.
- high fan-out lookups: 100 extra warm queries on the 50 originals with the most events, reported separately
  (outside the budget mix).
- fresh-process lookups: 200 queries of the same mix, each a new ``python -m citerift.retraction.cli lookup``
  process (interpreter start, imports, index open, query, JSON output).
- every query returns one full page (at most 20 events); the hit/miss mix and fan-out are recorded.
- tension: 200 warm Evidence Tension reports (all interventions of the default plan) on matched DOIs.
- ambiguity: 200 warm baseline candidate retrievals for events that have an original DOI, the event's own
  identifiers not used.
- digests of all builds are compared; two builds must give equal artifact and semantic digests and equal
  query output.

Run: python docs/verification/stage-02/scripts/benchmark.py --csv CSV --oracle ORACLE.json --work data/index/bench \
  --out OUT.json
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import random
import sqlite3
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from citerift.retraction import ambiguity, tension
from citerift.retraction.query import Index, render

CHILD = """
import json, resource, sys, time
from pathlib import Path
from citerift.retraction.source import load_receipt
from citerift.retraction.store import build
t = time.perf_counter()
r = build(Path(sys.argv[1]), load_receipt(), Path(sys.argv[2]))
print(json.dumps({"seconds": time.perf_counter() - t, "maxrss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                  "index": str(r.index_path), "digests": r.manifest["digests"], "counts": r.manifest["counts"]}))
"""
# SPECIFICATION.md 13: 40% matched DOI, 10% matched PMID, 10% notice-only, 5% ambiguous PMID, 5% two-ID,
# 25% absent synthetic, 5% invalid.
MIX = {
    "doi_hit": 800,
    "pmid_hit": 200,
    "notice_only": 200,
    "ambiguous_pmid": 100,
    "dual": 100,
    "miss": 500,
    "invalid": 100,
}
HIGH_FANOUT = 100
INVALID = ("10.", "10.1234", "doi:", "0", "-1", "12a45", "https://doi.org/", "pmid:", " ", "10.abc/x")


def pct(values: list[float], q: float) -> float:
    s = sorted(values)
    return s[min(len(s) - 1, max(0, round(q * len(s) + 0.5) - 1))]


def summary(values: list[float]) -> dict[str, float]:
    return {
        "n": len(values),
        "p50_ms": round(1000 * pct(values, 0.50), 3),
        "p95_ms": round(1000 * pct(values, 0.95), 3),
        "max_ms": round(1000 * max(values), 3),
        "mean_ms": round(1000 * statistics.fmean(values), 3),
    }


def queries(oracle: dict[str, Any], index: Path, scale: int, seed: int) -> list[tuple[str, str | None, str | None]]:
    rng = random.Random(seed)  # noqa: S311 - a reproducible workload, not a secret
    doi_orig = sorted(k for k, v in oracle["doi"].items() if v["original"])
    pmid_orig = sorted(k for k, v in oracle["pmid"].items() if v["original"])
    notice_only = sorted(k for k, v in oracle["doi"].items() if v["notice"] and not v["original"])
    conn = sqlite3.connect(f"file:{index}?mode=ro", uri=True)
    ambiguous = [
        k
        for (k,) in conn.execute(
            "SELECT original_pmid FROM event WHERE original_pmid IS NOT NULL AND original_doi IS NOT NULL "
            "GROUP BY original_pmid HAVING COUNT(DISTINCT original_doi) > 1 ORDER BY original_pmid"
        )
    ]
    dual = conn.execute(
        "SELECT original_doi, original_pmid FROM event WHERE original_doi IS NOT NULL AND original_pmid IS NOT NULL "
        "ORDER BY ordinal"
    ).fetchall()
    fanout = [
        k
        for (k,) in conn.execute(
            "SELECT original_doi FROM event WHERE original_doi IS NOT NULL GROUP BY original_doi "
            "ORDER BY COUNT(*) DESC, original_doi LIMIT 50"
        )
    ]
    conn.close()
    misses = oracle["absent_keys"]["doi"] + oracle["absent_keys"]["pmid"]
    out: list[tuple[str, str | None, str | None]] = []
    for kind, n in MIX.items():
        for _ in range(n // scale):
            if kind == "doi_hit":
                out.append((kind, rng.choice(doi_orig), None))
            elif kind == "pmid_hit":
                out.append((kind, None, rng.choice(pmid_orig)))
            elif kind == "notice_only":
                out.append((kind, rng.choice(notice_only), None))
            elif kind == "ambiguous_pmid":
                out.append((kind, None, rng.choice(ambiguous)))
            elif kind == "dual":
                d, p = rng.choice(dual)
                out.append((kind, d, p))
            elif kind == "miss":
                k = rng.choice(misses)
                out.append((kind, k, None) if k.startswith("10.") else (kind, None, k))
            elif kind == "invalid":
                k = rng.choice(INVALID)
                out.append((kind, k, None) if not k.isdigit() and not k.startswith("-") else (kind, None, k))
            else:
                raise ValueError(kind)
    rng.shuffle(out)
    extra = [("high_fanout", rng.choice(fanout), None) for _ in range(HIGH_FANOUT // scale)]
    return out + extra


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, required=True)
    ap.add_argument("--oracle", type=Path, required=True)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--builds", type=int, default=5)
    args = ap.parse_args(argv)
    builds = []
    for i in range(args.builds):
        out_dir = args.work / f"build{i + 1}"
        t = time.perf_counter()
        proc = subprocess.run(  # noqa: S603 - fixed interpreter and arguments
            [sys.executable, "-c", CHILD, str(args.csv), str(out_dir)], capture_output=True, text=True, check=True
        )
        wall = time.perf_counter() - t
        child = json.loads(proc.stdout.strip().splitlines()[-1])
        child["wall_seconds"] = round(wall, 3)
        child["seconds"] = round(child["seconds"], 3)
        child["db_bytes"] = Path(child["index"]).stat().st_size
        builds.append(child)
        print(
            json.dumps({"build": i + 1, "wall": child["wall_seconds"], "rss_mib": round(child["maxrss_kib"] / 1024, 1)})
        )
    index = Path(builds[0]["index"])
    oracle = json.loads(args.oracle.read_text(encoding="utf-8"))
    warm_q = queries(oracle, index, 1, 20261027)
    fresh_q = queries(oracle, index, 10, 20261028)
    warm: dict[str, list[float]] = {}
    gather_t: list[float] = []
    render_t: list[float] = []
    serial_t: list[float] = []
    states: dict[str, int] = {}
    max_events = 0
    with Index(index) as ix:
        for kind, d, p in warm_q:
            t0 = time.perf_counter()
            ev = ix.gather(d, p)
            t1 = time.perf_counter()
            out = render(ev, ix.snapshot_id)
            t2 = time.perf_counter()
            json.dumps(out, sort_keys=True, ensure_ascii=False)
            t3 = time.perf_counter()
            warm.setdefault(kind, []).append(t3 - t0)
            gather_t.append(t1 - t0)
            render_t.append(t2 - t1)
            serial_t.append(t3 - t2)
            states[out["lookup_state"]] = states.get(out["lookup_state"], 0) + 1
            max_events = max(max_events, out["total_event_count"])
            if len(out["events"]) > 20:
                raise RuntimeError("a page holds more than 20 events")
        rng = random.Random(20261029)  # noqa: S311 - a reproducible workload, not a secret
        doi_hits = [d for k, d, _p in warm_q if k == "doi_hit"]
        tension_t: list[float] = []
        for d in rng.sample(doi_hits, 200):
            t0 = time.perf_counter()
            tension.report(ix.gather(d), ix.snapshot_id)
            tension_t.append(time.perf_counter() - t0)
        events = [r[0] for r in ix.conn.execute("SELECT event_id FROM event WHERE original_doi IS NOT NULL")]
        base = ambiguity.Baseline(ix)
        ambiguity_t: list[float] = []
        for event_id in rng.sample(sorted(events), 200):
            probe = ambiguity.probe_for_event(ix, event_id)
            t0 = time.perf_counter()
            base.candidates(probe)
            ambiguity_t.append(time.perf_counter() - t0)
    fresh: list[float] = []
    for _kind, d, p in (q for q in fresh_q if q[0] != "high_fanout"):
        cmd = [sys.executable, "-m", "citerift.retraction.cli", "lookup", "--index", str(index)]
        cmd += (["--doi", d] if d else []) + (["--pmid", p] if p else [])
        t = time.perf_counter()
        subprocess.run(cmd, capture_output=True, check=False)  # noqa: S603 - fixed interpreter and arguments
        fresh.append(time.perf_counter() - t)
    # Double build: equal digests and equal query output across builds.
    digests = {json.dumps(b["digests"], sort_keys=True) for b in builds}
    sample = warm_q[:200]
    outputs = []
    for b in builds[:2]:
        with Index(Path(b["index"])) as ix:
            outputs.append([render(ix.gather(d, p), ix.snapshot_id) for _k, d, p in sample])
    all_warm = [x for k, v in warm.items() if k in MIX for x in v]
    wall = [b["wall_seconds"] for b in builds]
    report = {
        "protocol": __doc__,
        "host": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "sqlite": sqlite3.sqlite_version,
            "cpus": os.cpu_count(),
            "cpu": next(
                (
                    ln.split(":", 1)[1].strip()
                    for ln in Path("/proc/cpuinfo").read_text().splitlines()
                    if ln.startswith("model name")
                ),
                None,
            ),
            "mem_total_kib": next(
                (
                    int(ln.split()[1])
                    for ln in Path("/proc/meminfo").read_text().splitlines()
                    if ln.startswith("MemTotal")
                ),
                None,
            ),
        },
        "builds": builds,
        "build_wall_seconds": {"median": statistics.median(wall), "max": max(wall)},
        "build_peak_rss_mib_max": round(max(b["maxrss_kib"] for b in builds) / 1024, 1),
        "db_mib_max": round(max(b["db_bytes"] for b in builds) / 2**20, 1),
        "double_build": {"distinct_digest_sets": len(digests), "query_output_equal": outputs[0] == outputs[1]},
        "warm": {"all": summary(all_warm), "by_kind": {k: summary(v) for k, v in sorted(warm.items())}},
        "warm_phases": {"gather": summary(gather_t), "render": summary(render_t), "serialize": summary(serial_t)},
        "warm_states": states,
        "warm_max_total_event_count": max_events,
        "fresh_process": summary(fresh),
        "tension": summary(tension_t),
        "ambiguity_candidates": summary(ambiguity_t),
        "mix": MIX,
        "high_fanout_queries": HIGH_FANOUT,
        "budgets": {
            "build_seconds": 120,
            "peak_rss_mib": 512,
            "db_mib": 512,
            "warm_p95_ms": 20,
            "fresh_p95_ms": 1000,
            "tension_p95_ms": 50,
            "ambiguity_p95_ms": 100,
        },
    }
    report["budgets_met"] = {
        "build_seconds": max(wall) <= 120,
        "peak_rss_mib": report["build_peak_rss_mib_max"] <= 512,
        "db_mib": report["db_mib_max"] <= 512,
        "warm_p95_ms": report["warm"]["all"]["p95_ms"] <= 20,
        "fresh_p95_ms": report["fresh_process"]["p95_ms"] <= 1000,
        "tension_p95_ms": report["tension"]["p95_ms"] <= 50,
        "ambiguity_p95_ms": report["ambiguity_candidates"]["p95_ms"] <= 100,
        "double_build": len(digests) == 1 and outputs[0] == outputs[1],
    }
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "budgets_met": report["budgets_met"],
                "warm_p95": report["warm"]["all"]["p95_ms"],
                "fresh_p95": report["fresh_process"]["p95_ms"],
                "tension_p95": report["tension"]["p95_ms"],
                "ambiguity_p95": report["ambiguity_candidates"]["p95_ms"],
                "build": report["build_wall_seconds"],
                "rss": report["build_peak_rss_mib_max"],
                "db": report["db_mib_max"],
            }
        )
    )
    return 0 if all(report["budgets_met"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
