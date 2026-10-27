# ruff: noqa: S101 - pytest assertions
"""Deterministic tests of the Stage 01 cross-wiki link lookup and its failure states (no network).

Run: uv run pytest docs/verification/stage-01/tests
"""

from __future__ import annotations

import importlib.util
import io
import json
import urllib.error
from pathlib import Path
from typing import Any

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.negative]

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "stage01_probe.py"
spec = importlib.util.spec_from_file_location("stage01_probe", SCRIPT)
assert spec and spec.loader
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

DOI = "10.1016/S0140-6736(97)11096-0"
CITING = "<ref>{{cite journal |title=Ileal |doi=" + DOI + "}}{{Retracted}}</ref>"


def ok(body: Any) -> dict[str, Any]:
    return {"url": "u", "status": 200, "retrieved_at": "t", "body": body}


def failed(status: Any) -> dict[str, Any]:
    return {"url": "u", "status": status, "retrieved_at": "t", "body": None}


def rev_page(title: str, content: str, revid: int = 7) -> dict[str, Any]:
    slot = {"main": {"content": content}}
    revs = [{"revid": revid, "parentid": 6, "timestamp": "2026-10-26T00:00:00Z", "sha1": "s", "slots": slot}]
    return ok({"query": {"pages": [{"pageid": 1, "title": title, "revisions": revs}]}})


class FakeClient:
    """Answers wq() calls from a table keyed by (host, prop, titles, continue-token)."""

    def __init__(self, table: dict[tuple[str, ...], dict[str, Any]]) -> None:
        self.table = table
        self.calls: list[dict[str, str]] = []

    def get(self, url: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        params = params or {}
        self.calls.append(params)
        host = url.split("/")[2].split(".", maxsplit=1)[0]
        key = (host, params.get("prop", ""), params.get("titles", ""), params.get("llcontinue", ""))
        return self.table[key]


def discovery(*titles: str) -> dict[str, Any]:
    obs = [{"title": t, "wiki": "en", "revid": 1, "sha1": "x", "marked": True, "confirmed": True} for t in titles]
    return {"results": [{"doi": DOI, "wiki": "en", "observations": obs}]}


def ll(*pages: dict[str, Any], cont: dict[str, str] | None = None, normalized: Any = None) -> dict[str, Any]:
    body: dict[str, Any] = {"query": {"pages": list(pages)}}
    if normalized:
        body["query"]["normalized"] = normalized
    if cont:
        body["continue"] = cont
    return ok(body)


def test_linked_article_that_cites_is_doi_cited() -> None:
    c = FakeClient(
        {
            ("en", "langlinks", "A", ""): ll({"title": "A", "langlinks": [{"lang": "ar", "title": "ب"}]}),
            ("ar", "revisions", "ب", ""): rev_page("ب", CITING),
        }
    )
    [row] = probe.crosswiki(c, discovery("A"), "en", "ar")
    assert row["link_status"] == "linked" and row["dst_title"] == "ب"
    assert row["dst_status"] == "doi_cited" and row["dst"]["marked"] is True


def test_linked_article_without_doi_is_doi_not_found() -> None:
    c = FakeClient(
        {
            ("en", "langlinks", "A", ""): ll({"title": "A", "langlinks": [{"lang": "ar", "title": "ب"}]}),
            ("ar", "revisions", "ب", ""): rev_page("ب", "نص بلا مراجع"),
        }
    )
    [row] = probe.crosswiki(c, discovery("A"), "en", "ar")
    assert row["dst_status"] == "doi_not_found" and row["dst"]["doi_present"] is False


def test_mention_only_is_not_a_citation() -> None:
    mention = "<ref>{{cite journal |title=Retraction. DOI: " + DOI + " |doi=10.1/other}}</ref>"
    c = FakeClient(
        {
            ("en", "langlinks", "A", ""): ll({"title": "A", "langlinks": [{"lang": "ar", "title": "ب"}]}),
            ("ar", "revisions", "ب", ""): rev_page("ب", mention),
        }
    )
    [row] = probe.crosswiki(c, discovery("A"), "en", "ar")
    assert row["dst_status"] == "doi_mention_only"


def test_complete_answer_without_link_is_no_link() -> None:
    c = FakeClient({("en", "langlinks", "A", ""): ll({"title": "A"})})
    [row] = probe.crosswiki(c, discovery("A"), "en", "ar")
    assert row["link_status"] == "no_link" and row["dst_title"] is None and "dst_status" not in row


@pytest.mark.parametrize("status", [429, 500, 503, "failed"])
def test_failed_langlinks_request_is_never_no_link(status: Any) -> None:
    c = FakeClient({("en", "langlinks", "A|B", ""): failed(status)})
    rows = probe.crosswiki(c, discovery("A", "B"), "en", "ar")
    assert [r["link_status"] for r in rows] == ["request_failed", "request_failed"]
    assert all(r["link_http_status"] == status and r["dst_title"] is None for r in rows)


@pytest.mark.parametrize("body", [None, {}, {"query": {}}, {"error": {"code": "x"}, "query": {"pages": []}}, "x"])
def test_malformed_langlinks_response(body: Any) -> None:
    c = FakeClient({("en", "langlinks", "A", ""): ok(body)})
    [row] = probe.crosswiki(c, discovery("A"), "en", "ar")
    assert row["link_status"] == "malformed_response"


def test_page_absent_from_answer_is_malformed_not_no_link() -> None:
    c = FakeClient({("en", "langlinks", "A|B", ""): ll({"title": "A"})})
    rows = {r["src"]["title"]: r["link_status"] for r in probe.crosswiki(c, discovery("A", "B"), "en", "ar")}
    assert rows == {"A": "no_link", "B": "malformed_response"}


def test_missing_source_page() -> None:
    c = FakeClient({("en", "langlinks", "A", ""): ll({"title": "A", "missing": True})})
    [row] = probe.crosswiki(c, discovery("A"), "en", "ar")
    assert row["link_status"] == "source_missing"


def test_continuation_is_followed() -> None:
    c = FakeClient(
        {
            ("en", "langlinks", "A|B", ""): ll({"title": "A"}, {"title": "B"}, cont={"llcontinue": "2|ar"}),
            ("en", "langlinks", "A|B", "2|ar"): ll(
                {"title": "A"}, {"title": "B", "langlinks": [{"lang": "ar", "title": "ب"}]}
            ),
            ("ar", "revisions", "ب", ""): rev_page("ب", CITING),
        }
    )
    rows = {r["src"]["title"]: r for r in probe.crosswiki(c, discovery("A", "B"), "en", "ar")}
    assert rows["A"]["link_status"] == "no_link"
    assert rows["B"]["link_status"] == "linked" and rows["B"]["dst_status"] == "doi_cited"


def test_failure_on_continuation_marks_whole_batch_failed() -> None:
    c = FakeClient(
        {
            ("en", "langlinks", "A|B", ""): ll({"title": "A"}, {"title": "B"}, cont={"llcontinue": "2|ar"}),
            ("en", "langlinks", "A|B", "2|ar"): failed(503),
        }
    )
    rows = probe.crosswiki(c, discovery("A", "B"), "en", "ar")
    assert {r["link_status"] for r in rows} == {"request_failed"}


def test_normalized_title_maps_back() -> None:
    c = FakeClient(
        {
            ("en", "langlinks", "a_b", ""): ll(
                {"title": "A b", "langlinks": [{"lang": "ar", "title": "ب"}]},
                normalized=[{"from": "a_b", "to": "A b"}],
            ),
            ("ar", "revisions", "ب", ""): rev_page("ب", CITING),
        }
    )
    [row] = probe.crosswiki(c, discovery("a_b"), "en", "ar")
    assert row["link_status"] == "linked" and row["dst_status"] == "doi_cited"


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (failed(429), "fetch_failed"),
        (failed(503), "fetch_failed"),
        (ok({"query": {"pages": [{"title": "ب", "missing": True}]}}), "article_missing"),
        (ok({"query": {"pages": [{"title": "ب"}]}}), "malformed_response"),
        (ok(None), "malformed_response"),
    ],
)
def test_linked_article_fetch_outcomes(response: dict[str, Any], expected: str) -> None:
    c = FakeClient(
        {
            ("en", "langlinks", "A", ""): ll({"title": "A", "langlinks": [{"lang": "ar", "title": "ب"}]}),
            ("ar", "revisions", "ب", ""): response,
        }
    )
    [row] = probe.crosswiki(c, discovery("A"), "en", "ar")
    assert row["link_status"] == "linked" and row["dst_status"] == expected
    assert "confirmed" not in row["dst"]


@pytest.mark.parametrize("text", ["#REDIRECT [[X]]", "#تحويل [[س]]", "  #redirect[[x]]"])
def test_redirect_target_is_not_read_as_absence(text: str) -> None:
    c = FakeClient(
        {
            ("en", "langlinks", "A", ""): ll({"title": "A", "langlinks": [{"lang": "ar", "title": "ب"}]}),
            ("ar", "revisions", "ب", ""): rev_page("ب", text),
        }
    )
    [row] = probe.crosswiki(c, discovery("A"), "en", "ar")
    assert row["dst_status"] == "redirect"


# ------------------------------------------------------------------ the HTTP client under 429 and 5xx


class FakeHTTP:
    """Stands in for urllib.request.urlopen: replays a list of (status, headers, body)."""

    def __init__(self, script: list[tuple[int, dict[str, str], bytes]]) -> None:
        self.script = list(script)
        self.calls = 0

    def __call__(self, req: Any, timeout: float) -> Any:
        self.calls += 1
        status, headers, body = self.script.pop(0)
        if status != 200:
            raise urllib.error.HTTPError(req.full_url, status, "x", headers, io.BytesIO(body))  # type: ignore[arg-type]

        class Resp(io.BytesIO):
            def __enter__(self) -> Resp:
                return self

            def __exit__(self, *a: object) -> None:
                return None

        r = Resp(body)
        r.status = status  # type: ignore[attr-defined]
        r.headers = headers  # type: ignore[attr-defined]
        return r


@pytest.fixture
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    slept: list[float] = []
    monkeypatch.setattr(probe.time, "sleep", slept.append)
    return slept


def test_client_honours_retry_after_then_succeeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_sleep: list[float]
) -> None:
    http = FakeHTTP([(429, {"Retry-After": "7"}, b""), (200, {}, json.dumps({"query": {"pages": []}}).encode())])
    monkeypatch.setattr(probe.urllib.request, "urlopen", http)
    res = probe.Client(tmp_path).get("https://en.wikipedia.org/w/api.php", {"a": "b"})
    assert res["status"] == 200 and http.calls == 2
    assert 8.0 in no_sleep  # Retry-After + 1 s
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_client_persistent_5xx_is_failed_and_not_cached(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_sleep: list[float]
) -> None:
    http = FakeHTTP([(503, {}, b"")] * probe.MAX_ATTEMPTS)
    monkeypatch.setattr(probe.urllib.request, "urlopen", http)
    client = probe.Client(tmp_path)
    res = client.get("https://en.wikipedia.org/w/api.php", {"a": "b"})
    assert res["status"] == "failed" and http.calls == probe.MAX_ATTEMPTS
    assert not list(tmp_path.glob("*.json"))


def test_end_to_end_429_exhaustion_gives_request_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_sleep: list[float]
) -> None:
    http = FakeHTTP([(429, {"Retry-After": "1"}, b"")] * probe.MAX_ATTEMPTS)
    monkeypatch.setattr(probe.urllib.request, "urlopen", http)
    [row] = probe.crosswiki(probe.Client(tmp_path), discovery("A"), "en", "ar")
    assert row["link_status"] == "request_failed" and row["link_http_status"] == "failed"
