"""The network path and capture identity checks, on SYNTHETIC answers from a scripted transport (no sockets).

Covers the frozen network policy (FROZEN_PROTOCOL.md section 11): fixed hosts, at most three attempts, Retry-After
honored and never shortened, the global deadline ending ``deferred`` with ``not_before``, 403 never retried, body
limits, the cross-process network gate, and every refusal of a source or render that is not the pinned revision.
"""

from __future__ import annotations

import gzip
import json
import os
import time
from pathlib import Path
from typing import Any

import pytest
from wiki_support import (
    HTML_TYPE,
    JSON_TYPE,
    PAGE,
    REVISION,
    ScriptedClock,
    api_answer,
    capture,
    parsoid,
    response,
    scripted,
)

from citerift.wiki.capture import CaptureRequest, capture_revision
from citerift.wiki.fetch import (
    Attempt,
    Fetcher,
    FetchPolicy,
    NetworkGate,
    TransportError,
    parse_retry_after,
    plan_next,
)

API = "https://en.wikipedia.org/w/api.php?action=query&format=json"
HTML_URL = f"https://en.wikipedia.org/w/rest.php/v1/revision/{REVISION}/html"
TEXT = "Plain SYNTHETIC text.<ref>{{cite journal |title=T |doi=10.1000/x}}</ref>\n"


def ok_json(data: Any = None) -> Any:
    return response(200, {"content-type": JSON_TYPE}, json.dumps(data or {"query": {}}).encode())


def limited(retry_after: str | None = None, status: int = 429) -> Any:
    headers = {"content-type": "text/html"}
    if retry_after is not None:
        headers["retry-after"] = retry_after
    return response(status, headers, b"slow down")


def fetch(answers: list[Any], *, policy: FetchPolicy | None = None, expect: str = "json", url: str = API) -> Any:
    transport, seen = scripted(answers)
    clock = ScriptedClock()
    answer = Fetcher(policy or FetchPolicy(), transport, clock).get(url, expect=expect)
    return answer, seen, clock


def att(code: str | None, ended: float, retryable: bool = True, retry_after: float | None = None) -> Attempt:
    return Attempt(API, 1, "t", ended, ended, 429, code, retryable, retry_after_s=retry_after)


# ------------------------------------------------------------------------------------------- retry plan


@pytest.mark.unit
def test_plan_honors_retry_after_and_never_shortens_it() -> None:
    policy = FetchPolicy()
    plan = plan_next(policy, [att("HTTP_RATE_LIMITED", 5.0, retry_after=40.0)], 0.0)
    assert (plan.action, plan.at_mono) == ("retry", 45.0)
    shorter = plan_next(policy, [att("HTTP_RATE_LIMITED", 5.0, retry_after=1.0)], 0.0)
    assert shorter.at_mono == 5.0 + policy.min_interval_s  # the minimum interval still holds


@pytest.mark.unit
def test_plan_backs_off_without_retry_after_and_stops_after_three_attempts() -> None:
    policy = FetchPolicy()
    first = plan_next(policy, [att("HTTP_UNAVAILABLE", 1.0)], 0.0)
    second = plan_next(policy, [att("HTTP_UNAVAILABLE", 1.0), att("HTTP_UNAVAILABLE", 20.0)], 0.0)
    assert first.at_mono == 11.0 and second.at_mono == 40.0
    three = [att("HTTP_UNAVAILABLE", float(t)) for t in (1, 20, 60)]
    assert plan_next(policy, three, 0.0).code == "ATTEMPTS_EXHAUSTED"


@pytest.mark.unit
def test_plan_defers_past_the_deadline_with_not_before() -> None:
    policy = FetchPolicy()
    plan = plan_next(policy, [att("HTTP_RATE_LIMITED", 100.0, retry_after=120.0)], 0.0)
    assert (plan.action, plan.code, plan.not_before_mono) == ("stop", "DEFERRED_RETRY_AFTER", 220.0)
    no_header = plan_next(FetchPolicy(backoff_s=200.0), [att("HTTP_UNAVAILABLE", 100.0)], 0.0)
    assert no_header.code == "DEADLINE_EXCEEDED"


@pytest.mark.unit
def test_plan_does_not_retry_a_final_answer() -> None:
    policy = FetchPolicy()
    assert plan_next(policy, [att("HTTP_FORBIDDEN", 1.0, retryable=False)], 0.0).code == "HTTP_FORBIDDEN"
    assert plan_next(policy, [att(None, 1.0)], 0.0).code is None


@pytest.mark.unit
@pytest.mark.parametrize(
    ("value", "seconds", "problem"),
    [
        ("40", 40.0, None),
        ("Wed, 28 Oct 2026 12:01:30 GMT", 90.0, None),
        ("Wed, 28 Oct 2026 11:00:00 GMT", 0.0, None),
        ("soon", None, "RETRY_AFTER_UNREADABLE"),
        ("-5", None, "RETRY_AFTER_UNREADABLE"),
        ("٤٠", None, "RETRY_AFTER_UNREADABLE"),
        (None, None, None),
    ],
)
def test_retry_after_seconds_and_http_dates(value: str | None, seconds: float | None, problem: str | None) -> None:
    assert parse_retry_after(value, ScriptedClock().now()) == (seconds, problem)


@pytest.mark.unit
def test_policy_rejects_invalid_limits() -> None:
    for bad in ({"max_attempts": 0}, {"min_interval_s": -1}, {"deadline_s": 0}, {"max_body_bytes": 0}):
        with pytest.raises(ValueError, match="invalid fetch policy"):
            FetchPolicy(**bad)


# --------------------------------------------------------------------------------------------- fetcher


@pytest.mark.integration
def test_rate_limited_then_answered_waits_the_retry_after() -> None:
    answer, seen, _ = fetch([limited("39"), ok_json()])
    assert answer.code is None and len(answer.attempts) == 2 and len(seen) == 2
    assert answer.attempts[0].code == "HTTP_RATE_LIMITED" and answer.attempts[0].retry_after_s == 39.0
    assert answer.attempts[1].started_mono - answer.attempts[0].ended_mono >= 39.0
    assert answer.failure_bodies  # the 429 body is kept as a failure artifact


@pytest.mark.negative
def test_long_retry_after_ends_deferred_without_another_request() -> None:
    answer, seen, _ = fetch([limited("600")])
    assert answer.code == "DEFERRED_RETRY_AFTER" and len(seen) == 1
    assert answer.not_before == "2026-10-28T12:10:00.000000Z"


@pytest.mark.negative
@pytest.mark.parametrize("status", [403, 404, 301, 302, 418])
def test_forbidden_missing_and_redirect_answers_are_never_retried(status: int) -> None:
    answer, seen, _ = fetch([limited(status=status)])
    expected = {403: "HTTP_FORBIDDEN", 404: "HTTP_NOT_FOUND"}.get(status, "HTTP_STATUS_UNEXPECTED")
    assert (answer.code, len(seen), answer.body) == (expected, 1, None)


@pytest.mark.negative
def test_server_errors_stop_after_three_attempts() -> None:
    answer, seen, _ = fetch([limited(status=503), limited(status=500), limited(status=502)])
    assert answer.code == "ATTEMPTS_EXHAUSTED" and len(seen) == 3
    assert [a.code for a in answer.attempts] == ["HTTP_UNAVAILABLE", "HTTP_SERVER_ERROR", "HTTP_UNAVAILABLE"]


@pytest.mark.negative
def test_timeouts_are_retried_and_connection_refusals_recorded() -> None:
    answer, _, _ = fetch(
        [TransportError("HTTP_TIMEOUT", "t"), TransportError("HTTP_CONNECTION_FAILED", "c"), ok_json()]
    )
    assert answer.code is None and [a.code for a in answer.attempts] == ["HTTP_TIMEOUT", "HTTP_CONNECTION_FAILED", None]


@pytest.mark.negative
def test_api_maxlag_is_retried_and_other_api_errors_are_final() -> None:
    lag = ok_json({"error": {"code": "maxlag", "info": "lagged"}})
    answer, seen, _ = fetch([lag, ok_json()])
    assert answer.code is None and answer.attempts[0].code == "API_MAXLAG" and len(seen) == 2
    bad = ok_json({"error": {"code": "badvalue", "info": "x"}})
    answer, seen, _ = fetch([bad])
    assert answer.code == "API_ERROR" and len(seen) == 1


@pytest.mark.negative
def test_wrong_content_type_and_non_json_bodies_are_refused() -> None:
    answer, _, _ = fetch([response(200, {"content-type": "text/html"}, b"{}")])
    assert answer.code == "RESPONSE_CONTENT_TYPE"
    answer, _, _ = fetch([response(200, {"content-type": "application/json"}, b"<html>")], expect="html")
    assert answer.code == "RESPONSE_CONTENT_TYPE"
    dup = response(200, {"content-type": JSON_TYPE}, b'{"query": {}, "query": {"pages": []}}')
    answer, _, _ = fetch([dup, dup, dup])
    assert answer.code == "ATTEMPTS_EXHAUSTED" and answer.attempts[0].code == "RESPONSE_NOT_JSON"


@pytest.mark.security
def test_body_limits_hold_on_the_wire_and_after_decompression() -> None:
    policy = FetchPolicy(max_wire_bytes=1000, max_body_bytes=1000)
    big = response(200, {"content-type": JSON_TYPE}, b"x" * 5000, chunks=5)
    assert fetch([big], policy=policy)[0].code == "RESPONSE_TOO_LARGE"
    bomb = gzip.compress(b"{" + b" " * 500_000 + b"}")
    assert len(bomb) < 1000  # a small wire size that expands 500-fold
    gz = response(200, {"content-type": JSON_TYPE, "content-encoding": "gzip"}, bomb)
    assert fetch([gz], policy=policy)[0].code == "RESPONSE_TOO_LARGE"


@pytest.mark.negative
def test_corrupt_truncated_and_unsupported_encodings_are_refused() -> None:
    corrupt = response(200, {"content-type": JSON_TYPE, "content-encoding": "gzip"}, b"\x1f\x8bnot gzip at all")
    assert fetch([corrupt])[0].attempts[0].code == "RESPONSE_DECOMPRESSION_FAILED"
    cut = gzip.compress(b'{"query": {}}')[:-6]
    truncated = response(200, {"content-type": JSON_TYPE, "content-encoding": "gzip"}, cut)
    answer = fetch([truncated, truncated, truncated])[0]  # an incomplete body is retried, then given up
    assert answer.code == "ATTEMPTS_EXHAUSTED" and answer.attempts[0].code == "RESPONSE_INCOMPLETE"
    brotli = response(200, {"content-type": JSON_TYPE, "content-encoding": "br"}, b"{}")
    assert fetch([brotli])[0].attempts[0].code == "RESPONSE_ENCODING_UNSUPPORTED"
    short = response(200, {"content-type": JSON_TYPE, "content-length": "999"}, b"{}")
    assert fetch([short, short, short])[0].attempts[0].code == "RESPONSE_INCOMPLETE"


@pytest.mark.security
@pytest.mark.parametrize(
    "url",
    [
        "http://en.wikipedia.org/w/api.php",
        "https://doi.org/10.1000/x",
        "https://en.wikipedia.org.example.invalid/w/api.php",
        "https://en.wikipedia.org:8443/w/api.php",
        "https://user:pw@en.wikipedia.org/w/api.php",
        "https://en.wikipedia.org/w/api.php#frag",
        "https://fr.wikipedia.org/w/api.php",
    ],
)
def test_only_the_two_fixed_https_hosts_are_ever_requested(url: str) -> None:
    answer, seen, _ = fetch([], url=url)
    assert answer.code == "HOST_NOT_ALLOWED" and seen == []


@pytest.mark.unit
def test_attempts_keep_the_minimum_interval_within_a_capture() -> None:
    transport, _ = scripted([ok_json(), ok_json()])
    clock = ScriptedClock()
    fetcher = Fetcher(FetchPolicy(), transport, clock)
    first = fetcher.get(API, expect="json")
    second = fetcher.get(API + "&x=1", expect="json")
    assert second.attempts[0].started_mono - first.attempts[0].ended_mono >= 10.0
    assert fetcher.requests == 2


# --------------------------------------------------------------------------------------------- the gate


@pytest.mark.security
def test_gate_keeps_one_request_in_flight_across_holders(tmp_path: Path) -> None:
    lock = tmp_path / "gate.lock"
    first, second = NetworkGate(lock), NetworkGate(lock)
    assert first.acquire(0.0, 1.0) is None
    try:
        started = time.monotonic()
        assert second.acquire(0.0, 0.5) == "NETWORK_GATE_BUSY"
        assert time.monotonic() - started < 2.0
    finally:
        first.release()
    assert second.acquire(0.0, 1.0) is None
    second.release()


@pytest.mark.security
def test_gate_enforces_the_interval_recorded_by_another_process(tmp_path: Path) -> None:
    lock = tmp_path / "gate.lock"
    lock.write_text(f"{time.time():.3f}\n", encoding="ascii")
    gate = NetworkGate(lock)
    started = time.monotonic()
    assert gate.acquire(0.6, 5.0) is None
    gate.release()
    assert time.monotonic() - started >= 0.5
    assert float(lock.read_text(encoding="ascii")) >= time.time() - 5
    assert NetworkGate(lock).acquire(30.0, 0.5) == "NETWORK_GATE_BUSY"  # cannot wait 30 s within 0.5 s


@pytest.mark.security
def test_gate_refuses_a_symlinked_lock_file(tmp_path: Path) -> None:
    target = tmp_path / "elsewhere"
    target.write_text("0\n", encoding="ascii")
    lock = tmp_path / "gate.lock"
    os.symlink(target, lock)
    assert NetworkGate(lock).acquire(0.0, 1.0) == "NETWORK_GATE_UNAVAILABLE"


@pytest.mark.security
def test_live_path_uses_the_gate_and_injected_transports_do_not(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.setenv("CITERIFT_WIKI_NETWORK_LOCK", str(tmp_path / "g.lock"))
    live = Fetcher(FetchPolicy())
    assert isinstance(live.gate, NetworkGate) and live.gate.path == tmp_path / "g.lock"
    transport, _ = scripted([])
    assert Fetcher(FetchPolicy(), transport).gate is None
    held = NetworkGate(tmp_path / "g.lock")
    assert held.acquire(0.0, 1.0) is None
    try:
        transport, seen = scripted([ok_json()])
        gated = Fetcher(FetchPolicy(deadline_s=1.0), transport, gate=NetworkGate(tmp_path / "g.lock"))
        answer = gated.get(API, expect="json")
        assert answer.code == "NETWORK_GATE_BUSY" and seen == []
    finally:
        held.release()


# ------------------------------------------------------------------------------------------- capture


def capture_answer(answer: dict[str, Any], tmp: Path, **kw: Any) -> Any:
    return capture(tmp / "b", TEXT, None, answer=answer, **kw)


@pytest.mark.negative
@pytest.mark.parametrize(
    ("change", "code"),
    [
        (lambda a: a["query"]["pages"][0].update(missing=True), "PAGE_MISSING"),
        (lambda a: a["query"]["pages"][0].update(ns=1), "NAMESPACE_UNSUPPORTED"),
        (
            lambda a: a["query"]["pages"][0]["revisions"][0]["slots"]["main"].update(contentmodel="json"),
            "CONTENT_MODEL_UNSUPPORTED",
        ),
        (lambda a: a["query"]["pages"][0]["revisions"][0].update(texthidden=True), "REVISION_TEXT_HIDDEN"),
        (
            lambda a: a["query"]["pages"][0]["revisions"][0]["slots"]["main"].update(texthidden=True),
            "REVISION_TEXT_HIDDEN",
        ),
        (lambda a: a["query"]["pages"][0]["revisions"][0].update(sha1="0" * 40), "SOURCE_HASH_MISMATCH"),
        (lambda a: a["query"]["pages"][0]["revisions"][0].update(size=1), "SOURCE_HASH_MISMATCH"),
        (lambda a: a["query"]["pages"][0]["revisions"][0].update(revid=REVISION + 1), "REVISION_ID_MISMATCH"),
        (lambda a: a["query"]["pages"][0]["revisions"][0].pop("slots"), "SLOT_MISSING"),
        (lambda a: a["query"].update(badrevids={str(REVISION): {}}), "REVISION_NOT_FOUND"),
        (lambda a: a["query"]["pages"].append(dict(a["query"]["pages"][0])), "API_ERROR"),
        (lambda a: a.pop("query"), "API_ERROR"),
    ],
)
def test_capture_refuses_anything_but_the_pinned_main_slot_wikitext(tmp_path: Path, change: Any, code: str) -> None:
    answer = api_answer(TEXT)
    change(answer)
    outcome = capture_answer(answer, tmp_path)
    assert outcome.status == "failed" and outcome.bundle is None
    assert code in [i.code for i in outcome.issues]
    assert not (tmp_path / "b").exists()


@pytest.mark.negative
def test_capture_refuses_a_different_page_id(tmp_path: Path) -> None:
    req = CaptureRequest("en", page_id=PAGE + 7, render=False)
    outcome = capture(tmp_path / "b", TEXT, None, request=req)
    assert outcome.status == "failed" and "PAGE_ID_MISMATCH" in [i.code for i in outcome.issues]


@pytest.mark.negative
@pytest.mark.parametrize(("wiki", "text"), [("en", "#REDIRECT [[Elsewhere]]"), ("ar", "#تحويل [[مكان آخر]]")])
def test_redirect_pages_are_not_followed_implicitly(tmp_path: Path, wiki: str, text: str) -> None:
    outcome = capture(tmp_path / "b", text, None, wiki=wiki, answer=api_answer(text))
    assert outcome.status == "failed" and "REDIRECT_NOT_FOLLOWED" in [i.code for i in outcome.issues]


@pytest.mark.negative
def test_two_redirect_hops_are_refused_even_when_following(tmp_path: Path) -> None:
    answer = api_answer(TEXT)
    answer["query"]["redirects"] = [{"from": "A", "to": "B"}, {"from": "B", "to": "C"}]
    req = CaptureRequest("en", title="A", follow_redirect=True, render=False)
    outcome = capture(tmp_path / "b", TEXT, None, answer=answer, request=req)
    assert "REDIRECT_LIMIT" in [i.code for i in outcome.issues] and outcome.bundle is None


@pytest.mark.security
@pytest.mark.parametrize(
    "req",
    [
        CaptureRequest("fr", title="Paris"),
        CaptureRequest("en", title="A|B"),
        CaptureRequest("en", title="../../etc/passwd{{x}}"),
        CaptureRequest("en", title="   "),
        CaptureRequest("en", title="x" * 300),
        CaptureRequest("en", page_id=0),
        CaptureRequest("en", page_id=True),  # type: ignore[arg-type]
        CaptureRequest("en", title="A", page_id=1),
        CaptureRequest("en", revision_id=5, follow_redirect=True),
    ],
)
def test_invalid_requests_make_no_request(tmp_path: Path, req: CaptureRequest) -> None:
    transport, seen = scripted([])
    outcome = capture_revision(req, FetchPolicy(), out=tmp_path / "b", transport=transport, clock=ScriptedClock())
    assert outcome.status == "failed" and seen == []
    assert {i.code for i in outcome.issues} <= {"REQUEST_INVALID", "WIKI_UNSUPPORTED"}


@pytest.mark.negative
def test_deferred_render_keeps_the_source_and_says_when_to_retry(tmp_path: Path) -> None:
    transport, seen = scripted([ok_json(api_answer(TEXT)), limited("900")])
    req = CaptureRequest("en", revision_id=REVISION)
    outcome = capture_revision(req, FetchPolicy(), out=tmp_path / "b", transport=transport, clock=ScriptedClock())
    assert outcome.status == "partial" and outcome.bundle is not None and len(seen) == 2
    render = outcome.record["render"]
    assert render["state"] == "failed" and render["code"] == "DEFERRED_RETRY_AFTER" and render["not_before"]


@pytest.mark.negative
def test_deferred_source_publishes_nothing(tmp_path: Path) -> None:
    transport, _ = scripted([limited("900")])
    req = CaptureRequest("en", revision_id=REVISION)
    outcome = capture_revision(req, FetchPolicy(), out=tmp_path / "b", transport=transport, clock=ScriptedClock())
    assert outcome.status == "deferred" and outcome.bundle is None and outcome.record["not_before"]
    assert not (tmp_path / "b").exists()


@pytest.mark.negative
@pytest.mark.parametrize(
    ("html", "headers", "code"),
    [
        (b"\xff\xfe not utf-8", {}, "RENDER_NOT_UTF8"),
        (
            None,
            {"content-type": 'text/html; profile="https://www.mediawiki.org/wiki/Specs/HTML/1.8.0"'},
            "RENDER_PROFILE_UNSUPPORTED",
        ),
        (None, {"content-revision-id": str(REVISION - 1)}, "RENDER_REVISION_MISMATCH"),
    ],
)
def test_render_that_is_not_the_pinned_revision_is_rejected(
    tmp_path: Path, html: bytes | None, headers: dict[str, str], code: str
) -> None:
    body = html if html is not None else parsoid("<p>x</p>", TEXT)
    if html is not None:
        outcome = capture_revision(
            CaptureRequest("en", revision_id=REVISION),
            FetchPolicy(),
            out=tmp_path / "b",
            transport=scripted([ok_json(api_answer(TEXT)), response(200, {"content-type": HTML_TYPE}, body)])[0],
            clock=ScriptedClock(),
        )
    else:
        outcome = capture(tmp_path / "b", TEXT, body, render_headers=headers)
    assert outcome.status == "partial" and code in [i.code for i in outcome.issues]
    assert outcome.record["render"]["state"] in ("rejected", "failed")


@pytest.mark.negative
def test_render_without_any_revision_statement_is_not_accepted(tmp_path: Path) -> None:
    html = b"<!DOCTYPE html><html><head><meta charset='utf-8'/></head><body><p>x</p></body></html>"
    transport, _ = scripted([ok_json(api_answer(TEXT)), response(200, {"content-type": HTML_TYPE}, html)])
    outcome = capture_revision(
        CaptureRequest("en", revision_id=REVISION),
        FetchPolicy(),
        out=tmp_path / "b",
        transport=transport,
        clock=ScriptedClock(),
    )
    assert "RENDER_REVISION_UNCHECKED" in [i.code for i in outcome.issues]
