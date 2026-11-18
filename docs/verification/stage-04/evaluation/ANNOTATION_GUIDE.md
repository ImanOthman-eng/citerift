# Stage 04 evaluation: annotation guide

Pre-registered with `PREREGISTRATION.md` (section 7) and hashed before the draw. Annotators A and B and the
adjudicator receive this file unchanged. The executor checks the format of a label, never its content, and never
edits a label.

## 1. What you are asked

Each **item** is one citation unit of one Wikipedia article revision: the wikitext of a reference (a `<ref>` or a
list entry of a references section, as the Stage 03 extractor delimited it). Next to it you see:

- `identifiers`: the DOIs and PubMed IDs written in the unit, as written (`as_written`) and, when valid, normalized
  (`normalized`: lower-case DOI, PMID digits);
- `records`: up to a few Retraction Watch records (`R1`, `R2`, ...). A record describes one editorial event about one
  published paper: its `nature` (Retraction, Expression of concern, Correction, Reinstatement), the paper's title,
  journal, authors, date and identifiers (`original_doi`, `original_pmid`), and the identifiers of the notice that
  announced the event (`notice_doi`, `notice_pmid`).
- `reached_by`: why a record is shown. "doi:... as original" means an identifier of the unit equals the record's
  original-paper identifier; "as notice" means it equals the record's notice identifier; "title tokens" means the
  record's title words appear in the unit. **It is a search reason, not an answer**: a record shown by title can be a
  different paper, and an identifier can be mistyped.

You decide what the unit cites, and how each record relates to it. You do **not** decide whether a paper is retracted,
whether the record is correct, or whether Wikipedia should cite it. You see no output of any detector; there is none
to agree with.

Use only the item: the unit text, its identifiers and the records. Do not use the network or other files. Where the
item does not let you decide, answer `cannot_tell`; that is a correct answer, never a failure.

## 2. The label

One JSON object per item; every field is required:

```json
{"item_id": "...", "kind": "...", "same_work": "...", "records": {"R1": "...", "R2": "..."},
 "single_identifier_attachable": "...", "note": "..."}
```

### 2.1 `kind`: what the unit is

| Value | Meaning |
|---|---|
| `work_citation` | The unit is a bibliographic reference to a published work (article, paper, chapter, book, preprint) as a source. A retraction warning or template inside the same unit does not change this. |
| `notice_citation` | The unit's reference is to an editorial notice (a retraction notice, an expression of concern, a correction or erratum, a reinstatement notice), not to the paper the notice is about, even if it names that paper. |
| `retraction_marker` | The unit's content about the records is only a warning or template saying that some work was retracted or questioned (for example a `{{Retracted}}` template with its own identifiers), with no reference to a work of its own. |
| `other_mention` | The unit names a work without being a reference to it (an explanatory note, a quotation, a discussion of the paper). |
| `not_a_reference` | The unit is not a bibliographic reference at all (navigation, formatting, an empty or broken fragment). |
| `cannot_tell` | The item does not let you decide. |

When a unit contains two references (for example a paper and, after it, its retraction notice), answer for the
reference the unit's identifiers belong to; if they belong to both, answer `work_citation` when the paper itself is
cited, and judge each record separately in `records`.

### 2.2 `same_work`: do the unit's DOI(s) and PMID(s) name one work?

| Value | Meaning |
|---|---|
| `yes` | The unit has at least two identifiers (DOI and PMID, or two of one kind) and they all identify the same work. |
| `no` | The unit has at least two identifiers and they identify different works (for example the DOI of one paper with the PMID of another). |
| `single_identifier` | The unit has exactly one DOI or PMID. |
| `no_identifier` | The unit has no DOI and no PMID. |
| `cannot_tell` | The unit has at least two identifiers and the item does not show whether they name one work. |

Judge from what the item shows: a record listing a DOI and a PMID as the same paper's identifiers shows they name one
work; a record whose original DOI is the unit's DOI and whose original PMID differs from the unit's PMID, with the
unit's PMID being another record's paper, shows they do not. Count only identifiers listed under `identifiers`.

### 2.3 `records`: how each record relates to what the unit cites

One value for **every** record ref of the item:

| Value | Meaning |
|---|---|
| `cited_work` | The unit cites the record's original paper (the paper the event is about): same paper by title, authors, journal and year, or by an identifier that the unit text confirms. |
| `cited_notice` | The unit cites the record's notice (the notice document itself), not the original paper. |
| `unrelated` | The unit cites neither the record's original paper nor its notice (a different paper, perhaps with a similar title, or a mistyped identifier pointing elsewhere). |
| `cannot_tell` | The item does not let you decide. |

Several records can concern the same paper (for example a correction and a later retraction of one paper): judge each
on its own; all of them can be `cited_work`.

### 2.4 `single_identifier_attachable`

Whether the unit unambiguously cites one work **and** at least one of its identifiers alone identifies that work, so
that the citation could be attached to the work by that identifier alone:

| Value | Meaning |
|---|---|
| `yes` | One work is cited, without doubt, and one of the unit's identifiers alone identifies it (for example the title, journal and DOI agree, and the PMID is another paper's). |
| `no` | The unit is ambiguous (its text and identifiers point to different works and nothing decides between them), or no identifier of it identifies the cited work, or it has no identifier. |
| `cannot_tell` | The item does not let you decide. |

### 2.5 `note`

Free text, at most 500 characters: a short reason, especially for `no`, `unrelated` and `cannot_tell` answers. It is
kept with the label and never scored.

## 3. Examples (synthetic)

1. A `{{cite journal}}` with title "X causes Y", DOI 10.1/a, PMID 111; record R1 (Retraction) with title "X causes Y",
   original DOI 10.1/a, original PMID 111. Label: `work_citation`, `yes`, `{"R1": "cited_work"}`, `yes`.
2. A reference whose title is "Retraction: X causes Y", DOI 10.1/notice; R1 has notice DOI 10.1/notice. Label:
   `notice_citation`, `single_identifier`, `{"R1": "cited_notice"}`, `yes`.
3. A reference to "X causes Y" with DOI 10.1/a and PMID 222, where R1 (original DOI 10.1/a, PMID 111, title "X causes
   Y") and R2 (original PMID 222, title "Unrelated topic") are shown. Label: `work_citation`, `no`,
   `{"R1": "cited_work", "R2": "unrelated"}`, `yes` (the DOI alone identifies the cited paper).
4. A reference to "Z in mice" with no identifier, shown R1 by title tokens with title "Z in mice and rats", another
   journal and year. Label: `work_citation`, `no_identifier`, `{"R1": "unrelated"}`, `no`.

## 4. Output

Write one label file per batch in the format `citerift-stage04-eval-labels/1`:

```json
{"format": "citerift-stage04-eval-labels/1", "annotator": "A" | "B" | "ADJ", "instance": "...", "model": "...",
 "started_at": "...", "finished_at": "...", "labels": [ ... one label per item ... ]}
```

Annotators A and B label every item of their batch. The adjudicator labels exactly the items listed as disagreed.
