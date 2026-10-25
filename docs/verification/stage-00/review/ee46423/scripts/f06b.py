import sys
sys.path.insert(0, "/tmp/claude-0/-home-user-citerift/0bbaf0e6-71eb-560d-84bf-668fa4ffb288/scratchpad/review/scripts")
from lib import *
DEC = "\n## D-00{n} — Decision {n}\n- Status: accepted\n- Topic: {t}\n- Date: 2026-10-25\n- Stage: 00\n- Supersedes: none\n\nBody.\n"
pairs = [("python-version", "python_version"), ("python-version", "python version"), ("python-version", "Python‑version"), ("python-version", "ｐython-version")]
for i, (a, b) in enumerate(pairs):
    e = mk(f"f06_topicpair{i}")
    p = e / "DECISIONS.md"; p.write_text(p.read_text() + DEC.format(n=2, t=a) + DEC.format(n=3, t=b)); commit(e, "x")
    check(e, f"F-06 topics {a!r} and {b!r} both accepted")
