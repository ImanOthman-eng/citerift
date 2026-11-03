"""Evaluator packets for the initial draw (AMENDMENT_2026-11-02_CONFIRMATION.md section 7).

Usage (from the repository root): python make_packets.py PLAN_JSON OUT_DIR

Articles are taken in plan order and split, per wiki and split, into evaluator instances of at most 6 articles
(sizes as even as possible). Holdout packets come from ``evaluate.py packets`` (frozen window), challenge packets from
``warning_challenge.py packets``. Each article uses its final (complete) capture bundle. OUT_DIR/<instance>/ holds
the packets; OUT_DIR/ASSIGNMENT.json lists the instances. Nothing here reads a label or an extraction.
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[7]
EVALUATE = ROOT / "docs/verification/stage-03/protocol/scripts/evaluate.py"
CHALLENGE = ROOT / "docs/verification/stage-03/evaluation/confirmation-2026-11/scripts/warning_challenge.py"
MAX_PER_INSTANCE = 6


def main() -> int:
    plan = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    out = Path(sys.argv[2])
    capture = Path(sys.argv[1]).parent / "capture"
    states = json.loads((capture / "capture_states.json").read_text(encoding="utf-8"))["articles"]
    groups: dict[tuple[str, str], list[str]] = {}
    for a in plan["articles"]:
        key = f"{a['split']}/{a['wiki']}-{a['page_id']}"
        final = states[key]["final"]
        if final.get("status") != "complete":
            raise SystemExit(f"{key} has no complete capture")
        groups.setdefault((a["split"], a["wiki"]), []).append(final["bundle"])
    out.mkdir(parents=True, exist_ok=False)
    assignment: list[dict[str, object]] = []
    for (split, wiki), bundles in groups.items():
        n = math.ceil(len(bundles) / MAX_PER_INSTANCE)
        size, extra = divmod(len(bundles), n)
        start = 0
        for i in range(n):
            part = bundles[start : start + size + (i < extra)]
            start += len(part)
            name = f"{wiki}-{'h' if split == 'holdout' else 'c'}{i + 1}"
            tool = EVALUATE if split == "holdout" else CHALLENGE
            subprocess.run(  # noqa: S603 - fixed argv
                [sys.executable, str(tool), "packets", str(out / name / "packets"), *part], check=True
            )
            arts = sorted(p.name for p in (out / name / "packets").iterdir())
            assignment.append({"instance": name, "split": split, "wiki": wiki, "bundles": part, "packets": arts})
    (out / "ASSIGNMENT.json").write_text(json.dumps(assignment, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
