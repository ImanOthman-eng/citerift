"""Diagnostic: marker states and evidence over every retained real bundle (old data, regression use only)."""

import json
import sys
from pathlib import Path

from citerift.wiki.extract import extract_bundle

root = Path(sys.argv[1])
out = {}
for cap in sorted(root.glob("docs/verification/stage-03/**/capture.json")):
    b = cap.parent
    try:
        d = extract_bundle(b)
    except Exception as e:
        out[str(b.relative_to(root))] = {"error": repr(e)}
        continue
    out[str(b.relative_to(root))] = {
        m["container_id"]: [m["state"], sorted((e["kind"], e["part"], e["matched"]) for e in m["evidence"])]
        for m in d["markers"]
    }
json.dump(out, sys.stdout, ensure_ascii=False, indent=0)
