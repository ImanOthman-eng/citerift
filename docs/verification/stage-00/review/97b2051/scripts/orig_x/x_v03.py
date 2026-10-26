import sys
sys.path.insert(0, "/tmp/claude-0/-home-user-citerift/0bbaf0e6-71eb-560d-84bf-668fa4ffb288/scratchpad/review4/scripts/orig_x")
from lib import *
for label, edit in (("00 required_artifacts []", lambda s: s[0].update(required_artifacts=[])),
                    ("00 required_artifacts [HANDOFF.md]", lambda s: s[0].update(required_artifacts=["HANDOFF.md"])),
                    ("02 executor external-agent", lambda s: s[2].update(executor="external-agent")),
                    ("02 ci_required false", lambda s: s[2].update(ci_required=False))):
    d = mk("v03"); r = reg(d); edit(r["stages"]); save(d, r, render=False)
    code, out = gov(d, "check"); print(f"[{label}]", out.splitlines()[0], out.splitlines()[1][:150] if len(out.splitlines()) > 1 else "")
