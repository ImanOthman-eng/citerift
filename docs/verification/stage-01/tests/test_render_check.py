# ruff: noqa: S101 - pytest assertions
"""Deterministic tests of the rendered-reference check (no network).

Run: uv run pytest docs/verification/stage-01/tests
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.negative]

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "stage01_probe.py"
spec = importlib.util.spec_from_file_location("stage01_probe_render", SCRIPT)
assert spec and spec.loader
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

DOI = "10.1038/nature12968"
LINK = '<a class="external text" href="https://doi.org/10.1038%2Fnature12968">10.1038/nature12968</a>'
EN_WARNING = '<span class="error">(Retracted, see <a href="https://doi.org/10.1038%2Fnature13598">doi</a>)</span>'
AR_REDLINK = (
    '<a href="/w/index.php?title=%D9%82%D8%A7%D9%84%D8%A8:Retracted&amp;action=edit&amp;redlink=1" class="new" '
    'title="قالب:Retracted (الصفحة غير موجودة)">قالب:Retracted</a>'
)


def page(*items: str) -> str:
    lis = "".join(f'<li id="cite_note-{i}"><span class="reference-text">{t}</span></li>' for i, t in enumerate(items))
    return f'<div class="mw-parser-output"><p>Text.</p><ol class="references">{lis}</ol></div>'


def parse(text: Any, status: Any = 200) -> dict[str, Any]:
    body = (
        {"parse": {"title": "T", "revid": 1, "text": text}} if text is not None else {"error": {"code": "nosuchrevid"}}
    )
    return {"url": "u", "status": status, "retrieved_at": "t", "body": body}


class FakeClient:
    def __init__(self, res: dict[str, Any]) -> None:
        self.res = res
        self.params: dict[str, str] = {}

    def get(self, url: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        self.params = params or {}
        return self.res


def check(res: dict[str, Any]) -> dict[str, Any]:
    client = FakeClient(res)
    out = probe.render_check(client, "ar", 1, DOI)
    assert client.params["action"] == "parse" and client.params["oldid"] == "1"
    return out


def test_english_template_output_is_warning_text() -> None:
    out = check(parse(page("Other ref", "Obokata. Nature. " + LINK + " " + EN_WARNING)))
    assert out["state"] == "warning_text_in_rendered_reference"
    [ref] = out["references"]
    assert ref["warning_terms"][0]["term"].casefold() == "retract" and ref["missing_page_links"] == []


def test_missing_template_renders_as_link_not_warning() -> None:
    out = check(parse(page("أوبوكاتا. " + LINK + " " + AR_REDLINK)))
    assert out["state"] == "missing_template_link_only_in_rendered_reference"
    [ref] = out["references"]
    assert ref["warning_terms"] == [] and "قالب:Retracted" in ref["text_excerpt"]
    assert ref["missing_page_links"] == ["قالب:Retracted (الصفحة غير موجودة)"]


def test_arabic_warning_word_counts() -> None:
    out = check(parse(page("أوبوكاتا. " + LINK + " ورقة مسحوبة")))
    assert out["state"] == "warning_text_in_rendered_reference"


def test_doi_in_another_reference_only_is_not_found() -> None:
    assert check(parse(page("Other ref 10.1038/nature13598")))["state"] == "reference_not_found_in_render"


def test_entity_encoded_list_item_id_is_matched() -> None:
    """MediaWiki's parser output writes the reference id as cite&#95;note-N (observed on enwiki, 2026-10-27)."""
    html = page("Paper " + LINK + " " + EN_WARNING).replace('id="cite_note', 'id="cite&#95;note')
    assert check(parse(html))["state"] == "warning_text_in_rendered_reference"


def test_encoded_doi_link_is_matched() -> None:
    encoded = '<a href="https://doi.org/10.1038%2Fnature12968">doi</a>'
    assert check(parse(page("Paper " + encoded)))["references"]


@pytest.mark.parametrize("res", [parse(None), parse(page(LINK), status="failed"), parse(42)])
def test_unavailable_render_is_never_absence(res: dict[str, Any]) -> None:
    assert check(res)["state"] == "render_unavailable"


def test_reference_without_any_warning() -> None:
    assert check(parse(page("Paper " + LINK)))["state"] == "no_warning_text_in_inspected_rendered_reference"


def test_one_unwarned_reference_among_several_is_mixed_not_warning_text() -> None:
    out = check(parse(page(LINK + " " + EN_WARNING, LINK)))
    assert out["state"] == "mixed" and [r["state"] for r in out["references"]] == ["warning_text", "no_warning_text"]


def test_longer_doi_with_same_prefix_is_not_matched() -> None:
    longer = '<a href="https://doi.org/10.1038%2Fnature129681">10.1038/nature129681</a>'
    assert check(parse(page("Other paper " + longer + " " + EN_WARNING)))["state"] == "reference_not_found_in_render"


def test_retracted_word_in_cited_title_is_not_a_warning() -> None:
    cite = '<cite class="citation journal">"RETRACTED ARTICLE: Stimulus-triggered fate conversion". ' + LINK + "</cite>"
    out = check(parse(page(cite)))
    assert out["state"] == "no_warning_text_in_inspected_rendered_reference"
    assert "RETRACTED ARTICLE" in out["references"][0]["text_excerpt"]
