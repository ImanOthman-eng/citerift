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
def test_explanatory_note_is_not_unstructured(tmp_path: Path, wiki: str, text: str) -> None:
    """F: an explanatory footnote (the profile's ``efn`` family) whose text carries no locator cites nothing."""
    doc = run(tmp_path, text, None, wiki)
    assert kinds(doc) == []
    assert unresolved(doc) == []


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
        ("en", "A<ref>Beolens, B. (2011). ''The Eponym Dictionary''. {{ISBN|978-1-907807-44-2}}.</ref>"),
        ("en", "A<ref>Danilatos, G.D. {{US patent|4785182}} filed 1987.</ref>"),
        ("ar", "أ<ref>القاموس الطبي {{Webarchive|url=http://example.org/a|date=2020}}</ref>"),
    ],
)
def test_plain_text_reference_stays_unstructured(tmp_path: Path, with_render: bool, wiki: str, text: str) -> None:
    """D: a ``<ref>`` whose own text is a hand-written citation, with or without helper templates beside it."""
    doc = run(tmp_path, text, one_note("A", "x") if with_render else None, wiki)
    assert kinds(doc) == ["unstructured_text"]
    assert unresolved(doc) == []


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
    assert verify_bundle(path, doc)["status"] == "verified"


# The 21 false positives of the 2026-11 confirmation campaign (exposed data, regression only) --------------------

# (bundle directory under capture/bundles, body start code point of the definition, expected class)
CAMPAIGN_CASES: list[tuple[str, int, str]] = [
    *[
        ("reserve1/en-186224-a1", cp, "E")
        for cp in (92703, 93105, 94127, 94344, 94508, 95017, 96979, 97606, 98149, 98486, 99189)
    ],
    ("reserve1/en-9778156-a1", 4252, "E"),
    ("holdout/en-67651016-a1", 3402, "H"),
    ("holdout/en-67651016-a1", 208, "F"),
    ("holdout/en-38148109-a1", 6358, "F"),
    ("holdout/en-38148109-a1", 6857, "F"),
    ("holdout/en-38148109-a1", 10376, "F"),
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
