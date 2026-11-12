"""The child process of a live ACQUIRE attempt (Step 8, D-042): ``python -I -m <this module> WORKDIR PARENT_PID``.

It runs the accepted Stage 03 capture, ``citerift.wiki.capture.capture_revision``, for the pinned revision in
``WORKDIR/request.json`` with the fetch policy given there, and publishes the Stage 03 bundle at ``WORKDIR/bundle``.
Stage 03 is not changed: its transport, network gate, throttling and retries all run as accepted.

Two things are added around it:

- **Parent death.** First of all, ``prctl(PR_SET_PDEATHSIG, SIGKILL)``; then the parent pid is checked, because the
  parent may have died before the call. With no parent, the child exits before any request.
- **Retry-After side channel.** Stage 03 persists a Retry-After instant in its network gate only after the body is
  read. So that a child killed earlier still tells the parent what it saw, the module-level Stage 03 transport
  (``citerift.wiki.fetch.urllib_transport``, which the Fetcher uses together with its network gate) is wrapped: before
  each request a ``request`` line and, as soon as the response headers are in, a ``response`` line with the status
  and the raw ``Retry-After`` value and the wall-clock instant are appended to ``WORKDIR/network.jsonl`` and fsynced,
  before Stage 03 reads the body. A transport error is an ``error`` line. The parent reads this file only to decide
  retryability after a kill; it is never evidence.

The outcome is written atomically to ``WORKDIR/result.json``: the Stage 03 status, the capture record's
``not_before``, its issue codes and whether a bundle was published.
"""

from __future__ import annotations

import ctypes
import json
import os
import signal
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from citerift.wiki import fetch
from citerift.wiki.capture import CaptureRequest, capture_revision
from citerift.wiki.fetch import FetchPolicy, RawResponse, Transport, TransportError

PR_SET_PDEATHSIG = 1
NO_PARENT = 70


def die_with_parent(parent: int) -> None:
    """G-5: the kernel kills this process when its parent dies; a parent already gone ends it now."""
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        if libc.prctl(PR_SET_PDEATHSIG, signal.SIGKILL, 0, 0, 0) != 0:
            raise OSError(ctypes.get_errno(), "prctl(PR_SET_PDEATHSIG)")
    except (OSError, AttributeError) as exc:
        sys.stderr.write(f"PR_SET_PDEATHSIG unavailable: {exc}\n")
        sys.exit(NO_PARENT)  # fail closed: no unsupervised network use
    if os.getppid() != parent:
        sys.exit(NO_PARENT)


class Observer:
    """The Retry-After side channel around a Stage 03 transport."""

    def __init__(self, base: Transport, log: Path) -> None:
        self.base = base
        self.fd = os.open(log, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_CLOEXEC, 0o600)

    def _write(self, entry: dict[str, Any]) -> None:
        data = (json.dumps(entry, sort_keys=True) + "\n").encode()
        os.write(self.fd, data)
        os.fsync(self.fd)

    def __call__(self, url: str, headers: dict[str, str], timeout: float) -> RawResponse:
        self._write({"event": "request", "url": url, "at": time.time()})
        try:
            raw = self.base(url, headers, timeout)
        except TransportError as exc:
            self._write({"event": "error", "url": url, "code": exc.code, "at": time.time()})
            raise
        self._write(
            {
                "event": "response",
                "url": url,
                "status": raw.status,
                "retry_after": raw.headers.get("retry-after"),
                "at": time.time(),
            }
        )
        return raw


def _atomic(path: Path, value: Any) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "wb") as f:
        f.write(json.dumps(value, sort_keys=True).encode())
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def main(argv: list[str] | None = None, *, transport: Transport | None = None) -> int:
    """Run one capture. ``transport`` replaces the network only in tests; production passes none."""
    args = sys.argv[1:] if argv is None else argv
    workdir, parent = Path(args[0]), int(args[1])
    die_with_parent(parent)
    req = json.loads((workdir / "request.json").read_text(encoding="utf-8"))
    policy = FetchPolicy(**req["policy"])
    base: Callable[..., RawResponse] = transport or fetch.urllib_transport
    fetch.urllib_transport = Observer(base, workdir / "network.jsonl")  # the Fetcher keeps its network gate
    outcome = capture_revision(
        CaptureRequest(req["wiki"], revision_id=req["revision_id"]), policy, out=workdir / "bundle"
    )
    _atomic(
        workdir / "result.json",
        {
            "status": outcome.status,
            "not_before": outcome.record.get("not_before"),
            "issues": [i.to_json() for i in outcome.issues],
            "bundle": outcome.bundle is not None,
        },
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
