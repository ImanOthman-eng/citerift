"""Prospective scorer v2 for the confirmation campaign (AMENDMENT_2026-11-02_CONFIRMATION.md).

It is the frozen scorer ``evaluate.py``, imported unchanged, with one documented difference: the engine's predicted
reference definitions and units follow the definition rule of ``../../design/sfn-semantics/SEMANTIC_DECISION.md``
(D2, D4, D6). In a container whose occurrences repeat one content (``identical_definitions``) only the first
occurrence is a reference definition; in a conflicting container, the first occurrence of each distinct trimmed
source text is. Units of the other occurrences are not counted. Binding targets, uses, identifiers, render links,
markers, metrics, gates, thresholds, denominators, bootstrap and baselines are those of ``evaluate.py``.

Declared limitation (conservative): in a *conflicting* short-footnote reference, two calls with the same generated
content but different spellings (``p=`` and ``page=``) have different source texts, so the second one stays a
predicted definition. That can only add an engine false positive, never hide an error.

Usage: ``python evaluate_v2.py score <score_spec.json>`` (``packets`` and ``lock`` are the frozen commands).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import evaluate as v1  # the frozen scorer, imported unchanged

PROTOCOL = "AMENDMENT_2026-11-02_CONFIRMATION.md (scorer v2: definition rule D2/D6)"
# The frozen reader, kept before ``score`` substitutes v1's module attribute for the duration of a run.
_V1_ENGINE_PREDICTIONS = v1.engine_predictions


def repeat_definitions(doc: dict[str, Any], text: str) -> set[str]:
    """Definition ids (``ct-…/dN``) that repeat the content of an earlier occurrence of the same reference."""
    out: set[str] = set()
    for c in doc["containers"]:
        defs = c["definitions"]
        if c["binding_state"] == "identical_definitions":
            out.update(d["id"] for d in defs[1:])
        elif c["binding_state"] == "conflicting_definitions":
            seen: set[str] = set()
            for d in defs:
                b = d["body"]
                body = text[b["cp_start"] : b["cp_end"]].strip()
                if body in seen:
                    out.add(d["id"])
                seen.add(body)
    return out


def engine_predictions_v2(doc: dict[str, Any], text: str) -> v1.Predictions:
    pred = _V1_ENGINE_PREDICTIONS(doc)
    repeats = repeat_definitions(doc, text)
    if not repeats:
        return pred
    starts = {}
    for c in doc["containers"]:
        for d in c["definitions"]:
            starts[(d["source"]["cp_start"], d["source"]["cp_end"], c["id"])] = d["id"]
    defs = [p for p in pred.definitions if starts.get((p.start, p.end, p.data["container"])) not in repeats]
    repeat_units = {
        (u["source"]["cp_start"], u["source"]["cp_end"]) for u in doc["units"] if u["definition_id"] in repeats
    }
    units = [p for p in pred.units if (p.start, p.end) not in repeat_units]
    return v1.Predictions(defs, pred.uses, units, pred.identifiers)


def score(spec_path: Path) -> dict[str, Any]:
    """``evaluate.score`` with the engine's predictions read by ``engine_predictions_v2``."""
    original = _V1_ENGINE_PREDICTIONS
    current: dict[str, str] = {}

    def patched(doc: dict[str, Any]) -> v1.Predictions:
        return engine_predictions_v2(doc, current["text"])

    original_load = v1.load_bundle

    def load(path: Path) -> v1.Article:
        art = original_load(path)
        current["text"] = art.text
        return art

    v1.engine_predictions, v1.load_bundle = patched, load
    try:
        result = v1.score(spec_path)
    finally:
        v1.engine_predictions, v1.load_bundle = original, original_load
    result["protocol"] = PROTOCOL
    return result


def main() -> int:
    if sys.argv[1] == "score":
        sys.stdout.write(json.dumps(score(Path(sys.argv[2])), ensure_ascii=False, indent=1, default=str) + "\n")
        return 0
    return v1.main()


if __name__ == "__main__":
    sys.exit(main())
