# CITERIFT Project Status

<!-- GENERATED FILE: do not edit. Source: governance/stage_registry.json. Regenerate with `citerift-gov render-status --write`. CI fails if this file is stale. -->

Repository: `ImanOthman-eng/citerift`. Owner: EVE TELOS.

Technical verification, owner acceptance and authorization of the next stage are three separate decisions.
Only the owner can accept a stage or authorize one.

## Stages

| Stage | Name | Executor | Depends on | Status | Verified revision | Accepted |
|---|---|---|---|---|---|---|
| 00 | Engineering Foundation | engineering-agent | - | `ACCEPTED_CLOSED` | 0c21182e5871 | yes |
| 01 | Independent Feasibility Investigation | external-agent | - | `ACCEPTED_CLOSED` | 85da719ac43f | yes |
| 02 | Retraction Data Engine | engineering-agent | 00, 01 | `ACCEPTED_CLOSED` | cf060834afed | yes |
| 03 | Wikipedia Extraction Engine | engineering-agent | 00, 01 | `ACCEPTED_CLOSED` | b93314dfde74 | yes |
| 04 | Detection Engine and Vertical Slice | engineering-agent | 02, 03 | `NOT_STARTED` | - | no |
| 05 | Citation Context and Evidence Preparation | engineering-agent | 04 | `NOT_STARTED` | - | no |
| 06 | AI Investigation and Scientific Evaluation | engineering-agent | 05 | `NOT_STARTED` | - | no |
| 07 | Cross-Wiki Intelligence and Backend API | engineering-agent | 06 | `NOT_STARTED` | - | no |
| 08 | Creative Interactive Frontend | engineering-agent | 07 | `NOT_STARTED` | - | no |
| 09 | Release, Research Report, and Submission | engineering-agent | 08 | `NOT_STARTED` | - | no |

## Next actions

- Stage 04 (Detection Engine and Vertical Slice): dependencies accepted; NOT authorized until the owner explicitly authorizes it

## Open blockers

- None recorded.

## Stage notes

- Stage 01: Executed by a separate external agent. The owner reports the investigation was reported externally; its handoff has not been supplied to this repository and none of its findings are accepted. The exact evidence file set is fixed when the owner delivers the handoff.

## Recent history

- 2026-11-02T15:40:17Z stage 03: IMPLEMENTED_NOT_VERIFIED -> IN_PROGRESS by engineering-agent (owner ref `cmsg_018VCB51nDHP6HXmLU4ea5yP8BNaHtTfgxhSrEp6pbWPHh`). Rework under the owner's instruction of 2026-11-02 (D-034): short-footnote semantics, DOI/PMID and Retry-After audits, adversarial review, then one prospective confirmation campaign
- 2026-11-02T18:07:49Z stage 03: IN_PROGRESS -> IMPLEMENTED_NOT_VERIFIED by engineering-agent. D-034 candidate frozen before the confirmation draw: sfn semantics, DOI D-1/D-2, Retry-After G-1/G-2, campaign tools, MF-1 v2, reviews R6 and R7 fixed; CI green on 3e51792
- 2026-11-03T05:56:20Z stage 03: IMPLEMENTED_NOT_VERIFIED -> IN_PROGRESS by engineering-agent (owner ref `cmsg_018VCB51nDHP6HXmLU4ea5yPBxa7nEyAiE3VN5Lw442e8F`). Owner instruction of 2026-11-03 (D-035): correct the G5c citation-unit semantics and run one further prospective confirmation of the corrected candidate
- 2026-11-03T14:31:36Z stage 03: IN_PROGRESS -> IMPLEMENTED_NOT_VERIFIED by engineering-agent. D-035 candidate frozen before the confirmation draw: citation-unit classes A-H, both independent reviews fixed, MF-1 v3; CI green on fff0e5b
- 2026-11-04T02:22:53Z stage 03: IMPLEMENTED_NOT_VERIFIED -> IN_PROGRESS by engineering-agent (owner ref `cmsg_018VCB51nDHP6HXmLU4ea5yPJGcnAZCAku5nJRxTZzFaL7`). Owner instruction of 2026-11-04 (D-036): correct R-038 fail-first, review the Stage 03 flow before validation, and run one final prospective bilingual confirmation of the frozen corrected candidate
- 2026-11-04T09:05:12Z stage 03: IN_PROGRESS -> IMPLEMENTED_NOT_VERIFIED by engineering-agent. D-036 candidate frozen before the confirmation draw: R-038 corrected, two independent reviews and the focused re-review fixed; CI green on 8901a59
- 2026-11-09T13:20:44Z stage 03: IMPLEMENTED_NOT_VERIFIED -> IN_PROGRESS by engineering-agent. Clean delivery history (owner instruction 2026-11-09, cmsg_018VCB51nDHP6HXmLU4ea5yPKQJiBv5w48TqZw8UJbfJvw, D-038: a clean-history integration path that does not propagate restricted historical blobs into main). This branch starts from main with the exact tree of the scientific-record revision 80852e48732607129bdf7407480d417f588caf5d (branch claude/project-thread-o4amfd, continuing PR #5), whose src and schemas trees equal the frozen D-036 candidate 8901a597015b7c6d6eb8464554e79b4fa1383615. That candidate and the campaign commits are not ancestors here, so the implementation record is re-established on this history; no code, schema, test or evidence changes.
- 2026-11-09T13:48:53Z stage 03: IN_PROGRESS -> IMPLEMENTED_NOT_VERIFIED by engineering-agent. Stage 03 implementation re-recorded on the clean delivery history (owner instruction 2026-11-09, cmsg_018VCB51nDHP6HXmLU4ea5yPKQJiBv5w48TqZw8UJbfJvw, D-038). b93314d carries the D-036 candidate engine 8901a59 unchanged (src tree cda4a4b6, schemas tree 360501fc) and the complete D-036 campaign record of 80852e4.
- 2026-11-09T13:49:23Z stage 03: IMPLEMENTED_NOT_VERIFIED -> VERIFIED_AWAITING_OWNER_ACCEPTANCE by engineering-agent. D-036 final confirmation passes every gate G1-G11 and every minimum in both languages on the adjudicated labels (evaluation/confirmation-d036/campaign/REPORT.md); complete matrix at b93314d (2051 passed on Python 3.12 and 3.13, static, governance, schema, lock, dependency audit, protected paths, installed wheel, simulations, offline verify/replay 44/44; TEST_RESULTS.md section 9); GitHub CI run 42624868434 success. Owner instruction 2026-11-09 (cmsg_018VCB51nDHP6HXmLU4ea5yPKQJiBv5w48TqZw8UJbfJvw, D-038). Not owner acceptance.
- 2026-11-09T19:31:25Z stage 03: VERIFIED_AWAITING_OWNER_ACCEPTANCE -> ACCEPTED_CLOSED by owner (owner ref `cmsg_018VCB51nDHP6HXmLU4ea5yPA53UZUXU5DvyUnnjuxy3EJ`). Owner accepts Stage 03 (Wikipedia Extraction Engine) at the verified revision b93314d, delivered through PR #6 (head eb0b694), based on the completed D-036 validation and its documented scientific limitations (Arabic G2 decided by one adjudicated correction; English G5c interval reaching 0.929, R-036; G7 vacuous in the D-036 sample; 2026-11-04 evaluator transcripts unavailable; AI labels; limited field coverage of the R-038 path). The owner confirms the D-036 evidence archive and SHA-256 manifest are saved outside the Claude workspace. Stage 04 is not authorized.

Decisions: [DECISIONS.md](DECISIONS.md). Risks and known defects: [RISKS.md](RISKS.md).
Changes: [CHANGELOG.md](CHANGELOG.md). Rules: [GOVERNANCE.md](GOVERNANCE.md).
