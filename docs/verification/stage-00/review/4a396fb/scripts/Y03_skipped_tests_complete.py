"""Y-03: completeness covers selection, not execution. A committed conftest that marks all but one
test per suite as skipped (no report forging, no plugin state touched) gives a report with
complete=true, and check_test_report() accepts it: skipped and xfailed outcomes are never counted
against the evidence. Only one passed test per required suite is needed."""
import json
import subprocess
import sys

from lib import PY, clone_base, run

repo = clone_base("Y03")
(repo / "tests" / "conftest.py").write_text('''
import pytest

SUITES = ("unit", "integration", "negative", "regression", "reproducibility", "security", "contracts", "simulation")


def pytest_collection_modifyitems(config, items):
    kept = set()
    for item in items:
        suites = {s for s in SUITES if item.get_closest_marker(s)}
        if suites - kept:
            kept |= suites
            continue
        item.add_marker(pytest.mark.skip(reason="temporarily skipped"))
''')
env = {"GIT_AUTHOR_NAME": "r", "GIT_AUTHOR_EMAIL": "r@x.invalid", "GIT_COMMITTER_NAME": "r", "GIT_COMMITTER_EMAIL": "r@x.invalid"}
subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
subprocess.run(["git", "-C", str(repo), "commit", "-qm", "skip most tests"], check=True, env={**__import__("os").environ, **env})
out = run([PY, "-P", "-m", "pytest", "-q", "-p", "no:cacheprovider", "--citerift-report", "report.json"], cwd=repo,
          env={"PYTHONPATH": str(repo / "src")})
print(out.stdout.strip().splitlines()[-1])
report = json.loads((repo / "report.json").read_text())
print({k: report[k] for k in ("dirty", "exit_status", "collected", "totals")}, "complete:", report["selection"]["complete"])
sys.path.insert(0, str(repo / "src"))
from citerift.governance import evidence  # noqa: E402

head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
suites = ["unit", "integration", "negative", "regression", "reproducibility", "security", "contracts", "simulation"]
print("check_test_report problems:", [p.code for p in evidence.check_test_report(repo, "report.json", None, head, suites)])
