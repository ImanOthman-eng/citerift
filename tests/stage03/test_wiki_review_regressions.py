"""Regression tests for the second review round (REVIEW_FINDINGS.md RF-08 to RF-30), on SYNTHETIC inputs.

Each test names its finding. The fail-first outputs (before and after the fix) are kept under
docs/verification/stage-03/review/failfirst/.
"""

from __future__ import annotations

import gzip
import http.server
import json
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from wiki_support import (
    JSON_TYPE,
    REVISION,
    ScriptedClock,
    api_answer,
    bundle,
    codes,
    doi_link,
    extract,
    note_li,
    ref_sup,
    references,
    response,
    scripted,
)

from citerift.wiki.canonical import StrictJSONError, loads_strict
from citerift.wiki.capture import CaptureRequest, capture_revision
from citerift.wiki.fetch import Fetcher, FetchPolicy, NetworkGate, TransportError, parse_retry_after, urllib_transport
from citerift.wiki.markers import fold_map
from citerift.wiki.verify import verify_bundle

ROOT = Path(__file__).resolve().parents[2]
TEXT = 'A.<ref name="a">Smith 2001. Some paper.</ref>\n'


def one_note(
    tmp: Path, inner: str, text: str = TEXT, wiki: str = "en", backlinks: list[str] | None = None, name: str = "b"
) -> Any:
    body = (
        "<p>A."
        + ref_sup(1, "cite_note-a-1", "cite_ref-a_1-0", name="a")
        + "</p>"
        + references([note_li("cite_note-a-1", backlinks or ["cite_ref-a_1-0"], inner)])
    )
    return extract(bundle(tmp, text, body, wiki=wiki, name=name))


def marker(doc: dict[str, Any], i: int = 0) -> tuple[str, list[tuple[str, str]]]:
    m = doc["markers"][i]
    return m["state"], [(e["kind"], e["matched"]) for e in m["evidence"]]


# ------------------------------------------------------------------------------------- marker observations


@pytest.mark.negative
@pytest.mark.parametrize(
    "before",
    [
        "<!-- note -->",
        '<link rel="mw:PageProp/Category" href="./Category:CS1_maint"/>',
        "<style>.x{}</style>",
        '<meta typeof="mw:Placeholder/StrippedTag"/>',
    ],
)
def test_wiki_text_after_a_skipped_node_is_inspected(tmp_path: Path, before: str) -> None:
    """RF-08 (P2-01): the text after a comment, <link>, <style> or <meta> was dropped and "no warning" followed."""
    assert marker(one_note(tmp_path, "Smith 2001. " + before + " Retracted.")) == (
        "recognized_warning_text",
        [("warning", "Retracted")],
    )


@pytest.mark.negative
def test_wiki_standalone_template_region_covers_its_whole_output(tmp_path: Path) -> None:
    """RF-09 (P2-02): CS1 output starts with an empty <link>; the region is every element of the template's output."""
    text = "Intro.\n\n==Further reading==\n{{cite journal |title=Paper |doi=10.1000/p}} (Retracted)\n"
    dm = json.dumps(
        {
            "parts": [
                {
                    "template": {
                        "target": {"wt": "cite journal "},
                        "params": {"title": {"wt": "Paper "}, "doi": {"wt": "10.1000/p"}},
                        "i": 0,
                    }
                }
            ]
        }
    )
    body = (
        '<p><link rel="mw-deduplicated-inline-style" href="mw-data:TemplateStyles:r1" about="#mwt5" '
        f"typeof=\"mw:Extension/templatestyles mw:Transclusion\" data-mw='{dm}'/>"
        '<cite about="#mwt5" class="citation journal cs1">"Paper". '
        + doi_link("10.1000/p")
        + '</cite><span about="#mwt5"> (Retracted)</span></p>'
    )
    doc = extract(bundle(tmp_path, text, body))
    (bib,) = [c for c in doc["containers"] if c["kind"] == "bibliography_entry"]
    (obs,) = [m for m in doc["markers"] if m["container_id"] == bib["id"]]
    assert obs["state"] == "recognized_warning_text"


@pytest.mark.negative
def test_wiki_an_empty_region_is_never_a_negative(tmp_path: Path) -> None:
    """RF-09: a region without any text was observed as "no warning"."""
    assert marker(one_note(tmp_path, ""))[0] == "not_inspected"


@pytest.mark.negative
def test_wiki_doubtful_or_limited_regions_are_never_negative(tmp_path: Path) -> None:
    """RF-10 (P2-05): a backlink mismatch or a parser-limit comment without an ``about`` gave a verified negative."""
    mismatch = one_note(tmp_path, "Smith 2001. Some paper.", backlinks=["cite_ref-OTHER-0"], name="a")
    assert "RENDER_BACKLINK_MISMATCH" in codes(mismatch) and marker(mismatch)[0] == "not_inspected"
    limited = one_note(
        tmp_path, "Smith 2001. <!-- WARNING: template omitted, post-expand include size too large -->", name="l"
    )
    assert marker(limited)[0] == "not_inspected"


@pytest.mark.negative
@pytest.mark.parametrize(
    ("inner", "state"),
    [
        ('Smith J. "RETRACTED: Paper title". J Foo.', "ambiguous_text"),  # title prefix outside <cite>
        ("Smith 2001. The study was not retracted.", "ambiguous_text"),  # negation
        ('Smith 2001.<span style="DISPLAY:NONE">Retracted</span>', "ambiguous_text"),  # case-insensitive CSS
        ('Smith 2001.<span style="display:\tnone">Retracted</span>', "ambiguous_text"),
        (
            'Smith 2001.<span style="display:none"><a href="./Template:Retracted?action=edit&amp;redlink=1" '
            'title="Template:Retracted" class="new">Template:Retracted</a></span>',
            "ambiguous_text",  # a hidden red link is not "missing template link only"
        ),
        ("Smith 2001. Re­tracted.", "recognized_warning_text"),  # soft hyphen inside the term
    ],
)
def test_wiki_english_marker_wording(tmp_path: Path, inner: str, state: str) -> None:
    """RF-12 (P2-07, P2-11) and the negation found while re-running the P2 cases."""
    assert marker(one_note(tmp_path, inner))[0] == state


@pytest.mark.negative
@pytest.mark.parametrize(
    ("inner", "state"),
    [
        ("تقرير البنك المركزي عن المسحوبات النقدية", "ambiguous_text"),  # "withdrawals": a different word
        ("بطاقة مسحوبة من التداول", "recognized_warning_text"),  # feminine ending
        ("ورقة (مصدر مسحوب)", "recognized_warning_text"),
        ("ورقة والمسحوب", "recognized_warning_text"),  # conjunction and article written joined
        ("ورقة مس‌حوب", "recognized_warning_text"),  # ZWNJ inside
        ("ورقة ﻣﺴﺤﻮﺏ", "recognized_warning_text"),  # presentation forms
        ("ورقة غير مسحوب", "ambiguous_text"),  # negation
    ],
)
def test_wiki_arabic_marker_wording(tmp_path: Path, inner: str, state: str) -> None:
    """RF-12 (P2-06, P2-11): Arabic attached letters, format characters and presentation forms."""
    text = 'أ.<ref name="a">سميث 2001.</ref>\n'
    assert marker(one_note(tmp_path, inner, text=text, wiki="ar"))[0] == state


@pytest.mark.unit
@pytest.mark.parametrize("text", ["Straße. Retracted", "İİİ İstanbul retracted here", "ﬁﬂ Retracted"])
def test_wiki_marker_evidence_quotes_the_original_text(text: str) -> None:
    """RF-12 (P2-08): case folding that expands characters shifted the quoted evidence."""
    folded, origin = fold_map(text)
    start = folded.index("retracted")
    assert text[origin[start] : origin[start + len("retracted") - 1] + 1].casefold() == "retracted"


# ------------------------------------------------------------------------------------------ reconciliation


@pytest.mark.negative
def test_wiki_content_pairing_never_skips_an_incompatible_true_partner(tmp_path: Path) -> None:
    """RF-11 (P2-03): the plain reference was attached to the Cite Q note that shares its DOI."""
    text = "A.<ref>Smith 2001. https://doi.org/10.1000/x</ref> B.<ref>{{Cite Q|Q42}}</ref>\n"
    bad = (
        '<sup about="#mwt1" class="mw-ref reference" id="cite_ref-1" typeof="mw:Extension/ref" data-mw="{bad json">'
        '<a href="./SYNTHETIC#cite_note-1">[1]</a></sup>'
    )
    body = (
        "<p>A."
        + bad
        + " B."
        + ref_sup(2, "cite_note-2", "cite_ref-2")
        + "</p>"
        + references(
            [
                note_li("cite_note-1", ["cite_ref-1"], "Smith 2001. " + doi_link("10.1000/x")),
                note_li("cite_note-2", ["cite_ref-2"], "<cite>Jones.</cite> " + doi_link("10.1000/x")),
            ]
        )
    )
    doc = extract(bundle(tmp_path, text, body))
    first = doc["containers"][0]
    assert first["render"].get("region_id") != "cite_note-2"
    assert doc["uses"][0]["render"]["state"] == "abstained"


@pytest.mark.negative
def test_wiki_template_output_pairing_by_count_must_not_contradict_content(tmp_path: Path) -> None:
    """RF-11 (P2-04): one hidden infobox ref and one Wikidata ref were paired by count alone."""
    text = "{{Infobox settlement |unused=<ref>Census 2010 https://census.example/x</ref>}} A.\n"
    dm = (
        '{"parts":[{"template":{"target":{"wt":"Infobox settlement"},"params":{"unused":'
        '{"wt":"<ref>Census 2010 https://census.example/x</ref>"}},"i":0}}]}'
    )
    body = (
        f'<table about="#mwt5" typeof="mw:Transclusion" data-mw=\'{dm}\'><tr><td>Pop. 5'
        + ref_sup(1, "cite_note-1", "cite_ref-1").replace('about="#mwt1"', 'about="#mwt5"')
        + "</td></tr></table><p>A.</p>"
        + references([note_li("cite_note-1", ["cite_ref-1"], "Wikidata: <cite>Study</cite> " + doi_link("10.1000/wd"))])
    )
    doc = extract(bundle(tmp_path, text, body))
    assert doc["uses"][0]["render"]["state"] == "abstained"
    assert doc["containers"][0]["render"]["state"] != "matched"


# ------------------------------------------------------------------------------------------- source side


@pytest.mark.unit
def test_wiki_footnote_templates_with_an_empty_name_stay_anonymous(tmp_path: Path) -> None:
    """RF-13 (P1-01): {{efn|name=|...}} twice became one conflicting container."""
    doc = extract(bundle(tmp_path, "A{{efn|name=|One doi:10.1000/a}} B{{efn|name=|Two doi:10.1000/b}}"))
    assert [(c["name"], c["binding_state"]) for c in doc["containers"]] == [(None, "anonymous"), (None, "anonymous")]
    assert "REF_DEFINITIONS_CONFLICT" not in codes(doc)


@pytest.mark.unit
def test_wiki_list_defined_footnote_templates_are_not_uses(tmp_path: Path) -> None:
    """RF-14 (P1-02, P1-11): a list-defined {{efn}} counted as a use; an empty list-defined ref vanished."""
    doc = extract(bundle(tmp_path, "A{{efn|name=n1}}\n{{notelist|refs={{efn|name=n1|One}}{{efn|name=unused|Two}}}}\n"))
    assert [len(c["use_ids"]) for c in doc["containers"]] == [1, 0]
    assert "LIST_DEFINED_UNUSED" in codes(doc)
    empty = extract(
        bundle(tmp_path, name="e", text='A<ref name="b" />\n<references>\n<ref name="b" />\n</references>\n')
    )
    assert "LIST_DEFINED_WITHOUT_CONTENT" in codes(empty)


@pytest.mark.unit
def test_wiki_ref_names_are_read_as_mediawiki_reads_attributes(tmp_path: Path) -> None:
    """RF-15 (P1-06): whitespace runs collapse before entities are decoded."""
    doc = extract(bundle(tmp_path, 'A<ref name="Smith  2001">x</ref> B<ref name="Smith\n2001" />'))
    assert [u["binding"] for u in doc["uses"]] == ["bound", "bound"]
    nbsp = extract(bundle(tmp_path, name="n", text='A<ref name="x&nbsp;">one</ref> B<ref name="x">two</ref>'))
    assert [c["binding_state"] for c in nbsp["containers"]] == ["single_definition", "single_definition"]


@pytest.mark.unit
def test_wiki_short_footnote_identity_follows_the_parameters(tmp_path: Path) -> None:
    """RF-16 (P1-07): "Smith J" and "SmithJ" merged; {{sfn}} and {{Sfn}} split."""
    doc = extract(bundle(tmp_path, "A{{sfn|Smith J|2001|p=5}} B{{sfn|SmithJ|2001|p=5}}"))
    assert len(doc["containers"]) == 2
    same = extract(
        bundle(tmp_path, name="s", text="A{{sfn|Smith|2001|p=5}} B{{Sfn|Smith|2001|p=5}} C{{sfn |Smith|2001|p=5}}")
    )
    assert [len(c["definitions"]) for c in same["containers"]] == [3]


@pytest.mark.unit
def test_wiki_overridden_url_and_id_parameters_are_unresolved(tmp_path: Path) -> None:
    """RF-17 (P1-05): the RF-01 rule now covers URL and id parameters too."""
    for i, text in enumerate(
        [
            "A<ref>{{cite journal|title=T|url=https://doi.org/10.1000/old|url=https://example.org/paper}}</ref>",
            "A<ref>{{cite journal|title=T|id={{doi|10.1000/old}}|id=none}}</ref>",
        ]
    ):
        doc = extract(bundle(tmp_path, text, name=f"b{i}"))
        assert [x["role"] for x in doc["identifiers"]] == ["unresolved"]
        assert "IDENTIFIER_PARAMETER_OVERRIDDEN" in codes(doc)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("text", "raw", "boundary"),
    [
        ("A<ref>'''10.1000/bold'''</ref>", "10.1000/bold", "ambiguous_markup_or_entity"),
        ("A<ref>doi:10.1000/xyz''.</ref>", "10.1000/xyz", "ambiguous_markup_or_entity"),
        (
            "A<ref>doi:10.1002/(SICI)1097-4636(199706)35:4&lt;401::AID-JBM1&gt;3.0.CO;2-P</ref>",
            "10.1002/(SICI)1097-4636(199706)35:4&lt;401::AID-JBM1&gt;3.0.CO;2-P",
            "delimited",
        ),
        ("أ<ref>دوي: 10.2000/xyz،</ref>", "10.2000/xyz،", "ambiguous_trailing_punctuation"),
        ("أ<ref>دوي: 10.2000/xyz؟</ref>", "10.2000/xyz؟", "ambiguous_trailing_punctuation"),
    ],
)
def test_wiki_free_text_doi_boundaries(tmp_path: Path, text: str, raw: str, boundary: str) -> None:
    """RF-18 (P1-09, P2-09): wiki quotes end a DOI, entities are text, Arabic punctuation is flagged."""
    doc = extract(bundle(tmp_path, text, wiki="ar" if text.startswith("أ") else "en"))
    (occ,) = doc["identifiers"]
    assert (occ["source"]["raw"], occ["boundary"]) == (raw, boundary)


@pytest.mark.unit
def test_wiki_link_text_is_never_a_reference_identifier(tmp_path: Path) -> None:
    """RF-19 (P1-10): identifiers in a wiki link's display text and in an external link's text are mentions."""
    doc = extract(
        bundle(tmp_path, "A<ref>[[Retraction of Smith 2001|doi:10.1000/wl]] [https://x.example doi:10.1000/e]</ref>")
    )
    assert [i["role"] for i in doc["identifiers"]] == ["textual_mention", "textual_mention"]


@pytest.mark.unit
def test_wiki_url_identifier_decoding(tmp_path: Path) -> None:
    """RF-20 (P1-12, P1-13): invalid percent encoding gives no key; trimming a URL is recorded."""
    doc = extract(bundle(tmp_path, "A<ref>https://pubs.acs.org/doi/10.1021/ab%zz</ref>"))
    (occ,) = doc["identifiers"]
    assert occ["decoding"] is None and occ["normalization"] is None
    assert "IDENTIFIER_DECODING_FAILED" in codes(doc)
    ws = extract(
        bundle(tmp_path, name="w", text="A<ref>{{cite journal|title=T|url= https://doi.org/10.1000/ws }}</ref>")
    )
    assert ws["identifiers"][0]["decoding"]["structural_steps"] == ["URL_OUTER_WHITESPACE_TRIMMED"]


@pytest.mark.unit
def test_wiki_bidi_marks_in_template_names_are_ignored(tmp_path: Path) -> None:
    """RF-21 (P2-10): MediaWiki strips LRM/RLM from titles; the template stayed unsupported."""
    doc = extract(bundle(tmp_path, "أ<ref>{{استشهاد بدورية محكمة" + chr(0x200F) + "|دوي=10.1000/x}}</ref>", wiki="ar"))
    assert [i["role"] for i in doc["identifiers"]] == ["primary_citation_field"]


@pytest.mark.contracts
def test_wiki_every_structural_step_validates(tmp_path: Path) -> None:
    """RF-22 (P1-03): a step the schema did not list made the whole bundle fail verification."""
    path = bundle(tmp_path, "A<ref>https://pubs.acs.org/doi/10.1021/xy.5/abstract</ref>")
    doc = extract(path)
    out = tmp_path / "x.json"
    out.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    assert verify_bundle(path, out)["verified"]


@pytest.mark.security
def test_wiki_verify_rejects_forged_roles_and_keys(tmp_path: Path) -> None:
    """RF-23 (P1-04): a re-digested record with a promoted marker DOI or a forged key verified."""
    from citerift.wiki.canonical import digest

    path = bundle(tmp_path, "A<ref>{{cite journal|title=T|doi=10.1000/c}} {{Retracted|doi=10.1000/rn}}</ref>")
    doc = extract(path)
    for n, change in enumerate(("role", "key")):
        forged = json.loads(json.dumps(doc))
        target = next(i for i in forged["identifiers"] if i["role"] == "marker_target")
        if change == "role":
            target["role"] = "primary_citation_field"
            forged["accounting"]["identifiers_by_role"] = {"primary_citation_field": 2}
        else:
            target["normalization"]["normalized"] = "10.9999/forged"
        forged["extraction_digest"] = digest({k: v for k, v in forged.items() if k != "extraction_digest"})
        out = tmp_path / f"f{n}.json"
        out.write_text(json.dumps(forged, ensure_ascii=False), encoding="utf-8")
        report = verify_bundle(path, out)
        assert not report["verified"], change


# ------------------------------------------------------------------------------------- capture and network


@pytest.mark.negative
@pytest.mark.parametrize(
    ("value", "seconds", "problem"),
    [
        ("Wed Oct 28 12:05:00 2026", 300.0, None),  # asctime: UTC
        ("Wed, 28 Oct 2026 12:05:00 -0000", 300.0, None),
        ("100000000000000", None, "RETRY_AFTER_OUT_OF_RANGE"),
        ("1" * 5000, None, "RETRY_AFTER_OUT_OF_RANGE"),
    ],
)
def test_wiki_retry_after_dates_and_ranges(value: str, seconds: float | None, problem: str | None) -> None:
    """RF-24 (P3-04, P3-05): asctime dates were unreadable; huge values crashed the capture."""
    assert parse_retry_after(value, datetime(2026, 10, 28, 12, 0, tzinfo=UTC)) == (seconds, problem)


@pytest.mark.negative
def test_wiki_an_unusable_retry_after_is_never_replaced_by_a_shorter_backoff() -> None:
    """RF-24: with Retry-After present but unusable, the client stops instead of retrying on its own backoff."""
    transport, seen = scripted([response(429, {"retry-after": "99999999999999"}, b"")])
    answer = Fetcher(FetchPolicy(), transport, ScriptedClock()).get("https://en.wikipedia.org/w/api.php", expect="json")
    assert answer.code == "HTTP_RATE_LIMITED" and len(seen) == 1


@pytest.mark.negative
def test_wiki_retry_after_on_the_last_attempt_is_recorded_and_shared(tmp_path: Path) -> None:
    """RF-25 (P3-03): the last attempt's Retry-After was dropped and not passed to the next process."""
    transport, _ = scripted([response(429, {"retry-after": "30"}, b"")] * 3)
    answer = Fetcher(FetchPolicy(), transport, ScriptedClock()).get("https://en.wikipedia.org/w/api.php", expect="json")
    assert answer.code == "ATTEMPTS_EXHAUSTED" and answer.not_before is not None
    lock = tmp_path / "gate.lock"
    gate = NetworkGate(lock)
    assert gate.acquire(0.0, 5.0) is None
    gate.release(retry_after_s=120.0)
    other = NetworkGate(lock)
    assert other.acquire(0.1, 2.0) == "DEFERRED_RETRY_AFTER" and other.deferred_until is not None
    assert other.deferred_until >= time.time() + 100


@pytest.mark.security
@pytest.mark.parametrize("text", [b'{"x": 1e400}', b'{"x": -1E999}', b'{"x": "\\ud800"}'])
def test_wiki_strict_json_refuses_overflow_and_lone_surrogates(text: bytes) -> None:
    """RF-26 (P3-06, P3-07): 1e400 became infinity; a lone surrogate crashed verify and replay."""
    with pytest.raises(StrictJSONError):
        loads_strict(text)


@pytest.mark.security
def test_wiki_data_after_a_gzip_stream_is_refused() -> None:
    """RF-27 (P3-08): bytes after the gzip member were ignored."""
    body = gzip.compress(json.dumps(api_answer("T")).encode()) + b"GARBAGE"
    transport, _ = scripted([response(200, {"content-type": JSON_TYPE, "content-encoding": "gzip"}, body)])
    answer = Fetcher(FetchPolicy(), transport, ScriptedClock()).get("https://en.wikipedia.org/w/api.php", expect="json")
    assert answer.code == "RESPONSE_DECOMPRESSION_FAILED"


@pytest.mark.security
def test_wiki_a_drip_fed_body_cannot_outlast_the_operation_deadline() -> None:
    """RF-28 (P3-01): read(65536) waited for 64 KiB, so one byte at a time held the connection for days."""

    class Drip(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.end_headers()
            try:
                for _ in range(40):
                    self.wfile.write(b" ")
                    self.wfile.flush()
                    time.sleep(0.25)
            except OSError:
                pass

        def log_message(self, *args: Any) -> None:
            return None

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Drip)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        raw = urllib_transport(f"http://127.0.0.1:{server.server_address[1]}/", {}, 1.5)
        started = time.monotonic()
        with pytest.raises(TransportError) as err:
            for _ in raw.chunks:
                pass
        raw.close()
        assert err.value.code == "HTTP_TIMEOUT" and time.monotonic() - started < 4.0
    finally:
        server.shutdown()


@pytest.mark.negative
def test_wiki_capture_refuses_an_unusable_output_before_any_request(tmp_path: Path) -> None:
    """RF-29 (P3-11): two requests and a 10 s wait were spent before the existing --out was refused."""
    (tmp_path / "taken").mkdir()
    transport, seen = scripted([])
    outcome = capture_revision(
        CaptureRequest("en", revision_id=REVISION), FetchPolicy(), out=tmp_path / "taken", transport=transport
    )
    assert outcome.status == "failed" and seen == []
    assert [i.code for i in outcome.issues] == ["BUNDLE_PATH_UNSAFE"]


@pytest.mark.security
def test_wiki_worker_blocks_the_c_level_socket_type() -> None:
    """RF-30 (P3-10): _socket.socket.connect still connected after forbid_network()."""
    code = (
        "import _socket, socket\n"
        "from citerift.wiki.worker import forbid_network\n"
        "a, b = socket.socketpair(); forbid_network()\n"
        "s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)\n"
        "try:\n    s.connect(('127.0.0.1', 9))\nexcept PermissionError:\n    print('blocked')\n"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True, timeout=60)
    assert out.stdout.strip() == "blocked"


@pytest.mark.negative
def test_wiki_html_cut_by_the_parser_depth_limit_is_not_read_as_the_render(tmp_path: Path) -> None:
    """RF-31 (P3-02): libxml2 dropped everything after 256 levels and the render was still "complete"."""
    text = 'A.<ref name="a">{{cite journal|title=T|doi=10.1000/p}}</ref>\n'
    deep = "<div>" * 300 + "x" + "</div>" * 300
    body = (
        "<p>A."
        + ref_sup(1, "cite_note-a-1", "cite_ref-a_1-0", name="a")
        + "</p>"
        + deep
        + references([note_li("cite_note-a-1", ["cite_ref-a_1-0"], doi_link("10.1000/p"))])
    )
    doc = extract(bundle(tmp_path, text, body))
    assert doc["components"]["render"]["state"] == "failed"
    assert {m["state"] for m in doc["markers"]} == {"unavailable"}


@pytest.mark.security
def test_wiki_verify_refuses_render_attempts_without_a_render_request(tmp_path: Path) -> None:
    """RF-32 (P3-13): a capture whose render was edited to "not requested" still verified."""
    path = bundle(tmp_path, TEXT, "<p>A.</p>")
    cap = json.loads((path / "capture.json").read_text(encoding="utf-8"))
    cap["render"] = {"state": "not_requested"}
    cap["request"]["render"] = False
    cap["status"] = "complete"
    (path / "capture.json").write_text(json.dumps(cap, ensure_ascii=False, indent=1), encoding="utf-8")
    assert not verify_bundle(path)["verified"]


# ------------------------------------------------------------------- repair round after holdout run 1


@pytest.mark.negative
@pytest.mark.parametrize(
    ("wiki", "text"),
    [
        ("en", "Text.\n==External links==\nhttp://www.ncbi.nlm.nih.gov/pubmed/9380475\n"),
        ("en", "Text.{{Update inline|reason=see https://www.ncbi.nlm.nih.gov/pubmed/34699062}}\n"),
        ("en", "See {{doi|10.1000/prose}} for details.\n"),
        ("ar", "نص.\n== وصلات خارجية ==\nhttp://www.ncbi.nlm.nih.gov/pubmed/9380475\n"),
    ],
)
def test_wiki_identifier_links_outside_references_are_mentions(tmp_path: Path, wiki: str, text: str) -> None:
    """RF-36: a resolver or PubMed link outside any reference was given identifier_link, a cited-work role."""
    doc = extract(bundle(tmp_path, text, wiki=wiki))
    assert [i["role"] for i in doc["identifiers"]] == ["textual_mention"]
    inside = extract(bundle(tmp_path, "A<ref>https://doi.org/10.1000/inref</ref>\n", wiki=wiki, name="in"))
    assert [i["role"] for i in inside["identifiers"]] == ["identifier_link"]


@pytest.mark.unit
@pytest.mark.parametrize(
    ("wiki", "text"),
    [
        (
            "en",
            "A<ref>{{cite iucn |author=Ellis |year=2017 |title=X |doi=10.2305/IUCN.UK.2017-3.RLTS.T1A2.en}}</ref>\n",
        ),
        ("ar", "أ<ref>{{استشهاد بقاعدة بيانات غير مدرجة |عنوان=س |دوي=10.2305/IUCN.UK.2017-3.RLTS.T1A2.en}}</ref>\n"),
    ],
)
def test_wiki_unlisted_cite_templates_are_citation_templates(tmp_path: Path, wiki: str, text: str) -> None:
    """RF-37: "Cite …" / "استشهاد ب…" templates missing from profile v1 were unstructured, their DOI unresolved."""
    doc = extract(bundle(tmp_path, text, wiki=wiki))
    assert [u["kind"] for u in doc["units"]] == ["citation_template"]
    assert [i["role"] for i in doc["identifiers"]] == ["primary_citation_field"]
    assert doc["units"][0]["template"]["family"] == "unlisted"
    # The rule is the name prefix "Cite " (with the space), so maintenance templates such as {{Citation needed}}
    # are not citation templates.
    tag = extract(bundle(tmp_path, "A claim.{{Citation needed|date=May 2020}}\n", wiki=wiki, name="cn"))
    assert tag["units"] == []
