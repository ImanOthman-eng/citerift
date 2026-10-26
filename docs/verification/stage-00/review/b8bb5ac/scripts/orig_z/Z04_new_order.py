"""Z-04 replay in the CI step order of 6d1fa00 (derived from the confirmation reviewer's Z04 script; only the replayed steps differ)."""
import os, shutil, subprocess
from lib import BASE, clone_base
repo = clone_base("Z04")
BACKEND = r'''
import base64
import hashlib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
cli = ROOT / "src/citerift/governance/cli.py"
text = cli.read_text()
if "REWRITTEN" not in text:
    cli.write_text(text.replace("def cmd_check(orc: Orchestrator, args: argparse.Namespace) -> int:\n",
        "def cmd_check(orc: Orchestrator, args: argparse.Namespace) -> int:\n"
        "    print('Consistency check: 0 errors, 0 warnings')  # REWRITTEN\n    return 0\n", 1))

def _wheel(directory):
    dist = "citerift-0.1.0.dist-info"
    name = "citerift-0.1.0-py3-none-any.whl"
    files = {
        f"{dist}/METADATA": "Metadata-Version: 2.1\nName: citerift\nVersion: 0.1.0\nRequires-Dist: jsonschema<5,>=4.23\n",
        f"{dist}/WHEEL": "Wheel-Version: 1.0\nGenerator: in-tree\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        f"{dist}/entry_points.txt": "[console_scripts]\nciterift-gov = citerift.governance.cli:main\n",
        "citerift_src.pth": str(ROOT / "src") + "\n",
    }
    record = []
    with zipfile.ZipFile(Path(directory) / name, "w") as z:
        for k, v in files.items():
            z.writestr(k, v)
            d = base64.urlsafe_b64encode(hashlib.sha256(v.encode()).digest()).rstrip(b"=").decode()
            record.append(f"{k},sha256={d},{len(v.encode())}")
        record.append(f"{dist}/RECORD,,")
        z.writestr(f"{dist}/RECORD", "\n".join(record) + "\n")
    return name

def get_requires_for_build_wheel(config_settings=None):
    return []

def get_requires_for_build_editable(config_settings=None):
    return []

def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    return _wheel(wheel_directory)

def build_editable(wheel_directory, config_settings=None, metadata_directory=None):
    return _wheel(wheel_directory)
'''
(repo / "ci_backend.py").write_text(BACKEND)
py = (repo / "pyproject.toml").read_text()
py = py.replace('requires = ["uv_build>=0.11,<0.12"]\nbuild-backend = "uv_build"',
                'requires = []\nbuild-backend = "ci_backend"\nbackend-path = ["."]')
(repo / "pyproject.toml").write_text(py)
reg = (repo / "governance/stage_registry.json").read_text()
(repo / "governance/stage_registry.json").write_text(reg.replace('"status": "IN_PROGRESS"', '"status": "ACCEPTED_CLOSED"', 1))
env = {**os.environ, "GIT_AUTHOR_NAME": "r", "GIT_AUTHOR_EMAIL": "r@x.invalid", "GIT_COMMITTER_NAME": "r", "GIT_COMMITTER_EMAIL": "r@x.invalid"}
subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
subprocess.run(["git", "-C", str(repo), "commit", "-qm", "in-tree build backend + hand edit"], check=True, env=env)
def sh(name, cmd, **kw):
    r = subprocess.run(cmd, cwd=repo, capture_output=True, text=True, env={**env, "PYTHONPATH": "src", **kw}, shell=isinstance(cmd, str))
    out = [l for l in (r.stdout + r.stderr).splitlines() if "UV_NATIVE_TLS" not in l]
    print(f"[{name}] exit {r.returncode}: {(out or [''])[-1][:160]}"); return r
honest = subprocess.run([str(BASE / ".venv/bin/python"), "-P", "-m", "citerift.governance.cli", "check"], cwd=repo, capture_output=True, text=True,
                        env={**env, "PYTHONPATH": str(BASE / "src")})
print("honest checker (reviewed code) on this commit:", honest.stdout.splitlines()[0])
sh("guard", 'test "$(ls -A src)" = "citerift"')
sh("uv sync --frozen --no-install-project --no-build (offline)", ["uv", "sync", "--frozen", "--no-install-project", "--no-build", "--offline"])
print("git status after the dependency install:", subprocess.run(["git", "-C", str(repo), "status", "--porcelain"], capture_output=True, text=True).stdout.strip() or "clean")
sh("governance check (python -P -m citerift.governance.cli check)", ["uv", "run", "--no-sync", "python", "-P", "-m", "citerift.governance.cli", "check"])
sh("uv sync --locked (offline), after the check", ["uv", "sync", "--locked", "--offline"])
print("git status after the project install:", subprocess.run(["git", "-C", str(repo), "status", "--porcelain"], capture_output=True, text=True).stdout.strip())
