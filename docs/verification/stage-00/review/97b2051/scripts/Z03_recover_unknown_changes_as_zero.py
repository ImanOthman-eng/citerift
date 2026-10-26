"""Z-03: with a damaged git index, `citerift-gov recover` cannot list uncommitted changes (uncommitted_changes is
null in --json) but its text report prints 'Uncommitted changes: 0', although the tree here has an untracked file."""
import json, os, subprocess
from lib import BASE, PY, new_sandbox
sb = new_sandbox("Z03")
sb.write("an-uncommitted-file.txt", "not committed\n")
def cli(*a):
    return subprocess.run([PY, "-P", "-m", "citerift.governance.cli", *a], cwd=sb.root, capture_output=True, text=True,
                          env={**os.environ, "PYTHONPATH": str(BASE / "src")})
print("intact index:", [l for l in cli("recover").stdout.splitlines() if l.startswith("Uncommitted")])
(sb.root / ".git/index").write_bytes(b"DIRC garbage")
r = cli("recover")
print("damaged index, exit", r.returncode, [l for l in r.stdout.splitlines() if l.startswith("Uncommitted") or "REVISION_UNVERIFIABLE" in l])
print("damaged index, --json uncommitted_changes:", json.loads(cli("--json", "recover").stdout)["uncommitted_changes"])
