"""One later retry pass for selected articles whose capture failed, or whose render failed, with only retryable errors.

Usage: python retry_failed.py OUT_DIR

A capture that ends ``failed`` because every attempt was rate limited (for example three HTTP 429 answers within
the 180 s capture deadline, ``ATTEMPTS_EXHAUSTED``) says nothing about the article. This pass runs, once and after the
main pass, a new capture for each such article through ``capture_sample.capture`` (same CLI, same network policy),
appends the new attempts to the article's record, and recomputes its final state. Failures with a non-retryable
error are not retried. Every attempt of both passes stays in captures.jsonl and capture_states.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from capture_sample import capture

# NETWORK_GATE_BUSY (added 2026-10-29 before the confirmation retry pass): another local process held the network
# gate past the capture deadline; like a rate limit, it says nothing about the article.
RETRYABLE = {
    "ATTEMPTS_EXHAUSTED",
    "HTTP_RATE_LIMITED",
    "HTTP_UNAVAILABLE",
    "HTTP_TIMEOUT",
    "DEADLINE_EXCEEDED",
    "NETWORK_GATE_BUSY",
}
RANK = {"complete": 0, "partial": 1, "deferred": 2, "failed": 3}


def main() -> int:
    out = Path(sys.argv[1])
    states_path = out / "capture_states.json"
    states = json.loads(states_path.read_text(encoding="utf-8"))
    with (out / "captures.jsonl").open("a", encoding="utf-8") as log:
        for key, st in sorted(states["articles"].items()):
            final = st["final"]
            # A failed capture, or a partial one whose render failed (the source was captured), is retried only
            # when every recorded error is a rate limit or another transient condition (added 2026-10-29, before
            # any annotation: the recapture had three partial captures whose render met only HTTP 429).
            if (
                final["status"] not in ("failed", "partial")
                or not final["codes"]
                or not set(final["codes"]) <= RETRYABLE
            ):
                continue
            wiki, page = key.split("/", 1)[1].split("-", 1)
            first = max(a["attempt"] for a in st["attempts"]) + 1
            new = capture(wiki, int(page), out / "bundles" / st["split"], log, first=first)
            st["attempts"] += new["attempts"]
            st["retry_pass"] = True
            st["final"] = min(st["attempts"], key=lambda a: (RANK.get(a["status"] or "failed", 3), a["attempt"]))
            states_path.write_text(json.dumps(states, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            print(f"{key}: retry pass {st['final']['status']} {st['final']['codes']}", file=sys.stderr, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
