"""Exposure inventory for the supplemental final campaign (AMENDMENT_2026-10-29.md section 2).

Usage: python exposure_inventory.py > exposure_inventory.json   (run from the repository root)

Lists every article group this stage has touched, with what was done with it (selected, captured, annotated,
extracted for evaluation, used in a demonstration or a fixture), and the revisions captured. It then checks the
unused selection candidates against that list by page id and title, per wiki. It reads only committed files; it
makes no request. A group that was ever selected, captured or named is exposed, whatever happened to it later.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
S03 = ROOT / "docs" / "verification" / "stage-03"


def main() -> int:
    sel = json.loads((S03 / "evaluation" / "selection" / "selection.json").read_text(encoding="utf-8"))
    groups: dict[str, dict[str, Any]] = {}

    def group(wiki: str, page_id: int | None, title: str | None) -> dict[str, Any]:
        key = f"{wiki}:{page_id}" if page_id else f"{wiki}:title:{title}"
        g = groups.setdefault(
            key, {"wiki": wiki, "page_id": page_id, "titles": set(), "uses": set(), "revisions": set()}
        )
        if title:
            g["titles"].add(title)
        return g

    for wiki in ("ar", "en"):
        for split in ("holdout", "reserve", "confirmation"):
            for a in sel["splits"][wiki][split]:
                group(wiki, a["page_id"], a.get("title"))["uses"].add(f"selected:{split}")
        for a in sel["challenge"][wiki]["selected"]:
            group(wiki, a["page_id"], a.get("title"))["uses"].add("selected:challenge")
    for name in ("dev_selection.json", "dev_selection_supplement.json"):
        for a in json.loads((S03 / "calibration" / name).read_text(encoding="utf-8"))["articles"]:
            group(a["wiki"], None, a["title"])["uses"].add("development")
    roots = [S03, ROOT / "tests" / "stage03" / "fixtures"]
    for root in roots:
        for cap_path in sorted(root.rglob("capture.json")):
            cap = json.loads(cap_path.read_text(encoding="utf-8"))
            page = cap.get("page")
            if not page:
                continue
            g = group(page["wiki"], page["page_id"], page.get("title"))
            g["uses"].add("captured:" + str(cap_path.parent.relative_to(ROOT).parent))
            g["revisions"].add(page["revision_id"])
    for ann in sorted((S03 / "evaluation" / "annotations" / "locked").glob("*.json")):
        if ann.name == "ANNOTATION_LOCK.json":
            continue
        a = json.loads(ann.read_text(encoding="utf-8"))["article"]
        for g in groups.values():
            if a["revision_id"] in g["revisions"] and g["wiki"] == ann.name[:2]:
                g["uses"].add("annotated:run-1")
    for ext in sorted((S03 / "evaluation" / "run-1" / "extractions").glob("*.json")):
        wiki, rev = ext.stem.split("-", 1)
        for g in groups.values():
            if g["wiki"] == wiki and int(rev) in g["revisions"]:
                g["uses"].add("extracted:run-1")
    # Development titles are matched to page ids where a capture of the same title exists.
    by_title = {(g["wiki"], t): g for g in groups.values() if g["page_id"] for t in g["titles"]}
    for key in [k for k, g in groups.items() if not g["page_id"]]:
        g = groups[key]
        match = next((by_title[(g["wiki"], t)] for t in g["titles"] if (g["wiki"], t) in by_title), None)
        if match is not None:
            match["uses"] |= g["uses"]
            del groups[key]
    pool: dict[str, Any] = {}
    for wiki in ("ar", "en"):
        ids = {g["page_id"] for g in groups.values() if g["wiki"] == wiki and g["page_id"]}
        titles = {t for g in groups.values() if g["wiki"] == wiki for t in g["titles"]}
        unused = sel["splits"][wiki]["unused"]
        pool[wiki] = {
            "unused_candidates": len(unused),
            "overlap_by_page_id": [a for a in unused if a["page_id"] in ids],
            "overlap_by_title": [a for a in unused if a.get("title") in titles],
        }
    out = {
        "groups": [
            {**g, "titles": sorted(g["titles"]), "uses": sorted(g["uses"]), "revisions": sorted(g["revisions"])}
            for _, g in sorted(groups.items())
        ],
        "group_count": {w: sum(1 for g in groups.values() if g["wiki"] == w) for w in ("ar", "en")},
        "unused_pool_check": pool,
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
