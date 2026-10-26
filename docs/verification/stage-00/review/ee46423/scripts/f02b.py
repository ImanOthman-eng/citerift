import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-citerift/0bbaf0e6-71eb-560d-84bf-668fa4ffb288/scratchpad/review/scripts")
from lib import *
# Variant: exemption for amendment test reports. A correction amendment may name any file as test_report;
# that file is then exempt from EVIDENCE_UNLISTED, and for a correction its hash is never compared again.
e = mk("f02_amendexempt")
rel = "docs/verification/stage-00/late-evidence.md"
(e / rel).write_text("added after verification: gate 00-F really passed\n")
r = sh(GOV, "--root", str(e), "amend", "00", "--kind", "correction", "--reason", "reviewer experiment, not real",
       "--evidence", "docs/verification/stage-00/HANDOFF.md", "--owner-ref", "cmsg_REVIEWEXPERIMENT01",
       "--test-report", rel, "--at", "2026-01-01T00:01:00Z", check=False)
print("amend:", r.returncode, r.stdout.strip(), r.stderr.strip()[-300:])
commit(e, "amendment with test_report naming a new file")
check(e, "after correction amendment naming the new file as test_report")
(e / rel).write_text("rewritten again: anything\n"); commit(e, "rewrite the exempt file")
check(e, "F-02 exemption: the exempt file rewritten after the amendment")
