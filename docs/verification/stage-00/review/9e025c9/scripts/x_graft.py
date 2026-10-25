"""Rewritten history (orphan commit with the same tree) hides REVISION_NOT_IN_HISTORY once a graft file is added."""
import sys
sys.path.insert(0, "/tmp/claude-0/-home-user-citerift/0bbaf0e6-71eb-560d-84bf-668fa4ffb288/scratchpad/review2/scripts")
from lib import *
d = mk("graft_check")
old = git(d, "rev-parse", "HEAD")
git(d, "checkout", "-q", "--orphan", "rewritten"); git(d, "commit", "-q", "-m", "squashed history")
new = git(d, "rev-parse", "HEAD")
code, out = gov(d, "check"); print("orphan HEAD:", out.splitlines()[0], sorted({l.split()[1].rstrip(':') for l in out.splitlines()[1:]}))
(d / ".git/info/grafts").write_text(f"{new} {old}\n")
code, out = gov(d, "check"); print("orphan HEAD + .git/info/grafts:", out.splitlines()[0])
