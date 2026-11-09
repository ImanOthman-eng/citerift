"""Stage 03 acquisition simulation (SIMULATION_REPORT.md, 2026-11-02 addendum): the resumable campaign capture driver
(docs/verification/stage-03/evaluation/scripts/campaign_capture.py) under scripted outcomes, kills and restarts.

Each sequence draws a plan of 1-8 articles and a scripted stand-in for the capture CLI. Every run of the stand-in
answers complete, deferred (short or long wait, or by the network gate with no request), render-deferred, a
retryable failure, a 429 with an unreadable Retry-After, or a final failure, and some runs are killed mid-run (the
stand-in raises after creating the bundle directory, as a SIGKILL would leave it, or after publishing a complete
bundle). After a kill, the journal's last line is sometimes torn (a partial ``end`` line). The driver is restarted
after every kill and after every exit 4 (deferral pending), with the clock moved to a random later time, until it
exits 0, 2 or 5. No request is made. Checked invariants:

  C1  a bundle path is never reused;
  C2  no run of a deferred article starts before that article's not_before;
  C3  an article with a complete run is never run again;
  C4  at most MAX_RUNS runs per article, and every sequence ends (bounded restarts);
  C5  no run starts unless the recorded HTTP attempts and accepted bytes, with an interrupted run at its worst
      case, leave room for one more worst-case run within the ceilings;
  C6  after the final restart, every run in the journal is in the state, and the state has no other run;
  C7  a second driver started while one holds the lock makes no run;
  C8  a torn final journal line never stops a restart, and its bytes are kept in a side file;
  C9  no run starts at or after the acquisition time limit;
  C10 a run stopped by an unreadable Retry-After is the article's last run.

Usage: python simulations/stage03/campaign_driver_sim.py [N_SEQUENCES] [SEED]  (prints a JSON summary)
"""

from __future__ import annotations

import fcntl
import json
import os
import random
import sys
import tempfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "docs/verification/stage-03/evaluation/scripts"))
import campaign_capture as cc  # noqa: E402

T0 = 1_793_600_000.0


class Killed(Exception):
    pass


def stamp(t: float) -> str:
    return datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")  # as fetch.utc_text


class World:
    def __init__(self, rng: random.Random, attempts_per_run: int) -> None:
        self.rng = rng
        self.t = T0
        self.runs: list[tuple[str, float]] = []  # (bundle path, start time)
        self.not_before: dict[str, float] = {}  # article -> latest server not_before
        self.complete: set[str] = set()
        self.failures: list[str] = []
        self.attempts_per_run = attempts_per_run
        self.ra_problem: set[str] = set()

    def clock(self) -> float:
        return self.t

    def sleep(self, s: float) -> None:
        self.t += max(0.0, s)

    def cli(self, argv: list[str]) -> tuple[int, str, str]:
        out = Path(argv[argv.index("--out") + 1])
        art = f"{argv[3]}-{argv[5]}"
        if out.exists():
            self.failures.append(f"C1 reused {out.name}")
        if self.t < self.not_before.get(art, 0.0):
            self.failures.append(f"C2 {art} at {self.t} before {self.not_before[art]}")
        if art in self.complete:
            self.failures.append(f"C3 {art} run again")
        if art in self.ra_problem:
            self.failures.append(f"C10 {art} run again after an unreadable Retry-After")
        if self.t >= cc.ACQUISITION_END:
            self.failures.append(f"C9 {art} run at {self.t}")
        self.runs.append((str(out), self.t))
        out.mkdir(parents=True, exist_ok=True)
        self.t += self.rng.uniform(1, 60)
        roll = self.rng.random()
        attempts = [{"code": None, "body_bytes": self.rng.randint(10_000, 3_000_000)}] * self.rng.randint(
            1, self.attempts_per_run
        )
        cap: dict[str, Any] = {"attempts": attempts, "issues": [], "not_before": None, "render": {}}
        if roll < 0.06:
            raise Killed
        if roll < 0.12:  # killed after the CLI published a complete bundle
            (out / "capture.json").write_text(json.dumps({**cap, "status": "complete"}), encoding="utf-8")
            self.complete.add(art)
            raise Killed
        if roll < 0.45:
            status = "complete"
            self.complete.add(art)
        elif roll < 0.65:
            status = "deferred"
            nb = self.t + self.rng.choice([30, 300, 900, 4000])
            cap["not_before"] = stamp(nb)
            self.not_before[art] = nb
        elif roll < 0.75:
            status = "partial"
            nb = self.t + self.rng.choice([20, 2000])
            cap["render"] = {"code": "DEFERRED_RETRY_AFTER", "not_before": stamp(nb)}
            self.not_before[art] = nb
        elif roll < 0.8:
            status = "failed"
            cap["issues"] = [{"code": "ATTEMPTS_EXHAUSTED", "severity": "error"}]
        elif roll < 0.85:  # deferred by the network gate: no request was made
            status = "deferred"
            nb = self.t + self.rng.choice([30, 4000])
            cap["attempts"] = []
            cap["not_before"] = stamp(nb)
            self.not_before[art] = nb
        elif roll < 0.9:
            status = "failed"
            cap["attempts"] = [{"code": "HTTP_RATE_LIMITED", "retry_after_problem": "RETRY_AFTER_UNREADABLE"}]
            cap["issues"] = [{"code": "HTTP_RATE_LIMITED", "severity": "error"}]
            self.ra_problem.add(art)
        else:
            status = "failed"
            cap["issues"] = [{"code": "PAGE_NOT_FOUND", "severity": "error"}]
        return 0, json.dumps({"status": status, "bundle": str(out), "capture": cap}), ""


def check_ceilings(out: Path, failures: list[str]) -> None:
    """C5: replay the journal; before every start, the usage so far plus one worst-case run fits the ceilings."""
    entries = cc._journal(out)
    for i, e in enumerate(entries):
        if e.get("event") != "start":
            continue
        a, b = cc.used(entries[:i])
        if a + cc.RUN_WORST_ATTEMPTS > cc.MAX_HTTP_ATTEMPTS or b + cc.RUN_WORST_BYTES > cc.MAX_ACCEPTED_BYTES:
            failures.append(f"C5 run started at {a} attempts / {b} bytes")


def sequence(rng: random.Random, tmp: Path) -> tuple[list[str], Counter[str]]:
    n = rng.randint(1, 8)
    arts = [{"split": "holdout", "wiki": rng.choice(["ar", "en"]), "page_id": 1000 + i} for i in range(n)]
    plan = tmp / "plan.json"
    plan.write_text(json.dumps({"campaign": "sim", "articles": arts}), encoding="utf-8")
    out = tmp / "out"
    world = World(rng, attempts_per_run=rng.choice([6, 6, 6, 200]))
    outcomes: Counter[str] = Counter()
    for _restart in range(200):
        try:
            code = cc.run(plan, out, world.cli, world.clock, world.sleep)
        except Killed:
            outcomes["killed"] += 1
            world.t += rng.uniform(0, 600)
            if rng.random() < 0.5:  # the kill tore the end line being written
                with (out / "captures.jsonl").open("a", encoding="utf-8") as fh:
                    fh.write('{"event": "end", "key": "holdout/' + "x" * rng.randint(0, 40))
                outcomes["torn"] += 1
            continue
        except Exception as exc:  # any other exception is a failed restart
            world.failures.append(f"C8 restart raised {type(exc).__name__}: {exc}")
            break
        outcomes[f"exit_{code}"] += 1
        if code == 4:
            world.t += rng.uniform(60, 5000)
            continue
        break
    else:
        world.failures.append("C4 did not end within 200 restarts")
    torn_kept = sum(len(p.read_bytes()) > 0 for p in out.glob("captures.jsonl.torn-at-*"))
    if outcomes["torn"] and not torn_kept:
        world.failures.append("C8 a torn line was not kept")
    if not (out / "capture_states.json").exists():
        return world.failures, outcomes
    states = json.loads((out / "capture_states.json").read_text(encoding="utf-8"))["articles"]
    for key, rec in states.items():
        if len(rec["runs"]) > cc.MAX_RUNS:
            world.failures.append(f"C4 {key} has {len(rec['runs'])} runs")
    starts = {(e["key"], e["run"]) for e in cc._journal(out) if e.get("event") == "start"}
    recorded = {(k, r["run"]) for k, rec in states.items() for r in rec["runs"]}
    if starts != recorded:
        world.failures.append(f"C6 journal {sorted(starts - recorded)} state {sorted(recorded - starts)}")
    check_ceilings(out, world.failures)
    # C7: a second driver while the lock is held
    fd = os.open(out / "driver.lock", os.O_RDWR)
    fcntl.flock(fd, fcntl.LOCK_EX)
    try:
        before = len(world.runs)
        if cc.run(plan, out, world.cli, world.clock, world.sleep) != 3 or len(world.runs) != before:
            world.failures.append("C7 a second driver ran")
    finally:
        os.close(fd)
    for rec in states.values():
        outcomes[f"final_{(rec['final'] or {}).get('status')}"] += 1
    return world.failures, outcomes


def main() -> int:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 20261102
    rng = random.Random(seed)
    failures: list[str] = []
    outcomes: Counter[str] = Counter()
    devnull = open(os.devnull, "w")  # noqa: SIM115 - the driver's progress lines are not part of the summary
    old, sys.stderr = sys.stderr, devnull
    try:
        for i in range(n):
            with tempfile.TemporaryDirectory() as d:
                f, o = sequence(rng, Path(d))
                failures += [f"seq {i}: {x}" for x in f]
                outcomes += o
    finally:
        sys.stderr = old
        devnull.close()
    print(
        json.dumps(
            {
                "sequences": n,
                "seed": seed,
                "failure_count": len(failures),
                "failures": failures[:20],
                "outcomes": dict(sorted(outcomes.items())),
            },
            indent=1,
        )
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
