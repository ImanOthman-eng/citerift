"""Z-01 (variant of Y-02) on a clone of the reviewed revision: every committed test file is cut down to its first two
test functions by renaming 'def test_' to 'def xest_' (same length), the files' mtimes are restored, and
core.trustctime=false is set in .git/config. git status shows nothing, no file is flagged skip-worktree or
assume-unchanged, and the report of the narrowed run is accepted by check_test_report as clean and complete."""
import json, os, re, subprocess, sys, time
from lib import BASE, PY, clone_base, run
repo = clone_base("Z01")
def g(*a): return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, check=True).stdout
tests = sorted((repo / "tests").rglob("test_*.py"))
old = time.time_ns() - 3600 * 10**9
for f in tests: os.utime(f, ns=(old, old))
g("update-index", "--refresh"); time.sleep(1.1)
g("config", "core.trustctime", "false")
for f in tests:
    st = f.stat(); text = f.read_text(encoding="utf-8"); seen = 0
    def keep_two(m):
        global seen
        seen += 1
        return m.group(0) if seen <= 2 else m.group(1) + " xest_"
    new = re.sub(r"^(def) test_", keep_two, text, flags=re.M)
    assert len(new.encode()) == len(text.encode())
    with open(f, "r+", encoding="utf-8") as fh: fh.write(new)
    os.utime(f, ns=(st.st_atime_ns, st.st_mtime_ns))
print("content differs from HEAD in", sum(g("hash-object", str(f)).strip() != g("rev-parse", f"HEAD:{f.relative_to(repo)}").strip() for f in tests), "of", len(tests), "test files")
print("git status --porcelain:", repr(g("status", "--porcelain")))
print("flagged files (ls-files -v, lowercase or S):", [l for l in g("ls-files", "-v").splitlines() if l[0].islower() or l[0] == "S"])
out = run([PY, "-P", "-m", "pytest", "-q", "-p", "no:cacheprovider", "--citerift-report", "report.json"], cwd=repo,
          env={"PYTHONPATH": str(repo / "src")})
print(out.stdout.strip().splitlines()[-1])
rep = json.loads((repo / "report.json").read_text())
print({k: rep[k] for k in ("revision", "dirty", "dirty_paths", "exit_status", "collected", "totals")}, "complete:", rep["selection"]["complete"])
sys.path.insert(0, str(repo / "src"))
from citerift.governance import evidence  # noqa: E402
head = g("rev-parse", "HEAD").strip()
suites = ["unit", "integration", "negative", "regression", "reproducibility", "security", "contracts", "simulation"]
print("check_test_report problems:", [(p.code, p.message[:100]) for p in evidence.check_test_report(repo, "report.json", None, head, suites)])
c = run([PY, "-P", "-m", "citerift.governance.cli", "check-report", "report.json"], cwd=repo, env={"PYTHONPATH": str(repo / "src")})
print("citerift-gov check-report:", c.returncode, c.stdout.strip().splitlines()[-1])
