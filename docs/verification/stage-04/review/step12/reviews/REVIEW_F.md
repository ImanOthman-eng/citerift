# Stage 04 pre-freeze review — Reviewer F (CLI, report and user-facing semantics)

Repository `/home/user/citerift` at HEAD `65c30bd`. This review was read-only: `git status --short` was empty before and after. Scratch work is in `/tmp/claude-0/-home-user/6e897802-8925-5c74-9e54-d0b75d7ee684/scratchpad/review-F/`.

## 1. Scope and method

**Code read:** `cli.py`, `operations.py`, `outputs.py`, `explanations.py`, `projections.py`, `export.py`, `checkpoint.py`, `workflow.py` (`next_action`, `outcome`, `derive`, `explain`), `controller.py` (`run`, `RunResult`) and `adapters/assemble.py`.

**Contracts and records read:**
- `schemas/investigation/v1/{projection-set,report}.schema.json` and `schemas/contracts/v1/investigation.schema.json`.
- SPEC sections 7, 9 to 13.
- `STEP10_CLOSURE.md` and `STEP11_CLOSURE.md`.
- The Step 10 and Step 11 tests.

**Real CLI runs** (installed `.venv/bin/citerift-investigate`, offline, no evaluation or holdout bundle):
- **Fixture index:** built from the attributed Step 8 subset with the `step8_support.build_index` helper.
- **Retained bundles:** VS-3 `en-1372543632` (exit 0), VS-1 MMR (exit 6), VS-2 `ar-76190003` (exit 10).
- **FAILED:** a missing index (exit 9).
- **CREATED and RUNNING:** made with a small helper that calls `step8_support.run_until`.
- **STALE:** index bytes appended after LOOKUP committed.
- **CORRUPT:** one byte flipped in a copy.
- **BUSY:** `flock` held on the lock file.
- **Live-capture path:** `cli.main` with the SYNTHETIC child `tests/stage04/live_fake_child.py` and `CITERIFT_WIKI_NETWORK_LOCK` set to a scratch file.
  - Mode `throttled:600` gives the Stage 03 deferral: BLOCKED.
  - Mode `retry_after:600` with a 1,500 ms bound gives the D-042 kill after Retry-After (A11-5): RUNNING and `wait`.

**Read-only checks:** before and after `show`, `verify`, `replay`, `checkpoint` and `export`, I hashed the whole memory directory (content, file list, mtimes).

**Tests run:** only `tests/stage04/test_step10_cli.py -k "exit_8 or exit_14"` (2 passed, `-p no:cacheprovider`, basetemp in scratch).

**Not touched:** the confirmation-campaign challenge bundles under `docs/verification/stage-03/evaluation/…` (VS-4, VS-5) were not run. For VS-4 I read only the retained Stage 04 evidence file. The concern case was reproduced instead as an in-memory SYNTHETIC variant of VS-2.

## 2. Findings

| Id | Title | Severity | Evidence | Proposed classification | Suggested fix |
|---|---|---|---|---|---|
| UF-01 | A false `V1_DATE_NOT_UNIFORM` statement appears in every non-retraction v1 record (concern, correction, reinstatement) and in any single-claim work without a date | MEDIUM | `projections.py:215-219`, LOSSY text `projections.py:66-67`; Stage 02 gives a date only for `retracted` (`retraction/schemas.py:162-164`, `DATE_WITHOUT_RETRACTION`); retained real record `docs/verification/stage-04/evidence/vertical-slice/results/VS-4/v1/11de48b6….json` (one citation, `expression_of_concern`, text "the contributing claims of this work have different Stage 02 retraction dates"); reproduced with an in-memory SYNTHETIC concern variant of VS-2 (`concern_date.py`) | 1 | `distinct = {canon(d) for d in dates}`. One value that is not null: carry it. All null: omit the date, with no lossy code. Otherwise emit `V1_DATE_NOT_UNIFORM`. Fix `test_synthetic_correction_record` (`test_step10_report.py:378-387`), which keeps a retraction date on a correction, a shape Stage 02 refuses |
| UF-02 | A11-5: a RUNNING investigation that must wait gets exit 14 `incomplete`; `resume` does nothing and returns 14 again | MEDIUM | Reproduced: `run` gives `incomplete (exit 14)` with `next: wait ACQUIRE (rule T-RESTART)`; `resume` gives 14 and the journal is unchanged. Definitions contradicted: `operations.py:80` (8 = "a step may restart only at or after not_before"), `:86` (14 = "not terminal and not blocked"), docstring `:12-13` ("leaves the investigation BLOCKED"). Same issue the other way: lifecycle BLOCKED after `not_before` stays exit 8 with `next: start` (shown with a +1 h clock, `later.py`) | 1 (contract wording 4) | Section 4 |
| UF-03 | For a non-terminal investigation whose input identity changed, `show` predicts the wrong next transition | MEDIUM | RUNNING after LOOKUP, then index changed: `show` gives `incomplete (exit 14)`, `next: start DETECT (rule T-START)`. `resume` then records `stale_detected` (exit 11, terminal, irreversible). SPEC 10.1 (lines 927, 948) lists `show` among the opens that recompute step keys; S-9.2 requires the next *legal* transition. `operations.show` (`:323-375`) never calls `stale_identities`. Not the known I-5 (that covers terminal investigations) | 1 | `show` computes `stale_identities(mem, Integration())` read-only, as `verify` does. When it is not None, report `next = {action: "stale", rule: "T-STALE", changed: […]}` and status `stale` (11). At minimum, report a `stale` field so the operator can restore the input before `resume` makes the investigation STALE |
| UF-04 | `verify` says `result: failed` and `export` says "verification failed" for an investigation that is only not yet verified | LOW | `operations.py:520-521`, `:652`. Reproduced on CREATED, RUNNING, BLOCKED and FAILED: text shows `result: failed` with `FAIL COMMITTED_VERIFICATION`, and export shows `EXPORT_REFUSED: verification failed: nothing exported`. The exit code (14, 8 or 9) differs from 5, but the word matches a real verification failure. Pinned by `test_exit_14_incomplete` (`test_step10_cli.py:330`) | 4 | Use result `not_verified` for a lifecycle outside COMPLETED and NEEDS_RESOLUTION. Export detail: `lifecycle <L> is not verified; nothing exported`. Exit codes unchanged |
| UF-05 | The JSON contract "one stable shape" is broken in three places | LOW | (a) argparse usage errors and internal errors (exit 2 and 1) print nothing on stdout with `--format json` (`cli.py:200-204`, `:216-218`); reproduced, while `run --wiki en` usage errors do print JSON. (b) `checkpoint` without `--out` ignores `--format json` and prints the raw checkpoint (`cli.py:220-223`); reproduced. (c) `verify` returns busy and corrupt inside `result` (`operations.py:457-460`), while `show`, `replay`, `checkpoint` and `resume` return them inside `error`; reproduced. The contract is stated at `cli.py:42-44` and `STEP10_CLOSURE.md` §6 | 4 | Emit the error envelope for exit 1 and 2 when `--format json` was requested (parse `--format` early). Document (b) and (c) as exceptions in `cli.py`, or wrap the checkpoint in the envelope when `--format json` is given |
| UF-06 | Text output leaves out diagnostics a user needs | LOW | `cli._text` prints a fixed key list (`cli.py:167`). `replay` stale shows only `result: stale` and not the changed identity, which S-10.3 (SPEC line 996) requires ("which one is named"); reproduced. `verify` corrupt or busy prints no code or detail, and nothing on stderr; reproduced. `run`/`resume` `detail` is never printed | 1 | Add `changed`, `code`, `detail` and `stale.changed` to the printed keys |
| UF-07 | One JSON result gives the same `not_before` in two timestamp formats | LOW | `steps[].not_before` is `…Z` (`operations._iso`, `:389-390`); `next.not_before` is `…+00:00` (`workflow.explain`, `workflow.py:526`). Reproduced on BLOCKED and A11-5 | 4 | Format `next.not_before` with `_iso` in `show` |
| UF-08 | Article-level status and limitations are copied into every v1 record without saying they are article-level | LOW | The VS-2 v1 record for nature12968 (a clean D-14 finding) holds `status: partial`, "IDENTITY_CONFLICTS: 1 citation(s) have identifiers that conflict…" and "OPEN_QUESTIONS: 1 …". All of these concern another citation (un-00013). Source: `projections.py:244-249` | 4 | Add a lossy code such as `V1_ARTICLE_LEVEL_STATEMENTS`: "status and the limitations before the V1_ codes describe the whole article-revision investigation, not only this work." Wording only; the v1 contract is unchanged |
| UF-09 | v1 events drop `matched_by` and `linked_via`, so a bridged Stage 02 event looks like a direct event of the paper | LOW | `projections._core` and `_event` (`:112-127`, `:262-264`); LOSSY has no code for this. Stage 02 matched lookups can include `doi_cooccurrence`, `pmid_cooccurrence` and `query_pair` events (`retraction/query.py:317-357`). [inference] No design bundle exercised a bridged event inside a positive claim | 4 (or 5 with a code) | Put "matched by X via Y" into the event description, or add lossy code `V1_EVENT_LINKS_NOT_STATED` |
| UF-10 | `--help` shows no exit codes and no JSON contract, and the I-5 limitation is not documented where the Step 10 record says it is | LOW | `citerift-investigate --help` output has no exit-code table; the table exists only in `cli.__doc__` (the test at `test_step10_cli.py:64-66` checks the docstring, not the help). `STEP10_CLOSURE.md:320` (I-5) says "Documented … in the CLI help"; `cli.py` has no such statement. `cli.py:34` (11 = "or an input identity differs") is false for `run`, `resume` and `show` on a terminal investigation: reproduced, exit 0 after the index changed | 4 | Pass the table as the parser `epilog` (RawDescriptionHelpFormatter). Add the I-5 sentence. Qualify the row 11 text to "(verify, replay, export)" |
| UF-11 | `write_tree` checks the export target and then renames, and the rename can replace an empty directory created in between; an environment failure (ENOSPC, EIO) gets exit 3 `invalid` | LOW | `outputs.py:128-130`, `:136-137`. POSIX `rename` replaces an empty directory (confirmed in scratch). "never over an existing path" (`outputs.py:4-5`) is therefore not strictly true | 2 | Use `renameat2(RENAME_NOREPLACE)` where available (ctypes), or document the window. Map `OUTPUT_WRITE_FAILED` from ENOSPC/EIO to a distinct status, or document that 3 covers it |
| UF-12 | I-2: `workflow.outcome()` gives `completed` for a partial extraction | LOW | `workflow.py:488-495` (its docstring wrongly says the status is "read from the extraction from Step 8 on"). It reaches `WorkflowState.outcome` → `explain()["outcome"]` → `RunResult.explanation` (`controller.py:730`). **No user-visible path uses it**: `operations.show` reads only `lifecycle`, `next` and `terminated_by` from `explain` (`operations.py:328, 343-346`); `_drive` ignores `RunResult.explanation`; every other operation reads `manifest["outcome"]`. Consumers are tests and the evidence column `workflow_outcome` (`run_vertical_slice.py:159`) | 1 (internal) | Section 3 |
| UF-13 | Cosmetic CLI text | INFO | `next: terminal  (rule W-5)` has a double space (`cli.py:179`). `INVESTIGATION_REQUEST_DIFFERS: INVESTIGATION_REQUEST_DIFFERS: …` repeats the code (`operations.py:417` uses `str(exc)`) | 4 | Join the non-empty parts; use `exc.detail` |

**UF-01.** Stage 02 never states a retraction date unless the value is `retracted`. So every CONCERN, CORRECTION or REINSTATED work, including VS-4, the only real concern case, carries "the contributing claims of this work have different Stage 02 retraction dates". The sentence is false (one claim, no date). Inside an expression-of-concern record it also suggests retraction dates exist. This is the wording risk of scope item 5 (a concern worded near a retraction). It sits in the stored body, so the fix changes the projection digests of such works. That is acceptable before freeze.

**UF-02.** See section 4.

**UF-03.** `resume` checks staleness before anything else (`controller.py:313-315`). `show` does not. The next transition `show` prints is therefore not the one `resume` performs, and that transition is irreversible: STALE is terminal.

**UF-04.** For investigations that have not reached VERIFY, the same word `failed` covers three different situations: "not verified yet", lifecycle FAILED, and "integrity check failed" (exit 5). A user reading text output cannot tell them apart without the exit code.

**UF-05 to UF-07.** These are contract and consistency defects of the "stable shape" promise. None changes a scientific result.

**UF-08 and UF-09.** These are v1 lossiness points a v1-only consumer could misread. See also section 6 for the points that are already documented.

**UF-10.** The only place the exit-code contract is visible to a user is the Python module docstring.

**UF-11.** A narrow race window. Minor.

**UF-12.** The known I-2, confirmed internal-only.

## 3. I-2 analysis and proposed single helper

**Every place the outcome is derived or decided:**
1. `adapters/assemble.py:141`: `"partial" if open_q or unavailable or doc["status"] == "partial" else "completed"`. This is complete S-9.7. It is the authoritative value: it goes into the report manifest and the v1 `status` (`build_bodies(outcome=…)`, `projections.py:249`).
2. `workflow.outcome(f)`, `workflow.py:488-495`. It checks open questions and LOOKUP_UNAVAILABLE but not the extraction status. The fold cannot see that status: an `observation_recorded` payload holds only `blob`, `obs_kind` and `source_ref` (checked on the VS-1 journal). It feeds `derive`, then `explain`, then `RunResult.explanation`.
3. The report schema encodes S-9.7 as an equivalence (allOf if/then on `outcome`, `report.schema.json`). It is declarative, and Memory checks it on open.
4. `operations.status_of(lifecycle, outcome)`, `operations.py:105-109`. It consumes the outcome (from `manifest["outcome"]` in `show`, `verify`, `replay`, `export` and `checkpoint`). It maps COMPLETED with outcome `None` to `"partial"` silently. That case is unreachable under W-7, but it is not fail-closed.

**User-visible use of `workflow.outcome()`: none.** Evidence: grep for `workflow.outcome` and `.explanation` in `src/` (it is used only in `workflow.py` itself and in `controller.py:730`). `operations._drive` uses only `result.status` and `result.detail`. Test consumers: `test_controller_differential.py:404`, `test_step8_integration.py:102,292`, `test_controller_resolution_stale.py:70,125`. Evidence consumer: `run_vertical_slice.py:159`.

**Proposed helper**, pure and in one place (`report.py`, which ASSEMBLE and projections already import):

```python
def outcome(extraction_status: str, claim_classes: Iterable[str], open_questions: int) -> str:
    """SPEC S-9.7, the only derivation of the report outcome."""
    if extraction_status not in ("complete", "partial"):
        raise ValueError(f"no outcome for extraction status {extraction_status!r}")
    partial = extraction_status == "partial" or open_questions > 0 or "LOOKUP_UNAVAILABLE" in set(claim_classes)
    return "partial" if partial else "completed"
```

**Call sites:**
- `assemble.py:141` becomes `report.outcome(doc["status"], (c["class"] for c in claims), len(questions))`. VERIFY's `ASSEMBLE_REPLAY` covers it automatically.
- `workflow.outcome`, `WorkflowState.outcome` and `explain()["outcome"]`: remove them. A fold-only function cannot be correct, and nothing user-visible reads them. If an outcome is wanted in `explain`, have the caller pass it from the committed report manifest instead.
- Tests and the evidence script then read `report_of(mem)[1]["outcome"]`. The frozen Step 4 oracle under `simulations/` is not touched; only the comparison at `test_controller_differential.py:404-406` changes (or asserts `report.outcome("complete", classes, len(open_questions))`).
- `operations.status_of`: COMPLETED with `outcome is None` raises (fail closed) instead of returning `"partial"`.

## 4. A11-5 recommendation

**Facts** (reproduced through the CLI):
- **Stage 03 deferral:** lifecycle BLOCKED, `next.action = wait`, exit 8.
- **D-042 kill after Retry-After:** lifecycle RUNNING, `next.action = wait`, exit 14; `resume` returns 14 and writes nothing.
- **After `not_before`** (+1 h clock): BLOCKED still gives exit 8 with `next: start`; RUNNING gives 14 with `next: start`.

So in neither case does the exit code say whether `resume` can make progress now.

From `controller.run` (`controller.py:316-320`) [inference]: `run` and `resume` return CREATED or RUNNING only when the next action is `wait`. From those two commands, 14 therefore *always* means "must wait". The help text's example ("after a crash, before resume") never applies to them.

**Accepted contract (Step 10, `STEP10_CLOSURE.md` §6):** 8 = "BLOCKED: a step may restart only at or after `not_before`; nothing sleeps"; 14 = "CREATED or RUNNING". The code's own comment adds "not terminal and not blocked" (`operations.py:86`). The A11-5 state matches the text that defines 8 and contradicts the comment that defines 14.

**Recommendation: option (b), in its minimal form.** The user-facing status is `blocked` (exit 8) whenever lifecycle is CREATED or RUNNING and `next_action(f, now).action == "wait"`. JSON keeps `lifecycle: "RUNNING"`, `next.action: "wait"` and `next.not_before`. Lifecycle BLOCKED stays 8 as accepted.

Implementation: `status_of(lifecycle, outcome, next_action)`, called by `show`, `verify`, `replay`, `export` and `checkpoint` with `workflow.next_action(f, now)`. Fix the docstring at `operations.py:12-13` and the 8 and 14 rows in `cli.py` and `operations.EXIT`.

**Reasons:**
1. **Safety for automation.** A wrapper that loops "resume while exit is 14" spins without sleeping until `not_before`. Each iteration takes the writable lock and rewrites the lock file, so concurrent `show` or `verify` calls can get exit 13. With (b), exit 8 always means "wait until `next.not_before` (it may already be past), then resume", and 14 always means "resume can act now".
2. **Correct inference by a person.** Today, 14 plus the help text invites a `resume` that cannot make progress (UF-02).
3. **Minimal change to the accepted table.** No code changes meaning except the one state that already fits the 8 definition. No lifecycle, journal, controller rule or exit-8 behaviour for BLOCKED changes.

**Ambiguity (b) creates:**
- Exit 8 no longer means lifecycle BLOCKED; consumers must read `lifecycle` in JSON or text.
- The status of an unchanged journal depends on the clock: 8 before `not_before`, 14 after. That is already true of `next`.

**Ambiguity (a) keeps:** every consumer must parse `next.action` to know whether to wait, so the exit code alone is not actionable for the two forms of "wait".

**Owner decision needed:** (b) changes accepted Step 10 output for one state, so it requires an owner decision. The help table text would become: "8 blocked: no step may start before `not_before` (lifecycle BLOCKED, or RUNNING after a retryable failure that recorded a `not_before`); nothing waits or sleeps."

## 5. I-4 proposed wording

**Current** `projections.description` (`schemas/investigation/v1/projection-set.schema.json`): "Digests of the v1 investigation records (schemas/contracts/v1, unchanged), one per work with a positive claim."

This is inaccurate. The digests name the stored bodies, which have no `created_at` (each blob file's SHA-256 equals its name). The exported `v1/<digest>.json` files have other SHA-256 values: checked on the VS-3 export.

**Proposed** (description only; the v1 contract and the validation are unchanged):

> "SHA-256 digests of the stored v1 projection bodies, one per distinct work (Stage 02 identity anchor) with a positive claim. A body is a v1 investigation record (schemas/contracts/v1, unchanged) without created_at; each digest is the SHA-256 of the canonical encoding of the body blob it names. created_at (the at of investigation_created) is added only when a record is exported (SPEC 11.2), so an exported record does not hash to its digest; the export names each record file by this body digest."

**Top-level description:** change "The v1 projections of one report" to "The stored v1 projection bodies of one report".

## 6. Checked, no finding

**Read-only guarantees.**
- `show`, `verify`, `replay`, `checkpoint` (stdout and `--out`) and `export` left every byte, file and mtime under the investigation unchanged, on COMPLETED (VS-2) and on BLOCKED (live).
- `resume` on BLOCKED before `not_before` appends nothing; only the informational lock content changes, as SPEC 10.1 allows.

**Exit-code matrix** (all as documented, apart from UF-02, UF-03, UF-04 and I-5):

| State | Exit code across commands |
|---|---|
| CREATED | 14 (`verify` result `failed`, UF-04) |
| RUNNING | 14 |
| BLOCKED | 8 |
| COMPLETED | 0, or 6 when the outcome is partial |
| NEEDS_RESOLUTION | 10 |
| FAILED | 9 |
| STALE | 11 |
| CORRUPT | 12 |
| BUSY | 13 |
| not found | 4 |
| bad memory root | 3 |
| changed identity on a terminal investigation | `verify`, `replay`, `export`: 11; `run`, `resume`, `show`: 0 (I-5, documented in the Step 10 record) |

`replay` and `export` on a lifecycle that is not verified give the lifecycle code with `NOT_REPLAYABLE` or `EXPORT_REFUSED`. Success codes (0, 6, 10) never overlap with refusal codes (3, 5, 11, 12, 13) for `export`.

**Outcome in user-visible outputs.** VS-1 (partial extraction) is `partial` in `run`, `show`, `verify`, `export.json` and v1. VS-2 is NEEDS_RESOLUTION, exit 10, outcome `partial`.

**Wording** (scope item 5):
- No template, limitation, summary or lossy text holds "clean", "safe", "not retracted", "no retracted citations" or "never retracted".
- NOT_FOUND text is exactly "No matching record was found in the checked sources." plus the named checked sources. The summary's not-found sentence appears only when every in-scope claim is NOT_FOUND, and it is scoped to the listed citations and the snapshot.
- Concern and correction texts name their own event ("an expression of concern", "a correction"); none says retraction (apart from UF-01).
- Identity conflict and source contradiction texts say "no finding is stated" (D-6 always has a DOI and a PMID, so "The DOI and the PMID" is accurate).
- The "unavailable" text states no result.
- D-13's text pairs "the lookup query failed" with the budget refusal; that reason set is defined by the SPEC (D-13 row), so it is not a Stage 04 wording defect.

**v1 lossy points that are documented in the record and in SPEC 11.2 / STEP10 §4:**
- events without day precision (counted);
- the day-as-instant convention;
- a status or date that differs across claims;
- a second identifier that is not unique;
- one record per work;
- classes, reasons and chains not in v1;
- the revision sha1 carried in provenance `source_version`;
- `created_at` = `investigation_created.at`, added at export and excluded from digests;
- citation identifiers = the cited keys.

Also documented as deliberate (category 5): no v1 record for not-found, conflict, unavailable or notice claims, and no v1 records at all for an article without positive works. `export.json` carries the summary and limitations.

**Export and checkpoint.**
- Path safety checked in code.
- `write_file` uses `link` (atomic, never replaces).
- Export file names are fixed names and digests.
- The D-052 statement is word for word.

**`verify` with a changed `stage04` identity.** Failures of the `STAGE04_REDERIVED` checks are classed `stale` (`operations.py:510-511`). This could hide a forged projection behind exit 11 instead of 5, but the export is refused either way.

**Project gate commands.** Full `pytest`, `ruff`, `mypy` and `citerift-gov check` were not run: the brief prohibited the full suite and no repository file was changed. Every finding above rests on the cited code line or command output.

VERIFIED COMPLETE (read-only review)
