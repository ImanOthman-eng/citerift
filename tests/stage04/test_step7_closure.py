"""Stage 04 Step 7 corrective closure: owner decisions D-047 to D-051 (fail-first evidence:
docs/verification/stage-04/review/step7/closure/fail_first_before.log; design: STEP7_CLOSURE.md).

SYNTHETIC fake adapters (``controller_support``) and, for D-050, documents built by the accepted Stage 03 code.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from controller_support import (
    EXTRACTION,
    LOOKUP,
    Env,
    Plan,
    StepClock,
    claim_and_set,
    create,
    digest,
    evidence,
    evidence_items,
    journal,
    ok_result,
    run_once,
    synthetic_report,
)
from memory_support import bundle_request, h

from citerift.investigation import fold, ids, sets
from citerift.investigation.adapters import ContentRecord, Failed, StepRequest, StepResult, Succeeded
from citerift.investigation.canonical import H, canon
from citerift.investigation.errors import InvestigationMemoryError
from citerift.investigation.extraction import ADAPTER_INCONSISTENT, EXTRACTION_FAILED, extraction_failure
from citerift.investigation.fold import STEPS
from citerift.investigation.journal import JOURNAL_FORMAT, MAX_RECORD_BYTES
from citerift.investigation.lookup import DEFAULT_LOOKUP_EVIDENCE_BUDGET_BYTES, LIMIT_CODE, bounded_gather
from citerift.investigation.memory import InvestigationMemory
from citerift.investigation.schemas import EVIDENCE_BATCH, problems
from citerift.investigation.workflow import EXTRACT_RETRYABLE

REPO = Path(__file__).resolve().parents[2]


def _failures(root: Path, key: str) -> list[tuple[str, str, str | None]]:
    return [
        (r["step"], r["payload"]["code"], r["payload"]["reason"])
        for r in journal(root, key)
        if r["kind"] == "step_failed"
    ]


def _run(tmp: Path, script: dict[tuple[str, int], Any]) -> tuple[Path, str, Any]:
    clock = StepClock()
    root, key = create(tmp, clock=clock)
    return root, key, run_once(root, key, Plan(script), Env(), clock)


@pytest.fixture
def evidence_schema_skipped(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Skip the JSON Schema validation of evidence batches only (D-053), so tens of thousands of items fit a test run.
    Every other record, every Memory invariant (M-1 to M-14), every per-item check of a batch and every set check
    still runs, on append and on reopen. The batch schema is covered by the contract tests."""
    real = fold.problems

    def problems_except_evidence(value: Any, schema_id: str) -> list[str]:
        if schema_id == EVIDENCE_BATCH:
            return []
        return real(value, schema_id)

    monkeypatch.setattr(fold, "problems", problems_except_evidence)
    yield


# D-051: evidence_id = H(observation, pointer, kind) ------------------------------------------------------------------


@pytest.mark.regression
def test_d051_two_kinds_at_one_pointer_coexist(tmp_path: Path) -> None:
    """Fail-first (fail_first_before.log, D-051): the unit and an identifier occurrence at one pointer had one id and
    NORMALIZE failed DUPLICATE_ID. Now they are two evidence items and the investigation completes."""
    ext = digest(EXTRACTION)
    old_unit = H(ids.EVIDENCE_TAG, ext, "/units/0")
    old_occ = H(ids.EVIDENCE_TAG, ext, "/units/0")
    assert old_unit == old_occ  # the Step 7 derivation (no kind) collided

    def normalize(req: StepRequest) -> StepResult:
        unit = evidence("unit", ext, "/units/0", [], {"source_artifact": h("src"), "unit_span_sha256": h("span")})
        occ = evidence(
            "identifier_occurrence",
            ext,
            "/units/0",
            [unit["evidence_id"]],
            {"status": "CONFIRMED", "key": {"scheme": "doi", "normalized": "10.1000/xyz"}},
        )
        assert unit["evidence_id"] != occ["evidence_id"]
        out = {"normalized": [unit["evidence_id"], occ["evidence_id"]]}
        recs = (ContentRecord("evidence", unit), ContentRecord("evidence", occ))
        return Succeeded(records=recs, blobs=(out,), outputs=(digest(out),))

    root, key, st = _run(tmp_path, {("NORMALIZE", 1): normalize})
    assert st.lifecycle == "COMPLETED"
    kinds = {e["kind"] for e in evidence_items(root, key)}
    assert {"unit", "identifier_occurrence"} <= kinds


@pytest.mark.negative
def test_d051_same_kind_at_one_pointer_is_one_item_and_a_repeat_is_refused(tmp_path: Path) -> None:
    ext = digest(EXTRACTION)
    a = evidence("unit", ext, "/units/0", [], {"source_artifact": h("src"), "unit_span_sha256": h("span")})
    b = evidence("unit", ext, "/units/0", [], {"source_artifact": h("src"), "unit_span_sha256": h("span")})
    assert a["evidence_id"] == b["evidence_id"]

    def normalize(req: StepRequest) -> StepResult:
        out = {"normalized": [a["evidence_id"]]}
        recs = (ContentRecord("evidence", a), ContentRecord("evidence", b))
        return Succeeded(records=recs, blobs=(out,), outputs=(digest(out),))

    root, key, st = _run(tmp_path, {("NORMALIZE", 1): normalize})
    assert st.lifecycle == "FAILED"
    assert _failures(root, key) == [("NORMALIZE", ADAPTER_INCONSISTENT, None)]


@pytest.mark.unit
def test_d051_id_is_deterministic_and_binds_each_part() -> None:
    o, p, k = h("obs"), "/units/0", "unit"
    assert ids.evidence_id(o, p, k) == ids.evidence_id(o, p, k) == H("citerift-evidence/1", o, p, k)
    others = {ids.evidence_id(h("obs2"), p, k), ids.evidence_id(o, "/units/1", k), ids.evidence_id(o, p, "use")}
    assert ids.evidence_id(o, p, k) not in others and len(others) == 3


# D-047: evidence and projection sets ---------------------------------------------------------------------------------


def _ids(n: int, tag: str = "e") -> list[str]:
    return [h(f"{tag}{i}") for i in range(n)]


@pytest.mark.unit
def test_d047_set_of_50000_ids_is_canonical_valid_and_over_one_mib() -> None:
    ev = _ids(50_000)
    value = sets.evidence_set(ev)
    assert sets.evidence_set_problem(value) == "" and problems(value, sets.EVIDENCE_SET) == []
    assert len(canon(value)) > MAX_RECORD_BYTES  # the set is a blob; it could never be an inline record list
    shuffled = list(reversed(ev))
    assert digest(sets.evidence_set(shuffled)) == digest(value)  # deterministic: order of input is irrelevant
    assert value["supporting"] == sorted(ev) and len(value["supporting"]) == 50_000  # nothing dropped
    with pytest.raises(ValueError, match="twice"):
        sets.evidence_set([*ev, ev[0]])
    unsorted = copy.deepcopy(value)
    unsorted["supporting"][0], unsorted["supporting"][1] = unsorted["supporting"][1], unsorted["supporting"][0]
    assert "sorted" in sets.evidence_set_problem(unsorted)


@pytest.mark.unit
def test_d047_projection_set_of_50000_is_canonical_and_valid() -> None:
    ps = _ids(50_000, "p")
    value = sets.projection_set(ps)
    assert sets.projection_set_problem(value) == "" and len(canon(value)) > MAX_RECORD_BYTES
    assert digest(sets.projection_set(reversed(ps))) == digest(value)
    with pytest.raises(ValueError, match="twice"):
        sets.projection_set([*ps, ps[-1]])


def _detect_with(evs: list[dict[str, Any]], set_value: dict[str, Any], claim: dict[str, Any]) -> Any:
    def detect(req: StepRequest) -> StepResult:
        out = {"claims": [claim["claim_id"]]}
        recs = (*(ContentRecord("evidence", e) for e in evs), ContentRecord("claim_recorded", claim))
        return Succeeded(records=recs, blobs=(set_value, out), outputs=(digest(out),))

    return detect


def _lookup_evidence(n: int) -> list[dict[str, Any]]:
    obs = digest(LOOKUP)
    return [evidence("lookup_result", obs, f"/results/{i}", [], None) for i in range(n)]


def _bind(claim: dict[str, Any], value: dict[str, Any]) -> dict[str, Any]:
    c = copy.deepcopy(claim)
    c["evidence_set"] = digest(value)
    c["supporting_count"] = len(value["supporting"])
    c["contradicting_count"] = len(value["contradicting"])
    c["alternatives"] = [
        {"value": a["value"], "supporting_count": len(ids_)}
        for a, ids_ in zip(c["alternatives"], value["alternatives"], strict=True)
    ]
    c["claim_id"] = ids.claim_id(c["cand_ref"], c["class"], c["rule"], c["table_version"], c["evidence_set"])
    return c


@pytest.mark.regression
@pytest.mark.usefixtures("evidence_schema_skipped")
def test_d047_claim_over_50000_evidence_ids_commits_replays_and_keeps_no_inline_copy(tmp_path: Path) -> None:
    """Fail-first: a claim with 16,000 ids was RECORD_TOO_LARGE (1,072,796 bytes) and 50,000 ids 3,350,796 bytes.
    Now the claim names a 3.3 MB evidence-set blob and stays a small record; reopen replays and checks the set."""
    evs = _lookup_evidence(50_000)
    value = sets.evidence_set([e["evidence_id"] for e in evs])
    claim, _ = claim_and_set("RETRACTED_WORK_CITED", [evs[0]["evidence_id"]] * 4)
    claim = _bind(claim, value)
    root, key, st = _run(tmp_path, {("DETECT", 1): _detect_with(evs, value, claim)})
    assert st.lifecycle == "COMPLETED"
    recs = journal(root, key)
    rec = next(r for r in recs if r["kind"] == "claim_recorded")
    assert set(rec["payload"]) >= {"evidence_set", "supporting_count", "contradicting_count"}
    assert not {"supporting", "contradicting"} & set(rec["payload"])  # no second inline copy
    assert rec["payload"]["supporting_count"] == 50_000
    assert len(canon(rec)) < 4096
    stored = (root / key / "blobs" / rec["payload"]["evidence_set"]).read_bytes()
    assert stored == canon(value) and len(stored) > MAX_RECORD_BYTES
    # claim_id binds the exact set: a different set gives a different id.
    other = sets.evidence_set([e["evidence_id"] for e in evs[:-1]])
    assert ids.claim_id(claim["cand_ref"], claim["class"], claim["rule"], "dt-1", digest(other)) != claim["claim_id"]
    # Replay: a full reopen (blobs read, sets checked) gives the same content digest.
    digests = []
    for _ in range(2):
        with InvestigationMemory.open(root, key, writable=False) as m:
            assert m.view.lifecycle() == "COMPLETED"
            digests.append(m.view.content_digest())
    assert digests[0] == digests[1]


@pytest.mark.regression
@pytest.mark.usefixtures("evidence_schema_skipped")
def test_d047_large_conflict_alternatives(tmp_path: Path) -> None:
    """A contradiction whose two alternatives each have 9,000 supporting ids (a 1.2 MB set)."""
    evs = _lookup_evidence(18_000)
    a, b = [e["evidence_id"] for e in evs[:9000]], [e["evidence_id"] for e in evs[9000:]]
    value = sets.evidence_set([], [], [a, b])
    claim, _ = claim_and_set("CONTRADICTION_IN_SOURCES", [e["evidence_id"] for e in evs[:4]])
    claim = _bind(claim, value)
    assert len(canon(value)) > MAX_RECORD_BYTES
    root, key, st = _run(tmp_path, {("DETECT", 1): _detect_with(evs, value, claim)})
    assert st.lifecycle == "NEEDS_RESOLUTION"
    rec = next(r for r in journal(root, key) if r["kind"] == "claim_recorded")
    assert [x["supporting_count"] for x in rec["payload"]["alternatives"]] == [9000, 9000]
    assert len(canon(rec)) < 4096


def _assemble_with(n: int) -> Any:
    def assemble(req: StepRequest) -> StepResult:
        projections = [{"projection": i} for i in range(n)]
        value = sets.projection_set(digest(p) for p in projections)
        chunks: list[Any] = []  # the D-054 report manifest and its chunks (the report itself is not under test)
        report = synthetic_report(req.committed, req.root, req.investigation, req.request, req.live, chunks)
        rec = ContentRecord(
            "report_recorded", {"report": digest(report), "projection_set": digest(value), "projection_count": n}
        )
        return Succeeded(records=(rec,), blobs=(*chunks, report, value, *projections), outputs=(digest(report),))

    return assemble


@pytest.mark.regression
def test_d047_report_with_50000_projections(tmp_path: Path) -> None:
    """Fail-first: a report_recorded with 50,000 projections was RECORD_TOO_LARGE (3,350,437 bytes)."""
    root, key, st = _run(tmp_path, {("ASSEMBLE", 1): _assemble_with(50_000)})
    assert st.lifecycle == "COMPLETED"
    rec = next(r for r in journal(root, key) if r["kind"] == "report_recorded")
    assert rec["payload"]["projection_count"] == 50_000 and len(canon(rec)) < 1024
    with InvestigationMemory.open(root, key, writable=False) as m:
        assert m.view.lifecycle() == "COMPLETED"


def _claim_case(change: str) -> Any:
    def detect(req: StepRequest) -> StepResult:
        r = ok_result(req, (("NOT_FOUND_IN_CHECKED_SOURCES", "cand"),))
        assert isinstance(r, Succeeded)
        claim_rec = next(c for c in r.records if c.kind == "claim_recorded")
        claim = dict(claim_rec.payload)
        value = next(b for b in r.blobs if isinstance(b, dict) and b.get("schema") == sets.EVIDENCE_SET)
        blobs = [b for b in r.blobs if b is not value]
        if change == "missing":
            pass  # the set is never published
        elif change == "empty-set":
            value = sets.evidence_set([])
            claim = _bind_keep_counts(claim, value)
            blobs.append(value)
        elif change == "unsorted":
            value = {**value, "supporting": [h("z"), h("a")]}
            claim = _bind_keep_counts(claim, value, supporting=2)
            blobs.append(value)
        elif change == "count-mismatch":
            claim = {**claim, "supporting_count": 2}
            claim["claim_id"] = ids.claim_id(
                claim["cand_ref"], claim["class"], claim["rule"], "dt-1", claim["evidence_set"]
            )
            blobs.append(value)
        elif change == "not-a-set":
            value = {"supporting": value["supporting"]}
            claim = _bind_keep_counts(claim, value)
            blobs.append(value)
        elif change == "claim-id-of-another-set":
            claim["claim_id"] = ids.claim_id(claim["cand_ref"], claim["class"], claim["rule"], "dt-1", h("other"))
            blobs.append(value)
        recs = tuple(ContentRecord("claim_recorded", claim) if c.kind == "claim_recorded" else c for c in r.records)
        out = {"claims": [claim["claim_id"]]}
        blobs = [b for b in blobs if not (isinstance(b, dict) and "claims" in b)] + [out]
        return Succeeded(records=recs, blobs=tuple(blobs), outputs=(digest(out),))

    return detect


def _bind_keep_counts(claim: dict[str, Any], value: dict[str, Any], supporting: int | None = None) -> dict[str, Any]:
    c = dict(claim)
    c["evidence_set"] = digest(value)
    if supporting is not None:
        c["supporting_count"] = supporting
    c["claim_id"] = ids.claim_id(c["cand_ref"], c["class"], c["rule"], "dt-1", c["evidence_set"])
    return c


@pytest.mark.negative
@pytest.mark.parametrize(
    "change", ["missing", "empty-set", "unsorted", "count-mismatch", "not-a-set", "claim-id-of-another-set"]
)
def test_d047_a_missing_or_invalid_set_is_refused_never_empty(tmp_path: Path, change: str) -> None:
    root, key, st = _run(tmp_path, {("DETECT", 1): _claim_case(change)})
    assert st.lifecycle == "FAILED"
    assert _failures(root, key) == [("DETECT", ADAPTER_INCONSISTENT, None)]
    assert not [r for r in journal(root, key) if r["kind"] == "step_succeeded" and r["step"] == "DETECT"]


@pytest.mark.negative
@pytest.mark.parametrize("change", ["count", "missing-projection", "unsorted"])
def test_d047_an_invalid_projection_set_is_refused(tmp_path: Path, change: str) -> None:
    def assemble(req: StepRequest) -> StepResult:
        projections = [{"projection": i} for i in range(3)]
        digests = sorted(digest(p) for p in projections)
        value = sets.projection_set(digests)
        count = 3
        published: list[Any] = list(projections)
        if change == "count":
            count = 2
        elif change == "missing-projection":
            published = published[:2]
        else:
            value = {**value, "projections": list(reversed(digests))}
        report = {"report": "SYNTHETIC"}
        rec = ContentRecord(
            "report_recorded", {"report": digest(report), "projection_set": digest(value), "projection_count": count}
        )
        return Succeeded(records=(rec,), blobs=(report, value, *published), outputs=(digest(report),))

    root, key, st = _run(tmp_path, {("ASSEMBLE", 1): assemble})
    assert st.lifecycle == "FAILED"
    assert _failures(root, key) == [("ASSEMBLE", ADAPTER_INCONSISTENT, None)]


@pytest.mark.negative
@pytest.mark.parametrize("damage", ["delete", "modify"])
@pytest.mark.parametrize("which", ["evidence_set", "projection_set"])
def test_d047_a_set_damaged_after_commit_makes_the_investigation_corrupt(
    tmp_path: Path, damage: str, which: str
) -> None:
    root, key, st = _run(tmp_path, {})
    assert st.lifecycle == "COMPLETED"
    kind = "claim_recorded" if which == "evidence_set" else "report_recorded"
    d = next(r for r in journal(root, key) if r["kind"] == kind)["payload"][which]
    blob = root / key / "blobs" / d
    blob.chmod(0o600)
    if damage == "delete":
        blob.unlink()
    else:
        blob.write_bytes(
            canon(sets.evidence_set([])) if which == "evidence_set" else canon(sets.projection_set([h("x")]))
        )
    with pytest.raises(InvestigationMemoryError) as exc:
        InvestigationMemory.open(root, key, writable=False)
    assert exc.value.code == "CORRUPT"


@pytest.mark.negative
@pytest.mark.parametrize("old", [1, 2])
def test_d047_an_earlier_format_journal_is_refused_not_migrated(tmp_path: Path, old: int) -> None:
    """JOURNAL_FORMAT is 3 (D-053; 2 was D-047/D-051, 1 the Step 6/7 format, none released): a journal of an earlier
    format is refused with JOURNAL_VERSION_UNSUPPORTED, never migrated."""
    assert JOURNAL_FORMAT == 3
    root, key, _ = _run(tmp_path, {})
    path = root / key / "journal.jsonl"
    lines = path.read_bytes().splitlines()
    first = json.loads(lines[0])
    first["v"] = old
    first["digest"] = ids.record_digest({k: v for k, v in first.items() if k != "digest"})
    path.chmod(0o600)
    path.write_bytes(canon(first) + b"\n")
    with pytest.raises(InvestigationMemoryError) as exc:
        InvestigationMemory.open(root, key, writable=False)
    assert exc.value.code == "CORRUPT" and "JOURNAL_VERSION_UNSUPPORTED" in str(exc.value)


# D-049: ADAPTER_INCONSISTENT is terminal in every step; domain failures keep their codes -----------------------------

DOMAIN: dict[str, tuple[str, str | None]] = {
    "VALIDATE": ("INPUT_INVALID", "WIKI_UNSUPPORTED"),
    "ACQUIRE": ("PAGE_MISSING", None),
    "EXTRACT": ("EXTRACTION_FAILED", "LIMIT_NODES"),
    "NORMALIZE": ("NORMALIZE_INVALID", None),
    "LOOKUP": ("INDEX_MISSING", None),
    "DETECT": ("DECISION_TABLE_GAP", None),
    "ASSEMBLE": ("REPORT_INVALID", None),
    "VERIFY": ("VERIFY_FAILED", "CHECK_FAILED"),
}


@pytest.mark.negative
@pytest.mark.parametrize("step", STEPS)
@pytest.mark.parametrize(
    "bad",
    [
        pytest.param(lambda r: None, id="wrong-type"),
        pytest.param(lambda r: Failed("NOT_A_CODE_OF_ANY_STEP"), id="code-of-no-step"),
        pytest.param(lambda r: Failed("STEP_INTERRUPTED"), id="controller-reason-as-code"),
        pytest.param(lambda r: Failed("RETRY_BUDGET_EXHAUSTED"), id="controller-code"),
        pytest.param(lambda r: Failed("INPUT_INVALID", evidence={"x": 1}), id="evidence-with-a-foreign-code"),
    ],
)
def test_d049_defect_is_terminal_in_every_step(tmp_path: Path, step: str, bad: Any) -> None:
    """Fail-first for ACQUIRE: fail_first_acquire_code.log (an unknown code was recorded as the terminal code)."""
    root, key, st = _run(tmp_path, {(step, 1): bad})
    assert st.lifecycle == "FAILED"
    assert _failures(root, key) == [(step, ADAPTER_INCONSISTENT, None)]
    recs = [r for r in journal(root, key) if r["step"] == step]
    assert [r["kind"] for r in recs if r["kind"].startswith("step_")] == ["step_started", "step_failed"]
    assert recs[-1]["payload"]["retryable"] is False


@pytest.mark.regression
@pytest.mark.parametrize("step", STEPS)
def test_d049_domain_failures_keep_their_codes(tmp_path: Path, step: str) -> None:
    code, reason = DOMAIN[step]
    root, key, st = _run(tmp_path, {(step, a): Failed(code, reason=reason, detail="SYNTHETIC") for a in (1, 2, 3)})
    assert st.lifecycle == "FAILED"
    assert _failures(root, key) == [(step, code, reason)]


# D-050: failed Stage 03 documents -------------------------------------------------------------------------------------


def _stage03() -> Any:
    sys.path.insert(0, str(REPO / "tests" / "stage03"))
    try:
        import wiki_support
    finally:
        sys.path.remove(str(REPO / "tests" / "stage03"))
    return wiki_support


def _worker_doc(code: str) -> dict[str, Any]:
    from citerift.wiki.extract import ExtractConfig, failure_document

    return failure_document(None, ExtractConfig(), code, "SYNTHETIC")


@pytest.mark.regression
@pytest.mark.parametrize("code", sorted(EXTRACT_RETRYABLE))
def test_d050_worker_resource_codes_keep_their_code_and_retry(tmp_path: Path, code: str) -> None:
    doc = _worker_doc(code)
    f = extraction_failure(doc)
    assert (f.code, f.reason, f.evidence) == (code, None, doc)
    root, key, st = _run(tmp_path, {("EXTRACT", a): (lambda req, d=doc: extraction_failure(d)) for a in (1, 2, 3)})
    assert st.lifecycle == "FAILED"
    assert _failures(root, key) == [
        ("EXTRACT", code, None),
        ("EXTRACT", code, None),
        ("EXTRACT", "RETRY_BUDGET_EXHAUSTED", code),
    ]
    blob = canon(doc, allow_float=True)  # a Stage 03 document holds floats (its configuration)
    kept = [r for r in journal(root, key) if r["kind"] == "observation_recorded" and r["step"] == "EXTRACT"]
    assert len(kept) == 3 and all(r["payload"]["blob"] == hashlib.sha256(blob).hexdigest() for r in kept)
    assert (root / key / "blobs" / kept[0]["payload"]["blob"]).read_bytes() == blob


@pytest.mark.regression
@pytest.mark.parametrize("code", ["BUNDLE_MALFORMED", "PLATFORM_UNSUPPORTED", "BUNDLE_DIGEST_MISMATCH"])
def test_d050_other_worker_component_codes_are_extraction_failed(tmp_path: Path, code: str) -> None:
    doc = _worker_doc(code)
    root, key, st = _run(tmp_path, {("EXTRACT", 1): lambda req: extraction_failure(doc)})
    assert st.lifecycle == "FAILED"
    assert _failures(root, key) == [("EXTRACT", EXTRACTION_FAILED, code)]
    rec = next(r for r in journal(root, key) if r["kind"] == "step_failed")
    assert rec["payload"]["retryable"] is False


@pytest.mark.regression
@pytest.mark.parametrize(
    ("family", "code"),
    [
        ("limit_nodes", "LIMIT_NODES"),
        ("limit_depth", "LIMIT_DEPTH"),
        ("limit_occurrences", "LIMIT_OCCURRENCES"),
        ("parse_lossy", "SOURCE_PARSE_LOSSY"),
        ("no_supported_source", "BUNDLE_SEMANTIC_INVALID"),
        ("accounting", "BUNDLE_SEMANTIC_INVALID"),
    ],
)
def test_d050_source_and_accounting_failures_are_extraction_failed(tmp_path: Path, family: str, code: str) -> None:
    """Every non-worker failure family Stage 03 produces (wiki/extract.py): a source parser limit or a lossy parse
    (source component with the code), no supported source (source failed without a code, error issue), and an
    accounting failure (error issue). The first three are produced by the accepted Stage 03 code on a SYNTHETIC
    bundle; the last two are the complete document with exactly what wiki/extract.py lines 172-173 and 554-555 set."""
    from citerift.wiki.extract import ExtractConfig

    w = _stage03()
    text = (  # the Stage 03 structural-limit fixture (tests/stage03/test_wiki_bundle_verify.py)
        'Alpha.<ref name="a">{{cite journal |title=T |doi=10.1234/abc |pmid=123}}</ref> Beta.<ref name="a" />\n'
        "{{a|{{b|{{c|x}}}}}}<ref>{{cite web |url=https://doi.org/10.1/x}}</ref>\n"
    )
    configs = {
        "limit_nodes": ExtractConfig(max_nodes=5),
        "limit_depth": ExtractConfig(max_depth=1),
        "limit_occurrences": ExtractConfig(max_refs=1),
    }
    if family in configs:
        doc = w.extract(w.bundle(tmp_path, text), config=configs[family])
    elif family == "parse_lossy":
        doc = w.extract(w.bundle(tmp_path, "A{{sfn|Smith\0|2001}} B{{sfn|Smith|2001}}"))
    else:
        doc = w.extract(w.bundle(tmp_path, text))
        assert doc["status"] in ("complete", "partial")  # a source-only capture is partial
        issue = {
            "code": "BUNDLE_SEMANTIC_INVALID",
            "severity": "error",
            "retryable": False,
            "entities": [],
            "evidence": [],
        }
        if family == "no_supported_source":
            doc["status"], doc["components"] = "failed", {"source": {"state": "failed"}}
            doc["issues"] = [{**issue, "detail": "the capture holds no supported source"}]
            doc["accounting"] = {}
            for k in ("containers", "uses", "units", "identifiers", "excluded_identifiers", "markers"):
                doc[k] = []
        else:
            doc["status"] = "failed"
            doc["accounting"]["checks"][0]["ok"] = False
            doc["issues"].append({**issue, "detail": "an accounting check failed"})
    assert doc["status"] == "failed"
    f = extraction_failure(doc)
    assert (f.code, f.reason) == (EXTRACTION_FAILED, code), f.detail
    (tmp_path / "inv").mkdir()
    root, key, st = _run(tmp_path / "inv", {("EXTRACT", 1): lambda req: extraction_failure(doc)})
    assert st.lifecycle == "FAILED" and _failures(root, key) == [("EXTRACT", EXTRACTION_FAILED, code)]


@pytest.mark.negative
@pytest.mark.parametrize(
    "change",
    [
        "not-a-document",
        "status-complete",
        "worker-code-unknown",
        "worker-code-not-an-issue",
        "worker-code-in-source-component",
        "no-code-and-no-error",
        "unknown-component-code",
    ],
)
def test_d050_malformed_or_contradictory_documents_are_adapter_inconsistent(change: str) -> None:
    doc: Any = _worker_doc("EXTRACTION_DEADLINE_EXCEEDED")
    if change == "not-a-document":
        doc = {"status": "failed"}
    elif change == "status-complete":
        doc["status"] = "complete"
    elif change == "worker-code-unknown":
        doc["components"]["worker"]["code"] = "NOT_A_STAGE03_CODE"
        doc["issues"][0]["code"] = "NOT_A_STAGE03_CODE"
    elif change == "worker-code-not-an-issue":
        doc["issues"][0]["code"] = "BUNDLE_MALFORMED"
    elif change == "worker-code-in-source-component":
        doc["components"] = {"source": {"state": "failed", "code": "EXTRACTION_DEADLINE_EXCEEDED"}}
    elif change == "no-code-and-no-error":
        doc["components"] = {"source": {"state": "failed"}}
        doc["issues"] = []
    elif change == "unknown-component-code":
        doc["components"] = {"source": {"state": "failed", "code": "LIMIT_UNKNOWN"}}
        doc["issues"] = []
    f = extraction_failure(doc)
    assert f.code == ADAPTER_INCONSISTENT, f


# D-048 in Stage 04: the bounded lookup, its unavailable result and its configuration ---------------------------------


@pytest.mark.regression
def test_d048_budget_is_configuration_and_changes_config_digest(tmp_path: Path) -> None:
    req = bundle_request(tmp_path)
    assert req["config"]["lookup_evidence_budget_bytes"] == DEFAULT_LOOKUP_EVIDENCE_BUDGET_BYTES == 16 * 1024 * 1024
    a = ids.config_digest(req["config"])
    b = ids.config_digest({**req["config"], "lookup_evidence_budget_bytes": DEFAULT_LOOKUP_EVIDENCE_BUDGET_BYTES - 1})
    assert a != b
    missing = {k: v for k, v in req["config"].items() if k != "lookup_evidence_budget_bytes"}
    assert problems({**req, "config": missing}, "urn:citerift:schema:investigation:v1:request")
    over = {**req["config"], "lookup_evidence_budget_bytes": DEFAULT_LOOKUP_EVIDENCE_BUDGET_BYTES + 1}
    assert problems({**req, "config": over}, "urn:citerift:schema:investigation:v1:request")


def _fanout_index(tmp: Path, n: int) -> Path:
    sys.path.insert(0, str(REPO / "tests" / "stage02"))
    try:
        import rde_support as S
    finally:
        sys.path.remove(str(REPO / "tests" / "stage02"))
    rows = [
        S.row(
            **{
                "Record ID": str(i + 1),
                "RetractionNature": "Retraction",
                "OriginalPaperDOI": "10.5555/many",
                "RetractionDOI": f"10.5555/n{i}",
            }
        )
        for i in range(n)
    ]
    return S.build_rows(tmp, rows)


@pytest.mark.negative
def test_d048_over_the_budget_the_lookup_is_unavailable_whole(tmp_path: Path) -> None:
    from citerift.retraction.query import Index

    with Index(_fanout_index(tmp_path, 50)) as ix:
        full = ix.gather("10.5555/many")
        assert full.state == "matched" and len(full.events) == 50
        need = 0
        while True:  # the smallest budget the lookup fits
            ev = bounded_gather(ix, "10.5555/many", None, need)
            if ev.state != "unavailable":
                break
            need = ev.issues[0]["needed_at_least_bytes"]
        assert ev.events == full.events  # at N: the full result
        assert bounded_gather(ix, "10.5555/many", None, need + 1).events == full.events  # N + 1
        over = bounded_gather(ix, "10.5555/many", None, need - 1)  # N - 1
    assert over.state == "unavailable" and over.events == [] and over.notice_hits == []
    assert over.issues == [{"code": LIMIT_CODE, "budget_bytes": need - 1, "needed_at_least_bytes": need}]
    assert over.evidence_set is not None and over.evidence_set.assertions == ()
    from citerift.retraction.query import projection_of

    projection = projection_of(over)
    assert projection is None or projection["retraction_status"]["status"] == "unavailable"


@pytest.mark.regression
def test_d048_an_unavailable_lookup_decides_lookup_unavailable_in_the_reference_model() -> None:
    """The frozen Step 4 reference model (dt-1): a candidate whose only lookup is unavailable is LOOKUP_UNAVAILABLE
    (D-13); an over-budget lookup can therefore never yield a finding or NOT_FOUND_IN_CHECKED_SOURCES by itself."""
    sys.path.insert(0, str(REPO / "simulations" / "stage04"))
    try:
        import dt1_reference as R
    finally:
        sys.path.remove(str(REPO / "simulations" / "stage04"))
    unavailable = ("unavailable", "none", False)
    for shape, case in (
        ("DOI", R.Case("CITED", "DOI", frozenset(), False, unavailable)),
        ("PMID", R.Case("CITED", "PMID", frozenset(), False, None, unavailable)),
        ("PAIR", R.Case("CITED", "PAIR", frozenset(), False, unavailable, unavailable, unavailable)),
    ):
        dec = R.decide(case)
        assert (dec["class"], dec["rule"]) == ("LOOKUP_UNAVAILABLE", "D-13"), (shape, dec)
