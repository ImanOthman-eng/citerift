"""Variant of Y-02 in a tiny repository: hide an edit of a tracked file from `git status` without
--skip-worktree or --assume-unchanged, by keeping the file's size and mtime and setting core.trustctime=false
(local .git/config). Then ask citerift's gitutil.dirty_paths whether the tree is dirty."""
import os, subprocess, sys, tempfile, time
from pathlib import Path
W = Path(os.environ["W"]); sys.path.insert(0, str(W / "base/src"))
from citerift.governance import gitutil
env = {**os.environ, "GIT_AUTHOR_NAME": "r", "GIT_AUTHOR_EMAIL": "r@x.invalid", "GIT_COMMITTER_NAME": "r",
       "GIT_COMMITTER_EMAIL": "r@x.invalid", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}
def g(*a): return subprocess.run(["git", "-C", str(d), *a], capture_output=True, text=True, env=env, check=True).stdout
d = Path(tempfile.mkdtemp(dir=W))
f = d / "test_a.py"
f.write_text("def test_1():\n    pass\n\ndef test_2():\n    pass\n")
g("init", "-q"); g("add", "-A"); g("commit", "-qm", "t")
old = time.time_ns() - 3600 * 10**9
os.utime(f, ns=(old, old)); g("update-index", "--refresh")   # index records the old mtime
time.sleep(1.1)
g("config", "core.trustctime", "false")
st = f.stat()
with open(f, "r+") as fh:   # same size, in place (same inode)
    fh.write(f.read_text().replace("def test_2", "def xest_2"))
os.utime(f, ns=(st.st_atime_ns, st.st_mtime_ns))
print("content now:", f.read_text().split("\n")[3])
print("git status --porcelain:", repr(g("status", "--porcelain")))
print("gitutil.dirty_paths:", gitutil.dirty_paths(d))
print("git diff HEAD --stat (stat cache):", repr(g("diff", "HEAD", "--stat")))
print("control, content hash vs HEAD:", g("hash-object", "test_a.py").strip() != g("rev-parse", "HEAD:test_a.py").strip())
