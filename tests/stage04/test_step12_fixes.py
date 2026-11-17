"""Stage 04 Step 12: tests of the pre-freeze corrections (STEP12_TRIAGE.md) other than D-062 (``test_step12_d062``).

- I-2: one outcome rule (``report.outcome``), used by ASSEMBLE; nothing else derives an outcome.
- A11-5 (Reviewer F option b): whenever no step may start before ``not_before`` the user-facing status is ``blocked``
  (exit 8), also for a RUNNING investigation after a retryable failure with a Retry-After instant; the lifecycle stays
  in the output; no adapter starts early, nothing sleeps, export is refused.
- A11-6 / C-04 / C-06: relocation. The paths a request names are operational locators: the same inputs at other
  paths and another memory root give the same scientific content, and moved inputs are named with ``--index`` and
  ``--bundle``.
- UF-03, MM 10.2: ``show`` names the transition ``resume`` would take after an input change, and an input that
  cannot be established now is refused (exit 3), never reported as a change.
- A-02: VERIFY (and so ``replay``) requires the re-run DETECT claims and evidence items in full, not only their ids.
- C-09: an index path that is a symbolic link to a regular file is accepted, as Stage 02 opens it.
- UF-06: text output names the changed identities.
- B-05, B-06/SD-04, B-08, B-09, SD-05 (in ``test_memory_storage``), SD-06, UF-01, UF-04, UF-05, UF-08, UF-09.
- A-01, A-03, A-04 in ``test_step12_semantics``; B-01 in ``test_step12_d062``; B-04, SD-01 in ``test_step8_live``.

Real bundles and the attributed Retraction Watch subset index of ``step8_support``; offline except where a fake live
ACQUIRE stands in for Stage 03 (no network).
"""

from __future__ import annotations

import dataclasses
import json
import os
import shutil
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import step8_support as S8
import step10_support as T

from citerift.investigation import operations as ops
from citerift.investigation import projections, report
from citerift.investigation.adapters import ContentRecord, Failed, StepRequest, Succeeded
from citerift.investigation.adapters import verify as V
from citerift.investigation.adapters.plan import Integration
from citerift.investigation.errors import CorruptInvestigation
from citerift.investigation.memory import InvestigationMemory
from citerift.retraction.store import manifest_path_for

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def index(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return S8.build_index(tmp_path_factory.mktemp("rw"))


@pytest.fixture(scope="module")
def en(tmp_path_factory: pytest.TempPathFactory, index: Path) -> T.Inv:
    with T.offline():
        return T.Inv(tmp_path_factory.mktemp("en"), S8.EN_OBOKATA, index)


def _key_args(inv: T.Inv) -> list[Any]:
    return ["--memory-root", inv.root, "--key", inv.key]


# I-2 ---------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "open_q", "unavailable", "expected"),
    [
        ("complete", False, False, "completed"),
        ("partial", False, False, "partial"),
        ("complete", True, False, "partial"),
        ("complete", False, True, "partial"),
        ("partial", True, True, "partial"),
    ],
)
def test_i2_one_outcome_rule(status: str, open_q: bool, unavailable: bool, expected: str) -> None:
    assert report.outcome(status, open_questions=open_q, lookup_unavailable=unavailable) == expected


def test_i2_the_outcome_rule_refuses_an_unknown_extraction_status() -> None:
    with pytest.raises(ValueError, match="extraction status"):
        report.outcome("failed", open_questions=False, lookup_unavailable=False)


def test_i2_no_second_outcome_derivation_remains() -> None:
    from citerift.investigation import workflow

    assert not hasattr(workflow, "outcome")
    assert "outcome" not in {f.name for f in workflow.WorkflowState.__dataclass_fields__.values()}


def test_i2_completed_needs_a_report_outcome() -> None:
    with pytest.raises(ValueError, match="COMPLETED"):
        ops.status_of("COMPLETED", None)
    assert ops.status_of("COMPLETED", "partial") == "partial"


# A11-5 -------------------------------------------------------------------------------------------------------------


class _RateLimited:
    """A stand-in for live ACQUIRE whose capture failed retryably after a Retry-After instant (no network)."""

    def __init__(self, not_before: datetime) -> None:
        self.not_before, self.calls = not_before, 0

    def __call__(self, req: StepRequest) -> Failed:
        self.calls += 1
        return Failed("HTTP_RATE_LIMITED", detail="SYNTHETIC", not_before=self.not_before)


def test_a11_5_running_and_waiting_is_blocked(tmp_path: Path, index: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    later = (datetime.now(UTC) + timedelta(hours=1)).replace(microsecond=0)
    fake = _RateLimited(later)
    monkeypatch.setattr(ops, "integration_for", lambda request, locators=None: Integration(live=fake))
    root = S8.memory_root(tmp_path)
    started = time.monotonic()
    with T.offline():
        code, value = T.run_json("run", "--wiki", "en", "--revision", "1372543632", "--index", index,
                                 "--memory-root", root)  # fmt: skip
    res = value["result"]
    assert (code, value["status"], res["lifecycle"]) == (8, "blocked", "RUNNING")
    assert res["next"]["action"] == "wait" and res["next"]["step"] == "ACQUIRE"
    assert datetime.fromisoformat(res["next"]["not_before"].replace("Z", "+00:00")) == later
    assert res["next"]["not_before"].endswith("Z")  # UF-07: one timestamp format
    acquire = next(s for s in res["steps"] if s["step"] == "ACQUIRE")
    assert (acquire["state"], acquire["not_before"]) == ("failed_retryable", res["next"]["not_before"]), acquire
    key = res["investigation_key"]
    before = (root / key / "journal.jsonl").read_bytes()
    with T.offline():
        for command in ("resume", "show", "verify"):
            code, value = T.run_json(command, "--memory-root", root, "--key", key)
            assert (code, value["status"], value["result"]["lifecycle"]) == (8, "blocked", "RUNNING"), command
        assert T.run_cli("checkpoint", "--memory-root", root, "--key", key)[0] == 8
    code, value = T.run_json("export", "--memory-root", root, "--key", key, "--out", tmp_path / "x")
    assert code == 8 and value["error"]["code"] == "EXPORT_REFUSED" and not (tmp_path / "x").exists()
    assert "RUNNING is not verified" in value["error"]["detail"]
    assert fake.calls == 1  # never restarted before not_before
    assert (root / key / "journal.jsonl").read_bytes() == before
    assert time.monotonic() - started < 60  # nothing slept until not_before


def test_a11_5_a_step_that_may_start_now_is_incomplete(tmp_path: Path, index: Path) -> None:
    """14 keeps one meaning: CREATED or RUNNING and a step may start now (here: created, never run)."""
    root = S8.memory_root(tmp_path)
    payload = S8.create(root, S8.request(S8.EN_OBOKATA, index, root))
    code, value = T.run_json("show", "--memory-root", root, "--key", payload["investigation_key"])
    assert (code, value["status"], value["result"]["lifecycle"], value["result"]["next"]["action"]) == (
        14, "incomplete", "CREATED", "start",
    )  # fmt: skip


# A11-6, C-04, C-06: relocation ---------------------------------------------------------------------------------------


def _content(inv: T.Inv) -> dict[str, Any]:
    with InvestigationMemory.open(inv.root, inv.key, writable=False) as mem:
        f = mem.view
        return {
            "content_digest": f.content_digest(),
            "claims": sorted(f.committed.claims),
            "report": [r["payload"] for r in f.committed_content() if r["kind"] == "report_recorded"],
        }


def test_a11_6_relocated_inputs_and_memory_root_give_the_same_content(tmp_path: Path, index: Path, en: T.Inv) -> None:
    """Other paths for the bundle, the index and the memory root: same investigation key, same C(J), claims, report
    and projection set. The paths stay in the creation record (provenance) but in no scientific digest."""
    bundle = tmp_path / "elsewhere" / "bundle"
    shutil.copytree(S8.EN_OBOKATA, bundle)
    moved = tmp_path / "elsewhere" / "index" / index.name
    moved.parent.mkdir()
    S8.replace_index(moved, index)
    with T.offline():
        other = T.Inv(tmp_path / "other-root", bundle, moved)
    assert other.code == en.code == 0
    assert other.key == en.key
    assert _content(other) == _content(en)


def test_a11_6_moved_inputs_are_named_with_locators(tmp_path: Path, index: Path) -> None:
    bundle = tmp_path / "b"
    shutil.copytree(S8.EN_OBOKATA, bundle)
    first = tmp_path / "i1" / index.name
    first.parent.mkdir()
    S8.replace_index(first, index)
    with T.offline():
        inv = T.Inv(tmp_path / "inv", bundle, first)
    assert inv.code == 0
    second = tmp_path / "i2" / index.name
    second.parent.mkdir()
    S8.replace_index(second, first)
    for path in (first, manifest_path_for(first)):
        path.unlink()
    shutil.move(bundle, tmp_path / "b2")
    with T.offline():
        code, value = T.run_json("verify", *_key_args(inv))
        assert (code, value["error"]["code"]) == (3, "INDEX_MISSING")  # MM 10.2: refused, not stale
        locate = ["--index", second, "--bundle", tmp_path / "b2"]
        code, value = T.run_json("verify", *_key_args(inv), *locate)
        assert (code, value["result"]["result"]) == (0, "passed")
        code, value = T.run_json("replay", *_key_args(inv), *locate)
        assert (code, value["result"]["result"]) == (0, "reproduced")
        code, value = T.run_json("show", *_key_args(inv), *locate)
        assert code == 0 and value["result"]["next"]["action"] == "terminal"
        code, _ = T.run_json("export", *_key_args(inv), *locate, "--out", tmp_path / "x")
        assert code == 0 and (tmp_path / "x" / "export.json").is_file()
        code, _ = T.run_json("resume", *_key_args(inv), *locate)
        assert code == 0


def test_c06_the_validate_output_names_no_path(en: T.Inv) -> None:
    with InvestigationMemory.open(en.root, en.key, writable=False) as mem:
        f = mem.view
        [end] = [r for r in f.records if r["kind"] == "step_succeeded" and r["step"] == "VALIDATE"]
        text = b"".join(mem.blobs.get(d) for d in end["payload"]["outputs"]).decode("utf-8")
    for path in (str(en.root), str(S8.EN_OBOKATA), "index_path", "memory_root", "bundle_path"):
        assert path not in text


# UF-03 and MM 10.2: show and refusals ---------------------------------------------------------------------------------


def _partial(tmp: Path, index: Path) -> tuple[Path, dict[str, Any], Path]:
    path = tmp / "idx" / index.name
    path.parent.mkdir(parents=True)
    S8.replace_index(path, index)
    root = S8.memory_root(tmp / "m")
    payload = S8.create(root, S8.request(S8.EN_OBOKATA, path, root))
    S8.run_until(root, payload, Integration(), "LOOKUP")
    return root, payload, path


def test_uf03_show_names_the_stale_transition_resume_takes(tmp_path: Path, index: Path) -> None:
    root, payload, path = _partial(tmp_path, index)
    key = payload["investigation_key"]
    S8.replace_index(path, S8.build_index(tmp_path / "other", S8.RW_FEWER))
    before = (root / key / "journal.jsonl").read_bytes()
    code, value = T.run_json("show", "--memory-root", root, "--key", key)
    nxt = value["result"]["next"]
    assert (code, value["status"], nxt["action"], nxt["rule"], nxt["changed"]) == (
        11,
        "stale",
        "stale",
        "T-STALE",
        ["index"],
    )
    assert (root / key / "journal.jsonl").read_bytes() == before  # show wrote nothing
    code, value = T.run_json("resume", "--memory-root", root, "--key", key)
    assert (code, value["result"]["lifecycle"]) == (11, "STALE")


def test_mm10_2_an_unverifiable_index_is_refused_everywhere(tmp_path: Path, index: Path) -> None:
    root, payload, path = _partial(tmp_path, index)
    key = payload["investigation_key"]
    manifest_path_for(path).unlink()
    before = (root / key / "journal.jsonl").read_bytes()
    code, value = T.run_json("show", "--memory-root", root, "--key", key)
    assert code == 14 and value["result"]["next"] == {
        **value["result"]["next"], "action": "refused", "rule": "MM 10.2", "code": "INDEX_CORRUPT",
    }  # fmt: skip
    code, value = T.run_json("resume", "--memory-root", root, "--key", key)
    assert (code, value["error"]["code"]) == (3, "INDEX_CORRUPT")
    assert (root / key / "journal.jsonl").read_bytes() == before


# B-05, B-06/SD-04, SD-06: opening ------------------------------------------------------------------------------------


def test_b05_run_of_an_existing_investigation_opens_it_read_only_first(
    tmp_path: Path, en: T.Inv, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``run`` of an existing key never goes through ``InvestigationMemory.create`` (which opens writable and would
    repair a torn tail before the workflow check, D-044); a different creation payload is refused, nothing changed."""
    inv = en
    request = dict(inv.request)
    before = (inv.dir / "journal.jsonl").read_bytes()

    def no_create(*a: Any, **k: Any) -> Any:
        raise AssertionError("create called for an existing investigation")

    monkeypatch.setattr(ops.InvestigationMemory, "create", no_create)
    with T.offline():
        out, code = ops.run(request)
    assert code == 0 and out["investigation_key"] == inv.key
    other = {**request, "index_path": str(tmp_path / "elsewhere.sqlite")}  # same key, another creation payload
    assert ops.created_for(other)["investigation_key"] == inv.key
    with pytest.raises(ops.OperationError) as exc:
        ops.run(other)
    assert (exc.value.status, exc.value.code) == ("invalid", "INVESTIGATION_REQUEST_DIFFERS")
    assert (inv.dir / "journal.jsonl").read_bytes() == before


def test_b06_an_unsafe_investigation_directory_is_corrupt_not_absent(tmp_path: Path, en: T.Inv) -> None:
    inv = en.copy(tmp_path)
    real = inv.root / (inv.key + ".real")
    os.rename(inv.dir, real)
    os.symlink(real, inv.dir)
    code, value = T.run_json("show", *_key_args(inv))
    assert (code, value["status"], value["error"]["code"]) == (12, "corrupt", "INVESTIGATION_UNSAFE")
    os.unlink(inv.dir)
    code, value = T.run_json("show", *_key_args(inv))
    assert (code, value["error"]["code"]) == (4, "INVESTIGATION_NOT_FOUND")


@pytest.mark.parametrize("name", ["lock", "journal.jsonl"])
def test_sd06_a_hard_linked_lock_or_journal_is_refused(tmp_path: Path, en: T.Inv, name: str) -> None:
    inv = en.copy(tmp_path)
    outside = tmp_path / "outside"
    os.link(inv.dir / name, outside)
    saved = outside.read_bytes()
    for command in ("show", "resume"):
        code, _ = T.run_json(command, *_key_args(inv))
        assert code == 12, command
    assert outside.read_bytes() == saved


# B-08, B-09: the report graph ----------------------------------------------------------------------------------------


def test_b08_a_report_listing_a_claim_twice_is_refused(tmp_path: Path, en: T.Inv) -> None:
    inv = en.copy(tmp_path)

    def twice(m: dict[str, Any], put: Any) -> None:
        """The last claim listed again, at a later unit offset (so the order check passes) with the counts adjusted:
        only the duplicate claim id gives it away (Reviewer B's experiment)."""
        [ref] = m["components"]["claims"]["chunks"]
        chunk = json.loads((inv.dir / "blobs" / ref["chunk"]).read_bytes())
        dup = json.loads(json.dumps(chunk["items"][-1]))
        dup["unit"]["byte_start"] += 1_000_000
        dup["unit"]["byte_end"] += 1_000_000
        chunk["items"] = [*chunk["items"], dup]
        ref["chunk"], ref["count"] = put(chunk), len(chunk["items"])
        m["components"]["claims"]["count"] += 1
        summary = m["article_summary"]
        summary["claims_by_class"][dup["claim"]["class"]] += 1
        summary["open_questions"] += dup["question"] is not None

    assert not T.forge_report(inv.root, inv.key, manifest=twice)  # Memory refuses it on open
    with (
        pytest.raises(CorruptInvestigation, match="listed twice"),
        InvestigationMemory.open(inv.root, inv.key, writable=False),
    ):
        pass
    code, value = T.run_json("verify", *_key_args(inv))
    assert (code, value["result"]["result"]) == (12, "corrupt")


def test_b09_report_chunks_are_referenced_blobs(en: T.Inv) -> None:
    with InvestigationMemory.open(en.root, en.key, writable=False) as mem:
        f = mem.view
        manifest = json.loads(mem.blobs.get(en.report_record()["report"]))
        chunks = {c["chunk"] for comp in manifest["components"].values() for c in comp.get("chunks", [])}
        assert chunks and chunks <= f.referenced_blobs()


# UF-01, UF-08, UF-09: v1 lossy points ---------------------------------------------------------------------------------


def _bodies(inv: T.Inv, date: Any) -> list[dict[str, Any]]:
    """The v1 bodies of ``inv`` with every deciding lookup's retraction date replaced by ``date(claim_id, old)``."""
    entries, deciding, ctx = T.projection_inputs(inv)
    changed = {}
    for cid, original in deciding.items():
        obs = json.loads(json.dumps(original))
        projection = obs["result"]["projection"]
        value = date(cid, projection.get("retraction_date"))
        if value is None:
            projection.pop("retraction_date", None)
        else:
            projection["retraction_date"] = value
        changed[cid] = obs
    return projections.build_bodies(entries, lambda c: changed[c["claim_id"]], **ctx)[1]


def _codes(body: dict[str, Any]) -> list[str]:
    return [line.split(":", 1)[0] for line in body["limitations"]]


def test_uf01_the_date_lossy_point_is_only_for_dates_that_differ(en: T.Inv) -> None:
    some = {"status": "known", "value": "2014-07-02", "provenance": []}
    for body in _bodies(en, lambda cid, old: None):
        assert "retraction_date" not in body["subject_paper"] and "V1_DATE_NOT_UNIFORM" not in _codes(body)
    for body in _bodies(en, lambda cid, old: some):
        assert body["subject_paper"]["retraction_date"] == some and "V1_DATE_NOT_UNIFORM" not in _codes(body)
    # Two contributing claims of one work (a second citation of the first positive claim's work): only some state a
    # date, or they state different dates.
    entries, deciding, ctx = T.projection_inputs(en)
    first = next(e for e in entries if e["claim"]["claim_id"] in deciding)
    twin = json.loads(json.dumps(first))
    twin["claim"]["claim_id"] = "f" * 64
    twin["unit"] = {
        **twin["unit"],
        "unit_id": twin["unit"]["unit_id"] + "-twin",
        "byte_start": twin["unit"]["byte_start"] + 1,
    }
    base = deciding[first["claim"]["claim_id"]]
    for twin_date, first_date in ((None, some), ({**some, "value": "2015-01-01"}, some)):
        a, b = json.loads(json.dumps(base)), json.loads(json.dumps(base))
        a["result"]["projection"]["retraction_date"] = first_date
        b["result"]["projection"].pop("retraction_date", None)
        if twin_date is not None:
            b["result"]["projection"]["retraction_date"] = twin_date
        obs = {**deciding, first["claim"]["claim_id"]: a, "f" * 64: b}
        bodies = projections.build_bodies([*entries, twin], lambda c, o=obs: o[c["claim_id"]], **ctx)[1]
        [body] = [x for x in bodies if len(x["citations"]) == 2]
        assert "retraction_date" not in body["subject_paper"] and "V1_DATE_NOT_UNIFORM" in _codes(body)


def test_uf08_uf09_v1_records_state_the_article_level_and_link_limits(en: T.Inv, tmp_path: Path) -> None:
    code, _ = T.run_json("export", *_key_args(en), "--out", tmp_path / "x")
    assert code == 0
    records = [json.loads(p.read_bytes()) for p in sorted((tmp_path / "x" / "v1").glob("*.json"))]
    assert records
    for r in records:
        codes = [line.split(":", 1)[0] for line in r["limitations"]]
        assert "V1_ARTICLE_LEVEL_STATEMENTS" in codes
        assert ("V1_EVENT_LINKS_NOT_STATED" in codes) == bool(r["events"])
        if "retraction_date" not in r["subject_paper"]:
            assert (
                "V1_DATE_NOT_UNIFORM" not in codes or r["subject_paper"]["retraction_status"]["status"] != "retracted"
            )


# UF-04, UF-05: results and envelopes ----------------------------------------------------------------------------------


def test_uf05_usage_and_internal_errors_have_the_json_envelope(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    code, out, _ = T.run_cli("show", "--memory-root", tmp_path, "--key", "nothex", "--format", "json")
    value = json.loads(out)
    assert (code, value["status"], value["exit_code"], value["error"]["code"]) == (2, "usage", 2, "USAGE")

    def boom(*a: Any, **k: Any) -> Any:
        raise RuntimeError("SYNTHETIC defect")

    monkeypatch.setattr(ops, "show", boom)
    code, out, _ = T.run_cli("show", "--memory-root", tmp_path, "--key", "0" * 64, "--format", "json")
    value = json.loads(out)
    assert (code, value["status"], value["error"]["code"]) == (1, "internal", "INTERNAL")


def test_uf10_the_exit_codes_are_in_the_help(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = T.run_cli("--help")
    assert code == 0
    for line in ("8     blocked", "11    stale", "14    incomplete", "(I-5)"):
        assert line in out, line


# A-02: DETECT replay compares content -------------------------------------------------------------------------------


@pytest.mark.parametrize("what", ["claim", "evidence"])
def test_a02_a_detect_rerun_with_other_content_under_the_same_ids_fails_verification(
    tmp_path: Path, en: T.Inv, monkeypatch: pytest.MonkeyPatch, what: str
) -> None:
    """The re-run gives the committed claim and evidence ids, but one value differs (a reason, or an evidence field
    that no id binds): VERIFY's ``DETECT_REPLAY`` fails and ``replay`` does not report ``reproduced``."""
    inv = en.copy(tmp_path)
    real = V.make_detect

    def altered(detector: Any) -> Any:
        inner = real(detector)

        def run(req: StepRequest) -> Any:
            res = inner(req)
            assert isinstance(res, Succeeded)
            kind = "claim_recorded" if what == "claim" else "evidence"
            records, done = [], False
            for r in res.records:
                payload = dict(r.payload)
                if r.kind == kind and not done:
                    if what == "claim":
                        payload["reasons"] = [*payload["reasons"], "SYNTHETIC_REASON"]
                    else:
                        payload["synthetic"] = True
                    done = True
                records.append(ContentRecord(r.kind, payload))
            assert done
            return dataclasses.replace(res, records=tuple(records))

        return run

    monkeypatch.setattr(V, "make_detect", altered)
    with T.offline():
        out, code = ops.verify(inv.root, inv.key)
        assert code == 5 and out["result"] == "failed"
        [check] = [c for c in out["checks"] if c["check"] == "DETECT_REPLAY"]
        expected = "with other content" if what == "claim" else "that is not committed"
        assert not check["passed"] and expected in check["detail"], check
        out, code = ops.replay(inv.root, inv.key)
        assert out["result"] != "reproduced" and code != 0


# C-09: a symlinked index ---------------------------------------------------------------------------------------------


def test_c09_a_symlinked_index_is_accepted_like_stage02_opens_it(tmp_path: Path, index: Path, en: T.Inv) -> None:
    link = tmp_path / "link" / index.name
    link.parent.mkdir()
    link.symlink_to(index)
    manifest_path_for(link).symlink_to(manifest_path_for(index))
    with T.offline():
        inv = T.Inv(tmp_path / "m", S8.EN_OBOKATA, link)
    assert inv.code == 0 and inv.key == en.key
    assert _content(inv) == _content(en)


# UF-06: text output -------------------------------------------------------------------------------------------------


def test_uf06_text_output_names_the_changed_identities(tmp_path: Path, index: Path) -> None:
    root, payload, path = _partial(tmp_path, index)
    S8.replace_index(path, S8.build_index(tmp_path / "other", S8.RW_FEWER))
    code, out, _ = T.run_cli("show", "--memory-root", root, "--key", payload["investigation_key"])
    assert code == 11
    assert 'changed: ["index"]' in out
