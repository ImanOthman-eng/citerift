# Stage 03 adversarial integration review R6 (candidate 5b1dcb0)

Output root: `/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/review-r6/out/`
All repro scripts are in `out/repro/` (`h.py`, `h2.py` are shared helpers on top of `tests/stage03/wiki_support.py`).
Run any of them from the repo root with:
`PYTHONDONTWRITEBYTECODE=1 uv run --offline --frozen python <out>/repro/<script>.py`

## 1. Scope

**Read.** SPECIFICATION (sections touched), FROZEN_PROTOCOL, AMENDMENT_2026-11-02_CONFIRMATION, ANNOTATION_GUIDE_v1.1,
SEMANTIC_DECISION, doi-boundaries/AUDIT, retry-after/AUDIT, REVIEW_FINDINGS (to avoid re-reporting), the retained
enwiki/arwiki Module:Footnotes sources, the complete diff `eca4389..5b1dcb0` of `src/`, `campaign_capture.py`,
`select_confirmation.py`, `exposure_set.py`, `warning_challenge.py`, `reserve_step.py`, `disagreements_v2.py`,
`evaluate_v2.py`, plus the frozen `evaluate.py`, `disagreements.py`, `run_holdout.py`, `reserve_decision.py` that the
campaign reuses.

**Ran.**
- Synthetic bundles through the production capture code (no network at any point; the gate/driver/draw repros use a
  transport that raises if it is ever called, and it never was).
- `tests/stage03` complete: all dots, no `F`/`E` (`out/pytest_stage03.log`; part of that run saw the tokenizer edit
  described in RR-13).
- Extraction of every retained real bundle that contains `{{sfn` (6 bundles).
- Wheel: `uv build --offline --wheel` succeeded (`out/dist/`). Installing its dependencies offline is impossible (not
  in the uv cache), so I unzipped the wheel and ran its code with the repo venv's third-party packages and the
  editable `src` path removed. For two synthetic bundles (en, ar) `extract`, `verify` and `replay` through the wheel
  code with `CITERIFT_SCHEMAS` set gave byte-identical extraction documents (same SHA-256) as the source tree, exit
  codes 6 (partial, no render) / 0 / 0. Without `CITERIFT_SCHEMAS` the wheel fails closed with
  `SchemaRootUnavailable` (declared as R13, not reported).

**Could not check.** Anything that needs MediaWiki itself or live Parsoid output (whether arwiki `Template:Sfnp` uses
Module:Footnotes `sfn` semantics; arwiki concern vocabulary in a rendered note); Python 3.13; the rest of the
repository suite outside `tests/stage03`; a real SIGKILL of a driver or CLI (I simulated the kill points in-process).

**Side effects to be aware of.** The repo had differences from HEAD that are not mine: modified
`docs/.../AMENDMENT_2026-11-02_CONFIRMATION.md` (before I started), and during the review `src/citerift/wiki/source.py`
(`mwparserfromhell.parser.use_c = False`, MF-1) plus untracked `review/failfirst/mf-1/` and
`tests/stage03/test_wiki_mf1_tokenizer.py`. Before I set `PYTHONDONTWRITEBYTECODE`, some of my importlib-based repros
may have written gitignored `__pycache__` files under `docs/verification/stage-03/*/scripts/` (they may equally come
from that other activity). I created, modified and deleted no tracked or untracked source file.

## 2. Findings

| Id | Severity | Area | Title | Introduced in eca4389..5b1dcb0? |
|---|---|---|---|---|
| RR-1 | high | ceilings, failure accounting | Runs that make no HTTP request are charged the full worst case (6 attempts, 20 MiB); the driver and the draw hit a phantom ceiling after 14 runs | yes (7c2b260, 5b1dcb0) |
| RR-2 | high | draw, Retry-After, study validity | A server wait longer than one operation's deadline makes every draw request fail instantly; all `list=random` batches of a wiki are burnt, the frame is empty, no resume | yes (5b1dcb0) |
| RR-3 | medium | Retry-After at driver level | A 429 with an unreadable or out-of-range Retry-After ends the capture by design, but the driver re-runs the article after the 10 s gate interval | yes (7c2b260) |
| RR-4 | medium | crash recovery | A journal line torn by a kill makes every later driver start (and the draw's ceiling check) raise `JSONDecodeError` | yes (7c2b260) |
| RR-5 | low | short-footnote identity | Content key compares template spellings and raw `ref=`, not generated text: redirect aliases of one template give a false `conflicting_definitions` | yes (cb305bf) |
| RR-6 | low | crash recovery | A complete capture is repeated when the driver dies after the CLI published the bundle but before the `end` line | yes (7c2b260) |
| RR-7 | low | reserve rule | `reserve_step.decide` treats an unresolved (deferred-pending) article as "0 counts" and names the next block | yes (5b1dcb0) |
| RR-8 | low | scoring input | `run_holdout.py` silently leaves captured articles out of `score_spec.json` when their label is not in its single lock directory | pre-existing script, new use |
| RR-9 | low | challenge window | `warning_challenge.marker_calls` misses `{{Template:Retracted}}`-style calls (capital `Template:`, any `Template:` on arwiki) | yes (5b1dcb0) |
| RR-10 | informational | gate | An empty or partial gate record imposes no wait (two-step `ftruncate`+`pwrite` in `acquire` and `release`) | G-1 added a second window (7c2b260) |
| RR-11 | informational | short-footnote identity | Argument trim set `" \t\n\r\f\v\0"` differs from `mw.text.trim`; `Smith\v` merges with `Smith` | yes (cb305bf) |
| RR-12 | informational | ceilings | `RUN_WORST_BYTES` (20.06 MiB) is below what one run can accept under `FetchPolicy` (up to 64 MiB) | yes (7c2b260) |
| RR-13 | informational | candidate identity, procedure | Working tree is not the candidate; the acquisition time limit has no enforcement in any tool; an interrupted draw is not resumable | n/a |

Count: critical 0, high 2, medium 2, low 5, informational 4.

## 3. Details

### RR-1 (high) Phantom ceiling: attempt-less runs are charged the worst case

- **Where.** `docs/verification/stage-03/evaluation/scripts/campaign_capture.py:115-133` (`used`, lines 125-128:
  `if not recorded: attempts += RUN_WORST_ATTEMPTS; accepted += RUN_WORST_BYTES`), used at `:290-291`; the same ledger
  is used by `confirmation-2026-11/scripts/select_confirmation.py:96-102`.
- **What.** `used()` charges 6 attempts and 20.06 MiB to every `end` record whose capture has no recorded attempt. A
  run answered by the shared gate (`DEFERRED_RETRY_AFTER`, `NETWORK_GATE_BUSY`) or refused before the first request
  makes zero HTTP requests, but is charged as if it had made six large ones.
- **Repro.** `repro/rr_driver_ceiling.py` (gate file holds a 1-hour server wait; transport raises if used; 40-article plan):

  ```
  holdout/en-1000: run 1 deferred -> deferred
  ... (14 articles)
  ceiling: not starting holdout/en-1014 (84 attempts, 294518784 bytes)
  driver exit: 2 (2 = ceiling reached)
  runs executed: 14
  real HTTP attempts in all end records: 0
  charged attempts, MiB: 84 280.9
  first end record: status deferred codes ['DEFERRED_RETRY_AFTER'] attempts []
  ```
  After a long Retry-After, the first article defers legitimately; every following article's run is gate-deferred
  with zero requests, and after 14 of them the byte ceiling (300 MiB) is "reached". The driver stops with exit 2 and
  writes `ceiling.json`; no tool resets the journal. Under AMENDMENT 4/6 the remaining articles would be recorded as
  not captured and a reserve block "that cannot be captured leaves its minimum unmet", although the real use was
  0 attempts.
- **Expected.** AMENDMENT 6: "with an interrupted run counted at its worst case". Only a run with a `start` and no
  `end` has unknown cost; a finished run with no attempts cost nothing.
- **Smallest repair.** In `used()` charge the worst case only for `start` without `end` (or an unparsable stdout);
  for an `end` charge the recorded attempts, zero included.
- **Study impact.** An acquisition can be aborted by one rate-limit episode without a single wasted request, and then
  cannot be resumed: minimum denominators unmet for a reason unrelated to Wikipedia.

### RR-2 (high) One long Retry-After empties the draw

- **Where.** `select_confirmation.py:93-131` (`LiveGet.__call__` returns `None` for every failure including
  `DEFERRED_RETRY_AFTER`; `answer.not_before` is only journalled) and `:139-144` (`draw`: on `None` it records a failed
  batch and loops at once; each failed batch counts against `MAX_BATCHES`).
- **Repro.** `repro/rr_draw_deferral.py` (gate holds a 400 s server wait, transport raises if used):

  ```
  elapsed s: 0.01
  batches drawn: 6 failures: ['batch 1: list=random failed', ... 'batch 6: list=random failed']
  eligible: 0 initial: 0 reserve blocks: 0
  requests journalled: 6 codes: {'DEFERRED_RETRY_AFTER'} http attempts: 0
  campaign ledger charged: 36 attempts, 120.4 MiB (real requests: 0)
  ```
  The six arwiki batches are consumed in 10 ms without waiting; the arwiki frame is empty. `main()` then writes
  `SELECTION.json` and refuses to draw again (`:266-267` "the draw is made once"); `list=random` cannot be repeated.
- **Expected.** The shortfall rule (AMENDMENT 4) covers a small draw, not a draw lost to a wait that the repo's own
  driver is built to respect (retry-after AUDIT R4/R7/R8: a deferred operation resumes after `not_before`).
- **Smallest repair.** In `draw`/`challenge`, on `DEFERRED_RETRY_AFTER` (or any retryable code) sleep until
  `not_before` + 1 s, or abort without writing `SELECTION.json`, instead of counting a batch.
- **Same pattern.** A failed extlinks chunk silently removes up to 50 articles from eligibility (`:157-159`); it is
  recorded in `failures`, but eligibility then depends on network state.

### RR-3 (medium) The driver retries a 429 whose Retry-After was unusable

- **Where.** `campaign_capture.py:156-174` (`next_step`, lines 172-173), `:136-153` (`summarize` ignores
  `attempts[*].retry_after_problem`); `RETRYABLE` (`:60-71`) includes `HTTP_RATE_LIMITED`.
- **Repro.** `repro/rr_driver_ra_problem.py`:

  ```
  Retry-After='soon': status=failed codes=['HTTP_RATE_LIMITED'] problem=RETRY_AFTER_UNREADABLE deferred=False requests=1
     driver next_step: ('run', None)
  Retry-After='34560000': ... problem=RETRY_AFTER_OUT_OF_RANGE ...   driver next_step: ('run', None)
  Retry-After='Fri, 06 Nov 2026 10:00:00 XYZ': ... problem=RETRY_AFTER_UNREADABLE ... driver next_step: ('run', None)
  ```
- **Expected.** retry-after AUDIT R3/R4 and `plan_next` (`fetch.py`, "never retry earlier on a guessed backoff"):
  the capture stops for exactly this reason; the driver then repeats the request after the 10 s gate interval (a
  400-day request is retried in 10 s). The gate does not hold a wait either, because `retry_after_s` is `None` in that case.
- **Smallest repair.** In `summarize`/`next_step`, treat a run with any attempt carrying `retry_after_problem` as final.

### RR-4 (medium) A torn journal line stops the driver for good

- **Where.** `campaign_capture.py:101-105` (`_append` can leave a partial last line), `:108-112` (`_journal`: `json.loads`
  on every line), called at `:270` and `:289`; also `select_confirmation.py:97`.
- **Repro.** `repro/rr_driver_torn_journal.py`:
  ```
  driver killed mid-append
  journal tail: ':55+00:00", "exit": 0, "stdout": {"status": "complete", "bun'
  rerun -> JSONDecodeError Unterminated string starting at: line 1 column 130 (char 129)
  ```
  The `end` line embeds the whole capture JSON (tens of KB), so a kill during that write is plausible.
- **Expected.** AUDIT R8 / AMENDMENT 6: "recovery after an interruption". A torn final line is the textbook
  interruption; it must read as "no `end`" (the run is then interrupted), not abort the driver.
- **Smallest repair.** In `_journal`, ignore an unparsable final line; a bad line elsewhere stays an error.

### RR-5 (low) Short-footnote content key is textual: aliases and anchor-equal `ref=` give false conflicts

- **Where.** `src/citerift/wiki/source.py:257` (`content = json.dumps([template, ...])`) with `template =
  rec.canonical or rec.raw_name.strip()` (`:538`); state rule `model.py:227-255`.
- **Repro.** `repro/rr_alias.py`, `repro/rr_sfn_probe.py`, `repro/rr_v2_sfn_conflict.py`:
  ```
  'A{{sfn|Smith|2001}} B{{sf|Smith|2001}}'          [('', 'conflicting_definitions', 2, 2)] REF_DEFINITIONS_CONFLICT
  'A{{sfnp|Smith|2001}} B{{Sfnb|Smith|2001}}'        [('', 'conflicting_definitions', 2, 2)] REF_DEFINITIONS_CONFLICT
  ar 'أ{{Sfn|سميث|2001}} ب{{Sf|سميث|2001}}'           [('', 'conflicting_definitions', 2, 2)] REF_DEFINITIONS_CONFLICT
  ref=a b  vs ref=a_b (same anchorEncode)            conflicting_definitions
  ignore-err=yes vs none (text may differ)           identical_definitions
  scorer v2, 'sfn / sf / sfn'                        engine defs=3, v2 predicted defs=2 (guide v1.1: 1)
  ```
- **Expected.** The repo's own evidence (`calibration/profile_evidence.json`) shows `Sf`, `Snf`, `Hf`, `Sfnnb`,
  `Shortened footnote` are redirects of `Template:Sfn` and `Sfb`, `Sfnb` of `Template:Sfnp` on enwiki, and `HarvRef`,
  `Harvnp`, `Sf` of `قالب:Sfn` on arwiki. A redirect is the same template, with the same generated text, so MediaWiki
  shows one reference and no Cite conflict (SEMANTIC_DECISION D2: content "decided by the template variant").
  Guide v1.1 3.1 labels a repeat of the same reference as a use only; the engine reports two reference definitions
  and `REF_DEFINITIONS_CONFLICT`. Likewise `ref=` values equal after `mw.uri.anchorEncode` (`a b`, `a_b`), and
  `ignore-err=yes` (removes the "no target" error text from the generated note) are not decided by generated text.
  Scorer v2 keeps, in a conflicting container, one definition per distinct source text (declared limitation), so the
  alias spelling remains a predicted definition and costs G5a precision.
- **Real-data impact.** None observed: none of the 6 retained real bundles with short footnotes has a
  `conflicting_definitions` container (`rr_real_sfn.py`). It matters for articles that mix redirect spellings.
- **Smallest repair.** Map the profile's `sfn` family names to one canonical key per family (Sfn group, Sfnp group) in
  the content key, and normalise `ref=` with the anchor encoding.
- **Unverified (SPECULATIVE).** The arwiki `Sfnp` entry uses the arwiki `sfn` identity rules (no group, no `at`), but
  only `Template:Sfn` and its module were retained; that arwiki `Sfnp` shares them is not evidenced in the repo.

### RR-6 (low) A complete capture is repeated after a crash between CLI return and the `end` line

- **Where.** `campaign_capture.py:192-218` (`recover`: a `start` without `end` becomes `DRIVER_INTERRUPTED`; the bundle
  on disk is not examined), `:156-164` (`next_step` -> `run`).
- **Repro.** `repro/rr_driver_complete_repeat.py`:
  ```
  killed after run 1 published a bundle, before its end line
  holdout/en-7: run 2 complete -> complete
  rerun rc 0 | CLI calls: 2 | bundles on disk: ['en-7-a1', 'en-7-a2']
  state runs: [(1, None, ['DRIVER_INTERRUPTED']), (2, 'complete', [])] final: 2
  ```
- **Expected.** AMENDMENT 6 / AUDIT R8: "a complete capture is never repeated". The second run pins the latest
  revision, which can differ from the one in the orphaned `a1` bundle, which stays on disk unreferenced.
- **Smallest repair.** In `recover`, adopt a complete, verifiable `capture.json` found at an interrupted run's target.

### RR-7 (low) `reserve_step` has no notion of an unresolved article

- **Where.** `confirmation-2026-11/scripts/reserve_step.py:158-186` (`bundle = (states[k].get("final") or {}).get("bundle")`;
  no bundle gives counts 0).
- **Repro.** `repro/rr_reserve_pending.py` (en-2 is deferred until tomorrow, driver exit 4):
  ```
  ar next_block: reserve1 | included: ['holdout/ar-1', 'holdout/ar-2'] | at_maximum: False
  en next_block: reserve1 | included: ['holdout/en-1', 'holdout/en-2'] | at_maximum: False
  ```
- **Expected.** AMENDMENT 4: locked counts plus capture state. A pending article is not a final capture state;
  counting it as zero (and later capturing it) makes the block decision depend on when it is run. No label leaks, but
  the path is unguarded. Because the driver enters every plan article into the state at load, a plan that holds
  reserve blocks early also makes `decide` see them as captured.
- **Smallest repair.** `SystemExit` when any included article has a run that `next_step` would continue.

### RR-8 (low) `run_holdout.py` drops captured-but-unlocked articles silently

- **Where.** `docs/.../evaluation/scripts/run_holdout.py:85-87` (`if f"{name}.json" not in lock: row["annotation"] = None;
  continue`); it takes one `ANNOTATION_DIR`, whereas `reserve_step.py` takes several lock directories (per-batch locks,
  AMENDMENT 7).
- **Repro.** `repro/rr_run_holdout_drop.py`:
  ```
  {"articles": 2, "extracted": 2, "verify_or_replay_failed": []}
  score_spec splits: {'holdout': 1}
  runs.json annotation fields: [('holdout/en-1', 'en-1379214029.json'), ('reserve1/en-2', None)]
  ```
  The reserve article is extracted but never scored, and the printed summary does not say so. `reserve_step`
  aborts in the same situation.
- **Expected.** AMENDMENT 8: every selected article counts; scoring uses the locked labels of all blocks.
- **Smallest repair.** Fail (or print a count) when an article with a bundle has no locked label; accept several lock directories.

### RR-9 (low) Challenge window misses `{{Template:...}}` calls

- **Where.** `warning_challenge.py:58-62` (`pat`: the prefix `(?:template|قالب)` is lower-case only, no `re.IGNORECASE`;
  arwiki lacks `Template:`; `{{RETRACTED}}` also missed).
- **Repro.** `repro/rr_marker_calls.py`: `{{Template:Retracted|doi=1}}` -> `[]`, `{{template:Retracted|doi=1}}` -> `[0]`,
  arwiki `{{Template:Retracted|x}}` -> `[]`.
- **Expected.** AMENDMENT 9: the window starts at "a seeded-random marker-template call"; MediaWiki reads the
  namespace prefix case-insensitively (`profile.canonical_template` does). Articles whose calls are written that way
  get the frozen window, which may not contain the warning, so fewer labelled warnings enter the denominator. It does
  not depend on a label or a prediction, so it is not a leak.
- **Smallest repair.** `re.IGNORECASE` for the prefix and `Template` added to the Arabic prefixes.

### RR-10 (informational) Gate record: empty or partial record means no wait

- **Where.** `fetch.py:371-372` (`ftruncate` then `pwrite` in `acquire`, G-1) and `:404-405` (same in `release`).
- **Repro.** `repro/rr_gate_empty.py`:
  ```
  record of an attempt that started now                   acquire -> None after waiting 3.00s (min interval 3 s)
  empty record (killed between ftruncate and pwrite)      acquire -> None after waiting 0.00s (min interval 3 s)
  truncated record '17' (partial write)                   acquire -> None after waiting 0.00s (min interval 3 s)
  ```
  The window between the two calls is microseconds; I did not provoke a real kill there (the race is SPECULATIVE; the
  empty-record behaviour is confirmed). Writing the new record first and truncating to its length closes it.

### RR-11 (informational) Positional trim set differs from Lua

- **Where.** `source.py:198` `_ARG_TRIM = " \t\n\r\f\v\0"`, applied to positional values in `_footnote_identity` (`:233`).
- **Repro.** `repro/rr_sfn_probe.py`: `{{sfn|Smith\x0b|2001}}` with `{{sfn|Smith|2001}}` gives one `identical_definitions`
  container.
- **Expected.** Positional values are trimmed by `mw.text.trim` (`\t\r\n\f` and space only); `\v` and NUL stay, so
  MediaWiki keeps the names apart. The documented claim "never merges calls MediaWiki keeps apart" is not strictly
  true; no realistic input.

### RR-12 (informational) The pre-run worst case is not an upper bound

- **Where.** `campaign_capture.py:54-55` (`RUN_WORST_BYTES` = 4 MiB + 64 KiB + 16 MiB) against `fetch.py:53`
  (`max_body_bytes` = 32 MiB per accepted attempt; the 4 and 16 MiB limits apply after the body was read and accepted).
  One run can add up to 64 MiB of accepted bytes, so the 300 MiB ceiling can be exceeded by about 44 MiB on the last
  permitted run. Static finding, not exercised; real articles average 0.2 MiB.

### RR-13 (informational) Candidate identity and unenforced limits

- The working tree differs from `5b1dcb0` (see Scope). The amendment's section 7 (models) is edited but uncommitted;
  `source.py` and tests changed during the review. The amendment says it was committed before any draw, so any commit
  of that edit should be dated and referenced.
- The acquisition limit "2026-11-14 23:59 UTC" (AMENDMENT 6) is enforced by no tool (checked `campaign_capture.py`,
  `select_confirmation.py`).
- `select_confirmation.py:262-273`: an interrupted draw leaves no `SELECTION.json`, so a rerun draws a different
  `list=random` batch; request keys `selection/request-NNNN` restart at 0001, so `used()` no longer sees the old
  interrupted `start`. Not outcome-dependent, but it is a degree of freedom in the draw.

## 4. Checked, no defect found

- **sfn identity, new code.** `{{sfn}}` vs `{{Sfn}}` vs `{{Template:Sfn}}`; positional vs `1=`/`2=` (explicit later value wins);
  `p`/`page`, `pp`/`pages`, `at`/`loc` (en), `loc` only and no `group` (ar); empty `p=` shadowing `page=`; `ps=.` vs default;
  non-year P5 (engine splits, shared rendered note withdrawn as `RENDER_NOTE_AMBIGUOUS`, no attachment; `rr_sfn_render2.py`);
  identical calls (container matched, both uses linked to `_1-0`/`_1-1`, warning in the shared note recognised).
- **Real data.** All 6 retained real bundles with short footnotes extract with matched renders and no conflict.
- **Group/identity.** en `group=` separates references; ar ignores it; different groups never merge.
- **D-1 / D-2.** `&amp;`, `&#x26;`, `&amp;amp;` (decoded once), entity in `url=`/`doi=` bare URLs, `%2F`/`%2f` in a
  publisher path with trailing route; anchors cover the raw text exactly (`rr_anchor.py`, `rr_entity.py`). A lone
  surrogate entity (`&#xD800;`) raises in non-isolated extract and gives `EXTRACTION_WORKER_FAILED` in the worker
  (pre-existing, honest failure).
- **parse_retry_after.** Delta-seconds, the three date forms, GMT/UT/UTC/numeric zones, unknown zone, missing zone, huge
  and non-ASCII digits, 31 February: unreadable or out of range as designed. The `fullmatch` form accepts a 2-3 digit
  year (`94`, `994`), and Python reads `70` as 1970 where RFC 9110 says 2070; no real server sends these.
- **NetworkGate.** The provisional record holds the interval after a kill; the server's `not_before` is kept; one
  request in flight; symlinked lock refused (existing tests, `rr_gate_empty.py`).
- **Decompression and size.** `_read_body`: per-chunk `max_length`, unconsumed tail, multi-member gzip, content-length
  check; 200000-deep JSON ends in `StrictJSONError`, not an unhandled `RecursionError`.
- **Scorer v2 vs disagreement lists.** `disagreements_v2` loads before it predicts and patches the same module object;
  its per-item logic matches `score_article` for definitions, units, uses, bindings, render links, identifiers and
  markers (the list is a superset only for render abstentions and role disagreements, as designed). `evaluate_v2.score`
  sets `current["text"]` before each prediction. The declared limitation (conflict per source text) is as declared.
- **Study tooling and leakage.** `exposure_set.py` covers every `page_id`/title of all 105 `capture.json` files in the tree
  (0 missing); order, salts and exclusions match the amendment; no label, prediction or extraction is read in
  `select_confirmation.py`, `exposure_set.py` or `reserve_step.py` (only locked counts and capture state).
- **Roles.** Title/quote links -> `textual_mention`; a marker wrapping or wrapped by a cite template -> `marker_target`;
  archive-url nesting -> excluded; `{{doi}}` in `id=` -> `identifier_link`; ar and en alike (`rr_roles.py`). No promotion found.
- **Warning vocabulary.** en and ar variants incl. soft hyphen, zero-width characters, tatweel, diacritics, `مسحوبة`;
  `تم سحبه` -> ambiguous. SPECULATIVE only: Arabic `تعبير عن قلق` and `تراجع المؤلفون` give no warning (not evidenced as real arwiki output).
- **Stage boundaries.** `git diff 33e03ad..5b1dcb0 -- src/citerift/retraction src/citerift/governance src/citerift/contracts
  schemas/governance .github` is empty; the registry/PROJECT_STATUS change is the owner-referenced transition only.
- **Installed wheel.** Includes `wiki/data/profile-v1.json`; behaviour parity shown above.
- **Resource use of the new code.** 20 000 distinct or identical short-footnote calls: 8.1 s / 6.1 s isolated extract, near-linear.
- **Existing tests.** `tests/stage03` complete: no failure.
