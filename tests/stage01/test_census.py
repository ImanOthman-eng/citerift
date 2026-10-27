"""Deterministic tests of the Stage 01 dump census and its live confirmation (no network, no dump files).

Run: uv run pytest tests/stage01 (CI runs them with the whole suite)
"""

from __future__ import annotations

import gzip
import importlib.util
from pathlib import Path
from typing import Any

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.negative]

SCRIPT = Path(__file__).resolve().parents[2] / "docs" / "verification" / "stage-01" / "scripts" / "stage01_census.py"
spec = importlib.util.spec_from_file_location("stage01_census", SCRIPT)
assert spec and spec.loader
census = importlib.util.module_from_spec(spec)
spec.loader.exec_module(census)

DOIS = {"10.1038/nature12968": [("1", "original")], "10.1371/journal.pone.0012345": [("2", "original")]}
PMIDS = {"12345": [("3", "original")], "777": [("4", "notice")]}


@pytest.mark.parametrize(
    ("index", "path", "expected"),
    [
        ("https://org.doi.", "/10.1038/nature12968", [("10.1038/nature12968", "doi_resolver")]),
        ("https://org.doi.dx.", "/10.1038%2FNATURE12968", [("10.1038/nature12968", "doi_resolver")]),
        ("https://com.nature.www.", "/articles/10.1038/nature12968.pdf", [("10.1038/nature12968", "doi_in_url")]),
        (
            "https://org.plos.journals.",
            "/a?id=10.1371/journal.pone.0012345&x=1",
            [("10.1371/journal.pone.0012345", "doi_in_url")],
        ),
        ("http://gov.nih.nlm.ncbi.pubmed.", "/12345/", [("12345", "pubmed")]),
        ("https://gov.nih.nlm.ncbi.www.", "/pubmed/12345", [("12345", "pubmed")]),
        ("https://org.europepmc.", "/article/MED/777", [("777", "europepmc")]),
    ],
)
def test_link_matches_known_identifiers(index: str, path: str, expected: list[tuple[str, str]]) -> None:
    got = census.link_matches(index, path, DOIS, PMIDS)
    assert [(m["id"], m["link_kind"]) for m in got] == expected


@pytest.mark.parametrize(
    ("index", "path"),
    [
        ("https://org.plos.journals.", "/a?id=10.1371/journal.pone.0012345.g001"),  # figure DOI, not the paper
        ("https://org.doi.", "/10.1038/nature129680"),  # longer DOI
        ("https://gov.nih.nlm.ncbi.www.", "/pubmed/123456"),  # longer PMID
        ("https://gov.nih.nlm.ncbi.pubmed.", "/99999/"),  # unknown PMID
        ("https://com.example.", "/12345"),  # a number on another site is not a PMID
    ],
)
def test_link_matches_rejects_near_misses(index: str, path: str) -> None:
    assert census.link_matches(index, path, DOIS, PMIDS) == []


def test_fields_unescape_and_null() -> None:
    line = b"(7,42,'https://org.doi.','/10.1000/a\\'b\\\\c'),"
    assert census.fields(line) == ["7", "42", "https://org.doi.", "/10.1000/a'b\\c"]
    assert census.fields(b"(1,0,'T',0,0,0.5,'20260101000000',NULL,99,10,'wikitext',NULL),") == [
        "1",
        "0",
        "T",
        "0",
        "0",
        "0.5",
        "20260101000000",
        None,
        "99",
        "10",
        "wikitext",
        None,
    ]


def test_domain_host_reverses_the_index() -> None:
    assert census.domain_host("https://gov.nih.nlm.ncbi.pubmed.") == ("https", "pubmed.ncbi.nlm.nih.gov")


def test_sql_rows_reads_one_row_per_line(tmp_path: Path) -> None:
    dump = tmp_path / "x.sql.gz"
    with gzip.open(dump, "wb") as f:
        f.write(b"-- header\nINSERT INTO `t` VALUES\n(1,2,'a','b'),\n(3,4,'10.1000/x','c');\n")
    assert list(census.sql_rows(dump)) == [b"(1,2,'a','b'),", b"(3,4,'10.1000/x','c');"]
    assert list(census.sql_rows(dump, r"10\.[0-9]{4}")) == [b"(3,4,'10.1000/x','c');"]


def test_check_dump_refuses_unpinned_or_changed_files(tmp_path: Path) -> None:
    other = tmp_path / "other.sql.gz"
    other.write_bytes(b"x")
    with pytest.raises(SystemExit, match="not a pinned dump"):
        census.check_dump(other)
    pinned = tmp_path / "arwiki-20261001-page.sql.gz"
    pinned.write_bytes(b"not the dump")
    with pytest.raises(SystemExit, match="differs from the published"):
        census.check_dump(pinned)


WIKITEXT = (
    "Text.<ref>{{cite journal |title=Stem cells |doi=10.1038/nature12968 |pmid=24476887}}"
    "{{Retracted|doi=10.1038/nature13598}}</ref> More.<ref>{{استشهاد بدورية محكمة|عنوان=س|بمد=12345}}</ref>"
    " Mention only: 10.1371/journal.pone.0012345 in prose."
)


def record(rid: str, nature: str, *via: tuple[str, str, str]) -> dict[str, Any]:
    return {
        "record_id": rid,
        "nature": nature,
        "via": [{"side": s, "id_type": "doi" if i.startswith("10.") else "pmid", "id": i} for s, i, _ in via],
    }


def test_assess_doi_cited_and_marked() -> None:
    out = census.assess(WIKITEXT, record("1", "Retraction", ("original", "10.1038/nature12968", "")))
    assert out["original"]["cited_in_wikitext"] == ["10.1038/nature12968"] and out["original"]["marked"] is True


def test_assess_pmid_with_arabic_alias_cited_not_marked() -> None:
    out = census.assess(WIKITEXT, record("3", "Retraction", ("original", "12345", "")))
    assert out["original"]["cited_in_wikitext"] == ["12345"] and out["original"]["marked"] is False


def test_assess_prose_mention_is_not_a_citation() -> None:
    out = census.assess(WIKITEXT, record("2", "Retraction", ("original", "10.1371/journal.pone.0012345", "")))
    assert out["original"]["cited_in_wikitext"] == []
    assert out["original"]["identifier_text_present"] == ["10.1371/journal.pone.0012345"]


def test_pmid_positions_need_a_whole_number() -> None:
    assert census.pmid_positions("|pmid=123456", "12345") == []
    assert census.pmid_positions("https://pubmed.ncbi.nlm.nih.gov/12345/", "12345") == [8]  # "pubmed"


class FakeClient:
    def __init__(self, *responses: dict[str, Any]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, str]] = []

    def get(self, url: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        self.calls.append(params or {})
        return self.responses.pop(0)


def answer(body: Any, status: int = 200) -> dict[str, Any]:
    return {"url": "u", "status": status, "retrieved_at": "t", "body": body}


def rev(pid: int, content: str) -> dict[str, Any]:
    revision = {"revid": pid * 10, "timestamp": "ts", "sha1": "s", "slots": {"main": {"content": content}}}
    return {"pageid": pid, "ns": 0, "title": f"P{pid}", "revisions": [revision]}


def test_fetch_current_error_body_is_a_failure_not_an_absence() -> None:
    client = FakeClient(answer({"error": {"code": "internal_api_error_DBQueryError"}}))
    got = census.fetch_current(client, "ar", [1, 2])
    assert got == {p: {"ok": False, "reason": "request_failed", "status": 200} for p in (1, 2)}


def test_fetch_current_batches_and_marks_missing_and_absent_pages() -> None:
    client = FakeClient(answer({"query": {"pages": [rev(1, "x"), {"pageid": 2, "missing": True}]}}))
    got = census.fetch_current(client, "ar", [1, 2, 3])
    assert client.calls[0]["pageids"] == "1|2|3"
    assert got[1]["ok"] and got[1]["content"] == "x"
    assert got[2] == {"ok": False, "reason": "missing"}
    assert got[3] == {"ok": False, "reason": "absent_from_response"}


def test_confirm_keeps_failed_pages_as_unknown() -> None:
    scan = {
        "wiki": "ar",
        "pages": [
            {"page_id": 1, "ns": 0, "redirect": False, "title": "P1", "records": [record("1", "Retraction")]},
            {"page_id": 5, "ns": 2, "redirect": False, "title": "U", "records": []},
        ],
    }
    out = census.confirm(FakeClient(answer({"error": {"code": "readonly"}})), scan, {0})
    [row] = out["pages"]
    assert row["ok"] is False and row["reason"] == "request_failed" and "records" not in row


def test_render_failure_is_render_unavailable() -> None:
    confirmed = {
        "wiki": "ar",
        "pages": [
            {
                "ok": True,
                "title": "P1",
                "revid": 10,
                "records": [
                    {
                        "record_id": "1",
                        "nature": "Retraction",
                        "original": {"cited_in_wikitext": ["12345"], "marked": False},
                    }
                ],
            }
        ],
    }
    out = census.render(FakeClient(answer({"error": {"code": "nosuchrevid"}})), confirmed, {"Retraction"})
    [check] = out["checks"]
    assert check["state"] == "render_unavailable"


def test_render_finds_pmid_only_reference() -> None:
    html = (
        '<ol class="references"><li id="cite_note-1"><span class="reference-text">س. '
        '<a href="https://pubmed.ncbi.nlm.nih.gov/12345">12345</a></span></li></ol>'
    )
    confirmed = {
        "wiki": "ar",
        "pages": [
            {
                "ok": True,
                "title": "P1",
                "revid": 10,
                "records": [
                    {
                        "record_id": "3",
                        "nature": "Retraction",
                        "original": {"cited_in_wikitext": ["12345"], "marked": False},
                    }
                ],
            }
        ],
    }
    out = census.render(FakeClient(answer({"parse": {"text": html, "revid": 10}})), confirmed, {"Retraction"})
    [check] = out["checks"]
    assert check["state"] == "no_warning_text_in_inspected_rendered_reference"


@pytest.mark.parametrize(
    ("src_marked", "dst", "expected"),
    [
        (True, None, "unknown_target_unavailable"),
        (True, {"cited_in_wikitext": [], "marked": False}, "not_carried"),
        (True, {"cited_in_wikitext": ["x"], "marked": True}, "carried_marked_both"),
        (True, {"cited_in_wikitext": ["x"], "marked": False}, "carried_marked_source_only"),
        (False, {"cited_in_wikitext": ["x"], "marked": True}, "carried_marked_target_only"),
        (False, {"cited_in_wikitext": ["x"], "marked": False}, "carried_marked_neither"),
    ],
)
def test_pair_category(src_marked: bool, dst: dict[str, Any] | None, expected: str) -> None:
    assert census.pair_category({"cited_in_wikitext": ["x"], "marked": src_marked}, dst) == expected


RW_ROWS = [
    {
        "Record ID": "1",
        "RetractionNature": "Retraction",
        "OriginalPaperDOI": "10.1038/nature12968",
        "OriginalPaperPubMedID": "24476887",
    }
]
SCAN = {
    "wiki": "en",
    "pages": [
        {
            "page_id": 7,
            "ns": 0,
            "redirect": False,
            "title": "STAP cell",
            "records": [record("1", "Retraction", ("original", "10.1038/nature12968", ""))],
        }
    ],
}
LMAP = {"map": {"7": "خلية ستاب"}, "targets": {"titles": {"خلية ستاب": {"page_id": 70, "redirect": False}}}}
EN = "<ref>{{cite journal |doi=10.1038/nature12968}}{{Retracted}}</ref>"


def test_crosswiki_carried_by_pmid_counts_and_warning_loss_is_seen() -> None:
    client = FakeClient(
        answer({"query": {"pages": [rev(7, EN)]}}),
        answer({"query": {"pages": [rev(70, "<ref>{{استشهاد بدورية محكمة|بمد=24476887}}</ref>")]}}),
    )
    out = census.crosswiki_census(client, RW_ROWS, SCAN, LMAP, "ar", {"Retraction"}, history=False)
    [pair] = out["pairs"]
    assert pair["status"] == "ok" and pair["category"] == "carried_marked_source_only"
    assert pair["target"]["cited_in_wikitext"] == ["24476887"]


def test_crosswiki_target_failure_is_unknown_not_absent() -> None:
    client = FakeClient(answer({"query": {"pages": [rev(7, EN)]}}), answer({"error": {"code": "maxlag"}}, 200))
    out = census.crosswiki_census(client, RW_ROWS, SCAN, LMAP, "ar", {"Retraction"}, history=False)
    [pair] = out["pairs"]
    assert pair["status"] == "target_fetch_failed" and pair["category"] == "unknown_target_unavailable"


def test_crosswiki_history_tells_removed_from_never_carried() -> None:
    first = {"revid": 1, "timestamp": "2015-01-01T00:00:00Z", "slots": {"main": {"content": EN}}}
    then = {"revid": 2, "timestamp": "2014-12-31T00:00:00Z", "slots": {"main": {"content": EN}}}
    client = FakeClient(
        answer({"query": {"pages": [rev(7, EN)]}}),
        answer({"query": {"pages": [rev(70, "لا مراجع")]}}),
        answer({"query": {"pages": [{"pageid": 70, "revisions": [first]}]}}),
        answer({"query": {"pages": [{"pageid": 7, "revisions": [then]}]}}),
    )
    out = census.crosswiki_census(client, RW_ROWS, SCAN, LMAP, "ar", {"Retraction"}, history=True)
    [pair] = out["pairs"]
    assert pair["category"] == "not_carried"
    assert pair["history"]["target_first_cites"] is True  # carried at creation, removed later
    assert pair["history"]["source_cited_at_target_creation"] is True
    assert client.calls[2]["rvdir"] == "newer" and client.calls[3]["rvstart"] == "2015-01-01T00:00:00Z"


def test_crosswiki_without_langlink_sends_no_target_request() -> None:
    client = FakeClient(answer({"query": {"pages": []}}), answer({"query": {"pages": []}}))
    out = census.crosswiki_census(
        client, RW_ROWS, SCAN, {"map": {}, "targets": {"titles": {}}}, "ar", {"Retraction"}, False
    )
    assert out["source_articles_citing"] == 1 and out["source_articles_with_target_link"] == 0 and out["pairs"] == []


def test_work_key_groups_records_of_one_paper() -> None:
    by_doi = record("1", "Retraction", ("original", "10.1371/journal.pgen.0030110", ""))
    again = record("2", "Retraction", ("original", "10.1371/journal.pgen.0030110", ""))
    pmid_only = record("3", "Retraction", ("original", "12345", ""))
    assert census.work_key(by_doi) == census.work_key(again) == "10.1371/journal.pgen.0030110"
    assert census.work_key(pmid_only) == "pmid:12345"


def one_page(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {"wiki": "ar", "pages": [{"ok": True, "title": "P1", "revid": 10, "records": records}]}


CITED = {"record_id": "1", "nature": "Retraction", "original": {"cited_in_wikitext": ["10.1000/x"], "marked": False}}
LINK_X = '<a class="external text" href="https://doi.org/10.1000%2Fx">10.1000/x</a>'


def test_render_falls_back_to_a_bibliography_item_outside_the_footnotes() -> None:
    html = f'<h2>قراءات إضافية</h2><ul><li><cite>"RETRACTED: A paper". {LINK_X}</cite> (Retracted)</li></ul>'
    out = census.render(FakeClient(answer({"parse": {"text": html, "revid": 10}})), one_page([CITED]), {"Retraction"})
    [check] = out["checks"]
    assert check["location"] == "outside_footnotes" and check["state"] == "warning_text_in_rendered_reference"
    assert check["references"][0]["location"] == "li_outside_footnotes"


def test_render_title_word_inside_cite_is_not_a_warning_outside_footnotes() -> None:
    html = f'<ul><li><cite>"RETRACTED: A paper". {LINK_X}</cite></li></ul>'
    out = census.render(FakeClient(answer({"parse": {"text": html, "revid": 10}})), one_page([CITED]), {"Retraction"})
    [check] = out["checks"]
    assert check["state"] == "no_warning_text_in_inspected_rendered_reference"


def test_render_prefers_footnotes_and_ignores_other_blocks_then() -> None:
    html = (
        f"<p>See {LINK_X} (retracted).</p>"
        f'<ol class="references"><li id="cite_note-1"><span class="reference-text">{LINK_X}</span></li></ol>'
    )
    out = census.render(FakeClient(answer({"parse": {"text": html, "revid": 10}})), one_page([CITED]), {"Retraction"})
    [check] = out["checks"]
    assert check["location"] == "footnotes" and check["state"] == "no_warning_text_in_inspected_rendered_reference"


def test_render_identifier_absent_from_html_is_not_found() -> None:
    out = census.render(
        FakeClient(answer({"parse": {"text": "<p>x</p>", "revid": 10}})), one_page([CITED]), {"Retraction"}
    )
    [check] = out["checks"]
    assert check["state"] == "reference_not_found_in_render" and check["location"] is None
