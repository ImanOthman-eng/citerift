import json
import sys
from pathlib import Path

from citerift.wiki.extract import extract_bundle

root = Path(sys.argv[1])
out = {}
for cap in sorted(root.glob("docs/verification/stage-03/**/capture.json")):
    d = extract_bundle(cap.parent)
    out[str(cap.parent.relative_to(root))] = {
        "uses": [(u["origin"], u["name"], u["binding"], u["container_id"], u["render"]["state"]) for u in d["uses"]],
        "containers": [(c["kind"], c["name"], c["binding_state"]) for c in d["containers"]],
        "ids": sorted((i["role"], i["normalization"]["normalized"] or "") for i in d["identifiers"]),
        "issues": sorted(i["code"] for i in d["issues"]),
    }
json.dump(out, sys.stdout, ensure_ascii=False)
