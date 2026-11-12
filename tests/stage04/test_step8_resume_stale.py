"""Stage 04 Step 8: crash and resume, STALE on changed inputs, and VERIFY failing closed, with the real adapters
(owner Step 8 items 14, 17 and 18).

The VERIFY tests replay the real VERIFY request of a completed investigation with one input changed at the reader
(a changed source byte, a lookup missing an event, a shifted unit span, a detector or engine that does not replay).
In a real investigation such a blob cannot exist, because Memory refuses bytes that do not hash to their name; the
tests exercise each check's own logic, which is what guards against an adapter that commits wrong content.

Real bundles and the attributed Retraction Watch subset index; DETECT is the SYNTHETIC test detector of
``step8_support`` (not dt-1).
"""

from __future__ import annotations

import dataclasses
import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
import step8_support as S8

from citerift.investigation.adapters import Failed, StepRequest, Succeeded
from citerift.investigation.adapters import extract as extract_module
from citerift.investigation.adapters import plan as plan_module
from citerift.investigation.adapters.detect import DetectInput, Detection
from citerift.investigation.adapters.plan import STAGE04_IDENTITY, Integration
from citerift.investigation.adapters.verify import CHECKS, make_verify
from citerift.investigation.canonical import loads_blob
from citerift.investigation.controller import run_investigation
from citerift.investigation.memory import InvestigationMemory, created_payload
from citerift.investigation.schemas import BUNDLE_OBSERVATION, LOOKUP_PLAN
from citerift.retraction import policy
from citerift.wiki.extract import ExtractConfig
from citerift.wiki.profile import load_profile

pytestmark = pytest.mark.integration

HERE = Path(__file__).resolve().parent
DIE = 91


@pytest.fixture(scope="module")
def index(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return S8.build_index(tmp_path_factory.mktemp("rw"))


def _start(tmp: Path, bundle: Path, index: Path) -> tuple[Path, dict[str, Any]]:
    root = S8.memory_root(tmp)
    return root, S8.create(root, S8.request(bundle, index, root))


def _attempts(root: Path, payload: dict[str, Any]) -> dict[str, int]:
    with InvestigationMemory.open(root, payload["investigation_key"], writable=False) as mem:
        return {s: len(a) for s, a in mem.view.attempts.items()}


def _content(root: Path, payload: dict[str, Any]) -> tuple[set[str], str]:
    """The claim ids and ``C(J)`` (MM 7.3: the committed content, without execution data) of an investigation."""
    recs, _ = S8.committed(root, payload)
    with InvestigationMemory.open(root, payload["investigation_key"], writable=False) as mem:
        digest = mem.view.content_digest()
    return {r["payload"]["claim_id"] for r in recs if r["kind"] == "claim_recorded"}, digest


@pytest.fixture(scope="module")
def reference(tmp_path_factory: pytest.TempPathFactory, index: Path) -> tuple[set[str], str]:
    root, payload = _start(tmp_path_factory.mktemp("ref"), S8.AR_OBOKATA, index)
    assert S8.run(root, payload, S8.TEST_INTEGRATION).status == "NEEDS_RESOLUTION"
    return _content(root, payload)


# Crash and resume (item 17) ---------------------------------------------------------------------------------------

_CHILD = """
import os, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import step8_support as S8
root, bundle, index, step = Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]), sys.argv[5]
payload = S8.create(root, S8.request(bundle, index, root))
adapters = S8.TEST_INTEGRATION.adapters()
real = adapters[step]
def die_after(req):
    real(req)          # the step's work is done, nothing of it is committed yet
    os._exit(91)       # the process dies inside the step
adapters[step] = die_after
from citerift.investigation.canonical import loads_blob
from citerift.investigation.controller import run_investigation
run_investigation(root, payload["investigation_key"], adapters, S8.TEST_INTEGRATION.environment(payload))
sys.exit(3)
"""


@pytest.mark.parametrize("step", ["ACQUIRE", "EXTRACT", "LOOKUP", "DETECT", "VERIFY"])
def test_process_death_inside_a_step_resumes_without_repeating_committed_steps(
    tmp_path: Path, index: Path, reference: tuple[set[str], str], step: str
) -> None:
    root = S8.memory_root(tmp_path)
    child = subprocess.run(
        [sys.executable, "-c", _CHILD, str(HERE), str(root), str(S8.AR_OBOKATA), str(index), step],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert child.returncode == DIE, child.stderr[-2000:]
    payload = S8.create(root, S8.request(S8.AR_OBOKATA, index, root))
    result = S8.run(root, payload, S8.TEST_INTEGRATION)
    assert result.status == "NEEDS_RESOLUTION"
    attempts = _attempts(root, payload)
    order = ["VALIDATE", "ACQUIRE", "EXTRACT", "NORMALIZE", "LOOKUP", "DETECT", "ASSEMBLE", "VERIFY"]
    for s in order:
        assert attempts[s] == (2 if s == step else 1), (s, attempts)
    assert _content(root, payload) == reference  # the same claims and the same committed content C(J)


# STALE (item 18) -------------------------------------------------------------------------------------------------


def _stale_changed(root: Path, payload: dict[str, Any]) -> list[str]:
    with InvestigationMemory.open(root, payload["investigation_key"], writable=False) as mem:
        [stale] = [r["payload"] for r in mem.view.records if r["kind"] == "stale_detected"]
    return list(stale["changed"])


def test_a_replaced_bundle_is_stale(tmp_path: Path, index: Path) -> None:
    path = tmp_path / "bundle"
    shutil.copytree(S8.AR_OBOKATA, path)
    root, payload = _start(tmp_path / "m", path, index)
    S8.run_until(root, payload, S8.TEST_INTEGRATION, "LOOKUP")
    shutil.rmtree(path)
    shutil.copytree(S8.EN_OBOKATA, path)  # another capture at the same path
    assert S8.run(root, payload, S8.TEST_INTEGRATION).status == "STALE"
    assert _stale_changed(root, payload) == ["root"]


def test_an_unreadable_bundle_at_the_path_is_stale(tmp_path: Path, index: Path) -> None:
    path = tmp_path / "bundle"
    shutil.copytree(S8.AR_OBOKATA, path)
    root, payload = _start(tmp_path / "m", path, index)
    S8.run_until(root, payload, S8.TEST_INTEGRATION, "EXTRACT")
    (path / "capture.json").write_bytes(b"{}")
    assert S8.run(root, payload, S8.TEST_INTEGRATION).status == "STALE"
    assert _stale_changed(root, payload) == ["root"]


def test_a_changed_extraction_configuration_is_stale(tmp_path: Path, index: Path) -> None:
    root, payload = _start(tmp_path, S8.AR_OBOKATA, index)
    S8.run_until(root, payload, S8.TEST_INTEGRATION, "NORMALIZE")
    other = Integration(extract_config=ExtractConfig(max_refs=19_999), detector=S8.synthetic_detector)
    assert S8.run(root, payload, other).status == "STALE"
    assert _stale_changed(root, payload) == ["extraction"]


def test_a_changed_stage03_profile_is_stale(tmp_path: Path, index: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The Stage 03 profile is part of the extraction identity (SPEC 10.3): another profile digest is STALE."""
    root, payload = _start(tmp_path, S8.AR_OBOKATA, index)
    S8.run_until(root, payload, S8.TEST_INTEGRATION, "NORMALIZE")
    other = dataclasses.replace(load_profile(), digest="0" * 64)
    monkeypatch.setattr(extract_module, "load_profile", lambda: other)
    assert S8.run(root, payload, S8.TEST_INTEGRATION).status == "STALE"
    assert _stale_changed(root, payload) == ["extraction"]


def test_a_replaced_index_is_stale(tmp_path: Path, index: Path) -> None:
    path = tmp_path / "index.sqlite"
    shutil.copyfile(index, path)
    root, payload = _start(tmp_path / "m", S8.AR_OBOKATA, path)
    S8.run_until(root, payload, S8.TEST_INTEGRATION, "LOOKUP")
    with open(path, "r+b") as f:  # same file, other bytes: the recorded SHA-256 no longer holds
        f.seek(0, os.SEEK_END)
        f.write(b"\0" * 4096)
    assert S8.run(root, payload, S8.TEST_INTEGRATION).status == "STALE"
    assert _stale_changed(root, payload) == ["index"]


def test_a_changed_lookup_policy_is_stale(tmp_path: Path, index: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, payload = _start(tmp_path, S8.AR_OBOKATA, index)
    S8.run_until(root, payload, S8.TEST_INTEGRATION, "LOOKUP")
    monkeypatch.setattr(policy, "POLICY_VERSION", policy.POLICY_VERSION + "-changed")
    assert S8.run(root, payload, S8.TEST_INTEGRATION).status == "STALE"
    assert _stale_changed(root, payload) == ["index"]


def test_a_changed_lookup_budget_is_another_investigation(tmp_path: Path, index: Path) -> None:
    """Owner decision D-057: the lookup evidence budget is configuration, so part of config_digest and of the
    investigation key. The same request with the same budget is the same investigation; another budget is another
    investigation, never a STALE transition of the first: the first journal is not touched and neither is STALE."""
    root = S8.memory_root(tmp_path)
    req_a = S8.request(S8.AR_OBOKATA, index, root)
    capture = S8.open_bundle_capture(S8.AR_OBOKATA)
    again = created_payload(
        S8.request(S8.AR_OBOKATA, index, root), dict(STAGE04_IDENTITY), bundle_capture_sha256=capture
    )
    a = S8.create(root, req_a)
    assert (again["config_digest"], again["investigation_key"]) == (a["config_digest"], a["investigation_key"])
    assert S8.run(root, a, S8.TEST_INTEGRATION).status == "NEEDS_RESOLUTION"
    journal_a = root / a["investigation_key"] / "journal.jsonl"
    before = journal_a.read_bytes()
    b = S8.create(root, S8.request(S8.AR_OBOKATA, index, root, budget=1024))
    assert b["config_digest"] != a["config_digest"] and b["investigation_key"] != a["investigation_key"]
    assert S8.run(root, b, S8.TEST_INTEGRATION).status != "STALE"
    assert S8.run(root, a, S8.TEST_INTEGRATION).status == "NEEDS_RESOLUTION"  # resumed after the other exists
    assert journal_a.read_bytes() == before
    for payload in (a, b):
        with InvestigationMemory.open(root, payload["investigation_key"], writable=False) as mem:
            assert [r for r in mem.view.records if r["kind"] == "stale_detected"] == []


@pytest.mark.parametrize(
    "change",
    [
        lambda: Integration(detector=S8.synthetic_detector, stage04={**STAGE04_IDENTITY, "schema_version": "2.0.1"}),
        lambda: Integration(detector=S8.synthetic_detector, stage04={**STAGE04_IDENTITY, "table_version": "dt-2"}),
    ],
    ids=["schema", "table"],
)
def test_a_changed_stage04_schema_or_plan_is_stale(
    tmp_path: Path, index: Path, change: Callable[[], Integration]
) -> None:
    root, payload = _start(tmp_path, S8.AR_OBOKATA, index)
    S8.run_until(root, payload, S8.TEST_INTEGRATION, "EXTRACT")
    assert S8.run(root, payload, change()).status == "STALE"
    assert _stale_changed(root, payload) == ["stage04"]


def test_a_changed_integration_schema_is_stale(tmp_path: Path, index: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, payload = _start(tmp_path, S8.AR_OBOKATA, index)
    S8.run_until(root, payload, S8.TEST_INTEGRATION, "EXTRACT")
    monkeypatch.setitem(plan_module.INTEGRATION_SCHEMAS, "lookup-plan", "1.0.1")
    assert S8.run(root, payload, S8.TEST_INTEGRATION).status == "STALE"
    assert _stale_changed(root, payload) == ["stage04"]


# VERIFY fails closed (item 14) ----------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def verify_request(tmp_path_factory: pytest.TempPathFactory, index: Path) -> Iterator[StepRequest]:
    """The real VERIFY request of a completed real investigation (Obokata en), captured as the controller made it."""
    seen: list[StepRequest] = []
    adapters = S8.TEST_INTEGRATION.adapters()
    real = adapters["VERIFY"]

    def capture(req: StepRequest) -> Any:
        seen.append(req)
        return real(req)

    root, payload = _start(tmp_path_factory.mktemp("v"), S8.EN_OBOKATA, index)
    adapters["VERIFY"] = capture
    result = run_investigation(root, payload["investigation_key"], adapters, S8.TEST_INTEGRATION.environment(payload))
    assert result.status == "COMPLETED"
    # The captured request's readers are bound to the closed run; rebind them to the investigation opened read-only.
    with InvestigationMemory.open(root, payload["investigation_key"], writable=False) as mem:
        yield dataclasses.replace(seen[-1], read_blob=lambda d: loads_blob(mem.blobs.get(d)), read_bytes=mem.blobs.get)


VERIFY = make_verify(S8.synthetic_detector, STAGE04_IDENTITY)


def _blob_of(req: StepRequest, schema: str) -> tuple[str, dict[str, Any]]:
    for step_outputs in req.inputs.values():
        for d in step_outputs:
            value = req.read_blob(d)
            if isinstance(value, dict) and value.get("schema") == schema:
                return d, value
    raise AssertionError(schema)


def _with_blob(req: StepRequest, digest: str, value: Any) -> StepRequest:
    read = req.read_blob
    return dataclasses.replace(req, read_blob=lambda d: value if d == digest else read(d))


def _failed_check(result: Any) -> str:
    assert isinstance(result, Failed) and result.code == "VERIFY_FAILED", result
    return str(result.reason)


def test_verify_passes_all_fourteen_checks_on_real_content(verify_request: StepRequest) -> None:
    result = VERIFY(verify_request)
    assert isinstance(result, Succeeded)
    [rec] = result.records
    assert [c["check"] for c in rec.payload["checks"]] == list(CHECKS)


def test_verify_fails_on_a_changed_source_artifact(verify_request: StepRequest) -> None:
    _, manifest = _blob_of(verify_request, BUNDLE_OBSERVATION)
    src = manifest["source"]["artifact"]
    read = verify_request.read_bytes
    data = bytearray(read(src))
    data[100] ^= 1
    req = dataclasses.replace(verify_request, read_bytes=lambda d: bytes(data) if d == src else read(d))
    assert _failed_check(VERIFY(req)) == "STAGE03_CAPTURE_VERIFIED"


def test_verify_fails_on_a_lookup_missing_an_event(verify_request: StepRequest) -> None:
    _, plan = _blob_of(verify_request, LOOKUP_PLAN)
    entry = next(e for e in plan["lookups"] if verify_request.read_blob(e["observation"])["events"])
    obs = dict(verify_request.read_blob(entry["observation"]))
    obs["events"] = obs["events"][1:]
    result = VERIFY(_with_blob(verify_request, entry["observation"], obs))
    assert isinstance(result, Failed) and result.code == "VERIFY_FAILED"
    assert "BOUNDED_LOOKUP_PROVENANCE" in result.detail


def test_verify_fails_when_detect_does_not_replay(verify_request: StepRequest) -> None:
    def other(inp: DetectInput) -> Detection:
        out = S8.synthetic_detector(inp)
        return Detection(out.evidence, out.claims[:-1], out.identity)

    result = make_verify(other, STAGE04_IDENTITY)(verify_request)
    assert _failed_check(result) == "DETECT_REPLAY"


def test_verify_fails_on_a_report_that_does_not_replay(verify_request: StepRequest) -> None:
    """A committed report that ASSEMBLE would not give now (here: VERIFY holds another engine identity than the one
    the report was assembled with) fails ASSEMBLE_REPLAY. A blob whose bytes changed cannot reach VERIFY: Memory
    refuses any blob that does not hash to its name."""
    other = {**STAGE04_IDENTITY, "engine_version": STAGE04_IDENTITY["engine_version"] + "+other"}
    assert _failed_check(make_verify(S8.synthetic_detector, other)(verify_request)) == "ASSEMBLE_REPLAY"


def test_verify_fails_on_an_unanchored_unit(verify_request: StepRequest) -> None:
    ext_digest = next(
        r["payload"]["blob"]
        for r in verify_request.committed
        if r["kind"] == "observation_recorded" and r["payload"]["obs_kind"] == "extraction"
    )
    doc = dict(verify_request.read_blob(ext_digest))
    units = [dict(u) for u in doc["units"]]
    units[0] = {**units[0], "source": {**units[0]["source"], "byte_end": units[0]["source"]["byte_end"] - 1}}
    doc["units"] = units
    result = VERIFY(_with_blob(verify_request, ext_digest, doc))
    assert isinstance(result, Failed) and result.code == "VERIFY_FAILED"
    assert "D043_UNIT_ANCHORS" in result.detail


def test_a_deleted_raw_blob_is_corruption(tmp_path: Path, index: Path) -> None:
    """IF-7 / M-3: Memory checks every retained raw blob on open; a missing one is CORRUPT, never a re-read."""
    root, payload = _start(tmp_path, S8.EN_OBOKATA, index)
    assert S8.run(root, payload, S8.TEST_INTEGRATION).status == "COMPLETED"
    _, blobs = S8.committed(root, payload)
    [manifest] = [v for v in blobs.values() if isinstance(v, dict) and v.get("schema") == BUNDLE_OBSERVATION]
    (root / payload["investigation_key"] / "blobs" / manifest["source"]["artifact"]).unlink()
    assert S8.run(root, payload, S8.TEST_INTEGRATION).status == "CORRUPT"
