import sys
sys.path.insert(0, "/tmp/claude-0/-home-user-citerift/0bbaf0e6-71eb-560d-84bf-668fa4ffb288/scratchpad/review/scripts")
from lib import *
e = mk("h1_late_amendment"); r = reg(e); s0 = r["stages"][0]; h = r["history"]
s0["amendments"] = [{"id": "A-00-001", "kind": "correction", "reason": "recorded after the reopening", "evidence": ["docs/verification/stage-00/HANDOFF.md"],
     "owner_ref": "cmsg_LATEAMENDREF1", "revision": None, "test_report": None, "recorded_at": "2026-01-01T00:30:00Z"}]
h.append({"seq": len(h) + 1, "at": "2026-01-01T00:20:00Z", "stage": "00", "from": "ACCEPTED_CLOSED", "to": "IN_PROGRESS", "actor": "owner",
          "recorded_by": "engineering-agent", "reason": "reopen", "owner_ref": "cmsg_REOPENREF00077", "amendment": "A-00-001"})
s0["status"] = "IN_PROGRESS"; s0["implementation"] = s0["verification"] = s0["acceptance"] = None
save(e, r); commit(e, "x")
check(e, "H1 manual: correction amendment recorded 10 minutes after the reopening it justifies")
