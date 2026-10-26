"""Y-02 (also confirmed for `git update-index --assume-unchanged` in a tiny repository): the plugin decides "clean tree" with `git status`, which does not show tracked files
flagged skip-worktree (or assume-unchanged). Modify the committed tests so that only a few tests
per file are collected, hide the edits with `git update-index --skip-worktree`, run the suite
exactly as CI does, and the report says revision=HEAD, dirty=false, complete=true.
check_test_report() then accepts it as the stage's test evidence."""
import json
import re
import subprocess
from pathlib import Path

from lib import BASE, PY, clone_base, run

repo = clone_base("Y02")
tests = sorted((repo / "tests").rglob("test_*.py"))
pattern = re.compile(r"^(def|async def) test_", re.M)
for f in tests:
    text = f.read_text(encoding="utf-8")
    seen = 0

    def keep_two(m: re.Match[str]) -> str:
        global seen
        seen += 1
        return m.group(0) if seen <= 2 else m.group(1) + " disabled_"

    f.write_text(pattern.sub(keep_two, text), encoding="utf-8")
rels = [str(f.relative_to(repo)) for f in tests]
print("git status before hiding:", subprocess.run(["git", "-C", str(repo), "status", "--porcelain"],
                                                  capture_output=True, text=True).stdout.count("\n"), "changed files")
subprocess.run(["git", "-C", str(repo), "update-index", "--skip-worktree", *rels], check=True)
print("git status after hiding:", repr(subprocess.run(["git", "-C", str(repo), "status", "--porcelain"],
                                                    capture_output=True, text=True).stdout))
out = run([PY, "-P", "-m", "pytest", "-q", "--citerift-report", "report.json"], cwd=repo,
          env={"PYTHONPATH": str(repo / "src")})
print(out.stdout.strip().splitlines()[-1])
report = json.loads((repo / "report.json").read_text())
sel = report["selection"]
print({k: report[k] for k in ("revision", "dirty", "exit_status", "collected", "totals")})
print({k: sel[k] for k in ("complete", "deselected", "dropped", "repeated")}, "files:", len(sel["files"]))
head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
import sys
sys.path.insert(0, str(repo / "src"))
from citerift.governance import evidence  # noqa: E402

suites = ["unit", "integration", "negative", "regression", "reproducibility", "security", "contracts", "simulation"]
problems = evidence.check_test_report(repo, "report.json", None, head, suites)
print("check_test_report problems:", [(p.code, p.message[:80]) for p in problems])
