"""Stage 03 acquisition simulation (SIMULATION_REPORT.md 2): the fetch policy under scripted fault sequences.

An independent reference model of the retry schedule, written from SPECIFICATION.md 8 without calling the
production planner, predicts for each scripted sequence the number of attempts, the final code and the earliest
start of each attempt. The production Fetcher (src/citerift/wiki/fetch.py) is then driven with a simulated clock
and a scripted transport, and both its outcome and a set of invariants are checked:

  I1  an attempt never starts before the previous attempt's end plus min_interval_s;
  I2  an attempt never starts before the previous response's Retry-After has passed (never shortened);
  I3  at most max_attempts attempts per operation;
  I4  no attempt starts at or after the global deadline;
  I5  an answer is returned only when the last attempt was accepted, and then it carries the body;
  I6  a failure never carries a body or a parsed JSON answer as its result;
  I7  a deferred result's not_before is at least the last response time plus its Retry-After, and is past
      the deadline; a non-retryable code stops at once.

Usage: python simulations/stage03/fetch_policy_sim.py [N_SEQUENCES] [SEED]  (prints a JSON summary)
"""

from __future__ import annotations

import gzip
import json
import random
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from citerift.wiki.fetch import Fetcher, FetchPolicy, RawResponse, TransportError

EPOCH = datetime(2026, 10, 28, 12, 0, 0, tzinfo=UTC)


class SimClock:
    def __init__(self) -> None:
        self.t = 1000.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.t

    def now(self) -> datetime:
        return EPOCH + timedelta(seconds=self.t)

    def sleep(self, seconds: float) -> None:
        if seconds > 0:
            self.sleeps.append(seconds)
            self.t += seconds


@dataclass
class Step:
    """One scripted response. ``kind``: ok, http, maxlag, api_error, timeout, bad_json, huge, gzip_bomb."""

    kind: str
    status: int = 200
    retry_after: str | None = None  # header text as sent
    retry_after_s: float | None = None  # its meaning in seconds, for the reference model
    duration: float = 0.5


@dataclass
class Trace:
    starts: list[float] = field(default_factory=list)
    ends: list[float] = field(default_factory=list)


class ScriptedTransport:
    def __init__(self, steps: list[Step], clock: SimClock, trace: Trace) -> None:
        self.steps = list(steps)
        self.clock = clock
        self.trace = trace
        self.overrun = False

    def __call__(self, url: str, headers: dict[str, str], timeout: float) -> RawResponse:
        self.trace.starts.append(self.clock.t)
        if not self.steps:
            self.overrun = True
            self.trace.ends.append(self.clock.t)
            raise TransportError("HTTP_CONNECTION_FAILED", "attempt beyond the reference schedule")
        step = self.steps.pop(0)
        if step.kind == "timeout":
            self.clock.t += min(step.duration, timeout)
            self.trace.ends.append(self.clock.t)
            raise TransportError("HTTP_TIMEOUT", "simulated")
        self.clock.t += step.duration
        self.trace.ends.append(self.clock.t)
        hdrs = {"content-type": "application/json; charset=utf-8"}
        if step.retry_after is not None:
            hdrs["retry-after"] = step.retry_after
        if step.kind == "ok":
            body = b'{"batchcomplete":true,"query":{}}'
        elif step.kind == "maxlag":
            body = b'{"error":{"code":"maxlag","info":"lagged"}}'
        elif step.kind == "api_error":
            body = b'{"error":{"code":"nosuchrevid","info":"no"}}'
        elif step.kind == "bad_json":
            body = b'{"query": '
        elif step.kind == "huge":
            body = b"x" * 2048
        elif step.kind == "gzip_bomb":
            body = gzip.compress(b"0" * 4096)
            hdrs["content-encoding"] = "gzip"
        else:
            body = b"Too many requests"
            hdrs["content-type"] = "text/plain"

        def chunks() -> Iterator[bytes]:
            yield body

        return RawResponse(step.status, hdrs, chunks())


def reference(policy: FetchPolicy, steps: list[Step], start: float) -> dict[str, Any]:
    """The schedule the specification prescribes, computed independently of the production planner."""
    accept = {"ok"}
    retryable_kinds = {"timeout", "maxlag", "bad_json"}
    t = start
    prev_end = None
    deadline = start + policy.deadline_s
    expected_starts: list[float] = []
    for attempts, step in enumerate(steps, start=1):
        expected_starts.append(t)
        end = t + (min(step.duration, policy.op_timeout_s) if step.kind == "timeout" else step.duration)
        if step.kind in accept:
            return {"attempts": attempts, "code": None, "starts": expected_starts}
        if step.kind == "http":
            retryable = step.status in (429, 502, 503, 504) or 500 <= step.status < 600
            code = {429: "HTTP_RATE_LIMITED", 403: "HTTP_FORBIDDEN", 404: "HTTP_NOT_FOUND"}.get(step.status)
            if code is None:
                code = "HTTP_UNAVAILABLE" if step.status in (502, 503, 504) else "HTTP_SERVER_ERROR"
        elif step.kind in ("huge", "gzip_bomb"):
            retryable, code = False, "RESPONSE_TOO_LARGE"
        elif step.kind == "api_error":
            retryable, code = False, "API_ERROR"
        else:
            retryable = step.kind in retryable_kinds
            code = {"timeout": "HTTP_TIMEOUT", "maxlag": "API_MAXLAG", "bad_json": "RESPONSE_NOT_JSON"}[step.kind]
        if not retryable:
            return {"attempts": attempts, "code": code, "starts": expected_starts}
        if attempts >= policy.max_attempts:
            return {"attempts": attempts, "code": "ATTEMPTS_EXHAUSTED", "starts": expected_starts}
        if step.retry_after_s is not None:
            wait = max(policy.min_interval_s, step.retry_after_s)
        else:
            wait = max(policy.min_interval_s, policy.backoff_s * 2 ** (attempts - 1))
        nxt = end + wait
        if nxt >= deadline:
            code = "DEFERRED_RETRY_AFTER" if step.retry_after_s is not None else "DEADLINE_EXCEEDED"
            return {"attempts": attempts, "code": code, "starts": expected_starts, "not_before": nxt}
        prev_end = end
        t = nxt
    del prev_end
    raise AssertionError("script too short")


def random_step(rng: random.Random, clock_base: datetime) -> Step:
    kind = rng.choices(
        ["ok", "http", "maxlag", "api_error", "timeout", "bad_json", "huge", "gzip_bomb"],
        weights=[30, 35, 10, 3, 10, 5, 2, 2],
    )[0]
    step = Step(kind, duration=round(rng.uniform(0.05, 4.0), 3))
    if kind == "http":
        step.status = rng.choice([429, 429, 429, 503, 502, 500, 403, 404])
    if kind in ("http", "maxlag") and rng.random() < 0.7:
        seconds = rng.choice([0, 1, 5, 6, 30, 90, 200, 400])
        if rng.random() < 0.3:
            # HTTP date form; the reference meaning is relative to the response time, which the script knows.
            step.retry_after = "DATE"
        else:
            step.retry_after = str(seconds)
        step.retry_after_s = float(seconds)
    if kind == "timeout":
        step.duration = rng.choice([1.0, 30.0, 45.0])
    return step


def run(n: int, seed: int) -> dict[str, Any]:
    rng = random.Random(seed)
    policy = FetchPolicy(
        min_interval_s=10.0,
        max_attempts=3,
        op_timeout_s=30.0,
        deadline_s=180.0,
        backoff_s=10.0,
        max_wire_bytes=1024,
        max_body_bytes=1024,
    )
    failures: list[dict[str, Any]] = []
    outcomes: dict[str, int] = {}
    for case in range(n):
        steps = [random_step(rng, EPOCH) for _ in range(policy.max_attempts)]
        clock = SimClock()
        trace = Trace()
        # Resolve HTTP-date Retry-After headers against the simulated response time (end of that attempt).
        fixed: list[Step] = []
        exp = reference(policy, steps, clock.t)
        transport_steps = []
        sim_t = clock.t
        for i, planned in enumerate(steps[: exp["attempts"]]):
            st = planned
            sim_t = exp["starts"][i] + (min(st.duration, policy.op_timeout_s) if st.kind == "timeout" else st.duration)
            if st.retry_after == "DATE" and st.retry_after_s is not None:
                # HTTP dates have one-second resolution: round the meaning up so the header never shortens it.
                moment = EPOCH + timedelta(seconds=sim_t + st.retry_after_s)
                moment = moment.replace(microsecond=0) + (timedelta(seconds=1) if moment.microsecond else timedelta())
                st = Step(
                    st.kind,
                    st.status,
                    format_datetime(moment, usegmt=True),
                    (moment - (EPOCH + timedelta(seconds=sim_t))).total_seconds(),
                    st.duration,
                )
            transport_steps.append(st)
            fixed.append(st)
        exp = reference(policy, fixed + steps[len(fixed) :], clock.t)
        transport = ScriptedTransport(transport_steps, clock, trace)
        fetcher = Fetcher(policy, transport, clock)
        ans = fetcher.get("https://en.wikipedia.org/w/api.php?action=query", expect="json")
        problems = ["attempt beyond the reference schedule"] if transport.overrun else []
        if len(ans.attempts) != exp["attempts"]:
            problems.append(f"attempts {len(ans.attempts)} != expected {exp['attempts']}")
        if ans.code != exp["code"]:
            problems.append(f"code {ans.code} != expected {exp['code']}")
        for i in range(1, len(trace.starts)):
            prev = ans.attempts[i - 1]
            if trace.starts[i] < trace.ends[i - 1] + policy.min_interval_s - 1e-9:
                problems.append("I1 min interval")
            if prev.retry_after_s is not None and trace.starts[i] < trace.ends[i - 1] + prev.retry_after_s - 1e-9:
                problems.append("I2 retry-after shortened")
        if len(trace.starts) > policy.max_attempts:
            problems.append("I3 attempts")
        if any(s >= 1000.0 + policy.deadline_s for s in trace.starts):
            problems.append("I4 deadline")
        if ans.code is None and (ans.body is None or ans.attempts[-1].code is not None):
            problems.append("I5 answer without accepted attempt")
        if ans.code is not None and ans.body is not None:
            problems.append("I6 failure carries a body")
        if ans.code == "DEFERRED_RETRY_AFTER":
            last = ans.attempts[-1]
            nb = datetime.strptime(ans.not_before or "", "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=UTC)
            if nb < EPOCH + timedelta(seconds=trace.ends[-1] + (last.retry_after_s or 0)) - timedelta(milliseconds=1):
                problems.append("I7 not_before too early")
            if nb < EPOCH + timedelta(seconds=1000.0 + policy.deadline_s):
                problems.append("I7 deferred before the deadline")
        outcomes[str(ans.code)] = outcomes.get(str(ans.code), 0) + 1
        if problems:
            failures.append({"case": case, "problems": problems, "steps": [s.__dict__ for s in fixed]})
    return {
        "sequences": n,
        "seed": seed,
        "outcomes": dict(sorted(outcomes.items())),
        "failures": failures[:20],
        "failure_count": len(failures),
    }


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 20261028
    result = run(n, seed)
    print(json.dumps(result, indent=1, sort_keys=True))
    sys.exit(1 if result["failure_count"] else 0)
