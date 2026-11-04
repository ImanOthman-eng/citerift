"""RF-03 fail-first case: two references whose rendered notes carry the same DOM id. Each container was matched
to the id, and the marker region was read from whichever element the id lookup returned (SYNTHETIC input)."""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "tests" / "stage03"))
from wiki_support import bundle, codes, extract, note_li, ref_sup, references

TEXT = 'A.<ref name="a">one</ref> B.<ref name="b">two</ref>\n'
BODY = (
    "<p>A."
    + ref_sup(1, "cite_note-a-1", "cite_ref-a_1-0", name="a")
    + " B."
    + ref_sup(2, "cite_note-a-1", "cite_ref-b_2-0", name="b")
    + "</p>"
    + references(
        [note_li("cite_note-a-1", ["cite_ref-a_1-0"], "one"), note_li("cite_note-a-1", ["cite_ref-b_2-0"], "two")]
    )
)
with tempfile.TemporaryDirectory() as tmp:
    doc = extract(bundle(Path(tmp), TEXT, BODY))
print(
    json.dumps(
        {
            "containers": [{"name": c["name"], "render": c["render"]} for c in doc["containers"]],
            "markers": [
                {
                    "container": m["container_id"],
                    "state": m["state"],
                    "region": (m["region"] or {}).get("locator", {}).get("quote"),
                }
                for m in doc["markers"]
            ],
            "issues": sorted(codes(doc)),
        },
        indent=1,
    )
)
