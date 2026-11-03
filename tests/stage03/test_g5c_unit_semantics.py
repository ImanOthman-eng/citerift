"""D-035: what a citation unit is (classes A-H), fail-first.

The confirmation campaign of 2026-11 found that the engine called every definition without a recognized citation
template ``unstructured_text`` (English G5c 0.869). The required invariant: the absence of a recognized citation
template is not sufficient evidence that an unstructured bibliographic citation exists.

Classes (``docs/verification/stage-03/design/unit-semantics/SEMANTIC_DECISION.md``):
A a reference definition; B a citation unit inside it; C a structured citation template (profile);
D a genuine unstructured citation; E a short-citation link to an entry elsewhere (Harvard family);
F an explanatory note with no citation; G a citation-like template the profile does not support;
H a definition whose citation unit cannot be established safely.

Two kinds of cases:

* SYNTHETIC cases built through the production capture code (``wiki_support``): invented pages, never evidence
  about Wikipedia;
* the 21 unstructured-unit false positives of the 2026-11 confirmation campaign (19 English, 2 Arabic), read from the
  retained bundles. That campaign's data are exposed: these are regressions only, never a new scientific pass.
"""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Any

import pytest
from wiki_support import bundle, codes, extract, note_li, ref_sup, references

from citerift.wiki.extract import ExtractConfig, extract_bundle

ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN = ROOT / "docs/verification/stage-03/evaluation/confirmation-2026-11/campaign"
UNRESOLVED = "UNIT_CLASSIFICATION_UNRESOLVED"


# Helpers -------------------------------------------------------------------------------------------------------


def transclusion(n: int, target: str, params: dict[str, str], inner: str, tag: str = "span") -> str:
    """Parsoid output of one template call: the first element carries ``mw:Transclusion`` and its ``data-mw``."""
    part = {"target": {"wt": target}, "params": {k: {"wt": v} for k, v in params.items()}, "i": 0}
    dm = json.dumps({"parts": [{"template": part}]}, ensure_ascii=False).replace("'", "&#39;")
    return f'<{tag} about="#mwt{n}" typeof="mw:Transclusion" data-mw=\'{dm}\'>{inner}</{tag}>'


def citeref(anchor: str, text: str) -> str:
    return f'<a href="./SYNTHETIC#CITEREF{anchor}">{text}</a>'


def cs1(text: str) -> str:
    return f'<cite class="citation web cs1">{text}</cite>'


def one_note(prose: str, inner: str) -> str:
    """Render of one anonymous reference: the marker in a paragraph and its note in the list."""
    return f"<p>{prose}{ref_sup(1, 'cite_note-1', 'cite_ref-1')}</p>" + references(
        [note_li("cite_note-1", ["cite_ref-1"], inner)]
    )


def run(tmp: Path, text: str, body: str | None, wiki: str = "en") -> dict[str, Any]:
    return extract(bundle(tmp, text, body, wiki=wiki))


def kinds(doc: dict[str, Any]) -> list[str]:
    return [u["kind"] for u in doc["units"]]


def unresolved(doc: dict[str, Any]) -> list[dict[str, Any]]:
    return [i for i in doc["issues"] if i["code"] == UNRESOLVED]


# E: short-citation links --------------------------------------------------------------------------------------


@pytest.mark.regression
@pytest.mark.parametrize(
    ("wiki", "call", "target", "params"),
    [
        ("en", "{{harvnb|Fox|2002|p=4}}", "harvnb", {"1": "Fox", "2": "2002", "p": "4"}),
        ("en", "{{harvp|Danilatos|1988}}", "harvp", {"1": "Danilatos", "2": "1988"}),
        ("ar", "{{استشهاد بهارفارد دون أقواس|فوكس|2002}}", "استشهاد بهارفارد دون أقواس", {"1": "فوكس", "2": "2002"}),
    ],
)
def test_short_citation_link_alone_is_not_unstructured(
    tmp_path: Path, wiki: str, call: str, target: str, params: dict[str, str]
) -> None:
    """E: a definition that is only a Harvard link cites an entry elsewhere; it has no citation unit of its own."""
    text = f"A<ref>{call}.</ref>"
    inner = transclusion(5, target, params, citeref("Fox2002", "Fox 2002")) + "."
    doc = run(tmp_path, text, one_note("A", inner), wiki)
    assert kinds(doc) == []
    assert unresolved(doc) == []


@pytest.mark.regression
def test_short_citation_link_with_comment_is_unresolved(tmp_path: Path) -> None:
    """H: a Harvard link with plain text beside it. The text may be a comment or a second citation; nothing in the
    markup says which, so no unit is claimed and the definition is reported."""
    text = "A<ref>{{harvnb|Németh|2018|p=3}}, treats these as two separate volumes.</ref>"
    inner = (
        transclusion(5, "harvnb", {"1": "Németh", "2": "2018", "p": "3"}, citeref("Németh2018", "Németh 2018"))
        + ", treats these as two separate volumes."
    )
    doc = run(tmp_path, text, one_note("A", inner))
    assert kinds(doc) == []
    [issue] = unresolved(doc)
    assert issue["entities"] == [doc["containers"][0]["id"]]


@pytest.mark.regression
@pytest.mark.parametrize(
    ("tail", "render_tail"),
    [
        (
            "; see also [http://example.org/paper Jones, Paper, 2001].",
            '; see also <a rel="mw:ExtLink" href="http://example.org/paper" class="external text">Jones, Paper,'
            " 2001</a>.",
        ),
        (
            "; Jones 2001, doi:10.1000/xyz",
            "; Jones 2001, doi:10.1000/xyz",
        ),
    ],
)
def test_short_citation_link_keeps_a_genuine_plain_citation(tmp_path: Path, tail: str, render_tail: str) -> None:
    """D retained: plain text that carries its own locator (a link or an identifier) beside a Harvard link."""
    text = f"A<ref>{{{{harvnb|Fox|2002}}}}{tail}</ref>"
    inner = transclusion(5, "harvnb", {"1": "Fox", "2": "2002"}, citeref("Fox2002", "Fox 2002")) + render_tail
    doc = run(tmp_path, text, one_note("A", inner))
    assert kinds(doc) == ["unstructured_text"]
    assert all(i["unit_id"] == doc["units"][0]["id"] for i in doc["identifiers"])


@pytest.mark.regression
def test_short_citation_link_without_render_is_unresolved(tmp_path: Path) -> None:
    """H: without the render nothing shows what the template is; the definition is not called unstructured."""
    doc = run(tmp_path, "A<ref>{{harvnb|Fox|2002|p=4}}</ref>", None)
    assert kinds(doc) == []
    assert len(unresolved(doc)) == 1


# F: explanatory notes -----------------------------------------------------------------------------------------


@pytest.mark.regression
@pytest.mark.parametrize(
    ("wiki", "text"),
    [
        ("en", "A{{efn|An eyre was an occasional circuit court.}}\n{{notelist}}"),
        ("en", "A{{efn|[[Latin]]: ''Excerpta Constantiniana''; [[Greek language|Greek]]: ''Eklogai''.}}\n{{notelist}}"),
        ("ar", "أ{{ملا|كانت محكمة الإير محكمة متنقلة.}}\n{{ثبت الملاحظة}}"),
    ],
)
def test_explanatory_note_text_is_unresolved(tmp_path: Path, wiki: str, text: str) -> None:
    """H, not F (review RV-6): the text of an explanatory footnote (the profile's ``efn`` family) without a locator
    may explain or cite; it is not ``unstructured_text``, and the abstention is reported, not silent."""
    doc = run(tmp_path, text, None, wiki)
    assert kinds(doc) == []
    [issue] = unresolved(doc)
    assert issue["detail"] == "definition 1: explanatory-note text without a locator"


@pytest.mark.regression
def test_explanatory_note_with_nested_citation(tmp_path: Path) -> None:
    """F outside, D inside: the nested ref is a definition of its own and keeps its plain-text unit."""
    text = (
        "A{{efn|Writing in 1942, Warren argued this.<ref name=W>Warren ''Serjeants-at-Law'' p. 919.</ref>}}"
        "\n{{notelist}}\n{{reflist}}"
    )
    doc = run(tmp_path, text, None)
    nested = next(c for c in doc["containers"] if c["name"] == "W")
    note = next(c for c in doc["containers"] if c["kind"] == "generated_note")
    assert [u["kind"] for u in doc["units"] if u["container_id"] == nested["id"]] == ["unstructured_text"]
    assert [u for u in doc["units"] if u["container_id"] == note["id"]] == []


@pytest.mark.regression
def test_explanatory_note_with_a_link_is_a_citation(tmp_path: Path) -> None:
    """D: an explanatory note whose own text gives a locator cites that source."""
    doc = run(tmp_path, "A{{efn|Figures from [http://example.org/census the census].}}\n{{notelist}}", None)
    assert kinds(doc) == ["unstructured_text"]


# G: citation-like templates the profile does not support ------------------------------------------------------


@pytest.mark.regression
@pytest.mark.parametrize(
    ("wiki", "call", "target", "params"),
    [
        (
            "en",
            "{{Fishbase|Osteobrama|bhimensis|month=March|year=2024}}",
            "Fishbase",
            {"1": "Osteobrama", "2": "bhimensis", "month": "March", "year": "2024"},
        ),
        ("ar", "{{دائرة المعارف الإسلامية}}", "دائرة المعارف الإسلامية", {}),
    ],
)
def test_citation_like_template_is_kept_as_unsupported(
    tmp_path: Path, wiki: str, call: str, target: str, params: dict[str, str]
) -> None:
    """G: the render shows CS1/CS2 citation markup; the template is kept with its anchors as unsupported."""
    text = f"A<ref>{call}</ref>"
    inner = transclusion(5, target, params, cs1("Froese, R. FishBase."))
    doc = run(tmp_path, text, one_note("A", inner), wiki)
    assert kinds(doc) == ["unsupported_citation_template"]
    unit = doc["units"][0]
    assert unit["template"]["canonical"] == target[0].upper() + target[1:]
    assert unit["source"]["cp_start"] == text.index("{{")
    assert unit["source"]["cp_end"] == text.index("</ref>")
    assert unit["render"]["state"] == "matched"
    assert "CITATION_TEMPLATE_UNSUPPORTED" in codes(doc)


@pytest.mark.regression
def test_citation_like_template_with_text_has_one_unit(tmp_path: Path) -> None:
    """G with text beside it: like a supported template, the text adds no unstructured unit."""
    text = "A<ref>{{Fishbase|Osteobrama|bhimensis}} Accessed 2024.</ref>"
    inner = transclusion(5, "Fishbase", {"1": "Osteobrama", "2": "bhimensis"}, cs1("FishBase")) + " Accessed 2024."
    doc = run(tmp_path, text, one_note("A", inner))
    assert kinds(doc) == ["unsupported_citation_template"]


@pytest.mark.regression
def test_unsupported_template_identifier_stays_unresolved_in_its_unit(tmp_path: Path) -> None:
    """G keeps the identifier of an unsupported template's field in that template's unit, role ``unresolved``."""
    text = "A<ref>{{Fish db|doi=10.1000/abc}}</ref>"
    inner = transclusion(5, "Fish db", {"doi": "10.1000/abc"}, cs1("Fish db. doi:10.1000/abc"))
    doc = run(tmp_path, text, one_note("A", inner))
    [unit] = doc["units"]
    [ident] = doc["identifiers"]
    assert unit["kind"] == "unsupported_citation_template"
    assert ident["role"] == "unresolved"
    assert ident["unit_id"] == unit["id"]


# H: classification cannot be established ----------------------------------------------------------------------


@pytest.mark.regression
def test_short_citation_link_beside_unknown_template_is_unresolved(tmp_path: Path) -> None:
    """H: a Harvard link is class E only when nothing else is in the definition; an unknown template beside it may be
    the citation."""
    text = "A<ref>{{harvnb|Fox|2002}} {{NRDB species|genus=Polemon}}</ref>"
    inner = (
        transclusion(5, "harvnb", {"1": "Fox", "2": "2002"}, citeref("Fox2002", "Fox 2002"))
        + " "
        + transclusion(6, "NRDB species", {"genus": "Polemon"}, "<i>Polemon</i>")
    )
    doc = run(tmp_path, text, one_note("A", inner))
    assert kinds(doc) == []
    assert len(unresolved(doc)) == 1


@pytest.mark.regression
@pytest.mark.parametrize(
    ("note", "expected", "reason"),
    [
        ("<cite class='citation'>Who's Who</cite>", ["unsupported_citation_template"], None),
        ("Who's Who 2023", [], "only templates; render shows no citation markup: Who's Who"),
        (None, [], "only templates, some with no usable render: Who's Who"),
    ],
)
def test_template_without_own_render_output_is_decided_by_its_note(
    tmp_path: Path, note: str | None, expected: list[str], reason: str | None
) -> None:
    """A ref inside an infobox parameter has no transclusion of its own in the render (Parsoid renders the infobox as
    one block). Its rendered note shows the whole definition, whose one template made it (review 2, RV2-4): a
    citation there is G; a note without citation markup or link is H as for a template that renders none; without a
    render it is H (at 11bb5b2 every case was H, "no output of their own in the render")."""
    text = "{{Infobox person|birth_date=1945<ref>{{Who's Who|title=Wheeler|year=2023}}</ref>}}"
    infobox = transclusion(
        1,
        "Infobox person",
        {"birth_date": "1945<ref>{{Who's Who|title=Wheeler|year=2023}}</ref>"},
        f"<table><tr><td>1945{ref_sup(1, 'cite_note-1', 'cite_ref-1')}</td></tr></table>",
        "div",
    )
    body = None if note is None else infobox + references([note_li("cite_note-1", ["cite_ref-1"], note)])
    doc = run(tmp_path, text, body)
    assert kinds(doc) == expected
    assert [i["detail"] for i in unresolved(doc)] == ([] if reason is None else [f"definition 1: {reason}"])


@pytest.mark.regression
def test_conflicting_render_evidence_is_unresolved(tmp_path: Path) -> None:
    """H: two calls with one key whose outputs disagree give no evidence (equal keys must expand equally)."""
    text = "A<ref>{{Fish db|x}}</ref> B<ref name=b>{{Fish db|x}}</ref>"
    body = (
        f"<p>A{ref_sup(1, 'cite_note-1', 'cite_ref-1')} B{ref_sup(2, 'cite_note-b-2', 'cite_ref-b-2', name='b')}</p>"
        + references(
            [
                note_li("cite_note-1", ["cite_ref-1"], transclusion(5, "Fish db", {"1": "x"}, cs1("Fish"))),
                note_li("cite_note-b-2", ["cite_ref-b-2"], transclusion(6, "Fish db", {"1": "x"}, "Fish")),
            ]
        )
    )
    doc = run(tmp_path, text, body)
    assert kinds(doc) == []
    assert len(unresolved(doc)) == 2


@pytest.mark.regression
def test_omitted_template_is_unresolved(tmp_path: Path) -> None:
    """H: the output of a template MediaWiki stopped expanding (a parser-limit warning) is not evidence, even when it
    holds citation markup; the definition is never read as plain text."""
    text = "A<ref>{{Fish db|x}}</ref>"
    inner = transclusion(
        5, "Fish db", {"1": "x"}, "<!-- WARNING: template omitted, post-expand include size too large -->" + cs1("F")
    )
    doc = run(tmp_path, text, one_note("A", inner))
    assert kinds(doc) == []
    assert len(unresolved(doc)) == 1


@pytest.mark.regression
def test_unresolved_definition_is_in_the_exception_ledger(tmp_path: Path) -> None:
    doc = run(tmp_path, "A<ref>{{NRDB species|genus=Polemon}}</ref>", None)
    [container] = doc["containers"]
    assert [e for e in doc["exceptions"] if e["code"] == UNRESOLVED] == [
        {
            "entity": container["id"],
            "entity_type": "container",
            "code": UNRESOLVED,
            "detail": "definition 1: only templates, some with no usable render: NRDB species",
        }
    ]


@pytest.mark.regression
@pytest.mark.parametrize("with_render", [True, False])
def test_unknown_template_alone_is_unresolved(tmp_path: Path, with_render: bool) -> None:
    """H: a template whose output shows no citation markup (or no render at all) is not plain text."""
    text = "A<ref>{{NRDB species|genus=Polemon|species=christyi}}</ref>"
    inner = transclusion(
        5, "NRDB species", {"genus": "Polemon", "species": "christyi"}, "<i>Polemon christyi</i> at the database"
    )
    doc = run(tmp_path, text, one_note("A", inner) if with_render else None)
    assert kinds(doc) == []
    assert len(unresolved(doc)) == 1


@pytest.mark.regression
def test_unknown_template_identifier_has_no_unit(tmp_path: Path) -> None:
    """H: an identifier field of an unknown template stays ``unresolved``; it is not given a plain-text unit."""
    text = "A<ref>{{Fish db|doi=10.1000/abc}}</ref>"
    inner = transclusion(5, "Fish db", {"doi": "10.1000/abc"}, "Fish db entry")
    doc = run(tmp_path, text, one_note("A", inner))
    [ident] = doc["identifiers"]
    assert kinds(doc) == []
    assert ident["role"] == "unresolved"
    assert ident["unit_id"] is None
    assert len(unresolved(doc)) == 1


# D: positive controls (unchanged behaviour) -------------------------------------------------------------------


@pytest.mark.regression
@pytest.mark.parametrize("with_render", [True, False])
@pytest.mark.parametrize(
    ("wiki", "text"),
    [
        ("en", "A<ref>Smith, J. A book. 2001.</ref>"),
        ("ar", "أ<ref>سميث، ج. كتاب. 2001.</ref>"),
        ("en", "A<ref>Berlak, p. 63.</ref>"),
        ("ar", "أ<ref>مركز بيو: ليبيريا</ref>"),
    ],
)
def test_plain_text_reference_stays_unstructured(tmp_path: Path, with_render: bool, wiki: str, text: str) -> None:
    """D: a ``<ref>`` whose own text is a hand-written citation."""
    doc = run(tmp_path, text, one_note("A", "x") if with_render else None, wiki)
    assert kinds(doc) == ["unstructured_text"]
    assert unresolved(doc) == []


HELPERS = [
    (
        "en",
        "A<ref>Beolens, B. (2011). ''The Eponym Dictionary''. {{ISBN|978-1-907807-44-2}}.</ref>",
        "ISBN",
        {"1": "978-1-907807-44-2"},
        '<a href="./Special:BookSources/9781907807442">ISBN 978-1-907807-44-2</a>',
    ),
    (
        "en",
        "A<ref>Danilatos, G.D. {{US patent|4785182}} filed 1987.</ref>",
        "US patent",
        {"1": "4785182"},
        '<a rel="mw:ExtLink" href="https://patents.google.com/patent/US4785182" class="external text">US patent'
        " 4,785,182</a>",
    ),
    (
        "ar",
        "أ<ref>القاموس الطبي {{Webarchive|url=http://example.org/a|date=2020}}</ref>",
        "Webarchive",
        {"url": "http://example.org/a", "date": "2020"},
        '<a rel="mw:ExtLink" href="http://example.org/a" class="external text">مؤرشف</a>',
    ),
]


@pytest.mark.regression
@pytest.mark.parametrize(("wiki", "text", "target", "params", "output"), HELPERS)
def test_plain_text_beside_a_helper_template_stays_unstructured(
    tmp_path: Path, wiki: str, text: str, target: str, params: dict[str, str], output: str
) -> None:
    """D: a hand-written citation with a helper template beside it whose own render shows no citation markup and no
    short-citation link."""
    doc = run(tmp_path, text, one_note("A", "x " + transclusion(5, target, params, output)), wiki)
    assert kinds(doc) == ["unstructured_text"]
    assert unresolved(doc) == []


@pytest.mark.regression
@pytest.mark.parametrize(("wiki", "text", "target", "params", "output"), HELPERS)
def test_plain_text_beside_a_template_the_render_cannot_show_is_unresolved(
    tmp_path: Path, wiki: str, text: str, target: str, params: dict[str, str], output: str
) -> None:
    """H (review RV-4): without evidence of what the template beside the text is, it could be a short-citation link
    and the text a comment, so no unit is claimed. Without a render there is none; with a render where the template
    has no transclusion of its own, its note shows a short-citation link (review 2, RV2-4: a note that shows neither
    a link nor citation markup is evidence, ``test_g5c_review2.py``)."""
    del target, params, output
    link = one_note("A", 'x <a href="./SYNTHETIC#CITEREFSmith2001">Smith 2001</a>')
    for n, (body, reason) in enumerate(((None, "templates with no usable render"), (link, "a short-citation link"))):
        doc = extract(bundle(tmp_path, text, body, wiki=wiki, name=f"b{n}"))
        assert kinds(doc) == []
        [issue] = unresolved(doc)
        assert issue["detail"].startswith(f"definition 1: plain text beside {reason}")


@pytest.mark.regression
@pytest.mark.parametrize(
    "text",
    [
        "A<ref>{{doi|10.1000/abc}}</ref>",
        "A<ref>http://example.org/paper.pdf</ref>",
        "A<ref>[https://doi.org/10.1000/abc]</ref>",
    ],
)
def test_locator_only_reference_stays_unstructured(tmp_path: Path, text: str) -> None:
    """D: a reference that is only an identifier wrapper or a link still cites that work; identifiers keep it."""
    doc = run(tmp_path, text, None)
    assert kinds(doc) == ["unstructured_text"]
    assert all(i["unit_id"] == doc["units"][0]["id"] for i in doc["identifiers"])


@pytest.mark.regression
def test_list_defined_plain_reference_stays_unstructured(tmp_path: Path) -> None:
    text = 'A<ref name=a/>\n{{reflist|refs=<ref name=a>Danilatos, G.D. "Method", filed 1987.</ref>}}'
    doc = run(tmp_path, text, None)
    assert kinds(doc) == ["unstructured_text"]


@pytest.mark.regression
def test_citation_template_with_text_is_unchanged(tmp_path: Path) -> None:
    """C: a profile citation template with text beside it is one template unit (behaviour before D-035)."""
    doc = run(tmp_path, "A<ref>{{cite book |last=Smith |title=T |year=2001}} p. 5.</ref>", None)
    assert kinds(doc) == ["citation_template"]


@pytest.mark.regression
def test_bibliography_entry_is_unchanged(tmp_path: Path) -> None:
    doc = run(tmp_path, "Text.\n==Sources==\n* Jones, 1999. PMID 12345.\n", None)
    assert kinds(doc) == ["unstructured_text"]


@pytest.mark.regression
def test_mixed_reference_bilingual(tmp_path: Path) -> None:
    """Arabic text with an English Harvard call and an Arabic plain reference in one article."""
    text = "أ<ref>{{harvnb|Fox|2002}}</ref> ب<ref>فوكس، تاريخ العالم، 2002.</ref>"
    body = f"<p>أ{ref_sup(1, 'cite_note-1', 'cite_ref-1')} ب{ref_sup(2, 'cite_note-2', 'cite_ref-2')}</p>" + references(
        [
            note_li(
                "cite_note-1",
                ["cite_ref-1"],
                transclusion(5, "harvnb", {"1": "Fox", "2": "2002"}, citeref("Fox2002", "Fox 2002")),
            ),
            note_li("cite_note-2", ["cite_ref-2"], "فوكس، تاريخ العالم، 2002."),
        ]
    )
    doc = run(tmp_path, text, body, "ar")
    assert kinds(doc) == ["unstructured_text"]
    assert doc["units"][0]["source"]["cp_start"] == text.index("فوكس")


@pytest.mark.contracts
def test_document_with_new_kind_validates(tmp_path: Path) -> None:
    """The additive unit kind is in the extraction schema; the document validates and verifies offline."""
    from citerift.wiki.verify import verify_bundle

    text = "A<ref>{{Fishbase|Osteobrama|bhimensis}}</ref>"
    inner = transclusion(5, "Fishbase", {"1": "Osteobrama", "2": "bhimensis"}, cs1("FishBase"))
    path = bundle(tmp_path, text, one_note("A", inner))
    doc = extract(path)
    assert kinds(doc) == ["unsupported_citation_template"]
    report = verify_bundle(path, doc)
    assert report["verified"] is True, report


# The 21 false positives of the 2026-11 confirmation campaign (exposed data, regression only) --------------------

# (bundle directory under capture/bundles, body start code point of the definition, expected class)
CAMPAIGN_CASES: list[tuple[str, int, str]] = [
    *[
        ("reserve1/en-186224-a1", cp, "E")
        for cp in (92703, 93105, 94127, 94344, 94508, 95017, 96979, 97606, 98149, 98486, 99189)
    ],
    ("reserve1/en-9778156-a1", 4252, "E"),
    ("holdout/en-67651016-a1", 3402, "H"),
    ("holdout/en-67651016-a1", 208, "H"),
    ("holdout/en-38148109-a1", 6358, "H"),
    ("holdout/en-38148109-a1", 6857, "H"),
    ("holdout/en-38148109-a1", 10376, "H"),
    ("holdout/en-25916990-a1", 729, "G"),
    ("holdout/en-28279091-a1", 1399, "H"),
    ("holdout/ar-1325389-a1", 154, "H"),
    ("holdout/ar-8446039-a1", 2278, "G"),
]


def _in_repo(recorded: str) -> Path:
    """A path recorded in a score specification (absolute, under the original checkout) inside this checkout."""
    return ROOT / ("docs/verification/" + recorded.split("docs/verification/", 1)[1])


@cache
def campaign_doc(name: str) -> dict[str, Any]:
    return extract_bundle(CAMPAIGN / "capture/bundles" / name, ExtractConfig(), isolated=False)


@pytest.mark.regression
@pytest.mark.parametrize(("name", "body_cp", "expected"), CAMPAIGN_CASES)
def test_campaign_false_positive(name: str, body_cp: int, expected: str) -> None:
    doc = campaign_doc(name)
    [(container, definition)] = [
        (c, d) for c in doc["containers"] for d in c["definitions"] if d["body"]["cp_start"] == body_cp
    ]
    units = [u for u in doc["units"] if u["definition_id"] == definition["id"]]
    flagged = [i for i in unresolved(doc) if i["entities"] == [container["id"]]]
    assert [u["kind"] for u in units if u["kind"] == "unstructured_text"] == []
    if expected == "G":
        assert [u["kind"] for u in units] == ["unsupported_citation_template"]
    else:
        assert units == []
    assert bool(flagged) == (expected == "H")


def _labelled_unstructured() -> list[tuple[str, str, int]]:
    """Every definition the scored labels of the 44 gate articles call unstructured (adjudicated where an article
    was adjudicated, locked otherwise; exposed data)."""
    spec = json.loads((CAMPAIGN / "prediction/score_spec.json").read_text(encoding="utf-8"))
    out = []
    for entry in spec["splits"]["gate"]:
        name = "/".join(Path(entry["bundle"]).parts[-2:])
        labels = json.loads(_in_repo(entry.get("adjudicated") or entry["locked"]).read_text(encoding="utf-8"))
        for d in labels["definitions"]:
            if d.get("unstructured"):
                out.append((name, entry["extraction"].rsplit("/", 1)[1], d["at"]["cp"]))
    return out


@pytest.mark.regression
def test_campaign_labelled_unstructured_definitions_keep_their_unit() -> None:
    """No valid unit disappears: every adjudicated unstructured definition of the 44 gate articles that the frozen
    candidate's prediction covered with an unstructured unit still has one."""
    lost = []
    for name, extraction, cp in _labelled_unstructured():
        before = json.loads((CAMPAIGN / "prediction/extractions" / extraction).read_text(encoding="utf-8"))

        def covered(doc: dict[str, Any], cp: int = cp) -> bool:
            defs = [d for c in doc["containers"] for d in c["definitions"] if d["source"]["cp_start"] == cp]
            return any(
                u["kind"] == "unstructured_text" and u["definition_id"] == d["id"] for d in defs for u in doc["units"]
            )

        if covered(before) and not covered(campaign_doc(name)):
            lost.append((name, cp))
    assert lost == []


# Independent adversarial review of D-035 (design/unit-semantics/review/REVIEW.md) --------------------------------


@pytest.mark.regression
@pytest.mark.parametrize(
    ("wiki", "text", "wrapper", "params", "inner_name"),
    [
        (
            "en",
            "A<ref>{{small|{{cite web |url=http://example.org/a |title=T |doi=10.1000/abc}}}}</ref>",
            "small",
            {"1": "{{cite web |url=http://example.org/a |title=T |doi=10.1000/abc}}"},
            "Cite web",
        ),
        (
            "ar",
            "أ<ref>{{نص صغير|{{استشهاد بكتاب|عنوان=ك}}}}</ref>",
            "نص صغير",
            {"1": "{{استشهاد بكتاب|عنوان=ك}}"},
            "استشهاد بكتاب",
        ),
    ],
)
def test_a_wrapper_around_a_citation_template_is_not_a_second_unit(
    tmp_path: Path, wiki: str, text: str, wrapper: str, params: dict[str, str], inner_name: str
) -> None:
    """RV-1: Parsoid renders a nested template as part of the outer one, so the outer template's output holds the
    nested citation's markup. The wrapper is not a G unit; the one unit is the citation, with no parent."""
    doc = run(tmp_path, text, one_note("A", transclusion(5, wrapper, params, cs1("T"))), wiki)
    assert [(u["kind"], u["parent_unit"]) for u in doc["units"]] == [("citation_template", None)]
    assert "CITATION_TEMPLATE_UNSUPPORTED" not in codes(doc)
    assert unresolved(doc) == []
    del inner_name


@pytest.mark.regression
def test_a_wrapper_around_an_unclassified_template_with_citation_markup_is_unresolved(tmp_path: Path) -> None:
    """RV-1: the markup cannot be attributed to the wrapper or to the template inside it, so neither is a unit."""
    text = "A<ref>{{small|{{Fishbase|Osteobrama|bhimensis}}}}</ref>"
    body = one_note("A", transclusion(5, "small", {"1": "{{Fishbase|Osteobrama|bhimensis}}"}, cs1("Froese")))
    doc = run(tmp_path, text, body)
    assert kinds(doc) == []
    [issue] = unresolved(doc)
    assert "citation markup holds nested templates: Small" in issue["detail"]


@pytest.mark.regression
def test_issues_name_the_renumbered_unit(tmp_path: Path) -> None:
    """RV-2: units are renumbered by position after template units are made; the issues follow the renumbering."""
    text = (
        "A<ref>Smith, J. A book. 2001.</ref> B<ref>{{Fishbase|Osteobrama|bhimensis}}</ref>"
        " C<ref>{{cite web |title=T |title=U}}</ref>"
    )
    body = (
        f"<p>A{ref_sup(1, 'cite_note-1', 'cite_ref-1')} B{ref_sup(2, 'cite_note-2', 'cite_ref-2')}"
        f" C{ref_sup(3, 'cite_note-3', 'cite_ref-3')}</p>"
        + references(
            [
                note_li("cite_note-1", ["cite_ref-1"], "Smith, J. A book. 2001."),
                note_li(
                    "cite_note-2",
                    ["cite_ref-2"],
                    transclusion(5, "Fishbase", {"1": "Osteobrama", "2": "bhimensis"}, cs1("Froese")),
                ),
                note_li("cite_note-3", ["cite_ref-3"], cs1("U")),
            ]
        )
    )
    doc = run(tmp_path, text, body)
    by_kind = {u["kind"]: u["id"] for u in doc["units"]}
    assert set(by_kind) == {"unstructured_text", "unsupported_citation_template", "citation_template"}
    [unsupported] = [i for i in doc["issues"] if i["code"] == "CITATION_TEMPLATE_UNSUPPORTED"]
    [duplicate] = [i for i in doc["issues"] if i["code"] == "DUPLICATE_TEMPLATE_PARAMETER"]
    assert unsupported["entities"] == [by_kind["unsupported_citation_template"]]
    assert duplicate["entities"] == [by_kind["citation_template"]]


@pytest.mark.regression
def test_container_issues_name_the_renumbered_container(tmp_path: Path) -> None:
    """RV-2 (same cause, found while fixing it): containers are renumbered by position; a conflict issue made
    before that names the conflicting container, not the one that took its former id."""
    doc = run(tmp_path, "A<ref name=x>Smith 2001</ref> B<ref name=x>Jones 2002</ref> C<ref>Anon 2003</ref>", None)
    [conflict] = [i for i in doc["issues"] if i["code"] == "REF_DEFINITIONS_CONFLICT"]
    [named] = [c for c in doc["containers"] if c["name"] == "x"]
    assert conflict["entities"] == [named["id"]]


ARABIC_HARVARD = "استشهاد بهارفارد دون أقواس"


@pytest.mark.regression
@pytest.mark.parametrize(
    "text",
    ["A<ref>{{harvnb|Fox|2002}}</ref>", "{{Infobox person|birth_date=1945<ref>{{harvnb|Fox|2002}}</ref>}}"],
)
def test_an_unclassified_template_without_evidence_is_not_a_citation_unit(tmp_path: Path, text: str) -> None:
    """RV-3 (English side): without render evidence an unclassified template is not established as a citation."""
    doc = run(tmp_path, text, None)
    assert kinds(doc) == []
    assert len(unresolved(doc)) == 1


@pytest.mark.regression
@pytest.mark.parametrize(
    "text",
    [
        f"أ<ref>{{{{{ARABIC_HARVARD}|فوكس|2002}}}}</ref>",
        f"{{{{صندوق معلومات شخص|ولادة=1945<ref>{{{{{ARABIC_HARVARD}|فوكس|2002}}}}</ref>}}}}",
    ],
)
def test_a_name_rule_template_without_evidence_keeps_the_guide_name_rule(tmp_path: Path, text: str) -> None:
    """RV-3, decided and measured (DISPOSITIONS.md): a template named like a citation template ("استشهاد …", RF-37,
    the annotation guide's own examples) stays a citation unit unless its own render shows a short-citation link.
    Requiring render evidence instead removed 21 genuine CS1 wrappers from the retained bundles. The Arabic Harvard
    template without evidence is therefore a residual risk (RISKS.md R-037), pinned here so that it is visible."""
    doc = run(tmp_path, text, None, "ar")
    assert kinds(doc) == ["citation_template"]


@pytest.mark.regression
@pytest.mark.parametrize(
    ("wiki", "text"),
    [
        ("en", "A<ref>{{harvnb|Németh|2018|p=3}}, treats these as two separate volumes.</ref>"),
        ("en", "{{Infobox person|birth_date=1945<ref>{{harvnb|Németh|2018}}, treats these as two.</ref>}}"),
        ("ar", "أ<ref>{{قالب مجهول|فوكس|2002}}، ويقول إن المحكمة متنقلة.</ref>"),
    ],
)
def test_short_link_and_comment_without_evidence_is_unresolved(tmp_path: Path, wiki: str, text: str) -> None:
    """RV-4: plain text beside a template the render cannot show is not called unstructured; it is reported."""
    doc = run(tmp_path, text, None, wiki)
    assert kinds(doc) == []
    [issue] = unresolved(doc)
    assert "plain text beside templates with no usable render" in issue["detail"]


@pytest.mark.regression
def test_the_same_revision_is_unresolved_with_or_without_its_render() -> None:
    """RV-4 on retained data (exposed, regression only): two captures of one revision, one whose render failed."""
    for name in ("challenge/en-906156-a1", "challenge/en-906156-a2"):
        doc = campaign_doc(name)
        for cp in (49257, 49521):
            [(container, definition)] = [
                (c, d) for c in doc["containers"] for d in c["definitions"] if d["body"]["cp_start"] == cp
            ]
            assert [u for u in doc["units"] if u["definition_id"] == definition["id"]] == [], name
            assert [i for i in unresolved(doc) if i["entities"] == [container["id"]]], name


@pytest.mark.regression
@pytest.mark.parametrize(
    ("wiki", "text"),
    [
        ("en", "A{{efn|Smith, J. (2001). ''A Book''. Publisher. p. 5.}}\n{{notelist}}"),
        ("ar", "أ{{ملا|سميث، ج. (2001). كتاب. الناشر. ص 5.}}\n{{ثبت الملاحظة}}"),
    ],
)
def test_a_citation_written_in_an_explanatory_note_is_reported(tmp_path: Path, wiki: str, text: str) -> None:
    """RV-6: an efn whose text may be a citation is not dropped silently."""
    doc = run(tmp_path, text, None, wiki)
    assert kinds(doc) == []
    assert len(unresolved(doc)) == 1


@pytest.mark.regression
def test_a_ref_whose_text_is_only_in_nowiki_is_reported(tmp_path: Path) -> None:
    """RV-8: text in a tag the engine does not read is not an empty definition."""
    doc = run(tmp_path, "A<ref><nowiki>Smith, J. Book. 2001.</nowiki></ref>", None)
    assert kinds(doc) == []
    [issue] = unresolved(doc)
    assert issue["detail"] == "definition 1: text only inside <nowiki>, which is not read"


@pytest.mark.regression
def test_a_ref_with_only_a_comment_or_punctuation_is_empty(tmp_path: Path) -> None:
    """Controls for RV-8: a comment is not text of the definition, and punctuation is not a citation."""
    doc = run(tmp_path, "A<ref><!-- Originally: x --></ref> B<ref>.&nbsp;</ref>", None)
    assert kinds(doc) == []
    assert unresolved(doc) == []


@pytest.mark.regression
def test_the_reason_does_not_claim_render_evidence_that_was_not_read(tmp_path: Path) -> None:
    """RV-10: templates of profile kinds other than citation templates are named as such, not as renders."""
    doc = run(tmp_path, "A<ref>{{Retracted|doi=10.1000/x}}</ref>", one_note("A", "x"))
    [issue] = unresolved(doc)
    assert issue["detail"] == "definition 1: only templates; not citation templates in the profile: Retracted"


# Bibliography entries (found in the exposed regression of the final English holdout, after the review) -------


EI2 = "{{EI2|last=Barthold|title=al-Barāmika|doi=10.1163/1573-3912_islam_COM_0099}}"
EI2_PARAMS = {"last": "Barthold", "title": "al-Barāmika", "doi": "10.1163/1573-3912_islam_COM_0099"}


def bibliography(inner: str) -> str:
    return f"<h2>Sources</h2><ul><li>{inner}</li></ul>"


@pytest.mark.regression
def test_an_unlisted_template_with_citation_markup_in_a_bibliography_entry_is_g(tmp_path: Path) -> None:
    """G outside refs: the entry was made from the DOI field of a template the profile does not list. Its own render
    is a CS1 citation, so the entry's unit is that template, not ``unstructured_text``."""
    doc = run(tmp_path, f"== Sources ==\n* {EI2}\n", bibliography(transclusion(1, "EI2", EI2_PARAMS, cs1("Barthold"))))
    [unit] = doc["units"]
    assert unit["kind"] == "unsupported_citation_template"
    [entry] = [c for c in doc["containers"] if c["kind"] == "bibliography_entry"]
    assert unit["container_id"] == entry["id"]
    [ident] = doc["identifiers"]
    assert ident["unit_id"] == unit["id"] and ident["role"] == "unresolved"


@pytest.mark.regression
@pytest.mark.parametrize(
    ("body", "reason"),
    [
        (None, "identifiers only in templates with no usable render: EI2"),
        (
            bibliography(transclusion(1, "EI2", EI2_PARAMS, "Barthold, al-Barāmika")),
            "identifiers only in templates that are not citation templates: EI2",
        ),
        (bibliography("Barthold"), "identifiers only in templates with no output of their own"),
    ],
)
def test_a_bibliography_entry_made_only_from_a_template_field_is_unresolved(
    tmp_path: Path, body: str | None, reason: str
) -> None:
    """H outside refs: an identifier that is a field of an unlisted template is not evidence of a hand-written
    entry, and without citation markup of its own the template is not established as a citation."""
    doc = run(tmp_path, f"== Sources ==\n* {EI2}\n", body)
    assert kinds(doc) == []
    [issue] = unresolved(doc)
    assert issue["detail"].startswith(f"bibliography entry: {reason}")


@pytest.mark.regression
@pytest.mark.parametrize(
    "line",
    [
        "* Barthold, W. ''al-Barāmika''. doi:10.1163/1573-3912_islam_COM_0099",
        "* Barthold, W. ''al-Barāmika''. {{doi|10.1163/1573-3912_islam_COM_0099}}",
        "* Barthold, W. ''al-Barāmika''. https://doi.org/10.1163/1573-3912_islam_COM_0099",
    ],
)
def test_a_hand_written_bibliography_entry_stays_unstructured(tmp_path: Path, line: str) -> None:
    """D outside refs (control): the identifier is the entry's own text, a profile wrapper or a resolver link."""
    doc = run(tmp_path, f"== Sources ==\n{line}\n", None)
    assert kinds(doc) == ["unstructured_text"]
    assert unresolved(doc) == []


@pytest.mark.regression
def test_the_final_holdout_encyclopaedia_of_islam_entries_are_g() -> None:
    """Exposed regression: the three unstructured false positives of the final English holdout were
    ``{{EI2}}``/``{{EI3}}`` bibliography entries (adjudicated: templates, not unstructured)."""
    doc = extract_bundle(
        ROOT / "docs/verification/stage-03/evaluation/final/capture/bundles/holdout/en-66266685-a1",
        ExtractConfig(),
        isolated=False,
    )
    got = {u["source"]["cp_start"]: u["kind"] for u in doc["units"] if u["source"]["cp_start"] in (2449, 3074, 3222)}
    assert got == {
        2449: "unsupported_citation_template",
        3074: "unsupported_citation_template",
        3222: "unsupported_citation_template",
    }
