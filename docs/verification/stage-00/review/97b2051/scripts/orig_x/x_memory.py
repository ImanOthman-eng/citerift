"""V-06 variants on the accepted sandbox: topic spellings and defect entry forms."""
import sys
sys.path.insert(0, "/tmp/claude-0/-home-user-citerift/0bbaf0e6-71eb-560d-84bf-668fa4ffb288/scratchpad/review4/scripts/orig_x")
from lib import *

DEC = "\n## D-0{n:02d} — Variant decision\n- Status: accepted\n- Topic: {t}\n- Date: 2026-10-25\n- Stage: 00\n- Supersedes: none\n\nBody.\n"
for label, topic in (("control 'Sandbox'", "Sandbox"), ("ZWSP 'sand\\u200bbox'", "sand​box"),
                     ("soft hyphen 'sand\\u00adbox'", "sand­box"), ("Cyrillic a 's\\u0430ndbox'", "sаndbox"),
                     ("dot 'sand.box'", "sand.box")):
    d = mk("mem_topic")
    with open(d / "DECISIONS.md", "a", encoding="utf-8") as fh:
        fh.write(DEC.format(n=2, t=topic))
    code, out = gov(d, "check")
    print(f"[topic {label}] exit {code}: {out.splitlines()[0]} {'DECISION_CONTRADICTION' if 'CONTRADICTION' in out else ''}")

DEF = {
  "control": "\n## R-020 — Critical defect\n- Status: open\n- Severity: critical\n- Kind: defect\n- Stage: 00\n",
  "bullet '*'": "\n## R-020 — Critical defect\n* Status: open\n* Severity: critical\n* Kind: defect\n* Stage: 00\n",
  "bold fields": "\n### R–020 — Critical defect\n- **Status**: open\n- **Severity**: critical\n- **Kind**: defect\n- **Stage**: 00\n",
  "lowercase fields, en dash heading": "\n## R–020 — Critical defect\n- status: open\n- severity: critical\n- kind: defect\n- stage: 00\n",
  "indented fields, setext heading": "\nR-020 — Critical defect\n-----------------------\n  - Status: open\n  - Severity: critical\n  - Kind: defect\n  - Stage: 00\n",
  "table row": "\n| R-020 | Critical defect | open | critical | defect | 00 |\n",
}
for label, text in DEF.items():
    d = mk("mem_defect")
    with open(d / "RISKS.md", "a", encoding="utf-8") as fh:
        fh.write(text)
    code, out = gov(d, "check")
    codes = sorted({l.split(":")[0].strip().split()[-1] for l in out.splitlines()[1:] if l.strip().startswith("ERROR")})
    print(f"[defect {label}] exit {code}: {out.splitlines()[0]} {codes}")
