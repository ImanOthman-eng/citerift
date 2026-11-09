"""Format check of adjudicator outputs (ADJUDICATION_BRIEF_v1.1.md). Changes nothing.

Usage (from the repository root): python validate_adjudication.py ITEMS_DIR OUT_DIR

Per article of ITEMS_DIR (``items/<article>/``):

- ``OUT_DIR/decisions/<article>.json`` decides every disputed item exactly once, with ``confirm`` or ``correct``
  and a reason;
- ``OUT_DIR/adjudicated/<article>.json`` passes the label check of ``validate_labels.py`` against the packet
  (format, keys, hashes, window, every quote at its code point, value sets);
- the adjudicated file, without its ``adjudication`` key, is compared with ``locked.json``: the JSON paths that
  differ are listed, so that they can be compared with the corrections the adjudicator reported.

Prints one JSON report; exit 0 when every article passes the first two checks.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "annotations"))
import validate_labels


def diff(a: Any, b: Any, path: str = "") -> list[str]:
    if isinstance(a, dict) and isinstance(b, dict):
        out: list[str] = []
        for k in sorted(set(a) | set(b)):
            out += diff(a.get(k, "<absent>"), b.get(k, "<absent>"), f"{path}.{k}")
        return out
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return [p for i, (x, y) in enumerate(zip(a, b, strict=True)) for p in diff(x, y, f"{path}[{i}]")]
    return [] if a == b else [path or "."]


def main() -> int:
    items, out = Path(sys.argv[1]), Path(sys.argv[2])
    report: dict[str, Any] = {}
    ok = True
    for art in sorted(p for p in items.iterdir() if p.is_dir()):
        r: dict[str, Any] = {"problems": []}
        disputed = json.loads((art / "disputed_items.json").read_text(encoding="utf-8"))
        dec_path, adj_path = out / "decisions" / f"{art.name}.json", out / "adjudicated" / f"{art.name}.json"
        if not dec_path.exists() or not adj_path.exists():
            r["problems"].append("missing decisions or adjudicated file")
        else:
            dec = json.loads(dec_path.read_text(encoding="utf-8"))
            seen = [d.get("item") for d in dec.get("decisions", [])]
            if sorted(seen) != list(range(len(disputed))):
                r["problems"].append(f"items decided {sorted(seen)} != 0..{len(disputed) - 1}")
            for d in dec.get("decisions", []):
                if d.get("decision") not in ("confirm", "correct") or not d.get("reason"):
                    r["problems"].append(f"item {d.get('item')}: decision or reason")
            r["confirmed"] = sum(d.get("decision") == "confirm" for d in dec.get("decisions", []))
            r["corrected"] = sum(d.get("decision") == "correct" for d in dec.get("decisions", []))
            r["problems"] += validate_labels.check(art, adj_path)
            adj = json.loads(adj_path.read_text(encoding="utf-8"))
            adj.pop("adjudication", None)
            r["changed_paths"] = diff(json.loads((art / "locked.json").read_text(encoding="utf-8")), adj)
        ok = ok and not r["problems"]
        report[art.name] = r
    sys.stdout.write(json.dumps({"valid": ok, "articles": report}, ensure_ascii=False, indent=1) + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
