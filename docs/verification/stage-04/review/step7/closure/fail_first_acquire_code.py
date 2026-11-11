"""Fail-first probe for D-049 in ACQUIRE (found while writing the closure tests): ACQUIRE has no enumerated code list
in the record schema (SPEC 9.3: "other Stage 03 codes"), so a code that is neither a Stage 03 code nor a Stage 04
ACQUIRE code was recorded as the step's terminal code instead of ADAPTER_INCONSISTENT.

Run from the repository root:

    uv run python docs/verification/stage-04/review/step7/closure/fail_first_acquire_code.py

The output before the fix is retained as ``fail_first_acquire_code.log``.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(REPO / "tests" / "stage04"))

from controller_support import Env, Plan, StepClock, create, journal, run_once  # noqa: E402

from citerift.investigation.adapters import Failed  # noqa: E402

for code in ("NOT_A_CODE_OF_ANY_STEP", "STEP_INTERRUPTED", "PAGE_MISSING"):
    clock = StepClock()
    root, key = create(Path(tempfile.mkdtemp()), clock=clock)
    st = run_once(root, key, Plan({("ACQUIRE", 1): Failed(code)}), Env(), clock)
    fails = [(r["step"], r["payload"]["code"]) for r in journal(root, key) if r["kind"] == "step_failed"]
    print(f"ACQUIRE returns Failed({code!r}): lifecycle {st.lifecycle}, recorded {fails}")
