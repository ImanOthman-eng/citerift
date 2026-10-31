# Final campaign execution log

2026-10-30: candidate 48cfeab and protocol committed at 6a133ed before fresh
content acquisition. Initial 10 Arabic and 10 English captures all complete.
Including capability preflight, 44 HTTP attempts and 4054831 accepted body
bytes are charged to the same 500-attempt / 300-MiB campaign ceiling.
The retry driver found no eligible failures; it issued no additional request.

2026-10-31: four isolated ChatGPT/Codex evaluator instances completed the
initial 20 raw-only packets. Exact-position and metadata validation found no
errors; this checks record integrity, not semantic correctness of the labels.
No extraction predictions exist yet. Annotation hashes are locked before
reserve decisions. Raw helper bytes are retained as .py.txt in evaluator-specific
directories with ARCHIVE_MAP.json preserving original names and hashes; these
are historical evaluator artifacts, not product scripts to lint or import.

A detached evidence worktree is used while the two complete repository suites
run against a clean primary checkout at cd085dd. This permits protocol-required
annotation commits without changing the tested tree. One implementer writes
these additive evidence commits; they descend from the existing Stage 03 branch
and will be fast-forwarded back to it. No second PR, remote branch, merge into
main, acceptance record or later stage is created.
