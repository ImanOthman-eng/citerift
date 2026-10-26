# ruff: noqa: E501  (mutation patterns must match source lines exactly)
"""Stage 00 mutation check: each mutant disables one safety rule; the test suite must fail.

Run from a clean checkout: python docs/verification/stage-00/mutation/mutation_check.py
Every file is restored after its mutant runs.
"""

import pathlib
import subprocess

R = pathlib.Path(__file__).resolve().parents[4]
M = [
    ("M1 single-active rule disabled", "src/citerift/governance/orchestrator.py", "if len(active) > 1:", "if False:"),
    (
        "M2 owner-only edge check disabled",
        "src/citerift/governance/orchestrator.py",
        '            if actor != Actor.OWNER:\n                problems.append(\n                    (\n                        "OWNER_DECISION_REQUIRED"',
        '            if False:\n                problems.append(\n                    (\n                        "OWNER_DECISION_REQUIRED"',
    ),
    (
        "M3 absence-of-record must be uncertain (schema)",
        "schemas/contracts/v1/investigation.schema.json",
        '"then": {"properties": {"status": {"const": "uncertain"}',
        '"then": {"properties": {"status": {}',
    ),
    (
        "M4 test report revision check disabled",
        "src/citerift/governance/evidence.py",
        'if report.get("revision") != revision:',
        "if False:",
    ),
    (
        "M5 drift detection disabled",
        "src/citerift/governance/orchestrator.py",
        "if last is None:\n            return []",
        "if True:\n            return []",
    ),
    (
        "M6 history replay conflict disabled",
        "src/citerift/governance/orchestrator.py",
        'if replay[s["id"]] != s["status"]:',
        "if False:",
    ),
    (
        "M7 evidence hash check disabled",
        "src/citerift/governance/evidence.py",
        'if expected_sha is not None and sha256_file(path) != expected_sha:\n        problems.append(\n            Problem(\n                "EVIDENCE_STALE"',
        'if False:\n        problems.append(\n            Problem(\n                "EVIDENCE_STALE"',
    ),
    (
        "M8 dependency check disabled",
        "src/citerift/governance/orchestrator.py",
        'for d in self.dependencies(s["id"])["unsatisfied"]:\n                severity',
        "for d in []:\n                severity",
    ),
    (
        "M9 acceptance-of-other-revision check disabled",
        "src/citerift/governance/orchestrator.py",
        'if acc["accepted_revision"] != ver["revision"]:',
        "if False:",
    ),
]
for name, rel, old, new in M:
    path = R / rel
    orig = path.read_text()
    if old not in orig:
        print(name, "PATTERN NOT FOUND")
        continue
    path.write_text(orig.replace(old, new, 1))
    try:
        r = subprocess.run(
            ["uv", "run", "--no-sync", "pytest", "-q", "-x", "-p", "no:cacheprovider", "tests/stage00"],  # noqa: S607
            cwd=R,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        last = [line for line in r.stdout.splitlines() if "passed" in line or "failed" in line][-1:]
        print(f"{name}: {'KILLED' if r.returncode else 'SURVIVED'} {last}")
    finally:
        path.write_text(orig)
