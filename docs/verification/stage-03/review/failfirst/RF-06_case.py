"""RF-06 fail-first case: replay against a recorded extraction whose content was altered but whose digest was kept.

The recorded document's identifier key is changed while ``extraction_digest`` keeps the original value. Expected:
replay does not report ``reproduced``; the recorded document fails its own digest check (BUNDLE_DIGEST_MISMATCH).
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

with tempfile.TemporaryDirectory() as tmp:
    b = bundle(Path(tmp), "A<ref>{{cite journal |doi=10.1000/x}}</ref>\n")
    doc = extract_bundle(b, isolated=False)
    edited = json.loads(json.dumps(doc))
    edited["identifiers"][0]["normalization"]["normalized"] = "10.1000/forged"
    path = Path(tmp) / "recorded.json"
    path.write_bytes(canonical_bytes(edited))
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(["replay", "--bundle", str(b), "--extraction", str(path)])
    report = json.loads(out.getvalue())
    print(
        json.dumps(
            {
                "exit": code,
                "verified": report["verified"],
                "replay_state": report["replay"]["state"],
                "issues": sorted({i["code"] for i in report["issues"]}),
            },
            indent=1,
        )
    )
