"""Remaining probes: F-01, F-12, F-16, F-18, F-19, V-04, V-11, V-14, X-12 (inspection), O-1."""
import json, os, re, subprocess, tempfile
from pathlib import Path
from datetime import datetime, timedelta, UTC
from lib import BASE, PY, W, new_sandbox, run, codes
from citerift.governance import memory
from citerift.governance.model import Status, Actor
from citerift.governance.orchestrator import Orchestrator, GovernanceError
def hdr(s): print(f"\n### {s}")
ENV = {**os.environ, "GIT_AUTHOR_NAME": "r", "GIT_AUTHOR_EMAIL": "r@x", "GIT_COMMITTER_NAME": "r", "GIT_COMMITTER_EMAIL": "r@x"}
def git(d, *a): return subprocess.run(["git", "-C", str(d), *a], capture_output=True, text=True, env=ENV, check=True).stdout.strip()

hdr("F-01 merge restoring pre-verification owned content; F-19 uncommitted owned change")
sb = new_sandbox("f01"); sb.write("src/citerift/governance/x.py", "v0\n"); sb.commit("v0")
git(sb.root, "branch", "old")
sb.write("src/citerift/governance/x.py", "v1\n"); sb.commit("v1")
rev = sb.drive_to_accepted("00")
git(sb.root, "merge", "-q", "-s", "ours", "old", "-m", "merge old")  # tree unchanged by -s ours
git(sb.root, "checkout", "-q", "old", "--", "src/citerift/governance/x.py"); git(sb.root, "commit", "-q", "--amend", "--no-edit")
print("  merge commit restoring v0:", codes(sb.orc().check(include_status_doc=False)))
sb2 = new_sandbox("f19"); sb2.drive_to_accepted("00"); sb2.write("src/citerift/governance/y.py", "u\n")
print("  uncommitted owned change (warnings):", sorted({f.code for f in sb2.orc().check(include_status_doc=False) if f.severity == "warning"}))

hdr("F-12 CRLF checkout (core.autocrlf=true) of an accepted sandbox")
c = W / "sandbox-f12"; subprocess.run(["rm", "-rf", str(c)])
subprocess.run(["git", "-c", "core.autocrlf=true", "clone", "-q", str(W / "x2/exp/base"), str(c)], check=True)
git(c, "config", "core.autocrlf", "true")
print("  check in CRLF clone:", codes(Orchestrator(c).check()) or "0 errors")

hdr("F-16 future timestamp; V-11 default time after a forward-dated entry")
sb = new_sandbox("f16")
r = sb.go("00", Status.AUTHORIZED, at="2030-01-01T00:00:00Z"); print("  authorize at 2030:", r.allowed, codes(r.findings))
soon = (datetime.now(UTC) + timedelta(minutes=4)).strftime("%Y-%m-%dT%H:%M:%SZ")
assert sb.go("00", Status.AUTHORIZED, at=soon).allowed
bid = sb.orc().add_blocker("00", "blocker on a correct clock right after a forward-dated entry")
o = sb.orc(); print("  blocker opened_at", o.stage("00")["blockers"][0]["opened_at"], ">= last entry", o.registry["history"][-1]["at"], "| check:", codes(o.check(include_status_doc=False)) or "0 errors")

hdr("F-18 duplicate key in the registry")
sb = new_sandbox("f18"); p = sb.root / "governance/stage_registry.json"; t = p.read_text()
p.write_text(t.replace('"registry_version"', '"registry_version": "9.9.9", "registry_version"', 1))
c_ = run([PY, "-P", "-m", "citerift.governance.cli", "check"], cwd=sb.root); print("  check:", c_.returncode, c_.stdout.strip().splitlines()[:2])

hdr("V-04 entry point redirected to a shim: CI command is not affected")
c = W / "sandbox-v04"; subprocess.run(["rm", "-rf", str(c)]); subprocess.run(["git", "clone", "-q", str(BASE), str(c)], check=True)
pp = c / "pyproject.toml"; pp.write_text(pp.read_text().replace('citerift-gov = "citerift.governance.cli:main"', 'citerift-gov = "citerift.gov_shim:main"'))
(c / "src/citerift/gov_shim.py").write_text("def main():\n    print('Consistency check: 0 errors, 0 warnings')\n    return 0\n")
reg = c / "governance/stage_registry.json"; reg.write_text(reg.read_text().replace('"status": "IN_PROGRESS"', '"status": "ACCEPTED_CLOSED"', 1))
r = subprocess.run([PY, "-P", "-m", "citerift.governance.cli", "check"], cwd=c, capture_output=True, text=True, env={**ENV, "PYTHONPATH": "src"})
print("  CI command python -P -m citerift.governance.cli check:", r.returncode, r.stdout.splitlines()[0])

hdr("V-14 tests read the ruleset and fixtures with loads_strict")
for f in ("tests/stage00/test_repository.py", "tests/stage00/test_contracts.py"):
    t = (BASE / f).read_text(); print(f"  {f}: json.loads calls={len(re.findall(r'json\.loads\(', t))} loads_strict calls={t.count('loads_strict(')}")
rs = BASE / "tests/stage00/test_repository.py"; m = re.search(r"def test_branch_ruleset_definition.*?(?=\ndef |\Z)", rs.read_text(), re.S)
print("  ruleset test uses loads_strict:", "loads_strict" in m.group(0))

hdr("X-12 repository test asserts the rule, not today's state")
m = re.search(r"def test_no_stage_is_started_without_an_owner_authorization.*?(?=\n@|\ndef |\Z)", rs.read_text(), re.S)
print("  " + "\n  ".join(m.group(0).splitlines()[:14]))

hdr("O-1 Arabic tatweel and harakat")
for label, a, b in (("tatweel", "قرار", "قـرار"), ("fatha", "قرار", "قَرار"), ("shadda", "قرار", "قرّار"), ("superscript alef U+0670", "قرار", "قرارٰ")):
    p = Path(tempfile.mkdtemp(dir=W)) / "DECISIONS.md"
    p.write_text("# D\n" + "".join(f"\n## D-00{i} — t\n- Status: accepted\n- Topic: {t}\n" for i, t in ((1, a), (2, b))), encoding="utf-8")
    print(f"  {label}:", sorted({x.code for x in memory.check_decisions(p)[1]}) or "no problem")
