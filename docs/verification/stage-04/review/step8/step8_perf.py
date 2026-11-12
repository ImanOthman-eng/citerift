"""Step 8 performance of the warm retained real-article path (owner Step 8 item 21), separate from the cap stress tests.

For each previously exposed design bundle (VS-1 MMR, VS-2 ar Obokata, VS-3 en Obokata) it creates an investigation in
a fresh Memory and runs it one controller action at a time, timing each step (adapter plus commit). The first run of
each bundle is reported as cold (imports, schema compilation, page cache); then ``RUNS`` fresh investigations of the
same bundle are timed warm and the median is reported. ``reopen`` is a read-only ``InvestigationMemory.open`` of the
finished investigation (journal fold, checkpoint and blob checks), the cost of every resume and replay. The network is
refused in this process for the whole run. DETECT is the SYNTHETIC test detector, not dt-1.

It also measures the D-042 supervisor's kill, reap and sweep on a sleeping child with two descendants (one leaves the
session with setsid), with a short bound (``KILL_BOUND_S``) instead of 240 s: the bound only decides when the kill
starts, not how long it takes.

Nothing here optimizes or measures jsonschema on its own. Writes ``step8_perf.json`` beside itself.

Run: ``uv run python docs/verification/stage-04/review/step8/step8_perf.py``
"""

from __future__ import annotations

import json
import platform
import statistics
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO / "tests" / "stage04"))

import step8_support as S8  # noqa: E402

from citerift.investigation.adapters.supervise import supervise  # noqa: E402
from citerift.investigation.controller import open_controller  # noqa: E402
from citerift.investigation.memory import InvestigationMemory  # noqa: E402

RUNS = 5
KILL_RUNS = 5
KILL_BOUND_S = 1.0
BUNDLES = {"VS-1 en MMR": S8.EN_MMR, "VS-2 ar Obokata": S8.AR_OBOKATA, "VS-3 en Obokata": S8.EN_OBOKATA}
TREE = (
    "import subprocess, sys, time\n"
    "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(3600)'])\n"
    "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(3600)'], start_new_session=True)\n"
    "time.sleep(3600)\n"
)


def one_run(tmp: Path, bundle: Path, index: Path) -> dict[str, float]:
    root = S8.memory_root(tmp)
    t0 = time.perf_counter()
    payload = S8.create(root, S8.request(bundle, index, root))
    times = {"CREATE": time.perf_counter() - t0}
    integration = S8.TEST_INTEGRATION
    mem, ctl = open_controller(
        root, payload["investigation_key"], integration.adapters(), integration.environment(payload)
    )
    with mem:
        ctl.recover()
        for _ in range(64):
            t = time.perf_counter()
            action = ctl.step()
            if action.action == "terminal":
                break
            if action.action == "start" and action.step is not None:
                times[action.step] = times.get(action.step, 0.0) + time.perf_counter() - t
        else:
            raise AssertionError("the run did not finish")
        state = ctl.view.lifecycle()
    t = time.perf_counter()
    with InvestigationMemory.open(root, payload["investigation_key"], writable=False) as ro:
        records = len(ro.view.records)
    times["reopen"] = time.perf_counter() - t
    times["total"] = sum(v for k, v in times.items() if k != "reopen")
    if state not in ("COMPLETED", "NEEDS_RESOLUTION"):
        raise AssertionError(f"unexpected lifecycle {state}")
    times["records"] = records
    return times


def ms(values: dict[str, float]) -> dict[str, float]:
    return {k: (v if k == "records" else round(v * 1000, 1)) for k, v in values.items()}


def kill_reap(tmp: Path) -> dict[str, Any]:
    rows = []
    for i in range(KILL_RUNS):
        r = supervise(
            [sys.executable, "-c", TREE],
            t_acq_s=KILL_BOUND_S,
            cwd=tmp,
            stdout=tmp / f"out{i}",
            stderr=tmp / f"err{i}",
        )
        if not r.timed_out or r.survivors or len(r.killed) != 2:
            raise AssertionError(r)
        rows.append({"elapsed_ms": r.elapsed_ms, "kill_ms": r.kill_ms, "reap_ms": r.reap_ms, "sweep_ms": r.sweep_ms})
    return {
        "bound_s": KILL_BOUND_S,
        "runs": rows,
        "max": {k: max(row[k] for row in rows) for k in ("kill_ms", "reap_ms", "sweep_ms")},
        "overrun_ms_max": max(row["elapsed_ms"] - KILL_BOUND_S * 1000 for row in rows),
    }


def main() -> int:
    out: dict[str, Any] = {
        "python": platform.python_version(),
        "machine": f"{platform.machine()}, {__import__('os').cpu_count()} CPUs",
        "runs_warm": RUNS,
        "unit": "ms",
        "detector": S8.DETECTOR_IDENTITY,
        "bundles": {},
    }
    with tempfile.TemporaryDirectory() as d, pytest.MonkeyPatch.context() as mp:
        offline = S8.NoNetwork(mp)
        tmp = Path(d)
        t = time.perf_counter()
        index = S8.build_index(tmp / "rw")
        out["subset_index_build_ms"] = round((time.perf_counter() - t) * 1000, 1)
        for name, bundle in BUNDLES.items():
            cold = one_run(tmp / f"{name}-cold", bundle, index)
            warm = [one_run(tmp / f"{name}-{i}", bundle, index) for i in range(RUNS)]
            median = {k: statistics.median(w[k] for w in warm) for k in warm[0]}
            out["bundles"][name] = {"cold": ms(cold), "warm_median": ms(median)}
            print(name, json.dumps(ms(median)))
        out["network_attempts"] = len(offline.attempts)
        out["supervisor_kill_reap"] = kill_reap(tmp)
        print("kill/reap", json.dumps(out["supervisor_kill_reap"]["max"]))
    path = Path(__file__).with_suffix(".json")
    path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if out["network_attempts"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
