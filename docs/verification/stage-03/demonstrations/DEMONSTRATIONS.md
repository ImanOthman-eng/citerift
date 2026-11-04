# Stage 03 demonstrations (directive section 12)

All five demonstrations run the installed `citerift-wiki` command line, offline, on retained bundles. They are
reproduced by:

```bash
bash docs/verification/stage-03/demonstrations/run_demos.sh docs/verification/stage-03/demonstrations/output
```

`output/transcript.txt` holds every command with its exit code and JSON summary. Every bundle was verified,
extracted, verified with its extraction and replayed:

- 22 commands exited 0;
- the two extractions that are `partial` exited 6: the source-only bundle, and the Arabic article in which one
  use inside a template's output abstained (2 source uses against 1 rendered use, `RECONCILIATION_ABSTAINED`);
- every replay reports `reproduced` with the same extraction digest.

The `output/demo*.json` files are focused views printed by `show.py`. That script reads only the extraction
documents and the retained bytes.

The bundles used are:

| Bundle | Article / revision | Source of the bytes |
|---|---|---|
| `tests/stage03/fixtures/observed/ar-76190003` | هاروكو أوبوكاتا, rev 76190003 | development acquisition of 2026-10-28 (calibration). Its capture record was rebuilt by replaying the recorded answers, so its times are the replay's. |
| `tests/stage03/fixtures/observed/en-1372543632` | Haruko Obokata, rev 1372543632 | as above |
| `bundles/en-1372543632-recapture-2026-10-29` | Haruko Obokata, rev 1372543632 | live capture on 2026-10-29 (09:22 UTC) |
| `bundles/en-1381772671` | MMR vaccine, rev 1381772671 | live capture on 2026-10-29 |
| `bundles/en-1374726997` | GFAJ-1, rev 1374726997 | live capture on 2026-10-29 |
| `../evaluation/capture/bundles/holdout/en-81119391-a1` | holdout article, rev 1316994319 | evaluation capture on 2026-10-29 |

All of this is Wikipedia content under CC BY-SA 4.0. The revisions are named above and in each `capture.json`.

## 1. Source marker and missing-template rendering

The Arabic revision cites the two retracted Obokata papers. Each citation carries `{{Retracted|doi=…|pmid=…}}`
in the source. Arabic Wikipedia has no such template, so the render shows only a red link to `قالب:Retracted`.
`output/demo1_ar_markers.json` shows two containers:

- **ct-00012:** `source_marker_templates` holds `Retracted` at code points 7141-7642. The marker state is
  `missing_template_link_only`, with the evidence `{"kind": "missing_template_link", "matched": "قالب:Retracted"}`.
  The rendered region is `cite_note-11`.
- **ct-00013:** the same, with `cite_note-12`.

The source marker and the rendered observation are separate fields. The red link's label is never read as a
warning, and the observation is never turned into "no warning".

For contrast, the English revision of the same article (`output/demo1_en_markers.json`) renders the template.
Containers ct-00012 and ct-00013 are `recognized_warning_text` there, with `Retracted` in the shown text.
ct-00018 is `ambiguous_text`, because "Retraction" stands only inside the citation's own title (`cite_text`).

In both languages `browser_visibility` is `not_evaluated`.

## 2. One reference reused at several places

`output/demo2_en_reuse.json` shows one named reference, `rasko` (container ct-00017):

- it has one definition, at code point 10502, and seven uses, at code points 10502 to 17743;
- each use is bound and matched to its own rendered marker, `cite_ref-rasko_17-0` to `cite_ref-rasko_17-6`;
- the container is matched to the note `cite_note-rasko-17`.

The source is not duplicated: seven uses, one definition, one container.

In the Arabic revision (`output/demo2_ar_reuse.json`), the same reference is reused seven times and the uses are
linked the same way.

## 3. Notice identifiers next to the cited work, never promoted

In the GFAJ-1 revision (`output/demo3_en_roles.json`), the retraction notice's DOI `10.1126/science.adu5488` and
PMID `40705905` appear inside `{{Retracted}}` in two references (ct-00001, ct-00012). They are `marker_target`
there, with the reason "inside a retraction-marker template", and are never the cited work's
`primary_citation_field`. The same DOI is also cited in its own right in reference ct-00061, through a `url=` of
`{{Cite journal}}`. There it is an `identifier_link` of that citation.

The engine does not decide that these occurrences denote the same work as an original paper. Each occurrence keeps
its own role and container (directive section 10).

In the Arabic Obokata revision (`output/demo3_ar_roles.json`), both notices' DOIs and PMIDs are `marker_target`.

No retained real article has a citation whose **title** contains the original's DOI, so the title case is covered by
a SYNTHETIC test, labelled as such:

- the test is `tests/stage03/test_wiki_source_extraction.py::test_wiki_notice_title_and_marker_are_not_cited_work`;
- its title `Retraction note to 10.1000/orig` gives `textual_mention`;
- it has bilingual twins in `test_wiki_bilingual_matrix.py` (`notice_title_and_marker_template`).

## 4. Several works in one reference

`output/demo4_en_multiwork.json` (MMR vaccine) shows reference ct-00060, which holds three `{{Cite journal}}`
units. Each unit has its own DOI and PMID:

- `10.1542/peds.107.5.e84` / 11331734;
- `10.1542/peds.109.1.172` / 11773568;
- `10.1053/jinf.2001.0930` / 11972410.

They are three units with six identifier occurrences. Nothing merges them into one work, and nothing asserts that
a DOI and the PMID beside it name the same paper.

## 5. Differing render captures of one revision, and a source-only capture

Two captures of the English Obokata revision 1372543632 were taken on 2026-10-28 and 2026-10-29
(`output/demo5_captures.json`):

- **Source:** identical bytes (the same SHA-256).
- **HTML:** the same length, 116,074 bytes, but different hashes. The only bytes that differ are the 24
  characters of `<meta http-equiv="x-mediawiki-render-id" content="…">`.
- **Extractions:** the digests differ, because each extraction is bound to its own capture record and HTML hash.
  Containers, uses, units and identifiers are equal apart from the render hashes
  (`output/demo5_extractions.json`).

A changed HTML hash with unchanged source proves only that the captures differ. Here the byte comparison shows the
difference. In general the hash alone does not name a cause, and the engine never claims one.

Holdout article en-81119391 (`output/demo5_source_only.json`) shows a render failure:

- its render request met HTTP 429 three times (Retry-After 1, 39 and 1 s) within the capture deadline, and the
  retry pass's new capture (`-a2`) ended the same way;
- the bundle holds the source only;
- the extraction is `partial`: source `complete`, render `failed`, reconciliation and markers `not_run`, every
  marker `unavailable`.

The source extraction is kept, and nothing about the render is inferred.
