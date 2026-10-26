"""Accepted Stage 00: contract weakened through an enhancement amendment that reuses the acceptance's owner_ref."""
import json, sys
sys.path.insert(0, "/tmp/claude-0/-home-user-citerift/0bbaf0e6-71eb-560d-84bf-668fa4ffb288/scratchpad/review2/scripts")
from lib import *
d = mk("enhancement")
acc_ref = reg(d)["stages"][0]["acceptance"]["owner_ref"]
p = d / "schemas/contracts/v1/investigation.schema.json"; s = p.read_text()
s = s.replace('"enum": ["retracted", "expression_of_concern", "correction", "reinstated", "not_found_in_checked_sources", null]',
              '"enum": ["retracted", "not_retracted", "expression_of_concern", "correction", "reinstated", "not_found_in_checked_sources", null]', 1)
assert "not_retracted" in s; p.write_text(s)
rev = commit(d, "contracts: allow not_retracted (no version change)")
check(d, "owned contract changed, no amendment")
rep = json.loads((d / "docs/verification/stage-00/test-report.json").read_text()); rep["revision"] = rev
rep_rel = "docs/verification/stage-00/enhancement-report.json"; (d / rep_rel).write_text(json.dumps(rep, indent=2))
code, out = gov(d, "amend", "00", "--kind", "enhancement", "--reason", "small enhancement of the contract",
                "--evidence", rep_rel, "--owner-ref", acc_ref, "--revision", rev, "--test-report", rep_rel)
print("amend (reusing the acceptance owner_ref", acc_ref + "):", code, out)
commit(d, "record enhancement")
check(d, "after the enhancement amendment")
print("Stage 00 status:", reg(d)["stages"][0]["status"], "| ci in amendment record:", "ci" in reg(d)["stages"][0]["amendments"][0])
from citerift.contracts import load_contracts
cs = load_contracts(d / "schemas/contracts/v1")
base = json.loads((CLONE / "tests/stage00/fixtures/contracts/v1/valid/investigation_full.json").read_text())
base["subject_paper"]["retraction_status"] = {"status": "verified_fact", "value": "not_retracted", "provenance": [{"source_id": "retraction-watch", "locator": "x", "retrieved_at": "2026-01-01T00:00:00Z"}]}
print("record stating 'not_retracted' as verified fact under the accepted contract:", "VALID" if not cs.validate(base) else cs.validate(base)[0])
