"""Y-07: the X-13 rule "an amendment must cite an owner statement not cited before" compares
self-chosen timestamps. An enhancement amendment that reuses the acceptance's owner reference is
refused with the default time (control), but accepted when its time (`amend --at`) is the
acceptance's second, or back-dated to a time between verification and acceptance."""
import json

from lib import new_sandbox, codes
from citerift.governance.model import Status
from citerift.governance.orchestrator import GovernanceError

for label in ("default time (control)", "same second as the acceptance", "back-dated between verification and acceptance"):
    sb = new_sandbox("y12")
    sb.drive_to_verified("00")
    between = [sb.tick() for _ in range(3)][1]          # a second strictly after the verification
    assert sb.go("00", Status.ACCEPTED_CLOSED).allowed
    sb.commit("accept")
    reg = sb.registry()
    acc = reg["stages"][0]["acceptance"]
    sb.write("src/citerift/governance/enh.py", "y = 2\n")
    rev2 = sb.commit("enhancement")
    report = {"format": "citerift.test-report/1", "revision": rev2, "dirty": False, "exit_status": 0,
              "totals": {"passed": 80}, "selection": {"args": ["tests"], "deselected": 0, "complete": True},
              "suites": {s: {"passed": 10} for s in reg["stages"][0]["required_test_suites"]}}
    sb.write("docs/enh-report.json", json.dumps(report))
    at = {"default time (control)": None, "same second as the acceptance": acc["recorded_at"]}.get(label, between)
    try:
        aid = sb.orc().add_amendment("00", kind="enhancement", reason="enhancement reusing the acceptance reference",
                                     evidence_refs=["docs/enh-report.json"], owner_ref=acc["owner_ref"],
                                     revision=rev2, test_report="docs/enh-report.json", at=at)
        sb.commit("amend")
        print(f"{label}: recorded {aid} at {at} citing the acceptance's {acc['owner_ref']};",
              "check errors:", codes(sb.orc().check()) or "none")
    except GovernanceError as exc:
        print(f"{label}: REFUSED", sorted({f.code for f in exc.findings}))
    print("   verification at", reg["stages"][0]["verification"]["recorded_at"], "| acceptance at", acc["recorded_at"])
