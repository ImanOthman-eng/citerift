"""Secret scan of the freeze-3 candidate tree (owner decision D-083, item 13).

Usage (repository root, clean tree): ``python -I docs/verification/stage-04/freeze-3/secret_scan.py <output .json>``

Scans every file git tracks at HEAD (``git grep`` over the committed tree, so the working tree is not read) for the
formats of well-known credentials, and lists tracked files whose names are typical credential stores. The patterns are
fixed formats with distinctive prefixes, not entropy heuristics, so a hit is a finding to inspect, and no hit is
evidence only for these formats. The output names the commit, each pattern, its hit count and every hit location
(path and line, never the matched text).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

PATTERNS: dict[str, str] = {
    "private_key_block": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "aws_access_key_id": r"\b(AKIA|ASIA)[0-9A-Z]{16}\b",
    "github_token": r"\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36}\b",
    "github_fine_grained_pat": r"\bgithub_pat_[A-Za-z0-9_]{60,}\b",
    "anthropic_api_key": r"\bsk-ant-[A-Za-z0-9_-]{20,}",
    "openai_api_key": r"\bsk-(proj-)?[A-Za-z0-9]{32,}\b",
    "slack_token": r"\bxox[abprs]-[A-Za-z0-9-]{10,}",
    "google_api_key": r"\bAIza[0-9A-Za-z_-]{35}\b",
    "huggingface_token": r"\bhf_[A-Za-z0-9]{30,}\b",
    "stripe_secret_key": r"\b(sk|rk)_live_[A-Za-z0-9]{20,}\b",
    "jwt": r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
    "url_with_password": r"[a-z][a-z0-9+.-]*://[^/\s:@\"']+:[^/\s:@\"']+@[A-Za-z0-9.-]+",
}
CREDENTIAL_FILE_NAMES = re.compile(
    r"(^|/)(\.env(\..*)?|.*\.pem|.*\.p12|.*\.pfx|id_rsa|id_ed25519|credentials\.json|\.netrc|\.pypirc)$"
)


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=False)  # noqa: S603, S607


def main() -> int:
    target = Path(sys.argv[1])
    head = _git("rev-parse", "HEAD").stdout.strip()
    results: dict[str, object] = {}
    total = 0
    for name, pattern in PATTERNS.items():
        out = _git("grep", "-I", "-n", "-P", "-o", "--no-color", "-e", pattern, head)
        if out.returncode not in (0, 1):
            raise SystemExit(f"git grep failed for {name}: {out.stderr}")
        hits = []
        for line in out.stdout.splitlines():
            _, path, lineno, _match = line.split(":", 3)
            hits.append(f"{path}:{lineno}")
        total += len(hits)
        results[name] = {"pattern": pattern, "hits": len(hits), "locations": hits}
    files = _git("ls-tree", "-r", "--name-only", head).stdout.splitlines()
    cred_files = [f for f in files if CREDENTIAL_FILE_NAMES.search(f)]
    doc = {
        "commit": head,
        "tracked_files": len(files),
        "patterns": results,
        "pattern_hits": total,
        "credential_file_names": cred_files,
        "method": "git grep -I -P over the committed tree at the commit; binary files skipped",
    }
    target.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"commit": head, "pattern_hits": total, "credential_file_names": cred_files}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
