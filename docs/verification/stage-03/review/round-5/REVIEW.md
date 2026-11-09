# Adversarial integration review: Stage 03 RF-60 (commit 949cdc4)

Reviewer: independent. I did not write the change.
Scope: `git diff c3e54ae 949cdc4 -- src schemas tests`. The change edits `identifiers.decode`, the schema enum and one new test file.
Repository: `/home/user/citerift` (branch `claude/beautiful-planck-fm0pya`, HEAD 741a8de). No `src`, `schemas` or `tests` changes after 949cdc4.
Nothing in the repository was modified. All repro scripts are in `/home/user/stage03-review/` and run from the repo root with:

```
cd /home/user/citerift && uv run python -I /home/user/stage03-review/<script>.py
```

Baselines marked "before" switch RF-60 off in the same process: `identifiers._DOI_SHAPE` is replaced by a regex that never matches, so the code behaves as it did at c3e54ae.

## Verdict

I found **no material defect**.
- RF-60 does not change roles, markers, accounting totals or the Stage 02 normalizer.
- Source and render keys agree on every input I tried.
- Extraction is deterministic, and enwiki and arwiki behave the same.

I did reproduce several **minor** defects that RF-60 introduces:
- RV-1 and RV-2: the removal fires on inputs it should not touch (Unicode case variants, a trailing line feed).
- RV-3: the removal ignores the same unit's own `doi=` field. The result is a wrong key plus a new false `CO_REPORTED_IDENTIFIERS`.
- RV-4: correct content pairings now abstain.
- RV-5 and RV-6: version and spec gaps.

The verify weakness asked about in Q3 is **pre-existing, not new** (RV-9). Replay detects the forgery.

---

## Confirmed defects (reproduced)

### RV-1: Route words match non-ASCII case variants, and the segment is removed from the key (minor, introduced by RF-60)

`_VIEW_SEGMENT` uses `(?i)` on `str` patterns. In Python that means Unicode case-insensitive matching:
- `s` matches U+017F (LATIN SMALL LETTER LONG S);
- `i` matches U+0131 (dotless i) and U+0130 (I with dot above).

Before RF-60 this match only added the ambiguity flag. Now it rewrites the key. The module's own rule is "no Unicode normalization, structural steps never repair an identifier". This removal is a Unicode repair.

Repro: `r2_unicode_casefold.py`

```
'abſtract'   non-ascii=['LATIN SMALL LETTER LONG S']
   key='10.1002/abc.123' steps=[..., 'DOI_PATH_TRAILING_SEGMENT_AMBIGUOUS', 'PAGE_VIEW_SEGMENT_REMOVED']
   Stage 02 key of the unremoved text: '10.1002/abc.123/abſtract'
'suppınfo'   non-ascii=['LATIN SMALL LETTER DOTLESS I']   key='10.1002/abc.123' ... PAGE_VIEW_SEGMENT_REMOVED
'suppİnfo'   non-ascii=['LATIN CAPITAL LETTER I WITH DOT ABOVE']  key='10.1002/abc.123' ...
'cıtedby', 'fıgures', 'ſummary', 'referenceſ'  -> all removed, key '10.1002/abc.123'
```

Suggested minimal fix: compile `_VIEW_SEGMENT` with `re.IGNORECASE | re.ASCII` (`(?ai)`). Add one regression test that uses U+017F.

### RV-2: `$` also matches before a final line feed, so a decoded `%0A` is cut away with the route and no step records it (minor, introduced by RF-60)

`_VIEW_SEGMENT` ends in `$`. `decode` percent-decodes the publisher path once, so `…/abstract%0A` becomes `…/abstract\n`. The regex matches before the `\n`, and `value[:view.start()]` drops both the route and the LF. No step names the LF. `%20`, `%09` and `%0D` are not treated this way, so the behaviour is inconsistent.

Repro: `r6_dollar_newline.py`

```
before '%0A' in='10.1002/abc.123/abstract\n' key='10.1002/abc.123/abstract' steps=[..., 'DOI_PATH_TRAILING_SEGMENT_AMBIGUOUS']
after  '%0A' in='10.1002/abc.123'            key='10.1002/abc.123'          steps=[..., 'PAGE_VIEW_SEGMENT_REMOVED']
after  '%20' in='10.1002/abc.123/abstract '  key='10.1002/abc.123/abstract' steps=['PUBLISHER_URL_DOI_PATH', 'PERCENT_DECODED_ONCE']
```

Suggested minimal fix: end the pattern with `\Z` instead of `$`.

### RV-3: The removal ignores corroboration in the same unit, which gives a wrong URL key and a new false `CO_REPORTED_IDENTIFIERS` (minor, introduced by RF-60)

Take a DOI whose real suffix ends in a route word. When the citation template's own `doi=` field gives the full value, the URL occurrence still loses the last segment. The template then appears to report two different DOIs, and the status becomes `partial`.

A bare URL of the same kind gets a different, well-formed key, for example `10.1080/1` from `…/doi/10.1080/1/full`. That key could match an unrelated real DOI in any key-based lookup downstream.

The occurrence keeps `IDENTIFIER_BOUNDARY_AMBIGUOUS`. REVIEW_FINDINGS documents that a real DOI can lose a segment. It does not mention:
- the contradiction with the same unit's own field;
- the new co-report warning that follows.

Repro: `r3_integration.py`. The results are identical for `en` and `ar`.

```
== [en] field+url same text (suffix ends in /references)
   id-00001 doi primary_citation_field template_field key= 10.1080/1/2/references steps= []
   id-00002 doi identifier_link url key= 10.1080/1/2 steps= [..., 'PAGE_VIEW_SEGMENT_REMOVED']
   issue CO_REPORTED_IDENTIFIERS ['un-00001'] more than one distinct value for doi
== [en] bare url only, real DOI ends /full
   id-00001 doi identifier_link url key= 10.1080/1 ...
```

Before RF-60, both occurrences in the first case had the key `10.1080/1/2/references`, and no co-report was raised.

Suggested minimal fix, in `model.py` after decoding. When a `PAGE_VIEW_SEGMENT_REMOVED` occurrence shares its unit with a field or wrapper occurrence whose key equals the Stage 02 key of the unremoved text, keep the unremoved input. One way is to call `decode` again with removal disabled, or to add a `keep_route` flag. Record it as a step, for example `PAGE_VIEW_SEGMENT_KEPT_CORROBORATED`.

If adding code here is unwanted, at least document this case in REVIEW_FINDINGS or the spec as a known effect.

### RV-4: Content pairing now abstains where it used to pair correctly (minor, conservative; introduced by RF-60)

`Reconciler._source_urls` and `note_hrefs` include `id:doi:<key>`. RF-60 gives a route URL and a `doi=` field of the same work in *another* reference the same key. In a segment that position alignment cannot pair (here two source uses and three render uses), the uniqueness rule in `_content_pair` then sees two candidates. Both uses abstain, although before RF-60 they paired correctly by unique URL or unique identifier. The witnesses fall back to `region_not_reconciled`.

This is a loss of recall, not a wrong attachment. Uniqueness on both sides prevented a mispairing in every variant I built.

Repro: `r5_render_pairing.py`. The results are identical for `en` and `ar`.

```
before: us-00001 matched basis=unique_url_in_reference_text; us-00002 matched basis=unique_identifier_in_reference_text
        id-00001 render_link_found; id-00002 render_link_found
after : us-00001 abstained; us-00002 abstained; issues += RECONCILIATION_ABSTAINED
        id-00001 region_not_reconciled; id-00002 region_not_reconciled
```

Suggested fix (optional): in `_content_pair`, decide by raw-URL keys first and fall back to `id:` keys only for uses that are still unpaired. Otherwise, accept this as a conservative effect and note it in REVIEW_FINDINGS. Its "70 bundles, only one changes" statement covers only the retained bundles.

### RV-5: Schema content changed under the same id and `schema_version` 1.0.0, so external pre-RF-60 schema copies reject new documents (minor, introduced by RF-60)

The `structural_steps` enum is closed. An installed wheel validates against `CITERIFT_SCHEMAS`, a directory the operator copies. With the retained pre-RF-60 copy (`docs/verification/stage-03/current-checks/wheel-smoke-final/schemas`), a document produced after RF-60 fails verification with `BUNDLE_SCHEMA_INVALID`. Both documents carry `schema_version 1.0.0`.

The extractor identity (`citerift-wiki 1.0.0`, profile and parsers) is also unchanged. Replaying a pre-RF-60 record of such a bundle therefore reports `REPLAY_DIFFERS` rather than `REPLAY_IDENTITY_MISMATCH`. Earlier RF fixes followed the same practice of not bumping the version.

Repro: `r7_external_schemas.py`

```
# repo schemas
route URL  schema_version=1.0.0 status=partial verified=True issues=[]
# CITERIFT_SCHEMAS=.../wheel-smoke-final/schemas
route URL  schema_version=1.0.0 status=partial verified=False issues=[('BUNDLE_SCHEMA_INVALID', "schema extraction: /identifiers/0/decoding: {... 'PAGE_VIEW_SEGMENT_REMOVED' ...")]
plain URL  schema_version=1.0.0 status=partial verified=True issues=[]
```

Old documents still validate under the new schema, because the enum only grew.

Suggested fix: do at least one of the following.
- Bump the extraction `schema_version`, and preferably the engine version, so that new documents identify their rules.
- State in the spec that this is an additive v1 change, and that external schema directories must be refreshed. The retained wheel-smoke copy is historical evidence and should stay as it is.

### RV-6: Spec and module docstring not updated (minor, introduced by RF-60)

`SPECIFICATION.md` 11.4 lists the structural decoding steps: comments, entities, protocol-relative completion, query/fragment removal, and the publisher DOI path percent-decoded once. Route removal is not in that list.

The 949cdc4 diff does not touch the spec. The `identifiers.py` module docstring still says "Structural steps never repair an identifier: no punctuation trimming". The rule is described only in REVIEW_FINDINGS.

Check: `grep -n "PAGE_VIEW\|page-view" docs/verification/stage-03/SPECIFICATION.md` returns nothing.

Suggested fix: add one sentence to 11.4 that gives the 10 ASCII words, the one-segment limit, the DOI-shape condition, the recorded step and the kept ambiguity issue. Adjust the docstring to match.

### RV-7: Percent-encoded separators and degenerate remainders are accepted (informational, introduced by RF-60)

The removal is tested *after* the path is percent-decoded once.
- An encoded slash (`abc.123%2Fabstract`) is treated as a route separator. A server route is never written that way, so `%2F` is evidence that the segment belongs to the DOI.
- An encoded route word (`%61bstract`, `ab%73tract`) is removed as well.
- `_DOI_SHAPE` (`10\.[0-9]{4,9}/.+`) accepts degenerate remainders: `…/10.1002/abc.123//abstract` gives the key `10.1002/abc.123/`, and `…/10.1002/./abstract` gives the key `10.1002/.`.

Source and render keys stay consistent in all of these cases.

Repro: `r1_decode_matrix.py`

```
'.../doi/10.1002/abc.123%2Fabstract'  in='10.1002/abc.123' ... 'PERCENT_DECODED_ONCE', ..., 'PAGE_VIEW_SEGMENT_REMOVED'
'.../doi/10.1002/abc.123//abstract'   in='10.1002/abc.123/' key='10.1002/abc.123/' ... 'PAGE_VIEW_SEGMENT_REMOVED'
'.../doi/10.1002/./abstract'          in='10.1002/.' key='10.1002/.' ... 'PAGE_VIEW_SEGMENT_REMOVED'
```

Suggested fix:
- Look for the route segment in the raw path (`m.group(1)`), with a literal `/` separator, before percent-decoding.
- Require that the remainder does not end in `/`.

---

## Pre-existing (not introduced by RF-60)

### RV-8: The route rule covers only some forms (informational, pre-existing)

The following forms keep the route in the key and are not flagged ambiguous:
- `…/abstract/` (trailing slash);
- `…/abstract%20` (the Stage 02 normalizer trims the decoded space and returns the key `…/abstract`);
- `…/abstract;jsessionid=…`.

RF-60 makes the gap more visible, because the plain form is now repaired and these forms are not.

Repro: `r1_decode_matrix.py` and `r6_dollar_newline.py`.

### RV-9: verify accepts a forged, re-digested document with a changed `normalizer_input`; replay detects it (minor, pre-existing; RF-60 adds no new weakness)

`verify._semantics` checks only `normalization == normalize(normalizer_input)`. It never relates `normalizer_input` or `structural_steps` to the anchored `raw`. The schema accepts any combination from the step vocabulary, including combinations the decoder cannot produce. Examples are `PAGE_VIEW_SEGMENT_REMOVED` without `PUBLISHER_URL_DOI_PATH`, on a PMID, or twice.

The same forgery already worked before RF-60, with no step or with `PERCENT_DECODED_ONCE`. `replay` re-derives the identifiers and reports `differs` in every case. SPECIFICATION 14 states that verify does not re-derive identifier claims.

Repro: `r4_forged_verify.py`. The results are identical for `en` and `ar`.

```
[en] genuine                                                      verified=True  replay=reproduced
[en] RF-60 step kept, input -> other DOI 10.1111/evil             verified=True  replay=differs
[en] pre-existing: plain URL, input -> other DOI, no step         verified=True  replay=differs
[en] pre-existing: claim PERCENT_DECODED_ONCE + other DOI         verified=True  replay=differs
[en] impossible: PAGE_VIEW_SEGMENT_REMOVED alone on a plain URL   verified=True  replay=differs
[en] impossible: PAGE_VIEW_SEGMENT_REMOVED on a PMID field        verified=True  replay=differs
schema problems for duplicated/PMID PAGE_VIEW step: []
```

Suggested hardening, outside RF-60. For each identifier, verify could re-run `identifiers.decode(scheme, origin, <raw after the recorded input_steps>, input_steps)` and compare the result with the recorded `decoding`. This is cheap and deterministic.

### RV-10: The `/doi/` path regex is Unicode case-insensitive, so a homoglyph path counts as a publisher DOI URL (informational, pre-existing)

`https://example.org/doı/10.1002/abc.123`, written with a dotless i, returns `url_scheme == "doi"` and gets the key `10.1002/abc.123`. The cause is the same as RV-1, and the fix is the same: `(?ai)` on `_DOI_PATH` and `_PUBLISHER_DOI_PATH`.

Repro: the last lines of `r6_dollar_newline.py`.

---

## Checked with no defect found

- **Stage 02 normalizer.** `git diff c3e54ae 949cdc4 -- src/citerift/retraction` is empty. `normalize_doi` and `normalize_pmid` are called unchanged.
- **Roles and markers.**
  - `_role` is computed from the candidate before `decode`, so RF-60 cannot promote an occurrence to a cited-work role.
  - Markers do not depend on identifier keys. No negative warning marker is created or changed. The retained bundle en-1377523963 (page 37174434) still has `no_recognized_warning_in_inspected_region` for all 19 containers.
- **Accounting.** No occurrence is added or removed, and verify's accounting checks pass on new documents (`r4`, genuine row).
- **Source and render keys.** `decode` and `decode_render_href` gave the same key on all 34 inputs in `r1_decode_matrix.py`. The inputs covered:
  - uppercase routes, query and fragment, protocol-relative URLs, `/doi/abs/…/abstract` and `/doi/reader/…/pdf`;
  - Arabic suffixes, RLM, ZWSP and NUL;
  - fullwidth `ＰＤＦ` (not removed, which is correct);
  - resolver hosts with a trailing dot, a port or userinfo.

  Resolver URLs (`doi.org`) and template fields are unchanged.
- **Witnesses.** Witness pairing stays scoped to the region. The field and the URL of one unit now witness each other's links, which is intended. No witness attached across references.
- **Determinism and languages.**
  - Replay of a fresh extraction gives `reproduced` for both enwiki and arwiki (`r4`, genuine rows).
  - All integration repros give identical results for `en` and `ar`.
  - `[0-9]` in the patterns is ASCII-only, so Arabic-Indic digits are never treated as a DOI prefix.
- **Existing tests.** The commit adds only `tests/stage03/test_wiki_rf60_page_view_segment.py`, and no existing test file changed. The focused run passed:

  ```
  uv run pytest -q -p no:cacheprovider tests/stage03/test_wiki_rf60_page_view_segment.py tests/stage03/test_wiki_source_extraction.py
  45 passed in 0.42s
  ```

  One gap remains, and it predates RF-60: `test_wiki_publisher_doi_path_with_ambiguous_trailing_segment` still does not assert the key of the route URL.

## Suspicion (not reproduced)

Content pairing can now pair a route-URL source use by its `id:doi:` key with a render use that shows the same DOI from somewhere else. One example is a template-generated note when the true partner has no links. Before RF-60 such a use abstained. Pairing a `doi=` field use already carried the same risk, so RF-60 extends an existing risk rather than creating a new class. I could not build a case that mispairs, because the uniqueness check on both sides blocked every variant I tried.
