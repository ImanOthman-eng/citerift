"""Source/render reconciliation, marker observations and the exception ledger on SYNTHETIC Parsoid HTML.

The HTML is a minimal Parsoid 2.8.0 document written by ``wiki_support`` (reference markers typed
``mw:Extension/ref`` with ``data-mw``, a ``mw:Extension/references`` list, ``mw:ExtLink`` identifier links).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from wiki_support import bundle, capture, codes, doi_link, extract, note_li, parsoid, ref_sup, references

from citerift.wiki.capture import CaptureRequest
from citerift.wiki.verify import verify_bundle

REUSE_TEXT = (
    'Alpha.<ref name="a">{{cite journal |title=T |doi=10.1234/abc |pmid=123}}</ref> '
    "Beta.<ref>Plain text https://doi.org/10.5555/xyz</ref> "
    'Gamma.<ref name="a" />\n\n==References==\n{{reflist}}\n'
)
REUSE_BODY = (
    "<p>Alpha."
    + ref_sup(1, "cite_note-a-1", "cite_ref-a_1-0", name="a")
    + " Beta."
    + ref_sup(2, "cite_note-2", "cite_ref-2")
    + " Gamma."
    + ref_sup(1, "cite_note-a-1", "cite_ref-a_1-1", name="a")
    + "</p>"
    + references(
        [
            note_li(
                "cite_note-a-1",
                ["cite_ref-a_1-0", "cite_ref-a_1-1"],
                '<cite class="citation journal cs1">T. ' + doi_link("10.1234/abc") + "</cite>",
            ),
            note_li(
                "cite_note-2", ["cite_ref-2"], "Plain text " + doi_link("10.5555/xyz", "https://doi.org/10.5555/xyz")
            ),
        ]
    )
)


def one_note(text: str, inner: str, tmp_path: Path, name: str = "b") -> dict[str, Any]:
    body = (
        "<p>A."
        + ref_sup(1, "cite_note-a-1", "cite_ref-a_1-0", name="a")
        + "</p>"
        + references([note_li("cite_note-a-1", ["cite_ref-a_1-0"], inner)])
    )
    return extract(bundle(tmp_path, text, body, name=name))


@pytest.mark.integration
def test_wiki_reused_reference_links_every_use(tmp_path: Path) -> None:
    doc = extract(bundle(tmp_path, REUSE_TEXT, REUSE_BODY))
    assert doc["status"] == "complete"
    links = [(u["name"], u["render"]["state"], u["render"]["locator"]["element_id"]) for u in doc["uses"]]
    assert links == [
        ("a", "matched", "cite_ref-a_1-0"),
        (None, "matched", "cite_ref-2"),
        ("a", "matched", "cite_ref-a_1-1"),
    ]
    named = doc["containers"][0]
    assert named["render"] == {"state": "matched", "region_id": "cite_note-a-1"}
    assert len(named["use_ids"]) == 2
    states = {(i["scheme"], i["normalization"]["normalized"]): i["render"]["state"] for i in doc["identifiers"]}
    assert states[("doi", "10.1234/abc")] == "render_link_found"
    assert states[("doi", "10.5555/xyz")] == "render_link_found"
    assert states[("pmid", "123")] == "no_render_link_in_region"
    assert all(c["ok"] for c in doc["accounting"]["checks"])


@pytest.mark.integration
def test_wiki_locators_reverify(tmp_path: Path) -> None:
    path = bundle(tmp_path, REUSE_TEXT, REUSE_BODY)
    doc = extract(path)
    report = verify_bundle(path, doc)
    assert report["verified"], report["issues"]


@pytest.mark.negative
def test_wiki_no_render_means_unavailable_never_absent(tmp_path: Path) -> None:
    doc = extract(bundle(tmp_path, REUSE_TEXT))
    assert doc["status"] == "partial"
    assert {m["state"] for m in doc["markers"]} == {"unavailable"}
    assert {u["render"]["state"] for u in doc["uses"]} == {"not_reconciled"}
    assert {i["render"]["state"] for i in doc["identifiers"]} == {"not_reconciled"}
    assert "RECONCILIATION_UNAVAILABLE" in codes(doc)


@pytest.mark.negative
def test_wiki_render_of_another_revision_is_rejected(tmp_path: Path) -> None:
    html = parsoid(REUSE_BODY, REUSE_TEXT, revision=123)
    outcome = capture(tmp_path / "b", REUSE_TEXT, html)
    assert outcome.status == "partial"
    assert outcome.record["render"]["state"] == "rejected"
    assert "RENDER_REVISION_MISMATCH" in {i.code for i in outcome.issues}
    assert outcome.bundle is not None
    doc = extract(outcome.bundle)
    assert {m["state"] for m in doc["markers"]} == {"unavailable"}
    assert doc["capture"]["revision_id"] == 900_000_001  # the source identity is untouched


@pytest.mark.negative
def test_wiki_render_with_other_sha1_is_rejected(tmp_path: Path) -> None:
    html = parsoid(REUSE_BODY, REUSE_TEXT, sha1_hex="0" * 40)
    outcome = capture(tmp_path / "b", REUSE_TEXT, html)
    assert outcome.record["render"]["state"] == "rejected"
    assert "RENDER_REVISION_MISMATCH" in {i.code for i in outcome.issues}


@pytest.mark.reproducibility
def test_wiki_two_render_captures_keep_source_identity(tmp_path: Path) -> None:
    """Changing only the render capture cannot change the source revision identity or source anchors."""
    other = REUSE_BODY.replace("Plain text ", "Plain  text ")
    a = extract(bundle(tmp_path, REUSE_TEXT, REUSE_BODY, name="a"))
    b = extract(bundle(tmp_path, REUSE_TEXT, other, name="b"))
    assert a["capture"]["source_artifact"] == b["capture"]["source_artifact"]
    assert a["capture"]["render_artifact"] != b["capture"]["render_artifact"]
    for key in ("identifiers", "uses", "units"):
        assert [x["source"] for x in a[key]] == [x["source"] for x in b[key]]


@pytest.mark.negative
def test_wiki_duplicate_note_ids_are_ambiguous(tmp_path: Path) -> None:
    """RF-03: two notes with one DOM id must not attach either reference to whichever element comes first."""
    text = 'A.<ref name="a">one</ref> B.<ref name="b">two</ref>\n'
    body = (
        "<p>A."
        + ref_sup(1, "cite_note-a-1", "cite_ref-a_1-0", name="a")
        + " B."
        + ref_sup(2, "cite_note-a-1", "cite_ref-b_2-0", name="b")
        + "</p>"
        + references(
            [note_li("cite_note-a-1", ["cite_ref-a_1-0"], "one"), note_li("cite_note-a-1", ["cite_ref-b_2-0"], "two")]
        )
    )
    doc = extract(bundle(tmp_path, text, body))
    assert [c["render"]["state"] for c in doc["containers"]] == ["note_ambiguous", "note_ambiguous"]
    assert [m["state"] for m in doc["markers"]] == ["not_inspected", "not_inspected"]
    assert {"DOM_ID_DUPLICATE", "RENDER_NOTE_AMBIGUOUS"} <= codes(doc)
    assert {e["code"] for e in doc["exceptions"] if e["entity_type"] == "container"} == {"RECONCILIATION_AMBIGUOUS"}


@pytest.mark.negative
def test_wiki_missing_note_target(tmp_path: Path) -> None:
    text = 'A.<ref name="a">one</ref> B.<ref name="b">two</ref>\n'
    body = (
        "<p>A."
        + ref_sup(1, "cite_note-a-1", "cite_ref-a_1-0", name="a")
        + " B."
        + ref_sup(2, "cite_note-b-2", "cite_ref-b_2-0", name="b")
        + "</p>"
        + references([note_li("cite_note-a-1", [], "one")])
    )
    doc = extract(bundle(tmp_path, text, body))
    assert [c["render"]["state"] for c in doc["containers"]] == ["matched", "note_missing"]
    assert doc["markers"][1]["state"] == "not_inspected"
    assert "RENDER_TARGET_MISSING" in codes(doc)


@pytest.mark.negative
def test_wiki_malformed_html_abstains(tmp_path: Path) -> None:
    text = 'A.<ref name="a">one</ref> B.<ref name="b">two</ref>\n'
    body = '<p>A.<sup typeof="mw:Extension/ref" data-mw="{bad json"><a href="#cite_note-x">[1]</a></sup><div><span></p>'
    doc = extract(bundle(tmp_path, text, body))
    assert {u["render"]["state"] for u in doc["uses"]} == {"abstained"}
    assert {m["state"] for m in doc["markers"]} == {"not_inspected"}
    assert {"RENDER_DATA_MW_INVALID", "RECONCILIATION_ABSTAINED"} <= codes(doc)


@pytest.mark.integration
def test_wiki_template_generated_reference_is_render_only(tmp_path: Path) -> None:
    text = '{{Infobox drug |x=1}} A.<ref name="a">one {{cite journal|doi=10.1000/src}}</ref>\n'
    dm = '{"parts":[{"template":{"target":{"wt":"Infobox drug"},"params":{"x":{"wt":"1"}},"i":0}}]}'
    body = (
        f'<table about="#mwt5" typeof="mw:Transclusion" data-mw=\'{dm}\'><tr><td>X'
        + ref_sup(1, "cite_note-1", "cite_ref-1").replace('about="#mwt1"', 'about="#mwt5"')
        + "</td></tr></table><p>A."
        + ref_sup(2, "cite_note-a-2", "cite_ref-a_2-0", name="a")
        + "</p>"
        + references(
            [
                note_li("cite_note-1", ["cite_ref-1"], "Wikidata ref " + doi_link("10.1000/wd")),
                note_li("cite_note-a-2", ["cite_ref-a_2-0"], "one " + doi_link("10.1000/src")),
            ]
        )
    )
    doc = extract(bundle(tmp_path, text, body))
    assert doc["uses"][0]["render"]["state"] == "matched"
    assert len(doc["render_only"]["uses"]) == 1
    assert [x["normalized"] for x in doc["render_only"]["identifiers"]] == ["10.1000/wd"]
    # No source span is invented for the generated reference.
    assert all(i["normalization"]["normalized"] != "10.1000/wd" for i in doc["identifiers"])
    assert {"RENDER_ONLY_IDENTIFIER", "RENDER_USE_UNMATCHED"} <= {e["code"] for e in doc["exceptions"]}


# --------------------------------------------------------------------------------------------- markers

MARKED = 'A.<ref name="a">{{cite journal |title=Paper |doi=10.1000/p}} {{Retracted|doi=10.1000/n}}</ref>\n'


@pytest.mark.integration
def test_wiki_marker_rendered_warning(tmp_path: Path) -> None:
    inner = (
        "<cite>Paper. " + doi_link("10.1000/p") + "</cite> <span>(Retracted, see " + doi_link("10.1000/n") + ")</span>"
    )
    m = one_note(MARKED, inner, tmp_path)["markers"][0]
    assert m["state"] == "recognized_warning_text"
    assert m["source_marker_templates"][0]["template"] == "Retracted"
    assert m["browser_visibility"] == "not_evaluated"
    assert m["evidence"][0]["matched"] == "Retracted"


@pytest.mark.integration
def test_wiki_marker_missing_template_red_link(tmp_path: Path) -> None:
    red = (
        '<a rel="mw:WikiLink" href="./Template:Retracted?action=edit&amp;redlink=1" title="Template:Retracted" '
        'class="new">Template:Retracted</a>'
    )
    m = one_note(MARKED, "<cite>Paper " + doi_link("10.1000/p") + "</cite> " + red, tmp_path)["markers"][0]
    assert m["state"] == "missing_template_link_only"
    assert m["source_marker_templates"], "the source marker is kept separately"


@pytest.mark.negative
def test_wiki_marker_title_prefix_is_not_a_confirmed_warning(tmp_path: Path) -> None:
    text = 'A.<ref name="a">{{cite journal |title=RETRACTED: Paper |doi=10.1000/p}}</ref>\n'
    m = one_note(text, '<cite>"RETRACTED: Paper". ' + doi_link("10.1000/p") + "</cite>", tmp_path)["markers"][0]
    assert m["state"] == "ambiguous_text"


@pytest.mark.negative
def test_wiki_marker_ambiguous_word(tmp_path: Path) -> None:
    text = 'A.<ref name="a">{{cite journal |title=Paper withdrawn |doi=10.1000/p}}</ref>\n'
    m = one_note(text, '<cite>"Paper withdrawn". ' + doi_link("10.1000/p") + "</cite>", tmp_path)["markers"][0]
    assert m["state"] == "ambiguous_text"


@pytest.mark.negative
def test_wiki_marker_hidden_term_is_never_a_negative(tmp_path: Path) -> None:
    """RF-02: a warning term only in hidden text makes the region ambiguous, not "no warning"."""
    text = 'A.<ref name="a">{{cite journal |title=Paper |doi=10.1000/p}}</ref>\n'
    inner = "<cite>Paper " + doi_link("10.1000/p") + '</cite><span style="display:none">Retracted</span>'
    m = one_note(text, inner, tmp_path)["markers"][0]
    assert m["state"] == "ambiguous_text"
    assert [e["kind"] for e in m["evidence"]] == ["hidden"]


@pytest.mark.negative
def test_wiki_marker_script_and_style_text_ignored(tmp_path: Path) -> None:
    text = 'A.<ref name="a">{{cite journal |title=Paper |doi=10.1000/p}}</ref>\n'
    inner = "<cite>Paper " + doi_link("10.1000/p") + "</cite><style>.retracted{}</style><script>retracted()</script>"
    m = one_note(text, inner, tmp_path)["markers"][0]
    assert m["state"] == "no_recognized_warning_in_inspected_region"


@pytest.mark.unit
def test_wiki_marker_arabic_warning_and_stem(tmp_path: Path) -> None:
    text = 'أ.<ref name="a">{{استشهاد بدورية محكمة|عنوان=ورقة|دوي=10.1000/p}}</ref>\n'
    body = lambda inner: (  # noqa: E731
        "<p>أ."
        + ref_sup(1, "cite_note-a-1", "cite_ref-a_1-0", name="a")
        + "</p>"
        + references([note_li("cite_note-a-1", ["cite_ref-a_1-0"], inner)])
    )
    warn = extract(bundle(tmp_path, text, body("<cite>ورقة</cite> (مصدر مسحوب)"), wiki="ar", name="w"))
    assert warn["markers"][0]["state"] == "recognized_warning_text"
    broad = extract(bundle(tmp_path, text, body("<cite>ورقة</cite> سحب الجيش"), wiki="ar", name="s"))
    assert broad["markers"][0]["state"] == "ambiguous_text"


@pytest.mark.negative
def test_wiki_render_not_requested_marker_unavailable(tmp_path: Path) -> None:
    outcome = capture(tmp_path / "b", MARKED, None, request=CaptureRequest("en", revision_id=900_000_001, render=False))
    assert outcome.bundle is not None
    doc = extract(outcome.bundle)
    assert doc["markers"][0]["state"] == "unavailable"
    assert doc["markers"][0]["source_marker_templates"][0]["template"] == "Retracted"


@pytest.mark.negative
@pytest.mark.parametrize("wiki", ["en", "ar"])
def test_wiki_marker_order_against_the_list_numbering_abstains(tmp_path: Path, wiki: str) -> None:
    # RF-07: the render shows the marker of note 2 first; position pairing would attach "one" to note "two".
    text = "A.<ref>one</ref> B.<ref>two</ref>\n"
    body = (
        "<p>A."
        + ref_sup(2, "cite_note-2", "cite_ref-2")
        + " B."
        + ref_sup(1, "cite_note-1", "cite_ref-1")
        + "</p>"
        + references([note_li("cite_note-1", ["cite_ref-1"], "one"), note_li("cite_note-2", ["cite_ref-2"], "two")])
    )
    doc = extract(bundle(tmp_path, text, body, wiki=wiki))
    assert [u["render"]["state"] for u in doc["uses"]] == ["abstained", "abstained"]
    assert {c["render"]["state"] for c in doc["containers"]} != {"matched"}
    assert "RECONCILIATION_ABSTAINED" in codes(doc)
    assert {m["state"] for m in doc["markers"]} == {"not_inspected"}


@pytest.mark.negative
def test_wiki_anchor_does_not_license_a_misordered_neighbour(tmp_path: Path) -> None:
    # The named anchor is consistent, the anonymous use between anchors would take an earlier note: abstain.
    text = 'S0.<ref>zero</ref> S1.<ref name="n">body</ref> S2.<ref>two</ref> S3.<ref name="n" />\n'
    body = (
        "<p>S0."
        + ref_sup(2, "cite_note-n-2", "cite_ref-n_2-1", name="n")
        + " S1."
        + ref_sup(1, "cite_note-1", "cite_ref-1")
        + " S2."
        + ref_sup(2, "cite_note-n-2", "cite_ref-n_2-0", name="n")
        + " S3."
        + ref_sup(3, "cite_note-3", "cite_ref-3")
        + "</p>"
        + references(
            [
                note_li("cite_note-1", ["cite_ref-1"], "zero"),
                note_li("cite_note-n-2", ["cite_ref-n_2-0", "cite_ref-n_2-1"], "body"),
                note_li("cite_note-3", ["cite_ref-3"], "two"),
            ]
        )
    )
    doc = extract(bundle(tmp_path, text, body))
    linked = {
        text[u["source"]["cp_start"] : u["source"]["cp_end"]]: (u["render"].get("locator") or {}).get("element_id")
        for u in doc["uses"]
    }
    assert linked["<ref>two</ref>"] in (None, "cite_ref-3")
    assert linked["<ref>zero</ref>"] in (None, "cite_ref-1")
