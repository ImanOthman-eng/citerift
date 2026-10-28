"""Build capture bundles from the recorded development acquisition (no network).

Usage: python build_dev_bundles.py OUT_DIR ACQUISITION_DIR [ACQUISITION_DIR ...]

acquire_dev.py recorded the Action API answer and the Core REST HTML of each development revision. This script
replays those recorded bytes through the production ``capture_revision`` with a scripted transport and clock, so the
bundles hold exactly the recorded answers and pass the same identity checks as a live capture. Their timestamps and
attempt lists are those of the replay, not of the original requests (the original requests, including every HTTP
429, are in acquisition.json). Revisions whose render was not captured, and redirect pages, are skipped or fail
as a live capture would.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from citerift.wiki.capture import CaptureRequest, capture_revision
from citerift.wiki.fetch import FetchPolicy, RawResponse, Transport


class ScriptedClock:
    def __init__(self) -> None:
        self.t = 0.0
        self.base = datetime(2026, 10, 28, 18, 0, tzinfo=UTC)

    def monotonic(self) -> float:
        return self.t

    def now(self) -> datetime:
        return self.base + timedelta(seconds=self.t)

    def sleep(self, seconds: float) -> None:
        self.t += max(0.0, seconds)


def _closed() -> None:
    return None


def recorded(source: bytes, html: bytes, html_headers: dict[str, str]) -> Transport:
    def transport(url: str, headers: dict[str, str], timeout: float) -> RawResponse:
        if "/w/api.php" in url:
            return RawResponse(200, {"content-type": "application/json; charset=utf-8"}, iter([source]), _closed)
        kept = {k.lower(): v for k, v in html_headers.items() if k.lower() != "content-encoding"}
        return RawResponse(200, kept, iter([html]), _closed)

    return transport


def main() -> int:
    out_root = Path(sys.argv[1])
    for acq_dir in map(Path, sys.argv[2:]):
        acq = json.loads((acq_dir / "acquisition.json").read_text(encoding="utf-8"))
        for res in acq["results"]:
            if res.get("rest_status") != 200:
                continue
            source = (acq_dir / "artifacts" / res["source_sha256"]).read_bytes()
            html = (acq_dir / "artifacts" / res["rest_sha256"]).read_bytes()
            target = out_root / f"{res['wiki']}-{res['revision_id']}"
            if target.exists():
                continue
            outcome = capture_revision(
                CaptureRequest(res["wiki"], revision_id=res["revision_id"]),
                FetchPolicy(),
                out=target,
                transport=recorded(source, html, res["rest_headers"]),
                clock=ScriptedClock(),
            )
            print(res["wiki"], res["revision_id"], outcome.status, [i.code for i in outcome.issues], outcome.bundle)
    return 0


if __name__ == "__main__":
    sys.exit(main())
