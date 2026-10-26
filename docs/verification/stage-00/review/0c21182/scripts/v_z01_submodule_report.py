"""Z-01 variant, end to end: a committed test imports a helper from a submodule. The helper is edited so the test's
check passes trivially, and a local setting (submodule.<name>.ignore=all or diff.ignoreSubmodules=all) hides the edit.
Does the report of the run say clean, and does check_test_report accept it? Control: the same edit without the setting."""
import json, os, shutil, subprocess, sys
from pathlib import Path
W = Path(os.environ["W"]); BASE = Path(os.environ["BASE"]); PY = str(BASE / ".venv/bin/python"); sys.path.insert(0, str(BASE / "src"))
from citerift.governance import evidence  # noqa: E402
ENV = {**os.environ, "GIT_AUTHOR_NAME": "r", "GIT_AUTHOR_EMAIL": "r@x", "GIT_COMMITTER_NAME": "r", "GIT_COMMITTER_EMAIL": "r@x",
       "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}
TOP = W / "sandbox-vZ01sub"; shutil.rmtree(TOP, ignore_errors=True); TOP.mkdir()
def g(d, *a): return subprocess.run(["git", "-C", str(d), *a], capture_output=True, text=True, env=ENV, check=True).stdout
lib = TOP / "helperlib"; lib.mkdir(); (lib / "helper.py").write_text("def is_valid(n):\n    return n % 2 == 0\n")
g(lib, "init", "-q"); g(lib, "add", "-A"); g(lib, "commit", "-qm", "lib")
def project(name):
    d = TOP / name; (d / "tests").mkdir(parents=True)
    (d / ".gitattributes").write_text("* text=auto eol=lf\n"); (d / ".gitignore").write_text("__pycache__/\nreport.json\n")
    (d / "pyproject.toml").write_text('[tool.pytest.ini_options]\ntestpaths = ["tests"]\naddopts = ["-p", "citerift.governance.pytest_report", "--strict-markers"]\n')
    (d / "tests/test_h.py").write_text('import sys\nfrom pathlib import Path\nsys.path.insert(0, str(Path(__file__).parents[1] / "vendor"))\n'
        'import helper\nimport pytest\n\n\n@pytest.mark.unit\n@pytest.mark.parametrize("n", [1, 3])\ndef test_odd_is_invalid(n):\n    assert not helper.is_valid(n)\n')
    g(d, "init", "-q"); g(d, "-c", "protocol.file.allow=always", "submodule", "add", "-q", str(lib), "vendor"); g(d, "add", "-A"); g(d, "commit", "-qm", "t")
    (d / "vendor/helper.py").write_text("def is_valid(n):\n    return False\n")
    return d
for label, setting in (("control, no setting", None), ("submodule.vendor.ignore=all", ("submodule.vendor.ignore", "all")),
                       ("diff.ignoreSubmodules=all", ("diff.ignoreSubmodules", "all"))):
    d = project(label.split(",")[0].replace(" ", "_").replace("=", "_"))
    if setting: g(d, "config", *setting)
    r = subprocess.run([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--citerift-report", "report.json"], cwd=d,
                       capture_output=True, text=True, env={**ENV, "PYTHONPATH": str(BASE / "src")})
    rep = json.loads((d / "report.json").read_text())
    probs = [p.code for p in evidence.check_test_report(d, "report.json", None, g(d, "rev-parse", "HEAD").strip(), ["unit"])]
    print(f"{label}: git status {g(d, 'status', '--porcelain').strip()!r}; pytest: {r.stdout.strip().splitlines()[-1]}; "
          f"dirty={rep['dirty']} dirty_paths={rep['dirty_paths']} complete={rep['selection']['complete']}; check_test_report problems: {probs}")
