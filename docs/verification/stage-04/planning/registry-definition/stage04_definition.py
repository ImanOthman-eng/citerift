"""Owner decision D-1 (2026-11-09): the one-time Stage 04 registry-definition edit, and its proof.

citerift-gov has no command that defines a stage's owned paths, test suites or gates, so the owner approved one
controlled edit limited to those fields of Stage 04. This script is that edit. It refuses to write unless the
registry is in the expected state, changes only Stage 04's ``owned_paths``, ``required_test_suites`` and
``acceptance_gates``, writes the registry exactly as citerift-gov does (``json.dumps(indent=2,
ensure_ascii=False)`` plus a newline) and never touches PROJECT_STATUS.md (rendered afterwards by
``citerift-gov render-status --write``).

    python stage04_definition.py apply  <repo root>   # write the edit
    python stage04_definition.py verify <repo root> <before registry file>   # prove its boundary

``verify`` checks: every field other than the three is unchanged in every stage and at top level (policy,
project, history included); Stage 00-03 definitions are equal; no Stage 04 path equals, contains or lies inside
an owned path or verification directory of another stage; no tracked file exists yet under a new Stage 04 path.
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REGISTRY = "governance/stage_registry.json"
FIELDS = ("owned_paths", "required_test_suites", "acceptance_gates")

EXPECTED_BEFORE = {
    "owned_paths": [],
    "required_test_suites": ["unit", "integration", "negative", "regression"],
    "acceptance_gates": [
        {
            "id": "04-A",
            "requirement": (
                "A real documented investigation succeeds end-to-end, alongside negative and failure-case tests"
            ),
        }
    ],
}

DEFINITION = {
    "owned_paths": [
        "src/citerift/investigation",
        "schemas/investigation",
        "tests/stage04",
        "simulations/stage04",
    ],
    "required_test_suites": [
        "unit",
        "integration",
        "negative",
        "regression",
        "reproducibility",
        "security",
        "contracts",
        "simulation",
    ],
    "acceptance_gates": [
        {
            "id": "04-A",
            "requirement": (
                "A real documented investigation succeeds end-to-end, alongside negative and failure-case tests"
            ),
        },
        {
            "id": "04-B",
            "requirement": (
                "Contracts and investigation identity: Stage 04 schemas under schemas/investigation reference "
                "contracts v1 by URN without changing them; the root of every investigation is one immutable "
                "article revision (wiki, page id, revision id and, where a capture exists, its Stage 03 bundle "
                "identity), never title text alone; citation, reference and evidence units are its children; the "
                "subject model can be extended by later stages without breaking Stage 04 records (owner decision D-4)"
            ),
        },
        {
            "id": "04-C",
            "requirement": (
                "Detection semantics: a total, deterministic decision table with no numeric threshold; candidates "
                "only from primary citation fields and identifier links; retraction notices and marker targets never "
                "counted as citations of the retracted work; no value meaning 'not retracted'; a failure or an "
                "ambiguity never yields a positive or negative finding; zero differences against an independent "
                "reference model on the development set"
            ),
        },
        {
            "id": "04-D",
            "requirement": (
                "Cross-identifier coherence: when the DOI and PMID of one citation resolve to incompatible works the "
                "citation enters an explicit identity-conflict state; no positive or negative detection is emitted "
                "from that pair; both identities, their lookups and provenance are kept in Investigation Memory; the "
                "controller routes the case to needs-resolution; replay preserves the conflict; regression tests "
                "cover the Arabic Obokata citation (arwiki revision 76190003) and synthetic variants; Stages 02 and "
                "03 are not changed to hide it"
            ),
        },
        {
            "id": "04-E",
            "requirement": (
                "Investigation Memory and Workflow Controller: append-only, hash-chained journal with "
                "content-addressed evidence; explicit lifecycle and step state machines whose state is the fold of "
                "the journal; the memory/workflow invariants hold; an interrupted investigation resumes without "
                "repeating succeeded steps and reaches the same content digest; fault injection at every step "
                "boundary and write"
            ),
        },
        {
            "id": "04-F",
            "requirement": (
                "Replay and staleness: the same inputs reproduce byte-identical investigation content; a changed "
                "bundle, index, engine or schema is reported stale and never silently reused"
            ),
        },
        {
            "id": "04-G",
            "requirement": (
                "Failure containment: injected rate limits, upstream errors, timeouts, a missing or mismatched index "
                "and failed extraction end blocked, partial or failed with recorded limitations, never as a negative "
                "finding or a success"
            ),
        },
        {
            "id": "04-H",
            "requirement": (
                "Security and boundaries: no import of citerift.governance; no network use outside the Stage 03 "
                "capture path; path safety of investigation stores; secret scan of retained evidence"
            ),
        },
        {
            "id": "04-I",
            "requirement": (
                "Scientific evaluation under a protocol pre-registered before the draw (owner decisions D-3, D-5): "
                "sampling procedure, strata, replacement rules, minimum positive, negative and identity-conflict "
                "denominators, metrics, interval method and failure criteria fixed in advance; 30 primary and 10 "
                "predetermined reserve articles per language, expanded within 200 acquisition attempts when a "
                "denominator is not met, never weakened; labels from two independent blinded Claude Sonnet "
                "annotators locked before predictions are exposed, disagreements adjudicated by a third blinded "
                "Claude Sonnet instance, with retained evidence and model metadata, disclosed as AI-generated labels "
                "from one vendor and not human gold labels; one locked prediction run; uncertainty intervals and no "
                "population-prevalence claim; Stage 03 revisions examined during planning are not final-evaluation "
                "evidence"
            ),
        },
        {
            "id": "04-J",
            "requirement": (
                "Engineering verification and delivery: complete suite on Python 3.12 and 3.13, ruff check and "
                "format, mypy, citerift-gov check and successful GitHub CI at the cited revision; no new runtime "
                "dependency without a recorded reason; required documents including a measured creative "
                "differentiation review; unmerged pull request"
            ),
        },
    ],
}


def _stage(reg: dict[str, Any], sid: str) -> dict[str, Any]:
    return next(s for s in reg["stages"] if s["id"] == sid)


def _inside(a: str, b: str) -> bool:
    """True when path a equals b or lies inside it (component-wise)."""
    a, b = a.rstrip("/"), b.rstrip("/")
    return a == b or a.startswith(b + "/")


def apply(root: Path) -> None:
    path = root / REGISTRY
    reg = json.loads(path.read_text(encoding="utf-8"))
    s04 = _stage(reg, "04")
    for f in FIELDS:
        if s04[f] != EXPECTED_BEFORE[f]:
            sys.exit(f"refused: Stage 04 {f} is not in the expected state")
    if s04["status"] != "IN_PROGRESS":
        sys.exit("refused: Stage 04 is not IN_PROGRESS")
    for f in FIELDS:
        s04[f] = copy.deepcopy(DEFINITION[f])
    path.write_text(json.dumps(reg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Stage 04 definition written; now run: citerift-gov render-status --write")


def verify(root: Path, before_file: Path) -> int:
    before = json.loads(before_file.read_text(encoding="utf-8"))
    after = json.loads((root / REGISTRY).read_text(encoding="utf-8"))
    problems: list[str] = []
    b_rest = {k: v for k, v in before.items() if k != "stages"}
    a_rest = {k: v for k, v in after.items() if k != "stages"}
    if b_rest != a_rest:
        problems.append("top-level registry fields (policy, project, history, ...) changed")
    if [s["id"] for s in before["stages"]] != [s["id"] for s in after["stages"]]:
        problems.append("stage list changed")
    for b, a in zip(before["stages"], after["stages"], strict=True):
        if b["id"] != "04":
            if b != a:
                problems.append(f"stage {b['id']} changed")
            continue
        for k in sorted(set(b) | set(a)):
            if k not in FIELDS and b.get(k) != a.get(k):
                problems.append(f"stage 04 field {k} changed")
        for f in FIELDS:
            if a[f] != DEFINITION[f]:
                problems.append(f"stage 04 {f} is not the approved definition")
    print(
        "unchanged: top level (policy, project, history), stages 00-03 and 05-09, every other Stage 04 field"
        if not problems
        else ""
    )
    s04 = _stage(after, "04")
    for p in s04["owned_paths"]:
        for other in after["stages"]:
            if other["id"] == "04":
                continue
            for q in [*other["owned_paths"], other["verification_dir"]]:
                if _inside(p, q) or _inside(q, p):
                    problems.append(f"collision: Stage 04 {p} with Stage {other['id']} {q}")
        if _inside(p, s04["verification_dir"]) or _inside(s04["verification_dir"], p):
            problems.append(f"collision: {p} with Stage 04 verification directory")
        tracked = subprocess.run(  # noqa: S603
            ["git", "-C", str(root), "ls-files", "--", p],  # noqa: S607
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()
        if tracked:
            problems.append(f"{p} already holds tracked files: {tracked[:3]}")
        print(
            f"owned path {p}: no collision with any other stage's owned paths or verification directory; "
            f"{len(tracked)} tracked files"
        )
    for other in after["stages"]:
        print(f"  stage {other['id']} owned: {other['owned_paths']} verification: {other['verification_dir']}")
    for msg in problems:
        print("PROBLEM:", msg)
    print("RESULT:", "PASS" if not problems else "FAIL")
    return 1 if problems else 0


if __name__ == "__main__":
    if sys.argv[1:2] == ["apply"]:
        apply(Path(sys.argv[2]))
    elif sys.argv[1:2] == ["verify"]:
        raise SystemExit(verify(Path(sys.argv[2]), Path(sys.argv[3])))
    else:
        raise SystemExit(__doc__)
