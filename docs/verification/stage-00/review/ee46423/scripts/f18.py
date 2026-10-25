import sys, json, re
sys.path.insert(0, "/tmp/claude-0/-home-user-citerift/0bbaf0e6-71eb-560d-84bf-668fa4ffb288/scratchpad/review/scripts")
from lib import *
e = mk("f18_dupkey"); p = e / "governance/stage_registry.json"; t = p.read_text()
i = t.index('"id": "02"'); j = t.index('"status": "NOT_STARTED"', i)
p.write_text(t[:j] + '"status": "ACCEPTED_CLOSED",\n      ' + t[j:]); commit(e, "x")
check(e, "F-18 original: duplicate status key in the registry")
e = mk("f18_escaped"); p = e / "governance/stage_registry.json"; t = p.read_text()
i = t.index('"id": "02"'); j = t.index('"status": "NOT_STARTED"', i)
p.write_text(t[:j] + '"st\\u0061tus": "ACCEPTED_CLOSED",\n      ' + t[j:]); commit(e, "x")
check(e, "F-18 variant: duplicate key spelled with a \\u escape")
e = mk("f18_report"); p = e / "docs/verification/stage-00/test-report.json"; t = p.read_text()
p.write_text(t.replace('"exit_status": 0', '"exit_status": 1, "exit_status": 0', 1)); commit(e, "x")
check(e, "F-18 variant: duplicate key in the test report")
# duplicate amendment ids: two records named A-00-001
e = mk("f18_dupamend"); r = reg(e); s0 = r["stages"][0]
a = {"id": "A-00-001", "kind": "correction", "reason": "first record with this id", "evidence": ["docs/verification/stage-00/HANDOFF.md"],
     "owner_ref": "cmsg_DUPAMENDREF01", "revision": None, "test_report": None, "recorded_at": "2026-01-01T00:01:00Z"}
b = dict(a, kind="enhancement", reason="second record, same id, different kind", revision=s0["verification"]["revision"],
         test_report={"path": "docs/verification/stage-00/test-report.json", "sha256": s0["verification"]["test_report"]["sha256"]})
s0["amendments"] = [a, b]; save(e, r); commit(e, "x")
check(e, "F-18 variant: two amendment records with the same id A-00-001")
# duplicate blocker ids
e = mk("f18_dupblocker"); r = reg(e); s2 = next(s for s in r["stages"] if s["id"] == "02")
s2["blockers"] = [{"id": "B-02-001", "description": "x", "opened_at": "2026-01-01T00:01:00Z", "resolved_at": "2026-01-01T00:02:00Z", "resolution": "done"},
                  {"id": "B-02-001", "description": "y", "opened_at": "2026-01-01T00:01:00Z", "resolved_at": "2026-01-01T00:02:00Z", "resolution": "done"}]
save(e, r); commit(e, "x")
check(e, "F-18 variant: two blocker records with the same id B-02-001")
