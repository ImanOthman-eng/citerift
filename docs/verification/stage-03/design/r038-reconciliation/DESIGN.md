# R-038: repeated reference names inside one template's output

*CITERIFT — Created and Directed by EVE TELOS · IM*

Owner instruction of 2026-11-04 (DECISIONS.md D-036, `../../authorization/OWNER_DIRECTIVE_2026-11-04_R038.md`,
sections 3 and 4). Status of this document: engineering record of the correction. It is not a verification result
and not acceptance.

Sections 1 to 8 record the correction as first committed (`10bf0d2`). Sections 9 to 12 record what changed after it:
the weak-number fix S-1 (`2229146`) and the fixes of the readiness reviews (section 7 of the directive). Where
they differ, the later sections, SPECIFICATION.md and MATHEMATICAL_MODEL.md describe the engine as it is.

## 1. Root cause

`src/citerift/wiki/reconcile.py`, `Reconciler._align_unordered` (engine 1.1.0, code from `a29bb4e`, unchanged by
D-035). Inside one template's output the engine grouped the uses of each reference name and, when the source and the
render had the same number of uses of that name, paired them by zipping both lists: the source list in source order
and the render list in document order. The method's own docstring says the opposite assumption: "the template decides
the order (an infobox renders its parameters in its own order)". When a template renders its parameters in another
order than the editor wrote them, the zip attaches each use to another use's marker.

The D-035 G6b failure is one instance: in `ar-76814232` the star infobox renders its U−B row before its B−V row; the
reference `Mallama2014` is defined in the B−V parameter and reused in the U−B parameter, so the definition was
attached to the reuse's marker and the reuse to the definition's marker (2 false attachments).

## 2. How widespread (read-only surveys, before any production change)

All scripts and outputs are in `evidence/`. They read every retained real bundle (183 distinct articles with a
captured render at the time of the survey) with the unchanged engine.

* **data-mw `body` is reliable role evidence** (`data_mw_body_survey.py`, `.json`). For every source use that the
  engine paired by position or by a unique name, the source role (a `<ref>` with text = definition, a `<ref ... />`
  = reuse) agrees with Parsoid's `data-mw`: definitions carry `body.id` = `mw-reference-text-<the marker's note>`
  (4,659 markers, every one consistent with its link target), reuses carry no `body` or an empty inline
  `body.html`. The only two disagreements in the whole corpus are R-038 swaps: `Mallama2014` (ar) and
  `Chryssides 2001` (en-1371940951, a D-034 reserve article whose infobox uses were not in the labelled sample).
* **15 same-name groups** with two or more uses in one template's output exist in the corpus. Four have a
  definition among them; eleven are reuses only (the definition is in article text), where `body` cannot tell the
  markers apart.
* **The text before the marker settles most reuse-only groups** (`text_anchor_probe.py`, `.txt`): the visible text
  just before a marker in its table cell equals the parameter text just before the `<ref>` in the source. The probe
  found two more swaps, both in unlabelled uses: `ayres2023` (en-1381005609; the template shows 3.66 before 6,187)
  and `MPGfacts` (en-1380218630, a D-035 holdout article; the template shows the budget before the staff count).

## 3. The correction

Only the decision that was wrong is changed: how several uses of one name inside one template's output are paired.
Everything else in reconciliation is untouched (a name used once in a template's output still pairs by name, basis
`name_in_template_output`; prose, nested references, templates, containers, units and witnesses are unchanged).

For a name with n ≥ 2 uses on both sides (all compatible), `Reconciler._same_name` pairs only on evidence:

1. **Role** (`reference_role_in_template_output`). `RenderUse.body_role` (render.py `body_role`) reads the
   marker's data-mw: `definition` (a `body.id` naming this marker's own note text, or a non-empty `body.html`),
   `reuse` (no `body`, or an empty `body.html`), `contradictory` (a `body.id` naming another note, or a body of an
   unknown shape), or none (no readable data-mw). Every marker of the name must have a readable role and the two
   sides must hold the same number of definitions, or nothing in the name is paired. A role held by exactly one
   use on each side pairs those two.
2. **Anchor** (`anchor_in_template_output`). `source_anchor` reduces the parameter text before the `<ref>` (its
   last line; comments removed; other references become a space; piped and plain wiki links become their text;
   named external links their label; bold, italics and simple inline tags dropped; text after the last closed
   template) to visible text, or gives no anchor when that cannot be done without rendering. `preceding_text`
   (render.py) collects the visible text before the marker in its nearest block (table cell, list item,
   paragraph, ...), skipping hidden elements and putting a space where another marker stands. A use is supported
   by a marker when the rendered text ends with the source text and, unless the source text was cut to its last
   32 characters, does not continue a longer word or number (`1.31` does not anchor `11.31`). A source text
   shorter than 3 characters supports only a marker whose whole before-marker text it is (`6` anchors a cell that
   shows only `6`).

   When the last line before the `<ref>` holds templates, the text cannot be read without rendering. Then
   `source_numbers` takes the numbers of that line, leaving out template names and named-argument keys
   (`{{val|9494|143|u=K}}` gives 9494 and 143), and a marker supports the use when the numbers of its
   before-marker text are exactly those (`numbers_of`: grouping separators dropped, Arabic-Indic digits and the
   Arabic decimal separator read as ASCII). A template that changes its numbers (`{{val|1.2|0.4|e=3}}` shows
   `(1.2±0.4)×10³`) gives no support, and two parameters that show the same numbers support each other's markers,
   so neither is settled by them.
3. **Elimination** (`elimination_in_template_output`). Within one role, a use whose text cannot be read takes the
   one marker left once every other use is fixed. `_settle` fixes a pair only when one side has a single choice
   left; a use with an anchor may take only markers that support it, and a marker that supports some use may be
   taken only by such a use. The pairing is accepted only when every use of the role is fixed that way, which
   makes it the only complete pairing the constraints allow.
4. **Partial result.** When a role group is not settled completely, only pairs whose anchor is shared with no
   other use and no other marker are kept; the remaining uses stay unpaired and are reported with
   `RECONCILIATION_ABSTAINED` (as before for any unpaired use in template output).
5. **Contradiction.** If a use's anchor supports only markers of the other role, the data-mw and the text disagree:
   nothing in the name is paired.

Bounds: no pairing is attempted for more than 2,000 uses of one name in one template's output; a block larger than
20,000 elements gives no anchor; the anchor text compared is the last 32 (source) and 200 (render) characters, and a
rendered text that may have been cut gives no number support.

Nothing in the correction names an article, a template, a parameter or a reference name.

## 4. A defect found in the correction before it was committed

The first implementation of `preceding_text` kept the marker's ancestors as a set of `id()`s. lxml makes element
proxies on demand and an id can be reused once a proxy is released, so the walk sometimes stopped early ("Munich"
instead of "Munich, Germany"). The first differential run showed it (reuse-only groups abstained that the probe had
settled). The set now holds the elements themselves. Regression test:
`test_r038_before_marker_text_is_stable_across_element_proxies` fails three times out of three with the `id()` set
(`evidence/FAIL_FIRST_anchor_walk.txt`) and passes with the element set.

## 5. Tests

`tests/stage03/test_r038_template_output_order.py`. The cases required by the directive (section 3) are covered:
reordered infobox parameters; repeated named references; definition followed by reuse; reuse rendered before the
definition; multiple reuses; multiple groups; anonymous references; nested templates; a template producing many
markers; missing data-mw; contradictory data-mw (two bodies, no body, a body naming another note); unreadable
data-mw; duplicate DOM identifiers; a render of another revision; Arabic; identical (ambiguous) anchors; a number
inside a longer number; large (150 reversed parameters with anchors) and pathological (300 without anchors)
templates. Three real bundles are post-exposure regressions (they were captured, and in two cases scored or
reviewed, before the correction): `ar-76814232` (Mallama2014), `en-1371940951` (Chryssides 2001), `en-1381005609`
(ayres2023).

Fail-first: on the unchanged engine 20 of the first 25 tests fail, each with a wrong attachment or a missing
abstention (`evidence/FAIL_FIRST_before_fix.txt`, revision `ec81c7f`, whose `src` equals the D-035 candidate
`fff0e5b`). The number anchor was added after the first differential showed that the role and text evidence
alone left 17 reuses of `{{val}}`-style values unpaired, 4 of them correctly labelled before: its tests fail on
the role-and-text version (3 of 5; the 2 negative ones pass, as they should) (`evidence/FAIL_FIRST_number_anchor.txt`).
Two synthetic tests of the first set used `{{val|x}}` values as the example of a value with no readable text; with
the number anchor such values are settled (correctly), so those two tests now use a template that shows only an
image, which keeps what they test (unanchorable reuses abstain). After the correction all 32 tests pass.

## 6. Differential over every retained real bundle

`differential/` (scripts, `DIFFERENTIAL.json`, and `OUTPUTS.sha256` of the 2 × 195 extraction documents). The
engine before (`ec81c7f`) and after the correction extracted the 195 retained real bundles (every
`capture.json` under `docs/verification/stage-03` except SYNTHETIC ones; the five withheld files of
`en-1380218630` present on disk). The script reports any difference outside the render pairing of uses and what
follows from it; there is none.

| Change of a use's render pairing | Uses |
|---|---|
| unchanged | 6,693 |
| same marker, new basis (the old pairing is now backed by evidence) | 32 |
| different marker (the old pairing was a swap) | 15 |
| matched before, abstained now | 2 |

The 15 corrected uses are in 7 articles: `ar-76814232` (Mallama2014, 2), `en-1371940951` (Chryssides 2001, 2),
`en-1381005609` (ayres2023, 2), `en-1378959744` (Borisov2023, 2), `en-1329904848` (Jönsson et al. 2020, 3, and
Koutoulaki et al. 2018, 2), `en-1380218630` (MPGfacts, 2). The 2 abstentions are two reuses in `en-1375552426`
whose values come from data templates (`{{HESA undergraduate population|...}}`), where nothing in the source shows
what the render displays.

## 7. Every retained label (post-exposure)

`differential/labelled_links.py`, `LABELLED_LINKS.json`. 150 locked or adjudicated label files from all campaigns
(adjudicated labels replace locked ones). These labels were exposed before the correction; the comparison is a
regression check, not a gate result.

| Labelled render links | Before | After |
|---|---|---|
| engine marker = label | 1,372 | 1,376 |
| false attachments | 4 | 0 |
| engine abstained, label has a marker | 69 | 69 |

The 4 false attachments before are the 2 of the D-035 G6b failure (Mallama2014) and 2 in the D-034 challenge
split (`en-1378959744`, Borisov2023), where render links were labelled but only markers were scored, so G6 never
counted them. No labelled correct attachment is lost and no new false attachment appears.

## 8. Classification

* R-038 itself: genuine defect, corrected.
* The `id()` walk (section 4): genuine defect in the first version of the correction, corrected before commit.
* Reuses whose parameter values come from templates that show other text than their arguments (data templates,
  date templates that add an age): supported boundary; they are abstained and counted.
* A template that shows two parameters with identical text or numbers: supported boundary (ambiguous, abstained).
* After the review fixes: the readiness-review findings and their classification are in `review/DISPOSITIONS.md`.

## 9. S-1: a one- or two-digit number is too weak to anchor (`2229146`)

`simulations/stage03/template_order_sim.py` renders an infobox's parameters in random order, with clean values and
with adversarial values (several cells showing similar text), with and without one marker's data-mw. In the
adversarial mode the first correction made 12 swaps, all from a small number shown by two cells (`{{double|2}}`
showing 4 beside a cell showing 2). A number support now needs at least 3 digits in all. The fail-first evidence is
in `evidence/FAIL_FIRST_weak_number_anchor.txt`; the simulation outputs are in `simulation/` (the engine before the
correction: 2,916 swaps in 800 articles).

## 10. Readiness review and fixes

Two independent reviewers examined `10bf0d2`: A the reconciliation subsystem, B the integration boundary
(`review/`). A found two high defects. A-01: a template that restyles one value (`12345` shown as `12,345`), or a
value with no readable text, let elimination swap two markers. A-03: bibliography entries inside one multi-part list
transclusion shared the whole list as their region. A and B found five medium defects: A-02, A-04, A-05, B-1 and B-2.
Every confirmed finding was fixed fail-first or documented (`review/DISPOSITIONS.md`). The central change answers
A-01 and B-1 together. A swap can only come from a support relation that **misses** a use's true marker (the safety
argument in `MATHEMATICAL_MODEL.md`), so support was made generous instead of exact:

* whole-word occurrence anywhere in the before-marker text, not only at its end (a unit, an age or a qualifier may
  follow the value);
* the same comparison after folding case, digits, the Arabic decimal separator, the minus sign and digit-group
  separators;
* for a value without letters, its numbers in a row among the marker's numbers;
* `_settle` accepts a class only when the uses with support are exactly as many as the markers that support some
  use, and at most one use without support is left.

A marker added to a support wrongly can only make a class ambiguous (an abstention), never a wrong pair.

Simulations after the fixes:

| Simulation | Before the fixes | After |
|---|---|---|
| `template_order_sim.py` 200 articles, seed 20261104 (`simulation/template_order_sim.review-fixes.json`), 4 modes | 0 swaps, 0 wrong | 0 swaps, 0 wrong; clean/none linked 1,326 → 1,325 |
| reviewer B's metamorphic simulation, 200 articles per seed, seeds 1 to 8 (`evidence/REVIEWER_B_SIMULATION_after_fixes.txt`) | seed 1: 906 linked, 10 wrong | seed 1: 1,155 linked, 0 wrong; seeds 2 to 8: 0 wrong |

The one link lost in `template_order_sim.py` (article 121) shows why. Three cells of one name show `+2.43`, `-2.43`
and `-2.43`. The text `+2.43` occurs only in its own cell, but its number run `2.43` occurs in all three, so it is
no longer settled. Pathological sizes, before and after, are in `evidence/PERFORMANCE_after_fixes.txt`. No case
reaches the worker deadline; the reviewers' worst case went from 30.3 s (failed) to 5.5 s.

A nested use that A-05 re-pairs reports the bases of the same-name rule (`reference_role_in_template_output`,
`anchor_in_template_output`, `elimination_in_template_output`), although it is not in template output. The schema's
basis enum was not widened for a naming detail.

One pinned regression changed: the observed fixture `ar-76190003` (`tests/stage03/fixtures/observed/expected.json`)
gets a new extraction digest. Its only difference is that the `RECONCILIATION_ABSTAINED` issue naming `us-00002`, a
use that ends `source_only` in both versions, is no longer emitted (A-07). Every other pinned value is the same.

## 11. Differential and labels after the review fixes

The same 195 retained real bundles and the same engine before the correction (`ec81c7f`):
`differential/DIFFERENTIAL.review-fixes.json` and `OUTPUTS.review-fixes.sha256`. Two extractions of the current
tree gave byte-identical documents.

| Change of a use's render pairing against `ec81c7f` | After `10bf0d2` | After the review fixes |
|---|---|---|
| unchanged | 6,693 | 6,656 |
| same marker, new basis | 32 | 34 |
| different marker (the old pairing was a swap) | 15 | 15 |
| abstained before, matched now | 0 | 35 |
| matched before, abstained now | 2 | 2 |

The script reports one difference as unexpected, because it expects only template-output bases to change. It is the
two nested `Warren919` uses of `en-38148109-a1`, the corpus's one nested repeated name. They keep the same markers
(`cite_ref-Warren919_14-0`, `-1`) with the A-05 basis.

The full comparison with the extraction after S-1 is `differential/COMPARE_S1_TO_REVIEW_FIXES.txt`, made by
`compare_runs.py`:

* 35 uses in 4 articles gain a link (`en-2695828-a1` 16, `ar-10469946-a1` 8, `en-78365026-a1` 7,
  `en-70970708-a2` 4), from the grouping by transclusion (A-02) and the wider support;
* 63 bibliography entries move from a shared transclusion region to their own list item, and 32 that had no region
  gain one (A-03: the list item holding the entry's own identifier link);
* 303 entries that shared a region and have no list item of their own become `note_ambiguous`, so their marker
  observation is `not_inspected` instead of `no_recognized_warning_in_inspected_region` (no negative is made over
  a region that holds other entries);
* 60 identifier witnesses become `render_link_found`. One becomes `region_not_reconciled`: `en-1473997-a1`, an
  entry printed as a paragraph inside `{{Refbegin}}`, not as a list item;
* 9 statuses become `partial` (a `RENDER_NOTE_AMBIGUOUS` issue) and 3 become `complete`.

Every retained label (`differential/LABELLED_LINKS.review-fixes.json`, 150 files, post-exposure, not a gate):

| Labelled render links | Before (`ec81c7f`) | After `10bf0d2` + S-1 | After the review fixes |
|---|---|---|---|
| engine marker = label | 1,372 | 1,376 | 1,387 |
| false attachments | 4 | 0 | 0 |
| engine abstained, label has a marker | 69 | 69 | 58 |

## 12. D-035 scored again after the review fixes (post-exposure, not a gate result)

`post-exposure-d035/review-fixes/` uses the same method as `post-exposure-d035/README.md`: the 48 D-035 bundles
extracted again and scored by the frozen `evaluate_v2.py` against the campaign's own locked and adjudicated labels.

| Language | Render links correct | False | Abstained | G6c | Gates |
|---|---|---|---|---|---|
| ar, D-035 candidate (published) | 182 / 197 | 2 | 13 | 0.924 | G6b failed |
| ar, after `10bf0d2` | 184 / 197 | 0 | 13 | 0.934 | all pass |
| ar, after the review fixes | 192 / 197 | 0 | 5 | 0.975 | all pass |
| en, every engine | 203 / 207 | 0 | 4 | 0.981 | all pass |

Every other metric is unchanged except the marker confusion. In Arabic, 9 definitions move from `not_inspected` to
inspected `none`, all correct. In English, 5 move from `none` to `not_inspected` (the A-03 ambiguous bibliography
entries). G7 (fabricated negatives) stays 0 in both languages. These articles were exposed, so this shows only that
the fixes cost nothing on them. It is not evidence about unseen articles.

