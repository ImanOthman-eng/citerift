"""Exhaustive conformance of the history replay with the abstract model (correction A-00-001).

``state_machine_model.py`` decides which transition attempts are allowed.
``Orchestrator`` replays the recorded history and reports an entry that breaks
a rule. Before the correction the replay checked edges and actors only
(independent review F-04, F-05), so a history the model forbids could pass.

This script explores every status vector the model can reach for a small
configuration, keeps one shortest history per vector, and appends every
possible next entry (any stage, any target status, owner or executor, with or
without an owner reference, with or without an open blocker, with or without a
correction amendment). For each one it compares:

- model: ``guard(...)`` allows the attempt (evidence, tests and revision are
  taken as satisfied, because the replay does not decide them; the evidence
  checks are tested separately), and
- implementation: ``Orchestrator._history_findings`` reports no error.

They must agree on every case. Unlike ``state_machine_model.py`` this file
imports the implementation; the model itself stays independent.
"""

from __future__ import annotations

import argparse
import importlib.util
import itertools
import json
import sys
from collections import deque
from pathlib import Path
from types import ModuleType
from typing import Any

from citerift.governance.orchestrator import Orchestrator

MODEL_PATH = Path(__file__).with_name("state_machine_model.py")


def load_model() -> ModuleType:
    spec = importlib.util.spec_from_file_location("citerift_sim_model_conformance", MODEL_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {MODEL_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _at(step: int) -> str:
    seconds = 10 * step
    return f"2026-01-01T{seconds // 3600:02d}:{seconds // 60 % 60:02d}:{seconds % 60:02d}Z"


def _at_before(step: int) -> str:
    seconds = 10 * step - 5
    return f"2026-01-01T{seconds // 3600:02d}:{seconds // 60 % 60:02d}:{seconds % 60:02d}Z"


Move = tuple[int, str, bool, bool, bool, bool]  # stage, target, by owner, owner_ref, blocker open, amendment


class Config:
    def __init__(self, deps: dict[int, tuple[int, ...]], engineering: frozenset[int]):
        self.deps = deps
        self.engineering = engineering
        self.ids = [f"{s:02d}" for s in deps]

    def executor(self, s: int) -> str:
        return "engineering-agent" if s in self.engineering else "external-agent"

    def registry(self, moves: list[Move], statuses: tuple[str, ...]) -> dict[str, Any]:
        stages = [
            {
                "id": self.ids[s],
                "executor": self.executor(s),
                "depends_on": [self.ids[d] for d in self.deps[s]],
                "status": statuses[s],
                "blockers": [],
                "amendments": [],
            }
            for s in self.deps
        ]
        history = []
        for index, (s, target, by_owner, with_ref, blocker_open, with_amendment) in enumerate(moves, start=1):
            stage = stages[s]
            source = history_status(history, self.ids[s])
            at = _at(index)
            open_blockers = [b for b in stage["blockers"] if b["resolved_at"] is None]
            if blocker_open and not open_blockers:
                stage["blockers"].append(
                    {
                        "id": f"B-{self.ids[s]}-{len(stage['blockers']) + 1:03d}",
                        "description": "conformance",
                        "opened_at": _at_before(index),
                        "resolved_at": None,
                        "resolution": None,
                    }
                )
            if not blocker_open:
                for b in open_blockers:
                    b["resolved_at"], b["resolution"] = at, "resolved"
            entry: dict[str, Any] = {
                "seq": index,
                "at": at,
                "stage": self.ids[s],
                "from": source,
                "to": target,
                "actor": "owner" if by_owner else self.executor(s),
                "recorded_by": "engineering-agent",
                "reason": "conformance",
                "owner_ref": f"cmsg_CONFORMANCE{index:05d}" if with_ref else None,
            }
            if with_amendment:
                aid = f"A-{self.ids[s]}-{len(stage['amendments']) + 1:03d}"
                stage["amendments"].append(
                    {"id": aid, "kind": "correction", "recorded_at": _at_before(index), "test_report": None}
                )
                entry["amendment"] = aid
            history.append(entry)
        return {"policy": {"single_active_engineering_stage": True}, "stages": stages, "history": history}


def history_status(history: list[dict[str, Any]], sid: str) -> str:
    last = [h for h in history if h["stage"] == sid]
    return last[-1]["to"] if last else "NOT_STARTED"


def implementation_allows(orc_root: Path, config: Config, moves: list[Move], statuses: tuple[str, ...]) -> bool:
    orc = Orchestrator(orc_root, config.registry(moves, statuses))
    return not [f for f in orc._history_findings() if f.severity == "error"]


def explore(model: ModuleType, config: Config, root: Path) -> dict[str, Any]:
    n = len(config.deps)
    start = ("NOT_STARTED",) * n
    shortest: dict[tuple[str, ...], list[Move]] = {start: []}
    queue = deque([start])
    cases = agreements = permitted = 0
    disagreements: list[str] = []
    while queue:
        status = queue.popleft()
        path = shortest[status]
        for s, target in itertools.product(range(n), model.STATES):
            for by_owner, with_ref, blocker_open, with_amendment in itertools.product((False, True), repeat=4):
                inp = model.Inputs(
                    owner_ref=with_ref,
                    evidence_ok=True,
                    tests_ok=True,
                    blockers_open=blocker_open,
                    revision_ok=True,
                    amendment_ok=with_amendment,
                )
                actor = model.OWNER if by_owner else model.AGENT
                expected = model.guard(s, (status[s], target), actor, inp, status, config.deps, config.engineering)
                move: Move = (s, target, by_owner, with_ref, blocker_open, with_amendment)
                after = tuple(target if i == s else st for i, st in enumerate(status))
                actual = implementation_allows(root, config, [*path, move], after)
                cases += 1
                permitted += expected
                if expected == actual:
                    agreements += 1
                else:
                    disagreements.append(
                        f"{status} + stage {s} {status[s]}->{target} owner={by_owner} ref={with_ref} "
                        f"blocker={blocker_open} amendment={with_amendment}: model={expected} implementation={actual}"
                    )
                if expected and after not in shortest:
                    shortest[after] = [*path, move]
                    queue.append(after)
    return {
        "stages": n,
        "dependencies": {config.ids[k]: [config.ids[d] for d in v] for k, v in config.deps.items()},
        "engineering_stages": [config.ids[s] for s in sorted(config.engineering)],
        "reachable_status_vectors": len(shortest),
        "cases": cases,
        "model_permitted": permitted,
        "agreements": agreements,
        "disagreements": len(disagreements),
        "disagreement_examples": disagreements[:20],
        "max_history_length": max(len(p) for p in shortest.values()) + 1,
    }


CONFIGS = {
    "small": ({0: (), 1: (), 2: (0, 1)}, frozenset({0, 2})),
    "full": ({0: (), 1: (), 2: (0, 1), 3: (0, 1)}, frozenset({0, 2, 3})),
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", choices=sorted(CONFIGS), default="full")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    deps, engineering = CONFIGS[args.config]
    result = {
        "check": "citerift-history-replay-conformance/1",
        "config": args.config,
        **explore(load_model(), Config(deps, engineering), Path.cwd()),
    }
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 1 if result["disagreements"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
