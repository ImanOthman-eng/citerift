# MF-1: memory-limit failure misreported after a native crash (CI, 2026-11-02)

CI `verify (python 3.12)` on 5b1dcb0 failed one existing test,
`test_wiki_bundle_verify.py::test_the_memory_limit_ends_in_a_stable_failure`: the code was
`EXTRACTION_WORKER_FAILED` instead of `EXTRACTION_MEMORY_EXCEEDED`. No engine code had changed since the previous
green run, so the failure was intermittent.

**Reproduced locally (Python 3.12, before the fix).**

- `memory_limit_probe.py.txt 4` gave, at 64 MiB, 3 × `EXTRACTION_MEMORY_EXCEEDED` and 1 × `EXTRACTION_WORKER_FAILED`
  with detail `exit -11` (SIGSEGV). Limits of 72-96 MiB gave only `EXTRACTION_MEMORY_EXCEEDED`.
- `segfault_trace_probe.py.txt` (the same worker with `-X faulthandler`) crashed after a few dozen runs:

  ```
  Fatal Python error: Segmentation fault
    File ".../mwparserfromhell/parser/__init__.py", line 84 in parse
    File ".../mwparserfromhell/utils.py", line 63 in parse_anything
    File ".../citerift/wiki/source.py", line 318 in run
  ```

**Root cause.** The C tokenizer of mwparserfromhell 0.7.2 does not survive an allocation failure under the worker's
`RLIMIT_AS`: it segfaults instead of raising `MemoryError`. The parent then correctly reports an unexplained worker
death.

**Repair.** `source.py` selects the library's pure-Python tokenizer (`mwparserfromhell.parser.use_c = False`, a
public switch of the library). `tokenizer_equivalence_probe.py.txt` compared both tokenizers on 84 texts (every retained
real source and the 20,000-reference stress page):

- the token streams were identical on all 84;
- total tokenizing time was 0.56 s (C) against 2.45 s (Python);
- the worst single text took 2.03 s (the stress page).

**After the repair.**

- `memory_limit_probe.py.txt 6`: 24 of 24 runs `EXTRACTION_MEMORY_EXCEEDED`.
- `segfault_trace_probe.py.txt`: no crash in 60 runs.
- Regression test: `tests/stage03/test_wiki_mf1_tokenizer.py`.
- after the repair, the full suite: 1777 passed in 535.20s (Python 3.12, local).
- real-data impact: none of the 70 retained real bundles changes (`real_bundles_impact.json`).

## Superseded by MF-1 v2 after review R7 (2026-11-02)

The focused review R7 showed that the pure-Python tokenizer is not equivalent outside the retained corpus: it keeps
`:`, `;` and `!` inside a bare URL followed by a space (MediaWiki and the C tokenizer do not), and it is 10 to 150
times slower on unclosed constructs (RF7-1, RF7-2; `review/round-7/`). "Identical token streams on all 84 texts" was
true only of those texts. The repair above was therefore replaced:

- the engine keeps the C tokenizer, as for all evidence before `b00fa65`;
- `extract._run_worker` classifies a worker death by SIGSEGV or SIGBUS with one more run of the same work, under the
  same limits, with the pure-Python tokenizer: `EXTRACTION_MEMORY_EXCEEDED` when that run exceeds the memory limit,
  otherwise `EXTRACTION_WORKER_FAILED`; its output is never returned as an extraction.

Under a 64 MiB limit, 30 extractions of the stress page: the first (C) run crashed 2 times and reported memory 28
times; all 30 results are `EXTRACTION_MEMORY_EXCEEDED` (`review/round-7/mf1v2_crash_classification_probe.out.txt`).
