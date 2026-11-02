"""The prospective scorer v2 (``protocol/scripts/evaluate_v2.py``) counts reference definitions by the definition rule
of ``design/sfn-semantics/SEMANTIC_DECISION.md`` (D2/D6), and changes nothing else. SYNTHETIC."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

import pytest
from wiki_support import bundle, extract

SCRIPTS = Path(__file__).resolve().parents[2] / "docs/verification/stage-03/protocol/scripts"
sys.path.insert(0, str(SCRIPTS))
v1 = importlib.import_module("evaluate")
v2 = importlib.import_module("evaluate_v2")

TEXT = (
    "A.{{sfn|Smith|2001}} B.{{sfn|Smith|2001}} C.{{sfn|Smith|2001|page=3}} D.{{sfn|Smith|2001|p=3}}"
    ' E.<ref name="j">{{cite journal|title=T|doi=10.1000/j}}</ref>'
    ' F.<ref name="j">{{cite journal|title=T|doi=10.1000/j}}</ref>'
    ' G.<ref name="k">X</ref> H.<ref name="k">Y</ref> I.<ref name="k">X</ref>\n'
)


def at(text: str, needle: str, n: int = 1) -> dict[str, Any]:
    cp = -1
    for _ in range(n):
        cp = text.index(needle, cp + 1)
    return {"cp": cp, "quote": text[cp : cp + 12]}


def labels(text: str, art: Any) -> dict[str, Any]:
    """Guide v1.1 labels: the first occurrence of each reference content is a definition, every call is a use."""

    def d(needle: str, n: int = 1, templates: list[dict[str, Any]] | None = None, unstructured: bool = False) -> Any:
        return {
            "at": at(text, needle, n),
            "in_window": True,
            "kind": "generated_note" if needle.startswith("{{sfn") else "note",
            "name": None,
            "group": "",
            "templates": templates or [],
            "unstructured": unstructured,
            "render_note_id": None,
            "marker": "cannot_tell",
            "marker_text": None,
        }

    definitions = [
        d("{{sfn|Smith|2001}}"),
        d("{{sfn|Smith|2001|page=3}}"),
        d('<ref name="j">', templates=[{"at": at(text, "{{cite journal")}]),
        d('<ref name="k">', unstructured=True),
        d('<ref name="k">', 2, unstructured=True),
    ]
    return {
        "article": {"revision_id": art.revision_id, "source_sha256": art.source_sha256, "window": list(art.window)},
        "definitions": definitions,
        "uses": [],
        "identifiers": [],
    }


@pytest.mark.regression
def test_v2_counts_reference_definitions_and_their_units(tmp_path: Path) -> None:
    path = bundle(tmp_path, TEXT)
    doc = extract(path)
    art = v1.load_bundle(path)
    ann = labels(art.text, art)
    old = v1.score_article(art, ann, v1.engine_predictions(doc))
    new = v1.score_article(art, ann, v2.engine_predictions_v2(doc, art.text))
    # 9 occurrences, 5 reference definitions (the sfn pair, the alias pair, j twice identical, k as X, Y, X).
    assert (old["definitions"]["tp"], old["definitions"]["fp"]) == (5, 4)
    assert (new["definitions"]["tp"], new["definitions"]["fp"], new["definitions"]["fn"]) == (5, 0, 0)
    # The repeated identical {{cite journal}} body is not a second unit; units of the k conflict stay.
    assert (new["units"]["tp"], new["units"]["fp"], new["units"]["fn"]) == (3, 0, 0)
    assert old["units"]["fp"] == 2
    # Nothing else moves.
    for part in ("uses", "identifiers"):
        assert old[part] == new[part]


@pytest.mark.regression
def test_v2_is_v1_without_repeats(tmp_path: Path) -> None:
    path = bundle(tmp_path, 'A.<ref name="a">X</ref> B.<ref name="a"/> C.{{sfn|Smith|2001}}\n')
    doc = extract(path)
    art = v1.load_bundle(path)
    assert v2.repeat_definitions(doc, art.text) == set()
    assert v2.engine_predictions_v2(doc, art.text) == v1.engine_predictions(doc)
