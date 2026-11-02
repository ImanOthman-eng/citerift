"""Regressions for the confirmed findings of adversarial review R6 (candidate 5b1dcb0; review/r6/REVIEW.md).
SYNTHETIC: scripted stand-ins for the capture CLI, the fetch client and the clock. No request is made.

RR-1 a run with a reported capture record is charged what it records (zero for a gate deferral); RR-2 a draw request
deferred by a server waits and is sent again; RR-3 an unreadable Retry-After is final; RR-4 a torn journal line is
kept aside; RR-5 redirects of one short-footnote template are one template; RR-6 a bundle published before an
interruption is adopted; RR-7 the reserve step refuses unresolved captures; RR-8 the prediction run refuses a
captured article without a locked label; RR-9 a ``Template:`` prefix in any case is a marker call; RR-10 the gate
record is never left empty; RR-11 positional values are trimmed as Lua does; RR-12 the worst case of a run bounds
the fetch policy; RR-13 the acquisition time limit and draw request numbering.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from wiki_support import bundle, extract

from citerift.wiki import fetch
from citerift.wiki import source as source_module
from citerift.wiki.fetch import FetchPolicy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "docs/verification/stage-03/evaluation/scripts"))
sys.path.insert(0, str(ROOT / "docs/verification/stage-03/evaluation/confirmation-2026-11/scripts"))
cc = importlib.import_module("campaign_capture")
sel = importlib.import_module("select_confirmation")
rs = importlib.import_module("reserve_step")
wc = importlib.import_module("warning_challenge")
rc = importlib.import_module("run_confirmation")

T0 = 1_793_600_000.0  # 2026-11-02, before the acquisition time limit


class Clock:
    def __init__(self, t: float = T0) -> None:
        self.t = t
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.t

    def sleep(self, s: float) -> None:
        self.sleeps.append(s)
        self.t += s


class Cli:
    """A stand-in for ``citerift-wiki capture``; an answer may publish a bundle (capture.json) or raise."""

    def __init__(self, answers: list[Any]) -> None:
        self.answers = list(answers)
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str]) -> tuple[int, str, str]:
        self.calls.append(argv)
        out = Path(argv[argv.index("--out") + 1])
        assert not out.exists(), "a bundle path was reused"
        answer = self.answers.pop(0)
        if isinstance(answer, BaseException):
            out.mkdir(parents=True)
            (out / "capture.json").write_text(json.dumps(answer.args[0]), encoding="utf-8")
            raise answer
        out.mkdir(parents=True)
        return 0, json.dumps(answer), ""


class Killed(BaseException):
    """The driver was killed after the CLI published its bundle."""


def stamp(t: float) -> str:
    return cc._stamp(t).replace("+00:00", "Z")


def captured(status: str, attempts: list[dict[str, Any]] | None = None, **cap: Any) -> dict[str, Any]:
    record = {
        "attempts": [{"code": None, "body_bytes": 1000}] if attempts is None else attempts,
        "issues": [],
        "not_before": None,
        "render": {},
        **cap,
    }
    return {"status": status, "bundle": "b", "capture": record}


def plan(tmp: Path, *articles: tuple[str, str, int]) -> Path:
    p = tmp / "plan.json"
    rows = [{"split": s, "wiki": w, "page_id": n} for s, w, n in articles]
    p.write_text(json.dumps({"campaign": "t", "articles": rows}), encoding="utf-8")
    return p


def states(out: Path) -> dict[str, Any]:
    return dict(json.loads((out / "capture_states.json").read_text(encoding="utf-8"))["articles"])


# RR-1, RR-12 -----------------------------------------------------------------------------------------------------


@pytest.mark.regression
def test_a_run_the_gate_deferred_costs_nothing_and_an_unreported_run_the_worst_case() -> None:
    deferred = {"event": "end", "key": "k", "run": 1, "stdout": captured("deferred", attempts=[])}
    crashed = {"event": "end", "key": "k", "run": 2, "stdout": {"unparsed_stdout": "Traceback"}}
    assert cc.used([{"event": "start", "key": "k", "run": 1}, deferred]) == (0, 0)
    assert cc.used([{"event": "start", "key": "k", "run": 2}, crashed]) == (cc.RUN_WORST_ATTEMPTS, cc.RUN_WORST_BYTES)


@pytest.mark.regression
def test_many_gate_deferrals_never_reach_a_phantom_ceiling(tmp_path: Path) -> None:
    out = tmp_path / "out"
    out.mkdir()
    lines = []
    for i in range(100):  # 100 earlier runs answered by the gate: no request was made
        lines += [
            {"event": "start", "key": f"x/en-{i}", "run": 1},
            {"event": "end", "key": f"x/en-{i}", "run": 1, "exit": 75, "stdout": captured("deferred", attempts=[])},
        ]
    (out / "captures.jsonl").write_text("".join(json.dumps(x) + "\n" for x in lines))
    clock, cli = Clock(), Cli([captured("complete")])
    assert cc.run(plan(tmp_path, ("holdout", "en", 1)), out, cli, clock, clock.sleep) == 0
    assert len(cli.calls) == 1 and not (out / "ceiling.json").exists()


@pytest.mark.unit
def test_the_worst_case_of_one_run_bounds_the_fetch_policy() -> None:
    policy = FetchPolicy()
    assert 2 * policy.max_attempts == cc.RUN_WORST_ATTEMPTS
    assert 2 * policy.max_body_bytes == cc.RUN_WORST_BYTES  # one accepted body per operation


# RR-3 -----------------------------------------------------------------------------------------------------------


@pytest.mark.negative
@pytest.mark.parametrize("problem", ["RETRY_AFTER_UNREADABLE", "RETRY_AFTER_OUT_OF_RANGE"])
def test_a_429_with_an_unusable_retry_after_is_not_run_again(tmp_path: Path, problem: str) -> None:
    attempt = {"code": "HTTP_RATE_LIMITED", "retry_after_raw": "soon", "retry_after_problem": problem}
    failed = captured("failed", attempts=[attempt], issues=[{"code": "HTTP_RATE_LIMITED", "severity": "error"}])
    clock, cli = Clock(), Cli([failed])
    assert cc.run(plan(tmp_path, ("holdout", "en", 1)), tmp_path / "out", cli, clock, clock.sleep) == 0
    assert len(cli.calls) == 1
    run = states(tmp_path / "out")["holdout/en-1"]["runs"][0]
    assert run["retry_after_problems"] == [problem]


# RR-4 -----------------------------------------------------------------------------------------------------------


@pytest.mark.regression
def test_a_torn_final_journal_line_is_kept_aside_and_the_driver_resumes(tmp_path: Path) -> None:
    out = tmp_path / "out"
    out.mkdir()
    start = json.dumps({"event": "start", "key": "holdout/en-1", "run": 1}) + "\n"
    torn = '{"event": "end", "key": "holdout/en-1", "run": 1, "stdout": {"status": "comp'
    (out / "captures.jsonl").write_text(start + torn)
    assert cc._journal(out) == [json.loads(start)]  # a reader ignores the torn line
    clock, cli = Clock(), Cli([captured("complete")])
    assert cc.run(plan(tmp_path, ("holdout", "en", 1)), out, cli, clock, clock.sleep) == 0
    (side,) = out.glob("captures.jsonl.torn-at-*")
    assert side.read_text() == torn
    entries = cc._journal(out)  # every line parses again
    assert [e["event"] for e in entries] == ["start", "start", "end"]
    assert (out / "captures.jsonl").read_text().endswith("\n")


@pytest.mark.negative
def test_a_malformed_complete_journal_line_stays_an_error(tmp_path: Path) -> None:
    out = tmp_path / "out"
    out.mkdir()
    (out / "captures.jsonl").write_text("{not json}\n")
    with pytest.raises(json.JSONDecodeError):
        cc._journal(out)


# RR-6 -----------------------------------------------------------------------------------------------------------


@pytest.mark.regression
def test_a_bundle_published_before_an_interruption_is_adopted_not_captured_again(tmp_path: Path) -> None:
    out, clock = tmp_path / "out", Clock()
    published = {"status": "complete", "attempts": [{"code": None, "body_bytes": 4000}], "issues": [], "render": {}}
    p = plan(tmp_path, ("holdout", "en", 7))
    with pytest.raises(Killed):
        cc.run(p, out, Cli([Killed(published)]), clock, clock.sleep)
    again = Cli([])
    assert cc.run(p, out, again, clock, clock.sleep) == 0 and again.calls == []
    rec = states(out)["holdout/en-7"]
    assert [r["status"] for r in rec["runs"]] == ["complete"] and rec["final"]["bundle"].endswith("en-7-a1")
    recovered = [e for e in cc._journal(out) if e.get("recovered")]
    assert len(recovered) == 1 and cc.used(cc._journal(out)) == (1, 4000)  # charged what it recorded


@pytest.mark.regression
def test_an_interrupted_run_without_a_published_bundle_is_still_run_again(tmp_path: Path) -> None:
    out, clock = tmp_path / "out", Clock()
    out.mkdir()
    target = out / "bundles" / "holdout" / "en-7-a1"
    argv = ["citerift-wiki", "capture", "--wiki", "en", "--page-id", "7", "--out", str(target)]
    (out / "captures.jsonl").write_text(json.dumps({"event": "start", "key": "holdout/en-7", "run": 1, "argv": argv}))
    (out / "captures.jsonl").write_text((out / "captures.jsonl").read_text() + "\n")
    target.mkdir(parents=True)  # created, nothing published
    cli = Cli([captured("complete")])
    assert cc.run(plan(tmp_path, ("holdout", "en", 7)), out, cli, clock, clock.sleep) == 0
    assert cli.calls[0][-1].endswith("en-7-a2")
    assert states(out)["holdout/en-7"]["runs"][0]["codes"] == ["DRIVER_INTERRUPTED"]


# RR-13: acquisition time limit ------------------------------------------------------------------------------------


@pytest.mark.negative
def test_no_run_starts_after_the_acquisition_time_limit(tmp_path: Path) -> None:
    out = tmp_path / "out"
    clock, cli = Clock(cc.ACQUISITION_END), Cli([])
    assert cc.run(plan(tmp_path, ("holdout", "en", 1)), out, cli, clock, clock.sleep) == 5 and cli.calls == []
    assert json.loads((out / "acquisition_closed.json").read_text())["stopped_before"] == "holdout/en-1"
    assert cc._stamp(cc.ACQUISITION_END) == "2026-11-14T23:59:00+00:00"


# RR-2, RR-13: the draw ---------------------------------------------------------------------------------------------


class Fetch:
    """A stand-in for the production client's ``Fetcher.get``."""

    def __init__(self, answers: list[tuple[str | None, float | None, Any]]) -> None:
        self.answers = list(answers)
        self.urls: list[str] = []

    def __call__(self, url: str) -> Any:
        self.urls.append(url)
        code, not_before, data = self.answers.pop(0)
        attempts = [] if code in ("DEFERRED_RETRY_AFTER", "NETWORK_GATE_BUSY") else [{"code": code, "body_bytes": 10}]
        if code == "HTTP_RATE_LIMITED" and data == "unreadable":
            attempts = [{"code": code, "retry_after_problem": "RETRY_AFTER_UNREADABLE"}]
        return SimpleNamespace(
            code=code,
            not_before=stamp(not_before) if not_before is not None else None,
            attempts=[SimpleNamespace(to_json=lambda a=a: a) for a in attempts],
            body=json.dumps(data).encode() if code is None else None,
            json=data if code is None else None,
        )


@pytest.mark.regression
def test_a_deferred_draw_request_waits_for_not_before_and_is_sent_again(tmp_path: Path) -> None:
    clock = Clock()
    f = Fetch([("DEFERRED_RETRY_AFTER", T0 + 120, None), (None, None, {"query": {"random": []}})])
    get = sel.LiveGet(tmp_path, f, clock, clock.sleep)
    assert get("https://ar.wikipedia.org/w/api.php?x") == {"query": {"random": []}}
    assert clock.sleeps == [121.0] and len(f.urls) == 2
    assert cc.used(cc._journal(tmp_path / "capture")) == (1, 10)  # the deferral cost nothing


@pytest.mark.negative
def test_a_long_server_wait_stops_the_draw_before_any_selection(tmp_path: Path) -> None:
    clock = Clock()
    get = sel.LiveGet(tmp_path, Fetch([("DEFERRED_RETRY_AFTER", T0 + 2 * sel.DRAW_MAX_WAIT_S, None)]), clock)
    with pytest.raises(SystemExit, match="draw stopped"):
        sel.select(get, {"page_ids": [], "titles": []})
    assert clock.sleeps == []


@pytest.mark.regression
def test_a_retryable_draw_failure_is_sent_once_more_and_a_guessed_wait_never(tmp_path: Path) -> None:
    clock = Clock()
    f = Fetch([("ATTEMPTS_EXHAUSTED", None, None), (None, None, {"ok": 1})])
    assert sel.LiveGet(tmp_path / "a", f, clock, clock.sleep)("u") == {"ok": 1}
    f = Fetch([("ATTEMPTS_EXHAUSTED", None, None), ("ATTEMPTS_EXHAUSTED", None, None)])
    assert sel.LiveGet(tmp_path / "b", f, clock, clock.sleep)("u") is None and len(f.urls) == 2
    f = Fetch([("HTTP_RATE_LIMITED", None, "unreadable")])
    assert sel.LiveGet(tmp_path / "c", f, clock, clock.sleep)("u") is None and len(f.urls) == 1
    f = Fetch([("PAGE_NOT_FOUND", None, None)])
    assert sel.LiveGet(tmp_path / "d", f, clock, clock.sleep)("u") is None and len(f.urls) == 1


@pytest.mark.regression
def test_a_draw_after_an_interrupted_one_continues_the_request_numbers_and_lists_them(tmp_path: Path) -> None:
    log = tmp_path / "capture" / "captures.jsonl"
    log.parent.mkdir(parents=True)
    log.write_text(json.dumps({"event": "start", "key": "selection/request-0003", "run": 1}) + "\n")
    clock = Clock()
    get = sel.LiveGet(tmp_path, Fetch([(None, None, {"ok": 1})]), clock, clock.sleep)
    get("u")
    assert get.earlier == ["selection/request-0003"]
    assert cc._journal(tmp_path / "capture")[-1]["key"] == "selection/request-0004"


# RR-7: the reserve step -------------------------------------------------------------------------------------------


def _selection() -> dict[str, Any]:
    frame = {"initial": [{"page_id": 1}, {"page_id": 2}], "reserve_blocks": [[{"page_id": 3}]]}
    return {"frame": {"ar": frame, "en": frame}}


def _state(status: str, **extra: Any) -> dict[str, Any]:
    run = {"run": 1, "status": status, "bundle": None, "codes": [], "deferred": False, "not_before": None, **extra}
    return {"runs": [run], "final": run}


@pytest.mark.negative
def test_the_reserve_step_refuses_a_pending_deferral(tmp_path: Path) -> None:
    st = {f"holdout/{w}-{n}": _state("failed", codes=["PAGE_NOT_FOUND"]) for w in ("ar", "en") for n in (1, 2)}
    st["holdout/en-2"] = _state("deferred", deferred=True, not_before=stamp(T0 + 86400))
    with pytest.raises(SystemExit, match="unresolved"):
        rs.decide(_selection(), st, {}, now=T0)


@pytest.mark.regression
def test_after_a_stop_the_reserve_step_counts_what_it_has_and_names_no_block() -> None:
    st = {f"holdout/{w}-1": _state("failed", codes=["PAGE_NOT_FOUND"]) for w in ("ar", "en")}
    st["holdout/en-2"] = _state("deferred", deferred=True, not_before=stamp(T0 + 86400))
    st["holdout/ar-2"] = {"runs": [], "final": None}  # never run before the ceiling
    d = rs.decide(_selection(), st, {}, stopped="ceiling.json", now=T0)
    for wiki in ("ar", "en"):
        assert d[wiki]["next_block"] is None and d[wiki]["stopped"] == "ceiling.json"
        assert d[wiki]["included"] == [f"holdout/{wiki}-1", f"holdout/{wiki}-2"]


@pytest.mark.regression
def test_a_planned_but_never_run_block_is_the_next_block_not_a_captured_one() -> None:
    st = {f"holdout/{w}-{n}": _state("failed", codes=["PAGE_NOT_FOUND"]) for w in ("ar", "en") for n in (1, 2)}
    st |= {f"reserve1/{w}-3": {"runs": [], "final": None} for w in ("ar", "en")}  # in the plan, not yet run
    d = rs.decide(_selection(), st, {}, now=T0)
    assert d["ar"]["next_block"] == "reserve1" and d["ar"]["included"] == ["holdout/ar-1", "holdout/ar-2"]


# RR-8: the prediction run -----------------------------------------------------------------------------------------


def _captured_bundle(tmp: Path, wiki: str, page_id: int, rev: int) -> str:
    b = tmp / "bundles" / f"{wiki}-{page_id}"
    b.mkdir(parents=True)
    (b / "capture.json").write_text(json.dumps({"page": {"wiki": wiki, "revision_id": rev}}), encoding="utf-8")
    return str(b)


def _capture_dir(tmp: Path, rows: dict[str, Any]) -> Path:
    cap = tmp / "capture"
    cap.mkdir()
    (cap / "capture_states.json").write_text(json.dumps({"articles": rows}), encoding="utf-8")
    return cap


@pytest.mark.negative
def test_the_prediction_run_refuses_a_captured_article_without_a_locked_label(tmp_path: Path) -> None:
    complete = _state("complete")
    complete["final"] = {**complete["final"], "bundle": _captured_bundle(tmp_path, "en", 2, 22)}
    rows = {"holdout/en-1": {"split": "holdout", **_state("failed", codes=["PAGE_NOT_FOUND"])}}
    rows["reserve1/en-2"] = {"split": "reserve1", **complete}
    sel_doc: dict[str, Any] = {"challenge": {}}
    with pytest.raises(SystemExit, match=r"without a locked label: \['reserve1/en-2 \(en-22.json\)'\]"):
        rc.plan_run(sel_doc, _capture_dir(tmp_path, rows), {}, now=T0)


@pytest.mark.regression
def test_the_gate_spec_merges_holdout_and_reserves_and_the_challenge_is_separate(tmp_path: Path) -> None:
    labels: dict[str, Path] = {}
    rows: dict[str, Any] = {}
    for split, page in (("holdout", 1), ("reserve1", 2), ("challenge", 3)):
        st = _state("complete")
        st["final"] = {**st["final"], "bundle": _captured_bundle(tmp_path, "ar", page, page * 10)}
        rows[f"{split}/ar-{page}"] = {"split": split, **st}
        labels[f"ar-{page * 10}.json"] = tmp_path / f"ar-{page * 10}.json"
    sel_doc = {"challenge": {"ar": {"concern": {"selected": [{"page_id": 3}]}}}}
    planned = rc.plan_run(sel_doc, _capture_dir(tmp_path, rows), labels, now=T0)
    for r in planned:
        r["extraction"] = f"/x/{r['name']}"
    score_spec, challenge_spec = rc.specs(planned, None)
    assert [Path(e["locked"]).name for e in score_spec["splits"]["gate"]] == ["ar-10.json", "ar-20.json"]
    assert [(Path(e["locked"]).name, e["stratum"]) for e in challenge_spec["articles"]] == [("ar-30.json", "concern")]


# RR-9: marker calls -----------------------------------------------------------------------------------------------


@pytest.mark.regression
@pytest.mark.parametrize(
    ("wiki", "text"),
    [
        ("en", "{{Template:Retracted|doi=1}}"),
        ("en", "{{TEMPLATE : retracted|doi=1}}"),
        ("ar", "{{Template:Retracted|x}}"),
        ("ar", "{{قالب:مصدر مسحوب|x}}"),
    ],
)
def test_a_namespace_prefix_in_any_case_is_a_marker_call(wiki: str, text: str) -> None:
    assert wc.marker_calls(text, wiki) == [0]


# RR-10: the gate record -------------------------------------------------------------------------------------------


@pytest.mark.regression
@pytest.mark.parametrize("killed_at", ["pwrite", "ftruncate"])
def test_a_kill_while_the_gate_record_is_replaced_never_leaves_an_empty_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, killed_at: str
) -> None:
    path = tmp_path / "gate"
    path.write_text("1793600000.000 1793600100.000\n")
    fd = os.open(path, os.O_RDWR)

    def kill(*_: Any) -> None:
        raise Killed

    monkeypatch.setattr(fetch.os, killed_at, kill)
    try:
        with pytest.raises(Killed):
            fetch._write_record(fd, 1793600050.0, 1793600100.0)
    finally:
        monkeypatch.undo()
    assert fetch.NetworkGate._read(fd) in ((1793600000.0, 1793600100.0), (1793600050.0, 1793600100.0))
    os.close(fd)


@pytest.mark.negative
@pytest.mark.parametrize("record", [b"17", b"1793600000.000 17936", b"1 2 3\n"])
def test_a_torn_or_malformed_gate_record_imposes_the_full_interval(tmp_path: Path, record: bytes) -> None:
    path = tmp_path / "gate"
    path.write_bytes(record)
    fd = os.open(path, os.O_RDWR)
    before = time.time()
    last_end, not_before = fetch.NetworkGate._read(fd)
    os.close(fd)
    assert last_end >= before and not_before >= before  # read as "an attempt just ended": the full interval


@pytest.mark.unit
def test_an_empty_gate_file_is_no_record_yet(tmp_path: Path) -> None:
    path = tmp_path / "gate"
    path.write_bytes(b"")
    fd = os.open(path, os.O_RDWR)
    assert fetch.NetworkGate._read(fd) == (0.0, 0.0)
    os.close(fd)


# RR-5, RR-11: short-footnote identity -----------------------------------------------------------------------------


def short(doc: dict[str, Any]) -> list[tuple[str, int]]:
    return [(c["binding_state"], len(c["definitions"])) for c in doc["containers"] if c["layout"] == "short_footnote"]


@pytest.mark.regression
@pytest.mark.parametrize(
    ("wiki", "text"),
    [
        ("en", "A{{sfn|Smith|2001}} B{{sf|Smith|2001}}"),
        ("en", "A{{sfn|Smith|2001}} B{{Shortened footnote|Smith|2001}}"),
        ("en", "A{{sfnp|Smith|2001}} B{{Sfnb|Smith|2001}}"),
        ("ar", "أ{{Sfn|سميث|2001}} ب{{Sf|سميث|2001}}"),
        ("en", "A{{sfn|Smith|2001|ref=a b}} B{{sfn|Smith|2001|ref=a_b}}"),
        ("en", "A{{sfn|Smith\v|2001}} B{{sfn|Smith|2001}}"),  # Lua's %s trims \v
    ],
)
def test_redirects_of_one_template_and_equal_link_targets_are_one_reference(
    tmp_path: Path, wiki: str, text: str
) -> None:
    assert short(extract(bundle(tmp_path, text, wiki=wiki))) == [("identical_definitions", 2)]


@pytest.mark.regression
@pytest.mark.parametrize(
    "text",
    [
        "A{{sfn|Smith|2001}} B{{sfnp|Smith|2001}}",  # two templates: different note text
        "A{{sfn|Smith|2001|ref=a}} B{{sfn|Smith|2001|ref=b}}",
    ],
)
def test_different_templates_and_targets_stay_a_conflict(tmp_path: Path, text: str) -> None:
    assert short(extract(bundle(tmp_path, text))) == [("conflicting_definitions", 2)]


@pytest.mark.regression
def test_a_nul_in_the_source_is_never_trimmed_into_another_name(tmp_path: Path) -> None:
    """RR-11: Lua's %s has no NUL, so ``Smith\\0`` and ``Smith`` are two names in MediaWiki. The engine never merges
    them: the C tokenizer cannot parse a NUL losslessly, so the extraction fails honestly (review R7 restored the C
    tokenizer); the positional trim set is Lua's either way."""
    doc = extract(bundle(tmp_path, "A{{sfn|Smith\0|2001}} B{{sfn|Smith|2001}}"))
    assert doc["status"] == "failed" and "SOURCE_PARSE_LOSSY" in {i["code"] for i in doc["issues"]}
    assert "\0" in source_module._ARG_TRIM and "\0" not in source_module._LUA_TRIM
