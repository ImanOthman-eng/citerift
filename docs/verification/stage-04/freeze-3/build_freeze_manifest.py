"""Stage 04 final corrective cycle: the machine-readable manifest of the freeze-3 candidate (owner decision D-083,
item 13), built as the freeze-2 manifest (``../freeze-2/build_freeze_manifest.py``, kept unchanged with its freeze)
with the final-cycle evidence: the bib-1 specification and corpus, the dt-3 oracle beside the dt-1 and dt-2 oracles,
the regression on the exposed data, the role-collision study, the storage bounds, the reviews and the LOW disposition
table, and exposure manifest v3.

Run from the repository root after the freeze evidence is in place:

    uv run python docs/verification/stage-04/freeze-3/build_freeze_manifest.py

Reads only tracked repository files and the retained freeze evidence beside this script, and writes
``FREEZE_MANIFEST.json`` (indented, keys sorted) beside itself. The manifest digest is the SHA-256 of the canonical
encoding of the manifest (``citerift.investigation.canonical.canon`` with ``allow_float=True``, since the manifest holds
measured times); it is printed and recorded in ``FREEZE_REPORT.md``, never inside the manifest itself.

Two-record mechanism: this manifest is part of the freeze-content commit, so it cannot name that commit or its tree.
It names its parent commit, the code revision the evidence was produced from and the digest of every frozen file; the
attestation commit that follows names the content commit, its tree and the CI run on it.
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
FORMAT = "citerift-stage04-freeze/3"
BASELINE = "66633148c8226ef5bbd20b32d15a3c8c0bb7abf7"  # D-083 recorded; B-04-001 resolved for this cycle
PREVIOUS_FREEZES = [
    {
        "frozen_commit": "b5bf8edfcb6f7c747a9c751bd1d402858eecbcf0",
        "table_version": "dt-1",
        "status": "SUPERSEDED_AFTER_FAILED_04_I",
        "evaluation": "P, gate 04-I NOT PASSED (evaluation commit 1064113)",
        "manifest": f"{S04}/freeze/FREEZE_MANIFEST.json",
    },
    {
        "frozen_commit": "28ba6467c7005eec7bf51869974719a402059ca7",
        "table_version": "dt-2",
        "status": "accepted as D-076; gate 04-I NOT PASSED under P2 (D-080, evaluation commit 2b45931); historical, "
        "immutable; superseded only if the owner accepts this candidate",
        "evaluation": "P2, gate 04-I NOT PASSED (evaluation commit 2b45931)",
        "manifest": f"{S04}/freeze-2/FREEZE_MANIFEST.json",
    },
]
ORACLES = {
    "dt-1 (Step 4, frozen)": "simulations/stage04/oracle/MANIFEST.json",
    "dt-2 (corrective cycle, historical)": "simulations/stage04/oracle-dt2/MANIFEST.json",
    "dt-3 (final cycle)": "simulations/stage04/oracle-dt3/MANIFEST.json",
}
F3 = f"{S04}/freeze-3"
FC = f"{S04}/final-cycle"
EVIDENCE = {
    "d062_two_build_equivalence": f"{F3}/d062/two_build_equivalence.json",
    "d062_tamper_differential": f"{F3}/d062/tamper_differential.json",
    "vertical_slice": f"{F3}/vertical-slice/vertical_slice.json",
    "performance_breakdown": f"{F3}/performance/perf_breakdown.json",
    "verification_components": f"{F3}/performance/verification_components.json",
    "validation": f"{F3}/VALIDATION.json",
    "root_cause_and_architecture": f"{FC}/ROOT_CAUSE_AND_ARCHITECTURE.md",
    "bibliographic_specification": f"{FC}/BIBLIOGRAPHIC_SPEC.md",
    "build_vs_adopt": f"{FC}/BUILD_VS_ADOPT.md",
    "adversarial_corpus": f"{FC}/corpus/BIB_CORPUS.json",
    "fail_first_inputs": f"{FC}/fail-first/detector_inputs.json",
    "fail_first_dt2_engine": f"{FC}/fail-first/decided_by_dt2_engine_6663314.json",
    "fail_first_dt3_engine": f"{FC}/fail-first/decided_by_dt3_engine.json",
    "decision_space_dt3": f"{FC}/simulation/decision_space_dt3_summary.json",
    "dev_regression": f"{FC}/regression/DEV_REGRESSION.json",
    "campaign_regression": f"{FC}/regression/CAMPAIGN_REGRESSION.json",
    "p2_regression": f"{FC}/regression/P2_REGRESSION.json",
    "role_collision_census_dt3": f"{FC}/regression/census/CENSUS.json",
    "b03_census_dt3": f"{FC}/regression/census/B03_CENSUS.json",
    "pair_census_dt3": f"{FC}/regression/census/PAIR_CENSUS.json",
    "regression_report": f"{FC}/REGRESSION.md",
    "role_collision_study": f"{FC}/role-collision/ROLE_COLLISION_STUDY.json",
    "role_collision_report": f"{FC}/ROLE_COLLISION_STUDY.md",
    "performance_and_bounds": f"{FC}/PERFORMANCE_AND_BOUNDS.md",
    "storage_bounds": f"{FC}/bounds/bounds.json",
    "c07_profile": f"{FC}/lows/c07_profile.json",
    "description_sizes": f"{FC}/lows/description_sizes.json",
    "a04_invariant_census": f"{FC}/lows/a04_invariant_census.json",
    "author_coincidence": f"{FC}/lows/author_coincidence.json",
    "development_survey": f"{FC}/lows/survey_pairs.json",
    "identity_logical_view_diff": f"{FC}/identity/LOGICAL_VIEW_DIFF.json",
    "low_disposition": f"{FC}/LOW_DISPOSITION.md",
    "review_brief": f"{FC}/review/REVIEW_BRIEF.md",
    "review_a": f"{FC}/review/REVIEW_A.md",
    "review_b": f"{FC}/review/REVIEW_B.md",
    "review_c": f"{FC}/review/REVIEW_C.md",
    "review_d": f"{FC}/review/REVIEW_D.md",
    "review_e": f"{FC}/review/REVIEW_E.md",
    "review_f": f"{FC}/review/REVIEW_F.md",
    "review_g": f"{FC}/review/REVIEW_G.md",
}
EXPOSURE = f"{F3}/exposure/EXPOSURE_MANIFEST.json"
# The frozen decision semantics, by role.
SEMANTICS = {
    "decision_table_and_coherence": ["src/citerift/investigation/dt1.py"],
    "bibliographic_consistency": [
        "src/citerift/investigation/bibliographic.py",
        "src/citerift/investigation/data/bib-profile-1.json",
    ],
    "detector": ["src/citerift/investigation/adapters/detector.py", "src/citerift/investigation/adapters/detect.py"],
    "cited_description": ["src/citerift/investigation/adapters/normalize.py"],
    "evidence_identity": ["src/citerift/investigation/ids.py", "src/citerift/investigation/sets.py"],
    "report_and_projection_mappings": [
        "src/citerift/investigation/report.py",
        "src/citerift/investigation/projections.py",
        "src/citerift/investigation/explanations.py",
        "src/citerift/investigation/adapters/assemble.py",
    ],
    "outcome": ["src/citerift/investigation/report.py"],
    "canonical_stage02_identity_and_records": ["src/citerift/investigation/adapters/lookup.py"],
    "plan": ["src/citerift/investigation/adapters/plan.py", "src/citerift/investigation/workflow.py"],
}
LIMITATIONS = [
    "dt-3 / bib-1 (D-083): a material bibliographic conflict between the citation's own description and any event of "
    "the deciding lookup makes the candidate UNRESOLVED_IDENTITY (D-13a), never positive. bib-1 can block a positive, "
    "never create, restore or move one (dt-3 equals dt-2 case for case without a conflict: oracle-dt3).",
    "bib-1 recall costs on genuine citations (fail closed; BIBLIOGRAPHIC_SPEC.md section 9): a record that lists fewer "
    "authors than the citation, a misspelled or mixed-script record name, a genre word the citation adds to the "
    "record title ('Letter: X'), a title in another language, a conflicting bridged or co-keyed event of the same "
    "key. On the 243 design-exposed development pairs, 6 pairs (5 citations) abstain that an engineering reading "
    "of citation and record (not a label) takes for the retracted work itself (in-sample, never an estimate).",
    "bib-1 residual false compatibility (reviewer finding A-02): a commenter sharing a surname with the work's authors "
    "(3.3 % of random record pairs for one cited name), writing a note whose title holds the record's title and no "
    "lexicon word, stays positive; so does a related note cited with no comparable author whose extra title words "
    "are outside the lexicon or whose designation word is split by an invisible format character (review G-04); "
    "free-text references and identifier-only units have no description.",
    "bib-1 size bounds (spec 2.1 steps 1 and 6; reviewer findings E-02 and F-02): a citation source above 16,384 code "
    "points, a family above 64 values or a description above 4,096 code points has no description and decides as under "
    "dt-2 (development maxima: 5,722 code points, 56 values, 1,804 code points); a crafted unit under the source bound "
    "was measured at 6.5 s of parser time (one crafted shape, not a bound).",
    "D-071 recall cost: a citation whose only identifier is given by the checked sources as both the original and a "
    "notice (13,681 DOIs and 1,053 PMIDs in one record, 56 DOIs and 27 PMIDs across records, in the pinned snapshot) "
    "is UNRESOLVED_IDENTITY (IDENTIFIER_ROLE_COLLISION), never positive, even when the work is truly retracted.",
    "D-072 strict rule kept (D-083 item 5, ROLE_COLLISION_STUDY.md): bib-1 never resolves a role collision. In a "
    "same-record collision every event of the lookup describes a retracted work, never the notice, so bib-1 "
    "compares the citation with the same fields for both roles and cannot tell them apart; "
    "1,472 of 31,506 dt-1 positive DOI+PMID pairs stay UNRESOLVED_IDENTITY.",
    "D-073 (C-01): a second record of the same work makes a clean retraction abstain (53 snapshot pairs); no "
    "same-work-sibling exemption.",
    "D-075: an original DOI cited with the same record's notice PMID stays positive when the DOI is clean; the notice "
    "PMID is never positive support.",
    "The 232 development revisions, the 80 first-campaign and the 100 P2 articles are development evidence; the "
    "regression on them is not an evaluation, is never rescored and is never counted as unseen data.",
    "D-061 performance: the warm p95 of a retained investigation is above the 5 s target (NOT_MET, D-066); D-064 "
    "(per-process verify_index_identity) is not weakened.",
    "Storage: the maximal journal at the Stage 03 caps is 434,316,192 B (1.2x headroom) at 25,753 events per deciding "
    "lookup; above 32,030 events per deciding lookup a run is refused (JOURNAL_TOO_LARGE); LOOKUP observation v3 has a "
    "measured rho of 13.07 and no analytic bound; the Step 8 candidate-inputs terms have no derived bound (E-09).",
    "C-07: the role-collision scan is quadratic in a lookup's events (2.6 s at 3,000 synthetic events; below 0.03 s "
    "on the snapshot's largest keys); measured and retained.",
    "D-062 verification scope (D-064): each process runs verify_index_identity; Stage 02's per-event JSON-Schema pass "
    "runs only in Stage 02's complete verify; no tamper case is rejected by that pass alone.",
    "F-11: a descendant that leaves the session by double fork or setsid is attributed and killed only while it is "
    "found in the scan; the bound is per attempt, not per investigation.",
    "The external checkpoint (D-052) detects divergence from a recorded state; it is not authentication.",
    "Investigation Memory requires a local POSIX filesystem (rename, fsync, O_NOFOLLOW, flock semantics).",
    "Evaluation labels of a future gate are AI-generated (Stage 03 precedent); not human ground truth.",
    "The Stage 02 snapshot covers Retraction Watch records up to its build; later events are not covered.",
    "The reference models were written by the same engineering process as the production code; their independence "
    "is procedural (separate model, oracle and tests), not organisational.",
    "Accepted residuals re-reviewed (D-083 item 7): run idempotency depends on path spelling (use resume --key); a "
    "different bundle at the recorded path is STALE; Stage 02 crossref_sources has no ORDER BY (0 rows in the "
    "RW-only index).",
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
    from citerift.investigation import __version__, bibliographic, dt1
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
        "label": "Stage 04 freeze-3 candidate manifest (final corrective cycle, D-083). Frozen scientific code: the "
        "freeze-content commit that holds this file; named with its tree and CI run by the attestation commit that "
        "follows it. Not a freeze until the owner accepts it.",
        "previous_freezes": [{**f, "manifest_sha256": sha256_file(ROOT / f["manifest"])} for f in PREVIOUS_FREEZES],
        "baseline_sha": BASELINE,
        "parent_sha": git("rev-parse", "HEAD"),
        "stage04_identity": {
            **STAGE04_IDENTITY,
            "integration": dict(INTEGRATION_SCHEMAS),
            "package_version": __version__,
            "detector_identity": DETECTOR_IDENTITY,
            "bib_profile_sha256": bibliographic.PROFILE_SHA256,
            "parser_version": bibliographic.PARSER_VERSION,
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
        "oracle_manifests": {name: {"path": p, "sha256": sha256_file(ROOT / p)} for name, p in ORACLES.items()},
        "decision_table_version": dt1.TABLE_VERSION,
        "evidence": {name: {"path": p, "sha256": sha256_file(ROOT / p)} for name, p in EVIDENCE.items()},
        "vertical_slice": {
            "failed_checks": vs.get("failed_checks"),
            "cases": sorted(vs.get("cases", {})),
        },
        "d062_failed_checks": d062["failed_checks"],
        "d062_tamper_discrepancies": validation["d062"]["tamper_discrepancies"],
        "code_revision_of_the_evidence": validation["code_revision"],
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
    print(hashlib.sha256(canon(json.loads(text), allow_float=True)).hexdigest())
    return 0


if __name__ == "__main__":
    sys.exit(main())
