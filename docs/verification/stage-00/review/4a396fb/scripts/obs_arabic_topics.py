"""Observation O-1: topic folding covers case, separators and format (Cf) characters, as documented.
Arabic tatweel (U+0640, a justification character) and harakat (combining marks) are not folded, so two
accepted decisions whose Arabic topics differ only by them are not a DECISION_CONTRADICTION."""
import pathlib
import tempfile

from lib import new_sandbox  # noqa: F401  (sets sys.path)
from citerift.governance import memory

for label, a, b in (("tatweel", "قرار", "قـرار"),
                    ("fatha", "قرار", "قَرار"),
                    ("control: zero-width joiner", "قرار", "ق‍رار")):
    text = "# D\n" + "".join(f"\n## D-00{i} — t\n- Status: accepted\n- Topic: {t}\n" for i, t in ((1, a), (2, b)))
    p = pathlib.Path(tempfile.mkdtemp()) / "DECISIONS.md"
    p.write_text(text, encoding="utf-8")
    _, problems = memory.check_decisions(p)
    print(f"{label}: {[x.code for x in problems] or 'no problem'}")
