"""D-035, second independent review (``design/unit-semantics/review2/REVIEW.md``): fail-first regressions.

Every case is SYNTHETIC, built through the production capture code, except the one retained bundle of the final
English holdout (exposed data: regression only).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from test_g5c_unit_semantics import EI2, EI2_PARAMS, bibliography, cs1, kinds, one_note, run, transclusion, unresolved
from wiki_support import bundle, codes, extract, note_li, ref_sup, references

from citerift.wiki.verify import verify_bundle

ROOT = Path(__file__).resolve().parents[2]
OUTSIDE = "IDENTIFIER_OUTSIDE_UNITS"


def ids(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {i["source"]["raw"]: i for i in doc["identifiers"]}


# RV2-1: verification rebuilds the model the way extraction does ------------------------------------------------


@pytest.mark.regression
@pytest.mark.parametrize("wiki", ["en", "ar"])
def test_a_bibliography_entry_with_a_g_unit_verifies(tmp_path: Path, wiki: str) -> None:
    """The marker reconstruction of ``verify`` read no render evidence, so it found no G unit, did not reconcile the
    entry and contradicted the extraction's marker observation of the matched list item."""
    body = bibliography(transclusion(1, "EI2", EI2_PARAMS, cs1("B")))
    path = bundle(tmp_path, f"== S ==\n* {EI2}\n", body, wiki=wiki)
    doc = extract(path)
    assert kinds(doc) == ["unsupported_citation_template"]
    [marker] = doc["markers"]
    assert marker["state"] == "no_recognized_warning_in_inspected_region"
    report = verify_bundle(path, doc)
    assert report["verified"] is True, report["issues"]


@pytest.mark.regression
def test_the_final_holdout_bundle_with_bibliography_g_units_verifies() -> None:
    """Exposed regression: ``en-66266685-a1`` failed verification at 11bb5b2 (6 x BUNDLE_SEMANTIC_INVALID)."""
    path = ROOT / "docs/verification/stage-03/evaluation/final/capture/bundles/holdout/en-66266685-a1"
    doc = extract(path)
    report = verify_bundle(path, doc)
    assert report["verified"] is True, report["issues"]


# RV2-2: a located identifier beside template units is reported, never silent ------------------------------------


@pytest.mark.regression
@pytest.mark.parametrize(
    ("wiki", "line", "own", "body_text"),
    [
        ("en", f"* Smith, J. (2001). ''Own work''. Journal 5. doi:10.1000/own123 {EI2}", "10.1000/own123", "Smith "),
        ("ar", f"* سميث، ج. (2001). ''عمل''. مجلة 5. دوي:10.1000/own123 {EI2}", "10.1000/own123", "سميث "),
    ],
)
def test_a_located_identifier_beside_a_g_unit_on_a_bibliography_line_is_reported(
    tmp_path: Path, wiki: str, line: str, own: str, body_text: str
) -> None:
    body = bibliography(body_text + transclusion(1, "EI2", EI2_PARAMS, cs1("B")))
    doc = run(tmp_path, f"== S ==\n{line}\n", body, wiki)
    assert kinds(doc) == ["unsupported_citation_template"]
    ident = ids(doc)[own]
    assert ident["unit_id"] is None
    assert [i["entities"] for i in doc["issues"] if i["code"] == OUTSIDE] == [[ident["id"]]]


@pytest.mark.regression
def test_a_located_identifier_beside_a_citation_template_in_a_ref_is_reported(tmp_path: Path) -> None:
    text = "A<ref>{{cite journal|title=T|doi=10.1000/tpl}} Also: Smith, J. (2001). doi:10.1000/own123</ref>"
    doc = run(tmp_path, text, None)
    assert kinds(doc) == ["citation_template"]
    ident = ids(doc)["10.1000/own123"]
    assert ident["unit_id"] is None
    assert [i["entities"] for i in doc["issues"] if i["code"] == OUTSIDE] == [[ident["id"]]]


@pytest.mark.negative
def test_identifiers_inside_units_are_not_reported(tmp_path: Path) -> None:
    doc = run(tmp_path, "A<ref>{{cite journal|title=T|doi=10.1000/tpl}}</ref><ref>Smith. doi:10.1000/x</ref>", None)
    assert OUTSIDE not in codes(doc)


# RV2-3: a hand-written entry inside a layout or formatting template stays D ------------------------------------

COLUMNS = (
    "== S ==\n{{Columns-list|colwidth=30em|\n* Smith, J. (2001). ''Own work''. Journal 5. doi:10.1000/own123\n"
    "* Jones, K. (2003). ''Other''. Press. doi:10.1000/own456\n}}\n"
)


@pytest.mark.regression
@pytest.mark.parametrize(
    ("wiki", "text", "body"),
    [
        ("en", COLUMNS, None),
        (
            "en",
            COLUMNS,
            "<h2>S</h2>"
            + transclusion(
                1,
                "Columns-list",
                {"colwidth": "30em", "1": COLUMNS.split("|", 2)[2][:-3]},
                "<ul><li>Smith doi:10.1000/own123</li><li>Jones doi:10.1000/own456</li></ul>",
                tag="div",
            ),
        ),
        ("ar", "== م ==\n{{أعمدة|\n* سميث، ج. (2001). ''عمل''. مجلة 5. دوي:10.1000/own123\n}}\n", None),
    ],
)
def test_hand_written_entries_inside_a_list_layout_template_stay_unstructured(
    tmp_path: Path, wiki: str, text: str, body: str | None
) -> None:
    """A template around the whole list is not part of an entry: the entries' identifiers are their own text."""
    doc = run(tmp_path, text, body, wiki)
    entries = [c["id"] for c in doc["containers"] if c["kind"] == "bibliography_entry"]
    assert kinds(doc) == ["unstructured_text"] * len(entries) and entries
    assert unresolved(doc) == []


@pytest.mark.regression
@pytest.mark.parametrize("with_render", [False, True])
def test_a_hand_written_entry_with_its_doi_in_a_formatting_template_stays_unstructured(
    tmp_path: Path, with_render: bool
) -> None:
    """As in a ref: the entry has text of its own, and its DOI is labelled text, not a field of a template."""
    text = "== S ==\n* Smith, J. (2001). ''Own work''. Journal 5. {{small|doi:10.1000/own123}}\n"
    small = transclusion(1, "small", {"1": "doi:10.1000/own123"}, "<small>doi:10.1000/own123</small>")
    doc = run(tmp_path, text, bibliography("Smith " + small) if with_render else None)
    assert kinds(doc) == ["unstructured_text"]
    assert unresolved(doc) == []


@pytest.mark.negative
def test_an_entry_whose_only_text_is_a_template_field_stays_unresolved(tmp_path: Path) -> None:
    """Control: own text on the line does not make a field of an unlisted template the entry's own identifier."""
    doc = run(tmp_path, f"== S ==\n* Barthold. {EI2}\n", None)
    assert kinds(doc) == []
    [issue] = unresolved(doc)
    assert issue["detail"].startswith("bibliography entry: identifiers only in templates with no usable render: EI2")


# RV2-4: a definition whose templates have no output of their own is decided by its rendered note ------------------


def _reflist(n: int, target: str, refs_wt: str) -> str:
    dm = json.dumps(
        {"parts": [{"template": {"target": {"wt": target}, "params": {"refs": {"wt": refs_wt}}, "i": 0}}]},
        ensure_ascii=False,
    ).replace("'", "&#39;")
    return f'<span class="mw-empty-elt" about="#mwt{n}" typeof="mw:Transclusion" data-mw=\'{dm}\'></span>'


def list_defined(body_wt: str, note_html: str, reflist: str = "Reflist") -> tuple[str, str]:
    """A ref defined in a reference-list template's ``refs=``: Parsoid renders its templates inside that
    transclusion, so none of them has output of its own (structure of the retained ``en-2695828-a1``)."""
    ref = f"<ref name=a>{body_wt}</ref>"
    text = f"Text.<ref name=a/>\n\n== R ==\n{{{{{reflist}|refs=\n{ref}\n}}}}\n"
    body = (
        f"<p>Text.{ref_sup(1, 'cite_note-a-1', 'cite_ref-a_1-0', name='a')}</p>"
        + _reflist(127, reflist, f"\n{ref}\n")
        + references([note_li("cite_note-a-1", ["cite_ref-a_1-0"], note_html)])
    )
    return text, body


ISBN_HTML = 'ISBN <a href="./Special:BookSources/0-12-345678-9">0-12-345678-9</a>'


@pytest.mark.regression
@pytest.mark.parametrize(
    ("wiki", "body_wt", "note_html", "reflist"),
    [
        ("en", "Smith, J. (2001). ''A Book''. Press. {{ISBN|0-12-345678-9}}", f"Smith. A Book. {ISBN_HTML}", "Reflist"),
        ("ar", "سميث، ج. (2001). ''كتاب''. دار. {{ردمك|0-12-345678-9}}", f"سميث. كتاب. {ISBN_HTML}", "مراجع"),
    ],
)
def test_a_list_defined_plain_citation_beside_a_helper_template_stays_unstructured(
    tmp_path: Path, wiki: str, body_wt: str, note_html: str, reflist: str
) -> None:
    text, body = list_defined(body_wt, note_html, reflist)
    doc = run(tmp_path, text, body, wiki)
    assert kinds(doc) == ["unstructured_text"]
    assert unresolved(doc) == []


@pytest.mark.regression
def test_a_refn_plain_citation_beside_a_helper_template_stays_unstructured(tmp_path: Path) -> None:
    arg = "Smith, J. (2001). ''A Book''. Press. {{ISBN|0-12-345678-9}}"
    part = {"target": {"wt": "refn"}, "params": {"1": {"wt": arg}}, "i": 0}
    dm = json.dumps({"parts": [{"template": part}]}).replace("'", "&#39;")
    body = (
        f'<p>Text.<sup about="#mwt3" typeof="mw:Transclusion mw:Extension/ref" class="mw-ref reference" '
        f'id="cite_ref-1" data-mw=\'{dm}\'><a href="./SYNTHETIC#cite_note-1"><span class="mw-reflink-text">[1]'
        "</span></a></sup></p>" + references([note_li("cite_note-1", ["cite_ref-1"], f"Smith. A Book. {ISBN_HTML}")])
    )
    doc = run(tmp_path, f"Text.{{{{refn|{arg}}}}}\n", body)
    assert kinds(doc) == ["unstructured_text"]
    assert unresolved(doc) == []


@pytest.mark.negative
@pytest.mark.parametrize(
    ("body_wt", "note_html", "expected_kinds", "reason"),
    [
        (
            "{{harvnb|Smith|2001}}, who disagrees.",
            '<a href="./SYNTHETIC#CITEREFSmith2001">Smith 2001</a>, who disagrees.',
            [],
            "plain text beside a short-citation link",
        ),
        ("{{harvnb|Smith|2001|p=5}}", '<a href="./SYNTHETIC#CITEREFSmith2001">Smith 2001</a>, p. 5', [], None),
        ("{{Fishbase|Osteobrama|bhimensis}}", cs1("Froese"), ["unsupported_citation_template"], None),
        (
            "Smith {{harvnb|Smith|2001}} {{ISBN|0-12-345678-9}}",
            f'Smith <a href="./SYNTHETIC#CITEREFSmith2001">S</a> {ISBN_HTML}',
            [],
            "plain text beside templates with no output of their own in the render, or conflicting outputs: "
            "Harvnb, ISBN",
        ),
    ],
)
def test_the_rendered_note_decides_only_what_it_can_attribute(
    tmp_path: Path, body_wt: str, note_html: str, expected_kinds: list[str], reason: str | None
) -> None:
    """A short link or a citation in the note is attributed to the definition's one template without output of its
    own; with two such templates and a link, nothing is attributed."""
    text, body = list_defined(body_wt, note_html)
    doc = run(tmp_path, text, body)
    assert kinds(doc) == expected_kinds
    got = [i["detail"] for i in unresolved(doc)]
    assert got == ([] if reason is None else [f"definition 1: {reason}"])


# RV2-5 / RV2-8: templates that cannot make citation markup --------------------------------------------------------


LANG = transclusion(9, "lang", {"1": "la", "2": "Osteobrama"}, '<i lang="la">Osteobrama</i>')


@pytest.mark.regression
@pytest.mark.parametrize(
    ("nested", "prose_src", "prose_html"),
    [
        ("Foo {{!}} Bar", "", ""),
        ("{{lang|la|Osteobrama}}", "The {{lang|la|Osteobrama}} genus.", f"The {LANG} genus."),
    ],
)
def test_a_g_template_holding_a_template_that_cannot_make_citation_markup_stays_g(
    tmp_path: Path, nested: str, prose_src: str, prose_html: str
) -> None:
    """``{{!}}`` is MediaWiki syntax for a pipe; a template whose every own transclusion in the same render shows no
    citation markup did not make the citation markup of the template that holds it."""
    params = {"1": "Osteobrama", "2": "bhimensis", "title": nested}
    text = f"{prose_src}A<ref>{{{{Fishbase|Osteobrama|bhimensis|title={nested}}}}}</ref>"
    body = f"<p>{prose_html}</p>" + one_note("A", transclusion(5, "Fishbase", params, cs1("Osteobrama")))
    doc = run(tmp_path, text, body)
    assert kinds(doc) == ["unsupported_citation_template"]
    assert unresolved(doc) == []


@pytest.mark.negative
def test_a_g_template_holding_a_template_never_rendered_alone_stays_unresolved(tmp_path: Path) -> None:
    """Without a transclusion of its own anywhere in the render, the nested template could have made the markup."""
    params = {"1": "Osteobrama", "2": "bhimensis", "title": "{{lang|la|Osteobrama}}"}
    text = "A<ref>{{Fishbase|Osteobrama|bhimensis|title={{lang|la|Osteobrama}}}}</ref>"
    doc = run(tmp_path, text, one_note("A", transclusion(5, "Fishbase", params, cs1("Osteobrama"))))
    assert kinds(doc) == []
    [issue] = unresolved(doc)
    assert "citation markup holds nested templates: Fishbase" in issue["detail"]


@pytest.mark.regression
@pytest.mark.parametrize("with_render", [False, True])
def test_a_pipe_magic_word_in_a_plain_citation_is_not_an_unknown_template(tmp_path: Path, with_render: bool) -> None:
    text = "A<ref>Smith, J. (2001). ''History of {{!}} Foo''. Oxford: Clarendon Press.</ref>"
    body = one_note("A", "Smith, J. (2001). <i>History of | Foo</i>. Oxford: Clarendon Press.")
    doc = run(tmp_path, text, body if with_render else None)
    assert kinds(doc) == ["unstructured_text"]
    assert unresolved(doc) == []


@pytest.mark.regression
def test_a_magic_word_without_output_of_its_own_is_decided_by_the_note(tmp_path: Path) -> None:
    text = "A<ref>Smith, J. (2001). ''History of {{PAGENAME}}''. Oxford: Clarendon Press.</ref>"
    body = one_note("A", "Smith, J. (2001). <i>History of SYNTHETIC</i>. Oxford: Clarendon Press.")
    doc = run(tmp_path, text, body)
    assert kinds(doc) == ["unstructured_text"]


# RV2-7: an unlisted template over several lines starting on a list line ------------------------------------------


@pytest.mark.regression
def test_a_multi_line_template_on_a_list_line_makes_an_entry(tmp_path: Path) -> None:
    text = "== S ==\n* {{EI2|last=Barthold|title=al-Barāmika\n|doi=10.1163/1573-3912_islam_COM_0099}}\n"
    doc = run(tmp_path, text, bibliography(transclusion(1, "EI2", EI2_PARAMS, cs1("Barthold"))))
    [entry] = [c for c in doc["containers"] if c["kind"] == "bibliography_entry"]
    [unit] = doc["units"]
    assert (unit["kind"], unit["container_id"]) == ("unsupported_citation_template", entry["id"])
    [ident] = doc["identifiers"]
    assert (ident["container_id"], ident["unit_id"]) == (entry["id"], unit["id"])


@pytest.mark.negative
def test_a_multi_line_template_off_a_list_line_makes_no_entry(tmp_path: Path) -> None:
    text = "== S ==\nSee {{EI2|last=Barthold|title=al-Barāmika\n|doi=10.1163/1573-3912_islam_COM_0099}}\n"
    doc = run(tmp_path, text, None)
    assert [c for c in doc["containers"] if c["kind"] == "bibliography_entry"] == []
