"""Verify every extraction written by ``extract_all.py`` against its retained bundle (review 2, RV2-1 and RV2-10:
the differential compares documents; this checks that each document verifies offline).

Usage, from the repository root: ``python verify_all.py <extractions dir>``. Prints one line per bundle that does not
verify, then the totals.
"""

import json
import sys
from pathlib import Path

from citerift.wiki.verify import verify_bundle

out = Path(sys.argv[1])
listing = json.loads((out / "_bundles.json").read_text(encoding="utf-8"))
failed = 0
for rel in listing:
    doc = json.loads((out / (rel.replace("/", "__") + ".json")).read_text(encoding="utf-8"))
    report = verify_bundle(Path(rel), doc)
    if report["verified"] is not True:
        failed += 1
        print(rel, sorted({(i["code"], (i.get("detail") or "")[:80]) for i in report["issues"]})[:6])
print(f"{len(listing)} bundles, {len(listing) - failed} verified, {failed} not verified")
