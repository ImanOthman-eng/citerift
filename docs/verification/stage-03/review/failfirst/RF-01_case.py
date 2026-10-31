"""RF-01 fail-first case: a citation parameter given twice. MediaWiki uses the last value; the earlier one is
never rendered, so it must not be reported as the cited work's identifier (SYNTHETIC input)."""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "tests" / "stage03"))
from wiki_support import bundle, extract

TEXT = "A<ref>{{cite journal |title=T |doi=10.1000/shadowed |doi=10.1000/effective}}</ref>\n"
with tempfile.TemporaryDirectory() as tmp:
    doc = extract(bundle(Path(tmp), TEXT))
rows = [{"raw": i["source"]["raw"], "role": i["role"], "role_reason": i["role_reason"]} for i in doc["identifiers"]]
print(json.dumps({"identifiers": rows, "issues": sorted({i["code"] for i in doc["issues"]})}, indent=1))
