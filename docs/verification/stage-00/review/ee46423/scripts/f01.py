import sys, shutil
sys.path.insert(0, "/tmp/claude-0/-home-user-citerift/0bbaf0e6-71eb-560d-84bf-668fa4ffb288/scratchpad/review/scripts")
from lib import *
sys.path.insert(0, str(CLONE / "tests/stage00"))
from sandbox_repo import Sandbox
d = W / "exp/f01base"
sb = Sandbox(d)
shutil.copy(CLONE / ".gitattributes", d / ".gitattributes")
A = sb.commit("A: gitattributes")
p = d / "schemas/contracts/v1/common.schema.json"
p.write_text(p.read_text().replace('"title": "CITERIFT shared', '"title": "CITERIFT (B) shared'))
B = sb.commit("B: owned content changed before verification")
V = sb.drive_to_accepted("00"); sb.drive_to_accepted("01")
print("A", A, "B", B, "verified", V)
check(d, "f01base clean")

# Original topology: merge that takes owned paths from an older side branch
e = mk("f01_merge", d)
git(e, "checkout", "-q", "-b", "old", A)
(e / "side-note.txt").write_text("side\n"); commit(e, "unrelated side commit")
git(e, "checkout", "-q", "master" if "master" in git(e, "branch") else "main")
git(e, "merge", "--no-ff", "--no-commit", "old", check=False)
git(e, "checkout", "old", "--", "schemas/contracts/v1"); commit(e, "Merge branch old")
print("diff vs verified:", git(e, "diff", "--stat", V, "HEAD", "--", "schemas/contracts/v1"))
print("git log -1 -- owned:", git(e, "log", "-1", "--format=%h %s", "HEAD", "--", "schemas/contracts/v1"))
check(e, "F-01 original: merge restoring older owned content")

# Variant: octopus merge
e = mk("f01_octopus", d)
main = git(e, "rev-parse", "--abbrev-ref", "HEAD")
for b in ("o1", "o2"):
    git(e, "checkout", "-q", "-b", b, A); (e / f"{b}.txt").write_text(b); commit(e, b)
git(e, "checkout", "-q", main)
git(e, "merge", "--no-ff", "--no-commit", "o1", "o2", check=False)
git(e, "checkout", "o1", "--", "schemas/contracts/v1"); commit(e, "octopus")
check(e, "F-01 variant: octopus merge restoring older content")

# Variant: mode-only change in an owned path
e = mk("f01_mode", d)
git(e, "update-index", "--chmod=+x", "schemas/contracts/v1/common.schema.json"); git(e, "commit", "-q", "-m", "chmod")
check(e, "F-01 variant: mode-only change of an owned file")

# Variant: change then restore (content equal at HEAD) -> should be clean
e = mk("f01_restore", d)
p = e / "schemas/contracts/v1/common.schema.json"; orig = p.read_text()
p.write_text(orig + " "); commit(e, "tamper"); p.write_text(orig); commit(e, "restore")
check(e, "F-01 control: changed then restored (content equal)")

# Variant: git replace object makes the verified commit look like HEAD's content (local refs only)
e = mk("f01_replace", d)
p = e / "schemas/contracts/v1/common.schema.json"; p.write_text(p.read_text().replace("(B)", "(TAMPERED)")); T = commit(e, "tamper owned path")
check(e, "F-01 variant pre-replace: tampered owned content")
tree = git(e, "rev-parse", "HEAD^{tree}")
parent = git(e, "rev-parse", V + "^")
fake = git(e, "commit-tree", tree, "-p", parent, "-m", "fake")
git(e, "replace", V, fake)
check(e, "F-01 variant: same tamper plus local `git replace <verified> <commit with HEAD tree>`")
