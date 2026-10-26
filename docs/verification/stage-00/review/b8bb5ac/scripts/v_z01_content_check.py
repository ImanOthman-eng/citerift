"""Z-01 variants (local git state that hides an edit from `git status`) and regression cases of the new content
check (gitutil._content_changed) in tiny throwaway repositories under $W/sandbox-vZ01/. Nothing else is touched."""
import os, shutil, subprocess, sys, time
from pathlib import Path
W = Path(os.environ["W"]); sys.path.insert(0, str(W / "base" / "src"))
from citerift.governance import gitutil  # noqa: E402
ENV = {**os.environ, "GIT_AUTHOR_NAME": "r", "GIT_AUTHOR_EMAIL": "r@x", "GIT_COMMITTER_NAME": "r",
       "GIT_COMMITTER_EMAIL": "r@x", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}
os.environ.update({k: ENV[k] for k in ("GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM")})
TOP = W / "sandbox-vZ01"; shutil.rmtree(TOP, ignore_errors=True); TOP.mkdir()
def g(d, *a, check=True): return subprocess.run(["git", "-C", str(d), *a], capture_output=True, text=True, env=ENV, check=check).stdout
def new(name, fmt=None):
    d = TOP / name; d.mkdir()
    g(d, "init", "-q", *(["--object-format", fmt] if fmt else []))
    (d / ".gitattributes").write_text("* text=auto eol=lf\n")
    (d / "a.py").write_text("def test_a():\n    assert True\n")
    (d / "b.txt").write_text("line one\nline two\n")
    (d / "run.sh").write_text("#!/bin/sh\necho hi\n"); os.chmod(d / "run.sh", 0o755)
    os.symlink("b.txt", d / "link")
    g(d, "add", "-A"); g(d, "commit", "-qm", "init")
    return d
def report(label, d):
    st = g(d, "status", "--porcelain", "--untracked-files=all").strip().replace("\n", " | ")
    try: dp = gitutil.dirty_paths(d)
    except Exception as e: dp = f"{type(e).__name__}: {e}"
    print(f"{label}\n    git status: {st!r}\n    dirty_paths: {dp}")
def same_size_edit(f):
    st = f.stat(); data = f.read_bytes().replace(b"True", b"Fals", 1)
    with open(f, "r+b") as fh: fh.write(data)
    os.utime(f, ns=(st.st_atime_ns, st.st_mtime_ns))
print("== Z-01 variants: edits hidden from git status")
d = new("trustctime"); old = time.time_ns() - 3600 * 10**9; os.utime(d / "a.py", ns=(old, old)); g(d, "update-index", "--refresh"); time.sleep(1.1)
g(d, "config", "core.trustctime", "false"); same_size_edit(d / "a.py"); report("1 core.trustctime=false, same size and mtime (original Z-01)", d)
d = new("checkstat"); os.utime(d / "a.py", ns=(old, old)); g(d, "update-index", "--refresh"); time.sleep(1.1)
g(d, "config", "core.checkStat", "minimal"); g(d, "config", "core.trustctime", "false"); same_size_edit(d / "a.py"); report("2 core.checkStat=minimal + trustctime=false", d)
d = new("cleanfilter"); (d / ".git/info/attributes").write_text("a.py filter=hide\n")
g(d, "config", "filter.hide.clean", "git cat-file blob HEAD:%f"); g(d, "config", "filter.hide.smudge", "cat")
(d / "a.py").write_text("def test_a():\n    assert False  # edited\n"); report("3 clean filter in .git/info/attributes that returns the committed blob", d)
d = new("fsmonitor"); hook = d / ".git/fsmon.sh"; hook.write_text("#!/bin/sh\nprintf 'tok\\0'\n"); os.chmod(hook, 0o755)
g(d, "config", "core.fsmonitor", str(hook)); g(d, "status"); (d / "a.py").write_text("def test_a():\n    assert False\n")
report("4 core.fsmonitor hook reporting no change", d)
d = new("assume"); (d / "a.py").write_text("x\n"); g(d, "update-index", "--assume-unchanged", "a.py"); report("5 --assume-unchanged (Y-02)", d)
d = new("skipwt"); (d / "a.py").write_text("x\n"); g(d, "update-index", "--skip-worktree", "a.py"); report("6 --skip-worktree (Y-02)", d)
d = new("staged"); (d / "a.py").write_text("x\n"); g(d, "add", "a.py"); report("7 staged edit", d)
d = new("worktree"); other = TOP / "worktree-clean"; shutil.copytree(d, other, ignore=shutil.ignore_patterns(".git"), symlinks=True)
g(d, "config", "core.worktree", str(other)); (d / "a.py").write_text("def test_a():\n    assert False\n"); report("8 core.worktree pointed at a clean copy, edit in the checked directory", d)
d = new("exclude"); (d / "new_test.py").write_text("x\n"); (d / ".git/info/exclude").write_text("new_test.py\n"); report("9 new untracked file hidden by .git/info/exclude (not an edit)", d)
d = new("filemode"); g(d, "config", "core.fileMode", "false"); os.chmod(d / "a.py", 0o755); report("10 core.fileMode=false + chmod +x a.py (mode only)", d)
print("== regression cases on honest trees")
d = new("honest"); report("R1 honest tree (symlink, executable file, LF)", d)
src = new("crlfsrc"); d = TOP / "crlf"; subprocess.run(["git", "-c", "core.autocrlf=true", "-c", "core.eol=crlf", "clone", "-q", str(src), str(d)], check=True, env=ENV)
g(d, "config", "core.autocrlf", "true"); g(d, "config", "core.eol", "crlf"); report("R2 clone with core.autocrlf=true, core.eol=crlf", d)
src = new("noattr"); (src / ".gitattributes").unlink(); g(src, "commit", "-qam", "drop attributes"); d = TOP / "crlf-noattr"
subprocess.run(["git", "-c", "core.autocrlf=true", "clone", "-q", str(src), str(d)], check=True, env=ENV); g(d, "config", "core.autocrlf", "true")
report("R3 (outside this repository's setup) no .gitattributes, core.autocrlf=true: CRLF on disk", d)
d = new("infoattr"); (d / ".git/info/attributes").write_text("* text eol=crlf\n"); (d / "b.txt").unlink(); g(d, "checkout", "--", "b.txt")
report("R4 local .git/info/attributes '* text eol=crlf' (overrides the committed one), b.txt re-checked-out", d)
d = new("nosymlinks"); g(d, "config", "core.symlinks", "false"); (d / "link").unlink(); g(d, "checkout", "--", "link")
print("    link is now a", "symlink" if (d / "link").is_symlink() else "regular file"); report("R5 core.symlinks=false checkout of the tracked symlink", d)
d = new("missing"); (d / "b.txt").unlink(); report("R6 missing tracked file", d)
d = new("nonutf8"); name = os.fsdecode(b"caf\xe9.txt"); (d / name).write_bytes(b"x\n"); g(d, "add", "-A"); g(d, "commit", "-qm", "n")
report("R7 tracked file with a non-UTF-8 name, honest", d)
(d / name).write_bytes(b"y\n"); report("R7b the same file edited", d)
print("    is_tracked(non-UTF-8 name):", gitutil.is_tracked(d, name))
for nm in (":x.txt", "*.txt", "a?.py", "[ab].py", "sp ace.txt", ":(top)y.txt", ":!z.txt"):
    (d / nm).write_text("1\n")
g(d, "add", "-A"); g(d, "commit", "-qm", "names")
print("    is_tracked for magic / glob names:", {nm: gitutil.is_tracked(d, nm) for nm in (":x.txt", "*.txt", "a?.py", "[ab].py", "sp ace.txt", ":(top)y.txt", ":!z.txt", "untracked.txt", "*.py")})
try:
    d = new("sha256", "sha256"); report("R8 sha256 object format, honest", d); (d / "b.txt").write_text("changed!\n"); report("R8b sha256, edited", d)
except subprocess.CalledProcessError as e:
    print("R8 sha256 repository not available:", e.stderr)
sub = new("subsrc"); d = new("submod")
g(d, "-c", "protocol.file.allow=always", "submodule", "add", "-q", str(sub), "sub"); g(d, "commit", "-qm", "sub")
report("R9 honest tree with a submodule", d)
(d / "sub/a.py").write_text("x\n"); g(d, "config", "submodule.sub.ignore", "all"); report("R9b edit inside the submodule, submodule.sub.ignore=all in .git/config", d)
