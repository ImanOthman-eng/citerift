"""Run every Step 4 simulation and write the retained evidence.

    uv run python simulations/stage04/run_step4.py [--skip-decision-space]

Outputs (all deterministic except the timings and the transport experiments' elapsed times):

- ``docs/verification/stage-04/simulation/stage02_conformance.json``
- ``docs/verification/stage-04/simulation/controller_model_summary.json``
- ``docs/verification/stage-04/simulation/f11_bounds.json``
- ``docs/verification/stage-04/simulation/decision_space_summary.json``
- ``docs/verification/stage-04/simulation/mutants.json``
- ``simulations/stage04/oracle/`` (frozen dt-1 oracle: MANIFEST.json, dt1_decisions.json, dt1_table.u16le.gz)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

import bounds  # noqa: E402
import controller_model  # noqa: E402
import decision_space  # noqa: E402
import mutants  # noqa: E402
import stage02_conformance  # noqa: E402

OUT = ROOT / "docs" / "verification" / "stage-04" / "simulation"
ORACLE = HERE / "oracle"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-decision-space", action="store_true")
    args = ap.parse_args()
    status: dict[str, object] = {}
    t = time.monotonic()
    conf = stage02_conformance.run(OUT)
    status["conformance"] = {
        "worlds": conf["worlds"],
        "problems": conf["worlds_with_problems"],
        "signatures_equal": conf["signatures_equal"],
    }
    ctl = controller_model.run(OUT)
    status["controller"] = {
        "states": ctl["total_states"],
        "violations": {k: v for k, v in ctl["violations"].items() if v},
        "quotient_sound": [q["sound"] for q in ctl["quotient_checks"]],
    }
    f11 = bounds.run(OUT)
    status["f11"] = f11["conclusion"]["f11_result"]
    if not args.skip_decision_space:
        ds = decision_space.run(OUT, ORACLE, os.cpu_count() or 1, deep=True)
        status["decision_space"] = {
            "cases": ds["cases"],
            "valid": ds["cases_valid"],
            "violations": {k: v["violations"] for k, v in ds["properties"].items() if v["violations"]},
        }
    mt = mutants.run(OUT)
    status["mutants"] = {"injected": mt["mutants_injected"], "detected": mt["mutants_detected"]}
    status["elapsed_s"] = round(time.monotonic() - t, 1)
    print(json.dumps(status, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
