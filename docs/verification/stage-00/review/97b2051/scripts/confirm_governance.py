"""Confirmation probes (sandboxes built with the repository's own tests/stage00/sandbox_repo.py) for V, X and Y
findings in the orchestrator and memory parser, with close variants of each original attack."""
import json, os, subprocess, tempfile
from pathlib import Path
from lib import BASE, PY, W, new_sandbox, run, codes
from citerift.governance import evidence, memory
from citerift.governance.model import Status, Actor
from citerift.governance.orchestrator import GovernanceError

def hdr(s): print(f"\n### {s}")

def implemented(name, setup=None):
    sb = new_sandbox(name)
    if setup: setup(sb)
    for t in (Status.AUTHORIZED, Status.IN_PROGRESS):
        assert sb.go("00", t).allowed
    sb.write("impl/00.txt", "x\n")
    rev = sb.commit("impl")
    assert sb.go("00", Status.IMPLEMENTED_NOT_VERIFIED, revision=rev).allowed
    sb.write_evidence("00", rev)
    return sb, rev

def verify(sb, rev, gates=None, ci=None, apply=False):
    return sb.go("00", Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE, gates=gates or sb.gates("00"), ci=ci or sb.ci(rev), apply=apply)

def enh_report(sb, rev, rel):
    rep = {"format": "citerift.test-report/1", "revision": rev, "dirty": False, "exit_status": 0,
           "totals": {"passed": 80}, "selection": {"args": ["tests"], "deselected": 0, "complete": True},
           "suites": {s: {"passed": 10} for s in sb.orc().stage("00")["required_test_suites"]}}
    sb.write(rel, json.dumps(rep))

# ---------------------------------------------------------------- V-02
hdr("V-02 gate evidence: URL only; one pinned plus one unpinned file")
sb, rev = implemented("v02")
sb.write("NOTES.md", "n" * 400); sb.commit("notes")
for label, ev in (("URL only", ["https://example.org/x"]),
                  ("HANDOFF.md + NOTES.md", ["docs/verification/stage-00/HANDOFF.md", "NOTES.md"])):
    g = {k: {"result": "pass", "evidence": ev} for k in sb.gates("00")}
    r = verify(sb, rev, gates=g); print(f"  {label}: allowed={r.allowed} {codes(r.findings)}")

# ---------------------------------------------------------------- V-05 / V-07 / V-08 / V-09
hdr("V-05 correction test report added to the evidence directory")
sb = new_sandbox("v05"); sb.drive_to_accepted("00")
sb.write("docs/verification/stage-00/late.json", "{}")
try:
    sb.orc().add_amendment("00", kind="correction", reason="correction with late evidence", evidence_refs=["NOTES.md"],
                           owner_ref=sb.new_ref(), test_report="docs/verification/stage-00/late.json", at=sb.tick())
    sb.commit("amend")
    print("  check:", codes(sb.orc().check(include_status_doc=False)))
except GovernanceError as e:
    print("  refused:", sorted({f.code for f in e.findings}))

hdr("V-07 case 3 / V-08: acceptance citing the amendment's reference; second reopening with one amendment")
sb = new_sandbox("v07"); sb.drive_to_accepted("00")
ref = sb.new_ref()
aid = sb.orc().add_amendment("00", kind="correction", reason="correction needed here", evidence_refs=["RISKS.md"], owner_ref=ref, at=sb.tick())
r = sb.go("00", Status.IN_PROGRESS, actor=Actor.OWNER, owner_ref=sb.new_ref(), amendment=aid); print("  reopen:", r.allowed, codes(r.findings))
sb.commit("reopen")
for t in (Status.IMPLEMENTED_NOT_VERIFIED,):
    sb.write("impl/00.txt", "y\n"); rev2 = sb.commit("fix")
    assert sb.go("00", t, revision=rev2).allowed
sb.write_evidence("00", rev2)
assert verify(sb, rev2, apply=True).allowed; sb.commit("re-verify")
r = sb.go("00", Status.ACCEPTED_CLOSED, owner_ref=ref, apply=False); print("  accept citing the amendment ref:", r.allowed, codes(r.findings))
assert sb.go("00", Status.ACCEPTED_CLOSED).allowed; sb.commit("re-accept")
r = sb.go("00", Status.IN_PROGRESS, actor=Actor.OWNER, owner_ref=sb.new_ref(), amendment=aid, apply=False)
print("  second reopening with the same amendment:", r.allowed, codes(r.findings))

hdr("V-09 duplicate amendment and blocker ids (hand edit)")
sb = new_sandbox("v09"); sb.drive_to_accepted("00")
reg = sb.registry()
a = {"id": "A-00-001", "kind": "correction", "reason": "a reason here", "evidence": ["RISKS.md"], "owner_ref": "cmsg_X1",
     "revision": None, "test_report": None, "recorded_at": sb.tick()}
reg["stages"][0]["amendments"] += [a, {**a, "owner_ref": "cmsg_X2"}]
reg["stages"][2]["blockers"] += [{"id": "B-02-001", "description": "d", "opened_at": sb.tick(), "resolved_at": None, "resolution": None}] * 2
sb.save_registry(reg); print("  check:", codes(sb.orc().check(include_status_doc=False)))

# ---------------------------------------------------------------- V-13 / X-09
hdr("V-13 git replace hides drift")
sb = new_sandbox("v13"); rev = sb.drive_to_accepted("00")
sb.write("src/citerift/governance/tamper.py", "t\n"); sb.commit("tamper owned")
before = codes(sb.orc().check(include_status_doc=False))
tree = subprocess.run(["git", "-C", str(sb.root), "rev-parse", "HEAD^{tree}"], capture_output=True, text=True).stdout.strip()
fake = subprocess.run(["git", "-C", str(sb.root), "commit-tree", tree, "-p", rev + "^", "-m", "fake"], capture_output=True, text=True,
                      env={**os.environ, "GIT_AUTHOR_NAME": "r", "GIT_AUTHOR_EMAIL": "r@x", "GIT_COMMITTER_NAME": "r", "GIT_COMMITTER_EMAIL": "r@x"}).stdout.strip()
subprocess.run(["git", "-C", str(sb.root), "replace", rev, fake], check=True)
print("  before replace:", before, "| after replace:", codes(sb.orc().check(include_status_doc=False)))

# ---------------------------------------------------------------- X-04
hdr("X-04 module beside the package in src")
sb = new_sandbox("x04"); sb.write("src/citerift/__init__.py", ""); sb.write("src/sitecustomize.py", "x = 1\n"); sb.commit("shim")
print("  check:", codes(sb.orc().check(include_status_doc=False)))
print("  CI guard step exit:", subprocess.run(["sh", "-c", 'test "$(ls -A src)" = "citerift"'], cwd=sb.root).returncode)

# ---------------------------------------------------------------- Y-04 variants
hdr("Y-04 variants (memory)")
def risks(text):
    p = Path(tempfile.mkdtemp(dir=W)) / "RISKS.md"; p.write_text("# Risks\n" + text, encoding="utf-8")
    e, pr = memory.check_risks(p); return [x.id for x in e], sorted({x.code for x in pr}), e
CRIT = "- Status: open\n- Severity: critical\n- Kind: defect\n- Stage: {s}\n"
for label, head, stage in (("id in Arabic-Indic digits", "## R-٠٠٢ — t\n", "00"),
                           ("id in fullwidth digits", "## R-００２ — t\n", "00"),
                           ("id in superscript digits", "## R-⁰⁰² — t\n", "00"),
                           ("Stage mixed '00, ٠٢'", "## R-002 — t\n", "00, ٠٢"),
                           ("Stage '02,00' (no space)", "## R-002 — t\n", "02,00"),
                           ("Stage Arabic-Indic '٠٠' (original)", "## R-002 — t\n", "٠٠")):
    ids, pr, e = risks("\n" + head + CRIT.format(s=stage))
    print(f"  {label}: ids={ids} problems={pr} blocks 00={[x.id for x in memory.open_critical_defects(e, '00')]}")
p = Path(tempfile.mkdtemp(dir=W)) / "DECISIONS.md"
p.write_text("# D\n\n## D-٠٠١ — t\n- Status: accepted\n- Topic: x\n", encoding="utf-8")
print("  DECISIONS id in Arabic-Indic digits:", sorted({x.code for x in memory.check_decisions(p)[1]}))

# ---------------------------------------------------------------- Y-06 variants
hdr("Y-06 variants")
# a) back-dated hand-written enhancement on an ACCEPTED stage, covering owned drift
sb = new_sandbox("y06a"); sb.drive_to_verified("00")
between = [sb.tick() for _ in range(3)][1]
assert sb.go("00", Status.ACCEPTED_CLOSED).allowed; sb.commit("accept")
sb.write("src/citerift/governance/enh.py", "e = 1\n"); rev2 = sb.commit("owned change")
enh_report(sb, rev2, "docs/enh.json")
reg = sb.registry()
reg["stages"][0]["amendments"].append({"id": "A-00-001", "kind": "enhancement", "reason": "back-dated enhancement",
    "evidence": ["docs/enh.json"], "owner_ref": sb.new_ref(), "revision": rev2,
    "test_report": {"path": "docs/enh.json", "sha256": evidence.sha256_file(sb.root / "docs/enh.json")}, "recorded_at": between})
sb.save_registry(reg); sb.commit("amend")
print("  a) back-dated (between verification and acceptance):", codes(sb.orc().check(include_status_doc=False)))
# b) enhancement of an earlier acceptance does not cover after reopen and re-acceptance
sb = new_sandbox("y06b"); sb.drive_to_accepted("00")
sb.write("src/citerift/governance/enh.py", "e = 1\n"); rev2 = sb.commit("owned change v1")
enh_report(sb, rev2, "docs/enh.json")
sb.orc().add_amendment("00", kind="enhancement", reason="enhancement one here", evidence_refs=["docs/enh.json"],
                       owner_ref=sb.new_ref(), revision=rev2, test_report="docs/enh.json", at=sb.tick()); sb.commit("enh")
print("  b) enhancement covers its change:", codes(sb.orc().check(include_status_doc=False)) or "0 errors")
aid = sb.orc().add_amendment("00", kind="correction", reason="correction needed now", evidence_refs=["RISKS.md"], owner_ref=sb.new_ref(), at=sb.tick())
assert sb.go("00", Status.IN_PROGRESS, actor=Actor.OWNER, owner_ref=sb.new_ref(), amendment=aid).allowed
sb.write("src/citerift/governance/enh.py", "e = 2\n"); rev3 = sb.commit("fix v2")
assert sb.go("00", Status.IMPLEMENTED_NOT_VERIFIED, revision=rev3).allowed
sb.write_evidence("00", rev3); assert verify(sb, rev3, apply=True).allowed; sb.commit("re-verify")
assert sb.go("00", Status.ACCEPTED_CLOSED).allowed; sb.commit("re-accept")
sb.write("src/citerift/governance/enh.py", "e = 1\n"); sb.commit("owned content back to the old enhancement's revision")
print("  b) old enhancement after re-acceptance, owned content = its revision:", codes(sb.orc().check(include_status_doc=False)))

# ---------------------------------------------------------------- Y-07 variants
hdr("Y-07 variants")
sb = new_sandbox("y07"); sb.drive_to_accepted("00")
r1 = sb.new_ref(); t1 = sb.tick()
a1 = sb.orc().add_amendment("00", kind="correction", reason="first correction note", evidence_refs=["RISKS.md"], owner_ref=r1, at=t1)
for label, ref, at in (("same ref as an earlier amendment, same second", r1, t1),
                       ("Stage 00 authorization ref (OWNER_REF), later", "cmsg_TESTOWNERREF0001", None)):
    try:
        sb.orc().add_amendment("00", kind="correction", reason="second correction note", evidence_refs=["RISKS.md"], owner_ref=ref, at=at or sb.tick())
        print(f"  {label}: recorded; check:", codes(sb.orc().check(include_status_doc=False)) or "0 errors")
    except GovernanceError as e:
        print(f"  {label}: REFUSED", sorted({f.code for f in e.findings}))

# ---------------------------------------------------------------- Y-09 variants
hdr("Y-09 variants")
def y09(label, prepare):
    sb, rev = implemented("y09", prepare)
    ev = prepare.ev
    g = {k: {"result": "pass", "evidence": [ev]} for k in sb.gates("00")}
    r = verify(sb, rev, gates=g); print(f"  {label}: allowed={r.allowed} {codes(r.findings)}")
def untracked(sb): sb.write("src/citerift/governance/untracked-ev.txt", "u\n")
untracked.ev = "src/citerift/governance/untracked-ev.txt"
y09("written before the implementation commit, so committed by it (control; the untracked case is in confirm_governance2.py)", untracked)
def committed(sb): sb.write("src/citerift/governance/committed-ev.txt", "c\n"); sb.commit("ev")
committed.ev = "src/citerift/governance/committed-ev.txt"
y09("committed before the revision (control)", committed)
sb, rev = implemented("y09c")
sb.write("src/citerift/governance/late-ev.txt", "late\n"); sb.commit("evidence committed after the implementation revision")
g = {k: {"result": "pass", "evidence": ["src/citerift/governance/late-ev.txt"]} for k in sb.gates("00")}
r = verify(sb, rev, gates=g); print(f"  committed only after the verified revision: allowed={r.allowed} {codes(r.findings)}")
def link(sb):
    sb.write("NOTES.md", "n\n"); os.symlink("../../../NOTES.md", sb.root / "src/citerift/governance/ln.md") if (sb.root / "src/citerift/governance").exists() else None
    (sb.root / "src/citerift/governance").mkdir(parents=True, exist_ok=True)
    if not (sb.root / "src/citerift/governance/ln.md").is_symlink(): os.symlink("../../../NOTES.md", sb.root / "src/citerift/governance/ln.md")
    sb.commit("committed symlink")
link.ev = "src/citerift/governance/ln.md"
y09("committed symlink under an owned path", link)

# ---------------------------------------------------------------- Y-10 variants
hdr("Y-10 variants")
sb, rev = implemented("y10")
repo = sb.registry()["project"]["repository"]
for label, url in (("dot segments leading to another repository", f"https://github.com/{repo}/actions/runs/1/../../../../../other-owner/other-repo/actions/runs/2"),
                   ("other case of the same repository (GitHub is case-insensitive)", f"https://github.com/{repo.upper()}/actions/runs/3"),
                   ("prefix-sharing repository name", f"https://github.com/{repo}-fork/actions/runs/4"),
                   ("original: other repository", "https://github.com/someone/else/actions/runs/5")):
    r = verify(sb, rev, ci={"run_url": url, "head_sha": rev, "conclusion": "success"})
    print(f"  {label}: allowed={r.allowed} {codes(r.findings)}")
