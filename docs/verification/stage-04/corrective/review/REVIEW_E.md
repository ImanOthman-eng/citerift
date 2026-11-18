# Corrective cycle, independent review E: security

Reviewer E (security focus). Working tree on top of `f207bc0`, read on 2026-11-18. No file was changed except this one.
Probes ran in the session scratchpad (outside the repository); the one Stage 02 index copy made for a probe was
deleted afterwards. Side effect to note: importing `role_collision_census.py` for a probe refreshed its git-ignored
bytecode cache (`corrective/census/__pycache__/`).

## Scope read

- `corrective/runner/s13_run_v2.py`, `corrective/runner/fail_first_runner.py`, `tests/stage04/test_corrective_runner.py`,
  `corrective/evidence/runner_fail_first.txt`; for context `evaluation/tools/s13_common.py`,
  `src/citerift/investigation/fsutil.py` (`check_memory_root`), `cli.py`, `operations.py`, `outputs.py` (`target`),
  `export.py`, `memory.py` (`created_payload`), `blobs.py` (`get`).
- `git diff f207bc0 -- src schemas` in full: `dt1.py`, `adapters/detector.py`, `adapters/plan.py`, `adapters/detect.py`,
  `explanations.py`, `__init__.py`, `common.schema.json`, `claim.schema.json`; for context `adapters/lookup.py`
  (`observe`, schema check of observations), `investigation/lookup.py` (`bounded_gather`),
  `retraction/query.py` (`render`), `schemas/retraction/v1/lookup-result.schema.json`, `event.schema.json`.
- `corrective/census/role_collision_census.py` and `CENSUS.json`, `corrective/scripts/role_collision_fixture.py`,
  `corrective/regression/regress.py`, `freeze-2/exposure/build_exposure_manifest.py` (subprocess and file use only),
  `tests/stage04/step9_support.py` diff.
- Secret and private-data scan of all 44 changed or untracked files (`git diff f207bc0 --name-only` plus
  `git ls-files --others --exclude-standard`).

## Method

Code reading, then probes that confirm or refute each suspicion:

1. `prepare()` of the corrected runner called directly on scratch directories: a symlinked root, a pre-existing
   `0777` root with a planted file, a root under a directory holding `.git`, an `exports` parent that is a symlink, and a
   `..` path into the repository.
2. The frozen engine 0.2.0 (`git archive f207bc0 src schemas`, loaded with `PYTHONPATH`) ran VS-1 (enwiki 1381772671)
   on the attributed Step 8 subset index into a scratch memory root; then every CLI command of the corrected engine
   0.3.0 (`verify`, `replay`, `show`, `export`, `resume`, `run`) was pointed at that dt-1 investigation.
3. `lookup_view` + `dt1.role_ambiguous` on hand-made observations with malformed `flags` and `notice_hit_count`.
4. `role_collision_census.frozen_class` on a copy of the pinned index for `10.1002/asi.23238`.
5. `uv run pytest tests/stage04/test_corrective_runner.py -q -p no:cacheprovider`: `7 passed in 54.44s`.
6. `grep` for e-mail addresses, token and key formats, and absolute home or session paths in the changed files.

Each finding marks what was **verified** (seen in a probe or command output) and what is **inference** (from code).

## Findings

### E-01 MEDIUM: the runner changes permissions before it validates, and follows symlinks when it does

`s13_run_v2.py:64-67` runs `root.mkdir(..., exist_ok=True)` and `root.chmod(0o700)` **before**
`check_memory_root`. `Path.chmod` follows symlinks.

- Verified: `--memory-root` pointing at a symlink to a `0775` directory is refused ("is not a real directory"), but the
  target's mode has already been changed: `target mode before 0o775` → `target mode after 0o700`.
- Inference (not executed, because it would damage the host): the session runs as `uid=0`. An operator typo such as
  `--memory-root /tmp` or `--memory-root /` passes the inside-repository test (lines 60-63), `chmod 0700` succeeds on a
  root-owned system directory, and `check_memory_root` then **accepts** it (owner = euid, mode now 0700, no `.git` among
  its ancestors). The run would put Investigation Memory directly in `/tmp` or `/` after making it unusable for other
  users.
- This is a mutation-before-validation (check/act order) defect, not a TOCTOU in the strict sense. The engine re-checks the root at
  every subprocess (`memory.py:168/235/300`, fd-based `check_private_dir`), so a root swapped after `prepare()` is still
  refused by the engine. The defect is what `prepare()` itself does to the host.

Recommendation: `os.lstat` first and refuse a symlink or non-directory; `chmod` only a directory the runner has just
created (`mkdir(exist_ok=False)`), otherwise require that an existing root is already private and empty. If a mode fix is
kept, use `os.open(..., O_DIRECTORY | O_NOFOLLOW)` + `os.fchmod`. Add tests for a symlinked root and an existing
non-empty root.

### E-02 MEDIUM: a pre-existing group- or world-writable memory root is silently tightened and accepted

The engine rule (S-15.3, MR-13) **refuses** a memory root that is writable by group or others, because others may have
planted content in it. `prepare()` runs `chmod 0700` first, so the refusal never fires.

- Verified: a pre-existing `0777` directory containing a planted file → `ACCEPTED {...}`, mode `0o700`, planted file
  still present.
- The planted content survives. A pre-made `<key>/` investigation directory would itself be checked by the engine, so
  this is weaker defence in depth, not a demonstrated false positive. It also removes the operator's only signal that the
  directory was exposed.

Recommendation: refuse an existing root that is not already private, or require the root to be absent or empty
(the right default for "the one prediction run"; see also E-07). Test it.

### E-03 MEDIUM: the subprocess engine is not bound to the engine that was checked

`investigate()` (`s13_run_v2.py:83`) runs `[sys.executable, "-m", "citerift.investigation.cli", ...]` with the
inherited environment. `-m` also puts the current directory first on `sys.path`. `frozen_check()` compares **git trees**
of `checked_paths`, not the module the subprocess actually imports. `RUN.json` records no engine identity per article.

- Verified (same mechanism): with `PYTHONPATH=<scratch>/old/src`, `python -m citerift.investigation.cli run ...` ran
  engine **0.2.0** (dt-1) from outside the repository: `partial ... COMPLETED {'NOTICE_CITED': 1, ...,
  'RETRACTED_WORK_CITED': 1}`. The corrected runner would run the same way while `frozen_check` passes on the
  repository tree.
- The docstring (lines 22-23) declares the identity checks out of scope for this correction. The gap is in what those
  checks can prove, and it affects the integrity of the next one prediction run.

Recommendation: run the subprocess with `-I` (or `-P` plus an environment that drops `PYTHON*` variables), and check
once before the first article that `citerift.investigation.__file__` resolves under `REPO/src` and that `__version__` and
`dt1.TABLE_VERSION` are the expected ones. Record the `stage04` identity of each investigation (from `show` or
the export) in its article record and refuse to score on a mismatch.

### E-04 MEDIUM: the census's "frozen dt-1" column is computed with the working-tree table, now dt-2

`role_collision_census.py:30,50-51` imports `citerift.investigation.dt1` from the working tree and labels the result
`frozen_dt1_outcome` (docstring: "with the frozen dt-1 code"). The output records no table or engine version.

- Verified: rerun now on a copy of the pinned index, `frozen_class(index, "doi", "10.1002/asi.23238")` gives
  `dt-2 {'rule': 'D-10', 'class': 'UNRESOLVED_IDENTITY', 'reasons': ['IDENTIFIER_ROLE_COLLISION'], ...}`. The committed
  `CENSUS.json` shows D-14 positives for the same group (`same_record_only ... 'D-14 RETRACTED_WORK_CITED': 13489`), so it
  was produced before the change. A rerun of the tool documented in `ROOT_CAUSE.md` section 2 no longer reproduces the
  committed evidence. It would silently label dt-2 outcomes as frozen.

Recommendation: load the frozen table from git as `regress.py:frozen_dt1` does, assert `TABLE_VERSION == "dt-1"`, and
write the table version, tool SHA-256 and frozen commit into `CENSUS.json`.

### E-05 LOW: the absolute memory path goes into a committed record, and can leak through error records

- `RUN.json` gets `operational.memory_root` = the resolved absolute path (`prepare()` line 79, `main()` line 205).
  `RUN.json` is committed evidence. A path under `/home/<user>/` or a session scratchpad discloses an account name or
  session identifier (the identity rule in docs/identity.md concerns public files). Inference.
- The article record has no `memory_root` key (tested, line 89). But `rec["error"] = doc` (line 119),
  `rec["export_error"] = edoc` (line 134) and the `unparsed_stdout`/`stderr` fallback (line 88) copy engine detail
  strings verbatim. Some engine details echo the memory root (verified in probe 1: `MEMORY_ROOT_UNSAFE: /tmp/claude-0/...
  is not a real directory`). After `prepare()` this only happens if the root changes mid-run, so it is unlikely. It still
  contradicts the docstring's "in no article record".
- Verified, pre-existing and outside the repository: the journal's `investigation_created` payload stores
  `request.memory_root` (seen in the probe journal). It is not in the investigation key or the export.

Recommendation: record a non-identifying locator (for example `"memory_root": "outside repository; checked"` or a
salted digest) and redact the resolved root from error strings copied into article records.

### E-06 LOW: a symlinked export parent is accepted, so exports can land outside the campaign

`prepare()` lines 72-78 accept an existing `run/exports` that is a symlink (`is_dir()` follows it). The engine's
`outputs.target` resolves the parent (`outputs.py:42`), so exports are written to the link target while the record says
`run/exports/<name>`.

- Verified: `exports symlink: ACCEPTED`.

Recommendation: `os.lstat` the export parent and refuse a symlink. Resolve it and require it under the resolved
campaign directory.

### E-07 LOW: dt-1 investigations are refused, but reported as corrupt; a reused memory root fails every article

Version identity is enforced: the `stage04_identity` schema now pins `schema_version: "4.0.0"` and
`table_version: "dt-2"`, so a journal created by engine 0.2.0 fails record validation at seq 0.

- Verified: all six commands of engine 0.3.0 refuse the dt-1 investigation, and none misreads it:
  `corrupt 12 ... INVESTIGATION_CORRUPT CORRUPT: RECORD_INVALID: SCHEMA at seq 0: /payload/stage04/schema_version:
  '4.0.0' was expected; /payload/stage04/table_version: 'dt-2' was expected`. `export` gives `EXPORT_REFUSED` and
  writes nothing. Fail-closed holds.
- But a valid frozen-engine record is labelled "corrupt" (exit 12). An operator may take this as tampering or delete
  evidence. The investigation key does not include the engine identity, so the same article in a reused memory root
  collides: every article would end in this error. Neither the runner nor a test covers that case.

Recommendation: report an identity mismatch with its own code (for example `ENGINE_IDENTITY_DIFFERS`, status
`stale` or `invalid`) before schema validation of the created record. Have the runner require a fresh or empty memory
root. Add one test that opens a dt-1 journal with the new engine.

### E-08 LOW: `flags` type handling fails open where `notice_hit_count` fails closed (defence in depth)

`detector.py:54`: `flags=tuple(str(f) for f in e.get("flags") or ())`. `detector.py:95-96`: a non-integer, boolean
or negative `notice_hit_count` → `None` → `notice_elsewhere` returns True (may be a notice).

- Verified: `notice_hit_count` of `None`, `True`, `-1`, `"5"` or `1.0` → `hits None`, event ambiguous (fail closed, correct).
  `flags` given as the string `"NOTICE_DOI_EQUALS_ORIGINAL"` → `('N','O','T',...)`, not ambiguous. `flags` absent →
  `()`, not ambiguous (fail open).
- Mitigation (verified by reading): observations are schema-validated when LOOKUP writes them (`adapters/lookup.py:308`,
  `event.schema.json` requires `flags` as an array of enum values, and `lookup-result.schema.json` requires
  `notice_hit_count` as an integer ≥ 0). Blobs are hash-checked on every read (`blobs.py:75`). A malformed observation
  therefore cannot reach DETECT without a consistent rewrite of memory. DETECT does not re-validate observations
  (`detect.py:77-79` validates only the candidate inputs and the plan).

Recommendation: in `lookup_view`, treat `flags` that is not a list of strings as malformed (`DetectFailure
ADAPTER_INCONSISTENT`), symmetric with the `notice_hit_count` handling.

### E-09 INFO: the new inputs can only move a decision toward abstention

`role_ambiguous` is read only by `_d10` (adds D-10 → `UNRESOLVED_IDENTITY`) and by `decide` (adds the reason
`IDENTIFIER_ROLE_COLLISION`) (`dt1.py:393`, `465-466`). No new path leads to a positive or to `NOTICE_CITED`. Forging
these inputs in a tampered index or memory toward a positive (removing a flag, zeroing `notice_hit_count`) only restores
dt-1 behaviour. That is no more power than forging an event outright. The index identity (D-062, checked by
`IndexVerifier`) and the hash-chained memory cover both. An unavailable Q1 lookup states nothing (`notice_elsewhere`
returns False), but D-13 precedes every positive, so this does not open a positive path (inference from the documented
precedence).

### E-10 LOW: the regression loads the frozen table with `git show` and `exec`

`regress.py:60-73` runs `git -C REPO show b5bf8ed…:src/citerift/investigation/dt1.py` and `exec`s the output. A full
40-hex commit pins the content. The argv list has no shell. Verified: the blob is `27409702a03f04d49f5dd984b0fc6a8c6719c554` at
both `b5bf8ed` and `f207bc0`. The repository's `.gitattributes` defines no textconv, and the system config defines only
LFS filters. The residual dependence is on porcelain behaviour and git configuration.

Recommendation: use `git cat-file blob <commit>:<path>`, assert the blob id `27409702…`, and record it in the output.

### E-11 INFO: other scripts

- `role_collision_fixture.py` verifies the CSV against the pinned receipt (line 174) but not that `--index` was built
  from it. It also writes the fixture and manifest **before** returning 1 on disagreement (lines 221-243). A
  disagreement leaves files behind with `subset_equals_full_index: false` recorded in them. The flag is honest, but
  writing only on success would be safer.
- `build_exposure_manifest.py`: fixed argv (`git -C ROOT ...`, `sys.executable -I <tracked rule>`), and it writes to
  stdout. No issue found.
- `fail_first_runner.py` `exec`s a string-replaced copy of a repository file in a temporary directory (evidence mutant). No
  issue found.

### E-12 INFO: secrets and private data

No e-mail address, token, key format or legal name was found in the 44 changed or untracked files. The fixture CSV
keeps 11 non-personal columns: the Retraction Watch `Author` column is emptied. The only absolute session path is the
scratchpad index path in `REVIEW_BRIEF.md:56`, which is operational and not a secret.

### E-13 INFO: what holds, as specified

Verified: a relative root is refused. A root inside the repository, including through `..`
(`/home/user/citerift/../citerift/docs/x`), is refused **before** anything is created. A root under a `.git` working tree is
refused, but its directories are created first (`wt dirs created anyway: True`). The test for this case does not
assert absence, which is minor and covered by the E-01 recommendation. The export parent is created before the first
article. In `main()` every refusal (`frozen_check`, `prereg_check`, `prepare`, `articles_of`) happens before the first
`run_article`. `RunnerRefused` is a `SystemExit`. `pytest tests/stage04/test_corrective_runner.py`: `7 passed`.

## Verdict

No CRITICAL or HIGH finding in the production change: the new inputs can only add abstention, malformed hit counts fail
closed, and dt-1 investigations are refused rather than misread. Before the next prediction run, the runner needs E-01,
E-02 and E-03 fixed and the census needs E-04 fixed.
