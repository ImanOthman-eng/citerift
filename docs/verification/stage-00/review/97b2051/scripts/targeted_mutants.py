"""Run selected mutants of docs/verification/stage-00/mutation/mutation_check.py in a throwaway clone
($W/sandbox-mut), each against a targeted subset of the suite (-x). A mutant killed by a subset is killed by the
full suite too. Survivors of the subset are re-run against the full suite. Usage: targeted_mutants.py M26 M35 ..."""
import importlib.util, os, subprocess, sys
from pathlib import Path
W = Path(os.environ["W"]); R = W / "sandbox-mut"
if not R.exists():
    subprocess.run(["git", "clone", "-q", str(W / "base"), str(R)], check=True)
PY = str(W / "base/.venv/bin/python")
spec = importlib.util.spec_from_file_location("mc", R / "docs/verification/stage-00/mutation/mutation_check.py")
mc = importlib.util.module_from_spec(spec); spec.loader.exec_module(mc)
want = set(sys.argv[1:])
SUBSET = ["tests/stage00/test_corrections.py", "tests/stage00/test_contracts.py",
          "tests/stage00/test_unit_model_evidence_memory.py"]
env = {**os.environ, "PYTHONPATH": str(R / "src")}
def suite(paths):
    return subprocess.run([PY, "-P", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", *paths], cwd=R,
                          capture_output=True, text=True, env=env, timeout=1800)
base = suite(["tests/stage00/test_cli.py"])
print("baseline subset (test_cli) exit", base.returncode, flush=True)
for name, rel, old, new in mc.M:
    if name.split()[0] not in want:
        continue
    path = R / rel; orig = path.read_text(encoding="utf-8")
    pairs = list(zip(old, new, strict=True)) if isinstance(old, tuple) else [(old, new)]
    counts = [orig.count(o) for o, _ in pairs]
    if counts != [1] * len(pairs):
        print(name, "PATTERN COUNT", counts, flush=True); continue
    m = orig
    for o, n in pairs:
        m = m.replace(o, n, 1)
    path.write_text(m, encoding="utf-8")
    try:
        r = suite(SUBSET); scope = "subset"
        if r.returncode == 0:
            r = suite(["tests/stage00"]); scope = "full suite"
        last = [l for l in r.stdout.splitlines() if " passed" in l or " failed" in l][-1:]
        failed = [l for l in r.stdout.splitlines() if l.startswith("FAILED")][:1]
        print(f"{name}: {'KILLED' if r.returncode else 'SURVIVED'} ({scope}) {last} {failed}", flush=True)
    finally:
        path.write_text(orig, encoding="utf-8")
print("tree after:", subprocess.run(["git", "-C", str(R), "status", "--porcelain"], capture_output=True, text=True).stdout or "clean")
