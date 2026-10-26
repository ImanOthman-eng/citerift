"""R5-02 boundary cases against the revision in $BASE: gitutil.dirty_paths of that revision on a superproject with a
committed submodule `sub`, for each kind of change inside the submodule and each setting that can hide it.
Prints the default `git status --porcelain` next to dirty_paths. Throwaway repositories under $W/sandbox-r502."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

W = Path(os.environ["W"])
BASE = Path(os.environ["BASE"])
sys.path.insert(0, str(BASE / "src"))
from citerift.governance import gitutil  # noqa: E402

ENV = {**os.environ, "GIT_AUTHOR_NAME": "r", "GIT_AUTHOR_EMAIL": "r@x.invalid", "GIT_COMMITTER_NAME": "r",
       "GIT_COMMITTER_EMAIL": "r@x.invalid", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}
os.environ.update({k: ENV[k] for k in ("GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM")})
TOP = W / "sandbox-r502"
shutil.rmtree(TOP, ignore_errors=True)
TOP.mkdir(parents=True)


def g(d: Path, *a: str) -> str:
    return subprocess.run(["git", "-C", str(d), *a], capture_output=True, text=True, env=ENV, check=True).stdout


lib = TOP / "helperlib"
lib.mkdir()
(lib / "helper.py").write_text("CASES = 9\n")
g(lib, "init", "-q")
g(lib, "add", "-A")
g(lib, "commit", "-qm", "lib")
n = 0


def project(gitmodules_ignore: str | None) -> Path:
    global n
    n += 1
    d = TOP / f"p{n}"
    d.mkdir()
    (d / "a.txt").write_text("a\n")
    g(d, "init", "-q")
    g(d, "-c", "protocol.file.allow=always", "submodule", "add", "-q", str(lib), "sub")
    if gitmodules_ignore:
        g(d, "config", "-f", ".gitmodules", "submodule.sub.ignore", gitmodules_ignore)
    g(d, "add", "-A")
    g(d, "commit", "-qm", "p")
    return d


def change(d: Path, kind: str) -> None:
    s = d / "sub"
    if kind == "edit":
        (s / "helper.py").write_text("CASES = 1\n")
    elif kind == "untracked":
        (s / "extra.py").write_text("X = 1\n")
    elif kind == "staged":
        (s / "helper.py").write_text("CASES = 1\n")
        g(s, "add", "helper.py")
    elif kind == "new commit":
        (s / "helper.py").write_text("CASES = 1\n")
        g(s, "commit", "-qam", "moved")
    elif kind == "edit + assume-unchanged in sub":
        g(s, "update-index", "--assume-unchanged", "helper.py")
        (s / "helper.py").write_text("CASES = 1\n")
    elif kind == "edit + skip-worktree in sub":
        g(s, "update-index", "--skip-worktree", "helper.py")
        (s / "helper.py").write_text("CASES = 1\n")
    elif kind == "edit keeping size and mtime in sub":
        p = s / "helper.py"
        g(s, "status", "--porcelain")  # refresh the submodule's stat cache
        st = p.stat()
        p.write_text("CASES = 1\n")  # same length as "CASES = 9\n"
        os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))
    else:
        raise ValueError(kind)


def show(label: str, d: Path) -> None:
    st = g(d, "status", "--porcelain").strip()
    try:
        dp = gitutil.dirty_paths(d)
    except Exception as e:  # noqa: BLE001
        dp = f"error {type(e).__name__}: {e}"
    verdict = "SEEN" if isinstance(dp, list) and "sub" in dp else "HIDDEN"
    print(f"{label}: git status {st!r}; dirty_paths={dp} -> {verdict}")


print(f"revision {BASE.name} {g(BASE, 'rev-parse', 'HEAD').strip()}")
kinds = ["edit", "untracked", "staged", "new commit"]
for kind in kinds:
    show(f"[{kind}] control, no setting", (lambda d: (change(d, kind), d)[1])(project(None)))
    for where, key in ((".git/config", "submodule.sub.ignore"), (".git/config", "diff.ignoreSubmodules")):
        for value in ("none", "untracked", "dirty", "all"):
            d = project(None)
            g(d, "config", key, value)
            change(d, kind)
            show(f"[{kind}] {where} {key}={value}", d)
    for value in ("untracked", "dirty", "all"):
        d = project(value)
        change(d, kind)
        show(f"[{kind}] committed .gitmodules submodule.sub.ignore={value}", d)
    d = project("all")
    g(d, "config", "submodule.sub.ignore", "none")
    change(d, kind)
    show(f"[{kind}] .gitmodules ignore=all, .git/config ignore=none", d)
    d = project(None)
    g(d, "config", "submodule.sub.ignore", "all")
    g(d, "config", "diff.ignoreSubmodules", "all")
    change(d, kind)
    show(f"[{kind}] both .git/config settings =all", d)

print("-- settings and index flags inside the submodule's own repository (.git/modules/sub)")
for kind in ("edit + assume-unchanged in sub", "edit + skip-worktree in sub", "edit keeping size and mtime in sub"):
    d = project(None)
    change(d, kind)
    show(f"[{kind}]", d)
d = project(None)
g(d / "sub", "config", "status.showUntrackedFiles", "no")
change(d, "untracked")
show("[untracked] sub config status.showUntrackedFiles=no", d)
d = project(None)
g(d / "sub", "config", "core.fsmonitor", "true")
change(d, "edit")
show("[edit] sub config core.fsmonitor=true (no daemon)", d)
