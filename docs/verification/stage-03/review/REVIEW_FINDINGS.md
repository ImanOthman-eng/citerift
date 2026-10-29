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
