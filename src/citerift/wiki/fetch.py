"""The only network path of Stage 03: a bounded, throttled, read-only HTTP client for two Wikipedia hosts.

Design (SPECIFICATION.md 8): one request in flight; at least ``min_interval_s`` between the end of one attempt
and the start of the next; at most ``max_attempts`` attempts per operation; a global capture deadline;
Retry-After (seconds or HTTP date) is honored and never shortened; when the next allowed attempt would start
after the deadline the operation ends ``deferred`` with ``not_before``. Bodies are streamed with wire,
decompressed and retained limits. A failure is a recorded attempt, never an answer.

The retry decision is the pure function ``plan_next`` so that the schedule can be simulated
(simulations/stage03) and tested without sockets. The transport is injectable; the default uses urllib with
redirects refused and only the fixed hosts allowed. With the default transport every attempt also passes the
``NetworkGate``, which keeps one request in flight and the minimum interval across processes on this host.
"""

from __future__ import annotations

import email.utils
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol

from citerift.wiki.canonical import StrictJSONError, loads_strict, sha256_hex

HOSTS = {"ar": "ar.wikipedia.org", "en": "en.wikipedia.org"}
USER_AGENT = (
    "CITERIFT-wiki/1.0 (https://github.com/ImanOthman-eng/citerift; read-only research; contact via GitHub issues)"
)
MIB = 1024 * 1024
MAX_FAILURE_BODY = 64 * 1024
RETRYABLE_STATUS = {429: "HTTP_RATE_LIMITED", 502: "HTTP_UNAVAILABLE", 503: "HTTP_UNAVAILABLE", 504: "HTTP_UNAVAILABLE"}
TRANSIENT_API_ERRORS = {"maxlag": "API_MAXLAG", "ratelimited": "API_RATELIMITED"}


@dataclass(frozen=True)
class FetchPolicy:
    """Limits of the network path. Defaults are the frozen values of the protocol (FROZEN_PROTOCOL.md)."""

    min_interval_s: float = 10.0
    max_attempts: int = 3
    op_timeout_s: float = 30.0
    deadline_s: float = 180.0
    backoff_s: float = 10.0
    max_wire_bytes: int = 32 * MIB
    max_body_bytes: int = 32 * MIB
    maxlag_s: int = 5
    user_agent: str = USER_AGENT

    def __post_init__(self) -> None:
        if not (self.min_interval_s >= 0 and self.max_attempts >= 1 and self.op_timeout_s > 0 and self.deadline_s > 0):
            raise ValueError("invalid fetch policy")
        if self.max_wire_bytes < 1 or self.max_body_bytes < 1:
            raise ValueError("invalid fetch policy limits")

    def to_json(self) -> dict[str, Any]:
        return {
            "min_interval_s": self.min_interval_s,
            "max_attempts": self.max_attempts,
            "op_timeout_s": self.op_timeout_s,
            "deadline_s": self.deadline_s,
            "backoff_s": self.backoff_s,
            "max_wire_bytes": self.max_wire_bytes,
            "max_body_bytes": self.max_body_bytes,
            "maxlag_s": self.maxlag_s,
            "user_agent": self.user_agent,
        }


class Clock(Protocol):
    def monotonic(self) -> float: ...
    def now(self) -> datetime: ...
    def sleep(self, seconds: float) -> None: ...


class SystemClock:
    def monotonic(self) -> float:
        return time.monotonic()

    def now(self) -> datetime:
        return datetime.now(UTC)

    def sleep(self, seconds: float) -> None:
        if seconds > 0:
            time.sleep(seconds)


@dataclass
class RawResponse:
    status: int
    headers: dict[str, str]  # lower-case names
    chunks: Iterator[bytes]
    close: Callable[[], None] = lambda: None


class TransportError(Exception):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


Transport = Callable[[str, dict[str, str], float], RawResponse]


def utc_text(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def parse_retry_after(value: str | None, at: datetime) -> tuple[float | None, str | None]:
    """Seconds to wait from ``at``, from delta-seconds or an HTTP date. Returns (seconds, problem)."""
    if value is None:
        return None, None
    text = value.strip()
    if text.isascii() and text.isdigit():
        return float(int(text)), None
    try:
        moment = email.utils.parsedate_to_datetime(text)
    except (TypeError, ValueError, IndexError):
        return None, "RETRY_AFTER_UNREADABLE"
    if moment.tzinfo is None:
        return None, "RETRY_AFTER_UNREADABLE"
    return max(0.0, (moment - at).total_seconds()), None


@dataclass
class Attempt:
    """One request and its outcome. ``code`` is None for an accepted answer."""

    url: str
    number: int
    started_at: str
    started_mono: float
    ended_mono: float
    status: int | None
    code: str | None
    retryable: bool
    retry_after_raw: str | None = None
    retry_after_s: float | None = None
    retry_after_problem: str | None = None
    wire_bytes: int = 0
    body_bytes: int = 0
    body_sha256: str | None = None
    content_type: str | None = None
    detail: str = ""

    def to_json(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "number": self.number,
            "started_at": self.started_at,
            "duration_s": round(self.ended_mono - self.started_mono, 3),
            "status": self.status,
            "code": self.code,
            "retryable": self.retryable,
            "retry_after_raw": self.retry_after_raw,
            "retry_after_s": self.retry_after_s,
            "retry_after_problem": self.retry_after_problem,
            "wire_bytes": self.wire_bytes,
            "body_bytes": self.body_bytes,
            "body_sha256": self.body_sha256,
            "content_type": self.content_type,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class Plan:
    """What to do after the attempts so far: ``retry`` at ``at_mono``, or ``stop`` with ``code``."""

    action: str
    at_mono: float | None = None
    code: str | None = None
    not_before_mono: float | None = None


def plan_next(policy: FetchPolicy, attempts: list[Attempt], start_mono: float) -> Plan:
    """The retry decision (pure). ``start_mono`` is when the capture's global deadline began."""
    if not attempts:
        return Plan("retry", at_mono=start_mono)
    last = attempts[-1]
    if last.code is None:
        return Plan("stop", code=None)
    if not last.retryable:
        return Plan("stop", code=last.code)
    if len(attempts) >= policy.max_attempts:
        return Plan("stop", code="ATTEMPTS_EXHAUSTED")
    wait = policy.min_interval_s
    if last.retry_after_s is not None:
        wait = max(wait, last.retry_after_s)
    else:
        wait = max(wait, policy.backoff_s * (2 ** (len(attempts) - 1)))
    earliest = last.ended_mono + wait
    deadline = start_mono + policy.deadline_s
    if earliest >= deadline:
        if last.retry_after_s is not None:
            return Plan("stop", code="DEFERRED_RETRY_AFTER", not_before_mono=earliest)
        return Plan("stop", code="DEADLINE_EXCEEDED")
    return Plan("retry", at_mono=earliest)


@dataclass
class Answer:
    """The final outcome of one operation: an accepted body or a failure code, and every attempt."""

    url: str
    code: str | None
    attempts: list[Attempt]
    body: bytes | None = None
    headers: dict[str, str] = field(default_factory=dict)
    status: int | None = None
    json: Any = None
    not_before: str | None = None
    failure_bodies: dict[str, bytes] = field(default_factory=dict)


def _classify_status(status: int) -> tuple[str | None, bool]:
    if 200 <= status < 300:
        return None, False
    if status in RETRYABLE_STATUS:
        return RETRYABLE_STATUS[status], True
    if status == 403:
        return "HTTP_FORBIDDEN", False
    if status == 404:
        return "HTTP_NOT_FOUND", False
    if 500 <= status < 600:
        return "HTTP_SERVER_ERROR", True
    return "HTTP_STATUS_UNEXPECTED", False


def _read_body(raw: RawResponse, policy: FetchPolicy, deadline_mono: float, clock: Clock) -> tuple[bytes, int]:
    """Stream the body with wire and decompressed limits. Raises TransportError on any violation."""
    encoding = raw.headers.get("content-encoding", "identity").strip().lower() or "identity"
    if encoding not in ("identity", "gzip"):
        raise TransportError("RESPONSE_ENCODING_UNSUPPORTED", encoding)
    decomp = zlib.decompressobj(16 + zlib.MAX_WBITS) if encoding == "gzip" else None
    out = bytearray()
    wire = 0
    for chunk in raw.chunks:
        wire += len(chunk)
        if wire > policy.max_wire_bytes:
            raise TransportError("RESPONSE_TOO_LARGE", f"wire bytes over {policy.max_wire_bytes}")
        if clock.monotonic() > deadline_mono:
            raise TransportError("DEADLINE_EXCEEDED", "while reading the body")
        if decomp is None:
            out += chunk
        else:
            try:
                room = policy.max_body_bytes - len(out) + 1
                out += decomp.decompress(chunk, room)
                if decomp.unconsumed_tail:
                    raise TransportError("RESPONSE_TOO_LARGE", f"decompressed bytes over {policy.max_body_bytes}")
            except zlib.error as exc:
                raise TransportError("RESPONSE_DECOMPRESSION_FAILED", str(exc)) from exc
        if len(out) > policy.max_body_bytes:
            raise TransportError("RESPONSE_TOO_LARGE", f"body bytes over {policy.max_body_bytes}")
    if decomp is not None:
        if not decomp.eof:
            raise TransportError("RESPONSE_INCOMPLETE", "gzip stream ended early")
        try:
            out += decomp.flush()
        except zlib.error as exc:
            raise TransportError("RESPONSE_DECOMPRESSION_FAILED", str(exc)) from exc
        if len(out) > policy.max_body_bytes:
            raise TransportError("RESPONSE_TOO_LARGE", f"body bytes over {policy.max_body_bytes}")
    announced = raw.headers.get("content-length")
    if announced is not None and announced.strip().isdigit() and int(announced) != wire:
        raise TransportError("RESPONSE_INCOMPLETE", f"content-length {announced}, received {wire}")
    return bytes(out), wire


@dataclass
class _Outcome:
    attempt: Attempt
    body: bytes = b""
    headers: dict[str, str] = field(default_factory=dict)
    json: Any = None


class NetworkGate:
    """Project-wide gate for live requests on this host.

    An exclusive lock on one fixed file (``CITERIFT_WIKI_NETWORK_LOCK``, default
    ``~/.cache/citerift/wiki-network.lock``) is held for the whole attempt, so at most one request is in flight
    across processes; the file holds the wall-clock end of the last attempt of any process, so the minimum interval
    also holds between consecutive captures. POSIX only: without ``fcntl`` live capture fails closed.
    """

    POLL_S = 0.2

    def __init__(self, path: Path) -> None:
        self.path = path
        self._fd: int | None = None

    @classmethod
    def default(cls) -> NetworkGate:
        env = os.environ.get("CITERIFT_WIKI_NETWORK_LOCK")
        return cls(Path(env) if env else Path.home() / ".cache" / "citerift" / "wiki-network.lock")

    def acquire(self, min_interval_s: float, max_wait_s: float) -> str | None:
        """Wait for the gate; return an issue code instead when it cannot be had within ``max_wait_s``."""
        try:
            import fcntl  # noqa: PLC0415 - POSIX only; the gate fails closed elsewhere
        except ImportError:
            return "NETWORK_GATE_UNAVAILABLE"
        try:
            self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            fd = os.open(self.path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
        except OSError:
            return "NETWORK_GATE_UNAVAILABLE"
        start = time.monotonic()
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() - start + self.POLL_S > max_wait_s:
                    os.close(fd)
                    return "NETWORK_GATE_BUSY"
                time.sleep(self.POLL_S)
            except OSError:
                os.close(fd)
                return "NETWORK_GATE_UNAVAILABLE"
        try:
            last_end = float(os.pread(fd, 64, 0).decode("ascii").strip() or 0.0)
        except (OSError, UnicodeDecodeError, ValueError):
            last_end = time.time()  # unreadable record: wait the full interval
        wait = min(max(0.0, last_end + min_interval_s - time.time()), min_interval_s)
        if time.monotonic() - start + wait > max_wait_s:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
            return "NETWORK_GATE_BUSY"
        time.sleep(wait)
        self._fd = fd
        return None

    def release(self) -> None:
        if self._fd is None:
            return
        import fcntl  # noqa: PLC0415 - acquire succeeded, so fcntl exists

        fd, self._fd = self._fd, None
        try:
            os.ftruncate(fd, 0)
            os.pwrite(fd, f"{time.time():.3f}\n".encode("ascii"), 0)
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)


class Fetcher:
    """Executes operations under one FetchPolicy and one global deadline (one capture)."""

    def __init__(
        self,
        policy: FetchPolicy,
        transport: Transport | None = None,
        clock: Clock | None = None,
        gate: NetworkGate | None = None,
    ) -> None:
        self.policy = policy
        self.gate = gate if gate is not None or transport is not None else NetworkGate.default()
        self.transport = transport or urllib_transport
        self.clock = clock or SystemClock()
        self.start_mono = self.clock.monotonic()
        self.last_end_mono: float | None = None
        self.requests = 0

    @staticmethod
    def check_url(url: str) -> str | None:
        parts = urllib.parse.urlsplit(url)
        if parts.scheme != "https" or parts.hostname not in HOSTS.values() or parts.port is not None:
            return "HOST_NOT_ALLOWED"
        if parts.username or parts.password or parts.fragment:
            return "HOST_NOT_ALLOWED"
        return None

    def get(self, url: str, *, expect: str) -> Answer:
        """GET ``url``. ``expect`` is ``json`` (MediaWiki Action API) or ``html``."""
        if code := self.check_url(url):
            return Answer(url, code, [])
        attempts: list[Attempt] = []
        failure_bodies: dict[str, bytes] = {}
        outcome: _Outcome | None = None
        while True:
            plan = plan_next(self.policy, attempts, self.start_mono)
            if plan.action == "stop":
                if plan.code is None and outcome is not None:
                    return Answer(
                        url,
                        None,
                        attempts,
                        body=outcome.body,
                        headers=outcome.headers,
                        status=outcome.attempt.status,
                        json=outcome.json,
                        failure_bodies=failure_bodies,
                    )
                not_before = None
                if plan.not_before_mono is not None:
                    delta = plan.not_before_mono - self.clock.monotonic()
                    not_before = utc_text(self.clock.now() + timedelta(seconds=max(0.0, delta)))
                last_json = outcome.json if outcome is not None else None
                return Answer(
                    url, plan.code, attempts, json=last_json, not_before=not_before, failure_bodies=failure_bodies
                )
            at = plan.at_mono if plan.at_mono is not None else self.clock.monotonic()
            if self.last_end_mono is not None:
                at = max(at, self.last_end_mono + self.policy.min_interval_s)
            deadline = self.start_mono + self.policy.deadline_s
            if at >= deadline:
                return Answer(url, "DEADLINE_EXCEEDED", attempts, failure_bodies=failure_bodies)
            self.clock.sleep(at - self.clock.monotonic())
            if self.gate is not None and (code := self.gate.acquire(self.policy.min_interval_s, deadline - at)):
                return Answer(url, code, attempts, failure_bodies=failure_bodies)
            try:
                outcome = self._attempt(url, len(attempts) + 1, expect, deadline)
            finally:
                if self.gate is not None:
                    self.gate.release()
            attempts.append(outcome.attempt)
            self.last_end_mono = outcome.attempt.ended_mono
            failed = outcome.attempt
            if failed.code is not None and failed.body_sha256 and 0 < len(outcome.body) <= MAX_FAILURE_BODY:
                failure_bodies[failed.body_sha256] = outcome.body  # kept whole, or not at all

    def _attempt(self, url: str, number: int, expect: str, deadline: float) -> _Outcome:
        clock = self.clock
        started_mono = clock.monotonic()
        att = Attempt(url, number, utc_text(clock.now()), started_mono, started_mono, None, None, False)
        out = _Outcome(att)
        timeout = min(self.policy.op_timeout_s, deadline - started_mono)
        headers = {"User-Agent": self.policy.user_agent, "Accept-Encoding": "gzip"}
        headers["Accept"] = "application/json" if expect == "json" else "text/html"
        self.requests += 1
        try:
            raw = self.transport(url, headers, timeout)
        except TransportError as exc:
            att.ended_mono = clock.monotonic()
            att.code, att.detail = exc.code, exc.detail
            att.retryable = exc.code in ("HTTP_TIMEOUT", "HTTP_CONNECTION_FAILED")
            return out
        try:
            att.status = raw.status
            att.content_type = raw.headers.get("content-type")
            att.retry_after_raw = raw.headers.get("retry-after")
            att.retry_after_s, att.retry_after_problem = parse_retry_after(att.retry_after_raw, clock.now())
            op_deadline = min(deadline, started_mono + self.policy.op_timeout_s)
            body, att.wire_bytes = _read_body(raw, self.policy, op_deadline, clock)
        except TransportError as exc:
            att.ended_mono = clock.monotonic()
            att.code, att.detail = exc.code, exc.detail
            att.retryable = exc.code in ("RESPONSE_INCOMPLETE", "DEADLINE_EXCEEDED", "HTTP_TIMEOUT")
            return out
        finally:
            raw.close()
        att.ended_mono = clock.monotonic()
        att.body_bytes = len(body)
        att.body_sha256 = sha256_hex(body)
        out.body = body
        code, retryable = _classify_status(raw.status)
        if code is not None:
            att.code, att.retryable = code, retryable
            return out
        ctype = (att.content_type or "").split(";")[0].strip().lower()
        if expect == "json":
            if ctype != "application/json":
                att.code, att.detail = "RESPONSE_CONTENT_TYPE", ctype
                return out
            try:
                data = loads_strict(body)
            except StrictJSONError as exc:
                att.code, att.retryable, att.detail = "RESPONSE_NOT_JSON", True, str(exc)
                return out
            out.json = data
            err = data.get("error") if isinstance(data, dict) else None
            if isinstance(err, dict):
                api_code = str(err.get("code", ""))
                att.code = TRANSIENT_API_ERRORS.get(api_code, "API_ERROR")
                att.retryable = api_code in TRANSIENT_API_ERRORS
                att.detail = api_code
                return out
        elif ctype != "text/html":
            att.code, att.detail = "RESPONSE_CONTENT_TYPE", ctype
            return out
        out.headers = dict(raw.headers)
        return out


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def urllib_transport(url: str, headers: dict[str, str], timeout: float) -> RawResponse:
    """Default transport: urllib, redirects refused, body streamed in 64 KiB chunks."""
    req = urllib.request.Request(url, headers=headers, method="GET")  # noqa: S310 - https to the fixed hosts only
    try:
        resp = _OPENER.open(req, timeout=max(0.001, timeout))
    except urllib.error.HTTPError as exc:
        resp = exc
    except TimeoutError as exc:
        raise TransportError("HTTP_TIMEOUT", str(exc)) from exc
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, TimeoutError):
            raise TransportError("HTTP_TIMEOUT", str(exc.reason)) from exc
        raise TransportError("HTTP_CONNECTION_FAILED", str(exc.reason)[:200]) from exc
    except OSError as exc:
        raise TransportError("HTTP_CONNECTION_FAILED", str(exc)[:200]) from exc
    hdrs = {k.lower(): v for k, v in resp.headers.items()}

    def chunks() -> Iterator[bytes]:
        while True:
            try:
                block = resp.read(65536)
            except TimeoutError as exc:
                raise TransportError("HTTP_TIMEOUT", "read timed out") from exc
            except OSError as exc:
                raise TransportError("RESPONSE_INCOMPLETE", str(exc)[:200]) from exc
            if not block:
                return
            yield block

    return RawResponse(resp.status if hasattr(resp, "status") else resp.code, hdrs, chunks(), resp.close)
