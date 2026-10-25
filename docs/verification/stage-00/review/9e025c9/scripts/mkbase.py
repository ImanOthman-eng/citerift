"""Base sandbox: Stage 00 and 01 driven to ACCEPTED_CLOSED by citerift-gov's own propose/apply (R's sandbox_repo)."""
import sys, shutil
from pathlib import Path
CLONE = Path(sys.argv[1]); dest = Path(sys.argv[2])
sys.path.insert(0, str(CLONE / "tests/stage00"))
from sandbox_repo import Sandbox
sb = Sandbox(dest)
shutil.copy(CLONE / ".gitattributes", dest / ".gitattributes")
sb.write("NOTES.md", "notes v1\n")
sb.commit("add gitattributes and NOTES.md")
r00 = sb.drive_to_accepted("00")
r01 = sb.drive_to_accepted("01")
print("00 verified", r00, "01 verified", r01, "HEAD", sb.head(), "clock", sb.clock)
