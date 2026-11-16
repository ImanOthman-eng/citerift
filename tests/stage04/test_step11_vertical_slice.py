"""Step 11: compact CI regressions of the vertical-slice contract (owner Step 11 items 6, 9 to 14, 23).

The full vertical slice (VS-1..VS-10 on the full pinned index, through the command line in child processes with no
network interface) is the evidence run ``docs/verification/stage-04/evidence/vertical-slice/run_vertical_slice.py``;
it is too slow for every CI run. These tests keep, with the attributed Step 8 subset index and the same production
command line, the contracts that no earlier test pins:

- VS-3 GFAJ-1: one work cited by two units is one positive work and one v1 projection (Step 10 finding I-1);
- VS-6: an article whose every keyed citation has no record gives only NOT_FOUND_IN_CHECKED_SOURCES, no projection,
  and the scoped not-found wording (the subset gives no_record for these keys, as the full index does: evidence run);
- VS-7: a schema-invalid Stage 03 extraction fails EXTRACT closed (ADAPTER_INCONSISTENT), no claim, no export;
- VS-8: a 429 with Retry-After from the SYNTHETIC-network live child is BLOCKED through the command line; a resume
  before ``not_before`` starts nothing and does not sleep, and nothing is exported (the restart at or after the
  instant needs real time to pass for the Stage 03 gate in the child: the evidence run waits for it; the controller
  rule is pinned with a clock by ``test_step8_live``);
- VS-9: a process killed by SIGKILL inside DETECT (after one entry batch, LOOKUP committed) resumes through the
  command line to the same ``C(J)``, report and projection set as an uninterrupted run, without re-running
  ACQUIRE..LOOKUP (the evidence run also kills before the adapter and after it, on VS-1);
- VS-10: ``verify`` and ``replay`` both report ``stale`` (exit 11) and name the changed identity, including a changed
  Stage 04 identity (Step 11 fix: ``verify`` gave ``failed`` there);
- I-2: a partial Stage 03 extraction is ``partial`` in every user-visible output (run, show, verify, export, v1).

Every investigation runs with every socket refused. Inputs are previously exposed design bundles (owner decision
D-5); the VS-6 bundle is a Stage 03 reserve bundle, never a holdout bundle.
"""

from __future__ import annotations

import dataclasses
import json
import shutil
import signal
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import step8_support as S8
import step10_support as T

from citerift.investigation import operations as ops
from citerift.investigation.adapters import plan as plan_module
from citerift.investigation.adapters.live import make_live_acquire
from citerift.investigation.adapters.plan import Integration
from citerift.wiki.fetch import FetchPolicy

pytestmark = pytest.mark.integration

EN_GFAJ1 = S8.REPO / "docs/verification/stage-03/demonstrations/bundles/en-1374726997"  # VS-3
AR_NOT_FOUND = S8.REPO / "docs/verification/stage-03/evaluation/capture/bundles/reserve/ar-9617858-a1"  # VS-6
FAKE_CHILD = [sys.executable, "-I", str(Path(__file__).resolve().parent / "live_fake_child.py")]
FORBIDDEN = ("clean", "safe", "not retracted", "no retracted citations")


@pytest.fixture(scope="module")
def index(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return S8.build_index(tmp_path_factory.mktemp("rw"))


@pytest.fixture(scope="module")
def en(tmp_path_factory: pytest.TempPathFactory, index: Path) -> T.Inv:
    return T.Inv(tmp_path_factory.mktemp("en"), S8.EN_OBOKATA, index)


@pytest.fixture(scope="module")
def mmr(tmp_path_factory: pytest.TempPathFactory, index: Path) -> T.Inv:
    return T.Inv(tmp_path_factory.mktemp("mmr"), S8.EN_MMR, index)


def _run(bundle: Path, index: Path, root: Path) -> tuple[int, dict[str, Any]]:
    with T.offline():
        return T.run_json("run", "--bundle", bundle, "--index", index, "--memory-root", root)


def _args(root: Path, key: str) -> list[str | Path]:
    return ["--memory-root", root, "--key", key]


def _export(root: Path, key: str, out: Path) -> tuple[int, list[dict[str, Any]]]:
    code, _ = T.run_json("export", *_args(root, key), "--out", out)
    records = [json.loads(p.read_bytes()) for p in sorted((out / "v1").glob("*.json"))] if out.exists() else []
    return code, records


def test_vs3_one_work_cited_twice_is_one_positive_work_and_one_projection(tmp_path: Path, index: Path) -> None:
    root = S8.memory_root(tmp_path)
    code, out = _run(EN_GFAJ1, index, root)
    res = out["result"]
    assert (code, res["lifecycle"]) == (0, "COMPLETED")
    assert res["claims_by_class"]["RETRACTED_WORK_CITED"] == 2 and res["claims_by_class"]["NOTICE_CITED"] == 2
    assert res["report"]["positive_works"] == 1 and res["report"]["projection_count"] == 1
    code, records = _export(root, res["investigation_key"], tmp_path / "x")
    assert code == 0 and len(records) == 1
    assert [c["identifiers"]["doi"] for c in records[0]["citations"]] == ["10.1126/science.1197258"] * 2


def test_vs6_only_no_record_keys_give_only_scoped_not_found(tmp_path: Path, index: Path) -> None:
    root = S8.memory_root(tmp_path)
    code, out = _run(AR_NOT_FOUND, index, root)
    res = out["result"]
    assert (code, res["lifecycle"], res["claims_by_class"]) == (0, "COMPLETED", {"NOT_FOUND_IN_CHECKED_SOURCES": 1})
    assert res["report"]["positive_works"] == 0 and res["report"]["projection_count"] == 0
    key = res["investigation_key"]
    code, show = T.run_json("show", *_args(root, key), "--claims")
    texts = [show["result"]["report"]["summary"], *(c["text"] for c in show["result"]["report"]["claims"])]
    assert any("No matching record was found in the checked sources." in t for t in texts)
    assert not any(w in t.lower() for t in texts for w in FORBIDDEN)
    code, records = _export(root, key, tmp_path / "x")
    assert code == 0 and records == []


def test_vs7_schema_invalid_extraction_fails_closed(
    tmp_path: Path, index: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from citerift.investigation.adapters import extract

    real = extract.extract_bundle

    def damaged(*args: Any, **kwargs: Any) -> dict[str, Any]:
        doc = real(*args, **kwargs)
        doc["unexpected_property"] = True  # SYNTHETIC: one property the extraction schema does not allow
        return doc

    monkeypatch.setattr(extract, "extract_bundle", damaged)
    root = S8.memory_root(tmp_path)
    code, out = _run(S8.EN_OBOKATA, index, root)
    res = out["result"]
    t = res["terminated_by"]
    assert (code, res["lifecycle"], t["step"], t["code"]) == (9, "FAILED", "EXTRACT", "ADAPTER_INCONSISTENT")
    key = res["investigation_key"]
    assert not [r for r in T.journal(root, key) if r["kind"] in ("candidate_result_batch_recorded", "report_recorded")]
    code, out = T.run_json("export", *_args(root, key), "--out", tmp_path / "x")
    assert (code, out["error"]["code"]) == (9, "EXPORT_REFUSED") and not (tmp_path / "x").exists()


def test_vs8_retry_after_is_blocked_and_nothing_starts_before_not_before(
    tmp_path: Path, index: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    live = make_live_acquire(FetchPolicy(), child=FAKE_CHILD, workroot=tmp_path / "acquire")
    monkeypatch.setattr(ops, "integration_for", lambda request: Integration(live=live))
    monkeypatch.setenv("CITERIFT_WIKI_NETWORK_LOCK", str(tmp_path / "gate.lock"))  # not the host-wide gate file
    monkeypatch.setenv("CITERIFT_FAKE_BUNDLE", str(S8.AR_OBOKATA))
    monkeypatch.setenv("CITERIFT_FAKE_MODE", "throttled:600")  # SYNTHETIC 429; longer than the Stage 03 deadline
    root = S8.memory_root(tmp_path)
    with T.offline():
        code, out = T.run_json("run", "--wiki", "ar", "--revision", "76190003", "--index", index, "--memory-root", root)
    res = out["result"]
    acquire = next(s for s in res["steps"] if s["step"] == "ACQUIRE")
    assert (code, res["lifecycle"], acquire["state"], acquire["attempts"]) == (8, "BLOCKED", "deferred", 1)
    not_before = datetime.fromisoformat(acquire["not_before"].replace("Z", "+00:00"))
    assert not_before > datetime.now(UTC) + timedelta(seconds=500)
    key = res["investigation_key"]
    before = (root / key / "journal.jsonl").read_bytes()
    monkeypatch.setenv("CITERIFT_FAKE_MODE", "replay")
    with T.offline():
        code, out = T.run_json("resume", *_args(root, key))
    assert code == 8 and (root / key / "journal.jsonl").read_bytes() == before  # nothing started, nothing slept
    code, _ = T.run_json("export", *_args(root, key), "--out", tmp_path / "x")
    assert code == 8 and not (tmp_path / "x").exists()


_KILL = """
import os, signal, sys
from citerift.investigation import cli, faults

def handler(name, context):
    if name == sys.argv[1] and context.get("step") == "DETECT":
        os.kill(os.getpid(), signal.SIGKILL)

faults.install(handler)
sys.exit(cli.main(sys.argv[2:]))
"""


def test_vs9_killed_during_detect_resumes_to_the_same_content(tmp_path: Path, index: Path, en: T.Inv) -> None:
    """A real process killed by SIGKILL inside DETECT, after one D-055 entry batch was written and LOOKUP committed;
    then ``resume`` through the command line: only DETECT and the steps after it run, and the content is the
    uninterrupted run's (``en``)."""
    root = S8.memory_root(tmp_path)
    argv = ["run", "--bundle", str(S8.EN_OBOKATA), "--index", str(index), "--memory-root", str(root)]
    point = "controller.after_entry_batch"
    p = subprocess.run([sys.executable, "-c", _KILL, point, *argv], capture_output=True, check=False)
    assert p.returncode == -signal.SIGKILL
    key = en.key
    before = T.journal(root, key)
    assert any(r["kind"] == "step_succeeded" and r["step"] == "LOOKUP" for r in before)
    assert any(r["kind"] == "candidate_result_batch_recorded" for r in before)  # uncommitted DETECT content
    assert not any(r["kind"] == "step_succeeded" and r["step"] == "DETECT" for r in before)
    assert T.run_json("show", *_args(root, key))[0] == 14  # incomplete
    with T.offline():
        code, out = T.run_json("resume", *_args(root, key))
    assert code == 0 and out["result"]["lifecycle"] == "COMPLETED"
    after = T.journal(root, key)
    assert {r["step"] for r in after[len(before) :] if r["kind"] == "step_started"} == {"DETECT", "ASSEMBLE", "VERIFY"}
    with ops.opened(root, key) as a, ops.opened(en.root, key) as b:
        assert a.view.content_digest() == b.view.content_digest()
    rec = next(r for r in after if r["kind"] == "report_recorded")["payload"]
    ref = en.report_record()
    assert (rec["report"], rec["projection_set"]) == (ref["report"], ref["projection_set"])


def test_vs10_verify_and_replay_name_each_changed_identity(
    tmp_path: Path, index: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One identity changed at a time, then restored. The Stage 04 case is the Step 11 fix (``verify`` said
    ``failed``, exit 5, because ASSEMBLE re-run under the new identity gives another report)."""
    from citerift.investigation.adapters import extract

    bundle, idx = tmp_path / "bundle", tmp_path / "index.sqlite"
    shutil.copytree(S8.EN_OBOKATA, bundle)
    shutil.copyfile(index, idx)
    root = S8.memory_root(tmp_path / "m")
    key = _run(bundle, idx, root)[1]["result"]["investigation_key"]
    journal = (root / key / "journal.jsonl").read_bytes()
    profile = extract.load_profile

    def check(change: str) -> None:
        with T.offline():
            rc, rp = T.run_json("replay", *_args(root, key))
            vc, vf = T.run_json("verify", *_args(root, key))
        assert (rc, rp["result"]["result"], rp["result"]["changed"]) == (11, "stale", [change])
        assert (vc, vf["result"]["result"], vf["result"]["stale"]["changed"]) == (11, "stale", [change])
        assert (root / key / "journal.jsonl").read_bytes() == journal

    shutil.move(bundle, tmp_path / "saved")
    shutil.copytree(S8.AR_OBOKATA, bundle)  # another capture at the same path
    check("root")
    shutil.rmtree(bundle)
    shutil.move(tmp_path / "saved", bundle)
    with monkeypatch.context() as mp:
        mp.setattr(extract, "load_profile", lambda: dataclasses.replace(profile(), digest="0" * 64))
        check("extraction")
    with open(idx, "ab") as f:
        f.write(b"\0" * 4096)
    check("index")
    shutil.copyfile(index, idx)
    with monkeypatch.context() as mp:
        mp.setattr(plan_module, "STAGE04_IDENTITY", {**plan_module.STAGE04_IDENTITY, "schema_version": "2.0.1"})
        check("stage04")
    assert T.run_json("replay", *_args(root, key))[1]["result"]["result"] == "reproduced"


def test_i2_partial_extraction_is_partial_in_every_user_visible_output(mmr: T.Inv, tmp_path: Path) -> None:
    """Step 10 finding I-2: ``workflow.outcome`` does not read the extraction status; the outputs a user sees do (run
    and ``verify`` status: ``test_step10_cli.test_exit_6_partial``; here ``show``, the export and its v1 records)."""
    assert mmr.code == 6 and mmr.out["status"] == "partial" and mmr.out["report"]["outcome"] == "partial"
    with ops.opened(mmr.root, mmr.key) as mem:
        extraction = next(
            json.loads(mem.blobs.get(r["payload"]["blob"]))
            for r in mem.view.logical
            if r["kind"] == "observation_recorded" and r["payload"]["obs_kind"] == "extraction"
        )
    assert extraction["status"] == "partial"
    code, out = T.run_json("show", *_args(mmr.root, mmr.key))
    assert (code, out["status"], out["result"]["report"]["outcome"]) == (6, "partial", "partial")
    code, records = _export(mmr.root, mmr.key, tmp_path / "x")
    assert code == 6 and records and all(r["status"] == "partial" for r in records)
    assert json.loads((tmp_path / "x" / "export.json").read_bytes())["outcome"] == "partial"
