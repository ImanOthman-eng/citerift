"""RF-02 fail-first case: the only warning term in a reference's rendered region is in text the HTML hides
(display:none). Visibility is never evaluated, so the region must not be reported as having no warning
(SYNTHETIC input)."""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "tests" / "stage03"))
from wiki_support import bundle, doi_link, extract, note_li, ref_sup, references

TEXT = 'A.<ref name="a">{{cite journal |title=Paper |doi=10.1000/p}}</ref>\n'
HIDDEN = '<span style="display:none">Retracted</span>'
BODY = (
    "<p>A."
    + ref_sup(1, "cite_note-a-1", "cite_ref-a_1-0", name="a")
    + "</p>"
    + references(
        [note_li("cite_note-a-1", ["cite_ref-a_1-0"], "<cite>Paper " + doi_link("10.1000/p") + "</cite>" + HIDDEN)]
    )
)
with tempfile.TemporaryDirectory() as tmp:
    doc = extract(bundle(Path(tmp), TEXT, BODY))
m = doc["markers"][0]
print(json.dumps({"state": m["state"], "reason": m["reason"], "evidence": m["evidence"]}, indent=1, ensure_ascii=False))
