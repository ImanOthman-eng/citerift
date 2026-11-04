# Final independent integration audit of the D-035 work (owner instruction D-035 section 9)

**Auditor.** A separate Claude Code agent (general-purpose subagent, own context), instructed to work read-only: no
write in the repository, no state-changing git command, no network request, no governance transition. It is an AI
audit, not a human review. Run on 2026-11-03 against `6c499a7`; a documents-only commit (`6989622`) landed during the
audit and changes no code, schema, test, lock, `.github`, governance file, `GOVERNANCE.md` or `CLAUDE.md`.

**Legend.** [V] verified by a command and its output; [I] inference or judgement.

## Findings

| Id | Severity | Finding | Location |
|---|---|---|---|
| F-1 | high | Inside one template's output, uses of one name are paired with rendered markers in source order, while the template decides the rendered order (the function's own docstring). Causes both Arabic G6b false attachments; predates D-035. = RISKS.md R-038 | `src/citerift/wiki/reconcile.py` 283 (docstring), 307-311 (`zip(uses, rs)`), 382 (sort by source position) |
| F-2 | medium | No test covers this path (`grep name_in_template_output\|align_unordered tests/`: nothing) | `tests/` |
| F-3 | low | The third-party AWS key-id pattern remains in git history: tracked at `4766a1f` (3 files) and at `763c1c4`, `153efae`, `0ff6446` (5 files each), untracked from `eba17d7`. The Stage 00 secret test would fail at those commits, and a merge commit publishes that history to `main`. It is a third party's key id inside a public Wikipedia presigned URL | `campaign/WITHHELD_FILES.json` |
| F-4 | low | The new nested `.gitignore` narrows what the Stage 00 secret test scans: the test lists files with `git ls-files --cached --others --exclude-standard`, so ignored files are skipped. The test is unchanged and the exclusion is limited to the five listed files and disclosed | `tests/stage00/test_repository.py` 160-167, `campaign/.gitignore` |
| F-5 | info | The score field `false_attachments_allowed` holds the excess FA − max(1, ⌊0.01·links⌋), not the allowance (ar 1, en −2) | `protocol/scripts/evaluate.py` 744 (frozen) |
| F-6 | info | The MANIFEST lists `make_packets.py` as reused unchanged; the campaign ran it through `make_packets_partial.py` (disclosed; no effect on complete captures, item 3a) | `confirmation-d035/MANIFEST.json` |
| F-7 | info | The two re-pinned `extraction_digest` values in `fixtures/observed/expected.json` differ only through the version strings 1.0.0 → 1.1.0 | item 1 |

No critical finding.

## Item 1. Change set `f88bdd7..6c499a7`: confirmed

- [V] In `src`, `schemas`, `tests`: modified `schemas/wiki/v1/extraction.schema.json` and `src/citerift/wiki/`
  `__init__`, `extract`, `issues`, `model`, `source`, `verify`, `worker`; added `units.py` and three test files;
  modified pre-existing `fixtures/observed/expected.json` and `test_wiki_mf1_tokenizer.py`; nothing deleted.
- [V] Pre-existing tests not weakened: `expected.json` changes two digests only. Running the `f88bdd7` engine and
  the head engine on both fixtures, the only differences are `extractor.version`, `schema_version` and the digest.
  `test_wiki_mf1_tokenizer.py` gains three tests; no existing test edited. The only new `skipif` markers are on the
  two new `/proc`-dependent tests.
- [V] At the head code: `pytest -p no:cacheprovider -q` 1972 passed (632 s); `ruff check` clean; `mypy` no issues
  in 52 source files.
- [V] Protected paths unchanged: `.github/`, `src/citerift/governance`, `schemas/governance`, `GOVERNANCE.md`,
  `CLAUDE.md`, `tests/stage00-02`, `simulations/`, all of `src/citerift` outside `wiki/`.
- [V] Head equals the frozen candidate: tree and blob hashes of `src`, `schemas`, `pyproject.toml`, `uv.lock` and
  `tests` are identical at `fff0e5b` and `6c499a7`. The head engine reproduces the committed `ar-76814232` digest.
- [I] No high-impact bug introduced by D-035 was found in the render-before-model order of `extract.py` and
  `verify.py`, `units.source_model`, `_remap_entities` or the MF-1 v3 classification. Unit classes depend on render
  availability; this is documented (R-037).

## Item 2. Arabic G6b: confirmed in every part; the engine is wrong, the locked label is right

- [V] Bundle `ar-10469946-a1`: every artifact hashes to its name; source SHA-1 equals the page and render revision.
- [V] Source: cp 1897 `<ref name=Mallama2014>` on `| b-v = +1.31`; cp 2467 `<ref name=Mallama2014/>` on `| u-b = +1.45`.
- [V] Render: `cite_ref-Mallama2014_4-0` is in the U−B row (+1.45), first in document order, and its `data-mw` has
  no `body` (a reuse); `…_4-1` is in the B−V row (+1.31) with `"body":{"id":"mw-reference-text-cite_note-Mallama2014-4"}`
  (the definition).
- [V] Engine: definition `us-00005` → `_4-0`, reuse `us-00006` → `_4-1`, basis `name_in_template_output`: both wrong.
- [V] Locked label (locked in `153efae`, before the prediction commit `e2f7e0a`): `u5` → `_4-1`, `u6` → `_4-0`,
  correct; adjudication decisions 7-8 confirm it.
- [V] Independent recount: ar 184 engine links, 182 correct, 2 false (only `u5`, `u6`); en 203, 203, 0; identical on
  locked and adjudicated labels. G6b is the only failed gate in either language or label set.
- [V] The code predates D-035: empty diffs `3e51792..fff0e5b` and `f88bdd7..fff0e5b` for `reconcile.py`;
  `git log -L` names `a29bb4e` and `2f652ca`; the `f88bdd7` engine gives the same wrong pairing.
- [I] `RenderUse` (`render.py` 153-161) has no field for the `data-mw` body, which could tell the definition from a
  reuse here; untested.

## Item 3. Deviations: confirmed

- (a) [V] The frozen `make_packets.py` is unchanged since `6f39025`. The wrapper asserts the old guard occurs once,
  replaces only it, and executes the frozen source with its own `__file__`. Packets regenerated in scratch are
  byte-identical (`diff -r`) to the committed `annotations/packets`, `ASSIGNMENT.json` included. [I] For complete
  captures both guards behave identically.
- (b) [V] The five withheld files exist on disk with the declared SHA-256 and sizes, equal their blobs at `763c1c4`
  / `4766a1f`, are untracked and ignored, and hold the declared number of matches of `AKIA[0-9A-Z]{16}`, all one
  key id (not reproduced here). `git grep` at the head finds the pattern in no tracked file. The stated reason is
  accurate (`tests/stage00/test_repository.py` 152, 171, unchanged).

## Item 4. Evidence audit: confirmed

[V] `campaign/audit/evidence_audit.py` re-run from the repository root (output to scratch) exits 0. The only
difference from the committed `EVIDENCE_AUDIT.json` is `"head"` (`6c499a7` against `e754cce`, where it was generated);
all 28 checks are identical and `all_ok` is true.
