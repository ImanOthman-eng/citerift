"""Inputs that still end in a Python traceback instead of a named error (V-10 residuals)."""
import json, sys
sys.path.insert(0, "/tmp/claude-0/-home-user-citerift/0bbaf0e6-71eb-560d-84bf-668fa4ffb288/scratchpad/review4/scripts/orig_x")
from lib import *

def run(root, label, *args):
    code, out = gov(root, *args)
    tb = "Traceback" in out
    last = out.strip().splitlines()[-1] if out.strip() else ""
    print(f"[{label}] exit {code} {'TRACEBACK: ' + last if tb else 'named: ' + out.splitlines()[0][:150]}")

# 1. real repository copy, PROJECT_STATUS.md not UTF-8
d = mk("tb_status", base=CLONE); git(d, "checkout", "-q", "97b2051")
with open(d / "PROJECT_STATUS.md", "ab") as fh: fh.write(b"\xff\n")
run(d, "PROJECT_STATUS.md not UTF-8: check", "check")
run(d, "PROJECT_STATUS.md not UTF-8: render-status --check", "render-status", "--check")
run(d, "PROJECT_STATUS.md not UTF-8: recover", "recover")
# 2. unknown stage ids on the real copy
d2 = mk("tb_ids", base=CLONE); git(d2, "checkout", "-q", "97b2051")
for args in (("deps", "99"), ("readiness", "99"), ("handoff", "99"), ("blocker", "add", "99", "x"),
             ("amend", "99", "--kind", "correction", "--reason", "0123456789x", "--evidence", "README.md", "--owner-ref", "cmsg_ABCDEFGHIJK1")):
    run(d2, " ".join(args[:2]) + " (unknown stage)", *args)
# 3. registry schema valid JSON but not a usable schema
for name, text in (("type5", '{"type": 5}'), ("list", "[]"), ("badref", '{"$ref": "#/nope"}')):
    d3 = mk(f"tb_schema_{name}", base=CLONE); git(d3, "checkout", "-q", "97b2051")
    (d3 / "schemas/governance/stage_registry.schema.json").write_text(text)
    run(d3, f"schema {text}: check", "check")
# 4. accepted sandbox: HANDOFF.md not UTF-8; amendment test report missing; --record with a list
d4 = mk("tb_handoff")
with open(d4 / "docs/verification/stage-00/HANDOFF.md", "ab") as fh: fh.write(b"\xff\n")
run(d4, "HANDOFF.md not UTF-8 (verified stage): check", "check")
d5 = mk("tb_amend")
run(d5, "amend --test-report missing file", "amend", "00", "--kind", "correction", "--reason", "0123456789x",
    "--evidence", "NOTES.md", "--owner-ref", "cmsg_ABCDEFGHIJK1", "--test-report", "docs/verification/stage-00/nope.json")
(d5 / "rec.json").write_text('{"gates": []}')
run(d5, "--record with gates as a list", "transition", "02", "AUTHORIZED", "--actor", "owner", "--owner-ref", "cmsg_ABCDEFGHIJK1", "--reason", "x", "--record", str(d5 / "rec.json"))
(d5 / "rec2.json").write_text('[1]')
run(d5, "--record that is a JSON list", "transition", "02", "AUTHORIZED", "--actor", "owner", "--owner-ref", "cmsg_ABCDEFGHIJK1", "--reason", "x", "--record", str(d5 / "rec2.json"))
# 5. accepted sandbox: test report with a non-numeric count
d6 = mk("tb_report")
p = d6 / "docs/verification/stage-00/test-report.json"; rep = json.loads(p.read_text())
rep["totals"]["passed"] = "many"; p.write_text(json.dumps(rep))
run(d6, "test report totals.passed is a string: check", "check")
rep["totals"]["passed"] = 80; rep["suites"]["unit"] = [1]; p.write_text(json.dumps(rep))
run(d6, "test report suite counts are a list: check", "check")
