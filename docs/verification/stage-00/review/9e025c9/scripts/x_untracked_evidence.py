"""An OS metadata file in the evidence directory of a verified stage (owner opens the folder in Finder)."""
import sys
sys.path.insert(0, "/tmp/claude-0/-home-user-citerift/0bbaf0e6-71eb-560d-84bf-668fa4ffb288/scratchpad/review2/scripts")
from lib import *
d = mk("dsstore")
(d / "docs/verification/stage-00/.DS_Store").write_bytes(b"\x00\x00\x00\x01Bud1")
check(d, "untracked .DS_Store in docs/verification/stage-00 (nothing committed)")
