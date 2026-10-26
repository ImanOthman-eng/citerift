"""Run mutants M87 and M91..M96 of docs/verification/stage-00/mutation/mutation_check.py in a clone ($W/sandbox-mut),
with the harness's own suite command (uv run --no-sync pytest -q -x -p no:cacheprovider tests/stage00) and its own
pattern rules. Each mutated file is restored afterwards; the clone's tree must be clean at the end."""
import importlib.util, os, subprocess, sys
from pathlib import Path
R = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("mc", R / "docs/verification/stage-00/mutation/mutation_check.py")
mc = importlib.util.module_from_spec(spec); spec.loader.exec_module(mc)
assert mc.R == R, (mc.R, R)
want = {"M87", "M91", "M92", "M93", "M94", "M95", "M96"}
sel = [m for m in mc.M if m[0].split()[0] in want]
print("selected:", [m[0].split()[0] for m in sel], flush=True)
for name, rel, old, new in sel:
    path = R / rel; orig = path.read_text(encoding="utf-8")
    pairs = list(zip(old, new, strict=True)) if isinstance(old, tuple) else [(old, new)]
    counts = [orig.count(o) for o, _ in pairs]
    if counts != [1] * len(pairs):
        print(f"{name}: PATTERN FOUND {counts} TIMES", flush=True); continue
    mutated = orig
    for o, n in pairs: mutated = mutated.replace(o, n, 1)
    path.write_text(mutated, encoding="utf-8")
    try:
        r = mc._suite()
        failed = [l for l in r.stdout.splitlines() if l.startswith("FAILED") or l.startswith("ERROR")]
        last = [l for l in r.stdout.splitlines() if "passed" in l or "failed" in l][-1:]
        print(f"{name}: {'KILLED' if r.returncode != 0 else 'SURVIVED'} {last} {failed[:1]}", flush=True)
    finally:
        path.write_text(orig, encoding="utf-8")
print("git status --porcelain after the mutants:", repr(subprocess.run(["git", "-C", str(R), "status", "--porcelain"], capture_output=True, text=True).stdout))
