"""S-1 to S-4: the identity of a short footnote follows Module:Footnotes, per wiki. SYNTHETIC.

Module:Footnotes (enwiki ``sfn``) names the reference it generates ``FOOTNOTE`` + the positional arguments 1-5 +
``p``/``page`` + ``pp``/``pages`` + ``at``/``loc``, with runs of whitespace as one space, and passes ``group=``.
arwiki's Module:Footnotes (``وحدة:Footnotes``, ``sfn``) builds the name the same way from ``p``/``page``,
``pp``/``pages`` and ``loc`` only, keeps whitespace as written, and passes no group. Calls with one name (and group)
are one reference: identical content makes the later calls reuses, different content is a Cite conflict. Sources
retained in ``docs/verification/stage-03/design/sfn-semantics/``. These cases are synthetic regressions, not
evaluation evidence.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from wiki_support import bundle, codes, extract


def short(doc: dict[str, Any]) -> list[tuple[str, str, int]]:
    return [
        (c["group"], c["binding_state"], len(c["definitions"]))
        for c in doc["containers"]
        if c["layout"] == "short_footnote"
    ]


@pytest.mark.regression
@pytest.mark.parametrize(
    ("wiki", "text"),
    [
        ("en", "A{{sfn|Smith|2001|p=5}} B{{sfn|Smith|2001|page=5}}"),
        ("ar", "أ{{Sfn|سميث|2001|p=5}} ب{{Sfn|سميث|2001|page=5}}"),
        ("en", "A{{sfn|Smith|2001|pp=5-6}} B{{sfn|Smith|2001|pages=5-6}}"),
        ("en", "A{{sfn|Smith|2001|loc=ch. 2}} B{{sfn|Smith|2001|at=ch. 2}}"),
    ],
)
def test_parameter_aliases_name_one_reference(tmp_path: Path, wiki: str, text: str) -> None:
    """S-2: an alias spelling of the same location argument gives the same name and the same note text."""
    doc = extract(bundle(tmp_path, text, wiki=wiki))
    assert short(doc) == [("", "identical_definitions", 2)]
    (container,) = [c for c in doc["containers"] if c["layout"] == "short_footnote"]
    assert len(container["use_ids"]) == 2


@pytest.mark.regression
@pytest.mark.parametrize(
    ("wiki", "text"),
    [
        ("en", "A{{sfn|Smith|2001|p=5}} B{{sfn|Smith|2001|p=5|ps=none}}"),
        ("en", "A{{sfn|Smith|2001}} B{{sfnp|Smith|2001}}"),
        ("en", "A{{sfn|Smith|2001|ref=x}} B{{sfn|Smith|2001}}"),
        ("ar", "أ{{Sfn|سميث|2001|ps=؛}} ب{{Sfn|سميث|2001}}"),
    ],
)
def test_same_name_with_different_text_is_a_conflict(tmp_path: Path, wiki: str, text: str) -> None:
    """S-3, S-4: the postscript, the anchor and the template variant change the note text but not its name."""
    doc = extract(bundle(tmp_path, text, wiki=wiki))
    assert short(doc) == [("", "conflicting_definitions", 2)]
    assert "REF_DEFINITIONS_CONFLICT" in codes(doc)


@pytest.mark.regression
def test_enwiki_group_is_the_reference_group(tmp_path: Path) -> None:
    """S-1: enwiki's module passes group= to the ref; the same name in two groups is two references."""
    doc = extract(bundle(tmp_path, "A{{sfn|Smith|2001|group=n}} B{{sfn|Smith|2001|group=n}} C{{sfn|Smith|2001}}"))
    assert sorted(short(doc)) == [("", "single_definition", 1), ("n", "identical_definitions", 2)]
    assert sorted(u["group"] for u in doc["uses"]) == ["", "n", "n"]


@pytest.mark.regression
def test_arwiki_module_takes_no_group(tmp_path: Path) -> None:
    """S-1: arwiki's module ignores group= (its ref has a name only), so these calls are one reference."""
    doc = extract(bundle(tmp_path, "أ{{Sfn|سميث|2001|group=n}} ب{{Sfn|سميث|2001}}", wiki="ar"))
    assert short(doc) == [("", "identical_definitions", 2)]


@pytest.mark.regression
def test_arwiki_has_no_at_alias(tmp_path: Path) -> None:
    """arwiki's module reads loc= only: at= changes neither the name nor the text there."""
    doc = extract(bundle(tmp_path, "أ{{Sfn|سميث|2001|at=ف 2}} ب{{Sfn|سميث|2001}}", wiki="ar"))
    assert short(doc) == [("", "identical_definitions", 2)]
    en = extract(bundle(tmp_path, "A{{sfn|Smith|2001|at=ch 2}} B{{sfn|Smith|2001}}", name="e"))
    assert len(short(en)) == 2


@pytest.mark.regression
def test_whitespace_in_the_name(tmp_path: Path) -> None:
    """enwiki collapses whitespace in the name (one reference, but the text differs: a conflict); arwiki keeps it
    (two references)."""
    en = extract(bundle(tmp_path, "A{{sfn|Smith  J|2001}} B{{sfn|Smith J|2001}}"))
    assert short(en) == [("", "conflicting_definitions", 2)]
    ar = extract(bundle(tmp_path, "أ{{Sfn|سميث  ج|2001}} ب{{Sfn|سميث ج|2001}}", wiki="ar", name="a"))
    assert len(short(ar)) == 2


@pytest.mark.regression
@pytest.mark.parametrize("wiki", ["en", "ar"])
def test_distinct_locations_stay_distinct(tmp_path: Path, wiki: str) -> None:
    """Calls that MediaWiki names differently are never merged."""
    doc = extract(
        bundle(tmp_path, "A{{sfn|Smith|2001|p=5}} B{{sfn|Smith|2001|p=6}} C{{sfn|Smith|2002|p=5}}", wiki=wiki)
    )
    assert len(short(doc)) == 3


@pytest.mark.regression
def test_name_collisions_across_fields_stay_split(tmp_path: Path) -> None:
    """Declared conservative boundary: p=5 and pp=5 both give the name FOOTNOTESmith20015, which MediaWiki treats as
    one reference with conflicting text. The engine keeps the fields apart and splits them; the render step then
    withdraws the shared note from both containers rather than attach it to one."""
    doc = extract(bundle(tmp_path, "A{{sfn|Smith|2001|p=5}} B{{sfn|Smith|2001|pp=5}}"))
    assert len(short(doc)) == 2
