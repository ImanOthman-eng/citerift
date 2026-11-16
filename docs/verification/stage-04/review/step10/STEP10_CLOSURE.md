# Stage 04 Step 10: production report assembly, v1 projections and `citerift-investigate` (closure record)

Owner instruction `cmsg_018VCB51nDHP6HXmLU4ea5yPSW7jXkQV4o696BLytWfZux` (2026-11-16T14:42:10Z), baseline
`7ed21488fdfb1d42f06694e8214d718d1bd0db75` (Steps 0 to 9 accepted and closed). Step 11 is not started: no formal
vertical-slice acceptance campaign, no Step 12 freeze, no evaluation, holdout, pre-registration, annotation or scoring,
no Stage 05+ work, no dt-1 change and no change to the frozen Step 4 oracle.

**Status: VERIFIED — AWAITING OWNER ACCEPTANCE.** All 47 exit criteria pass (section 15) at `9643fdc` (CI run 326
green).

Labels: **[verified]** measured or tested here, with the file named; **[inference]** derived, not measured;
**[limit]** a stated limitation; **[owner]** needs an owner decision.

Data. Real inputs are only previously exposed design data (owner decision D-5): the SPEC S-7.4 bundles VS-1 (MMR, en
1381772671), VS-2 (ar Obokata 76190003), VS-3 (en Obokata 1372543632), the retained challenge bundles used at Step 9
for VS-4 (en 1360148888, an expression of concern) and VS-5 (BCAS3, ar 76488293), with the Step 8 and Step 9
attributed Retraction Watch subsets. Inputs changed in memory to reach mapping branches no exposed bundle reaches are
labeled SYNTHETIC in the tests. Nothing here is precision, recall or an evaluation, and none of it is the Step 11
acceptance campaign.

## 1. Build-vs-Adopt (item 2)

`STEP10_BUILD_VS_ADOPT.md`. argparse (standard library) is adopted; Click 8.5.1, Typer 0.29.1 and Cyclopts 5.5.1 are
rejected (no capability the command needs that argparse lacks; Typer adds 12 packages including pydantic and rich;
all permissive licences, pip-audit clean). Jinja2 and Rich are rejected for rendering: fixed `str.format` templates in
one module meet S-12.2 exactly. **No new dependency**: `pyproject.toml` gains only the console-script entry
`citerift-investigate = "citerift.investigation.cli:main"`; `uv lock --check` passes [verified].

## 2. Production ASSEMBLE (items 3 to 10)

`src/citerift/investigation/adapters/assemble.py`. ASSEMBLE reads only committed content through its `StepRequest`:
the committed records, the extraction, the candidate inputs, the lookup plan and lookup observations, the evidence
batches, the bundle manifest and the retained `capture.json`. It never queries Stage 02, re-runs Stage 03, uses the
network, changes a claim, resolves a question or adds evidence. Its output is one `report_recorded` record
`{report, projection_set, projection_count}` and the blobs those name. Any projection that cannot be formed or does not
validate fails the step closed (`REPORT_INVALID`, reason `V1_PROJECTION`).

| Component | What it holds | Order |
|---|---|---|
| `claims` | every current committed claim with its decision, its open question or null, its unit anchor (`unit_id`, byte span, `unit_span_sha256`) and, for `NOT_FOUND_IN_CHECKED_SOURCES`, the checked sources of its deciding lookup | `unit-byte-start/candidate-keys/claim-id/1` |
| `observations` | `{obs_kind, blob}` of every committed observation; no content is copied | `commit/1` |
| `positive_works` | one entry per Stage 02 identity anchor with a positive claim: `{work, classes, claim_ids}` | `work/1` |
| `evidence` | the committed D-053 batches `{batch, count}`; no item is copied | `commit/evidence-batch/1` |

Chunks use the accepted D-053/D-054 byte-bounded boundary rule (`report.chunks`, `batches.boundaries`); the manifest
and chunk schemas are unchanged (`report` 3.0.0, `report-chunk` 1.0.0). **No schema change**: the report's closed list
of seven limitation codes is kept, and the finer statements of item 10 are derived at render time from the stored
graph (section 3), so the durable report stays exactly the D-054 graph.

**Positive works (item 8).** Step 8's ASSEMBLE grouped positive claims by their candidate keys (inherited finding I-1,
section 10). Step 10 groups them by the Stage 02 identity anchor (`result.identity.anchor`, `doi:…` or `pmid:…`) of
each positive claim's deciding lookup (S-6.11): a work cited once by DOI and once by DOI+PMID is one work, and two
anchors are two works even when one record's events name the other's identifier (never merged on one matching
identifier). Only `RETRACTED_WORK_CITED`, `CONCERN_CITED`, `CORRECTION_CITED` and `REINSTATED_WORK_CITED` form works;
every contributing claim id and every distinct class is kept. A positive claim whose deciding lookup has no anchor
fails ASSEMBLE closed. [verified, `test_step10_report.py`: VS-5 two units → one work with two claim ids; VS-3 two
works; SYNTHETIC distinct anchors sharing an identifier → two works; missing or malformed anchor → `ProjectionError`.]

**Summary (item 9, S-7.7).** The manifest's `article_summary` holds the counts by class, the open questions and the
snapshot id (unchanged). The rendered summary statement (`explanations.summary_statement`) adds the scoped sentence
"For the N identified citation(s) listed, no matching record was found in the checked sources (snapshot …)" only when
every in-scope claim is `NOT_FOUND_IN_CHECKED_SOURCES`; it never says "clean", "safe", "not retracted" or "no retracted
citations" [verified, `test_summary_scoped_statement_only_when_everything_is_not_found`].

## 3. Explanations and limitations (items 10, 11, 32)

`src/citerift/investigation/explanations.py`: fixed templates and constants only; no model, no network; equal input
gives byte-identical output [verified, `test_explanations_are_byte_identical_across_runs`, two independent runs].

- `claim_explanation(entry)` returns `{claim_id, class, kind, rule, disposition, text, chain, reasons}`. `text` is the
  class template; `chain` names the rule and table version, the candidate keys, the supporting and contradicting
  counts, the evidence-set digest, the unit id, byte span and `unit_span_sha256`, the reason texts and the open
  question. Every one of the 21 reason codes has a fixed text.
- `kind` keeps the owner's distinctions apart: `finding`, `not_found`, `notice`, `identity_conflict`,
  `source_contradiction`, `unresolved_identity`, `unresolved_identifier`, `unresolved_status`, `unavailable`,
  `out_of_scope`.
- Mandatory wording [verified, `test_mandatory_wording_and_no_forbidden_words`, `test_lookup_unavailable_wording`]:
  not found → "No matching record was found in the checked sources."; notice → "The cited identifier resolves to a
  notice in the checked sources, not to the work it concerns."; unavailable → "The lookup was unavailable for this
  citation; no result is stated for it."; identity conflict → "The identifiers of this citation conflict and require
  resolution." No template, reason text, limitation or lossy text contains "clean", "safe", "not retracted", "no
  retracted citations" or "never retracted" (checked as whole words over every constant and over the real outputs).
- `limitations(manifest, claims)` gives `{code, text}` in a fixed order: `CHECKED_SOURCES_ONLY`, `SNAPSHOT_COVERAGE`,
  `EXTRACTION_PARTIAL`, `LOOKUP_UNAVAILABLE_FOR_SOME_CANDIDATES`, `LOOKUP_EVIDENCE_BUDGET_REFUSED`,
  `IDENTITY_CONFLICTS`, `SOURCE_CONTRADICTIONS`, `UNRESOLVED_IDENTITY`, `UNRESOLVED_IDENTIFIER`, `UNRESOLVED_STATUS`,
  `NOTICE_CITATIONS`, `OPEN_QUESTIONS`, `OUT_OF_SCOPE_UNITS`, `MARKERS_NOT_INTERPRETED`,
  `OBSERVATION_ROLE_IDENTIFIERS_NOT_DECIDED`, `UNSTRUCTURED_TEXT_AS_STAGE03_DEFINES`. Each is present only when the
  stored limitations or the claims component show it (counts, never prose judgement).

## 4. v1 projections (items 12, 13)

`src/citerift/investigation/projections.py`. One record per positive work, valid against the unchanged
`urn:citerift:schema:contracts:v1:investigation` 1.0.1 (`citerift.contracts.validate`; `schemas/contracts` unchanged
[verified, `git diff 7ed2148 -- schemas/contracts` empty]).

**Stored form.** The blob the projection set names is the record without `created_at` (the *body*). `created_at` is
the `at` of `investigation_created` and is added when the record is exported (`projections.v1_record`). Reason: SPEC
11.2 excludes `created_at` from the content digest; with the body stored, `C(J)`, every projection digest and the
projection-set digest are functions of the committed content alone, equal for an interrupted-and-resumed run and an
uninterrupted one (MM P6, VS-9). v1 relates `created_at` to no other field, so a body is valid exactly when the body
with any valid timestamp is; ASSEMBLE and VERIFY check the body with a fixed timestamp and the export checks each
exported record [verified, `test_created_at_never_enters_a_stored_body`,
`test_export_is_a_bounded_directory_derived_from_the_graph`].

| v1 field | Source |
|---|---|
| `schema_version` | `1.0.1` |
| `investigation_id` | the Stage 04 investigation id (S-4.8), the same in every record of one investigation |
| `status` | the report outcome (S-9.7): `completed` or `partial` |
| `subject_paper.identifiers` | the anchor key, plus the other scheme when every event of that anchor names exactly one value for it |
| `subject_paper.retraction_status` | Stage 02's projection assertion of the deciding lookup when identical across the work's claims; with equal status and value but different provenance, that value with the provenance union; otherwise `uncertain`, value null, a reason |
| `subject_paper.retraction_date` | the deciding assertion when identical across the work's claims, else omitted |
| `citations[]` | one per contributing claim, in report claim order: `citation_id` `{wiki}:{revision}:{unit_id}:{cand_ref[:16]}` (no title text), article language, title, page id, revision id and timestamp, the cited keys, and provenance naming the Stage 03 capture (API URL, completion time, `source_version` `revision_id=…;sha1=…`, source artifact SHA-256) |
| `events[]` | the union of the deciding lookups' Stage 02 events (deduplicated by event id and row hash), kind = event type, `at` = the notice day at `T00:00:00Z` when its effective precision is a day, provenance = the Retraction Watch checked source; ordered by time then event id |
| `limitations[]` | the report's limitation statements, then the record's lossy codes, as `CODE: text` |
| `assessments` | `[]` (Stage 06) |
| `synthetic` | `true` only when a checked source of the work says so |

**Lossy mappings** (`projections.LOSSY`, listed in each record that has them):

- `V1_ONE_RECORD_PER_WORK`: v1 holds one paper per record, so the article investigation is split into one record per
  work, each with the same investigation id;
- `V1_CLASSES_PER_WORK`: classes, rules, reasons and evidence chains stay in the Stage 04 report;
- `V1_EVENT_DATE_IS_A_DAY`: v1 events need an instant; `00:00:00Z` marks the day only (also said in each event's
  description);
- `V1_EVENTS_WITHOUT_DAY_OMITTED`: Stage 02 events without a day-precision notice date are not v1 events (they stay
  in the report; VS-5 has two);
- `V1_STATUS_NOT_UNIFORM`: different Stage 02 statuses across the work's claims → `uncertain` with a reason, never
  `conflicting` (different lookups of one work are not sources that disagree), never one chosen status;
- `V1_DATE_NOT_UNIFORM`: different retraction dates → none;
- `V1_SECOND_IDENTIFIER_NOT_UNIQUE`: the events name more than one value of the other scheme → the anchor only.
- The revision sha1, which v1's `article` cannot hold, is in the citation provenance `source_version`.

**Determinism** [verified]: two independent runs give the same report digest, projection-set digest and `C(J)`
(`test_two_independent_runs_give_the_same_digests`); ASSEMBLE with the claim, decision and question records reversed
in memory gives the same payload and blobs (`test_assemble_does_not_depend_on_in_memory_record_order`, VS-1, VS-2,
VS-5); the projection function ignores the order of entries and events (`test_projection_function_ignores_input_order`);
a lowered chunk ceiling changes the report digest but not the projections or the projection set
(`test_claim_chunking_does_not_change_projection_identity`); replay reproduces the report and projection-set digests
(`test_replay_reproduces_offline`).

**Contract tests (item 29)** [verified, `test_step10_report.py`]: retracted (VS-1, VS-2, VS-3), expression of concern
(VS-4, `expression_of_concern`, never retracted), correction (SYNTHETIC), several units for one work (VS-5), several
events for one work (VS-1: two events; SYNTHETIC deduplication across lookups), two distinct works (VS-3), and no
projection for the notice (VS-1), the identity conflict and the not-found claim (VS-2), and `LOOKUP_UNAVAILABLE` (a
1,024-byte lookup budget on VS-3). Every stored body validates, and rebuilding the bodies from the committed content
gives the stored projection set.

## 5. Export (items 14, 15, 25)

`src/citerift/investigation/export.py` and `outputs.py`. The authoritative report is the D-054 graph in
Investigation Memory; the export is derived from it, written only to the directory the user names, and only after the
export gate passes under the same read-only open (one lock): `verify` must give `passed`, which needs ASSEMBLE and
VERIFY committed, a lifecycle of `COMPLETED` or `NEEDS_RESOLUTION`, and every check holding now. `CREATED`, `RUNNING`,
`BLOCKED`, `FAILED`, `STALE` and `CORRUPT` investigations export nothing (`EXPORT_REFUSED` with that state's exit code)
[verified, `test_step10_cli.py` exit 8, 9, 11, 12, 13, 14; `test_step10_corruption.py`].

The export is a directory graph, never one flattened document: `export.json` (format, identities, lifecycle, report
and projection-set digests, `C(J)`, `created_at`, summary, limitations, and every other file with its SHA-256 and
size), `report/<digest>.json` (the manifest and every chunk, as stored), `evidence/`, `observations/`,
`explanations/<claims-chunk>.json`, `v1/<body-digest>.json` and `projection_set.json`. File names are fixed names and
digests only; no raw wikitext or HTML is exported.

Path safety [verified, `test_step10_d052.py`]: a target inside the memory root, including through a symbolic link
outside it, is refused (`OUTPUT_PATH_UNSAFE`); an existing target is never replaced unless `--overwrite` is given for a
checkpoint file (never for an export directory, never through a symbolic link, never over a directory); writes go to a
new temporary entry (`O_CREAT|O_EXCL|O_NOFOLLOW`), are `fsync`ed, moved into place in one step (`link` without
overwrite, `replace` with it, `rename` for a directory) and the directory is `fsync`ed; a failure at write, `fsync` or
rename leaves no target and no temporary entry, and a failed overwrite keeps the old file.

## 6. Command line (items 16 to 23)

`citerift-investigate` (`src/citerift/investigation/cli.py`, argparse; operations in `operations.py`). Every command
takes `--format text` (default) or `--format json`.

```
citerift-investigate run (--request FILE | --bundle DIR | --wiki {ar,en} --revision N)
                         [--index FILE --memory-root DIR] [--lookup-budget BYTES]
citerift-investigate resume     --memory-root DIR --key KEY
citerift-investigate replay     --memory-root DIR --key KEY
citerift-investigate verify     --memory-root DIR --key KEY [--checkpoint FILE]
citerift-investigate show       --memory-root DIR --key KEY [--claims]
citerift-investigate export     --memory-root DIR --key KEY --out DIR
citerift-investigate checkpoint --memory-root DIR --key KEY [--out FILE [--overwrite]]
```

JSON output has one shape: `{command, status, exit_code, result}` on success, `{command, status, exit_code,
error: {code, detail}}` otherwise; diagnostics go to standard error. Text output is for people and is never a
scientific identity. Files are written only by `export` and `checkpoint`.

**Exit codes** (one table for every subcommand, `operations.EXIT`). Existing conventions were inspected first
(`src/citerift/wiki/cli.py`, `src/citerift/retraction/cli.py`): 0, 1, 2, 3 and 5 mean the same in both tools
(success, internal, usage, invalid input, verification failed) and keep that meaning; 6, 8 and 9 keep their
`citerift-wiki` meaning (partial, deferred, failed); 4 is "unavailable" in both and is used for the closest case here,
no investigation under that key; 7 is left unused because the two tools give it different meanings (unsupported,
enrichment); 10 to 14 are investigation states neither tool has. When a command succeeds its exit code is the
investigation's status; no exit code carries a claim class.

| Code | Status | Meaning |
|---|---|---|
| 0 | completed | COMPLETED with outcome completed, and the command did what was asked |
| 1 | internal | an unexpected error (a defect); nothing is exported |
| 2 | usage | the command line is wrong |
| 3 | invalid | the request, a configuration, a checkpoint or an output path is invalid or unsafe |
| 4 | not_found | no investigation with that key under the memory root |
| 5 | verify_failed | a verification check failed, a replay differs, or a checkpoint does not match |
| 6 | partial | COMPLETED with outcome partial |
| 8 | blocked | BLOCKED: a step may restart only at or after `not_before`; nothing sleeps |
| 9 | failed | FAILED: a step failed terminally |
| 10 | needs_resolution | NEEDS_RESOLUTION: verified, with an open question |
| 11 | stale | STALE, or an input identity differs from the recorded one |
| 12 | corrupt | CORRUPT: the journal, a blob or the report graph is invalid |
| 13 | busy | another process holds the investigation lock |
| 14 | incomplete | CREATED or RUNNING (for example after a crash, before `resume`) |

Every code is produced by a real command in `test_step10_cli.py` (`test_exit_0_completed` …
`test_exit_14_incomplete`), and the table in the command's help text is checked against `EXIT`.

**Results on the design bundles** [verified, `test_step10_cli.py`]:

- `run`: VS-3 → 0 (COMPLETED, completed, 2 works); VS-1 → 6 (partial: the Stage 03 extraction is partial); VS-2 → 10 (NEEDS_RESOLUTION, the identity conflict's question open). The same request twice addresses
  the same investigation and appends nothing; the same bundle at another path is the same key with another payload and
  is refused (`INVESTIGATION_REQUEST_DIFFERS`, exit 3, nothing changed); another lookup budget is another key.
- `resume`: runs a CREATED investigation to its end offline; a BLOCKED investigation before `not_before` is reported
  (exit 8) without sleeping, without calling the adapter and without appending. Interrupted attempts are closed by the
  accepted controller (W-6, Step 7 crash tests unchanged).
- `replay`: `reproduced` on VS-1 and VS-2 with the committed report and projection-set digests and the VS-2 identity
  conflict; `stale` (exit 11) after the index file changed; `differs` with the first differing component on forged
  reports (section 8); refused (`NOT_REPLAYABLE`) for a FAILED investigation.
- `verify`: `passed` with 19 named checks (20 with a checkpoint) (MEMORY_OPEN, WORKFLOW_INVARIANTS, COMMITTED_VERIFICATION, the 15 VERIFY
  checks re-run read-only including D054_REPORT_GRAPH and the new V1_PROJECTIONS, INPUT_IDENTITIES_CURRENT, and
  D052_CHECKPOINT when one is given); `failed` (5) when any integrity check fails; `stale` (11); `corrupt` (12) and
  `busy` (13) reported as results. Opening the journal alone is never success.
- `show`: read-only; key, id, lifecycle, report outcome, each step's state, attempts and `not_before`, the terminating
  record, open questions, claim counts by class (from the committed claims, also before a report exists), the next
  legal transition with its rule (e.g. `wait ACQUIRE (rule T-RESTART)`, `terminal (rule W-5)`); `--claims` adds the
  template explanations. No blob content and no captured page text is printed.
- Read-only commands (`show`, `verify`, `replay`, `checkpoint` to standard output) leave every byte under the
  investigation unchanged [verified, `test_read_only_commands_write_nothing`].

**Offline (item 26)** [verified]: every socket call (`connect`, `connect_ex`, `create_connection`, `getaddrinfo`) is
refused and counted while retained-bundle `run` and `resume`, `replay`, `verify`, `show`, `export` and `checkpoint`
run; the count is zero in every test. Only live ACQUIRE (a supervised Stage 03 child process) may use the network.

## 7. D-052 external journal checkpoint (item 24)

`src/citerift/investigation/checkpoint.py`, design `review/step7/closure/STEP7_D052_CHECKPOINT_DESIGN.md`. A checkpoint
is one canonical JSON object with exactly `format` (`citerift-investigation-checkpoint`), `format_version` (`1`),
`investigation_key`, `seq` (the last journal record it covers) and `journal_digest` (that record's digest, which
commits to the whole prefix through `prev`). It holds no time, path, host, user or content. `checkpoint` writes it to
standard output (the statement goes to standard error) or to a file outside the memory root; `verify --checkpoint
FILE` compares it with the opened journal and answers exactly one of `CHECKPOINT_MATCH`, `CHECKPOINT_TRUNCATED`,
`CHECKPOINT_PREFIX_REWRITTEN`, `CHECKPOINT_KEY_MISMATCH`; a malformed file is `CHECKPOINT_INVALID` (exit 3).

The only statement made, word for word: **"A checkpoint retained outside Investigation Memory can detect rewriting or
truncation of the journal prefix it covers."** It is not a signature, authentication, non-repudiation or tamper-proof
storage, and none of those words appears in the module [verified, `test_no_security_wording_anywhere_in_the_checkpoint_code`].
[limit] An adversary who can replace both the journal and the checkpoint is outside this guarantee; a checkpoint
stored inside the investigation directory is refused as an output and would not be an external anchor.

Tests [verified, `test_step10_d052.py`, 18 tests]: exact match; an earlier checkpoint still matches after the journal
grew; truncation with a recomputed chain (the journal still opens as RUNNING, `verify` without the checkpoint cannot
see it) → TRUNCATED; rewrite of an earlier record with every later digest recomputed (the journal opens, plain `verify`
passes) → PREFIX_REWRITTEN; wrong investigation → KEY_MISMATCH; seq beyond the journal, seq of another record, digest of
another record, digest naming nothing; 17 malformed variants (empty, not JSON, not canonical, wrong field set, wrong
format or version, negative, text, boolean or float seq, upper-case or short hex, too large, two newlines) and an
unreadable file → CHECKPOINT_INVALID, journal unchanged.

## 8. Corruption and security (items 7, 27, 28)

`test_step10_corruption.py` (45 tests) damages copies of a verified VS-3 investigation as an adversary with write
access to the memory root could. Every case ends in `corrupt` (12) or `failed` (5), never `passed`; `export` writes
nothing (`EXPORT_REFUSED`); `replay` never says `reproduced` [verified].

- **Blob damage → corrupt (12)**, each missing and changed: claims chunk, positive-works chunk, observations chunk,
  report manifest, projection set, projection body, evidence batch (14 cases).
- **Forged report graphs with a recomputed hash chain → corrupt (12)** (Memory refuses them on open, D-054): claims
  reordered, claim missing, claims chunk listed twice, wrong chunk digest, claim changed, decision changed, wrong
  chunk count, wrong total count, summary counts not the claims, evidence batch missing, wrong batch count,
  observations reordered, positive claim in no work, work listed twice, work with a wrong class, another investigation
  key, another investigation id, another root (18); a summary the schema refuses (partial outcome without its cause, a
  snapshot id of another form); a projection count that is not the set's.
- **Forged reports that open, with the verified content digest re-sealed to `C(J)` → failed (5)**: works merged or a
  work identity replaced (a wrong positive-work list that the graph check alone accepts), limitations dropped, another
  snapshot id, another configuration in the identities → `ASSEMBLE_REPLAY` fails; a projection missing from the set,
  replaced by another valid body, invalid against v1, or holding `created_at` → `V1_PROJECTIONS` fails.
- Controls: the undamaged copy verifies, exports and replays; re-sealing an unchanged report still verifies.
- Item 27 failures [verified, `test_step10_cli.py`]: invalid requests (nine forms) and a missing or unreadable bundle
  → 3 with nothing created; a bundle whose artifact or revision id changed → ACQUIRE FAILED (9); a missing or foreign
  index → FAILED (9); lookup overflow (1,024-byte budget) → `LOOKUP_UNAVAILABLE`, no projection; Retry-After deferral →
  BLOCKED (8); busy lock → 13 for every command; a changed journal line → 12 for every command, and `run` neither
  repairs nor rewrites it; changed index → 11; checkpoint mismatch → 5; export path failures → 3. No failure case has a
  positive claim, a not-found claim or an export.

**Verify classification change (this step).** While testing the forged reports, `verify` treated a failed
`COMMITTED_VERIFICATION` as "state, not integrity" even for a verified lifecycle, and `replay` reported `stale` with no
changed identity when a recorded step key did not derive from the committed inputs. Both are fixed in
`operations.py`: for a verified lifecycle every failed check is `verify_failed`, except `INPUT_IDENTITIES_CURRENT`
when an identity really changed (stale); a step key that differs while no identity changed is `STEP_KEY_MISMATCH`
(verify: failed; replay: `differs` at `step_keys`).

## 9. Carry-forward constraints (item 31)

D-058, D-059 and D-060 hold: no dt-1, table, detector, D-051 identity or B-8 guard code is changed [verified, `git diff
7ed2148 -- src/citerift/investigation/dt1.py src/citerift/investigation/adapters/detector.py
src/citerift/investigation/ids.py` empty], and the Step 9 tests (`test_step9_real.py`, `test_step9_b8.py`,
`test_step9_detector.py`) pass unchanged in the full suite. The Step 4 oracle is unchanged [verified, `git diff
7ed2148 -- simulations/` empty; `test_the_step4_oracle_manifest_is_unchanged` passes].

## 10. Inherited-baseline audit (item 33)

| Id | Finding | Classification | Action |
|---|---|---|---|
| I-1 | Step 8 ASSEMBLE keyed positive works by the citation's candidate keys: one work cited by DOI and by DOI+PMID became two works (SPEC 11.1, 11.2 say one per Stage 02 work) | Stage 04 defect in the pre-production ASSEMBLE (identity collapse in reverse: one work split) | Fixed in scope: works keyed by the Stage 02 anchor (section 2) |
| I-2 | `workflow.outcome()` ignores a partial extraction, and its docstring says the extraction status is read "from Step 8 on" | Stage 04 inconsistency in the accepted controller (Step 7), visible on VS-1: `workflow.outcome` gives `completed`, the report (ASSEMBLE, S-9.7) `partial` [verified] | Not changed (accepted controller, no Step 10 need); the CLI reads the outcome from the report. Recorded for Step 12 |
| I-3 | Journals assembled before Step 10 replay as `differs` at ASSEMBLE although the engine identity is unchanged | Same property as the Step 9 carry-forward A-6 (engine version not bumped) | Not changed; carried to Step 12 with A-6 |
| I-4 | The projection-set schema describes its digests as "v1 investigation records" while the stored blobs are records without `created_at` | Stage 04 documentation inconsistency | Schema not changed (no validation impact); SPEC 11.2 now states the stored form. [owner] whether to reword the description at Step 12 |
| I-5 | `run`, `resume` and `show` of a terminal investigation report the recorded state without checking current input identities; staleness of a terminal investigation is shown by `verify` and `replay` (exit 11) | Accepted controller behaviour (S-9.4: a terminal investigation is not run again) | Documented here and in the CLI help; not changed |
| I-6 | Stage 03 `verify_bundle` accepts an attempt-log request URL whose revision parameter differs from the source (same host); the source URL, hosts and artifacts are checked (a forged source URL or foreign host fails ACQUIRE) | Stage 03 observation; the revision content itself is verified | Not changed (no silent Stage 00–03 edit); no claim or projection depends on the attempt log |

No contract mismatch with v1 was found (every body validates); no timestamp instability (`created_at` is excluded from
every digest); no unsafe path behaviour in Memory (its rules are unchanged); no report text found that strengthens a
claim.

## 11. Originality and differentiation review (item 34)

Evaluated as practical properties of this implementation; no novelty is claimed and none was searched for in primary
literature in this step.

- The report is a content-addressed manifest graph that Memory re-proves on every open, and an export is only a
  derived, verified copy of it.
- Every explanation is a fixed template over the rule, reasons and evidence chain, so the same evidence gives the same
  text and a reader can trace each sentence to an evidence-set digest and a byte span.
- Findings, not-found-in-checked-sources, notices, unresolved identities, contradictions and unavailable lookups stay
  separate kinds through the report, the CLI and the summary; nothing absent is turned into a negative.
- The v1 projection is explicitly a compatibility view: one record per Stage 02 work, with its lossy points written
  into the record.
- Replay re-derives the report and projections from retained inputs offline and names the first differing component.
- An external checkpoint can be kept outside Investigation Memory, with one exact, limited statement of what it shows.

## 12. Runtime (item 35)

- **Step 10 tests alone** (4 modules, 144 tests): **2 min 27 s** locally (Python 3.12, 4 vCPU). Slowest: the report
  module's five real investigations (fixture setup 10.2 s), `test_read_only_commands_write_nothing` 4.2 s, the MMR
  fixture 4.1 s, `test_replay_reproduces_offline` 4.0 s. The 45 corruption cases each run `verify`, `export` and
  `replay` on a copy (about 1 s each).
- **Full suite locally**, clean tree at `9643fdc`, 3.12 and 3.13 run at the same time: **3,180 passed, 0 skipped**
  on each; 14 min 28 s and 14 min 15 s (Step 9: 3,035 tests, 11 min 54 s and 11 min 28 s). The slowest tests are
  all pre-existing (`test_d047_report_with_50000_projections` 34.4 s, the Stage 00 differential simulations 26 s).
- **GitHub CI run 326 at `9643fdc`: green.** 3.12: test step 11 min 51 s, job 12 min 13 s; 3.13: test step 10 min
  46 s, job 11 min 18 s. **Slowest job 12 min 13 s, under the 18-min boundary** (Step 9: 12 min 11 s). [inference]
  CI runners vary by minutes between jobs; Step 10 adds about 2.5 minutes of test time on a local machine, and the CI
  jobs did not grow by that much in this one run, so the margin should be judged over further runs. No `.github/`
  change and no timeout change.
- CI run 325 at `74d93e7` failed in static analysis on one unused test variable (ruff RUF059), before any test ran;
  fixed in `9643fdc` (test file only).

## 13. Files

New: `src/citerift/investigation/{checkpoint,cli,explanations,export,operations,outputs,projections}.py`;
`tests/stage04/{step10_support,test_step10_cli,test_step10_d052,test_step10_corruption,test_step10_report}.py`;
`docs/verification/stage-04/review/step10/{STEP10_BUILD_VS_ADOPT,STEP10_CLOSURE}.md`. Changed:
`adapters/assemble.py` (production ASSEMBLE), `adapters/verify.py` (V1_PROJECTIONS, projection set in the ASSEMBLE
replay), `pyproject.toml` (console script), `SPECIFICATION.md` (narrow Step 10 notes in 11.2 and 13),
`tests/stage04/test_step8_integration.py` (15 VERIFY checks). Not changed: `.github/`, `src/citerift/governance`,
`schemas/` (governance, investigation, contracts), Stages 00–03 code, dt-1, the Step 4 oracle.

## 14. Verification and CI

At `9643fdc`, clean tree [verified]: `pytest` 3,180 passed, 0 skipped on 3.12 and on 3.13, `check-report` 0
problems for both; `ruff check .` passed; `ruff format --check .` 535 files formatted; `mypy` no issues in 95 source
files; `citerift-gov check` 0 errors, 0 warnings; `render-status --check` up to date; `check-schemas` 0 problems;
the Step 3 checker PASS (0 failed); `pip-audit --strict --disable-pip --require-hashes` over the CI export (all
groups): no known vulnerabilities; `uv lock --check` passed. GitHub CI run 326: green (`ci-gate` success).

## 15. Exit criteria (item 37)

| # | Criterion | Result |
|---|---|---|
| 1 | production ASSEMBLE exists | PASS. `adapters/assemble.py` (section 2). |
| 2 | report manifest graph produced from the committed fold | PASS. D-054 graph; Memory re-proves it on append and open. |
| 3 | report ordering deterministic | PASS. `claim_key`, `work_key`, commit order; reversed in-memory orders give the same output. |
| 4 | report chunking deterministic | PASS. Accepted D-053/D-054 boundary rule, unchanged. |
| 5 | evidence batches reused, not duplicated | PASS. `evidence` lists committed batches; no item copied. |
| 6 | positive works correct and deduplicated | PASS. Stage 02 anchor grouping (I-1 fixed); VS-3, VS-5 and SYNTHETIC tests. |
| 7 | article summary obeys S-7.7 | PASS. Counts, open questions, snapshot; scoped not-found sentence only. |
| 8 | limitations deterministic | PASS. Fixed codes and templates over stored codes and claim counts. |
| 9 | fixed explanation templates exist | PASS. `explanations.py`. |
| 10 | explanations do not strengthen meaning | PASS. Mandatory sentences and forbidden-word tests. |
| 11 | v1 projections validate against contracts 1.0.1 | PASS. Every body and exported record validates; schemas/contracts unchanged. |
| 12 | one projection per distinct positive work | PASS. Set count = positive works; V1_PROJECTIONS check. |
| 13 | non-positive classes create no projection | PASS. Notice, conflict, not found, unavailable tested. |
| 14 | projection-set identity deterministic | PASS. Independent runs, reordering, chunking, replay. |
| 15 | report graph corruption fails closed | PASS. 45 cases (section 8). |
| 16 | export only after VERIFY success | PASS. Gate under one lock; refused for every other state. |
| 17 | run works | PASS. Section 6. |
| 18 | resume works | PASS. CREATED to COMPLETED offline; BLOCKED reported without waiting. |
| 19 | replay works read-only | PASS. Reproduced, differs, stale; files unchanged. |
| 20 | verify works | PASS. 19 named checks (20 with a checkpoint). |
| 21 | show works read-only | PASS. Files unchanged; next transition with its rule. |
| 22 | human-readable output works | PASS. Text and JSON carry the same status. |
| 23 | machine-readable JSON works | PASS. One documented shape, checked in every CLI test. |
| 24 | exit-code mapping explicit and tested | PASS. Every code produced by a real command. |
| 25 | busy/blocked/stale/corrupt distinguishable | PASS. 13, 8, 11, 12. |
| 26 | D-052 checkpoint export works | PASS. Standard output or a file outside the memory root. |
| 27 | checkpoint verification detects prefix rewrite/truncation | PASS. With recomputed chains (section 7). |
| 28 | checkpoint limitations documented | PASS. Exact statement; no security wording; both-replaced limit stated. |
| 29 | path/export safety passes | PASS. Section 5. |
| 30 | offline commands make zero network attempts | PASS. Socket refusal counters are zero. |
| 31 | deterministic replay reproduces digests | PASS. Report and projection-set digests. |
| 32 | D-058/D-059/D-060 intact | PASS. Section 9; Step 9 tests pass unchanged. |
| 33 | inherited-baseline audit retained | PASS. Section 10 (I-1 to I-6). |
| 34 | originality review retained | PASS. Section 11. |
| 35 | no Step 11 acceptance work begun | PASS. No campaign, no evaluation; only design bundles in tests. |
| 36 | full tests pass on 3.12 and 3.13 | PASS. 3,180 each. |
| 37 | zero required skips | PASS. 0 skipped; check-report 0 problems. |
| 38 | ruff passes | PASS. |
| 39 | format check passes | PASS. |
| 40 | mypy passes | PASS. |
| 41 | pip-audit --strict clean | PASS. |
| 42 | schema checks pass | PASS. |
| 43 | Step 3 checker passes | PASS. |
| 44 | frozen Step 4 oracle unchanged | PASS. `git diff 7ed2148 -- simulations/` empty; manifest test passes. |
| 45 | citerift-gov check 0/0 | PASS. |
| 46 | render-status --check passes | PASS. |
| 47 | GitHub CI green within the runtime boundary | PASS. Run 326; slowest job 12 min 13 s. |

## 16. Owner decisions

None is required to accept Step 10. Open for later steps, not blocking: [owner] I-2 (`workflow.outcome` and the
extraction status) and I-4 (projection-set schema description) at Step 12; I-3 with A-6 (engine version) at Step 12.
