"""Stage 04 P2: the pre-registration manifest and its digest (PREREGISTRATION.md section 4.1).

Lists every pre-registered file of P2 with its SHA-256 (every file under ``evaluation-p2/`` except this manifest, and
the external inputs P2 reads), the frozen-engine identity, the exposure manifest v2 and the historical P it supersedes
as the plan of record (that P and its files stay unchanged, D-074, D-076). The manifest's canonical digest
(``p2_common.digest``: sorted keys, no whitespace, UTF-8, SHA-256) is the pre-registration digest ``P`` that the
owner accepts and that the seed binds.

    python -P docs/verification/stage-04/evaluation-p2/tools/p2_manifest.py          # write and print P2
    python -P docs/verification/stage-04/evaluation-p2/tools/p2_manifest.py --check  # compare files with the manifest
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from p2_common import EVALUATION, REPO, digest, file_sha256, read_json, write_json

FORMAT = "citerift-stage04-eval-preregistration-manifest/2"
MANIFEST = EVALUATION / "PREREGISTRATION_MANIFEST.json"
EXTERNAL = (
    "docs/verification/stage-01/data/census/ar_scan.json",
    "docs/verification/stage-01/scripts/stage01_census.py",
    "docs/verification/stage-03/evaluation/confirmation-d036/scripts/exposure_set.py",
    "docs/verification/stage-04/evaluation/frame/en_scan.json",
    "docs/verification/stage-04/evaluation/frame/listed_tier.json",
    "docs/verification/stage-04/evaluation/PREREGISTRATION_MANIFEST.json",
    "docs/verification/stage-04/freeze-2/FREEZE_MANIFEST.json",
    "docs/verification/stage-04/freeze-2/exposure/EXPOSURE_MANIFEST.json",
    "tests/stage04/test_p2_evaluation.py",
)
HISTORICAL_P = {
    "digest": "4eded723bbb464c247b31e675d2f2fc7d16133328d55925c9a787801efd1098a",
    "commit": "827ac1aa1d9d16d444d4860e4119f8633d8e802e",
    "status": "historical evidence, immutable (D-071, D-074, D-076); P2 does not change it",
}


def files() -> list[str]:
    own = sorted(
        str(p.relative_to(REPO))
        for p in EVALUATION.rglob("*")
        if p.is_file() and p != MANIFEST and "__pycache__" not in p.parts
    )
    return own + list(EXTERNAL)


def build() -> dict[str, Any]:
    params = read_json(EVALUATION / "PARAMETERS.json")
    return {
        "format": FORMAT,
        "frozen_engine": params["frozen_engine"],
        "exposure": params["exposure"],
        "historical_p": HISTORICAL_P,
        "retraction_watch": params["retraction_watch"],
        "files": [{"path": f, "sha256": file_sha256(REPO / f)} for f in files()],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Stage 04 P2 pre-registration manifest")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    if a.check:
        recorded = read_json(MANIFEST)
        now = build()
        if recorded != now:
            changed = sorted(
                {f["path"] for f in recorded["files"]} ^ {f["path"] for f in now["files"]}
                | {
                    f["path"]
                    for f in recorded["files"]
                    if (REPO / f["path"]).exists() and file_sha256(REPO / f["path"]) != f["sha256"]
                }
            )
            print("differs:", changed)
            return 1
        print("matches; P =", digest(recorded))
        return 0
    m = build()
    write_json(MANIFEST, m)
    print(digest(m))
    return 0


if __name__ == "__main__":
    sys.exit(main())
