"""Resource measurements for the evaluation run (FROZEN_PROTOCOL.md section 11 budgets).

Usage: python measure_holdout.py CAPTURE_DIR [CAPTURE_DIR ...] > costs.json

Extraction: every final bundle named in each CAPTURE_DIR/capture_states.json is extracted by the production worker
code in a fresh interpreter, once cold and five times warm (``measure_costs.run_once`` of the calibration, which
reports wall and CPU time, VmHWM and VmPeak and the extraction digest). Network: every recorded request of every
capture attempt (the ``attempts`` of each capture record in captures.jsonl, published or not) and the selection's
requests. No request is made by this script.
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "calibration" / "scripts"))

from measure_costs import quantiles, run_once

SELECTION = Path(__file__).resolve().parents[1] / "selection" / "selection.json"


def _bundle(path: str, capture_dir: Path) -> Path:
    p = Path(path)
    return p if p.exists() else capture_dir / "bundles" / p.parent.name / p.name


def extraction(dirs: list[Path]) -> dict[str, Any]:
    rows = []
    for d in dirs:
        states = json.loads((d / "capture_states.json").read_text(encoding="utf-8"))["articles"]
        for key, st in sorted(states.items()):
            if not st["final"]["bundle"]:
                continue
            b = _bundle(st["final"]["bundle"], d)
            cap = json.loads((b / "capture.json").read_text(encoding="utf-8"))
            cold = run_once(b)
            warm = [run_once(b) for _ in range(5)]
            rows.append(
                {
                    "article": key,
                    "revision_id": cap["page"]["revision_id"],
                    "source_bytes": cap["source"]["bytes"],
                    "html_bytes": cap["render"].get("bytes"),
                    "bundle_bytes": sum(f.stat().st_size for f in b.rglob("*") if f.is_file()),
                    "output_bytes": cold["output_bytes"],
                    "status": cold["status"],
                    "deterministic": len({cold["digest"], *(w["digest"] for w in warm)}) == 1,
                    "cold": {k: cold[k] for k in ("wall_s", "cpu_s", "vm_hwm_kib", "vm_peak_kib")},
                    "warm_median": {
                        k: statistics.median(w[k] for w in warm)
                        for k in ("wall_s", "cpu_s", "vm_hwm_kib", "vm_peak_kib")
                    },
                }
            )
    summary: dict[str, Any] = {
        k: quantiles([r["warm_median"][k] for r in rows]) for k in ("wall_s", "cpu_s", "vm_hwm_kib", "vm_peak_kib")
    }
    summary["cold_wall_s"] = quantiles([r["cold"]["wall_s"] for r in rows])
    summary["all_deterministic"] = all(r["deterministic"] for r in rows)
    return {"rows": rows, "summary": summary}


def network(dirs: list[Path]) -> dict[str, Any]:
    attempts = []
    for d in dirs:
        for line in (d / "captures.jsonl").read_text(encoding="utf-8").splitlines():
            entry = json.loads(line)
            cap = (entry.get("stdout") or {}).get("capture") or {}
            attempts += cap.get("attempts") or []
    sel = json.loads(SELECTION.read_text(encoding="utf-8"))["requests"]
    codes = Counter(str(a.get("code")) for a in attempts)
    statuses = Counter(str(a.get("status")) for a in attempts)
    accepted = [a for a in attempts if a.get("code") is None]
    retry_after = [a["retry_after_s"] for a in attempts if a.get("retry_after_s") is not None]
    return {
        "capture_requests": len(attempts),
        "selection_requests": len(sel),
        "total_requests": len(attempts) + len(sel),
        "capture_statuses": dict(statuses),
        "capture_codes": dict(codes),
        "rate_limited_share": round(statuses.get("429", 0) / len(attempts), 3) if attempts else None,
        "retry_after_s": quantiles(retry_after) if retry_after else None,
        "request_seconds": quantiles([a["duration_s"] for a in attempts]) if attempts else None,
        "accepted_wire_bytes": sum(a.get("wire_bytes", 0) for a in accepted),
        "accepted_body_bytes": sum(a.get("body_bytes", 0) for a in accepted),
    }


def main() -> int:
    dirs = [Path(p) for p in sys.argv[1:]]
    result = {"python": sys.version.split()[0], "extraction": extraction(dirs), "network": network(dirs)}
    sys.stdout.write(json.dumps(result, indent=1, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
