"""Y-09: a gate may cite a file that is merely *under* an owned path. The check does not ask
whether that file is tracked at the verified revision, so a git-ignored (or untracked) file
there counts as "hash-pinned" evidence although nothing pins it: verification is allowed,
the file can then be rewritten with check still at 0 errors, and only a fresh clone, where
the file is absent, reports it."""
import subprocess

from lib import W, new_sandbox, codes
from citerift.governance.model import Status
from citerift.governance.orchestrator import Orchestrator

sb = new_sandbox("y03")
sb.write(".gitignore", "__pycache__/\n")
sb.commit("ignore caches")
for t in (Status.AUTHORIZED, Status.IN_PROGRESS):
    assert sb.go("00", t).allowed
sb.write("src/citerift/governance/impl.py", "x = 1\n")
rev = sb.commit("impl")
assert sb.go("00", Status.IMPLEMENTED_NOT_VERIFIED, revision=rev).allowed
sb.write_evidence("00", rev)
ev = "src/citerift/governance/__pycache__/gate-evidence.txt"   # ignored, never committed
sb.write(ev, "all gates pass\n")
gates = {g["id"]: {"result": "pass", "evidence": [ev]} for g in sb.orc().stage("00")["acceptance_gates"]}
r = sb.go("00", Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE, gates=gates, ci=sb.ci(rev))
print("verify with only an ignored file as gate evidence: allowed =", r.allowed, codes(r.findings))
sb.commit("verify")
sb.write(ev, "rewritten after verification: nothing passed\n")
print("check after rewriting the cited file:", codes(sb.orc().check()) or "0 errors")
clone = W / "sandbox-y03" / "clone"
subprocess.run(["git", "clone", "-q", str(sb.root), str(clone)], check=True)
print("check in a fresh clone:", codes(Orchestrator(clone).check()))
