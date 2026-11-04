# R-038: repeated reference names inside one template's output

*CITERIFT — Created and Directed by EVE TELOS · IM*

Owner instruction of 2026-11-04 (DECISIONS.md D-036, `../../authorization/OWNER_DIRECTIVE_2026-11-04_R038.md`,
sections 3 and 4). Status of this document: engineering record of the correction. It is not a verification result
and not acceptance.

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
