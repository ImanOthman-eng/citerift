"""Original V-10 and V-12 reproductions against R."""
import sys
sys.path.insert(0, "/tmp/claude-0/-home-user-citerift/0bbaf0e6-71eb-560d-84bf-668fa4ffb288/scratchpad/review4/scripts/orig_x")
from lib import *
def run(root, label, *args):
    code, out = gov(root, *args)
    print(f"[{label}] exit {code} {'TRACEBACK ' + out.splitlines()[-1] if 'Traceback' in out else out.splitlines()[0][:170]}")
d = mk("v10_schema_deleted", base=CLONE); git(d, "checkout", "-q", "97b2051"); (d / "schemas/governance/stage_registry.schema.json").unlink()
run(d, "schema deleted: check", "check")
d = mk("v10_schema_trunc", base=CLONE); git(d, "checkout", "-q", "97b2051"); p = d / "schemas/governance/stage_registry.schema.json"; p.write_text(p.read_text()[:500])
run(d, "schema truncated: recover", "recover")
d = mk("v10_empty", base=CLONE); git(d, "checkout", "-q", "97b2051"); (d / "governance/stage_registry.json").write_text("{}")
run(d, "registry {}: check", "check"); run(d, "registry {}: recover", "recover"); run(d, "registry {}: status", "status")
d = mk("v10_risks", base=CLONE); git(d, "checkout", "-q", "97b2051")
with open(d / "RISKS.md", "ab") as fh: fh.write(b"\xff")
run(d, "RISKS.md 0xff: check", "check")
# V-12: nested .gitattributes on the accepted sandbox, then a fresh clone
d = mk("v12_nested")
(d / "docs/.gitattributes").write_text("*.md text eol=crlf\n"); commit(d, "nested attributes")
run(d, "nested docs/.gitattributes: check (same tree)", "check")
c = W / "exp/v12_nested_clone"; sh("rm", "-rf", c); sh("git", "clone", "-q", d, c)
code, out = gov(c, "check"); print("[nested .gitattributes: fresh clone]", out.splitlines()[0], sorted({l.split()[1].rstrip(':') for l in out.splitlines()[1:] if l.strip()}))
