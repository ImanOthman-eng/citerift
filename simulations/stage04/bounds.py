"""F-11: worst-case operational bound of one investigation (Step 4 item 7).

The owner's condition (2026-11-10): no investigation-level wall-clock timer is required if every reachable execution
path has a finite operational bound derived from the configured retry, deferral and timeout limits; if a path has no
derivable bound, or a local operation can wait indefinitely, stop at that finding and recommend a wall-clock budget.

This module derives the bound symbolically, instantiates it with the configured values (read from the accepted
Stage 03 code, never copied by hand), takes the attempt and record maxima from the exhaustive controller model, and
runs two small experiments on the real Stage 03 transport against a local socket server:

- **slow headers**: a server that sends one header byte every 0.5 s keeps ``urllib_transport`` (timeout 1 s) for the
  whole drip, because Python's socket timeout applies to each receive, not to the response head;
- **endless 100 Continue**: ``http.client`` skips any number of interim ``100 Continue`` responses, so a server can
  hold the request for as long as it keeps sending them; the timeout never fires.

Both are in the network path of a live capture (ACQUIRE). Neither concerns a retained bundle.
"""

from __future__ import annotations

import json
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import controller_model as C

from citerift.wiki.extract import ExtractConfig
from citerift.wiki.fetch import FetchPolicy, TransportError, urllib_transport

PLAN_STEPS = len(C.STEPS)


def symbolic() -> dict[str, Any]:
    fp, ec = FetchPolicy(), ExtractConfig()
    A, F = C.A_MAX, C.F_MAX
    W = ec.worker_wall_s
    D, T = fp.deadline_s, fp.op_timeout_s
    out: dict[str, Any] = {
        "parameters": {
            "A_max": A,
            "F_max": F,
            "steps": PLAN_STEPS,
            "deadline_s": D,
            "op_timeout_s": T,
            "max_attempts_per_request": fp.max_attempts,
            "min_interval_s": fp.min_interval_s,
            "backoff_s": fp.backoff_s,
            "worker_wall_s": W,
            "worker_memory_mib": ec.worker_memory_mib,
            "max_refs": ec.max_refs,
            "max_candidates": ec.max_candidates,
            "max_nodes": ec.max_nodes,
        },
        "attempts": {
            "formula": "ACQUIRE (capture): A + F; ACQUIRE (retained bundle) and every other step: A",
            "live_total": (PLAN_STEPS - 1) * A + (A + F),
            "retained_total": PLAN_STEPS * A,
            "acquire_live": A + F,
        },
        "execution_records": {
            "formula": "1 (created) + 2 per attempt (start, close) + 1 (stale_detected, at most once)",
            "live": 1 + 2 * ((PLAN_STEPS - 1) * A + (A + F)) + 1,
            "retained": 1 + 2 * PLAN_STEPS * A + 1,
        },
        # Isolated Stage 03 worker: communicate(timeout=W), then SIGKILL of the session group; _run_worker may run a
        # second time to classify a native crash, so one isolated call is at most 2W plus kill-and-reap latency.
        "isolated_worker_s": {
            "per_call": 2 * W,
            "EXTRACT (A attempts x extract_bundle)": A * 2 * W,
            "ACQUIRE retained (A attempts x verify_bundle markers)": A * 2 * W,
            "VERIFY (A attempts x (verify_bundle + replay_bundle))": A * 4 * W,
        },
        # Live capture as designed: one Fetcher per capture shares one deadline; every attempt starts before it and
        # its body read ends by min(op_timeout, deadline - start); sleeps (min interval, backoff, Retry-After, gate
        # wait) never pass the deadline (fetch.py plan_next, Fetcher.get, NetworkGate.acquire).
        "live_capture_design_s": {
            "per_attempt_designed": D,
            "ACQUIRE live (A + F attempts)": (A + F) * D,
            "assumes": "the response head (status line and headers) and TLS handshake arrive within op_timeout; "
            "DNS resolution ends within the OS resolver limits",
        },
    }
    out["retained_bound_s"] = {
        "isolated_workers": out["isolated_worker_s"]["EXTRACT (A attempts x extract_bundle)"]
        + out["isolated_worker_s"]["ACQUIRE retained (A attempts x verify_bundle markers)"]
        + out["isolated_worker_s"]["VERIFY (A attempts x (verify_bundle + replay_bundle))"],
        "plus": "finite local work L (below) and kill/reap latency per worker call",
    }
    out["local_work"] = [
        {"step": "VALIDATE", "work": "a fixed number of stat calls and string checks", "bound": "O(1)"},
        {
            "step": "ACQUIRE (retained)",
            "work": "open_bundle reads capture.json <= 4 MiB; artifacts <= 64 MiB each, "
            "named in capture.json; SHA-256 over those bytes",
            "bound": "O(bundle bytes), bytes capped by Stage 03",
        },
        {"step": "EXTRACT", "work": "parent side: read the worker's JSON output", "bound": "O(document size)"},
        {
            "step": "NORMALIZE",
            "work": "one pass over units, containers and identifier occurrences",
            "bound": f"O(units + identifiers), units <= max_refs = {ec.max_refs}, identifiers <= max_candidates = "
            f"{ec.max_candidates}",
        },
        {
            "step": "LOOKUP",
            "work": "K <= distinct keys + pairs queries on an immutable read-only SQLite index; each "
            "gather runs indexed selects and, for matched and no_record, a relevance scan of the quarantine table and "
            "of invalid identifiers",
            "bound": "O(K x (events per key + Q)), Q = quarantined rows + invalid "
            "identifiers of the pinned index (a constant of the index)",
        },
        {"step": "DETECT", "work": "17 guards per candidate", "bound": "O(candidates)"},
        {"step": "ASSEMBLE", "work": "one pass over claims; schema validation", "bound": "O(claims)"},
        {
            "step": "VERIFY (in memory)",
            "work": "re-run NORMALIZE, DETECT, ASSEMBLE; re-check the chain",
            "bound": "O(journal records + the above)",
        },
        {
            "step": "journal and blobs",
            "work": "append, fsync, rename on a local file system",
            "bound": "assumption E-2",
        },
        {"step": "investigation lock", "work": "flock LOCK_EX | LOCK_NB", "bound": "returns at once (busy or held)"},
    ]
    out["assumptions"] = {
        "E-1": "local file reads of regular files and SQLite reads of an immutable file complete (no FIFO or device "
        "substituted after Stage 03's lstat checks)",
        "E-2": "write, fsync and rename on the local file system complete (network file systems are not supported, "
        "SPEC 10.1, RA R4-26)",
        "E-3": "the isolated worker creates no process outside its session, so killing the session group closes its "
        "pipes and communicate() returns",
        "E-4": "the process is not suspended (SIGSTOP) or starved; wall-clock bounds are bounds on the controller's "
        "own waiting",
        "E-5": "BLOCKED is not a wait inside the controller: the process exits and a later invocation resumes; the "
        "calendar time until not_before is set by the server's Retry-After and the operator, and is not part of the "
        "operational bound",
    }
    return out


def _serve_once(script: list[tuple[float, bytes]]) -> int:
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = srv.getsockname()[1]

    def serve() -> None:
        conn, _ = srv.accept()
        try:
            conn.recv(65536)
            for delay, data in script:
                time.sleep(delay)
                conn.sendall(data)
            time.sleep(0.2)
        finally:
            conn.close()
            srv.close()

    threading.Thread(target=serve, daemon=True).start()
    return port


def _measure(script: list[tuple[float, bytes]], timeout: float) -> dict[str, Any]:
    port = _serve_once(script)
    started = time.monotonic()
    outcome: str
    try:
        raw = urllib_transport(f"http://127.0.0.1:{port}/", {}, timeout)
        body = b"".join(raw.chunks)
        outcome = f"status {raw.status}, body {body!r}"
    except TransportError as exc:
        outcome = f"TransportError {exc.code}"
    return {"timeout_s": timeout, "elapsed_s": round(time.monotonic() - started, 2), "outcome": outcome}


def experiments() -> dict[str, Any]:
    slow = [(0.0, b"HTTP/1.1 200 OK\r\n")] + [(0.5, b"X")] * 12 + [(0.0, b"-a: b\r\nContent-Length: 2\r\n\r\nok")]
    cont = [(0.5, b"HTTP/1.1 100 Continue\r\n\r\n")] * 12 + [(0.0, b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok")]
    return {
        "slow_header_drip": {"server": "status line, then one header byte every 0.5 s for 6 s", **_measure(slow, 1.0)},
        "endless_100_continue": {
            "server": "a '100 Continue' interim response every 0.5 s for 6 s",
            **_measure(cont, 1.0),
        },
        "transport": "citerift.wiki.fetch.urllib_transport (the default transport of Stage 03 live captures)",
    }


def conclusion(sym: dict[str, Any], exp: dict[str, Any], model: dict[str, Any] | None) -> dict[str, Any]:
    over = [k for k, v in exp.items() if isinstance(v, dict) and v.get("elapsed_s", 0) > 2 * v.get("timeout_s", 0)]
    return {
        "controller": "bounded: attempts, records and cycles are finite in every scenario of the exhaustive model "
        "(no record is appended inside any cycle)" + (f"; max attempts {model}" if model else ""),
        "retained_bundle_path": "bounded under assumptions E-1 to E-5: "
        f"{sym['retained_bound_s']['isolated_workers']} s of isolated-worker time plus finite local work",
        "live_capture_path": "NOT bounded by the configured limits" if over else "bounded as designed",
        "evidence": over,
        "f11_result": "BLOCKED ON F-11" if over else "BOUNDED",
        "recommendation": (
            "Before Step 7, bound each live ACQUIRE attempt at the Stage 04 boundary, without changing Stage 03: run "
            "the capture in a child process in its own session and kill the session after T_acq = deadline_s + "
            "op_timeout_s + 30 s (240 s with the configured values); record the kill as a retryable ACQUIRE failure "
            "ACQUIRE_WALL_CLOCK_EXCEEDED counted in phi. Then live ACQUIRE <= (A_max + F_max) x T_acq = 9 x 240 = "
            "2160 s and the investigation's operational bound is that plus the retained-path terms. An "
            "investigation-level total budget is then a derived constant, not a separate timer. Owner decision."
            if over
            else "No timer: the machine is provably bounded."
        ),
    }


def run(out: Path | None = None, run_experiments: bool = True) -> dict[str, Any]:
    sym = symbolic()
    exp = experiments() if run_experiments else {}
    model_peaks: Any = None
    summary_path = None if out is None else out / "controller_model_summary.json"
    if summary_path is not None and summary_path.exists():
        cm = json.loads(summary_path.read_text())
        model_peaks = {r["scenario"]["request"]: r["max_attempts_per_step"] for r in cm["scenarios"]}
    result = {"symbolic": sym, "experiments": exp, "conclusion": conclusion(sym, exp, model_peaks)}
    if out is not None:
        out.mkdir(parents=True, exist_ok=True)
        (out / "f11_bounds.json").write_text(json.dumps(result, indent=1, sort_keys=True) + "\n")
    return result


if __name__ == "__main__":
    r = run(Path(sys.argv[1]) if len(sys.argv) > 1 else None)
    print(
        json.dumps(
            {
                "experiments": r["experiments"],
                "conclusion": r["conclusion"],
                "attempts": r["symbolic"]["attempts"],
                "records": r["symbolic"]["execution_records"],
                "workers": r["symbolic"]["isolated_worker_s"],
            },
            indent=1,
        )
    )
