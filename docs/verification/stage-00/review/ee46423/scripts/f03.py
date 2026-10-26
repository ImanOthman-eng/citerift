import sys, json, subprocess
sys.path.insert(0, "/tmp/claude-0/-home-user-citerift/0bbaf0e6-71eb-560d-84bf-668fa4ffb288/scratchpad/review/scripts")
from lib import *
POL = str(CLONE / "docs/audits/stage-00-2026-10-25/scripts/policy_edit.py")
for name in ("drop_ci", "shrink_gates", "drop_owned_paths", "gate_dot"):
    e = mk("f03_" + name)
    sh(PY, POL, str(e), name); sh(GOV, "--root", str(e), "render-status", "--write")
    if name == "drop_owned_paths":
        commit(e, "registry edit")
        p = e / "schemas/contracts/v1/common.schema.json"; p.write_text(p.read_text().replace('"title"', '"title" ', 1))
    commit(e, name)
    rc, out = check(e, f"F-03 original policy_edit.py {name}")
# single_active_flip (sandbox script from the audit)
r = sh(PY, str(CLONE / "docs/audits/stage-00-2026-10-25/scripts/single_active_flip.py"), str(CLONE), str(W / "exp"), check=False)
print("--- F-03 original single_active_flip.py [exit", r.returncode, "]\n", r.stdout, r.stderr[-1500:])
