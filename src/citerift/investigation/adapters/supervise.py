"""The D-042 supervisor of a live ACQUIRE attempt: one child process, one wall-clock bound, the whole session killed
and reaped (Step 8; ``docs/verification/stage-04/review/step8/STEP8_BUILD_VS_ADOPT.md`` section 4).

Standard library and Linux ``/proc`` only. The parent takes the time immediately before it launches the child, so the
bound covers interpreter start-up and everything the child does. The child runs in its own session
(``start_new_session``), so its session id and process-group id are its pid.

At the deadline, in this order:

1. ``killpg(SIGSTOP)`` freezes every member of the child's process group, so none can fork or exit while the tree is
   read;
2. ``/proc`` is read for every process of the child's session and every descendant of the child by parent links
   (this finds a descendant that left the session with ``setsid`` while its parent was alive);
3. each of them gets ``SIGKILL``, and the group gets ``killpg(SIGKILL)``, before the leader is reaped (the leader's
   zombie keeps the group id reserved, so the signal cannot reach a process that reused it);
4. the leader, the only child of this process, is reaped with ``wait`` (never ``waitpid(-1)``, which could take the
   status of another child of the controller);
5. the killed processes are swept: until each is gone or a zombie (re-parented and reaped by init), within a bound.

``kill_ms``, ``reap_ms`` and ``sweep_ms`` are measured separately from the attempt's elapsed time. A process of the
session, or a killed descendant, that is still alive after the sweep is a survivor; a survivor makes the attempt a
supervision failure (fail closed). A child that exits on its own is swept the same way: anything it left in its
session is killed, and it is a supervision failure too.

Limit (stated in the review): a descendant that double-forks and calls ``setsid`` after its intermediate parent has
exited has neither the session nor a parent link to the child, so ``/proc`` cannot attribute it without cgroups. The
live ACQUIRE child runs only Stage 03 capture code, which starts no process.
"""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

SWEEP_S = 5.0
POLL_S = 0.01


@dataclass(frozen=True)
class Supervised:
    """One supervised run. ``returncode`` is None when the deadline killed the child."""

    returncode: int | None
    timed_out: bool
    elapsed_ms: int  # from just before launch to the child's exit, or to the deadline
    kill_ms: float | None  # SIGSTOP, tree read and SIGKILL
    reap_ms: float | None  # the leader's wait
    sweep_ms: float  # until every killed process is gone (and the session is empty)
    killed: tuple[int, ...]  # the pids that received SIGKILL besides the group signal
    survivors: tuple[int, ...]  # alive after the sweep: a supervision failure


def _stat(pid: int) -> tuple[str, int, int, int, int] | None:
    """(state, ppid, pgrp, session, starttime) of ``pid`` from ``/proc``, or None when it does not exist."""
    try:
        with open(f"/proc/{pid}/stat", "rb") as f:
            raw = f.read()
    except OSError:
        return None
    fields = raw[raw.rfind(b")") + 2 :].split()
    try:
        return fields[0].decode(), int(fields[1]), int(fields[2]), int(fields[3]), int(fields[19])
    except (IndexError, ValueError):
        return None


def _all() -> dict[int, tuple[str, int, int, int, int]]:
    out = {}
    for name in os.listdir("/proc"):
        if name.isdigit():
            st = _stat(int(name))
            if st is not None:
                out[int(name)] = st
    return out


def tree(leader: int) -> dict[int, int]:
    """Every live process in ``leader``'s session or below it by parent links: pid -> start time (pid reuse guard)."""
    procs = _all()
    children: dict[int, list[int]] = {}
    for pid, st in procs.items():
        children.setdefault(st[1], []).append(pid)
    found = {pid for pid, st in procs.items() if st[3] == leader}
    todo = [leader, *found]
    while todo:
        for c in children.get(todo.pop(), []):
            if c not in found:
                found.add(c)
                todo.append(c)
    found.discard(os.getpid())
    return {pid: procs[pid][4] for pid in found if pid in procs and procs[pid][0] != "Z"}


def _alive(pid: int, start: int) -> bool:
    st = _stat(pid)
    return st is not None and st[4] == start and st[0] not in ("Z", "X")


def _kill(pids: Mapping[int, int]) -> None:
    for pid, start in pids.items():
        if _alive(pid, start):
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.kill(pid, signal.SIGKILL)


def _sweep(pids: Mapping[int, int], leader: int, clock: Callable[[], float]) -> tuple[int, ...]:
    """Wait (bounded) until every killed process is gone; return those still alive, and any live session member."""
    ends = clock() + SWEEP_S
    while True:
        left = {p: s for p, s in pids.items() if p != leader and _alive(p, s)}
        session = {p: st[4] for p, st in _all().items() if st[3] == leader and st[0] not in ("Z", "X")}
        if not left and not session:
            return ()
        if clock() >= ends:
            return tuple(sorted({*left, *session}))
        _kill(session)
        time.sleep(POLL_S)


def supervise(
    argv: Sequence[str],
    *,
    t_acq_s: float,
    cwd: Path,
    stdout: Path,
    stderr: Path,
    env: Mapping[str, str] | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> Supervised:
    """Run ``argv`` under the D-042 bound ``t_acq_s``. The child's output goes to files, never to pipes the parent
    must drain."""
    with open(stdout, "wb") as out, open(stderr, "wb") as err:
        t0 = clock()
        proc = subprocess.Popen(  # noqa: S603 - a fixed interpreter and module, no shell
            list(argv),
            cwd=cwd,
            env=dict(env) if env is not None else None,
            stdin=subprocess.DEVNULL,
            stdout=out,
            stderr=err,
            start_new_session=True,
            close_fds=True,
        )
        try:
            returncode: int | None = proc.wait(timeout=max(0.0, t_acq_s - (clock() - t0)))
            elapsed = clock() - t0
        except subprocess.TimeoutExpired:
            returncode, elapsed = None, clock() - t0
        except BaseException:
            _terminate(proc, clock)
            raise
    if returncode is not None:
        start = clock()
        left = {p: s for p, s in tree(proc.pid).items() if p != proc.pid}
        _kill(left)
        survivors = _sweep(left, proc.pid, clock)
        return Supervised(
            returncode, False, int(elapsed * 1000), None, None, (clock() - start) * 1000, tuple(left), survivors
        )
    killed, kill_ms, reap_ms, sweep_ms, survivors = _terminate(proc, clock)
    return Supervised(None, True, int(elapsed * 1000), kill_ms, reap_ms, sweep_ms, killed, survivors)


def _terminate(
    proc: subprocess.Popen[bytes], clock: Callable[[], float]
) -> tuple[tuple[int, ...], float, float, float, tuple[int, ...]]:
    k0 = clock()
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(proc.pid, signal.SIGSTOP)
    members = tree(proc.pid)
    _kill(members)
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(proc.pid, signal.SIGKILL)  # before the leader is reaped: its zombie reserves the group id
    k1 = clock()
    proc.wait()
    k2 = clock()
    survivors = _sweep(members, proc.pid, clock)
    k3 = clock()
    killed = tuple(sorted(p for p in members if p != proc.pid))
    return killed, (k1 - k0) * 1000, (k2 - k1) * 1000, (k3 - k2) * 1000, survivors
