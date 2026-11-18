"""The frozen engine's decision table dt-1, for comparisons in the corrective cycle (owner decision D-071).

Loaded from the git object store by its blob id (the file ``src/citerift/investigation/dt1.py`` of the frozen commit
``b5bf8ed``), never from the working tree, and checked against that id before it is executed (reviewer findings E-04,
E-10). ``to_frozen`` converts a dt-2 candidate view into the dt-1 view the frozen table reads (the dt-2 fields, event
flags, notice identifiers and ``notice_hits``, do not exist in dt-1 and are dropped).
"""

from __future__ import annotations

import hashlib
import sqlite3
import subprocess
import sys
import types
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[4]
FROZEN_COMMIT = "b5bf8edfcb6f7c747a9c751bd1d402858eecbcf0"
FROZEN_BLOB = "27409702a03f04d49f5dd984b0fc6a8c6719c554"  # git rev-parse b5bf8ed:src/citerift/investigation/dt1.py


def load() -> types.ModuleType:
    name = "dt1_frozen_b5bf8ed"
    if name in sys.modules:
        return sys.modules[name]
    tree_blob = subprocess.run(  # noqa: S603 - fixed argv
        ["git", "-C", str(REPO), "rev-parse", f"{FROZEN_COMMIT}:src/citerift/investigation/dt1.py"],  # noqa: S607
        capture_output=True, text=True, check=True,
    ).stdout.strip()  # fmt: skip
    if tree_blob != FROZEN_BLOB:
        raise SystemExit(f"the frozen commit names blob {tree_blob}, not {FROZEN_BLOB}")
    data = subprocess.run(  # noqa: S603 - fixed argv
        ["git", "-C", str(REPO), "cat-file", "blob", FROZEN_BLOB],  # noqa: S607
        capture_output=True, check=True,
    ).stdout  # fmt: skip
    got = hashlib.sha1(f"blob {len(data)}\0".encode() + data, usedforsecurity=False).hexdigest()
    if got != FROZEN_BLOB:
        raise SystemExit(f"the frozen dt-1 bytes hash to {got}, not {FROZEN_BLOB}")
    mod = types.ModuleType(name)
    sys.modules[name] = mod  # dataclasses resolve annotations through sys.modules
    exec(compile(data.decode("utf-8"), f"{name}.py", "exec"), mod.__dict__)  # noqa: S102 - pinned repository blob
    if mod.TABLE_VERSION != "dt-1":
        raise SystemExit("the frozen table is not dt-1")
    return mod


def to_frozen(c: Any) -> Any:
    """A dt-2 ``Candidate`` as the frozen dt-1 ``Candidate``."""
    F = load()

    def lk(x: Any) -> Any:
        events = tuple(
            F.Event(e.position, e.event_id, e.event_type, e.matched_by, e.linked_via, e.original_doi, e.original_pmid)
            for e in x.events
        )
        return F.Lookup(
            x.state, x.projection, x.status, x.value, x.basis_reasons, x.conflict_groups, x.collision, x.budget_refused,
            events,
        )  # fmt: skip

    return F.Candidate(
        c.eligibility, c.eligibility_reason, c.shape, c.doi, c.pmid, c.taint, c.multi,
        tuple((r, lk(x)) for r, x in c.lookups),
    )  # fmt: skip


def provenance(index_path: Path) -> dict[str, Any]:
    """What a census output records about its inputs (reviewer finding D-02): the index identity from its stored
    metadata, the two tables compared, the engine version and the code commit."""
    from citerift.investigation import __version__, dt1  # noqa: PLC0415 - only when provenance is asked for

    con = sqlite3.connect(f"file:{index_path}?mode=ro", uri=True)
    meta = dict(con.execute("SELECT key, value FROM meta").fetchall())
    con.close()
    head = subprocess.run(  # noqa: S603 - fixed argv
        ["git", "-C", str(REPO), "rev-parse", "HEAD"],  # noqa: S607
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    dirty = subprocess.run(  # noqa: S603 - fixed argv
        ["git", "-C", str(REPO), "status", "--porcelain", "--", "src", "schemas"],  # noqa: S607
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    return {
        "index": {k: meta.get(k) for k in ("snapshot_id", "artifact_digest", "semantic_digest", "source_sha256")},
        "tables": {
            "frozen": {"table_version": "dt-1", "commit": FROZEN_COMMIT, "blob": FROZEN_BLOB},
            "current": {"table_version": dt1.TABLE_VERSION, "engine_version": __version__},
        },
        "code_commit": head,
        "engine_sources_uncommitted": bool(dirty),
    }


def decide(c: Any) -> Any:
    """The frozen dt-1 decision of a dt-2 candidate view."""
    return load().decide(to_frozen(c))
