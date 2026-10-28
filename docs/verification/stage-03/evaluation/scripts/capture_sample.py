"""Capture the selected holdout and challenge articles with the production CLI, one at a time.

Usage: python capture_sample.py SELECTION_JSON OUT_DIR SPLIT [SPLIT ...]

SPLIT is ``holdout``, ``reserve``, ``confirmation`` or ``challenge``. For each selected article, in the order of
selection.json, this runs ``citerift-wiki capture --wiki W --page-id N --out OUT_DIR/bundles/<split>/<wiki>-<page
id>-a<attempt>`` (the path comes from the integer page id, never from the title). A capture that ends ``deferred``,
or ``partial`` because the render was deferred, is retried after its ``not_before`` (at most MAX_ATTEMPTS attempts and
MAX_WAIT_S of waiting per article); every attempt is kept. Each attempt's exit code, stdout JSON and stderr are
written to OUT_DIR/captures.jsonl, and the final state per article to OUT_DIR/capture_states.json (FROZEN_PROTOCOL.md
G9: complete, partial, deferred or failed, with issue codes). The network policy is the production one: every
request goes through the project network gate, so no two requests are ever in flight.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MAX_ATTEMPTS = 3
MAX_WAIT_S = 600.0


def _seconds_until(stamp: str | None) -> float:
    if not stamp:
        return 0.0
    when = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    return max(0.0, (when - datetime.now(UTC)).total_seconds())


def _render_deferred(result: dict[str, Any]) -> tuple[bool, str | None]:
    render = (result.get("capture") or {}).get("render") or {}
    return render.get("code") == "DEFERRED_RETRY_AFTER", render.get("not_before")


def capture(wiki: str, page_id: int, out: Path, log: Any) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    waited = 0.0
    for n in range(1, MAX_ATTEMPTS + 1):
        target = out / f"{wiki}-{page_id}-a{n}"
        cmd = ["citerift-wiki", "capture", "--wiki", wiki, "--page-id", str(page_id), "--out", str(target)]
        started = datetime.now(UTC).isoformat(timespec="seconds")
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)  # noqa: S603 - fixed argv
        try:
            result = json.loads(proc.stdout) if proc.stdout.strip() else {}
        except json.JSONDecodeError:
            result = {"unparsed_stdout": proc.stdout}
        entry = {
            "wiki": wiki,
            "page_id": page_id,
            "attempt": n,
            "started_at": started,
            "argv": cmd,
            "exit": proc.returncode,
            "stdout": result,
            "stderr": proc.stderr,
        }
        log.write(json.dumps(entry, ensure_ascii=False) + "\n")
        log.flush()
        status = result.get("status")
        codes = sorted(
            {i.get("code") for i in (result.get("capture") or {}).get("issues", []) if isinstance(i, dict)} - {None}
        )
        attempts.append(
            {"attempt": n, "exit": proc.returncode, "status": status, "bundle": result.get("bundle"), "codes": codes}
        )
        render_deferred, render_nb = _render_deferred(result)
        if status == "deferred":
            delay = _seconds_until((result.get("capture") or {}).get("not_before"))
        elif status == "partial" and render_deferred:
            delay = _seconds_until(render_nb)
        else:
            break
        if n == MAX_ATTEMPTS or waited + delay > MAX_WAIT_S:
            break
        print(f"{wiki}-{page_id}: {status}, retrying in {delay:.0f} s", file=sys.stderr, flush=True)
        time.sleep(delay)
        waited += delay
    rank = {"complete": 0, "partial": 1, "deferred": 2, "failed": 3}
    best = min(attempts, key=lambda a: (rank.get(a["status"] or "failed", 3), a["attempt"]))
    return {"wiki": wiki, "page_id": page_id, "final": best, "attempts": attempts}


def main() -> int:
    selection = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    out = Path(sys.argv[2])
    splits = sys.argv[3:]
    out.mkdir(parents=True, exist_ok=True)
    states_path = out / "capture_states.json"
    states: dict[str, Any] = (
        json.loads(states_path.read_text(encoding="utf-8")) if states_path.exists() else {"articles": {}}
    )
    with (out / "captures.jsonl").open("a", encoding="utf-8") as log:
        for split in splits:
            for wiki in ("ar", "en"):
                if split == "challenge":
                    chosen = selection["challenge"][wiki]["selected"]
                else:
                    chosen = selection["splits"][wiki][split]
                for article in chosen:
                    key = f"{split}/{wiki}-{article['page_id']}"
                    if key in states["articles"]:
                        continue
                    bundles = out / "bundles" / split
                    bundles.mkdir(parents=True, exist_ok=True)
                    state = capture(wiki, int(article["page_id"]), bundles, log)
                    state["split"] = split
                    states["articles"][key] = state
                    states_path.write_text(json.dumps(states, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
                    print(f"{key}: {state['final']['status']} {state['final']['codes']}", file=sys.stderr, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
