"""Adjudicator inputs (ADJUDICATION_BRIEF_v1.1.md) from the disagreement listing.

Usage (from the repository root): python make_adjudication_items.py DISAGREEMENTS_JSON SPEC_JSON PACKETS_ROOT OUT_DIR

For every article with at least one disputed item, OUT_DIR/<instance>/items/<article>/ gets the packet files
(``source.wikitext``, ``render.html``, ``packet.json``, byte copies from PACKETS_ROOT/**/packets/<article>/), the
locked label as ``locked.json`` (byte copy) and ``disputed_items.json`` (the listed items, numbered from 0).
Articles are grouped per wiki and split, in listing order, into instances of at most 6 articles, as even as
possible. OUT_DIR/ASSIGNMENT.json lists them. No label is changed and no extraction document is copied.
"""

from __future__ import annotations

import json
import math
import shutil
import sys
from pathlib import Path
from typing import Any

MAX_PER_INSTANCE = 6


def main() -> int:
    dis = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    spec = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    packets = {p.name: p for p in Path(sys.argv[3]).glob("**/packets/*") if p.is_dir()}
    out = Path(sys.argv[4])
    locked = {Path(e["locked"]).stem: Path(e["locked"]) for entries in spec["splits"].values() for e in entries}
    out.mkdir(parents=True, exist_ok=False)
    assignment: list[dict[str, Any]] = []
    for split, arts in dis.items():
        groups: dict[str, list[dict[str, Any]]] = {}
        for a in arts:
            if a["items"]:
                groups.setdefault(a["article"].split("-")[0], []).append(a)
        for wiki, rows in groups.items():
            n = math.ceil(len(rows) / MAX_PER_INSTANCE)
            size, extra = divmod(len(rows), n)
            start = 0
            for i in range(n):
                part = rows[start : start + size + (i < extra)]
                start += len(part)
                name = f"{wiki}-{'g' if split == 'gate' else 'c'}{i + 1}"
                for a in part:
                    d = out / name / "items" / a["article"]
                    d.mkdir(parents=True)
                    for f in ("source.wikitext", "render.html", "packet.json"):
                        if (packets[a["article"]] / f).exists():
                            shutil.copyfile(packets[a["article"]] / f, d / f)
                    shutil.copyfile(locked[a["article"]], d / "locked.json")
                    items = [{"item": k, **it} for k, it in enumerate(a["items"])]
                    (d / "disputed_items.json").write_text(
                        json.dumps(items, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
                    )
                assignment.append(
                    {"instance": name, "split": split, "wiki": wiki, "articles": [a["article"] for a in part]}
                )
    (out / "ASSIGNMENT.json").write_text(json.dumps(assignment, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
