import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-citerift/0bbaf0e6-71eb-560d-84bf-668fa4ffb288/scratchpad/review/scripts")
from lib import *
MUT = str(CLONE / "docs/audits/stage-00-2026-10-25/scripts/mutate.py")
def entry(h, stage, frm, to, actor, at, ref=None, **kw):
    return {"seq": 0, "at": at, "stage": stage, "from": frm, "to": to, "actor": actor, "recorded_by": "engineering-agent",
            "reason": "review hand edit", "owner_ref": ref, **kw}
def reseq(r):
    for i, e in enumerate(r["history"], 1): e["seq"] = i

# F-04 original shape: 02 authorized and withdrawn while 00 IN_PROGRESS and 01 not accepted
e = mk("f04_past"); r = reg(e); h = r["history"]
at = h[1]["at"]
h[2:2] = [entry(h, "02", "NOT_STARTED", "AUTHORIZED", "owner", at, "cmsg_FORGEDREF0001"),
          entry(h, "02", "AUTHORIZED", "NOT_STARTED", "owner", at, "cmsg_FORGEDREF0002")]
reseq(r); save(e, r); commit(e, "x")
check(e, "F-04 original: past authorization of 02 while 00 active and 01 unaccepted, then withdrawn")

# F-04 variant: same past violation, but placed for an external-agent stage pair is irrelevant; instead violate
# the dependency rule only at verification time: insert 02 AUTH (after 00+01 accepted) is legal; we instead make
# 01's verify entry happen before 01's own dependencies? 01 has none. Use acceptance ordering: move 00 acceptance after 02 verify.
# Variant: single-active violated only via a BLOCKED/IMPLEMENTED stage (not AUTHORIZED)
e = mk("f04_variant"); r = reg(e); h = r["history"]
at = h[-1]["at"]
h += [entry(h, "02", "NOT_STARTED", "AUTHORIZED", "owner", at, "cmsg_FORGEDREF0003"),
      entry(h, "02", "AUTHORIZED", "IN_PROGRESS", "engineering-agent", at),
      entry(h, "03", "NOT_STARTED", "AUTHORIZED", "owner", at, "cmsg_FORGEDREF0004"),
      entry(h, "02", "IN_PROGRESS", "BLOCKED", "engineering-agent", at)]
# end state must be consistent: withdraw 03, so only 02 (BLOCKED) remains active at the end
h += [entry(h, "03", "AUTHORIZED", "NOT_STARTED", "owner", at, "cmsg_FORGEDREF0005")]
s2 = next(s for s in r["stages"] if s["id"] == "02"); s2["status"] = "BLOCKED"
s2["authorization"] = {"owner_ref": "cmsg_FORGEDREF0003", "scope": "x", "recorded_at": at}
s2["blockers"] = [{"id": "B-02-001", "description": "x", "opened_at": at, "resolved_at": None, "resolution": None}]
reseq(r); save(e, r); commit(e, "x")
check(e, "F-04 variant: 03 authorized in the past while 02 IN_PROGRESS, later withdrawn")

# F-05 originals
e = mk("f05_reopen"); sh(PY, MUT, str(e), "reopen_without_amendment"); sh(GOV, "--root", str(e), "render-status", "--write"); commit(e, "x")
check(e, "F-05 original: reopen without amendment")
e = mk("f05_blocker"); r = reg(e); h = r["history"]; at = h[-1]["at"]
s2 = next(s for s in r["stages"] if s["id"] == "02")
h += [entry(h, "02", "NOT_STARTED", "AUTHORIZED", "owner", at, "cmsg_FORGEDREF0006"),
      entry(h, "02", "AUTHORIZED", "IN_PROGRESS", "engineering-agent", at)]
s2["status"] = "IN_PROGRESS"; s2["authorization"] = {"owner_ref": "cmsg_FORGEDREF0006", "scope": "x", "recorded_at": at}
s2["blockers"] = [{"id": "B-02-001", "description": "open", "opened_at": at, "resolved_at": None, "resolution": None}]
reseq(r); save(e, r); commit(e, "x")
check(e, "F-05 original: IN_PROGRESS entered with an open blocker")
