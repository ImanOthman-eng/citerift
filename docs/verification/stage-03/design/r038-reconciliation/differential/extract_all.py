"""Extract every retained real bundle with the engine of the current tree (in process, default configuration)."""

import json
import sys
from pathlib import Path

from citerift.wiki.extract import ExtractConfig, extract_bundle, write_canonical

root = Path(sys.argv[1])
out = Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
listing = []
for cap in sorted(root.glob("docs/verification/stage-03/**/capture.json")):
    rel = cap.parent.relative_to(root).as_posix()
    c = json.loads(cap.read_text(encoding="utf-8"))
    title = (c.get("page") or {}).get("title") or ""
    if "SYNTHETIC" in title.upper() or "/synthetic" in rel:
        continue
    doc = extract_bundle(cap.parent, ExtractConfig(), isolated=False)
    name = rel.replace("/", "__")
    (out / f"{name}.json").write_bytes(write_canonical(doc))
    listing.append(rel)
(out / "_bundles.json").write_text(json.dumps(listing, indent=1))
print(len(listing))
