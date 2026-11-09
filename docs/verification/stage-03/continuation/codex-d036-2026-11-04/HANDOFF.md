# D-036 safe continuation checkpoint — 2026-11-04

CITERIFT — Created and Directed by EVE TELOS · IM

Executor: OpenAI Codex. This is a recovery supplement, not scientific verification,
owner acceptance, an amendment, or a new campaign. Authority: the owner's current
“CITERIFT — Precision Recovery and Controlled Continuation of Stage 03” instruction.
The historical Claude Opus attribution in the manifest remains historical; Codex
has not resumed a Claude context. No unauthorized model substitution occurred.

**SCIENTIFIC_CONTINUATION_BLOCKED_BY_REQUIRED_EVALUATOR.** Stage 03 remains
`IMPLEMENTED_NOT_VERIFIED`. Stages 00–02 and Stage 04 are untouched. G6b and G6c
have no D-036 result; an unavailable evaluator is not a failed scientific gate.

## Git checkpoint and preservation

- Remote Claude head and inspected source revision:
  `80000f292b1991ab14c0dfa5edc8e78d2e3ed06a`.
- Main: `94ac4f8df27383a03a810a4501ed1439bf8bcaea`.
- Continuation branch: `codex/stage03-d036-safe-continuation`, created from the
  actual remote Claude head; no existing continuation ref was returned.
- The checkpoint commit is the commit adding this directory; resolve its exact
  SHA with `git log -1 --format=%H -- docs/verification/stage-03/continuation/codex-d036-2026-11-04`. Publication SHA and
  read-back verification are reported in the executor's final response.
- PR #5 was open at the inspected Claude head. Source-head CI runs
  [41843525440](https://github.com/ImanOthman-eng/citerift/actions/runs/41843525440)
  and [41843511939](https://github.com/ImanOthman-eng/citerift/actions/runs/41843511939)
  were completed/success (`source-ci.json`). This is not final scientific CI. The existing workflow only auto-runs on
  main/claude pushes or PRs; continuation-head CI requires workflow_dispatch,
  without changing the protected workflow.
- No merge, PR creation/update, force push, shared-history rewrite, sampling,
  capture, annotation, label lock, prediction, scoring or adjudication occurred.
- Only this supplement is added. Existing evidence and accepted foundations are
  byte-identical to the source revision. `SHA256SUMS` pins the supplement;
  `integrity.json` separately inventories the committed pre-existing D-036 directory.

The working checkout was freshly cloned. It cannot reveal the original Claude
executor's uncommitted files. A missing file here is not evidence that it was
never produced there. Recheck both remote refs and the original workspace before
resuming, and preserve any later work without resetting either branch.

## Verified completed work

The frozen candidate is `8901a597015b7c6d6eb8464554e79b4fa1383615`.
Its `src` tree is `cda4a4b6a754fc9fa4cd00839c78192c34e56f79` and `schemas`
tree is `360501fccd024a9e4e74cb2e09f5b3d34e125892`. Both equal HEAD. All
29 manifest-pinned file/amendment digests match. No frozen code was changed. The manifest
booleans for exposure/draw/capture describe its prospective freeze-time state;
they are not current-progress flags and were not rewritten.

R-038 correction, independent A/B reviews, dispositions and focused re-review
are already committed under `design/r038-reconciliation/`. They were inspected;
the correction campaign was not repeated. Existing full-suite regression tests
are used for current engineering verification; see ENGINEERING.md for exact
commands, revisions, interpreter versions and retained results. The old Stage 03 root handoff
and test narrative chiefly describe D-035; they must not be mistaken for a
D-036 verdict or a current unfixed R-038 finding.

The ordered commits, fully resolved in `chronology.json`, prove: candidate →
prospective freeze → exposure set → draw → 40 captures → initial packets →
40-label lock → reserve decision 1 → four reserve captures → reserve packets.
The stored exposure exclusions and hash-salted eligible order also validate
without regenerating either artifact. The original reserve decision reproduces exactly from its historical committed
capture state and existing locked labels, without a new draw or decision.
The campaign journal has 70 matched start/end runs, 208 HTTP attempts and
7,394,021 accepted bytes (ceilings 500 / 314,572,800). No acquisition was added.

`integrity.json` verifies all 238 content-addressed artifacts, all 44 accepted
capture source/render pairs and revision pins, and all 44 evaluator packet
source/render hashes. Existing labels pass the unchanged format/quote/window
validator. The reserve brief equals the frozen template after the approved
substitutions, with its original omitted terminal newline preserved.
No D-036 prediction/extraction/score files were found.

Existing immutable locks:

| Batch | Labels | SHA-256 of ANNOTATION_LOCK.json |
|---|---:|---|
| initial-ar | 24 | `da123b3c53a26b4230779ea62ee0b4efddefeb305e1cfb5ac3774c13d98b973c` |
| initial-en | 16 | `4388190f7152a0fe030ae3db7b6b2e3184b05c8cc21c5e3882bbadb2f7faabc6` |

Paths relative to `evaluation/confirmation-d036/campaign/annotations/locked/`.
Individual label digests and lock records remain in those directories.

| Language | Target identifiers | Uses | Definitions | Linkable uses |
|---|---:|---:|---:|---:|
| ar | 56 | 187 | 147 | 187 |
| en | 49 | 226 | 103 | 226 |
| Required per language | 50 | 80 | 60 | 60 |

Arabic initial minimums are met; English needs its already-selected reserve1.
These are locked annotation counts, not engine scores.

## Exact next unfinished operation

**First inspect the original evaluator host** for an already-running or completed
`d036-eval-en-r1-1` context, raw transcript, `out/` and any new commits. Its
historical work path is in the committed `annotations/briefs/en-r1-1.txt`:
`/tmp/claude-0/-home-user-citerift/a52d5c86-81c2-5300-a98c-c54b1eaf0da5/scratchpad/eval-d036/en-r1-1`.
That path is unavailable here. Do not relaunch or duplicate completed work.
If there is partial work, preserve it and resume only its original valid context
under the same brief; do not invent its history.

If no reserve evaluator was launched, use **one genuine fresh Claude Sonnet
instance**, with no more than these four articles, in an isolated directory
outside the repository. Approved raw input root:
`docs/verification/stage-03/evaluation/confirmation-d036/campaign/annotations/packets-reserve1/en-r1-1/packets/`.
Assignment is `packets-reserve1/ASSIGNMENT.json`; the brief is
`annotations/briefs/en-r1-1.txt`. Guide 1.1 and the original brief are pinned in
`MANIFEST.json`; do not change their contents or expose the engine, review,
prior failures, locked labels, this handoff or predictions to the evaluator.
Rebind only the approved WORK placeholder if the original path is unavailable,
and retain the exact dispatched brief and its digest. Keep the raw transcript,
model identity, times, file access and isolation audit.

| Page ID | Article | Pinned revision | Accepted bundle suffix |
|---|---|---|---|
| 76434050 | Dick Sandberg | 1376175856 | `reserve1/en-76434050-a2` |
| 32105383 | Gender and development | 1370070834 | `reserve1/en-32105383-a1` |
| 1582736 | Caliciviridae | 1377341430 | `reserve1/en-1582736-a1` |
| 11579232 | Mycobacterium pinnipedii | 1377158630 | `reserve1/en-11579232-a1` |

Note: the packet assignment lists packet names in revision order, which differs
from bundle order. Match by revision/hash, never by zipping the two lists.
The accepted Sandberg capture is **a2**, not the deferred a1. Both historical
attempts stay unchanged. Full packet and bundle hashes are in `integrity.json`.

This session exposes no Claude Sonnet/Haiku evaluator tool or Claude CLI, and its
runtime reports no configured secrets or provider identities. No paid API was
added. Codex/GPT agents cannot supply the required provenance. A substitution
would be a prospective methodological change needing separate owner authority;
it has not been made. Access to the approved independent contexts, not an
engineering change or threshold adjustment, is required.

## Resume commands and order (on the evaluator-capable host)

Start with `uv sync --locked`, `uv run citerift-gov recover`, and
`uv run citerift-gov check`. Verify remote changes and the original evaluator
workspace before any annotation launch. Use existing scripts as authoritative:

```sh
# From repository root, after legitimate Sonnet output exists:
uv run python docs/verification/stage-03/evaluation/confirmation-2026-11/campaign/annotations/validate_labels.py \
  <isolated-work>/packets <isolated-work>/out
```

After format-only validation, preserve byte-identical original outputs and
transcripts, audit isolation with the existing `audit_evaluators.py` procedure,
and copy the valid labels into a new reserve1 lock directory. Run the existing
`protocol/scripts/evaluate.py lock <lock-directory>`; record candidate,
amendment `10db8cb9df178792c8fe797a800af1bd63af29c5`, guide hash and actual
provenance as in the initial LOCK_RECORDs. Never edit evaluator labels to improve
scores. Apply the existing D-036 secret gate before staging any campaign file;
commit and publish the new lock before extraction.

```sh
# Only AFTER the valid reserve1 lock is committed:
uv run python docs/verification/stage-03/evaluation/confirmation-d036/scripts/reserve_step.py \
  docs/verification/stage-03/evaluation/confirmation-d036/campaign/selection/SELECTION.json \
  docs/verification/stage-03/evaluation/confirmation-d036/campaign/capture \
  docs/verification/stage-03/evaluation/confirmation-d036/campaign/annotations/locked/initial-ar \
  docs/verification/stage-03/evaluation/confirmation-d036/campaign/annotations/locked/initial-en \
  <committed-reserve1-lock-directory>
```

Only locked counts can authorize a further ordered reserve block. Keep the
original ceiling and acquisition deadline **2026-11-14 23:59 UTC**. Do not
capture anything already accepted, redraw, replace articles or start a campaign.

Only after all required locks and denominators are final: verify the candidate
source/schema trees and clean bytes again, then use the unchanged
`confirmation-d036/scripts/run_confirmation.py` **once**, through the installed
frozen engine. Read its usage before invocation; no prediction command was run
or preflighted here. Next use the unchanged disagreements procedure and genuine
independent **Claude Haiku** contexts with `ADJUDICATION_BRIEF_v1.1.md`; retain
locked and adjudicated scores, bootstrap/Clopper-Pearson intervals, audit and
all verify/replay outputs. No repair or retuning after predictions.

## Scientific gates and release completeness

| Gates | D-036 checkpoint disposition |
|---|---|
| G1 identifiers | Not scored; pending valid labels and the one prediction |
| G2 key correctness | Not scored |
| G3 roles/promotions | Not scored |
| G4 uses/binding | Not scored |
| G5 definitions/units | Not scored; G5c/G5d ≥ 0.95 unchanged |
| G6 render | Not scored; G6a ≥ 0.98, G6b ≤ max(1, 1% of engine links), G6c ≥ 0.85 unchanged |
| G7 markers | Not scored; marker correctness and zero fabricated negatives remain mandatory |
| G8 integrity | Raw hashes/revisions checked; campaign extraction verification awaits the one run |
| G9 acquisition | Current 44/44 accepted captures complete; final sample and costs await reserve completion |
| G10 replay | Historical wheel cases pass; D-036 replay awaits the one run |
| G11 synthetic exact outcomes | Existing engineering tests exercise these; no scientific acceptance inferred |

D-036 final campaign report, adjudicated scores, confidence intervals, final
scientific audit, complete final export and governance verification must remain
unfinished. Earlier failed campaigns remain their original results. This
checkpoint does not waive any gate. Final-head full engineering and CI are still
required at the eventual scientific delivery revision.

## Missing evidence and provenance limits

- Original Claude evaluator directories and seven raw initial evaluator
  transcripts are not present here. The committed transcript map, audit/final
  reports, helper snippets, 40 validated labels and locks exist. Their hashes
  are verified; their underlying transcript claims cannot be independently
  re-audited without the private originals.
- Review A/B/R external worktrees, reviewer raw scripts/outputs and original
  private evidence exports are not available. Committed review reports,
  dispositions, fail-first evidence, differential and simulation records exist.
  No external export preservation or checksum verification is claimed.
- Whether reserve1 has any original local-only outputs is unknown.
- Five D-035 withheld working-copy files are absent, but all five are exactly
  recoverable from existing historical blobs and their SHA-256/size checks pass.
  They are not missing scientific bytes. No withheld file was restored to the
  public tree, replaced, edited or accessed over the network.

## Security and nondestructive delivery

`security.json` independently checks the five-file manifest and the three
restricted historical blobs. They are ancestors of HEAD and therefore also of
this continuation branch, and absent from main's reachable history. No current
tracked file matches the AWS key-id shape. The D-036 campaign passes the broader
existing secret-gate patterns, including percent-decoded readings.

The existing `security/PRESIGNED_URL_REVIEW.md` classifies the historical value
as a third-party key identifier plus an expired S3 SigV2 request signature
(expired 2024-03-25), not a secret access key. No URL was followed. Object
existence, public accessibility and key status remain unknown and were not tested.
A current clean tree does not remove its historical blobs. Neither PR #5 nor
this continuation branch is a clean-history delivery branch.

Nondestructive strategy, **not executed**: preserve original refs and private
checksum-verified evidence; after actual scientific completion, construct a new
branch whose sole base ancestry is accepted main and whose sanitized source
content matches the final reviewed tree. Do not merge or cherry-pick contaminated
ancestry. Audit every reachable blob. Reconcile governance ancestry requirements
through approved new provenance/verification records, retaining original
scientific SHAs as external evidence; an identical tree alone does not make the
old candidate an ancestor. Validate the delivery branch itself and obtain owner
choice of merge path. Do not fabricate ancestry, use replace refs, weaken the
checker, rewrite public history or create a competing PR now. Owner-side
remediation may be needed for public historical copies and existing personal
Git attribution; no public history has been altered.

## Do not repeat

Do not repeat the initial 40 annotations, R-038 correction/review campaign,
exposure collection, deterministic draw, accepted captures, reserve decision 1,
or reserve packet generation. Do not mutate frozen evidence, change models,
thresholds or sampling order, treat unavailable local files as never produced,
merge, modify main, update the original Claude branch or start Stage 04.

BLOCKED — EVIDENCE PROVIDED
