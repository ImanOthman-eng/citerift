import sys, tempfile
from pathlib import Path
sys.path.insert(0, sys.argv[1] + "/tests/stage00")
from sandbox_repo import Sandbox
from citerift.governance.model import Status
sb = Sandbox(Path(tempfile.mkdtemp(dir=sys.argv[2])) / "repo")
sb.drive_to_accepted("00"); sb.drive_to_accepted("01")
assert sb.go("02", Status.AUTHORIZED).allowed
r = sb.go("03", Status.AUTHORIZED, apply=False)
print("authorize 03 while 02 AUTHORIZED, policy true ->", r.allowed, [f.code for f in r.findings if f.severity == "error"])
reg = sb.registry(); reg["policy"]["single_active_engineering_stage"] = False; sb.save_registry(reg)
from citerift.governance.orchestrator import Orchestrator
Orchestrator(sb.root).write()
r = sb.go("03", Status.AUTHORIZED)
print("after hand-flipping policy flag: authorize 03 ->", r.allowed)
print("check errors:", [str(f) for f in sb.orc().check() if f.severity == "error"])
print("active:", [(s["id"], s["status"]) for s in sb.orc().stages if s["status"] == "AUTHORIZED"])
