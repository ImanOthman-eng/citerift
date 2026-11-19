# Stage 04 final corrective cycle: root cause and architecture review

Owner decision D-083 (`cmsg_018VCB51nDHP6HXmLU4ea5yPYP4QxCiKQ1Hzx2XLj9zxep`, 2026-11-19T20:37:57Z), items 1 and 2.
Both prospective evaluations (P / dt-1 and P2 / dt-2) stay NOT PASSED and unchanged. Everything here reads only
development evidence (the 232 Step 13 development revisions, the 80 articles of evaluation 1 and the 100 articles of
evaluation 2, all design-exposed); no label, adjudication or score of either campaign is read to choose a rule.

## 1. Root cause of the P2 false attachment (D-080)

Unit `en-27958530` / `un-00004` (revision 1373069395), source bytes 3331–3672 of the committed bundle:

```
{{cite journal |author=Robert Garry
 |title=Influenza or not influenza: Analysis of a case of high fever that happened 2000 years ago in Biblical time – Comments
 |journal=Virology Journal |date=21 July 2010 |volume=7 |issue=1 |page=169
 |doi=10.1186/1743-422X-7-169 |pmid=20663162 |pmc=2918564 |s2cid=8124033 |doi-access=free }}
```

Stage 02 (index `rw-2f116e9ffed718e6`), event `ev-0071523`, `retracted`: original DOI `10.1186/1743-422x-7-169`,
original PMID `20663162`, title "Influenza or not Influenza: Analysis of a Case of High Fever That Happened 2000 Years
Ago in Biblical Time", authors "Kam L E Hon;Pak C Ng;Ting F Leung", journal "Virology Journal", original date
2010-07-21.

dt-2 decides from identifiers only. Both cited keys are the record's original identifiers, Q1(DOI), Q1(PMID) and Q2
are `matched` with `verified_fact` / `retracted`, kappa is COHERENT, no role collision: D-14 →
`RETRACTED_WORK_CITED`. **Root cause: no part of dt-2 compares the citation's own bibliographic description with the
record its identifiers reach.** The citation's text names another object (a different author; a title that is the
record's title plus further material) while its identifiers name the retracted paper. The candidate inputs carry no
bibliographic field (Stage 03 units carry template names and byte spans, not argument values) and the lookup
observation keeps Stage 02's public event, which has the title and journal but neither authors nor dates. The defect
is general, not specific to this unit: in the 80 articles of evaluation 1 (development evidence since D-071), unit
`ar-10305362` cites "Induction of human neuronal cells by defined transcription factors" by Pang, Yang, Vierbuchen
and others with identifiers that reach the retracted record "Directed Conversion of Alzheimer's Disease Patient Skin
Fibroblasts Into Functional Neurons" by Qiang, Fujita, Yamashita and others: no shared author and almost no shared
title word.

## 2. Development survey (descriptive, used to set no threshold)

Reproducible with `scripts/survey_pairs.py` (read-only; Stage 02 index path and an output path outside the repository
as arguments; section 5). Over the 411 revisions with a committed source artifact (232 + 80 + 100, one development
bundle, `en-614753-a1`, has no source artifact), every citation template whose `doi` or `pmid` reaches a Stage 02 event
as an original identifier gives 243 (citation, event) pairs (28 development, 99 evaluation 1, 116 evaluation 2). Each
pair is described by the bib-1 code itself (specification sections 2 to 5):

| Observation (bib-1) | Count |
|---|---|
| Authors AGREE / CONFLICT / INSUFFICIENT | 239 / 2 / 2 |
| Title EQUAL / CONTAINED / OVERLAP / DISJOINT | 165 / 61 / 17 / 0 |
| CONTAINED or OVERLAP with a designation | 2 |
| Year SAME / DIFFERENT / INSUFFICIENT | 223 / 19 / 1 |
| Object COMPATIBLE / MATERIAL_CONFLICT | 240 / 3 |
| Stage 02 events with an Arabic-script title (whole snapshot, 73,356 events) | 0 |
| Stage 02 events with empty authors (whole snapshot) | 0 |

The three MATERIAL_CONFLICT pairs are the two units of section 1 (`en-27958530` / `ev-0071523`: authors disjoint and
a related-object designation; `ar-10305362` / `ev-0073139`: authors disjoint) and the evaluation-1 JASIST unit
(`en-39868218` / `ev-0033558`: "Withdrawal:" designation, authors agreeing), which dt-2 already decides by D-10 (role
collision) before D-13a is reached. No other pair is changed: the recall cost of bib-1 on this development evidence is
nil beyond the two misattributions it is meant to stop (`REGRESSION.md` gives the claim-level effect).

An earlier exploratory pass over the same 243 pairs (before the specification, with ad hoc folding) found that the
titles of one object vary (typographic variants, Greek letters spelled out, "(Pub 2)" in Retraction Watch, publisher
watermarks such as "RETRACTED:", truncation), that 19 pairs differ in year (15 by one year; 4 by two or more: two
Cochrane review updates, one book record), and one apparent "no shared title word" pair (`ar-311750-a1`, whose
`title` holds the journal name "Cochrane Database of Systematic Reviews" and whose `chapter` holds the review title;
bib-1 compares the whole title family and finds the chapter EQUAL).

What the survey shows, and how the specification uses it:

- Titles of the same object vary (typographic variants, Greek letters spelled out, "(Pub 2)" in Retraction Watch,
  publisher watermarks such as "RETRACTED:", truncation). A similarity threshold would have to be fitted to these
  data; the specification therefore uses only threshold-free relations (equality, containment, shared word, no
  shared word).
- Publication years of the same object differ by one or more in 19 of 243 pairs. Year is recorded, never decisive.
- Leading designations occur on genuine citations of the record's own object: "RETRACTED:" / "Retracted article:"
  (status watermarks of the work itself) and "Letter:" (`Cello scrotum` is itself a retracted letter). A designation
  can therefore only count where it names a *relation to another object* (section 4 of the specification), never a
  genre or a status.

## 3. Architecture review (item 2)

| Layer | What it holds today | Needed for the layer | Finding |
|---|---|---|---|
| Stage 03 extraction units | `kind`, template canonical name and family, source byte and code-point spans, identifier ids | the template's argument values | not in the document; the retained source artifact holds them |
| Stage 03 library | `citerift.wiki.source` scanner (mwparserfromhell 0.7.2, MediaWiki argument semantics) | parsing argument values | usable read-only; Stage 04 already depends on it |
| Stage 04 NORMALIZE | reads the committed extraction **and the source artifact bytes** (`unit_span_sha256`) | citation fields per unit | can parse each citation-template unit's own span: a Stage 04-owned change |
| Stage 02 public lookup result | event: ids, type, identifiers, notice fields, `title`, `journal`, flags, `row_sha256` (`public_event`, schema `additionalProperties: false`) | record authors, title, journal, year | authors and dates absent from the public result |
| Stage 02 `Index` read interface | `Index.gather_bounded` returns the full Stage 02 events (`schemas/retraction/v1/event.schema.json`: `title`, `authors`, `journal`, `original_date`, `original_year` all required); `event_detail` (CLI `event`) the same plus the raw row | record fields | **available through the accepted interface**: Stage 02 HANDOFF, "Requirements for the next stage": "Read the index only through `citerift.retraction.query` (`Index`, `lookup`, `event`)" |
| DETECT evidence model | evidence items over committed observations (D-051 ids), claims with evidence sets | a recorded comparison | new evidence kinds `cited_bibliography`, `bibliographic_comparison`: Stage 04-owned schema change |

**Decision: a Stage 04-owned correction; no Stage 02 or Stage 03 maintenance is required.**

- Citation side: NORMALIZE parses the argument values of each `citation_template` unit from the unit's own committed
  source span with mwparserfromhell (the parser Stage 03 pins), using a Stage 04 parameter-alias profile taken from
  the wikis' own CS1 configuration modules (specification section 2.2). Stage 03 code and its documents are not
  changed; its extraction is not reinterpreted (the span and the template identity come from it unchanged).
- Record side: LOOKUP already holds Stage 02's full events from `Index.gather_bounded` (the accepted interface, the
  byte budget of D-048 already counts every stored column, authors included). It records, beside the unchanged public
  events, each event's bibliographic fields from the same Stage 02 event, bound to the public event by `event_id` and
  Stage 02's `row_sha256`. No Stage 02 code, schema, policy or index changes; the Stage 02 public lookup result is
  recorded exactly as before.
- Decision: a new rule of a new table version (dt-3) between D-13 and D-14 (specification section 6).

Rejected alternatives: (a) changing Stage 02's public lookup result to carry authors and dates (an accepted-stage
change, not needed because the accepted `Index` interface already returns them); (b) adding argument values to
Stage 03 units (an accepted-stage change, not needed because the source bytes are already committed and read by
NORMALIZE); (c) reading the SQLite file directly (forbidden by the Stage 02 handoff); (d) a title-similarity score
(would need a threshold fitted to development data).

## 4. Build-vs-adopt (permanent rule of 2026-11-10)

See `BUILD_VS_ADOPT.md`. No new dependency is adopted: the comparison uses only the Python standard library
(`unicodedata`, `re`, `html`) and mwparserfromhell 0.7.2, already pinned for Stage 03.

## 5. Reproduction

`scripts/survey_pairs.py` (read-only; arguments: the Stage 02 index `rw-2f116e9ffed718e6` and an output path outside
the repository) recomputes the table of section 2 from the committed bundles. It reads the index only through
`citerift.retraction.query.Index` and reads no label, adjudication or score.
