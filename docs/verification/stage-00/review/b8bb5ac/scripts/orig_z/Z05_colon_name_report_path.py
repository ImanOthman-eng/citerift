"""Z-05 (edge variant of Y-01): gitutil.is_tracked passes the path to `git ls-files --error-unmatch -- PATH` as a
pathspec, so a tracked file whose name starts with ':' (pathspec magic) is reported as untracked and the report path
is left out of the dirty check. Tiny project: tests are parametrized from a tracked data file ':cases.json'; the
file is cut to one case, the run writes its report over it, the file is restored with git checkout."""
import json, os, shutil, subprocess, sys
from pathlib import Path
W = Path(os.environ["W"]); BASE = W / "base"; PY = str(BASE / ".venv/bin/python"); sys.path.insert(0, str(BASE / "src"))
from citerift.governance import evidence  # noqa: E402
ENV = {**os.environ, "GIT_AUTHOR_NAME": "r", "GIT_AUTHOR_EMAIL": "r@x", "GIT_COMMITTER_NAME": "r", "GIT_COMMITTER_EMAIL": "r@x",
       "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}
d = W / "sandbox-Z05"; shutil.rmtree(d, ignore_errors=True); (d / "tests").mkdir(parents=True)
def g(*a): return subprocess.run(["git", "-C", str(d), *a], capture_output=True, text=True, env=ENV, check=True).stdout
(d / "pyproject.toml").write_text('[tool.pytest.ini_options]\ntestpaths = ["tests"]\naddopts = ["-p", "citerift.governance.pytest_report", "--strict-markers"]\n')
(d / ":cases.json").write_text(json.dumps([1, 2, 3, 4, 5, 6, 7, 8]))
(d / "tests/test_cases.py").write_text('import json\nfrom pathlib import Path\nimport pytest\n\n'
    'CASES = json.loads((Path(__file__).parents[1] / ":cases.json").read_text())\n\n\n'
    '@pytest.mark.unit\n@pytest.mark.parametrize("n", CASES)\ndef test_case(n):\n    assert n > 0\n')
(d / ".gitignore").write_text("__pycache__/\n")
g("init", "-q"); g("add", "-A"); g("commit", "-qm", "t")
print("tracked:", g("ls-files").split())
(d / ":cases.json").write_text(json.dumps([1]))
print("git status before the run:", g("status", "--porcelain").strip())
r = subprocess.run([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--citerift-report", ":cases.json"], cwd=d,
                   capture_output=True, text=True, env={**ENV, "PYTHONPATH": str(BASE / "src")})
print(r.stdout.strip().splitlines()[-1])
shutil.copy(d / ":cases.json", d.parent / "z05-report.json"); g("checkout", "-q", "--", ":(literal):cases.json")
shutil.copy(d.parent / "z05-report.json", d / "report.json")
rep = json.loads((d / "report.json").read_text())
print({k: rep[k] for k in ("dirty", "dirty_paths", "collected", "totals")}, "complete:", rep["selection"]["complete"])
print("check_test_report problems:", [p.code for p in evidence.check_test_report(d, "report.json", None, g("rev-parse", "HEAD").strip(), ["unit"])])
print("control: the same run with the report over a normal tracked name would be TEST_EVIDENCE_DIRTY (see confirm_pytest_tiny.py, Y-01 case)")
