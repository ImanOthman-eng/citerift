"""Step 6: fault injection at every persistence boundary (owner Step 6 item 10; SPEC 10.2; gate 04-E).

For every named boundary in ``citerift.investigation.faults.POINTS`` and every time the synthetic workload reaches
it, a forked child runs the workload and is killed there with ``os._exit`` (at the ``during`` boundaries after
writing a prefix of the pending bytes). The parent then checks, for that one crash:

* reopen succeeds (no CORRUPT), and the stored journal is a byte-equal prefix of the uninterrupted run's journal
  (no history rewrite; a torn line is preserved in ``journal.jsonl.torn-<k>`` and removed);
* the number of committed records is exactly what the child had written when it died (no false committed success,
  no lost acknowledged record);
* every blob a record names exists and verifies; unreferenced blobs are orphans of the same content, kept;
* no temporary file survives a writable reopen;
* resuming with ``drive`` reaches the same content digest C(J), the same blob set, one succeeded attempt per step,
  and the same root, as the uninterrupted run (idempotent retry, no silent identity change).

Limitation (stated, not hidden): this is process death. The page cache survives it, so it does not show what a power
loss after ``write`` and before ``fsync`` would lose; that rests on the fsync ordering argued in the evidence.
"""

from __future__ import annotations

import json
import os
import shutil
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from memory_support import STEPS, Clock, bundle_payload, drive, memory_root

from citerift.investigation import faults
from citerift.investigation.memory import InvestigationMemory

pytestmark = pytest.mark.simulation

CRASH = 77
PARTIAL = {"blob.during_write": ("half",), "journal.during_append": ("one byte", "half", "all but the newline")}
WORKLOAD_POINTS = tuple(p for p in faults.POINTS if not p.startswith("torn."))


def _prefix(data: bytes, how: str) -> bytes:
    return {"one byte": data[:1], "half": data[: len(data) // 2], "all but the newline": data[:-1]}[how]


def _workload(root: Path) -> None:
    mem = InvestigationMemory.create(root, bundle_payload(root), clock=Clock())
    drive(mem)
    mem.close()


class Reference:
    """The uninterrupted run: its journal, blobs, content digest, and how often each boundary is reached."""

    def __init__(self, base: Path) -> None:
        # Every run uses the same memory root path, so the creation record (which names it) and the whole chain
        # are byte-comparable across runs.
        self.base = base
        root = _fresh_root(base)
        counts: Counter[str] = Counter()
        faults.install(lambda name, ctx: counts.update([name]))
        try:
            _workload(root)
        finally:
            faults.install(None)
        self.counts = counts
        mem = InvestigationMemory.open(root, bundle_payload(root)["investigation_key"], clock=Clock())
        self.key = mem.key
        self.lines = (root / self.key / "journal.jsonl").read_bytes().split(b"\n")[:-1]
        self.blobs = set(mem.blobs.names())
        self.content = mem.view.content_digest()
        self.root_id = mem.view.root_id
        mem.close()


@pytest.fixture(scope="module")
def reference(tmp_path_factory: pytest.TempPathFactory) -> Reference:
    return Reference(tmp_path_factory.mktemp("faults"))


def _crash_child(
    root: Path, point: str, occurrence: int, how: str | None, run: Callable[[Path], None]
) -> dict[str, Any]:
    """Run ``run`` in a forked child that dies at the given boundary; return what it had written at that moment."""
    report = root.parent / "report.json"
    report.unlink(missing_ok=True)
    pid = os.fork()
    if pid == 0:  # child
        code = 1
        try:
            seen: Counter[str] = Counter()

            def handler(name: str, ctx: dict[str, Any]) -> None:
                seen.update([name])
                if name == point and seen[name] == occurrence:
                    written = 0
                    if how is not None:
                        part = _prefix(ctx["data"], how)
                        os.write(ctx["fd"], part)
                        written = len(part)
                    report.write_text(json.dumps({"appends_done": seen["journal.after_write"], "partial": written}))
                    os._exit(CRASH)

            faults.install(handler)
            run(root)
            code = 0
        except BaseException:  # any failure in the child shows in its exit code
            code = 2
        finally:
            os._exit(code)
    _, status = os.waitpid(pid, 0)
    exit_code = os.waitstatus_to_exitcode(status)
    assert exit_code == CRASH, f"{point}#{occurrence}: child ended with {exit_code}, not at the boundary"
    return dict(json.loads(report.read_text()))


def _check_after_crash(ref: Reference, root: Path, point: str, occurrence: int, done: dict[str, Any]) -> dict[str, Any]:
    payload = bundle_payload(root)
    inv = root / ref.key
    existed = inv.exists()
    with InvestigationMemory.create(root, payload, clock=Clock()) as mem:  # opens it, or creates it if never renamed
        lines = (inv / "journal.jsonl").read_bytes().split(b"\n")[:-1]
        n = len(lines)
        assert lines == ref.lines[:n], "history differs from the uninterrupted run"
        # Exactly the records whose line was completely written are committed: rec0 plus the appends done.
        expected = 1 + done["appends_done"]
        assert n == expected, f"{n} records after reopen, {expected} lines were completely written"
        assert len(mem.view.records) == n
        torn = mem.torn_copies()
        assert (mem.torn_tail is not None) == bool(torn)
        if point == "journal.during_append":
            assert torn == ["journal.jsonl.torn-0"] and mem.torn_tail is not None
        for name in mem.view.referenced_blobs():
            mem.blobs.verify(name)
        orphans = mem.orphan_blobs()
        assert set(mem.blobs.names()) <= ref.blobs, "a blob the uninterrupted run never wrote"
        assert mem.blobs.temporaries() == []
        assert not [x for x in os.listdir(inv) if x.startswith(".journal.tmp-")]
        committed_before = sorted(s for s in STEPS if mem.view.step_state(s) == "succeeded")
        drive(mem)
        assert mem.view.content_digest() == ref.content
        assert mem.view.root_id == ref.root_id
        assert set(mem.blobs.names()) == ref.blobs
        assert mem.orphan_blobs() == []
        for step in STEPS:
            succeeded = [a for a in mem.view.attempts[step] if a.end_kind == "step_succeeded"]
            assert len(succeeded) == 1, f"{step}: {len(succeeded)} succeeded attempts"
        final = (inv / "journal.jsonl").read_bytes().split(b"\n")[:-1]
        assert final[:n] == lines, "resume rewrote history"
    return {
        "point": point,
        "occurrence": occurrence,
        "existed": existed,
        "records_after_reopen": n,
        "torn_copies": len(torn),
        "orphans_before_resume": len(orphans),
        "committed_steps_before_resume": committed_before,
    }


def _fresh_root(tmp: Path) -> Path:
    shutil.rmtree(tmp / "memory", ignore_errors=True)
    return memory_root(tmp)


@pytest.mark.parametrize("point", WORKLOAD_POINTS)
def test_crash_at_every_occurrence_of_every_boundary(reference: Reference, point: str) -> None:
    occurrences = reference.counts[point]
    assert occurrences >= 1, f"the workload never reaches {point}"
    rows = []
    for how in PARTIAL.get(point, (None,)):
        for k in range(1, occurrences + 1):
            root = _fresh_root(reference.base)
            done = _crash_child(root, point, k, how, _workload)
            row = _check_after_crash(reference, root, point, k, done)
            row["partial"] = how
            rows.append(row)
    _record_matrix(point, rows)


def _record_matrix(point: str, rows: list[dict[str, Any]]) -> None:
    """With CITERIFT_FAULT_MATRIX set, append the rows (JSON lines) for the Step 6 evidence."""
    out = os.environ.get("CITERIFT_FAULT_MATRIX")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, sort_keys=True) + "\n")


@pytest.mark.parametrize("point", ["torn.copied", "torn.prefix_written"])
def test_crash_during_torn_tail_repair(reference: Reference, point: str) -> None:
    """A crash while a torn tail is being preserved and removed leaves the journal unchanged or repaired, never
    damaged; the next writable open finishes the repair and every preserved copy equals the torn journal."""
    root = _fresh_root(reference.base)
    _workload(root)
    journal = root / reference.key / "journal.jsonl"
    torn = journal.read_bytes()[:-7]  # the final record loses its end
    journal.write_bytes(torn)

    def reopen(r: Path) -> None:
        InvestigationMemory.open(r, reference.key, clock=Clock()).close()

    _crash_child(root, point, 1, None, reopen)
    assert journal.read_bytes() == torn  # the rename never happened: the journal is untouched
    with InvestigationMemory.open(root, reference.key, clock=Clock()) as mem:
        copies = mem.torn_copies()
        assert copies and all((root / reference.key / c).read_bytes() == torn for c in copies)
        assert (journal.read_bytes() + b"").split(b"\n")[:-1] == reference.lines[:-1]
        assert not [x for x in os.listdir(root / reference.key) if x.startswith(".journal.tmp-")]
        drive(mem)
        assert mem.view.content_digest() == reference.content
    _record_matrix(point, [{"point": point, "occurrence": 1, "torn_copies": len(copies), "partial": None}])


@pytest.mark.parametrize("point", ["create.prepared", "create.renamed"])
def test_crash_during_creation_leaves_no_half_investigation(reference: Reference, point: str) -> None:
    root = _fresh_root(reference.base)
    _crash_child(root, point, 1, None, _workload)
    names = os.listdir(root)
    if point == "create.prepared":
        # Not yet renamed: no investigation exists; the prepared directory is an inert leftover (reported).
        assert reference.key not in names
        assert all(n.startswith(".creating-") for n in names) and names
    else:
        assert reference.key in names
    with InvestigationMemory.create(root, bundle_payload(root), clock=Clock()) as mem:
        drive(mem)
        assert mem.view.content_digest() == reference.content


def test_every_boundary_is_exercised(reference: Reference) -> None:
    """The workload reaches every non-repair boundary; the repair boundaries have their own test."""
    assert {p for p in WORKLOAD_POINTS if reference.counts[p] == 0} == set()
    assert set(faults.POINTS) == set(WORKLOAD_POINTS) | {"torn.copied", "torn.prefix_written"}
