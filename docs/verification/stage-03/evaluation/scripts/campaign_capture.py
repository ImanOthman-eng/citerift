"""Resumable capture driver for the 2026-11-02 confirmation campaign (owner instruction D-034, section 5, R8).

Usage: python campaign_capture.py PLAN_JSON OUT_DIR

PLAN_JSON is ``{"campaign": NAME, "articles": [{"split": S, "wiki": "ar"|"en", "page_id": N}, ...]}``, in capture
order. Reserve blocks are appended to the plan only after a locked reserve decision; keys already in the state are
never captured again.

Each run is the production ``citerift-wiki capture --wiki W --page-id N --out OUT_DIR/bundles/<split>/<wiki>-<page
id>-a<n>``. Every request goes through the project network gate, which also holds every server-requested
``not_before`` across processes. The driver adds what the earlier one-shot scripts lacked:

- **Durable state.** A ``start`` line is appended (and fsynced) to OUT_DIR/captures.jsonl before each run and an
  ``end`` line after it. OUT_DIR/capture_states.json is rewritten atomically after each run.
- **Recovery.**
  - A run with a ``start`` line and no ``end`` line was interrupted. It is recorded as such and charged at its worst
    case against the ceilings.
  - An ``end`` line that is missing from the state (a crash before the state was saved) is adopted.
  - Run numbers continue after every number seen in the state, the log or the bundle directory, so an existing
    bundle path is never reused.
- **No duplicate workers.** An exclusive non-blocking lock on OUT_DIR/driver.lock. A second driver exits 3 without
  any request.
- **Ceilings.** Before every run, the HTTP attempts and accepted body bytes already recorded must leave room for the
  worst case of one more run (2 operations x 3 attempts; source, API envelope and HTML limits). Otherwise the driver
  writes OUT_DIR/ceiling.json and exits 2.
- **Bounded retries.** An article gets at most MAX_RUNS runs. A run is followed by another only when it was
  deferred (whole capture, or the render), interrupted, or failed with retryable codes only; the last case at most
  once. A complete capture is never repeated.
- **Deferral.** The next run of a deferred article starts no earlier than its ``not_before`` plus one second. A
  wait of up to MAX_INLINE_WAIT_S is slept; a longer one leaves the article pending. The driver then finishes the
  other articles and exits 4, printing the earliest ``not_before``. Rerunning the same command after that time
  resumes it: a deterministic manual resume, with no scheduler.

Exit codes: 0 every article resolved; 2 ceiling reached; 3 another driver holds the lock; 4 deferred articles
pending.
"""

from __future__ import annotations

import fcntl
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MAX_HTTP_ATTEMPTS = 500
MAX_ACCEPTED_BYTES = 300 * 1024 * 1024
RUN_WORST_ATTEMPTS = 2 * 3
RUN_WORST_BYTES = 4 * 1024 * 1024 + 64 * 1024 + 16 * 1024 * 1024
MAX_RUNS = 4
MAX_INLINE_WAIT_S = 600.0
# Recorded times have microsecond resolution; the next run starts at least this long after a not_before, never at it.
NOT_BEFORE_MARGIN_S = 1.0
RETRYABLE = {
    "ATTEMPTS_EXHAUSTED",
    "HTTP_RATE_LIMITED",
    "HTTP_UNAVAILABLE",
    "HTTP_TIMEOUT",
    "HTTP_CONNECTION_FAILED",
    "DEADLINE_EXCEEDED",
    "NETWORK_GATE_BUSY",
    "CLIENT_INTERNAL_ERROR",
    "API_MAXLAG",
    "API_RATELIMITED",
}
RANK = {"complete": 0, "partial": 1, "deferred": 2, "failed": 3}

Cli = Callable[[list[str]], tuple[int, str, str]]


def default_cli(argv: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(argv, capture_output=True, text=True, check=False)  # noqa: S603 - fixed argv
    return proc.returncode, proc.stdout, proc.stderr


def _stamp(t: float) -> str:
    return datetime.fromtimestamp(t, UTC).isoformat(timespec="seconds")


def _parse_time(text: str | None) -> float | None:
    if not text:
        return None
    return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()


def _write_atomic(path: Path, data: Any) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def _append(path: Path, entry: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def _journal(out: Path) -> list[dict[str, Any]]:
    log = out / "captures.jsonl"
    if not log.exists():
        return []
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]


def used(entries: list[dict[str, Any]]) -> tuple[int, int]:
    """HTTP attempts and accepted body bytes recorded so far; an interrupted or unreported run at its worst case."""
    ended = {(e["key"], e["run"]) for e in entries if e.get("event") == "end"}
    attempts = accepted = 0
    for e in entries:
        if e.get("event") == "start" and (e["key"], e["run"]) not in ended:
            attempts += RUN_WORST_ATTEMPTS
            accepted += RUN_WORST_BYTES
        if e.get("event") != "end":
            continue
        recorded = ((e.get("stdout") or {}).get("capture") or {}).get("attempts") or []
        if not recorded:
            attempts += RUN_WORST_ATTEMPTS
            accepted += RUN_WORST_BYTES
        for a in recorded:
            attempts += 1
            if a.get("code") is None:
                accepted += int(a.get("body_bytes") or 0)
    return attempts, accepted


def summarize(exit_code: int, stdout: dict[str, Any]) -> dict[str, Any]:
    cap = stdout.get("capture") or {}
    codes = sorted({i.get("code") for i in cap.get("issues", []) if isinstance(i, dict)} - {None})
    status = stdout.get("status")
    if status is None:
        codes = sorted(set(codes) | {"CLIENT_INTERNAL_ERROR"})
    render = cap.get("render") or {}
    not_before = cap.get("not_before")
    if status == "partial" and render.get("code") == "DEFERRED_RETRY_AFTER":
        not_before = render.get("not_before")
    return {
        "exit": exit_code,
        "status": status,
        "bundle": stdout.get("bundle"),
        "codes": codes,
        "not_before": not_before,
        "deferred": status == "deferred" or (status == "partial" and render.get("code") == "DEFERRED_RETRY_AFTER"),
    }


def next_step(record: dict[str, Any], now: float) -> tuple[str, float | None]:
    """``done``, ``run`` (now), or ``wait`` until a time, for one article's runs so far."""
    runs = record["runs"]
    if not runs:
        return "run", None
    if any(r["status"] == "complete" for r in runs) or len(runs) >= MAX_RUNS:
        return "done", None
    last = runs[-1]
    if last.get("interrupted"):
        return "run", None
    if last["deferred"]:
        when = _parse_time(last["not_before"])
        if when is not None:
            when += NOT_BEFORE_MARGIN_S
        return ("wait", when) if when is not None and when > now else ("run", None)
    retried = sum(1 for r in runs if not r["deferred"] and not r.get("interrupted")) > 1
    if last["status"] in ("failed", "partial", None) and last["codes"] and set(last["codes"]) <= RETRYABLE:
        return ("done", None) if retried else ("run", None)
    return "done", None


def _final(record: dict[str, Any]) -> dict[str, Any] | None:
    runs = [r for r in record["runs"] if not r.get("interrupted")]
    if not runs:
        return None
    return min(runs, key=lambda r: (RANK.get(r["status"] or "failed", 3), r["run"]))


def _run_numbers_on_disk(out: Path, split: str, wiki: str, page_id: int) -> set[int]:
    folder = out / "bundles" / split
    if not folder.is_dir():
        return set()
    pat = re.compile(rf"{wiki}-{page_id}-a([0-9]+)")
    return {int(m.group(1)) for p in folder.iterdir() if (m := pat.fullmatch(p.name))}


def recover(out: Path, states: dict[str, Any], entries: list[dict[str, Any]]) -> None:
    """Bring the state in line with the journal after an interruption (idempotent)."""
    ends = {(e["key"], e["run"]): e for e in entries if e.get("event") == "end"}
    for e in entries:
        if e.get("event") != "start":
            continue
        rec = states["articles"].get(e["key"])
        if rec is None or any(r["run"] == e["run"] for r in rec["runs"]):
            continue
        end = ends.get((e["key"], e["run"]))
        if end is not None:
            rec["runs"].append({"run": e["run"], **summarize(end["exit"], end.get("stdout") or {})})
        else:
            rec["runs"].append(
                {
                    "run": e["run"],
                    "exit": None,
                    "status": None,
                    "bundle": None,
                    "codes": ["DRIVER_INTERRUPTED"],
                    "not_before": None,
                    "deferred": False,
                    "interrupted": True,
                }
            )
        rec["runs"].sort(key=lambda r: r["run"])
        rec["final"] = _final(rec)


def load_plan(path: Path) -> list[dict[str, Any]]:
    plan = json.loads(path.read_text(encoding="utf-8"))
    seen: set[str] = set()
    out = []
    for a in plan["articles"]:
        wiki, page_id, split = a["wiki"], a["page_id"], a["split"]
        if wiki not in ("ar", "en") or not isinstance(page_id, int) or page_id <= 0:
            raise SystemExit(f"invalid plan entry: {a}")
        if not re.fullmatch(r"[a-z0-9_-]+", split):
            raise SystemExit(f"invalid split: {split}")
        key = f"{split}/{wiki}-{page_id}"
        if key in seen:
            raise SystemExit(f"duplicate plan entry: {key}")
        seen.add(key)
        out.append({"key": key, "split": split, "wiki": wiki, "page_id": page_id})
    return out


def run(
    plan_path: Path,
    out: Path,
    cli: Cli = default_cli,
    clock: Callable[[], float] = time.time,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    out.mkdir(parents=True, exist_ok=True)
    lock_fd = os.open(out / "driver.lock", os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("another capture driver holds this output directory", file=sys.stderr)
            return 3
        return _run_locked(load_plan(plan_path), out, cli, clock, sleep)
    finally:
        os.close(lock_fd)


def _run_locked(
    plan: list[dict[str, Any]], out: Path, cli: Cli, clock: Callable[[], float], sleep: Callable[[float], None]
) -> int:
    states_path, log = out / "capture_states.json", out / "captures.jsonl"
    states: dict[str, Any] = (
        json.loads(states_path.read_text(encoding="utf-8")) if states_path.exists() else {"articles": {}}
    )
    for a in plan:
        states["articles"].setdefault(
            a["key"], {"split": a["split"], "wiki": a["wiki"], "page_id": a["page_id"], "runs": [], "final": None}
        )
    recover(out, states, _journal(out))
    _write_atomic(states_path, states)
    pending: list[float] = []
    for a in plan:
        rec = states["articles"][a["key"]]
        sleeps = 0
        while True:
            step, when = next_step(rec, clock())
            if step == "done":
                break
            if step == "wait" and when is not None:
                delay = when - clock()
                if delay > MAX_INLINE_WAIT_S or sleeps >= 3:  # a clock that does not advance never spins
                    pending.append(when)
                    print(f"{a['key']}: deferred until {_stamp(when)}", file=sys.stderr, flush=True)
                    break
                sleep(max(0.0, delay))
                sleeps += 1
                continue
            entries = _journal(out)
            attempts, accepted = used(entries)
            if attempts + RUN_WORST_ATTEMPTS > MAX_HTTP_ATTEMPTS or accepted + RUN_WORST_BYTES > MAX_ACCEPTED_BYTES:
                _write_atomic(
                    out / "ceiling.json",
                    {
                        "stopped_before": a["key"],
                        "at": _stamp(clock()),
                        "http_attempts": attempts,
                        "accepted_body_bytes": accepted,
                        "limits": {"http_attempts": MAX_HTTP_ATTEMPTS, "accepted_body_bytes": MAX_ACCEPTED_BYTES},
                    },
                )
                print(f"ceiling: not starting {a['key']} ({attempts} attempts, {accepted} bytes)", file=sys.stderr)
                return 2
            seen = {r["run"] for r in rec["runs"]}
            seen |= {e["run"] for e in entries if e.get("key") == a["key"]}
            seen |= _run_numbers_on_disk(out, a["split"], a["wiki"], a["page_id"])
            n = max(seen, default=0) + 1
            target = out / "bundles" / a["split"] / f"{a['wiki']}-{a['page_id']}-a{n}"
            target.parent.mkdir(parents=True, exist_ok=True)
            argv = [
                "citerift-wiki",
                "capture",
                "--wiki",
                a["wiki"],
                "--page-id",
                str(a["page_id"]),
                "--out",
                str(target),
            ]
            _append(log, {"event": "start", "key": a["key"], "run": n, "at": _stamp(clock()), "argv": argv})
            code, stdout_text, stderr = cli(argv)
            try:
                stdout = json.loads(stdout_text) if stdout_text.strip() else {}
            except json.JSONDecodeError:
                stdout = {"unparsed_stdout": stdout_text}
            _append(
                log,
                {
                    "event": "end",
                    "key": a["key"],
                    "run": n,
                    "at": _stamp(clock()),
                    "exit": code,
                    "stdout": stdout,
                    "stderr": stderr,
                },
            )
            rec["runs"].append({"run": n, **summarize(code, stdout)})
            rec["final"] = _final(rec)
            _write_atomic(states_path, states)
            final = rec["final"] or {}
            print(f"{a['key']}: run {n} {stdout.get('status')} -> {final.get('status')}", file=sys.stderr, flush=True)
    if pending:
        print(f"resume after {_stamp(min(pending))}: rerun the same command", file=sys.stderr)
        return 4
    return 0


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    return run(Path(sys.argv[1]), Path(sys.argv[2]))


if __name__ == "__main__":
    sys.exit(main())
