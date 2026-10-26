"""Section 2 rechecks: variants of earlier attacks that the fixes still stop (no bypass)."""
import json
import os
import subprocess

from lib import BASE, PY, W, new_sandbox, run, codes
from citerift.governance.model import Status
from citerift.contracts.validate import load_contracts

# ---- X-01: gate evidence path forms
sb = new_sandbox("rx01")
for t in (Status.AUTHORIZED, Status.IN_PROGRESS):
    assert sb.go("00", t).allowed
sb.write("src/citerift/governance/real.py", "x = 1\n" * 100)
sb.write("NOTES.md", "n" * 400)
rev = sb.commit("impl")
assert sb.go("00", Status.IMPLEMENTED_NOT_VERIFIED, revision=rev).allowed
sb.write_evidence("00", rev)
os.symlink("../..", sb.root / "src/citerift/up")
for ref in ("src/citerift/governance/../../../NOTES.md", "src/citerift//governance/real.py", "./src/citerift/governance/real.py",
            "src/citerift/up/NOTES.md", "src/citerift/governance/real.py/", "http://example.org/x"):
    gates = {g["id"]: {"result": "pass", "evidence": [ref]} for g in sb.orc().stage("00")["acceptance_gates"]}
    r = sb.go("00", Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE, gates=gates, ci=sb.ci(rev), apply=False)
    print(f"X-01 {ref!r}: allowed={r.allowed}", codes(r.findings)[:3])

# ---- X-03 variants in a tiny project that uses the reviewed plugin
tiny = W / "sandbox-rx03"
subprocess.run(["rm", "-rf", str(tiny)])
(tiny / "tests").mkdir(parents=True)
(tiny / "pyproject.toml").write_text('[tool.pytest.ini_options]\ntestpaths = ["tests"]\n'
                                     'addopts = ["-p", "citerift.governance.pytest_report", "--strict-markers"]\n')
(tiny / "tests/test_a.py").write_text("import pytest\n\n" + "".join(
    f"@pytest.mark.unit\ndef test_{i}():\n    pass\n\n" for i in range(5)))
(tiny / "plug.py").write_text("def pytest_collection_modifyitems(items):\n    del items[1:]\n")
env = {"GIT_AUTHOR_NAME": "r", "GIT_AUTHOR_EMAIL": "r@x.invalid", "GIT_COMMITTER_NAME": "r", "GIT_COMMITTER_EMAIL": "r@x.invalid"}
for c in (["init", "-q"], ["add", "-A"], ["commit", "-qm", "t"]):
    subprocess.run(["git", "-C", str(tiny), *c], check=True, env={**os.environ, **env})
for label, extra_env, args in (
    ("PYTEST_ADDOPTS=-p plug", {"PYTEST_ADDOPTS": "-p plug"}, []),
    ("-pplug (no space)", {}, ["-pplug"]),
    ("--deselect", {}, ["--deselect", "tests/test_a.py::test_1"]),
    ("--sw-skip", {}, ["--sw-skip"]),
    ("-x", {}, ["-x"]),
    ("--co", {}, ["--co"]),
    ("--setup-only", {}, ["--setup-only"]),
    ("--noconftest", {}, ["--noconftest"]),
    ("-p no:python", {}, ["-p", "no:python"]),
    ("--keep-duplicates tests tests", {}, ["--keep-duplicates", "tests", "tests"]),
):
    out = run([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--citerift-report", "../rx03.json", *args], cwd=tiny,
              env={"PYTHONPATH": f"{BASE / 'src'}:{tiny}", **extra_env})
    try:
        rep = json.loads((W / "rx03.json").read_text())
        print(f"X-03 {label}: complete={rep['selection']['complete']} totals={rep['totals']} exit={rep['exit_status']}")
    except FileNotFoundError:
        print(f"X-03 {label}: no report", out.stdout[-100:])
    (W / "rx03.json").unlink(missing_ok=True)

# ---- X-07: remove a stage, duplicate a stage
for label, edit in (("remove stage 01", lambda r: r["stages"].pop(1)),
                    ("duplicate stage 02", lambda r: r["stages"].append(json.loads(json.dumps(r["stages"][2]))))):
    sb = new_sandbox("rx07")
    reg = sb.registry()
    edit(reg)
    sb.save_registry(reg)
    sb.orc().write()
    print(f"X-07 {label}:", codes(sb.orc().check()))

# ---- X-09: a shallow-graft file (.git/shallow) cannot hide drift; it fails closed
sb = new_sandbox("rx09")
rev = sb.drive_to_verified("00")
sb.write("src/citerift/governance/drift.py", "z\n")
sb.commit("drift")
head = subprocess.run(["git", "-C", str(sb.root), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
(sb.root / ".git/shallow").write_text(head + "\n")
print("X-09 .git/shallow at HEAD:", codes(sb.orc().check()))

# ---- X-11: Wikipedia edition codes
contracts = load_contracts(BASE / "schemas/contracts")
lang = contracts.schemas["urn:citerift:schema:contracts:v1:common"]["$defs"]["wiki_language"]["pattern"]
import re
codes_list = ["en", "ar", "simple", "zh-yue", "zh-classical", "zh-min-nan", "be-tarask", "be-x-old", "roa-tara",
              "map-bms", "bat-smg", "cbk-zam", "fiu-vro", "nds-nl", "roa-rup", "arz", "azb", "ckb"]
print("X-11 rejected edition codes:", [c for c in codes_list if not re.search(lang, c)] or "none")
