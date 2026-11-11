"""Step 6: journal chain, fold, Memory invariants, torn tail versus corruption (SPEC 8, 10.1, 10.2; MM 7)."""

from __future__ import annotations

import copy
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from memory_support import (
    CAPTURE,
    STAGE04,
    Clock,
    append_evidence,
    bundle_payload,
    drive,
    h,
    live_request,
    memory_root,
    new_memory,
    not_found_claim,
    root_object,
)

from citerift.investigation import batches, ids
from citerift.investigation import journal as journal_module
from citerift.investigation.canonical import canon
from citerift.investigation.errors import (
    AppendRefused,
    BlobError,
    CanonError,
    CorruptInvestigation,
    InvestigationMemoryError,
    StorageError,
)
from citerift.investigation.memory import InvestigationMemory, created_payload

pytestmark = pytest.mark.integration


def journal_path(root: Path, key: str) -> Path:
    return root / key / "journal.jsonl"


def records_of(root: Path, key: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in journal_path(root, key).read_bytes().splitlines()]


def rewrite(root: Path, key: str, records: list[dict[str, Any]], *, rechain: bool = True) -> None:
    """Write records back, recomputing seq-independent chain fields so that only the intended defect remains."""
    out = []
    prev = ids.genesis(key)
    for original in records:
        r = copy.deepcopy(original)
        if rechain:
            r["prev"] = prev
            r["digest"] = ids.record_digest(r)
            prev = r["digest"]
        out.append(canon(r) + b"\n")
    journal_path(root, key).write_bytes(b"".join(out))


def reopen_error(root: Path, key: str) -> CorruptInvestigation:
    with pytest.raises(CorruptInvestigation) as exc:
        InvestigationMemory.open(root, key, clock=Clock())
    return exc.value


def completed(tmp: Path) -> tuple[Path, str]:
    mem, root = new_memory(tmp)
    drive(mem)
    key = mem.key
    mem.close()
    return root, key


# Creation and reopening -------------------------------------------------------------------------------------------


def test_create_reopen_and_fold_agree(tmp_path: Path) -> None:
    mem, root = new_memory(tmp_path)
    drive(mem)
    states = {s: mem.view.step_state(s) for s in mem.view.attempts}
    digest, n, root_id = mem.view.content_digest(), len(mem.view.records), mem.view.root_id
    mem.close()
    with InvestigationMemory.open(root, mem.key, clock=Clock()) as again:
        assert {s: again.view.step_state(s) for s in again.view.attempts} == states
        assert (again.view.content_digest(), len(again.view.records), again.view.root_id) == (digest, n, root_id)
        assert again.orphan_blobs() == []
        assert again.torn_copies() == []
    assert sorted(os.listdir(root / mem.key)) == ["blobs", "journal.jsonl", "lock"]


def test_creation_is_idempotent_and_refuses_a_different_payload(tmp_path: Path) -> None:
    mem, root = new_memory(tmp_path)
    key = mem.key
    mem.close()
    with InvestigationMemory.create(root, bundle_payload(root), clock=Clock()) as again:
        assert again.key == key and len(again.view.records) == 1
    other = bundle_payload(root)
    other["request"]["index_path"] = "/data/other-index.sqlite"  # same key (paths are not identity), other payload
    assert other["investigation_key"] == key
    with pytest.raises(InvestigationMemoryError) as exc:
        InvestigationMemory.create(root, other, clock=Clock())
    assert exc.value.code == "INVESTIGATION_REQUEST_DIFFERS"
    assert len(records_of(root, key)) == 1


def test_live_request_creation_and_derived_identities(tmp_path: Path) -> None:
    root = memory_root(tmp_path)
    payload = created_payload(live_request(root), STAGE04)
    assert payload["request_key"] == {"wiki": "ar", "revision_id": 76190003}
    with InvestigationMemory.create(root, payload, clock=Clock()) as mem:
        assert (
            mem.key
            == payload["investigation_key"]
            == ids.investigation_key(payload["request_key"], "plan-1", ids.config_digest(payload["request"]["config"]))
        )
        assert payload["investigation_id"] == ids.investigation_id(mem.key)
    bad = copy.deepcopy(payload)
    bad["request"]["config"]["live_acquire_bound"]["t_acq_ms"] = 239_999  # D-042 arithmetic
    bad["config_digest"] = ids.config_digest(bad["request"]["config"])
    bad["investigation_key"] = ids.investigation_key(bad["request_key"], "plan-1", bad["config_digest"])
    bad["investigation_id"] = ids.investigation_id(bad["investigation_key"])
    with pytest.raises(AppendRefused) as exc:
        InvestigationMemory.create(root, bad, clock=Clock())
    assert exc.value.code == "CONFIG_INVALID"


@pytest.mark.negative
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("config_digest", h("x")),
        ("investigation_key", h("x")),
        ("investigation_id", "00000000-0000-8000-8000-000000000000"),
        ("request_key", {"capture_sha256": h("other")}),
    ],
)
def test_creation_identities_are_recomputed(tmp_path: Path, field: str, value: Any) -> None:
    root = memory_root(tmp_path)
    payload = bundle_payload(root)
    payload[field] = value
    with pytest.raises(InvestigationMemoryError):
        InvestigationMemory.create(root, payload, clock=Clock())


# Append guard: each Memory invariant refuses a bad record before it is written --------------------------------------


def journal_bytes(mem: InvestigationMemory) -> bytes:
    """The stored journal, read through the open investigation directory (no path is needed)."""
    fd = os.open("../journal.jsonl", os.O_RDONLY, dir_fd=mem.blobs.dir_fd)
    try:
        return os.read(fd, 1 << 24)
    finally:
        os.close(fd)


def refused(mem: InvestigationMemory, invariant: str, kind: str, payload: Any, **kw: Any) -> None:
    before = journal_bytes(mem)
    with pytest.raises(AppendRefused) as exc:
        mem.append(kind, payload, **kw)
    assert exc.value.invariant == invariant, exc.value
    assert journal_bytes(mem) == before  # nothing written


@pytest.fixture
def mem(tmp_path: Path) -> Any:
    m, _ = new_memory(tmp_path)
    yield m
    m.close()


@pytest.mark.negative
def test_m6_commit_discipline(mem: InvestigationMemory) -> None:
    blob = mem.put_blob({"x": 1})
    obs = {"obs_kind": "bundle", "blob": blob, "source_ref": {"engine": "citerift.wiki", "operation": "open_bundle",
                                                               "locator": None}}  # fmt: skip
    refused(mem, "M-6", "observation_recorded", obs, step="ACQUIRE", attempt=1)  # no open attempt
    refused(mem, "M-6", "step_started", {"step_key": h("v")}, step="VALIDATE", attempt=2)  # attempts count from 1
    mem.append("step_started", {"step_key": h("v")}, step="VALIDATE", attempt=1)
    refused(mem, "M-6", "step_started", {"step_key": h("a")}, step="ACQUIRE", attempt=1)  # overlapping attempt
    refused(mem, "M-6", "step_failed", {"step_key": h("v"), "code": "INPUT_INVALID", "retryable": False,
                                        "reason": "WIKI_UNSUPPORTED", "detail": None, "wall_clock": None},
            step="VALIDATE", attempt=2)  # fmt: skip
    mem.append("step_interrupted", {"step_key": h("v")}, step="VALIDATE", attempt=1)
    mem.append("step_started", {"step_key": h("v")}, step="VALIDATE", attempt=2)
    out = [mem.put_blob({"validated": "SYNTHETIC"})]
    mem.append("step_succeeded", {"step_key": h("v"), "outputs": out, "root": None}, step="VALIDATE", attempt=2)
    assert mem.view.step_state("VALIDATE") == "succeeded"


@pytest.mark.negative
def test_m14_a_succeeded_step_never_restarts(mem: InvestigationMemory) -> None:
    drive(mem, ("VALIDATE",))
    refused(mem, "M-14", "step_started", {"step_key": h("v")}, step="VALIDATE", attempt=2)


@pytest.mark.negative
def test_m9_root_binding(mem: InvestigationMemory) -> None:
    drive(mem, ("VALIDATE",))
    mem.append("step_started", {"step_key": h("a")}, step="ACQUIRE", attempt=1)
    out = [mem.put_blob({"bundle": "SYNTHETIC"})]
    good = root_object()
    wrong_id = copy.deepcopy(good)
    wrong_id["root_id"] = h("not the hash")
    refused(mem, "M-9", "step_succeeded", {"step_key": h("a"), "outputs": out, "root": wrong_id},
            step="ACQUIRE", attempt=1)  # fmt: skip
    other_capture = root_object(capture=h("another capture"))  # a root that does not match the request
    refused(mem, "M-9", "step_succeeded", {"step_key": h("a"), "outputs": out, "root": other_capture},
            step="ACQUIRE", attempt=1)  # fmt: skip
    title_only = copy.deepcopy(good)
    title_only["subject"]["display"]["title"] = "Another title"  # the title is not identity: still the same root
    mem.append("step_succeeded", {"step_key": h("a"), "outputs": out, "root": title_only}, step="ACQUIRE", attempt=1)
    assert mem.view.root_id == good["root_id"] and mem.view.bind_seq == len(mem.view.records) - 1
    # After the bind every record carries the root (set by Memory); the root cannot be replaced.
    rec = mem.append("step_started", {"step_key": h("e")}, step="EXTRACT", attempt=1)
    assert rec["root_id"] == good["root_id"]
    assert mem.view.root_id == good["root_id"]


@pytest.mark.negative
def test_m9_records_before_the_bind_are_unbound_and_scientific_content_needs_the_root(
    mem: InvestigationMemory,
) -> None:
    rec = mem.append("step_started", {"step_key": h("v")}, step="VALIDATE", attempt=1)
    assert rec["root_id"] is None
    refused(mem, "SCHEMA", "evidence_batch_recorded", batch_payload(mem, [_ev(h("o"))]), step="VALIDATE", attempt=1)


@pytest.mark.negative
def test_m4_m10_references_resolve_to_earlier_records_of_the_right_layer(mem: InvestigationMemory) -> None:
    drive(mem, ("VALIDATE", "ACQUIRE", "EXTRACT"))
    mem.append("step_started", {"step_key": h("n")}, step="NORMALIZE", attempt=1)
    unrecorded = mem.put_blob({"never": "recorded as an observation"})
    refused(mem, "M-10", "evidence_batch_recorded", batch_payload(mem, [_ev(unrecorded)]), step="NORMALIZE", attempt=1)
    extraction = _extraction_blob(mem)
    ok_ev = _ev(extraction)
    dangling = batch_payload(mem, [{**ok_ev, "refs": [h("missing")]}])
    refused(mem, "M-4", "evidence_batch_recorded", dangling, step="NORMALIZE", attempt=1)
    mem.append("evidence_batch_recorded", batch_payload(mem, [ok_ev], total=2), step="NORMALIZE", attempt=1)
    again = batch_payload(mem, [ok_ev, _ev(extraction, "/x")], index=1, total=2)
    refused(mem, "M-14", "evidence_batch_recorded", again, step="NORMALIZE", attempt=1)  # defined once


def _ev(obs: str, pointer: str = "", refs: list[str] | None = None) -> dict[str, Any]:
    return {"evidence_id": ids.evidence_id(obs, pointer, "lookup_result"), "observation": obs, "pointer": pointer,
            "kind": "lookup_result", "refs": refs or [], "value": None}  # fmt: skip


def batch_payload(mem: InvestigationMemory, items: list[dict[str, Any]], index: int = 0, total: int = 1) -> Any:
    """A batch record payload over ``items`` as given (no reordering): for refusal tests."""
    digest = mem.put_blob(batches.evidence_batch(items))
    return {"batch": digest, "batch_index": index, "batch_total": total, "evidence_count": len(items)}


def candidate_payload(mem: InvestigationMemory, entries: list[dict[str, Any]], index: int = 0, total: int = 1) -> Any:
    """A DETECT candidate-result batch record payload over ``entries`` as given (no reordering): for refusal tests."""
    digest = mem.put_blob(batches.candidate_batch(entries))
    return {"batch": digest, "batch_index": index, "batch_total": total, "entry_count": len(entries)}


def _extraction_blob(mem: InvestigationMemory) -> str:
    for r in mem.view.records:
        if r["kind"] == "observation_recorded" and r["payload"]["obs_kind"] == "extraction":
            return str(r["payload"]["blob"])
    raise AssertionError("no extraction observation")


@pytest.mark.negative
def test_m7_claims_and_decisions_need_committed_support(mem: InvestigationMemory) -> None:
    drive(mem, ("VALIDATE", "ACQUIRE", "EXTRACT", "NORMALIZE", "LOOKUP"))
    mem.append("step_started", {"step_key": h("d")}, step="DETECT", attempt=1)
    claim = not_found_claim(mem, h("evidence that does not exist"))
    decision = {"decision_id": h("dec"), "claim_id": claim["claim_id"], "disposition": "REPORT_NOT_FOUND"}
    entry = {"claim": claim, "decision": decision, "question": None}
    refused(mem, "M-4", "candidate_result_batch_recorded", candidate_payload(mem, [entry]), step="DETECT", attempt=1)
    # D-055: a decision inside a candidate entry must name the entry's own claim.
    other = {**decision, "claim_id": h("no claim")}
    bad = {"claim": claim, "decision": other, "question": None}
    refused(mem, "M-7", "candidate_result_batch_recorded", candidate_payload(mem, [bad]), step="DETECT", attempt=1)


@pytest.mark.negative
def test_uncommitted_content_is_not_visible_to_later_attempts(mem: InvestigationMemory) -> None:
    """M-6: content of an attempt that did not succeed is ignored, so a retry may define the same ids again and
    nothing may refer to the failed attempt's ids."""
    drive(mem, ("VALIDATE", "ACQUIRE", "EXTRACT"))
    ext = _extraction_blob(mem)
    ev = _ev(ext)
    mem.append("step_started", {"step_key": h("n")}, step="NORMALIZE", attempt=1)
    append_evidence(mem, [ev], "NORMALIZE", 1)
    mem.append("step_interrupted", {"step_key": h("n")}, step="NORMALIZE", attempt=1)
    assert mem.view.committed.evidence == {}
    mem.append("step_started", {"step_key": h("n")}, step="NORMALIZE", attempt=2)
    child = _ev(ext, "/child", [ev["evidence_id"]])
    refused(mem, "M-4", "evidence_batch_recorded", batch_payload(mem, [child]), step="NORMALIZE", attempt=2)
    append_evidence(mem, [ev], "NORMALIZE", 2)  # the same batch again: the failed attempt's record is not a definition
    out = [mem.put_blob({"normalized": [ev["evidence_id"]]})]
    mem.append("step_succeeded", {"step_key": h("n"), "outputs": out, "root": None}, step="NORMALIZE", attempt=2)
    assert set(mem.view.committed.evidence) == {ev["evidence_id"]}


@pytest.mark.negative
def test_m8_supersession_needs_new_evidence(mem: InvestigationMemory) -> None:
    drive(mem)
    lookup_ev = next(iter(mem.view.committed.evidence))
    old = next(iter(mem.view.committed.claims))
    mem.append("step_started", {"step_key": h("x")}, step="ASSEMBLE", attempt=1)
    # ASSEMBLE cannot write claims (schema), and a supersession must name a successor with new evidence.
    bad = {"old_claim_id": old, "new_claim_id": old, "reason": "NEW_EVIDENCE", "new_evidence": [lookup_ev]}
    refused(mem, "M-8", "claim_superseded", bad, step="ASSEMBLE", attempt=1)


@pytest.mark.negative
def test_m3_a_record_cannot_name_a_missing_blob(mem: InvestigationMemory) -> None:
    mem.append("step_started", {"step_key": h("v")}, step="VALIDATE", attempt=1)
    refused(mem, "M-5", "step_succeeded", {"step_key": h("v"), "outputs": [h("not written")], "root": None},
            step="VALIDATE", attempt=1)  # fmt: skip


@pytest.mark.negative
def test_records_with_floats_or_oversize_are_refused(mem: InvestigationMemory) -> None:
    mem.append("step_started", {"step_key": h("v")}, step="VALIDATE", attempt=1)
    with pytest.raises(CanonError):
        mem.append("step_failed", {"step_key": h("v"), "code": "INPUT_INVALID", "retryable": False,
                                   "reason": "WIKI_UNSUPPORTED", "detail": None, "wall_clock": None, "x": 1.0},
                   step="VALIDATE", attempt=1)  # fmt: skip
    with pytest.raises(AppendRefused) as exc:
        mem.append("step_failed", {"step_key": h("v"), "code": "INPUT_INVALID", "retryable": False,
                                   "reason": "WIKI_UNSUPPORTED", "detail": "x" * (1024 * 1024), "wall_clock": None},
                   step="VALIDATE", attempt=1)  # fmt: skip
    assert exc.value.code == "RECORD_TOO_LARGE"


def test_at_never_decreases_even_if_the_clock_does(tmp_path: Path) -> None:
    """M-1: ``at`` is non-decreasing; a clock that goes back is clamped to the previous record's time."""
    root = memory_root(tmp_path)
    noon = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)
    times = iter([noon + timedelta(seconds=5), noon + timedelta(seconds=6), noon + timedelta(seconds=2)])
    with InvestigationMemory.create(root, bundle_payload(root), clock=lambda: next(times)) as m:
        m.append("step_started", {"step_key": h("v")}, step="VALIDATE", attempt=1)
        m.append("step_interrupted", {"step_key": h("v")}, step="VALIDATE", attempt=1)
        ats = [r["at"] for r in m.view.records]
    assert ats == ["2026-11-10T12:00:05.000000Z", "2026-11-10T12:00:06.000000Z", "2026-11-10T12:00:06.000000Z"]


@pytest.mark.negative
def test_read_only_open_cannot_append(tmp_path: Path) -> None:
    root, key = completed(tmp_path)
    with InvestigationMemory.open(root, key, writable=False, clock=Clock()) as ro:
        with pytest.raises(InvestigationMemoryError) as exc:
            ro.append("step_started", {"step_key": h("x")}, step="ASSEMBLE", attempt=1)
        assert exc.value.code == "READ_ONLY"


# Corruption on open: every invariant, found in a stored journal --------------------------------------------------


@pytest.mark.negative
@pytest.mark.parametrize(
    ("mutate", "invariant"),
    [
        (lambda rs: rs.__setitem__(3, {**rs[3], "seq": 9}), "M-1"),
        (lambda rs: rs.__delitem__(3), "M-1"),
        (lambda rs: rs.__setitem__(3, {**rs[3], "at": "2026-01-01T00:00:00Z"}), "M-1"),
        (lambda rs: rs.__setitem__(7, {**rs[7], "root_id": h("forged")}), "M-9"),  # after the bind at seq 5
        (lambda rs: rs.__setitem__(4, {**rs[4], "root_id": h("forged")}), "SCHEMA"),  # before the bind: null
        (lambda rs: rs.insert(6, copy.deepcopy(rs[6])), "M-1"),
        (lambda rs: rs.__setitem__(0, {**rs[0], "v": 2}), "S-8.7"),  # format 2 (D-047) is refused (D-053)
        (lambda rs: rs.append({**rs[-1], "seq": len(rs)}), "M-6"),  # a second terminal, no open attempt
        (lambda rs: rs.append({**rs[6], "seq": len(rs), "at": rs[-1]["at"], "attempt": 2}), "M-14"),  # EXTRACT again
    ],
)
def test_invariant_violations_in_a_stored_journal_are_corrupt(tmp_path: Path, mutate: Any, invariant: str) -> None:
    root, key = completed(tmp_path)
    rs = records_of(root, key)
    mutate(rs)
    rewrite(root, key, rs)
    err = reopen_error(root, key)
    assert getattr(err.cause, "invariant", None) == invariant, err


@pytest.mark.negative
def test_corrupt_investigation_is_never_repaired(tmp_path: Path) -> None:
    root, key = completed(tmp_path)
    rs = records_of(root, key)
    rs[2]["payload"]["step_key"] = h("tampered")  # historical record changed, digest not recomputed
    rewrite(root, key, rs, rechain=False)
    before = journal_path(root, key).read_bytes()
    err = reopen_error(root, key)
    assert err.cause.code == "JOURNAL_CORRUPT"
    assert journal_path(root, key).read_bytes() == before
    assert not [n for n in os.listdir(root / key) if n.startswith("journal.jsonl.torn")]


# Torn tail versus corruption: the owner's evidence list ------------------------------------------------------------


def _flip_hex(line: bytes, field: bytes) -> bytes:
    """Change the first hex digit of ``field``'s value, keeping its length."""
    at = line.index(field) + len(field)
    new = b"1" if line[at : at + 1] == b"0" else b"0"
    return line[:at] + new + line[at + 1 :]


def _lines(root: Path, key: str) -> list[bytes]:
    """The journal's lines without their newlines."""
    return journal_path(root, key).read_bytes().split(b"\n")[:-1]


@pytest.mark.parametrize(
    ("name", "tail"),
    [
        ("truncated final line", lambda last: last[: len(last) // 2]),
        ("invalid final JSON without its newline", lambda last: b"{not json"),
        ("final line zero-filled, no newline", lambda last: b"\x00" * 40),
        # D-044: a newline-terminated final line is a complete record; its defects are CORRUPT (tests below).
    ],
)
def test_torn_tail_is_preserved_and_removed(tmp_path: Path, name: str, tail: Any) -> None:
    root, key = completed(tmp_path)
    lines = _lines(root, key)
    good = b"".join(line + b"\n" for line in lines[:-1])
    damaged = good + tail(lines[-1] + b"\n")
    journal_path(root, key).write_bytes(damaged)
    with InvestigationMemory.open(root, key, writable=False, clock=Clock()) as ro:  # read-only: reported, unchanged
        assert ro.torn_tail is not None
        assert len(ro.view.records) == len(lines) - 1
    assert journal_path(root, key).read_bytes() == damaged
    with InvestigationMemory.open(root, key, clock=Clock()) as rw:
        assert rw.torn_copies() == ["journal.jsonl.torn-0"]
        assert len(rw.view.records) == len(lines) - 1
        assert rw.view.step_state("DETECT") == "running"  # the final step_succeeded was torn: not committed
        drive(rw)  # resume: the step re-runs and commits
        assert rw.view.step_state("DETECT") == "succeeded"
    assert (root / key / "journal.jsonl.torn-0").read_bytes() == damaged  # Copy → Verify → Preserve


@pytest.mark.negative
@pytest.mark.parametrize(
    "case",
    ["modified historical record", "broken prev", "wrong digest in history", "torn line before the end"],
)
def test_corruption_is_distinct_from_a_torn_tail(tmp_path: Path, case: str) -> None:
    root, key = completed(tmp_path)
    lines = _lines(root, key)
    i = 5
    if case == "modified historical record":
        lines[i] = _flip_hex(lines[i], b'"step_key":"')  # still schema-valid; the digest no longer matches
    elif case == "broken prev":
        rs = records_of(root, key)
        rs[i]["prev"] = h("other")
        rs[i]["digest"] = ids.record_digest(rs[i])  # the record is self-consistent; the chain is not
        lines[i] = canon(rs[i])
    elif case == "wrong digest in history":
        lines[i] = _flip_hex(lines[i], b'"digest":"')
    else:
        lines[i] = lines[i][:20]
    data = b"".join(line + b"\n" for line in lines)
    journal_path(root, key).write_bytes(data)
    err = reopen_error(root, key)
    assert getattr(err.cause, "invariant", None) == "M-2", err
    assert journal_path(root, key).read_bytes() == data


@pytest.mark.negative
def test_missing_or_corrupted_blob_is_corrupt(tmp_path: Path) -> None:
    root, key = completed(tmp_path)
    blobs = sorted((root / key / "blobs").iterdir())
    victim = blobs[0]
    data = victim.read_bytes()
    victim.unlink()
    err = reopen_error(root, key)
    assert err.cause.code == "BLOB_MISSING"
    victim.write_bytes(data.replace(b"S", b"T", 1) if b"S" in data else data + b" ")
    err = reopen_error(root, key)
    assert err.cause.code == "BLOB_CORRUPT"
    victim.write_bytes(data)
    with InvestigationMemory.open(root, key, clock=Clock()):
        pass


@pytest.mark.negative
def test_blob_under_its_name_that_is_not_canonical_is_corrupt(tmp_path: Path) -> None:
    mem, root = new_memory(tmp_path)
    with pytest.raises(CanonError):
        mem.put_blob_bytes(b'{"a": 1}')
    blob = mem.put_blob({"a": 1})
    assert mem.put_blob({"a": 1}) == blob  # idempotent
    mem.close()
    path = root / mem.key / "blobs" / blob
    path.chmod(0o644)
    path.write_bytes(b'{"a":2}')
    with InvestigationMemory.open(root, mem.key, clock=Clock()) as again, pytest.raises(BlobError) as exc:
        again.put_blob({"a": 1})  # orphan blob (no record names it), so the open succeeds; the put refuses
    assert exc.value.code == "BLOB_CORRUPT"
    assert path.read_bytes() == b'{"a":2}'  # never overwritten


@pytest.mark.negative
def test_corrupt_history_with_a_torn_tail_is_not_repaired(tmp_path: Path) -> None:
    """Validation precedes any change: a torn tail after a corrupt record is not removed, nothing is copied."""
    root, key = completed(tmp_path)
    lines = _lines(root, key)
    lines[3] = _flip_hex(lines[3], b'"digest":"')
    data = b"".join(line + b"\n" for line in lines[:-1]) + lines[-1][:10]
    journal_path(root, key).write_bytes(data)
    err = reopen_error(root, key)
    assert getattr(err.cause, "invariant", None) == "M-2"
    assert journal_path(root, key).read_bytes() == data
    assert sorted(os.listdir(root / key)) == ["blobs", "journal.jsonl", "lock"]


@pytest.mark.reproducibility
def test_m13_equal_committed_inputs_give_an_equal_content_digest(tmp_path: Path) -> None:
    """M-13: C(J) depends on committed content only, not on the memory root, times, or failed attempts."""
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    first, _ = new_memory(tmp_path / "a")
    drive(first)
    second, _ = new_memory(tmp_path / "b")
    drive(second, ("VALIDATE", "ACQUIRE"))
    second.append("step_started", {"step_key": h("EXTRACT")}, step="EXTRACT", attempt=1)
    second.put_blob({"partial": "work of an attempt that never commits"})
    second.append("step_interrupted", {"step_key": h("EXTRACT")}, step="EXTRACT", attempt=1)
    drive(second)
    assert first.key == second.key
    assert first.view.content_digest() == second.view.content_digest()
    assert len(first.view.records) != len(second.view.records)
    first.close()
    second.close()


@pytest.mark.negative
def test_failed_write_poisons_the_instance_until_reopen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC 10.2 disk full: a failed append raises STORAGE_ERROR, commits nothing, and the instance writes no more."""
    m, root = new_memory(tmp_path)
    m.append("step_started", {"step_key": h("v")}, step="VALIDATE", attempt=1)

    def no_space(fd: int) -> None:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(journal_module.os, "fsync", no_space)
    with pytest.raises(StorageError) as exc:
        m.append("step_interrupted", {"step_key": h("v")}, step="VALIDATE", attempt=1)
    assert exc.value.code == "STORAGE_ERROR"
    assert len(m.view.records) == 2  # the fold did not advance
    monkeypatch.undo()
    with pytest.raises(StorageError):
        m.append("step_interrupted", {"step_key": h("v")}, step="VALIDATE", attempt=1)
    with pytest.raises(StorageError):
        m.put_blob({"x": 1})
    m.close()
    with InvestigationMemory.open(root, m.key, clock=Clock()) as again:
        # The line reached the file before fsync failed; append truncated it back, so nothing was committed.
        assert len(again.view.records) == 2
        assert again.torn_tail is None


@pytest.mark.negative
@pytest.mark.parametrize("where", ["request", "stage04"])
def test_unsupported_schema_version_is_refused(tmp_path: Path, where: str) -> None:
    """SR-12 / S-8.7: a version the reader does not know is refused, not interpreted."""
    root = memory_root(tmp_path)
    payload = bundle_payload(root)
    payload = copy.deepcopy(payload)
    payload[where]["schema_version"] = "3.0.0"
    with pytest.raises(AppendRefused) as exc:
        InvestigationMemory.create(root, payload, clock=Clock())
    assert exc.value.invariant == "SCHEMA"
    assert os.listdir(root) == []


@pytest.mark.negative
def test_an_exception_of_any_type_during_append_commits_nothing(tmp_path: Path) -> None:
    """Review finding R6-1: an interrupt after the write and before fsync leaves no record and a poisoned instance,
    so the next append cannot reuse the sequence number and fork the chain."""
    from citerift.investigation import faults

    m, root = new_memory(tmp_path)

    def interrupt(name: str, ctx: dict[str, Any]) -> None:
        if name == "journal.after_write":
            raise KeyboardInterrupt

    faults.install(interrupt)
    try:
        with pytest.raises(KeyboardInterrupt):
            m.append("step_started", {"step_key": h("v")}, step="VALIDATE", attempt=1)
    finally:
        faults.install(None)
    with pytest.raises(StorageError):
        m.append("step_started", {"step_key": h("v")}, step="VALIDATE", attempt=1)
    m.close()
    with InvestigationMemory.open(root, m.key, clock=Clock()) as again:
        assert len(again.view.records) == 1
        drive(again)


@pytest.mark.negative
def test_records_never_alias_the_callers_objects(tmp_path: Path) -> None:
    """Review finding R6-4: mutating a payload after append, or the record append returns, changes neither the view
    nor C(J); created_payload copies its inputs."""
    root = memory_root(tmp_path)
    stage04 = dict(STAGE04)
    payload = created_payload(bundle_payload(root)["request"], stage04, bundle_capture_sha256=CAPTURE)
    stage04["schema_version"] = "9.9.9"
    assert payload["stage04"]["schema_version"] == "2.0.0"
    with InvestigationMemory.create(root, payload, clock=Clock()) as m:
        drive(m)
        before = m.view.content_digest()
        mine = {"step_key": h("x")}
        returned = m.append("step_started", mine, step="ASSEMBLE", attempt=1)
        mine["step_key"] = h("changed")
        returned["payload"]["step_key"] = h("changed too")
        assert m.view.records[-1]["payload"]["step_key"] == h("x")
        assert m.view.content_digest() == before


@pytest.mark.negative
def test_journal_size_bound_is_enforced_on_append(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Review finding R6-9: an append that would make the journal unreadable (over its bound) is refused."""
    from citerift.investigation import memory as memory_module

    m, _ = new_memory(tmp_path)
    with m:
        size = len(journal_bytes(m))
        monkeypatch.setattr(memory_module, "MAX_JOURNAL_BYTES", size + 10)
        refused(m, "S-8.3", "step_started", {"step_key": h("v")}, step="VALIDATE", attempt=1)


# D-044: an incomplete append is a torn tail; a complete record that fails validation is CORRUPT ------------------


def _d044_journal(tmp_path: Path) -> tuple[Path, str, list[bytes]]:
    root, key = completed(tmp_path)
    return root, key, _lines(root, key)


def _store(root: Path, key: str, data: bytes) -> bytes:
    journal_path(root, key).write_bytes(data)
    return data


@pytest.mark.regression
def test_d044_r6_2_complete_final_record_with_wrong_digest_is_corrupt(tmp_path: Path) -> None:
    """R6-2 fail-first regression (D-044 case 3): at 6fd799d this record was dropped as a torn tail."""
    root, key, lines = _d044_journal(tmp_path)
    data = _store(root, key, b"".join(x + b"\n" for x in lines[:-1]) + _flip_hex(lines[-1], b'"digest":"') + b"\n")
    for writable in (False, True):
        with pytest.raises(CorruptInvestigation) as exc:
            InvestigationMemory.open(root, key, writable=writable, clock=Clock())
        assert getattr(exc.value.cause, "invariant", None) == "M-2"
        assert exc.value.cause.code == "JOURNAL_CORRUPT"
    assert journal_path(root, key).read_bytes() == data
    assert sorted(os.listdir(root / key)) == ["blobs", "journal.jsonl", "lock"]


@pytest.mark.negative
@pytest.mark.parametrize(
    "case",
    [
        "malformed JSON, newline-terminated",  # D-044 case 4
        "non-canonical JSON, newline-terminated",  # D-044 case 4
        "valid digest over a wrong prev",  # D-044 case 5
        "schema violation, newline-terminated",
        "invariant violation, newline-terminated",
        "middle record corrupt",  # D-044 case 6
        "zero bytes, newline-terminated",
    ],
)
def test_d044_complete_defective_records_are_corrupt(tmp_path: Path, case: str) -> None:
    root, key, lines = _d044_journal(tmp_path)
    rs = records_of(root, key)
    if case == "malformed JSON, newline-terminated":
        lines[-1] = lines[-1][: len(lines[-1]) // 2]
    elif case == "non-canonical JSON, newline-terminated":
        lines[-1] = json.dumps(rs[-1], sort_keys=True, ensure_ascii=False).encode()  # spaces after separators
    elif case == "valid digest over a wrong prev":
        rs[-1]["prev"] = h("not the previous digest")
        rs[-1]["digest"] = ids.record_digest(rs[-1])
        lines[-1] = canon(rs[-1])
    elif case == "schema violation, newline-terminated":
        rs[-1]["kind"] = "no_such_kind"
        rs[-1]["digest"] = ids.record_digest(rs[-1])
        lines[-1] = canon(rs[-1])
    elif case == "invariant violation, newline-terminated":
        rs[-1]["seq"] = rs[-1]["seq"] + 1  # M-1
        rs[-1]["digest"] = ids.record_digest(rs[-1])
        lines[-1] = canon(rs[-1])
    elif case == "middle record corrupt":
        lines[10] = _flip_hex(lines[10], b'"digest":"')
    else:
        lines[-1] = b"\x00" * 40
    data = _store(root, key, b"".join(x + b"\n" for x in lines))
    for writable in (False, True):
        with pytest.raises(CorruptInvestigation):
            InvestigationMemory.open(root, key, writable=writable, clock=Clock())
    assert journal_path(root, key).read_bytes() == data
    assert not list((root / key).glob("journal.jsonl.torn-*"))


@pytest.mark.integration
@pytest.mark.parametrize(
    "case",
    [
        "truncated final JSON, no newline",  # D-044 case 1
        "complete canonical record, newline missing",  # D-044 case 2
        "one byte, no newline",
    ],
)
def test_d044_incomplete_final_line_is_a_torn_tail(tmp_path: Path, case: str) -> None:
    root, key, lines = _d044_journal(tmp_path)
    prefix = b"".join(x + b"\n" for x in lines[:-1])
    tail = {
        "truncated final JSON, no newline": lines[-1][:-9],
        "complete canonical record, newline missing": lines[-1],
        "one byte, no newline": lines[-1][:1],
    }[case]
    data = _store(root, key, prefix + tail)
    with InvestigationMemory.open(root, key, writable=False, clock=Clock()) as ro:
        assert ro.torn_tail is not None and ro.torn_tail.reason == "final line has no newline"
        assert len(ro.view.records) == len(lines) - 1
    assert journal_path(root, key).read_bytes() == data  # read-only: unchanged
    with InvestigationMemory.open(root, key, clock=Clock()) as rw:  # D-044 case 8: recovery still works
        assert rw.torn_copies() == ["journal.jsonl.torn-0"]
        drive(rw)
        assert rw.view.step_state("DETECT") == "succeeded"
    assert journal_path(root, key).read_bytes().startswith(prefix)
    assert (root / key / "journal.jsonl.torn-0").read_bytes() == data


@pytest.mark.integration
def test_d044_legitimate_complete_final_record_is_valid(tmp_path: Path) -> None:
    """D-044 case 7."""
    root, key, lines = _d044_journal(tmp_path)
    with InvestigationMemory.open(root, key, clock=Clock()) as m:
        assert m.torn_tail is None and len(m.view.records) == len(lines)
        assert m.torn_copies() == []


@pytest.mark.negative
def test_d044_corrupt_prefix_before_an_incomplete_tail_is_not_mutated(tmp_path: Path) -> None:
    """D-044 recovery order: the prefix is validated first; a corrupt prefix means no journal mutation at all."""
    root, key, lines = _d044_journal(tmp_path)
    lines[4] = _flip_hex(lines[4], b'"digest":"')
    data = _store(root, key, b"".join(x + b"\n" for x in lines[:-1]) + lines[-1][:15])
    with pytest.raises(CorruptInvestigation):
        InvestigationMemory.open(root, key, clock=Clock())
    assert journal_path(root, key).read_bytes() == data
    assert sorted(os.listdir(root / key)) == ["blobs", "journal.jsonl", "lock"]


# D-044 focused re-review (findings D44-R1, D44-R2) ------------------------------------------------------------------


@pytest.mark.negative
def test_d044_fold_only_prefix_defect_before_an_incomplete_tail_is_not_mutated(tmp_path: Path) -> None:
    """D44-R1: the prefix is folded (schema, invariants, blobs) before any repair, not only parsed.

    Every line is intact, so ``parse_journal`` accepts the prefix; only the fold sees the missing blob. A repair run
    before the fold would preserve, rewrite and clean up here; the required order leaves every name and byte in place.
    The lock file is the one exception: taking the lock writes its informational content (SPEC 10.1 step 1)."""
    root, key, lines = _d044_journal(tmp_path)
    inv = root / key
    data = _store(root, key, b"".join(x + b"\n" for x in lines[:-1]) + lines[-1][:9])
    victim = sorted((inv / "blobs").iterdir())[0]
    victim.unlink()
    (inv / ".journal.tmp-deadbeefdeadbeef").write_bytes(b"stale")
    listing = sorted(os.listdir(inv))
    blobs = sorted(os.listdir(inv / "blobs"))
    for writable in (False, True):
        with pytest.raises(CorruptInvestigation) as exc:
            InvestigationMemory.open(root, key, writable=writable, clock=Clock())
        assert exc.value.cause.code == "BLOB_MISSING"
    assert journal_path(root, key).read_bytes() == data
    assert sorted(os.listdir(inv)) == listing  # the stale temporary is still there; no torn-* copy
    assert sorted(os.listdir(inv / "blobs")) == blobs
    assert (inv / ".journal.tmp-deadbeefdeadbeef").read_bytes() == b"stale"


@pytest.mark.negative
@pytest.mark.parametrize(
    "case",
    [
        "complete record, newline damaged",  # 0x0A -> 0x0B: a committed record, not an interrupted append
        "complete record followed by another byte",
        "complete record, newline replaced and a fragment follows",
        "tail longer than any append",
        "tail that cannot start a record",
        "garbage with a zero byte inside",  # D44-R2b
        "complete record, a zero byte, then other bytes",  # D44-R2b
        "complete value that is not a record",  # D44-R2b
        "complete record with a wrong digest",  # D44-R2b
        "copy of an earlier record",  # D44-R2b: valid, but not the next record
    ],
)
def test_d044_final_bytes_no_append_can_produce_are_corrupt(tmp_path: Path, case: str) -> None:
    """D44-R2: final bytes without a newline are a torn tail only if an interrupted append could have written them.

    An append writes one record line (at most ``MAX_RECORD_BYTES``, starting with ``{``) and its newline in one write,
    so an interrupted append leaves a prefix of that line, possibly followed by zero bytes. Final bytes that hold a
    complete record followed by anything but zero bytes, that exceed a record line, or that cannot start one were
    never an append in progress: the journal is CORRUPT and nothing is dropped."""
    root, key, lines = _d044_journal(tmp_path)
    last = lines[-1]
    tail = {
        "complete record, newline damaged": last + b"\x0b",
        "complete record followed by another byte": last + b"}",
        "complete record, newline replaced and a fragment follows": last + b" " + last[:20],
        "tail longer than any append": b"{" + b"a" * (journal_module.MAX_RECORD_BYTES + 1),  # > line + newline
        "tail that cannot start a record": b"\r",
        "garbage with a zero byte inside": b"garbage\x00x",
        "complete record, a zero byte, then other bytes": last + b"\x00junk",
        "complete value that is not a record": b'{"a":1}',
        "complete record with a wrong digest": _flip_hex(last, b'"digest":"'),
        "copy of an earlier record": lines[-3],
    }[case]
    data = _store(root, key, b"".join(x + b"\n" for x in lines[:-1]) + tail)
    # A valid record that is not the next one is refused by the fold's next-record check (D-046), as M-1.
    expected = "SEQUENCE_BROKEN" if case == "copy of an earlier record" else "JOURNAL_CORRUPT"
    for writable in (False, True):
        with pytest.raises(CorruptInvestigation) as exc:
            InvestigationMemory.open(root, key, writable=writable, clock=Clock())
        assert exc.value.cause.code == expected
    assert journal_path(root, key).read_bytes() == data
    assert sorted(os.listdir(root / key)) == ["blobs", "journal.jsonl", "lock"]


@pytest.mark.integration
@pytest.mark.parametrize(
    "case",
    [
        "prefix of the final record, then zero bytes",
        "complete final record, then zero bytes instead of its newline",
        "zero bytes, then the rest of the final record",
        "prefix of the final record with zeroed bytes inside",
        "a whole maximal append zero-filled",  # D44-R2a: a line of MAX_RECORD_BYTES and its newline, all zeroed
    ],
)
def test_d044_interrupted_append_with_zero_filled_bytes_is_a_torn_tail(tmp_path: Path, case: str) -> None:
    """D44-R2 counterpart: what a crash can leave of an append (a prefix, with zero-filled blocks) stays a torn tail."""
    root, key, lines = _d044_journal(tmp_path)
    last = lines[-1]
    prefix = b"".join(x + b"\n" for x in lines[:-1])
    tail = {
        "prefix of the final record, then zero bytes": last[:30] + b"\x00" * 50,
        "complete final record, then zero bytes instead of its newline": last + b"\x00",
        "zero bytes, then the rest of the final record": b"\x00" * 30 + last[30:-5],
        "prefix of the final record with zeroed bytes inside": last[:10] + b"\x00" * 20 + last[30:-5],
        "a whole maximal append zero-filled": b"\x00" * (journal_module.MAX_RECORD_BYTES + 1),
    }[case]
    data = _store(root, key, prefix + tail)
    with InvestigationMemory.open(root, key, writable=False, clock=Clock()) as ro:
        assert ro.torn_tail is not None and len(ro.view.records) == len(lines) - 1
    assert journal_path(root, key).read_bytes() == data
    with InvestigationMemory.open(root, key, clock=Clock()) as rw:
        assert rw.torn_copies() == ["journal.jsonl.torn-0"]
        drive(rw)
        assert rw.view.step_state("DETECT") == "succeeded"
    assert (root / key / "journal.jsonl.torn-0").read_bytes() == data


# D-046: a complete record without its newline is a torn tail only if it is a fully valid next record -------------


def _unterminated_candidate(root: Path, key: str, at: int, change: Any) -> bytes:
    """Keep records before ``at``; append record ``at``, changed, with a recomputed digest and no newline.

    ``seq`` and ``prev`` stay those of the next record, and the digest is correct, so only full next-record
    validation (schema with JSON token types, kind, step legality, root binding, references, blobs) can refuse it."""
    lines = _lines(root, key)
    rec = records_of(root, key)[at]
    change(rec)
    rec["digest"] = ids.record_digest(rec)
    return _store(root, key, b"".join(x + b"\n" for x in lines[:at]) + canon(rec))


def _set(field: str, value: Any) -> Any:
    return lambda rec: rec.__setitem__(field, value)


def _set_payload(field: str, value: Any) -> Any:
    return lambda rec: rec["payload"].__setitem__(field, value)


@pytest.mark.regression
@pytest.mark.parametrize(
    ("at", "change"),
    [
        pytest.param(1, _set("seq", True), id="seq true where 1 is expected"),  # True == 1 in Python, not in JSON
        pytest.param(18, _set("v", True), id="journal version true"),
        pytest.param(18, _set("attempt", True), id="attempt true"),
        pytest.param(18, _set("kind", "no_such_kind"), id="unknown record kind"),
        pytest.param(18, _set("at", "2026-11-10T12:00:00.000000Z"), id="time earlier than the previous record"),
        pytest.param(18, _set("attempt", 2), id="terminal record of an attempt that is not open"),
        pytest.param(18, _set("root_id", h("another root")), id="root that is not the bound root"),
        pytest.param(18, _set_payload("outputs", [h("no such blob")]), id="success naming a missing blob"),
        pytest.param(17, _set_payload("batch", h("no such batch")), id="candidate batch naming a missing blob"),
        pytest.param(17, _set_payload("entry_count", 2), id="candidate batch with a wrong entry count"),
        pytest.param(17, _set_payload("batch_index", 1), id="candidate batch with a wrong batch index"),
        pytest.param(13, _set_payload("batch", h("no such batch")), id="lookup batch naming a missing blob"),
        pytest.param(13, _set_payload("batch_total", 0), id="lookup batch with a wrong batch total"),
        pytest.param(16, _set_payload("batch", h("no such batch")), id="evidence batch naming a missing blob"),
        pytest.param(16, _set_payload("evidence_count", 2), id="evidence batch with a wrong item count"),
    ],
)
def test_d046_complete_unterminated_record_must_be_a_valid_next_record(tmp_path: Path, at: int, change: Any) -> None:
    """D-046: complete, canonical, correctly hashed, next ``seq`` and ``prev``, but not a legal next record: CORRUPT."""
    root, key = completed(tmp_path)
    data = _unterminated_candidate(root, key, at, change)
    for writable in (False, True):
        with pytest.raises(CorruptInvestigation):
            InvestigationMemory.open(root, key, writable=writable, clock=Clock())
    assert journal_path(root, key).read_bytes() == data
    assert sorted(os.listdir(root / key)) == ["blobs", "journal.jsonl", "lock"]


@pytest.mark.integration
@pytest.mark.parametrize("at", [1, 5, 13, 16, 17, 18])
def test_d046_valid_next_record_without_its_newline_stays_a_torn_tail(tmp_path: Path, at: int) -> None:
    """D-046 positive control: the unchanged next record, only its newline missing, is torn and recovered."""
    root, key = completed(tmp_path)
    data = _unterminated_candidate(root, key, at, lambda rec: None)
    with InvestigationMemory.open(root, key, writable=False, clock=Clock()) as ro:
        assert ro.torn_tail is not None and len(ro.view.records) == at
    assert journal_path(root, key).read_bytes() == data
    with InvestigationMemory.open(root, key, clock=Clock()) as rw:
        assert rw.torn_copies() == ["journal.jsonl.torn-0"]
        drive(rw)
        assert rw.view.step_state("DETECT") == "succeeded"
