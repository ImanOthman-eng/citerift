"""Cost of the content check on the repository (clone at b8bb5ac): time of gitutil._content_changed and of
dirty_paths, number of dirty_paths calls made by one `check`, and wall time of `check` at 97b2051 vs b8bb5ac."""
import os, subprocess, sys, time
from pathlib import Path
W = Path(os.environ["W"]); BASE = W / "base"; sys.path.insert(0, str(BASE / "src"))
from citerift.governance import gitutil, orchestrator  # noqa: E402
def t(f, n=5):
    best = 1e9
    for _ in range(n):
        s = time.perf_counter(); f(); best = min(best, time.perf_counter() - s)
    return best
files = gitutil._git(BASE, "ls-files", "-z").stdout.split("\0")
print("tracked files:", len([f for f in files if f]), "bytes:", sum((BASE / f).stat().st_size for f in files if f))
print(f"_content_changed best of 5: {t(lambda: gitutil._content_changed(BASE))*1000:.1f} ms")
print(f"dirty_paths best of 5: {t(lambda: gitutil.dirty_paths(BASE))*1000:.1f} ms")
calls = 0; orig = gitutil.dirty_paths
def counting(*a, **k):
    global calls; calls += 1; return orig(*a, **k)
gitutil.dirty_paths = counting
orchestrator.Orchestrator(BASE).check()
print("dirty_paths calls in one check():", calls)
gitutil.dirty_paths = orig
PY = str(BASE / ".venv/bin/python")
for label, root in (("97b2051", W / "sandbox-old"), ("b8bb5ac", BASE)):
    def run(): subprocess.run([PY, "-P", "-m", "citerift.governance.cli", "check"], cwd=root, env={**os.environ, "PYTHONPATH": str(root / "src")}, capture_output=True, check=True)
    print(f"check wall time at {label}, best of 5: {t(run):.2f} s")
