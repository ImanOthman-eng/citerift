"""Owner decisions D-053 (evidence committed in content-addressed batches) and D-054 (the report as a manifest graph).

Owner items covered here: the deterministic order (input-order independence, references across batch boundaries,
cycle, missing reference), the byte ceiling (N - 1 / N / N + 1, one legal item always fits, the derived constant),
commit discipline (batches of an attempt that did not succeed are not authoritative), process death at every point
the owner listed (with deterministic resume, no false or missing committed evidence, harmless orphans and an equal
content digest), and every corruption the owner listed (all fail closed). SYNTHETIC fake adapters.

Most tests here lower ``MAX_PART_BYTES`` (fixture ``small_ceiling``) so that a few synthetic items make several
batches and chunks; the rules do not depend on the value.
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
    EXTRACTION,
    T0,
    Env,
    Plan,
    StepClock,
    create,
    digest,
    evidence,
    evidence_items,
    journal,
    ok_result,
    run_once,
)
from memory_support import append_evidence, drive, h, new_memory, with_legacy_bundle

from citerift.investigation import batches, faults, ids, report
from citerift.investigation.adapters import ContentRecord, StepRequest, StepResult, Succeeded
from citerift.investigation.blobs import MAX_BLOB_BYTES
from citerift.investigation.canonical import canon
from citerift.investigation.errors import AppendRefused, CorruptInvestigation
from citerift.investigation.memory import InvestigationMemory

ROOT = Path(__file__).resolve().parents[2]
CEILING_RECORD = ROOT / "docs" / "verification" / "stage-04" / "review" / "step7" / "d053" / "part_ceiling.json"
SMALL = 700  # bytes: a unit and an identifier occurrence, or two lookup results, per batch
CLASSES = (("NOT_FOUND_IN_CHECKED_SOURCES", "c1"), ("RETRACTED_WORK_CITED", "c2"))
CRASH = 77


@pytest.fixture
def small_ceiling(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(batches, "MAX_PART_BYTES", SMALL)
    yield


def _dag(obs: str = h("obs")) -> list[dict[str, Any]]:
    """Five units, an occurrence per unit (ref the unit), a candidate per occurrence (ref the occurrence)."""
    units = [evidence("unit", obs, f"/units/{i}", [], {"source_artifact": h("src"), "unit_span_sha256": h(f"s{i}")})
             for i in range(5)]  # fmt: skip
    occ = [evidence("identifier_occurrence", obs, f"/units/{i}/identifiers/0", [u["evidence_id"]],
                    {"status": "CONFIRMED", "key": {"scheme": "doi", "normalized": f"10.1000/x{i}"}})
           for i, u in enumerate(units)]  # fmt: skip
    cand = [evidence("work_candidate", obs, f"/candidates/{i}", [o["evidence_id"]],
                     {"shape": "DOI", "keys": [o["value"]["key"]], "coherence": None})
            for i, o in enumerate(occ)]  # fmt: skip
    return [*units, *occ, *cand]


def _flat(found: list[dict[str, Any]]) -> list[str]:
    return [i["evidence_id"] for b in found for i in b["items"]]


# Order (SPEC 8.8) ---------------------------------------------------------------------------------------------------


@pytest.mark.unit
def test_order_does_not_depend_on_the_input_order() -> None:
    items = _dag()
    first = batches.evidence_batches(items, lambda r: False, 900)
    assert len(first) > 2
    rnd = random.Random(53)
    for _ in range(50):
        shuffled = copy.deepcopy(items)
        rnd.shuffle(shuffled)
        again = batches.evidence_batches(shuffled, lambda r: False, 900)
        assert [digest(b) for b in again] == [digest(b) for b in first]


@pytest.mark.unit
def test_every_reference_precedes_its_item_also_across_batch_boundaries() -> None:
    found = batches.evidence_batches(_dag(), lambda r: False, 900)
    where = {i["evidence_id"]: (n, k) for n, b in enumerate(found) for k, i in enumerate(b["items"])}
    crossing = 0
    for b in found:
        for i in b["items"]:
            for r in i["refs"]:
                assert where[r] < where[i["evidence_id"]]
                crossing += where[r][0] < where[i["evidence_id"]][0]
    assert crossing > 0  # at least one reference names an item of an earlier batch


@pytest.mark.unit
def test_ready_items_come_in_evidence_id_order() -> None:
    items = [evidence("lookup_result", h("obs"), f"/r/{i}", [], None) for i in range(30)]
    assert _flat(batches.evidence_batches(items, lambda r: False)) == sorted(i["evidence_id"] for i in items)
    # A reference outranks the tie-break: an item comes after what it names even if its id is smaller.
    a, b = sorted(items[:2], key=lambda i: i["evidence_id"])
    child = {**a, "refs": [b["evidence_id"]]}
    assert _flat(batches.evidence_batches([child, b], lambda r: False)) == [b["evidence_id"], a["evidence_id"]]


@pytest.mark.negative
def test_cycle_missing_reference_and_duplicate_are_refused() -> None:
    obs = h("obs")
    a = evidence("unit", obs, "/a", [], None)
    b = evidence("unit", obs, "/b", [a["evidence_id"]], None)
    a["refs"] = [b["evidence_id"]]
    with pytest.raises(batches.BatchError) as exc:
        batches.evidence_batches([a, b], lambda r: False)
    assert exc.value.code == "DEPENDENCY_CYCLE"
    selfloop = evidence("unit", obs, "/s", [], None)
    selfloop["refs"] = [selfloop["evidence_id"]]
    with pytest.raises(batches.BatchError) as exc:
        batches.evidence_batches([selfloop], lambda r: False)
    assert exc.value.code == "DEPENDENCY_CYCLE"
    orphan = evidence("unit", obs, "/o", [h("nowhere")], None)
    with pytest.raises(batches.BatchError) as exc:
        batches.evidence_batches([orphan], lambda r: False)
    assert exc.value.code == "DANGLING_REFERENCE"
    assert batches.evidence_batches([orphan], lambda r: r == h("nowhere"))  # defined earlier: accepted
    with pytest.raises(batches.BatchError) as exc:
        batches.evidence_batches([orphan, dict(orphan)], lambda r: True)
    assert exc.value.code == "DUPLICATE_ID"


# The byte ceiling ---------------------------------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize("k", [1, 2, 7])
def test_boundaries_at_n_minus_one_n_and_n_plus_one(k: int) -> None:
    s, e = 50, 40
    n = e + k * s + (k - 1)  # a part of exactly k items
    sizes = [s] * (k + 1)

    def groups(total: int, per: int) -> list[int]:  # greedy parts of at most ``per`` items (at least one)
        per = max(per, 1)
        return [per] * (total // per) + ([total % per] if total % per else [])

    assert batches.boundaries(sizes, e, n - 1) == groups(k + 1, k - 1)  # N - 1: k items no longer fit
    assert batches.boundaries(sizes, e, n) == [k, 1]  # N: exactly k fit
    assert batches.boundaries(sizes, e, n + 1) == [k, 1]  # N + 1: still k, the next needs s + 1 more
    assert batches.boundaries(sizes[:k], e, n) == [k]
    assert batches.boundaries(sizes[:k], e, n - 1) == groups(k, k - 1)
    # Real items: every batch is within the ceiling and the next item would not have fitted.
    items = _dag()
    for limit in (n - 1, n, n + 1, 1000, 1001):
        found = batches.evidence_batches(items, lambda r: False, limit)
        for this, nxt in zip(found, [*found[1:], None], strict=True):
            size = len(canon(this))
            assert size <= limit or len(this["items"]) == 1
            if nxt is not None:
                assert size + 1 + batches.item_bytes(nxt["items"][0]) > limit


@pytest.mark.unit
def test_an_item_larger_than_the_ceiling_forms_its_own_part() -> None:
    assert batches.boundaries([10, 1000, 10, 10], 40, 100) == [1, 1, 2]
    assert batches.boundaries([], 40, 100) == []


@pytest.mark.contracts
def test_ceiling_is_the_derived_one_and_one_legal_item_always_fits() -> None:
    record = json.loads(CEILING_RECORD.read_text(encoding="utf-8"))
    assert record["selected_bytes"] == batches.MAX_PART_BYTES
    lower = record["rule_1_largest_item"]["lower_bound_bytes"]
    assert lower <= batches.MAX_PART_BYTES <= MAX_BLOB_BYTES
    assert (
        record["rule_5_record_count"]["batch_record_bytes_at_selected"] <= record["rule_5_record_count"]["budget_bytes"]
    )
    # The largest legal item, rebuilt here: a batch of it alone is within the ceiling.
    big = evidence("work_candidate", h("o"), "/" + "\x01" * 4095, [h(str(i)) for i in range(8)],
                   {"shape": "PAIR", "keys": [{"scheme": "doi", "normalized": "10.1234/" + "\U0001f600" * 504},
                                              {"scheme": "pmid", "normalized": "999999999"}],
                    "coherence": "UNDETERMINED"})  # fmt: skip
    assert len(canon(batches.evidence_batch([big]))) <= lower <= batches.MAX_PART_BYTES


# Investigation Memory and the controller ------------------------------------------------------------------------------


def _run(tmp: Path, script: dict[tuple[str, int], Any] | None = None, classes: Any = CLASSES) -> tuple[Path, str, Any]:
    clock = StepClock()
    root, key = create(tmp, clock=clock)
    return root, key, run_once(root, key, Plan(script, classes=classes), Env(), clock)


def _batch_records(root: Path, key: str, step: str | None = None) -> list[dict[str, Any]]:
    return [r for r in journal(root, key) if r["kind"] == "evidence_batch_recorded" and step in (None, r["step"])]


@pytest.mark.integration
@pytest.mark.usefixtures("small_ceiling")
def test_batches_with_references_across_boundaries_commit_and_reopen(tmp_path: Path) -> None:
    root, key, st = _run(tmp_path)
    assert st.lifecycle == "COMPLETED"
    for step in ("NORMALIZE", "DETECT"):
        recs = _batch_records(root, key, step)
        assert len(recs) >= 2
        assert [r["payload"]["batch_index"] for r in recs] == list(range(len(recs)))
        assert {r["payload"]["batch_total"] for r in recs} == {len(recs)}
    items = evidence_items(root, key)
    unit = next(i for i in items if i["kind"] == "unit")
    occ = next(i for i in items if i["kind"] == "identifier_occurrence")
    assert occ["refs"] == [unit["evidence_id"]]
    with InvestigationMemory.open(root, key, writable=False) as mem:  # the occurrence's ref crosses a boundary
        assert mem.view.evidence_batch(unit["evidence_id"]) != mem.view.evidence_batch(occ["evidence_id"])


def _normalize_with(items: Callable[[str], list[dict[str, Any]]]) -> Callable[[StepRequest], StepResult]:
    def normalize(req: StepRequest) -> StepResult:
        out = {"normalized": "SYNTHETIC"}
        recs = tuple(ContentRecord("evidence", i) for i in items(digest(EXTRACTION)))
        return Succeeded(records=recs, blobs=(out,), outputs=(digest(out),))

    return normalize


def _cyclic(obs: str) -> list[dict[str, Any]]:
    a = evidence("unit", obs, "/units/0", [], {"source_artifact": h("src"), "unit_span_sha256": h("span")})
    b = evidence("identifier_occurrence", obs, "/units/0/identifiers/0", [a["evidence_id"]],
                 {"status": "CONFIRMED", "key": {"scheme": "doi", "normalized": "10.1000/xyz"}})  # fmt: skip
    a["refs"] = [b["evidence_id"]]
    return [a, b]


def _dangling(obs: str) -> list[dict[str, Any]]:
    return [
        evidence("unit", obs, "/units/0", [h("nowhere")], {"source_artifact": h("src"), "unit_span_sha256": h("s")})
    ]


@pytest.mark.negative
@pytest.mark.parametrize("items", [_cyclic, _dangling], ids=["cycle", "dangling"])
def test_controller_refuses_evidence_it_cannot_order(tmp_path: Path, items: Any) -> None:
    root, key, st = _run(tmp_path, {("NORMALIZE", 1): _normalize_with(items)})
    assert st.lifecycle == "FAILED"
    fail = next(r for r in journal(root, key) if r["kind"] == "step_failed")
    assert fail["payload"]["code"] == "ADAPTER_INCONSISTENT" and "batched" in fail["payload"]["detail"]
    assert _batch_records(root, key) == []  # nothing of the attempt was written


def _memory_until_normalize(tmp: Path) -> tuple[InvestigationMemory, Path, str]:
    mem, root = new_memory(tmp)
    drive(mem, ("VALIDATE", "ACQUIRE", "EXTRACT"))
    obs = mem.put_blob({"units": [{"id": "un-00001"}], "ratio": 0.5})  # the EXTRACT observation (same bytes)
    mem.append("step_started", {"step_key": h("NORMALIZE")}, step="NORMALIZE", attempt=1)
    return mem, root, obs


def _succeed_normalize(mem: InvestigationMemory, attempt: int = 1) -> None:
    out = mem.put_blob({"normalized": "SYNTHETIC"})
    mem.append("step_succeeded", {"step_key": h("NORMALIZE"), "outputs": [out], "root": None}, step="NORMALIZE",
               attempt=attempt)  # fmt: skip


def _raw_batches(mem: InvestigationMemory, groups: list[list[dict[str, Any]]], attempt: int = 1) -> None:
    """Publish and record ``groups`` as the attempt's batches exactly as given (no ordering, no cut)."""
    found = [batches.evidence_batch(g) for g in groups]
    digests = [mem.put_blob(b) for b in found]
    for p in batches.batch_records(digests, found):
        mem.append("evidence_batch_recorded", p, step="NORMALIZE", attempt=attempt)


@pytest.mark.negative
@pytest.mark.usefixtures("small_ceiling")
def test_non_canonical_order_or_cut_is_refused_at_success(tmp_path: Path) -> None:
    for name, cut in (
        ("one batch over the ceiling", lambda items: [items]),
        ("canonical items, another cut", lambda items: [items[:1], items[1:]]),
        ("reversed order of ready items", lambda items: [list(reversed(items))[:1], list(reversed(items))[1:]]),
    ):
        base = tmp_path / name.replace(" ", "-")
        base.mkdir()
        mem, _, obs = _memory_until_normalize(base)
        items = _flat_items(batches.evidence_batches(_independent(obs, 4), lambda r: False))
        groups = cut(items)
        if name == "canonical items, another cut":
            assert [len(g) for g in groups] != batches.boundaries(
                [batches.item_bytes(i) for i in items], batches.BATCH_ENVELOPE
            )
        _raw_batches(mem, groups)
        with pytest.raises(AppendRefused) as exc:
            _succeed_normalize(mem)
        assert (exc.value.invariant, exc.value.code) == ("S-8.8", "BATCH_NOT_CANONICAL"), name
        mem.close()


def _independent(obs: str, n: int) -> list[dict[str, Any]]:
    return [evidence("unit", obs, f"/units/{i}", [], {"source_artifact": h("src"), "unit_span_sha256": h(f"{i}")})
            for i in range(n)]  # fmt: skip


def _flat_items(found: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [i for b in found for i in b["items"]]


@pytest.mark.negative
def test_non_canonical_batches_in_a_stored_journal_are_corrupt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Batches cut under another ceiling commit under that ceiling, and the journal is CORRUPT under this one."""
    monkeypatch.setattr(batches, "MAX_PART_BYTES", 100_000)
    mem, root, obs = _memory_until_normalize(tmp_path)
    append_evidence(mem, _independent(obs, 6), "NORMALIZE", 1)
    _succeed_normalize(mem)
    key = mem.key
    mem.close()
    monkeypatch.setattr(batches, "MAX_PART_BYTES", SMALL)
    with pytest.raises(CorruptInvestigation) as exc:
        InvestigationMemory.open(root, key, writable=False)
    assert (exc.value.cause.invariant, exc.value.cause.code) == ("S-8.8", "BATCH_NOT_CANONICAL")


@pytest.mark.integration
@pytest.mark.usefixtures("small_ceiling")
def test_batches_of_an_attempt_that_did_not_succeed_are_not_authoritative(tmp_path: Path) -> None:
    mem, root, obs = _memory_until_normalize(tmp_path)
    items = _independent(obs, 4)
    found = batches.evidence_batches(items, lambda r: False)
    assert len(found) >= 2
    first = [mem.put_blob(b) for b in found]
    mem.append("evidence_batch_recorded", batches.batch_records(first, found)[0], step="NORMALIZE", attempt=1)
    assert mem.view.committed.evidence == {}  # open attempt: defined for its own checks, not committed
    in_first = [i["evidence_id"] for i in found[0]["items"]]
    assert all(mem.view.evidence_batch(e) == first[0] for e in in_first)
    with pytest.raises(AppendRefused) as exc:  # an incomplete series cannot succeed
        _succeed_normalize(mem)
    assert (exc.value.invariant, exc.value.code) == ("S-8.8", "BATCH_SEQUENCE")
    mem.append("step_interrupted", {"step_key": h("NORMALIZE")}, step="NORMALIZE", attempt=1)
    assert mem.view.committed.evidence == {} and all(mem.view.evidence_batch(e) is None for e in in_first)
    # Attempt 2 records the same batches again (same content, same digests) and only its success commits them.
    mem.append("step_started", {"step_key": h("NORMALIZE")}, step="NORMALIZE", attempt=2)
    append_evidence(mem, items, "NORMALIZE", 2)
    _succeed_normalize(mem, 2)
    assert set(mem.view.committed.evidence) == {i["evidence_id"] for i in items}
    assert mem.view.committed.batches == first
    key = mem.key
    mem.close()
    with InvestigationMemory.open(root, key, writable=False) as again:
        assert set(again.view.committed.evidence) == {i["evidence_id"] for i in items}


# Process death (owner D-053 crash list) ----------------------------------------------------------------------------


def _is_batch(data: bytes) -> bool:
    return b"urn:citerift:schema:investigation:v1:evidence-batch" in data


def _is_claim_chunk(data: bytes) -> bool:
    return b"urn:citerift:schema:investigation:v1:report-chunk" in data and b'"part":"claims"' in data


def _is_manifest(data: bytes) -> bool:
    return b'"components":' in data


# name -> (fault point, predicate on (context, state), occurrence)
CRASH_POINTS: dict[str, tuple[str, Callable[[dict[str, Any], dict[str, Any]], bool], int]] = {
    "before batch blob creation": ("controller.after_adapter", lambda c, s: c["step"] == "NORMALIZE", 1),
    "during the batch blob write": ("blob.during_write", lambda c, s: _is_batch(c["data"]), 1),
    "after fsync, before publication": ("blob.after_fsync", lambda c, s: _is_batch(s["data"]), 1),
    "after publication, before the record": ("controller.after_blobs", lambda c, s: c["step"] == "NORMALIZE", 1),
    "between batch records": ("controller.after_batch", lambda c, s: c["step"] == "NORMALIZE" and c["index"] == 0, 1),
    "after all batch records, before success": ("controller.after_batch", lambda c, s: c["step"] == "DETECT", 2),
    "during the batch record append": (
        "journal.during_append",
        lambda c, s: b"evidence_batch_recorded" in c["data"],
        2,
    ),
    "during claim-chunk creation": ("blob.during_write", lambda c, s: _is_claim_chunk(c["data"]), 2),
    "during manifest creation": ("blob.during_write", lambda c, s: _is_manifest(c["data"]), 1),
}


def _content(root: Path, key: str) -> tuple[str, set[str], str]:
    with InvestigationMemory.open(root, key, writable=False) as mem:
        f = mem.view
        return f.content_digest(), set(f.committed.evidence), f.lifecycle()


class Reference:
    def __init__(self, base: Path) -> None:
        clock = StepClock()
        root, key = create(base, clock=clock)
        st = run_once(root, key, Plan(classes=CLASSES), Env(), clock)
        assert st.lifecycle == "COMPLETED"
        self.digest, self.evidence, self.lifecycle = _content(root, key)
        self.batches = {s: len(_batch_records(root, key, s)) for s in ("NORMALIZE", "DETECT")}
        self.blobs = set(os.listdir(root / key / "blobs"))


@pytest.fixture
def reference(tmp_path: Path, small_ceiling: None) -> Reference:
    d = tmp_path / "reference"
    d.mkdir()
    return Reference(d)


def _crash(root: Path, key: str, clock: StepClock, point: str, pred: Any, occurrence: int) -> int:
    pid = os.fork()
    if pid == 0:  # child: dies at the point, never returns
        code = 1
        try:
            state: dict[str, Any] = {"data": b"", "seen": 0}

            def handler(name: str, ctx: dict[str, Any]) -> None:
                if name == "blob.before_write":
                    state["data"] = ctx["data"]
                if name == point and pred(ctx, state):
                    state["seen"] += 1
                    if state["seen"] == occurrence:
                        os._exit(CRASH)

            faults.install(handler)
            run_once(root, key, Plan(classes=CLASSES), Env(), clock)
            code = 0
        except BaseException:
            code = 2
        finally:
            os._exit(code)
    _, status = os.waitpid(pid, 0)
    return os.waitstatus_to_exitcode(status)


@pytest.mark.simulation
@pytest.mark.parametrize("name", list(CRASH_POINTS))
def test_process_death_at_every_listed_point(reference: Reference, tmp_path: Path, name: str) -> None:
    assert reference.batches["NORMALIZE"] == 2 and reference.batches["DETECT"] == 2  # the occurrences above
    point, pred, occurrence = CRASH_POINTS[name]
    clock = StepClock()
    root, key = create(tmp_path, clock=clock)
    assert _crash(root, key, clock, point, pred, occurrence) == CRASH, name
    before = journal(root, key)  # reopens (a torn tail is preserved, never CORRUPT)
    _, committed, _ = _content(root, key)
    succeeded = {r["step"] for r in before if r["kind"] == "step_succeeded"}
    # No false committed evidence: only the evidence of succeeded steps is committed, and none of it is missing.
    expected = set()
    with InvestigationMemory.open(root, key, writable=False) as mem:
        for r in mem.view.records:
            if r["kind"] == "evidence_batch_recorded" and r["step"] in succeeded:
                expected |= {i["evidence_id"] for i in mem.view.blob_read(r["payload"]["batch"])["items"]}
    assert committed == expected and committed <= reference.evidence, name
    plan = Plan(classes=CLASSES)
    st = run_once(root, key, plan, Env(), StepClock(T0 + timedelta(days=1)))
    after = journal(root, key)
    assert after[: len(before)] == before and st.lifecycle == reference.lifecycle, name
    assert not {s for s, _ in plan.calls} & succeeded, name  # succeeded steps never run again
    assert Counter(r["step"] for r in after if r["kind"] == "step_succeeded") == Counter(
        {s: 1 for s in ("VALIDATE", "ACQUIRE", "EXTRACT", "NORMALIZE", "LOOKUP", "DETECT", "ASSEMBLE", "VERIFY")}
    ), name
    digest_after, committed_after, _ = _content(root, key)
    assert committed_after == reference.evidence, name  # nothing missing after the resume
    assert digest_after == reference.digest, name  # replay gives the same content digest
    assert set(os.listdir(root / key / "blobs")) >= reference.blobs  # orphans, if any, are harmless extras


# Corruption (owner D-053 and D-054 lists): every case fails closed --------------------------------------------------


@pytest.fixture
def stored(tmp_path: Path, small_ceiling: None) -> tuple[Path, str]:
    root, key, st = _run(tmp_path)
    assert st.lifecycle == "COMPLETED"
    return root, key


def _rewrite(root: Path, key: str, records: list[dict[str, Any]]) -> None:
    out, prev = [], ids.genesis(key)
    for original in records:
        r = copy.deepcopy(original)
        r["prev"] = prev
        r["digest"] = ids.record_digest(r)
        prev = r["digest"]
        out.append(canon(r) + b"\n")
    path = root / key / "journal.jsonl"
    path.chmod(0o600)
    path.write_bytes(b"".join(out))


def _put(root: Path, key: str, value: Any) -> str:
    data = canon(value, allow_float=True)
    d = digest(value)
    p = root / key / "blobs" / d
    if not p.exists():
        p.write_bytes(data)
        p.chmod(0o444)
    return d


def _corrupt(root: Path, key: str) -> Any:
    with pytest.raises(CorruptInvestigation) as exc:
        InvestigationMemory.open(root, key, writable=False)
    return exc.value.cause


def _blob_path(root: Path, key: str, d: str) -> Path:
    return root / key / "blobs" / d


def _damage(path: Path, how: str) -> None:
    path.chmod(0o644)
    if how == "missing":
        path.unlink()
    else:
        data = bytearray(path.read_bytes())
        data[len(data) // 2] ^= 0x01
        path.write_bytes(bytes(data))


def _forge_batch(root: Path, key: str, change: Callable[[dict[str, Any]], dict[str, Any]]) -> None:
    """Replace the first NORMALIZE batch by ``change(batch)`` (published), cut the journal after its record."""
    recs = journal(root, key)
    at = next(i for i, r in enumerate(recs) if r["kind"] == "evidence_batch_recorded")
    old = json.loads(_blob_path(root, key, recs[at]["payload"]["batch"]).read_bytes())
    new = change(copy.deepcopy(old))
    rec = copy.deepcopy(recs[at])
    rec["payload"]["batch"] = _put(root, key, new)
    rec["payload"]["evidence_count"] = len(new["items"]) if isinstance(new.get("items"), list) else 1
    _rewrite(root, key, [*recs[:at], rec])


@pytest.mark.negative
@pytest.mark.parametrize("how", ["missing", "changed bytes"])
def test_batch_missing_or_changed_is_corrupt(stored: tuple[Path, str], how: str) -> None:
    root, key = stored
    rec = next(r for r in journal(root, key) if r["kind"] == "evidence_batch_recorded")
    _damage(_blob_path(root, key, rec["payload"]["batch"]), how)
    cause = _corrupt(root, key)
    assert cause.invariant == "M-3" and cause.code in ("BLOB_MISSING", "BLOB_CORRUPT"), cause


@pytest.mark.negative
def test_wrong_batch_digest_is_corrupt(stored: tuple[Path, str]) -> None:
    root, key = stored
    recs = journal(root, key)
    at = [i for i, r in enumerate(recs) if r["kind"] == "evidence_batch_recorded"]
    rec = copy.deepcopy(recs[at[0]])
    rec["payload"]["batch"] = recs[at[1]]["payload"]["batch"]  # another existing batch
    _rewrite(root, key, [*recs[: at[0]], rec])
    cause = _corrupt(root, key)
    assert cause.invariant in ("M-4", "M-3"), cause  # its occurrence names a unit not defined before it
    rec["payload"]["batch"] = recs[0]["digest"]  # a digest that names no blob
    _rewrite(root, key, [*recs[: at[0]], rec])
    assert _corrupt(root, key).code == "BLOB_MISSING"


BATCH_FORGERIES: dict[str, tuple[Callable[[dict[str, Any]], dict[str, Any]], tuple[str, str]]] = {
    "invalid item": (
        lambda b: {**b, "items": [{**b["items"][0], "kind": "not_a_kind"}]},
        ("M-3", "EVIDENCE_BATCH_INVALID"),
    ),
    "duplicate id": (lambda b: {**b, "items": [b["items"][0], b["items"][0]]}, ("M-14", "DUPLICATE_ID")),
    "cycle": (
        lambda b: {**b, "items": [{**b["items"][0], "refs": [b["items"][0]["evidence_id"]]}]},
        ("M-4", "DANGLING_REFERENCE"),
    ),
    "dangling reference": (
        lambda b: {**b, "items": [{**b["items"][0], "refs": [h("nowhere")]}]},
        ("M-4", "DANGLING_REFERENCE"),
    ),
    "id not derived": (
        lambda b: {**b, "items": [{**b["items"][0], "evidence_id": h("forged")}]},
        ("CH-1", "EVIDENCE_ID_INVALID"),
    ),
    "unknown batch version": (lambda b: {**b, "schema_version": "2.0.0"}, ("M-3", "EVIDENCE_BATCH_INVALID")),
    "wrong order label": (lambda b: {**b, "order": "input/1"}, ("M-3", "EVIDENCE_BATCH_INVALID")),
}


@pytest.mark.negative
@pytest.mark.parametrize("name", list(BATCH_FORGERIES))
def test_forged_batch_is_corrupt(stored: tuple[Path, str], name: str) -> None:
    root, key = stored
    change, (invariant, code) = BATCH_FORGERIES[name]
    _forge_batch(root, key, change)
    cause = _corrupt(root, key)
    assert (cause.invariant, cause.code) == (invariant, code), cause


@pytest.mark.negative
def test_wrong_evidence_count_and_batch_sequence_are_corrupt(stored: tuple[Path, str]) -> None:
    root, key = stored
    recs = journal(root, key)
    at = next(i for i, r in enumerate(recs) if r["kind"] == "evidence_batch_recorded")
    for field, value, expected in (
        ("evidence_count", 7, ("M-3", "EVIDENCE_BATCH_INVALID")),
        ("batch_index", 1, ("S-8.8", "BATCH_SEQUENCE")),
        ("batch_total", 1, ("S-8.8", "BATCH_SEQUENCE")),  # this attempt has more than one batch
    ):
        rec = copy.deepcopy(recs[at])
        rec["payload"][field] = value
        tail = [r for r in recs[at + 1 :] if r["step"] == "NORMALIZE"]
        _rewrite(root, key, [*recs[:at], rec, *tail])
        cause = _corrupt(root, key)
        assert (cause.invariant, cause.code) == expected, (field, cause)


def _manifest(root: Path, key: str) -> tuple[list[dict[str, Any]], int, dict[str, Any]]:
    recs = journal(root, key)
    at = next(i for i, r in enumerate(recs) if r["kind"] == "report_recorded")
    return recs, at, json.loads(_blob_path(root, key, recs[at]["payload"]["report"]).read_bytes())


def _forge_manifest(root: Path, key: str, change: Callable[[dict[str, Any]], None]) -> None:
    recs, at, manifest = _manifest(root, key)
    change(manifest)
    rec = copy.deepcopy(recs[at])
    rec["payload"]["report"] = _put(root, key, manifest)
    _rewrite(root, key, [*recs[:at], rec])


def _swap(m: dict[str, Any]) -> None:
    chunks = m["components"]["claims"]["chunks"]
    chunks[0], chunks[1] = chunks[1], chunks[0]


MANIFEST_FORGERIES: dict[str, Callable[[dict[str, Any]], None]] = {
    "duplicated chunk reference": lambda m: m["components"]["claims"]["chunks"].__setitem__(
        1, dict(m["components"]["claims"]["chunks"][0])
    ),
    "wrong chunk count": lambda m: m["components"]["claims"]["chunks"][0].__setitem__("count", 2),
    "wrong total count": lambda m: m["components"]["claims"].__setitem__("count", 3),
    "wrong ordering metadata (order label)": lambda m: m["components"]["claims"].__setitem__("order", "input/1"),
    "wrong ordering metadata (chunks out of order)": _swap,
    "claim missing from the report": lambda m: (
        m["components"]["claims"]["chunks"].pop(),
        m["components"]["claims"].__setitem__("count", 1),
    ),
    "evidence batch omitted": lambda m: (
        m["components"]["evidence"]["batches"].pop(),
        m["components"]["evidence"].__setitem__(
            "count", sum(b["count"] for b in m["components"]["evidence"]["batches"])
        ),
    ),
    "summary disagrees with claims": lambda m: m["article_summary"]["claims_by_class"].__setitem__(
        "RETRACTED_WORK_CITED", 2
    ),
    "another investigation": lambda m: m.__setitem__("investigation_key", h("another")),
}


@pytest.mark.negative
@pytest.mark.parametrize("name", list(MANIFEST_FORGERIES))
def test_forged_report_manifest_is_corrupt(stored: tuple[Path, str], name: str) -> None:
    root, key = stored
    _, _, manifest = _manifest(root, key)
    assert len(manifest["components"]["claims"]["chunks"]) == 2
    _forge_manifest(root, key, MANIFEST_FORGERIES[name])
    cause = _corrupt(root, key)
    assert (cause.invariant, cause.code) == ("M-3", "REPORT_INVALID"), cause


@pytest.mark.negative
@pytest.mark.parametrize("how", ["missing", "changed bytes"])
def test_claim_chunk_missing_or_corrupt_is_corrupt(stored: tuple[Path, str], how: str) -> None:
    root, key = stored
    _, _, manifest = _manifest(root, key)
    _damage(_blob_path(root, key, manifest["components"]["claims"]["chunks"][1]["chunk"]), how)
    cause = _corrupt(root, key)
    assert (cause.invariant, cause.code) == ("M-3", "REPORT_INVALID") and "chunk 1" in str(cause), cause


@pytest.mark.negative
def test_claim_chunks_merged_into_a_non_canonical_cut_are_corrupt(stored: tuple[Path, str]) -> None:
    root, key = stored
    _, _, manifest = _manifest(root, key)
    refs = manifest["components"]["claims"]["chunks"]
    items = [i for r in refs for i in json.loads(_blob_path(root, key, r["chunk"]).read_bytes())["items"]]
    merged = _put(root, key, report.chunk("claims", items))

    def change(m: dict[str, Any]) -> None:
        m["components"]["claims"]["chunks"] = [{"chunk": merged, "count": len(items)}]

    _forge_manifest(root, key, change)
    cause = _corrupt(root, key)
    assert (cause.invariant, cause.code) == ("M-3", "REPORT_INVALID") and "boundaries" in str(cause), cause


@pytest.mark.integration
@pytest.mark.usefixtures("small_ceiling")
def test_report_reuses_the_committed_batches_and_copies_no_evidence(tmp_path: Path) -> None:
    root, key, st = _run(tmp_path)
    assert st.lifecycle == "COMPLETED"
    _recs, _, manifest = _manifest(root, key)
    committed = [(r["payload"]["batch"], r["payload"]["evidence_count"]) for r in _batch_records(root, key)]
    assert [(b["batch"], b["count"]) for b in manifest["components"]["evidence"]["batches"]] == committed
    assert manifest["components"]["evidence"]["count"] == len(evidence_items(root, key))
    for part in report.PARTS:
        for ref in manifest["components"][part]["chunks"]:
            assert b'"evidence_id"' not in _blob_path(root, key, ref["chunk"]).read_bytes()
    assert len(canon(manifest)) < 8192  # small: the collections are referenced, not held


@pytest.mark.negative
@pytest.mark.usefixtures("small_ceiling")
def test_a_report_that_omits_a_claim_is_refused_when_recorded(tmp_path: Path) -> None:
    def assemble(req: StepRequest) -> StepResult:
        r = ok_result(req, CLASSES)
        assert isinstance(r, Succeeded)
        manifest = next(b for b in r.blobs if isinstance(b, dict) and "components" in b)
        bad = copy.deepcopy(manifest)
        bad["components"]["claims"]["chunks"].pop()
        bad["components"]["claims"]["count"] -= 1
        rec = ContentRecord("report_recorded", {**r.records[0].payload, "report": digest(bad)})
        return Succeeded(records=(rec,), blobs=(*r.blobs, bad), outputs=(digest(bad),))

    root, key, st = _run(tmp_path, {("ASSEMBLE", 1): assemble})
    assert st.lifecycle == "FAILED"
    fail = next(r for r in journal(root, key) if r["kind"] == "step_failed")
    assert fail["payload"]["code"] == "ADAPTER_INCONSISTENT" and "REPORT_INVALID" in fail["payload"]["detail"]
    assert not [r for r in journal(root, key) if r["kind"] == "report_recorded"]


@pytest.mark.unit
def test_report_build_is_deterministic_and_ordered() -> None:
    def entry(i: int, start: int) -> dict[str, Any]:
        c = ok_claim(h(f"c{i}"))
        return {"claim": c, "decision": {"decision_id": h(f"d{i}"), "disposition": "REPORT_NOT_FOUND"},
                "question": None, "unit": {"unit_id": "un-00001", "byte_start": start, "byte_end": start + 5,
                                           "unit_span_sha256": h("s")}, "checked_sources": []}  # fmt: skip

    entries = [entry(i, start) for i, start in enumerate((30, 10, 20, 10))]
    published: dict[str, Any] = {}

    def publish(v: Any) -> str:
        published[digest(v)] = v
        return digest(v)

    header = {"investigation_key": h("k"), "investigation_id": "x", "root": {}, "terminal_state": "COMPLETED",
              "outcome": "completed", "limitations": [], "identities": {}, "snapshot_id": "s"}  # fmt: skip
    a = report.build(header, entries, [], [], [], publish)
    b = report.build(header, list(reversed(entries)), [], [], [], publish)
    assert a == b
    order = [i for r in a["components"]["claims"]["chunks"] for i in published[r["chunk"]]["items"]]
    assert [report.claim_key(e) for e in order] == sorted(report.claim_key(e) for e in entries)


def ok_claim(cid: str) -> dict[str, Any]:
    keys = [{"scheme": "doi", "normalized": "10.1/x"}]
    return {"claim_id": cid, "class": "NOT_FOUND_IN_CHECKED_SOURCES",
            "candidate": {"shape": "DOI", "keys": keys, "coherence": None}}  # fmt: skip


# Scientific invariance (owner D-053): the logical content equals the accepted baseline's ---------------------------

# Logical-view digests of docs/verification/stage-04/review/step7/d053/equivalence.py run on the accepted baseline
# 64e7acace6d13e61f3346b51cd045883236f9dca (journal format 2, one record per evidence item); equivalence_before.json.
BASELINE_64E7ACA = {
    "not found and retracted": "77916a7ebfa74c9e4cf43a5ccd049319997c3488cb7c1a7bd2095545da78d718",
    "identity conflict": "ac2f0e1643f2b29d107490a4b2ec66764bcc287a736ba1e305f7d8a24457c37b",
    "source contradiction beside a finding": "64bf58a5f910cb8943fda8390bc78504a85517fb89e6fa14e9110f738a187e0b",
    "lookup unavailable": "b0df2b0193c46c06c78e712d0323b231f1ab632685b28295f5bb0368f61afff7",
    "unsupported synthetic class (DETECT fails terminally)": (
        "3bd6e925d55854e2ce4a3e457bd6219a300986d0e39bbf201811bc12e02519f0"
    ),
}


@pytest.mark.reproducibility
@pytest.mark.parametrize("name", list(BASELINE_64E7ACA))
def test_logical_content_equals_the_accepted_baseline(name: str) -> None:
    import importlib.util

    path = CEILING_RECORD.with_name("equivalence.py")
    spec = importlib.util.spec_from_file_location("d053_equivalence", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    got = module.logical_view(ROOT, module.SCENARIOS[name])
    # Step 8 (IF-7) replaced the SYNTHETIC bundle observation; everything else equals the baseline.
    assert with_legacy_bundle(got["view"], module._canon) == BASELINE_64E7ACA[name], got["counts"]
