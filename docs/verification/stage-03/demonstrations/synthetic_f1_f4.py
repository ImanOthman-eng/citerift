"""SYNTHETIC demonstrations of the F1-F4 repairs: build capture bundles for the reviewed cases, offline.

Usage: python synthetic_f1_f4.py OUT_DIR   (run from the repository root)

Each case is captured through the production capture code with a scripted transport (no network): an Action API
answer for the SYNTHETIC wikitext and, where the case needs one, a minimal Parsoid HTML 2.8.0 render. The bundles
are written to OUT_DIR/<case>; run_demos.sh then runs the production CLI (verify, extract, verify --extraction,
replay) on them. These are synthetic inputs, not observed Wikipedia revisions.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tests" / "stage03"))

from wiki_support import bundle, note_li, ref_sup, references  # noqa: E402

EN = 'A.<ref name="a">Smith 2001.</ref>\n'
AR = 'أ.<ref name="a">سميث 2001.</ref>\n'
RED = '<a rel="mw:WikiLink" href="./{href}?action=edit&amp;redlink=1" title="{title}" class="new">{label}</a>'


def note(inner: str, wrap: tuple[str, str] = ("", "")) -> str:
    return (
        "<p>A."
        + ref_sup(1, "cite_note-a-1", "cite_ref-a_1-0", name="a")
        + "</p>"
        + wrap[0]
        + references([note_li("cite_note-a-1", ["cite_ref-a_1-0"], inner)])
        + wrap[1]
    )


CASES: dict[str, tuple[str, str, str | None]] = {
    "F1-en-span": ("en", EN, note("Paper. <span>Re</span>tracted.")),
    "F1-ar-comment": ("ar", AR, note("ورقة. مس<!--x-->حوب.")),
    "F2-en-red-link-label": (
        "en",
        EN,
        note("Paper. " + RED.format(href="Missing_page", title="Missing page", label="Retracted")),
    ),
    "F2-ar-missing-marker-template": (
        "ar",
        AR,
        note("ورقة. " + RED.format(href="قالب:Retracted", title="قالب:Retracted", label="قالب:Retracted")),
    ),
    "F3-en-hidden-ancestor": ("en", EN, note("Paper. Retracted.", ('<div style="display:none">', "</div>"))),
    "F3-ar-hidden-ancestor": ("ar", AR, note("ورقة. مسحوب.", ('<div style="display:none">', "</div>"))),
    "F4-en-numbered-reuse": ("en", 'A.<ref name="a">Paper</ref> B.{{r|1=a}}', None),
    "F4-ar-numbered-reuse": ("ar", 'A.<ref name="a">Paper</ref> B.{{استشهاد متعدد|1=a}}', None),
}


def main() -> int:
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=False)
    made = {}
    for name, (wiki, text, body) in CASES.items():
        path = bundle(out, text, body, wiki=wiki, name=name)
        made[name] = {"wiki": wiki, "bundle": str(path.relative_to(out)), "render": body is not None}
    (out / "cases.json").write_text(json.dumps(made, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
