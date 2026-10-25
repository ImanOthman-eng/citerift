import sys
sys.path.insert(0, "/tmp/claude-0/-home-user-citerift/0bbaf0e6-71eb-560d-84bf-668fa4ffb288/scratchpad/review/scripts")
from lib import *
e = mk("pre_existing"); r = reg(e); r["history"][2]["actor"] = "owner"; r["history"][3]["actor"] = "external-agent"; save(e, r); commit(e, "hand edit")
check(e, "registry with a pre-existing error")
x = sh(GOV, "--root", str(e), "blocker", "add", "02", "a blocker on top of a failing registry", "--at", "2026-01-01T00:05:00Z", check=False)
print("blocker add:", x.returncode, x.stdout.strip())
x = sh(GOV, "--root", str(e), "amend", "00", "--kind", "correction", "--reason", "amendment on a failing registry", "--evidence", "docs/verification/stage-00/HANDOFF.md", "--owner-ref", "cmsg_PREEXISTREF01", "--at", "2026-01-01T00:05:00Z", check=False)
print("amend:", x.returncode, x.stdout.strip())
check(e, "after both writes")
