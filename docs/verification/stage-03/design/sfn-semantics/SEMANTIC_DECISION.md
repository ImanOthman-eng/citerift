# Short-footnote and repeated-reference semantics: formal decision (2026-11-02)

Authority: the owner's instruction of 2026-11-02, section 3 (DECISIONS.md D-034). This decision is prospective. It
governs the confirmation campaign of `../../protocol/AMENDMENT_2026-11-02_CONFIRMATION.md` and annotation guide
v1.1. It does not change the frozen guide (`../../protocol/ANNOTATION_GUIDE.md`), the frozen scorer, or any earlier
label, prediction, score or adjudication. The final campaign of D-031 stays a failed historical result.

## 1. The disagreement

On the same frozen guide wording, two adjudicators disagreed about repeated identical `{{sfn}}` calls:

- the run-1 adjudicator read guide 3.1 ("a short-footnote template call" is a definition) as making every call a
  definition;
- the final-campaign adjudicator read guide 3.2 ("identical short-footnote calls bind to the first such call") as
  making only the first call a definition and the later calls uses.

The frozen engine lists every call among a container's `definitions` and also as a use. Under the second reading,
article ar-75574746 has 10 extra definitions, and Arabic G5a fell to 106/116.

Guide 3.1 says both "every ... short-footnote template call" and "two definitions with the same name and group are
one reference". Both readings are defensible from the text, so the text is ambiguous.

## 2. What MediaWiki does (evidence)

**Module source.** Retained in `sources/`, with provenance in `PROVENANCE.json`.

- enwiki `Module:Footnotes`, function `sfn`:
  - `name = table.concat({'FOOTNOTE', P1, P2, P3, P4, P5, strip_url(page), strip_url(pages), strip_url(location)}):gsub('%s+', ' ')`;
  - P1-P5 are positional arguments 1-5, trimmed. With more than five, a year is searched from argument 6 on.
  - `page = p or page`; `pages = pp or pages`, with hyphens turned into dashes; `location = at or loc`.
  - `group = group`.
  - The function returns `frame:extensionTag{name='ref', args={group=group, name=name}, content=core(args)}`.
  - The content depends on P1-P5, page, pages, location, the postscript (`postscript or ps or '.'`, with `none`
    meaning empty), `ref`/`Ref`, and the template variant (`{{sfnp}}` adds brackets).
- arwiki `وحدة:Footnotes`, function `sfn`, invoked by `قالب:Sfn`:
  - `name = "FOOTNOTE" .. P1 .. P2 .. P3 .. P4 .. P5 .. page .. pages .. location`, with no whitespace collapsing
    and no URL stripping;
  - `location = loc` only, with no `at` alias;
  - the ref gets **no group** (`args = {name=name}`);
  - the postscript is `postscript or ps or "."`.

**Cite extension.** A named `<ref>` whose name and group already have content is a reuse when its content is
identical. When its content differs, it is a duplicate-key error: the first content is shown with an error. Either
way the reference has one list item, and every call produces its own footnote marker.

**Retained render.** In article ar-75574746 (final campaign packet, Parsoid HTML):

- the 9 calls `{{sfn|Lerner|Mindell|2005}}` render 9 markers `cite_ref-FOOTNOTELernerMindell2005_16-0 … _16-8`,
  all pointing to one list item, `cite_note-FOOTNOTELernerMindell2005-16`;
- the 3 calls `{{sfn|Thiollay|1994}}` likewise render 3 markers and one note.

## 3. Decision

### D1. Reference identity

A reference is identified by its group and its name.

- For `<ref>` tags, the name and group are the written attributes, as before.
- For short-footnote calls, the name and group are what the wiki's Module:Footnotes computes (section 2):
  - enwiki: positional 1-5, `p`/`page`, `pp`/`pages`, `at`/`loc`, whitespace runs collapsed, and `group`;
  - arwiki: positional 1-5, `p`/`page`, `pp`/`pages`, `loc`, whitespace kept, and no group.
- Named and positional spellings of one argument are the same argument (`{{sfn|Smith|2001}}` = `{{sfn|1=Smith|2=2001}}`).
  A repeated argument counts once, with its last value. Comments are removed and values are trimmed.

### D2. Definition and use

A **reference definition** is a content-bearing occurrence of a reference identity that does not repeat the content
of an earlier occurrence of the same identity. For a `<ref>`, "content" is the body, trimmed. For a short footnote,
"content" is the text the module generates, which is decided by the template variant, the name arguments, the
postscript and `ref`.

Every content-bearing occurrence and every reuse is a **use**.

Consequences:

| Situation | Definitions | Uses |
|---|---|---|
| one call or one `<ref>` with content | 1 | 1 |
| *n* identical calls / identical named bodies | 1 (the first in source order) | *n* |
| *n* occurrences, *k* distinct contents (a Cite conflict) | *k* (the first occurrence of each content) | *n* |
| self-closing `<ref name=x/>` | 0 | 1 |
| different names (`p=5` and `p=6`) | one per name | one per call |

### D3. Group identity

References in different groups are different references, even with the same name. On arwiki a short footnote has no
group, whatever `group=` says.

### D4. Source anchors

Every call and every `<ref>` keeps its own exact source anchor in the ledger. A repeated identical occurrence stays in
the container's `definitions` list as source evidence, and the container state `identical_definitions` says that the
occurrences repeat one content.

The reference definition of D2 is derived from the ledger as follows:

- for `single_definition` and `identical_definitions`, it is the container's first definition;
- for `conflicting_definitions`, it is the first definition of each distinct trimmed source text.

Nothing in the ledger is dropped.

### D5. Generated-note containers and rendered markers

A short-footnote reference is one container (`kind` `generated_note`, `layout` `short_footnote`, `name` null),
holding every call. Each call is a use and is linked to its own rendered marker. The container is linked to the one
rendered list item that all its matched uses point to. When two containers point to one rendered note, the note is
withdrawn from both, and the engine records an abstention, never an attachment.

### D6. Accounting

Definition precision and recall (G5a/G5b) count reference definitions (D2). Unit counts (G5c/G5d) count the citation
templates and unstructured texts of reference definitions only; a repeated identical body contributes no unit. Uses,
bindings (a use binds to its reference; any occurrence of the reference's content is an acceptable target),
identifiers and render links are counted as before.

## 4. Engine conformance and the correction made

The frozen engine already listed every occurrence, used container states, and gave every call a use. That is
consistent with D2 and D4, because the reference definition is derivable. It was **inconsistent with D1/D3** in
four respects, each confirmed by a fail-first test (`tests/stage03/test_wiki_sfn_identity.py`; before: 12 failed,
3 controls passed; `../../review/failfirst/sfn-identity/`):

- **S-1:** `group=` on enwiki short footnotes was ignored (container and uses in group `""`). arwiki correctly has
  no group, now by rule rather than by accident.
- **S-2:** alias spellings (`p`/`page`, `pp`/`pages`, enwiki `at`/`loc`) gave separate references.
- **S-3:** calls with one name but a different postscript or `ref` gave separate references, not one conflicting
  reference.
- **S-4:** `{{sfn}}` and `{{sfnp}}` with the same arguments gave separate references, not one conflicting
  reference.

The correction is `_footnote_identity` in `src/citerift/wiki/source.py` and the state rule in `model.py`. It keys
containers by identity and sets `identical_definitions` / `conflicting_definitions` from the content key, with
`REF_DEFINITIONS_CONFLICT` for a conflict.

**Declared conservative boundaries.** These are documented, not fixed; the engine splits where MediaWiki might
merge, and never merges what MediaWiki keeps apart:

- name collisions across fields (`p=5` and `pp=5` both give `…5`);
- enwiki URL stripping and hyphen-to-dash in page values;
- more than five positional arguments on enwiki;
- other templates of the profile's `sfn` family that do not use Module:Footnotes.

A split leaves the shared rendered note withdrawn from both containers (an abstention). **Real-data impact:** none of
the 70 retained real bundles changes (5 contain short footnotes), per `real_bundles_impact.json`.

## 5. Not changed

The frozen annotation guide, the frozen scorer, every earlier annotation, lock, prediction, score and adjudication.
The definition-unit rule D2/D6 is applied only by the prospective guide v1.1 and the prospective scorer
`protocol/scripts/evaluate_v2.py`, which differs from `evaluate.py` only in this derivation.
