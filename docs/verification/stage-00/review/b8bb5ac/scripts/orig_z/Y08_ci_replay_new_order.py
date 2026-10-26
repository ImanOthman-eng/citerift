"""Y-08 at 97b2051: replay the CI steps of .github/workflows/ci.yml in their new order in clones (no network).
A) the original attack (mypy plugin rewrites cmd_check; registry broken by hand): the governance step now runs first.
B) the documented residual (R-016): the same kind of plugin targets the later steps instead. It writes an untracked
   src/sitecustomize.py that makes check_test_report return no problems, and pyproject.toml narrows pytest with -k.
C) the tree-check step compares the working tree with the index only: a tool that rewrites a tracked file and
   stages it passes `git diff --exit-code`."""
import subprocess
from lib import BASE, clone_base
VPY = str(BASE / ".venv/bin/python"); MYPY = str(BASE / ".venv/bin/mypy"); RUFF = str(BASE / ".venv/bin/ruff")
ENV = {"PYTHONPATH": "src", "GIT_AUTHOR_NAME": "r", "GIT_AUTHOR_EMAIL": "r@x.invalid", "GIT_COMMITTER_NAME": "r", "GIT_COMMITTER_EMAIL": "r@x.invalid"}
import os
def sh(cmd, repo): return subprocess.run(cmd, cwd=repo, capture_output=True, text=True, env={**os.environ, **ENV}, shell=isinstance(cmd, str))
STEPS = [
    ("guard: nothing beside citerift in src", 'test "$(ls -A src)" = "citerift"'),
    ("governance check", [VPY, "-P", "-m", "citerift.governance.cli", "check"]),
    ("render-status --check", [VPY, "-P", "-m", "citerift.governance.cli", "render-status", "--check"]),
    ("ruff check", [RUFF, "check", "."]),
    ("ruff format --check", [RUFF, "format", "--check", "."]),
    ("mypy", [MYPY]),
    ("pytest", [VPY, "-P", "-m", "pytest", "--citerift-report", "ci-test-report.json", "-q", "-p", "no:cacheprovider"]),
    ("check-report", [VPY, "-P", "-m", "citerift.governance.cli", "check-report", "ci-test-report.json"]),
    ("git diff --exit-code", "git diff --exit-code"),
]
def replay(repo, label):
    print(f"== {label}")
    for name, cmd in STEPS:
        r = sh(cmd, repo)
        tail = (r.stdout.strip().splitlines() or r.stderr.strip().splitlines() or [""])[-1][:140]
        print(f"   {name}: exit {r.returncode} | {tail}")
        if r.returncode != 0:
            print("   -> CI stops here (red)"); return
    print("   -> CI green")
def commit(repo, msg):
    sh([RUFF, "check", "--fix", "-q", "ci_mypy_plugin.py"], repo); sh([RUFF, "format", "-q", "ci_mypy_plugin.py"], repo)
    sh(["git", "add", "-A"], repo); sh(["git", "commit", "-qm", msg], repo)

# A
repo = clone_base("Y08A")
(repo / "ci_mypy_plugin.py").write_text('''
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
''')
py = (repo / "pyproject.toml").read_text()
(repo / "pyproject.toml").write_text(py.replace('files = ["src"]\n', 'files = ["src"]\nplugins = ["ci_mypy_plugin.py"]\n'))
reg = (repo / "governance/stage_registry.json").read_text()
(repo / "governance/stage_registry.json").write_text(reg.replace('"status": "IN_PROGRESS"', '"status": "ACCEPTED_CLOSED"', 1))
commit(repo, "A")
replay(repo, "A original attack, new step order")

# B
repo = clone_base("Y08B")
(repo / "ci_mypy_plugin.py").write_text('''
from pathlib import Path
from mypy.plugin import Plugin
(Path(__file__).parent / "src/sitecustomize.py").write_text(
    "from citerift.governance import evidence\\n"
    "evidence.check_test_report = lambda *a, **k: []\\n")
def plugin(version: str) -> type[Plugin]:
    return Plugin
''')
py = (repo / "pyproject.toml").read_text()
py = py.replace('files = ["src"]\n', 'files = ["src"]\nplugins = ["ci_mypy_plugin.py"]\n')
assert "addopts = [" in py
py = py.replace("addopts = [", 'addopts = ["-k", "test_read_only_commands", ', 1)
(repo / "pyproject.toml").write_text(py)
commit(repo, "B")
replay(repo, "B residual: later steps changed, run narrowed to one test")
print("   untracked after the run:", sh(["git", "status", "--porcelain"], repo).stdout.split())

# C
repo = clone_base("Y08C")
(repo / "ci_mypy_plugin.py").write_text('''
import subprocess
from pathlib import Path
from mypy.plugin import Plugin
root = Path(__file__).parent
p = root / "src/citerift/governance/evidence.py"
t = p.read_text()
if "STAGED" not in t:
    p.write_text(t + "\\n# STAGED rewrite\\n")
    subprocess.run(["git", "-C", str(root), "add", str(p)], check=True)
def plugin(version: str) -> type[Plugin]:
    return Plugin
''')
py = (repo / "pyproject.toml").read_text()
py = py.replace('files = ["src"]\n', 'files = ["src"]\nplugins = ["ci_mypy_plugin.py"]\n')
py = py.replace("addopts = [", 'addopts = ["-k", "test_read_only_commands", ', 1)
(repo / "pyproject.toml").write_text(py)
commit(repo, "C")
STEPS_C = [s for s in STEPS if s[0] in ("mypy", "git diff --exit-code")]
print("== C staged rewrite of a tracked owned file")
for name, cmd in STEPS_C:
    r = sh(cmd, repo); print(f"   {name}: exit {r.returncode}")
print("   git status --porcelain:", sh(["git", "status", "--porcelain"], repo).stdout.strip())
