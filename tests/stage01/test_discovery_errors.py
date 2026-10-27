"""Deterministic tests of discovery under MediaWiki error bodies (no network).

MediaWiki reports some overload conditions (cirrussearch-too-busy-error, maxlag) as HTTP 200 with an error body.
In the first run of 2026-10-26, 7 Arabic M2 searches of sample S received such a body and were recorded as complete
searches with no hits (data/run-logs/sample_S_search_errors_first_run.json). These tests fix the intended behaviour:
an error body is never an answer, never "no hits", and never cached.

Run: uv run pytest tests/stage01 (CI runs them with the whole suite)
"""

from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
from typing import Any

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.negative]

SCRIPT = Path(__file__).resolve().parents[2] / "docs" / "verification" / "stage-01" / "scripts" / "stage01_probe.py"
spec = importlib.util.spec_from_file_location("stage01_probe_errors", SCRIPT)
assert spec and spec.loader
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

DOI = "10.1016/j.biopha.2021.111349"
BUSY = {"error": {"code": "cirrussearch-too-busy-error", "info": "Search is currently too busy."}}


def ok(body: Any) -> dict[str, Any]:
    return {"url": "u", "status": 200, "retrieved_at": "t", "body": body}


def search(total: int, titles: list[str], offset: int | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"query": {"searchinfo": {"totalhits": total}, "search": [{"title": t} for t in titles]}}
    if offset is not None:
        body["continue"] = {"sroffset": offset, "continue": "-||"}
    return ok(body)


def ext(titles: list[str], cont: str | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"query": {"exturlusage": [{"title": t} for t in titles]}}
    if cont is not None:
        body["continue"] = {"euoffset": cont, "continue": "-||"}
    return ok(body)


class FakeClient:
    """Answers wq() calls from a table keyed by (list, sroffset or euquery, euoffset)."""

    def __init__(self, table: dict[tuple[str, str, str], dict[str, Any]], default: dict[str, Any] | None = None):
        self.table = table
        self.default = default
        self.calls: list[dict[str, str]] = []

    def get(self, url: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        params = params or {}
        self.calls.append(params)
        if params.get("list") == "search":
            key = ("search", params["sroffset"], "")
        elif params.get("list") == "exturlusage":
            key = ("exturlusage", params["euquery"], params.get("euoffset", ""))
        else:
            key = ("other", "", "")
        if key in self.table:
            return self.table[key]
        assert self.default is not None, key
        return self.default


# ------------------------------------------------------------------ M2 (CirrusSearch)


def test_m2_error_body_is_not_a_complete_search() -> None:
    res = probe.m2_search(FakeClient({("search", "0", ""): ok(BUSY)}), "ar", DOI)
    assert res["ok"] is False and res["titles"] == []
    assert res["calls"][0]["api_error"] == "cirrussearch-too-busy-error" and res["calls"][0]["totalhits"] is None


def test_m2_zero_hits_with_stated_total_is_complete() -> None:
    res = probe.m2_search(FakeClient({("search", "0", ""): search(0, [])}), "ar", DOI)
    assert res["ok"] is True and res["titles"] == [] and res["calls"][0]["totalhits"] == 0


@pytest.mark.parametrize(
    "response",
    [
        ok({"query": {"search": []}}),  # no searchinfo: total unknown
        ok({"batchcomplete": True}),  # no query section
        ok(None),  # body was not JSON
        ok([]),  # JSON, but not an object
        {"url": "u", "status": "failed", "retrieved_at": "t", "body": None},
        {"url": "u", "status": 503, "retrieved_at": "t", "body": None},
    ],
)
def test_m2_unusable_answers_are_incomplete(response: dict[str, Any]) -> None:
    assert probe.m2_search(FakeClient({("search", "0", ""): response}), "en", DOI)["ok"] is False


def test_m2_continuation_is_followed_and_error_on_second_page_is_incomplete() -> None:
    table = {("search", "0", ""): search(51, ["A"], offset=50), ("search", "50", ""): search(51, ["B"])}
    res = probe.m2_search(FakeClient(table), "en", DOI)
    assert res["ok"] is True and res["titles"] == ["A", "B"] and len(res["calls"]) == 2
    table[("search", "50", "")] = ok(BUSY)
    res = probe.m2_search(FakeClient(table), "en", DOI)
    assert res["ok"] is False and res["titles"] == ["A"]


def test_discover_with_error_body_is_not_complete() -> None:
    res = probe.discover(FakeClient({("search", "0", ""): ok(BUSY)}), "ar", DOI, ("m2",))
    assert res["complete"] is False and res["observations"] == []


# ------------------------------------------------------------------ M1 (exturlusage)


def test_m1_error_body_is_incomplete() -> None:
    res = probe.m1_exturlusage(FakeClient({}, default=ok({"error": {"code": "maxlag"}})), "en", DOI)
    assert res["ok"] is False and res["titles"] == []
    assert {c["api_error"] for c in res["calls"]} == {"maxlag"}


def test_m1_continuation_is_followed() -> None:
    form = probe.m1_forms(DOI)[0]
    table = {("exturlusage", form, ""): ext(["A"], cont="500"), ("exturlusage", form, "500"): ext(["B"])}
    res = probe.m1_exturlusage(FakeClient(table, default=ext([])), "en", DOI)
    assert res["ok"] is True and res["titles"] == ["A", "B"]
    assert len(res["calls"]) == len(probe.m1_forms(DOI)) + 1


# ------------------------------------------------------------------ the HTTP client and the cache


class FakeHTTP:
    """Stands in for urllib.request.urlopen: replays a list of HTTP 200 bodies (JSON-encoded unless bytes)."""

    def __init__(self, bodies: list[Any]) -> None:
        self.bodies = list(bodies)
        self.calls = 0

    def __call__(self, req: Any, timeout: float) -> Any:
        self.calls += 1

        class Resp(io.BytesIO):
            def __enter__(self) -> Resp:
                return self

            def __exit__(self, *a: object) -> None:
                return None

        body = self.bodies.pop(0)
        r = Resp(body if isinstance(body, bytes) else json.dumps(body).encode())
        r.status = 200  # type: ignore[attr-defined]
        r.headers = {}  # type: ignore[attr-defined]
        return r


@pytest.fixture
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    slept: list[float] = []
    monkeypatch.setattr(probe.time, "sleep", slept.append)
    return slept


URL = "https://ar.wikipedia.org/w/api.php"
GOOD = {"query": {"searchinfo": {"totalhits": 0}, "search": []}}


def test_client_retries_transient_error_body(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_sleep: list[float]):
    http = FakeHTTP([BUSY, BUSY, GOOD])
    monkeypatch.setattr(probe.urllib.request, "urlopen", http)
    res = probe.Client(tmp_path).get(URL, {"q": "1"})
    assert http.calls == 3 and res["status"] == 200 and res["body"] == GOOD
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_client_records_api_error_of_each_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_sleep: list[float]
) -> None:
    monkeypatch.setattr(probe.urllib.request, "urlopen", FakeHTTP([BUSY, GOOD]))
    res = probe.Client(tmp_path).get(URL, {"q": "1"})
    assert [a.get("api_error") for a in res["attempts"]] == ["cirrussearch-too-busy-error", None]


def test_client_non_json_answer_is_not_cached(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_sleep: list[float]):
    http = FakeHTTP([b"<html>maintenance</html>", GOOD])
    monkeypatch.setattr(probe.urllib.request, "urlopen", http)
    client = probe.Client(tmp_path)
    first = client.get(URL, {"q": "1"})
    assert first["status"] == 200 and first["body"] is None and not probe.api_ok(first)
    assert not list(tmp_path.glob("*.json"))
    assert client.get(URL, {"q": "1"})["body"] == GOOD and http.calls == 2


def test_client_persistent_error_body_is_failed_and_not_cached(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_sleep: list[float]
) -> None:
    http = FakeHTTP([BUSY] * probe.MAX_ATTEMPTS)
    monkeypatch.setattr(probe.urllib.request, "urlopen", http)
    res = probe.Client(tmp_path).get(URL, {"q": "1"})
    assert http.calls == probe.MAX_ATTEMPTS and res["status"] == "failed"
    assert not list(tmp_path.glob("*.json"))


def test_client_non_transient_error_is_returned_once_and_not_cached(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_sleep: list[float]
) -> None:
    bad = {"error": {"code": "badvalue"}}
    http = FakeHTTP([bad])
    monkeypatch.setattr(probe.urllib.request, "urlopen", http)
    res = probe.Client(tmp_path).get(URL, {"q": "1"})
    assert http.calls == 1 and res["status"] == 200 and probe.api_error(res["body"]) == "badvalue"
    assert not probe.api_ok(res)
    assert not list(tmp_path.glob("*.json"))


def test_cached_error_body_is_refetched(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_sleep: list[float]):
    """A cache written by the first run (before the fix) may hold an error body; it must not be served."""
    client = probe.Client(tmp_path)
    full = URL + "?q=1"
    key = tmp_path / (probe.hashlib.sha256(full.encode()).hexdigest() + ".json")
    key.write_text(json.dumps({"url": full, "status": 200, "retrieved_at": "2026-10-26T19:04:00Z", "body": BUSY}))
    http = FakeHTTP([GOOD])
    monkeypatch.setattr(probe.urllib.request, "urlopen", http)
    res = client.get(URL, {"q": "1"})
    assert http.calls == 1 and res["body"] == GOOD
    assert json.loads(key.read_text())["body"] == GOOD


def test_cached_good_answer_is_served_without_network(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    full = URL + "?q=1"
    key = tmp_path / (probe.hashlib.sha256(full.encode()).hexdigest() + ".json")
    key.write_text(json.dumps({"url": full, "status": 200, "retrieved_at": "t", "body": GOOD}))
    http = FakeHTTP([])
    monkeypatch.setattr(probe.urllib.request, "urlopen", http)
    assert probe.Client(tmp_path).get(URL, {"q": "1"})["body"] == GOOD and http.calls == 0
