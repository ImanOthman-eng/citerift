"""The inputs of the fail-first run (owner decision D-083, item 4; reviewer finding D-03): for every case of
``../corpus/BIB_CORPUS.json``, the cited description NORMALIZE computes (``bibliographic.cited_object``) and the record
fields LOOKUP keeps (``bibliographic.RecordObject``), as this tree's dt-3 code computes them.

The output is a pure function of the corpus and the bib-1 code; ``tests/stage04/test_final_provenance.py`` checks that
the committed ``detector_inputs.json`` equals ``inputs()``. Usage: ``uv run python detector_inputs.py`` (rewrites
``detector_inputs.json`` next to this file).
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

from citerift.investigation import bibliographic as B

HERE = Path(__file__).resolve().parent
CORPUS = HERE.parent / "corpus" / "BIB_CORPUS.json"


def inputs() -> list[dict[str, Any]]:
    out = []
    for c in json.loads(CORPUS.read_text(encoding="utf-8"))["cases"]:
        cited = B.cited_object(c["source"], c["wiki"])
        record = B.RecordObject.from_json(c["record"])
        out.append(
            {
                "id": c["id"],
                "object": c["expect"]["object"],
                "cited": cited.to_json() if cited is not None else None,
                "record": dataclasses.asdict(record) if record is not None else None,
            }
        )
    return out


def render() -> str:
    return json.dumps(inputs(), indent=1, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    (HERE / "detector_inputs.json").write_text(render(), encoding="utf-8")
