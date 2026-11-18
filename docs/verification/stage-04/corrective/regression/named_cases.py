"""Corrective cycle (owner decision D-071 section 8): the named regression cases, dt-2 against the frozen dt-1.

DEVELOPMENT AND REGRESSION EVIDENCE ONLY (design-exposed bundles). The named cases of D-071 are the vertical-slice
bundles: MMR vaccine (Wakefield), Haruko Obokata (ar and en), GFAJ-1, the expression of concern, BCAS3 and the two
reserve articles. Each runs one offline investigation through the production plan (``regress.one``); every claim is
decided by dt-2 (recorded) and by the frozen dt-1 on the same committed inputs. Owner decisions D-058, D-059 and D-060
are pinned by named tests (``test_step9_detector.py``, ``test_step9_real.py``, ``test_step9_b8.py``), run in the full
suite.

    uv run python -P docs/verification/stage-04/corrective/regression/named_cases.py --index I --out NAMED_CASES.json
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from collections import Counter
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import regress as RG

S03 = "docs/verification/stage-03"
C11 = f"{S03}/evaluation/confirmation-2026-11/campaign/capture/bundles"
CASES = {
    "VS-1 MMR vaccine (Wakefield)": f"{S03}/demonstrations/bundles/en-1381772671",
    "VS-2 Haruko Obokata (ar)": "tests/stage03/fixtures/observed/ar-76190003",
    "VS-3a Haruko Obokata (en)": "tests/stage03/fixtures/observed/en-1372543632",
    "VS-3b GFAJ-1": f"{S03}/demonstrations/bundles/en-1374726997",
    "VS-4 expression of concern": f"{C11}/challenge/en-65547507-a1",
    "VS-5 BCAS3": f"{S03}/evaluation/capture/bundles/challenge/ar-4541237-a1",
    "VS-6a reserve (ar)": f"{S03}/evaluation/capture/bundles/reserve/ar-9617858-a1",
    "VS-6b reserve (en)": f"{C11}/reserve1/en-44351447-a1",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    prov = RG.F1.provenance(a.index)
    cases = {}
    with tempfile.TemporaryDirectory() as d, pytest.MonkeyPatch.context() as mp:
        offline = RG.S8.NoNetwork(mp)
        for i, (name, rel) in enumerate(CASES.items()):
            row = RG.one(Path(d) / str(i), RG.REPO / rel, a.index.resolve())
            cands = row.pop("all_candidates", [])
            cases[name] = {
                "bundle": rel,
                "lifecycle": row["lifecycle"],
                "verified": row["verified"],
                "candidates": row["candidates"],
                "recorded_equals_dt2": row.get("recorded_equals_dt2", True),
                "dt1_classes": dict(sorted(Counter(c["dt1"]["class"] for c in cands).items())),
                "dt2_classes": dict(sorted(Counter(c["dt2"]["class"] for c in cands).items())),
                "changed": row.get("changed", []),
            }
            print(name, row["lifecycle"], len(row.get("changed", [])), flush=True)
        attempts = len(offline.attempts)
    out = {
        "label": "DEVELOPMENT AND REGRESSION EVIDENCE ONLY (design-exposed named cases); not an evaluation",
        "provenance": prov,
        "tool_sha256": RG.file_sha256(Path(__file__)),
        "network_attempts": attempts,
        "unchanged": all(not c["changed"] and c["recorded_equals_dt2"] for c in cases.values()),
        "cases": cases,
    }
    RG.write_json(a.out, out)
    print({"unchanged": out["unchanged"], "network_attempts": attempts})
    return 0


if __name__ == "__main__":
    sys.exit(main())
