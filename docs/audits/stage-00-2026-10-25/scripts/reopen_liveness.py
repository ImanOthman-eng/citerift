import sys, tempfile
from pathlib import Path
sys.path.insert(0, sys.argv[1] + "/tests/stage00")
from sandbox_repo import Sandbox, OWNER_REF
from citerift.governance.model import Status, Actor
sb = Sandbox(Path(tempfile.mkdtemp(dir=sys.argv[2])) / "repo")
for sid in ("00", "01", "02"):
    sb.drive_to_accepted(sid)
orc = sb.orc()
aid = orc.add_amendment("00", kind="correction", reason="foundation bug found after 02 accepted",
                        evidence_refs=["docs/verification/stage-00/HANDOFF.md"], owner_ref=OWNER_REF, at=sb.tick())
r = sb.go("00", Status.IN_PROGRESS, actor=Actor.OWNER, amendment=aid, apply=False)
print("reopen 00 with correction", aid, "while 02 ACCEPTED_CLOSED ->", "ALLOWED" if r.allowed else "REFUSED")
for f in r.findings: print("  ", f)
