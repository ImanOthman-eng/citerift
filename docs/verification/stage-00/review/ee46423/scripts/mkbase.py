"""Build a base sandbox: Stage 00 and 01 accepted, with .gitattributes. Usage: mkbase.py CLONE DEST"""
import sys, shutil
from pathlib import Path
sys.path.insert(0, sys.argv[1] + "/tests/stage00")
from sandbox_repo import Sandbox, git
dest = Path(sys.argv[2])
sb = Sandbox(dest)
shutil.copy(Path(sys.argv[1]) / ".gitattributes", dest / ".gitattributes")
sb.commit("add gitattributes")
r00 = sb.drive_to_accepted("00")
r01 = sb.drive_to_accepted("01")
print("00 verified", r00, "01 verified", r01, "HEAD", sb.head(), "clock", sb.clock)
