"""Stage 04 Step 12: the machine-readable freeze manifest (owner Step 12 message, sections 20 and 21).

Run from the repository root after the freeze evidence is in place:

    uv run python docs/verification/stage-04/freeze/build_freeze_manifest.py

Reads only tracked repository files and the retained freeze evidence beside this script, and writes
``FREEZE_MANIFEST.json`` (indented, keys sorted) beside itself. The manifest digest is the SHA-256 of the canonical
encoding of the manifest (``citerift.investigation.canonical.canon``: sorted keys, no insignificant whitespace,
UTF-8); it is printed and recorded in ``FREEZE_REPORT.md``, never inside the manifest itself.

Two-record mechanism (section 22): this manifest is part of the freeze-content commit, so it cannot name that
commit or its tree. It names its parent (the corrections commit the evidence was produced from) and the digest of
every frozen file; the attestation commit that follows names the content commit, its tree and the CI run on it.
"""

# ruff: noqa: PLC0415

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
S04 = "docs/verification/stage-04"
FORMAT = "citerift-stage04-freeze/1"
BASELINE = "65c30bde697dced5f1698fb3db46707b939cc0c7"
ORACLE = "simulations/stage04/oracle/MANIFEST.json"
EVIDENCE = {
    "d062_two_build_equivalence": f"{S04}/freeze/d062/two_build_equivalence.json",
    "d062_tamper_differential": f"{S04}/freeze/d062/tamper_differential.json",
    "vertical_slice": f"{S04}/freeze/vertical-slice/vertical_slice.json",
    "performance_breakdown": f"{S04}/freeze/performance/perf_breakdown.json",
    "validation": f"{S04}/freeze/VALIDATION.json",
    "triage": f"{S04}/review/step12/STEP12_TRIAGE.md",
    "prior_art_04j": f"{S04}/review/step12/PRIOR_ART_04J.md",
}
EXPOSURE = f"{S04}/freeze/exposure/EXPOSURE_MANIFEST.json"
# The frozen decision semantics (section 20), by role.
SEMANTICS = {
    "decision_table_and_coherence": ["src/citerift/investigation/dt1.py"],
    "detector": ["src/citerift/investigation/adapters/detector.py", "src/citerift/investigation/adapters/detect.py"],
    "evidence_identity": ["src/citerift/investigation/ids.py", "src/citerift/investigation/sets.py"],
    "report_and_projection_mappings": [
        "src/citerift/investigation/report.py",
        "src/citerift/investigation/projections.py",
        "src/citerift/investigation/explanations.py",
        "src/citerift/investigation/adapters/assemble.py",
    ],
    "outcome": ["src/citerift/investigation/report.py"],
    "canonical_stage02_identity": ["src/citerift/investigation/adapters/lookup.py"],
    "plan": ["src/citerift/investigation/adapters/plan.py", "src/citerift/investigation/workflow.py"],
}
LIMITATIONS = [
    "D-061 performance: the warm p95 of a retained investigation is above the 5 s target (NOT_MET); see the "
    "performance section of FREEZE_REPORT.md for the residual cases and bottlenecks.",
    "D-062 verification scope (D-064, owner decision OD-S12-1): each process runs the D-062 identity-verification "
    "profile (verify_index_identity: format and policy, integrity and structure, digests recomputed against the "
    "metadata, build manifest, full derivation recompute); Stage 02's per-event JSON-Schema pass runs only in Stage "
    "02's complete verify (the certification, run in the Step 12 evidence); in the differential tamper evidence no "
    "case is rejected by that pass alone.",
    "F-11: a descendant that leaves the session by double fork or setsid is attributed and killed only while it is "
    "found in the scan; the bound is per attempt, not per investigation.",
    "The external checkpoint (D-052) detects divergence from a recorded state; it is not authentication or a "
    "signature.",
    "Investigation Memory requires a local POSIX filesystem (rename, fsync, O_NOFOLLOW, flock semantics).",
    "Evaluation labels planned for Step 14 are AI-generated (Stage 03 precedent); not human ground truth.",
    "The Stage 02 snapshot covers Retraction Watch records up to its build; later events are not covered.",
    "Some dt-1 classes were not seen in real development data; they are covered by the Step 4 enumerated domain "
    "and synthetic tests only.",
    "A11-5: the lifecycle distinction BLOCKED versus RUNNING-and-waiting is kept in the journal and the JSON "
    "output; the user-facing status is blocked (exit 8) for both.",
    "A11-6: journals keep the absolute bundle, index and memory-root paths of the creating host as provenance; they "
    "enter no scientific digest, and moved inputs are named with --index and --bundle (no journal rewriting).",
    "The Step 4 reference model was written by the same engineering process as the production code; its "
    "independence is procedural (separate model, oracle and tests), not organisational.",
    "A-07: D-7 drops taint reasons that D-6 keeps (frozen Step 4 model and SPEC 7.3 agree).",
    "B-03 residual: a retry whose earlier ACQUIRE side channel was deleted by someone is not detected.",
    "B-13: LOOKUP memory is bounded per query; the aggregate is queries x per-query bound.",
    "C-12: Stage 02 crossref_sources has no ORDER BY (upstream; 0 rows in the accepted RW-only index).",
    "E-05, E-06, E-08: denominator and sensitivity-variant choices are Step 13 pre-registration decisions.",
]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.run(  # noqa: S603 - fixed argv
        ["git", "-C", str(ROOT), *args],  # noqa: S607
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()


def tracked(prefix: str) -> list[str]:
    return sorted(p for p in git("ls-files", "-z", prefix).split("\0") if p)


def digests(paths: list[str]) -> dict[str, str]:
    return {p: sha256_file(ROOT / p) for p in paths}


def build() -> dict[str, Any]:
    from citerift.investigation import __version__
    from citerift.investigation.adapters import lookup
    from citerift.investigation.adapters.detector import DETECTOR_IDENTITY
    from citerift.investigation.adapters.extract import ExtractConfig, extraction_identity
    from citerift.investigation.adapters.plan import INTEGRATION_SCHEMAS, STAGE04_IDENTITY

    d062 = json.loads((ROOT / EVIDENCE["d062_two_build_equivalence"]).read_text(encoding="utf-8"))
    vs = json.loads((ROOT / EVIDENCE["vertical_slice"]).read_text(encoding="utf-8"))
    perf = json.loads((ROOT / EVIDENCE["performance_breakdown"]).read_text(encoding="utf-8"))
    validation = json.loads((ROOT / EVIDENCE["validation"]).read_text(encoding="utf-8"))
    source = tracked("src/citerift/investigation")
    schemas = tracked("schemas/investigation")
    return {
        "format": FORMAT,
        "label": "Stage 04 freeze manifest (Step 12). Frozen scientific code: the freeze-content commit that holds "
        "this file; named with its tree and CI run by the attestation commit that follows it.",
        "baseline_sha": BASELINE,
        "parent_sha": git("rev-parse", "HEAD"),
        "stage04_identity": {
            **STAGE04_IDENTITY,
            "integration": dict(INTEGRATION_SCHEMAS),
            "package_version": __version__,
            "detector_identity": DETECTOR_IDENTITY,
        },
        "decision_semantics": {role: digests(paths) for role, paths in SEMANTICS.items()},
        "canonical_stage02_identity": {
            "definition": "snapshot_id, policy_version, lookup_schema_version, artifact_digest (scientific); "
            "semantic_digest, export_lines (consistency); verified by Stage 02 checks before use (D-062)",
            "digest_keys": list(lookup.DIGEST_KEYS),
            "verification_profile": "verify_index_identity (OD-S12-1)",
            "accepted_snapshot": d062["builds"]["A"]["identity"],
            "csv_sha256": d062["csv_sha256"],
        },
        "stage03_extraction_identity": extraction_identity(ExtractConfig()),
        "schemas": digests(schemas),
        "source_files": digests(source),
        "lockfile": {"uv.lock": sha256_file(ROOT / "uv.lock"), "pyproject.toml": sha256_file(ROOT / "pyproject.toml")},
        "exposure_manifest": {"path": EXPOSURE, "sha256": sha256_file(ROOT / EXPOSURE)},
        "step4_oracle_manifest": {"path": ORACLE, "sha256": sha256_file(ROOT / ORACLE)},
        "evidence": {name: {"path": p, "sha256": sha256_file(ROOT / p)} for name, p in EVIDENCE.items()},
        "vertical_slice": {
            "failed_checks": vs.get("failed_checks"),
            "cases": sorted(vs.get("cases", {})),
        },
        "d062_failed_checks": d062["failed_checks"],
        "performance": validation["performance"],
        "performance_breakdown_median": perf["median"],
        "tests": validation["tests"],
        "limitations": LIMITATIONS,
    }


def main() -> int:
    from citerift.investigation.canonical import canon

    manifest = build()
    text = json.dumps(manifest, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    (HERE / "FREEZE_MANIFEST.json").write_text(text, encoding="utf-8")
    print(hashlib.sha256(canon(json.loads(text))).hexdigest())
    return 0


if __name__ == "__main__":
    sys.exit(main())
