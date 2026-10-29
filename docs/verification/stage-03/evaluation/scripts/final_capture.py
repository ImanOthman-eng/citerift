"""Final-campaign capture with the amendment's network ceilings (../../protocol/AMENDMENT_2026-10-29.md section 3).

Usage:
  python final_capture.py main  SELECTION_JSON OUT_DIR   # holdout, then reserve, ar before en (capture_sample order)
  python final_capture.py retry OUT_DIR                  # the one bounded retry pass (retry_failed.py's rules)

Each article is captured by ``capture_sample.capture`` (the production ``citerift-wiki capture`` CLI, the shared
network gate, its retry policy and attempt logging), and the retry pass applies ``retry_failed.py``'s committed
transient set and selection rule unchanged. This driver only adds the ceilings: before each article it counts the
HTTP attempts and accepted body bytes already recorded in OUT_DIR/captures.jsonl, and stops without starting the
article when its worst case could cross 500 attempts or 300 MiB. The worst case per article is 3 CLI runs x 2
operations x 3 attempts, and at most 2 accepted bodies per CLI run within the source and render size limits. A
stop is written to OUT_DIR/ceiling.json and the article stays uncaptured; it still counts in acquisition success.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from capture_sample import MAX_ATTEMPTS, capture
from retry_failed import RANK, RETRYABLE

MAX_HTTP_ATTEMPTS = 500
MAX_ACCEPTED_BYTES = 300 * 1024 * 1024
WORST_ATTEMPTS = MAX_ATTEMPTS * 2 * 3
WORST_BYTES = MAX_ATTEMPTS * (4 * 1024 * 1024 + 64 * 1024 + 16 * 1024 * 1024)  # source text + API envelope + HTML


def used(out: Path) -> tuple[int, int]:
    attempts = accepted = 0
    log = out / "captures.jsonl"
    if not log.exists():
        return 0, 0
    for line in log.read_text(encoding="utf-8").splitlines():
        entry = json.loads(line)
        for a in ((entry.get("stdout") or {}).get("capture") or {}).get("attempts") or []:
            attempts += 1
            if a.get("code") is None:
                accepted += int(a.get("body_bytes") or 0)
        if not ((entry.get("stdout") or {}).get("capture") or {}).get("attempts"):
            # A run that reported no attempts (an internal error) is counted at its worst case.
            attempts += 2 * 3
    return attempts, accepted


def allowed(out: Path, key: str) -> bool:
    attempts, accepted = used(out)
    if attempts + WORST_ATTEMPTS <= MAX_HTTP_ATTEMPTS and accepted + WORST_BYTES <= MAX_ACCEPTED_BYTES:
        return True
    (out / "ceiling.json").write_text(
        json.dumps(
            {
                "stopped_before": key,
                "at": datetime.now(UTC).isoformat(timespec="seconds"),
                "http_attempts": attempts,
                "accepted_body_bytes": accepted,
                "limits": {"http_attempts": MAX_HTTP_ATTEMPTS, "accepted_body_bytes": MAX_ACCEPTED_BYTES},
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"ceiling: not starting {key} ({attempts} attempts, {accepted} bytes used)", file=sys.stderr, flush=True)
    return False


def save(path: Path, states: dict[str, Any]) -> None:
    path.write_text(json.dumps(states, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main_pass(selection_path: Path, out: Path) -> int:
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    out.mkdir(parents=True, exist_ok=True)
    states_path = out / "capture_states.json"
    states: dict[str, Any] = (
        json.loads(states_path.read_text(encoding="utf-8")) if states_path.exists() else {"articles": {}}
    )
    with (out / "captures.jsonl").open("a", encoding="utf-8") as log:
        for split in ("holdout", "reserve"):
            for wiki in ("ar", "en"):
                for article in selection["splits"][wiki][split]:
                    key = f"{split}/{wiki}-{article['page_id']}"
                    if key in states["articles"]:
                        continue
                    if not allowed(out, key):
                        return 2
                    bundles = out / "bundles" / split
                    bundles.mkdir(parents=True, exist_ok=True)
                    state = capture(wiki, int(article["page_id"]), bundles, log)
                    state["split"] = split
                    states["articles"][key] = state
                    save(states_path, states)
                    print(f"{key}: {state['final']['status']} {state['final']['codes']}", file=sys.stderr, flush=True)
    return 0


def retry_pass(out: Path) -> int:
    states_path = out / "capture_states.json"
    states = json.loads(states_path.read_text(encoding="utf-8"))
    with (out / "captures.jsonl").open("a", encoding="utf-8") as log:
        for key, st in sorted(states["articles"].items()):
            final = st["final"]
            if final["status"] is None and final["exit"] == 1:
                final = {**final, "status": "failed", "codes": ["CLIENT_INTERNAL_ERROR"]}
            if (
                final["status"] not in ("failed", "partial")
                or not final["codes"]
                or not set(final["codes"]) <= RETRYABLE
            ):
                continue
            if st.get("retry_pass"):
                continue
            if not allowed(out, key + " (retry pass)"):
                return 2
            wiki, page = key.split("/", 1)[1].split("-", 1)
            first = max(a["attempt"] for a in st["attempts"]) + 1
            new = capture(wiki, int(page), out / "bundles" / st["split"], log, first=first)
            st["attempts"] += new["attempts"]
            st["retry_pass"] = True
            st["final"] = min(st["attempts"], key=lambda a: (RANK.get(a["status"] or "failed", 3), a["attempt"]))
            save(states_path, states)
            print(f"{key}: retry pass {st['final']['status']} {st['final']['codes']}", file=sys.stderr, flush=True)
    return 0


def main() -> int:
    if sys.argv[1] == "main":
        return main_pass(Path(sys.argv[2]), Path(sys.argv[3]))
    if sys.argv[1] == "retry":
        return retry_pass(Path(sys.argv[2]))
    raise SystemExit(__doc__)


if __name__ == "__main__":
    sys.exit(main())
