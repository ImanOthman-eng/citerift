"""RF-05 fail-first case: replay of a recorded extraction whose configuration is not a valid configuration.

A recorded document is edited so that its ``config`` holds an unknown key or an out-of-range value, then
``citerift-wiki replay --extraction`` is run. Expected: the recorded document is refused as invalid (exit 3,
BUNDLE_SCHEMA_INVALID); never an internal error (exit 1).
"""

import io
import json
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "tests" / "stage03"))
from wiki_support import bundle

from citerift.wiki.canonical import canonical_bytes
from citerift.wiki.cli import main
from citerift.wiki.extract import extract_bundle

rows = []
with tempfile.TemporaryDirectory() as tmp:
    b = bundle(Path(tmp), "A<ref>{{cite journal |doi=10.1000/x}}</ref>\n")
    doc = extract_bundle(b, isolated=False)
    for n, change in enumerate([{"bogus": 1}, {"max_depth": 0}, {"worker_wall_s": -5}]):
        edited = json.loads(json.dumps(doc))
        edited["config"].update(change)
        path = Path(tmp) / f"r{n}.json"
        path.write_bytes(canonical_bytes(edited))
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(["replay", "--bundle", str(b), "--extraction", str(path)])
        rows.append({"config_change": change, "exit": code, "stderr": err.getvalue().strip()[:200]})
print(json.dumps(rows, indent=1))
