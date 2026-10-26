"""V-06 original heading and topic forms (first final review) against memory.check_risks / check_decisions."""
import os, sys, tempfile
from pathlib import Path
W = Path(os.environ["W"]); sys.path.insert(0, str(W / "base/src"))
from citerift.governance import memory
F = "- Status: open\n- Severity: critical\n- Kind: defect\n- Stage: 00\n"
for label, head in (("control ## R-016 —", "## R-016 — Critical defect\n"), ("en dash in id", "## R–016 — Critical defect\n"),
                    ("non-breaking hyphen", "## R‑016 — Critical defect\n"), ("underscore", "## R_016 — Critical defect\n"),
                    ("fullwidth R", "## Ｒ-016 — Critical defect\n"), ("setext", "R-016 — Critical defect\n-----------------------\n"),
                    ("html", "<h2>R-016 — Critical defect</h2>\n")):
    p = Path(tempfile.mkdtemp(dir=W)) / "RISKS.md"; p.write_text("# Risks\n\n" + head + F, encoding="utf-8")
    e, pr = memory.check_risks(p)
    print(f"{label}: problems={sorted({x.code for x in pr})} blocks 00={[x.id for x in memory.open_critical_defects(e, '00')]}")
for b in ("python version", "Python‑version", "ｐython-version", "python_version"):
    p = Path(tempfile.mkdtemp(dir=W)) / "DECISIONS.md"
    p.write_text("# D\n" + "".join(f"\n## D-00{i} — t\n- Status: accepted\n- Topic: {t}\n" for i, t in ((1, "python-version"), (2, b))), encoding="utf-8")
    print(f"topic python-version vs {b!r}:", sorted({x.code for x in memory.check_decisions(p)[1]}) or "no problem")
