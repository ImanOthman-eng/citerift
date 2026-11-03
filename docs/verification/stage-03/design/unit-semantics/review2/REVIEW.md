# Second independent adversarial review of D-035 (commit 11bb5b2)

Reviewer: an independent context that did not write the change. Change under review: `git diff 4d44e6c 11bb5b2`.
Report only: no file in `/home/user/citerift` was created, edited or deleted by me, and git state was not touched.
(During the review other processes added untracked files and the commit `1483024` to the repository. That commit
changes no file under `src/` or `schemas/`, so the engine under review is unchanged.)
Every Python run used `PYTHONDONTWRITEBYTECODE=1` and `uv run --no-sync`. There was no network access.
Inputs were SYNTHETIC bundles built through the production capture code (`tests/stage03/wiki_support.bundle`) or
retained bundles. The retained bundles are exposed data and serve for regression only.

Scripts are in `scripts/` in this directory. Run each one from `/home/user/citerift` with
`PYTHONDONTWRITEBYTECODE=1 uv run --no-sync python <script>`. For a 4d44e6c comparison, add
`PYTHONPATH=<scratchpad>/rev-4d44e6c/src`. Raw outputs are in `out/`.

## Confirmed defects

### RV2-1 (high, CONFIRMED, regression): a bibliography entry with a G unit makes its own extraction fail `verify_bundle`

**Reproductions.**
- Real retained bundle (`scripts/t6_verify_real.py out/cur <bundle>`). With 11bb5b2's own extraction of
  `evaluation/final/capture/bundles/holdout/en-66266685-a1`:
  ```
  en-66266685-a1 verified False [('BUNDLE_SEMANTIC_INVALID', 'marker context reproduces: ct-00009'), (… ct-00011), (… ct-00012),
   ('BUNDLE_SEMANTIC_INVALID', 'marker region follows retained binding: ct-00009'), …]
  ```
  At 4d44e6c, with its own extraction of the same bundle: `verified True`. Over all 146 retained bundles, 145
  verify and this is the only failure (`out/verify_all.txt`).
- Synthetic (`scripts/t5_remap_verify.py`). Every random document that holds a `* {{EI2|…|doi=…}}` entry rendered
  with CS1 markup gives `verified False`, with the same two checks. `replay_bundle` reports `reproduced` for the
  same documents.

**Cause.** `verify.py` reconstructs the markers in the worker with
`build(scan_source(...), wiki, profile, ByteMap(text))`, which passes no `evidence` argument. The reconstructed model
therefore has no G units. The bibliography entry is not reconciled through its template, its marker is
`not_inspected`, and it differs from the recorded `no_recognized_warning_in_inspected_region` on the matched `li`.

**Expected.** Verification rebuilds the model the way extraction does: it calls `template_evidence` on the retained
render before `build`. A correct document then verifies. As things stand:
- `citerift-wiki verify` exits 5 on a correct extraction;
- the only exposed bundle that the new bibliography rule changes is unverifiable;
- neither the test suite nor the differential runs `verify` on these documents, so neither catches it.

### RV2-2 (medium, CONFIRMED, regression): a hand-written citation with its own DOI on a bibliography line beside a G template loses its unit silently

**Reproduction** (`scripts/t1_bib.py`, cases B1 and B10). Source:
`* Smith, J. (2001). ''Own work''. Journal 5. doi:10.1000/own123 {{EI2|…|doi=10.1163/…}}`, with EI2 rendered as CS1.

**Observed.**
- 11bb5b2: one unit, `unsupported_citation_template` EI2. The identifier `10.1000/own123` has role
  `labeled_reference_text`, `unit_id` None, and no issue is raised.
- 4d44e6c: one `unstructured_text` unit holding both identifiers.
- Arabic gives the same result (`دوي:` plus an unlisted template rendered as CS1).

**Expected.** The hand-written citation with its own locator is D (rule 1, positive evidence), or at least it is
reported. The directive says that a genuine plain-text citation must not be lost silently. The documented rule
"an entry with a C or G unit gets no unstructured_text" now applies to bibliography lines that held two works. The
same holds for refs with C units, so this is a design gap rather than a coding slip, but here it is a new silent
loss.

### RV2-3 (medium, CONFIRMED, regression; implementation differs from the specification): own-text identifiers inside any non-wrapper template make a hand-written entry H

**Reproduction** (`scripts/t1_bib.py`).

| Case | Source | 11bb5b2 | 4d44e6c |
|---|---|---|---|
| B2 | `{{Columns-list\|colwidth=30em\|` then `* Smith, J. (2001). ''Own work''. Journal 5. doi:10.1000/own123` on a list line inside the template | H: "identifiers only in templates that are not citation templates: Columns-list" (render) or "…no usable render…" (no render) | D |
| B3 | `* Smith … {{small\|doi:10.1000/own123}}` | H "…: Small" | D |
| B3r | the same text in a `<ref>` | D | D |
| B10b | Arabic: a hand-written entry inside `{{أعمدة\|…}}` | H | D |

**Cause.** `_bibliography_entry` treats an identifier as the entry's own text only when every frame in
`cand.frames` is a profile wrapper, and it counts every enclosing template, even a layout template around the whole
list. In refs, `_plain_definition` counts only frames inside the same ref, so refs and bibliography entries are
treated differently. `frames[:1]` then names the layout template as the reason.

**Expected.**
- `SEMANTIC_DECISION.md` section 4 and the SPECIFICATION make an entry H only when its "identifiers [are] only as
  fields of other templates". `doi:10.1000/own123` is labelled text, not a field, so the specification says D.
- A genuine located plain citation inside a list-layout template should stay D, as it does in a ref.
- No retained bundle exercises this case, because none has a bibliography H, so the differential cannot show it.

### RV2-4 (medium, CONFIRMED): the RV-4 rule turns every plain citation with a helper template in a template-embedded ref into H, even with a complete render

**Reproduction** (`scripts/t3_listdefined.py`). The render structure is copied from the retained Parsoid output of
`en-2695828-a1`: in `{{Reflist|refs=}}` the note's inner templates carry no `about`.

| Case | 11bb5b2 | 4d44e6c |
|---|---|---|
| `{{Reflist\|refs=<ref name=a>Smith, J. (2001). ''A Book''. Press. {{ISBN\|0-12-345678-9}}</ref>}}` | H "plain text beside templates with no output of their own in the render, or conflicting outputs: ISBN" | D |
| Arabic `{{مراجع\|refs=…{{ردمك\|…}}…}}` | H | D |
| `{{refn\|Smith … {{ISBN\|…}}}}` | H | D |
| control: the same ref inline | D | D |

**Cause.** Parsoid expands templates nested in another template's arguments as part of the outer transclusion.
Helpers in a ref inside a template therefore never have evidence. This is structural and is not a render failure.
It covers list-defined refs in reflist `refs=`, `{{refn}}`, `{{#tag:ref}}` and infobox-parameter refs.

**Expected.** At least, document the scope. SEMANTIC_DECISION section 3.2 and section 5 mention only the infobox
parameter and the failed render (`en-906156-a1`). The documents state "No other unstructured_text unit … changed",
which is true only of the retained data.

**Measured exposure** (`scripts/t2_rv4_survey.py`, `out/rv4_survey.txt`): 36 of the 476 D units in refs of the 146
retained bundles (7.6%) are D only because the render shows their helper template; without it they would be H. The
helpers are Webarchive, ISBN, ردمك, أرشيف الويب, US patent, Ill-WD2 and others.

### RV2-5 (medium, CONFIRMED, regression for refs): the holder rule (RV-1) disqualifies G whenever any unclassified template is nested, including `{{lang}}`, `{{transl}}` and the magic word `{{!}}`

**Reproduction** (`scripts/t8_holders.py`).

| Source | 11bb5b2 | 4d44e6c |
|---|---|---|
| `<ref>{{Fishbase\|Osteobrama\|bhimensis\|title={{lang\|la\|Osteobrama}}}}</ref>` | H "only templates, whose citation markup holds nested templates: Fishbase" | `unsupported_citation_template` |
| `title=Foo {{!}} Bar` | H | `unsupported_citation_template` |
| `title={{transl\|ar\|…}}` | H | `unsupported_citation_template` |
| `* {{EI2\|…\|title={{lang\|…}}\|doi=…}}` | H "identifiers in templates whose citation markup holds nested templates: EI2" | D |

**Expected.** RV-1 is about markup that the nested template produces. A formatting template or a magic word whose
own render has no `<cite class="citation">` cannot be the source of that markup. The engine already reads, or could
read, evidence for the nested template.

As implemented, a genuine G citation with a transliterated or `{{lang}}` title becomes H. This is common in
Encyclopaedia of Islam (EI2) and taxonomy citations. That is a recall loss on structured citations, which the
directive forbids, although it is reported rather than silent. DISPOSITIONS RV-1 says "if only an unclassified
template is nested, the definition is H". It does not say that this includes `{{lang}}` or `{{!}}`.

### RV2-6 (medium, CONFIRMED, documentation): DISPOSITIONS.md misstates the effect of 11bb5b2 relative to 4d44e6c

DISPOSITIONS.md, section "Effect on the retained data", says that compared with 4d44e6c "no unit is added" and that
"two `unstructured_text` units are removed". It also says: "The frozen scorer gives the same G5c and G5d as at
`4d44e6c` on every exposed campaign."

**Measured.**
- `out/diff_4d44_cur.json`, the repository's `differential.py` with 4d44e6c outputs as the base: `en-66266685-a1`
  gains 3 `unsupported_citation_template` units and loses 3 more `unstructured_text` units, so 5 are removed in all.
- `rescore/r4d44.txt` against `rescore/cur.txt`, `rescore_exposed.py` with the frozen scorer: final holdout English
  G5c 0.9732 → 1.0 and G5d 0.9561 → 0.9825 between 4d44e6c and 11bb5b2.

The F→H count (5) and the RV-2 entity corrections (13 + 1) are correct.

## Lower-severity confirmed findings

- **RV2-7 (low, CONFIRMED, predates the change, silent).** An unlisted template that spans several lines and starts
  on a list line makes no entry, no unit and no issue.
  - Source: `* {{EI2|last=Barthold|title=al-Barāmika\n|doi=10.1163/…}}` (`t1_bib.py` B7).
  - The control, a multi-line `{{cite journal …}}`, gives a C entry (B7c).
  - The cause is that bibliography members for candidates use the candidate's own line.
  - The new G-in-bibliography rule therefore covers only single-line calls, and the documents do not say so.
- **RV2-8 (low, CONFIRMED in the engine; the Parsoid behaviour is a hypothesis).** Magic words and parser functions
  (`{{!}}`, `{{PAGENAME}}`, `{{CURRENTYEAR}}`, `{{nbsp}}`, `{{#if:}}`, `{{#invoke:}}`) are deciding "unclassified
  templates".
  - Source: `A<ref>Smith, J. (2001). ''History of {{!}}''. Oxford: Clarendon Press.</ref>`
    (`scripts/t4_magic.py`).
  - Result: D only if the render gives the magic word its own transclusion; H with no render or without a wrapper.
  - Whether Parsoid always wraps these could not be checked offline. The retained renders contain only
    `defaultsort`. A magic word cannot be a short-citation link, so treating it as unknown evidence is needlessly
    conservative.
- **RV2-9 (low, CONFIRMED): MF-1 v3 uses the lifetime peak, not the state at the failure** (`scripts/t7_mf1.py`).
  - Probe: under RLIMIT_AS = 128 MiB, the process allocates until it gets MemoryError and frees everything. A later
    `SystemError("error return without exception set")` is then classified as a memory failure
    (`transient True`); without the earlier peak, `none False`.
  - A non-memory SystemError with that exact text after a transient peak would be mislabelled
    `EXTRACTION_MEMORY_EXCEEDED`. That is improbable, because the message comes only from CPython's error paths.
  - Non-Linux systems, a missing `/proc` and RLIM_INFINITY all correctly give False.
  - `test_a_system_error_far_below_the_limit_is_not_a_memory_failure` runs in the pytest process, where RLIMIT_AS is
    infinite, so it tests the RLIM_INFINITY branch rather than "far below the limit". The third test does cover that
    case.
- **RV2-10 (low, CONFIRMED, differential tool).**
  - `entity_fits` rejects every `UNIT_CLASSIFICATION_UNRESOLVED` issue on a `bibliography_entry`. The new rule
    creates exactly those issues, so the tool would report them as "names an entity that does not fit". It would
    also class a removed bibliography D unit as "E-or-empty".
  - The "explained" check accepts any new marker state for a G entry whose marker was `not_inspected`, and it does
    not check that the claimed `region_id` is the G unit's transclusion item.
  - It "explained" exactly the bundle whose new document fails `verify` (RV2-1). The differential never runs
    verify.

## Information (not defects)

- **RV2-11.** The bibliography rule was designed after inspecting the false positives of the exposed final English
  holdout, and it lifts that split's G5c to 1.000. The documents say "regression only". This should not be read as
  evidence of generalisation.
- **Render dependence:** 36 of 476 D units in refs depend on render evidence (RV2-4 survey).

## Tried and NOT falsified

- **Issue-entity remap (RV-2).** I checked 115 container and unit issues in 25 random synthetic documents. The
  documents mixed bibliography entries before refs, duplicate named refs, unused list-defined refs, G units,
  duplicate parameters and plain refs. None misfit (`t5_remap_verify.py`). Over the 146 retained bundles, 0
  misnamed issues remain against 14 before. The mapping keys are only `ct-`/`un-` ids, mapped once per stage, so
  there is no chaining or cross-namespace collision.
- **Bibliography cases that behave correctly** (`t1_bib.py`):
  - two EI2 calls on one line give two G units, each holding its own identifier (B4);
  - `{{doi}}` as an EI2 field or positional argument gives G, and the wrapper identifier is in the G unit (B5, B5b);
  - `{{small|{{EI2}}}}` gives H, which is consistent with RV-1 in refs (B6);
  - `**`, `:` and `;` lines give G (B8);
  - a ref inside a list line does not leak: the EI2 in the ref becomes the note's G unit and the outer EI2 the
    entry's G unit (B9);
  - Arabic behaves like English.
- **Determinism.** `en-66266685-a1` gives an identical extraction digest under PYTHONHASHSEED 1 and 999 and
  in-process.
- **Reproducibility.** All 147 regenerated outputs match `OUTPUTS.sha256` "new/", and the differential totals equal
  the committed `DIFFERENTIAL.json`.
- **Replay and schema.** Every synthetic document gave replay `reproduced`. Schema validation passes, as part of
  verify and replay.
- **Tests.** `tests/stage03/test_g5c_unit_semantics.py` and `test_wiki_mf1_tokenizer.py`: 111 passed. I did not
  run the full suite.
- **RV-6 and RV-8 counts.** The 5 F→H transitions are confirmed, and so is the absence of bibliography H in the
  retained data.

## Summary

| Id | Severity | Status | One line |
|---|---|---|---|
| RV2-1 | high | CONFIRMED (real and synthetic) | `verify_bundle` rebuilds the model without render evidence, so documents with bibliography G units fail verification (`en-66266685-a1`) |
| RV2-2 | medium | CONFIRMED | A hand-written entry with its own DOI beside a G template loses its unit and identifier binding, with no issue |
| RV2-3 | medium | CONFIRMED | A DOI written as text inside a layout or formatting template (`Columns-list`, `small`, `أعمدة`) makes a hand-written entry H; the specification says D, and in refs it is D |
| RV2-4 | medium | CONFIRMED | Plain citations with helpers in `reflist refs=`, `refn` or `#tag:ref` are always H, even with a full render; the scope is undocumented |
| RV2-5 | medium | CONFIRMED | Any nested unclassified template (`lang`, `transl`, `{{!}}`) turns G into H; regression from 4d44e6c |
| RV2-6 | medium | CONFIRMED | DISPOSITIONS' "no unit added / same G5c and G5d as 4d44e6c" is false: 3 G units added; final English holdout G5c 0.973→1.0, G5d 0.956→0.983 |
| RV2-7 | low | CONFIRMED | A multi-line unlisted template on a list line leaves no entry and no issue |
| RV2-8 | low | CONFIRMED (engine) / HYPOTHESIS (Parsoid) | Magic words count as unknown deciding templates; the result depends on Parsoid wrapping them |
| RV2-9 | low | CONFIRMED | MF-1 v3 uses the lifetime VmPeak; a transient peak plus that exact SystemError is labelled a memory failure |
| RV2-10 | low | CONFIRMED | Differential: stale `entity_fits` for bibliography H; the "explained" category accepted a bundle whose document fails verify |
| RV2-11 | info | n/a | The bibliography rule was tuned on the exposed final holdout |

NOT VERIFIED
