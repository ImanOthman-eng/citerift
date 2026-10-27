"""Bounded Crossref corroboration with transport doubles, and replay (SPECIFICATION.md 9;
directive section 14 items 7 and 16). No test opens a socket."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import rde_support as S

from citerift.retraction import tension
from citerift.retraction.corroboration import (
    Limits,
    Response,
    TransportConnectionError,
    TransportTimeout,
    UrllibTransport,
    enrich,
    load_manifest,
    work_url,
)
from citerift.retraction.query import Index, lookup
from citerift.retraction.source import ImportFailure
from citerift.retraction.store import build


class Clock:
    def __init__(self) -> None:
        self.t = 0.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.t += seconds


Step = Response | Exception | Callable[[], Response]


class Script:
    """A transport double: a list of responses per URL, consumed in order; each call takes ``cost`` seconds."""

    def __init__(self, clock: Clock, steps: dict[str, list[Step]], cost: float = 0.2):
        self.clock = clock
        self.steps = {k: list(v) for k, v in steps.items()}
        self.calls: list[str] = []
        self.cost = cost

    def get(self, url: str, timeout: float, max_bytes: int) -> Response:
        self.calls.append(url)
        self.clock.t += self.cost
        step = self.steps[url].pop(0)
        if isinstance(step, Exception):
            raise step
        return step() if callable(step) else step


def work(doi: str, updated_by: list[dict[str, Any]] | None = None, **message: Any) -> bytes:
    payload = {
        "status": "ok",
        "message-type": "work",
        "message-version": "1.0.0",
        "message": {"DOI": doi, "type": "journal-article", "updated-by": updated_by or [], **message},
    }
    return json.dumps(payload).encode("utf-8")


def ok(body: bytes, **headers: str) -> Response:
    return Response(200, {k.replace("_", "-"): v for k, v in headers.items()}, body)


def run(
    tmp: Path, steps: dict[str, list[Step]], dois: list[str], **limits: Any
) -> tuple[dict[str, Any], Script, Clock]:
    clock = Clock()
    transport = Script(clock, {work_url(k): v for k, v in steps.items()})
    manifest = enrich(
        dois,
        tmp / "bundle",
        transport=transport,
        limits=Limits(**limits),
        clock=clock,
        sleep=clock.sleep,
        now=lambda: "2026-10-27T00:00:00Z",
    )
    return manifest, transport, clock


def outcome(manifest: dict[str, Any], doi: str) -> tuple[str, str | None]:
    w = next(w for w in manifest["works"] if w["doi"] == doi)
    return w["outcome"], w["failure"]


@pytest.mark.negative
@pytest.mark.parametrize(
    ("steps", "failure"),
    [
        ([TransportTimeout("t")] * 3, "TIMEOUT"),
        ([TransportConnectionError("c")] * 3, "CONNECTION_ERROR"),
        ([Response(503, {}, b"")] * 3, "SERVER_ERROR"),
        ([Response(429, {}, b"")] * 3, "RATE_LIMITED"),
        ([Response(404, {}, b"")], "HTTP_ERROR"),
        ([ok(b"{not json")], "INVALID_JSON"),
        ([ok(b'{"a": 1, "a": 2}')], "INVALID_JSON"),  # duplicate keys are rejected
        ([ok(json.dumps({"status": "ok", "message-type": "work-list"}).encode())], "SCHEMA_INVALID"),
        ([ok(work("10.5555/a", [{"DOI": 5, "type": "retraction"}]))], "SCHEMA_INVALID"),
        ([ok(work("10.5555/OTHER"))], "DOI_MISMATCH"),
        ([Response(200, {}, work("10.5555/a")[:10], truncated=True)], "PAYLOAD_TOO_LARGE"),
    ],
    ids=[
        "timeout",
        "connection",
        "5xx",
        "429",
        "404",
        "invalid-json",
        "duplicate-keys",
        "wrong-type",
        "bad-updated-by",
        "doi-mismatch",
        "too-large",
    ],
)
def test_rde_failures_are_recorded_never_absence(tmp_path: Path, steps: list[Step], failure: str) -> None:
    manifest, transport, _ = run(tmp_path, {"10.5555/a": steps}, ["10.5555/a"])
    assert outcome(manifest, "10.5555/a") == ("failed", failure)
    assert len(transport.calls) == len(steps)
    assert not list((tmp_path / "bundle" / "payloads").iterdir())  # nothing cached for a failed response
    # Replayed into a build, a failure creates no assertion and leaves the RW-only answer unchanged.
    rows = [S.row(**{"Record ID": "1", "RetractionNature": "Correction", "OriginalPaperDOI": "10.5555/a"})]
    src, receipt = S.write_source(tmp_path / "b", S.csv_bytes(rows))
    idx = build(src, receipt, tmp_path / "ix", corroboration=tmp_path / "bundle" / "manifest.json").index_path
    out = lookup(idx, "10.5555/a")
    assert out["projection"]["retraction_status"]["value"] == "correction"
    with Index(idx) as ix:
        assert ix.conn.execute("SELECT COUNT(*) FROM cr_assertion").fetchone()[0] == 0
        assert ix.conn.execute("SELECT outcome, failure FROM cr_attempt").fetchall() == [("failed", failure)]
    assert all(s["source_id"] != "crossref" for s in out["checked_sources"])  # a failed source is not checked


@pytest.mark.negative
def test_rde_retry_backoff_and_retry_after(tmp_path: Path) -> None:
    steps: list[Step] = [Response(429, {"retry-after": "5"}, b""), Response(503, {}, b""), ok(work("10.5555/a"))]
    manifest, _transport, clock = run(tmp_path, {"10.5555/a": steps}, ["10.5555/a"])
    assert outcome(manifest, "10.5555/a") == ("ok", None)
    w = manifest["works"][0]
    assert w["attempts"] == 3 and w["waits"] == [5.0, 4.0]  # Retry-After over the 2 s backoff, then 4 s
    assert clock.sleeps[:2] == [5.0, 4.0]


@pytest.mark.negative
def test_rde_access_denied_stops_the_run(tmp_path: Path) -> None:
    steps = {"10.5555/a": [Response(403, {}, b"")], "10.5555/b": [ok(work("10.5555/b"))]}
    manifest, transport, _ = run(tmp_path, steps, ["10.5555/a", "10.5555/b"])
    assert manifest["stopped"] == "ACCESS_DENIED"
    assert outcome(manifest, "10.5555/a") == ("failed", "ACCESS_DENIED")
    assert outcome(manifest, "10.5555/b") == ("failed", "DEFERRED_BUDGET")  # listed, not requested
    assert transport.calls == [work_url("10.5555/a")]


@pytest.mark.negative
def test_rde_budgets_defer_instead_of_waiting(tmp_path: Path) -> None:
    long_wait = {"10.5555/a": [Response(429, {"retry-after": "60"}, b"")]}
    manifest, transport, clock = run(tmp_path, long_wait, ["10.5555/a"])
    assert outcome(manifest, "10.5555/a") == ("failed", "DEFERRED_BUDGET")
    assert clock.sleeps == [] and len(transport.calls) == 1
    many = {f"10.5555/w{i}": [ok(work(f"10.5555/w{i}"))] for i in range(5)}
    manifest, transport, _ = run(tmp_path / "m", many, list(many), max_works=3)
    assert len(transport.calls) == 3 and manifest["not_requested_over_work_limit"] == ["10.5555/w3", "10.5555/w4"]
    manifest, transport, _ = run(tmp_path / "n", many, list(many), max_attempts=2)
    assert len(transport.calls) == 2
    assert [w["failure"] for w in manifest["works"]][2:] == ["DEFERRED_BUDGET"] * 3
    manifest, transport, _ = run(tmp_path / "r", many, list(many), per_run=12.0)
    assert manifest["elapsed_seconds"] <= 12.0
    assert any(w["failure"] == "DEFERRED_BUDGET" for w in manifest["works"])


@pytest.mark.unit
def test_rde_rate_spacing_honours_headers(tmp_path: Path) -> None:
    steps = {
        "10.5555/a": [ok(work("10.5555/a"), x_rate_limit_limit="1", x_rate_limit_interval="3s")],
        "10.5555/b": [ok(work("10.5555/b"))],
    }
    _, _, clock = run(tmp_path, steps, ["10.5555/a", "10.5555/b"])
    assert clock.sleeps and clock.sleeps[0] == pytest.approx(3.0 - 0.2)


@pytest.mark.negative
def test_rde_invalid_inputs_are_rejected_not_requested(tmp_path: Path) -> None:
    manifest, transport, _ = run(tmp_path, {}, ["not a doi", "https://example.org/10.5555/a"])
    assert transport.calls == [] and len(manifest["rejected_inputs"]) == 2


@pytest.mark.security
def test_rde_real_transport_refuses_other_hosts() -> None:
    with pytest.raises(ValueError, match="refusing"):
        UrllibTransport().get("https://example.org/works/10.5555/a", 1.0, 10)


def _bundle_with(tmp: Path, original: str, updated_by: list[dict[str, Any]]) -> Path:
    return S.crossref_bundle(tmp, [{"original": original, "updated_by": updated_by}])


@pytest.mark.integration
def test_rde_replay_lineage_and_dependence(tmp_path: Path) -> None:
    """RW-sourced Crossref relations share the RW origin; publisher relations keep unknown independence."""
    rows = [
        S.row(
            **{
                "Record ID": "1",
                "RetractionNature": "Retraction",
                "OriginalPaperDOI": "10.5555/o",
                "RetractionDOI": "10.5555/o.n",
            }
        )
    ]
    entries = [
        {"DOI": "10.5555/o.n", "type": "retraction", "source": "retraction-watch", "record-id": 1},
        {"DOI": "10.5555/o.p", "type": "retraction", "source": "publisher"},
        {"DOI": "10.5555/o.x", "type": "addendum"},
    ]
    idx = S.build_rows(tmp_path, rows, [{"original": "10.5555/o", "updated_by": entries}])
    with Index(idx) as ix:
        cr = {r[0]: r[1:] for r in ix.conn.execute("SELECT pointer, origin, depends_on, mapped_type FROM cr_assertion")}
        ev = ix.gather("10.5555/o")
        rep = tension.report(ev, ix.snapshot_id)
    assert cr["/message/updated-by/0"] == ("retraction-watch", '["retraction-watch"]', "retracted")
    assert cr["/message/updated-by/1"] == ("publisher", "[]", "retracted")
    assert cr["/message/updated-by/2"] == ("unknown", "[]", None)  # unmapped types carry no type
    out = lookup(idx, "10.5555/o")
    basis = out["projection"]["basis"]
    assert sorted(basis["origins"]) == ["publisher", "retraction-watch"]
    collapse = next(r for r in rep["interventions"] if r["intervention"] == "collapse_shared_origin")
    assert collapse["result"]["support.observations"] == 2  # two origins, not three channels
    assert rep["base"]["result"]["support.observations"] == 3
    assert "redistributed_support" in rep["diagnostic_classes"]
    no_rw = next(
        r
        for r in rep["interventions"]
        if r["intervention"] == "exclude_origin" and r["origins"] == ["retraction-watch"]
    )
    assert no_rw["result"]["retraction_status.value"] == "retracted"  # the publisher relation alone remains
    assert sorted(no_rw["affected_assertions"]) == sorted(
        a for a in (s["assertion_id"] for s in rep["source_pointers"]) if a.endswith("/event_type") or a.endswith("-u0")
    )


@pytest.mark.integration
def test_rde_resolving_notice_is_not_typed_corroboration(tmp_path: Path) -> None:
    rows = [
        S.row(
            **{
                "Record ID": "1",
                "RetractionNature": "Correction",
                "OriginalPaperDOI": "10.5555/o",
                "RetractionDOI": "10.5555/o.n",
            }
        )
    ]
    idx = S.build_rows(tmp_path, rows, [{"original": "10.5555/o.n", "updated_by": []}])
    with Index(idx) as ix:
        preds = ix.conn.execute("SELECT predicate, notice_doi, mapped_type FROM cr_assertion").fetchall()
    assert preds == [("notice_record_exists", "10.5555/o.n", None)]
    out = lookup(idx, "10.5555/o")
    assert out["projection"]["basis"]["origins"] == ["retraction-watch"]
    assert out["projection"]["retraction_status"]["value"] == "correction"


@pytest.mark.negative
def test_rde_replay_rejects_tampered_bundles(tmp_path: Path) -> None:
    rows = [S.row(**{"Record ID": "1", "RetractionNature": "Retraction", "OriginalPaperDOI": "10.5555/o"})]
    src, receipt = S.write_source(tmp_path, S.csv_bytes(rows))
    manifest = _bundle_with(tmp_path, "10.5555/o", [{"DOI": "10.5555/n", "type": "retraction"}])
    data = json.loads(manifest.read_text(encoding="utf-8"))
    payload = manifest.parent / "payloads" / f"{data['works'][0]['payload_sha256']}.json"

    def expect_invalid(mutated: dict[str, Any] | str) -> None:
        text = mutated if isinstance(mutated, str) else json.dumps(mutated)
        manifest.write_text(text, encoding="utf-8")
        with pytest.raises(ImportFailure) as info:
            build(src, receipt, tmp_path / "ix", corroboration=manifest)
        assert info.value.code == "CORROBORATION_INVALID"
        assert not list((tmp_path / "ix").glob("*.sqlite")) if (tmp_path / "ix").exists() else True

    expect_invalid({**data, "manifest_version": "9"})
    expect_invalid({**data, "works": [data["works"][0], data["works"][0]]})
    expect_invalid({**data, "works": [{**data["works"][0], "doi": "10.5555/O"}]})
    expect_invalid({**data, "works": [{**data["works"][0], "outcome": "failed", "failure": "MADE_UP"}]})
    expect_invalid(json.dumps(data)[:-1] + ', "works": []}')  # duplicate key
    original = payload.read_bytes()
    payload.write_bytes(original.replace(b"retraction", b"correction"))
    expect_invalid(data)
    payload.write_bytes(original)
    good = json.dumps(data)
    manifest.write_text(good, encoding="utf-8")
    assert load_manifest(manifest)["works"][0]["payload_sha256"] == hashlib.sha256(original).hexdigest()
    build(src, receipt, tmp_path / "ix", corroboration=manifest)


@pytest.mark.reproducibility
def test_rde_replay_reproduces_assertions_and_keeps_retrieval_time(tmp_path: Path) -> None:
    rows = [S.row(**{"Record ID": "1", "RetractionNature": "Retraction", "OriginalPaperDOI": "10.5555/o"})]
    relations = [{"original": "10.5555/o", "updated_by": [{"DOI": "10.5555/n", "type": "retraction"}]}]
    a = S.build_rows(tmp_path / "a", rows, relations)
    b = S.build_rows(tmp_path / "b", rows, relations)
    with Index(a) as ia, Index(b) as ib:
        qa = ia.conn.execute("SELECT * FROM cr_assertion ORDER BY assertion_id").fetchall()
        qb = ib.conn.execute("SELECT * FROM cr_assertion ORDER BY assertion_id").fetchall()
        assert qa == qb and qa
        assert {r[0] for r in ia.conn.execute("SELECT retrieved_at FROM cr_assertion")} == {"2026-01-02T00:00:00Z"}
        assert ia.meta["semantic_digest"] == ib.meta["semantic_digest"]
