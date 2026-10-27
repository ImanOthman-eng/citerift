"""Bounded Crossref corroboration and its replay bundle (SPECIFICATION.md section 9).

Retrieval is a separate, explicit preparation step (``citerift-rde enrich``); building and querying never
open a socket. Every request outcome is recorded; a failed request is a failure, never evidence that a
relation is absent. The transport, clock and sleep are injectable so that every failure mode is tested
with doubles.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol

from citerift.contracts.formats import loads_strict
from citerift.retraction.canonical import canonical
from citerift.retraction.identifiers import normalize_doi
from citerift.retraction.source import ImportFailure

CLIENT_VERSION = "citerift-rde-crossref/1.0.0"
MANIFEST_VERSION = "1.0.0"
API_BASE = "https://api.crossref.org/works/"
CHANNEL = "crossref-rest-api"
USER_AGENT = "citerift-rde/1.0 (https://github.com/ImanOthman-eng/citerift; research integrity tool)"
TYPE_MAP = {
    "retraction": "retracted",
    "correction": "correction",
    "corrigendum": "correction",
    "erratum": "correction",
    "expression_of_concern": "expression_of_concern",
    "reinstatement": "reinstated",
}
FAILURES = (
    "TIMEOUT",
    "RATE_LIMITED",
    "ACCESS_DENIED",
    "SERVER_ERROR",
    "HTTP_ERROR",
    "CONNECTION_ERROR",
    "PAYLOAD_TOO_LARGE",
    "INVALID_JSON",
    "SCHEMA_INVALID",
    "DOI_MISMATCH",
    "DEFERRED_BUDGET",
)


@dataclass(frozen=True)
class Limits:
    max_works: int = 40
    max_attempts: int = 80
    min_interval: float = 1.0
    timeout: float = 10.0
    per_work: float = 30.0
    per_run: float = 600.0
    max_bytes: int = 4 * 1024 * 1024
    retries: int = 2
    backoff: tuple[float, ...] = (2.0, 4.0)


@dataclass(frozen=True)
class Response:
    status: int
    headers: dict[str, str]  # lower-case names
    body: bytes
    truncated: bool = False  # more than max_bytes were available


class TransportTimeout(Exception):
    pass


class TransportConnectionError(Exception):
    pass


class Transport(Protocol):
    def get(self, url: str, timeout: float, max_bytes: int) -> Response: ...


class UrllibTransport:
    """The real transport: one HTTPS GET with a read cap. Redirects are followed by urllib (Crossref sends none)."""

    def get(self, url: str, timeout: float, max_bytes: int) -> Response:
        if not url.startswith(API_BASE):
            raise ValueError(f"refusing a request outside {API_BASE}")
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})  # noqa: S310
        try:
            with urllib.request.urlopen(request, timeout=timeout) as resp:  # noqa: S310
                body = resp.read(max_bytes + 1)
                headers = {k.lower(): v for k, v in resp.headers.items()}
                return Response(resp.status, headers, body[:max_bytes], len(body) > max_bytes)
        except urllib.error.HTTPError as exc:
            headers = {k.lower(): v for k, v in exc.headers.items()} if exc.headers else {}
            return Response(exc.code, headers, b"")
        except TimeoutError as exc:
            raise TransportTimeout(str(exc)) from None
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise TransportTimeout(str(exc.reason)) from None
            raise TransportConnectionError(str(exc.reason)) from None
        except OSError as exc:
            raise TransportConnectionError(str(exc)) from None


def _utc_now() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def work_url(doi_key: str) -> str:
    return API_BASE + urllib.parse.quote(doi_key, safe="")


class PayloadProblem(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


def check_payload(body: bytes, doi_key: str) -> dict[str, Any]:
    """Validate a work payload; raise PayloadProblem(INVALID_JSON | SCHEMA_INVALID | DOI_MISMATCH)."""
    try:
        data = loads_strict(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise PayloadProblem("INVALID_JSON", str(exc)[:200]) from None
    if not isinstance(data, dict) or data.get("status") != "ok" or data.get("message-type") != "work":
        raise PayloadProblem("SCHEMA_INVALID", "expected status 'ok' and message-type 'work'")
    message = data.get("message")
    if not isinstance(message, dict) or not isinstance(message.get("DOI"), str):
        raise PayloadProblem("SCHEMA_INVALID", "message.DOI missing")
    got = normalize_doi(message["DOI"])
    if got.normalized != doi_key:
        raise PayloadProblem("DOI_MISMATCH", f"requested {doi_key}, payload {message['DOI'][:200]}")
    updated_by = message.get("updated-by", [])
    if not isinstance(updated_by, list) or not all(
        isinstance(u, dict) and isinstance(u.get("DOI"), str) and isinstance(u.get("type"), str) for u in updated_by
    ):
        raise PayloadProblem("SCHEMA_INVALID", "updated-by entries need string DOI and type")
    if "type" in message and not isinstance(message["type"], str):
        raise PayloadProblem("SCHEMA_INVALID", "message.type is not a string")
    return data


@dataclass
class WorkRecord:
    doi: str
    url: str
    outcome: str = "failed"
    failure: str | None = None
    http_status: int | None = None
    attempts: int = 0
    retrieved_at: str | None = None
    payload_sha256: str | None = None
    bytes: int | None = None
    waits: list[float] = field(default_factory=list)


def _header_float(headers: dict[str, str], name: str) -> float | None:
    value = headers.get(name)
    if value is None:
        return None
    try:
        number = float(value.strip().rstrip("s"))
    except ValueError:
        return None
    return number if number >= 0 else None


def _spacing(headers: dict[str, str], current: float) -> float:
    """Minimum spacing between request starts from x-rate-limit-limit / x-rate-limit-interval."""
    limit = _header_float(headers, "x-rate-limit-limit")
    interval = _header_float(headers, "x-rate-limit-interval")
    if limit and interval:
        return max(current, interval / limit)
    return current


def enrich(
    dois: list[str],
    out_dir: Path,
    *,
    transport: Transport | None = None,
    limits: Limits = Limits(),  # noqa: B008
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], str] = _utc_now,
) -> dict[str, Any]:
    """Fetch up to ``limits.max_works`` works and write a replay bundle (manifest.json and payloads/)."""
    transport = transport or UrllibTransport()
    keys: list[str] = []
    rejected: list[dict[str, Any]] = []
    for raw in dois:
        norm = normalize_doi(raw)
        if norm.normalized is None:
            rejected.append({"raw": raw, "issues": list(norm.issues)})
        elif norm.normalized not in keys:
            keys.append(norm.normalized)
    over = keys[limits.max_works :]
    keys = keys[: limits.max_works]
    payload_dir = out_dir / "payloads"
    payload_dir.mkdir(parents=True, exist_ok=True)
    run_start = clock()
    last_start: float | None = None
    spacing = limits.min_interval
    attempts_total = 0
    stopped: str | None = None
    works: list[WorkRecord] = []
    started_at = now()
    for key in keys:
        rec = WorkRecord(key, work_url(key))
        works.append(rec)
        if stopped:
            rec.failure = "DEFERRED_BUDGET"
            continue
        work_start = clock()
        retry = 0
        while True:
            if attempts_total >= limits.max_attempts:
                rec.failure = "DEFERRED_BUDGET"
                break
            wait = 0.0 if last_start is None else max(0.0, last_start + spacing - clock())
            if rec.waits:
                wait = max(wait, rec.waits[-1])
            elapsed_work = clock() - work_start
            elapsed_run = clock() - run_start
            if (
                elapsed_work + wait + limits.timeout > limits.per_work
                or elapsed_run + wait + limits.timeout > limits.per_run
            ):
                rec.failure = "DEFERRED_BUDGET"
                break
            if wait > 0:
                sleep(wait)
            last_start = clock()
            attempts_total += 1
            rec.attempts += 1
            rec.retrieved_at = now()
            transient: str | None = None
            retry_after: float | None = None
            try:
                resp = transport.get(rec.url, limits.timeout, limits.max_bytes)
            except TransportTimeout:
                transient = "TIMEOUT"
            except TransportConnectionError:
                transient = "CONNECTION_ERROR"
            else:
                rec.http_status = resp.status
                spacing = _spacing(resp.headers, spacing)
                if resp.status == 403:
                    rec.failure, stopped = "ACCESS_DENIED", "ACCESS_DENIED"
                    break
                if resp.status == 429:
                    transient = "RATE_LIMITED"
                    retry_after = _header_float(resp.headers, "retry-after")
                elif resp.status >= 500:
                    transient = "SERVER_ERROR"
                elif resp.status != 200:
                    rec.failure = "HTTP_ERROR"
                    break
                elif resp.truncated or len(resp.body) > limits.max_bytes:
                    rec.failure = "PAYLOAD_TOO_LARGE"
                    break
                else:
                    try:
                        check_payload(resp.body, key)
                    except PayloadProblem as exc:
                        rec.failure = exc.code
                        break
                    sha = hashlib.sha256(resp.body).hexdigest()
                    (payload_dir / f"{sha}.json").write_bytes(resp.body)
                    rec.outcome, rec.failure, rec.payload_sha256, rec.bytes = "ok", None, sha, len(resp.body)
                    break
            if retry >= limits.retries:
                rec.failure = transient
                break
            backoff = limits.backoff[min(retry, len(limits.backoff) - 1)]
            rec.waits.append(max(backoff, retry_after or 0.0))
            retry += 1
    finished_at = now()
    manifest = {
        "manifest_version": MANIFEST_VERSION,
        "client_version": CLIENT_VERSION,
        "endpoint": API_BASE + "{doi}",
        "limits": {k: list(v) if isinstance(v, tuple) else v for k, v in asdict(limits).items()},
        "started_at": started_at,
        "finished_at": finished_at,
        "elapsed_seconds": round(clock() - run_start, 3),
        "requests": attempts_total,
        "stopped": stopped,
        "rejected_inputs": rejected,
        "not_requested_over_work_limit": over,
        "works": [{k: v for k, v in asdict(w).items()} for w in works],
        "note": "A failed or deferred work is not evidence that a relation is absent.",
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", "utf-8")
    return manifest


# Replay -----------------------------------------------------------------------------------------------


def _origin(source: Any) -> tuple[str, list[str]]:
    if source == "retraction-watch":
        return "retraction-watch", ["retraction-watch"]
    if source == "publisher":
        return "publisher", []
    return "unknown", []


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        data = loads_strict(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ImportFailure("CORROBORATION_INVALID", f"manifest unreadable: {exc}") from None
    if not isinstance(data, dict) or data.get("manifest_version") != MANIFEST_VERSION:
        raise ImportFailure("CORROBORATION_INVALID", "manifest_version is not 1.0.0")
    works = data.get("works")
    if not isinstance(works, list):
        raise ImportFailure("CORROBORATION_INVALID", "works is not a list")
    seen: set[str] = set()
    for w in works:
        if not isinstance(w, dict) or not isinstance(w.get("doi"), str) or w.get("outcome") not in ("ok", "failed"):
            raise ImportFailure("CORROBORATION_INVALID", "malformed work entry")
        if normalize_doi(w["doi"]).normalized != w["doi"]:
            raise ImportFailure("CORROBORATION_INVALID", f"work DOI is not a normalized key: {w['doi'][:200]}")
        if w["doi"] in seen:
            raise ImportFailure("CORROBORATION_INVALID", f"work {w['doi']} listed twice")
        seen.add(w["doi"])
        if w["outcome"] == "failed" and w.get("failure") not in FAILURES:
            raise ImportFailure("CORROBORATION_INVALID", f"unknown failure reason {w.get('failure')!r}")
        if w["outcome"] == "ok" and not isinstance(w.get("retrieved_at"), str):
            raise ImportFailure("CORROBORATION_INVALID", "successful work without retrieved_at")
    return data


def replay_assertions(manifest: dict[str, Any], base: Path) -> tuple[list[tuple[Any, ...]], list[dict[str, Any]]]:
    """Verify every payload hash and return (attempt rows, assertion dicts) without touching a database."""
    attempts: list[tuple[Any, ...]] = []
    assertions: list[dict[str, Any]] = []
    for w in manifest["works"]:
        sha = w.get("payload_sha256")
        attempts.append(
            (
                f"cra-{hashlib.sha256(canonical([w['doi'], w.get('retrieved_at'), sha]).encode()).hexdigest()[:16]}",
                w["doi"],
                w.get("url") or work_url(w["doi"]),
                w["outcome"],
                w.get("failure"),
                w.get("http_status"),
                w.get("retrieved_at") or manifest.get("started_at") or "",
                sha,
                w.get("bytes"),
                int(w.get("attempts") or 0),
                CHANNEL,
            )
        )
        if w["outcome"] != "ok":
            continue
        if not isinstance(sha, str) or len(sha) != 64:
            raise ImportFailure("CORROBORATION_INVALID", f"work {w['doi']} has no payload hash")
        path = base / "payloads" / f"{sha}.json"
        try:
            body = path.read_bytes()
        except OSError as exc:
            raise ImportFailure("CORROBORATION_INVALID", f"payload missing: {exc}") from None
        if hashlib.sha256(body).hexdigest() != sha or (w.get("bytes") is not None and len(body) != w["bytes"]):
            raise ImportFailure("CORROBORATION_INVALID", f"payload hash or size mismatch for {w['doi']}")
        try:
            data = check_payload(body, w["doi"])
        except PayloadProblem as exc:
            raise ImportFailure("CORROBORATION_INVALID", f"payload of {w['doi']}: {exc}") from None
        message = data["message"]
        common = {
            "origin_doi": w["doi"],
            "retrieved_at": w["retrieved_at"],
            "locator": w.get("url") or work_url(w["doi"]),
            "payload_sha256": sha,
            "channel": CHANNEL,
        }
        for i, entry in enumerate(message.get("updated-by", [])):
            nd = normalize_doi(entry["DOI"]).normalized
            origin, depends = _origin(entry.get("source"))
            assertions.append(
                {
                    **common,
                    "assertion_id": f"cr-{sha[:16]}-u{i}",
                    "predicate": "update_relation",
                    "original_doi": w["doi"],
                    "notice_doi": nd,
                    "notice_key": f"doi:{nd}" if nd is not None and nd != w["doi"] else None,
                    "relation_type": entry["type"],
                    "mapped_type": TYPE_MAP.get(entry["type"]),
                    "label": entry.get("label") if isinstance(entry.get("label"), str) else None,
                    "source_label": entry.get("source") if isinstance(entry.get("source"), str) else None,
                    "origin": origin,
                    "depends_on": depends,
                    "pointer": f"/message/updated-by/{i}",
                    "record_id_raw": None if entry.get("record-id") is None else str(entry.get("record-id")),
                    "updated_raw": entry.get("updated"),
                }
            )
        assertions.append(
            {
                **common,
                "assertion_id": f"cr-{sha[:16]}-w",
                "predicate": "notice_record_exists",
                "original_doi": None,
                "notice_doi": w["doi"],
                "notice_key": f"doi:{w['doi']}",
                "relation_type": None,
                "mapped_type": None,
                "label": message.get("type"),
                "source_label": None,
                "origin": "crossref",
                "depends_on": [],
                "pointer": "/message",
                "record_id_raw": None,
                "updated_raw": None,
            }
        )
    return attempts, assertions


def ingest_replay(conn: sqlite3.Connection, manifest_path: Path) -> dict[str, Any]:
    """Load a replay bundle into ``cr_attempt`` and ``cr_assertion`` (inside the build transaction).

    ``update_relation`` assertions are kept for works that are originals of the snapshot;
    ``notice_record_exists`` only for works that are notice DOIs of the snapshot. A replay is not a new
    retrieval: the original ``retrieved_at`` is kept.
    """
    manifest = load_manifest(manifest_path)
    attempts, assertions = replay_assertions(manifest, manifest_path.parent)
    conn.executemany("INSERT INTO cr_attempt VALUES (?,?,?,?,?,?,?,?,?,?,?)", attempts)
    kept = 0
    for a in assertions:
        if a["predicate"] == "update_relation":
            role_hit = conn.execute("SELECT 1 FROM event WHERE original_doi = ? LIMIT 1", (a["original_doi"],))
        else:
            role_hit = conn.execute("SELECT 1 FROM event WHERE notice_doi = ? LIMIT 1", (a["notice_doi"],))
        if role_hit.fetchone() is None:
            continue
        conn.execute(
            "INSERT INTO cr_assertion VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                a["assertion_id"],
                a["predicate"],
                a["original_doi"],
                a["notice_doi"],
                a["notice_key"],
                a["relation_type"],
                a["mapped_type"],
                a["label"],
                a["source_label"],
                a["origin"],
                a["channel"],
                canonical(a["depends_on"]),
                a["retrieved_at"],
                a["locator"],
                a["payload_sha256"],
                a["pointer"],
                a["record_id_raw"],
                None if a["updated_raw"] is None else canonical(a["updated_raw"]),
            ),
        )
        kept += 1
    manifest_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    return {
        "manifests": [
            {
                "manifest_sha256": manifest_sha,
                "client_version": manifest.get("client_version"),
                "started_at": manifest.get("started_at"),
                "works": len(manifest["works"]),
                "works_ok": sum(w["outcome"] == "ok" for w in manifest["works"]),
                "works_failed": sum(w["outcome"] != "ok" for w in manifest["works"]),
                "assertions_kept": kept,
                "stopped": manifest.get("stopped"),
            }
        ]
    }
