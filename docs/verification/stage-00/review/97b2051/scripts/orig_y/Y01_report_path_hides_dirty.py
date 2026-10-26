"""Y-01: the plugin leaves the report path out of the dirty check, whatever that path is.
Pointing --citerift-report at a *tracked, modified* file hides that file's modification: here
tests/stage00/test_corrections.py is cut down to two tests, the run writes the report over it,
and the report says dirty=false and complete=true. No git flag or plugin is involved."""
import json
import re
import shutil
import subprocess
import sys

from lib import PY, clone_base, run

repo = clone_base("Y01")
target = "tests/stage00/test_corrections.py"
text = (repo / target).read_text(encoding="utf-8")
seen = 0


def keep_two(m):
    global seen
    seen += 1
    return m.group(0) if seen <= 2 else m.group(1) + " disabled_"


(repo / target).write_text(re.sub(r"^(def) test_", keep_two, text, flags=re.M), encoding="utf-8")
print("git status before the run:", subprocess.run(["git", "-C", str(repo), "status", "--porcelain"],
                                                   capture_output=True, text=True).stdout.strip())
out = run([PY, "-P", "-m", "pytest", "-q", "-p", "no:cacheprovider", "--citerift-report", target], cwd=repo,
          env={"PYTHONPATH": str(repo / "src")})
print(out.stdout.strip().splitlines()[-1])
report = json.loads((repo / target).read_text())
shutil.copy(repo / target, repo.parent / "y02b-report.json")
subprocess.run(["git", "-C", str(repo), "checkout", "-q", "--", target], check=True)
print({k: report[k] for k in ("dirty", "dirty_paths", "exit_status", "collected")}, "complete:", report["selection"]["complete"])
sys.path.insert(0, str(repo / "src"))
from citerift.governance import evidence  # noqa: E402

shutil.copy(repo.parent / "y02b-report.json", repo / "report.json")
head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
suites = ["unit", "integration", "negative", "regression", "reproducibility", "security", "contracts", "simulation"]
print("check_test_report problems:", [p.code for p in evidence.check_test_report(repo, "report.json", None, head, suites)])
