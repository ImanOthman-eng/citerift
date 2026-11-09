# Independent adversarial review of D-035 (citation-unit classes A-H)

Reviewer: an independent context that did not write the change (owner instruction D-035, section 6).
Change under review: `git diff 26398f5 4d44e6c` (fail-first tests in `907d30d`). Report only; nothing was fixed.

## Scope, method, environment

- I read `SEMANTIC_DECISION.md`, the D-035 section of `SPECIFICATION.md`, the owner directive (sections 3, 5, 6),
  annotation guide v1.1 (section 3.3: `unstructured` is true when "the definition cites something in plain text with
  no citation template"), and the changed code in `model.py`, `units.py`, `source.py`, `extract.py`, `issues.py` and
  the schema.
- All inputs are SYNTHETIC bundles built through the production capture code (`tests/stage03/wiki_support.bundle`),
  or retained bundles under `docs/verification/stage-03/` used **for regression only** (exposed data). I made no
  network access.
- Scripts are in this directory. Run each one with
  `cd /home/user/citerift && PYTHONDONTWRITEBYTECODE=1 uv run python <script>`. `rvlib.py` is the shared helper.
  Pre-fix comparisons ran in the worktree `../base-26398f5`.
- **Working tree.** The checkout at `/home/user/citerift` has uncommitted edits on top of `4d44e6c`:
  - `src/citerift/wiki/worker.py`, which covers worker memory-error handling only;
  - documentation files and one tokenizer test.

  None of these touches the extraction semantics. All outputs of the in-process extraction match `4d44e6c`: I
  re-ran the differential's `extract_all.py`, and all 147 "new/" digests of `OUTPUTS.sha256` match.
- **Repository side effect.** My first import of `tests/stage03/test_g5c_unit_semantics.py` wrote one ignored
  bytecode cache file, `tests/stage03/__pycache__/test_g5c_unit_semantics.cpython-312.pyc` (07:56). The path is
  git-ignored. I did not delete it, because deleting would be another change to the repository. Every later run used
  `PYTHONDONTWRITEBYTECODE=1`. No other file in the repository was created, edited or deleted.

## Summary of findings

| Id | Severity | Status | One line |
|---|---|---|---|
| RV-1 | high | CONFIRMED (regression vs 26398f5) | A non-citation wrapper template (`{{small}}`, citebundle, Arabic wrapper) around a profile citation template becomes an `unsupported_citation_template` unit. The wrapped C unit gets this unit as its `parent_unit`. |
| RV-2 | medium | CONFIRMED | `CITATION_TEMPLATE_UNSUPPORTED` (and, already before the change, `DUPLICATE_TEMPLATE_PARAMETER`) names the unit id from before renumbering, which can be another unit. |
| RV-3 | medium | CONFIRMED | The Arabic Harvard template (RF-37 name rule) stays a `citation_template` unit whenever no render evidence exists, while `{{harvnb}}` in the same place is H. This contradicts "without a usable render, no unlisted template is established as a citation construct". |
| RV-4 | high | CONFIRMED (synthetic and real retained bundle) | A Harvard link plus comment text (adjudicated category 1) is still `unstructured_text` when the link has no render evidence: render failed or missing, or the ref is in a template parameter. The same revision gives D in `en-906156-a1` (render failed) and H in `-a2`. |
| RV-5 | medium | CONFIRMED (synthetic and exposed adjudicated label) | A citation-like template without CS1 markup, followed by any accessory text, is still `unstructured_text` (category 3 persists). Example: IUCN2008 plus commentary in `ar-2700573-a1`, adjudicated `unstructured: false`. |
| RV-6 | medium | CONFIRMED | A genuine plain-text citation inside `{{efn}}` / `{{ملا}}` gets no unit and no issue (silent false negative). This is not listed as a known limit. |
| RV-7 | low | CONFIRMED (follows from rule 3) | A whole plain citation wrapped in a formatting or identifier template (`{{lang}}`, `{{nowrap}}`, `{{ISBN}}`, `{{arxiv}}`, `{{URL}}`) is H, not D. It is reported, not lost. |
| RV-8 | low | CONFIRMED | A ref whose whole text is in `<nowiki>` gets no unit and no issue. |
| RV-9 | low | CONFIRMED | Version bump inconsistent: `extraction.schema.json` still declares `x-citerift-version` 1.0.0 after its enum was widened, and new captures report client 1.1.0 although capture did not change. |
| RV-10 | low | CONFIRMED | The H reason "only templates whose render shows no citation markup: Retracted / Efn / Reflist" claims render evidence that was never read for those kinds. |
| RV-11 | medium | design observation | Stage 04 interpretability: E, F and empty definitions leave no record. H is keyed by container, with the definition only in the free-text detail. RV-1 makes the meaning of G ambiguous. |
| RV-12 | info | documented and deliberate | A Harvard link plus a plain citation without a locator is H, not D. This is deliberate (section 5). It sits against the directive's "a genuine plain-text citation in the same definition must be retained", so the owner should see it. |

Checked and found correct (no finding):
- the source/render key pairing;
- determinism;
- complexity;
- verify and replay;
- schema validation;
- failure paths;
- non-unit outputs (the differential reproduced byte-identically);
- the plain-text recognition of wikilinks, formatting, `<span>`, entities, Arabic-Indic digits, `#tag:ref`, `refn`,
  infobox-parameter refs, list-defined refs and `<references>` blocks.

See "Verified behaviour" at the end.

---

## RV-1 (high, CONFIRMED, regression): a wrapper template around a profile citation becomes `unsupported_citation_template`

**Input** (`t1_wrapper.py`, `base_wrapper.py`). The render is Parsoid's: nested templates have no transclusion of
their own, so the wrapper's output holds the CS1 `<cite>` of the template nested in it.
```
A<ref>{{small|{{cite web |url=http://example.org/a |title=T |doi=10.1000/abc}}}}</ref>
render: <small typeof="mw:Transclusion" data-mw={small, 1="{{cite web …}}"}><cite class="citation web cs1">…</cite></small>
```

**Observed.**

Pre-fix engine (`26398f5`):
```
[('un-00001', 'citation_template', 'Cite web', None, 'within_matched_template')]
```

`4d44e6c`:
```
[('un-00001', 'unsupported_citation_template', 'Small', None, 'matched'),
 ('un-00002', 'citation_template', 'Cite web', 'un-00001', 'within_matched_template')]
issue CITATION_TEMPLATE_UNSUPPORTED ['un-00001'] 'Small'
```

The same happens in these cases:
- `{{Unbulleted list citebundle|{{cite book…}}|{{cite book…}}}}` gives G "Unbulleted list citebundle" plus 2 C units;
- `أ<ref>{{نص صغير|{{استشهاد بكتاب|عنوان=ك}}}}</ref>` gives G "نص صغير" plus C;
- `<ref>{{small|{{Fishbase|…}}}}</ref>` anchors the G unit on `{{small}}`, not on Fishbase.

Without a render, the same source gives one C unit only, so the unit set depends on whether a render exists.

**Expected.** Class G is "a template the profile does not list whose render is a CS1/CS2 citation". The SPEC says
"whose **own** Parsoid output contains a CS1/CS2 `<cite>`". `{{small}}` formats no citation. The CS1 markup comes
from the nested profile template, which is already a C unit. The definition should have exactly one unit, the C unit
with `parent_unit` null, as before the change.

**Why it matters.**
- It adds a false citation unit, so G5c precision falls, and Stage 04 would count two works for one citation.
- It labels a formatting template "unsupported citation template".
- It changes a field of an unchanged C unit (`parent_unit`). The directive forbids leakage of this kind ("Keep
  definitions, uses, bindings, identifiers … intact").

`units.output_evidence` scans the whole about-group and does not exclude output that comes from a nested template
of kind `citation` or `external_data`. In the 146 retained bundles I found no G unit with a nested C unit (scan:
`t9_survey.py`). Wrappers such as `{{Unbulleted list citebundle}}` and `{{Multiref}}` exist on enwiki.

## RV-2 (medium, CONFIRMED): an issue names the unit id from before renumbering

**Input** (`t2_issue_ids.py`): `A<ref>Smith, J. A book. 2001.</ref> B<ref>{{Fishbase|Osteobrama|bhimensis}}</ref>`,
with a render that gives Fishbase CS1 markup.

**Observed.**
```
units: un-00001 unstructured_text (Smith…), un-00002 unsupported_citation_template (Fishbase)
issue: CITATION_TEMPLATE_UNSUPPORTED entities ['un-00001'] detail 'Fishbase'   <- names the unstructured_text unit
verify_bundle: verified True
```
Cause: `model.build` creates the issue with `un.id` while template units come first. Units are later sorted by span
and renumbered (`renumber_u`), but issue entities are not remapped. `DUPLICATE_TEMPLATE_PARAMETER` has the same
defect, and it already existed before the change (`base_dup.py` on `26398f5`: the issue names `un-00001`, the
unstructured unit). In the retained real bundles all 9 `CITATION_TEMPLATE_UNSUPPORTED` issues happen to be correct
(`t11_issue_ids_real.py`), so the defect is latent there. `verify` does not check issue entities.

**Expected.** The issue names the G unit. **Why it matters.** Any consumer that joins issues to units by entity
attaches "unsupported template" to a plain-text unit, which is the wrong warning state on the wrong unit.

## RV-3 (medium, CONFIRMED): the RF-37 Arabic Harvard template is a citation unit whenever evidence is missing

**Input** (`t4_rf37.py`). `H = استشهاد بهارفارد دون أقواس`. Each case below gives the input, then what the new engine
outputs.

- `أ<ref>{{H|فوكس|2002}}</ref>` with a render that has a `#CITEREF` link: no unit (E). Correct.
- The same source with **no render**: `citation_template` unit.
- The same call nested in another template in the ref (`{{نص صغير|{{H|…}}}}`), with a render: `citation_template`
  unit (no evidence is read for nested templates).
- The same call in a ref inside an infobox parameter, with a render: `citation_template` unit.
- English `{{harvnb|Fox|2002}}` in the no-render and infobox cases: `UNIT_CLASSIFICATION_UNRESOLVED` (H).

**Expected.** The SPEC D-035 section says "Without a usable render, no unlisted template is established as a citation
construct". The same construct should get the same class in both languages. When there is no evidence, H (or the
same treatment as `{{harvnb}}`) is expected, not a citation unit.

**Why it matters.**
- The Arabic G5c false-positive category (a Harvard link counted as a citation template) returns whenever the render
  fails or the call is nested.
- It is an Arabic/English asymmetry for the same Harvard construct, which the directive names.
- In the bibliography zone (outside refs) such calls are never examined at all. This is consistent with "deciding
  templates are in refs", but it should be stated.

## RV-4 (high, CONFIRMED): a Harvard link plus comment is still `unstructured_text` without render evidence

**Synthetic input** (`t10_harv_text_norender.py`):
`A<ref>{{harvnb|Németh|2018|p=3}}, treats these as two separate volumes.</ref>`. This is the adjudicated category-1
false positive of `en-67651016`.

| Situation | Output |
|---|---|
| render with `#CITEREF` | H "plain text beside a short-citation link" (correct) |
| no render | **`unstructured_text`** |
| ref inside `{{Infobox person|birth_date=…<ref>…</ref>}}`, with render | **`unstructured_text`** |
| Arabic `{{استشهاد بهارفارد دون أقواس|…}}، ويقول …` with no render | `citation_template` (RV-3) |

**Real retained data** (exposed, regression only; `t10b_real.py`). The campaign holds two captures of the same
revision 1382942090:
```
en-906156-a1 render: failed
   (49257, '{{Harvnb|UKCCC H2|2018|p=79}}: The potential ', ['unstructured_text'], [])
   (49521, '{{Harvnb|UKCCC H2|2018|p=33}}: production of ', ['unstructured_text'], [])
en-906156-a2 render: complete
   (49257, …, [], ['definition 1: plain text beside a short-citation link'])
   (49521, …, [], ['definition 1: plain text beside a short-citation link'])
```

**Expected.** Rule 2 says text beside a short-citation link is H. With no evidence, the engine cannot tell whether a
template is a short link. The conservative reading of the required invariant, and of section 5 ("Without a usable
render … the engine does not guess"), is H whenever own text stands beside a template of kind `other` that has no
evidence. As implemented, missing evidence makes `short` empty and the text becomes D.

**Why it matters.**
- It reintroduces the exact 13-case category the owner ordered eliminated.
- It does so silently: no definition-level issue is emitted.
- The output for one revision depends on whether the render was captured, so the unit is not a property of the
  source.
- R-037 documents only that template-only definitions become H without a render, so this consequence is not
  documented.

## RV-5 (medium, CONFIRMED): a citation-like template without CS1 markup plus accessory text is still `unstructured_text`

**Synthetic input** (`t8_text_beside_unknown.py`), with a render in which the template shows no `<cite class=citation>`:

| Source | Output |
|---|---|
| `{{NRDB species|genus=Polemon|species=christyi}}` alone | H (as intended) |
| `{{NRDB species|…}} Retrieved 5 May 2024.` | **`unstructured_text`** |
| Arabic `{{القائمة الحمراء|معرف=1234}} تاريخ الاطلاع 2020.` | **`unstructured_text`** |

**Exposed adjudicated example** (`t16_iucn_real.py`, run-1 Arabic holdout `ar-2700573-a1`, definition at cp 1765):
```
<ref name=iucn>{{IUCN2008|assessors=McKnight, M.|year=2008|…}} Database entry includes justification …</ref>
engine 4d44e6c: unit unstructured_text
adjudicated label: templates=[IUCN2008], unstructured=false
  ("{{IUCN2008}} … formats a citation … followed by hand-written plain text … commentary, not a separate citation")
```

**Expected** (guide). Unstructured is false when the citation is made by a template, even one the profile does not
list. A definition whose only template is an unclassified template with no CS1 markup, beside text without a
locator, cannot be established either way. It should be H, like the template-only case, not D.

**Why it matters.** It is category 3 of the adjudicated false positives (unsupported citation-like templates). It
remains whenever any trailing text such as "Retrieved …" or "تاريخ الاطلاع …" is present. It is not a regression
(the pre-fix engine had the same output). However, section 5 does not list it, and the SEMANTIC_DECISION section 7
table omits Arabic run 1, where this instance sits. Prevalence in the retained data is low. In my scan, 1 of about
170 D units with a template of kind `other` beside text is of this kind. Most are `Webarchive`, `ISBN`, `US patent`
and `ردمك` beside genuine plain citations, so a fix must not turn those into H.

## RV-6 (medium, CONFIRMED): a plain citation inside `{{efn}}` / `{{ملا}}` is dropped silently

**Input** (`t3_fn.py`, no render):

| Source | Output |
|---|---|
| `A{{efn|Smith, J. (2001). ''A Book''. Publisher. p. 5.}}` | no unit, no issue |
| `أ{{ملا|سميث، ج. (2001). كتاب. الناشر. ص 5.}}` | no unit, no issue |
| `A{{efn|Smith, J. (2001). ''A Book''. ISBN 978-0-00-000000-2.}}` | no unit, no issue (ISBN is not a locator) |
| `A{{efn|Smith, J. (2001). ''A Paper''. doi:10.1000/xyz}}` | `unstructured_text` (locator) |

**Expected.** Guide 3.3 counts footnote templates that carry content (`{{efn}}`, `{{ملا}}`) as definitions, and
`unstructured` is true when the definition "cites something in plain text with no citation template". The efn rule
(own text without a locator gives F) is a name-family rule that decides "explanation" with no evidence. When it is
wrong, nothing is reported.

**Why it matters.**
- It is a silent false negative: no H issue and no ledger entry. The directive's conservative stance is to report
  rather than lose.
- R-037 says only "efn only: only the efn family is treated as explanatory"; the loss of genuine citations is not
  stated. Making efn text without a locator H, not F, would remove the 4 adjudicated false positives just as well,
  and would keep the abstention visible.
- In the retained data all 5 efn F cases are explanatory (`survey.json`), so there is no observed loss yet.

## RV-7 (low, CONFIRMED, follows from rule 3): a formatting or identifier template around a whole plain citation gives H

`<ref>{{lang|fr|Dupont, ''Histoire'', 1990}}</ref>`, `{{nowrap|…}}`, `{{ISBN|…}}`, `{{arxiv|…}}`, `{{URL|…}}` and
`{{webarchive|url=…|title=…}}` each give H: "only templates whose render shows no citation markup", or "no usable
render" (`t3_fn.py`, `t8_text_beside_unknown.py`). Per the guide these are unstructured (no citation template). The
result is reported, not lost, and follows from rule 3 as documented. Section 5 and R-037 list only the no-render
case, so the recall cost of wrappers and identifier-only refs should be stated there.

## RV-8 (low, CONFIRMED): a ref whose text is only `<nowiki>` gives no unit and no issue

`A<ref><nowiki>Smith, J. Book. 2001.</nowiki></ref>` gives no unit and no issue (`t3_fn.py`). Text in excluded tags
is not "own text", so the definition is treated as empty (F) without a report. This is rare, but it is a silent loss.
An abstention (H) would be safer.

## RV-9 (low, CONFIRMED): the version bump is inconsistent

- `schemas/wiki/v1/extraction.schema.json` widened the `kind` enum but still declares `"x-citerift-version":
  "1.0.0"`. Meanwhile the documents state `schema_version` 1.1.0, and SEMANTIC_DECISION says "extraction schema
  1.1.0". `docs/data-contracts.md` (Versioning) and the governance check `CONTRACT_VERSION_NOT_INCREASED` (applied
  to `schemas/contracts` only) state the project's rule that a changed contract raises its version.
- `capture.py` records the client version as `citerift.wiki.__version__`. New captures therefore say client 1.1.0,
  although the capture code did not change. This is harmless but undocumented.
- `verify.py` keeps `SCHEMA_VERSION = "1.0.0"`. That is correct, because the verification schema did not change.
- Verify and replay of new documents are correct (`t7_verify.py`): all validate, verify and reproduce. A 1.0.0
  prediction replays as `REPLAY_IDENTITY_MISMATCH` and still verifies, as documented (`t14_replay_old.py`).

## RV-10 (low, CONFIRMED): the H reason claims render evidence that was never read

`A<ref>{{Retracted|doi=10.1000/x}}</ref>`, `A<ref>{{efn|A note.}}</ref>` and `A<ref>{{reflist}}</ref>` each give
"definition 1: only templates whose render shows no citation markup: Retracted / Efn / Reflist" (`t15_messages.py`).
Evidence is read only for kind `other` and the `unlisted` family, so these reasons are not true statements about the
render. Stage 04 would read them as evidence.

## RV-11 (medium, design observation): downstream interpretability for Stage 04

- E (short link only), F (efn explanation) and the empty case produce **no record at all**. So does a short
  footnote. A consumer cannot tell "points to a bibliography entry" from "explanatory" from "empty" from "not
  examined". The directive asked for a formal distinction between A and H. The output does not collapse them into
  `unstructured_text` any more, but it collapses E, F and empty into silence. A per-definition `unit_class` field, or
  an info issue for E and F, would make this explicit.
- `UNIT_CLASSIFICATION_UNRESOLVED` names the **container**. The definition appears only as the free-text prefix
  "definition N:" of `detail`. With identical or conflicting named definitions, a consumer must parse free text to
  learn which definition is unresolved.
- With RV-1, `unsupported_citation_template` sometimes means "a formatting wrapper containing citations", so the
  kind is not unambiguous.

## RV-12 (info, documented and deliberate): a Harvard link plus a plain citation without a locator is H

`<ref>{{harvnb|Fox|2002}}; Jones, J. (2001). ''Other Book''. London.</ref>` with a render gives H, with no unit.
SEMANTIC_DECISION section 5 records this as deliberate, so it is not reported as a defect. The directive (section 3)
says "a genuine plain-text citation in the same definition must be retained". The implementation retains it only
when it carries a link, DOI or PMID. This is listed so that the owner sees the trade-off.

---

## Verified behaviour (attempts to falsify that did not succeed)

**Plain-text recognition** (`t3_fn.py`). Each of these keeps `unstructured_text`:
- a wikilink-only ref, and `''[[…]]''`;
- `<span>`, `<small>` and `'''bold'''`;
- the entity `&#49;`;
- Arabic-Indic digits `١٩٩٠`;
- `{{#tag:ref|…}}`, including with `group=note`;
- `{{refn|…}}`;
- a ref in an infobox parameter;
- list-defined refs in `{{reflist|refs=}}` and in `<references>`;
- a ref nested in an efn;
- identical named definitions;
- `{{harvnb}}` plus `{{doi}}`, and `{{harvnb}}` plus "PMID 12345".

Refs that are only `&nbsp;`, only punctuation or only a comment correctly give no unit.

**Key pairing** (`t5_keys.py`). G is found regardless of:
- whitespace around names and values;
- the case of the first letter;
- an underscore in the name, or a `Template:` prefix;
- parameter order;
- an explicit `1=`;
- newlines in the call;
- a duplicate parameter (last wins on both sides);
- a comment in a value;
- a double space in the name;
- an Arabic name with spaces.

Conflicting outputs for one key and omitted (parser-limit) output both give H, as documented.

**Determinism** (`t13_hashseed.py`): a mixed E/G/H/D document has the same digest under `PYTHONHASHSEED` values 0, 1,
12345 and random.

**Complexity** (`t6_stress.py`, in-process, new against pre-fix):

| Case | N | new | pre-fix |
|---|---|---|---|
| distinct harvnb refs | 2000 | 2.7 s | 2.7 s |
| distinct harvnb refs | 8000 | 14.4 s | 23.0 s |
| identical-key G refs | 2000 | 2.4 s | 2.2 s |
| identical-key G refs | 8000 | 19.8 s | 21.0 s |

There is no new super-linear term. The existing growth (about 7-9x for 4x the refs) is from code that predates the
change (`c.unit_ids` and `_unit_for` scans) and is not made worse. At 8000 refs the default `worker_wall_s=30` is
close.

**Failure paths and non-unit output** (`t12_failpaths.py`). Each was compared field by field with the pre-fix
engine:
- render element limit;
- source `max_refs` and `max_templates` limits;
- a render that cannot be used (the RECONCILIATION_UNAVAILABLE path).

Source-limit documents are identical. Otherwise only `units`, container `unit_ids`, identifier `unit_id`, the new
issue and ledger entry, and the unit accounting differ. Components, status, other issues, uses, bindings, roles,
normalization and anchors are unchanged.

**Differential reproduced.** I re-extracted all 146 retained real bundles with both engines and re-ran
`differential.py`. The result is byte-identical to the committed `DIFFERENTIAL.json` (22 changed, 124 unchanged,
`unexpected` empty). All base and new digests in `OUTPUTS.sha256` match.

**Schema, verify and replay** (`t7_verify.py`). The G, H, E, wrapper-G, Arabic-E and H-without-render documents:
- validate against the extraction schema;
- give verification reports that validate;
- give `verified: true`;
- give `replay: reproduced`.

The ledger entity type `container` is accepted.

**Focused tests:** `uv run pytest tests/stage03/test_g5c_unit_semantics.py -p no:cacheprovider` gives 68 passed.

## Suggested regression tests (for the implementer; not written into the repository)

- RV-1: `{{small|{{cite web|…}}}}` with a render must give exactly one `citation_template` unit with `parent_unit`
  null, and no `CITATION_TEMPLATE_UNSUPPORTED`.
- RV-2: a plain ref before a G ref, and before a cite with a duplicate parameter. The issue entity must be the
  template unit.
- RV-3 and RV-4: Arabic Harvard and `{{harvnb}}`, alone and with comment text, under no render, a nested call and an
  infobox parameter. There must be no `citation_template` or `unstructured_text` unit.
- RV-5: an unknown template without CS1 markup plus "Retrieved …" must not be `unstructured_text`, while `{{ISBN}}`,
  `{{Webarchive}}` and `{{US patent}}` beside a genuine plain citation must stay D.
- RV-6 and RV-8: an efn or `ملا` plain citation, and a ref that is only `<nowiki>`. The result must be reported, not
  silent.

NOT VERIFIED — this is a review report. Six material findings are open for the implementer: RV-1 to RV-6, two high
(RV-1, RV-4) and four medium.
