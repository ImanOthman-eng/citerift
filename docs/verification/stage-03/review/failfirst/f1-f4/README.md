# F1-F4: reproduction, fixes and evidence (SYNTHETIC inputs)

| File | What |
|---|---|
| `F1-F4_case.py.txt` | The reproduction: synthetic bundles through the public isolated extraction API (run with `uv run python`) |
| `F1-F4_before.json` | Its output at `049c48c`, the reviewed head: every F1-F4 failure reproduced, and the controls correct |
| `F1-F4_after.json` | Its output after the fixes (RF-39 to RF-42) |
| `tests_at_62ffe3f.txt` | `tests/stage03/test_wiki_f1_f4.py` run against the code before any fix (the test's import of `effective_arguments` stubbed out) |
| `tests_at_fa877d9.txt` | The same, after F4 and before F1-F3 |
| `template-sources/` | The retained source of the reuse templates that F4's rules follow, with the request log |
| `real-bundles/` | Marker states and evidence over all 54 retained real bundles, before and after the F1-F3 change: identical (`marker_diag.py`; old data used for regression only) |

The mapping to review ids is in `../../REVIEW_FINDINGS.md`: F1 = RF-39, F2 = RF-40, F3 = RF-41, F4 = RF-42, and
RF-43 is the short-footnote key check that F4 asked for.
