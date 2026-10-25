"""Simulation evidence: the abstract model, its regression, and a differential test against the implementation."""

from __future__ import annotations

import importlib.util
import random
import sys
from pathlib import Path
from types import ModuleType

import pytest
from sandbox_repo import OWNER_REF, Sandbox

from citerift.governance.model import EDGES, Actor, Status

pytestmark = [pytest.mark.simulation]

MODEL_PATH = Path(__file__).resolve().parents[2] / "simulations" / "stage00" / "state_machine_model.py"


def load_model() -> ModuleType:
    spec = importlib.util.spec_from_file_location("citerift_sim_model", MODEL_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def model() -> ModuleType:
    return load_model()


def test_model_edge_table_matches_implementation(model: ModuleType) -> None:
    impl = {(e.source.value, e.target.value): e.owner_only for e in EDGES}
    abstract = {edge: actor == model.OWNER for edge, (actor, _) in model.EDGES.items()}
    assert impl == abstract
    assert set(model.STATES) == {s.value for s in Status}


def test_exhaustive_reduced_model_has_no_violations(model: ModuleType) -> None:
    result = model.explore({0: (), 1: (0,), 2: (1,), 3: ()}, frozenset({0, 1, 2}))
    assert result["invariant_violations"] == 0
    assert result["all_stages_accepted_reachable"] is True
    assert result["reachable_nodes"] > 100
    assert result["edges_into_accepted_closed_from"] == ["VERIFIED_AWAITING_OWNER_ACCEPTANCE"]


def test_guided_completion_of_all_ten_stages(model: ModuleType) -> None:
    assert model.guided_completion() == {"completed": True, "steps": 50}


@pytest.mark.regression
def test_iteration_1_defect_is_detected_by_the_search(model: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """Re-introduce the iteration-1 guard (VERIFIED -> IN_PROGRESS skips the single-active check).

    The exhaustive search must find the violation.
    """
    original = model.guard

    def iteration_1_guard(stage, edge, actor, inp, status, deps, engineering):  # type: ignore[no-untyped-def]
        if edge == (model.VA, model.IP):
            return True
        return original(stage, edge, actor, inp, status, deps, engineering)

    monkeypatch.setattr(model, "guard", iteration_1_guard)
    result = model.explore({0: (), 1: (0,), 2: (1,), 3: ()}, frozenset({0, 1, 2}))
    assert result["invariant_violations"] > 0
    assert result["shortest_counterexample"][-1].startswith("VIOLATION I3")


# --------------------------------------------------------------------------
# Differential test: random attempts are decided both by the abstract model and
# by the real orchestrator on a git sandbox; every decision must agree.
# --------------------------------------------------------------------------

STAGES = ("00", "01", "02", "03")
MODEL_DEPS = {0: (), 1: (), 2: (0, 1), 3: (0, 1)}
MODEL_ENGINEERING = frozenset({0, 2, 3})


def _attempt(
    sandbox: Sandbox, model: ModuleType, index: int, target: Status, actor_is_owner: bool
) -> tuple[bool, bool]:
    sid = STAGES[index]
    orc = sandbox.orc()
    status = tuple(orc.stage(s)["status"] for s in STAGES)
    executor = orc.stage(sid)["executor"]
    actor = Actor.OWNER if actor_is_owner else Actor(executor)
    good = model.Inputs(
        owner_ref=actor_is_owner,
        evidence_ok=True,
        tests_ok=True,
        blockers_open=False,
        revision_ok=True,
        amendment_ok=True,
    )
    expected = model.guard(
        index,
        (status[index], target.value),
        model.OWNER if actor_is_owner else model.AGENT,
        good,
        status,
        MODEL_DEPS,
        MODEL_ENGINEERING,
    )
    # Each owner decision cites its own statement (an acceptance may not reuse an earlier one).
    owner_ref = f"cmsg_TESTDIFFREF{len(orc.registry['history']):05d}"
    kwargs: dict[str, object] = {"actor": actor, "owner_ref": owner_ref if actor_is_owner else None}
    current = Status(status[index])
    if target == Status.IMPLEMENTED_NOT_VERIFIED:
        sandbox.write(f"impl/{sid}.txt", f"step {sandbox.clock}\n")
        kwargs["revision"] = sandbox.commit(f"implementation step for {sid}")
    if target == Status.VERIFIED_AWAITING_OWNER_ACCEPTANCE and current == Status.IMPLEMENTED_NOT_VERIFIED:
        rev = orc.stage(sid)["implementation"]["revision"]
        sandbox.write_evidence(sid, rev)
        kwargs["gates"] = sandbox.gates(sid)
        kwargs["ci"] = sandbox.ci(rev) if executor == "engineering-agent" else None
    if current == Status.ACCEPTED_CLOSED and target == Status.IN_PROGRESS and actor_is_owner:
        kwargs["amendment"] = orc.add_amendment(
            sid,
            kind="correction",
            reason="differential test correction",
            evidence_refs=["RISKS.md"],
            owner_ref=OWNER_REF,
            at=sandbox.tick(),
        )
    result = sandbox.go(sid, target, **kwargs)  # type: ignore[arg-type]
    return expected, result.allowed


@pytest.mark.parametrize("seed", [7, 20261025])
def test_differential_model_vs_implementation(model: ModuleType, tmp_path: Path, seed: int) -> None:
    sandbox = Sandbox(tmp_path / "repo")
    rng = random.Random(seed)
    edges_by_source: dict[str, list[str]] = {}
    for source, target in model.EDGES:
        edges_by_source.setdefault(source, []).append(target)
    agreements = permitted = 0
    disagreements: list[str] = []
    exercised: set[tuple[str, str]] = set()
    for _ in range(200):
        index = rng.randrange(len(STAGES))
        current = sandbox.orc().stage(STAGES[index])["status"]
        if rng.random() < 0.75:
            target = Status(rng.choice(edges_by_source[current]))
            owner_edge = model.EDGES[(current, target.value)][0] == model.OWNER
            owner = rng.random() < (0.85 if owner_edge else 0.3)
        else:
            target = Status(rng.choice(model.STATES))
            owner = rng.random() < 0.5
        expected, actual = _attempt(sandbox, model, index, target, owner)
        if expected == actual:
            agreements += 1
        else:
            disagreements.append(
                f"stage {STAGES[index]} {current}->{target} owner={owner}: model={expected} impl={actual}"
            )
        permitted += actual
        if actual:
            exercised.add((current, target.value))
    assert disagreements == []
    assert permitted >= 40, "the walk must exercise a meaningful number of permitted transitions"
    assert len(exercised) >= 8, f"only {len(exercised)} distinct edges were exercised"


def test_differential_fixed_case_reopen_foundation_after_dependent_accepted(model: ModuleType, tmp_path: Path) -> None:
    """Independent review F-11: the model allowed this reopening and the implementation refused it."""
    sandbox = Sandbox(tmp_path / "repo")
    reg = sandbox.registry()
    reg["stages"][2]["owned_paths"] = ["impl/02.txt"]
    sandbox.save_registry(reg)
    sandbox.commit("define stage 02 paths")
    for sid in ("00", "01", "02"):
        sandbox.drive_to_accepted(sid)
    status = tuple(sandbox.orc().stage(s)["status"] for s in STAGES)
    good = model.Inputs(True, True, True, False, True, True)
    expected = model.guard(0, (model.AC, model.IP), model.OWNER, good, status, MODEL_DEPS, MODEL_ENGINEERING)
    aid = sandbox.orc().add_amendment(
        "00",
        kind="correction",
        reason="differential fixed case for F-11",
        evidence_refs=["RISKS.md"],
        owner_ref="cmsg_TESTREOPENREF01",
        at=sandbox.tick(),
    )
    result = sandbox.go("00", Status.IN_PROGRESS, actor=Actor.OWNER, amendment=aid, owner_ref="cmsg_TESTREOPENREF01")
    assert expected is True
    assert result.allowed is expected, [str(f) for f in result.findings]


def test_history_replay_conforms_to_the_model_exhaustively() -> None:
    """Every reachable status vector of a 3-stage configuration, every possible next history entry."""
    spec = importlib.util.spec_from_file_location(
        "citerift_replay_conformance", MODEL_PATH.with_name("replay_conformance.py")
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    deps, engineering = module.CONFIGS["small"]
    result = module.explore(module.load_model(), module.Config(deps, engineering), Path.cwd())
    assert result["disagreements"] == 0, result["disagreement_examples"]
    assert result["cases"] == 45024 and result["reachable_status_vectors"] == 134
    assert 0 < result["model_permitted"] < result["cases"]
