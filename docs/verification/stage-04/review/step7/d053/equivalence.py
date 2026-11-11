"""Owner decision D-053 / D-054, scientific invariance: the logical content of an investigation is the same before
(``64e7aca``, one ``evidence_recorded`` record per item, journal format 2) and after (evidence batches, format 3).

For each scenario the same SYNTHETIC fake adapters (``tests/stage04/controller_support.py`` of the tree being run)
drive an investigation to its end. The script then reads the committed content of the journal and reduces it to the
**logical view**, which does not depend on the storage representation:

- every committed evidence item (read from its record before, from its batch blob after), as a set by evidence id;
- every committed claim, decision and question (opened and closed) payload;
- every committed observation ``{obs_kind, blob}`` in commit order;
- the lifecycle and outcome.

The report blob is excluded: before D-054 the fake ASSEMBLE wrote a placeholder, not a report (Step 8 builds the
real one), so there is nothing scientific to compare; its structure is checked by ``report.py``.

Usage (run once per tree; the tree's ``src`` and ``tests/stage04`` are imported first)::

    uv run python docs/verification/stage-04/review/step7/d053/equivalence.py --tree <checkout> --out <file.json>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

SCENARIOS: dict[str, tuple[tuple[str, str], ...]] = {
    "not found and retracted": (("NOT_FOUND_IN_CHECKED_SOURCES", "c1"), ("RETRACTED_WORK_CITED", "c2")),
    "identity conflict": (("IDENTITY_CONFLICT", "c1"),),
    "source contradiction beside a finding": (("CONTRADICTION_IN_SOURCES", "c1"), ("RETRACTED_WORK_CITED", "c2")),
    "lookup unavailable": (("LOOKUP_UNAVAILABLE", "c1"),),
    "every positive class": (
        ("RETRACTED_WORK_CITED", "c1"),
        ("CONCERN_CITED", "c2"),
        ("CORRECTION_CITED", "c3"),
        ("REINSTATED_WORK_CITED", "c4"),
    ),
}


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def logical_view(tree: Path, classes: tuple[tuple[str, str], ...]) -> dict[str, Any]:
    from controller_support import Env, Plan, StepClock, create, run_once  # noqa: PLC0415

    from citerift.investigation.memory import InvestigationMemory  # noqa: PLC0415

    with tempfile.TemporaryDirectory() as d:
        clock = StepClock()
        root, key = create(Path(d), clock=clock)
        st = run_once(root, key, Plan(classes=classes), Env(), clock)
        with InvestigationMemory.open(root, key, writable=False) as mem:
            f = mem.view
            evidence: dict[str, Any] = {}
            claims, decisions, questions, observations = [], [], [], []
            for rec in f.committed_content():
                kind, p = rec["kind"], rec["payload"]
                if kind == "evidence_recorded":  # format 2
                    evidence[p["evidence_id"]] = p
                elif kind == "evidence_batch_recorded":  # format 3 (D-053)
                    for item in json.loads(mem.blobs.get(p["batch"]))["items"]:
                        evidence[item["evidence_id"]] = item
                elif kind == "claim_recorded":
                    claims.append(p)
                elif kind == "decision_recorded":
                    decisions.append(p)
                elif kind in ("question_opened", "question_closed"):
                    questions.append({"kind": kind, **p})
                elif kind == "observation_recorded":
                    observations.append({"obs_kind": p["obs_kind"], "blob": p["blob"]})
    view = {
        "lifecycle": st.lifecycle,
        "outcome": st.outcome,
        "evidence": [evidence[k] for k in sorted(evidence)],
        "claims": sorted(claims, key=_canon),
        "decisions": sorted(decisions, key=_canon),
        "questions": sorted(questions, key=_canon),
        "observations": observations,
    }
    return {
        "counts": {k: len(v) for k, v in view.items() if isinstance(v, list)},
        "digest": hashlib.sha256(_canon(view).encode()).hexdigest(),
        "view": view,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    tree = args.tree.resolve()
    sys.path[:0] = [str(tree / "src"), str(tree / "tests" / "stage04")]
    import citerift  # noqa: PLC0415

    if not (Path(citerift.__file__).resolve().is_relative_to(tree)):
        raise SystemExit(citerift.__file__)
    from citerift.investigation.journal import JOURNAL_FORMAT  # noqa: PLC0415

    head = subprocess.run(["git", "-C", str(tree), "rev-parse", "HEAD"], capture_output=True, text=True, check=True)  # noqa: S603, S607
    status = ["git", "-C", str(tree), "status", "--porcelain"]
    dirty = subprocess.run(status, capture_output=True, text=True, check=True)  # noqa: S603
    out = {
        "tree_head": head.stdout.strip(),
        "tree_dirty": bool(dirty.stdout.strip()),
        "journal_format": JOURNAL_FORMAT,
        "scenarios": {name: logical_view(tree, classes) for name, classes in SCENARIOS.items()},
    }
    args.out.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: v["digest"] for k, v in out["scenarios"].items()}, indent=2))


if __name__ == "__main__":
    main()
