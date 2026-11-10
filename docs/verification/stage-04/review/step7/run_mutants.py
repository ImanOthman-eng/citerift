"""Stage 04 Step 7 mutation run (owner Step 7 item 22).

Each mutant is one deliberate defect in the production controller (``src/citerift/investigation/controller.py`` or
``workflow.py``). For each, the source tree is copied to a temporary directory, the defect is applied there (the
repository is never changed), and the Step 7 controller tests run against the copy (``PYTHONPATH`` puts the copy
first). A mutant is detected when the test run fails. The unmutated copy is run first as a control and must pass.

Usage: ``uv run python docs/verification/stage-04/review/step7/run_mutants.py [--out FILE]``
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
TESTS = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "tests" / "stage04").glob("test_controller_*.py"))

W = "src/citerift/investigation/workflow.py"
CT = "src/citerift/investigation/controller.py"

# id -> (owner item 22 wording, [(file, old, new), ...]); every ``old`` must occur exactly once.
MUTANTS: dict[str, tuple[str, list[tuple[str, str, str]]]] = {
    "MS-1": (
        "restart a succeeded step (the guard permits it)",
        [(W, '    raise _refuse("TR-2", f"{step} is {sv.state}", seq)', '    return "T-RESTART"')],
    ),
    "MS-2": (
        "reset the retry count (only the last attempt counts)",
        [
            (
                W,
                'phi = sum(1 for a in history if a.end_kind == "step_interrupted"',
                'phi = sum(1 for a in history[-1:] if a.end_kind == "step_interrupted"',
            )
        ],
    ),
    "MS-3": (
        "ignore not_before (schedule and guard)",
        [
            (W, "sv.not_before is not None and now < sv.not_before", "False"),
            (W, "if sv.not_before is not None and (at is None or at < sv.not_before):", "if False:"),
        ],
    ),
    "MS-4": (
        "allow step k + 1 before step k",
        [
            (
                W,
                '    earlier = [s for s in STEPS[:index] if f.step_state(s) != "succeeded"]',
                "    earlier: list[str] = []",
            )
        ],
    ),
    "MS-5": (
        "allow continuing after a terminal lifecycle",
        [
            (W, "    if lc in LIFECYCLE_TERMINAL:\n        raise _refuse(", "    if False:\n        raise _refuse("),
            (
                W,
                "    if lc in LIFECYCLE_TERMINAL:\n        return NextAction(",
                '    if lc == "COMPLETED":\n        return NextAction(',
            ),
        ],
    ),
    "MS-6": (
        "turn NEEDS_RESOLUTION into COMPLETED",
        [
            (
                W,
                "        lifecycle=f.lifecycle(),",
                '        lifecycle="COMPLETED" if f.lifecycle() == "NEEDS_RESOLUTION" else f.lifecycle(),',
            )
        ],
    ),
    "MS-7": (
        "drop the open question (not derived and not required)",
        [
            (CT, "        if cls in workflow.CONFLICT:", "        if False:"),
            (
                W,
                "        if cls in CONFLICT:\n            if len(qs) != 1",
                "        if False:\n            if len(qs) != 1",
            ),
        ],
    ),
    "MS-8": (
        "repeat a committed step (the schedule offers it again)",
        [
            (
                W,
                '        if sv.state == "succeeded":\n            continue',
                '        if sv.state == "succeeded" and step != "DETECT":\n            continue',
            )
        ],
    ),
    "MS-9": (
        "ignore a changed key (no staleness)",
        [(CT, "        if not changed_steps:\n            return None", "        if True:\n            return None")],
    ),
    "MS-10": (
        "treat an adapter exception as success",
        [
            (
                CT,
                (
                    "            self._defect(step, attempt, key, "
                    '_Defect(f"adapter raised {type(exc).__name__}: {exc}"))'
                    "\n            return"
                ),
                "            result = Succeeded()",
            )
        ],
    ),
}


def _copy() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="citerift-mutant-"))
    shutil.copytree(ROOT / "src", tmp / "src")
    os.symlink(ROOT / "schemas", tmp / "schemas")
    return tmp


def _apply(tmp: Path, edits: list[tuple[str, str, str]]) -> None:
    for rel, old, new in edits:
        path = tmp / rel
        text = path.read_text(encoding="utf-8")
        if text.count(old) != 1:
            raise SystemExit(f"mutation anchor not unique in {rel}: {old!r}")
        path.write_text(text.replace(old, new), encoding="utf-8")


def _run(tmp: Path) -> tuple[int, str, str]:
    env = dict(os.environ, PYTHONPATH=str(tmp / "src"))
    probe = subprocess.run(
        [sys.executable, "-c", "import citerift.investigation.controller as c; print(c.__file__)"],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if not probe.startswith(str(tmp)):
        raise SystemExit(f"the copy is not the code under test: {probe}")
    proc = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "pytest", *TESTS, "-x", "-q", "-p", "no:cacheprovider"],
        env=env,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    failed = re.findall(r"^(?:FAILED|ERROR) (\S+)", proc.stdout, flags=re.MULTILINE)
    summary = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else proc.stderr[-300:]
    return proc.returncode, failed[0] if failed else "", summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).with_name("mutation_results.json")))
    args = ap.parse_args()
    rows = []
    tmp = _copy()
    try:
        code, first, summary = _run(tmp)
        rows.append(
            {
                "id": "CONTROL",
                "what": "unmutated copy",
                "exit": code,
                "detected": code != 0,
                "first_failure": first,
                "summary": summary,
            }
        )
        if code != 0:
            raise SystemExit(f"control run failed: {summary}")
    finally:
        shutil.rmtree(tmp)
    for mid, (what, edits) in MUTANTS.items():
        tmp = _copy()
        try:
            _apply(tmp, edits)
            code, first, summary = _run(tmp)
        finally:
            shutil.rmtree(tmp)
        rows.append(
            {"id": mid, "what": what, "exit": code, "detected": code != 0, "first_failure": first, "summary": summary}
        )
        print(mid, "detected" if code != 0 else "SURVIVED", first, flush=True)
    result = {
        "tests": TESTS,
        "mutants": len(MUTANTS),
        "detected": sum(1 for r in rows[1:] if r["detected"]),
        "rows": rows,
    }
    Path(args.out).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("mutants", "detected")}))


if __name__ == "__main__":
    main()
