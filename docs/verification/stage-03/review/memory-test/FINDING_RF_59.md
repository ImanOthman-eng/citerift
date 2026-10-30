# RF-59 — memory-pressure regression fixture is deadline-sensitive

Observed at 3d91429 on Python 3.12.14: two complete clean-tree runs each ended
with 1662 passing tests and one failing test. The 3000-reference/64-MiB case
returned EXTRACTION_DEADLINE_EXCEEDED instead of its asserted
EXTRACTION_MEMORY_EXCEEDED. Both are containment failures, but the test did
not pass. An isolated run also failed; other isolated runs and the full Python
3.13.5 run passed. All outputs are retained. No exact allocator or scheduler
root cause is claimed.

The fixture was an unreliable discriminator between the independent memory and
wall limits. The correction increases its input to 20000 synthetic references
(1615560 source bytes). Both production limits and the exact memory-error
assertion, including verification of the failure document, remain unchanged.
No production file changes. The 44-test bundle-verifier file passed on both
Python versions (3.93 s and 5.34 s). The new input returned the expected memory
failure in 0.255 s in the direct Python 3.12 size probe.

This is a Stage 03 test correction, not a newly observed incorrect extraction.
The complete suites must be refreshed after this test change. Earlier failed
reports are not replaced or presented as passes. Actual executor: ChatGPT/Codex.
