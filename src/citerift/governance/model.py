"""Stage lifecycle model: states, actors and the explicit transition table.

The table is the single definition of which edges exist and who may take them.
Whether a permitted edge is actually allowed in a given repository state is
decided by the orchestrator, which applies the edge to a copy of the registry
and runs the full consistency check on the result.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Status(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    AUTHORIZED = "AUTHORIZED"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    IMPLEMENTED_NOT_VERIFIED = "IMPLEMENTED_NOT_VERIFIED"
    VERIFIED_AWAITING_OWNER_ACCEPTANCE = "VERIFIED_AWAITING_OWNER_ACCEPTANCE"
    ACCEPTED_CLOSED = "ACCEPTED_CLOSED"


class Actor(StrEnum):
    OWNER = "owner"
    ENGINEERING_AGENT = "engineering-agent"
    EXTERNAL_AGENT = "external-agent"


S = Status

# Stages in these states hold the single "active" engineering slot.
ACTIVE: frozenset[Status] = frozenset({S.AUTHORIZED, S.IN_PROGRESS, S.BLOCKED, S.IMPLEMENTED_NOT_VERIFIED})

# States that require each record to be present on the stage.
NEEDS_AUTHORIZATION: frozenset[Status] = frozenset(set(S) - {S.NOT_STARTED})
NEEDS_IMPLEMENTATION: frozenset[Status] = frozenset(
    {S.IMPLEMENTED_NOT_VERIFIED, S.VERIFIED_AWAITING_OWNER_ACCEPTANCE, S.ACCEPTED_CLOSED}
)
NEEDS_VERIFICATION: frozenset[Status] = frozenset({S.VERIFIED_AWAITING_OWNER_ACCEPTANCE, S.ACCEPTED_CLOSED})


@dataclass(frozen=True)
class Edge:
    source: Status
    target: Status
    owner_only: bool
    meaning: str


EDGES: tuple[Edge, ...] = (
    Edge(S.NOT_STARTED, S.AUTHORIZED, True, "owner authorizes the stage"),
    Edge(S.AUTHORIZED, S.NOT_STARTED, True, "owner withdraws the authorization"),
    Edge(S.AUTHORIZED, S.IN_PROGRESS, False, "work starts"),
    Edge(S.IN_PROGRESS, S.BLOCKED, False, "an open blocker stops work"),
    Edge(S.BLOCKED, S.IN_PROGRESS, False, "all blockers resolved"),
    Edge(S.IN_PROGRESS, S.IMPLEMENTED_NOT_VERIFIED, False, "implementation revision recorded"),
    Edge(S.IMPLEMENTED_NOT_VERIFIED, S.IN_PROGRESS, False, "rework before verification"),
    Edge(
        S.IMPLEMENTED_NOT_VERIFIED,
        S.VERIFIED_AWAITING_OWNER_ACCEPTANCE,
        False,
        "technical verification evidence recorded",
    ),
    Edge(
        S.VERIFIED_AWAITING_OWNER_ACCEPTANCE,
        S.IN_PROGRESS,
        False,
        "defect found or owner requests changes",
    ),
    Edge(
        S.VERIFIED_AWAITING_OWNER_ACCEPTANCE,
        S.ACCEPTED_CLOSED,
        True,
        "owner accepts the verified handoff",
    ),
    Edge(
        S.ACCEPTED_CLOSED,
        S.IN_PROGRESS,
        True,
        "owner reopens an accepted stage for an evidence-supported correction",
    ),
)

EDGE_MAP: dict[tuple[Status, Status], Edge] = {(e.source, e.target): e for e in EDGES}


def find_edge(source: Status, target: Status) -> Edge | None:
    return EDGE_MAP.get((source, target))
