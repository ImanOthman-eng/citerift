"""Stage 04 corrective cycle (D-071): ``VALIDATION.json`` of the freeze-2 candidate, the measured validation summary
that its freeze manifest records (the Step 12 format; the superseded freeze's numbers are the comparison column).

Run from the repository root after the freeze evidence is committed:

    uv run python -P docs/verification/stage-04/freeze-2/build_validation.py

Every number is read from the retained evidence files beside this script, except the test runs (local and CI), which
are recorded here from their logs and the GitHub Actions API, with the run ids so that they can be checked.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
S04 = HERE.parent
TARGET_S = 5.0
CODE_REVISION = "99c4194622498b2343584f08b4f6e52cd2f077e3"
# ``src`` and ``schemas`` of CODE_REVISION equal those of every commit the freeze-2 evidence ran from (dfee881 to
# 99c4194: regression, vertical slice, D-062, performance); the later commits change documents and tests only.

# Test runs of the code revision above. One test fails, by design of the pre-registration P, until the owner decides
# how a P-listed test that pins the superseded engine is handled (decision card on the P-listed test); it is not
# skipped, marked or edited here (owner rule: never skip or disable a test to get green).
KNOWN_FAILURE = (
    "tests/stage04/test_step13_evaluation.py::test_frozen_check_passes_on_the_frozen_engine: the P-listed check "
    "that the running engine is the superseded frozen engine b5bf8ed; fails because src and schemas are now dt-2"
)
TESTS: dict[str, Any] = {
    "code_revision": CODE_REVISION,
    "local": {
        "python": "3.12.3",
        "passed": 3371,
        "failed": 1,
        "skipped": 0,
        "known_failure": KNOWN_FAILURE,
        "wall": "20 min 45 s",
        "note": "full suite in this 4-vCPU container, after the evidence runs",
    },
    "ci": {
        "run_id": 44449077298,
        "run_number": 360,
        "conclusion": "failure (the known failure only)",
        "jobs": {
            "verify (python 3.12)": {"python": "3.12.3", "passed": 3371, "failed": 1, "pytest_reported": "809.54 s"},
            "verify (python 3.13)": {"python": "3.13.14", "passed": 3371, "failed": 1, "pytest_reported": "736.92 s"},
            "ci-gate": {"conclusion": "failure (verify matrix)"},
        },
        "known_failure": KNOWN_FAILURE,
    },
    "lint": {
        "ruff_check": "All checks passed!",
        "ruff_format": "620 files already formatted",
        "mypy": "Success: no issues found in 95 source files",
        "citerift_gov_check": "0 errors, 0 warnings",
    },
}

# GitHub-hosted runner times of the corrective-cycle CI run on the code revision (OD-S12-2: 30 minutes hard timeout).
CI_RUNTIME = [
    {"run": 360, "commit": "99c4194", "py312_tests": "13m29s", "py313_tests": "12m16s", "result": "failure (known)"},
]
CI_RUNTIME_FINDING = "No required job reached 30 minutes (OD-S12-2)."


def load(rel: str) -> Any:
    return json.loads((S04 / rel).read_text(encoding="utf-8"))


def main() -> int:
    vs = load("freeze-2/vertical-slice/vertical_slice.json")
    old_freeze = load("freeze/vertical-slice/vertical_slice.json")
    perf = load("freeze-2/performance/perf_breakdown.json")
    comp = load("freeze-2/performance/verification_components.json")
    d062 = load("freeze-2/d062/two_build_equivalence.json")
    tamper = load("freeze-2/d062/tamper_differential.json")
    rows = []
    for case, c in vs["cases"].items():
        p = c["perf"]["wall_s"]
        old = old_freeze["cases"][case]["perf"]["wall_s"]
        rows.append(
            {
                "case": case,
                "n": p["n"],
                "run_median_s": p["median"],
                "run_p95_s": p["p95"],
                "superseded_freeze_run_p95_s": old["p95"],
                "replay_p95_s": c["perf"]["replay_wall_s"]["p95"],
                "meets_target": p["p95"] <= TARGET_S,
            }
        )
    out = {
        "label": "Stage 04 corrective cycle validation summary (freeze-2 candidate); measured, not an evaluation",
        "code_revision": CODE_REVISION,
        "tests": TESTS,
        "ci_runtime": {"runs": CI_RUNTIME, "finding": CI_RUNTIME_FINDING, "policy": "OD-S12-2 (D-065)"},
        "vertical_slice": {
            "failed_checks": vs["failed_checks"],
            "cases": sorted(vs["cases"]),
            "extras": ["VS-7", "VS-8", "VS-9", "VS-10", "checkpoint", "I-2"],
            "machine": vs["machine"],
            "python": vs["python"],
        },
        "d062": {
            "two_build_failed_checks": d062["failed_checks"],
            "tamper_cases": len(tamper["cases"]),
            "tamper_discrepancies": tamper["discrepancies"],
            "tamper_rejected_only_by_profile": tamper["rejected_only_by_the_profile"],
            "operational_tests": tamper["operational"]["pytest_summary"],
        },
        "performance": {
            "target": "warm retained investigation <= 5 s p95 (D-061, unchanged)",
            "status": "NOT_MET",
            "table": rows,
            "max_run_p95_s": max(r["run_p95_s"] for r in rows),
            "cause": "the D-062 identity-verification profile of D-064 runs in every process that reaches LOOKUP "
            "(no cross-process reuse, OD-S12-1)",
            "breakdown_median_s": perf["median"],
            "verification_components_median_s": comp["median_s"],
        },
    }
    (HERE / "VALIDATION.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    for r in rows:
        print(r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
