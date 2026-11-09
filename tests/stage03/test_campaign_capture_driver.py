"""The resumable confirmation-campaign capture driver (``evaluation/scripts/campaign_capture.py``; owner instruction
D-034, section 5, R8 and R10). SYNTHETIC: a scripted stand-in for the capture CLI and a scripted clock. No request
is made."""

from __future__ import annotations

import fcntl
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "docs/verification/stage-03/evaluation/scripts"
sys.path.insert(0, str(SCRIPTS))
cc = importlib.import_module("campaign_capture")

T0 = 1_793_600_000.0  # a fixed wall-clock time


class Clock:
    def __init__(self) -> None:
        self.t = T0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.t

    def sleep(self, s: float) -> None:
        self.sleeps.append(s)
        self.t += s


def stamp(t: float) -> str:
    return cc._stamp(t).replace("+00:00", "Z")


def result(status: str, *, not_before: float | None = None, codes: tuple[str, ...] = (), render: Any = None) -> Any:
    attempts = [{"code": None, "body_bytes": 1000}, {"code": None, "body_bytes": 2000}]
    cap = {
        "attempts": attempts,
        "issues": [{"code": c, "severity": "error"} for c in codes],
        "not_before": stamp(not_before) if not_before is not None and status == "deferred" else None,
        "render": render or {},
    }
    return {"status": status, "bundle": "b", "capture": cap}


class FakeCli:
    def __init__(self, answers: list[Any]) -> None:
        self.answers = list(answers)
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str]) -> tuple[int, str, str]:
        self.calls.append(argv)
        out = Path(argv[argv.index("--out") + 1])
        assert not out.exists(), "a bundle path was reused"
        out.mkdir(parents=True)
        return 0, json.dumps(self.answers.pop(0)), ""


def plan(tmp_path: Path, *articles: tuple[str, str, int]) -> Path:
    p = tmp_path / "plan.json"
    p.write_text(
        json.dumps({"campaign": "t", "articles": [{"split": s, "wiki": w, "page_id": n} for s, w, n in articles]}),
        encoding="utf-8",
    )
    return p


def states(out: Path) -> dict[str, Any]:
    return dict(json.loads((out / "capture_states.json").read_text(encoding="utf-8"))["articles"])


def go(p: Path, out: Path, cli: FakeCli, clock: Clock) -> int:
    return int(cc.run(p, out, cli, clock, clock.sleep))


@pytest.mark.regression
def test_a_complete_capture_is_never_repeated(tmp_path: Path) -> None:
    p, out, clock = plan(tmp_path, ("holdout", "ar", 1), ("holdout", "en", 2)), tmp_path / "out", Clock()
    cli = FakeCli([result("complete"), result("complete")])
    assert go(p, out, cli, clock) == 0 and len(cli.calls) == 2
    again = FakeCli([])
    assert go(p, out, again, clock) == 0 and again.calls == []


@pytest.mark.regression
def test_a_long_deferral_is_resumed_only_after_not_before(tmp_path: Path) -> None:
    p, out, clock = plan(tmp_path, ("holdout", "ar", 1), ("holdout", "en", 2)), tmp_path / "out", Clock()
    cli = FakeCli([result("deferred", not_before=T0 + 3600), result("complete")])
    assert go(p, out, cli, clock) == 4  # the other article was still captured
    assert [c[5] for c in cli.calls] == ["1", "2"]
    early = FakeCli([])
    clock.t = T0 + 1800
    assert go(p, out, early, clock) == 4 and early.calls == []  # restarted before not_before: no request
    clock.t = T0 + 3601
    late = FakeCli([result("complete")])
    assert go(p, out, late, clock) == 0
    assert late.calls[0][-1].endswith("ar-1-a2")
    assert states(out)["holdout/ar-1"]["final"]["status"] == "complete"


@pytest.mark.regression
def test_a_short_deferral_is_waited_inline_never_earlier(tmp_path: Path) -> None:
    p, out, clock = plan(tmp_path, ("holdout", "ar", 1)), tmp_path / "out", Clock()
    cli = FakeCli([result("deferred", not_before=T0 + 120), result("complete")])
    assert go(p, out, cli, clock) == 0
    assert clock.sleeps == [121.0]  # not_before plus the one-second margin


@pytest.mark.regression
def test_a_deferred_render_is_retried_after_its_not_before(tmp_path: Path) -> None:
    p, out, clock = plan(tmp_path, ("holdout", "ar", 1)), tmp_path / "out", Clock()
    render = {"code": "DEFERRED_RETRY_AFTER", "not_before": stamp(T0 + 60)}
    cli = FakeCli([result("partial", render=render), result("complete")])
    assert go(p, out, cli, clock) == 0 and clock.sleeps == [61.0]


@pytest.mark.regression
def test_an_interrupted_run_is_recorded_charged_and_never_reused(tmp_path: Path) -> None:
    p, out, clock = plan(tmp_path, ("holdout", "ar", 1)), tmp_path / "out", Clock()
    out.mkdir()
    # A driver was killed while the CLI ran: a start line, no end line, and a half-written bundle directory.
    (out / "captures.jsonl").write_text(json.dumps({"event": "start", "key": "holdout/ar-1", "run": 1}) + "\n")
    (out / "bundles" / "holdout" / "ar-1-a1").mkdir(parents=True)
    assert cc.used(cc._journal(out)) == (cc.RUN_WORST_ATTEMPTS, cc.RUN_WORST_BYTES)
    cli = FakeCli([result("complete")])
    assert go(p, out, cli, clock) == 0
    assert cli.calls[0][-1].endswith("ar-1-a2")
    runs = states(out)["holdout/ar-1"]["runs"]
    assert [r["run"] for r in runs] == [1, 2] and runs[0]["codes"] == ["DRIVER_INTERRUPTED"]


@pytest.mark.regression
def test_a_run_logged_but_not_saved_is_adopted_not_repeated(tmp_path: Path) -> None:
    p, out, clock = plan(tmp_path, ("holdout", "ar", 1)), tmp_path / "out", Clock()
    out.mkdir()
    lines = [
        {"event": "start", "key": "holdout/ar-1", "run": 1},
        {"event": "end", "key": "holdout/ar-1", "run": 1, "exit": 0, "stdout": result("complete")},
    ]
    (out / "captures.jsonl").write_text("".join(json.dumps(x) + "\n" for x in lines))
    cli = FakeCli([])
    assert go(p, out, cli, clock) == 0 and cli.calls == []
    assert states(out)["holdout/ar-1"]["final"]["status"] == "complete"


@pytest.mark.security
def test_a_second_driver_on_the_same_directory_makes_no_request(tmp_path: Path) -> None:
    p, out, clock = plan(tmp_path, ("holdout", "ar", 1)), tmp_path / "out", Clock()
    out.mkdir()
    fd = os.open(out / "driver.lock", os.O_RDWR | os.O_CREAT, 0o600)
    fcntl.flock(fd, fcntl.LOCK_EX)
    try:
        cli = FakeCli([])
        assert go(p, out, cli, clock) == 3 and cli.calls == []
    finally:
        os.close(fd)


@pytest.mark.security
def test_the_ceiling_stops_before_a_run_that_could_cross_it(tmp_path: Path) -> None:
    p, out, clock = plan(tmp_path, ("holdout", "ar", 1)), tmp_path / "out", Clock()
    out.mkdir()
    big = {"status": "failed", "capture": {"attempts": [{"code": "HTTP_RATE_LIMITED"}] * 495}}  # a reported record
    lines = [
        {"event": "start", "key": "x/ar-9", "run": 1},
        {"event": "end", "key": "x/ar-9", "run": 1, "exit": 1, "stdout": big},
    ]
    (out / "captures.jsonl").write_text("".join(json.dumps(x) + "\n" for x in lines))
    cli = FakeCli([])
    assert go(p, out, cli, clock) == 2 and cli.calls == []
    ceiling = json.loads((out / "ceiling.json").read_text())
    assert ceiling["http_attempts"] == 495 and ceiling["stopped_before"] == "holdout/ar-1"


@pytest.mark.negative
def test_retryable_failures_get_one_more_run_and_others_none(tmp_path: Path) -> None:
    p, out, clock = plan(tmp_path, ("holdout", "ar", 1), ("holdout", "en", 2)), tmp_path / "out", Clock()
    cli = FakeCli(
        [
            result("failed", codes=("ATTEMPTS_EXHAUSTED",)),
            result("failed", codes=("ATTEMPTS_EXHAUSTED",)),
            result("failed", codes=("PAGE_NOT_FOUND",)),
        ]
    )
    assert go(p, out, cli, clock) == 0 and len(cli.calls) == 3
    s = states(out)
    assert len(s["holdout/ar-1"]["runs"]) == 2 and len(s["holdout/en-2"]["runs"]) == 1


@pytest.mark.negative
def test_runs_per_article_are_bounded(tmp_path: Path) -> None:
    p, out, clock = plan(tmp_path, ("holdout", "ar", 1)), tmp_path / "out", Clock()
    cli = FakeCli([result("deferred", not_before=T0 + 10 * (i + 1)) for i in range(10)])
    assert go(p, out, cli, clock) == 0
    assert len(cli.calls) == cc.MAX_RUNS


@pytest.mark.negative
def test_a_clock_that_does_not_advance_never_spins(tmp_path: Path) -> None:
    p, out = plan(tmp_path, ("holdout", "ar", 1)), tmp_path / "out"
    clock = Clock()
    cli = FakeCli([result("deferred", not_before=T0 + 60)])
    assert int(cc.run(p, out, cli, clock, lambda s: None)) == 4 and len(cli.calls) == 1


@pytest.mark.negative
@pytest.mark.parametrize(
    "bad",
    [
        [{"split": "h", "wiki": "fr", "page_id": 1}],
        [{"split": "h", "wiki": "ar", "page_id": 0}],
        [{"split": "../x", "wiki": "ar", "page_id": 1}],
        [{"split": "h", "wiki": "ar", "page_id": 1}, {"split": "h", "wiki": "ar", "page_id": 1}],
    ],
)
def test_an_invalid_plan_is_refused_before_any_request(tmp_path: Path, bad: list[dict[str, Any]]) -> None:
    p = tmp_path / "plan.json"
    p.write_text(json.dumps({"campaign": "t", "articles": bad}))
    cli = FakeCli([])
    with pytest.raises(SystemExit):
        go(p, tmp_path / "out", cli, Clock())
    assert cli.calls == []


@pytest.mark.simulation
def test_campaign_driver_simulation_holds_every_invariant() -> None:
    root = Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        [sys.executable, str(root / "simulations" / "stage03" / "campaign_driver_sim.py"), "300", "20261102"],
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    )
    summary = json.loads(proc.stdout)
    assert proc.returncode == 0 and summary["failure_count"] == 0 and summary["sequences"] == 300
    assert {"killed", "exit_0", "exit_2", "exit_4"} <= set(summary["outcomes"])
