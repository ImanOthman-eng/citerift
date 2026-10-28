"""SYNTHETIC stress bundle for calibration step C: the largest development revision scaled toward the size limits.

Usage: python stress_bundle.py SOURCE_TEXT HTML FACTOR OUT_BUNDLE

The source text is repeated FACTOR times (separated by a blank line) and the HTML body is repeated FACTOR times
inside one document. The capture goes through the production capture code with a scripted transport and clock, so
the bundle is internally consistent (SHA-1, size, render revision checks); its revision id, page id and SHA-1 are
those of a revision that does not exist. It measures cost only and is never evidence about Wikipedia.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from citerift.wiki.capture import CaptureRequest, capture_revision
from citerift.wiki.fetch import FetchPolicy, RawResponse

REVISION = 999_000_001
PAGE = 999_000_002


class ScriptedClock:
    def __init__(self) -> None:
        self.t = 0.0
        self.base = datetime(2026, 10, 28, 0, 0, tzinfo=UTC)

    def monotonic(self) -> float:
        return self.t

    def now(self) -> datetime:
        return self.base + timedelta(seconds=self.t)

    def sleep(self, seconds: float) -> None:
        self.t += max(0.0, seconds)


def base36(hex_digest: str) -> str:
    n, digits, out = int(hex_digest, 16), "0123456789abcdefghijklmnopqrstuvwxyz", ""
    while n:
        n, r = divmod(n, 36)
        out = digits[r] + out
    return out or "0"


def main() -> int:
    text = Path(sys.argv[1]).read_text(encoding="utf-8")
    html = Path(sys.argv[2]).read_bytes().decode("utf-8")
    factor = int(sys.argv[3])
    out = Path(sys.argv[4])
    big = "\n\n".join([text] * factor)
    data = big.encode("utf-8")
    sha1 = hashlib.sha1(data, usedforsecurity=False).hexdigest()
    answer = {
        "batchcomplete": True,
        "query": {
            "pages": [
                {
                    "pageid": PAGE,
                    "ns": 0,
                    "title": "SYNTHETIC stress page",
                    "lastrevid": REVISION,
                    "revisions": [
                        {
                            "revid": REVISION,
                            "parentid": 0,
                            "timestamp": "2026-10-28T00:00:00Z",
                            "size": len(data),
                            "sha1": sha1,
                            "slots": {
                                "main": {"contentmodel": "wikitext", "contentformat": "text/x-wiki", "content": big}
                            },
                        }
                    ],
                }
            ]
        },
    }
    head, rest = html.split("<body", 1)
    body_open, body = rest.split(">", 1)
    body, tail = body.rsplit("</body>", 1)
    head = re.sub(r'about="([^"]*/revision/)[0-9]+"', rf'about="\g<1>{REVISION}"', head)
    head = re.sub(r'(property="mw:pageId" content=")[0-9]+', rf"\g<1>{PAGE}", head)
    head = re.sub(r'(property="mw:revisionSHA1" content=")[0-9a-z]+', rf"\g<1>{base36(sha1)}", head)
    doc = (head + "<body" + body_open + ">" + body * factor + "</body>" + tail).encode("utf-8")
    headers = {
        "content-type": 'text/html; charset=utf-8; profile="https://www.mediawiki.org/wiki/Specs/HTML/2.8.0"',
        "content-revision-id": str(REVISION),
    }

    def transport(url: str, request_headers: dict[str, str], timeout: float) -> RawResponse:
        if "/w/api.php" in url:
            body_bytes = json.dumps(answer, ensure_ascii=False).encode("utf-8")
            return RawResponse(200, {"content-type": "application/json; charset=utf-8"}, iter([body_bytes]), _no)
        return RawResponse(200, headers, iter([doc]), _no)

    outcome = capture_revision(
        CaptureRequest("ar", revision_id=REVISION), FetchPolicy(), out=out, transport=transport, clock=ScriptedClock()
    )
    result: dict[str, Any] = {
        "status": outcome.status,
        "issues": [i.code for i in outcome.issues],
        "source_bytes": len(data),
        "html_bytes": len(doc),
    }
    print(json.dumps(result))
    return 0 if outcome.bundle is not None else 1


def _no() -> None:
    return None


if __name__ == "__main__":
    sys.exit(main())
