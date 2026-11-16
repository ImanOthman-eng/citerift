"""The instrumented entry of the Step 11 vertical slice: ``citerift.investigation.cli.main`` (the function the
``citerift-investigate`` console script runs) with optional instrumentation chosen by environment variables.

Instrumentation never changes a scientific decision; it observes, injects a named fault, or presents another engine
identity, as the owner's Step 11 instruction allows (item 3: "Internal helpers may be used for instrumentation, fault
injection and independent verification").

- ``VS_NET_LOG=<file>``: every socket connect, ``create_connection`` and ``getaddrinfo`` in this process is recorded
  (one JSON line) and refused. The runner also runs this process in a network namespace with no interface
  (``unshare -rn``), so a socket that escaped the counter would fail as well.
- ``VS_KILL=<STEP>:<point>``: at the named controller boundary of that step (``citerift.investigation.faults``), the
  process kills itself with SIGKILL (no clean-up, no exception handler runs).
- ``VS_EXTRACTION=schema_invalid``: the Stage 03 extraction document gets one property its schema does not allow
  (VS-7, a schema-invalid extraction input).
- ``VS_PROFILE_DIGEST=<hex>``: the Stage 03 profile is presented with another digest (VS-10, extraction identity).
- ``VS_STAGE04=<json object>``: fields replacing the Stage 04 identity (VS-10, engine/schema identity).
- ``VS_LIVE_MODE=<mode>`` with ``VS_LIVE_BUNDLE`` and ``VS_WORKROOT``: a live-capture request uses the production live
  ACQUIRE adapter with the default fetch policy and its D-042 bound, but the SYNTHETIC-network child of the Step 8
  tests (``tests/stage04/live_fake_child.py``): no request leaves the machine.

Run: ``python vs_entry.py <citerift-investigate arguments>``.
"""

# ruff: noqa: PLC0415  (each instrumentation imports the module it patches only when it is chosen)

from __future__ import annotations

import dataclasses
import json
import os
import signal
import socket
import sys
import time
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[5]


def _guard_network(log: Path) -> None:
    def record(what: str, target: Any) -> None:
        with open(log, "a", encoding="utf-8") as f:
            f.write(json.dumps({"call": what, "target": repr(target)[:200], "pid": os.getpid()}) + "\n")
        raise OSError(101, f"VS network guard: {what} refused")

    def connect(self: socket.socket, address: Any) -> None:
        record("socket.connect", address)

    def connect_ex(self: socket.socket, address: Any) -> int:
        record("socket.connect_ex", address)
        return 101

    def create_connection(address: Any, *args: Any, **kwargs: Any) -> socket.socket:
        record("socket.create_connection", address)
        raise AssertionError  # unreachable

    def getaddrinfo(host: Any, *args: Any, **kwargs: Any) -> Any:
        record("socket.getaddrinfo", host)

    socket.socket.connect = connect  # type: ignore[method-assign]
    socket.socket.connect_ex = connect_ex  # type: ignore[method-assign]
    socket.create_connection = create_connection
    socket.getaddrinfo = getaddrinfo


def _kill_at(spec: str) -> None:
    from citerift.investigation import faults

    step, point = spec.split(":", 1)

    def handler(name: str, context: dict[str, Any]) -> None:
        if name == point and context.get("step") == step:
            sys.stdout.flush()
            os.kill(os.getpid(), signal.SIGKILL)
            time.sleep(60)  # never reached

    faults.install(handler)


def _schema_invalid_extraction() -> None:
    from citerift.investigation.adapters import extract

    real = extract.extract_bundle

    def damaged(*args: Any, **kwargs: Any) -> dict[str, Any]:
        doc = real(*args, **kwargs)
        doc["vs7_unexpected_property"] = True
        return doc

    extract.extract_bundle = damaged  # type: ignore[assignment]


def _profile_digest(value: str) -> None:
    from citerift.investigation.adapters import extract

    real = extract.load_profile
    extract.load_profile = lambda: dataclasses.replace(real(), digest=value)  # type: ignore[assignment]


def _stage04(fields: dict[str, Any]) -> None:
    from citerift.investigation.adapters import plan

    plan.STAGE04_IDENTITY = {**plan.STAGE04_IDENTITY, **fields}


def _live(mode: str) -> None:
    from citerift.investigation import operations as ops
    from citerift.investigation.adapters.live import make_live_acquire
    from citerift.investigation.adapters.plan import Integration
    from citerift.wiki.fetch import FetchPolicy

    os.environ["CITERIFT_FAKE_MODE"] = mode
    os.environ["CITERIFT_FAKE_BUNDLE"] = os.environ["VS_LIVE_BUNDLE"]
    child = [sys.executable, "-I", str(REPO / "tests" / "stage04" / "live_fake_child.py")]
    work = Path(os.environ["VS_WORKROOT"])

    def integration_for(request: Any) -> Integration:
        if request["mode"] != "live_capture":
            return Integration(live=None)
        return Integration(live=make_live_acquire(FetchPolicy(), child=child, workroot=work))

    ops.integration_for = integration_for


def main(argv: list[str]) -> int:
    env = os.environ
    if env.get("VS_NET_LOG"):
        _guard_network(Path(env["VS_NET_LOG"]))
    if env.get("VS_KILL"):
        _kill_at(env["VS_KILL"])
    if env.get("VS_EXTRACTION") == "schema_invalid":
        _schema_invalid_extraction()
    if env.get("VS_PROFILE_DIGEST"):
        _profile_digest(env["VS_PROFILE_DIGEST"])
    if env.get("VS_STAGE04"):
        _stage04(json.loads(env["VS_STAGE04"]))
    if env.get("VS_LIVE_MODE"):
        _live(env["VS_LIVE_MODE"])
    from citerift.investigation import cli

    return cli.main(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
