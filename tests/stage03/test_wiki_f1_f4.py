"""Regressions for the external review findings F1-F4 (owner directive 2026-10-29, section 4).

Mapping: F1 = RF-39, F2 = RF-40, F3 = RF-41, F4 = RF-42; RF-43 is the short-footnote key check that F4 asked for.
All inputs are SYNTHETIC. The before outputs are in docs/verification/stage-03/review/failfirst/f1-f4/.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from wiki_support import bundle, codes, extract, note_li, ref_sup, references

from citerift.wiki.source import ParamRecord, effective_arguments

AR_REUSE = "استشهاد متعدد"


def uses(doc: dict[str, Any]) -> list[tuple[str, str | None, str, int]]:
    return [(u["origin"], u["name"], u["binding"], u["position"]) for u in doc["uses"]]


def r_uses(doc: dict[str, Any]) -> list[tuple[str | None, str]]:
    return [(u["name"], u["binding"]) for u in doc["uses"] if u["origin"] == "r"]


def issue_details(doc: dict[str, Any], code: str) -> list[str]:
    return [i.get("detail") or "" for i in doc["issues"] if i["code"] == code]


# ----------------------------------------------------------------------------- F4 / RF-42: numbered reuse names

DEFS = '<ref name="a">Paper A</ref> <ref name="b">Paper B</ref> '


@pytest.mark.unit
@pytest.mark.parametrize(
    ("wiki", "calls"),
    [
        ("en", ["{{r|a}}", "{{r|1=a}}", "{{r| 1 = a }}", "{{r|name=a}}", "{{r|n=a}}", "{{r|name1=a}}", "{{R|1=a}}"]),
        ("ar", ["{{استشهاد متعدد|a}}", "{{استشهاد متعدد|1=a}}", "{{استشهاد متعدد| 1 =a}}", "{{R|1=a}}"]),
    ],
)
def test_wiki_explicitly_numbered_reuse_is_the_same_use(tmp_path: Path, wiki: str, calls: list[str]) -> None:
    """F4: {{r|1=a}} lost the reuse; implicit and explicit numbering must give the same use and binding facts."""
    facts = []
    for i, call in enumerate(calls):
        doc = extract(bundle(tmp_path, f'A.<ref name="a">Paper</ref> B.{call}', wiki=wiki, name=f"c{i}"))
        facts.append(uses(doc))
        assert not {"REUSE_NAME_MISSING", "REUSE_NAME_NOT_USED"} & codes(doc), call
    assert facts == [[("tag", "a", "bound", 0), ("r", "a", "bound", 0)]] * len(calls)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("wiki", "calls"),
    [
        (
            "en",
            ["{{r|a|b}}", "{{r|1=a|2=b}}", "{{r|2=b|1=a}}", "{{r|a|2=b}}", "{{r|name1=a|name2=b}}", "{{r|n=a|n2=b}}"],
        ),
        ("ar", ["{{استشهاد متعدد|a|b}}", "{{استشهاد متعدد|2=b|1=a}}", "{{استشهاد متعدد|a|2=b}}"]),
    ],
)
def test_wiki_reuse_names_follow_numeric_order(tmp_path: Path, wiki: str, calls: list[str]) -> None:
    """The order of the uses is the numeric order of the arguments, not the order they are written in."""
    for i, call in enumerate(calls):
        doc = extract(bundle(tmp_path, DEFS + call, wiki=wiki, name=f"c{i}"))
        assert [(n, b, p) for o, n, b, p in uses(doc) if o == "r"] == [("a", "bound", 0), ("b", "bound", 1)], call


@pytest.mark.unit
@pytest.mark.parametrize("wiki", ["en", "ar"])
@pytest.mark.parametrize(("args", "expected"), [("a|1=b", "b"), ("1=b|a", "a"), ("1=a|1=b", "b")])
def test_wiki_a_replaced_reuse_argument_creates_no_phantom_use(
    tmp_path: Path, wiki: str, args: str, expected: str
) -> None:
    """A later argument with the same key replaces the earlier one (MediaWiki), and the replaced one is reported."""
    name = "r" if wiki == "en" else AR_REUSE
    doc = extract(bundle(tmp_path, DEFS + "{{" + name + "|" + args + "}}", wiki=wiki))
    assert r_uses(doc) == [(expected, "bound")]
    assert len(issue_details(doc, "REUSE_ARGUMENT_REPLACED")) == 1


@pytest.mark.unit
@pytest.mark.parametrize(
    ("wiki", "call", "names", "not_used"),
    [
        # Module:R stops at the first number without a non-blank name; blank arguments count as absent.
        ("en", "{{r|a||b}}", ["a"], 1),
        ("en", "{{r|1=a|3=b}}", ["a"], 1),
        ("en", "{{r|a| |b}}", ["a"], 1),
        # name= is read before 1, so the numbered name is not read; 2 is then missing.
        ("en", "{{r|name=a|b}}", ["a"], 1),
        ("en", "{{r|01=a}}", [None], 1),
        # The Arabic template nests its #if tests: an empty argument hides all later ones; at most 9 names.
        ("ar", "{{استشهاد متعدد|a||b}}", ["a"], 1),
        ("ar", "{{استشهاد متعدد|a|<!-- -->|b}}", ["a"], 1),
        ("ar", "{{استشهاد متعدد|" + "|".join("a" * 10) + "}}", ["a"] * 9, 1),
    ],
)
def test_wiki_reuse_names_the_template_does_not_read(
    tmp_path: Path, wiki: str, call: str, names: list[str | None], not_used: int
) -> None:
    doc = extract(bundle(tmp_path, DEFS + call, wiki=wiki))
    assert [n for n, _ in r_uses(doc)] == names
    assert len(issue_details(doc, "REUSE_NAME_NOT_USED")) == not_used


@pytest.mark.unit
def test_wiki_reuse_without_a_first_name(tmp_path: Path) -> None:
    """enwiki writes name="" (an empty use); arwiki passes the literal text {{{1}}} as the name."""
    en = extract(bundle(tmp_path, DEFS + "{{r|}}", name="en"))
    assert r_uses(en) == [(None, "empty_anonymous")]
    assert "REUSE_NAME_MISSING" in codes(en)
    ar = extract(bundle(tmp_path, DEFS + "{{استشهاد متعدد|2=b}}", wiki="ar", name="ar"))
    assert r_uses(ar) == [("{{{1}}}", "definition_missing"), ("b", "bound")]
    assert "REUSE_NAME_MISSING" in codes(ar)
    ar_named = extract(bundle(tmp_path, DEFS + "{{استشهاد متعدد|name=a}}", wiki="ar", name="arn"))
    assert r_uses(ar_named) == [("{{{1}}}", "definition_missing")]


@pytest.mark.unit
@pytest.mark.parametrize(
    ("wiki", "call"),
    [
        ("en", "{{r|group=n|a}}"),
        ("en", "{{r|grp=n|1=a}}"),
        ("en", "{{r|a|g=n}}"),
        ("ar", "{{استشهاد متعدد|a|group=n}}"),
        ("ar", "{{استشهاد متعدد|group=n|1=a}}"),
    ],
)
def test_wiki_reuse_groups(tmp_path: Path, wiki: str, call: str) -> None:
    doc = extract(bundle(tmp_path, '<ref name="a" group="n">Note</ref> ' + call, wiki=wiki))
    assert [(u["origin"], u["group"], u["binding"]) for u in doc["uses"]] == [
        ("tag", "n", "bound"),
        ("r", "n", "bound"),
    ]


@pytest.mark.unit
def test_wiki_reuse_content_and_markup_have_dispositions(tmp_path: Path) -> None:
    content = extract(bundle(tmp_path, DEFS + "{{r|a|r=Extra text}} {{r|b|style=sub|p=4}}", name="c"))
    assert r_uses(content) == [("a", "bound"), ("b", "bound")]
    assert len(issue_details(content, "REUSE_CONTENT_UNSUPPORTED")) == 2
    pages = extract(bundle(tmp_path, DEFS + "{{r|a|p=4|quote=Q}}", name="p"))
    assert r_uses(pages) == [("a", "bound")]
    assert "REUSE_CONTENT_UNSUPPORTED" not in codes(pages)
    markup = extract(bundle(tmp_path, DEFS + "{{r|{{x}}|b}}", name="m"))
    assert r_uses(markup) == [("{{x}}", "unbindable_name"), ("b", "bound")]
    assert "REF_NAME_HAS_MARKUP" in codes(markup)


def _reuse_render(call: str, name: str) -> tuple[str, str]:
    """The source and a structurally faithful Parsoid render: one note, reused by a transcluded reuse template."""
    text = f'A.<ref name="a">Paper</ref> B.{call}'
    params = {"1": {"wt": "a"}}
    tpl = json.dumps(
        {"parts": [{"template": {"target": {"wt": name, "href": f"./Template:{name}"}, "params": params, "i": 0}}]},
        ensure_ascii=False,
    )
    first = ref_sup(1, "cite_note-a-1", "cite_ref-a_1-0", name="a")
    second = ref_sup(1, "cite_note-a-1", "cite_ref-a_1-1", name="a").replace('about="#mwt1"', 'about="#mwt5"')
    lead = f'<link rel="mw-deduplicated-inline-style" about="#mwt5" typeof="mw:Transclusion" data-mw=\'{tpl}\'/>'
    body = f"<p>A.{first} B.{lead}{second}</p>" + references(
        [note_li("cite_note-a-1", ["cite_ref-a_1-0", "cite_ref-a_1-1"], "Paper")]
    )
    return text, body


@pytest.mark.unit
@pytest.mark.parametrize(
    ("wiki", "calls", "name"),
    [("en", ["{{r|a}}", "{{r|1=a}}"], "R"), ("ar", ["{{استشهاد متعدد|a}}", "{{استشهاد متعدد|1=a}}"], AR_REUSE)],
)
def test_wiki_rendered_reuse_is_equivalent_for_both_numberings(
    tmp_path: Path, wiki: str, calls: list[str], name: str
) -> None:
    facts = []
    for i, call in enumerate(calls):
        text, body = _reuse_render(call, name)
        doc = extract(bundle(tmp_path, text, body, wiki=wiki, name=f"c{i}"))
        facts.append([(u["origin"], u["name"], u["binding"], u["render"]["state"]) for u in doc["uses"]])
    assert facts[0] == facts[1]
    assert facts[1] == [("tag", "a", "bound", "matched"), ("r", "a", "bound", "matched")]


@pytest.mark.unit
def test_wiki_effective_arguments_follow_the_preprocessor() -> None:
    def p(name: str, showkey: bool, at: int) -> ParamRecord:
        return ParamRecord(name, name.strip(), showkey, at, at + 1, at, at + 1)

    params = [p("1", True, 0), p("1", False, 2), p("x", True, 4), p("2", False, 6), p("01", True, 8)]
    effective, replaced = effective_arguments(params)
    assert {k: v.start for k, v in effective.items()} == {"1": 2, "x": 4, "2": 6, "01": 8}
    assert [r.start for r in replaced] == [0]


# ------------------------------------------------------------------------ RF-43: the short-footnote key check


@pytest.mark.unit
@pytest.mark.parametrize("wiki", ["en", "ar"])
def test_wiki_short_footnote_key_uses_effective_arguments(tmp_path: Path, wiki: str) -> None:
    """{{sfn|Smith|2001}} and {{sfn|1=Smith|2=2001}} are one call to Module:Footnotes, so one note; a replaced
    argument does not count; different effective arguments stay different notes."""
    same = extract(
        bundle(
            tmp_path,
            "A{{sfn|Smith|2001|p=5}} B{{sfn|1=Smith|2=2001|p=5}} C{{sfn|p=5|2=2001|1=Smith}}"
            " D{{sfn|Jones|2001|p=5|1=Smith}}",
            wiki=wiki,
            name="s",
        )
    )
    assert [len(c["definitions"]) for c in same["containers"]] == [4]
    different = extract(bundle(tmp_path, "A{{sfn|Smith|2001|p=5}} B{{sfn|Smith|2001|p=6}}", wiki=wiki, name="d"))
    assert len(different["containers"]) == 2
