"""Item-level disagreements for the confirmation campaign (AMENDMENT_2026-11-02_CONFIRMATION.md section 8).

Usage: python disagreements_v2.py SCORE_SPEC.json > disagreements.json

This is the retained ``disagreements.py``, unchanged, with two substitutions so that every listed item is exactly
one that the campaign's scoring counts as an error:

- the engine's predictions are read by scorer v2 (``evaluate_v2.engine_predictions_v2``: definition rule D2/D6);
- articles of the split ``challenge`` get the challenge window (``warning_challenge.load``).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT / "docs/verification/stage-03/protocol/scripts"))
sys.path.insert(0, str(ROOT / "docs/verification/stage-03/evaluation/scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import disagreements as d1  # noqa: E402 - the retained script, unchanged
import evaluate_v2 as v2  # noqa: E402
import warning_challenge as wc  # noqa: E402


def items(spec: dict[str, Any]) -> dict[str, Any]:
    original_pred, original_load = d1.ev.engine_predictions, d1.ev.load_bundle
    current: dict[str, Any] = {}

    def load(path: Path) -> Any:
        art = wc.load(path) if current["challenge"] else original_load(path)
        current["text"] = art.text
        return art

    def pred(doc: dict[str, Any]) -> Any:
        return v2.engine_predictions_v2(doc, current["text"])

    d1.ev.engine_predictions, d1.ev.load_bundle = pred, load
    out: dict[str, Any] = {}
    try:
        for split, entries in spec["splits"].items():
            current["challenge"] = split == "challenge"
            out[split] = [
                d1.article_items(Path(e["bundle"]), Path(e["locked"]), Path(e["extraction"]))
                for e in sorted(entries, key=lambda x: x["locked"])
            ]
    finally:
        d1.ev.engine_predictions, d1.ev.load_bundle = original_pred, original_load
    return out


def main() -> int:
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    sys.stdout.write(json.dumps(items(spec), ensure_ascii=False, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
