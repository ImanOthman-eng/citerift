"""A SYNTHETIC-network live ACQUIRE child for the Step 8 tests: the production child (``live_child.main``) with the
Stage 03 transport replaced by a fake chosen by ``CITERIFT_FAKE_MODE``. Nothing here reaches a network.

``replay`` answers from a real retained bundle (``CITERIFT_FAKE_BUNDLE``): the exact recorded Action API body and
render HTML with the recorded headers. The other modes stall or answer in ways a test needs (Retry-After forms, a
request in flight at the kill, descendants that try to outlive the child).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

from citerift.investigation.adapters import live_child
from citerift.wiki.fetch import RawResponse, TransportError

MODE = os.environ.get("CITERIFT_FAKE_MODE", "replay")
BUNDLE = Path(os.environ.get("CITERIFT_FAKE_BUNDLE", "."))


def _hang() -> Iterator[bytes]:
    while True:
        time.sleep(3600)
        yield b""


def _spawn_descendants() -> None:
    """One descendant in the child's session and one that leaves it with setsid; both would sleep for an hour."""
    pids = Path(os.environ["CITERIFT_FAKE_PIDS"])
    stay = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(3600)"])
    leave = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(3600)"], start_new_session=True)
    pids.write_text(json.dumps([stay.pid, leave.pid]))


def transport(url: str, headers: dict[str, str], timeout: float) -> RawResponse:
    if os.environ.get("CITERIFT_FAKE_CHILD_PID"):
        Path(os.environ["CITERIFT_FAKE_CHILD_PID"]).write_text(str(os.getpid()))
    if MODE == "replay":
        capture = json.loads((BUNDLE / "capture.json").read_bytes())
        if "/w/api.php" in url:
            body = (BUNDLE / "artifacts" / capture["source"]["response_artifact"]).read_bytes()
            hdrs = {"content-type": "application/json; charset=utf-8"}
        else:
            body = (BUNDLE / "artifacts" / capture["render"]["artifact"]).read_bytes()
            hdrs = dict(capture["render"]["headers"])
        return RawResponse(200, hdrs, iter([body]))
    if MODE == "in_flight":  # killed before any response header is seen
        time.sleep(3600)
    if MODE.startswith("retry_after:"):  # headers seen (and the side channel written), then the body never ends
        return RawResponse(429, {"retry-after": MODE.split(":", 1)[1], "content-type": "text/plain"}, _hang())
    if MODE == "spawn":
        _spawn_descendants()
        time.sleep(3600)
    if MODE == "refused":
        raise TransportError("HTTP_CONNECTION_FAILED", "SYNTHETIC: connection refused")
    raise AssertionError(MODE)


if __name__ == "__main__":
    sys.exit(live_child.main(sys.argv[1:], transport=transport))
