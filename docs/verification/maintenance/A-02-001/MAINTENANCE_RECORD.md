# A-02-001: Stage 02 maintenance transaction (bounded lookup before materialization)

Owner authorization: owner decision D-048 (RB-2) in the Stage 04 thread, 2026-11-11T07:04:33Z
(`cmsg_018VCB51nDHP6HXmLU4ea5yP4dn3r7aj9NgLkPeaJaD5L3`): "Add the smallest backward-compatible Stage 02 facility"
and route it through the accepted-stage governance mechanism. That message is the authorization; this file records
what was done under it. Mechanism: the maintenance transaction of D-024 (model in
`docs/verification/maintenance/A-00-002/MAINTENANCE_MODEL.md`), unchanged; precedent A-03-001. Stage 02 is not
reopened and its acceptance (`cf060834afedfa4a82712ca247ad2fc2b2fa9665`) is not rewritten. Decision record:
DECISIONS.md D-048.

Can the mechanism represent this enhancement? Yes [verified against `src/citerift/governance/maintenance.py` and
`orchestrator.py`]: it records an exact owned-file patch against the accepted revision with the owner's reference,
refuses any other owned change while pending, and finalizes only on complete passing reports on 3.12 and 3.13 of a
clean revision whose owned content equals the candidate. Nothing in the patch touches `schemas/retraction` or a
contract schema.

## 1. Defect / need [verified]

| Item | Fact |
|---|---|
| Accepted API | `Index.gather(doi, pmid, supersessions=())` reads every event row, Crossref row and relevance hit of a key into Python before returning |
| Bound | only `source.ROW_LIMIT` (2,000,000 rows) bounds the events of one key |
| Effect | a Stage 04 cap applied after `gather()` bounds nothing: the memory and time are already spent (owner: "A cap applied only after calling the current Index.gather() is rejected") |
| Evidence | `docs/verification/stage-04/review/step7/closure/fail_first_before.log`: 200 and 2,000 events of one key all materialized (traced peaks 1.06 MB, 10.4 MB) before a cap of 100 could apply |

## 2. Patch (candidate `b052a72b1de05c1130556a8b43e016f37b6d980f`)

Two owned files, additions only:

- `src/citerift/retraction/query.py`:
  - `EvidenceBudgetExceeded(QueryError)` (code `EVIDENCE_BUDGET_EXCEEDED`, with `budget` and `needed`);
  - the row-size helpers `_stored_bytes`, `_listed_bytes`, `_EVENT_BYTES`, `_CR_BYTES`, `_ATTEMPT_BYTES`;
  - the per-call `_Budget(limit, used)`;
  - `Index._budget = None` and `Index.gather_bounded(doi, pmid, *, budget_bytes, supersessions=())`;
  - five guards `if self._budget is not None:` that charge a row's stored size (SQL `length` of its stored fields)
    or a relevance hit's canonical size **before** the row is read or the hit is kept.
  `gather()` itself is not edited. With no budget set (every call except through `gather_bounded`) each guard is
  skipped and the code path is the accepted one.
- `tests/stage02/test_rde_gather_bounded.py` (new).

File SHA-256 at the candidate: `query.py` `08154e78b1de97dc6557859c90ce2946e3109cf60f9e43157eaa3cbd4002250e`; test
`d30a077482372459a63183714473704c6882391848daa2f51bbe0bd6b8a0b255`.

## 3. Proof that `gather()` is unchanged and the facility is correct [verified]

| Test | What it shows |
|---|---|
| `test_module_without_the_maintenance_is_the_accepted_module` | removing exactly the added names and the five guards from the candidate's AST unparses to the accepted module's AST (SHA-256 pinned per Python minor: 3.12 `5e1f67b9…852d`, 3.13 `003045b8…b7dd`) |
| `test_no_budget_is_set_outside_gather_bounded` | `_budget` is None before, after, and after a refusal |
| `test_bounded_lookup_within_budget_equals_gather_on_every_case` | identical results to `gather()` on every Stage 02 policy and tension case |
| `test_below_at_and_one_over_the_bound` | N−1 refused; N and N+1 equal `gather()` (pmid None and "123456") |
| `test_one_event_more_than_the_budget_allows_is_refused_whole` | k events fit, k+1 refused; nothing partial |
| `test_over_the_budget_nothing_beyond_it_is_materialized` | at 2,000 events the stored bytes of rows made stay within the budget at fractions 0, 0.25, 0.5, 0.75, 0.999 |
| `test_budget_must_be_a_non_negative_int`, `test_invalid_query_needs_no_budget`, `test_relevance_hits_are_charged_before_they_are_kept` | input validation, query validation first, relevance hits charged |

## 4. Fail-first [verified]

`fail_first.sh` → `fail_first.log`: the new test module against the accepted revision `cf06083` (query.py SHA-256
`0b1b74ed…d9e3`) does not collect: `EvidenceBudgetExceeded` does not exist. The behavioural fail-first is in
section 1.

## 5. Transaction record

| Step | Record |
|---|---|
| Baseline | `cf060834afedfa4a82712ca247ad2fc2b2fa9665` (Stage 02 accepted revision; unchanged). Stage 02 owned content at `ab0ce66` equals it (`git diff cf06083 ab0ce66 -- <owned paths>` is empty) |
| P (candidate) | `b052a72b1de05c1130556a8b43e016f37b6d980f`: the two owned files only |
| prepare | `citerift-gov maintenance prepare 02 --candidate b052a72… --path src/citerift/retraction/query.py --path tests/stage02/test_rde_gather_bounded.py --owner-ref cmsg_018VCB51nDHP6HXmLU4ea5yP4dn3r7aj9NgLkPeaJaD5L3 --purpose … --reason … --evidence docs/verification/maintenance/A-02-001/MAINTENANCE_RECORD.md` gave A-02-001, `pending_validation`, recorded 2026-11-11T08:25:58Z, `opened_after_seq` 50, patch digest `db8f3c2e…4a67a`; check: 0 errors, 1 warning (`MAINTENANCE_PENDING`) |
| Stage 04 work | `906308ea9aa4b8fcd09a7735dc1a793d6b83011e` (Stage 04 Step 7 closure, which uses `gather_bounded`); no Stage 02 owned file |
| V (validated) | the commit that adds the pending registry record and this file; owned content identical to P |
