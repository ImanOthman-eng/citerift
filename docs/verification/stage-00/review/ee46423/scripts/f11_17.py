import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-citerift/0bbaf0e6-71eb-560d-84bf-668fa4ffb288/scratchpad/review/scripts")
from lib import *
sys.path.insert(0, str(CLONE / "tests/stage00"))
from sandbox_repo import Sandbox, OWNER_REF
from citerift.governance.model import Status, Actor
def sbox(root, clock=100):
    sb = Sandbox.__new__(Sandbox); sb.root = root; sb.clock = clock; return sb
def show(label, res):
    print(f"{label}: {'ALLOWED' if res.allowed else 'REFUSED'}")
    for f in res.findings: print("    ", f)

# F-11 original script
r = sh(PY, str(CLONE / "docs/audits/stage-00-2026-10-25/scripts/reopen_liveness.py"), str(CLONE), str(W / "exp"), check=False)
print("--- F-11 original reopen_liveness.py [exit", r.returncode, "]\n", r.stdout, r.stderr[-800:])

# F-11 variant: dependent 02 is IN_PROGRESS (active) when 00 needs a correction
e = mk("f11_active_dependent"); sb = sbox(e)
assert sb.go("02", Status.AUTHORIZED).allowed and sb.go("02", Status.IN_PROGRESS).allowed
aid = sb.orc().add_amendment("00", kind="correction", reason="foundation bug while 02 in progress", evidence_refs=["docs/verification/stage-00/HANDOFF.md"], owner_ref=OWNER_REF, at=sb.tick())
show("F-11 variant: owner reopens 00 (correction) while dependent 02 is IN_PROGRESS", sb.go("00", Status.IN_PROGRESS, actor=Actor.OWNER, amendment=aid, apply=False))

# F-05 variant: one correction amendment used for two reopenings
e = mk("f05_amend_reuse"); sb = sbox(e)
aid = sb.orc().add_amendment("00", kind="correction", reason="first correction of stage 00", evidence_refs=["docs/verification/stage-00/HANDOFF.md"], owner_ref="cmsg_AMENDREF000001", at=sb.tick())
commit(e, "amend")
def recycle(sb, aid, ref):
    res = sb.go("00", Status.IN_PROGRESS, actor=Actor.OWNER, amendment=aid, owner_ref=ref); assert res.allowed, [str(f) for f in res.findings]
    (sb.root / "impl/00.txt").write_text(f"fix {sb.clock}\n"); rev = sb.commit("fix")
    assert sb.go("00", Status.IMPLEMENTED_NOT_VERIFIED, revision=rev).allowed
    sb.write_evidence("00", rev)
    res = sb.go("00", Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE, gates=sb.gates("00"), ci=sb.ci(rev)); assert res.allowed, [str(f) for f in res.findings]
    sb.commit("verify")
    return rev
recycle(sb, aid, "cmsg_REOPENREF00001")
res = sb.go("00", Status.ACCEPTED_CLOSED); assert res.allowed; sb.commit("accept")
show("F-05 variant: second reopening citing the already-used correction A-00-001", sb.go("00", Status.IN_PROGRESS, actor=Actor.OWNER, amendment=aid, owner_ref="cmsg_REOPENREF00002", apply=False))

# F-17 original variants
e = mk("f17_auth_ref"); r = reg(e); s0 = r["stages"][0]
ref = s0["authorization"]["owner_ref"]; s0["acceptance"]["owner_ref"] = ref
next(h for h in reversed(r["history"]) if h["stage"] == "00" and h["to"] == "ACCEPTED_CLOSED")["owner_ref"] = ref
save(e, r); commit(e, "x"); check(e, "F-17 original: acceptance reuses the authorization owner_ref")
e = mk("f17_times"); sh(PY, str(CLONE / "docs/audits/stage-00-2026-10-25/scripts/mutate.py"), str(e), "acceptance_before_history")
sh(GOV, "--root", str(e), "render-status", "--write"); commit(e, "x"); check(e, "F-17 original: acceptance_before_history")

# F-17 variant (a): two stages verified, owner accepts one; the agent records the other's acceptance with the same ref
d = W / "exp/f17_shared_accept"; sb = Sandbox(d)
sb.drive_to_verified("00"); sb.drive_to_verified("01")
show("accept 00 with cmsg_ONESTATEMENT001", sb.go("00", Status.ACCEPTED_CLOSED, owner_ref="cmsg_ONESTATEMENT001")); sb.commit("a")
show("F-17 variant (a): accept 01 with the same cmsg_ONESTATEMENT001", sb.go("01", Status.ACCEPTED_CLOSED, owner_ref="cmsg_ONESTATEMENT001")); sb.commit("b")
check(d, "after both acceptances with one owner statement")

# F-17 variant (b): authorize a later stage citing the acceptance message of an earlier one
e = mk("f17_auth_from_accept"); sb = sbox(e)
acc_ref = reg(e)["stages"][0]["acceptance"]["owner_ref"]
show(f"F-17 variant (b): authorize 02 citing 00's acceptance ref {acc_ref}", sb.go("02", Status.AUTHORIZED, owner_ref=acc_ref, apply=False))

# F-17 variant (c): acceptance cites the owner_ref of the correction amendment recorded before the verification
e = mk("f17_amend_ref"); sb = sbox(e)
aid = sb.orc().add_amendment("00", kind="correction", reason="correction of stage 00", evidence_refs=["docs/verification/stage-00/HANDOFF.md"], owner_ref="cmsg_AMENDMENTREF01", at=sb.tick())
commit(e, "amend")
recycle(sb, aid, "cmsg_REOPENREF00001")
show("F-17 variant (c): accept re-verified 00 citing the amendment's owner_ref (cited before the verification)", sb.go("00", Status.ACCEPTED_CLOSED, owner_ref="cmsg_AMENDMENTREF01", apply=False))
show("control: accept citing the reopening's owner_ref", sb.go("00", Status.ACCEPTED_CLOSED, owner_ref="cmsg_REOPENREF00001", apply=False))
