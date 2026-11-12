# Stage 04 Step 8: open-source leverage review for live ACQUIRE supervision

Status: Step 8 record, written before any supervision code. It follows the owner's permanent rule of 2026-11-10
(message `cmsg_018VCB51nDHP6HXmLU4ea5yP2h9GM56jQT5F4jCEcUv9zu`) and the Step 8 instruction, item 1
(`cmsg_018VCB51nDHP6HXmLU4ea5yP3N7KPNwX5cW1HPdZKPNpQP`).

**Scope.** This review covers the boundary that enforces D-042:

- supervising a child process;
- a hard wall-clock timeout over the child's whole process tree and session;
- killing and reaping;
- terminating a POSIX process group;
- testing timeouts and faults.

It covers nothing else in Step 8. The other Step 8 adapters call the accepted Stage 02 and Stage 03 engines, which
are already in the repository.

**Baseline to beat (owner's words):** "subprocess + setsid/start_new_session + killpg + wait/reap".

**Result: no dependency is adopted.** The stdlib/POSIX baseline is the implementation.
- None of the candidates gives a stronger process-tree guarantee than a session kill plus a child subreaper.
- psutil, the strongest technical candidate, finds descendants by walking parent links. That walk loses a
  double-forked orphan, which a session kill does not.
- Pebble fails the licence gate (LGPL).

The details are below.

## 1. Method (2026-11-12)

- **Version, upload date of the latest release, declared licence, `requires_python`, Python classifiers and direct
  dependencies:** from the PyPI JSON API (`https://pypi.org/pypi/<name>/json`).
- **Known vulnerabilities:** from the OSV API (`POST https://api.osv.dev/v1/query`, ecosystem PyPI), with the affected
  ranges taken from the advisories.
- **Maintenance:** judged only by the date of the latest release and the number of releases. Commit history and issue
  response were not examined.
- **Process-tree behaviour:** from each project's documented API.
- No candidate was installed and no code was copied. "Documented" below means stated in the project's own
  documentation; nothing in this review was measured on a candidate.
- **Baseline measurements:** made on this container (Linux 6.18.44, Python 3.13.18) with
  `scratchpad/sup_probe.py`, reproduced in section 5.

## 2. What the supervisor must guarantee

Each requirement comes from D-042, SPEC 7 (F-11) and the Step 8 instruction, item 4.

1. **G-1, one deadline over everything.** The parent owns the deadline. It starts immediately before launch and covers
   interpreter start-up, DNS, the Stage 03 network gate, TCP/TLS, headers, bodies, processing, bundle publication and
   the return path.
2. **G-2, whole-tree termination.** At the deadline no network-capable descendant of the child survives. This includes
   a descendant that was re-parented because its own parent exited.
3. **G-3, reaping.** Every terminated process is reaped. No zombie is left, and the kill and reap times are measured
   separately.
4. **G-4, nothing authoritative after a timeout.** A killed attempt's output is discarded by the parent. Only a child
   that exited normally before the deadline can produce a bundle that the parent verifies and retains.
5. **G-5, parent death.** If the supervising process dies, the child must not continue on the network unsupervised.
6. **G-6, deterministic and offline tests.** The deadline must be injectable, so that tests can run at sub-second
   deadlines with fake transports and sockets blocked.
7. **G-7, Python 3.12 and 3.13 on Linux.** These are the CI and container targets (`.github/workflows`, the
   `ubuntu-latest` runner). Other POSIX systems are not required to pass. The supervisor fails closed if a Linux-only
   facility it relies on is missing.

## 3. Candidates

Common to every candidate: none needs network access to run, and none is in `uv.lock`.

### 3.1 psutil

- **Version and licence:** 7.2.2, uploaded 2026-01-28, 104 releases. BSD-3-Clause. No runtime dependencies.
  Licence gate: pass.
- **Platforms:** `requires_python >=3.6`. Its classifiers do not list minor versions, and it ships compiled abi3
  wheels, so it covers 3.12 and 3.13. It adds a C extension and is a compiled build dependency on any platform
  without a wheel.
- **Security:** OSV lists only GHSA-qfc5-mcwq-26q8 / CVE-2019-18874 (a double free, affecting versions below 5.6.6).
  It is fixed long before 7.2.2.
- **What it provides:** `Process.children(recursive=True)`, `wait_procs(procs, timeout, callback)`, and process
  status and enumeration across platforms.
- **Process-tree guarantee:** `children(recursive=True)` is computed from parent-pid links at the moment of the call
  (documented). A process whose parent already exited is re-parented to init or to the nearest subreaper, and then
  no longer appears under the child. A double-forked grandchild is exactly that case. It also offers no atomic
  "kill the tree" operation, so a fork between the walk and the signal escapes.
  A session kill (`killpg` on a session created with `setsid`) reaches every member of the group, whatever its
  parent.
- **Kill and reap:** `wait_procs` reaps only processes that are children of the caller, like `waitpid`. It adds no
  reaping power over the stdlib.
- **Offline and deterministic:** yes.
- **Complexity saved:** a roughly 25-line `/proc/<pid>/stat` session scan used as a test-time and post-kill
  assertion. psutil would make that scan portable, but G-7 does not require portability.
- **Complexity added:** a compiled dependency, pinning, attribution and audit, for no change in the kill path.
- **Versus internal:** the internal kill path is the same `killpg` that psutil would also need. For G-2, psutil's
  tree walk is weaker than the session kill.
- **Verdict: REFERENCE ONLY.** Its process-status vocabulary is used in tests (state `Z` means a zombie). It is not
  a dependency.

### 3.2 Pebble

- **Version and licence:** 5.2.3, uploaded 2026-10-04, 105 releases. Declared licence: LGPL.
- **Licence gate: fail.** Copyleft needs an owner decision, and the material gain that would justify asking for one
  is not there.
- **Platforms:** `requires_python >=3.10`. OSV: none recorded.
- **What it provides:** `concurrent.process` decorators and a `ProcessPool` with per-task timeouts, built on
  `multiprocessing`.
- **Process-tree guarantee:** its documentation describes stopping the worker process on timeout. It does not
  describe a process-group or session kill, and it does not describe reaping of grandchildren.
- **Offline and deterministic:** yes, but `multiprocessing` start methods add fork/spawn behaviour and pickling at
  the boundary.
- **Complexity:** it would save only the timer, and it would add a pool abstraction CITERIFT does not need (one child
  per attempt).
- **Verdict: REJECT** (licence gate; no tree guarantee beyond the baseline).

### 3.3 sarge

- **Version and licence:** 0.1.8, uploaded 2026-01-20, 12 releases. BSD-3-Clause. No dependencies.
- **Platforms:** classifiers 3.10 to 3.14. OSV: none recorded.
- **What it provides:** command pipelines, capture objects and asynchronous running on top of `subprocess`.
- **Process-tree guarantee:** none beyond the `subprocess.Popen` it wraps. It documents no group or session kill.
- **Complexity:** it saves nothing for a single child, and it adds a command-language parser that CITERIFT would have
  to audit.
- **Verdict: REJECT.**

### 3.4 plumbum

- **Version and licence:** 2.0.2, uploaded 2026-07-22, 33 releases. MIT. One dependency, `typing-extensions`, and
  only on Python below 3.13.
- **Platforms:** classifiers 3.10 to 3.15. OSV: none recorded.
- **What it provides:** shell-like command combinators, remote (SSH) machines and CLI helpers.
- **Process-tree guarantee:** timeouts act on the started process. No session kill is documented.
- **Complexity:** large surface (local and remote shells, path objects) for one `Popen`.
- **Verdict: REJECT.**

### 3.5 AnyIO

- **Version and licence:** 4.16.0, uploaded 2026-11-01, 73 releases. MIT. Dependencies: `idna`, plus
  `exceptiongroup` and `typing_extensions` on older Pythons.
- **Platforms:** classifiers 3.10 to 3.15.
- **Security:** OSV lists CVE-2026-63349 (versions 4.14.0 up to 4.14.2), CVE-2026-64847 and CVE-2026-63374 (both
  below 4.14.2). All are fixed in 4.14.2, which 4.16.0 is later than.
- **What it provides:** `open_process` and `run_process` under structured cancellation (`fail_after`).
- **Process-tree guarantee:** cancellation terminates the direct process. A group or session kill is still the
  caller's code.
- **Offline and deterministic:** yes, but it brings an event loop into a controller that is synchronous by design
  (Step 7 R-4: no threads, timers or background tasks in the controller).
- **Verdict: REJECT.**

### 3.6 pexpect

- **Version and licence:** 4.9.0, uploaded 2023-11-25, 20 releases. ISC. One dependency, `ptyprocess`.
- **Platforms:** `requires_python` is not declared, and the classifiers do not list 3.12 or 3.13. OSV: none recorded
  for pexpect or ptyprocess.
- **What it provides:** spawning a program in a pseudo-terminal and expecting output, with `terminate(force=True)`
  for the direct child.
- **Fit:** pseudo-terminal control is irrelevant to a non-interactive child, and there is no release since 2023.
- **Verdict: REJECT.**

### 3.7 Not reviewed further

- **Cloud workers, job queues and service supervisors** (systemd units, supervisord, Celery, RQ): excluded by the
  instruction ("No cloud worker/service"), and each needs a daemon.
- **cgroup-based containment** (systemd-run scopes, cgroup v2 `cgroup.kill`): this would give the strongest tree
  guarantee, but the container and the GitHub runner give no delegated cgroup to an unprivileged test process. It is
  recorded as a future hardening option, not adopted.

## 4. The adopted baseline (stdlib/POSIX, owned by CITERIFT)

1. **Session.** `subprocess.Popen([sys.executable, "-I", "-m", <child module>], start_new_session=True, close_fds=True,
   stdin=DEVNULL)`. The child calls `setsid` before `exec`, so it leads a new session and process group whose id
   equals its pid.
2. **Parent death (G-5).** The child sets `prctl(PR_SET_PDEATHSIG, SIGKILL)` first. It then checks `getppid()`
   against the pid of the parent that launched it, because the parent may have died before the `prctl` call. If the
   parent is gone, the child exits before touching the network.
3. **Subreaper (G-2, G-3).** The supervising process sets `prctl(PR_SET_CHILD_SUBREAPER, 1)`. Orphaned descendants
   are then re-parented to the supervisor instead of init, so the supervisor can reap them. `PR_SET_CHILD_SUBREAPER`
   is a process attribute, so the supervisor's own process is marked for its lifetime.
   - **Inference:** this is harmless here. The Stage 04 controller has no other children that it could
     accidentally reap: the Stage 03 extraction worker is created and reaped inside `extract_bundle`, by the same
     `waitpid` on its own pid.
4. **Deadline (G-1).** The parent takes `t0 = monotonic()` immediately before `Popen` and waits with
   `wait(timeout=T_acq − elapsed)`.
5. **Termination (G-2).**
   - At the deadline, the parent sends `killpg(pgid, SIGKILL)` **before** reaping the leader. The leader's zombie keeps
     the process-group id reserved, so the signal cannot reach a process that reused the id.
   - SIGKILL is sent without a SIGTERM grace period: nothing produced after the deadline may count (G-4), so a
     cooperative shutdown has no value.
   - The parent then reaps the leader with `wait()`, and any re-parented orphans with `waitpid(-1, WNOHANG)` against
     the session. It then scans `/proc/*/stat` for any process still in the session; a non-empty result is a
     supervision failure (fail closed).
6. **Measurements.** `kill_ms` (the `killpg` call), `reap_ms` (leader `wait`) and `sweep_ms` (orphan reap and session
   scan) are recorded separately from the wall clock of the attempt.
7. **Output (G-4).**
   - The child writes into a private directory that the parent created. The parent looks at it only after the child
     exited normally inside the deadline.
   - After a timeout the directory is deleted without being read, except for the Retry-After side-channel described in
     the Step 8 design. That side channel is advisory input to the retry decision and never a bundle.
8. **Testability (G-6).** `T_acq` is a constructor parameter of the supervisor. Production derives it from the
   Investigation config (`deadline_s + op_timeout_s + 30 s`, in `config_digest`). Tests pass sub-second values and run
   the child against a fake transport.

**Limits stated plainly.**
- A descendant that calls `setsid` itself leaves the child's session, so `killpg` does not reach it.
- Because the supervisor is a subreaper, such a descendant is still re-parented to the supervisor when its parent
  dies, and the orphan sweep reaps it only after it exits. A live process outside the session is detected only if it
  is a direct child of the supervisor (`waitpid` does not reap a running process).
- **Mitigation:** the live ACQUIRE child runs only Stage 03 capture code, which creates no subprocesses. The sweep
  records every pid that is still a child of the supervisor after the kill. Any such pid gets its own `kill`, is
  reaped and is reported. This covers the descendants that matter (network-capable code started by the child) as far
  as POSIX allows without cgroups.

## 5. Baseline probe (2026-11-12, this container)

The probe started a child with `start_new_session=True` that double-forked a grandchild. It then killed the session
and reaped:

```
prctl 0 0                                               # PR_SET_CHILD_SUBREAPER succeeded
before [(1451, 'S'), (1452, 'Z'), (1453, 'S')]          # session members: child, exited middle, grandchild
after [(1452, 'Z'), (1453, 'Z')] kill_ms 0.043 reap_ms 0.84
reaped orphan 1453
reaped orphan 1452
final []                                                # no member of the session left
```

- **Result:** `killpg` reached the re-parented grandchild that a parent-link walk would have missed, and the
  subreaper let the supervisor reap it.
- The Step 8 supervisor tests repeat this under pytest and assert the empty session scan. They are recorded in the
  Step 8 evidence.

## 6. Decision

- **Adopted:** the stdlib/POSIX baseline (`subprocess`, `os.killpg`, `os.waitpid`, `prctl` through `ctypes`, and a
  `/proc` session scan).
- **Dependencies:** none added. `pyproject.toml` and `uv.lock` are unchanged by this decision.
