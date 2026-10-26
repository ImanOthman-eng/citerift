import sys, tempfile
from pathlib import Path
sys.path.insert(0, sys.argv[1] + "/tests/stage00")
from sandbox_repo import Sandbox, OWNER_REF
from citerift.governance.model import Status, Actor
sb = Sandbox(Path(tempfile.mkdtemp(dir=sys.argv[2])) / "repo")
reg = sb.registry(); reg["stages"][2]["owned_paths"] = ["impl/02.txt"]; sb.save_registry(reg)  # adapted: Stage 02 has no owned paths yet at 97b2051
from citerift.governance.orchestrator import Orchestrator; Orchestrator(sb.root).write(); sb.commit("define 02 owned path")
for sid in ("00", "01", "02"):
    sb.drive_to_accepted(sid)
orc = sb.orc()
aid = orc.add_amendment("00", kind="correction", reason="foundation bug found after 02 accepted",
                        evidence_refs=["docs/verification/stage-00/HANDOFF.md"], owner_ref="cmsg_NEWCORRECTIONREF01", at=sb.tick())
r = sb.go("00", Status.IN_PROGRESS, actor=Actor.OWNER, owner_ref="cmsg_NEWCORRECTIONREF01", amendment=aid, apply=False)
print("reopen 00 with correction", aid, "while 02 ACCEPTED_CLOSED ->", "ALLOWED" if r.allowed else "REFUSED")
for f in r.findings: print("  ", f)
