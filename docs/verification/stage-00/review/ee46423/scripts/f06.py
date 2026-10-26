import sys
sys.path.insert(0, "/tmp/claude-0/-home-user-citerift/0bbaf0e6-71eb-560d-84bf-668fa4ffb288/scratchpad/review/scripts")
from lib import *
FIELDS = "- Status: open\n- Severity: critical\n- Kind: defect\n- Stage: 00\n\nBody.\n"
cases = {
 "em dash (control)": "## R-016 — Critical defect\n" + FIELDS,
 "ASCII hyphen": "## R-016 - Critical defect\n" + FIELDS,
 "en dash after id": "## R-016 – Critical defect\n" + FIELDS,
 "level 3": "### R-016 — Critical defect\n" + FIELDS,
 "Stage: project": "## R-016 — Critical defect\n" + FIELDS.replace("Stage: 00", "Stage: project"),
 "duplicate Status": "## R-016 — Critical defect\n" + FIELDS.replace("- Kind", "- Status: closed\n- Kind"),
 "en dash inside id (R–016)": "## R–016 — Critical defect\n" + FIELDS,
 "non-breaking hyphen inside id (R‑016)": "## R‑016 — Critical defect\n" + FIELDS,
 "underscore id (R_016)": "## R_016 — Critical defect\n" + FIELDS,
 "fullwidth R": "## Ｒ-016 — Critical defect\n" + FIELDS,
 "setext heading": "R-016 — Critical defect\n----------------------\n" + FIELDS,
 "html heading": "<h2>R-016 — Critical defect</h2>\n\n" + FIELDS,
 "bold heading text": "## **R-016 — Critical defect**\n" + FIELDS,
}
for label, text in cases.items():
    e = mk("f06_" + "".join(c if c.isalnum() else "_" for c in label)[:40])
    p = e / "RISKS.md"; p.write_text(p.read_text() + "\n" + text); commit(e, "x")
    rc, out = check(e, "F-06 " + label)
# DECISIONS topic variants
DEC = "\n## D-002 — Second decision\n- Status: accepted\n- Topic: {t}\n- Date: 2026-10-25\n- Stage: 00\n- Supersedes: none\n\nBody.\n"
for t in ("Sandbox", "SANDBOX ", "sand_box", "sand box", "sand-box", "ｓandbox"):
    e = mk("f06_topic_" + "".join(c if c.isalnum() else "_" for c in t))
    p = e / "DECISIONS.md"; p.write_text(p.read_text() + DEC.format(t=t)); commit(e, "x")
    check(e, f"F-06 topic {t!r} against existing accepted topic 'sandbox'")
