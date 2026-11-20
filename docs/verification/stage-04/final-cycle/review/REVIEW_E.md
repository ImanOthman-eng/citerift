# Review E: security, boundaries and performance (final corrective cycle, D-083)

Reviewer E, independent of the author. Base `6663314`, head `de7dcc2`. [V] marks a fact I verified (by reading the
code at the line given or by running the probe shown); [I] marks an inference.

## Scope read

- `src/citerift/investigation/bibliographic.py` (all), `adapters/normalize.py` (diff and `normalize`/`_normalize`),
  `adapters/lookup.py` (diff, `observe`), `adapters/detector.py` (lookup_record items), `dt1.py` (role scans,
  `comparisons`, RULES, `decide`), `controller.py` (`_attempt`, `_succeed`, `_defect`, `open_controller`),
  `canonical.py` (`check_value`, `canon`), `fold.py` (E-07 diff), `memory.py` (`create`, `open`, `_read`), `lock.py`,
  `fsutil.py` (`check_memory_root`), `cli.py` (E-05 diff, `_request`, `dispatch`, `main`), `operations.py`
  (`run`, `opened`, `checkpoint`), `checkpoint.py` (`make`).
- Stage 03 isolation for comparison: `src/citerift/wiki/source.py:42-45,338`, `wiki/extract.py:49-65,596-707`,
  `wiki/worker.py`.
- `schemas/investigation/v1/common.schema.json` (`cited_bibliography`), `candidate-inputs.schema.json` (bounds).
- `BIBLIOGRAPHIC_SPEC.md` sections 2.1, 2.2, 8, 9.
- Bounds: `final-cycle/bounds/bounds.json`, `review/step7/d055/bounds.json`, `d055/bounds.py`, `d055/part_ceiling.py`
  (diff), `closure/storage_bounds.py` (diff), `closure/lookup_budget.py` and `.json`, `d053/part_ceiling.json`.
- `final-cycle/scripts/c07_profile.py`; `tests/stage04/test_final_lows.py`; `final-cycle/lows/fail_first_e05_before.log`.

## Method

Code reading plus small probes (`uv run --offline python`, each a few seconds of CPU; one probe at 36 KB took 29 s
before I scaled it down) in my scratchpad; one targeted test file (`tests/stage04/test_final_lows.py`: 3 passed).
No full suite, no network, no file changed except this one. I did not read campaign labels.

## Findings

### E-01 MEDIUM: an HTML numeric entity for a surrogate fails the whole NORMALIZE step

- [V] Spec 2.1 step 4 decodes HTML entities (`strip_code(normalize=True)`, `bibliographic.py:251-254`).
  mwparserfromhell decodes `&#xD800;` (or `&#55296;`, any of U+D800 to U+DFFF) to a lone surrogate. Probe:
  `cited_object('{{cite journal |title=Retraction of X&#xD800; |last1=Hon}}','en').titles` is
  `('Retraction of X\ud800',)`. `canon()` of the `cited_bibliography` evidence then raises
  `CanonError CANON_INVALID: a string holds a lone surrogate` (`canonical.py:73-77`).
- [V] `cited_description` (`normalize.py:137-148`) catches only decoding errors. `normalize()` (`normalize.py:150-159`)
  does not catch `CanonError`. The error comes up either in the adapter's own `canon(output)`
  (`normalize.py:347`, caught by `controller.py:310` as "adapter raised") or in `_succeed`'s evidence batching
  (`controller.py:374-377`). Either way the result is `_defect`, which ends the attempt terminally (`controller.py:531-536`).
- Effect: one edit to any title, author, periodical, date or page argument of any citation template on a page makes the
  whole page's investigation fail. It should give that unit no cited object (`C = ⊥`). The failure is closed, so
  there is no false positive, but it breaks spec B8 ("no input ... raises; it yields INSUFFICIENT"). Stage 03 does not
  decode title arguments, so it extracts such a page without complaint [I]. The reference model makes the same call
  (`simulations/stage04/bib_reference.py:160`), so the differential tests cannot find this. No corpus case or test
  covers it (grep for `D800`/`surrogate` in `test_final_bib.py`, `build_corpus.py`, `bib_reference.py`: none).
- Recommendation: amend spec 2.1 (owner) so that a cleaned value that is not UTF-8 encodable gives `C = ⊥` (or makes
  that value absent). Implement it in production and in the reference model, add corpus cases (`&#xD800;`,
  `&#xDFFF;`) and an adapter-level fail-first test that NORMALIZE succeeds on such a unit.

### E-02 LOW: parsing is super-linear, runs in the controller process with no deadline, and the size bound comes after it

- [V] The bound of spec 2.1 step 6 (`bibliographic.py:283-287`) is checked after `mwparserfromhell.parse` and after
  `strip_code` of every family argument. It does not limit parse cost. Probes (CPU seconds, `cited_object`):
  `'[[a|{{b|[[c|' * n` inside `|title=`: n=100 → 0.023 s, 200 → 0.099, 400 → 0.44, 800 → 1.86 (9.6 KB),
  3000 → 29.5 s (36 KB). Doubling n gives about four times the time, so the cost is quadratic. Other shapes stay
  linear or fast: 5,000-deep templates (0.07 s), 20,000 unclosed `{{`/`[[`/`{{{` (≤ 0.007 s), 20,000 parameters
  (0.36 s, `None`), 1 MB title (0.08 s, `None`), 100k entities (0.32 s, `None`), a 200k-digit `author###` name
  (0.006 s). Peak RSS was 64 MiB.
- [V] Stage 03 runs the same tokenizer (C, `use_c=True`) in a subprocess with an address-space limit, RLIMIT_CPU and
  a 30 s wall deadline (`wiki/extract.py:55-56,596-602,676-685`). Its comments (`source.py:42-45`) record that the C
  tokenizer can segfault under memory pressure. NORMALIZE now parses in-process with none of these limits.
- [V] The same pathological text costs the same to parse in page context with Stage 03's `skip_style_tags=True`
  (n=800: 1.375 s vs 1.399 s). So whatever Stage 03 accepted within its deadline, NORMALIZE re-parses at roughly
  the same cost again: the bound is relative, not absolute [I]. With style-heavy text the cost is about 2.5 to 3 times
  higher without `skip_style_tags` (n=1000 `''[[a|''b`: 0.163 s vs 0.407 s).
- Recommendation: measure and retain is acceptable for the freeze. Record the per-page NORMALIZE parse time in the
  D-064 performance evidence. If the owner wants an absolute limit, a pre-parse span cap that gives `C = ⊥` is a spec
  change and needs an owner decision. It must not truncate.

### E-03 MEDIUM: the E-05 redaction is incomplete (two verified leaks)

- [V] `run --request FILE`: `_redactor` reads only `args.memory_root` (`cli.py:273`). With `--request` that is None
  (`cli.py:165-167`), so the redactor does nothing, while the root comes from the request file. Probe: a request
  whose `memory_root` is world-writable printed
  `"detail": "/…/e05/acct-secret/ww/mem is writable by group or others"` in JSON and text (exit 3).
- [V] Ancestor paths: `check_memory_root` names the enclosing working tree
  (`fsutil.py:112`: `"{path} is inside a repository working tree ({parent})"`) and the repository
  (`fsutil.py:116`). The redactor replaces only whole spellings of the root, so the ancestor is printed. Probe:
  `show --memory-root …/acct-secret/proj/mem` (with `proj/.git`) printed
  `<memory-root> is inside a repository working tree (/…/e05/acct-secret/proj)`. The account and session segments
  leak. `test_final_lows.py:51-60` covers only `world_writable` and `missing_key` on `show`.
- [V] Covered correctly: a symlinked parent (`…/link/ww/mem` → redacted), trailing slash and `.` (pathlib
  normalizes them), `..` (the as-given and resolved spellings are both replaced), library `OSError` text
  (substring), and text format (redaction runs before `_text`).
- Not part of E-05 but the same class [V]: `--index`, `--bundle` and `--request` absolute paths are not redacted
  (`operations.py:178-186` print the request path).
- Recommendation: build the redactor from the effective root (the request's `memory_root` for `run --request`).
  Also replace every ancestor path of the root that is longer than `/` and contains a path segment below the root's
  first two components, or (simpler and stronger) make `fsutil` messages never print `parent`/`repo` and redact
  those at the source. Add both probes as fail-first tests.

### E-04 MEDIUM: the redaction rewrites unrelated substrings and can corrupt digests in printed output

- [V] `_redactor` applies plain `str.replace` to every string of the result (`cli.py:285-289,340`). It includes the
  as-given relative spelling if it is longer than one character (`cli.py:280-281`). Probe:
  `_redactor(Namespace(memory_root=Path('ab')))({'claim_id': '00ab12ab'*8})` returns
  `'00<memory-root>12<memory-root>…'`. With `memory_root=Path('memory')` the text "under the memory root" becomes
  "under the `<memory-root>` root". A relative `--memory-root` is accepted (`cli.py:171,184` call `.absolute()`).
  So `--memory-root db` (hex letters) silently changes claim ids, digests and the `checkpoint --out` result's
  `journal_digest` in JSON output. The checkpoint file itself is not affected.
- Recommendation: replace only absolute spellings, and only at path boundaries (followed by end, `/`, a quote or
  whitespace). Or redact only the fields that can carry paths (error details, `exported`, `written`, `request`) and
  never digest-valued fields. Add a test with a short hex-letter relative root.

### E-05 INFO: the unredacted checkpoint output is safe

- [V] The bytes written by `checkpoint` without `--out` are `d052.encode(make(...))`. `checkpoint.py:38-46` holds
  only `format`, `format_version`, `investigation_key`, `seq` and `journal_digest`, so it carries no path. Not
  redacting it is correct, because redaction could only damage it (see E-04). The `statement` on stderr is redacted.

### E-06 INFO: the E-07 refusal comes before schema validation and before any write

- [V] `Folder` checks `v`, then `engine_identity_differs` for seq 0, then `problems(rec, RECORD)`
  (`fold.py:631-640`). The check reads only `stage04.table_version` and `stage04.schema_version` as strings and runs
  `ref_problems` against two small definitions (`fold.py:164-182`).
- [V] The controller opens read-only first (`controller.py:747-752`). `operations.opened` and `run` (existing key)
  also open read-only. A read-only lock uses `O_RDONLY` with `flock` and writes nothing (`lock.py:47-53`). Torn-tail
  repair and temporary cleanup run only after every record folds (`memory.py:262-279`). So no crafted journal reaches
  a write before the refusal.
- Two small overstatements of "nothing is read" [V]: the whole journal (≤ 512 MiB) is read and canonically parsed by
  `_read`/`parse_journal` (`memory.py:395-406`) before record 0 is folded. The refusal detail embeds
  `engine_version!r` with no length cap (`fold.py:180`; `InvariantViolation` does not truncate, `errors.py:47-51`),
  so a crafted value of up to the 1 MiB record limit is echoed in full. Recommendation: truncate the repr (for example
  to 200 characters) and say "nothing is written" rather than "nothing is read".

### E-07 MEDIUM: the LOOKUP observation bound (D-048) is stale for observation v3

- [V] The D-048 derivation assumes no stored byte costs more than 6 observation bytes
  (`closure/lookup_budget.py:344-348`, `rho_bound 6.0`). Its JSON was not regenerated (last commit `906308e`).
  `final-cycle/bounds/bounds.json` carries the same row: `LOOKUP observation (D-048)`: 102,311,086 B, 0.3811.
- [V] Observation v3 adds `records` (title, authors, journal per event, `lookup.py:252-255`). `title` and `journal`
  were already in both `result.events` and `events`, so they now appear three times. I measured with
  `lookup_budget.py`'s own row builder and the production `observe()` (rows of `\x01` × 4096, n = 20 and 80):

  | text in | ρ v2 `observe` | ρ v3 `observe` |
  | --- | --- | --- |
  | Title, Journal, Author (doi match) | 3.859 | 7.663 |
  | Title only | – | 7.966 |
  | Journal only | – | 7.966 |
  | Title + Journal | – | 8.445 |
  | Author only | – | 2.788 |
  | PMID role-collision shape | 3.864 | 6.717 |

  ρ_max is now above 6.
- [V] The budget is capped at 16 MiB (`common.schema.json` `maximum: 16777216`). At ρ ≈ 8.45 the observation is about
  135 MiB plus the 1.6 MB intercept, still under `MAX_BLOB_BYTES` (256 MiB), and an overflow would be `BLOB_TOO_LARGE`
  → `STORAGE_ERROR` (fail closed, `controller.py:405-410`). The conclusion very likely holds [I], but the argument and
  the number in bounds.json are wrong for v3. The `lookup.py:17-20` docstring ("the budget and the events are
  unchanged") is true but omits that the observation per budget byte roughly doubled.
- Recommendation: before a freeze, re-run the shape measurement on the actual v3 `observe()` output (not the
  Step 7 design representation), update ρ_bound, the bounds.json row and `budget_max_from_blob_limit`, and say so in
  the docstring.

### E-08 LOW: the D-055 re-proof did not re-derive the evidence item size and count for the new kinds

- [V] `storage_bounds.py` now builds a maximal `cited_bibliography` value. Its maths is right: 134 values, 4,096
  code points, 6 bytes each. But `d055/bounds.py:64` suppresses every `"evidence "` measurement. The maximal evidence
  item still comes from `d053/part_ceiling.json` (`E_max` 27,477, `bounds.py:117`). Measured: the maximal
  `cited_bibliography` item at the code bound with a schema-maximal pointer is **50,412 B**. At the schema bound
  (64 + 64 + 6 values × 4,096 code points, which a crafted journal could hold) it is 3,319,020 B, still under
  `MAX_PART_BYTES`, so "one maximal entry fits a batch" holds.
- [V] `entries_per_run["evidence item"]` = 510,000 is the d053 census. It omits `cited_bibliography` (≤ 20,000 per
  run) and `lookup_record` (one per event of each deciding lookup a D-13a/D-14 claim reaches, `detector.py:343-353`).
- [I] The journal conclusion survives with a wide margin (batch records about 537 B per 8 MiB part; headroom 62×).
  The stated derivation is still incomplete. Recommendation: add both kinds to the item census and `E_max`, and
  regenerate `bounds.json`.

### E-09 LOW: the NORMALIZE candidate-inputs blob has no bounds row, and it now carries per-unit bibliography

- [V] Neither the old nor the new `bounds.json` has a row for the `candidate-inputs` blob (a gap that predates this
  cycle). Since schema 2.0.0 every unit carries `bibliography` (`normalize.py:241`).
- [I] The increment is bounded by the source: the source is ≤ 4 MiB (`wiki/capture.py:35`), `strip_code` drops nested
  templates (no byte counts twice), and JSON costs at most 6 bytes per code point. That gives ≤ about 24 MiB, plus
  20,000 × about 150 B of null fields, so well under 256 MiB. [V] An overflow fails closed (`BLOB_TOO_LARGE`,
  `blobs.py:100-110` → `STORAGE_ERROR`).
- Recommendation: add the row with this argument (and the pre-existing unit, candidate and query terms).

### E-10 LOW: performance (C-07): the role scan is quadratic, bib-1 is linear and computed twice

- [V] Breakdown on `c07_profile.synthetic(n)` (three lookups of n events, D-14):

  | n | `role_ambiguous` | `comparisons` | `decide` |
  | --- | --- | --- | --- |
  | 300 | 0.024 s | 0.014 s | 0.053 s |
  | 1000 | 0.273 s | 0.078 s | 0.364 s |
  | 2000 | 1.029 s | 0.097 s | 1.28 s |

  `role_collided` (`dt1.py:308-320`) scans every event of every lookup. It is called for each attached key of each
  event, and again through `discriminating`, so the cost is O(n·N). `bib.compare` costs about 45 µs per event for
  realistic records. Worst-case titles at the bound are fast because slices run in C: 2,048-word cited title against
  400 / 2,049 / 8,000-word record titles → 10.4 / 2.5 / 4.3 ms. `comparisons` runs in the D-13a guard and again for
  D-13a/D-14 evidence (`dt1.py:472,544,551`), so it is linear and runs twice. bib-1 adds no quadratic term.
- [V] Pinned index: at most 255 events for one original DOI and 281 for one PMID (73,356 events, longest title 392
  characters), so `decide` takes about 0.05 s.
- [I] Within the 16 MiB budget a lookup can hold about 16,000 to 26,000 matched events (651 to 994 stored bytes per
  event, `lookup_budget.json` shapes). Extrapolating the quadratic gives about a minute or more per candidate for a
  future index that concentrates events on one key.
- Recommendation: optimize, because the change is mechanical and safe. Precompute once per `decide` the set of
  `(scheme, key)` whose record carries the same-record flag, which makes `role_collided` O(1). Compute `comparisons`
  once and carry it in `_Ctx`. Gate both with differential tests: the existing dt-2/dt-3 reference oracles plus a
  random-candidate equivalence test against the current implementation. If that is declined, measure and retain:
  commit the `c07_profile.py` output (no result file exists in `final-cycle/` yet) and state the pinned maximum.

### E-11 LOW: bib-1 depends on the C tokenizer but does not pin it

- [V] Stage 03 documents that the pure-Python tokenizer gives different parses from the C one (`source.py:42-45`), and
  its worker switches `mwparserfromhell.parser.use_c` process-wide for crash classification (`worker.py:94-98`).
  bib-1 calls `mwparserfromhell.parse` with whatever tokenizer is active (`bibliographic.py:261`). It records neither
  the tokenizer nor the profile digest: `profile_identity()` (`bibliographic.py:222`) is never called, although spec
  2.2 says the profile "is part of the engine identity".
- [I] On a host without the C extension, or in a process that flipped `use_c`, the same unit could get a different
  cited object, which breaks B1 across hosts. Recommendation: assert `parser.use_c` (or the `CTokenizer` class) in
  `cited_object` and fail closed to `C = ⊥` otherwise, or record it. Either wire `profile_identity()` into the engine
  identity or delete it and reword spec 2.2.

### E-12 INFO: the size bound gives up the description for large real templates (stated in the spec)

- [V] 65 or more `authorN` arguments, or more than 4,096 code points in total, gives `C = ⊥` (probe: 20,000 author
  arguments → `None`). Large collaboration papers on en.wikipedia do list more than 64 authors, so such citations fall
  back to the dt-2 identifier-only decision. That is stated in spec section 9 and is not a material conflict.
  Nothing in the evidence records why a unit has no description (bound exceeded, no single template, other kind).
  Recommendation (optional): record the reason, for auditability.

### E-13 INFO: the secrets and identity scan is clean

- [V] `git diff 6663314 HEAD` added lines contain no `/tmp/claude-0`, `/root/`, `/home/<user>`, `scratchpad`, session
  links, e-mail addresses, tokens (`ghp_`, `github_pat_`, `sk-`, `AKIA`), private-key headers or passwords. The only
  `cmsg_` ids are owner-decision references. The `"path"` values are JSON pointers. `fc_provenance.py` records a
  repo-relative tool path and the index identity only, not its location. The E-05 fail-first log uses `<tmp>`. The
  commits in range carry the environment identity (`Claude <noreply@anthropic.com>`).

## Verdict

No CRITICAL or HIGH. Four MEDIUM findings must be settled before a freeze: E-01 (a surrogate entity fails the whole
NORMALIZE step, against B8), E-03 and E-04 (E-05 redaction leaks in two ways and corrupts output in a third), and E-07
(the D-048 lookup-observation bound is stale for v3, though still under the blob limit and failing closed).
