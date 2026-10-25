"""Seeded property tests for Persistent Project Memory.

No property-testing library is used: each test draws its cases from
``random.Random(seed)`` with fixed seeds, so every run checks the same cases
and a failure names the seed and the case index needed to reproduce it.
"""

from __future__ import annotations

import copy
import json
import random
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from sandbox_repo import Sandbox, git

from citerift.governance.model import Status
from citerift.governance.orchestrator import errors

pytestmark = [pytest.mark.security, pytest.mark.regression]

SEEDS = [11, 20261025]
CASES_PER_SEED = 60

Registry = dict[str, Any]
Mutation = Callable[[random.Random, Registry, Sandbox], str]


def _owner_entries(reg: Registry) -> list[int]:
    owner_edges = {("NOT_STARTED", "AUTHORIZED"), ("VERIFIED_AWAITING_OWNER_ACCEPTANCE", "ACCEPTED_CLOSED")}
    return [i for i, h in enumerate(reg["history"]) if (h["from"], h["to"]) in owner_edges]


def _verified(reg: Registry) -> list[dict[str, Any]]:
    return [s for s in reg["stages"] if s["verification"]]


def _flip_hex(value: str, rng: random.Random) -> str:
    i = rng.randrange(len(value))
    return value[:i] + ("0" if value[i] != "0" else "1") + value[i + 1 :]


def m_history_target(rng: random.Random, reg: Registry, sb: Sandbox) -> str:
    i = rng.randrange(len(reg["history"]))
    h = reg["history"][i]
    h["to"] = rng.choice([s for s in Status if s != h["to"]]).value
    return f"history[{i}].to"


def m_history_source(rng: random.Random, reg: Registry, sb: Sandbox) -> str:
    i = rng.randrange(len(reg["history"]))
    h = reg["history"][i]
    h["from"] = rng.choice([s for s in Status if s != h["from"]]).value
    return f"history[{i}].from"


def m_owner_edge_by_agent(rng: random.Random, reg: Registry, sb: Sandbox) -> str:
    i = rng.choice(_owner_entries(reg))
    reg["history"][i]["actor"] = "engineering-agent"
    return f"history[{i}].actor"


def m_owner_ref_removed(rng: random.Random, reg: Registry, sb: Sandbox) -> str:
    i = rng.choice(_owner_entries(reg))
    reg["history"][i]["owner_ref"] = None
    return f"history[{i}].owner_ref"


def m_delete_entry(rng: random.Random, reg: Registry, sb: Sandbox) -> str:
    i = rng.randrange(len(reg["history"]))
    del reg["history"][i]
    return f"delete history[{i}]"


def m_duplicate_entry(rng: random.Random, reg: Registry, sb: Sandbox) -> str:
    i = rng.randrange(len(reg["history"]))
    copy_entry = {**reg["history"][i], "seq": len(reg["history"]) + 1, "at": reg["history"][-1]["at"]}
    reg["history"].append(copy_entry)
    return f"duplicate history[{i}]"


def m_swap_entries(rng: random.Random, reg: Registry, sb: Sandbox) -> str:
    i = rng.randrange(len(reg["history"]) - 1)
    reg["history"][i], reg["history"][i + 1] = reg["history"][i + 1], reg["history"][i]
    return f"swap history[{i}] and [{i + 1}]"


def m_future_time(rng: random.Random, reg: Registry, sb: Sandbox) -> str:
    reg["history"][-1]["at"] = "2099-01-01T00:00:00Z"
    return "history[-1].at in the future"


def m_status(rng: random.Random, reg: Registry, sb: Sandbox) -> str:
    s = rng.choice(reg["stages"])
    s["status"] = rng.choice([x for x in Status if x != s["status"]]).value
    return f"stage {s['id']} status"


def m_artifact_hash(rng: random.Random, reg: Registry, sb: Sandbox) -> str:
    s = rng.choice(_verified(reg))
    a = rng.choice(s["verification"]["artifacts"])
    a["sha256"] = _flip_hex(a["sha256"], rng)
    return f"stage {s['id']} artifact hash {a['path']}"


def m_manifest_hash(rng: random.Random, reg: Registry, sb: Sandbox) -> str:
    s = rng.choice(_verified(reg))
    e = rng.choice(s["verification"]["evidence_manifest"])
    e["sha256"] = _flip_hex(e["sha256"], rng)
    return f"stage {s['id']} manifest hash {e['path']}"


def m_definition_hash(rng: random.Random, reg: Registry, sb: Sandbox) -> str:
    s = rng.choice(_verified(reg))
    s["verification"]["definition_sha256"] = _flip_hex(s["verification"]["definition_sha256"], rng)
    return f"stage {s['id']} definition hash"


def m_drop_gate(rng: random.Random, reg: Registry, sb: Sandbox) -> str:
    s = rng.choice([s for s in _verified(reg) if s["acceptance_gates"]])
    gid = rng.choice(sorted(s["verification"]["gates"]))
    if rng.random() < 0.5:
        del s["verification"]["gates"][gid]
        return f"stage {s['id']} gate {gid} removed"
    s["verification"]["gates"][gid]["result"] = rng.choice(["fail", "not_verified"])
    return f"stage {s['id']} gate {gid} not passed"


def m_shrink_definition(rng: random.Random, reg: Registry, sb: Sandbox) -> str:
    s = rng.choice([s for s in _verified(reg) if len(s["acceptance_gates"]) > 1])
    del s["acceptance_gates"][rng.randrange(len(s["acceptance_gates"]))]
    return f"stage {s['id']} acceptance gate definition removed"


def m_policy(rng: random.Random, reg: Registry, sb: Sandbox) -> str:
    key = rng.choice(sorted(reg["policy"]))
    value = reg["policy"][key]
    if isinstance(value, bool):
        reg["policy"][key] = not value
    elif isinstance(value, list):
        reg["policy"][key] = value[:-1]
    else:
        reg["policy"][key] = value + ".x"
    return f"policy {key}"


def m_acceptance_ref(rng: random.Random, reg: Registry, sb: Sandbox) -> str:
    s = rng.choice([s for s in reg["stages"] if s["acceptance"]])
    s["acceptance"]["owner_ref"] = "cmsg_FORGEDREFERENCE01"
    return f"stage {s['id']} acceptance owner_ref"


def m_open_blocker(rng: random.Random, reg: Registry, sb: Sandbox) -> str:
    s = rng.choice(_verified(reg))
    s["blockers"].append(
        {
            "id": f"B-{s['id']}-{len(s['blockers']) + 1:03d}",
            "description": "forged",
            "opened_at": reg["history"][-1]["at"],
            "resolved_at": None,
            "resolution": None,
        }
    )
    return f"stage {s['id']} open blocker"


def m_ci_conclusion(rng: random.Random, reg: Registry, sb: Sandbox) -> str:
    s = rng.choice([s for s in _verified(reg) if s["verification"].get("ci")])
    s["verification"]["ci"]["conclusion"] = rng.choice(["failure", "cancelled", "skipped"])
    return f"stage {s['id']} CI conclusion"


def m_revision(rng: random.Random, reg: Registry, sb: Sandbox) -> str:
    s = rng.choice(_verified(reg))
    s["verification"]["revision"] = rng.choice(
        ["f" * 40, git(sb.root, "rev-list", "--max-parents=0", "HEAD")]  # missing, or the initial commit
    )
    return f"stage {s['id']} verified revision"


MUTATIONS: list[Mutation] = [
    m_history_target,
    m_history_source,
    m_owner_edge_by_agent,
    m_owner_ref_removed,
    m_delete_entry,
    m_duplicate_entry,
    m_swap_entries,
    m_future_time,
    m_status,
    m_artifact_hash,
    m_manifest_hash,
    m_definition_hash,
    m_drop_gate,
    m_shrink_definition,
    m_policy,
    m_acceptance_ref,
    m_open_blocker,
    m_ci_conclusion,
    m_revision,
]


@pytest.fixture(scope="module")
def accepted(tmp_path_factory: pytest.TempPathFactory) -> Sandbox:
    sb = Sandbox(tmp_path_factory.mktemp("properties") / "repo")
    sb.drive_to_accepted("00")
    sb.drive_to_accepted("01")
    assert sb.go("02", Status.AUTHORIZED).allowed
    sb.commit("state for property tests")
    assert not errors(sb.orc().check())
    return sb


@pytest.mark.parametrize("seed", SEEDS)
def test_every_integrity_mutation_is_detected(accepted: Sandbox, seed: int) -> None:
    """Property: any single mutation from these classes leaves at least one error."""
    rng = random.Random(seed)
    original = accepted.registry()
    missed: list[str] = []
    used: set[str] = set()
    try:
        for index in range(CASES_PER_SEED):
            reg = copy.deepcopy(original)
            mutation = MUTATIONS[index % len(MUTATIONS)] if index < len(MUTATIONS) else rng.choice(MUTATIONS)
            what = mutation(rng, reg, accepted)
            used.add(mutation.__name__)
            if reg == original:
                continue
            accepted.save_registry(reg)
            if not errors(accepted.orc().check()):
                missed.append(f"seed {seed} case {index}: {what}")
    finally:
        accepted.save_registry(original)
    assert missed == []
    assert used == {m.__name__ for m in MUTATIONS}
    assert not errors(accepted.orc().check())


def test_check_is_read_only_and_deterministic(accepted: Sandbox) -> None:
    root = accepted.root
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file() and ".git" not in p.parts}
    first = [str(f) for f in accepted.orc().check()]
    second = [str(f) for f in accepted.orc().check()]
    accepted.orc().recover()
    after = {p: p.read_bytes() for p in root.rglob("*") if p.is_file() and ".git" not in p.parts}
    assert first == second
    assert before == after


@pytest.mark.parametrize("seed", SEEDS)
def test_random_byte_damage_never_crashes(accepted: Sandbox, seed: int) -> None:
    """Property: damaging the registry bytes gives findings or a clean refusal, never an exception.

    A changed byte inside free text (a reason, a description) is not an integrity
    violation and may give no error; the property is about failing safely. The
    detected fraction is reported in the assertion message for the record.
    """
    from citerift.governance.cli import main

    rng = random.Random(seed)
    path = accepted.root / "governance/stage_registry.json"
    original = path.read_bytes()
    detected = 0
    try:
        for _ in range(25):
            data = bytearray(original)
            for _ in range(rng.randint(1, 3)):
                data[rng.randrange(len(data))] = rng.randrange(32, 127)
            path.write_bytes(bytes(data))
            code = main(["--root", str(accepted.root), "--json", "check"])
            assert code in (0, 1)
            detected += code == 1
    finally:
        path.write_bytes(original)
    assert detected > 0, f"{detected}/25 damaged registries detected"


def test_registry_round_trip_is_stable(accepted: Sandbox) -> None:
    text = (accepted.root / "governance/stage_registry.json").read_text(encoding="utf-8")
    assert json.dumps(json.loads(text), indent=2, ensure_ascii=False) + "\n" == text
    assert Path(accepted.root / "PROJECT_STATUS.md").read_text(encoding="utf-8") == accepted.orc().render_status()
