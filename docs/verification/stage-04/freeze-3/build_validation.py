"""Stage 04 final corrective cycle (D-083, item 13): ``VALIDATION.json`` of the freeze-3 candidate, the measured
validation summary that its freeze manifest records (the freeze-2 format, ``../freeze-2/build_validation.py``, kept
unchanged with its freeze; the freeze-2 numbers are the comparison column).

Run from the repository root after the freeze evidence is committed:

    uv run python -P docs/verification/stage-04/freeze-3/build_validation.py

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
CODE_REVISION = "032bbaf434291126976c06ad10d6cddeb90408c6"
# ``src`` and ``schemas`` of CODE_REVISION equal those of every commit the freeze-2 evidence ran from (dfee881 onwards:
# regression, vertical slice, D-062, performance); the later commits change documents and tests only.

# Test runs of the code revision above, after owner decisions D-072 to D-075. The P-listed test that pinned the
# superseded engine was corrected under D-074 (it now verifies the historical freeze from git objects); no test is
# skipped, marked or disabled.
TESTS: dict[str, Any] = {
    "code_revision": CODE_REVISION,
    "local": {
        "python_3_12": {"python": "3.12.3", "passed": 3382, "failed": 0, "skipped": 0, "wall": "22 min 06 s"},
        "python_3_13": {"python": "3.13.18", "passed": 3382, "failed": 0, "skipped": 0, "wall": "20 min 38 s"},
        "note": "full suite in this 4-vCPU container, both versions run at the same time",
    },
    "ci": {
        "run_id": 44483392722,
        "run_number": 364,
        "conclusion": "success",
        "jobs": {
            "verify (python 3.12)": {
                "passed": 3382,
                "failed": 0,
                "pytest_reported": "790.06 s",
                "report": "0 problems",
            },
            "verify (python 3.13)": {
                "passed": 3382,
                "failed": 0,
                "pytest_reported": "1079.54 s",
                "report": "0 problems",
            },
            "ci-gate": {"conclusion": "success"},
        },
        "pip_audit": "No known vulnerabilities found (both jobs)",
    },
    "lint": {
        "ruff_check": "All checks passed!",
        "ruff_format": "623 files already formatted",
        "mypy": "Success: no issues found in 95 source files",
        "check_schemas": "2 schemas checked, 0 problems",
        "step3_docs_check": "RESULT: PASS (0 failed)",
        "citerift_gov_check": "0 errors, 0 warnings",
        "render_status_check": "PROJECT_STATUS.md is up to date",
    },
}

# GitHub-hosted runner times of the corrective-cycle CI runs on code revisions (OD-S12-2: 30 minutes hard timeout).
CI_RUNTIME = [
    {"run": 360, "commit": "99c4194", "py312_tests": "13m29s", "py313_tests": "12m16s", "result": "failure (P test)"},
    {"run": 364, "commit": "032bbaf", "py312_tests": "13m11s", "py313_tests": "18m01s", "result": "success"},
]
CI_RUNTIME_FINDING = "No required job reached 30 minutes (OD-S12-2)."


def load(rel: str) -> Any:
    return json.loads((S04 / rel).read_text(encoding="utf-8"))


def main() -> int:
    vs = load("freeze-3/vertical-slice/vertical_slice.json")
    old_freeze = load("freeze-2/vertical-slice/vertical_slice.json")
    perf = load("freeze-3/performance/perf_breakdown.json")
    comp = load("freeze-3/performance/verification_components.json")
    d062 = load("freeze-3/d062/two_build_equivalence.json")
    tamper = load("freeze-3/d062/tamper_differential.json")
    sizes = load("final-cycle/lows/description_sizes.json")["summary"]
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
                "freeze_2_run_p95_s": old["p95"],
                "replay_p95_s": c["perf"]["replay_wall_s"]["p95"],
                "meets_target": p["p95"] <= TARGET_S,
            }
        )
    out = {
        "label": "Stage 04 final corrective cycle validation summary (freeze-3 candidate); measured, not an evaluation",
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
            "bib1_cpu_s_per_development_page": sizes["bib1_cpu_s_per_page"],
            "bib1_crafted_unit_under_source_bound": sizes["crafted_under_source_bound"],
        },
    }
    (HERE / "VALIDATION.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    for r in rows:
        print(r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
