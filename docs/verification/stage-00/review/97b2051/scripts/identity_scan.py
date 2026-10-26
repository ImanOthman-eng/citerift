"""Identity check (docs/identity.md rules 2-4). Reads forbidden name terms from the environment
variable NAME_TERMS (comma separated; never stored in this file) and reports only file:line
locations, never the matching text. Occurrences inside the repository account login (the
OWNERSHIP.md exception, rule 2) are ignored by stripping tokens listed in ALLOWED_TOKENS (also
from the environment). Also looks for trademark marks and AI tools presented as creator/owner."""
import os
import re
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
terms = [t.strip() for t in os.environ.get("NAME_TERMS", "").split(",") if t.strip()]
allowed = [t.strip() for t in os.environ.get("ALLOWED_TOKENS", "").split(",") if t.strip()]
files = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], capture_output=True, text=True).stdout.split("\0")
name_hits, tm_hits, ai_hits = [], [], []
ai_re = re.compile(r"(created|directed|owned|authored)\s+by\s+(claude|anthropic|an?\s+ai)", re.I)
for rel in filter(None, files):
    p = root / rel
    try:
        lines = p.read_text(encoding="utf-8").splitlines()
    except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError):
        continue
    for n, line in enumerate(lines, 1):
        scrubbed = line
        for tok in allowed:
            scrubbed = re.sub(re.escape(tok), " ", scrubbed, flags=re.I)
        if any(re.search(rf"\b{re.escape(t)}\b", scrubbed, re.I) for t in terms):
            name_hits.append(f"{rel}:{n}")
        if "™" in line or "®" in line:
            tm_hits.append(f"{rel}:{n}")
        if ai_re.search(line):
            ai_hits.append(f"{rel}:{n}")
print("name terms checked:", len(terms))
print("name-term hits outside the account login:", name_hits or "not found")
print("trademark marks:", tm_hits or "not found")
print("AI tool presented as creator/owner (pattern):", ai_hits or "not found")
