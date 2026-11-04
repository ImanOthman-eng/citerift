"""Retry-After and cooldown audit of 2026-11-02 (owner instruction D-034, section 5, R1-R7). SYNTHETIC: scripted
transports and clocks, and a real lock file shared with a child process. No live request is made.

The existing tests in ``test_wiki_fetch_capture.py`` and ``test_wiki_review_regressions.py`` already cover the
plan, deferral, exhaustion and the shared ``not_before``. These tests add the cases the audit found untested, and
two defects:

- G-1: a process killed during an attempt left no record of that attempt, so the next process could send its
  request at once, closer than the minimum interval.
- G-2: the HTTP-date reader guessed. A date with an unknown zone, no zone or trailing text was read as UTC, although
  the contract is that a value that cannot be read stops the capture instead of guessing a wait.
"""

from __future__ import annotations

import itertools
import json
import os
import signal
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from wiki_support import JSON_TYPE, ScriptedClock, response

from citerift.wiki.fetch import Fetcher, FetchPolicy, NetworkGate, RawResponse, parse_retry_after

API = "https://en.wikipedia.org/w/api.php?action=query&format=json"
AT = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)
SRC = Path(__file__).resolve().parents[2] / "src"


def timed(answers: list[RawResponse | Exception], clock: ScriptedClock) -> tuple[Any, list[float]]:
    """A scripted transport that records the clock time of every request."""
    times: list[float] = []
    queue = list(answers)

    def transport(url: str, headers: dict[str, str], timeout: float) -> RawResponse:
        times.append(clock.t)
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    return transport, times


def api(data: Any, status: int = 200, retry_after: str | None = None) -> RawResponse:
    headers = {"content-type": JSON_TYPE}
    if retry_after is not None:
        headers["retry-after"] = retry_after
    return response(status, headers, json.dumps(data).encode())


# ------------------------------------------------------------------------------- R3: header parsing edge cases


@pytest.mark.unit
@pytest.mark.parametrize(
    ("value", "seconds", "problem"),
    [
        (" 40 ", 40.0, None),  # surrounding whitespace is not part of the value
        ("0", 0.0, None),
        ("1.5", None, "RETRY_AFTER_UNREADABLE"),  # delta-seconds is an integer (RFC 9110 10.2.3)
        ("120, 60", None, "RETRY_AFTER_UNREADABLE"),  # two combined header values: never pick one
        ("", None, "RETRY_AFTER_UNREADABLE"),
        ("+40", None, "RETRY_AFTER_UNREADABLE"),
        ("Wed, 28 Oct 2026 15:01:30 +0300", 90.0, None),  # an explicit numeric offset is honored
        ("Wednesday, 28-Oct-26 12:01:30 GMT", 90.0, None),  # RFC 850
        ("Mon, 28 Oct 2026 12:01:30 GMT", 90.0, None),  # a wrong weekday is not used
        # G-2: the date parser guessed. A zone it does not know, a missing zone or trailing text was read as UTC.
        ("Wed, 28 Oct 2026 12:01:30 GMT garbage", None, "RETRY_AFTER_UNREADABLE"),
        ("Wed, 28 Oct 2026 12:01:30 XYZ", None, "RETRY_AFTER_UNREADABLE"),
        ("Wed, 28 Oct 2026 12:01:30 EST", None, "RETRY_AFTER_UNREADABLE"),
        ("Wed, 28 Oct 2026 12:01:30", None, "RETRY_AFTER_UNREADABLE"),
        ("28 Oct 2026 12:01", None, "RETRY_AFTER_UNREADABLE"),
        ("Wed, 28 Oct 2028 12:00:00 GMT", None, "RETRY_AFTER_OUT_OF_RANGE"),
    ],
)
def test_retry_after_edge_cases(value: str, seconds: float | None, problem: str | None) -> None:
    assert parse_retry_after(value, AT) == (seconds, problem)


# ------------------------------------------------------------------------- R1/R2: 429, 503 and maxlag waits


@pytest.mark.negative
@pytest.mark.parametrize(
    "first",
    [
        api({"error": {"code": "maxlag", "info": "lagged"}}, 200, "40"),  # an HTTP 200 API error with Retry-After
        api({"x": 1}, 503, "40"),
        api({"x": 1}, 429, "40"),
    ],
)
def test_a_server_wait_is_honored_from_the_end_of_the_answer(first: RawResponse) -> None:
    clock = ScriptedClock()
    transport, times = timed([first, api({"query": {}})], clock)
    answer = Fetcher(FetchPolicy(), transport, clock).get(API, expect="json")
    assert answer.code is None and len(times) == 2
    assert answer.attempts[0].retry_after_s == 40.0
    assert times[1] - answer.attempts[0].ended_mono >= 40.0


@pytest.mark.negative
def test_maxlag_with_an_unreadable_retry_after_stops() -> None:
    clock = ScriptedClock()
    transport, times = timed([api({"error": {"code": "maxlag", "info": "x"}}, 200, "soon")], clock)
    answer = Fetcher(FetchPolicy(), transport, clock).get(API, expect="json")
    assert answer.code == "API_MAXLAG" and len(times) == 1


@pytest.mark.negative
def test_maxlag_past_the_deadline_is_deferred_with_not_before() -> None:
    clock = ScriptedClock()
    transport, times = timed([api({"error": {"code": "maxlag", "info": "x"}}, 200, "600")], clock)
    answer = Fetcher(FetchPolicy(), transport, clock).get(API, expect="json")
    assert answer.code == "DEFERRED_RETRY_AFTER" and len(times) == 1
    assert answer.not_before == "2026-10-28T12:10:00.000000Z"


# ------------------------------------------------------------------------- R5: network failures are bounded


@pytest.mark.negative
def test_network_failures_never_exceed_the_attempt_budget() -> None:
    from citerift.wiki.fetch import TransportError

    clock = ScriptedClock()
    failures: list[RawResponse | Exception] = [TransportError("HTTP_CONNECTION_FAILED", "x") for _ in range(10)]
    transport, times = timed(failures, clock)
    answer = Fetcher(FetchPolicy(), transport, clock).get(API, expect="json")
    assert answer.code == "ATTEMPTS_EXHAUSTED" and len(times) == 3
    assert all(b - a >= 10.0 for a, b in itertools.pairwise(times))


# ---------------------------------------------------------------- R4/R6: cross-process gate and interruptions


HOLDER = """
import sys, time
from pathlib import Path
from citerift.wiki.fetch import NetworkGate
gate = NetworkGate(Path(sys.argv[1]))
assert gate.acquire(0.0, 5.0) is None
print("acquired", flush=True)
time.sleep(60)  # killed here, during the "attempt"
"""


def _killed_holder(lock: Path) -> None:
    env = {**os.environ, "PYTHONPATH": str(SRC)}
    child = subprocess.Popen([sys.executable, "-c", HOLDER, str(lock)], stdout=subprocess.PIPE, text=True, env=env)
    try:
        assert child.stdout is not None and child.stdout.readline().strip() == "acquired"
    finally:
        child.send_signal(signal.SIGKILL)
        child.wait(timeout=10)


@pytest.mark.security
def test_an_attempt_interrupted_by_a_killed_process_still_counts_for_the_interval(tmp_path: Path) -> None:
    """G-1: the attempt started by the killed process is recorded when the gate is taken, so the next process
    waits the minimum interval from then. The kernel releases the lock with the process: no stale lock remains."""
    lock = tmp_path / "gate.lock"
    lock.write_text(f"{time.time() - 3600:.3f} 0\n", encoding="ascii")  # the previous attempt ended long ago
    before = time.time()
    _killed_holder(lock)
    assert float(lock.read_text(encoding="ascii").split()[0]) >= before  # the interrupted attempt is on record
    gate = NetworkGate(lock)
    started = time.monotonic()
    assert gate.acquire(1.0, 5.0) is None
    gate.release()
    assert time.monotonic() - started >= 0.5


@pytest.mark.security
def test_a_killed_holder_never_leaves_the_gate_busy(tmp_path: Path) -> None:
    lock = tmp_path / "gate.lock"
    _killed_holder(lock)
    gate = NetworkGate(lock)
    assert gate.acquire(0.0, 2.0) is None
    gate.release()


@pytest.mark.security
def test_a_recorded_server_wait_holds_for_every_later_process(tmp_path: Path) -> None:
    lock = tmp_path / "gate.lock"
    gate = NetworkGate(lock)
    assert gate.acquire(0.0, 5.0) is None
    gate.release(retry_after_s=120.0)
    other = NetworkGate(lock)
    assert other.acquire(0.1, 2.0) == "DEFERRED_RETRY_AFTER"
    assert NetworkGate(lock).acquire(0.1, 2.0) == "DEFERRED_RETRY_AFTER"


@pytest.mark.security
def test_an_unreadable_gate_record_waits_the_full_interval(tmp_path: Path) -> None:
    lock = tmp_path / "gate.lock"
    lock.write_bytes(b"\xff\xfe garbage")
    gate = NetworkGate(lock)
    started = time.monotonic()
    assert gate.acquire(0.6, 5.0) is None
    gate.release()
    assert time.monotonic() - started >= 0.5
