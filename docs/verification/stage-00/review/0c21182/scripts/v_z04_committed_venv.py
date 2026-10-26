"""Z-04 variant: code that runs before the governance step without pyproject.toml. A committed .venv (force-added
past .gitignore) whose bin/python is a wrapper script. The wrapper rewrites the checker the first time it runs, then
hands over to the real interpreter. CI steps replayed in the order of b8bb5ac (guard, dependency-only sync, check),
offline, in a throwaway clone. The registry gets the same hand edit as the Z-04 script (honest check: 5 errors)."""
import os, subprocess, sys
from pathlib import Path
from lib import BASE, clone_base
repo = clone_base("vZ04venv")
real = os.path.realpath(BASE / ".venv/bin/python")
cfg = (BASE / ".venv/pyvenv.cfg").read_text()
venv = repo / ".venv"; (venv / "bin").mkdir(parents=True)
(venv / "pyvenv.cfg").write_text(cfg)
WRAP = f'''#!/bin/sh
cli="$(dirname "$0")/../../src/citerift/governance/cli.py"
echo "wrapper ran: $*" >> "$(dirname "$0")/../../wrapper-ran.log"
if ! grep -q REWRITTEN "$cli"; then
  {real} - "$cli" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); t = p.read_text()
p.write_text(t.replace("def cmd_check(orc: Orchestrator, args: argparse.Namespace) -> int:\\n",
  "def cmd_check(orc: Orchestrator, args: argparse.Namespace) -> int:\\n    print('Consistency check: 0 errors, 0 warnings')  # REWRITTEN\\n    return 0\\n", 1))
PY
fi
exec {real} "$@"
'''
(venv / "bin/python").write_text(WRAP); os.chmod(venv / "bin/python", 0o755)
os.symlink("python", venv / "bin/python3")
reg = (repo / "governance/stage_registry.json").read_text()
(repo / "governance/stage_registry.json").write_text(reg.replace('"status": "IN_PROGRESS"', '"status": "ACCEPTED_CLOSED"', 1))
env = {**os.environ, "GIT_AUTHOR_NAME": "r", "GIT_AUTHOR_EMAIL": "r@x.invalid", "GIT_COMMITTER_NAME": "r", "GIT_COMMITTER_EMAIL": "r@x.invalid"}
subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
subprocess.run(["git", "-C", str(repo), "add", "-f", ".venv/pyvenv.cfg", ".venv/bin/python", ".venv/bin/python3"], check=True)
subprocess.run(["git", "-C", str(repo), "commit", "-qm", "committed .venv + hand edit"], check=True, env=env)
print("committed under .venv:", subprocess.run(["git", "-C", str(repo), "ls-files", ".venv"], capture_output=True, text=True).stdout.split())
def sh(name, cmd):
    r = subprocess.run(cmd, cwd=repo, capture_output=True, text=True, env={**env, "PYTHONPATH": "src", "UV_PYTHON": "3.12"}, shell=isinstance(cmd, str))
    out = [l for l in (r.stdout + r.stderr).splitlines() if "UV_NATIVE_TLS" not in l]
    print(f"[{name}] exit {r.returncode}:", " / ".join(out[-3:])[:300]); return r
honest = subprocess.run([str(BASE / ".venv/bin/python"), "-P", "-m", "citerift.governance.cli", "check"], cwd=repo, capture_output=True, text=True,
                        env={**env, "PYTHONPATH": str(BASE / "src")})
print("honest checker on this commit:", honest.stdout.splitlines()[0])
sh("guard", 'test "$(ls -A src)" = "citerift"')
sh("uv sync --frozen --no-install-project --no-build (offline)", ["uv", "sync", "--frozen", "--no-install-project", "--no-build", "--offline"])
log = repo / "wrapper-ran.log"
print("wrapper ran during the sync:", log.read_text().strip().splitlines() if log.exists() else "no")
print(".venv/bin/python is still the wrapper:", "REWRITTEN" in (venv / "bin/python").read_text() if (venv / "bin/python").exists() else "missing")
print("git status after the dependency install:", subprocess.run(["git", "-C", str(repo), "status", "--porcelain"], capture_output=True, text=True).stdout.strip() or "clean")
sh("governance check", ["uv", "run", "--no-sync", "python", "-P", "-m", "citerift.governance.cli", "check"])
print("wrapper log now:", log.read_text().strip().splitlines() if log.exists() else "no")
print("git status after the check:", subprocess.run(["git", "-C", str(repo), "status", "--porcelain"], capture_output=True, text=True).stdout.strip() or "clean")
