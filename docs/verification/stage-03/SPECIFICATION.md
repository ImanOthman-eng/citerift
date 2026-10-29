# Stage 03 specification: Wikipedia Extraction Engine (`citerift.wiki`, engine 1.0.0)

Owner directive: `cmsg_018VCB51nDHP6HXmLU4ea5yPJCa6mkaQhr3oirPxgVDQbS` (copy in
`authorization/OWNER_DIRECTIVE_2026-10-28.md`). This is the final specification of what is implemented. It
supersedes `design/INITIAL_SPECIFICATION.md` (kept as the pre-calibration record). The support matrix, splits,
metrics and gates are frozen in `protocol/FROZEN_PROTOCOL.md` and are not repeated here. Section numbers 8-15 are
cited from the module docstrings in `src/citerift/wiki/`.

## 1. Product

A deterministic, article-first extractor for **arwiki and enwiki**, namespace 0, main-slot wikitext. For one pinned
revision it produces:

- the saved source revision (ids, SHA-1, size, content model, text) and, separately identified, a render capture of
  the same revision (Parsoid HTML);
- reference containers (one per footnote, list-defined note, generated note or bibliography entry) with every
  definition, and every use of each container;
- citation units (citation templates, external-data templates, unstructured reference text);
- every DOI and PMID occurrence, raw and normalized through the Stage 02 normalizers, with a markup role and the rule
  that gave it;
- exact source anchors (code point and UTF-8 byte intervals, raw text and its SHA-256) and DOM locators in the render;
- source/render reconciliation states (`matched`, `source_only`, `render_only`, `ambiguous`/`abstained`,
  `unavailable`), render-only uses and identifiers, and marker observations of each rendered reference;
- an exception ledger, structured issues with stable codes, component states, accounting checks, and a digest of the
  whole document, so that the result can be verified and replayed offline.

Stage 03 does **not** decide whether any work is retracted. It never states "not retracted"; a marker observation
says only what the captured HTML of one region shows (R-029, R-031). End-to-end retraction matching is Stage 04.

## 2. Out of scope

Wikipedia editing; other wikis, namespaces, slots or content models; fetching any publisher, DOI resolver or
PubMed page; executing retained HTML or scripts; browser visibility (CSS, skins, gadgets); following short-footnote
chains to bibliography entries; subreferences; the retraction index (no Stage 02 query, policy, advisory or local
model module is imported, and no SQLite index is opened).

## 3. Support matrix

`protocol/FROZEN_PROTOCOL.md` section 2 (full, partial, unsupported per construct and language). The profile
`src/citerift/wiki/data/profile-v1.json` (version 1.0.0, digest `ba5ae18b…c3a697`) holds every language-specific
name: 28 citation-template families with English and Arabic names and redirects, external-data templates,
generated-reference templates (`efn`, `refn`, `ملا`, `r`, `sfn` family), wrappers, identifier and URL parameters,
reference-list templates, marker templates, warning and ambiguous terms, redirect words and namespace prefixes. Its
provenance (inspected template pages) is `calibration/profile-v1.provenance.json`.

## 4. Modules

| Module | Role |
|---|---|
| `fetch.py` | the only network path: two fixed hosts, retry plan, limits, cross-process network gate (8) |
| `capture.py` | source query and render request for one revision; identity checks; bundle publication (8) |
| `bundle.py`, `canonical.py` | bundle layout, atomic publication, path safety, canonical JSON and digests (9) |
| `source.py`, `textmap.py` | lossless wikitext traversal; code point to byte offsets (11, 12.1) |
| `model.py`, `identifiers.py` | containers, uses, units, identifier occurrences, roles; Stage 02 adapter (10, 11) |
| `render.py`, `reconcile.py` | Parsoid HTML reading and DOM locators; source/render joins (12) |
| `markers.py` | marker observations (13) |
| `extract.py`, `worker.py` | document assembly; isolated worker with limits and no network (10, 16) |
| `verify.py` | offline verification and replay (14) |
| `cli.py` | `citerift-wiki` (15) |
| `issues.py` | catalog of 102 stable issue codes with severity and retryability (10) |
| `schemas.py` | validation against `schemas/wiki/v1` and the accepted `schemas/contracts/v1` common definitions |

## 5. Python API (`citerift.wiki`)

| Function | Network | Result |
|---|---|---|
| `capture_revision(CaptureRequest, FetchPolicy=None, *, out=None)` | yes, the only one | `CaptureOutcome(status, record, bundle, issues)`; status `complete`, `partial`, `deferred` or `failed` |
| `extract_bundle(bundle, ExtractConfig=None, *, isolated=True)` | no | extraction document (schema `urn:citerift:schema:wiki:v1:extraction`) |
| `verify_bundle(bundle, extraction=None)` | no | verification report (schema `…:verification`), `verified` true only without error issues |
| `replay_bundle(bundle, pinned_config=None, recorded=None)` | no | verification report with `replay.state` `reproduced`, `differs`, `not_compared` or `failed` |

A failure is always a document with `status: failed` and an error issue, never an exception and never an empty
result.

## 6. Dependencies

Runtime additions (locked in `uv.lock`): `mwparserfromhell` 0.7.2 (wikitext) and `lxml` 6.1.3 with libxml2 2.14.6
(HTML), qualified against selectolax 1.0.2 in `calibration/parser_qualification.json` (D-029). Existing:
`jsonschema` and the Stage 02 identifier normalizers. Python 3.12 and 3.13.

## 7. Decisions

D-029 (stack and render source: Core REST `/w/rest.php/v1/revision/{id}/html`, Parsoid HTML 2.x) and D-030 (frozen
evaluation protocol and gates 03-A to 03-K), both delegated engineering decisions recorded in `DECISIONS.md`.

## 8. Network and capture

### 8.1 Policy (`FetchPolicy`, frozen values)

One request in flight; at least 10 s between the end of one attempt and the start of the next; at most 3 attempts
per operation; 30 s per attempt; a global capture deadline of 180 s; `maxlag=5` on every Action API request;
`Retry-After` (delta seconds or HTTP date) honored and never shortened, otherwise backoff 10 s × 2^(n−1); when the
next allowed attempt would start after the deadline the operation ends `DEFERRED_RETRY_AFTER` with `not_before`
(with Retry-After) or `DEADLINE_EXCEEDED`. 403, 404, 3xx and other unexpected statuses are final and never retried;
429, 502-504 and other 5xx, timeouts, connection failures, `maxlag` and `ratelimited` API errors, incomplete bodies
and unparseable JSON are retried. Bodies are streamed with a 32 MiB wire limit and a 32 MiB decompressed limit
(gzip only), and `Content-Length` must match. Only `https://ar.wikipedia.org` and `https://en.wikipedia.org`
without port, credentials or fragment are requested; redirects are refused. A fixed User-Agent names the project.
No proxy rotation, no identity change, no 403 bypass. The retry decision is the pure function `plan_next`.

### 8.2 Network gate

With the default transport every attempt holds an exclusive `flock` on one file (`CITERIFT_WIKI_NETWORK_LOCK`,
default `~/.cache/citerift/wiki-network.lock`, opened with `O_NOFOLLOW`), which stores the wall-clock end of the last
attempt of any process; the minimum interval therefore holds across processes and captures. A gate that cannot be
had before the deadline ends `NETWORK_GATE_BUSY`; a platform without `fcntl` or an unusable lock file ends
`NETWORK_GATE_UNAVAILABLE` (fail closed).

### 8.3 Source identity

One Action API `query` (`prop=revisions|info`, `rvslots=main`, by title, page id or revision id) must name exactly
one page in namespace 0, the requested page id or revision id, a main slot with content model `wikitext`, visible
text, and text whose SHA-1 and byte size equal the revision's. A redirect page is refused unless `--follow-redirect`
was given (then exactly one hop). Source text above 4 MiB is refused.

### 8.4 Render identity

The render of exactly that revision id is requested. It is accepted only when it is UTF-8, at most 16 MiB, of
Parsoid HTML profile 2.x, and every revision statement it makes (`Content-Revision-Id` header, the document's
`about` revision) equals the source revision, with the same page id, namespace 0 and the same revision SHA-1
(`mw:revisionSHA1`, base 36). A render that states no revision at all is not accepted
(`RENDER_REVISION_UNCHECKED`). A rejected or failed render leaves the capture `partial` with the source kept and the
reason recorded; render and source are never joined across revisions.

## 9. Bundles and canonical form

A bundle is a directory with `capture.json` (schema `…:capture`) and `artifacts/<sha256>` for every retained body
(source text, the source answer, the render, failure bodies up to 64 KiB). Paths are never derived from titles. A
bundle is written in a fresh temporary directory beside its target and renamed into place; an existing target is
never replaced. Reading refuses symbolic links anywhere (bundle, `capture.json`, `artifacts`, each artifact),
artifact names that are not 64 lowercase hex digits, artifacts that do not hash to their name, and duplicate keys,
NaN or infinity in any JSON. Files the record does not list are reported (`BUNDLE_UNLISTED_FILE`, warning).
Canonical JSON: UTF-8, sorted keys, no insignificant whitespace, non-ASCII kept; a digest is the SHA-256 of the
canonical form of the object without its digest field.

## 10. Extraction document

Fields: `extractor` (name, version, profile version and digest, parser versions, normalizer), `config` and
`config_digest`, `capture` (bundle digest, page, revision, SHA-1, artifacts, render state), `status`,
`components` (source, render, reconciliation, markers, each with a state), `containers`, `uses`, `units`,
`identifiers`, `excluded_identifiers`, `markers`, `render_only` (uses and identifiers), `exceptions` (the ledger),
`issues`, `accounting` and `extraction_digest`. Every issue has a code from the catalog, a severity, the affected
entity ids and a detail. `status` is `complete` when every requested component completed, `partial` when the source
completed and some other component did not (for example no render requested or the render rejected), `failed`
otherwise. The accounting checks (each with left and right counts) are: candidates = identifiers + excluded; the
identifiers by role sum to the identifiers; one marker observation per container; every unit in exactly one
container; no source span reported twice for one scheme.

## 11. Source extraction

### 11.1 Traversal

mwparserfromhell parses the slot text and `str(tree) == text` is required (`SOURCE_PARSE_LOSSY` otherwise). Every
node's interval is computed from its parent's with the serialization formula of its node type and checked against
the text before use; a boundary that fails the check is reported (`ANCHOR_NOT_EXACT`) and never used as an exact
anchor. No global text search locates anything.

### 11.2 Containers, definitions and uses

A `<ref>` with a body defines; `<ref name=… />` uses; a ref name binds within its group only (name and group compared
after trimming and entity decoding). Definitions in `<references>` or a reference-list template's `refs=` are
`list_defined_note` and are not uses. Identical definitions give `identical_definitions`; differing ones
`conflicting_definitions` and no body is chosen. A named use without a definition is `definition_missing`
(`REF_DEFINITION_MISSING`). `efn`/`refn`/`ملا` with content are `generated_note`s with the profile's default group;
`{{r|a|b}}` is one use per name; identical `sfn`-family calls form one note. A list item or standalone citation
template outside footnotes is a `bibliography_entry`.

Template arguments are read as MediaWiki's preprocessor builds them. Unnamed arguments are numbered 1, 2, … among
unnamed arguments only. A named argument's key is its trimmed name, so `1=` is position 1 and `01=` is not. A
repeated key keeps its last value.

The names of a reuse template follow its retained source (`review/failfirst/f1-f4/template-sources/`):

- **enwiki `{{r}}` (Module:R).** The first name is the first non-blank of `name1`, `name`, `n1`, `n`, `1`. Name k is
  the first non-blank of `namek`, `nk`, `k`, and the names stop at the first k without one. The group is `group`,
  `grp` or `g`.
- **arwiki `{{استشهاد متعدد}}`.** The names are `1`, then `2`…`9` while each is non-blank; an absent `1` is the text
  `{{{1}}}`. The group is `group`.

Names and argument keys are trimmed of ASCII whitespace only, as PHP `trim` and Module:Arguments do. Names keep
character references literally: they reach Cite as attributes of `#tag` or `frame:extensionTag`, which are not
entity-decoded, unlike `<ref name="…">`. The `#tag` path also drops one pair of enclosing quotes. Implicit and
explicit numbering therefore give the same uses. Every replaced, unread or missing name argument is
reported: `REUSE_ARGUMENT_REPLACED`, `REUSE_NAME_NOT_USED`, `REUSE_NAME_MISSING`. Note text added through Module:R's
content parameters (reference, annotation, postscript and content id), or `style=sub`, is reported as
`REUSE_CONTENT_UNSUPPORTED`. A short-footnote call is keyed by its effective arguments, with comments removed, so
`{{sfn|Smith|2001}}` and `{{sfn|1=Smith|2=2001}}` form one note.

Refs in `<gallery>`, `<poem>`, `<imagemap>` and subreferences are reported, not extracted.

### 11.3 Citation units

A template whose canonical name is a profile citation family, or (RF-37) a name the profile does not list that
starts with "Cite " or "استشهاد ب" (family `unlisted`), is a `citation_template` unit; `Cite Q` and
`استشهاد بويكي بيانات` are `external_data_template` units; a definition with no template unit is
`unstructured_text`. Parameter names are compared after trimming; a repeated parameter is recorded in
`duplicate_params`.

### 11.4 Identifier occurrences

Candidates: identifier fields of templates (`doi`, `DOI`, `دوي`, `biorxiv`, `medrxiv`, `pmid`, `PMID`), wrapper
arguments (`{{doi}}`, `{{دوي}}`, `{{PMID}}`), resolver and PubMed URLs (in parameters, external links and free text),
publisher URLs with a `/doi/10.…` path, labelled text (`doi:`, `دوي:`, `PMID`), and DOIs in free text. A free-text
DOI is `10.` + 4-9 digits (optionally subdivided) + `/` and ends at the first whitespace or wikitext delimiter;
trailing sentence punctuation is kept and flagged `IDENTIFIER_BOUNDARY_AMBIGUOUS`, never trimmed silently. A field
anchor covers the value as written, including surrounding whitespace (the normalizer records
`TRIM_OUTER_WHITESPACE`). Structural decoding (comments removed, HTML entities decoded, protocol-relative URLs
completed, URL query and fragment removed, a publisher URL's DOI path taken and percent-decoded once) is recorded step
by step; then the accepted Stage 02 `normalize_doi`/`normalize_pmid` are applied unchanged through `identifiers.py`.
Occurrences in comments, `<nowiki>`, `<pre>`, `<math>`, `<syntaxhighlight>`/`<source>`, ref names and other sites'
URLs are `excluded_identifiers` with a reason; they are never targets. Every occurrence is kept; co-reported
identifiers in one unit are never merged into one work (`CO_REPORTED_IDENTIFIERS`).

### 11.5 Roles (decision list, first rule that applies)

1. inside a retraction-marker template (profile `markers`) → `marker_target`;
2. display text of a link → `textual_mention`;
3. inside a citation or external-data template: in the template name → `textual_mention`; the value of an identifier
   field of that template → `primary_citation_field`, unless the same template repeats the parameter later
   (MediaWiki uses the last value) → `unresolved` with `IDENTIFIER_PARAMETER_OVERRIDDEN`; a URL or wrapper in an
   identifier or URL parameter → `identifier_link`; labelled text there → `labeled_reference_text`; anything else in
   the template (titles, other parameters) → `textual_mention`;
4. an identifier field of a template the profile does not support → `unresolved` (`TEMPLATE_UNSUPPORTED`);
5. a URL or wrapper inside a reference container (note, list-defined note, generated note, bibliography entry) →
   `identifier_link`; outside every reference container → `textual_mention` (RF-36);
6. labelled text inside a reference container → `labeled_reference_text`;
7. otherwise → `textual_mention`.

A notice, marker or title identifier is therefore never a `primary_citation_field`.

## 12. Render and reconciliation

### 12.1 Anchors

Source anchors are `[cp_start, cp_end)` and `[byte_start, byte_end)` of the retained UTF-8 bytes, with the raw text and
its SHA-256 for identifiers; `byte(i) = i + extra UTF-8 bytes of the code points before i`.

### 12.2 Render reading

lxml builds the DOM of the retained HTML (no script, no resource fetch). Reference uses are elements whose `typeof`
contains `mw:Extension/ref` with `data-mw`; reference lists are `mw:Extension/references`; template output is
grouped by `about` with the first element carrying `mw:Transclusion` and the template's `data-mw`. A locator is the
element id with its uniqueness, the lxml element path, a short text quote and the SHA-256 of the element's lxml
serialization (derived from the DOM, not a byte range). Duplicate DOM ids are reported (`DOM_ID_DUPLICATE`).

### 12.3 Reconciliation

Uses are matched within three groups the render keeps apart (article text, template output, nested in another
reference). In article text the sequences are aligned at anchors (named uses whose name occurs equally often on both
sides); between anchors a segment is matched position by position only when both sides have the same length, every pair is
compatible, and the notes of the first uses it pairs appear in each reference list in source order, also relative to
the pairs accepted before it (Cite numbers notes by first use); otherwise the segment is paired by unique shared
content or abstained and reported (`RECONCILIATION_ABSTAINED`, `RENDER_USE_UNMATCHED`), never guessed. Template
output is joined to the source template whose canonical name and parameter values equal those in `data-mw`. A
container is matched to the reference-list item its matched uses all point to; a note claimed by two containers, or
a note id that occurs twice in the DOM, is `note_ambiguous` (`RENDER_NOTE_AMBIGUOUS`) and no region is attached. A
unit is matched to template output inside that item by the same template key. An identifier is confirmed in the render
when an identifier link inside the matched region decodes to the same scheme and normalized value; links that no
source occurrence explains are render-only. With no render, every render-dependent state is `unavailable` and the
ledger says so; nothing is inferred.

## 13. Marker observations

One observation per container, of its matched rendered region (the reference-list or bibliography item, without
backlinks, styles and scripts). States: `recognized_warning_text` (a profile warning term in the region's shown
text), `ambiguous_text` (only ambiguous terms, a warning term only inside `<cite>`, or a warning or ambiguous term
only in text the HTML hides: `display:none`, the `hidden` attribute, CS1 maintenance classes),
`missing_template_link_only` (only a red link to a marker template), `no_recognized_warning_in_inspected_region`,
`not_inspected` (region not reconciled or ambiguous) and `unavailable` (no render). English terms must stand as
words; Arabic matching ignores harakat and tatweel and allows attached letters. `browser_visibility` is always
`not_evaluated`. No path turns a failure, an unavailable render or a hidden term into "no warning".

**Region text** (`RenderReader.region_text`) is rebuilt in two channels:

- the text a reader is shown, each character labelled `text`, or `cite` inside `<cite>`;
- the text the HTML hides.

Links to marker-template pages are kept apart. How the pieces join:

- Inline elements, comments, `<style>`, `<script>`, `<link>` and `<meta>` do not break a word:
  `<span>Re</span>tracted` is "Retracted".
- `<q>` adds its quotation marks.
- Every run of Unicode whitespace is one space.
- Block elements and `<br>` are a hard boundary (U+2029). No term, including a multi-word one, matches across it.
- Hidden content inside shown text is a soft boundary. A match that crosses a soft boundary, or that is found only
  with the soft boundaries joined or only with them separated, is ambiguous (`exclusion: interrupted`).
- Content a reader sees that is not region text, touching a word with no space between, is an edge, and a match
  that starts or ends at an edge is likewise ambiguous. Such content is a marker link's label, Parsoid's backlink
  span (only the direct child of the note's list item holding the `mw:referencedBy` links), or an unknown element.

How shown matches are classified:

- A shown match is `text` evidence only when all its characters are labelled `text`.
- Inside the citation it is ambiguous `cite_text`; across the citation's boundary, ambiguous (`spans_citation`).
- Word boundaries and the exclusions (title prefix, negation, quotation, Arabic attached letters) read the whole
  shown channel, so they see the text on both sides of the citation's boundary.

Hiding:

- The rules are inline `display:none` or `visibility:hidden`, the `hidden` attribute, the CS1 maintenance classes
  and `mw-empty-elt`.
- Hiding is inherited from every ancestor, including ancestors outside the region.
- A descendant that declares itself visible is still treated as hidden, because CSS is not evaluated.

**Links.** A link (red or blue) is classified by its target, read from Parsoid's `./Title` href or else from the
title attribute. If the target is a template-namespace page of a profile marker template, the label is kept out of
the text. A red one is then `missing_template_link` evidence, and a blue one is ambiguous (`template_page_link`).
Any other link is ordinary: its label is text in the channel it sits in, whatever the target.

**Evidence.** Each evidence item carries:

- its channel (`part`), the matched original text and a snippet;
- the DOM locator of the nearest element containing every matched character (required);
- the exclusion basis or `hidden_basis`, when there is one;
- for text inside a link: the link's target, how the target was read, and whether it is red.

**Running text.** A citation template standing in running text is a `standalone_template` bibliography entry.
Its region is the template's output. When letters or digits follow that output on its rendered line, that text
was not inspected, and the observation is `not_inspected` rather than a negative.

The matching cost is linear in the region's text and in its matches.

## 14. Verification and replay

`verify_bundle` re-checks from retained bytes only: schemas, artifact hashes and listing, source SHA-1 and size, the
source answer against the recorded identity, the render checks of 8.4, and for an extraction: its own digest, the
configuration digest, the capture it names, every span and exact anchor against the source bytes, every DOM locator
against the retained HTML (marker evidence locators included), the marker evidence (below), references between
entities and the accounting checks.

**Marker evidence checks:**

- a term item quotes text its element shows, in the channel its part names, with `text` labels throughout for a
  `text` item;
- the term matches the quoted text;
- a link item's label, target, marker-template target and red/blue status agree with its part;
- a hidden item's element is hidden;
- kinds agree with parts;
- the marker state follows from its evidence.

Evidence that was left out cannot be seen from the document; `replay` re-derives every observation. `replay_bundle` checks the recorded
document's schema and own digest, refuses a pinned configuration or extractor identity (version, profile, parsers)
that differs from the recorded one, re-extracts in the isolated worker and reports `reproduced` only when the new
document equals the recorded one.

## 15. Command line

`citerift-wiki capture | extract | verify | replay`. JSON on stdout, diagnostics on stderr. Exit codes: 0 ok,
1 internal error, 2 usage, 3 invalid input (unsafe path, malformed bundle, invalid configuration, missing schemas),
4 unavailable (network or service failure), 5 verification failure or replay difference, 6 partial, 7 unsupported
(wiki, namespace, content model, redirect, size), 8 deferred (`not_before` given), 9 failed. No command exits 0 with
a failure or an empty result; outputs are never replaced.

## 16. Isolation and limits

`extract_bundle` runs the extraction in a child Python process (`-I`, environment reduced to `PATH`, new session)
with `RLIMIT_AS` = `worker_memory_mib` (default 1024 MiB), `RLIMIT_CPU`, and a wall deadline `worker_wall_s`
(default 30 s) after which the process group is killed (`EXTRACTION_DEADLINE_EXCEEDED`,
`EXTRACTION_MEMORY_EXCEEDED`). The worker replaces socket connection functions before importing the extractor, so
any connection attempt fails. Structural limits (nodes 400 000, depth 60, refs 20 000, templates 50 000, candidates
50 000, render elements 2 000 000) fail closed with `LIMIT_*` codes. Every configuration value is validated
(positive integers; memory 64-65 536 MiB; wall time in (0, 3600] s); the schema pins the configuration object.

## 17. Security properties

Read-only access to two fixed hosts; no credentials; no paid or new services; no outbound fetch of publisher,
resolver or PubMed pages; no execution of retained HTML; no path from titles; no symlink following when reading or
publishing; no replacement of existing outputs; strict JSON; no `eval`/`exec`/`shell=True` in the engine (tested);
the worker refuses network connections (tested). `RISK_ANALYSIS.md` lists residual risks.
