import sys, shutil, json
sys.path.insert(0, "/tmp/claude-0/-home-user-citerift/0bbaf0e6-71eb-560d-84bf-668fa4ffb288/scratchpad/review/scripts")
from lib import *
sys.path.insert(0, str(CLONE / "tests/stage00"))
from sandbox_repo import Sandbox
from citerift.governance.model import Status, Actor
from citerift.governance.orchestrator import Orchestrator

# --- original F-02 repros on the base sandbox
e = mk("f02_edit")
p = e / "docs/verification/stage-00/TEST_RESULTS.md"; p.write_text(p.read_text() + "\nM1 survived\n"); commit(e, "edit gate evidence")
check(e, "F-02 original: edit and commit a gate-evidence file in the verification dir")
e = mk("f02_report")
p = e / "docs/verification/stage-00/test-report.json"; d = json.loads(p.read_text()); d["totals"] = {"passed": 1, "failed": 160}; d["exit_status"] = 1
p.write_text(json.dumps(d)); commit(e, "edit report")
check(e, "F-02 original: test report totals rewritten")
e = mk("f02_dot")
r = reg(e)
for g in r["stages"][0]["verification"]["gates"].values(): g["evidence"] = ["."]
save(e, r); commit(e, "gate dot")
check(e, "F-02 original: every gate evidence set to '.'")
e = mk("f02_newfile")
(e / "docs/verification/stage-00/extra-claims.md").write_text("added after verification\n"); commit(e, "add file")
check(e, "F-02 variant: new file added to the verification dir after verification")

def build(name, gate_evidence, extra_files=()):
    d = W / "exp" / name
    sb = Sandbox(d)
    for rel, text in extra_files:
        sb.write(rel, text)
    sb.commit("extra files")
    for t in (Status.AUTHORIZED, Status.IN_PROGRESS):
        assert sb.go("00", t).allowed
    sb.write("impl/00.txt", "x\n"); rev = sb.commit("impl")
    assert sb.go("00", Status.IMPLEMENTED_NOT_VERIFIED, revision=rev).allowed
    sb.write_evidence("00", rev)
    gates = {g["id"]: {"result": "pass", "evidence": gate_evidence} for g in sb.orc().stage("00")["acceptance_gates"]}
    res = sb.go("00", Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE, gates=gates, ci=sb.ci(rev))
    print(f"verify 00 with gate evidence {gate_evidence}: {'ALLOWED' if res.allowed else 'REFUSED'}")
    for f in res.findings: print("   ", f)
    sb.commit("verify")
    return sb, d

# Variant: gate evidence is only an https URL (no hash at all)
sb, d = build("f02_url", ["https://example.invalid/anything-at-all"])
check(d, "F-02 variant: every gate cites only an https URL")

# Variant: a gate cites one pinned file and one unpinned repository file; the unpinned one changes later
sb, d = build("f02_mixed", ["docs/verification/stage-00/HANDOFF.md", "NOTES.md"], extra_files=[("NOTES.md", "gate 00-B result: 9/9 mutants killed\n")])
(d / "NOTES.md").write_text("gate 00-B result: 0/9 mutants killed (all survived)\n"); commit(d, "rewrite the real gate evidence")
check(d, "F-02 variant: unpinned co-evidence (NOTES.md) rewritten after verification")
