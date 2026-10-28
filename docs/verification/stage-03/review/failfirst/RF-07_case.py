"""RF-07 fail-first case: anonymous footnote markers in an order that contradicts the reference list.

Source: two anonymous refs, "one" then "two". Render: the marker of note 2 comes first, then the marker of note 1,
while the list still numbers "one" as 1 and "two" as 2 (a render that does not follow the saved source's order).
Expected: no use is linked to the other reference's marker; the segment is abstained or paired by content.
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "tests" / "stage03"))
from wiki_support import bundle, extract, note_li, ref_sup, references

TEXT = "A.<ref>one</ref> B.<ref>two</ref>\n"
BODY = (
    "<p>A."
    + ref_sup(2, "cite_note-2", "cite_ref-2")
    + " B."
    + ref_sup(1, "cite_note-1", "cite_ref-1")
    + "</p>"
    + references([note_li("cite_note-1", ["cite_ref-1"], "one"), note_li("cite_note-2", ["cite_ref-2"], "two")])
)
with tempfile.TemporaryDirectory() as tmp:
    doc = extract(bundle(Path(tmp), TEXT, BODY))
by_container = {c["id"]: c for c in doc["containers"]}
rows = [
    {
        "use_text": TEXT[u["source"]["cp_start"] : u["source"]["cp_end"]],
        "state": u["render"]["state"],
        "marker": (u["render"].get("locator") or {}).get("element_id"),
        "container_note": by_container[u["container_id"]]["render"].get("region_id"),
    }
    for u in doc["uses"]
]
print(json.dumps({"uses": rows, "issues": sorted({i["code"] for i in doc["issues"]})}, indent=1))
