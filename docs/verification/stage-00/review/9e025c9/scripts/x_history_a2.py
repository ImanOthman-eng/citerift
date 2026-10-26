"""Blocker open at the moment of the acceptance (hand edit, resolved later): is the acceptance checked over history?"""
import sys
sys.path.insert(0, "/tmp/claude-0/-home-user-citerift/0bbaf0e6-71eb-560d-84bf-668fa4ffb288/scratchpad/review2/scripts")
from lib import *
d = mk("hist_blocker_accept2")
r = reg(d); s01 = [s for s in r["stages"] if s["id"] == "01"][0]
acc = [h for h in r["history"] if h["stage"] == "01" and h["to"] == "ACCEPTED_CLOSED"][-1]["at"]
s01["blockers"].append({"id": "B-01-001", "description": "external handoff missing a section", "opened_at": acc,
                        "resolved_at": "2026-01-01T01:00:00Z", "resolution": "resolved after the acceptance"})
print("accepted at", acc, "; blocker open from", acc, "to 2026-01-01T01:00:00Z")
save(d, r); commit(d, "hand edit")
check(d, "A2: acceptance while a blocker was open")
# control: the same blocker still open now
r["stages"][1]["blockers"][0].update(resolved_at=None, resolution=None); save(d, r)
check(d, "A2 control: blocker still open")
