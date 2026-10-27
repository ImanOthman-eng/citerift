"""Regression tests for the findings of the three Stage 02 review passes (TEST_RESULTS.md, review dispositions).

Each test names the finding it holds; every one failed, or could not run, before its fix."""

from __future__ import annotations

import base64
import hashlib
import http.server
import json
import os
import shutil
import sqlite3
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any, ClassVar

import pytest
import rde_support as S

from citerift.retraction import corroboration, schemas, tension
from citerift.retraction.cli import main
from citerift.retraction.corroboration import Limits, Response, UrllibTransport, enrich
from citerift.retraction.export import diff, verify
from citerift.retraction.identifiers import normalize_doi
from citerift.retraction.query import Index, QueryError, lookup
from citerift.retraction.source import ImportFailure
from citerift.retraction.store import build, manifest_path_for, open_index


def _retraction(record_id: str, **values: str) -> dict[str, str]:
    return S.row(**{"Record ID": record_id, "RetractionNature": "Retraction"} | values)


def _writable_copy(index: Path, tmp: Path) -> Path:
    copy = tmp / "tampered" / index.name
    copy.parent.mkdir(parents=True)
    shutil.copy(index, copy)
    return copy


# Architecture and data integrity ---------------------------------------------------------------------------


@pytest.mark.regression
def test_rde_a1_long_date_builds_and_verifies(tmp_path: Path) -> None:
    """A-1: a field problem never quarantines, and the published index passes its own verify."""
    idx = S.build_rows(tmp_path, [_retraction("1", OriginalPaperDOI="10.5555/o", RetractionDate="x" * 201)])
    with Index(idx) as ix:
        report = verify(ix.conn, manifest_path=manifest_path_for(idx))
    assert report["ok"], report["problems"]


@pytest.mark.regression
def test_rde_a1_build_refuses_to_publish_an_invalid_event(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [_retraction("1", OriginalPaperDOI="10.5555/o")]
    first = S.build_rows(tmp_path, rows)
    before = first.read_bytes()
    monkeypatch.setattr(schemas, "event_problems", lambda events: [f"EVENT_INVALID {events[0]['event_id']}: x"])
    source, receipt = S.write_source(tmp_path, S.csv_bytes(rows))
    with pytest.raises(ImportFailure) as exc:
        build(source, receipt, tmp_path / "index")
    assert exc.value.code == "ARTIFACT_INVALID"
    assert first.read_bytes() == before  # the earlier artifact is untouched
    assert sorted(p.name for p in first.parent.iterdir()) == sorted([first.name, manifest_path_for(first).name])


@pytest.mark.regression
def test_rde_a2_rebuild_never_replaces_another_build(tmp_path: Path) -> None:
    """A-2: a plain rebuild into the directory of a corroborated build would have deleted its Crossref evidence."""
    rows = [_retraction("1", OriginalPaperDOI="10.5555/o", RetractionDOI="10.5555/n")]
    entries = [{"original": "10.5555/o", "updated_by": [{"DOI": "10.5555/n", "type": "retraction", "source": "x"}]}]
    idx = S.build_rows(tmp_path, rows, entries)
    source, receipt = S.write_source(tmp_path, S.csv_bytes(rows))
    with pytest.raises(ImportFailure) as exc:
        build(source, receipt, tmp_path / "index")
    assert exc.value.code == "ARTIFACT_EXISTS"
    with Index(idx) as ix:
        assert ix.conn.execute("SELECT COUNT(*) FROM cr_assertion").fetchone()[0] == 1
    again = build(source, receipt, tmp_path / "plain")  # another directory works
    assert again.index_path != idx
    same = build(source, receipt, tmp_path / "plain")  # an equal build may replace itself
    assert same.manifest["digests"] == again.manifest["digests"]


@pytest.mark.regression
def test_rde_a2_verify_compares_the_manifest(tmp_path: Path) -> None:
    a = S.build_rows(tmp_path / "a", [_retraction("1", OriginalPaperDOI="10.5555/o")])
    b = S.build_rows(tmp_path / "b", [_retraction("1", OriginalPaperDOI="10.5555/p")])
    other = json.loads(manifest_path_for(b).read_text(encoding="utf-8"))
    manifest_path_for(a).write_text(json.dumps(other), encoding="utf-8")
    with Index(a) as ix:
        problems = verify(ix.conn, manifest_path=manifest_path_for(a))["problems"]
    assert any(p.startswith("MANIFEST_MISMATCH") for p in problems)
    manifest_path_for(a).unlink()
    assert main(["verify", "--index", str(a)]) == 5


@pytest.mark.regression
@pytest.mark.parametrize(
    "tamper",
    [
        "UPDATE ident SET raw = '10.5555/forged' WHERE id = 1",
        "DELETE FROM title_token WHERE rowid IN (SELECT rowid FROM title_token LIMIT 1)",
        "UPDATE notice SET n_events = 7",
        "UPDATE token_df SET df = df + 1",
    ],
    ids=["ident", "title_token", "notice", "token_df"],
)
def test_rde_a3_verify_recomputes_derived_tables(tmp_path: Path, tamper: str) -> None:
    """A-3: tables a lookup reads but no digest covered are recomputed from the raw records by verify."""
    rows = [_retraction("1", OriginalPaperDOI="10.5555/o", RetractionDOI="10.5555/n", Title="Alpha beta gamma")]
    copy = _writable_copy(S.build_rows(tmp_path, rows), tmp_path)
    conn = sqlite3.connect(copy)
    if "title_token" in tamper:
        tamper = "DELETE FROM title_token WHERE token = (SELECT MIN(token) FROM title_token)"
    conn.execute(tamper)
    conn.commit()
    conn.close()
    with Index(copy) as ix:
        report = verify(ix.conn)
    assert not report["ok"]
    assert any("INCONSISTENT" in p for p in report["problems"])


@pytest.mark.regression
def test_rde_a3_crossref_attempts_are_in_both_digests(tmp_path: Path) -> None:
    """A-3: an extra successful Crossref work with no relation changes checked sources, so it changes both
    digests."""
    rows = [_retraction("1", OriginalPaperDOI="10.5555/o")]
    one = S.build_rows(tmp_path / "one", rows, [{"original": "10.5555/o", "updated_by": []}])
    two = S.build_rows(
        tmp_path / "two",
        rows,
        [{"original": "10.5555/o", "updated_by": []}, {"original": "10.5555/q", "updated_by": []}],
    )
    with Index(one) as a, Index(two) as b:
        assert a.meta["artifact_digest"] != b.meta["artifact_digest"]
        assert a.meta["semantic_digest"] != b.meta["semantic_digest"]


@pytest.mark.regression
def test_rde_a6_retrieval_time_is_not_semantic(tmp_path: Path) -> None:
    rows = [_retraction("1", OriginalPaperDOI="10.5555/o", RetractionDOI="10.5555/n")]
    entries = [{"original": "10.5555/o", "updated_by": [{"DOI": "10.5555/n", "type": "retraction"}]}]
    digests = []
    for when in ("2026-01-02T00:00:00Z", "2026-02-03T00:00:00Z"):
        tmp = tmp_path / when[:10]
        source, receipt = S.write_source(tmp, S.csv_bytes(rows))
        bundle = S.crossref_bundle(tmp, entries, retrieved_at=when)
        digests.append(build(source, receipt, tmp / "index", corroboration=bundle).manifest["digests"])
    assert digests[0]["semantic_digest"] == digests[1]["semantic_digest"]
    assert digests[0]["artifact_digest"] != digests[1]["artifact_digest"]


@pytest.mark.regression
def test_rde_a5_diff_compares_semantic_content_and_header(tmp_path: Path) -> None:
    """A-5: the same records with the columns reordered are three new raw rows but no semantic change."""
    rows = [_retraction(str(i), OriginalPaperDOI=f"10.5555/o{i}") for i in range(3)]
    old = S.build_rows(tmp_path / "old", rows)
    header = list(rows[0])
    reordered = [header[-1], *header[:-1]]
    data = S.csv_bytes([[r[c] for c in reordered] for r in rows], header=reordered)
    source, receipt = S.write_source(tmp_path / "new", data)
    new = build(source, receipt, tmp_path / "new" / "index").index_path
    with Index(old) as a, Index(new) as b:
        out = diff(a.conn, b.conn)
    assert out["added_records"] == 3 and out["unchanged_records"] == 0
    assert out["semantic_lines"] == {"unchanged": 3, "added": 0, "absent_in_new": 0}
    assert out["header"]["equal"] is False and out["header"]["same_columns"] is True


@pytest.mark.regression
def test_rde_a7_notice_hits_are_capped_with_a_count(tmp_path: Path) -> None:
    rows = [_retraction(str(i), OriginalPaperDOI=f"10.5555/o{i}", RetractionDOI="10.5555/shared") for i in range(101)]
    out = lookup(S.build_rows(tmp_path, rows), "10.5555/shared")
    assert out["lookup_state"] == "notice_only"
    assert len(out["notice_hits"]) == 100 and out["notice_hit_count"] == 101
    assert out["total_event_count"] == 101
    assert not schemas.validate_lookup(out)


# Adversarial QA and security ----------------------------------------------------------------------------------


@pytest.mark.security
@pytest.mark.parametrize(
    ("row", "query"),
    [
        (
            {"Record ID": "1", "RetractionNature": "Retraction ", "OriginalPaperDOI": "https://doi.org/10.5555%2Fq1"},
            "10.5555/q1",
        ),
        ({"Record ID": "1", "RetractionNature": "Retraction", "OriginalPaperDOI": "10.5555/ab\u200bc"}, "10.5555/abc"),
        (
            {"Record ID": "1", "RetractionNature": "Retraction", "OriginalPaperDOI": "https://doi.org/10.5555/pe%2Fx%"},
            "10.5555/pe/x",
        ),
    ],
    ids=["quarantined-url-encoded", "zero-width-space", "bad-percent"],
)
def test_rde_s1_hidden_forms_are_coverage_gaps(tmp_path: Path, row: dict[str, str], query: str) -> None:
    """S-1: an encoded or hidden form of the queried key must not let the lookup say 'not found'."""
    out = lookup(S.build_rows(tmp_path, [S.row(**row)]), query)
    assert out["lookup_state"] == "no_record"
    status = out["projection"]["retraction_status"]
    assert (status["status"], status["value"]) == ("uncertain", None)
    assert "COVERAGE_GAP_RELEVANT_ROWS" in out["projection"]["basis"]["reasons"]


@pytest.mark.security
@pytest.mark.parametrize("name", ["real#x.sqlite", "decoy?mode=rwc&x=.sqlite", "x%2Esqlite", "w#y.sqlite"])
def test_rde_s2_index_path_cannot_redirect_or_unlock_the_open(tmp_path: Path, name: str) -> None:
    idx = S.build_rows(tmp_path, [_retraction("1", OriginalPaperDOI="10.5555/o")])
    target = tmp_path / "odd" / name
    target.parent.mkdir()
    shutil.copy(idx, target)
    before = sorted(p.name for p in target.parent.iterdir())
    conn = open_index(target)
    try:
        [(_, _, opened)] = [r for r in conn.execute("PRAGMA database_list") if r[1] == "main"]
        assert Path(opened).resolve() == target.resolve()
        conn.execute("PRAGMA query_only=OFF")
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("CREATE TABLE pwn (x)")
    finally:
        conn.close()
    assert sorted(p.name for p in target.parent.iterdir()) == before  # no file created


class _Handler(http.server.BaseHTTPRequestHandler):
    hits: ClassVar[list[str]] = []

    def log_message(self, *_args: Any) -> None:
        pass

    def do_GET(self) -> None:
        type(self).hits.append(self.path)
        if self.path.startswith("/works/redirect"):
            self.send_response(302)
            self.send_header("Location", "/elsewhere/not-works")
            self.end_headers()
        elif self.path.startswith("/works/drip"):
            self.send_response(200)
            self.send_header("Content-Length", "100")
            self.end_headers()
            for _ in range(20):
                self.wfile.write(b" ")
                self.wfile.flush()
                time.sleep(0.1)
        else:
            body = b'{"forged": true}'
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)


@pytest.fixture
def loopback(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """A loopback HTTP server standing in for the API host (no external network)."""
    _Handler.hits = []
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}/works/"
    monkeypatch.setattr(corroboration, "API_BASE", base)
    try:
        yield base
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.security
def test_rde_s3_redirects_are_refused(loopback: str) -> None:
    resp = UrllibTransport().get(loopback + "redirect", timeout=5, max_bytes=1024)
    assert resp.status == 302
    assert _Handler.hits == ["/works/redirect"]  # the redirect target was never requested


@pytest.mark.security
def test_rde_s8_request_deadline_covers_the_whole_response(loopback: str) -> None:
    started = time.monotonic()
    with pytest.raises(corroboration.TransportTimeout):
        UrllibTransport().get(loopback + "drip", timeout=0.5, max_bytes=1024)
    assert time.monotonic() - started < 1.5  # per-read timeouts alone would allow about 2 seconds


class _Clock:
    def __init__(self) -> None:
        self.t = 0.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.t += seconds


class _Once:
    def __init__(self, clock: _Clock, responses: list[Response]):
        self.clock, self.responses, self.calls = clock, responses, 0

    def get(self, url: str, timeout: float, max_bytes: int) -> Response:
        self.calls += 1
        self.clock.t += 0.1
        return self.responses.pop(0)


def _work(doi: str) -> bytes:
    message = {"DOI": doi, "type": "journal-article", "updated-by": []}
    return json.dumps({"status": "ok", "message-type": "work", "message": message}).encode()


@pytest.mark.negative
@pytest.mark.parametrize(
    ("first", "wait"),
    [
        (Response(503, {"retry-after": "7"}, b""), 7.0),
        (Response(429, {"retry-after": "Tue, 27 Oct 2026 00:00:05 GMT"}, b""), 5.0),
    ],
    ids=["503-seconds", "429-http-date"],
)
def test_rde_s5_retry_after_is_honoured(tmp_path: Path, first: Response, wait: float) -> None:
    import datetime as dt

    clock = _Clock()
    transport = _Once(clock, [first, Response(200, {}, _work("10.5555/a"))])
    manifest = enrich(
        ["10.5555/a"],
        tmp_path,
        transport=transport,
        clock=clock,
        sleep=clock.sleep,
        now=lambda: "2026-10-27T00:00:00Z",
        wall=lambda: dt.datetime(2026, 10, 27, tzinfo=dt.UTC),
    )
    assert manifest["works"][0]["outcome"] == "ok"
    assert max(clock.sleeps) >= wait


@pytest.mark.negative
def test_rde_s5_unreadable_retry_after_is_not_guessed(tmp_path: Path) -> None:
    clock = _Clock()
    transport = _Once(clock, [Response(429, {"retry-after": "soon"}, b"")])
    manifest = enrich(["10.5555/a"], tmp_path, transport=transport, clock=clock, sleep=clock.sleep)
    assert (manifest["works"][0]["outcome"], manifest["works"][0]["failure"]) == ("failed", "RATE_LIMITED")
    assert transport.calls == 1


def _bundle(tmp: Path) -> tuple[Path, dict[str, Any]]:
    rows = [_retraction("1", OriginalPaperDOI="10.5555/o", RetractionDOI="10.5555/n")]
    S.write_source(tmp, S.csv_bytes(rows))
    path = S.crossref_bundle(tmp, [{"original": "10.5555/o", "updated_by": []}])
    return path, json.loads(path.read_text(encoding="utf-8"))


def _rebuild(tmp: Path, path: Path) -> None:
    source = tmp / "source.csv"
    build(source, S.receipt_for(source.read_bytes()), tmp / "index", corroboration=path)


@pytest.mark.security
@pytest.mark.parametrize(
    "change",
    [
        {"url": "https://evil.example/fake"},
        {"retrieved_at": "not a time; DROP TABLE event;--"},
        {"http_status": 404},
        {"attempts": "many"},
        {"attempts": [1]},
        {"http_status": {}},
        {"payload_sha256": "Z" * 64},
    ],
    ids=["foreign-url", "bad-time", "ok-404", "attempts-text", "attempts-list", "status-object", "hash-not-hex"],
)
def test_rde_s4_replay_manifest_is_schema_checked(tmp_path: Path, change: dict[str, Any]) -> None:
    path, manifest = _bundle(tmp_path)
    manifest["works"][0].update(change)
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ImportFailure) as exc:
        _rebuild(tmp_path, path)
    assert exc.value.code == "CORROBORATION_INVALID"


@pytest.mark.security
def test_rde_s4_nan_and_float_dates_are_rejected(tmp_path: Path) -> None:
    path, manifest = _bundle(tmp_path)
    text = json.dumps(manifest).replace('"attempts": 1', '"attempts": NaN')
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ImportFailure) as exc:
        _rebuild(tmp_path, path)
    assert exc.value.code == "CORROBORATION_INVALID"
    payload = json.dumps(
        {
            "status": "ok",
            "message-type": "work",
            "message": {
                "DOI": "10.5555/o",
                "updated-by": [{"DOI": "10.5555/n", "type": "retraction", "updated": {"timestamp": 1.5}}],
            },
        }
    ).encode()
    with pytest.raises(corroboration.PayloadProblem) as problem:
        corroboration.check_payload(payload, "10.5555/o")
    assert problem.value.code == "SCHEMA_INVALID"


@pytest.mark.security
def test_rde_s7_payload_links_and_oversize_are_refused(tmp_path: Path) -> None:
    path, manifest = _bundle(tmp_path)
    payload = path.parent / "payloads" / f"{manifest['works'][0]['payload_sha256']}.json"
    outside = tmp_path / "outside.json"
    outside.write_bytes(payload.read_bytes())
    payload.unlink()
    os.symlink(outside, payload)
    with pytest.raises(ImportFailure) as exc:
        _rebuild(tmp_path, path)
    assert exc.value.code == "CORROBORATION_INVALID" and "regular file" in str(exc.value)
    payload.unlink()
    big = b" " * (Limits().max_bytes + 1)
    sha = hashlib.sha256(big).hexdigest()
    (path.parent / "payloads" / f"{sha}.json").write_bytes(big)
    manifest["works"][0].update(payload_sha256=sha, bytes=len(big))
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ImportFailure) as exc:
        _rebuild(tmp_path, path)
    assert exc.value.code == "CORROBORATION_INVALID" and "exceeds" in str(exc.value)


@pytest.mark.security
def test_rde_s9_deep_cursor_is_invalid_not_a_crash(tmp_path: Path) -> None:
    idx = S.build_rows(tmp_path, [_retraction("1", OriginalPaperDOI="10.5555/o")])
    deep = base64.urlsafe_b64encode(("[" * 100_000 + "]" * 100_000).encode()).decode().rstrip("=")
    with pytest.raises(QueryError) as exc:
        lookup(idx, "10.5555/o", cursor=deep)
    assert exc.value.code == "CURSOR_INVALID"
    assert main(["lookup", "--index", str(idx), "--doi", "10.5555/o", "--cursor", deep]) == 2


@pytest.mark.security
@pytest.mark.parametrize("edge", ["\x1f", "\x1e", "\x1c", "\x0b", "\x0c", "\x85"])
def test_rde_s6_controls_at_identifier_edges_are_rejected(edge: str) -> None:
    """S-6: str.strip() removed these as whitespace and the key became an exact match."""
    norm = normalize_doi(f"{edge}10.5555/abc{edge}")
    assert norm.normalized is None
    assert any("CONTROL" in issue or "WHITESPACE" in issue for issue in norm.issues)  # flagged, not trimmed
    assert normalize_doi(" \t10.5555/abc　").normalized == "10.5555/abc"  # real whitespace is still trimmed


# Scientific semantics ---------------------------------------------------------------------------------------


@pytest.mark.regression
def test_rde_c7_tension_marks_an_unresolved_base(tmp_path: Path) -> None:
    """Science finding 7: a report with no changed field is a control only when the base is resolved."""
    rows = [
        _retraction("1", OriginalPaperDOI="10.5555/a", OriginalPaperPubMedID="9"),
        _retraction("2", OriginalPaperDOI="10.5555/b", OriginalPaperPubMedID="9"),
    ]
    idx = S.build_rows(tmp_path, rows)
    with Index(idx) as ix:
        ambiguous = tension.report(ix.gather(pmid="9"), ix.snapshot_id)
        resolved = tension.report(ix.gather("10.5555/a"), ix.snapshot_id)
    assert ambiguous["lookup_state"] == "ambiguous_identity" and ambiguous["base_unresolved"] is True
    assert resolved["base_unresolved"] is False
    assert not schemas.validate_tension(ambiguous)
