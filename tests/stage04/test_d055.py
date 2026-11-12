"""Owner decision D-055: the remaining per-candidate journal records are committed in step-local batches.

LOOKUP's lookup observation references are committed in LOOKUP batches and DETECT's claim, decision and optional
question of each candidate in DETECT candidate-result batches (SPEC 8.9). Owner items covered here: the deterministic
order and cut (input-order independence, N - 1 / N / N + 1, one legal entry always fits), commit discipline (a batch of
an attempt that did not succeed is not authoritative; no batch crosses a step or an attempt), the logical fold (the
same claims, decisions, questions and lookup observations as before), W-8 over the batched content, every batch and
candidate-result corruption the owner listed (all fail closed), and process death at the listed points with a
deterministic resume. SYNTHETIC fake adapters.
"""

from __future__ import annotations

import copy
import json
import os
import random
from collections import Counter
from collections.abc import Callable, Iterator
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from controller_support import (
    LOOKUP,
    T0,
    Env,
    Plan,
    Session,
    StepClock,
    claim_and_set,
    create,
    digest,
    journal,
    lookup_evidence,
    ok_result,
    run_once,
)
from memory_support import append_candidates, append_evidence, drive, h, new_memory, not_found_claim, with_legacy_bundle

from citerift.investigation import batches, faults, ids, workflow
from citerift.investigation.adapters import ContentRecord, StepRequest, StepResult, Succeeded
from citerift.investigation.blobs import MAX_BLOB_BYTES
from citerift.investigation.canonical import canon
from citerift.investigation.controller import run_investigation
from citerift.investigation.errors import AppendRefused, CorruptInvestigation
from citerift.investigation.fold import STEPS
from citerift.investigation.memory import InvestigationMemory

CLASSES = (
    ("IDENTITY_CONFLICT", "c1"),
    ("NOT_FOUND_IN_CHECKED_SOURCES", "c2"),
    ("CONTRADICTION_IN_SOURCES", "c3"),
)
ENTRY_KINDS = ("lookup_batch_recorded", "candidate_result_batch_recorded")
SMALL = 700  # bytes: below the size of one candidate entry, so each candidate result is its own batch
CRASH = 77


@pytest.fixture
def small_ceiling(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(batches, "MAX_PART_BYTES", SMALL)
    yield


def _lookup_entry(i: int, blob: str | None = None) -> dict[str, Any]:
    return {
        "obs_kind": "lookup",
        "blob": blob or h(f"lookup-{i}"),
        "source_ref": {"engine": "citerift.retraction", "operation": "gather", "locator": f"doi:10.1000/{i}"},
    }


def _candidate_entry(cls: str, cand: str) -> dict[str, Any]:
    c, _ = claim_and_set(cls, [e["evidence_id"] for e in lookup_evidence()], cand)
    disposition = workflow.DISPOSITION[cls]
    decision = {
        "decision_id": ids.decision_id(c["claim_id"], disposition),
        "claim_id": c["claim_id"],
        "disposition": disposition,
    }
    q = None
    if cls in workflow.CONFLICT:
        qkind = workflow.CONFLICT[cls]
        q = {"question_id": ids.question_id(c["claim_id"], qkind), "claim_id": c["claim_id"], "kind": qkind}
    return {"claim": c, "decision": decision, "question": q}


def _parts_digests(parts: list[dict[str, Any]]) -> list[str]:
    return [digest(p) for p in parts]


# Order and cut (SPEC 8.9) -------------------------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize("seed", range(5))
def test_candidate_order_and_boundaries_do_not_depend_on_the_input_order(seed: int) -> None:
    entries = [
        _candidate_entry(cls, f"cand-{i}")
        for i, cls in enumerate(
            ["RETRACTED_WORK_CITED"] * 6 + ["NOT_FOUND_IN_CHECKED_SOURCES", "IDENTITY_CONFLICT", "LOOKUP_UNAVAILABLE"]
        )
    ]
    reference = batches.ordered_parts(entries, batches.candidate_key, batches.candidate_batch, limit=3000)
    shuffled = entries[:]
    random.Random(seed).shuffle(shuffled)
    again = batches.ordered_parts(shuffled, batches.candidate_key, batches.candidate_batch, limit=3000)
    assert again == reference and _parts_digests(again) == _parts_digests(reference)
    flat = [e for p in reference for e in p["entries"]]
    keys = [batches.candidate_key(e) for e in flat]
    assert keys == sorted(keys) and len(set(keys)) == len(keys)  # strictly increasing: one entry per candidate
    assert len(reference) > 1  # the limit cuts: the property holds across batch boundaries


@pytest.mark.unit
@pytest.mark.parametrize("seed", range(5))
def test_lookup_order_and_boundaries_do_not_depend_on_the_input_order(seed: int) -> None:
    entries = [_lookup_entry(i) for i in range(40)] + [_lookup_entry(1), _lookup_entry(7)]  # two shared lookups
    reference = batches.ordered_parts(entries, batches.lookup_key, batches.lookup_batch, limit=2000)
    shuffled = entries[:]
    random.Random(seed).shuffle(shuffled)
    again = batches.ordered_parts(shuffled, batches.lookup_key, batches.lookup_batch, limit=2000)
    assert again == reference and _parts_digests(again) == _parts_digests(reference)
    keys = [batches.lookup_key(e) for p in reference for e in p["entries"]]
    assert keys == sorted(keys) and len(keys) == 42 and len(reference) > 1


@pytest.mark.unit
@pytest.mark.parametrize(("which", "k"), [("lookup", 1), ("lookup", 4), ("candidate", 1), ("candidate", 3)])
def test_entry_boundaries_at_n_minus_one_n_and_n_plus_one(which: str, k: int) -> None:
    """The same cut as D-053: a batch is exactly full at N bytes, one byte less moves its last entry on."""
    if which == "lookup":
        entries = [_lookup_entry(i) for i in range(k + 1)]
        key, make = batches.lookup_key, batches.lookup_batch
    else:
        entries = [_candidate_entry("RETRACTED_WORK_CITED", f"cand-{i}") for i in range(k + 1)]
        key, make = batches.candidate_key, batches.candidate_batch
    ordered = sorted(entries, key=key)
    n = len(canon(make(ordered[:k])))  # the exact bytes of a batch of the first k entries
    at_n = batches.ordered_parts(entries, key, make, limit=n)
    assert [len(p["entries"]) for p in at_n] == [k, 1] and all(len(canon(p)) <= n for p in at_n)
    below = batches.ordered_parts(entries, key, make, limit=n - 1)
    assert len(below[0]["entries"]) == k - 1 if k > 1 else len(below[0]["entries"]) == 1
    above = batches.ordered_parts(entries, key, make, limit=n + 1)
    assert [len(p["entries"]) for p in above] == [len(p["entries"]) for p in at_n]


@pytest.mark.unit
def test_one_legal_entry_always_fits_and_the_ceiling_is_the_d053_one() -> None:
    """D-055 reuses the D-053 primitive and ceiling (no second size): an entry larger than the ceiling forms its own
    batch, which is still below the blob limit (the bound is derived in ``d055/part_ceiling.json``)."""
    assert batches.MAX_PART_BYTES == 8 * 1024 * 1024
    big = _candidate_entry("RETRACTED_WORK_CITED", "big")
    parts = batches.ordered_parts(
        [big, _candidate_entry("RETRACTED_WORK_CITED", "x")], batches.candidate_key, batches.candidate_batch, limit=10
    )
    assert [len(p["entries"]) for p in parts] == [1, 1]


# Integration: format 4 commits, reopens and exposes the same logical objects ---------------------------------------


def _detect(classes: tuple[tuple[str, str], ...], reverse: bool = False) -> Callable[[StepRequest], StepResult]:
    def run(req: StepRequest) -> StepResult:
        r = ok_result(req, classes)
        assert isinstance(r, Succeeded)
        if not reverse:
            return r
        recs = tuple(reversed(r.records))
        return Succeeded(records=recs, blobs=tuple(reversed(r.blobs)), outputs=r.outputs)

    return run


def _lookup(n: int, reverse: bool = False) -> Callable[[StepRequest], StepResult]:
    """A LOOKUP adapter with ``n`` lookup observations (blob LOOKUP is the one the DETECT evidence names)."""

    def run(req: StepRequest) -> StepResult:
        values = [LOOKUP, *({"lookup": "SYNTHETIC", "candidate": i} for i in range(1, n))]
        recs = [ContentRecord("observation_recorded", _lookup_entry(i, digest(v))) for i, v in enumerate(values)]
        if reverse:
            recs.reverse()
        return Succeeded(records=tuple(recs), blobs=tuple(values), outputs=(digest(LOOKUP),))

    return run


def _run(tmp: Path, script: dict[tuple[str, int], Any] | None = None, classes: Any = CLASSES) -> tuple[Path, str, Any]:
    clock = StepClock()
    root, key = create(tmp, clock=clock)
    return root, key, run_once(root, key, Plan(script, classes=classes), Env(), clock)


def _view(root: Path, key: str) -> Any:
    with InvestigationMemory.open(root, key, writable=False) as mem:
        return mem.view


@pytest.mark.integration
@pytest.mark.usefixtures("small_ceiling")
def test_lookup_and_detect_records_are_batch_backed(tmp_path: Path) -> None:
    root, key, st = _run(tmp_path, {("LOOKUP", 1): _lookup(3)})
    assert st.lifecycle == "NEEDS_RESOLUTION"
    recs = journal(root, key)
    kinds = Counter((r["kind"], r["step"]) for r in recs)
    # No per-candidate record remains: one record per batch, the batches a canonical series of their attempt.
    assert not {k for k, _ in kinds} & {"claim_recorded", "decision_recorded", "question_opened"}
    assert not [r for r in recs if r["kind"] == "observation_recorded" and r["payload"]["obs_kind"] == "lookup"]
    look = [r for r in recs if r["kind"] == "lookup_batch_recorded"]
    cand = [r for r in recs if r["kind"] == "candidate_result_batch_recorded"]
    assert {(r["step"], r["attempt"]) for r in look} == {("LOOKUP", 1)}
    assert {(r["step"], r["attempt"]) for r in cand} == {("DETECT", 1)}
    assert [r["payload"]["batch_index"] for r in cand] == [0, 1, 2]  # SMALL: each candidate its own batch
    assert {r["payload"]["batch_total"] for r in cand} == {3}
    # The logical fold: three lookup observations, three claims with their decisions, two questions.
    f = _view(root, key)
    logical = Counter(r["kind"] for r in f.committed_content())
    assert logical["claim_recorded"] == 3 and logical["decision_recorded"] == 3
    assert logical["question_opened"] == 2
    assert (
        sum(
            1
            for r in f.committed_content()
            if r["kind"] == "observation_recorded" and r["payload"]["obs_kind"] == "lookup"
        )
        == 3
    )
    assert len(f.open_questions()) == 2 and len(f.committed.claims) == 3 and len(f.committed.decisions) == 3
    workflow.check_journal(f)


@pytest.mark.integration
def test_adapter_order_does_not_change_the_batches_or_the_digest(tmp_path: Path, small_ceiling: None) -> None:
    out = []
    for i, reverse in enumerate((False, True)):
        d = tmp_path / str(i)
        d.mkdir()
        script = {
            ("LOOKUP", 1): _lookup(5, reverse),
            ("DETECT", 1): _detect(CLASSES[::-1] if reverse else CLASSES, reverse),
        }
        root, key, st = _run(d, script)
        assert st.lifecycle == "NEEDS_RESOLUTION"
        f = _view(root, key)
        batch_digests = [r["payload"]["batch"] for r in f.records if r["kind"] in ENTRY_KINDS]
        out.append((batch_digests, f.content_digest()))
    assert out[0] == out[1]


# Commit discipline --------------------------------------------------------------------------------------------------


@pytest.mark.integration
def test_a_batch_of_an_attempt_that_did_not_succeed_is_not_authoritative(tmp_path: Path) -> None:
    mem, _ = new_memory(tmp_path)
    try:
        drive(mem, ("VALIDATE", "ACQUIRE", "EXTRACT", "NORMALIZE", "LOOKUP"))
        lookup = mem.put_blob({"lookup": "SYNTHETIC", "state": "no_record"})
        ev = {
            "evidence_id": ids.evidence_id(lookup, "", "lookup_result"),
            "observation": lookup,
            "pointer": "",
            "kind": "lookup_result",
            "refs": [],
            "value": None,
        }
        claim = not_found_claim(mem, ev["evidence_id"])
        decision = {"decision_id": h("decision"), "claim_id": claim["claim_id"], "disposition": "REPORT_NOT_FOUND"}
        entry = {"claim": claim, "decision": decision, "question": None}
        for attempt, end in ((1, "step_interrupted"), (2, "step_failed")):
            mem.append("step_started", {"step_key": h("DETECT")}, step="DETECT", attempt=attempt)
            append_evidence(mem, [ev], "DETECT", attempt)
            (rec,) = append_candidates(mem, [entry], "DETECT", attempt)
            assert mem.view.pending.series["candidate_result_batch_recorded"].digests == [rec["payload"]["batch"]]
            payload: dict[str, Any] = {"step_key": h("DETECT")}
            if end == "step_failed":
                payload.update(code="DECISION_TABLE_GAP", retryable=False, reason=None, detail=None, wall_clock=None)
            mem.append(end, payload, step="DETECT", attempt=attempt)
            # The batch record of an ended attempt defines nothing: no claim, decision or batch is committed.
            assert mem.view.committed.claims == {} and mem.view.committed.decisions == {}
            assert rec["payload"]["batch"] not in mem.view.committed.entry_batches
            assert not [r for r in mem.view.committed_content() if r["step"] == "DETECT"]
        key = mem.view.key
    finally:
        mem.close()
    root = tmp_path / "memory"
    assert key is not None
    f = _view(root, key)  # the stored journal replays with the same (empty) committed DETECT content
    assert f.committed.claims == {} and f.step_state("DETECT") == "failed_terminal"


@pytest.mark.negative
def test_no_batch_crosses_a_step_or_an_attempt(tmp_path: Path) -> None:
    mem, _ = new_memory(tmp_path)
    try:
        drive(mem, ("VALIDATE", "ACQUIRE", "EXTRACT", "NORMALIZE"))
        mem.append("step_started", {"step_key": h("LOOKUP")}, step="LOOKUP", attempt=1)
        d = mem.put_blob(batches.lookup_batch([_lookup_entry(0, mem.put_blob({"lookup": 0}))]))
        payload = {"batch": d, "batch_index": 0, "batch_total": 1, "entry_count": 1}
        for kind, step, attempt, invariant in (
            ("candidate_result_batch_recorded", "LOOKUP", 1, "SCHEMA"),  # a DETECT batch kind in LOOKUP
            ("lookup_batch_recorded", "LOOKUP", 2, "M-6"),  # a record of another attempt than the open one
            ("lookup_batch_recorded", "NORMALIZE", 1, "SCHEMA"),  # another step than the open one
        ):
            with pytest.raises(AppendRefused) as exc:
                mem.append(kind, payload, step=step, attempt=attempt)
            assert exc.value.invariant == invariant, (kind, step, attempt, exc.value)
        mem.append("lookup_batch_recorded", payload, step="LOOKUP", attempt=1)
        mem.append("step_succeeded", {"step_key": h("LOOKUP"), "outputs": [d], "root": None}, step="LOOKUP", attempt=1)
        assert mem.view.committed.entry_batches == {d}
        # DETECT cannot record the committed LOOKUP batch again, under either kind.
        mem.append("step_started", {"step_key": h("DETECT")}, step="DETECT", attempt=1)
        with pytest.raises(AppendRefused) as exc:
            mem.append("candidate_result_batch_recorded", payload, step="DETECT", attempt=1)
        assert exc.value.invariant == "M-14", exc.value
    finally:
        mem.close()


# W-8 over the batched content: every forbidden combination is refused at success and is corrupt in a stored journal


def _forge(root: Path, key: str, clock: StepClock, ops: list[tuple[str, Any, str | None, int | None]]) -> None:
    with InvestigationMemory.open(root, key, clock=clock) as mem:
        for kind, payload, step, attempt in ops:
            if kind == "blob":
                mem.put_blob(payload)
            else:
                mem.append(kind, payload, step=step, attempt=attempt)


def _until_lookup(tmp_path: Path) -> tuple[Path, str, StepClock]:
    clock = StepClock()
    root, key = create(tmp_path, clock=clock)
    with Session(root, key, Plan(), Env(), clock) as ctl:
        while ctl.view.step_state("LOOKUP") != "succeeded":
            ctl.step()
    return root, key, clock


def _detect_key(root: Path, key: str, clock: StepClock) -> str:
    with Session(root, key, Plan(), Env(), clock) as ctl:
        return workflow.step_key(ctl.view, "DETECT", ctl.current_digests())


def _claim_entry(cls: str, cand: str, disposition: str | None = None, question: Any = "derived") -> dict[str, Any]:
    e = _candidate_entry(cls, cand)
    if disposition is not None:
        cid = e["claim"]["claim_id"]
        e["decision"] = {"decision_id": ids.decision_id(cid, disposition), "claim_id": cid, "disposition": disposition}
    if question != "derived":
        e["question"] = question
    return e


def _extra_question(cls: str, cand: str) -> dict[str, Any]:
    e = _candidate_entry(cls, cand)
    cid = e["claim"]["claim_id"]
    e["question"] = {
        "question_id": ids.question_id(cid, "identity_conflict"),
        "claim_id": cid,
        "kind": "identity_conflict",
    }
    return e


# name -> the DETECT candidate entries of the forged attempt
W8_FORGERIES: dict[str, Callable[[], list[dict[str, Any]]]] = {
    "two claims for one candidate": lambda: [
        _candidate_entry("NOT_FOUND_IN_CHECKED_SOURCES", "c1"),
        _candidate_entry("RETRACTED_WORK_CITED", "c1"),
    ],
    "wrong disposition": lambda: [_claim_entry("NOT_FOUND_IN_CHECKED_SOURCES", "c1", disposition="REPORT_FINDING")],
    "conflict plus a positive result": lambda: [
        _candidate_entry("IDENTITY_CONFLICT", "c1"),
        _candidate_entry("RETRACTED_WORK_CITED", "c1"),
    ],
    "conflict plus a negative result": lambda: [
        _candidate_entry("CONTRADICTION_IN_SOURCES", "c1"),
        _candidate_entry("NOT_FOUND_IN_CHECKED_SOURCES", "c1"),
    ],
    "missing required question": lambda: [_claim_entry("IDENTITY_CONFLICT", "c1", question=None)],
    "extra question": lambda: [_extra_question("NOT_FOUND_IN_CHECKED_SOURCES", "c1")],
}


def _ev_and_sets(entries: list[dict[str, Any]]) -> list[tuple[str, Any, str | None, int | None]]:
    evs = lookup_evidence()
    ops: list[tuple[str, Any, str | None, int | None]] = []
    for e in entries:
        _, value = claim_and_set(
            e["claim"]["class"], [x["evidence_id"] for x in evs], _cand_name(e["claim"]["cand_ref"])
        )
        ops.append(("blob", value, None, None))
    found = batches.evidence_batches(evs, lambda ref: False)
    ops += [("blob", b, None, None) for b in found]
    ops += [("evidence_batch_recorded", r, "DETECT", 1) for r in batches.batch_records(_parts_digests(found), found)]
    parts = batches.ordered_parts(entries, batches.candidate_key, batches.candidate_batch)
    ops += [("blob", b, None, None) for b in parts]
    ops += [
        ("candidate_result_batch_recorded", r, "DETECT", 1) for r in batches.entry_records(_parts_digests(parts), parts)
    ]
    return ops


def _cand_name(cand_ref: str) -> str:
    return next(n for n in ("c1", "c2", "c3", "cand") if h(n) == cand_ref)


@pytest.mark.negative
@pytest.mark.parametrize("name", list(W8_FORGERIES))
def test_w8_refuses_forged_candidate_results_in_a_stored_journal(tmp_path: Path, name: str) -> None:
    root, key, clock = _until_lookup(tmp_path)
    k = _detect_key(root, key, clock)
    entries = W8_FORGERIES[name]()
    out = {"claims": sorted(e["claim"]["claim_id"] for e in entries)}
    _forge(
        root,
        key,
        clock,
        [
            ("blob", out, None, None),
            ("step_started", {"step_key": k}, "DETECT", 1),
            *_ev_and_sets(entries),
            ("step_succeeded", {"step_key": k, "outputs": [digest(out)], "root": None}, "DETECT", 1),
        ],
    )
    before = {p.name: p.read_bytes() for p in (root / key).iterdir() if p.is_file() and p.name != "lock"}
    res = run_investigation(root, key, Plan().adapters(), Env(), clock=clock)
    assert res.status == "CORRUPT" and "W-8:" in res.detail, res.detail
    after = {p.name: p.read_bytes() for p in (root / key).iterdir() if p.is_file() and p.name != "lock"}
    assert after == before


@pytest.mark.negative
@pytest.mark.parametrize("name", list(W8_FORGERIES))
def test_w8_refuses_forged_candidate_results_when_appended(tmp_path: Path, name: str) -> None:
    root, key, clock = _until_lookup(tmp_path)
    entries = W8_FORGERIES[name]()
    with Session(root, key, Plan(), Env(), clock) as ctl:
        digests = ctl.current_digests()
        k = workflow.step_key(ctl.view, "DETECT", digests)
        ctl._append("step_started", {"step_key": k}, "DETECT", 1)
        for kind, payload, step, attempt in _ev_and_sets(entries):
            if kind == "blob":
                ctl._mem.put_blob(payload)
            else:
                ctl._append(kind, payload, step, attempt)
        man = ctl._mem.put_blob(workflow.manifest(ctl.view, "DETECT", k, digests))
        with pytest.raises(workflow.WorkflowRefused) as exc:
            ctl._append("step_succeeded", {"step_key": k, "outputs": [man], "root": None}, "DETECT", 1)
        assert exc.value.rule == "W-8"


# Corruption: every case the owner listed fails closed -------------------------------------------------------------


@pytest.fixture
def stored(tmp_path: Path, small_ceiling: None) -> tuple[Path, str]:
    root, key, st = _run(tmp_path, {("LOOKUP", 1): _lookup(3)})
    assert st.lifecycle == "NEEDS_RESOLUTION"
    return root, key


def _rewrite(root: Path, key: str, records: list[dict[str, Any]]) -> None:
    out, prev = [], ids.genesis(key)
    for seq, original in enumerate(records):
        r = copy.deepcopy(original)
        r["seq"] = seq
        r["prev"] = prev
        r["digest"] = ids.record_digest(r)
        prev = r["digest"]
        out.append(canon(r) + b"\n")
    path = root / key / "journal.jsonl"
    path.chmod(0o600)
    path.write_bytes(b"".join(out))


def _put(root: Path, key: str, value: Any) -> str:
    d = digest(value)
    p = root / key / "blobs" / d
    if not p.exists():
        p.write_bytes(canon(value))
        p.chmod(0o444)
    return d


def _corrupt(root: Path, key: str) -> Any:
    with pytest.raises(CorruptInvestigation) as exc:
        InvestigationMemory.open(root, key, writable=False)
    return exc.value.cause


def _at(recs: list[dict[str, Any]], kind: str) -> list[int]:
    return [i for i, r in enumerate(recs) if r["kind"] == kind]


def _damage(path: Path, how: str) -> None:
    path.chmod(0o644)
    if how == "missing":
        path.unlink()
    else:
        data = bytearray(path.read_bytes())
        data[len(data) // 2] ^= 0x01
        path.write_bytes(bytes(data))


@pytest.mark.negative
@pytest.mark.parametrize("kind", ["candidate_result_batch_recorded", "lookup_batch_recorded"])
@pytest.mark.parametrize("how", ["missing", "changed bytes"])
def test_missing_or_corrupt_batch_is_corrupt(stored: tuple[Path, str], kind: str, how: str) -> None:
    root, key = stored
    rec = next(r for r in journal(root, key) if r["kind"] == kind)
    _damage(root / key / "blobs" / rec["payload"]["batch"], how)
    cause = _corrupt(root, key)
    assert cause.invariant == "M-3" and cause.code in ("BLOB_MISSING", "BLOB_CORRUPT"), cause


@pytest.mark.negative
def test_wrong_batch_digest_is_corrupt(stored: tuple[Path, str]) -> None:
    root, key = stored
    recs = journal(root, key)
    at = _at(recs, "candidate_result_batch_recorded")
    rec = copy.deepcopy(recs[at[0]])
    rec["payload"]["batch"] = recs[at[1]]["payload"]["batch"]  # another existing candidate batch
    _rewrite(root, key, [*recs[: at[0]], rec, *recs[at[0] + 1 :]])
    cause = _corrupt(root, key)
    assert (cause.invariant, cause.code) == ("M-14", "DUPLICATE_ID"), cause  # recorded twice in the series
    rec["payload"]["batch"] = recs[0]["digest"]  # a digest that names no blob
    _rewrite(root, key, [*recs[: at[0]], rec])
    assert _corrupt(root, key).code == "BLOB_MISSING"
    look = _at(recs, "lookup_batch_recorded")[0]
    rec = copy.deepcopy(recs[look])
    rec["payload"]["batch"] = recs[at[0]]["payload"]["batch"]  # a candidate batch named as a LOOKUP batch
    _rewrite(root, key, [*recs[:look], rec])
    assert (_corrupt(root, key).invariant, _corrupt(root, key).code) == ("M-3", "LOOKUP_BATCH_INVALID")


def _forge_candidate_batch(
    root: Path, key: str, change: Callable[[dict[str, Any]], dict[str, Any]], index: int = 0
) -> list[dict[str, Any]]:
    """Replace candidate batch ``index`` by ``change(batch)`` (published); keep the rest of the journal."""
    recs = journal(root, key)
    at = _at(recs, "candidate_result_batch_recorded")[index]
    old = json.loads((root / key / "blobs" / recs[at]["payload"]["batch"]).read_bytes())
    new = change(copy.deepcopy(old))
    rec = copy.deepcopy(recs[at])
    rec["payload"]["batch"] = _put(root, key, new)
    # An empty entry list keeps entry_count 1 so that the batch blob, not the record schema, is what is refused.
    rec["payload"]["entry_count"] = max(1, len(new["entries"])) if isinstance(new.get("entries"), list) else 1
    out = [*recs[:at], rec, *recs[at + 1 :]]
    _rewrite(root, key, out)
    return out


def _other_entry(root: Path, key: str, index: int) -> dict[str, Any]:
    recs = journal(root, key)
    at = _at(recs, "candidate_result_batch_recorded")[index]
    return json.loads((root / key / "blobs" / recs[at]["payload"]["batch"]).read_bytes())["entries"][0]  # type: ignore[no-any-return]


def _other_claim(e: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(e)
    out["claim"]["claim_id"] = h("another claim id")
    return out


# name -> (change of candidate batch 0, expected (invariant, code))
CANDIDATE_FORGERIES: dict[str, tuple[Callable[[dict[str, Any]], dict[str, Any]], tuple[str, str]]] = {
    "duplicate candidate entry": (
        lambda b: {**b, "entries": [b["entries"][0], b["entries"][0]]},
        ("M-14", "DUPLICATE_ID"),
    ),
    "duplicate claim id": (
        lambda b: {**b, "entries": [b["entries"][0], {**b["entries"][0], "question": None}]},
        ("M-14", "DUPLICATE_ID"),
    ),
    "claim without decision": (
        lambda b: {**b, "entries": [{k: v for k, v in b["entries"][0].items() if k != "decision"}]},
        ("M-3", "CANDIDATE_BATCH_INVALID"),
    ),
    "decision without claim": (
        lambda b: {**b, "entries": [{**b["entries"][0], "claim": None}]},
        ("M-3", "CANDIDATE_BATCH_INVALID"),
    ),
    "decision for another claim": (
        lambda b: {
            **b,
            "entries": [{**b["entries"][0], "decision": {**b["entries"][0]["decision"], "claim_id": h("x")}}],
        },
        ("M-7", "CANDIDATE_ENTRY_INVALID"),
    ),
    "question for another claim": (
        lambda b: {
            **b,
            "entries": [{**b["entries"][0], "question": {**b["entries"][0]["question"], "claim_id": h("x")}}],
        },
        ("M-7", "CANDIDATE_ENTRY_INVALID"),
    ),
    "claim naming a missing evidence set": (
        lambda b: {
            **b,
            "entries": [{**b["entries"][0], "claim": {**b["entries"][0]["claim"], "evidence_set": h("no set")}}],
        },
        ("M-3", "BLOB_MISSING"),
    ),
    "unknown batch version": (lambda b: {**b, "schema_version": "2.0.0"}, ("M-3", "CANDIDATE_BATCH_INVALID")),
    "wrong order label": (lambda b: {**b, "order": "input/1"}, ("M-3", "CANDIDATE_BATCH_INVALID")),
    "empty batch": (lambda b: {**b, "entries": []}, ("M-3", "CANDIDATE_BATCH_INVALID")),
}


@pytest.mark.negative
@pytest.mark.parametrize("name", list(CANDIDATE_FORGERIES))
def test_forged_candidate_batch_is_corrupt(stored: tuple[Path, str], name: str) -> None:
    root, key = stored
    change, expected = CANDIDATE_FORGERIES[name]
    _forge_candidate_batch(root, key, change)  # batch 0 is the IDENTITY_CONFLICT candidate (it has a question)
    cause = _corrupt(root, key)
    assert (cause.invariant, cause.code) == expected, cause


@pytest.mark.negative
def test_duplicate_candidate_across_two_batches_is_corrupt(stored: tuple[Path, str]) -> None:
    """The same candidate result in two batches is a duplicate id (M-14); the same candidate with another claim in a
    second batch is two claims for one candidate (W-8, checked when the controller opens the journal)."""
    root, key = stored
    first = _other_entry(root, key, 0)
    _forge_candidate_batch(root, key, lambda b: {**b, "entries": [first]}, index=1)
    cause = _corrupt(root, key)
    assert (cause.invariant, cause.code) == ("M-14", "DUPLICATE_ID"), cause


@pytest.mark.negative
def test_incorrect_batch_ordering_or_cut_is_corrupt(stored: tuple[Path, str]) -> None:
    root, key = stored
    recs = journal(root, key)
    at = _at(recs, "candidate_result_batch_recorded")
    e0, e1 = _other_entry(root, key, 0), _other_entry(root, key, 1)
    # Swap the batches of entries 0 and 1 (each record keeps its index): the order of the entries is broken.
    swapped = copy.deepcopy(recs)
    swapped[at[0]]["payload"]["batch"], swapped[at[1]]["payload"]["batch"] = (
        recs[at[1]]["payload"]["batch"],
        recs[at[0]]["payload"]["batch"],
    )
    _rewrite(root, key, swapped)
    cause = _corrupt(root, key)
    assert (cause.invariant, cause.code) == ("S-8.9", "BATCH_NOT_CANONICAL"), cause
    # Merge two batches into one (a cut that is not the canonical one under the small ceiling of this fixture).
    merged = batches.candidate_batch([e0, e1])
    rec0 = copy.deepcopy(recs[at[0]])
    rec0["payload"].update(batch=_put(root, key, merged), entry_count=2, batch_total=2)
    rec2 = copy.deepcopy(recs[at[2]])
    rec2["payload"].update(batch_index=1, batch_total=2)
    _rewrite(root, key, [*recs[: at[0]], rec0, rec2, *recs[at[2] + 1 :]])
    cause = _corrupt(root, key)
    assert (cause.invariant, cause.code) == ("S-8.9", "BATCH_NOT_CANONICAL"), cause


@pytest.mark.negative
@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("entry_count", 7, ("M-3", "CANDIDATE_BATCH_INVALID")),
        ("batch_index", 1, ("S-8.9", "BATCH_SEQUENCE")),
        ("batch_total", 1, ("S-8.9", "BATCH_SEQUENCE")),
        ("batch_total", 4, ("S-8.9", "BATCH_SEQUENCE")),  # the series ends short at step_succeeded
    ],
)
def test_incorrect_batch_count_or_index_is_corrupt(
    stored: tuple[Path, str], field: str, value: int, expected: tuple[str, str]
) -> None:
    root, key = stored
    recs = journal(root, key)
    at = _at(recs, "candidate_result_batch_recorded")
    out = copy.deepcopy(recs)
    for i in at if field == "batch_total" else at[:1]:
        out[i]["payload"][field] = value
    _rewrite(root, key, out)
    cause = _corrupt(root, key)
    assert (cause.invariant, cause.code) == expected, cause


@pytest.mark.negative
def test_lookup_batch_naming_a_missing_observation_blob_is_corrupt(stored: tuple[Path, str]) -> None:
    root, key = stored
    recs = journal(root, key)
    at = _at(recs, "lookup_batch_recorded")[0]
    old = json.loads((root / key / "blobs" / recs[at]["payload"]["batch"]).read_bytes())
    old["entries"][0]["blob"] = h("no lookup blob")
    old["entries"].sort(key=batches.lookup_key)
    rec = copy.deepcopy(recs[at])
    rec["payload"]["batch"] = _put(root, key, old)
    _rewrite(root, key, [*recs[:at], rec])
    cause = _corrupt(root, key)
    assert (cause.invariant, cause.code) == ("M-3", "BLOB_MISSING"), cause


# Process death at the listed points, deterministic resume -----------------------------------------------------------


def _is_candidate_batch(data: bytes) -> bool:
    return b"urn:citerift:schema:investigation:v1:candidate-result-batch" in data


CRASH_POINTS: dict[str, tuple[str, Callable[[dict[str, Any], dict[str, Any]], bool], int]] = {
    "during the candidate batch blob write": ("blob.during_write", lambda c, s: _is_candidate_batch(c["data"]), 1),
    "after publication, before the batch record": ("controller.after_blobs", lambda c, s: c["step"] == "DETECT", 1),
    "between candidate batch records": (
        "controller.after_entry_batch",
        lambda c, s: c["step"] == "DETECT" and c["index"] == 0,
        1,
    ),
    "after all candidate batch records, before success": (
        "controller.after_entry_batch",
        lambda c, s: c["step"] == "DETECT" and c["index"] == 2,
        1,
    ),
    "between LOOKUP batch records": (
        "controller.after_entry_batch",
        lambda c, s: c["step"] == "LOOKUP" and c["index"] == 0,
        1,
    ),
}


def _plan() -> Plan:
    return Plan({("LOOKUP", 1): _lookup(3), ("LOOKUP", 2): _lookup(3)}, classes=CLASSES)


def _logical(root: Path, key: str) -> tuple[str, list[Any], str]:
    f = _view(root, key)
    content = [[r["kind"], r["step"], r["payload"]] for r in f.committed_content()]
    return f.content_digest(), content, f.lifecycle()


def _crash(root: Path, key: str, clock: StepClock, point: str, pred: Any, occurrence: int) -> int:
    pid = os.fork()
    if pid == 0:  # child: dies at the point, never returns
        code = 1
        try:
            state: dict[str, Any] = {"seen": 0}

            def handler(name: str, ctx: dict[str, Any]) -> None:
                if name == point and pred(ctx, state):
                    state["seen"] += 1
                    if state["seen"] == occurrence:
                        os._exit(CRASH)

            faults.install(handler)
            run_once(root, key, _plan(), Env(), clock)
            code = 0
        except BaseException:
            code = 2
        finally:
            os._exit(code)
    _, status = os.waitpid(pid, 0)
    return os.waitstatus_to_exitcode(status)


@pytest.mark.simulation
@pytest.mark.usefixtures("small_ceiling")
@pytest.mark.parametrize("name", list(CRASH_POINTS))
def test_process_death_at_every_listed_point(tmp_path: Path, name: str) -> None:
    ref_dir = tmp_path / "reference"
    ref_dir.mkdir()
    clock = StepClock()
    ref_root, ref_key = create(ref_dir, clock=clock)
    assert run_once(ref_root, ref_key, _plan(), Env(), clock).lifecycle == "NEEDS_RESOLUTION"
    reference = _logical(ref_root, ref_key)
    point, pred, occurrence = CRASH_POINTS[name]
    clock = StepClock()
    root, key = create(_fresh(tmp_path), clock=clock)
    assert _crash(root, key, clock, point, pred, occurrence) == CRASH, name
    before = journal(root, key)
    f = _view(root, key)
    succeeded = {r["step"] for r in before if r["kind"] == "step_succeeded"}
    # No false committed content: claims only from a succeeded DETECT, lookups only from a succeeded LOOKUP.
    steps_committed = {r["step"] for r in f.committed_content()}
    assert steps_committed <= succeeded, name
    if "DETECT" not in succeeded:
        assert f.committed.claims == {} and f.committed.decisions == {}, name
    plan = _plan()
    st = run_once(root, key, plan, Env(), StepClock(T0 + timedelta(days=1)))
    after = journal(root, key)
    assert after[: len(before)] == before and st.lifecycle == reference[2], name
    assert not {s for s, _ in plan.calls} & succeeded, name  # succeeded steps never run again
    assert Counter(r["step"] for r in after if r["kind"] == "step_succeeded") == dict.fromkeys(STEPS, 1), name
    assert _logical(root, key) == reference, name  # deterministic replay: same logical content, same C(J)


def _fresh(tmp_path: Path) -> Path:
    d = tmp_path / "crash"
    d.mkdir()
    return d


# Ceiling (owner D-055: the D-053 primitive and ceiling, re-checked with the LOOKUP and DETECT entries) ----------------

D055 = Path(__file__).resolve().parents[2] / "docs" / "verification" / "stage-04" / "review" / "step7" / "d055"


@pytest.mark.contracts
def test_ceiling_still_holds_with_lookup_and_candidate_entries() -> None:
    record = json.loads((D055 / "part_ceiling.json").read_text(encoding="utf-8"))
    assert record["selected_bytes"] == batches.MAX_PART_BYTES == record["d053_selected_bytes"]
    assert record["changed_from_d053"] is False
    lower = record["rule_1_largest_entry"]["lower_bound_bytes"]
    assert lower <= batches.MAX_PART_BYTES <= MAX_BLOB_BYTES
    rule5 = record["rule_5_record_count"]
    assert rule5["batch_record_bytes_at_selected"] <= rule5["budget_bytes"]
    # The largest legal entries, rebuilt here: a batch of one alone is within the lower bound.
    lookup = {
        "obs_kind": "lookup",
        "blob": h("b"),
        "source_ref": {"engine": "citerift.retraction", "operation": "gather", "locator": "\x01" * 4096},
    }
    assert len(canon(batches.lookup_batch([lookup]))) <= lower
    assert record["rule_1_largest_entry"]["lookup_reference_max"] == batches.item_bytes(lookup)


# Scientific invariance (owner D-055): the logical content equals the accepted baseline's ---------------------------

# Logical-view digests of docs/verification/stage-04/review/step7/d055/equivalence.py run on the accepted baseline
# 0097a9329d728e8260d48dc79a53a6be5f9c4fa9 (journal format 3), retained in d055/equivalence_0097a93.json.
BASELINE_RUN = json.loads((D055 / "equivalence_0097a93.json").read_text(encoding="utf-8"))
BASELINE_0097A93 = {name: s["digest"] for name, s in BASELINE_RUN["scenarios"].items()}


@pytest.mark.reproducibility
def test_the_baseline_run_is_the_accepted_format_3_tree() -> None:
    assert BASELINE_RUN["tree_head"] == "0097a9329d728e8260d48dc79a53a6be5f9c4fa9"
    assert BASELINE_RUN["journal_format"] == 3 and BASELINE_RUN["tree_dirty"] is False
    assert len(BASELINE_0097A93) == 8


@pytest.mark.reproducibility
@pytest.mark.parametrize("name", list(BASELINE_0097A93))
def test_logical_content_equals_the_format_3_baseline(name: str) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("d055_equivalence", D055 / "equivalence.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    got = module.logical_view(name)
    # Step 8 (IF-7) replaced the SYNTHETIC bundle observation; everything else equals the baseline.
    assert with_legacy_bundle(got["view"], module._canon) == BASELINE_0097A93[name], got["counts"]


# The journal bound of format 4 is executable and retained (owner D-055) --------------------------------------------


@pytest.mark.contracts
def test_format_4_bounds_are_recomputed_and_proven() -> None:
    """Recompute ``d055/bounds.py`` from the format-4 records as implemented and compare with the retained
    ``bounds.json``: every record kind within 1 MiB, the worst-case journal of a run at the Stage 03 caps within 512 MiB
    with substantial headroom, and every blob kind except the ACQUIRE observation (IF-7, a Step 8 condition) within
    256 MiB."""
    import importlib.util

    from citerift.investigation.journal import JOURNAL_FORMAT, MAX_JOURNAL_BYTES, MAX_RECORD_BYTES

    spec = importlib.util.spec_from_file_location("d055_bounds", D055 / "bounds.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    kinds = module.record_kinds()
    journal_bound = module.journal(kinds, module.entry_sizes())
    retained = json.loads((D055 / "bounds.json").read_text(encoding="utf-8"))
    assert retained["journal_format"] == JOURNAL_FORMAT == 4
    assert {k: v["bytes"] for k, v in kinds.items()} == {
        k: v["bytes"] for k, v in retained["record_kinds_max_bytes"].items()
    }
    assert max(v["bytes"] for v in kinds.values()) <= MAX_RECORD_BYTES
    assert journal_bound["maximal"]["journal_bytes"] == retained["journal"]["maximal"]["journal_bytes"]
    assert journal_bound["maximal"]["journal_bytes"] * 20 <= MAX_JOURNAL_BYTES  # at least 20x headroom
    assert retained["journal_limit_proven"] and retained["record_limit_proven"]
    assert retained["blob_limit_proven_except_ACQUIRE_observation"]
