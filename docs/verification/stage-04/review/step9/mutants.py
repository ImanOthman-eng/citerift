"""Step 9 mutation testing of the production detector (owner Step 9 item 16).

Each mutant is a textual change to a copy of ``src/`` (never to the repository): every ``old`` string must occur
exactly once in its file, or the mutant is refused as stale. The mutated copy is put first on ``PYTHONPATH`` and the
Step 9 suites run against it:

- ``tests/stage04/test_step9_detector.py`` (synthetic, every valid decision signature of the frozen model, kappa
  variants, guards), ``tests/stage04/test_step9_b8.py`` and ``tests/stage04/test_step9_real.py`` (real bundles);
- with ``--differential``, the differential against the frozen oracle on the 244,884 valid cases as well.

A mutant is **caught** when at least one of them fails. Writes ``mutants.json`` beside itself.

Run: ``uv run python docs/verification/stage-04/review/step9/mutants.py [--differential]``
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
DT1 = "citerift/investigation/dt1.py"
DET = "citerift/investigation/adapters/detector.py"
WF = "citerift/investigation/workflow.py"

D6 = '    ("D-6", lambda x: x.c.shape == "PAIR" and x.kappa == INCOMPATIBLE),\n'
D13 = '    ("D-13", lambda x: any(not lk.available for _, lk in x.c.lookups)),\n'
D14 = '    ("D-14", lambda x: x.L_is("matched", VF)),\n'
D17 = '    ("D-17", lambda x: True),\n'

MUTANTS: dict[str, list[tuple[str, str, str]]] = {
    "M01 D-14 before identity conflict": [(DT1, D14, ""), (DT1, D6, D14 + D6)],
    "M02 D-13 after positive": [(DT1, D13, ""), (DT1, D14, D14 + D13)],
    "M03 remove D-6": [(DT1, D6, "")],
    "M04 remove D-17": [(DT1, D17, "")],
    "M05 notice becomes positive": [
        (DT1, '"NOTICE_CITED", {"CITED_IDENTIFIER_IS_NOTICE"}', '"RETRACTED_WORK_CITED", set()')
    ],
    "M06 no-record becomes retracted": [
        (DT1, '"NOT_FOUND_IN_CHECKED_SOURCES", {"NOT_FOUND_IN_CHECKED_SOURCES"}', '"RETRACTED_WORK_CITED", set()')
    ],
    "M07 unavailable becomes no-record": [
        (
            DET,
            'state=str(res.get("lookup_state")),',
            'state=str(res.get("lookup_state")).replace("unavailable", "no_record"),',
        )
    ],
    "M08 ignore taint": [(DT1, '("D-8", lambda x: bool(x.c.taint)),', '("D-8", lambda x: False),')],
    "M09 ignore bridge-only": [
        (DT1, 'and (bool(lk.collision) or "BRIDGE_ONLY_SUPPORT" in lk.basis_reasons)', "and bool(lk.collision)")
    ],
    "M10 allow an ambiguous DOI-only query": [(DT1, 'out.append("DOI_QUERY_AMBIGUOUS")', "pass")],
    "M11 ignore the kappa/Q2 disagreement": [
        (DT1, 'out.append("PAIR_WITNESS_STATE")', "pass"),
        (DT1, 'out.append("PAIR_STATE_DISAGREES")', "pass"),
        (DT1, 'out.append("KAPPA_Q2_DISAGREE")  # MM proposition P2', "pass"),
    ],
    "M12 NEEDS_RESOLUTION becomes normal completion": [
        (
            WF,
            'CONFLICT = {"IDENTITY_CONFLICT": "identity_conflict", "CONTRADICTION_IN_SOURCES": "source_conflict"}',
            "CONFLICT: dict[str, str] = {}",
        )
    ],
    "M13 collapse the two B-8 candidate evidence items": [
        (DET, 'pointer = self.occurrence[key_ev[0]][0] if key_ev else unit["pointer"]', 'pointer = unit["pointer"]')
    ],
}
SUITES = (
    "tests/stage04/test_step9_detector.py",
    "tests/stage04/test_step9_b8.py",
    "tests/stage04/test_step9_real.py",
)


def mutate(src: Path, changes: list[tuple[str, str, str]]) -> None:
    for rel, old, new in changes:
        path = src / rel
        text = path.read_text(encoding="utf-8")
        if text.count(old) != 1:
            raise SystemExit(f"stale mutant: {old!r} occurs {text.count(old)} times in {rel}")
        path.write_text(text.replace(old, new), encoding="utf-8")


def run(cmd: list[str], src: Path) -> tuple[int, str]:
    env = {**os.environ, "PYTHONPATH": str(src)}
    p = subprocess.run(cmd, cwd=REPO, env=env, capture_output=True, text=True, timeout=3600, check=False)  # noqa: S603
    return p.returncode, (p.stdout + p.stderr)[-4000:]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--differential", action="store_true")
    ap.add_argument("--only", default=None, help="run the mutants whose name starts with this")
    args = ap.parse_args()
    results = {}
    for name, changes in MUTANTS.items():
        if args.only and not name.startswith(args.only):
            continue
        t0 = time.perf_counter()
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "src"
            shutil.copytree(REPO / "src", src, ignore=shutil.ignore_patterns("__pycache__"))
            mutate(src, changes)
            probe, _ = run(
                [
                    sys.executable,
                    "-c",
                    f"import citerift, sys; sys.exit(0 if citerift.__file__.startswith({str(src)!r}) else 1)",
                ],
                src,
            )
            if probe != 0:
                raise SystemExit("the mutated copy is not the module under test")
            row: dict[str, object] = {}
            failed = []
            for suite in SUITES:
                code, out = run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", suite], src)
                row[suite] = {"exit": code, "tail": out.strip().splitlines()[-1] if out.strip() else ""}
                if code != 0:
                    failed.append(suite)
            if args.differential:
                code, out = run(
                    [
                        sys.executable,
                        str(Path(__file__).parent / "differential.py"),
                        "--out",
                        str(Path(d) / "diff.json"),
                    ],
                    src,
                )
                diff = json.loads((Path(d) / "diff.json").read_text()) if (Path(d) / "diff.json").exists() else None
                row["differential"] = {"exit": code, "cases": diff["cases_compared"] if diff else out[-300:]}
                if code != 0:
                    failed.append("differential")
        row["caught_by"] = failed
        row["caught"] = bool(failed)
        row["seconds"] = round(time.perf_counter() - t0, 1)
        results[name] = row
        print(name, "CAUGHT" if failed else "SURVIVED", failed, flush=True)
    summary = {"mutants": len(results), "caught": sum(1 for r in results.values() if r["caught"]), "results": results}
    if not args.only:
        (Path(__file__).parent / "mutants.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(summary["caught"], "of", summary["mutants"], "caught")
    return 0 if summary["caught"] == summary["mutants"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
