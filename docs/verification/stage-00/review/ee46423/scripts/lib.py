import json, os, subprocess, sys
from pathlib import Path
W = Path("/tmp/claude-0/-home-user-citerift/0bbaf0e6-71eb-560d-84bf-668fa4ffb288/scratchpad/review")
CLONE = W / "clone"
GOV = str(CLONE / ".venv/bin/citerift-gov")
PY = str(CLONE / ".venv/bin/python")
BASE = W / "exp/base"
ENV = {**os.environ, "GIT_AUTHOR_NAME": "R", "GIT_AUTHOR_EMAIL": "r@example.invalid",
       "GIT_COMMITTER_NAME": "R", "GIT_COMMITTER_EMAIL": "r@example.invalid",
       "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}

def sh(*cmd, cwd=None, check=True):
    r = subprocess.run(list(cmd), cwd=cwd, capture_output=True, text=True, env=ENV)
    if check and r.returncode != 0:
        raise RuntimeError(f"{cmd}: {r.stdout}{r.stderr}")
    return r

def git(root, *a, check=True):
    return sh("git", "-C", str(root), *a, check=check).stdout.strip()

def mk(name, base=BASE):
    d = W / "exp" / name
    if d.exists():
        raise SystemExit(f"{d} exists")
    sh("git", "clone", "-q", str(base), str(d))
    return d

def reg(root):
    return json.loads((root / "governance/stage_registry.json").read_text())

def save(root, r, render=True):
    (root / "governance/stage_registry.json").write_text(json.dumps(r, indent=2, ensure_ascii=False) + "\n")
    if render:
        sh(GOV, "--root", str(root), "render-status", "--write")

def commit(root, msg):
    git(root, "add", "-A"); git(root, "commit", "-q", "--allow-empty", "-m", msg)
    return git(root, "rev-parse", "HEAD")

def check(root, label=""):
    r = sh(GOV, "--root", str(root), "check", check=False)
    out = (r.stdout + r.stderr).strip()
    print(f"--- {label} [exit {r.returncode}]\n{out}\n")
    return r.returncode, out
