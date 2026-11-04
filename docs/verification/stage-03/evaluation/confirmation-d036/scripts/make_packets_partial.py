"""Runs the frozen ``confirmation-2026-11/campaign/annotations/make_packets.py`` with one condition changed, so that
an article whose capture ended ``partial`` (source captured, no render) gets a packet like every other article.

Usage (from the repository root): python make_packets_partial.py PLAN_JSON OUT_DIR [SPLIT ...]

[D-036 copy of ``../../confirmation-d035/scripts/make_packets_partial.py``, unchanged except this paragraph. The
D-036 campaign uses it from the start (AMENDMENT_2026-11-04_D036_CONFIRMATION.md section 2), so a partial capture
needs no change of tool during the campaign. Its history follows.]

Why. The frozen tool refuses the whole plan when any article's final capture is not ``complete``. In the D-035
campaign, ``holdout/ar-9335702`` ended ``partial`` (render ATTEMPTS_EXHAUSTED on HTTP 429, final under the capture
driver's rules). The campaign's own rules require that article to be labelled:

- AMENDMENT_2026-11-02_CONFIRMATION.md section 6, failure policy: an article that ends without a render stays in the
  sample;
- ``run_confirmation.py`` (unchanged) refuses to run while any article with a capture bundle has no locked label
  (review R6, RR-8: an article is never left out silently);
- ``evaluate.py packets`` (frozen) makes render-less packets (no ``render.html``, ``html_sha256`` null), and the
  unchanged brief gives ``render.html`` "when it was captured".

The 2026-11 campaign had no partial capture, so the guard never met this case. This wrapper replaces exactly the
guard below and nothing else; it asserts that the guard occurs once, and runs the frozen file's code with its own
``__file__``, so the repository root, the packet tool and the instance split are the frozen ones. An article with no
bundle at all is still refused. Nothing here reads a label or an extraction.
"""

from __future__ import annotations

import sys
from pathlib import Path

FROZEN = Path(__file__).resolve().parents[2] / "confirmation-2026-11" / "campaign" / "annotations" / "make_packets.py"
OLD = '        if final.get("status") != "complete":\n            raise SystemExit(f"{key} has no complete capture")\n'
NEW = (
    '        if final.get("status") not in ("complete", "partial") or not final.get("bundle"):\n'
    '            raise SystemExit(f"{key} has no capture bundle")\n'
)


def main() -> int:
    source = FROZEN.read_text(encoding="utf-8")
    if source.count(OLD) != 1:
        raise SystemExit("the frozen guard was not found exactly once")
    namespace = {"__name__": "make_packets", "__file__": str(FROZEN)}
    exec(compile(source.replace(OLD, NEW), str(FROZEN), "exec"), namespace)  # noqa: S102 - the frozen file
    result: int = namespace["main"]()  # type: ignore[operator]
    return result


if __name__ == "__main__":
    sys.exit(main())
