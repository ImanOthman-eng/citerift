"""Y-06: `check` accepts an enhancement amendment recorded on a stage that is only verified
(not accepted). The CLI refuses to write one (AMENDMENT_NOT_APPLICABLE), but a hand-written one
passes every check and then covers owned-path drift, so the owner can accept "the verified
revision" while the owned code at HEAD is a different, unverified-by-CI revision."""
import json

from lib import new_sandbox, codes
from citerift.governance import evidence
from citerift.governance.model import Status
from citerift.governance.orchestrator import GovernanceError

sb = new_sandbox("y06")
rev = sb.drive_to_verified("00")
sb.write("src/citerift/governance/changed_after_verification.py", "BEHAVIOUR = 'different'\n")
rev2 = sb.commit("change owned code after verification")
print("control, owned change after verification:", codes(sb.orc().check()))
try:
    sb.orc().add_amendment("00", kind="enhancement", reason="enhancement before acceptance",
                           evidence_refs=["docs/x.md"], owner_ref=sb.new_ref(), revision=rev2)
except GovernanceError as exc:
    print("CLI path refuses:", [f.code for f in exc.findings])
report = {"format": "citerift.test-report/1", "revision": rev2, "dirty": False, "exit_status": 0,
          "totals": {"passed": 80}, "selection": {"args": ["tests"], "deselected": 0, "complete": True},
          "suites": {s: {"passed": 10} for s in sb.orc().stage("00")["required_test_suites"]}}
sb.write("docs/amendments/enh-report.json", json.dumps(report))
reg = sb.registry()
reg["stages"][0]["amendments"].append({
    "id": "A-00-001", "kind": "enhancement", "reason": "hand-written enhancement on a verified stage",
    "evidence": ["docs/amendments/enh-report.json"], "owner_ref": sb.new_ref(), "revision": rev2,
    "test_report": {"path": "docs/amendments/enh-report.json",
                    "sha256": evidence.sha256_file(sb.root / "docs/amendments/enh-report.json")},
    "recorded_at": sb.tick()})
sb.save_registry(reg)
sb.orc().write()
sb.commit("hand-written amendment")
print("stage status:", sb.orc().stage("00")["status"], "| check errors:", codes(sb.orc().check()) or "none")
r = sb.go("00", Status.ACCEPTED_CLOSED)
print("owner acceptance of", rev[:12], "with owned code at", rev2[:12], ": allowed =", r.allowed, codes(r.findings))
