"""Secret gate of the D-036 campaign (AMENDMENT_2026-11-04_D036_CONFIRMATION.md section 5): no captured or derived
file that matches the accepted Stage 00 secret patterns is ever committed.

Usage (from the repository root): python secret_gate.py CAMPAIGN_DIR

The patterns are those of the accepted, unchanged Stage 00 test (``tests/stage00/test_repository.py``,
``SECRET_PATTERNS``), read from that file so the gate can never miss what that test finds, plus ``EXTRA_PATTERNS``
below (readiness review B-3): the shapes of access-bearing URLs and keys that the Stage 00 list does not cover
(S3 SigV2 and SigV4 presigned URLs, temporary STS key ids and session tokens, Google Cloud Storage signed URLs, Azure
shared access signatures, Google API keys, Slack webhooks). The extra patterns are deliberately broad: a false match
only withholds a file from the public repository; it stays on disk and in the checksummed export.

Every file under CAMPAIGN_DIR that is not yet tracked is scanned (bytes, decoded as UTF-8 with replacement, so a
binary file is scanned too). For every match:

- the file's path is added to CAMPAIGN_DIR/.gitignore (it stays on disk, byte-identical, for the prediction run,
  verify and replay);
- CAMPAIGN_DIR/WITHHELD_FILES.json records its path, SHA-256, size and the number of matches (summed over the
  text and its two percent-decoded readings), never the matched text.

The script prints only paths and counts. It exits 0 when nothing new was found, 3 when it withheld files (the caller
then reviews and commits the updated .gitignore and WITHHELD_FILES.json before anything else), and 2 on misuse.
Withholding is not proof that a string never entered history: the gate must run before every ``git add`` of campaign
files, which the campaign procedure requires.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
STAGE00 = ROOT / "tests/stage00/test_repository.py"
# Review B-3 and re-review R-03. Parameter names are matched (in any case), not values, so a key id that is
# percent-encoded is still caught; the text is also scanned once and twice percent-decoded (``scanned``), so a
# signed URL nested inside another URL is caught too.
EXTRA_PATTERNS = [
    re.compile(p)
    for p in (
        r"(?i)AWSAccessKeyId=",
        r"(?i)X-Amz-(?:Credential|Security-Token|Signature)=",
        r"ASIA[0-9A-Z]{16}",
        r"(?i)X-Goog-(?:Credential|Signature)=",
        r"(?i)GoogleAccessId=",
        r"(?i)Key-Pair-Id=",
        r"[?&;]sv=20\d\d-\d\d-\d\d[^\s\"'<>]*[&;]sig=",
        r"[?&;]sig=[^\s\"'<>]*[&;]sv=20\d\d-\d\d-\d\d",
        r"AIza[0-9A-Za-z_-]{35}",
        r"hooks\.slack\.com/services/[A-Za-z0-9]+/[A-Za-z0-9]+/[A-Za-z0-9]+",
    )
]


def patterns() -> list[re.Pattern[str]]:
    spec = importlib.util.spec_from_file_location("stage00_repository_patterns", STAGE00)
    if spec is None or spec.loader is None:
        raise SystemExit(2)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return [*module.SECRET_PATTERNS, *EXTRA_PATTERNS]


def scanned(data: bytes) -> list[str]:
    """The file's text, and that text percent-decoded once and twice (a URL nested in a redirect is encoded twice)."""
    text = data.decode("utf-8", errors="replace")
    once = urllib.parse.unquote(text)
    return [text, once, urllib.parse.unquote(once)]


def untracked(campaign: Path) -> list[Path]:
    out = subprocess.run(  # noqa: S603
        ["git", "-C", str(ROOT), "ls-files", "--others", "--exclude-standard", "-z", "--", str(campaign)],  # noqa: S607
        capture_output=True,
        check=True,
    ).stdout
    return [ROOT / p.decode() for p in out.split(b"\0") if p and (ROOT / p.decode()).is_file()]


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    campaign = Path(argv[1]).resolve()
    pats = patterns()
    ledger_path = campaign / "WITHHELD_FILES.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else {"files": []}
    known = {f["path"] for f in ledger["files"]}
    found = []
    for path in sorted(untracked(campaign)):
        data = path.read_bytes()
        matches = sum(len(p.findall(text)) for text in scanned(data) for p in pats)
        if not matches:
            continue
        rel = path.relative_to(campaign).as_posix()
        if rel in known:
            continue
        found.append({"path": rel, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "matches": matches})
    if not found:
        print("secret gate: no new match")
        return 0
    ledger.setdefault(
        "why",
        "Files matching the accepted Stage 00 secret patterns or the access-bearing URL patterns of review B-3 are "
        "never committed (amendment section 5). They stay on disk unchanged for the prediction run, verify and "
        "replay, and are in the checksummed export.",
    )
    ledger["files"].extend(found)
    ledger_path.write_text(json.dumps(ledger, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    ignore = campaign / ".gitignore"
    lines = ignore.read_text(encoding="utf-8").splitlines() if ignore.exists() else []
    lines += ["/" + f["path"] for f in found]
    ignore.write_text("\n".join(lines) + "\n", encoding="utf-8")
    for f in found:
        print(f"secret gate: withheld {f['path']} ({f['matches']} matches)")
    return 3


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
