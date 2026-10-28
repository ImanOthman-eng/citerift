"""Calibration step C: measure extraction cost per development bundle and network cost from the acquisition logs.

Usage: python measure_costs.py BUNDLES_DIR ACQUISITION_JSON [ACQUISITION_JSON ...] > costs.json

Extraction: each bundle is extracted by the production worker code in a fresh interpreter, once cold (first run
after the bundle files were read by nothing else in that process) and five times warm (median). The process resets
its peak-RSS counter first (Linux keeps the parent's peak across fork and exec), then reports VmHWM (peak resident
set) and VmPeak (peak address space, which is what RLIMIT_AS limits). No limit is applied here, so the figures show
the natural peak that the 512 MiB address-space limit must cover.

Network: requests, HTTP statuses, Retry-After values and waiting time are read from the acquisition logs written by
acquire_dev.py; no request is made by this script.
"""

from __future__ import annotations

import json
import statistics
import subprocess
import sys
from collections import Counter
from datetime import datetime
from itertools import pairwise
from pathlib import Path
from typing import Any

SRC = str(Path(__file__).resolve().parents[5] / "src")
MEASURE = r"""
import io, json, sys, time
from pathlib import Path
Path("/proc/self/clear_refs").write_text("5")
sys.path.insert(0, sys.argv[1])
t0 = time.perf_counter(); c0 = time.process_time()
from citerift.wiki.worker import main
real = sys.stdout
sink = io.BytesIO()
sys.stdout = io.TextIOWrapper(sink)
code = main(sys.argv[2:])
data = sink.getvalue()
wall = time.perf_counter() - t0; cpu = time.process_time() - c0
status = Path("/proc/self/status").read_text().splitlines()
kib = {line.split(":")[0]: int(line.split()[1]) for line in status if line.startswith(("VmHWM", "VmPeak"))}
doc = json.loads(data)
real.write(json.dumps({"exit": code, "wall_s": wall, "cpu_s": cpu, "vm_hwm_kib": kib["VmHWM"],
                       "vm_peak_kib": kib["VmPeak"], "output_bytes": len(data),
                       "status": doc["status"], "digest": doc["extraction_digest"]}))
"""
CONFIG = json.dumps(
    {
        "max_nodes": 400000,
        "max_depth": 60,
        "max_refs": 20000,
        "max_templates": 50000,
        "max_candidates": 50000,
        "max_render_elements": 2000000,
        "worker_memory_mib": 1024,
        "worker_wall_s": 30.0,
    }
)


def run_once(bundle: Path) -> dict[str, Any]:
    out = subprocess.run(  # noqa: S603 - the running interpreter with fixed code
        [sys.executable, "-I", "-c", MEASURE, SRC, str(bundle), CONFIG], capture_output=True, check=True
    )
    result: dict[str, Any] = json.loads(out.stdout)
    return result


def quantiles(values: list[float]) -> dict[str, float]:
    values = sorted(values)
    p95 = values[min(len(values) - 1, round(0.95 * (len(values) - 1)))]
    return {"n": len(values), "p50": statistics.median(values), "p95": p95, "max": values[-1]}


def extraction(bundles: Path) -> dict[str, Any]:
    rows = []
    for b in sorted(bundles.iterdir()):
        cap = json.loads((b / "capture.json").read_text())
        cold = run_once(b)
        warm = [run_once(b) for _ in range(5)]
        rows.append(
            {
                "bundle": b.name,
                "wiki": cap["page"]["wiki"],
                "revision_id": cap["page"]["revision_id"],
                "source_bytes": cap["source"]["bytes"],
                "html_bytes": cap["render"].get("bytes"),
                "bundle_bytes": sum(f.stat().st_size for f in b.rglob("*") if f.is_file()),
                "output_bytes": cold["output_bytes"],
                "status": cold["status"],
                "deterministic": len({cold["digest"], *(w["digest"] for w in warm)}) == 1,
                "cold": {k: cold[k] for k in ("wall_s", "cpu_s", "vm_hwm_kib", "vm_peak_kib")},
                "warm_median": {
                    k: statistics.median(w[k] for w in warm) for k in ("wall_s", "cpu_s", "vm_hwm_kib", "vm_peak_kib")
                },
            }
        )
    summary = {
        k: quantiles([r["warm_median"][k] for r in rows]) for k in ("wall_s", "cpu_s", "vm_hwm_kib", "vm_peak_kib")
    }
    summary["cold_wall_s"] = quantiles([r["cold"]["wall_s"] for r in rows])
    return {"rows": rows, "summary": summary}


def _t(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ")


def network(paths: list[Path]) -> dict[str, Any]:
    entries = []
    for p in paths:
        entries += json.loads(p.read_text())["log"]
    statuses = Counter(str(e["status"]) for e in entries)
    retry_after = [float(e["headers"]["retry-after"]) for e in entries if "retry-after" in e.get("headers", {})]
    times = sorted(_t(e["at"]) for e in entries)
    gaps = [(b - a).total_seconds() for a, b in pairwise(times)]
    ok = [e for e in entries if e["status"] == 200]
    return {
        "requests": len(entries),
        "statuses": dict(statuses),
        "rate_limited_share": round(statuses.get("429", 0) / len(entries), 3),
        "retry_after_s": quantiles(retry_after) if retry_after else None,
        "gap_between_requests_s": quantiles([g for g in gaps if g < 600]),
        "request_seconds": quantiles([e["seconds"] for e in entries]),
        "accepted_wire_bytes": sum(e["wire_bytes"] for e in ok),
        "accepted_body_bytes": sum(e["body_bytes"] for e in ok),
        "note": "gaps over 600 s (pauses between runs) are left out of the gap quantiles",
    }


def main() -> int:
    bundles = Path(sys.argv[1])
    logs = [Path(p) for p in sys.argv[2:]]
    import_probe = subprocess.run(  # noqa: S603 - the running interpreter with fixed code
        [
            sys.executable,
            "-I",
            "-X",
            "importtime",
            "-c",
            f"import sys; sys.path.insert(0, {SRC!r}); import citerift.wiki.extract",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    last = [line for line in import_probe.stderr.splitlines() if "citerift.wiki.extract" in line]
    result = {
        "python": sys.version.split()[0],
        "extraction": extraction(bundles),
        "network": network(logs),
        "import_citerift_wiki_extract_cumulative_us": int(last[-1].split("|")[1]) if last else None,
    }
    sys.stdout.write(json.dumps(result, indent=1, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
