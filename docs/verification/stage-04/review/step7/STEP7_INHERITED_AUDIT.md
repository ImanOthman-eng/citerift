# Stage 04 Step 7: inherited baseline audit (owner Step 7 items 18 and 19)

Building the controller showed some things about Stages 00–03 and about Stage 04's own accepted Steps 3–6. This
document records them.

Classes:

1. Stage 04 integration/hardening improvement
2. accepted-stage maintenance defect
3. scientific defect
4. governance/contract defect
5. documentation/evidence defect
6. accepted residual limitation

No file of Stages 00–03 was changed in Step 7.

## Findings

| ID | What was checked | Finding | Class | Owner | Disposition |
|---|---|---|---|---|---|
| IA-1 | Resource-bound mismatch: Stage 03 caps against the Step 6 record limit | Stage 03 counts all identifier occurrences against `max_candidates` = 50,000 (`wiki/source.py`, `Scanner._add`). It has no per-unit cap. A claim's evidence list and the report's projection list can therefore reach about 3.35 MB, over the 1 MiB record limit. Upstream is correct. The Stage 04 limit rejects an upstream-bounded investigation. | 1 (Stage 04 defect, not upstream) | Stage 04 | Owner decision RB-1 (`STEP7_RESOURCE_BOUNDS.md`). Fail-closed today (`STORAGE_ERROR` / `RECORD_TOO_LARGE`, tested). |
| IA-2 | Resource-bound mismatch: Stage 02 events per key | Only `ROW_LIMIT` (2,000,000) bounds the events one key can match. No Stage 02 constant bounds the lookup blob, the journal or the claim's lookup evidence below that. | 6 | Stage 04 (cap at LOOKUP) | Owner decision RB-2. Stage 02 unchanged. |
| IA-3 | Failure-code mismatch: Stage 03 network codes | All nine codes in `workflow.NETWORK_CODES` exist in `wiki/fetch.py` and `wiki/issues.py`. All three Stage 02 `INDEX_*` codes exist in `retraction/store.py` and `retraction/query.py`. | none | n/a | Checked by script (grep of the code strings). No mismatch. |
| IA-4 | Accepted contract ambiguity: EXTRACT failure classification | Stage 03 returns an extraction *document* with `status: failed` for every failure. That includes the three worker codes (`failure_document(..., "EXTRACTION_DEADLINE_EXCEEDED", ...)` in `wiki/extract.py`) as well as `LIMIT_*`, `SOURCE_PARSE_LOSSY`, `BUNDLE_DIGEST_MISMATCH` and `PLATFORM_UNSUPPORTED`. SPEC 9.3 lists the three worker codes as retryable and `EXTRACTION_FAILED` as "document `failed`". Both descriptions fit a failed document carrying a worker code. Reading taken: a failed document whose `worker.code` is one of the three is that retryable code; any other failed document is `EXTRACTION_FAILED` with the Stage 03 code as `reason`. | 4 (Stage 04 SPEC, Step 3) | Stage 04 | The Step 8 EXTRACT adapter must implement this rule with a test. Owner confirmation recommended. The controller already accepts both shapes. |
| IA-5 | Retry/timeout semantics: Stage 03 `not_before` | Stage 03 computes `not_before` on a monotonic clock (`Plan.not_before_mono`) and reports it as a string (`FetchResult.not_before`). It returns `not_before` both on `DEFERRED_RETRY_AFTER` and on `ATTEMPTS_EXHAUSTED` when a Retry-After was seen. The controller accepts only an aware UTC instant. It honours `not_before` on a deferral and on a retryable network failure (`test_future_not_before_makes_the_run_wait_without_sleeping`, which uses `HTTP_RATE_LIMITED`). `ATTEMPTS_EXHAUSTED` is in the same retryable set (`workflow.NETWORK_CODES`) and takes the same path. | 1 | Stage 04 (Step 8) | The Step 8 ACQUIRE adapter must convert the string to a UTC instant, never shortening it. No upstream change. |
| IA-6 | Provenance / identifier gap: SPEC 4.3 `evidence_id = H(obs, pointer)` | The id leaves out the evidence kind, so two kinds of evidence at one pointer of one observation get the same id. Memory refuses the second one as `DUPLICATE_ID`. This fails closed, never silently. | 4 (Stage 04 SPEC, Step 3) | Stage 04 | Residual: the Step 8/9 NORMALIZE must give each derived kind its own pointer, or the owner must decide to add the kind to the hash (this changes accepted ids). Recorded as an owner decision point. |
| IA-7 | Stale documentation: the record schema's `decision_recorded` description | The description says "it is checked against the claim by Investigation Memory". Memory never checked it (`grep disposition src/citerift/investigation/memory.py fold.py` finds nothing). | 5 (Stage 04 Step 5 schema text) and 1 | Stage 04 | The controller now enforces it: `workflow.detect_problem` is applied by the guard and by `check_journal`. Test: `test_guard_refuses_detect_content_that_breaks_w8[wrong-disposition]`. The schema text is not edited in Step 7, because a schema edit changes schema digests that the accepted steps cite. It is listed for the Step 12 review. |
| IA-8 | Encoding parity: Stage 03 vs Stage 04 canonical JSON | `wiki.canonical.canonical_bytes` and `investigation.canonical.canon` use the same `json.dumps` arguments. Memory blobs accept floats (`put_blob(..., allow_float=True)`). That matters because the Stage 03 extraction document carries a float, `config.worker_wall_s`. Journal records refuse floats. | 6 | Stage 04 (Step 8) | No defect. The Step 8 adapter must keep the Stage 03 config in the blob, never in a journal record. |
| IA-9 | Stale metadata | The `citerift.investigation` package docstring said the Workflow Controller was a later step. | 5 | Stage 04 | Fixed in Step 7. |
| IA-10 | Unsafe fail-open | With a full journal, Memory's raw `AppendRefused` escaped the controller when the record closing an attempt was itself refused. Nothing false was written. | 1 | Stage 04 | Fixed in Step 7: `StorageExhausted`, attempt left open, resume by W-6. Tests: `test_journal_limit_*`. |
| IA-11 | Failure-code gap: steps with no schema-legal defect code | VALIDATE, EXTRACT and LOOKUP have no `step_failed` code for "the adapter misbehaved". In those steps the controller raises `AdapterDefect` and leaves the attempt open. Recovery closes it (W-6), and after `A_max` the step ends with `RETRY_BUDGET_EXHAUSTED`. | 4 (Stage 04 Step 5 schema) | Stage 04 | Owner decision: add `ADAPTER_INCONSISTENT` to those steps' code lists, or keep the crash semantics. Tested in `test_controller_adversarial.py`. |
| IA-12 | Governance consistency | `citerift-gov check` reports 0 errors and 0 warnings (exit criteria run). Nothing in `src/citerift/governance`, `schemas/governance` or `.github/` was changed. | none | n/a | n/a |

Not observed:

- **Scientific defects (class 3).** The controller runs over fake adapters, so it cannot exercise Stage 02 or
  Stage 03 science. That check belongs to Step 8 and later.
- **Accepted-stage maintenance defects (class 2).** None found.

Nothing above needs an upstream (Stage 00–03) correction, so no governance authorization is pending for upstream.

## Tamper-evidence (R6-12)

R6-12 is kept as a limitation. The journal's hash chain is unkeyed. Anyone who can write the investigation folder can
rewrite or truncate a suffix and recompute every digest, and the fold will not notice. Nothing in Step 7 changes that.

Candidate anchors already in the architecture, reviewed against "small, offline, keyless, reproducible, no false
security claim":

| Candidate | Assessment |
|---|---|
| Chain head `(seq, digest)` from the fold (`Folder.last_digest`) | Already computed, keyless and reproducible. It becomes an anchor only once it is stored somewhere the journal's writer cannot also rewrite, for example printed in the Stage 04 report or kept by the user. A verifier with a kept head detects any rewrite or truncation of the prefix up to that head. It detects nothing after the head, and nothing if the attacker also controls where the head is kept. |
| Git commit signing of the repository | Signs repository commits, not investigation folders, which live under a memory root outside the repository. Committing journals would need a new workflow. Not suitable. |
| Governance registry (`citerift-gov`) | Records stage and commit evidence. S-15.1 forbids importing it from `citerift.investigation`. Not suitable. |
| Stage 03 `capture_sha256`, Stage 02 index identity | Anchor the *inputs*, not the journal. Already in the step keys. |

**Conclusion.** One small existing primitive can materially improve detection: the fold's chain head, exported as a
checkpoint the user keeps outside the investigation folder. It needs no key, no network and no new dependency. Its
guarantee is limited to "the prefix up to the kept head is unchanged".

**Owner decision TA-1, not implemented.** The options:

- (a) Keep R6-12 as is.
- (b) Have the Stage 04 report and the controller's explanation print `(seq, digest)` of the head, and add a verifier
  that checks a journal against a supplied head.

Step 7 does not implement (b), because it would add a report field (report assembly is a later step) and a user-facing claim. That claim must
be worded so that it promises no more than prefix integrity relative to a head the user kept.
