# Retry-After and cooldown audit, R1-R10 (2026-11-02)

**Authority.** The owner's instruction of 2026-11-02, section 5 (DECISIONS.md D-034): "Retry-After is already
implemented. Do not rebuild it from scratch."

**Method.**

- Each requirement was checked against the code (`src/citerift/wiki/fetch.py`, the capture scripts) and the
  existing tests.
- Missing cases got new tests (`tests/stage03/test_wiki_retry_after_audit.py`).
- Each defect was fixed only after a failing test showed it.
- The fail-first evidence is in `../../review/failfirst/retry-after-r8/`:
  - `pytest-before-f4d07c4.txt`: 6 failed, 19 passed;
  - `pytest-after.txt`;
  - `old_driver_restart_demo.py` with its output.

No live 429 was provoked.

| Req | What is required | Finding | Evidence |
|---|---|---|---|
| R1 | HTTP 429 honours Retry-After | Met. The wait starts at the end of the answer and is never shortened (`max(min_interval, retry_after)`). | `test_plan_honors_retry_after_and_never_shortens_it`, `test_rate_limited_then_answered_waits_the_retry_after`, `test_a_server_wait_is_honored_from_the_end_of_the_answer[429]` |
| R2 | 503 and maxlag, including HTTP 200 API errors | Met. 502/503/504 are retryable, and so are the API errors `maxlag`/`ratelimited` inside an HTTP 200. The Retry-After header is read for every status. Every source request carries `maxlag=5`. | `test_api_maxlag_is_retried_and_other_api_errors_are_final`, `test_a_server_wait_is_honored_from_the_end_of_the_answer[maxlag-200, 503]`, `test_maxlag_with_an_unreadable_retry_after_stops`, `test_maxlag_past_the_deadline_is_deferred_with_not_before` |
| R3 | Header parsing edge cases | **Defect G-2, fixed** (below). The other cases were already met: delta-seconds, the three HTTP-date forms, past dates (0 s), negative or non-ASCII digits, values out of range, and an unusable value stopping the capture instead of falling back to a shorter backoff. | `test_retry_after_seconds_and_http_dates`, `test_wiki_retry_after_dates_and_ranges`, `test_retry_after_edge_cases` |
| R4 | Truthful deferral at the deadline | Met. A wait past the 180 s deadline ends `DEFERRED_RETRY_AFTER` with `not_before`, and makes no further request. The last attempt's Retry-After is recorded even when attempts are exhausted. | `test_plan_defers_past_the_deadline_with_not_before`, `test_long_retry_after_ends_deferred_without_another_request`, `test_wiki_retry_after_on_the_last_attempt_is_recorded_and_shared` |
| R5 | Budgets and no infinite loops; network failures | Met. There are at most 3 attempts per operation and one global deadline per capture. Timeouts and connection failures are retried within that budget. Every other transport error is final. | `test_server_errors_stop_after_three_attempts`, `test_timeouts_are_retried_and_connection_refusals_recorded`, `test_network_failures_never_exceed_the_attempt_budget`, simulation `fetch_policy_sim.py` (I1-I8) |
| R6 | Cross-process gate; interrupted and stale locks | **Defect G-1, fixed** (below). Already met: one request in flight across processes; the interval and the server's `not_before` shared through the gate file; a symlinked lock refused; an unreadable record treated as "wait the full interval". A stale lock cannot occur, because `flock` is released by the kernel when the holder dies. | `test_gate_keeps_one_request_in_flight_across_holders`, `test_gate_enforces_the_interval_recorded_by_another_process`, `test_an_attempt_interrupted_by_a_killed_process_still_counts_for_the_interval`, `test_a_killed_holder_never_leaves_the_gate_busy`, `test_an_unreadable_gate_record_waits_the_full_interval` |
| R7 | Server waits survive restarts | Met. The gate file stores `not_before` in wall-clock time, so every later process, including one started after a crash, defers instead of requesting early. | `test_a_recorded_server_wait_holds_for_every_later_process` |
| R8 | Resume after deferral: persisted work, `not_before` respected after a restart, no repeated successful capture, idempotent, no duplicate workers, no new infrastructure | **Not met by the earlier drivers; a new driver was added** (below). | `test_campaign_capture_driver.py` (16 tests, including the simulation), simulation `campaign_driver_sim.py` (C1-C7) |
| R9 | Wikimedia policy | Met. The User-Agent is descriptive and has a contact (`CITERIFT-wiki/1.0 (…; contact via GitHub issues)`). Only the two fixed HTTPS hosts are used, with no rotation of identity, host, address or proxy. One request is in flight per host machine, at least 10 s apart. `maxlag=5` is set. Responses are gzip. | `test_only_the_two_fixed_https_hosts_are_ever_requested`, `test_attempts_keep_the_minimum_interval_within_a_capture` |
| R10 | Deterministic simulation, scripted transports, no live 429 | Met. Every test above uses scripted transports and clocks, or a real lock file shared with a child process. There are two seeded simulations. | `simulations/stage03/fetch_policy_sim.py` (400 sequences, 0 failures), `simulations/stage03/campaign_driver_sim.py` (300 sequences, 0 failures) |

## Defects fixed

### G-1: an interrupted attempt left no record

**Root cause.** `NetworkGate.release` recorded the end of an attempt, but nothing recorded its start. A process
killed during an attempt released the lock (through the kernel) and left the record of the previous attempt. The next
process could then send its request at once, closer than the minimum interval to the killed process's request.

**Fix.** `acquire` writes a provisional record (the current time and the unchanged `not_before`) before it returns.
`release` overwrites it as before.

**Before:** the interrupted-attempt test failed; the record still held the old time.

### G-2: the HTTP-date reader guessed

**Root cause.** `email.utils.parsedate_to_datetime` is lenient. A date with an unknown zone (`XYZ`, read as UTC),
an obsolete zone, no zone, or trailing text was accepted. The documented contract is that a value which cannot be
read stops the capture rather than guessing a wait.

**Fix.** Before parsing, the value must match one of these forms; anything else is `RETRY_AFTER_UNREADABLE`:

- IMF-fixdate or its RFC 5322 relatives, with `GMT`, `UT`, `UTC` or a numeric offset. The existing tests accept
  `-0000`, so this form must stay accepted.
- RFC 850.
- asctime.

Delta-seconds parsing is unchanged. Wikimedia sends delta-seconds.

**Before:** 5 parsing cases failed.

## R8: the earlier drivers, and the new one

**Earlier drivers.** `capture_sample.py`, `final_capture.py` and `retry_failed.py` stay unchanged as historical
records.

- They saved the state only after each article.
- They numbered runs from `a1` on every start. After an interruption, a restart asked the CLI for an existing bundle
  path, and the CLI refuses an existing path, so the article was recorded as failed with `BUNDLE_PATH_UNSAFE`
  (`old_driver_restart_demo.out.txt`).
- They had no lock against a second driver on the same directory.
- A deferred article was resumed only by the one retry pass, and only for some codes.

**New driver: `evaluation/scripts/campaign_capture.py`.** It uses only the production CLI, the network gate and
files; there is no scheduler, service or database.

- A fsynced `start`/`end` journal line around every run.
- An atomic state file.
- Recovery that adopts logged runs and records interrupted runs.
- Run numbers that skip every number seen in the state, the log or on disk.
- An exclusive driver lock.
- The 500-attempt and 300 MiB ceilings checked before every run, counting an interrupted run at its worst case.
- At most 4 runs per article; a complete capture is never repeated.
- A deferred article is resumed only after `not_before` plus one second. A long wait ends the driver with exit 4,
  and rerunning the same command resumes it.

## What this does not change

The FetchPolicy values (10 s interval, 3 attempts, 30 s operation timeout, 180 s deadline, 10 s backoff), the hosts,
the User-Agent and the retryable status set.
