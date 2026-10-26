"""Pytest-report confirmations in a tiny project that uses the reviewed plugin and evidence.check_test_report
(F-07, F-14, V-01, V-16, X-02, X-03, Y-01, Y-02, Y-03), each original attack plus close variants. Every case
starts from a fresh copy of the tiny repository."""
import json, os, shutil, subprocess, sys, time
from pathlib import Path
W = Path(os.environ["W"]); BASE = W / "base"; PY = str(BASE / ".venv/bin/python")
sys.path.insert(0, str(BASE / "src"))
from citerift.governance import evidence  # noqa: E402
ENV = {**os.environ, "GIT_AUTHOR_NAME": "r", "GIT_AUTHOR_EMAIL": "r@x.invalid", "GIT_COMMITTER_NAME": "r",
       "GIT_COMMITTER_EMAIL": "r@x.invalid", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}
TEMPLATE = W / "tiny-template"
def g(d, *a): return subprocess.run(["git", "-C", str(d), *a], capture_output=True, text=True, env=ENV, check=True).stdout
PYPROJECT = ('[tool.pytest.ini_options]\ntestpaths = ["tests"]\nxfail_strict = true\n'
             'addopts = ["-p", "citerift.governance.pytest_report", "--strict-markers"]\n')
def body(n): return "import pytest\n\n" + "".join(f"@pytest.mark.unit\ndef test_{i}():\n    assert True\n\n" for i in range(n))
if TEMPLATE.exists(): shutil.rmtree(TEMPLATE)
(TEMPLATE / "tests").mkdir(parents=True)
(TEMPLATE / "pyproject.toml").write_text(PYPROJECT)
(TEMPLATE / "tests/test_a.py").write_text(body(5)); (TEMPLATE / "tests/test_b.py").write_text(body(5))
(TEMPLATE / ".gitignore").write_text("__pycache__/\n.pytest_cache/\n")
g(TEMPLATE, "init", "-q"); g(TEMPLATE, "add", "-A"); g(TEMPLATE, "commit", "-qm", "tiny")
n = 0
def fresh():
    global n; n += 1
    d = W / f"sandbox-tiny-{n}"
    if d.exists(): shutil.rmtree(d)
    subprocess.run(["git", "clone", "-q", str(TEMPLATE), str(d)], check=True, env=ENV); return d
def commit(d, msg): g(d, "add", "-A"); g(d, "commit", "-qm", msg)
def case(label, prepare=None, args=(), env=None, report="report.json", after=None):
    d = fresh()
    if prepare: prepare(d)
    r = subprocess.run([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--citerift-report", report, *args], cwd=d,
                       capture_output=True, text=True, env={**ENV, "PYTHONPATH": f"{BASE / 'src'}:{d}", **(env or {})})
    if after: after(d)
    rp = d / report if not os.path.isabs(report) else Path(report)
    if not rp.exists():
        print(f"{label}: NO REPORT exit {r.returncode} {r.stdout[-200:]} {r.stderr[-300:]}"); return
    rep = json.loads(rp.read_text())
    rel = "report-copy.json"; shutil.copy(rp, d / rel)
    if after is None and report != "report.json" and not os.path.isabs(report): pass
    head = g(d, "rev-parse", "HEAD").strip()
    probs = sorted({p.code for p in evidence.check_test_report(d, rel, None, head, ["unit"])})
    last = (r.stdout.strip().splitlines() or [""])[-1]
    print(f"{label}: [{last}] dirty={rep['dirty']} complete={rep['selection']['complete']} totals={rep['totals']} -> {probs or 'ACCEPTED'}")

case("control: honest complete run")
case("F-07 path argument tests/test_a.py", args=["tests/test_a.py"])
case("V-01 -o python_files=test_a.py", args=["-o", "python_files=test_a.py"])
def other_ini(d): (d / "other.ini").write_text("[pytest]\ntestpaths = tests\naddopts = -p citerift.governance.pytest_report\npython_files = test_a.py\n"); commit(d, "ini")
case("V-01 -c other.ini (committed)", other_ini, args=["-c", "other.ini"])
def drop(d): (d / "tests/conftest.py").write_text("def pytest_collection_modifyitems(items):\n    del items[1:]\n"); commit(d, "conftest")
case("V-01 committed conftest dropping items", drop)
def cignore(d): (d / "tests/conftest.py").write_text('collect_ignore = ["test_b.py"]\n'); commit(d, "conftest")
case("V-01 committed conftest collect_ignore", cignore)
def pyfunc(d): (d / "pyproject.toml").write_text(PYPROJECT.replace("xfail_strict = true\n", 'xfail_strict = true\npython_functions = ["test_0"]\n')); commit(d, "narrow")
case("X-02 python_functions in pyproject (committed)", pyfunc)
def pyclasses(d): (d / "pyproject.toml").write_text(PYPROJECT.replace("xfail_strict = true\n", 'xfail_strict = true\nnorecursedirs = ["tests"]\n')); commit(d, "narrow")
case("X-02 variant: norecursedirs = [tests] in pyproject", pyclasses)
def pad(d):
    (d / "tests/conftest.py").write_text("def pytest_collection_modifyitems(items):\n    n = len(items)\n    keep = [items[0], items[5]]\n    items[:] = (keep * n)[:n]\n"); commit(d, "pad")
case("X-03 committed conftest padding with repeats", pad)
def plug(d): (d / "plug.py").write_text("def pytest_collection_modifyitems(items):\n    del items[1:]\n"); commit(d, "plug")
case("X-03 -p plug", plug, args=["-p", "plug"])
case("X-03 PYTEST_PLUGINS=plug", plug, env={"PYTEST_PLUGINS": "plug"})
def unc(d): (d / "tests/conftest.py").write_text("def pytest_collection_modifyitems(items):\n    pass\n")
case("X-03 uncommitted (untracked) conftest", unc)
def ign_conf(d):
    (d / ".gitignore").write_text("__pycache__/\ntests/conftest.py\n"); commit(d, "ignore"); (d / "tests/conftest.py").write_text("x = 1\n")
case("X-03 variant: git-ignored conftest", ign_conf)
def nar_b(d): (d / "tests/test_b.py").write_text(body(1))
case("Y-01 report written over the modified tracked test file", nar_b, report="tests/test_b.py",
     after=lambda d: None)
def nar_link(d): (d / "tests/test_b.py").write_text(body(1)); os.symlink("tests/test_b.py", d / "r.json")
case("Y-01 variant: untracked symlink report path to the modified tracked file", nar_link, report="r.json")
def nar_rel(d): (d / "tests/test_b.py").write_text(body(1))
case("Y-01 variant: report path ./tests/../tests/test_b.py", nar_rel, report="./tests/../tests/test_b.py")
def skipw(d): (d / "tests/test_b.py").write_text(body(1)); g(d, "update-index", "--skip-worktree", "tests/test_b.py")
case("Y-02 skip-worktree", skipw)
def assume(d): (d / "tests/test_b.py").write_text(body(1)); g(d, "update-index", "--assume-unchanged", "tests/test_b.py")
case("Y-02 assume-unchanged", assume)
def statcache(d):
    f = d / "tests/test_b.py"; old = time.time_ns() - 3600 * 10**9
    os.utime(f, ns=(old, old)); g(d, "update-index", "--refresh"); time.sleep(1.1)
    g(d, "config", "core.trustctime", "false")
    st = f.stat(); text = f.read_text()
    new = text.replace("def test_1", "def xest_1").replace("def test_2", "def xest_2").replace("def test_3", "def xest_3").replace("def test_4", "def xest_4")
    assert len(new) == len(text)
    with open(f, "r+") as fh: fh.write(new)
    os.utime(f, ns=(st.st_atime_ns, st.st_mtime_ns))
case("Y-02 variant: same size and mtime, core.trustctime=false (local config)", statcache)
def skip(d): (d / "tests/conftest.py").write_text("import pytest\ndef pytest_collection_modifyitems(items):\n    for i in items[1:]:\n        i.add_marker(pytest.mark.skip(reason='x'))\n"); commit(d, "skip")
case("Y-03 committed conftest skipping", skip)
def xfail(d): (d / "tests/conftest.py").write_text("import pytest\ndef pytest_collection_modifyitems(items):\n    for i in items[1:]:\n        i.add_marker(pytest.mark.xfail(strict=False, reason='x'))\n"); commit(d, "xfail")
case("Y-03 variant: xfail(strict=False) on passing tests (xpassed)", xfail)
def modskip(d): (d / "tests/test_b.py").write_text('import pytest\npytest.importorskip("module_that_is_not_installed_xyz")\n' + body(5)); commit(d, "optional")
case("Y-03 variant: module-level importorskip in a committed test file", modskip)
def skipif(d): (d / "tests/test_b.py").write_text('import pytest\npytestmark = pytest.mark.skipif(True, reason="platform")\n' + body(5)[len("import pytest\n"):]); commit(d, "skipif")
case("Y-03 variant: module-level skipif", skipif)
case("V-16 report into a new directory", report="new/dir/report.json")
case("F-14 report outside the repository", report=str(W / "tiny-outside-report.json"))
