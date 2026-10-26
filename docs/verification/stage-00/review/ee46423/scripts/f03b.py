import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-citerift/0bbaf0e6-71eb-560d-84bf-668fa4ffb288/scratchpad/review/scripts")
from lib import *
sys.path.insert(0, str(CLONE / "tests/stage00"))
from sandbox_repo import Sandbox
from citerift.governance.model import Status, Actor
e = mk("f03_predef")
r = reg(e)
s2 = next(s for s in r["stages"] if s["id"] == "02")
s2["executor"] = "external-agent"; s2["ci_required"] = False
s2["required_artifacts"] = []; s2["acceptance_gates"] = s2["acceptance_gates"][:1]; s2["required_test_suites"] = ["unit"]
s2["owned_paths"] = []
save(e, r); commit(e, "weaken stage 02 definition before it starts")
check(e, "stage 02 definition weakened before authorization")
sb = Sandbox.__new__(Sandbox); sb.root = e; sb.clock = 30
assert sb.go("02", Status.AUTHORIZED).allowed
assert sb.go("02", Status.IN_PROGRESS).allowed
(e / "impl/02.txt").write_text("x\n"); rev = commit(e, "impl 02")
assert sb.go("02", Status.IMPLEMENTED_NOT_VERIFIED, revision=rev).allowed
vdir = e / "docs/verification/stage-02"; vdir.mkdir(parents=True, exist_ok=True)
(vdir / "test-report.json").write_text(json.dumps({"format": "citerift.test-report/1", "revision": rev, "dirty": False,
   "exit_status": 0, "totals": {"passed": 1}, "selection": {"complete": True}, "suites": {"unit": {"passed": 1}}}))
gid = s2["acceptance_gates"][0]["id"]
res = sb.go("02", Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE, gates={gid: {"result": "pass", "evidence": ["https://example.invalid/x"]}}, ci=None)
print("verify 02 with no artifacts, no handoff, no CI, 1 gate, 1 suite, URL-only gate evidence:", "ALLOWED" if res.allowed else "REFUSED")
for f in res.findings: print("   ", f)
commit(e, "verify 02")
check(e, "after verification of weakened stage 02")
