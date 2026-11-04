# Adversarial follow-up review R7 (candidate 0dfef1c, delta since 5b1dcb0)

Reviewer: independent, did not write the code. Worktree: `/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/r7wt` (detached at 0dfef1c).
All scripts and outputs are under `/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/review-r7/out/` (repro scripts in `repro/`). No network request was made; the driver and the draw were exercised with stand-in CLIs and fetch functions only.

## 1. Scope

`git diff 5b1dcb0..0dfef1c`: commit b00fa65 (MF-1, pure-Python tokenizer) and commit 0dfef1c (fixes for RR-1..RR-13): `campaign_capture.py`, `select_confirmation.py`, `reserve_step.py`, `run_confirmation.py`, `warning_challenge.py`, `wiki/{fetch,profile,source}.py`, the driver simulation, tests, amendment section 11 (and an edit to section 7, see RF7-3), SEMANTIC_DECISION section 6. R6 findings are not re-reported except where the fix is wrong or incomplete.

## 2. What I ran

| Check | Result |
|---|---|
| `git diff 33e03ad..0dfef1c -- src/citerift/retraction src/citerift/governance src/citerift/contracts schemas/governance .github` | empty (0 lines). `governance/stage_registry.json` is not touched by 5b1dcb0..0dfef1c either. |
| `git diff 5b1dcb0..0dfef1c -- tests/stage03/test_campaign_capture_driver.py tests/stage03/test_confirmation_campaign_tools.py` | Claim holds: only fixtures changed (a `"status": "failed"` key added to the 495-attempt record so it counts as a reported record; the capture states given a `runs` list). All assertions are unchanged. |
| `pytest -p no:cacheprovider tests/stage03` (whole directory) | all dots, no failure (log `pytest_stage03.log`, run with `-q -q` so no summary line); the four touched/new test files separately: 67 passed. |
| `ruff check --no-cache .`, `mypy --cache-dir=<out>` | all checks passed; no issues in 51 files. |
| `simulations/stage03/campaign_driver_sim.py 300 12345` | `failure_count: 0` (killed 233, torn 104 included). |
| Extraction of all 83 retained real bundles with 5b1dcb0 (C tokenizer) and 0dfef1c (`repro/ext_all.py`, `ext_base/` vs `ext_new/`) | 83 compared, 0 differ (so the claim "no retained real bundle changes" holds). |
| C vs pure-Python tokenizer fuzz, 30000 random wikitext strings (`repro/tok_fuzz.py`, `tok_min.py`) | 53 differ; all minimise to bare external links (RF7-1, plus an empty-`Text` token that does not change extraction). |
| Adversarial inputs, C vs Python (`repro/tok_one.py`, `rf_tok_deadline.py`, `rf_tok_big.py`) | RF7-2. |
| Driver, draw, gate, adoption, reserve, marker probes | `repro/rf_*.py`; outputs quoted below. |
| `git status --short` in the worktree at the end | empty. (`.venv/` and `__pycache__/` under `src/` exist and are git-ignored; `uv` built the editable install on first use.) |

## 3. Findings

| id | severity | file:line | title | reproduced |
|---|---|---|---|---|
| RF7-1 | medium | `src/citerift/wiki/source.py:46` | MF-1 changes extraction: the Python tokenizer keeps `:` `;` `!` inside a bare URL, so a bare DOI URL gives a wrong DOI | yes |
| RF7-2 | low | `src/citerift/wiki/source.py:46` | The Python tokenizer is 10-150x slower on unclosed constructs: an 18 KB source goes from 1.4 s to `EXTRACTION_DEADLINE_EXCEEDED` | yes |
| RF7-3 | medium | `protocol/AMENDMENT_2026-11-02_CONFIRMATION.md:183-188` | The model-independence rule of section 7 was rewritten inside the R6-fix commit, with no owner reference and while section 11 says nothing but tool corrections changed | yes (git diff) |
| RF7-4 | low | `evaluation/scripts/campaign_capture.py:131` | `_journal` still uses `str.splitlines()`: U+0085/U+2028/U+2029 inside a journal string make the driver and the draw crash on restart | yes |
| RF7-5 | low | `evaluation/scripts/campaign_capture.py:134-154` | Torn-line repair: a complete JSON final line missing only its `\n` is dropped, and a second tear at the same offset is not kept | yes |
| RF7-6 | low | `evaluation/scripts/campaign_capture.py:200,222` | `retry_after_problems` is read from every attempt of a run, so an odd header on an accepted source response ends retries of an unrelated render failure | yes |
| RF7-7 | informational | `evaluation/scripts/campaign_capture.py:57-58,173-181` | Four kills (unreported runs at 64 MiB each) exhaust the 300 MiB budget with zero real use | yes |
| RF7-8 | informational | `evaluation/confirmation-2026-11/scripts/select_confirmation.py:346` | SELECTION.json is written non-atomically; a torn file blocks the "made once" guard for good | no (SPECULATIVE, reading only) |

### RF7-1 (medium) MF-1 is not behaviour-neutral: bare URLs followed by `:` `;` `!`

- **Where.** `src/citerift/wiki/source.py:46` (`mwparserfromhell.parser.use_c = False`). The claim in `review/failfirst/mf-1/BEFORE_AND_AFTER.md` ("token streams identical on all 84 texts") and in amendment section 11 ("none of them changes an extraction") is true only for the retained corpus.
- **What.** In mwparserfromhell 0.7.2 the pure-Python tokenizer leaves the trailing punctuation `:`, `;` and `!` inside a free external link when a space follows; the C tokenizer (and MediaWiki, which strips `,;.:!?` from a free link) puts it outside. The engine takes the DOI from the link target, so the identifier changes.
- **Repro.** `repro/rf_tok_url_punct.py` (run once with `PYTHONPATH=out/base/src`, i.e. 5b1dcb0, once with the worktree), output `rf_tok_url_punct.out`:
  ```
  C  ': Smith 2001'  -> [('url', 'https://doi.org/10.1234/abc',  '10.1234/abc',  True)]
  Py ': Smith 2001'  -> [('url', 'https://doi.org/10.1234/abc:', '10.1234/abc:', True)]
  C  '; Smith 2001'  -> ... '10.1234/abc'      Py -> '10.1234/abc;'
  C  '! Smith'       -> ... '10.1234/abc'      Py -> '10.1234/abc!'
  ```
  (`.` and `,` are handled identically; text is `Claim.<ref>https://doi.org/10.1234/abc: Smith 2001</ref>`.) Token level: `repro/tok_punct.py`.
- **Expected.** Same identifier as before the change and as MediaWiki: `10.1234/abc`. The wrong value is marked `valid: true`, so nothing flags it, and a bare DOI URL followed by `;` or `:` is an ordinary shape in a reference. The 83 retained bundles contain none, which is why the equivalence probe did not see it. Prospective articles will.
- **Smallest repair.** Either keep the C tokenizer and map a SIGSEGV worker death under `RLIMIT_AS` to `EXTRACTION_MEMORY_EXCEEDED` (the symptom MF-1 fixed), or keep the Python tokenizer and re-trim `[,;.:!?]` from the end of a bare `ExternalLink` url in `_plain`/the identifier scan; in either case widen the equivalence probe with the fuzz corpus (`tok_fuzz.py`) and add a test for `abc: `, `abc; `, `abc! `.

### RF7-2 (low) New failure mode: pathological sources exceed the 30 s worker limit

- **Where.** same line. The Python tokenizer is quadratic or worse on unclosed constructs, and 10-150x slower than C on them.
- **Repro.** `repro/rf_tok_deadline.py N` (source `Intro...` plus `"[[a|" * N`; base = 5b1dcb0), `rf_tok_deadline.out`:
  ```
  N=4500 (18066 bytes)  5b1dcb0: 1.4 s, no extraction failure   0dfef1c: EXTRACTION_DEADLINE_EXCEEDED 30.1 s
  N=2000 (8066 bytes)   0.5 s  vs 8.8 s;   N=3000  0.8 s vs 18.1 s
  ```
  Tokenizer only (`tok_adv2.out`): `<ref>` x5000 (25 KB) C 1.76 s, Python 33.76 s; `[http://a.b ` x1000 C 0.19 s, Python 3.70 s; `[[a|` x2000 C 0.25 s, Python 36.97 s. Realistic large input is fine: the largest retained source repeated to 3.9 MB takes 7.2 s (C) and 9.0 s (Python) (`rf_tok_big.out`), a stray `[[`, `{{`, `{|`, `<ref>` in a 98 KB real source is 0.05-0.11 s; no recursion error was seen (nesting is capped by the tokenizer's own depth limit; C and Python agree on nested inputs).
- **Expected.** A source the previous engine extracted should still extract, or the limit should be documented. The failure is stable and reported (not a crash), so the effect is a few broken pages becoming `EXTRACTION_DEADLINE_EXCEEDED`.
- **Smallest repair.** Same as RF7-1 (keep C, handle the segfault), or document the limit and raise `worker_wall_s`.

### RF7-3 (medium) Protocol rule on model independence rewritten in the fix commit

- **Where.** `protocol/AMENDMENT_2026-11-02_CONFIRMATION.md:183-188` (section 7, "Models"), changed by 0dfef1c.
- **What.** Before: "Evaluators use a different Claude model from the implementing agent, and adjudicators use a third." After: evaluators are "Claude Sonnet", adjudicators "Claude Opus ... different model from the evaluators", with "A third model was planned, but its use was refused for lack of credits on 2026-11-02, before any draw, so this line was corrected then." Section 11 lists the corrections as tool corrections and says no threshold, gate, minimum, size, salt, order or stopping rule changed; it does not mention this edit. There is no reference to the owner's own words (CLAUDE.md: never record an owner decision without one). The implementing agent in this environment is also a Sonnet model (the attribution reminder names Sonnet 5.5), so "a different Claude model from the implementing agent" is not shown by the text "Claude Sonnet"; the adjudicator is no longer required to differ from the implementer. R6 RR-13 had noted this paragraph as an uncommitted edit.
- **Repro.** `git diff 5b1dcb0..0dfef1c -- docs/verification/stage-03/protocol/AMENDMENT_2026-11-02_CONFIRMATION.md`.
- **Expected.** A change to an independence rule is the owner's to make and must cite the owner's instruction; the evaluator and adjudicator model identifiers should be stated so the difference from the implementer can be checked.
- **Smallest repair.** Cite the owner message that accepted two models, name the model versions, list the edit in section 11 (or move it to its own dated amendment), and have the owner review it.

### RF7-4 (low) `str.splitlines()` splits journal lines at U+0085, U+2028, U+2029

- **Where.** `campaign_capture.py:131`. `_append` writes `json.dumps(..., ensure_ascii=False)`, which leaves those characters raw inside strings; the rewritten `_journal` kept `splitlines()` (it is not a line end of the file format, only `\n` is). Pre-existing, but the torn-line rewrite was the place to fix it, and a failure here stops both the driver and the draw (`LiveGet.__init__` and `_once` call `_journal`).
- **Repro.** `repro/rf_unicode_separator.py`:
  ```
  0x2028 -> _journal raises JSONDecodeError Unterminated string starting at: line 1 column 50
  0x85   -> _journal raises JSONDecodeError ...        0x2029 -> same
  ```
- **Expected.** The line is read whole. Reachability is low (an `end` line embeds the CLI's stdout/stderr and API `detail` strings), but the failure is permanent for the campaign.
- **Smallest repair.** `complete.decode("utf-8").split("\n")` instead of `splitlines()` (or `ensure_ascii=True` in `_append`).

### RF7-5 (low) Torn-line repair: two edge cases

- **Where.** `campaign_capture.py:123-131` and `134-154`.
- (a) A final line that is a complete JSON object lacking only its `\n` is treated as torn: not read, moved aside, and truncated. If it was an `end` line the run is re-evaluated as interrupted; a deferral's `not_before` is lost. Repro `repro/rf_torn_valid_json.py`: a `deferred` end line with `not_before` +100000 s is dropped and the article is run again at once (the network gate still holds the real wait, so no request is sent early; the bundle case is rescued by adoption).
- (b) The side file name is `captures.jsonl.torn-at-<cut>` and an existing one is never rewritten. Kill, restart (repair at cut 41), driver appends and is killed again at the same cut: the second torn line is discarded although the docstring and the sim (C8) say the bytes are kept. Repro `repro/rf_torn_twice.py`: `bytes of tear 2 kept anywhere: False`.
- **Smallest repair.** (a) if the fragment parses as a JSON object, append the missing `\n` instead of moving it aside; (b) append to the side file or add a counter to its name.

### RF7-6 (low) `retry_after_problems` has the wrong scope

- **Where.** `campaign_capture.py:200` (set over all attempts) and `:222`. The R6 "smallest repair" asked for any attempt; the planner (`fetch.plan_next`) stops only for the last attempt of an operation.
- **Repro.** `repro/rf_ra_scope.py`: a `partial` run whose source attempt was accepted (200) with an unreadable `Retry-After` and whose render ended `ATTEMPTS_EXHAUSTED` with no Retry-After gives `next_step -> ('done', None)`; without the header on the source attempt it gives `('run', None)`.
- **Expected.** Final only when the attempt that ended the failing operation carries the problem. Practical reach is very small (a malformed header on a 200).
- **Smallest repair.** In `summarize` take the problem from the last attempt of the failing operation (`attempts[-1]` when `code` is not None).

### RF7-7 (informational) Worst-case charging halts the campaign after four kills

- **Where.** `campaign_capture.py:57-58` (`RUN_WORST_BYTES = 64 MiB`) and `used()` (`:173-181`): a start without end, or an end without a reported record, is charged 6 attempts and 64 MiB.
- **Repro.** `repro/rf_ceiling_kills.py`: four starts without ends give `(24 attempts, 268435456 bytes)` and the driver exits 2 with `ceiling.json`, no CLI call. The same applies to a killed draw request. This follows the protocol ("an interrupted run counted at its worst case") and R6 RR-12, but the new bound tightened it from about 20 MiB to 64 MiB per unknown run, so four crashes in a 1-2 hour acquisition end it. A restart after a kill that published a bundle is now charged correctly (adoption).
- **Smallest repair.** None required; the owner should know the budget is four unknown runs, not fourteen.

### RF7-8 (informational, SPECULATIVE) `SELECTION.json` is written non-atomically

- `select_confirmation.py:346` `out.write_text(...)`. A kill during this write leaves a partial file; `main()` then refuses to draw ("the draw is made once") and the file cannot be parsed. The new restart rules only cover a draw stopped before this write. Not reproduced.
- **Smallest repair.** Write to a temp name, fsync, `os.replace`.

## 4. Checked, no defect found

- **Charging rule (`used()`, `reported_attempts()`).** A run is charged zero only when `status` is present and `capture.attempts` is a list that is empty; in `capture_revision` an empty list means no request was made (host check, existing target, or `NetworkGate` returning a code before any attempt), because every attempt is appended to the record right after `fetcher.get` and a CLI crash gives no `status` (worst case). `rf_adoption.py`: a `capture.json` without `attempts` is charged the worst case. `check_url` and gate refusals return `Answer(..., [])`, correctly zero. Draw `end` lines carry `status`, so a gate deferral costs zero and a killed request costs the worst case (`rf_draw.py` a, e).
- **Adoption (`_adopt_published`, `recover`).** `publish_bundle` publishes by atomic no-replace rename, so `capture.json` at the target exists only for a finished bundle. `rf_adoption.py` (stand-in CLI killed after publishing): complete bundle adopted (1 CLI call, charged its recorded attempts, no double charge), `partial` with render deferral or retryable render failure adopted and retried exactly as an unkilled run, a `failed` or unreadable record is not adopted (worst case and a new run number; the path is never reused). Draw `start` lines (no state record) never reach adoption. Idempotent on restart.
- **Torn journal.** `_journal` ignores an unterminated tail; `repair_journal` cuts at the last `\n` under the driver lock (draw and driver both hold `driver.lock`), writes and fsyncs the side file before truncating, so a kill between the two loses nothing; a reader without the lock sees the same complete lines before and after. A malformed complete line stays an error. Sim C8 passes. (Edge cases: RF7-4, RF7-5.)
- **Draw wait loop.** `rf_draw.py`: a gate deferral sleeps `not_before + 1 s - now` once and re-sends (121 s for +120 s); `not_before` over 3600 s raises `SystemExit` with no sleep; endless deferrals with a clock that does not advance stop after 6 calls and 5 sleeps (`DRAW_MAX_DEFERRALS`); a retryable failure is sent once more, a failure with an unreadable Retry-After is not; every pass re-checks the ceiling and the acquisition limit; a past `not_before` sleeps 0 and the network gate still enforces the real wait. It cannot loop forever, wait less than asked (the gate is the authority), or pass the ceiling. Numbering continues after an interrupted draw and `earlier_interrupted_draw_requests` lists the earlier keys.
- **Reserve step / run_confirmation.** `decide` reads only capture states and locked-label counts (the reserve rule of section 4); no extraction, prediction or disagreement enters it. A pending deferral, a due-but-unrun deferral, an interrupted article and a partly run block all stop the decision, so it no longer depends on when it is made; after a `ceiling.json` or `acquisition_closed.json` states are kept and no block is named. `run_confirmation.plan_run` refuses a bundle without a locked label and unresolved captures, uses `reserve_step.locked_labels` (hash and git checks), and `specs()` feed the existing scorers' formats (`splits.<name>`, `articles[].stratum`).
- **Gate record.** `rf_gate.py`: empty file = no record; complete 1- or 2-field record read; unterminated, 3-field, blank-first-line records impose the full interval; a crash between `pwrite` and `ftruncate` leaves the new record plus an old tail and `_read` takes the new one; every reader holds the exclusive flock, so there is no concurrent unlocked reader. Records written by the previous version (same format) are still accepted.
- **Short-footnote content key.** `rf_sfn_probe.py`: `sfn` = `sf` = `Shortened footnote` = `Sfnnb` (en), `sfnp` = `Sfnb`, ar `Sfn` = `Sf` = `Harvnp` merge; `sfn` vs `sfnp` (en and ar) conflict; `ref=a b` = `ref=a_b` = `ref=a  b` merge, `ref=a` vs `ref=A`, `ref=a` vs `ref=` and `ref=harv` vs none stay apart (the last is a split MediaWiki would merge, the permitted direction); NBSP in a positional value stays apart; a trailing tab merges. The redirect sets are the ones in `calibration/profile_evidence.json`. Collapsing `[ _]+` to `_` matches MediaWiki's title whitespace collapse for a fragment. Positional trim with `%s` (no NUL, with `\v`) agrees with the retained Scribunto/Module:Arguments sources.
- **Time limit.** Driver checks `clock() >= acquisition_end` before every run (exit 5, `acquisition_closed.json`), draw before every request; sim C9 passes; the date matches amendment section 6.
- **Marker regex (RR-9).** `rf_marker.py`: `Template:`, `TEMPLATE:`, `template :` found on both wikis, `Template_talk:` and `msgnw:` not, comments and nowiki still hide. (`{{قالب:Retracted}}` also matches on enwiki; unchanged behaviour.)
- **Stages 00-02.** Untouched (empty diff above). No `.github`, governance or schema change in the delta.
- **Tests.** The two test files named in the brief changed fixtures only; assertions unchanged. No gate, threshold or minimum in `evaluate*.py`, `reserve_decision.py` (`MIN`) or the amendment's numeric rules changed (RF7-3 is the one rule that did).
- **Orphan CLI after a SIGKILL of the driver.** The child is not killed, so a restarted driver can run a second capture beside it. Both go through the network gate (no concurrent requests, the orphan is charged as an interrupted run), but an orphan's later bundle is not adopted. Not reproduced, not reported as a finding.
