# Stage 03 memory-pressure test review

Reviewer: ChatGPT/Codex. Date: 2026-10-30. Read-only repository review; no network, evaluation/final cohort inspection, new probes, or full-suite reruns.

**Disposition: accept the test change as a legitimate stronger memory-pressure test; no blocking finding.** This is a scoped test/evidence assessment, not a claim that the modified full suite has passed.

Reviewed production candidate: `3d91429cbad7108c169c6a45544710faf1abb14d` (HEAD). The sole working-tree change increases synthetic references from 3,000 to 20,000 and adds a comment. Reviewed patch SHA-256: `84d4a4b174681577748888e3828fc5656aa9004c7fa9ad85acc4d6f87deb8d91`. Modified test file SHA-256: `e3f2d37fcacaa297ed03cfc71708f0584a2fc3d874590425a8388ca3c60dbb3e`. Exact reviewed source/evidence hashes are in [SHA256SUMS](SHA256SUMS); patch is in [reviewed.diff](reviewed.diff).

The 64 MiB address-space cap, 30-second wall deadline, CPU limit, isolated child execution, exact `EXTRACTION_MEMORY_EXCEEDED` assertion, and failure-document verification are unchanged. Production code is unchanged. The larger input is 1,615,560 bytes versus 232,560 bytes and requests substantially more parsing/allocation work. Its 20,000 refs equal the configured maximum; the scanner checks the existing count before appending, so this count does not itself exceed the ref limit. Parsing precedes traversal limits. The exact assertion still rejects deadline and structural-limit failures.

Evidence reviewed:

- Both Python 3.12 full-suite logs report 1,662 passed / 1 failed at the original 3,000-reference memory test, which returned the deadline code. The original isolated recheck also failed that way; a second isolated recheck and baseline file run passed. This establishes instability in the original test outcome.
- The clean candidate Python 3.13 report records 1,663 passed, exit 0. It predates the test modification and is not validation of the modified full suite.
- The Python 3.12 size probe returned the exact memory code for 3,000, 6,000, 12,000, and 20,000 refs in approximately 0.25–0.58 seconds. The supplied post-change file runs report 44/44 passing on Python 3.12 and 3.13.

Evidence limits: the evidence supports stronger pressure and the focused passing results, but does not locate the allocation failure, measure worker address-space history, or prove an allocator/interpreter root cause. The final comment correctly describes the observed intermittent deadline result without claiming that mechanism; the initial wording concern is resolved. No report here claims universal determinism or a post-change full-suite pass. `git diff --check` passed. No unresolved material concern was found within this review’s scope.
