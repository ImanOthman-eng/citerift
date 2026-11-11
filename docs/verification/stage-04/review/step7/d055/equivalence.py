"""Owner decision D-055, scientific invariance: the logical content of an investigation is the same before
(``0097a93``, journal format 3: one record per lookup observation, claim, decision and question) and after (format 4:
LOOKUP batches and DETECT candidate-result batches).

For each scenario the same SYNTHETIC fake adapters (``tests/stage04/controller_support.py`` of the tree being run,
plus the LOOKUP and DETECT adapters defined here, which use only the adapter interface both trees share) drive an
investigation to its end. The committed content is reduced to the **logical view**, which does not depend on the
storage representation:

- every committed evidence item (read from its batch blob), as a set by evidence id;
- every committed claim, decision and question payload, as sorted lists;
- the committed ``{obs_kind, blob, source_ref}`` of each observation: bundle and extraction observations in commit
  order, lookup observations as a sorted multiset. Format 3 commits lookup observations in the adapter's order,
  format 4 in the canonical order of SPEC 8.9; the order of lookup references carries no meaning (they are
  content-addressed, and the report orders its observations by digest), so only the multiset is compared;
- the lifecycle, outcome and the failing step's code when the run ends failed.

Scenario names say exactly which claim classes DETECT commits; a scenario whose DETECT fails names the failure.

Usage (run once per tree; the tree's ``src`` and ``tests/stage04`` are imported first)::

    uv run python docs/verification/stage-04/review/step7/d055/equivalence.py --tree <checkout> --out <file.json>
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

# name -> (DETECT classes with their candidate, number of distinct lookup observations, shared lookup, DETECT change)
SCENARIOS: dict[str, tuple[tuple[tuple[str, str], ...], int, bool, str | None]] = {
    "positive finding (RETRACTED_WORK_CITED)": ((("RETRACTED_WORK_CITED", "c1"),), 1, False, None),
    "not found in checked sources": ((("NOT_FOUND_IN_CHECKED_SOURCES", "c1"),), 1, False, None),
    "lookup unavailable": ((("LOOKUP_UNAVAILABLE", "c1"),), 1, False, None),
    "identity conflict": ((("IDENTITY_CONFLICT", "c1"),), 1, False, None),
    "contradiction in sources": ((("CONTRADICTION_IN_SOURCES", "c1"),), 1, False, None),
    "terminal DETECT failure (decision-table gap: a claim of an unknown class)": (
        (("NOT_FOUND_IN_CHECKED_SOURCES", "c1"),),
        1,
        False,
        "unknown class",
    ),
    "terminal DETECT failure (adapter exception: the synthetic DETECT has no CONCERN_CITED claim)": (
        (("RETRACTED_WORK_CITED", "c1"), ("CONCERN_CITED", "c2")),
        1,
        False,
        None,
    ),
    "mixed article (RETRACTED, NOT_FOUND, LOOKUP_UNAVAILABLE, IDENTITY_CONFLICT, CONTRADICTION;"
    " 5 lookups, one shared)": (
        (
            ("RETRACTED_WORK_CITED", "c1"),
            ("NOT_FOUND_IN_CHECKED_SOURCES", "c2"),
            ("LOOKUP_UNAVAILABLE", "c3"),
            ("IDENTITY_CONFLICT", "c4"),
            ("CONTRADICTION_IN_SOURCES", "c5"),
        ),
        4,
        True,
        None,
    ),
}


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def logical_view(name: str) -> dict[str, Any]:
    from controller_support import LOOKUP, Env, Plan, StepClock, create, digest, ok_result, run_once  # noqa: PLC0415

    from citerift.investigation.adapters import ContentRecord, Succeeded  # noqa: PLC0415
    from citerift.investigation.memory import InvestigationMemory  # noqa: PLC0415

    classes, n_lookups, shared, change = SCENARIOS[name]

    def lookup(req: Any) -> Any:
        values = [LOOKUP, *({"lookup": "SYNTHETIC", "candidate": i} for i in range(1, n_lookups))]
        refs = [
            {
                "obs_kind": "lookup",
                "blob": digest(v),
                "source_ref": {"engine": "citerift.retraction", "operation": "gather", "locator": f"doi:10.1000/{i}"},
            }
            for i, v in enumerate(values)
        ]
        if shared:  # two candidates share one lookup: the same reference twice
            refs.append(dict(refs[0]))
        refs.reverse()  # an adapter order that is not the canonical one
        return Succeeded(
            records=tuple(ContentRecord("observation_recorded", r) for r in refs),
            blobs=tuple(values),
            outputs=(digest(LOOKUP),),
        )

    def detect(req: Any) -> Any:
        r = ok_result(req, classes)
        if change == "unknown class":
            recs = tuple(
                ContentRecord(c.kind, {**c.payload, "class": "NOT_A_CLASS"}) if c.kind == "claim_recorded" else c
                for c in r.records
            )
            return Succeeded(records=recs, blobs=r.blobs, outputs=r.outputs)
        return r

    script = {("LOOKUP", a): lookup for a in (1, 2, 3)} | {("DETECT", a): detect for a in (1, 2, 3)}
    with tempfile.TemporaryDirectory() as d:
        clock = StepClock()
        root, key = create(Path(d), clock=clock)
        st = run_once(root, key, Plan(script, classes=classes), Env(), clock)
        with InvestigationMemory.open(root, key, writable=False) as mem:
            f = mem.view
            failure = [
                {"step": r["step"], "code": r["payload"]["code"], "reason": r["payload"]["reason"]}
                for r in f.records
                if r["kind"] == "step_failed"
            ]
            evidence: dict[str, Any] = {}
            claims, decisions, questions, observations, lookups = [], [], [], [], []
            for rec in f.committed_content():
                kind, p = rec["kind"], rec["payload"]
                if kind == "evidence_batch_recorded":
                    for item in json.loads(mem.blobs.get(p["batch"]))["items"]:
                        evidence[item["evidence_id"]] = item
                elif kind == "claim_recorded":
                    claims.append(p)
                elif kind == "decision_recorded":
                    decisions.append(p)
                elif kind in ("question_opened", "question_closed"):
                    questions.append({"kind": kind, **p})
                elif kind == "observation_recorded" and p["obs_kind"] == "lookup":
                    lookups.append(p)
                elif kind == "observation_recorded":
                    observations.append(p)
    view = {
        "lifecycle": st.lifecycle,
        "outcome": st.outcome,
        "failures": failure,
        "evidence": [evidence[k] for k in sorted(evidence)],
        "claims": sorted(claims, key=_canon),
        "decisions": sorted(decisions, key=_canon),
        "questions": sorted(questions, key=_canon),
        "observations": observations,
        "lookup_observations": sorted(lookups, key=_canon),
    }
    return {
        "counts": {k: len(v) for k, v in view.items() if isinstance(v, list)},
        "claim_classes": sorted(c["class"] for c in claims),
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
        "scenarios": {name: logical_view(name) for name in SCENARIOS},
    }
    args.out.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {k: (v["digest"], v["view"]["lifecycle"], v["claim_classes"]) for k, v in out["scenarios"].items()},
            indent=1,
        )
    )


if __name__ == "__main__":
    main()
