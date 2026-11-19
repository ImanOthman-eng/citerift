"""Development survey of (citation, Stage 02 event) pairs under bib-1 (owner decision D-083; read-only, descriptive).

Usage: ``uv run python survey_pairs.py <Stage 02 index .sqlite> <output .json outside the repository>``

Over every development bundle with a committed source artifact (the 232 Step 13 development revisions, the 80
articles of evaluation 1 and the 100 articles of evaluation 2, all design-exposed), every citation template (any depth)
whose ``doi`` or ``pmid`` argument reaches a Stage 02 event as an original identifier gives one pair per distinct event.
Each pair is described by the bib-1 code (``citerift.investigation.bibliographic``): authors and title verdicts, title
relation, designation, year and the object verdict. No label, adjudication or score of either campaign is read; the
counts set no threshold (bib-1 has none). The Stage 02 index is read only through ``citerift.retraction.query.Index``.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import mwparserfromhell

from citerift.investigation import bibliographic as B
from citerift.retraction.query import Index

REPO = Path(__file__).resolve().parents[5]
S04 = REPO / "docs" / "verification" / "stage-04"
CITE_PREFIXES = ("cite", "citation", "استشهاد", "مرجع")


def bundles() -> list[tuple[str, Path]]:
    dev = json.loads((S04 / "evaluation" / "dev" / "DEV_RUN.json").read_text(encoding="utf-8"))
    out = [("development-232", REPO / v["bundle"]) for v in dev["revisions"].values()]
    for tag, rel in (("evaluation-1", "evaluation-campaign"), ("evaluation-2", "evaluation-p2-campaign")):
        out += [(tag, p) for p in sorted((S04 / rel / "bundles").iterdir())]
    return out


def main() -> None:
    index = Index(Path(sys.argv[1]))
    target = Path(sys.argv[2]).resolve()
    if target.is_relative_to(REPO):
        raise SystemExit("write the survey outside the repository")
    pairs: list[dict[str, Any]] = []
    skipped: list[str] = []
    for tag, bundle in bundles():
        cap = json.loads((bundle / "capture.json").read_text(encoding="utf-8"))
        art = bundle / "artifacts" / cap["source"]["artifact"] if cap.get("source") else None
        if art is None or not art.exists():
            skipped.append(bundle.name)
            continue
        wiki = bundle.name.split("-", 1)[0]
        text = art.read_bytes().decode("utf-8")
        for t in mwparserfromhell.parse(text).filter_templates(recursive=True):
            if not str(t.name).strip().lower().startswith(CITE_PREFIXES):
                continue
            args = {str(p.name).strip(): str(p.value).strip() for p in t.params}
            doi, pmid = args.get("doi", "").lower(), args.get("pmid", "")
            events = (index.events_by("original_doi", doi) if doi else []) + (
                index.events_by("original_pmid", pmid) if pmid.isdigit() else []
            )
            cited = B.cited_object(str(t), wiki)
            seen: set[str] = set()
            for e in events:
                if e["event_id"] in seen:
                    continue
                seen.add(e["event_id"])
                rec = B.RecordObject.from_json(e)
                cmp = B.compare(cited, rec).to_json()
                pairs.append({"set": tag, "bundle": bundle.name, "event_id": e["event_id"], **cmp})
    summary = {
        "bundles_skipped_without_source": skipped,
        "pairs": len(pairs),
        "by_set": dict(Counter(p["set"] for p in pairs)),
        "authors": dict(Counter(p["authors"] for p in pairs)),
        "title_relation": dict(Counter(p["title_relation"] for p in pairs)),
        "designation": sum(p["designation"] for p in pairs),
        "year": dict(Counter(p["year"] for p in pairs)),
        "object": dict(Counter(p["object"] for p in pairs)),
        "material_conflicts": [p for p in pairs if p["object"] == B.MATERIAL_CONFLICT],
    }
    target.write_text(json.dumps({"summary": summary, "pairs": pairs}, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "material_conflicts"}, indent=1, ensure_ascii=False))
    for p in summary["material_conflicts"]:
        print("MATERIAL_CONFLICT", p["set"], p["bundle"], p["event_id"], p["reasons"])


if __name__ == "__main__":
    main()
