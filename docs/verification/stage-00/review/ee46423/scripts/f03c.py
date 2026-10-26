import sys
sys.path.insert(0, "/tmp/claude-0/-home-user-citerift/0bbaf0e6-71eb-560d-84bf-668fa4ffb288/scratchpad/review/scripts")
from lib import *
sys.path.insert(0, str(CLONE / "tests/stage00"))
from sandbox_repo import Sandbox
from citerift.governance.model import Status
from citerift.governance.orchestrator import Orchestrator
d = W / "exp/f03_noartifacts2"; sb = Sandbox(d)
r = sb.registry(); r["stages"][0]["required_artifacts"] = []; sb.save_registry(r); Orchestrator(d).write(); sb.commit("stage 00 requires no artifacts")
for t in (Status.AUTHORIZED, Status.IN_PROGRESS): assert sb.go("00", t).allowed
sb.write("impl/00.txt", "x\n"); rev = sb.commit("impl")
assert sb.go("00", Status.IMPLEMENTED_NOT_VERIFIED, revision=rev).allowed
sb.write_evidence("00", rev)
ev = "docs/verification/stage-00/test-report.json"
gates = {g["id"]: {"result": "pass", "evidence": [ev]} for g in sb.orc().stage("00")["acceptance_gates"]}
res = sb.go("00", Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE, gates=gates, ci=sb.ci(rev))
print("verify engineering stage 00 (CI recorded) with required_artifacts: [] ->", "ALLOWED" if res.allowed else "REFUSED", [str(f) for f in res.findings])
sb.commit("verify")
print("files in verification dir:", sorted(p.name for p in (d / "docs/verification/stage-00").iterdir()))
check(d, "after verification")
