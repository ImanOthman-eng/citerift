"""The source-side support matrix (FROZEN_PROTOCOL.md section 2) in both languages: one SYNTHETIC case per construct.

Each construct is written once in English and once in Arabic (Arabic template and parameter names from profile v1)
and must give the same structural outcome, so that a construct is never "supported" in one language only by
accident (gate 03-C). Where MediaWiki itself differs between the wikis (for example the default group of ``efn``),
the expectation names each language's value. Render-side constructs in both languages are in
test_wiki_render_ledger.py and test_wiki_observed_regression.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from wiki_support import bundle, codes, extract


def summary(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "containers": [(c["kind"], c["name"], c["group"], c["binding_state"]) for c in doc["containers"]],
        "uses": [(u["origin"], u["name"], u["group"], u["binding"]) for u in doc["uses"]],
        "units": [u["kind"] for u in doc["units"]],
        "identifiers": [(i["scheme"], i["role"], i["normalization"]["normalized"]) for i in doc["identifiers"]],
        "excluded": sorted(e["reason"] for e in doc["excluded_identifiers"]),
    }


CASES: list[tuple[str, str, str, dict[str, Any], set[str]]] = [
    # (construct, English source, Arabic source, expected summary subset, issue codes that must be present)
    (
        "anonymous_ref",
        "A<ref>{{cite journal |title=T |doi=10.1000/a}}</ref>",
        "نص<ref>{{استشهاد بدورية محكمة |عنوان=ع |دوي=10.1000/a}}</ref>",
        {
            "containers": [("note", None, "", "anonymous")],
            "uses": [("tag", None, "", "anonymous")],
            "units": ["citation_template"],
            "identifiers": [("doi", "primary_citation_field", "10.1000/a")],
        },
        set(),
    ),
    (
        "named_reuse_before_after_self_closing",
        'A<ref name="x" /> B<ref name="x">{{cite book |title=T |doi=10.1000/b}}</ref> C<ref name="x"/>',
        'أ<ref name="س" /> ب<ref name="س">{{استشهاد بكتاب |عنوان=ع |دوي=10.1000/b}}</ref> ج<ref name="س"/>',
        {"uses": [("tag", "*", "", "bound")] * 3, "identifiers": [("doi", "primary_citation_field", "10.1000/b")]},
        set(),
    ),
    (
        "same_name_different_groups",
        'A<ref name="x">one</ref> B<ref group="n" name="x">two</ref> C<ref group="n" name="x" />',
        'أ<ref name="س">واحد</ref> ب<ref group="ن" name="س">اثنان</ref> ج<ref group="ن" name="س" />',
        {"containers": [("note", "*", "", "single_definition"), ("note", "*", "*", "single_definition")]},
        set(),
    ),
    (
        "missing_definition",
        'A<ref name="nowhere" /> B<ref>body</ref>',
        'أ<ref name="لامكان" /> ب<ref>نص</ref>',
        {"uses": [("tag", "*", "", "definition_missing"), ("tag", None, "", "anonymous")]},
        {"REF_DEFINITION_MISSING"},
    ),
    (
        "conflicting_and_identical_definitions",
        'A<ref name="c">first</ref> B<ref name="c">second</ref> C<ref name="d">same</ref><ref name="d">same</ref>',
        'أ<ref name="ج">أول</ref> ب<ref name="ج">ثان</ref> ج<ref name="د">نفسه</ref><ref name="د">نفسه</ref>',
        {
            "containers": [
                ("note", "*", "", "conflicting_definitions"),
                ("note", "*", "", "identical_definitions"),
            ]
        },
        {"REF_DEFINITIONS_CONFLICT", "REF_DEFINITIONS_DUPLICATE"},
    ),
    (
        "list_defined_and_unused",
        'A<ref name="L" />\n{{Reflist|refs=\n<ref name="L">{{cite book |title=B |doi=10.1000/lst}}</ref>\n'
        '<ref name="U">unused</ref>\n}}\n',
        'نص<ref name="L" />\n{{مراجع|مراجع=\n<ref name="L">{{استشهاد بكتاب|عنوان=ب|دوي=10.1000/lst}}</ref>\n'
        '<ref name="U">غير مستعمل</ref>\n}}\n',
        {
            "containers": [
                ("list_defined_note", "L", "", "single_definition"),
                ("list_defined_note", "U", "", "single_definition"),
            ],
            "uses": [("tag", "L", "", "bound")],
            "identifiers": [("doi", "primary_citation_field", "10.1000/lst")],
        },
        {"LIST_DEFINED_UNUSED"},
    ),
    (
        "footnote_template_with_content",
        "A{{efn|A note with {{cite web |url=https://doi.org/10.1000/inner |title=T}}}}",
        "أ{{ملا|ملاحظة فيها {{استشهاد ويب |مسار=https://doi.org/10.1000/inner |عنوان=ع}}}}",
        {
            "containers": [("generated_note", None, {"en": "lower-alpha", "ar": "arabic-abajed"}, "anonymous")],
            "identifiers": [("doi", "identifier_link", "10.1000/inner")],
        },
        set(),
    ),
    (
        "r_reuse_one_use_per_name",
        'A{{r|x|y}}<ref name="x">X</ref><ref name="y">Y</ref>',
        'أ{{استشهاد متعدد|x|y}}<ref name="x">س</ref><ref name="y">ص</ref>',
        {
            "uses": [
                ("r", "x", "", "bound"),
                ("r", "y", "", "bound"),
                ("tag", "x", "", "bound"),
                ("tag", "y", "", "bound"),
            ]
        },
        set(),
    ),
    (
        "short_footnotes_identical_calls_are_one_footnote",
        "A{{sfn|Smith|2001|p=5}} B{{sfn|Smith|2001|p=5}}",
        "أ{{Sfn|سميث|2001|p=5}} ب{{Sfn|سميث|2001|p=5}}",
        {"containers": [("generated_note", None, "", "identical_definitions")]},
        set(),
    ),
    (
        "subreference_and_unsupported_context",
        'A<ref details="p. 5" name="sub">sub</ref> B<gallery>File:X.jpg|cap<ref>gal</ref></gallery>',
        'أ<ref details="ص. 5" name="sub">فرعي</ref> ب<gallery>ملف:X.jpg|تعليق<ref>معرض</ref></gallery>',
        {},
        {"SUBREFERENCE_UNSUPPORTED", "REF_IN_UNSUPPORTED_CONTEXT"},
    ),
    (
        "external_data_citation",
        "A<ref>{{Cite Q|Q42}}</ref>",
        "أ<ref>{{استشهاد بويكي بيانات|Q42}}</ref>",
        {"units": ["external_data_template"], "identifiers": []},
        set(),
    ),
    (
        "nested_and_wrapping_templates",
        "A<ref>{{small|{{cite journal |title=X {{lang|fr|Y}} |pmid=999}}}}</ref>",
        "أ<ref>{{صغير|{{استشهاد بدورية محكمة |عنوان=س {{lang|fr|Y}} |pmid=999}}}}</ref>",
        {"units": ["citation_template"], "identifiers": [("pmid", "primary_citation_field", "999")]},
        set(),
    ),
    (
        "doi_fields_and_preprint_fields",
        "A<ref>{{cite journal |DOI=10.1000/up |pmid=4242}} {{cite biorxiv |biorxiv=10.1101/2020.01.01.1}}</ref>",
        "أ<ref>{{استشهاد بدورية محكمة |DOI=10.1000/up |pmid=4242}} "
        "{{استشهاد ببيوركسيف |biorxiv=10.1101/2020.01.01.1}}</ref>",
        {
            "identifiers": [
                ("doi", "primary_citation_field", "10.1000/up"),
                ("pmid", "primary_citation_field", "4242"),
                ("doi", "primary_citation_field", "10.1101/2020.01.01.1"),
            ]
        },
        set(),
    ),
    (
        "identifier_in_an_unknown_template",
        "A<ref>{{Some infobox source |doi=10.1000/unk}}</ref>",
        "أ<ref>{{قالب غير معروف |دوي=10.1000/unk}}</ref>",
        {"identifiers": [("doi", "unresolved", "10.1000/unk")]},
        set(),
    ),
    (
        "wrappers_links_labels_and_pubmed_urls",
        "A<ref>{{doi|10.1000/wrap}} {{PMID|777}} https://dx.doi.org/10.1000/dx doi:10.1000/lab "
        "https://pubmed.ncbi.nlm.nih.gov/888/</ref>",
        "أ<ref>{{دوي|10.1000/wrap}} {{PMID|777}} https://dx.doi.org/10.1000/dx دوي:10.1000/lab "
        "https://pubmed.ncbi.nlm.nih.gov/888/</ref>",
        {
            "identifiers": [
                ("doi", "identifier_link", "10.1000/wrap"),
                ("pmid", "identifier_link", "777"),
                ("doi", "identifier_link", "10.1000/dx"),
                ("doi", "labeled_reference_text", "10.1000/lab"),
                ("pmid", "identifier_link", "888"),
            ]
        },
        set(),
    ),
    (
        "url_parameter_with_resolver",
        "A<ref>{{cite web |url=https://doi.org/10.1000/inurl |title=T}}</ref>",
        "أ<ref>{{استشهاد ويب |مسار=https://doi.org/10.1000/inurl |عنوان=ع}}</ref>",
        {"identifiers": [("doi", "identifier_link", "10.1000/inurl")]},
        set(),
    ),
    (
        "publisher_doi_path",
        "A<ref>https://onlinelibrary.wiley.com/doi/full/10.1002/abc.123</ref>",
        "أ<ref>https://onlinelibrary.wiley.com/doi/full/10.1002/abc.123</ref>",
        {"identifiers": [("doi", "identifier_link", "10.1002/abc.123")]},
        set(),
    ),
    (
        "percent_and_entity_decoding_once",
        "A<ref>https://doi.org/10.1000/a%2Fb%252F {{cite journal |doi=10.1000/q&amp;r}}</ref>",
        "أ<ref>https://doi.org/10.1000/a%2Fb%252F {{استشهاد بدورية محكمة |دوي=10.1000/q&amp;r}}</ref>",
        {
            "identifiers": [
                ("doi", "identifier_link", "10.1000/a/b%2f"),
                ("doi", "primary_citation_field", "10.1000/q&r"),
            ]
        },
        set(),
    ),
    (
        "multiple_works_and_repeated_doi_in_one_ref",
        "A<ref>{{cite journal |doi=10.1000/same}} {{cite journal |doi=10.1000/same}} "
        "{{cite book |doi=10.1000/other}}</ref>",
        "أ<ref>{{استشهاد بدورية محكمة |دوي=10.1000/same}} {{استشهاد بدورية محكمة |دوي=10.1000/same}} "
        "{{استشهاد بكتاب |دوي=10.1000/other}}</ref>",
        {
            "containers": [("note", None, "", "anonymous")],
            "units": ["citation_template"] * 3,
            "identifiers": [
                ("doi", "primary_citation_field", k) for k in ("10.1000/same", "10.1000/same", "10.1000/other")
            ],
        },
        set(),
    ),
    (
        "notice_title_and_marker_template",
        "A<ref>{{cite journal |title=Retraction note to 10.1000/orig |doi=10.1000/notice}} "
        "{{Retracted|doi=10.1000/rn}}</ref>",
        "أ<ref>{{استشهاد بدورية محكمة |عنوان=Retraction note to 10.1000/orig |دوي=10.1000/notice}} "
        "{{مصدر مسحوب|doi=10.1000/rn}}</ref>",
        {
            "identifiers": [
                ("doi", "textual_mention", "10.1000/orig"),
                ("doi", "primary_citation_field", "10.1000/notice"),
                ("doi", "marker_target", "10.1000/rn"),
            ]
        },
        set(),
    ),
    (
        "prose_mention",
        "In 2010 the paper 10.1000/prose was retracted.\n",
        "في 2010 سُحبت الورقة 10.1000/prose من الدورية.\n",
        {"identifiers": [("doi", "textual_mention", "10.1000/prose")]},
        set(),
    ),
    (
        "comment_nowiki_and_ref_name_are_not_targets",
        '<!-- doi=10.1000/comment --> <nowiki>10.1000/nowiki</nowiki><ref name="10.1000/inname">x</ref>',
        '<!-- دوي=10.1000/comment --> <nowiki>10.1000/nowiki</nowiki><ref name="10.1000/inname">س</ref>',
        {"identifiers": [], "excluded": ["comment", "tag:nowiki"]},
        set(),
    ),
    (
        "bibliography_entries_outside_footnotes",
        "Text.\n==Sources==\n* {{cite book |last=Smith |year=2001 |doi=10.1000/book}}\n* Jones, 1999. PMID 12345.\n",
        "نص.\n==مصادر==\n* {{استشهاد بكتاب |الأخير=سميث |سنة=2001 |دوي=10.1000/book}}\n* جونز، 1999. PMID 12345.\n",
        {
            "containers": [
                ("bibliography_entry", None, "", "*"),
                ("bibliography_entry", None, "", "*"),
            ],
            "uses": [],
            "identifiers": [
                ("doi", "primary_citation_field", "10.1000/book"),
                ("pmid", "labeled_reference_text", "12345"),
            ],
        },
        set(),
    ),
    (
        "identifierless_reference",
        "A<ref>Smith, J. A book. 2001.</ref>",
        "أ<ref>سميث، ج. كتاب. 2001.</ref>",
        {"units": ["unstructured_text"], "identifiers": []},
        set(),
    ),
]


def _matches(expected: Any, actual: Any, wiki: str) -> bool:
    """Compare with ``"*"`` as a wildcard and ``{"en": .., "ar": ..}`` as a per-language value."""
    if expected == "*":
        return True
    if isinstance(expected, dict) and set(expected) == {"en", "ar"}:
        return bool(expected[wiki] == actual)
    if isinstance(expected, (list, tuple)):
        return (
            isinstance(actual, (list, tuple))
            and len(expected) == len(actual)
            and all(_matches(e, a, wiki) for e, a in zip(expected, actual, strict=True))
        )
    return bool(expected == actual)


@pytest.mark.unit
@pytest.mark.parametrize("wiki", ["en", "ar"])
@pytest.mark.parametrize(("construct", "en", "ar", "expected", "required_codes"), CASES, ids=[c[0] for c in CASES])
def test_wiki_construct_in_each_language(
    tmp_path: Path, wiki: str, construct: str, en: str, ar: str, expected: dict[str, Any], required_codes: set[str]
) -> None:
    doc = extract(bundle(tmp_path, en if wiki == "en" else ar, wiki=wiki))
    got = summary(doc)
    for key, value in expected.items():
        assert _matches(value, got[key], wiki), (construct, wiki, key, got[key])
    assert required_codes <= codes(doc), (construct, wiki, sorted(codes(doc)))
    assert doc["accounting"]["checks"] and all(c["ok"] for c in doc["accounting"]["checks"])
