import sys, tempfile
from pathlib import Path
sys.path.insert(0, sys.argv[1] + "/tests/stage00")
from sandbox_repo import Sandbox, OWNER_REF
from citerift.governance.model import Status, Actor
sb = Sandbox(Path(sys.argv[2]))
reg = sb.registry(); next(s for s in reg["stages"] if s["id"] == "02")["owned_paths"] = ["impl/02.txt"]; sb.save_registry(reg)
from citerift.governance.orchestrator import Orchestrator
Orchestrator(sb.root).write(); sb.commit("give 02 an owned path (its real definition is set when it is specified)")
for sid in ("00", "01", "02"):
    sb.drive_to_accepted(sid)
orc = sb.orc()
aid = orc.add_amendment("00", kind="correction", reason="foundation bug found after 02 accepted",
                        evidence_refs=["docs/verification/stage-00/HANDOFF.md"], owner_ref=OWNER_REF, at=sb.tick())
r = sb.go("00", Status.IN_PROGRESS, actor=Actor.OWNER, amendment=aid, owner_ref="cmsg_REOPENREF00009")
print("F-11 (adapted audit script): reopen 00 with correction", aid, "while 02 ACCEPTED_CLOSED ->", "ALLOWED" if r.allowed else "REFUSED")
for f in r.findings: print("  ", f)
sb.commit("reopen")
r = sb.go("03", Status.AUTHORIZED, apply=False)
print("then authorize 03 while 00 is reopened ->", "ALLOWED" if r.allowed else "REFUSED", [f.code for f in r.findings if f.severity == "error"])
