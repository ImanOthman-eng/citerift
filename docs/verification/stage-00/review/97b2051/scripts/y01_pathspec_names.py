"""Y-01 variant: does gitutil.is_tracked (git ls-files --error-unmatch -- PATH) recognise tracked files whose names
contain pathspec glob characters or start with ':'? A miss would let the report path be left out of the dirty check."""
import os, subprocess, sys, tempfile
from pathlib import Path
W = Path(os.environ["W"]); sys.path.insert(0, str(W / "base/src"))
from citerift.governance import gitutil
d = Path(tempfile.mkdtemp(dir=W))
env = {**os.environ, "GIT_AUTHOR_NAME": "r", "GIT_AUTHOR_EMAIL": "r@x", "GIT_COMMITTER_NAME": "r", "GIT_COMMITTER_EMAIL": "r@x"}
names = ["tests/test_[b].py", "tests/test_*.py", "tests/test_?.py", ":test_colon.py", "tests/test b.py"]
for n in names:
    (d / n).parent.mkdir(parents=True, exist_ok=True); (d / n).write_text("x\n")
subprocess.run(["git", "-C", str(d), "init", "-q"], check=True)
subprocess.run(["git", "-C", str(d), "add", "--", *[f":(literal){n}" for n in names]], check=True, env=env)
subprocess.run(["git", "-C", str(d), "commit", "-qm", "t"], check=True, env=env)
for n in names:
    (d / n).write_text("modified\n")
    print(f"{n!r}: is_tracked={gitutil.is_tracked(d, n)} dirty_paths(exclude=[it])-> {gitutil.dirty_paths(d, exclude=(n,)) if not gitutil.is_tracked(d, n) else 'not excluded'}")
print("untracked control:", gitutil.is_tracked(d, "nope.json"))
