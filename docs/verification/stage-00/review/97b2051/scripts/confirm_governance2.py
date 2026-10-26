"""Second batch: corrected Y-09 untracked probe, V-09 with distinct records, Y-11 variants, and regressions
(legitimate flows that must still work), run through the CLI the way CI does where it matters."""
import json, os, subprocess
from pathlib import Path
from lib import BASE, PY, W, new_sandbox, run, codes
from citerift.governance import evidence
from citerift.governance.model import Status, Actor

def hdr(s): print(f"\n### {s}")
def implemented(name):
    sb = new_sandbox(name)
    for t in (Status.AUTHORIZED, Status.IN_PROGRESS):
        assert sb.go("00", t).allowed
    sb.write("impl/00.txt", "x\n"); rev = sb.commit("impl")
    assert sb.go("00", Status.IMPLEMENTED_NOT_VERIFIED, revision=rev).allowed
    sb.write_evidence("00", rev)
    return sb, rev
def verify(sb, rev, gates=None, ci=None, apply=False):
    return sb.go("00", Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE, gates=gates or sb.gates("00"), ci=ci or sb.ci(rev), apply=apply)
def cli(sb, *args):
    r = subprocess.run([PY, "-P", "-m", "citerift.governance.cli", *args], cwd=sb.root, capture_output=True,
                       env={**os.environ, "PYTHONPATH": str(BASE / "src")})
    out = subprocess.CompletedProcess(r.args, r.returncode, r.stdout.decode("utf-8", "backslashreplace"), r.stderr.decode("utf-8", "backslashreplace"))
    tb = "Traceback" in out.stderr
    return out.returncode, ("TRACEBACK " + out.stderr.strip().splitlines()[-1]) if tb else (out.stdout.strip().splitlines() or [""])[0][:200], out

hdr("Y-09 variant: untracked (not ignored) file under an owned path, written after the implementation commit")
sb, rev = implemented("y09u")
sb.write("src/citerift/governance/untracked-ev.txt", "u\n")
g = {k: {"result": "pass", "evidence": ["src/citerift/governance/untracked-ev.txt"]} for k in sb.gates("00")}
r = verify(sb, rev, gates=g); print(f"  allowed={r.allowed} {codes(r.findings)}")

hdr("V-09 distinct duplicate ids")
sb = new_sandbox("v09b"); sb.drive_to_accepted("00")
reg = sb.registry()
a = {"id": "A-00-001", "kind": "correction", "reason": "a reason here", "evidence": ["RISKS.md"], "owner_ref": "cmsg_XDUPLICATE01",
     "revision": None, "test_report": None, "recorded_at": sb.tick()}
reg["stages"][0]["amendments"] += [a, {**a, "owner_ref": "cmsg_XDUPLICATE02", "reason": "another reason"}]
reg["stages"][2]["blockers"] += [{"id": "B-02-001", "description": d, "opened_at": sb.tick(), "resolved_at": None, "resolution": None} for d in ("d1", "d2")]
sb.save_registry(reg); print("  check:", codes(sb.orc().check(include_status_doc=False)))

hdr("Y-11 variants")
# a) untracked file with a non-UTF-8 name at the repository root: recover and check
sb = new_sandbox("y11a")
os.close(os.open(os.fsencode(str(sb.root)) + b"/notes-\xff.md", os.O_CREAT | os.O_WRONLY))
for args in (("recover",), ("--json", "recover"), ("check",), ("status",)):
    c, line, out = cli(sb, *args); print(f"  a) non-UTF-8 untracked name, {' '.join(args)}: exit {c} {line}")
# b) the same name inside tests/ while pytest writes a report (tiny project using the plugin)
# c) deeply nested --record file and deeply nested test report given to check-report
sb, rev = implemented("y11c"); sb.commit("evidence")
(sb.root.parent / "deep.json").write_text("[" * 100000 + "]" * 100000)
c, line, _ = cli(sb, "transition", "00", "VERIFIED_AWAITING_OWNER_ACCEPTANCE", "--actor", "engineering-agent", "--reason", "verify",
                 "--record", str(sb.root.parent / "deep.json"), "--at", sb.tick())
print(f"  c) deeply nested --record: exit {c} {line}")
(sb.root / "deep-report.json").write_text("[" * 100000 + "]" * 100000)
c, line, out = cli(sb, "check-report", "deep-report.json"); print(f"  c) deeply nested report, check-report: exit {c} {line} | {out.stdout.strip().splitlines()[-1][:120]}")
c, line, out = cli(sb, "check-report", "missing.json"); print(f"  c) missing report, check-report: exit {c} {line}")
c, line, out = cli(sb, "check-report", "../outside.json"); print(f"  c) report outside the repository, check-report: exit {c} {line}")
c, line, out = cli(sb, "check-report", "x.json", "--stage", "99"); print(f"  c) unknown stage, check-report: exit {c} {line}")
# d) damaged index: what recover says about uncommitted changes
sb = new_sandbox("y11d"); sb.write("untracked-change.txt", "u\n")
(sb.root / ".git" / "index").write_bytes(b"DIRC garbage")
c, line, out = cli(sb, "recover")
print(f"  d) damaged index, recover: exit {c}; lines:", [l for l in out.stdout.splitlines() if "Uncommitted" in l or "REVISION_UNVERIFIABLE" in l])
c, line, out = cli(sb, "--json", "recover"); print("  d) damaged index, recover --json uncommitted_changes:", json.loads(out.stdout)["uncommitted_changes"])

hdr("Regression: correction amendment and reopening in the same second (CLI, as an owner would record it)")
sb = new_sandbox("reg1"); sb.drive_to_accepted("00"); t = sb.tick()
c, line, out = cli(sb, "amend", "00", "--kind", "correction", "--reason", "behaviour must change", "--evidence", "RISKS.md",
                   "--owner-ref", "cmsg_OWNERCORRECTION01", "--at", t)
print(f"  amend at {t}: exit {c} {line}")
c, line, out = cli(sb, "transition", "00", "IN_PROGRESS", "--actor", "owner", "--owner-ref", "cmsg_OWNERCORRECTION01",
                   "--amendment", "A-00-001", "--reason", "reopen for the correction", "--at", t, "--apply")
print(f"  reopen at the same second, same owner statement: exit {c} {line}")
print("  check:", codes(sb.orc().check(include_status_doc=False)) or "0 errors")

hdr("Regression: legitimate enhancement on an accepted stage (CLI), new owner statement, test report at the new revision")
sb = new_sandbox("reg2"); sb.drive_to_accepted("00")
sb.write("src/citerift/governance/feature.py", "FEATURE = 1\n"); rev2 = sb.commit("enhancement")
rep = {"format": "citerift.test-report/1", "revision": rev2, "dirty": False, "exit_status": 0, "totals": {"passed": 80},
       "selection": {"args": ["tests"], "deselected": 0, "complete": True},
       "suites": {s: {"passed": 10} for s in sb.orc().stage("00")["required_test_suites"]}}
sb.write("docs/amendments/enh-report.json", json.dumps(rep)); sb.commit("report")
print("  before amendment:", codes(sb.orc().check(include_status_doc=False)))
c, line, out = cli(sb, "amend", "00", "--kind", "enhancement", "--reason", "add a feature that keeps contracts",
                   "--evidence", "docs/amendments/enh-report.json", "--owner-ref", "cmsg_OWNERENHANCE0001", "--revision", rev2,
                   "--test-report", "docs/amendments/enh-report.json")
print(f"  amend: exit {c} {line}")
sb.commit("amend")
print("  check after amendment:", codes(sb.orc().check(include_status_doc=False)) or "0 errors")
acc = sb.registry()["stages"][0]["acceptance"]
sb2 = new_sandbox("reg2b"); sb2.drive_to_accepted("00"); acc2 = sb2.registry()["stages"][0]["acceptance"]
sb2.write("src/citerift/governance/feature.py", "FEATURE = 1\n"); rev3 = sb2.commit("enhancement")
rep["revision"] = rev3; sb2.write("docs/amendments/enh-report.json", json.dumps(rep)); sb2.commit("report")
c, line, out = cli(sb2, "amend", "00", "--kind", "enhancement", "--reason", "enhancement in the acceptance second",
                   "--evidence", "docs/amendments/enh-report.json", "--owner-ref", "cmsg_OWNERENHANCE0002", "--revision", rev3,
                   "--test-report", "docs/amendments/enh-report.json", "--at", acc2["recorded_at"])
print(f"  enhancement recorded in the acceptance's own second with a new statement: exit {c} {line}")
sb2.commit("amend"); print("  check:", codes(sb2.orc().check(include_status_doc=False)) or "0 errors")
