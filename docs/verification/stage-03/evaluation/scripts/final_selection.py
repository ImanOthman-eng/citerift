"""The final-campaign selection (../../protocol/AMENDMENT_2026-10-29.md section 2), derived mechanically.

Usage: python final_selection.py > ../final/selection_final.json   (run from the repository root)

The pool is ``splits.<wiki>.unused`` of the committed original draw (selection/selection.json), in its stored order:
the frozen order of select_sample.py, continuing after position 22. Pool positions 1-10 are the final holdout and
11-16 the final reserve; arwiki has 15 pool candidates, so its reserve has 5 until a 16th is drawn under section 4
of the amendment. The output has the shape capture_sample.py reads (``splits`` and an empty ``challenge``). No
request is made.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SELECTION = ROOT / "docs" / "verification" / "stage-03" / "evaluation" / "selection" / "selection.json"
HOLDOUT, RESERVE_END = 10, 16


def main() -> int:
    data = SELECTION.read_bytes()
    sel = json.loads(data)
    out: dict[str, object] = {
        "procedure": __doc__,
        "source": {
            "path": str(SELECTION.relative_to(ROOT)),
            "sha256": hashlib.sha256(data).hexdigest(),
            "field": "splits.<wiki>.unused",
        },
        "splits": {},
        "challenge": {"ar": {"selected": []}, "en": {"selected": []}},
    }
    for wiki in ("ar", "en"):
        pool = sel["splits"][wiki]["unused"]
        out["splits"][wiki] = {  # type: ignore[index]
            "pool_size": len(pool),
            "holdout": [{**a, "pool_position": i + 1} for i, a in enumerate(pool[:HOLDOUT])],
            "reserve": [{**a, "pool_position": i + 1} for i, a in enumerate(pool[HOLDOUT:RESERVE_END], HOLDOUT)],
        }
    sys.stdout.write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
