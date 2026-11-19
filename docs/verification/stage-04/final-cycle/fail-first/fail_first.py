"""Fail-first evidence (owner decision D-083, item 4): the detector-level corpus decided by a given engine source tree.

Usage: ``uv run python fail_first.py <engine src dir> detector_inputs.json > decided.json``

``detector_inputs.json`` holds, for every case of ``../corpus/BIB_CORPUS.json``, the cited description and the record
as the dt-3 code computes them (NORMALIZE and LOOKUP). Each case is decided as a matched retracted-work DOI candidate
(``step9_support.concretize``) by the detector of the given source tree. Run with the dt-2 tree (commit 6663314, engine
0.3.0) every MATERIAL_CONFLICT case is a D-14 positive, which the dt-3 tests forbid; with this tree it is D-13a.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

SRC = Path(sys.argv[1]).resolve()
REPO = Path(__file__).resolve().parents[5]
sys.path[:0] = [str(SRC), str(REPO / "tests" / "stage04"), str(REPO / "simulations" / "stage04")]

import dt3_reference as R3  # noqa: E402
import step9_support as S9  # noqa: E402

import citerift.investigation as ci  # noqa: E402
from citerift.investigation import dt1  # noqa: E402
from citerift.investigation.adapters.detector import dt1_detector  # noqa: E402

if not Path(ci.__file__).resolve().is_relative_to(SRC):
    raise SystemExit(f"the engine was imported from {ci.__file__}, not from {SRC}")


class WithBib:
    def __init__(self, case: Any, bib: tuple[Any, Any]) -> None:
        self._case = case
        self.bib = bib

    def __getattr__(self, name: str) -> Any:
        return getattr(self._case, name)


def main() -> None:
    cases = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    out: dict[str, Any] = {"engine": ci.__version__, "table_version": dt1.TABLE_VERSION, "cases": {}}
    for c in cases:
        base = R3.Case("CITED", "DOI", frozenset(), False, ("matched", "vf:retracted", False), None, None)
        inp, _ = S9.concretize(WithBib(base, (c["cited"], c["record"])))
        claim = dict(dt1_detector(inp).claims[0][0])
        out["cases"][c["id"]] = {
            "expect_object": c["object"],
            "rule": claim["rule"],
            "class": claim["class"],
            "reasons": sorted(claim["reasons"]),
        }
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
