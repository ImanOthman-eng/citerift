# Integration review R3 of the F1-F4 repairs (2026-10-29)

**Reviewer.** A separate Claude Code `general-purpose` subagent with its own context. It did not write the code it
reviewed.

**Restrictions.** It was read-only on the repository and used only synthetic offline inputs. It made no network
request, was told not to read `docs/verification/stage-03/evaluation/`, and did not run the full suite.

**Scope.** `git diff 049c48c..d11112c -- src/citerift/wiki schemas/wiki` and its integration with the rest of the
package.

**This copy.** The reviewer's answer is reproduced below without changes of substance. The harness refused its own
write of `REPORT.md`, so the executor saved the text. Its repro scripts are in `repro/`, renamed `*.py.txt` so that
the repository's lint does not run on them. They ran against `d11112c`, through `uv run python` from the
repository root.

The dispositions are in `../REVIEW_FINDINGS.md` (RF-44 to RF-54).

---

| id | severity | finding |
|---|---|---|
| R3-01 | high | A term split across the cite/text channel boundary is never matched, so the result is a confident `no_recognized_warning…`. |
| R3-02 | medium | Word boundaries and exclusion context ignore neighbouring text in another channel, so a warning is reported where the reader sees none. |
| R3-03 | medium | Any element with class `mw-cite-backlink`, which an editor can set, has its content dropped, giving a confident negative. |
| R3-04 | low | `<q>Retracted</q>` gives `recognized_warning_text`, while `"Retracted"` gives ambiguous (`quoted`). |
| R3-05 | medium | `verify_bundle` accepts forged marker evidence. |
| R3-06 | medium | Module:R's postscript (`ps`) and content-id (`ref`/`id`) parameters are not reported as `REUSE_CONTENT_UNSUPPORTED`. |
| R3-07 | low-med | RF-43: the sfn key still uses raw text, so a comment (or a blank argument) splits one note into two containers. |
| R3-08 | low | Reuse names are trimmed with Unicode `str.strip()`, not ASCII trim, so `{{r|a<NBSP>}}` binds to the wrong container. |
| R3-09 | medium | Cost is quadratic in the number of matches per region: a 41 kB note goes past the 30 s worker deadline, and verify has no deadline. |
| R3-10 | low | A literal U+2029 in the text is mistaken for the HARD boundary marker. |

**Checked and found sound:**

- **Determinism:** two isolated runs and one in-process run gave the same `extraction_digest`.
- **Valid inputs:** about 100 probes all passed the schema and `verify_bundle`.
- **Deep nesting:** it is caught at depth 255 by the render limit, with no crash.
- **Odd HTML:** comments, PIs, entities, missing `href`/`title` and U+2028/U+2029 raised no exceptions.
- **Large regions without terms:** 20,000 inline spans with no term took 0.7 s.
- **Isolation:** nothing in the change affects `worker.py`.
- **Reuse naming:** numbering, aliases, gaps, groups, replaced keys, the arwiki 10th name, comments, markup and
  excluded contexts all match the retained Module:R and arwiki sources.

## Confirmed reproductions (actual outputs, at d11112c)

**R3-01**

```
en 'Paper. Re<cite>tracted</cite>.'                      -> ('no_recognized_warning_in_inspected_region', []) verified=True
en 'Paper. <cite>Smith. Expression</cite> of concern.'   -> ('no_recognized_warning_in_inspected_region', []) verified=True
ar 'ورقة. <cite>سميث. مس</cite>حوب.'                      -> ('no_recognized_warning_in_inspected_region', []) verified=True
```

**R3-02**

```
en 'Paper. <cite>Smith. Un</cite>retracted.'          -> recognized_warning_text 'retracted'
en 'Paper. <cite>Smith. It was not</cite> retracted.' -> recognized_warning_text
en 'Paper. Retracted<cite>: a title. J Foo.</cite>'   -> recognized_warning_text
ar 'ورقة. <cite>سميث. غير</cite>مسحوب.'                -> recognized_warning_text
en 'Paper. <a rel="mw:WikiLink" href="./Template:Retracted">Un</a>retracted.' -> recognized_warning_text 'retracted'
```

**R3-03**

```
en 'Paper. <span class="mw-cite-backlink">Retracted</span>.' -> ('no_recognized_warning_in_inspected_region', [])
ar 'ورقة. <span class="mw-cite-backlink">مسحوب</span>.'      -> ('no_recognized_warning_in_inspected_region', [])
```

**R3-04**

```
en 'Paper. "Retracted" article.'      -> ('ambiguous_text', [('ambiguous','text','Retracted','quoted')])
en 'Paper. <q>Retracted</q> article.' -> ('recognized_warning_text', [('warning','text','Retracted',None)])
```

**R3-05**

```
forge 1 (hidden -> shown, locator kept): ('recognized_warning_text', ...) verified = True
forge 2 (no locator): ('recognized_warning_text', ...) verified = True
forge 3 (blue ordinary link as marker redlink): ('missing_template_link_only', ...) verified = True
```

**R3-06**

```
en '{{r|a|ps=.}}' [('r','a','bound')] []
en '{{r|a|postscript=.}}' [('r','a','bound')] []
en '{{r|a|id=x}}' [('r','a','bound')] []
en '{{r|a|ref=x}}' [('r','a','bound')] []
en '{{r|a|b|2ps=.}}' [('r','a','bound'),('r','b','bound')] []
```

**R3-07**

```
'A.{{sfn|Smith|2001}} B.{{sfn|Smith|2001<!-- c -->}}' -> 2 containers
'A.{{sfn|Smith|2001}} B.{{sfn|Smith|2001|p=}}'        -> 2 containers
```

**R3-08**

```
'A.<ref name="a">A</ref> <ref name="a&nbsp;">B</ref> C.{{r|a\xa0}}' -> the use bound to ct-00001 (name 'a'), expected ct-00002
```

**R3-09**

```
words 1000 (10.9 kB) 6.3s | words 2000 (20.9 kB) 21.8s | words 4000 (40.9 kB) 82.3s
new code only: soft 5000 19.8s | 10000 79.9s | 20000 339.9s
verify, 480 kB note: 100 items 11.1s | 200 22.1s | 400 49.1s
```

**R3-10**

`Expression<U+2029>of concern` gives `no_recognized_warning_in_inspected_region`. With U+2028 in the same place it
gives `recognized_warning_text`.

## Suspected, or outside the change

- **S-1.** `style="display:/**/none"` (CSS comments) is read as shown. This is likely unreachable, because
  MediaWiki's Sanitizer normalises CSS first. `visibility:collapse` is not treated as hidden; the specification
  lists only `visibility:hidden`.
- **S-2.** `<noscript>` content is dropped. This is likely unreachable, because wikitext does not allow
  `<noscript>`.
- **S-3.** Outside the diff: a standalone citation template's region is its `about` group only, so
  `{{cite journal …}} Retracted.` in a paragraph gives a negative.
- **S-4.** `Expression of<br/>concern` gives a negative. The specification requires this.
- **S-5.** Entity-encoded reuse names are decoded. MediaWiki may not decode them for `#tag` attributes; this was
  not verified.
- **S-6.** sfn parameter aliases (`p` / `page`, `sfn` / `sfnp`) may produce the same Module:Footnotes ref name but
  different keys here. Module:Footnotes is not retained.

The reviewer's own terminal status: NOT VERIFIED (it reviewed; it did not certify).
