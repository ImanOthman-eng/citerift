"""History/model gaps on sandboxes built by citerift-gov itself."""
import json, shutil, sys
sys.path.insert(0, "/tmp/claude-0/-home-user-citerift/0bbaf0e6-71eb-560d-84bf-668fa4ffb288/scratchpad/review4/scripts/orig_x")
from lib import *
sys.path.insert(0, str(CLONE / "tests/stage00"))
from sandbox_repo import Sandbox
from citerift.governance.model import Status, Actor

# A. Blocker open while Stage 01 was VERIFIED and ACCEPTED (hand edit: blocker resolved later)
d = mk("hist_blocker_accept")
r = reg(d); s01 = [s for s in r["stages"] if s["id"] == "01"][0]
ver = [h for h in r["history"] if h["stage"] == "01" and h["to"] == "VERIFIED_AWAITING_OWNER_ACCEPTANCE"][-1]["at"]
acc = [h for h in r["history"] if h["stage"] == "01" and h["to"] == "ACCEPTED_CLOSED"][-1]["at"]
s01["blockers"].append({"id": "B-01-001", "description": "external handoff missing a section", "opened_at": ver,
                        "resolved_at": "2026-01-01T01:00:00Z", "resolution": "resolved after the acceptance"})
print("verified at", ver, "accepted at", acc, "blocker open", ver, "-> 2026-01-01T01:00:00Z")
save(d, r); commit(d, "hand edit")
check(d, "A: stage accepted while a blocker was open (by history)")

# B. Pre-verification edit of depends_on: Stage 02 no longer depends on Stage 01 (external, NOT accepted)
d = W / "exp/hist_deps"
if d.exists(): shutil.rmtree(d)
sb = Sandbox(d); shutil.copy(CLONE / ".gitattributes", d / ".gitattributes"); sb.commit("attrs")
sb.drive_to_accepted("00")
r = sb.registry(); s02 = [s for s in r["stages"] if s["id"] == "02"][0]
print("02 depends_on before:", s02["depends_on"]); s02["depends_on"] = ["00"]; s02["owned_paths"] = ["impl/02.txt"]
sb.save_registry(r); Orchestrator = __import__("citerift.governance.orchestrator", fromlist=["Orchestrator"]).Orchestrator
Orchestrator(d).write(); sb.commit("edit 02 definition")
print("01 status:", sb.orc().stage("01")["status"])
rev = sb.drive_to_verified("02")
res = sb.go("02", Status.ACCEPTED_CLOSED); print("accept 02 while 01 NOT_STARTED:", "ALLOWED" if res.allowed else "REJECTED", [str(f) for f in res.findings][:3])
sb.commit("accept 02")
check(d, "B: Stage 02 verified and accepted without Stage 01")
