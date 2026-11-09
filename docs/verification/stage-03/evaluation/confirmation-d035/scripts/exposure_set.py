"""[D-035 copy; see the end of this docstring.]
Exposure set for the 2026-11-02 confirmation campaign (AMENDMENT_2026-11-02_CONFIRMATION.md section 3).

Usage (from the repository root): python exposure_set.py > EXPOSURE_SET.json

Deliberately over-inclusive. It reads every JSON document committed under ``docs/verification/stage-03/`` and
``tests/stage03/``: plain ``.json`` files and the raw API answers kept as artifacts (any file that parses as JSON).
From them it collects:

- every integer under a ``page_id``, ``pageid`` or ``pageId`` key;
- every ``id`` that sits next to a ``title`` (``list=random`` and similar answers);
- every string under a ``title`` key and every string in a ``titles`` list;
- the development titles.

So every article that this stage ever selected, drew, captured, annotated, extracted, used as a fixture or merely
listed is exposed. An exposed page id or title is excluded in both wikis; over-exclusion costs nothing. The set is
committed before the draw, and the draw reads it, never the files directly. No request is made.


Copied for the D-035 confirmation (AMENDMENT_2026-11-03_D035_CONFIRMATION.md) from
``../../confirmation-2026-11/scripts/`` with only the changes that amendment lists.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[6]
ROOTS = ("docs/verification/stage-03", "tests/stage03")
MAX_BYTES = 32 * 1024 * 1024


def walk(node: Any, ids: set[int], titles: set[str]) -> None:
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ("page_id", "pageid", "pageId") and isinstance(v, int) and not isinstance(v, bool):
                ids.add(v)
            elif k == "title" and isinstance(v, str):
                titles.add(v)
            elif k == "titles" and isinstance(v, list):
                titles.update(t for t in v if isinstance(t, str))
        if isinstance(node.get("id"), int) and isinstance(node.get("title"), str):
            ids.add(node["id"])
        for v in node.values():
            walk(v, ids, titles)
    elif isinstance(node, list):
        for v in node:
            walk(v, ids, titles)


def main() -> int:
    listed = subprocess.run(  # noqa: S603 - fixed argv
        ["git", "-C", str(ROOT), "ls-files", "-z", "--", *ROOTS],  # noqa: S607
        capture_output=True,
        check=True,
    ).stdout.split(b"\0")
    files = sorted(p.decode() for p in listed if p)
    ids: set[int] = set()
    titles: set[str] = set()
    read: list[str] = []
    for rel in files:
        path = ROOT / rel
        if not path.is_file() or path.stat().st_size > MAX_BYTES:
            continue
        data = path.read_bytes()
        if data.lstrip()[:1] not in (b"{", b"["):
            continue
        try:
            doc = json.loads(data)
        except (ValueError, UnicodeDecodeError):
            continue
        read.append(rel)
        walk(doc, ids, titles)
    for name in ("dev_selection.json", "dev_selection_supplement.json"):
        dev = json.loads((ROOT / "docs/verification/stage-03/calibration" / name).read_text(encoding="utf-8"))
        titles.update(a["title"] for a in dev.get("articles", []))
    listing = "\n".join(read).encode()
    out = {
        "procedure": __doc__,
        "documents_read": len(read),
        "documents_sha256": hashlib.sha256(listing).hexdigest(),
        "page_ids": sorted(ids),
        "titles": sorted(titles),
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
