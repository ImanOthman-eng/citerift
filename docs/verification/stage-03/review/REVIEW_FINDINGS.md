# Stage 03 review findings

Four review perspectives were applied to the engine after the protocol freeze (`afa0115`) and before any holdout
prediction existed, by the implementing agent (not an independent reviewer; the independent evaluation is the
separate evaluator's annotation, `../evaluation/`). Every defect that was fixed has a fail-first case under
`failfirst/`: `RF-nn_case.py` runs the case through the public API or the CLI, `RF-nn_before.json` is its output on
the code before the fix and `RF-nn_after.json` on the fixed code (re-run on the final code and byte-identical). Each
fix also has a regression test in `tests/stage03/`.

| Perspective | Question asked |
|---|---|
| P1 semantic correctness | does every identifier get the role and binding MediaWiki gives it; is any render region attached to the wrong container? |
| P2 observation honesty | can any failure, hidden text or missing evidence turn into "no warning", or anything into a statement about retraction? |
| P3 security and robustness | can input (bundles, records, configurations, network answers) make the tools run unsafely, misreport, or crash? |
| P4 reproducibility, packaging and evaluation integrity | do replay, the wheel, a clean clone and the scorer behave as documented? |

## Findings

| Id | Perspective | Severity | Finding | Disposition | Evidence |
|---|---|---|---|---|---|
| RF-01 | P1 | high | A citation template that repeats `doi=` reported both values as `primary_citation_field`, although MediaWiki uses only the last one: the overridden value was presented as the cited work's DOI. | Fixed (`bb8756b`): the overridden value is `unresolved` with `IDENTIFIER_PARAMETER_OVERRIDDEN`; the last value stays primary. | `failfirst/RF-01_*`; `test_wiki_source_extraction.py` |
| RF-02 | P2 | high | A warning term present only in text the HTML hides (`display:none`) gave `no_recognized_warning_in_inspected_region`: what a reader saw is not evaluated, so this was a failure-to-absence path. | Fixed (`bb8756b`): `ambiguous_text`, evidence kept with `kind: hidden`. | `failfirst/RF-02_*`; `test_wiki_render_ledger.py` |
| RF-03 | P1 | high | When two reference-list items share one DOM id, or two containers point to one note, both containers were `matched` to the same item and container `a` received the text of note "two" (a wrong attachment feeding a marker observation). | Fixed (`bb8756b`): `note_ambiguous` with `RENDER_NOTE_AMBIGUOUS`; no region attached; marker `not_inspected`. | `failfirst/RF-03_*`; `test_wiki_render_ledger.py` |
| RF-04 | P3 | medium | `ExtractConfig` accepted any value: `worker_wall_s=-1`, `worker_memory_mib=true`, `max_nodes="400000"` or `max_depth=0` ran and published an extraction failure (exit 9) that blamed the article instead of refusing the configuration. | Fixed (`93f5ffb`): every value validated; the CLI exits 3 with the reason. | `failfirst/RF-04_*`; `test_wiki_bundle_verify.py::test_invalid_configurations_are_refused` |
| RF-05 | P3 | medium | `replay` of a recorded extraction whose `config` held an unknown key ended in an internal error (exit 1); out-of-range values replayed with them. The schema allowed any numbers in `config`. | Fixed (`93f5ffb`): the schema pins the configuration object; replay reports `BUNDLE_SCHEMA_INVALID` (exit 3). | `failfirst/RF-05_*`; `test_wiki_cli.py` |
| RF-06 | P3 | high | `replay` compared only the recorded `extraction_digest` with the new one, so a recorded document edited after extraction (here a forged normalized DOI) was reported `reproduced` with exit 0. | Fixed (`93f5ffb`): replay checks the record's own digest (`BUNDLE_DIGEST_MISMATCH`, exit 5) and compares whole documents. | `failfirst/RF-06_*`; `test_wiki_bundle_verify.py::test_replay_refuses_forged_mismatched_and_foreign_records` |
| RF-07 | P1 | high | Found by the new reconciliation simulation (`simulations/stage03/reconcile_perturbation_sim.py`): when anonymous footnote markers appear in an order that contradicts the reference list (for example a marker moved between two named anchors), position pairing between anchors linked a use to another reference's marker and its container to the other note, with no issue (11 wrong use links in 60 simulated articles before the fix). | Fixed: a position segment is accepted only when the notes of the first uses it pairs appear in each reference list in source order, also relative to the pairs already accepted (Cite numbers notes by first use); otherwise the segment is abstained or paired by content. 0 wrong links in 200 articles × 5 perturbations after the fix; observed regression digests unchanged. | `failfirst/RF-07_*`; `test_wiki_render_ledger.py::test_wiki_marker_order_against_the_list_numbering_abstains`; simulation test |

## Checked without a defect

- P1: a field anchor covers the parameter value as written, with surrounding whitespace; the Stage 02 normalizer
  records `TRIM_OUTER_WHITESPACE`. This is documented behavior (SPECIFICATION.md 11.4), not a defect; the scorer
  matches identifiers by overlap.
- P3: an unlisted file in a bundle is a warning (`BUNDLE_UNLISTED_FILE`) and does not fail verification: it changes
  no claim of the capture, and it is always reported.
- P3: a 1.8 MB synthetic article with 20 000 named references exceeds the 30 s worker deadline at 256 MiB and the
  memory limit at 64-128 MiB; both end in their stable failure codes. Real articles are within budget
  (`TEST_RESULTS.md`).

## Second review round (2026-10-29, after the session recovery)

Three reviewer agents, each a separate Claude Code subagent with its own context, reviewed the engine at `e9b7cfa`
(the code of `40aaeba` plus tests): P1 (architecture, contracts, scientific semantics), P2 (Arabic/English
extraction, reconciliation, marker honesty) and P3/P4 (adversarial input, failure handling, resources,
reproducibility, packaging). They did not edit the repository, and they were told not to read the evaluation
directory or the holdout captures. They are AI agents in the same session as the implementer: this is separate
review, not independent human review. The implementing agent fixed what they found. No holdout prediction existed
at any point of this round; the fixes were made before the single prediction run of FROZEN_PROTOCOL.md section 9.

Evidence for every finding is in `failfirst/round2/`:

- `p1/`, `p2/`, `p3/`: the reviewers' own reproduction scripts, kept verbatim and renamed to `.py.txt` so the
  repository linter does not apply to them. Run one with `uv run python <file>`. Some insert absolute paths from
  the session scratchpad into `sys.path` (their helper `h.py.txt` sits in the same folder).
- `before/`: each script's output on the code before the fixes (`e9b7cfa`).
- `after/`: the same output on the fixed code. `after/p3-probe_misc.out` and `after/p3-probe_surrogate.out` come from
  copies that run the CLI in the fixed tree; the originals run it in the unmodified tree.

Each fix has a regression test, most in `tests/stage03/test_wiki_review_regressions.py`.

| Id | Reviewer finding | Severity | Defect | Disposition |
|---|---|---|---|---|
| RF-08 | P2-01 | high | Text after a comment, `<link>`, `<style>`, `<meta>` or backlink in a rendered note was never read, so a warning there became "no warning". Real fixtures had dropped tails in 3 notes per article (no marker term in them). | Fixed: the tail of a skipped node is read in its parent's context. |
| RF-09 | P2-02 | high | A standalone citation template's region was the first element of its output, an empty `<link>`, so it was observed as "no warning". | Fixed: every element of the template's output (`about` group) is read; a region with no text is `not_inspected`. |
| RF-10 | P2-05 | medium | A negative was issued although a matched use was not among the note's backlinks, or a parser-limit comment without `about` lay in the region. | Fixed: both give `not_inspected`. |
| RF-11 | P2-03, P2-04 | medium | Wrong target: content pairing ignored an incompatible true partner, and a template's single use was paired by count while the content contradicted it. | Fixed: uniqueness is counted over all sharers; a count pairing must not contradict the URLs or identifiers; otherwise the use abstains. |
| RF-12 | P2-06, P2-07, P2-08, P2-11, plus negation | medium | `مسحوب` matched inside `المسحوبات` ("withdrawals"). "RETRACTED:" was excluded only inside `<cite>`. Evidence offsets shifted after characters that case folding expands. `DISPLAY:NONE` and tab-separated CSS were read as shown. A hidden red link gave `missing_template_link_only`. Format characters and presentation forms hid the term. "was not retracted" was a recognized warning (found while re-running the P2 cases). | Fixed: Arabic matches allow only joined و ف ب ل ك ال and the feminine ending, and other attached letters make the match `ambiguous`. Title prefixes, quotations and negations are `ambiguous`. Folding is mapped character by character (NFKC, Cf removed). Inline CSS is read without case or whitespace. A hidden red link is hidden evidence. |
| RF-13 | P1-01 | high | `{{efn|name=|…}}` twice (Template:Efn always passes `name=`) became one conflicting container. | Fixed: an empty name is no name. |
| RF-14 | P1-02, P1-11 (part) | high | A list-defined `{{efn}}` or `{{#tag:ref}}` was counted as an in-article use. A content-less ref inside a reference list vanished. | Fixed: list-defined refs are never uses; a content-less one gives `LIST_DEFINED_WITHOUT_CONTENT`. |
| RF-15 | P1-06 | medium | Ref names were not read as MediaWiki reads attributes (whitespace runs collapse, trim, then decode). | Fixed (`_decode_attr`). |
| RF-16 | P1-07 | medium | The short-footnote key was the raw text without spaces: "Smith J" and "SmithJ" merged, while `{{sfn}}` and `{{Sfn}}` were split. | Fixed: the key is the canonical template and its parameters as written. |
| RF-17 | P1-05 | medium | RF-01 covered only identifier fields: an overridden `url=` or `id=` still gave `identifier_link`. | Fixed: overridden identifier, URL and id parameters are `unresolved` with `IDENTIFIER_PARAMETER_OVERRIDDEN`. |
| RF-18 | P1-09, P2-09 | medium | Free-text DOI boundaries took in wiki quotes (`'''`). A SICI DOI written with `&lt;` was cut short and reported as `delimited`. Arabic punctuation (، ؛ ؟ ۔) was absorbed without a flag. | Fixed: wiki quotes end the DOI (`ambiguous_markup_or_entity`); characters from entities are text; Arabic and `!?` are flagged as trailing punctuation. |
| RF-19 | P1-10 | medium | The wikilink target was marked as link text and its display text was not; an external link's text was link text only for identifier URLs. | Fixed: both parts of a wikilink and every external link's text are link text (rule 2, `textual_mention`). `[[doi:…]]` interwiki links stay `textual_mention`: the interwiki map was not inspected (limitation). |
| RF-20 | P1-12, P1-13 | low | Invalid percent encoding in a publisher DOI path gave a valid key. A URL's outer whitespace was trimmed with no recorded step, and control characters were stripped too. | Fixed: no normalizer input and no key (`IDENTIFIER_DECODING_FAILED`); only space, tab and line breaks are trimmed, as `URL_OUTER_WHITESPACE_TRIMMED`. |
| RF-21 | P2-10 | low | Bidi marks or typographic spaces in a template name made a supported template unsupported (fails safe). | Fixed: MediaWiki's title whitespace and bidi stripping. |
| RF-22 | P1-03 | high | `DOI_PATH_TRAILING_SEGMENT_AMBIGUOUS` was not in the schema enum, so every extraction holding it failed verification. | Fixed: the schema lists every step the code emits; a test verifies such an extraction. |
| RF-23 | P1-04 | medium | `verify` did not check role consistency or normalization: a re-digested record with a promoted marker DOI or a forged key verified. | Fixed: verify checks necessary role conditions and re-runs the Stage 02 normalizer on every recorded input (full re-derivation remains `replay`). |
| RF-24 | P3-04, P3-05 | medium | An asctime Retry-After was unreadable, so the client retried on its own backoff, earlier than asked. A huge value crashed the capture (`OverflowError`). | Fixed: zone-less dates are UTC (RFC 9110); values beyond one year are `RETRY_AFTER_OUT_OF_RANGE`; an unusable Retry-After stops the operation instead of guessing. |
| RF-25 | P3-03 | medium | Retry-After on the last attempt was dropped (`not_before` empty), and the next process did not wait for it. | Fixed: `ATTEMPTS_EXHAUSTED` keeps `not_before`; the network gate records the not-before time and defers later captures. |
| RF-26 | P3-06, P3-07 | medium | `1e400` became infinity in strict JSON. A lone surrogate crashed verify and replay (exit 1). | Fixed: non-finite numbers and lone surrogates are refused (`BUNDLE_MALFORMED`, exit 3). |
| RF-27 | P3-08 | low | Data after the gzip member was ignored. | Fixed: `RESPONSE_DECOMPRESSION_FAILED`. |
| RF-28 | P3-01 | medium | A body sent one byte at a time was not bounded by the operation deadline (`read(65536)` waits to fill), so it held the network gate. | Fixed: `read1` and a per-read socket timeout of the time left; a local drip server ends in `HTTP_TIMEOUT` within the deadline. |
| RF-29 | P3-11 | low | `capture` made its requests before refusing an existing `--out`. | Fixed: the path is checked first. |
| RF-30 | P3-10 | low | The worker's network ban did not cover the C-level `_socket` type. | Fixed for `_socket.socket`, `sendto`, `sendmsg` and `getaddrinfo`. Stated as an in-process guard, not a sandbox. |
| RF-31 | P3-02 | medium | HTML nested beyond libxml2's depth limit was cut silently, and the render was still "complete". | Fixed: a fatal parser error makes the render unreadable (`failed`, markers `unavailable`). |
| RF-32 | P3-13 | low | A capture whose render was edited to "not requested" still verified while the render attempt stayed recorded. | Fixed: render attempts without a render request fail verification. |
| RF-33 | P3-09 | low | `rename(2)` could replace an empty directory that appeared at the target during publication. | Fixed on Linux with `renameat2(RENAME_NOREPLACE)`; the parent directory is fsynced. Elsewhere the existence check leaves a short race (RISK_ANALYSIS.md). |
| RF-34 | P3-12 | low | `replay` without `--extraction` exited 0 for a partial extraction. | Fixed: the exit code is the new extraction's (complete 0, partial 6). |
| RF-35 | P1-11 (part) | medium | DOIs inside a ref name or another site's URL had no disposition, and the old test asserted that. | Fixed: excluded with reasons `ref_attribute` and `other_site_url`; the test now asserts the dispositions. |

Not fixed, with reasons:

- P1-08 (low): `{{efn|group=foo}}` keeps a group the template may map to its default. The template sources were
  not retained in the calibration evidence (only their hashes), so the accepted group lists cannot be verified.
  The group is kept as written. This is a known limitation in HANDOFF.md.
- P2, suspected and not reproduced: identical source templates are paired with identical render output in document
  order. The content is identical by construction, so no wrong text is attached; marker neighbours are not used.
- P3, suspected: `verify` parses the retained HTML in the CLI process, without the worker's limits. Measured cost
  2.3 s and +243 MiB for a 15.4 MiB synthetic render, bounded by the 16 MiB size limit. Documented in
  RISK_ANALYSIS.md.
- P3, suspected: the worker could exit exactly at the deadline (`ProcessLookupError` from `killpg`). Guarded.
- P3, design note: the `prop=info` redirect flag is not cross-checked against redirect-word detection. Redirect
  pages are refused by the source answer's redirect state; the flag is not used. Documented.
- P1, design note: the extraction digest covers the capture record's own SHA-256, so two captures with identical
  artifacts have different extraction digests. This is intended: an extraction is bound to one capture record.
  SPECIFICATION.md section 9 states it.

## Repair round after holdout run 1 (FROZEN_PROTOCOL.md section 9)

Holdout run 1 (`../evaluation/run-1/`, engine of `d626c06`) failed two gates on adjudicated labels. Both failures
trace to one defect each, where the engine differed from the frozen annotation guide. This is the protocol's one
permitted repair round. The repaired engine is evaluated once on the confirmation articles (positions 17-22),
annotated and locked before its predictions. Run 1 stays published as the holdout result and is not called fresh.

| Id | Found by | Severity | Defect | Disposition | Evidence |
|---|---|---|---|---|---|
| RF-36 | holdout run 1, gate G3a (arwiki, 2 promotions); also the observed enwiki challenge (1) | high | A resolver or PubMed URL (or `{{doi}}`/`{{PMID}}` wrapper) outside any reference was given `identifier_link`, a cited-work role. Cases: a bare PubMed URL on an External links line, and a URL in `{{Update inline|reason=…}}`. SPECIFICATION.md 11.5 rule 5 said "a URL or wrapper elsewhere", while the frozen guide limits `identifier_link` to a reference or citation template. | Fixed: outside a reference container (note, list-defined note, generated note, bibliography entry) such a link is `textual_mention`. `verify` checks that an `identifier_link` lies in a reference or a citation template. | `failfirst/repair1/RF-36-37_*`; `test_wiki_identifier_links_outside_references_are_mentions` |
| RF-37 | holdout run 1, gates G5c/G5d (enwiki unit precision 0.941, recall 0.949) | medium | `{{cite iucn}}` and `{{cite simbad}}` are citation templates by the guide's definition ("Cite …") but are not in profile v1. They were counted as unstructured text, and their `doi=` was `unresolved`. | Fixed: a template whose canonical name starts with "Cite " or "استشهاد ب" and that the profile does not list is a citation template of family `unlisted`. The name prefix includes the space, so `{{Citation needed}}` is not one. Templates of other names that format citations (`{{Who's Who}}`, `{{NRDB species}}`, `{{IUCN2008}}`) stay unsupported (partial support, HANDOFF.md). | `failfirst/repair1/RF-36-37_*`; `test_wiki_unlisted_cite_templates_are_citation_templates` |

Not repaired from run 1, and documented:

- **DOIs in publisher URLs whose path is not `/doi/`** (`/article/10.…`, `/content/journals/10.…`). These are 4
  missed identifiers. The engine has no reliable boundary rule for them. Identifier recall was 0.97 in both
  languages.
- **A note whose body is not a citation** ("Originally: …") is reported as an unstructured unit. Telling a
  citation from an explanatory note needs a semantic judgement, which is out of scope.
- **Observed challenge article ar-74891699.** An unbalanced `{{FixBunching}}` begin/end pair makes Parsoid wrap
  the whole body as one template's output. The engine abstains on all 12 render links rather than pair source
  prose with template output. This is a coverage loss with no wrong attachment.
- **An empty `pmid=` field** is reported as an identifier occurrence with `normalization.missing = true`. The
  guide does not count it. It is kept so that a missing value stays visible.

| Id | Found by | Severity | Defect | Disposition | Evidence |
|---|---|---|---|---|---|
| RF-38 | the confirmation capture (`confirmation/ar-4823675` exited 1, internal error) | high (capture) | The RF-28 read loop lowered the socket timeout before every read. After `read1` had taken the last byte of a body with a Content-Length, `http.client` closed the connection, and the next `settimeout` raised `EBADF`. The capture failed with an internal error instead of finishing, so it was introduced by the RF-28 fix itself. Extraction is not affected (no extraction digest changes). | Fixed: the loop ends when the response has closed its connection and never sets a timeout on a closed socket. The confirmation capture was stopped at the first occurrence and resumed after the fix. The bounded retry pass treats an attempt that ended in a client internal error as transient. | `test_wiki_a_complete_body_with_content_length_reads_to_the_end` (fails before: `OSError: [Errno 9] Bad file descriptor` at `fetch.py:573`); `../evaluation/confirmation/capture/capture_notes.txt` |

## External review findings F1-F4 (owner directive 2026-10-29, section 4)

A separate ChatGPT/Codex review session found F1-F4 by running synthetic capture bundles through the public isolated
extraction API at the reviewed head. They are synthetic failures, not observed live-Wikipedia occurrences.

- **Reproduction at `049c48c`:** `failfirst/f1-f4/F1-F4_case.py.txt`, output `F1-F4_before.json`.
- **After the fixes:** `F1-F4_after.json`.
- **Regression module:** `tests/stage03/test_wiki_f1_f4.py`, 91 tests. Its results at the revisions before each fix
  are in `failfirst/f1-f4/tests_at_62ffe3f.txt` (before all four fixes: 76 fail, and every test that passes is a
  control) and `failfirst/f1-f4/tests_at_fa877d9.txt` (after F4, before F1-F3: 49 fail).
- **Real data:** on the 54 retained real bundles (933 marker observations, old data used for regression only), the
  F1-F3 change alters no marker state and no evidence kind, channel or matched text
  (`failfirst/f1-f4/real-bundles/`). Only the added evidence fields and therefore the extraction digests change.

| Id | External id | Severity | Defect | Disposition | Evidence |
|---|---|---|---|---|---|
| RF-39 | F1 | high (fabricated negative) | `region_text` joined every text fragment with a space, so `<span>Re</span>tracted`, `Re<!--x-->tracted`, `<span>مس</span>حوب` and `مس<!--x-->حوب` were matched as two words and observed as `no_recognized_warning_in_inspected_region`. | Fixed at the root: the region text is rebuilt in channels that keep real inline adjacency and whitespace. Block elements and `<br>` are hard boundaries; content of another channel, a backlink, a marker link or an unknown element is a soft boundary, across which a match is only ambiguous (`interrupted`). Exclusions (negation, quotation, title prefix, English word boundaries, Arabic attached letters) apply to the rebuilt text. Every evidence item now carries the locator of its element. | `test_wiki_region_text_keeps_inline_adjacency`, `test_wiki_formatting_only_changes_keep_the_observation`, `test_wiki_evidence_names_its_element` |
| RF-40 | F2 | high (fabricated negative) | Every `<a class="new">` was dropped from the text and kept only as a "red link" title, so an ordinary red link labelled `Retracted` or `مسحوب` vanished. A main-namespace title such as `Retracted` was also taken for the marker template. | Fixed: a link is classified by its target (Parsoid's `./Title` href, else the title attribute). Only a template-namespace page of a profile marker template is a marker link: red links give `missing_template_link`, blue ones ambiguous `template_page_link`, and hidden ones hidden evidence. Every other link's label is text in its own channel, and evidence inside a link records the target, the basis and whether the link is red. The schema's evidence `part` enum now lists `hidden_redlink`, which the code already emitted. | `test_wiki_link_labels_keep_their_channel`, `test_wiki_link_evidence_is_inspectable` |
| RF-41 | F3 | high (hidden text as a shown warning) | Hiding was evaluated from the region element downwards only. A reference list inside `<div style="display:none">` gave `recognized_warning_text` with `hidden_elements: 0`. | Fixed: the supported hiding rules are inherited from every ancestor, also outside the region, for notes and template-output (bibliography) regions. The evidence records the hiding element and rule (`hidden_basis`), and `browser_visibility` stays `not_evaluated`. | `test_wiki_hidden_ancestors_hide_the_region` (ancestor, grand-ancestor, self and descendant, with `display:none`, `visibility:hidden`, `hidden` and a hidden class), `test_wiki_visible_ancestors_are_controls`, `test_wiki_hidden_bibliography_output_is_hidden` |
| RF-42 | F4 | high (lost use) | `_generated_ref` took the reuse names only from unnamed arguments, so `{{r|1=a}}` and `{{استشهاد متعدد|1=a}}` produced no reuse and no issue. | Fixed at the root: `effective_arguments` resolves arguments as MediaWiki's preprocessor does (implicit numbering, trimmed explicit keys, last value wins). The names follow the retained template sources: enwiki Module:R and arwiki's wikitext template with its 9-name limit and nested `#if`. Replaced, unread and missing names are reported (`REUSE_ARGUMENT_REPLACED`, `REUSE_NAME_NOT_USED`, `REUSE_NAME_MISSING`), as is note content the template adds (`REUSE_CONTENT_UNSUPPORTED`). Names with markup are unbindable. | `test_wiki_explicitly_numbered_reuse_is_the_same_use`, `test_wiki_reuse_names_follow_numeric_order`, `test_wiki_a_replaced_reuse_argument_creates_no_phantom_use`, `test_wiki_reuse_names_the_template_does_not_read`, `test_wiki_reuse_without_a_first_name`, `test_wiki_reuse_groups`, `test_wiki_reuse_content_and_markup_have_dispositions`, `test_wiki_rendered_reuse_is_equivalent_for_both_numberings`; template sources in `failfirst/f1-f4/template-sources/` |
| RF-43 | F4 (the check it asked for) | medium (split note) | The short-footnote key put unnamed arguments in a positional list and named ones in a sorted list, so `{{sfn|Smith|2001}}` and `{{sfn|1=Smith|2=2001}}` became two notes, although Module:Footnotes receives the same arguments. A replaced argument was also counted twice. | Fixed: the key is built from the effective arguments. Calls with different effective arguments stay different notes. | `test_wiki_short_footnote_key_uses_effective_arguments` (fails at `62ffe3f`) |

## Integration review R3 of the F1-F4 repairs (RF-44 to RF-55)

A separate reviewer agent reviewed `049c48c..d11112c` (`round-3/R3_REPORT.md`, with its repro scripts in
`round-3/repro/`).

- **Regressions:** each fix below has a regression in `tests/stage03/test_wiki_f1_f4.py`.
- **Real data:** on the 54 retained real bundles (933 observations), these fixes change no marker state and no
  evidence kind, channel or matched text. Two snippets of the observed English fixture now include the citation
  text before them, and its pinned digest was updated.

| Id | Review id | Severity | Defect | Disposition | Regression |
|---|---|---|---|---|---|
| RF-44 | R3-01 | high (fabricated negative) | Shown text and the citation's text were matched in separate channels, so a term split across the `<cite>` boundary was found in neither: `Re<cite>tracted</cite>` was a negative. | Fixed: one shown channel holds both, each character labelled `text` or `cite`. A match is `text` only when every character is; a match partly inside the citation is ambiguous (`spans_citation`). | `test_wiki_region_text_review_r3` |
| RF-45 | R3-02 | medium (warning without a word) | Word boundaries and exclusions ignored the neighbouring text of the other channel (`<cite>Un</cite>retracted`, a negation or a title colon inside the citation). An excluded marker-link label touching a word (`…>Un</a>retracted`) was invisible to matching. | Fixed: boundaries and exclusions read the single shown channel. Where visible but excluded content (a marker link, a backlink, an unknown element) touches a word with no space, the position is an edge, and a match starting or ending there is ambiguous (`interrupted`). | `test_wiki_region_text_review_r3` |
| RF-46 | R3-03 | medium (fabricated negative) | Any element with class `mw-cite-backlink` was dropped, and editors can set that class. | Fixed: only Parsoid's backlink is left out, the span that is a direct child of the note's list item and holds `mw:referencedBy` links. | `test_wiki_region_text_review_r3` |
| RF-47 | R3-04 | low | `<q>` renders quotation marks, but its content was read unquoted. | Fixed: `<q>` contributes its quotation marks to the text, so the quotation exclusion applies. | `test_wiki_region_text_review_r3` |
| RF-48 | R3-05 | medium (verification) | `verify` accepted forged marker evidence: hidden turned shown, evidence without a locator, an ordinary link presented as a missing marker template, and a state not following from its evidence. | Fixed: the schema requires a locator. Verify now also checks: a term item's quote in the channel its part names (`text` labels for a `text` item); the term pattern against the quote; for a link item, the label, target, marker-template target and red/blue against its part; hiding against hidden parts; kind against part; and the state against its evidence. Omitted evidence is still only detectable by `replay`, as documented. | `test_wiki_verify_rejects_forged_marker_evidence` |
| RF-49 | R3-06 | medium (silent loss) | Module:R's postscript and content-id parameters put text into the note, but were not reported. | Fixed: they are included in `REUSE_CONTENT_UNSUPPORTED`. | `test_wiki_reuse_postscript_and_content_id_are_note_text` |
| RF-50 | R3-07 | low-medium (split note) | A comment inside a short-footnote argument split one note into two. | Fixed: the key drops comments, as the preprocessor does. Blank arguments and parameter aliases (`p` / `page`) still give different keys: Module:Footnotes is not retained, so they are kept apart. This is conservative: two containers for one rendered note can abstain, but cannot attach a use to another work. | `test_wiki_short_footnote_key_ignores_comments` |
| RF-51 | R3-08 | low (wrong binding) | Reuse names and argument keys were trimmed of Unicode whitespace. MediaWiki and Module:Arguments trim ASCII only. | Fixed: they are trimmed of ASCII whitespace only, so a no-break space stays part of a name, as in `<ref name>`. | `test_wiki_reuse_names_keep_a_no_break_space` |
| RF-52 | R3-09 | medium (resources) | Matching, exclusion context, locators and verify were quadratic in the matches of a region. A 41 kB note with 4,000 matches took 82 s, past the 30 s worker deadline. | Fixed: one text build per channel, sorted boundaries with bisection, one quotation sweep per text, a bounded context window for negations and attached letters, a locator cache, and per-element caches in verify. The same note now takes 0.4 s to extract and 0.8 s to verify; 4,000 words split by hidden text take 0.7 s and 1.0 s; a 480 kB note with 4,000 negated matches takes 1.7 s and 1.2 s. | `test_wiki_region_text_cost_is_linear` |
| RF-53 | R3-10 | low | A U+2029 in the text was taken for the block-boundary marker. | Fixed: every Unicode space in the text, U+2029 included, is a space; only block boundaries write U+2029. | `test_wiki_region_text_review_r3` |
| RF-54 | R3 S-3 (outside the diff) | medium (unfounded negative) | A citation template standing in running text is a container with only the template's output as its region. Text after it on the same rendered line (`{{cite journal …}} Retracted.`) was never inspected, yet the observation said "no recognized warning". | Fixed conservatively: when letters or digits follow the template's output on its rendered line, a would-be negative is `not_inspected`. None of the 54 real bundles has such a container (all 59 bibliography entries there are list items). | `test_wiki_standalone_citation_in_running_text` |

The remaining suspected items are dispositioned, not repaired:

- **S-1, CSS comments inside an inline style.** MediaWiki's Sanitizer normalizes inline CSS before Parsoid writes
  it, so such a style cannot reach the captured HTML. `visibility:collapse` is outside the declared rules.
- **S-2, `<noscript>`.** Wikitext cannot produce it.
- **S-4.** A line break between "Expression of" and "concern" separates the words, as the specification requires.
- **S-5, entity-encoded reuse names: repaired as RF-55.** A reuse template's names reach Cite as attributes of
  `#tag` (arwiki) or `frame:extensionTag` (Module:R). Per MediaWiki core's `CoreParserFunctions::tagObj` and
  Scribunto, which this repository does not retain, those attributes are not entity-decoded, while
  `<ref name="…">` is. Decoding reuse names could therefore bind a use the wiki does not bind. Reuse names now keep
  entities literally, and arwiki's `#tag` path drops one pair of enclosing quotes, as `tagObj` does. Regression:
  `test_wiki_reuse_names_are_not_entity_decoded`.
- **S-6, short-footnote parameter aliases.** As RF-50: they are kept apart, which is conservative.

## Findings from the final-campaign adjudication (2026-11-02, post-exposure)

The final campaign's articles are exposed. Each item below was found from an adjudicated disagreement. Every
repair here is a **post-exposure** repair: the retained articles serve as regression data only, and the frozen
evaluation result stays as published (`../evaluation/final/adjudication/README.md`).

| Id | Source | Severity | Finding | Disposition | Evidence |
|---|---|---|---|---|---|
| RF-60 | final campaign, en-1377523963 (adjudication confirmed the locked key) | medium (wrong normalized key; gate G2) | A publisher DOI URL ending in a page-view route (`…/doi/10.1111/0004-5608.00043/abstract`) kept the route in the normalizer input. It got the key `10.1111/0004-5608.00043/abstract` and was only flagged `IDENTIFIER_BOUNDARY_AMBIGUOUS`. Root cause: `identifiers.decode` decided not to decide the boundary, but still passed the undecided text on as the key. The guide (3.5) defines the key as the DOI of the `/doi/` path segment. The same entry's `{{Doi}}` confirms the boundary. | **Fixed** (post-exposure). See the note below the table. | `failfirst/rf-60/` (`pytest-before-d151507.txt`: 11 failed and 6 controls passed; `pytest-after.txt`: 17 passed; `real_bundles_impact.json`); `tests/stage03/test_wiki_rf60_page_view_segment.py` |
| — | final campaign, ar-75574746 and en-1374633449 (12 `definition_extra`) | none in code; a guide ambiguity | The engine records each repeated identical `{{sfn}}` call as a definition of one container (SPECIFICATION 11.2: "identical sfn-family calls form one note"). Both final adjudicators read guide 3.2 (identical calls bind to the first) and confirmed that the later calls are not definitions. The run-1 adjudicator read guide 3.1 ("a short-footnote template call" is a definition) and added such calls as definitions (`../evaluation/annotations/adjudication_decisions/en-1380771007.json`). Uses, bindings and render links of these calls are all correct (G4 and G6 pass in both languages). | **Not changed.** The engine follows the specification and the earlier adjudicated reading. Changing it now would be post-exposure tuning toward one of two conflicting adjudications. The frozen G5a failure (ar 0.914) stands. The guide ambiguity goes to the owner. | `../evaluation/final/adjudication/decisions/ar-75574746.json`, `en-1374633449.json` |
| — | final campaign, ar-76553307, en-1351525729, en-1372000829 (3 `identifier_missed`) | low (recall; declared support boundary) | A DOI written in a publisher URL path without `/doi/` (iopscience `/article/10.…`, Springer `/10.…`) is not an identifier occurrence for the engine. In all three references, the same DOI is also found in the template's `doi=` field. | **Not changed.** These URLs are outside the frozen support matrix ("Publisher URLs with a `/doi/10.…` path"). A host-independent rule for arbitrary `/10.` paths would add uncertain boundaries (`…/68/pdf`). Recorded as a limitation. | `../evaluation/final/adjudication/decisions/` |
| — | final campaign, ar-73367172, en-1374633449 (unit and role items) | low (declared partial support) | Citation templates the profile does not list, including EI2, EI3, `The History of al-Tabari`, `Slaves on Horses`, `قاموس دورلاند` and `من سمى هذا`, are reported as unstructured units. Their DOIs get role `unresolved`. | **Not changed.** The frozen matrix declares templates the profile does not know as partial, role `unresolved`. Adding these names now would tune the profile to exposed articles. Recorded as a limitation. Both unit gates and G3b pass. | same |
| — | final campaign, en-1381749944 (1 `use_missed`) | none in code; a guide ambiguity | The guide counts a list-defined `<ref>` as a use, but the specification does not (11.2). | **Not changed.** Recorded as a limitation. | same |

**RF-60 fix.** One recognized page-view segment at the end of a publisher `/doi/` path (abstract, full, pdf,
epdf, references, suppinfo, citedby, figures, summary, meta) is removed from the normalizer input, but only when
what remains is still a DOI (`10.` + 4-9 digits + `/` + suffix). The removal is recorded as the new structural step
`PAGE_VIEW_SEGMENT_REMOVED`. The occurrence keeps `DOI_PATH_TRAILING_SEGMENT_AMBIGUOUS` and the
`IDENTIFIER_BOUNDARY_AMBIGUOUS` issue. Only one segment is removed. Resolver URLs, template fields and wrapper
arguments are unchanged.

**Alternatives considered for RF-60:**
- *Withhold the key* (abstain): never wrong, but it loses the lookup in the common case.
- *Keep the old behavior*: always wrong for page routes.
- *Corroborate with another identifier of the same reference*: more code, and no gain over the shape check for the
  observed cases.

The chosen rule is the smallest that gives the guide's key. Its remaining risk is a real DOI whose last suffix
segment is exactly one of those words; such a DOI would lose that segment, but its occurrence stays flagged
ambiguous.

**Impact on the 70 retained real bundles** (exposed, regression only; extraction at `d151507` and after the fix,
same bundles): only en-1377523963 changes. Its Wiley occurrence now has key `10.1111/0004-5608.00043`. Both
occurrences of that key link to both rendered links. The warning `UNIT_BOUNDARY_UNRESOLVED` ("more than one
distinct value for doi") disappears.

## Integration review R5 of RF-60 (2026-11-02)

A separate reviewer agent (a fresh Claude Code context; it did not write RF-60) reviewed `c3e54ae..949cdc4` on its
integration paths. Its report and repro scripts are in `round-5/` (`REVIEW.md`, `repro/*.py.txt`). It found nothing
material. Its own focused runs passed; it did not run the full suite.

| Id | Severity | Finding | Introduced by | Disposition |
|---|---|---|---|---|
| RV-1 | minor | Route words were matched case-insensitively across Unicode (`abſtract`, `suppınfo`). | RF-60 | **Fixed:** ASCII-only matching (`(?ai)`). |
| RV-2 | minor | `$` matched before a final line feed, so `…/abstract%0A` lost the line feed silently. | RF-60 | **Fixed:** anchored with `\Z`. |
| RV-3 | minor | A route is removed even when the same unit's `doi=` field states the longer DOI. The two keys then differ and `CO_REPORTED_IDENTIFIERS` is reported (status partial). | RF-60 | **Not changed.** The disagreement is reported, not hidden. A DOI whose real suffix ends in a route word was not observed in the 70 retained real bundles. Recorded as residual risk R-03-RF60 in RISK_ANALYSIS.md. |
| RV-4 | minor (recall) | A route URL and a `doi=` field of the same work in another reference now share a key. Content pairing that used them as unique keys abstains (`RECONCILIATION_ABSTAINED`). | RF-60 | **Not changed.** This is a conservative abstention: the reviewer could not build a wrong attachment, and no such case occurs in the retained real bundles. Recorded with RV-3. |
| RV-5 | minor | The schema enum gained a value without a version change. Documents made after RF-60 fail against the pre-RF-60 external schema copy. | RF-60 | **Not changed.** Stage 03 has no released or accepted contract version, and earlier Stage 03 schema repairs (for example `d11112c`) kept 1.0.0. Pre-RF-60 documents validate under the new schema. The installed-wheel smoke test is rerun with the current schemas (TEST_RESULTS.md). |
| RV-6 | minor | The specification and the docstring did not describe the rule. | RF-60 | **Fixed:** SPECIFICATION.md 11.4 and the `identifiers.py` docstring. |
| RV-7 | informational | The removal was tested after percent-decoding, so `%2Fabstract` and `/%61bstract` were removed. Degenerate remainders (`…//abstract`, `/./abstract`) were accepted. | RF-60 | **Fixed:** the route must be written literally in the raw path. The remainder must be a DOI whose last segment is not empty, `.` or `..`. Encoded forms stay flagged ambiguous. |
| RV-8 | informational | `/abstract/`, `/abstract%20` and `;jsessionid` kept the route in the key with no ambiguity flag. | pre-existing | **Partly fixed:** a final `/` after the route is accepted. `%20` and `;jsessionid` forms are recorded as a limitation. |
| RV-9 | minor | `verify` accepts a forged, re-digested `normalizer_input`, including step combinations the decoder cannot produce. `replay` detects every case. | pre-existing | **Not changed.** SPECIFICATION 14 states that verify does not re-derive identifiers; `replay` is the complete check. Recorded as a known limitation. |
| RV-10 | minor | A lookalike path such as `/doı/10.…` was accepted as a publisher DOI URL. | pre-existing | **Fixed** with RV-1: ASCII-only `/doi/` matching for source and render URLs. |

**Regressions** (`tests/stage03/test_wiki_rf60_page_view_segment.py`):
- At `949cdc4`, before these fixes, the 10 new cases fail and 17 pass (`round-5/pytest-before-949cdc4.txt`).
- After the fixes, all 27 pass.

**Real bundles:** on the same 70 retained real bundles, the R5 fixes change no extraction compared with `949cdc4`.

## Adversarial integration review R6 under D-034 (2026-11-02)

Owner instruction D-034, section 9, asks for one independent adversarial integration review after the fixes and
before the study. A separate reviewer agent (a fresh Claude Code context on Sonnet; it wrote none of the code under
review) reviewed candidate `5b1dcb0` (`eca4389..5b1dcb0`: short-footnote identity, DOI D-1/D-2, Retry-After G-1/G-2,
the capture driver, the confirmation tools, scorer v2). It made no network request. Its report, repro scripts and
logs are in `round-6/` (`REVIEW.md`, `repro/*.py.txt`). During the review the MF-1 change (`b00fa65`) was being
made in the same working tree; the reviewer noted it (RR-13) and its runs partly saw it.

It reports 13 findings: 0 critical, 2 high, 2 medium, 5 low, 4 informational. I reran every repro at `b00fa65`
before any fix (`round-6/repro-output-before-b00fa65/`); each reproduced as reported.

| Id | Severity | Finding | Disposition |
|---|---|---|---|
| RR-1 | high | The driver and the draw charged every finished run without recorded attempts the full worst case, including runs the network gate deferred without any request. 14 gate deferrals reached a phantom 300 MiB ceiling. | **Fixed.** A run with a reported capture record is charged what it records, zero included. Only a run without a reported record (crash, unreadable output) or without an `end` line is charged the worst case. |
| RR-2 | high | A draw request deferred by a server's Retry-After counted as a failed `list=random` batch at once; one long wait emptied a wiki's frame and SELECTION.json was then written. | **Fixed.** A deferred request waits until `not_before` + 1 s and is sent again. A wait over 3600 s stops the draw before SELECTION.json is written. A retryable failure is sent once more; an unreadable Retry-After is never retried. The draw holds the driver lock. |
| RR-3 | medium | A 429 whose Retry-After was unreadable or out of range was rerun by the driver after the 10 s gate interval. | **Fixed.** Such a run is final; the state records `retry_after_problems`. |
| RR-4 | medium | A journal line torn by a kill made every later driver start raise `JSONDecodeError`. | **Fixed.** Readers ignore a final line without its line end. The driver (and the draw), holding the lock, move it to `captures.jsonl.torn-at-<offset>` before the next append. A malformed complete line stays an error. |
| RR-5 | low | The short-footnote content key compared template spellings: redirects of one template (`sfn`/`sf`, `sfnp`/`sfnb`, arwiki `Sfn`/`Sf`) gave a false `conflicting_definitions`, and `ref=a b` vs `ref=a_b` too. | **Fixed.** The content key uses the profile entry of the template (one entry holds a template and its redirects) and `ref=` as a link target (spaces and underscores alike). `sfn` vs `sfnp` and different `ref=` targets stay conflicts. `ignore-err=` is **not changed**: its effect depends on whether the target exists, which the source does not show. |
| RR-6 | low | A capture published by the CLI before the driver was killed (before the `end` line) was captured again. | **Fixed.** Recovery adopts the published bundle's own capture record (the CLI publishes by atomic rename) and journals it as a recovered `end`. The reviewer's repro writes a placeholder `capture.json` of `{}`, which is not a capture record and is still not adopted; the unit test uses a real record shape. |
| RR-7 | low | `reserve_step.decide` counted an unresolved (pending) article as 0 and named the next block; a planned but never-run block looked captured. | **Fixed.** Unresolved or partly run blocks stop the decision. A block counts as captured only once its articles have runs. After a ceiling or the acquisition time limit, every article keeps its state, and no further block is named. |
| RR-8 | low | `run_holdout.py` silently left a captured article without a label in its single lock directory out of the scoring spec. | **Fixed for this campaign** with a new tool, `confirmation-2026-11/scripts/run_confirmation.py`. It takes every lock directory, refuses a captured article without a locked label or an unresolved capture, and writes one `gate` split (holdout and included reserves) and a separate challenge spec. `run_holdout.py` is **not changed**: it produced earlier committed evidence. |
| RR-9 | low | `warning_challenge.marker_calls` missed `{{Template:...}}` (capital, and any `Template:` on arwiki). | **Fixed.** The namespace prefix is matched case-insensitively, and `Template:` is accepted on both wikis. |
| RR-10 | info | The gate record was replaced by truncate-then-write; an empty or partial record imposed no wait. | **Fixed.** The record is written first and the file is then cut to its length. A non-empty record that is not one complete line of one or two numbers now imposes the full interval. An empty file is still "no record yet" (the initial state). |
| RR-11 | info | Positional values were trimmed with the PHP set (with NUL); the reviewer said Lua's trim keeps `\v`. | **Partly confirmed.** Lua's `%s` includes `\v` (`round-6/reference-sources/`), so `Smith\v` and `Smith` are one name in MediaWiki too; the reviewer's expectation was wrong for `\v`. NUL is the real difference: positional values are now trimmed with the Lua set (no NUL); named values keep the PHP-and-Lua set. |
| RR-12 | info | `RUN_WORST_BYTES` (20.06 MiB) was below what one run can accept (2 x 32 MiB). | **Fixed.** `RUN_WORST_BYTES` = 64 MiB; a test ties both worst cases to `FetchPolicy`. |
| RR-13 | info | The working tree was not the candidate; the acquisition time limit was enforced by no tool; an interrupted draw was not resumable and its request numbers restarted. | **Fixed** where it is a tool defect: the driver exits 5 and the draw stops at 2026-11-14 23:59 UTC; draw request numbers continue after an interrupted draw, and SELECTION.json lists the earlier requests. The candidate identity is handled by freezing a committed revision before the draw (MANIFEST.json). |

**Two existing tests of mine had fixtures in the old shape** (both added under D-034, not part of accepted
evidence). `test_the_ceiling_stops_before_a_run_that_could_cross_it` now gives its synthetic `end` line a `status`,
so that it is a reported record; its assertions are unchanged. `test_the_reserve_step_adds_the_next_block_from_locked_counts_only`
now gives each article a resolved run, as the driver records it; its assertions are unchanged.

**Regressions** (`tests/stage03/test_review_r6_fixes.py`, 38 cases):
- At `b00fa65`, before the fixes, 29 fail and 9 pass (`round-6/pytest-before-b00fa65.txt`). The 9 that pass are
  controls whose behaviour must not change (two conflicts that stay conflicts, an `قالب:` marker call, `Smith\v`
  trimmed as Lua trims it, an empty gate file, a malformed complete journal line, an interrupted run without a
  bundle) and the two RR-8 cases, which test the new tool.
- After the fixes, all 38 pass.

**Simulation.** `simulations/stage03/campaign_driver_sim.py` now also draws gate deferrals without requests,
unreadable Retry-After answers, kills after a published bundle and torn journal lines, and checks C8 (a torn line
never stops a restart and is kept), C9 (no run after the acquisition time limit) and C10 (no rerun after an
unreadable Retry-After). With seed 20261102, 300 sequences: 0 failures. The same simulation on the `b00fa65`
driver stops with `JSONDecodeError` at the first torn line (`round-6/sim-before-b00fa65.txt`).

**Real bundles:** on the 70 retained real bundles, the R6 fixes change no extraction compared with `b00fa65`
(`round-6/real_bundles_impact.json`).

## Focused follow-up review R7 under D-034 (2026-11-02)

Owner instruction D-034, section 9, allows one second focused review, only of the changes since the first. A separate
reviewer agent (a fresh context on Sonnet) reviewed `5b1dcb0..0dfef1c` (MF-1 in `b00fa65` and the R6 fixes in
`0dfef1c`) in its own detached worktree at `0dfef1c`, with no network request. Its report, repro scripts and outputs
are in `round-7/`. It reports 8 findings: 0 critical, 0 high, 2 medium, 4 low, 2 informational. It confirmed the R6
fixes for charging, adoption, the draw wait loop, the reserve step, the prediction run, the gate record, the
short-footnote keys, the time limit and the marker regex, and that the two changed fixtures kept their assertions.

| Id | Severity | Finding | Disposition |
|---|---|---|---|
| RF7-1 | medium | MF-1's pure-Python tokenizer keeps `:` `;` `!` inside a bare URL followed by a space, so `https://doi.org/10.1234/abc; Smith` gave DOI `10.1234/abc;`, marked valid. The equivalence claim held only for the retained corpus (fuzz: 53 of 30,000 strings differ). | **Fixed (MF-1 v2).** The engine keeps the C tokenizer. A native crash of the worker is classified by a second run with the Python tokenizer under the same limits; that run's output is never an extraction (`failfirst/mf-1/BEFORE_AND_AFTER.md`, last section). |
| RF7-2 | low | The Python tokenizer is 10 to 150 times slower on unclosed constructs: an 18 KB page went from 1.4 s to `EXTRACTION_DEADLINE_EXCEEDED`. | **Fixed** with RF7-1: 1.5 s again (`round-7/repro-output-after/rf_tok_deadline.out.txt`). A crashing page now takes up to two worker runs. |
| RF7-3 | medium | The R6 commit also rewrote the model rule of amendment section 7 (to evaluators on Sonnet and adjudicators on Opus, the implementing agent's own model), without listing it in section 11 or citing the owner. | **Fixed.** The edit is withdrawn. Section 7 again requires three distinct models, as committed in `5b1dcb0`, now named: implementing agent Opus, evaluators Sonnet, adjudicators Haiku (available without paid credits; checked by a one-line call before any draw). The smaller adjudicator model is reported as a limitation. Section 12 records the correction. The reviewer's reading that the implementing agent runs on Sonnet came from its own context; this session runs on Opus. |
| RF7-4 | low | `_journal` split lines with `str.splitlines()`, so U+0085, U+2028 or U+2029 inside a journal string crashed every restart. | **Fixed.** Only `\n` ends a line. |
| RF7-5 | low | Torn-line repair dropped a whole final JSON line missing only its `\n` (losing a deferral's `not_before`), and discarded a second tear at the same offset. | **Fixed.** A whole final object is completed; every torn tail goes to a new numbered side file. |
| RF7-6 | low | `retry_after_problems` was read from every attempt, so an odd header on an accepted source response ended retries of an unrelated render failure. | **Fixed.** Only the last attempt of each operation, when it failed, counts. |
| RF7-7 | info | Four unreported or interrupted runs (64 MiB each at the worst case) exhaust the 300 MiB ceiling with no real use. | **Not changed.** It follows the protocol (an interrupted run at its worst case) and RR-12. Recorded as a campaign risk. |
| RF7-8 | info (speculative) | SELECTION.json was written non-atomically. | **Fixed.** Written atomically. |

**Effect on an R6 test.** With the C tokenizer, a NUL in a source makes the parse lossy (`SOURCE_PARSE_LOSSY`), so the
R6 NUL case (RR-11) can no longer reach the trim. That test of mine now asserts the honest failure and that the
positional trim set has no NUL. The `MF-1` test that asserted the Python tokenizer was replaced by one that asserts
the C tokenizer, with new tests for the bare-URL punctuation and the crash classification. The existing memory test
`test_the_memory_limit_ends_in_a_stable_failure` is unchanged and passes.

**Regressions** (`tests/stage03/test_review_r7_fixes.py` and `tests/stage03/test_wiki_mf1_tokenizer.py`, 18 cases):
- At `0dfef1c`, before these fixes, 13 fail and 5 pass (`round-7/pytest-before-0dfef1c.txt`). The 5 that pass are
  `.`/`,` punctuation (the same with both tokenizers), the memory test, and two classification controls.
- After the fixes, all 18 pass.

**Real bundles:** on the 70 retained real bundles, no extraction changes compared with `0dfef1c`
(`round-7/real_bundles_impact.json`). The reviewer found the same for 83 bundles between `5b1dcb0` and `0dfef1c`.

This was the one focused follow-up review the instruction allows. No further code review is made before the study;
the evidence-integrity audit follows the study.

## Findings under D-034 outside the reviews, and from the confirmation campaign (2026-11-02 to 2026-11-03)

The audits of owner instruction sections 4 and 5 found four engine defects before the freeze. Each was reproduced
before its fix and is described with its tests in the audit named.

| Id | Severity | Finding | Disposition |
|---|---|---|---|
| D-1 | medium | An HTML character reference in a bare URL inside a template field (`url=…&amp;…`) stayed in the DOI key. | **Fixed** in `8753448` (`design/doi-boundaries/AUDIT.md`). |
| D-2 | medium | A `%2F` separator in a publisher `/doi/` path gave no identifier. | **Fixed** in `8753448` (same audit). |
| G-1 | medium | An attempt interrupted by a killed process left no record, so the next process could send a request inside the minimum interval. | **Fixed** in `7c2b260`: a provisional record on acquire (`design/retry-after/AUDIT.md`). |
| G-2 | low | The HTTP-date reader accepted unknown or missing zones and trailing text, guessing a wait. | **Fixed** in `7c2b260`: strict forms, anything else `RETRY_AFTER_UNREADABLE`. |

Found during the campaign, after the freeze (`../evaluation/confirmation-2026-11/campaign/REPORT.md` section 6):

| Id | Severity | Finding | Disposition |
|---|---|---|---|
| CF-1 | medium (evaluation tool) | The frozen `disagreements_v2.py` raised RecursionError on a challenge split: its replacement of `evaluate.load_bundle` was called again through `warning_challenge.load`. | The frozen file is unchanged. A wrapper (`../evaluation/confirmation-2026-11/scripts/disagreements_challenge_fix.py`) binds the challenge loader to the original function. `tests/stage03/test_disagreements_challenge_fix.py`: the frozen function recurses; the wrapper lists the challenge split; on the gate split it equals the frozen output (also checked on the campaign data). No engine code involved. |
| CF-2 | low (campaign tool) | `make_packets.py` resolved the repository root one level too high, and would have given reserve blocks the challenge window and tag. | Fixed before any packet was built; the reserve windows were checked to equal the frozen window. |
| CF-3 | specification divergence | English G5c fails (0.869): SPECIFICATION 11.3 makes every definition without a template unit `unstructured_text`, while the guide gives `unstructured` only to a plain-text citation. 19 definitions (Harvard short-citation links, explanatory notes, two unlisted citation-like templates) differ. | **Not changed.** No repair after the prediction run (amendment section 8). Reported as the campaign's failure; the owner decides (`../evaluation/confirmation-2026-11/DECISION_RECORD.md`). |
