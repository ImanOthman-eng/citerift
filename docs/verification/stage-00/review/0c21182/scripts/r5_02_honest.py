"""R5-02 regression check: honest (unchanged) submodule states must stay clean with --ignore-submodules=none.
Uses r5_02_boundary's helpers by import of its functions would rerun it, so the setup is repeated here."""
import os, shutil, subprocess, sys
from pathlib import Path
W = Path(os.environ["W"]); BASE = Path(os.environ["BASE"]); sys.path.insert(0, str(BASE / "src"))
from citerift.governance import gitutil  # noqa: E402
ENV = {**os.environ, "GIT_AUTHOR_NAME": "r", "GIT_AUTHOR_EMAIL": "r@x.invalid", "GIT_COMMITTER_NAME": "r",
       "GIT_COMMITTER_EMAIL": "r@x.invalid", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}
os.environ.update({k: ENV[k] for k in ("GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM")})
TOP = W / "sandbox-r502h"; shutil.rmtree(TOP, ignore_errors=True); TOP.mkdir(parents=True)
def g(d, *a): return subprocess.run(["git", "-C", str(d), *a], capture_output=True, text=True, env=ENV, check=True).stdout
lib = TOP / "lib"; lib.mkdir(); (lib / "h.py").write_text("C = 9\n"); g(lib, "init", "-q"); g(lib, "add", "-A"); g(lib, "commit", "-qm", "l")
p = TOP / "p"; p.mkdir(); (p / "a.txt").write_text("a\n"); g(p, "init", "-q")
g(p, "-c", "protocol.file.allow=always", "submodule", "add", "-q", str(lib), "sub"); g(p, "add", "-A"); g(p, "commit", "-qm", "p")
print(f"revision {BASE.name} {g(BASE, 'rev-parse', 'HEAD').strip()}")
print("clean initialised submodule:", repr(g(p, "status", "--porcelain").strip()), gitutil.dirty_paths(p))
for key in ("submodule.sub.ignore", "diff.ignoreSubmodules"):
    for v in ("untracked", "dirty", "all"):
        g(p, "config", key, v); print(f"clean, {key}={v}:", gitutil.dirty_paths(p)); g(p, "config", "--unset", key)
c = TOP / "clone-no-recurse"; subprocess.run(["git", "clone", "-q", str(p), str(c)], check=True, env=ENV)
print("fresh clone without --recurse-submodules (as actions/checkout default):", repr(g(c, "status", "--porcelain").strip()),
      "sub is empty dir:", (c / "sub").is_dir() and not any((c / "sub").iterdir()), "dirty_paths:", gitutil.dirty_paths(c))
c2 = TOP / "clone-recurse"; subprocess.run(["git", "-c", "protocol.file.allow=always", "clone", "-q", "--recurse-submodules", str(p), str(c2)], check=True, env=ENV)
print("fresh clone with --recurse-submodules:", repr(g(c2, "status", "--porcelain").strip()), gitutil.dirty_paths(c2))
