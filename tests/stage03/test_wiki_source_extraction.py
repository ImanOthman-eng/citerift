"""Source-side extraction on SYNTHETIC wikitext in both languages: containers, uses, units, identifiers, anchors.

Every case is a source-only capture built through the production capture code (``wiki_support.bundle``) and
extracted in-process; the isolated worker is tested in test_wiki_isolation.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from wiki_support import bundle, by_role, codes, extract, slice_bytes

from citerift.retraction.identifiers import normalize_doi, normalize_pmid


def run(tmp_path: Path, text: str, wiki: str = "en") -> tuple[Path, dict[str, Any]]:
    path = bundle(tmp_path, text, wiki=wiki)
    return path, extract(path)


def containers(doc: dict[str, Any]) -> list[tuple[str, str | None, str, str]]:
    return [(c["kind"], c["name"], c["group"], c["binding_state"]) for c in doc["containers"]]


def uses(doc: dict[str, Any]) -> list[tuple[str, str | None, str, str]]:
    return [(u["origin"], u["name"], u["group"], u["binding"]) for u in doc["uses"]]


# --------------------------------------------------------------------------------------------- references


@pytest.mark.unit
def test_wiki_named_reuse_before_and_after_definition(tmp_path: Path) -> None:
    _, doc = run(tmp_path, 'A<ref name="x" /> B<ref name="x">{{cite journal|doi=10.1000/a}}</ref> C<ref name="x"/>')
    assert containers(doc) == [("note", "x", "", "single_definition")]
    assert [u[3] for u in uses(doc)] == ["bound", "bound", "bound"]
    cid = doc["containers"][0]["id"]
    assert all(u["container_id"] == cid for u in doc["uses"])
    assert doc["containers"][0]["use_ids"] == [u["id"] for u in doc["uses"]]


@pytest.mark.unit
def test_wiki_same_name_in_different_groups_stays_apart(tmp_path: Path) -> None:
    _, doc = run(tmp_path, 'A<ref name="x">one</ref> B<ref group="n" name="x">two</ref> C<ref group="n" name="x" />')
    assert containers(doc) == [("note", "x", "", "single_definition"), ("note", "x", "n", "single_definition")]
    first, second = (c["id"] for c in doc["containers"])
    assert [u["container_id"] for u in doc["uses"]] == [first, second, second]


@pytest.mark.negative
def test_wiki_missing_definition_is_reported_not_dropped(tmp_path: Path) -> None:
    _, doc = run(tmp_path, 'A<ref name="nowhere" /> B<ref>body</ref>')
    assert uses(doc)[0] == ("tag", "nowhere", "", "definition_missing")
    assert doc["uses"][0]["container_id"] is None
    assert "REF_DEFINITION_MISSING" in codes(doc)
    assert any(e["code"] == "REF_DEFINITION_MISSING" for e in doc["exceptions"])


@pytest.mark.negative
def test_wiki_conflicting_and_identical_definitions(tmp_path: Path) -> None:
    _, doc = run(
        tmp_path,
        'A<ref name="c">first</ref> B<ref name="c">second</ref> C<ref name="d">same</ref><ref name="d">same</ref>',
    )
    assert containers(doc) == [
        ("note", "c", "", "conflicting_definitions"),
        ("note", "d", "", "identical_definitions"),
    ]
    assert {"REF_DEFINITIONS_CONFLICT", "REF_DEFINITIONS_DUPLICATE"} <= codes(doc)
    assert [u[3] for u in uses(doc)[:2]] == ["bound_conflicting", "bound_conflicting"]
    # No body is chosen for the conflicting reference: both definitions stay.
    assert len(doc["containers"][0]["definitions"]) == 2


@pytest.mark.unit
@pytest.mark.parametrize(
    ("wiki", "text"),
    [
        ("en", 'A<ref name="L" />\n{{Reflist|refs=\n<ref name="L">{{cite book |title=B |doi=10.1000/lst}}</ref>\n}}\n'),
        (
            "ar",
            'نص<ref name="L" />\n{{مراجع|مراجع=\n<ref name="L">{{استشهاد بكتاب|عنوان=ب|دوي=10.1000/lst}}</ref>\n}}\n',
        ),
    ],
)
def test_wiki_list_defined_reference(tmp_path: Path, wiki: str, text: str) -> None:
    _, doc = run(tmp_path, text, wiki)
    assert containers(doc) == [("list_defined_note", "L", "", "single_definition")]
    assert uses(doc) == [("tag", "L", "", "bound")]
    assert by_role(doc) == {"primary_citation_field": ["10.1000/lst"]}


@pytest.mark.negative
def test_wiki_unused_list_defined_reference_is_reported(tmp_path: Path) -> None:
    _, doc = run(tmp_path, 'A\n{{Reflist|refs=\n<ref name="U">unused</ref>\n}}\n')
    assert "LIST_DEFINED_UNUSED" in codes(doc)


@pytest.mark.unit
def test_wiki_footnote_templates_and_r(tmp_path: Path) -> None:
    text = (
        "A{{efn|Note<ref>{{cite web|url=https://doi.org/10.1000/inner}}</ref>}} B{{efn|name=e2|Other}} "
        'C{{r|x|y}}<ref name="x">X</ref><ref name="y">Y</ref>'
    )
    _, doc = run(tmp_path, text)
    kinds = containers(doc)
    assert ("generated_note", None, "lower-alpha", "anonymous") in kinds
    assert ("generated_note", "e2", "lower-alpha", "single_definition") in kinds
    assert [u[:2] for u in uses(doc) if u[0] == "r"] == [("r", "x"), ("r", "y")]
    assert all(u[3] == "bound" for u in uses(doc) if u[0] == "r")
    assert by_role(doc) == {"identifier_link": ["10.1000/inner"]}


@pytest.mark.unit
def test_wiki_short_footnotes_and_bibliography(tmp_path: Path) -> None:
    text = (
        "A{{sfn|Smith|2001|p=5}} B{{sfn|Smith|2001|p=5}} C{{sfn|Jones|1999}}\n==Sources==\n"
        "* {{cite book |last=Smith |year=2001 |doi=10.1000/book}}\n* Jones, 1999. PMID 12345.\n"
    )
    _, doc = run(tmp_path, text)
    sfn = [c for c in doc["containers"] if c["layout"] == "short_footnote"]
    assert [(c["binding_state"], len(c["definitions"])) for c in sfn] == [
        ("identical_definitions", 2),
        ("single_definition", 1),
    ]
    bib = [c for c in doc["containers"] if c["kind"] == "bibliography_entry"]
    assert len(bib) == 2 and all(not c["use_ids"] for c in bib)
    roles = by_role(doc)
    assert roles["primary_citation_field"] == ["10.1000/book"]
    assert roles["labeled_reference_text"] == ["12345"]
    # The chain from a short footnote to its bibliography entry is not followed (partial support).
    assert all(not c["unit_ids"] for c in sfn)


@pytest.mark.negative
def test_wiki_unsupported_constructs_are_reported(tmp_path: Path) -> None:
    _, doc = run(tmp_path, 'A<ref details="p. 5" name="sub">sub</ref> B<gallery>File:X.jpg|cap<ref>gal</ref></gallery>')
    assert {"SUBREFERENCE_UNSUPPORTED", "REF_IN_UNSUPPORTED_CONTEXT"} <= codes(doc)
    assert len(doc["uses"]) == 2  # reported, not dropped


@pytest.mark.unit
def test_wiki_identifierless_reference_has_unstructured_unit(tmp_path: Path) -> None:
    _, doc = run(tmp_path, "A<ref>Smith, J. A book. 2001.</ref>")
    assert [u["kind"] for u in doc["units"]] == ["unstructured_text"]
    assert doc["identifiers"] == []


@pytest.mark.unit
def test_wiki_nested_and_wrapped_templates(tmp_path: Path) -> None:
    _, doc = run(tmp_path, "A<ref>{{citation|title=X {{lang|fr|Y}}|pmid=999}}</ref>")
    assert [u["template"]["canonical"] for u in doc["units"]] == ["Citation"]
    assert by_role(doc) == {"primary_citation_field": ["999"]}


# --------------------------------------------------------------------------------------------- identifiers


@pytest.mark.unit
def test_wiki_duplicate_identifier_parameter_last_value_wins(tmp_path: Path) -> None:
    """RF-01: MediaWiki uses the last value of a repeated parameter; the earlier one is not the cited DOI."""
    _, doc = run(tmp_path, "A<ref>{{cite journal |title=T |doi=10.1000/shadowed |doi=10.1000/effective}}</ref>")
    roles = {i["normalization"]["normalized"]: i["role"] for i in doc["identifiers"]}
    assert roles == {"10.1000/shadowed": "unresolved", "10.1000/effective": "primary_citation_field"}
    assert {"DUPLICATE_TEMPLATE_PARAMETER", "IDENTIFIER_PARAMETER_OVERRIDDEN"} <= codes(doc)
    assert doc["units"][0]["duplicate_params"] == ["doi"]


@pytest.mark.unit
def test_wiki_notice_title_and_marker_are_not_cited_work(tmp_path: Path) -> None:
    text = (
        "A<ref>{{cite journal |title=Retraction note to 10.1000/orig |doi=10.1000/notice}} "
        "{{Retracted|doi=10.1000/rn|pmid=555}}</ref>"
    )
    _, doc = run(tmp_path, text)
    roles = {(i["scheme"], i["normalization"]["normalized"]): i["role"] for i in doc["identifiers"]}
    assert roles == {
        ("doi", "10.1000/orig"): "textual_mention",
        ("doi", "10.1000/notice"): "primary_citation_field",
        ("doi", "10.1000/rn"): "marker_target",
        ("pmid", "555"): "marker_target",
    }


@pytest.mark.negative
def test_wiki_comment_nowiki_archive_and_ref_name_are_not_targets(tmp_path: Path) -> None:
    text = (
        "A<ref>{{cite web |url=https://web.archive.org/web/2020/https://doi.org/10.1000/arch |title=T}}</ref>"
        '<!-- doi=10.1000/comment --> <nowiki>10.1000/nowiki</nowiki><ref name="10.1000/inname">x</ref>'
    )
    _, doc = run(tmp_path, text)
    assert doc["identifiers"] == []
    assert sorted(e["reason"] for e in doc["excluded_identifiers"]) == ["comment", "tag:nowiki"]


@pytest.mark.unit
def test_wiki_links_wrappers_labels_and_pubmed_urls(tmp_path: Path) -> None:
    text = (
        "A<ref>[https://doi.org/10.1000/disp 10.1000/shown] doi:10.1000/lab. {{doi|10.1000/wrap}} {{PMID|777}} "
        "https://pubmed.ncbi.nlm.nih.gov/888/ https://www.ncbi.nlm.nih.gov/pubmed/999</ref>"
    )
    _, doc = run(tmp_path, text)
    got = [(i["scheme"], i["role"], i["normalization"]["normalized"], i["boundary"]) for i in doc["identifiers"]]
    assert got == [
        ("doi", "identifier_link", "10.1000/disp", "url"),
        ("doi", "textual_mention", "10.1000/shown", "delimited"),
        ("doi", "labeled_reference_text", "10.1000/lab.", "ambiguous_trailing_punctuation"),
        ("doi", "identifier_link", "10.1000/wrap", "field"),
        ("pmid", "identifier_link", "777", "field"),
        ("pmid", "identifier_link", "888", "url"),
        ("pmid", "identifier_link", "999", "url"),
    ]
    assert "IDENTIFIER_BOUNDARY_AMBIGUOUS" in codes(doc)


@pytest.mark.unit
def test_wiki_publisher_doi_path_with_ambiguous_trailing_segment(tmp_path: Path) -> None:
    text = "A<ref>https://onlinelibrary.wiley.com/doi/full/10.1002/abc.123 and https://pubs.acs.org/doi/10.1021/xy.5/abstract</ref>"
    _, doc = run(tmp_path, text)
    first, second = doc["identifiers"]
    assert first["normalization"]["normalized"] == "10.1002/abc.123"
    assert first["decoding"]["structural_steps"] == ["PUBLISHER_URL_DOI_PATH"]
    assert "DOI_PATH_TRAILING_SEGMENT_AMBIGUOUS" in second["decoding"]["structural_steps"]
    assert any(e["code"] == "IDENTIFIER_BOUNDARY_AMBIGUOUS" for e in doc["exceptions"])


@pytest.mark.unit
def test_wiki_percent_and_entity_decoding_once(tmp_path: Path) -> None:
    text = (
        "A<ref>https://doi.org/10.1000/a%2Fb%252F and https://doi.org/10.1000/x&amp;y "
        "{{cite journal|doi=10.1000/q&amp;r}}</ref>"
    )
    _, doc = run(tmp_path, text)
    keys = [i["normalization"]["normalized"] for i in doc["identifiers"]]
    assert keys == ["10.1000/a/b%2f", "10.1000/x&y", "10.1000/q&r"]
    assert doc["identifiers"][2]["decoding"]["input_steps"] == ["HTML_ENTITY_DECODED"]


@pytest.mark.negative
def test_wiki_arabic_digits_bidi_and_non_ascii(tmp_path: Path) -> None:
    _, doc = run(tmp_path, "نص<ref>{{استشهاد بدورية محكمة|دوي=10.1000/عربي|pmid=١٢٣}}</ref>", "ar")
    doi, pmid = doc["identifiers"]
    assert doi["normalization"]["normalized"] == "10.1000/عربي"
    assert "DOI_NON_ASCII_SUFFIX" in doi["normalization"]["issues"]
    assert pmid["normalization"]["normalized"] is None
    _, doc2 = run(tmp_path / "b", "A<ref>{{cite journal|doi=10.1000/x\u200fy}}</ref>")
    assert doc2["identifiers"][0]["normalization"]["normalized"] is None
    assert "IDENTIFIER_INVALID" in codes(doc2)


@pytest.mark.unit
def test_wiki_valid_punctuation_and_longer_prefixes(tmp_path: Path) -> None:
    text = (
        "A<ref>{{cite journal|doi=10.1002/(SICI)1097-4636(199601)30:1<1::AID-JBM1>3.0.CO;2-B}}</ref>"
        "B<ref>{{cite journal |doi=10.1000/abc}}{{cite journal |doi=10.1000/abcd}}</ref>"
    )
    _, doc = run(tmp_path, text)
    keys = [i["normalization"]["normalized"] for i in doc["identifiers"]]
    assert keys == ["10.1002/(sici)1097-4636(199601)30:1<1::aid-jbm1>3.0.co;2-b", "10.1000/abc", "10.1000/abcd"]


@pytest.mark.unit
def test_wiki_repeated_doi_keeps_every_occurrence(tmp_path: Path) -> None:
    _, doc = run(tmp_path, "C<ref>{{cite journal |doi=10.1000/same}} {{cite journal |doi=10.1000/same}}</ref>")
    assert [i["normalization"]["normalized"] for i in doc["identifiers"]] == ["10.1000/same", "10.1000/same"]
    assert len({i["source"]["byte_start"] for i in doc["identifiers"]}) == 2
    assert len(doc["units"]) == 2  # two units, never merged into one work


@pytest.mark.unit
def test_wiki_co_reported_doi_and_pmid_are_not_merged(tmp_path: Path) -> None:
    _, doc = run(tmp_path, "A<ref>{{cite journal |doi=10.1000/x |pmid=4242}}</ref>")
    assert sorted((i["scheme"], i["normalization"]["normalized"]) for i in doc["identifiers"]) == [
        ("doi", "10.1000/x"),
        ("pmid", "4242"),
    ]
    # Separate occurrences, each with its own anchor; nothing states they are the same work.
    assert all("same_work" not in i and "work_id" not in i for i in doc["identifiers"])


@pytest.mark.unit
def test_wiki_prose_mentions_are_textual(tmp_path: Path) -> None:
    _, doc = run(tmp_path, "In 2010 the paper 10.1000/prose was retracted. PMID 4242 too.\n")
    assert by_role(doc) == {"textual_mention": ["10.1000/prose", "4242"]}


@pytest.mark.unit
def test_wiki_normalization_reuses_stage02(tmp_path: Path) -> None:
    text = "A<ref>{{cite journal |doi= 10.1000/ABC |pmid=00042}} https://dx.doi.org/10.1000/Q%41</ref>"
    _, doc = run(tmp_path, text)
    for occ in doc["identifiers"]:
        fn = normalize_doi if occ["scheme"] == "doi" else normalize_pmid
        assert occ["normalization"] == fn(occ["decoding"]["normalizer_input"]).to_json()


# --------------------------------------------------------------------------------------------- anchors


@pytest.mark.unit
@pytest.mark.parametrize(
    ("wiki", "text"),
    [
        (
            "ar",
            'مُقدّمة عربيّة<ref name="أ">{{استشهاد بدورية محكمة|عنوان=عنوانٌ|دوي=10.1000/عربي}}</ref> ثم<ref name="أ" />',
        ),
        (
            "en",
            "Cafe\u0301 \u202bmixed\u202c<ref>{{cite journal|title=Ünïcode|doi=10.1000/x}}</ref> 😀<ref>https://doi.org/10.1000/y</ref>",
        ),
    ],
)
def test_wiki_exact_anchors_roundtrip_bytes(tmp_path: Path, wiki: str, text: str) -> None:
    path, doc = run(tmp_path, text, wiki)
    data = text.encode("utf-8")
    for occ in doc["identifiers"]:
        span = occ["source"]
        assert span["exact"] is True
        assert slice_bytes(path, doc, span) == occ["source"]["raw"].encode("utf-8")
        assert text[span["cp_start"] : span["cp_end"]] == occ["source"]["raw"]
        assert len(text[: span["cp_start"]].encode("utf-8")) == span["byte_start"]
    for item in doc["uses"] + doc["units"] + doc["containers"]:
        span = item["source"]
        assert data[span["byte_start"] : span["byte_end"]] == text[span["cp_start"] : span["cp_end"]].encode("utf-8")


@pytest.mark.unit
def test_wiki_repeated_fragment_gets_its_own_anchor(tmp_path: Path) -> None:
    """A global text search would anchor both to the first copy; the anchors must differ."""
    text = (
        'A<ref name="r1">{{cite journal|doi=10.1000/same}}</ref> '
        'B<ref name="r2">{{cite journal|doi=10.1000/same}}</ref>'
    )
    _, doc = run(tmp_path, text)
    starts = [i["source"]["cp_start"] for i in doc["identifiers"]]
    assert starts == [text.index("10.1000/same"), text.rindex("10.1000/same")]


@pytest.mark.unit
def test_wiki_accounting_checks_hold(tmp_path: Path) -> None:
    text = 'A<ref name="x">{{cite journal|doi=10.1000/a}}</ref><!-- 10.1000/c --> B<ref name="x"/> {{doi|10.1000/b}}'
    _, doc = run(tmp_path, text)
    assert doc["accounting"]["checks"] and all(c["ok"] for c in doc["accounting"]["checks"])
    assert doc["accounting"]["excluded_identifiers"] == {"comment": 1}
