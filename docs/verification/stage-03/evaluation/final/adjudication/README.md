# Final campaign adjudication (2026-11-02)

The adjudication step of the single final campaign (FROZEN_PROTOCOL.md section 4.5; AMENDMENT_2026-10-29.md
section 6), done under the owner's instruction of 2026-11-02 (DECISIONS.md D-033). The locked labels, the one
prediction run and the locked scores were not changed. Both label sets are scored, and both are published.

## Inputs

- Disputed items: the 37 items of `../run/disagreements.json` (8 articles: 3 Arabic, 5 English), unchanged.
- `tools/prepare_adjudication.py` checked each locked file against `../annotations/ANNOTATION_LOCK.json`. It then
  copied the guide, the raw-only packets, the locked files and one `disputed_items.json` per article into a
  workspace outside the repository (`/home/user/stage03-adj`, ephemeral). `INPUT_MANIFEST.json` holds the SHA-256
  of every input.
- Briefs: `briefs/brief_adjudicator_{ar,en}.txt`. Each is the committed `../../ADJUDICATION_BRIEF.md` text with
  only `{LANG}`, `{ITEMS}` and `{OUT}` filled in. Two lines are added: one points to a byte-identical copy of the
  guide outside the repository, and one is the amendment's own-helper-directory line.

## Who adjudicated, and how independent they are

There were two adjudicator instances, one per language. Each was a Claude Code `general-purpose` subagent with its
own fresh context, started by the executor session on 2026-11-02 (Arabic 12:27-12:29 UTC, English about 12:30 UTC).

- **What they did not do.** Neither made the locked labels (those came from ChatGPT/Codex evaluator instances).
  Neither wrote or reviewed the engine changes. Each saw only the guide, the raw source and HTML, the window, the
  locked labels and the engine's value for the disputed items.
- **What they report.** Each says it opened nothing in the repository, ran no git, CITERIFT command or network
  access, and wrote only to its own output directory.
- **What cannot be proven.** The executor cannot prove those statements. This is procedural independence between
  AI agents. It is not human gold and not owner review.
- **Same model as the executor.** The adjudicators run the same model as the executor session, and that model
  family also wrote engine code before 2026-10-29.

Their helper scripts are kept as `adjudicator-helpers/*.py.txt`. They are evaluator artifacts, not product code.

## Decisions (`decisions/`, `adjudicated/`)

| Article | Items | Confirmed | Corrected | Corrections |
|---|---|---|---|---|
| ar-73367172 | 4 | 4 | 0 | none. `{{قاموس دورلاند}}` and `{{من سمى هذا}}` are citation templates by purpose (guide 3.1). |
| ar-75574746 | 10 | 10 | 0 | none. Repeated identical `{{sfn}}` calls are uses that bind to the first call (guide 3.2), not new definitions. |
| ar-76553307 | 1 | 0 | 1 | role `textual_mention` changed to `identifier_link`. The DOI is in the publisher URL in `مسار=`. The raw text and key are unchanged. |
| en-1351525729 | 1 | 0 | 1 | the raw text changed from the whole `link.springer.com/10.…` URL to the DOI text. That URL has no `/doi/` path, so the guide's "anything else" row applies. |
| en-1372000829 | 1 | 0 | 1 | same as en-1351525729. |
| en-1374633449 | 18 | 18 | 0 | none. EI2, EI3 and similar templates are citation templates. Repeated `{{sfn}}` calls are uses. The markers are `none`. |
| en-1377523963 | 1 | 1 | 0 | none. The Wiley key is `10.1111/0004-5608.00043`; `/abstract` is a page route. |
| en-1381749944 | 1 | 1 | 0 | none. A list-defined `<ref>` counts as a use under the wording "each `<ref>` tag". |

**Total: 37 items, 34 confirmed, 3 corrected.** The executor checked every adjudicated file:

- it differs from its locked file only in the listed corrections plus the `adjudication` block;
- every location still satisfies `text[cp:cp+len(quote)] == quote`.

### Ambiguities the adjudicators reported

1. **Repeated identical short-footnote calls.** Guide 3.1 lists "a short-footnote template call" among
   definitions, while 3.2 makes identical calls bind to the first. In holdout run 1, the English adjudicator read
   3.1 literally and **added** such calls as definitions (`../../annotations/adjudication_decisions/en-1380771007.json`).
   In this campaign, both adjudicators read 3.2 and **confirmed** that they are not definitions. The two
   adjudications disagree on the same guide wording. This is not resolved here, and no label was edited to resolve it.
2. **Publisher URLs without `/doi/`** (Springer `/10.…`, iopscience `/article/10.…`): whether the URL row of 3.5 is a
   closed list or a set of examples.
3. **List-defined references as uses**: guide 3.2 ("each `<ref>` tag") against the specification, where
   list-defined notes are not uses.

## Scores

- `../run/score_spec_adjudicated.json` uses repository-relative paths and adds the 8 adjudicated files.
- `../run/scores_adjudicated.json` is the frozen `evaluate.py score` run on that spec.
- Its `locked` sections are identical to `../run/scores_locked.json`, field by field (engine, bootstrap, gates, B1,
  B0, A/B/C, per article). The locked result therefore reproduces exactly.

**No gate outcome changes with adjudication.** Gate results, using the adjudicated labels:

| Gate | ar | en |
|---|---|---|
| G1a identifier precision ≥ 0.97 | 1.000 pass | 1.000 pass |
| G1b identifier recall ≥ 0.90 | 0.970 pass | 0.963 pass |
| G2 key error rate ≤ 0.01 | 0.000 pass | **0.0192 fail** (1 of 52) |
| G3a promotions = 0 | 0 pass | 0 pass |
| G3b role agreement ≥ 0.90 | 1.000 pass | 0.942 pass |
| G4a/b/c uses | 1.000 / 1.000 / 1.000 pass | 1.000 / 0.992 / 1.000 pass |
| G5a definition precision ≥ 0.95 | **0.914 fail** (106 / 116) | 0.984 pass |
| G5b definition recall ≥ 0.95 | 1.000 pass | 0.984 pass |
| G5c/d unit precision / recall ≥ 0.95 | 0.981 / 0.981 pass | 0.973 / 0.956 pass |
| G6a/b/c render | 1.000 / 0 false attachments / 1.000 pass | 1.000 / 0 / 1.000 pass |
| G7 fabricated negatives = 0 | 0 pass | 0 pass |
| Minimum denominators (50 identifiers, 80 uses, 60 definitions, 60 linkable) | **identifiers 33 fail**; 119 / 106 / 119 pass | 54 / 118 / 122 / 117 pass |

- **Bootstrap.** The 95 % article-cluster bootstrap for Arabic definition precision is [0.733, 1.000].
- **Arabic identifier denominator.** Adjudication changes no target-identifier count: it stays 33.
- **Not gates.** The G2 and G5a outcomes after the post-exposure repair RF-60, and under the other short-footnote
  reading, are given in `../../../TEST_RESULTS.md`. Neither is a gate result.
