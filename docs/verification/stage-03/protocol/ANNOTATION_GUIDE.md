# Stage 03 annotation guide (frozen with FROZEN_PROTOCOL.md)

This guide is given, unchanged, to the separate evaluator agent that labels the
holdout and the observed challenge set. It defines **what** counts as a reference,
a use, an identifier occurrence, a role, a key, a rendered link and a warning. It
deliberately does not describe how the extractor finds them.

## 1. Rules of independence

1. You inspect the retained raw artifacts only: `source.wikitext` (the article's
   wikitext at a pinned revision) and `render.html` (the Parsoid HTML of the same
   revision), with the window given in `packet.json`.
2. You must not read, import or run anything under `src/citerift/wiki/`,
   `tests/stage03/`, the calibration scripts, or any extraction output
   (`extraction*.json`, `*_extraction*`). You must not read the scoring script
   `evaluate.py` beyond this guide. You may use general tools (a text editor view,
   Python string search such as `str.find`, a general HTML parser such as lxml to
   list elements and attributes) to locate and verify what you see.
3. You do not edit any file outside your output directory.
4. Record in `provenance` which files you opened (with their SHA-256 from
   `packet.json`), which tools you used, and anything you could not decide.
5. Your labels are locked by hash before the extractor is run on these articles.
   After that, you may be asked to review disagreements; you will then see the
   extractor's answer for the disputed items only, and every change you make is
   recorded next to the locked label. You decide; no one else edits your labels.

## 2. Scope

`packet.json` gives a window `[cp_start, cp_end)` in **Unicode code points** of
`source.wikitext` (Python string indices of the decoded UTF-8 text). An item is in
scope when **its own start** lies in the window:

| Item | Its start |
|---|---|
| reference definition (`<ref …>…</ref>` with content) | the `<` of `<ref` |
| list-defined reference (inside `{{Reflist|refs=…}}` and equivalents) | the `<` of `<ref` |
| footnote template that carries content (`{{efn|…}}`, `{{refn|…}}`, Arabic `{{ملا|…}}`) | the first `{` |
| short footnote (`{{sfn|…}}`, `{{harvnb}}`-style templates that generate a footnote) | the first `{` |
| bibliography entry (see 3.4) | the list marker (`*`, `#`, `:`, `;`) at the start of the line, or the first `{` of a citation template that stands alone outside any footnote |
| use | the `<` of the `<ref` tag, or the first `{` of the template |
| citation template | the first `{` |
| identifier occurrence | the first character of its raw text (3.5) |

Also list a definition that starts **before** the window when one of its uses,
templates or identifiers starts inside the window (set `"in_window": false`), so
that bindings and identifiers can point to it. Items after the window are not
needed except as binding targets.

Every location is written as `{"cp": <int>, "quote": "<exact text>"}`, where
`quote` is the exact source text starting at `cp` (at least 8 characters where
possible, up to about 60). The scorer rejects any location whose quote does not
occur at exactly that position, so check each one with `text[cp:cp+len(quote)] == quote`.

## 3. What to label

### 3.1 Reference definitions

Every footnote reference that carries content: a `<ref>` with a non-empty body,
a content-bearing footnote template, a short-footnote template call, and every
bibliography entry. For each:

- `kind`: `note` (a `<ref>` in the article body), `list_defined_note` (a `<ref>`
  inside the references-list template), `generated_note` (a footnote template:
  efn/refn/sfn and their Arabic equivalents), or `bibliography_entry`;
- `name` and `group` as written (unquoted), `null` / `""` when absent; for
  footnote templates the group they use by default (e.g. `lower-alpha` for
  `{{efn}}` on enwiki) when no group is written, or `null` if you cannot tell;
- `templates`: every **citation template** inside the definition (templates whose
  purpose is to format a citation: `Cite …`, `Citation`, `استشهاد …`, `Cite Q`,
  and similar), each as a location; a short footnote has none;
- `unstructured`: `true` when the definition cites something in plain text with no
  citation template (bare URL, hand-written reference); `false` otherwise;
- `render_note_id`: the `id` of the `<li>` in the rendered reference list that
  shows this footnote (Parsoid HTML: `<li id="cite_note-…">`), or `null` when you
  find none (bibliography entries have none);
- `marker`: see 3.6; `marker_text`: the exact rendered text you based it on.

Two definitions with the same `name` and `group` are one reference (MediaWiki
shows the first; note whether their contents differ in `notes`).

### 3.2 Uses

Every place in the source that calls a footnote: each `<ref>` tag (with content,
or self-closing `<ref name="x" />`), each footnote template call (efn, refn, sfn,
`{{r|…}}` and equivalents; a `{{r|a|b}}` call with several names is one use per
name, all with the same location). For each:

- `binds_to`: the location of the definition MediaWiki uses for it (a `<ref>`
  with content is its own definition; a reuse by name binds to the definition
  with the same name **and group**, wherever it is; identical short-footnote
  calls bind to the first such call), or `"missing"` when no definition exists,
  or `"unclear"`;
- `render_ref_id`: the `id` of the rendered footnote marker for this use, a
  `<sup>` whose `typeof` contains `mw:Extension/ref` (its id starts with
  `cite_ref-`), or `null` when the use produces no marker you can identify.
  Parsoid places these markers in source order, and `data-mw` on each marker
  holds the ref's name and body; use them to align, and leave `null` when two
  candidates are equally plausible (write why in `notes`).

### 3.3 Templates that generate references the source does not contain

Infoboxes and other templates can emit references from Wikidata or from template
code; those references are rendered but are not in the article source. Do not
list them as definitions or uses (they have no source location). You may note
them in `unresolved_notes`.

### 3.4 Bibliography entries

A citation outside footnotes: a list item (a line starting with `*`, `#`, `:` or
`;`) outside any `<ref>` that contains a citation template or a DOI/PMID, or a
citation template standing alone outside footnotes (for example in a "Sources",
"Bibliography" or "Further reading" section).

### 3.5 Identifier occurrences (DOI and PMID)

Every occurrence of a DOI or a PubMed id in the window, wherever it is (also in
comments, `<nowiki>`, titles, prose, URLs). Its raw text is:

| Written as | Raw text to quote |
|---|---|
| citation-template field (`doi=`, `دوي=`, `pmid=`, also `biorxiv=`/`medrxiv=` which hold DOIs) | the value, without surrounding spaces |
| wrapper template (`{{doi|…}}`, `{{دوي|…}}`, `{{PMID|…}}`) | the argument |
| URL (`https://doi.org/…`, `dx.doi.org`, `pubmed.ncbi.nlm.nih.gov/…`, `ncbi.nlm.nih.gov/pubmed/…`, a publisher URL whose path contains `/doi/10.…`) | the whole URL |
| labelled text (`doi:10.…`, `PMID 12345`) | the identifier after the label |
| anything else | the identifier text |

For each: `scheme` (`doi` or `pmid`), `role`, `key`, optional `notes`.

**Roles** (choose by where the identifier sits, not by what the work is):

- `primary_citation_field`: the value of an identifier field of a citation
  template, that is the identifier of the cited work as the citation states it;
- `identifier_link`: a resolver/PubMed/publisher URL or a wrapper template inside
  a reference or citation template (for example in `url=`), pointing at the
  identifier;
- `labeled_reference_text`: plain text with a DOI/PMID label inside a reference
  (`doi:10.…`), not a link and not a field;
- `marker_target`: inside a retraction/correction/concern template
  (`{{Retracted|doi=…}}`, `{{Expression of concern|…}}`, `{{مصدر مسحوب|…}}`) —
  the identifier of a notice or of the work the notice concerns, not a citation;
- `textual_mention`: mentioned in text, not as the reference's identifier: in a
  title (`title=Retraction note to 10.…`), in prose, in link display text, in a
  parameter that is not an identifier field;
- `unresolved`: an identifier field of a template that is not a citation template
  and whose meaning you cannot establish;
- `not_a_target`: text that is not article content or not an identifier
  occurrence of its own: inside an HTML comment, `<nowiki>`, `<pre>`, `<math>`,
  `<syntaxhighlight>`/`<source>`; inside the value of a ref `name=`; inside
  another site's URL (for example an archive.org snapshot URL that contains a
  doi.org URL).

**Key**: DOI: the DOI starting at `10.` after removing a `doi:` label or a
`doi.org`/`dx.doi.org` resolver prefix, percent-decoded once when it came from a
URL, HTML entities decoded, with ASCII letters A-Z lower-cased (other characters
kept as they are); trailing sentence punctuation that is not part of the DOI is
not part of it; for a publisher URL, the DOI from the `/doi/` path segment (write
`null` and explain in `notes` when you cannot tell where it ends). `null` when the
text is not a syntactically valid DOI (`10.` + 4-9 digits + `/` + suffix).
PMID: the decimal digits with no leading zero (`null` for zero, leading zeros or
more than 9 digits).

### 3.6 Warning markers (per definition)

Look at the rendered footnote (`render_note_id`) and the definition's source.

- `warning`: the rendered text states that the cited work is retracted or is under
  an expression of concern (for example "Retracted", "(Retracted)", a retraction
  notice line produced by a template, "مسحوب"), as a statement about the cited
  work — not a word in the work's own title;
- `ambiguous`: retraction/correction vocabulary whose relation to the cited work
  you cannot settle (for example "Retraction", "withdrawn", "erratum",
  "corrigendum", "سحب" in a title or a note);
- `missing_template_link_only`: the only marker-like thing is a red link to a
  template page that does not exist (`class="new"`, title `Template:…`/`قالب:…`);
- `none`: none of these in the rendered footnote and source;
- `cannot_tell`: the footnote is not rendered or you cannot inspect it.

## 4. Output

One file per article, `<wiki>-<revision_id>.json`:

```json
{
  "format": "citerift-stage03-annotation-v1",
  "article": {"wiki": "en", "revision_id": 0, "source_sha256": "…", "html_sha256": "…", "window": [0, 8000]},
  "provenance": {"agent": "…", "started_at": "…", "finished_at": "…",
                 "files_opened": [{"path": "…", "sha256": "…"}], "tools": "…", "unresolved": "…"},
  "definitions": [{"id": "d1", "at": {"cp": 0, "quote": "<ref name=…"}, "in_window": true, "kind": "note",
                   "name": null, "group": "", "templates": [{"at": {"cp": 0, "quote": "{{cite journal"}}],
                   "unstructured": false, "render_note_id": "cite_note-…", "marker": "none",
                   "marker_text": null, "notes": ""}],
  "uses": [{"id": "u1", "at": {"cp": 0, "quote": "<ref name=…"}, "binds_to": {"cp": 0, "quote": "<ref name=…"},
            "render_ref_id": "cite_ref-…", "notes": ""}],
  "identifiers": [{"at": {"cp": 0, "quote": "10.1000/xyz"}, "scheme": "doi", "role": "primary_citation_field",
                   "key": "10.1000/xyz", "notes": ""}],
  "unresolved_notes": []
}
```

Label everything in scope, including what looks broken, unusual or unsupported.
When unsure, give your best reading and say why in `notes`; do not drop the item.
