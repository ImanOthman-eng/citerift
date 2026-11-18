"""Stage 04 Step 12: ``VALIDATION.json``, the measured validation summary that the freeze manifest records.

Run from the repository root after the freeze evidence is committed:

    uv run python -P docs/verification/stage-04/freeze/build_validation.py

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
CODE_REVISION = "3eec84f63467192407934dda2de544338a5d9140"

# Test runs of the code revision above (the freeze evidence was produced from it); the freeze-content commit's own
# CI run is named by the attestation commit.
TESTS: dict[str, Any] = {
    "code_revision": CODE_REVISION,
    "local": {
        "python": "3.12.3",
        "passed": 3249,
        "skipped": 0,
        "failed": 0,
        "wall": "18 min 48 s",
        "note": "full suite in this 4-vCPU container, before the evidence runs",
    },
    "ci": {
        "run_id": 44179654515,
        "run_number": 337,
        "conclusion": "success",
        "jobs": {
            "verify (python 3.12)": {
                "python": "3.12.3",
                "passed": 3249,
                "test_step": "19 min 34 s",
                "pytest_reported": "1173.38 s",
                "job": "19 min 56 s",
                "check_report": "0 problems",
            },
            "verify (python 3.13)": {
                "python": "3.13.14",
                "passed": 3249,
                "test_step": "11 min 30 s",
                "pytest_reported": "689.21 s",
                "job": "11 min 53 s",
                "check_report": "0 problems",
            },
            "ci-gate": {"conclusion": "success"},
        },
        "clean_tree": True,
        "pip_audit_strict": "no known vulnerabilities",
    },
}

# GitHub-hosted runner times of the Step 12 runs (OD-S12-2: 18 minutes is diagnostic, 30 minutes the hard timeout).
CI_RUNTIME = [
    {"run": 332, "commit": "9499c49", "py312_tests": "10m16s", "py313_tests": "11m29s", "result": "success"},
    {"run": 333, "commit": "75e7b26", "py312_tests": "19m53s", "py313_tests": "17m07s", "result": "cancelled (20 min)"},
    {"run": 334, "commit": "00c2d6c", "py312_tests": "19m40s", "py313_tests": "11m28s", "result": "cancelled (20 min)"},
    {"run": 335, "commit": "91c70af", "py312_tests": "13m59s", "py313_tests": "10m06s", "result": "success"},
    {"run": 336, "commit": "c23e5dc", "py312_tests": "12m32s", "py313_tests": "18m03s", "result": "success"},
    {"run": 337, "commit": "3eec84f", "py312_tests": "19m34s", "py313_tests": "11m30s", "result": "success"},
]
CI_RUNTIME_FINDING = (
    "Runs over 18 minutes alternate between the Python versions on the same code (run 336: 3.13 slow, 3.12 fast; run "
    "337: 3.12 slow, 3.13 fast). In run 337 the untouched Stage 00-03 test files ran a median 1.46x slower on 3.12 "
    "than in run 335 and the Stage 04 files 1.44x; Python 3.13 per-file times equal run 334 (median 1.00x). Recorded "
    "as GitHub-hosted runner variance under OD-S12-2; no required job reached 30 minutes."
)


def load(rel: str) -> Any:
    return json.loads((S04 / rel).read_text(encoding="utf-8"))


def main() -> int:
    vs = load("freeze/vertical-slice/vertical_slice.json")
    step11 = load("evidence/vertical-slice/results/vertical_slice.json")
    perf = load("freeze/performance/perf_breakdown.json")
    comp = load("freeze/performance/verification_components.json")
    d062 = load("freeze/d062/two_build_equivalence.json")
    tamper = load("freeze/d062/tamper_differential.json")
    rows = []
    for case, c in vs["cases"].items():
        p = c["perf"]["wall_s"]
        old = step11["cases"][case]["perf"]["wall_s"]
        rows.append(
            {
                "case": case,
                "n": p["n"],
                "run_median_s": p["median"],
                "run_p95_s": p["p95"],
                "step11_run_p95_s": old["p95"],
                "replay_p95_s": c["perf"]["replay_wall_s"]["p95"],
                "meets_target": p["p95"] <= TARGET_S,
            }
        )
    out = {
        "label": "Stage 04 Step 12 validation summary (freeze); measured, not an evaluation",
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
