"""Run ``disagreements_v2.py`` (frozen, unchanged) on a spec that has a ``challenge`` split.

Usage: python disagreements_challenge_fix.py SCORE_SPEC.json > disagreements.json

Defect found after the prediction run (2026-11-03), when the disagreements were first listed: for the ``challenge``
split, ``disagreements_v2.items`` replaces ``evaluate.load_bundle`` by its own ``load``, which calls
``warning_challenge.load``, which calls ``evaluate.load_bundle`` again, now the replacement: an endless recursion
(RecursionError). The gate split is not affected. The frozen tests did not run a challenge split.

The frozen files stay byte-identical. This wrapper gives ``warning_challenge`` a ``load`` bound to the original
``evaluate.load_bundle``, captured before ``items`` replaces it, and computes the same challenge window
(``warning_challenge.challenge_window``, unchanged). Everything else is ``disagreements_v2.items`` as frozen. It reads
no label other than the locked ones in the spec and changes no prediction.
"""

from __future__ import annotations

import dataclasses
import importlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
dv2 = importlib.import_module("disagreements_v2")
wc = importlib.import_module("warning_challenge")
_ORIGINAL_LOAD_BUNDLE = dv2.d1.ev.load_bundle


def _challenge_load(path: Path) -> Any:
    art = _ORIGINAL_LOAD_BUNDLE(path)
    return dataclasses.replace(art, window=wc.challenge_window(art.text, art.wiki, art.revision_id))


def items(spec: dict[str, Any]) -> dict[str, Any]:
    original = wc.load
    wc.load = _challenge_load
    try:
        result: dict[str, Any] = dv2.items(spec)
        return result
    finally:
        wc.load = original


def main() -> int:
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    sys.stdout.write(json.dumps(items(spec), ensure_ascii=False, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
