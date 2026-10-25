"""Pre-implementation simulation of the CITERIFT stage-governance state machine.

This is an ABSTRACT model, written before the implementation and kept
independent of it (it imports nothing from ``citerift``). It answers one design
question: do the proposed transition rules and guards satisfy the governance
invariants, without blocking legitimate progress?

Two analyses are run:

1. Exhaustive breadth-first exploration of a reduced model (3 engineering
   stages in a dependency chain plus 1 independent external stage). The
   environment is adversarial: at every step any actor may attempt any edge on
   any stage, and every guard input (evidence complete, tests passing, owner
   statement present, blockers open) may be true or false.
2. Seeded random walks over the full approved 10-stage dependency graph.

The output is written as JSON so that SIMULATION_REPORT.md can cite the actual
numbers. The tests in ``tests/test_simulation.py`` re-run a smaller version
and the differential test compares this model with the implementation.

Limits: this checks the rule design over synthetic inputs. It says nothing
about whether real evidence files are truthful, and it cannot model an agent
that edits the registry file by hand (that is covered by consistency checks,
not by the transition guards).
"""

from __future__ import annotations

import argparse
import itertools
import json
import random
import sys
from collections import deque
from dataclasses import dataclass

NS = "NOT_STARTED"
AU = "AUTHORIZED"
IP = "IN_PROGRESS"
BL = "BLOCKED"
IM = "IMPLEMENTED_NOT_VERIFIED"
VA = "VERIFIED_AWAITING_OWNER_ACCEPTANCE"
AC = "ACCEPTED_CLOSED"
STATES = (NS, AU, IP, BL, IM, VA, AC)
ACTIVE = frozenset({AU, IP, BL, IM})

OWNER = "owner"
AGENT = "agent"
ACTORS = (OWNER, AGENT)

# (from, to) -> (actor required, guard name)
EDGES: dict[tuple[str, str], tuple[str | None, str]] = {
    (NS, AU): (OWNER, "authorize"),
    (AU, NS): (OWNER, "withdraw"),
    (AU, IP): (None, "start"),
    (IP, BL): (None, "block"),
    (BL, IP): (None, "unblock"),
    (IP, IM): (None, "implemented"),
    (IM, IP): (None, "rework"),
    (IM, VA): (None, "verify"),
    (VA, IP): (None, "rework"),
    (VA, AC): (OWNER, "accept"),
    (AC, IP): (OWNER, "reopen"),
}


@dataclass(frozen=True)
class Inputs:
    """Guard inputs chosen by the (adversarial) environment for one attempt."""

    owner_ref: bool
    evidence_ok: bool
    tests_ok: bool
    blockers_open: bool
    revision_ok: bool
    amendment_ok: bool


ALL_INPUTS = tuple(Inputs(*bits) for bits in itertools.product((False, True), repeat=6))


def guard(
    stage: int,
    edge: tuple[str, str],
    actor: str,
    inp: Inputs,
    status: tuple[str, ...],
    deps: dict[int, tuple[int, ...]],
    engineering: frozenset[int],
) -> bool:
    if edge not in EDGES:
        return False
    required_actor, name = EDGES[edge]
    if required_actor is not None and actor != required_actor:
        return False
    deps_ok = all(status[d] == AC for d in deps[stage])
    # Single-active rule (I3), applied to EVERY edge that enters the active set.
    # Iteration 1 applied it only to "authorize" and "reopen"; the exhaustive
    # search found that VERIFIED -> IN_PROGRESS ("rework") bypassed it.
    if edge[1] in ACTIVE and edge[0] not in ACTIVE and stage in engineering:
        if any(status[s] in ACTIVE for s in engineering if s != stage):
            return False
    if name == "authorize":
        return inp.owner_ref and deps_ok
    if name in ("withdraw",):
        return inp.owner_ref
    if name == "block":
        return inp.blockers_open
    if name in ("unblock", "start"):
        return not inp.blockers_open
    if name == "implemented":
        return inp.revision_ok
    if name == "rework":
        return True
    if name == "verify":
        return inp.evidence_ok and inp.tests_ok and inp.revision_ok and not inp.blockers_open and deps_ok
    if name == "accept":
        return inp.owner_ref and inp.evidence_ok and deps_ok
    if name == "reopen":
        return inp.owner_ref and inp.amendment_ok
    raise AssertionError(name)


@dataclass(frozen=True)
class Node:
    status: tuple[str, ...]
    # Ghost variables that record how each stage reached its current status.
    verified_properly: tuple[bool, ...]
    accepted_by_owner: tuple[bool, ...]


def check_invariants(
    node: Node,
    prev: Node | None,
    deps: dict[int, tuple[int, ...]],
    engineering: frozenset[int],
    changed: int | None,
) -> list[str]:
    errs: list[str] = []
    st = node.status
    for s, value in enumerate(st):
        if value == AC and not (node.verified_properly[s] and node.accepted_by_owner[s]):
            errs.append(f"I1 stage {s} accepted without proper verification and owner acceptance")
        if value == VA and not node.verified_properly[s]:
            errs.append(f"I1b stage {s} verified without evidence")
    active = [s for s in engineering if st[s] in ACTIVE]
    if len(active) > 1:
        errs.append(f"I3 more than one active engineering stage: {active}")
    if prev is not None and changed is not None:
        for s, value in enumerate(st):
            if s != changed and value != prev.status[s]:
                errs.append(f"I5 transition on stage {changed} changed stage {s}")
        if prev.status[changed] != AC and st[changed] == AC:
            if not all(st[d] == AC for d in deps[changed]):
                errs.append(f"I2 stage {changed} accepted while a dependency is not accepted")
        if prev.status[changed] == NS and st[changed] == AU:
            if not all(st[d] == AC for d in deps[changed]):
                errs.append(f"I2 stage {changed} authorized while a dependency is not accepted")
    return errs


def step(
    node: Node,
    s: int,
    to: str,
    actor: str,
    inp: Inputs,
    deps: dict[int, tuple[int, ...]],
    engineering: frozenset[int],
) -> Node | None:
    edge = (node.status[s], to)
    if not guard(s, edge, actor, inp, node.status, deps, engineering):
        return None
    status = list(node.status)
    vp = list(node.verified_properly)
    ao = list(node.accepted_by_owner)
    status[s] = to
    if to == VA:
        vp[s] = inp.evidence_ok and inp.tests_ok and inp.revision_ok
    elif to == AC:
        ao[s] = actor == OWNER and inp.owner_ref
    elif to in (IP, NS):
        vp[s] = False
        ao[s] = False
    return Node(tuple(status), tuple(vp), tuple(ao))


def _trace(parent: dict[Node, tuple[Node, str] | None], node: Node) -> list[str]:
    moves: list[str] = []
    entry = parent[node]
    while entry is not None:
        prev, move = entry
        moves.append(move)
        entry = parent[prev]
    return list(reversed(moves))


def explore(deps: dict[int, tuple[int, ...]], engineering: frozenset[int]) -> dict:
    n = len(deps)
    start = Node((NS,) * n, (False,) * n, (False,) * n)
    seen = {start}
    parent: dict[Node, tuple[Node, str] | None] = {start: None}
    queue = deque([start])
    attempts = accepted = rejected = 0
    violations: list[str] = []
    counterexample: list[str] | None = None
    while queue:
        node = queue.popleft()
        for s in range(n):
            for to in STATES:
                for actor in ACTORS:
                    for inp in ALL_INPUTS:
                        attempts += 1
                        nxt = step(node, s, to, actor, inp, deps, engineering)
                        if nxt is None:
                            rejected += 1
                            continue
                        accepted += 1
                        move = f"stage {s}: {node.status[s]} -> {to} by {actor}"
                        errs = check_invariants(nxt, node, deps, engineering, s)
                        if errs and counterexample is None:
                            counterexample = [*_trace(parent, node), move, f"VIOLATION {errs[0]}"]
                        violations.extend(errs)
                        if nxt not in seen:
                            seen.add(nxt)
                            parent[nxt] = (node, move)
                            queue.append(nxt)
    statuses = {node.status for node in seen}
    all_accepted = (AC,) * n
    reachable_per_stage = {s: sorted({st[s] for st in statuses}, key=STATES.index) for s in range(n)}
    # Owner-gated edge check: every edge into ACCEPTED_CLOSED comes only from VA.
    into_ac = sorted(f for (f, t) in EDGES if t == AC)
    return {
        "stages": n,
        "dependencies": {str(k): list(v) for k, v in deps.items()},
        "engineering_stages": sorted(engineering),
        "reachable_nodes": len(seen),
        "reachable_status_vectors": len(statuses),
        "transition_attempts": attempts,
        "attempts_permitted": accepted,
        "attempts_rejected": rejected,
        "invariant_violations": len(violations),
        "violation_examples": violations[:10],
        "shortest_counterexample": counterexample,
        "all_stages_accepted_reachable": all_accepted in statuses,
        "states_reachable_per_stage": {str(k): v for k, v in reachable_per_stage.items()},
        "edges_into_accepted_closed_from": into_ac,
    }


FULL_DEPS: dict[int, tuple[int, ...]] = {
    0: (),
    1: (),
    2: (0, 1),
    3: (0, 1),
    4: (2, 3),
    5: (4,),
    6: (5,),
    7: (6,),
    8: (7,),
    9: (8,),
}
FULL_ENGINEERING = frozenset(s for s in FULL_DEPS if s != 1)


def random_walks(walks: int, length: int, seed: int) -> dict:
    rng = random.Random(seed)
    n = len(FULL_DEPS)
    violations: list[str] = []
    permitted = rejected = 0
    max_accepted = 0
    successor_unlocked_without_owner = 0
    for _ in range(walks):
        node = Node((NS,) * n, (False,) * n, (False,) * n)
        for _ in range(length):
            s = rng.randrange(n)
            # Half the attempts follow an existing edge shape so that walks get
            # deep into the lifecycle; the other half are arbitrary targets.
            shaped = [t for (f, t) in EDGES if f == node.status[s]]
            to = rng.choice(shaped) if rng.random() < 0.5 else rng.choice(STATES)
            actor = rng.choice(ACTORS)
            inp = Inputs(
                owner_ref=rng.random() < 0.8,
                evidence_ok=rng.random() < 0.8,
                tests_ok=rng.random() < 0.8,
                blockers_open=rng.random() < 0.2,
                revision_ok=rng.random() < 0.8,
                amendment_ok=rng.random() < 0.8,
            )
            nxt = step(node, s, to, actor, inp, FULL_DEPS, FULL_ENGINEERING)
            if nxt is None:
                rejected += 1
                continue
            permitted += 1
            if to == AU and actor != OWNER:
                successor_unlocked_without_owner += 1
            violations.extend(check_invariants(nxt, node, FULL_DEPS, FULL_ENGINEERING, s))
            node = nxt
        max_accepted = max(max_accepted, sum(1 for v in node.status if v == AC))
    return {
        "walks": walks,
        "length": length,
        "seed": seed,
        "attempts": walks * length,
        "attempts_permitted": permitted,
        "attempts_rejected": rejected,
        "invariant_violations": len(violations),
        "violation_examples": violations[:10],
        "authorizations_without_owner": successor_unlocked_without_owner,
        "max_stages_accepted_in_one_walk": max_accepted,
    }


def guided_completion() -> dict:
    """Show that the rules permit legitimate completion of all ten stages."""
    n = len(FULL_DEPS)
    good = Inputs(True, True, True, False, True, True)
    node = Node((NS,) * n, (False,) * n, (False,) * n)
    order = [1, 0, 2, 3, 4, 5, 6, 7, 8, 9]
    path = [(AU, OWNER), (IP, AGENT), (IM, AGENT), (VA, AGENT), (AC, OWNER)]
    steps = 0
    for s in order:
        for to, actor in path:
            nxt = step(node, s, to, actor, good, FULL_DEPS, FULL_ENGINEERING)
            if nxt is None:
                return {"completed": False, "failed_at": {"stage": s, "to": to}, "steps": steps}
            node = nxt
            steps += 1
    return {"completed": all(v == AC for v in node.status), "steps": steps}


def run(walks: int, length: int, seed: int) -> dict:
    reduced_deps = {0: (), 1: (0,), 2: (1,), 3: ()}
    reduced_eng = frozenset({0, 1, 2})
    return {
        "model": "citerift-stage-governance-abstract/1",
        "exhaustive_reduced_model": explore(reduced_deps, reduced_eng),
        "random_walks_full_model": random_walks(walks, length, seed),
        "guided_full_completion": guided_completion(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--walks", type=int, default=20000)
    parser.add_argument("--length", type=int, default=200)
    parser.add_argument("--seed", type=int, default=20261025)
    parser.add_argument("--output", help="write JSON results to this path")
    args = parser.parse_args(argv)
    result = run(args.walks, args.length, args.seed)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text)
    sys.stdout.write(text)
    failed = (
        result["exhaustive_reduced_model"]["invariant_violations"]
        or result["random_walks_full_model"]["invariant_violations"]
        or not result["exhaustive_reduced_model"]["all_stages_accepted_reachable"]
        or not result["guided_full_completion"]["completed"]
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
