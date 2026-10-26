"""V-02 bypass: gate evidence that is 'owned' by string prefix but resolves outside the owned paths."""
import os, sys, shutil
from pathlib import Path
sys.path.insert(0, "/tmp/claude-0/-home-user-citerift/0bbaf0e6-71eb-560d-84bf-668fa4ffb288/scratchpad/review4/scripts/orig_x")
from lib import *
sys.path.insert(0, str(CLONE / "tests/stage00"))
from sandbox_repo import Sandbox
from citerift.governance.model import Status

for case, ref in (("dotdot", "tests/stage00/../../NOTES.md"), ("symlink", "tests/stage00/ev.md"), ("control", "NOTES.md")):
    d = W / "exp" / f"gate_{case}"
    if d.exists(): shutil.rmtree(d)
    sb = Sandbox(d)
    shutil.copy(CLONE / ".gitattributes", d / ".gitattributes")
    sb.write("NOTES.md", "gate evidence v1: all gates pass\n")
    (d / "tests/stage00").mkdir(parents=True)
    os.symlink("../../NOTES.md", d / "tests/stage00/ev.md")
    sb.commit("notes + owned symlink")
    for t in (Status.AUTHORIZED, Status.IN_PROGRESS):
        assert sb.go("00", t).allowed
    rev = sb.commit("impl")
    assert sb.go("00", Status.IMPLEMENTED_NOT_VERIFIED, revision=rev).allowed
    sb.write_evidence("00", rev)
    gates = {g["id"]: {"result": "pass", "evidence": [ref]} for g in sb.orc().stage("00")["acceptance_gates"]}
    r = sb.go("00", Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE, gates=gates, ci=sb.ci(rev))
    print(f"[{case}] gate evidence {ref!r}: verify {'ALLOWED' if r.allowed else 'REJECTED'}",
          sorted({f.code for f in r.findings if f.severity == 'error'}))
    if not r.allowed:
        continue
    sb.commit("verify")
    check(d, f"{case}: after verification")
    sb.write("NOTES.md", "gate evidence v2: REWRITTEN AFTER VERIFICATION, gates actually failed\n")
    sb.commit("rewrite the cited evidence")
    print("diff of owned paths since verified revision:", git(d, "diff", "--name-only", rev, "HEAD", "--", *sb.orc().stage("00")["owned_paths"]) or "(none)")
    check(d, f"{case}: after rewriting NOTES.md")
