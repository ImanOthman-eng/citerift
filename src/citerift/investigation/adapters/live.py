"""Live ACQUIRE: one Stage 03 capture per attempt in a supervised child process under the D-042 bound (Step 8).

``make_live_acquire(policy)`` returns the ACQUIRE adapter of a ``live_capture`` request. Each attempt:

1. checks that ``policy`` is the request's (``fetch_policy_sha256`` = Stage 03 ``digest(policy.to_json())``) and that
   the request's D-042 bound is this policy's (``deadline_ms``, ``op_timeout_ms``, ``t_acq_ms``);
2. creates a private work directory (mode 0700) and runs ``live_child`` in it under ``supervise`` with
   ``T_acq = t_acq_ms`` (240 s with the Stage 03 defaults), the timer started immediately before launch;
3. **inside the bound**, reads the child's ``result.json``: a ``complete`` or ``partial`` capture is opened and
   verified with Stage 03 (``open_bundle``, ``verify_bundle``) and retained exactly as a retained bundle is (IF-7,
   ``acquire.retain``); ``deferred`` is ``Deferred(not_before)``; ``failed`` is the first Stage 03 error code;
4. **past the bound**, ``ACQUIRE_WALL_CLOCK_EXCEEDED`` with ``wall_clock = {t_acq_ms, elapsed_ms}``. Nothing the child
   wrote is read except the Retry-After side channel, and nothing is returned for commit: no root, no bundle, no
   evidence. The failure is retryable only if the side channel proves every request's response headers were seen and
   every Retry-After value was readable; ``not_before`` is then the latest instant they name (never shortened).
   Otherwise ``retry_after_known`` is false and the controller records it as terminal;
5. keeps only the side channel of the attempt (in a per-investigation directory) until a capture succeeds, so a
   later attempt never starts before a Retry-After instant an earlier one saw, even when the controller died with
   the child: it defers to that instant, and an earlier attempt whose Retry-After is unknown fails it terminally.

The 240 s bound covers one attempt's child process. It is not the investigation's bound: ``9 x T_acq`` is the most
child time one investigation can spend in live ACQUIRE (SPEC 9.2), before termination overhead and the other steps.

A supervision failure (a process of the child's session alive after the sweep) or a child that ends without a result
is ``ADAPTER_INCONSISTENT`` with ``retry_after_known`` false when it was killed: never a capture.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from citerift.investigation.adapters import Deferred, Failed, StepRequest, StepResult, WallClock
from citerift.investigation.adapters.acquire import open_verified, retain
from citerift.investigation.adapters.supervise import Supervised, supervise
from citerift.investigation.extraction import ADAPTER_INCONSISTENT
from citerift.investigation.workflow import WALL_CLOCK
from citerift.wiki.canonical import digest as stage03_digest
from citerift.wiki.fetch import FetchPolicy, parse_retry_after
from citerift.wiki.issues import CATALOG

CHILD_MODULE = "citerift.investigation.adapters.live_child"


def policy_digest(policy: FetchPolicy) -> str:
    """The request's ``fetch_policy_sha256`` for ``policy`` (Stage 03's canonical digest of its JSON form)."""
    return stage03_digest(policy.to_json())


def bound_for(policy: FetchPolicy) -> dict[str, int]:
    """The D-042 bound of ``policy``: ``t_acq_ms = deadline_ms + op_timeout_ms + 30 000``."""
    deadline, op = round(policy.deadline_s * 1000), round(policy.op_timeout_s * 1000)
    return {
        "deadline_ms": deadline,
        "op_timeout_ms": op,
        "safety_allowance_ms": 30_000,
        "t_acq_ms": deadline + op + 30_000,
    }


def _parse_at(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo is not None else None


def side_channel(path: Path) -> tuple[bool, datetime | None]:
    """(retry_after_known, not_before) from the child's ``network.jsonl`` after a kill.

    Known only when every request has its response or error line and every Retry-After value is readable by Stage 03's
    own parser. A torn last line counts as missing (the response it would have recorded is then unknown)."""
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        return True, None  # the child never sent a request
    except OSError:
        return False, None
    pending = 0
    instants: list[datetime] = []
    for line in data.split(b"\n")[:-1]:  # the part after the last newline is torn or empty
        try:
            entry = json.loads(line)
            event, at = entry["event"], datetime.fromtimestamp(float(entry["at"]), UTC)
        except (ValueError, KeyError, TypeError, OverflowError):
            return False, None
        if event == "request":
            pending += 1
        elif event in ("response", "error"):
            pending -= 1
            if event == "response" and entry.get("retry_after") is not None:
                seconds, problem = parse_retry_after(str(entry["retry_after"]), at)
                if seconds is None or problem is not None:
                    return False, None  # unreadable or out of range: never guess a shorter wait
                instants.append(at + timedelta(seconds=seconds))
        else:
            return False, None
    return pending == 0, max(instants) if instants else None


def _first_code(issues: Sequence[dict[str, Any]]) -> str:
    for i in issues:
        if i.get("severity") == "error" and i.get("code") in CATALOG:
            return str(i["code"])
    return ADAPTER_INCONSISTENT


def earlier_attempts(base: Path, attempt: int) -> tuple[bool, datetime | None]:
    """The side channels earlier attempts of this investigation left (kept until a capture succeeds): whether all of
    them are known, and the latest Retry-After instant any of them saw. This covers an attempt whose controller died
    with the child (the child dies with it, PR_SET_PDEATHSIG) before its failure could be recorded (owner item 17)."""
    known, latest = True, None
    for d in sorted(base.iterdir()) if base.is_dir() else ():
        if not d.name.startswith("attempt-") or d.name.startswith(f"attempt-{attempt}-"):
            continue
        k, nb = side_channel(d / "network.jsonl")
        known = known and k
        latest = max((t for t in (latest, nb) if t is not None), default=None)
    return known, latest


def _keep_side_channel(work: Path) -> None:
    for entry in work.iterdir():
        if entry.name != "network.jsonl":
            shutil.rmtree(entry) if entry.is_dir() and not entry.is_symlink() else entry.unlink()


def make_live_acquire(
    policy: FetchPolicy,
    *,
    child: Sequence[str] | None = None,
    t_acq_ms: int | None = None,
    workroot: Path | None = None,
) -> Any:
    """The live ACQUIRE adapter. ``workroot`` holds one private directory per investigation (default: a per-user
    directory under the system temporary directory). ``child`` (an argv prefix to which ``WORKDIR PARENT_PID`` is
    appended) and ``t_acq_ms`` replace the production child and the configured bound only in tests (G-6)."""
    argv = list(child) if child is not None else [sys.executable, "-I", "-m", CHILD_MODULE]
    root = workroot if workroot is not None else Path(tempfile.gettempdir()) / f"citerift-acquire-{os.getuid()}"

    def live_acquire(req: StepRequest) -> StepResult:
        cfg = req.request["config"]
        subject = req.request["subject"]
        if cfg.get("fetch_policy_sha256") != policy_digest(policy):
            return Failed(ADAPTER_INCONSISTENT, detail="the fetch policy is not the one the request names")
        bound = cfg.get("live_acquire_bound")
        if bound != bound_for(policy):
            return Failed(ADAPTER_INCONSISTENT, detail="the request's D-042 bound is not this fetch policy's")
        limit = t_acq_ms if t_acq_ms is not None else int(bound["t_acq_ms"])
        base = root / req.investigation["investigation_key"]
        os.makedirs(base, mode=0o700, exist_ok=True)
        os.chmod(root, 0o700)
        os.chmod(base, 0o700)
        known, earlier = earlier_attempts(base, req.attempt)
        if not known:
            return Failed(
                ADAPTER_INCONSISTENT,
                detail="an earlier attempt ended with a request whose Retry-After is unknown; a retry could be early",
            )
        if earlier is not None and earlier > req.now:
            return Deferred(earlier)
        work = Path(tempfile.mkdtemp(prefix=f"attempt-{req.attempt}-", dir=base))
        try:
            spec = {"wiki": subject["wiki"], "revision_id": subject["revision_id"], "policy": policy.to_json()}
            (work / "request.json").write_text(json.dumps(spec), encoding="utf-8")
            run = supervise(
                [*argv, str(work), str(os.getpid())],
                t_acq_s=limit / 1000,
                cwd=work,
                stdout=work / "stdout.log",
                stderr=work / "stderr.log",
            )
            result = _outcome(run, work, limit, req)
        finally:
            _keep_side_channel(work)  # what it saw stays until a capture succeeds
        if not isinstance(result, (Failed, Deferred)):
            shutil.rmtree(base, ignore_errors=True)
        return result

    return live_acquire


def _outcome(run: Supervised, work: Path, limit: int, req: StepRequest) -> StepResult:
    known, not_before = side_channel(work / "network.jsonl")
    if run.timed_out:
        if run.survivors:
            return Failed(
                ADAPTER_INCONSISTENT,
                detail=f"supervision failure: {len(run.survivors)} processes survived the kill",
                retry_after_known=True,
            )
        return Failed(
            WALL_CLOCK,
            detail=f"killed at the D-042 bound (kill {run.kill_ms:.3f} ms, reap {run.reap_ms:.3f} ms)",
            wall_clock=WallClock(t_acq_ms=limit, elapsed_ms=max(run.elapsed_ms, limit)),
            not_before=not_before,
            retry_after_known=known,
        )
    if run.survivors or run.killed:
        return Failed(ADAPTER_INCONSISTENT, detail="the capture child left processes in its session")
    try:
        result = json.loads((work / "result.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return Failed(ADAPTER_INCONSISTENT, detail=f"the capture child exited {run.returncode} without a result")
    stated = _parse_at(result.get("not_before"))
    latest = max((t for t in (stated, not_before) if t is not None), default=None)
    status = result.get("status")
    if status in ("complete", "partial") and result.get("bundle"):
        bundle, failure = open_verified(work / "bundle")
        if failure is not None or bundle is None:
            return failure or Failed(ADAPTER_INCONSISTENT, detail="no bundle")
        return retain(bundle, req.request_key)
    if status == "deferred":
        if latest is None:
            return Failed(ADAPTER_INCONSISTENT, detail="a deferred capture without a not_before instant")
        return Deferred(latest)
    return Failed(_first_code(result.get("issues") or []), detail="Stage 03 capture failed", not_before=latest)
