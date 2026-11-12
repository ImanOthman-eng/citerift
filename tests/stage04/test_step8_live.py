"""Stage 04 Step 8: live ACQUIRE under the D-042 bound, the supervisor, and the Retry-After proof (owner items 4, 5, 15
and 17).

No test reaches a network. The child is the production child module (``live_child.main``) with the Stage 03 transport
replaced by ``live_fake_child.py`` (SYNTHETIC network: a replay of a real retained bundle's recorded responses, or a
stall). The bound is injected (G-6): 1.5 s instead of 240 s. The parent process refuses sockets.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from pathlib import Path
from typing import Any

import pytest
import step8_support as S8

from citerift.investigation import workflow
from citerift.investigation.adapters import Deferred, Failed, StepRequest, Succeeded
from citerift.investigation.adapters.live import (
    bound_for,
    earlier_attempts,
    make_live_acquire,
    policy_digest,
    side_channel,
)
from citerift.investigation.adapters.plan import STAGE04_IDENTITY, Integration
from citerift.investigation.adapters.supervise import supervise, tree
from citerift.investigation.controller import run_investigation
from citerift.investigation.memory import InvestigationMemory, created_payload
from citerift.wiki.fetch import FetchPolicy

pytestmark = pytest.mark.integration

HERE = Path(__file__).resolve().parent
FAKE = [sys.executable, "-I", str(HERE / "live_fake_child.py")]
POLICY = FetchPolicy(min_interval_s=0, max_attempts=2, op_timeout_s=2, deadline_s=5, backoff_s=0.05)
T_ACQ_MS = 1500


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("CITERIFT_WIKI_NETWORK_LOCK", str(tmp_path / "gate.lock"))
    monkeypatch.setenv("CITERIFT_FAKE_BUNDLE", str(S8.AR_OBOKATA))
    monkeypatch.setenv("CITERIFT_FAKE_PIDS", str(tmp_path / "pids.json"))
    monkeypatch.setenv("CITERIFT_FAKE_CHILD_PID", str(tmp_path / "child.pid"))
    S8.NoNetwork(monkeypatch)
    return tmp_path


def live_request(root: Path, index: Path) -> dict[str, Any]:
    req = S8.request(S8.AR_OBOKATA, index, root)
    req["mode"] = "live_capture"
    req["subject"] = {"type": S8.SUBJECT, "wiki": "ar", "revision_id": 76190003}
    req["config"]["fetch_policy_sha256"] = policy_digest(POLICY)
    req["config"]["live_acquire_bound"] = bound_for(POLICY)
    return req


def step_request(tmp: Path, attempt: int = 1, now: datetime | None = None) -> StepRequest:
    fields: dict[str, Any] = dict.fromkeys(StepRequest.__dataclass_fields__)
    fields.update(
        step="ACQUIRE",
        attempt=attempt,
        live=True,
        request=live_request(tmp, tmp / "index.sqlite"),
        request_key={"wiki": "ar", "revision_id": 76190003},
        investigation={"investigation_key": "0" * 64, "investigation_id": "x"},
        now=now or datetime.now(UTC),
    )
    return StepRequest(**fields)


def acquire(tmp: Path, mode: str, monkeypatch: pytest.MonkeyPatch, **kw: Any) -> Any:
    monkeypatch.setenv("CITERIFT_FAKE_MODE", mode)
    return make_live_acquire(POLICY, child=FAKE, t_acq_ms=T_ACQ_MS, workroot=tmp / "acquire", **kw)


def _alive(pid: int) -> bool:
    try:
        with open(f"/proc/{pid}/stat") as f:
            return f.read().rsplit(")", 1)[1].split()[0] not in ("Z", "X")
    except OSError:
        return False


# The supervisor (item 4) -----------------------------------------------------------------------------------------


def _sup(tmp: Path, code: str, t: float) -> Any:
    return supervise([sys.executable, "-c", code], t_acq_s=t, cwd=tmp, stdout=tmp / "out", stderr=tmp / "err")


def test_a_child_inside_the_bound_is_not_killed(tmp_path: Path) -> None:
    run = _sup(tmp_path, "pass", 10)
    assert (run.returncode, run.timed_out, run.survivors, run.killed) == (0, False, (), ())


def test_the_bound_kills_and_reaps_the_child_and_measures_it(tmp_path: Path) -> None:
    t0 = time.monotonic()
    run = _sup(tmp_path, "import time; time.sleep(3600)", 0.5)
    took = time.monotonic() - t0
    assert run.timed_out and run.returncode is None and run.survivors == ()
    assert 500 <= run.elapsed_ms < 1500 and took < 3
    assert run.kill_ms is not None and run.reap_ms is not None and run.kill_ms < 1000 and run.reap_ms < 1000


def test_the_whole_tree_dies_including_a_descendant_that_left_the_session(tmp_path: Path) -> None:
    code = (
        "import json, subprocess, sys, time\n"
        "a = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(3600)'])\n"
        "b = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(3600)'], start_new_session=True)\n"
        f"open({str(tmp_path / 'pids')!r}, 'w').write(json.dumps([a.pid, b.pid]))\n"
        "time.sleep(3600)\n"
    )
    run = _sup(tmp_path, code, 1.5)
    pids = json.loads((tmp_path / "pids").read_text())
    assert run.timed_out and run.survivors == ()
    assert set(pids) <= set(run.killed)
    assert not any(_alive(p) for p in pids)


def test_a_process_left_in_the_session_after_a_normal_exit_is_killed_and_reported(tmp_path: Path) -> None:
    code = (
        "import subprocess, sys\n"
        "p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(3600)'])\n"
        f"open({str(tmp_path / 'pid')!r}, 'w').write(str(p.pid))\n"
    )
    run = _sup(tmp_path, code, 10)
    pid = int((tmp_path / "pid").read_text())
    assert run.returncode == 0 and pid in run.killed and run.survivors == ()
    assert not _alive(pid)


def test_tree_is_empty_for_a_session_with_no_process() -> None:
    assert tree(2**22 + 12345) == {}


# The live adapter (items 3, 4) -----------------------------------------------------------------------------------


def test_a_replayed_capture_is_retained_like_a_retained_bundle(env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result = acquire(env, "replay", monkeypatch)(step_request(env))
    assert isinstance(result, Succeeded)
    ident = result.root["subject"]["identity"]
    assert (ident["wiki"], ident["revision_id"], ident["page_id"]) == ("ar", 76190003, 10487829)
    source = (
        S8.AR_OBOKATA / "artifacts" / json.loads((S8.AR_OBOKATA / "capture.json").read_bytes())["source"]["artifact"]
    ).read_bytes()
    assert source in result.raw_blobs
    assert not (env / "acquire" / ("0" * 64)).exists()  # a success leaves nothing behind


def test_a_killed_attempt_returns_nothing_authoritative(env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Item 4: past T_acq the attempt is ACQUIRE_WALL_CLOCK_EXCEEDED with the bound and the elapsed time; no root, no
    bundle, no record, no blob. A request in flight at the kill leaves its Retry-After unknown: terminal."""
    result = acquire(env, "in_flight", monkeypatch)(step_request(env))
    assert isinstance(result, Failed) and result.code == "ACQUIRE_WALL_CLOCK_EXCEEDED"
    assert result.wall_clock is not None and result.wall_clock.t_acq_ms == T_ACQ_MS
    assert result.wall_clock.elapsed_ms >= T_ACQ_MS
    assert result.retry_after_known is False and result.not_before is None
    assert not _alive(int((env / "child.pid").read_text()))


def test_wrong_policy_or_bound_is_refused_before_any_child(env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    req = step_request(env)
    other = make_live_acquire(FetchPolicy(), child=FAKE, workroot=env / "acquire")
    assert isinstance(other(req), Failed)
    assert not (env / "child.pid").exists()


def test_a_stage03_failure_keeps_its_code(env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result = acquire(env, "refused", monkeypatch)(step_request(env))
    assert isinstance(result, Failed) and result.code == "ATTEMPTS_EXHAUSTED" and result.retry_after_known


# Retry-After (item 5) --------------------------------------------------------------------------------------------


@pytest.mark.parametrize("form", ["seconds", "date"])
def test_a_retry_after_seen_before_the_kill_is_the_retry_instant(
    env: Path, monkeypatch: pytest.MonkeyPatch, form: str
) -> None:
    """Persisted before the kill (the side channel line is fsynced as the headers arrive): known, and the instant is
    the server's, never shorter."""
    target = (datetime.now(UTC) + timedelta(seconds=600)).replace(microsecond=0)
    value = "600" if form == "seconds" else format_datetime(target, usegmt=True)
    before = datetime.now(UTC)
    result = acquire(env, f"retry_after:{value}", monkeypatch)(step_request(env))
    after = datetime.now(UTC)
    assert isinstance(result, Failed) and result.code == "ACQUIRE_WALL_CLOCK_EXCEEDED" and result.retry_after_known
    assert result.not_before is not None
    if form == "seconds":
        assert before + timedelta(seconds=600) <= result.not_before <= after + timedelta(seconds=600)
    else:
        assert result.not_before == target


@pytest.mark.parametrize("value", ["soon", "99999999999999", "Mon, 01 Jan 2120 00:00:00 GMT"])
def test_an_unreadable_or_out_of_range_retry_after_is_unknown(
    env: Path, monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    result = acquire(env, f"retry_after:{value}", monkeypatch)(step_request(env))
    assert isinstance(result, Failed) and result.retry_after_known is False and result.not_before is None


def _lines(path: Path, *entries: dict[str, Any], torn: bytes = b"") -> Path:
    path.write_bytes(b"".join(json.dumps(e).encode() + b"\n" for e in entries) + torn)
    return path


def test_side_channel_never_shortens_and_treats_a_torn_line_as_unknown(tmp_path: Path) -> None:
    t = time.time()
    req = {"event": "request", "url": "u", "at": t}
    a = {"event": "response", "url": "u", "status": 429, "retry_after": "300", "at": t}
    b = {"event": "response", "url": "u", "status": 429, "retry_after": "60", "at": t + 10}
    known, nb = side_channel(_lines(tmp_path / "a", req, a, req, b))
    assert known and nb == datetime.fromtimestamp(t, UTC) + timedelta(seconds=300)
    assert side_channel(_lines(tmp_path / "b", req, torn=b'{"event": "resp'))[0] is False
    assert side_channel(
        _lines(tmp_path / "c", req, {"event": "error", "url": "u", "code": "HTTP_TIMEOUT", "at": t})
    ) == (
        True,
        None,
    )
    assert side_channel(tmp_path / "missing") == (True, None)


def test_a_later_attempt_defers_to_an_earlier_attempts_retry_after(env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An attempt whose failure was never recorded (its controller died) still holds back the next attempt."""
    base = env / "acquire" / ("0" * 64) / "attempt-1-x"
    base.mkdir(parents=True)
    t = time.time()
    _lines(
        base / "network.jsonl",
        {"event": "request", "url": "u", "at": t},
        {"event": "response", "url": "u", "status": 429, "retry_after": "900", "at": t},
    )
    now = datetime.now(UTC)
    result = acquire(env, "replay", monkeypatch)(step_request(env, attempt=2, now=now))
    assert isinstance(result, Deferred) and result.not_before > now + timedelta(seconds=800)
    assert not (env / "child.pid").exists()  # no child: no request before the instant
    assert earlier_attempts(base.parent, 2) == (True, result.not_before)


def test_a_later_attempt_after_an_unknown_one_fails(env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    base = env / "acquire" / ("0" * 64) / "attempt-1-x"
    base.mkdir(parents=True)
    _lines(base / "network.jsonl", {"event": "request", "url": "u", "at": time.time()})
    result = acquire(env, "replay", monkeypatch)(step_request(env, attempt=2))
    assert isinstance(result, Failed) and result.code == "ADAPTER_INCONSISTENT"
    assert not (env / "child.pid").exists()


# Through the controller (items 5, 17) -----------------------------------------------------------------------------


@pytest.fixture(scope="module")
def index(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return S8.build_index(tmp_path_factory.mktemp("rw"))


def _live(env: Path, index: Path) -> tuple[Path, dict[str, Any]]:
    root = S8.memory_root(env / "m")
    payload = created_payload(live_request(root, index), dict(STAGE04_IDENTITY))
    InvestigationMemory.create(root, payload).close()
    return root, payload


def _integration(env: Path, **kw: Any) -> Integration:
    live = make_live_acquire(POLICY, child=FAKE, t_acq_ms=kw.pop("t_acq_ms", T_ACQ_MS), workroot=env / "acquire")
    return Integration(detector=S8.synthetic_detector, live=live)


def _run(root: Path, payload: dict[str, Any], integ: Integration, at: datetime | None = None) -> Any:
    clock = (lambda: at) if at is not None else None
    return run_investigation(
        root, payload["investigation_key"], integ.adapters(), integ.environment(payload), clock=clock
    )


def test_a_live_investigation_runs_end_to_end(env: Path, index: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CITERIFT_FAKE_MODE", "replay")
    root, payload = _live(env, index)
    result = _run(root, payload, _integration(env))
    assert result.status == "NEEDS_RESOLUTION"  # the same real content as the retained Obokata ar bundle


def test_retry_after_resume_waits_before_the_instant_and_starts_at_it(
    env: Path, index: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Item 5: the killed attempt is recorded retryable with the instant it saw; the controller does not restart
    ACQUIRE before it, and does at it and after it."""
    root, payload = _live(env, index)
    monkeypatch.setenv("CITERIFT_FAKE_MODE", "retry_after:600")
    first = _run(root, payload, _integration(env))
    assert first.status == "RUNNING" and first.explanation["next"]["action"] == "wait"
    with InvestigationMemory.open(root, payload["investigation_key"], writable=False) as mem:
        [failed] = [r["payload"] for r in mem.view.records if r["kind"] == "step_failed"]
        nb = datetime.fromisoformat(failed["not_before"].replace("Z", "+00:00"))
        assert failed["code"] == "ACQUIRE_WALL_CLOCK_EXCEEDED" and failed["retryable"] is True
        assert failed["wall_clock"] == {"t_acq_ms": T_ACQ_MS, "elapsed_ms": failed["wall_clock"]["elapsed_ms"]}
        assert workflow.next_action(mem.view, nb - timedelta(milliseconds=1)).action == "wait"
        assert workflow.next_action(mem.view, nb).action == "start"
        assert workflow.next_action(mem.view, nb + timedelta(hours=1)).action == "start"
    monkeypatch.setenv("CITERIFT_FAKE_MODE", "replay")
    early = _run(root, payload, _integration(env), at=nb - timedelta(seconds=1))
    assert early.status == "RUNNING" and early.explanation["next"]["action"] == "wait"
    assert _attempts(root, payload) == 1
    done = _run(root, payload, _integration(env), at=nb)
    assert done.status == "NEEDS_RESOLUTION" and _attempts(root, payload) == 2


def _attempts(root: Path, payload: dict[str, Any]) -> int:
    with InvestigationMemory.open(root, payload["investigation_key"], writable=False) as mem:
        return len(mem.view.attempts["ACQUIRE"])


def test_an_unknown_retry_after_at_the_kill_is_terminal(
    env: Path, index: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CITERIFT_FAKE_MODE", "in_flight")
    root, payload = _live(env, index)
    result = _run(root, payload, _integration(env))
    assert result.status == "FAILED"
    t = result.explanation["terminated_by"]
    assert (t["code"], t["step"]) == ("ACQUIRE_WALL_CLOCK_EXCEEDED", "ACQUIRE")
    with InvestigationMemory.open(root, payload["investigation_key"], writable=False) as mem:
        assert mem.view.root is None and mem.view.logical == []


_CONTROLLER = """
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import test_step8_live as L
root, env, payload = Path(sys.argv[2]), Path(sys.argv[4]), json.loads(Path(sys.argv[5]).read_text())
L._run(root, payload, L._integration(env, t_acq_ms=60_000))
"""


@pytest.mark.parametrize("mode", ["in_flight", "retry_after:600"])
def test_controller_death_during_the_live_child(
    env: Path, index: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    """Item 17: the controller dies while the child is inside a request. The child dies with it (PR_SET_PDEATHSIG).
    On resume the attempt is interrupted, and the next attempt never sends a request early: it defers to the
    Retry-After instant the dead child saw, or fails when what the dead child saw is unknown."""
    root, payload = _live(env, index)
    (env / "payload.json").write_text(json.dumps(payload))
    monkeypatch.setenv("CITERIFT_FAKE_MODE", mode)
    proc = subprocess.Popen(
        [sys.executable, "-c", _CONTROLLER, str(HERE), str(root), str(index), str(env), str(env / "payload.json")],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    deadline = time.monotonic() + 30
    marker = "response" if mode.startswith("retry_after") else "request"
    while time.monotonic() < deadline:
        logs = list((env / "acquire").glob("*/attempt-*/network.jsonl"))
        if logs and marker in logs[0].read_text() and (env / "child.pid").exists():
            break
        time.sleep(0.05)
    else:
        proc.kill()
        raise AssertionError(proc.stderr.read().decode() if proc.stderr else "no child")
    child = int((env / "child.pid").read_text())
    os.kill(proc.pid, signal.SIGKILL)
    proc.wait()
    gone = time.monotonic() + 5
    while _alive(child) and time.monotonic() < gone:
        time.sleep(0.02)
    assert not _alive(child), "the capture child outlived its controller"
    monkeypatch.setenv("CITERIFT_FAKE_MODE", "replay")
    (env / "child.pid").unlink()
    result = _run(root, payload, _integration(env))
    with InvestigationMemory.open(root, payload["investigation_key"], writable=False) as mem:
        kinds = [r["kind"] for r in mem.view.records if r.get("step") == "ACQUIRE"]
    assert "step_interrupted" in kinds
    assert not (env / "child.pid").exists()  # no request was sent by the attempt after the crash
    if mode == "in_flight":
        assert result.status == "FAILED"
        assert result.explanation["terminated_by"]["code"] == "ADAPTER_INCONSISTENT"
    else:
        assert result.status == "BLOCKED" and kinds[-1] == "step_deferred"
